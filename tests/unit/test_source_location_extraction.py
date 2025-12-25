"""Comprehensive tests for source location extraction functionality."""

import json
import logging
from pathlib import Path
import tempfile
from types import FrameType
from unittest.mock import Mock, patch

from mypylogger.formatters import SourceLocationJSONFormatter


class TestSourceLocationExtraction:
    """Test source location extraction with focus on task 3.2 requirements."""

    def test_extract_module_name_from_call_stack(self) -> None:
        """Test extraction of module name from call stack (Requirement 8.1)."""
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

        # Mock frame with specific module name
        mock_frame = Mock(spec=FrameType)
        mock_frame.f_code.co_filename = "/path/to/user_module.py"
        mock_frame.f_code.co_name = "user_function"
        mock_frame.f_lineno = 100
        mock_frame.f_globals = {"__name__": "myapp.services.auth"}
        mock_frame.f_back = None

        with patch("sys._getframe", return_value=mock_frame):
            with patch.object(formatter, "_is_logging_internal", return_value=False):
                location = formatter._extract_source_location(record)

                assert location["module"] == "myapp.services.auth"

    def test_extract_relative_filename_from_call_stack(self) -> None:
        """Test extraction of relative filename from call stack (Requirement 8.2)."""
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

        # Mock frame with absolute path
        mock_frame = Mock(spec=FrameType)
        mock_frame.f_code.co_filename = "/absolute/path/to/services/auth.py"
        mock_frame.f_code.co_name = "authenticate"
        mock_frame.f_lineno = 150
        mock_frame.f_globals = {"__name__": "services.auth"}
        mock_frame.f_back = None

        with patch("sys._getframe", return_value=mock_frame):
            with patch.object(formatter, "_is_logging_internal", return_value=False):
                with patch.object(
                    formatter, "_get_relative_filename", return_value="services/auth.py"
                ):
                    location = formatter._extract_source_location(record)

                    assert location["filename"] == "services/auth.py"

    def test_extract_function_name_from_call_stack(self) -> None:
        """Test extraction of function name from call stack (Requirement 8.3)."""
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

        # Mock frame with specific function name
        mock_frame = Mock(spec=FrameType)
        mock_frame.f_code.co_filename = "/path/to/user_code.py"
        mock_frame.f_code.co_name = "process_user_request"
        mock_frame.f_lineno = 200
        mock_frame.f_globals = {"__name__": "user_module"}
        mock_frame.f_back = None

        with patch("sys._getframe", return_value=mock_frame):
            with patch.object(formatter, "_is_logging_internal", return_value=False):
                location = formatter._extract_source_location(record)

                assert location["function_name"] == "process_user_request"

    def test_extract_line_number_from_call_stack(self) -> None:
        """Test extraction of line number from call stack (Requirement 8.4)."""
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

        # Mock frame with specific line number
        mock_frame = Mock(spec=FrameType)
        mock_frame.f_code.co_filename = "/path/to/user_code.py"
        mock_frame.f_code.co_name = "user_function"
        mock_frame.f_lineno = 999
        mock_frame.f_globals = {"__name__": "user_module"}
        mock_frame.f_back = None

        with patch("sys._getframe", return_value=mock_frame):
            with patch.object(formatter, "_is_logging_internal", return_value=False):
                location = formatter._extract_source_location(record)

                assert location["line"] == 999

    def test_source_location_with_nested_function_calls(self) -> None:
        """Test source location works correctly with nested calls (Requirement 8.5)."""
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

        # Create a chain of frames: logging internal -> user code level 1 -> user code level 2
        user_frame_level_2 = Mock(spec=FrameType)
        user_frame_level_2.f_code.co_filename = "/path/to/level2.py"
        user_frame_level_2.f_code.co_name = "level_2_function"
        user_frame_level_2.f_lineno = 50
        user_frame_level_2.f_globals = {"__name__": "level2_module"}
        user_frame_level_2.f_back = None

        user_frame_level_1 = Mock(spec=FrameType)
        user_frame_level_1.f_code.co_filename = "/path/to/level1.py"
        user_frame_level_1.f_code.co_name = "level_1_function"
        user_frame_level_1.f_lineno = 25
        user_frame_level_1.f_globals = {"__name__": "level1_module"}
        user_frame_level_1.f_back = user_frame_level_2

        logging_frame = Mock(spec=FrameType)
        logging_frame.f_code.co_filename = "/python/logging/__init__.py"
        logging_frame.f_code.co_name = "info"
        logging_frame.f_back = user_frame_level_1

        with patch("sys._getframe", return_value=logging_frame):
            with patch.object(formatter, "_get_relative_filename", return_value="level1.py"):
                location = formatter._extract_source_location(record)

                # Should extract from the first non-logging frame (level_1_function)
                assert location["module"] == "level1_module"
                assert location["filename"] == "level1.py"
                assert location["function_name"] == "level_1_function"
                assert location["line"] == 25

    def test_relative_path_conversion_under_cwd(self) -> None:
        """Test relative path conversion for files under current working directory."""
        formatter = SourceLocationJSONFormatter()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a nested directory structure
            nested_dir = Path(temp_dir) / "src" / "myapp"
            nested_dir.mkdir(parents=True)
            test_file = nested_dir / "module.py"
            test_file.touch()

            with patch("pathlib.Path.cwd", return_value=Path(temp_dir)):
                result = formatter._get_relative_filename(str(test_file))
                assert result == "src/myapp/module.py"

    def test_relative_path_conversion_outside_cwd(self) -> None:
        """Test relative path conversion for files outside current working directory."""
        formatter = SourceLocationJSONFormatter()

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "external_module.py"
            test_file.touch()

            # Use a different directory as cwd
            with tempfile.TemporaryDirectory() as other_dir:
                with patch("pathlib.Path.cwd", return_value=Path(other_dir)):
                    result = formatter._get_relative_filename(str(test_file))
                    # Should return just the filename when outside cwd
                    assert result == "external_module.py"

    def test_call_stack_inspection_skips_formatter_methods(self) -> None:
        """Test that call stack inspection correctly skips formatter internal methods."""
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

        # Create frame chain: format -> _extract_source_location -> user code
        user_frame = Mock(spec=FrameType)
        user_frame.f_code.co_filename = "/path/to/user.py"
        user_frame.f_code.co_name = "user_function"
        user_frame.f_lineno = 100
        user_frame.f_globals = {"__name__": "user_module"}
        user_frame.f_back = None

        extract_frame = Mock(spec=FrameType)
        extract_frame.f_code.co_filename = "/path/to/mypylogger/formatters.py"
        extract_frame.f_code.co_name = "_extract_source_location"
        extract_frame.f_back = user_frame

        format_frame = Mock(spec=FrameType)
        format_frame.f_code.co_filename = "/path/to/mypylogger/formatters.py"
        format_frame.f_code.co_name = "format"
        format_frame.f_back = extract_frame

        with patch("sys._getframe", return_value=format_frame):
            with patch.object(formatter, "_get_relative_filename", return_value="user.py"):
                location = formatter._extract_source_location(record)

                # Should skip formatter methods and find user code
                assert location["module"] == "user_module"
                assert location["function_name"] == "user_function"

    def test_call_stack_inspection_max_frames_safety(self) -> None:
        """Test that call stack inspection has safety limit to prevent infinite loops."""
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

        # Create a very long chain of logging internal frames
        def create_frame_chain(depth: int) -> Mock:
            if depth <= 0:
                return None

            frame = Mock(spec=FrameType)
            frame.f_code.co_filename = "/python/logging/__init__.py"
            frame.f_code.co_name = f"logging_function_{depth}"
            frame.f_back = create_frame_chain(depth - 1)
            return frame

        # Create a chain longer than MAX_STACK_FRAMES
        long_chain = create_frame_chain(25)  # MAX_STACK_FRAMES is 20

        with patch("sys._getframe", return_value=long_chain):
            with patch.object(formatter, "_get_relative_filename", return_value="test.py"):
                location = formatter._extract_source_location(record)

                # Should fall back to record information when max frames exceeded
                assert location["module"] == "test_logger"  # From record.name
                assert location["filename"] == "test.py"
                assert location["function_name"] == "unknown"  # Default fallback
                assert location["line"] == 42  # From record.lineno

    def test_source_location_integration_with_format(self) -> None:
        """Test that source location extraction integrates correctly with format method."""
        formatter = SourceLocationJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Integration test message",
            args=(),
            exc_info=None,
        )

        # Mock a realistic frame
        mock_frame = Mock(spec=FrameType)
        mock_frame.f_code.co_filename = "/project/src/services/auth.py"
        mock_frame.f_code.co_name = "authenticate_user"
        mock_frame.f_lineno = 150
        mock_frame.f_globals = {"__name__": "services.auth"}
        mock_frame.f_back = None

        with patch("sys._getframe", return_value=mock_frame):
            with patch.object(formatter, "_is_logging_internal", return_value=False):
                with patch.object(
                    formatter, "_get_relative_filename", return_value="src/services/auth.py"
                ):
                    result = formatter.format(record)

                    # Parse the JSON output
                    parsed = json.loads(result)

                    # Verify all source location fields are present and correct
                    assert parsed["module"] == "services.auth"
                    assert parsed["filename"] == "src/services/auth.py"
                    assert parsed["function_name"] == "authenticate_user"
                    assert parsed["line"] == 150
                    assert parsed["message"] == "Integration test message"
                    assert parsed["level"] == "INFO"

    def test_source_location_handles_missing_globals(self) -> None:
        """Test source location extraction handles frames with missing __name__ in globals."""
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

        # Mock frame without __name__ in globals
        mock_frame = Mock(spec=FrameType)
        mock_frame.f_code.co_filename = "/path/to/user.py"
        mock_frame.f_code.co_name = "user_function"
        mock_frame.f_lineno = 100
        mock_frame.f_globals = {}  # No __name__ key
        mock_frame.f_back = None

        with patch("sys._getframe", return_value=mock_frame):
            with patch.object(formatter, "_is_logging_internal", return_value=False):
                with patch.object(formatter, "_get_relative_filename", return_value="user.py"):
                    location = formatter._extract_source_location(record)

                    assert location["module"] == "unknown"  # Fallback when __name__ missing
                    assert location["filename"] == "user.py"
                    assert location["function_name"] == "user_function"
                    assert location["line"] == 100
