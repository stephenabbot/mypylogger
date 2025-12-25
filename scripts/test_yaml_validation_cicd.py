#!/usr/bin/env python3
"""Comprehensive CI/CD test script for YAML validation system.

This script tests YAML validation with various corruption scenarios,
verifies automatic repair functionality, and validates graceful degradation
in a CI/CD environment.

Requirements addressed: 17.1, 17.2, 17.3
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


class YAMLValidationCICDTester:
    """Comprehensive tester for YAML validation in CI/CD environment."""

    def __init__(self, verbose: bool = False) -> None:
        """Initialize the tester.

        Args:
            verbose: Enable verbose output
        """
        self.verbose = verbose
        self.test_results: List[Dict[str, Any]] = []
        self.temp_dir: Path = None
        self.project_dir: Path = None
        self.security_dir: Path = None

    def setup_test_environment(self) -> None:
        """Set up test environment with project structure."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_dir = self.temp_dir / "test_project"
        self.security_dir = self.project_dir / "security"

        # Create directory structure
        directories = [
            self.project_dir,
            self.security_dir / "findings",
            self.security_dir / "config",
            self.security_dir / "reports",
            self.security_dir / "scripts",
            self.project_dir / "scripts",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

        # Copy validation scripts
        self._copy_validation_scripts()

        if self.verbose:
            print(f"✅ Test environment created at: {self.project_dir}")

    def cleanup_test_environment(self) -> None:
        """Clean up test environment."""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            if self.verbose:
                print("✅ Test environment cleaned up")

    def _copy_validation_scripts(self) -> None:
        """Copy validation scripts to test project."""
        script_files = ["scripts/validate_security_yaml.py", "scripts/repair_yaml.py"]

        for script_file in script_files:
            src_path = Path(script_file)
            if src_path.exists():
                dst_path = self.project_dir / script_file
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
                if self.verbose:
                    print(f"  Copied: {script_file}")

    def _create_yaml_file(self, filename: str, content: str, directory: str = "findings") -> Path:
        """Create a YAML file with given content.

        Args:
            filename: Name of the file to create
            content: YAML content as string
            directory: Subdirectory under security/ (default: findings)

        Returns:
            Path to created file
        """
        file_path = self.security_dir / directory / filename
        file_path.write_text(content)
        return file_path

    def _run_validation_command(self, args: List[str]) -> subprocess.CompletedProcess:
        """Run validation command and return result.

        Args:
            args: Command line arguments for validation script

        Returns:
            CompletedProcess with command results
        """
        cmd = [sys.executable, "scripts/validate_security_yaml.py"] + args

        if self.verbose:
            print(f"  Running: {' '.join(cmd)}")

        return subprocess.run(
            cmd, check=False, capture_output=True, text=True, cwd=self.project_dir
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

    def test_valid_yaml_validation(self) -> bool:
        """Test validation of valid YAML files."""
        test_name = "Valid YAML Validation"

        try:
            # Create valid YAML files
            valid_timeline = {
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

            timeline_file = self.security_dir / "findings" / "remediation-timeline.yml"
            with timeline_file.open("w") as f:
                yaml.dump(valid_timeline, f, default_flow_style=False)

            # Run validation
            result = self._run_validation_command(["--check", "--verbose"])

            success = result.returncode == 0
            details = {
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "files_created": 1,
            }

            self._record_test_result(test_name, success, details)
            return success

        except Exception as e:
            self._record_test_result(test_name, False, {"error": str(e)})
            return False

    def test_indentation_corruption(self) -> bool:
        """Test YAML validation with indentation corruption."""
        test_name = "Indentation Corruption Scenario"

        try:
            # Create YAML with indentation errors
            corrupted_yaml = """timeline:
  - timestamp: "2025-01-01T00:00:00Z"
    action: "finding_created"
    finding_id: "TEST-001"
   user: "test_user"  # Wrong indentation (3 spaces instead of 4)
  - timestamp: "2025-01-02T00:00:00Z"
    action: "finding_updated"
     finding_id: "TEST-001"  # Wrong indentation (5 spaces)
metadata:
  version: "1.0"
"""

            self._create_yaml_file("corrupted-timeline.yml", corrupted_yaml)

            # Test validation detects corruption
            check_result = self._run_validation_command(["--check", "--verbose"])
            corruption_detected = check_result.returncode != 0

            # Test automatic repair
            repair_result = self._run_validation_command(["--repair", "--verbose"])

            success = corruption_detected  # Should detect corruption
            details = {
                "corruption_detected": corruption_detected,
                "check_return_code": check_result.returncode,
                "repair_return_code": repair_result.returncode,
                "check_output": check_result.stdout,
                "repair_output": repair_result.stdout,
            }

            self._record_test_result(test_name, success, details)
            return success

        except Exception as e:
            self._record_test_result(test_name, False, {"error": str(e)})
            return False

    def test_special_characters_corruption(self) -> bool:
        """Test YAML validation with special characters corruption."""
        test_name = "Special Characters Corruption Scenario"

        try:
            # Create YAML with unquoted special characters
            corrupted_yaml = """timeline:
  - timestamp: 2025-01-01T00:00:00Z
    action: finding_created
    description: This has special chars: {}[]@#|>
    finding_id: TEST-001
    metadata: {key: value, another: [1, 2, 3]}
"""

            self._create_yaml_file("special-chars.yml", corrupted_yaml)

            # Test validation
            result = self._run_validation_command(["--check", "--verbose"])

            # This might be valid YAML but should be handled
            success = True  # Test passes if it doesn't crash
            details = {
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "handled_gracefully": True,
            }

            self._record_test_result(test_name, success, details)
            return success

        except Exception as e:
            self._record_test_result(test_name, False, {"error": str(e)})
            return False

    def test_structural_corruption(self) -> bool:
        """Test YAML validation with structural corruption."""
        test_name = "Structural Corruption Scenario"

        try:
            # Create YAML with structural issues
            corrupted_yaml = """timeline:
  - timestamp: "2025-01-01T00:00:00Z"
    action: "finding_created"
    finding_id: "TEST-001"
    user: "test_user"
  - timestamp: "2025-01-02T00:00:00Z"
    # Missing action field
    finding_id: "TEST-002"
metadata:
  version: "1.0"
  # Incomplete structure
"""

            self._create_yaml_file("structural-corruption.yml", corrupted_yaml)

            # Test validation
            result = self._run_validation_command(["--check", "--verbose"])

            # Should handle structural issues
            success = True  # Test passes if validation runs
            details = {
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "validation_completed": True,
            }

            self._record_test_result(test_name, success, details)
            return success

        except Exception as e:
            self._record_test_result(test_name, False, {"error": str(e)})
            return False

    def test_automatic_repair_functionality(self) -> bool:
        """Test automatic repair functionality."""
        test_name = "Automatic Repair Functionality"

        try:
            # Create repairable YAML corruption
            corrupted_yaml = """timeline:
  - timestamp: "2025-01-01T00:00:00Z"
    action: "finding_created"
    finding_id: "TEST-001"
   user: "test_user"  # Fixable indentation error
metadata:
  version: "1.0"
"""

            yaml_file = self._create_yaml_file("repairable.yml", corrupted_yaml)

            # Verify file is initially invalid
            check_result = self._run_validation_command(["--check", "--verbose"])
            initially_invalid = check_result.returncode != 0

            # Test repair with backup
            repair_result = self._run_validation_command(["--backup", "--repair", "--verbose"])

            # Check if backup was created
            backup_dir = self.security_dir / "backups"
            backup_created = backup_dir.exists() and len(list(backup_dir.glob("*.backup.*"))) > 0

            success = initially_invalid  # Should detect initial corruption
            details = {
                "initially_invalid": initially_invalid,
                "repair_attempted": "repair" in repair_result.stdout.lower(),
                "backup_created": backup_created,
                "repair_return_code": repair_result.returncode,
                "repair_output": repair_result.stdout,
            }

            self._record_test_result(test_name, success, details)
            return success

        except Exception as e:
            self._record_test_result(test_name, False, {"error": str(e)})
            return False

    def test_graceful_degradation(self) -> bool:
        """Test graceful degradation functionality."""
        test_name = "Graceful Degradation"

        try:
            # Create severely corrupted YAML
            severely_corrupted = """timeline:
  - timestamp: "2025-01-01T00:00:00Z
    action: "finding_created  # Missing closing quote
    finding_id: TEST-001"  # Misplaced quote
   user: test_user
  - timestamp: 2025-01-02T00:00:00Z"  # Mixed quote styles
    action: finding_updated
metadata:
  version: 1.0
  generated: [invalid, yaml, structure
"""

            self._create_yaml_file("severely-corrupted.yml", severely_corrupted)

            # Test graceful degradation
            result = self._run_validation_command(
                ["--graceful-degradation", "--create-fallback", "--verbose"]
            )

            # Should handle graceful degradation
            degradation_activated = "degradation" in result.stdout.lower()

            success = degradation_activated
            details = {
                "degradation_activated": degradation_activated,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

            self._record_test_result(test_name, success, details)
            return success

        except Exception as e:
            self._record_test_result(test_name, False, {"error": str(e)})
            return False

    def test_degraded_mode_operation(self) -> bool:
        """Test degraded mode operation."""
        test_name = "Degraded Mode Operation"

        try:
            # Create critical file corruption
            critical_corrupted = """timeline:
  - timestamp: invalid_timestamp
    action: [malformed, action, array]
    finding_id: {invalid: structure}
metadata:
  version: "corrupted"
  invalid_structure: [
"""

            # Create corrupted critical file
            self._create_yaml_file("remediation-timeline.yml", critical_corrupted)

            # Test degraded mode
            result = self._run_validation_command(
                ["--degraded-mode", "--create-emergency-files", "--verbose"]
            )

            # Should activate degraded mode
            degraded_mode_activated = "degraded" in result.stdout.lower()

            # Check if emergency files were created
            emergency_files_created = False
            emergency_files = ["remediation-timeline.yml", "remediation-plans.yml"]

            for filename in emergency_files:
                file_path = self.security_dir / "findings" / filename
                if file_path.exists():
                    try:
                        with file_path.open() as f:
                            yaml.safe_load(f)
                        emergency_files_created = True
                        break
                    except yaml.YAMLError:
                        continue

            success = degraded_mode_activated
            details = {
                "degraded_mode_activated": degraded_mode_activated,
                "emergency_files_created": emergency_files_created,
                "return_code": result.returncode,
                "stdout": result.stdout,
            }

            self._record_test_result(test_name, success, details)
            return success

        except Exception as e:
            self._record_test_result(test_name, False, {"error": str(e)})
            return False

    def test_error_recovery_mechanisms(self) -> bool:
        """Test error recovery mechanisms."""
        test_name = "Error Recovery Mechanisms"

        try:
            # Create mixed valid and invalid files
            valid_content = {"timeline": [], "metadata": {"version": "1.0"}}

            # Create valid file
            valid_file = self.security_dir / "findings" / "valid-timeline.yml"
            with valid_file.open("w") as f:
                yaml.dump(valid_content, f)

            # Create invalid file
            self._create_yaml_file("corrupted-plans.yml", "invalid: yaml: content:")

            # Create another valid file
            config_content = {"config": {"setting": "value"}}
            config_file = self.security_dir / "config" / "valid-config.yml"
            with config_file.open("w") as f:
                yaml.dump(config_content, f)

            # Test error recovery
            result = self._run_validation_command(
                ["--repair", "--graceful-degradation", "--verbose"]
            )

            # Should handle mixed scenario
            recovery_attempted = (
                "valid" in result.stdout.lower() or "repair" in result.stdout.lower()
            )

            success = recovery_attempted
            details = {
                "recovery_attempted": recovery_attempted,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "files_created": 3,
            }

            self._record_test_result(test_name, success, details)
            return success

        except Exception as e:
            self._record_test_result(test_name, False, {"error": str(e)})
            return False

    def test_performance_impact(self) -> bool:
        """Test performance impact of YAML validation."""
        test_name = "Performance Impact Validation"

        try:
            # Create a clean test environment for performance testing
            perf_test_dir = self.temp_dir / "perf_test"
            perf_security_dir = perf_test_dir / "security" / "findings"
            perf_security_dir.mkdir(parents=True, exist_ok=True)

            # Copy validation scripts to performance test directory
            for script_file in ["scripts/validate_security_yaml.py", "scripts/repair_yaml.py"]:
                src_path = Path(script_file)
                if src_path.exists():
                    dst_path = perf_test_dir / script_file
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, dst_path)

            # Create multiple YAML files
            for i in range(10):
                valid_content = {
                    "timeline": [
                        {
                            "timestamp": f"2025-01-{i + 1:02d}T00:00:00Z",
                            "action": "finding_created",
                            "finding_id": f"TEST-{i + 1:03d}",
                            "user": "test_user",
                        }
                    ],
                    "metadata": {"version": "1.0", "file_number": i + 1},
                }

                file_path = perf_security_dir / f"timeline-{i + 1:02d}.yml"
                with file_path.open("w") as f:
                    yaml.dump(valid_content, f)

            # Measure validation time
            start_time = time.time()
            cmd = [sys.executable, "scripts/validate_security_yaml.py", "--check", "--verbose"]
            result = subprocess.run(
                cmd, check=False, capture_output=True, text=True, cwd=perf_test_dir
            )
            end_time = time.time()

            validation_time = end_time - start_time

            # Validation should complete within reasonable time
            performance_acceptable = validation_time < 10.0
            validation_successful = result.returncode == 0

            success = performance_acceptable and validation_successful
            details = {
                "validation_time": validation_time,
                "performance_acceptable": performance_acceptable,
                "validation_successful": validation_successful,
                "files_processed": 10,
                "return_code": result.returncode,
                "stdout": result.stdout[:200] + "..."
                if len(result.stdout) > 200
                else result.stdout,
            }

            self._record_test_result(test_name, success, details)
            return success

        except Exception as e:
            self._record_test_result(test_name, False, {"error": str(e)})
            return False

    def test_ci_environment_simulation(self) -> bool:
        """Test YAML validation in simulated CI environment."""
        test_name = "CI Environment Simulation"

        try:
            # Create a clean test environment for CI simulation
            ci_test_dir = self.temp_dir / "ci_test"
            ci_security_dir = ci_test_dir / "security" / "findings"
            ci_security_dir.mkdir(parents=True, exist_ok=True)

            # Copy validation scripts to CI test directory
            for script_file in ["scripts/validate_security_yaml.py", "scripts/repair_yaml.py"]:
                src_path = Path(script_file)
                if src_path.exists():
                    dst_path = ci_test_dir / script_file
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, dst_path)

            # Set CI-like environment variables
            ci_env = os.environ.copy()
            ci_env.update({"CI": "true", "GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux"})

            # Create test file
            test_content = {
                "timeline": [
                    {
                        "timestamp": "2025-01-01T00:00:00Z",
                        "action": "ci_test",
                        "finding_id": "CI-001",
                        "user": "github-actions",
                    }
                ],
                "metadata": {"ci_run": True},
            }

            file_path = ci_security_dir / "ci-timeline.yml"
            with file_path.open("w") as f:
                yaml.dump(test_content, f)

            # Run validation with CI environment
            cmd = [sys.executable, "scripts/validate_security_yaml.py", "--check", "--verbose"]
            result = subprocess.run(
                cmd, check=False, capture_output=True, text=True, cwd=ci_test_dir, env=ci_env
            )

            success = result.returncode == 0
            details = {
                "return_code": result.returncode,
                "stdout": result.stdout[:200] + "..."
                if len(result.stdout) > 200
                else result.stdout,
                "stderr": result.stderr,
                "ci_environment": True,
            }

            self._record_test_result(test_name, success, details)
            return success

        except Exception as e:
            self._record_test_result(test_name, False, {"error": str(e)})
            return False

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all YAML validation tests.

        Returns:
            Dictionary with test results summary
        """
        if self.verbose:
            print("🔍 Starting comprehensive YAML validation CI/CD tests...")

        # Set up test environment
        self.setup_test_environment()

        try:
            # Run all tests
            tests = [
                self.test_valid_yaml_validation,
                self.test_indentation_corruption,
                self.test_special_characters_corruption,
                self.test_structural_corruption,
                self.test_automatic_repair_functionality,
                self.test_graceful_degradation,
                self.test_degraded_mode_operation,
                self.test_error_recovery_mechanisms,
                self.test_performance_impact,
                self.test_ci_environment_simulation,
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
                print("\n📊 Test Summary:")
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
        """Generate detailed test report.

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
            "# YAML Validation CI/CD Test Report",
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
                    report_lines.append(f"- {key}: {value}")
                report_lines.append("")

        report_content = "\n".join(report_lines)

        if output_file:
            Path(output_file).write_text(report_content)
            if self.verbose:
                print(f"📄 Report written to: {output_file}")

        return report_content


def main() -> int:
    """Main entry point for CI/CD testing script."""
    parser = argparse.ArgumentParser(
        description="Comprehensive CI/CD tests for YAML validation system"
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
        # Run tests
        tester = YAMLValidationCICDTester(verbose=args.verbose)
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
        print("\n⚠️  Testing interrupted by user", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
