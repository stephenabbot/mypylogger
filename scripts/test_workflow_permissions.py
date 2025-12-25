#!/usr/bin/env python3
"""Test script to validate GitHub Actions workflow permission fixes.

This script validates that workflows have proper permissions configured
and can perform repository operations without permission errors.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import yaml


class WorkflowPermissionTester:
    """Test GitHub Actions workflow permissions."""

    def __init__(self, repo_root: Path) -> None:
        """Initialize the workflow permission tester.

        Args:
            repo_root: Path to the repository root
        """
        self.repo_root = repo_root
        self.workflows_dir = repo_root / ".github" / "workflows"
        self.test_results = []

    def test_all_workflows(self) -> bool:
        """Test all workflow files for proper permission configuration.

        Returns:
            True if all tests pass, False otherwise
        """
        print("🔍 Testing GitHub Actions workflow permissions...")

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
                result = self._test_workflow_file(workflow_file)
                self.test_results.append(result)

                if result["status"] == "PASS":
                    print(f"✅ {workflow_file.name}: {result['message']}")
                else:
                    print(f"❌ {workflow_file.name}: {result['message']}")
                    all_passed = False

            except Exception as e:
                error_result = {
                    "workflow": workflow_file.name,
                    "status": "ERROR",
                    "message": f"Failed to test workflow: {e}",
                    "details": {},
                }
                self.test_results.append(error_result)
                print(f"💥 {workflow_file.name}: Error testing workflow: {e}")
                all_passed = False

        return all_passed

    def _test_workflow_file(self, workflow_file: Path) -> dict:
        """Test a single workflow file for permission configuration.

        Args:
            workflow_file: Path to the workflow file

        Returns:
            Test result dictionary
        """
        with open(workflow_file) as f:
            try:
                workflow_data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                return {
                    "workflow": workflow_file.name,
                    "status": "FAIL",
                    "message": f"Invalid YAML syntax: {e}",
                    "details": {},
                }

        # Check if workflow has permissions section
        permissions = workflow_data.get("permissions", {})

        # Analyze workflow for repository operations
        needs_write_permissions = self._analyze_workflow_operations(workflow_data)

        # Validate permissions
        return self._validate_permissions(workflow_file.name, permissions, needs_write_permissions)

    def _analyze_workflow_operations(self, workflow_data: dict) -> dict[str, bool]:
        """Analyze workflow for operations that require specific permissions.

        Args:
            workflow_data: Parsed workflow YAML data

        Returns:
            Dictionary indicating which permissions are needed
        """
        needs_permissions = {
            "contents_write": False,
            "security_events_write": False,
            "actions_write": False,
            "pull_requests_write": False,
        }

        # Check all jobs and steps
        jobs = workflow_data.get("jobs", {})

        for job_data in jobs.values():
            steps = job_data.get("steps", [])

            for step in steps:
                step_name = step.get("name", "")
                step_run = step.get("run", "")
                step_uses = step.get("uses", "")

                # Check for git operations that need write permissions
                if any(
                    keyword in step_run.lower()
                    for keyword in ["git commit", "git push", "git add", "commit -m", "push origin"]
                ):
                    needs_permissions["contents_write"] = True

                # Check for security report uploads
                if any(
                    keyword in step_name.lower()
                    for keyword in ["security", "upload", "sarif", "bandit", "audit"]
                ) and ("upload" in step_name.lower() or "actions/upload" in step_uses):
                    needs_permissions["security_events_write"] = True

                # Check for workflow dispatch operations
                if "workflow_dispatch" in step_run or "createWorkflowDispatch" in step_run:
                    needs_permissions["actions_write"] = True

                # Check for PR operations
                if any(
                    keyword in step_run.lower()
                    for keyword in ["pull_request", "pr comment", "github.rest.pulls"]
                ):
                    needs_permissions["pull_requests_write"] = True

        return needs_permissions

    def _validate_permissions(
        self, workflow_name: str, permissions: dict, needs_permissions: dict[str, bool]
    ) -> dict:
        """Validate that workflow has appropriate permissions.

        Args:
            workflow_name: Name of the workflow file
            permissions: Permissions section from workflow
            needs_permissions: Required permissions based on operations

        Returns:
            Validation result dictionary
        """
        issues = []

        # Check contents permission
        if needs_permissions["contents_write"]:
            contents_perm = permissions.get("contents", "none")
            if contents_perm != "write":
                issues.append(f"Needs 'contents: write' but has '{contents_perm}'")

        # Check security-events permission
        if needs_permissions["security_events_write"]:
            security_perm = permissions.get("security-events", "none")
            if security_perm != "write":
                issues.append(f"Needs 'security-events: write' but has '{security_perm}'")

        # Check actions permission
        if needs_permissions["actions_write"]:
            actions_perm = permissions.get("actions", "none")
            if actions_perm not in ["write", "read"]:
                issues.append(f"Needs 'actions: write' but has '{actions_perm}'")

        # Check pull-requests permission
        if needs_permissions["pull_requests_write"]:
            pr_perm = permissions.get("pull-requests", "none")
            if pr_perm != "write":
                issues.append(f"Needs 'pull-requests: write' but has '{pr_perm}'")

        # Determine overall status
        if issues:
            status = "FAIL"
            message = f"Permission issues: {'; '.join(issues)}"
        else:
            status = "PASS"
            message = "All required permissions properly configured"

        return {
            "workflow": workflow_name,
            "status": status,
            "message": message,
            "details": {
                "permissions": permissions,
                "needs_permissions": needs_permissions,
                "issues": issues,
            },
        }

    def test_git_operations(self) -> bool:
        """Test that git operations work with current configuration.

        Returns:
            True if git operations work, False otherwise
        """
        print("\n🔧 Testing git operations...")

        try:
            # Check git configuration
            result = subprocess.run(
                ["git", "config", "--get", "user.name"],
                check=False,
                capture_output=True,
                text=True,
                cwd=self.repo_root,
            )

            if result.returncode != 0:
                print("❌ Git user.name not configured")
                return False

            result = subprocess.run(
                ["git", "config", "--get", "user.email"],
                check=False,
                capture_output=True,
                text=True,
                cwd=self.repo_root,
            )

            if result.returncode != 0:
                print("❌ Git user.email not configured")
                return False

            # Test git status (should work with read permissions)
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                check=False,
                capture_output=True,
                text=True,
                cwd=self.repo_root,
            )

            if result.returncode != 0:
                print(f"❌ Git status failed: {result.stderr}")
                return False

            print("✅ Git operations configured correctly")
            return True

        except Exception as e:
            print(f"❌ Git operations test failed: {e}")
            return False

    def test_github_token_access(self) -> bool:
        """Test GitHub token access and permissions.

        Returns:
            True if token access works, False otherwise
        """
        print("\n🔑 Testing GitHub token access...")

        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            print("⚠️  GITHUB_TOKEN not available (expected in CI environment)")
            return True  # Not a failure in local environment

        try:
            # Test token by checking repository access
            repo_name = os.getenv("GITHUB_REPOSITORY", "unknown/unknown")

            # Use curl to test API access with timeout for GitHub Actions
            # GitHub Actions can have variable network performance, so use longer timeout
            result = subprocess.run(
                [
                    "curl",
                    "-s",
                    "--max-time",
                    "30",  # 30 seconds timeout for GitHub Actions environment
                    "-H",
                    f"Authorization: token {github_token}",
                    f"https://api.github.com/repos/{repo_name}",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                try:
                    repo_data = json.loads(result.stdout)
                    if "id" in repo_data:
                        print("✅ GitHub token access verified")
                        return True
                except json.JSONDecodeError:
                    pass

            print(f"❌ GitHub token access failed: {result.stderr}")
            return False

        except Exception as e:
            print(f"❌ GitHub token test failed: {e}")
            return False

    def generate_report(self) -> dict:
        """Generate a comprehensive test report.

        Returns:
            Test report dictionary
        """
        passed_tests = sum(1 for result in self.test_results if result["status"] == "PASS")
        total_tests = len(self.test_results)

        return {
            "summary": {
                "total_workflows": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            },
            "test_results": self.test_results,
            "recommendations": self._generate_recommendations(),
        }

    def _generate_recommendations(self) -> list[str]:
        """Generate recommendations based on test results.

        Returns:
            List of recommendation strings
        """
        recommendations = []

        failed_tests = [r for r in self.test_results if r["status"] == "FAIL"]

        if failed_tests:
            recommendations.append(
                "Fix workflow permission configurations before deploying to production"
            )

            for test in failed_tests:
                workflow = test["workflow"]
                issues = test["details"].get("issues", [])
                for issue in issues:
                    recommendations.append(f"{workflow}: {issue}")

        else:
            recommendations.append("All workflow permissions are properly configured")

        return recommendations


def main() -> int:
    """Main function to run workflow permission tests."""
    repo_root = Path.cwd()

    print("🚀 GitHub Actions Workflow Permission Validation")
    print("=" * 50)

    tester = WorkflowPermissionTester(repo_root)

    # Run all tests
    workflows_passed = tester.test_all_workflows()
    git_passed = tester.test_git_operations()
    token_passed = tester.test_github_token_access()

    # Generate report
    report = tester.generate_report()

    print("\n📊 Test Summary")
    print("=" * 20)
    print(f"Workflows tested: {report['summary']['total_workflows']}")
    print(f"Tests passed: {report['summary']['passed_tests']}")
    print(f"Tests failed: {report['summary']['failed_tests']}")
    print(f"Success rate: {report['summary']['success_rate']:.1f}%")

    if report["recommendations"]:
        print("\n💡 Recommendations:")
        for rec in report["recommendations"]:
            print(f"  • {rec}")

    # Save detailed report
    report_file = repo_root / "workflow_permission_test_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n📄 Detailed report saved to: {report_file}")

    # Determine overall success
    overall_success = workflows_passed and git_passed and token_passed

    if overall_success:
        print("\n✅ All workflow permission tests passed!")
        return 0
    print("\n❌ Some workflow permission tests failed!")
    return 1


if __name__ == "__main__":
    sys.exit(main())
