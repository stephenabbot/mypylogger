"""Integration tests for complete release automation system.

This module tests the end-to-end integration of security scanning,
change detection, release decision making, and release notes generation.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
import tempfile

from scripts.release_automation_engine import (
    ReleaseAutomationEngine,
    ReleaseType,
    SecurityChange,
    SecurityChangeType,
)
from scripts.release_notes_generator import ComprehensiveReleaseNotesGenerator
from scripts.security_change_detector import SecurityChangeDetector
from security.models import SecurityFinding


class TestEndToEndReleaseAutomation:
    """Test complete end-to-end release automation workflows."""

    def test_complete_security_driven_release_workflow(self) -> None:
        """Test complete workflow from security findings to release decision."""
        # Create test security findings
        previous_findings = [
            SecurityFinding(
                finding_id="CVE-2025-OLD",
                package="test-package",
                version="1.0.0",
                severity="medium",
                source_scanner="pip-audit",
                discovered_date=date.today(),
                description="Old vulnerability",
                impact="Medium impact",
                fix_available=False,
            )
        ]

        current_findings = [
            SecurityFinding(
                finding_id="CVE-2025-NEW",
                package="test-package",
                version="1.0.0",
                severity="high",
                source_scanner="pip-audit",
                discovered_date=date.today(),
                description="New high severity vulnerability",
                impact="High impact",
                fix_available=False,
            )
        ]

        # Initialize components
        detector = SecurityChangeDetector()
        engine = ReleaseAutomationEngine()
        notes_generator = ComprehensiveReleaseNotesGenerator()

        # Step 1: Detect security changes
        changes = detector.detect_changes(previous_findings, current_findings)

        # Verify changes detected
        assert len(changes) == 2  # One new, one resolved
        new_changes = [c for c in changes if c.change_type == SecurityChangeType.NEW_VULNERABILITY]
        resolved_changes = [
            c for c in changes if c.change_type == SecurityChangeType.RESOLVED_VULNERABILITY
        ]

        assert len(new_changes) == 1
        assert len(resolved_changes) == 1
        assert new_changes[0].finding_id == "CVE-2025-NEW"
        assert new_changes[0].impact_level == "high"

        # Step 2: Make release decision
        decision = engine.make_release_decision(changes)

        # Verify release decision
        assert decision.should_release is True
        assert decision.trigger_type == ReleaseType.SECURITY_AUTO
        assert "high" in decision.justification.lower()

        # Step 3: Generate release notes
        release_notes_data = notes_generator.generate_complete_release_notes(
            release_type=decision.trigger_type,
            security_changes=changes,
            version="0.2.1",
        )

        # Verify release notes
        assert "release_notes" in release_notes_data
        assert "justification" in release_notes_data
        assert "CVE-2025-NEW" in release_notes_data["release_notes"]
        assert "CVE-2025-OLD" in release_notes_data["release_notes"]
        assert "high severity" in release_notes_data["release_notes"].lower()

    def test_no_release_workflow_for_unchanged_security(self) -> None:
        """Test workflow when no security changes are detected."""
        # Identical findings
        finding = SecurityFinding(
            finding_id="CVE-2025-SAME",
            package="test-package",
            version="1.0.0",
            severity="medium",
            source_scanner="pip-audit",
            discovered_date=date.today(),
            description="Unchanged vulnerability",
            impact="Medium impact",
            fix_available=False,
        )

        previous_findings = [finding]
        current_findings = [finding]

        # Initialize components
        detector = SecurityChangeDetector()
        engine = ReleaseAutomationEngine()

        # Detect changes (should be none)
        changes = detector.detect_changes(previous_findings, current_findings)
        assert len(changes) == 0

        # Make release decision (should be no release)
        decision = engine.make_release_decision(changes)
        assert decision.should_release is False
        assert decision.trigger_type == ReleaseType.NONE

    def test_manual_release_override_workflow(self) -> None:
        """Test manual release override functionality."""
        # No security changes
        changes = []

        # Initialize components
        engine = ReleaseAutomationEngine()
        notes_generator = ComprehensiveReleaseNotesGenerator()

        # Make manual release decision
        decision = engine.make_release_decision(
            changes, manual_trigger=True, custom_notes="Bug fixes and improvements"
        )

        # Verify manual release decision
        assert decision.should_release is True
        assert decision.trigger_type == ReleaseType.MANUAL
        assert "manual" in decision.justification.lower()

        # Generate manual release notes
        release_notes_data = notes_generator.generate_complete_release_notes(
            release_type=decision.trigger_type,
            security_changes=changes,
            custom_notes="Bug fixes and improvements",
            version="0.2.1",
        )

        # Verify manual release notes
        assert "Manual Release v0.2.1" in release_notes_data["release_notes"]
        assert "Bug fixes and improvements" in release_notes_data["release_notes"]

    def test_vulnerability_resolution_workflow(self) -> None:
        """Test workflow when vulnerabilities are resolved."""
        # Previous findings with vulnerabilities
        previous_findings = [
            SecurityFinding(
                finding_id="CVE-2025-RESOLVED-1",
                package="test-package",
                version="1.0.0",
                severity="high",
                source_scanner="pip-audit",
                discovered_date=date.today(),
                description="Resolved vulnerability 1",
                impact="High impact",
                fix_available=True,
            ),
            SecurityFinding(
                finding_id="CVE-2025-RESOLVED-2",
                package="test-package",
                version="1.0.0",
                severity="medium",
                source_scanner="pip-audit",
                discovered_date=date.today(),
                description="Resolved vulnerability 2",
                impact="Medium impact",
                fix_available=True,
            ),
        ]

        # Current findings (vulnerabilities resolved)
        current_findings = []

        # Initialize components
        detector = SecurityChangeDetector()
        engine = ReleaseAutomationEngine()
        notes_generator = ComprehensiveReleaseNotesGenerator()

        # Detect changes
        changes = detector.detect_changes(previous_findings, current_findings)

        # Verify resolved vulnerabilities detected
        assert len(changes) == 2
        for change in changes:
            assert change.change_type == SecurityChangeType.RESOLVED_VULNERABILITY
            assert change.finding_id in ["CVE-2025-RESOLVED-1", "CVE-2025-RESOLVED-2"]

        # Make release decision
        decision = engine.make_release_decision(changes)

        # Verify release triggered for resolutions
        assert decision.should_release is True
        assert decision.trigger_type == ReleaseType.SECURITY_AUTO
        assert "resolved" in decision.justification.lower()

        # Generate release notes
        release_notes_data = notes_generator.generate_complete_release_notes(
            release_type=decision.trigger_type,
            security_changes=changes,
            version="0.2.1",
        )

        # Verify resolution notes
        assert "Resolved Security Findings" in release_notes_data["release_notes"]
        assert "CVE-2025-RESOLVED-1" in release_notes_data["release_notes"]
        assert "CVE-2025-RESOLVED-2" in release_notes_data["release_notes"]


class TestSecurityPostureAnalysis:
    """Test security posture analysis and decision making."""

    def test_security_posture_improvement_analysis(self) -> None:
        """Test analysis when security posture improves."""
        # Previous findings with high severity
        previous_findings = [
            SecurityFinding(
                finding_id="CVE-2025-HIGH",
                package="test-package",
                version="1.0.0",
                severity="high",
                source_scanner="pip-audit",
                discovered_date=date.today(),
                description="High severity vulnerability",
                impact="High impact",
                fix_available=False,
            ),
            SecurityFinding(
                finding_id="CVE-2025-MEDIUM",
                package="test-package",
                version="1.0.0",
                severity="medium",
                source_scanner="pip-audit",
                discovered_date=date.today(),
                description="Medium severity vulnerability",
                impact="Medium impact",
                fix_available=False,
            ),
        ]

        # Current findings (high severity resolved)
        current_findings = [
            SecurityFinding(
                finding_id="CVE-2025-MEDIUM",
                package="test-package",
                version="1.0.0",
                severity="medium",
                source_scanner="pip-audit",
                discovered_date=date.today(),
                description="Medium severity vulnerability",
                impact="Medium impact",
                fix_available=False,
            ),
        ]

        detector = SecurityChangeDetector()

        # Analyze posture change
        posture_analysis = detector.analyze_security_posture_change(
            previous_findings, current_findings
        )

        # Verify improvement detected
        assert posture_analysis["posture_trend"] == "improved"
        assert posture_analysis["high_critical_change"] == -1
        assert posture_analysis["requires_attention"] is True  # Due to changes

    def test_security_posture_deterioration_analysis(self) -> None:
        """Test analysis when security posture deteriorates."""
        # Previous findings (low severity)
        previous_findings = [
            SecurityFinding(
                finding_id="CVE-2025-LOW",
                package="test-package",
                version="1.0.0",
                severity="low",
                source_scanner="pip-audit",
                discovered_date=date.today(),
                description="Low severity vulnerability",
                impact="Low impact",
                fix_available=False,
            ),
        ]

        # Current findings (new critical vulnerability)
        current_findings = [
            SecurityFinding(
                finding_id="CVE-2025-LOW",
                package="test-package",
                version="1.0.0",
                severity="low",
                source_scanner="pip-audit",
                discovered_date=date.today(),
                description="Low severity vulnerability",
                impact="Low impact",
                fix_available=False,
            ),
            SecurityFinding(
                finding_id="CVE-2025-CRITICAL",
                package="test-package",
                version="1.0.0",
                severity="critical",
                source_scanner="pip-audit",
                discovered_date=date.today(),
                description="Critical vulnerability",
                impact="Critical impact",
                fix_available=False,
            ),
        ]

        detector = SecurityChangeDetector()

        # Analyze posture change
        posture_analysis = detector.analyze_security_posture_change(
            previous_findings, current_findings
        )

        # Verify deterioration detected
        assert posture_analysis["posture_trend"] == "deteriorated"
        assert posture_analysis["high_critical_change"] == 1
        assert posture_analysis["requires_attention"] is True


class TestReleaseDecisionMatrix:
    """Test release decision matrix with various scenarios."""

    def test_critical_vulnerability_triggers_immediate_release(self) -> None:
        """Test that critical vulnerabilities trigger immediate release."""
        changes = [
            SecurityChange(
                change_type=SecurityChangeType.NEW_VULNERABILITY,
                finding_id="CVE-2025-CRITICAL",
                old_state=None,
                new_state="critical vulnerability",
                impact_level="critical",
            )
        ]

        engine = ReleaseAutomationEngine()
        decision = engine.make_release_decision(changes)

        assert decision.should_release is True
        assert decision.trigger_type == ReleaseType.SECURITY_AUTO
        assert "critical" in decision.justification.lower()

    def test_multiple_medium_vulnerabilities_no_automatic_release(self) -> None:
        """Test that multiple medium vulnerabilities don't trigger automatic release."""
        changes = [
            SecurityChange(
                change_type=SecurityChangeType.NEW_VULNERABILITY,
                finding_id="CVE-2025-MED-1",
                old_state=None,
                new_state="medium vulnerability",
                impact_level="medium",
            ),
            SecurityChange(
                change_type=SecurityChangeType.NEW_VULNERABILITY,
                finding_id="CVE-2025-MED-2",
                old_state=None,
                new_state="medium vulnerability",
                impact_level="medium",
            ),
        ]

        engine = ReleaseAutomationEngine()
        decision = engine.make_release_decision(changes)

        # Medium vulnerabilities alone should not trigger automatic release
        assert decision.should_release is False
        assert decision.trigger_type == ReleaseType.NONE

    def test_severity_escalation_triggers_release(self) -> None:
        """Test that severity escalation to high/critical triggers release."""
        changes = [
            SecurityChange(
                change_type=SecurityChangeType.SEVERITY_CHANGE,
                finding_id="CVE-2025-ESCALATED",
                old_state="medium vulnerability",
                new_state="high vulnerability",
                impact_level="high",
            )
        ]

        engine = ReleaseAutomationEngine()
        decision = engine.make_release_decision(changes)

        assert decision.should_release is True
        assert decision.trigger_type == ReleaseType.SECURITY_AUTO
        assert "severity" in decision.justification.lower()


class TestReleaseNotesGeneration:
    """Test comprehensive release notes generation scenarios."""

    def test_mixed_security_changes_release_notes(self) -> None:
        """Test release notes generation with mixed security changes."""
        changes = [
            SecurityChange(
                change_type=SecurityChangeType.NEW_VULNERABILITY,
                finding_id="CVE-2025-NEW-HIGH",
                old_state=None,
                new_state="high vulnerability",
                impact_level="high",
            ),
            SecurityChange(
                change_type=SecurityChangeType.NEW_VULNERABILITY,
                finding_id="CVE-2025-NEW-MEDIUM",
                old_state=None,
                new_state="medium vulnerability",
                impact_level="medium",
            ),
            SecurityChange(
                change_type=SecurityChangeType.RESOLVED_VULNERABILITY,
                finding_id="CVE-2025-RESOLVED",
                old_state="low vulnerability",
                new_state="resolved",
                impact_level="low",
            ),
            SecurityChange(
                change_type=SecurityChangeType.SEVERITY_CHANGE,
                finding_id="CVE-2025-DOWNGRADED",
                old_state="high vulnerability",
                new_state="medium vulnerability",
                impact_level="medium",
            ),
        ]

        generator = ComprehensiveReleaseNotesGenerator()

        release_notes_data = generator.generate_complete_release_notes(
            release_type=ReleaseType.SECURITY_AUTO,
            security_changes=changes,
            version="0.2.1",
        )

        notes = release_notes_data["release_notes"]

        # Verify all sections are present
        assert "New Security Findings" in notes
        assert "Resolved Security Findings" in notes
        assert "Severity Changes" in notes

        # Verify specific findings are mentioned
        assert "CVE-2025-NEW-HIGH" in notes
        assert "CVE-2025-NEW-MEDIUM" in notes
        assert "CVE-2025-RESOLVED" in notes
        assert "CVE-2025-DOWNGRADED" in notes

        # Verify severity grouping
        assert "High/Critical Severity" in notes
        assert "Medium/Low Severity" in notes

    def test_release_notes_file_generation(self) -> None:
        """Test saving release notes to files."""
        changes = [
            SecurityChange(
                change_type=SecurityChangeType.NEW_VULNERABILITY,
                finding_id="CVE-2025-FILE-TEST",
                old_state=None,
                new_state="high vulnerability",
                impact_level="high",
            )
        ]

        generator = ComprehensiveReleaseNotesGenerator()

        release_notes_data = generator.generate_complete_release_notes(
            release_type=ReleaseType.SECURITY_AUTO,
            security_changes=changes,
            version="0.2.1",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            files_created = generator.save_release_notes(release_notes_data, output_dir)

            # Verify all expected files are created
            expected_files = ["release_notes", "justification", "summary"]
            for file_type in expected_files:
                assert file_type in files_created
                assert files_created[file_type].exists()
                assert files_created[file_type].stat().st_size > 0

            # Verify content
            release_notes_content = files_created["release_notes"].read_text()
            assert "CVE-2025-FILE-TEST" in release_notes_content
            assert "Security-Driven Release v0.2.1" in release_notes_content
