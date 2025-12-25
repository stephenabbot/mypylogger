"""Remediation synchronization logic for security findings.

This module provides functionality for automatically synchronizing remediation plans
with security findings, ensuring 1:1 coupling and preserving manual edits.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
from typing import TYPE_CHECKING

from security.parsers import extract_all_findings

if TYPE_CHECKING:
    from security.history import HistoricalDataManager
    from security.models import SecurityFinding
    from security.remediation import RemediationDatastore


class RemediationSynchronizer:
    """Manages synchronization between security findings and remediation plans."""

    def __init__(
        self,
        datastore: RemediationDatastore | None = None,
        reports_dir: str | Path | None = None,
        historical_manager: HistoricalDataManager | None = None,
    ) -> None:
        """Initialize the remediation synchronizer.

        Args:
            datastore: RemediationDatastore instance. If None, uses default.
            reports_dir: Directory containing security scan reports.
                        Defaults to security/reports/latest/
            historical_manager: Historical data manager. If None, uses default.
        """
        from security.history import get_default_historical_manager
        from security.remediation import get_default_datastore

        self.datastore = datastore or get_default_datastore()
        self.historical_manager = historical_manager or get_default_historical_manager()

        if reports_dir is None:
            reports_dir = Path("security/reports/latest")
        self.reports_dir = Path(reports_dir)

    def synchronize_findings(self, preserve_manual_edits: bool = True) -> dict[str, int]:
        """Synchronize remediation plans with current security findings.

        Args:
            preserve_manual_edits: Whether to preserve manual edits to remediation plans

        Returns:
            Dictionary with synchronization statistics:
            - added: Number of new remediation plans created
            - removed: Number of remediation plans removed
            - preserved: Number of existing plans preserved
            - errors: Number of errors encountered

        Raises:
            RuntimeError: If synchronization fails
        """
        try:
            # Get current findings from scan reports
            current_findings = self._get_current_findings()
            current_finding_ids = {finding.finding_id for finding in current_findings}

            # Get existing remediation plans
            existing_plans = self.datastore.list_all_plans()
            existing_plan_ids = {plan.finding_id for plan in existing_plans}

            # Calculate changes needed
            new_finding_ids = current_finding_ids - existing_plan_ids
            obsolete_plan_ids = existing_plan_ids - current_finding_ids
            preserved_plan_ids = existing_plan_ids & current_finding_ids

            stats = {
                "added": 0,
                "removed": 0,
                "preserved": len(preserved_plan_ids),
                "errors": 0,
            }

            # Create remediation plans for new findings
            for finding_id in new_finding_ids:
                try:
                    # Find the corresponding finding for historical tracking
                    finding = next(
                        (f for f in current_findings if f.finding_id == finding_id), None
                    )

                    # Record finding discovery
                    if finding:
                        self.historical_manager.record_finding_discovered(finding)

                    # Create remediation plan
                    plan = self.datastore.create_default_plan(finding_id)
                    if plan:
                        self.historical_manager.record_remediation_created(plan)

                    stats["added"] += 1
                except Exception as e:
                    print(
                        f"Warning: Failed to create plan for {finding_id}: {e}", file=os.sys.stderr
                    )
                    stats["errors"] += 1

            # Remove remediation plans for resolved findings
            for finding_id in obsolete_plan_ids:
                try:
                    # Record finding resolution
                    self.historical_manager.record_finding_resolved(finding_id, "scanner")

                    if preserve_manual_edits:
                        # Check if plan has been manually modified
                        plan = self.datastore.get_remediation_plan(finding_id)
                        if plan and self._is_manually_modified(plan):
                            # Keep the plan but mark it as resolved
                            old_status = plan.status
                            plan.status = "completed"
                            plan.notes += f"\n[{datetime.now(timezone.utc).date()}] Finding resolved - auto-marked as completed"
                            self.datastore.save_remediation_plan(plan)

                            # Record status change
                            self.historical_manager.record_remediation_status_change(
                                finding_id,
                                old_status,
                                "completed",
                                "system",
                                "Finding resolved - auto-marked as completed",
                            )
                            continue

                    # Remove the plan
                    if self.datastore.delete_remediation_plan(finding_id):
                        stats["removed"] += 1
                except Exception as e:
                    print(
                        f"Warning: Failed to remove plan for {finding_id}: {e}", file=os.sys.stderr
                    )
                    stats["errors"] += 1

            return stats

        except Exception as e:
            msg = f"Failed to synchronize findings: {e}"
            raise RuntimeError(msg) from e

    def _get_current_findings(self) -> list[SecurityFinding]:
        """Get current security findings from scan reports.

        Returns:
            List of SecurityFinding objects from current scan reports

        Raises:
            RuntimeError: If findings cannot be extracted
        """
        try:
            if not self.reports_dir.exists():
                return []

            return extract_all_findings(self.reports_dir)

        except Exception as e:
            msg = f"Failed to extract current findings: {e}"
            raise RuntimeError(msg) from e

    def _is_manually_modified(self, plan) -> bool:
        """Check if a remediation plan has been manually modified.

        Args:
            plan: RemediationPlan to check

        Returns:
            True if plan appears to have manual modifications
        """
        # Check for indicators of manual modification
        default_indicators = {
            "Under evaluation",
            "Newly discovered - assessment in progress",
            "None identified",
        }

        # If any of the key fields have been changed from defaults, consider it modified
        if (
            plan.planned_action not in default_indicators
            and plan.notes not in default_indicators
            and plan.workaround not in default_indicators
        ):
            return True

        # Check if status has been changed from default
        if plan.status not in ("new", "completed"):
            return True

        # Check if priority or business impact have been set
        if plan.priority != "medium" or plan.business_impact != "Under assessment":
            return True

        # Check if target date has been set
        return plan.target_date is not None

    def resolve_conflicts(self, finding_ids: list[str]) -> dict[str, str]:
        """Resolve conflicts for specific findings.

        Args:
            finding_ids: List of finding IDs to resolve conflicts for

        Returns:
            Dictionary mapping finding_id to resolution action taken

        Raises:
            RuntimeError: If conflict resolution fails
        """
        try:
            resolutions = {}
            current_findings = self._get_current_findings()
            current_finding_ids = {finding.finding_id for finding in current_findings}

            for finding_id in finding_ids:
                try:
                    existing_plan = self.datastore.get_remediation_plan(finding_id)

                    if finding_id in current_finding_ids:
                        if existing_plan is None:
                            # Create new plan for existing finding
                            self.datastore.create_default_plan(finding_id)
                            resolutions[finding_id] = "created_new_plan"
                        else:
                            # Finding exists and plan exists - no conflict
                            resolutions[finding_id] = "no_conflict"
                    elif existing_plan is not None:
                        # Finding resolved but plan exists
                        if self._is_manually_modified(existing_plan):
                            # Mark as completed but keep plan
                            existing_plan.status = "completed"
                            existing_plan.notes += f"\n[{datetime.now(timezone.utc).date()}] Finding resolved - marked as completed"
                            self.datastore.save_remediation_plan(existing_plan)
                            resolutions[finding_id] = "marked_completed"
                        else:
                            # Remove default plan
                            self.datastore.delete_remediation_plan(finding_id)
                            resolutions[finding_id] = "removed_plan"
                    else:
                        # Finding resolved and no plan - no conflict
                        resolutions[finding_id] = "no_conflict"

                except Exception as e:
                    resolutions[finding_id] = f"error: {e}"

            return resolutions

        except Exception as e:
            msg = f"Failed to resolve conflicts: {e}"
            raise RuntimeError(msg) from e

    def get_synchronization_status(self) -> dict[str, any]:
        """Get current synchronization status between findings and plans.

        Returns:
            Dictionary with synchronization status information

        Raises:
            RuntimeError: If status cannot be determined
        """
        try:
            current_findings = self._get_current_findings()
            current_finding_ids = {finding.finding_id for finding in current_findings}

            existing_plans = self.datastore.list_all_plans()
            existing_plan_ids = {plan.finding_id for plan in existing_plans}

            # Calculate synchronization metrics
            in_sync_ids = current_finding_ids & existing_plan_ids
            missing_plans = current_finding_ids - existing_plan_ids
            orphaned_plans = existing_plan_ids - current_finding_ids

            # Analyze orphaned plans
            manually_modified_orphans = []
            auto_generated_orphans = []

            for finding_id in orphaned_plans:
                plan = self.datastore.get_remediation_plan(finding_id)
                if plan and self._is_manually_modified(plan):
                    manually_modified_orphans.append(finding_id)
                else:
                    auto_generated_orphans.append(finding_id)

            return {
                "total_findings": len(current_findings),
                "total_plans": len(existing_plans),
                "in_sync": len(in_sync_ids),
                "missing_plans": len(missing_plans),
                "orphaned_plans": len(orphaned_plans),
                "manually_modified_orphans": len(manually_modified_orphans),
                "auto_generated_orphans": len(auto_generated_orphans),
                "sync_percentage": (
                    len(in_sync_ids) / len(current_finding_ids) * 100
                    if current_finding_ids
                    else 100.0
                ),
                "missing_plan_ids": list(missing_plans),
                "orphaned_plan_ids": list(orphaned_plans),
                "manually_modified_orphan_ids": manually_modified_orphans,
                "auto_generated_orphan_ids": auto_generated_orphans,
            }

        except Exception as e:
            msg = f"Failed to get synchronization status: {e}"
            raise RuntimeError(msg) from e

    def validate_synchronization(self) -> list[str]:
        """Validate the current synchronization state.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        try:
            status = self.get_synchronization_status()

            # Check for missing plans
            if status["missing_plans"] > 0:
                errors.append(
                    f"{status['missing_plans']} findings have no remediation plans: "
                    f"{status['missing_plan_ids']}"
                )

            # Check for auto-generated orphaned plans
            if status["auto_generated_orphans"] > 0:
                errors.append(
                    f"{status['auto_generated_orphans']} auto-generated plans have no corresponding findings: "
                    f"{status['auto_generated_orphan_ids']}"
                )

            # Validate registry structure
            registry_errors = self.datastore.validate_registry_structure()
            errors.extend(registry_errors)

        except Exception as e:
            errors.append(f"Validation failed: {e}")

        return errors


def get_default_synchronizer() -> RemediationSynchronizer:
    """Get the default remediation synchronizer instance.

    Returns:
        RemediationSynchronizer configured with default settings
    """
    return RemediationSynchronizer()
