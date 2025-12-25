"""Security status monitoring and alerting system.

This module provides functionality to monitor security status API availability,
collect performance metrics, and create alerting for status update failures.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from badges.github_pages import GitHubPagesGenerator
from badges.live_status import SecurityStatusManager


@dataclass
class PerformanceMetrics:
    """Performance metrics for security status API."""

    response_time_ms: float
    status_code: int
    content_size_bytes: int
    timestamp: datetime
    endpoint_url: str
    success: bool = True
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "response_time_ms": self.response_time_ms,
            "status_code": self.status_code,
            "content_size_bytes": self.content_size_bytes,
            "timestamp": self.timestamp.isoformat(),
            "endpoint_url": self.endpoint_url,
            "success": self.success,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PerformanceMetrics:
        """Create from dictionary representation."""
        return cls(
            response_time_ms=data["response_time_ms"],
            status_code=data["status_code"],
            content_size_bytes=data["content_size_bytes"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            endpoint_url=data["endpoint_url"],
            success=data.get("success", True),
            error_message=data.get("error_message"),
        )


@dataclass
class UptimeMetrics:
    """Uptime metrics for security status API."""

    total_checks: int = 0
    successful_checks: int = 0
    failed_checks: int = 0
    last_check_time: datetime | None = None
    last_success_time: datetime | None = None
    last_failure_time: datetime | None = None
    consecutive_failures: int = 0
    average_response_time_ms: float = 0.0

    @property
    def uptime_percentage(self) -> float:
        """Calculate uptime percentage."""
        if self.total_checks == 0:
            return 100.0
        return (self.successful_checks / self.total_checks) * 100.0

    @property
    def is_healthy(self) -> bool:
        """Check if service is considered healthy."""
        # Consider healthy if uptime > 95% and no recent consecutive failures
        return self.uptime_percentage > 95.0 and self.consecutive_failures < 3

    def record_success(self, response_time_ms: float) -> None:
        """Record a successful check."""
        now = datetime.now(timezone.utc)
        self.total_checks += 1
        self.successful_checks += 1
        self.last_check_time = now
        self.last_success_time = now
        self.consecutive_failures = 0

        # Update average response time
        if self.successful_checks == 1:
            self.average_response_time_ms = response_time_ms
        else:
            # Running average
            self.average_response_time_ms = (
                self.average_response_time_ms * (self.successful_checks - 1) + response_time_ms
            ) / self.successful_checks

    def record_failure(self) -> None:
        """Record a failed check."""
        now = datetime.now(timezone.utc)
        self.total_checks += 1
        self.failed_checks += 1
        self.last_check_time = now
        self.last_failure_time = now
        self.consecutive_failures += 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total_checks": self.total_checks,
            "successful_checks": self.successful_checks,
            "failed_checks": self.failed_checks,
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "last_success_time": self.last_success_time.isoformat()
            if self.last_success_time
            else None,
            "last_failure_time": self.last_failure_time.isoformat()
            if self.last_failure_time
            else None,
            "consecutive_failures": self.consecutive_failures,
            "average_response_time_ms": self.average_response_time_ms,
            "uptime_percentage": self.uptime_percentage,
            "is_healthy": self.is_healthy,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UptimeMetrics:
        """Create from dictionary representation."""
        return cls(
            total_checks=data.get("total_checks", 0),
            successful_checks=data.get("successful_checks", 0),
            failed_checks=data.get("failed_checks", 0),
            last_check_time=datetime.fromisoformat(data["last_check_time"])
            if data.get("last_check_time")
            else None,
            last_success_time=datetime.fromisoformat(data["last_success_time"])
            if data.get("last_success_time")
            else None,
            last_failure_time=datetime.fromisoformat(data["last_failure_time"])
            if data.get("last_failure_time")
            else None,
            consecutive_failures=data.get("consecutive_failures", 0),
            average_response_time_ms=data.get("average_response_time_ms", 0.0),
        )


@dataclass
class AlertConfig:
    """Configuration for alerting system."""

    response_time_threshold_ms: float = 1000.0  # Alert if response time > 1s
    uptime_threshold_percentage: float = 95.0  # Alert if uptime < 95%
    consecutive_failure_threshold: int = 3  # Alert after 3 consecutive failures
    alert_cooldown_minutes: int = 60  # Wait 60 minutes between similar alerts
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "response_time_threshold_ms": self.response_time_threshold_ms,
            "uptime_threshold_percentage": self.uptime_threshold_percentage,
            "consecutive_failure_threshold": self.consecutive_failure_threshold,
            "alert_cooldown_minutes": self.alert_cooldown_minutes,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AlertConfig:
        """Create from dictionary representation."""
        return cls(
            response_time_threshold_ms=data.get("response_time_threshold_ms", 1000.0),
            uptime_threshold_percentage=data.get("uptime_threshold_percentage", 95.0),
            consecutive_failure_threshold=data.get("consecutive_failure_threshold", 3),
            alert_cooldown_minutes=data.get("alert_cooldown_minutes", 60),
            enabled=data.get("enabled", True),
        )


class SecurityStatusMonitor:
    """Monitors security status API availability and performance."""

    def __init__(
        self,
        base_url: str | None = None,
        metrics_file: Path | None = None,
        alert_config: AlertConfig | None = None,
    ) -> None:
        """Initialize security status monitor.

        Args:
            base_url: Base URL for security status API.
            metrics_file: Path to metrics storage file.
            alert_config: Alert configuration.
        """
        self.base_url = base_url or "https://stabbotco1.github.io/mypylogger"
        self.metrics_file = metrics_file or Path("monitoring/metrics.json")
        self.alert_config = alert_config or AlertConfig()
        self.uptime_metrics = UptimeMetrics()
        self.performance_history: list[PerformanceMetrics] = []
        self.last_alerts: dict[str, datetime] = {}

        # Load existing metrics
        self._load_metrics()

    def check_api_availability(self) -> PerformanceMetrics:
        """Check API availability and measure performance.

        Returns:
            PerformanceMetrics with check results.
        """
        endpoint_url = urljoin(self.base_url, "/security-status/index.json")
        start_time = time.time()

        try:
            # Create request with timeout
            request = Request(endpoint_url)
            request.add_header("User-Agent", "SecurityStatusMonitor/1.0")

            # Make request
            with urlopen(request, timeout=10) as response:
                content = response.read()
                end_time = time.time()

                # Calculate metrics
                response_time_ms = (end_time - start_time) * 1000
                status_code = response.getcode()
                content_size = len(content)

                # Validate JSON content
                try:
                    json.loads(content.decode("utf-8"))
                except json.JSONDecodeError:
                    msg = "Invalid JSON response"
                    raise ValueError(msg)

                # Create metrics
                metrics = PerformanceMetrics(
                    response_time_ms=response_time_ms,
                    status_code=status_code,
                    content_size_bytes=content_size,
                    timestamp=datetime.now(timezone.utc),
                    endpoint_url=endpoint_url,
                    success=True,
                )

                # Update uptime metrics
                self.uptime_metrics.record_success(response_time_ms)

                return metrics

        except (URLError, HTTPError, ValueError, OSError) as e:
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000

            # Create failure metrics
            metrics = PerformanceMetrics(
                response_time_ms=response_time_ms,
                status_code=0,
                content_size_bytes=0,
                timestamp=datetime.now(timezone.utc),
                endpoint_url=endpoint_url,
                success=False,
                error_message=str(e),
            )

            # Update uptime metrics
            self.uptime_metrics.record_failure()

            return metrics

    def run_monitoring_check(self) -> dict[str, Any]:
        """Run complete monitoring check with alerting.

        Returns:
            Dictionary with monitoring results.
        """
        try:
            # Check API availability
            metrics = self.check_api_availability()

            # Add to performance history
            self.performance_history.append(metrics)

            # Keep only last 100 metrics
            if len(self.performance_history) > 100:
                self.performance_history = self.performance_history[-100:]

            # Check for alerts
            alerts = self._check_alerts(metrics)

            # Save metrics
            self._save_metrics()

            return {
                "success": True,
                "metrics": metrics.to_dict(),
                "uptime": self.uptime_metrics.to_dict(),
                "alerts": alerts,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def get_monitoring_summary(self) -> dict[str, Any]:
        """Get monitoring summary with current status.

        Returns:
            Dictionary with monitoring summary.
        """
        recent_metrics = self.performance_history[-10:] if self.performance_history else []

        return {
            "uptime": self.uptime_metrics.to_dict(),
            "recent_performance": [m.to_dict() for m in recent_metrics],
            "alert_config": self.alert_config.to_dict(),
            "last_check": self.uptime_metrics.last_check_time.isoformat()
            if self.uptime_metrics.last_check_time
            else None,
            "service_status": "healthy" if self.uptime_metrics.is_healthy else "degraded",
        }

    def _check_alerts(self, metrics: PerformanceMetrics) -> list[dict[str, Any]]:
        """Check for alert conditions and generate alerts.

        Args:
            metrics: Latest performance metrics.

        Returns:
            List of alert dictionaries.
        """
        if not self.alert_config.enabled:
            return []

        alerts = []
        now = datetime.now(timezone.utc)

        # Check response time alert
        if (
            metrics.success
            and metrics.response_time_ms > self.alert_config.response_time_threshold_ms
        ):
            alert_key = "high_response_time"
            if self._should_send_alert(alert_key, now):
                alerts.append(
                    {
                        "type": "high_response_time",
                        "severity": "warning",
                        "message": f"High response time: {metrics.response_time_ms:.1f}ms (threshold: {self.alert_config.response_time_threshold_ms}ms)",
                        "timestamp": now.isoformat(),
                        "metrics": metrics.to_dict(),
                    }
                )
                self.last_alerts[alert_key] = now

        # Check uptime alert
        if self.uptime_metrics.uptime_percentage < self.alert_config.uptime_threshold_percentage:
            alert_key = "low_uptime"
            if self._should_send_alert(alert_key, now):
                alerts.append(
                    {
                        "type": "low_uptime",
                        "severity": "critical",
                        "message": f"Low uptime: {self.uptime_metrics.uptime_percentage:.1f}% (threshold: {self.alert_config.uptime_threshold_percentage}%)",
                        "timestamp": now.isoformat(),
                        "uptime_metrics": self.uptime_metrics.to_dict(),
                    }
                )
                self.last_alerts[alert_key] = now

        # Check consecutive failures alert
        if (
            self.uptime_metrics.consecutive_failures
            >= self.alert_config.consecutive_failure_threshold
        ):
            alert_key = "consecutive_failures"
            if self._should_send_alert(alert_key, now):
                alerts.append(
                    {
                        "type": "consecutive_failures",
                        "severity": "critical",
                        "message": f"Consecutive failures: {self.uptime_metrics.consecutive_failures} (threshold: {self.alert_config.consecutive_failure_threshold})",
                        "timestamp": now.isoformat(),
                        "uptime_metrics": self.uptime_metrics.to_dict(),
                    }
                )
                self.last_alerts[alert_key] = now

        # Check API failure alert
        if not metrics.success:
            alert_key = "api_failure"
            if self._should_send_alert(alert_key, now):
                alerts.append(
                    {
                        "type": "api_failure",
                        "severity": "error",
                        "message": f"API check failed: {metrics.error_message}",
                        "timestamp": now.isoformat(),
                        "metrics": metrics.to_dict(),
                    }
                )
                self.last_alerts[alert_key] = now

        return alerts

    def _should_send_alert(self, alert_key: str, current_time: datetime) -> bool:
        """Check if alert should be sent based on cooldown period.

        Args:
            alert_key: Unique key for the alert type.
            current_time: Current timestamp.

        Returns:
            True if alert should be sent, False otherwise.
        """
        if alert_key not in self.last_alerts:
            return True

        last_alert_time = self.last_alerts[alert_key]
        cooldown_delta = current_time - last_alert_time
        cooldown_minutes = cooldown_delta.total_seconds() / 60

        return cooldown_minutes >= self.alert_config.alert_cooldown_minutes

    def _load_metrics(self) -> None:
        """Load metrics from storage file."""
        try:
            if not self.metrics_file.exists():
                return

            with self.metrics_file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            # Load uptime metrics
            if "uptime_metrics" in data:
                self.uptime_metrics = UptimeMetrics.from_dict(data["uptime_metrics"])

            # Load performance history
            if "performance_history" in data:
                self.performance_history = [
                    PerformanceMetrics.from_dict(m) for m in data["performance_history"]
                ]

            # Load last alerts
            if "last_alerts" in data:
                self.last_alerts = {
                    key: datetime.fromisoformat(timestamp)
                    for key, timestamp in data["last_alerts"].items()
                }

        except Exception:
            # If loading fails, start with fresh metrics
            pass

    def _save_metrics(self) -> None:
        """Save metrics to storage file."""
        try:
            # Ensure directory exists
            self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "uptime_metrics": self.uptime_metrics.to_dict(),
                "performance_history": [m.to_dict() for m in self.performance_history],
                "last_alerts": {
                    key: timestamp.isoformat() for key, timestamp in self.last_alerts.items()
                },
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            with self.metrics_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        except Exception:
            # If saving fails, continue without persistence
            pass


class StatusUpdateMonitor:
    """Monitors security status update processes for failures."""

    def __init__(
        self,
        status_manager: SecurityStatusManager | None = None,
        pages_generator: GitHubPagesGenerator | None = None,
        alert_config: AlertConfig | None = None,
    ) -> None:
        """Initialize status update monitor.

        Args:
            status_manager: Security status manager instance.
            pages_generator: GitHub Pages generator instance.
            alert_config: Alert configuration.
        """
        self.status_manager = status_manager or SecurityStatusManager()
        self.pages_generator = pages_generator or GitHubPagesGenerator()
        self.alert_config = alert_config or AlertConfig()

    def monitor_status_update(self) -> dict[str, Any]:
        """Monitor status update process and detect failures.

        Returns:
            Dictionary with monitoring results.
        """
        try:
            start_time = time.time()

            # Test status manager update
            status_manager_result = self._test_status_manager_update()

            # Test pages generator update
            pages_generator_result = self._test_pages_generator_update()

            end_time = time.time()
            total_time = (end_time - start_time) * 1000

            # Determine overall success
            overall_success = status_manager_result["success"] and pages_generator_result["success"]

            alerts = []
            if not overall_success and self.alert_config.enabled:
                alerts.append(
                    {
                        "type": "status_update_failure",
                        "severity": "error",
                        "message": "Security status update process failed",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "details": {
                            "status_manager": status_manager_result,
                            "pages_generator": pages_generator_result,
                        },
                    }
                )

            return {
                "success": overall_success,
                "total_time_ms": total_time,
                "status_manager": status_manager_result,
                "pages_generator": pages_generator_result,
                "alerts": alerts,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def _test_status_manager_update(self) -> dict[str, Any]:
        """Test status manager update functionality.

        Returns:
            Dictionary with test results.
        """
        try:
            start_time = time.time()

            # Test getting current status
            current_status = self.status_manager.get_current_status()

            # Test updating status (this should work even if no reports exist)
            updated_status = self.status_manager.update_status()

            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000

            return {
                "success": True,
                "duration_ms": duration_ms,
                "has_current_status": current_status is not None,
                "updated_status_grade": updated_status.security_grade,
                "vulnerability_count": updated_status.vulnerability_summary.total,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration_ms": 0,
            }

    def _test_pages_generator_update(self) -> dict[str, Any]:
        """Test pages generator update functionality.

        Returns:
            Dictionary with test results.
        """
        try:
            start_time = time.time()

            # Test generating API endpoint
            self.pages_generator.generate_api_endpoint()

            # Test generating HTML page
            self.pages_generator.generate_html_page()

            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000

            # Check if files were created
            api_file = self.pages_generator.pages_dir / "index.json"
            html_file = self.pages_generator.pages_dir / "index.html"

            return {
                "success": True,
                "duration_ms": duration_ms,
                "api_file_exists": api_file.exists(),
                "html_file_exists": html_file.exists(),
                "pages_dir": str(self.pages_generator.pages_dir),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration_ms": 0,
            }


def get_default_monitor() -> SecurityStatusMonitor:
    """Get default security status monitor instance.

    Returns:
        SecurityStatusMonitor with default configuration.
    """
    return SecurityStatusMonitor()


def get_default_update_monitor() -> StatusUpdateMonitor:
    """Get default status update monitor instance.

    Returns:
        StatusUpdateMonitor with default configuration.
    """
    return StatusUpdateMonitor()


def run_monitoring_check(
    base_url: str | None = None,
    metrics_file: Path | None = None,
    alert_config: AlertConfig | None = None,
) -> dict[str, Any]:
    """Run monitoring check with optional custom parameters.

    Args:
        base_url: Base URL for security status API.
        metrics_file: Path to metrics storage file.
        alert_config: Alert configuration.

    Returns:
        Dictionary with monitoring results.
    """
    monitor = SecurityStatusMonitor(base_url, metrics_file, alert_config)
    return monitor.run_monitoring_check()
