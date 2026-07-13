# mypylogger

[![PyPI Version](https://img.shields.io/pypi/v/mypylogger)](https://pypi.org/project/mypylogger/)
[![Python Versions](https://img.shields.io/pypi/pyversions/mypylogger)](https://pypi.org/project/mypylogger/)
[![License](https://img.shields.io/github/license/stephenabbot/mypylogger)](https://github.com/stephenabbot/mypylogger/blob/main/LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/stephenabbot/mypylogger/ci.yml?branch=main)](https://github.com/stephenabbot/mypylogger/actions/workflows/ci.yml)

Zero-dependency structured JSON logging for Python, with sensible defaults. One
JSON event per line, standard-library only, ready for local development, AWS
Lambda, and Linux containers.

## Installation

```bash
pip install mypylogger
```

## Quick start

```python
from mypylogger import get_logger, bind, clear_bindings

logger = get_logger(__name__)
logger.info("service started")

# Attach context to every subsequent event in this task/thread.
bind(request_id="abc123", user="stephen")
logger.info("handling request")        # includes request_id and user
clear_bindings()

# Per-call extra fields.
logger.info("processed", extra={"items": 42})

# Exceptions render as a structured ECS-style error object.
try:
    1 / 0
except ZeroDivisionError:
    logger.exception("computation failed")
```

Each event is a single JSON line with a stable field order, `timestamp` always
first (ISO 8601, microsecond precision, `Z` suffix):

```json
{"timestamp": "2026-07-12T18:30:00.123456Z", "level": "INFO", "message": "service started", "module": "app", "filename": "app.py", "function_name": "main", "line": 10, "hostname": "host", "pid": 4123, "service": "mypylogger", "environment": "unknown", "version": "unknown"}
```

DEBUG/INFO route to stdout; WARNING/ERROR/CRITICAL route to stderr.

## Configuration

All configuration is via environment variables, read once at import time. No
config file.

| Variable | Default | Effect |
|---|---|---|
| `APP_NAME` | `mypylogger` | Logger name and log-file prefix; also the `service` field |
| `LOG_LEVEL` | `INFO` | Effective log level (case-insensitive) |
| `LOG_TO_FILE` | `false` | Enable file logging when `true` |
| `LOG_FILE_DIR` | current working dir | Directory for log files |
| `LOG_MULTIPROCESS` | `false` | Route file writes through a library-owned listener process for safe multi-process shared-file logging |
| `LOG_SOCKET_PORT` | `9020` | TCP port on `127.0.0.1` for the multi-process listener |
| `HOSTNAME` | `socket.gethostname()` | `hostname` static field |
| `APP_ENV` | `unknown` | `environment` static field |
| `APP_VERSION` | `unknown` | `version` static field |

Setting `HOSTNAME`, `APP_ENV`, or `APP_VERSION` to an empty string omits that
field entirely.

## API

- `get_logger(name=None, static_fields=None) -> logging.Logger`
- `bind(**fields) -> None`
- `clear_bindings() -> None`

## Specifications

Authoritative behavior and packaging are documented in
[`01_rewrite_specification.md`](https://github.com/stephenabbot/mypylogger/blob/main/01_rewrite_specification.md)
and
[`02_packaging_specification.md`](https://github.com/stephenabbot/mypylogger/blob/main/02_packaging_specification.md).

## License

MIT — see [LICENSE](https://github.com/stephenabbot/mypylogger/blob/main/LICENSE).
