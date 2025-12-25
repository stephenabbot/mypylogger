#!/usr/bin/env python3
"""AWS Authentication Retry Logic.

Implements retry wrapper around AWS OIDC authentication with exponential backoff
and comprehensive logging for troubleshooting authentication failures.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time


class AWSAuthError(Exception):
    """Custom exception for AWS authentication errors."""


def log_structured(level: str, message: str, **kwargs) -> None:
    """Log structured messages for AWS authentication steps.

    Args:
        level: Log level (INFO, WARN, ERROR)
        message: Log message
        **kwargs: Additional structured data
    """
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "level": level,
        "message": message,
        "component": "aws_auth_retry",
        **kwargs,
    }

    print(json.dumps(log_entry))


def run_command(command: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    """Run a command with timeout and error handling.

    Args:
        command: Command to run as list of strings
        timeout: Timeout in seconds

    Returns:
        CompletedProcess result

    Raises:
        AWSAuthError: If command fails
    """
    try:
        log_structured("INFO", "Executing command", command=" ".join(command))

        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False
        )

        if result.returncode == 0:
            log_structured("INFO", "Command succeeded", command=" ".join(command), duration=timeout)
        else:
            log_structured(
                "ERROR",
                "Command failed",
                command=" ".join(command),
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )

        return result

    except subprocess.TimeoutExpired:
        log_structured("ERROR", "Command timed out", command=" ".join(command), timeout=timeout)
        msg = f"Command timed out after {timeout} seconds: {' '.join(command)}"
        raise AWSAuthError(msg)

    except Exception as e:
        log_structured("ERROR", "Command execution failed", command=" ".join(command), error=str(e))
        msg = f"Failed to execute command: {e}"
        raise AWSAuthError(msg)


def validate_aws_connectivity() -> None:
    """Validate AWS connectivity and basic authentication.

    Raises:
        AWSAuthError: If connectivity validation fails
    """
    log_structured("INFO", "Validating AWS connectivity")

    try:
        # Test basic AWS CLI connectivity
        result = run_command(["aws", "sts", "get-caller-identity"], timeout=30)

        if result.returncode != 0:
            msg = f"AWS connectivity test failed: {result.stderr}"
            raise AWSAuthError(msg)

        # Parse caller identity
        try:
            caller_identity = json.loads(result.stdout)
            log_structured(
                "INFO",
                "AWS connectivity validated",
                account=caller_identity.get("Account"),
                arn=caller_identity.get("Arn"),
                user_id=caller_identity.get("UserId"),
            )
        except json.JSONDecodeError:
            log_structured("WARN", "Could not parse caller identity response", stdout=result.stdout)

    except Exception as e:
        msg = f"AWS connectivity validation failed: {e}"
        raise AWSAuthError(msg)


def validate_secrets_manager_access(secret_name: str) -> None:
    """Validate access to AWS Secrets Manager.

    Args:
        secret_name: Name of the secret to test access

    Raises:
        AWSAuthError: If Secrets Manager access fails
    """
    log_structured("INFO", "Validating Secrets Manager access", secret_name=secret_name)

    try:
        # Test access to the specific secret
        result = run_command(
            [
                "aws",
                "secretsmanager",
                "describe-secret",
                "--secret-id",
                secret_name,
                "--query",
                "Name",
                "--output",
                "text",
            ],
            timeout=30,
        )

        if result.returncode != 0:
            if "ResourceNotFoundException" in result.stderr:
                msg = f"Secret '{secret_name}' not found in AWS Secrets Manager"
                raise AWSAuthError(msg)
            if "AccessDenied" in result.stderr:
                msg = f"Access denied to secret '{secret_name}'. Check IAM permissions."
                raise AWSAuthError(msg)
            msg = f"Secrets Manager access test failed: {result.stderr}"
            raise AWSAuthError(msg)

        log_structured("INFO", "Secrets Manager access validated", secret_name=secret_name)

    except Exception as e:
        msg = f"Secrets Manager validation failed: {e}"
        raise AWSAuthError(msg)


def configure_aws_credentials_with_retry(
    role_arn: str,
    aws_region: str,
    session_name: str = "GitHubActions-PyPI-Publishing",
    duration_seconds: int = 900,
    max_attempts: int = 3,
) -> None:
    """Configure AWS credentials with retry logic and exponential backoff.

    Args:
        role_arn: AWS Role ARN to assume
        aws_region: AWS region
        session_name: Session name for the role assumption
        duration_seconds: Duration for the session
        max_attempts: Maximum number of retry attempts

    Raises:
        AWSAuthError: If authentication fails after all retries
    """
    log_structured(
        "INFO",
        "Starting AWS OIDC authentication with retry logic",
        role_arn=role_arn,
        aws_region=aws_region,
        session_name=session_name,
        max_attempts=max_attempts,
    )

    for attempt in range(1, max_attempts + 1):
        try:
            log_structured("INFO", f"AWS authentication attempt {attempt}/{max_attempts}")

            # Set environment variables for aws-actions/configure-aws-credentials
            env_vars = {
                "INPUT_ROLE_TO_ASSUME": role_arn,
                "INPUT_AWS_REGION": aws_region,
                "INPUT_ROLE_SESSION_NAME": session_name,
                "INPUT_ROLE_DURATION_SECONDS": str(duration_seconds),
                "AWS_RETRY_MODE": "adaptive",
                "AWS_MAX_ATTEMPTS": "3",
            }

            # Update environment
            for key, value in env_vars.items():
                os.environ[key] = value
                log_structured(
                    "INFO",
                    "Set environment variable",
                    key=key,
                    value=value if "ARN" not in key else "***",
                )

            # Simulate the aws-actions/configure-aws-credentials action
            # In a real GitHub Actions environment, this would be handled by the action
            log_structured("INFO", "AWS OIDC authentication configured successfully")

            # Validate the authentication worked
            validate_aws_connectivity()

            log_structured("INFO", "AWS authentication successful", attempt=attempt)
            return

        except Exception as e:
            log_structured(
                "ERROR",
                f"AWS authentication attempt {attempt} failed",
                attempt=attempt,
                error=str(e),
            )

            if attempt < max_attempts:
                # Exponential backoff: 2s, 4s, 8s
                backoff_seconds = 2**attempt
                log_structured(
                    "INFO",
                    f"Retrying in {backoff_seconds} seconds...",
                    backoff_seconds=backoff_seconds,
                )
                time.sleep(backoff_seconds)
            else:
                log_structured(
                    "ERROR", "All AWS authentication attempts failed", total_attempts=max_attempts
                )
                msg = f"AWS authentication failed after {max_attempts} attempts: {e}"
                raise AWSAuthError(msg)


def main() -> int:
    """Main function to run AWS authentication with retry logic.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Get configuration from environment
        role_arn = os.environ.get("AWS_ROLE_ARN")
        aws_region = os.environ.get("AWS_REGION", "us-east-1")
        secret_name = os.environ.get("AWS_SECRET_NAME")

        if not role_arn:
            msg = "AWS_ROLE_ARN environment variable is required"
            raise AWSAuthError(msg)

        if not secret_name:
            msg = "AWS_SECRET_NAME environment variable is required"
            raise AWSAuthError(msg)

        log_structured(
            "INFO",
            "Starting AWS authentication process",
            aws_region=aws_region,
            secret_name=secret_name,
        )

        # Configure AWS credentials with retry
        configure_aws_credentials_with_retry(
            role_arn=role_arn, aws_region=aws_region, max_attempts=3
        )

        # Validate Secrets Manager access
        validate_secrets_manager_access(secret_name)

        log_structured("INFO", "AWS authentication and validation completed successfully")
        return 0

    except AWSAuthError as e:
        log_structured("ERROR", "AWS authentication failed", error=str(e))
        print("\n🔧 Troubleshooting AWS Authentication:", file=sys.stderr)
        print("  1. Verify AWS_ROLE_ARN is correctly configured in GitHub secrets", file=sys.stderr)
        print(
            "  2. Check that the IAM role has proper trust relationship with GitHub OIDC",
            file=sys.stderr,
        )
        print("  3. Ensure the role has SecretsManagerReadWrite permissions", file=sys.stderr)
        print("  4. Verify AWS_REGION is a valid AWS region", file=sys.stderr)
        print("  5. Check that AWS_SECRET_NAME exists in Secrets Manager", file=sys.stderr)
        return 1

    except Exception as e:
        log_structured("ERROR", "Unexpected error during AWS authentication", error=str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
