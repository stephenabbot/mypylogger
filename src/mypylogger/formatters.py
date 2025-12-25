"""JSON formatters with source location tracking for mypylogger."""

from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from types import FrameType

# Constants
MAX_STACK_FRAMES = 20  # Safety limit to prevent infinite loops


class SourceLocationJSONFormatter(logging.Formatter):
    """JSON formatter with automatic source location tracking."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with source location fields.

        Args:
            record: LogRecord instance to format.

        Returns:
            JSON-formatted log string.
        """
        try:
            # Extract source location information
            location = self._extract_source_location(record)

            # Build the JSON record with consistent field ordering
            json_record = self._build_json_record(record, location)

            # Handle custom fields from extra and custom parameters
            custom_fields = self._handle_custom_fields(record)
            json_record.update(custom_fields)

            # Serialize to JSON - this is the most likely point of failure
            try:
                return json.dumps(json_record, ensure_ascii=False, separators=(",", ":"))
            except (TypeError, ValueError, RecursionError) as json_error:
                # Specific JSON serialization error handling (Requirement 5.2)
                self._log_formatting_error(f"JSON serialization failed: {json_error}")
                return self._fallback_to_plain_text(record)
            except Exception as json_error:
                # Catch-all for any other JSON-related errors
                self._log_formatting_error(f"Unexpected JSON error: {json_error}")
                return self._fallback_to_plain_text(record)

        except Exception as e:
            # Graceful fallback for any other formatting errors (Requirement 5.2)
            self._log_formatting_error(f"JSON formatting failed: {e}")
            return self._fallback_to_plain_text(record)

    def _extract_source_location(self, record: logging.LogRecord) -> dict[str, Any]:
        """Extract module, filename, function_name, and line from call stack.

        Args:
            record: LogRecord instance containing call information.

        Returns:
            Dictionary with source location fields.
        """
        try:
            # Start from the current frame and walk up the stack
            frame: FrameType | None = sys._getframe()

            # Skip frames until we find the actual user code that made the logging call
            # We need to skip: this method, format method, logging internals
            skip_count = 0
            while frame and skip_count < MAX_STACK_FRAMES:
                filename = frame.f_code.co_filename
                function_name = frame.f_code.co_name

                # Skip logging internals and our own formatter methods
                if not self._is_logging_internal(filename) and function_name not in [
                    "format",
                    "_extract_source_location",
                    "_build_json_record",
                ]:
                    # This should be the user code that called the logger
                    module_name = frame.f_globals.get("__name__", "unknown")
                    relative_filename = self._get_relative_filename(frame.f_code.co_filename)
                    line_number = frame.f_lineno

                    return {
                        "module": module_name,
                        "filename": relative_filename,
                        "function_name": function_name,
                        "line": line_number,
                    }

                frame = frame.f_back
                skip_count += 1

            # If we couldn't find a suitable frame, fall back to record information
            module_name = getattr(record, "name", "unknown")
            filename = self._get_relative_filename(getattr(record, "pathname", "unknown"))
            function_name = getattr(record, "funcName", None) or "unknown"
            line_number = getattr(record, "lineno", 0)

            return {
                "module": module_name,
                "filename": filename,
                "function_name": function_name,
                "line": line_number,
            }

        except Exception:
            # Fallback to basic information
            return {
                "module": "unknown",
                "filename": "unknown",
                "function_name": "unknown",
                "line": 0,
            }

    def _build_json_record(
        self, record: logging.LogRecord, location: dict[str, Any]
    ) -> dict[str, Any]:
        """Build ordered JSON record with consistent field ordering.

        Args:
            record: LogRecord instance.
            location: Source location information.

        Returns:
            Ordered dictionary for JSON output.
        """
        # Consistent field ordering with timestamp first
        return {
            "timestamp": self._format_timestamp(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": location["module"],
            "filename": location["filename"],
            "function_name": location["function_name"],
            "line": location["line"],
        }

    def _format_timestamp(self, record: logging.LogRecord) -> str:
        """Format timestamp in ISO 8601 format with microsecond precision.

        Args:
            record: LogRecord instance.

        Returns:
            ISO 8601 formatted timestamp string.
        """
        # Convert the record's created timestamp to datetime
        dt = datetime.datetime.fromtimestamp(record.created, tz=datetime.timezone.utc)

        # Format with microsecond precision
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    def _handle_custom_fields(self, record: logging.LogRecord) -> dict[str, Any]:
        """Extract and merge custom fields from extra and custom parameters.

        Args:
            record: LogRecord instance.

        Returns:
            Dictionary of custom fields to merge into JSON output.
        """
        custom_fields = {}

        # Standard fields that should not be overridden
        standard_fields = {
            "timestamp",
            "level",
            "message",
            "module",
            "filename",
            "function_name",
            "line",
            "name",
            "msg",
            "args",
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
            "taskName",  # pytest-related field
            "custom",  # Don't include the custom parameter itself as a field
        }

        # Handle custom parameter for convenience (Requirement 6.2)
        if hasattr(record, "custom") and isinstance(record.custom, dict):
            for key, value in record.custom.items():
                if key not in standard_fields:
                    try:
                        # Ensure the value is JSON serializable
                        json.dumps(value)
                        custom_fields[key] = value
                    except (TypeError, ValueError, RecursionError) as e:
                        # Skip non-serializable values gracefully (Requirement 6.5)
                        self._log_formatting_error(
                            f"Skipping non-serializable custom field '{key}': {e}"
                        )
                        continue
                    except Exception as e:
                        # Catch-all for any other serialization errors
                        self._log_formatting_error(
                            f"Unexpected error with custom field '{key}': {e}"
                        )
                        continue

        # Extract custom fields from record.__dict__ (extra parameter support - Requirement 6.1)
        for key, value in record.__dict__.items():
            if key not in standard_fields:
                try:
                    # Ensure the value is JSON serializable
                    json.dumps(value)
                    custom_fields[key] = value
                except (TypeError, ValueError, RecursionError) as e:
                    # Skip non-serializable values gracefully (Requirement 6.5)
                    self._log_formatting_error(
                        f"Skipping non-serializable extra field '{key}': {e}"
                    )
                    continue
                except Exception as e:
                    # Catch-all for any other serialization errors
                    self._log_formatting_error(f"Unexpected error with extra field '{key}': {e}")
                    continue

        return custom_fields

    def _is_logging_internal(self, filename: str) -> bool:
        """Check if filename is part of logging internals.

        Args:
            filename: File path to check.

        Returns:
            True if file is part of logging internals.
        """
        logging_paths = [
            "logging/__init__.py",
            "logging/handlers.py",
            "/logging/__init__.py",
            "/logging/handlers.py",
            "mypylogger/formatters.py",
            "mypylogger/core.py",
            "mypylogger/handlers.py",
            "/mypylogger/",
        ]

        return any(path in filename for path in logging_paths)

    def _get_relative_filename(self, filepath: str) -> str:
        """Convert absolute filepath to relative path.

        Args:
            filepath: Absolute file path.

        Returns:
            Relative file path.
        """
        try:
            path = Path(filepath)
            # Try to make it relative to current working directory
            try:
                return str(path.relative_to(Path.cwd()))
            except ValueError:
                # If not under cwd, just return the filename
                return path.name
        except Exception:
            return filepath

    def _fallback_to_plain_text(self, record: logging.LogRecord) -> str:
        """Fallback to plain text formatting when JSON formatting fails.

        Args:
            record: LogRecord instance to format.

        Returns:
            Plain text formatted log string.
        """
        try:
            # Try to get the formatted message safely
            message = record.getMessage()
        except Exception:
            # If even getMessage() fails, use the raw msg
            message = str(getattr(record, "msg", ""))

        # Return simple plain text format (Requirement 5.2)
        return f"{record.levelname}: {message}"

    def _log_formatting_error(self, message: str) -> None:
        """Log formatting errors to stderr without affecting user logging.

        Args:
            message: Error message to log.
        """
        try:
            print(f"mypylogger: {message}", file=sys.stderr)
        except OSError:
            # If stderr is not available or fails, silently continue
            # This is intentional to prevent mypylogger from crashing user applications
            pass
