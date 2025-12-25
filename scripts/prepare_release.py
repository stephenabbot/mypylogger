#!/usr/bin/env python3
"""Prepare for release by running all pre-release checks.

This script runs comprehensive checks to ensure the package is ready
for release, including tests, validation, and documentation checks.
"""

from __future__ import annotations

import subprocess
import sys


class ReleasePreparation:
    """Prepare package for release."""

    def __init__(self) -> None:
        """Initialize release preparation."""
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def run_command(self, cmd: list[str], description: str) -> bool:
        """Run a command and report results.

        Args:
            cmd: Command to run
            description: Description of what the command does

        Returns:
            True if successful, False otherwise
        """
        print(f"Running {description}...", end=" ")

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            print("✓ PASS")
            return True
        except subprocess.CalledProcessError as e:
            print("✗ FAIL")
            self.errors.append(f"{description} failed: {e.stderr.strip()}")
            return False

    def check_git_status(self) -> bool:
        """Check Git repository status.

        Returns:
            True if repository is clean, False otherwise
        """
        print("Checking Git status...", end=" ")

        try:
            # Check for uncommitted changes
            result = subprocess.run(
                ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
            )

            if result.stdout.strip():
                print("✗ FAIL")
                self.errors.append("Repository has uncommitted changes")
                return False

            # Check if we're on main branch
            result = subprocess.run(
                ["git", "branch", "--show-current"], capture_output=True, text=True, check=True
            )

            current_branch = result.stdout.strip()
            if current_branch != "main":
                print("⚠ WARNING")
                self.warnings.append(f"Not on main branch (currently on {current_branch})")
            else:
                print("✓ PASS")

            return True

        except subprocess.CalledProcessError as e:
            print("✗ FAIL")
            self.errors.append(f"Git status check failed: {e}")
            return False

    def run_tests(self) -> bool:
        """Run the complete test suite.

        Returns:
            True if all tests pass, False otherwise
        """
        return self.run_command(["./scripts/run_tests.sh"], "complete test suite")

    def validate_package(self) -> bool:
        """Validate package for publishing.

        Returns:
            True if package is valid, False otherwise
        """
        return self.run_command(
            ["uv", "run", "python", "scripts/validate_package.py"], "package validation"
        )

    def check_documentation(self) -> bool:
        """Check documentation build.

        Returns:
            True if documentation builds successfully, False otherwise
        """
        return self.run_command(
            ["uv", "run", "python", "scripts/validate_documentation.py"], "documentation validation"
        )

    def check_security(self) -> bool:
        """Run security checks.

        Returns:
            True if no security issues found, False otherwise
        """
        return self.run_command(["./scripts/security_check.sh"], "security scan")

    def build_package(self) -> bool:
        """Build the package to verify it can be built.

        Returns:
            True if package builds successfully, False otherwise
        """
        return self.run_command(["uv", "build"], "package build")

    def run_all_checks(self) -> bool:
        """Run all pre-release checks.

        Returns:
            True if all checks pass, False otherwise
        """
        print("Preparing for release...")
        print("=" * 60)

        checks = [
            ("Git status", self.check_git_status),
            ("Test suite", self.run_tests),
            ("Package validation", self.validate_package),
            ("Documentation", self.check_documentation),
            ("Security scan", self.check_security),
            ("Package build", self.build_package),
        ]

        all_passed = True

        for name, check_func in checks:
            try:
                if not check_func():
                    all_passed = False
            except Exception as e:
                print(f"✗ ERROR: {e}")
                self.errors.append(f"{name} check error: {e}")
                all_passed = False

        # Print summary
        print("\n" + "=" * 60)
        print("RELEASE PREPARATION SUMMARY")
        print("=" * 60)

        if self.errors:
            print(f"❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  • {error}")
            print()

        if self.warnings:
            print(f"⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  • {warning}")
            print()

        if all_passed and not self.errors:
            print("✅ All checks passed! Ready for release.")
            print("\nNext steps:")
            print("1. Run the release workflow: gh workflow run release.yml")
            print("2. Or use the GitHub Actions UI to trigger a release")
            print("3. Choose the appropriate version bump (patch/minor/major)")
        else:
            print("❌ Release preparation failed. Please fix errors before releasing.")

        return all_passed and not self.errors


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Prepare package for release")
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running the test suite (faster, but less thorough)",
    )

    args = parser.parse_args()

    preparation = ReleasePreparation()

    # Skip tests if requested
    if args.skip_tests:
        preparation.run_tests = lambda: True

    success = preparation.run_all_checks()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
