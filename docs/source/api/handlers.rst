Handlers Module
===============

The handlers module manages log output destinations with automatic fallback logic.

Handler Classes
---------------

.. autoclass:: mypylogger.handlers.HandlerFactory
   :members:
   :undoc-members:
   :show-inheritance:

Handler Types
-------------

mypylogger automatically configures appropriate handlers based on your environment configuration:

* **Console Handler**: Always enabled, outputs to stdout with immediate flush
* **File Handler**: Optional, enabled via ``LOG_TO_FILE`` environment variable

Usage Examples
--------------

**Console Logging (Default)**

.. code-block:: python

   from mypylogger import get_logger
   
   # Console logging is always enabled
   logger = get_logger("console_app")
   logger.info("This appears on stdout")
   
   # Output to stdout:
   # {"timestamp":"2025-01-21T10:30:45.123456Z","level":"INFO","message":"This appears on stdout",...}

**File Logging Configuration**

.. code-block:: python

   import os
   from mypylogger import get_logger
   
   # Enable file logging
   os.environ["LOG_TO_FILE"] = "true"
   os.environ["LOG_FILE_DIR"] = "/var/log/myapp"
   os.environ["APP_NAME"] = "web_service"
   
   logger = get_logger()
   logger.info("This appears in both console and file")
   
   # Creates file: /var/log/myapp/web_service_20250121_10.log
   # Also outputs to stdout

**File Naming Convention**

File names follow the pattern: ``{APP_NAME}_{YYYYMMDD}_{HH}.log``

.. code-block:: python

   import os
   from datetime import datetime
   
   os.environ["APP_NAME"] = "api_server"
   os.environ["LOG_TO_FILE"] = "true"
   
   logger = get_logger()
   logger.info("Log entry")
   
   # Creates file based on current date/time:
   # api_server_20250121_10.log  (if logged at 10:xx AM on Jan 21, 2025)
   # api_server_20250121_14.log  (if logged at 2:xx PM on Jan 21, 2025)

**Graceful Fallback Behavior**

.. code-block:: python

   import os
   
   # Try to log to a directory that doesn't exist or lacks permissions
   os.environ["LOG_TO_FILE"] = "true"
   os.environ["LOG_FILE_DIR"] = "/root/restricted"  # Permission denied
   
   logger = get_logger("fallback_test")
   logger.info("This will still work")
   
   # mypylogger handles the error gracefully:
   # 1. Tries to create /root/restricted - fails
   # 2. Falls back to temp directory
   # 3. If temp fails, continues with console-only logging
   # 4. Logs error to stderr: "mypylogger: File logging failed, using stdout only"
   # 5. Your application continues running normally

**Multiple Loggers with Different Configurations**

.. code-block:: python

   import os
   
   # Global configuration
   os.environ["LOG_TO_FILE"] = "true"
   os.environ["LOG_FILE_DIR"] = "/var/log"
   
   # Different loggers use the same configuration
   api_logger = get_logger("api")
   db_logger = get_logger("database")
   auth_logger = get_logger("auth")
   
   api_logger.info("API request received")      # Logs to console + /var/log/api_*.log
   db_logger.info("Database query executed")   # Logs to console + /var/log/database_*.log
   auth_logger.info("User authenticated")      # Logs to console + /var/log/auth_*.log

Handler Features
----------------

**Console Handler**

* **Always enabled**: Every logger gets a console handler
* **Stdout output**: Uses stdout (not stderr) for application logs
* **Immediate flush**: Real-time log visibility for development and debugging
* **JSON formatting**: Consistent JSON output format
* **UTF-8 encoding**: Full Unicode support

**File Handler**

* **Optional**: Enabled only when ``LOG_TO_FILE=true``
* **Hourly rotation**: New file each hour for natural log rotation
* **UTF-8 encoding**: Full Unicode support in log files
* **Append mode**: Multiple processes can write to the same file safely
* **Immediate flush**: Real-time file updates
* **Graceful fallback**: Falls back to console-only if file operations fail

**Directory Management**

.. code-block:: python

   # mypylogger automatically creates directories as needed
   os.environ["LOG_FILE_DIR"] = "/var/log/myapp/services/api"
   
   logger = get_logger("handler_test")
   logger.info("Creating nested directories")
   
   # Automatically creates: /var/log/myapp/services/api/
   # Then creates: handler_test_20250121_10.log

**Error Handling**

The handler system includes comprehensive error handling:

* **Permission errors**: Falls back to temp directory, then console-only
* **Disk space issues**: Continues with console logging
* **Network filesystem problems**: Uses local temp directory
* **Invalid paths**: Sanitizes and falls back to safe defaults
* **Concurrent access**: Handles multiple processes writing to same directory

**Performance Characteristics**

* **Immediate flush**: All handlers flush immediately for real-time visibility
* **Minimal overhead**: Simple file operations with no complex buffering
* **Thread-safe**: Uses Python's built-in thread-safe logging handlers
* **Process-safe**: Multiple processes can safely write to different files

**Integration with System Tools**

The file handler works well with standard log management tools:

.. code-block:: bash

   # Log rotation with logrotate
   /var/log/myapp/*.log {
       daily
       rotate 30
       compress
       delaycompress
       missingok
       notifempty
   }
   
   # Real-time monitoring with tail
   tail -f /var/log/myapp/api_*.log
   
   # JSON parsing with jq
   tail -f /var/log/myapp/api_*.log | jq '.message'

This design ensures reliable log delivery while providing flexibility for different deployment environments and operational requirements.