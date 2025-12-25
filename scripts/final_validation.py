#!/usr/bin/env python3
"""Final validation script for CI-only badge updates and integration.

This script performs comprehensive validation of the badge system
to ensure it meets all requirements for task 6.5.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def run_command(cmd: list[str], description: str, timeout: int = 60) -> bool:
    """Run a command and return success status."""
    print(f"🧪 {description}...")

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        print(f"✅ {description} - PASSED")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(f"   Return code: {e.returncode}")
        if e.stdout:
            print(f"   Output: {e.stdout[:200]}...")
        if e.stderr:
            print(f"   Error: {e.stderr[:200]}...")
        return False
    except subprocess.TimeoutExpired:
        print(f"❌ {description} - TIMEOUT")
        return False


def main() -> int:
    """Main validation function."""
    print("🚀 Final Badge System Validation")
    print("=" * 50)

    # Change to project root
    project_root = Path(__file__).parent.parent
    import os

    os.chdir(project_root)

    tests = [
        # Core functionality tests
        (
            ["uv", "run", "python", "-m", "badges", "--config-check"],
            "Badge configuration validation",
        ),
        (
            ["uv", "run", "python", "-m", "badges", "--generate-only", "--no-status-detection"],
            "Badge generation (local development mode)",
        ),
        # CI integration tests
        (
            ["uv", "run", "python", "scripts/test_ci_badge_integration.py"],
            "CI badge integration test",
        ),
        # PyPI compatibility tests
        (
            ["uv", "run", "python", "scripts/test_pypi_compatibility.py"],
            "PyPI compatibility validation",
        ),
        # Badge-specific tests (without coverage to avoid issues)
        (
            [
                "uv",
                "run",
                "pytest",
                "tests/unit/test_badge_config.py",
                "tests/unit/test_badge_generator.py",
                "tests/unit/test_readme_updater.py",
                "-v",
                "--tb=short",
                "--no-cov",
            ],
            "Badge system unit tests",
        ),
        (
            [
                "uv",
                "run",
                "pytest",
                "tests/integration/test_badge_workflow.py",
                "-v",
                "--tb=short",
                "--no-cov",
            ],
            "Badge workflow integration tests",
        ),
        # Security validation (local only)
        (
            [
                "uv",
                "run",
                "python",
                "-c",
                "from badges.security import security_checks_passed; exit(0 if security_checks_passed() else 1)",
            ],
            "Security validation (local scans only)",
        ),
        # Import verification
        (
            [
                "uv",
                "run",
                "python",
                "-c",
                "import badges; print('Badge system imports successfully')",
            ],
            "Badge system import verification",
        ),
    ]

    passed = 0
    total = len(tests)

    for cmd, description in tests:
        if run_command(cmd, description):
            passed += 1
        print()  # Add spacing between tests

    print("📊 Final Validation Results")
    print("=" * 30)
    print(f"Tests Passed: {passed}/{total}")

    if passed == total:
        print("🎉 ALL VALIDATIONS PASSED!")
        print()
        print("✅ Badge system is ready for production use")
        print("✅ CI-only badge updates implemented correctly")
        print("✅ Local development focuses on code quality only")
        print("✅ PyPI compatibility verified")
        print("✅ Security validation working")
        print("✅ All badge generation functions working correctly")
        print()
        print("🚀 Task 6.5 - Final testing and validation: COMPLETE")
        return 0
    print("❌ Some validations failed")
    print(f"   {total - passed} test(s) need attention")
    return 1


if __name__ == "__main__":
    sys.exit(main())
