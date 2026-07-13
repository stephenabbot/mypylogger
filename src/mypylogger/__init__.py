"""mypylogger — zero-dependency structured JSON logging for Python.

Public API:
    get_logger(name=None, static_fields=None) -> logging.Logger
    bind(**fields) -> None
    clear_bindings() -> None

Behavior is defined by ``01_rewrite_specification.md``. Two implementation
notes where the code intentionally realizes the spec's *intent* rather than a
literal snippet:

* Exception tracebacks are rendered with ``traceback.format_exception`` bound to
  the record's own ``exc_info`` (spec §6). ``traceback.format_exc`` reads the
  current thread's exception state, which is empty on the background drain
  thread, so it cannot be used in an async pipeline.
* Context-bound fields (spec §7) are captured onto the record as a single
  marker dict so the formatter can emit them in the exact position required by
  the field-ordering contract (spec §4.2, item 9 — before per-call ``extra``).
"""

from __future__ import annotations

import atexit
import contextlib
import contextvars
import datetime
import errno
import json
import logging
import logging.handlers
import multiprocessing
import os
import queue
import selectors
import signal
import socket
import sys
import threading
import traceback
from pathlib import Path
from types import FrameType
from typing import Any, cast

__version__ = "1.0.0"

__all__ = ["__version__", "bind", "clear_bindings", "get_logger"]

_SOCKET_HOST = "127.0.0.1"


# --------------------------------------------------------------------------- #
# Configuration — read once at import time (spec §3).
# --------------------------------------------------------------------------- #
def _env_flag(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() == "true"


def _resolve_level(name: str) -> int:
    level = getattr(logging, name.upper(), None)
    return level if isinstance(level, int) else logging.INFO


_APP_NAME: str = os.environ.get("APP_NAME", "mypylogger")
_LOG_LEVEL: int = _resolve_level(os.environ.get("LOG_LEVEL", "INFO"))
_LOG_TO_FILE: bool = _env_flag("LOG_TO_FILE")
_LOG_FILE_DIR: str = os.environ.get("LOG_FILE_DIR") or str(Path.cwd())
_LOG_MULTIPROCESS: bool = _env_flag("LOG_MULTIPROCESS")
_LOG_SOCKET_PORT: int = int(os.environ.get("LOG_SOCKET_PORT", "9020"))


# --------------------------------------------------------------------------- #
# Static global fields (spec §4.4).
# --------------------------------------------------------------------------- #
def _suppressed(var: str) -> bool:
    """True when ``var`` is present in the environment but set to an empty string."""
    return os.environ.get(var) == ""


def _build_static_fields() -> dict[str, Any]:
    fields: dict[str, Any] = {}
    if not _suppressed("HOSTNAME"):
        fields["hostname"] = os.environ.get("HOSTNAME") or socket.gethostname()
    fields["pid"] = os.getpid()  # not env-sourced; never suppressed
    fields["service"] = os.environ.get("APP_NAME", "mypylogger")
    if not _suppressed("APP_ENV"):
        fields["environment"] = os.environ.get("APP_ENV", "unknown")
    if not _suppressed("APP_VERSION"):
        fields["version"] = os.environ.get("APP_VERSION", "unknown")
    return fields


_static_lock = threading.Lock()
_static_fields: dict[str, Any] = _build_static_fields()


def _register_static_fields(fields: dict[str, str]) -> None:
    with _static_lock:
        _static_fields.update(fields)


# --------------------------------------------------------------------------- #
# Context-bound fields (spec §7).
# --------------------------------------------------------------------------- #
_context_fields: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "mypylogger_context",
    default={},  # noqa: B039 — never mutated in place; bind()/clear_bindings() replace it (spec §7)
)


def bind(**fields: Any) -> None:
    """Merge ``fields`` into the context-local bindings (spec §7.2)."""
    current = _context_fields.get().copy()
    current.update(fields)
    _context_fields.set(current)


def clear_bindings() -> None:
    """Remove all context-local bindings (spec §7.2)."""
    _context_fields.set({})


class _ContextFilter(logging.Filter):
    """Capture context bindings onto the record at call time (spec §7.3)."""

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = _context_fields.get()
        if ctx:
            record.__dict__["_mypylogger_context"] = ctx
        return True


# --------------------------------------------------------------------------- #
# JSON formatter (spec §4, §6).
# --------------------------------------------------------------------------- #
_RESERVED_ATTRS = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}


def _format_error(exc_info: Any) -> dict[str, str]:
    exc_type, exc, tb = exc_info
    etype = exc_type.__name__ if exc_type is not None else type(exc).__name__
    stack = "".join(traceback.format_exception(exc_type, exc, tb)).rstrip()
    return {
        "type": etype,
        "message": str(exc),
        "stack_trace": stack.replace("\n", "\\n"),
    }


class _JSONFormatter(logging.Formatter):
    """Render a record as a single JSON line with the spec §4.2 field order."""

    def format(self, record: logging.LogRecord) -> str:
        moment = datetime.datetime.fromtimestamp(record.created, tz=datetime.UTC)
        event: dict[str, Any] = {
            "timestamp": moment.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "filename": record.filename,
            "function_name": record.funcName,
            "line": record.lineno,
        }
        with _static_lock:
            event.update(_static_fields)
        ctx = record.__dict__.get("_mypylogger_context")
        if ctx:
            event.update(ctx)
        for key, value in record.__dict__.items():
            if key in _RESERVED_ATTRS or key.startswith("_mypylogger"):
                continue
            event[key] = value
        if record.exc_info and record.exc_info != (None, None, None):
            event["error"] = _format_error(record.exc_info)
        return json.dumps(event, ensure_ascii=False, default=str)


_formatter = _JSONFormatter()


# --------------------------------------------------------------------------- #
# Handlers (spec §5, §8, §10, §11).
# --------------------------------------------------------------------------- #
class _MaxLevelFilter(logging.Filter):
    def __init__(self, max_level: int) -> None:
        super().__init__()
        self._max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= self._max_level


class _MinLevelFilter(logging.Filter):
    def __init__(self, min_level: int) -> None:
        super().__init__()
        self._min_level = min_level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= self._min_level


class _PassThroughQueueHandler(logging.handlers.QueueHandler):
    """Enqueue records unmodified so ``exc_info`` and context survive the queue.

    The stdlib default ``prepare`` pre-formats the record and drops ``exc_info``
    for cross-process pickling. Our queue is in-process, so we pass the record
    through intact (spec §8, and §1 rationale for the 3.12 floor).
    """

    def prepare(self, record: logging.LogRecord) -> logging.LogRecord:
        return record


def _make_stdout_handler() -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_MaxLevelFilter(logging.INFO))
    handler.setFormatter(_formatter)
    return handler


def _make_stderr_handler() -> logging.Handler:
    handler = logging.StreamHandler(sys.stderr)
    handler.addFilter(_MinLevelFilter(logging.WARNING))
    handler.setFormatter(_formatter)
    return handler


def _file_path(file_dir: str, app_name: str) -> Path:
    directory = Path(file_dir)
    directory.mkdir(parents=True, exist_ok=True)
    date = datetime.datetime.now(tz=datetime.UTC).strftime("%Y-%m-%d")
    return directory / f"{app_name}-{date}.log"


def _make_timed_file_handler(
    file_dir: str,
    app_name: str,
) -> logging.handlers.TimedRotatingFileHandler:
    return logging.handlers.TimedRotatingFileHandler(
        _file_path(file_dir, app_name),
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )


def _make_file_handler() -> logging.Handler:
    handler = _make_timed_file_handler(_LOG_FILE_DIR, _APP_NAME)
    handler.setFormatter(_formatter)
    return handler


class _JSONSocketHandler(logging.Handler):
    """Ship newline-delimited JSON to the Tier-2 listener (spec §11.3).

    Never blocks or raises into the caller: on failure it drops the record and
    emits a single stderr warning (spec §11.5).
    """

    def __init__(self, host: str, port: int) -> None:
        super().__init__()
        self._host = host
        self._port = port
        self._sock: socket.socket | None = None
        self._warned = False
        self.setFormatter(_formatter)

    def _ensure_conn(self) -> None:
        if self._sock is None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            sock.connect((self._host, self._port))
            self._sock = sock

    def emit(self, record: logging.LogRecord) -> None:
        try:
            line = self.format(record) + "\n"
            self._ensure_conn()
            sock = self._sock
            if sock is not None:
                sock.sendall(line.encode("utf-8"))
        except Exception:  # degrade gracefully, never raise into the caller
            self._drop()

    def _drop(self) -> None:
        if self._sock is not None:
            with contextlib.suppress(OSError):
                self._sock.close()
            self._sock = None
        if not self._warned:
            self._warned = True
            with contextlib.suppress(OSError):
                sys.stderr.write(
                    "mypylogger: file-log listener unreachable; dropping file records\n"
                )

    def close(self) -> None:
        if self._sock is not None:
            with contextlib.suppress(OSError):
                self._sock.close()
            self._sock = None
        super().close()


# --------------------------------------------------------------------------- #
# Tier-2 listener process (spec §11).
# --------------------------------------------------------------------------- #
class _RawFormatter(logging.Formatter):
    """Emit the pre-built JSON line verbatim (workers already formatted it)."""

    def format(self, record: logging.LogRecord) -> str:
        return record.getMessage()


def _write_line(handler: logging.Handler, raw: bytes) -> None:
    if not raw.strip():
        return
    try:
        text = raw.decode("utf-8")
        json.loads(text)  # validate; malformed lines are dropped (spec §11.3)
    except (ValueError, UnicodeDecodeError):
        return
    handler.emit(logging.makeLogRecord({"msg": text}))


def _listener_main(server: socket.socket, file_dir: str, app_name: str) -> None:
    """Sole writer/rotator: drain client sockets to the shared file (spec §11.1)."""

    def _stop(_signum: int, _frame: FrameType | None) -> None:
        sys.exit(0)

    with contextlib.suppress(ValueError, OSError):
        signal.signal(signal.SIGTERM, _stop)

    handler = _make_timed_file_handler(file_dir, app_name)
    handler.setFormatter(_RawFormatter())
    selector = selectors.DefaultSelector()
    server.setblocking(False)
    selector.register(server, selectors.EVENT_READ, data=None)
    buffers: dict[int, bytes] = {}
    try:
        while True:
            for key, _mask in selector.select(timeout=1.0):
                if key.data is None:
                    _accept(server, selector, buffers)
                else:
                    _drain(cast(socket.socket, key.fileobj), selector, buffers, handler)
    except SystemExit:
        pass
    finally:
        handler.close()
        with contextlib.suppress(OSError):
            server.close()


def _accept(
    server: socket.socket,
    selector: selectors.BaseSelector,
    buffers: dict[int, bytes],
) -> None:
    try:
        conn, _addr = server.accept()
    except OSError:
        return
    conn.setblocking(False)
    selector.register(conn, selectors.EVENT_READ, data=conn.fileno())
    buffers[conn.fileno()] = b""


def _drain(
    conn: socket.socket,
    selector: selectors.BaseSelector,
    buffers: dict[int, bytes],
    handler: logging.Handler,
) -> None:
    fileno = conn.fileno()
    try:
        data = conn.recv(65536)
    except (BlockingIOError, InterruptedError):
        return
    except OSError:
        data = b""
    if not data:
        selector.unregister(conn)
        buffers.pop(fileno, None)
        conn.close()
        return
    buffer = buffers.get(fileno, b"") + data
    while b"\n" in buffer:
        line, buffer = buffer.split(b"\n", 1)
        _write_line(handler, line)
    buffers[fileno] = buffer


# --------------------------------------------------------------------------- #
# Pipeline lifecycle (spec §8, §9).
# --------------------------------------------------------------------------- #
_lock = threading.RLock()
_queue: queue.Queue[Any] | None = None
_queue_handler: _PassThroughQueueHandler | None = None
_listener: logging.handlers.QueueListener | None = None
_loggers: dict[str, logging.Logger] = {}
_tier2_proc: Any = None


def _start_tier2() -> None:
    """First-binder-elects the listener process (spec §11.2)."""
    global _tier2_proc
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind((_SOCKET_HOST, _LOG_SOCKET_PORT))
        server.listen(128)
    except OSError as exc:
        server.close()
        if exc.errno in (errno.EADDRINUSE, errno.EACCES):
            return  # a listener already owns the socket; act as client only
        raise
    proc = multiprocessing.get_context("fork").Process(
        target=_listener_main,
        args=(server, _LOG_FILE_DIR, _APP_NAME),
        daemon=True,
    )
    proc.start()
    server.close()  # the forked child holds its own copy of the fd
    _tier2_proc = proc


def _ensure_initialized() -> None:
    global _queue, _queue_handler, _listener
    if _listener is not None:
        return
    events: queue.Queue[Any] = queue.Queue()
    handlers: list[logging.Handler] = [_make_stdout_handler(), _make_stderr_handler()]
    if _LOG_TO_FILE:
        if _LOG_MULTIPROCESS:
            _start_tier2()
            handlers.append(_JSONSocketHandler(_SOCKET_HOST, _LOG_SOCKET_PORT))
        else:
            handlers.append(_make_file_handler())
    listener = logging.handlers.QueueListener(events, *handlers, respect_handler_level=True)
    listener.start()
    _queue = events
    _queue_handler = _PassThroughQueueHandler(events)
    _listener = listener


def _resolve_name(name: str | None) -> str:
    if name:
        return name
    env = os.environ.get("APP_NAME")
    if env:
        return env
    return "mypylogger"


def get_logger(
    name: str | None = None,
    static_fields: dict[str, str] | None = None,
) -> logging.Logger:
    """Return a configured JSON logger (spec §9).

    Args:
        name: Logger name. Falls back to ``APP_NAME`` then ``"mypylogger"``.
        static_fields: Process-global static fields merged into every event
            (spec §4.4). Caller keys override auto-detected keys.

    Returns:
        A cached ``logging.Logger``; the same resolved name yields the same
        object with no handler duplication.
    """
    if static_fields:
        _register_static_fields(static_fields)
    resolved = _resolve_name(name)
    with _lock:
        _ensure_initialized()
        cached = _loggers.get(resolved)
        if cached is not None:
            return cached
        handler = _queue_handler
        if handler is None:  # pragma: no cover — _ensure_initialized sets it
            msg = "logging pipeline not initialized"
            raise RuntimeError(msg)
        logger = logging.getLogger(resolved)
        logger.setLevel(_LOG_LEVEL)
        logger.propagate = False
        logger.handlers.clear()
        logger.filters.clear()
        logger.addFilter(_ContextFilter())
        logger.addHandler(handler)
        _loggers[resolved] = logger
        return logger


# --------------------------------------------------------------------------- #
# Shutdown & fork safety (spec §8.3, §8.4).
# --------------------------------------------------------------------------- #
def _shutdown(timeout: float = 5.0) -> None:
    """Drain and stop the pipeline. Idempotent (spec §8.3)."""
    global _listener, _tier2_proc
    with _lock:
        listener = _listener
        _listener = None
        proc = _tier2_proc
        _tier2_proc = None
    if listener is not None:
        with contextlib.suppress(Exception):  # shutdown must never raise
            listener.stop()  # lossless drain + join on 3.12+
    if proc is not None:
        with contextlib.suppress(Exception):  # shutdown must never raise
            proc.terminate()
            proc.join(timeout)


def _reinitialize_after_fork() -> None:
    """Discard the parent's (unforked) pipeline; re-init lazily (spec §8.4)."""
    global _queue, _queue_handler, _listener, _loggers, _tier2_proc
    _listener = None
    _queue = None
    _queue_handler = None
    _loggers = {}
    _tier2_proc = None
    if "pid" in _static_fields:
        _static_fields["pid"] = os.getpid()


atexit.register(_shutdown)


def _sigterm_handler(signum: int, frame: FrameType | None) -> None:
    _shutdown()
    sys.exit(0)


with contextlib.suppress(ValueError, OSError):  # not on the main thread
    signal.signal(signal.SIGTERM, _sigterm_handler)

if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_reinitialize_after_fork)
