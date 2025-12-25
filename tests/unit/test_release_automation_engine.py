"""Tests for release automation engine functionality.

This module tests the ReleaseAutomationEngine class that determines when
releases should be triggered based on security findings changes.
"""

from __future__ import annotations


class TestReleaseAutomationEngine:
    """Test cases for ReleaseAutomationEngine."""

    def test_release_automation_engine_import(self) -> None:
        """Test that ReleaseAutomationEngine can be imported."""
        from scripts.release_automation_engine import ReleaseAutomationEngine

        # Test that we can create an instance
        engine = ReleaseAutomationEngine()
        assert engine is not None

    def test_release_decision_for_new_high_vulnerability(self) -> None:
        """Test release decision when new high severity vulnerability is discovered."""
        from scripts.release_automation_engine import (
            ReleaseAutomationEngine,
            SecurityChange,
            SecurityChangeType,
        )

        engine = ReleaseAutomationEngine()

        # Create a high severity security change
        security_changes = [
            SecurityChange(
                change_type=SecurityChangeType.NEW_VULNERABILITY,
                finding_id="CVE-2025-1234",
                old_state=None,
                new_state="high vulnerability",
                impact_level="high",
            )
        ]

        decision = engine.make_release_decision(security_changes)

        assert decision.should_release is True
        assert decision.trigger_type.value == "security_auto"
        assert "high" in decision.justification.lower()
        assert "CVE-2025-1234" in decision.release_notes

    def test_release_decision_for_resolved_vulnerability(self) -> None:
        """Test release decision when vulnerability is resolved."""
        from scripts.release_automation_engine import (
            ReleaseAutomationEngine,
            SecurityChange,
            SecurityChangeType,
        )

        engine = ReleaseAutomationEngine()

        # Create a resolved vulnerability change
        security_changes = [
            SecurityChange(
                change_type=SecurityChangeType.RESOLVED_VULNERABILITY,
                finding_id="CVE-2025-5678",
                old_state="medium vulnerability",
                new_state="resolved",
                impact_level="medium",
            )
        ]

        decision = engine.make_release_decision(security_changes)

        assert decision.should_release is True
        assert decision.trigger_type.value == "security_auto"
        assert "resolved" in decision.justification.lower()
        assert "CVE-2025-5678" in decision.release_notes

    def test_no_release_for_unchanged_security_status(self) -> None:
        """Test no release when security status remains unchanged."""
        from scripts.release_automation_engine import ReleaseAutomationEngine

        engine = ReleaseAutomationEngine()

        # No security changes
        security_changes = []

        decision = engine.make_release_decision(security_changes)

        assert decision.should_release is False
        assert decision.trigger_type.value == "none"
        assert "no release triggers" in decision.justification.lower()

    def test_manual_release_trigger(self) -> None:
        """Test manual release trigger mechanism."""
        from scripts.release_automation_engine import ReleaseAutomationEngine

        engine = ReleaseAutomationEngine()

        # No security changes but manual trigger
        security_changes = []

        decision = engine.make_release_decision(security_changes, manual_trigger=True)

        assert decision.should_release is True
        assert decision.trigger_type.value == "manual"
        assert "manual" in decision.justification.lower()

    def test_release_justification_generation(self) -> None:
        """Test automatic release notes generation."""
        from scripts.release_automation_engine import (
            ReleaseAutomationEngine,
            SecurityChange,
            SecurityChangeType,
        )

        engine = ReleaseAutomationEngine()

        # Create security changes
        security_changes = [
            SecurityChange(
                change_type=SecurityChangeType.NEW_VULNERABILITY,
                finding_id="CVE-2025-1111",
                old_state=None,
                new_state="critical vulnerability",
                impact_level="critical",
            )
        ]

        decision = engine.make_release_decision(
            security_changes, custom_notes="Custom release notes"
        )

        assert decision.release_notes is not None
        assert len(decision.release_notes) > 0
        assert "CVE-2025-1111" in decision.release_notes
        assert "critical" in decision.release_notes.lower()


class TestReleaseDecisionMatrix:
    """Test cases for release decision matrix logic."""

    def test_decision_matrix_import(self) -> None:
        """Test that ReleaseDecisionMatrix can be imported."""
        from scripts.release_automation_engine import ReleaseDecisionMatrix

        matrix = ReleaseDecisionMatrix()
        assert matrix is not None

    def test_high_severity_vulnerability_triggers_release(self) -> None:
        """Test that high/critical vulnerabilities trigger automatic release."""
        from scripts.release_automation_engine import (
            ReleaseDecisionMatrix,
            ReleaseType,
            SecurityChange,
            SecurityChangeType,
        )

        matrix = ReleaseDecisionMatrix()

        # Test critical vulnerability
        critical_change = SecurityChange(
            change_type=SecurityChangeType.NEW_VULNERABILITY,
            finding_id="CVE-2025-CRIT",
            old_state=None,
            new_state="critical vulnerability",
            impact_level="critical",
        )

        should_release, release_type = matrix.should_trigger_release([critical_change])
        assert should_release is True
        assert release_type == ReleaseType.SECURITY_AUTO

        # Test high vulnerability
        high_change = SecurityChange(
            change_type=SecurityChangeType.NEW_VULNERABILITY,
            finding_id="CVE-2025-HIGH",
            old_state=None,
            new_state="high vulnerability",
            impact_level="high",
        )

        should_release, release_type = matrix.should_trigger_release([high_change])
        assert should_release is True
        assert release_type == ReleaseType.SECURITY_AUTO

    def test_medium_low_vulnerability_no_automatic_release(self) -> None:
        """Test that medium/low vulnerabilities don't trigger automatic release."""
        from scripts.release_automation_engine import (
            ReleaseDecisionMatrix,
            ReleaseType,
            SecurityChange,
            SecurityChangeType,
        )

        matrix = ReleaseDecisionMatrix()

        # Test medium vulnerability
        medium_change = SecurityChange(
            change_type=SecurityChangeType.NEW_VULNERABILITY,
            finding_id="CVE-2025-MED",
            old_state=None,
            new_state="medium vulnerability",
            impact_level="medium",
        )

        should_release, release_type = matrix.should_trigger_release([medium_change])
        assert should_release is False
        assert release_type == ReleaseType.NONE

        # Test low vulnerability
        low_change = SecurityChange(
            change_type=SecurityChangeType.NEW_VULNERABILITY,
            finding_id="CVE-2025-LOW",
            old_state=None,
            new_state="low vulnerability",
            impact_level="low",
        )

        should_release, release_type = matrix.should_trigger_release([low_change])
        assert should_release is False
        assert release_type == ReleaseType.NONE

    def test_vulnerability_resolution_triggers_release(self) -> None:
        """Test that vulnerability resolution triggers release."""
        from scripts.release_automation_engine import (
            ReleaseDecisionMatrix,
            ReleaseType,
            SecurityChange,
            SecurityChangeType,
        )

        matrix = ReleaseDecisionMatrix()

        resolved_change = SecurityChange(
            change_type=SecurityChangeType.RESOLVED_VULNERABILITY,
            finding_id="CVE-2025-RESOLVED",
            old_state="medium vulnerability",
            new_state="resolved",
            impact_level="medium",
        )

        should_release, release_type = matrix.should_trigger_release([resolved_change])
        assert should_release is True
        assert release_type == ReleaseType.SECURITY_AUTO

    def test_manual_trigger_overrides_decision_matrix(self) -> None:
        """Test that manual triggers override automatic decision logic."""
        from scripts.release_automation_engine import ReleaseDecisionMatrix, ReleaseType

        matrix = ReleaseDecisionMatrix()

        # Even with no security changes, manual trigger should work
        should_release, release_type = matrix.should_trigger_release([], manual_trigger=True)
        assert should_release is True
        assert release_type == ReleaseType.MANUAL


class TestReleaseJustificationGenerator:
    """Test cases for release justification and notes generation."""

    def test_justification_generator_import(self) -> None:
        """Test that ReleaseJustificationGenerator can be imported."""
        from scripts.release_automation_engine import ReleaseJustificationGenerator

        generator = ReleaseJustificationGenerator()
        assert generator is not None

    def test_security_driven_release_notes_generation(self) -> None:
        """Test generation of release notes for security-driven releases."""
        from scripts.release_automation_engine import (
            ReleaseJustificationGenerator,
            ReleaseType,
            SecurityChange,
            SecurityChangeType,
        )

        generator = ReleaseJustificationGenerator()

        security_changes = [
            SecurityChange(
                change_type=SecurityChangeType.NEW_VULNERABILITY,
                finding_id="CVE-2025-TEST",
                old_state=None,
                new_state="high vulnerability",
                impact_level="high",
            )
        ]

        notes = generator.generate_release_notes(ReleaseType.SECURITY_AUTO, security_changes)

        assert "Security-Driven Release" in notes
        assert "CVE-2025-TEST" in notes
        assert "high severity" in notes

    def test_manual_release_notes_generation(self) -> None:
        """Test generation of release notes for manual releases."""
        from scripts.release_automation_engine import ReleaseJustificationGenerator, ReleaseType

        generator = ReleaseJustificationGenerator()

        notes = generator.generate_release_notes(ReleaseType.MANUAL, [], "Custom release notes")

        assert "Manual Release" in notes
        assert "Custom release notes" in notes
        assert "Security Status" in notes

    def test_vulnerability_resolution_notes(self) -> None:
        """Test release notes for vulnerability resolution."""
        from scripts.release_automation_engine import (
            ReleaseJustificationGenerator,
            ReleaseType,
            SecurityChange,
            SecurityChangeType,
        )

        generator = ReleaseJustificationGenerator()

        security_changes = [
            SecurityChange(
                change_type=SecurityChangeType.RESOLVED_VULNERABILITY,
                finding_id="CVE-2025-RESOLVED",
                old_state="medium vulnerability",
                new_state="resolved",
                impact_level="medium",
            )
        ]

        notes = generator.generate_release_notes(ReleaseType.SECURITY_AUTO, security_changes)

        assert "Vulnerabilities Resolved" in notes
        assert "CVE-2025-RESOLVED" in notes
        assert "Resolved" in notes

    def test_new_vulnerability_notes(self) -> None:
        """Test release notes for new vulnerability discovery."""
        from scripts.release_automation_engine import (
            ReleaseJustificationGenerator,
            ReleaseType,
            SecurityChange,
            SecurityChangeType,
        )

        generator = ReleaseJustificationGenerator()

        security_changes = [
            SecurityChange(
                change_type=SecurityChangeType.NEW_VULNERABILITY,
                finding_id="CVE-2025-NEW",
                old_state=None,
                new_state="critical vulnerability",
                impact_level="critical",
            )
        ]

        notes = generator.generate_release_notes(ReleaseType.SECURITY_AUTO, security_changes)

        assert "New Vulnerabilities Detected" in notes
        assert "CVE-2025-NEW" in notes
        assert "critical severity" in notes
