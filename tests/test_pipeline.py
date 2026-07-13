"""End-to-end pipeline: stream routing, config, static-field construction, shutdown."""

from __future__ import annotations

import json
import logging
import os

import mypylogger as m


def test_stream_routing_end_to_end(fresh_pipeline, capsys):
    logger = m.get_logger("route-svc")
    logger.setLevel(logging.DEBUG)
    logger.debug("dbg-line")
    logger.info("out-line")
    logger.warning("err-line")
    logger.error("err-line-2")
    m._shutdown()  # drain the listener before reading

    captured = capsys.readouterr()
    assert "out-line" in captured.out
    assert "dbg-line" in captured.out
    assert "out-line" not in captured.err
    assert "err-line" in captured.err
    assert "err-line-2" in captured.err
    assert "err-line" not in captured.out

    out_lines = [json.loads(line) for line in captured.out.strip().splitlines()]
    assert {rec["level"] for rec in out_lines} <= {"DEBUG", "INFO"}
    err_lines = [json.loads(line) for line in captured.err.strip().splitlines()]
    assert {rec["level"] for rec in err_lines} <= {"WARNING", "ERROR", "CRITICAL"}


def test_bound_fields_appear_in_output(fresh_pipeline, capsys):
    logger = m.get_logger("bind-svc")
    m.bind(request_id="req-42")
    logger.info("with-context")
    m.clear_bindings()
    m._shutdown()
    obj = json.loads(capsys.readouterr().out.strip())
    assert obj["request_id"] == "req-42"


def test_shutdown_is_idempotent():
    m.get_logger("shutdown-svc")
    m._shutdown()
    m._shutdown()  # must not raise or hang


def test_reinitialize_after_fork_resets_state():
    m.get_logger("fork-svc")
    assert m._listener is not None
    m._reinitialize_after_fork()
    assert m._listener is None
    assert m._loggers == {}
    assert m._static_fields["pid"] == os.getpid()


def test_build_static_fields_suppression(monkeypatch):
    monkeypatch.setenv("HOSTNAME", "")  # suppressed
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.setenv("APP_NAME", "svc-x")
    fields = m._build_static_fields()
    assert "hostname" not in fields
    assert fields["environment"] == "prod"
    assert fields["version"] == "unknown"
    assert fields["service"] == "svc-x"
    assert fields["pid"] == os.getpid()


def test_build_static_fields_hostname_from_env(monkeypatch):
    monkeypatch.setenv("HOSTNAME", "myhost")
    assert m._build_static_fields()["hostname"] == "myhost"


def test_resolve_level(monkeypatch):
    assert m._resolve_level("debug") == logging.DEBUG
    assert m._resolve_level("WARNING") == logging.WARNING
    assert m._resolve_level("nonsense") == logging.INFO
