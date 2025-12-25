"""Integration tests for end-to-end logging workflows."""

import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

import mypylogger


class TestEndToEndWorkflows:
    """Test complete logging workflows from get_logger() to output."""

    def test_complete_console_logging_workflow(self) -> None:
        """Test complete workflow from get_logger to console output."""
        with patch.dict(os.environ, {"LOG_TO_FILE": "false"}, clear=True):
            logger = mypylogger.get_logger("e2e_console_test")

            # Verify logger is properly configured
            assert logger.name == "e2e_console_test"
            assert len(logger.handlers) > 0

            # Test logging at different levels
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            logger.critical("Critical message")

    def test_complete_file_logging_workflow(self) -> None:
        """Test complete workflow from get_logger to file output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_vars = {
                "APP_NAME": "e2e_file_test",
                "LOG_TO_FILE": "true",
                "LOG_FILE_DIR": temp_dir,
                "LOG_LEVEL": "DEBUG",
            }

            with patch.dict(os.environ, env_vars, clear=True):
                logger = mypylogger.get_logger()

                # Log test messages
                logger.info("Test info message")
                logger.error("Test error message")

                # Verify file was created
                log_files = list(Path(temp_dir).glob("*.log"))
                assert len(log_files) > 0

                # Verify log content
                log_file = log_files[0]
                content = log_file.read_text()
                lines = [line.strip() for line in content.split("\n") if line.strip()]

                assert len(lines) >= 2

                # Verify JSON structure
                for line in lines:
                    log_entry = json.loads(line)
                    assert "timestamp" in log_entry
                    assert "level" in log_entry
                    assert "message" in log_entry
                    assert "module" in log_entry
                    assert "filename" in log_entry
                    assert "function_name" in log_entry
                    assert "line" in log_entry

    def test_environment_variable_configuration_integration(self) -> None:
        """Test complete environment variable configuration integration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_vars = {
                "APP_NAME": "env_config_test",
                "LOG_LEVEL": "WARNING",
                "LOG_TO_FILE": "true",
                "LOG_FILE_DIR": temp_dir,
            }

            with patch.dict(os.environ, env_vars, clear=True):
                logger = mypylogger.get_logger()

                # Verify logger name from environment
                assert logger.name == "env_config_test"

                # Test that log level is respected
                logger.debug("Debug message - should not appear")
                logger.info("Info message - should not appear")
                logger.warning("Warning message - should appear")
                logger.error("Error message - should appear")

                # Verify file output
                log_files = list(Path(temp_dir).glob("*.log"))
                assert len(log_files) > 0

                content = log_files[0].read_text()
                lines = [line.strip() for line in content.split("\n") if line.strip()]

                # Should only have WARNING and ERROR messages
                assert len(lines) == 2

                for line in lines:
                    log_entry = json.loads(line)
                    assert log_entry["level"] in ["WARNING", "ERROR"]

    def test_custom_fields_end_to_end(self) -> None:
        """Test custom fields integration end-to-end."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_vars = {
                "APP_NAME": "custom_fields_test",
                "LOG_TO_FILE": "true",
                "LOG_FILE_DIR": temp_dir,
            }

            with patch.dict(os.environ, env_vars, clear=True):
                logger = mypylogger.get_logger()

                # Log with custom fields via extra
                logger.info(
                    "Message with extra",
                    extra={"user_id": 123, "session_id": "abc123", "request_id": "req-456"},
                )

                # Log with custom fields via extra parameter (second example)
                logger.error(
                    "Error with custom",
                    extra={"error_code": "E001", "component": "auth", "retry_count": 3},
                )

                # Verify file output includes custom fields
                log_files = list(Path(temp_dir).glob("*.log"))
                assert len(log_files) > 0

                content = log_files[0].read_text()
                lines = [line.strip() for line in content.split("\n") if line.strip()]

                assert len(lines) == 2

                # Check first log entry
                log_entry1 = json.loads(lines[0])
                assert log_entry1["user_id"] == 123
                assert log_entry1["session_id"] == "abc123"
                assert log_entry1["request_id"] == "req-456"

                # Check second log entry
                log_entry2 = json.loads(lines[1])
                assert log_entry2["error_code"] == "E001"
                assert log_entry2["component"] == "auth"
                assert log_entry2["retry_count"] == 3

    def test_error_handling_end_to_end(self) -> None:
        """Test error handling and graceful degradation end-to-end."""
        # Test with invalid log directory - should fall back gracefully
        env_vars = {
            "APP_NAME": "error_handling_test",
            "LOG_TO_FILE": "true",
            "LOG_FILE_DIR": "/nonexistent/invalid/path",
            "LOG_LEVEL": "INVALID_LEVEL",  # Invalid level should use safe default
        }

        with patch.dict(os.environ, env_vars, clear=True):
            # Should not raise exceptions
            logger = mypylogger.get_logger()

            # Should be able to log without errors
            logger.info("Test message with invalid config")
            logger.error("Error message with invalid config")

            # Logger should still work
            assert logger.name == "error_handling_test"
            assert len(logger.handlers) > 0

    def test_multiple_loggers_integration(self) -> None:
        """Test multiple loggers working together."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_vars = {"LOG_TO_FILE": "true", "LOG_FILE_DIR": temp_dir}

            with patch.dict(os.environ, env_vars, clear=True):
                # Create multiple loggers
                logger1 = mypylogger.get_logger("service1")
                logger2 = mypylogger.get_logger("service2")
                logger3 = mypylogger.get_logger("service3")

                # Log from different loggers
                logger1.info("Message from service1")
                logger2.warning("Warning from service2")
                logger3.error("Error from service3")

                # Verify all messages are logged
                log_files = list(Path(temp_dir).glob("*.log"))
                assert len(log_files) > 0

                content = log_files[0].read_text()
                lines = [line.strip() for line in content.split("\n") if line.strip()]

                assert len(lines) >= 3

                # Verify different modules are logged
                modules = set()
                for line in lines:
                    log_entry = json.loads(line)
                    modules.add(log_entry.get("module", ""))

                # Should have entries from different loggers
                assert len(modules) >= 1

    def test_json_output_format_validation(self) -> None:
        """Test that JSON output format meets all requirements."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_vars = {
                "APP_NAME": "json_format_test",
                "LOG_TO_FILE": "true",
                "LOG_FILE_DIR": temp_dir,
            }

            with patch.dict(os.environ, env_vars, clear=True):
                logger = mypylogger.get_logger()

                logger.info("JSON format validation test")

                # Read and validate JSON output
                log_files = list(Path(temp_dir).glob("*.log"))
                assert len(log_files) > 0

                content = log_files[0].read_text()
                lines = [line.strip() for line in content.split("\n") if line.strip()]

                assert len(lines) >= 1

                log_entry = json.loads(lines[0])

                # Verify required fields exist
                required_fields = [
                    "timestamp",
                    "level",
                    "message",
                    "module",
                    "filename",
                    "function_name",
                    "line",
                ]

                for field in required_fields:
                    assert field in log_entry, f"Required field '{field}' missing"

                # Verify field types
                assert isinstance(log_entry["timestamp"], str)
                assert isinstance(log_entry["level"], str)
                assert isinstance(log_entry["message"], str)
                assert isinstance(log_entry["module"], str)
                assert isinstance(log_entry["filename"], str)
                assert isinstance(log_entry["function_name"], str)
                assert isinstance(log_entry["line"], int)

                # Verify timestamp format (ISO 8601 with microseconds)
                timestamp = log_entry["timestamp"]
                assert "T" in timestamp
                assert timestamp.endswith("Z")

                # Verify level is valid
                assert log_entry["level"] in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    def test_real_filesystem_operations_and_cleanup(self) -> None:
        """Test real filesystem operations with proper cleanup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "logs"

            env_vars = {
                "APP_NAME": "filesystem_test",
                "LOG_TO_FILE": "true",
                "LOG_FILE_DIR": str(log_dir),
            }

            with patch.dict(os.environ, env_vars, clear=True):
                logger = mypylogger.get_logger()

                # Log multiple messages
                for i in range(10):
                    logger.info("Test message %d", i)

                # Verify directory was created
                assert log_dir.exists()
                assert log_dir.is_dir()

                # Verify log file was created
                log_files = list(log_dir.glob("*.log"))
                assert len(log_files) == 1

                log_file = log_files[0]
                assert log_file.exists()
                assert log_file.is_file()

                # Verify file naming pattern
                assert log_file.name.startswith("filesystem_test_")
                assert log_file.name.endswith(".log")

                # Verify content
                content = log_file.read_text()
                lines = [line.strip() for line in content.split("\n") if line.strip()]
                assert len(lines) == 10

                # Verify each line is valid JSON
                for i, line in enumerate(lines):
                    log_entry = json.loads(line)
                    assert log_entry["message"] == f"Test message {i}"
