"""Remediation datastore management for security findings.

This module provides functionality for managing the YAML-based remediation registry,
including automatic synchronization between findings and remediation plans.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import os
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

from security.models import RemediationPlan, create_default_remediation_plan


class RemediationDatastore:
    """Manages the YAML-based remediation registry with automatic synchronization."""

    def __init__(self, registry_path: str | Path | None = None) -> None:
        """Initialize the remediation datastore.

        Args:
            registry_path: Path to the remediation registry YAML file.
                          Defaults to security/findings/remediation-plans.yml
        """
        if yaml is None:
            msg = (
                "PyYAML is required for the security module. "
                "Install it with: pip install 'mypylogger[security]' or pip install PyYAML"
            )
            raise ImportError(msg)

        if registry_path is None:
            registry_path = Path("security/findings/remediation-plans.yml")

        self.registry_path = Path(registry_path)
        self._ensure_registry_exists()

    def _ensure_registry_exists(self) -> None:
        """Ensure the remediation registry file and directory exist."""
        try:
            # Create parent directories if they don't exist
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)

            # Create empty registry if it doesn't exist
            if not self.registry_path.exists():
                self._create_empty_registry()
        except (OSError, PermissionError) as e:
            msg = f"Failed to create remediation registry at {self.registry_path}: {e}"
            raise RuntimeError(msg) from e

    def _create_empty_registry(self) -> None:
        """Create an empty remediation registry with proper structure."""
        empty_registry = {
            "metadata": {
                "version": "1.0",
                "created": datetime.now(timezone.utc).isoformat(),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            },
            "findings": {},
        }

        try:
            with open(self.registry_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(empty_registry, f, default_flow_style=False, sort_keys=False)
        except (OSError, PermissionError) as e:
            msg = f"Failed to create empty registry: {e}"
            raise RuntimeError(msg) from e

    def _load_registry(self) -> dict[str, Any]:
        """Load the remediation registry from YAML file.

        Returns:
            Dictionary containing the registry data

        Raises:
            RuntimeError: If registry cannot be loaded or is invalid
        """
        try:
            with open(self.registry_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                msg = "Registry file must contain a YAML dictionary"
                raise RuntimeError(msg)

            # Ensure required structure exists
            if "findings" not in data:
                data["findings"] = {}
            if "metadata" not in data:
                data["metadata"] = {
                    "version": "1.0",
                    "created": datetime.now(timezone.utc).isoformat(),
                }

            return data

        except yaml.YAMLError as e:
            msg = f"Invalid YAML in registry file: {e}"
            raise RuntimeError(msg) from e
        except (OSError, PermissionError) as e:
            msg = f"Failed to load registry: {e}"
            raise RuntimeError(msg) from e

    def _save_registry(self, data: dict[str, Any]) -> None:
        """Save the remediation registry to YAML file.

        Args:
            data: Registry data to save

        Raises:
            RuntimeError: If registry cannot be saved
        """
        try:
            # Update metadata
            data["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()

            # Create backup of existing file
            if self.registry_path.exists():
                backup_path = self.registry_path.with_suffix(".yml.backup")
                self.registry_path.rename(backup_path)

            # Write new data
            with open(self.registry_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

        except (OSError, PermissionError) as e:
            msg = f"Failed to save registry: {e}"
            raise RuntimeError(msg) from e

    def get_remediation_plan(self, finding_id: str) -> RemediationPlan | None:
        """Get remediation plan for a specific finding.

        Args:
            finding_id: Unique identifier for the security finding

        Returns:
            RemediationPlan if found, None otherwise

        Raises:
            RuntimeError: If registry cannot be loaded
        """
        registry = self._load_registry()
        finding_data = registry["findings"].get(finding_id)

        if finding_data is None:
            return None

        return self._dict_to_remediation_plan(finding_data)

    def save_remediation_plan(self, plan: RemediationPlan) -> None:
        """Save or update a remediation plan in the registry.

        Args:
            plan: RemediationPlan to save

        Raises:
            RuntimeError: If registry cannot be loaded or saved
        """
        registry = self._load_registry()

        # Convert plan to dictionary format
        plan_dict = self._remediation_plan_to_dict(plan)

        # Update registry
        registry["findings"][plan.finding_id] = plan_dict

        # Save registry
        self._save_registry(registry)

    def delete_remediation_plan(self, finding_id: str) -> bool:
        """Delete a remediation plan from the registry.

        Args:
            finding_id: Unique identifier for the security finding

        Returns:
            True if plan was deleted, False if it didn't exist

        Raises:
            RuntimeError: If registry cannot be loaded or saved
        """
        registry = self._load_registry()

        if finding_id not in registry["findings"]:
            return False

        del registry["findings"][finding_id]
        self._save_registry(registry)
        return True

    def list_all_plans(self) -> list[RemediationPlan]:
        """Get all remediation plans from the registry.

        Returns:
            List of all RemediationPlan objects

        Raises:
            RuntimeError: If registry cannot be loaded
        """
        registry = self._load_registry()
        plans = []

        for finding_id, plan_data in registry["findings"].items():
            try:
                plan = self._dict_to_remediation_plan(plan_data)
                plans.append(plan)
            except (ValueError, KeyError) as e:
                # Log warning but continue with other plans
                print(f"Warning: Invalid plan data for {finding_id}: {e}", file=os.sys.stderr)
                continue

        return plans

    def create_default_plan(self, finding_id: str) -> RemediationPlan:
        """Create and save a default remediation plan for a new finding.

        Args:
            finding_id: Unique identifier for the security finding

        Returns:
            Created RemediationPlan

        Raises:
            RuntimeError: If registry cannot be loaded or saved
        """
        # Check if plan already exists
        existing_plan = self.get_remediation_plan(finding_id)
        if existing_plan is not None:
            return existing_plan

        # Create new default plan
        plan = create_default_remediation_plan(finding_id)

        # Save to registry
        self.save_remediation_plan(plan)

        return plan

    def validate_registry_structure(self) -> list[str]:
        """Validate the structure and content of the remediation registry.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        try:
            registry = self._load_registry()
        except RuntimeError as e:
            return [f"Failed to load registry: {e}"]

        # Check required top-level keys
        if "findings" not in registry:
            errors.append("Missing 'findings' key in registry")

        if "metadata" not in registry:
            errors.append("Missing 'metadata' key in registry")

        # Validate each finding entry
        findings = registry.get("findings", {})
        if not isinstance(findings, dict):
            errors.append("'findings' must be a dictionary")
            return errors

        for finding_id, plan_data in findings.items():
            if not isinstance(plan_data, dict):
                errors.append(f"Plan data for {finding_id} must be a dictionary")
                continue

            # Validate required fields
            required_fields = {
                "finding_id",
                "status",
                "planned_action",
                "assigned_to",
                "notes",
                "workaround",
                "created_date",
                "updated_date",
            }

            missing_fields = required_fields - set(plan_data.keys())
            if missing_fields:
                errors.append(f"Missing fields in {finding_id}: {missing_fields}")

            # Validate finding_id consistency
            if plan_data.get("finding_id") != finding_id:
                errors.append(f"Inconsistent finding_id in {finding_id}")

        return errors

    def _dict_to_remediation_plan(self, data: dict[str, Any]) -> RemediationPlan:
        """Convert dictionary data to RemediationPlan object.

        Args:
            data: Dictionary containing plan data

        Returns:
            RemediationPlan object

        Raises:
            ValueError: If data is invalid
            KeyError: If required fields are missing
        """
        # Parse dates
        target_date = None
        if data.get("target_date"):
            target_date = date.fromisoformat(data["target_date"])

        created_date = date.fromisoformat(data["created_date"])
        updated_date = date.fromisoformat(data["updated_date"])

        return RemediationPlan(
            finding_id=data["finding_id"],
            status=data["status"],
            planned_action=data["planned_action"],
            assigned_to=data["assigned_to"],
            notes=data["notes"],
            workaround=data["workaround"],
            target_date=target_date,
            priority=data.get("priority", "medium"),
            business_impact=data.get("business_impact", "unknown"),
            created_date=created_date,
            updated_date=updated_date,
        )

    def _remediation_plan_to_dict(self, plan: RemediationPlan) -> dict[str, Any]:
        """Convert RemediationPlan object to dictionary format.

        Args:
            plan: RemediationPlan to convert

        Returns:
            Dictionary representation of the plan
        """
        return {
            "finding_id": plan.finding_id,
            "status": plan.status,
            "planned_action": plan.planned_action,
            "assigned_to": plan.assigned_to,
            "notes": plan.notes,
            "workaround": plan.workaround,
            "target_date": plan.target_date.isoformat() if plan.target_date else None,
            "priority": plan.priority,
            "business_impact": plan.business_impact,
            "created_date": plan.created_date.isoformat(),
            "updated_date": plan.updated_date.isoformat(),
        }


def get_default_datastore() -> RemediationDatastore:
    """Get the default remediation datastore instance.

    Returns:
        RemediationDatastore configured with default path
    """
    return RemediationDatastore()
