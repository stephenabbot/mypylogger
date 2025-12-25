"""Unit tests for publishing error handler."""

from __future__ import annotations

import json
from pathlib import Path

# Import the modules we're testing
import sys
import tempfile
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from publishing_error_handler import (
    ErrorCategory,
    ErrorSeverity,
    PublishingError,
    PublishingErrorHandler,
    RetryConfig,
)


class TestPublishingError:
    """Test PublishingError class."""

    def test_publishing_error_creation(self) -> None:
        """Test creating a PublishingError instance."""
        error = PublishingError(
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.CRITICAL,
            message="Authentication failed",
            details="Invalid API token",
            command="twine upload",
            exit_code=1,
            stderr="401 Unauthorized",
        )

        assert error.category == ErrorCategory.AUTHENTICATION
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.message == "Authentication failed"
        assert error.details == "Invalid API token"
        assert error.command == "twine upload"
        assert error.exit_code == 1
        assert error.stderr == "401 Unauthorized"
        assert error.is_retryable is True  # Default value
        assert error.retry_count == 0  # Default value

    def test_publishing_error_to_dict(self) -> None:
        """Test converting PublishingError to dictionary."""
        error = PublishingError(
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            message="Network timeout",
            retry_count=2,
        )

        error_dict = error.to_dict()

        assert error_dict["category"] == "network"
        assert error_dict["severity"] == "medium"
        assert error_dict["message"] == "Network timeout"
        assert error_dict["retry_count"] == 2
        assert "timestamp" in error_dict


class TestRetryConfig:
    """Test RetryConfig class."""

    def test_retry_config_defaults(self) -> None:
        """Test RetryConfig with default values."""
        config = RetryConfig()

        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_factor == 2.0
        assert config.jitter is True

    def test_retry_config_custom_values(self) -> None:
        """Test RetryConfig with custom values."""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
            backoff_factor=3.0,
            jitter=False,
        )

        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.backoff_factor == 3.0
        assert config.jitter is False

    def test_get_delay_exponential_backoff(self) -> None:
        """Test exponential backoff delay calculation."""
        config = RetryConfig(base_delay=1.0, backoff_factor=2.0, jitter=False)

        assert config.get_delay(0) == 1.0  # 1.0 * 2^0
        assert config.get_delay(1) == 2.0  # 1.0 * 2^1
        assert config.get_delay(2) == 4.0  # 1.0 * 2^2
        assert config.get_delay(3) == 8.0  # 1.0 * 2^3

    def test_get_delay_max_delay_cap(self) -> None:
        """Test that delay is capped at max_delay."""
        config = RetryConfig(base_delay=1.0, max_delay=5.0, backoff_factor=2.0, jitter=False)

        assert config.get_delay(0) == 1.0
        assert config.get_delay(1) == 2.0
        assert config.get_delay(2) == 4.0
        assert config.get_delay(3) == 5.0  # Capped at max_delay
        assert config.get_delay(4) == 5.0  # Still capped

    def test_get_delay_with_jitter(self) -> None:
        """Test delay calculation with jitter."""
        config = RetryConfig(base_delay=2.0, backoff_factor=2.0, jitter=True)

        # With jitter, delay should be between 50% and 100% of calculated delay
        delay = config.get_delay(1)  # Base calculation: 2.0 * 2^1 = 4.0
        assert 2.0 <= delay <= 4.0  # Should be between 50% and 100% of 4.0


class TestPublishingErrorHandler:
    """Test PublishingErrorHandler class."""

    def test_error_handler_initialization(self) -> None:
        """Test error handler initialization."""
        handler = PublishingErrorHandler()

        assert handler.errors == []
        assert handler.log_file is None
        assert handler.logger is not None

    def test_error_handler_with_log_file(self) -> None:
        """Test error handler initialization with log file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            handler = PublishingErrorHandler(log_file)

            assert handler.log_file == log_file
            assert handler.logger is not None

    def test_categorize_authentication_error(self) -> None:
        """Test categorizing authentication errors."""
        handler = PublishingErrorHandler()

        category = handler.categorize_error(
            "twine upload", 1, "401 Unauthorized: Invalid API token"
        )
        assert category == ErrorCategory.AUTHENTICATION

        category = handler.categorize_error("twine upload", 1, "Authentication failed")
        assert category == ErrorCategory.AUTHENTICATION

        category = handler.categorize_error("twine upload", 1, "Forbidden access")
        assert category == ErrorCategory.AUTHENTICATION

    def test_categorize_network_error(self) -> None:
        """Test categorizing network errors."""
        handler = PublishingErrorHandler()

        category = handler.categorize_error("twine upload", 1, "Connection timeout")
        assert category == ErrorCategory.NETWORK

        category = handler.categorize_error("twine upload", 1, "Network unreachable")
        assert category == ErrorCategory.NETWORK

        category = handler.categorize_error("twine upload", 1, "SSL certificate error")
        assert category == ErrorCategory.NETWORK

    def test_categorize_validation_error(self) -> None:
        """Test categorizing validation errors."""
        handler = PublishingErrorHandler()

        category = handler.categorize_error("twine check", 1, "Validation failed")
        assert category == ErrorCategory.VALIDATION

        category = handler.categorize_error("twine check", 1, "Invalid metadata")
        assert category == ErrorCategory.VALIDATION

        category = handler.categorize_error("build", 1, "Syntax error in setup.py")
        assert category == ErrorCategory.VALIDATION

    def test_categorize_build_error(self) -> None:
        """Test categorizing build errors."""
        handler = PublishingErrorHandler()

        category = handler.categorize_error("python -m build", 1, "Build failed")
        assert category == ErrorCategory.BUILD

        category = handler.categorize_error("python -m build", 1, "Missing file: README.md")
        assert category == ErrorCategory.BUILD

        category = handler.categorize_error("python -m build", 1, "Import error: module not found")
        assert category == ErrorCategory.BUILD

    def test_categorize_upload_error(self) -> None:
        """Test categorizing upload errors."""
        handler = PublishingErrorHandler()

        category = handler.categorize_error("twine upload", 1, "File already exists")
        assert category == ErrorCategory.UPLOAD

        category = handler.categorize_error("twine upload", 1, "Version already exists")
        assert category == ErrorCategory.UPLOAD

        category = handler.categorize_error("twine upload", 1, "Duplicate upload")
        assert category == ErrorCategory.UPLOAD

    def test_categorize_unknown_error(self) -> None:
        """Test categorizing unknown errors."""
        handler = PublishingErrorHandler()

        category = handler.categorize_error("unknown command", 1, "Some random error")
        assert category == ErrorCategory.UNKNOWN

    def test_determine_severity(self) -> None:
        """Test determining error severity."""
        handler = PublishingErrorHandler()

        assert handler.determine_severity(ErrorCategory.AUTHENTICATION, 1) == ErrorSeverity.CRITICAL
        assert handler.determine_severity(ErrorCategory.VALIDATION, 1) == ErrorSeverity.HIGH
        assert handler.determine_severity(ErrorCategory.BUILD, 1) == ErrorSeverity.HIGH
        assert handler.determine_severity(ErrorCategory.NETWORK, 1) == ErrorSeverity.MEDIUM
        assert handler.determine_severity(ErrorCategory.UPLOAD, 1) == ErrorSeverity.MEDIUM
        assert handler.determine_severity(ErrorCategory.CONFIGURATION, 1) == ErrorSeverity.HIGH
        assert handler.determine_severity(ErrorCategory.UNKNOWN, 1) == ErrorSeverity.MEDIUM

    def test_is_retryable_error(self) -> None:
        """Test determining if error is retryable."""
        handler = PublishingErrorHandler()

        # Non-retryable errors
        assert not handler.is_retryable_error(ErrorCategory.AUTHENTICATION, "unauthorized")
        assert not handler.is_retryable_error(ErrorCategory.VALIDATION, "invalid metadata")
        assert not handler.is_retryable_error(ErrorCategory.UPLOAD, "file exists")

        # Retryable errors
        assert handler.is_retryable_error(ErrorCategory.NETWORK, "connection timeout")
        assert handler.is_retryable_error(ErrorCategory.UNKNOWN, "random error")

    def test_handle_command_error(self) -> None:
        """Test handling command errors."""
        handler = PublishingErrorHandler()

        error = handler.handle_command_error(
            "twine upload",
            1,
            "stdout content",
            "401 Unauthorized",
            retry_count=1,
        )

        assert error.category == ErrorCategory.AUTHENTICATION
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.message == "Command failed: twine upload"
        assert error.command == "twine upload"
        assert error.exit_code == 1
        assert error.stdout == "stdout content"
        assert error.stderr == "401 Unauthorized"
        assert error.retry_count == 1
        assert not error.is_retryable

        # Check that error was added to handler's error list
        assert len(handler.errors) == 1
        assert handler.errors[0] == error

    def test_handle_command_error_with_list_command(self) -> None:
        """Test handling command errors with list command."""
        handler = PublishingErrorHandler()

        error = handler.handle_command_error(
            ["twine", "upload", "dist/*"],
            1,
            "",
            "Network error",
        )

        assert error.command == "twine upload dist/*"
        assert error.category == ErrorCategory.NETWORK

    @patch("subprocess.run")
    def test_run_command_with_retry_success(self, mock_run: Mock) -> None:
        """Test running command with retry - success case."""
        handler = PublishingErrorHandler()

        # Mock successful command execution
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "success"
        mock_run.return_value.stderr = ""

        success, error = handler.run_command_with_retry("echo test")

        assert success is True
        assert error is None
        assert len(handler.errors) == 0
        mock_run.assert_called_once()

    @patch("subprocess.run")
    @patch("time.sleep")
    def test_run_command_with_retry_failure_then_success(
        self, mock_sleep: Mock, mock_run: Mock
    ) -> None:
        """Test running command with retry - failure then success."""
        handler = PublishingErrorHandler()

        # Mock first call fails, second call succeeds
        mock_run.side_effect = [
            Mock(returncode=1, stdout="", stderr="Network timeout"),
            Mock(returncode=0, stdout="success", stderr=""),
        ]

        retry_config = RetryConfig(max_retries=2, base_delay=0.1)
        success, error = handler.run_command_with_retry("test command", retry_config)

        assert success is True
        assert error is None
        assert mock_run.call_count == 2
        mock_sleep.assert_called_once()

    @patch("subprocess.run")
    @patch("time.sleep")
    def test_run_command_with_retry_permanent_failure(
        self, mock_sleep: Mock, mock_run: Mock
    ) -> None:
        """Test running command with retry - permanent failure."""
        handler = PublishingErrorHandler()

        # Mock all calls fail
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "Authentication failed"

        retry_config = RetryConfig(max_retries=2, base_delay=0.1)
        success, error = handler.run_command_with_retry("test command", retry_config)

        assert success is False
        assert error is not None
        assert error.category == ErrorCategory.AUTHENTICATION
        assert not error.is_retryable
        assert mock_run.call_count == 1  # Should not retry non-retryable errors
        mock_sleep.assert_not_called()

    def test_generate_error_report_no_errors(self) -> None:
        """Test generating error report with no errors."""
        handler = PublishingErrorHandler()

        report = handler.generate_error_report()

        assert report["status"] == "success"
        assert report["errors"] == []
        assert "No errors occurred" in report["summary"]

    def test_generate_error_report_with_errors(self) -> None:
        """Test generating error report with errors."""
        handler = PublishingErrorHandler()

        # Add some test errors
        error1 = PublishingError(
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.CRITICAL,
            message="Auth failed",
            is_retryable=False,
        )
        error2 = PublishingError(
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            message="Network timeout",
            is_retryable=True,
        )

        handler.errors = [error1, error2]

        report = handler.generate_error_report()

        assert report["status"] == "error"
        assert report["total_errors"] == 2
        assert report["error_categories"]["authentication"] == 1
        assert report["error_categories"]["network"] == 1
        assert report["severity_counts"]["critical"] == 1
        assert report["severity_counts"]["medium"] == 1
        assert report["retryable_errors"] == 1
        assert report["most_severe"] == "critical"
        assert len(report["errors"]) == 2

    def test_save_error_report(self) -> None:
        """Test saving error report to file."""
        handler = PublishingErrorHandler()

        # Add a test error
        error = PublishingError(
            category=ErrorCategory.BUILD,
            severity=ErrorSeverity.HIGH,
            message="Build failed",
        )
        handler.errors = [error]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "error_report.json"
            handler.save_error_report(output_file)

            assert output_file.exists()

            # Verify file contents
            with output_file.open() as f:
                saved_report = json.load(f)

            assert saved_report["status"] == "error"
            assert saved_report["total_errors"] == 1
            assert len(saved_report["errors"]) == 1

    def test_execute_with_retry_success(self) -> None:
        """Test execute_with_retry with successful function."""
        handler = PublishingErrorHandler()

        def success_func() -> tuple[int, str, str]:
            return 0, "success", ""

        success, error = handler.execute_with_retry(success_func, operation_name="test_op")

        assert success is True
        assert error is None
        assert len(handler.errors) == 0

    @patch("time.sleep")
    def test_execute_with_retry_with_retries(self, mock_sleep: Mock) -> None:
        """Test execute_with_retry with retries."""
        handler = PublishingErrorHandler()

        call_count = 0

        def retry_func() -> tuple[int, str, str]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return 1, "", "Network timeout"  # Retryable error
            return 0, "success", ""  # Success on second try

        retry_config = RetryConfig(max_retries=2, base_delay=0.1)
        success, error = handler.execute_with_retry(retry_func, retry_config, "test_operation")

        assert success is True
        assert error is None
        assert call_count == 2
        mock_sleep.assert_called_once()

    def test_execute_with_retry_exception(self) -> None:
        """Test execute_with_retry with function that raises exception."""
        handler = PublishingErrorHandler()

        def exception_func() -> tuple[int, str, str]:
            msg = "Test exception"
            raise ValueError(msg)

        success, error = handler.execute_with_retry(exception_func, operation_name="test_op")

        assert success is False
        assert error is not None
        assert error.category == ErrorCategory.UNKNOWN
        assert error.severity == ErrorSeverity.HIGH
        assert "Unexpected error" in error.message
        assert not error.is_retryable
