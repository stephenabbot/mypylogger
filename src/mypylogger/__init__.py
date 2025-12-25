"""mypylogger v0.2.8 - Zero-dependency JSON logging with sensible defaults."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .core import LoggerManager
from .exceptions import ConfigurationError, FormattingError, HandlerError, MypyloggerError

if TYPE_CHECKING:
    import logging

__version__ = "0.2.8"

# Global logger manager instance
_logger_manager = LoggerManager()


def get_logger(name: str | None = None) -> logging.Logger:
    """Get or create a logger with JSON formatting and source location tracking.

    Args:
        name: Logger name. If None, uses APP_NAME env var, then calling module's __name__,
              then "mypylogger" as final fallback.

    Returns:
        Configured Logger instance with JSON formatting and appropriate handlers.
    """
    return _logger_manager.get_or_create_logger(name)


def get_version() -> str:
    """Get the version of mypylogger.

    Returns:
        The version string.
    """
    return __version__


# Public API exports
__all__ = [
    "ConfigurationError",
    "FormattingError",
    "HandlerError",
    "MypyloggerError",
    "get_logger",
    "get_version",
]
