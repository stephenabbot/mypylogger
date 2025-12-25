"""Unit tests for security and performance validator."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from unittest.mock import Mock, mock_open, patch

import pytest

from scripts.security_performance_validator import (
    PerformanceValidator,
    SecurityPerformanceValidator,
    SecurityValidator,
)


class TestSecurityValidator:
    """Test SecurityValidator class."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.validator = SecurityValidator()

    def test_validate_trusted_publishing_configuration_success(self) -> None:
        """Test successful trusted publishing configuration validation."""
        # The test should pass with the existing pypi-publish.yml workflow
        from pathlib import Path

        # Find the project root directory (where pyproject.toml is located)
        project_root = Path(__file__).parent.parent.parent
        workflow_path = project_root / ".github/workflows/pypi-publish.yml"

        # Ensure the workflow file exists
        assert workflow_path.exists(), f"Workflow file not found at: {workflow_path}"

        # Temporarily change to project root for the test
        import os

        original_cwd = None
        try:
            original_cwd = Path.cwd()
        except (OSError, FileNotFoundError):
            # If we can't get the current directory, that's fine
            pass

        try:
            os.chdir(project_root)
            result = self.validator.validate_trusted_publishing_configuration()
        finally:
            # Restore original directory if we had one
            if original_cwd and original_cwd.exists():
                try:
                    os.chdir(original_cwd)
                except (OSError, FileNotFoundError):
                    # If we can't restore, that's fine
                    pass

        assert result.passed is True, f"Test failed: {result.message}. Details: {result.details}"
        assert result.test_name == "Trusted Publishing Configuration"
        assert "valid" in result.message
        assert result.details is not None
        assert result.execution_time is not None

    def test_validate_trusted_publishing_configuration_missing_workflow(self) -> None:
        """Test trusted publishing configuration validation with missing workflow."""
        # Mock Path.exists to return False for workflow file
        with patch("pathlib.Path.exists", return_value=False):
            result = self.validator.validate_trusted_publishing_configuration()

            assert result.passed is False
            assert "PyPI publishing workflow not found" in result.message

    def test_validate_trusted_publishing_configuration_invalid_permissions(self) -> None:
        """Test trusted publishing configuration validation with invalid permissions."""
        # Create a temporary workflow with invalid permissions
        temp_workflow = """
name: Test Workflow
jobs:
  publish-to-pypi:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: pypa/gh-action-pypi-publish@release/v1
"""

        with patch("builtins.open", mock_open(read_data=temp_workflow)):
            with patch("pathlib.Path.exists", return_value=True):
                result = self.validator.validate_trusted_publishing_configuration()

                assert result.passed is False
                assert "Missing required OIDC permissions" in result.message

    def test_validate_credential_security_success(self) -> None:
        """Test successful credential security validation."""
        # Create temporary workflow files without hardcoded secrets
        temp_dir = Path(tempfile.mkdtemp())
        workflows_dir = temp_dir / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)

        workflow_content = """
name: Test Workflow
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Test
        run: echo "No secrets here"
        env:
          TOKEN: ${{ secrets.PYPI_TOKEN }}
"""

        (workflows_dir / "test.yml").write_text(workflow_content)

        with patch("pathlib.Path.cwd", return_value=temp_dir):
            result = self.validator.validate_credential_security()

            assert result.passed is True
            assert result.test_name == "Credential Security"

        # Clean up
        import shutil

        shutil.rmtree(temp_dir)

    def test_validate_publishing_authorization_success(self) -> None:
        """Test successful publishing authorization validation."""
        # Create temporary workflow file with proper permissions
        temp_dir = Path(tempfile.mkdtemp())
        workflows_dir = temp_dir / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)

        workflow_content = """
name: PyPI Publish
on: workflow_dispatch
permissions:
  id-token: write
  contents: read
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
"""

        (workflows_dir / "pypi-publish.yml").write_text(workflow_content)

        # Mock the glob method to return our test file
        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.return_value = [workflows_dir / "pypi-publish.yml"]
            result = self.validator.validate_publishing_authorization()

            assert result.passed is True
            assert result.test_name == "Publishing Authorization"

        # Clean up
        import shutil

        shutil.rmtree(temp_dir)

    def test_run_all_security_validations(self) -> None:
        """Test running all security validations."""
        with patch.dict(
            os.environ,
            {
                "AWS_ROLE_ARN": "arn:aws:iam::123456789012:role/GitHubActionsRole",
                "AWS_REGION": "us-east-1",
                "AWS_SECRET_NAME": "pypi-token-secret",
            },
        ):
            results = self.validator.run_all_security_validations()

            assert len(results) == 3
            assert all(isinstance(result.passed, bool) for result in results)
            assert all(result.test_name for result in results)


class TestPerformanceValidator:
    """Test PerformanceValidator class."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.validator = PerformanceValidator()

    @patch("requests.get")
    @patch("scripts.security_performance_validator.is_ci_environment")
    def test_validate_api_response_time_success(self, mock_is_ci: Mock, mock_get: Mock) -> None:
        """Test successful API response time validation."""
        # Mock non-CI environment to get original target time
        mock_is_ci.return_value = False

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = self.validator.validate_api_response_time("https://example.com/api", 0.5)

        assert result.test_name.startswith("API Response Time")
        assert result.target_time == 0.5
        assert result.actual_time >= 0
        # Should pass since we're not actually making real requests
        assert mock_get.call_count == 5  # Should make 5 test requests

    @patch("requests.get")
    def test_validate_api_response_time_failure(self, mock_get: Mock) -> None:
        """Test API response time validation with failure."""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = self.validator.validate_api_response_time("https://example.com/api", 0.2)

        assert result.passed is False
        assert "status code 404" in result.message

    def test_validate_workflow_execution_time_no_metrics(self) -> None:
        """Test workflow execution time validation with no metrics."""
        result = self.validator.validate_workflow_execution_time("test-workflow", 300.0)

        assert result.passed is False
        assert result.test_name.startswith("Workflow Execution Time")
        assert (
            "No metrics directory found" in result.message
            or "No metrics found" in result.message
            or "No such file or directory" in result.message
        )

    @patch("scripts.security_performance_validator.is_ci_environment")
    def test_validate_workflow_execution_time_with_metrics(self, mock_is_ci: Mock) -> None:
        """Test workflow execution time validation with sample metrics."""
        # Mock non-CI environment to get original target time
        mock_is_ci.return_value = False

        # Create temporary metrics directory
        temp_dir = Path(tempfile.mkdtemp())
        metrics_dir = temp_dir / "metrics"
        metrics_dir.mkdir()

        # Create sample metrics files
        sample_metrics = [
            {"duration_seconds": 120.0, "status": "success"},
            {"duration_seconds": 150.0, "status": "success"},
            {"duration_seconds": 180.0, "status": "success"},
        ]

        for i, metrics in enumerate(sample_metrics):
            metrics_file = metrics_dir / f"workflow-test-workflow-{i}.json"
            with metrics_file.open("w") as f:
                json.dump(metrics, f)

        # Patch Path.cwd to return our temp directory
        with patch("pathlib.Path.cwd", return_value=temp_dir):
            result = self.validator.validate_workflow_execution_time("test-workflow", 300.0)

            assert result.passed is True
            assert result.actual_time == 150.0  # Average of 120, 150, 180
            assert result.target_time == 300.0

        # Clean up
        import shutil

        shutil.rmtree(temp_dir)

    @patch("scripts.security_performance_validator.is_ci_environment")
    def test_validate_status_api_performance_local_file(self, mock_is_ci: Mock) -> None:
        """Test status API performance validation with local file."""
        # Mock non-CI environment to get original target time
        mock_is_ci.return_value = False

        # Create temporary status file
        temp_dir = Path(tempfile.mkdtemp())
        status_dir = temp_dir / "docs" / "security-status"
        status_dir.mkdir(parents=True)

        status_data = {"status": "ok", "vulnerabilities": 0}
        status_file = status_dir / "index.json"
        with status_file.open("w") as f:
            json.dump(status_data, f)

        # Patch Path.cwd to return our temp directory
        with patch("pathlib.Path.cwd", return_value=temp_dir):
            result = self.validator.validate_status_api_performance()

            assert result.test_name == "Status API Performance (Local)"
            assert result.actual_time >= 0
            assert result.target_time == 0.01

        # Clean up
        import shutil

        shutil.rmtree(temp_dir)

    def test_run_all_performance_validations(self) -> None:
        """Test running all performance validations."""
        # Create a temporary directory for the test
        temp_dir = Path(tempfile.mkdtemp())

        with patch("pathlib.Path.cwd", return_value=temp_dir):
            results = self.validator.run_all_performance_validations()

            assert len(results) == 3
            assert all(isinstance(result.passed, bool) for result in results)
            assert all(result.test_name for result in results)
            assert all(result.target_time > 0 for result in results)

        # Clean up
        import shutil

        shutil.rmtree(temp_dir)


class TestSecurityPerformanceValidator:
    """Test SecurityPerformanceValidator class."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.validator = SecurityPerformanceValidator()

    @patch.object(SecurityValidator, "run_all_security_validations")
    @patch.object(PerformanceValidator, "run_all_performance_validations")
    def test_run_complete_validation(
        self,
        mock_perf_validations: Mock,
        mock_sec_validations: Mock,
    ) -> None:
        """Test running complete validation."""
        # Mock security results
        from scripts.security_performance_validator import SecurityValidationResult

        mock_sec_validations.return_value = [
            SecurityValidationResult(
                test_name="Test Security",
                passed=True,
                message="Security test passed",
                execution_time=0.1,
            )
        ]

        # Mock performance results
        from scripts.security_performance_validator import PerformanceValidationResult

        mock_perf_validations.return_value = [
            PerformanceValidationResult(
                test_name="Test Performance",
                passed=True,
                target_time=1.0,
                actual_time=0.5,
                message="Performance test passed",
            )
        ]

        results = self.validator.run_complete_validation()

        assert "timestamp" in results
        assert "overall_passed" in results
        assert "security" in results
        assert "performance" in results

        assert results["overall_passed"] is True
        assert results["security"]["passed"] is True
        assert results["performance"]["passed"] is True

        assert len(results["security"]["results"]) == 1
        assert len(results["performance"]["results"]) == 1

    def test_generate_validation_report(self) -> None:
        """Test generating validation report."""
        sample_results = {
            "timestamp": "2025-01-21T10:00:00Z",
            "overall_passed": True,
            "security": {
                "passed": True,
                "results": [
                    {
                        "test_name": "OIDC Configuration",
                        "passed": True,
                        "message": "Configuration is valid",
                        "execution_time": 0.1,
                        "details": None,
                    }
                ],
            },
            "performance": {
                "passed": True,
                "results": [
                    {
                        "test_name": "API Response Time",
                        "passed": True,
                        "target_time": 0.2,
                        "actual_time": 0.15,
                        "message": "Response time within target",
                        "details": None,
                    }
                ],
            },
        }

        report = self.validator.generate_validation_report(sample_results)

        assert "Security and Performance Validation Report" in report
        assert "2025-01-21T10:00:00Z" in report
        assert "PASSED" in report
        assert "OIDC Configuration" in report
        assert "API Response Time" in report
        assert "✅" in report  # Should have success icons


class TestValidatorCLI:
    """Test validator CLI functionality."""

    @patch("scripts.security_performance_validator.SecurityPerformanceValidator")
    def test_cli_validate_command(self, mock_validator_class: Mock) -> None:
        """Test CLI validate command."""
        mock_validator = Mock()
        mock_validator.run_complete_validation.return_value = {
            "overall_passed": True,
            "security": {"passed": True},
            "performance": {"passed": True},
        }
        mock_validator_class.return_value = mock_validator

        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["security_performance_validator.py", "validate"]):
            with patch("builtins.print"):
                with patch("builtins.open", create=True):
                    from scripts.security_performance_validator import main

                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 0  # Should exit with success

                    # Verify validation was run
                    mock_validator.run_complete_validation.assert_called_once()

    @patch("scripts.security_performance_validator.SecurityValidator")
    def test_cli_security_command(self, mock_validator_class: Mock) -> None:
        """Test CLI security command."""
        from scripts.security_performance_validator import SecurityValidationResult

        mock_validator = Mock()
        mock_validator.run_all_security_validations.return_value = [
            SecurityValidationResult(
                test_name="Test",
                passed=True,
                message="Test passed",
            )
        ]
        mock_validator_class.return_value = mock_validator

        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["security_performance_validator.py", "security"]):
            with patch("builtins.print"):
                from scripts.security_performance_validator import main

                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0  # Should exit with success
