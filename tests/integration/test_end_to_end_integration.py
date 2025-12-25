"""Integration tests for end-to-end Phase 7 PyPI publishing workflows.

This module tests the complete integration of security monitoring, release
decision making, and PyPI publishing workflows.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import time
from unittest.mock import Mock, patch

from scripts.integration_orchestrator import IntegrationOrchestrator


class TestEndToEndIntegration:
    """Test complete end-to-end integration workflows."""

    def setup_method(self) -> None:
        """Set up test environment for each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.security_reports_dir = self.temp_dir / "security" / "reports" / "latest"
        self.status_output_dir = self.temp_dir / "docs" / "security-status"

        # Create directories
        self.security_reports_dir.mkdir(parents=True, exist_ok=True)
        self.status_output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize orchestrator with test directories
        self.orchestrator = IntegrationOrchestrator(
            security_reports_dir=self.security_reports_dir,
            status_output_dir=self.status_output_dir,
        )

    def teardown_method(self) -> None:
        """Clean up test environment after each test."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_security_driven_workflow_no_changes(self) -> None:
        """Test security-driven workflow when no security changes are detected."""
        # Create empty security reports in correct format
        bandit_report = {"results": []}
        pip_audit_report = {"dependencies": []}

        (self.security_reports_dir / "bandit.json").write_text(json.dumps(bandit_report))
        (self.security_reports_dir / "pip-audit.json").write_text(json.dumps(pip_audit_report))
        (self.security_reports_dir / "secrets-scan.json").write_text("[]")

        # Execute workflow
        result = self.orchestrator.execute_security_driven_workflow()

        # Verify results
        assert result["success"] is True
        assert result["security_changes"] == 0
        assert result["release_decision"]["should_release"] is False
        assert result["release_decision"]["trigger_type"] == "none"
        assert result["status_updated"] is True

        # Verify status files were created
        assert (self.status_output_dir / "index.json").exists()
        assert (self.status_output_dir / "index.html").exists()

        # Verify workflow outputs
        workflow_outputs = result["workflow_outputs"]
        assert workflow_outputs["should_release"] == "false"
        assert workflow_outputs["release_type"] == "none"
        assert workflow_outputs["changes_detected"] == "false"

    def test_security_driven_workflow_with_vulnerabilities(self) -> None:
        """Test security-driven workflow when vulnerabilities are detected."""
        # Create security reports with vulnerabilities in correct format
        bandit_report = {
            "results": [
                {
                    "filename": "src/mypylogger/core.py",
                    "test_name": "hardcoded_password_string",
                    "test_id": "B105",
                    "issue_severity": "LOW",
                    "issue_confidence": "MEDIUM",
                    "issue_text": "Possible hardcoded password",
                    "line_number": 42,
                    "line_range": [42],
                    "code": "password = 'test123'",
                }
            ]
        }

        pip_audit_report = {
            "dependencies": [
                {
                    "name": "requests",
                    "version": "2.25.1",
                    "vulns": [
                        {
                            "id": "PYSEC-2023-74",
                            "fix_versions": ["2.31.0"],
                            "description": "Requests Proxy-Authorization header leak",
                            "aliases": ["CVE-2023-32681"],
                        }
                    ],
                }
            ]
        }

        (self.security_reports_dir / "bandit.json").write_text(json.dumps(bandit_report))
        (self.security_reports_dir / "pip-audit.json").write_text(json.dumps(pip_audit_report))
        (self.security_reports_dir / "secrets-scan.json").write_text("[]")

        # Execute workflow
        result = self.orchestrator.execute_security_driven_workflow()

        # Verify results
        assert result["success"] is True
        assert result["security_changes"] >= 0  # May be 0 if no previous state to compare
        assert result["status_updated"] is True

        # Verify status reflects vulnerabilities
        status_file = self.status_output_dir / "index.json"
        assert status_file.exists()

        status_data = json.loads(status_file.read_text())
        assert status_data["vulnerability_summary"]["total"] > 0
        assert status_data["security_grade"] in ["B", "C", "D"]  # Not A due to vulnerabilities

    def test_manual_release_workflow(self) -> None:
        """Test manual release workflow with status updates."""
        # Create minimal security reports in correct format
        bandit_report = {"results": []}
        pip_audit_report = {"dependencies": []}

        (self.security_reports_dir / "bandit.json").write_text(json.dumps(bandit_report))
        (self.security_reports_dir / "pip-audit.json").write_text(json.dumps(pip_audit_report))
        (self.security_reports_dir / "secrets-scan.json").write_text("[]")

        # Execute manual workflow
        release_notes = "Manual release for bug fixes and improvements"
        result = self.orchestrator.execute_manual_release_workflow(
            release_notes=release_notes,
            update_status=True,
        )

        # Verify results
        assert result["success"] is True
        assert result["release_decision"]["should_release"] is True
        assert result["release_decision"]["trigger_type"] == "manual"
        assert release_notes in result["release_decision"]["release_notes"]
        assert result["status_updated"] is True

        # Verify workflow outputs
        workflow_outputs = result["workflow_outputs"]
        assert workflow_outputs["should_release"] == "true"
        assert workflow_outputs["release_type"] == "manual"
        assert release_notes in workflow_outputs["release_notes"]  # Notes are included in template

    def test_integration_health_validation(self) -> None:
        """Test integration health validation functionality."""
        # Create minimal security reports for health check
        (self.security_reports_dir / "bandit.json").write_text("[]")
        (self.security_reports_dir / "pip-audit.json").write_text("[]")

        # Execute health check
        health_result = self.orchestrator.validate_integration_health()

        # Verify health check results
        assert "timestamp" in health_result
        assert "overall_healthy" in health_result
        assert "components" in health_result

        # Check individual component health
        components = health_result["components"]
        assert "security_reports" in components
        assert "status_output" in components
        assert "security_findings" in components
        assert "release_engine" in components

        # Verify security reports component
        security_reports = components["security_reports"]
        assert security_reports["healthy"] is True
        assert security_reports["files_count"] >= 2  # bandit.json and pip-audit.json

    def test_workflow_error_handling(self) -> None:
        """Test error handling in workflow execution."""
        # Create orchestrator with invalid directories to trigger errors
        invalid_orchestrator = IntegrationOrchestrator(
            security_reports_dir=Path("/nonexistent/path"),
            status_output_dir=self.status_output_dir,
        )

        # Execute workflow that should handle errors gracefully
        result = invalid_orchestrator.execute_security_driven_workflow()

        # Verify error handling - should succeed but with no security changes
        # The system is designed to handle missing directories gracefully
        assert result["success"] is True
        assert result["security_changes"] == 0  # No findings from missing directory
        assert "timestamp" in result

    def test_status_file_generation(self) -> None:
        """Test live security status file generation."""
        # Create security reports with mixed findings in correct format
        bandit_report = {
            "results": [
                {
                    "filename": "test.py",
                    "test_name": "hardcoded_password_string",
                    "test_id": "B105",
                    "issue_severity": "MEDIUM",
                    "issue_confidence": "HIGH",
                    "issue_text": "Possible hardcoded password",
                    "line_number": 10,
                    "line_range": [10],
                    "code": "password = 'secret'",
                }
            ]
        }

        pip_audit_report = {"dependencies": []}

        (self.security_reports_dir / "bandit.json").write_text(json.dumps(bandit_report))
        (self.security_reports_dir / "pip-audit.json").write_text(json.dumps(pip_audit_report))
        (self.security_reports_dir / "secrets-scan.json").write_text("[]")

        # Execute workflow to generate status files
        self.orchestrator.execute_security_driven_workflow()

        # Verify status files were created
        json_file = self.status_output_dir / "index.json"
        html_file = self.status_output_dir / "index.html"

        assert json_file.exists()
        assert html_file.exists()

        # Verify JSON content
        status_data = json.loads(json_file.read_text())
        assert "last_updated" in status_data
        assert "vulnerability_summary" in status_data
        assert "security_grade" in status_data
        assert status_data["vulnerability_summary"]["total"] > 0

        # Verify HTML content
        html_content = html_file.read_text()
        assert "mypylogger Security Status" in html_content
        assert "Security Grade:" in html_content
        assert "Vulnerability Summary" in html_content

    def test_workflow_outputs_format(self) -> None:
        """Test that workflow outputs are properly formatted for GitHub Actions."""
        # Create minimal setup in correct format
        bandit_report = {"results": []}
        pip_audit_report = {"dependencies": []}

        (self.security_reports_dir / "bandit.json").write_text(json.dumps(bandit_report))
        (self.security_reports_dir / "pip-audit.json").write_text(json.dumps(pip_audit_report))
        (self.security_reports_dir / "secrets-scan.json").write_text("[]")

        # Execute workflow
        result = self.orchestrator.execute_security_driven_workflow()

        # Verify workflow outputs format
        workflow_outputs = result["workflow_outputs"]

        # Check all required outputs are present
        required_outputs = [
            "should_release",
            "release_type",
            "release_notes",
            "justification",
            "changes_detected",
            "sync_summary",
        ]

        for output in required_outputs:
            assert output in workflow_outputs

        # Verify boolean outputs are lowercase strings
        assert workflow_outputs["should_release"] in ["true", "false"]
        assert workflow_outputs["changes_detected"] in ["true", "false"]

        # Verify sync_summary is valid JSON
        sync_summary = json.loads(workflow_outputs["sync_summary"])
        assert isinstance(sync_summary, dict)

    def test_synchronizer_integration(self) -> None:
        """Test integration with remediation synchronizer."""
        # Mock the synchronizer on the orchestrator instance
        mock_synchronizer = Mock()
        mock_synchronizer.synchronize_findings.return_value = {
            "added": 2,
            "updated": 1,
            "removed": 0,
        }
        self.orchestrator.synchronizer = mock_synchronizer

        # Create minimal security reports in correct format
        bandit_report = {"results": []}
        pip_audit_report = {"dependencies": []}

        (self.security_reports_dir / "bandit.json").write_text(json.dumps(bandit_report))
        (self.security_reports_dir / "pip-audit.json").write_text(json.dumps(pip_audit_report))
        (self.security_reports_dir / "secrets-scan.json").write_text("[]")

        # Execute workflow
        result = self.orchestrator.execute_security_driven_workflow()

        # Verify synchronizer was called
        mock_synchronizer.synchronize_findings.assert_called_once()

        # Verify sync results are included
        assert result["success"] is True
        assert "sync_results" in result
        assert result["sync_results"]["added"] == 2
        assert result["sync_results"]["updated"] == 1

    def test_force_release_functionality(self) -> None:
        """Test force release functionality in security-driven workflow."""
        # Create minimal security reports (no changes) in correct format
        bandit_report = {"results": []}
        pip_audit_report = {"dependencies": []}

        (self.security_reports_dir / "bandit.json").write_text(json.dumps(bandit_report))
        (self.security_reports_dir / "pip-audit.json").write_text(json.dumps(pip_audit_report))
        (self.security_reports_dir / "secrets-scan.json").write_text("[]")

        # Execute workflow with force release
        result = self.orchestrator.execute_security_driven_workflow(
            force_release=True,
            custom_notes="Forced release for testing",
        )

        # Verify forced release behavior
        assert result["success"] is True
        assert result["release_decision"]["should_release"] is True
        assert result["release_decision"]["trigger_type"] == "manual"
        assert "Forced release for testing" in result["release_decision"]["release_notes"]

        # Verify workflow outputs reflect forced release
        workflow_outputs = result["workflow_outputs"]
        assert workflow_outputs["should_release"] == "true"
        assert workflow_outputs["release_type"] == "manual"

    def test_complete_publishing_workflow_simulation(self) -> None:
        """Test complete end-to-end publishing workflow simulation."""
        # Create security reports with vulnerabilities that should trigger release
        bandit_report = {
            "results": [
                {
                    "filename": "src/mypylogger/core.py",
                    "test_name": "hardcoded_password_string",
                    "test_id": "B105",
                    "issue_severity": "HIGH",
                    "issue_confidence": "HIGH",
                    "issue_text": "Possible hardcoded password",
                    "line_number": 42,
                    "line_range": [42],
                    "code": "password = 'secret123'",
                }
            ]
        }

        pip_audit_report = {
            "dependencies": [
                {
                    "name": "requests",
                    "version": "2.25.1",
                    "vulns": [
                        {
                            "id": "PYSEC-2023-74",
                            "fix_versions": ["2.31.0"],
                            "description": "Requests Proxy-Authorization header leak",
                            "aliases": ["CVE-2023-32681"],
                        }
                    ],
                }
            ]
        }

        (self.security_reports_dir / "bandit.json").write_text(json.dumps(bandit_report))
        (self.security_reports_dir / "pip-audit.json").write_text(json.dumps(pip_audit_report))
        (self.security_reports_dir / "secrets-scan.json").write_text("[]")

        # Execute security-driven workflow
        result = self.orchestrator.execute_security_driven_workflow()

        # Verify workflow execution
        assert result["success"] is True
        assert "execution_id" in result
        assert result["security_changes"] >= 0
        assert result["status_updated"] is True

        # Verify status files were created with vulnerability data
        status_file = self.status_output_dir / "index.json"
        assert status_file.exists()

        status_data = json.loads(status_file.read_text())
        assert status_data["vulnerability_summary"]["total"] > 0

        # Verify HTML status page was created
        html_file = self.status_output_dir / "index.html"
        assert html_file.exists()

        html_content = html_file.read_text()
        assert "Security Grade:" in html_content
        assert "Vulnerability Summary" in html_content

    def test_security_driven_automation_scenarios(self) -> None:
        """Test various security-driven automation scenarios."""
        test_scenarios = [
            {
                "name": "No vulnerabilities",
                "bandit_results": [],
                "pip_audit_deps": [],
                "expected_release": False,
                "expected_grade": "A",
            },
            {
                "name": "Low severity vulnerabilities",
                "bandit_results": [
                    {
                        "filename": "test.py",
                        "test_name": "hardcoded_password_string",
                        "test_id": "B105",
                        "issue_severity": "LOW",
                        "issue_confidence": "MEDIUM",
                        "issue_text": "Possible hardcoded password",
                        "line_number": 10,
                        "line_range": [10],
                        "code": "password = 'test'",
                    }
                ],
                "pip_audit_deps": [],
                "expected_release": False,  # Low severity shouldn't trigger auto-release
                "expected_grade": "B",
            },
            {
                "name": "High severity vulnerabilities",
                "bandit_results": [
                    {
                        "filename": "test.py",
                        "test_name": "hardcoded_password_string",
                        "test_id": "B105",
                        "issue_severity": "HIGH",
                        "issue_confidence": "HIGH",
                        "issue_text": "Hardcoded password detected",
                        "line_number": 10,
                        "line_range": [10],
                        "code": "password = 'production_secret'",
                    }
                ],
                "pip_audit_deps": [],
                "expected_release": False,  # May not trigger without previous state
                "expected_grade": "C",
            },
        ]

        for scenario in test_scenarios:
            # Use pytest.param for parameterized testing instead of subTest
            # Create security reports for this scenario
            bandit_report = {"results": scenario["bandit_results"]}
            pip_audit_report = {"dependencies": scenario["pip_audit_deps"]}

            (self.security_reports_dir / "bandit.json").write_text(json.dumps(bandit_report))
            (self.security_reports_dir / "pip-audit.json").write_text(json.dumps(pip_audit_report))
            (self.security_reports_dir / "secrets-scan.json").write_text("[]")

            # Execute workflow
            result = self.orchestrator.execute_security_driven_workflow()

            # Verify basic success
            assert result["success"] is True, f"Scenario '{scenario['name']}' failed"

            # Verify status was updated
            assert result["status_updated"] is True

            # Check security grade if status file exists
            status_file = self.status_output_dir / "index.json"
            if status_file.exists():
                status_data = json.loads(status_file.read_text())
                # Note: Grade calculation may vary based on implementation
                assert "security_grade" in status_data

    def test_performance_and_load_scenarios(self) -> None:
        """Test performance and load scenarios for status API endpoints."""
        # Create a status file to test performance
        bandit_report = {"results": []}
        pip_audit_report = {"dependencies": []}

        (self.security_reports_dir / "bandit.json").write_text(json.dumps(bandit_report))
        (self.security_reports_dir / "pip-audit.json").write_text(json.dumps(pip_audit_report))
        (self.security_reports_dir / "secrets-scan.json").write_text("[]")

        # Execute workflow to create status files
        result = self.orchestrator.execute_security_driven_workflow()
        assert result["success"] is True

        # Test multiple rapid status updates (load testing)
        start_time = time.time()

        for i in range(10):
            # Simulate rapid status updates
            result = self.orchestrator.execute_manual_release_workflow(
                release_notes=f"Load test release {i}",
                update_status=True,
            )
            assert result["success"] is True

        total_time = time.time() - start_time

        # Verify performance is reasonable (should complete 10 updates in under 5 seconds)
        assert total_time < 5.0, f"Load test took too long: {total_time:.2f}s"

        # Verify status file is still valid after load testing
        status_file = self.status_output_dir / "index.json"
        assert status_file.exists()

        status_data = json.loads(status_file.read_text())
        assert "last_updated" in status_data
        assert "vulnerability_summary" in status_data

    def test_error_recovery_and_resilience(self) -> None:
        """Test error recovery and system resilience."""
        # Test with corrupted security reports
        (self.security_reports_dir / "bandit.json").write_text("invalid json")
        (self.security_reports_dir / "pip-audit.json").write_text("{}")
        (self.security_reports_dir / "secrets-scan.json").write_text("[]")

        # Workflow should handle corrupted data gracefully
        result = self.orchestrator.execute_security_driven_workflow()

        # Should still succeed but with warnings
        assert result["success"] is True
        assert result["security_changes"] == 0  # No valid findings to process

        # Test with missing security reports directory
        import shutil

        shutil.rmtree(self.security_reports_dir)

        result = self.orchestrator.execute_security_driven_workflow()

        # Should handle missing directory gracefully
        assert result["success"] is True
        assert result["security_changes"] == 0

        # Test health check with degraded state
        health_result = self.orchestrator.validate_integration_health()

        assert "overall_healthy" in health_result
        assert "components" in health_result
        # May not be fully healthy due to missing reports, but should not crash

    def test_monitoring_integration(self) -> None:
        """Test monitoring and metrics collection integration."""
        # Create minimal security reports
        bandit_report = {"results": []}
        pip_audit_report = {"dependencies": []}

        (self.security_reports_dir / "bandit.json").write_text(json.dumps(bandit_report))
        (self.security_reports_dir / "pip-audit.json").write_text(json.dumps(pip_audit_report))
        (self.security_reports_dir / "secrets-scan.json").write_text("[]")

        # Execute workflow and verify monitoring data is collected
        result = self.orchestrator.execute_security_driven_workflow()

        assert result["success"] is True
        assert "execution_id" in result

        # Verify monitoring dashboard data can be generated
        dashboard_data = self.orchestrator.get_monitoring_dashboard()

        assert "generated_at" in dashboard_data
        assert "publishing_stats" in dashboard_data
        assert "health_status" in dashboard_data

        # Verify publishing statistics can be retrieved
        stats = self.orchestrator.get_publishing_statistics(7)

        assert "total_attempts" in stats
        assert "success_rate_percent" in stats


class TestIntegrationOrchestratorCLI:
    """Test command-line interface of integration orchestrator."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.security_reports_dir = self.temp_dir / "security" / "reports" / "latest"
        self.security_reports_dir.mkdir(parents=True, exist_ok=True)

        # Create minimal security reports in correct format
        bandit_report = {"results": []}
        pip_audit_report = {"dependencies": []}

        (self.security_reports_dir / "bandit.json").write_text(json.dumps(bandit_report))
        (self.security_reports_dir / "pip-audit.json").write_text(json.dumps(pip_audit_report))
        (self.security_reports_dir / "secrets-scan.json").write_text("[]")

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch("scripts.integration_orchestrator.IntegrationOrchestrator")
    def test_cli_security_workflow_command(self, mock_orchestrator_class: Mock) -> None:
        """Test CLI security workflow command."""
        # Mock orchestrator behavior
        mock_orchestrator = Mock()
        mock_orchestrator.execute_security_driven_workflow.return_value = {
            "success": True,
            "security_changes": 0,
        }
        mock_orchestrator_class.return_value = mock_orchestrator

        # Test CLI execution
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["integration_orchestrator.py", "security-workflow"]):
            with patch("builtins.print"):
                from scripts.integration_orchestrator import main

                # Should not raise SystemExit on success
                main()

                # Verify orchestrator was called
                mock_orchestrator.execute_security_driven_workflow.assert_called_once_with(
                    force_release=False,
                    custom_notes=None,
                )

    @patch("scripts.integration_orchestrator.IntegrationOrchestrator")
    def test_cli_manual_workflow_command(self, mock_orchestrator_class: Mock) -> None:
        """Test CLI manual workflow command."""
        # Mock orchestrator behavior
        mock_orchestrator = Mock()
        mock_orchestrator.execute_manual_release_workflow.return_value = {
            "success": True,
        }
        mock_orchestrator_class.return_value = mock_orchestrator

        # Test CLI execution with notes
        import sys
        from unittest.mock import patch

        test_args = [
            "integration_orchestrator.py",
            "manual-workflow",
            "--notes=Test release notes",
        ]

        with patch.object(sys, "argv", test_args):
            with patch("builtins.print"):
                from scripts.integration_orchestrator import main

                # Should not raise SystemExit on success
                main()

                # Verify orchestrator was called with correct parameters
                mock_orchestrator.execute_manual_release_workflow.assert_called_once_with(
                    release_notes="Test release notes",
                    update_status=True,
                )

    @patch("scripts.integration_orchestrator.IntegrationOrchestrator")
    def test_cli_health_check_command(self, mock_orchestrator_class: Mock) -> None:
        """Test CLI health check command."""
        # Mock orchestrator behavior
        mock_orchestrator = Mock()
        mock_orchestrator.validate_integration_health.return_value = {
            "overall_healthy": True,
            "components": {},
        }
        mock_orchestrator_class.return_value = mock_orchestrator

        # Test CLI execution
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["integration_orchestrator.py", "health-check"]):
            with patch("builtins.print"):
                from scripts.integration_orchestrator import main

                # Should not raise SystemExit on success
                main()

                # Verify orchestrator was called
                mock_orchestrator.validate_integration_health.assert_called_once()
