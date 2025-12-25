"""Workflow monitoring and observability for PyPI publishing system.

This module provides comprehensive monitoring, metrics collection, and
observability features for the Phase 7 PyPI publishing workflows.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


@dataclass
class WorkflowMetrics:
    """Metrics for workflow execution tracking."""

    workflow_name: str
    execution_id: str
    start_time: datetime
    end_time: datetime | None = None
    status: str = "running"  # running, success, failed
    duration_seconds: float | None = None

    # Workflow-specific metrics
    release_triggered: bool = False
    release_type: str | None = None
    security_changes_count: int = 0
    quality_gates_passed: bool = False
    publishing_success: bool = False

    # Error tracking
    error_message: str | None = None
    error_stage: str | None = None

    # Performance metrics
    security_scan_duration: float | None = None
    build_duration: float | None = None
    publish_duration: float | None = None

    def __post_init__(self) -> None:
        """Calculate derived metrics after initialization."""
        if self.end_time and self.start_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for JSON serialization."""
        return {
            "workflow_name": self.workflow_name,
            "execution_id": self.execution_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status,
            "duration_seconds": self.duration_seconds,
            "release_triggered": self.release_triggered,
            "release_type": self.release_type,
            "security_changes_count": self.security_changes_count,
            "quality_gates_passed": self.quality_gates_passed,
            "publishing_success": self.publishing_success,
            "error_message": self.error_message,
            "error_stage": self.error_stage,
            "security_scan_duration": self.security_scan_duration,
            "build_duration": self.build_duration,
            "publish_duration": self.publish_duration,
        }


@dataclass
class PublishingStats:
    """Publishing success/failure rate statistics."""

    total_attempts: int = 0
    successful_publishes: int = 0
    failed_publishes: int = 0
    security_driven_releases: int = 0
    manual_releases: int = 0

    # Time-based metrics
    last_successful_publish: datetime | None = None
    last_failed_publish: datetime | None = None
    average_publish_duration: float | None = None

    def success_rate(self) -> float:
        """Calculate publishing success rate as percentage."""
        if self.total_attempts == 0:
            return 0.0
        return (self.successful_publishes / self.total_attempts) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert stats to dictionary for JSON serialization."""
        return {
            "total_attempts": self.total_attempts,
            "successful_publishes": self.successful_publishes,
            "failed_publishes": self.failed_publishes,
            "security_driven_releases": self.security_driven_releases,
            "manual_releases": self.manual_releases,
            "success_rate_percent": round(self.success_rate(), 2),
            "last_successful_publish": self.last_successful_publish.isoformat()
            if self.last_successful_publish
            else None,
            "last_failed_publish": self.last_failed_publish.isoformat()
            if self.last_failed_publish
            else None,
            "average_publish_duration": self.average_publish_duration,
        }


class WorkflowMonitor:
    """Monitor and track workflow execution metrics."""

    def __init__(self, metrics_dir: Path | None = None) -> None:
        """Initialize workflow monitor.

        Args:
            metrics_dir: Directory to store metrics data
        """
        self.metrics_dir = metrics_dir or Path("metrics")
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

        self.current_metrics: dict[str, WorkflowMetrics] = {}

    def start_workflow(
        self,
        workflow_name: str,
        execution_id: str | None = None,
    ) -> str:
        """Start tracking a workflow execution.

        Args:
            workflow_name: Name of the workflow being executed
            execution_id: Unique execution ID (generated if not provided)

        Returns:
            Execution ID for tracking this workflow run
        """
        if execution_id is None:
            execution_id = f"{workflow_name}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

        metrics = WorkflowMetrics(
            workflow_name=workflow_name,
            execution_id=execution_id,
            start_time=datetime.now(timezone.utc),
        )

        self.current_metrics[execution_id] = metrics
        return execution_id

    def update_workflow_metrics(
        self,
        execution_id: str,
        **kwargs: Any,
    ) -> None:
        """Update metrics for a running workflow.

        Args:
            execution_id: Execution ID to update
            **kwargs: Metric fields to update
        """
        if execution_id not in self.current_metrics:
            msg = f"No workflow found with execution_id: {execution_id}"
            raise ValueError(msg)

        metrics = self.current_metrics[execution_id]

        # Update metrics fields
        for key, value in kwargs.items():
            if hasattr(metrics, key):
                setattr(metrics, key, value)

    def complete_workflow(
        self,
        execution_id: str,
        status: str = "success",
        error_message: str | None = None,
        error_stage: str | None = None,
    ) -> WorkflowMetrics:
        """Complete workflow tracking and save metrics.

        Args:
            execution_id: Execution ID to complete
            status: Final workflow status
            error_message: Error message if workflow failed
            error_stage: Stage where error occurred

        Returns:
            Final workflow metrics
        """
        if execution_id not in self.current_metrics:
            msg = f"No workflow found with execution_id: {execution_id}"
            raise ValueError(msg)

        metrics = self.current_metrics[execution_id]
        metrics.end_time = datetime.now(timezone.utc)
        metrics.status = status
        metrics.error_message = error_message
        metrics.error_stage = error_stage

        # Recalculate duration
        if metrics.end_time and metrics.start_time:
            metrics.duration_seconds = (metrics.end_time - metrics.start_time).total_seconds()

        # Save metrics to file
        self._save_workflow_metrics(metrics)

        # Update publishing stats
        self._update_publishing_stats(metrics)

        # Remove from current tracking
        del self.current_metrics[execution_id]

        return metrics

    def get_publishing_stats(self, days_back: int = 30) -> PublishingStats:
        """Get publishing statistics for the specified time period.

        Args:
            days_back: Number of days to look back for statistics

        Returns:
            Publishing statistics
        """
        stats = PublishingStats()

        # Load historical metrics
        from datetime import timedelta

        cutoff_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date - timedelta(days=days_back)

        metrics_files = list(self.metrics_dir.glob("workflow-*.json"))
        durations = []

        for metrics_file in metrics_files:
            try:
                with metrics_file.open() as f:
                    data = json.load(f)

                # Parse start time
                start_time = datetime.fromisoformat(data["start_time"].replace("Z", "+00:00"))

                # Skip if outside time window
                if start_time < cutoff_date:
                    continue

                # Count attempts
                if data["workflow_name"] in ["pypi-publish", "security-driven-release"]:
                    stats.total_attempts += 1

                    # Track success/failure
                    if data["status"] == "success" and data.get("publishing_success", False):
                        stats.successful_publishes += 1
                        if data.get("end_time"):
                            stats.last_successful_publish = datetime.fromisoformat(
                                data["end_time"].replace("Z", "+00:00")
                            )
                    elif data["status"] == "failed":
                        stats.failed_publishes += 1
                        if data.get("end_time"):
                            stats.last_failed_publish = datetime.fromisoformat(
                                data["end_time"].replace("Z", "+00:00")
                            )

                    # Track release types
                    if data.get("release_type") == "security_auto":
                        stats.security_driven_releases += 1
                    elif data.get("release_type") == "manual":
                        stats.manual_releases += 1

                    # Collect durations for average
                    if data.get("publish_duration"):
                        durations.append(data["publish_duration"])

            except (json.JSONDecodeError, KeyError, ValueError):
                # Skip invalid metrics files
                continue

        # Calculate average duration
        if durations:
            stats.average_publish_duration = sum(durations) / len(durations)

        return stats

    def generate_dashboard_data(self) -> dict[str, Any]:
        """Generate dashboard data for release automation visibility.

        Returns:
            Dictionary containing dashboard metrics and visualizations
        """
        # Get recent publishing stats
        stats_7d = self.get_publishing_stats(7)
        stats_30d = self.get_publishing_stats(30)

        # Get recent workflow executions
        recent_workflows = self._get_recent_workflows(limit=10)

        # Calculate trends
        success_trend = self._calculate_success_trend()

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "publishing_stats": {
                "last_7_days": stats_7d.to_dict(),
                "last_30_days": stats_30d.to_dict(),
            },
            "recent_workflows": recent_workflows,
            "success_trend": success_trend,
            "active_workflows": len(self.current_metrics),
            "health_status": self._calculate_health_status(stats_7d),
        }

    def _save_workflow_metrics(self, metrics: WorkflowMetrics) -> None:
        """Save workflow metrics to file."""
        filename = f"workflow-{metrics.execution_id}.json"
        filepath = self.metrics_dir / filename

        with filepath.open("w") as f:
            json.dump(metrics.to_dict(), f, indent=2)

    def _update_publishing_stats(self, metrics: WorkflowMetrics) -> None:
        """Update publishing statistics file."""
        stats_file = self.metrics_dir / "publishing_stats.json"

        # Load existing stats or create new
        if stats_file.exists():
            try:
                with stats_file.open() as f:
                    data = json.load(f)
                stats = PublishingStats(**data)
            except (json.JSONDecodeError, TypeError):
                stats = PublishingStats()
        else:
            stats = PublishingStats()

        # Update stats based on workflow metrics
        if metrics.workflow_name in ["pypi-publish", "security-driven-release"]:
            stats.total_attempts += 1

            if metrics.status == "success" and metrics.publishing_success:
                stats.successful_publishes += 1
                stats.last_successful_publish = metrics.end_time
            elif metrics.status == "failed":
                stats.failed_publishes += 1
                stats.last_failed_publish = metrics.end_time

            # Track release types
            if metrics.release_type == "security_auto":
                stats.security_driven_releases += 1
            elif metrics.release_type == "manual":
                stats.manual_releases += 1

        # Save updated stats
        with stats_file.open("w") as f:
            json.dump(stats.to_dict(), f, indent=2)

    def _get_recent_workflows(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent workflow executions."""
        metrics_files = list(self.metrics_dir.glob("workflow-*.json"))
        workflows = []

        for metrics_file in metrics_files:
            try:
                with metrics_file.open() as f:
                    data = json.load(f)
                workflows.append(data)
            except (json.JSONDecodeError, KeyError):
                continue

        # Sort by start time (most recent first)
        workflows.sort(key=lambda x: x.get("start_time", ""), reverse=True)

        return workflows[:limit]

    def _calculate_success_trend(self) -> dict[str, float]:
        """Calculate success rate trend over time."""
        # Simple trend calculation - compare last 7 days to previous 7 days
        current_stats = self.get_publishing_stats(7)
        previous_stats = PublishingStats()

        # Get stats for days 8-14 (previous week)
        from datetime import timedelta

        cutoff_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = cutoff_date - timedelta(days=14)
        end_date = cutoff_date - timedelta(days=7)

        metrics_files = list(self.metrics_dir.glob("workflow-*.json"))

        for metrics_file in metrics_files:
            try:
                with metrics_file.open() as f:
                    data = json.load(f)

                start_time = datetime.fromisoformat(data["start_time"].replace("Z", "+00:00"))

                if start_date <= start_time < end_date:
                    if data["workflow_name"] in ["pypi-publish", "security-driven-release"]:
                        previous_stats.total_attempts += 1
                        if data["status"] == "success" and data.get("publishing_success", False):
                            previous_stats.successful_publishes += 1

            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        current_rate = current_stats.success_rate()
        previous_rate = previous_stats.success_rate()

        return {
            "current_success_rate": current_rate,
            "previous_success_rate": previous_rate,
            "trend_direction": "up"
            if current_rate > previous_rate
            else "down"
            if current_rate < previous_rate
            else "stable",
            "trend_change": current_rate - previous_rate,
        }

    def _calculate_health_status(self, stats: PublishingStats) -> str:
        """Calculate overall health status based on recent metrics."""
        success_rate = stats.success_rate()

        if success_rate >= 95:
            return "excellent"
        if success_rate >= 85:
            return "good"
        if success_rate >= 70:
            return "fair"
        return "poor"


def create_monitoring_dashboard(monitor: WorkflowMonitor, output_file: Path) -> None:
    """Create HTML monitoring dashboard.

    Args:
        monitor: WorkflowMonitor instance
        output_file: Path to output HTML file
    """
    dashboard_data = monitor.generate_dashboard_data()

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PyPI Publishing Monitoring Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .dashboard {{ max-width: 1200px; margin: 0 auto; }}
        .card {{ background: white; border-radius: 8px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric {{ display: inline-block; margin: 10px 20px; text-align: center; }}
        .metric h3 {{ margin: 0; font-size: 2em; color: #333; }}
        .metric p {{ margin: 5px 0 0 0; color: #666; }}
        .status-excellent {{ color: #28a745; }}
        .status-good {{ color: #17a2b8; }}
        .status-fair {{ color: #ffc107; }}
        .status-poor {{ color: #dc3545; }}
        .trend-up {{ color: #28a745; }}
        .trend-down {{ color: #dc3545; }}
        .trend-stable {{ color: #6c757d; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f8f9fa; }}
        .timestamp {{ color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="dashboard">
        <h1>PyPI Publishing Monitoring Dashboard</h1>
        <p class="timestamp">Last updated: {dashboard_data["generated_at"]}</p>

        <div class="card">
            <h2>Publishing Statistics (Last 7 Days)</h2>
            <div class="metric">
                <h3>{dashboard_data["publishing_stats"]["last_7_days"]["total_attempts"]}</h3>
                <p>Total Attempts</p>
            </div>
            <div class="metric">
                <h3>{dashboard_data["publishing_stats"]["last_7_days"]["successful_publishes"]}</h3>
                <p>Successful</p>
            </div>
            <div class="metric">
                <h3>{dashboard_data["publishing_stats"]["last_7_days"]["success_rate_percent"]}%</h3>
                <p>Success Rate</p>
            </div>
            <div class="metric">
                <h3 class="status-{dashboard_data["health_status"]}">{dashboard_data["health_status"].title()}</h3>
                <p>Health Status</p>
            </div>
        </div>

        <div class="card">
            <h2>Release Types (Last 7 Days)</h2>
            <div class="metric">
                <h3>{dashboard_data["publishing_stats"]["last_7_days"]["security_driven_releases"]}</h3>
                <p>Security-Driven</p>
            </div>
            <div class="metric">
                <h3>{dashboard_data["publishing_stats"]["last_7_days"]["manual_releases"]}</h3>
                <p>Manual</p>
            </div>
        </div>

        <div class="card">
            <h2>Success Rate Trend</h2>
            <div class="metric">
                <h3 class="trend-{dashboard_data["success_trend"]["trend_direction"]}">{dashboard_data["success_trend"]["current_success_rate"]:.1f}%</h3>
                <p>Current (7 days)</p>
            </div>
            <div class="metric">
                <h3>{dashboard_data["success_trend"]["previous_success_rate"]:.1f}%</h3>
                <p>Previous (7 days)</p>
            </div>
            <div class="metric">
                <h3 class="trend-{dashboard_data["success_trend"]["trend_direction"]}">{dashboard_data["success_trend"]["trend_change"]:+.1f}%</h3>
                <p>Change</p>
            </div>
        </div>

        <div class="card">
            <h2>Recent Workflow Executions</h2>
            <table>
                <thead>
                    <tr>
                        <th>Workflow</th>
                        <th>Status</th>
                        <th>Duration</th>
                        <th>Release Type</th>
                        <th>Started</th>
                    </tr>
                </thead>
                <tbody>"""

    for workflow in dashboard_data["recent_workflows"]:
        duration = (
            f"{workflow.get('duration_seconds', 0):.1f}s"
            if workflow.get("duration_seconds")
            else "N/A"
        )
        release_type = workflow.get("release_type", "N/A")
        start_time = workflow.get("start_time", "N/A")

        html_content += f"""
                    <tr>
                        <td>{workflow.get("workflow_name", "Unknown")}</td>
                        <td><span class="status-{workflow.get("status", "unknown")}">{workflow.get("status", "Unknown").title()}</span></td>
                        <td>{duration}</td>
                        <td>{release_type}</td>
                        <td>{start_time}</td>
                    </tr>"""

    html_content += """
                </tbody>
            </table>
        </div>

        <div class="card">
            <h2>30-Day Overview</h2>
            <div class="metric">
                <h3>{}</h3>
                <p>Total Attempts</p>
            </div>
            <div class="metric">
                <h3>{}%</h3>
                <p>Success Rate</p>
            </div>
            <div class="metric">
                <h3>{:.1f}s</h3>
                <p>Avg Duration</p>
            </div>
        </div>
    </div>
</body>
</html>""".format(
        dashboard_data["publishing_stats"]["last_30_days"]["total_attempts"],
        dashboard_data["publishing_stats"]["last_30_days"]["success_rate_percent"],
        dashboard_data["publishing_stats"]["last_30_days"]["average_publish_duration"] or 0,
    )

    with output_file.open("w") as f:
        f.write(html_content)


def main() -> None:
    """Main entry point for workflow monitoring."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python workflow_monitoring.py <command> [options]")
        print("Commands:")
        print("  dashboard [--output=path] - Generate monitoring dashboard")
        print("  stats [--days=N] - Show publishing statistics")
        print("  health - Show health status")
        sys.exit(1)

    monitor = WorkflowMonitor()
    command = sys.argv[1]

    if command == "dashboard":
        output_file = Path("monitoring_dashboard.html")
        for arg in sys.argv[2:]:
            if arg.startswith("--output="):
                output_file = Path(arg.split("=", 1)[1])

        create_monitoring_dashboard(monitor, output_file)
        print(f"Dashboard generated: {output_file}")

    elif command == "stats":
        days = 30
        for arg in sys.argv[2:]:
            if arg.startswith("--days="):
                days = int(arg.split("=", 1)[1])

        stats = monitor.get_publishing_stats(days)
        print(json.dumps(stats.to_dict(), indent=2))

    elif command == "health":
        stats = monitor.get_publishing_stats(7)
        health = monitor._calculate_health_status(stats)
        print(f"Health Status: {health}")
        print(f"Success Rate: {stats.success_rate():.1f}%")
        print(f"Total Attempts (7 days): {stats.total_attempts}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
