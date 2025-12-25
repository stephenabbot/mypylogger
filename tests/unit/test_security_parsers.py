"""Unit tests for security scanner output parsers.

This module tests the parsing functionality for different security scanner outputs
to ensure proper extraction and conversion to SecurityFinding objects.
"""

from datetime import date
import json
from pathlib import Path
import tempfile
from tempfile import NamedTemporaryFile

import pytest

from security.parsers import (
    ScannerParseError,
    _extract_reference_url,
    extract_all_findings,
    parse_bandit_json,
    parse_pip_audit_json,
    parse_scanner_file,
    parse_secrets_json,
)


class TestPipAuditParser:
    """Test cases for pip-audit JSON parser."""

    def test_parse_pip_audit_with_vulnerabilities(self) -> None:
        """Test parsing pip-audit output with vulnerabilities."""
        json_data = {
            "dependencies": [
                {
                    "name": "pip",
                    "version": "25.2",
                    "vulns": [
                        {
                            "id": "GHSA-4xh5-x5gv-qwph",
                            "fix_versions": [],
                            "aliases": ["CVE-2025-8869"],
                            "description": "Arbitrary file overwrite vulnerability in pip",
                        }
                    ],
                },
                {
                    "name": "py",
                    "version": "1.11.0",
                    "vulns": [
                        {
                            "id": "PYSEC-2022-42969",
                            "fix_versions": ["1.12.0"],
                            "aliases": ["GHSA-w596-4wvx-j9j6", "CVE-2022-42969"],
                            "description": "ReDoS vulnerability in py library",
                        }
                    ],
                },
            ],
            "fixes": [],
        }

        test_date = date(2025, 1, 15)
        findings = parse_pip_audit_json(json_data, test_date)

        assert len(findings) == 2

        # Check first finding (pip)
        pip_finding = findings[0]
        assert pip_finding.finding_id == "GHSA-4xh5-x5gv-qwph"
        assert pip_finding.package == "pip"
        assert pip_finding.version == "25.2"
        assert pip_finding.severity == "medium"
        assert pip_finding.source_scanner == "pip-audit"
        assert pip_finding.discovered_date == test_date
        assert "Arbitrary file overwrite" in pip_finding.description
        assert pip_finding.fix_available is False
        assert pip_finding.fix_version is None
        assert pip_finding.reference_url == "https://github.com/advisories/GHSA-4xh5-x5gv-qwph"

        # Check second finding (py)
        py_finding = findings[1]
        assert py_finding.finding_id == "PYSEC-2022-42969"
        assert py_finding.package == "py"
        assert py_finding.version == "1.11.0"
        assert py_finding.fix_available is True
        assert py_finding.fix_version == "1.12.0"
        assert py_finding.reference_url == "https://osv.dev/vulnerability/PYSEC-2022-42969"

    def test_parse_pip_audit_no_vulnerabilities(self) -> None:
        """Test parsing pip-audit output with no vulnerabilities."""
        json_data = {
            "dependencies": [{"name": "requests", "version": "2.32.5", "vulns": []}],
            "fixes": [],
        }

        findings = parse_pip_audit_json(json_data)
        assert len(findings) == 0

    def test_parse_pip_audit_empty_dependencies(self) -> None:
        """Test parsing pip-audit output with empty dependencies."""
        json_data = {"dependencies": [], "fixes": []}

        findings = parse_pip_audit_json(json_data)
        assert len(findings) == 0

    def test_parse_pip_audit_invalid_structure(self) -> None:
        """Test parsing pip-audit output with invalid structure."""
        invalid_data = {"invalid": "structure"}

        # Should not raise error, just return empty list
        findings = parse_pip_audit_json(invalid_data)
        assert len(findings) == 0

    def test_parse_pip_audit_long_description(self) -> None:
        """Test parsing pip-audit output with very long description."""
        long_description = "A" * 600  # Longer than 500 chars
        json_data = {
            "dependencies": [
                {
                    "name": "test-package",
                    "version": "1.0.0",
                    "vulns": [
                        {
                            "id": "CVE-2025-1234",
                            "description": long_description,
                            "fix_versions": [],
                            "aliases": [],
                        }
                    ],
                }
            ]
        }

        findings = parse_pip_audit_json(json_data)
        assert len(findings) == 1
        assert len(findings[0].description) <= 503  # 500 + "..."
        assert findings[0].description.endswith("...")


class TestBanditParser:
    """Test cases for bandit JSON parser."""

    def test_parse_bandit_with_issues(self) -> None:
        """Test parsing bandit output with security issues."""
        json_data = {
            "results": [
                {
                    "filename": "src/example.py",
                    "test_id": "B101",
                    "test_name": "assert_used",
                    "issue_severity": "LOW",
                    "issue_confidence": "HIGH",
                    "issue_text": "Use of assert detected",
                    "line_number": 42,
                },
                {
                    "filename": "src/security.py",
                    "test_id": "B605",
                    "test_name": "start_process_with_a_shell",
                    "issue_severity": "HIGH",
                    "issue_confidence": "HIGH",
                    "issue_text": "Starting a process with a shell",
                    "line_number": 15,
                },
            ],
            "metrics": {},
        }

        test_date = date(2025, 1, 15)
        findings = parse_bandit_json(json_data, test_date)

        assert len(findings) == 2

        # Check first finding
        first_finding = findings[0]
        assert first_finding.finding_id == "BANDIT-B101-example.py-42"
        assert first_finding.package == "example.py"
        assert first_finding.version == "local"
        assert first_finding.severity == "low"
        assert first_finding.source_scanner == "bandit"
        assert first_finding.discovered_date == test_date
        assert "assert_used: Use of assert detected" in first_finding.description
        assert "src/example.py at line 42" in first_finding.impact
        assert first_finding.fix_available is False
        assert (
            first_finding.reference_url
            == "https://bandit.readthedocs.io/en/latest/plugins/b101.html"
        )

        # Check second finding
        second_finding = findings[1]
        assert second_finding.finding_id == "BANDIT-B605-security.py-15"
        assert second_finding.severity == "high"

    def test_parse_bandit_no_issues(self) -> None:
        """Test parsing bandit output with no security issues."""
        json_data = {
            "results": [],
            "metrics": {"_totals": {"SEVERITY.HIGH": 0, "SEVERITY.MEDIUM": 0, "SEVERITY.LOW": 0}},
        }

        findings = parse_bandit_json(json_data)
        assert len(findings) == 0

    def test_parse_bandit_severity_mapping(self) -> None:
        """Test bandit severity mapping to our severity levels."""
        json_data = {
            "results": [
                {
                    "filename": "test.py",
                    "test_id": "B101",
                    "test_name": "test",
                    "issue_severity": "HIGH",
                    "issue_confidence": "HIGH",
                    "issue_text": "High severity issue",
                    "line_number": 1,
                },
                {
                    "filename": "test.py",
                    "test_id": "B102",
                    "test_name": "test",
                    "issue_severity": "UNKNOWN",  # Should default to medium
                    "issue_confidence": "HIGH",
                    "issue_text": "Unknown severity issue",
                    "line_number": 2,
                },
            ]
        }

        findings = parse_bandit_json(json_data)
        assert len(findings) == 2
        assert findings[0].severity == "high"
        assert findings[1].severity == "medium"  # Default for unknown


class TestSecretsParser:
    """Test cases for secrets scanning JSON parser."""

    def test_parse_secrets_with_findings(self) -> None:
        """Test parsing secrets scanner output with findings."""
        json_data = {
            "secrets": [
                {
                    "type": "AWS Access Key",
                    "filename": "config.py",
                    "line": 25,
                    "description": "Potential AWS access key detected",
                },
                {
                    "type": "API Key",
                    "file": "settings.json",  # Alternative field name
                    "line_number": 10,  # Alternative field name
                    "message": "API key pattern found",  # Alternative field name
                },
            ]
        }

        test_date = date(2025, 1, 15)
        findings = parse_secrets_json(json_data, test_date)

        assert len(findings) == 2

        # Check first finding
        first_finding = findings[0]
        assert first_finding.finding_id == "SECRET-AWS Access Key-config.py-25"
        assert first_finding.package == "config.py"
        assert first_finding.version == "local"
        assert first_finding.severity == "high"
        assert first_finding.source_scanner == "secrets"
        assert first_finding.discovered_date == test_date
        assert "AWS Access Key" in first_finding.description
        assert "config.py at line 25" in first_finding.impact
        assert first_finding.fix_available is False

        # Check second finding with alternative field names
        second_finding = findings[1]
        assert second_finding.finding_id == "SECRET-API Key-settings.json-10"
        assert second_finding.package == "settings.json"

    def test_parse_secrets_direct_array(self) -> None:
        """Test parsing secrets scanner output as direct array."""
        json_data = [
            {
                "type": "Password",
                "filename": "test.py",
                "line": 5,
                "description": "Hardcoded password detected",
            }
        ]

        findings = parse_secrets_json(json_data)
        assert len(findings) == 1
        assert findings[0].finding_id == "SECRET-Password-test.py-5"

    def test_parse_secrets_no_findings(self) -> None:
        """Test parsing secrets scanner output with no findings."""
        json_data = {"secrets": []}

        findings = parse_secrets_json(json_data)
        assert len(findings) == 0


class TestScannerFileParser:
    """Test cases for scanner file parsing."""

    def test_parse_scanner_file_pip_audit(self) -> None:
        """Test parsing a pip-audit JSON file."""
        json_data = {
            "dependencies": [
                {
                    "name": "test-package",
                    "version": "1.0.0",
                    "vulns": [
                        {
                            "id": "CVE-2025-1234",
                            "description": "Test vulnerability",
                            "fix_versions": [],
                            "aliases": [],
                        }
                    ],
                }
            ]
        }

        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(json_data, f)
            temp_path = Path(f.name)

        try:
            findings = parse_scanner_file(temp_path, "pip-audit")
            assert len(findings) == 1
            assert findings[0].source_scanner == "pip-audit"
        finally:
            temp_path.unlink()

    def test_parse_scanner_file_not_found(self) -> None:
        """Test parsing a non-existent file."""
        non_existent_path = Path("non_existent_file.json")

        with pytest.raises(FileNotFoundError):
            parse_scanner_file(non_existent_path, "pip-audit")

    def test_parse_scanner_file_invalid_json(self) -> None:
        """Test parsing a file with invalid JSON."""
        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            temp_path = Path(f.name)

        try:
            with pytest.raises(ScannerParseError, match="Invalid JSON"):
                parse_scanner_file(temp_path, "pip-audit")
        finally:
            temp_path.unlink()

    def test_parse_scanner_file_unsupported_type(self) -> None:
        """Test parsing with unsupported scanner type."""
        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({}, f)
            temp_path = Path(f.name)

        try:
            with pytest.raises(ScannerParseError, match="Unsupported scanner type"):
                parse_scanner_file(temp_path, "unsupported-scanner")
        finally:
            temp_path.unlink()


class TestExtractAllFindings:
    """Test cases for extracting findings from multiple scanner reports."""

    def test_extract_all_findings_multiple_scanners(self) -> None:
        """Test extracting findings from multiple scanner reports."""
        # Create temporary directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            reports_dir = Path(temp_dir)

            # Create pip-audit report
            pip_audit_data = {
                "dependencies": [
                    {
                        "name": "vulnerable-package",
                        "version": "1.0.0",
                        "vulns": [
                            {
                                "id": "CVE-2025-1234",
                                "description": "Test vulnerability",
                                "fix_versions": [],
                                "aliases": [],
                            }
                        ],
                    }
                ]
            }

            with (reports_dir / "pip-audit.json").open("w") as f:
                json.dump(pip_audit_data, f)

            # Create bandit report
            bandit_data = {
                "results": [
                    {
                        "filename": "test.py",
                        "test_id": "B101",
                        "test_name": "assert_used",
                        "issue_severity": "LOW",
                        "issue_confidence": "HIGH",
                        "issue_text": "Use of assert detected",
                        "line_number": 1,
                    }
                ]
            }

            with (reports_dir / "bandit.json").open("w") as f:
                json.dump(bandit_data, f)

            # Extract all findings
            test_date = date(2025, 1, 15)
            findings = extract_all_findings(reports_dir, test_date)

            assert len(findings) == 2

            # Should have one from each scanner
            scanners = {f.source_scanner for f in findings}
            assert scanners == {"pip-audit", "bandit"}

    def test_extract_all_findings_missing_files(self) -> None:
        """Test extracting findings when some scanner files are missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            reports_dir = Path(temp_dir)

            # Only create pip-audit report (bandit and secrets missing)
            pip_audit_data = {
                "dependencies": [
                    {
                        "name": "test-package",
                        "version": "1.0.0",
                        "vulns": [
                            {
                                "id": "CVE-2025-5678",
                                "description": "Another test vulnerability",
                                "fix_versions": [],
                                "aliases": [],
                            }
                        ],
                    }
                ]
            }

            with (reports_dir / "pip-audit.json").open("w") as f:
                json.dump(pip_audit_data, f)

            # Should only extract from available files
            findings = extract_all_findings(reports_dir)
            assert len(findings) == 1
            assert findings[0].source_scanner == "pip-audit"

    def test_extract_all_findings_empty_directory(self) -> None:
        """Test extracting findings from empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            reports_dir = Path(temp_dir)

            findings = extract_all_findings(reports_dir)
            assert len(findings) == 0


class TestExtractReferenceUrl:
    """Test cases for reference URL extraction."""

    def test_extract_reference_url_cve(self) -> None:
        """Test extracting reference URL for CVE."""
        url = _extract_reference_url("CVE-2025-1234")
        assert url == "https://nvd.nist.gov/vuln/detail/CVE-2025-1234"

    def test_extract_reference_url_ghsa(self) -> None:
        """Test extracting reference URL for GHSA."""
        url = _extract_reference_url("GHSA-abcd-efgh-ijkl")
        assert url == "https://github.com/advisories/GHSA-abcd-efgh-ijkl"

    def test_extract_reference_url_pysec(self) -> None:
        """Test extracting reference URL for PYSEC."""
        url = _extract_reference_url("PYSEC-2025-123")
        assert url == "https://osv.dev/vulnerability/PYSEC-2025-123"

    def test_extract_reference_url_with_aliases(self) -> None:
        """Test extracting reference URL using aliases."""
        url = _extract_reference_url("UNKNOWN-ID", ["CVE-2025-5678", "OTHER-ID"])
        assert url == "https://nvd.nist.gov/vuln/detail/CVE-2025-5678"

    def test_extract_reference_url_unknown(self) -> None:
        """Test extracting reference URL for unknown format."""
        url = _extract_reference_url("UNKNOWN-FORMAT")
        assert url is None

    def test_extract_reference_url_empty(self) -> None:
        """Test extracting reference URL for empty ID."""
        url = _extract_reference_url("")
        assert url is None
