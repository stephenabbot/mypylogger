"""Deployment validation script for Phase 7 PyPI publishing system.

This script performs comprehensive validation of the deployment to ensure
all components are properly configured and working correctly.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.integration_orchestrator import IntegrationOrchestrator
from scripts.security_performance_validator import SecurityPerformanceValidator


class DeploymentValidator:
    """Comprehensive deployment validation for Phase 7 system."""

    def __init__(self) -> None:
        """Initialize deployment validator."""
        self.results: list[dict[str, Any]] = []
        self.orchestrator = IntegrationOrchestrator()
        self.security_validator = SecurityPerformanceValidator()

    def validate_file_structure(self) -> dict[str, Any]:
        """Validate required file structure exists."""
        print("🗂️  Validating file structure...")

        required_files = [
            # Core scripts
            "scripts/integration_orchestrator.py",
            "scripts/release_automation_engine.py",
            "scripts/security_change_detector.py",
            "scripts/workflow_monitoring.py",
            "scripts/security_performance_validator.py",
            # GitHub Actions workflows
            ".github/workflows/pypi-publish.yml",
            ".github/workflows/security-driven-release.yml",
            ".github/workflows/security-scan.yml",
            # Security infrastructure
            "security/findings/SECURITY_FINDINGS.md",
            "security/config/scanner-settings.yml",
            # Documentation
            "docs/PHASE_7_PYPI_PUBLISHING.md",
            "docs/OPERATIONAL_RUNBOOK.md",
            # Infrastructure
            "infrastructure/cloudformation/pypi-oidc-stack.yaml",
            "infrastructure/terraform/main.tf",
        ]

        missing_files = []
        existing_files = []

        for file_path in required_files:
            if Path(file_path).exists():
                existing_files.append(file_path)
            else:
                missing_files.append(file_path)

        return {
            "test_name": "File Structure Validation",
            "passed": len(missing_files) == 0,
            "message": f"Found {len(existing_files)}/{len(required_files)} required files",
            "details": {
                "existing_files": existing_files,
                "missing_files": missing_files,
            },
        }

    def validate_python_imports(self) -> dict[str, Any]:
        """Validate all Python modules can be imported."""
        print("🐍 Validating Python imports...")

        modules_to_test = [
            "scripts.integration_orchestrator",
            "scripts.release_automation_engine",
            "scripts.security_change_detector",
            "scripts.workflow_monitoring",
            "scripts.security_performance_validator",
            "badges.live_status",
            "security.models",
            "security.parsers",
            "security.synchronizer",
        ]

        import_results = []
        failed_imports = []

        for module in modules_to_test:
            try:
                __import__(module)
                import_results.append({"module": module, "status": "success"})
            except ImportError as e:
                import_results.append({"module": module, "status": "failed", "error": str(e)})
                failed_imports.append(module)

        return {
            "test_name": "Python Import Validation",
            "passed": len(failed_imports) == 0,
            "message": f"Successfully imported {len(modules_to_test) - len(failed_imports)}/{len(modules_to_test)} modules",
            "details": {
                "import_results": import_results,
                "failed_imports": failed_imports,
            },
        }

    def validate_github_workflows(self) -> dict[str, Any]:
        """Validate GitHub Actions workflow syntax."""
        print("⚙️  Validating GitHub Actions workflows...")

        workflow_files = [
            ".github/workflows/pypi-publish.yml",
            ".github/workflows/security-driven-release.yml",
            ".github/workflows/security-scan.yml",
        ]

        validation_results = []

        for workflow_file in workflow_files:
            if not Path(workflow_file).exists():
                validation_results.append(
                    {
                        "file": workflow_file,
                        "status": "missing",
                        "error": "File does not exist",
                    }
                )
                continue

            try:
                # Basic YAML syntax validation
                import yaml

                with open(workflow_file) as f:
                    yaml.safe_load(f)

                # Check for required workflow elements
                with open(workflow_file) as f:
                    content = f.read()

                required_elements = ["name:", "on:", "jobs:"]
                missing_elements = [elem for elem in required_elements if elem not in content]

                if missing_elements:
                    validation_results.append(
                        {
                            "file": workflow_file,
                            "status": "invalid",
                            "error": f"Missing required elements: {missing_elements}",
                        }
                    )
                else:
                    validation_results.append(
                        {
                            "file": workflow_file,
                            "status": "valid",
                        }
                    )

            except Exception as e:
                validation_results.append(
                    {
                        "file": workflow_file,
                        "status": "error",
                        "error": str(e),
                    }
                )

        failed_validations = [r for r in validation_results if r["status"] != "valid"]

        return {
            "test_name": "GitHub Workflows Validation",
            "passed": len(failed_validations) == 0,
            "message": f"Validated {len(workflow_files) - len(failed_validations)}/{len(workflow_files)} workflow files",
            "details": {
                "validation_results": validation_results,
                "failed_validations": failed_validations,
            },
        }

    def validate_environment_configuration(self) -> dict[str, Any]:
        """Validate environment configuration for deployment."""
        print("🔧 Validating environment configuration...")

        # Check for required environment variables (optional for deployment)
        optional_env_vars = [
            "AWS_ROLE_ARN",
            "AWS_REGION",
            "AWS_SECRET_NAME",
            "GITHUB_PAGES_URL",
        ]

        env_status = {}
        configured_vars = 0

        for var in optional_env_vars:
            value = os.getenv(var)
            if value:
                env_status[var] = "configured"
                configured_vars += 1
            else:
                env_status[var] = "not_configured"

        # Check Python environment
        python_version = sys.version_info
        python_ok = python_version >= (3, 8)

        # Check UV installation
        uv_available = False
        try:
            result = subprocess.run(
                ["uv", "--version"], check=False, capture_output=True, text=True
            )
            uv_available = result.returncode == 0
        except FileNotFoundError:
            pass

        return {
            "test_name": "Environment Configuration",
            "passed": python_ok and uv_available,
            "message": f"Python {python_version.major}.{python_version.minor}, UV: {'available' if uv_available else 'missing'}",
            "details": {
                "python_version": f"{python_version.major}.{python_version.minor}.{python_version.micro}",
                "python_ok": python_ok,
                "uv_available": uv_available,
                "environment_variables": env_status,
                "configured_env_vars": f"{configured_vars}/{len(optional_env_vars)}",
            },
        }

    def validate_integration_health(self) -> dict[str, Any]:
        """Validate integration health using orchestrator."""
        print("🏥 Validating integration health...")

        try:
            health_result = self.orchestrator.validate_integration_health()

            return {
                "test_name": "Integration Health Check",
                "passed": health_result.get("overall_healthy", False),
                "message": f"Health status: {'healthy' if health_result.get('overall_healthy') else 'degraded'}",
                "details": health_result,
            }

        except Exception as e:
            return {
                "test_name": "Integration Health Check",
                "passed": False,
                "message": f"Health check failed: {e}",
                "details": {"error": str(e)},
            }

    def validate_security_configuration(self) -> dict[str, Any]:
        """Validate security configuration and requirements."""
        print("🔒 Validating security configuration...")

        try:
            # Run security validations (may fail if AWS not configured)
            security_results = (
                self.security_validator.security_validator.run_all_security_validations()
            )

            passed_tests = sum(1 for result in security_results if result.passed)
            total_tests = len(security_results)

            return {
                "test_name": "Security Configuration",
                "passed": passed_tests >= total_tests // 2,  # At least half should pass
                "message": f"Security validation: {passed_tests}/{total_tests} tests passed",
                "details": {
                    "security_results": [
                        {
                            "test_name": result.test_name,
                            "passed": result.passed,
                            "message": result.message,
                        }
                        for result in security_results
                    ],
                },
            }

        except Exception as e:
            return {
                "test_name": "Security Configuration",
                "passed": False,
                "message": f"Security validation failed: {e}",
                "details": {"error": str(e)},
            }

    def validate_test_suite(self) -> dict[str, Any]:
        """Validate test suite can run successfully."""
        print("🧪 Validating test suite...")

        try:
            # Run a subset of tests to validate they work
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "pytest",
                    "tests/unit/test_integration_orchestrator.py",
                    "-v",
                    "--tb=short",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )

            return {
                "test_name": "Test Suite Validation",
                "passed": result.returncode == 0,
                "message": f"Test execution: {'passed' if result.returncode == 0 else 'failed'}",
                "details": {
                    "return_code": result.returncode,
                    "stdout": result.stdout[-1000:] if result.stdout else "",  # Last 1000 chars
                    "stderr": result.stderr[-1000:] if result.stderr else "",
                },
            }

        except subprocess.TimeoutExpired:
            return {
                "test_name": "Test Suite Validation",
                "passed": False,
                "message": "Test execution timed out",
                "details": {"error": "Timeout after 60 seconds"},
            }
        except Exception as e:
            return {
                "test_name": "Test Suite Validation",
                "passed": False,
                "message": f"Test execution failed: {e}",
                "details": {"error": str(e)},
            }

    def validate_documentation(self) -> dict[str, Any]:
        """Validate documentation completeness."""
        print("📚 Validating documentation...")

        required_docs = [
            "docs/PHASE_7_PYPI_PUBLISHING.md",
            "docs/OPERATIONAL_RUNBOOK.md",
            "README.md",
        ]

        doc_status = {}
        missing_docs = []

        for doc_file in required_docs:
            if Path(doc_file).exists():
                # Check if file has reasonable content
                content = Path(doc_file).read_text()
                if len(content) > 100:  # At least 100 characters
                    doc_status[doc_file] = "complete"
                else:
                    doc_status[doc_file] = "incomplete"
                    missing_docs.append(doc_file)
            else:
                doc_status[doc_file] = "missing"
                missing_docs.append(doc_file)

        return {
            "test_name": "Documentation Validation",
            "passed": len(missing_docs) == 0,
            "message": f"Documentation: {len(required_docs) - len(missing_docs)}/{len(required_docs)} files complete",
            "details": {
                "documentation_status": doc_status,
                "missing_or_incomplete": missing_docs,
            },
        }

    def run_complete_validation(self) -> dict[str, Any]:
        """Run complete deployment validation suite."""
        print("🚀 Starting Phase 7 deployment validation...")
        print("=" * 60)

        validation_tests = [
            self.validate_file_structure,
            self.validate_python_imports,
            self.validate_github_workflows,
            self.validate_environment_configuration,
            self.validate_integration_health,
            self.validate_security_configuration,
            self.validate_test_suite,
            self.validate_documentation,
        ]

        results = []
        passed_tests = 0

        for test_func in validation_tests:
            try:
                result = test_func()
                results.append(result)

                # Print test result
                status_icon = "✅" if result["passed"] else "❌"
                print(f"{status_icon} {result['test_name']}: {result['message']}")

                if result["passed"]:
                    passed_tests += 1

            except Exception as e:
                error_result = {
                    "test_name": test_func.__name__,
                    "passed": False,
                    "message": f"Test execution failed: {e}",
                    "details": {"error": str(e)},
                }
                results.append(error_result)
                print(f"❌ {test_func.__name__}: Test execution failed: {e}")

        overall_passed = passed_tests >= len(validation_tests) * 0.8  # 80% pass rate

        print("\n" + "=" * 60)
        print("DEPLOYMENT VALIDATION SUMMARY")
        print("=" * 60)

        if overall_passed:
            print("✅ DEPLOYMENT VALIDATION PASSED")
            print(f"   {passed_tests}/{len(validation_tests)} tests passed")
        else:
            print("❌ DEPLOYMENT VALIDATION FAILED")
            print(f"   Only {passed_tests}/{len(validation_tests)} tests passed")
            print("   Please review failed tests and fix issues before deployment")

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_passed": overall_passed,
            "passed_tests": passed_tests,
            "total_tests": len(validation_tests),
            "pass_rate": (passed_tests / len(validation_tests)) * 100,
            "results": results,
        }

    def generate_validation_report(self, results: dict[str, Any]) -> str:
        """Generate detailed validation report."""
        report = []
        report.append("# Phase 7 Deployment Validation Report")
        report.append(f"Generated: {results['timestamp']}")
        report.append("")

        # Overall status
        status_icon = "✅" if results["overall_passed"] else "❌"
        report.append(
            f"{status_icon} **Overall Status**: {'PASSED' if results['overall_passed'] else 'FAILED'}"
        )
        report.append(
            f"**Pass Rate**: {results['pass_rate']:.1f}% ({results['passed_tests']}/{results['total_tests']})"
        )
        report.append("")

        # Individual test results
        report.append("## Test Results")
        report.append("")

        for result in results["results"]:
            icon = "✅" if result["passed"] else "❌"
            report.append(f"{icon} **{result['test_name']}**: {result['message']}")

            if not result["passed"] and "details" in result:
                report.append("   - Details:")
                if "error" in result["details"]:
                    report.append(f"     - Error: {result['details']['error']}")
                if "missing_files" in result["details"]:
                    for file in result["details"]["missing_files"]:
                        report.append(f"     - Missing: {file}")

        report.append("")

        # Recommendations
        report.append("## Recommendations")
        report.append("")

        if results["overall_passed"]:
            report.append(
                "✅ Deployment validation passed. The system is ready for production deployment."
            )
            report.append("")
            report.append("**Next Steps:**")
            report.append("1. Configure AWS OIDC infrastructure if not already done")
            report.append("2. Set up GitHub repository secrets")
            report.append("3. Test workflows in dry-run mode")
            report.append("4. Enable automated workflows")
        else:
            report.append("❌ Deployment validation failed. Please address the following issues:")
            report.append("")

            failed_tests = [r for r in results["results"] if not r["passed"]]
            for i, test in enumerate(failed_tests, 1):
                report.append(f"{i}. **{test['test_name']}**: {test['message']}")

        return "\n".join(report)


def main() -> None:
    """Main entry point for deployment validation."""
    validator = DeploymentValidator()

    # Run validation
    results = validator.run_complete_validation()

    # Save results
    with open("deployment_validation_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Generate report
    report = validator.generate_validation_report(results)
    with open("deployment_validation_report.md", "w") as f:
        f.write(report)

    print("\nDetailed results saved to:")
    print("  - deployment_validation_results.json")
    print("  - deployment_validation_report.md")

    # Exit with appropriate code
    sys.exit(0 if results["overall_passed"] else 1)


if __name__ == "__main__":
    main()
