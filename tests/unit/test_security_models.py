"""Unit tests for security finding and remediation data models.

This module tests the SecurityFinding and RemediationPlan dataclasses
to ensure proper validation, data integrity, and functionality.
"""

from datetime import date, datetime, timedelta, timezone

import pytest

from security.models import RemediationPlan, SecurityFinding, create_default_remediation_plan


class TestSecurityFinding:
    """Test cases for SecurityFinding dataclass."""

    def test_valid_security_finding_creation(self) -> None:
        """Test creating a valid SecurityFinding with all required fields."""
        finding = SecurityFinding(
            finding_id="CVE-2025-1234",
            package="test-package",
            version="1.0.0",
            severity="high",
            source_scanner="pip-audit",
            discovered_date=datetime.now(timezone.utc).date(),
            description="Test vulnerability description",
            impact="High impact on system security",
            fix_available=True,
            fix_version="1.0.1",
            cvss_score=7.5,
            reference_url="https://nvd.nist.gov/vuln/detail/CVE-2025-1234",
        )

        assert finding.finding_id == "CVE-2025-1234"
        assert finding.package == "test-package"
        assert finding.version == "1.0.0"
        assert finding.severity == "high"
        assert finding.source_scanner == "pip-audit"
        assert finding.discovered_date == datetime.now(timezone.utc).date()
        assert finding.description == "Test vulnerability description"
        assert finding.impact == "High impact on system security"
        assert finding.fix_available is True
        assert finding.fix_version == "1.0.1"
        assert finding.cvss_score == 7.5
        assert finding.reference_url == "https://nvd.nist.gov/vuln/detail/CVE-2025-1234"

    def test_security_finding_with_minimal_fields(self) -> None:
        """Test creating SecurityFinding with only required fields."""
        finding = SecurityFinding(
            finding_id="GHSA-abcd-efgh-ijkl",
            package="minimal-package",
            version="2.0.0",
            severity="medium",
            source_scanner="bandit",
            discovered_date=datetime.now(timezone.utc).date(),
            description="Minimal test description",
            impact="Medium impact",
            fix_available=False,
        )

        assert finding.finding_id == "GHSA-abcd-efgh-ijkl"
        assert finding.fix_version is None
        assert finding.cvss_score is None
        assert finding.reference_url is None

    def test_finding_id_validation_cve_format(self) -> None:
        """Test finding_id validation for CVE format."""
        # Valid CVE formats
        valid_cves = ["CVE-2025-1234", "CVE-2020-12345", "CVE-2023-999999"]

        for cve_id in valid_cves:
            finding = SecurityFinding(
                finding_id=cve_id,
                package="test-package",
                version="1.0.0",
                severity="high",
                source_scanner="pip-audit",
                discovered_date=datetime.now(timezone.utc).date(),
                description="Test description",
                impact="Test impact",
                fix_available=True,
            )
            assert finding.finding_id == cve_id

    def test_finding_id_validation_failures(self) -> None:
        """Test finding_id validation with invalid inputs."""
        invalid_finding_ids = [
            "",  # Empty string
            "AB",  # Too short
            "A" * 101,  # Too long
        ]

        for invalid_id in invalid_finding_ids:
            with pytest.raises(ValueError, match="finding_id"):
                SecurityFinding(
                    finding_id=invalid_id,
                    package="test-package",
                    version="1.0.0",
                    severity="high",
                    source_scanner="pip-audit",
                    discovered_date=datetime.now(timezone.utc).date(),
                    description="Test description",
                    impact="Test impact",
                    fix_available=True,
                )

    def test_severity_validation_valid_levels(self) -> None:
        """Test severity validation with valid severity levels."""
        valid_severities = ["critical", "high", "medium", "low", "info", "unknown"]

        for severity in valid_severities:
            finding = SecurityFinding(
                finding_id="CVE-2025-1234",
                package="test-package",
                version="1.0.0",
                severity=severity,
                source_scanner="pip-audit",
                discovered_date=datetime.now(timezone.utc).date(),
                description="Test description",
                impact="Test impact",
                fix_available=True,
            )
            assert finding.severity == severity.lower()

    def test_severity_validation_failures(self) -> None:
        """Test severity validation with invalid severity levels."""
        invalid_severities = ["invalid", "super-high"]

        for invalid_severity in invalid_severities:
            with pytest.raises(ValueError, match="severity"):
                SecurityFinding(
                    finding_id="CVE-2025-1234",
                    package="test-package",
                    version="1.0.0",
                    severity=invalid_severity,
                    source_scanner="pip-audit",
                    discovered_date=datetime.now(timezone.utc).date(),
                    description="Test description",
                    impact="Test impact",
                    fix_available=True,
                )

    def test_cvss_score_validation_valid_range(self) -> None:
        """Test CVSS score validation with valid scores."""
        valid_scores = [0.0, 2.5, 5.0, 7.5, 10.0, 3, 8]  # Include integers

        for score in valid_scores:
            finding = SecurityFinding(
                finding_id="CVE-2025-1234",
                package="test-package",
                version="1.0.0",
                severity="high",
                source_scanner="pip-audit",
                discovered_date=datetime.now(timezone.utc).date(),
                description="Test description",
                impact="Test impact",
                fix_available=True,
                cvss_score=score,
            )
            assert finding.cvss_score == score

    def test_cvss_score_validation_failures(self) -> None:
        """Test CVSS score validation with invalid scores."""
        invalid_scores = [-1.0, 10.1, 15.0, "7.5"]

        for invalid_score in invalid_scores:
            with pytest.raises(ValueError, match="cvss_score"):
                SecurityFinding(
                    finding_id="CVE-2025-1234",
                    package="test-package",
                    version="1.0.0",
                    severity="high",
                    source_scanner="pip-audit",
                    discovered_date=datetime.now(timezone.utc).date(),
                    description="Test description",
                    impact="Test impact",
                    fix_available=True,
                    cvss_score=invalid_score,
                )

    def test_reference_url_validation_valid_urls(self) -> None:
        """Test reference URL validation with valid URLs."""
        valid_urls = [
            "https://nvd.nist.gov/vuln/detail/CVE-2025-1234",
            "http://example.com/advisory",
            "https://github.com/advisories/GHSA-abcd-efgh-ijkl",
        ]

        for url in valid_urls:
            finding = SecurityFinding(
                finding_id="CVE-2025-1234",
                package="test-package",
                version="1.0.0",
                severity="high",
                source_scanner="pip-audit",
                discovered_date=datetime.now(timezone.utc).date(),
                description="Test description",
                impact="Test impact",
                fix_available=True,
                reference_url=url,
            )
            assert finding.reference_url == url

    def test_reference_url_validation_failures(self) -> None:
        """Test reference URL validation with invalid URLs."""
        invalid_urls = ["not-a-url", "just-text"]

        for invalid_url in invalid_urls:
            with pytest.raises(ValueError, match="reference_url"):
                SecurityFinding(
                    finding_id="CVE-2025-1234",
                    package="test-package",
                    version="1.0.0",
                    severity="high",
                    source_scanner="pip-audit",
                    discovered_date=datetime.now(timezone.utc).date(),
                    description="Test description",
                    impact="Test impact",
                    fix_available=True,
                    reference_url=invalid_url,
                )

    def test_days_since_discovery(self) -> None:
        """Test days_since_discovery calculation."""
        # Test with today's date
        finding_today = SecurityFinding(
            finding_id="CVE-2025-1234",
            package="test-package",
            version="1.0.0",
            severity="high",
            source_scanner="pip-audit",
            discovered_date=datetime.now(timezone.utc).date(),
            description="Test description",
            impact="Test impact",
            fix_available=True,
        )
        assert finding_today.days_since_discovery() == 0

        # Test with past date
        past_date = datetime.now(timezone.utc).date() - timedelta(days=5)
        finding_past = SecurityFinding(
            finding_id="CVE-2025-5678",
            package="test-package",
            version="1.0.0",
            severity="medium",
            source_scanner="pip-audit",
            discovered_date=past_date,
            description="Test description",
            impact="Test impact",
            fix_available=False,
        )
        assert finding_past.days_since_discovery() == 5

    def test_is_high_severity(self) -> None:
        """Test is_high_severity method."""
        high_severities = ["critical", "high"]
        low_severities = ["medium", "low", "info", "unknown"]

        for severity in high_severities:
            finding = SecurityFinding(
                finding_id="CVE-2025-1234",
                package="test-package",
                version="1.0.0",
                severity=severity,
                source_scanner="pip-audit",
                discovered_date=datetime.now(timezone.utc).date(),
                description="Test description",
                impact="Test impact",
                fix_available=True,
            )
            assert finding.is_high_severity() is True

        for severity in low_severities:
            finding = SecurityFinding(
                finding_id="CVE-2025-5678",
                package="test-package",
                version="1.0.0",
                severity=severity,
                source_scanner="pip-audit",
                discovered_date=datetime.now(timezone.utc).date(),
                description="Test description",
                impact="Test impact",
                fix_available=True,
            )
            assert finding.is_high_severity() is False

    def test_to_dict_conversion(self) -> None:
        """Test conversion to dictionary representation."""
        finding = SecurityFinding(
            finding_id="CVE-2025-1234",
            package="test-package",
            version="1.0.0",
            severity="high",
            source_scanner="pip-audit",
            discovered_date=date(2025, 1, 15),
            description="Test vulnerability description",
            impact="High impact on system security",
            fix_available=True,
            fix_version="1.0.1",
            cvss_score=7.5,
            reference_url="https://nvd.nist.gov/vuln/detail/CVE-2025-1234",
        )

        expected_dict = {
            "finding_id": "CVE-2025-1234",
            "package": "test-package",
            "version": "1.0.0",
            "severity": "high",
            "source_scanner": "pip-audit",
            "discovered_date": "2025-01-15",
            "description": "Test vulnerability description",
            "impact": "High impact on system security",
            "fix_available": True,
            "fix_version": "1.0.1",
            "cvss_score": 7.5,
            "reference_url": "https://nvd.nist.gov/vuln/detail/CVE-2025-1234",
        }

        assert finding.to_dict() == expected_dict


class TestRemediationPlan:
    """Test cases for RemediationPlan dataclass."""

    def test_valid_remediation_plan_creation(self) -> None:
        """Test creating a valid RemediationPlan with all fields."""
        target_date = datetime.now(timezone.utc).date() + timedelta(days=30)
        plan = RemediationPlan(
            finding_id="CVE-2025-1234",
            status="in_progress",
            planned_action="Upgrade to version 1.0.1",
            assigned_to="security-team",
            notes="Upgrade scheduled for next maintenance window",
            workaround="Disable affected feature temporarily",
            target_date=target_date,
            priority="high",
            business_impact="Medium impact on user authentication",
        )

        assert plan.finding_id == "CVE-2025-1234"
        assert plan.status == "in_progress"
        assert plan.planned_action == "Upgrade to version 1.0.1"
        assert plan.assigned_to == "security-team"
        assert plan.notes == "Upgrade scheduled for next maintenance window"
        assert plan.workaround == "Disable affected feature temporarily"
        assert plan.target_date == target_date
        assert plan.priority == "high"
        assert plan.business_impact == "Medium impact on user authentication"
        # Check dates are within reasonable range (today or yesterday due to timezone differences)
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)
        assert plan.created_date in (today, yesterday)
        assert plan.updated_date in (today, yesterday)

    def test_remediation_plan_with_minimal_fields(self) -> None:
        """Test creating RemediationPlan with only required fields."""
        plan = RemediationPlan(
            finding_id="GHSA-abcd-efgh-ijkl",
            status="new",
            planned_action="Under evaluation",
            assigned_to="dev-team",
            notes="",
            workaround="",
        )

        assert plan.finding_id == "GHSA-abcd-efgh-ijkl"
        assert plan.status == "new"
        assert plan.target_date is None
        assert plan.priority == "medium"  # Default value
        assert plan.business_impact == "unknown"  # Default value

    def test_status_validation_valid_statuses(self) -> None:
        """Test status validation with valid status values."""
        valid_statuses = [
            "new",
            "in_progress",
            "awaiting_upstream",
            "completed",
            "deferred",
            "accepted_risk",
            "false_positive",
        ]

        for status in valid_statuses:
            plan = RemediationPlan(
                finding_id="CVE-2025-1234",
                status=status,
                planned_action="Test action",
                assigned_to="test-team",
                notes="Test notes",
                workaround="Test workaround",
            )
            assert plan.status == status.lower()

    def test_status_validation_failures(self) -> None:
        """Test status validation with invalid status values."""
        invalid_statuses = ["invalid", "pending"]

        for invalid_status in invalid_statuses:
            with pytest.raises(ValueError, match="status"):
                RemediationPlan(
                    finding_id="CVE-2025-1234",
                    status=invalid_status,
                    planned_action="Test action",
                    assigned_to="test-team",
                    notes="Test notes",
                    workaround="Test workaround",
                )

    def test_priority_validation_valid_priorities(self) -> None:
        """Test priority validation with valid priority levels."""
        valid_priorities = ["critical", "high", "medium", "low"]

        for priority in valid_priorities:
            plan = RemediationPlan(
                finding_id="CVE-2025-1234",
                status="new",
                planned_action="Test action",
                assigned_to="test-team",
                notes="Test notes",
                workaround="Test workaround",
                priority=priority,
            )
            assert plan.priority == priority.lower()

    def test_is_overdue(self) -> None:
        """Test is_overdue method."""
        # Test not overdue (future target date)
        future_plan = RemediationPlan(
            finding_id="CVE-2025-1234",
            status="in_progress",
            planned_action="Test action",
            assigned_to="test-team",
            notes="Test notes",
            workaround="Test workaround",
            target_date=datetime.now(timezone.utc).date() + timedelta(days=5),
        )
        assert future_plan.is_overdue() is False

        # Test overdue (past target date)
        overdue_plan = RemediationPlan(
            finding_id="CVE-2025-5678",
            status="in_progress",
            planned_action="Test action",
            assigned_to="test-team",
            notes="Test notes",
            workaround="Test workaround",
            target_date=datetime.now(timezone.utc).date() - timedelta(days=5),
        )
        assert overdue_plan.is_overdue() is True

        # Test completed (not overdue even if past target date)
        completed_plan = RemediationPlan(
            finding_id="CVE-2025-9999",
            status="completed",
            planned_action="Test action",
            assigned_to="test-team",
            notes="Test notes",
            workaround="Test workaround",
            target_date=datetime.now(timezone.utc).date() - timedelta(days=5),
        )
        assert completed_plan.is_overdue() is False

        # Test no target date
        no_target_plan = RemediationPlan(
            finding_id="CVE-2025-0000",
            status="new",
            planned_action="Test action",
            assigned_to="test-team",
            notes="Test notes",
            workaround="Test workaround",
        )
        assert no_target_plan.is_overdue() is False

    def test_days_until_target(self) -> None:
        """Test days_until_target calculation."""
        # Test future target date
        future_plan = RemediationPlan(
            finding_id="CVE-2025-1234",
            status="new",
            planned_action="Test action",
            assigned_to="test-team",
            notes="Test notes",
            workaround="Test workaround",
            target_date=datetime.now(timezone.utc).date() + timedelta(days=10),
        )
        assert future_plan.days_until_target() == 10

        # Test past target date (negative days)
        past_plan = RemediationPlan(
            finding_id="CVE-2025-5678",
            status="new",
            planned_action="Test action",
            assigned_to="test-team",
            notes="Test notes",
            workaround="Test workaround",
            target_date=datetime.now(timezone.utc).date() - timedelta(days=5),
        )
        assert past_plan.days_until_target() == -5

        # Test no target date
        no_target_plan = RemediationPlan(
            finding_id="CVE-2025-0000",
            status="new",
            planned_action="Test action",
            assigned_to="test-team",
            notes="Test notes",
            workaround="Test workaround",
        )
        assert no_target_plan.days_until_target() is None

    def test_update_status(self) -> None:
        """Test update_status method."""
        plan = RemediationPlan(
            finding_id="CVE-2025-1234",
            status="new",
            planned_action="Test action",
            assigned_to="test-team",
            notes="Initial notes",
            workaround="Test workaround",
        )

        # Update status with notes
        plan.update_status("in_progress", "Started working on fix")

        assert plan.status == "in_progress"
        assert plan.updated_date == datetime.now(timezone.utc).date()
        assert "Status changed from new to in_progress" in plan.notes
        assert "Started working on fix" in plan.notes

        # Update status without notes
        plan.update_status("completed")
        assert plan.status == "completed"
        assert plan.updated_date == datetime.now(timezone.utc).date()

    def test_to_dict_conversion(self) -> None:
        """Test conversion to dictionary representation."""
        target_date = date(2025, 2, 15)
        created_date = date(2025, 1, 1)
        updated_date = date(2025, 1, 10)

        plan = RemediationPlan(
            finding_id="CVE-2025-1234",
            status="in_progress",
            planned_action="Upgrade to version 1.0.1",
            assigned_to="security-team",
            notes="Upgrade scheduled for next maintenance window",
            workaround="Disable affected feature temporarily",
            target_date=target_date,
            priority="high",
            business_impact="Medium impact on user authentication",
            created_date=created_date,
            updated_date=updated_date,
        )

        expected_dict = {
            "finding_id": "CVE-2025-1234",
            "status": "in_progress",
            "planned_action": "Upgrade to version 1.0.1",
            "assigned_to": "security-team",
            "notes": "Upgrade scheduled for next maintenance window",
            "workaround": "Disable affected feature temporarily",
            "target_date": "2025-02-15",
            "priority": "high",
            "business_impact": "Medium impact on user authentication",
            "created_date": "2025-01-01",
            "updated_date": "2025-01-10",
        }

        assert plan.to_dict() == expected_dict


class TestCreateDefaultRemediationPlan:
    """Test cases for create_default_remediation_plan function."""

    def test_create_default_plan(self) -> None:
        """Test creating a default remediation plan."""
        finding_id = "CVE-2025-1234"
        plan = create_default_remediation_plan(finding_id)

        assert plan.finding_id == finding_id
        assert plan.status == "new"
        assert plan.planned_action == "Under evaluation"
        assert plan.assigned_to == "security-team"
        assert plan.notes == "Newly discovered - assessment in progress"
        assert plan.workaround == "None identified"
        assert plan.priority == "medium"
        assert plan.business_impact == "Under assessment"
        assert plan.target_date is None
        # Check dates are within reasonable range (today or yesterday due to timezone differences)
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)
        assert plan.created_date in (today, yesterday)
        assert plan.updated_date in (today, yesterday)

    def test_create_default_plan_different_finding_ids(self) -> None:
        """Test creating default plans for different finding ID formats."""
        finding_ids = [
            "CVE-2025-1234",
            "GHSA-abcd-efgh-ijkl",
            "PYSEC-2025-123",
            "CUSTOM-FINDING-001",
        ]

        for finding_id in finding_ids:
            plan = create_default_remediation_plan(finding_id)
            assert plan.finding_id == finding_id
            assert plan.status == "new"
            # All other fields should have the same defaults
            assert plan.planned_action == "Under evaluation"
            assert plan.assigned_to == "security-team"
