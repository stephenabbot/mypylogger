"""Compliance and reporting features for security findings.

This module provides functionality for generating compliance reports,
calculating metrics, and providing audit trail queries for security findings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

try:
    import yaml
except ImportError:
    yaml = None

if TYPE_CHECKING:
    from security.history import HistoricalDataManager
    from security.remediation import RemediationDatastore


@dataclass
class ComplianceMetrics:
    """Compliance metrics for security findings management."""

    report_date: date
    period_days: int
    total_findings: int
    findings_by_severity: dict[str, int] = field(default_factory=dict)
    response_times: dict[str, float] = field(default_factory=dict)
    resolution_rates: dict[str, float] = field(default_factory=dict)
    overdue_findings: int = 0
    sla_compliance_rate: float = 0.0
    mean_time_to_remediation: float = 0.0
    findings_trend: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary representation."""
        return {
            "report_date": self.report_date.isoformat(),
            "period_days": self.period_days,
            "total_findings": self.total_findings,
            "findings_by_severity": self.findings_by_severity,
            "response_times": self.response_times,
            "resolution_rates": self.resolution_rates,
            "overdue_findings": self.overdue_findings,
            "sla_compliance_rate": self.sla_compliance_rate,
            "mean_time_to_remediation": self.mean_time_to_remediation,
            "findings_trend": self.findings_trend,
        }


@dataclass
class FindingLifecycle:
    """Represents the lifecycle of a security finding."""

    finding_id: str
    discovered_date: date
    first_response_date: date | None = None
    resolution_date: date | None = None
    severity: str = "unknown"
    current_status: str = "new"
    days_to_first_response: int | None = None
    days_to_resolution: int | None = None
    is_overdue: bool = False
    sla_target_days: int = 30

    def calculate_metrics(self) -> None:
        """Calculate lifecycle metrics."""
        if self.first_response_date:
            self.days_to_first_response = (self.first_response_date - self.discovered_date).days

        if self.resolution_date:
            self.days_to_resolution = (self.resolution_date - self.discovered_date).days
        else:
            # Check if overdue based on SLA
            days_since_discovery = (datetime.now(timezone.utc).date() - self.discovered_date).days
            self.is_overdue = days_since_discovery > self.sla_target_days

    def to_dict(self) -> dict[str, Any]:
        """Convert lifecycle to dictionary representation."""
        return {
            "finding_id": self.finding_id,
            "discovered_date": self.discovered_date.isoformat(),
            "first_response_date": self.first_response_date.isoformat()
            if self.first_response_date
            else None,
            "resolution_date": self.resolution_date.isoformat() if self.resolution_date else None,
            "severity": self.severity,
            "current_status": self.current_status,
            "days_to_first_response": self.days_to_first_response,
            "days_to_resolution": self.days_to_resolution,
            "is_overdue": self.is_overdue,
            "sla_target_days": self.sla_target_days,
        }


class ComplianceReporter:
    """Generates compliance reports and metrics for security findings."""

    def __init__(
        self,
        datastore: RemediationDatastore | None = None,
        historical_manager: HistoricalDataManager | None = None,
    ) -> None:
        """Initialize the compliance reporter.

        Args:
            datastore: Remediation datastore instance
            historical_manager: Historical data manager instance
        """
        if yaml is None:
            msg = (
                "PyYAML is required for the security module. "
                "Install it with: pip install 'mypylogger[security]' or pip install PyYAML"
            )
            raise ImportError(msg)

        from security.history import get_default_historical_manager
        from security.remediation import get_default_datastore

        self.datastore = datastore or get_default_datastore()
        self.historical_manager = historical_manager or get_default_historical_manager()

        # SLA targets (in days) by severity
        self.sla_targets = {
            "critical": 1,
            "high": 7,
            "medium": 30,
            "low": 90,
            "info": 180,
        }

    def generate_compliance_metrics(self, period_days: int = 30) -> ComplianceMetrics:
        """Generate comprehensive compliance metrics.

        Args:
            period_days: Number of days to analyze

        Returns:
            ComplianceMetrics object with calculated metrics

        Raises:
            RuntimeError: If metrics calculation fails
        """
        try:
            cutoff_date = datetime.now(timezone.utc).date() - timedelta(days=period_days)

            # Get finding lifecycles
            lifecycles = self._get_finding_lifecycles(cutoff_date)

            # Calculate basic metrics
            total_findings = len(lifecycles)
            findings_by_severity = self._calculate_severity_distribution(lifecycles)

            # Calculate response and resolution metrics
            response_times = self._calculate_response_times(lifecycles)
            resolution_rates = self._calculate_resolution_rates(lifecycles)

            # Calculate SLA compliance
            overdue_count = sum(1 for lc in lifecycles if lc.is_overdue)
            sla_compliance_rate = self._calculate_sla_compliance(lifecycles)

            # Calculate mean time to remediation
            mtr = self._calculate_mean_time_to_remediation(lifecycles)

            # Calculate trend data
            findings_trend = self._calculate_findings_trend(period_days)

            return ComplianceMetrics(
                report_date=datetime.now(timezone.utc).date(),
                period_days=period_days,
                total_findings=total_findings,
                findings_by_severity=findings_by_severity,
                response_times=response_times,
                resolution_rates=resolution_rates,
                overdue_findings=overdue_count,
                sla_compliance_rate=sla_compliance_rate,
                mean_time_to_remediation=mtr,
                findings_trend=findings_trend,
            )

        except Exception as e:
            error_msg = f"Failed to generate compliance metrics: {e}"
            raise RuntimeError(error_msg) from e

    def generate_audit_trail_report(self, finding_id: str) -> dict[str, Any]:
        """Generate audit trail report for a specific finding.

        Args:
            finding_id: ID of the finding to generate report for

        Returns:
            Dictionary containing complete audit trail

        Raises:
            RuntimeError: If audit trail generation fails
        """
        try:
            # Get finding lifecycle
            lifecycle = self._get_finding_lifecycle(finding_id)
            if not lifecycle:
                return {"finding_id": finding_id, "error": "Finding not found"}

            # Get historical events
            history = self.historical_manager.get_finding_history(finding_id)

            # Get current remediation plan
            remediation_plan = self.datastore.get_remediation_plan(finding_id)

            # Compile audit trail
            return {
                "finding_id": finding_id,
                "lifecycle": lifecycle.to_dict(),
                "remediation_plan": remediation_plan.to_dict() if remediation_plan else None,
                "historical_events": [
                    event.to_dict() if hasattr(event, "to_dict") else event for event in history
                ],
                "compliance_status": self._assess_compliance_status(lifecycle),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            error_msg = f"Failed to generate audit trail for {finding_id}: {e}"
            raise RuntimeError(error_msg) from e

    def query_findings_by_criteria(self, criteria: dict[str, Any]) -> list[dict[str, Any]]:
        """Query findings based on compliance criteria.

        Args:
            criteria: Dictionary of query criteria

        Returns:
            List of findings matching criteria

        Raises:
            RuntimeError: If query fails
        """
        try:
            # Get all finding lifecycles
            all_lifecycles = self._get_finding_lifecycles()

            # Apply filters based on criteria
            filtered_lifecycles = []

            for lifecycle in all_lifecycles:
                if self._matches_criteria(lifecycle, criteria):
                    filtered_lifecycles.append(lifecycle)

            # Convert to dictionaries and add additional data
            results = []
            for lifecycle in filtered_lifecycles:
                result = lifecycle.to_dict()

                # Add remediation plan data if requested
                if criteria.get("include_remediation", False):
                    plan = self.datastore.get_remediation_plan(lifecycle.finding_id)
                    result["remediation_plan"] = plan.to_dict() if plan else None

                results.append(result)

            return results

        except Exception as e:
            error_msg = f"Failed to query findings: {e}"
            raise RuntimeError(error_msg) from e

    def _get_finding_lifecycles(self, cutoff_date: date | None = None) -> list[FindingLifecycle]:
        """Get finding lifecycles from historical data."""
        try:
            lifecycles = []

            # Read timeline data
            if not self.historical_manager.timeline_file.exists():
                return lifecycles

            with self.historical_manager.timeline_file.open("r", encoding="utf-8") as f:
                timeline_data = yaml.safe_load(f) or {}

            findings_data = timeline_data.get("findings", {})
            remediation_data = timeline_data.get("remediation", {})

            for finding_id, finding_info in findings_data.items():
                try:
                    # Parse discovery date
                    first_discovered = finding_info.get("first_discovered")
                    if not first_discovered:
                        continue

                    discovered_date = datetime.fromisoformat(
                        first_discovered.replace("Z", "+00:00")
                    ).date()

                    # Skip if before cutoff date
                    if cutoff_date and discovered_date < cutoff_date:
                        continue

                    # Create lifecycle object
                    lifecycle = FindingLifecycle(
                        finding_id=finding_id,
                        discovered_date=discovered_date,
                    )

                    # Extract additional data from events
                    events = finding_info.get("events", [])
                    for event in events:
                        if isinstance(event, dict):
                            # Extract severity from discovery event
                            if event.get("event_type") == "discovered" and event.get("new_data"):
                                lifecycle.severity = event["new_data"].get("severity", "unknown")

                    # Get remediation data
                    if finding_id in remediation_data:
                        rem_info = remediation_data[finding_id]
                        rem_events = rem_info.get("events", [])

                        for event in rem_events:
                            if isinstance(event, dict) and "timestamp" in event:
                                try:
                                    event_date = datetime.fromisoformat(
                                        event["timestamp"].replace("Z", "+00:00")
                                    ).date()

                                    # First response (plan creation)
                                    if (
                                        event.get("event_type") == "created"
                                        and not lifecycle.first_response_date
                                    ):
                                        lifecycle.first_response_date = event_date

                                    # Resolution
                                    if (
                                        event.get("event_type") == "status_changed"
                                        and event.get("new_status") == "completed"
                                    ):
                                        lifecycle.resolution_date = event_date
                                        lifecycle.current_status = "completed"

                                    # Update current status
                                    if event.get("new_status"):
                                        lifecycle.current_status = event["new_status"]

                                except (ValueError, TypeError):
                                    continue

                    # Set SLA target based on severity
                    lifecycle.sla_target_days = self.sla_targets.get(lifecycle.severity, 30)

                    # Calculate metrics
                    lifecycle.calculate_metrics()

                    lifecycles.append(lifecycle)

                except Exception:
                    # Skip malformed entries
                    continue

            return lifecycles

        except Exception as e:
            error_msg = f"Failed to get finding lifecycles: {e}"
            raise RuntimeError(error_msg) from e

    def _get_finding_lifecycle(self, finding_id: str) -> FindingLifecycle | None:
        """Get lifecycle for a specific finding."""
        lifecycles = self._get_finding_lifecycles()
        for lifecycle in lifecycles:
            if lifecycle.finding_id == finding_id:
                return lifecycle
        return None

    def _calculate_severity_distribution(
        self, lifecycles: list[FindingLifecycle]
    ) -> dict[str, int]:
        """Calculate distribution of findings by severity."""
        distribution = {}
        for lifecycle in lifecycles:
            severity = lifecycle.severity
            distribution[severity] = distribution.get(severity, 0) + 1
        return distribution

    def _calculate_response_times(self, lifecycles: list[FindingLifecycle]) -> dict[str, float]:
        """Calculate average response times by severity."""
        response_times = {}
        severity_totals = {}
        severity_counts = {}

        for lifecycle in lifecycles:
            if lifecycle.days_to_first_response is not None:
                severity = lifecycle.severity
                if severity not in severity_totals:
                    severity_totals[severity] = 0
                    severity_counts[severity] = 0

                severity_totals[severity] += lifecycle.days_to_first_response
                severity_counts[severity] += 1

        for severity in severity_totals:
            if severity_counts[severity] > 0:
                response_times[severity] = severity_totals[severity] / severity_counts[severity]

        return response_times

    def _calculate_resolution_rates(self, lifecycles: list[FindingLifecycle]) -> dict[str, float]:
        """Calculate resolution rates by severity."""
        resolution_rates = {}
        severity_totals = {}
        severity_resolved = {}

        for lifecycle in lifecycles:
            severity = lifecycle.severity
            if severity not in severity_totals:
                severity_totals[severity] = 0
                severity_resolved[severity] = 0

            severity_totals[severity] += 1
            if lifecycle.resolution_date is not None:
                severity_resolved[severity] += 1

        for severity in severity_totals:
            if severity_totals[severity] > 0:
                resolution_rates[severity] = (
                    severity_resolved[severity] / severity_totals[severity]
                ) * 100

        return resolution_rates

    def _calculate_sla_compliance(self, lifecycles: list[FindingLifecycle]) -> float:
        """Calculate overall SLA compliance rate."""
        if not lifecycles:
            return 100.0

        compliant_count = 0
        total_count = len(lifecycles)

        for lifecycle in lifecycles:
            # Consider compliant if resolved within SLA or not yet overdue
            if lifecycle.resolution_date:
                # Resolved - check if within SLA
                if (
                    lifecycle.days_to_resolution
                    and lifecycle.days_to_resolution <= lifecycle.sla_target_days
                ):
                    compliant_count += 1
            elif not lifecycle.is_overdue:
                # Not resolved but not overdue yet
                compliant_count += 1

        return (compliant_count / total_count) * 100

    def _calculate_mean_time_to_remediation(self, lifecycles: list[FindingLifecycle]) -> float:
        """Calculate mean time to remediation for resolved findings."""
        resolution_times = []

        for lifecycle in lifecycles:
            if lifecycle.days_to_resolution is not None:
                resolution_times.append(lifecycle.days_to_resolution)

        if not resolution_times:
            return 0.0

        return sum(resolution_times) / len(resolution_times)

    def _calculate_findings_trend(self, period_days: int) -> dict[str, int]:
        """Calculate findings trend over the period."""
        # Simplified implementation - could be enhanced with weekly/monthly breakdowns
        cutoff_date = datetime.now(timezone.utc).date() - timedelta(days=period_days)

        recent_lifecycles = self._get_finding_lifecycles(cutoff_date)
        older_lifecycles = self._get_finding_lifecycles()

        return {
            "current_period": len(recent_lifecycles),
            "total_historical": len(older_lifecycles),
            "trend_direction": "increasing" if len(recent_lifecycles) > 0 else "stable",
        }

    def _assess_compliance_status(self, lifecycle: FindingLifecycle) -> dict[str, Any]:
        """Assess compliance status for a finding."""
        status = {
            "is_compliant": True,
            "issues": [],
            "recommendations": [],
        }

        # Check response time compliance
        if lifecycle.first_response_date is None:
            days_since_discovery = (
                datetime.now(timezone.utc).date() - lifecycle.discovered_date
            ).days
            if days_since_discovery > 1:  # Should respond within 1 day
                status["is_compliant"] = False
                status["issues"].append("No initial response recorded")
                status["recommendations"].append("Create remediation plan immediately")

        # Check SLA compliance
        if lifecycle.is_overdue:
            status["is_compliant"] = False
            status["issues"].append(f"Finding is overdue (>{lifecycle.sla_target_days} days)")
            status["recommendations"].append("Escalate for immediate attention")

        # Check resolution status for old findings
        if not lifecycle.resolution_date:
            days_open = (datetime.now(timezone.utc).date() - lifecycle.discovered_date).days
            if days_open > lifecycle.sla_target_days:
                status["recommendations"].append("Review remediation progress and update timeline")

        return status

    def _matches_criteria(self, lifecycle: FindingLifecycle, criteria: dict[str, Any]) -> bool:
        """Check if a lifecycle matches the given criteria."""
        # Severity filter
        if "severity" in criteria:
            if isinstance(criteria["severity"], list):
                if lifecycle.severity not in criteria["severity"]:
                    return False
            elif lifecycle.severity != criteria["severity"]:
                return False

        # Status filter
        if "status" in criteria:
            if isinstance(criteria["status"], list):
                if lifecycle.current_status not in criteria["status"]:
                    return False
            elif lifecycle.current_status != criteria["status"]:
                return False

        # Overdue filter
        if "overdue" in criteria and criteria["overdue"] != lifecycle.is_overdue:
            return False

        # Date range filter
        if "date_from" in criteria:
            date_from = datetime.fromisoformat(criteria["date_from"]).date()
            if lifecycle.discovered_date < date_from:
                return False

        if "date_to" in criteria:
            date_to = datetime.fromisoformat(criteria["date_to"]).date()
            if lifecycle.discovered_date > date_to:
                return False

        return True


def get_default_compliance_reporter() -> ComplianceReporter:
    """Get the default compliance reporter instance."""
    return ComplianceReporter()
