"""Security findings document generator.

This module provides functionality to generate live markdown documents
from security findings and remediation plans.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from security.parsers import extract_all_findings
from security.remediation import RemediationDatastore

if TYPE_CHECKING:
    from security.models import RemediationPlan, SecurityFinding


class FindingsDocumentGenerator:
    """Generates live security findings documents."""

    def __init__(
        self,
        datastore: RemediationDatastore | None = None,
        reports_dir: Path | None = None,
        output_file: Path | None = None,
    ) -> None:
        """Initialize the document generator.

        Args:
            datastore: Remediation datastore instance. If None, uses default.
            reports_dir: Directory containing security reports. If None, uses default.
            output_file: Output file path. If None, uses default location.
        """
        self.datastore = datastore or RemediationDatastore()
        self.reports_dir = reports_dir or Path("security/reports/latest")
        self.output_file = output_file or Path("security/findings/SECURITY_FINDINGS.md")

    def generate_document(self) -> None:
        """Generate the complete security findings document."""
        try:
            # Get current findings and remediation plans
            findings = self._get_current_findings()
            remediation_plans = self._get_remediation_plans(findings)

            # Generate document content
            content = self._generate_document_content(findings, remediation_plans)

            # Ensure output directory exists
            self.output_file.parent.mkdir(parents=True, exist_ok=True)

            # Write document
            with self.output_file.open("w", encoding="utf-8") as f:
                f.write(content)

        except Exception as e:
            error_msg = f"Failed to generate findings document: {e}"
            raise RuntimeError(error_msg) from e

    def _get_current_findings(self) -> list[SecurityFinding]:
        """Get current security findings from reports."""
        try:
            if not self.reports_dir.exists():
                return []

            return extract_all_findings(self.reports_dir)
        except Exception as e:
            error_msg = f"Failed to extract current findings: {e}"
            raise RuntimeError(error_msg) from e

    def _get_remediation_plans(self, findings: list[SecurityFinding]) -> dict[str, RemediationPlan]:
        """Get remediation plans for the given findings."""
        plans = {}
        for finding in findings:
            try:
                plan = self.datastore.get_remediation_plan(finding.finding_id)
                if plan:
                    plans[finding.finding_id] = plan
            except Exception as e:
                # Log error but continue with other plans
                print(f"Warning: Failed to get remediation plan for {finding.finding_id}: {e}")
                continue
        return plans

    def _generate_document_content(
        self, findings: list[SecurityFinding], remediation_plans: dict[str, RemediationPlan]
    ) -> str:
        """Generate the complete document content."""
        # Sort findings by severity (high -> medium -> low -> info)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        sorted_findings = sorted(
            findings, key=lambda f: (severity_order.get(f.severity.lower(), 5), f.finding_id)
        )

        # Generate header
        content = self._generate_header(sorted_findings)

        # Generate findings sections
        content += self._generate_findings_sections(sorted_findings, remediation_plans)

        # Generate remediation summary
        content += self._generate_remediation_summary(remediation_plans)

        return content

    def _generate_header(self, findings: list[SecurityFinding]) -> str:
        """Generate document header with summary statistics."""
        now = datetime.now(timezone.utc)
        total_findings = len(findings)

        # Calculate days since last scan (assume current scan)
        days_since_scan = 0

        # Count findings by severity
        severity_counts = {}
        for finding in findings:
            severity = finding.severity.lower()
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        header = f"""# Security Findings Summary

**Last Updated**: {now.strftime("%Y-%m-%d %H:%M:%S UTC")}
**Total Active Findings**: {total_findings}
**Days Since Last Scan**: {days_since_scan}

"""

        # Add severity breakdown if there are findings
        if findings:
            header += "**Severity Breakdown**:  \n"
            for severity in ["critical", "high", "medium", "low", "info"]:
                if severity in severity_counts:
                    count = severity_counts[severity]
                    header += f"- **{severity.title()}**: {count}  \n"
            header += "\n"

        return header

    def _generate_findings_sections(
        self, findings: list[SecurityFinding], remediation_plans: dict[str, RemediationPlan]
    ) -> str:
        """Generate findings sections organized by severity."""
        if not findings:
            return "## Current Findings\n\nNo active security findings detected.\n\n"

        content = "## Current Findings\n\n"

        # Group findings by severity
        severity_groups = {}
        for finding in findings:
            severity = finding.severity.lower()
            if severity not in severity_groups:
                severity_groups[severity] = []
            severity_groups[severity].append(finding)

        # Generate sections for each severity level
        severity_order = ["critical", "high", "medium", "low", "info"]
        for severity in severity_order:
            if severity in severity_groups:
                content += self._generate_severity_section(
                    severity, severity_groups[severity], remediation_plans
                )

        return content

    def _generate_severity_section(
        self,
        severity: str,
        findings: list[SecurityFinding],
        remediation_plans: dict[str, RemediationPlan],
    ) -> str:
        """Generate a section for findings of a specific severity."""
        section_title = f"### {severity.title()} Severity\n\n"
        content = section_title

        for finding in findings:
            content += self._generate_finding_entry(
                finding, remediation_plans.get(finding.finding_id)
            )

        return content

    def _generate_finding_entry(
        self, finding: SecurityFinding, remediation_plan: RemediationPlan | None
    ) -> str:
        """Generate a single finding entry."""
        # Calculate days active
        now = datetime.now(timezone.utc).date()
        days_active = (now - finding.discovered_date).days

        # Generate finding title
        title = f"#### {finding.finding_id}"
        if finding.description:
            # Extract a short title from description (first part before detailed explanation)
            desc_parts = finding.description.split(".")
            if desc_parts:
                short_desc = desc_parts[0].strip()
                if len(short_desc) > 60:
                    short_desc = short_desc[:57] + "..."
                title += f" - {short_desc}"

        entry = f"{title}\n"

        # Basic finding information
        entry += f"- **Package**: {finding.package} {finding.version}\n"
        entry += f"- **Source**: {finding.source_scanner}\n"
        entry += f"- **Discovered**: {finding.discovered_date.strftime('%Y-%m-%d')} ({days_active} days active)\n"

        # Description and impact
        if finding.description:
            entry += f"- **Description**: {finding.description}\n"
        if finding.impact:
            entry += f"- **Impact**: {finding.impact}\n"

        # Reference URL
        if finding.reference_url:
            entry += f"- **Reference**: {finding.reference_url}\n"

        # Fix information
        fix_available = "Yes" if finding.fix_available else "No"
        if finding.fix_version:
            fix_available += f" ({finding.fix_version})"
        entry += f"- **Fix Available**: {fix_available}\n"

        # Remediation information from plan
        if remediation_plan:
            entry += f"- **Remediation**: {remediation_plan.planned_action}\n"
            if remediation_plan.target_date:
                entry += (
                    f"- **Planned Fix Date**: {remediation_plan.target_date.strftime('%Y-%m-%d')}\n"
                )
            entry += f"- **Assigned To**: {remediation_plan.assigned_to}\n"
            if remediation_plan.workaround and remediation_plan.workaround != "None identified":
                entry += f"- **Workaround**: {remediation_plan.workaround}\n"

        entry += "\n"
        return entry

    def _generate_remediation_summary(self, remediation_plans: dict[str, RemediationPlan]) -> str:
        """Generate remediation summary section."""
        if not remediation_plans:
            return "## Remediation Summary\n\nNo remediation plans available.\n\n"

        # Count plans by status
        status_counts = {}
        priority_counts = {}
        overdue_count = 0

        for plan in remediation_plans.values():
            # Count by status
            status = plan.status
            status_counts[status] = status_counts.get(status, 0) + 1

            # Count by priority
            priority = plan.priority
            priority_counts[priority] = priority_counts.get(priority, 0) + 1

            # Count overdue plans
            if plan.is_overdue():
                overdue_count += 1

        # Generate summary
        content = "## Remediation Summary\n\n"

        # Overall statistics
        total_plans = len(remediation_plans)
        content += f"**Total Plans**: {total_plans}  \n"

        # Status breakdown with more descriptive names
        status_display_names = {
            "new": "New",
            "in_progress": "In Progress",
            "awaiting_upstream": "Awaiting Upstream",
            "completed": "Completed",
            "on_hold": "On Hold",
            "cancelled": "Cancelled",
        }

        for status in [
            "new",
            "in_progress",
            "awaiting_upstream",
            "completed",
            "on_hold",
            "cancelled",
        ]:
            if status in status_counts:
                display_name = status_display_names.get(status, status.replace("_", " ").title())
                content += f"**{display_name}**: {status_counts[status]}  \n"

        # Priority breakdown
        if priority_counts:
            content += "\n**Priority Breakdown**:  \n"
            for priority in ["critical", "high", "medium", "low"]:
                if priority in priority_counts:
                    content += f"**{priority.title()}**: {priority_counts[priority]}  \n"

        # Overdue plans
        if overdue_count > 0:
            content += f"\n**⚠️ Overdue Plans**: {overdue_count}  \n"

        content += "\n"
        return content


def get_default_generator() -> FindingsDocumentGenerator:
    """Get a default findings document generator instance."""
    return FindingsDocumentGenerator()


def generate_findings_document(
    datastore: RemediationDatastore | None = None,
    reports_dir: Path | None = None,
    output_file: Path | None = None,
) -> None:
    """Generate security findings document with optional custom parameters.

    Args:
        datastore: Remediation datastore instance. If None, uses default.
        reports_dir: Directory containing security reports. If None, uses default.
        output_file: Output file path. If None, uses default location.
    """
    generator = FindingsDocumentGenerator(datastore, reports_dir, output_file)
    generator.generate_document()
