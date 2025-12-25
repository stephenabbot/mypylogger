#!/usr/bin/env python3
"""Test script for CI badge integration.

This script simulates the CI environment and tests badge update functionality.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def simulate_ci_environment() -> bool:
    """Simulate CI environment variables for testing."""
    print("🔧 Setting up CI environment simulation...")

    # Set CI environment variables
    os.environ["CI"] = "true"
    os.environ["GITHUB_ACTIONS"] = "true"
    os.environ["TESTS_PASSED"] = "true"
    os.environ["GITHUB_REPOSITORY"] = "stabbotco1/mypylogger"
    os.environ["PYPI_PACKAGE"] = "mypylogger"

    print("✅ CI environment variables set")
    return True


def test_badge_generation() -> bool:
    """Test badge generation in CI mode."""
    print("🧪 Testing badge generation...")

    try:
        # Test badge generation without README updates
        result = subprocess.run(
            ["uv", "run", "python", "-m", "badges", "--generate-only", "--no-status-detection"],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )

        print("✅ Badge generation test passed")
        print(f"Output: {result.stdout}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Badge generation test failed: {e}")
        print(f"Error output: {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Badge generation test timed out")
        return False


def test_ci_badge_update() -> bool:
    """Test CI-only badge update functionality."""
    print("🧪 Testing CI-only badge update...")

    try:
        # Test CI-only badge update (should work in simulated CI environment)
        # Use dry-run mode to avoid actual git operations in test
        result = subprocess.run(
            ["uv", "run", "python", "-m", "badges", "--dry-run", "--no-status-detection"],
            check=False,  # Don't fail on non-zero exit
            capture_output=True,
            text=True,
            timeout=30,  # Reduced timeout
        )

        # Check if the command ran without major errors
        if "Generated badge section:" in result.stdout or result.returncode == 0:
            print("✅ CI badge update test passed")
            print(f"Output: {result.stdout}")
            return True
        print(f"❌ CI badge update test failed with return code: {result.returncode}")
        print(f"Error output: {result.stderr}")
        return False

    except subprocess.TimeoutExpired:
        print("❌ CI badge update test timed out")
        return False


def test_local_restriction() -> bool:
    """Test that badge updates are restricted in local environment."""
    print("🧪 Testing local environment restriction...")

    # Clear CI environment variables
    ci_vars = ["CI", "GITHUB_ACTIONS", "TESTS_PASSED"]
    original_values = {}

    for var in ci_vars:
        original_values[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]

    try:
        # Test that badge update fails in local environment
        result = subprocess.run(
            ["uv", "run", "python", "-m", "badges", "--no-status-detection"],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Should fail or show restriction message
        if "only allowed in CI/CD environments" in result.stderr or result.returncode != 0:
            print("✅ Local restriction test passed")
            return True
        print("❌ Local restriction test failed - badge update should be restricted")
        return False

    except subprocess.TimeoutExpired:
        print("❌ Local restriction test timed out")
        return False
    finally:
        # Restore original environment variables
        for var, value in original_values.items():
            if value is not None:
                os.environ[var] = value


def main() -> int:
    """Main test function."""
    print("🚀 CI Badge Integration Test")
    print("=" * 40)

    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    tests = [
        ("CI Environment Simulation", simulate_ci_environment),
        ("Badge Generation", test_badge_generation),
        ("CI Badge Update", test_ci_badge_update),
        ("Local Restriction", test_local_restriction),
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
        print("🎉 All CI badge integration tests passed!")
        return 0
    print("❌ Some tests failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
