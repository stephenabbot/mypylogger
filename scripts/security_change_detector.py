"""Security change detection system for release automation.

This module implements the SecurityChangeDetector that compares security findings
over time and identifies changes that may trigger releases.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from scripts.release_automation_engine import SecurityChange, SecurityChangeType
from security.parsers import extract_all_findings
from security.remediation import RemediationDatastore

if TYPE_CHECKING:
    from security.models import SecurityFinding


class SecurityChangeDetector:
    """Detects changes in security findings over time."""

    def __init__(
        self,
        datastore: RemediationDatastore | None = None,
        reports_dir: Path | None = None,
    ) -> None:
        """Initialize the security change detector.

        Args:
            datastore: Remediation datastore for accessing historical data
            reports_dir: Directory containing security reports
        """
        self.datastore = datastore or RemediationDatastore()
        self.reports_dir = reports_dir or Path("security/reports/latest")
        self.historical_dir = Path("security/reports/archived")

    def detect_changes(
        self,
        previous_findings: list[SecurityFinding],
        current_findings: list[SecurityFinding],
    ) -> list[SecurityChange]:
        """Detect changes between previous and current security findings.

        Args:
            previous_findings: Previous security findings for comparison
            current_findings: Current security findings

        Returns:
            List of detected security changes
        """
        changes = []

        # Create lookup dictionaries for efficient comparison
        previous_dict = {f.finding_id: f for f in previous_findings}
        current_dict = {f.finding_id: f for f in current_findings}

        # Detect new vulnerabilities
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

        # Detect resolved vulnerabilities
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

        # Detect severity changes
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

    def load_current_findings(self) -> list[SecurityFinding]:
        """Load current security findings from Phase 6 system.

        Returns:
            List of current security findings
        """
        try:
            if not self.reports_dir.exists():
                return []

            return extract_all_findings(self.reports_dir)
        except Exception as e:
            error_msg = f"Failed to load current findings: {e}"
            raise RuntimeError(error_msg) from e

    def load_previous_findings(self, days_back: int = 7) -> list[SecurityFinding]:
        """Load previous security findings for comparison.

        Args:
            days_back: Number of days back to look for previous findings

        Returns:
            List of previous security findings
        """
        try:
            # Look for archived findings from specified days back
            datetime.now(timezone.utc).date()

            # Try to find the most recent archived findings
            if self.historical_dir.exists():
                # Look for archived findings files
                archived_files = list(self.historical_dir.glob("**/pip-audit.json"))
                if archived_files:
                    # Use the most recent archived findings
                    most_recent = max(archived_files, key=lambda p: p.stat().st_mtime)
                    return extract_all_findings(most_recent.parent)

            # If no archived findings, return empty list (treat as first scan)
            return []

        except Exception as e:
            # If we can't load previous findings, treat as first scan
            print(f"Warning: Could not load previous findings: {e}")
            return []

    def detect_changes_from_current_scan(self, days_back: int = 7) -> list[SecurityChange]:
        """Detect changes from current scan compared to previous scan.

        Args:
            days_back: Number of days back to compare against

        Returns:
            List of detected security changes
        """
        try:
            current_findings = self.load_current_findings()
            previous_findings = self.load_previous_findings(days_back)

            return self.detect_changes(previous_findings, current_findings)

        except Exception as e:
            error_msg = f"Failed to detect changes from current scan: {e}"
            raise RuntimeError(error_msg) from e

    def get_findings_summary(self, findings: list[SecurityFinding]) -> dict[str, Any]:
        """Get summary statistics for security findings.

        Args:
            findings: List of security findings

        Returns:
            Dictionary with summary statistics
        """
        if not findings:
            return {
                "total": 0,
                "by_severity": {},
                "by_scanner": {},
                "high_critical_count": 0,
            }

        # Count by severity
        severity_counts = {}
        for finding in findings:
            severity = finding.severity.lower()
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        # Count by scanner
        scanner_counts = {}
        for finding in findings:
            scanner = finding.source_scanner
            scanner_counts[scanner] = scanner_counts.get(scanner, 0) + 1

        # Count high/critical
        high_critical_count = sum(1 for f in findings if f.severity.lower() in {"high", "critical"})

        return {
            "total": len(findings),
            "by_severity": severity_counts,
            "by_scanner": scanner_counts,
            "high_critical_count": high_critical_count,
        }

    def analyze_security_posture_change(
        self,
        previous_findings: list[SecurityFinding],
        current_findings: list[SecurityFinding],
    ) -> dict[str, Any]:
        """Analyze overall security posture change.

        Args:
            previous_findings: Previous security findings
            current_findings: Current security findings

        Returns:
            Dictionary with security posture analysis
        """
        previous_summary = self.get_findings_summary(previous_findings)
        current_summary = self.get_findings_summary(current_findings)

        changes = self.detect_changes(previous_findings, current_findings)

        # Calculate posture change
        total_change = current_summary["total"] - previous_summary["total"]
        high_critical_change = (
            current_summary["high_critical_count"] - previous_summary["high_critical_count"]
        )

        # Determine posture trend
        if high_critical_change > 0:
            posture_trend = "deteriorated"
        elif high_critical_change < 0:
            posture_trend = "improved"
        elif total_change > 0:
            posture_trend = "slightly_deteriorated"
        elif total_change < 0:
            posture_trend = "slightly_improved"
        else:
            posture_trend = "unchanged"

        return {
            "previous_summary": previous_summary,
            "current_summary": current_summary,
            "changes": [change.__dict__ for change in changes],
            "total_change": total_change,
            "high_critical_change": high_critical_change,
            "posture_trend": posture_trend,
            "requires_attention": high_critical_change > 0 or len(changes) > 0,
        }


def get_default_detector() -> SecurityChangeDetector:
    """Get a default security change detector instance."""
    return SecurityChangeDetector()


def detect_security_changes(
    days_back: int = 7,
    reports_dir: Path | None = None,
) -> list[SecurityChange]:
    """Detect security changes from current scan.

    Args:
        days_back: Number of days back to compare against
        reports_dir: Directory containing security reports

    Returns:
        List of detected security changes
    """
    detector = SecurityChangeDetector(reports_dir=reports_dir)
    return detector.detect_changes_from_current_scan(days_back)
