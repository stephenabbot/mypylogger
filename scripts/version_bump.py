#!/usr/bin/env python3
"""Interactive version bump script for mypylogger.

This script provides centralized version management with automatic document updates.
It uses pyproject.toml as the single source of truth for version information.
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys

try:
    import tomli
except ImportError:
    import tomllib as tomli  # Python 3.11+


class VersionError(Exception):
    """Raised when version operations fail."""


class VersionInfo:
    """Represents semantic version information."""

    def __init__(self, version_string: str) -> None:
        """Initialize version info from string.

        Args:
            version_string: Version in format "major.minor.patch"

        Raises:
            VersionError: If version format is invalid
        """
        self.version_string = version_string
        match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version_string)
        if not match:
            raise VersionError(f"Invalid version format: {version_string}")

        self.major = int(match.group(1))
        self.minor = int(match.group(2))
        self.patch = int(match.group(3))

    def bump_major(self) -> VersionInfo:
        """Create new version with major bump."""
        return VersionInfo(f"{self.major + 1}.0.0")

    def bump_minor(self) -> VersionInfo:
        """Create new version with minor bump."""
        return VersionInfo(f"{self.major}.{self.minor + 1}.0")

    def bump_patch(self) -> VersionInfo:
        """Create new version with patch bump."""
        return VersionInfo(f"{self.major}.{self.minor}.{self.patch + 1}")

    def __str__(self) -> str:
        """Return version string."""
        return self.version_string

    def __repr__(self) -> str:
        """Return version representation."""
        return f"VersionInfo('{self.version_string}')"


class VersionManager:
    """Manages version information and updates across the project."""

    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize version manager.

        Args:
            project_root: Project root directory. If None, uses current directory.
        """
        self.project_root = project_root or Path.cwd()
        self.pyproject_path = self.project_root / "pyproject.toml"
        self.backup_path = self.project_root / ".version_backup"

        if not self.pyproject_path.exists():
            raise VersionError(f"pyproject.toml not found at {self.pyproject_path}")

    def get_current_version(self) -> VersionInfo:
        """Get current version from pyproject.toml.

        Returns:
            Current version information

        Raises:
            VersionError: If version cannot be read or parsed
        """
        try:
            with open(self.pyproject_path, "rb") as f:
                data = tomli.load(f)

            version_string = data.get("project", {}).get("version")
            if not version_string:
                raise VersionError("Version not found in pyproject.toml")

            return VersionInfo(version_string)
        except (OSError, tomli.TOMLDecodeError) as e:
            raise VersionError(f"Failed to read pyproject.toml: {e}") from e

    def update_pyproject_version(self, new_version: VersionInfo) -> None:
        """Update version in pyproject.toml.

        Args:
            new_version: New version to set

        Raises:
            VersionError: If update fails
        """
        try:
            # Read current content
            content = self.pyproject_path.read_text(encoding="utf-8")

            # Replace version line
            pattern = r'^version = "[^"]*"'
            replacement = f'version = "{new_version}"'

            new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

            if new_content == content:
                raise VersionError("Version line not found in pyproject.toml")

            # Write updated content
            self.pyproject_path.write_text(new_content, encoding="utf-8")

        except OSError as e:
            raise VersionError(f"Failed to update pyproject.toml: {e}") from e

    def get_version_files(self) -> list[tuple[Path, str, str]]:
        """Get list of files containing version references.

        Returns:
            List of tuples (file_path, pattern, description)
        """
        files = [
            # Source code files
            (
                self.project_root / "src" / "mypylogger" / "__init__.py",
                r'__version__ = "[^"]*"',
                "Package version constant",
            ),
            (
                self.project_root / "src" / "mypylogger" / "__init__.py",
                r'"""mypylogger v[0-9]+\.[0-9]+\.[0-9]+ - [^"]*"""',
                "Module docstring version",
            ),
            # Documentation files
            (
                self.project_root / "README.md",
                r"# mypylogger v[0-9]+\.[0-9]+\.[0-9]+",
                "README title",
            ),
            (
                self.project_root / "README.md",
                r"mypylogger v[0-9]+\.[0-9]+\.[0-9]+ does ONE thing",
                "README description",
            ),
            # Test runner script
            (
                self.project_root / "scripts" / "run_tests.sh",
                r"# Master test script for mypylogger v[0-9]+\.[0-9]+\.[0-9]+",
                "Test script comment",
            ),
            (
                self.project_root / "scripts" / "run_tests.sh",
                r"echo \"🧪 mypylogger v[0-9]+\.[0-9]+\.[0-9]+ - Master Test Runner\"",
                "Test script output",
            ),
            # Test files with version assertions - tests/unit/test_core.py
            (
                self.project_root / "tests" / "unit" / "test_core.py",
                r'assert __version__ == "[^"]*"',
                "Test version assertion (__version__) - test_version_available",
            ),
            (
                self.project_root / "tests" / "unit" / "test_core.py",
                r'assert get_version\(\) == "[^"]*"',
                "Test version assertion (get_version()) - test_version_available",
            ),
            (
                self.project_root / "tests" / "unit" / "test_core.py",
                r'assert "mypylogger v[0-9]+\.[0-9]+\.[0-9]+" in mypylogger\.__doc__',
                "Test module docstring version check - test_module_docstring",
            ),
            (
                self.project_root / "tests" / "unit" / "test_core.py",
                r'assert __version__ == "[^"]*"',
                "Test version string literal assertion - test_version_is_string_literal",
            ),
            # Test files with version assertions - tests/unit/test_public_api.py
            (
                self.project_root / "tests" / "unit" / "test_public_api.py",
                r'assert version == "[^"]*"',
                "Test version assertion (version variable) - test_get_version_returns_version",
            ),
            (
                self.project_root / "tests" / "unit" / "test_public_api.py",
                r'assert mypylogger\.__version__ == "[^"]*"',
                "Test module version assertion - test_version_attribute",
            ),
            # Test files with version references - tests/performance/__init__.py
            (
                self.project_root / "tests" / "performance" / "__init__.py",
                r"# Performance tests for mypylogger v[0-9]+\.[0-9]+\.[0-9]+",
                "Performance test module comment",
            ),
            # Test files with version references - tests/performance/test_benchmarks.py
            (
                self.project_root / "tests" / "performance" / "test_benchmarks.py",
                r'"""Performance benchmarks for mypylogger v[0-9]+\.[0-9]+\.[0-9]+\.',
                "Performance test docstring",
            ),
        ]

        # Add steering documents
        steering_files = [
            ".kiro/steering/tech.md",
            ".kiro/steering/development-workflow.md",
            ".kiro/steering/feature-control.md",
            ".kiro/steering/product.md",
        ]

        for steering_file in steering_files:
            file_path = self.project_root / steering_file
            files.append(
                (
                    file_path,
                    r"mypylogger v[0-9]+\.[0-9]+\.[0-9]+",
                    f"Steering document: {steering_file}",
                )
            )

        # Add spec documents
        spec_dirs = [
            ".kiro/specs/phase-1-project-setup",
            ".kiro/specs/phase-2-core-functionality",
            ".kiro/specs/phase-3-github-cicd",
            ".kiro/specs/phase-4-documentation",
            ".kiro/specs/phase-5-project-badges",
            ".kiro/specs/phase-7-pypi-publishing",
        ]

        for spec_dir in spec_dirs:
            for spec_file in ["requirements.md", "design.md", "tasks.md"]:
                file_path = self.project_root / spec_dir / spec_file
                files.append(
                    (
                        file_path,
                        r"mypylogger v[0-9]+\.[0-9]+\.[0-9]+",
                        f"Spec document: {spec_dir}/{spec_file}",
                    )
                )

        # Add other documentation files
        doc_files = ["docs/quality-config.yml", "docs/custom-dict.txt", "docs/README.md"]

        for doc_file in doc_files:
            file_path = self.project_root / doc_file
            files.append(
                (file_path, r"mypylogger v[0-9]+\.[0-9]+\.[0-9]+", f"Documentation: {doc_file}")
            )

        # Add script files
        script_files = [
            "scripts/security_check.sh",
            "scripts/validate_performance.py",
            "scripts/ci_security_check.sh",
            "scripts/validate_documentation.py",
        ]

        for script_file in script_files:
            file_path = self.project_root / script_file
            files.append(
                (file_path, r"mypylogger v[0-9]+\.[0-9]+\.[0-9]+", f"Script: {script_file}")
            )

        return files

    def update_version_files(
        self, old_version: VersionInfo, new_version: VersionInfo
    ) -> list[Path]:
        """Update version references in all project files.

        Args:
            old_version: Current version
            new_version: New version to set

        Returns:
            List of files that were updated

        Raises:
            VersionError: If any file update fails
        """
        updated_files = []

        for file_path, pattern, description in self.get_version_files():
            if not file_path.exists():
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
                new_content = content

                # Apply specific pattern replacements
                if "assert __version__ ==" in pattern:
                    # Test file __version__ assertions
                    new_content = re.sub(pattern, f'assert __version__ == "{new_version}"', content)
                elif "assert get_version\\(\\)" in pattern:
                    # Test file get_version() assertions
                    new_content = re.sub(
                        pattern, f'assert get_version() == "{new_version}"', content
                    )
                elif "assert version ==" in pattern:
                    # Test file version variable assertions
                    new_content = re.sub(pattern, f'assert version == "{new_version}"', content)
                elif "assert mypylogger\\.__version__ ==" in pattern:
                    # Test file module version assertions
                    new_content = re.sub(
                        pattern, f'assert mypylogger.__version__ == "{new_version}"', content
                    )
                elif 'assert "mypylogger v' in pattern and "__doc__" in pattern:
                    # Test file docstring version checks (test_module_docstring)
                    new_content = re.sub(
                        r'assert "mypylogger v[0-9]+\.[0-9]+\.[0-9]+" in mypylogger\.__doc__',
                        f'assert "mypylogger v{new_version}" in mypylogger.__doc__',
                        content,
                    )
                elif "__version__" in pattern and "assert" not in pattern:
                    # Source code __version__ constant
                    new_content = re.sub(pattern, f'__version__ = "{new_version}"', content)
                elif "# mypylogger v" in pattern:
                    new_content = re.sub(pattern, f"# mypylogger v{new_version}", content)
                elif "# Performance tests for mypylogger v" in pattern:
                    new_content = re.sub(
                        pattern, f"# Performance tests for mypylogger v{new_version}", content
                    )
                elif "Master test script" in pattern:
                    new_content = re.sub(
                        pattern, f"# Master test script for mypylogger v{new_version}", content
                    )
                elif "Master Test Runner" in pattern:
                    new_content = re.sub(
                        pattern,
                        f'echo "🧪 mypylogger v{new_version} - Master Test Runner"',
                        content,
                    )
                elif '"""mypylogger v' in pattern:
                    new_content = re.sub(
                        r'"""mypylogger v[0-9]+\.[0-9]+\.[0-9]+',
                        f'"""mypylogger v{new_version}',
                        content,
                    )
                elif '"""Performance benchmarks for mypylogger v' in pattern:
                    new_content = re.sub(
                        r'"""Performance benchmarks for mypylogger v[0-9]+\.[0-9]+\.[0-9]+',
                        f'"""Performance benchmarks for mypylogger v{new_version}',
                        content,
                    )
                elif '"mypylogger v' in pattern and "docstring" in description:
                    # Test file docstring version checks
                    new_content = re.sub(
                        r'"mypylogger v[0-9]+\.[0-9]+\.[0-9]+"',
                        f'"mypylogger v{new_version}"',
                        content,
                    )
                else:
                    # Generic mypylogger version replacement
                    new_content = re.sub(
                        r"mypylogger v[0-9]+\.[0-9]+\.[0-9]+", f"mypylogger v{new_version}", content
                    )

                if new_content != content:
                    file_path.write_text(new_content, encoding="utf-8")
                    updated_files.append(file_path)
                    print(
                        f"  ✓ Updated {description} in {file_path.relative_to(self.project_root)}"
                    )

            except OSError as e:
                raise VersionError(f"Failed to update {file_path}: {e}") from e

        return updated_files

    def validate_semantic_version(self, version_string: str) -> bool:
        """Validate semantic version format.

        Args:
            version_string: Version string to validate

        Returns:
            True if valid semantic version
        """
        try:
            VersionInfo(version_string)
            return True
        except VersionError:
            return False

    def create_backup(self) -> None:
        """Create backup of current project state.

        Raises:
            VersionError: If backup creation fails
        """
        try:
            # Create backup directory
            self.backup_path.mkdir(exist_ok=True)

            # Backup pyproject.toml
            backup_pyproject = self.backup_path / "pyproject.toml"
            backup_pyproject.write_text(
                self.pyproject_path.read_text(encoding="utf-8"), encoding="utf-8"
            )

            # Backup version files
            for file_path, _, description in self.get_version_files():
                if file_path.exists():
                    backup_file = self.backup_path / file_path.name
                    backup_file.write_text(file_path.read_text(encoding="utf-8"), encoding="utf-8")

        except OSError as e:
            raise VersionError(f"Failed to create backup: {e}") from e

    def restore_backup(self) -> None:
        """Restore project state from backup.

        Raises:
            VersionError: If restore fails
        """
        if not self.backup_path.exists():
            raise VersionError("No backup found to restore")

        try:
            # Restore pyproject.toml
            backup_pyproject = self.backup_path / "pyproject.toml"
            if backup_pyproject.exists():
                self.pyproject_path.write_text(
                    backup_pyproject.read_text(encoding="utf-8"), encoding="utf-8"
                )

            # Restore version files
            for file_path, _, description in self.get_version_files():
                backup_file = self.backup_path / file_path.name
                if backup_file.exists() and file_path.exists():
                    file_path.write_text(backup_file.read_text(encoding="utf-8"), encoding="utf-8")

        except OSError as e:
            raise VersionError(f"Failed to restore backup: {e}") from e

    def cleanup_backup(self) -> None:
        """Clean up backup files.

        Raises:
            VersionError: If cleanup fails
        """
        import shutil

        # Clean up both possible backup directory names
        backup_paths = [
            self.backup_path,  # .version_backup
            self.project_root / "version_backup",  # version_backup (without dot)
        ]

        cleanup_errors = []

        for backup_path in backup_paths:
            if backup_path.exists():
                try:
                    shutil.rmtree(backup_path)
                except OSError as e:
                    cleanup_errors.append(f"Failed to cleanup {backup_path}: {e}")

        if cleanup_errors:
            raise VersionError("; ".join(cleanup_errors))

    def validate_version_consistency(self) -> tuple[bool, list[str]]:
        """Validate that all version references are consistent.

        Returns:
            Tuple of (is_consistent, list_of_inconsistencies)
        """
        current_version = self.get_current_version()
        inconsistencies = []

        for file_path, pattern, description in self.get_version_files():
            if not file_path.exists():
                continue

            try:
                content = file_path.read_text(encoding="utf-8")

                # Find version references in the file
                version_matches = re.findall(r"v?([0-9]+\.[0-9]+\.[0-9]+)", content)

                for match in version_matches:
                    if match != str(current_version):
                        inconsistencies.append(
                            f"{file_path.relative_to(self.project_root)}: "
                            f"found v{match}, expected v{current_version}"
                        )
                        break  # Only report first inconsistency per file

            except OSError:
                # Skip files that can't be read
                continue

        return len(inconsistencies) == 0, inconsistencies


class GitManager:
    """Manages Git operations for version bumps."""

    def __init__(self, project_root: Path) -> None:
        """Initialize Git manager.

        Args:
            project_root: Project root directory
        """
        self.project_root = project_root

    def is_clean_working_directory(self) -> bool:
        """Check if working directory is clean.

        Returns:
            True if working directory is clean
        """
        try:
            result = subprocess.run(
                ["git", "--no-pager", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return len(result.stdout.strip()) == 0
        except subprocess.CalledProcessError:
            return False

    def validate_git_repository(self) -> bool:
        """Validate that we're in a Git repository.

        Returns:
            True if in a valid Git repository
        """
        try:
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.project_root,
                capture_output=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def get_current_branch(self) -> str:
        """Get current Git branch name.

        Returns:
            Current branch name

        Raises:
            VersionError: If unable to get branch name
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise VersionError(f"Failed to get current branch: {e}") from e

    def validate_remote_connection(self) -> bool:
        """Validate connection to remote repository.

        Returns:
            True if remote is accessible
        """
        try:
            subprocess.run(
                ["git", "ls-remote", "--exit-code", "origin"],
                cwd=self.project_root,
                capture_output=True,
                check=True,
                timeout=10,  # 10 second timeout
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False

    def stage_files(self, files: list[Path]) -> None:
        """Stage files for commit.

        Args:
            files: List of files to stage

        Raises:
            VersionError: If staging fails
        """
        try:
            # Stage all modified files
            subprocess.run(["git", "add", "."], cwd=self.project_root, check=True)
        except subprocess.CalledProcessError as e:
            raise VersionError(f"Failed to stage files: {e}") from e

    def commit_and_push(
        self, old_version: VersionInfo, new_version: VersionInfo, comment: str
    ) -> str:
        """Commit changes and push to remote.

        Args:
            old_version: Previous version
            new_version: New version
            comment: User comment for the version bump

        Returns:
            Commit hash

        Raises:
            VersionError: If commit or push fails
        """
        try:
            # Create commit message
            commit_message = f"feat: bump version {old_version} → {new_version}"
            if comment:
                commit_message += f"\n\n{comment}"

            # Commit changes
            result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )

            # Get commit hash
            commit_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            commit_hash = commit_result.stdout.strip()

            # Push to remote
            subprocess.run(["git", "push", "origin", "main"], cwd=self.project_root, check=True)

            return commit_hash

        except subprocess.CalledProcessError as e:
            raise VersionError(f"Failed to commit and push: {e}") from e


def get_user_input(prompt: str, default: str | None = None) -> str:
    """Get user input with optional default.

    Args:
        prompt: Prompt to display
        default: Default value if user presses enter

    Returns:
        User input or default value
    """
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "

    response = input(full_prompt).strip()
    return response if response else (default or "")


def main() -> None:
    """Main version bump workflow."""
    print("🔄 mypylogger Version Bump Tool")
    print("=" * 40)

    try:
        # Initialize managers
        version_manager = VersionManager()
        git_manager = GitManager(version_manager.project_root)

        # Validate Git repository
        if not git_manager.validate_git_repository():
            print("❌ Not in a Git repository. Please run from project root.")
            sys.exit(1)

        # Check current branch
        current_branch = git_manager.get_current_branch()
        if current_branch != "main":
            print(
                f"⚠️  Currently on branch '{current_branch}'. Version bumps should be done on 'main' branch."
            )
            confirm_branch = get_user_input("Continue anyway? (y/N)", "n").lower()
            if confirm_branch not in ("y", "yes"):
                print("❌ Version bump cancelled. Switch to 'main' branch first.")
                sys.exit(1)

        # Check Git status
        if not git_manager.is_clean_working_directory():
            print("❌ Working directory is not clean. Please commit or stash changes first.")
            sys.exit(1)

        # Check remote connection
        if not git_manager.validate_remote_connection():
            print("⚠️  Cannot connect to remote repository. Push may fail.")
            confirm_remote = get_user_input(
                "Continue without remote validation? (y/N)", "n"
            ).lower()
            if confirm_remote not in ("y", "yes"):
                print("❌ Version bump cancelled. Check remote connection.")
                sys.exit(1)

        # Get current version
        current_version = version_manager.get_current_version()
        print(f"📋 Current version: {current_version}")
        print()

        # Show version bump options
        print("Version bump options:")
        print(f"  1. Patch: {current_version.bump_patch()} (bug fixes)")
        print(f"  2. Minor: {current_version.bump_minor()} (new features)")
        print(f"  3. Major: {current_version.bump_major()} (breaking changes)")
        print("  4. Custom version")
        print()

        # Get user choice
        choice = get_user_input("Select version bump type (1-4)", "1")

        if choice == "1":
            new_version = current_version.bump_patch()
        elif choice == "2":
            new_version = current_version.bump_minor()
        elif choice == "3":
            new_version = current_version.bump_major()
        elif choice == "4":
            while True:
                version_input = get_user_input("Enter custom version (e.g., 1.2.3)")
                if version_manager.validate_semantic_version(version_input):
                    new_version = VersionInfo(version_input)
                    break
                print("❌ Invalid version format. Please use semantic versioning (e.g., 1.2.3)")
        else:
            print("❌ Invalid choice. Exiting.")
            sys.exit(1)

        print(f"📈 New version: {new_version}")
        print()

        # Get version bump comment
        comment = get_user_input("Enter version bump comment (optional)")

        # Confirm the change
        print()
        print("📝 Version bump summary:")
        print(f"  Current: {current_version}")
        print(f"  New:     {new_version}")
        if comment:
            print(f"  Comment: {comment}")
        print()

        confirm = get_user_input("Proceed with version bump? (y/N)", "n").lower()
        if confirm not in ("y", "yes"):
            print("❌ Version bump cancelled.")
            sys.exit(0)

        print()
        print("🚀 Starting version bump...")

        # Create backup
        print("  💾 Creating backup...")
        version_manager.create_backup()

        try:
            # Update pyproject.toml
            print("  📝 Updating pyproject.toml...")
            version_manager.update_pyproject_version(new_version)

            # Update all version files
            print("  📝 Updating version references...")
            updated_files = version_manager.update_version_files(current_version, new_version)

            if not updated_files:
                print("  ⚠️  No files were updated")

            # Stage files
            print("  📦 Staging changes...")
            git_manager.stage_files(updated_files)

            # Commit and push
            print("  🔄 Committing and pushing...")
            commit_hash = git_manager.commit_and_push(current_version, new_version, comment)

        except Exception as e:
            print(f"  ❌ Error during version bump: {e}")
            print("  🔄 Restoring backup...")
            try:
                version_manager.restore_backup()
                print("  ✅ Backup restored successfully")
            except VersionError as restore_error:
                print(f"  ❌ Failed to restore backup: {restore_error}")
            raise
        finally:
            # Always clean up backup directory, regardless of success or failure
            try:
                version_manager.cleanup_backup()
                print("  🧹 Backup directory cleaned up")
            except VersionError as cleanup_error:
                print(f"  ⚠️  Failed to cleanup backup: {cleanup_error}")

        print()
        print("✅ Version bump completed successfully!")
        print(f"  📋 Version: {current_version} → {new_version}")
        print(f"  📦 Commit: {commit_hash[:8]}")
        print(f"  📁 Files updated: {len(updated_files)}")

    except VersionError as e:
        print(f"❌ Version bump failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n❌ Version bump cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
