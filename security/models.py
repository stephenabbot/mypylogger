"""Security finding and remediation data models.

This module defines the core data structures for security vulnerability tracking
and remediation planning within the security module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
import re
from urllib.parse import urlparse


@dataclass
class SecurityFinding:
    """Represents a security vulnerability finding from scanner output.

    This dataclass encapsulates all information about a security vulnerability
    discovered by security scanning tools like pip-audit, bandit, or secrets scanning.
    """

    finding_id: str
    package: str
    version: str
    severity: str
    source_scanner: str
    discovered_date: date
    description: str
    impact: str
    fix_available: bool
    fix_version: str | None = None
    cvss_score: float | None = None
    reference_url: str | None = None

    def __post_init__(self) -> None:
        """Validate data integrity after initialization."""
        self._validate_finding_id()
        self._validate_severity()
        self._validate_cvss_score()
        self._validate_reference_url()
        self._validate_required_fields()

    def _validate_finding_id(self) -> None:
        """Validate finding_id format and content."""
        if not self.finding_id or not isinstance(self.finding_id, str):
            msg = "finding_id must be a non-empty string"
            raise ValueError(msg)

        # Check for common vulnerability ID patterns
        valid_patterns = [
            r"^CVE-\d{4}-\d{4,}$",  # CVE format
            r"^GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}$",  # GitHub Security Advisory
            r"^PYSEC-\d{4}-\d+$",  # PyUp Security
            r"^RUSTSEC-\d{4}-\d{4}$",  # RustSec Advisory
        ]

        # Allow custom format for bandit/secrets findings
        if not any(re.match(pattern, self.finding_id) for pattern in valid_patterns):
            # For non-standard IDs, ensure they're reasonable
            if len(self.finding_id) < 3 or len(self.finding_id) > 100:
                msg = (
                    f"finding_id '{self.finding_id}' must be 3-100 characters or match "
                    "standard vulnerability ID format (CVE, GHSA, PYSEC, etc.)"
                )
                raise ValueError(msg)

    def _validate_severity(self) -> None:
        """Validate severity level."""
        valid_severities = {"critical", "high", "medium", "low", "info", "unknown"}
        if self.severity.lower() not in valid_severities:
            msg = f"severity must be one of {valid_severities}, got '{self.severity}'"
            raise ValueError(msg)
        # Normalize to lowercase
        self.severity = self.severity.lower()

    def _validate_cvss_score(self) -> None:
        """Validate CVSS score range."""
        if self.cvss_score is not None:
            if not isinstance(self.cvss_score, (int, float)):
                msg = "cvss_score must be a number"
                raise ValueError(msg)
            if not 0.0 <= self.cvss_score <= 10.0:
                msg = "cvss_score must be between 0.0 and 10.0"
                raise ValueError(msg)

    def _validate_reference_url(self) -> None:
        """Validate reference URL format."""
        if self.reference_url is not None:
            if not isinstance(self.reference_url, str):
                msg = "reference_url must be a string"
                raise ValueError(msg)

            # Basic URL validation
            try:
                parsed = urlparse(self.reference_url)
                if not parsed.scheme or not parsed.netloc:
                    msg = f"reference_url must be a valid URL, got '{self.reference_url}'"
                    raise ValueError(msg)
            except Exception as e:
                msg = f"Invalid reference_url: {e}"
                raise ValueError(msg) from e

    def _validate_required_fields(self) -> None:
        """Validate all required fields are present and valid."""
        required_string_fields = {
            "package": self.package,
            "version": self.version,
            "source_scanner": self.source_scanner,
            "description": self.description,
            "impact": self.impact,
        }

        for field_name, field_value in required_string_fields.items():
            if not field_value or not isinstance(field_value, str):
                msg = f"{field_name} must be a non-empty string"
                raise ValueError(msg)

        # Validate discovered_date
        if not isinstance(self.discovered_date, date):
            msg = "discovered_date must be a date object"
            raise ValueError(msg)

        # Validate fix_available
        if not isinstance(self.fix_available, bool):
            msg = "fix_available must be a boolean"
            raise ValueError(msg)

    def days_since_discovery(self) -> int:
        """Calculate days since vulnerability was discovered."""
        today = datetime.now(timezone.utc).date()
        return (today - self.discovered_date).days

    def is_high_severity(self) -> bool:
        """Check if finding is high or critical severity."""
        return self.severity.lower() in {"critical", "high"}

    def to_dict(self) -> dict:
        """Convert finding to dictionary representation."""
        return {
            "finding_id": self.finding_id,
            "package": self.package,
            "version": self.version,
            "severity": self.severity,
            "source_scanner": self.source_scanner,
            "discovered_date": self.discovered_date.isoformat(),
            "description": self.description,
            "impact": self.impact,
            "fix_available": self.fix_available,
            "fix_version": self.fix_version,
            "cvss_score": self.cvss_score,
            "reference_url": self.reference_url,
        }


@dataclass
class RemediationPlan:
    """Represents a remediation plan for a security finding.

    This dataclass tracks the planned response and current status of remediation
    efforts for a specific security vulnerability.
    """

    finding_id: str
    status: str
    planned_action: str
    assigned_to: str
    notes: str
    workaround: str
    target_date: date | None = None
    priority: str = "medium"
    business_impact: str = "unknown"
    created_date: date = field(default_factory=date.today)
    updated_date: date = field(default_factory=date.today)

    def __post_init__(self) -> None:
        """Validate data integrity after initialization."""
        self._validate_finding_id()
        self._validate_status()
        self._validate_priority()
        self._validate_required_fields()
        self._validate_dates()

    def _validate_finding_id(self) -> None:
        """Validate finding_id matches SecurityFinding validation."""
        if not self.finding_id or not isinstance(self.finding_id, str):
            msg = "finding_id must be a non-empty string"
            raise ValueError(msg)

        # Use same validation as SecurityFinding
        valid_patterns = [
            r"^CVE-\d{4}-\d{4,}$",
            r"^GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}$",
            r"^PYSEC-\d{4}-\d+$",
            r"^RUSTSEC-\d{4}-\d{4}$",
        ]

        if not any(re.match(pattern, self.finding_id) for pattern in valid_patterns):
            if len(self.finding_id) < 3 or len(self.finding_id) > 100:
                msg = (
                    f"finding_id '{self.finding_id}' must be 3-100 characters or match "
                    "standard vulnerability ID format"
                )
                raise ValueError(msg)

    def _validate_status(self) -> None:
        """Validate remediation status."""
        valid_statuses = {
            "new",
            "in_progress",
            "awaiting_upstream",
            "completed",
            "deferred",
            "accepted_risk",
            "false_positive",
        }
        if self.status.lower() not in valid_statuses:
            msg = f"status must be one of {valid_statuses}, got '{self.status}'"
            raise ValueError(msg)
        # Normalize to lowercase
        self.status = self.status.lower()

    def _validate_priority(self) -> None:
        """Validate priority level."""
        valid_priorities = {"critical", "high", "medium", "low"}
        if self.priority.lower() not in valid_priorities:
            msg = f"priority must be one of {valid_priorities}, got '{self.priority}'"
            raise ValueError(msg)
        # Normalize to lowercase
        self.priority = self.priority.lower()

    def _validate_required_fields(self) -> None:
        """Validate all required fields are present and valid."""
        required_string_fields = {
            "planned_action": self.planned_action,
            "assigned_to": self.assigned_to,
            "notes": self.notes,
            "workaround": self.workaround,
            "business_impact": self.business_impact,
        }

        for field_name, field_value in required_string_fields.items():
            if not isinstance(field_value, str):
                msg = f"{field_name} must be a string"
                raise ValueError(msg)
            # Allow empty strings for some fields, but not None

    def _validate_dates(self) -> None:
        """Validate date fields."""
        date_fields = {
            "created_date": self.created_date,
            "updated_date": self.updated_date,
        }

        for field_name, field_value in date_fields.items():
            if not isinstance(field_value, date):
                msg = f"{field_name} must be a date object"
                raise ValueError(msg)

        if self.target_date is not None and not isinstance(self.target_date, date):
            msg = "target_date must be a date object or None"
            raise ValueError(msg)

        # Logical date validation
        if self.updated_date < self.created_date:
            msg = "updated_date cannot be before created_date"
            raise ValueError(msg)

    def is_overdue(self) -> bool:
        """Check if remediation is past target date."""
        if self.target_date is None:
            return False
        return datetime.now(timezone.utc).date() > self.target_date and self.status != "completed"

    def days_until_target(self) -> int | None:
        """Calculate days until target date (negative if overdue)."""
        if self.target_date is None:
            return None
        return (self.target_date - datetime.now(timezone.utc).date()).days

    def update_status(self, new_status: str, notes: str | None = None) -> None:
        """Update remediation status and timestamp."""
        old_status = self.status
        self.status = new_status
        self.updated_date = datetime.now(timezone.utc).date()

        if notes:
            if self.notes:
                self.notes += f"\n[{datetime.now(timezone.utc).date()}] Status changed from {old_status} to {new_status}: {notes}"
            else:
                self.notes = f"[{datetime.now(timezone.utc).date()}] Status changed from {old_status} to {new_status}: {notes}"

        # Re-validate after update
        self._validate_status()

    def to_dict(self) -> dict:
        """Convert remediation plan to dictionary representation."""
        return {
            "finding_id": self.finding_id,
            "status": self.status,
            "planned_action": self.planned_action,
            "assigned_to": self.assigned_to,
            "notes": self.notes,
            "workaround": self.workaround,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "priority": self.priority,
            "business_impact": self.business_impact,
            "created_date": self.created_date.isoformat(),
            "updated_date": self.updated_date.isoformat(),
        }


def create_default_remediation_plan(finding_id: str) -> RemediationPlan:
    """Create a default remediation plan for a new finding.

    Args:
        finding_id: The unique identifier for the security finding

    Returns:
        RemediationPlan with default values for new findings
    """
    return RemediationPlan(
        finding_id=finding_id,
        status="new",
        planned_action="Under evaluation",
        assigned_to="security-team",
        notes="Newly discovered - assessment in progress",
        workaround="None identified",
        priority="medium",
        business_impact="Under assessment",
    )
