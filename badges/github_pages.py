"""GitHub Pages security status API implementation.

This module provides functionality to create and manage GitHub Pages
endpoints for live security status reporting.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from badges.live_status import SecurityStatus, SecurityStatusManager


class GitHubPagesGenerator:
    """Generates GitHub Pages content for security status API."""

    def __init__(
        self,
        pages_dir: Path | None = None,
        status_manager: SecurityStatusManager | None = None,
    ) -> None:
        """Initialize GitHub Pages generator.

        Args:
            pages_dir: Directory for GitHub Pages content.
            status_manager: Security status manager instance.
        """
        self.pages_dir = pages_dir or Path("security-status")
        self.status_manager = status_manager or SecurityStatusManager()

    def generate_api_endpoint(self) -> None:
        """Generate JSON API endpoint for security status.

        Creates security-status/index.json with current security status data.
        """
        try:
            # Get current security status
            status = self.status_manager.update_status()

            # Ensure pages directory exists
            self.pages_dir.mkdir(parents=True, exist_ok=True)

            # Create JSON API endpoint
            api_file = self.pages_dir / "index.json"
            with api_file.open("w", encoding="utf-8") as f:
                f.write(status.to_json())

            # Create CORS-friendly version
            self._create_cors_endpoint(status)

        except Exception as e:
            error_msg = f"Failed to generate API endpoint: {e}"
            raise RuntimeError(error_msg) from e

    def generate_html_page(self) -> None:
        """Generate HTML page for human-readable security status.

        Creates security-status/index.html with formatted security information.
        """
        try:
            # Get current security status
            current_status = self.status_manager.get_current_status()
            if current_status is None:
                # Generate fresh status if none exists
                current_status = self.status_manager.update_status()

            # Ensure pages directory exists
            self.pages_dir.mkdir(parents=True, exist_ok=True)

            # Generate HTML content
            html_content = self._generate_html_content(current_status)

            # Write HTML file
            html_file = self.pages_dir / "index.html"
            with html_file.open("w", encoding="utf-8") as f:
                f.write(html_content)

        except Exception as e:
            error_msg = f"Failed to generate HTML page: {e}"
            raise RuntimeError(error_msg) from e

    def update_all_endpoints(self) -> SecurityStatus:
        """Update both JSON API and HTML endpoints.

        Returns:
            Updated SecurityStatus object.
        """
        try:
            # Generate API endpoint (this updates the status)
            self.generate_api_endpoint()

            # Generate HTML page
            self.generate_html_page()

            # Return current status
            status = self.status_manager.get_current_status()
            if status is None:
                msg = "Failed to retrieve updated status"
                raise RuntimeError(msg)

            return status

        except Exception as e:
            error_msg = f"Failed to update all endpoints: {e}"
            raise RuntimeError(error_msg) from e

    def _create_cors_endpoint(self, status: SecurityStatus) -> None:
        """Create CORS-friendly JSON endpoint.

        Args:
            status: SecurityStatus to serialize.
        """
        # Create JSONP-style endpoint for cross-origin requests
        jsonp_file = self.pages_dir / "status.jsonp"
        jsonp_content = f"securityStatusCallback({status.to_json()});"

        with jsonp_file.open("w", encoding="utf-8") as f:
            f.write(jsonp_content)

    def _generate_html_content(self, status: SecurityStatus) -> str:
        """Generate HTML content for security status page.

        Args:
            status: SecurityStatus to display.

        Returns:
            HTML content string.
        """
        # Format timestamps
        last_updated = status.last_updated.strftime("%Y-%m-%d %H:%M:%S UTC")
        scan_date = status.scan_date.strftime("%Y-%m-%d %H:%M:%S UTC")

        # Generate severity breakdown
        summary = status.vulnerability_summary
        severity_rows = []
        for severity, count in [
            ("Critical", summary.critical),
            ("High", summary.high),
            ("Medium", summary.medium),
            ("Low", summary.low),
            ("Info", summary.info),
        ]:
            if count > 0:
                severity_rows.append(f"            <tr><td>{severity}</td><td>{count}</td></tr>")

        severity_table = (
            "\n".join(severity_rows)
            if severity_rows
            else '            <tr><td colspan="2">No vulnerabilities found</td></tr>'
        )

        # Generate findings list
        findings_html = self._generate_findings_html(status.findings)

        # Determine status color
        grade_colors = {
            "A": "#28a745",  # Green
            "B": "#ffc107",  # Yellow
            "C": "#fd7e14",  # Orange
            "D": "#dc3545",  # Red
            "F": "#6f42c1",  # Purple
        }
        grade_color = grade_colors.get(status.security_grade, "#6c757d")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Status - mypylogger</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .container {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e9ecef;
        }}
        .security-grade {{
            display: inline-block;
            font-size: 3em;
            font-weight: bold;
            color: {grade_color};
            background: rgba(0,0,0,0.05);
            padding: 20px 30px;
            border-radius: 50%;
            margin: 10px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .summary-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            text-align: center;
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            color: #495057;
        }}
        .summary-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #007bff;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }}
        th {{
            background-color: #e9ecef;
            font-weight: 600;
        }}
        .finding {{
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 4px;
            padding: 15px;
            margin: 10px 0;
        }}
        .finding.critical {{ background: #f8d7da; border-color: #f5c6cb; }}
        .finding.high {{ background: #f8d7da; border-color: #f5c6cb; }}
        .finding.medium {{ background: #fff3cd; border-color: #ffeaa7; }}
        .finding.low {{ background: #d1ecf1; border-color: #bee5eb; }}
        .finding-title {{
            font-weight: bold;
            margin-bottom: 8px;
        }}
        .finding-meta {{
            font-size: 0.9em;
            color: #6c757d;
            margin-bottom: 8px;
        }}
        .timestamp {{
            color: #6c757d;
            font-size: 0.9em;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e9ecef;
            color: #6c757d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Security Status</h1>
            <div class="security-grade">{status.security_grade}</div>
            <p>Overall Security Grade</p>
        </div>

        <div class="summary-grid">
            <div class="summary-card">
                <h3>Total Vulnerabilities</h3>
                <div class="value">{summary.total}</div>
            </div>
            <div class="summary-card">
                <h3>Days Since Last Vulnerability</h3>
                <div class="value">{status.days_since_last_vulnerability}</div>
            </div>
            <div class="summary-card">
                <h3>Remediation Status</h3>
                <div class="value">{status.remediation_status.title()}</div>
            </div>
        </div>

        <h2>Vulnerability Breakdown</h2>
        <table>
            <thead>
                <tr>
                    <th>Severity</th>
                    <th>Count</th>
                </tr>
            </thead>
            <tbody>
{severity_table}
            </tbody>
        </table>

        {findings_html}

        <div class="footer">
            <p class="timestamp">Last Updated: {last_updated}</p>
            <p class="timestamp">Last Scan: {scan_date}</p>
            <p><a href="index.json">View JSON API</a> | <a href="https://github.com/stabbotco1/mypylogger/security">GitHub Security</a></p>
        </div>
    </div>
</body>
</html>"""

    def _generate_findings_html(self, findings: list) -> str:
        """Generate HTML for security findings list.

        Args:
            findings: List of SecurityStatusFinding objects.

        Returns:
            HTML string for findings section.
        """
        if not findings:
            return """
        <h2>Current Findings</h2>
        <div class="finding">
            <div class="finding-title">✅ No Security Vulnerabilities Found</div>
            <p>All security scans completed successfully with no vulnerabilities detected.</p>
        </div>"""

        findings_html = ["        <h2>Current Findings</h2>"]

        for finding in findings:
            severity_class = finding.severity.lower()
            fix_status = "✅ Fix Available" if finding.fix_available else "⚠️ No Fix Available"
            if finding.fix_version:
                fix_status += f" (v{finding.fix_version})"

            finding_html = f"""
        <div class="finding {severity_class}">
            <div class="finding-title">{finding.finding_id} - {finding.severity.upper()}</div>
            <div class="finding-meta">
                Package: {finding.package} v{finding.version} |
                Discovered: {finding.discovered_date} ({finding.days_since_discovery} days ago) |
                {fix_status}
            </div>
            <p>{finding.description}</p>"""

            if finding.reference_url:
                finding_html += f'            <p><a href="{finding.reference_url}" target="_blank">View Details</a></p>'

            finding_html += "        </div>"
            findings_html.append(finding_html)

        return "\n".join(findings_html)


class GitHubActionsIntegration:
    """Integration with GitHub Actions for automated status updates."""

    def __init__(self, pages_generator: GitHubPagesGenerator | None = None) -> None:
        """Initialize GitHub Actions integration.

        Args:
            pages_generator: GitHub Pages generator instance.
        """
        self.pages_generator = pages_generator or GitHubPagesGenerator()

    def update_status_workflow(self) -> dict[str, Any]:
        """Update security status and return workflow summary.

        Returns:
            Dictionary with workflow execution summary.
        """
        try:
            start_time = datetime.now()

            # Update all endpoints
            status = self.pages_generator.update_all_endpoints()

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            return {
                "success": True,
                "duration_seconds": duration,
                "status": {
                    "security_grade": status.security_grade,
                    "total_vulnerabilities": status.vulnerability_summary.total,
                    "remediation_status": status.remediation_status,
                },
                "endpoints_updated": [
                    "security-status/index.json",
                    "security-status/index.html",
                    "security-status/status.jsonp",
                ],
                "timestamp": end_time.isoformat(),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def create_workflow_file(self, workflow_path: Path | None = None) -> None:
        """Create GitHub Actions workflow file for status updates.

        Args:
            workflow_path: Path to workflow file.
        """
        if workflow_path is None:
            workflow_path = Path(".github/workflows/update-security-status.yml")

        workflow_content = """name: Update Security Status

on:
  schedule:
    # Run weekly on Sundays at 6 AM UTC
    - cron: '0 6 * * 0'
  workflow_dispatch:
    # Allow manual triggering
  push:
    paths:
      - 'security/reports/latest/**'
      - 'security/findings/**'

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  update-security-status:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install UV
        uses: astral-sh/setup-uv@v3

      - name: Install dependencies
        run: uv sync

      - name: Update security status
        run: |
          uv run python -c "
          from badges.github_pages import GitHubActionsIntegration
          integration = GitHubActionsIntegration()
          result = integration.update_status_workflow()
          print(f'Status update result: {result}')
          if not result['success']:
              exit(1)
          "

      - name: Setup Pages
        uses: actions/configure-pages@v5

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: './security-status'

      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
"""

        # Ensure workflow directory exists
        workflow_path.parent.mkdir(parents=True, exist_ok=True)

        # Write workflow file
        with workflow_path.open("w", encoding="utf-8") as f:
            f.write(workflow_content)


def get_default_pages_generator() -> GitHubPagesGenerator:
    """Get default GitHub Pages generator instance.

    Returns:
        GitHubPagesGenerator with default configuration.
    """
    return GitHubPagesGenerator()


def update_github_pages_status(
    pages_dir: Path | None = None,
    status_manager: SecurityStatusManager | None = None,
) -> SecurityStatus:
    """Update GitHub Pages security status with optional custom parameters.

    Args:
        pages_dir: Directory for GitHub Pages content.
        status_manager: Security status manager instance.

    Returns:
        Updated SecurityStatus object.
    """
    generator = GitHubPagesGenerator(pages_dir, status_manager)
    return generator.update_all_endpoints()
