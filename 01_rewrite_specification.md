# mypylogger v1 — Functional Specification

**Audience:** AI agent implementing the rewrite.  
**Status:** Authoritative. Implement exactly as written; do not infer unstated behavior.  
**Derived from:** Behavioral testing of PyPI `mypylogger==0.2.8` + QnA session 2026-07-12.

---

## 1. Goals and constraints

- Personal convenience library: no rewriting a logger for every Python project.
- Portfolio signal: elegant, minimal LOC, production-ready.
- **Zero runtime dependencies.** stdlib only — hard constraint.
- **Python minimum: 3.12.** Rationale: `QueueHandler.prepare()` extension point, lossless `QueueListener` shutdown, clean async pipeline without workarounds.
- Target environments: macOS local, Linux local, AWS Lambda, ECS/Linux containers.
- Windows: not required.

---

## 2. Package structure

Single package: `mypylogger/`. All implementation in `mypylogger/__init__.py`. No submodules.

Public surface (everything else is private, prefixed `_`):

```
mypylogger.get_logger(name=None, static_fields=None) -> logging.Logger
mypylogger.bind(**fields) -> None
mypylogger.clear_bindings() -> None
```

`static_fields: dict[str, str] | None` — optional caller-supplied static fields registered at declaration time (see §4.4). Merged into the module-level static dict; applied to every event globally (static fields are process-global, not per-logger).

---

## 3. Configuration — environment variables

Read once at import time. No config file support.

| Variable | Type | Default | Effect |
|---|---|---|---|
| `APP_NAME` | str | `"mypylogger"` | Logger name and log file prefix |
| `LOG_LEVEL` | str | `"INFO"` | Effective log level (case-insensitive) |
| `LOG_TO_FILE` | str | `"false"` | Enable file handler when `"true"` (case-insensitive) |
| `LOG_FILE_DIR` | str | CWD at import time | Directory for log files |
| `LOG_MULTIPROCESS` | str | `"false"` | When `"true"` (with `LOG_TO_FILE="true"`), route file writes through the library-owned listener process (§11) for safe multi-process shared-file logging |
| `LOG_SOCKET_PORT` | int | `9020` | TCP port on `127.0.0.1` for the Tier-2 listener (§11). Only used when `LOG_MULTIPROCESS="true"` |
| `HOSTNAME` | str | `socket.gethostname()` | Static field: hostname |
| `APP_ENV` | str | `"unknown"` | Static field: environment |
| `APP_VERSION` | str | `"unknown"` | Static field: version |

**Static field suppression:** if any of `HOSTNAME`, `APP_ENV`, or `APP_VERSION` is set to an empty string in the environment, omit that field from all log events entirely. Do not emit the key with a null or empty value.

---

## 4. Output format

### 4.1 Encoding

- Valid JSON, one event per line (`\n` terminated).
- All string values must be JSON-safe (control characters and special characters escaped).
- Non-serializable values in `extra` or context fields: convert to `str()`, do not raise.

### 4.2 Field ordering

Fields must appear in this exact order:

1. `timestamp` — always first
2. `level`
3. `message`
4. `module`
5. `filename`
6. `function_name`
7. `line`
8. Static global fields (in definition order: `hostname`, `pid`, `service`, `environment`, `version`, then any caller-supplied `static_fields` in insertion order) — omit any suppressed field
9. Context-bound fields (`bind()`) — in insertion order
10. Per-call `extra` fields — in the order provided by the caller
11. `error` object — only present when an exception is attached (see §6)

### 4.3 Base field definitions

| Field | Source | Type |
|---|---|---|
| `timestamp` | `record.created` converted to UTC | str — ISO 8601, microsecond precision, Z suffix |
| `level` | `record.levelname` | str |
| `message` | `record.getMessage()` | str |
| `module` | `record.module` | str |
| `filename` | `record.filename` | str |
| `function_name` | `record.funcName` | str |
| `line` | `record.lineno` | int |

**Timestamp format:** `datetime.datetime.fromtimestamp(record.created, tz=datetime.timezone.utc)` formatted as `YYYY-MM-DDTHH:MM:SS.ffffffZ` (exactly 6 decimal digits, always Z suffix, never `+00:00`).

### 4.4 Static global fields

Initialized once at module import. Two sources:

**(a) Auto-detected runtime values** — always present unless suppressed:

| Field | Value |
|---|---|
| `hostname` | `os.environ.get('HOSTNAME') or socket.gethostname()` |
| `pid` | `os.getpid()` (int) — re-read after fork (§8.4) |
| `service` | `os.environ.get('APP_NAME', 'mypylogger')` |
| `environment` | `os.environ.get('APP_ENV', 'unknown')` |
| `version` | `os.environ.get('APP_VERSION', 'unknown')` |

**(b) Caller-supplied static fields** — the `static_fields` dict passed to `get_logger()` (§2). Merged into the module-level static dict on first initialization; later calls update it. These are process-global (applied to every event, every logger), not per-logger. Keys collide-last-wins; caller fields override auto-detected fields of the same name.

Stored in a single module-level `dict`. Applied to every log event by the formatter. `pid` is exempt from empty-string suppression (it is not env-sourced).

---

## 5. Stream routing

Two `logging.StreamHandler` instances, both attached to the same `QueueListener` (see §8):

- **stdout handler:** emits `DEBUG` and `INFO` only. Filter: `record.levelno <= logging.INFO`.
- **stderr handler:** emits `WARNING`, `ERROR`, and `CRITICAL` only. Filter: `record.levelno >= logging.WARNING`.

Both handlers use the same `_JSONFormatter` instance.

---

## 6. Exception handling

When a log record carries exception info (`record.exc_info` is not None and not `(None, None, None)`):

Append an `error` object as the last field in the JSON event:

```json
"error": {
  "type": "<exception class name, e.g. ValueError>",
  "message": "<str(exception)>",
  "stack_trace": "<formatted traceback as a single string, newlines as \\n>"
}
```

- `type`: `type(exc).__name__` — class name only, no module prefix.
- `message`: `str(exc)`.
- `stack_trace`: `traceback.format_exc()` stripped of trailing whitespace, with internal newlines replaced by `\n` (literal backslash-n) so the entire value is a single JSON string.
- **Do not append exception text to `message`.** The `message` field contains only what the caller passed.
- **Do not emit `exc_info` or `exc_text`** as separate fields.
- This fixes a confirmed bug in v0.2.8 where traceback was silently dropped.

---

## 7. Context-bound fields

### 7.1 Storage

```python
import contextvars
_context_fields: contextvars.ContextVar[dict] = contextvars.ContextVar(
    'mypylogger_context', default={}
)
```

`ContextVar` is automatically scoped per async task and per thread (when set per thread). Module-level `bind()` does not bleed across concurrent requests.

### 7.2 Public API

```python
def bind(**fields) -> None:
    current = _context_fields.get().copy()
    current.update(fields)
    _context_fields.set(current)

def clear_bindings() -> None:
    _context_fields.set({})
```

### 7.3 Injection

A `_ContextFilter` subclassing `logging.Filter` reads `_context_fields.get()` and sets each key as an attribute on `record`. Applied to the `QueueHandler` (caller-side, before enqueue) so context is captured at call time, not drain time.

```python
class _ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for k, v in _context_fields.get().items():
            setattr(record, k, v)
        return True
```

---

## 8. Concurrency model

### 8.1 Architecture

```
caller thread
  logger.info(...)
    → _ContextFilter.filter()   # captures context at call time
    → QueueHandler.emit()       # enqueues, non-blocking
        → Queue (thread-safe)
            → QueueListener (background thread)
                → stdout StreamHandler  (DEBUG, INFO)
                → stderr StreamHandler  (WARNING, ERROR, CRITICAL)
                → FileHandler           (if LOG_TO_FILE=true)
```

### 8.2 QueueHandler / QueueListener

- Use `queue.Queue()` (unbounded) — do not set `maxsize`. Blocking callers on a full queue is not acceptable.
- `QueueListener` started with `respect_handler_level=True`.
- One `QueueListener` per process, module-level singleton, started lazily on first `get_logger()` call.

### 8.3 Shutdown

Register both of the following at module import time:

**atexit:**
```python
import atexit
atexit.register(_shutdown)
```

**SIGTERM handler:**
```python
import signal
def _sigterm_handler(signum, frame):
    _shutdown()
    sys.exit(0)
signal.signal(signal.SIGTERM, _sigterm_handler)
```

**`_shutdown()` implementation:**
```python
def _shutdown(timeout: float = 5.0) -> None:
    if _listener is not None:
        _listener.stop()   # QueueListener.stop() drains the queue before returning
```

`QueueListener.stop()` in Python 3.12+ is lossless: it enqueues a sentinel and joins the background thread. The `timeout` parameter is reserved for future use if a manual drain loop is needed; for now, `stop()` handles it.

`_shutdown()` must be idempotent — safe to call more than once (guard with a flag or check `_listener is None`).

### 8.4 Fork safety

Register at module import time:

```python
os.register_at_fork(
    after_in_child=_reinitialize_after_fork
)
```

`_reinitialize_after_fork()`: closes the existing `QueueListener` and its queue without joining (the background thread was not forked into the child), clears `_listener` and `_loggers`, and re-initializes fresh on next `get_logger()` call.

---

## 9. Logger lifecycle and caching

```python
_loggers: dict[str, logging.Logger] = {}

def get_logger(name: str | None = None) -> logging.Logger:
    ...
```

**Name resolution (in order):**
1. `name` argument if not None and not empty string
2. `os.environ.get('APP_NAME')` if set and non-empty
3. `"mypylogger"` (literal fallback)

This fixes a v0.2.8 documentation bug (docstring claimed fallback was `__name__`; actual behavior and correct behavior is `"mypylogger"`).

**Caching:** same resolved name → same `logging.Logger` object returned. No handler duplication. Cache stored in `_loggers`.

**Logger configuration (on first creation):**
- `logger.setLevel(...)` from `LOG_LEVEL` env var
- `logger.propagate = False`
- `logger.addFilter(_ContextFilter())`
- `logger.addHandler(_get_queue_handler())` — the single `QueueHandler` backed by the module-level queue

Child loggers created via `logging.getLogger('parent.child')` propagate to the parent by default (stdlib behavior, do not override).

---

## 10. File logging (two-tier)

File logging is enabled only when `LOG_TO_FILE` is `"true"` (case-insensitive). The write path depends on `LOG_MULTIPROCESS`.

### 10.1 Tier 1 — single process (default; `LOG_MULTIPROCESS` != `"true"`)

- `logging.handlers.TimedRotatingFileHandler`
- `when='midnight'`, `backupCount=7`, `encoding='utf-8'` — **daily** rotation.
- Filename: `{APP_NAME}-{YYYY-MM-DD}.log` in `LOG_FILE_DIR` (or `Path.cwd()` if unset).
- Uses the same `_JSONFormatter` instance as the stream handlers.
- Added to the `QueueListener`'s handler list, not directly to the logger.
- **Do not use system temp as the default directory.** `Path.cwd()` is the correct default.
- **Not multi-process safe.** If two processes point at the same file in this tier, rotation races and appends can corrupt. Tier 1 is defined as single-process only; multi-process file logging requires Tier 2.

### 10.2 Tier 2 — multi-process shared file (`LOG_MULTIPROCESS` == `"true"` and `LOG_TO_FILE` == `"true"`)

A **single library-owned listener process** is the sole writer and sole rotator of the shared file. Worker processes never touch the file directly; they ship records to the listener over a socket. See §11.

Rationale: `TimedRotatingFileHandler` is not multi-process safe (rotation renames+reopens → races, lost logs). Exactly one writer eliminates both corruption and rotation races. Per-process file fan-out and `fcntl` locking were both considered and rejected (fan-out proliferates files; locking still races on rotation).

---

## 11. Multi-process listener (Tier 2 architecture)

Library-owned. Auto-starts on first use, auto-stops on shutdown. Active only when both `LOG_MULTIPROCESS` and `LOG_TO_FILE` are `"true"`.

### 11.1 Roles

- **Listener process:** owns the `TimedRotatingFileHandler` (config as §10.1) and is the single writer/rotator. Binds a TCP socket on `127.0.0.1:{LOG_SOCKET_PORT}` and drains incoming events to the file.
- **Worker (client) process:** its `QueueListener` fans out to stdout/stderr (§5) locally, plus a socket client that sends each event to the listener. Workers do **not** attach a `FileHandler`.

### 11.2 Election and discovery (no separate entry point)

- On first Tier-2 initialization, a process attempts to `bind()` `127.0.0.1:{LOG_SOCKET_PORT}`.
  - **Bind succeeds** → this process spawns the listener in a dedicated child via `multiprocessing.Process` (daemon), hands it the bound socket, and also acts as a normal worker client.
  - **Bind fails (`EADDRINUSE`)** → a listener already exists; the process connects as a client only.
- This first-binder-elects pattern needs no standalone entry point and no lock file; the OS bind is the atomic election primitive.

### 11.3 Transport

- **Newline-delimited JSON** over TCP to `127.0.0.1:{LOG_SOCKET_PORT}`. One event = one JSON object + `\n`. **Never pickle** (eliminates the v0.2.8 code-execution risk).
- The listener reads line-framed, parses each line, and re-emits through its `TimedRotatingFileHandler` using the same schema/formatter. Malformed lines are dropped, not raised.
- Bound to `127.0.0.1` only — never a routable interface.

### 11.4 Lifecycle

- **Start:** lazy, on the first `get_logger()` in a Tier-2 process (§11.2).
- **Stop:** the listener drains its socket backlog, then closes the file, on `_shutdown()` (§8.3) via `atexit` + SIGTERM. The spawning process signals the child listener to stop and joins it with the `_shutdown` timeout.
- **Fork safety:** clients re-establish their socket connection after fork (§8.4); a forked child never inherits the listener role.

### 11.5 Consistency and failure

- **Eventually consistent.** Events traverse per-process queue → socket → listener → file asynchronously. On a hard crash (SIGKILL, power loss), events still in a worker's queue or in flight on the socket are lost. Inherent to non-blocking logging; accepted.
- Local stdout/stderr emission (§5) is unaffected by listener state — a worker always logs to its own streams even if the listener is unreachable.
- If a worker cannot reach the listener, it must not block or raise into the caller: drop-and-continue (optionally emit a one-time internal warning to stderr).

---

## 12. Behavioral corrections from v0.2.8

Implement all of the following; do not carry forward any of these bugs:

| # | v0.2.8 behavior | Correct behavior |
|---|---|---|
| 1 | Exception traceback silently dropped | ECS-structured `error` object (§6) |
| 2 | Name resolution fallback was `__name__` per docstring; actual was `"mypylogger"` | Actual behavior kept, docstring fixed |
| 3 | No ECS exception structure | Implemented (§6) |
| 4 | No context-bound field injection | `bind()` / `clear_bindings()` via `ContextVar` (§7) |
| 5 | No static global fields | Auto-detected `hostname`, `pid`, `service`, `environment`, `version` + caller `static_fields` (§4.4) |
| 6 | All levels routed to stdout | Level-based routing: DEBUG/INFO → stdout, WARNING+ → stderr (§5) |
| 7 | File default was system temp | File default is CWD (§10) |
| 8 | No log rotation | `TimedRotatingFileHandler` daily rotation (§10) |
| 9 | Socket transport used pickle | Tier-2 multi-process listener uses newline-delimited JSON over socket, never pickle (§11) |

---

## 13. Non-goals (do not implement)

- Config file (TOML or otherwise)
- Per-logger `bind()` — module-level only
- Windows support
- Any runtime dependency outside stdlib
- Log sampling, rate limiting, or buffering beyond the QueueHandler queue
- HTTP/remote log shipping
- Log redaction or masking
- Structured query or search API

---

## 14. Key behaviors to verify during implementation

These are the non-obvious invariants that must hold:

1. **Field order is stable.** JSON keys appear in the order specified in §4.2 across all event types (normal, exception, with extras, with context fields).
2. **Timestamp has exactly 6 decimal digits** and ends in `Z`, never `+00:00`.
3. **Exception traceback appears in `error.stack_trace`**, not appended to `message`, and contains no unescaped newlines.
4. **`bind()` fields are captured at call time**, not at drain time. (Context filter runs on the caller thread, not the listener thread.)
5. **Same name → same logger object.** Call `get_logger("x")` twice; assert `is` identity, assert handler count does not double.
6. **`propagate = False`** on all loggers created by this library. Root logger must not receive duplicate events.
7. **stdout receives only DEBUG and INFO.** stderr receives only WARNING, ERROR, CRITICAL. Verify with captured output.
8. **Static fields are omitted (not nulled)** when the corresponding env var is set to empty string.
9. **`_shutdown()` is idempotent.** Call twice; no exception, no hang.
10. **Non-serializable `extra` value** (e.g. a custom object) is rendered as `str()`, not dropped and not raised.
