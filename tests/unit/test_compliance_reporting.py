"""Tests for compliance and reporting functionality."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch

import pytest
import yaml

from security.compliance import (
    ComplianceMetrics,
    ComplianceReporter,
    FindingLifecycle,
    get_default_compliance_reporter,
)
from security.history import HistoricalDataManager
from security.models import RemediationPlan
from security.remediation import RemediationDatastore


class TestComplianceMetrics:
    """Test ComplianceMetrics data model."""

    def test_compliance_metrics_creation(self) -> None:
        """Test creating compliance metrics."""
        report_date = datetime.now(timezone.utc).date()
        metrics = ComplianceMetrics(
            report_date=report_date,
            period_days=30,
            total_findings=10,
            findings_by_severity={"high": 3, "medium": 7},
            overdue_findings=2,
            sla_compliance_rate=80.0,
        )

        assert metrics.report_date == report_date
        assert metrics.period_days == 30
        assert metrics.total_findings == 10
        assert metrics.findings_by_severity == {"high": 3, "medium": 7}
        assert metrics.overdue_findings == 2
        assert metrics.sla_compliance_rate == 80.0

    def test_compliance_metrics_to_dict(self) -> None:
        """Test converting compliance metrics to dictionary."""
        report_date = datetime.now(timezone.utc).date()
        metrics = ComplianceMetrics(
            report_date=report_date,
            period_days=30,
            total_findings=5,
        )

        result = metrics.to_dict()

        assert result["report_date"] == report_date.isoformat()
        assert result["period_days"] == 30
        assert result["total_findings"] == 5
        assert "findings_by_severity" in result
        assert "response_times" in result


class TestFindingLifecycle:
    """Test FindingLifecycle data model."""

    def test_finding_lifecycle_creation(self) -> None:
        """Test creating finding lifecycle."""
        discovered_date = datetime.now(timezone.utc).date()
        lifecycle = FindingLifecycle(
            finding_id="CVE-2025-1234",
            discovered_date=discovered_date,
            severity="high",
            current_status="in_progress",
        )

        assert lifecycle.finding_id == "CVE-2025-1234"
        assert lifecycle.discovered_date == discovered_date
        assert lifecycle.severity == "high"
        assert lifecycle.current_status == "in_progress"

    def test_finding_lifecycle_calculate_metrics(self) -> None:
        """Test calculating lifecycle metrics."""
        discovered_date = date(2025, 10, 1)
        first_response_date = date(2025, 10, 2)
        resolution_date = date(2025, 10, 10)

        lifecycle = FindingLifecycle(
            finding_id="CVE-2025-1234",
            discovered_date=discovered_date,
            first_response_date=first_response_date,
            resolution_date=resolution_date,
        )

        lifecycle.calculate_metrics()

        assert lifecycle.days_to_first_response == 1
        assert lifecycle.days_to_resolution == 9
        assert not lifecycle.is_overdue

    def test_finding_lifecycle_overdue_calculation(self) -> None:
        """Test overdue calculation for unresolved findings."""
        # Create a finding from 60 days ago (should be overdue with default 30-day SLA)
        old_date = datetime.now(timezone.utc).date() - timedelta(days=60)

        lifecycle = FindingLifecycle(
            finding_id="CVE-2025-1234",
            discovered_date=old_date,
            sla_target_days=30,
        )

        lifecycle.calculate_metrics()

        assert lifecycle.is_overdue

    def test_finding_lifecycle_to_dict(self) -> None:
        """Test converting lifecycle to dictionary."""
        discovered_date = datetime.now(timezone.utc).date()
        lifecycle = FindingLifecycle(
            finding_id="CVE-2025-1234",
            discovered_date=discovered_date,
            severity="medium",
        )

        result = lifecycle.to_dict()

        assert result["finding_id"] == "CVE-2025-1234"
        assert result["discovered_date"] == discovered_date.isoformat()
        assert result["severity"] == "medium"
        assert result["first_response_date"] is None
        assert result["resolution_date"] is None


class TestComplianceReporter:
    """Test ComplianceReporter functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())

        # Create mock datastore
        self.mock_datastore = Mock(spec=RemediationDatastore)

        # Create historical manager with temp directory
        self.historical_manager = HistoricalDataManager(
            history_dir=self.temp_dir / "history",
            reports_dir=self.temp_dir / "reports" / "latest",
            archived_reports_dir=self.temp_dir / "reports" / "archived",
        )

        self.reporter = ComplianceReporter(
            datastore=self.mock_datastore,
            historical_manager=self.historical_manager,
        )

    def test_reporter_initialization(self) -> None:
        """Test compliance reporter initialization."""
        assert self.reporter.datastore == self.mock_datastore
        assert self.reporter.historical_manager == self.historical_manager
        assert "critical" in self.reporter.sla_targets
        assert self.reporter.sla_targets["critical"] == 1
        assert self.reporter.sla_targets["high"] == 7

    def test_generate_compliance_metrics_empty_data(self) -> None:
        """Test generating metrics with no data."""
        # Ensure timeline file doesn't exist
        if self.historical_manager.timeline_file.exists():
            self.historical_manager.timeline_file.unlink()

        metrics = self.reporter.generate_compliance_metrics(30)

        assert isinstance(metrics, ComplianceMetrics)
        assert metrics.period_days == 30
        assert metrics.total_findings == 0
        assert metrics.sla_compliance_rate == 100.0  # No findings = 100% compliance

    def test_generate_compliance_metrics_with_data(self) -> None:
        """Test generating metrics with sample data."""
        # Create sample timeline data
        timeline_data = {
            "findings": {
                "CVE-2025-1234": {
                    "first_discovered": "2025-10-01T10:00:00+00:00",
                    "events": [
                        {
                            "timestamp": "2025-10-01T10:00:00+00:00",
                            "event_type": "discovered",
                            "new_data": {"severity": "high"},
                        }
                    ],
                },
                "CVE-2025-5678": {
                    "first_discovered": "2025-10-02T10:00:00+00:00",
                    "events": [
                        {
                            "timestamp": "2025-10-02T10:00:00+00:00",
                            "event_type": "discovered",
                            "new_data": {"severity": "medium"},
                        }
                    ],
                },
            },
            "remediation": {
                "CVE-2025-1234": {
                    "created": "2025-10-01T11:00:00+00:00",
                    "events": [
                        {
                            "timestamp": "2025-10-01T11:00:00+00:00",
                            "event_type": "created",
                        },
                        {
                            "timestamp": "2025-10-05T12:00:00+00:00",
                            "event_type": "status_changed",
                            "new_status": "completed",
                        },
                    ],
                },
                "CVE-2025-5678": {
                    "created": "2025-10-02T11:00:00+00:00",
                    "events": [
                        {
                            "timestamp": "2025-10-02T11:00:00+00:00",
                            "event_type": "created",
                        }
                    ],
                },
            },
        }

        # Write timeline data
        self.historical_manager.timeline_file.parent.mkdir(parents=True, exist_ok=True)
        with self.historical_manager.timeline_file.open("w") as f:
            yaml.dump(timeline_data, f)

        metrics = self.reporter.generate_compliance_metrics(30)

        assert metrics.total_findings == 2
        assert "high" in metrics.findings_by_severity
        assert "medium" in metrics.findings_by_severity
        assert metrics.findings_by_severity["high"] == 1
        assert metrics.findings_by_severity["medium"] == 1

    def test_generate_audit_trail_report(self) -> None:
        """Test generating audit trail report."""
        finding_id = "CVE-2025-1234"

        # Create sample timeline data
        timeline_data = {
            "findings": {
                finding_id: {
                    "first_discovered": "2025-10-01T10:00:00+00:00",
                    "events": [
                        {
                            "timestamp": "2025-10-01T10:00:00+00:00",
                            "event_type": "discovered",
                            "new_data": {"severity": "high"},
                        }
                    ],
                }
            },
            "remediation": {
                finding_id: {
                    "created": "2025-10-01T11:00:00+00:00",
                    "events": [
                        {
                            "timestamp": "2025-10-01T11:00:00+00:00",
                            "event_type": "created",
                        }
                    ],
                }
            },
        }

        # Write timeline data
        self.historical_manager.timeline_file.parent.mkdir(parents=True, exist_ok=True)
        with self.historical_manager.timeline_file.open("w") as f:
            yaml.dump(timeline_data, f)

        # Mock remediation plan
        mock_plan = Mock(spec=RemediationPlan)
        mock_plan.to_dict.return_value = {"finding_id": finding_id, "status": "new"}
        self.mock_datastore.get_remediation_plan.return_value = mock_plan

        audit_trail = self.reporter.generate_audit_trail_report(finding_id)

        assert audit_trail["finding_id"] == finding_id
        assert "lifecycle" in audit_trail
        assert "remediation_plan" in audit_trail
        assert "compliance_status" in audit_trail
        assert "generated_at" in audit_trail

    def test_generate_audit_trail_report_not_found(self) -> None:
        """Test generating audit trail for non-existent finding."""
        # Ensure timeline file doesn't exist
        if self.historical_manager.timeline_file.exists():
            self.historical_manager.timeline_file.unlink()

        audit_trail = self.reporter.generate_audit_trail_report("NONEXISTENT")

        assert audit_trail["finding_id"] == "NONEXISTENT"
        assert "error" in audit_trail

    def test_query_findings_by_criteria(self) -> None:
        """Test querying findings by criteria."""
        # Create sample timeline data
        timeline_data = {
            "findings": {
                "CVE-2025-1234": {
                    "first_discovered": "2025-10-01T10:00:00+00:00",
                    "events": [
                        {
                            "timestamp": "2025-10-01T10:00:00+00:00",
                            "event_type": "discovered",
                            "new_data": {"severity": "high"},
                        }
                    ],
                },
                "CVE-2025-5678": {
                    "first_discovered": "2025-10-02T10:00:00+00:00",
                    "events": [
                        {
                            "timestamp": "2025-10-02T10:00:00+00:00",
                            "event_type": "discovered",
                            "new_data": {"severity": "medium"},
                        }
                    ],
                },
            }
        }

        # Write timeline data
        self.historical_manager.timeline_file.parent.mkdir(parents=True, exist_ok=True)
        with self.historical_manager.timeline_file.open("w") as f:
            yaml.dump(timeline_data, f)

        # Query for high severity findings
        criteria = {"severity": "high"}
        results = self.reporter.query_findings_by_criteria(criteria)

        assert len(results) == 1
        assert results[0]["finding_id"] == "CVE-2025-1234"
        assert results[0]["severity"] == "high"

    def test_query_findings_with_remediation_data(self) -> None:
        """Test querying findings with remediation data included."""
        # Create sample timeline data
        timeline_data = {
            "findings": {
                "CVE-2025-1234": {
                    "first_discovered": "2025-10-01T10:00:00+00:00",
                    "events": [
                        {
                            "timestamp": "2025-10-01T10:00:00+00:00",
                            "event_type": "discovered",
                            "new_data": {"severity": "high"},
                        }
                    ],
                }
            }
        }

        # Write timeline data
        self.historical_manager.timeline_file.parent.mkdir(parents=True, exist_ok=True)
        with self.historical_manager.timeline_file.open("w") as f:
            yaml.dump(timeline_data, f)

        # Mock remediation plan
        mock_plan = Mock(spec=RemediationPlan)
        mock_plan.to_dict.return_value = {"finding_id": "CVE-2025-1234", "status": "new"}
        self.mock_datastore.get_remediation_plan.return_value = mock_plan

        # Query with remediation data
        criteria = {"include_remediation": True}
        results = self.reporter.query_findings_by_criteria(criteria)

        assert len(results) == 1
        assert "remediation_plan" in results[0]
        assert results[0]["remediation_plan"]["status"] == "new"

    def test_sla_compliance_calculation(self) -> None:
        """Test SLA compliance calculation."""
        # Create lifecycles with different compliance statuses
        lifecycles = [
            FindingLifecycle(
                finding_id="CVE-1",
                discovered_date=date(2025, 10, 1),
                resolution_date=date(2025, 10, 2),
                severity="critical",
                sla_target_days=1,
            ),
            FindingLifecycle(
                finding_id="CVE-2",
                discovered_date=date(2025, 10, 1),
                resolution_date=date(2025, 10, 10),
                severity="high",
                sla_target_days=7,
            ),
        ]

        # Calculate metrics for each
        for lc in lifecycles:
            lc.calculate_metrics()

        compliance_rate = self.reporter._calculate_sla_compliance(lifecycles)

        # First finding: resolved in 1 day (within 1-day SLA) = compliant
        # Second finding: resolved in 9 days (outside 7-day SLA) = non-compliant
        assert compliance_rate == 50.0

    def test_response_times_calculation(self) -> None:
        """Test response times calculation."""
        lifecycles = [
            FindingLifecycle(
                finding_id="CVE-1",
                discovered_date=date(2025, 10, 1),
                first_response_date=date(2025, 10, 2),
                severity="high",
            ),
            FindingLifecycle(
                finding_id="CVE-2",
                discovered_date=date(2025, 10, 1),
                first_response_date=date(2025, 10, 3),
                severity="high",
            ),
        ]

        # Calculate metrics
        for lc in lifecycles:
            lc.calculate_metrics()

        response_times = self.reporter._calculate_response_times(lifecycles)

        # Average response time for high severity: (1 + 2) / 2 = 1.5 days
        assert response_times["high"] == 1.5

    def test_resolution_rates_calculation(self) -> None:
        """Test resolution rates calculation."""
        lifecycles = [
            FindingLifecycle(
                finding_id="CVE-1",
                discovered_date=date(2025, 10, 1),
                resolution_date=date(2025, 10, 5),
                severity="medium",
            ),
            FindingLifecycle(
                finding_id="CVE-2",
                discovered_date=date(2025, 10, 1),
                severity="medium",  # Not resolved
            ),
        ]

        resolution_rates = self.reporter._calculate_resolution_rates(lifecycles)

        # 1 out of 2 medium findings resolved = 50%
        assert resolution_rates["medium"] == 50.0

    def test_error_handling_in_metrics_generation(self) -> None:
        """Test error handling in metrics generation."""
        # Mock historical manager to raise exception
        with patch.object(
            self.reporter, "_get_finding_lifecycles", side_effect=Exception("Test error")
        ):
            with pytest.raises(RuntimeError, match="Failed to generate compliance metrics"):
                self.reporter.generate_compliance_metrics(30)

    def test_error_handling_in_audit_trail(self) -> None:
        """Test error handling in audit trail generation."""
        # Mock to raise exception
        with patch.object(
            self.reporter, "_get_finding_lifecycle", side_effect=Exception("Test error")
        ):
            with pytest.raises(RuntimeError, match="Failed to generate audit trail"):
                self.reporter.generate_audit_trail_report("CVE-2025-1234")

    def test_error_handling_in_query(self) -> None:
        """Test error handling in findings query."""
        # Mock to raise exception
        with patch.object(
            self.reporter, "_get_finding_lifecycles", side_effect=Exception("Test error")
        ):
            with pytest.raises(RuntimeError, match="Failed to query findings"):
                self.reporter.query_findings_by_criteria({})

    def test_compliance_status_assessment(self) -> None:
        """Test compliance status assessment."""
        # Test compliant finding
        compliant_lifecycle = FindingLifecycle(
            finding_id="CVE-COMPLIANT",
            discovered_date=datetime.now(timezone.utc).date(),
            first_response_date=datetime.now(timezone.utc).date(),
            resolution_date=datetime.now(timezone.utc).date(),
        )

        status = self.reporter._assess_compliance_status(compliant_lifecycle)
        assert status["is_compliant"] is True
        assert len(status["issues"]) == 0

        # Test non-compliant finding (no response)
        old_date = datetime.now(timezone.utc).date() - timedelta(days=5)
        non_compliant_lifecycle = FindingLifecycle(
            finding_id="CVE-NONCOMPLIANT",
            discovered_date=old_date,
            first_response_date=None,
        )

        status = self.reporter._assess_compliance_status(non_compliant_lifecycle)
        assert status["is_compliant"] is False
        assert "No initial response recorded" in status["issues"]

    def test_criteria_matching(self) -> None:
        """Test criteria matching logic."""
        lifecycle = FindingLifecycle(
            finding_id="CVE-2025-1234",
            discovered_date=date(2025, 10, 1),
            severity="high",
            current_status="in_progress",
            is_overdue=True,
        )

        # Test severity matching
        assert self.reporter._matches_criteria(lifecycle, {"severity": "high"})
        assert not self.reporter._matches_criteria(lifecycle, {"severity": "low"})
        assert self.reporter._matches_criteria(lifecycle, {"severity": ["high", "medium"]})

        # Test status matching
        assert self.reporter._matches_criteria(lifecycle, {"status": "in_progress"})
        assert not self.reporter._matches_criteria(lifecycle, {"status": "completed"})

        # Test overdue matching
        assert self.reporter._matches_criteria(lifecycle, {"overdue": True})
        assert not self.reporter._matches_criteria(lifecycle, {"overdue": False})

        # Test date range matching
        assert self.reporter._matches_criteria(lifecycle, {"date_from": "2025-09-01"})
        assert not self.reporter._matches_criteria(lifecycle, {"date_from": "2025-11-01"})


class TestDefaultComplianceReporter:
    """Test default compliance reporter factory function."""

    def test_get_default_compliance_reporter(self) -> None:
        """Test getting default compliance reporter."""
        reporter = get_default_compliance_reporter()

        assert isinstance(reporter, ComplianceReporter)
        assert reporter.datastore is not None
        assert reporter.historical_manager is not None
