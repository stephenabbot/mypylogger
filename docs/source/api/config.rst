Configuration Module
====================

The configuration module manages mypylogger settings through environment variables with safe defaults.

Configuration Classes
---------------------

.. autoclass:: mypylogger.config.LogConfig
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: mypylogger.config.ConfigResolver
   :members:
   :undoc-members:
   :show-inheritance:

Environment Variables
---------------------

mypylogger uses the following environment variables for configuration:

.. list-table:: Environment Variables
   :widths: 25 25 50
   :header-rows: 1

   * - Variable
     - Default
     - Description
   * - ``APP_NAME``
     - ``"mypylogger"``
     - Application name used in log entries and filenames
   * - ``LOG_LEVEL``
     - ``"INFO"``
     - Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
   * - ``LOG_TO_FILE``
     - ``"false"``
     - Enable file logging (true/false, 1/0, yes/no, on/off)
   * - ``LOG_FILE_DIR``
     - ``tempfile.gettempdir()``
     - Directory for log files (falls back to temp directory)

Usage Examples
--------------

**Basic Environment Configuration**

.. code-block:: python

   import os
   from mypylogger import get_logger
   
   # Set configuration via environment
   os.environ["APP_NAME"] = "web_api"
   os.environ["LOG_LEVEL"] = "DEBUG"
   
   logger = get_logger()
   logger.debug("Debug message will be shown")
   # Output: {"timestamp":"2025-01-21T10:30:45.123456Z","level":"DEBUG","message":"Debug message will be shown",...}

**File Logging Configuration**

.. code-block:: python

   import os
   from pathlib import Path
   
   # Enable file logging
   os.environ["LOG_TO_FILE"] = "true"
   os.environ["LOG_FILE_DIR"] = "/var/log/myapp"
   
   logger = get_logger("file_logger")
   logger.info("This will be written to file and console")
   # Creates file: /var/log/myapp/file_logger_20250121_10.log

**Production Configuration**

.. code-block:: python

   import os
   
   # Production settings
   os.environ["APP_NAME"] = "production_api"
   os.environ["LOG_LEVEL"] = "WARNING"  # Only warnings and errors
   os.environ["LOG_TO_FILE"] = "true"
   os.environ["LOG_FILE_DIR"] = "/var/log/production"
   
   logger = get_logger()
   logger.info("This won't appear (below WARNING level)")
   logger.warning("This will appear in logs")
   # Output: {"timestamp":"2025-01-21T10:30:45.123456Z","level":"WARNING","message":"This will appear in logs",...}

**Configuration Validation**

.. code-block:: python

   import os
   from mypylogger.config import ConfigResolver
   
   # Invalid log level will fall back to INFO
   os.environ["LOG_LEVEL"] = "INVALID_LEVEL"
   
   resolver = ConfigResolver()
   config = resolver.resolve_config()
   print(config.log_level)  # Output: INFO (safe default)

**Boolean Configuration Values**

.. code-block:: python

   import os
   
   # All these values enable file logging
   os.environ["LOG_TO_FILE"] = "true"   # ✓
   os.environ["LOG_TO_FILE"] = "1"      # ✓
   os.environ["LOG_TO_FILE"] = "yes"    # ✓
   os.environ["LOG_TO_FILE"] = "on"     # ✓
   
   # All these values disable file logging
   os.environ["LOG_TO_FILE"] = "false"  # ✗
   os.environ["LOG_TO_FILE"] = "0"      # ✗
   os.environ["LOG_TO_FILE"] = "no"     # ✗
   os.environ["LOG_TO_FILE"] = "off"    # ✗

Configuration Features
----------------------

The configuration system provides:

* **Environment-driven setup** - No code changes needed between environments
* **Safe defaults** - Works out of the box with zero configuration
* **Validation** - Invalid values fall back to safe defaults
* **Error handling** - Configuration errors don't crash your application
* **Path resolution** - Automatic path validation and fallback to temp directories