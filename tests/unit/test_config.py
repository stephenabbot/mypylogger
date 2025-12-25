"""Unit tests for mypylogger configuration functionality."""

import os
from pathlib import Path
import tempfile
from unittest.mock import patch

import pytest

from mypylogger.config import ConfigResolver, LogConfig
from mypylogger.exceptions import ConfigurationError


class TestLogConfig:
    """Test LogConfig data model."""

    def test_logconfig_creation_with_defaults(self) -> None:
        """Test LogConfig can be created with all required fields."""
        config = LogConfig(
            app_name="test_app",
            log_level="INFO",
            log_to_file=False,
            log_file_dir=Path(tempfile.gettempdir()),
        )

        assert config.app_name == "test_app"
        assert config.log_level == "INFO"
        assert config.log_to_file is False
        assert config.log_file_dir == Path(tempfile.gettempdir())

    def test_logconfig_env_mappings_exist(self) -> None:
        """Test LogConfig has environment variable mappings."""
        expected_mappings = {
            "APP_NAME": "app_name",
            "LOG_LEVEL": "log_level",
            "LOG_TO_FILE": "log_to_file",
            "LOG_FILE_DIR": "log_file_dir",
        }

        assert expected_mappings == LogConfig.ENV_MAPPINGS

    def test_logconfig_with_custom_values(self) -> None:
        """Test LogConfig with custom configuration values."""
        custom_dir = Path("/var/log/myapp")
        config = LogConfig(
            app_name="custom_app", log_level="DEBUG", log_to_file=True, log_file_dir=custom_dir
        )

        assert config.app_name == "custom_app"
        assert config.log_level == "DEBUG"
        assert config.log_to_file is True
        assert config.log_file_dir == custom_dir


class TestConfigResolver:
    """Test ConfigResolver class."""

    def test_resolve_config_with_defaults(self) -> None:
        """Test config resolution with default values when no env vars set."""
        with patch.dict(os.environ, {}, clear=True):
            resolver = ConfigResolver()
            config = resolver.resolve_config()

            assert config.app_name == "mypylogger"
            assert config.log_level == "INFO"
            assert config.log_to_file is False
            assert config.log_file_dir == Path(tempfile.gettempdir()).resolve()

    def test_resolve_config_with_env_vars(self) -> None:
        """Test config resolution with environment variables set."""
        env_vars = {
            "APP_NAME": "test_application",
            "LOG_LEVEL": "DEBUG",
            "LOG_TO_FILE": "true",
            "LOG_FILE_DIR": "/var/log/test",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            resolver = ConfigResolver()
            config = resolver.resolve_config()

            assert config.app_name == "test_application"
            assert config.log_level == "DEBUG"
            assert config.log_to_file is True
            assert config.log_file_dir == Path("/var/log/test").resolve()

    def test_get_safe_log_level_valid_levels(self) -> None:
        """Test safe log level validation with valid levels."""
        resolver = ConfigResolver()

        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in valid_levels:
            assert resolver._get_safe_log_level(level) == level
            assert resolver._get_safe_log_level(level.lower()) == level

    def test_get_safe_log_level_invalid_level(self) -> None:
        """Test safe log level validation with invalid level falls back to INFO."""
        resolver = ConfigResolver()

        invalid_levels = ["INVALID", "TRACE", "VERBOSE", ""]
        for level in invalid_levels:
            assert resolver._get_safe_log_level(level) == "INFO"

    def test_get_safe_file_dir_valid_path(self) -> None:
        """Test safe file directory validation with valid path."""
        resolver = ConfigResolver()

        with tempfile.TemporaryDirectory() as temp_dir:
            result = resolver._get_safe_file_dir(temp_dir)
            assert result == Path(temp_dir).resolve()

    def test_get_safe_file_dir_invalid_path(self) -> None:
        """Test safe file directory validation with invalid path falls back to temp."""
        resolver = ConfigResolver()

        # Test path that will cause OSError during resolve()
        with patch("pathlib.Path.resolve", side_effect=OSError("Path error")):
            result = resolver._get_safe_file_dir("/some/path")
            assert result == Path(tempfile.gettempdir())

        # Test path that will cause ValueError during resolve()
        with patch("pathlib.Path.resolve", side_effect=ValueError("Invalid path")):
            result = resolver._get_safe_file_dir("/some/path")
            assert result == Path(tempfile.gettempdir())

        # Test empty string separately as it resolves to current directory
        result = resolver._get_safe_file_dir("")
        # Empty string resolves to current working directory, not temp
        assert result == Path().resolve()

    def test_parse_bool_true_values(self) -> None:
        """Test boolean parsing with true values."""
        resolver = ConfigResolver()

        true_values = ["true", "True", "TRUE", "1", "yes", "YES", "on", "ON"]
        for value in true_values:
            assert resolver._parse_bool(value) is True

    def test_parse_bool_false_values(self) -> None:
        """Test boolean parsing with false values."""
        resolver = ConfigResolver()

        false_values = ["false", "False", "FALSE", "0", "no", "NO", "off", "OFF", ""]
        for value in false_values:
            assert resolver._parse_bool(value) is False

    def test_resolve_config_handles_exceptions(self) -> None:
        """Test config resolution handles exceptions gracefully."""
        resolver = ConfigResolver()

        # Mock os.getenv to raise an exception
        with patch("os.getenv", side_effect=Exception("Environment error")):
            with pytest.raises(ConfigurationError) as exc_info:
                resolver.resolve_config()

            assert "Failed to resolve configuration" in str(exc_info.value)
            assert "Environment error" in str(exc_info.value)

    def test_valid_log_levels_constant(self) -> None:
        """Test that VALID_LOG_LEVELS constant contains expected levels."""
        expected_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        assert expected_levels == ConfigResolver.VALID_LOG_LEVELS

    def test_get_safe_file_dir_with_path_object(self) -> None:
        """Test _get_safe_file_dir with Path object input."""
        resolver = ConfigResolver()

        with tempfile.TemporaryDirectory() as temp_dir:
            path_obj = Path(temp_dir)
            result = resolver._get_safe_file_dir(str(path_obj))
            assert result == path_obj.resolve()

    def test_resolve_config_integration(self) -> None:
        """Test complete config resolution integration."""
        env_vars = {
            "APP_NAME": "integration_test",
            "LOG_LEVEL": "warning",  # Test case conversion
            "LOG_TO_FILE": "1",  # Test numeric true
            "LOG_FILE_DIR": tempfile.gettempdir(),
        }

        with patch.dict(os.environ, env_vars, clear=True):
            resolver = ConfigResolver()
            config = resolver.resolve_config()

            assert config.app_name == "integration_test"
            assert config.log_level == "WARNING"  # Should be uppercase
            assert config.log_to_file is True
            assert config.log_file_dir == Path(tempfile.gettempdir()).resolve()

    def test_get_safe_file_dir_os_error_handling(self) -> None:
        """Test _get_safe_file_dir handles OSError gracefully."""
        resolver = ConfigResolver()

        with patch("pathlib.Path.resolve", side_effect=OSError("Path resolution error")):
            result = resolver._get_safe_file_dir("/some/path")
            assert result == Path(tempfile.gettempdir())

    def test_get_safe_file_dir_value_error_handling(self) -> None:
        """Test _get_safe_file_dir handles ValueError gracefully."""
        resolver = ConfigResolver()

        with patch("pathlib.Path.resolve", side_effect=ValueError("Invalid path")):
            result = resolver._get_safe_file_dir("/some/path")
            assert result == Path(tempfile.gettempdir())
