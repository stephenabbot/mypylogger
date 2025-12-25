"""Shared test fixtures and configuration for mypylogger tests."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
from typing import Any, Generator
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def clean_env() -> Generator[None, None, None]:
    """Clean environment variables before and after test."""
    # Store original environment
    original_env = dict(os.environ)

    # Clear mypylogger-related environment variables
    env_vars_to_clear = [
        "APP_NAME",
        "LOG_LEVEL",
        "LOG_TO_FILE",
        "LOG_FILE_DIR",
        "LOG_FILE_NAME",
        "LOG_IMMEDIATE_FLUSH",
    ]

    for var in env_vars_to_clear:
        os.environ.pop(var, None)

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def sample_log_data() -> dict[str, str]:
    """Sample log data for testing."""
    return {
        "message": "Test log message",
        "level": "INFO",
        "extra_field": "extra_value",
    }


@pytest.fixture
def repository_context() -> Generator[dict[str, str], None, None]:
    """Set up consistent repository context for tests.

    This fixture ensures all tests have consistent GitHub repository
    information available, which is critical for PyPI publishing
    integration tests and GitHub API interactions.
    """
    # Store original environment variables
    original_env = {}
    github_env_vars = [
        "GITHUB_REPOSITORY",
        "GITHUB_REPOSITORY_OWNER",
        "GITHUB_API_URL",
        "GITHUB_SERVER_URL",
        "GITHUB_REF",
        "GITHUB_SHA",
        "GITHUB_WORKFLOW",
        "GITHUB_RUN_ID",
        "GITHUB_RUN_NUMBER",
        "GITHUB_ACTOR",
    ]

    for var in github_env_vars:
        original_env[var] = os.environ.get(var)

    # Set consistent repository context for all tests
    os.environ["GITHUB_REPOSITORY"] = "stabbotco1/mypylogger"
    os.environ["GITHUB_REPOSITORY_OWNER"] = "stabbotco1"
    os.environ["GITHUB_API_URL"] = "https://api.github.com"
    os.environ["GITHUB_SERVER_URL"] = "https://github.com"
    os.environ["GITHUB_REF"] = "refs/heads/main"
    os.environ["GITHUB_SHA"] = "abc123def456"  # Mock commit SHA
    os.environ["GITHUB_WORKFLOW"] = "test-workflow"
    os.environ["GITHUB_RUN_ID"] = "123456789"
    os.environ["GITHUB_RUN_NUMBER"] = "42"
    os.environ["GITHUB_ACTOR"] = "test-actor"

    # Return repository context data
    context = {
        "owner": "stabbotco1",
        "name": "mypylogger",
        "full_name": "stabbotco1/mypylogger",
        "api_url": "https://api.github.com",
        "server_url": "https://github.com",
    }

    yield context

    # Restore original environment
    for var, original_value in original_env.items():
        if original_value is not None:
            os.environ[var] = original_value
        else:
            os.environ.pop(var, None)


def is_ci_environment() -> bool:
    """Detect if running in CI environment.

    Checks multiple CI environment indicators to reliably detect
    CI execution context for environment-specific test configuration.
    """
    ci_indicators = [
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
    return any(
        os.environ.get(indicator, "").lower() in ("true", "1", "yes") for indicator in ci_indicators
    )


def get_performance_threshold(base_threshold: float) -> float:
    """Get performance threshold adjusted for CI environment.

    CI environments typically have more variable performance due to
    shared resources, so we apply a multiplier to base thresholds.
    GitHub Actions specifically requires additional cushion due to
    shared runner resources and network variability.

    Args:
        base_threshold: Base performance threshold in seconds

    Returns:
        Adjusted threshold for current environment
    """
    if is_ci_environment():
        # GitHub Actions requires 30% cushion + additional CI overhead
        return base_threshold * 2.0  # 100% more time for GitHub Actions
    return base_threshold


def get_test_timeout(base_timeout: float) -> float:
    """Get test timeout adjusted for CI environment.

    Args:
        base_timeout: Base timeout in seconds

    Returns:
        Adjusted timeout for current environment
    """
    if is_ci_environment():
        return base_timeout * 2.0  # Double timeout for CI
    return base_timeout


@pytest.fixture
def test_environment_config() -> dict[str, Any]:
    """Provide environment-specific test configuration.

    Returns configuration values adjusted for the current test environment
    (local development vs CI) to ensure reliable test execution.
    """
    is_ci = is_ci_environment()

    return {
        "is_ci": is_ci,
        "performance_multiplier": 2.0 if is_ci else 1.0,  # GitHub Actions needs 100% more time
        "timeout_multiplier": 2.5 if is_ci else 1.0,  # 150% more timeout for GitHub Actions
        "max_execution_time": 600.0 if is_ci else 300.0,  # 10 minutes for CI, 5 minutes local
        "api_timeout": 60.0 if is_ci else 30.0,  # Double API timeout for CI
        "file_operation_timeout": 20.0 if is_ci else 10.0,  # Double file operation timeout
        "retry_attempts": 5 if is_ci else 2,  # More retries for GitHub Actions
        "retry_delay": 3.0 if is_ci else 1.0,  # Longer delays between retries
    }


@pytest.fixture(autouse=True)
def standardized_test_environment(
    repository_context: dict[str, str], test_environment_config: dict[str, Any]
) -> Generator[None, None, None]:
    """Automatically set up standardized test environment for all tests.

    This fixture combines repository context and environment configuration
    to provide a consistent test environment across all test scenarios.
    It's marked as autouse=True so it applies to all tests automatically.

    Args:
        repository_context: Repository context fixture (dependency)
        test_environment_config: Environment configuration fixture
    """
    # Use the repository_context dependency to ensure it's set up first
    _ = repository_context

    # Store original test-related environment variables
    original_test_env = {}
    test_env_vars = [
        "PYTEST_CURRENT_TEST",
        "TEST_ENVIRONMENT",
        "TEST_REPOSITORY_CONTEXT",
    ]

    for var in test_env_vars:
        original_test_env[var] = os.environ.get(var)

    # Set standardized test environment variables
    os.environ["TEST_ENVIRONMENT"] = "ci" if test_environment_config["is_ci"] else "local"
    os.environ["TEST_REPOSITORY_CONTEXT"] = "stabbotco1/mypylogger"

    yield

    # Restore original test environment
    for var, original_value in original_test_env.items():
        if original_value is not None:
            os.environ[var] = original_value
        else:
            os.environ.pop(var, None)


@pytest.fixture
def mock_github_api() -> Generator[Mock, None, None]:
    """Provide mock GitHub API for testing GitHub interactions.

    This fixture mocks urllib.request.urlopen to simulate GitHub API
    responses without making actual network calls during tests.
    """
    with patch("urllib.request.urlopen") as mock_urlopen:
        # Configure default successful response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"success": true}'
        mock_urlopen.return_value = mock_response

        yield mock_urlopen


@pytest.fixture
def github_api_responses() -> dict[str, Any]:
    """Provide common GitHub API response templates for testing.

    Returns a dictionary of common API responses that can be used
    to configure mock_github_api for specific test scenarios.
    """
    return {
        "issue_created": {
            "status": 201,
            "response": {
                "html_url": "https://github.com/stabbotco1/mypylogger/issues/123",
                "number": 123,
                "title": "Test Issue",
                "state": "open",
            },
        },
        "issue_creation_failed": {
            "status": 422,
            "response": {
                "message": "Validation Failed",
                "errors": [{"field": "title", "code": "missing"}],
            },
        },
        "repository_info": {
            "status": 200,
            "response": {
                "full_name": "stabbotco1/mypylogger",
                "owner": {"login": "stabbotco1"},
                "name": "mypylogger",
                "private": False,
                "html_url": "https://github.com/stabbotco1/mypylogger",
            },
        },
        "unauthorized": {"status": 401, "response": {"message": "Bad credentials"}},
        "not_found": {"status": 404, "response": {"message": "Not Found"}},
    }


@pytest.fixture
def mock_file_operations() -> Generator[Mock, None, None]:
    """Provide mock file operations for testing file I/O without actual files.

    This fixture can be used to mock file operations when testing
    components that interact with the filesystem.
    """
    with patch("pathlib.Path.open"), patch("pathlib.Path.write_text"), patch(
        "pathlib.Path.read_text"
    ), patch("pathlib.Path.exists"), patch("pathlib.Path.mkdir") as mock_operations:
        yield mock_operations
