"""Unit tests for public API functionality."""

import logging
import os
from unittest.mock import patch

import mypylogger


class TestPublicAPI:
    """Test public API functions."""

    def test_get_logger_returns_logger(self) -> None:
        """Test that get_logger returns a Logger instance."""
        logger = mypylogger.get_logger("test_public_api")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_public_api"

    def test_get_logger_without_name(self) -> None:
        """Test that get_logger works without providing a name."""
        logger = mypylogger.get_logger()

        assert isinstance(logger, logging.Logger)

    def test_get_logger_with_none_name(self) -> None:
        """Test that get_logger works with explicit None name."""
        logger = mypylogger.get_logger(None)

        assert isinstance(logger, logging.Logger)

    def test_get_logger_with_app_name_env_var(self) -> None:
        """Test that get_logger uses APP_NAME environment variable."""
        with patch.dict(os.environ, {"APP_NAME": "test_env_app"}, clear=True):
            logger = mypylogger.get_logger()

            assert isinstance(logger, logging.Logger)
            assert logger.name == "test_env_app"

    def test_get_logger_graceful_error_handling(self) -> None:
        """Test that get_logger handles errors gracefully and never crashes."""
        # Test with various invalid inputs - should never raise exceptions
        logger1 = mypylogger.get_logger("")
        logger2 = mypylogger.get_logger("   ")
        logger3 = mypylogger.get_logger("test/with/slashes")

        assert isinstance(logger1, logging.Logger)
        assert isinstance(logger2, logging.Logger)
        assert isinstance(logger3, logging.Logger)

    def test_get_logger_error_handling_with_invalid_config(self) -> None:
        """Test get_logger handles invalid configuration gracefully."""
        # Set invalid environment variables
        with patch.dict(
            os.environ,
            {
                "LOG_LEVEL": "INVALID_LEVEL",
                "LOG_TO_FILE": "invalid_boolean",
                "LOG_FILE_DIR": "/nonexistent/invalid/path",
            },
            clear=True,
        ):
            # Should not raise exceptions, should use safe defaults
            logger = mypylogger.get_logger("test_invalid_config")

            assert isinstance(logger, logging.Logger)
            assert logger.name == "test_invalid_config"

    def test_get_logger_integration_with_all_components(self) -> None:
        """Test get_logger integrates all components correctly."""
        logger = mypylogger.get_logger("integration_test")

        # Verify logger has handlers
        assert len(logger.handlers) > 0

        # Verify logger can log without errors
        logger.info("Test message")
        logger.debug("Debug message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

    def test_get_logger_with_custom_fields(self) -> None:
        """Test get_logger works with custom fields in logging calls."""
        logger = mypylogger.get_logger("custom_fields_test")

        # Should not raise exceptions when using extra parameter
        logger.info("Test with extra", extra={"user_id": 123, "session": "abc"})

        # Should not raise exceptions when using extra parameter (second example)
        logger.info("Test with custom", extra={"request_id": "xyz", "trace": "def"})

    def test_get_version_returns_version(self) -> None:
        """Test that get_version returns the version string."""
        version = mypylogger.get_version()

        assert isinstance(version, str)
        assert version == "0.2.8"

    def test_public_api_exports(self) -> None:
        """Test that all expected items are in __all__."""
        expected_exports = [
            "ConfigurationError",
            "FormattingError",
            "HandlerError",
            "MypyloggerError",
            "get_logger",
            "get_version",
        ]

        for export in expected_exports:
            assert export in mypylogger.__all__
            assert hasattr(mypylogger, export)

    def test_version_attribute(self) -> None:
        """Test that __version__ attribute is available."""
        assert hasattr(mypylogger, "__version__")
        assert mypylogger.__version__ == "0.2.8"

    def test_exception_classes_available(self) -> None:
        """Test that all exception classes are available and properly inherit."""
        # Test that exception classes exist and inherit correctly
        assert issubclass(mypylogger.MypyloggerError, Exception)
        assert issubclass(mypylogger.ConfigurationError, mypylogger.MypyloggerError)
        assert issubclass(mypylogger.FormattingError, mypylogger.MypyloggerError)
        assert issubclass(mypylogger.HandlerError, mypylogger.MypyloggerError)

    def test_get_logger_never_raises_exceptions(self) -> None:
        """Test that get_logger never raises exceptions under any circumstances."""
        # Test various edge cases that might cause exceptions
        test_cases = [
            None,
            "",
            "   ",
            "test\nwith\nnewlines",
            "test\twith\ttabs",
            "test with spaces",
            "test/with/slashes",
            "test\\with\\backslashes",
            "test.with.dots",
            "test-with-dashes",
            "test_with_underscores",
            "UPPERCASE_NAME",
            "mixedCaseName",
            "123numeric_start",
            "special!@#$%^&*()chars",
            "very_long_name_" * 10,  # Very long name
        ]

        for test_name in test_cases:
            logger = mypylogger.get_logger(test_name)
            assert isinstance(logger, logging.Logger)
