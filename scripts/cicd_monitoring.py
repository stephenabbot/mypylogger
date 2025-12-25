#!/usr/bin/env python3
"""CI/CD Monitoring and Alerting System.

Implements comprehensive monitoring and alerting for data integrity operations
in CI/CD workflows. Provides logging, audit trails, and notification mechanisms
for unrecoverable data corruption.

Requirements addressed: 18.4, 18.5
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sys
from typing import Any

# Add project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import existing monitoring infrastructure
try:
    from security.error_handling import CorruptionSeverity, FileIntegrityInfo, RecoveryResult
    from security.monitoring import (
        AlertChannel,
        AlertConfig,
        AlertSeverity,
        AuditEntry,
        DataIntegrityMonitor,
        IntegrityAlert,
    )
except ImportError as e:
    print(f"ERROR: Required monitoring modules not available: {e}", file=sys.stderr)
    print("Ensure security modules are properly installed", file=sys.stderr)
    sys.exit(1)


@dataclass
class CICDMonitoringConfig:
    """Configuration for CI/CD monitoring and alerting."""

    workflow_name: str = "cicd-workflow"
    enable_audit_logging: bool = True
    enable_alerting: bool = True
    enable_github_annotations: bool = True
    enable_workflow_summary: bool = True
    alert_channels: list[AlertChannel] = field(
        default_factory=lambda: [AlertChannel.LOG, AlertChannel.CONSOLE, AlertChannel.FILE]
    )
    audit_file: Path | None = None
    alert_file: Path | None = None
    min_alert_severity: AlertSeverity = AlertSeverity.WARNING
    github_token: str | None = None
    verbose: bool = False


@dataclass
class CICDMonitoringResult:
    """Result of CI/CD monitoring operations."""

    success: bool
    audit_entries_created: int = 0
    alerts_generated: int = 0
    github_annotations_created: int = 0
    workflow_summary_updated: bool = False
    audit_file_path: str | None = None
    alert_file_path: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class CICDMonitor:
    """Comprehensive monitoring system for CI/CD workflows."""

    def __init__(self, config: CICDMonitoringConfig | None = None) -> None:
        """Initialize the CI/CD monitor.

        Args:
            config: Monitoring configuration (uses defaults if None)
        """
        self.config = config or CICDMonitoringConfig()

        # Set up paths
        self.audit_file = self.config.audit_file or Path(
            f"security/audit/cicd-{self.config.workflow_name}.log"
        )
        self.alert_file = self.config.alert_file or Path(
            f"security/alerts/cicd-{self.config.workflow_name}.json"
        )

        # Ensure directories exist
        self.audit_file.parent.mkdir(parents=True, exist_ok=True)
        self.alert_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize monitoring components
        self.monitor = self._initialize_monitor()
        self.logger = self._setup_logger()

        # GitHub integration
        self.github_token = self.config.github_token or os.getenv("GITHUB_TOKEN")
        self.github_step_summary = os.getenv("GITHUB_STEP_SUMMARY")

        # Tracking
        self.session_stats = {
            "start_time": datetime.now(timezone.utc),
            "audit_entries": 0,
            "alerts_generated": 0,
            "annotations_created": 0,
            "files_monitored": 0,
            "corruption_events": 0,
            "recovery_events": 0,
            "manual_intervention_events": 0,
        }

    def _initialize_monitor(self) -> DataIntegrityMonitor:
        """Initialize the data integrity monitor.

        Returns:
            Configured DataIntegrityMonitor instance
        """
        alert_config = AlertConfig(
            enabled=self.config.enable_alerting,
            channels=self.config.alert_channels,
            min_severity=self.config.min_alert_severity,
            alert_file=self.alert_file,
        )

        return DataIntegrityMonitor(
            audit_file=self.audit_file, alert_config=alert_config, verbose=self.config.verbose
        )

    def _setup_logger(self) -> logging.Logger:
        """Set up logging for CI/CD monitoring.

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(f"cicd_monitor_{self.config.workflow_name}")
        logger.setLevel(logging.DEBUG if self.config.verbose else logging.INFO)

        if not logger.handlers:
            # Console handler for CI/CD output
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - CICD-MONITOR - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

            # File handler for audit log
            if self.config.enable_audit_logging:
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
        """Log a validation operation with CI/CD-specific enhancements.

        Args:
            file_path: Path to the validated file
            integrity_info: File integrity information
            operation_details: Additional operation details
        """
        try:
            self.session_stats["files_monitored"] += 1

            if integrity_info.is_corrupted:
                self.session_stats["corruption_events"] += 1

            # Log to the underlying monitor
            self.monitor.log_validation_operation(file_path, integrity_info, operation_details)
            self.session_stats["audit_entries"] += 1

            # Create GitHub annotation if enabled
            if self.config.enable_github_annotations:
                self._create_github_annotation(
                    "validation",
                    file_path,
                    integrity_info.corruption_severity,
                    f"File validation: {'CORRUPTED' if integrity_info.is_corrupted else 'CLEAN'}",
                )

            # Log CI/CD specific information
            self.logger.info(
                f"📊 Validation logged: {file_path} - "
                f"{'CORRUPTED' if integrity_info.is_corrupted else 'CLEAN'}"
            )

        except Exception as e:
            self.logger.exception(f"Failed to log validation operation for {file_path}: {e}")

    def log_recovery_operation(
        self,
        file_path: str | Path,
        recovery_result: RecoveryResult,
        operation_details: dict[str, Any] | None = None,
    ) -> None:
        """Log a recovery operation with CI/CD-specific enhancements.

        Args:
            file_path: Path to the recovered file
            recovery_result: Recovery operation result
            operation_details: Additional operation details
        """
        try:
            self.session_stats["recovery_events"] += 1

            # Log to the underlying monitor
            self.monitor.log_repair_operation(file_path, recovery_result, operation_details)
            self.session_stats["audit_entries"] += 1

            # Create GitHub annotation if enabled
            if self.config.enable_github_annotations:
                severity = AlertSeverity.INFO if recovery_result.success else AlertSeverity.ERROR
                self._create_github_annotation(
                    "recovery",
                    file_path,
                    severity,
                    f"Recovery: {'SUCCESS' if recovery_result.success else 'FAILED'} "
                    f"({recovery_result.strategy_used.value})",
                )

            # Log CI/CD specific information
            status = "SUCCESS" if recovery_result.success else "FAILED"
            self.logger.info(f"🔧 Recovery logged: {file_path} - {status}")

        except Exception as e:
            self.logger.exception(f"Failed to log recovery operation for {file_path}: {e}")

    def log_manual_intervention_required(
        self, file_path: str | Path, reason: str, details: dict[str, Any] | None = None
    ) -> None:
        """Log when manual intervention is required with CI/CD-specific enhancements.

        Args:
            file_path: Path to the file requiring intervention
            reason: Reason for manual intervention
            details: Additional details
        """
        try:
            self.session_stats["manual_intervention_events"] += 1

            # Log to the underlying monitor
            self.monitor.log_manual_intervention_required(file_path, reason, details)
            self.session_stats["audit_entries"] += 1

            # Create GitHub annotation if enabled
            if self.config.enable_github_annotations:
                self._create_github_annotation(
                    "manual_intervention",
                    file_path,
                    AlertSeverity.CRITICAL,
                    f"Manual intervention required: {reason}",
                )

            # Log CI/CD specific information
            self.logger.critical(f"🚨 Manual intervention logged: {file_path} - {reason}")

        except Exception as e:
            self.logger.exception(f"Failed to log manual intervention for {file_path}: {e}")

    def _create_github_annotation(
        self,
        operation_type: str,
        file_path: str | Path,
        severity: AlertSeverity | CorruptionSeverity,
        message: str,
    ) -> None:
        """Create a GitHub workflow annotation.

        Args:
            operation_type: Type of operation (validation, recovery, manual_intervention)
            file_path: Path to the file
            severity: Severity level
            message: Annotation message
        """
        try:
            if not self.config.enable_github_annotations:
                return

            # Map severity to GitHub annotation type
            if isinstance(severity, CorruptionSeverity):
                if severity in [CorruptionSeverity.CRITICAL, CorruptionSeverity.SEVERE]:
                    annotation_type = "error"
                elif severity == CorruptionSeverity.MODERATE:
                    annotation_type = "warning"
                else:
                    annotation_type = "notice"
            elif severity == AlertSeverity.CRITICAL:
                annotation_type = "error"
            elif severity in [AlertSeverity.ERROR, AlertSeverity.WARNING]:
                annotation_type = "warning"
            else:
                annotation_type = "notice"

            # Create GitHub annotation
            annotation = (
                f"::{annotation_type} file={file_path},title={operation_type.title()}::{message}"
            )
            print(annotation)

            self.session_stats["annotations_created"] += 1

        except Exception as e:
            self.logger.warning(f"Failed to create GitHub annotation: {e}")

    def generate_workflow_summary(self) -> dict[str, Any]:
        """Generate a comprehensive workflow summary.

        Returns:
            Dictionary with workflow summary data
        """
        try:
            end_time = datetime.now(timezone.utc)
            duration = end_time - self.session_stats["start_time"]

            # Get audit summary from monitor
            audit_summary = self.monitor.get_audit_summary(
                start_time=self.session_stats["start_time"], end_time=end_time
            )

            # Get active alerts
            active_alerts = self.monitor.get_active_alerts()

            return {
                "workflow_name": self.config.workflow_name,
                "session": {
                    "start_time": self.session_stats["start_time"].isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration.total_seconds(),
                },
                "statistics": {
                    "files_monitored": self.session_stats["files_monitored"],
                    "audit_entries_created": self.session_stats["audit_entries"],
                    "alerts_generated": self.session_stats["alerts_generated"],
                    "github_annotations_created": self.session_stats["annotations_created"],
                    "corruption_events": self.session_stats["corruption_events"],
                    "recovery_events": self.session_stats["recovery_events"],
                    "manual_intervention_events": self.session_stats["manual_intervention_events"],
                },
                "audit_summary": audit_summary,
                "active_alerts": [
                    {
                        "alert_id": alert.alert_id,
                        "severity": alert.severity.value,
                        "title": alert.title,
                        "file_path": alert.file_path,
                        "requires_manual_intervention": alert.requires_manual_intervention,
                    }
                    for alert in active_alerts
                ],
                "files": {"audit_log": str(self.audit_file), "alert_log": str(self.alert_file)},
                "recommendations": self._generate_monitoring_recommendations(),
            }

        except Exception as e:
            self.logger.exception(f"Failed to generate workflow summary: {e}")
            return {
                "error": str(e),
                "workflow_name": self.config.workflow_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def _generate_monitoring_recommendations(self) -> list[str]:
        """Generate monitoring-specific recommendations.

        Returns:
            List of recommendation strings
        """
        recommendations = []

        if self.session_stats["corruption_events"] > 0:
            recommendations.append("File corruption detected - review audit logs for details")

        if self.session_stats["manual_intervention_events"] > 0:
            recommendations.append("Manual intervention required - check critical alerts")

        if self.session_stats["recovery_events"] > 0:
            recommendations.append("File recovery operations performed - verify recovered files")

        active_alerts = self.monitor.get_active_alerts()
        critical_alerts = [a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]

        if critical_alerts:
            recommendations.append(
                f"{len(critical_alerts)} critical alerts require immediate attention"
            )

        if self.session_stats["files_monitored"] == 0:
            recommendations.append("No files were monitored - verify monitoring configuration")

        return recommendations

    def update_github_step_summary(self, summary: dict[str, Any]) -> bool:
        """Update GitHub step summary with monitoring information.

        Args:
            summary: Workflow summary data

        Returns:
            True if summary was updated, False otherwise
        """
        try:
            if not self.config.enable_workflow_summary or not self.github_step_summary:
                return False

            # Create markdown summary
            markdown = self._create_markdown_summary(summary)

            # Append to GitHub step summary
            with open(self.github_step_summary, "a") as f:
                f.write(markdown)

            self.logger.info("📄 GitHub step summary updated")
            return True

        except Exception as e:
            self.logger.exception(f"Failed to update GitHub step summary: {e}")
            return False

    def _create_markdown_summary(self, summary: dict[str, Any]) -> str:
        """Create markdown summary for GitHub step summary.

        Args:
            summary: Workflow summary data

        Returns:
            Markdown formatted summary
        """
        stats = summary.get("statistics", {})
        active_alerts = summary.get("active_alerts", [])
        recommendations = summary.get("recommendations", [])

        markdown = f"""
## 📊 Data Integrity Monitoring Summary

**Workflow:** {summary.get("workflow_name", "Unknown")}
**Duration:** {stats.get("duration_seconds", 0):.1f} seconds

### Statistics
- **Files Monitored:** {stats.get("files_monitored", 0)}
- **Corruption Events:** {stats.get("corruption_events", 0)}
- **Recovery Events:** {stats.get("recovery_events", 0)}
- **Manual Interventions:** {stats.get("manual_intervention_events", 0)}
- **Audit Entries:** {stats.get("audit_entries_created", 0)}
- **Alerts Generated:** {stats.get("alerts_generated", 0)}

"""

        if active_alerts:
            markdown += "### 🚨 Active Alerts\n"
            for alert in active_alerts:
                severity_icon = {"critical": "🚨", "error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(
                    alert["severity"], "📢"
                )

                markdown += f"- {severity_icon} **{alert['title']}** ({alert['file_path']})\n"
            markdown += "\n"

        if recommendations:
            markdown += "### 💡 Recommendations\n"
            for rec in recommendations:
                markdown += f"- {rec}\n"
            markdown += "\n"

        # Add file locations
        files = summary.get("files", {})
        if files:
            markdown += "### 📁 Log Files\n"
            if files.get("audit_log"):
                markdown += f"- **Audit Log:** `{files['audit_log']}`\n"
            if files.get("alert_log"):
                markdown += f"- **Alert Log:** `{files['alert_log']}`\n"
            markdown += "\n"

        return markdown

    def create_monitoring_report(self) -> CICDMonitoringResult:
        """Create a comprehensive monitoring report.

        Returns:
            CICDMonitoringResult with monitoring details
        """
        try:
            # Generate workflow summary
            summary = self.generate_workflow_summary()

            # Update GitHub step summary if enabled
            github_summary_updated = False
            if self.config.enable_workflow_summary:
                github_summary_updated = self.update_github_step_summary(summary)

            # Create result
            result = CICDMonitoringResult(
                success=True,
                audit_entries_created=self.session_stats["audit_entries"],
                alerts_generated=self.session_stats["alerts_generated"],
                github_annotations_created=self.session_stats["annotations_created"],
                workflow_summary_updated=github_summary_updated,
                audit_file_path=str(self.audit_file) if self.audit_file.exists() else None,
                alert_file_path=str(self.alert_file) if self.alert_file.exists() else None,
            )

            # Save summary to file
            summary_file = Path(
                f"security/reports/monitoring/cicd-{self.config.workflow_name}-summary.json"
            )
            summary_file.parent.mkdir(parents=True, exist_ok=True)

            with open(summary_file, "w") as f:
                json.dump(summary, f, indent=2)

            self.logger.info(f"📊 Monitoring report created: {summary_file}")

            return result

        except Exception as e:
            self.logger.exception(f"Failed to create monitoring report: {e}")
            return CICDMonitoringResult(success=False, errors=[str(e)])

    def alert_unrecoverable_corruption(
        self, file_paths: list[str | Path], details: dict[str, Any] | None = None
    ) -> None:
        """Alert for unrecoverable data corruption.

        Args:
            file_paths: List of file paths with unrecoverable corruption
            details: Additional details about the corruption
        """
        try:
            for file_path in file_paths:
                self.log_manual_intervention_required(
                    file_path,
                    "Unrecoverable data corruption detected",
                    {
                        "corruption_type": "unrecoverable",
                        "requires_immediate_attention": True,
                        **(details or {}),
                    },
                )

            # Create consolidated alert for multiple files
            if len(file_paths) > 1:
                self.logger.critical(
                    f"🚨 CRITICAL: {len(file_paths)} files have unrecoverable corruption"
                )

                if self.config.enable_github_annotations:
                    files_str = ", ".join(str(p) for p in file_paths[:3])
                    if len(file_paths) > 3:
                        files_str += f" and {len(file_paths) - 3} more"

                    print(
                        f"::error title=Unrecoverable Corruption::Multiple files corrupted: {files_str}"
                    )

        except Exception as e:
            self.logger.exception(f"Failed to alert unrecoverable corruption: {e}")


def main() -> int:
    """Main entry point for CI/CD monitoring."""
    import argparse

    parser = argparse.ArgumentParser(description="CI/CD Monitoring and Alerting for Data Integrity")
    parser.add_argument(
        "--workflow-name", default="cicd-workflow", help="Name of the CI/CD workflow"
    )
    parser.add_argument("--test-monitoring", action="store_true", help="Run monitoring system test")
    parser.add_argument("--generate-report", action="store_true", help="Generate monitoring report")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--output-report", help="Path to write monitoring report JSON file")

    args = parser.parse_args()

    try:
        # Configure monitoring
        config = CICDMonitoringConfig(workflow_name=args.workflow_name, verbose=args.verbose)

        # Initialize monitor
        monitor = CICDMonitor(config)

        if args.test_monitoring:
            # Run monitoring system test
            print("🧪 Testing CI/CD monitoring system...")

            # Simulate some monitoring operations
            from security.error_handling import CorruptionSeverity, FileIntegrityInfo

            # Test validation logging
            test_integrity = FileIntegrityInfo(
                file_path="test-file.yml", file_type="yaml", is_corrupted=False
            )
            monitor.log_validation_operation("test-file.yml", test_integrity)

            # Test corruption logging
            corrupt_integrity = FileIntegrityInfo(
                file_path="corrupt-file.yml",
                file_type="yaml",
                is_corrupted=True,
                corruption_severity=CorruptionSeverity.MODERATE,
                corruption_details=["Test corruption for monitoring"],
            )
            monitor.log_validation_operation("corrupt-file.yml", corrupt_integrity)

            print("✅ Monitoring system test completed")

        if args.generate_report or args.test_monitoring:
            # Generate monitoring report
            result = monitor.create_monitoring_report()

            if args.output_report:
                summary = monitor.generate_workflow_summary()
                with open(args.output_report, "w") as f:
                    json.dump(summary, f, indent=2)
                print(f"📄 Monitoring report saved to: {args.output_report}")

            # Print summary
            print("\n" + "=" * 60)
            print("📊 CI/CD Monitoring Summary")
            print("=" * 60)
            print(f"Workflow: {config.workflow_name}")
            print(f"Success: {'✅ YES' if result.success else '❌ NO'}")
            print(f"Audit Entries: {result.audit_entries_created}")
            print(f"Alerts Generated: {result.alerts_generated}")
            print(f"GitHub Annotations: {result.github_annotations_created}")
            print(
                f"Workflow Summary Updated: {'✅ YES' if result.workflow_summary_updated else '❌ NO'}"
            )

            if result.audit_file_path:
                print(f"Audit Log: {result.audit_file_path}")
            if result.alert_file_path:
                print(f"Alert Log: {result.alert_file_path}")

            if result.errors:
                print("❌ Errors:")
                for error in result.errors:
                    print(f"   - {error}")

            if result.warnings:
                print("⚠️ Warnings:")
                for warning in result.warnings:
                    print(f"   - {warning}")

        return 0 if not args.test_monitoring or result.success else 1

    except KeyboardInterrupt:
        print("\n⚠️ CI/CD monitoring interrupted by user", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"💥 Critical error in CI/CD monitoring: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
