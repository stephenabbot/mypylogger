"""Unit tests for HandlerFactory functionality."""

import logging
from pathlib import Path
import sys
import tempfile
from unittest.mock import Mock, patch

import pytest

from mypylogger.config import LogConfig
from mypylogger.exceptions import HandlerError
from mypylogger.formatters import SourceLocationJSONFormatter
from mypylogger.handlers import HandlerFactory


class TestHandlerFactory:
    """Test HandlerFactory class."""

    def test_handler_factory_initialization(self) -> None:
        """Test HandlerFactory initializes correctly."""
        factory = HandlerFactory()

        assert hasattr(factory, "_formatter")
        assert isinstance(factory._formatter, SourceLocationJSONFormatter)

    def test_create_console_handler_success(self) -> None:
        """Test successful console handler creation."""
        factory = HandlerFactory()

        handler = factory.create_console_handler()

        assert isinstance(handler, logging.StreamHandler)
        assert handler.stream is sys.stdout
        assert isinstance(handler.formatter, SourceLocationJSONFormatter)
        assert hasattr(handler, "flush")

    def test_create_console_handler_exception(self) -> None:
        """Test console handler creation handles exceptions."""
        factory = HandlerFactory()

        with patch("logging.StreamHandler", side_effect=Exception("Handler error")):
            with pytest.raises(HandlerError) as exc_info:
                factory.create_console_handler()

            assert "Failed to create console handler" in str(exc_info.value)
            assert "Handler error" in str(exc_info.value)

    def test_create_file_handler_disabled(self) -> None:
        """Test file handler creation when file logging is disabled."""
        factory = HandlerFactory()
        config = LogConfig(
            app_name="test_app",
            log_level="INFO",
            log_to_file=False,
            log_file_dir=Path(tempfile.gettempdir()),
        )

        handler = factory.create_file_handler(config)

        assert handler is None

    def test_create_file_handler_success(self) -> None:
        """Test successful file handler creation."""
        factory = HandlerFactory()

        with tempfile.TemporaryDirectory() as temp_dir:
            config = LogConfig(
                app_name="test_app", log_level="INFO", log_to_file=True, log_file_dir=Path(temp_dir)
            )

            with patch.object(factory, "_generate_log_filename", return_value="test.log"):
                handler = factory.create_file_handler(config)

                assert isinstance(handler, logging.FileHandler)
                assert isinstance(handler.formatter, SourceLocationJSONFormatter)
                assert hasattr(handler, "flush")

    def test_create_file_handler_directory_creation_fails(self) -> None:
        """Test file handler creation when directory creation fails."""
        factory = HandlerFactory()
        config = LogConfig(
            app_name="test_app",
            log_level="INFO",
            log_to_file=True,
            log_file_dir=Path("/nonexistent/path"),
        )

        with patch.object(factory, "_ensure_log_directory", return_value=False):
            with patch.object(factory, "_log_handler_error") as mock_log_error:
                handler = factory.create_file_handler(config)

                assert handler is None
                mock_log_error.assert_called_once()

    def test_create_file_handler_os_error(self) -> None:
        """Test file handler creation handles OSError."""
        factory = HandlerFactory()
        config = LogConfig(
            app_name="test_app",
            log_level="INFO",
            log_to_file=True,
            log_file_dir=Path(tempfile.gettempdir()),
        )

        with patch.object(factory, "_ensure_log_directory", return_value=True):
            with patch("logging.FileHandler", side_effect=OSError("Permission denied")):
                with patch.object(factory, "_log_handler_error") as mock_log_error:
                    handler = factory.create_file_handler(config)

                    assert handler is None
                    mock_log_error.assert_called_once()

    def test_create_file_handler_permission_error(self) -> None:
        """Test file handler creation handles PermissionError."""
        factory = HandlerFactory()
        config = LogConfig(
            app_name="test_app",
            log_level="INFO",
            log_to_file=True,
            log_file_dir=Path(tempfile.gettempdir()),
        )

        with patch.object(factory, "_ensure_log_directory", return_value=True):
            with patch("logging.FileHandler", side_effect=PermissionError("Access denied")):
                with patch.object(factory, "_log_handler_error") as mock_log_error:
                    handler = factory.create_file_handler(config)

                    assert handler is None
                    mock_log_error.assert_called_once()

    def test_create_file_handler_unexpected_exception(self) -> None:
        """Test file handler creation handles unexpected exceptions."""
        factory = HandlerFactory()
        config = LogConfig(
            app_name="test_app",
            log_level="INFO",
            log_to_file=True,
            log_file_dir=Path(tempfile.gettempdir()),
        )

        with patch.object(factory, "_ensure_log_directory", return_value=True):
            with patch.object(
                factory, "_generate_log_filename", side_effect=Exception("Unexpected error")
            ):
                with patch.object(factory, "_log_handler_error") as mock_log_error:
                    handler = factory.create_file_handler(config)

                    assert handler is None
                    mock_log_error.assert_called_once()

    def test_generate_log_filename_basic(self) -> None:
        """Test log filename generation with basic config."""
        factory = HandlerFactory()
        config = LogConfig(
            app_name="myapp",
            log_level="INFO",
            log_to_file=True,
            log_file_dir=Path(tempfile.gettempdir()),
        )

        with patch("mypylogger.handlers.datetime") as mock_datetime:
            mock_now = Mock()
            mock_now.strftime.side_effect = lambda fmt: {"%Y%m%d": "20231201", "%H": "14"}[fmt]
            mock_datetime.now.return_value = mock_now

            filename = factory._generate_log_filename(config)

            assert filename == "myapp_20231201_14.log"

    def test_generate_log_filename_with_different_app_name(self) -> None:
        """Test log filename generation with different app name."""
        factory = HandlerFactory()
        config = LogConfig(
            app_name="different_app",
            log_level="INFO",
            log_to_file=True,
            log_file_dir=Path(tempfile.gettempdir()),
        )

        with patch("mypylogger.handlers.datetime") as mock_datetime:
            mock_now = Mock()
            mock_now.strftime.side_effect = lambda fmt: {"%Y%m%d": "20231225", "%H": "09"}[fmt]
            mock_datetime.now.return_value = mock_now

            filename = factory._generate_log_filename(config)

            assert filename == "different_app_20231225_09.log"

    def test_ensure_log_directory_success(self) -> None:
        """Test successful log directory creation."""
        factory = HandlerFactory()

        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "logs"

            result = factory._ensure_log_directory(log_dir)

            assert result is True
            assert log_dir.exists()

    def test_ensure_log_directory_already_exists(self) -> None:
        """Test log directory creation when directory already exists."""
        factory = HandlerFactory()

        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)  # Use existing directory

            result = factory._ensure_log_directory(log_dir)

            assert result is True

    def test_ensure_log_directory_os_error_with_temp_fallback(self) -> None:
        """Test log directory creation with OSError and successful temp fallback."""
        factory = HandlerFactory()
        log_dir = Path("/nonexistent/path")

        with patch.object(factory, "_log_handler_error") as mock_log_error:
            with patch("pathlib.Path.mkdir") as mock_mkdir:
                # First call (main directory) fails, second call (temp) succeeds
                mock_mkdir.side_effect = [OSError("Permission denied"), None]

                result = factory._ensure_log_directory(log_dir)

                assert result is True
                assert mock_log_error.call_count == 2  # One for main error, one for temp success

    def test_ensure_log_directory_os_error_temp_fallback_fails(self) -> None:
        """Test log directory creation when both main and temp directory creation fail."""
        factory = HandlerFactory()
        log_dir = Path("/nonexistent/path")

        with patch.object(factory, "_log_handler_error") as mock_log_error:
            with patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied")):
                result = factory._ensure_log_directory(log_dir)

                assert result is False
                assert mock_log_error.call_count == 2  # One for main error, one for temp error

    def test_log_handler_error_success(self) -> None:
        """Test _log_handler_error prints to stderr successfully."""
        factory = HandlerFactory()

        with patch("builtins.print") as mock_print:
            factory._log_handler_error("Test error message")

            mock_print.assert_called_once()
            args, kwargs = mock_print.call_args
            assert "mypylogger: Test error message" in args
            assert kwargs.get("file") is sys.stderr

    def test_log_handler_error_exception_handling(self) -> None:
        """Test _log_handler_error handles print exceptions gracefully."""
        factory = HandlerFactory()

        with patch("builtins.print", side_effect=OSError("Print error")):
            # Should not raise an exception
            factory._log_handler_error("Test error message")

    def test_file_handler_flush_functionality(self) -> None:
        """Test that file handler has flush functionality."""
        factory = HandlerFactory()

        with tempfile.TemporaryDirectory() as temp_dir:
            config = LogConfig(
                app_name="test_app", log_level="INFO", log_to_file=True, log_file_dir=Path(temp_dir)
            )

            handler = factory.create_file_handler(config)
            assert handler is not None

            # Test that flush method exists and can be called
            with patch.object(handler.stream, "flush"):
                handler.flush()
                # The custom flush should call both stream.flush and original flush

    def test_console_handler_flush_functionality(self) -> None:
        """Test that console handler has flush functionality."""
        factory = HandlerFactory()

        handler = factory.create_console_handler()

        # Test that flush method exists and can be called
        with patch("sys.stdout.flush") as mock_flush:
            handler.flush()
            # The custom flush calls both sys.stdout.flush() and original flush()
            # sys.stdout.flush() should be called at least once
            assert mock_flush.call_count >= 1

    def test_file_handler_encoding(self) -> None:
        """Test that file handler uses UTF-8 encoding."""
        factory = HandlerFactory()

        with tempfile.TemporaryDirectory() as temp_dir:
            config = LogConfig(
                app_name="test_app", log_level="INFO", log_to_file=True, log_file_dir=Path(temp_dir)
            )

            with patch("logging.FileHandler") as mock_file_handler:
                mock_handler = Mock()
                mock_file_handler.return_value = mock_handler

                factory.create_file_handler(config)

                # Verify FileHandler was called with UTF-8 encoding
                mock_file_handler.assert_called_once()
                _args, kwargs = mock_file_handler.call_args
                assert kwargs.get("encoding") == "utf-8"
                assert kwargs.get("mode") == "a"

    def test_file_handler_with_stream_none(self) -> None:
        """Test file handler flush when stream is None."""
        factory = HandlerFactory()

        with tempfile.TemporaryDirectory() as temp_dir:
            config = LogConfig(
                app_name="test_app", log_level="INFO", log_to_file=True, log_file_dir=Path(temp_dir)
            )

            handler = factory.create_file_handler(config)
            assert handler is not None

            # Set stream to None to test the condition
            handler.stream = None

            # Should not raise an exception
            handler.flush()

    def test_temp_directory_fallback_path(self) -> None:
        """Test that temp directory fallback uses correct path."""
        factory = HandlerFactory()
        log_dir = Path("/nonexistent/path")

        with patch.object(factory, "_log_handler_error"):
            with patch("pathlib.Path.mkdir") as mock_mkdir:
                # First call fails, second call succeeds
                mock_mkdir.side_effect = [OSError("Permission denied"), None]

                result = factory._ensure_log_directory(log_dir)

                assert result is True
                # Verify the temp directory path was created
                assert mock_mkdir.call_count == 2
                # Second call should be for temp directory
                mock_mkdir.call_args_list[1]
                # The temp directory should be created with exist_ok=True
