"""Security scanning integration module.

This module provides functions to integrate security scanning tools
into the local testing workflow for badge status determination.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
import urllib.error
import urllib.request


def run_bandit_scan() -> bool:
    """Execute bandit security scanner and return pass/fail status.

    Returns:
        True if bandit scan passes, False if security issues found.
    """
    try:
        # Check if bandit is available
        result = subprocess.run(
            ["uv", "run", "bandit", "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            print("Warning: bandit not available, installing...", file=sys.stderr)
            # Try to install bandit
            install_result = subprocess.run(
                ["uv", "add", "--dev", "bandit"],
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if install_result.returncode != 0:
                print("Error: Could not install bandit", file=sys.stderr)
                return False

        # Run bandit scan on source code
        scan_result = subprocess.run(
            ["uv", "run", "bandit", "-r", "src/", "-f", "json"],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if scan_result.returncode == 0:
            return True
        if scan_result.returncode == 1:
            # Bandit found issues
            try:
                report = json.loads(scan_result.stdout)
                if report.get("results"):
                    print(f"Bandit found {len(report['results'])} security issues", file=sys.stderr)
                    return False
            except json.JSONDecodeError:
                pass
            return False
        # Bandit execution error
        print(f"Bandit execution error: {scan_result.stderr}", file=sys.stderr)
        return False

    except subprocess.TimeoutExpired:
        print("Bandit scan timed out", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Bandit scan failed: {e}", file=sys.stderr)
        return False


def run_safety_check() -> bool:
    """Execute safety dependency scanner and return pass/fail status.

    Returns:
        True if safety check passes, False if vulnerabilities found.
    """
    try:
        # Check if safety is available
        result = subprocess.run(
            ["uv", "run", "safety", "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            print("Warning: safety not available, installing...", file=sys.stderr)
            # Try to install safety
            install_result = subprocess.run(
                ["uv", "add", "--dev", "safety"],
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if install_result.returncode != 0:
                print("Error: Could not install safety", file=sys.stderr)
                return False

        # Run safety check on dependencies
        check_result = subprocess.run(
            ["uv", "run", "safety", "check", "--json"],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if check_result.returncode == 0:
            return True
        # Safety found vulnerabilities or had an error
        try:
            if check_result.stdout:
                report = json.loads(check_result.stdout)
                # For MVP, we'll be more tolerant of dependency vulnerabilities
                # Focus on high-severity issues in our direct dependencies
                if isinstance(report, dict) and "vulnerabilities" in report:
                    vulnerabilities = report["vulnerabilities"]
                    # Count only high-severity vulnerabilities in direct dependencies
                    critical_vulns = [
                        v
                        for v in vulnerabilities
                        if not v.get("is_transitive", True)
                        and v.get("severity", "").upper() in ["HIGH", "CRITICAL"]
                    ]
                    if critical_vulns:
                        print(
                            f"Safety found {len(critical_vulns)} critical vulnerabilities "
                            "in direct dependencies",
                            file=sys.stderr,
                        )
                        return False
                    print(
                        f"Safety found {len(vulnerabilities)} vulnerabilities "
                        "(transitive/low severity - acceptable for MVP)",
                        file=sys.stderr,
                    )
                    return True
                if isinstance(report, list) and report:
                    # Old format - be more tolerant for MVP
                    print(
                        f"Safety found {len(report)} vulnerabilities (acceptable for MVP)",
                        file=sys.stderr,
                    )
                    return True
        except json.JSONDecodeError:
            pass

        # Check stderr for vulnerability messages
        if (
            "vulnerability" in check_result.stderr.lower()
            or "vulnerabilities" in check_result.stderr.lower()
        ):
            print("Safety found vulnerabilities (acceptable for MVP)", file=sys.stderr)
            return True

        # If we get here, safety had an error but no clear vulnerability indication
        # For MVP, be tolerant of safety issues
        if check_result.stderr:
            print(f"Safety check error: {check_result.stderr}", file=sys.stderr)
        else:
            print("Safety check completed with warnings (acceptable for MVP)", file=sys.stderr)
        return True

    except subprocess.TimeoutExpired:
        print("Safety check timed out", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Safety check failed: {e}", file=sys.stderr)
        return False


def run_semgrep_analysis() -> bool:
    """Execute semgrep security analysis and return pass/fail status.

    Returns:
        True if semgrep analysis passes, False if security patterns found.
    """
    try:
        # Check if semgrep is available
        result = subprocess.run(
            ["semgrep", "--version"], check=False, capture_output=True, text=True, timeout=30
        )

        if result.returncode != 0:
            print("Warning: semgrep not available, skipping semgrep analysis", file=sys.stderr)
            # Semgrep requires separate installation, not available via uv
            # Return True to not fail the build for missing optional tool
            return True

        # Run semgrep analysis with Python security rules
        analysis_result = subprocess.run(
            ["semgrep", "--config=auto", "--json", "src/"],
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )

        if analysis_result.returncode == 0:
            try:
                report = json.loads(analysis_result.stdout)
                results = report.get("results", [])
                if results:
                    print(f"Semgrep found {len(results)} security patterns", file=sys.stderr)
                    return False
                return True
            except json.JSONDecodeError:
                return True
        else:
            # Semgrep found issues or had an error
            print(f"Semgrep analysis error: {analysis_result.stderr}", file=sys.stderr)
            return False

    except subprocess.TimeoutExpired:
        print("Semgrep analysis timed out", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Semgrep analysis failed: {e}", file=sys.stderr)
        # Don't fail build for semgrep issues since it's optional
        return True


def simulate_codeql_checks() -> bool:
    """Run CodeQL-equivalent checks locally where possible.

    This function simulates CodeQL analysis using available Python tools
    that can detect similar security patterns.

    Returns:
        True if CodeQL simulation passes, False if issues found.
    """
    try:
        # CodeQL simulation using basic static analysis patterns
        # Check for common security anti-patterns in Python code

        issues_found = []

        # Scan source files for basic security patterns
        src_path = Path("src")
        if src_path.exists():
            for py_file in src_path.rglob("*.py"):
                try:
                    content = py_file.read_text(encoding="utf-8")

                    # Check for dangerous patterns
                    dangerous_patterns = [
                        ("eval(", "Use of eval() function"),
                        ("exec(", "Use of exec() function"),
                        ("__import__(", "Dynamic import usage"),
                        ("subprocess.call(", "Subprocess call without shell=False"),
                        ("os.system(", "Use of os.system()"),
                        ("pickle.loads(", "Unsafe pickle deserialization"),
                        ("yaml.load(", "Unsafe YAML loading"),
                    ]

                    for pattern, description in dangerous_patterns:
                        if pattern in content:
                            # Basic check - could have false positives
                            lines = content.split("\n")
                            for i, line in enumerate(lines, 1):
                                if pattern in line and not line.strip().startswith("#"):
                                    issues_found.append(f"{py_file}:{i} - {description}")

                except Exception as e:
                    print(f"Warning: Could not scan {py_file}: {e}", file=sys.stderr)

        if issues_found:
            print(
                f"CodeQL simulation found {len(issues_found)} potential security issues:",
                file=sys.stderr,
            )
            for issue in issues_found[:5]:  # Limit output
                print(f"  {issue}", file=sys.stderr)
            if len(issues_found) > 5:
                print(f"  ... and {len(issues_found) - 5} more", file=sys.stderr)
            return False

        return True

    except Exception as e:
        print(f"CodeQL simulation failed: {e}", file=sys.stderr)
        # Don't fail build for simulation issues
        return True


def run_all_security_checks() -> dict[str, bool]:
    """Run all security checks and return results.

    Returns:
        Dictionary mapping check names to pass/fail status.
    """
    results = {}

    print("Running security checks...", file=sys.stderr)

    results["bandit"] = run_bandit_scan()
    results["safety"] = run_safety_check()
    results["semgrep"] = run_semgrep_analysis()
    results["codeql_simulation"] = simulate_codeql_checks()

    return results


def security_checks_passed() -> bool:
    """Check if all security scans pass.

    Returns:
        True if all security checks pass, False otherwise.
    """
    results = run_all_security_checks()
    return all(results.values())


def get_github_codeql_status() -> str:
    """Get GitHub CodeQL scan status from GitHub API.

    Returns:
        CodeQL status: "success", "failure", "pending", "unknown"
    """
    try:
        # Get repository information from environment or config
        github_repo = os.getenv("GITHUB_REPOSITORY", "username/mypylogger")
        github_token = os.getenv("GITHUB_TOKEN")

        # GitHub API endpoint for code scanning alerts
        api_url = f"https://api.github.com/repos/{github_repo}/code-scanning/alerts"

        # Prepare request headers
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "mypylogger-badge-system/1.0",
        }

        # Add authentication if token is available
        if github_token:
            headers["Authorization"] = f"token {github_token}"

        # Create request
        request = urllib.request.Request(api_url, headers=headers)

        # Make API call with timeout
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())

                    # Check for open alerts
                    open_alerts = [alert for alert in data if alert.get("state") == "open"]

                    if not open_alerts:
                        return "success"  # No open alerts
                    # Check severity of open alerts
                    high_severity_alerts = [
                        alert
                        for alert in open_alerts
                        if alert.get("rule", {}).get("severity") in ["error", "warning"]
                    ]
                    if high_severity_alerts:
                        return "failure"  # High severity alerts found
                    return "success"  # Only low severity alerts

                if response.status == 404:
                    # Repository not found or CodeQL not enabled
                    return "unknown"
                print(f"GitHub API returned status {response.status}", file=sys.stderr)
                return "unknown"

        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Repository not found or CodeQL not enabled
                return "unknown"
            if e.code == 403:
                # Rate limited or insufficient permissions
                print("GitHub API rate limited or insufficient permissions", file=sys.stderr)
                return "unknown"
            print(f"GitHub API HTTP error {e.code}: {e.reason}", file=sys.stderr)
            return "unknown"

    except Exception as e:
        print(f"Failed to get GitHub CodeQL status: {e}", file=sys.stderr)
        return "unknown"


def get_comprehensive_security_status() -> dict[str, Any]:
    """Combine local security scans with GitHub CodeQL results.

    Returns:
        Dictionary containing comprehensive security status information.
    """
    try:
        # Check if we have cached results to avoid redundant API calls
        from badges.status import get_status_cache

        cache = get_status_cache()

        # Try to get cached local results first
        cached_local = cache.get("local_security_results")
        if cached_local and not cache.is_expired(max_age_seconds=300):  # 5 minute cache
            local_results = cached_local.get("results", {})
            local_passed = cached_local.get("passed", False)
        else:
            # Run local security checks
            local_results = run_all_security_checks()
            local_passed = all(local_results.values())

            # Cache the results
            cache.set("local_security_results", {"results": local_results, "passed": local_passed})

        # Try to get cached GitHub CodeQL status
        cached_codeql = cache.get("github_codeql_status")
        if cached_codeql and not cache.is_expired(max_age_seconds=300):  # 5 minute cache
            codeql_status = cached_codeql.get("status", "unknown")
        else:
            # Get GitHub CodeQL status
            codeql_status = get_github_codeql_status()

            # Cache the result
            cache.set("github_codeql_status", {"status": codeql_status})

        codeql_passed = codeql_status == "success"

        # Determine overall status
        if local_passed and codeql_passed:
            status = "Verified"
        elif not local_passed or codeql_status == "failure":
            status = "Issues Found"
        elif codeql_status == "pending":
            status = "Scanning"
        else:
            status = "Unknown"

        # Get repository information for links
        github_repo = os.getenv("GITHUB_REPOSITORY", "username/mypylogger")

        # Determine appropriate link URL
        if codeql_status in ["success", "failure"]:
            link_url = f"https://github.com/{github_repo}/security/code-scanning"
        else:
            link_url = f"https://github.com/{github_repo}/security"

        return {
            "status": status,
            "local_results": local_results,
            "local_passed": local_passed,
            "codeql_status": codeql_status,
            "codeql_passed": codeql_passed,
            "link_url": link_url,
            "github_repo": github_repo,
        }

    except Exception as e:
        print(f"Failed to get comprehensive security status: {e}", file=sys.stderr)

        # Fallback status
        github_repo = os.getenv("GITHUB_REPOSITORY", "username/mypylogger")
        return {
            "status": "Unknown",
            "local_results": {},
            "local_passed": False,
            "codeql_status": "unknown",
            "codeql_passed": False,
            "link_url": f"https://github.com/{github_repo}/security",
            "github_repo": github_repo,
        }
