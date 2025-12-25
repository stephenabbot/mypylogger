"""Unit tests for test environment standardization functionality."""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import Mock, patch

from tests.conftest import (
    get_performance_threshold,
    get_test_timeout,
    is_ci_environment,
)


class TestEnvironmentDetection:
    """Test CI environment detection functionality."""

    def test_ci_environment_detection_github_actions(self) -> None:
        """Test CI detection with GitHub Actions environment."""
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=True):
            assert is_ci_environment() is True

    def test_ci_environment_detection_generic_ci(self) -> None:
        """Test CI detection with generic CI environment."""
        with patch.dict(os.environ, {"CI": "true"}, clear=True):
            assert is_ci_environment() is True

    def test_ci_environment_detection_multiple_indicators(self) -> None:
        """Test CI detection with multiple CI indicators."""
        with patch.dict(
            os.environ,
            {"CI": "true", "GITHUB_ACTIONS": "true", "CONTINUOUS_INTEGRATION": "true"},
            clear=True,
        ):
            assert is_ci_environment() is True

    def test_ci_environment_detection_false_values(self) -> None:
        """Test CI detection with false values."""
        with patch.dict(os.environ, {"CI": "false", "GITHUB_ACTIONS": "0"}, clear=True):
            assert is_ci_environment() is False

    def test_local_environment_detection(self) -> None:
        """Test local environment detection (no CI indicators)."""
        # Clear all CI-related environment variables
        ci_vars = [
            "CI",
            "CONTINUOUS_INTEGRATION",
            "GITHUB_ACTIONS",
            "TRAVIS",
            "CIRCLECI",
            "JENKINS_URL",
            "BUILDKITE",
            "GITLAB_CI",
            "APPVEYOR",
            "TEAMCITY_VERSION",
        ]

        with patch.dict(os.environ, {}, clear=True):
            # Ensure no CI variables are set
            for var in ci_vars:
                os.environ.pop(var, None)

            assert is_ci_environment() is False

    def test_performance_threshold_adjustment_ci(self) -> None:
        """Test performance threshold adjustment for CI environment."""
        base_threshold = 10.0

        with patch.dict(os.environ, {"CI": "true"}, clear=True):
            adjusted_threshold = get_performance_threshold(base_threshold)
            expected_threshold = base_threshold * 2.0  # 100% increase for GitHub Actions
            assert adjusted_threshold == expected_threshold

    def test_performance_threshold_adjustment_local(self) -> None:
        """Test performance threshold adjustment for local environment."""
        base_threshold = 10.0

        with patch.dict(os.environ, {}, clear=True):
            adjusted_threshold = get_performance_threshold(base_threshold)
            assert adjusted_threshold == base_threshold  # No adjustment for local

    def test_timeout_adjustment_ci(self) -> None:
        """Test timeout adjustment for CI environment."""
        base_timeout = 30.0

        with patch.dict(os.environ, {"CI": "true"}, clear=True):
            adjusted_timeout = get_test_timeout(base_timeout)
            expected_timeout = base_timeout * 2.0  # Double timeout for CI
            assert adjusted_timeout == expected_timeout

    def test_timeout_adjustment_local(self) -> None:
        """Test timeout adjustment for local environment."""
        base_timeout = 30.0

        with patch.dict(os.environ, {}, clear=True):
            adjusted_timeout = get_test_timeout(base_timeout)
            assert adjusted_timeout == base_timeout  # No adjustment for local


class TestEnvironmentConfiguration:
    """Test environment-specific configuration functionality."""

    def test_test_environment_config_ci(self, test_environment_config: dict[str, Any]) -> None:
        """Test environment configuration in CI environment."""
        # This test will use the actual environment detection
        config = test_environment_config

        # Verify all required configuration keys are present
        required_keys = [
            "is_ci",
            "performance_multiplier",
            "timeout_multiplier",
            "max_execution_time",
            "api_timeout",
            "file_operation_timeout",
            "retry_attempts",
            "retry_delay",
        ]

        for key in required_keys:
            assert key in config

        # Verify configuration values are appropriate for environment
        if config["is_ci"]:
            assert config["performance_multiplier"] == 2.0  # GitHub Actions needs 100% more time
            assert config["timeout_multiplier"] == 2.5  # 150% more timeout for GitHub Actions
            assert config["max_execution_time"] == 600.0  # 10 minutes for CI
            assert config["retry_attempts"] == 5  # More retries for GitHub Actions
        else:
            assert config["performance_multiplier"] == 1.0
            assert config["timeout_multiplier"] == 1.0
            assert config["max_execution_time"] == 300.0  # 5 minutes for local
            assert config["retry_attempts"] == 2

    def test_repository_context_standardization(self, repository_context: None) -> None:
        """Test repository context standardization."""
        # Use the repository_context fixture to ensure it's active
        _ = repository_context

        # Verify repository context environment variables are set
        assert os.environ.get("GITHUB_REPOSITORY") == "stabbotco1/mypylogger"
        assert os.environ.get("GITHUB_REPOSITORY_OWNER") == "stabbotco1"
        assert os.environ.get("GITHUB_API_URL") == "https://api.github.com"
        assert os.environ.get("GITHUB_SERVER_URL") == "https://github.com"

        # Verify additional GitHub context variables
        assert os.environ.get("GITHUB_REF") == "refs/heads/main"
        assert os.environ.get("GITHUB_SHA") == "abc123def456"
        assert os.environ.get("GITHUB_WORKFLOW") == "test-workflow"
        assert os.environ.get("GITHUB_RUN_ID") == "123456789"
        assert os.environ.get("GITHUB_RUN_NUMBER") == "42"
        assert os.environ.get("GITHUB_ACTOR") == "test-actor"

    def test_standardized_test_environment_variables(
        self, standardized_test_environment: None
    ) -> None:
        """Test standardized test environment variables are set."""
        # Use the standardized_test_environment fixture to ensure it's active
        _ = standardized_test_environment

        # Verify test environment variables are set
        test_env = os.environ.get("TEST_ENVIRONMENT")
        assert test_env in ["ci", "local"]

        assert os.environ.get("TEST_REPOSITORY_CONTEXT") == "stabbotco1/mypylogger"

    def test_github_api_mock_functionality(
        self, mock_github_api: Mock, github_api_responses: dict[str, Any]
    ) -> None:
        """Test GitHub API mocking functionality."""
        # Verify mock is available and configured
        assert mock_github_api is not None

        # Verify response templates are available
        assert "issue_created" in github_api_responses
        assert "repository_info" in github_api_responses
        assert "unauthorized" in github_api_responses
        assert "not_found" in github_api_responses

        # Test configuring mock with response template
        issue_response = github_api_responses["issue_created"]
        mock_response = mock_github_api.return_value
        mock_response.status = issue_response["status"]

        # Verify mock configuration
        assert mock_response.status == 201

    def test_environment_isolation_between_tests(self) -> None:
        """Test that environment changes are isolated between tests."""
        # This test verifies that the fixtures properly clean up
        # environment variables between tests

        # Set a test-specific environment variable
        test_var = "TEST_ISOLATION_VAR"
        original_value = os.environ.get(test_var)

        try:
            os.environ[test_var] = "test_value"
            assert os.environ.get(test_var) == "test_value"
        finally:
            # Clean up
            if original_value is not None:
                os.environ[test_var] = original_value
            else:
                os.environ.pop(test_var, None)


class TestPerformanceThresholdCalculation:
    """Test performance threshold calculation with different scenarios."""

    def test_threshold_calculation_with_various_base_values(self) -> None:
        """Test threshold calculation with various base values."""
        test_cases = [
            (
                1.0,
                1.0,
                2.0,
            ),  # (base, local_expected, ci_expected) - GitHub Actions needs 100% more time
            (5.0, 5.0, 10.0),
            (10.0, 10.0, 20.0),
            (30.0, 30.0, 60.0),
            (60.0, 60.0, 120.0),
        ]

        for base_threshold, local_expected, ci_expected in test_cases:
            # Test local environment
            with patch.dict(os.environ, {}, clear=True):
                local_result = get_performance_threshold(base_threshold)
                assert local_result == local_expected

            # Test CI environment
            with patch.dict(os.environ, {"CI": "true"}, clear=True):
                ci_result = get_performance_threshold(base_threshold)
                assert ci_result == ci_expected

    def test_timeout_calculation_with_various_base_values(self) -> None:
        """Test timeout calculation with various base values."""
        test_cases = [
            (10.0, 10.0, 20.0),  # (base, local_expected, ci_expected)
            (30.0, 30.0, 60.0),
            (60.0, 60.0, 120.0),
            (120.0, 120.0, 240.0),
        ]

        for base_timeout, local_expected, ci_expected in test_cases:
            # Test local environment
            with patch.dict(os.environ, {}, clear=True):
                local_result = get_test_timeout(base_timeout)
                assert local_result == local_expected

            # Test CI environment
            with patch.dict(os.environ, {"CI": "true"}, clear=True):
                ci_result = get_test_timeout(base_timeout)
                assert ci_result == ci_expected
