#!/usr/bin/env python3
"""YAML Corruption Alerting System.

Generates alerts for unrecoverable YAML corruption in CI/CD workflows.
Integrates with monitoring systems and provides actionable recommendations.

Requirements addressed: 17.5
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import logging
from pathlib import Path
import sys
from typing import Any


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert delivery channels."""

    LOG = "log"
    CONSOLE = "console"
    FILE = "file"
    GITHUB_ANNOTATIONS = "github_annotations"
    WORKFLOW_SUMMARY = "workflow_summary"


@dataclass
class YAMLCorruptionAlert:
    """Alert for YAML corruption issues."""

    severity: AlertSeverity
    title: str
    message: str
    corrupted_files: list[str] = field(default_factory=list)
    recovery_attempted: bool = False
    recovery_successful: bool = False
    workflow_impact: str = "unknown"
    recommendations: list[str] = field(default_factory=list)
    technical_details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class YAMLCorruptionAlerter:
    """Alerting system for YAML corruption issues."""

    def __init__(
        self,
        channels: list[AlertChannel] | None = None,
        output_dir: Path | None = None,
        verbose: bool = False,
    ) -> None:
        """Initialize the alerting system.

        Args:
            channels: Alert delivery channels to use
            output_dir: Directory for file-based alerts
            verbose: Enable verbose logging
        """
        self.channels = channels or [AlertChannel.LOG, AlertChannel.CONSOLE, AlertChannel.FILE]
        self.output_dir = output_dir or Path("security/alerts")
        self.verbose = verbose

        # Set up logging
        self.logger = self._setup_logger()

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _setup_logger(self) -> logging.Logger:
        """Set up logging for the alerter.

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger("yaml_corruption_alerter")
        logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - YAML-ALERT - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def generate_corruption_alert(
        self,
        corrupted_files: list[str],
        validation_results: dict[str, Any],
        recovery_results: dict[str, Any] | None = None,
        workflow_context: dict[str, Any] | None = None,
    ) -> YAMLCorruptionAlert:
        """Generate a comprehensive alert for YAML corruption.

        Args:
            corrupted_files: List of corrupted file paths
            validation_results: Results from YAML validation
            recovery_results: Results from recovery attempts (if any)
            workflow_context: Additional workflow context

        Returns:
            YAMLCorruptionAlert with comprehensive details
        """
        try:
            # Determine alert severity
            severity = self._determine_alert_severity(
                corrupted_files, validation_results, recovery_results
            )

            # Generate alert title and message
            title, message = self._generate_alert_content(
                corrupted_files, validation_results, recovery_results
            )

            # Determine workflow impact
            workflow_impact = self._assess_workflow_impact(validation_results, recovery_results)

            # Generate recommendations
            recommendations = self._generate_recommendations(
                corrupted_files, validation_results, recovery_results
            )

            # Compile technical details
            technical_details = self._compile_technical_details(
                corrupted_files, validation_results, recovery_results, workflow_context
            )

            # Create alert
            alert = YAMLCorruptionAlert(
                severity=severity,
                title=title,
                message=message,
                corrupted_files=corrupted_files,
                recovery_attempted=recovery_results is not None,
                recovery_successful=recovery_results.get("success", False)
                if recovery_results
                else False,
                workflow_impact=workflow_impact,
                recommendations=recommendations,
                technical_details=technical_details,
            )

            self.logger.info(
                f"Generated {severity.value} alert for {len(corrupted_files)} corrupted files"
            )
            return alert

        except Exception as e:
            self.logger.exception(f"Failed to generate corruption alert: {e}")
            # Return a basic alert
            return YAMLCorruptionAlert(
                severity=AlertSeverity.ERROR,
                title="YAML Corruption Alert Generation Failed",
                message=f"Failed to generate proper alert: {e}",
                corrupted_files=corrupted_files,
                recommendations=["Manual investigation required", "Check alerting system logs"],
            )

    def send_alert(self, alert: YAMLCorruptionAlert) -> dict[str, bool]:
        """Send alert through configured channels.

        Args:
            alert: Alert to send

        Returns:
            Dictionary mapping channel names to success status
        """
        results = {}

        for channel in self.channels:
            try:
                if channel == AlertChannel.LOG:
                    results[channel.value] = self._send_log_alert(alert)
                elif channel == AlertChannel.CONSOLE:
                    results[channel.value] = self._send_console_alert(alert)
                elif channel == AlertChannel.FILE:
                    results[channel.value] = self._send_file_alert(alert)
                elif channel == AlertChannel.GITHUB_ANNOTATIONS:
                    results[channel.value] = self._send_github_annotation(alert)
                elif channel == AlertChannel.WORKFLOW_SUMMARY:
                    results[channel.value] = self._send_workflow_summary(alert)
                else:
                    self.logger.warning(f"Unknown alert channel: {channel}")
                    results[channel.value] = False

            except Exception as e:
                self.logger.exception(f"Failed to send alert via {channel.value}: {e}")
                results[channel.value] = False

        success_count = sum(1 for success in results.values() if success)
        self.logger.info(f"Alert sent via {success_count}/{len(self.channels)} channels")

        return results

    def _determine_alert_severity(
        self,
        corrupted_files: list[str],
        validation_results: dict[str, Any],
        recovery_results: dict[str, Any] | None,
    ) -> AlertSeverity:
        """Determine the appropriate alert severity.

        Args:
            corrupted_files: List of corrupted files
            validation_results: Validation results
            recovery_results: Recovery results (if any)

        Returns:
            Appropriate AlertSeverity
        """
        # Critical files that require immediate attention
        critical_files = {
            "remediation-timeline.yml",
            "remediation-plans.yml",
            "security-findings.yml",
            "security-config.yml",
        }

        # Check if any critical files are corrupted
        critical_corrupted = any(
            any(critical in str(file_path) for critical in critical_files)
            for file_path in corrupted_files
        )

        # Check validation level
        validation_level = validation_results.get("degradation_level", "unknown")

        # Check recovery success
        recovery_failed = recovery_results and not recovery_results.get("success", False)

        if critical_corrupted and (validation_level == "emergency" or recovery_failed):
            return AlertSeverity.CRITICAL
        if critical_corrupted or validation_level == "emergency":
            return AlertSeverity.ERROR
        if validation_level in ["minimal", "degraded"] or recovery_failed:
            return AlertSeverity.WARNING
        return AlertSeverity.INFO

    def _generate_alert_content(
        self,
        corrupted_files: list[str],
        validation_results: dict[str, Any],
        recovery_results: dict[str, Any] | None,
    ) -> tuple[str, str]:
        """Generate alert title and message.

        Args:
            corrupted_files: List of corrupted files
            validation_results: Validation results
            recovery_results: Recovery results (if any)

        Returns:
            Tuple of (title, message)
        """
        file_count = len(corrupted_files)
        validation_level = validation_results.get("degradation_level", "unknown")

        # Generate title
        if validation_level == "emergency":
            title = f"CRITICAL: {file_count} YAML Files Corrupted - Emergency Mode Active"
        elif validation_level == "minimal":
            title = f"ERROR: {file_count} YAML Files Corrupted - Minimal Mode Active"
        elif validation_level == "degraded":
            title = f"WARNING: {file_count} YAML Files Corrupted - Degraded Mode Active"
        else:
            title = f"NOTICE: {file_count} YAML Files Have Issues"

        # Generate message
        message_parts = [
            f"YAML corruption detected in {file_count} security data files.",
            f"System operating in {validation_level} mode.",
        ]

        if recovery_results:
            if recovery_results.get("success", False):
                message_parts.append("Automatic recovery was successful.")
            else:
                message_parts.append("Automatic recovery failed - manual intervention required.")
        else:
            message_parts.append("No recovery attempts were made.")

        # Add workflow impact
        workflow_impact = self._assess_workflow_impact(validation_results, recovery_results)
        message_parts.append(f"Workflow impact: {workflow_impact}")

        message = " ".join(message_parts)

        return title, message

    def _assess_workflow_impact(
        self, validation_results: dict[str, Any], recovery_results: dict[str, Any] | None
    ) -> str:
        """Assess the impact on workflow execution.

        Args:
            validation_results: Validation results
            recovery_results: Recovery results (if any)

        Returns:
            String describing workflow impact
        """
        validation_level = validation_results.get("degradation_level", "unknown")
        can_continue = validation_results.get("can_continue", False)

        if validation_level == "emergency":
            return "Critical - Workflow may be blocked"
        if validation_level == "minimal":
            return "Severe - Limited functionality available"
        if validation_level == "degraded":
            return "Moderate - Reduced functionality active"
        if can_continue:
            return "Minor - Workflow can continue with warnings"
        return "Unknown - Manual assessment required"

    def _generate_recommendations(
        self,
        corrupted_files: list[str],
        validation_results: dict[str, Any],
        recovery_results: dict[str, Any] | None,
    ) -> list[str]:
        """Generate actionable recommendations.

        Args:
            corrupted_files: List of corrupted files
            validation_results: Validation results
            recovery_results: Recovery results (if any)

        Returns:
            List of recommendation strings
        """
        recommendations = []

        validation_level = validation_results.get("degradation_level", "unknown")

        # Immediate actions based on severity
        if validation_level == "emergency":
            recommendations.extend(
                [
                    "IMMEDIATE: Stop all automated processes",
                    "IMMEDIATE: Restore critical files from backups",
                    "IMMEDIATE: Contact system administrators",
                ]
            )
        elif validation_level in ["minimal", "degraded"]:
            recommendations.extend(
                [
                    "Restore corrupted files from backups if available",
                    "Review YAML syntax in corrupted files",
                    "Consider manual validation of security data",
                ]
            )

        # Recovery-specific recommendations
        if recovery_results:
            if not recovery_results.get("success", False):
                recommendations.extend(
                    [
                        "Review recovery attempt logs for specific errors",
                        "Try manual YAML repair using validation tools",
                        "Check file permissions and disk space",
                    ]
                )
        else:
            recommendations.append("Run YAML validation with repair attempts")

        # File-specific recommendations
        critical_files = {
            "remediation-timeline.yml": "Remediation timeline data",
            "remediation-plans.yml": "Remediation plans data",
            "security-findings.yml": "Security findings data",
            "security-config.yml": "Security configuration",
        }

        for file_path in corrupted_files:
            for critical_file, description in critical_files.items():
                if critical_file in str(file_path):
                    recommendations.append(f"Priority: Restore {description} ({critical_file})")

        # General recommendations
        recommendations.extend(
            [
                "Verify backup systems are functioning properly",
                "Review recent changes to YAML files",
                "Consider implementing additional YAML validation in CI/CD",
                "Monitor for recurring corruption patterns",
            ]
        )

        return recommendations

    def _compile_technical_details(
        self,
        corrupted_files: list[str],
        validation_results: dict[str, Any],
        recovery_results: dict[str, Any] | None,
        workflow_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Compile technical details for the alert.

        Args:
            corrupted_files: List of corrupted files
            validation_results: Validation results
            recovery_results: Recovery results (if any)
            workflow_context: Workflow context (if any)

        Returns:
            Dictionary with technical details
        """
        details = {
            "corrupted_files": corrupted_files,
            "validation_results": validation_results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if recovery_results:
            details["recovery_results"] = recovery_results

        if workflow_context:
            details["workflow_context"] = workflow_context

        # Add file analysis
        file_analysis = {}
        for file_path in corrupted_files:
            file_analysis[file_path] = {
                "exists": Path(file_path).exists(),
                "size": Path(file_path).stat().st_size if Path(file_path).exists() else 0,
                "is_critical": any(
                    critical in str(file_path)
                    for critical in [
                        "remediation-timeline.yml",
                        "remediation-plans.yml",
                        "security-findings.yml",
                        "security-config.yml",
                    ]
                ),
            }

        details["file_analysis"] = file_analysis

        return details

    def _send_log_alert(self, alert: YAMLCorruptionAlert) -> bool:
        """Send alert to logging system.

        Args:
            alert: Alert to send

        Returns:
            True if successful
        """
        try:
            log_level = {
                AlertSeverity.INFO: logging.INFO,
                AlertSeverity.WARNING: logging.WARNING,
                AlertSeverity.ERROR: logging.ERROR,
                AlertSeverity.CRITICAL: logging.CRITICAL,
            }[alert.severity]

            self.logger.log(log_level, f"{alert.title}: {alert.message}")

            if self.verbose:
                self.logger.info(f"Corrupted files: {', '.join(alert.corrupted_files)}")
                self.logger.info(f"Recommendations: {len(alert.recommendations)} items")

            return True

        except Exception as e:
            self.logger.exception(f"Failed to send log alert: {e}")
            return False

    def _send_console_alert(self, alert: YAMLCorruptionAlert) -> bool:
        """Send alert to console output.

        Args:
            alert: Alert to send

        Returns:
            True if successful
        """
        try:
            # Choose appropriate emoji and color
            severity_indicators = {
                AlertSeverity.INFO: "ℹ️",
                AlertSeverity.WARNING: "⚠️",
                AlertSeverity.ERROR: "❌",
                AlertSeverity.CRITICAL: "🚨",
            }

            indicator = severity_indicators.get(alert.severity, "📢")

            print(f"\n{indicator} {alert.title}")
            print(f"   {alert.message}")

            if alert.corrupted_files:
                print(f"   Corrupted files ({len(alert.corrupted_files)}):")
                for file_path in alert.corrupted_files[:5]:  # Show first 5
                    print(f"     - {file_path}")
                if len(alert.corrupted_files) > 5:
                    print(f"     ... and {len(alert.corrupted_files) - 5} more files")

            if alert.recommendations:
                print("   Immediate actions:")
                for rec in alert.recommendations[:3]:  # Show first 3
                    print(f"     • {rec}")
                if len(alert.recommendations) > 3:
                    print(f"     • ... and {len(alert.recommendations) - 3} more recommendations")

            print()  # Empty line for readability
            return True

        except Exception as e:
            print(f"ERROR: Failed to send console alert: {e}", file=sys.stderr)
            return False

    def _send_file_alert(self, alert: YAMLCorruptionAlert) -> bool:
        """Send alert to file system.

        Args:
            alert: Alert to send

        Returns:
            True if successful
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            alert_file = self.output_dir / f"yaml_corruption_alert_{timestamp}.json"

            alert_data = {
                "severity": alert.severity.value,
                "title": alert.title,
                "message": alert.message,
                "corrupted_files": alert.corrupted_files,
                "recovery_attempted": alert.recovery_attempted,
                "recovery_successful": alert.recovery_successful,
                "workflow_impact": alert.workflow_impact,
                "recommendations": alert.recommendations,
                "technical_details": alert.technical_details,
                "timestamp": alert.timestamp,
            }

            with open(alert_file, "w") as f:
                json.dump(alert_data, f, indent=2)

            self.logger.info(f"Alert saved to file: {alert_file}")
            return True

        except Exception as e:
            self.logger.exception(f"Failed to send file alert: {e}")
            return False

    def _send_github_annotation(self, alert: YAMLCorruptionAlert) -> bool:
        """Send alert as GitHub workflow annotation.

        Args:
            alert: Alert to send

        Returns:
            True if successful
        """
        try:
            # Map severity to GitHub annotation type
            annotation_types = {
                AlertSeverity.INFO: "notice",
                AlertSeverity.WARNING: "warning",
                AlertSeverity.ERROR: "error",
                AlertSeverity.CRITICAL: "error",
            }

            annotation_type = annotation_types.get(alert.severity, "notice")

            # Create GitHub workflow command
            print(f"::{annotation_type} title={alert.title}::{alert.message}")

            # Add file-specific annotations for corrupted files
            for file_path in alert.corrupted_files[:3]:  # Limit to avoid spam
                print(
                    f"::{annotation_type} file={file_path}::YAML corruption detected in this file"
                )

            return True

        except Exception as e:
            self.logger.exception(f"Failed to send GitHub annotation: {e}")
            return False

    def _send_workflow_summary(self, alert: YAMLCorruptionAlert) -> bool:
        """Send alert to GitHub workflow summary.

        Args:
            alert: Alert to send

        Returns:
            True if successful
        """
        try:
            # Check if we're in a GitHub Actions environment
            github_step_summary = Path(os.environ.get("GITHUB_STEP_SUMMARY", ""))
            if not github_step_summary or not github_step_summary.parent.exists():
                self.logger.warning("Not in GitHub Actions environment, skipping workflow summary")
                return False

            # Choose appropriate emoji
            severity_emojis = {
                AlertSeverity.INFO: "ℹ️",
                AlertSeverity.WARNING: "⚠️",
                AlertSeverity.ERROR: "❌",
                AlertSeverity.CRITICAL: "🚨",
            }

            emoji = severity_emojis.get(alert.severity, "📢")

            # Write to step summary
            with open(github_step_summary, "a") as f:
                f.write(f"\n## {emoji} YAML Corruption Alert\n\n")
                f.write(f"**{alert.title}**\n\n")
                f.write(f"{alert.message}\n\n")

                if alert.corrupted_files:
                    f.write(f"### Corrupted Files ({len(alert.corrupted_files)})\n\n")
                    for file_path in alert.corrupted_files:
                        f.write(f"- `{file_path}`\n")
                    f.write("\n")

                if alert.recommendations:
                    f.write("### Recommended Actions\n\n")
                    for i, rec in enumerate(alert.recommendations[:5], 1):
                        f.write(f"{i}. {rec}\n")
                    if len(alert.recommendations) > 5:
                        f.write(f"... and {len(alert.recommendations) - 5} more recommendations\n")
                    f.write("\n")

                f.write(f"**Workflow Impact:** {alert.workflow_impact}\n")
                f.write(f"**Recovery Attempted:** {'Yes' if alert.recovery_attempted else 'No'}\n")
                if alert.recovery_attempted:
                    f.write(
                        f"**Recovery Successful:** {'Yes' if alert.recovery_successful else 'No'}\n"
                    )
                f.write(f"**Alert Generated:** {alert.timestamp}\n\n")

            return True

        except Exception as e:
            self.logger.exception(f"Failed to send workflow summary: {e}")
            return False


def main() -> int:
    """Main entry point for YAML corruption alerter."""
    parser = argparse.ArgumentParser(description="YAML Corruption Alerting System")

    parser.add_argument(
        "--corrupted-files", nargs="*", default=[], help="List of corrupted file paths"
    )
    parser.add_argument("--validation-results", help="Path to JSON file with validation results")
    parser.add_argument("--recovery-results", help="Path to JSON file with recovery results")
    parser.add_argument("--workflow-context", help="Path to JSON file with workflow context")
    parser.add_argument(
        "--channels",
        nargs="*",
        choices=["log", "console", "file", "github_annotations", "workflow_summary"],
        default=["log", "console", "file"],
        help="Alert channels to use",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("security/alerts"),
        help="Directory for file-based alerts",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    try:
        # Parse input data
        validation_results = {}
        if args.validation_results and Path(args.validation_results).exists():
            with open(args.validation_results) as f:
                validation_results = json.load(f)

        recovery_results = None
        if args.recovery_results and Path(args.recovery_results).exists():
            with open(args.recovery_results) as f:
                recovery_results = json.load(f)

        workflow_context = None
        if args.workflow_context and Path(args.workflow_context).exists():
            with open(args.workflow_context) as f:
                workflow_context = json.load(f)

        # Convert channel names to enums
        channels = [AlertChannel(channel) for channel in args.channels]

        # Initialize alerter
        alerter = YAMLCorruptionAlerter(
            channels=channels, output_dir=args.output_dir, verbose=args.verbose
        )

        # Generate and send alert
        alert = alerter.generate_corruption_alert(
            corrupted_files=args.corrupted_files,
            validation_results=validation_results,
            recovery_results=recovery_results,
            workflow_context=workflow_context,
        )

        send_results = alerter.send_alert(alert)

        # Print summary
        successful_channels = [channel for channel, success in send_results.items() if success]
        failed_channels = [channel for channel, success in send_results.items() if not success]

        print("\n📊 Alert Summary:")
        print(f"   Severity: {alert.severity.value.upper()}")
        print(f"   Corrupted Files: {len(alert.corrupted_files)}")
        print(
            f"   Successful Channels: {', '.join(successful_channels) if successful_channels else 'None'}"
        )
        if failed_channels:
            print(f"   Failed Channels: {', '.join(failed_channels)}")

        # Return appropriate exit code
        if not successful_channels:
            print("❌ All alert channels failed")
            return 1
        if failed_channels:
            print("⚠️ Some alert channels failed")
            return 0  # Partial success
        print("✅ All alerts sent successfully")
        return 0

    except KeyboardInterrupt:
        print("\n⚠️ Alert generation interrupted by user", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"💥 Critical error in YAML corruption alerter: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import os

    sys.exit(main())
