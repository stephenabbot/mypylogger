"""Unit tests for workflow monitoring system."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch

import pytest

from scripts.workflow_monitoring import (
    PublishingStats,
    WorkflowMetrics,
    WorkflowMonitor,
    create_monitoring_dashboard,
)


class TestWorkflowMetrics:
    """Test WorkflowMetrics dataclass."""

    def test_metrics_initialization(self) -> None:
        """Test basic metrics initialization."""
        start_time = datetime.now(timezone.utc)
        metrics = WorkflowMetrics(
            workflow_name="test-workflow",
            execution_id="test-123",
            start_time=start_time,
        )

        assert metrics.workflow_name == "test-workflow"
        assert metrics.execution_id == "test-123"
        assert metrics.start_time == start_time
        assert metrics.status == "running"
        assert metrics.duration_seconds is None

    def test_metrics_duration_calculation(self) -> None:
        """Test duration calculation when end_time is set."""
        start_time = datetime.now(timezone.utc)
        # Use timedelta to safely add 30 seconds
        from datetime import timedelta

        end_time = start_time + timedelta(seconds=30)

        metrics = WorkflowMetrics(
            workflow_name="test-workflow",
            execution_id="test-123",
            start_time=start_time,
            end_time=end_time,
        )

        assert metrics.duration_seconds == 30.0

    def test_metrics_to_dict(self) -> None:
        """Test conversion to dictionary for JSON serialization."""
        start_time = datetime.now(timezone.utc)
        metrics = WorkflowMetrics(
            workflow_name="test-workflow",
            execution_id="test-123",
            start_time=start_time,
            release_triggered=True,
            release_type="manual",
        )

        result = metrics.to_dict()

        assert result["workflow_name"] == "test-workflow"
        assert result["execution_id"] == "test-123"
        assert result["start_time"] == start_time.isoformat()
        assert result["release_triggered"] is True
        assert result["release_type"] == "manual"


class TestPublishingStats:
    """Test PublishingStats dataclass."""

    def test_stats_initialization(self) -> None:
        """Test basic stats initialization."""
        stats = PublishingStats()

        assert stats.total_attempts == 0
        assert stats.successful_publishes == 0
        assert stats.failed_publishes == 0
        assert stats.success_rate() == 0.0

    def test_success_rate_calculation(self) -> None:
        """Test success rate calculation."""
        stats = PublishingStats(
            total_attempts=10,
            successful_publishes=8,
            failed_publishes=2,
        )

        assert stats.success_rate() == 80.0

    def test_success_rate_zero_attempts(self) -> None:
        """Test success rate with zero attempts."""
        stats = PublishingStats()
        assert stats.success_rate() == 0.0

    def test_stats_to_dict(self) -> None:
        """Test conversion to dictionary."""
        stats = PublishingStats(
            total_attempts=5,
            successful_publishes=4,
            failed_publishes=1,
        )

        result = stats.to_dict()

        assert result["total_attempts"] == 5
        assert result["successful_publishes"] == 4
        assert result["success_rate_percent"] == 80.0


class TestWorkflowMonitor:
    """Test WorkflowMonitor class."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.monitor = WorkflowMonitor(metrics_dir=self.temp_dir)

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_start_workflow(self) -> None:
        """Test starting workflow tracking."""
        execution_id = self.monitor.start_workflow("test-workflow")

        assert execution_id.startswith("test-workflow-")
        assert execution_id in self.monitor.current_metrics

        metrics = self.monitor.current_metrics[execution_id]
        assert metrics.workflow_name == "test-workflow"
        assert metrics.status == "running"

    def test_start_workflow_with_custom_id(self) -> None:
        """Test starting workflow with custom execution ID."""
        custom_id = "custom-execution-123"
        execution_id = self.monitor.start_workflow("test-workflow", custom_id)

        assert execution_id == custom_id
        assert custom_id in self.monitor.current_metrics

    def test_update_workflow_metrics(self) -> None:
        """Test updating workflow metrics."""
        execution_id = self.monitor.start_workflow("test-workflow")

        self.monitor.update_workflow_metrics(
            execution_id,
            release_triggered=True,
            release_type="manual",
            security_changes_count=3,
        )

        metrics = self.monitor.current_metrics[execution_id]
        assert metrics.release_triggered is True
        assert metrics.release_type == "manual"
        assert metrics.security_changes_count == 3

    def test_update_nonexistent_workflow(self) -> None:
        """Test updating metrics for nonexistent workflow."""
        with pytest.raises(ValueError, match="No workflow found"):
            self.monitor.update_workflow_metrics("nonexistent", status="success")

    def test_complete_workflow_success(self) -> None:
        """Test completing workflow successfully."""
        execution_id = self.monitor.start_workflow("test-workflow")

        metrics = self.monitor.complete_workflow(execution_id, "success")

        assert metrics.status == "success"
        assert metrics.end_time is not None
        assert metrics.duration_seconds is not None
        assert execution_id not in self.monitor.current_metrics

        # Check that metrics file was created
        metrics_files = list(self.temp_dir.glob("workflow-*.json"))
        assert len(metrics_files) == 1

    def test_complete_workflow_with_error(self) -> None:
        """Test completing workflow with error."""
        execution_id = self.monitor.start_workflow("test-workflow")

        metrics = self.monitor.complete_workflow(
            execution_id,
            "failed",
            error_message="Test error",
            error_stage="build",
        )

        assert metrics.status == "failed"
        assert metrics.error_message == "Test error"
        assert metrics.error_stage == "build"

    def test_get_publishing_stats_empty(self) -> None:
        """Test getting publishing stats with no data."""
        stats = self.monitor.get_publishing_stats(30)

        assert stats.total_attempts == 0
        assert stats.successful_publishes == 0
        assert stats.success_rate() == 0.0

    def test_get_publishing_stats_with_data(self) -> None:
        """Test getting publishing stats with sample data."""
        # Create sample metrics files
        sample_metrics = [
            {
                "workflow_name": "pypi-publish",
                "execution_id": "test-1",
                "start_time": datetime.now(timezone.utc).isoformat(),
                "status": "success",
                "publishing_success": True,
                "release_type": "manual",
                "duration_seconds": 120.0,
                "publish_duration": 30.0,
            },
            {
                "workflow_name": "pypi-publish",
                "execution_id": "test-2",
                "start_time": datetime.now(timezone.utc).isoformat(),
                "status": "failed",
                "publishing_success": False,
                "release_type": "security_auto",
                "duration_seconds": 60.0,
            },
        ]

        for i, metrics in enumerate(sample_metrics):
            metrics_file = self.temp_dir / f"workflow-test-{i}.json"
            with metrics_file.open("w") as f:
                json.dump(metrics, f)

        stats = self.monitor.get_publishing_stats(30)

        assert stats.total_attempts == 2
        assert stats.successful_publishes == 1
        assert stats.failed_publishes == 1
        assert stats.success_rate() == 50.0
        assert stats.manual_releases == 1
        assert stats.security_driven_releases == 1

    def test_generate_dashboard_data(self) -> None:
        """Test generating dashboard data."""
        dashboard_data = self.monitor.generate_dashboard_data()

        assert "generated_at" in dashboard_data
        assert "publishing_stats" in dashboard_data
        assert "recent_workflows" in dashboard_data
        assert "success_trend" in dashboard_data
        assert "health_status" in dashboard_data

        # Check structure of publishing stats
        assert "last_7_days" in dashboard_data["publishing_stats"]
        assert "last_30_days" in dashboard_data["publishing_stats"]

    def test_health_status_calculation(self) -> None:
        """Test health status calculation."""
        # Test excellent health (95%+ success rate)
        stats = PublishingStats(total_attempts=20, successful_publishes=19)
        health = self.monitor._calculate_health_status(stats)
        assert health == "excellent"

        # Test good health (85-94% success rate)
        stats = PublishingStats(total_attempts=20, successful_publishes=17)
        health = self.monitor._calculate_health_status(stats)
        assert health == "good"

        # Test fair health (70-84% success rate)
        stats = PublishingStats(total_attempts=20, successful_publishes=15)
        health = self.monitor._calculate_health_status(stats)
        assert health == "fair"

        # Test poor health (<70% success rate)
        stats = PublishingStats(total_attempts=20, successful_publishes=10)
        health = self.monitor._calculate_health_status(stats)
        assert health == "poor"


class TestMonitoringDashboard:
    """Test monitoring dashboard generation."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.monitor = WorkflowMonitor(metrics_dir=self.temp_dir)

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_create_monitoring_dashboard(self) -> None:
        """Test creating HTML monitoring dashboard."""
        output_file = self.temp_dir / "dashboard.html"

        create_monitoring_dashboard(self.monitor, output_file)

        assert output_file.exists()

        # Check that HTML content is valid
        content = output_file.read_text()
        assert "<!DOCTYPE html>" in content
        assert "PyPI Publishing Monitoring Dashboard" in content
        assert "Publishing Statistics" in content
        assert "Recent Workflow Executions" in content

    def test_dashboard_with_sample_data(self) -> None:
        """Test dashboard generation with sample data."""
        # Create sample metrics
        sample_metrics = {
            "workflow_name": "pypi-publish",
            "execution_id": "test-1",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "status": "success",
            "publishing_success": True,
            "release_type": "manual",
            "duration_seconds": 120.0,
        }

        metrics_file = self.temp_dir / "workflow-test-1.json"
        with metrics_file.open("w") as f:
            json.dump(sample_metrics, f)

        output_file = self.temp_dir / "dashboard.html"
        create_monitoring_dashboard(self.monitor, output_file)

        content = output_file.read_text()
        assert "test-1" in content or "Success" in content  # Should show the successful workflow


class TestMonitoringCLI:
    """Test monitoring CLI functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch("scripts.workflow_monitoring.WorkflowMonitor")
    def test_cli_dashboard_command(self, mock_monitor_class: Mock) -> None:
        """Test CLI dashboard command."""
        mock_monitor = Mock()
        mock_monitor.generate_dashboard_data.return_value = {
            "generated_at": "2025-01-21T10:00:00Z",
            "publishing_stats": {
                "last_7_days": {
                    "total_attempts": 5,
                    "successful_publishes": 4,
                    "success_rate_percent": 80.0,
                    "security_driven_releases": 2,
                    "manual_releases": 3,
                },
                "last_30_days": {
                    "total_attempts": 20,
                    "successful_publishes": 18,
                    "success_rate_percent": 90.0,
                    "security_driven_releases": 8,
                    "manual_releases": 12,
                    "average_publish_duration": 45.5,
                },
            },
            "recent_workflows": [],
            "success_trend": {
                "trend_direction": "up",
                "current_success_rate": 80.0,
                "previous_success_rate": 75.0,
                "trend_change": 5.0,
            },
            "health_status": "excellent",
        }
        mock_monitor_class.return_value = mock_monitor

        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["workflow_monitoring.py", "dashboard"]):
            with patch("builtins.print"):
                with patch("pathlib.Path.open", create=True) as mock_open:
                    from scripts.workflow_monitoring import main

                    try:
                        main()
                    except SystemExit:
                        pass  # Expected for successful completion

                    # Verify dashboard generation was attempted
                    mock_open.assert_called_once()

    @patch("scripts.workflow_monitoring.WorkflowMonitor")
    def test_cli_stats_command(self, mock_monitor_class: Mock) -> None:
        """Test CLI stats command."""
        mock_monitor = Mock()
        mock_stats = Mock()
        mock_stats.to_dict.return_value = {"total_attempts": 5, "success_rate_percent": 80.0}
        mock_monitor.get_publishing_stats.return_value = mock_stats
        mock_monitor_class.return_value = mock_monitor

        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["workflow_monitoring.py", "stats", "--days=7"]):
            with patch("builtins.print"):
                from scripts.workflow_monitoring import main

                try:
                    main()
                except SystemExit:
                    pass

                # Verify stats were requested with correct days
                mock_monitor.get_publishing_stats.assert_called_with(7)
