"""Unit tests for security scanning integration."""

import os
import subprocess
from unittest.mock import Mock, patch
import urllib.error

from badges.security import (
    get_comprehensive_security_status,
    get_github_codeql_status,
    run_all_security_checks,
    run_bandit_scan,
    run_safety_check,
    run_semgrep_analysis,
    security_checks_passed,
    simulate_codeql_checks,
)


class TestBanditScan:
    """Test bandit security scanning functionality."""

    @patch("subprocess.run")
    def test_run_bandit_scan_success(self, mock_run: Mock) -> None:
        """Test successful bandit scan."""
        # Mock bandit version check
        mock_run.side_effect = [
            Mock(returncode=0, stdout="bandit 1.7.5", stderr=""),  # version check
            Mock(returncode=0, stdout='{"results": []}', stderr=""),  # scan
        ]

        result = run_bandit_scan()
        assert result is True
        assert mock_run.call_count == 2

    @patch("subprocess.run")
    def test_run_bandit_scan_with_issues(self, mock_run: Mock) -> None:
        """Test bandit scan with security issues found."""
        # Mock bandit version check and scan with issues
        mock_run.side_effect = [
            Mock(returncode=0, stdout="bandit 1.7.5", stderr=""),  # version check
            Mock(
                returncode=1,
                stdout='{"results": [{"issue_severity": "HIGH"}]}',
                stderr="",
            ),  # scan with issues
        ]

        result = run_bandit_scan()
        assert result is False

    @patch("subprocess.run")
    def test_run_bandit_scan_not_installed(self, mock_run: Mock) -> None:
        """Test bandit scan when bandit is not installed."""
        # Mock bandit not available, then successful install and scan
        mock_run.side_effect = [
            Mock(returncode=1, stdout="", stderr="command not found"),  # version check fails
            Mock(returncode=0, stdout="", stderr=""),  # install succeeds
            Mock(returncode=0, stdout='{"results": []}', stderr=""),  # scan succeeds
        ]

        result = run_bandit_scan()
        assert result is True
        assert mock_run.call_count == 3

    @patch("subprocess.run")
    def test_run_bandit_scan_install_fails(self, mock_run: Mock) -> None:
        """Test bandit scan when installation fails."""
        # Mock bandit not available and install fails
        mock_run.side_effect = [
            Mock(returncode=1, stdout="", stderr="command not found"),  # version check fails
            Mock(returncode=1, stdout="", stderr="install failed"),  # install fails
        ]

        result = run_bandit_scan()
        assert result is False

    @patch("subprocess.run")
    def test_run_bandit_scan_timeout(self, mock_run: Mock) -> None:
        """Test bandit scan timeout handling."""
        mock_run.side_effect = subprocess.TimeoutExpired("bandit", 30)

        result = run_bandit_scan()
        assert result is False

    @patch("subprocess.run")
    def test_run_bandit_scan_exception(self, mock_run: Mock) -> None:
        """Test bandit scan exception handling."""
        mock_run.side_effect = Exception("Unexpected error")

        result = run_bandit_scan()
        assert result is False


class TestSafetyCheck:
    """Test safety dependency scanning functionality."""

    @patch("subprocess.run")
    def test_run_safety_check_success(self, mock_run: Mock) -> None:
        """Test successful safety check."""
        # Mock safety version check and clean scan
        mock_run.side_effect = [
            Mock(returncode=0, stdout="safety 2.3.1", stderr=""),  # version check
            Mock(returncode=0, stdout="[]", stderr=""),  # clean scan
        ]

        result = run_safety_check()
        assert result is True

    @patch("subprocess.run")
    def test_run_safety_check_with_vulnerabilities(self, mock_run: Mock) -> None:
        """Test safety check with vulnerabilities found."""
        # Mock safety version check and scan with vulnerabilities
        mock_run.side_effect = [
            Mock(returncode=0, stdout="safety 2.3.1", stderr=""),  # version check
            Mock(
                returncode=1,
                stdout='[{"vulnerability": "CVE-2023-1234"}]',
                stderr="",
            ),  # vulnerabilities found
        ]

        result = run_safety_check()
        assert result is True  # MVP tolerant of vulnerabilities

    @patch("subprocess.run")
    def test_run_safety_check_not_installed(self, mock_run: Mock) -> None:
        """Test safety check when safety is not installed."""
        # Mock safety not available, then successful install and scan
        mock_run.side_effect = [
            Mock(returncode=1, stdout="", stderr="command not found"),  # version check fails
            Mock(returncode=0, stdout="", stderr=""),  # install succeeds
            Mock(returncode=0, stdout="[]", stderr=""),  # scan succeeds
        ]

        result = run_safety_check()
        assert result is True

    @patch("subprocess.run")
    def test_run_safety_check_stderr_vulnerabilities(self, mock_run: Mock) -> None:
        """Test safety check with vulnerabilities in stderr."""
        # Mock safety version check and scan with vulnerabilities in stderr
        mock_run.side_effect = [
            Mock(returncode=0, stdout="safety 2.3.1", stderr=""),  # version check
            Mock(
                returncode=1, stdout="", stderr="Found 2 vulnerabilities"
            ),  # vulnerabilities in stderr
        ]

        result = run_safety_check()
        assert result is True  # MVP tolerant of vulnerabilities

    @patch("subprocess.run")
    def test_run_safety_check_timeout(self, mock_run: Mock) -> None:
        """Test safety check timeout handling."""
        mock_run.side_effect = subprocess.TimeoutExpired("safety", 30)

        result = run_safety_check()
        assert result is False


class TestSemgrepAnalysis:
    """Test semgrep security analysis functionality."""

    @patch("subprocess.run")
    def test_run_semgrep_analysis_success(self, mock_run: Mock) -> None:
        """Test successful semgrep analysis."""
        # Mock semgrep version check and clean analysis
        mock_run.side_effect = [
            Mock(returncode=0, stdout="semgrep 1.45.0", stderr=""),  # version check
            Mock(returncode=0, stdout='{"results": []}', stderr=""),  # clean analysis
        ]

        result = run_semgrep_analysis()
        assert result is True

    @patch("subprocess.run")
    def test_run_semgrep_analysis_with_findings(self, mock_run: Mock) -> None:
        """Test semgrep analysis with security findings."""
        # Mock semgrep version check and analysis with findings
        mock_run.side_effect = [
            Mock(returncode=0, stdout="semgrep 1.45.0", stderr=""),  # version check
            Mock(
                returncode=0,
                stdout='{"results": [{"check_id": "python.lang.security"}]}',
                stderr="",
            ),  # findings
        ]

        result = run_semgrep_analysis()
        assert result is False

    @patch("subprocess.run")
    def test_run_semgrep_analysis_not_installed(self, mock_run: Mock) -> None:
        """Test semgrep analysis when semgrep is not installed."""
        # Mock semgrep not available
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="command not found")

        result = run_semgrep_analysis()
        assert result is True  # Should return True when not available

    @patch("subprocess.run")
    def test_run_semgrep_analysis_timeout(self, mock_run: Mock) -> None:
        """Test semgrep analysis timeout handling."""
        mock_run.side_effect = subprocess.TimeoutExpired("semgrep", 30)

        result = run_semgrep_analysis()
        assert result is False

    @patch("subprocess.run")
    def test_run_semgrep_analysis_exception(self, mock_run: Mock) -> None:
        """Test semgrep analysis exception handling."""
        mock_run.side_effect = Exception("Unexpected error")

        result = run_semgrep_analysis()
        assert result is True  # Should not fail build for semgrep issues


class TestCodeQLSimulation:
    """Test CodeQL simulation functionality."""

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.rglob")
    @patch("pathlib.Path.read_text")
    def test_simulate_codeql_checks_clean(
        self, mock_read_text: Mock, mock_rglob: Mock, mock_exists: Mock
    ) -> None:
        """Test CodeQL simulation with clean code."""
        mock_exists.return_value = True
        mock_rglob.return_value = [Mock(spec=["read_text"])]
        mock_read_text.return_value = "import os\nprint('Hello world')\n"

        result = simulate_codeql_checks()
        assert result is True

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.rglob")
    def test_simulate_codeql_checks_with_issues(self, mock_rglob: Mock, mock_exists: Mock) -> None:
        """Test CodeQL simulation with security issues."""
        mock_exists.return_value = True
        mock_file = Mock()
        mock_file.read_text.return_value = "import os\neval(user_input)\nprint('Hello world')\n"
        mock_rglob.return_value = [mock_file]

        result = simulate_codeql_checks()
        assert result is False

    @patch("pathlib.Path.exists")
    def test_simulate_codeql_checks_no_src(self, mock_exists: Mock) -> None:
        """Test CodeQL simulation when src directory doesn't exist."""
        mock_exists.return_value = False

        result = simulate_codeql_checks()
        assert result is True

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.rglob")
    def test_simulate_codeql_checks_exception(self, mock_rglob: Mock, mock_exists: Mock) -> None:
        """Test CodeQL simulation exception handling."""
        mock_exists.return_value = True
        mock_rglob.side_effect = Exception("File system error")

        result = simulate_codeql_checks()
        assert result is True  # Should not fail build for simulation issues


class TestSecurityIntegration:
    """Test security integration functions."""

    @patch("badges.security.run_bandit_scan")
    @patch("badges.security.run_safety_check")
    @patch("badges.security.run_semgrep_analysis")
    @patch("badges.security.simulate_codeql_checks")
    def test_run_all_security_checks(
        self, mock_codeql: Mock, mock_semgrep: Mock, mock_safety: Mock, mock_bandit: Mock
    ) -> None:
        """Test running all security checks."""
        mock_bandit.return_value = True
        mock_safety.return_value = True
        mock_semgrep.return_value = True
        mock_codeql.return_value = True

        results = run_all_security_checks()

        assert results == {
            "bandit": True,
            "safety": True,
            "semgrep": True,
            "codeql_simulation": True,
        }

        mock_bandit.assert_called_once()
        mock_safety.assert_called_once()
        mock_semgrep.assert_called_once()
        mock_codeql.assert_called_once()

    @patch("badges.security.run_all_security_checks")
    def test_security_checks_passed_all_pass(self, mock_run_all: Mock) -> None:
        """Test security_checks_passed when all checks pass."""
        mock_run_all.return_value = {
            "bandit": True,
            "safety": True,
            "semgrep": True,
            "codeql_simulation": True,
        }

        result = security_checks_passed()
        assert result is True

    @patch("badges.security.run_all_security_checks")
    def test_security_checks_passed_some_fail(self, mock_run_all: Mock) -> None:
        """Test security_checks_passed when some checks fail."""
        mock_run_all.return_value = {
            "bandit": True,
            "safety": False,
            "semgrep": True,
            "codeql_simulation": True,
        }

        result = security_checks_passed()
        assert result is False

    @patch("badges.security.run_all_security_checks")
    def test_security_checks_passed_all_fail(self, mock_run_all: Mock) -> None:
        """Test security_checks_passed when all checks fail."""
        mock_run_all.return_value = {
            "bandit": False,
            "safety": False,
            "semgrep": False,
            "codeql_simulation": False,
        }

        result = security_checks_passed()
        assert result is False


class TestAdditionalCoverage:
    """Additional tests to improve coverage."""

    @patch("subprocess.run")
    def test_bandit_scan_execution_error(self, mock_run: Mock) -> None:
        """Test bandit scan with execution error."""
        # Mock bandit version check success but scan execution error
        mock_run.side_effect = [
            Mock(returncode=0, stdout="bandit 1.7.5", stderr=""),  # version check
            Mock(returncode=2, stdout="", stderr="execution error"),  # execution error
        ]

        result = run_bandit_scan()
        assert result is False

    @patch("subprocess.run")
    def test_bandit_scan_invalid_json(self, mock_run: Mock) -> None:
        """Test bandit scan with invalid JSON output."""
        # Mock bandit version check and scan with invalid JSON
        mock_run.side_effect = [
            Mock(returncode=0, stdout="bandit 1.7.5", stderr=""),  # version check
            Mock(returncode=1, stdout="invalid json", stderr=""),  # invalid JSON
        ]

        result = run_bandit_scan()
        assert result is False

    @patch("subprocess.run")
    def test_safety_check_execution_error(self, mock_run: Mock) -> None:
        """Test safety check with execution error."""
        # Mock safety version check success but check execution error
        mock_run.side_effect = [
            Mock(returncode=0, stdout="safety 2.3.1", stderr=""),  # version check
            Mock(returncode=1, stdout="", stderr="execution error"),  # execution error
        ]

        result = run_safety_check()
        assert result is True  # MVP tolerant of execution errors

    @patch("subprocess.run")
    def test_safety_check_empty_output(self, mock_run: Mock) -> None:
        """Test safety check with empty output."""
        # Mock safety version check and check with empty output
        mock_run.side_effect = [
            Mock(returncode=0, stdout="safety 2.3.1", stderr=""),  # version check
            Mock(returncode=1, stdout="", stderr=""),  # empty output
        ]

        result = run_safety_check()
        assert result is True  # MVP tolerant of empty output

    @patch("subprocess.run")
    def test_semgrep_analysis_execution_error(self, mock_run: Mock) -> None:
        """Test semgrep analysis with execution error."""
        # Mock semgrep version check success but analysis execution error
        mock_run.side_effect = [
            Mock(returncode=0, stdout="semgrep 1.45.0", stderr=""),  # version check
            Mock(returncode=1, stdout="", stderr="execution error"),  # execution error
        ]

        result = run_semgrep_analysis()
        assert result is False

    @patch("subprocess.run")
    def test_semgrep_analysis_invalid_json(self, mock_run: Mock) -> None:
        """Test semgrep analysis with invalid JSON output."""
        # Mock semgrep version check and analysis with invalid JSON
        mock_run.side_effect = [
            Mock(returncode=0, stdout="semgrep 1.45.0", stderr=""),  # version check
            Mock(returncode=0, stdout="invalid json", stderr=""),  # invalid JSON
        ]

        result = run_semgrep_analysis()
        assert result is True  # Should return True for invalid JSON

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.rglob")
    def test_codeql_simulation_file_read_error(self, mock_rglob: Mock, mock_exists: Mock) -> None:
        """Test CodeQL simulation with file read error."""
        mock_exists.return_value = True
        mock_file = Mock()
        mock_file.read_text.side_effect = Exception("Permission denied")
        mock_rglob.return_value = [mock_file]

        result = simulate_codeql_checks()
        assert result is True  # Should continue despite file read errors

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.rglob")
    def test_codeql_simulation_multiple_patterns(self, mock_rglob: Mock, mock_exists: Mock) -> None:
        """Test CodeQL simulation with multiple dangerous patterns."""
        mock_exists.return_value = True
        mock_file = Mock()
        mock_file.__str__ = Mock(return_value="test_file.py")
        mock_file.read_text.return_value = """
import os
import subprocess
# This is a comment with eval() - should be ignored
eval(user_input)  # This should be detected
exec(malicious_code)  # This should be detected
os.system('rm -rf /')  # This should be detected
"""
        mock_rglob.return_value = [mock_file]

        result = simulate_codeql_checks()
        assert result is False

    @patch("subprocess.run")
    def test_bandit_scan_no_results_key(self, mock_run: Mock) -> None:
        """Test bandit scan with JSON missing results key."""
        # Mock bandit version check and scan with JSON missing results
        mock_run.side_effect = [
            Mock(returncode=0, stdout="bandit 1.7.5", stderr=""),  # version check
            Mock(returncode=1, stdout='{"errors": []}', stderr=""),  # JSON without results key
        ]

        result = run_bandit_scan()
        assert result is False

    @patch("subprocess.run")
    def test_safety_check_install_failure(self, mock_run: Mock) -> None:
        """Test safety check when installation fails."""
        # Mock safety not available and install fails
        mock_run.side_effect = [
            Mock(returncode=1, stdout="", stderr="command not found"),  # version check fails
            Mock(returncode=1, stdout="", stderr="install failed"),  # install fails
        ]

        result = run_safety_check()
        assert result is False

    @patch("subprocess.run")
    def test_safety_check_invalid_json(self, mock_run: Mock) -> None:
        """Test safety check with invalid JSON output."""
        # Mock safety version check and check with invalid JSON
        mock_run.side_effect = [
            Mock(returncode=0, stdout="safety 2.3.1", stderr=""),  # version check
            Mock(returncode=1, stdout="invalid json", stderr=""),  # invalid JSON
        ]

        result = run_safety_check()
        assert result is True  # MVP tolerant of invalid JSON

    @patch("subprocess.run")
    def test_safety_check_with_new_json_format(self, mock_run: Mock) -> None:
        """Test safety check with new JSON format containing vulnerabilities dict."""
        # Mock safety version check and scan with new JSON format
        mock_run.side_effect = [
            Mock(returncode=0, stdout="safety 2.3.1", stderr=""),  # version check
            Mock(
                returncode=1,
                stdout='{"vulnerabilities": [{"is_transitive": false, "severity": "HIGH"}]}',
                stderr="",
            ),  # new format with high severity direct dependency
        ]

        result = run_safety_check()
        assert result is False  # Should fail for high severity direct dependencies

    @patch("subprocess.run")
    def test_safety_check_with_transitive_vulnerabilities(self, mock_run: Mock) -> None:
        """Test safety check with transitive vulnerabilities (should pass for MVP)."""
        # Mock safety version check and scan with transitive vulnerabilities
        mock_run.side_effect = [
            Mock(returncode=0, stdout="safety 2.3.1", stderr=""),  # version check
            Mock(
                returncode=1,
                stdout='{"vulnerabilities": [{"is_transitive": true, "severity": "HIGH"}]}',
                stderr="",
            ),  # transitive vulnerability
        ]

        result = run_safety_check()
        assert result is True  # Should pass for transitive vulnerabilities


class TestGitHubCodeQLIntegration:
    """Test GitHub CodeQL API integration functionality."""

    @patch("urllib.request.urlopen")
    def test_get_github_codeql_status_success_no_alerts(self, mock_urlopen: Mock) -> None:
        """Test GitHub CodeQL status with no open alerts."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b"[]"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = get_github_codeql_status()
        assert result == "success"

    @patch("urllib.request.urlopen")
    def test_get_github_codeql_status_success_with_low_severity(self, mock_urlopen: Mock) -> None:
        """Test GitHub CodeQL status with only low severity alerts."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b'[{"state": "open", "rule": {"severity": "note"}}]'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = get_github_codeql_status()
        assert result == "success"

    @patch("urllib.request.urlopen")
    def test_get_github_codeql_status_failure_with_high_severity(self, mock_urlopen: Mock) -> None:
        """Test GitHub CodeQL status with high severity alerts."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b'[{"state": "open", "rule": {"severity": "error"}}]'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = get_github_codeql_status()
        assert result == "failure"

    @patch("urllib.request.urlopen")
    def test_get_github_codeql_status_404_not_found(self, mock_urlopen: Mock) -> None:
        """Test GitHub CodeQL status when repository not found."""
        mock_response = Mock()
        mock_response.status = 404
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = get_github_codeql_status()
        assert result == "unknown"

    @patch("urllib.request.urlopen")
    def test_get_github_codeql_status_http_error_404(self, mock_urlopen: Mock) -> None:
        """Test GitHub CodeQL status with HTTP 404 error."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=404, msg="Not Found", hdrs=None, fp=None
        )

        result = get_github_codeql_status()
        assert result == "unknown"

    @patch("urllib.request.urlopen")
    def test_get_github_codeql_status_http_error_403(self, mock_urlopen: Mock) -> None:
        """Test GitHub CodeQL status with HTTP 403 error (rate limited)."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=403, msg="Forbidden", hdrs=None, fp=None
        )

        result = get_github_codeql_status()
        assert result == "unknown"

    @patch("urllib.request.urlopen")
    def test_get_github_codeql_status_http_error_other(self, mock_urlopen: Mock) -> None:
        """Test GitHub CodeQL status with other HTTP error."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=500, msg="Internal Server Error", hdrs=None, fp=None
        )

        result = get_github_codeql_status()
        assert result == "unknown"

    @patch("urllib.request.urlopen")
    def test_get_github_codeql_status_timeout(self, mock_urlopen: Mock) -> None:
        """Test GitHub CodeQL status with timeout."""
        mock_urlopen.side_effect = Exception("Timeout")

        result = get_github_codeql_status()
        assert result == "unknown"

    @patch("urllib.request.urlopen")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"})
    def test_get_github_codeql_status_with_auth_token(self, mock_urlopen: Mock) -> None:
        """Test GitHub CodeQL status with authentication token."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b"[]"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = get_github_codeql_status()
        assert result == "success"

        # Verify that authorization header was added
        call_args = mock_urlopen.call_args[0][0]
        assert "Authorization" in call_args.headers
        assert call_args.headers["Authorization"] == "token test_token"

    @patch("urllib.request.urlopen")
    @patch.dict(os.environ, {"GITHUB_REPOSITORY": "testuser/testrepo"})
    def test_get_github_codeql_status_custom_repo(self, mock_urlopen: Mock) -> None:
        """Test GitHub CodeQL status with custom repository."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b"[]"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = get_github_codeql_status()
        assert result == "success"

        # Verify correct API URL was called
        call_args = mock_urlopen.call_args[0][0]
        assert "testuser/testrepo" in call_args.full_url

    @patch("urllib.request.urlopen")
    def test_get_github_codeql_status_invalid_json(self, mock_urlopen: Mock) -> None:
        """Test GitHub CodeQL status with invalid JSON response."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b"invalid json"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = get_github_codeql_status()
        assert result == "unknown"


class TestComprehensiveSecurityStatus:
    """Test comprehensive security status functionality."""

    @patch("badges.status.get_status_cache")
    @patch("badges.security.run_all_security_checks")
    @patch("badges.security.get_github_codeql_status")
    def test_get_comprehensive_security_status_verified(
        self, mock_codeql: Mock, mock_local: Mock, mock_cache: Mock
    ) -> None:
        """Test comprehensive security status when all checks pass."""
        # Mock cache to return None (no cached results)
        mock_cache_instance = Mock()
        mock_cache_instance.get.return_value = None
        mock_cache_instance.is_expired.return_value = True
        mock_cache.return_value = mock_cache_instance

        mock_local.return_value = {
            "bandit": True,
            "safety": True,
            "semgrep": True,
            "codeql_simulation": True,
        }
        mock_codeql.return_value = "success"

        result = get_comprehensive_security_status()

        assert result["status"] == "Verified"
        assert result["local_passed"] is True
        assert result["codeql_passed"] is True
        assert "code-scanning" in result["link_url"]

    @patch("badges.status.get_status_cache")
    @patch("badges.security.run_all_security_checks")
    @patch("badges.security.get_github_codeql_status")
    def test_get_comprehensive_security_status_issues_found_local(
        self, mock_codeql: Mock, mock_local: Mock, mock_cache: Mock
    ) -> None:
        """Test comprehensive security status when local checks fail."""
        # Mock cache to return None (no cached results)
        mock_cache_instance = Mock()
        mock_cache_instance.get.return_value = None
        mock_cache_instance.is_expired.return_value = True
        mock_cache.return_value = mock_cache_instance

        mock_local.return_value = {
            "bandit": False,
            "safety": True,
            "semgrep": True,
            "codeql_simulation": True,
        }
        mock_codeql.return_value = "success"

        result = get_comprehensive_security_status()

        assert result["status"] == "Issues Found"
        assert result["local_passed"] is False
        assert result["codeql_passed"] is True

    @patch("badges.status.get_status_cache")
    @patch("badges.security.run_all_security_checks")
    @patch("badges.security.get_github_codeql_status")
    def test_get_comprehensive_security_status_issues_found_codeql(
        self, mock_codeql: Mock, mock_local: Mock, mock_cache: Mock
    ) -> None:
        """Test comprehensive security status when CodeQL fails."""
        # Mock cache to return None (no cached results)
        mock_cache_instance = Mock()
        mock_cache_instance.get.return_value = None
        mock_cache_instance.is_expired.return_value = True
        mock_cache.return_value = mock_cache_instance

        mock_local.return_value = {
            "bandit": True,
            "safety": True,
            "semgrep": True,
            "codeql_simulation": True,
        }
        mock_codeql.return_value = "failure"

        result = get_comprehensive_security_status()

        assert result["status"] == "Issues Found"
        assert result["local_passed"] is True
        assert result["codeql_passed"] is False
        assert "code-scanning" in result["link_url"]

    @patch("badges.status.get_status_cache")
    @patch("badges.security.run_all_security_checks")
    @patch("badges.security.get_github_codeql_status")
    def test_get_comprehensive_security_status_scanning(
        self, mock_codeql: Mock, mock_local: Mock, mock_cache: Mock
    ) -> None:
        """Test comprehensive security status when CodeQL is pending."""
        # Mock cache to return None (no cached results)
        mock_cache_instance = Mock()
        mock_cache_instance.get.return_value = None
        mock_cache_instance.is_expired.return_value = True
        mock_cache.return_value = mock_cache_instance

        mock_local.return_value = {
            "bandit": True,
            "safety": True,
            "semgrep": True,
            "codeql_simulation": True,
        }
        mock_codeql.return_value = "pending"

        result = get_comprehensive_security_status()

        assert result["status"] == "Scanning"
        assert result["local_passed"] is True
        assert result["codeql_passed"] is False

    @patch("badges.status.get_status_cache")
    @patch("badges.security.run_all_security_checks")
    @patch("badges.security.get_github_codeql_status")
    def test_get_comprehensive_security_status_unknown(
        self, mock_codeql: Mock, mock_local: Mock, mock_cache: Mock
    ) -> None:
        """Test comprehensive security status when CodeQL status is unknown."""
        # Mock cache to return None (no cached results)
        mock_cache_instance = Mock()
        mock_cache_instance.get.return_value = None
        mock_cache_instance.is_expired.return_value = True
        mock_cache.return_value = mock_cache_instance

        mock_local.return_value = {
            "bandit": True,
            "safety": True,
            "semgrep": True,
            "codeql_simulation": True,
        }
        mock_codeql.return_value = "unknown"

        result = get_comprehensive_security_status()

        assert result["status"] == "Unknown"
        assert result["local_passed"] is True
        assert result["codeql_passed"] is False
        assert "/security" in result["link_url"]
        assert "code-scanning" not in result["link_url"]

    @patch("badges.security.run_all_security_checks")
    @patch("badges.security.get_github_codeql_status")
    @patch.dict(os.environ, {"GITHUB_REPOSITORY": "testuser/testrepo"})
    def test_get_comprehensive_security_status_custom_repo(
        self, mock_codeql: Mock, mock_local: Mock
    ) -> None:
        """Test comprehensive security status with custom repository."""
        mock_local.return_value = {
            "bandit": True,
            "safety": True,
            "semgrep": True,
            "codeql_simulation": True,
        }
        mock_codeql.return_value = "success"

        result = get_comprehensive_security_status()

        assert result["github_repo"] == "testuser/testrepo"
        assert "testuser/testrepo" in result["link_url"]

    @patch("badges.status.get_status_cache")
    @patch("badges.security.run_all_security_checks")
    @patch("badges.security.get_github_codeql_status")
    def test_get_comprehensive_security_status_exception(
        self, mock_codeql: Mock, mock_local: Mock, mock_cache: Mock
    ) -> None:
        """Test comprehensive security status with exception."""
        # Mock cache to return None (no cached results)
        mock_cache_instance = Mock()
        mock_cache_instance.get.return_value = None
        mock_cache_instance.is_expired.return_value = True
        mock_cache.return_value = mock_cache_instance

        mock_local.side_effect = Exception("Test error")
        mock_codeql.return_value = "success"

        result = get_comprehensive_security_status()

        assert result["status"] == "Unknown"
        assert result["local_passed"] is False
        assert result["codeql_passed"] is False
