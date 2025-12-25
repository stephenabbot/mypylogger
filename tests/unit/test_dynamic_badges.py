"""Tests for dynamic README badge integration."""

from datetime import datetime, timezone
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch

from badges.dynamic_badges import (
    BadgeAutomation,
    DynamicBadgeGenerator,
    ReadmeBadgeUpdater,
    get_default_badge_generator,
    get_default_readme_updater,
    update_readme_badges,
)
from badges.live_status import SecurityStatus, VulnerabilitySummary


class TestDynamicBadgeGenerator:
    """Test DynamicBadgeGenerator class."""

    def test_init_default_config(self) -> None:
        """Test initialization with default configuration."""
        generator = DynamicBadgeGenerator()

        assert generator.status_manager is not None
        assert "github.io" in generator.github_pages_base_url

    def test_init_custom_config(self) -> None:
        """Test initialization with custom configuration."""
        status_manager = Mock()
        base_url = "https://custom.github.io/repo"

        generator = DynamicBadgeGenerator(status_manager, base_url)

        assert generator.status_manager == status_manager
        assert generator.github_pages_base_url == base_url

    def test_generate_security_status_badge_grade_a(self) -> None:
        """Test security status badge generation with grade A."""
        # Mock status manager
        mock_status_manager = Mock()
        mock_status = self._create_test_status("A", 0, 0, 0)
        mock_status_manager.get_current_status.return_value = mock_status

        generator = DynamicBadgeGenerator(mock_status_manager, "https://test.github.io/repo")
        result = generator.generate_security_status_badge()

        assert result["status"] == "passing"
        assert "Grade A" in result["alt_text"]
        assert "0 vulnerabilities" in result["alt_text"]
        assert "brightgreen" in result["url"]
        assert result["link"] == "https://test.github.io/repo/security-status"

    def test_generate_security_status_badge_grade_f(self) -> None:
        """Test security status badge generation with grade F."""
        # Mock status manager
        mock_status_manager = Mock()
        mock_status = self._create_test_status(
            "F", 0, 2, 0, 3, 0
        )  # 2 critical + 3 medium = 5 total
        mock_status_manager.get_current_status.return_value = mock_status

        generator = DynamicBadgeGenerator(mock_status_manager, "https://test.github.io/repo")
        result = generator.generate_security_status_badge()

        assert result["status"] == "failing"
        assert "Grade F" in result["alt_text"]
        assert "5 vulnerabilities" in result["alt_text"]
        assert "red" in result["url"]

    def test_generate_security_status_badge_no_current_status(self) -> None:
        """Test security status badge generation when no current status exists."""
        # Mock status manager
        mock_status_manager = Mock()
        mock_status = self._create_test_status("B", 0, 0, 1, 1, 0)  # 1 high + 1 medium = 2 total
        mock_status_manager.get_current_status.return_value = None
        mock_status_manager.update_status.return_value = mock_status

        generator = DynamicBadgeGenerator(mock_status_manager, "https://test.github.io/repo")
        result = generator.generate_security_status_badge()

        assert result["status"] == "warning"
        assert "Grade B" in result["alt_text"]
        mock_status_manager.update_status.assert_called_once()

    def test_generate_security_status_badge_error(self) -> None:
        """Test security status badge generation with error."""
        # Mock status manager to raise exception
        mock_status_manager = Mock()
        mock_status_manager.get_current_status.side_effect = RuntimeError("Status error")

        generator = DynamicBadgeGenerator(mock_status_manager, "https://test.github.io/repo")
        result = generator.generate_security_status_badge()

        assert result["status"] == "unknown"
        assert "Unknown" in result["alt_text"]
        assert "lightgrey" in result["url"]

    def test_generate_vulnerability_count_badge_no_vulnerabilities(self) -> None:
        """Test vulnerability count badge with no vulnerabilities."""
        # Mock status manager
        mock_status_manager = Mock()
        mock_status = self._create_test_status("A", 0, 0, 0)
        mock_status_manager.get_current_status.return_value = mock_status

        generator = DynamicBadgeGenerator(mock_status_manager, "https://test.github.io/repo")
        result = generator.generate_vulnerability_count_badge()

        assert result["status"] == "passing"
        assert "0 vulnerabilities" in result["alt_text"]
        assert "brightgreen" in result["url"]

    def test_generate_vulnerability_count_badge_critical_high(self) -> None:
        """Test vulnerability count badge with critical/high vulnerabilities."""
        # Mock status manager
        mock_status_manager = Mock()
        mock_status = self._create_test_status(
            "F", 0, 2, 1, 2, 0
        )  # 2 critical + 1 high + 2 medium = 5 total
        mock_status_manager.get_current_status.return_value = mock_status

        generator = DynamicBadgeGenerator(mock_status_manager, "https://test.github.io/repo")
        result = generator.generate_vulnerability_count_badge()

        assert result["status"] == "critical"
        assert "3 critical/high" in result["alt_text"]
        assert "red" in result["url"]

    def test_generate_vulnerability_count_badge_medium_low_only(self) -> None:
        """Test vulnerability count badge with only medium/low vulnerabilities."""
        # Mock status manager
        mock_status_manager = Mock()
        mock_status = self._create_test_status("B", 3, 0, 0, 2, 1)
        mock_status_manager.get_current_status.return_value = mock_status

        generator = DynamicBadgeGenerator(mock_status_manager, "https://test.github.io/repo")
        result = generator.generate_vulnerability_count_badge()

        assert result["status"] == "warning"
        assert "3 vulnerabilities" in result["alt_text"]
        assert "yellow" in result["url"]

    def test_generate_last_scan_badge_today(self) -> None:
        """Test last scan badge for today's scan."""
        # Mock status manager
        mock_status_manager = Mock()
        mock_status = self._create_test_status("A", 0, 0, 0)
        mock_status_manager.get_current_status.return_value = mock_status

        generator = DynamicBadgeGenerator(mock_status_manager, "https://test.github.io/repo")
        result = generator.generate_last_scan_badge()

        assert result["status"] == "passing"
        assert "today" in result["alt_text"]
        assert "brightgreen" in result["url"]

    def test_generate_last_scan_badge_old_scan(self) -> None:
        """Test last scan badge for old scan."""
        # Mock status manager with old scan date
        mock_status_manager = Mock()
        mock_status = self._create_test_status("A", 0, 0, 0)
        # Set scan date to 10 days ago
        from datetime import timedelta

        old_date = datetime.now(timezone.utc) - timedelta(days=10)
        mock_status.scan_date = old_date
        mock_status_manager.get_current_status.return_value = mock_status

        generator = DynamicBadgeGenerator(mock_status_manager, "https://test.github.io/repo")
        result = generator.generate_last_scan_badge()

        assert result["status"] == "warning"
        assert "10 days ago" in result["alt_text"]
        assert "yellow" in result["url"]

    def _create_test_status(
        self, grade: str, _total: int, critical: int, high: int, medium: int = 0, low: int = 0
    ) -> SecurityStatus:
        """Create test SecurityStatus object."""
        now = datetime.now(timezone.utc)
        # Ensure total matches sum of individual counts
        calculated_total = critical + high + medium + low
        summary = VulnerabilitySummary(
            total=calculated_total,
            critical=critical,
            high=high,
            medium=medium,
            low=low,
        )

        return SecurityStatus(
            last_updated=now,
            scan_date=now,
            vulnerability_summary=summary,
            security_grade=grade,
            days_since_last_vulnerability=0,
            remediation_status="current",
        )


class TestReadmeBadgeUpdater:
    """Test ReadmeBadgeUpdater class."""

    def test_init_default_paths(self) -> None:
        """Test initialization with default paths."""
        updater = ReadmeBadgeUpdater()

        assert updater.readme_path == Path("README.md")
        assert updater.badge_generator is not None

    def test_init_custom_paths(self) -> None:
        """Test initialization with custom paths."""
        readme_path = Path("/custom/README.md")
        badge_generator = Mock()

        updater = ReadmeBadgeUpdater(readme_path, badge_generator)

        assert updater.readme_path == readme_path
        assert updater.badge_generator == badge_generator

    def test_update_security_badges_success(self) -> None:
        """Test successful security badge update."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            readme_path = temp_path / "README.md"

            # Create test README content
            readme_content = """# Test Project

![Security Status](https://img.shields.io/badge/security-old-red)
![Vulnerabilities](https://img.shields.io/badge/vulnerabilities-old-red)
![Last Scan](https://img.shields.io/badge/last%20scan-old-red)

Some content here.
"""
            with readme_path.open("w") as f:
                f.write(readme_content)

            # Mock badge generator
            mock_generator = Mock()
            mock_generator.generate_security_status_badge.return_value = {
                "url": "https://img.shields.io/badge/security-Grade%20A-brightgreen",
                "link": "https://test.github.io/repo/security-status",
                "alt_text": "Security Status: Grade A",
                "status": "passing",
            }
            mock_generator.generate_vulnerability_count_badge.return_value = {
                "url": "https://img.shields.io/badge/vulnerabilities-0-brightgreen",
                "link": "https://test.github.io/repo/security-status",
                "alt_text": "Vulnerabilities: 0",
                "status": "passing",
            }
            mock_generator.generate_last_scan_badge.return_value = {
                "url": "https://img.shields.io/badge/last%20scan-today-brightgreen",
                "link": "https://test.github.io/repo/security-status",
                "alt_text": "Last Scan: today",
                "status": "passing",
            }

            updater = ReadmeBadgeUpdater(readme_path, mock_generator)
            result = updater.update_security_badges()

            assert result["success"] is True
            assert "security_status" in result["badges_updated"]
            assert result["security_status"] == "passing"

            # Verify README was updated
            with readme_path.open("r") as f:
                updated_content = f.read()
            assert "Grade%20A" in updated_content
            assert "0-brightgreen" in updated_content

    def test_update_security_badges_file_not_found(self) -> None:
        """Test security badge update when README file doesn't exist."""
        readme_path = Path("/nonexistent/README.md")
        mock_generator = Mock()

        updater = ReadmeBadgeUpdater(readme_path, mock_generator)
        result = updater.update_security_badges()

        assert result["success"] is False
        assert "not found" in result["error"]

    def test_add_badge_to_section_with_marker(self) -> None:
        """Test adding badge to section with badges marker."""
        updater = ReadmeBadgeUpdater()

        content = """# Test Project

<!-- BADGES -->

Some content here.
"""

        badge_data = {
            "url": "https://img.shields.io/badge/test-badge-green",
            "link": "https://example.com",
            "alt_text": "Test Badge",
        }

        result = updater._add_badge_to_section(content, "test", badge_data)

        assert "[![Test Badge]" in result
        assert "https://img.shields.io/badge/test-badge-green" in result
        assert "https://example.com" in result

    def test_add_badge_to_section_no_marker(self) -> None:
        """Test adding badge to section without badges marker."""
        updater = ReadmeBadgeUpdater()

        content = """# Test Project

Some content here.
"""

        badge_data = {
            "url": "https://img.shields.io/badge/test-badge-green",
            "link": "https://example.com",
            "alt_text": "Test Badge",
        }

        result = updater._add_badge_to_section(content, "test", badge_data)

        # Should return unchanged content when no marker found
        assert result == content


class TestBadgeAutomation:
    """Test BadgeAutomation class."""

    def test_init_default_components(self) -> None:
        """Test initialization with default components."""
        automation = BadgeAutomation()

        assert automation.readme_updater is not None
        assert automation.status_manager is not None

    def test_init_custom_components(self) -> None:
        """Test initialization with custom components."""
        readme_updater = Mock()
        status_manager = Mock()

        automation = BadgeAutomation(readme_updater, status_manager)

        assert automation.readme_updater == readme_updater
        assert automation.status_manager == status_manager

    def test_update_badges_if_changed_success(self) -> None:
        """Test successful badge update."""
        # Mock components
        mock_readme_updater = Mock()
        mock_status_manager = Mock()

        mock_readme_updater.update_security_badges.return_value = {
            "success": True,
            "badges_updated": ["security_status"],
            "security_status": "passing",
        }
        mock_status_manager.get_current_status.return_value = Mock()

        automation = BadgeAutomation(mock_readme_updater, mock_status_manager)
        result = automation.update_badges_if_changed()

        assert result["success"] is True
        assert result["reason"] == "Security status updated"
        assert result["security_status"] == "passing"

    def test_update_badges_if_changed_failure(self) -> None:
        """Test badge update failure."""
        # Mock components
        mock_readme_updater = Mock()
        mock_status_manager = Mock()

        mock_readme_updater.update_security_badges.return_value = {
            "success": False,
            "error": "Update failed",
        }
        mock_status_manager.get_current_status.return_value = Mock()

        automation = BadgeAutomation(mock_readme_updater, mock_status_manager)
        result = automation.update_badges_if_changed()

        assert result["success"] is False
        assert "Update failed" in result["error"]

    def test_update_badges_if_changed_exception(self) -> None:
        """Test badge update with exception."""
        # Mock components to raise exception
        mock_readme_updater = Mock()
        mock_status_manager = Mock()

        mock_status_manager.get_current_status.side_effect = RuntimeError("Status error")

        automation = BadgeAutomation(mock_readme_updater, mock_status_manager)
        result = automation.update_badges_if_changed()

        assert result["success"] is False
        assert "Status error" in result["error"]
        assert result["reason"] == "Badge update failed"

    def test_create_automation_script(self) -> None:
        """Test automation script creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            script_path = temp_path / "update_badges.py"

            automation = BadgeAutomation()
            automation.create_automation_script(script_path)

            assert script_path.exists()

            # Verify script content
            with script_path.open("r") as f:
                content = f.read()
            assert "#!/usr/bin/env python3" in content
            assert "BadgeAutomation" in content
            assert "update_badges_if_changed" in content

            # Verify script is executable
            assert script_path.stat().st_mode & 0o111  # Check execute permissions


class TestModuleFunctions:
    """Test module-level functions."""

    def test_get_default_badge_generator(self) -> None:
        """Test getting default badge generator."""
        generator = get_default_badge_generator()

        assert isinstance(generator, DynamicBadgeGenerator)

    def test_get_default_readme_updater(self) -> None:
        """Test getting default README updater."""
        updater = get_default_readme_updater()

        assert isinstance(updater, ReadmeBadgeUpdater)
        assert updater.readme_path == Path("README.md")

    @patch("badges.dynamic_badges.ReadmeBadgeUpdater")
    def test_update_readme_badges(self, mock_updater_class: Mock) -> None:
        """Test update_readme_badges function."""
        mock_updater = Mock()
        mock_result = {"success": True}
        mock_updater.update_security_badges.return_value = mock_result
        mock_updater_class.return_value = mock_updater

        readme_path = Path("/custom/README.md")
        badge_generator = Mock()

        result = update_readme_badges(readme_path, badge_generator)

        mock_updater_class.assert_called_once_with(readme_path, badge_generator)
        mock_updater.update_security_badges.assert_called_once()
        assert result == mock_result
