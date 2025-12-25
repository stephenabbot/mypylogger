"""Placeholder test to verify pytest configuration."""

from __future__ import annotations

from typing import Any


def test_placeholder() -> None:
    """Placeholder test to ensure pytest configuration works."""
    assert True


def test_with_fixture(sample_log_data: dict[str, Any]) -> None:
    """Test using shared fixture from conftest.py."""
    assert sample_log_data["message"] == "Test log message"
    assert sample_log_data["level"] == "INFO"
