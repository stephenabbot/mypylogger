"""Unit tests for SourceLocationJSONFormatter functionality."""

import datetime
import json
import logging
from pathlib import Path
import sys
import tempfile
from types import FrameType
from unittest.mock import Mock, patch

from mypylogger.formatters import SourceLocationJSONFormatter


class TestSourceLocationJSONFormatter:
    """Test SourceLocationJSONFormatter class."""

    def test_formatter_initialization(self) -> None:
        """Test formatter initializes correctly."""
        formatter = SourceLocationJSONFormatter()
        assert isinstance(formatter, logging.Formatter)

    def test_format_basic_record(self) -> None:
        """Test formatting a basic log record."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        # Should be valid JSON
        parsed = json.loads(result)

        # Check required fields
        assert "timestamp" in parsed
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Test message"
        assert "module" in parsed
        assert "filename" in parsed
        assert "function_name" in parsed
        assert "line" in parsed

    def test_format_with_args(self) -> None:
        """Test formatting a log record with message arguments."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.DEBUG,
            pathname="/path/to/test.py",
            lineno=100,
            msg="Test message with %s and %d",
            args=("string", 123),
            exc_info=None,
        )

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["level"] == "DEBUG"
        assert parsed["message"] == "Test message with string and 123"

    def test_format_with_custom_fields(self) -> None:
        """Test formatting with custom fields in extra parameter."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.WARNING,
            pathname="/path/to/test.py",
            lineno=200,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add custom fields to record
        record.user_id = 12345
        record.request_id = "abc-123"
        record.custom_data = {"key": "value"}

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["level"] == "WARNING"
        assert parsed["message"] == "Test message"
        assert parsed["user_id"] == 12345
        assert parsed["request_id"] == "abc-123"
        assert parsed["custom_data"] == {"key": "value"}

    def test_format_exception_fallback(self) -> None:
        """Test formatter falls back to plain text on JSON errors."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="/path/to/test.py",
            lineno=300,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        with patch.object(formatter, "_build_json_record", side_effect=Exception("JSON error")):
            with patch.object(formatter, "_log_formatting_error") as mock_log_error:
                result = formatter.format(record)

                assert result == "ERROR: Test message"
                mock_log_error.assert_called_once()

    def test_format_json_serialization_error_fallback(self) -> None:
        """Test formatter falls back to plain text on JSON serialization errors."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.WARNING,
            pathname="/path/to/test.py",
            lineno=400,
            msg="Test message with serialization error",
            args=(),
            exc_info=None,
        )

        # Mock json.dumps to raise TypeError (common JSON serialization error)
        with patch("json.dumps", side_effect=TypeError("Object not serializable")):
            with patch.object(formatter, "_log_formatting_error") as mock_log_error:
                result = formatter.format(record)

                assert result == "WARNING: Test message with serialization error"
                mock_log_error.assert_called_once()
                assert "JSON serialization failed" in mock_log_error.call_args[0][0]

    def test_format_json_value_error_fallback(self) -> None:
        """Test formatter falls back to plain text on JSON ValueError."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=500,
            msg="Test message with value error",
            args=(),
            exc_info=None,
        )

        # Mock json.dumps to raise ValueError
        with patch("json.dumps", side_effect=ValueError("Invalid JSON value")):
            with patch.object(formatter, "_log_formatting_error") as mock_log_error:
                result = formatter.format(record)

                assert result == "INFO: Test message with value error"
                mock_log_error.assert_called_once()
                assert "JSON serialization failed" in mock_log_error.call_args[0][0]

    def test_format_json_recursion_error_fallback(self) -> None:
        """Test formatter falls back to plain text on JSON RecursionError."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.CRITICAL,
            pathname="/path/to/test.py",
            lineno=600,
            msg="Test message with recursion error",
            args=(),
            exc_info=None,
        )

        # Mock json.dumps to raise RecursionError
        with patch("json.dumps", side_effect=RecursionError("Maximum recursion depth exceeded")):
            with patch.object(formatter, "_log_formatting_error") as mock_log_error:
                result = formatter.format(record)

                assert result == "CRITICAL: Test message with recursion error"
                mock_log_error.assert_called_once()
                assert "JSON serialization failed" in mock_log_error.call_args[0][0]

    def test_extract_source_location_with_frame(self) -> None:
        """Test source location extraction with frame inspection."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Mock frame
        mock_frame = Mock(spec=FrameType)
        mock_frame.f_code.co_filename = "/path/to/caller.py"
        mock_frame.f_code.co_name = "test_function"
        mock_frame.f_lineno = 100
        mock_frame.f_globals = {"__name__": "test_module"}
        mock_frame.f_back = None

        with patch("sys._getframe", return_value=mock_frame):
            with patch.object(formatter, "_is_logging_internal", return_value=False):
                with patch.object(formatter, "_get_relative_filename", return_value="caller.py"):
                    location = formatter._extract_source_location(record)

                    assert location["module"] == "test_module"
                    assert location["filename"] == "caller.py"
                    assert location["function_name"] == "test_function"
                    assert location["line"] == 100

    def test_extract_source_location_skip_logging_internals(self) -> None:
        """Test source location extraction skips logging internal frames."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Mock frame chain: logging internal -> user code
        user_frame = Mock(spec=FrameType)
        user_frame.f_code.co_filename = "/path/to/user.py"
        user_frame.f_code.co_name = "user_function"
        user_frame.f_lineno = 100
        user_frame.f_globals = {"__name__": "user_module"}
        user_frame.f_back = None

        logging_frame = Mock(spec=FrameType)
        logging_frame.f_code.co_filename = "/python/logging/__init__.py"
        logging_frame.f_back = user_frame

        with patch("sys._getframe", return_value=logging_frame):
            with patch.object(formatter, "_get_relative_filename", return_value="user.py"):
                location = formatter._extract_source_location(record)

                assert location["module"] == "user_module"
                assert location["filename"] == "user.py"
                assert location["function_name"] == "user_function"
                assert location["line"] == 100

    def test_extract_source_location_fallback_to_record(self) -> None:
        """Test source location extraction falls back to record when no valid frame."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.funcName = "record_function"

        with patch("sys._getframe", return_value=None):
            with patch.object(formatter, "_get_relative_filename", return_value="test.py"):
                location = formatter._extract_source_location(record)

                assert location["module"] == "test_logger"  # Uses record.name as fallback
                assert location["filename"] == "test.py"
                assert location["function_name"] == "record_function"
                assert location["line"] == 42

    def test_extract_source_location_exception_fallback(self) -> None:
        """Test source location extraction handles exceptions gracefully."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        with patch("sys._getframe", side_effect=Exception("Frame error")):
            location = formatter._extract_source_location(record)

            assert location["module"] == "unknown"
            assert location["filename"] == "unknown"
            assert location["function_name"] == "unknown"
            assert location["line"] == 0

    def test_build_json_record_field_ordering(self) -> None:
        """Test JSON record has consistent field ordering."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        location = {
            "module": "test_module",
            "filename": "test.py",
            "function_name": "test_function",
            "line": 42,
        }

        json_record = formatter._build_json_record(record, location)

        # Check field ordering (timestamp should be first)
        keys = list(json_record.keys())
        assert keys[0] == "timestamp"
        assert "level" in keys
        assert "message" in keys
        assert "module" in keys
        assert "filename" in keys
        assert "function_name" in keys
        assert "line" in keys

    def test_handle_custom_fields_basic(self) -> None:
        """Test custom fields extraction from record."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add custom fields
        record.user_id = 123
        record.session_id = "abc-123"
        record.custom_data = {"key": "value"}

        custom_fields = formatter._handle_custom_fields(record)

        assert custom_fields["user_id"] == 123
        assert custom_fields["session_id"] == "abc-123"
        assert custom_fields["custom_data"] == {"key": "value"}

    def test_handle_custom_fields_excludes_standard_fields(self) -> None:
        """Test custom fields extraction excludes standard logging fields."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add custom field
        record.custom_field = "custom_value"

        custom_fields = formatter._handle_custom_fields(record)

        # Should include custom field
        assert custom_fields["custom_field"] == "custom_value"

        # Should exclude standard fields
        assert "name" not in custom_fields
        assert "levelname" not in custom_fields
        assert "pathname" not in custom_fields
        assert "lineno" not in custom_fields

    def test_handle_custom_fields_non_serializable(self) -> None:
        """Test custom fields handles non-JSON-serializable values."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add serializable and non-serializable fields
        record.good_field = "serializable"
        record.bad_field = lambda x: x  # Non-serializable function

        with patch.object(formatter, "_log_formatting_error") as mock_log_error:
            custom_fields = formatter._handle_custom_fields(record)

            # Should include serializable field
            assert custom_fields["good_field"] == "serializable"

            # Should exclude non-serializable field
            assert "bad_field" not in custom_fields

            # Should log the error
            mock_log_error.assert_called_once()
            assert "non-serializable extra field 'bad_field'" in mock_log_error.call_args[0][0]

    def test_handle_custom_fields_custom_parameter_non_serializable(self) -> None:
        """Test custom parameter handles non-JSON-serializable values."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add custom parameter with serializable and non-serializable values
        record.custom = {
            "good_field": "serializable",
            "bad_field": lambda x: x,  # Non-serializable function
        }

        with patch.object(formatter, "_log_formatting_error") as mock_log_error:
            custom_fields = formatter._handle_custom_fields(record)

            # Should include serializable field
            assert custom_fields["good_field"] == "serializable"

            # Should exclude non-serializable field
            assert "bad_field" not in custom_fields

            # Should log the error
            mock_log_error.assert_called_once()
            assert "non-serializable custom field 'bad_field'" in mock_log_error.call_args[0][0]

    def test_handle_custom_fields_recursion_error(self) -> None:
        """Test custom fields handles RecursionError gracefully."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Create a circular reference that would cause RecursionError
        circular_dict = {}
        circular_dict["self"] = circular_dict
        record.circular_field = circular_dict

        with patch.object(formatter, "_log_formatting_error") as mock_log_error:
            custom_fields = formatter._handle_custom_fields(record)

            # Should exclude the problematic field
            assert "circular_field" not in custom_fields

            # Should log the error
            mock_log_error.assert_called_once()
            assert "non-serializable extra field 'circular_field'" in mock_log_error.call_args[0][0]

    def test_handle_custom_fields_unexpected_error(self) -> None:
        """Test custom fields handles unexpected errors gracefully."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        record.problem_field = "normal_value"

        # Mock json.dumps to raise an unexpected error for this specific field
        original_dumps = json.dumps

        def mock_dumps(obj: object, **kwargs: object) -> str:
            if obj == "normal_value":
                error_msg = "Unexpected error"
                raise RuntimeError(error_msg)
            return original_dumps(obj, **kwargs)

        with patch("json.dumps", side_effect=mock_dumps):
            with patch.object(formatter, "_log_formatting_error") as mock_log_error:
                custom_fields = formatter._handle_custom_fields(record)

                # Should exclude the problematic field
                assert "problem_field" not in custom_fields

                # Should log the unexpected error
                mock_log_error.assert_called_once()
                assert (
                    "Unexpected error with extra field 'problem_field'"
                    in mock_log_error.call_args[0][0]
                )

    def test_is_logging_internal_true(self) -> None:
        """Test _is_logging_internal identifies logging internal files."""
        formatter = SourceLocationJSONFormatter()

        internal_paths = [
            "/python/logging/__init__.py",
            "/python/logging/handlers.py",
            "/path/to/mypylogger/core.py",
            "/path/to/mypylogger/formatters.py",
        ]

        for path in internal_paths:
            assert formatter._is_logging_internal(path) is True

    def test_is_logging_internal_false(self) -> None:
        """Test _is_logging_internal identifies user code files."""
        formatter = SourceLocationJSONFormatter()

        user_paths = [
            "/path/to/user/code.py",
            "/app/main.py",
            "/project/src/module.py",
            "/home/user/script.py",
        ]

        for path in user_paths:
            assert formatter._is_logging_internal(path) is False

    def test_get_relative_filename_under_cwd(self) -> None:
        """Test _get_relative_filename with file under current directory."""
        formatter = SourceLocationJSONFormatter()

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.touch()

            with patch("pathlib.Path.cwd", return_value=Path(temp_dir)):
                result = formatter._get_relative_filename(str(test_file))
                assert result == "test.py"

    def test_get_relative_filename_outside_cwd(self) -> None:
        """Test _get_relative_filename with file outside current directory."""
        formatter = SourceLocationJSONFormatter()

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.touch()

            # Use a different directory as cwd
            with tempfile.TemporaryDirectory() as other_dir:
                with patch("pathlib.Path.cwd", return_value=Path(other_dir)):
                    result = formatter._get_relative_filename(str(test_file))
                    assert result == "test.py"  # Should return just filename

    def test_get_relative_filename_exception_handling(self) -> None:
        """Test _get_relative_filename handles exceptions gracefully."""
        formatter = SourceLocationJSONFormatter()

        with patch("mypylogger.formatters.Path", side_effect=Exception("Path error")):
            result = formatter._get_relative_filename("/path/to/file.py")
            assert result == "/path/to/file.py"  # Should return original path

    def test_log_formatting_error_success(self) -> None:
        """Test _log_formatting_error prints to stderr successfully."""
        formatter = SourceLocationJSONFormatter()

        with patch("builtins.print") as mock_print:
            formatter._log_formatting_error("Test error message")

            mock_print.assert_called_once()
            args, kwargs = mock_print.call_args
            assert "mypylogger: Test error message" in args
            assert kwargs.get("file") is sys.stderr

    def test_log_formatting_error_exception_handling(self) -> None:
        """Test _log_formatting_error handles print exceptions gracefully."""
        formatter = SourceLocationJSONFormatter()

        with patch("builtins.print", side_effect=OSError("Print error")):
            # Should not raise an exception
            formatter._log_formatting_error("Test error message")

    def test_format_timestamp_format(self) -> None:
        """Test that timestamp is formatted correctly."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        with patch.object(
            formatter,
            "_extract_source_location",
            return_value={
                "module": "test",
                "filename": "test.py",
                "function_name": "test",
                "line": 1,
            },
        ):
            result = formatter.format(record)
            parsed = json.loads(result)

            timestamp = parsed["timestamp"]
            # Should be ISO format with microseconds
            assert "T" in timestamp
            assert timestamp.endswith("Z")
            assert "." in timestamp  # Should have microseconds

            # Should be parseable as ISO format
            parsed_dt = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            assert isinstance(parsed_dt, datetime.datetime)

    def test_format_timestamp_method(self) -> None:
        """Test the _format_timestamp method directly."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        timestamp = formatter._format_timestamp(record)

        # Should be ISO format with microseconds
        assert "T" in timestamp
        assert timestamp.endswith("Z")
        assert "." in timestamp

        # Should be parseable as ISO format
        parsed_dt = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert isinstance(parsed_dt, datetime.datetime)

    def test_format_json_output_structure(self) -> None:
        """Test that JSON output has expected structure and no extra fields."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        with patch.object(
            formatter,
            "_extract_source_location",
            return_value={
                "module": "test",
                "filename": "test.py",
                "function_name": "test",
                "line": 1,
            },
        ):
            result = formatter.format(record)
            parsed = json.loads(result)

            # Should have at least these base fields
            required_fields = {
                "timestamp",
                "level",
                "message",
                "module",
                "filename",
                "function_name",
                "line",
            }
            assert required_fields.issubset(set(parsed.keys()))

    def test_fallback_to_plain_text_basic(self) -> None:
        """Test _fallback_to_plain_text method with basic record."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test error message",
            args=(),
            exc_info=None,
        )

        result = formatter._fallback_to_plain_text(record)
        assert result == "ERROR: Test error message"

    def test_fallback_to_plain_text_with_args(self) -> None:
        """Test _fallback_to_plain_text method with message arguments."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.WARNING,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test message with %s and %d",
            args=("string", 123),
            exc_info=None,
        )

        result = formatter._fallback_to_plain_text(record)
        assert result == "WARNING: Test message with string and 123"

    def test_fallback_to_plain_text_get_message_exception(self) -> None:
        """Test _fallback_to_plain_text handles getMessage() exceptions."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Mock getMessage to raise an exception
        with patch.object(record, "getMessage", side_effect=Exception("getMessage error")):
            result = formatter._fallback_to_plain_text(record)
            assert result == "INFO: Test message"  # Should use raw msg
