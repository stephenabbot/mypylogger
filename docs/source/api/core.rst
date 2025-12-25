Core Module
===========

The core module provides the main entry points for mypylogger functionality.

Public Functions
----------------

.. autofunction:: mypylogger.get_logger

.. autofunction:: mypylogger.get_version

Core Classes
------------

.. autoclass:: mypylogger.core.LoggerManager
   :members:
   :undoc-members:
   :show-inheritance:

Usage Examples
--------------

**Basic Logger Creation**

.. code-block:: python

   from mypylogger import get_logger
   
   # Get logger with module name
   logger = get_logger(__name__)
   logger.info("Application started")
   # Output: {"timestamp":"2025-01-21T10:30:45.123456Z","level":"INFO","message":"Application started",...}

**Custom Logger Name**

.. code-block:: python

   # Get logger with custom name
   logger = get_logger("my_service")
   logger.warning("Service degraded performance")
   # Output: {"timestamp":"2025-01-21T10:30:45.123456Z","level":"WARNING","message":"Service degraded performance",...}

**Automatic Name Resolution**

.. code-block:: python

   import os
   
   # Set APP_NAME environment variable
   os.environ["APP_NAME"] = "web_api"
   
   # Logger will use APP_NAME when no name provided
   logger = get_logger()
   logger.error("Database connection failed")
   # Output: {"timestamp":"2025-01-21T10:30:45.123456Z","level":"ERROR","message":"Database connection failed",...}

**Version Information**

.. code-block:: python

   from mypylogger import get_version
   
   version = get_version()
   print(f"Using mypylogger version: {version}")
   # Output: Using mypylogger version: 0.2.0

**Logger with Custom Fields**

.. code-block:: python

   logger = get_logger("user_service")
   
   # Add custom fields using extra parameter
   logger.info("User login successful", extra={"user_id": "12345", "ip": "192.168.1.1"})
   # Output: {"timestamp":"2025-01-21T10:30:45.123456Z","level":"INFO","message":"User login successful","user_id":"12345","ip":"192.168.1.1",...}

Key Features
------------

The core module automatically provides:

* **JSON formatting** for all log messages with consistent structure
* **Source location tracking** including module, filename, function, and line number
* **Environment-driven configuration** with sensible defaults
* **Graceful error handling** that never crashes your application
* **Immediate flush** for real-time log visibility
* **Multiple handlers** (console and optional file logging)