#!/usr/bin/env python3
"""Test script for validating YAML validation integration with security workflows.

Tests that security workflows execute successfully with YAML validation enabled,
verifies error handling doesn't interfere with normal operation, and validates
fallback mechanisms work correctly when data files are corrupted.

Requirements addressed: 18.3, 19.4, 19.5
"""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List

import yaml


class SecurityWorkflowIntegrationTester:
    """Test integration between YAML validation and security workflows."""

    def __init__(self, verbose: bool = False) -> None:
        """Initialize the tester.

        Args:
            verbose: Enable verbose output
        """
        self.verbose = verbose
        self.test_results: List[Dict[str, Any]] = []
        self.temp_dir: Path = None
        self.project_dir: Path = None

    def setup_test_environment(self) -> None:
        """Set up test environment with complete project structure."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_dir = self.temp_dir / "test_project"

        # Create complete directory structure
        directories = [
            self.project_dir,
            self.project_dir / "security" / "findings",
            self.project_dir / "security" / "config",
            self.project_dir / "security" / "reports",
            self.project_dir / "security" / "scripts",
            self.project_dir / "security" / "audit",
            self.project_dir / "security" / "backups",
            self.project_dir / "security" / "alerts",
            self.project_dir / "scripts",
            self.project_dir / ".github" / "workflows",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

        # Copy all necessary scripts and workflows
        self._copy_project_files()

        if self.verbose:
            print(f"✅ Test environment created at: {self.project_dir}")

    def cleanup_test_environment(self) -> None:
        """Clean up test environment."""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            if self.verbose:
                print("✅ Test environment cleaned up")

    def _copy_project_files(self) -> None:
        """Copy all necessary project files to test environment."""
        # Scripts to copy
        script_files = [
            "scripts/validate_security_yaml.py",
            "scripts/repair_yaml.py",
            "scripts/cicd_error_handler.py",
            "scripts/cicd_monitoring.py",
            "security/scripts/update-findings.py",
        ]

        # Security modules to copy
        security_modules = ["security/error_handling.py", "security/monitoring.py"]

        # Workflow files to copy
        workflow_files = [
            ".github/workflows/security-scan.yml",
            ".github/workflows/yaml-validation-step.yml",
            ".github/workflows/error-handling-step.yml",
            ".github/workflows/monitoring-step.yml",
        ]

        all_files = script_files + security_modules + workflow_files

        for file_path in all_files:
            src_path = Path(file_path)
            if src_path.exists():
                dst_path = self.project_dir / file_path
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
                if self.verbose:
                    print(f"  Copied: {file_path}")

    def _create_test_security_files(self, scenario: str = "valid") -> None:
        """Create test security files for different scenarios.

        Args:
            scenario: Type of scenario (valid, corrupted, mixed)
        """
        security_dir = self.project_dir / "security" / "findings"

        if scenario == "valid":
            # Create valid security files
            timeline_content = {
                "timeline": [
                    {
                        "timestamp": "2025-01-01T00:00:00Z",
                        "action": "finding_created",
                        "finding_id": "TEST-001",
                        "user": "test_user",
                    }
                ],
                "metadata": {"version": "1.0", "generated": "2025-01-01T00:00:00Z"},
            }

            findings_content = {
                "findings": [
                    {
                        "id": "TEST-001",
                        "severity": "high",
                        "description": "Test security finding",
                        "status": "active",
                    }
                ],
                "metadata": {"total_findings": 1, "generated": "2025-01-01T00:00:00Z"},
            }

            # Write valid files
            with (security_dir / "remediation-timeline.yml").open("w") as f:
                yaml.dump(timeline_content, f, default_flow_style=False)

            with (security_dir / "remediation-plans.yml").open("w") as f:
                yaml.dump(findings_content, f, default_flow_style=False)

        elif scenario == "corrupted":
            # Create corrupted YAML files
            corrupted_timeline = """timeline:
  - timestamp: "2025-01-01T00:00:00Z
    action: "finding_created  # Missing closing quote
    finding_id: TEST-001"  # Misplaced quote
metadata:
  version: 1.0
"""

            corrupted_findings = """findings:
  - id: TEST-001
    severity: high
    description: [invalid, yaml, structure
metadata:
  total_findings: 1
"""

            (security_dir / "remediation-timeline.yml").write_text(corrupted_timeline)
            (security_dir / "remediation-plans.yml").write_text(corrupted_findings)

        elif scenario == "mixed":
            # Create mix of valid and corrupted files
            valid_content = {"timeline": [], "metadata": {"version": "1.0"}}

            with (security_dir / "valid-timeline.yml").open("w") as f:
                yaml.dump(valid_content, f)

            corrupted_content = "invalid: yaml: content:"
            (security_dir / "corrupted-plans.yml").write_text(corrupted_content)

    def _run_script(
        self, script_path: str, args: List[str] = None, env_vars: Dict[str, str] = None
    ) -> subprocess.CompletedProcess:
        """Run a script and return the result.

        Args:
            script_path: Path to script relative to project directory
            args: Command line arguments
            env_vars: Additional environment variables

        Returns:
            CompletedProcess with results
        """
        if args is None:
            args = []

        cmd = [sys.executable, script_path] + args

        # Set up environment
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)

        if self.verbose:
            print(f"  Running: {' '.join(cmd)}")

        return subprocess.run(
            cmd, check=False, capture_output=True, text=True, cwd=self.project_dir, env=env
        )

    def _record_test_result(self, test_name: str, success: bool, details: Dict[str, Any]) -> None:
        """Record test result.

        Args:
            test_name: Name of the test
            success: Whether test passed
            details: Additional test details
        """
        result = {
            "test_name": test_name,
            "success": success,
            "timestamp": time.time(),
            "details": details,
        }
        self.test_results.append(result)

        status = "✅ PASS" if success else "❌ FAIL"
        if self.verbose:
            print(f"{status}: {test_name}")

    def test_yaml_validation_with_normal_security_workflow(self) -> bool:
        """Test that YAML validation works with normal security workflow execution."""
        test_name = "YAML Validation with Normal Security Workflow"

        try:
            # Create valid security files
            self._create_test_security_files("valid")

            # Run YAML validation
            yaml_result = self._run_script(
                "scripts/validate_security_yaml.py", ["--check", "--verbose"]
            )

            # Run security workflow components
            error_handler_result = self._run_script(
                "scripts/cicd_error_handler.py", ["--workflow-name", "test-security", "--verbose"]
            )

            monitoring_result = self._run_script(
                "scripts/cicd_monitoring.py",
                ["--workflow-name", "test-security", "--test-monitoring", "--verbose"],
            )

            # All should succeed with valid files
            yaml_success = yaml_result.returncode == 0
            error_handler_success = error_handler_result.returncode == 0
            monitoring_success = monitoring_result.returncode == 0

            overall_success = yaml_success and error_handler_success and monitoring_success

            details = {
                "yaml_validation_success": yaml_success,
                "error_handler_success": error_handler_success,
                "monitoring_success": monitoring_success,
                "yaml_return_code": yaml_result.returncode,
                "error_handler_return_code": error_handler_result.returncode,
                "monitoring_return_code": monitoring_result.returncode,
                "yaml_output": yaml_result.stdout[:200] + "..."
                if len(yaml_result.stdout) > 200
                else yaml_result.stdout,
            }

            self._record_test_result(test_name, overall_success, details)
            return overall_success

        except Exception as e:
            self._record_test_result(test_name, False, {"error": str(e)})
            return False

    def test_error_handling_with_yaml_corruption(self) -> bool:
        """Test that error handling doesn't interfere when YAML files are corrupted."""
        test_name = "Error Handling with YAML Corruption"

        try:
            # Create corrupted security files
            self._create_test_security_files("corrupted")

            # Run YAML validation with graceful degradation
            yaml_result = self._run_script(
                "scripts/validate_security_yaml.py",
                ["--graceful-degradation", "--create-fallback", "--verbose"],
            )

            # Run error handler - should handle YAML corruption gracefully
            error_handler_result = self._run_script(
                "scripts/cicd_error_handler.py", ["--workflow-name", "test-security", "--verbose"]
            )

            # YAML validation should activate degradation
            yaml_degradation_activated = "degradation" in yaml_result.stdout.lower()

            # Error handler should complete (may have warnings but shouldn't crash)
            error_handler_completed = error_handler_result.returncode in [0, 1]  # Allow warnings

            success = yaml_degradation_activated and error_handler_completed

            details = {
                "yaml_degradation_activated": yaml_degradation_activated,
                "error_handler_completed": error_handler_completed,
                "yaml_return_code": yaml_result.returncode,
                "error_handler_return_code": error_handler_result.returncode,
                "yaml_output": yaml_result.stdout[:200] + "..."
                if len(yaml_result.stdout) > 200
                else yaml_result.stdout,
                "error_handler_output": error_handler_result.stdout[:200] + "..."
                if len(error_handler_result.stdout) > 200
                else error_handler_result.stdout,
            }

            self._record_test_result(test_name, success, details)
            return success

        except Exception as e:
            self._record_test_result(test_name, False, {"error": str(e)})
            return False

    def test_fallback_mechanisms_with_corrupted_data(self) -> bool:
        """Test that fallback mechanisms work correctly when data files are corrupted."""
        test_name = "Fallback Mechanisms with Corrupted Data"

        try:
            # Create corrupted security files
            self._create_test_security_files("corrupted")

            # Run YAML validation with emergency file creation
            yaml_result = self._run_script(
                "scripts/validate_security_yaml.py",
                ["--degraded-mode", "--create-emergency-files", "--verbose"],
            )

            # Check if emergency files were created
            emergency_files = [
                "security/findings/remediation-timeline.yml",
                "security/findings/remediation-plans.yml",
            ]

            emergency_files_created = []
            for file_path in emergency_files:
                full_path = self.project_dir / file_path
                if full_path.exists():
                    try:
                        with full_path.open() as f:
                            yaml.safe_load(f)
                        emergency_files_created.append(file_path)
                    except yaml.YAMLError:
                        pass

            # Run error handler with emergency files
            error_handler_result = self._run_script(
                "scripts/cicd_error_handler.py", ["--workflow-name", "test-security", "--verbose"]
            )

            # Run monitoring with fallback data
            monitoring_result = self._run_script(
                "scripts/cicd_monitoring.py",
                ["--workflow-name", "test-security", "--test-monitoring", "--verbose"],
            )

            fallback_successful = len(emergency_files_created) > 0
            workflows_continued = error_handler_result.returncode in [
                0,
                1,
            ] and monitoring_result.returncode in [0, 1]

            success = fallback_successful and workflows_continued

            details = {
                "fallback_successful": fallback_successful,
                "workflows_continued": workflows_continued,
                "emergency_files_created": emergency_files_created,
                "yaml_return_code": yaml_result.returncode,
                "error_handler_return_code": error_handler_result.returncode,
                "monitoring_return_code": monitoring_result.returncode,
            }

            self._record_test_result(test_name, success, details)
            return success

        except Exception as e:
            self._record_test_result(test_name, False, {"error": str(e)})
            return False

    def test_workflow_performance_impact(self) -> bool:
        """Test that YAML validation doesn't significantly impact workflow performance."""
        test_name = "Workflow Performance Impact"

        try:
            # Create valid security files
            self._create_test_security_files("valid")

            # Measure workflow execution time without YAML validation
            start_time = time.time()
            baseline_result = self._run_script(
                "scripts/cicd_error_handler.py", ["--workflow-name", "test-security", "--verbose"]
            )
            baseline_time = time.time() - start_time

            # Measure workflow execution time with YAML validation
            start_time = time.time()

            # Run YAML validation first
            yaml_result = self._run_script(
                "scripts/validate_security_yaml.py", ["--check", "--verbose"]
            )

            # Then run error handler
            with_yaml_result = self._run_script(
                "scripts/cicd_error_handler.py", ["--workflow-name", "test-security", "--verbose"]
            )

            with_yaml_time = time.time() - start_time

            # Calculate performance impact
            performance_impact = (
                ((with_yaml_time - baseline_time) / baseline_time) * 100 if baseline_time > 0 else 0
            )

            # Performance impact should be reasonable (less than 50% increase)
            performance_acceptable = performance_impact < 50.0

            # Both executions should succeed
            baseline_success = baseline_result.returncode == 0
            with_yaml_success = yaml_result.returncode == 0 and with_yaml_result.returncode == 0

            success = performance_acceptable and baseline_success and with_yaml_success

            details = {
                "baseline_time": baseline_time,
                "with_yaml_time": with_yaml_time,
                "performance_impact_percent": performance_impact,
                "performance_acceptable": performance_acceptable,
                "baseline_success": baseline_success,
                "with_yaml_success": with_yaml_success,
            }

            self._record_test_result(test_name, success, details)
            return success

        except Exception as e:
            self._record_test_result(test_name, False, {"error": str(e)})
            return False

    def test_workflow_coordination_with_yaml_validation(self) -> bool:
        """Test coordination between multiple workflow components with YAML validation."""
        test_name = "Workflow Coordination with YAML Validation"

        try:
            # Create mixed scenario (some valid, some corrupted)
            self._create_test_security_files("mixed")

            # Run complete workflow sequence
            workflow_steps = [
                (
                    "YAML Validation",
                    "scripts/validate_security_yaml.py",
                    ["--repair", "--graceful-degradation", "--verbose"],
                ),
                (
                    "Error Handling",
                    "scripts/cicd_error_handler.py",
                    ["--workflow-name", "test-security", "--verbose"],
                ),
                (
                    "Monitoring",
                    "scripts/cicd_monitoring.py",
                    ["--workflow-name", "test-security", "--test-monitoring", "--verbose"],
                ),
            ]

            step_results = []
            overall_success = True

            for step_name, script_path, args in workflow_steps:
                result = self._run_script(script_path, args)
                step_success = result.returncode in [0, 1]  # Allow warnings
                step_results.append(
                    {
                        "step": step_name,
                        "success": step_success,
                        "return_code": result.returncode,
                        "output_length": len(result.stdout),
                    }
                )

                if not step_success:
                    overall_success = False

                if self.verbose:
                    print(f"    {step_name}: {'✅' if step_success else '❌'}")

            # Check that workflow coordination worked
            coordination_successful = all(step["success"] for step in step_results)

            success = coordination_successful

            details = {
                "coordination_successful": coordination_successful,
                "step_results": step_results,
                "total_steps": len(workflow_steps),
                "successful_steps": sum(1 for step in step_results if step["success"]),
            }

            self._record_test_result(test_name, success, details)
            return success

        except Exception as e:
            self._record_test_result(test_name, False, {"error": str(e)})
            return False

    def test_error_propagation_and_handling(self) -> bool:
        """Test that errors are properly propagated and handled across workflow components."""
        test_name = "Error Propagation and Handling"

        try:
            # Create severely corrupted files that should trigger error handling
            security_dir = self.project_dir / "security" / "findings"

            # Create files that will cause validation errors
            severely_corrupted = """timeline:
  - timestamp: invalid_format
    action: [malformed, structure
    finding_id: {broken: yaml
metadata:
  corrupted: true
  structure: [incomplete
"""

            (security_dir / "remediation-timeline.yml").write_text(severely_corrupted)
            (security_dir / "remediation-plans.yml").write_text("completely: [broken: yaml")

            # Run YAML validation - should detect errors
            yaml_result = self._run_script(
                "scripts/validate_security_yaml.py", ["--check", "--verbose"]
            )

            # Run with graceful degradation - should handle errors
            degradation_result = self._run_script(
                "scripts/validate_security_yaml.py",
                ["--graceful-degradation", "--create-emergency-files", "--verbose"],
            )

            # Run error handler - should process the error conditions
            error_handler_result = self._run_script(
                "scripts/cicd_error_handler.py", ["--workflow-name", "test-security", "--verbose"]
            )

            # Validation should detect errors
            errors_detected = yaml_result.returncode != 0

            # Degradation should activate
            degradation_activated = (
                "degradation" in degradation_result.stdout.lower()
                or degradation_result.returncode == 0
            )

            # Error handler should complete (may have warnings)
            error_handling_completed = error_handler_result.returncode in [0, 1]

            success = errors_detected and degradation_activated and error_handling_completed

            details = {
                "errors_detected": errors_detected,
                "degradation_activated": degradation_activated,
                "error_handling_completed": error_handling_completed,
                "yaml_check_return_code": yaml_result.returncode,
                "degradation_return_code": degradation_result.returncode,
                "error_handler_return_code": error_handler_result.returncode,
            }

            self._record_test_result(test_name, success, details)
            return success

        except Exception as e:
            self._record_test_result(test_name, False, {"error": str(e)})
            return False

    def test_workflow_resilience_to_yaml_issues(self) -> bool:
        """Test that workflows are resilient to various YAML issues."""
        test_name = "Workflow Resilience to YAML Issues"

        try:
            # Test multiple YAML issue scenarios
            yaml_scenarios = [
                (
                    "indentation_error",
                    """timeline:
  - timestamp: "2025-01-01T00:00:00Z"
   action: "test"  # Wrong indentation
metadata:
  version: "1.0"
""",
                ),
                (
                    "structure_error",
                    """timeline:
  - timestamp: "2025-01-01T00:00:00Z"
    # Missing required fields
metadata:
  # Incomplete structure
""",
                ),
                (
                    "syntax_error",
                    """timeline:
  - timestamp: "2025-01-01T00:00:00Z
    action: "test  # Missing quotes
metadata:
  version: 1.0
""",
                ),
            ]

            resilience_results = []

            for scenario_name, yaml_content in yaml_scenarios:
                # Create scenario-specific files
                security_dir = self.project_dir / "security" / "findings"
                test_file = security_dir / f"{scenario_name}.yml"
                test_file.write_text(yaml_content)

                # Test YAML validation with this scenario
                yaml_result = self._run_script(
                    "scripts/validate_security_yaml.py", ["--graceful-degradation", "--verbose"]
                )

                # Test error handler resilience
                error_result = self._run_script(
                    "scripts/cicd_error_handler.py",
                    ["--workflow-name", f"test-{scenario_name}", "--verbose"],
                )

                scenario_resilient = (
                    yaml_result.returncode in [0, 1]  # May have warnings but shouldn't crash
                    and error_result.returncode in [0, 1]  # Should handle gracefully
                )

                resilience_results.append(
                    {
                        "scenario": scenario_name,
                        "resilient": scenario_resilient,
                        "yaml_return_code": yaml_result.returncode,
                        "error_return_code": error_result.returncode,
                    }
                )

                # Clean up scenario file
                if test_file.exists():
                    test_file.unlink()

            # Overall resilience - all scenarios should be handled
            overall_resilience = all(result["resilient"] for result in resilience_results)

            success = overall_resilience

            details = {
                "overall_resilience": overall_resilience,
                "scenarios_tested": len(yaml_scenarios),
                "resilient_scenarios": sum(1 for r in resilience_results if r["resilient"]),
                "scenario_results": resilience_results,
            }

            self._record_test_result(test_name, success, details)
            return success

        except Exception as e:
            self._record_test_result(test_name, False, {"error": str(e)})
            return False

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all security workflow integration tests.

        Returns:
            Dictionary with test results summary
        """
        if self.verbose:
            print("🔍 Starting security workflow integration tests...")

        # Set up test environment
        self.setup_test_environment()

        try:
            # Run all tests
            tests = [
                self.test_yaml_validation_with_normal_security_workflow,
                self.test_error_handling_with_yaml_corruption,
                self.test_fallback_mechanisms_with_corrupted_data,
                self.test_workflow_performance_impact,
                self.test_workflow_coordination_with_yaml_validation,
                self.test_error_propagation_and_handling,
                self.test_workflow_resilience_to_yaml_issues,
            ]

            passed_tests = 0
            total_tests = len(tests)

            for test_func in tests:
                if test_func():
                    passed_tests += 1

            # Generate summary
            success_rate = (passed_tests / total_tests) * 100
            overall_success = passed_tests == total_tests

            summary = {
                "overall_success": overall_success,
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": success_rate,
                "test_results": self.test_results,
                "timestamp": time.time(),
            }

            if self.verbose:
                print("\n📊 Integration Test Summary:")
                print(f"   Total Tests: {total_tests}")
                print(f"   Passed: {passed_tests}")
                print(f"   Failed: {total_tests - passed_tests}")
                print(f"   Success Rate: {success_rate:.1f}%")
                print(f"   Overall: {'✅ PASS' if overall_success else '❌ FAIL'}")

            return summary

        finally:
            # Clean up test environment
            self.cleanup_test_environment()

    def generate_report(self, output_file: str = None) -> str:
        """Generate detailed integration test report.

        Args:
            output_file: Optional file to write report to

        Returns:
            Report content as string
        """
        if not self.test_results:
            return "No test results available"

        # Calculate summary statistics
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0

        # Generate report
        report_lines = [
            "# Security Workflow Integration Test Report",
            "",
            f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
            f"**Total Tests**: {total_tests}",
            f"**Passed**: {passed_tests}",
            f"**Failed**: {failed_tests}",
            f"**Success Rate**: {success_rate:.1f}%",
            "",
            "## Test Results",
            "",
        ]

        for result in self.test_results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            report_lines.extend(
                [
                    f"### {result['test_name']}",
                    f"**Status**: {status}",
                    f"**Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(result['timestamp']))}",
                    "",
                ]
            )

            if result["details"]:
                report_lines.append("**Details**:")
                for key, value in result["details"].items():
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:100] + "..."
                    elif isinstance(value, list) and len(str(value)) > 100:
                        value = f"[{len(value)} items]"
                    report_lines.append(f"- {key}: {value}")
                report_lines.append("")

        report_content = "\n".join(report_lines)

        if output_file:
            Path(output_file).write_text(report_content)
            if self.verbose:
                print(f"📄 Integration report written to: {output_file}")

        return report_content


def main() -> int:
    """Main entry point for integration testing script."""
    parser = argparse.ArgumentParser(
        description="Test YAML validation integration with security workflows"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--report", "-r", type=str, help="Generate detailed report to specified file"
    )
    parser.add_argument(
        "--json-output", "-j", type=str, help="Output results as JSON to specified file"
    )

    args = parser.parse_args()

    try:
        # Run integration tests
        tester = SecurityWorkflowIntegrationTester(verbose=args.verbose)
        summary = tester.run_all_tests()

        # Generate report if requested
        if args.report:
            tester.generate_report(args.report)

        # Output JSON results if requested
        if args.json_output:
            with open(args.json_output, "w") as f:
                json.dump(summary, f, indent=2)
            if args.verbose:
                print(f"📄 JSON results written to: {args.json_output}")

        # Return appropriate exit code
        return 0 if summary["overall_success"] else 1

    except KeyboardInterrupt:
        print("\n⚠️  Integration testing interrupted by user", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
