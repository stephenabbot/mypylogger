"""Security and performance validation for Phase 7 PyPI publishing system.

This module provides comprehensive validation of security requirements
(OIDC authentication) and performance requirements (API response times,
workflow execution times) for the PyPI publishing system.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from typing import Any

import requests


def is_ci_environment() -> bool:
    """Detect if running in CI environment."""
    ci_indicators = [
        "CI",
        "CONTINUOUS_INTEGRATION",
        "GITHUB_ACTIONS",
        "TRAVIS",
        "CIRCLECI",
        "JENKINS_URL",
        "BUILDKITE",
    ]
    return any(
        os.environ.get(indicator, "").lower() in ("true", "1", "yes") for indicator in ci_indicators
    )


def get_performance_threshold(base_threshold: float) -> float:
    """Get performance threshold adjusted for CI environment."""
    if is_ci_environment():
        return base_threshold * 1.5  # 50% more time for CI
    return base_threshold


@dataclass
class SecurityValidationResult:
    """Result of security validation checks."""

    test_name: str
    passed: bool
    message: str
    details: dict[str, Any] | None = None
    execution_time: float | None = None


@dataclass
class PerformanceValidationResult:
    """Result of performance validation checks."""

    test_name: str
    passed: bool
    target_time: float
    actual_time: float
    message: str
    details: dict[str, Any] | None = None


class SecurityValidator:
    """Validator for security requirements and OIDC authentication."""

    def __init__(self) -> None:
        """Initialize security validator."""
        self.results: list[SecurityValidationResult] = []

    def validate_trusted_publishing_configuration(self) -> SecurityValidationResult:
        """Validate trusted publishing configuration and environment setup.

        Returns:
            Security validation result for trusted publishing configuration
        """
        start_time = time.time()

        try:
            # Check for PyPI publishing workflow configuration
            workflow_path = Path(".github/workflows/pypi-publish.yml")
            if not workflow_path.exists():
                return SecurityValidationResult(
                    test_name="Trusted Publishing Configuration",
                    passed=False,
                    message="PyPI publishing workflow not found",
                    details={"workflow_path": str(workflow_path)},
                    execution_time=time.time() - start_time,
                )

            # Read and validate workflow configuration
            import yaml

            with open(workflow_path) as f:
                workflow = yaml.safe_load(f)

            # Check for proper OIDC permissions
            publish_job = workflow.get("jobs", {}).get("publish-to-pypi", {})
            permissions = publish_job.get("permissions", {})

            required_permissions = {"id-token": "write", "contents": "read"}
            missing_permissions = []

            for perm, level in required_permissions.items():
                if permissions.get(perm) != level:
                    missing_permissions.append(f"{perm}: {level}")

            if missing_permissions:
                return SecurityValidationResult(
                    test_name="Trusted Publishing Configuration",
                    passed=False,
                    message=f"Missing required OIDC permissions: {missing_permissions}",
                    details={"missing_permissions": missing_permissions},
                    execution_time=time.time() - start_time,
                )

            # Check for pypa/gh-action-pypi-publish usage
            steps = publish_job.get("steps", [])
            has_trusted_publishing = any(
                step.get("uses", "").startswith("pypa/gh-action-pypi-publish") for step in steps
            )

            if not has_trusted_publishing:
                return SecurityValidationResult(
                    test_name="Trusted Publishing Configuration",
                    passed=False,
                    message="Workflow does not use pypa/gh-action-pypi-publish for trusted publishing",
                    details={"steps": [step.get("uses") for step in steps if "uses" in step]},
                    execution_time=time.time() - start_time,
                )

            return SecurityValidationResult(
                test_name="Trusted Publishing Configuration",
                passed=True,
                message="Trusted publishing configuration is valid",
                details={
                    "permissions": permissions,
                    "uses_trusted_publishing": has_trusted_publishing,
                },
                execution_time=time.time() - start_time,
            )

        except Exception as e:
            return SecurityValidationResult(
                test_name="Trusted Publishing Configuration",
                passed=False,
                message=f"Trusted publishing configuration validation failed: {e}",
                details={"error": str(e)},
                execution_time=time.time() - start_time,
            )

    def validate_credential_security(self) -> SecurityValidationResult:
        """Validate credential security measures.

        Returns:
            Security validation result for credential security
        """
        start_time = time.time()

        try:
            security_checks = []

            # Check that no PyPI tokens are in environment variables
            env_vars = os.environ
            for key, value in env_vars.items():
                if "pypi" in key.lower() and "token" in key.lower():
                    if value and value.startswith("pypi-"):
                        security_checks.append(
                            {
                                "check": "PyPI token in environment",
                                "passed": False,
                                "message": f"PyPI token found in environment variable {key}",
                            }
                        )
                    else:
                        security_checks.append(
                            {
                                "check": "PyPI token in environment",
                                "passed": True,
                                "message": "No PyPI tokens found in environment variables",
                            }
                        )

            # Check for hardcoded secrets in workflow files
            workflow_files = list(Path(".github/workflows").glob("*.yml"))
            hardcoded_secrets = []

            for workflow_file in workflow_files:
                try:
                    content = workflow_file.read_text()
                    # Look for potential hardcoded tokens (actual token values, not references)
                    if "pypi-" in content.lower():
                        lines = content.split("\n")
                        for i, line in enumerate(lines):
                            # Only flag lines that contain actual token values (start with pypi- and have more content)
                            if (
                                "pypi-" in line.lower()
                                and "secret" not in line.lower()
                                and "token" not in line.lower()
                            ):
                                # Check if it looks like an actual token (pypi- followed by alphanumeric)
                                import re

                                if re.search(r"pypi-[a-zA-Z0-9]{20,}", line):
                                    hardcoded_secrets.append(
                                        {
                                            "file": str(workflow_file),
                                            "line": i + 1,
                                            "content": line.strip(),
                                        }
                                    )
                except Exception:
                    continue

            if hardcoded_secrets:
                security_checks.append(
                    {
                        "check": "Hardcoded secrets in workflows",
                        "passed": False,
                        "message": f"Found {len(hardcoded_secrets)} potential hardcoded secrets",
                        "details": hardcoded_secrets,
                    }
                )
            else:
                security_checks.append(
                    {
                        "check": "Hardcoded secrets in workflows",
                        "passed": True,
                        "message": "No hardcoded secrets found in workflow files",
                    }
                )

            # Overall result
            all_passed = all(check["passed"] for check in security_checks)

            return SecurityValidationResult(
                test_name="Credential Security",
                passed=all_passed,
                message="All credential security checks passed"
                if all_passed
                else "Some credential security checks failed",
                details={"security_checks": security_checks},
                execution_time=time.time() - start_time,
            )

        except Exception as e:
            return SecurityValidationResult(
                test_name="Credential Security",
                passed=False,
                message=f"Error validating credential security: {e}",
                execution_time=time.time() - start_time,
            )

    def validate_publishing_authorization(self) -> SecurityValidationResult:
        """Validate PyPI publishing authorization and scope limitations.

        Returns:
            Security validation result for publishing authorization
        """
        start_time = time.time()

        try:
            # Check workflow permissions
            workflow_files = list(Path(".github/workflows").glob("*pypi*.yml"))

            authorization_checks = []

            for workflow_file in workflow_files:
                try:
                    content = workflow_file.read_text()

                    # Check for proper permissions configuration
                    if "permissions:" in content:
                        if "id-token: write" in content:
                            authorization_checks.append(
                                {
                                    "check": f"OIDC permissions in {workflow_file.name}",
                                    "passed": True,
                                    "message": "Proper OIDC permissions configured",
                                }
                            )
                        else:
                            authorization_checks.append(
                                {
                                    "check": f"OIDC permissions in {workflow_file.name}",
                                    "passed": False,
                                    "message": "Missing id-token: write permission",
                                }
                            )
                    else:
                        authorization_checks.append(
                            {
                                "check": f"Permissions in {workflow_file.name}",
                                "passed": False,
                                "message": "No permissions section found",
                            }
                        )

                    # Check for trusted publishing action usage
                    if "pypa/gh-action-pypi-publish" in content:
                        authorization_checks.append(
                            {
                                "check": f"Trusted publishing in {workflow_file.name}",
                                "passed": True,
                                "message": "Uses PyPI trusted publishing action",
                            }
                        )
                    else:
                        authorization_checks.append(
                            {
                                "check": f"Trusted publishing in {workflow_file.name}",
                                "passed": False,
                                "message": "Does not use PyPI trusted publishing action",
                            }
                        )

                except Exception:
                    continue

            if not authorization_checks:
                return SecurityValidationResult(
                    test_name="Publishing Authorization",
                    passed=False,
                    message="No PyPI workflow files found for validation",
                    execution_time=time.time() - start_time,
                )

            all_passed = all(check["passed"] for check in authorization_checks)

            return SecurityValidationResult(
                test_name="Publishing Authorization",
                passed=all_passed,
                message="All authorization checks passed"
                if all_passed
                else "Some authorization checks failed",
                details={"authorization_checks": authorization_checks},
                execution_time=time.time() - start_time,
            )

        except Exception as e:
            return SecurityValidationResult(
                test_name="Publishing Authorization",
                passed=False,
                message=f"Error validating publishing authorization: {e}",
                execution_time=time.time() - start_time,
            )

    def run_all_security_validations(self) -> list[SecurityValidationResult]:
        """Run all security validation checks.

        Returns:
            List of all security validation results
        """
        self.results = [
            self.validate_trusted_publishing_configuration(),
            self.validate_credential_security(),
            self.validate_publishing_authorization(),
        ]

        return self.results


class PerformanceValidator:
    """Validator for performance requirements."""

    def __init__(self) -> None:
        """Initialize performance validator."""
        self.results: list[PerformanceValidationResult] = []

    def validate_api_response_time(
        self,
        url: str,
        target_time: float = 0.2,  # 200ms target
    ) -> PerformanceValidationResult:
        """Validate API response time meets performance targets.

        Args:
            url: URL to test
            target_time: Target response time in seconds

        Returns:
            Performance validation result for API response time
        """
        # Adjust target time for CI environment
        adjusted_target_time = get_performance_threshold(target_time)

        try:
            # Make multiple requests to get average response time
            response_times = []

            for _ in range(5):  # Test 5 times
                start_time = time.time()
                try:
                    response = requests.get(url, timeout=5)
                    response_time = time.time() - start_time

                    if response.status_code == 200:
                        response_times.append(response_time)
                    else:
                        return PerformanceValidationResult(
                            test_name=f"API Response Time ({url})",
                            passed=False,
                            target_time=adjusted_target_time,
                            actual_time=response_time,
                            message=f"API returned status code {response.status_code}",
                            details={"status_code": response.status_code},
                        )

                except requests.RequestException as e:
                    return PerformanceValidationResult(
                        test_name=f"API Response Time ({url})",
                        passed=False,
                        target_time=adjusted_target_time,
                        actual_time=0.0,
                        message=f"Request failed: {e}",
                        details={"error": str(e)},
                    )

                # Small delay between requests
                time.sleep(0.1)

            if not response_times:
                return PerformanceValidationResult(
                    test_name=f"API Response Time ({url})",
                    passed=False,
                    target_time=adjusted_target_time,
                    actual_time=0.0,
                    message="No successful responses received",
                )

            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)

            passed = avg_response_time <= adjusted_target_time

            return PerformanceValidationResult(
                test_name=f"API Response Time ({url})",
                passed=passed,
                target_time=adjusted_target_time,
                actual_time=avg_response_time,
                message=f"Average response time: {avg_response_time:.3f}s (target: {adjusted_target_time}s)",
                details={
                    "average_time": avg_response_time,
                    "max_time": max_response_time,
                    "min_time": min_response_time,
                    "sample_count": len(response_times),
                },
            )

        except Exception as e:
            return PerformanceValidationResult(
                test_name=f"API Response Time ({url})",
                passed=False,
                target_time=adjusted_target_time,
                actual_time=0.0,
                message=f"Error testing API response time: {e}",
            )

    def validate_workflow_execution_time(
        self,
        workflow_name: str,
        target_time: float = 300.0,  # 5 minutes target
    ) -> PerformanceValidationResult:
        """Validate workflow execution time meets performance targets.

        Args:
            workflow_name: Name of the workflow to validate
            target_time: Target execution time in seconds

        Returns:
            Performance validation result for workflow execution time
        """
        # Adjust target time for CI environment
        adjusted_target_time = get_performance_threshold(target_time)
        try:
            # Look for recent workflow execution metrics
            metrics_dir = Path.cwd() / "metrics"
            if not metrics_dir.exists():
                return PerformanceValidationResult(
                    test_name=f"Workflow Execution Time ({workflow_name})",
                    passed=False,
                    target_time=adjusted_target_time,
                    actual_time=0.0,
                    message="No metrics directory found",
                )

            # Find recent workflow metrics
            workflow_files = list(metrics_dir.glob(f"workflow-{workflow_name}*.json"))

            if not workflow_files:
                return PerformanceValidationResult(
                    test_name=f"Workflow Execution Time ({workflow_name})",
                    passed=False,
                    target_time=adjusted_target_time,
                    actual_time=0.0,
                    message=f"No metrics found for workflow {workflow_name}",
                )

            # Get execution times from recent workflows
            execution_times = []

            for metrics_file in workflow_files[-10:]:  # Last 10 executions
                try:
                    with metrics_file.open() as f:
                        data = json.load(f)

                    if data.get("duration_seconds"):
                        execution_times.append(data["duration_seconds"])

                except (json.JSONDecodeError, KeyError):
                    continue

            if not execution_times:
                return PerformanceValidationResult(
                    test_name=f"Workflow Execution Time ({workflow_name})",
                    passed=False,
                    target_time=adjusted_target_time,
                    actual_time=0.0,
                    message="No valid execution time data found",
                )

            avg_execution_time = sum(execution_times) / len(execution_times)
            max_execution_time = max(execution_times)
            min_execution_time = min(execution_times)

            passed = avg_execution_time <= adjusted_target_time

            return PerformanceValidationResult(
                test_name=f"Workflow Execution Time ({workflow_name})",
                passed=passed,
                target_time=adjusted_target_time,
                actual_time=avg_execution_time,
                message=f"Average execution time: {avg_execution_time:.1f}s (target: {adjusted_target_time}s)",
                details={
                    "average_time": avg_execution_time,
                    "max_time": max_execution_time,
                    "min_time": min_execution_time,
                    "sample_count": len(execution_times),
                },
            )

        except Exception as e:
            return PerformanceValidationResult(
                test_name=f"Workflow Execution Time ({workflow_name})",
                passed=False,
                target_time=adjusted_target_time,
                actual_time=0.0,
                message=f"Error validating workflow execution time: {e}",
            )

    def validate_status_api_performance(self) -> PerformanceValidationResult:
        """Validate live security status API performance.

        Returns:
            Performance validation result for status API
        """
        # Check if status files exist locally first
        status_files = [
            Path.cwd() / "docs/security-status/index.json",
            Path.cwd() / "security-status/index.json",
        ]

        local_file = None
        for status_file in status_files:
            if status_file.exists():
                local_file = status_file
                break

        if local_file:
            # Test local file access performance
            start_time = time.time()
            try:
                with local_file.open() as f:
                    json.load(f)
                access_time = time.time() - start_time

                # Adjust target time for CI environment
                local_target_time = get_performance_threshold(0.01)

                return PerformanceValidationResult(
                    test_name="Status API Performance (Local)",
                    passed=access_time <= local_target_time,
                    target_time=local_target_time,
                    actual_time=access_time,
                    message=f"Local status file access time: {access_time:.3f}s",
                    details={"file_path": str(local_file)},
                )

            except Exception as e:
                local_target_time = get_performance_threshold(0.01)
                return PerformanceValidationResult(
                    test_name="Status API Performance (Local)",
                    passed=False,
                    target_time=local_target_time,
                    actual_time=0.0,
                    message=f"Error accessing local status file: {e}",
                )

        # If no local file, try to test a GitHub Pages URL (if available)
        # This would be configured based on the actual deployment
        github_pages_url = os.getenv("GITHUB_PAGES_URL")
        if github_pages_url:
            status_url = f"{github_pages_url}/security-status/index.json"
            return self.validate_api_response_time(status_url, 0.2)

        fallback_target_time = get_performance_threshold(0.2)
        return PerformanceValidationResult(
            test_name="Status API Performance",
            passed=False,
            target_time=fallback_target_time,
            actual_time=0.0,
            message="No status API endpoint available for testing",
        )

    def run_all_performance_validations(self) -> list[PerformanceValidationResult]:
        """Run all performance validation checks.

        Returns:
            List of all performance validation results
        """
        self.results = [
            self.validate_status_api_performance(),
            self.validate_workflow_execution_time("pypi-publish"),
            self.validate_workflow_execution_time("security-driven-release"),
        ]

        return self.results


class SecurityPerformanceValidator:
    """Main validator for security and performance requirements."""

    def __init__(self) -> None:
        """Initialize the validator."""
        self.security_validator = SecurityValidator()
        self.performance_validator = PerformanceValidator()

    def run_complete_validation(self) -> dict[str, Any]:
        """Run complete security and performance validation.

        Returns:
            Dictionary containing all validation results
        """
        print("🔒 Running security validations...")
        security_results = self.security_validator.run_all_security_validations()

        print("⚡ Running performance validations...")
        performance_results = self.performance_validator.run_all_performance_validations()

        # Calculate overall results
        security_passed = all(result.passed for result in security_results)
        performance_passed = all(result.passed for result in performance_results)
        overall_passed = security_passed and performance_passed

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_passed": overall_passed,
            "security": {
                "passed": security_passed,
                "results": [
                    {
                        "test_name": result.test_name,
                        "passed": result.passed,
                        "message": result.message,
                        "execution_time": result.execution_time,
                        "details": result.details,
                    }
                    for result in security_results
                ],
            },
            "performance": {
                "passed": performance_passed,
                "results": [
                    {
                        "test_name": result.test_name,
                        "passed": result.passed,
                        "target_time": result.target_time,
                        "actual_time": result.actual_time,
                        "message": result.message,
                        "details": result.details,
                    }
                    for result in performance_results
                ],
            },
        }

    def generate_validation_report(self, results: dict[str, Any]) -> str:
        """Generate a human-readable validation report.

        Args:
            results: Validation results from run_complete_validation

        Returns:
            Formatted validation report
        """
        report = []
        report.append("# Security and Performance Validation Report")
        report.append(f"Generated: {results['timestamp']}")
        report.append("")

        # Overall status
        status_icon = "✅" if results["overall_passed"] else "❌"
        report.append(
            f"{status_icon} **Overall Status**: {'PASSED' if results['overall_passed'] else 'FAILED'}"
        )
        report.append("")

        # Security results
        security_icon = "✅" if results["security"]["passed"] else "❌"
        report.append(
            f"{security_icon} **Security Validation**: {'PASSED' if results['security']['passed'] else 'FAILED'}"
        )
        report.append("")

        for result in results["security"]["results"]:
            icon = "✅" if result["passed"] else "❌"
            report.append(f"{icon} {result['test_name']}: {result['message']}")
            if result.get("execution_time"):
                report.append(f"   Execution time: {result['execution_time']:.3f}s")

        report.append("")

        # Performance results
        performance_icon = "✅" if results["performance"]["passed"] else "❌"
        report.append(
            f"{performance_icon} **Performance Validation**: {'PASSED' if results['performance']['passed'] else 'FAILED'}"
        )
        report.append("")

        for result in results["performance"]["results"]:
            icon = "✅" if result["passed"] else "❌"
            report.append(f"{icon} {result['test_name']}: {result['message']}")
            if result.get("target_time") and result.get("actual_time"):
                report.append(
                    f"   Target: {result['target_time']:.3f}s, Actual: {result['actual_time']:.3f}s"
                )

        return "\n".join(report)


def main() -> None:
    """Main entry point for security and performance validation."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python security_performance_validator.py <command> [options]")
        print("Commands:")
        print("  validate - Run complete security and performance validation")
        print("  security - Run security validation only")
        print("  performance - Run performance validation only")
        print("  report [--json] - Generate validation report")
        sys.exit(1)

    validator = SecurityPerformanceValidator()
    command = sys.argv[1]

    if command == "validate":
        results = validator.run_complete_validation()

        # Print summary
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)

        if results["overall_passed"]:
            print("✅ ALL VALIDATIONS PASSED")
        else:
            print("❌ SOME VALIDATIONS FAILED")

        print(f"Security: {'✅ PASSED' if results['security']['passed'] else '❌ FAILED'}")
        print(f"Performance: {'✅ PASSED' if results['performance']['passed'] else '❌ FAILED'}")

        # Save results
        with open("validation_results.json", "w") as f:
            json.dump(results, f, indent=2)

        print("\nDetailed results saved to: validation_results.json")

        # Exit with appropriate code
        sys.exit(0 if results["overall_passed"] else 1)

    elif command == "security":
        results = validator.security_validator.run_all_security_validations()

        for result in results:
            icon = "✅" if result.passed else "❌"
            print(f"{icon} {result.test_name}: {result.message}")

        all_passed = all(result.passed for result in results)
        sys.exit(0 if all_passed else 1)

    elif command == "performance":
        results = validator.performance_validator.run_all_performance_validations()

        for result in results:
            icon = "✅" if result.passed else "❌"
            print(f"{icon} {result.test_name}: {result.message}")

        all_passed = all(result.passed for result in results)
        sys.exit(0 if all_passed else 1)

    elif command == "report":
        if os.path.exists("validation_results.json"):
            with open("validation_results.json") as f:
                results = json.load(f)

            if "--json" in sys.argv:
                print(json.dumps(results, indent=2))
            else:
                report = validator.generate_validation_report(results)
                print(report)
        else:
            print("No validation results found. Run 'validate' command first.")
            sys.exit(1)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
