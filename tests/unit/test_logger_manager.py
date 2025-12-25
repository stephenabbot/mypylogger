"""Unit tests for LoggerManager functionality."""

import logging
import os
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch

from mypylogger.config import LogConfig
from mypylogger.core import LoggerManager


class TestLoggerManager:
    """Test LoggerManager class."""

    def test_logger_manager_initialization(self) -> None:
        """Test LoggerManager initializes correctly."""
        manager = LoggerManager()

        assert hasattr(manager, "_configured_loggers")
        assert hasattr(manager, "_handler_cache")
        assert hasattr(manager, "_config_resolver")
        assert hasattr(manager, "_handler_factory")
        assert len(manager._configured_loggers) == 0

    def test_get_or_create_logger_with_name(self) -> None:
        """Test getting logger with explicit name."""
        manager = LoggerManager()

        with patch.object(manager._config_resolver, "resolve_config") as mock_resolve:
            mock_config = LogConfig(
                app_name="test_app",
                log_level="INFO",
                log_to_file=False,
                log_file_dir=Path(tempfile.gettempdir()),
            )
            mock_resolve.return_value = mock_config

            with patch.object(manager._handler_factory, "create_console_handler") as mock_console:
                mock_handler = Mock(spec=logging.StreamHandler)
                mock_console.return_value = mock_handler

                logger = manager.get_or_create_logger("test_logger")

                assert isinstance(logger, logging.Logger)
                assert logger.name == "test_logger"
                assert "test_logger" in manager._configured_loggers

    def test_get_or_create_logger_without_name_uses_fallback(self) -> None:
        """Test getting logger without name uses fallback chain."""
        manager = LoggerManager()

        with patch.object(manager._config_resolver, "resolve_config") as mock_resolve:
            mock_config = LogConfig(
                app_name="test_app",
                log_level="INFO",
                log_to_file=False,
                log_file_dir=Path(tempfile.gettempdir()),
            )
            mock_resolve.return_value = mock_config

            with patch.object(manager._handler_factory, "create_console_handler") as mock_console:
                mock_handler = Mock(spec=logging.StreamHandler)
                mock_console.return_value = mock_handler

                with patch.dict(os.environ, {"APP_NAME": "env_app"}, clear=True):
                    logger = manager.get_or_create_logger(None)

                    assert isinstance(logger, logging.Logger)
                    assert logger.name == "env_app"

    def test_get_or_create_logger_fallback_to_mypylogger(self) -> None:
        """Test logger name fallback to 'mypylogger' when no other options."""
        manager = LoggerManager()

        with patch.object(manager._config_resolver, "resolve_config") as mock_resolve:
            mock_config = LogConfig(
                app_name="test_app",
                log_level="INFO",
                log_to_file=False,
                log_file_dir=Path(tempfile.gettempdir()),
            )
            mock_resolve.return_value = mock_config

            with patch.object(manager._handler_factory, "create_console_handler") as mock_console:
                mock_handler = Mock(spec=logging.StreamHandler)
                mock_console.return_value = mock_handler

                with patch.dict(os.environ, {}, clear=True), patch(
                    "inspect.currentframe", return_value=None
                ):
                    logger = manager.get_or_create_logger(None)

                    assert isinstance(logger, logging.Logger)
                    assert logger.name == "mypylogger"

    def test_get_or_create_logger_already_configured(self) -> None:
        """Test that already configured loggers are not reconfigured."""
        manager = LoggerManager()
        manager._configured_loggers.add("existing_logger")

        logger = manager.get_or_create_logger("existing_logger")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "existing_logger"

    def test_get_or_create_logger_exception_handling(self) -> None:
        """Test exception handling in get_or_create_logger."""
        manager = LoggerManager()

        with patch.object(
            manager._config_resolver, "resolve_config", side_effect=Exception("Config error")
        ), patch.object(manager, "_log_library_error") as mock_log_error:
            logger = manager.get_or_create_logger("test_logger")

            assert isinstance(logger, logging.Logger)
            assert logger.name == "mypylogger_fallback"
            mock_log_error.assert_called_once()

    def test_configure_logger_basic(self) -> None:
        """Test basic logger configuration."""
        manager = LoggerManager()
        logger = logging.getLogger("test_config")

        config = LogConfig(
            app_name="test_app",
            log_level="DEBUG",
            log_to_file=False,
            log_file_dir=Path(tempfile.gettempdir()),
        )

        with patch.object(manager._handler_factory, "create_console_handler") as mock_console:
            mock_handler = Mock(spec=logging.StreamHandler)
            mock_console.return_value = mock_handler

            manager.configure_logger(logger, config)

            assert logger.level == logging.DEBUG
            assert logger.propagate is False
            mock_console.assert_called_once()

    def test_configure_logger_with_file_handler(self) -> None:
        """Test logger configuration with file handler."""
        manager = LoggerManager()
        logger = logging.getLogger("test_file_config")

        config = LogConfig(
            app_name="test_app",
            log_level="INFO",
            log_to_file=True,
            log_file_dir=Path(tempfile.gettempdir()),
        )

        with patch.object(manager._handler_factory, "create_console_handler") as mock_console:
            mock_console_handler = Mock(spec=logging.StreamHandler)
            mock_console.return_value = mock_console_handler

            with patch.object(manager._handler_factory, "create_file_handler") as mock_file:
                mock_file_handler = Mock(spec=logging.FileHandler)
                mock_file.return_value = mock_file_handler

                manager.configure_logger(logger, config)

                assert logger.level == logging.INFO
                assert logger.propagate is False
                mock_console.assert_called_once()
                mock_file.assert_called_once_with(config)

    def test_configure_logger_file_handler_none(self) -> None:
        """Test logger configuration when file handler creation returns None."""
        manager = LoggerManager()
        logger = logging.getLogger("test_file_none")

        config = LogConfig(
            app_name="test_app",
            log_level="INFO",
            log_to_file=True,
            log_file_dir=Path(tempfile.gettempdir()),
        )

        with patch.object(manager._handler_factory, "create_console_handler") as mock_console:
            mock_console_handler = Mock(spec=logging.StreamHandler)
            mock_console.return_value = mock_console_handler

            with patch.object(manager._handler_factory, "create_file_handler", return_value=None):
                manager.configure_logger(logger, config)

                assert logger.level == logging.INFO
                assert logger.propagate is False

    def test_configure_logger_exception_handling(self) -> None:
        """Test exception handling in configure_logger."""
        manager = LoggerManager()
        logger = logging.getLogger("test_config_error")

        config = LogConfig(
            app_name="test_app",
            log_level="INVALID_LEVEL",  # This will cause an error
            log_to_file=False,
            log_file_dir=Path(tempfile.gettempdir()),
        )

        with patch.object(manager, "_log_library_error") as mock_log_error, patch.object(
            manager._handler_factory,
            "create_console_handler",
            side_effect=Exception("Handler error"),
        ):
            manager.configure_logger(logger, config)

            mock_log_error.assert_called_once()

    def test_resolve_logger_name_with_provided_name(self) -> None:
        """Test _resolve_logger_name with provided name."""
        manager = LoggerManager()

        result = manager._resolve_logger_name("provided_name")
        assert result == "provided_name"

    def test_resolve_logger_name_with_env_var(self) -> None:
        """Test _resolve_logger_name with APP_NAME environment variable."""
        manager = LoggerManager()

        with patch.dict(os.environ, {"APP_NAME": "env_app_name"}, clear=True):
            result = manager._resolve_logger_name(None)
            assert result == "env_app_name"

    def test_resolve_logger_name_with_caller_module(self) -> None:
        """Test _resolve_logger_name with caller module name."""
        manager = LoggerManager()

        # Mock the frame inspection to return a module name
        mock_frame = Mock()
        mock_frame.f_back = Mock()
        mock_frame.f_back.f_back = Mock()
        mock_frame.f_back.f_back.f_globals = {"__name__": "test_module"}

        with patch.dict(os.environ, {}, clear=True), patch(
            "inspect.currentframe", return_value=mock_frame
        ):
            result = manager._resolve_logger_name(None)
            assert result == "test_module"

    def test_resolve_logger_name_skip_main_module(self) -> None:
        """Test _resolve_logger_name skips __main__ module."""
        manager = LoggerManager()

        # Mock the frame inspection to return __main__
        mock_frame = Mock()
        mock_frame.f_back = Mock()
        mock_frame.f_back.f_back = Mock()
        mock_frame.f_back.f_back.f_globals = {"__name__": "__main__"}

        with patch.dict(os.environ, {}, clear=True), patch(
            "inspect.currentframe", return_value=mock_frame
        ):
            result = manager._resolve_logger_name(None)
            assert result == "mypylogger"  # Should fall back to default

    def test_resolve_logger_name_frame_exception(self) -> None:
        """Test _resolve_logger_name handles frame inspection exceptions."""
        manager = LoggerManager()

        with patch.dict(os.environ, {}, clear=True), patch(
            "inspect.currentframe", side_effect=AttributeError("Frame error")
        ):
            result = manager._resolve_logger_name(None)
            assert result == "mypylogger"

    def test_resolve_logger_name_no_frame_back(self) -> None:
        """Test _resolve_logger_name when frame.f_back is None."""
        manager = LoggerManager()

        mock_frame = Mock()
        mock_frame.f_back = None

        with patch.dict(os.environ, {}, clear=True), patch(
            "inspect.currentframe", return_value=mock_frame
        ):
            result = manager._resolve_logger_name(None)
            assert result == "mypylogger"

    def test_is_logger_configured_true(self) -> None:
        """Test _is_logger_configured returns True for configured logger."""
        manager = LoggerManager()
        manager._configured_loggers.add("configured_logger")

        result = manager._is_logger_configured("configured_logger")
        assert result is True

    def test_is_logger_configured_false(self) -> None:
        """Test _is_logger_configured returns False for unconfigured logger."""
        manager = LoggerManager()

        result = manager._is_logger_configured("unconfigured_logger")
        assert result is False

    def test_log_library_error_success(self) -> None:
        """Test _log_library_error prints to stderr successfully."""
        manager = LoggerManager()

        with patch("builtins.print") as mock_print:
            manager._log_library_error("Test error message")

            mock_print.assert_called_once()
            args, kwargs = mock_print.call_args
            assert "mypylogger: Test error message" in args[0]
            assert kwargs.get("file") is not None

    def test_log_library_error_exception_handling(self) -> None:
        """Test _log_library_error handles print exceptions gracefully."""
        manager = LoggerManager()

        with patch("builtins.print", side_effect=OSError("Print error")):
            # Should not raise an exception
            manager._log_library_error("Test error message")
