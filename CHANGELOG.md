# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-12

Clean-slate rewrite. The `0.2.x` line is retired; nothing is carried forward.

### Breaking

- **Python floor raised to 3.12** (from 3.8), for a lossless async logging
  pipeline (`QueueHandler.prepare()` extension point, lossless `QueueListener`
  shutdown).
- **New public API surface:** `get_logger(name=None, static_fields=None)`,
  `bind(**fields)`, `clear_bindings()`. Legacy modules
  (`config`, `formatters`, `handlers`, `core`, `exceptions`) are removed; the
  library is a single module.

### Added

- Structured ECS-style `error` object (`type`, `message`, `stack_trace`) on
  exception records — fixes silent traceback loss in 0.2.x.
- Context-bound fields via `bind()` / `clear_bindings()`, scoped per async task
  and thread with `contextvars`.
- Auto-detected static global fields (`hostname`, `pid`, `service`,
  `environment`, `version`) plus caller-supplied `static_fields`.
- Level-based stream routing: DEBUG/INFO to stdout, WARNING/ERROR/CRITICAL to
  stderr.
- Non-blocking `QueueHandler`/`QueueListener` pipeline with `atexit` + SIGTERM
  drain and fork re-initialization.
- Two-tier file logging: `TimedRotatingFileHandler` (daily) for single process;
  a library-owned single-writer listener process over newline-delimited JSON on
  `127.0.0.1` for multi-process shared-file logging.

### Changed

- Default log-file directory is the current working directory (was system temp).
- Multi-process socket transport uses newline-delimited JSON, never pickle.

### Removed

- Stored PyPI token and rotation infrastructure — publishing is via PyPI Trusted
  Publishing (OIDC).
- Homegrown badge subsystem, security tooling, scripts, and Sphinx docs.

[1.0.0]: https://github.com/stephenabbot/mypylogger/releases/tag/v1.0.0
