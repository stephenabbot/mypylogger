"""Unit tests for README updater functionality."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from badges.updater import (
    atomic_write_readme,
    find_badge_section,
    is_ci_environment,
    setup_git_config,
    update_readme_with_badges,
    update_readme_with_badges_ci_only,
    verify_ci_test_success,
)


class TestFindBadgeSection:
    """Test find_badge_section function."""

    def test_find_badge_section_with_markers(self) -> None:
        """Test finding badge section with start and end markers."""
        content = """# Project Title

Some content here.

<!-- BADGES START -->
Existing badge content
<!-- BADGES END -->

More content here.
"""
        start, end = find_badge_section(content)

        # Should find the section between markers
        assert start > 0
        assert end > start
        assert "<!-- BADGES START -->" in content[start:end]
        assert "<!-- BADGES END -->" in content[start:end]

    def test_find_badge_section_with_single_marker(self) -> None:
        """Test finding badge section with single marker."""
        content = """# Project Title

Some content here.

<!-- BADGES -->

More content here.
"""
        start, end = find_badge_section(content)

        # Should find the marker position
        marker_pos = content.find("<!-- BADGES -->")
        assert start == marker_pos
        assert end == marker_pos + len("<!-- BADGES -->")

    def test_find_badge_section_no_markers(self) -> None:
        """Test finding badge section when no markers exist."""
        content = """# Project Title

Some content here.

## Installation

More content here.
"""
        start, end = find_badge_section(content)

        # Should return position after first heading for insertion
        first_heading_end = content.find("\n", content.find("# Project Title"))
        assert start == first_heading_end + 1
        assert end == start  # Empty section for insertion

    def test_find_badge_section_empty_content(self) -> None:
        """Test finding badge section with empty content."""
        content = ""
        start, end = find_badge_section(content)

        assert start == 0
        assert end == 0

    def test_find_badge_section_only_heading(self) -> None:
        """Test finding badge section with only heading."""
        content = "# Project Title"
        start, end = find_badge_section(content)

        # Should position after heading
        assert start == len(content)
        assert end == start

    def test_find_badge_section_multiple_headings(self) -> None:
        """Test finding badge section with multiple headings."""
        content = """# Main Title

## Subtitle

Content here.
"""
        start, end = find_badge_section(content)

        # Should position after first heading
        first_heading_end = content.find("\n", content.find("# Main Title"))
        assert start == first_heading_end + 1
        assert end == start


class TestAtomicWriteReadme:
    """Test atomic_write_readme function."""

    def test_atomic_write_readme_success(self) -> None:
        """Test successful atomic write to README."""
        with tempfile.TemporaryDirectory() as temp_dir:
            readme_path = Path(temp_dir) / "README.md"
            original_content = "# Original Content\n\nSome text."
            readme_path.write_text(original_content)

            # Change to temp directory for test
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)

                new_content = "# Updated Content\n\nNew text."
                result = atomic_write_readme(new_content)

                assert result is True
                assert readme_path.read_text() == new_content
            finally:
                os.chdir(original_cwd)

    def test_atomic_write_readme_creates_backup(self) -> None:
        """Test that atomic write creates backup of original file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            readme_path = Path(temp_dir) / "README.md"
            backup_path = Path(temp_dir) / "README.md.backup"
            original_content = "# Original Content\n\nSome text."
            readme_path.write_text(original_content)

            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)

                new_content = "# Updated Content\n\nNew text."
                result = atomic_write_readme(new_content)

                assert result is True
                assert backup_path.exists()
                assert backup_path.read_text() == original_content
            finally:
                os.chdir(original_cwd)

    def test_atomic_write_readme_no_existing_file(self) -> None:
        """Test atomic write when README doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            readme_path = Path(temp_dir) / "README.md"

            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)

                new_content = "# New Content\n\nNew text."
                result = atomic_write_readme(new_content)

                assert result is True
                assert readme_path.exists()
                assert readme_path.read_text() == new_content
            finally:
                os.chdir(original_cwd)

    def test_atomic_write_readme_permission_error(self) -> None:
        """Test atomic write with permission error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            readme_path = Path(temp_dir) / "README.md"
            readme_path.write_text("Original content")

            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)

                # Mock tempfile.NamedTemporaryFile to raise PermissionError
                with patch("badges.updater.tempfile.NamedTemporaryFile") as mock_temp:
                    mock_temp.side_effect = PermissionError("Permission denied")

                    new_content = "# Updated Content"
                    result = atomic_write_readme(new_content, max_retries=1)

                    assert result is False
            finally:
                os.chdir(original_cwd)

    def test_atomic_write_readme_retry_delay_configuration(self) -> None:
        """Test that atomic write uses correct retry delay."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)

                # Mock to always fail to test retry delay
                with patch("badges.updater.tempfile.NamedTemporaryFile") as mock_temp:
                    mock_temp.side_effect = PermissionError("Always fail")
                    with patch("badges.updater.time.sleep") as mock_sleep:
                        new_content = "# Updated Content"
                        result = atomic_write_readme(new_content, max_retries=3)

                        assert result is False
                        # Should sleep between retries (max_retries - 1 times)
                        assert mock_sleep.call_count == 2
                        # Should sleep for 5 seconds each time
                        mock_sleep.assert_called_with(5)
            finally:
                os.chdir(original_cwd)

    def test_atomic_write_readme_max_retries_exceeded(self) -> None:
        """Test atomic write when max retries are exceeded."""
        with tempfile.TemporaryDirectory() as temp_dir:
            readme_path = Path(temp_dir) / "README.md"
            readme_path.write_text("Original content")

            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)

                # Mock tempfile.NamedTemporaryFile to always fail
                with patch("badges.updater.tempfile.NamedTemporaryFile") as mock_temp:
                    mock_temp.side_effect = PermissionError("Persistent failure")
                    with patch("badges.updater.time.sleep") as mock_sleep:  # Speed up test
                        new_content = "# Updated Content"
                        result = atomic_write_readme(new_content, max_retries=3)

                        assert result is False
                        assert mock_sleep.call_count == 2  # Should sleep max_retries - 1 times
                        # Original content should be unchanged
                        assert readme_path.read_text() == "Original content"
            finally:
                os.chdir(original_cwd)

    def test_atomic_write_readme_file_integrity_verification(self) -> None:
        """Test that atomic write verifies file integrity."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)

                # Mock Path.read_text to return different content (simulating corruption)
                original_read_text = Path.read_text

                def mock_read_text(self, *args, **kwargs):  # noqa: ANN001,ANN002,ANN003,ANN202
                    if self.name.endswith(".tmp"):
                        return "corrupted content"  # Simulate corruption
                    return original_read_text(self, *args, **kwargs)

                with patch.object(Path, "read_text", side_effect=mock_read_text):
                    new_content = "# Updated Content"
                    result = atomic_write_readme(new_content)

                    assert result is False
            finally:
                os.chdir(original_cwd)


class TestUpdateReadmeWithBadges:
    """Test update_readme_with_badges function."""

    def test_update_readme_with_badges_with_markers(self) -> None:
        """Test updating README with badges using existing markers."""
        with tempfile.TemporaryDirectory() as temp_dir:
            readme_path = Path(temp_dir) / "README.md"
            original_content = """# Project Title

Description here.

<!-- BADGES START -->
Old badge content
<!-- BADGES END -->

## Installation

More content.
"""
            readme_path.write_text(original_content)

            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)

                badges = [
                    "![Quality Gate](https://img.shields.io/badge/quality-passing-green)",
                    "![Security](https://img.shields.io/badge/security-passing-green)",
                ]

                result = update_readme_with_badges(badges)

                assert result is True

                updated_content = readme_path.read_text()
                assert "![Quality Gate]" in updated_content
                assert "![Security]" in updated_content
                assert "Old badge content" not in updated_content
                assert "<!-- BADGES START -->" in updated_content
                assert "<!-- BADGES END -->" in updated_content
            finally:
                os.chdir(original_cwd)

    def test_update_readme_with_badges_no_markers(self) -> None:
        """Test updating README with badges when no markers exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            readme_path = Path(temp_dir) / "README.md"
            original_content = """# Project Title

Description here.

## Installation

More content.
"""
            readme_path.write_text(original_content)

            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)

                badges = [
                    "![Quality Gate](https://img.shields.io/badge/quality-passing-green)",
                ]

                result = update_readme_with_badges(badges)

                assert result is True

                updated_content = readme_path.read_text()
                assert "![Quality Gate]" in updated_content
                assert "<!-- BADGES START -->" in updated_content
                assert "<!-- BADGES END -->" in updated_content
            finally:
                os.chdir(original_cwd)

    def test_update_readme_with_badges_empty_list(self) -> None:
        """Test updating README with empty badge list."""
        with tempfile.TemporaryDirectory() as temp_dir:
            readme_path = Path(temp_dir) / "README.md"
            original_content = """# Project Title

<!-- BADGES START -->
Old badges
<!-- BADGES END -->

Content.
"""
            readme_path.write_text(original_content)

            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)

                result = update_readme_with_badges([])

                assert result is True

                updated_content = readme_path.read_text()
                assert "Old badges" not in updated_content
                assert "<!-- BADGES START -->" in updated_content
                assert "<!-- BADGES END -->" in updated_content
            finally:
                os.chdir(original_cwd)

    def test_update_readme_with_badges_no_readme_file(self) -> None:
        """Test updating README when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)

                badges = ["![Test](https://img.shields.io/badge/test-passing-green)"]
                result = update_readme_with_badges(badges)

                assert result is False
            finally:
                os.chdir(original_cwd)


class TestMainWorkflowIntegration:
    """Test main README update workflow integration."""

    def test_update_readme_with_generated_badges(self) -> None:
        """Test updating README with badges from generator functions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            readme_path = Path(temp_dir) / "README.md"
            original_content = """# mypylogger

A Python logging library.

## Installation

pip install mypylogger
"""
            readme_path.write_text(original_content)

            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)

                # Generate some badge URLs (these would come from generator functions)
                badges = [
                    "![Quality Gate](https://img.shields.io/github/actions/workflow/status/user/repo/quality-gate.yml?branch=main&style=flat)",
                    "![Security](https://img.shields.io/github/actions/workflow/status/user/repo/security-driven-release.yml?branch=main&style=flat)",
                    "![Code Style](https://img.shields.io/badge/code%20style-ruff-000000?style=flat)",
                    "![Type Checked](https://img.shields.io/badge/type%20checked-mypy-blue?style=flat)",
                ]

                result = update_readme_with_badges(badges)

                assert result is True

                updated_content = readme_path.read_text()

                # Should contain all badges
                for badge in badges:
                    assert badge in updated_content

                # Should have proper badge section markers
                assert "<!-- BADGES START -->" in updated_content
                assert "<!-- BADGES END -->" in updated_content

                # Should preserve original content
                assert "# mypylogger" in updated_content
                assert "A Python logging library." in updated_content
                assert "## Installation" in updated_content

            finally:
                os.chdir(original_cwd)

    def test_update_readme_preserves_structure(self) -> None:
        """Test that README update preserves document structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            readme_path = Path(temp_dir) / "README.md"
            original_content = """# Project Title

Description paragraph.

## Section 1

Content 1.

## Section 2

Content 2.
"""
            readme_path.write_text(original_content)

            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)

                badges = ["![Test](https://img.shields.io/badge/test-passing-green)"]
                result = update_readme_with_badges(badges)

                assert result is True

                updated_content = readme_path.read_text()
                lines = updated_content.split("\n")

                # Should start with title
                assert lines[0] == "# Project Title"

                # Should have badge section after title
                badge_start_idx = None
                for i, line in enumerate(lines):
                    if "<!-- BADGES START -->" in line:
                        badge_start_idx = i
                        break

                assert badge_start_idx is not None
                assert badge_start_idx > 0  # Should be after title

                # Should preserve all original sections
                assert "Description paragraph." in updated_content
                assert "## Section 1" in updated_content
                assert "## Section 2" in updated_content

            finally:
                os.chdir(original_cwd)

    def test_update_readme_handles_complex_markdown(self) -> None:
        """Test README update with complex markdown content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            readme_path = Path(temp_dir) / "README.md"
            original_content = """# Project

<!-- BADGES START -->
Old badges here
<!-- BADGES END -->

## Features

- Feature 1
- Feature 2

```python
# Code example
logger = get_logger(__name__)
```

### Subsection

More content with **bold** and *italic* text.

| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |

> Quote block

[Link](https://example.com)
"""
            readme_path.write_text(original_content)

            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)

                badges = [
                    "![New Badge 1](https://img.shields.io/badge/new1-passing-green)",
                    "![New Badge 2](https://img.shields.io/badge/new2-passing-blue)",
                ]

                result = update_readme_with_badges(badges)

                assert result is True

                updated_content = readme_path.read_text()

                # Should replace old badges with new ones
                assert "Old badges here" not in updated_content
                assert "![New Badge 1]" in updated_content
                assert "![New Badge 2]" in updated_content

                # Should preserve all complex markdown
                assert "## Features" in updated_content
                assert "- Feature 1" in updated_content
                assert "```python" in updated_content
                assert "logger = get_logger(__name__)" in updated_content
                assert "### Subsection" in updated_content
                assert "**bold**" in updated_content
                assert "*italic*" in updated_content
                assert "| Column 1 | Column 2 |" in updated_content
                assert "> Quote block" in updated_content
                assert "[Link](https://example.com)" in updated_content

            finally:
                os.chdir(original_cwd)


class TestCIOnlyFunctionality:
    """Test CI-only badge update functionality."""

    def test_is_ci_environment_github_actions(self) -> None:
        """Test CI environment detection for GitHub Actions."""
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=False):
            assert is_ci_environment() is True

    def test_is_ci_environment_general_ci(self) -> None:
        """Test CI environment detection for general CI."""
        with patch.dict(os.environ, {"CI": "true"}, clear=False):
            assert is_ci_environment() is True

    def test_is_ci_environment_no_ci(self) -> None:
        """Test CI environment detection when not in CI."""
        # Clear all CI environment variables
        ci_vars = [
            "CI",
            "GITHUB_ACTIONS",
            "GITLAB_CI",
            "JENKINS_URL",
            "TRAVIS",
            "CIRCLECI",
            "BUILDKITE",
        ]
        with patch.dict(os.environ, dict.fromkeys(ci_vars, ""), clear=False):
            assert is_ci_environment() is False

    def test_verify_ci_test_success_github_actions_with_tests_passed(self) -> None:
        """Test CI test success verification in GitHub Actions with tests passed."""
        with patch.dict(
            os.environ, {"GITHUB_ACTIONS": "true", "TESTS_PASSED": "true"}, clear=False
        ):
            assert verify_ci_test_success() is True

    def test_verify_ci_test_success_github_actions_without_tests_passed(self) -> None:
        """Test CI test success verification in GitHub Actions without tests passed."""
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=False):
            # Remove TESTS_PASSED if it exists
            if "TESTS_PASSED" in os.environ:
                del os.environ["TESTS_PASSED"]
            assert verify_ci_test_success() is False

    def test_verify_ci_test_success_not_in_ci(self) -> None:
        """Test CI test success verification when not in CI."""
        ci_vars = [
            "CI",
            "GITHUB_ACTIONS",
            "GITLAB_CI",
            "JENKINS_URL",
            "TRAVIS",
            "CIRCLECI",
            "BUILDKITE",
        ]
        with patch.dict(os.environ, dict.fromkeys(ci_vars, ""), clear=False):
            assert verify_ci_test_success() is False

    def test_setup_git_config_success(self) -> None:
        """Test successful git configuration setup."""
        with patch("badges.updater.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = setup_git_config()
            assert result is True
            assert mock_run.call_count == 2  # Two git config commands

    def test_setup_git_config_failure(self) -> None:
        """Test git configuration setup failure."""
        with patch("badges.updater.subprocess.run") as mock_run:
            from subprocess import CalledProcessError

            mock_run.side_effect = CalledProcessError(1, "git config")
            result = setup_git_config()
            assert result is False

    def test_update_readme_with_badges_ci_only_not_in_ci(self) -> None:
        """Test CI-only badge update when not in CI environment."""
        with patch("badges.updater.verify_ci_test_success", return_value=False):
            result = update_readme_with_badges_ci_only(["![Test](https://example.com/badge)"])
            assert result is False

    def test_update_readme_with_badges_ci_only_git_config_failure(self) -> None:
        """Test CI-only badge update when git config fails."""
        with patch("badges.updater.verify_ci_test_success", return_value=True):
            with patch("badges.updater.setup_git_config", return_value=False):
                result = update_readme_with_badges_ci_only(["![Test](https://example.com/badge)"])
                assert result is False

    def test_update_readme_with_badges_ci_only_readme_update_failure(self) -> None:
        """Test CI-only badge update when README update fails."""
        with patch("badges.updater.verify_ci_test_success", return_value=True):
            with patch("badges.updater.setup_git_config", return_value=True):
                with patch("badges.updater.update_readme_with_badges", return_value=False):
                    result = update_readme_with_badges_ci_only(
                        ["![Test](https://example.com/badge)"]
                    )
                    assert result is False

    def test_update_readme_with_badges_ci_only_commit_failure(self) -> None:
        """Test CI-only badge update when commit fails."""
        with patch("badges.updater.verify_ci_test_success", return_value=True):
            with patch("badges.updater.setup_git_config", return_value=True):
                with patch("badges.updater.update_readme_with_badges", return_value=True):
                    with patch("badges.updater.commit_badge_updates", return_value=False):
                        result = update_readme_with_badges_ci_only(
                            ["![Test](https://example.com/badge)"]
                        )
                        assert result is False

    def test_update_readme_with_badges_ci_only_success(self) -> None:
        """Test successful CI-only badge update."""
        with patch("badges.updater.verify_ci_test_success", return_value=True):
            with patch("badges.updater.setup_git_config", return_value=True):
                with patch("badges.updater.update_readme_with_badges", return_value=True):
                    with patch("badges.updater.commit_badge_updates", return_value=True):
                        result = update_readme_with_badges_ci_only(
                            ["![Test](https://example.com/badge)"]
                        )
                        assert result is True
