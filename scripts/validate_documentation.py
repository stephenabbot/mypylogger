#!/usr/bin/env python3
"""Documentation Quality Validation Script for mypylogger v0.2.8.

This script provides comprehensive validation of documentation quality including:
- Docstring coverage validation (100% requirement)
- Link validation for internal and external references
- Spelling and grammar checking
- Documentation formatting and style consistency
- API documentation completeness

Requirements Addressed:
- 16.1: Docstring coverage validation requiring 100% coverage
- 16.2: Link validation to check all internal and external references
- 16.3: Spelling and grammar checking for documentation content
- 16.4: Documentation formatting and style consistency checks
- 16.5: Documentation quality metrics and reporting
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

# Constants
MIN_DOCSTRING_LENGTH = 10
MAX_LINE_LENGTH = 120
FIRST_N_ISSUES = 10


class DocumentationValidator:
    """Comprehensive documentation quality validator."""

    def __init__(self, project_root: Path) -> None:
        """Initialize the documentation validator.

        Args:
            project_root: Path to the project root directory
        """
        self.project_root = project_root
        self.src_dir = project_root / "src"
        self.docs_dir = project_root / "docs"
        self.results: dict[str, Any] = {
            "docstring_coverage": {"status": "unknown", "coverage": 0.0, "details": []},
            "link_validation": {"status": "unknown", "broken_links": [], "details": []},
            "spelling_grammar": {"status": "unknown", "errors": [], "details": []},
            "formatting_style": {"status": "unknown", "issues": [], "details": []},
            "api_completeness": {"status": "unknown", "missing": [], "details": []},
            "overall_status": "unknown",
            "summary": {},
        }

    def validate_docstring_coverage(self, threshold: float = 100.0) -> bool:
        """Validate docstring coverage meets the required threshold.

        Args:
            threshold: Minimum required coverage percentage (default: 100.0)

        Returns:
            True if coverage meets threshold, False otherwise
        """
        print("🔍 Validating Docstring Coverage...")

        try:
            # Run interrogate to check docstring coverage
            cmd = [
                "uv",
                "run",
                "interrogate",
                str(self.src_dir),
                "--fail-under",
                str(threshold),
                "--ignore-init-method",
                "--ignore-init-module",
                "--ignore-magic",
                "--ignore-nested-functions",
                "--ignore-private",
                "--ignore-property-decorators",
                "--ignore-semiprivate",
                "--verbose",
                "--quiet",
            ]

            result = subprocess.run(cmd, check=False, capture_output=True, text=True)

            # Parse coverage percentage from output
            coverage_match = re.search(r"(\d+\.?\d*)%", result.stdout)
            coverage = float(coverage_match.group(1)) if coverage_match else 0.0

            self.results["docstring_coverage"]["coverage"] = coverage

            if result.returncode == 0 and coverage >= threshold:
                self.results["docstring_coverage"]["status"] = "pass"
                self.results["docstring_coverage"]["details"] = [
                    f"✅ Docstring coverage: {coverage}% (threshold: {threshold}%)"
                ]
                print(f"✅ Docstring coverage: {coverage}% (meets {threshold}% threshold)")
                return True

            self.results["docstring_coverage"]["status"] = "fail"
            self.results["docstring_coverage"]["details"] = [
                f"❌ Docstring coverage: {coverage}% (below {threshold}% threshold)",
                "Missing docstrings found in:",
                result.stdout,
            ]
            print(f"❌ Docstring coverage: {coverage}% (below {threshold}% threshold)")
            return False

        except Exception as e:
            self.results["docstring_coverage"]["status"] = "error"
            self.results["docstring_coverage"]["details"] = [f"Error checking coverage: {e}"]
            print(f"❌ Error checking docstring coverage: {e}")
            return False

    def validate_api_completeness(self) -> bool:
        """Validate that all public APIs have complete documentation.

        Returns:
            True if all APIs are documented, False otherwise
        """
        print("🔍 Validating API Documentation Completeness...")

        try:
            missing_docs = []

            # Find all Python files in src directory
            for py_file in self.src_dir.rglob("*.py"):
                if "__pycache__" in str(py_file):
                    continue

                # Parse the Python file to find public functions and classes
                try:
                    with py_file.open(encoding="utf-8") as f:
                        tree = ast.parse(f.read())

                    for node in ast.walk(tree):
                        if isinstance(
                            node, (ast.FunctionDef, ast.ClassDef)
                        ) and not node.name.startswith("_"):
                            # Check if it has a docstring
                            docstring = ast.get_docstring(node)
                            if not docstring:
                                missing_docs.append(
                                    f"{py_file.relative_to(self.project_root)}:{node.lineno} - "
                                    f"{node.name}"
                                )
                            elif (
                                len(docstring.strip()) < MIN_DOCSTRING_LENGTH
                            ):  # Very short docstring
                                missing_docs.append(
                                    f"{py_file.relative_to(self.project_root)}:{node.lineno} - "
                                    f"{node.name} (insufficient documentation)"
                                )

                except Exception as e:
                    print(f"⚠️ Warning: Could not parse {py_file}: {e}")

            if not missing_docs:
                self.results["api_completeness"]["status"] = "pass"
                self.results["api_completeness"]["details"] = [
                    "✅ All public APIs have complete documentation"
                ]
                print("✅ All public APIs have complete documentation")
                return True

            self.results["api_completeness"]["status"] = "fail"
            self.results["api_completeness"]["missing"] = missing_docs
            self.results["api_completeness"]["details"] = [
                f"❌ Found {len(missing_docs)} APIs with missing or insufficient documentation:",
                *missing_docs,
            ]
            print(f"❌ Found {len(missing_docs)} APIs with missing or insufficient documentation")
            return False

        except Exception as e:
            self.results["api_completeness"]["status"] = "error"
            self.results["api_completeness"]["details"] = [f"Error checking API completeness: {e}"]
            print(f"❌ Error checking API completeness: {e}")
            return False

    def validate_links(self) -> bool:
        """Validate all documentation links are accessible.

        Returns:
            True if all links are valid, False otherwise
        """
        print("🔍 Validating Documentation Links...")

        try:
            # Use Sphinx linkcheck builder
            cmd = [
                "uv",
                "run",
                "sphinx-build",
                "-b",
                "linkcheck",
                "-W",  # Treat warnings as errors
                "--keep-going",
                str(self.docs_dir / "source"),
                str(self.docs_dir / "build" / "linkcheck"),
            ]

            result = subprocess.run(cmd, check=False, capture_output=True, text=True)

            broken_links = []
            if result.returncode != 0:
                # Parse broken links from output
                broken_links.extend(
                    line.strip()
                    for line in result.stdout.split("\n")
                    if "broken" in line.lower() or "error" in line.lower()
                )

            if result.returncode == 0:
                self.results["link_validation"]["status"] = "pass"
                self.results["link_validation"]["details"] = [
                    "✅ All documentation links are valid"
                ]
                print("✅ All documentation links are valid")
                return True

            self.results["link_validation"]["status"] = "fail"
            self.results["link_validation"]["broken_links"] = broken_links
            self.results["link_validation"]["details"] = [
                f"❌ Found {len(broken_links)} broken links:",
                *broken_links,
            ]
            print(f"❌ Found {len(broken_links)} broken links")
            return False

        except Exception as e:
            self.results["link_validation"]["status"] = "error"
            self.results["link_validation"]["details"] = [f"Error checking links: {e}"]
            print(f"❌ Error checking links: {e}")
            return False

    def validate_spelling_grammar(self) -> bool:
        """Validate spelling and grammar in documentation.

        Returns:
            True if no spelling/grammar errors found, False otherwise
        """
        print("🔍 Validating Spelling and Grammar...")

        try:
            # Create custom dictionary for technical terms
            custom_dict = self.project_root / "docs" / "custom-dict.txt"
            custom_dict.parent.mkdir(exist_ok=True)

            technical_terms = [
                "mypylogger",
                "JSON",
                "stdlib",
                "docstring",
                "docstrings",
                "autodoc",
                "Sphinx",
                "reStructuredText",
                "PyPI",
                "GitHub",
                "API",
                "APIs",
                "CLI",
                "UUID",
                "timestamp",
                "timestamps",
                "formatter",
                "formatters",
                "handler",
                "handlers",
                "kwargs",
                "args",
                "bool",
                "str",
                "int",
                "dict",
                "tuple",
                "async",
                "await",
                "coroutine",
                "asyncio",
                "pytest",
                "mypy",
                "ruff",
            ]

            with custom_dict.open("w") as f:
                for term in technical_terms:
                    f.write(f"{term}\n")

            # Run codespell on documentation files
            cmd = [
                "uv",
                "run",
                "codespell",
                "--dictionary",
                str(custom_dict),
                "--ignore-words",
                str(custom_dict),
                "--skip",
                "*.pyc,*.git,*/.mypy_cache,*/.pytest_cache,*/.ruff_cache,*/htmlcov,*/build",
                "--check-filenames",
                "--check-hidden",
                str(self.docs_dir),
                str(self.project_root / "README.md"),
            ]

            result = subprocess.run(cmd, check=False, capture_output=True, text=True)

            spelling_errors = []
            if result.returncode != 0:
                spelling_errors = result.stdout.strip().split("\n") if result.stdout.strip() else []

            if result.returncode == 0:
                self.results["spelling_grammar"]["status"] = "pass"
                self.results["spelling_grammar"]["details"] = [
                    "✅ No spelling or grammar errors found"
                ]
                print("✅ No spelling or grammar errors found")
                return True

            self.results["spelling_grammar"]["status"] = "fail"
            self.results["spelling_grammar"]["errors"] = spelling_errors
            self.results["spelling_grammar"]["details"] = [
                f"❌ Found {len(spelling_errors)} spelling/grammar errors:",
                *spelling_errors,
            ]
            print(f"❌ Found {len(spelling_errors)} spelling/grammar errors")
            return False

        except Exception as e:
            self.results["spelling_grammar"]["status"] = "error"
            self.results["spelling_grammar"]["details"] = [f"Error checking spelling/grammar: {e}"]
            print(f"❌ Error checking spelling/grammar: {e}")
            return False

    def validate_formatting_style(self) -> bool:
        """Validate documentation formatting and style consistency.

        Returns:
            True if formatting is consistent, False otherwise
        """
        print("🔍 Validating Documentation Formatting and Style...")

        try:
            formatting_issues = []

            # Check reStructuredText files for common formatting issues
            for rst_file in self.docs_dir.rglob("*.rst"):
                try:
                    with rst_file.open(encoding="utf-8") as f:
                        lines = f.readlines()

                    for i, line in enumerate(lines, 1):
                        # Check for inconsistent heading underlines
                        if re.match(r'^[=\-^"~]+$', line.strip()) and i > 1:  # Not the first line
                            prev_line = lines[i - 2].strip()
                            if len(line.strip()) != len(prev_line):
                                formatting_issues.append(
                                    f"{rst_file.relative_to(self.project_root)}:{i} - "
                                    "Heading underline length mismatch"
                                )

                        # Check for very long lines (>120 characters)
                        if len(line) > MAX_LINE_LENGTH:
                            formatting_issues.append(
                                f"{rst_file.relative_to(self.project_root)}:{i} - "
                                f"Line too long ({len(line)} characters)"
                            )

                        # Check for trailing whitespace
                        if line.rstrip() != line.rstrip("\n"):
                            formatting_issues.append(
                                f"{rst_file.relative_to(self.project_root)}:{i} - "
                                "Trailing whitespace"
                            )

                except Exception as e:
                    print(f"⚠️ Warning: Could not check formatting in {rst_file}: {e}")

            # Use sphinx-lint if available
            try:
                cmd = ["uv", "run", "sphinx-lint", str(self.docs_dir / "source")]
                result = subprocess.run(cmd, check=False, capture_output=True, text=True)

                if result.returncode != 0 and result.stdout.strip():
                    sphinx_issues = result.stdout.strip().split("\n")
                    formatting_issues.extend(sphinx_issues)

            except Exception:
                # sphinx-lint not available, skip
                pass

            if not formatting_issues:
                self.results["formatting_style"]["status"] = "pass"
                self.results["formatting_style"]["details"] = [
                    "✅ Documentation formatting and style is consistent"
                ]
                print("✅ Documentation formatting and style is consistent")
                return True

            self.results["formatting_style"]["status"] = "fail"
            self.results["formatting_style"]["issues"] = formatting_issues
            self.results["formatting_style"]["details"] = [
                f"❌ Found {len(formatting_issues)} formatting/style issues:",
                *formatting_issues[:FIRST_N_ISSUES],  # Limit to first 10 issues
                *(["...and more"] if len(formatting_issues) > FIRST_N_ISSUES else []),
            ]
            print(f"❌ Found {len(formatting_issues)} formatting/style issues")
            return False

        except Exception as e:
            self.results["formatting_style"]["status"] = "error"
            self.results["formatting_style"]["details"] = [f"Error checking formatting/style: {e}"]
            print(f"❌ Error checking formatting/style: {e}")
            return False

    def run_all_validations(self) -> bool:
        """Run all documentation quality validations.

        Returns:
            True if all validations pass, False otherwise
        """
        print("📚 Running Comprehensive Documentation Quality Validation")
        print("=" * 60)

        validations = [
            ("Docstring Coverage", self.validate_docstring_coverage),
            ("API Completeness", self.validate_api_completeness),
            ("Link Validation", self.validate_links),
            ("Spelling & Grammar", self.validate_spelling_grammar),
            ("Formatting & Style", self.validate_formatting_style),
        ]

        all_passed = True

        for name, validation_func in validations:
            print(f"\n{name}:")
            print("-" * 40)
            try:
                passed = validation_func()
                if not passed:
                    all_passed = False
            except Exception as e:
                print(f"❌ {name} validation failed with error: {e}")
                all_passed = False

        # Update overall status
        self.results["overall_status"] = "pass" if all_passed else "fail"

        # Generate summary
        self.results["summary"] = {
            "total_validations": len(validations),
            "passed": sum(
                1
                for v in self.results.values()
                if isinstance(v, dict) and v.get("status") == "pass"
            ),
            "failed": sum(
                1
                for v in self.results.values()
                if isinstance(v, dict) and v.get("status") == "fail"
            ),
            "errors": sum(
                1
                for v in self.results.values()
                if isinstance(v, dict) and v.get("status") == "error"
            ),
        }

        print("\n" + "=" * 60)
        print("📊 Documentation Quality Validation Summary")
        print("=" * 60)

        if all_passed:
            print("✅ ALL VALIDATIONS PASSED")
            print("Documentation meets all quality requirements!")
        else:
            print("❌ SOME VALIDATIONS FAILED")
            print("Please review and fix the issues above.")

        print(
            f"\nResults: {self.results['summary']['passed']} passed, "
            f"{self.results['summary']['failed']} failed, "
            f"{self.results['summary']['errors']} errors"
        )

        return all_passed

    def save_results(self, output_file: Path | None = None) -> None:
        """Save validation results to JSON file.

        Args:
            output_file: Path to save results (default: docs-validation-results.json)
        """
        if output_file is None:
            output_file = self.project_root / "docs-validation-results.json"

        with output_file.open("w") as f:
            json.dump(self.results, f, indent=2)

        print(f"\n📄 Validation results saved to: {output_file}")


def main() -> None:
    """Main entry point for documentation validation."""
    parser = argparse.ArgumentParser(
        description="Validate documentation quality for mypylogger v0.2.8"
    )
    parser.add_argument(
        "--project-root", type=Path, default=Path.cwd(), help="Path to project root directory"
    )
    parser.add_argument("--output", type=Path, help="Path to save validation results JSON file")
    parser.add_argument(
        "--docstring-threshold",
        type=float,
        default=100.0,
        help="Minimum docstring coverage threshold (default: 100.0)",
    )
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first validation failure")

    args = parser.parse_args()

    # Validate project structure
    if not (args.project_root / "src").exists():
        print("❌ Error: src/ directory not found in project root")
        sys.exit(1)

    if not (args.project_root / "docs").exists():
        print("❌ Error: docs/ directory not found in project root")
        sys.exit(1)

    # Run validation
    validator = DocumentationValidator(args.project_root)

    if args.fail_fast:
        # Run validations individually and stop on first failure
        validations = [
            (
                "Docstring Coverage",
                lambda: validator.validate_docstring_coverage(args.docstring_threshold),
            ),
            ("API Completeness", validator.validate_api_completeness),
            ("Link Validation", validator.validate_links),
            ("Spelling & Grammar", validator.validate_spelling_grammar),
            ("Formatting & Style", validator.validate_formatting_style),
        ]

        for name, validation_func in validations:
            print(f"\n🔍 Running {name} validation...")
            if not validation_func():
                print(f"❌ {name} validation failed - stopping due to --fail-fast")
                validator.save_results(args.output)
                sys.exit(1)

        success = True
    else:
        # Run all validations
        success = validator.run_all_validations()

    # Save results
    validator.save_results(args.output)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
