#!/usr/bin/env python3
"""Simplified integration test for YAML validation with security workflows.

Tests core integration functionality without complex dependencies.
Focuses on validating that YAML validation integrates properly with
security workflows and doesn't interfere with normal operations.

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


class SimpleYAMLIntegrationTester:
    """Simple integration tester for YAML validation with security workflows."""

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
        """Set up minimal test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_dir = self.temp_dir / "test_project"

        # Create minimal directory structure
        directories = [
            self.project_dir,
            self.project_dir / "security" / "findings",
            self.project_dir / "security" / "config",
            self.project_dir / "scripts",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

        # Copy only essential scripts
        essential_scripts = ["scripts/validate_security_yaml.py", "scripts/repair_yaml.py"]

        for script_file in essential_scripts:
            src_path = Path(script_file)
            if src_path.exists():
                dst_path = self.project_dir / script_file
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
                if self.verbose:
                    print(f"  Copied: {script_file}")

        if self.verbose:
            print(f"✅ Test environment created at: {self.project_dir}")

    def cleanup_test_environment(self) -> None:
        """Clean up test environment."""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            if self.verbose:
                print("✅ Test environment cleaned up")

    def _create_security_files(self, scenario: str) -> None:
        """Create security files for testing scenarios."""
        security_dir = self.project_dir / "security" / "findings"

        if scenario == "valid":
            # Create valid YAML files
            timeline_content = {
                "timeline": [
                    {
                        "timestamp": "2025-01-01T00:00:00Z",
                        "action": "finding_created",
                        "finding_id": "TEST-001",
                        "user": "test_user",
                    }
                ],
                "metadata": {"version": "1.0"},
            }

            with (security_dir / "remediation-timeline.yml").open("w") as f:
                yaml.dump(timeline_content, f, default_flow_style=False)

        elif scenario == "corrupted":
            # Create corrupted YAML
            corrupted_yaml = """timeline:
  - timestamp: "2025-01-01T00:00:00Z
    action: "finding_created  # Missing closing quote
metadata:
  version: 1.0
"""
            (security_dir / "remediation-timeline.yml").write_text(corrupted_yaml)

    def _run_yaml_validation(self, args: List[str]) -> subprocess.CompletedProcess:
        """Run YAML validation script."""
        cmd = [sys.executable, "scripts/validate_security_yaml.py"] + args

        if self.verbose:
            print(f"  Running: {' '.join(cmd)}")

        return subprocess.run(
            cmd, check=False, capture_output=True, text=True, cwd=self.project_dir
        )

    def _record_test_result(self, test_name: str, success: bool, details: Dict[str, Any]) -> None:
        """Record test result."""
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

    def test_yaml_validation_normal_operation(self) -> bool:
        """Test YAML validation during normal security workflow operation."""
        test_name = "YAML Validation Normal Operation"

        try:
            # Create valid security files
            self._create_security_files("valid")

            # Test normal validation
            result = self._run_yaml_validation(["--check", "--verbose"])

            success = result.returncode == 0
            details = {
                "return_code": result.returncode,
                "validation_successful": success,
                "output_contains_valid": "valid" in result.stdout.lower(),
                "no_errors_in_stderr": len(result.stderr.strip()) == 0,
            }

            self._record_test_result(test_name, success, details)
            return success

        except Exception as e:
            self._record_test_result(test_name, False, {"error": str(e)})
            return False

    def test_yaml_validation_with_corruption(self) -> bool:
        """Test YAML validation handles corruption without blocking workflows."""
        test_name = "YAML Validation with Corruption"

        try:
            # Create corrupted security files
            self._create_security_files("corrupted")

            # Test validation detects corruption
            check_result = self._run_yaml_validation(["--check", "--verbose"])
            corruption_detected = check_result.returncode != 0

            # Test graceful degradation allows workflow to continue
            degradation_result = self._run_yaml_validation(
                ["--graceful-degradation", "--create-fallback", "--verbose"]
            )
            workflow_can_continue = degradation_result.returncode == 0

            success = corruption_detected and workflow_can_continue
            details = {
                "corruption_detected": corruption_detected,
                "workflow_can_continue": workflow_can_continue,
                "check_return_code": check_result.returncode,
                "degradation_return_code": degradation_result.returncode,
                "degradation_activated": "degradation" in degradation_result.stdout.lower(),
            }

            self._record_test_result(test_name, success, details)
            return success

        except Exception as e:
            self._record_test_result(test_name, False, {"error": str(e)})
            return False

    def test_yaml_repair_functionality(self) -> bool:
        """Test YAML repair functionality in workflow context."""
        test_name = "YAML Repair Functionality"

        try:
            # Create repairable corruption
            repairable_yaml = """timeline:
  - timestamp: "2025-01-01T00:00:00Z"
    action: "finding_created"
    finding_id: "TEST-001"
   user: "test_user"  # Wrong indentation
metadata:
  version: "1.0"
"""

            security_dir = self.project_dir / "security" / "findings"
            yaml_file = security_dir / "repairable.yml"
            yaml_file.write_text(repairable_yaml)

            # Test repair with backup
            repair_result = self._run_yaml_validation(["--backup", "--repair", "--verbose"])

            # Check if backup was created
            backup_dir = self.project_dir / "security" / "backups"
            backup_created = backup_dir.exists() and len(list(backup_dir.glob("*.backup.*"))) > 0

            success = "repair" in repair_result.stdout.lower()
            details = {
                "repair_attempted": success,
                "backup_created": backup_created,
                "return_code": repair_result.returncode,
                "repair_output_length": len(repair_result.stdout),
            }

            self._record_test_result(test_name, success, details)
            return success

        except Exception as e:
            self._record_test_result(test_name, False, {"error": str(e)})
            return False

    def test_emergency_file_creation(self) -> bool:
        """Test emergency file creation for critical workflow continuation."""
        test_name = "Emergency File Creation"

        try:
            # Create severely corrupted files
            severely_corrupted = """timeline:
  - timestamp: invalid_format
    action: [broken, yaml
metadata:
  corrupted: [structure
"""

            security_dir = self.project_dir / "security" / "findings"
            (security_dir / "remediation-timeline.yml").write_text(severely_corrupted)

            # Test emergency file creation
            emergency_result = self._run_yaml_validation(
                ["--degraded-mode", "--create-emergency-files", "--verbose"]
            )

            # Check if emergency files were created and are valid
            emergency_files_valid = []
            emergency_files = ["remediation-timeline.yml", "remediation-plans.yml"]

            for filename in emergency_files:
                file_path = security_dir / filename
                if file_path.exists():
                    try:
                        with file_path.open() as f:
                            yaml.safe_load(f)
                        emergency_files_valid.append(filename)
                    except yaml.YAMLError:
                        pass

            success = len(emergency_files_valid) > 0
            details = {
                "emergency_files_created": len(emergency_files_valid),
                "valid_emergency_files": emergency_files_valid,
                "return_code": emergency_result.returncode,
                "degraded_mode_activated": "degraded" in emergency_result.stdout.lower(),
            }

            self._record_test_result(test_name, success, details)
            return success

        except Exception as e:
            self._record_test_result(test_name, False, {"error": str(e)})
            return False

    def test_workflow_performance_impact(self) -> bool:
        """Test that YAML validation has acceptable performance impact."""
        test_name = "Workflow Performance Impact"

        try:
            # Clean up any existing files first
            security_dir = self.project_dir / "security" / "findings"
            for existing_file in security_dir.glob("*.yml"):
                existing_file.unlink()

            # Create multiple valid files for performance testing
            for i in range(5):
                content = {
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

                with (security_dir / f"perf-timeline-{i + 1:02d}.yml").open("w") as f:
                    yaml.dump(content, f)

            # Measure validation time
            start_time = time.time()
            result = self._run_yaml_validation(["--check", "--verbose"])
            validation_time = time.time() - start_time

            # Performance should be reasonable (under 5 seconds for 5 files)
            performance_acceptable = validation_time < 5.0
            validation_successful = result.returncode == 0

            success = performance_acceptable and validation_successful
            details = {
                "validation_time": validation_time,
                "performance_acceptable": performance_acceptable,
                "validation_successful": validation_successful,
                "files_processed": 5,
                "stdout_snippet": result.stdout[:200] + "..."
                if len(result.stdout) > 200
                else result.stdout,
            }

            self._record_test_result(test_name, success, details)
            return success

        except Exception as e:
            self._record_test_result(test_name, False, {"error": str(e)})
            return False

    def test_workflow_error_handling(self) -> bool:
        """Test that YAML validation errors are handled gracefully in workflows."""
        test_name = "Workflow Error Handling"

        try:
            # Create mixed scenario
            security_dir = self.project_dir / "security" / "findings"

            # Valid file
            valid_content = {"timeline": [], "metadata": {"version": "1.0"}}
            with (security_dir / "valid.yml").open("w") as f:
                yaml.dump(valid_content, f)

            # Invalid file
            (security_dir / "invalid.yml").write_text("invalid: yaml: content:")

            # Test that validation handles mixed scenario
            result = self._run_yaml_validation(["--repair", "--graceful-degradation", "--verbose"])

            # Should handle gracefully (may have warnings but shouldn't crash)
            handled_gracefully = result.returncode in [0, 1]
            contains_valid_info = "valid" in result.stdout.lower()

            success = handled_gracefully and contains_valid_info
            details = {
                "handled_gracefully": handled_gracefully,
                "contains_valid_info": contains_valid_info,
                "return_code": result.returncode,
                "output_length": len(result.stdout),
            }

            self._record_test_result(test_name, success, details)
            return success

        except Exception as e:
            self._record_test_result(test_name, False, {"error": str(e)})
            return False

    def test_ci_environment_compatibility(self) -> bool:
        """Test YAML validation compatibility with CI environment."""
        test_name = "CI Environment Compatibility"

        try:
            # Clean up any existing files first
            security_dir = self.project_dir / "security" / "findings"
            for existing_file in security_dir.glob("*.yml"):
                existing_file.unlink()

            # Create fresh test files
            self._create_security_files("valid")

            # Set CI environment variables
            ci_env = os.environ.copy()
            ci_env.update({"CI": "true", "GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux"})

            # Run validation in CI environment
            cmd = [sys.executable, "scripts/validate_security_yaml.py", "--check", "--verbose"]
            result = subprocess.run(
                cmd, check=False, capture_output=True, text=True, cwd=self.project_dir, env=ci_env
            )

            success = result.returncode == 0
            details = {
                "ci_compatible": success,
                "return_code": result.returncode,
                "output_contains_validation": "validation" in result.stdout.lower(),
                "no_ci_specific_errors": "CI" not in result.stderr,
                "stdout_snippet": result.stdout[:200] + "..."
                if len(result.stdout) > 200
                else result.stdout,
                "stderr_content": result.stderr,
            }

            self._record_test_result(test_name, success, details)
            return success

        except Exception as e:
            self._record_test_result(test_name, False, {"error": str(e)})
            return False

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all simplified integration tests."""
        if self.verbose:
            print("🔍 Starting simplified YAML integration tests...")

        # Set up test environment
        self.setup_test_environment()

        try:
            # Run all tests
            tests = [
                self.test_yaml_validation_normal_operation,
                self.test_yaml_validation_with_corruption,
                self.test_yaml_repair_functionality,
                self.test_emergency_file_creation,
                self.test_workflow_performance_impact,
                self.test_workflow_error_handling,
                self.test_ci_environment_compatibility,
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


def main() -> int:
    """Main entry point for simplified integration testing."""
    parser = argparse.ArgumentParser(description="Simplified YAML validation integration tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--json-output", "-j", type=str, help="Output results as JSON to specified file"
    )

    args = parser.parse_args()

    try:
        # Run tests
        tester = SimpleYAMLIntegrationTester(verbose=args.verbose)
        summary = tester.run_all_tests()

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
