"""Tests for version management system."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

# Import the version management modules
import sys
import tempfile
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from version_bump import GitManager, VersionError, VersionInfo, VersionManager


class TestVersionInfo:
    """Test VersionInfo class."""

    def test_valid_version_parsing(self) -> None:
        """Test parsing valid semantic versions."""
        version = VersionInfo("1.2.3")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert str(version) == "1.2.3"

    def test_invalid_version_parsing(self) -> None:
        """Test parsing invalid versions raises error."""
        with pytest.raises(VersionError, match="Invalid version format"):
            VersionInfo("invalid")

        with pytest.raises(VersionError, match="Invalid version format"):
            VersionInfo("1.2")

        with pytest.raises(VersionError, match="Invalid version format"):
            VersionInfo("1.2.3.4")

    def test_version_bumps(self) -> None:
        """Test version bump operations."""
        version = VersionInfo("1.2.3")

        major_bump = version.bump_major()
        assert str(major_bump) == "2.0.0"

        minor_bump = version.bump_minor()
        assert str(minor_bump) == "1.3.0"

        patch_bump = version.bump_patch()
        assert str(patch_bump) == "1.2.4"

    def test_version_representation(self) -> None:
        """Test version string representation."""
        version = VersionInfo("0.1.0")
        assert repr(version) == "VersionInfo('0.1.0')"


class TestVersionManager:
    """Test VersionManager class."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.pyproject_path = self.temp_dir / "pyproject.toml"

        # Create minimal pyproject.toml
        self.pyproject_path.write_text(
            """
[project]
name = "test-package"
version = "1.0.0"
description = "Test package"
""",
            encoding="utf-8",
        )

    def teardown_method(self) -> None:
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_initialization(self) -> None:
        """Test VersionManager initialization."""
        manager = VersionManager(self.temp_dir)
        assert manager.project_root == self.temp_dir
        assert manager.pyproject_path == self.pyproject_path

    def test_initialization_no_pyproject(self) -> None:
        """Test initialization fails without pyproject.toml."""
        empty_dir = self.temp_dir / "empty"
        empty_dir.mkdir()

        with pytest.raises(VersionError, match=r"pyproject\.toml not found"):
            VersionManager(empty_dir)

    def test_get_current_version(self) -> None:
        """Test getting current version from pyproject.toml."""
        manager = VersionManager(self.temp_dir)
        version = manager.get_current_version()
        assert str(version) == "1.0.0"

    def test_get_current_version_missing(self) -> None:
        """Test error when version is missing from pyproject.toml."""
        # Create pyproject.toml without version
        self.pyproject_path.write_text(
            """
[project]
name = "test-package"
description = "Test package"
""",
            encoding="utf-8",
        )

        manager = VersionManager(self.temp_dir)
        with pytest.raises(VersionError, match="Version not found"):
            manager.get_current_version()

    def test_update_pyproject_version(self) -> None:
        """Test updating version in pyproject.toml."""
        manager = VersionManager(self.temp_dir)
        new_version = VersionInfo("2.0.0")

        manager.update_pyproject_version(new_version)

        # Verify update
        content = self.pyproject_path.read_text(encoding="utf-8")
        assert 'version = "2.0.0"' in content
        assert 'version = "1.0.0"' not in content

    def test_validate_semantic_version(self) -> None:
        """Test semantic version validation."""
        manager = VersionManager(self.temp_dir)

        assert manager.validate_semantic_version("1.2.3") is True
        assert manager.validate_semantic_version("0.0.1") is True
        assert manager.validate_semantic_version("invalid") is False
        assert manager.validate_semantic_version("1.2") is False

    def test_backup_and_restore(self) -> None:
        """Test backup and restore functionality."""
        manager = VersionManager(self.temp_dir)

        # Create a test file to backup
        test_file = self.temp_dir / "src" / "test" / "__init__.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text('__version__ = "1.0.0"', encoding="utf-8")

        # Create backup
        manager.create_backup()
        assert manager.backup_path.exists()

        # Modify files
        manager.update_pyproject_version(VersionInfo("2.0.0"))
        test_file.write_text('__version__ = "2.0.0"', encoding="utf-8")

        # Restore backup
        manager.restore_backup()

        # Verify restoration
        version = manager.get_current_version()
        assert str(version) == "1.0.0"

        # Cleanup
        manager.cleanup_backup()
        assert not manager.backup_path.exists()

    def test_get_version_files(self) -> None:
        """Test getting list of version files."""
        manager = VersionManager(self.temp_dir)
        files = manager.get_version_files()

        # Should return a list of tuples
        assert isinstance(files, list)
        assert len(files) > 0

        # Each item should be a tuple with 3 elements
        for file_path, pattern, description in files:
            assert isinstance(file_path, Path)
            assert isinstance(pattern, str)
            assert isinstance(description, str)

    def test_update_version_files(self) -> None:
        """Test updating version references in files."""
        manager = VersionManager(self.temp_dir)

        # Create test files with version references
        init_file = self.temp_dir / "src" / "mypylogger" / "__init__.py"
        init_file.parent.mkdir(parents=True)
        init_file.write_text(
            '''"""mypylogger v1.0.0 - Test package."""
__version__ = "1.0.0"
''',
            encoding="utf-8",
        )

        readme_file = self.temp_dir / "README.md"
        readme_file.write_text(
            """# mypylogger v1.0.0

mypylogger v1.0.0 does ONE thing exceptionally well.
""",
            encoding="utf-8",
        )

        # Update versions
        old_version = VersionInfo("1.0.0")
        new_version = VersionInfo("2.0.0")
        updated_files = manager.update_version_files(old_version, new_version)

        # Verify updates
        assert len(updated_files) > 0

        init_content = init_file.read_text(encoding="utf-8")
        assert "mypylogger v2.0.0" in init_content
        assert '__version__ = "2.0.0"' in init_content

        readme_content = readme_file.read_text(encoding="utf-8")
        assert "mypylogger v2.0.0" in readme_content

    def test_validate_version_consistency(self) -> None:
        """Test version consistency validation."""
        manager = VersionManager(self.temp_dir)

        # Create files with consistent versions
        init_file = self.temp_dir / "src" / "mypylogger" / "__init__.py"
        init_file.parent.mkdir(parents=True)
        init_file.write_text('__version__ = "1.0.0"', encoding="utf-8")

        is_consistent, inconsistencies = manager.validate_version_consistency()
        assert is_consistent is True
        assert len(inconsistencies) == 0

        # Create inconsistent version
        init_file.write_text('__version__ = "2.0.0"', encoding="utf-8")

        is_consistent, inconsistencies = manager.validate_version_consistency()
        assert is_consistent is False
        assert len(inconsistencies) > 0


class TestGitManager:
    """Test GitManager class."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self) -> None:
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_initialization(self) -> None:
        """Test GitManager initialization."""
        manager = GitManager(self.temp_dir)
        assert manager.project_root == self.temp_dir

    @patch("subprocess.run")
    def test_validate_git_repository(self, mock_run: Mock) -> None:
        """Test Git repository validation."""
        manager = GitManager(self.temp_dir)

        # Test valid repository
        mock_run.return_value = Mock(returncode=0)
        assert manager.validate_git_repository() is True

        # Test invalid repository
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")
        assert manager.validate_git_repository() is False

    @patch("subprocess.run")
    def test_is_clean_working_directory(self, mock_run: Mock) -> None:
        """Test working directory status check."""
        manager = GitManager(self.temp_dir)

        # Test clean directory
        mock_run.return_value = Mock(stdout="", returncode=0)
        assert manager.is_clean_working_directory() is True

        # Test dirty directory
        mock_run.return_value = Mock(stdout="M file.txt\n", returncode=0)
        assert manager.is_clean_working_directory() is False

        # Test Git error
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")
        assert manager.is_clean_working_directory() is False

    @patch("subprocess.run")
    def test_get_current_branch(self, mock_run: Mock) -> None:
        """Test getting current branch name."""
        manager = GitManager(self.temp_dir)

        # Test successful branch retrieval
        mock_run.return_value = Mock(stdout="main\n", returncode=0)
        assert manager.get_current_branch() == "main"

        # Test Git error
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")
        with pytest.raises(VersionError, match="Failed to get current branch"):
            manager.get_current_branch()

    @patch("subprocess.run")
    def test_validate_remote_connection(self, mock_run: Mock) -> None:
        """Test remote connection validation."""
        manager = GitManager(self.temp_dir)

        # Test successful connection
        mock_run.return_value = Mock(returncode=0)
        assert manager.validate_remote_connection() is True

        # Test connection failure
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")
        assert manager.validate_remote_connection() is False

        # Test timeout
        mock_run.side_effect = subprocess.TimeoutExpired("git", 10)
        assert manager.validate_remote_connection() is False

    @patch("subprocess.run")
    def test_stage_files(self, mock_run: Mock) -> None:
        """Test file staging."""
        manager = GitManager(self.temp_dir)

        # Test successful staging
        mock_run.return_value = Mock(returncode=0)
        manager.stage_files([Path("file1.txt"), Path("file2.txt")])
        mock_run.assert_called_once()

        # Test staging failure
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")
        with pytest.raises(VersionError, match="Failed to stage files"):
            manager.stage_files([Path("file1.txt")])

    @patch("subprocess.run")
    def test_commit_and_push(self, mock_run: Mock) -> None:
        """Test commit and push operations."""
        manager = GitManager(self.temp_dir)

        # Mock successful operations
        mock_run.side_effect = [
            Mock(returncode=0),  # commit
            Mock(stdout="abc123\n", returncode=0),  # get commit hash
            Mock(returncode=0),  # push
        ]

        old_version = VersionInfo("1.0.0")
        new_version = VersionInfo("2.0.0")
        comment = "Test version bump"

        commit_hash = manager.commit_and_push(old_version, new_version, comment)
        assert commit_hash == "abc123"
        assert mock_run.call_count == 3

        # Test commit failure
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")
        with pytest.raises(VersionError, match="Failed to commit and push"):
            manager.commit_and_push(old_version, new_version, comment)


class TestIntegration:
    """Integration tests for version management workflow."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.setup_test_project()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def setup_test_project(self) -> None:
        """Set up a minimal test project structure."""
        # Create pyproject.toml
        pyproject_path = self.temp_dir / "pyproject.toml"
        pyproject_path.write_text(
            """
[project]
name = "test-package"
version = "1.0.0"
description = "Test package"
""",
            encoding="utf-8",
        )

        # Create source files
        init_file = self.temp_dir / "src" / "mypylogger" / "__init__.py"
        init_file.parent.mkdir(parents=True)
        init_file.write_text(
            '''"""mypylogger v1.0.0 - Test package."""
__version__ = "1.0.0"
''',
            encoding="utf-8",
        )

        # Create README
        readme_file = self.temp_dir / "README.md"
        readme_file.write_text(
            """# mypylogger v1.0.0

mypylogger v1.0.0 does ONE thing exceptionally well.
""",
            encoding="utf-8",
        )

    def test_complete_version_bump_workflow(self) -> None:
        """Test complete version bump workflow without Git operations."""
        version_manager = VersionManager(self.temp_dir)

        # Get current version
        current_version = version_manager.get_current_version()
        assert str(current_version) == "1.0.0"

        # Create backup
        version_manager.create_backup()
        assert version_manager.backup_path.exists()

        # Update to new version
        new_version = VersionInfo("2.0.0")
        version_manager.update_pyproject_version(new_version)
        updated_files = version_manager.update_version_files(current_version, new_version)

        # Verify updates
        assert len(updated_files) > 0

        updated_version = version_manager.get_current_version()
        assert str(updated_version) == "2.0.0"

        # Test rollback
        version_manager.restore_backup()
        restored_version = version_manager.get_current_version()
        assert str(restored_version) == "1.0.0"

        # Cleanup
        version_manager.cleanup_backup()
        assert not version_manager.backup_path.exists()

    def test_error_handling_and_rollback(self) -> None:
        """Test error handling and rollback scenarios."""
        version_manager = VersionManager(self.temp_dir)

        # Create backup
        version_manager.create_backup()

        # Simulate partial failure by making a file read-only
        init_file = self.temp_dir / "src" / "mypylogger" / "__init__.py"
        original_mode = init_file.stat().st_mode

        try:
            # Make file read-only to simulate failure
            init_file.chmod(0o444)

            current_version = version_manager.get_current_version()
            new_version = VersionInfo("2.0.0")

            # This should fail due to read-only file
            with pytest.raises(VersionError):
                version_manager.update_version_files(current_version, new_version)

            # Restore file permissions before restore
            init_file.chmod(original_mode)

            # Restore backup should work
            version_manager.restore_backup()
            restored_version = version_manager.get_current_version()
            assert str(restored_version) == "1.0.0"

        finally:
            # Ensure file permissions are restored
            if init_file.exists():
                init_file.chmod(original_mode)
            version_manager.cleanup_backup()

    @patch("subprocess.run")
    def test_git_integration_workflow(self, mock_run: Mock) -> None:
        """Test Git integration workflow."""
        git_manager = GitManager(self.temp_dir)

        # Mock Git operations
        mock_run.side_effect = [
            Mock(returncode=0),  # validate repository
            Mock(stdout="main\n", returncode=0),  # get branch
            Mock(stdout="", returncode=0),  # check status
            Mock(returncode=0),  # validate remote
            Mock(returncode=0),  # stage files
            Mock(returncode=0),  # commit
            Mock(stdout="abc123\n", returncode=0),  # get commit hash
            Mock(returncode=0),  # push
        ]

        # Test Git validation
        assert git_manager.validate_git_repository() is True
        assert git_manager.get_current_branch() == "main"
        assert git_manager.is_clean_working_directory() is True
        assert git_manager.validate_remote_connection() is True

        # Test commit and push
        old_version = VersionInfo("1.0.0")
        new_version = VersionInfo("2.0.0")

        git_manager.stage_files([Path("file1.txt")])
        commit_hash = git_manager.commit_and_push(old_version, new_version, "Test bump")

        assert commit_hash == "abc123"
        assert mock_run.call_count == 8
