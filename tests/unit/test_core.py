"""Unit tests for core mypylogger functionality."""

import inspect
from pathlib import Path

import mypylogger
from mypylogger import __version__, get_version


def test_version_available() -> None:
    """Test that version information is available."""
    assert __version__ == "0.2.8"
    assert get_version() == "0.2.8"


def test_package_imports() -> None:
    """Test that the package can be imported successfully."""
    assert hasattr(mypylogger, "__version__")
    assert hasattr(mypylogger, "get_version")


def test_get_version_returns_string() -> None:
    """Test that get_version returns a string."""
    version = get_version()
    assert isinstance(version, str)
    assert len(version) > 0


def test_version_format() -> None:
    """Test that version follows semantic versioning format."""
    parts = __version__.split(".")
    assert len(parts) == 3
    for part in parts:
        assert part.isdigit()


def test_get_version_function_signature() -> None:
    """Test that get_version function has correct signature."""
    sig = inspect.signature(get_version)
    assert len(sig.parameters) == 0
    assert sig.return_annotation in (str, "str")


def test_module_docstring() -> None:
    """Test that the module has a proper docstring."""
    assert mypylogger.__doc__ is not None
    assert "mypylogger v0.2.8" in mypylogger.__doc__
    assert "JSON logging" in mypylogger.__doc__


def test_get_version_consistency() -> None:
    """Test that get_version() returns the same value as __version__."""
    assert get_version() == __version__


def test_version_is_string_literal() -> None:
    """Test that __version__ is a string literal."""
    assert isinstance(__version__, str)
    assert __version__ == "0.2.8"


def test_package_structure() -> None:
    """Test that package has expected structure."""
    # Test that __file__ exists and points to __init__.py
    assert hasattr(mypylogger, "__file__")
    assert mypylogger.__file__.endswith("__init__.py")
    assert Path(mypylogger.__file__).exists()
