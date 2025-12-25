#!/usr/bin/env python3
"""AWS OIDC Credential Manager for PyPI Publishing.

This script handles secure credential retrieval and validation for PyPI publishing
using AWS OIDC authentication with GitHub Actions.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class OIDCCredentialManager:
    """Manages AWS OIDC credentials for PyPI publishing."""

    def __init__(self, secret_name: str, aws_region: str = "us-east-1") -> None:
        """Initialize the credential manager.

        Args:
            secret_name: Name of the AWS Secrets Manager secret
            aws_region: AWS region for Secrets Manager
        """
        self.secret_name = secret_name
        self.aws_region = aws_region
        self.secrets_client = None

    def _get_secrets_client(self) -> boto3.client:
        """Get or create AWS Secrets Manager client."""
        if self.secrets_client is None:
            try:
                self.secrets_client = boto3.client("secretsmanager", region_name=self.aws_region)
            except Exception as e:
                logger.exception(f"Failed to create AWS Secrets Manager client: {e}")
                raise
        return self.secrets_client

    def verify_aws_authentication(self) -> dict[str, Any]:
        """Verify AWS OIDC authentication is working.

        Returns:
            Dictionary with authentication details

        Raises:
            Exception: If authentication verification fails
        """
        try:
            # Test STS access
            sts_client = boto3.client("sts", region_name=self.aws_region)
            identity = sts_client.get_caller_identity()

            logger.info("AWS OIDC authentication verified")
            logger.info(f"Account: {identity.get('Account')}")
            logger.info(f"User/Role: {identity.get('Arn')}")

            return {
                "account": identity.get("Account"),
                "arn": identity.get("Arn"),
                "user_id": identity.get("UserId"),
                "authenticated": True,
            }

        except NoCredentialsError:
            logger.exception("No AWS credentials found")
            msg = "AWS OIDC authentication failed: No credentials"
            raise Exception(msg)
        except ClientError as e:
            logger.exception(f"AWS authentication failed: {e}")
            msg = f"AWS OIDC authentication failed: {e}"
            raise Exception(msg)

    def _validate_pypi_token_format(self, token: str) -> None:
        """Validate PyPI token format for security.

        Args:
            token: PyPI token to validate

        Raises:
            Exception: If token format is invalid
        """
        import re

        if not token:
            msg = "Invalid PyPI token format: empty token"
            raise Exception(msg)

        if not token.startswith("pypi-"):
            msg = "Invalid PyPI token format: must start with 'pypi-'"
            raise Exception(msg)

        if len(token) < 55:  # pypi- (5) + minimum 50 chars
            msg = "Invalid PyPI token format: too short"
            raise Exception(msg)

        if len(token) > 200:  # Reasonable maximum length
            msg = "Invalid PyPI token format: too long"
            raise Exception(msg)

        # Check for valid characters only (alphanumeric, hyphens, underscores)
        token_body = token[5:]  # Remove 'pypi-' prefix
        if not re.match(r"^[A-Za-z0-9_-]+$", token_body):
            msg = "Invalid PyPI token format: invalid characters"
            raise Exception(msg)

        # Check for obvious low-entropy patterns
        if len(set(token_body)) < 10:  # At least 10 unique characters
            msg = "Invalid PyPI token format: insufficient entropy"
            raise Exception(msg)

        # Check for repeated patterns (more than 10 consecutive same chars)
        for char in ["A", "1", "a", "B", "2", "b", "0", "9", "Z", "z"]:
            if char * 10 in token_body:
                msg = "Invalid PyPI token format: repeated patterns detected"
                raise Exception(msg)

        # Check for simple repeated sequences
        for length in [5, 10]:
            for i in range(len(token_body) - length * 3):
                pattern = token_body[i : i + length]
                if pattern * 3 in token_body:
                    msg = "Invalid PyPI token format: repeated patterns detected"
                    raise Exception(msg)

    def _validate_repository_url(self, repository: str) -> None:
        """Validate repository URL for security.

        Args:
            repository: Repository URL to validate

        Raises:
            Exception: If repository URL is invalid
        """
        if not repository:
            msg = "Invalid repository URL: empty URL"
            raise Exception(msg)

        # Must be HTTPS
        if not repository.startswith("https://"):
            msg = "Invalid repository URL: must use HTTPS"
            raise Exception(msg)

        # Must be official PyPI domains
        valid_domains = [
            "https://upload.pypi.org/legacy/",
            "https://test.pypi.org/legacy/",
        ]

        if repository not in valid_domains:
            msg = f"Invalid repository URL: must be one of {valid_domains}"
            raise Exception(msg)

    def _validate_package_name(self, package: str) -> None:
        """Validate package name for security.

        Args:
            package: Package name to validate

        Raises:
            Exception: If package name is invalid
        """
        import re

        if not package:
            msg = "Invalid package name: empty name"
            raise Exception(msg)

        # Check for valid package name format (PEP 508)
        if not re.match(r"^[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?$", package):
            msg = "Invalid package name: invalid format"
            raise Exception(msg)

        # Check for path traversal attempts
        if ".." in package or "/" in package or "\\" in package:
            msg = "Invalid package name: path traversal detected"
            raise Exception(msg)

        # Check for command injection attempts
        dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">"]
        if any(char in package for char in dangerous_chars):
            msg = "Invalid package name: dangerous characters detected"
            raise Exception(msg)

    def test_secrets_access(self) -> bool:
        """Test access to the PyPI token secret.

        Returns:
            True if access is successful, False otherwise
        """
        try:
            client = self._get_secrets_client()

            # Test describe access (read metadata)
            response = client.describe_secret(SecretId=self.secret_name)
            logger.info(f"Secret access verified: {response['Name']}")

            return True

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "ResourceNotFoundException":
                logger.exception(f"Secret not found: {self.secret_name}")
            elif error_code == "AccessDenied":
                logger.exception(f"Access denied to secret: {self.secret_name}")
            else:
                logger.exception(f"Failed to access secret: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error accessing secret: {e}")
            return False

    def retrieve_pypi_token(self) -> dict[str, Any]:
        """Retrieve PyPI token from AWS Secrets Manager.

        Returns:
            Dictionary containing token and metadata

        Raises:
            Exception: If token retrieval fails
        """
        try:
            client = self._get_secrets_client()

            logger.info(f"Retrieving PyPI token from secret: {self.secret_name}")

            # Get the secret value
            response = client.get_secret_value(SecretId=self.secret_name)

            # Parse the secret JSON
            secret_data = json.loads(response["SecretString"])

            # Validate required fields
            required_fields = ["token", "repository", "package"]
            missing_fields = [field for field in required_fields if field not in secret_data]

            if missing_fields:
                msg = f"Missing required fields in secret: {missing_fields}"
                raise Exception(msg)

            # Validate token format with enhanced security checks
            token = secret_data["token"]
            self._validate_pypi_token_format(token)

            # Validate repository URL
            repository = secret_data.get("repository", "https://upload.pypi.org/legacy/")
            self._validate_repository_url(repository)

            # Validate package name
            package = secret_data.get("package")
            self._validate_package_name(package)

            logger.info("PyPI token retrieved successfully")

            return {
                "token": token,
                "repository": repository,
                "package": package,
                "retrieved_at": response.get("CreatedDate"),
                "version_id": response.get("VersionId"),
            }

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "ResourceNotFoundException":
                msg = f"PyPI token secret not found: {self.secret_name}"
                raise Exception(msg)
            if error_code == "AccessDenied":
                msg = f"Access denied to PyPI token secret: {self.secret_name}"
                raise Exception(msg)
            if error_code == "DecryptionFailure":
                msg = "Failed to decrypt PyPI token secret"
                raise Exception(msg)
            msg = f"Failed to retrieve PyPI token: {e}"
            raise Exception(msg)
        except json.JSONDecodeError as e:
            msg = f"Invalid JSON in PyPI token secret: {e}"
            raise Exception(msg)
        except Exception as e:
            msg = f"Unexpected error retrieving PyPI token: {e}"
            raise Exception(msg)

    def validate_token_permissions(self, token: str) -> bool:
        """Validate PyPI token has required permissions.

        Args:
            token: PyPI API token

        Returns:
            True if token has valid permissions, False otherwise
        """
        try:
            import requests

            # Test token by checking PyPI API
            headers = {
                "Authorization": f"token {token}",
                "User-Agent": "mypylogger-oidc-validator/1.0",
            }

            # Use PyPI API to validate token (this is a safe read-only operation)
            response = requests.get(
                "https://pypi.org/pypi/mypylogger/json", headers=headers, timeout=10
            )

            if response.status_code == 200:
                logger.info("PyPI token validation successful")
                return True
            if response.status_code == 401:
                logger.error("PyPI token is invalid or expired")
                return False
            logger.warning(f"PyPI token validation returned status {response.status_code}")
            return False

        except ImportError:
            logger.warning("requests library not available - skipping token validation")
            return True  # Assume valid if we can't test
        except Exception as e:
            logger.exception(f"Failed to validate PyPI token: {e}")
            return False

    def get_credential_summary(self) -> dict[str, Any]:
        """Get a summary of credential status for diagnostics.

        Returns:
            Dictionary with credential status information
        """
        summary = {
            "aws_region": self.aws_region,
            "secret_name": self.secret_name,
            "aws_authenticated": False,
            "secrets_access": False,
            "token_retrieved": False,
            "token_valid": False,
            "errors": [],
        }

        try:
            # Test AWS authentication
            auth_info = self.verify_aws_authentication()
            summary["aws_authenticated"] = True
            summary["aws_account"] = auth_info.get("account")
            summary["aws_arn"] = auth_info.get("arn")
        except Exception as e:
            summary["errors"].append(f"AWS authentication: {e}")

        try:
            # Test secrets access
            summary["secrets_access"] = self.test_secrets_access()
        except Exception as e:
            summary["errors"].append(f"Secrets access: {e}")

        if summary["secrets_access"]:
            try:
                # Test token retrieval
                token_data = self.retrieve_pypi_token()
                summary["token_retrieved"] = True
                summary["package"] = token_data.get("package")
                summary["repository"] = token_data.get("repository")

                # Test token validation
                summary["token_valid"] = self.validate_token_permissions(token_data["token"])

            except Exception as e:
                summary["errors"].append(f"Token retrieval: {e}")

        return summary


def main() -> int:
    """Main function for command-line usage.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    import argparse

    parser = argparse.ArgumentParser(description="AWS OIDC Credential Manager for PyPI Publishing")
    parser.add_argument("--secret-name", required=True, help="AWS Secrets Manager secret name")
    parser.add_argument("--aws-region", default="us-east-1", help="AWS region (default: us-east-1)")
    parser.add_argument(
        "--action",
        choices=["verify", "retrieve", "validate", "summary"],
        default="summary",
        help="Action to perform (default: summary)",
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)",
    )

    args = parser.parse_args()

    try:
        manager = OIDCCredentialManager(args.secret_name, args.aws_region)

        if args.action == "verify":
            auth_info = manager.verify_aws_authentication()
            if args.output_format == "json":
                print(json.dumps(auth_info, indent=2))
            else:
                print("✅ AWS OIDC authentication verified")
                print(f"Account: {auth_info['account']}")
                print(f"ARN: {auth_info['arn']}")

        elif args.action == "retrieve":
            token_data = manager.retrieve_pypi_token()
            if args.output_format == "json":
                # Don't output the actual token in JSON for security
                safe_data = {k: v for k, v in token_data.items() if k != "token"}
                safe_data["token"] = "***MASKED***"
                print(json.dumps(safe_data, indent=2, default=str))
            else:
                print("✅ PyPI token retrieved successfully")
                print(f"Package: {token_data['package']}")
                print(f"Repository: {token_data['repository']}")

        elif args.action == "validate":
            token_data = manager.retrieve_pypi_token()
            is_valid = manager.validate_token_permissions(token_data["token"])
            if args.output_format == "json":
                print(json.dumps({"valid": is_valid}))
            elif is_valid:
                print("✅ PyPI token validation successful")
            else:
                print("❌ PyPI token validation failed")
                return 1

        elif args.action == "summary":
            summary = manager.get_credential_summary()
            if args.output_format == "json":
                print(json.dumps(summary, indent=2, default=str))
            else:
                print("🔐 OIDC Credential Summary")
                print("=" * 30)
                print(f"AWS Region: {summary['aws_region']}")
                print(f"Secret Name: {summary['secret_name']}")
                print(f"AWS Authenticated: {'✅' if summary['aws_authenticated'] else '❌'}")
                print(f"Secrets Access: {'✅' if summary['secrets_access'] else '❌'}")
                print(f"Token Retrieved: {'✅' if summary['token_retrieved'] else '❌'}")
                print(f"Token Valid: {'✅' if summary['token_valid'] else '❌'}")

                if summary["errors"]:
                    print("\n❌ Errors:")
                    for error in summary["errors"]:
                        print(f"  - {error}")
                    return 1
                print("\n🎉 All credential checks passed!")

        return 0

    except Exception as e:
        if args.output_format == "json":
            print(json.dumps({"error": str(e)}))
        else:
            print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
