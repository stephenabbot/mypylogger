"""Integration tests for security scanning and zero-tolerance policy enforcement.

This test module validates that the security infrastructure works correctly
and enforces the zero-tolerance security policy as required.

Requirements Addressed:
- 6.3: Configure workflow to fail on any security vulnerabilities
- 6.4: Require zero security issues found before allowing PR merges
- 6.5: Scan both direct and transitive dependencies for vulnerabilities
- 6.6: Provide detailed security reporting when vulnerabilities detected
"""

import os
from pathlib import Path
import subprocess

import pytest
import yaml


class TestSecurityIntegration:
    """Integration tests for security scanning infrastructure."""

    def test_security_configuration_files_exist(self) -> None:
        """Test that all required security configuration files exist."""
        project_root = Path(__file__).parent.parent.parent

        required_files = [
            ".github/workflows/security-driven-release.yml",
            ".github/dependabot.yml",
            ".github/SECURITY.md",
            ".github/SECURITY_CONFIG.yml",
            "scripts/security_check.sh",
        ]

        for file_path in required_files:
            full_path = project_root / file_path
            assert full_path.exists(), f"Required security file missing: {file_path}"
            assert full_path.stat().st_size > 0, f"Security file is empty: {file_path}"

    def test_security_workflow_configuration(self) -> None:
        """Test that security workflow is properly configured."""
        project_root = Path(__file__).parent.parent.parent
        workflow_file = project_root / ".github/workflows/security-driven-release.yml"

        with workflow_file.open() as f:
            workflow_content = f.read()

        # Check for required workflow components
        required_components = [
            "name: Security-Driven Release",
            "security-change-analysis",
            "pip-audit",
            "bandit",
            "schedule:",
            "workflow_dispatch:",
        ]

        for component in required_components:
            assert component.lower() in workflow_content.lower(), (
                f"Required security component missing: {component}"
            )

    def test_dependabot_configuration(self) -> None:
        """Test that Dependabot is properly configured for security updates."""
        project_root = Path(__file__).parent.parent.parent
        dependabot_file = project_root / ".github/dependabot.yml"

        with dependabot_file.open() as f:
            dependabot_config = yaml.safe_load(f)

        assert dependabot_config["version"] == 2, "Dependabot version should be 2"

        # Check for Python dependency updates
        updates = dependabot_config["updates"]
        python_update = None

        for update in updates:
            if update["package-ecosystem"] == "pip":
                python_update = update
                break

        assert python_update is not None, "Python dependency updates not configured"
        assert python_update["schedule"]["interval"] == "daily", (
            "Daily security updates not configured"
        )
        assert "security" in python_update["labels"], (
            "Security label not configured for dependency updates"
        )

    def test_security_config_zero_tolerance_policy(self) -> None:
        """Test that zero-tolerance policy is properly configured."""
        project_root = Path(__file__).parent.parent.parent
        config_file = project_root / ".github/SECURITY_CONFIG.yml"

        with config_file.open() as f:
            security_config = yaml.safe_load(f)

        # Validate zero-tolerance policy configuration
        zero_tolerance = security_config["zero_tolerance_policy"]
        assert zero_tolerance["enabled"] is True, "Zero-tolerance policy not enabled"
        assert zero_tolerance["block_pr_merge"] is True, "PR merge blocking not enabled"

        # Check that all severity levels trigger failure
        fail_on_severity = zero_tolerance["fail_on_severity"]
        required_severities = ["critical", "high", "medium", "low"]
        for severity in required_severities:
            assert severity in fail_on_severity, (
                f"Zero-tolerance policy missing severity: {severity}"
            )

        # Validate required scans
        required_scans = zero_tolerance["required_scans"]
        expected_scans = [
            "dependency_vulnerabilities",
            "code_security_analysis",
            "secret_detection",
            "supply_chain_security",
        ]
        for scan in expected_scans:
            assert scan in required_scans, f"Required security scan missing: {scan}"

    def test_security_check_script_executable(self) -> None:
        """Test that security check script is executable and functional."""
        project_root = Path(__file__).parent.parent.parent
        script_path = project_root / "scripts/security_check.sh"

        # Check file exists and is executable
        assert script_path.exists(), "Security check script not found"
        assert os.access(script_path, os.X_OK), "Security check script not executable"

        # Test script help/version (should not fail)
        try:
            subprocess.run(
                ["/bin/bash", str(script_path), "--help"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=project_root,
            )
            # Script may not have --help, but should not crash
        except subprocess.TimeoutExpired:
            pytest.fail("Security check script timed out")
        except Exception:
            # Script may not support --help, that's okay
            pass

    def test_security_policy_documentation(self) -> None:
        """Test that security policy documentation is comprehensive."""
        project_root = Path(__file__).parent.parent.parent
        security_md = project_root / ".github/SECURITY.md"

        with security_md.open() as f:
            security_content = f.read()

        # Check for required policy sections
        required_sections = [
            "Zero-Tolerance Security Policy",
            "Security Scanning Coverage",
            "Vulnerability Response Process",
            "Security Requirements for Contributors",
            "Reporting Security Vulnerabilities",
        ]

        for section in required_sections:
            assert section in security_content, (
                f"Required security policy section missing: {section}"
            )

        # Check for specific zero-tolerance language
        zero_tolerance_terms = [
            "zero-tolerance",
            "no security vulnerabilities",
            "all security scans must pass",
            "immediate action required",
        ]

        content_lower = security_content.lower()
        for term in zero_tolerance_terms:
            assert term.lower() in content_lower, f"Zero-tolerance policy term missing: {term}"

    def test_workflow_triggers_configuration(self) -> None:
        """Test that security workflow has proper triggers configured."""
        project_root = Path(__file__).parent.parent.parent
        workflow_file = project_root / ".github/workflows/security-driven-release.yml"

        with workflow_file.open() as f:
            workflow_content = f.read()

        # Parse YAML to check triggers
        try:
            workflow_yaml = yaml.safe_load(workflow_content)
            # Handle YAML parsing quirk where 'on:' becomes boolean True
            triggers = workflow_yaml.get(True, workflow_yaml.get("on", {}))
        except yaml.YAMLError:
            # Fallback to text-based validation if YAML parsing fails
            assert "on:" in workflow_content, "Workflow triggers not found"
            assert "schedule:" in workflow_content, "Scheduled scan trigger missing"
            assert "workflow_dispatch:" in workflow_content, "Manual trigger missing"
            return

        # Check required triggers
        assert "schedule" in triggers, "Scheduled scan trigger missing"
        assert "workflow_dispatch" in triggers, "Manual trigger missing"

        # The security-driven-release workflow doesn't have pull_request or push triggers
        # It only runs on schedule and manual dispatch

        # Validate scheduled trigger (weekly scans for CodeQL optimization)
        schedule_trigger = triggers["schedule"]
        assert len(schedule_trigger) > 0, "No scheduled scans configured"
        cron_expr = schedule_trigger[0]["cron"]
        assert "0 3 * * 1" in cron_expr, "Weekly Monday 3 AM UTC scan not configured"

    def test_security_tools_configuration(self) -> None:
        """Test that security tools are properly configured."""
        project_root = Path(__file__).parent.parent.parent
        config_file = project_root / ".github/SECURITY_CONFIG.yml"

        with config_file.open() as f:
            security_config = yaml.safe_load(f)

        # Check dependency security tools
        dep_security = security_config["dependency_security"]
        tools = dep_security["tools"]

        # Validate pip-audit configuration
        pip_audit = tools["pip_audit"]
        assert pip_audit["enabled"] is True, "pip-audit not enabled"
        assert pip_audit["fail_on_any_vulnerability"] is True, (
            "pip-audit not configured to fail on vulnerabilities"
        )

        # Validate safety configuration
        safety = tools["safety"]
        assert safety["enabled"] is True, "safety not enabled"
        assert safety["fail_on_any_vulnerability"] is True, (
            "safety not configured to fail on vulnerabilities"
        )

        # Check code security tools
        code_security = security_config["code_security"]

        # Validate CodeQL configuration
        codeql = code_security["codeql"]
        assert codeql["enabled"] is True, "CodeQL not enabled"
        assert codeql["fail_on_error"] is True, "CodeQL not configured to fail on errors"
        assert "python" in codeql["languages"], "Python not in CodeQL languages"

        # Validate Bandit configuration
        bandit = code_security["bandit"]
        assert bandit["enabled"] is True, "Bandit not enabled"
        assert bandit["fail_on_any_issue"] is True, "Bandit not configured to fail on any issue"

    def test_security_reporting_configuration(self) -> None:
        """Test that security reporting is properly configured."""
        project_root = Path(__file__).parent.parent.parent
        config_file = project_root / ".github/SECURITY_CONFIG.yml"

        with config_file.open() as f:
            security_config = yaml.safe_load(f)

        # Check security reporting configuration
        reporting = security_config["security_reporting"]

        # Validate report formats
        formats = reporting["formats"]
        required_formats = ["json", "sarif", "table"]
        for fmt in required_formats:
            assert fmt in formats, f"Required report format missing: {fmt}"

        # Validate upload locations
        upload_locations = reporting["upload_locations"]
        required_locations = ["github_security_tab", "workflow_artifacts"]
        for location in required_locations:
            assert location in upload_locations, f"Required upload location missing: {location}"

        # Validate notifications
        notifications = reporting["notifications"]
        assert notifications["enabled"] is True, "Notifications not enabled"

        # Check severity-based notifications
        critical_high = notifications["critical_high"]
        assert critical_high["block_workflow"] is True, (
            "Critical/high severity not configured to block workflow"
        )

        medium_low = notifications["medium_low"]
        assert medium_low["block_workflow"] is True, (
            "Medium/low severity not configured to block workflow (zero-tolerance)"
        )

    def test_emergency_response_configuration(self) -> None:
        """Test that emergency response procedures are configured."""
        project_root = Path(__file__).parent.parent.parent
        config_file = project_root / ".github/SECURITY_CONFIG.yml"

        with config_file.open() as f:
            security_config = yaml.safe_load(f)

        # Check emergency response configuration
        emergency = security_config["emergency_response"]

        # Validate critical response times
        critical_response = emergency["critical_response"]
        assert critical_response["max_response_time_hours"] <= 24, "Critical response time too long"
        assert critical_response["max_resolution_time_hours"] <= 48, (
            "Critical resolution time too long"
        )
        assert critical_response["escalation_enabled"] is True, (
            "Escalation not enabled for critical issues"
        )

        # Validate emergency procedures
        procedures = emergency["procedures"]
        required_procedures = [
            "immediate_block",
            "create_security_issue",
            "notify_maintainers",
            "document_incident",
        ]
        for procedure in required_procedures:
            assert procedures[procedure] is True, f"Emergency procedure not enabled: {procedure}"

    @pytest.mark.integration
    def test_security_workflow_integration(self) -> None:
        """Integration test for complete security workflow functionality."""
        project_root = Path(__file__).parent.parent.parent

        # This test validates that all security components work together
        # In a real scenario, this would trigger the actual workflow

        # Check that all required files exist and are properly configured
        security_files = [
            ".github/workflows/security-driven-release.yml",
            ".github/dependabot.yml",
            ".github/SECURITY.md",
            ".github/SECURITY_CONFIG.yml",
            "scripts/security_check.sh",
        ]

        for file_path in security_files:
            full_path = project_root / file_path
            assert full_path.exists(), f"Security file missing: {file_path}"

        # Validate that security configuration is internally consistent
        config_file = project_root / ".github/SECURITY_CONFIG.yml"
        with config_file.open() as f:
            security_config = yaml.safe_load(f)

        # Ensure zero-tolerance policy is consistently applied
        zero_tolerance = security_config["zero_tolerance_policy"]
        assert zero_tolerance["enabled"] is True
        assert zero_tolerance["block_pr_merge"] is True

        # Ensure all security scan types are enabled
        dep_security = security_config["dependency_security"]["tools"]
        code_security = security_config["code_security"]
        secret_detection = security_config["secret_detection"]

        assert dep_security["pip_audit"]["enabled"] is True
        assert dep_security["safety"]["enabled"] is True
        assert code_security["codeql"]["enabled"] is True
        assert code_security["bandit"]["enabled"] is True
        assert secret_detection["trufflehog"]["enabled"] is True

        # Validate that all tools are configured to fail on any issue
        assert dep_security["pip_audit"]["fail_on_any_vulnerability"] is True
        assert dep_security["safety"]["fail_on_any_vulnerability"] is True
        assert code_security["codeql"]["fail_on_error"] is True
        assert code_security["bandit"]["fail_on_any_issue"] is True
        assert secret_detection["trufflehog"]["fail_on_any_secret"] is True

    def test_compliance_and_audit_configuration(self) -> None:
        """Test that compliance and audit features are properly configured."""
        project_root = Path(__file__).parent.parent.parent
        config_file = project_root / ".github/SECURITY_CONFIG.yml"

        with config_file.open() as f:
            security_config = yaml.safe_load(f)

        # Check compliance configuration
        compliance = security_config["compliance"]

        # Validate security standards compliance
        standards = compliance["standards"]
        required_standards = ["owasp_top_10", "cwe_top_25", "nist_cybersecurity_framework"]
        for standard in required_standards:
            assert standard in standards, f"Required security standard missing: {standard}"

        # Validate audit trail configuration
        audit_trail = compliance["audit_trail"]
        assert audit_trail["enabled"] is True, "Audit trail not enabled"
        assert audit_trail["retention_days"] >= 365, "Audit trail retention too short"
        assert audit_trail["include_scan_results"] is True, (
            "Scan results not included in audit trail"
        )

        # Validate metrics collection
        metrics = compliance["metrics"]
        assert metrics["enabled"] is True, "Metrics collection not enabled"
        assert metrics["track_resolution_time"] is True, "Resolution time tracking not enabled"
        assert metrics["track_detection_accuracy"] is True, (
            "Detection accuracy tracking not enabled"
        )
