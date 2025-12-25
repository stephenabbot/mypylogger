"""Core logger management for mypylogger."""

from __future__ import annotations

import inspect
import logging
import os
import sys

from .config import ConfigResolver, LogConfig
from .handlers import HandlerFactory


class LoggerManager:
    """Manages logger creation and configuration."""

    def __init__(self) -> None:
        """Initialize LoggerManager."""
        self._configured_loggers: set[str] = set()
        self._handler_cache: dict[str, logging.Handler] = {}
        self._config_resolver = ConfigResolver()
        self._handler_factory = HandlerFactory()

    def get_or_create_logger(self, name: str | None = None) -> logging.Logger:
        """Get existing logger or create new one with full configuration.

        Args:
            name: Logger name. If None, uses fallback chain.

        Returns:
            Configured Logger instance.
        """
        try:
            # Resolve logger name using fallback chain
            logger_name = self._resolve_logger_name(name)

            # Get or create logger
            logger = logging.getLogger(logger_name)

            # Configure logger if not already configured
            if not self._is_logger_configured(logger_name):
                config = self._config_resolver.resolve_config()
                self.configure_logger(logger, config)
                self._configured_loggers.add(logger_name)

            return logger

        except Exception as e:
            self._log_library_error(f"Failed to create logger: {e}")
            # Return basic logger as fallback
            return logging.getLogger("mypylogger_fallback")

    def configure_logger(self, logger: logging.Logger, config: LogConfig) -> None:
        """Apply handlers, formatters, and level configuration to logger.

        Args:
            logger: Logger instance to configure.
            config: LogConfig with configuration settings.
        """
        try:
            # Set log level
            level = getattr(logging, config.log_level, logging.INFO)
            logger.setLevel(level)

            # Create and add console handler
            console_handler = self._handler_factory.create_console_handler()
            logger.addHandler(console_handler)

            # Create and add file handler if configured
            if config.log_to_file:
                file_handler = self._handler_factory.create_file_handler(config)
                if file_handler:
                    logger.addHandler(file_handler)

            # Prevent propagation to avoid duplicate logs
            logger.propagate = False

        except Exception as e:
            self._log_library_error(f"Failed to configure logger: {e}")

    def _resolve_logger_name(self, name: str | None) -> str:
        """Resolve logger name using fallback chain.

        Args:
            name: Provided logger name.

        Returns:
            Resolved logger name using fallback chain.
        """
        # Use provided name if available
        if name:
            return name

        # Try APP_NAME environment variable
        app_name = os.getenv("APP_NAME")
        if app_name:
            return app_name

        # Try to get calling module's __name__
        try:
            frame = inspect.currentframe()
            if frame and frame.f_back and frame.f_back.f_back:
                caller_globals = frame.f_back.f_back.f_globals
                module_name = caller_globals.get("__name__")
                if module_name and isinstance(module_name, str) and module_name != "__main__":
                    return str(module_name)
        except (AttributeError, KeyError, TypeError):
            # Expected exceptions when frame inspection fails
            pass

        # Final fallback
        return "mypylogger"

    def _is_logger_configured(self, logger_name: str) -> bool:
        """Check if logger has already been configured by mypylogger.

        Args:
            logger_name: Name of logger to check.

        Returns:
            True if logger is already configured.
        """
        return logger_name in self._configured_loggers

    def _log_library_error(self, message: str) -> None:
        """Log mypylogger internal errors to stderr.

        Args:
            message: Error message to log.
        """
        try:
            print(f"mypylogger: {message}", file=sys.stderr)
        except OSError:
            # If stderr is not available or fails, silently continue
            # This is intentional to prevent mypylogger from crashing user applications
            pass
