#!/usr/bin/env python3
"""Notification system for PyPI publishing failures.

This script provides failure notification mechanisms for the PyPI publishing workflow,
including GitHub issue creation and detailed failure reporting.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from typing import Any


class PublishingFailureNotifier:
    """Handles notifications for PyPI publishing failures."""

    def __init__(self, github_token: str | None = None) -> None:
        """Initialize failure notifier.

        Args:
            github_token: GitHub API token for issue creation
        """
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")
        self.repository = os.environ.get("GITHUB_REPOSITORY", "unknown/unknown")

    def format_error_for_github(self, error_report: dict[str, Any]) -> str:
        """Format error report for GitHub issue.

        Args:
            error_report: Error report from publishing workflow

        Returns:
            Formatted markdown content for GitHub issue
        """
        if error_report.get("status") == "success":
            return "No errors to report - publishing succeeded."

        errors = error_report.get("errors", [])
        total_errors = error_report.get("total_errors", 0)
        most_severe = error_report.get("most_severe", "unknown")
        summary = error_report.get("summary", "Publishing failed")

        # Create markdown content
        content = f"""# PyPI Publishing Failure Report

## Summary
{summary}

Total Errors: {total_errors}
Most Severe: {most_severe.upper()}
Timestamp: {datetime.utcnow().isoformat()}Z
Repository: {self.repository}

## Error Details

"""

        # Group errors by category
        error_categories = {}
        for error in errors:
            category = error.get("category", "unknown")
            if category not in error_categories:
                error_categories[category] = []
            error_categories[category].append(error)

        for category, category_errors in error_categories.items():
            content += f"### {category.upper()} Errors ({len(category_errors)})\n\n"

            for i, error in enumerate(category_errors, 1):
                severity = error.get("severity", "unknown")
                message = error.get("message", "No message")
                details = error.get("details", "")
                command = error.get("command", "")
                stderr = error.get("stderr", "")
                is_retryable = error.get("is_retryable", False)
                retry_count = error.get("retry_count", 0)

                content += f"#### Error {i}: {severity.upper()}\n\n"
                content += f"**Message:** {message}\n\n"

                if details:
                    content += f"**Details:** {details}\n\n"

                if command:
                    content += f"**Command:** `{command}`\n\n"

                if stderr:
                    # Truncate stderr if too long
                    stderr_display = stderr[:500] + "..." if len(stderr) > 500 else stderr
                    content += f"**Error Output:**\n```\n{stderr_display}\n```\n\n"

                content += f"**Retryable:** {'Yes' if is_retryable else 'No'}\n"
                content += f"**Retry Count:** {retry_count}\n\n"
                content += "---\n\n"

        # Add troubleshooting section
        content += """## Troubleshooting Steps

### For Authentication Errors
1. Check PyPI API token configuration
2. Verify OIDC authentication setup (if applicable)
3. Ensure proper permissions for PyPI publishing

### For Network Errors
1. Check network connectivity
2. Verify PyPI service status
3. Consider retry with exponential backoff

### For Validation Errors
1. Run local package validation: `uv run python scripts/validate_package.py`
2. Check package metadata in `pyproject.toml`
3. Verify all required files are present

### For Build Errors
1. Run local build: `uv build`
2. Check build dependencies
3. Verify source code structure

## Next Steps

1. Review the error details above
2. Apply appropriate troubleshooting steps
3. Fix identified issues
4. Re-run the publishing workflow

## Workflow Information

- **Workflow Run:** ${{ github.run_id }}
- **Commit SHA:** ${{ github.sha }}
- **Branch:** ${{ github.ref_name }}
- **Actor:** ${{ github.actor }}

---

*This issue was automatically created by the PyPI publishing workflow failure notification system.*
"""

        return content

    def create_github_issue(
        self,
        title: str,
        body: str,
        labels: list[str] | None = None,
    ) -> bool:
        """Create GitHub issue for publishing failure.

        Args:
            title: Issue title
            body: Issue body content
            labels: Optional list of labels

        Returns:
            True if issue created successfully, False otherwise
        """
        if not self.github_token:
            print("⚠️  No GitHub token available - cannot create issue")
            return False

        try:
            import json
            from urllib.error import HTTPError, URLError
            import urllib.request

            url = f"https://api.github.com/repos/{self.repository}/issues"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json",
            }

            data = {
                "title": title,
                "body": body,
                "labels": labels or ["bug", "publishing", "automated"],
            }

            request = urllib.request.Request(
                url=url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST"
            )

            response = urllib.request.urlopen(request, timeout=30)

            if response.status == 201:  # Created
                response_data = json.loads(response.read().decode("utf-8"))
                issue_url = response_data.get("html_url", "")
                issue_number = response_data.get("number", "")

                print(f"✅ GitHub issue created: #{issue_number}")
                print(f"🔗 Issue URL: {issue_url}")
                return True
            print(f"❌ Failed to create GitHub issue. Status: {response.status}")
            return False

        except HTTPError as e:
            print(f"❌ HTTP error creating GitHub issue: {e.code} - {e.reason}")
            return False
        except URLError as e:
            print(f"❌ URL error creating GitHub issue: {e.reason}")
            return False
        except Exception as e:
            print(f"❌ Failed to create GitHub issue: {e}")
            return False

    def send_console_notification(self, error_report: dict[str, Any]) -> None:
        """Send console notification for publishing failure.

        Args:
            error_report: Error report from publishing workflow
        """
        if error_report.get("status") == "success":
            print("✅ Publishing succeeded - no notification needed")
            return

        print("\n" + "=" * 80)
        print("🚨 PYPI PUBLISHING FAILURE NOTIFICATION")
        print("=" * 80)

        total_errors = error_report.get("total_errors", 0)
        most_severe = error_report.get("most_severe", "unknown")
        summary = error_report.get("summary", "Publishing failed")

        print(f"Summary: {summary}")
        print(f"Total Errors: {total_errors}")
        print(f"Most Severe: {most_severe.upper()}")
        print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
        print(f"Repository: {self.repository}")

        # Show top 3 most severe errors
        errors = error_report.get("errors", [])
        if errors:
            print("\nTop Errors:")
            print("-" * 40)

            # Sort by severity (critical > high > medium > low)
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            sorted_errors = sorted(
                errors, key=lambda e: severity_order.get(e.get("severity", "low"), 3)
            )

            for i, error in enumerate(sorted_errors[:3], 1):
                severity = error.get("severity", "unknown")
                category = error.get("category", "unknown")
                message = error.get("message", "No message")

                print(f"{i}. [{severity.upper()}] {category.upper()}: {message}")

        print("\n" + "=" * 80)
        print("See full error report for detailed troubleshooting information.")
        print("=" * 80)

    def notify_failure(
        self,
        error_report: dict[str, Any],
        create_issue: bool = False,
        issue_title: str | None = None,
    ) -> bool:
        """Send failure notifications.

        Args:
            error_report: Error report from publishing workflow
            create_issue: Whether to create GitHub issue
            issue_title: Custom issue title

        Returns:
            True if notifications sent successfully, False otherwise
        """
        # Always send console notification
        self.send_console_notification(error_report)

        # Create GitHub issue if requested
        if create_issue and error_report.get("status") != "success":
            if not issue_title:
                most_severe = error_report.get("most_severe", "unknown")
                timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
                issue_title = f"PyPI Publishing Failure - {most_severe.upper()} - {timestamp}"

            issue_body = self.format_error_for_github(error_report)
            return self.create_github_issue(issue_title, issue_body)

        return True


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Notify PyPI publishing failures")
    parser.add_argument(
        "--error-report",
        type=Path,
        required=True,
        help="Path to error report JSON file",
    )
    parser.add_argument(
        "--create-issue",
        action="store_true",
        help="Create GitHub issue for failure",
    )
    parser.add_argument(
        "--issue-title",
        help="Custom title for GitHub issue",
    )
    parser.add_argument(
        "--github-token",
        help="GitHub API token (can also use GITHUB_TOKEN env var)",
    )

    args = parser.parse_args()

    # Load error report
    if not args.error_report.exists():
        print(f"❌ Error report file not found: {args.error_report}")
        sys.exit(1)

    try:
        with args.error_report.open() as f:
            error_report = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load error report: {e}")
        sys.exit(1)

    # Initialize notifier
    notifier = PublishingFailureNotifier(args.github_token)

    # Send notifications
    success = notifier.notify_failure(
        error_report,
        create_issue=args.create_issue,
        issue_title=args.issue_title,
    )

    if success:
        print("✅ Failure notifications sent successfully")
    else:
        print("❌ Some failure notifications failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
