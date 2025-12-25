"""Badge system configuration and data models.

This module provides configuration settings, URL templates, and data
models for the badge generation system.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any


class BadgeConfigurationError(Exception):
    """Raised when badge configuration is invalid."""


@dataclass
class Badge:
    """Represents a single project badge."""

    name: str
    url: str
    alt_text: str
    link_url: str | None = None
    status: str = "unknown"  # "passing", "failing", "unknown"


@dataclass
class BadgeSection:
    """Represents the complete badge section for README."""

    title: str
    badges: list[Badge]
    markdown: str


@dataclass
class BadgeConfig:
    """Badge system configuration."""

    github_repo: str
    pypi_package: str
    shields_base_url: str
    max_retries: int = 10
    retry_delay: int = 5
    badge_section_marker: str = "<!-- BADGES -->"

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate badge configuration parameters.

        Raises:
            BadgeConfigurationError: If configuration is invalid.
        """
        if not self.github_repo or "/" not in self.github_repo:
            msg = (
                f"Invalid github_repo format: {self.github_repo}. "
                "Expected format: 'owner/repository'"
            )
            raise BadgeConfigurationError(msg)

        if not self.pypi_package:
            msg = "pypi_package cannot be empty"
            raise BadgeConfigurationError(msg)

        if not self.shields_base_url.startswith(("http://", "https://")):
            msg = (
                f"Invalid shields_base_url: {self.shields_base_url}. "
                "Must start with http:// or https://"
            )
            raise BadgeConfigurationError(msg)

        if self.max_retries < 0:
            msg = f"max_retries must be non-negative, got: {self.max_retries}"
            raise BadgeConfigurationError(msg)

        if self.retry_delay < 0:
            msg = f"retry_delay must be non-negative, got: {self.retry_delay}"
            raise BadgeConfigurationError(msg)


def get_badge_config() -> BadgeConfig:
    """Get badge configuration from environment variables or defaults.

    Returns:
        BadgeConfig: Validated badge configuration.

    Raises:
        BadgeConfigurationError: If configuration is invalid.
    """
    try:
        github_repo = os.getenv("GITHUB_REPOSITORY", "stabbotco1/mypylogger")
        pypi_package = os.getenv("PYPI_PACKAGE", "mypylogger")
        shields_base_url = os.getenv("SHIELDS_BASE_URL", "https://img.shields.io")

        max_retries = int(os.getenv("BADGE_MAX_RETRIES", "10"))
        retry_delay = int(os.getenv("BADGE_RETRY_DELAY", "5"))

        badge_section_marker = os.getenv("BADGE_SECTION_MARKER", "<!-- BADGES -->")

        return BadgeConfig(
            github_repo=github_repo,
            pypi_package=pypi_package,
            shields_base_url=shields_base_url,
            max_retries=max_retries,
            retry_delay=retry_delay,
            badge_section_marker=badge_section_marker,
        )
    except ValueError as e:
        msg = f"Invalid configuration value: {e}"
        raise BadgeConfigurationError(msg) from e
    except Exception as e:
        msg = f"Failed to load configuration: {e}"
        raise BadgeConfigurationError(msg) from e


# Badge template URLs for shields.io integration
BADGE_CONFIG: dict[str, Any] = {
    "github_repo": "stabbotco1/mypylogger",
    "pypi_package": "mypylogger",
    "shields_base_url": "https://img.shields.io",
    "badge_templates": {
        # Overall quality gate badge (aggregates all quality checks)
        "quality_gate": "badge/quality%20gate-{status}-{color}?style=flat",
        # Comprehensive security badge (all security tests combined)
        "comprehensive_security": "badge/security-{status}-{color}?style=flat",
        # Static code quality badges
        "code_style": "badge/code%20style-ruff-000000?style=flat",
        "type_checked": "badge/type%20checked-mypy-blue?style=flat",
        # Test coverage badge
        "test_coverage": "badge/coverage-{coverage}%25-{color}?style=flat",
        # Python version compatibility badge
        "python_versions": "pypi/pyversions/{package}?style=flat",
        # PyPI badges
        "pypi_version": "pypi/v/{package}?style=flat",
        # PyPI downloads badge (monthly)
        "downloads": "pypi/dm/{package}?style=flat",
        # License badge
        "license": "github/license/{repo}?style=flat",
    },
    "security_badge_links": {
        "codeql_results": "https://github.com/{repo}/security/code-scanning",
        "security_tab": "https://github.com/{repo}/security",
    },
}
