#!/usr/bin/env python3
"""AWS Configuration Validation Script.

Validates AWS OIDC configuration for PyPI publishing workflow.
Checks AWS_REGION format and AWS_ROLE_ARN presence with proper error handling.
"""

from __future__ import annotations

import os
import re
import sys


class AWSConfigError(Exception):
    """Custom exception for AWS configuration errors."""


def validate_aws_region(region: str | None) -> str:
    """Validate AWS region format.

    Args:
        region: AWS region string to validate

    Returns:
        Validated region string

    Raises:
        AWSConfigError: If region format is invalid
    """
    if not region:
        # Use default region
        region = "us-east-1"
        print(f"ℹ️  No AWS_REGION specified, using default: {region}")
        return region

    # AWS region format: 2-3 letter region code, dash, direction, dash, number
    # Examples: us-east-1, eu-west-2, ap-southeast-1, ca-central-1
    region_pattern = r"^[a-z]{2,3}-[a-z]+-\d+$"

    if not re.match(region_pattern, region):
        msg = (
            f"Invalid AWS region format: '{region}'. "
            f"Expected format: <region>-<direction>-<number> (e.g., us-east-1, eu-west-2)"
        )
        raise AWSConfigError(msg)

    # Additional validation for known AWS regions
    valid_regions = {
        # US regions
        "us-east-1",
        "us-east-2",
        "us-west-1",
        "us-west-2",
        # EU regions
        "eu-central-1",
        "eu-west-1",
        "eu-west-2",
        "eu-west-3",
        "eu-north-1",
        "eu-south-1",
        # Asia Pacific regions
        "ap-east-1",
        "ap-south-1",
        "ap-southeast-1",
        "ap-southeast-2",
        "ap-northeast-1",
        "ap-northeast-2",
        "ap-northeast-3",
        # Canada
        "ca-central-1",
        # South America
        "sa-east-1",
        # Middle East
        "me-south-1",
        # Africa
        "af-south-1",
        # China (special regions)
        "cn-north-1",
        "cn-northwest-1",
        # GovCloud
        "us-gov-east-1",
        "us-gov-west-1",
    }

    if region not in valid_regions:
        print(f"⚠️  Warning: '{region}' is not a recognized AWS region. Proceeding anyway.")

    return region


def validate_aws_role_arn(role_arn: str | None) -> str:
    """Validate AWS Role ARN format.

    Args:
        role_arn: AWS Role ARN to validate

    Returns:
        Validated role ARN string

    Raises:
        AWSConfigError: If role ARN is missing or invalid
    """
    if not role_arn:
        msg = (
            "AWS_ROLE_ARN is required for OIDC authentication. "
            "Please set the AWS_ROLE_ARN secret in your GitHub repository."
        )
        raise AWSConfigError(msg)

    # AWS Role ARN format: arn:aws:iam::account-id:role/role-name
    arn_pattern = r"^arn:aws:iam::\d{12}:role/[a-zA-Z0-9+=,.@_-]+$"

    if not re.match(arn_pattern, role_arn):
        msg = (
            f"Invalid AWS Role ARN format: '{role_arn}'. "
            f"Expected format: arn:aws:iam::ACCOUNT-ID:role/ROLE-NAME"
        )
        raise AWSConfigError(msg)

    return role_arn


def validate_aws_secret_name(secret_name: str | None) -> str:
    """Validate AWS Secrets Manager secret name.

    Args:
        secret_name: Secret name to validate

    Returns:
        Validated secret name

    Raises:
        AWSConfigError: If secret name is missing or invalid
    """
    if not secret_name:
        msg = (
            "AWS_SECRET_NAME is required for PyPI token retrieval. "
            "Please set the AWS_SECRET_NAME secret in your GitHub repository."
        )
        raise AWSConfigError(msg)

    # AWS Secrets Manager name validation
    # Can contain alphanumeric characters and /_+=.@-
    secret_pattern = r"^[a-zA-Z0-9/_+=.@-]+$"

    if not re.match(secret_pattern, secret_name):
        msg = (
            f"Invalid AWS secret name format: '{secret_name}'. "
            f"Secret names can only contain alphanumeric characters and /_+=.@-"
        )
        raise AWSConfigError(msg)

    if len(secret_name) > 512:
        msg = (
            f"AWS secret name too long: {len(secret_name)} characters. "
            f"Maximum length is 512 characters."
        )
        raise AWSConfigError(msg)

    return secret_name


def validate_aws_configuration() -> dict:
    """Validate complete AWS OIDC configuration.

    Returns:
        Dictionary with validated configuration values

    Raises:
        AWSConfigError: If any configuration is invalid
    """
    print("🔍 Validating AWS OIDC configuration...")

    errors: list[str] = []
    config = {}

    try:
        # Validate AWS region
        aws_region = os.environ.get("AWS_REGION") or os.environ.get("INPUT_AWS_REGION")
        config["aws_region"] = validate_aws_region(aws_region)
        print(f"✅ AWS Region: {config['aws_region']}")
    except AWSConfigError as e:
        errors.append(f"AWS Region: {e}")

    try:
        # Validate AWS Role ARN
        aws_role_arn = os.environ.get("AWS_ROLE_ARN") or os.environ.get("INPUT_AWS_ROLE_ARN")
        config["aws_role_arn"] = validate_aws_role_arn(aws_role_arn)
        print(f"✅ AWS Role ARN: {config['aws_role_arn']}")
    except AWSConfigError as e:
        errors.append(f"AWS Role ARN: {e}")

    try:
        # Validate AWS Secret Name
        aws_secret_name = os.environ.get("AWS_SECRET_NAME") or os.environ.get(
            "INPUT_AWS_SECRET_NAME"
        )
        config["aws_secret_name"] = validate_aws_secret_name(aws_secret_name)
        print(f"✅ AWS Secret Name: {config['aws_secret_name']}")
    except AWSConfigError as e:
        errors.append(f"AWS Secret Name: {e}")

    if errors:
        error_message = "AWS configuration validation failed:\n" + "\n".join(
            f"  - {error}" for error in errors
        )
        raise AWSConfigError(error_message)

    print("✅ AWS OIDC configuration validation successful")
    return config


def main() -> int:
    """Main function to run AWS configuration validation.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        config = validate_aws_configuration()

        print("\n📋 Validated Configuration:")
        for key, value in config.items():
            # Mask sensitive values
            if "arn" in key.lower():
                masked_value = value[:20] + "..." + value[-10:] if len(value) > 30 else value
                print(f"  {key}: {masked_value}")
            else:
                print(f"  {key}: {value}")

        return 0

    except AWSConfigError as e:
        print(f"❌ {e}", file=sys.stderr)
        print("\n🔧 Troubleshooting:", file=sys.stderr)
        print("  1. Ensure AWS_ROLE_ARN is set in GitHub repository secrets", file=sys.stderr)
        print(
            "  2. Verify AWS_REGION is a valid AWS region (or omit for us-east-1 default)",
            file=sys.stderr,
        )
        print(
            "  3. Check AWS_SECRET_NAME contains the correct Secrets Manager secret name",
            file=sys.stderr,
        )
        print(
            "  4. Verify the IAM role has proper permissions for Secrets Manager access",
            file=sys.stderr,
        )
        return 1

    except Exception as e:
        print(f"❌ Unexpected error during validation: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
