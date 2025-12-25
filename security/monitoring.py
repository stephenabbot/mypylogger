#!/usr/bin/env python3
"""Data Integrity Monitoring and Alerting System.

This module provides comprehensive monitoring and alerting for security data file integrity.
It implements logging for all validation and repair operations, alerting mechanisms for
unrecoverable corruption, and audit trails for automatic repairs and recoveries.

Requirements addressed: 5.4, 5.5
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
import json
import logging
from pathlib import Path
import smtplib
from typing import Any

from security.error_handling import (
    CorruptionSeverity,
    FileIntegrityInfo,
    RecoveryResult,
)


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Available alert channels."""

    LOG = "log"
    EMAIL = "email"
    WEBHOOK = "webhook"
    CONSOLE = "console"
    FILE = "file"


@dataclass
class AlertConfig:
    """Configuration for alerting system."""

    enabled: bool = True
    channels: list[AlertChannel] = field(
        default_factory=lambda: [AlertChannel.LOG, AlertChannel.CONSOLE]
    )
    email_config: dict[str, str] | None = None
    webhook_url: str | None = None
    alert_file: Path | None = None
    min_severity: AlertSeverity = AlertSeverity.WARNING


@dataclass
class AuditEntry:
    """Audit trail entry for data integrity operations."""

    timestamp: datetime
    operation_type: str  # validation, repair, recovery, alert
    file_path: str
    severity: AlertSeverity
    details: dict[str, Any]
    user: str = "system"
    success: bool = True
    error_message: str | None = None


@dataclass
class IntegrityAlert:
    """Data integrity alert."""

    alert_id: str
    timestamp: datetime
    severity: AlertSeverity
    title: str
    message: str
    file_path: str
    corruption_details: list[str] = field(default_factory=list)
    recovery_attempted: bool = False
    recovery_successful: bool = False
    requires_manual_intervention: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class DataIntegrityMonitor:
    """Monitors data integrity and provides alerting capabilities."""

    def __init__(
        self,
        audit_file: Path | None = None,
        alert_config: AlertConfig | None = None,
        verbose: bool = False,
    ) -> None:
        """Initialize the data integrity monitor.

        Args:
            audit_file: Path to audit log file (defaults to security/audit/integrity.log)
            alert_config: Alert configuration (uses defaults if None)
            verbose: Enable verbose logging
        """
        self.audit_file = audit_file or Path("security/audit/integrity.log")
        self.alert_config = alert_config or AlertConfig()
        self.verbose = verbose

        # Ensure audit directory exists
        self.audit_file.parent.mkdir(parents=True, exist_ok=True)

        # Set up logging
        self.logger = self._setup_logger()

        # Alert tracking
        self.active_alerts: dict[str, IntegrityAlert] = {}
        self.alert_history: list[IntegrityAlert] = []

        # Statistics
        self.stats = {
            "validations_performed": 0,
            "corruptions_detected": 0,
            "repairs_attempted": 0,
            "repairs_successful": 0,
            "alerts_sent": 0,
            "manual_interventions_required": 0,
        }

    def _setup_logger(self) -> logging.Logger:
        """Set up logging for the monitor.

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger("data_integrity_monitor")
        logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)

        if not logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)

            # File handler for audit log
            file_handler = logging.FileHandler(self.audit_file)
            file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        return logger

    def log_validation_operation(
        self,
        file_path: str | Path,
        integrity_info: FileIntegrityInfo,
        operation_details: dict[str, Any] | None = None,
    ) -> None:
        """Log a validation operation to the audit trail.

        Args:
            file_path: Path to the validated file
            integrity_info: File integrity information
            operation_details: Additional operation details
        """
        try:
            self.stats["validations_performed"] += 1

            if integrity_info.is_corrupted:
                self.stats["corruptions_detected"] += 1

            # Create audit entry
            audit_entry = AuditEntry(
                timestamp=datetime.now(timezone.utc),
                operation_type="validation",
                file_path=str(file_path),
                severity=self._map_corruption_to_alert_severity(integrity_info.corruption_severity),
                details={
                    "file_type": integrity_info.file_type,
                    "is_corrupted": integrity_info.is_corrupted,
                    "corruption_severity": integrity_info.corruption_severity.value,
                    "corruption_details": integrity_info.corruption_details,
                    "checksum": integrity_info.checksum,
                    "size_bytes": integrity_info.size_bytes,
                    "backup_available": integrity_info.backup_available,
                    **(operation_details or {}),
                },
                success=not integrity_info.is_corrupted,
            )

            # Write to audit log
            self._write_audit_entry(audit_entry)

            # Generate alert if corruption detected
            if integrity_info.is_corrupted:
                self._generate_corruption_alert(file_path, integrity_info)

            self.logger.info(
                f"Validation logged for {file_path}: "
                f"{'CLEAN' if not integrity_info.is_corrupted else 'CORRUPTED'}"
            )

        except Exception as e:
            self.logger.exception(f"Failed to log validation operation for {file_path}: {e}")

    def log_repair_operation(
        self,
        file_path: str | Path,
        recovery_result: RecoveryResult,
        operation_details: dict[str, Any] | None = None,
    ) -> None:
        """Log a repair operation to the audit trail.

        Args:
            file_path: Path to the repaired file
            recovery_result: Recovery operation result
            operation_details: Additional operation details
        """
        try:
            self.stats["repairs_attempted"] += 1

            if recovery_result.success:
                self.stats["repairs_successful"] += 1

            # Create audit entry
            audit_entry = AuditEntry(
                timestamp=datetime.now(timezone.utc),
                operation_type="repair",
                file_path=str(file_path),
                severity=AlertSeverity.INFO if recovery_result.success else AlertSeverity.ERROR,
                details={
                    "strategy_used": recovery_result.strategy_used.value,
                    "success": recovery_result.success,
                    "recovered_file": recovery_result.recovered_file,
                    "backup_created": recovery_result.backup_created,
                    "data_integrity_verified": recovery_result.data_integrity_verified,
                    "errors": recovery_result.errors,
                    "warnings": recovery_result.warnings,
                    **(operation_details or {}),
                },
                success=recovery_result.success,
                error_message="; ".join(recovery_result.errors) if recovery_result.errors else None,
            )

            # Write to audit log
            self._write_audit_entry(audit_entry)

            # Generate alert for failed repairs
            if not recovery_result.success:
                self._generate_repair_failure_alert(file_path, recovery_result)

            self.logger.info(
                f"Repair logged for {file_path}: "
                f"{'SUCCESS' if recovery_result.success else 'FAILED'}"
            )

        except Exception as e:
            self.logger.exception(f"Failed to log repair operation for {file_path}: {e}")

    def log_manual_intervention_required(
        self, file_path: str | Path, reason: str, details: dict[str, Any] | None = None
    ) -> None:
        """Log when manual intervention is required.

        Args:
            file_path: Path to the file requiring intervention
            reason: Reason for manual intervention
            details: Additional details
        """
        try:
            self.stats["manual_interventions_required"] += 1

            # Create audit entry
            audit_entry = AuditEntry(
                timestamp=datetime.now(timezone.utc),
                operation_type="manual_intervention_required",
                file_path=str(file_path),
                severity=AlertSeverity.CRITICAL,
                details={"reason": reason, "requires_immediate_attention": True, **(details or {})},
                success=False,
                error_message=reason,
            )

            # Write to audit log
            self._write_audit_entry(audit_entry)

            # Generate critical alert
            self._generate_manual_intervention_alert(file_path, reason, details)

            self.logger.critical(f"Manual intervention required for {file_path}: {reason}")

        except Exception as e:
            self.logger.exception(
                f"Failed to log manual intervention requirement for {file_path}: {e}"
            )

    def _map_corruption_to_alert_severity(
        self, corruption_severity: CorruptionSeverity
    ) -> AlertSeverity:
        """Map corruption severity to alert severity.

        Args:
            corruption_severity: Corruption severity level

        Returns:
            Corresponding alert severity
        """
        mapping = {
            CorruptionSeverity.NONE: AlertSeverity.INFO,
            CorruptionSeverity.MINOR: AlertSeverity.WARNING,
            CorruptionSeverity.MODERATE: AlertSeverity.WARNING,
            CorruptionSeverity.SEVERE: AlertSeverity.ERROR,
            CorruptionSeverity.CRITICAL: AlertSeverity.CRITICAL,
        }
        return mapping.get(corruption_severity, AlertSeverity.WARNING)

    def _write_audit_entry(self, entry: AuditEntry) -> None:
        """Write an audit entry to the audit log.

        Args:
            entry: Audit entry to write
        """
        try:
            # Convert to JSON for structured logging
            audit_data = {
                "timestamp": entry.timestamp.isoformat(),
                "operation_type": entry.operation_type,
                "file_path": entry.file_path,
                "severity": entry.severity.value,
                "user": entry.user,
                "success": entry.success,
                "error_message": entry.error_message,
                "details": entry.details,
            }

            # Append to audit file
            with open(self.audit_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(audit_data) + "\n")

        except Exception as e:
            self.logger.exception(f"Failed to write audit entry: {e}")

    def _generate_corruption_alert(
        self, file_path: str | Path, integrity_info: FileIntegrityInfo
    ) -> None:
        """Generate an alert for detected corruption.

        Args:
            file_path: Path to the corrupted file
            integrity_info: File integrity information
        """
        try:
            alert_severity = self._map_corruption_to_alert_severity(
                integrity_info.corruption_severity
            )

            # Skip if below minimum severity
            if self._is_below_min_severity(alert_severity):
                return

            alert_id = (
                f"corruption_{Path(file_path).name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

            alert = IntegrityAlert(
                alert_id=alert_id,
                timestamp=datetime.now(timezone.utc),
                severity=alert_severity,
                title=f"Data Corruption Detected: {Path(file_path).name}",
                message=f"Corruption detected in {file_path} with severity {integrity_info.corruption_severity.value}",
                file_path=str(file_path),
                corruption_details=integrity_info.corruption_details,
                requires_manual_intervention=(
                    integrity_info.corruption_severity == CorruptionSeverity.CRITICAL
                ),
                metadata={
                    "file_type": integrity_info.file_type,
                    "checksum": integrity_info.checksum,
                    "backup_available": integrity_info.backup_available,
                },
            )

            self._send_alert(alert)

        except Exception as e:
            self.logger.exception(f"Failed to generate corruption alert for {file_path}: {e}")

    def _generate_repair_failure_alert(
        self, file_path: str | Path, recovery_result: RecoveryResult
    ) -> None:
        """Generate an alert for failed repair operations.

        Args:
            file_path: Path to the file that failed repair
            recovery_result: Recovery operation result
        """
        try:
            alert_id = (
                f"repair_failure_{Path(file_path).name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

            alert = IntegrityAlert(
                alert_id=alert_id,
                timestamp=datetime.now(timezone.utc),
                severity=AlertSeverity.ERROR,
                title=f"Repair Failed: {Path(file_path).name}",
                message=f"Failed to repair {file_path} using strategy {recovery_result.strategy_used.value}",
                file_path=str(file_path),
                corruption_details=recovery_result.errors,
                recovery_attempted=True,
                recovery_successful=False,
                requires_manual_intervention=True,
                metadata={
                    "strategy_used": recovery_result.strategy_used.value,
                    "backup_created": recovery_result.backup_created,
                    "warnings": recovery_result.warnings,
                },
            )

            self._send_alert(alert)

        except Exception as e:
            self.logger.exception(f"Failed to generate repair failure alert for {file_path}: {e}")

    def _generate_manual_intervention_alert(
        self, file_path: str | Path, reason: str, details: dict[str, Any] | None = None
    ) -> None:
        """Generate an alert for manual intervention requirements.

        Args:
            file_path: Path to the file requiring intervention
            reason: Reason for manual intervention
            details: Additional details
        """
        try:
            alert_id = f"manual_intervention_{Path(file_path).name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            alert = IntegrityAlert(
                alert_id=alert_id,
                timestamp=datetime.now(timezone.utc),
                severity=AlertSeverity.CRITICAL,
                title=f"Manual Intervention Required: {Path(file_path).name}",
                message=f"Manual intervention required for {file_path}: {reason}",
                file_path=str(file_path),
                requires_manual_intervention=True,
                metadata=details or {},
            )

            self._send_alert(alert)

        except Exception as e:
            self.logger.exception(
                f"Failed to generate manual intervention alert for {file_path}: {e}"
            )

    def _is_below_min_severity(self, severity: AlertSeverity) -> bool:
        """Check if alert severity is below minimum threshold.

        Args:
            severity: Alert severity to check

        Returns:
            True if below minimum, False otherwise
        """
        severity_levels = {
            AlertSeverity.INFO: 0,
            AlertSeverity.WARNING: 1,
            AlertSeverity.ERROR: 2,
            AlertSeverity.CRITICAL: 3,
        }

        return severity_levels[severity] < severity_levels[self.alert_config.min_severity]

    def _send_alert(self, alert: IntegrityAlert) -> None:
        """Send an alert through configured channels.

        Args:
            alert: Alert to send
        """
        try:
            if not self.alert_config.enabled:
                return

            # Track alert
            self.active_alerts[alert.alert_id] = alert
            self.alert_history.append(alert)
            self.stats["alerts_sent"] += 1

            # Send through configured channels
            for channel in self.alert_config.channels:
                try:
                    if channel == AlertChannel.LOG:
                        self._send_log_alert(alert)
                    elif channel == AlertChannel.CONSOLE:
                        self._send_console_alert(alert)
                    elif channel == AlertChannel.EMAIL:
                        self._send_email_alert(alert)
                    elif channel == AlertChannel.WEBHOOK:
                        self._send_webhook_alert(alert)
                    elif channel == AlertChannel.FILE:
                        self._send_file_alert(alert)

                except Exception as e:
                    self.logger.exception(f"Failed to send alert via {channel.value}: {e}")

        except Exception as e:
            self.logger.exception(f"Failed to send alert {alert.alert_id}: {e}")

    def _send_log_alert(self, alert: IntegrityAlert) -> None:
        """Send alert to log.

        Args:
            alert: Alert to send
        """
        log_level = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.ERROR: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL,
        }[alert.severity]

        self.logger.log(
            log_level, f"ALERT [{alert.severity.value.upper()}] {alert.title}: {alert.message}"
        )

    def _send_console_alert(self, alert: IntegrityAlert) -> None:
        """Send alert to console.

        Args:
            alert: Alert to send
        """
        severity_icons = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.ERROR: "❌",
            AlertSeverity.CRITICAL: "🚨",
        }

        icon = severity_icons.get(alert.severity, "📢")

        print(f"\n{icon} DATA INTEGRITY ALERT [{alert.severity.value.upper()}]")
        print(f"Title: {alert.title}")
        print(f"File: {alert.file_path}")
        print(f"Message: {alert.message}")
        print(f"Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")

        if alert.corruption_details:
            print("Details:")
            for detail in alert.corruption_details:
                print(f"  - {detail}")

        if alert.requires_manual_intervention:
            print("⚠️  MANUAL INTERVENTION REQUIRED")

        print("-" * 60)

    def _send_email_alert(self, alert: IntegrityAlert) -> None:
        """Send alert via email.

        Args:
            alert: Alert to send
        """
        if not self.alert_config.email_config:
            self.logger.warning("Email alert requested but no email configuration provided")
            return

        try:
            # Create email message
            msg = MIMEMultipart()
            msg["From"] = self.alert_config.email_config.get(
                "from_address", "noreply@security.local"
            )
            msg["To"] = self.alert_config.email_config.get("to_address", "admin@security.local")
            msg["Subject"] = f"[{alert.severity.value.upper()}] {alert.title}"

            # Create email body
            body = f"""
Data Integrity Alert

Severity: {alert.severity.value.upper()}
File: {alert.file_path}
Time: {alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}

Message: {alert.message}

"""

            if alert.corruption_details:
                body += "Corruption Details:\n"
                for detail in alert.corruption_details:
                    body += f"  - {detail}\n"
                body += "\n"

            if alert.requires_manual_intervention:
                body += "⚠️  MANUAL INTERVENTION REQUIRED\n\n"

            body += f"Alert ID: {alert.alert_id}\n"

            msg.attach(MIMEText(body, "plain"))

            # Send email
            smtp_server = self.alert_config.email_config.get("smtp_server", "localhost")
            smtp_port = int(self.alert_config.email_config.get("smtp_port", 587))

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if self.alert_config.email_config.get("use_tls", True):
                    server.starttls()

                username = self.alert_config.email_config.get("username")
                password = self.alert_config.email_config.get("password")

                if username and password:
                    server.login(username, password)

                server.send_message(msg)

            self.logger.info(f"Email alert sent for {alert.alert_id}")

        except Exception as e:
            self.logger.exception(f"Failed to send email alert: {e}")

    def _send_webhook_alert(self, alert: IntegrityAlert) -> None:
        """Send alert via webhook.

        Args:
            alert: Alert to send
        """
        if not self.alert_config.webhook_url:
            self.logger.warning("Webhook alert requested but no webhook URL provided")
            return

        try:
            import requests

            payload = {
                "alert_id": alert.alert_id,
                "timestamp": alert.timestamp.isoformat(),
                "severity": alert.severity.value,
                "title": alert.title,
                "message": alert.message,
                "file_path": alert.file_path,
                "corruption_details": alert.corruption_details,
                "recovery_attempted": alert.recovery_attempted,
                "recovery_successful": alert.recovery_successful,
                "requires_manual_intervention": alert.requires_manual_intervention,
                "metadata": alert.metadata,
            }

            response = requests.post(self.alert_config.webhook_url, json=payload, timeout=30)
            response.raise_for_status()

            self.logger.info(f"Webhook alert sent for {alert.alert_id}")

        except ImportError:
            self.logger.exception("requests library not available for webhook alerts")
        except Exception as e:
            self.logger.exception(f"Failed to send webhook alert: {e}")

    def _send_file_alert(self, alert: IntegrityAlert) -> None:
        """Send alert to file.

        Args:
            alert: Alert to send
        """
        try:
            alert_file = self.alert_config.alert_file or Path("security/alerts/alerts.json")
            alert_file.parent.mkdir(parents=True, exist_ok=True)

            alert_data = {
                "alert_id": alert.alert_id,
                "timestamp": alert.timestamp.isoformat(),
                "severity": alert.severity.value,
                "title": alert.title,
                "message": alert.message,
                "file_path": alert.file_path,
                "corruption_details": alert.corruption_details,
                "recovery_attempted": alert.recovery_attempted,
                "recovery_successful": alert.recovery_successful,
                "requires_manual_intervention": alert.requires_manual_intervention,
                "metadata": alert.metadata,
            }

            # Append to alerts file
            with open(alert_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(alert_data) + "\n")

            self.logger.info(f"File alert written for {alert.alert_id}")

        except Exception as e:
            self.logger.exception(f"Failed to write file alert: {e}")

    def get_audit_summary(
        self, start_time: datetime | None = None, end_time: datetime | None = None
    ) -> dict[str, Any]:
        """Get audit summary for a time period.

        Args:
            start_time: Start time for summary (defaults to beginning of audit log)
            end_time: End time for summary (defaults to now)

        Returns:
            Dictionary with audit summary statistics
        """
        try:
            if not self.audit_file.exists():
                return {"error": "Audit file not found"}

            summary = {
                "period": {
                    "start": start_time.isoformat() if start_time else "beginning",
                    "end": end_time.isoformat()
                    if end_time
                    else datetime.now(timezone.utc).isoformat(),
                },
                "statistics": dict(self.stats),
                "operations": {"validation": 0, "repair": 0, "manual_intervention_required": 0},
                "severity_breakdown": {"info": 0, "warning": 0, "error": 0, "critical": 0},
                "files_affected": set(),
                "recent_alerts": [],
            }

            # Parse audit log
            with open(self.audit_file, encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        entry_time = datetime.fromisoformat(entry["timestamp"])

                        # Filter by time period
                        if start_time and entry_time < start_time:
                            continue
                        if end_time and entry_time > end_time:
                            continue

                        # Count operations
                        op_type = entry["operation_type"]
                        if op_type in summary["operations"]:
                            summary["operations"][op_type] += 1

                        # Count severity
                        severity = entry["severity"]
                        if severity in summary["severity_breakdown"]:
                            summary["severity_breakdown"][severity] += 1

                        # Track affected files
                        summary["files_affected"].add(entry["file_path"])

                    except (json.JSONDecodeError, KeyError) as e:
                        self.logger.warning(f"Invalid audit log entry: {e}")
                        continue

            # Convert set to list for JSON serialization
            summary["files_affected"] = list(summary["files_affected"])

            # Add recent alerts
            summary["recent_alerts"] = [
                {
                    "alert_id": alert.alert_id,
                    "timestamp": alert.timestamp.isoformat(),
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "file_path": alert.file_path,
                }
                for alert in self.alert_history[-10:]  # Last 10 alerts
            ]

            return summary

        except Exception as e:
            self.logger.exception(f"Failed to generate audit summary: {e}")
            return {"error": str(e)}

    def clear_resolved_alerts(self, alert_ids: list[str]) -> int:
        """Clear resolved alerts from active alerts.

        Args:
            alert_ids: List of alert IDs to clear

        Returns:
            Number of alerts cleared
        """
        cleared_count = 0

        for alert_id in alert_ids:
            if alert_id in self.active_alerts:
                del self.active_alerts[alert_id]
                cleared_count += 1
                self.logger.info(f"Cleared resolved alert: {alert_id}")

        return cleared_count

    def get_active_alerts(self) -> list[IntegrityAlert]:
        """Get list of active alerts.

        Returns:
            List of active alerts
        """
        return list(self.active_alerts.values())


# Convenience functions for common monitoring operations
def create_default_monitor(verbose: bool = False) -> DataIntegrityMonitor:
    """Create a default data integrity monitor.

    Args:
        verbose: Enable verbose logging

    Returns:
        Configured DataIntegrityMonitor instance
    """
    return DataIntegrityMonitor(verbose=verbose)


def log_validation_result(
    file_path: str | Path,
    integrity_info: FileIntegrityInfo,
    monitor: DataIntegrityMonitor | None = None,
) -> None:
    """Log a validation result.

    Args:
        file_path: Path to the validated file
        integrity_info: File integrity information
        monitor: Monitor instance (creates default if None)
    """
    if monitor is None:
        monitor = create_default_monitor()

    monitor.log_validation_operation(file_path, integrity_info)


def log_recovery_result(
    file_path: str | Path,
    recovery_result: RecoveryResult,
    monitor: DataIntegrityMonitor | None = None,
) -> None:
    """Log a recovery result.

    Args:
        file_path: Path to the recovered file
        recovery_result: Recovery operation result
        monitor: Monitor instance (creates default if None)
    """
    if monitor is None:
        monitor = create_default_monitor()

    monitor.log_repair_operation(file_path, recovery_result)


def alert_manual_intervention(
    file_path: str | Path,
    reason: str,
    details: dict[str, Any] | None = None,
    monitor: DataIntegrityMonitor | None = None,
) -> None:
    """Alert that manual intervention is required.

    Args:
        file_path: Path to the file requiring intervention
        reason: Reason for manual intervention
        details: Additional details
        monitor: Monitor instance (creates default if None)
    """
    if monitor is None:
        monitor = create_default_monitor()

    monitor.log_manual_intervention_required(file_path, reason, details)
