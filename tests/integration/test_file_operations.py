"""Integration tests for file logging operations."""

import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

import mypylogger


class TestFileOperations:
    """Test file logging operations and filesystem interactions."""

    def test_log_file_creation_and_naming(self) -> None:
        """Test log file creation with correct naming pattern."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_vars = {
                "APP_NAME": "file_naming_test",
                "LOG_TO_FILE": "true",
                "LOG_FILE_DIR": temp_dir,
            }

            with patch.dict(os.environ, env_vars, clear=True):
                logger = mypylogger.get_logger()
                logger.info("Test log file creation")

                # Verify file was created
                log_files = list(Path(temp_dir).glob("*.log"))
                assert len(log_files) == 1

                log_file = log_files[0]

                # Verify naming pattern: {APP_NAME}_{date}_{hour}.log
                filename = log_file.name
                assert filename.startswith("file_naming_test_")
                assert filename.endswith(".log")

                # Extract date and hour parts
                parts = filename.replace("file_naming_test_", "").replace(".log", "").split("_")
                assert len(parts) == 2

                date_part, hour_part = parts
                assert len(date_part) == 8  # YYYYMMDD
                assert len(hour_part) == 2  # HH
                assert date_part.isdigit()
                assert hour_part.isdigit()
                assert 0 <= int(hour_part) <= 23

    def test_log_directory_creation(self) -> None:
        """Test automatic log directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Use nested directory that doesn't exist
            log_dir = Path(temp_dir) / "logs" / "app" / "nested"

            env_vars = {
                "APP_NAME": "dir_creation_test",
                "LOG_TO_FILE": "true",
                "LOG_FILE_DIR": str(log_dir),
            }

            with patch.dict(os.environ, env_vars, clear=True):
                # Directory should not exist initially
                assert not log_dir.exists()

                logger = mypylogger.get_logger()
                logger.info("Test directory creation")

                # Directory should be created
                assert log_dir.exists()
                assert log_dir.is_dir()

                # Log file should be created in the directory
                log_files = list(log_dir.glob("*.log"))
                assert len(log_files) == 1

    def test_file_logging_with_utf8_encoding(self) -> None:
        """Test file logging with UTF-8 encoding for unicode characters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_vars = {"APP_NAME": "utf8_test", "LOG_TO_FILE": "true", "LOG_FILE_DIR": temp_dir}

            with patch.dict(os.environ, env_vars, clear=True):
                logger = mypylogger.get_logger()

                # Log messages with unicode characters
                logger.info("Test with émojis: 🚀 🎉 ✨")
                logger.info("Test with accents: café, naïve, résumé")
                logger.info("Test with symbols: ©️ ®️ ™️")
                logger.info("Test with Chinese: 你好世界")
                logger.info("Test with Arabic: مرحبا بالعالم")

                # Read file and verify unicode content
                log_files = list(Path(temp_dir).glob("*.log"))
                assert len(log_files) == 1

                # Read with UTF-8 encoding
                content = log_files[0].read_text(encoding="utf-8")
                lines = [line.strip() for line in content.split("\n") if line.strip()]

                assert len(lines) == 5

                # Verify unicode characters are preserved
                messages = []
                for line in lines:
                    log_entry = json.loads(line)
                    messages.append(log_entry["message"])

                assert "🚀 🎉 ✨" in messages[0]
                assert "café, naïve, résumé" in messages[1]
                assert "©️ ®️ ™️" in messages[2]
                assert "你好世界" in messages[3]
                assert "مرحبا بالعالم" in messages[4]

    def test_file_logging_immediate_flush(self) -> None:
        """Test that file logging uses immediate flush for real-time visibility."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_vars = {"APP_NAME": "flush_test", "LOG_TO_FILE": "true", "LOG_FILE_DIR": temp_dir}

            with patch.dict(os.environ, env_vars, clear=True):
                logger = mypylogger.get_logger()

                # Log a message
                logger.info("First message")

                # Immediately check if file content is available (immediate flush)
                log_files = list(Path(temp_dir).glob("*.log"))
                assert len(log_files) == 1

                content = log_files[0].read_text()
                lines = [line.strip() for line in content.split("\n") if line.strip()]
                assert len(lines) == 1

                log_entry = json.loads(lines[0])
                assert log_entry["message"] == "First message"

                # Log another message
                logger.info("Second message")

                # Should be immediately available
                content = log_files[0].read_text()
                lines = [line.strip() for line in content.split("\n") if line.strip()]
                assert len(lines) == 2

    def test_file_logging_fallback_to_stdout(self) -> None:
        """Test fallback to stdout when file logging fails."""
        # Use invalid directory path
        invalid_path = "/nonexistent/invalid/path"

        env_vars = {
            "APP_NAME": "fallback_test",
            "LOG_TO_FILE": "true",
            "LOG_FILE_DIR": invalid_path,
        }

        with patch.dict(os.environ, env_vars, clear=True):
            # Should not raise exceptions, should fall back gracefully
            logger = mypylogger.get_logger()

            # Should be able to log without errors
            logger.info("Test fallback message")
            logger.error("Test fallback error")

            # Logger should still have handlers (console fallback)
            assert len(logger.handlers) > 0

    def test_file_logging_permission_error_handling(self) -> None:
        """Test handling of permission errors during file operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a directory and make it read-only
            restricted_dir = Path(temp_dir) / "restricted"
            restricted_dir.mkdir()

            env_vars = {
                "APP_NAME": "permission_test",
                "LOG_TO_FILE": "true",
                "LOG_FILE_DIR": str(restricted_dir),
            }

            with patch.dict(os.environ, env_vars, clear=True):
                # Mock permission error during file creation
                with patch("logging.FileHandler", side_effect=PermissionError("Access denied")):
                    # Should not raise exceptions
                    logger = mypylogger.get_logger()

                    # Should be able to log (falls back to console)
                    logger.info("Test with permission error")

                    # Should have console handler as fallback
                    assert len(logger.handlers) > 0

    def test_multiple_loggers_same_file(self) -> None:
        """Test multiple loggers writing to the same file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_vars = {"LOG_TO_FILE": "true", "LOG_FILE_DIR": temp_dir}

            with patch.dict(os.environ, env_vars, clear=True):
                # Create multiple loggers with same app name
                logger1 = mypylogger.get_logger("shared_app")
                logger2 = mypylogger.get_logger("shared_app")
                logger3 = mypylogger.get_logger("different_app")

                # Log from different loggers
                logger1.info("Message from logger1")
                logger2.warning("Message from logger2")
                logger3.error("Message from logger3")

                # Should have log files created
                log_files = list(Path(temp_dir).glob("*.log"))
                assert len(log_files) > 0

                # Read all content
                all_content = ""
                for log_file in log_files:
                    all_content += log_file.read_text()

                lines = [line.strip() for line in all_content.split("\n") if line.strip()]
                assert len(lines) >= 3

                # Verify all messages are present
                messages = []
                for line in lines:
                    log_entry = json.loads(line)
                    messages.append(log_entry["message"])

                assert "Message from logger1" in messages
                assert "Message from logger2" in messages
                assert "Message from logger3" in messages

    def test_log_file_append_mode(self) -> None:
        """Test that log files are opened in append mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_vars = {"APP_NAME": "append_test", "LOG_TO_FILE": "true", "LOG_FILE_DIR": temp_dir}

            with patch.dict(os.environ, env_vars, clear=True):
                # First logger session
                logger1 = mypylogger.get_logger()
                logger1.info("First session message")

                # Get the log file
                log_files = list(Path(temp_dir).glob("*.log"))
                assert len(log_files) == 1
                log_file = log_files[0]

                # Verify first message
                content = log_file.read_text()
                lines = [line.strip() for line in content.split("\n") if line.strip()]
                assert len(lines) == 1

                # Second logger session (simulating app restart)
                logger2 = mypylogger.get_logger()
                logger2.info("Second session message")

                # Verify both messages are present (append mode)
                content = log_file.read_text()
                lines = [line.strip() for line in content.split("\n") if line.strip()]
                assert len(lines) == 2

                messages = []
                for line in lines:
                    log_entry = json.loads(line)
                    messages.append(log_entry["message"])

                assert "First session message" in messages
                assert "Second session message" in messages

    def test_file_cleanup_and_resource_management(self) -> None:
        """Test proper file handle cleanup and resource management."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_vars = {"APP_NAME": "cleanup_test", "LOG_TO_FILE": "true", "LOG_FILE_DIR": temp_dir}

            with patch.dict(os.environ, env_vars, clear=True):
                # Create logger and log messages
                logger = mypylogger.get_logger()

                for i in range(100):
                    logger.info("Message %d", i)

                # Verify file was created and contains all messages
                log_files = list(Path(temp_dir).glob("*.log"))
                assert len(log_files) == 1

                content = log_files[0].read_text()
                lines = [line.strip() for line in content.split("\n") if line.strip()]
                assert len(lines) == 100

                # Verify all messages are present and properly formatted
                for i, line in enumerate(lines):
                    log_entry = json.loads(line)
                    assert log_entry["message"] == f"Message {i}"

    def test_concurrent_file_access(self) -> None:
        """Test concurrent access to log files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_vars = {
                "APP_NAME": "concurrent_test",
                "LOG_TO_FILE": "true",
                "LOG_FILE_DIR": temp_dir,
            }

            with patch.dict(os.environ, env_vars, clear=True):
                # Create multiple loggers (simulating concurrent access)
                loggers = []
                for i in range(5):
                    logger = mypylogger.get_logger(f"concurrent_logger_{i}")
                    loggers.append(logger)

                # Log from all loggers
                for i, logger in enumerate(loggers):
                    for j in range(10):
                        logger.info("Logger %d message %d", i, j)

                # Verify all messages were logged
                log_files = list(Path(temp_dir).glob("*.log"))
                assert len(log_files) > 0

                all_content = ""
                for log_file in log_files:
                    all_content += log_file.read_text()

                lines = [line.strip() for line in all_content.split("\n") if line.strip()]
                assert len(lines) >= 50  # 5 loggers * 10 messages each

                # Verify all lines are valid JSON
                for line in lines:
                    log_entry = json.loads(line)
                    assert "message" in log_entry
                    assert "Logger" in log_entry["message"]
