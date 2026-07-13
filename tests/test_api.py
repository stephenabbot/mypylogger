"""Public API: name resolution, caching, propagation, bind/clear, static fields."""

from __future__ import annotations

import contextvars
import logging

import mypylogger as m


def test_name_resolution(monkeypatch):
    monkeypatch.delenv("APP_NAME", raising=False)
    assert m._resolve_name(None) == "mypylogger"
    assert m._resolve_name("") == "mypylogger"
    assert m._resolve_name("explicit") == "explicit"
    monkeypatch.setenv("APP_NAME", "from-env")
    assert m._resolve_name(None) == "from-env"
    assert m._resolve_name("") == "from-env"
    assert m._resolve_name("explicit") == "explicit"


def test_get_logger_caches_same_object():
    first = m.get_logger("cache-svc")
    second = m.get_logger("cache-svc")
    assert first is second


def test_get_logger_no_handler_duplication():
    logger = m.get_logger("dup-svc")
    m.get_logger("dup-svc")
    m.get_logger("dup-svc")
    assert len(logger.handlers) == 1


def test_logger_does_not_propagate():
    assert m.get_logger("prop-svc").propagate is False


def test_get_logger_returns_logger():
    assert isinstance(m.get_logger("type-svc"), logging.Logger)


def test_static_fields_registered_via_get_logger():
    m.get_logger("static-svc", static_fields={"region": "us-east"})
    assert m._static_fields["region"] == "us-east"


def test_bind_and_clear():
    m.clear_bindings()
    m.bind(a=1)
    m.bind(b=2)
    assert m._context_fields.get() == {"a": 1, "b": 2}
    m.clear_bindings()
    assert m._context_fields.get() == {}


def test_bind_is_context_isolated():
    m.clear_bindings()
    m.bind(outer=1)

    def inner() -> set[str]:
        m.bind(inner=2)
        return set(m._context_fields.get())

    result = contextvars.copy_context().run(inner)
    assert result == {"outer", "inner"}
    # The child context's binding must not leak back to the parent.
    assert m._context_fields.get() == {"outer": 1}
    m.clear_bindings()
