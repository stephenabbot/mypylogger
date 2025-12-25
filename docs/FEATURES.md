# mypylogger Features

**Complete feature reference with code examples**

## Core Features

### 1. Zero-Dependency JSON Logging

Pure Python standard library only. No external dependencies.

```python
from mypylogger import get_logger

logger = get_logger(__name__)
logger.info("User logged in", extra={"user_id": "12345", "ip": "192.168.1.1"})
```

**Output:**
```json
{"timestamp":"2025-01-21T10:30:45.123456Z","level":"INFO","message":"User logged in","module":"myapp","filename":"app.py","function_name":"login","line":42,"user_id":"12345","ip":"192.168.1.1"}
```

### 2. Automatic Source Location Tracking

Every log includes `module`, `filename`, `function_name`, and `line` automatically.

```python
logger = get_logger(__name__)
logger.error("Database connection failed")
```

**Output:**
```json
{"timestamp":"2025-01-21T10:30:45.123456Z","level":"ERROR","message":"Database connection failed","module":"db_handler","filename":"database.py","function_name":"connect","line":78}
```

**How it works:**
- Stack frame inspection to find the actual calling code
- Skips logging internals automatically
- Graceful fallback if inspection fails
- Relative paths from current working directory

### 3. Environment-Driven Configuration

Zero-code configuration via environment variables.

**Environment Variables:**
- `APP_NAME` - Logger name (default: "mypylogger")
- `LOG_LEVEL` - Logging level (default: "INFO")
  - Valid values: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `LOG_TO_FILE` - Enable file logging (default: "false")
  - Valid values: true, false, 1, 0, yes, no
- `LOG_FILE_DIR` - Log file directory (default: system temp dir)

**Example:**
```python
import os
os.environ["APP_NAME"] = "my_service"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["LOG_TO_FILE"] = "true"
os.environ["LOG_FILE_DIR"] = "/var/log/myapp"

from mypylogger import get_logger
logger = get_logger()  # Uses APP_NAME from environment
logger.debug("This will be logged to file and console")
```

### 4. Intelligent Logger Name Resolution

Fallback chain for logger names:

1. Explicit name provided to `get_logger(name)`
2. `APP_NAME` environment variable
3. Calling module's `__name__`
4. Final fallback: "mypylogger"

```python
# Explicit name
logger = get_logger("payment_service")

# Uses APP_NAME env var
os.environ["APP_NAME"] = "order_system"
logger = get_logger()

# Uses module's __name__
logger = get_logger(__name__)
```

### 5. ISO 8601 Timestamps with Microsecond Precision

All timestamps in UTC with microsecond precision.

```python
logger.info("Event occurred")
```

**Output:**
```json
{"timestamp":"2025-01-21T10:30:45.123456Z","level":"INFO",...}
```

**Format:** `YYYY-MM-DDTHH:MM:SS.ffffffZ`

### 6. Structured Data via `extra` Parameter

Standard Python logging `extra` parameter fully supported.

```python
logger.info(
    "Order placed",
    extra={
        "order_id": "ORD-2025-001",
        "amount": 299.99,
        "currency": "USD",
        "customer_id": "CUST-789"
    }
)
```

**Output:**
```json
{"timestamp":"2025-01-21T10:30:45.123456Z","level":"INFO","message":"Order placed","module":"orders","filename":"order_handler.py","function_name":"place_order","line":156,"order_id":"ORD-2025-001","amount":299.99,"currency":"USD","customer_id":"CUST-789"}
```

### 7. Exception Logging

Standard Python exception logging works seamlessly.

```python
try:
    result = 10 / 0
except ZeroDivisionError:
    logger.exception("Math error occurred")
```

**Output:**
```json
{"timestamp":"2025-01-21T10:30:45.123456Z","level":"ERROR","message":"Math error occurred","module":"calculator","filename":"calc.py","function_name":"divide","line":23,"exc_info":"Traceback (most recent call last):\n  File \"calc.py\", line 21, in divide\n    result = 10 / 0\nZeroDivisionError: division by zero"}
```

### 8. All Standard Log Levels

Full Python logging level support:

```python
logger.debug("Detailed diagnostic info")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical system failure")
```

### 9. Console and File Logging

**Console (default):**
- Logs to stdout
- JSON formatted
- Immediate flush for real-time monitoring

**File (optional):**
```python
os.environ["LOG_TO_FILE"] = "true"
os.environ["LOG_FILE_DIR"] = "/var/log/myapp"

logger = get_logger(__name__)
logger.info("Logged to both console and file")
```

**File naming:** `{app_name}_{timestamp}.log`
**Example:** `my_service_20250121_103045.log`

### 10. Graceful Error Handling

mypylogger never crashes your application.

**If JSON serialization fails:**
- Falls back to plain text: `LEVEL: message`
- Logs error to stderr
- Continues operation

**If configuration fails:**
- Uses safe defaults
- Logs error to stderr
- Returns working logger

**If file handler creation fails:**
- Continues with console logging only
- Logs warning to stderr

```python
# Non-serializable data handled gracefully
class CustomObject:
    pass

logger.info("Event", extra={"obj": CustomObject()})
# Skips non-serializable field, logs everything else
```

### 11. Standard Python Logging Interface

Returns a standard Python `logging.Logger` instance.

```python
import logging

logger = get_logger(__name__)

# Standard logging methods
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical message")
logger.exception("Exception with traceback")

# Standard API compatibility
logger.setLevel(logging.DEBUG)
logger.log(logging.INFO, "Custom level message")
```

**Note**: Advanced features like custom handlers and filters are not tested with mypylogger's JSON formatter and source location tracking. Use at your own risk.

### 12. Single Function API

One function to remember: `get_logger()`

```python
from mypylogger import get_logger

logger = get_logger(__name__)
# That's it. Start logging.
```

## Advanced Features

### Custom Field Filtering

Only JSON-serializable fields are included. Non-serializable fields are skipped with warnings to stderr.

```python
# These work
logger.info("Event", extra={"count": 42, "name": "test", "valid": True})

# These are skipped gracefully
logger.info("Event", extra={"func": lambda x: x})  # Functions skipped
logger.info("Event", extra={"thread": threading.Lock()})  # Non-serializable skipped
```

### Relative Path Resolution

File paths are relative to current working directory when possible.

```bash
# Working directory: /home/user/project
# Log shows: "filename":"src/app.py" instead of "/home/user/project/src/app.py"
```

### Consistent Field Ordering

JSON output has predictable field order for readability:

1. `timestamp`
2. `level`
3. `message`
4. `module`
5. `filename`
6. `function_name`
7. `line`
8. Custom fields (alphabetically)

### Protected Standard Fields

Standard logging fields cannot be overridden via `extra`:

Protected fields: `timestamp`, `level`, `message`, `module`, `filename`, `function_name`, `line`, `name`, `msg`, `args`, `levelname`, `levelno`, `pathname`, `lineno`, `funcName`, `created`, `msecs`, `relativeCreated`, `thread`, `threadName`, `processName`, `process`, `stack_info`, `exc_info`, `exc_text`

```python
# This 'level' field is ignored, standard 'level' preserved
logger.info("Test", extra={"level": "CUSTOM"})
```

## Platform Support

### Environments

✅ **Tested and working:**
- Local development (all OS)
- AWS Lambda
- Docker containers
- Kubernetes pods
- Air-gapped systems
- CI/CD pipelines

### Operating Systems

- Linux (all distributions)
- macOS (all versions)
- Windows (all versions)

### Python Versions

- Python 3.8
- Python 3.9
- Python 3.10
- Python 3.11
- Python 3.12

## What's NOT Included

mypylogger intentionally does NOT include:

❌ Log aggregation or shipping
❌ Remote logging handlers
❌ Log rotation (use external tools)
❌ Multiple output formats (JSON only)
❌ Async logging
❌ Structured log parsing/querying
❌ Built-in log filtering rules
❌ Performance metrics collection
❌ Log compression

**Philosophy:** Do ONE thing well. Use other tools for these features.

## Configuration Reference

| Variable | Type | Default | Valid Values |
|----------|------|---------|--------------|
| `APP_NAME` | string | "mypylogger" | Any string |
| `LOG_LEVEL` | string | "INFO" | DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `LOG_TO_FILE` | boolean | false | true, false, 1, 0, yes, no |
| `LOG_FILE_DIR` | path | system temp | Any writable directory path |

## Size & Footprint

| Metric | Value |
|--------|-------|
| **Package size** | <100KB |
| **Memory footprint** | <1MB |
| **Source files** | 6 files |
| **Total lines of code** | ~759 lines |
| **Public API functions** | 1 (`get_logger`) |

## JSON Output Schema

```json
{
  "timestamp": "ISO 8601 UTC string with microseconds",
  "level": "DEBUG|INFO|WARNING|ERROR|CRITICAL",
  "message": "Log message string",
  "module": "Python module name",
  "filename": "Relative file path",
  "function_name": "Function name where log was called",
  "line": "Line number (integer)",
  "...": "Any additional fields from extra parameter"
}
```

**Field types:**
- `timestamp`: string (ISO 8601)
- `level`: string
- `message`: string
- `module`: string
- `filename`: string
- `function_name`: string
- `line`: integer
- Custom fields: any JSON-serializable type

---

**Next:** [SECURITY.md](SECURITY.md) | [PERFORMANCE.md](PERFORMANCE.md) | [Back to docs](README.md)
