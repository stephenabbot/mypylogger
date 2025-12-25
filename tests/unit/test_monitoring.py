"""Unit tests for data integrity monitoring and alerting system.

Tests the monitoring functionality for security data file integrity operations.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from security.error_handling import (
    CorruptionSeverity,
    FileIntegrityInfo,
    RecoveryResult,
    RecoveryStrategy,
)
from security.monitoring import (
    AlertChannel,
    AlertConfig,
    AlertSeverity,
    AuditEntry,
    DataIntegrityMonitor,
    IntegrityAlert,
    alert_manual_intervention,
    create_default_monitor,
    log_recovery_result,
    log_validation_result,
)


class TestDataIntegrityMonitor(unittest.TestCase):
    """Test cases for DataIntegrityMonitor class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.audit_file = self.temp_dir / "audit.log"

        # Create test alert config
        self.alert_config = AlertConfig(
            enabled=True,
            channels=[AlertChannel.LOG, AlertChannel.CONSOLE],
            min_severity=AlertSeverity.WARNING,
        )

        self.monitor = DataIntegrityMonitor(
            audit_file=self.audit_file, alert_config=self.alert_config, verbose=False
        )

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_monitor_initialization(self) -> None:
        """Test monitor initialization."""
        assert self.audit_file.parent.exists()
        assert self.monitor.audit_file == self.audit_file
        assert self.monitor.alert_config == self.alert_config
        assert len(self.monitor.active_alerts) == 0
        assert len(self.monitor.alert_history) == 0

    def test_map_corruption_to_alert_severity(self) -> None:
        """Test corruption to alert severity mapping."""
        # Test all corruption severity levels
        assert (
            self.monitor._map_corruption_to_alert_severity(CorruptionSeverity.NONE)
            == AlertSeverity.INFO
        )
        assert (
            self.monitor._map_corruption_to_alert_severity(CorruptionSeverity.MINOR)
            == AlertSeverity.WARNING
        )
        assert (
            self.monitor._map_corruption_to_alert_severity(CorruptionSeverity.MODERATE)
            == AlertSeverity.WARNING
        )
        assert (
            self.monitor._map_corruption_to_alert_severity(CorruptionSeverity.SEVERE)
            == AlertSeverity.ERROR
        )
        assert (
            self.monitor._map_corruption_to_alert_severity(CorruptionSeverity.CRITICAL)
            == AlertSeverity.CRITICAL
        )

    def test_is_below_min_severity(self) -> None:
        """Test minimum severity filtering."""
        # With min severity WARNING
        assert self.monitor._is_below_min_severity(AlertSeverity.INFO)
        assert not self.monitor._is_below_min_severity(AlertSeverity.WARNING)
        assert not self.monitor._is_below_min_severity(AlertSeverity.ERROR)
        assert not self.monitor._is_below_min_severity(AlertSeverity.CRITICAL)

    def test_write_audit_entry(self) -> None:
        """Test audit entry writing."""
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc),
            operation_type="validation",
            file_path="/test/file.yml",
            severity=AlertSeverity.WARNING,
            details={"test": "data"},
            success=True,
        )

        self.monitor._write_audit_entry(entry)

        # Verify audit file was created and contains entry
        assert self.audit_file.exists()

        with self.audit_file.open() as f:
            logged_entry = json.loads(f.read().strip())

        assert logged_entry["operation_type"] == "validation"
        assert logged_entry["file_path"] == "/test/file.yml"
        assert logged_entry["severity"] == "warning"
        assert logged_entry["success"]
        assert logged_entry["details"]["test"] == "data"

    def test_log_validation_operation_clean_file(self) -> None:
        """Test logging validation operation for clean file."""
        integrity_info = FileIntegrityInfo(
            file_path="/test/clean.yml",
            file_type="yaml",
            checksum="abc123",
            size_bytes=1024,
            is_corrupted=False,
            corruption_severity=CorruptionSeverity.NONE,
        )

        self.monitor.log_validation_operation("/test/clean.yml", integrity_info)

        # Check statistics
        assert self.monitor.stats["validations_performed"] == 1
        assert self.monitor.stats["corruptions_detected"] == 0

        # Check audit log
        assert self.audit_file.exists()
        with self.audit_file.open() as f:
            entry = json.loads(f.read().strip())

        assert entry["operation_type"] == "validation"
        assert entry["success"]
        assert not entry["details"]["is_corrupted"]

    def test_log_validation_operation_corrupted_file(self) -> None:
        """Test logging validation operation for corrupted file."""
        integrity_info = FileIntegrityInfo(
            file_path="/test/corrupted.yml",
            file_type="yaml",
            checksum="def456",
            size_bytes=2048,
            is_corrupted=True,
            corruption_severity=CorruptionSeverity.SEVERE,
            corruption_details=["YAML parsing error", "Invalid indentation"],
        )

        with patch.object(self.monitor, "_send_alert") as mock_send_alert:
            self.monitor.log_validation_operation("/test/corrupted.yml", integrity_info)

        # Check statistics
        assert self.monitor.stats["validations_performed"] == 1
        assert self.monitor.stats["corruptions_detected"] == 1

        # Check that alert was generated
        mock_send_alert.assert_called_once()

        # Check audit log
        with self.audit_file.open() as f:
            entry = json.loads(f.read().strip())

        assert entry["operation_type"] == "validation"
        assert not entry["success"]
        assert entry["details"]["is_corrupted"]
        assert entry["details"]["corruption_severity"] == "severe"

    def test_log_repair_operation_success(self) -> None:
        """Test logging successful repair operation."""
        recovery_result = RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.REPAIR_IN_PLACE,
            original_file="/test/repaired.yml",
            recovered_file="/test/repaired.yml",
            backup_created="/test/repaired.backup.yml",
            data_integrity_verified=True,
        )

        self.monitor.log_repair_operation("/test/repaired.yml", recovery_result)

        # Check statistics
        assert self.monitor.stats["repairs_attempted"] == 1
        assert self.monitor.stats["repairs_successful"] == 1

        # Check audit log
        with self.audit_file.open() as f:
            entry = json.loads(f.read().strip())

        assert entry["operation_type"] == "repair"
        assert entry["success"]
        assert entry["details"]["strategy_used"] == "repair_in_place"
        assert entry["details"]["data_integrity_verified"]

    def test_log_repair_operation_failure(self) -> None:
        """Test logging failed repair operation."""
        recovery_result = RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.REPAIR_IN_PLACE,
            original_file="/test/failed.yml",
            errors=["Repair failed", "File too corrupted"],
        )

        with patch.object(self.monitor, "_send_alert") as mock_send_alert:
            self.monitor.log_repair_operation("/test/failed.yml", recovery_result)

        # Check statistics
        assert self.monitor.stats["repairs_attempted"] == 1
        assert self.monitor.stats["repairs_successful"] == 0

        # Check that alert was generated
        mock_send_alert.assert_called_once()

        # Check audit log
        with self.audit_file.open() as f:
            entry = json.loads(f.read().strip())

        assert entry["operation_type"] == "repair"
        assert not entry["success"]
        assert "Repair failed" in entry["error_message"]

    def test_log_manual_intervention_required(self) -> None:
        """Test logging manual intervention requirement."""
        with patch.object(self.monitor, "_send_alert") as mock_send_alert:
            self.monitor.log_manual_intervention_required(
                "/test/critical.yml", "File completely corrupted", {"backup_missing": True}
            )

        # Check statistics
        assert self.monitor.stats["manual_interventions_required"] == 1

        # Check that critical alert was generated
        mock_send_alert.assert_called_once()

        # Check audit log
        with self.audit_file.open() as f:
            entry = json.loads(f.read().strip())

        assert entry["operation_type"] == "manual_intervention_required"
        assert not entry["success"]
        assert entry["severity"] == "critical"
        assert entry["error_message"] == "File completely corrupted"

    def test_send_log_alert(self) -> None:
        """Test sending alert to log."""
        alert = IntegrityAlert(
            alert_id="test_alert_001",
            timestamp=datetime.now(timezone.utc),
            severity=AlertSeverity.ERROR,
            title="Test Alert",
            message="This is a test alert",
            file_path="/test/file.yml",
        )

        with patch.object(self.monitor.logger, "log") as mock_log:
            self.monitor._send_log_alert(alert)

        # Verify log was called with correct level and message
        mock_log.assert_called_once()
        args, _kwargs = mock_log.call_args
        assert args[0] == 40  # ERROR level
        assert "Test Alert" in args[1]

    def test_send_console_alert(self) -> None:
        """Test sending alert to console."""
        alert = IntegrityAlert(
            alert_id="test_alert_002",
            timestamp=datetime.now(timezone.utc),
            severity=AlertSeverity.WARNING,
            title="Test Warning",
            message="This is a test warning",
            file_path="/test/file.yml",
            corruption_details=["Detail 1", "Detail 2"],
        )

        with patch("builtins.print") as mock_print:
            self.monitor._send_console_alert(alert)

        # Verify print was called multiple times
        assert mock_print.call_count > 5

        # Check that key information was printed
        printed_text = " ".join([str(call.args[0]) for call in mock_print.call_args_list])
        assert "Test Warning" in printed_text
        assert "/test/file.yml" in printed_text
        assert "Detail 1" in printed_text

    def test_send_file_alert(self) -> None:
        """Test sending alert to file."""
        alert_file = self.temp_dir / "alerts.json"
        self.monitor.alert_config.alert_file = alert_file

        alert = IntegrityAlert(
            alert_id="test_alert_003",
            timestamp=datetime.now(timezone.utc),
            severity=AlertSeverity.CRITICAL,
            title="Test Critical Alert",
            message="This is a test critical alert",
            file_path="/test/file.yml",
            requires_manual_intervention=True,
        )

        self.monitor._send_file_alert(alert)

        # Verify alert file was created
        assert alert_file.exists()

        # Verify alert content
        with alert_file.open() as f:
            alert_data = json.loads(f.read().strip())

        assert alert_data["alert_id"] == "test_alert_003"
        assert alert_data["severity"] == "critical"
        assert alert_data["title"] == "Test Critical Alert"
        assert alert_data["requires_manual_intervention"]

    def test_send_alert_integration(self) -> None:
        """Test complete alert sending integration."""
        # Configure for log and console channels
        self.monitor.alert_config.channels = [AlertChannel.LOG, AlertChannel.CONSOLE]

        alert = IntegrityAlert(
            alert_id="integration_test_001",
            timestamp=datetime.now(timezone.utc),
            severity=AlertSeverity.ERROR,
            title="Integration Test Alert",
            message="Testing alert integration",
            file_path="/test/integration.yml",
        )

        with patch.object(self.monitor, "_send_log_alert") as mock_log, patch.object(
            self.monitor, "_send_console_alert"
        ) as mock_console:
            self.monitor._send_alert(alert)

        # Verify alert was sent through both channels
        mock_log.assert_called_once_with(alert)
        mock_console.assert_called_once_with(alert)

        # Verify alert tracking
        assert "integration_test_001" in self.monitor.active_alerts
        assert len(self.monitor.alert_history) == 1
        assert self.monitor.stats["alerts_sent"] == 1

    def test_get_audit_summary(self) -> None:
        """Test audit summary generation."""
        # Create some test audit entries
        entries = [
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operation_type": "validation",
                "file_path": "/test/file1.yml",
                "severity": "warning",
                "success": False,
            },
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operation_type": "repair",
                "file_path": "/test/file1.yml",
                "severity": "info",
                "success": True,
            },
        ]

        # Write entries to audit file
        with self.audit_file.open("w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        summary = self.monitor.get_audit_summary()

        # Verify summary structure
        assert "period" in summary
        assert "statistics" in summary
        assert "operations" in summary
        assert "severity_breakdown" in summary
        assert "files_affected" in summary

        # Verify counts
        assert summary["operations"]["validation"] == 1
        assert summary["operations"]["repair"] == 1
        assert summary["severity_breakdown"]["warning"] == 1
        assert summary["severity_breakdown"]["info"] == 1
        assert "/test/file1.yml" in summary["files_affected"]

    def test_clear_resolved_alerts(self) -> None:
        """Test clearing resolved alerts."""
        # Add some active alerts
        alert1 = IntegrityAlert(
            alert_id="alert_001",
            timestamp=datetime.now(timezone.utc),
            severity=AlertSeverity.WARNING,
            title="Alert 1",
            message="Test alert 1",
            file_path="/test/file1.yml",
        )

        alert2 = IntegrityAlert(
            alert_id="alert_002",
            timestamp=datetime.now(timezone.utc),
            severity=AlertSeverity.ERROR,
            title="Alert 2",
            message="Test alert 2",
            file_path="/test/file2.yml",
        )

        self.monitor.active_alerts["alert_001"] = alert1
        self.monitor.active_alerts["alert_002"] = alert2

        # Clear one alert
        cleared_count = self.monitor.clear_resolved_alerts(["alert_001"])

        assert cleared_count == 1
        assert "alert_001" not in self.monitor.active_alerts
        assert "alert_002" in self.monitor.active_alerts

    def test_get_active_alerts(self) -> None:
        """Test getting active alerts."""
        # Initially no active alerts
        active_alerts = self.monitor.get_active_alerts()
        assert len(active_alerts) == 0

        # Add an active alert
        alert = IntegrityAlert(
            alert_id="active_001",
            timestamp=datetime.now(timezone.utc),
            severity=AlertSeverity.WARNING,
            title="Active Alert",
            message="Test active alert",
            file_path="/test/active.yml",
        )

        self.monitor.active_alerts["active_001"] = alert

        # Get active alerts
        active_alerts = self.monitor.get_active_alerts()
        assert len(active_alerts) == 1
        assert active_alerts[0].alert_id == "active_001"


class TestConvenienceFunctions(unittest.TestCase):
    """Test cases for convenience functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_default_monitor(self) -> None:
        """Test creating default monitor."""
        monitor = create_default_monitor(verbose=True)

        assert isinstance(monitor, DataIntegrityMonitor)
        assert monitor.verbose

    @patch("security.monitoring.create_default_monitor")
    def test_log_validation_result(self, mock_create_monitor: MagicMock) -> None:
        """Test log_validation_result convenience function."""
        mock_monitor = MagicMock()
        mock_create_monitor.return_value = mock_monitor

        integrity_info = FileIntegrityInfo(
            file_path="/test/file.yml", file_type="yaml", is_corrupted=False
        )

        log_validation_result("/test/file.yml", integrity_info)

        mock_create_monitor.assert_called_once()
        mock_monitor.log_validation_operation.assert_called_once_with(
            "/test/file.yml", integrity_info
        )

    @patch("security.monitoring.create_default_monitor")
    def test_log_recovery_result(self, mock_create_monitor: MagicMock) -> None:
        """Test log_recovery_result convenience function."""
        mock_monitor = MagicMock()
        mock_create_monitor.return_value = mock_monitor

        recovery_result = RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.REPAIR_IN_PLACE,
            original_file="/test/file.yml",
        )

        log_recovery_result("/test/file.yml", recovery_result)

        mock_create_monitor.assert_called_once()
        mock_monitor.log_repair_operation.assert_called_once_with("/test/file.yml", recovery_result)

    @patch("security.monitoring.create_default_monitor")
    def test_alert_manual_intervention(self, mock_create_monitor: MagicMock) -> None:
        """Test alert_manual_intervention convenience function."""
        mock_monitor = MagicMock()
        mock_create_monitor.return_value = mock_monitor

        alert_manual_intervention("/test/file.yml", "File corrupted", {"details": "test"})

        mock_create_monitor.assert_called_once()
        mock_monitor.log_manual_intervention_required.assert_called_once_with(
            "/test/file.yml", "File corrupted", {"details": "test"}
        )


if __name__ == "__main__":
    unittest.main()
