"""Configuration management for mypylogger."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tempfile
from typing import ClassVar

from .exceptions import ConfigurationError


@dataclass
class LogConfig:
    """Configuration container for logger setup."""

    app_name: str
    log_level: str
    log_to_file: bool
    log_file_dir: Path

    # Environment variable mappings
    ENV_MAPPINGS: ClassVar[dict[str, str]] = {
        "APP_NAME": "app_name",
        "LOG_LEVEL": "log_level",
        "LOG_TO_FILE": "log_to_file",
        "LOG_FILE_DIR": "log_file_dir",
    }


class ConfigResolver:
    """Resolves configuration from environment variables with safe defaults."""

    VALID_LOG_LEVELS: ClassVar[set[str]] = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

    def resolve_config(self) -> LogConfig:
        """Get configuration from environment with fallback to safe defaults.

        Returns:
            LogConfig instance with resolved configuration values.
        """
        try:
            app_name = os.getenv("APP_NAME", "mypylogger")
            log_level = self._get_safe_log_level(os.getenv("LOG_LEVEL", "INFO"))
            log_to_file = self._parse_bool(os.getenv("LOG_TO_FILE", "false"))
            log_file_dir = self._get_safe_file_dir(os.getenv("LOG_FILE_DIR", tempfile.gettempdir()))

            return LogConfig(
                app_name=app_name,
                log_level=log_level,
                log_to_file=log_to_file,
                log_file_dir=log_file_dir,
            )
        except Exception as e:
            msg = f"Failed to resolve configuration: {e}"
            raise ConfigurationError(msg) from e

    def _get_safe_log_level(self, level_str: str) -> str:
        """Validate and return safe log level.

        Args:
            level_str: Log level string from environment.

        Returns:
            Valid log level string.
        """
        level_upper = level_str.upper()
        if level_upper in self.VALID_LOG_LEVELS:
            return level_upper
        return "INFO"  # Safe default

    def _get_safe_file_dir(self, dir_path: str) -> Path:
        """Validate and return safe file directory path.

        Args:
            dir_path: Directory path string from environment.

        Returns:
            Path object for log file directory.
        """
        try:
            return Path(dir_path).resolve()
        except (OSError, ValueError):
            return Path(tempfile.gettempdir())  # Safe default

    def _parse_bool(self, value: str) -> bool:
        """Parse boolean value from string.

        Args:
            value: String value to parse as boolean.

        Returns:
            Boolean value.
        """
        return value.lower() in ("true", "1", "yes", "on")
