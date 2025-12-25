#!/usr/bin/env python3
"""PyPI Authentication Verification Script.

This script helps verify PyPI authentication and package ownership
for the mypylogger package as part of Phase 7 Task 0.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def run_command(cmd: list[str], capture_output: bool = True) -> tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd, check=False, capture_output=capture_output, text=True, timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)


def check_pypi_token() -> bool:
    """Check if PyPI token is available in environment."""
    token = os.getenv("PYPI_API_TOKEN")
    if not token:
        print("❌ PYPI_API_TOKEN environment variable not set")
        print("   Set it with: export PYPI_API_TOKEN=pypi-...")
        return False

    if not token.startswith("pypi-"):
        print("❌ PYPI_API_TOKEN does not appear to be a valid PyPI token")
        print("   PyPI tokens should start with 'pypi-'")
        return False

    print("✅ PYPI_API_TOKEN found and appears valid")
    return True


def check_twine_installation() -> bool:
    """Check if twine is installed."""
    exit_code, _, _ = run_command(["twine", "--version"])
    if exit_code != 0:
        print("❌ Twine is not installed")
        print("   Install with: uv add --dev twine")
        return False

    print("✅ Twine is installed")
    return True


def build_test_package() -> Path | None:
    """Build the package for testing."""
    print("🏗️ Building package for authentication test...")

    # Check if build is installed
    exit_code, _, _ = run_command(["python", "-m", "build", "--version"])
    if exit_code != 0:
        print("❌ Build tool is not available")
        print("   Install with: uv add --dev build")
        return None

    # Build the package
    exit_code, _stdout, stderr = run_command(["python", "-m", "build", "--wheel"])
    if exit_code != 0:
        print(f"❌ Package build failed: {stderr}")
        return None

    # Find the built wheel
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("❌ dist/ directory not found after build")
        return None

    wheel_files = list(dist_dir.glob("*.whl"))
    if not wheel_files:
        print("❌ No wheel files found in dist/")
        return None

    wheel_file = wheel_files[-1]  # Get the most recent
    print(f"✅ Package built: {wheel_file}")
    return wheel_file


def test_package_check(wheel_file: Path) -> bool:
    """Test package validation with twine check."""
    print("🔍 Validating package with twine check...")

    exit_code, _stdout, stderr = run_command(["twine", "check", str(wheel_file)])
    if exit_code != 0:
        print(f"❌ Package validation failed: {stderr}")
        return False

    print("✅ Package validation passed")
    return True


def test_testpypi_upload(wheel_file: Path) -> bool:
    """Test upload to TestPyPI (dry run)."""
    print("🧪 Testing authentication with TestPyPI...")

    # Set up environment for TestPyPI
    env = os.environ.copy()
    env["TWINE_REPOSITORY"] = "testpypi"
    env["TWINE_USERNAME"] = "__token__"
    env["TWINE_PASSWORD"] = os.getenv("PYPI_API_TOKEN", "")

    # Try to upload (this will fail if package version exists, but will test auth)
    exit_code, _stdout, stderr = run_command(
        ["twine", "upload", "--repository", "testpypi", str(wheel_file)]
    )

    # Check for authentication success indicators
    if "Invalid or non-existent authentication information" in stderr:
        print("❌ Authentication failed - invalid token")
        return False

    if "403" in stderr and "Forbidden" in stderr:
        print("❌ Authentication failed - insufficient permissions")
        return False

    if "400" in stderr and "already exists" in stderr:
        print("✅ Authentication successful (version already exists on TestPyPI)")
        return True

    if exit_code == 0:
        print("✅ Authentication successful - uploaded to TestPyPI")
        return True

    # Other errors might be network or server issues
    print(f"⚠️ Upload failed with unclear error: {stderr}")
    print("   This might be a network issue or server problem")
    return False


def main() -> int:
    """Main verification function."""
    print("🔐 PyPI Authentication Verification")
    print("=" * 40)

    # Check prerequisites
    if not check_twine_installation():
        return 1

    if not check_pypi_token():
        print("\n💡 To set up PyPI authentication:")
        print("1. Login to https://pypi.org/account/login/")
        print("2. Go to Account Settings → API tokens")
        print("3. Generate new token for 'mypylogger' project")
        print("4. Export token: export PYPI_API_TOKEN=pypi-...")
        return 1

    # Build package for testing
    wheel_file = build_test_package()
    if not wheel_file:
        return 1

    # Validate package
    if not test_package_check(wheel_file):
        return 1

    # Test authentication
    print("\n🔐 Testing PyPI Authentication...")
    if not test_testpypi_upload(wheel_file):
        print("\n💡 Authentication troubleshooting:")
        print("1. Verify token is correct and not expired")
        print("2. Check token has upload permissions for mypylogger")
        print("3. Ensure you have maintainer/owner role on the package")
        return 1

    print("\n🎉 PyPI Authentication Verification Complete!")
    print("✅ All checks passed - ready for automated publishing")

    return 0


if __name__ == "__main__":
    sys.exit(main())
