"""Tests for release notes and justification generator.

This module tests the comprehensive release notes generation system
with templates for different types of security-driven releases.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import tempfile

from scripts.release_automation_engine import ReleaseType, SecurityChange, SecurityChangeType


class TestSecurityDrivenReleaseTemplate:
    """Test cases for SecurityDrivenReleaseTemplate."""

    def test_template_import(self) -> None:
        """Test that SecurityDrivenReleaseTemplate can be imported."""
        from scripts.release_notes_generator import SecurityDrivenReleaseTemplate

        template = SecurityDrivenReleaseTemplate()
        assert template is not None

    def test_generate_notes_with_new_vulnerabilities(self) -> None:
        """Test generating notes for new vulnerabilities."""
        from scripts.release_notes_generator import SecurityDrivenReleaseTemplate

        template = SecurityDrivenReleaseTemplate()

        security_changes = [
            SecurityChange(
                change_type=SecurityChangeType.NEW_VULNERABILITY,
                finding_id="CVE-2025-HIGH",
                old_state=None,
                new_state="high vulnerability",
                impact_level="high",
            ),
            SecurityChange(
                change_type=SecurityChangeType.NEW_VULNERABILITY,
                finding_id="CVE-2025-MEDIUM",
                old_state=None,
                new_state="medium vulnerability",
                impact_level="medium",
            ),
        ]

        notes = template.generate(
            security_changes=security_changes,
            version="0.2.1",
            timestamp=datetime(2025, 1, 21, 10, 30, tzinfo=timezone.utc),
        )

        assert "Security-Driven Release v0.2.1" in notes
        assert "2025-01-21 10:30 UTC" in notes
        assert "New Security Findings" in notes
        assert "CVE-2025-HIGH" in notes
        assert "CVE-2025-MEDIUM" in notes
        assert "High/Critical Severity" in notes
        assert "Medium/Low Severity" in notes

    def test_generate_notes_with_resolved_vulnerabilities(self) -> None:
        """Test generating notes for resolved vulnerabilities."""
        from scripts.release_notes_generator import SecurityDrivenReleaseTemplate

        template = SecurityDrivenReleaseTemplate()

        security_changes = [
            SecurityChange(
                change_type=SecurityChangeType.RESOLVED_VULNERABILITY,
                finding_id="CVE-2025-RESOLVED",
                old_state="medium vulnerability",
                new_state="resolved",
                impact_level="medium",
            ),
        ]

        notes = template.generate(security_changes=security_changes)

        assert "Resolved Security Findings" in notes
        assert "CVE-2025-RESOLVED" in notes
        assert "Previously medium vulnerability" in notes

    def test_generate_notes_with_severity_changes(self) -> None:
        """Test generating notes for severity changes."""
        from scripts.release_notes_generator import SecurityDrivenReleaseTemplate

        template = SecurityDrivenReleaseTemplate()

        security_changes = [
            SecurityChange(
                change_type=SecurityChangeType.SEVERITY_CHANGE,
                finding_id="CVE-2025-SEVERITY",
                old_state="medium vulnerability",
                new_state="high vulnerability",
                impact_level="high",
            ),
        ]

        notes = template.generate(security_changes=security_changes)

        assert "Severity Changes" in notes
        assert "CVE-2025-SEVERITY" in notes
        assert "medium vulnerability → high vulnerability" in notes


class TestManualReleaseTemplate:
    """Test cases for ManualReleaseTemplate."""

    def test_template_import(self) -> None:
        """Test that ManualReleaseTemplate can be imported."""
        from scripts.release_notes_generator import ManualReleaseTemplate

        template = ManualReleaseTemplate()
        assert template is not None

    def test_generate_notes_with_custom_notes(self) -> None:
        """Test generating manual release notes with custom notes."""
        from scripts.release_notes_generator import ManualReleaseTemplate

        template = ManualReleaseTemplate()

        notes = template.generate(
            custom_notes="Fixed bug in logging configuration",
            version="0.2.1",
            timestamp=datetime(2025, 1, 21, 10, 30, tzinfo=timezone.utc),
        )

        assert "Manual Release v0.2.1" in notes
        assert "2025-01-21 10:30 UTC" in notes
        assert "Fixed bug in logging configuration" in notes
        assert "Security Status" in notes

    def test_generate_notes_without_custom_notes(self) -> None:
        """Test generating manual release notes without custom notes."""
        from scripts.release_notes_generator import ManualReleaseTemplate

        template = ManualReleaseTemplate()

        notes = template.generate()

        assert "Manual Release" in notes
        assert "Manual Release" in notes
        assert "Security Status" in notes


class TestReleaseJustificationGenerator:
    """Test cases for ReleaseJustificationGenerator."""

    def test_generator_import(self) -> None:
        """Test that ReleaseJustificationGenerator can be imported."""
        from scripts.release_notes_generator import ReleaseJustificationGenerator

        generator = ReleaseJustificationGenerator()
        assert generator is not None

    def test_generate_manual_justification(self) -> None:
        """Test generating justification for manual releases."""
        from scripts.release_notes_generator import ReleaseJustificationGenerator

        generator = ReleaseJustificationGenerator()

        justification = generator.generate_justification(
            ReleaseType.MANUAL, [], "Bug fixes and improvements"
        )

        assert "Manual release requested by maintainer" in justification
        assert "Bug fixes and improvements" in justification

    def test_generate_security_justification_with_high_vulnerabilities(self) -> None:
        """Test generating justification for security releases with high vulnerabilities."""
        from scripts.release_notes_generator import ReleaseJustificationGenerator

        generator = ReleaseJustificationGenerator()

        security_changes = [
            SecurityChange(
                change_type=SecurityChangeType.NEW_VULNERABILITY,
                finding_id="CVE-2025-CRITICAL",
                old_state=None,
                new_state="critical vulnerability",
                impact_level="critical",
            ),
        ]

        justification = generator.generate_justification(
            ReleaseType.SECURITY_AUTO,
            security_changes,
        )

        assert "Security-driven release" in justification
        assert "1 new high/critical vulnerability" in justification

    def test_generate_security_justification_with_resolved_vulnerabilities(self) -> None:
        """Test generating justification for resolved vulnerabilities."""
        from scripts.release_notes_generator import ReleaseJustificationGenerator

        generator = ReleaseJustificationGenerator()

        security_changes = [
            SecurityChange(
                change_type=SecurityChangeType.RESOLVED_VULNERABILITY,
                finding_id="CVE-2025-RESOLVED",
                old_state="medium vulnerability",
                new_state="resolved",
                impact_level="medium",
            ),
        ]

        justification = generator.generate_justification(
            ReleaseType.SECURITY_AUTO,
            security_changes,
        )

        assert "Security-driven release" in justification
        assert "1 vulnerability resolved" in justification


class TestComprehensiveReleaseNotesGenerator:
    """Test cases for ComprehensiveReleaseNotesGenerator."""

    def test_generator_import(self) -> None:
        """Test that ComprehensiveReleaseNotesGenerator can be imported."""
        from scripts.release_notes_generator import ComprehensiveReleaseNotesGenerator

        generator = ComprehensiveReleaseNotesGenerator()
        assert generator is not None

    def test_generate_complete_security_release_notes(self) -> None:
        """Test generating complete security release notes package."""
        from scripts.release_notes_generator import ComprehensiveReleaseNotesGenerator

        generator = ComprehensiveReleaseNotesGenerator()

        security_changes = [
            SecurityChange(
                change_type=SecurityChangeType.NEW_VULNERABILITY,
                finding_id="CVE-2025-TEST",
                old_state=None,
                new_state="high vulnerability",
                impact_level="high",
            ),
        ]

        result = generator.generate_complete_release_notes(
            release_type=ReleaseType.SECURITY_AUTO,
            security_changes=security_changes,
            version="0.2.1",
        )

        assert "release_notes" in result
        assert "justification" in result
        assert "summary" in result
        assert "timestamp" in result
        assert "release_type" in result

        assert "CVE-2025-TEST" in result["release_notes"]
        assert "Security-driven release" in result["justification"]
        assert "0.2.1" in result["summary"]
        assert result["release_type"] == "security_auto"

    def test_generate_complete_manual_release_notes(self) -> None:
        """Test generating complete manual release notes package."""
        from scripts.release_notes_generator import ComprehensiveReleaseNotesGenerator

        generator = ComprehensiveReleaseNotesGenerator()

        result = generator.generate_complete_release_notes(
            release_type=ReleaseType.MANUAL,
            security_changes=[],
            version="0.2.1",
            custom_notes="Bug fixes and improvements",
        )

        assert "release_notes" in result
        assert "justification" in result
        assert "summary" in result

        assert "Manual Release v0.2.1" in result["release_notes"]
        assert "Bug fixes and improvements" in result["release_notes"]
        assert "Manual release requested" in result["justification"]
        assert result["release_type"] == "manual"

    def test_save_release_notes_to_files(self) -> None:
        """Test saving release notes to files."""
        from scripts.release_notes_generator import ComprehensiveReleaseNotesGenerator

        generator = ComprehensiveReleaseNotesGenerator()

        release_notes_data = {
            "release_notes": "# Test Release Notes",
            "justification": "Test justification",
            "summary": "Test summary",
            "timestamp": "2025-01-21T10:30:00Z",
            "release_type": "manual",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            files_created = generator.save_release_notes(release_notes_data, output_dir)

            assert "release_notes" in files_created
            assert "justification" in files_created
            assert "summary" in files_created

            # Check files exist and have correct content
            assert files_created["release_notes"].exists()
            assert files_created["justification"].exists()
            assert files_created["summary"].exists()

            assert "# Test Release Notes" in files_created["release_notes"].read_text()
            assert "Test justification" in files_created["justification"].read_text()
            assert "Test summary" in files_created["summary"].read_text()


class TestConvenienceFunctions:
    """Test cases for convenience functions."""

    def test_generate_security_release_notes_function(self) -> None:
        """Test the convenience function for generating security release notes."""
        from scripts.release_notes_generator import generate_security_release_notes

        security_changes = [
            SecurityChange(
                change_type=SecurityChangeType.NEW_VULNERABILITY,
                finding_id="CVE-2025-CONVENIENCE",
                old_state=None,
                new_state="medium vulnerability",
                impact_level="medium",
            ),
        ]

        result = generate_security_release_notes(
            security_changes=security_changes,
            version="0.2.1",
        )

        assert "release_notes" in result
        assert "justification" in result
        assert "CVE-2025-CONVENIENCE" in result["release_notes"]
