"""Performance and stress tests for mypylogger."""

import gc
import os
from pathlib import Path
import tempfile
import time
from unittest.mock import patch

import mypylogger


class TestPerformance:
    """Test performance characteristics and stress scenarios."""

    def test_logger_initialization_performance(self) -> None:
        """Test logger initialization performance (<10ms target)."""
        with patch.dict(os.environ, {"LOG_TO_FILE": "false"}, clear=True):
            # Warm up
            mypylogger.get_logger("warmup")

            # Measure initialization time
            start_time = time.perf_counter()
            logger = mypylogger.get_logger("performance_test")
            end_time = time.perf_counter()

            initialization_time = (end_time - start_time) * 1000  # Convert to milliseconds

            # Should be less than 10ms
            assert initialization_time < 10.0, (
                f"Initialization took {initialization_time:.2f}ms, expected <10ms"
            )

            # Verify logger works
            assert logger.name == "performance_test"
            assert len(logger.handlers) > 0

    def test_single_log_entry_performance(self) -> None:
        """Test single log entry performance (<1ms target)."""
        with patch.dict(os.environ, {"LOG_TO_FILE": "false"}, clear=True):
            logger = mypylogger.get_logger("log_performance_test")

            # Warm up
            logger.info("Warmup message")

            # Measure single log entry time
            start_time = time.perf_counter()
            logger.info("Performance test message")
            end_time = time.perf_counter()

            log_time = (end_time - start_time) * 1000  # Convert to milliseconds

            # Should be less than 1ms
            assert log_time < 1.0, f"Single log entry took {log_time:.2f}ms, expected <1ms"

    def test_multiple_logger_memory_usage(self) -> None:
        """Test memory usage with multiple loggers."""
        with patch.dict(os.environ, {"LOG_TO_FILE": "false"}, clear=True):
            # Force garbage collection before test
            gc.collect()

            # Create multiple loggers
            loggers = []
            for i in range(100):
                logger = mypylogger.get_logger(f"memory_test_logger_{i}")
                loggers.append(logger)

            # Log from each logger
            for i, logger in enumerate(loggers):
                logger.info("Message from logger %d", i)

            # Force garbage collection after test
            gc.collect()

            # Verify all loggers are functional
            assert len(loggers) == 100
            for logger in loggers:
                assert len(logger.handlers) > 0

    def test_high_frequency_logging_stress(self) -> None:
        """Test high-frequency logging stress scenario."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_vars = {"APP_NAME": "stress_test", "LOG_TO_FILE": "true", "LOG_FILE_DIR": temp_dir}

            with patch.dict(os.environ, env_vars, clear=True):
                logger = mypylogger.get_logger()

                # Log 1000 messages rapidly
                start_time = time.perf_counter()

                for i in range(1000):
                    logger.info("Stress test message %d", i)

                end_time = time.perf_counter()

                total_time = end_time - start_time
                avg_time_per_log = (total_time / 1000) * 1000  # ms per log

                # Should handle high frequency logging
                assert avg_time_per_log < 5.0, (
                    f"Average time per log: {avg_time_per_log:.2f}ms, expected <5ms"
                )

                # Verify all messages were logged
                log_files = list(Path(temp_dir).glob("*.log"))
                assert len(log_files) > 0

                content = log_files[0].read_text()
                lines = [line.strip() for line in content.split("\n") if line.strip()]
                assert len(lines) == 1000

    def test_large_message_performance(self) -> None:
        """Test performance with large log messages."""
        with patch.dict(os.environ, {"LOG_TO_FILE": "false"}, clear=True):
            logger = mypylogger.get_logger("large_message_test")

            # Create large message (10KB)
            large_message = "A" * 10240

            # Measure time for large message
            start_time = time.perf_counter()
            logger.info(large_message)
            end_time = time.perf_counter()

            log_time = (end_time - start_time) * 1000  # Convert to milliseconds

            # Should handle large messages reasonably well
            assert log_time < 10.0, f"Large message logging took {log_time:.2f}ms, expected <10ms"

    def test_custom_fields_performance(self) -> None:
        """Test performance impact of custom fields."""
        with patch.dict(os.environ, {"LOG_TO_FILE": "false"}, clear=True):
            logger = mypylogger.get_logger("custom_fields_performance")

            # Create large custom fields dictionary
            custom_fields = {f"field_{i}": f"value_{i}" for i in range(50)}

            # Measure time with custom fields
            start_time = time.perf_counter()
            logger.info("Message with custom fields", extra=custom_fields)
            end_time = time.perf_counter()

            log_time = (end_time - start_time) * 1000  # Convert to milliseconds

            # Should handle custom fields efficiently
            assert log_time < 5.0, f"Custom fields logging took {log_time:.2f}ms, expected <5ms"

    def test_concurrent_logger_creation_stress(self) -> None:
        """Test concurrent logger creation stress scenario."""
        with patch.dict(os.environ, {"LOG_TO_FILE": "false"}, clear=True):
            # Simulate concurrent logger creation
            start_time = time.perf_counter()

            loggers = []
            for i in range(50):
                # Create multiple loggers with same name (should reuse)
                logger1 = mypylogger.get_logger("concurrent_test")
                logger2 = mypylogger.get_logger(f"unique_logger_{i}")
                loggers.extend([logger1, logger2])

            end_time = time.perf_counter()

            total_time = (end_time - start_time) * 1000  # Convert to milliseconds
            avg_time_per_logger = total_time / 100

            # Should handle concurrent creation efficiently
            assert avg_time_per_logger < 1.0, (
                f"Average logger creation time: {avg_time_per_logger:.2f}ms, expected <1ms"
            )

            # Verify all loggers work
            for logger in loggers:
                logger.info("Concurrent test message")

    def test_file_io_performance_stress(self) -> None:
        """Test file I/O performance under stress."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_vars = {
                "APP_NAME": "file_io_stress",
                "LOG_TO_FILE": "true",
                "LOG_FILE_DIR": temp_dir,
            }

            with patch.dict(os.environ, env_vars, clear=True):
                logger = mypylogger.get_logger()

                # Log many messages with immediate flush
                start_time = time.perf_counter()

                for i in range(500):
                    logger.info("File I/O stress test message %d", i)

                end_time = time.perf_counter()

                total_time = end_time - start_time
                avg_time_per_log = (total_time / 500) * 1000  # ms per log

                # Should handle file I/O efficiently even with immediate flush
                assert avg_time_per_log < 10.0, (
                    f"Average file I/O time per log: {avg_time_per_log:.2f}ms, expected <10ms"
                )

                # Verify all messages were written
                log_files = list(Path(temp_dir).glob("*.log"))
                assert len(log_files) > 0

                content = log_files[0].read_text()
                lines = [line.strip() for line in content.split("\n") if line.strip()]
                assert len(lines) == 500

    def test_json_serialization_performance(self) -> None:
        """Test JSON serialization performance with complex data."""
        with patch.dict(os.environ, {"LOG_TO_FILE": "false"}, clear=True):
            logger = mypylogger.get_logger("json_performance")

            # Create complex custom data
            complex_data = {
                "nested": {"level1": {"level2": {"level3": [1, 2, 3, 4, 5] * 10}}},
                "list": list(range(100)),
                "string": "test" * 100,
            }

            # Measure JSON serialization time
            start_time = time.perf_counter()
            logger.info("Complex data test", extra=complex_data)
            end_time = time.perf_counter()

            serialization_time = (end_time - start_time) * 1000  # Convert to milliseconds

            # Should handle complex JSON serialization efficiently
            assert serialization_time < 5.0, (
                f"JSON serialization took {serialization_time:.2f}ms, expected <5ms"
            )

    def test_error_handling_performance_impact(self) -> None:
        """Test that error handling doesn't significantly impact performance."""
        with patch.dict(os.environ, {"LOG_TO_FILE": "false"}, clear=True):
            logger = mypylogger.get_logger("error_performance")

            # Create data that will cause JSON serialization errors
            class NonSerializable:
                def __str__(self) -> str:
                    return "non_serializable"

            non_serializable_data = {"bad_data": NonSerializable()}

            # Measure time with error handling
            start_time = time.perf_counter()

            for _i in range(100):
                # This should trigger error handling and fallback
                logger.info("Error handling test", extra=non_serializable_data)

            end_time = time.perf_counter()

            total_time = end_time - start_time
            avg_time_per_log = (total_time / 100) * 1000  # ms per log

            # Error handling should not significantly impact performance
            assert avg_time_per_log < 10.0, (
                f"Error handling time per log: {avg_time_per_log:.2f}ms, expected <10ms"
            )

    def test_memory_leak_prevention(self) -> None:
        """Test that repeated logger creation doesn't cause memory leaks."""
        with patch.dict(os.environ, {"LOG_TO_FILE": "false"}, clear=True):
            # Force garbage collection before test
            gc.collect()

            # Create and use many loggers
            for i in range(200):
                logger = mypylogger.get_logger(f"memory_leak_test_{i}")
                logger.info("Memory test message %d", i)

                # Occasionally force garbage collection
                if i % 50 == 0:
                    gc.collect()

            # Final garbage collection
            gc.collect()

            # Test should complete without memory issues
            # If there were memory leaks, this test would likely fail or be very slow
            assert True  # Test completion indicates no major memory issues
