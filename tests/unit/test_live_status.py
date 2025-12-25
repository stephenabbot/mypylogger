"""Tests for live security status data management."""

from datetime import date, datetime, timezone
import json
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch

import pytest

from badges.live_status import (
    SecurityStatus,
    SecurityStatusFinding,
    SecurityStatusManager,
    VulnerabilitySummary,
    get_default_status_manager,
    update_live_security_status,
)
from security.models import SecurityFinding


class TestVulnerabilitySummary:
    """Test VulnerabilitySummary class."""

    def test_init_valid_data(self) -> None:
        """Test initialization with valid data."""
        summary = VulnerabilitySummary(
            total=5,
            critical=1,
            high=2,
            medium=1,
            low=1,
            info=0,
        )

        assert summary.total == 5
        assert summary.critical == 1
        assert summary.high == 2
        assert summary.medium == 1
        assert summary.low == 1
        assert summary.info == 0

    def test_init_invalid_negative_counts(self) -> None:
        """Test initialization with negative counts raises error."""
        with pytest.raises(ValueError, match="Vulnerability counts cannot be negative"):
            VulnerabilitySummary(total=-1)

    def test_init_invalid_total_mismatch(self) -> None:
        """Test initialization with mismatched total raises error."""
        with pytest.raises(ValueError, match=r"Total count .* does not match sum"):
            VulnerabilitySummary(
                total=10,  # Should be 3
                critical=1,
                high=1,
                medium=1,
                low=0,
                info=0,
            )

    def test_from_findings_empty(self) -> None:
        """Test creating summary from empty findings list."""
        summary = VulnerabilitySummary.from_findings([])

        assert summary.total == 0
        assert summary.critical == 0
        assert summary.high == 0
        assert summary.medium == 0
        assert summary.low == 0
        assert summary.info == 0

    def test_from_findings_mixed_severities(self) -> None:
        """Test creating summary from findings with mixed severities."""
        findings = [
            SecurityFinding(
                finding_id="CVE-2023-0001",
                package="test-pkg",
                version="1.0.0",
                severity="critical",
                source_scanner="test",
                discovered_date=date.today(),
                description="Test critical",
                impact="High impact",
                fix_available=True,
            ),
            SecurityFinding(
                finding_id="CVE-2023-0002",
                package="test-pkg",
                version="1.0.0",
                severity="high",
                source_scanner="test",
                discovered_date=date.today(),
                description="Test high",
                impact="High impact",
                fix_available=True,
            ),
            SecurityFinding(
                finding_id="CVE-2023-0003",
                package="test-pkg",
                version="1.0.0",
                severity="medium",
                source_scanner="test",
                discovered_date=date.today(),
                description="Test medium",
                impact="Medium impact",
                fix_available=False,
            ),
        ]

        summary = VulnerabilitySummary.from_findings(findings)

        assert summary.total == 3
        assert summary.critical == 1
        assert summary.high == 1
        assert summary.medium == 1
        assert summary.low == 0
        assert summary.info == 0

    def test_to_dict(self) -> None:
        """Test converting summary to dictionary."""
        summary = VulnerabilitySummary(
            total=3,
            critical=1,
            high=1,
            medium=1,
            low=0,
            info=0,
        )

        result = summary.to_dict()

        expected = {
            "total": 3,
            "critical": 1,
            "high": 1,
            "medium": 1,
            "low": 0,
            "info": 0,
        }
        assert result == expected


class TestSecurityStatusFinding:
    """Test SecurityStatusFinding class."""

    def test_from_security_finding(self) -> None:
        """Test creating status finding from security finding."""
        security_finding = SecurityFinding(
            finding_id="CVE-2023-0001",
            package="test-pkg",
            version="1.0.0",
            severity="high",
            source_scanner="test",
            discovered_date=date(2023, 1, 1),
            description="Test vulnerability",
            impact="High impact",
            fix_available=True,
            fix_version="1.0.1",
            reference_url="https://example.com/cve-2023-0001",
        )

        status_finding = SecurityStatusFinding.from_security_finding(security_finding)

        assert status_finding.finding_id == "CVE-2023-0001"
        assert status_finding.package == "test-pkg"
        assert status_finding.version == "1.0.0"
        assert status_finding.severity == "high"
        assert status_finding.discovered_date == "2023-01-01"
        assert status_finding.description == "Test vulnerability"
        assert status_finding.fix_available is True
        assert status_finding.fix_version == "1.0.1"
        assert status_finding.reference_url == "https://example.com/cve-2023-0001"

    def test_to_dict(self) -> None:
        """Test converting status finding to dictionary."""
        finding = SecurityStatusFinding(
            finding_id="CVE-2023-0001",
            package="test-pkg",
            version="1.0.0",
            severity="high",
            discovered_date="2023-01-01",
            days_since_discovery=30,
            description="Test vulnerability",
            fix_available=True,
            fix_version="1.0.1",
            reference_url="https://example.com/cve",
        )

        result = finding.to_dict()

        expected = {
            "finding_id": "CVE-2023-0001",
            "package": "test-pkg",
            "version": "1.0.0",
            "severity": "high",
            "discovered_date": "2023-01-01",
            "days_since_discovery": 30,
            "description": "Test vulnerability",
            "fix_available": True,
            "fix_version": "1.0.1",
            "reference_url": "https://example.com/cve",
        }
        assert result == expected


class TestSecurityStatus:
    """Test SecurityStatus class."""

    def test_init_valid_data(self) -> None:
        """Test initialization with valid data."""
        now = datetime.now(timezone.utc)
        summary = VulnerabilitySummary(total=0)

        status = SecurityStatus(
            last_updated=now,
            scan_date=now,
            vulnerability_summary=summary,
        )

        assert status.last_updated == now
        assert status.scan_date == now
        assert status.vulnerability_summary == summary
        assert status.security_grade == "A"
        assert status.days_since_last_vulnerability == 0
        assert status.remediation_status == "current"

    def test_init_invalid_timezone_naive(self) -> None:
        """Test initialization with timezone-naive datetime raises error."""
        naive_dt = datetime.now()  # No timezone
        summary = VulnerabilitySummary(total=0)

        with pytest.raises(ValueError, match="must be timezone-aware"):
            SecurityStatus(
                last_updated=naive_dt,
                scan_date=naive_dt,
                vulnerability_summary=summary,
            )

    def test_init_invalid_security_grade(self) -> None:
        """Test initialization with invalid security grade raises error."""
        now = datetime.now(timezone.utc)
        summary = VulnerabilitySummary(total=0)

        with pytest.raises(ValueError, match="security_grade must be one of"):
            SecurityStatus(
                last_updated=now,
                scan_date=now,
                vulnerability_summary=summary,
                security_grade="X",  # Invalid grade
            )

    def test_init_invalid_remediation_status(self) -> None:
        """Test initialization with invalid remediation status raises error."""
        now = datetime.now(timezone.utc)
        summary = VulnerabilitySummary(total=0)

        with pytest.raises(ValueError, match="remediation_status must be one of"):
            SecurityStatus(
                last_updated=now,
                scan_date=now,
                vulnerability_summary=summary,
                remediation_status="invalid",
            )

    def test_from_findings_empty(self) -> None:
        """Test creating status from empty findings list."""
        status = SecurityStatus.from_findings([])

        assert status.vulnerability_summary.total == 0
        assert status.security_grade == "A"
        assert status.days_since_last_vulnerability == 0
        assert status.remediation_status == "current"
        assert len(status.findings) == 0

    def test_from_findings_with_vulnerabilities(self) -> None:
        """Test creating status from findings with vulnerabilities."""
        findings = [
            SecurityFinding(
                finding_id="CVE-2023-0001",
                package="test-pkg",
                version="1.0.0",
                severity="critical",
                source_scanner="test",
                discovered_date=date.today(),
                description="Critical vulnerability",
                impact="High impact",
                fix_available=True,
            ),
        ]

        status = SecurityStatus.from_findings(findings)

        assert status.vulnerability_summary.total == 1
        assert status.vulnerability_summary.critical == 1
        assert status.security_grade == "F"  # Critical = F grade
        assert status.remediation_status == "pending"  # Critical = pending
        assert len(status.findings) == 1

    def test_calculate_security_grade_critical(self) -> None:
        """Test security grade calculation with critical vulnerabilities."""
        summary = VulnerabilitySummary(total=1, critical=1)
        grade = SecurityStatus._calculate_security_grade(summary)
        assert grade == "F"

    def test_calculate_security_grade_high_multiple(self) -> None:
        """Test security grade calculation with multiple high vulnerabilities."""
        summary = VulnerabilitySummary(total=3, high=3)
        grade = SecurityStatus._calculate_security_grade(summary)
        assert grade == "D"

    def test_calculate_security_grade_high_single(self) -> None:
        """Test security grade calculation with single high vulnerability."""
        summary = VulnerabilitySummary(total=1, high=1)
        grade = SecurityStatus._calculate_security_grade(summary)
        assert grade == "C"

    def test_calculate_security_grade_medium_multiple(self) -> None:
        """Test security grade calculation with multiple medium vulnerabilities."""
        summary = VulnerabilitySummary(total=6, medium=6)
        grade = SecurityStatus._calculate_security_grade(summary)
        assert grade == "C"

    def test_calculate_security_grade_medium_few(self) -> None:
        """Test security grade calculation with few medium vulnerabilities."""
        summary = VulnerabilitySummary(total=2, medium=2)
        grade = SecurityStatus._calculate_security_grade(summary)
        assert grade == "B"

    def test_calculate_security_grade_low_many(self) -> None:
        """Test security grade calculation with many low vulnerabilities."""
        summary = VulnerabilitySummary(total=15, low=15)
        grade = SecurityStatus._calculate_security_grade(summary)
        assert grade == "B"

    def test_calculate_security_grade_clean(self) -> None:
        """Test security grade calculation with no significant vulnerabilities."""
        summary = VulnerabilitySummary(total=2, low=2)
        grade = SecurityStatus._calculate_security_grade(summary)
        assert grade == "A"

    def test_calculate_days_since_last_vulnerability_empty(self) -> None:
        """Test days calculation with no vulnerabilities."""
        days = SecurityStatus._calculate_days_since_last_vulnerability([])
        assert days == 0

    def test_determine_remediation_status_clean(self) -> None:
        """Test remediation status with no vulnerabilities."""
        summary = VulnerabilitySummary(total=0)
        status = SecurityStatus._determine_remediation_status(summary)
        assert status == "current"

    def test_determine_remediation_status_critical(self) -> None:
        """Test remediation status with critical vulnerabilities."""
        summary = VulnerabilitySummary(total=1, critical=1)
        status = SecurityStatus._determine_remediation_status(summary)
        assert status == "pending"

    def test_determine_remediation_status_high(self) -> None:
        """Test remediation status with high vulnerabilities."""
        summary = VulnerabilitySummary(total=1, high=1)
        status = SecurityStatus._determine_remediation_status(summary)
        assert status == "pending"

    def test_determine_remediation_status_medium(self) -> None:
        """Test remediation status with medium vulnerabilities."""
        summary = VulnerabilitySummary(total=1, medium=1)
        status = SecurityStatus._determine_remediation_status(summary)
        assert status == "pending"

    def test_determine_remediation_status_low_only(self) -> None:
        """Test remediation status with only low vulnerabilities."""
        summary = VulnerabilitySummary(total=1, low=1)
        status = SecurityStatus._determine_remediation_status(summary)
        assert status == "current"

    def test_to_dict(self) -> None:
        """Test converting status to dictionary."""
        now = datetime.now(timezone.utc)
        summary = VulnerabilitySummary(total=1, medium=1)
        finding = SecurityStatusFinding(
            finding_id="CVE-2023-0001",
            package="test-pkg",
            version="1.0.0",
            severity="medium",
            discovered_date="2023-01-01",
            days_since_discovery=30,
            description="Test vulnerability",
            fix_available=True,
        )

        status = SecurityStatus(
            last_updated=now,
            scan_date=now,
            vulnerability_summary=summary,
            findings=[finding],
            security_grade="B",
            days_since_last_vulnerability=30,
            remediation_status="pending",
        )

        result = status.to_dict()

        assert result["last_updated"] == now.isoformat()
        assert result["scan_date"] == now.isoformat()
        assert result["vulnerability_summary"] == summary.to_dict()
        assert result["findings"] == [finding.to_dict()]
        assert result["security_grade"] == "B"
        assert result["days_since_last_vulnerability"] == 30
        assert result["remediation_status"] == "pending"

    def test_to_json(self) -> None:
        """Test converting status to JSON string."""
        now = datetime.now(timezone.utc)
        summary = VulnerabilitySummary(total=0)

        status = SecurityStatus(
            last_updated=now,
            scan_date=now,
            vulnerability_summary=summary,
        )

        json_str = status.to_json()
        parsed = json.loads(json_str)

        assert parsed["last_updated"] == now.isoformat()
        assert parsed["security_grade"] == "A"


class TestSecurityStatusManager:
    """Test SecurityStatusManager class."""

    def test_init_default_paths(self) -> None:
        """Test initialization with default paths."""
        manager = SecurityStatusManager()

        assert manager.reports_dir == Path("security/reports/latest")
        assert manager.status_file == Path("security-status/index.json")

    def test_init_custom_paths(self) -> None:
        """Test initialization with custom paths."""
        reports_dir = Path("/custom/reports")
        status_file = Path("/custom/status.json")

        manager = SecurityStatusManager(reports_dir, status_file)

        assert manager.reports_dir == reports_dir
        assert manager.status_file == status_file

    def test_update_status_success(self) -> None:
        """Test successful status update."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            reports_dir = temp_path / "reports"
            status_file = temp_path / "status.json"

            # Create reports directory and mock reports
            reports_dir.mkdir(parents=True)

            # Mock the extract_all_findings function to return test findings
            with patch("badges.live_status.extract_all_findings") as mock_extract:
                mock_findings = [
                    SecurityFinding(
                        finding_id="CVE-2023-0001",
                        package="test-pkg",
                        version="1.0.0",
                        severity="medium",
                        source_scanner="test",
                        discovered_date=date.today(),
                        description="Test vulnerability",
                        impact="Medium impact",
                        fix_available=True,
                    ),
                ]
                mock_extract.return_value = mock_findings

                manager = SecurityStatusManager(reports_dir, status_file)
                status = manager.update_status()

                assert status.vulnerability_summary.total == 1
                assert status.vulnerability_summary.medium == 1
                assert status.security_grade == "B"
                assert status_file.exists()

                # Verify JSON content
                with status_file.open("r") as f:
                    data = json.load(f)
                assert data["vulnerability_summary"]["total"] == 1

    def test_get_current_status_no_file(self) -> None:
        """Test getting current status when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            status_file = temp_path / "nonexistent.json"

            manager = SecurityStatusManager(status_file=status_file)
            status = manager.get_current_status()

            assert status is None

    def test_get_current_status_success(self) -> None:
        """Test getting current status from existing file."""
        now = datetime.now(timezone.utc)
        test_data = {
            "last_updated": now.isoformat(),
            "scan_date": now.isoformat(),
            "vulnerability_summary": {
                "total": 1,
                "critical": 0,
                "high": 0,
                "medium": 1,
                "low": 0,
                "info": 0,
            },
            "findings": [],
            "security_grade": "B",
            "days_since_last_vulnerability": 30,
            "remediation_status": "pending",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            status_file = temp_path / "status.json"

            # Write test data
            with status_file.open("w") as f:
                json.dump(test_data, f)

            manager = SecurityStatusManager(status_file=status_file)
            status = manager.get_current_status()

            assert status is not None
            assert status.vulnerability_summary.total == 1
            assert status.security_grade == "B"
            assert status.days_since_last_vulnerability == 30

    def test_update_status_extract_failure(self) -> None:
        """Test status update when findings extraction fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            with patch("badges.live_status.extract_all_findings") as mock_extract:
                mock_extract.side_effect = RuntimeError("Extraction failed")

                manager = SecurityStatusManager(status_file=temp_path / "status.json")

                with pytest.raises(RuntimeError, match="Failed to update security status"):
                    manager.update_status()


class TestModuleFunctions:
    """Test module-level functions."""

    def test_get_default_status_manager(self) -> None:
        """Test getting default status manager."""
        manager = get_default_status_manager()

        assert isinstance(manager, SecurityStatusManager)
        assert manager.reports_dir == Path("security/reports/latest")
        assert manager.status_file == Path("security-status/index.json")

    @patch("badges.live_status.SecurityStatusManager")
    def test_update_live_security_status(self, mock_manager_class: Mock) -> None:
        """Test update_live_security_status function."""
        mock_manager = Mock()
        mock_status = Mock()
        mock_manager.update_status.return_value = mock_status
        mock_manager_class.return_value = mock_manager

        reports_dir = Path("/custom/reports")
        status_file = Path("/custom/status.json")

        result = update_live_security_status(reports_dir, status_file)

        mock_manager_class.assert_called_once_with(reports_dir, status_file)
        mock_manager.update_status.assert_called_once()
        assert result == mock_status
