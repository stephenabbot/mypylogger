"""Integration tests for OIDC authentication workflow."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from typing import Any
from unittest.mock import Mock, patch

import pytest

# Add scripts directory to path for imports
scripts_path = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_path))

# Import after path modification
# ruff: noqa: E402
from credential_security_validator import CredentialSecurityValidator
from oidc_credential_manager import OIDCCredentialManager


class TestOIDCAuthenticationIntegration:
    """Integration tests for OIDC authentication workflow."""

    @patch("boto3.client")
    def test_complete_oidc_workflow_success(self, mock_boto_client: Mock) -> None:
        """Test complete OIDC authentication workflow."""
        # Mock AWS STS client
        mock_sts_client = Mock()
        mock_sts_client.get_caller_identity.return_value = {
            "Account": "123456789012",
            "Arn": "arn:aws:sts::123456789012:assumed-role/GitHubActions-Role/GitHubActions",
            "UserId": "AIDACKCEVSQ6C2EXAMPLE",
        }

        # Mock Secrets Manager client
        mock_secrets_client = Mock()
        secret_data = {
            "token": (
                "pypi-AgEIcHlwaS5vcmcCJRVOaXMxLjAyAAABhGlkAAABhGh0dHBzOi8vcHlwaS5vcmcvbGVnYWN5Lw"
            ),
            "repository": "https://upload.pypi.org/legacy/",
            "package": "mypylogger",
        }
        mock_secrets_client.get_secret_value.return_value = {
            "SecretString": json.dumps(secret_data),
            "CreatedDate": "2025-01-21T10:30:00Z",
            "VersionId": "v1",
        }
        mock_secrets_client.describe_secret.return_value = {"Name": "test-secret"}

        # Configure boto3.client to return appropriate clients
        def client_side_effect(service_name: str, **_kwargs: dict[str, Any]) -> Mock:
            if service_name == "sts":
                return mock_sts_client
            if service_name == "secretsmanager":
                return mock_secrets_client
            return Mock()

        mock_boto_client.side_effect = client_side_effect

        # Test the complete workflow
        manager = OIDCCredentialManager("test-secret", "us-east-1")

        # Step 1: Verify AWS authentication
        auth_result = manager.verify_aws_authentication()
        assert auth_result["authenticated"] is True
        assert auth_result["account"] == "123456789012"

        # Step 2: Test secrets access
        secrets_access = manager.test_secrets_access()
        assert secrets_access is True

        # Step 3: Retrieve PyPI token
        token_data = manager.retrieve_pypi_token()
        assert token_data["token"] == secret_data["token"]
        assert token_data["package"] == secret_data["package"]

        # Step 4: Get comprehensive summary
        summary = manager.get_credential_summary()
        assert summary["aws_authenticated"] is True
        assert summary["secrets_access"] is True
        assert summary["token_retrieved"] is True
        assert len(summary["errors"]) == 0

    @patch("boto3.client")
    def test_oidc_workflow_authentication_failure(self, mock_boto_client: Mock) -> None:
        """Test OIDC workflow with authentication failure."""
        # Mock STS client to fail authentication
        mock_sts_client = Mock()
        mock_sts_client.get_caller_identity.side_effect = Exception("Authentication failed")
        mock_boto_client.return_value = mock_sts_client

        manager = OIDCCredentialManager("test-secret")

        # Should fail at authentication step
        with pytest.raises(Exception, match="Authentication failed"):
            manager.verify_aws_authentication()

        # Summary should reflect the failure
        summary = manager.get_credential_summary()
        assert summary["aws_authenticated"] is False
        assert len(summary["errors"]) > 0

    @patch("boto3.client")
    def test_oidc_workflow_secrets_access_failure(self, mock_boto_client: Mock) -> None:
        """Test OIDC workflow with secrets access failure."""
        # Mock successful STS but failed Secrets Manager
        mock_sts_client = Mock()
        mock_sts_client.get_caller_identity.return_value = {
            "Account": "123456789012",
            "Arn": "arn:aws:sts::123456789012:assumed-role/test-role/test-session",
            "UserId": "AIDACKCEVSQ6C2EXAMPLE",
        }

        mock_secrets_client = Mock()
        mock_secrets_client.describe_secret.side_effect = Exception("Access denied")

        def client_side_effect(service_name: str, **_kwargs: dict[str, Any]) -> Mock:
            if service_name == "sts":
                return mock_sts_client
            if service_name == "secretsmanager":
                return mock_secrets_client
            return Mock()

        mock_boto_client.side_effect = client_side_effect

        manager = OIDCCredentialManager("test-secret")

        # Authentication should succeed
        auth_result = manager.verify_aws_authentication()
        assert auth_result["authenticated"] is True

        # Secrets access should fail
        secrets_access = manager.test_secrets_access()
        assert secrets_access is False

        # Summary should reflect partial success
        summary = manager.get_credential_summary()
        assert summary["aws_authenticated"] is True
        assert summary["secrets_access"] is False
        assert summary["token_retrieved"] is False

    @patch("requests.get")
    @patch("boto3.client")
    def test_oidc_workflow_with_token_validation(
        self, mock_boto_client: Mock, mock_requests: Mock
    ) -> None:
        """Test OIDC workflow with token validation."""
        # Mock successful AWS clients
        mock_sts_client = Mock()
        mock_sts_client.get_caller_identity.return_value = {
            "Account": "123456789012",
            "Arn": "arn:aws:sts::123456789012:assumed-role/test-role/test-session",
            "UserId": "AIDACKCEVSQ6C2EXAMPLE",
        }

        mock_secrets_client = Mock()
        secret_data = {
            "token": (
                "pypi-AgEIcHlwaS5vcmcCJRVOaXMxLjAyAAABhGlkAAABhGh0dHBzOi8vcHlwaS5vcmcvbGVnYWN5Lw"
            ),
            "repository": "https://upload.pypi.org/legacy/",
            "package": "mypylogger",
        }
        mock_secrets_client.get_secret_value.return_value = {
            "SecretString": json.dumps(secret_data)
        }
        mock_secrets_client.describe_secret.return_value = {"Name": "test-secret"}

        def client_side_effect(service_name: str, **_kwargs: dict[str, Any]) -> Mock:
            if service_name == "sts":
                return mock_sts_client
            if service_name == "secretsmanager":
                return mock_secrets_client
            return Mock()

        mock_boto_client.side_effect = client_side_effect

        # Mock successful token validation
        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests.return_value = mock_response

        manager = OIDCCredentialManager("test-secret")

        # Complete workflow with validation
        token_data = manager.retrieve_pypi_token()
        is_valid = manager.validate_token_permissions(token_data["token"])

        assert is_valid is True

        # Verify token validation request
        mock_requests.assert_called_once()
        call_args = mock_requests.call_args
        assert "Authorization" in call_args[1]["headers"]
        assert f"token {token_data['token']}" in call_args[1]["headers"]["Authorization"]

    def test_security_validation_integration(self) -> None:
        """Test integration with security validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            # Create a mock workflow file with proper OIDC usage
            workflows_dir = workspace / ".github" / "workflows"
            workflows_dir.mkdir(parents=True)

            workflow_content = """
name: PyPI Publishing
on: workflow_dispatch
jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - name: Configure AWS OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ secrets.AWS_REGION }}
      - name: Retrieve PyPI token
        run: |
          aws secretsmanager get-secret-value --secret-id ${{ secrets.AWS_SECRET_NAME }}
"""

            workflow_file = workflows_dir / "pypi-publish.yml"
            workflow_file.write_text(workflow_content)

            # Run security validation
            validator = CredentialSecurityValidator(workspace)
            results = validator.run_comprehensive_scan()

            # Should not find any credential violations
            total_violations = sum(len(violations) for violations in results.values())
            assert total_violations == 0

    def test_security_validation_detects_violations(self) -> None:
        """Test that security validation detects OIDC-related violations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            # Create a workflow file with exposed credentials
            workflows_dir = workspace / ".github" / "workflows"
            workflows_dir.mkdir(parents=True)

            bad_workflow_content = """
name: Bad PyPI Publishing
on: workflow_dispatch
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - name: Bad step
        env:
          AWS_ROLE_ARN: arn:aws:iam::123456789012:role/bad-hardcoded-role
          PYPI_TOKEN: >-
            pypi-AgEIcHlwaS5vcmcCJRVOaXMxLjAyAAABhGlkAAABhGh0dHBzOi8vcHlwaS5vcmcvbGVnYWN5Lw
        run: echo "bad"
"""

            workflow_file = workflows_dir / "bad-workflow.yml"
            workflow_file.write_text(bad_workflow_content)

            # Run security validation
            validator = CredentialSecurityValidator(workspace)
            results = validator.run_comprehensive_scan()

            # Should find violations
            workflow_violations = results["workflow_files"]
            github_secrets_violations = results["github_secrets"]

            assert len(workflow_violations) > 0
            assert len(github_secrets_violations) > 0

            # Should detect the PyPI token
            pypi_violations = [v for v in workflow_violations if "pypi-" in v["matched_text"]]
            assert len(pypi_violations) > 0

    @patch.dict(
        os.environ,
        {
            "AWS_ROLE_ARN": "arn:aws:iam::123456789012:role/test-role",
            "AWS_SECRET_NAME": "test-secret",
            "AWS_REGION": "us-east-1",
        },
    )
    def test_environment_variable_security_validation(self) -> None:
        """Test security validation of environment variables."""
        validator = CredentialSecurityValidator()

        # These should be safe (ARN and region are not sensitive)
        violations = validator.validate_environment_variables()

        # Should not flag AWS_ROLE_ARN, AWS_SECRET_NAME, or AWS_REGION as violations
        # since they don't contain actual credentials
        assert len(violations) == 0

    @patch.dict(
        os.environ,
        {
            "PYPI_API_TOKEN": (
                "pypi-AgEIcHlwaS5vcmcCJRVOaXMxLjAyAAABhGlkAAABhGh0dHBzOi8vcHlwaS5vcmcvbGVnYWN5Lw"
            ),
            "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
        },
    )
    def test_environment_variable_credential_detection(self) -> None:
        """Test detection of actual credentials in environment variables."""
        validator = CredentialSecurityValidator()

        violations = validator.validate_environment_variables()

        # Should flag actual credentials
        assert len(violations) >= 2

        # Check for PyPI token violation
        pypi_violations = [v for v in violations if v["variable"] == "PYPI_API_TOKEN"]
        assert len(pypi_violations) == 1
        assert pypi_violations[0]["severity"] == "HIGH"

        # Check for AWS key violation
        aws_violations = [v for v in violations if v["variable"] == "AWS_ACCESS_KEY_ID"]
        assert len(aws_violations) == 1
        assert aws_violations[0]["severity"] == "HIGH"

    def test_end_to_end_security_report_generation(self) -> None:
        """Test end-to-end security report generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            # Create various files with different security issues
            scripts_dir = workspace / "scripts"
            scripts_dir.mkdir()

            # Script with credential
            script_content = """#!/usr/bin/env python3
import os

# This is bad - hardcoded token
PYPI_TOKEN = (
    "pypi-AgEIcHlwaS5vcmcCJRVOaXMxLjAyAAABhGlkAAABhGh0dHBzOi8vcHlwaS5vcmcvbGVnYWN5Lw"
)

def publish():
    # This is good - using environment variable
    token = os.environ.get("PYPI_API_TOKEN", "***")
    print(f"Using token: {token}")
"""

            script_file = scripts_dir / "bad_script.py"
            script_file.write_text(script_content)

            # Workflow with mixed good and bad practices
            workflows_dir = workspace / ".github" / "workflows"
            workflows_dir.mkdir(parents=True)

            workflow_content = """
name: Mixed Workflow
jobs:
  good:
    steps:
      - name: Good step
        env:
          TOKEN: ${{ secrets.PYPI_API_TOKEN }}
        run: echo "good"
  bad:
    steps:
      - name: Bad step
        env:
          HARDCODED_TOKEN: pypi-another-bad-token-here
        run: echo "bad"
"""

            workflow_file = workflows_dir / "mixed.yml"
            workflow_file.write_text(workflow_content)

            # Run comprehensive scan
            validator = CredentialSecurityValidator(workspace)
            results = validator.run_comprehensive_scan()

            # Generate report
            report = validator.generate_security_report(results)

            # Verify report content
            assert "# Credential Security Scan Report" in report
            assert "ISSUES FOUND" in report
            assert "Script Files" in report
            assert "Workflow Files" in report
            assert "## Recommendations" in report

            # Should find violations in both scripts and workflows
            assert len(results["script_files"]) > 0
            assert len(results["workflow_files"]) > 0

    def test_credential_masking_in_logs(self) -> None:
        """Test that credentials are properly masked in log outputs."""
        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            # Mock successful token retrieval
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

            # Retrieve token
            token_data = manager.retrieve_pypi_token()

            # Verify token is returned
            assert token_data["token"] == secret_data["token"]

            # Verify no log messages contain the actual token
            all_log_calls = (
                mock_logger.info.call_args_list
                + mock_logger.warning.call_args_list
                + mock_logger.error.call_args_list
                + mock_logger.debug.call_args_list
            )

            for call in all_log_calls:
                log_message = str(call)
                assert secret_data["token"] not in log_message, f"Token found in log: {log_message}"

    def test_oidc_workflow_error_handling(self) -> None:
        """Test error handling in OIDC workflow."""
        manager = OIDCCredentialManager("test-secret")

        # Test with no AWS credentials configured
        with patch("boto3.client") as mock_boto_client:
            mock_boto_client.side_effect = Exception("No credentials configured")

            # Should handle gracefully
            summary = manager.get_credential_summary()

            assert summary["aws_authenticated"] is False
            assert len(summary["errors"]) > 0
            assert any("No credentials configured" in error for error in summary["errors"])

    def test_concurrent_oidc_operations(self) -> None:
        """Test concurrent OIDC operations for thread safety."""
        manager = OIDCCredentialManager("test-secret")
        results = []
        errors = []

        def worker() -> None:
            try:
                # Simulate concurrent access
                time.sleep(0.01)  # Small delay to increase chance of race conditions
                summary = manager.get_credential_summary()
                results.append(summary)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should not have any thread safety issues
        assert len(errors) == 0
        assert len(results) == 5

        # All results should have consistent structure
        for result in results:
            assert "aws_authenticated" in result
            assert "secrets_access" in result
            assert "token_retrieved" in result
            assert "errors" in result
