"""Unit tests for credential security validator."""

import os
from pathlib import Path

# Import the module we're testing
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from credential_security_validator import CredentialSecurityValidator


class TestCredentialSecurityValidator:
    """Test cases for CredentialSecurityValidator."""

    def test_initialization(self) -> None:
        """Test CredentialSecurityValidator initialization."""
        workspace = Path("/test/workspace")
        validator = CredentialSecurityValidator(workspace)

        assert validator.workspace_root == workspace
        assert validator.violations == []

    def test_initialization_with_default(self) -> None:
        """Test CredentialSecurityValidator initialization with default workspace."""
        validator = CredentialSecurityValidator()

        assert validator.workspace_root == Path()

    def test_credential_patterns(self) -> None:
        """Test that credential patterns are properly defined."""
        validator = CredentialSecurityValidator()

        # Verify we have expected patterns
        assert len(validator.CREDENTIAL_PATTERNS) > 0

        # Test PyPI token pattern
        pypi_pattern = next(p for p in validator.CREDENTIAL_PATTERNS if "pypi-" in p)
        assert pypi_pattern is not None

        # Test GitHub token patterns
        github_patterns = [p for p in validator.CREDENTIAL_PATTERNS if "ghp_" in p or "ghs_" in p]
        assert len(github_patterns) > 0

    def test_safe_patterns(self) -> None:
        """Test that safe patterns are properly defined."""
        validator = CredentialSecurityValidator()

        # Verify we have expected safe patterns
        assert len(validator.SAFE_PATTERNS) > 0

        # Test masked pattern
        masked_pattern = next(p for p in validator.SAFE_PATTERNS if r"\*+" in p)
        assert masked_pattern is not None

    def test_is_safe_line_comments(self) -> None:
        """Test safe line detection for comments."""
        validator = CredentialSecurityValidator()

        safe_lines = [
            "# This is a comment",
            "// This is a comment",
            "/* This is a comment */",
            "* This is a comment",
            "<!-- This is a comment -->",
            "   # Indented comment",
            "",
            "   ",
            '"""This is a docstring"""',
            "'''This is a docstring'''",
        ]

        for line in safe_lines:
            assert validator._is_safe_line(line), f"Line should be safe: {line}"

    def test_is_safe_line_code(self) -> None:
        """Test safe line detection for code."""
        validator = CredentialSecurityValidator()

        unsafe_lines = [
            'token = "pypi-abc123"',
            "GITHUB_TOKEN = ghp_abc123",
            'password = "secret123"',
            'api_key = "some-key-value"',
        ]

        for line in unsafe_lines:
            assert not validator._is_safe_line(line), f"Line should not be safe: {line}"

    def test_is_safe_credential_masked(self) -> None:
        """Test safe credential detection for masked values."""
        validator = CredentialSecurityValidator()

        safe_credentials = [
            "***",
            "xxx",
            "example-token",
            "placeholder-value",
            "your-token-here",
            "test-token",
            "demo-key",
            "sample-value",
            "redacted",
            "masked",
            "hidden",
        ]

        for credential in safe_credentials:
            assert validator._is_safe_credential(credential), (
                f"Credential should be safe: {credential}"
            )

    def test_is_safe_credential_real(self) -> None:
        """Test safe credential detection for real-looking values."""
        validator = CredentialSecurityValidator()

        unsafe_credentials = [
            "pypi-AgEIcHlwaS5vcmcCJRVOaXMxLjAyAAABhGlkAAABhGh0dHBzOi8vcHlwaS5vcmcvbGVnYWN5Lw",
            "ghp_1234567890abcdef1234567890abcdef12",
            "AKIAIOSFODNN7EXAMPLE",
            "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        ]

        for credential in unsafe_credentials:
            assert not validator._is_safe_credential(credential), (
                f"Credential should not be safe: {credential}"
            )

    def test_determine_severity_pypi(self) -> None:
        """Test severity determination for PyPI tokens."""
        validator = CredentialSecurityValidator()

        severity = validator._determine_severity(r"pypi-[A-Za-z0-9_-]{50,}", "pypi-test-token")
        assert severity == "HIGH"

    def test_determine_severity_github(self) -> None:
        """Test severity determination for GitHub tokens."""
        validator = CredentialSecurityValidator()

        patterns = [r"ghp_[A-Za-z0-9]{36}", r"ghs_[A-Za-z0-9]{36}", r"github_pat_[A-Za-z0-9_]{82}"]

        for pattern in patterns:
            severity = validator._determine_severity(pattern, "test-token")
            assert severity == "HIGH"

    def test_determine_severity_aws(self) -> None:
        """Test severity determination for AWS keys."""
        validator = CredentialSecurityValidator()

        severity = validator._determine_severity(r"AKIA[0-9A-Z]{16}", "AKIATEST")
        assert severity == "HIGH"

    def test_determine_severity_long_token(self) -> None:
        """Test severity determination for long tokens."""
        validator = CredentialSecurityValidator()

        long_token = "a" * 60
        severity = validator._determine_severity(r"[A-Za-z0-9/+=]{40}", long_token)
        assert severity == "MEDIUM"

    def test_determine_severity_short_token(self) -> None:
        """Test severity determination for short tokens."""
        validator = CredentialSecurityValidator()

        short_token = "a" * 30
        severity = validator._determine_severity(r"[A-Za-z0-9/+=]{40}", short_token)
        assert severity == "LOW"

    def test_scan_file_for_credentials_with_violations(self) -> None:
        """Test file scanning with credential violations."""
        validator = CredentialSecurityValidator()

        file_content = """
# This is a safe comment
token = "pypi-AgEIcHlwaS5vcmcCJRVOaXMxLjAyAAABhGlkAAABhGh0dHBzOi8vcHlwaS5vcmcvbGVnYWN5Lw"
github_token = ghp_1234567890abcdef1234567890abcdef12
# Another safe comment
aws_key = AKIAIOSFODNN7EXAMPLE
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(file_content)
            f.flush()

            try:
                violations = validator.scan_file_for_credentials(Path(f.name))

                # Should find violations for PyPI token, GitHub token, and AWS key
                assert len(violations) >= 3

                # Check that violations have required fields
                for violation in violations:
                    assert "file" in violation
                    assert "line" in violation
                    assert "pattern" in violation
                    assert "matched_text" in violation
                    assert "severity" in violation

            finally:
                Path(f.name).unlink()

    def test_scan_file_for_credentials_safe_content(self) -> None:
        """Test file scanning with safe content."""
        validator = CredentialSecurityValidator()

        file_content = """
# This is a safe comment
token = "***"
github_token = "example-token"
# Another safe comment
aws_key = "your-key-here"
placeholder = "xxx"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(file_content)
            f.flush()

            try:
                violations = validator.scan_file_for_credentials(Path(f.name))

                # Should find no violations
                assert len(violations) == 0

            finally:
                Path(f.name).unlink()

    def test_scan_file_for_credentials_file_not_found(self) -> None:
        """Test file scanning with non-existent file."""
        validator = CredentialSecurityValidator()

        violations = validator.scan_file_for_credentials(Path("/non/existent/file.py"))

        # Should return empty list without crashing
        assert violations == []

    def test_scan_workflow_files_no_directory(self) -> None:
        """Test workflow file scanning with no workflows directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            validator = CredentialSecurityValidator(Path(temp_dir))

            violations = validator.scan_workflow_files()

            assert violations == []

    def test_scan_workflow_files_with_violations(self) -> None:
        """Test workflow file scanning with violations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            workflows_dir = workspace / ".github" / "workflows"
            workflows_dir.mkdir(parents=True)

            # Create a workflow file with a credential
            workflow_content = """
name: Test Workflow
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Test
        env:
          TOKEN: pypi-AgEIcHlwaS5vcmcCJRVOaXMxLjAyAAABhGlkAAABhGh0dHBzOi8vcHlwaS5vcmcvbGVnYWN5Lw
        run: echo "test"
"""

            workflow_file = workflows_dir / "test.yml"
            workflow_file.write_text(workflow_content)

            validator = CredentialSecurityValidator(workspace)
            violations = validator.scan_workflow_files()

            assert len(violations) > 0
            assert any("pypi-" in v["matched_text"] for v in violations)

    def test_scan_script_files_no_directory(self) -> None:
        """Test script file scanning with no scripts directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            validator = CredentialSecurityValidator(Path(temp_dir))

            violations = validator.scan_script_files()

            assert violations == []

    def test_scan_script_files_with_violations(self) -> None:
        """Test script file scanning with violations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            scripts_dir = workspace / "scripts"
            scripts_dir.mkdir()

            # Create a script file with a credential
            script_content = """#!/bin/bash
export GITHUB_TOKEN=ghp_1234567890abcdef1234567890abcdef12
echo "Running script"
"""

            script_file = scripts_dir / "test.sh"
            script_file.write_text(script_content)

            validator = CredentialSecurityValidator(workspace)
            violations = validator.scan_script_files()

            assert len(violations) > 0
            assert any("ghp_" in v["matched_text"] for v in violations)

    def test_validate_environment_variables_no_sensitive_vars(self) -> None:
        """Test environment variable validation with no sensitive variables."""
        validator = CredentialSecurityValidator()

        with patch.dict(os.environ, {}, clear=True):
            violations = validator.validate_environment_variables()

            assert violations == []

    def test_validate_environment_variables_with_safe_vars(self) -> None:
        """Test environment variable validation with safe variables."""
        validator = CredentialSecurityValidator()

        safe_env = {
            "PYPI_API_TOKEN": "***",
            "GITHUB_TOKEN": "example-token",
            "AWS_ACCESS_KEY_ID": "your-key-here",
        }

        with patch.dict(os.environ, safe_env, clear=True):
            violations = validator.validate_environment_variables()

            assert violations == []

    def test_validate_environment_variables_with_unsafe_vars(self) -> None:
        """Test environment variable validation with unsafe variables."""
        validator = CredentialSecurityValidator()

        unsafe_env = {
            "PYPI_API_TOKEN": (
                "pypi-AgEIcHlwaS5vcmcCJRVOaXMxLjAyAAABhGlkAAABhGh0dHBzOi8vcHlwaS5vcmcvbGVnYWN5Lw"
            ),
            "GITHUB_TOKEN": "ghp_1234567890abcdef1234567890abcdef12",
        }

        with patch.dict(os.environ, unsafe_env, clear=True):
            violations = validator.validate_environment_variables()

            assert len(violations) >= 2
            assert all(v["severity"] == "HIGH" for v in violations)

    def test_check_github_secrets_usage_no_directory(self) -> None:
        """Test GitHub secrets usage check with no workflows directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            validator = CredentialSecurityValidator(Path(temp_dir))

            violations = validator.check_github_secrets_usage()

            assert violations == []

    def test_check_github_secrets_usage_proper_usage(self) -> None:
        """Test GitHub secrets usage check with proper usage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            workflows_dir = workspace / ".github" / "workflows"
            workflows_dir.mkdir(parents=True)

            # Create a workflow file with proper secrets usage
            workflow_content = """
name: Test Workflow
jobs:
  test:
    steps:
      - name: Test
        env:
          AWS_ROLE_ARN: ${{ secrets.AWS_ROLE_ARN }}
          AWS_SECRET_NAME: ${{ secrets.AWS_SECRET_NAME }}
        run: echo "test"
"""

            workflow_file = workflows_dir / "test.yml"
            workflow_file.write_text(workflow_content)

            validator = CredentialSecurityValidator(workspace)
            violations = validator.check_github_secrets_usage()

            assert violations == []

    def test_check_github_secrets_usage_improper_usage(self) -> None:
        """Test GitHub secrets usage check with improper usage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            workflows_dir = workspace / ".github" / "workflows"
            workflows_dir.mkdir(parents=True)

            # Create a workflow file with improper secrets usage
            workflow_content = """
name: Test Workflow
jobs:
  test:
    steps:
      - name: Test
        env:
          AWS_ROLE_ARN: arn:aws:iam::123456789012:role/test-role
          AWS_SECRET_NAME: my-secret
        run: echo "test"
"""

            workflow_file = workflows_dir / "test.yml"
            workflow_file.write_text(workflow_content)

            validator = CredentialSecurityValidator(workspace)
            violations = validator.check_github_secrets_usage()

            assert len(violations) >= 2
            assert all(v["severity"] == "MEDIUM" for v in violations)

    def test_run_comprehensive_scan_clean(self) -> None:
        """Test comprehensive scan with clean workspace."""
        with tempfile.TemporaryDirectory() as temp_dir:
            validator = CredentialSecurityValidator(Path(temp_dir))

            with patch.dict(os.environ, {}, clear=True):
                results = validator.run_comprehensive_scan()

            # Should have all categories
            expected_categories = [
                "workflow_files",
                "script_files",
                "log_files",
                "environment_variables",
                "github_secrets",
            ]

            for category in expected_categories:
                assert category in results
                assert results[category] == []

    def test_run_comprehensive_scan_with_violations(self) -> None:
        """Test comprehensive scan with violations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            # Create a script with violations
            scripts_dir = workspace / "scripts"
            scripts_dir.mkdir()
            script_file = scripts_dir / "test.py"
            script_file.write_text('token = "pypi-test-token-violation"')

            validator = CredentialSecurityValidator(workspace)

            unsafe_env = {"PYPI_API_TOKEN": "pypi-unsafe-token"}
            with patch.dict(os.environ, unsafe_env, clear=True):
                results = validator.run_comprehensive_scan()

            # Should find violations in script files and environment variables
            assert len(results["script_files"]) > 0
            assert len(results["environment_variables"]) > 0

    def test_generate_security_report_clean(self) -> None:
        """Test security report generation for clean scan."""
        validator = CredentialSecurityValidator()

        clean_results = {
            "workflow_files": [],
            "script_files": [],
            "log_files": [],
            "environment_variables": [],
            "github_secrets": [],
        }

        report = validator.generate_security_report(clean_results)

        assert "# Credential Security Scan Report" in report
        assert "✅ Security Status: CLEAN" in report
        assert "No credential security violations" in report

    def test_generate_security_report_with_violations(self) -> None:
        """Test security report generation with violations."""
        validator = CredentialSecurityValidator()

        results_with_violations = {
            "workflow_files": [
                {"file": "test.yml", "line": 5, "severity": "HIGH", "matched_text": "pypi-test..."}
            ],
            "script_files": [],
            "log_files": [],
            "environment_variables": [
                {"variable": "PYPI_API_TOKEN", "severity": "HIGH", "issue": "Token exposed"}
            ],
            "github_secrets": [],
        }

        report = validator.generate_security_report(results_with_violations)

        assert "# Credential Security Scan Report" in report
        assert "⚠️ Security Status: 2 ISSUES FOUND" in report
        assert "Workflow Files (1 issues)" in report
        assert "Environment Variables (1 issues)" in report
        assert "## Recommendations" in report


class TestCredentialSecurityValidatorSecurity:
    """Security-focused tests for credential security validator."""

    def test_no_false_positives_for_documentation(self) -> None:
        """Test that documentation examples don't trigger false positives."""
        validator = CredentialSecurityValidator()

        doc_content = """
# PyPI Token Configuration

To configure your PyPI token, set the following environment variable:

```bash
export PYPI_API_TOKEN="pypi-your-token-here"
```

Example token format: `pypi-AgEIcHlwaS5vcmcC...` (truncated for security)

For GitHub tokens, use the format: `ghp_example1234567890abcdef1234567890`
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(doc_content)
            f.flush()

            try:
                violations = validator.scan_file_for_credentials(Path(f.name))

                # Should not flag documentation examples
                assert len(violations) == 0

            finally:
                Path(f.name).unlink()

    def test_regex_injection_protection(self) -> None:
        """Test protection against regex injection attacks."""
        validator = CredentialSecurityValidator()

        # Test with malicious content that could cause regex issues
        malicious_content = """
token = "pypi-" + "A" * 1000000  # Very long string
regex_bomb = "((((((((((x))))))))))" * 1000
nested_groups = "(" * 100 + "test" + ")" * 100
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(malicious_content)
            f.flush()

            try:
                # Should not hang or crash
                violations = validator.scan_file_for_credentials(Path(f.name))

                # Should handle gracefully
                assert isinstance(violations, list)

            finally:
                Path(f.name).unlink()

    def test_file_permission_security(self) -> None:
        """Test handling of files with restricted permissions."""
        validator = CredentialSecurityValidator()

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write('token = "pypi-test-token"')
            f.flush()

            try:
                # Remove read permissions
                Path(f.name).chmod(0o000)

                # Should handle permission errors gracefully
                violations = validator.scan_file_for_credentials(Path(f.name))

                # Should return empty list without crashing
                assert violations == []

            finally:
                # Restore permissions for cleanup
                Path(f.name).chmod(0o644)
                Path(f.name).unlink()

    def test_large_file_handling(self) -> None:
        """Test handling of large files."""
        validator = CredentialSecurityValidator()

        # Create a large file with a credential at the end
        large_content = "# Safe comment\n" * 10000 + 'token = "pypi-test-token-at-end"'

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(large_content)
            f.flush()

            try:
                violations = validator.scan_file_for_credentials(Path(f.name))

                # Should find the credential even in a large file
                assert len(violations) > 0
                assert any("pypi-" in v["matched_text"] for v in violations)

            finally:
                Path(f.name).unlink()

    def test_unicode_and_encoding_handling(self) -> None:
        """Test handling of files with various encodings and Unicode."""
        validator = CredentialSecurityValidator()

        # Content with Unicode characters
        unicode_content = """
# Comment with émojis 🔐🔑
token = "pypi-test-token-with-unicode-context"
# More Unicode: 中文, العربية, русский
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(unicode_content)
            f.flush()

            try:
                violations = validator.scan_file_for_credentials(Path(f.name))

                # Should handle Unicode properly and find the credential
                assert len(violations) > 0
                assert any("pypi-" in v["matched_text"] for v in violations)

            finally:
                Path(f.name).unlink()

    def test_binary_file_handling(self) -> None:
        """Test handling of binary files."""
        validator = CredentialSecurityValidator()

        # Create a binary file
        binary_content = b"\x00\x01\x02pypi-test-token-in-binary\x03\x04\x05"

        with tempfile.NamedTemporaryFile(mode="wb", suffix=".bin", delete=False) as f:
            f.write(binary_content)
            f.flush()

            try:
                # Should handle binary files gracefully
                violations = validator.scan_file_for_credentials(Path(f.name))

                # Should not crash and may or may not find the credential
                assert isinstance(violations, list)

            finally:
                Path(f.name).unlink()
