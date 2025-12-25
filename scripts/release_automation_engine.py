"""Release automation engine for security-driven PyPI publishing.

This module implements the core logic for determining when releases should be
triggered based on security findings changes and generating appropriate
release justifications.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from security.models import SecurityFinding


class ReleaseType(Enum):
    """Types of releases that can be triggered."""

    SECURITY_AUTO = "security_auto"
    MANUAL = "manual"
    NONE = "none"


class SecurityChangeType(Enum):
    """Types of security changes that can trigger releases."""

    NEW_VULNERABILITY = "new_vulnerability"
    RESOLVED_VULNERABILITY = "resolved"
    SEVERITY_CHANGE = "severity_change"
    NO_CHANGE = "no_change"


@dataclass
class SecurityChange:
    """Represents a change in security findings."""

    change_type: SecurityChangeType
    finding_id: str
    old_state: str | None
    new_state: str
    impact_level: str

    def __post_init__(self) -> None:
        """Validate security change data."""
        if not self.finding_id:
            msg = "finding_id cannot be empty"
            raise ValueError(msg)

        if not self.new_state:
            msg = "new_state cannot be empty"
            raise ValueError(msg)

        valid_impacts = {"critical", "high", "medium", "low", "info"}
        if self.impact_level.lower() not in valid_impacts:
            msg = f"impact_level must be one of {valid_impacts}"
            raise ValueError(msg)


@dataclass
class ReleaseDecision:
    """Represents a decision about whether to trigger a release."""

    should_release: bool
    trigger_type: ReleaseType
    justification: str
    security_changes: list[SecurityChange]
    release_notes: str

    def __post_init__(self) -> None:
        """Validate release decision data."""
        if not isinstance(self.should_release, bool):
            msg = "should_release must be a boolean"
            raise ValueError(msg)

        if not isinstance(self.trigger_type, ReleaseType):
            msg = "trigger_type must be a ReleaseType enum"
            raise ValueError(msg)

    def to_dict(self) -> dict[str, Any]:
        """Convert release decision to dictionary for JSON serialization."""
        return {
            "should_release": self.should_release,
            "trigger_type": self.trigger_type.value,
            "justification": self.justification,
            "release_notes": self.release_notes,
            "security_changes_count": len(self.security_changes),
            "security_changes": [
                {
                    "change_type": change.change_type.value,
                    "finding_id": change.finding_id,
                    "old_state": change.old_state,
                    "new_state": change.new_state,
                    "impact_level": change.impact_level,
                }
                for change in self.security_changes
            ],
        }


class ReleaseDecisionMatrix:
    """Decision matrix for determining when releases should be triggered."""

    def __init__(self) -> None:
        """Initialize the decision matrix with default rules."""
        self.auto_release_severities = {"critical", "high"}
        self.resolution_triggers_release = True
        self.manual_override_enabled = True

    def should_trigger_release(
        self,
        security_changes: list[SecurityChange],
        manual_trigger: bool = False,
    ) -> tuple[bool, ReleaseType]:
        """Determine if a release should be triggered.

        Args:
            security_changes: List of security changes detected
            manual_trigger: Whether this is a manual release request

        Returns:
            Tuple of (should_release, release_type)
        """
        # Manual trigger always overrides automatic logic
        if manual_trigger:
            return True, ReleaseType.MANUAL

        # Check for automatic release triggers
        for change in security_changes:
            # New high/critical vulnerabilities trigger automatic release
            if (
                change.change_type == SecurityChangeType.NEW_VULNERABILITY
                and change.impact_level.lower() in self.auto_release_severities
            ):
                return True, ReleaseType.SECURITY_AUTO

            # Resolved vulnerabilities trigger release
            if (
                change.change_type == SecurityChangeType.RESOLVED_VULNERABILITY
                and self.resolution_triggers_release
            ):
                return True, ReleaseType.SECURITY_AUTO

            # Severity changes to high/critical trigger release
            if (
                change.change_type == SecurityChangeType.SEVERITY_CHANGE
                and change.impact_level.lower() in self.auto_release_severities
            ):
                return True, ReleaseType.SECURITY_AUTO

        # No triggers found
        return False, ReleaseType.NONE

    def get_trigger_reason(
        self,
        security_changes: list[SecurityChange],
        release_type: ReleaseType,
    ) -> str:
        """Get human-readable reason for the release trigger.

        Args:
            security_changes: List of security changes
            release_type: Type of release being triggered

        Returns:
            Human-readable trigger reason
        """
        if release_type == ReleaseType.MANUAL:
            return "Manual release requested"

        if release_type == ReleaseType.NONE:
            return "No release triggers detected"

        # Analyze security changes for automatic releases
        high_new = [
            c
            for c in security_changes
            if c.change_type == SecurityChangeType.NEW_VULNERABILITY
            and c.impact_level.lower() in self.auto_release_severities
        ]

        resolved = [
            c
            for c in security_changes
            if c.change_type == SecurityChangeType.RESOLVED_VULNERABILITY
        ]

        severity_increases = [
            c
            for c in security_changes
            if c.change_type == SecurityChangeType.SEVERITY_CHANGE
            and c.impact_level.lower() in self.auto_release_severities
        ]

        reasons = []
        if high_new:
            count = len(high_new)
            reasons.append(f"{count} new high/critical vulnerabilit{'y' if count == 1 else 'ies'}")

        if resolved:
            count = len(resolved)
            reasons.append(f"{count} vulnerabilit{'y' if count == 1 else 'ies'} resolved")

        if severity_increases:
            count = len(severity_increases)
            reasons.append(
                f"{count} severit{'y' if count == 1 else 'ies'} increased to high/critical"
            )

        if reasons:
            return f"Security-driven release: {', '.join(reasons)}"

        return "Automatic security release triggered"


class ReleaseJustificationGenerator:
    """Generates release notes and justifications for different release types."""

    def __init__(self) -> None:
        """Initialize the justification generator."""
        self.templates = {
            "security_auto": self._security_auto_template,
            "manual": self._manual_template,
            "vulnerability_resolution": self._resolution_template,
            "new_vulnerability": self._new_vulnerability_template,
        }

    def generate_release_notes(
        self,
        release_type: ReleaseType,
        security_changes: list[SecurityChange],
        custom_notes: str | None = None,
    ) -> str:
        """Generate release notes based on release type and changes.

        Args:
            release_type: Type of release being made
            security_changes: List of security changes
            custom_notes: Optional custom notes to include

        Returns:
            Formatted release notes
        """
        if release_type == ReleaseType.MANUAL:
            return self._generate_manual_notes(custom_notes)

        if release_type == ReleaseType.SECURITY_AUTO:
            return self._generate_security_notes(security_changes)

        return "Release notes not available"

    def _generate_manual_notes(self, custom_notes: str | None) -> str:
        """Generate notes for manual releases."""
        base_notes = """## Manual Release

This release was triggered manually and may include:
- Code improvements and bug fixes
- Feature enhancements
- Documentation updates
- Dependency updates

"""

        if custom_notes:
            base_notes += f"## Release Notes\n\n{custom_notes}\n\n"

        base_notes += "## Security Status\n\nSee the live security status for current vulnerability information.\n"

        return base_notes

    def _generate_security_notes(self, security_changes: list[SecurityChange]) -> str:
        """Generate notes for security-driven releases."""
        notes = "## Security-Driven Release\n\n"
        notes += "This release was automatically triggered due to security findings changes.\n\n"

        # Group changes by type
        new_vulns = [
            c for c in security_changes if c.change_type == SecurityChangeType.NEW_VULNERABILITY
        ]
        resolved_vulns = [
            c
            for c in security_changes
            if c.change_type == SecurityChangeType.RESOLVED_VULNERABILITY
        ]
        severity_changes = [
            c for c in security_changes if c.change_type == SecurityChangeType.SEVERITY_CHANGE
        ]

        if new_vulns:
            notes += "### New Vulnerabilities Detected\n\n"
            for change in new_vulns:
                notes += f"- **{change.finding_id}**: {change.impact_level} severity\n"
            notes += "\n"

        if resolved_vulns:
            notes += "### Vulnerabilities Resolved\n\n"
            for change in resolved_vulns:
                notes += f"- **{change.finding_id}**: Resolved\n"
            notes += "\n"

        if severity_changes:
            notes += "### Severity Changes\n\n"
            for change in severity_changes:
                notes += f"- **{change.finding_id}**: Changed to {change.impact_level} severity\n"
            notes += "\n"

        notes += "## Security Documentation\n\n"
        notes += "For detailed security information, see:\n"
        notes += "- [Security Findings Document](security/findings/SECURITY_FINDINGS.md)\n"
        notes += "- [Live Security Status](https://username.github.io/mypylogger/security-status)\n"

        return notes

    def _security_auto_template(self, **kwargs: Any) -> str:
        """Template for automatic security releases."""
        return "Security-driven automatic release"

    def _manual_template(self, **kwargs: Any) -> str:
        """Template for manual releases."""
        return "Manual release"

    def _resolution_template(self, **kwargs: Any) -> str:
        """Template for vulnerability resolution releases."""
        return "Vulnerability resolution release"

    def _new_vulnerability_template(self, **kwargs: Any) -> str:
        """Template for new vulnerability releases."""
        return "New vulnerability detection release"


class ReleaseAutomationEngine:
    """Main engine for release automation decisions and execution."""

    def __init__(
        self,
        decision_matrix: ReleaseDecisionMatrix | None = None,
        justification_generator: ReleaseJustificationGenerator | None = None,
    ) -> None:
        """Initialize the release automation engine.

        Args:
            decision_matrix: Custom decision matrix. If None, uses default.
            justification_generator: Custom justification generator. If None, uses default.
        """
        self.decision_matrix = decision_matrix or ReleaseDecisionMatrix()
        self.justification_generator = justification_generator or ReleaseJustificationGenerator()

    def analyze_security_changes(
        self,
        current_findings: list[SecurityFinding],
        previous_findings: list[SecurityFinding] | None = None,
    ) -> list[SecurityChange]:
        """Analyze security findings to detect changes.

        Args:
            current_findings: Current security findings
            previous_findings: Previous security findings for comparison

        Returns:
            List of detected security changes
        """
        if previous_findings is None:
            # If no previous findings, treat all current findings as new
            return [
                SecurityChange(
                    change_type=SecurityChangeType.NEW_VULNERABILITY,
                    finding_id=finding.finding_id,
                    old_state=None,
                    new_state=f"{finding.severity} vulnerability",
                    impact_level=finding.severity,
                )
                for finding in current_findings
            ]

        changes = []

        # Create lookup dictionaries
        current_dict = {f.finding_id: f for f in current_findings}
        previous_dict = {f.finding_id: f for f in previous_findings}

        # Find new vulnerabilities
        for finding_id, finding in current_dict.items():
            if finding_id not in previous_dict:
                changes.append(
                    SecurityChange(
                        change_type=SecurityChangeType.NEW_VULNERABILITY,
                        finding_id=finding_id,
                        old_state=None,
                        new_state=f"{finding.severity} vulnerability",
                        impact_level=finding.severity,
                    )
                )

        # Find resolved vulnerabilities
        for finding_id, finding in previous_dict.items():
            if finding_id not in current_dict:
                changes.append(
                    SecurityChange(
                        change_type=SecurityChangeType.RESOLVED_VULNERABILITY,
                        finding_id=finding_id,
                        old_state=f"{finding.severity} vulnerability",
                        new_state="resolved",
                        impact_level=finding.severity,
                    )
                )

        # Find severity changes
        for finding_id in current_dict:
            if finding_id in previous_dict:
                current_severity = current_dict[finding_id].severity.lower()
                previous_severity = previous_dict[finding_id].severity.lower()

                if current_severity != previous_severity:
                    changes.append(
                        SecurityChange(
                            change_type=SecurityChangeType.SEVERITY_CHANGE,
                            finding_id=finding_id,
                            old_state=f"{previous_severity} vulnerability",
                            new_state=f"{current_severity} vulnerability",
                            impact_level=current_severity,
                        )
                    )

        return changes

    def make_release_decision(
        self,
        security_changes: list[SecurityChange],
        manual_trigger: bool = False,
        custom_notes: str | None = None,
    ) -> ReleaseDecision:
        """Make a decision about whether to trigger a release.

        Args:
            security_changes: List of detected security changes
            manual_trigger: Whether this is a manual release request
            custom_notes: Optional custom release notes

        Returns:
            ReleaseDecision with recommendation and justification
        """
        # Get decision from matrix
        should_release, release_type = self.decision_matrix.should_trigger_release(
            security_changes, manual_trigger
        )

        # Generate justification
        justification = self.decision_matrix.get_trigger_reason(security_changes, release_type)

        # Generate release notes
        release_notes = self.justification_generator.generate_release_notes(
            release_type, security_changes, custom_notes
        )

        return ReleaseDecision(
            should_release=should_release,
            trigger_type=release_type,
            justification=justification,
            security_changes=security_changes,
            release_notes=release_notes,
        )

    def process_security_update(
        self,
        current_findings: list[SecurityFinding],
        previous_findings: list[SecurityFinding] | None = None,
        manual_trigger: bool = False,
        custom_notes: str | None = None,
    ) -> ReleaseDecision:
        """Process a security update and make release decision.

        Args:
            current_findings: Current security findings
            previous_findings: Previous security findings for comparison
            manual_trigger: Whether this is a manual release request
            custom_notes: Optional custom release notes

        Returns:
            ReleaseDecision with complete analysis and recommendation
        """
        # Analyze changes
        security_changes = self.analyze_security_changes(current_findings, previous_findings)

        # Make decision
        return self.make_release_decision(security_changes, manual_trigger, custom_notes)


def get_default_engine() -> ReleaseAutomationEngine:
    """Get a default release automation engine instance."""
    return ReleaseAutomationEngine()
