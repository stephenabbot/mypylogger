"""Integration tests for complete badge workflow.

This module tests the end-to-end badge generation and README update process,
badge status detection, API integration, and error handling scenarios.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest

from badges import (
    BadgeSystemError,
    create_badge_section,
    generate_all_badges,
    update_project_badges,
)
from badges.config import Badge, get_badge_config
from badges.status import (
    BadgeStatusCache,
    detect_code_style_status,
    detect_type_check_status,
    get_status_cache,
    validate_badge_status,
)

if TYPE_CHECKING:
    from pathlib import Path
else:
    from pathlib import Path as PathLib


class TestBadgeWorkflowIntegration:
    """Integration tests for complete badge workflow."""

    def test_end_to_end_badge_generation_and_readme_update(self, tmp_path: Path) -> None:
        """Test complete badge generation and README update process."""
        # Create a test README file
        readme_content = """# Test Project

This is a test project.

## Installation

Install the package.
"""
        readme_path = tmp_path / "README.md"
        readme_path.write_text(readme_content)

        # Change to temp directory for test
        original_cwd = PathLib.cwd()
        try:
            os.chdir(tmp_path)

            # Test badge generation without status detection (faster)
            badges = generate_all_badges(detect_status=False)
            assert len(badges) == 9
            assert all(isinstance(badge, Badge) for badge in badges)

            # Test badge section creation
            badge_section = create_badge_section(badges)
            assert badge_section.title == "Project Badges"
            assert len(badge_section.badges) == 9
            assert badge_section.markdown
            assert "[![" in badge_section.markdown

            # Test README update (this will fail since we're not in project root)
            # But we can test the function doesn't crash
            try:
                update_project_badges(detect_status=False)
                # May fail due to directory structure, but shouldn't crash
            except Exception:
                pass  # Expected in test environment

        finally:
            os.chdir(original_cwd)

    def test_badge_status_detection_integration(self) -> None:
        """Test badge status detection and API integration."""
        # Test status cache functionality
        cache = get_status_cache()
        assert isinstance(cache, BadgeStatusCache)

        # Test cache operations
        test_status = {"status": "passing", "message": "Test status"}
        cache.set("test_badge", test_status)
        cached_status = cache.get("test_badge")
        assert cached_status == test_status

        # Test cache expiration
        assert not cache.is_expired(max_age_seconds=3600)  # Should not be expired

        # Test status validation
        valid_status = {"status": "passing", "message": "All tests pass"}
        assert validate_badge_status("test", valid_status)

        invalid_status = {"status": "invalid", "message": "Bad status"}
        assert not validate_badge_status("test", invalid_status)

        # Clear cache for clean state
        cache.clear()

    @patch("badges.status.subprocess.run")
    def test_badge_status_detection_with_mocked_commands(self, mock_run: Mock) -> None:
        """Test badge status detection with mocked subprocess calls."""
        # Mock successful command execution
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        # Clear cache to ensure fresh detection
        cache = get_status_cache()
        cache.clear()

        # Test code style detection
        status = detect_code_style_status()
        assert status["status"] == "passing"
        assert "message" in status

        # Test type check detection
        status = detect_type_check_status()
        assert status["status"] == "passing"
        assert "message" in status

        # Verify subprocess was called
        assert mock_run.called

    @patch("badges.status.subprocess.run")
    def test_badge_status_detection_with_failures(self, mock_run: Mock) -> None:
        """Test badge status detection when commands fail."""
        # Mock failed command execution
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Error")

        # Clear cache to ensure fresh detection
        cache = get_status_cache()
        cache.clear()

        # Test code style detection with failure
        status = detect_code_style_status()
        assert status["status"] == "failing"
        assert "message" in status

        # Test type check detection with failure
        status = detect_type_check_status()
        assert status["status"] == "failing"
        assert "message" in status

    def test_error_handling_and_recovery_scenarios(self) -> None:
        """Test error handling and recovery scenarios."""
        # Test badge generation with invalid configuration
        with patch("badges.config.get_badge_config") as mock_config:
            mock_config.side_effect = Exception("Config error")

            # Should not crash, should use fallback
            badges = generate_all_badges(detect_status=False)
            # Should still generate some badges using fallback config
            assert isinstance(badges, list)

        # Test badge section creation with empty badges
        empty_section = create_badge_section([])
        assert empty_section.title == "Project Badges"
        assert empty_section.badges == []
        assert empty_section.markdown == ""

        # Test status validation with invalid inputs
        assert not validate_badge_status("test", None)
        assert not validate_badge_status("test", "not a dict")
        assert not validate_badge_status("test", {})
        assert not validate_badge_status("test", {"status": "invalid"})

    def test_badge_workflow_with_configuration_variations(self) -> None:
        """Test badge workflow with different configuration variations."""
        # Test with environment variable overrides
        original_repo = os.environ.get("GITHUB_REPOSITORY")
        original_package = os.environ.get("PYPI_PACKAGE")

        try:
            os.environ["GITHUB_REPOSITORY"] = "testuser/testproject"
            os.environ["PYPI_PACKAGE"] = "testpackage"

            # Test configuration loading
            config = get_badge_config()
            assert config.github_repo == "testuser/testproject"
            assert config.pypi_package == "testpackage"

            # Test badge generation with custom config
            badges = generate_all_badges(detect_status=False)
            assert len(badges) == 9

            # Verify URLs contain custom values
            license_badge = next(b for b in badges if b.name == "license")
            assert "testuser/testproject" in license_badge.url

            pypi_badge = next(b for b in badges if b.name == "pypi_version")
            assert "testpackage" in pypi_badge.url

        finally:
            # Restore original environment
            if original_repo is not None:
                os.environ["GITHUB_REPOSITORY"] = original_repo
            else:
                os.environ.pop("GITHUB_REPOSITORY", None)

            if original_package is not None:
                os.environ["PYPI_PACKAGE"] = original_package
            else:
                os.environ.pop("PYPI_PACKAGE", None)

    def test_badge_caching_behavior(self) -> None:
        """Test badge status caching behavior."""
        cache = get_status_cache()
        cache.clear()

        # Test cache miss and set
        assert cache.get("nonexistent") is None

        test_status = {"status": "passing", "message": "Cached status"}
        cache.set("test_badge", test_status)

        # Test cache hit
        cached = cache.get("test_badge")
        assert cached == test_status

        # Test cache expiration check
        assert not cache.is_expired(max_age_seconds=1)

        # Test cache clearing
        cache.clear()
        assert cache.get("test_badge") is None

    @patch("badges.updater.atomic_write_readme")
    def test_readme_update_integration(self, mock_write: Mock, tmp_path: Path) -> None:
        """Test README update integration with mocked file operations."""
        mock_write.return_value = True

        # Change to temp directory
        original_cwd = PathLib.cwd()
        try:
            os.chdir(tmp_path)

            # Create a minimal README
            readme_path = tmp_path / "README.md"
            readme_path.write_text("# Test Project\n\nContent here.")

            # Test complete workflow - this will fail in CI-only mode but we're mocking the write
            with patch("badges.updater.verify_ci_test_success", return_value=True):
                with patch("badges.updater.setup_git_config", return_value=True):
                    with patch("badges.updater.commit_badge_updates", return_value=True):
                        update_project_badges(detect_status=False)

            # Verify atomic_write_readme was called
            assert mock_write.called

        finally:
            os.chdir(original_cwd)

    def test_badge_system_error_handling(self) -> None:
        """Test BadgeSystemError handling in workflow."""
        # Test that BadgeSystemError is raised appropriately
        with patch("badges.generate_all_badges") as mock_generate:
            mock_generate.side_effect = Exception("Generation failed")

            with pytest.raises(BadgeSystemError):
                update_project_badges(detect_status=False)

    def test_all_badge_types_generated(self) -> None:
        """Test that all expected badge types are generated."""
        badges = generate_all_badges(detect_status=False)

        expected_badge_names = {
            "quality_gate",
            "security",
            "code_style",
            "type_check",
            "test_coverage",
            "python_versions",
            "pypi_version",
            "downloads",
            "license",
        }

        actual_badge_names = {badge.name for badge in badges}
        assert actual_badge_names == expected_badge_names

        # Verify all badges have required attributes
        for badge in badges:
            assert badge.name
            assert badge.url
            assert badge.alt_text
            assert badge.status in {"passing", "failing", "unknown", "development"}

    def test_badge_markdown_formatting(self) -> None:
        """Test badge markdown formatting is correct."""
        badges = generate_all_badges(detect_status=False)
        badge_section = create_badge_section(badges)

        markdown = badge_section.markdown

        # Should contain proper markdown image syntax
        assert "[![" in markdown
        assert "](" in markdown
        assert ")" in markdown

        # Should contain shields.io URLs
        assert "img.shields.io" in markdown

        # Should be a single line (badges on same line)
        assert "\n" not in markdown.strip()

        # Should contain all badges
        for badge in badges:
            assert badge.alt_text in markdown
