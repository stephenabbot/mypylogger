"""Unit tests for security findings document generator.

This module tests the FindingsDocumentGenerator class and related functionality
for generating live markdown documents from security findings.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
import tempfile

import pytest

from security.generator import (
    FindingsDocumentGenerator,
    generate_findings_document,
    get_default_generator,
)
from security.models import RemediationPlan, SecurityFinding
from security.remediation import RemediationDatastore


class TestFindingsDocumentGenerator:
    """Test cases for FindingsDocumentGenerator class."""

    def test_init_with_defaults(self) -> None:
        """Test initialization with default parameters."""
        generator = FindingsDocumentGenerator()

        assert isinstance(generator.datastore, RemediationDatastore)
        assert generator.reports_dir == Path("security/reports/latest")
        assert generator.output_file == Path("security/findings/SECURITY_FINDINGS.md")

    def test_init_with_custom_parameters(self) -> None:
        """Test initialization with custom parameters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            datastore_path = Path(temp_dir) / "custom-registry.yml"
            reports_dir = Path(temp_dir) / "custom-reports"
            output_file = Path(temp_dir) / "custom-findings.md"

            datastore = RemediationDatastore(datastore_path)
            generator = FindingsDocumentGenerator(datastore, reports_dir, output_file)

            assert generator.datastore == datastore
            assert generator.reports_dir == reports_dir
            assert generator.output_file == output_file

    def test_get_current_findings_no_reports_dir(self) -> None:
        """Test getting current findings when reports directory doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_dir = Path(temp_dir) / "nonexistent"
            generator = FindingsDocumentGenerator(reports_dir=nonexistent_dir)

            findings = generator._get_current_findings()

            assert findings == []

    def test_get_current_findings_with_reports(self) -> None:
        """Test getting current findings from scan reports."""
        with tempfile.TemporaryDirectory() as temp_dir:
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir()

            # Create mock scan report
            pip_audit_file = reports_dir / "pip-audit.json"
            pip_audit_data = {
                "dependencies": [
                    {
                        "name": "test-package",
                        "version": "1.0.0",
                        "vulns": [
                            {
                                "id": "CVE-2025-1234",
                                "description": "Test vulnerability",
                                "fix_versions": ["1.0.1"],
                            }
                        ],
                    }
                ]
            }

            with pip_audit_file.open("w") as f:
                json.dump(pip_audit_data, f)

            generator = FindingsDocumentGenerator(reports_dir=reports_dir)
            findings = generator._get_current_findings()

            assert len(findings) == 1
            assert findings[0].finding_id == "CVE-2025-1234"
            assert findings[0].package == "test-package"

    def test_get_remediation_plans(self) -> None:
        """Test getting remediation plans for findings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "registry.yml"
            datastore = RemediationDatastore(registry_path)

            # Create test finding and plan
            finding = SecurityFinding(
                finding_id="CVE-2025-1234",
                package="test-package",
                version="1.0.0",
                severity="high",
                source_scanner="pip-audit",
                discovered_date=datetime.now(timezone.utc).date(),
                description="Test vulnerability",
                impact="High impact",
                fix_available=True,
            )

            datastore.create_default_plan("CVE-2025-1234")

            generator = FindingsDocumentGenerator(datastore=datastore)
            plans = generator._get_remediation_plans([finding])

            assert "CVE-2025-1234" in plans
            assert plans["CVE-2025-1234"].finding_id == "CVE-2025-1234"

    def test_get_remediation_plans_missing_plan(self) -> None:
        """Test getting remediation plans when plan doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "registry.yml"
            datastore = RemediationDatastore(registry_path)

            finding = SecurityFinding(
                finding_id="CVE-2025-1234",
                package="test-package",
                version="1.0.0",
                severity="high",
                source_scanner="pip-audit",
                discovered_date=datetime.now(timezone.utc).date(),
                description="Test vulnerability",
                impact="High impact",
                fix_available=True,
            )

            generator = FindingsDocumentGenerator(datastore=datastore)
            plans = generator._get_remediation_plans([finding])

            assert plans == {}

    def test_generate_header(self) -> None:
        """Test generating document header."""
        generator = FindingsDocumentGenerator()

        findings = [
            SecurityFinding(
                finding_id="CVE-2025-1234",
                package="test-package",
                version="1.0.0",
                severity="high",
                source_scanner="pip-audit",
                discovered_date=datetime.now(timezone.utc).date(),
                description="Test vulnerability",
                impact="High impact",
                fix_available=True,
            )
        ]

        header = generator._generate_header(findings)

        assert "# Security Findings Summary" in header
        assert "**Total Active Findings**: 1" in header
        assert "**Days Since Last Scan**: 0" in header
        assert "UTC" in header

    def test_generate_findings_sections_empty(self) -> None:
        """Test generating findings sections with no findings."""
        generator = FindingsDocumentGenerator()

        content = generator._generate_findings_sections([], {})

        assert "## Current Findings" in content
        assert "No active security findings detected" in content

    def test_generate_findings_sections_with_findings(self) -> None:
        """Test generating findings sections with findings."""
        generator = FindingsDocumentGenerator()

        findings = [
            SecurityFinding(
                finding_id="CVE-2025-1234",
                package="test-package",
                version="1.0.0",
                severity="high",
                source_scanner="pip-audit",
                discovered_date=datetime.now(timezone.utc).date(),
                description="Test vulnerability",
                impact="High impact",
                fix_available=True,
            ),
            SecurityFinding(
                finding_id="CVE-2025-5678",
                package="another-package",
                version="2.0.0",
                severity="medium",
                source_scanner="pip-audit",
                discovered_date=datetime.now(timezone.utc).date(),
                description="Another vulnerability",
                impact="Medium impact",
                fix_available=False,
            ),
        ]

        content = generator._generate_findings_sections(findings, {})

        assert "## Current Findings" in content
        assert "### High Severity" in content
        assert "### Medium Severity" in content
        assert "#### CVE-2025-1234" in content
        assert "#### CVE-2025-5678" in content

    def test_generate_finding_entry(self) -> None:
        """Test generating a single finding entry."""
        generator = FindingsDocumentGenerator()

        finding = SecurityFinding(
            finding_id="CVE-2025-1234",
            package="test-package",
            version="1.0.0",
            severity="high",
            source_scanner="pip-audit",
            discovered_date=date(2025, 10, 20),
            description="Test vulnerability description",
            impact="High impact on system",
            fix_available=True,
            fix_version="1.0.1",
            reference_url="https://example.com/CVE-2025-1234",
        )

        plan = RemediationPlan(
            finding_id="CVE-2025-1234",
            status="in_progress",
            planned_action="Upgrade to version 1.0.1",
            assigned_to="dev-team",
            notes="Working on upgrade",
            workaround="Temporary mitigation",
            target_date=date(2025, 11, 15),
        )

        entry = generator._generate_finding_entry(finding, plan)

        assert "#### CVE-2025-1234 - Test vulnerability description" in entry
        assert "**Package**: test-package 1.0.0" in entry
        assert "**Source**: pip-audit" in entry
        assert "**Discovered**: 2025-10-20" in entry
        assert "**Description**: Test vulnerability description" in entry
        assert "**Impact**: High impact on system" in entry
        assert "**Reference**: https://example.com/CVE-2025-1234" in entry
        assert "**Fix Available**: Yes (1.0.1)" in entry
        assert "**Remediation**: Upgrade to version 1.0.1" in entry
        assert "**Planned Fix Date**: 2025-11-15" in entry
        assert "**Assigned To**: dev-team" in entry
        assert "**Workaround**: Temporary mitigation" in entry

    def test_generate_finding_entry_no_plan(self) -> None:
        """Test generating finding entry without remediation plan."""
        generator = FindingsDocumentGenerator()

        finding = SecurityFinding(
            finding_id="CVE-2025-1234",
            package="test-package",
            version="1.0.0",
            severity="high",
            source_scanner="pip-audit",
            discovered_date=date(2025, 10, 20),
            description="Test vulnerability",
            impact="High impact",
            fix_available=False,
        )

        entry = generator._generate_finding_entry(finding, None)

        assert "#### CVE-2025-1234 - Test vulnerability" in entry
        assert "**Fix Available**: No" in entry
        assert "**Remediation**:" not in entry
        assert "**Assigned To**:" not in entry

    def test_generate_remediation_summary_empty(self) -> None:
        """Test generating remediation summary with no plans."""
        generator = FindingsDocumentGenerator()

        content = generator._generate_remediation_summary({})

        assert "## Remediation Summary" in content
        assert "No remediation plans available" in content

    def test_generate_remediation_summary_with_plans(self) -> None:
        """Test generating remediation summary with plans."""
        generator = FindingsDocumentGenerator()

        plans = {
            "CVE-2025-1234": RemediationPlan(
                finding_id="CVE-2025-1234",
                status="in_progress",
                planned_action="Upgrade",
                assigned_to="dev-team",
                notes="Working on upgrade",
                workaround="None identified",
            ),
            "CVE-2025-5678": RemediationPlan(
                finding_id="CVE-2025-5678",
                status="new",
                planned_action="Evaluate",
                assigned_to="security-team",
                notes="Under evaluation",
                workaround="None identified",
            ),
            "CVE-2025-9999": RemediationPlan(
                finding_id="CVE-2025-9999",
                status="in_progress",
                planned_action="Patch",
                assigned_to="dev-team",
                notes="Applying patch",
                workaround="None identified",
            ),
        }

        content = generator._generate_remediation_summary(plans)

        assert "## Remediation Summary" in content
        assert "**Total Plans**: 3" in content
        assert "**In Progress**: 2" in content
        assert "**New**: 1" in content

    def test_generate_document_complete_workflow(self) -> None:
        """Test complete document generation workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup directories and files
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir()
            output_file = Path(temp_dir) / "findings.md"
            registry_path = Path(temp_dir) / "registry.yml"

            # Create mock scan report
            pip_audit_file = reports_dir / "pip-audit.json"
            pip_audit_data = {
                "dependencies": [
                    {
                        "name": "test-package",
                        "version": "1.0.0",
                        "vulns": [
                            {
                                "id": "CVE-2025-1234",
                                "description": "Test vulnerability",
                                "fix_versions": ["1.0.1"],
                            }
                        ],
                    }
                ]
            }

            with pip_audit_file.open("w") as f:
                json.dump(pip_audit_data, f)

            # Create datastore and plan
            datastore = RemediationDatastore(registry_path)
            datastore.create_default_plan("CVE-2025-1234")

            # Generate document
            generator = FindingsDocumentGenerator(datastore, reports_dir, output_file)
            generator.generate_document()

            # Verify document was created
            assert output_file.exists()

            # Verify document content
            content = output_file.read_text()
            assert "# Security Findings Summary" in content
            assert "CVE-2025-1234" in content
            assert "test-package" in content
            assert "## Remediation Summary" in content

    def test_generate_document_error_handling(self) -> None:
        """Test error handling during document generation."""
        with tempfile.TemporaryDirectory():
            # Create generator with invalid output path (read-only directory)
            invalid_output = Path("/invalid/path/findings.md")
            generator = FindingsDocumentGenerator(output_file=invalid_output)

            with pytest.raises(RuntimeError, match="Failed to generate findings document"):
                generator.generate_document()

    def test_get_current_findings_error_handling(self) -> None:
        """Test error handling when extracting findings fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir()

            # Create invalid JSON file
            invalid_file = reports_dir / "pip-audit.json"
            invalid_file.write_text("invalid json content")

            generator = FindingsDocumentGenerator(reports_dir=reports_dir)

            # The parser logs warnings but doesn't raise exceptions for invalid files
            # It should return an empty list instead
            findings = generator._get_current_findings()
            assert findings == []

    def test_get_remediation_plans_error_handling(self) -> None:
        """Test error handling when getting remediation plans fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "registry.yml"
            datastore = RemediationDatastore(registry_path)

            # Create a finding
            finding = SecurityFinding(
                finding_id="CVE-2025-1234",
                package="test-package",
                version="1.0.0",
                severity="high",
                source_scanner="pip-audit",
                discovered_date=datetime.now(timezone.utc).date(),
                description="Test vulnerability",
                impact="High impact",
                fix_available=True,
            )

            # Mock the datastore to raise an exception
            def mock_get_plan(_finding_id: str) -> None:
                error_msg = "Database error"
                raise RuntimeError(error_msg)

            datastore.get_remediation_plan = mock_get_plan

            generator = FindingsDocumentGenerator(datastore=datastore)

            # Should handle the error gracefully and continue
            plans = generator._get_remediation_plans([finding])
            assert plans == {}

    def test_generate_finding_entry_with_long_description(self) -> None:
        """Test generating finding entry with long description that gets truncated."""
        generator = FindingsDocumentGenerator()

        long_description = "A" * 100  # Long description that should be truncated
        finding = SecurityFinding(
            finding_id="CVE-2025-1234",
            package="test-package",
            version="1.0.0",
            severity="high",
            source_scanner="pip-audit",
            discovered_date=date(2025, 10, 20),
            description=long_description,
            impact="High impact",
            fix_available=True,
        )

        entry = generator._generate_finding_entry(finding, None)

        # Should truncate the description in the title
        assert "..." in entry
        assert len(long_description) > 60  # Ensure we're testing truncation

    def test_generate_finding_entry_with_workaround_none_identified(self) -> None:
        """Test generating finding entry with 'None identified' workaround."""
        generator = FindingsDocumentGenerator()

        finding = SecurityFinding(
            finding_id="CVE-2025-1234",
            package="test-package",
            version="1.0.0",
            severity="high",
            source_scanner="pip-audit",
            discovered_date=date(2025, 10, 20),
            description="Test vulnerability",
            impact="High impact",
            fix_available=True,
        )

        plan = RemediationPlan(
            finding_id="CVE-2025-1234",
            status="new",
            planned_action="Under evaluation",
            assigned_to="security-team",
            notes="Test notes",
            workaround="None identified",  # Should not be included in output
        )

        entry = generator._generate_finding_entry(finding, plan)

        # Should not include workaround when it's "None identified"
        assert "**Workaround**:" not in entry

    def test_generate_findings_sections_severity_ordering(self) -> None:
        """Test that findings are properly ordered by severity."""
        generator = FindingsDocumentGenerator()

        findings = [
            SecurityFinding(
                finding_id="CVE-2025-0001",
                package="pkg1",
                version="1.0.0",
                severity="low",
                source_scanner="pip-audit",
                discovered_date=datetime.now(timezone.utc).date(),
                description="Low severity",
                impact="Low impact",
                fix_available=True,
            ),
            SecurityFinding(
                finding_id="CVE-2025-0002",
                package="pkg2",
                version="1.0.0",
                severity="critical",
                source_scanner="pip-audit",
                discovered_date=datetime.now(timezone.utc).date(),
                description="Critical severity",
                impact="Critical impact",
                fix_available=True,
            ),
            SecurityFinding(
                finding_id="CVE-2025-0003",
                package="pkg3",
                version="1.0.0",
                severity="medium",
                source_scanner="pip-audit",
                discovered_date=datetime.now(timezone.utc).date(),
                description="Medium severity",
                impact="Medium impact",
                fix_available=True,
            ),
        ]

        content = generator._generate_findings_sections(findings, {})

        # Critical should come before medium, which should come before low
        critical_pos = content.find("### Critical Severity")
        medium_pos = content.find("### Medium Severity")
        low_pos = content.find("### Low Severity")

        assert critical_pos < medium_pos < low_pos

    def test_generate_header_with_severity_breakdown(self) -> None:
        """Test generating header with severity breakdown."""
        generator = FindingsDocumentGenerator()

        findings = [
            SecurityFinding(
                finding_id="CVE-2025-0001",
                package="pkg1",
                version="1.0.0",
                severity="high",
                source_scanner="pip-audit",
                discovered_date=datetime.now(timezone.utc).date(),
                description="High severity",
                impact="High impact",
                fix_available=True,
            ),
            SecurityFinding(
                finding_id="CVE-2025-0002",
                package="pkg2",
                version="1.0.0",
                severity="high",
                source_scanner="pip-audit",
                discovered_date=datetime.now(timezone.utc).date(),
                description="Another high severity",
                impact="High impact",
                fix_available=True,
            ),
            SecurityFinding(
                finding_id="CVE-2025-0003",
                package="pkg3",
                version="1.0.0",
                severity="medium",
                source_scanner="pip-audit",
                discovered_date=datetime.now(timezone.utc).date(),
                description="Medium severity",
                impact="Medium impact",
                fix_available=True,
            ),
        ]

        header = generator._generate_header(findings)

        assert "**Total Active Findings**: 3" in header
        assert "**Severity Breakdown**:" in header
        assert "**High**: 2" in header
        assert "**Medium**: 1" in header

    def test_generate_remediation_summary_enhanced(self) -> None:
        """Test generating enhanced remediation summary with priority and overdue info."""
        generator = FindingsDocumentGenerator()

        plans = {
            "CVE-2025-1234": RemediationPlan(
                finding_id="CVE-2025-1234",
                status="in_progress",
                planned_action="Upgrade",
                assigned_to="dev-team",
                notes="Working on upgrade",
                workaround="None identified",
                priority="high",
                target_date=date(2020, 1, 1),  # Overdue date
            ),
            "CVE-2025-5678": RemediationPlan(
                finding_id="CVE-2025-5678",
                status="new",
                planned_action="Evaluate",
                assigned_to="security-team",
                notes="Under evaluation",
                workaround="None identified",
                priority="medium",
            ),
            "CVE-2025-9999": RemediationPlan(
                finding_id="CVE-2025-9999",
                status="awaiting_upstream",
                planned_action="Wait for patch",
                assigned_to="dev-team",
                notes="Waiting for vendor",
                workaround="None identified",
                priority="critical",
            ),
        }

        content = generator._generate_remediation_summary(plans)

        assert "## Remediation Summary" in content
        assert "**Total Plans**: 3" in content
        assert "**In Progress**: 1" in content
        assert "**New**: 1" in content
        assert "**Awaiting Upstream**: 1" in content
        assert "**Priority Breakdown**:" in content
        assert "**Critical**: 1" in content
        assert "**High**: 1" in content
        assert "**Medium**: 1" in content
        assert "**⚠️ Overdue Plans**: 1" in content


class TestModuleFunctions:
    """Test cases for module-level functions."""

    def test_get_default_generator(self) -> None:
        """Test getting default generator instance."""
        generator = get_default_generator()

        assert isinstance(generator, FindingsDocumentGenerator)
        assert isinstance(generator.datastore, RemediationDatastore)

    def test_generate_findings_document_function(self) -> None:
        """Test the generate_findings_document convenience function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "findings.md"

            # Create empty reports directory
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir()

            generate_findings_document(output_file=output_file, reports_dir=reports_dir)

            # Verify document was created
            assert output_file.exists()
            content = output_file.read_text()
            assert "# Security Findings Summary" in content
            assert "No active security findings detected" in content
