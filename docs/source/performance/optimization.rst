Performance Optimization
========================

Comprehensive guidelines for optimizing mypylogger performance in your applications.

Performance Characteristics Overview
------------------------------------

**mypylogger Performance Profile**:

* **Logger initialization**: ~5ms (target: <10ms)
* **Single log entry**: ~0.5ms with immediate flush (target: <1ms)
* **Memory usage**: ~2MB baseline + ~1KB per log entry
* **Throughput**: Optimized for typical application logging (1-1000 logs/second)
* **Latency**: Prioritizes reliability over speed (immediate flush enabled)

**Performance Philosophy**:
mypylogger is designed for "fast enough" performance with reliability as the primary goal. It's optimized for typical application logging scenarios, not high-frequency logging systems.

Log Level Optimization
----------------------

**1. Strategic log level selection**

Log levels have significant performance impact due to filtering and processing overhead:

.. code-block:: python

   import os
   from mypylogger import get_logger
   
   # Performance impact by log level (from highest to lowest overhead):
   
   # DEBUG: Highest overhead - processes all messages
   os.environ["LOG_LEVEL"] = "DEBUG"    # ~100% of messages processed
   
   # INFO: Moderate overhead - filters debug messages  
   os.environ["LOG_LEVEL"] = "INFO"     # ~80% of messages processed
   
   # WARNING: Lower overhead - filters debug and info
   os.environ["LOG_LEVEL"] = "WARNING"  # ~20% of messages processed
   
   # ERROR: Minimal overhead - only errors and critical
   os.environ["LOG_LEVEL"] = "ERROR"    # ~5% of messages processed
   
   # CRITICAL: Lowest overhead - only critical messages
   os.environ["LOG_LEVEL"] = "CRITICAL" # ~1% of messages processed

**2. Environment-specific log level optimization**

.. code-block:: python

   import os
   
   def configure_optimal_log_level():
       """Configure log level based on environment for optimal performance."""
       
       environment = os.getenv("ENVIRONMENT", "development")
       
       if environment == "production":
           # Production: Minimal logging for maximum performance
           os.environ["LOG_LEVEL"] = "ERROR"
       elif environment == "staging":
           # Staging: Balanced logging for testing
           os.environ["LOG_LEVEL"] = "WARNING"
       elif environment == "development":
           # Development: Full logging for debugging
           os.environ["LOG_LEVEL"] = "DEBUG"
       else:
           # Default: Safe middle ground
           os.environ["LOG_LEVEL"] = "INFO"
   
   configure_optimal_log_level()

**3. Conditional expensive operations**

Avoid computing expensive data when it won't be logged:

.. code-block:: python

   import logging
   import time
   from mypylogger import get_logger
   
   logger = get_logger(__name__)
   
   def expensive_debug_computation():
       """Simulate expensive computation for debug data."""
       time.sleep(0.1)  # Simulate 100ms computation
       return {"complex_data": "expensive_result"}
   
   # WRONG: Always computes expensive data
   def inefficient_logging():
       debug_data = expensive_debug_computation()  # Always runs!
       logger.debug("Debug info", extra=debug_data)
   
   # RIGHT: Only compute when debug logging is enabled
   def efficient_logging():
       if logger.isEnabledFor(logging.DEBUG):
           debug_data = expensive_debug_computation()  # Only runs if needed
           logger.debug("Debug info", extra=debug_data)
       else:
           logger.info("Operation completed")  # Lightweight alternative

**4. Performance measurement of log level impact**

.. code-block:: python

   import time
   import os
   from mypylogger import get_logger
   
   def measure_log_level_performance():
       """Measure performance impact of different log levels."""
       
       test_iterations = 1000
       
       for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
           os.environ["LOG_LEVEL"] = level
           logger = get_logger(f"perf_test_{level.lower()}")
           
           start_time = time.time()
           
           for i in range(test_iterations):
               logger.debug(f"Debug message {i}")
               logger.info(f"Info message {i}")
               logger.warning(f"Warning message {i}")
               logger.error(f"Error message {i}")
           
           duration = time.time() - start_time
           avg_per_log = (duration / (test_iterations * 4)) * 1000  # ms per log
           
           print(f"Level {level}: {duration:.3f}s total, {avg_per_log:.3f}ms per log")

Batch Processing Optimization
-----------------------------

**1. Batch logging for high-volume scenarios**

.. code-block:: python

   from mypylogger import get_logger
   
   logger = get_logger(__name__)
   
   # INEFFICIENT: Log every item individually
   def process_items_inefficient(items):
       for item in items:
           result = process_item(item)
           logger.info("Item processed", extra={
               "item_id": item.id,
               "result": result,
               "timestamp": time.time()
           })  # 1000 items = 1000 log entries
   
   # EFFICIENT: Log in batches
   def process_items_efficient(items, batch_size=100):
       processed_count = 0
       errors = []
       
       for i in range(0, len(items), batch_size):
           batch = items[i:i+batch_size]
           batch_start_time = time.time()
           
           for item in batch:
               try:
                   process_item(item)
                   processed_count += 1
               except Exception as e:
                   errors.append({"item_id": item.id, "error": str(e)})
           
           batch_duration = time.time() - batch_start_time
           
           # Single log entry per batch
           logger.info("Batch processed", extra={
               "batch_number": i // batch_size + 1,
               "batch_size": len(batch),
               "processed_count": len(batch) - len([e for e in errors if e in batch]),
               "error_count": len([e for e in errors if e in batch]),
               "duration_ms": round(batch_duration * 1000, 2),
               "items_per_second": round(len(batch) / batch_duration, 2)
           })
       
       # Summary log entry
       logger.info("Processing completed", extra={
           "total_items": len(items),
           "processed_count": processed_count,
           "error_count": len(errors),
           "success_rate": round(processed_count / len(items) * 100, 2)
       })

**2. Aggregated metrics logging**

.. code-block:: python

   import time
   from collections import defaultdict
   from mypylogger import get_logger
   
   class MetricsAggregator:
       """Aggregate metrics and log periodically for better performance."""
       
       def __init__(self, log_interval=60):  # Log every 60 seconds
           self.logger = get_logger(__name__)
           self.metrics = defaultdict(int)
           self.timings = defaultdict(list)
           self.last_log_time = time.time()
           self.log_interval = log_interval
       
       def record_metric(self, metric_name, value=1):
           """Record a metric value."""
           self.metrics[metric_name] += value
           self._maybe_log_metrics()
       
       def record_timing(self, operation_name, duration_ms):
           """Record operation timing."""
           self.timings[operation_name].append(duration_ms)
           self._maybe_log_metrics()
       
       def _maybe_log_metrics(self):
           """Log aggregated metrics if interval has passed."""
           current_time = time.time()
           
           if current_time - self.last_log_time >= self.log_interval:
               self._log_aggregated_metrics()
               self._reset_metrics()
               self.last_log_time = current_time
       
       def _log_aggregated_metrics(self):
           """Log all aggregated metrics."""
           if not self.metrics and not self.timings:
               return
           
           # Aggregate timing statistics
           timing_stats = {}
           for operation, durations in self.timings.items():
               if durations:
                   timing_stats[operation] = {
                       "count": len(durations),
                       "avg_ms": round(sum(durations) / len(durations), 2),
                       "min_ms": min(durations),
                       "max_ms": max(durations)
                   }
           
           self.logger.info("Aggregated metrics", extra={
               "interval_seconds": self.log_interval,
               "counters": dict(self.metrics),
               "timings": timing_stats,
               "timestamp": time.time()
           })
       
       def _reset_metrics(self):
           """Reset all metrics for next interval."""
           self.metrics.clear()
           self.timings.clear()
   
   # Usage example
   metrics = MetricsAggregator(log_interval=30)  # Log every 30 seconds
   
   def process_request(request):
       start_time = time.time()
       
       try:
           result = handle_request(request)
           metrics.record_metric("requests_successful")
           return result
       except Exception as e:
           metrics.record_metric("requests_failed")
           raise
       finally:
           duration_ms = (time.time() - start_time) * 1000
           metrics.record_timing("request_processing", duration_ms)

Memory Usage Optimization
-------------------------

**1. Logger instance management**

.. code-block:: python

   from mypylogger import get_logger
   
   # INEFFICIENT: Creating multiple logger instances
   class BadExample:
       def __init__(self, user_id):
           self.user_id = user_id
           # Creates new logger for each instance - memory waste!
           self.logger = get_logger(f"user_{user_id}")
       
       def process(self):
           self.logger.info("Processing user", extra={"user_id": self.user_id})
   
   # EFFICIENT: Shared module-level logger
   logger = get_logger(__name__)  # Single logger per module
   
   class GoodExample:
       def __init__(self, user_id):
           self.user_id = user_id
           # No logger instance - uses shared module logger
       
       def process(self):
           logger.info("Processing user", extra={"user_id": self.user_id})

**2. Optimize extra data size**

.. code-block:: python

   import sys
   from mypylogger import get_logger
   
   logger = get_logger(__name__)
   
   # INEFFICIENT: Large objects in log entries
   def log_large_data_inefficient(user_data):
       # This creates large log entries and high memory usage
       logger.info("User data processed", extra={
           "full_user_object": user_data,  # Could be MB of data!
           "raw_request": request.body,    # Could be very large
           "complete_response": response   # Entire response object
       })
   
   # EFFICIENT: Essential data only
   def log_large_data_efficient(user_data):
       # Extract only essential information
       essential_data = {
           "user_id": user_data.get("id"),
           "user_type": user_data.get("type"),
           "request_size_bytes": len(request.body) if request.body else 0,
           "response_status": response.status_code,
           "response_size_bytes": len(response.content) if response.content else 0
       }
       
       logger.info("User data processed", extra=essential_data)

**3. Memory usage monitoring**

.. code-block:: python

   import psutil
   import os
   from mypylogger import get_logger
   
   class MemoryMonitor:
       """Monitor memory usage of logging operations."""
       
       def __init__(self):
           self.logger = get_logger(__name__)
           self.process = psutil.Process(os.getpid())
           self.baseline_memory = self.process.memory_info().rss
       
       def log_memory_usage(self, operation_name):
           """Log current memory usage."""
           current_memory = self.process.memory_info().rss
           memory_delta = current_memory - self.baseline_memory
           
           self.logger.info("Memory usage", extra={
               "operation": operation_name,
               "current_memory_mb": round(current_memory / 1024 / 1024, 2),
               "memory_delta_mb": round(memory_delta / 1024 / 1024, 2),
               "baseline_memory_mb": round(self.baseline_memory / 1024 / 1024, 2)
           })
       
       def reset_baseline(self):
           """Reset memory baseline for delta calculations."""
           self.baseline_memory = self.process.memory_info().rss
   
   # Usage
   memory_monitor = MemoryMonitor()
   
   # Monitor memory usage during operations
   memory_monitor.log_memory_usage("application_startup")
   
   # Perform memory-intensive operation
   large_data = process_large_dataset()
   memory_monitor.log_memory_usage("after_large_dataset_processing")

File I/O Optimization
---------------------

**1. File logging performance considerations**

.. code-block:: python

   import os
   from mypylogger import get_logger
   
   def configure_file_logging_for_performance():
       """Configure file logging for optimal performance."""
       
       # Performance considerations for file logging:
       
       # 1. Use fast storage (SSD preferred over HDD)
       os.environ["LOG_FILE_DIR"] = "/fast/ssd/logs"  # Use SSD if available
       
       # 2. Consider disabling file logging for high-performance scenarios
       high_performance_mode = os.getenv("HIGH_PERFORMANCE_MODE", "false")
       if high_performance_mode.lower() == "true":
           os.environ["LOG_TO_FILE"] = "false"  # Console only for max speed
       else:
           os.environ["LOG_TO_FILE"] = "true"
       
       return get_logger()

**2. Disk I/O impact measurement**

.. code-block:: python

   import time
   import os
   from mypylogger import get_logger
   
   def measure_file_logging_impact():
       """Measure performance impact of file logging vs console-only."""
       
       test_iterations = 1000
       
       # Test console-only logging
       os.environ["LOG_TO_FILE"] = "false"
       console_logger = get_logger("console_test")
       
       start_time = time.time()
       for i in range(test_iterations):
           console_logger.info(f"Console message {i}", extra={"iteration": i})
       console_duration = time.time() - start_time
       
       # Test file + console logging
       os.environ["LOG_TO_FILE"] = "true"
       os.environ["LOG_FILE_DIR"] = "/tmp/perf_test"
       file_logger = get_logger("file_test")
       
       start_time = time.time()
       for i in range(test_iterations):
           file_logger.info(f"File message {i}", extra={"iteration": i})
       file_duration = time.time() - start_time
       
       # Report results
       console_avg = (console_duration / test_iterations) * 1000  # ms per log
       file_avg = (file_duration / test_iterations) * 1000       # ms per log
       overhead = ((file_duration - console_duration) / console_duration) * 100
       
       print(f"Console-only: {console_avg:.3f}ms per log")
       print(f"File + console: {file_avg:.3f}ms per log")
       print(f"File logging overhead: {overhead:.1f}%")

High-Throughput Scenarios
-------------------------

**1. Throughput optimization strategies**

.. code-block:: python

   import os
   import threading
   import queue
   import time
   from mypylogger import get_logger
   
   class HighThroughputLogger:
       """Optimized logger for high-throughput scenarios."""
       
       def __init__(self, max_queue_size=10000):
           # Configure for maximum performance
           os.environ["LOG_LEVEL"] = "WARNING"  # Minimal logging
           os.environ["LOG_TO_FILE"] = "false"  # Console only for speed
           
           self.logger = get_logger(__name__)
           self.log_queue = queue.Queue(maxsize=max_queue_size)
           self.worker_thread = threading.Thread(target=self._log_worker, daemon=True)
           self.worker_thread.start()
           self.shutdown = False
       
       def log_async(self, level, message, extra=None):
           """Log message asynchronously to avoid blocking main thread."""
           try:
               self.log_queue.put_nowait((level, message, extra))
           except queue.Full:
               # Queue full - drop message to avoid blocking
               pass
       
       def _log_worker(self):
           """Background worker thread for processing log messages."""
           while not self.shutdown:
               try:
                   level, message, extra = self.log_queue.get(timeout=1.0)
                   
                   # Log the message
                   log_method = getattr(self.logger, level.lower())
                   if extra:
                       log_method(message, extra=extra)
                   else:
                       log_method(message)
                   
                   self.log_queue.task_done()
               except queue.Empty:
                   continue
               except Exception as e:
                   # Handle logging errors gracefully
                   print(f"Logging error: {e}")
       
       def shutdown_logger(self):
           """Shutdown the async logger and wait for queue to empty."""
           self.shutdown = True
           self.log_queue.join()  # Wait for all messages to be processed
           self.worker_thread.join()
   
   # Usage for high-throughput scenarios
   async_logger = HighThroughputLogger()
   
   def high_frequency_operation():
       """Example of high-frequency logging."""
       for i in range(10000):
           # Non-blocking log call
           async_logger.log_async("INFO", f"Operation {i}", {"iteration": i})
           
           # Continue with main work without waiting for log I/O
           perform_fast_operation()

**2. Throughput measurement and monitoring**

.. code-block:: python

   import time
   import threading
   from collections import deque
   from mypylogger import get_logger
   
   class ThroughputMonitor:
       """Monitor logging throughput and performance."""
       
       def __init__(self, window_size=60):  # 60-second window
           self.logger = get_logger(__name__)
           self.window_size = window_size
           self.log_timestamps = deque()
           self.lock = threading.Lock()
       
       def record_log_event(self):
           """Record a log event for throughput calculation."""
           current_time = time.time()
           
           with self.lock:
               self.log_timestamps.append(current_time)
               
               # Remove old timestamps outside the window
               cutoff_time = current_time - self.window_size
               while self.log_timestamps and self.log_timestamps[0] < cutoff_time:
                   self.log_timestamps.popleft()
       
       def get_current_throughput(self):
           """Get current logging throughput (logs per second)."""
           with self.lock:
               if len(self.log_timestamps) < 2:
                   return 0.0
               
               time_span = self.log_timestamps[-1] - self.log_timestamps[0]
               if time_span == 0:
                   return 0.0
               
               return len(self.log_timestamps) / time_span
       
       def log_throughput_stats(self):
           """Log current throughput statistics."""
           throughput = self.get_current_throughput()
           
           self.logger.info("Logging throughput", extra={
               "logs_per_second": round(throughput, 2),
               "window_size_seconds": self.window_size,
               "sample_count": len(self.log_timestamps)
           })
   
   # Usage
   throughput_monitor = ThroughputMonitor()
   
   def monitored_logging_operation():
       logger = get_logger(__name__)
       
       for i in range(1000):
           logger.info(f"Operation {i}")
           throughput_monitor.record_log_event()
           
           # Log throughput stats every 100 operations
           if i % 100 == 0:
               throughput_monitor.log_throughput_stats()

Container and Cloud Optimization
--------------------------------

**1. Container-optimized configuration**

.. code-block:: python

   import os
   from mypylogger import get_logger
   
   def configure_for_containers():
       """Optimize mypylogger configuration for containerized environments."""
       
       # Container-specific optimizations
       container_config = {
           "APP_NAME": os.getenv("SERVICE_NAME", "app"),  # Use service name
           "LOG_LEVEL": "INFO",                           # Balanced logging
           "LOG_TO_FILE": "false"                         # Let container runtime handle files
       }
       
       # Detect container environment
       if os.path.exists("/.dockerenv") or os.getenv("KUBERNETES_SERVICE_HOST"):
           # Running in container - optimize for container logging
           container_config["LOG_TO_FILE"] = "false"
       
       os.environ.update(container_config)
       return get_logger()

**2. Serverless optimization (AWS Lambda)**

.. code-block:: python

   import os
   import json
   from mypylogger import get_logger
   
   # Lambda-optimized configuration
   os.environ.update({
       "LOG_LEVEL": "INFO",
       "LOG_TO_FILE": "false",  # CloudWatch handles log collection
       "APP_NAME": "lambda-function"
   })
   
   logger = get_logger()
   
   def optimized_lambda_handler(event, context):
       """Lambda handler optimized for performance and cost."""
       
       # Minimal logging to reduce CloudWatch costs
       logger.info("Invocation", extra={
           "request_id": context.aws_request_id,
           "remaining_ms": context.get_remaining_time_in_millis()
       })
       
       try:
           result = process_event(event)
           
           # Log only essential success information
           logger.info("Success", extra={
               "request_id": context.aws_request_id,
               "result_size": len(json.dumps(result))
           })
           
           return result
           
       except Exception as e:
           # Always log errors for debugging
           logger.error("Error", extra={
               "request_id": context.aws_request_id,
               "error": str(e),
               "error_type": type(e).__name__
           })
           raise

Performance Testing and Benchmarking
------------------------------------

**1. Custom performance benchmarks**

.. code-block:: python

   import time
   import statistics
   from mypylogger import get_logger
   
   class PerformanceBenchmark:
       """Custom performance benchmarking for mypylogger."""
       
       def __init__(self):
           self.logger = get_logger(__name__)
       
       def benchmark_logger_creation(self, iterations=100):
           """Benchmark logger creation performance."""
           times = []
           
           for i in range(iterations):
               start_time = time.perf_counter()
               test_logger = get_logger(f"test_logger_{i}")
               end_time = time.perf_counter()
               
               times.append((end_time - start_time) * 1000)  # Convert to ms
           
           return {
               "mean_ms": statistics.mean(times),
               "median_ms": statistics.median(times),
               "min_ms": min(times),
               "max_ms": max(times),
               "std_dev_ms": statistics.stdev(times) if len(times) > 1 else 0
           }
       
       def benchmark_log_operations(self, iterations=1000):
           """Benchmark log operation performance."""
           logger = get_logger("benchmark_logger")
           times = []
           
           for i in range(iterations):
               start_time = time.perf_counter()
               logger.info(f"Benchmark message {i}", extra={"iteration": i})
               end_time = time.perf_counter()
               
               times.append((end_time - start_time) * 1000)  # Convert to ms
           
           return {
               "mean_ms": statistics.mean(times),
               "median_ms": statistics.median(times),
               "min_ms": min(times),
               "max_ms": max(times),
               "std_dev_ms": statistics.stdev(times) if len(times) > 1 else 0,
               "throughput_per_second": 1000 / statistics.mean(times)
           }
       
       def run_full_benchmark(self):
           """Run complete performance benchmark suite."""
           self.logger.info("Starting performance benchmark")
           
           # Benchmark logger creation
           creation_stats = self.benchmark_logger_creation()
           self.logger.info("Logger creation benchmark", extra=creation_stats)
           
           # Benchmark log operations
           operation_stats = self.benchmark_log_operations()
           self.logger.info("Log operation benchmark", extra=operation_stats)
           
           return {
               "logger_creation": creation_stats,
               "log_operations": operation_stats
           }
   
   # Usage
   benchmark = PerformanceBenchmark()
   results = benchmark.run_full_benchmark()

**2. Continuous performance monitoring**

.. code-block:: python

   import time
   import threading
   from mypylogger import get_logger
   
   class ContinuousPerformanceMonitor:
       """Monitor mypylogger performance continuously in production."""
       
       def __init__(self, sample_interval=300):  # Sample every 5 minutes
           self.logger = get_logger(__name__)
           self.sample_interval = sample_interval
           self.monitoring = True
           self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
           self.monitor_thread.start()
       
       def _monitor_loop(self):
           """Continuous monitoring loop."""
           while self.monitoring:
               try:
                   # Measure current performance
                   perf_stats = self._measure_current_performance()
                   
                   # Log performance metrics
                   self.logger.info("Performance metrics", extra=perf_stats)
                   
                   time.sleep(self.sample_interval)
               except Exception as e:
                   self.logger.error("Performance monitoring error", extra={"error": str(e)})
       
       def _measure_current_performance(self):
           """Measure current logging performance."""
           test_iterations = 10
           start_time = time.perf_counter()
           
           test_logger = get_logger("perf_monitor_test")
           for i in range(test_iterations):
               test_logger.info(f"Performance test {i}")
           
           end_time = time.perf_counter()
           avg_time_ms = ((end_time - start_time) / test_iterations) * 1000
           
           return {
               "avg_log_time_ms": round(avg_time_ms, 3),
               "throughput_per_second": round(1000 / avg_time_ms, 2),
               "test_iterations": test_iterations,
               "timestamp": time.time()
           }
       
       def stop_monitoring(self):
           """Stop continuous performance monitoring."""
           self.monitoring = False
           self.monitor_thread.join()
   
   # Usage in production
   perf_monitor = ContinuousPerformanceMonitor(sample_interval=600)  # Every 10 minutes

High-Throughput Scenarios
-------------------------

For applications with very high log volume:

**1. Consider log level filtering**

.. code-block:: python

   # Filter at the source
   os.environ["LOG_LEVEL"] = "ERROR"  # Only errors and critical

**2. Use structured data efficiently**

.. code-block:: python

   # Efficient: Simple data types
   logger.info("User action", extra={
       "user_id": "123",
       "action": "login",
       "timestamp": 1642781445
   })
   
   # Less efficient: Complex objects
   logger.info("User action", extra={
       "user": user_object,  # Avoid complex objects
       "metadata": nested_dict  # Avoid deep nesting
   })

**3. Consider async patterns for I/O-heavy applications**

.. code-block:: python

   import asyncio
   from concurrent.futures import ThreadPoolExecutor
   from mypylogger import get_logger
   
   logger = get_logger(__name__)
   
   async def log_async(message, extra_data):
       # Offload logging to thread pool for I/O-heavy apps
       loop = asyncio.get_event_loop()
       with ThreadPoolExecutor() as executor:
           await loop.run_in_executor(executor, logger.info, message, extra_data)

Memory Optimization
-------------------

**1. Avoid logger proliferation**

.. code-block:: python

   # Good: Module-level logger
   logger = get_logger(__name__)
   
   class MyClass:
       def method(self):
           logger.info("Method called")  # Reuse module logger
   
   # Avoid: Logger per instance
   class MyClass:
       def __init__(self):
           self.logger = get_logger(f"{__name__}.{id(self)}")  # Memory waste

**2. Limit extra data size**

.. code-block:: python

   # Good: Essential data only
   logger.info("File processed", extra={
       "filename": "data.csv",
       "size_bytes": 1024,
       "duration_ms": 150
   })
   
   # Avoid: Large data dumps
   logger.info("File processed", extra={
       "file_contents": large_string,  # Avoid large strings
       "full_metadata": huge_dict      # Avoid large objects
   })

Container Optimization
----------------------

For containerized applications:

**1. Use stdout logging**

.. code-block:: bash

   # Let container runtime handle log collection
   export LOG_TO_FILE="false"

**2. Configure appropriate log levels**

.. code-block:: dockerfile

   # Dockerfile
   ENV LOG_LEVEL="INFO"
   ENV APP_NAME="myapp"

**3. Consider log rotation at container level**

.. code-block:: yaml

   # docker-compose.yml
   services:
     app:
       logging:
         driver: "json-file"
         options:
           max-size: "10m"
           max-file: "3"

Performance Monitoring
----------------------

Monitor mypylogger performance in your application:

.. code-block:: python

   import time
   from mypylogger import get_logger
   
   logger = get_logger(__name__)
   
   def timed_operation():
       start_time = time.time()
       
       # Your operation here
       result = perform_operation()
       
       duration = time.time() - start_time
       logger.info("Operation completed", extra={
           "operation": "data_processing",
           "duration_ms": round(duration * 1000, 2),
           "result_size": len(result)
       })
       
       return result

When to Consider Alternatives
-----------------------------

Consider specialized logging solutions if you need:

* **Extreme throughput**: >10,000 logs/second sustained
* **Complex routing**: Multiple destinations with different formats
* **Advanced filtering**: Complex log processing rules
* **Minimal latency**: Sub-millisecond logging requirements

For these scenarios, consider:
* Direct syslog integration
* Specialized high-performance loggers
* Custom logging solutions
* Log aggregation at infrastructure level