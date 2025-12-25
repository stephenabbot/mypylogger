"""Performance benchmarks for mypylogger v0.2.8.

This module contains performance tests that validate the library meets
performance requirements:
- Logger initialization: <10ms
- Single log entry: <1ms with immediate flush

Requirements addressed:
- 9.1: Run performance benchmarks on every pull request and main branch push
- 9.2: Measure logger initialization time and fail if it exceeds 10ms
- 9.3: Measure single log entry time and fail if it exceeds 1ms with immediate flush
"""

import logging
import os
from pathlib import Path
import time
from typing import TYPE_CHECKING

import pytest

from mypylogger import get_logger

# Optional import for memory testing
try:
    import psutil
except ImportError:
    psutil = None

if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture


class TestLoggerInitializationPerformance:
    """Test logger initialization performance requirements."""

    def test_logger_initialization_performance(self, benchmark: "BenchmarkFixture") -> None:
        """Test that logger initialization completes within 10ms threshold.

        Requirements:
        - 9.2: Measure logger initialization time and fail if it exceeds 10ms
        """
        # Benchmark the get_logger function
        result = benchmark(get_logger, "perf_test_init")

        # Verify the logger was created successfully
        assert result is not None
        assert result.name == "perf_test_init"

        # Validate performance threshold (10ms = 0.01 seconds)
        mean_time = benchmark.stats["mean"]
        assert mean_time < 0.01, (
            f"Logger initialization took {mean_time:.4f}s, exceeds 10ms threshold (0.01s)"
        )

    def test_logger_initialization_with_file_config_performance(
        self, benchmark: "BenchmarkFixture", tmp_path: Path
    ) -> None:
        """Test logger initialization performance with file logging configuration.

        This test ensures that even with file logging enabled, initialization
        remains under the 10ms threshold.
        """
        # Set up file logging configuration
        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        def setup_and_get_logger() -> logging.Logger:
            # Configure environment for file logging
            os.environ["LOG_TO_FILE"] = "true"
            os.environ["LOG_FILE_DIR"] = str(log_dir)
            try:
                return get_logger("perf_test_file_init")
            finally:
                # Clean up environment
                os.environ.pop("LOG_TO_FILE", None)
                os.environ.pop("LOG_FILE_DIR", None)

        # Benchmark logger initialization with file configuration
        result = benchmark(setup_and_get_logger)

        # Verify the logger was created successfully
        assert result is not None
        assert result.name == "perf_test_file_init"

        # Validate performance threshold
        mean_time = benchmark.stats["mean"]
        assert mean_time < 0.01, (
            f"Logger initialization with file config took {mean_time:.4f}s, "
            f"exceeds 10ms threshold (0.01s)"
        )


class TestLogEntryPerformance:
    """Test individual log entry performance requirements."""

    @pytest.fixture
    def logger_for_perf_test(self) -> logging.Logger:
        """Create a logger instance for performance testing."""
        return get_logger("perf_test_logging")

    def test_single_log_entry_performance(
        self, benchmark: "BenchmarkFixture", logger_for_perf_test: logging.Logger
    ) -> None:
        """Test that single log entry completes within 1ms threshold.

        Requirements:
        - 9.3: Measure single log entry time and fail if it exceeds 1ms with immediate flush
        """
        logger = logger_for_perf_test

        # Benchmark a single log entry
        benchmark(logger.info, "Performance test message")

        # Validate performance threshold (1ms = 0.001 seconds)
        mean_time = benchmark.stats["mean"]
        assert mean_time < 0.001, (
            f"Single log entry took {mean_time:.6f}s, exceeds 1ms threshold (0.001s)"
        )

    def test_log_entry_with_extra_fields_performance(
        self, benchmark: "BenchmarkFixture", logger_for_perf_test: logging.Logger
    ) -> None:
        """Test log entry performance with additional structured data."""
        logger = logger_for_perf_test

        extra_data = {
            "user_id": "12345",
            "request_id": "req-abc-123",
            "operation": "performance_test",
            "duration_ms": 42,
        }

        # Benchmark log entry with extra fields
        benchmark(logger.info, "Performance test with extra fields", extra=extra_data)

        # Validate performance threshold
        mean_time = benchmark.stats["mean"]
        assert mean_time < 0.001, (
            f"Log entry with extra fields took {mean_time:.6f}s, exceeds 1ms threshold (0.001s)"
        )

    def test_file_logging_performance(self, benchmark: "BenchmarkFixture", tmp_path: Path) -> None:
        """Test log entry performance with file logging enabled."""
        # Set up file logging
        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        os.environ["LOG_TO_FILE"] = "true"
        os.environ["LOG_FILE_DIR"] = str(log_dir)

        try:
            logger = get_logger("perf_test_file_logging")

            # Benchmark file logging
            benchmark(logger.info, "Performance test file logging message")

            # Validate performance threshold
            mean_time = benchmark.stats["mean"]
            assert mean_time < 0.001, (
                f"File log entry took {mean_time:.6f}s, exceeds 1ms threshold (0.001s)"
            )

            # Verify log file was created and contains the message
            log_files = list(log_dir.glob("*.log"))
            assert len(log_files) > 0, "No log file was created"

        finally:
            # Clean up environment
            os.environ.pop("LOG_TO_FILE", None)
            os.environ.pop("LOG_FILE_DIR", None)


class TestThroughputPerformance:
    """Test logging throughput and sustained performance."""

    def test_sustained_logging_performance(self, tmp_path: Path) -> None:
        """Test sustained logging performance over multiple entries.

        This test validates that performance remains consistent over time
        and doesn't degrade significantly with multiple log entries.
        """
        # Set up file logging for realistic performance testing
        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        os.environ["LOG_TO_FILE"] = "true"
        os.environ["LOG_FILE_DIR"] = str(log_dir)

        try:
            logger = get_logger("perf_test_sustained")

            # Measure time for 100 log entries
            start_time = time.perf_counter()

            for i in range(100):
                logger.info("Sustained performance test message %d", i)

            end_time = time.perf_counter()
            total_time = end_time - start_time

            # Calculate average time per log entry
            avg_time_per_entry = total_time / 100

            # Validate that average time per entry is still under 1ms
            assert avg_time_per_entry < 0.001, (
                f"Average time per log entry in sustained test: {avg_time_per_entry:.6f}s, "
                f"exceeds 1ms threshold (0.001s)"
            )

            # Validate total time is reasonable (should be well under 1 second)
            assert total_time < 0.5, (
                f"Total time for 100 log entries: {total_time:.3f}s, "
                f"exceeds reasonable threshold (0.5s)"
            )

            # Calculate throughput (entries per second)
            throughput = 100 / total_time

            # Expect at least 1000 entries per second
            assert throughput >= 1000, (
                f"Throughput: {throughput:.0f} entries/second, "
                f"below expected minimum (1000 entries/second)"
            )

        finally:
            # Clean up environment
            os.environ.pop("LOG_TO_FILE", None)
            os.environ.pop("LOG_FILE_DIR", None)

    def test_memory_usage_stability(self, tmp_path: Path) -> None:
        """Test that memory usage remains stable during logging operations.

        This test ensures that the logger doesn't have memory leaks or
        excessive memory growth during normal operations.
        """
        if psutil is None:
            pytest.skip("psutil not available for memory testing")

        # Set up file logging
        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        os.environ["LOG_TO_FILE"] = "true"
        os.environ["LOG_FILE_DIR"] = str(log_dir)

        try:
            process = psutil.Process()

            # Measure baseline memory
            baseline_memory = process.memory_info().rss

            logger = get_logger("perf_test_memory")

            # Log 1000 entries and measure memory growth
            for i in range(1000):
                logger.info("Memory test message %d", i, extra={"iteration": i})

            final_memory = process.memory_info().rss
            memory_growth = final_memory - baseline_memory

            # Memory growth should be reasonable (less than 10MB for 1000 entries)
            max_acceptable_growth = 10 * 1024 * 1024  # 10MB
            assert memory_growth < max_acceptable_growth, (
                f"Memory growth: {memory_growth / 1024 / 1024:.2f}MB, "
                f"exceeds acceptable limit (10MB)"
            )

            # Calculate memory per log entry
            memory_per_entry = memory_growth / 1000

            # Each log entry should use less than 1KB of memory
            max_memory_per_entry = 1024  # 1KB
            assert memory_per_entry < max_memory_per_entry, (
                f"Memory per log entry: {memory_per_entry:.0f} bytes, "
                f"exceeds acceptable limit (1KB)"
            )

        finally:
            # Clean up environment
            os.environ.pop("LOG_TO_FILE", None)
            os.environ.pop("LOG_FILE_DIR", None)


class TestPerformanceRegression:
    """Test for performance regression detection."""

    def test_performance_baseline_validation(self, benchmark: "BenchmarkFixture") -> None:
        """Validate current performance against established baselines.

        This test serves as a regression detector for performance changes.
        """
        logger = get_logger("perf_baseline_test")

        # Benchmark typical logging operation
        benchmark(logger.info, "Baseline performance test", extra={"test": True})

        # Store performance metrics for regression analysis
        mean_time = benchmark.stats["mean"]
        std_dev = benchmark.stats["stddev"]

        # Performance should be well within thresholds with room for variance
        assert mean_time < 0.0005, (  # 0.5ms - well under 1ms threshold
            f"Baseline performance degraded: {mean_time:.6f}s > 0.5ms"
        )

        # Standard deviation should be low (consistent performance)
        assert std_dev < 0.0002, (  # 0.2ms standard deviation
            f"Performance variance too high: {std_dev:.6f}s > 0.2ms"
        )
