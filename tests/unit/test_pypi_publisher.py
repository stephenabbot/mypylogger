"""Unit tests for PyPI publisher."""

from __future__ import annotations

from pathlib import Path

# Import the modules we're testing
import sys
import tempfile
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from publish_with_error_handling import PyPIPublisher
from publishing_error_handler import ErrorCategory, ErrorSeverity, PublishingError


class TestPyPIPublisher:
    """Test PyPIPublisher class."""

    def test_publisher_initialization(self) -> None:
        """Test PyPI publisher initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir)
            log_file = package_dir / "test.log"

            publisher = PyPIPublisher(
                package_dir=package_dir,
                dry_run=True,
                log_file=log_file,
            )

            assert publisher.package_dir == package_dir
            assert publisher.dry_run is True
            assert publisher.error_handler.log_file == log_file
            assert publisher.build_dir is None

    def test_validate_environment_missing_files(self) -> None:
        """Test environment validation with missing required files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir)
            publisher = PyPIPublisher(package_dir=package_dir)

            # No required files exist
            result = publisher.validate_environment()

            assert result is False
            assert len(publisher.error_handler.errors) > 0

            # Check that we have configuration errors
            config_errors = [
                e
                for e in publisher.error_handler.errors
                if e.category == ErrorCategory.CONFIGURATION
            ]
            assert len(config_errors) > 0

    def test_validate_environment_success(self) -> None:
        """Test successful environment validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir)

            # Create required files
            (package_dir / "pyproject.toml").write_text("[project]\nname = 'test'\n")
            (package_dir / "README.md").write_text("# Test Package\n")
            (package_dir / "src").mkdir()

            publisher = PyPIPublisher(package_dir=package_dir)

            with patch.object(publisher.error_handler, "run_command_with_retry") as mock_run:
                mock_run.return_value = (True, None)  # UV command succeeds

                result = publisher.validate_environment()

                assert result is True
                assert len(publisher.error_handler.errors) == 0

    @patch("subprocess.run")
    def test_run_quality_gates_success(self, mock_run: Mock) -> None:
        """Test successful quality gates execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir)
            scripts_dir = package_dir / "scripts"
            scripts_dir.mkdir()

            # Create test script
            test_script = scripts_dir / "run_tests.sh"
            test_script.write_text("#!/bin/bash\nexit 0\n")
            test_script.chmod(0o755)

            publisher = PyPIPublisher(package_dir=package_dir)

            # Mock successful command execution
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "All tests passed"
            mock_run.return_value.stderr = ""

            result = publisher.run_quality_gates()

            assert result is True
            assert len(publisher.error_handler.errors) == 0

    def test_run_quality_gates_no_script(self) -> None:
        """Test quality gates when test script doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir)
            publisher = PyPIPublisher(package_dir=package_dir)

            result = publisher.run_quality_gates()

            # Should succeed with warning when no script exists
            assert result is True
            assert len(publisher.error_handler.errors) == 0

    @patch("subprocess.run")
    def test_validate_package_metadata_success(self, mock_run: Mock) -> None:
        """Test successful package metadata validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir)
            scripts_dir = package_dir / "scripts"
            scripts_dir.mkdir()

            # Create validation script
            validation_script = scripts_dir / "validate_package.py"
            validation_script.write_text("#!/usr/bin/env python3\nprint('Validation passed')\n")

            publisher = PyPIPublisher(package_dir=package_dir)

            # Mock successful command execution
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Validation passed"
            mock_run.return_value.stderr = ""

            result = publisher.validate_package_metadata()

            assert result is True
            assert len(publisher.error_handler.errors) == 0

    def test_validate_package_metadata_no_script(self) -> None:
        """Test package metadata validation when script doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir)
            publisher = PyPIPublisher(package_dir=package_dir)

            result = publisher.validate_package_metadata()

            # Should succeed with warning when no script exists
            assert result is True
            assert len(publisher.error_handler.errors) == 0

    @patch("subprocess.run")
    def test_build_package_success(self, mock_run: Mock) -> None:
        """Test successful package building."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir)
            publisher = PyPIPublisher(package_dir=package_dir)

            # Mock successful build commands
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Build successful"
            mock_run.return_value.stderr = ""

            with patch("tempfile.mkdtemp") as mock_mkdtemp:
                build_dir = Path(temp_dir) / "build"
                build_dir.mkdir()
                mock_mkdtemp.return_value = str(build_dir)

                # Create mock distribution files
                (build_dir / "test-1.0.0.tar.gz").touch()
                (build_dir / "test-1.0.0-py3-none-any.whl").touch()

                result = publisher.build_package()

                assert result is True
                assert publisher.build_dir == build_dir
                assert len(publisher.error_handler.errors) == 0

    @patch("subprocess.run")
    def test_build_package_no_files_created(self, mock_run: Mock) -> None:
        """Test package building when no distribution files are created."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir)
            publisher = PyPIPublisher(package_dir=package_dir)

            # Mock successful build commands but no files created
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Build successful"
            mock_run.return_value.stderr = ""

            with patch("tempfile.mkdtemp") as mock_mkdtemp:
                build_dir = Path(temp_dir) / "build"
                build_dir.mkdir()
                mock_mkdtemp.return_value = str(build_dir)

                # Don't create any distribution files

                result = publisher.build_package()

                assert result is False
                assert len(publisher.error_handler.errors) > 0

                # Check for build errors
                build_errors = [
                    e for e in publisher.error_handler.errors if e.category == ErrorCategory.BUILD
                ]
                assert len(build_errors) > 0

    def test_validate_built_package_no_build_dir(self) -> None:
        """Test package validation when no build directory exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir)
            publisher = PyPIPublisher(package_dir=package_dir)

            result = publisher.validate_built_package()

            assert result is False
            assert len(publisher.error_handler.errors) > 0

            # Check for validation error
            validation_errors = [
                e for e in publisher.error_handler.errors if e.category == ErrorCategory.VALIDATION
            ]
            assert len(validation_errors) > 0

    @patch("subprocess.run")
    def test_validate_built_package_success(self, mock_run: Mock) -> None:
        """Test successful built package validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir)
            build_dir = Path(temp_dir) / "build"
            build_dir.mkdir()

            # Create mock distribution files
            (build_dir / "test-1.0.0.tar.gz").touch()
            (build_dir / "test-1.0.0-py3-none-any.whl").touch()

            publisher = PyPIPublisher(package_dir=package_dir)
            publisher.build_dir = build_dir

            # Mock successful twine check
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Checking passed"
            mock_run.return_value.stderr = ""

            result = publisher.validate_built_package()

            assert result is True
            assert len(publisher.error_handler.errors) == 0

    def test_publish_to_pypi_dry_run(self) -> None:
        """Test PyPI publishing in dry run mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir)
            publisher = PyPIPublisher(package_dir=package_dir, dry_run=True)

            result = publisher.publish_to_pypi()

            assert result is True
            assert len(publisher.error_handler.errors) == 0

    def test_publish_to_pypi_no_build_dir(self) -> None:
        """Test PyPI publishing when no build directory exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir)
            publisher = PyPIPublisher(package_dir=package_dir, dry_run=False)

            result = publisher.publish_to_pypi()

            assert result is False
            assert len(publisher.error_handler.errors) > 0

            # Check for upload error
            upload_errors = [
                e for e in publisher.error_handler.errors if e.category == ErrorCategory.UPLOAD
            ]
            assert len(upload_errors) > 0

    def test_publish_to_pypi_no_token(self) -> None:
        """Test PyPI publishing when no API token is available."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir)
            build_dir = Path(temp_dir) / "build"
            build_dir.mkdir()

            # Create mock distribution files
            (build_dir / "test-1.0.0.tar.gz").touch()
            (build_dir / "test-1.0.0-py3-none-any.whl").touch()

            publisher = PyPIPublisher(package_dir=package_dir, dry_run=False)
            publisher.build_dir = build_dir

            with patch.dict("os.environ", {}, clear=True):
                result = publisher.publish_to_pypi()

                # Should succeed with placeholder behavior when no token
                assert result is True
                assert len(publisher.error_handler.errors) == 0

    @patch("subprocess.run")
    @patch.dict(
        "os.environ",
        {
            "PYPI_API_TOKEN": (
                "pypi-AgEIcHlwaS5vcmcCJRVOaXMxLjAyAAABhGlkAAABhGh0dHBzOi8vcHlwaS5vcmcvbGVnYWN5Lw"
            )
        },
    )
    def test_publish_to_pypi_with_token_success(self, mock_run: Mock) -> None:
        """Test successful PyPI publishing with API token."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir)
            build_dir = Path(temp_dir) / "build"
            build_dir.mkdir()

            # Create mock distribution files
            (build_dir / "test-1.0.0.tar.gz").touch()
            (build_dir / "test-1.0.0-py3-none-any.whl").touch()

            publisher = PyPIPublisher(package_dir=package_dir, dry_run=False)
            publisher.build_dir = build_dir

            # Mock successful twine upload
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Upload successful"
            mock_run.return_value.stderr = ""

            result = publisher.publish_to_pypi()

            assert result is True
            assert len(publisher.error_handler.errors) == 0

    def test_cleanup(self) -> None:
        """Test cleanup of temporary build directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir)
            build_dir = Path(temp_dir) / "build"
            build_dir.mkdir()

            # Create some files in build directory
            (build_dir / "test.txt").write_text("test")

            publisher = PyPIPublisher(package_dir=package_dir)
            publisher.build_dir = build_dir

            assert build_dir.exists()

            publisher.cleanup()

            assert not build_dir.exists()

    def test_generate_publishing_report_success(self) -> None:
        """Test generating publishing report for successful workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir)
            build_dir = Path(temp_dir) / "build"
            build_dir.mkdir()

            # Create mock distribution files
            (build_dir / "test-1.0.0.tar.gz").write_text("sdist content")
            (build_dir / "test-1.0.0-py3-none-any.whl").write_text("wheel content")

            publisher = PyPIPublisher(package_dir=package_dir, dry_run=True)
            publisher.build_dir = build_dir

            report = publisher.generate_publishing_report()

            assert report["publishing_status"] == "success"
            assert report["dry_run"] is True
            assert report["package_dir"] == str(package_dir)
            assert report["build_dir"] == str(build_dir)
            assert report["error_report"]["status"] == "success"
            assert len(report["distribution_files"]) == 2

    def test_generate_publishing_report_with_errors(self) -> None:
        """Test generating publishing report with errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir)
            publisher = PyPIPublisher(package_dir=package_dir)

            # Add a test error
            error = PublishingError(
                category=ErrorCategory.BUILD,
                severity=ErrorSeverity.HIGH,
                message="Build failed",
            )
            publisher.error_handler.errors = [error]

            report = publisher.generate_publishing_report()

            assert report["publishing_status"] == "failed"
            assert report["error_report"]["status"] == "error"
            assert report["error_report"]["total_errors"] == 1

    @patch.object(PyPIPublisher, "validate_environment")
    @patch.object(PyPIPublisher, "run_quality_gates")
    @patch.object(PyPIPublisher, "validate_package_metadata")
    @patch.object(PyPIPublisher, "build_package")
    @patch.object(PyPIPublisher, "validate_built_package")
    @patch.object(PyPIPublisher, "publish_to_pypi")
    @patch.object(PyPIPublisher, "cleanup")
    def test_run_publishing_workflow_success(
        self,
        mock_cleanup: Mock,
        mock_publish: Mock,
        mock_validate_built: Mock,
        mock_build: Mock,
        mock_validate_metadata: Mock,
        mock_quality_gates: Mock,
        mock_validate_env: Mock,
    ) -> None:
        """Test successful publishing workflow execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir)
            publisher = PyPIPublisher(package_dir=package_dir)

            # Mock all steps to succeed
            mock_validate_env.return_value = True
            mock_quality_gates.return_value = True
            mock_validate_metadata.return_value = True
            mock_build.return_value = True
            mock_validate_built.return_value = True
            mock_publish.return_value = True

            result = publisher.run_publishing_workflow()

            assert result is True
            assert len(publisher.error_handler.errors) == 0

            # Verify all steps were called
            mock_validate_env.assert_called_once()
            mock_quality_gates.assert_called_once()
            mock_validate_metadata.assert_called_once()
            mock_build.assert_called_once()
            mock_validate_built.assert_called_once()
            mock_publish.assert_called_once()
            mock_cleanup.assert_called_once()

    @patch.object(PyPIPublisher, "validate_environment")
    @patch.object(PyPIPublisher, "cleanup")
    def test_run_publishing_workflow_early_failure(
        self,
        mock_cleanup: Mock,
        mock_validate_env: Mock,
    ) -> None:
        """Test publishing workflow with early failure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir)
            publisher = PyPIPublisher(package_dir=package_dir)

            # Mock environment validation to fail
            mock_validate_env.return_value = False

            result = publisher.run_publishing_workflow()

            assert result is False

            # Verify cleanup is still called
            mock_cleanup.assert_called_once()

    @patch.object(PyPIPublisher, "validate_environment")
    @patch.object(PyPIPublisher, "cleanup")
    def test_run_publishing_workflow_exception(
        self,
        mock_cleanup: Mock,
        mock_validate_env: Mock,
    ) -> None:
        """Test publishing workflow with unexpected exception."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir)
            publisher = PyPIPublisher(package_dir=package_dir)

            # Mock environment validation to raise exception
            mock_validate_env.side_effect = ValueError("Test exception")

            result = publisher.run_publishing_workflow()

            assert result is False
            assert len(publisher.error_handler.errors) > 0

            # Check for unknown error
            unknown_errors = [
                e for e in publisher.error_handler.errors if e.category == ErrorCategory.UNKNOWN
            ]
            assert len(unknown_errors) > 0

            # Verify cleanup is still called
            mock_cleanup.assert_called_once()
