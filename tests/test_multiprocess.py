"""Tier-2 multi-process file logging: socket transport and listener process."""

from __future__ import annotations

import logging
import selectors
import socket
import time

import mypylogger as m


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def test_raw_formatter_passes_message_through():
    record = logging.makeLogRecord({"msg": '{"already": "json"}'})
    assert m._RawFormatter().format(record) == '{"already": "json"}'


def test_write_line_validates_json(tmp_path):
    handler = m._make_timed_file_handler(str(tmp_path), "wl")
    handler.setFormatter(m._RawFormatter())
    m._write_line(handler, b'{"a": 1}')
    m._write_line(handler, b"not-json")
    m._write_line(handler, b"   ")
    m._write_line(handler, b"\xff\xfe")  # invalid utf-8
    handler.close()
    content = next(tmp_path.glob("wl-*.log")).read_text()
    assert '{"a": 1}' in content
    assert "not-json" not in content


def test_socket_handler_unreachable_does_not_raise():
    handler = m._JSONSocketHandler("127.0.0.1", _free_port())  # nothing listening
    record = logging.LogRecord("a", logging.INFO, "/p/a.py", 1, "hi", (), None)
    handler.emit(record)  # must not raise
    assert handler._warned is True
    handler.close()


def test_accept_and_drain_line_framing(tmp_path):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen()
    port = server.getsockname()[1]

    selector = selectors.DefaultSelector()
    server.setblocking(False)
    selector.register(server, selectors.EVENT_READ, data=None)
    buffers: dict[int, bytes] = {}

    client = socket.create_connection(("127.0.0.1", port))
    time.sleep(0.05)
    m._accept(server, selector, buffers)
    accepted = next(k.fileobj for k in selector.get_map().values() if k.data is not None)

    handler = m._make_timed_file_handler(str(tmp_path), "ad")
    handler.setFormatter(m._RawFormatter())

    client.sendall(b'{"x": 1}\n{"y": 2}\n')
    time.sleep(0.05)
    m._drain(accepted, selector, buffers, handler)

    client.sendall(b'{"z": 3}')  # unterminated; must not be written
    time.sleep(0.05)
    m._drain(accepted, selector, buffers, handler)

    client.close()
    time.sleep(0.05)
    m._drain(accepted, selector, buffers, handler)  # empty read -> unregister/close

    handler.close()
    server.close()
    content = next(tmp_path.glob("ad-*.log")).read_text()
    assert '{"x": 1}' in content
    assert '{"y": 2}' in content
    assert '{"z": 3}' not in content


def test_start_tier2_second_binder_is_client_only(monkeypatch):
    port = _free_port()
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    blocker.bind(("127.0.0.1", port))
    blocker.listen()
    try:
        monkeypatch.setattr(m, "_LOG_SOCKET_PORT", port)
        m._tier2_proc = None
        m._start_tier2()  # bind fails (EADDRINUSE) -> client only
        assert m._tier2_proc is None
    finally:
        blocker.close()


def test_tier2_end_to_end_writes_shared_file(tmp_path, monkeypatch):
    port = _free_port()
    monkeypatch.setattr(m, "_LOG_FILE_DIR", str(tmp_path))
    monkeypatch.setattr(m, "_LOG_SOCKET_PORT", port)
    monkeypatch.setattr(m, "_APP_NAME", "mp")

    m._start_tier2()
    assert m._tier2_proc is not None
    try:
        handler = m._JSONSocketHandler("127.0.0.1", port)
        record = logging.LogRecord("mp", logging.INFO, "/p/a.py", 1, "hello-mp", (), None, func="f")
        time.sleep(0.3)
        handler.emit(record)
        time.sleep(0.4)
        handler.close()
    finally:
        m._shutdown()  # terminates and joins the listener process

    time.sleep(0.2)
    files = list(tmp_path.glob("mp-*.log"))
    assert files, "listener process should have created the log file"
    assert "hello-mp" in files[0].read_text()
