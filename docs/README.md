# mypylogger Documentation

**Version 0.2.0** | **Python 3.8+** | **Zero Dependencies**

## Quick Overview

mypylogger is a zero-dependency JSON logging library for Python. It provides structured logging with sensible defaults that work everywhere—from local development to AWS Lambda to Kubernetes.

```python
from mypylogger import get_logger

logger = get_logger(__name__)
logger.info("Application started", extra={"version": "1.0.0"})
```

**Output:**
```json
{"time":"2025-01-21T10:30:45.123456Z","levelname":"INFO","name":"myapp","message":"Application started","version":"1.0.0"}
```

## Core Value

- **Zero Dependencies**: Pure Python standard library only
- **One Thing Well**: Structured JSON logs
- **Works Everywhere**: Lambda, containers, air-gapped systems, local dev
- **Sensible Defaults**: No configuration required

## Documentation

### Essential Reading

- **[FEATURES.md](FEATURES.md)** - Complete feature list with code examples
- **[SECURITY.md](SECURITY.md)** - Security posture and current findings
- **[PERFORMANCE.md](PERFORMANCE.md)** - Performance characteristics and benchmarks

### Additional Resources

- **[Sphinx Documentation](source/index.rst)** - Comprehensive API reference and guides
  - [Installation Guide](source/installation.rst)
  - [Quick Start](source/quickstart.rst)
  - [API Reference](source/api/index.rst)
  - [Usage Guides](source/guides/index.rst)
  - [Examples](source/examples/index.rst)

## Quick Install

```bash
pip install mypylogger
```

## At a Glance

| **Aspect** | **Details** |
|------------|-------------|
| **Size** | <100KB installed |
| **Memory** | <1MB runtime footprint |
| **Dependencies** | Zero runtime dependencies |
| **Python Versions** | 3.8, 3.9, 3.10, 3.11, 3.12 |
| **License** | MIT |
| **API Surface** | 1 function: `get_logger()` |

## When to Use mypylogger

✅ **Use when you need:**
- Structured JSON logs with zero setup
- Platform-independent logging
- Minimal dependencies
- Predictable, consistent output
- Drop-in enhancement for Python's logging

❌ **Don't use when you need:**
- Complex log routing/filtering
- Built-in log aggregation
- Custom formatters beyond JSON
- Performance-critical applications (benchmarks pending)

## Project Philosophy

mypylogger does **ONE thing exceptionally well**: structured JSON logging.

It's designed for developers who want:
- Safe, predictable logging
- No dependency bloat
- Standard Python patterns
- Same logger across Python projects (myjavalogger, mynodelogger planned)

---

**Repository**: https://github.com/stabbotco1/mypylogger
**Issues**: https://github.com/stabbotco1/mypylogger/issues
**PyPI**: https://pypi.org/project/mypylogger/
