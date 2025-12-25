#!/usr/bin/env python3
"""Update package URLs in pyproject.toml with actual repository information.

This script updates the placeholder URLs in pyproject.toml with the actual
GitHub repository information detected from the Git remote.
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys


def get_git_remote_url() -> str | None:
    """Get the Git remote URL for origin.

    Returns:
        Git remote URL or None if not found
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def parse_github_url(git_url: str) -> tuple[str, str] | None:
    """Parse GitHub username and repository from Git URL.

    Args:
        git_url: Git remote URL

    Returns:
        Tuple of (username, repository) or None if not a GitHub URL
    """
    # Handle both HTTPS and SSH URLs
    patterns = [
        r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
        r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?/?$",
    ]

    for pattern in patterns:
        match = re.match(pattern, git_url)
        if match:
            return match.group(1), match.group(2)

    return None


def update_pyproject_urls(username: str, repository: str) -> bool:
    """Update URLs in pyproject.toml with actual repository information.

    Args:
        username: GitHub username
        repository: Repository name

    Returns:
        True if successful, False otherwise
    """
    pyproject_path = Path("pyproject.toml")

    if not pyproject_path.exists():
        print("Error: pyproject.toml not found", file=sys.stderr)
        return False

    try:
        content = pyproject_path.read_text()

        # Update URLs
        url_replacements = {
            'Homepage = "https://github.com/username/mypylogger"': f'Homepage = "https://github.com/{username}/{repository}"',
            'Documentation = "https://username.github.io/mypylogger"': f'Documentation = "https://{username}.github.io/{repository}"',
            'Repository = "https://github.com/username/mypylogger"': f'Repository = "https://github.com/{username}/{repository}"',
            '"Bug Tracker" = "https://github.com/username/mypylogger/issues"': f'"Bug Tracker" = "https://github.com/{username}/{repository}/issues"',
            'Changelog = "https://github.com/username/mypylogger/blob/main/CHANGELOG.md"': (
                f'Changelog = "https://github.com/{username}/{repository}/blob/main/CHANGELOG.md"'
            ),
            '"Source Code" = "https://github.com/username/mypylogger"': f'"Source Code" = "https://github.com/{username}/{repository}"',
            '"Download" = "https://pypi.org/project/mypylogger/"': f'"Download" = "https://pypi.org/project/{repository}/"',
        }

        updated_content = content
        changes_made = 0

        for old_url, new_url in url_replacements.items():
            if old_url in updated_content:
                updated_content = updated_content.replace(old_url, new_url)
                changes_made += 1
                print(f"Updated: {old_url} -> {new_url}")

        if changes_made > 0:
            pyproject_path.write_text(updated_content)
            print(f"Successfully updated {changes_made} URLs in pyproject.toml")
            return True
        print("No placeholder URLs found to update")
        return True

    except Exception as e:
        print(f"Error updating pyproject.toml: {e}", file=sys.stderr)
        return False


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Update package URLs with actual repository information"
    )
    parser.add_argument("--username", help="GitHub username (default: auto-detect from git remote)")
    parser.add_argument(
        "--repository", help="Repository name (default: auto-detect from git remote)"
    )

    args = parser.parse_args()

    username = args.username
    repository = args.repository

    # Auto-detect from Git remote if not provided
    if not username or not repository:
        git_url = get_git_remote_url()
        if not git_url:
            print("Error: Could not get Git remote URL", file=sys.stderr)
            sys.exit(1)

        parsed = parse_github_url(git_url)
        if not parsed:
            print(f"Error: Not a GitHub URL: {git_url}", file=sys.stderr)
            sys.exit(1)

        detected_username, detected_repository = parsed
        username = username or detected_username
        repository = repository or detected_repository

    print(f"Updating URLs for {username}/{repository}")

    if update_pyproject_urls(username, repository):
        print("Package URLs updated successfully")
        sys.exit(0)
    else:
        print("Failed to update package URLs")
        sys.exit(1)


if __name__ == "__main__":
    main()
