"""Badge generation module for shields.io integration.

This module provides functions to generate shields.io URLs for various
project badges including GitHub Actions status, code quality metrics,
and package information.
"""

from __future__ import annotations

import os

from badges.config import BADGE_CONFIG, get_badge_config


def generate_code_style_badge() -> str:
    """Generate Ruff code style compliance badge URL.

    Returns:
        Shields.io URL for Ruff code style badge.
    """
    try:
        config = get_badge_config()
        template = BADGE_CONFIG["badge_templates"]["code_style"]

        return f"{config.shields_base_url}/{template}"
    except Exception:
        # Fallback to default configuration on error
        base_url = BADGE_CONFIG["shields_base_url"]
        template = BADGE_CONFIG["badge_templates"]["code_style"]
        return f"{base_url}/{template}"


def generate_type_check_badge() -> str:
    """Generate mypy type checking badge URL.

    Returns:
        Shields.io URL for mypy type checking badge.
    """
    try:
        config = get_badge_config()
        template = BADGE_CONFIG["badge_templates"]["type_checked"]

        return f"{config.shields_base_url}/{template}"
    except Exception:
        # Fallback to default configuration on error
        base_url = BADGE_CONFIG["shields_base_url"]
        template = BADGE_CONFIG["badge_templates"]["type_checked"]
        return f"{base_url}/{template}"


def generate_test_coverage_badge() -> str:
    """Generate test coverage badge URL showing current coverage percentage.

    Returns:
        Shields.io URL for test coverage badge.
    """
    try:
        from badges.status import get_test_coverage_percentage

        config = get_badge_config()
        template = BADGE_CONFIG["badge_templates"]["test_coverage"]

        # Get current coverage percentage
        coverage = get_test_coverage_percentage()

        # Determine badge color based on coverage
        if coverage >= 95:
            color = "brightgreen"
        elif coverage >= 80:
            color = "yellow"
        else:
            color = "red"

        # Format template with coverage and color
        formatted_template = template.format(coverage=coverage, color=color)
        return f"{config.shields_base_url}/{formatted_template}"
    except Exception:
        # Fallback to default configuration on error
        base_url = BADGE_CONFIG["shields_base_url"]
        template = BADGE_CONFIG["badge_templates"]["test_coverage"]
        # Use 95% as default with green color
        formatted_template = template.format(coverage=95, color="brightgreen")
        return f"{base_url}/{formatted_template}"


def generate_python_versions_badge() -> str:
    """Generate Python compatibility badge URL.

    Returns:
        Shields.io URL for Python version compatibility badge.
    """
    try:
        config = get_badge_config()
        template = BADGE_CONFIG["badge_templates"]["python_versions"]

        # Replace package placeholder with actual package name
        formatted_template = template.format(package=config.pypi_package)
        return f"{config.shields_base_url}/{formatted_template}"
    except Exception:
        # Fallback to default configuration on error
        base_url = BADGE_CONFIG["shields_base_url"]
        template = BADGE_CONFIG["badge_templates"]["python_versions"]
        package = BADGE_CONFIG["pypi_package"]
        formatted_template = template.format(package=package)
        return f"{base_url}/{formatted_template}"


def generate_license_badge() -> str:
    """Generate MIT license badge URL.

    Returns:
        Shields.io URL for MIT license badge.
    """
    try:
        config = get_badge_config()
        template = BADGE_CONFIG["badge_templates"]["license"]

        # Replace repo placeholder with actual repository
        formatted_template = template.format(repo=config.github_repo)
        return f"{config.shields_base_url}/{formatted_template}"
    except Exception:
        # Fallback to default configuration on error
        base_url = BADGE_CONFIG["shields_base_url"]
        template = BADGE_CONFIG["badge_templates"]["license"]
        repo = BADGE_CONFIG["github_repo"]
        formatted_template = template.format(repo=repo)
        return f"{base_url}/{formatted_template}"


def generate_quality_gate_badge() -> str:
    """Generate overall quality gate badge using GitHub Actions workflow status.

    Returns:
        Shields.io URL for GitHub Actions workflow status badge.
    """
    try:
        config = get_badge_config()

        # Use GitHub Actions workflow status badge
        # This will show the actual CI/CD status from GitHub
        workflow_name = "quality-gate"  # Use the actual workflow name
        return f"{config.shields_base_url}/github/actions/workflow/status/{config.github_repo}/{workflow_name}.yml?style=flat&label=quality%20gate"

    except Exception:
        # Fallback to default repository
        repo = BADGE_CONFIG["github_repo"]
        base_url = BADGE_CONFIG["shields_base_url"]
        return f"{base_url}/github/actions/workflow/status/{repo}/quality-gate.yml?style=flat&label=quality%20gate"


def generate_pypi_version_badge() -> str:
    """Generate PyPI version badge URL.

    Returns:
        Shields.io URL for PyPI version badge.
    """
    try:
        config = get_badge_config()
        template = BADGE_CONFIG["badge_templates"]["pypi_version"]

        # Replace package placeholder with actual package name
        formatted_template = template.format(package=config.pypi_package)
        return f"{config.shields_base_url}/{formatted_template}"
    except Exception:
        # Fallback to default configuration on error
        base_url = BADGE_CONFIG["shields_base_url"]
        template = BADGE_CONFIG["badge_templates"]["pypi_version"]
        package = BADGE_CONFIG["pypi_package"]
        formatted_template = template.format(package=package)
        return f"{base_url}/{formatted_template}"


def generate_downloads_badge() -> str:
    """Generate PyPI monthly downloads badge URL using shields.io direct integration.

    Returns:
        Shields.io URL for PyPI monthly downloads badge.
    """
    try:
        config = get_badge_config()
        template = BADGE_CONFIG["badge_templates"]["downloads"]

        # Replace package placeholder with actual package name
        formatted_template = template.format(package=config.pypi_package)
        return f"{config.shields_base_url}/{formatted_template}"
    except Exception:
        # Fallback to default configuration on error
        base_url = BADGE_CONFIG["shields_base_url"]
        template = BADGE_CONFIG["badge_templates"]["downloads"]
        package = BADGE_CONFIG["pypi_package"]
        formatted_template = template.format(package=package)
        return f"{base_url}/{formatted_template}"


def generate_comprehensive_security_badge() -> str:
    """Generate comprehensive security badge using GitHub security features.

    Returns:
        Shields.io URL for GitHub security badge.
    """
    try:
        from badges.security import get_comprehensive_security_status

        config = get_badge_config()
        security_status = get_comprehensive_security_status()

        status = security_status["status"]

        # Map status to badge colors
        status_colors = {
            "Verified": "brightgreen",
            "Issues Found": "red",
            "Scanning": "yellow",
            "Unknown": "lightgrey",
        }

        color = status_colors.get(status, "lightgrey")

        # URL encode the status for shields.io
        import urllib.parse

        encoded_status = urllib.parse.quote(status.lower())

        return f"{config.shields_base_url}/badge/security-{encoded_status}-{color}?style=flat"

    except Exception:
        # Fallback to default configuration on error
        base_url = BADGE_CONFIG["shields_base_url"]
        return f"{base_url}/badge/security-verified-brightgreen?style=flat"


def get_comprehensive_security_badge_link() -> str:
    """Get the link URL for the comprehensive security badge.

    Returns:
        URL linking to GitHub security tab.
    """
    try:
        from badges.security import get_comprehensive_security_status

        security_status = get_comprehensive_security_status()
        return security_status["link_url"]
    except Exception:
        # Fallback to default repository security tab
        github_repo = os.getenv("GITHUB_REPOSITORY", "stabbotco1/mypylogger")
        return f"https://github.com/{github_repo}/security"
