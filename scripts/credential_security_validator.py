#!/usr/bin/env python3
"""Credential Security Validator for PyPI Publishing.

This script provides comprehensive security validation for credentials used in
PyPI publishing workflows, ensuring no credential exposure and proper security measures.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import re
import sys
from typing import ClassVar

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class CredentialSecurityValidator:
    """Validates credential security in workflows and logs."""

    # Patterns that might indicate credential exposure
    CREDENTIAL_PATTERNS: ClassVar[list[str]] = [
        r"pypi-[A-Za-z0-9_-]{10,}",  # PyPI tokens (flexible for testing, real tokens are 50+ chars)
        r"ghp_[A-Za-z0-9]{30,40}",  # GitHub personal access tokens (flexible length)
        r"ghs_[A-Za-z0-9]{30,40}",  # GitHub app tokens (flexible length)
        r"github_pat_[A-Za-z0-9_]{82}",  # GitHub fine-grained tokens
        r"AKIA[0-9A-Z]{16}",  # AWS access keys
        r"[A-Za-z0-9/+=]{40,}",  # Generic base64 tokens (40+ chars)
    ]

    # Safe patterns that should not be flagged
    SAFE_PATTERNS: ClassVar[list[str]] = [
        r"\*+",  # Masked tokens (asterisks)
        r"xxx+",  # Placeholder tokens
        r"placeholder",  # Placeholder text
        r"your-token-here",  # Template text
        r"<[^>]+>",  # Template variables
        r"\$\{[^}]+\}",  # Environment variable references
        r"\$[A-Z_]+",  # Environment variable references
    ]

    # Constants for magic numbers
    TRUNCATE_LENGTH = 20
    LINE_LENGTH_LIMIT = 100
    LONG_TOKEN_THRESHOLD = 50
    EXAMPLE_TOKEN_MAX_LENGTH = 40

    def __init__(self, workspace_root: Path = Path()) -> None:
        """Initialize the credential security validator.

        Args:
            workspace_root: Root directory of the workspace
        """
        self.workspace_root = workspace_root
        self.violations: list[dict[str, str]] = []

    def scan_file_for_credentials(self, file_path: Path) -> list[dict[str, str]]:
        """Scan a file for potential credential exposure.

        Args:
            file_path: Path to the file to scan

        Returns:
            List of potential credential violations
        """
        violations = []

        try:
            with file_path.open(encoding="utf-8", errors="ignore") as f:
                content = f.read()

            lines = content.split("\n")

            for line_num, line in enumerate(lines, 1):
                # Skip comments and documentation
                if self._is_safe_line(line):
                    continue

                # Check for credential patterns
                for pattern in self.CREDENTIAL_PATTERNS:
                    matches = re.finditer(pattern, line, re.IGNORECASE)

                    for match in matches:
                        matched_text = match.group()

                        # Check if it's a safe pattern
                        if self._is_safe_credential(matched_text):
                            continue

                        # Check if the match is followed by "..." in the line (truncated token)
                        match_end = match.end()
                        if match_end < len(line) and line[match_end : match_end + 3] == "...":
                            continue

                        # Handle file path safely - use relative path if possible, otherwise absolute
                        try:
                            file_display = str(file_path.relative_to(self.workspace_root))
                        except ValueError:
                            # File is outside workspace root, use absolute path
                            file_display = str(file_path)

                        violations.append(
                            {
                                "file": file_display,
                                "line": line_num,
                                "pattern": pattern,
                                "matched_text": matched_text[: self.TRUNCATE_LENGTH] + "..."
                                if len(matched_text) > self.TRUNCATE_LENGTH
                                else matched_text,
                                "full_line": line.strip()[: self.LINE_LENGTH_LIMIT] + "..."
                                if len(line.strip()) > self.LINE_LENGTH_LIMIT
                                else line.strip(),
                                "severity": self._determine_severity(pattern, matched_text),
                            }
                        )

        except Exception as e:
            logger.warning("Failed to scan file %s: %s", file_path, e)

        return violations

    def _is_safe_line(self, line: str) -> bool:
        """Check if a line is safe to ignore (comments, docs, etc.).

        Args:
            line: Line of text to check

        Returns:
            True if the line is safe to ignore
        """
        stripped = line.strip()

        # Empty lines
        if not stripped:
            return True

        # Comments
        if stripped.startswith(("#", "//", "/*", "*", "<!--")):
            return True

        # Documentation strings
        if '"""' in stripped or "'''" in stripped:
            return True

        # YAML comments
        return stripped.startswith("# ")

    def _is_safe_credential(self, credential: str) -> bool:
        """Check if a credential match is actually safe (masked, example, etc.).

        Args:
            credential: The matched credential text

        Returns:
            True if the credential is safe
        """
        credential_lower = credential.lower()

        for safe_pattern in self.SAFE_PATTERNS:
            if re.search(safe_pattern, credential_lower):
                return True

        # Check for common safe indicators - be specific to avoid false positives
        # Only consider obviously safe patterns, not just any occurrence of these words
        safe_indicators = [
            "placeholder",
            "your-",
            "sample-",
            "xxx",
            "***",
            "...",  # Truncated tokens
            "redacted",
            "masked",
            "hidden",
        ]

        # Check basic safe indicators first
        if any(indicator in credential_lower for indicator in safe_indicators):
            return True

        # Special handling for "example" - only consider safe if it's clearly a placeholder
        # Exclude AWS keys that contain EXAMPLE (these are real format examples from AWS docs)
        if (
            "example" in credential_lower
            and not credential_lower.startswith("akia")
            and not (
                "examplekey" in credential_lower or credential_lower.endswith("example")
            )  # Don't treat AWS format examples as safe
            and (
                credential_lower.startswith("example")
                or "example-" in credential_lower
                or "-example-" in credential_lower
                or credential_lower == "example"
                or (
                    "example" in credential_lower
                    and len(credential_lower) <= self.EXAMPLE_TOKEN_MAX_LENGTH
                )
            )
        ):
            return True

        # "test" - only consider safe if it's clearly a test placeholder
        if "test" in credential_lower and (
            credential_lower.startswith("test-")
            or credential_lower.endswith("-test")
            or credential_lower == "test"
        ):
            return True

        # "demo" - only consider safe if it's clearly a demo placeholder
        return bool(
            "demo" in credential_lower
            and (
                credential_lower.startswith("demo-")
                or credential_lower.endswith("-demo")
                or credential_lower == "demo"
            )
        )

    def _determine_severity(self, pattern: str, matched_text: str) -> str:
        """Determine the severity of a credential exposure.

        Args:
            pattern: The regex pattern that matched
            matched_text: The actual matched text

        Returns:
            Severity level (HIGH, MEDIUM, LOW)
        """
        # PyPI tokens are high severity
        if pattern.startswith(r"pypi-"):
            return "HIGH"

        # GitHub tokens are high severity
        if any(gh_pattern in pattern for gh_pattern in ["ghp_", "ghs_", "github_pat_"]):
            return "HIGH"

        # AWS keys are high severity
        if "AKIA" in pattern:
            return "HIGH"

        # Long base64 strings are medium severity
        if len(matched_text) > self.LONG_TOKEN_THRESHOLD:
            return "MEDIUM"

        return "LOW"

    def scan_workflow_files(self) -> list[dict[str, str]]:
        """Scan GitHub Actions workflow files for credential exposure.

        Returns:
            List of credential violations in workflow files
        """
        violations = []
        workflows_dir = self.workspace_root / ".github" / "workflows"

        if not workflows_dir.exists():
            logger.info("No GitHub workflows directory found")
            return violations

        for workflow_file in workflows_dir.glob("*.yml"):
            file_violations = self.scan_file_for_credentials(workflow_file)
            violations.extend(file_violations)

        for workflow_file in workflows_dir.glob("*.yaml"):
            file_violations = self.scan_file_for_credentials(workflow_file)
            violations.extend(file_violations)

        return violations

    def scan_script_files(self) -> list[dict[str, str]]:
        """Scan script files for credential exposure.

        Returns:
            List of credential violations in script files
        """
        violations = []
        scripts_dir = self.workspace_root / "scripts"

        if not scripts_dir.exists():
            logger.info("No scripts directory found")
            return violations

        for script_file in scripts_dir.glob("*.py"):
            file_violations = self.scan_file_for_credentials(script_file)
            violations.extend(file_violations)

        for script_file in scripts_dir.glob("*.sh"):
            file_violations = self.scan_file_for_credentials(script_file)
            violations.extend(file_violations)

        return violations

    def scan_log_files(self, log_directory: Path | None = None) -> list[dict[str, str]]:
        """Scan log files for credential exposure.

        Args:
            log_directory: Directory containing log files

        Returns:
            List of credential violations in log files
        """
        violations = []

        if log_directory is None:
            # Check common log locations (avoid /tmp for security)
            log_locations = [
                self.workspace_root / "logs",
                self.workspace_root / ".logs",
                Path.home() / ".logs",
            ]
        else:
            log_locations = [log_directory]

        for log_dir in log_locations:
            if not log_dir.exists():
                continue

            try:
                for log_file in log_dir.glob("*.log"):
                    file_violations = self.scan_file_for_credentials(log_file)
                    violations.extend(file_violations)

                for log_file in log_dir.glob("*.txt"):
                    if "log" in log_file.name.lower():
                        file_violations = self.scan_file_for_credentials(log_file)
                        violations.extend(file_violations)
            except PermissionError:
                logger.warning("Permission denied accessing log directory: %s", log_dir)

        return violations

    def validate_environment_variables(self) -> list[dict[str, str]]:
        """Validate that sensitive environment variables are not exposed.

        Returns:
            List of environment variable security issues
        """
        violations = []

        # Check for potentially exposed environment variables
        sensitive_env_vars = [
            "PYPI_API_TOKEN",
            "PYPI_TOKEN",
            "TWINE_PASSWORD",
            "GITHUB_TOKEN",
            "GH_TOKEN",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_SESSION_TOKEN",
        ]

        for env_var in sensitive_env_vars:
            value = os.environ.get(env_var)
            if value and not self._is_safe_credential(value):
                violations.append(
                    {
                        "type": "environment_variable",
                        "variable": env_var,
                        "severity": "HIGH",
                        "issue": "Sensitive environment variable may be exposed",
                        "recommendation": "Ensure this variable is only set in secure contexts",
                    }
                )

        return violations

    def check_github_secrets_usage(self) -> list[dict[str, str]]:
        """Check that GitHub secrets are properly referenced in workflows.

        Returns:
            List of GitHub secrets usage issues
        """
        violations = []
        workflows_dir = self.workspace_root / ".github" / "workflows"

        if not workflows_dir.exists():
            return violations

        required_secrets = ["AWS_ROLE_ARN", "AWS_SECRET_NAME", "AWS_REGION"]

        for workflow_file in workflows_dir.glob("*.yml"):
            try:
                with workflow_file.open(encoding="utf-8") as f:
                    content = f.read()

                # Check for proper secrets usage
                for secret in required_secrets:
                    if secret in content and f"secrets.{secret}" not in content:
                        violations.append(
                            {
                                "file": str(workflow_file.relative_to(self.workspace_root)),
                                "secret": secret,
                                "severity": "MEDIUM",
                                "issue": f"Secret {secret} may not be properly referenced",
                                "recommendation": f"Use ${{{{ secrets.{secret} }}}} syntax",
                            }
                        )

            except Exception as e:
                logger.warning("Failed to check secrets in %s: %s", workflow_file, e)

        return violations

    def run_comprehensive_scan(self) -> dict[str, list[dict[str, str]]]:
        """Run a comprehensive credential security scan.

        Returns:
            Dictionary of scan results by category
        """
        logger.info("Starting comprehensive credential security scan...")

        results = {
            "workflow_files": self.scan_workflow_files(),
            "script_files": self.scan_script_files(),
            "log_files": self.scan_log_files(),
            "environment_variables": self.validate_environment_variables(),
            "github_secrets": self.check_github_secrets_usage(),
        }

        # Count total violations
        total_violations = sum(len(violations) for violations in results.values())

        if total_violations == 0:
            logger.info("✅ No credential security violations found")
        else:
            logger.warning("⚠️  Found %d potential credential security issues", total_violations)

        return results

    def generate_security_report(self, results: dict[str, list[dict[str, str]]]) -> str:
        """Generate a detailed security report.

        Args:
            results: Scan results from run_comprehensive_scan

        Returns:
            Formatted security report
        """
        report_lines = [
            "# Credential Security Scan Report",
            "",
            f"**Scan Date**: {__import__('datetime').datetime.now().isoformat()}",
            f"**Workspace**: {self.workspace_root.absolute()}",
            "",
        ]

        total_violations = sum(len(violations) for violations in results.values())

        if total_violations == 0:
            report_lines.extend(
                [
                    "## ✅ Security Status: CLEAN",
                    "",
                    "No credential security violations were found in the scan.",
                    "",
                ]
            )
        else:
            report_lines.extend([f"## ⚠️ Security Status: {total_violations} ISSUES FOUND", ""])

        for category, violations in results.items():
            if not violations:
                continue

            category_title = category.replace("_", " ").title()
            report_lines.extend([f"### {category_title} ({len(violations)} issues)", ""])

            for violation in violations:
                severity = violation.get("severity", "UNKNOWN")
                report_lines.append(f"**{severity}**: {violation}")
                report_lines.append("")

        if total_violations > 0:
            report_lines.extend(
                [
                    "## Recommendations",
                    "",
                    "1. **Remove any exposed credentials** from code and logs immediately",
                    "2. **Rotate any potentially compromised credentials**",
                    "3. **Use GitHub secrets** for sensitive values in workflows",
                    "4. **Implement credential masking** in logging systems",
                    "5. **Review and update security practices** regularly",
                    "",
                ]
            )

        return "\n".join(report_lines)


def main() -> int:
    """Main function for command-line usage.

    Returns:
        Exit code (0 for success, 1 for violations found)
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Credential Security Validator for PyPI Publishing"
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path(),
        help="Workspace root directory (default: current directory)",
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "text", "markdown"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument("--output-file", type=Path, help="Output file path (default: stdout)")
    parser.add_argument(
        "--fail-on-violations",
        action="store_true",
        help="Exit with error code if violations are found",
    )

    args = parser.parse_args()

    try:
        validator = CredentialSecurityValidator(args.workspace)
        results = validator.run_comprehensive_scan()

        total_violations = sum(len(violations) for violations in results.values())

        if args.output_format == "json":
            output = json.dumps(results, indent=2)
        elif args.output_format == "markdown":
            output = validator.generate_security_report(results)
        elif total_violations == 0:
            output = "✅ No credential security violations found"
        else:
            output = f"⚠️  Found {total_violations} potential credential security issues:\n\n"
            for category, violations in results.items():
                if violations:
                    output += f"{category.replace('_', ' ').title()}:\n"
                    for violation in violations:
                        output += f"  - {violation}\n"
                    output += "\n"

        if args.output_file:
            args.output_file.write_text(output, encoding="utf-8")
            print(f"Security report written to: {args.output_file}")
        else:
            print(output)

        if args.fail_on_violations and total_violations > 0:
            return 1

        return 0

    except Exception as e:
        logger.exception("Security scan failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
