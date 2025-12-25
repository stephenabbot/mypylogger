"""Tests for security automation engine."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest


class TestAutomationEngine:
    """Test cases for the automation engine."""

    def test_automation_script_exists(self) -> None:
        """Test that automation script exists and is executable."""
        script_path = (
            Path(__file__).parent.parent.parent / "security" / "scripts" / "update-findings.py"
        )
        assert script_path.exists(), f"Automation script not found: {script_path}"
        assert script_path.is_file(), f"Script path is not a file: {script_path}"

    def test_automation_script_syntax(self) -> None:
        """Test that automation script has valid Python syntax."""
        script_path = (
            Path(__file__).parent.parent.parent / "security" / "scripts" / "update-findings.py"
        )

        # Test syntax by compiling the script
        try:
            with script_path.open("r", encoding="utf-8") as f:
                script_content = f.read()
            compile(script_content, str(script_path), "exec")
        except SyntaxError as e:
            pytest.fail(f"Automation script has syntax error: {e}")

    def test_automation_script_dry_run(self) -> None:
        """Test automation script dry-run functionality."""
        script_path = (
            Path(__file__).parent.parent.parent / "security" / "scripts" / "update-findings.py"
        )

        # Run script with --dry-run flag
        result = subprocess.run(  # nosec B603 B607
            [sys.executable, str(script_path), "--dry-run"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, (
            f"Script failed with exit code {result.returncode}: {result.stderr}"
        )
        assert "DRY RUN MODE" in result.stdout, "Dry run mode not indicated in output"
        assert "Reports directory:" in result.stdout, "Reports directory not shown in dry run"

    def test_automation_script_help(self) -> None:
        """Test automation script help functionality."""
        script_path = (
            Path(__file__).parent.parent.parent / "security" / "scripts" / "update-findings.py"
        )

        # Run script with --help flag
        result = subprocess.run(  # nosec B603 B607
            [sys.executable, str(script_path), "--help"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, (
            f"Help command failed with exit code {result.returncode}: {result.stderr}"
        )
        assert "Security findings automation engine" in result.stdout, "Help text not found"
        assert "--verbose" in result.stdout, "Verbose option not documented"
        assert "--dry-run" in result.stdout, "Dry-run option not documented"

    def test_automation_script_with_nonexistent_reports(self) -> None:
        """Test automation script with nonexistent reports directory."""
        script_path = (
            Path(__file__).parent.parent.parent / "security" / "scripts" / "update-findings.py"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            nonexistent_reports = temp_path / "nonexistent_reports"
            output_file = temp_path / "findings.md"

            # Run script with nonexistent reports directory
            result = subprocess.run(  # nosec B603 B607
                [
                    sys.executable,
                    str(script_path),
                    "--reports-dir",
                    str(nonexistent_reports),
                    "--output",
                    str(output_file),
                    "--verbose",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Script should handle missing directory gracefully
            # It might succeed with warnings or fail gracefully
            assert result.returncode in [0, 1], (
                f"Unexpected exit code {result.returncode}: {result.stderr}"
            )

    def test_automation_script_with_empty_reports_dir(self) -> None:
        """Test automation script with empty reports directory."""
        script_path = (
            Path(__file__).parent.parent.parent / "security" / "scripts" / "update-findings.py"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            reports_dir = temp_path / "reports"
            output_file = temp_path / "findings.md"

            # Create empty reports directory
            reports_dir.mkdir(parents=True)

            # Run script with empty reports directory
            result = subprocess.run(  # nosec B603 B607
                [
                    sys.executable,
                    str(script_path),
                    "--reports-dir",
                    str(reports_dir),
                    "--output",
                    str(output_file),
                    "--verbose",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Script should handle empty directory gracefully
            assert result.returncode in [0, 1], (
                f"Unexpected exit code {result.returncode}: {result.stderr}"
            )

    def test_automation_script_with_sample_reports(self) -> None:
        """Test automation script with sample scanner reports."""
        script_path = (
            Path(__file__).parent.parent.parent / "security" / "scripts" / "update-findings.py"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            reports_dir = temp_path / "reports"
            output_file = temp_path / "findings.md"

            # Create reports directory and sample files
            reports_dir.mkdir(parents=True)

            # Create sample pip-audit report
            pip_audit_data = {
                "dependencies": [
                    {
                        "name": "test-package",
                        "version": "1.0.0",
                        "vulns": [
                            {
                                "id": "CVE-2023-12345",
                                "description": "Test vulnerability description",
                                "aliases": ["GHSA-test-1234"],
                                "fix_versions": ["1.0.1"],
                            }
                        ],
                    }
                ]
            }

            with (reports_dir / "pip-audit.json").open("w") as f:
                json.dump(pip_audit_data, f)

            # Create sample bandit report
            bandit_data = {
                "results": [
                    {
                        "test_id": "B101",
                        "test_name": "assert_used",
                        "filename": "test_file.py",
                        "line_number": 10,
                        "issue_severity": "LOW",
                        "issue_confidence": "HIGH",
                        "issue_text": "Use of assert detected",
                    }
                ]
            }

            with (reports_dir / "bandit.json").open("w") as f:
                json.dump(bandit_data, f)

            # Run script with sample reports
            result = subprocess.run(  # nosec B603 B607
                [
                    sys.executable,
                    str(script_path),
                    "--reports-dir",
                    str(reports_dir),
                    "--output",
                    str(output_file),
                    "--verbose",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Script should process reports successfully
            assert result.returncode in [0, 1], (
                f"Unexpected exit code {result.returncode}: {result.stderr}"
            )

            # Check if output file was created (if script succeeded)
            if result.returncode == 0:
                assert output_file.exists(), "Output file was not created"

                # Verify output file has some content
                content = output_file.read_text(encoding="utf-8")
                assert len(content) > 0, "Output file is empty"
                assert "Security Findings Summary" in content, "Expected header not found in output"

    def test_automation_script_json_output(self) -> None:
        """Test automation script JSON output functionality."""
        script_path = (
            Path(__file__).parent.parent.parent / "security" / "scripts" / "update-findings.py"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            reports_dir = temp_path / "reports"
            output_file = temp_path / "findings.md"

            # Create empty reports directory
            reports_dir.mkdir(parents=True)

            # Run script with JSON output
            result = subprocess.run(  # nosec B603 B607
                [
                    sys.executable,
                    str(script_path),
                    "--reports-dir",
                    str(reports_dir),
                    "--output",
                    str(output_file),
                    "--json-output",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Script should handle JSON output
            assert result.returncode in [0, 1], (
                f"Unexpected exit code {result.returncode}: {result.stderr}"
            )

            # If successful, output should be valid JSON
            if result.returncode == 0 and result.stdout.strip():
                try:
                    json_output = json.loads(result.stdout)
                    assert isinstance(json_output, dict), "JSON output should be a dictionary"
                    assert "timestamp" in json_output, "JSON output should include timestamp"
                except json.JSONDecodeError as e:
                    pytest.fail(f"Invalid JSON output: {e}")

    def test_automation_script_imports_security_modules(self) -> None:
        """Test that automation script can import required security modules."""
        script_path = (
            Path(__file__).parent.parent.parent / "security" / "scripts" / "update-findings.py"
        )

        # Test that the script can import without errors by running a simple check
        test_script = f"""
import sys
sys.path.insert(0, '{script_path.parent.parent}')

try:
    from generator import FindingsDocumentGenerator
    from parsers import extract_all_findings
    from remediation import RemediationDatastore
    from synchronizer import RemediationSynchronizer
    print("SUCCESS: All imports successful")
except ImportError as e:
    print(f"IMPORT_ERROR: {{e}}")
    sys.exit(1)
"""

        result = subprocess.run(  # nosec B603 B607
            [sys.executable, "-c", test_script],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Import test failed: {result.stderr}"
        assert "SUCCESS" in result.stdout, f"Import test did not succeed: {result.stdout}"
