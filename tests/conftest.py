"""Shared fixtures. Each test runs against an isolated logging pipeline."""

from __future__ import annotations

import pytest

import mypylogger as m


def _hard_reset() -> None:
    m._shutdown()
    with m._lock:
        m._listener = None
        m._queue = None
        m._queue_handler = None
        m._loggers = {}


@pytest.fixture(autouse=True)
def _isolate_pipeline():
    """Tear the pipeline down after every test to avoid handler/queue leakage."""
    yield
    _hard_reset()


@pytest.fixture
def fresh_pipeline():
    """Guarantee a pipeline built inside the test (e.g. under capsys)."""
    _hard_reset()
    yield
    _hard_reset()
