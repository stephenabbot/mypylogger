"""Unit tests for remediation datastore management.

This module tests the RemediationDatastore class and related functionality
for managing YAML-based remediation registry.
"""

from datetime import date
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

import pytest
import yaml

from security.models import RemediationPlan, create_default_remediation_plan
from security.remediation import RemediationDatastore, get_default_datastore


class TestRemediationDatastore:
    """Test cases for RemediationDatastore class."""

    def test_init_with_default_path(self) -> None:
        """Test initialization with default registry path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            datastore = RemediationDatastore()

            expected_path = Path("security/findings/remediation-plans.yml")
            assert datastore.registry_path == expected_path
            assert datastore.registry_path.exists()

    def test_init_with_custom_path(self) -> None:
        """Test initialization with custom registry path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_path = Path(temp_dir) / "custom-remediation.yml"

            datastore = RemediationDatastore(custom_path)

            assert datastore.registry_path == custom_path
            assert datastore.registry_path.exists()

    def test_create_empty_registry(self) -> None:
        """Test creation of empty registry structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"

            RemediationDatastore(registry_path)

            # Verify file was created
            assert registry_path.exists()

            # Verify structure
            with registry_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)

            assert "metadata" in data
            assert "findings" in data
            assert data["findings"] == {}
            assert "version" in data["metadata"]
            assert "created" in data["metadata"]

    def test_save_and_load_remediation_plan(self) -> None:
        """Test saving and loading a remediation plan."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"
            datastore = RemediationDatastore(registry_path)

            # Create test plan
            plan = RemediationPlan(
                finding_id="CVE-2025-1234",
                status="in_progress",
                planned_action="Upgrade package to latest version",
                assigned_to="dev-team",
                notes="Working on upgrade",
                workaround="Temporary mitigation applied",
                target_date=date(2025, 12, 31),
                priority="high",
                business_impact="Medium impact on operations",
            )

            # Save plan
            datastore.save_remediation_plan(plan)

            # Load plan
            loaded_plan = datastore.get_remediation_plan("CVE-2025-1234")

            assert loaded_plan is not None
            assert loaded_plan.finding_id == plan.finding_id
            assert loaded_plan.status == plan.status
            assert loaded_plan.planned_action == plan.planned_action
            assert loaded_plan.assigned_to == plan.assigned_to
            assert loaded_plan.notes == plan.notes
            assert loaded_plan.workaround == plan.workaround
            assert loaded_plan.target_date == plan.target_date
            assert loaded_plan.priority == plan.priority
            assert loaded_plan.business_impact == plan.business_impact

    def test_get_nonexistent_plan(self) -> None:
        """Test getting a plan that doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"
            datastore = RemediationDatastore(registry_path)

            result = datastore.get_remediation_plan("NONEXISTENT-ID")

            assert result is None

    def test_delete_remediation_plan(self) -> None:
        """Test deleting a remediation plan."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"
            datastore = RemediationDatastore(registry_path)

            # Create and save plan
            plan = create_default_remediation_plan("CVE-2025-1234")
            datastore.save_remediation_plan(plan)

            # Verify it exists
            assert datastore.get_remediation_plan("CVE-2025-1234") is not None

            # Delete it
            result = datastore.delete_remediation_plan("CVE-2025-1234")

            assert result is True
            assert datastore.get_remediation_plan("CVE-2025-1234") is None

    def test_delete_nonexistent_plan(self) -> None:
        """Test deleting a plan that doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"
            datastore = RemediationDatastore(registry_path)

            result = datastore.delete_remediation_plan("NONEXISTENT-ID")

            assert result is False

    def test_list_all_plans(self) -> None:
        """Test listing all remediation plans."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"
            datastore = RemediationDatastore(registry_path)

            # Create multiple plans
            plan1 = create_default_remediation_plan("CVE-2025-1111")
            plan2 = create_default_remediation_plan("CVE-2025-2222")
            plan3 = create_default_remediation_plan("GHSA-abcd-efgh-ijkl")

            # Save plans
            datastore.save_remediation_plan(plan1)
            datastore.save_remediation_plan(plan2)
            datastore.save_remediation_plan(plan3)

            # List all plans
            all_plans = datastore.list_all_plans()

            assert len(all_plans) == 3
            finding_ids = {plan.finding_id for plan in all_plans}
            assert finding_ids == {"CVE-2025-1111", "CVE-2025-2222", "GHSA-abcd-efgh-ijkl"}

    def test_create_default_plan(self) -> None:
        """Test creating a default remediation plan."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"
            datastore = RemediationDatastore(registry_path)

            # Create default plan
            plan = datastore.create_default_plan("CVE-2025-5555")

            assert plan.finding_id == "CVE-2025-5555"
            assert plan.status == "new"
            assert plan.planned_action == "Under evaluation"
            assert plan.assigned_to == "security-team"

            # Verify it was saved
            loaded_plan = datastore.get_remediation_plan("CVE-2025-5555")
            assert loaded_plan is not None
            assert loaded_plan.finding_id == plan.finding_id

    def test_create_default_plan_existing(self) -> None:
        """Test creating default plan when one already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"
            datastore = RemediationDatastore(registry_path)

            # Create and save existing plan
            existing_plan = RemediationPlan(
                finding_id="CVE-2025-6666",
                status="in_progress",
                planned_action="Custom action",
                assigned_to="custom-team",
                notes="Custom notes",
                workaround="Custom workaround",
            )
            datastore.save_remediation_plan(existing_plan)

            # Try to create default plan
            result_plan = datastore.create_default_plan("CVE-2025-6666")

            # Should return existing plan, not create new one
            assert result_plan.status == "in_progress"
            assert result_plan.planned_action == "Custom action"
            assert result_plan.assigned_to == "custom-team"

    def test_validate_registry_structure_valid(self) -> None:
        """Test validation of valid registry structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"
            datastore = RemediationDatastore(registry_path)

            # Add a valid plan
            plan = create_default_remediation_plan("CVE-2025-7777")
            datastore.save_remediation_plan(plan)

            # Validate
            errors = datastore.validate_registry_structure()

            assert errors == []

    def test_validate_registry_structure_invalid(self) -> None:
        """Test validation of invalid registry structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"

            # Create invalid registry manually
            invalid_data = {
                "findings": {
                    "CVE-2025-8888": {
                        "finding_id": "CVE-2025-8888",
                        "status": "new",
                        # Missing required fields
                    }
                }
            }

            with registry_path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(invalid_data, f)

            datastore = RemediationDatastore(registry_path)
            errors = datastore.validate_registry_structure()

            assert len(errors) > 0
            assert any("Missing fields" in error for error in errors)

    def test_registry_backup_on_save(self) -> None:
        """Test that registry creates backup before saving."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"
            datastore = RemediationDatastore(registry_path)

            # Save initial plan
            plan1 = create_default_remediation_plan("CVE-2025-1111")
            datastore.save_remediation_plan(plan1)

            # Save another plan (should create backup)
            plan2 = create_default_remediation_plan("CVE-2025-2222")
            datastore.save_remediation_plan(plan2)

            # Check backup exists
            backup_path = registry_path.with_suffix(".yml.backup")
            assert backup_path.exists()

    def test_error_handling_invalid_yaml(self) -> None:
        """Test error handling for invalid YAML file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"

            # Create invalid YAML
            with registry_path.open("w", encoding="utf-8") as f:
                f.write("invalid: yaml: content: [")

            datastore = RemediationDatastore(registry_path)

            with pytest.raises(RuntimeError, match="Invalid YAML"):
                datastore._load_registry()

    def test_error_handling_permission_denied(self) -> None:
        """Test error handling for permission denied."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create read-only directory
            readonly_dir = Path(temp_dir) / "readonly"
            readonly_dir.mkdir()
            readonly_dir.chmod(0o444)

            registry_path = readonly_dir / "test-registry.yml"

            with pytest.raises(RuntimeError, match="Failed to create"):
                RemediationDatastore(registry_path)

    def test_error_handling_save_permission_denied(self) -> None:
        """Test error handling for save permission denied."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"
            datastore = RemediationDatastore(registry_path)

            # Make directory read-only to prevent file access
            temp_dir_path = Path(temp_dir)
            temp_dir_path.chmod(0o444)

            plan = create_default_remediation_plan("CVE-2025-9999")

            with pytest.raises(RuntimeError, match="Failed to load registry"):
                datastore.save_remediation_plan(plan)

    def test_error_handling_load_permission_denied(self) -> None:
        """Test error handling for load permission denied."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"
            datastore = RemediationDatastore(registry_path)

            # Make file unreadable
            registry_path.chmod(0o000)

            with pytest.raises(RuntimeError, match="Failed to load"):
                datastore.get_remediation_plan("CVE-2025-9999")

    def test_load_registry_not_dict(self) -> None:
        """Test loading registry that's not a dictionary."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"

            # Create invalid registry (list instead of dict)
            with registry_path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(["not", "a", "dict"], f)

            datastore = RemediationDatastore(registry_path)

            with pytest.raises(RuntimeError, match="Registry file must contain a YAML dictionary"):
                datastore._load_registry()

    def test_list_all_plans_with_invalid_data(self) -> None:
        """Test listing plans when some have invalid data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"
            datastore = RemediationDatastore(registry_path)

            # Create valid plan
            valid_plan = create_default_remediation_plan("CVE-2025-1111")
            datastore.save_remediation_plan(valid_plan)

            # Manually add invalid plan data
            registry = datastore._load_registry()
            registry["findings"]["INVALID-ID"] = {
                "finding_id": "INVALID-ID",
                "status": "new",
                # Missing required fields
            }
            datastore._save_registry(registry)

            # Should return only valid plans and print warning
            with patch("builtins.print") as mock_print:
                plans = datastore.list_all_plans()

            assert len(plans) == 1
            assert plans[0].finding_id == "CVE-2025-1111"
            mock_print.assert_called()

    def test_validate_registry_missing_metadata(self) -> None:
        """Test validation when metadata is missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"

            # Create registry without metadata
            data = {"findings": {}}
            with registry_path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(data, f)

            # The _load_registry method automatically adds metadata if missing
            # So we need to test the validation directly on the loaded data
            datastore = RemediationDatastore(registry_path)

            # Manually create invalid registry for validation
            invalid_data = {"findings": {}}  # No metadata

            # Temporarily replace the loaded data
            original_load = datastore._load_registry
            datastore._load_registry = lambda: invalid_data

            errors = datastore.validate_registry_structure()

            # Restore original method
            datastore._load_registry = original_load

            assert any("Missing 'metadata'" in error for error in errors)

    def test_validate_registry_findings_not_dict(self) -> None:
        """Test validation when findings is not a dictionary."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"

            # Create registry with invalid findings
            data = {"metadata": {"version": "1.0"}, "findings": ["not", "a", "dict"]}
            with registry_path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(data, f)

            datastore = RemediationDatastore(registry_path)
            errors = datastore.validate_registry_structure()

            assert any("'findings' must be a dictionary" in error for error in errors)

    def test_validate_registry_plan_not_dict(self) -> None:
        """Test validation when plan data is not a dictionary."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"

            # Create registry with invalid plan data
            data = {"metadata": {"version": "1.0"}, "findings": {"CVE-2025-1234": "not a dict"}}
            with registry_path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(data, f)

            datastore = RemediationDatastore(registry_path)
            errors = datastore.validate_registry_structure()

            assert any(
                "Plan data for CVE-2025-1234 must be a dictionary" in error for error in errors
            )

    def test_validate_registry_inconsistent_finding_id(self) -> None:
        """Test validation when finding_id is inconsistent."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"

            # Create registry with inconsistent finding_id
            data = {
                "metadata": {"version": "1.0"},
                "findings": {
                    "CVE-2025-1234": {
                        "finding_id": "CVE-2025-5678",  # Different from key
                        "status": "new",
                        "planned_action": "test",
                        "assigned_to": "test",
                        "notes": "test",
                        "workaround": "test",
                        "created_date": "2025-01-01",
                        "updated_date": "2025-01-01",
                    }
                },
            }
            with registry_path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(data, f)

            datastore = RemediationDatastore(registry_path)
            errors = datastore.validate_registry_structure()

            assert any("Inconsistent finding_id in CVE-2025-1234" in error for error in errors)

    def test_dict_to_remediation_plan_with_none_target_date(self) -> None:
        """Test converting dict with None target_date to RemediationPlan."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"
            datastore = RemediationDatastore(registry_path)

            plan_data = {
                "finding_id": "CVE-2025-1234",
                "status": "new",
                "planned_action": "Test action",
                "assigned_to": "test-team",
                "notes": "Test notes",
                "workaround": "Test workaround",
                "target_date": None,
                "priority": "high",
                "business_impact": "high",
                "created_date": "2025-01-01",
                "updated_date": "2025-01-01",
            }

            plan = datastore._dict_to_remediation_plan(plan_data)

            assert plan.target_date is None
            assert plan.priority == "high"
            assert plan.business_impact == "high"

    def test_error_handling_create_empty_registry_permission_denied(self) -> None:
        """Test error handling when creating empty registry fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create read-only directory
            readonly_dir = Path(temp_dir) / "readonly"
            readonly_dir.mkdir()
            readonly_dir.chmod(0o444)

            registry_path = readonly_dir / "subdir" / "test-registry.yml"

            with pytest.raises(RuntimeError, match="Failed to create remediation registry"):
                RemediationDatastore(registry_path)

    def test_error_handling_create_empty_registry_write_fail(self) -> None:
        """Test error handling when writing empty registry fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"

            # Create the file first
            registry_path.touch()

            # Make it read-only
            registry_path.chmod(0o444)

            def create_empty_registry_fail() -> None:
                datastore = RemediationDatastore.__new__(RemediationDatastore)
                datastore.registry_path = registry_path
                datastore._create_empty_registry()

            with pytest.raises(RuntimeError, match="Failed to create empty registry"):
                create_empty_registry_fail()

    def test_remediation_plan_to_dict_with_none_target_date(self) -> None:
        """Test converting RemediationPlan with None target_date to dict."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"
            datastore = RemediationDatastore(registry_path)

            plan = RemediationPlan(
                finding_id="CVE-2025-1234",
                status="new",
                planned_action="Test action",
                assigned_to="test-team",
                notes="Test notes",
                workaround="Test workaround",
                target_date=None,
                priority="high",
                business_impact="high",
            )

            plan_dict = datastore._remediation_plan_to_dict(plan)

            assert plan_dict["target_date"] is None
            assert plan_dict["priority"] == "high"
            assert plan_dict["business_impact"] == "high"

    def test_dict_to_remediation_plan_missing_optional_fields(self) -> None:
        """Test converting dict with missing optional fields to RemediationPlan."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"
            datastore = RemediationDatastore(registry_path)

            # Missing priority and business_impact (should use defaults)
            plan_data = {
                "finding_id": "CVE-2025-1234",
                "status": "new",
                "planned_action": "Test action",
                "assigned_to": "test-team",
                "notes": "Test notes",
                "workaround": "Test workaround",
                "target_date": None,
                "created_date": "2025-01-01",
                "updated_date": "2025-01-01",
            }

            plan = datastore._dict_to_remediation_plan(plan_data)

            assert plan.priority == "medium"  # Default value
            assert plan.business_impact == "unknown"  # Default value

    def test_dict_to_remediation_plan_with_target_date(self) -> None:
        """Test converting dict with valid target_date to RemediationPlan."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"
            datastore = RemediationDatastore(registry_path)

            plan_data = {
                "finding_id": "CVE-2025-1234",
                "status": "new",
                "planned_action": "Test action",
                "assigned_to": "test-team",
                "notes": "Test notes",
                "workaround": "Test workaround",
                "target_date": "2025-12-31",
                "priority": "high",
                "business_impact": "high",
                "created_date": "2025-01-01",
                "updated_date": "2025-01-01",
            }

            plan = datastore._dict_to_remediation_plan(plan_data)

            assert plan.target_date == date(2025, 12, 31)

    def test_load_registry_missing_findings_and_metadata(self) -> None:
        """Test loading registry that's missing both findings and metadata."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test-registry.yml"

            # Create registry with neither findings nor metadata
            data = {"other_key": "value"}
            with registry_path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(data, f)

            datastore = RemediationDatastore(registry_path)
            loaded_data = datastore._load_registry()

            # Should have added both findings and metadata
            assert "findings" in loaded_data
            assert "metadata" in loaded_data
            assert loaded_data["findings"] == {}
            assert "version" in loaded_data["metadata"]

    def test_save_registry_without_existing_backup(self) -> None:
        """Test saving registry when no existing file exists (no backup needed)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "new-registry.yml"

            # Create datastore but delete the file to test save without existing file
            datastore = RemediationDatastore(registry_path)
            registry_path.unlink()  # Remove the file

            # Now save should work without creating backup
            data = {
                "metadata": {"version": "1.0"},
                "findings": {"CVE-2025-1234": {"finding_id": "CVE-2025-1234", "status": "new"}},
            }

            datastore._save_registry(data)

            # Verify file was created
            assert registry_path.exists()

            # Verify no backup was created
            backup_path = registry_path.with_suffix(".yml.backup")
            assert not backup_path.exists()


class TestGetDefaultDatastore:
    """Test cases for get_default_datastore function."""

    def test_get_default_datastore(self) -> None:
        """Test getting default datastore instance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            datastore = get_default_datastore()

            assert isinstance(datastore, RemediationDatastore)
            expected_path = Path("security/findings/remediation-plans.yml")
            assert datastore.registry_path == expected_path
