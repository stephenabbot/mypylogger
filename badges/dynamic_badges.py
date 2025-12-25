"""Dynamic README badge integration with live security status.

This module provides functionality to generate and update README badges
that reflect current security posture from live status endpoints.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any
from urllib.parse import quote

from badges.config import get_badge_config
from badges.live_status import SecurityStatus, SecurityStatusManager


class DynamicBadgeGenerator:
    """Generates dynamic badges based on live security status."""

    def __init__(
        self,
        status_manager: SecurityStatusManager | None = None,
        github_pages_base_url: str | None = None,
    ) -> None:
        """Initialize dynamic badge generator.

        Args:
            status_manager: Security status manager instance.
            github_pages_base_url: Base URL for GitHub Pages endpoints.
        """
        self.status_manager = status_manager or SecurityStatusManager()

        # Default GitHub Pages URL pattern
        if github_pages_base_url is None:
            config = get_badge_config()
            repo_parts = config.github_repo.split("/")
            if len(repo_parts) == 2:
                owner, repo = repo_parts
                self.github_pages_base_url = f"https://{owner}.github.io/{repo}"
            else:
                self.github_pages_base_url = "https://example.github.io/repo"
        else:
            self.github_pages_base_url = github_pages_base_url

    def generate_security_status_badge(self) -> dict[str, str]:
        """Generate security status badge URL and link.

        Returns:
            Dictionary with 'url' and 'link' keys for the badge.
        """
        try:
            # Get current security status
            status = self.status_manager.get_current_status()
            if status is None:
                # Generate fresh status if none exists
                status = self.status_manager.update_status()

            # Generate badge based on security grade and vulnerability count
            badge_data = self._create_badge_data_from_status(status)

            # Create shields.io URL
            config = get_badge_config()
            badge_url = self._create_shields_url(badge_data, config.shields_base_url)

            # Create link to live status page
            status_link = f"{self.github_pages_base_url}/security-status"

            return {
                "url": badge_url,
                "link": status_link,
                "alt_text": f"Security Status: {badge_data['message']}",
                "status": badge_data["status"],
            }

        except Exception as e:
            # Fallback badge for errors
            return self._create_fallback_badge(str(e))

    def generate_vulnerability_count_badge(self) -> dict[str, str]:
        """Generate vulnerability count badge URL and link.

        Returns:
            Dictionary with 'url' and 'link' keys for the badge.
        """
        try:
            # Get current security status
            status = self.status_manager.get_current_status()
            if status is None:
                status = self.status_manager.update_status()

            # Create vulnerability count badge
            total_vulns = status.vulnerability_summary.total
            critical_high = (
                status.vulnerability_summary.critical + status.vulnerability_summary.high
            )

            if critical_high > 0:
                color = "red"
                message = f"{total_vulns} ({critical_high} critical/high)"
            elif total_vulns > 0:
                color = "yellow"
                message = f"{total_vulns} vulnerabilities"
            else:
                color = "brightgreen"
                message = "0 vulnerabilities"

            # Create shields.io URL
            config = get_badge_config()
            label = "vulnerabilities"
            encoded_label = quote(label)
            encoded_message = quote(message)
            badge_url = f"{config.shields_base_url}/badge/{encoded_label}-{encoded_message}-{color}?style=flat"

            # Create link to live status page
            status_link = f"{self.github_pages_base_url}/security-status"

            return {
                "url": badge_url,
                "link": status_link,
                "alt_text": f"Vulnerabilities: {message}",
                "status": "critical"
                if critical_high > 0
                else ("warning" if total_vulns > 0 else "passing"),
            }

        except Exception as e:
            return self._create_fallback_badge(str(e), label="vulnerabilities")

    def generate_last_scan_badge(self) -> dict[str, str]:
        """Generate last scan date badge URL and link.

        Returns:
            Dictionary with 'url' and 'link' keys for the badge.
        """
        try:
            # Get current security status
            status = self.status_manager.get_current_status()
            if status is None:
                status = self.status_manager.update_status()

            # Calculate days since scan
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            days_since_scan = (now.date() - status.scan_date.date()).days

            # Determine color based on scan age
            if days_since_scan == 0:
                color = "brightgreen"
                message = "today"
            elif days_since_scan <= 7:
                color = "green"
                message = f"{days_since_scan} days ago"
            elif days_since_scan <= 30:
                color = "yellow"
                message = f"{days_since_scan} days ago"
            else:
                color = "red"
                message = f"{days_since_scan} days ago"

            # Create shields.io URL
            config = get_badge_config()
            label = "last scan"
            encoded_label = quote(label)
            encoded_message = quote(message)
            badge_url = f"{config.shields_base_url}/badge/{encoded_label}-{encoded_message}-{color}?style=flat"

            # Create link to live status page
            status_link = f"{self.github_pages_base_url}/security-status"

            return {
                "url": badge_url,
                "link": status_link,
                "alt_text": f"Last Scan: {message}",
                "status": "warning" if days_since_scan > 7 else "passing",
            }

        except Exception as e:
            return self._create_fallback_badge(str(e), label="last scan")

    def _create_badge_data_from_status(self, status: SecurityStatus) -> dict[str, str]:
        """Create badge data from security status.

        Args:
            status: SecurityStatus object.

        Returns:
            Dictionary with badge data.
        """
        grade = status.security_grade
        total_vulns = status.vulnerability_summary.total

        # Map security grade to color and status
        grade_colors = {
            "A": "brightgreen",
            "B": "green",
            "C": "yellow",
            "D": "orange",
            "F": "red",
        }

        color = grade_colors.get(grade, "lightgrey")

        if total_vulns == 0:
            message = f"Grade {grade} (0 vulnerabilities)"
            badge_status = "passing"
        else:
            message = f"Grade {grade} ({total_vulns} vulnerabilities)"
            badge_status = "failing" if grade in ["D", "F"] else "warning"

        return {
            "label": "security",
            "message": message,
            "color": color,
            "status": badge_status,
        }

    def _create_shields_url(self, badge_data: dict[str, str], base_url: str) -> str:
        """Create shields.io URL from badge data.

        Args:
            badge_data: Badge data dictionary.
            base_url: Shields.io base URL.

        Returns:
            Complete shields.io badge URL.
        """
        label = quote(badge_data["label"])
        message = quote(badge_data["message"])
        color = badge_data["color"]

        return f"{base_url}/badge/{label}-{message}-{color}?style=flat"

    def _create_fallback_badge(self, error_msg: str, label: str = "security") -> dict[str, str]:
        """Create fallback badge for errors.

        Args:
            error_msg: Error message.
            label: Badge label.

        Returns:
            Fallback badge dictionary.
        """
        config = get_badge_config()
        encoded_label = quote(label)
        encoded_message = quote("unknown")
        badge_url = f"{config.shields_base_url}/badge/{encoded_label}-{encoded_message}-lightgrey?style=flat"

        return {
            "url": badge_url,
            "link": f"{self.github_pages_base_url}/security-status",
            "alt_text": f"{label.title()}: Unknown (Error: {error_msg})",
            "status": "unknown",
        }


class ReadmeBadgeUpdater:
    """Updates README.md file with dynamic security badges."""

    def __init__(
        self,
        readme_path: Path | None = None,
        badge_generator: DynamicBadgeGenerator | None = None,
    ) -> None:
        """Initialize README badge updater.

        Args:
            readme_path: Path to README.md file.
            badge_generator: Dynamic badge generator instance.
        """
        self.readme_path = readme_path or Path("README.md")
        self.badge_generator = badge_generator or DynamicBadgeGenerator()

    def update_security_badges(self) -> dict[str, Any]:
        """Update security badges in README.md file.

        Returns:
            Dictionary with update results.
        """
        try:
            if not self.readme_path.exists():
                msg = f"README file not found: {self.readme_path}"
                raise FileNotFoundError(msg)

            # Read current README content
            with self.readme_path.open("r", encoding="utf-8") as f:
                content = f.read()

            # Generate new badge data
            security_badge = self.badge_generator.generate_security_status_badge()
            vulnerability_badge = self.badge_generator.generate_vulnerability_count_badge()
            last_scan_badge = self.badge_generator.generate_last_scan_badge()

            # Update badges in content
            updated_content = self._update_badge_content(
                content,
                {
                    "security_status": security_badge,
                    "vulnerability_count": vulnerability_badge,
                    "last_scan": last_scan_badge,
                },
            )

            # Write updated content back to file
            with self.readme_path.open("w", encoding="utf-8") as f:
                f.write(updated_content)

            return {
                "success": True,
                "badges_updated": ["security_status", "vulnerability_count", "last_scan"],
                "security_status": security_badge["status"],
                "vulnerability_count": vulnerability_badge["status"],
                "last_scan": last_scan_badge["status"],
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def _update_badge_content(self, content: str, badges: dict[str, dict[str, str]]) -> str:
        """Update badge content in README.

        Args:
            content: Current README content.
            badges: Dictionary of badge data.

        Returns:
            Updated README content.
        """
        updated_content = content

        # Define badge patterns and replacements
        badge_patterns = {
            "security_status": {
                "pattern": r"!\[Security Status\]\([^)]+\)",
                "replacement": f"![Security Status]({badges['security_status']['url']})",
            },
            "vulnerability_count": {
                "pattern": r"!\[Vulnerabilities\]\([^)]+\)",
                "replacement": f"![Vulnerabilities]({badges['vulnerability_count']['url']})",
            },
            "last_scan": {
                "pattern": r"!\[Last Scan\]\([^)]+\)",
                "replacement": f"![Last Scan]({badges['last_scan']['url']})",
            },
        }

        # Update each badge pattern
        for badge_name, pattern_data in badge_patterns.items():
            pattern = pattern_data["pattern"]
            replacement = pattern_data["replacement"]

            if re.search(pattern, updated_content):
                updated_content = re.sub(pattern, replacement, updated_content)
            else:
                # If badge doesn't exist, add it to badges section
                updated_content = self._add_badge_to_section(
                    updated_content, badge_name, badges[badge_name]
                )

        return updated_content

    def _add_badge_to_section(
        self, content: str, badge_name: str, badge_data: dict[str, str]
    ) -> str:
        """Add badge to badges section if it doesn't exist.

        Args:
            content: README content.
            badge_name: Name of the badge.
            badge_data: Badge data dictionary.

        Returns:
            Updated content with badge added.
        """
        # Look for badges section marker
        badges_marker = "<!-- BADGES -->"

        if badges_marker in content:
            # Find the badges section and add the badge
            badge_markdown = (
                f"[![{badge_data['alt_text']}]({badge_data['url']})]({badge_data['link']})"
            )

            # Insert after the badges marker
            marker_pos = content.find(badges_marker)
            if marker_pos != -1:
                # Find the end of the line
                line_end = content.find("\n", marker_pos)
                if line_end != -1:
                    insert_pos = line_end + 1
                    content = content[:insert_pos] + badge_markdown + "\n" + content[insert_pos:]

        return content


class BadgeAutomation:
    """Automates badge updates based on security status changes."""

    def __init__(
        self,
        readme_updater: ReadmeBadgeUpdater | None = None,
        status_manager: SecurityStatusManager | None = None,
    ) -> None:
        """Initialize badge automation.

        Args:
            readme_updater: README badge updater instance.
            status_manager: Security status manager instance.
        """
        self.readme_updater = readme_updater or ReadmeBadgeUpdater()
        self.status_manager = status_manager or SecurityStatusManager()

    def update_badges_if_changed(self) -> dict[str, Any]:
        """Update badges only if security status has changed.

        Returns:
            Dictionary with update results.
        """
        try:
            # Get current status
            self.status_manager.get_current_status()

            # Always update for now (in a real implementation, you'd compare with previous status)
            # This could be enhanced to track status changes and only update when needed
            result = self.readme_updater.update_security_badges()

            if result["success"]:
                result["reason"] = "Security status updated"

            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "reason": "Badge update failed",
            }

    def create_automation_script(self, script_path: Path | None = None) -> None:
        """Create automation script for badge updates.

        Args:
            script_path: Path to automation script.
        """
        if script_path is None:
            script_path = Path("scripts/update_badges.py")

        script_content = '''#!/usr/bin/env python3
"""Automated badge update script.

This script updates README badges with current security status.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from badges.dynamic_badges import BadgeAutomation


def main() -> None:
    """Main function to update badges."""
    try:
        automation = BadgeAutomation()
        result = automation.update_badges_if_changed()

        if result["success"]:
            print(f"✅ Badges updated successfully: {result.get('reason', 'Updated')}")
            print(f"Security Status: {result.get('security_status', 'unknown')}")
            print(f"Vulnerability Count: {result.get('vulnerability_count', 'unknown')}")
            print(f"Last Scan: {result.get('last_scan', 'unknown')}")
        else:
            print(f"❌ Badge update failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Script execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
'''

        # Ensure script directory exists
        script_path.parent.mkdir(parents=True, exist_ok=True)

        # Write script file
        with script_path.open("w", encoding="utf-8") as f:
            f.write(script_content)

        # Make script executable
        script_path.chmod(0o755)


def get_default_badge_generator() -> DynamicBadgeGenerator:
    """Get default dynamic badge generator instance.

    Returns:
        DynamicBadgeGenerator with default configuration.
    """
    return DynamicBadgeGenerator()


def get_default_readme_updater() -> ReadmeBadgeUpdater:
    """Get default README badge updater instance.

    Returns:
        ReadmeBadgeUpdater with default configuration.
    """
    return ReadmeBadgeUpdater()


def update_readme_badges(
    readme_path: Path | None = None,
    badge_generator: DynamicBadgeGenerator | None = None,
) -> dict[str, Any]:
    """Update README badges with optional custom parameters.

    Args:
        readme_path: Path to README.md file.
        badge_generator: Dynamic badge generator instance.

    Returns:
        Dictionary with update results.
    """
    updater = ReadmeBadgeUpdater(readme_path, badge_generator)
    return updater.update_security_badges()
