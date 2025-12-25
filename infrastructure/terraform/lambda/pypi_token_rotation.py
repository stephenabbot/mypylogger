"""AWS Lambda function for PyPI token rotation.

This function handles automatic rotation of PyPI API tokens stored in AWS Secrets Manager.
It's triggered by Secrets Manager rotation schedule.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import boto3

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
secrets_client = boto3.client("secretsmanager")


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle PyPI token rotation.

    Args:
        event: Lambda event containing rotation details
        context: Lambda context

    Returns:
        Response indicating success or failure
    """
    try:
        # Extract rotation details from event
        secret_arn = event.get("SecretId", "${secret_arn}")
        token_type = event.get("ClientRequestToken", "AWSCURRENT")
        step = event.get("Step", "createSecret")

        logger.info(f"Starting PyPI token rotation for secret: {secret_arn}")
        logger.info(f"Rotation step: {step}, Token type: {token_type}")

        # Handle different rotation steps
        if step == "createSecret":
            return create_secret(secret_arn, token_type)
        if step == "setSecret":
            return set_secret(secret_arn, token_type)
        if step == "testSecret":
            return test_secret(secret_arn, token_type)
        if step == "finishSecret":
            return finish_secret(secret_arn, token_type)
        logger.error(f"Unknown rotation step: {step}")
        msg = f"Unknown rotation step: {step}"
        raise ValueError(msg)

    except Exception as e:
        logger.exception(f"PyPI token rotation failed: {e!s}")
        raise


def create_secret(secret_arn: str, token_type: str) -> dict[str, Any]:
    """Create new secret version with rotated token.

    Args:
        secret_arn: ARN of the secret to rotate
        token_type: Type of token being rotated

    Returns:
        Success response
    """
    logger.info("Creating new secret version")

    # In a real implementation, this would:
    # 1. Generate a new PyPI API token
    # 2. Store it as a new secret version
    # 3. Mark it as AWSPENDING

    # For now, this is a placeholder that maintains the existing token
    try:
        current_secret = secrets_client.get_secret_value(
            SecretId=secret_arn, VersionStage="AWSCURRENT"
        )

        # Create new version with same token (placeholder)
        secrets_client.put_secret_value(
            SecretId=secret_arn,
            ClientRequestToken=token_type,
            SecretString=current_secret["SecretString"],
            VersionStages=["AWSPENDING"],
        )

        logger.info("New secret version created successfully")
        return {"statusCode": 200, "body": "Secret created"}

    except Exception as e:
        logger.exception(f"Failed to create secret: {e!s}")
        raise


def set_secret(secret_arn: str, token_type: str) -> dict[str, Any]:
    """Configure the new secret in the service.

    Args:
        secret_arn: ARN of the secret to rotate
        token_type: Type of token being rotated

    Returns:
        Success response
    """
    logger.info("Setting secret in service")

    # In a real implementation, this would:
    # 1. Update PyPI account with new token
    # 2. Verify the token is properly configured

    # For now, this is a placeholder
    logger.info("Secret set in service successfully")
    return {"statusCode": 200, "body": "Secret set"}


def test_secret(secret_arn: str, token_type: str) -> dict[str, Any]:
    """Test the new secret to ensure it works.

    Args:
        secret_arn: ARN of the secret to rotate
        token_type: Type of token being rotated

    Returns:
        Success response
    """
    logger.info("Testing new secret")

    try:
        # Get the pending secret
        pending_secret = secrets_client.get_secret_value(
            SecretId=secret_arn, VersionId=token_type, VersionStage="AWSPENDING"
        )

        # Parse the secret
        secret_data = json.loads(pending_secret["SecretString"])
        token = secret_data.get("token")

        if not token:
            msg = "No token found in secret"
            raise ValueError(msg)

        # In a real implementation, this would:
        # 1. Test the token against PyPI API
        # 2. Verify it has correct permissions
        # 3. Ensure it can publish packages

        # For now, basic validation
        if not token.startswith("pypi-"):
            msg = "Invalid PyPI token format"
            raise ValueError(msg)

        logger.info("Secret tested successfully")
        return {"statusCode": 200, "body": "Secret tested"}

    except Exception as e:
        logger.exception(f"Failed to test secret: {e!s}")
        raise


def finish_secret(secret_arn: str, token_type: str) -> dict[str, Any]:
    """Finalize the rotation by making the new secret current.

    Args:
        secret_arn: ARN of the secret to rotate
        token_type: Type of token being rotated

    Returns:
        Success response
    """
    logger.info("Finishing secret rotation")

    try:
        # Move AWSPENDING to AWSCURRENT
        secrets_client.update_secret_version_stage(
            SecretId=secret_arn,
            VersionStage="AWSCURRENT",
            ClientRequestToken=token_type,
            RemoveFromVersionId=secrets_client.describe_secret(SecretId=secret_arn)[
                "VersionIdsToStages"
            ]["AWSCURRENT"][0],
        )

        logger.info("Secret rotation completed successfully")
        return {"statusCode": 200, "body": "Rotation completed"}

    except Exception as e:
        logger.exception(f"Failed to finish rotation: {e!s}")
        raise
