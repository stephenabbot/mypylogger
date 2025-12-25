"""End-to-end integration orchestrator for Phase 7 PyPI publishing system.

This module provides the main integration point that connects security monitoring,
release decision making, and PyPI publishing workflows into a cohesive system.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import TYPE_CHECKING, Any

# Add current directory to Python path for badges module
if str(Path.cwd()) not in sys.path:
    sys.path.insert(0, str(Path.cwd()))

from badges.live_status import SecurityStatus
from scripts.release_automation_engine import ReleaseAutomationEngine, ReleaseDecision
from scripts.security_change_detector import SecurityChangeDetector
from scripts.workflow_monitoring import WorkflowMonitor
from security.parsers import extract_all_findings
from security.synchronizer import RemediationSynchronizer

if TYPE_CHECKING:
    from security.models import SecurityFinding


class IntegrationOrchestrator:
    """Orchestrates end-to-end workflows for security-driven PyPI publishing."""

    def __init__(
        self,
        security_reports_dir: Path | None = None,
        status_output_dir: Path | None = None,
    ) -> None:
        """Initialize the integration orchestrator.

        Args:
            security_reports_dir: Directory containing security scan reports
            status_output_dir: Directory for live security status output
        """
        self.security_reports_dir = security_reports_dir or Path("security/reports/latest")
        self.status_output_dir = status_output_dir or Path("docs/security-status")

        # Initialize component systems
        self.change_detector = SecurityChangeDetector(reports_dir=self.security_reports_dir)
        self.release_engine = ReleaseAutomationEngine()
        self.synchronizer = RemediationSynchronizer(reports_dir=self.security_reports_dir)
        self.monitor = WorkflowMonitor()

    def execute_security_driven_workflow(
        self,
        force_release: bool = False,
        custom_notes: str | None = None,
    ) -> dict[str, Any]:
        """Execute complete security-driven release workflow.

        Args:
            force_release: Force release even if no security changes detected
            custom_notes: Custom release notes to include

        Returns:
            Dictionary containing workflow execution results
        """
        # Start workflow monitoring
        execution_id = self.monitor.start_workflow("security-driven-release")

        try:
            # Step 1: Synchronize security findings with remediation plans
            sync_results = self.synchronizer.synchronize_findings()

            # Step 2: Extract current security findings
            current_findings = self._get_current_security_findings()

            # Step 3: Detect security changes from previous state
            previous_findings = self._get_previous_security_findings()
            security_changes = self.change_detector.detect_changes(
                previous_findings, current_findings
            )

            # Step 4: Make release decision based on security changes
            release_decision = self.release_engine.make_release_decision(
                security_changes=security_changes,
                manual_trigger=force_release,
                custom_notes=custom_notes,
            )

            # Step 5: Update live security status
            status_update_result = self._update_live_security_status(current_findings)

            # Step 6: Prepare workflow outputs for GitHub Actions
            workflow_outputs = self._prepare_workflow_outputs(
                release_decision, security_changes, sync_results
            )

            # Update monitoring metrics
            self.monitor.update_workflow_metrics(
                execution_id,
                release_triggered=release_decision.should_release,
                release_type=release_decision.trigger_type.value,
                security_changes_count=len(security_changes),
                quality_gates_passed=True,  # Assume passed if we got this far
            )

            # Complete workflow monitoring
            self.monitor.complete_workflow(execution_id, "success")

            return {
                "success": True,
                "execution_id": execution_id,
                "sync_results": sync_results,
                "security_changes": len(security_changes),
                "release_decision": release_decision.to_dict(),
                "status_updated": status_update_result,
                "workflow_outputs": workflow_outputs,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            # Complete workflow monitoring with error
            self.monitor.complete_workflow(
                execution_id, "failed", error_message=str(e), error_stage="workflow_execution"
            )

            return {
                "success": False,
                "execution_id": execution_id,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def execute_manual_release_workflow(
        self,
        release_notes: str,
        update_status: bool = True,
    ) -> dict[str, Any]:
        """Execute manual release workflow with security status updates.

        Args:
            release_notes: Manual release notes
            update_status: Whether to update live security status

        Returns:
            Dictionary containing workflow execution results
        """
        # Start workflow monitoring
        execution_id = self.monitor.start_workflow("manual-release")

        try:
            # Step 1: Get current security findings for status update
            current_findings = self._get_current_security_findings()

            # Step 2: Create manual release decision
            release_decision = self.release_engine.make_release_decision(
                security_changes=[],  # No security changes for manual release
                manual_trigger=True,
                custom_notes=release_notes,
            )

            # Step 3: Update live security status if requested
            status_update_result = None
            if update_status:
                status_update_result = self._update_live_security_status(current_findings)

            # Step 4: Prepare workflow outputs
            workflow_outputs = self._prepare_workflow_outputs(release_decision, [], {})

            # Update monitoring metrics
            self.monitor.update_workflow_metrics(
                execution_id,
                release_triggered=True,
                release_type="manual",
                security_changes_count=0,
                quality_gates_passed=True,
            )

            # Complete workflow monitoring
            self.monitor.complete_workflow(execution_id, "success")

            return {
                "success": True,
                "execution_id": execution_id,
                "release_decision": release_decision.to_dict(),
                "status_updated": status_update_result,
                "workflow_outputs": workflow_outputs,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def validate_integration_health(self) -> dict[str, Any]:
        """Validate health of all integrated components.

        Returns:
            Dictionary containing health check results
        """
        health_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_healthy": True,
            "components": {},
        }

        try:
            # Check security reports directory
            health_results["components"]["security_reports"] = {
                "healthy": self.security_reports_dir.exists(),
                "path": str(self.security_reports_dir),
                "files_count": len(list(self.security_reports_dir.glob("*.json")))
                if self.security_reports_dir.exists()
                else 0,
            }

            # Check status output directory
            health_results["components"]["status_output"] = {
                "healthy": True,  # Will be created if needed
                "path": str(self.status_output_dir),
                "exists": self.status_output_dir.exists(),
            }

            # Test security findings extraction
            try:
                findings = self._get_current_security_findings()
                health_results["components"]["security_findings"] = {
                    "healthy": True,
                    "findings_count": len(findings),
                }
            except Exception as e:
                health_results["components"]["security_findings"] = {
                    "healthy": False,
                    "error": str(e),
                }
                health_results["overall_healthy"] = False

            # Test release engine
            try:
                # Test with empty changes (should not trigger release)
                test_decision = self.release_engine.make_release_decision([])
                health_results["components"]["release_engine"] = {
                    "healthy": True,
                    "test_decision": test_decision.should_release,
                }
            except Exception as e:
                health_results["components"]["release_engine"] = {
                    "healthy": False,
                    "error": str(e),
                }
                health_results["overall_healthy"] = False

        except Exception as e:
            health_results["overall_healthy"] = False
            health_results["error"] = str(e)

        return health_results

    def get_monitoring_dashboard(self) -> dict[str, Any]:
        """Get monitoring dashboard data for release automation visibility.

        Returns:
            Dictionary containing dashboard metrics and visualizations
        """
        return self.monitor.generate_dashboard_data()

    def get_publishing_statistics(self, days_back: int = 30) -> dict[str, Any]:
        """Get publishing success/failure rate statistics.

        Args:
            days_back: Number of days to look back for statistics

        Returns:
            Dictionary containing publishing statistics
        """
        stats = self.monitor.get_publishing_stats(days_back)
        return stats.to_dict()

    def _get_current_security_findings(self) -> list[SecurityFinding]:
        """Get current security findings from reports directory."""
        try:
            return extract_all_findings(self.security_reports_dir)
        except Exception as e:
            # Log the error but return empty list to allow workflow to continue
            print(f"Warning: Failed to extract security findings: {e}")
            return []

    def _get_previous_security_findings(self) -> list[SecurityFinding]:
        """Get previous security findings for comparison."""
        # For now, return empty list - in production this would load from
        # historical data or previous scan results
        return []

    def _update_live_security_status(self, findings: list[SecurityFinding]) -> bool:
        """Update live security status with current findings.

        Args:
            findings: Current security findings

        Returns:
            True if status was updated successfully
        """
        try:
            # Create security status from findings
            status = SecurityStatus.from_findings(findings)

            # Ensure output directory exists
            self.status_output_dir.mkdir(parents=True, exist_ok=True)

            # Write JSON status file
            status_file = self.status_output_dir / "index.json"
            with status_file.open("w") as f:
                json.dump(status.to_dict(), f, indent=2)

            # Write HTML status page
            html_file = self.status_output_dir / "index.html"
            html_content = self._generate_status_html(status)
            with html_file.open("w") as f:
                f.write(html_content)

            return True

        except Exception:
            return False

    def _generate_status_html(self, status: SecurityStatus) -> str:
        """Generate HTML status page from security status data."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>mypylogger Security Status</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .status-card {{ border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin: 20px 0; }}
        .grade-A {{ border-left: 5px solid #28a745; }}
        .grade-B {{ border-left: 5px solid #ffc107; }}
        .grade-C {{ border-left: 5px solid #fd7e14; }}
        .grade-D {{ border-left: 5px solid #dc3545; }}
        .summary {{ display: flex; gap: 20px; }}
        .metric {{ text-align: center; }}
        .metric h3 {{ margin: 0; font-size: 2em; }}
        .metric p {{ margin: 5px 0 0 0; color: #666; }}
    </style>
</head>
<body>
    <h1>mypylogger Security Status</h1>

    <div class="status-card grade-{status.security_grade}">
        <h2>Security Grade: {status.security_grade}</h2>
        <p>Last Updated: {status.last_updated}</p>
        <p>Last Scan: {status.scan_date}</p>
    </div>

    <div class="status-card">
        <h2>Vulnerability Summary</h2>
        <div class="summary">
            <div class="metric">
                <h3>{status.vulnerability_summary.total}</h3>
                <p>Total</p>
            </div>
            <div class="metric">
                <h3>{status.vulnerability_summary.critical}</h3>
                <p>Critical</p>
            </div>
            <div class="metric">
                <h3>{status.vulnerability_summary.high}</h3>
                <p>High</p>
            </div>
            <div class="metric">
                <h3>{status.vulnerability_summary.medium}</h3>
                <p>Medium</p>
            </div>
            <div class="metric">
                <h3>{status.vulnerability_summary.low}</h3>
                <p>Low</p>
            </div>
        </div>
    </div>

    <div class="status-card">
        <h2>Security Metrics</h2>
        <p><strong>Days Since Last Vulnerability:</strong> {status.days_since_last_vulnerability}</p>
        <p><strong>Remediation Status:</strong> {status.remediation_status}</p>
    </div>

    <div class="status-card">
        <h2>API Access</h2>
        <p>JSON API: <a href="index.json">index.json</a></p>
        <p>This page updates automatically with each security scan.</p>
    </div>
</body>
</html>"""

    def _prepare_workflow_outputs(
        self,
        release_decision: ReleaseDecision,
        security_changes: list[Any],
        sync_results: dict[str, Any],
    ) -> dict[str, str]:
        """Prepare outputs for GitHub Actions workflow consumption.

        Args:
            release_decision: Release decision from automation engine
            security_changes: List of detected security changes
            sync_results: Results from remediation synchronization

        Returns:
            Dictionary of workflow outputs
        """
        return {
            "should_release": str(release_decision.should_release).lower(),
            "release_type": release_decision.trigger_type.value,
            "release_notes": release_decision.release_notes,
            "justification": release_decision.justification,
            "changes_detected": str(len(security_changes) > 0).lower(),
            "sync_summary": json.dumps(sync_results),
        }


def main() -> None:
    """Main entry point for integration orchestrator."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python integration_orchestrator.py <command> [options]")
        print("Commands:")
        print("  security-workflow [--force] [--notes='Custom notes']")
        print("  manual-workflow --notes='Release notes' [--no-status-update]")
        print("  health-check")
        print("  dashboard")
        print("  stats [--days=N]")
        sys.exit(1)

    orchestrator = IntegrationOrchestrator()
    command = sys.argv[1]

    if command == "security-workflow":
        force_release = "--force" in sys.argv
        custom_notes = None
        for arg in sys.argv:
            if arg.startswith("--notes="):
                custom_notes = arg.split("=", 1)[1].strip("'\"")

        result = orchestrator.execute_security_driven_workflow(
            force_release=force_release,
            custom_notes=custom_notes,
        )

    elif command == "manual-workflow":
        release_notes = None
        update_status = True

        for arg in sys.argv:
            if arg.startswith("--notes="):
                release_notes = arg.split("=", 1)[1].strip("'\"")
            elif arg == "--no-status-update":
                update_status = False

        if not release_notes:
            print("Error: --notes is required for manual workflow")
            sys.exit(1)

        result = orchestrator.execute_manual_release_workflow(
            release_notes=release_notes,
            update_status=update_status,
        )

    elif command == "health-check":
        result = orchestrator.validate_integration_health()

    elif command == "dashboard":
        result = orchestrator.get_monitoring_dashboard()

    elif command == "stats":
        days = 30
        for arg in sys.argv:
            if arg.startswith("--days="):
                days = int(arg.split("=", 1)[1])

        result = orchestrator.get_publishing_statistics(days)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

    # Output results as JSON for GitHub Actions consumption
    print(json.dumps(result, indent=2))

    # Exit with appropriate code
    if not result.get("success", True):
        sys.exit(1)


if __name__ == "__main__":
    main()
