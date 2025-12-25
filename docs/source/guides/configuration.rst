Configuration Guide
===================

Complete guide to configuring mypylogger using environment variables and file logging.

Environment Variables Reference
-------------------------------

mypylogger uses environment variables for all configuration, making it perfect for 12-factor applications. All configuration is resolved at logger creation time with automatic fallbacks to safe defaults.

APP_NAME
~~~~~~~~

**Purpose**: Application name used in log entries and file names

**Type**: String
**Default**: Automatic fallback chain (see below)
**Required**: No
**Example**: ``export APP_NAME="myapp"``

**Fallback Chain**:
1. Explicit ``APP_NAME`` environment variable
2. Calling module's ``__name__`` (if not ``__main__``)
3. ``"mypylogger"`` (final fallback)

**Usage**:
- Logger names: ``get_logger()`` uses APP_NAME if no name provided
- Log file names: ``{APP_NAME}_{date}_{hour}.log``
- JSON log entries: Included in structured output

**Validation Rules**:
- Any string value is accepted
- Empty strings fall back to next option in chain
- Special characters are preserved in log files (sanitized by OS)

**Examples**:

.. code-block:: bash

   # Simple application name
   export APP_NAME="user-service"
   
   # Environment-specific naming
   export APP_NAME="user-service-prod"
   
   # Microservice naming
   export APP_NAME="payment-api-v2"

**Security Considerations**:
- Avoid sensitive information in application names
- Use consistent naming for log aggregation
- Consider including environment in name for multi-environment deployments

LOG_LEVEL
~~~~~~~~~

**Purpose**: Minimum log level to output (filters messages below this level)

**Type**: String (case-insensitive)
**Default**: ``INFO``
**Required**: No
**Valid Values**: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``

**Validation Rules**:
- Case-insensitive: ``debug``, ``Debug``, ``DEBUG`` all work
- Invalid values automatically fall back to ``INFO``
- No error is raised for invalid values (graceful degradation)

**Level Hierarchy** (from most to least verbose):
1. ``DEBUG`` - Detailed diagnostic information
2. ``INFO`` - General application flow information  
3. ``WARNING`` - Potentially harmful situations
4. ``ERROR`` - Error events that don't stop execution
5. ``CRITICAL`` - Serious errors that may cause termination

**Examples**:

.. code-block:: bash

   # Development: See all messages
   export LOG_LEVEL="DEBUG"
   
   # Production: Only important messages
   export LOG_LEVEL="WARNING"
   
   # Case insensitive
   export LOG_LEVEL="info"     # Same as INFO
   export LOG_LEVEL="Error"    # Same as ERROR

**Performance Impact**:
- Lower levels (DEBUG) have higher performance cost
- Higher levels (ERROR) filter more messages, improving performance
- Filtering happens at logger level (efficient)

**Security Considerations**:
- ``DEBUG`` may expose sensitive information in logs
- Use ``WARNING`` or higher in production environments
- Avoid ``DEBUG`` in security-sensitive applications

LOG_TO_FILE
~~~~~~~~~~~

**Purpose**: Enable file logging in addition to console output

**Type**: Boolean (parsed from string)
**Default**: ``false``
**Required**: No
**Valid Values**: ``true``, ``false``, ``1``, ``0``, ``yes``, ``no``, ``on``, ``off``

**Validation Rules**:
- Case-insensitive boolean parsing
- Truthy values: ``true``, ``1``, ``yes``, ``on`` (case-insensitive)
- Falsy values: ``false``, ``0``, ``no``, ``off`` (case-insensitive)
- Invalid values default to ``false``
- Empty string defaults to ``false``

**Behavior**:
- ``true``: Logs to both console (stdout) and file
- ``false``: Logs only to console (stdout)
- File logging requires valid ``LOG_FILE_DIR``
- Graceful fallback to console-only if file logging fails

**Examples**:

.. code-block:: bash

   # Enable file logging
   export LOG_TO_FILE="true"
   export LOG_TO_FILE="1"
   export LOG_TO_FILE="yes"
   export LOG_TO_FILE="ON"      # Case insensitive
   
   # Disable file logging (default)
   export LOG_TO_FILE="false"
   export LOG_TO_FILE="0"
   export LOG_TO_FILE="no"

**Performance Considerations**:
- File I/O adds latency to log operations
- Immediate flush ensures reliability but reduces throughput
- Consider disk space and I/O capacity in high-volume scenarios

**Security Considerations**:
- File logs persist on disk (consider log rotation)
- Ensure proper file permissions on log directories
- Monitor disk usage to prevent DoS via log flooding

LOG_FILE_DIR
~~~~~~~~~~~~

**Purpose**: Directory path for log files (when ``LOG_TO_FILE=true``)

**Type**: String (file system path)
**Default**: System temporary directory (``tempfile.gettempdir()``)
**Required**: No (when ``LOG_TO_FILE=false``)
**Example**: ``export LOG_FILE_DIR="/var/log/myapp"``

**Validation Rules**:
- Path is resolved to absolute path using ``Path.resolve()``
- Invalid paths fall back to system temporary directory
- Directory is created automatically if it doesn't exist
- Parent directories are created recursively (``mkdir -p`` behavior)

**Fallback Behavior**:
1. Use provided ``LOG_FILE_DIR`` if valid and writable
2. Try to create directory if it doesn't exist
3. Fall back to ``/tmp/mypylogger`` if creation fails
4. Fall back to system temp directory if all else fails
5. Disable file logging if no writable directory found

**File Naming Convention**:
Log files are automatically named: ``{APP_NAME}_{YYYYMMDD}_{HH}.log``

- ``APP_NAME``: From APP_NAME environment variable
- ``YYYYMMDD``: Current date (e.g., ``20250121``)
- ``HH``: Current hour (00-23, enables hourly rotation)

**Examples**:

.. code-block:: bash

   # Absolute paths (recommended)
   export LOG_FILE_DIR="/var/log/myapp"
   export LOG_FILE_DIR="/home/user/logs"
   
   # Relative paths (resolved to absolute)
   export LOG_FILE_DIR="./logs"           # Becomes /current/dir/logs
   export LOG_FILE_DIR="../shared/logs"   # Becomes /parent/dir/shared/logs
   
   # Windows paths
   export LOG_FILE_DIR="C:\logs\myapp"
   export LOG_FILE_DIR="\\server\share\logs"

**Directory Creation Examples**:

.. code-block:: python

   import os
   from pathlib import Path
   
   # This directory structure will be created automatically
   log_dir = "/var/log/myapp/production/2025/01"
   os.environ["LOG_FILE_DIR"] = log_dir
   os.environ["LOG_TO_FILE"] = "true"
   
   # mypylogger creates: /var/log/myapp/production/2025/01/
   # Log file: myapp_20250121_14.log

**Security Considerations**:
- Use absolute paths to avoid directory traversal issues
- Set appropriate directory permissions (750 recommended)
- Avoid world-writable directories
- Consider disk quotas and monitoring
- Implement log rotation to prevent disk exhaustion

**Production Best Practices**:
- Use dedicated log directories: ``/var/log/{app_name}``
- Set proper ownership: ``chown app_user:app_group /var/log/myapp``
- Configure log rotation: Use ``logrotate`` or similar tools
- Monitor disk usage: Implement alerting for disk space
- Backup strategy: Include log files in backup procedures

Configuration Validation and Error Handling
-------------------------------------------

**Automatic Validation**

mypylogger validates all configuration at logger creation time:

.. code-block:: python

   import os
   from mypylogger import get_logger
   
   # Invalid configuration - automatic fallbacks applied
   os.environ["LOG_LEVEL"] = "INVALID"        # Falls back to INFO
   os.environ["LOG_FILE_DIR"] = "/invalid"    # Falls back to temp dir
   os.environ["LOG_TO_FILE"] = "maybe"        # Falls back to false
   
   # Logger still works with safe defaults
   logger = get_logger()
   logger.info("Logger created successfully with fallback configuration")

**Configuration Errors**

mypylogger handles configuration errors gracefully:

.. code-block:: python

   # These scenarios are handled automatically:
   
   # 1. Permission denied on log directory
   os.environ["LOG_FILE_DIR"] = "/root/logs"  # May not be writable
   os.environ["LOG_TO_FILE"] = "true"
   
   # 2. Invalid log level
   os.environ["LOG_LEVEL"] = "TRACE"  # Not a valid Python log level
   
   # 3. Non-existent directory
   os.environ["LOG_FILE_DIR"] = "/nonexistent/path/logs"
   
   # Logger creation succeeds with fallbacks
   logger = get_logger()  # No exception raised

**Error Reporting**

Configuration issues are reported to stderr without affecting application:

.. code-block:: python

   # Example stderr output for configuration issues:
   # mypylogger: Failed to create log directory /invalid/path: Permission denied
   # mypylogger: Using temporary directory: /tmp/mypylogger
   # mypylogger: Invalid log level 'TRACE', using INFO

**Validation Utilities**

Check configuration before application startup:

.. code-block:: python

   import os
   import sys
   from pathlib import Path
   
   def validate_mypylogger_config():
       """Validate mypylogger configuration and report issues."""
       
       issues = []
       
       # Validate log level
       log_level = os.getenv("LOG_LEVEL", "INFO").upper()
       valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
       if log_level not in valid_levels:
           issues.append(f"Invalid LOG_LEVEL '{log_level}', will use INFO")
       
       # Validate file logging configuration
       if os.getenv("LOG_TO_FILE", "false").lower() in ("true", "1", "yes", "on"):
           log_dir = Path(os.getenv("LOG_FILE_DIR", "/tmp"))
           
           try:
               log_dir.mkdir(parents=True, exist_ok=True)
               # Test write permissions
               test_file = log_dir / ".mypylogger_test"
               test_file.write_text("test")
               test_file.unlink()
           except (OSError, PermissionError) as e:
               issues.append(f"Log directory not writable: {log_dir} - {e}")
       
       # Report issues
       if issues:
           print("mypylogger configuration issues:")
           for issue in issues:
               print(f"  ⚠️  {issue}")
           return False
       else:
           print("✅ mypylogger configuration validated successfully")
           return True
   
   if __name__ == "__main__":
       if not validate_mypylogger_config():
           sys.exit(1)

File Logging Configuration
--------------------------

**Basic File Logging Setup**

Enable file logging with minimal configuration:

.. code-block:: bash

   export LOG_TO_FILE="true"
   export LOG_FILE_DIR="/var/log/myapp"

.. code-block:: python

   from mypylogger import get_logger
   
   logger = get_logger("myapp")
   logger.info("This will appear in console AND file")

**File Naming Convention**

Log files are automatically named using the pattern: ``{app_name}.log``

* APP_NAME="myapp" → ``myapp.log``
* APP_NAME="user-service" → ``user-service.log``
* No APP_NAME set → ``mypylogger.log``

**Directory Management**

mypylogger handles directory creation and permissions automatically:

.. code-block:: python

   import os
   
   # This directory will be created if it doesn't exist
   os.environ["LOG_FILE_DIR"] = "/var/log/myapp/production"
   os.environ["LOG_TO_FILE"] = "true"
   
   logger = get_logger("myapp")
   logger.info("Directory created automatically")

**File Logging Best Practices**:

* **Use absolute paths**: ``/var/log/myapp`` instead of ``./logs``
* **Set proper permissions**: Ensure the application can write to the directory
* **Consider log rotation**: Use logrotate or similar tools for production
* **Monitor disk space**: File logging can consume significant disk space
* **Backup strategy**: Include log files in your backup procedures

Environment-Based Configuration Patterns
----------------------------------------

**Development Environment**

Verbose logging to console only:

.. code-block:: bash

   export APP_NAME="myapp-dev"
   export LOG_LEVEL="DEBUG"
   export LOG_TO_FILE="false"

.. code-block:: python

   # All debug information visible in console
   logger.debug("Database query", extra={"sql": "SELECT * FROM users", "duration_ms": 15})

**Staging Environment**

Moderate logging with file backup:

.. code-block:: bash

   export APP_NAME="myapp-staging"
   export LOG_LEVEL="INFO"
   export LOG_TO_FILE="true"
   export LOG_FILE_DIR="/var/log/myapp/staging"

**Production Environment**

Optimized for performance and storage:

.. code-block:: bash

   export APP_NAME="myapp"
   export LOG_LEVEL="WARNING"  # Only warnings and errors
   export LOG_TO_FILE="true"
   export LOG_FILE_DIR="/var/log/myapp/production"

**Container Environment (Docker/Kubernetes)**

Let container runtime handle log collection:

.. code-block:: dockerfile

   # Dockerfile
   ENV APP_NAME="myapp"
   ENV LOG_LEVEL="INFO"
   ENV LOG_TO_FILE="false"  # Use container log drivers

.. code-block:: yaml

   # docker-compose.yml
   services:
     myapp:
       environment:
         - APP_NAME=myapp
         - LOG_LEVEL=INFO
         - LOG_TO_FILE=false

**Serverless Environment (AWS Lambda)**

Optimized for serverless constraints:

.. code-block:: python

   # Lambda function
   import os
   
   # Configure before importing logger
   os.environ["APP_NAME"] = "lambda-function"
   os.environ["LOG_LEVEL"] = "INFO"
   os.environ["LOG_TO_FILE"] = "false"  # CloudWatch handles collection
   
   from mypylogger import get_logger
   
   logger = get_logger()
   
   def lambda_handler(event, context):
       logger.info("Lambda invocation", extra={
           "request_id": context.aws_request_id,
           "function_name": context.function_name,
           "remaining_time_ms": context.get_remaining_time_in_millis()
       })

**Multi-Environment Configuration**

Use environment-specific configuration files:

.. code-block:: bash

   # config/development.env
   APP_NAME="myapp-dev"
   LOG_LEVEL="DEBUG"
   LOG_TO_FILE="false"
   
   # config/production.env  
   APP_NAME="myapp"
   LOG_LEVEL="INFO"
   LOG_TO_FILE="true"
   LOG_FILE_DIR="/var/log/myapp"

.. code-block:: python

   # Load environment-specific config
   import os
   from pathlib import Path
   
   def load_env_config(environment="development"):
       env_file = Path(f"config/{environment}.env")
       if env_file.exists():
           with open(env_file) as f:
               for line in f:
                   if line.strip() and not line.startswith('#'):
                       key, value = line.strip().split('=', 1)
                       os.environ[key] = value
   
   # Load config before creating logger
   load_env_config(os.getenv("ENVIRONMENT", "development"))
   
   from mypylogger import get_logger
   logger = get_logger()

Advanced File Logging Patterns
-------------------------------

**Programmatic Configuration**

Set configuration in Python code before creating loggers:

.. code-block:: python

   import os
   from pathlib import Path
   from mypylogger import get_logger
   
   # Configure before creating any loggers
   os.environ["APP_NAME"] = "myapp"
   os.environ["LOG_LEVEL"] = "INFO"
   os.environ["LOG_TO_FILE"] = "true"
   os.environ["LOG_FILE_DIR"] = str(Path.home() / "logs" / "myapp")
   
   logger = get_logger()
   logger.info("Configuration set programmatically")

**Dynamic Directory Management**

Create environment-specific log directories:

.. code-block:: python

   import os
   from datetime import datetime
   from pathlib import Path
   
   # Create date-based log directories
   log_date = datetime.now().strftime("%Y-%m-%d")
   log_dir = Path("/var/log/myapp") / log_date
   
   os.environ["LOG_FILE_DIR"] = str(log_dir)
   os.environ["LOG_TO_FILE"] = "true"
   
   from mypylogger import get_logger
   logger = get_logger()
   
   # Logs will be written to /var/log/myapp/2025-01-21/myapp.log

**Multiple Log Files by Component**

Use different loggers for different application components:

.. code-block:: python

   import os
   
   # Configure base settings
   os.environ["LOG_TO_FILE"] = "true"
   os.environ["LOG_FILE_DIR"] = "/var/log/myapp"
   
   from mypylogger import get_logger
   
   # Each logger creates its own file
   db_logger = get_logger("database")      # → database.log
   api_logger = get_logger("api")          # → api.log
   auth_logger = get_logger("auth")        # → auth.log
   
   db_logger.info("Database connection established")
   api_logger.info("API server started on port 8000")
   auth_logger.info("Authentication service initialized")

**Conditional File Logging**

Enable file logging based on runtime conditions:

.. code-block:: python

   import os
   import sys
   from mypylogger import get_logger
   
   # Enable file logging only in production
   is_production = os.getenv("ENVIRONMENT") == "production"
   
   if is_production:
       os.environ["LOG_TO_FILE"] = "true"
       os.environ["LOG_FILE_DIR"] = "/var/log/myapp"
       os.environ["LOG_LEVEL"] = "WARNING"
   else:
       os.environ["LOG_TO_FILE"] = "false"
       os.environ["LOG_LEVEL"] = "DEBUG"
   
   logger = get_logger()
   logger.info("Application started", extra={
       "environment": os.getenv("ENVIRONMENT", "development"),
       "file_logging": is_production
   })

Configuration Validation and Error Handling
-------------------------------------------

**Automatic Fallbacks**

mypylogger provides safe fallbacks for invalid configuration:

.. code-block:: python

   import os
   from mypylogger import get_logger
   
   # Invalid log level - falls back to INFO
   os.environ["LOG_LEVEL"] = "INVALID_LEVEL"
   
   # Invalid directory - falls back to temp directory
   os.environ["LOG_FILE_DIR"] = "/invalid/path/that/does/not/exist"
   os.environ["LOG_TO_FILE"] = "true"
   
   logger = get_logger()
   # Logger still works with safe defaults
   logger.info("Logger created with fallback configuration")

**Configuration Validation**

Check configuration before application startup:

.. code-block:: python

   import os
   import sys
   from pathlib import Path
   from mypylogger import get_logger
   
   def validate_log_config():
       """Validate logging configuration before starting application."""
       
       # Check log directory is writable
       if os.getenv("LOG_TO_FILE", "false").lower() == "true":
           log_dir = Path(os.getenv("LOG_FILE_DIR", "/tmp"))
           
           try:
               log_dir.mkdir(parents=True, exist_ok=True)
               test_file = log_dir / "test_write.tmp"
               test_file.write_text("test")
               test_file.unlink()
               print(f"✓ Log directory writable: {log_dir}")
           except (OSError, PermissionError) as e:
               print(f"✗ Log directory not writable: {log_dir} - {e}")
               sys.exit(1)
       
       # Validate log level
       log_level = os.getenv("LOG_LEVEL", "INFO").upper()
       valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
       if log_level not in valid_levels:
           print(f"✗ Invalid log level: {log_level}")
           print(f"Valid levels: {', '.join(valid_levels)}")
           sys.exit(1)
       
       print("✓ Logging configuration validated")
   
   if __name__ == "__main__":
       validate_log_config()
       logger = get_logger()
       logger.info("Application started with validated configuration")

Production-Ready Configuration Examples
----------------------------------------

**Development Environment**

Optimized for debugging and rapid development:

.. code-block:: bash

   # .env.development
   APP_NAME="myapp-dev"
   LOG_LEVEL="DEBUG"
   LOG_TO_FILE="false"  # Console only for immediate feedback

.. code-block:: python

   # Load development configuration
   import os
   from mypylogger import get_logger
   
   # Development-specific settings
   os.environ.update({
       "APP_NAME": "myapp-dev",
       "LOG_LEVEL": "DEBUG",
       "LOG_TO_FILE": "false"
   })
   
   logger = get_logger()
   logger.debug("Development mode active", extra={
       "environment": "development",
       "debug_mode": True,
       "file_logging": False
   })

**Staging Environment**

Balanced configuration for testing production-like scenarios:

.. code-block:: bash

   # .env.staging
   APP_NAME="myapp-staging"
   LOG_LEVEL="INFO"
   LOG_TO_FILE="true"
   LOG_FILE_DIR="/var/log/myapp/staging"

.. code-block:: python

   # Staging configuration with validation
   import os
   from pathlib import Path
   from mypylogger import get_logger
   
   # Staging-specific settings
   staging_config = {
       "APP_NAME": "myapp-staging",
       "LOG_LEVEL": "INFO",
       "LOG_TO_FILE": "true",
       "LOG_FILE_DIR": "/var/log/myapp/staging"
   }
   
   # Ensure log directory exists with proper permissions
   log_dir = Path(staging_config["LOG_FILE_DIR"])
   log_dir.mkdir(parents=True, exist_ok=True, mode=0o750)
   
   os.environ.update(staging_config)
   logger = get_logger()
   
   logger.info("Staging environment initialized", extra={
       "environment": "staging",
       "log_directory": str(log_dir),
       "file_logging": True
   })

**Production Environment**

Optimized for performance, security, and reliability:

.. code-block:: bash

   # .env.production
   APP_NAME="myapp"
   LOG_LEVEL="WARNING"  # Only warnings, errors, and critical
   LOG_TO_FILE="true"
   LOG_FILE_DIR="/var/log/myapp/production"

.. code-block:: python

   # Production configuration with security considerations
   import os
   import stat
   from pathlib import Path
   from mypylogger import get_logger
   
   def setup_production_logging():
       """Configure production logging with security best practices."""
       
       # Production settings
       config = {
           "APP_NAME": "myapp",
           "LOG_LEVEL": "WARNING",  # Minimal logging for performance
           "LOG_TO_FILE": "true",
           "LOG_FILE_DIR": "/var/log/myapp/production"
       }
       
       # Create secure log directory
       log_dir = Path(config["LOG_FILE_DIR"])
       log_dir.mkdir(parents=True, exist_ok=True)
       
       # Set secure permissions (owner: read/write/execute, group: read/execute)
       log_dir.chmod(stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)
       
       os.environ.update(config)
       return get_logger()
   
   logger = setup_production_logging()
   logger.warning("Production logging initialized", extra={
       "environment": "production",
       "security_level": "high",
       "log_level": "WARNING"
   })

**Container Environment (Docker/Kubernetes)**

Optimized for containerized deployments:

.. code-block:: dockerfile

   # Dockerfile
   FROM python:3.11-slim
   
   # Set logging configuration for containers
   ENV APP_NAME="myapp"
   ENV LOG_LEVEL="INFO"
   ENV LOG_TO_FILE="false"  # Let container runtime handle log collection
   
   # Install application
   COPY . /app
   WORKDIR /app
   RUN pip install -e .
   
   CMD ["python", "main.py"]

.. code-block:: yaml

   # docker-compose.yml
   version: '3.8'
   services:
     myapp:
       build: .
       environment:
         - APP_NAME=myapp
         - LOG_LEVEL=INFO
         - LOG_TO_FILE=false
       logging:
         driver: "json-file"
         options:
           max-size: "10m"
           max-file: "3"

.. code-block:: yaml

   # kubernetes-deployment.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: myapp
   spec:
     template:
       spec:
         containers:
         - name: myapp
           image: myapp:latest
           env:
           - name: APP_NAME
             value: "myapp"
           - name: LOG_LEVEL
             value: "INFO"
           - name: LOG_TO_FILE
             value: "false"  # Use Kubernetes log collection

**Serverless Environment (AWS Lambda)**

Optimized for serverless constraints and CloudWatch integration:

.. code-block:: python

   # lambda_function.py
   import os
   import json
   from mypylogger import get_logger
   
   # Configure for Lambda environment
   os.environ.update({
       "APP_NAME": "lambda-processor",
       "LOG_LEVEL": "INFO",
       "LOG_TO_FILE": "false"  # CloudWatch handles log collection
   })
   
   logger = get_logger()
   
   def lambda_handler(event, context):
       """AWS Lambda handler with structured logging."""
       
       # Log invocation details
       logger.info("Lambda invocation started", extra={
           "request_id": context.aws_request_id,
           "function_name": context.function_name,
           "function_version": context.function_version,
           "remaining_time_ms": context.get_remaining_time_in_millis(),
           "memory_limit_mb": context.memory_limit_in_mb
       })
       
       try:
           # Process event
           result = process_event(event)
           
           logger.info("Lambda invocation completed", extra={
               "request_id": context.aws_request_id,
               "result_size": len(json.dumps(result)),
               "status": "success"
           })
           
           return result
           
       except Exception as e:
           logger.error("Lambda invocation failed", extra={
               "request_id": context.aws_request_id,
               "error_type": type(e).__name__,
               "error_message": str(e),
               "status": "error"
           })
           raise

**Multi-Environment Configuration Management**

Centralized configuration management for multiple environments:

.. code-block:: python

   # config/environments.py
   import os
   from pathlib import Path
   from typing import Dict, Any
   
   class EnvironmentConfig:
       """Centralized environment configuration for mypylogger."""
       
       ENVIRONMENTS = {
           "development": {
               "APP_NAME": "myapp-dev",
               "LOG_LEVEL": "DEBUG",
               "LOG_TO_FILE": "false"
           },
           "testing": {
               "APP_NAME": "myapp-test",
               "LOG_LEVEL": "INFO",
               "LOG_TO_FILE": "true",
               "LOG_FILE_DIR": "/tmp/myapp-test-logs"
           },
           "staging": {
               "APP_NAME": "myapp-staging",
               "LOG_LEVEL": "INFO",
               "LOG_TO_FILE": "true",
               "LOG_FILE_DIR": "/var/log/myapp/staging"
           },
           "production": {
               "APP_NAME": "myapp",
               "LOG_LEVEL": "WARNING",
               "LOG_TO_FILE": "true",
               "LOG_FILE_DIR": "/var/log/myapp/production"
           }
       }
       
       @classmethod
       def load_environment(cls, env_name: str) -> None:
           """Load configuration for specified environment."""
           
           if env_name not in cls.ENVIRONMENTS:
               raise ValueError(f"Unknown environment: {env_name}")
           
           config = cls.ENVIRONMENTS[env_name]
           
           # Create log directory if file logging is enabled
           if config.get("LOG_TO_FILE") == "true":
               log_dir = Path(config["LOG_FILE_DIR"])
               log_dir.mkdir(parents=True, exist_ok=True)
           
           # Set environment variables
           os.environ.update(config)
       
       @classmethod
       def get_current_environment(cls) -> str:
           """Detect current environment from ENV variable."""
           return os.getenv("ENVIRONMENT", "development")
   
   # Usage in application startup
   from config.environments import EnvironmentConfig
   from mypylogger import get_logger
   
   # Load environment-specific configuration
   current_env = EnvironmentConfig.get_current_environment()
   EnvironmentConfig.load_environment(current_env)
   
   logger = get_logger()
   logger.info("Application started", extra={
       "environment": current_env,
       "configuration_loaded": True
   })

**Configuration File Integration**

Loading configuration from external files:

.. code-block:: python

   # config_loader.py
   import os
   import json
   import yaml
   from pathlib import Path
   from typing import Dict, Any
   
   def load_config_from_file(config_path: str) -> Dict[str, Any]:
       """Load mypylogger configuration from JSON or YAML file."""
       
       config_file = Path(config_path)
       
       if not config_file.exists():
           raise FileNotFoundError(f"Configuration file not found: {config_path}")
       
       # Load based on file extension
       if config_file.suffix.lower() == '.json':
           with open(config_file) as f:
               config = json.load(f)
       elif config_file.suffix.lower() in ('.yml', '.yaml'):
           with open(config_file) as f:
               config = yaml.safe_load(f)
       else:
           raise ValueError(f"Unsupported config file format: {config_file.suffix}")
       
       # Extract mypylogger configuration
       logging_config = config.get('logging', {})
       
       # Map to environment variables
       env_mapping = {
           'app_name': 'APP_NAME',
           'log_level': 'LOG_LEVEL',
           'log_to_file': 'LOG_TO_FILE',
           'log_file_dir': 'LOG_FILE_DIR'
       }
       
       for config_key, env_var in env_mapping.items():
           if config_key in logging_config:
               os.environ[env_var] = str(logging_config[config_key])
       
       return logging_config

.. code-block:: yaml

   # config/production.yml
   logging:
     app_name: "myapp"
     log_level: "WARNING"
     log_to_file: true
     log_file_dir: "/var/log/myapp/production"
   
   database:
     host: "prod-db.example.com"
     port: 5432
   
   api:
     base_url: "https://api.example.com"

.. code-block:: python

   # Usage with configuration file
   from config_loader import load_config_from_file
   from mypylogger import get_logger
   
   # Load configuration from file
   config = load_config_from_file("config/production.yml")
   
   # Logger is automatically configured from environment variables
   logger = get_logger()
   logger.info("Configuration loaded from file", extra={
       "config_file": "config/production.yml",
       "logging_config": config
   })

Security and Production Considerations
--------------------------------------

**File Permissions and Security**

.. code-block:: bash

   # Set secure permissions for log directory
   sudo mkdir -p /var/log/myapp
   sudo chown myapp:myapp /var/log/myapp
   sudo chmod 750 /var/log/myapp  # Owner: rwx, Group: rx, Other: none
   
   # Set secure permissions for log files
   sudo find /var/log/myapp -type f -exec chmod 640 {} \;  # Owner: rw, Group: r, Other: none

**Log Rotation Setup**

.. code-block:: bash

   # /etc/logrotate.d/myapp
   /var/log/myapp/*.log {
       daily
       rotate 30
       compress
       delaycompress
       missingok
       notifempty
       create 640 myapp myapp
       postrotate
           # Send HUP signal to application if needed
           /bin/kill -HUP $(cat /var/run/myapp.pid) 2>/dev/null || true
       endscript
   }

**Security Best Practices**:

* **Never log sensitive data**: Passwords, API keys, personal information, tokens
* **Use appropriate log levels**: Avoid DEBUG in production to prevent information leakage
* **Secure log directories**: Set proper file permissions (640 for files, 750 for directories)
* **Monitor disk usage**: Implement log rotation and cleanup policies
* **Audit log access**: Track who accesses log files in production environments
* **Encrypt logs at rest**: Use encrypted file systems for sensitive applications
* **Secure log transmission**: Use TLS when shipping logs to external systems
* **Implement log retention policies**: Define how long logs are kept and when they're deleted
* **Regular security audits**: Review log configurations and access patterns
* **Compliance considerations**: Ensure logging meets regulatory requirements (GDPR, HIPAA, etc.)