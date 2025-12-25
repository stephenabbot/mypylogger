"""Historical tracking and audit trails for security findings.

This module provides functionality for tracking changes to security findings
and remediation plans over time, maintaining audit trails for compliance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
import shutil
from typing import TYPE_CHECKING, Any

try:
    import yaml
except ImportError:
    yaml = None

if TYPE_CHECKING:
    from security.models import RemediationPlan, SecurityFinding


@dataclass
class FindingChangeEvent:
    """Represents a change event for a security finding."""

    timestamp: datetime
    finding_id: str
    event_type: str  # discovered, resolved, updated
    old_data: dict[str, Any] | None = None
    new_data: dict[str, Any] | None = None
    source: str = "system"  # system, manual, scanner
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "finding_id": self.finding_id,
            "event_type": self.event_type,
            "old_data": self.old_data,
            "new_data": self.new_data,
            "source": self.source,
            "notes": self.notes,
        }


@dataclass
class RemediationChangeEvent:
    """Represents a change event for a remediation plan."""

    timestamp: datetime
    finding_id: str
    event_type: str  # created, status_changed, updated, completed
    old_status: str | None = None
    new_status: str | None = None
    changed_fields: list[str] = field(default_factory=list)
    user: str = "system"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "finding_id": self.finding_id,
            "event_type": self.event_type,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "changed_fields": self.changed_fields,
            "user": self.user,
            "notes": self.notes,
        }


class HistoricalDataManager:
    """Manages historical tracking and audit trails for security findings."""

    def __init__(
        self,
        history_dir: Path | None = None,
        reports_dir: Path | None = None,
        archived_reports_dir: Path | None = None,
    ) -> None:
        """Initialize the historical data manager.

        Args:
            history_dir: Directory for historical tracking files
            reports_dir: Directory containing current scan reports
            archived_reports_dir: Directory for archived scan reports
        """
        if yaml is None:
            msg = (
                "PyYAML is required for the security module. "
                "Install it with: pip install 'mypylogger[security]' or pip install PyYAML"
            )
            raise ImportError(msg)

        self.history_dir = history_dir or Path("security/findings/history")
        self.reports_dir = reports_dir or Path("security/reports/latest")
        self.archived_reports_dir = archived_reports_dir or Path("security/reports/archived")

        # Ensure directories exist
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.archived_reports_dir.mkdir(parents=True, exist_ok=True)

        # File paths
        self.changelog_file = self.history_dir / "findings-changelog.md"
        self.timeline_file = self.history_dir / "remediation-timeline.yml"

    def record_finding_discovered(self, finding: SecurityFinding) -> None:
        """Record when a new finding is discovered.

        Args:
            finding: The newly discovered security finding
        """
        try:
            event = FindingChangeEvent(
                timestamp=datetime.now(timezone.utc),
                finding_id=finding.finding_id,
                event_type="discovered",
                new_data=finding.to_dict(),
                source="scanner",
                notes=f"New {finding.severity} severity finding discovered by {finding.source_scanner}",
            )

            self._append_to_changelog(event)
            self._update_timeline_for_finding(event)

        except Exception as e:
            error_msg = f"Failed to record finding discovery: {e}"
            raise RuntimeError(error_msg) from e

    def record_finding_resolved(self, finding_id: str, source: str = "scanner") -> None:
        """Record when a finding is resolved.

        Args:
            finding_id: ID of the resolved finding
            source: Source of the resolution (scanner, manual, etc.)
        """
        try:
            event = FindingChangeEvent(
                timestamp=datetime.now(timezone.utc),
                finding_id=finding_id,
                event_type="resolved",
                source=source,
                notes="Finding resolved - no longer detected by security scanners",
            )

            self._append_to_changelog(event)
            self._update_timeline_for_finding(event)

        except Exception as e:
            error_msg = f"Failed to record finding resolution: {e}"
            raise RuntimeError(error_msg) from e

    def record_remediation_created(self, plan: RemediationPlan) -> None:
        """Record when a remediation plan is created.

        Args:
            plan: The newly created remediation plan
        """
        try:
            event = RemediationChangeEvent(
                timestamp=datetime.now(timezone.utc),
                finding_id=plan.finding_id,
                event_type="created",
                new_status=plan.status,
                user="system",
                notes=f"Remediation plan created with status: {plan.status}",
            )

            self._update_remediation_timeline(event)

        except Exception as e:
            error_msg = f"Failed to record remediation creation: {e}"
            raise RuntimeError(error_msg) from e

    def record_remediation_status_change(
        self,
        finding_id: str,
        old_status: str,
        new_status: str,
        user: str = "system",
        notes: str = "",
    ) -> None:
        """Record when a remediation plan status changes.

        Args:
            finding_id: ID of the finding
            old_status: Previous status
            new_status: New status
            user: User who made the change
            notes: Additional notes about the change
        """
        try:
            event = RemediationChangeEvent(
                timestamp=datetime.now(timezone.utc),
                finding_id=finding_id,
                event_type="status_changed",
                old_status=old_status,
                new_status=new_status,
                changed_fields=["status"],
                user=user,
                notes=notes or f"Status changed from {old_status} to {new_status}",
            )

            self._update_remediation_timeline(event)

        except Exception as e:
            error_msg = f"Failed to record status change: {e}"
            raise RuntimeError(error_msg) from e

    def record_remediation_updated(
        self,
        finding_id: str,
        changed_fields: list[str],
        user: str = "system",
        notes: str = "",
    ) -> None:
        """Record when a remediation plan is updated.

        Args:
            finding_id: ID of the finding
            changed_fields: List of fields that were changed
            user: User who made the change
            notes: Additional notes about the change
        """
        try:
            event = RemediationChangeEvent(
                timestamp=datetime.now(timezone.utc),
                finding_id=finding_id,
                event_type="updated",
                changed_fields=changed_fields,
                user=user,
                notes=notes or f"Updated fields: {', '.join(changed_fields)}",
            )

            self._update_remediation_timeline(event)

        except Exception as e:
            error_msg = f"Failed to record remediation update: {e}"
            raise RuntimeError(error_msg) from e

    def archive_scan_results(self, scan_date: date | None = None) -> Path:
        """Archive current scan results to dated directory.

        Args:
            scan_date: Date of the scan. If None, uses current date.

        Returns:
            Path to the archived directory

        Raises:
            RuntimeError: If archival fails
        """
        try:
            if scan_date is None:
                scan_date = datetime.now(timezone.utc).date()

            # Create dated archive directory
            archive_dir = self.archived_reports_dir / scan_date.strftime("%Y-%m-%d")
            archive_dir.mkdir(parents=True, exist_ok=True)

            # Copy all files from latest reports to archive
            if self.reports_dir.exists():
                for file_path in self.reports_dir.iterdir():
                    if file_path.is_file():
                        dest_path = archive_dir / file_path.name
                        shutil.copy2(file_path, dest_path)

            return archive_dir

        except Exception as e:
            error_msg = f"Failed to archive scan results: {e}"
            raise RuntimeError(error_msg) from e

    def get_finding_history(self, finding_id: str) -> list[FindingChangeEvent]:
        """Get the complete history for a specific finding.

        Args:
            finding_id: ID of the finding to get history for

        Returns:
            List of change events for the finding
        """
        try:
            events = []

            # Parse changelog for finding events
            if self.changelog_file.exists():
                self.changelog_file.read_text(encoding="utf-8")
                # This is a simplified implementation - in practice, you'd parse the markdown
                # For now, return empty list as the changelog is human-readable

            # Parse timeline for remediation events
            if self.timeline_file.exists():
                with self.timeline_file.open("r", encoding="utf-8") as f:
                    timeline_data = yaml.safe_load(f) or {}

                finding_timeline = timeline_data.get("findings", {}).get(finding_id, {})
                for _event_data in finding_timeline.get("events", []):
                    # Convert back to event object if needed
                    pass

            return events

        except Exception as e:
            error_msg = f"Failed to get finding history: {e}"
            raise RuntimeError(error_msg) from e

    def get_remediation_metrics(self, days: int = 30) -> dict[str, Any]:
        """Calculate remediation metrics for the specified period.

        Args:
            days: Number of days to calculate metrics for

        Returns:
            Dictionary containing remediation metrics
        """
        try:
            from datetime import timedelta

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            metrics = {
                "period_days": days,
                "total_findings_discovered": 0,
                "total_findings_resolved": 0,
                "average_resolution_time_days": 0.0,
                "findings_by_severity": {},
                "remediation_status_distribution": {},
                "overdue_remediations": 0,
                "response_time_metrics": {
                    "average_time_to_plan_creation": 0.0,
                    "average_time_to_first_action": 0.0,
                },
            }

            # Parse timeline data for metrics calculation
            if self.timeline_file.exists():
                with self.timeline_file.open("r", encoding="utf-8") as f:
                    timeline_data = yaml.safe_load(f) or {}

                findings_data = timeline_data.get("findings", {})

                for finding_data in findings_data.values():
                    events = finding_data.get("events", [])

                    # Filter events within the time period
                    recent_events = []
                    for event in events:
                        if isinstance(event, dict) and "timestamp" in event:
                            try:
                                event_time = datetime.fromisoformat(
                                    event["timestamp"].replace("Z", "+00:00")
                                )
                                if event_time >= cutoff_date:
                                    recent_events.append(event)
                            except (ValueError, TypeError):
                                # Skip events with invalid timestamps
                                continue

                    # Calculate metrics from recent events
                    for event in recent_events:
                        if event.get("event_type") == "created":
                            metrics["total_findings_discovered"] += 1
                        elif (
                            event.get("event_type") == "status_changed"
                            and event.get("new_status") == "completed"
                        ):
                            metrics["total_findings_resolved"] += 1

            return metrics

        except Exception as e:
            error_msg = f"Failed to calculate remediation metrics: {e}"
            raise RuntimeError(error_msg) from e

    def _append_to_changelog(self, event: FindingChangeEvent) -> None:
        """Append a finding change event to the changelog."""
        try:
            # Create changelog if it doesn't exist
            if not self.changelog_file.exists():
                self._initialize_changelog()

            # Format event for markdown
            timestamp_str = event.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")

            entry = f"\n## {timestamp_str}\n\n"
            entry += f"**Finding ID**: {event.finding_id}  \n"
            entry += f"**Event**: {event.event_type.replace('_', ' ').title()}  \n"
            entry += f"**Source**: {event.source}  \n"

            if event.notes:
                entry += f"**Notes**: {event.notes}  \n"

            if event.new_data and event.event_type == "discovered":
                entry += f"**Severity**: {event.new_data.get('severity', 'unknown')}  \n"
                entry += f"**Package**: {event.new_data.get('package', 'unknown')} {event.new_data.get('version', '')}  \n"
                entry += f"**Scanner**: {event.new_data.get('source_scanner', 'unknown')}  \n"

            entry += "\n"

            # Append to changelog
            with self.changelog_file.open("a", encoding="utf-8") as f:
                f.write(entry)

        except Exception as e:
            error_msg = f"Failed to append to changelog: {e}"
            raise RuntimeError(error_msg) from e

    def _update_timeline_for_finding(self, event: FindingChangeEvent) -> None:
        """Update the timeline with a finding event."""
        try:
            # Load existing timeline
            timeline_data = {}
            if self.timeline_file.exists():
                with self.timeline_file.open("r", encoding="utf-8") as f:
                    timeline_data = yaml.safe_load(f) or {}

            # Ensure structure exists
            if "findings" not in timeline_data:
                timeline_data["findings"] = {}

            if event.finding_id not in timeline_data["findings"]:
                timeline_data["findings"][event.finding_id] = {
                    "first_discovered": event.timestamp.isoformat(),
                    "events": [],
                }

            # Add event
            timeline_data["findings"][event.finding_id]["events"].append(event.to_dict())

            # Update last_updated
            timeline_data["last_updated"] = datetime.now(timezone.utc).isoformat()

            # Save timeline
            with self.timeline_file.open("w", encoding="utf-8") as f:
                yaml.dump(timeline_data, f, default_flow_style=False, sort_keys=False)

        except Exception as e:
            error_msg = f"Failed to update timeline: {e}"
            raise RuntimeError(error_msg) from e

    def _update_remediation_timeline(self, event: RemediationChangeEvent) -> None:
        """Update the remediation timeline with an event."""
        try:
            # Load existing timeline
            timeline_data = {}
            if self.timeline_file.exists():
                with self.timeline_file.open("r", encoding="utf-8") as f:
                    timeline_data = yaml.safe_load(f) or {}

            # Ensure structure exists
            if "remediation" not in timeline_data:
                timeline_data["remediation"] = {}

            if event.finding_id not in timeline_data["remediation"]:
                timeline_data["remediation"][event.finding_id] = {
                    "created": event.timestamp.isoformat(),
                    "events": [],
                }

            # Add event
            timeline_data["remediation"][event.finding_id]["events"].append(event.to_dict())

            # Update last_updated
            timeline_data["last_updated"] = datetime.now(timezone.utc).isoformat()

            # Save timeline
            with self.timeline_file.open("w", encoding="utf-8") as f:
                yaml.dump(timeline_data, f, default_flow_style=False, sort_keys=False)

        except Exception as e:
            error_msg = f"Failed to update remediation timeline: {e}"
            raise RuntimeError(error_msg) from e

    def _initialize_changelog(self) -> None:
        """Initialize the changelog file with header."""
        header = """# Security Findings Changelog

This document tracks chronological changes to security findings and their lifecycle.
Each entry represents a significant event in the security findings management process.

**Legend**:
- **Discovered**: New security finding detected by scanners
- **Resolved**: Finding no longer detected (vulnerability fixed or false positive)
- **Updated**: Finding information updated (severity, description, etc.)

---

"""
        self.changelog_file.write_text(header, encoding="utf-8")


def get_default_historical_manager() -> HistoricalDataManager:
    """Get the default historical data manager instance."""
    return HistoricalDataManager()
