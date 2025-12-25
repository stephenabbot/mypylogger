#!/usr/bin/env python3
"""Test script for PyPI compatibility verification.

This script tests badge functionality with PyPI package structure
and verifies badges work correctly after package publication.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import urllib.request


def test_package_structure() -> bool:
    """Test that badge system works with PyPI package structure."""
    print("🧪 Testing PyPI package structure compatibility...")

    # Check that required files exist
    required_files = [
        "pyproject.toml",
        "README.md",
        "src/mypylogger/__init__.py",
        "badges/__init__.py",
    ]

    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)

    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        return False

    print("✅ Package structure is compatible with PyPI")
    return True


def test_pypi_badge_urls() -> bool:
    """Test that PyPI-related badge URLs are correctly formatted."""
    print("🧪 Testing PyPI badge URL generation...")

    try:
        # Test badge generation via command line
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-c",
                "from badges.generator import generate_pypi_version_badge, generate_downloads_badge, generate_python_versions_badge; "
                "print('pypi_version:', generate_pypi_version_badge()); "
                "print('downloads:', generate_downloads_badge()); "
                "print('python_versions:', generate_python_versions_badge())",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )

        output = result.stdout

        # Check PyPI version badge URL
        if "pypi/v/mypylogger" not in output:
            print(f"❌ PyPI version badge URL not found in output: {output}")
            return False

        # Check downloads badge URL
        if "pypi/dm/" not in output:
            print(f"❌ Downloads badge URL not found in output: {output}")
            return False

        # Check Python versions badge URL
        if "pypi/pyversions/mypylogger" not in output:
            print(f"❌ Python versions badge URL not found in output: {output}")
            return False

        print("✅ PyPI badge URLs are correctly formatted")
        return True

    except Exception as e:
        print(f"❌ Failed to generate PyPI badge URLs: {e}")
        return False


def test_shields_io_connectivity() -> bool:
    """Test connectivity to shields.io service."""
    print("🧪 Testing shields.io connectivity...")

    try:
        # Test a simple shields.io badge
        test_url = "https://img.shields.io/badge/test-passing-green"

        request = urllib.request.Request(test_url)
        request.add_header("User-Agent", "mypylogger-badge-test/1.0")

        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status == 200:
                print("✅ shields.io connectivity working")
                return True
            print(f"❌ shields.io returned status: {response.status}")
            return False

    except Exception as e:
        print(f"❌ shields.io connectivity failed: {e}")
        return False


def test_pyproject_toml_compatibility() -> bool:
    """Test that pyproject.toml is compatible with badge generation."""
    print("🧪 Testing pyproject.toml compatibility...")

    try:
        # Read pyproject.toml
        pyproject_path = Path("pyproject.toml")
        if not pyproject_path.exists():
            print("❌ pyproject.toml not found")
            return False

        content = pyproject_path.read_text()

        # Check for required fields (more flexible matching)
        required_fields = [
            ("name", "mypylogger"),
            ("version", "0.2."),  # Version should start with 0.2.
            ("description", "logging"),  # Should contain logging
            ("requires-python", ">=3.8"),  # Should specify Python version
        ]

        missing_fields = []
        for field, expected_content in required_fields:
            if field not in content or expected_content not in content:
                missing_fields.append(field)

        if missing_fields:
            print(f"❌ Missing required pyproject.toml fields: {missing_fields}")
            return False

        print("✅ pyproject.toml is compatible with badge generation")
        return True

    except Exception as e:
        print(f"❌ Failed to read pyproject.toml: {e}")
        return False


def test_readme_badge_integration() -> bool:
    """Test that README.md can be updated with badges."""
    print("🧪 Testing README badge integration...")

    try:
        # Read current README
        readme_path = Path("README.md")
        if not readme_path.exists():
            print("❌ README.md not found")
            return False

        original_content = readme_path.read_text()

        # Test badge section detection via command line
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-c",
                f"from badges.updater import find_badge_section; "
                f"content = '''{original_content}'''; "
                f"start, end = find_badge_section(content); "
                f"print(f'positions: {{start}}, {{end}}')",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )

        output = result.stdout

        # Should find valid positions (non-negative)
        if "positions:" not in output:
            print("❌ Could not get badge section positions")
            return False

        print("✅ README badge integration working")
        return True

    except Exception as e:
        print(f"❌ README badge integration failed: {e}")
        return False


def test_badge_generation_without_pypi() -> bool:
    """Test badge generation works even when package isn't published to PyPI."""
    print("🧪 Testing badge generation without PyPI publication...")

    try:
        # Generate badges in development mode
        result = subprocess.run(
            ["uv", "run", "python", "-m", "badges", "--generate-only", "--no-status-detection"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # If command succeeded (return code 0), consider it a pass
        if result.returncode == 0:
            print("✅ Badge generation works without PyPI publication")
            return True
        print("❌ Badge generation failed in development mode")
        print(f"Return code: {result.returncode}")
        print(f"Output: {result.stdout}")
        print(f"Error: {result.stderr}")
        return False

    except subprocess.CalledProcessError as e:
        print(f"❌ Badge generation failed: {e}")
        print(f"Error output: {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Badge generation timed out")
        return False


def test_configuration_validation() -> bool:
    """Test badge configuration validation."""
    print("🧪 Testing badge configuration validation...")

    try:
        # Test configuration check
        result = subprocess.run(
            ["uv", "run", "python", "-m", "badges", "--config-check"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )

        print("✅ Badge configuration validation passed")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Badge configuration validation failed: {e}")
        print(f"Error output: {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Configuration validation timed out")
        return False


def main() -> int:
    """Main test function."""
    print("🚀 PyPI Compatibility Test")
    print("=" * 40)

    # Change to project root
    project_root = Path(__file__).parent.parent
    original_cwd = Path.cwd()

    try:
        import os

        os.chdir(project_root)

        tests = [
            ("Package Structure", test_package_structure),
            ("PyPI Badge URLs", test_pypi_badge_urls),
            ("shields.io Connectivity", test_shields_io_connectivity),
            ("pyproject.toml Compatibility", test_pyproject_toml_compatibility),
            ("README Badge Integration", test_readme_badge_integration),
            ("Badge Generation (Development)", test_badge_generation_without_pypi),
            ("Configuration Validation", test_configuration_validation),
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            print(f"\n📋 Running: {test_name}")
            print("-" * 30)

            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} failed")

        print(f"\n📊 Test Results: {passed}/{total} passed")

        if passed == total:
            print("🎉 All PyPI compatibility tests passed!")
            print("\n✅ Badge system is ready for PyPI publication")
            return 0
        print("❌ Some compatibility tests failed")
        return 1

    finally:
        os.chdir(original_cwd)


if __name__ == "__main__":
    sys.exit(main())
