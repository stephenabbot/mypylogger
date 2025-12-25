Quick Start Guide
=================

Get up and running with mypylogger in under 5 minutes! This guide will take you from installation to production-ready logging.

⏱️ 5-Minute Tutorial
--------------------

**Step 1: Installation (30 seconds)**

.. code-block:: bash

   pip install mypylogger

**Step 2: Hello World (1 minute)**

Create a file called ``hello_logger.py``:

.. code-block:: python

   from mypylogger import get_logger
   
   # Create a logger
   logger = get_logger(__name__)
   
   # Log your first message
   logger.info("Hello, World!")
   logger.info("mypylogger is working!", extra={"status": "success"})

Run it:

.. code-block:: bash

   python hello_logger.py

**Expected Output:**

.. code-block:: json

   {"time":"2025-01-21T10:30:45.123456Z","levelname":"INFO","name":"__main__","message":"Hello, World!"}
   {"time":"2025-01-21T10:30:45.123457Z","levelname":"INFO","name":"__main__","message":"mypylogger is working!","status":"success"}

✅ **Success!** You now have structured JSON logging working.

**Step 3: Add Structure (2 minutes)**

Create ``structured_example.py`` to see the power of structured logging:

.. code-block:: python

   from mypylogger import get_logger
   
   logger = get_logger("my_app")
   
   # Log with context
   logger.info("User action", extra={
       "user_id": "12345",
       "action": "login",
       "ip_address": "192.168.1.100",
       "success": True
   })
   
   # Log different levels
   logger.debug("Debug info - only visible if LOG_LEVEL=DEBUG")
   logger.info("Application event")
   logger.warning("Something needs attention")
   logger.error("An error occurred")

**Output:**

.. code-block:: json

   {"time":"2025-01-21T10:30:45.123456Z","levelname":"INFO","name":"my_app","message":"User action","user_id":"12345","action":"login","ip_address":"192.168.1.100","success":true}
   {"time":"2025-01-21T10:30:45.123457Z","levelname":"INFO","name":"my_app","message":"Application event"}
   {"time":"2025-01-21T10:30:45.123458Z","levelname":"WARNING","name":"my_app","message":"Something needs attention"}
   {"time":"2025-01-21T10:30:45.123459Z","levelname":"ERROR","name":"my_app","message":"An error occurred"}

**Step 4: File Logging (1.5 minutes)**

Create ``file_logging_example.py`` to save logs to files:

.. code-block:: python

   import os
   from mypylogger import get_logger
   
   # Configure file logging
   os.environ["LOG_TO_FILE"] = "true"
   os.environ["LOG_FILE_DIR"] = "./logs"
   os.environ["APP_NAME"] = "tutorial_app"
   
   logger = get_logger()
   
   logger.info("This goes to both console AND file")
   logger.info("File location: ./logs/tutorial_app.log")
   
   # Check if file was created
   import pathlib
   log_file = pathlib.Path("./logs/tutorial_app.log")
   if log_file.exists():
       print(f"✅ Log file created: {log_file.absolute()}")
       print(f"📄 File size: {log_file.stat().st_size} bytes")
   else:
       print("❌ Log file not found")

**🎉 Congratulations!** In 5 minutes, you've learned:

- ✅ Basic JSON logging
- ✅ Structured logging with context
- ✅ Different log levels
- ✅ File logging configuration

Core Concepts
-------------

**1. Zero Configuration**

mypylogger works immediately without any setup:

.. code-block:: python

   from mypylogger import get_logger
   
   logger = get_logger(__name__)
   logger.info("It just works!")

**2. Structured Logging**

Add context to your logs using the ``extra`` parameter:

.. code-block:: python

   logger.info("User action", extra={
       "user_id": "12345",
       "action": "purchase",
       "amount": 99.99,
       "currency": "USD"
   })

**Output:**

.. code-block:: json

   {"time":"2025-01-21T10:30:45.123456Z","levelname":"INFO","name":"myapp","message":"User action","user_id":"12345","action":"purchase","amount":99.99,"currency":"USD"}

**3. Environment-Driven Configuration**

Configure behavior without changing code:

.. code-block:: bash

   # Set application name
   export APP_NAME="myapp"
   
   # Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
   export LOG_LEVEL="INFO"
   
   # Enable file logging
   export LOG_TO_FILE="true"
   export LOG_FILE_DIR="/var/log/myapp"

**4. Standard Python Patterns**

mypylogger uses familiar Python logging patterns:

.. code-block:: python

   # Per-module loggers (recommended)
   logger = get_logger(__name__)
   
   # Named loggers
   logger = get_logger("database")
   logger = get_logger("api.auth")
   
   # Application logger (uses APP_NAME env var)
   logger = get_logger()

Log Levels and Usage
--------------------

mypylogger supports all standard Python logging levels:

.. code-block:: python

   logger = get_logger(__name__)
   
   # DEBUG - Detailed diagnostic information
   logger.debug("Database query executed", extra={"query": "SELECT * FROM users", "duration_ms": 45})
   
   # INFO - General application flow
   logger.info("User logged in", extra={"user_id": "12345"})
   
   # WARNING - Something unexpected but not an error
   logger.warning("API rate limit approaching", extra={"requests_remaining": 10})
   
   # ERROR - An error occurred but application continues
   logger.error("Failed to send email", extra={"recipient": "user@example.com", "error": "SMTP timeout"})
   
   # CRITICAL - Serious error, application may not continue
   logger.critical("Database connection lost", extra={"host": "db.example.com"})

**Setting Log Level:**

.. code-block:: bash

   # Show all messages (DEBUG and above)
   export LOG_LEVEL="DEBUG"
   
   # Show INFO and above (default)
   export LOG_LEVEL="INFO"
   
   # Show only warnings and errors
   export LOG_LEVEL="WARNING"

Configuration Options
---------------------

**Environment Variables:**

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Variable
     - Default
     - Description
   * - ``APP_NAME``
     - ``"mypylogger"``
     - Default logger name when none provided
   * - ``LOG_LEVEL``
     - ``"INFO"``
     - Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
   * - ``LOG_TO_FILE``
     - ``"false"``
     - Enable file logging (true/false)
   * - ``LOG_FILE_DIR``
     - ``"./logs"``
     - Directory for log files
   * - ``LOG_IMMEDIATE_FLUSH``
     - ``"true"``
     - Flush logs immediately for real-time monitoring

**Configuration Examples:**

.. code-block:: python

   import os
   
   # Development configuration
   os.environ["LOG_LEVEL"] = "DEBUG"
   os.environ["LOG_TO_FILE"] = "false"  # Console only
   
   # Production configuration
   os.environ["APP_NAME"] = "myapp"
   os.environ["LOG_LEVEL"] = "INFO"
   os.environ["LOG_TO_FILE"] = "true"
   os.environ["LOG_FILE_DIR"] = "/var/log/myapp"

File Logging
------------

**Basic File Logging:**

.. code-block:: python

   import os
   from mypylogger import get_logger
   
   # Enable file logging
   os.environ["LOG_TO_FILE"] = "true"
   os.environ["LOG_FILE_DIR"] = "./logs"
   
   logger = get_logger("myapp")
   logger.info("This message goes to both console and file")

**File Location:**

- **File name:** ``{logger_name}.log`` (e.g., ``myapp.log``)
- **Directory:** Value of ``LOG_FILE_DIR`` environment variable
- **Full path:** ``{LOG_FILE_DIR}/{logger_name}.log``

**File Behavior:**

- **Automatic creation:** Directories and files are created automatically
- **Append mode:** New logs are appended to existing files
- **Immediate flush:** Logs are written immediately (configurable)
- **Graceful fallback:** If file logging fails, continues with console logging

Real-World Examples
-------------------

**Web Application Logging:**

.. code-block:: python

   import os
   from mypylogger import get_logger
   
   # Configure for production
   os.environ["APP_NAME"] = "webapp"
   os.environ["LOG_LEVEL"] = "INFO"
   os.environ["LOG_TO_FILE"] = "true"
   os.environ["LOG_FILE_DIR"] = "/var/log/webapp"
   
   logger = get_logger(__name__)
   
   def handle_request(request):
       logger.info("Request received", extra={
           "method": request.method,
           "path": request.path,
           "user_agent": request.headers.get("User-Agent"),
           "ip": request.remote_addr
       })
       
       try:
           response = process_request(request)
           logger.info("Request completed", extra={
               "status_code": response.status_code,
               "response_time_ms": response.duration
           })
           return response
           
       except Exception as e:
           logger.error("Request failed", extra={
               "error": str(e),
               "traceback": traceback.format_exc()
           })
           raise

**CLI Application Logging:**

.. code-block:: python

   import os
   import sys
   from mypylogger import get_logger
   
   def main():
       # Configure based on verbosity
       verbose = "--verbose" in sys.argv
       os.environ["LOG_LEVEL"] = "DEBUG" if verbose else "INFO"
       
       logger = get_logger("cli_tool")
       
       logger.info("CLI tool started", extra={"args": sys.argv[1:]})
       
       try:
           result = do_work()
           logger.info("Operation completed", extra={"result": result})
           return 0
           
       except Exception as e:
           logger.error("Operation failed", extra={"error": str(e)})
           return 1
       
       finally:
           logger.info("CLI tool finished")

**Microservice Logging:**

.. code-block:: python

   import os
   from mypylogger import get_logger
   
   # Kubernetes-friendly configuration
   os.environ["APP_NAME"] = "user-service"
   os.environ["LOG_LEVEL"] = "INFO"
   os.environ["LOG_TO_FILE"] = "false"  # Use stdout for container logs
   
   logger = get_logger(__name__)
   
   def process_user_event(event):
       correlation_id = event.get("correlation_id", "unknown")
       
       logger.info("Processing user event", extra={
           "correlation_id": correlation_id,
           "event_type": event["type"],
           "user_id": event["user_id"]
       })
       
       try:
           result = handle_event(event)
           logger.info("Event processed successfully", extra={
               "correlation_id": correlation_id,
               "processing_time_ms": result["duration"]
           })
           
       except ValidationError as e:
           logger.warning("Invalid event data", extra={
               "correlation_id": correlation_id,
               "validation_errors": e.errors
           })
           
       except Exception as e:
           logger.error("Event processing failed", extra={
               "correlation_id": correlation_id,
               "error": str(e)
           })

Common Patterns
---------------

**Error Handling with Context:**

.. code-block:: python

   def risky_operation(user_id):
       logger = get_logger(__name__)
       
       try:
           result = external_api_call(user_id)
           logger.info("API call successful", extra={
               "user_id": user_id,
               "response_size": len(result)
           })
           return result
           
       except requests.Timeout:
           logger.error("API timeout", extra={
               "user_id": user_id,
               "timeout_seconds": 30
           })
           raise
           
       except requests.HTTPError as e:
           logger.error("API HTTP error", extra={
               "user_id": user_id,
               "status_code": e.response.status_code,
               "response_body": e.response.text[:500]  # Truncate long responses
           })
           raise

**Performance Monitoring:**

.. code-block:: python

   import time
   
   def timed_operation(operation_name):
       logger = get_logger(__name__)
       start_time = time.time()
       
       logger.info("Operation started", extra={"operation": operation_name})
       
       try:
           result = perform_operation()
           duration = time.time() - start_time
           
           logger.info("Operation completed", extra={
               "operation": operation_name,
               "duration_seconds": round(duration, 3),
               "success": True
           })
           
           return result
           
       except Exception as e:
           duration = time.time() - start_time
           
           logger.error("Operation failed", extra={
               "operation": operation_name,
               "duration_seconds": round(duration, 3),
               "error": str(e),
               "success": False
           })
           raise

**Batch Processing:**

.. code-block:: python

   def process_batch(items):
       logger = get_logger(__name__)
       batch_id = str(uuid.uuid4())
       
       logger.info("Batch processing started", extra={
           "batch_id": batch_id,
           "item_count": len(items)
       })
       
       processed = 0
       errors = 0
       
       for item in items:
           try:
               process_item(item)
               processed += 1
               
               # Log progress every 100 items
               if processed % 100 == 0:
                   logger.info("Batch progress", extra={
                       "batch_id": batch_id,
                       "processed": processed,
                       "remaining": len(items) - processed
                   })
                   
           except Exception as e:
               errors += 1
               logger.error("Item processing failed", extra={
                   "batch_id": batch_id,
                   "item_id": item.get("id"),
                   "error": str(e)
               })
       
       logger.info("Batch processing completed", extra={
           "batch_id": batch_id,
           "total_items": len(items),
           "processed": processed,
           "errors": errors,
           "success_rate": round(processed / len(items) * 100, 2)
       })

Best Practices
--------------

**1. Use Module-Level Loggers**

.. code-block:: python

   # ✅ Good - Each module has its own logger
   logger = get_logger(__name__)
   
   # ❌ Avoid - Shared logger across modules
   logger = get_logger("shared")

**2. Include Relevant Context**

.. code-block:: python

   # ✅ Good - Structured context
   logger.info("User action", extra={
       "user_id": user.id,
       "action": "purchase",
       "amount": order.total
   })
   
   # ❌ Avoid - Unstructured messages
   logger.info(f"User {user.id} purchased ${order.total}")

**3. Use Appropriate Log Levels**

.. code-block:: python

   # ✅ Good - Appropriate levels
   logger.debug("SQL query executed")      # Development info
   logger.info("User logged in")           # Business events
   logger.warning("Rate limit exceeded")   # Attention needed
   logger.error("Payment failed")          # Errors
   logger.critical("Database unavailable") # System failures
   
   # ❌ Avoid - Wrong levels
   logger.error("User logged in")          # Not an error
   logger.info("System crashed")           # Too low level

**4. Handle Sensitive Data**

.. code-block:: python

   # ✅ Good - Mask sensitive data
   logger.info("Payment processed", extra={
       "user_id": user.id,
       "card_last_four": card.number[-4:],
       "amount": payment.amount
   })
   
   # ❌ Avoid - Logging sensitive data
   logger.info("Payment processed", extra={
       "credit_card": card.number,  # Never log full card numbers
       "password": user.password    # Never log passwords
   })

Troubleshooting
---------------

**No Output Visible**

Check log level configuration:

.. code-block:: python

   import os
   
   # Ensure DEBUG messages are visible
   os.environ["LOG_LEVEL"] = "DEBUG"
   
   logger = get_logger(__name__)
   logger.debug("This should now be visible")

**File Logging Not Working**

Verify file logging configuration:

.. code-block:: python

   import os
   import pathlib
   
   # Check configuration
   print(f"LOG_TO_FILE: {os.getenv('LOG_TO_FILE')}")
   print(f"LOG_FILE_DIR: {os.getenv('LOG_FILE_DIR')}")
   
   # Ensure directory exists and is writable
   log_dir = pathlib.Path(os.getenv("LOG_FILE_DIR", "./logs"))
   print(f"Directory exists: {log_dir.exists()}")
   print(f"Directory writable: {os.access(log_dir, os.W_OK)}")

**JSON Format Issues**

Ensure extra data is JSON-serializable:

.. code-block:: python

   import datetime
   import json
   
   # ✅ Good - JSON-serializable data
   logger.info("Event", extra={
       "timestamp": datetime.datetime.now().isoformat(),
       "count": 42,
       "success": True
   })
   
   # ❌ Avoid - Non-serializable objects
   logger.info("Event", extra={
       "datetime_obj": datetime.datetime.now(),  # Not JSON-serializable
       "custom_obj": MyCustomClass()             # Not JSON-serializable
   })

Next Steps
----------

Now that you're up and running:

1. **📖 Read the Configuration Guide** - :doc:`guides/configuration` for advanced environment setup
2. **🔍 Explore the API Reference** - :doc:`api/index` for detailed function documentation  
3. **💡 Check Real-World Examples** - :doc:`examples/index` for Flask, Django, FastAPI integration
4. **⚡ Performance Optimization** - :doc:`performance/index` for high-throughput scenarios
5. **🔧 Framework Integration** - :doc:`guides/frameworks` for web framework patterns

**Happy Logging! 🎉**