"""Comprehensive tests for custom fields support functionality (Task 3.3)."""

from io import StringIO
import json
import logging
from unittest.mock import patch

from mypylogger.formatters import SourceLocationJSONFormatter


class TestCustomFieldsSupport:
    """Test custom fields support with focus on task 3.3 requirements."""

    def test_support_custom_fields_via_extra_parameter(self) -> None:
        """Test custom fields support via standard extra parameter (Requirement 6.1)."""
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

        # Add custom fields via extra parameter (standard Python logging way)
        record.user_id = 12345
        record.session_id = "abc-123"
        record.request_id = "req-456"

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

            # Should include custom fields
            assert parsed["user_id"] == 12345
            assert parsed["session_id"] == "abc-123"
            assert parsed["request_id"] == "req-456"

            # Should also include standard fields
            assert "timestamp" in parsed
            assert parsed["level"] == "INFO"
            assert parsed["message"] == "Test message"

    def test_support_custom_fields_via_custom_parameter(self) -> None:
        """Test custom fields support via custom parameter for convenience (Requirement 6.2)."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.WARNING,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add custom fields via custom parameter (convenience method)
        record.custom = {
            "operation": "user_login",
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
        }

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

            # Should include custom fields from custom parameter (flattened into main JSON)
            assert parsed["operation"] == "user_login"
            assert parsed["ip_address"] == "192.168.1.1"
            assert parsed["user_agent"] == "Mozilla/5.0"

            # Should not include the custom parameter itself as a field
            assert "custom" not in parsed

    def test_merge_custom_fields_into_json_output(self) -> None:
        """Test custom fields are merged into JSON output alongside standard fields.

        (Requirement 6.3)
        """
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=None,
        )

        # Add multiple custom fields
        record.error_code = "E001"
        record.error_category = "authentication"
        record.retry_count = 3
        record.metadata = {"source": "api", "version": "1.0"}

        with patch.object(
            formatter,
            "_extract_source_location",
            return_value={
                "module": "auth_service",
                "filename": "auth.py",
                "function_name": "authenticate",
                "line": 150,
            },
        ):
            result = formatter.format(record)
            parsed = json.loads(result)

            # Should have standard fields
            assert "timestamp" in parsed
            assert parsed["level"] == "ERROR"
            assert parsed["message"] == "Error occurred"
            assert parsed["module"] == "auth_service"
            assert parsed["filename"] == "auth.py"
            assert parsed["function_name"] == "authenticate"
            assert parsed["line"] == 150

            # Should have custom fields merged in
            assert parsed["error_code"] == "E001"
            assert parsed["error_category"] == "authentication"
            assert parsed["retry_count"] == 3
            assert parsed["metadata"] == {"source": "api", "version": "1.0"}

    def test_custom_fields_do_not_override_standard_fields(self) -> None:
        """Test custom fields cannot override standard fields (Requirement 6.4)."""
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

        # Try to override standard fields with custom fields
        record.timestamp = "fake_timestamp"
        record.level = "FAKE_LEVEL"
        record.message = "fake_message"
        record.module = "fake_module"
        record.filename = "fake_filename"
        record.function_name = "fake_function"
        record.line = 999999

        # Also add legitimate custom fields
        record.legitimate_field = "legitimate_value"

        with patch.object(
            formatter,
            "_extract_source_location",
            return_value={
                "module": "real_module",
                "filename": "real.py",
                "function_name": "real_function",
                "line": 100,
            },
        ):
            result = formatter.format(record)
            parsed = json.loads(result)

            # Standard fields should NOT be overridden by custom fields
            assert "timestamp" in parsed  # Should be real timestamp, not "fake_timestamp"
            assert parsed["level"] == "INFO"  # Should be real level, not "FAKE_LEVEL"
            assert parsed["message"] == "Test message"  # Should be real message
            assert parsed["module"] == "real_module"  # Should be from source location
            assert parsed["filename"] == "real.py"  # Should be from source location
            assert parsed["function_name"] == "real_function"  # Should be from source location
            assert parsed["line"] == 100  # Should be from source location

            # Legitimate custom field should be included
            assert parsed["legitimate_field"] == "legitimate_value"

            # Fake values should NOT appear in output
            assert parsed["timestamp"] != "fake_timestamp"
            assert parsed["level"] != "FAKE_LEVEL"
            assert parsed["message"] != "fake_message"
            assert parsed["module"] != "fake_module"
            assert parsed["filename"] != "fake_filename"
            assert parsed["function_name"] != "fake_function"
            assert parsed["line"] != 999999

    def test_handle_custom_field_serialization_errors_gracefully(self) -> None:
        """Test custom field serialization errors are handled gracefully (Requirement 6.5)."""
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

        # Add serializable and non-serializable custom fields
        record.good_field = "serializable_value"
        record.bad_field = lambda x: x  # Non-serializable function
        record.another_good_field = {"nested": "data"}

        # Add a circular reference (non-serializable)
        circular_dict = {"key": "value"}
        circular_dict["self"] = circular_dict
        record.circular_field = circular_dict

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
            # Should not raise an exception
            result = formatter.format(record)
            parsed = json.loads(result)

            # Should include serializable fields
            assert parsed["good_field"] == "serializable_value"
            assert parsed["another_good_field"] == {"nested": "data"}

            # Should exclude non-serializable fields
            assert "bad_field" not in parsed
            assert "circular_field" not in parsed

            # Should still have standard fields
            assert "timestamp" in parsed
            assert parsed["level"] == "INFO"
            assert parsed["message"] == "Test message"

    def test_custom_fields_with_various_data_types(self) -> None:
        """Test custom fields support various JSON-serializable data types."""
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

        # Add custom fields with various data types
        record.string_field = "string_value"
        record.int_field = 42
        record.float_field = 3.14
        record.bool_field = True
        record.none_field = None
        record.list_field = [1, 2, 3, "four"]
        record.dict_field = {"nested": {"deep": "value"}}

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

            # Should include all serializable data types
            assert parsed["string_field"] == "string_value"
            assert parsed["int_field"] == 42
            assert parsed["float_field"] == 3.14
            assert parsed["bool_field"] is True
            assert parsed["none_field"] is None
            assert parsed["list_field"] == [1, 2, 3, "four"]
            assert parsed["dict_field"] == {"nested": {"deep": "value"}}

    def test_custom_fields_exclude_standard_logging_fields(self) -> None:
        """Test that standard logging fields are excluded from custom fields."""
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

        # Add a legitimate custom field
        record.custom_field = "custom_value"

        custom_fields = formatter._handle_custom_fields(record)

        # Should include custom field
        assert custom_fields["custom_field"] == "custom_value"

        # Should exclude standard logging fields
        standard_fields = [
            "name",
            "levelname",
            "levelno",
            "pathname",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "stack_info",
            "exc_info",
            "exc_text",
            "msg",
            "args",
        ]

        for field in standard_fields:
            assert field not in custom_fields

    def test_custom_fields_integration_with_real_logging(self) -> None:
        """Test custom fields integration with real Python logging calls."""
        formatter = SourceLocationJSONFormatter()

        # Create a logger with our formatter
        logger = logging.getLogger("test_custom_fields")
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Capture the output
        captured_output = StringIO()
        handler.stream = captured_output

        # Log with custom fields using extra parameter
        logger.info(
            "User action performed",
            extra={
                "user_id": 12345,
                "action": "login",
                "ip_address": "192.168.1.100",
                "success": True,
            },
        )

        # Get the output and parse it
        output = captured_output.getvalue().strip()
        parsed = json.loads(output)

        # Should have standard fields
        assert "timestamp" in parsed
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "User action performed"

        # Should have custom fields from extra
        assert parsed["user_id"] == 12345
        assert parsed["action"] == "login"
        assert parsed["ip_address"] == "192.168.1.100"
        assert parsed["success"] is True

        # Clean up
        logger.removeHandler(handler)

    def test_empty_custom_fields(self) -> None:
        """Test handling when no custom fields are provided."""
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

        # No custom fields added to record

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

            # Should only have standard fields
            expected_fields = {
                "timestamp",
                "level",
                "message",
                "module",
                "filename",
                "function_name",
                "line",
            }
            assert set(parsed.keys()) == expected_fields

    def test_custom_fields_with_unicode_and_special_characters(self) -> None:
        """Test custom fields with Unicode and special characters."""
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

        # Add custom fields with Unicode and special characters
        record.unicode_field = "Hello 世界 🌍"
        record.special_chars = "Special: !@#$%^&*()_+-=[]{}|;':\",./<>?"
        record.emoji_field = "🚀 🎉 ✅"

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

            # Should handle Unicode and special characters correctly
            assert parsed["unicode_field"] == "Hello 世界 🌍"
            assert parsed["special_chars"] == "Special: !@#$%^&*()_+-=[]{}|;':\",./<>?"
            assert parsed["emoji_field"] == "🚀 🎉 ✅"
