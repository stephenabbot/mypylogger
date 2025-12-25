#!/usr/bin/env python3
"""Generate changelog entries from commit messages.

This script generates changelog entries from Git commit messages following
conventional commit format and updates the CHANGELOG.md file.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import subprocess
import sys


class ChangelogGenerator:
    """Generate changelog entries from Git commit messages."""

    def __init__(self, changelog_path: str = "CHANGELOG.md") -> None:
        """Initialize changelog generator.

        Args:
            changelog_path: Path to the CHANGELOG.md file
        """
        self.changelog_path = Path(changelog_path)
        self.commit_types = {
            "feat": "Added",
            "fix": "Fixed",
            "docs": "Changed",
            "style": "Changed",
            "refactor": "Changed",
            "perf": "Changed",
            "test": "Changed",
            "chore": "Changed",
            "ci": "Changed",
            "build": "Changed",
            "revert": "Changed",
            "security": "Security",
            "breaking": "Changed",
            "deprecated": "Deprecated",
            "removed": "Removed",
        }

    def get_commits_since_tag(self, tag: str | None = None) -> list[str]:
        """Get commit messages since the specified tag.

        Args:
            tag: Git tag to get commits since. If None, gets all commits.

        Returns:
            List of commit messages

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        try:
            if tag:
                cmd = ["git", "log", f"{tag}..HEAD", "--oneline", "--no-merges"]
            else:
                cmd = ["git", "log", "--oneline", "--no-merges", "-10"]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        except subprocess.CalledProcessError as e:
            print(f"Error getting commits: {e}", file=sys.stderr)
            return []

    def parse_commit_message(self, commit_line: str) -> tuple[str, str, str] | None:
        """Parse a commit message line into type, scope, and description.

        Args:
            commit_line: Git commit line (hash + message)

        Returns:
            Tuple of (type, scope, description) or None if not conventional format
        """
        # Remove commit hash
        parts = commit_line.split(" ", 1)
        if len(parts) < 2:
            return None

        message = parts[1]

        # Parse conventional commit format: type(scope): description
        pattern = r"^(\w+)(?:\(([^)]+)\))?: (.+)$"
        match = re.match(pattern, message)

        if match:
            commit_type = match.group(1).lower()
            scope = match.group(2) or ""
            description = match.group(3)
            return commit_type, scope, description

        return None

    def categorize_changes(self, commits: list[str]) -> dict[str, list[str]]:
        """Categorize commits by changelog section.

        Args:
            commits: List of commit message lines

        Returns:
            Dictionary mapping changelog sections to lists of changes
        """
        categories: dict[str, list[str]] = {}

        for commit in commits:
            parsed = self.parse_commit_message(commit)
            if not parsed:
                continue

            commit_type, scope, description = parsed

            # Map commit type to changelog category
            category = self.commit_types.get(commit_type, "Changed")

            # Format the change entry
            change_entry = f"**{scope}**: {description}" if scope else description

            if category not in categories:
                categories[category] = []
            categories[category].append(change_entry)

        return categories

    def get_latest_version(self) -> str | None:
        """Get the latest version tag from Git.

        Returns:
            Latest version tag or None if no tags found
        """
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def get_new_version(self) -> str | None:
        """Get the new version from environment or pyproject.toml.

        Returns:
            New version string or None if not found
        """
        import os

        # Check environment variable first (set by bump2version)
        new_version = os.environ.get("NEW_VERSION")
        if new_version:
            return new_version

        # Try to read from pyproject.toml
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                print(
                    "Warning: Cannot read pyproject.toml, tomllib/tomli not available",
                    file=sys.stderr,
                )
                return None

        try:
            with open("pyproject.toml", "rb") as f:
                data = tomllib.load(f)
                return data.get("project", {}).get("version")
        except (FileNotFoundError, KeyError):
            return None

    def format_changelog_entry(self, version: str, categories: dict[str, list[str]]) -> str:
        """Format a changelog entry for the given version and changes.

        Args:
            version: Version string
            categories: Dictionary of categorized changes

        Returns:
            Formatted changelog entry
        """
        today = datetime.now().strftime("%Y-%m-%d")
        entry_lines = [f"## [{version}] - {today}", ""]

        # Order categories consistently
        category_order = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]

        for category in category_order:
            if categories.get(category):
                entry_lines.append(f"### {category}")
                entry_lines.append("")
                for change in categories[category]:
                    entry_lines.append(f"- {change}")
                entry_lines.append("")

        return "\n".join(entry_lines)

    def update_changelog(self, new_entry: str, version: str) -> None:
        """Update the CHANGELOG.md file with a new entry.

        Args:
            new_entry: Formatted changelog entry
            version: Version string for URL updates
        """
        if not self.changelog_path.exists():
            print(f"Error: {self.changelog_path} not found", file=sys.stderr)
            return

        content = self.changelog_path.read_text()

        # Find the [Unreleased] section and insert new entry after it
        unreleased_pattern = r"(## \[Unreleased\].*?\n\n)"
        match = re.search(unreleased_pattern, content, re.DOTALL)

        if match:
            # Insert new entry after unreleased section
            insert_pos = match.end()
            new_content = content[:insert_pos] + new_entry + "\n" + content[insert_pos:]
        else:
            # If no unreleased section, insert after first ## heading
            lines = content.split("\n")
            insert_line = 0
            for i, line in enumerate(lines):
                if line.startswith("## "):
                    insert_line = i
                    break

            lines.insert(insert_line, new_entry)
            new_content = "\n".join(lines)

        # Update version links at the bottom
        new_content = self.update_version_links(new_content, version)

        self.changelog_path.write_text(new_content)
        print(f"Updated {self.changelog_path} with version {version}")

    def update_version_links(self, content: str, version: str) -> str:
        """Update version comparison links at the bottom of changelog.

        Args:
            content: Current changelog content
            version: New version string

        Returns:
            Updated changelog content
        """
        # Find existing version links section
        lines = content.split("\n")

        # Look for the [Unreleased] link and update it
        for i, line in enumerate(lines):
            if line.startswith("[Unreleased]:"):
                # Update unreleased link to compare from new version
                lines[i] = (
                    f"[Unreleased]: https://github.com/username/mypylogger/compare/v{version}...HEAD"
                )

                # Add new version link after unreleased
                new_version_link = (
                    f"[{version}]: https://github.com/username/mypylogger/releases/tag/v{version}"
                )
                lines.insert(i + 1, new_version_link)
                break

        return "\n".join(lines)

    def generate_changelog_for_version(self, version: str | None = None) -> None:
        """Generate changelog entry for a version.

        Args:
            version: Version to generate changelog for. If None, uses current version.
        """
        if not version:
            version = self.get_new_version()
            if not version:
                print("Error: Could not determine version", file=sys.stderr)
                return

        # Get commits since last tag
        latest_tag = self.get_latest_version()
        commits = self.get_commits_since_tag(latest_tag)

        if not commits:
            print("No commits found since last tag", file=sys.stderr)
            return

        # Categorize changes
        categories = self.categorize_changes(commits)

        if not categories:
            print("No conventional commits found", file=sys.stderr)
            return

        # Generate and update changelog
        new_entry = self.format_changelog_entry(version, categories)
        self.update_changelog(new_entry, version)

        # Create a file with just the latest entry for GitHub releases
        latest_path = Path("CHANGELOG_LATEST.md")
        latest_path.write_text(new_entry)
        print(f"Created {latest_path} for GitHub release")


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate changelog from commit messages")
    parser.add_argument(
        "--version", help="Version to generate changelog for (default: auto-detect)"
    )
    parser.add_argument(
        "--changelog", default="CHANGELOG.md", help="Path to changelog file (default: CHANGELOG.md)"
    )

    args = parser.parse_args()

    generator = ChangelogGenerator(args.changelog)
    generator.generate_changelog_for_version(args.version)


if __name__ == "__main__":
    main()
