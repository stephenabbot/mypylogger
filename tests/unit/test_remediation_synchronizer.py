"""Unit tests for remediation synchronization logic.

This module tests the RemediationSynchronizer class and related functionality
for automatically synchronizing remediation plans with security findings.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import NoReturn
from unittest.mock import patch

import pytest

from security.history import HistoricalDataManager
from security.models import RemediationPlan, SecurityFinding
from security.remediation import RemediationDatastore
from security.synchronizer import RemediationSynchronizer, get_default_synchronizer


class TestRemediationSynchronizer:
    """Test cases for RemediationSynchronizer class."""

    def _create_synchronizer(
        self, datastore: RemediationDatastore, reports_dir: Path, temp_dir: str
    ) -> RemediationSynchronizer:
        """Helper to create synchronizer with proper historical manager."""
        historical_manager = HistoricalDataManager(
            history_dir=Path(temp_dir) / "history",
            reports_dir=reports_dir,
            archived_reports_dir=Path(temp_dir) / "archived",
        )
        return RemediationSynchronizer(datastore, reports_dir, historical_manager)

    def test_init_with_defaults(self) -> None:
        """Test initialization with default parameters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            synchronizer = RemediationSynchronizer()

            assert isinstance(synchronizer.datastore, RemediationDatastore)
            assert synchronizer.reports_dir == Path("security/reports/latest")

    def test_init_with_custom_parameters(self) -> None:
        """Test initialization with custom parameters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            datastore_path = Path(temp_dir) / "custom-registry.yml"
            reports_dir = Path(temp_dir) / "custom-reports"

            datastore = RemediationDatastore(datastore_path)
            synchronizer = self._create_synchronizer(datastore, reports_dir, temp_dir)

            assert synchronizer.datastore == datastore
            assert synchronizer.reports_dir == reports_dir

    def test_get_current_findings_no_reports_dir(self) -> None:
        """Test getting current findings when reports directory doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            nonexistent_dir = Path(temp_dir) / "nonexistent"
            registry_path = Path(temp_dir) / "registry.yml"

            datastore = RemediationDatastore(registry_path)
            synchronizer = RemediationSynchronizer(datastore, nonexistent_dir)

            findings = synchronizer._get_current_findings()

            assert findings == []

    def test_get_current_findings_with_reports(self) -> None:
        """Test getting current findings from scan reports."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir()
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

            datastore = RemediationDatastore(registry_path)
            synchronizer = self._create_synchronizer(datastore, reports_dir, temp_dir)
            findings = synchronizer._get_current_findings()

            assert len(findings) == 1
            assert findings[0].finding_id == "CVE-2025-1234"
            assert findings[0].package == "test-package"

    def test_is_manually_modified_default_plan(self) -> None:
        """Test detecting manually modified plans - default plan."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            registry_path = Path(temp_dir) / "registry.yml"

            datastore = RemediationDatastore(registry_path)
            synchronizer = RemediationSynchronizer(datastore)

            # Create default plan
            plan = RemediationPlan(
                finding_id="CVE-2025-1234",
                status="new",
                planned_action="Under evaluation",
                assigned_to="security-team",
                notes="Newly discovered - assessment in progress",
                workaround="None identified",
                priority="medium",
                business_impact="Under assessment",
            )

            assert not synchronizer._is_manually_modified(plan)

    def test_is_manually_modified_modified_plan(self) -> None:
        """Test detecting manually modified plans - modified plan."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            registry_path = Path(temp_dir) / "registry.yml"

            datastore = RemediationDatastore(registry_path)
            synchronizer = RemediationSynchronizer(datastore)

            # Create modified plan
            plan = RemediationPlan(
                finding_id="CVE-2025-1234",
                status="in_progress",
                planned_action="Upgrade to version 1.0.1",
                assigned_to="dev-team",
                notes="Working on upgrade",
                workaround="Temporary mitigation applied",
                priority="high",
                business_impact="High impact",
                target_date=date(2025, 12, 31),
            )

            assert synchronizer._is_manually_modified(plan)

    def test_synchronize_findings_new_findings(self) -> None:
        """Test synchronizing when new findings are discovered."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "registry.yml"
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir()

            # Create mock finding
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

            datastore = RemediationDatastore(registry_path)
            synchronizer = self._create_synchronizer(datastore, reports_dir, temp_dir)

            # Mock the _get_current_findings method
            synchronizer._get_current_findings = lambda: findings

            stats = synchronizer.synchronize_findings()

            assert stats["added"] == 1
            assert stats["removed"] == 0
            assert stats["preserved"] == 0
            assert stats["errors"] == 0

            # Verify plan was created
            plan = datastore.get_remediation_plan("CVE-2025-1234")
            assert plan is not None
            assert plan.status == "new"

    def test_synchronize_findings_resolved_findings(self) -> None:
        """Test synchronizing when findings are resolved."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "registry.yml"
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir()

            datastore = RemediationDatastore(registry_path)

            # Create existing plan
            plan = datastore.create_default_plan("CVE-2025-1234")

            synchronizer = self._create_synchronizer(datastore, reports_dir, temp_dir)

            # Mock no current findings (finding resolved)
            synchronizer._get_current_findings = list

            stats = synchronizer.synchronize_findings()

            assert stats["added"] == 0
            assert stats["removed"] == 1
            assert stats["preserved"] == 0
            assert stats["errors"] == 0

            # Verify plan was removed
            plan = datastore.get_remediation_plan("CVE-2025-1234")
            assert plan is None

    def test_synchronize_findings_preserve_manual_edits(self) -> None:
        """Test synchronizing while preserving manual edits."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "registry.yml"
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir()

            datastore = RemediationDatastore(registry_path)

            # Create manually modified plan
            plan = RemediationPlan(
                finding_id="CVE-2025-1234",
                status="in_progress",
                planned_action="Custom action",
                assigned_to="dev-team",
                notes="Custom notes",
                workaround="Custom workaround",
                priority="high",
                business_impact="High impact",
            )
            datastore.save_remediation_plan(plan)

            synchronizer = self._create_synchronizer(datastore, reports_dir, temp_dir)

            # Mock no current findings (finding resolved)
            synchronizer._get_current_findings = list

            stats = synchronizer.synchronize_findings(preserve_manual_edits=True)

            assert stats["added"] == 0
            assert stats["removed"] == 0  # Should not be removed due to manual edits
            assert stats["preserved"] == 0
            assert stats["errors"] == 0

            # Verify plan was marked as completed but not removed
            updated_plan = datastore.get_remediation_plan("CVE-2025-1234")
            assert updated_plan is not None
            assert updated_plan.status == "completed"
            assert "Finding resolved - auto-marked as completed" in updated_plan.notes

    def test_resolve_conflicts_create_missing_plan(self) -> None:
        """Test resolving conflicts by creating missing plans."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "registry.yml"
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir()

            # Create mock finding
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

            datastore = RemediationDatastore(registry_path)
            synchronizer = self._create_synchronizer(datastore, reports_dir, temp_dir)

            # Mock current findings
            synchronizer._get_current_findings = lambda: findings

            resolutions = synchronizer.resolve_conflicts(["CVE-2025-1234"])

            assert resolutions["CVE-2025-1234"] == "created_new_plan"

            # Verify plan was created
            plan = datastore.get_remediation_plan("CVE-2025-1234")
            assert plan is not None

    def test_resolve_conflicts_mark_completed(self) -> None:
        """Test resolving conflicts by marking plans as completed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "registry.yml"
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir()

            datastore = RemediationDatastore(registry_path)

            # Create manually modified plan
            plan = RemediationPlan(
                finding_id="CVE-2025-1234",
                status="in_progress",
                planned_action="Custom action",
                assigned_to="dev-team",
                notes="Custom notes",
                workaround="Custom workaround",
            )
            datastore.save_remediation_plan(plan)

            synchronizer = self._create_synchronizer(datastore, reports_dir, temp_dir)

            # Mock no current findings
            synchronizer._get_current_findings = list

            resolutions = synchronizer.resolve_conflicts(["CVE-2025-1234"])

            assert resolutions["CVE-2025-1234"] == "marked_completed"

            # Verify plan was marked as completed
            updated_plan = datastore.get_remediation_plan("CVE-2025-1234")
            assert updated_plan is not None
            assert updated_plan.status == "completed"

    def test_get_synchronization_status(self) -> None:
        """Test getting synchronization status."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "registry.yml"
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir()

            # Create mock findings
            findings = [
                SecurityFinding(
                    finding_id="CVE-2025-1111",
                    package="package1",
                    version="1.0.0",
                    severity="high",
                    source_scanner="pip-audit",
                    discovered_date=datetime.now(timezone.utc).date(),
                    description="Test vulnerability 1",
                    impact="High impact",
                    fix_available=True,
                ),
                SecurityFinding(
                    finding_id="CVE-2025-2222",
                    package="package2",
                    version="1.0.0",
                    severity="medium",
                    source_scanner="pip-audit",
                    discovered_date=datetime.now(timezone.utc).date(),
                    description="Test vulnerability 2",
                    impact="Medium impact",
                    fix_available=True,
                ),
            ]

            datastore = RemediationDatastore(registry_path)

            # Create plans for some findings
            datastore.create_default_plan("CVE-2025-1111")  # In sync
            datastore.create_default_plan("CVE-2025-3333")  # Orphaned

            synchronizer = self._create_synchronizer(datastore, reports_dir, temp_dir)

            # Mock current findings
            synchronizer._get_current_findings = lambda: findings

            status = synchronizer.get_synchronization_status()

            assert status["total_findings"] == 2
            assert status["total_plans"] == 2
            assert status["in_sync"] == 1
            assert status["missing_plans"] == 1
            assert status["orphaned_plans"] == 1
            assert status["missing_plan_ids"] == ["CVE-2025-2222"]
            assert status["orphaned_plan_ids"] == ["CVE-2025-3333"]
            assert status["sync_percentage"] == 50.0

    def test_validate_synchronization_valid(self) -> None:
        """Test validation with valid synchronization state."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "registry.yml"
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir()

            # Create mock finding
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

            datastore = RemediationDatastore(registry_path)
            datastore.create_default_plan("CVE-2025-1234")

            synchronizer = self._create_synchronizer(datastore, reports_dir, temp_dir)

            # Mock current findings
            synchronizer._get_current_findings = lambda: findings

            errors = synchronizer.validate_synchronization()

            assert errors == []

    def test_validate_synchronization_invalid(self) -> None:
        """Test validation with invalid synchronization state."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "registry.yml"
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir()

            # Create mock finding
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

            datastore = RemediationDatastore(registry_path)
            # Don't create plan for the finding
            datastore.create_default_plan("CVE-2025-9999")  # Orphaned plan

            synchronizer = self._create_synchronizer(datastore, reports_dir, temp_dir)

            # Mock current findings
            synchronizer._get_current_findings = lambda: findings

            errors = synchronizer.validate_synchronization()

            assert len(errors) >= 2  # Missing plan + orphaned plan
            assert any("findings have no remediation plans" in error for error in errors)
            assert any(
                "auto-generated plans have no corresponding findings" in error for error in errors
            )

    def test_synchronize_findings_error_handling(self) -> None:
        """Test error handling during synchronization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "registry.yml"
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir()

            datastore = RemediationDatastore(registry_path)
            synchronizer = self._create_synchronizer(datastore, reports_dir, temp_dir)

            # Mock _get_current_findings to raise an exception
            def mock_get_findings() -> NoReturn:
                msg = "Test error"
                raise RuntimeError(msg)

            synchronizer._get_current_findings = mock_get_findings

            with pytest.raises(RuntimeError, match="Failed to synchronize findings"):
                synchronizer.synchronize_findings()

    def test_get_current_findings_error_handling(self) -> None:
        """Test error handling when extracting current findings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir()
            registry_path = Path(temp_dir) / "registry.yml"

            datastore = RemediationDatastore(registry_path)
            synchronizer = self._create_synchronizer(datastore, reports_dir, temp_dir)

            # Mock extract_all_findings to raise an exception
            with patch("security.synchronizer.extract_all_findings") as mock_extract:
                mock_extract.side_effect = RuntimeError("Test error")

                with pytest.raises(RuntimeError, match="Failed to extract current findings"):
                    synchronizer._get_current_findings()


class TestGetDefaultSynchronizer:
    """Test cases for get_default_synchronizer function."""

    def _create_synchronizer(
        self, datastore: RemediationDatastore, reports_dir: Path, temp_dir: str
    ) -> RemediationSynchronizer:
        """Helper to create synchronizer with proper historical manager."""
        historical_manager = HistoricalDataManager(
            history_dir=Path(temp_dir) / "history",
            reports_dir=reports_dir,
            archived_reports_dir=Path(temp_dir) / "archived",
        )
        return RemediationSynchronizer(datastore, reports_dir, historical_manager)

    def test_get_default_synchronizer(self) -> None:
        """Test getting default synchronizer instance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            synchronizer = get_default_synchronizer()

            assert isinstance(synchronizer, RemediationSynchronizer)
            assert isinstance(synchronizer.datastore, RemediationDatastore)

    def test_synchronize_findings_with_errors(self) -> None:
        """Test synchronization with some errors during processing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            registry_path = Path(temp_dir) / "registry.yml"
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir()

            # Create mock finding
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

            datastore = RemediationDatastore(registry_path)
            synchronizer = self._create_synchronizer(datastore, reports_dir, temp_dir)

            # Mock current findings
            synchronizer._get_current_findings = lambda: findings

            # Mock create_default_plan to raise an exception
            original_create = datastore.create_default_plan

            def mock_create_with_error(finding_id: str) -> RemediationPlan:
                if finding_id == "CVE-2025-1234":
                    msg = "Test error"
                    raise RuntimeError(msg)
                return original_create(finding_id)

            datastore.create_default_plan = mock_create_with_error

            with patch("builtins.print") as mock_print:
                stats = synchronizer.synchronize_findings()

            assert stats["added"] == 0
            assert stats["errors"] == 1
            mock_print.assert_called()

    def test_synchronize_findings_remove_with_errors(self) -> None:
        """Test synchronization with errors during removal."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            registry_path = Path(temp_dir) / "registry.yml"
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir()

            datastore = RemediationDatastore(registry_path)

            # Create existing plan
            datastore.create_default_plan("CVE-2025-1234")

            synchronizer = self._create_synchronizer(datastore, reports_dir, temp_dir)

            # Mock no current findings (finding resolved)
            synchronizer._get_current_findings = list

            # Mock delete_remediation_plan to raise an exception
            original_delete = datastore.delete_remediation_plan

            def mock_delete_with_error(finding_id: str) -> None:
                if finding_id == "CVE-2025-1234":
                    msg = "Test error"
                    raise RuntimeError(msg)
                return original_delete(finding_id)

            datastore.delete_remediation_plan = mock_delete_with_error

            with patch("builtins.print") as mock_print:
                stats = synchronizer.synchronize_findings()

            assert stats["removed"] == 0
            assert stats["errors"] == 1
            mock_print.assert_called()

    def test_resolve_conflicts_with_errors(self) -> None:
        """Test resolving conflicts with errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            registry_path = Path(temp_dir) / "registry.yml"
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir()

            datastore = RemediationDatastore(registry_path)
            synchronizer = self._create_synchronizer(datastore, reports_dir, temp_dir)

            # Mock current findings to raise an exception
            def mock_get_findings() -> NoReturn:
                msg = "Test error"
                raise RuntimeError(msg)

            synchronizer._get_current_findings = mock_get_findings

            with pytest.raises(RuntimeError, match="Failed to resolve conflicts"):
                synchronizer.resolve_conflicts(["CVE-2025-1234"])

    def test_get_synchronization_status_error_handling(self) -> None:
        """Test error handling in get_synchronization_status."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            registry_path = Path(temp_dir) / "registry.yml"
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir()

            datastore = RemediationDatastore(registry_path)
            synchronizer = self._create_synchronizer(datastore, reports_dir, temp_dir)

            # Mock _get_current_findings to raise an exception
            def mock_get_findings() -> NoReturn:
                msg = "Test error"
                raise RuntimeError(msg)

            synchronizer._get_current_findings = mock_get_findings

            with pytest.raises(RuntimeError, match="Failed to get synchronization status"):
                synchronizer.get_synchronization_status()

    def test_validate_synchronization_error_handling(self) -> None:
        """Test error handling in validate_synchronization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            registry_path = Path(temp_dir) / "registry.yml"
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir()

            datastore = RemediationDatastore(registry_path)
            synchronizer = self._create_synchronizer(datastore, reports_dir, temp_dir)

            # Mock get_synchronization_status to raise an exception
            def mock_get_status() -> NoReturn:
                msg = "Test error"
                raise RuntimeError(msg)

            synchronizer.get_synchronization_status = mock_get_status

            errors = synchronizer.validate_synchronization()

            assert len(errors) == 1
            assert "Validation failed: Test error" in errors[0]

    def test_resolve_conflicts_individual_errors(self) -> None:
        """Test resolving conflicts with individual finding errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            registry_path = Path(temp_dir) / "registry.yml"
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir()

            datastore = RemediationDatastore(registry_path)
            synchronizer = self._create_synchronizer(datastore, reports_dir, temp_dir)

            # Mock current findings (empty)
            synchronizer._get_current_findings = list

            # Mock get_remediation_plan to raise an exception for specific finding
            original_get = datastore.get_remediation_plan

            def mock_get_with_error(finding_id: str) -> RemediationPlan | None:
                if finding_id == "CVE-2025-ERROR":
                    msg = "Individual error"
                    raise RuntimeError(msg)
                return original_get(finding_id)

            datastore.get_remediation_plan = mock_get_with_error

            resolutions = synchronizer.resolve_conflicts(["CVE-2025-1234", "CVE-2025-ERROR"])

            assert resolutions["CVE-2025-1234"] == "no_conflict"
            assert "error: Individual error" in resolutions["CVE-2025-ERROR"]

    def test_resolve_conflicts_no_conflict_cases(self) -> None:
        """Test resolve_conflicts for no-conflict cases."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            registry_path = Path(temp_dir) / "registry.yml"
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir()

            # Create mock finding
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

            datastore = RemediationDatastore(registry_path)
            datastore.create_default_plan("CVE-2025-1234")

            synchronizer = self._create_synchronizer(datastore, reports_dir, temp_dir)

            # Mock current findings
            synchronizer._get_current_findings = lambda: findings

            resolutions = synchronizer.resolve_conflicts(["CVE-2025-1234", "CVE-2025-5555"])

            assert resolutions["CVE-2025-1234"] == "no_conflict"  # Finding exists, plan exists
            assert resolutions["CVE-2025-5555"] == "no_conflict"  # Finding doesn't exist, no plan

    def test_resolve_conflicts_remove_plan(self) -> None:
        """Test resolve_conflicts removing default plans."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            registry_path = Path(temp_dir) / "registry.yml"
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir()

            datastore = RemediationDatastore(registry_path)
            # Create default plan (not manually modified)
            datastore.create_default_plan("CVE-2025-1234")

            synchronizer = self._create_synchronizer(datastore, reports_dir, temp_dir)

            # Mock no current findings (finding resolved)
            synchronizer._get_current_findings = list

            resolutions = synchronizer.resolve_conflicts(["CVE-2025-1234"])

            assert resolutions["CVE-2025-1234"] == "removed_plan"

            # Verify plan was removed
            plan = datastore.get_remediation_plan("CVE-2025-1234")
            assert plan is None

    def test_is_manually_modified_edge_cases(self) -> None:
        """Test edge cases for manual modification detection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            registry_path = Path(temp_dir) / "registry.yml"

            datastore = RemediationDatastore(registry_path)
            synchronizer = RemediationSynchronizer(datastore)

            # Test plan with non-default status but default other fields
            plan1 = RemediationPlan(
                finding_id="CVE-2025-1234",
                status="in_progress",  # Non-default status
                planned_action="Under evaluation",
                assigned_to="security-team",
                notes="Newly discovered - assessment in progress",
                workaround="None identified",
                priority="medium",
                business_impact="Under assessment",
            )
            assert synchronizer._is_manually_modified(plan1)

            # Test plan with non-default priority
            plan2 = RemediationPlan(
                finding_id="CVE-2025-1234",
                status="new",
                planned_action="Under evaluation",
                assigned_to="security-team",
                notes="Newly discovered - assessment in progress",
                workaround="None identified",
                priority="high",  # Non-default priority
                business_impact="Under assessment",
            )
            assert synchronizer._is_manually_modified(plan2)

            # Test plan with target date set
            plan3 = RemediationPlan(
                finding_id="CVE-2025-1234",
                status="new",
                planned_action="Under evaluation",
                assigned_to="security-team",
                notes="Newly discovered - assessment in progress",
                workaround="None identified",
                priority="medium",
                business_impact="Under assessment",
                target_date=date(2025, 12, 31),  # Target date set
            )
            assert synchronizer._is_manually_modified(plan3)
