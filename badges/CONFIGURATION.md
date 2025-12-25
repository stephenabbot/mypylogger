# Badge System Configuration Guide

This guide covers all configuration options and customization possibilities for the mypylogger badge system.

## Configuration Overview

The badge system uses environment variables for configuration, providing flexibility for different deployment environments while maintaining sensible defaults.

## Environment Variables

### Core Configuration

#### `GITHUB_REPOSITORY`
- **Description**: GitHub repository in `owner/repository` format
- **Default**: `username/mypylogger`
- **Example**: `export GITHUB_REPOSITORY="myorg/myproject"`
- **Used for**: GitHub Actions workflow badges, license badge

#### `PYPI_PACKAGE`
- **Description**: PyPI package name
- **Default**: `mypylogger`
- **Example**: `export PYPI_PACKAGE="myproject"`
- **Used for**: PyPI version badge, Python versions badge

#### `SHIELDS_BASE_URL`
- **Description**: Base URL for shields.io service
- **Default**: `https://img.shields.io`
- **Example**: `export SHIELDS_BASE_URL="https://img.shields.io"`
- **Used for**: All badge URL generation

### README Integration

#### `BADGE_SECTION_MARKER`
- **Description**: HTML comment marker in README.md where badges should be inserted
- **Default**: `<!-- BADGES -->`
- **Example**: `export BADGE_SECTION_MARKER="<!-- PROJECT_BADGES -->"`
- **Usage**: Place this marker in your README.md where you want badges to appear

### Atomic Write Configuration

#### `BADGE_MAX_RETRIES`
- **Description**: Maximum number of retry attempts for atomic README writes
- **Default**: `10`
- **Example**: `export BADGE_MAX_RETRIES="15"`
- **Range**: 0-100 (0 disables retries)

#### `BADGE_RETRY_DELAY`
- **Description**: Delay in seconds between retry attempts
- **Default**: `5`
- **Example**: `export BADGE_RETRY_DELAY="3"`
- **Range**: 0-60 seconds

## Configuration Methods

### Method 1: Environment Variables

```bash
# Set environment variables in shell
export GITHUB_REPOSITORY="myorg/myproject"
export PYPI_PACKAGE="myproject"
export BADGE_SECTION_MARKER="<!-- PROJECT_BADGES -->"

# Run badge update
python -m badges
```

### Method 2: .env File

Create a `.env` file in your project root:

```bash
# .env file
GITHUB_REPOSITORY=myorg/myproject
PYPI_PACKAGE=myproject
SHIELDS_BASE_URL=https://img.shields.io
BADGE_SECTION_MARKER=<!-- PROJECT_BADGES -->
BADGE_MAX_RETRIES=15
BADGE_RETRY_DELAY=3
```

Load the .env file before running badges:

```python
#!/usr/bin/env python3
"""Load .env file and update badges."""

import os
from pathlib import Path

def load_env_file(env_path=".env"):
    """Load environment variables from .env file."""
    env_file = Path(env_path)
    
    if not env_file.exists():
        print(f"Environment file {env_path} not found")
        return
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

def main():
    """Load environment and update badges."""
    load_env_file()
    
    from badges import update_project_badges
    success = update_project_badges()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
```

### Method 3: CI/CD Environment

Configure in GitHub Actions:

```yaml
# .github/workflows/badges.yml
name: Update Badges

on:
  push:
    branches: [main]

jobs:
  update-badges:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Update badges
        run: python -m badges
        env:
          GITHUB_REPOSITORY: ${{ github.repository }}
          PYPI_PACKAGE: myproject
          BADGE_MAX_RETRIES: 15
```

### Method 4: Python Configuration

```python
#!/usr/bin/env python3
"""Programmatic badge configuration."""

import os
from badges import update_project_badges

def configure_badges():
    """Set badge configuration programmatically."""
    config = {
        "GITHUB_REPOSITORY": "myorg/myproject",
        "PYPI_PACKAGE": "myproject",
        "SHIELDS_BASE_URL": "https://img.shields.io",
        "BADGE_SECTION_MARKER": "<!-- PROJECT_BADGES -->",
        "BADGE_MAX_RETRIES": "15",
        "BADGE_RETRY_DELAY": "3",
    }
    
    for key, value in config.items():
        os.environ[key] = value

def main():
    """Configure and update badges."""
    configure_badges()
    
    success = update_project_badges()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
```

## Configuration Validation

### Validation Script

```python
#!/usr/bin/env python3
"""Badge configuration validation script."""

import os
import sys
from badges.config import get_badge_config, BadgeConfigurationError

def validate_github_repository(repo):
    """Validate GitHub repository format."""
    if not repo or "/" not in repo:
        return False, "Must be in 'owner/repository' format"
    
    parts = repo.split("/")
    if len(parts) != 2:
        return False, "Must contain exactly one slash"
    
    owner, repository = parts
    if not owner or not repository:
        return False, "Owner and repository cannot be empty"
    
    return True, "Valid"

def validate_pypi_package(package):
    """Validate PyPI package name."""
    if not package:
        return False, "Package name cannot be empty"
    
    # Basic validation (PyPI has more complex rules)
    if not package.replace("-", "").replace("_", "").replace(".", "").isalnum():
        return False, "Package name contains invalid characters"
    
    return True, "Valid"

def validate_shields_url(url):
    """Validate shields.io URL."""
    if not url:
        return False, "URL cannot be empty"
    
    if not url.startswith(("http://", "https://")):
        return False, "Must start with http:// or https://"
    
    return True, "Valid"

def validate_retry_settings(max_retries, retry_delay):
    """Validate retry settings."""
    try:
        max_retries = int(max_retries)
        retry_delay = int(retry_delay)
    except ValueError:
        return False, "Must be integers"
    
    if max_retries < 0:
        return False, "Max retries cannot be negative"
    
    if retry_delay < 0:
        return False, "Retry delay cannot be negative"
    
    if max_retries > 100:
        return False, "Max retries should not exceed 100"
    
    if retry_delay > 60:
        return False, "Retry delay should not exceed 60 seconds"
    
    return True, "Valid"

def run_validation():
    """Run comprehensive configuration validation."""
    print("=== Badge Configuration Validation ===\n")
    
    try:
        config = get_badge_config()
        
        # Validate GitHub repository
        valid, message = validate_github_repository(config.github_repo)
        status = "✓" if valid else "✗"
        print(f"{status} GitHub Repository: {config.github_repo} - {message}")
        
        # Validate PyPI package
        valid, message = validate_pypi_package(config.pypi_package)
        status = "✓" if valid else "✗"
        print(f"{status} PyPI Package: {config.pypi_package} - {message}")
        
        # Validate shields URL
        valid, message = validate_shields_url(config.shields_base_url)
        status = "✓" if valid else "✗"
        print(f"{status} Shields URL: {config.shields_base_url} - {message}")
        
        # Validate retry settings
        valid, message = validate_retry_settings(config.max_retries, config.retry_delay)
        status = "✓" if valid else "✗"
        print(f"{status} Retry Settings: {config.max_retries} retries, {config.retry_delay}s delay - {message}")
        
        # Validate badge section marker
        marker_valid = bool(config.badge_section_marker.strip())
        status = "✓" if marker_valid else "✗"
        message = "Valid" if marker_valid else "Cannot be empty"
        print(f"{status} Badge Section Marker: {config.badge_section_marker} - {message}")
        
        print("\n✓ Configuration validation completed successfully")
        return True
        
    except BadgeConfigurationError as e:
        print(f"✗ Configuration Error: {e}")
        return False

def main():
    """Run configuration validation."""
    if run_validation():
        return 0
    else:
        return 1

if __name__ == "__main__":
    exit(main())
```

## README Integration Setup

### Basic Setup

1. Add the badge section marker to your README.md:

```markdown
# Your Project Name

<!-- BADGES -->

## Description
Your project description here...
```

2. Run the badge system:

```bash
python -m badges
```

3. The README.md will be updated with badges:

```markdown
# Your Project Name

[![Quality Gate](https://img.shields.io/github/actions/workflow/status/owner/repo/quality-gate.yml?branch=main&style=flat)](https://github.com/owner/repo/actions) [![Security Scan](https://img.shields.io/github/actions/workflow/status/owner/repo/security-scan.yml?branch=main&style=flat)](https://github.com/owner/repo/actions) [![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000?style=flat)](https://github.com/astral-sh/ruff) [![Type Checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue?style=flat)](http://mypy-lang.org/) [![Python Versions](https://img.shields.io/pypi/pyversions/package?style=flat)](https://pypi.org/project/package/) [![PyPI Version](https://img.shields.io/pypi/v/package?style=flat)](https://pypi.org/project/package/) [![Downloads: Development](https://img.shields.io/badge/downloads-development-yellow?style=flat)](https://pypi.org/project/package/) [![License: MIT](https://img.shields.io/github/license/owner/repo?style=flat)](https://github.com/owner/repo/blob/main/LICENSE)

## Description
Your project description here...
```

### Custom Marker Setup

Use a custom badge section marker:

```bash
export BADGE_SECTION_MARKER="<!-- PROJECT_STATUS -->"
```

Add the custom marker to README.md:

```markdown
# Your Project Name

## Status

<!-- PROJECT_STATUS -->

## Description
Your project description here...
```

### Multiple Badge Sections

You can have multiple badge sections with different markers:

```python
#!/usr/bin/env python3
"""Multiple badge sections example."""

import os
from badges import generate_all_badges, create_badge_section
from badges.updater import update_readme_with_badges

def update_multiple_badge_sections():
    """Update multiple badge sections in README."""
    # Generate badges
    badges = generate_all_badges(detect_status=True)
    badge_section = create_badge_section(badges)
    
    # Update main badge section
    os.environ["BADGE_SECTION_MARKER"] = "<!-- BADGES -->"
    update_readme_with_badges([badge_section.markdown])
    
    # Update status section with subset of badges
    status_badges = [b for b in badges if b.name in ["quality_gate", "security_scan"]]
    status_section = create_badge_section(status_badges)
    
    os.environ["BADGE_SECTION_MARKER"] = "<!-- STATUS -->"
    update_readme_with_badges([status_section.markdown])

if __name__ == "__main__":
    update_multiple_badge_sections()
```

## Advanced Configuration

### Custom Badge Templates

While the badge system uses predefined templates, you can create custom badge generation:

```python
#!/usr/bin/env python3
"""Custom badge generation example."""

from badges.config import get_badge_config, Badge

def generate_custom_badge(label, message, color="blue"):
    """Generate custom badge URL."""
    config = get_badge_config()
    
    # URL encode the label and message
    import urllib.parse
    label_encoded = urllib.parse.quote(label)
    message_encoded = urllib.parse.quote(message)
    
    url = f"{config.shields_base_url}/badge/{label_encoded}-{message_encoded}-{color}?style=flat"
    
    return Badge(
        name=f"custom_{label.lower().replace(' ', '_')}",
        url=url,
        alt_text=f"{label}: {message}",
        link_url=url,
        status="custom"
    )

def main():
    """Generate custom badges."""
    custom_badges = [
        generate_custom_badge("Build", "Passing", "green"),
        generate_custom_badge("Coverage", "95%", "brightgreen"),
        generate_custom_badge("Dependencies", "Up to date", "blue"),
    ]
    
    for badge in custom_badges:
        print(f"{badge.name}: {badge.url}")

if __name__ == "__main__":
    main()
```

### Configuration Profiles

Create configuration profiles for different environments:

```python
#!/usr/bin/env python3
"""Configuration profiles example."""

import os

PROFILES = {
    "development": {
        "GITHUB_REPOSITORY": "dev-org/project-dev",
        "PYPI_PACKAGE": "project-dev",
        "BADGE_SECTION_MARKER": "<!-- DEV_BADGES -->",
        "BADGE_MAX_RETRIES": "5",
    },
    "staging": {
        "GITHUB_REPOSITORY": "staging-org/project-staging",
        "PYPI_PACKAGE": "project-staging",
        "BADGE_SECTION_MARKER": "<!-- STAGING_BADGES -->",
        "BADGE_MAX_RETRIES": "10",
    },
    "production": {
        "GITHUB_REPOSITORY": "prod-org/project",
        "PYPI_PACKAGE": "project",
        "BADGE_SECTION_MARKER": "<!-- BADGES -->",
        "BADGE_MAX_RETRIES": "15",
    },
}

def load_profile(profile_name):
    """Load configuration profile."""
    if profile_name not in PROFILES:
        raise ValueError(f"Unknown profile: {profile_name}")
    
    profile = PROFILES[profile_name]
    
    for key, value in profile.items():
        os.environ[key] = value
    
    print(f"Loaded profile: {profile_name}")

def main():
    """Load profile and update badges."""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python config_profiles.py <profile>")
        print(f"Available profiles: {', '.join(PROFILES.keys())}")
        return 1
    
    profile_name = sys.argv[1]
    
    try:
        load_profile(profile_name)
        
        from badges import update_project_badges
        success = update_project_badges()
        
        return 0 if success else 1
        
    except ValueError as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
```

## Troubleshooting Configuration

### Common Configuration Issues

#### Issue: "Invalid github_repo format"
```bash
# Wrong
export GITHUB_REPOSITORY="myrepo"

# Correct
export GITHUB_REPOSITORY="myorg/myrepo"
```

#### Issue: "pypi_package cannot be empty"
```bash
# Wrong
export PYPI_PACKAGE=""

# Correct
export PYPI_PACKAGE="mypackage"
```

#### Issue: "Invalid shields_base_url"
```bash
# Wrong
export SHIELDS_BASE_URL="img.shields.io"

# Correct
export SHIELDS_BASE_URL="https://img.shields.io"
```

#### Issue: Badge section not found
```bash
# Check README.md contains the marker
grep "<!-- BADGES -->" README.md

# Or use custom marker
export BADGE_SECTION_MARKER="<!-- MY_BADGES -->"
```

### Configuration Debugging

Enable debug logging to troubleshoot configuration issues:

```python
#!/usr/bin/env python3
"""Configuration debugging script."""

import logging
import os
from badges.config import get_badge_config, BadgeConfigurationError

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

def debug_configuration():
    """Debug badge configuration."""
    print("=== Configuration Debug ===\n")
    
    # Show environment variables
    print("Environment Variables:")
    env_vars = [
        "GITHUB_REPOSITORY",
        "PYPI_PACKAGE", 
        "SHIELDS_BASE_URL",
        "BADGE_SECTION_MARKER",
        "BADGE_MAX_RETRIES",
        "BADGE_RETRY_DELAY",
    ]
    
    for var in env_vars:
        value = os.environ.get(var, "Not set")
        print(f"  {var}: {value}")
    
    print()
    
    # Try to load configuration
    try:
        config = get_badge_config()
        print("Configuration loaded successfully:")
        print(f"  GitHub Repository: {config.github_repo}")
        print(f"  PyPI Package: {config.pypi_package}")
        print(f"  Shields Base URL: {config.shields_base_url}")
        print(f"  Max Retries: {config.max_retries}")
        print(f"  Retry Delay: {config.retry_delay}")
        print(f"  Badge Section Marker: {config.badge_section_marker}")
        
    except BadgeConfigurationError as e:
        print(f"Configuration error: {e}")

if __name__ == "__main__":
    debug_configuration()
```

This configuration guide covers all aspects of setting up and customizing the badge system for your specific needs.