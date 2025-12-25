"""README update module with CI-only badge updates.

This module provides functionality to update README.md with generated badges
exclusively in CI/CD environments, with git commit functionality.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def find_badge_section(content: str) -> tuple[int, int]:
    """Locate badge insertion point in README content.

    Args:
        content: README.md file content as string.

    Returns:
        Tuple of (start_index, end_index) for badge section location.
    """
    if not content:
        return (0, 0)

    # Look for existing badge section markers
    start_marker = "<!-- BADGES START -->"
    end_marker = "<!-- BADGES END -->"
    single_marker = "<!-- BADGES -->"

    start_pos = content.find(start_marker)
    end_pos = content.find(end_marker)

    if start_pos != -1 and end_pos != -1:
        # Found both markers, return the section between them
        return (start_pos, end_pos + len(end_marker))

    # Look for single marker
    single_pos = content.find(single_marker)
    if single_pos != -1:
        return (single_pos, single_pos + len(single_marker))

    # No markers found, find position after first heading
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.strip().startswith("# "):
            # Found first heading, position after it
            if i + 1 < len(lines):
                # Position at start of next line
                pos = len("\n".join(lines[: i + 1])) + 1
                return (pos, pos)
            # Heading is last line, position at end
            return (len(content), len(content))

    # No heading found, position at start
    return (0, 0)


def atomic_write_readme(content: str, max_retries: int = 10) -> bool:
    """Perform atomic write with retry logic for race condition prevention.

    Args:
        content: Complete README content to write.
        max_retries: Maximum number of retry attempts for file contention.

    Returns:
        True if write was successful, False otherwise.
    """
    readme_path = Path("README.md")

    for attempt in range(max_retries):
        try:
            # Create backup if original file exists
            if readme_path.exists():
                backup_path = Path("README.md.backup")
                backup_path.write_text(readme_path.read_text(), encoding="utf-8")

            # Write to temporary file first
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".tmp", dir=readme_path.parent, delete=False, encoding="utf-8"
            ) as temp_file:
                temp_file.write(content)
                temp_path = Path(temp_file.name)

            # Verify content was written correctly
            if temp_path.read_text(encoding="utf-8") != content:
                temp_path.unlink(missing_ok=True)
                return False

            # Atomic rename operation
            temp_path.replace(readme_path)
            return True

        except (OSError, PermissionError):
            # Handle file contention or permission errors
            # Clean up temp file if it exists
            if "temp_path" in locals():
                temp_path.unlink(missing_ok=True)

            if attempt < max_retries - 1:
                time.sleep(5)  # Wait 5 seconds before retry
                continue
            # Final attempt failed
            return False
        except Exception:
            # Unexpected error, clean up temp file if it exists
            if "temp_path" in locals():
                temp_path.unlink(missing_ok=True)
            return False

    return False


def update_readme_with_badges(badges: list[str]) -> bool:
    """Update README.md with badge markdown using atomic writes.

    Args:
        badges: List of badge markdown strings to insert into README.

    Returns:
        True if update was successful, False otherwise.
    """
    readme_path = Path("README.md")

    # Check if README exists
    if not readme_path.exists():
        return False

    try:
        # Read current README content
        current_content = readme_path.read_text(encoding="utf-8")

        # Find badge section location
        start_pos, end_pos = find_badge_section(current_content)

        # Generate badge section content
        if badges:
            badge_lines = []
            badge_lines.append("<!-- BADGES START -->")
            badge_lines.extend(badges)
            badge_lines.append("<!-- BADGES END -->")
            badge_section = "\n".join(badge_lines)
        else:
            # Empty badge list, create empty section
            badge_section = "<!-- BADGES START -->\n<!-- BADGES END -->"

        # Construct new content
        if start_pos == end_pos:
            # No existing section, insert new one
            if start_pos == 0:
                # Insert at beginning
                new_content = badge_section + "\n\n" + current_content
            else:
                # Insert after first heading
                new_content = (
                    current_content[:start_pos]
                    + "\n"
                    + badge_section
                    + "\n"
                    + current_content[start_pos:]
                )
        else:
            # Replace existing section
            new_content = current_content[:start_pos] + badge_section + current_content[end_pos:]

        # Write updated content atomically
        return atomic_write_readme(new_content)

    except Exception:
        return False


def is_ci_environment() -> bool:
    """Check if we're running in a CI/CD environment.

    Returns:
        True if running in CI, False otherwise.
    """
    ci_indicators = [
        "CI",
        "CONTINUOUS_INTEGRATION",
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "JENKINS_URL",
        "TRAVIS",
        "CIRCLECI",
        "BUILDKITE",
    ]

    return any(os.getenv(indicator) for indicator in ci_indicators)


def setup_git_config() -> bool:
    """Configure git for CI commits.

    Returns:
        True if git config was set up successfully, False otherwise.
    """
    try:
        # Set git user for CI commits
        subprocess.run(
            ["git", "config", "--local", "user.email", "action@github.com"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "config", "--local", "user.name", "GitHub Action"],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to configure git: {e}", file=sys.stderr)
        return False


def commit_badge_updates() -> bool:
    """Commit updated README back to main branch with [skip ci] message.

    Returns:
        True if commit was successful, False otherwise.
    """
    try:
        # Check if there are any changes to README.md
        result = subprocess.run(
            ["git", "diff", "--quiet", "README.md"],
            check=False,
            capture_output=True,
        )

        if result.returncode == 0:
            # No changes to commit
            print("No badge changes to commit", file=sys.stderr)
            return True

        # Stage README.md changes
        subprocess.run(
            ["git", "add", "README.md"],
            check=True,
            capture_output=True,
            text=True,
        )

        # Check if there are staged changes
        result = subprocess.run(
            ["git", "diff", "--staged", "--quiet"],
            check=False,
            capture_output=True,
        )

        if result.returncode == 0:
            # No staged changes
            print("No staged badge changes to commit", file=sys.stderr)
            return True

        # Commit with [skip ci] to prevent infinite loops
        subprocess.run(
            ["git", "commit", "-m", "docs: update badges [skip ci]"],
            check=True,
            capture_output=True,
            text=True,
        )

        # Push changes to main branch
        subprocess.run(
            ["git", "push", "origin", "HEAD:main"],
            check=True,
            capture_output=True,
            text=True,
        )

        print("Successfully committed and pushed badge updates", file=sys.stderr)
        return True

    except subprocess.CalledProcessError as e:
        print(f"Failed to commit badge updates: {e}", file=sys.stderr)
        print(f"Command output: {e.output if hasattr(e, 'output') else 'N/A'}", file=sys.stderr)
        return False


def verify_ci_test_success() -> bool:
    """Verify that CI tests have passed before allowing badge updates.

    Returns:
        True if CI tests passed, False otherwise.
    """
    # Check for CI environment variables that indicate test success
    ci_success_indicators = [
        "GITHUB_ACTIONS",  # GitHub Actions environment
        "CI",  # General CI indicator
    ]

    # Must be in CI environment
    if not any(os.getenv(indicator) for indicator in ci_success_indicators):
        print("Not in CI environment - badge updates not allowed", file=sys.stderr)
        return False

    # For GitHub Actions, check if we're in a successful workflow context
    if os.getenv("GITHUB_ACTIONS"):
        # Check if this is running after tests (workflow should set this)
        if not os.getenv("TESTS_PASSED"):
            print("CI tests have not passed - badge updates not allowed", file=sys.stderr)
            return False

    return True


def update_readme_with_badges_ci_only(badges: list[str]) -> bool:
    """Update README.md with badges (CI environment only, after successful tests).

    This function ensures badge updates only occur in CI/CD environments
    after successful test execution to maintain consistency with actual code state.

    Args:
        badges: List of badge markdown strings to insert.

    Returns:
        True if update was successful, False otherwise.
    """
    # Verify we're in CI environment and tests have passed
    if not verify_ci_test_success():
        return False

    # Set up git configuration for CI commits
    if not setup_git_config():
        print("Failed to configure git for CI environment", file=sys.stderr)
        return False

    # Update README with badges
    if not update_readme_with_badges(badges):
        print("Failed to update README with badges", file=sys.stderr)
        return False

    # Commit and push changes back to repository
    return commit_badge_updates()
