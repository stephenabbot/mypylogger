"""Unit tests for OIDC credential manager."""

import json
from pathlib import Path

# Import the module we're testing
import sys
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError, NoCredentialsError
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from oidc_credential_manager import OIDCCredentialManager


class TestOIDCCredentialManager:
    """Test cases for OIDCCredentialManager."""

    def test_initialization(self) -> None:
        """Test OIDCCredentialManager initialization."""
        manager = OIDCCredentialManager("test-secret", "us-west-2")

        assert manager.secret_name == "test-secret"  # noqa: S105
        assert manager.aws_region == "us-west-2"
        assert manager.secrets_client is None

    def test_initialization_with_defaults(self) -> None:
        """Test OIDCCredentialManager initialization with defaults."""
        manager = OIDCCredentialManager("test-secret")

        assert manager.secret_name == "test-secret"  # noqa: S105
        assert manager.aws_region == "us-east-1"

    @patch("boto3.client")
    def test_get_secrets_client_creation(self, mock_boto_client: Mock) -> None:
        """Test secrets client creation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        manager = OIDCCredentialManager("test-secret")
        client = manager._get_secrets_client()

        assert client == mock_client
        mock_boto_client.assert_called_once_with("secretsmanager", region_name="us-east-1")

    @patch("boto3.client")
    def test_get_secrets_client_reuse(self, mock_boto_client: Mock) -> None:
        """Test secrets client reuse."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        manager = OIDCCredentialManager("test-secret")
        client1 = manager._get_secrets_client()
        client2 = manager._get_secrets_client()

        assert client1 == client2
        mock_boto_client.assert_called_once()

    @patch("boto3.client")
    def test_get_secrets_client_exception(self, mock_boto_client: Mock) -> None:
        """Test secrets client creation exception handling."""
        mock_boto_client.side_effect = Exception("AWS client creation failed")

        manager = OIDCCredentialManager("test-secret")

        with pytest.raises(Exception, match="AWS client creation failed"):
            manager._get_secrets_client()

    @patch("boto3.client")
    def test_verify_aws_authentication_success(self, mock_boto_client: Mock) -> None:
        """Test successful AWS authentication verification."""
        mock_sts_client = Mock()
        mock_sts_client.get_caller_identity.return_value = {
            "Account": "123456789012",
            "Arn": "arn:aws:sts::123456789012:assumed-role/test-role/test-session",
            "UserId": "AIDACKCEVSQ6C2EXAMPLE",
        }
        mock_boto_client.return_value = mock_sts_client

        manager = OIDCCredentialManager("test-secret")
        result = manager.verify_aws_authentication()

        assert result["account"] == "123456789012"
        assert result["authenticated"] is True
        assert "test-role" in result["arn"]

    @patch("boto3.client")
    def test_verify_aws_authentication_no_credentials(self, mock_boto_client: Mock) -> None:
        """Test AWS authentication verification with no credentials."""
        mock_sts_client = Mock()
        mock_sts_client.get_caller_identity.side_effect = NoCredentialsError()
        mock_boto_client.return_value = mock_sts_client

        manager = OIDCCredentialManager("test-secret")

        with pytest.raises(Exception, match="AWS OIDC authentication failed: No credentials"):
            manager.verify_aws_authentication()

    @patch("boto3.client")
    def test_verify_aws_authentication_client_error(self, mock_boto_client: Mock) -> None:
        """Test AWS authentication verification with client error."""
        mock_sts_client = Mock()
        mock_sts_client.get_caller_identity.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "GetCallerIdentity"
        )
        mock_boto_client.return_value = mock_sts_client

        manager = OIDCCredentialManager("test-secret")

        with pytest.raises(Exception, match="AWS OIDC authentication failed"):
            manager.verify_aws_authentication()

    def test_test_secrets_access_success(self) -> None:
        """Test successful secrets access."""
        mock_client = Mock()
        mock_client.describe_secret.return_value = {"Name": "test-secret"}

        manager = OIDCCredentialManager("test-secret")
        manager.secrets_client = mock_client

        result = manager.test_secrets_access()

        assert result is True
        mock_client.describe_secret.assert_called_once_with(SecretId="test-secret")

    def test_test_secrets_access_not_found(self) -> None:
        """Test secrets access with secret not found."""
        mock_client = Mock()
        mock_client.describe_secret.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Secret not found"}},
            "DescribeSecret",
        )

        manager = OIDCCredentialManager("test-secret")
        manager.secrets_client = mock_client

        result = manager.test_secrets_access()

        assert result is False

    def test_test_secrets_access_denied(self) -> None:
        """Test secrets access with access denied."""
        mock_client = Mock()
        mock_client.describe_secret.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "DescribeSecret"
        )

        manager = OIDCCredentialManager("test-secret")
        manager.secrets_client = mock_client

        result = manager.test_secrets_access()

        assert result is False

    def test_test_secrets_access_unexpected_error(self) -> None:
        """Test secrets access with unexpected error."""
        mock_client = Mock()
        mock_client.describe_secret.side_effect = Exception("Unexpected error")

        manager = OIDCCredentialManager("test-secret")
        manager.secrets_client = mock_client

        result = manager.test_secrets_access()

        assert result is False

    def test_retrieve_pypi_token_success(self) -> None:
        """Test successful PyPI token retrieval."""
        mock_client = Mock()
        secret_data = {
            "token": (
                "pypi-AgEIcHlwaS5vcmcCJRVOaXMxLjAyAAABhGlkAAABhGh0dHBzOi8vcHlwaS5vcmcvbGVnYWN5Lw"
            ),
            "repository": "https://upload.pypi.org/legacy/",
            "package": "mypylogger",
        }
        mock_client.get_secret_value.return_value = {
            "SecretString": json.dumps(secret_data),
            "CreatedDate": "2025-01-21T10:30:00Z",
            "VersionId": "v1",
        }

        manager = OIDCCredentialManager("test-secret")
        manager.secrets_client = mock_client

        result = manager.retrieve_pypi_token()

        assert result["token"] == secret_data["token"]
        assert result["repository"] == secret_data["repository"]
        assert result["package"] == secret_data["package"]
        assert result["retrieved_at"] == "2025-01-21T10:30:00Z"

    def test_retrieve_pypi_token_missing_fields(self) -> None:
        """Test PyPI token retrieval with missing required fields."""
        mock_client = Mock()
        secret_data = {
            "token": "pypi-test-token"
            # Missing 'repository' and 'package'
        }
        mock_client.get_secret_value.return_value = {"SecretString": json.dumps(secret_data)}

        manager = OIDCCredentialManager("test-secret")
        manager.secrets_client = mock_client

        with pytest.raises(Exception, match="Missing required fields in secret"):
            manager.retrieve_pypi_token()

    def test_retrieve_pypi_token_invalid_format(self) -> None:
        """Test PyPI token retrieval with invalid token format."""
        mock_client = Mock()
        secret_data = {
            "token": "invalid-token-format",
            "repository": "https://upload.pypi.org/legacy/",
            "package": "mypylogger",
        }
        mock_client.get_secret_value.return_value = {"SecretString": json.dumps(secret_data)}

        manager = OIDCCredentialManager("test-secret")
        manager.secrets_client = mock_client

        with pytest.raises(Exception, match="Invalid PyPI token format"):
            manager.retrieve_pypi_token()

    def test_retrieve_pypi_token_secret_not_found(self) -> None:
        """Test PyPI token retrieval with secret not found."""
        mock_client = Mock()
        mock_client.get_secret_value.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Secret not found"}},
            "GetSecretValue",
        )

        manager = OIDCCredentialManager("test-secret")
        manager.secrets_client = mock_client

        with pytest.raises(Exception, match="PyPI token secret not found"):
            manager.retrieve_pypi_token()

    def test_retrieve_pypi_token_access_denied(self) -> None:
        """Test PyPI token retrieval with access denied."""
        mock_client = Mock()
        mock_client.get_secret_value.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "GetSecretValue"
        )

        manager = OIDCCredentialManager("test-secret")
        manager.secrets_client = mock_client

        with pytest.raises(Exception, match="Access denied to PyPI token secret"):
            manager.retrieve_pypi_token()

    def test_retrieve_pypi_token_decryption_failure(self) -> None:
        """Test PyPI token retrieval with decryption failure."""
        mock_client = Mock()
        mock_client.get_secret_value.side_effect = ClientError(
            {"Error": {"Code": "DecryptionFailure", "Message": "Decryption failed"}},
            "GetSecretValue",
        )

        manager = OIDCCredentialManager("test-secret")
        manager.secrets_client = mock_client

        with pytest.raises(Exception, match="Failed to decrypt PyPI token secret"):
            manager.retrieve_pypi_token()

    def test_retrieve_pypi_token_invalid_json(self) -> None:
        """Test PyPI token retrieval with invalid JSON."""
        mock_client = Mock()
        mock_client.get_secret_value.return_value = {"SecretString": "invalid-json-content"}

        manager = OIDCCredentialManager("test-secret")
        manager.secrets_client = mock_client

        with pytest.raises(Exception, match="Invalid JSON in PyPI token secret"):
            manager.retrieve_pypi_token()

    @patch("requests.get")
    def test_validate_token_permissions_success(self, mock_requests: Mock) -> None:
        """Test successful token permission validation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests.return_value = mock_response

        manager = OIDCCredentialManager("test-secret")
        result = manager.validate_token_permissions("pypi-test-token")

        assert result is True
        mock_requests.assert_called_once()

    @patch("requests.get")
    def test_validate_token_permissions_invalid_token(self, mock_requests: Mock) -> None:
        """Test token permission validation with invalid token."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_requests.return_value = mock_response

        manager = OIDCCredentialManager("test-secret")
        result = manager.validate_token_permissions("pypi-invalid-token")

        assert result is False

    @patch("requests.get")
    def test_validate_token_permissions_other_status(self, mock_requests: Mock) -> None:
        """Test token permission validation with other status code."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_requests.return_value = mock_response

        manager = OIDCCredentialManager("test-secret")
        result = manager.validate_token_permissions("pypi-test-token")

        assert result is False

    def test_validate_token_permissions_no_requests(self) -> None:
        """Test token permission validation without requests library."""
        manager = OIDCCredentialManager("test-secret")

        # Mock ImportError for requests
        with patch("builtins.__import__", side_effect=ImportError("No module named 'requests'")):
            result = manager.validate_token_permissions("pypi-test-token")

        assert result is True  # Should assume valid if can't test

    @patch("requests.get")
    def test_validate_token_permissions_exception(self, mock_requests: Mock) -> None:
        """Test token permission validation with exception."""
        mock_requests.side_effect = Exception("Network error")

        manager = OIDCCredentialManager("test-secret")
        result = manager.validate_token_permissions("pypi-test-token")

        assert result is False

    def test_get_credential_summary_all_success(self) -> None:
        """Test credential summary with all operations successful."""
        manager = OIDCCredentialManager("test-secret")

        # Mock all methods to succeed
        with patch.object(manager, "verify_aws_authentication") as mock_auth, patch.object(
            manager, "test_secrets_access"
        ) as mock_secrets, patch.object(manager, "retrieve_pypi_token") as mock_token, patch.object(
            manager, "validate_token_permissions"
        ) as mock_validate:
            mock_auth.return_value = {"account": "123456789012", "arn": "test-arn"}
            mock_secrets.return_value = True
            mock_token.return_value = {
                "token": "pypi-test-token",
                "package": "mypylogger",
                "repository": "https://upload.pypi.org/legacy/",
            }
            mock_validate.return_value = True

            summary = manager.get_credential_summary()

            assert summary["aws_authenticated"] is True
            assert summary["secrets_access"] is True
            assert summary["token_retrieved"] is True
            assert summary["token_valid"] is True
            assert len(summary["errors"]) == 0

    def test_get_credential_summary_with_errors(self) -> None:
        """Test credential summary with various errors."""
        manager = OIDCCredentialManager("test-secret")

        # Mock methods to fail
        with patch.object(manager, "verify_aws_authentication") as mock_auth, patch.object(
            manager, "test_secrets_access"
        ) as mock_secrets:
            mock_auth.side_effect = Exception("Auth failed")
            mock_secrets.return_value = False

            summary = manager.get_credential_summary()

            assert summary["aws_authenticated"] is False
            assert summary["secrets_access"] is False
            assert summary["token_retrieved"] is False
            assert summary["token_valid"] is False
            assert len(summary["errors"]) > 0
            assert any("Auth failed" in error for error in summary["errors"])


class TestOIDCCredentialManagerSecurity:
    """Security-focused tests for OIDC credential manager."""

    def test_credential_exposure_prevention(self) -> None:
        """Test that credentials are not exposed in logs or outputs."""
        mock_client = Mock()
        secret_data = {
            "token": (
                "pypi-AgEIcHlwaS5vcmcCJRVOaXMxLjAyAAABhGlkAAABhGh0dHBzOi8vcHlwaS5vcmcvbGVnYWN5Lw"
            ),
            "repository": "https://upload.pypi.org/legacy/",
            "package": "mypylogger",
        }
        mock_client.get_secret_value.return_value = {"SecretString": json.dumps(secret_data)}

        manager = OIDCCredentialManager("test-secret")
        manager.secrets_client = mock_client

        # Capture log output
        with patch("logging.getLogger") as mock_logger:
            mock_log = Mock()
            mock_logger.return_value = mock_log

            result = manager.retrieve_pypi_token()

            # Verify token is returned but not logged
            assert result["token"] == secret_data["token"]

            # Check that no log calls contain the actual token
            for call in mock_log.info.call_args_list:
                log_message = str(call)
                assert secret_data["token"] not in log_message

    def test_token_format_validation_security(self) -> None:
        """Test that token format validation prevents injection attacks."""
        manager = OIDCCredentialManager("test-secret")
        mock_client = Mock()

        # Test various malicious token formats
        malicious_tokens = [
            "",  # Empty token
            "not-a-pypi-token",  # Wrong format
            "pypi-",  # Too short
            "pypi-" + "A" * 10,  # Too short
            "pypi-" + "; rm -rf /",  # Command injection attempt
            "pypi-" + '<script>alert("xss")</script>',  # XSS attempt
        ]

        for _i, malicious_token in enumerate(malicious_tokens):
            secret_data = {
                "token": malicious_token,
                "repository": "https://upload.pypi.org/legacy/",
                "package": "mypylogger",
            }
            mock_client.get_secret_value.return_value = {"SecretString": json.dumps(secret_data)}
            manager.secrets_client = mock_client

            with pytest.raises(Exception, match="Invalid PyPI token format"):
                manager.retrieve_pypi_token()

    def test_aws_region_validation(self) -> None:
        """Test AWS region validation for security."""
        # Test with various region formats
        valid_regions = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]

        for region in valid_regions:
            manager = OIDCCredentialManager("test-secret", region)
            assert manager.aws_region == region

    def test_secret_name_validation(self) -> None:
        """Test secret name validation for security."""
        # Test with various secret name formats
        valid_names = ["mypylogger/pypi-token", "test-secret", "my_secret_123", "prod/app/token"]

        for name in valid_names:
            manager = OIDCCredentialManager(name)
            assert manager.secret_name == name

    @patch("boto3.client")
    def test_client_error_handling_security(self, mock_boto_client: Mock) -> None:
        """Test that client errors don't expose sensitive information."""
        mock_client = Mock()
        mock_client.get_secret_value.side_effect = ClientError(
            {
                "Error": {
                    "Code": "AccessDenied",
                    "Message": (
                        "User: arn:aws:sts::123456789012:assumed-role/test-role/test-session "
                        "is not authorized to perform: secretsmanager:GetSecretValue on "
                        "resource: arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret"
                    ),
                }
            },
            "GetSecretValue",
        )
        mock_boto_client.return_value = mock_client

        manager = OIDCCredentialManager("test-secret")

        with pytest.raises(Exception, match="Access denied") as exc_info:
            manager.retrieve_pypi_token()

        # Verify that the exception message doesn't expose the full ARN
        error_message = str(exc_info.value)
        assert "Access denied to PyPI token secret" in error_message
        # The specific ARN details should not be in the error message
        assert "123456789012" not in error_message

    def test_timeout_and_retry_security(self) -> None:
        """Test that timeouts and retries don't create security vulnerabilities."""
        manager = OIDCCredentialManager("test-secret")

        # Mock a client that times out
        mock_client = Mock()
        mock_client.get_secret_value.side_effect = Exception("Request timed out")
        manager.secrets_client = mock_client

        # Verify that timeout doesn't expose credentials
        with pytest.raises(Exception, match="Unexpected error retrieving PyPI token"):
            manager.retrieve_pypi_token()

    @patch("requests.get")
    def test_token_validation_security(self, mock_requests: Mock) -> None:
        """Test that token validation doesn't expose tokens in requests."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests.return_value = mock_response

        manager = OIDCCredentialManager("test-secret")
        test_token = "pypi-test-token-should-not-be-logged"  # noqa: S105

        manager.validate_token_permissions(test_token)

        # Verify the token is used in headers but not logged
        call_args = mock_requests.call_args
        headers = call_args[1]["headers"]
        assert f"token {test_token}" in headers["Authorization"]

        # Verify timeout is set for security
        assert call_args[1]["timeout"] == 10
