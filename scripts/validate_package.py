#!/usr/bin/env python3
"""Validate Python package before publishing.

This script performs comprehensive validation of the Python package
to ensure it meets quality standards before publishing to PyPI.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

# Constants
MIN_README_LENGTH = 100


class PackageValidator:
    """Validate Python package for publishing."""

    def __init__(self, package_dir: str = ".") -> None:
        """Initialize package validator.

        Args:
            package_dir: Directory containing the package
        """
        self.package_dir = Path(package_dir)
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def run_command(self, cmd: list[str], check: bool = True) -> subprocess.CompletedProcess | None:
        """Run a command and capture output.

        Args:
            cmd: Command to run
            check: Whether to raise exception on failure

        Returns:
            CompletedProcess result or None if failed
        """
        try:
            return subprocess.run(  # noqa: S603
                cmd, capture_output=True, text=True, cwd=self.package_dir, check=check
            )
        except subprocess.CalledProcessError as e:
            if check:
                self.errors.append(f"Command failed: {' '.join(cmd)}\n{e.stderr}")
            return None

    def validate_pyproject_toml(self) -> bool:
        """Validate pyproject.toml configuration.

        Returns:
            True if valid, False otherwise
        """
        pyproject_path = self.package_dir / "pyproject.toml"

        if not pyproject_path.exists():
            self.errors.append("pyproject.toml not found")
            return False

        if tomllib is None:
            self.errors.append("Cannot validate pyproject.toml: tomllib/tomli not available")
            return False

        try:
            with pyproject_path.open("rb") as f:
                data = tomllib.load(f)
        except Exception as e:
            self.errors.append(f"Invalid pyproject.toml: {e}")
            return False

        # Check required fields
        project = data.get("project", {})
        required_fields = ["name", "version", "description", "authors"]

        for field in required_fields:
            if field not in project:
                self.errors.append(f"Missing required field in pyproject.toml: project.{field}")

        # Check version format
        version = project.get("version", "")
        if not version or not version.replace(".", "").replace("-", "").replace("+", "").isalnum():
            self.errors.append(f"Invalid version format: {version}")

        # Check classifiers
        classifiers = project.get("classifiers", [])
        if not classifiers:
            self.warnings.append("No classifiers specified in pyproject.toml")

        # Check URLs
        urls = project.get("urls", {})
        if not urls:
            self.warnings.append("No project URLs specified in pyproject.toml")

        return len(self.errors) == 0

    def validate_readme(self) -> bool:
        """Validate README file.

        Returns:
            True if valid, False otherwise
        """
        readme_path = self.package_dir / "README.md"

        if not readme_path.exists():
            self.errors.append("README.md not found")
            return False

        try:
            content = readme_path.read_text()
            if len(content.strip()) < MIN_README_LENGTH:
                self.warnings.append("README.md is very short (< 100 characters)")

            # Check for basic sections
            content_lower = content.lower()
            expected_sections = ["installation", "usage", "example"]
            missing_sections = [s for s in expected_sections if s not in content_lower]

            if missing_sections:
                self.warnings.append(f"README.md missing sections: {', '.join(missing_sections)}")

        except Exception as e:
            self.errors.append(f"Error reading README.md: {e}")
            return False

        return True

    def validate_changelog(self) -> bool:
        """Validate CHANGELOG file.

        Returns:
            True if valid, False otherwise
        """
        changelog_path = self.package_dir / "CHANGELOG.md"

        if not changelog_path.exists():
            self.warnings.append("CHANGELOG.md not found")
            return True  # Not required, just a warning

        try:
            content = changelog_path.read_text()
            if "## [Unreleased]" not in content:
                self.warnings.append("CHANGELOG.md missing [Unreleased] section")

        except Exception as e:
            self.warnings.append(f"Error reading CHANGELOG.md: {e}")

        return True

    def validate_license(self) -> bool:
        """Validate license information.

        Returns:
            True if valid, False otherwise
        """
        license_path = self.package_dir / "LICENSE"

        if not license_path.exists():
            self.warnings.append("LICENSE file not found")

        # Check if license is specified in pyproject.toml
        if tomllib is not None:
            try:
                with (self.package_dir / "pyproject.toml").open("rb") as f:
                    data = tomllib.load(f)

                project = data.get("project", {})
                if "license" not in project:
                    self.warnings.append("No license specified in pyproject.toml")

            except Exception:
                pass

        return True

    def validate_source_code(self) -> bool:
        """Validate source code structure.

        Returns:
            True if valid, False otherwise
        """
        src_dir = self.package_dir / "src"

        if not src_dir.exists():
            self.errors.append("src/ directory not found")
            return False

        # Find package directories
        package_dirs = [d for d in src_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]

        if not package_dirs:
            self.errors.append("No package directories found in src/")
            return False

        # Check for __init__.py files
        for pkg_dir in package_dirs:
            init_file = pkg_dir / "__init__.py"
            if not init_file.exists():
                self.errors.append(f"Missing __init__.py in {pkg_dir}")

        return len(self.errors) == 0

    def validate_tests(self) -> bool:
        """Validate test structure.

        Returns:
            True if valid, False otherwise
        """
        tests_dir = self.package_dir / "tests"

        if not tests_dir.exists():
            self.warnings.append("tests/ directory not found")
            return True

        # Check for test files
        test_files = list(tests_dir.rglob("test_*.py"))

        if not test_files:
            self.warnings.append("No test files found in tests/")

        return True

    def validate_build_system(self) -> bool:
        """Validate build system configuration.

        Returns:
            True if valid, False otherwise
        """
        # Check if build system is properly configured in pyproject.toml
        if tomllib is None:
            self.warnings.append("Cannot validate build system: tomllib/tomli not available")
            return True

        try:
            with (self.package_dir / "pyproject.toml").open("rb") as f:
                data = tomllib.load(f)

            build_system = data.get("build-system", {})
            if not build_system:
                self.errors.append("No build-system configuration in pyproject.toml")
                return False

            if "requires" not in build_system:
                self.errors.append("Missing 'requires' in build-system configuration")
                return False

            if "build-backend" not in build_system:
                self.errors.append("Missing 'build-backend' in build-system configuration")
                return False

        except Exception as e:
            self.errors.append(f"Error validating build system: {e}")
            return False

        return True

    def validate_package_contents(self) -> bool:
        """Validate built package contents.

        Returns:
            True if valid, False otherwise
        """
        # Build package in temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_command(["uv", "build", "--out-dir", temp_dir], check=False)

            if result is None or result.returncode != 0:
                self.errors.append("Failed to build package for validation")
                return False

            # Check built files
            temp_path = Path(temp_dir)
            wheel_files = list(temp_path.glob("*.whl"))
            sdist_files = list(temp_path.glob("*.tar.gz"))

            if not wheel_files:
                self.errors.append("No wheel file generated")

            if not sdist_files:
                self.errors.append("No source distribution generated")

            # Validate with twine
            all_files = wheel_files + sdist_files
            if all_files:
                result = self.run_command(
                    ["uv", "run", "twine", "check", *[str(f) for f in all_files]], check=False
                )

                if result is None or result.returncode != 0:
                    self.errors.append("Package validation failed with twine check")
                    if result and result.stderr:
                        self.errors.append(f"Twine errors: {result.stderr}")

        return len(self.errors) == 0

    def run_all_validations(self) -> bool:
        """Run all package validations.

        Returns:
            True if all validations pass, False otherwise
        """
        validations = [
            ("pyproject.toml", self.validate_pyproject_toml),
            ("README", self.validate_readme),
            ("CHANGELOG", self.validate_changelog),
            ("License", self.validate_license),
            ("Source code", self.validate_source_code),
            ("Tests", self.validate_tests),
            ("Build system", self.validate_build_system),
            ("Package contents", self.validate_package_contents),
        ]

        print("Running package validation...")
        print("=" * 50)

        all_passed = True

        for name, validation_func in validations:
            print(f"Validating {name}...", end=" ")

            try:
                if validation_func():
                    print("✓ PASS")
                else:
                    print("✗ FAIL")
                    all_passed = False
            except Exception as e:
                print(f"✗ ERROR: {e}")
                self.errors.append(f"{name} validation error: {e}")
                all_passed = False

        # Print summary
        print("\n" + "=" * 50)
        print("VALIDATION SUMMARY")
        print("=" * 50)

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
            print("✅ All validations passed! Package is ready for publishing.")
        else:
            print("❌ Package validation failed. Please fix errors before publishing.")

        return all_passed and not self.errors


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate Python package for publishing")
    parser.add_argument(
        "--package-dir",
        default=".",
        help="Directory containing the package (default: current directory)",
    )

    args = parser.parse_args()

    validator = PackageValidator(args.package_dir)
    success = validator.run_all_validations()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
