"""Handler management for mypylogger."""

from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path
import sys
import tempfile
from typing import TYPE_CHECKING, TextIO

from .exceptions import HandlerError
from .formatters import SourceLocationJSONFormatter

if TYPE_CHECKING:
    from .config import LogConfig


class HandlerFactory:
    """Creates and configures log handlers with fallback logic."""

    def __init__(self) -> None:
        """Initialize HandlerFactory."""
        self._formatter = SourceLocationJSONFormatter()

    def create_console_handler(self) -> logging.StreamHandler[TextIO]:
        """Create stdout handler with JSON formatter.

        Returns:
            Configured StreamHandler for stdout.
        """
        try:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(self._formatter)
            # Enable immediate flush for real-time log visibility
            original_flush = handler.flush

            def custom_flush() -> None:
                sys.stdout.flush()
                original_flush()

            handler.flush = custom_flush  # type: ignore[method-assign]
            return handler
        except Exception as e:
            msg = f"Failed to create console handler: {e}"
            raise HandlerError(msg) from e

    def create_file_handler(self, config: LogConfig) -> logging.FileHandler | None:
        """Create file handler with graceful fallback on failure.

        Args:
            config: LogConfig instance with file logging configuration.

        Returns:
            FileHandler instance if successful, None if fallback needed.
        """
        if not config.log_to_file:
            return None

        try:
            # Ensure log directory exists
            if not self._ensure_log_directory(config.log_file_dir):
                self._log_handler_error(
                    "Failed to create log directory, falling back to stdout only"
                )
                return None

            # Generate log filename
            log_filename = self._generate_log_filename(config)
            log_filepath = config.log_file_dir / log_filename

            # Create file handler
            handler = logging.FileHandler(log_filepath, mode="a", encoding="utf-8")
            handler.setFormatter(self._formatter)

            # Enable immediate flush for real-time log visibility
            original_flush = handler.flush

            def custom_flush() -> None:
                if handler.stream:
                    handler.stream.flush()
                original_flush()

            handler.flush = custom_flush  # type: ignore[method-assign]

            return handler

        except (OSError, PermissionError) as e:
            self._log_handler_error(f"File logging failed, using stdout only: {e}")
            return None
        except Exception as e:
            self._log_handler_error(f"Unexpected error creating file handler: {e}")
            return None

    def _generate_log_filename(self, config: LogConfig) -> str:
        """Generate log filename using pattern {APP_NAME}_{date}_{hour}.log.

        Args:
            config: LogConfig instance.

        Returns:
            Generated log filename.
        """
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        hour_str = now.strftime("%H")
        return f"{config.app_name}_{date_str}_{hour_str}.log"

    def _ensure_log_directory(self, log_dir: Path) -> bool:
        """Create log directory with fallback handling.

        Args:
            log_dir: Path to log directory.

        Returns:
            True if directory exists or was created successfully.
        """
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            return True
        except OSError as e:
            self._log_handler_error(f"Failed to create log directory {log_dir}: {e}")

            # Try temp directory as fallback
            try:
                temp_dir = Path(tempfile.gettempdir()) / "mypylogger"
                temp_dir.mkdir(exist_ok=True)
                self._log_handler_error(f"Using temporary directory: {temp_dir}")
                # Update the config to use temp directory
                return True
            except OSError as e2:
                self._log_handler_error(f"Failed to create temp directory: {e2}")
                return False

    def _log_handler_error(self, message: str) -> None:
        """Log handler errors to stderr without affecting user logging.

        Args:
            message: Error message to log.
        """
        try:
            print(f"mypylogger: {message}", file=sys.stderr)
        except OSError:
            # If stderr is not available or fails, silently continue
            # This is intentional to prevent mypylogger from crashing user applications
            pass
