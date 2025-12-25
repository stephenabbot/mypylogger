Formatters Module
=================

The formatters module provides JSON formatting with automatic source location tracking.

Formatter Classes
-----------------

.. autoclass:: mypylogger.formatters.SourceLocationJSONFormatter
   :members:
   :undoc-members:
   :show-inheritance:

JSON Output Format
------------------

mypylogger produces consistent JSON output with the following characteristics:

* **Timestamp first**: Always the first field for chronological sorting
* **Flat structure**: No nested objects for simple parsing and querying
* **Consistent keys**: Predictable field names across all log entries
* **Source location**: Automatic tracking of module, filename, function, and line number
* **Human readable**: ISO format timestamps and clear field names

**Standard Fields**

Every log entry includes these standard fields in this order:

.. code-block:: json

   {
     "timestamp": "2025-01-21T10:30:45.123456Z",
     "level": "INFO",
     "message": "User action completed",
     "module": "myapp.user_service",
     "filename": "user_service.py",
     "function_name": "process_login",
     "line": 42
   }

Usage Examples
--------------

**Basic JSON Formatting**

.. code-block:: python

   from mypylogger import get_logger
   
   logger = get_logger("user_service")
   logger.info("User login successful")
   
   # Output:
   # {"timestamp":"2025-01-21T10:30:45.123456Z","level":"INFO","message":"User login successful","module":"user_service","filename":"main.py","function_name":"login","line":15}

**Custom Fields with Extra Parameter**

.. code-block:: python

   logger = get_logger("api")
   logger.info("Request processed", extra={
       "user_id": "12345",
       "endpoint": "/api/users",
       "response_time_ms": 150
   })
   
   # Output:
   # {"timestamp":"2025-01-21T10:30:45.123456Z","level":"INFO","message":"Request processed","module":"api","filename":"handlers.py","function_name":"handle_request","line":28,"user_id":"12345","endpoint":"/api/users","response_time_ms":150}

**Exception Handling**

.. code-block:: python

   try:
       result = risky_operation()
   except Exception as e:
       logger.error("Operation failed", exc_info=True)
   
   # Output includes exception information:
   # {"timestamp":"2025-01-21T10:30:45.123456Z","level":"ERROR","message":"Operation failed","module":"service","filename":"operations.py","function_name":"risky_operation","line":45,"exc_info":"Traceback (most recent call last)..."}

**Different Log Levels**

.. code-block:: python

   logger = get_logger("monitoring")
   
   logger.debug("Detailed debugging information")
   logger.info("General information")
   logger.warning("Something unexpected happened")
   logger.error("An error occurred")
   logger.critical("System is in critical state")
   
   # Each produces JSON with appropriate level field:
   # {"timestamp":"...","level":"DEBUG","message":"Detailed debugging information",...}
   # {"timestamp":"...","level":"INFO","message":"General information",...}
   # {"timestamp":"...","level":"WARNING","message":"Something unexpected happened",...}
   # {"timestamp":"...","level":"ERROR","message":"An error occurred",...}
   # {"timestamp":"...","level":"CRITICAL","message":"System is in critical state",...}

**Complex Data Serialization**

.. code-block:: python

   # mypylogger handles complex data gracefully
   logger.info("Processing user data", extra={
       "user": {
           "id": 12345,
           "name": "John Doe",
           "preferences": ["email", "sms"]
       },
       "timestamp": "2025-01-21T10:30:45Z",
       "metadata": {"source": "web", "version": "1.2.3"}
   })
   
   # Non-serializable data is handled gracefully:
   import threading
   logger.info("Thread info", extra={
       "thread_id": threading.current_thread().ident,  # ✓ Serializable
       "thread_obj": threading.current_thread()        # ✗ Skipped gracefully
   })

**Source Location Tracking**

.. code-block:: python

   # File: /app/services/user_manager.py
   def create_user(username):
       logger = get_logger(__name__)
       logger.info(f"Creating user: {username}")  # Line 25
   
   # Output automatically includes source location:
   # {
   #   "timestamp": "2025-01-21T10:30:45.123456Z",
   #   "level": "INFO",
   #   "message": "Creating user: john_doe",
   #   "module": "services.user_manager",
   #   "filename": "services/user_manager.py",
   #   "function_name": "create_user",
   #   "line": 25
   # }

Formatter Features
------------------

**Timestamp Formatting**

* **ISO 8601 format**: ``2025-01-21T10:30:45.123456Z``
* **UTC timezone**: All timestamps in UTC for consistency
* **Microsecond precision**: High precision for debugging and correlation
* **Always first field**: Enables chronological sorting in log aggregation tools

**Field Ordering**

Fields appear in this consistent order:

1. ``timestamp`` - ISO 8601 UTC timestamp
2. ``level`` - Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
3. ``message`` - The formatted log message
4. ``module`` - Python module name
5. ``filename`` - Relative path to source file
6. ``function_name`` - Function where log was called
7. ``line`` - Line number where log was called
8. Custom fields from ``extra`` parameter (alphabetically sorted)

**Error Handling and Fallbacks**

* **Graceful degradation**: Falls back to plain text if JSON serialization fails
* **Non-serializable data**: Skips fields that can't be JSON serialized
* **Source location fallback**: Uses record information if stack inspection fails
* **Never crashes**: Formatting errors are logged to stderr, not raised

**Unicode and International Support**

.. code-block:: python

   logger.info("用户登录成功", extra={"用户名": "张三", "città": "Roma"})
   
   # Output with full Unicode support:
   # {"timestamp":"2025-01-21T10:30:45.123456Z","level":"INFO","message":"用户登录成功","用户名":"张三","città":"Roma",...}

**Integration with Log Aggregation Tools**

The consistent JSON format works seamlessly with:

* **Splunk**: Direct JSON parsing with predictable field names
* **Elasticsearch/ELK**: Automatic field mapping and indexing
* **CloudWatch Logs**: JSON log parsing and filtering
* **Datadog**: Structured log analysis and alerting
* **Fluentd/Fluent Bit**: JSON log forwarding and processing

The flat structure and consistent field names make it easy to create dashboards, alerts, and queries across different log aggregation platforms.