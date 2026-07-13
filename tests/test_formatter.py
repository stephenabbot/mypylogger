"""Formatter behavior: field order, timestamp, error object, static/context/extra."""

from __future__ import annotations

import json
import logging
import sys

import mypylogger as m
from tests.helpers import make_record


def test_timestamp_is_utc_microsecond_z(monkeypatch):
    monkeypatch.setattr(m, "_static_fields", {})
    record = make_record()
    record.created = 1_720_000_000.123456
    obj = json.loads(m._formatter.format(record))
    ts = obj["timestamp"]
    assert ts.endswith("Z")
    assert "+00:00" not in ts
    fractional = ts.split(".")[1].rstrip("Z")
    assert len(fractional) == 6


def test_base_field_order(monkeypatch):
    monkeypatch.setattr(m, "_static_fields", {})
    obj = json.loads(m._formatter.format(make_record()))
    assert list(obj) == [
        "timestamp",
        "level",
        "message",
        "module",
        "filename",
        "function_name",
        "line",
    ]


def test_full_field_order_static_context_extra_error(monkeypatch):
    monkeypatch.setattr(m, "_static_fields", {"hostname": "h", "pid": 1})
    record = make_record(level=logging.ERROR, msg="failed", user_field="x")
    record.__dict__["_mypylogger_context"] = {"req": "r1"}
    try:
        raise ValueError("boom")
    except ValueError:
        record.exc_info = sys.exc_info()
    obj = json.loads(m._formatter.format(record))
    assert list(obj) == [
        "timestamp",
        "level",
        "message",
        "module",
        "filename",
        "function_name",
        "line",
        "hostname",
        "pid",
        "req",
        "user_field",
        "error",
    ]


def test_error_object_structure(monkeypatch):
    monkeypatch.setattr(m, "_static_fields", {})
    record = make_record(level=logging.ERROR, msg="caller message")
    try:
        _ = 1 / 0
    except ZeroDivisionError:
        record.exc_info = sys.exc_info()
    line = m._formatter.format(record)
    obj = json.loads(line)
    err = obj["error"]
    assert err["type"] == "ZeroDivisionError"
    assert err["message"] == "division by zero"
    assert "Traceback" in err["stack_trace"]
    assert "\\n" in err["stack_trace"]  # newlines escaped to literal backslash-n
    assert obj["message"] == "caller message"  # message untouched
    assert "\n" not in line  # single JSON line, no raw newline
    assert "exc_info" not in obj
    assert "exc_text" not in obj


def test_static_fields_applied(monkeypatch):
    monkeypatch.setattr(m, "_static_fields", {"hostname": "H", "pid": 99, "service": "svc"})
    obj = json.loads(m._formatter.format(make_record()))
    assert obj["hostname"] == "H"
    assert obj["pid"] == 99
    assert obj["service"] == "svc"


def test_non_serializable_extra_rendered_as_str(monkeypatch):
    monkeypatch.setattr(m, "_static_fields", {})

    class Thing:
        def __str__(self) -> str:
            return "THING"

    obj = json.loads(m._formatter.format(make_record(thing=Thing())))
    assert obj["thing"] == "THING"


def test_context_before_extra(monkeypatch):
    monkeypatch.setattr(m, "_static_fields", {})
    record = make_record(extra_key="e")
    record.__dict__["_mypylogger_context"] = {"ctx_key": "c"}
    obj = json.loads(m._formatter.format(record))
    keys = list(obj)
    assert keys.index("ctx_key") < keys.index("extra_key")
