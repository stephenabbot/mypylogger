# mypylogger v0.2.8

<!-- BADGES START -->
[![Quality Gate](https://img.shields.io/github/actions/workflow/status/stephenabbot/mypylogger/quality-gate.yml?style=flat&label=quality%20gate)](https://img.shields.io/github/actions/workflow/status/stephenabbot/mypylogger/quality-gate.yml?style=flat&label=quality%20gate) [![Security](https://img.shields.io/badge/security-verified-brightgreen?style=flat)](https://github.com/stephenabbot/mypylogger/security/code-scanning) [![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000?style=flat)](https://img.shields.io/badge/code%20style-ruff-000000?style=flat) [![Type Checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue?style=flat)](https://img.shields.io/badge/type%20checked-mypy-blue?style=flat) [![Test Coverage](https://img.shields.io/badge/coverage-96%25-brightgreen?style=flat)](https://img.shields.io/badge/coverage-96%25-brightgreen?style=flat) [![Python Versions](https://img.shields.io/pypi/pyversions/mypylogger?style=flat)](https://img.shields.io/pypi/pyversions/mypylogger?style=flat) [![PyPI Version](https://img.shields.io/pypi/v/mypylogger?style=flat)](https://img.shields.io/pypi/v/mypylogger?style=flat) [![Downloads: Development](https://img.shields.io/pypi/dm/mypylogger?style=flat)](https://img.shields.io/pypi/dm/mypylogger?style=flat) [![License: MIT](https://img.shields.io/github/license/stephenabbot/mypylogger?style=flat)](https://img.shields.io/github/license/stephenabbot/mypylogger?style=flat)
<!-- BADGES END -->

A Python logging library designed to provide enhanced logging capabilities with zero dependencies and sensible defaults.

## Vision

Create a **zero-dependency JSON logging library with sensible defaults** for Python applications. mypylogger v0.2.8 does ONE thing exceptionally well: structured JSON logs that work everywhere—from local development to AWS Lambda to Kubernetes.

## Installation

```bash
pip install mypylogger
```

## Quick Start

```python
from mypylogger import get_logger

logger = get_logger(__name__)
logger.info("Application started")
```

## Features

- **Zero Dependencies** (pure Python standard library)
- **Clean, Predictable JSON Output**
- **Developer-Friendly Defaults**
- **Standard Python Patterns**

## Documentation

📚 **Complete documentation available in [docs/](https://github.com/stabbotco1/mypylogger/tree/main/docs)**

- **[Features](https://github.com/stabbotco1/mypylogger/blob/main/docs/FEATURES.md)** - Complete feature reference with code examples
- **[Security](https://github.com/stabbotco1/mypylogger/blob/main/docs/SECURITY.md)** - Security posture and vulnerability management
- **[Performance](https://github.com/stabbotco1/mypylogger/blob/main/docs/PERFORMANCE.md)** - Performance characteristics and best practices

For comprehensive API documentation, see the [Sphinx docs](https://github.com/stabbotco1/mypylogger/tree/main/docs/source).

## Development

This project uses UV for dependency management:

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Format code
uv run ruff format .

# Check linting
uv run ruff check .
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

© 2025 Stephen Abbot - MIT License
