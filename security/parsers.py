"""Security scanner output parsers.

This module provides parsers for different security scanner outputs,
converting them into standardized SecurityFinding objects.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
from typing import Any

from security.models import SecurityFinding


class ScannerParseError(Exception):
    """Exception raised when scanner output cannot be parsed."""


def parse_pip_audit_json(
    json_data: dict[str, Any], discovered_date: date | None = None
) -> list[SecurityFinding]:
    """Parse pip-audit JSON output into SecurityFinding objects.

    Args:
        json_data: Parsed JSON data from pip-audit output
        discovered_date: Date when vulnerabilities were discovered (defaults to today)

    Returns:
        List of SecurityFinding objects extracted from the pip-audit report

    Raises:
        ScannerParseError: If the JSON structure is invalid or missing required fields
    """
    if discovered_date is None:
        discovered_date = datetime.now(timezone.utc).date()

    findings = []

    try:
        # pip-audit format: {"dependencies": [...], "fixes": [...]}
        dependencies = json_data.get("dependencies", [])

        for dependency in dependencies:
            if not isinstance(dependency, dict):
                continue

            package_name = dependency.get("name")
            package_version = dependency.get("version")
            vulnerabilities = dependency.get("vulns", [])

            # Skip dependencies without vulnerabilities
            if not vulnerabilities or not package_name or not package_version:
                continue

            for vuln in vulnerabilities:
                if not isinstance(vuln, dict):
                    continue

                # Extract vulnerability information
                vuln_id = vuln.get("id", "")
                description = vuln.get("description", "")
                aliases = vuln.get("aliases", [])
                fix_versions = vuln.get("fix_versions", [])

                # Determine if fix is available
                fix_available = bool(fix_versions)
                fix_version = fix_versions[0] if fix_versions else None

                # Create finding
                finding = SecurityFinding(
                    finding_id=vuln_id,
                    package=package_name,
                    version=package_version,
                    severity="medium",  # pip-audit doesn't provide severity, default to medium
                    source_scanner="pip-audit",
                    discovered_date=discovered_date,
                    description=description[:500] + "..."
                    if len(description) > 500
                    else description,
                    impact=f"Vulnerability in {package_name} package",
                    fix_available=fix_available,
                    fix_version=fix_version,
                    reference_url=_extract_reference_url(vuln_id, aliases),
                )

                findings.append(finding)

    except (KeyError, TypeError, AttributeError) as e:
        msg = f"Invalid pip-audit JSON structure: {e}"
        raise ScannerParseError(msg) from e

    return findings


def parse_bandit_json(
    json_data: dict[str, Any], discovered_date: date | None = None
) -> list[SecurityFinding]:
    """Parse bandit JSON output into SecurityFinding objects.

    Args:
        json_data: Parsed JSON data from bandit output
        discovered_date: Date when vulnerabilities were discovered (defaults to today)

    Returns:
        List of SecurityFinding objects extracted from the bandit report

    Raises:
        ScannerParseError: If the JSON structure is invalid or missing required fields
    """
    if discovered_date is None:
        discovered_date = datetime.now(timezone.utc).date()

    findings = []

    try:
        # bandit format: {"results": [...], "metrics": {...}}
        results = json_data.get("results", [])

        for result in results:
            if not isinstance(result, dict):
                continue

            # Extract bandit result information
            test_id = result.get("test_id", "")
            test_name = result.get("test_name", "")
            filename = result.get("filename", "")
            line_number = result.get("line_number", 0)
            issue_severity = result.get("issue_severity", "MEDIUM")
            result.get("issue_confidence", "MEDIUM")
            issue_text = result.get("issue_text", "")

            # Create a unique finding ID for bandit issues
            finding_id = f"BANDIT-{test_id}-{Path(filename).name}-{line_number}"

            # Map bandit severity to our severity levels
            severity_mapping = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}
            severity = severity_mapping.get(issue_severity.upper(), "medium")

            # Create finding
            finding = SecurityFinding(
                finding_id=finding_id,
                package=Path(filename).name,  # Use filename as package
                version="local",  # Local code doesn't have version
                severity=severity,
                source_scanner="bandit",
                discovered_date=discovered_date,
                description=f"{test_name}: {issue_text}",
                impact=f"Code security issue in {filename} at line {line_number}",
                fix_available=False,  # Bandit issues require manual fixes
                reference_url=f"https://bandit.readthedocs.io/en/latest/plugins/{test_id.lower()}.html",
            )

            findings.append(finding)

    except (KeyError, TypeError, AttributeError) as e:
        msg = f"Invalid bandit JSON structure: {e}"
        raise ScannerParseError(msg) from e

    return findings


def parse_secrets_json(
    json_data: dict[str, Any], discovered_date: date | None = None
) -> list[SecurityFinding]:
    """Parse secrets scanning JSON output into SecurityFinding objects.

    Args:
        json_data: Parsed JSON data from secrets scanner output
        discovered_date: Date when secrets were discovered (defaults to today)

    Returns:
        List of SecurityFinding objects extracted from the secrets report

    Raises:
        ScannerParseError: If the JSON structure is invalid or missing required fields
    """
    if discovered_date is None:
        discovered_date = datetime.now(timezone.utc).date()

    findings = []

    try:
        # Generic secrets scanner format (adaptable to different tools)
        # Expected format: {"secrets": [...]} or direct array
        secrets_data = (
            json_data.get("secrets", json_data) if isinstance(json_data, dict) else json_data
        )

        if not isinstance(secrets_data, list):
            secrets_data = [secrets_data] if secrets_data else []

        for secret in secrets_data:
            if not isinstance(secret, dict):
                continue

            # Extract secret information (flexible field names)
            secret_type = secret.get("type", secret.get("rule", "unknown"))
            filename = secret.get("filename", secret.get("file", "unknown"))
            line_number = secret.get("line", secret.get("line_number", 0))
            description = secret.get("description", secret.get("message", ""))

            # Create a unique finding ID for secrets
            finding_id = f"SECRET-{secret_type}-{Path(filename).name}-{line_number}"

            # Create finding
            finding = SecurityFinding(
                finding_id=finding_id,
                package=Path(filename).name,  # Use filename as package
                version="local",  # Local files don't have version
                severity="high",  # Secrets are generally high severity
                source_scanner="secrets",
                discovered_date=discovered_date,
                description=f"Potential {secret_type} secret detected: {description}",
                impact=f"Exposed secret in {filename} at line {line_number}",
                fix_available=False,  # Secrets require manual remediation
            )

            findings.append(finding)

    except (KeyError, TypeError, AttributeError) as e:
        msg = f"Invalid secrets JSON structure: {e}"
        raise ScannerParseError(msg) from e

    return findings


def parse_scanner_file(
    file_path: Path, scanner_type: str, discovered_date: date | None = None
) -> list[SecurityFinding]:
    """Parse a scanner output file into SecurityFinding objects.

    Args:
        file_path: Path to the scanner output file
        scanner_type: Type of scanner ("pip-audit", "bandit", "secrets")
        discovered_date: Date when vulnerabilities were discovered (defaults to today)

    Returns:
        List of SecurityFinding objects extracted from the file

    Raises:
        ScannerParseError: If the file cannot be read or parsed
        FileNotFoundError: If the file doesn't exist
    """
    if not file_path.exists():
        msg = f"Scanner output file not found: {file_path}"
        raise FileNotFoundError(msg)

    try:
        with file_path.open("r", encoding="utf-8") as f:
            json_data = json.load(f)
    except json.JSONDecodeError as e:
        msg = f"Invalid JSON in {file_path}: {e}"
        raise ScannerParseError(msg) from e
    except Exception as e:
        msg = f"Error reading {file_path}: {e}"
        raise ScannerParseError(msg) from e

    # Route to appropriate parser based on scanner type
    parser_map = {
        "pip-audit": parse_pip_audit_json,
        "bandit": parse_bandit_json,
        "secrets": parse_secrets_json,
    }

    parser = parser_map.get(scanner_type)
    if not parser:
        msg = f"Unsupported scanner type: {scanner_type}"
        raise ScannerParseError(msg)

    return parser(json_data, discovered_date)


def extract_all_findings(
    reports_dir: Path, discovered_date: date | None = None
) -> list[SecurityFinding]:
    """Extract findings from all scanner reports in a directory.

    Args:
        reports_dir: Directory containing scanner output files
        discovered_date: Date when vulnerabilities were discovered (defaults to today)

    Returns:
        List of all SecurityFinding objects from all scanners

    Raises:
        ScannerParseError: If any scanner output cannot be parsed
    """
    if discovered_date is None:
        discovered_date = datetime.now(timezone.utc).date()

    all_findings = []

    # Define expected scanner files and their types
    scanner_files = {
        "pip-audit.json": "pip-audit",
        "bandit.json": "bandit",
        "secrets-scan.json": "secrets",
    }

    for filename, scanner_type in scanner_files.items():
        file_path = reports_dir / filename

        if file_path.exists():
            try:
                findings = parse_scanner_file(file_path, scanner_type, discovered_date)
                all_findings.extend(findings)
            except Exception as e:
                # Log error but continue with other scanners
                print(f"Warning: Failed to parse {filename}: {e}")
                continue

    return all_findings


def _extract_reference_url(vuln_id: str, aliases: list[str] | None = None) -> str | None:
    """Extract reference URL for a vulnerability ID.

    Args:
        vuln_id: Vulnerability identifier (CVE, GHSA, etc.)
        aliases: List of alternative identifiers

    Returns:
        Reference URL if available, None otherwise
    """
    if not vuln_id:
        return None

    # Map vulnerability ID patterns to reference URLs
    if vuln_id.startswith("CVE-"):
        return f"https://nvd.nist.gov/vuln/detail/{vuln_id}"
    if vuln_id.startswith("GHSA-"):
        return f"https://github.com/advisories/{vuln_id}"
    if vuln_id.startswith("PYSEC-"):
        return f"https://osv.dev/vulnerability/{vuln_id}"

    # Check aliases for known patterns
    if aliases:
        for alias in aliases:
            if alias.startswith("CVE-"):
                return f"https://nvd.nist.gov/vuln/detail/{alias}"
            if alias.startswith("GHSA-"):
                return f"https://github.com/advisories/{alias}"

    return None
