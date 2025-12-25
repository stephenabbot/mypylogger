# Badge System Documentation

## Overview

The mypylogger badge system provides automated generation and management of project status badges using shields.io integration. This system displays professional project badges in README.md with atomic file operations to prevent race conditions during concurrent updates.

## Features

- **8 Professional Badges**: Quality gate, security scan, code style, type checking, Python versions, PyPI version, downloads, and license
- **Shields.io Integration**: Dynamic badge generation using shields.io service
- **Atomic README Updates**: Race condition prevention with retry logic
- **PyPI Compatibility**: Works correctly after package publication
- **CI/CD Integration**: Graceful error handling for automated environments
- **Minimal Dependencies**: Uses only Python standard library and existing project dependencies

## Badge Types

### 1. Quality Gate Badge
- **Purpose**: Shows GitHub Actions quality-gate.yml workflow status
- **URL**: `https://img.shields.io/github/actions/workflow/status/{repo}/quality-gate.yml?branch=main&style=flat`
- **Status**: Reflects current CI/CD pipeline status

### 2. Security Scan Badge
- **Purpose**: Shows GitHub Actions security-scan.yml workflow status
- **URL**: `https://img.shields.io/github/actions/workflow/status/{repo}/security-scan.yml?branch=main&style=flat`
- **Status**: Reflects security scanning results

### 3. Code Style Badge
- **Purpose**: Shows Ruff code formatting compliance
- **URL**: `https://img.shields.io/badge/code%20style-ruff-000000?style=flat`
- **Status**: Static badge indicating Ruff usage

### 4. Type Checking Badge
- **Purpose**: Shows mypy type checking validation
- **URL**: `https://img.shields.io/badge/type%20checked-mypy-blue?style=flat`
- **Status**: Static badge indicating mypy usage

### 5. Python Versions Badge
- **Purpose**: Shows Python version compatibility
- **URL**: `https://img.shields.io/pypi/pyversions/{package}?style=flat`
- **Status**: Dynamic badge from PyPI package metadata

### 6. PyPI Version Badge
- **Purpose**: Shows current PyPI package version
- **URL**: `https://img.shields.io/pypi/v/{package}?style=flat`
- **Status**: Dynamic badge from PyPI package information

### 7. Downloads Badge
- **Purpose**: Shows development status
- **URL**: `https://img.shields.io/badge/downloads-development-yellow?style=flat`
- **Status**: Static badge indicating development phase

### 8. License Badge
- **Purpose**: Shows project license (MIT)
- **URL**: `https://img.shields.io/github/license/{repo}?style=flat`
- **Status**: Dynamic badge from GitHub repository license

## Installation

The badge system is included with mypylogger. No additional installation is required.

```bash
# Install mypylogger (includes badge system)
pip install mypylogger
```

## Usage

### Command Line Interface

#### Basic Badge Update
```bash
# Update badges in README.md
python -m badges

# Update badges with verbose output
python -m badges --verbose

# Dry run (generate badges but don't update README)
python -m badges --dry-run

# Skip badge status detection (use defaults)
python -m badges --no-status-detection
```

#### Configuration Check
```bash
# Check badge configuration
python -m badges --config-check
```

### Python API

#### Basic Usage
```python
from badges import update_project_badges

# Update all badges in README.md
success = update_project_badges()
if success:
    print("Badges updated successfully")
else:
    print("Badge update failed")
```

#### Generate Badges Only
```python
from badges import generate_all_badges, create_badge_section

# Generate all badges with status detection
badges = generate_all_badges(detect_status=True)

# Create badge section markdown
badge_section = create_badge_section(badges)
print(badge_section.markdown)
```

#### Individual Badge Generation
```python
from badges import (
    generate_quality_gate_badge,
    generate_security_scan_badge,
    generate_code_style_badge,
    generate_type_check_badge,
    generate_python_versions_badge,
    generate_pypi_version_badge,
    generate_downloads_badge,
    generate_license_badge,
)

# Generate individual badges
quality_url = generate_quality_gate_badge()
security_url = generate_security_scan_badge()
style_url = generate_code_style_badge()
type_url = generate_type_check_badge()
python_url = generate_python_versions_badge()
pypi_url = generate_pypi_version_badge()
downloads_url = generate_downloads_badge()
license_url = generate_license_badge()
```

## Configuration

### Environment Variables

The badge system can be configured using environment variables:

```bash
# GitHub repository (default: username/mypylogger)
export GITHUB_REPOSITORY="your-username/your-repo"

# PyPI package name (default: mypylogger)
export PYPI_PACKAGE="your-package-name"

# Shields.io base URL (default: https://img.shields.io)
export SHIELDS_BASE_URL="https://img.shields.io"

# Badge section marker in README (default: <!-- BADGES -->)
export BADGE_SECTION_MARKER="<!-- BADGES -->"

# Atomic write retry settings
export BADGE_MAX_RETRIES="10"
export BADGE_RETRY_DELAY="5"
```

### Configuration Validation

```python
from badges.config import get_badge_config, BadgeConfigurationError

try:
    config = get_badge_config()
    print(f"GitHub repo: {config.github_repo}")
    print(f"PyPI package: {config.pypi_package}")
    print(f"Shields URL: {config.shields_base_url}")
except BadgeConfigurationError as e:
    print(f"Configuration error: {e}")
```

## README Integration

### Badge Section Marker

Add a badge section marker to your README.md where you want badges to appear:

```markdown
# Your Project

<!-- BADGES -->

## Description
Your project description here...
```

### Automatic Badge Insertion

The badge system will automatically:
1. Locate the `<!-- BADGES -->` marker in README.md
2. Generate current badge URLs with status detection
3. Insert badges as a single line of markdown
4. Use atomic write operations to prevent file corruption

### Manual Badge Section

You can also manually create a badge section:

```markdown
# Your Project

[![Quality Gate](https://img.shields.io/github/actions/workflow/status/username/repo/quality-gate.yml?branch=main&style=flat)](https://github.com/username/repo/actions)
[![Security Scan](https://img.shields.io/github/actions/workflow/status/username/repo/security-scan.yml?branch=main&style=flat)](https://github.com/username/repo/actions)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000?style=flat)](https://github.com/astral-sh/ruff)
[![Type Checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue?style=flat)](http://mypy-lang.org/)
[![Python Versions](https://img.shields.io/pypi/pyversions/mypylogger?style=flat)](https://pypi.org/project/mypylogger/)
[![PyPI Version](https://img.shields.io/pypi/v/mypylogger?style=flat)](https://pypi.org/project/mypylogger/)
[![Downloads: Development](https://img.shields.io/badge/downloads-development-yellow?style=flat)](https://pypi.org/project/mypylogger/)
[![License: MIT](https://img.shields.io/github/license/username/mypylogger?style=flat)](https://github.com/username/mypylogger/blob/main/LICENSE)

## Description
Your project description here...
```

## CI/CD Integration

### GitHub Actions

Add badge updates to your CI/CD workflow:

```yaml
name: Update Badges
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  update-badges:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -e .
      
      - name: Update badges
        run: |
          python -m badges --verbose
        env:
          GITHUB_REPOSITORY: ${{ github.repository }}
      
      - name: Commit badge updates
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add README.md
          git diff --staged --quiet || git commit -m "Update project badges"
          git push
```

### Error Handling in CI/CD

The badge system provides graceful error handling for CI/CD environments:

```bash
# Badge system returns appropriate exit codes
python -m badges
echo "Exit code: $?"

# Use conditional execution in CI/CD
python -m badges || echo "Badge update failed, continuing..."
```

## Error Handling

### Common Issues

#### Configuration Errors
```python
from badges.config import BadgeConfigurationError

try:
    from badges import update_project_badges
    update_project_badges()
except BadgeConfigurationError as e:
    print(f"Configuration error: {e}")
    # Fix configuration and retry
```

#### Network Errors
```python
from badges import BadgeSystemError

try:
    from badges import update_project_badges
    update_project_badges()
except BadgeSystemError as e:
    print(f"Badge system error: {e}")
    # Retry with exponential backoff
```

#### File Operation Errors
```python
import logging

# Enable verbose logging to debug file operations
logging.basicConfig(level=logging.DEBUG)

from badges import update_project_badges
update_project_badges()
```

### Troubleshooting

#### Badge Not Updating
1. Check README.md contains `<!-- BADGES -->` marker
2. Verify file permissions allow writing to README.md
3. Check network connectivity to shields.io and APIs
4. Validate configuration with `python -m badges --config-check`

#### API Failures
1. Check GitHub repository exists and is accessible
2. Verify PyPI package name is correct
3. Test network connectivity to api.github.com and pypi.org
4. Check for API rate limiting

#### File Corruption
1. Badge system uses atomic writes to prevent corruption
2. Temporary files are created and renamed atomically
3. Retry mechanism handles file contention
4. Backup original README.md before updates

## Development

### Running Tests

```bash
# Run all badge system tests
uv run pytest tests/unit/test_badge_*.py -v

# Run integration tests
uv run pytest tests/integration/test_badge_workflow.py -v

# Test with coverage
uv run pytest --cov=badges tests/unit/test_badge_*.py
```

### Code Quality

```bash
# Format code
uv run ruff format badges/

# Check linting
uv run ruff check badges/

# Type checking
uv run mypy badges/
```

### Security Scanning

```bash
# Run security scans (integrated with badge system)
python -m badges.security
```

## API Reference

### Core Functions

#### `update_project_badges(detect_status: bool = True) -> bool`
Main badge update workflow - generate badges and update README.

**Parameters:**
- `detect_status`: Whether to detect actual badge status or use defaults

**Returns:**
- `True` if badge update was successful, `False` otherwise

**Raises:**
- `BadgeSystemError`: If badge update workflow fails

#### `generate_all_badges(detect_status: bool = True) -> list[Badge]`
Generate all project badges with current status.

**Parameters:**
- `detect_status`: Whether to detect actual badge status or use defaults

**Returns:**
- List of Badge objects with generated URLs and status

**Raises:**
- `BadgeSystemError`: If badge generation fails

#### `create_badge_section(badges: list[Badge]) -> BadgeSection`
Create badge section with markdown formatting.

**Parameters:**
- `badges`: List of Badge objects to include in section

**Returns:**
- BadgeSection with formatted markdown content

**Raises:**
- `BadgeSystemError`: If badge section creation fails

### Data Models

#### `Badge`
```python
@dataclass
class Badge:
    name: str
    url: str
    alt_text: str
    link_url: str | None = None
    status: str = "unknown"  # "passing", "failing", "unknown"
```

#### `BadgeSection`
```python
@dataclass
class BadgeSection:
    title: str
    badges: list[Badge]
    markdown: str
```

#### `BadgeConfig`
```python
@dataclass
class BadgeConfig:
    github_repo: str
    pypi_package: str
    shields_base_url: str
    max_retries: int = 10
    retry_delay: int = 5
    badge_section_marker: str = "<!-- BADGES -->"
```

### Exceptions

#### `BadgeSystemError`
Raised when badge system operations fail.

#### `BadgeConfigurationError`
Raised when badge configuration is invalid.

#### `BadgeStatusError`
Raised when badge status detection fails.

## License

This badge system is part of mypylogger and is licensed under the MIT License.