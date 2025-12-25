"""Live security status data management for GitHub Pages API.

This module provides functionality to create and manage live security status
data that can be served via GitHub Pages as a JSON API endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from security.parsers import extract_all_findings

if TYPE_CHECKING:
    from security.models import SecurityFinding


@dataclass
class VulnerabilitySummary:
    """Summary of vulnerabilities by severity level."""

    total: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0

    def __post_init__(self) -> None:
        """Validate summary data after initialization."""
        if any(
            count < 0
            for count in [self.total, self.critical, self.high, self.medium, self.low, self.info]
        ):
            msg = "Vulnerability counts cannot be negative"
            raise ValueError(msg)

        # Validate total matches sum of individual counts
        calculated_total = self.critical + self.high + self.medium + self.low + self.info
        if self.total != calculated_total:
            msg = f"Total count ({self.total}) does not match sum of individual counts ({calculated_total})"
            raise ValueError(msg)

    @classmethod
    def from_findings(cls, findings: list[SecurityFinding]) -> VulnerabilitySummary:
        """Create vulnerability summary from security findings.

        Args:
            findings: List of security findings to summarize.

        Returns:
            VulnerabilitySummary with counts by severity.
        """
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}

        for finding in findings:
            severity = finding.severity.lower()
            if severity in counts:
                counts[severity] += 1

        total = sum(counts.values())

        return cls(
            total=total,
            critical=counts["critical"],
            high=counts["high"],
            medium=counts["medium"],
            low=counts["low"],
            info=counts["info"],
        )

    def to_dict(self) -> dict[str, int]:
        """Convert to dictionary representation."""
        return {
            "total": self.total,
            "critical": self.critical,
            "high": self.high,
            "medium": self.medium,
            "low": self.low,
            "info": self.info,
        }


@dataclass
class SecurityStatusFinding:
    """Simplified security finding for live status API."""

    finding_id: str
    package: str
    version: str
    severity: str
    discovered_date: str  # ISO format string
    days_since_discovery: int
    description: str
    fix_available: bool
    fix_version: str | None = None
    reference_url: str | None = None

    @classmethod
    def from_security_finding(cls, finding: SecurityFinding) -> SecurityStatusFinding:
        """Create status finding from security finding.

        Args:
            finding: SecurityFinding to convert.

        Returns:
            SecurityStatusFinding for API response.
        """
        return cls(
            finding_id=finding.finding_id,
            package=finding.package,
            version=finding.version,
            severity=finding.severity,
            discovered_date=finding.discovered_date.isoformat(),
            days_since_discovery=finding.days_since_discovery(),
            description=finding.description,
            fix_available=finding.fix_available,
            fix_version=finding.fix_version,
            reference_url=finding.reference_url,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "finding_id": self.finding_id,
            "package": self.package,
            "version": self.version,
            "severity": self.severity,
            "discovered_date": self.discovered_date,
            "days_since_discovery": self.days_since_discovery,
            "description": self.description,
            "fix_available": self.fix_available,
            "fix_version": self.fix_version,
            "reference_url": self.reference_url,
        }


@dataclass
class SecurityStatus:
    """Live security status data model for GitHub Pages API."""

    last_updated: datetime
    scan_date: datetime
    vulnerability_summary: VulnerabilitySummary
    findings: list[SecurityStatusFinding] = field(default_factory=list)
    security_grade: str = "A"
    days_since_last_vulnerability: int = 0
    remediation_status: str = "current"

    def __post_init__(self) -> None:
        """Validate security status data after initialization."""
        self._validate_timestamps()
        self._validate_security_grade()
        self._validate_remediation_status()

    def _validate_timestamps(self) -> None:
        """Validate timestamp fields."""
        if not isinstance(self.last_updated, datetime):
            msg = "last_updated must be a datetime object"
            raise ValueError(msg)

        if not isinstance(self.scan_date, datetime):
            msg = "scan_date must be a datetime object"
            raise ValueError(msg)

        # Ensure timestamps are timezone-aware
        if self.last_updated.tzinfo is None:
            msg = "last_updated must be timezone-aware"
            raise ValueError(msg)

        if self.scan_date.tzinfo is None:
            msg = "scan_date must be timezone-aware"
            raise ValueError(msg)

    def _validate_security_grade(self) -> None:
        """Validate security grade."""
        valid_grades = {"A", "B", "C", "D", "F"}
        if self.security_grade not in valid_grades:
            msg = f"security_grade must be one of {valid_grades}, got '{self.security_grade}'"
            raise ValueError(msg)

    def _validate_remediation_status(self) -> None:
        """Validate remediation status."""
        valid_statuses = {"current", "outdated", "pending", "unknown"}
        if self.remediation_status not in valid_statuses:
            msg = f"remediation_status must be one of {valid_statuses}, got '{self.remediation_status}'"
            raise ValueError(msg)

    @classmethod
    def from_findings(cls, findings: list[SecurityFinding]) -> SecurityStatus:
        """Create security status from security findings.

        Args:
            findings: List of current security findings.

        Returns:
            SecurityStatus with calculated metrics.
        """
        now = datetime.now(timezone.utc)

        # Create vulnerability summary
        vulnerability_summary = VulnerabilitySummary.from_findings(findings)

        # Convert findings to status findings
        status_findings = [SecurityStatusFinding.from_security_finding(f) for f in findings]

        # Calculate security grade
        security_grade = cls._calculate_security_grade(vulnerability_summary)

        # Calculate days since last vulnerability
        days_since_last_vulnerability = cls._calculate_days_since_last_vulnerability(findings)

        # Determine remediation status
        remediation_status = cls._determine_remediation_status(vulnerability_summary)

        return cls(
            last_updated=now,
            scan_date=now,  # Assume current scan
            vulnerability_summary=vulnerability_summary,
            findings=status_findings,
            security_grade=security_grade,
            days_since_last_vulnerability=days_since_last_vulnerability,
            remediation_status=remediation_status,
        )

    @staticmethod
    def _calculate_security_grade(summary: VulnerabilitySummary) -> str:
        """Calculate security grade based on vulnerability summary.

        Args:
            summary: Vulnerability summary to grade.

        Returns:
            Security grade (A-F).
        """
        # Grade based on severity and count of vulnerabilities
        if summary.critical > 0:
            return "F"  # Any critical vulnerability = F
        if summary.high > 2:
            return "D"  # More than 2 high vulnerabilities = D
        if summary.high > 0:
            return "C"  # Any high vulnerability = C
        if summary.medium > 5:
            return "C"  # More than 5 medium vulnerabilities = C
        if summary.medium > 0:
            return "B"  # Any medium vulnerability = B
        if summary.low > 10:
            return "B"  # More than 10 low vulnerabilities = B
        return "A"  # No significant vulnerabilities = A

    @staticmethod
    def _calculate_days_since_last_vulnerability(findings: list[SecurityFinding]) -> int:
        """Calculate days since the most recent vulnerability was discovered.

        Args:
            findings: List of security findings.

        Returns:
            Days since most recent vulnerability, or 0 if any exist.
        """
        if not findings:
            # No vulnerabilities - could return a large number, but 0 is safer
            return 0

        # Find the most recent discovery date
        most_recent = max(finding.discovered_date for finding in findings)
        today = datetime.now(timezone.utc).date()

        return (today - most_recent).days

    @staticmethod
    def _determine_remediation_status(summary: VulnerabilitySummary) -> str:
        """Determine overall remediation status.

        Args:
            summary: Vulnerability summary.

        Returns:
            Remediation status string.
        """
        if summary.total == 0:
            return "current"
        if summary.critical > 0 or summary.high > 0 or summary.medium > 0:
            return "pending"
        return "current"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation for JSON serialization."""
        return {
            "last_updated": self.last_updated.isoformat(),
            "scan_date": self.scan_date.isoformat(),
            "vulnerability_summary": self.vulnerability_summary.to_dict(),
            "findings": [finding.to_dict() for finding in self.findings],
            "security_grade": self.security_grade,
            "days_since_last_vulnerability": self.days_since_last_vulnerability,
            "remediation_status": self.remediation_status,
        }

    def to_json(self, indent: int | None = 2) -> str:
        """Convert to JSON string.

        Args:
            indent: JSON indentation level.

        Returns:
            JSON string representation.
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class SecurityStatusManager:
    """Manages live security status data and updates."""

    def __init__(
        self,
        reports_dir: Path | None = None,
        status_file: Path | None = None,
    ) -> None:
        """Initialize security status manager.

        Args:
            reports_dir: Directory containing security reports.
            status_file: Path to live status JSON file.
        """
        self.reports_dir = reports_dir or Path("security/reports/latest")
        self.status_file = status_file or Path("security-status/index.json")

    def update_status(self) -> SecurityStatus:
        """Update live security status from current findings.

        Returns:
            Updated SecurityStatus object.

        Raises:
            RuntimeError: If status update fails.
        """
        try:
            # Get current findings
            findings = self._get_current_findings()

            # Create security status
            status = SecurityStatus.from_findings(findings)

            # Save to file
            self._save_status(status)

            return status

        except Exception as e:
            error_msg = f"Failed to update security status: {e}"
            raise RuntimeError(error_msg) from e

    def get_current_status(self) -> SecurityStatus | None:
        """Get current security status from file.

        Returns:
            Current SecurityStatus or None if not available.
        """
        try:
            if not self.status_file.exists():
                return None

            with self.status_file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            return self._status_from_dict(data)

        except Exception:
            # Return None if status cannot be loaded
            return None

    def _get_current_findings(self) -> list[SecurityFinding]:
        """Get current security findings from reports.

        Returns:
            List of current security findings.
        """
        try:
            if not self.reports_dir.exists():
                return []

            return extract_all_findings(self.reports_dir)

        except Exception as e:
            error_msg = f"Failed to extract current findings: {e}"
            raise RuntimeError(error_msg) from e

    def _save_status(self, status: SecurityStatus) -> None:
        """Save security status to JSON file.

        Args:
            status: SecurityStatus to save.
        """
        try:
            # Ensure directory exists
            self.status_file.parent.mkdir(parents=True, exist_ok=True)

            # Write JSON file
            with self.status_file.open("w", encoding="utf-8") as f:
                f.write(status.to_json())

        except Exception as e:
            error_msg = f"Failed to save security status: {e}"
            raise RuntimeError(error_msg) from e

    def _status_from_dict(self, data: dict[str, Any]) -> SecurityStatus:
        """Create SecurityStatus from dictionary data.

        Args:
            data: Dictionary data from JSON.

        Returns:
            SecurityStatus object.
        """
        # Parse timestamps
        last_updated = datetime.fromisoformat(data["last_updated"])
        scan_date = datetime.fromisoformat(data["scan_date"])

        # Parse vulnerability summary
        summary_data = data["vulnerability_summary"]
        vulnerability_summary = VulnerabilitySummary(**summary_data)

        # Parse findings
        findings = []
        for finding_data in data.get("findings", []):
            finding = SecurityStatusFinding(**finding_data)
            findings.append(finding)

        return SecurityStatus(
            last_updated=last_updated,
            scan_date=scan_date,
            vulnerability_summary=vulnerability_summary,
            findings=findings,
            security_grade=data.get("security_grade", "A"),
            days_since_last_vulnerability=data.get("days_since_last_vulnerability", 0),
            remediation_status=data.get("remediation_status", "current"),
        )


def get_default_status_manager() -> SecurityStatusManager:
    """Get default security status manager instance.

    Returns:
        SecurityStatusManager with default configuration.
    """
    return SecurityStatusManager()


def update_live_security_status(
    reports_dir: Path | None = None,
    status_file: Path | None = None,
) -> SecurityStatus:
    """Update live security status with optional custom parameters.

    Args:
        reports_dir: Directory containing security reports.
        status_file: Path to live status JSON file.

    Returns:
        Updated SecurityStatus object.
    """
    manager = SecurityStatusManager(reports_dir, status_file)
    return manager.update_status()
