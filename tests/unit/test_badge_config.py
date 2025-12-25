"""Unit tests for badge configuration functionality."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from badges.config import (
    BADGE_CONFIG,
    Badge,
    BadgeConfig,
    BadgeConfigurationError,
    BadgeSection,
    get_badge_config,
)


class TestBadge:
    """Test Badge data model."""

    def test_badge_creation_with_defaults(self) -> None:
        """Test Badge can be created with required fields and defaults."""
        badge = Badge(
            name="test_badge",
            url="https://img.shields.io/badge/test-passing-green",
            alt_text="Test Badge",
        )

        assert badge.name == "test_badge"
        assert badge.url == "https://img.shields.io/badge/test-passing-green"
        assert badge.alt_text == "Test Badge"
        assert badge.link_url is None
        assert badge.status == "unknown"

    def test_badge_creation_with_all_fields(self) -> None:
        """Test Badge creation with all fields specified."""
        badge = Badge(
            name="quality_gate",
            url="https://img.shields.io/github/actions/workflow/status/user/repo/test.yml",
            alt_text="Quality Gate",
            link_url="https://github.com/user/repo/actions",
            status="passing",
        )

        assert badge.name == "quality_gate"
        assert badge.link_url == "https://github.com/user/repo/actions"
        assert badge.status == "passing"


class TestBadgeSection:
    """Test BadgeSection data model."""

    def test_badge_section_creation(self) -> None:
        """Test BadgeSection creation with badges."""
        badges = [
            Badge("test1", "url1", "alt1"),
            Badge("test2", "url2", "alt2"),
        ]

        section = BadgeSection(
            title="Project Badges",
            badges=badges,
            markdown="<!-- badges markdown -->",
        )

        assert section.title == "Project Badges"
        assert len(section.badges) == 2
        assert section.markdown == "<!-- badges markdown -->"


class TestBadgeConfig:
    """Test BadgeConfig data model and validation."""

    def test_badge_config_creation_with_defaults(self) -> None:
        """Test BadgeConfig creation with valid defaults."""
        config = BadgeConfig(
            github_repo="owner/repository",
            pypi_package="mypackage",
            shields_base_url="https://img.shields.io",
        )

        assert config.github_repo == "owner/repository"
        assert config.pypi_package == "mypackage"
        assert config.shields_base_url == "https://img.shields.io"
        assert config.max_retries == 10
        assert config.retry_delay == 5
        assert config.badge_section_marker == "<!-- BADGES -->"

    def test_badge_config_creation_with_custom_values(self) -> None:
        """Test BadgeConfig creation with custom values."""
        config = BadgeConfig(
            github_repo="user/repo",
            pypi_package="testpkg",
            shields_base_url="https://shields.io",
            max_retries=5,
            retry_delay=3,
            badge_section_marker="<!-- CUSTOM -->",
        )

        assert config.max_retries == 5
        assert config.retry_delay == 3
        assert config.badge_section_marker == "<!-- CUSTOM -->"

    def test_badge_config_validation_invalid_github_repo(self) -> None:
        """Test BadgeConfig validation with invalid GitHub repo format."""
        with pytest.raises(BadgeConfigurationError) as exc_info:
            BadgeConfig(
                github_repo="invalid-repo-format",
                pypi_package="mypackage",
                shields_base_url="https://img.shields.io",
            )

        assert "Invalid github_repo format" in str(exc_info.value)
        assert "Expected format: 'owner/repository'" in str(exc_info.value)

    def test_badge_config_validation_empty_github_repo(self) -> None:
        """Test BadgeConfig validation with empty GitHub repo."""
        with pytest.raises(BadgeConfigurationError) as exc_info:
            BadgeConfig(
                github_repo="",
                pypi_package="mypackage",
                shields_base_url="https://img.shields.io",
            )

        assert "Invalid github_repo format" in str(exc_info.value)

    def test_badge_config_validation_empty_pypi_package(self) -> None:
        """Test BadgeConfig validation with empty PyPI package."""
        with pytest.raises(BadgeConfigurationError) as exc_info:
            BadgeConfig(
                github_repo="owner/repo",
                pypi_package="",
                shields_base_url="https://img.shields.io",
            )

        assert "pypi_package cannot be empty" in str(exc_info.value)

    def test_badge_config_validation_invalid_shields_url(self) -> None:
        """Test BadgeConfig validation with invalid shields URL."""
        with pytest.raises(BadgeConfigurationError) as exc_info:
            BadgeConfig(
                github_repo="owner/repo",
                pypi_package="mypackage",
                shields_base_url="invalid-url",
            )

        assert "Invalid shields_base_url" in str(exc_info.value)
        assert "Must start with http:// or https://" in str(exc_info.value)

    def test_badge_config_validation_negative_max_retries(self) -> None:
        """Test BadgeConfig validation with negative max_retries."""
        with pytest.raises(BadgeConfigurationError) as exc_info:
            BadgeConfig(
                github_repo="owner/repo",
                pypi_package="mypackage",
                shields_base_url="https://img.shields.io",
                max_retries=-1,
            )

        assert "max_retries must be non-negative" in str(exc_info.value)

    def test_badge_config_validation_negative_retry_delay(self) -> None:
        """Test BadgeConfig validation with negative retry_delay."""
        with pytest.raises(BadgeConfigurationError) as exc_info:
            BadgeConfig(
                github_repo="owner/repo",
                pypi_package="mypackage",
                shields_base_url="https://img.shields.io",
                retry_delay=-1,
            )

        assert "retry_delay must be non-negative" in str(exc_info.value)


class TestGetBadgeConfig:
    """Test get_badge_config function."""

    def test_get_badge_config_with_defaults(self) -> None:
        """Test get_badge_config with default environment."""
        with patch.dict(os.environ, {}, clear=True):
            config = get_badge_config()

            assert config.github_repo == "stabbotco1/mypylogger"
            assert config.pypi_package == "mypylogger"
            assert config.shields_base_url == "https://img.shields.io"
            assert config.max_retries == 10
            assert config.retry_delay == 5
            assert config.badge_section_marker == "<!-- BADGES -->"

    def test_get_badge_config_with_env_vars(self) -> None:
        """Test get_badge_config with environment variables set."""
        env_vars = {
            "GITHUB_REPOSITORY": "testuser/testrepo",
            "PYPI_PACKAGE": "testpackage",
            "SHIELDS_BASE_URL": "https://custom.shields.io",
            "BADGE_MAX_RETRIES": "15",
            "BADGE_RETRY_DELAY": "7",
            "BADGE_SECTION_MARKER": "<!-- CUSTOM BADGES -->",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = get_badge_config()

            assert config.github_repo == "testuser/testrepo"
            assert config.pypi_package == "testpackage"
            assert config.shields_base_url == "https://custom.shields.io"
            assert config.max_retries == 15
            assert config.retry_delay == 7
            assert config.badge_section_marker == "<!-- CUSTOM BADGES -->"

    def test_get_badge_config_with_invalid_int_values(self) -> None:
        """Test get_badge_config with invalid integer environment variables."""
        env_vars = {
            "BADGE_MAX_RETRIES": "not_a_number",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(BadgeConfigurationError) as exc_info:
                get_badge_config()

            assert "Invalid configuration value" in str(exc_info.value)

    def test_get_badge_config_with_invalid_repo_format(self) -> None:
        """Test get_badge_config with invalid repository format from env."""
        env_vars = {
            "GITHUB_REPOSITORY": "invalid-format",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(BadgeConfigurationError) as exc_info:
                get_badge_config()

            assert "Invalid github_repo format" in str(exc_info.value)


class TestBadgeConfigConstants:
    """Test BADGE_CONFIG constants."""

    def test_badge_config_structure(self) -> None:
        """Test BADGE_CONFIG has expected structure."""
        assert isinstance(BADGE_CONFIG, dict)
        assert "github_repo" in BADGE_CONFIG
        assert "pypi_package" in BADGE_CONFIG
        assert "shields_base_url" in BADGE_CONFIG
        assert "badge_templates" in BADGE_CONFIG

    def test_badge_templates_structure(self) -> None:
        """Test badge_templates has all required badge types."""
        templates = BADGE_CONFIG["badge_templates"]

        expected_badges = [
            "quality_gate",
            "comprehensive_security",
            "code_style",
            "type_checked",
            "python_versions",
            "pypi_version",
            "downloads",
            "license",
        ]

        for badge_type in expected_badges:
            assert badge_type in templates, f"Missing badge template: {badge_type}"

    def test_badge_template_urls_format(self) -> None:
        """Test badge template URLs have correct format."""
        templates = BADGE_CONFIG["badge_templates"]

        # Dynamic badges should have badge format with status and color placeholders
        assert "badge/quality%20gate-{status}-{color}" in templates["quality_gate"]
        assert "badge/security-{status}-{color}" in templates["comprehensive_security"]

        # Static badges should have badge format
        assert "badge/code%20style-ruff" in templates["code_style"]
        assert "badge/type%20checked-mypy" in templates["type_checked"]

        # PyPI badges should have pypi format
        assert "pypi/pyversions/{package}" in templates["python_versions"]
        assert "pypi/v/{package}" in templates["pypi_version"]

        # License badge should have github format
        assert "github/license/{repo}" in templates["license"]

        # All badges should have style parameter
        for template_url in templates.values():
            assert "style=flat" in template_url, f"Missing style parameter in: {template_url}"
