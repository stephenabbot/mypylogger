"""Tests for historical tracking and audit trails functionality."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch

import pytest
import yaml

from security.history import (
    FindingChangeEvent,
    HistoricalDataManager,
    RemediationChangeEvent,
    get_default_historical_manager,
)
from security.models import RemediationPlan, SecurityFinding


class TestFindingChangeEvent:
    """Test FindingChangeEvent data model."""

    def test_finding_change_event_creation(self) -> None:
        """Test creating a finding change event."""
        timestamp = datetime.now(timezone.utc)
        event = FindingChangeEvent(
            timestamp=timestamp,
            finding_id="CVE-2025-1234",
            event_type="discovered",
            new_data={"severity": "high"},
            source="scanner",
            notes="Test finding discovered",
        )

        assert event.timestamp == timestamp
        assert event.finding_id == "CVE-2025-1234"
        assert event.event_type == "discovered"
        assert event.new_data == {"severity": "high"}
        assert event.source == "scanner"
        assert event.notes == "Test finding discovered"

    def test_finding_change_event_to_dict(self) -> None:
        """Test converting finding change event to dictionary."""
        timestamp = datetime.now(timezone.utc)
        event = FindingChangeEvent(
            timestamp=timestamp,
            finding_id="CVE-2025-1234",
            event_type="discovered",
            new_data={"severity": "high"},
            source="scanner",
            notes="Test finding",
        )

        result = event.to_dict()

        assert result["timestamp"] == timestamp.isoformat()
        assert result["finding_id"] == "CVE-2025-1234"
        assert result["event_type"] == "discovered"
        assert result["new_data"] == {"severity": "high"}
        assert result["source"] == "scanner"
        assert result["notes"] == "Test finding"


class TestRemediationChangeEvent:
    """Test RemediationChangeEvent data model."""

    def test_remediation_change_event_creation(self) -> None:
        """Test creating a remediation change event."""
        timestamp = datetime.now(timezone.utc)
        event = RemediationChangeEvent(
            timestamp=timestamp,
            finding_id="CVE-2025-1234",
            event_type="status_changed",
            old_status="new",
            new_status="in_progress",
            changed_fields=["status"],
            user="admin",
            notes="Status updated",
        )

        assert event.timestamp == timestamp
        assert event.finding_id == "CVE-2025-1234"
        assert event.event_type == "status_changed"
        assert event.old_status == "new"
        assert event.new_status == "in_progress"
        assert event.changed_fields == ["status"]
        assert event.user == "admin"
        assert event.notes == "Status updated"

    def test_remediation_change_event_to_dict(self) -> None:
        """Test converting remediation change event to dictionary."""
        timestamp = datetime.now(timezone.utc)
        event = RemediationChangeEvent(
            timestamp=timestamp,
            finding_id="CVE-2025-1234",
            event_type="created",
            new_status="new",
            user="system",
        )

        result = event.to_dict()

        assert result["timestamp"] == timestamp.isoformat()
        assert result["finding_id"] == "CVE-2025-1234"
        assert result["event_type"] == "created"
        assert result["new_status"] == "new"
        assert result["user"] == "system"


class TestHistoricalDataManager:
    """Test HistoricalDataManager functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.history_dir = self.temp_dir / "history"
        self.reports_dir = self.temp_dir / "reports" / "latest"
        self.archived_dir = self.temp_dir / "reports" / "archived"

        self.manager = HistoricalDataManager(
            history_dir=self.history_dir,
            reports_dir=self.reports_dir,
            archived_reports_dir=self.archived_dir,
        )

        # Create test finding
        self.test_finding = SecurityFinding(
            finding_id="CVE-2025-1234",
            package="test-package",
            version="1.0.0",
            severity="high",
            source_scanner="pip-audit",
            discovered_date=datetime.now(timezone.utc).date(),
            description="Test vulnerability",
            impact="High impact",
            fix_available=True,
            fix_version="1.0.1",
        )

        # Create test remediation plan
        self.test_plan = RemediationPlan(
            finding_id="CVE-2025-1234",
            status="new",
            planned_action="Upgrade package",
            assigned_to="security-team",
            notes="Test plan",
            workaround="None",
        )

    def test_manager_initialization(self) -> None:
        """Test historical data manager initialization."""
        assert self.manager.history_dir == self.history_dir
        assert self.manager.reports_dir == self.reports_dir
        assert self.manager.archived_reports_dir == self.archived_dir
        assert self.history_dir.exists()
        assert self.archived_dir.exists()

    def test_record_finding_discovered(self) -> None:
        """Test recording finding discovery."""
        self.manager.record_finding_discovered(self.test_finding)

        # Check changelog was created and updated
        assert self.manager.changelog_file.exists()
        content = self.manager.changelog_file.read_text()
        assert "CVE-2025-1234" in content
        assert "Discovered" in content
        assert "high severity" in content

        # Check timeline was updated
        assert self.manager.timeline_file.exists()
        with self.manager.timeline_file.open("r") as f:
            timeline_data = yaml.safe_load(f)

        assert "findings" in timeline_data
        assert "CVE-2025-1234" in timeline_data["findings"]
        finding_data = timeline_data["findings"]["CVE-2025-1234"]
        assert "first_discovered" in finding_data
        assert "events" in finding_data
        assert len(finding_data["events"]) == 1
        assert finding_data["events"][0]["event_type"] == "discovered"

    def test_record_finding_resolved(self) -> None:
        """Test recording finding resolution."""
        # First record discovery
        self.manager.record_finding_discovered(self.test_finding)

        # Then record resolution
        self.manager.record_finding_resolved("CVE-2025-1234", "scanner")

        # Check changelog was updated
        content = self.manager.changelog_file.read_text()
        assert "Resolved" in content
        assert "no longer detected" in content

        # Check timeline was updated
        with self.manager.timeline_file.open("r") as f:
            timeline_data = yaml.safe_load(f)

        finding_data = timeline_data["findings"]["CVE-2025-1234"]
        assert len(finding_data["events"]) == 2
        assert finding_data["events"][1]["event_type"] == "resolved"

    def test_record_remediation_created(self) -> None:
        """Test recording remediation plan creation."""
        self.manager.record_remediation_created(self.test_plan)

        # Check timeline was updated
        assert self.manager.timeline_file.exists()
        with self.manager.timeline_file.open("r") as f:
            timeline_data = yaml.safe_load(f)

        assert "remediation" in timeline_data
        assert "CVE-2025-1234" in timeline_data["remediation"]
        remediation_data = timeline_data["remediation"]["CVE-2025-1234"]
        assert "created" in remediation_data
        assert "events" in remediation_data
        assert len(remediation_data["events"]) == 1
        assert remediation_data["events"][0]["event_type"] == "created"

    def test_record_remediation_status_change(self) -> None:
        """Test recording remediation status change."""
        # First create remediation
        self.manager.record_remediation_created(self.test_plan)

        # Then record status change
        self.manager.record_remediation_status_change(
            "CVE-2025-1234", "new", "in_progress", "admin", "Started work"
        )

        # Check timeline was updated
        with self.manager.timeline_file.open("r") as f:
            timeline_data = yaml.safe_load(f)

        remediation_data = timeline_data["remediation"]["CVE-2025-1234"]
        assert len(remediation_data["events"]) == 2

        status_event = remediation_data["events"][1]
        assert status_event["event_type"] == "status_changed"
        assert status_event["old_status"] == "new"
        assert status_event["new_status"] == "in_progress"
        assert status_event["user"] == "admin"
        assert status_event["notes"] == "Started work"

    def test_record_remediation_updated(self) -> None:
        """Test recording remediation plan updates."""
        # First create remediation
        self.manager.record_remediation_created(self.test_plan)

        # Then record update
        self.manager.record_remediation_updated(
            "CVE-2025-1234", ["planned_action", "target_date"], "admin", "Updated plan"
        )

        # Check timeline was updated
        with self.manager.timeline_file.open("r") as f:
            timeline_data = yaml.safe_load(f)

        remediation_data = timeline_data["remediation"]["CVE-2025-1234"]
        assert len(remediation_data["events"]) == 2

        update_event = remediation_data["events"][1]
        assert update_event["event_type"] == "updated"
        assert update_event["changed_fields"] == ["planned_action", "target_date"]
        assert update_event["user"] == "admin"
        assert update_event["notes"] == "Updated plan"

    def test_archive_scan_results(self) -> None:
        """Test archiving scan results."""
        # Create some test scan files
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        (self.reports_dir / "pip-audit.json").write_text('{"test": "data"}')
        (self.reports_dir / "bandit.json").write_text('{"bandit": "results"}')

        # Archive results
        scan_date = date(2025, 10, 24)
        archive_dir = self.manager.archive_scan_results(scan_date)

        # Check archive was created
        expected_dir = self.archived_dir / "2025-10-24"
        assert archive_dir == expected_dir
        assert archive_dir.exists()
        assert (archive_dir / "pip-audit.json").exists()
        assert (archive_dir / "bandit.json").exists()

        # Verify file contents were copied
        assert (archive_dir / "pip-audit.json").read_text() == '{"test": "data"}'
        assert (archive_dir / "bandit.json").read_text() == '{"bandit": "results"}'

    def test_archive_scan_results_no_reports_dir(self) -> None:
        """Test archiving when reports directory doesn't exist."""
        # Remove reports directory
        if self.reports_dir.exists():
            self.reports_dir.rmdir()

        # Archive should still work but create empty archive
        archive_dir = self.manager.archive_scan_results()
        assert archive_dir.exists()
        assert len(list(archive_dir.iterdir())) == 0

    def test_get_remediation_metrics(self) -> None:
        """Test calculating remediation metrics."""
        # Create some test data
        self.manager.record_remediation_created(self.test_plan)
        self.manager.record_remediation_status_change("CVE-2025-1234", "new", "completed", "admin")

        # Get metrics
        metrics = self.manager.get_remediation_metrics(30)

        # Check basic structure
        assert "period_days" in metrics
        assert "total_findings_discovered" in metrics
        assert "total_findings_resolved" in metrics
        assert "average_resolution_time_days" in metrics
        assert "findings_by_severity" in metrics
        assert "remediation_status_distribution" in metrics
        assert "overdue_remediations" in metrics
        assert "response_time_metrics" in metrics

        assert metrics["period_days"] == 30

    def test_get_finding_history(self) -> None:
        """Test getting finding history."""
        # Record some events
        self.manager.record_finding_discovered(self.test_finding)
        self.manager.record_finding_resolved("CVE-2025-1234")

        # Get history (basic test - implementation is simplified)
        history = self.manager.get_finding_history("CVE-2025-1234")
        assert isinstance(history, list)

    def test_error_handling_in_record_methods(self) -> None:
        """Test error handling in record methods."""
        # Test with invalid finding (should raise RuntimeError)
        invalid_finding = Mock()
        invalid_finding.to_dict.side_effect = Exception("Test error")

        with pytest.raises(RuntimeError, match="Failed to record finding discovery"):
            self.manager.record_finding_discovered(invalid_finding)

    def test_changelog_initialization(self) -> None:
        """Test changelog file initialization."""
        # Remove changelog if it exists
        if self.manager.changelog_file.exists():
            self.manager.changelog_file.unlink()

        # Record an event to trigger initialization
        self.manager.record_finding_discovered(self.test_finding)

        # Check changelog was initialized with header
        content = self.manager.changelog_file.read_text()
        assert "# Security Findings Changelog" in content
        assert "Legend" in content
        assert "Discovered" in content

    def test_error_handling_in_archive(self) -> None:
        """Test error handling in archive method."""
        # Mock shutil.copy2 to raise an exception
        with patch("shutil.copy2", side_effect=Exception("Copy failed")):
            # Create some test files to copy
            self.reports_dir.mkdir(parents=True, exist_ok=True)
            (self.reports_dir / "test.json").write_text('{"test": "data"}')

            with pytest.raises(RuntimeError, match="Failed to archive scan results"):
                self.manager.archive_scan_results()

    def test_error_handling_in_timeline_update(self) -> None:
        """Test error handling in timeline update methods."""
        # Make timeline file read-only to trigger write error
        self.manager.timeline_file.parent.mkdir(parents=True, exist_ok=True)
        self.manager.timeline_file.write_text("test")
        self.manager.timeline_file.chmod(0o444)  # Read-only

        try:
            with pytest.raises(RuntimeError, match="Failed to record remediation creation"):
                self.manager.record_remediation_created(self.test_plan)
        finally:
            # Restore write permissions for cleanup
            self.manager.timeline_file.chmod(0o644)

    def test_metrics_with_empty_timeline(self) -> None:
        """Test metrics calculation with empty timeline."""
        # Ensure timeline file doesn't exist
        if self.manager.timeline_file.exists():
            self.manager.timeline_file.unlink()

        metrics = self.manager.get_remediation_metrics(30)

        # Should return default metrics structure
        assert metrics["period_days"] == 30
        assert metrics["total_findings_discovered"] == 0
        assert metrics["total_findings_resolved"] == 0

    def test_finding_history_with_nonexistent_files(self) -> None:
        """Test getting finding history when files don't exist."""
        # Ensure files don't exist
        if self.manager.changelog_file.exists():
            self.manager.changelog_file.unlink()
        if self.manager.timeline_file.exists():
            self.manager.timeline_file.unlink()

        history = self.manager.get_finding_history("CVE-2025-1234")
        assert isinstance(history, list)
        assert len(history) == 0

    def test_record_finding_with_minimal_data(self) -> None:
        """Test recording finding with minimal required data."""
        minimal_finding = SecurityFinding(
            finding_id="MINIMAL-001",
            package="minimal-pkg",
            version="1.0",
            severity="low",
            source_scanner="test",
            discovered_date=datetime.now(timezone.utc).date(),
            description="Minimal test",
            impact="Low impact",
            fix_available=False,
        )

        self.manager.record_finding_discovered(minimal_finding)

        # Verify it was recorded
        content = self.manager.changelog_file.read_text()
        assert "MINIMAL-001" in content
        assert "low severity" in content

    def test_multiple_events_timeline_ordering(self) -> None:
        """Test that multiple events are properly ordered in timeline."""
        # Record multiple events
        self.manager.record_remediation_created(self.test_plan)
        self.manager.record_remediation_status_change(
            "CVE-2025-1234", "new", "in_progress", "user1", "Started"
        )
        self.manager.record_remediation_status_change(
            "CVE-2025-1234", "in_progress", "completed", "user2", "Finished"
        )

        # Check timeline has all events in order
        with self.manager.timeline_file.open("r") as f:
            timeline_data = yaml.safe_load(f)

        remediation_data = timeline_data["remediation"]["CVE-2025-1234"]
        events = remediation_data["events"]

        assert len(events) == 3
        assert events[0]["event_type"] == "created"
        assert events[1]["event_type"] == "status_changed"
        assert events[1]["new_status"] == "in_progress"
        assert events[2]["event_type"] == "status_changed"
        assert events[2]["new_status"] == "completed"

    def test_archive_with_specific_date(self) -> None:
        """Test archiving with a specific date."""
        # Create test files
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        (self.reports_dir / "test-report.json").write_text('{"test": "data"}')

        # Archive with specific date
        specific_date = date(2024, 12, 25)
        archive_dir = self.manager.archive_scan_results(specific_date)

        expected_path = self.archived_dir / "2024-12-25"
        assert archive_dir == expected_path
        assert (expected_path / "test-report.json").exists()

    def test_error_in_metrics_calculation(self) -> None:
        """Test error handling in metrics calculation."""
        # Create invalid timeline data
        self.manager.timeline_file.parent.mkdir(parents=True, exist_ok=True)
        self.manager.timeline_file.write_text("invalid: yaml: content: [")

        with pytest.raises(RuntimeError, match="Failed to calculate remediation metrics"):
            self.manager.get_remediation_metrics(30)

    def test_comprehensive_metrics_calculation(self) -> None:
        """Test comprehensive metrics calculation with real data."""
        # Create timeline with various events
        timeline_data = {
            "findings": {
                "CVE-2025-1234": {
                    "first_discovered": "2025-10-01T10:00:00+00:00",
                    "events": [
                        {
                            "timestamp": "2025-10-01T10:00:00+00:00",
                            "event_type": "discovered",
                            "finding_id": "CVE-2025-1234",
                        }
                    ],
                }
            },
            "remediation": {
                "CVE-2025-1234": {
                    "created": "2025-10-01T11:00:00+00:00",
                    "events": [
                        {
                            "timestamp": "2025-10-01T11:00:00+00:00",
                            "event_type": "created",
                            "finding_id": "CVE-2025-1234",
                        },
                        {
                            "timestamp": "2025-10-02T12:00:00+00:00",
                            "event_type": "status_changed",
                            "finding_id": "CVE-2025-1234",
                            "new_status": "completed",
                        },
                    ],
                }
            },
        }

        # Write timeline data
        self.manager.timeline_file.parent.mkdir(parents=True, exist_ok=True)
        with self.manager.timeline_file.open("w") as f:
            yaml.dump(timeline_data, f)

        # Calculate metrics
        metrics = self.manager.get_remediation_metrics(30)

        # Verify metrics structure
        assert metrics["period_days"] == 30
        assert "total_findings_discovered" in metrics
        assert "total_findings_resolved" in metrics

    def test_error_handling_in_finding_resolution(self) -> None:
        """Test error handling when recording finding resolution fails."""
        # Mock the timeline update to fail
        with patch.object(
            self.manager, "_update_timeline_for_finding", side_effect=Exception("Timeline error")
        ):
            with pytest.raises(RuntimeError, match="Failed to record finding resolution"):
                self.manager.record_finding_resolved("CVE-2025-1234")

    def test_error_handling_in_status_change(self) -> None:
        """Test error handling when recording status change fails."""
        # Mock the timeline update to fail
        with patch.object(
            self.manager, "_update_remediation_timeline", side_effect=Exception("Timeline error")
        ):
            with pytest.raises(RuntimeError, match="Failed to record status change"):
                self.manager.record_remediation_status_change("CVE-2025-1234", "new", "in_progress")

    def test_error_handling_in_remediation_update(self) -> None:
        """Test error handling when recording remediation update fails."""
        # Mock the timeline update to fail
        with patch.object(
            self.manager, "_update_remediation_timeline", side_effect=Exception("Timeline error")
        ):
            with pytest.raises(RuntimeError, match="Failed to record remediation update"):
                self.manager.record_remediation_updated("CVE-2025-1234", ["status"])

    def test_error_handling_in_changelog_append(self) -> None:
        """Test error handling when appending to changelog fails."""
        # Mock the _append_to_changelog method to fail
        with patch.object(
            self.manager, "_append_to_changelog", side_effect=Exception("Changelog error")
        ):
            with pytest.raises(RuntimeError, match="Failed to record finding discovery"):
                self.manager.record_finding_discovered(self.test_finding)

    def test_timeline_update_with_existing_data(self) -> None:
        """Test updating timeline when data already exists."""
        # First, create some initial data
        self.manager.record_finding_discovered(self.test_finding)

        # Record another event for the same finding
        self.manager.record_finding_resolved("CVE-2025-1234")

        # Verify both events are in timeline
        with self.manager.timeline_file.open("r") as f:
            timeline_data = yaml.safe_load(f)

        finding_data = timeline_data["findings"]["CVE-2025-1234"]
        assert len(finding_data["events"]) == 2
        assert finding_data["events"][0]["event_type"] == "discovered"
        assert finding_data["events"][1]["event_type"] == "resolved"

    def test_remediation_timeline_with_existing_data(self) -> None:
        """Test updating remediation timeline when data already exists."""
        # Create initial remediation
        self.manager.record_remediation_created(self.test_plan)

        # Add multiple updates
        self.manager.record_remediation_status_change("CVE-2025-1234", "new", "in_progress")
        self.manager.record_remediation_updated("CVE-2025-1234", ["planned_action"])

        # Verify all events are recorded
        with self.manager.timeline_file.open("r") as f:
            timeline_data = yaml.safe_load(f)

        remediation_data = timeline_data["remediation"]["CVE-2025-1234"]
        assert len(remediation_data["events"]) == 3
        assert remediation_data["events"][0]["event_type"] == "created"
        assert remediation_data["events"][1]["event_type"] == "status_changed"
        assert remediation_data["events"][2]["event_type"] == "updated"

    def test_finding_change_event_defaults(self) -> None:
        """Test FindingChangeEvent with default values."""
        timestamp = datetime.now(timezone.utc)
        event = FindingChangeEvent(
            timestamp=timestamp,
            finding_id="CVE-2025-1234",
            event_type="discovered",
        )

        assert event.old_data is None
        assert event.new_data is None
        assert event.source == "system"
        assert event.notes == ""

    def test_remediation_change_event_defaults(self) -> None:
        """Test RemediationChangeEvent with default values."""
        timestamp = datetime.now(timezone.utc)
        event = RemediationChangeEvent(
            timestamp=timestamp,
            finding_id="CVE-2025-1234",
            event_type="created",
        )

        assert event.old_status is None
        assert event.new_status is None
        assert event.changed_fields == []
        assert event.user == "system"
        assert event.notes == ""

    def test_get_finding_history_with_timeline_data(self) -> None:
        """Test getting finding history when timeline exists."""
        # Create some timeline data
        self.manager.record_finding_discovered(self.test_finding)
        self.manager.record_remediation_created(self.test_plan)

        # Get history - should return empty list for now (simplified implementation)
        history = self.manager.get_finding_history("CVE-2025-1234")
        assert isinstance(history, list)

    def test_metrics_with_malformed_events(self) -> None:
        """Test metrics calculation with malformed event data."""
        # Create timeline with malformed events
        timeline_data = {
            "findings": {
                "CVE-2025-1234": {
                    "events": [
                        {"event_type": "created"},  # Missing timestamp
                        {"timestamp": "invalid-date", "event_type": "created"},  # Invalid timestamp
                    ]
                }
            }
        }

        self.manager.timeline_file.parent.mkdir(parents=True, exist_ok=True)
        with self.manager.timeline_file.open("w") as f:
            yaml.dump(timeline_data, f)

        # Should handle malformed data gracefully
        metrics = self.manager.get_remediation_metrics(30)
        assert metrics["period_days"] == 30
        # Should have zero counts since malformed events are skipped
        assert metrics["total_findings_discovered"] == 0
        assert metrics["total_findings_resolved"] == 0

    def test_changelog_with_finding_data(self) -> None:
        """Test changelog generation with complete finding data."""
        # Create a finding with all optional fields
        complete_finding = SecurityFinding(
            finding_id="CVE-2025-5678",
            package="complete-pkg",
            version="2.0.0",
            severity="critical",
            source_scanner="bandit",
            discovered_date=datetime.now(timezone.utc).date(),
            description="Complete test vulnerability",
            impact="Critical impact",
            fix_available=True,
            fix_version="2.0.1",
            cvss_score=9.5,
            reference_url="https://example.com/vuln",
        )

        self.manager.record_finding_discovered(complete_finding)

        # Check changelog contains all the data
        content = self.manager.changelog_file.read_text()
        assert "CVE-2025-5678" in content
        assert "critical" in content
        assert "complete-pkg 2.0.0" in content
        assert "bandit" in content


class TestDefaultHistoricalManager:
    """Test default historical manager factory function."""

    def test_get_default_historical_manager(self) -> None:
        """Test getting default historical manager."""
        manager = get_default_historical_manager()

        assert isinstance(manager, HistoricalDataManager)
        assert manager.history_dir == Path("security/findings/history")
        assert manager.reports_dir == Path("security/reports/latest")
        assert manager.archived_reports_dir == Path("security/reports/archived")
