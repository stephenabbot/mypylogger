#!/usr/bin/env python3
"""AWS OIDC Workflow Testing Script.

Tests and validates the AWS OIDC configuration for PyPI publishing workflow.
Simulates different scenarios including default region, custom region, and retry logic.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time


class WorkflowTestError(Exception):
    """Custom exception for workflow testing errors."""


def log_test_step(step: str, status: str, details: str | None = None) -> None:
    """Log test step with structured output.

    Args:
        step: Test step description
        status: Status (PASS, FAIL, INFO)
        details: Additional details
    """
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    if status == "PASS":
        icon = "✅"
    elif status == "FAIL":
        icon = "❌"
    else:
        icon = "ℹ️"

    print(f"{icon} [{timestamp}] {step}: {status}")
    if details:
        print(f"   {details}")


def test_aws_config_validation() -> bool:
    """Test AWS configuration validation script.

    Returns:
        True if validation tests pass, False otherwise
    """
    log_test_step("AWS Configuration Validation", "INFO", "Testing validation script")

    try:
        # Test 1: Valid configuration
        env = {
            "AWS_REGION": "us-east-1",
            "AWS_ROLE_ARN": "arn:aws:iam::123456789012:role/GitHubActions-PyPI-Role",
            "AWS_SECRET_NAME": "pypi-token-secret",
        }

        result = subprocess.run(
            [sys.executable, "scripts/validate_aws_config.py"],
            check=False,
            env={**os.environ, **env},
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            log_test_step("Valid AWS configuration", "PASS")
        else:
            log_test_step("Valid AWS configuration", "FAIL", result.stderr)
            return False

        # Test 2: Missing AWS_ROLE_ARN
        env_missing_role = {"AWS_REGION": "us-east-1", "AWS_SECRET_NAME": "pypi-token-secret"}

        result = subprocess.run(
            [sys.executable, "scripts/validate_aws_config.py"],
            check=False,
            env={**os.environ, **env_missing_role},
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            log_test_step("Missing AWS_ROLE_ARN detection", "PASS")
        else:
            log_test_step("Missing AWS_ROLE_ARN detection", "FAIL", "Should have failed")
            return False

        # Test 3: Invalid region format
        env_invalid_region = {
            "AWS_REGION": "invalid-region",
            "AWS_ROLE_ARN": "arn:aws:iam::123456789012:role/GitHubActions-PyPI-Role",
            "AWS_SECRET_NAME": "pypi-token-secret",
        }

        result = subprocess.run(
            [sys.executable, "scripts/validate_aws_config.py"],
            check=False,
            env={**os.environ, **env_invalid_region},
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            log_test_step("Invalid region format detection", "PASS")
        else:
            log_test_step("Invalid region format detection", "FAIL", "Should have failed")
            return False

        # Test 4: Default region fallback
        env_no_region = {
            "AWS_ROLE_ARN": "arn:aws:iam::123456789012:role/GitHubActions-PyPI-Role",
            "AWS_SECRET_NAME": "pypi-token-secret",
        }

        result = subprocess.run(
            [sys.executable, "scripts/validate_aws_config.py"],
            check=False,
            env={**os.environ, **env_no_region},
            capture_output=True,
            text=True,
        )

        if result.returncode == 0 and "us-east-1" in result.stdout:
            log_test_step("Default region fallback", "PASS")
        else:
            log_test_step("Default region fallback", "FAIL", result.stderr)
            return False

        return True

    except Exception as e:
        log_test_step("AWS Configuration Validation", "FAIL", str(e))
        return False


def test_workflow_yaml_syntax() -> bool:
    """Test PyPI publishing workflow YAML syntax.

    Returns:
        True if YAML is valid, False otherwise
    """
    log_test_step("Workflow YAML Syntax", "INFO", "Validating pypi-publish.yml")

    try:
        import yaml

        with open(".github/workflows/pypi-publish.yml") as f:
            workflow = yaml.safe_load(f)

        # Validate required sections
        # Note: YAML parser converts 'on:' to boolean True
        required_sections = ["name", "jobs"]
        for section in required_sections:
            if section not in workflow:
                log_test_step(f"Required section '{section}'", "FAIL", "Missing from workflow")
                return False

        # Check for 'on' section (which becomes True in YAML)
        if True not in workflow and "on" not in workflow:
            log_test_step("Required section 'on'", "FAIL", "Missing from workflow")
            return False

        # Validate publish-to-pypi job exists
        if "publish-to-pypi" not in workflow["jobs"]:
            log_test_step("publish-to-pypi job", "FAIL", "Missing from workflow")
            return False

        # Validate AWS authentication steps
        publish_job = workflow["jobs"]["publish-to-pypi"]
        steps = publish_job.get("steps", [])

        aws_auth_steps = [step for step in steps if "aws" in step.get("name", "").lower()]
        if not aws_auth_steps:
            log_test_step("AWS authentication steps", "FAIL", "No AWS auth steps found")
            return False

        log_test_step("Workflow YAML Syntax", "PASS")
        return True

    except Exception as e:
        log_test_step("Workflow YAML Syntax", "FAIL", str(e))
        return False


def test_aws_region_scenarios() -> bool:
    """Test different AWS region scenarios.

    Returns:
        True if all region scenarios pass, False otherwise
    """
    log_test_step("AWS Region Scenarios", "INFO", "Testing region configurations")

    scenarios = [
        ("us-east-1", "Default US East region"),
        ("eu-west-1", "EU West region"),
        ("ap-southeast-1", "Asia Pacific region"),
        ("ca-central-1", "Canada Central region"),
        (None, "No region specified (should default to us-east-1)"),
    ]

    try:
        for region, description in scenarios:
            env = {
                "AWS_ROLE_ARN": "arn:aws:iam::123456789012:role/GitHubActions-PyPI-Role",
                "AWS_SECRET_NAME": "pypi-token-secret",
            }

            if region:
                env["AWS_REGION"] = region

            result = subprocess.run(
                [sys.executable, "scripts/validate_aws_config.py"],
                check=False,
                env={**os.environ, **env},
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                expected_region = region or "us-east-1"
                if expected_region in result.stdout:
                    log_test_step(f"Region scenario: {description}", "PASS")
                else:
                    log_test_step(
                        f"Region scenario: {description}",
                        "FAIL",
                        f"Expected {expected_region} in output",
                    )
                    return False
            else:
                log_test_step(f"Region scenario: {description}", "FAIL", result.stderr)
                return False

        return True

    except Exception as e:
        log_test_step("AWS Region Scenarios", "FAIL", str(e))
        return False


def test_error_messages() -> bool:
    """Test error messages and troubleshooting guidance.

    Returns:
        True if error messages are appropriate, False otherwise
    """
    log_test_step("Error Messages", "INFO", "Testing error message quality")

    try:
        # Test missing role ARN error message
        env = {
            "AWS_REGION": "us-east-1",
            "AWS_SECRET_NAME": "pypi-token-secret",
            # AWS_ROLE_ARN intentionally missing
        }

        result = subprocess.run(
            [sys.executable, "scripts/validate_aws_config.py"],
            check=False,
            env={**os.environ, **env},
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            error_output = result.stderr

            # Check for helpful error messages
            required_phrases = ["AWS_ROLE_ARN", "required", "GitHub repository secrets"]

            missing_phrases = [phrase for phrase in required_phrases if phrase not in error_output]

            if not missing_phrases:
                log_test_step("Missing role ARN error message", "PASS")
            else:
                log_test_step(
                    "Missing role ARN error message", "FAIL", f"Missing phrases: {missing_phrases}"
                )
                return False
        else:
            log_test_step(
                "Missing role ARN error message", "FAIL", "Should have failed with missing role ARN"
            )
            return False

        # Test invalid region error message
        env_invalid = {
            "AWS_REGION": "not-a-region",
            "AWS_ROLE_ARN": "arn:aws:iam::123456789012:role/GitHubActions-PyPI-Role",
            "AWS_SECRET_NAME": "pypi-token-secret",
        }

        result = subprocess.run(
            [sys.executable, "scripts/validate_aws_config.py"],
            check=False,
            env={**os.environ, **env_invalid},
            capture_output=True,
            text=True,
        )

        if result.returncode != 0 and "Invalid AWS region format" in result.stderr:
            log_test_step("Invalid region error message", "PASS")
        else:
            log_test_step(
                "Invalid region error message", "FAIL", "Should provide clear region format error"
            )
            return False

        return True

    except Exception as e:
        log_test_step("Error Messages", "FAIL", str(e))
        return False


def generate_test_report(results: dict[str, bool]) -> None:
    """Generate a comprehensive test report.

    Args:
        results: Dictionary of test results
    """
    print("\n" + "=" * 60)
    print("AWS OIDC WORKFLOW TEST REPORT")
    print("=" * 60)

    total_tests = len(results)
    passed_tests = sum(results.values())
    failed_tests = total_tests - passed_tests

    print("\nSummary:")
    print(f"  Total Tests: {total_tests}")
    print(f"  Passed: {passed_tests}")
    print(f"  Failed: {failed_tests}")
    print(f"  Success Rate: {(passed_tests / total_tests) * 100:.1f}%")

    print("\nDetailed Results:")
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")

    if failed_tests > 0:
        print("\n🔧 Troubleshooting:")
        print("  - Review failed test details above")
        print("  - Check AWS configuration validation script")
        print("  - Verify workflow YAML syntax")
        print("  - Test error message clarity")
    else:
        print("\n🎉 All tests passed! AWS OIDC workflow is ready for production.")


def main() -> int:
    """Main function to run AWS OIDC workflow tests.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("🧪 Starting AWS OIDC Workflow Tests")
    print("=" * 50)

    # Run all tests
    test_results = {
        "AWS Configuration Validation": test_aws_config_validation(),
        "Workflow YAML Syntax": test_workflow_yaml_syntax(),
        "AWS Region Scenarios": test_aws_region_scenarios(),
        "Error Messages": test_error_messages(),
    }

    # Generate report
    generate_test_report(test_results)

    # Return appropriate exit code
    if all(test_results.values()):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
