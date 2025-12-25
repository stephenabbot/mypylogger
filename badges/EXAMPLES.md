# Badge System Usage Examples

This document provides practical examples of using the mypylogger badge system in various scenarios.

## Basic Usage Examples

### Example 1: Simple Badge Update

```python
#!/usr/bin/env python3
"""Simple badge update example."""

from badges import update_project_badges

def main():
    """Update project badges with status detection."""
    print("Updating project badges...")
    
    success = update_project_badges(detect_status=True)
    
    if success:
        print("✓ Badges updated successfully!")
    else:
        print("✗ Badge update failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
```

### Example 2: Badge Generation with Error Handling

```python
#!/usr/bin/env python3
"""Badge generation with comprehensive error handling."""

import logging
from badges import generate_all_badges, create_badge_section, BadgeSystemError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_badges_with_fallback():
    """Generate badges with fallback to defaults on error."""
    try:
        # Try to generate badges with status detection
        logger.info("Generating badges with status detection...")
        badges = generate_all_badges(detect_status=True)
        
    except BadgeSystemError as e:
        logger.warning(f"Status detection failed: {e}")
        logger.info("Falling back to default badge generation...")
        
        try:
            # Fallback to default badges without status detection
            badges = generate_all_badges(detect_status=False)
        except BadgeSystemError as e:
            logger.error(f"Badge generation failed completely: {e}")
            return None
    
    if not badges:
        logger.error("No badges were generated")
        return None
    
    logger.info(f"Generated {len(badges)} badges successfully")
    
    # Create badge section
    try:
        badge_section = create_badge_section(badges)
        logger.info("Badge section created successfully")
        return badge_section
        
    except BadgeSystemError as e:
        logger.error(f"Failed to create badge section: {e}")
        return None

def main():
    """Main function with error handling."""
    badge_section = generate_badges_with_fallback()
    
    if badge_section:
        print("Badge Section Markdown:")
        print(badge_section.markdown)
        return 0
    else:
        print("Failed to generate badge section")
        return 1

if __name__ == "__main__":
    exit(main())
```

### Example 3: Individual Badge Generation

```python
#!/usr/bin/env python3
"""Individual badge generation example."""

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

def generate_individual_badges():
    """Generate each badge type individually."""
    badge_generators = {
        "Quality Gate": generate_quality_gate_badge,
        "Security Scan": generate_security_scan_badge,
        "Code Style": generate_code_style_badge,
        "Type Check": generate_type_check_badge,
        "Python Versions": generate_python_versions_badge,
        "PyPI Version": generate_pypi_version_badge,
        "Downloads": generate_downloads_badge,
        "License": generate_license_badge,
    }
    
    badges = {}
    
    for name, generator in badge_generators.items():
        try:
            url = generator()
            badges[name] = url
            print(f"✓ {name}: {url}")
        except Exception as e:
            print(f"✗ {name}: Failed to generate ({e})")
            badges[name] = None
    
    return badges

def main():
    """Generate and display individual badges."""
    print("Generating individual badges...\n")
    
    badges = generate_individual_badges()
    
    print(f"\nGenerated {sum(1 for url in badges.values() if url)} out of {len(badges)} badges")
    
    # Create markdown for successful badges
    markdown_badges = []
    for name, url in badges.items():
        if url:
            alt_text = name.replace(" ", " ")
            markdown = f"![{alt_text}]({url})"
            markdown_badges.append(markdown)
    
    if markdown_badges:
        print("\nMarkdown for generated badges:")
        print(" ".join(markdown_badges))
    
    return 0

if __name__ == "__main__":
    exit(main())
```

## Configuration Examples

### Example 4: Custom Configuration

```python
#!/usr/bin/env python3
"""Custom badge configuration example."""

import os
from badges.config import get_badge_config, BadgeConfigurationError

def setup_custom_config():
    """Set up custom badge configuration."""
    # Set custom environment variables
    os.environ["GITHUB_REPOSITORY"] = "myorg/myproject"
    os.environ["PYPI_PACKAGE"] = "myproject"
    os.environ["SHIELDS_BASE_URL"] = "https://img.shields.io"
    os.environ["BADGE_SECTION_MARKER"] = "<!-- PROJECT_BADGES -->"
    os.environ["BADGE_MAX_RETRIES"] = "15"
    os.environ["BADGE_RETRY_DELAY"] = "3"

def validate_config():
    """Validate badge configuration."""
    try:
        config = get_badge_config()
        
        print("Badge Configuration:")
        print(f"  GitHub Repository: {config.github_repo}")
        print(f"  PyPI Package: {config.pypi_package}")
        print(f"  Shields Base URL: {config.shields_base_url}")
        print(f"  Max Retries: {config.max_retries}")
        print(f"  Retry Delay: {config.retry_delay}")
        print(f"  Badge Section Marker: {config.badge_section_marker}")
        
        return True
        
    except BadgeConfigurationError as e:
        print(f"Configuration validation failed: {e}")
        return False

def main():
    """Set up and validate custom configuration."""
    print("Setting up custom badge configuration...")
    setup_custom_config()
    
    print("\nValidating configuration...")
    if validate_config():
        print("✓ Configuration is valid!")
        return 0
    else:
        print("✗ Configuration validation failed!")
        return 1

if __name__ == "__main__":
    exit(main())
```

### Example 5: Configuration Check Script

```python
#!/usr/bin/env python3
"""Configuration check and diagnostic script."""

import os
import sys
from badges.config import get_badge_config, BadgeConfigurationError

def check_environment_variables():
    """Check relevant environment variables."""
    env_vars = {
        "GITHUB_REPOSITORY": "GitHub repository (owner/repo)",
        "PYPI_PACKAGE": "PyPI package name",
        "SHIELDS_BASE_URL": "Shields.io base URL",
        "BADGE_SECTION_MARKER": "Badge section marker in README",
        "BADGE_MAX_RETRIES": "Maximum retry attempts",
        "BADGE_RETRY_DELAY": "Retry delay in seconds",
    }
    
    print("Environment Variables:")
    for var, description in env_vars.items():
        value = os.environ.get(var)
        if value:
            print(f"  ✓ {var}: {value}")
        else:
            print(f"  - {var}: Not set (using default)")
    print()

def check_configuration():
    """Check badge configuration."""
    try:
        config = get_badge_config()
        
        print("Configuration Validation:")
        print(f"  ✓ GitHub Repository: {config.github_repo}")
        print(f"  ✓ PyPI Package: {config.pypi_package}")
        print(f"  ✓ Shields Base URL: {config.shields_base_url}")
        print(f"  ✓ Max Retries: {config.max_retries}")
        print(f"  ✓ Retry Delay: {config.retry_delay}")
        print(f"  ✓ Badge Section Marker: {config.badge_section_marker}")
        print()
        
        return True
        
    except BadgeConfigurationError as e:
        print(f"Configuration Error: {e}")
        print()
        return False

def check_readme_file():
    """Check README.md file for badge section marker."""
    readme_path = "README.md"
    
    if not os.path.exists(readme_path):
        print(f"README Check:")
        print(f"  ✗ {readme_path} not found")
        return False
    
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        config = get_badge_config()
        marker = config.badge_section_marker
        
        print(f"README Check:")
        print(f"  ✓ {readme_path} exists")
        
        if marker in content:
            print(f"  ✓ Badge section marker found: {marker}")
        else:
            print(f"  - Badge section marker not found: {marker}")
            print(f"    Add '{marker}' to README.md where you want badges to appear")
        
        return True
        
    except Exception as e:
        print(f"README Check:")
        print(f"  ✗ Error reading {readme_path}: {e}")
        return False

def main():
    """Run comprehensive configuration check."""
    print("=== Badge System Configuration Check ===\n")
    
    # Check environment variables
    check_environment_variables()
    
    # Check configuration
    config_valid = check_configuration()
    
    # Check README file
    readme_valid = check_readme_file()
    
    # Summary
    print("=== Summary ===")
    if config_valid and readme_valid:
        print("✓ Badge system is properly configured!")
        return 0
    else:
        print("✗ Badge system configuration needs attention!")
        return 1

if __name__ == "__main__":
    exit(main())
```

## CI/CD Integration Examples

### Example 6: GitHub Actions Workflow

```yaml
# .github/workflows/update-badges.yml
name: Update Project Badges

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    # Update badges daily at 6 AM UTC
    - cron: '0 6 * * *'

jobs:
  update-badges:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e .
      
      - name: Update badges
        run: |
          python -m badges --verbose
        env:
          GITHUB_REPOSITORY: ${{ github.repository }}
          PYPI_PACKAGE: mypylogger
      
      - name: Check for changes
        id: verify-changed-files
        run: |
          if [ -n "$(git status --porcelain)" ]; then
            echo "changed=true" >> $GITHUB_OUTPUT
          else
            echo "changed=false" >> $GITHUB_OUTPUT
          fi
      
      - name: Commit badge updates
        if: steps.verify-changed-files.outputs.changed == 'true'
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add README.md
          git commit -m "Update project badges [skip ci]"
          git push
```

### Example 7: Badge Update Script for CI/CD

```python
#!/usr/bin/env python3
"""CI/CD badge update script with error handling."""

import sys
import logging
from badges import update_project_badges, BadgeSystemError

# Configure logging for CI/CD
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def update_badges_for_cicd():
    """Update badges with CI/CD-appropriate error handling."""
    try:
        logger.info("Starting badge update for CI/CD...")
        
        # Update badges with status detection
        success = update_project_badges(detect_status=True)
        
        if success:
            logger.info("✓ Badges updated successfully")
            return 0
        else:
            logger.warning("Badge update completed with warnings")
            # Don't fail CI/CD for badge update issues
            return 0
            
    except BadgeSystemError as e:
        logger.error(f"Badge system error: {e}")
        # Don't fail CI/CD for badge system errors
        logger.info("Continuing CI/CD pipeline despite badge update failure")
        return 0
        
    except Exception as e:
        logger.error(f"Unexpected error during badge update: {e}")
        # Don't fail CI/CD for unexpected errors
        logger.info("Continuing CI/CD pipeline despite unexpected error")
        return 0

def main():
    """Main function for CI/CD badge updates."""
    logger.info("=== CI/CD Badge Update ===")
    
    exit_code = update_badges_for_cicd()
    
    if exit_code == 0:
        logger.info("Badge update completed")
    else:
        logger.error("Badge update failed")
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
```

## Advanced Usage Examples

### Example 8: Custom Badge Status Detection

```python
#!/usr/bin/env python3
"""Custom badge status detection example."""

import subprocess
import sys
from pathlib import Path
from badges import generate_all_badges, Badge
from badges.status import BadgeStatusCache, get_status_cache

def run_custom_quality_checks():
    """Run custom quality checks and return status."""
    try:
        # Run ruff check
        result = subprocess.run(
            ["uv", "run", "ruff", "check", "."],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        ruff_passing = result.returncode == 0
        
        # Run mypy check
        result = subprocess.run(
            ["uv", "run", "mypy", "src/"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        mypy_passing = result.returncode == 0
        
        # Run tests
        result = subprocess.run(
            ["uv", "run", "pytest", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        tests_passing = result.returncode == 0
        
        return {
            "code_style": "passing" if ruff_passing else "failing",
            "type_check": "passing" if mypy_passing else "failing",
            "quality_gate": "passing" if (ruff_passing and mypy_passing and tests_passing) else "failing",
        }
        
    except subprocess.TimeoutExpired:
        return {
            "code_style": "unknown",
            "type_check": "unknown", 
            "quality_gate": "unknown",
        }
    except Exception as e:
        print(f"Error running quality checks: {e}")
        return {}

def generate_badges_with_custom_status():
    """Generate badges with custom status detection."""
    print("Running custom quality checks...")
    
    # Get custom status
    custom_status = run_custom_quality_checks()
    
    # Update status cache
    cache = get_status_cache()
    for badge_name, status in custom_status.items():
        cache.set_status(badge_name, {"status": status})
    
    print(f"Custom status detected: {custom_status}")
    
    # Generate badges (will use cached status)
    badges = generate_all_badges(detect_status=True)
    
    return badges

def main():
    """Generate badges with custom status detection."""
    badges = generate_badges_with_custom_status()
    
    print(f"\nGenerated {len(badges)} badges:")
    for badge in badges:
        print(f"  {badge.name}: {badge.status} - {badge.url}")
    
    return 0

if __name__ == "__main__":
    exit(main())
```

### Example 9: Batch Badge Operations

```python
#!/usr/bin/env python3
"""Batch badge operations example."""

import json
import sys
from pathlib import Path
from badges import generate_all_badges, create_badge_section

def save_badges_to_json(badges, filename="badges.json"):
    """Save badges to JSON file."""
    badge_data = []
    
    for badge in badges:
        badge_data.append({
            "name": badge.name,
            "url": badge.url,
            "alt_text": badge.alt_text,
            "link_url": badge.link_url,
            "status": badge.status,
        })
    
    with open(filename, 'w') as f:
        json.dump(badge_data, f, indent=2)
    
    print(f"Badges saved to {filename}")

def load_badges_from_json(filename="badges.json"):
    """Load badges from JSON file."""
    if not Path(filename).exists():
        print(f"Badge file {filename} not found")
        return []
    
    with open(filename, 'r') as f:
        badge_data = json.load(f)
    
    from badges.config import Badge
    
    badges = []
    for data in badge_data:
        badge = Badge(
            name=data["name"],
            url=data["url"],
            alt_text=data["alt_text"],
            link_url=data.get("link_url"),
            status=data.get("status", "unknown"),
        )
        badges.append(badge)
    
    print(f"Loaded {len(badges)} badges from {filename}")
    return badges

def generate_multiple_formats(badges):
    """Generate badges in multiple formats."""
    # Markdown format
    badge_section = create_badge_section(badges)
    
    with open("badges.md", 'w') as f:
        f.write("# Project Badges\n\n")
        f.write(badge_section.markdown)
        f.write("\n")
    
    print("Badges saved to badges.md")
    
    # HTML format
    html_badges = []
    for badge in badges:
        if badge.link_url:
            html = f'<a href="{badge.link_url}"><img src="{badge.url}" alt="{badge.alt_text}"></a>'
        else:
            html = f'<img src="{badge.url}" alt="{badge.alt_text}">'
        html_badges.append(html)
    
    with open("badges.html", 'w') as f:
        f.write("<!DOCTYPE html>\n<html>\n<head>\n<title>Project Badges</title>\n</head>\n<body>\n")
        f.write("<h1>Project Badges</h1>\n")
        f.write("<p>\n")
        f.write("\n".join(html_badges))
        f.write("\n</p>\n</body>\n</html>\n")
    
    print("Badges saved to badges.html")

def main():
    """Perform batch badge operations."""
    print("=== Batch Badge Operations ===\n")
    
    # Generate fresh badges
    print("Generating badges...")
    badges = generate_all_badges(detect_status=True)
    
    if not badges:
        print("No badges generated")
        return 1
    
    # Save to JSON
    save_badges_to_json(badges)
    
    # Generate multiple formats
    generate_multiple_formats(badges)
    
    # Load from JSON (demonstration)
    loaded_badges = load_badges_from_json()
    
    print(f"\nBatch operations completed:")
    print(f"  Generated: {len(badges)} badges")
    print(f"  Loaded: {len(loaded_badges)} badges")
    print(f"  Files created: badges.json, badges.md, badges.html")
    
    return 0

if __name__ == "__main__":
    exit(main())
```

## Testing Examples

### Example 10: Badge System Testing

```python
#!/usr/bin/env python3
"""Badge system testing example."""

import tempfile
import unittest
from pathlib import Path
from badges import generate_all_badges, update_project_badges
from badges.config import get_badge_config

class BadgeSystemTest(unittest.TestCase):
    """Test badge system functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_badge_generation(self):
        """Test badge generation."""
        badges = generate_all_badges(detect_status=False)
        
        self.assertIsInstance(badges, list)
        self.assertGreater(len(badges), 0)
        
        # Check that all badges have required attributes
        for badge in badges:
            self.assertIsInstance(badge.name, str)
            self.assertIsInstance(badge.url, str)
            self.assertIsInstance(badge.alt_text, str)
            self.assertTrue(badge.url.startswith("https://"))
    
    def test_configuration(self):
        """Test badge configuration."""
        config = get_badge_config()
        
        self.assertIsInstance(config.github_repo, str)
        self.assertIsInstance(config.pypi_package, str)
        self.assertIsInstance(config.shields_base_url, str)
        self.assertIn("/", config.github_repo)
        self.assertTrue(config.shields_base_url.startswith("https://"))
    
    def test_readme_update_with_temp_file(self):
        """Test README update with temporary file."""
        # Create temporary README
        temp_readme = Path(self.temp_dir) / "README.md"
        temp_readme.write_text("# Test Project\n\n<!-- BADGES -->\n\n## Content\n")
        
        # Change to temp directory
        import os
        os.chdir(self.temp_dir)
        
        try:
            # Test badge update
            success = update_project_badges(detect_status=False)
            self.assertTrue(success)
            
            # Check README was updated
            updated_content = temp_readme.read_text()
            self.assertIn("![", updated_content)
            
        finally:
            # Restore original directory
            os.chdir(self.original_cwd)

def run_tests():
    """Run badge system tests."""
    unittest.main(verbosity=2)

if __name__ == "__main__":
    run_tests()
```

These examples demonstrate various ways to use the badge system, from basic usage to advanced customization and CI/CD integration. Each example includes error handling and follows best practices for production use.