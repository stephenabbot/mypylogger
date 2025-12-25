#!/usr/bin/env python3
"""Enhanced workflow configuration validation for GitHub Actions.

This script provides comprehensive validation of GitHub Actions workflows
to prevent permission errors and ensure proper configuration.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any

import yaml


class WorkflowValidator:
    """Validates GitHub Actions workflow configurations."""

    def __init__(self, repo_root: Path) -> None:
        """Initialize the workflow validator.

        Args:
            repo_root: Path to the repository root
        """
        self.repo_root = repo_root
        self.workflows_dir = repo_root / ".github" / "workflows"
        self.validation_results: list[dict[str, Any]] = []

    def validate_all_workflows(self) -> bool:
        """Validate all workflow files for proper configuration.

        Returns:
            True if all validations pass, False otherwise
        """
        print("🔍 Validating GitHub Actions workflow configurations...")

        if not self.workflows_dir.exists():
            print(f"❌ Workflows directory not found: {self.workflows_dir}")
            return False

        workflow_files = list(self.workflows_dir.glob("*.yml"))
        if not workflow_files:
            print(f"❌ No workflow files found in {self.workflows_dir}")
            return False

        all_passed = True

        for workflow_file in workflow_files:
            try:
                result = self._validate_workflow_file(workflow_file)
                self.validation_results.append(result)

                if result["status"] == "PASS":
                    print(f"✅ {workflow_file.name}: {result['message']}")
                else:
                    print(f"❌ {workflow_file.name}: {result['message']}")
                    all_passed = False

            except Exception as e:
                error_result = {
                    "workflow": workflow_file.name,
                    "status": "ERROR",
                    "message": f"Failed to validate workflow: {e}",
                    "details": {},
                }
                self.validation_results.append(error_result)
                print(f"💥 {workflow_file.name}: Error validating workflow: {e}")
                all_passed = False

        return all_passed

    def _validate_workflow_file(self, workflow_file: Path) -> dict[str, Any]:
        """Validate a single workflow file.

        Args:
            workflow_file: Path to the workflow file

        Returns:
            Validation result dictionary
        """
        try:
            with workflow_file.open() as f:
                workflow_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            return {
                "workflow": workflow_file.name,
                "status": "FAIL",
                "message": f"Invalid YAML syntax: {e}",
                "details": {},
            }

        # Perform comprehensive validation
        issues = []

        # Validate basic structure
        issues.extend(self._validate_basic_structure(workflow_data))

        # Validate permissions
        issues.extend(self._validate_permissions(workflow_data))

        # Validate repository operations
        issues.extend(self._validate_repository_operations(workflow_data))

        # Validate environment variables
        issues.extend(self._validate_environment_variables(workflow_data))

        # Determine overall status
        if issues:
            status = "FAIL"
            message = f"Validation issues found: {len(issues)} issues"
        else:
            status = "PASS"
            message = "All validations passed"

        return {
            "workflow": workflow_file.name,
            "status": status,
            "message": message,
            "details": {
                "issues": issues,
                "permissions": workflow_data.get("permissions", {}),
                "jobs_count": len(workflow_data.get("jobs", {})),
            },
        }

    def _validate_basic_structure(self, workflow_data: dict[str, Any]) -> list[str]:
        """Validate basic workflow structure.

        Args:
            workflow_data: Parsed workflow YAML data

        Returns:
            List of validation issues
        """
        issues = []

        # Check required fields (handle YAML parsing quirk where 'on' becomes True)
        required_fields = ["name", "jobs"]
        for field in required_fields:
            if field not in workflow_data:
                issues.append(f"Missing required field: {field}")

        # Special handling for 'on' field which can be parsed as boolean True
        if "on" not in workflow_data and True not in workflow_data:
            issues.append("Missing required field: on")

        # Validate jobs structure
        jobs = workflow_data.get("jobs", {})
        if not jobs:
            issues.append("No jobs defined in workflow")

        for job_name, job_data in jobs.items():
            if not isinstance(job_data, dict):
                issues.append(f"Job '{job_name}' must be a dictionary")
                continue

            if "runs-on" not in job_data:
                issues.append(f"Job '{job_name}' missing 'runs-on' field")

            if "steps" not in job_data:
                issues.append(f"Job '{job_name}' missing 'steps' field")

        return issues

    def _validate_permissions(self, workflow_data: dict[str, Any]) -> list[str]:
        """Validate workflow permissions configuration.

        Args:
            workflow_data: Parsed workflow YAML data

        Returns:
            List of permission validation issues
        """
        issues = []
        permissions = workflow_data.get("permissions", {})

        # Analyze what permissions are needed
        needed_permissions = self._analyze_required_permissions(workflow_data)

        # Check if permissions are properly configured
        for perm_type, required in needed_permissions.items():
            if required:
                # Map permission types to GitHub permission names
                perm_mapping = {
                    "contents_write": "contents",
                    "contents_read": "contents",
                    "security_events_write": "security-events",
                    "actions_read": "actions",
                    "pull_requests_write": "pull-requests",
                }

                github_perm_name = perm_mapping.get(perm_type)
                if not github_perm_name:
                    continue

                current_perm = permissions.get(github_perm_name, "none")

                if perm_type.endswith("_write") and current_perm != "write":
                    issues.append(f"Needs '{github_perm_name}: write' but has '{current_perm}'")
                elif perm_type.endswith("_read") and current_perm not in ["read", "write"]:
                    issues.append(f"Needs '{github_perm_name}: read' but has '{current_perm}'")

        # Check for overly broad permissions
        if permissions.get("contents") == "write":
            if not needed_permissions.get("contents_write", False):
                issues.append("Has 'contents: write' but doesn't appear to need it")

        return issues

    def _analyze_required_permissions(self, workflow_data: dict[str, Any]) -> dict[str, bool]:
        """Analyze workflow to determine required permissions.

        Args:
            workflow_data: Parsed workflow YAML data

        Returns:
            Dictionary of required permissions
        """
        needed = {
            "contents_write": False,
            "contents_read": True,  # Almost always needed
            "security_events_write": False,
            "actions_read": False,
            "pull_requests_write": False,
        }

        jobs = workflow_data.get("jobs", {})

        for job_data in jobs.values():
            steps = job_data.get("steps", [])

            for step in steps:
                step_name = step.get("name", "").lower()
                step_run = step.get("run", "").lower()
                step_uses = step.get("uses", "").lower()

                # Check for git operations
                git_operations = [
                    "git commit",
                    "git push",
                    "git add",
                    "commit -m",
                    "push origin",
                    "git config --local",
                ]
                if any(op in step_run for op in git_operations):
                    needed["contents_write"] = True

                # Check for security operations
                security_keywords = ["security", "sarif", "bandit", "audit", "vulnerability"]
                if any(keyword in step_name for keyword in security_keywords) and (
                    "upload" in step_name or "actions/upload" in step_uses
                ):
                    needed["security_events_write"] = True

                # Check for workflow operations (not including basic actions like checkout)
                if "workflow_dispatch" in step_run or (
                    "actions/" in step_uses
                    and not any(
                        standard in step_uses
                        for standard in [
                            "actions/checkout",
                            "actions/setup-",
                            "actions/upload-artifact",
                            "actions/download-artifact",
                            "actions/cache",
                        ]
                    )
                ):
                    needed["actions_read"] = True

                # Check for PR operations
                pr_operations = ["pull_request", "pr comment", "github.rest.pulls"]
                if any(op in step_run for op in pr_operations):
                    needed["pull_requests_write"] = True

        return needed

    def _validate_repository_operations(self, workflow_data: dict[str, Any]) -> list[str]:
        """Validate repository operations in workflow.

        Args:
            workflow_data: Parsed workflow YAML data

        Returns:
            List of repository operation validation issues
        """
        issues = []
        jobs = workflow_data.get("jobs", {})

        for job_name, job_data in jobs.items():
            steps = job_data.get("steps", [])

            for i, step in enumerate(steps):
                step_run = step.get("run", "")

                # Check for git operations without proper authentication
                if "git push" in step_run or "git commit" in step_run:
                    # Look for git config setup in previous steps or current step
                    has_git_config = False

                    # Check current step
                    if "git config" in step_run:
                        has_git_config = True

                    # Check previous steps
                    for prev_step in steps[:i]:
                        if "git config" in prev_step.get("run", ""):
                            has_git_config = True
                            break

                    if not has_git_config:
                        issues.append(
                            f"Job '{job_name}' has git operations but no git config setup"
                        )

                # Check for repository context usage
                if "${{ github.repository }}" in step_run:
                    # This is good - using proper repository context
                    continue
                if (
                    "github.com/" in step_run
                    and "repository" not in step_run
                    and "secrets.GITHUB_TOKEN" not in step_run
                    and "x-access-token" not in step_run
                ):
                    # Flag only actual hardcoded references, not auth patterns
                    issues.append(f"Job '{job_name}' may be using hardcoded repository references")

        return issues

    def _validate_environment_variables(self, workflow_data: dict[str, Any]) -> list[str]:
        """Validate environment variable usage in workflow.

        Args:
            workflow_data: Parsed workflow YAML data

        Returns:
            List of environment variable validation issues
        """
        issues = []
        jobs = workflow_data.get("jobs", {})

        # Check for required environment variables for testing
        required_test_env_vars = ["GITHUB_REPOSITORY", "PYPI_PACKAGE"]

        for job_name, job_data in jobs.items():
            job_env = job_data.get("env", {})

            for step in job_data.get("steps", []):
                step_env = step.get("env", {})
                step_run = step.get("run", "")

                # Check if test-related steps have required environment variables
                if "test" in step.get("name", "").lower() or "./scripts/run_tests.sh" in step_run:
                    combined_env = {**job_env, **step_env}

                    for env_var in required_test_env_vars:
                        if env_var not in combined_env and f"${env_var}" not in step_run:
                            issues.append(
                                f"Job '{job_name}' test step missing environment variable: {env_var}"
                            )

        return issues

    def generate_validation_report(self) -> dict[str, Any]:
        """Generate comprehensive validation report.

        Returns:
            Validation report dictionary
        """
        passed_validations = sum(
            1 for result in self.validation_results if result["status"] == "PASS"
        )
        total_validations = len(self.validation_results)

        return {
            "summary": {
                "total_workflows": total_validations,
                "passed_validations": passed_validations,
                "failed_validations": total_validations - passed_validations,
                "success_rate": (
                    (passed_validations / total_validations * 100) if total_validations > 0 else 0
                ),
            },
            "validation_results": self.validation_results,
            "recommendations": self._generate_recommendations(),
        }

    def _generate_recommendations(self) -> list[str]:
        """Generate recommendations based on validation results.

        Returns:
            List of recommendation strings
        """
        recommendations = []

        failed_validations = [r for r in self.validation_results if r["status"] == "FAIL"]

        if not failed_validations:
            recommendations.append("All workflow configurations are valid")
            return recommendations

        recommendations.append("Fix workflow configuration issues before deploying to production")

        # Collect all issues and provide specific recommendations
        all_issues = []
        for validation in failed_validations:
            workflow = validation["workflow"]
            issues = validation["details"].get("issues", [])
            all_issues.extend([f"{workflow}: {issue}" for issue in issues])

        recommendations.extend(all_issues)

        return recommendations


def validate_repository_context() -> bool:
    """Validate repository context configuration for tests.

    Returns:
        True if repository context is properly configured, False otherwise
    """
    print("\n🏗️ Validating repository context configuration...")

    # Check environment variables
    github_repo = os.getenv("GITHUB_REPOSITORY")
    if not github_repo:
        print("⚠️  GITHUB_REPOSITORY environment variable not set")
        return False

    if github_repo != "stabbotco1/mypylogger":
        print(f"❌ Incorrect repository context: {github_repo} (expected: stabbotco1/mypylogger)")
        return False

    print("✅ Repository context properly configured")
    return True


def main() -> int:
    """Main function to run workflow validation."""
    repo_root = Path.cwd()

    print("🚀 GitHub Actions Workflow Configuration Validation")
    print("=" * 55)

    validator = WorkflowValidator(repo_root)

    # Run workflow validation
    workflows_valid = validator.validate_all_workflows()

    # Validate repository context
    context_valid = validate_repository_context()

    # Generate report
    report = validator.generate_validation_report()

    print("\n📊 Validation Summary")
    print("=" * 25)
    print(f"Workflows validated: {report['summary']['total_workflows']}")
    print(f"Validations passed: {report['summary']['passed_validations']}")
    print(f"Validations failed: {report['summary']['failed_validations']}")
    print(f"Success rate: {report['summary']['success_rate']:.1f}%")

    if report["recommendations"]:
        print("\n💡 Recommendations:")
        for rec in report["recommendations"]:
            print(f"  • {rec}")

    # Save detailed report
    report_file = repo_root / "workflow_validation_report.json"
    with report_file.open("w") as f:
        json.dump(report, f, indent=2)
    print(f"\n📄 Detailed report saved to: {report_file}")

    # Determine overall success
    overall_success = workflows_valid and context_valid

    if overall_success:
        print("\n✅ All workflow validations passed!")
        return 0

    print("\n❌ Some workflow validations failed!")
    return 1


if __name__ == "__main__":
    sys.exit(main())
