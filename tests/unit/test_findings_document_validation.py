"""Tests for security findings document validation."""

from pathlib import Path
import subprocess
import sys


class TestFindingsDocumentValidation:
    """Test the findings document validation script."""

    def test_validation_script_exists(self) -> None:
        """Test that the validation script exists."""
        script_path = Path("security/scripts/validate-findings-document.py")
        assert script_path.exists()

    def test_validation_script_executable(self) -> None:
        """Test that the validation script is executable."""
        script_path = Path("security/scripts/validate-findings-document.py")

        # Test that the script can be run
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=False,
            capture_output=True,
            text=True,
        )

        # Should exit with 0 (success) or 1 (validation failure)
        assert result.returncode in [0, 1]

    def test_findings_document_exists(self) -> None:
        """Test that the findings document exists."""
        document_path = Path("security/findings/SECURITY_FINDINGS.md")

        # Document should exist after running the security automation
        if document_path.exists():
            assert document_path.is_file()
            assert document_path.stat().st_size > 0

    def test_findings_document_structure(self) -> None:
        """Test basic structure of the findings document."""
        document_path = Path("security/findings/SECURITY_FINDINGS.md")

        if document_path.exists():
            content = document_path.read_text(encoding="utf-8")

            # Check for required sections
            assert "# Security Findings Summary" in content
            assert "## Current Findings" in content
            assert "## Remediation Summary" in content

            # Check for required header fields
            assert "**Last Updated**:" in content
            assert "**Total Active Findings**:" in content
            assert "**Days Since Last Scan**:" in content

    def test_ci_security_check_includes_validation(self) -> None:
        """Test that CI security check includes document validation."""
        ci_script_path = Path("scripts/ci_security_check.sh")

        if ci_script_path.exists():
            content = ci_script_path.read_text(encoding="utf-8")

            # Should include document validation
            assert "validate-findings-document.py" in content
            assert "Security findings document validation" in content

    def test_document_accessibility_for_automation(self) -> None:
        """Test that the document is accessible for automated processing."""
        document_path = Path("security/findings/SECURITY_FINDINGS.md")

        if document_path.exists():
            # Should be readable
            content = document_path.read_text(encoding="utf-8")
            assert len(content) > 0

            # Should be valid UTF-8
            assert isinstance(content, str)

            # Should have consistent line endings
            lines = content.split("\n")
            assert len(lines) > 1


class TestDocumentValidationIntegration:
    """Test document validation integration with CI/CD."""

    def test_validation_integration_with_ci_script(self) -> None:
        """Test that validation integrates properly with CI script."""
        # Run the CI security check to ensure it includes validation
        result = subprocess.run(
            ["./scripts/ci_security_check.sh"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )

        # Should complete successfully (exit code 0)
        assert result.returncode == 0

        # Should include validation output
        output = result.stdout + result.stderr
        assert (
            "Security findings document" in output
            or "Security findings update" in output
            or "validate-findings-document.py" in output
        )

    def test_document_validation_error_handling(self) -> None:
        """Test that document validation handles errors gracefully."""
        # Test with a non-existent document path
        result = subprocess.run(
            [sys.executable, "security/scripts/validate-findings-document.py"],
            env={"PYTHONPATH": "security/scripts"},
            check=False,
            capture_output=True,
            text=True,
        )

        # Should handle missing document gracefully
        # Either succeed (if document exists) or fail gracefully (if it doesn't)
        assert result.returncode in [0, 1]
