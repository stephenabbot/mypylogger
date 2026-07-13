"""Test helpers shared across modules."""

from __future__ import annotations

import logging


def make_record(
    level: int = logging.INFO,
    msg: str = "hi",
    **extra: object,
) -> logging.LogRecord:
    record = logging.LogRecord("app", level, "/path/app.py", 10, msg, (), None, func="main")
    for key, value in extra.items():
        setattr(record, key, value)
    return record
