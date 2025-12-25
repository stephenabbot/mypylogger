#!/usr/bin/env python3
"""Comprehensive error handling for PyPI publishing workflow.

This module provides error handling, retry logic with exponential backoff,
and failure notification mechanisms for the PyPI publishing workflow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Callable


class ErrorCategory(Enum):
    """Categories of publishing errors."""

    AUTHENTICATION = "authentication"
    NETWORK = "network"
    VALIDATION = "validation"
    BUILD = "build"
    UPLOAD = "upload"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Severity levels for errors."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PublishingError:
    """Represents a publishing error with context."""

    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: str = ""
    command: str | None = None
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    timestamp: float = field(default_factory=time.time)
    retry_count: int = 0
    max_retries: int = 3
    is_retryable: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for JSON serialization."""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "command": self.command,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "timestamp": self.timestamp,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "is_retryable": self.is_retryable,
        }


class RetryConfig:
    """Configuration for retry logic with exponential backoff."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
    ) -> None:
        """Initialize retry configuration.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            backoff_factor: Exponential backoff factor
            jitter: Whether to add random jitter to delays
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number.

        Args:
            attempt: Current attempt number (0-based)

        Returns:
            Delay in seconds
        """
        delay = self.base_delay * (self.backoff_factor**attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            import random

            delay *= 0.5 + random.random() * 0.5

        return delay


class PublishingErrorHandler:
    """Comprehensive error handler for PyPI publishing workflow."""

    def __init__(self, log_file: Path | None = None) -> None:
        """Initialize error handler.

        Args:
            log_file: Optional log file path for error logging
        """
        self.errors: list[PublishingError] = []
        self.log_file = log_file
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Set up logger for error handling."""
        logger = logging.getLogger("publishing_error_handler")
        logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler if log file specified
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    def categorize_error(self, command: str, exit_code: int, stderr: str) -> ErrorCategory:
        """Categorize error based on command, exit code, and stderr.

        Args:
            command: Command that failed
            exit_code: Exit code from command
            stderr: Standard error output

        Returns:
            Error category
        """
        stderr_lower = stderr.lower()

        # Authentication errors
        if any(
            keyword in stderr_lower
            for keyword in [
                "authentication",
                "unauthorized",
                "forbidden",
                "invalid token",
                "api key",
                "credentials",
                "login",
            ]
        ):
            return ErrorCategory.AUTHENTICATION

        # Network errors
        if any(
            keyword in stderr_lower
            for keyword in [
                "network",
                "connection",
                "timeout",
                "dns",
                "unreachable",
                "socket",
                "ssl",
                "certificate",
            ]
        ):
            return ErrorCategory.NETWORK

        # Validation errors
        if any(
            keyword in stderr_lower
            for keyword in [
                "validation",
                "invalid",
                "malformed",
                "syntax error",
                "parse error",
                "schema",
            ]
        ):
            return ErrorCategory.VALIDATION

        # Build errors
        if any(
            keyword in stderr_lower
            for keyword in ["build", "compilation", "missing file", "import error"]
        ):
            return ErrorCategory.BUILD

        # Upload errors
        if any(
            keyword in stderr_lower
            for keyword in [
                "upload",
                "file exists",
                "version exists",
                "duplicate",
                "already exists",
            ]
        ):
            return ErrorCategory.UPLOAD

        # Configuration errors
        if any(
            keyword in stderr_lower
            for keyword in ["configuration", "config", "missing", "not found"]
        ):
            return ErrorCategory.CONFIGURATION

        return ErrorCategory.UNKNOWN

    def determine_severity(self, category: ErrorCategory, exit_code: int) -> ErrorSeverity:
        """Determine error severity based on category and exit code.

        Args:
            category: Error category
            exit_code: Exit code from command

        Returns:
            Error severity
        """
        if category == ErrorCategory.AUTHENTICATION:
            return ErrorSeverity.CRITICAL
        if category in (ErrorCategory.VALIDATION, ErrorCategory.BUILD):
            return ErrorSeverity.HIGH
        if category in (ErrorCategory.NETWORK, ErrorCategory.UPLOAD):
            return ErrorSeverity.MEDIUM
        if category == ErrorCategory.CONFIGURATION:
            return ErrorSeverity.HIGH
        return ErrorSeverity.MEDIUM

    def is_retryable_error(self, category: ErrorCategory, stderr: str) -> bool:
        """Determine if error is retryable.

        Args:
            category: Error category
            stderr: Standard error output

        Returns:
            True if error is retryable, False otherwise
        """
        stderr_lower = stderr.lower()

        # Non-retryable errors
        non_retryable_keywords = [
            "authentication",
            "unauthorized",
            "forbidden",
            "invalid token",
            "file exists",
            "version exists",
            "duplicate",
            "already exists",
            "validation",
            "invalid",
            "malformed",
            "syntax error",
        ]

        if any(keyword in stderr_lower for keyword in non_retryable_keywords):
            return False

        # Retryable categories
        retryable_categories = [ErrorCategory.NETWORK, ErrorCategory.UNKNOWN]

        return category in retryable_categories

    def handle_command_error(
        self,
        command: str | list[str],
        exit_code: int,
        stdout: str = "",
        stderr: str = "",
        retry_count: int = 0,
    ) -> PublishingError:
        """Handle command execution error.

        Args:
            command: Command that failed
            exit_code: Exit code from command
            stdout: Standard output
            stderr: Standard error output
            retry_count: Current retry count

        Returns:
            PublishingError instance
        """
        command_str = " ".join(command) if isinstance(command, list) else command

        category = self.categorize_error(command_str, exit_code, stderr)
        severity = self.determine_severity(category, exit_code)
        is_retryable = self.is_retryable_error(category, stderr)

        error = PublishingError(
            category=category,
            severity=severity,
            message=f"Command failed: {command_str}",
            details=f"Exit code: {exit_code}",
            command=command_str,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            retry_count=retry_count,
            is_retryable=is_retryable,
        )

        self.errors.append(error)
        self.logger.error(f"Command error: {error.message}")
        self.logger.debug(f"Error details: {error.to_dict()}")

        return error

    def execute_with_retry(
        self,
        func: Callable[[], tuple[int, str, str]],
        retry_config: RetryConfig | None = None,
        operation_name: str = "operation",
    ) -> tuple[bool, PublishingError | None]:
        """Execute function with retry logic and exponential backoff.

        Args:
            func: Function to execute that returns (exit_code, stdout, stderr)
            retry_config: Retry configuration
            operation_name: Name of operation for logging

        Returns:
            Tuple of (success, error)
        """
        if retry_config is None:
            retry_config = RetryConfig()

        last_error = None

        for attempt in range(retry_config.max_retries + 1):
            try:
                self.logger.info(f"Executing {operation_name} (attempt {attempt + 1})")

                exit_code, stdout, stderr = func()

                if exit_code == 0:
                    if attempt > 0:
                        self.logger.info(f"{operation_name} succeeded after {attempt + 1} attempts")
                    return True, None

                # Handle error
                error = self.handle_command_error(
                    operation_name, exit_code, stdout, stderr, attempt
                )
                last_error = error

                if not error.is_retryable or attempt >= retry_config.max_retries:
                    self.logger.error(f"{operation_name} failed permanently: {error.message}")
                    break

                # Calculate delay and wait
                delay = retry_config.get_delay(attempt)
                self.logger.warning(
                    f"{operation_name} failed (attempt {attempt + 1}), "
                    f"retrying in {delay:.1f} seconds: {error.message}"
                )
                time.sleep(delay)

            except Exception as e:
                error = PublishingError(
                    category=ErrorCategory.UNKNOWN,
                    severity=ErrorSeverity.HIGH,
                    message=f"Unexpected error in {operation_name}: {e!s}",
                    retry_count=attempt,
                    is_retryable=False,
                )
                self.errors.append(error)
                self.logger.exception(f"Unexpected error in {operation_name}")
                last_error = error
                break

        return False, last_error

    def run_command_with_retry(
        self,
        command: str | list[str],
        retry_config: RetryConfig | None = None,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> tuple[bool, PublishingError | None]:
        """Run command with retry logic.

        Args:
            command: Command to run
            retry_config: Retry configuration
            cwd: Working directory
            env: Environment variables

        Returns:
            Tuple of (success, error)
        """
        command_list = command if isinstance(command, list) else command.split()
        command_str = " ".join(command_list)

        def run_command() -> tuple[int, str, str]:
            try:
                result = subprocess.run(  # noqa: S603
                    command_list,
                    check=False,
                    capture_output=True,
                    text=True,
                    cwd=cwd,
                    env=env,
                    timeout=300,  # 5 minute timeout
                )
                return result.returncode, result.stdout, result.stderr
            except subprocess.TimeoutExpired:
                return 124, "", "Command timed out after 5 minutes"
            except Exception as e:
                return 1, "", f"Failed to execute command: {e!s}"

        return self.execute_with_retry(run_command, retry_config, command_str)

    def generate_error_report(self) -> dict[str, Any]:
        """Generate comprehensive error report.

        Returns:
            Error report dictionary
        """
        if not self.errors:
            return {"status": "success", "errors": [], "summary": "No errors occurred"}

        # Categorize errors
        error_counts = {}
        severity_counts = {}
        retryable_count = 0

        for error in self.errors:
            error_counts[error.category.value] = error_counts.get(error.category.value, 0) + 1
            severity_counts[error.severity.value] = severity_counts.get(error.severity.value, 0) + 1
            if error.is_retryable:
                retryable_count += 1

        # Find most severe error
        severity_order = [
            ErrorSeverity.CRITICAL,
            ErrorSeverity.HIGH,
            ErrorSeverity.MEDIUM,
            ErrorSeverity.LOW,
        ]
        most_severe = None
        for severity in severity_order:
            if any(error.severity == severity for error in self.errors):
                most_severe = severity
                break

        return {
            "status": "error",
            "total_errors": len(self.errors),
            "error_categories": error_counts,
            "severity_counts": severity_counts,
            "retryable_errors": retryable_count,
            "most_severe": most_severe.value if most_severe else None,
            "errors": [error.to_dict() for error in self.errors],
            "summary": self._generate_error_summary(),
        }

    def _generate_error_summary(self) -> str:
        """Generate human-readable error summary."""
        if not self.errors:
            return "No errors occurred"

        critical_errors = [e for e in self.errors if e.severity == ErrorSeverity.CRITICAL]
        high_errors = [e for e in self.errors if e.severity == ErrorSeverity.HIGH]

        if critical_errors:
            return f"Critical errors occurred: {critical_errors[0].message}"
        if high_errors:
            return f"High severity errors occurred: {high_errors[0].message}"
        return f"Publishing failed with {len(self.errors)} error(s)"

    def save_error_report(self, output_file: Path) -> None:
        """Save error report to file.

        Args:
            output_file: Path to save error report
        """
        report = self.generate_error_report()

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open("w") as f:
            json.dump(report, f, indent=2)

        self.logger.info(f"Error report saved to {output_file}")

    def print_error_summary(self) -> None:
        """Print error summary to console."""
        if not self.errors:
            print("✅ No errors occurred")
            return

        print(f"\n❌ Publishing failed with {len(self.errors)} error(s):")
        print("=" * 60)

        for i, error in enumerate(self.errors, 1):
            print(f"\n{i}. {error.category.value.upper()} ERROR ({error.severity.value})")
            print(f"   Message: {error.message}")
            if error.details:
                print(f"   Details: {error.details}")
            if error.command:
                print(f"   Command: {error.command}")
            if error.stderr:
                print(f"   Error Output: {error.stderr[:200]}...")
            print(f"   Retryable: {'Yes' if error.is_retryable else 'No'}")
            print(f"   Retry Count: {error.retry_count}")

        print("\n" + "=" * 60)
        print(f"Summary: {self._generate_error_summary()}")


def main() -> None:
    """Main entry point for testing error handler."""
    import argparse

    parser = argparse.ArgumentParser(description="Test publishing error handler")
    parser.add_argument("--log-file", type=Path, help="Log file path")
    parser.add_argument("--test-command", help="Test command to run")

    args = parser.parse_args()

    handler = PublishingErrorHandler(args.log_file)

    if args.test_command:
        print(f"Testing command: {args.test_command}")
        success, _error = handler.run_command_with_retry(args.test_command)

        if success:
            print("✅ Command succeeded")
        else:
            print("❌ Command failed")
            handler.print_error_summary()

        # Save error report
        if handler.errors:
            report_file = Path("error_report.json")
            handler.save_error_report(report_file)
            print(f"Error report saved to {report_file}")

    else:
        print("No test command specified. Use --test-command to test error handling.")


if __name__ == "__main__":
    main()
