"""Integration tests for PyPI publishing workflows and security validation.

This module provides comprehensive integration tests for the complete
PyPI publishing system including security validation, performance testing,
and end-to-end workflow validation.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
from typing import Any
from unittest.mock import patch

from scripts.integration_orchestrator import IntegrationOrchestrator
from scripts.security_performance_validator import SecurityPerformanceValidator
from scripts.workflow_monitoring import WorkflowMonitor


class TestPyPIPublishingIntegration:
    """Test complete PyPI publishing integration scenarios."""

    def setup_method(self) -> None:
        """Set up test environment for each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.security_reports_dir = self.temp_dir / "security" / "reports" / "latest"
        self.status_output_dir = self.temp_dir / "docs" / "security-status"
        self.metrics_dir = self.temp_dir / "metrics"

        # Create directories
        self.security_reports_dir.mkdir(parents=True, exist_ok=True)
        self.status_output_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.orchestrator = IntegrationOrchestrator(
            security_reports_dir=self.security_reports_dir,
            status_output_dir=self.status_output_dir,
        )

        # Override the monitor to use our test metrics directory
        self.orchestrator.monitor = WorkflowMonitor(metrics_dir=self.metrics_dir)

        self.validator = SecurityPerformanceValidator()
        self.monitor = WorkflowMonitor(metrics_dir=self.metrics_dir)

    def teardown_method(self) -> None:
        """Clean up test environment after each test."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_complete_security_driven_publishing_workflow(self) -> None:
        """Test complete security-driven publishing workflow from start to finish."""
        # Step 1: Create security reports that should trigger a release
        high_severity_bandit = {
            "results": [
                {
                    "filename": "src/mypylogger/core.py",
                    "test_name": "hardcoded_password_string",
                    "test_id": "B105",
                    "issue_severity": "HIGH",
                    "issue_confidence": "HIGH",
                    "issue_text": "Hardcoded password detected",
                    "line_number": 42,
                    "line_range": [42],
                    "code": "password = 'production_secret_key'",
                }
            ]
        }

        vulnerable_dependency = {
            "dependencies": [
                {
                    "name": "requests",
                    "version": "2.25.1",
                    "vulns": [
                        {
                            "id": "PYSEC-2023-74",
                            "fix_versions": ["2.31.0"],
                            "description": "Requests Proxy-Authorization header leak vulnerability",
                            "aliases": ["CVE-2023-32681"],
                        }
                    ],
                }
            ]
        }

        (self.security_reports_dir / "bandit.json").write_text(json.dumps(high_severity_bandit))
        (self.security_reports_dir / "pip-audit.json").write_text(json.dumps(vulnerable_dependency))
        (self.security_reports_dir / "secrets-scan.json").write_text("[]")

        # Step 2: Execute security-driven workflow
        workflow_result = self.orchestrator.execute_security_driven_workflow()

        # Step 3: Verify workflow execution
        assert workflow_result["success"] is True
        assert "execution_id" in workflow_result
        assert workflow_result["status_updated"] is True

        # Step 4: Verify security status was updated correctly
        status_file = self.status_output_dir / "index.json"
        assert status_file.exists()

        status_data = json.loads(status_file.read_text())
        assert status_data["vulnerability_summary"]["total"] > 0
        assert status_data["vulnerability_summary"]["high"] > 0
        assert status_data["security_grade"] in [
            "B",
            "C",
            "D",
        ]  # Should not be A due to vulnerabilities

        # Step 5: Verify HTML status page
        html_file = self.status_output_dir / "index.html"
        assert html_file.exists()

        html_content = html_file.read_text()
        assert "mypylogger Security Status" in html_content
        assert "Vulnerability Summary" in html_content
        assert status_data["security_grade"] in html_content

        # Step 6: Verify monitoring metrics were recorded
        dashboard_data = self.orchestrator.get_monitoring_dashboard()
        assert "generated_at" in dashboard_data
        assert "publishing_stats" in dashboard_data

    def test_manual_release_with_status_update_workflow(self) -> None:
        """Test manual release workflow with comprehensive status updates."""
        # Create baseline security reports (clean state)
        clean_bandit = {"results": []}
        clean_pip_audit = {"dependencies": []}

        (self.security_reports_dir / "bandit.json").write_text(json.dumps(clean_bandit))
        (self.security_reports_dir / "pip-audit.json").write_text(json.dumps(clean_pip_audit))
        (self.security_reports_dir / "secrets-scan.json").write_text("[]")

        # Execute manual release workflow
        release_notes = "Manual release v0.2.1 - Bug fixes and performance improvements"
        result = self.orchestrator.execute_manual_release_workflow(
            release_notes=release_notes,
            update_status=True,
        )

        # Verify manual release execution
        assert result["success"] is True
        assert result["release_decision"]["should_release"] is True
        assert result["release_decision"]["trigger_type"] == "manual"
        assert release_notes in result["release_decision"]["release_notes"]
        assert result["status_updated"] is True

        # Verify status reflects clean security state
        status_file = self.status_output_dir / "index.json"
        assert status_file.exists()

        status_data = json.loads(status_file.read_text())
        assert status_data["vulnerability_summary"]["total"] == 0
        assert status_data["security_grade"] == "A"  # Should be A with no vulnerabilities

        # Verify workflow outputs for GitHub Actions
        workflow_outputs = result["workflow_outputs"]
        assert workflow_outputs["should_release"] == "true"
        assert workflow_outputs["release_type"] == "manual"
        assert workflow_outputs["changes_detected"] == "false"

    def test_security_performance_validation_integration(self) -> None:
        """Test integration with security and performance validation."""
        # Create status files for performance testing
        clean_bandit = {"results": []}
        clean_pip_audit = {"dependencies": []}

        (self.security_reports_dir / "bandit.json").write_text(json.dumps(clean_bandit))
        (self.security_reports_dir / "pip-audit.json").write_text(json.dumps(clean_pip_audit))
        (self.security_reports_dir / "secrets-scan.json").write_text("[]")

        # Execute workflow to create status files
        result = self.orchestrator.execute_security_driven_workflow()
        assert result["success"] is True

        # Test security validation (no AWS environment variables needed for trusted publishing)
        validation_results = self.validator.run_complete_validation()

        assert "overall_passed" in validation_results
        assert "security" in validation_results
        assert "performance" in validation_results

        # Security validation should pass with trusted publishing configuration
        assert validation_results["security"]["passed"] is True

        # Performance validation may pass or fail depending on file availability
        assert "passed" in validation_results["performance"]

    def test_workflow_monitoring_and_metrics_collection(self) -> None:
        """Test comprehensive workflow monitoring and metrics collection."""
        # Create test security reports
        bandit_report = {"results": []}
        pip_audit_report = {"dependencies": []}

        (self.security_reports_dir / "bandit.json").write_text(json.dumps(bandit_report))
        (self.security_reports_dir / "pip-audit.json").write_text(json.dumps(pip_audit_report))
        (self.security_reports_dir / "secrets-scan.json").write_text("[]")

        # Execute multiple workflows to generate metrics
        workflows = [
            (
                "security-driven-release",
                lambda: self.orchestrator.execute_security_driven_workflow(),
            ),
            (
                "manual-release",
                lambda: self.orchestrator.execute_manual_release_workflow("Test release"),
            ),
        ]

        execution_ids = []

        for _workflow_name, workflow_func in workflows:
            result = workflow_func()
            assert result["success"] is True
            assert "execution_id" in result
            execution_ids.append(result["execution_id"])

        # Verify metrics files were created
        metrics_files = list(self.metrics_dir.glob("workflow-*.json"))
        # Note: May only have 1 file if workflows complete very quickly
        assert len(metrics_files) >= 1

        # Verify metrics content
        for metrics_file in metrics_files:
            with metrics_file.open() as f:
                metrics_data = json.load(f)

            assert "workflow_name" in metrics_data
            assert "execution_id" in metrics_data
            assert "start_time" in metrics_data
            assert "status" in metrics_data
            assert metrics_data["status"] == "success"

        # Test publishing statistics
        stats = self.monitor.get_publishing_stats(30)
        assert stats.total_attempts >= 1

        # Test dashboard generation
        dashboard_data = self.monitor.generate_dashboard_data()
        assert "generated_at" in dashboard_data
        assert "publishing_stats" in dashboard_data
        assert "recent_workflows" in dashboard_data
        assert len(dashboard_data["recent_workflows"]) >= 1

    def test_error_handling_and_recovery_scenarios(self) -> None:
        """Test comprehensive error handling and recovery scenarios."""
        # Test scenario 1: Corrupted security reports
        (self.security_reports_dir / "bandit.json").write_text("invalid json content")
        (self.security_reports_dir / "pip-audit.json").write_text('{"malformed": json}')
        (self.security_reports_dir / "secrets-scan.json").write_text("not json at all")

        result = self.orchestrator.execute_security_driven_workflow()

        # Should handle corrupted data gracefully
        assert result["success"] is True  # Should not crash
        assert result["security_changes"] == 0  # No valid data to process

        # Test scenario 2: Missing security reports directory
        import shutil

        shutil.rmtree(self.security_reports_dir)

        result = self.orchestrator.execute_security_driven_workflow()

        # Should handle missing directory gracefully
        assert result["success"] is True
        assert result["security_changes"] == 0

        # Test scenario 3: Permission errors (simulate)
        self.security_reports_dir.mkdir(parents=True, exist_ok=True)

        # Create valid reports again
        (self.security_reports_dir / "bandit.json").write_text('{"results": []}')
        (self.security_reports_dir / "pip-audit.json").write_text('{"dependencies": []}')
        (self.security_reports_dir / "secrets-scan.json").write_text("[]")

        # Simulate status output directory permission error
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            mock_mkdir.side_effect = PermissionError("Permission denied")

            result = self.orchestrator.execute_security_driven_workflow()

            # Should handle permission errors gracefully
            assert result["success"] is True
            # Status update may fail, but workflow should continue

        # Test scenario 4: Health check with degraded components
        health_result = self.orchestrator.validate_integration_health()

        assert "overall_healthy" in health_result
        assert "components" in health_result
        assert "timestamp" in health_result

    def test_performance_and_load_testing(self) -> None:
        """Test performance characteristics and load handling."""
        # Create baseline security reports
        bandit_report = {"results": []}
        pip_audit_report = {"dependencies": []}

        (self.security_reports_dir / "bandit.json").write_text(json.dumps(bandit_report))
        (self.security_reports_dir / "pip-audit.json").write_text(json.dumps(pip_audit_report))
        (self.security_reports_dir / "secrets-scan.json").write_text("[]")

        # Performance test: Measure workflow execution time
        start_time = time.time()

        result = self.orchestrator.execute_security_driven_workflow()

        execution_time = time.time() - start_time

        assert result["success"] is True

        # Use CI-aware performance threshold from test environment config
        # The standardized_test_environment fixture provides this automatically
        # Increased CI threshold to account for variable CI performance
        threshold = 60.0 if os.environ.get("TEST_ENVIRONMENT") == "ci" else 10.0
        assert execution_time < threshold

        # Load test: Execute multiple workflows rapidly
        load_test_start = time.time()

        for i in range(5):
            result = self.orchestrator.execute_manual_release_workflow(
                release_notes=f"Load test release {i}",
                update_status=True,
            )
            assert result["success"] is True

        load_test_time = time.time() - load_test_start

        # Should handle 5 rapid executions within reasonable time
        # Use CI-aware performance threshold from test environment config
        # The standardized_test_environment fixture provides this automatically
        load_threshold = 30.0 if os.environ.get("TEST_ENVIRONMENT") == "ci" else 15.0
        assert load_test_time < load_threshold

        # Verify status file integrity after load testing
        status_file = self.status_output_dir / "index.json"
        assert status_file.exists()

        status_data = json.loads(status_file.read_text())
        assert "last_updated" in status_data
        assert "vulnerability_summary" in status_data

        # Performance test: Status file access time
        access_start = time.time()

        for _ in range(100):
            with status_file.open() as f:
                json.load(f)

        access_time = time.time() - access_start

        # 100 file accesses should be very fast
        assert access_time < 1.0  # Under 1 second for 100 accesses

    def test_integration_health_monitoring(self) -> None:
        """Test comprehensive integration health monitoring."""
        # Create various states to test health monitoring
        test_states = [
            {
                "name": "Healthy state",
                "setup": lambda: self._create_clean_reports(),
                "expected_healthy": True,
            },
            {
                "name": "Degraded state - missing reports",
                "setup": lambda: shutil.rmtree(self.security_reports_dir, ignore_errors=True),
                "expected_healthy": True,  # Should still be considered healthy
            },
            {
                "name": "Recovered state",
                "setup": lambda: self._create_clean_reports(),
                "expected_healthy": True,
            },
        ]

        for state in test_states:
            # Use pytest.param for parameterized testing instead of subTest
            # Set up the test state
            state["setup"]()

            # Run health check
            health_result = self.orchestrator.validate_integration_health()

            # Verify health check structure
            assert "timestamp" in health_result
            assert "overall_healthy" in health_result
            assert "components" in health_result

            # Verify component checks
            components = health_result["components"]
            assert "security_reports" in components
            assert "status_output" in components
            assert "security_findings" in components
            assert "release_engine" in components

            # Each component should have health status
            for component_data in components.values():
                assert "healthy" in component_data

    def test_environment_detection_and_configuration(
        self, test_environment_config: dict[str, Any]
    ) -> None:
        """Test CI environment detection and configuration adjustment."""
        # Verify test environment configuration is available
        assert "is_ci" in test_environment_config
        assert "performance_multiplier" in test_environment_config
        assert "timeout_multiplier" in test_environment_config
        assert "max_execution_time" in test_environment_config

        # Verify environment-specific values are set correctly
        is_ci = test_environment_config["is_ci"]

        if is_ci:
            # CI environment should have more lenient thresholds for GitHub Actions
            assert test_environment_config["performance_multiplier"] == 2.0  # 100% more time
            assert test_environment_config["timeout_multiplier"] == 2.5  # 150% more timeout
            assert test_environment_config["max_execution_time"] == 600.0  # 10 minutes for CI
            assert test_environment_config["retry_attempts"] == 5  # More retries for GitHub Actions
        else:
            # Local environment should have stricter thresholds
            assert test_environment_config["performance_multiplier"] == 1.0
            assert test_environment_config["timeout_multiplier"] == 1.0
            assert test_environment_config["max_execution_time"] == 300.0  # 5 minutes for local
            assert test_environment_config["retry_attempts"] == 2

        # Verify repository context is set correctly
        assert os.environ.get("GITHUB_REPOSITORY") == "stabbotco1/mypylogger"
        assert os.environ.get("GITHUB_REPOSITORY_OWNER") == "stabbotco1"
        assert os.environ.get("TEST_REPOSITORY_CONTEXT") == "stabbotco1/mypylogger"

        # Test performance threshold calculation with environment config
        # Use the max_execution_time from test environment config which already
        # accounts for GitHub Actions performance requirements (30% cushion + overhead)
        expected_threshold = test_environment_config["max_execution_time"]

        # Create a simple workflow to test performance
        start_time = time.time()

        # Simulate some work (create and process security reports)
        self._create_clean_reports()
        result = self.orchestrator.execute_security_driven_workflow()

        execution_time = time.time() - start_time

        # Verify workflow succeeded
        assert result["success"] is True

        # Verify execution time is within environment-appropriate threshold
        # GitHub Actions environments get 600s (10 minutes), local gets 300s (5 minutes)
        assert execution_time < expected_threshold, (
            f"Execution time {execution_time:.2f}s exceeded threshold {expected_threshold}s "
            f"for {'CI' if test_environment_config['is_ci'] else 'local'} environment"
        )

    def _create_clean_reports(self) -> None:
        """Helper method to create clean security reports."""
        self.security_reports_dir.mkdir(parents=True, exist_ok=True)

        bandit_report = {"results": []}
        pip_audit_report = {"dependencies": []}

        (self.security_reports_dir / "bandit.json").write_text(json.dumps(bandit_report))
        (self.security_reports_dir / "pip-audit.json").write_text(json.dumps(pip_audit_report))
        (self.security_reports_dir / "secrets-scan.json").write_text("[]")


class TestSecurityValidationIntegration:
    """Test security validation integration scenarios."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.validator = SecurityPerformanceValidator()

    def test_trusted_publishing_security_validation_scenarios(self) -> None:
        """Test various trusted publishing security validation scenarios."""
        # Test with existing workflow configuration
        results = self.validator.security_validator.run_all_security_validations()

        # Find trusted publishing configuration result
        trusted_publishing_result = next(
            (r for r in results if r.test_name == "Trusted Publishing Configuration"), None
        )

        assert trusted_publishing_result is not None
        # Should pass since we have a valid pypi-publish.yml workflow
        assert trusted_publishing_result.passed is True

    def test_credential_security_validation_scenarios(self) -> None:
        """Test credential security validation scenarios."""
        # Create temporary workflow directory
        temp_dir = Path(tempfile.mkdtemp())
        workflows_dir = temp_dir / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)

        try:
            # Test scenario 1: Secure workflow (no hardcoded secrets)
            secure_workflow = """
name: Secure PyPI Publish
on: workflow_dispatch
permissions:
  id-token: write
  contents: read
environment: pypi-publishing
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - name: Publish
        run: echo "Publishing"
        env:
          PYPI_TOKEN: ${{ secrets.PYPI_TOKEN }}
"""

            (workflows_dir / "secure-publish.yml").write_text(secure_workflow)

            with patch("pathlib.Path.cwd", return_value=temp_dir):
                results = self.validator.security_validator.run_all_security_validations()

                credential_result = next(
                    (r for r in results if r.test_name == "Credential Security"), None
                )

                assert credential_result is not None
                assert credential_result.passed is True

            # Test scenario 2: Workflow with proper authorization
            auth_result = next(
                (r for r in results if r.test_name == "Publishing Authorization"), None
            )

            assert auth_result is not None
            assert auth_result.passed is True

        finally:
            # Clean up
            import shutil

            shutil.rmtree(temp_dir)


class TestPerformanceValidationIntegration:
    """Test performance validation integration scenarios."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.validator = SecurityPerformanceValidator()
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_status_api_performance_validation(self) -> None:
        """Test status API performance validation scenarios."""
        # Create status file for local testing
        status_dir = self.temp_dir / "docs" / "security-status"
        status_dir.mkdir(parents=True)

        status_data = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "vulnerability_summary": {"total": 0, "high": 0, "medium": 0, "low": 0},
            "security_grade": "A",
            "days_since_last_vulnerability": 30,
        }

        status_file = status_dir / "index.json"
        with status_file.open("w") as f:
            json.dump(status_data, f)

        # Test performance validation
        with patch("pathlib.Path.cwd", return_value=self.temp_dir):
            results = self.validator.performance_validator.run_all_performance_validations()

            # Find status API performance result
            status_result = next(
                (r for r in results if "Status API Performance" in r.test_name), None
            )

            assert status_result is not None
            assert status_result.actual_time >= 0
            assert status_result.target_time > 0

    def test_workflow_execution_time_validation(self) -> None:
        """Test workflow execution time validation scenarios."""
        # Create metrics directory with sample workflow data
        metrics_dir = self.temp_dir / "metrics"
        metrics_dir.mkdir()

        # Create sample workflow metrics (fast execution)
        fast_metrics = [
            {"duration_seconds": 45.0, "status": "success"},
            {"duration_seconds": 52.0, "status": "success"},
            {"duration_seconds": 38.0, "status": "success"},
        ]

        for i, metrics in enumerate(fast_metrics):
            metrics_file = metrics_dir / f"workflow-pypi-publish-{i}.json"
            with metrics_file.open("w") as f:
                json.dump(metrics, f)

        # Test with fast execution times
        with patch("pathlib.Path.cwd", return_value=self.temp_dir):
            results = self.validator.performance_validator.run_all_performance_validations()

            # Find workflow execution time result
            workflow_result = next(
                (r for r in results if "Workflow Execution Time (pypi-publish)" in r.test_name),
                None,
            )

            assert workflow_result is not None
            assert workflow_result.passed is True  # Should pass with fast times
            assert workflow_result.actual_time < workflow_result.target_time

        # Test with slow execution times
        slow_metrics = [
            {"duration_seconds": 600.0, "status": "success"},  # 10 minutes
            {"duration_seconds": 720.0, "status": "success"},  # 12 minutes
            {"duration_seconds": 540.0, "status": "success"},  # 9 minutes
        ]

        for i, metrics in enumerate(slow_metrics):
            metrics_file = metrics_dir / f"workflow-pypi-publish-slow-{i}.json"
            with metrics_file.open("w") as f:
                json.dump(metrics, f)

        # Test with slow execution times (should fail 5-minute target)
        # In CI, 300s becomes 450s (1.5x), so we need times > 450s average to fail
        with patch("pathlib.Path.cwd", return_value=self.temp_dir):
            result = self.validator.performance_validator.validate_workflow_execution_time(
                "pypi-publish-slow",
                300.0,  # 5-minute target (becomes 450s in CI)
            )

            assert result.passed is False  # Should fail with slow times
            assert result.actual_time > result.target_time
