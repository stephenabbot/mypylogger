#!/usr/bin/env python3
"""Core automation engine for security findings management.

This script provides complete automation workflow for processing security scanner
outputs, synchronizing remediation plans, and generating findings documents.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

# Add security module to path for imports
security_dir = Path(__file__).parent.parent
sys.path.insert(0, str(security_dir))
sys.path.insert(0, str(security_dir.parent))  # Add project root for security module

# Add scripts directory to path for YAML validation
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from security.generator import FindingsDocumentGenerator
from security.history import HistoricalDataManager, get_default_historical_manager
from security.parsers import ScannerParseError, extract_all_findings
from security.remediation import RemediationDatastore, get_default_datastore
from security.synchronizer import RemediationSynchronizer


class AutomationEngine:
    """Core automation engine for security findings management."""

    def __init__(
        self,
        reports_dir: Path | None = None,
        findings_file: Path | None = None,
        datastore: RemediationDatastore | None = None,
        historical_manager: HistoricalDataManager | None = None,
        verbose: bool = False,
        yaml_safe: bool = False,
        reduced_mode: bool = False,
        degraded_mode: bool = False,
        minimal_mode: bool = False,
        with_monitoring: bool = False,
    ) -> None:
        """Initialize the automation engine.

        Args:
            reports_dir: Directory containing security scan reports
            findings_file: Output file for findings document
            datastore: Remediation datastore instance
            historical_manager: Historical data manager instance
            verbose: Enable verbose logging
            yaml_safe: Enable YAML validation and graceful degradation
            reduced_mode: Enable reduced functionality mode
            degraded_mode: Enable degraded functionality mode
            minimal_mode: Enable minimal functionality mode
            with_monitoring: Enable monitoring integration
        """
        self.reports_dir = reports_dir or Path("security/reports/latest")
        self.findings_file = findings_file or Path("security/findings/SECURITY_FINDINGS.md")
        self.datastore = datastore or get_default_datastore()
        self.historical_manager = historical_manager or get_default_historical_manager()
        self.verbose = verbose
        self.yaml_safe = yaml_safe
        self.reduced_mode = reduced_mode
        self.degraded_mode = degraded_mode
        self.minimal_mode = minimal_mode
        self.with_monitoring = with_monitoring
        self.yaml_validation_results = None
        self.operational_mode = self._determine_operational_mode()

        # Initialize components with error handling
        try:
            self.synchronizer = RemediationSynchronizer(
                self.datastore, self.reports_dir, self.historical_manager
            )
            self.generator = FindingsDocumentGenerator(
                self.datastore, self.reports_dir, self.findings_file
            )
        except Exception as e:
            if self.yaml_safe:
                self._log(f"WARNING: Component initialization failed, using fallback: {e}")
                self.synchronizer = None
                self.generator = None
            else:
                raise

    def run_complete_workflow(self) -> dict[str, any]:
        """Run the complete automation workflow with YAML validation and error handling.

        Returns:
            Dictionary with workflow execution results and statistics

        Raises:
            RuntimeError: If workflow execution fails and cannot be recovered
        """
        try:
            self._log(
                f"Starting security findings automation workflow in {self.operational_mode} mode..."
            )

            workflow_results = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operational_mode": self.operational_mode,
                "reports_processed": 0,
                "findings_extracted": 0,
                "synchronization_stats": {},
                "document_generated": False,
                "archive_created": False,
                "yaml_validation_status": "not_performed",
                "yaml_validation_errors": [],
                "yaml_validation_warnings": [],
                "fallback_actions": [],
                "monitoring_alerts": [],
                "errors": [],
                "warnings": [],
            }

            # Step 0: YAML validation and error handling (if enabled)
            if self.yaml_safe:
                self._log("Step 0: Validating security YAML files with error handling...")
                yaml_result = self._validate_security_yaml_files_with_error_handling()
                workflow_results.update(yaml_result)

            # Step 1: Process scanner outputs with fallback handling
            self._log("Step 1: Processing scanner outputs with fallback handling...")
            findings_result = self._process_scanner_outputs_with_fallback()
            workflow_results.update(findings_result)

            # Step 2: Synchronize remediation plans with error recovery
            if self.operational_mode not in ["emergency", "minimal"]:
                self._log("Step 2: Synchronizing remediation plans with error recovery...")
                sync_result = self._synchronize_remediation_plans_with_recovery()
                workflow_results["synchronization_stats"] = sync_result
            else:
                self._log("Step 2: Skipping synchronization in emergency/minimal mode")
                workflow_results["synchronization_stats"] = {
                    "skipped": True,
                    "reason": "emergency_mode",
                }

            # Step 3: Generate findings document with fallback
            self._log("Step 3: Generating findings document with fallback support...")
            doc_result = self._generate_findings_document_with_fallback()
            workflow_results["document_generated"] = doc_result

            # Step 4: Archive scan results (if possible)
            if self.operational_mode != "emergency":
                self._log("Step 4: Archiving scan results...")
                archive_result = self._archive_scan_results_safely()
                workflow_results["archive_created"] = archive_result
            else:
                self._log("Step 4: Skipping archival in emergency mode")
                workflow_results["archive_created"] = False

            # Step 5: Validate results with error tolerance
            self._log("Step 5: Validating results with error tolerance...")
            validation_result = self._validate_workflow_results_with_tolerance()
            workflow_results["validation_errors"] = validation_result

            # Step 6: Generate monitoring alerts if enabled
            if self.with_monitoring:
                self._log("Step 6: Generating monitoring alerts...")
                monitoring_result = self._generate_monitoring_alerts(workflow_results)
                workflow_results["monitoring_alerts"] = monitoring_result

            self._log(f"Automation workflow completed in {self.operational_mode} mode!")
            return workflow_results

        except Exception as e:
            error_msg = f"Automation workflow failed: {e}"
            self._log(f"ERROR: {error_msg}")

            # In YAML-safe mode, try to create emergency fallback
            if self.yaml_safe:
                try:
                    self._log("Attempting emergency fallback due to workflow failure...")
                    emergency_result = self._create_emergency_fallback()
                    return {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "operational_mode": "emergency_fallback",
                        "emergency_fallback": emergency_result,
                        "original_error": error_msg,
                        "workflow_status": "failed_with_fallback",
                    }
                except Exception as fallback_error:
                    self._log(f"ERROR: Emergency fallback also failed: {fallback_error}")

            raise RuntimeError(error_msg) from e

    def _process_scanner_outputs(self) -> dict[str, any]:
        """Process security scanner outputs and extract findings.

        Returns:
            Dictionary with processing results
        """
        try:
            if not self.reports_dir.exists():
                self._log(f"WARNING: Reports directory not found: {self.reports_dir}")
                return {
                    "reports_processed": 0,
                    "findings_extracted": 0,
                    "warnings": [f"Reports directory not found: {self.reports_dir}"],
                }

            # Check for expected scanner output files
            expected_files = {
                "pip-audit.json": "pip-audit",
                "bandit.json": "bandit",
                "secrets-scan.json": "secrets",
            }

            reports_found = []
            for filename, scanner_type in expected_files.items():
                file_path = self.reports_dir / filename
                if file_path.exists():
                    reports_found.append((file_path, scanner_type))
                    self._log(f"Found {scanner_type} report: {file_path}")

            if not reports_found:
                self._log("WARNING: No scanner output files found")
                return {
                    "reports_processed": 0,
                    "findings_extracted": 0,
                    "warnings": ["No scanner output files found"],
                }

            # Extract findings from all available reports
            try:
                all_findings = extract_all_findings(self.reports_dir)
                self._log(
                    f"Extracted {len(all_findings)} findings from {len(reports_found)} reports"
                )

                return {
                    "reports_processed": len(reports_found),
                    "findings_extracted": len(all_findings),
                    "scanner_types": [scanner_type for _, scanner_type in reports_found],
                }

            except ScannerParseError as e:
                error_msg = f"Failed to parse scanner outputs: {e}"
                self._log(f"ERROR: {error_msg}")

                # In YAML-safe mode, provide fallback behavior
                if self.yaml_safe:
                    self._log("YAML-safe mode: Attempting to continue with available data")
                    return {
                        "reports_processed": len(reports_found),
                        "findings_extracted": 0,
                        "warnings": [f"Scanner parsing failed but continuing: {error_msg}"],
                    }
                return {
                    "reports_processed": 0,
                    "findings_extracted": 0,
                    "errors": [error_msg],
                }

        except Exception as e:
            error_msg = f"Failed to process scanner outputs: {e}"
            self._log(f"ERROR: {error_msg}")
            raise RuntimeError(error_msg) from e

    def _synchronize_remediation_plans(self) -> dict[str, any]:
        """Synchronize remediation plans with current findings.

        Returns:
            Dictionary with synchronization statistics
        """
        try:
            # Check if we're in degraded mode due to YAML issues
            if self.yaml_safe and self.yaml_validation_results:
                degradation_level = self.yaml_validation_results.get("degradation_level")
                if degradation_level and degradation_level.value in ["minimal", "emergency"]:
                    self._log(
                        "WARNING: Operating in degraded mode - synchronization may be limited"
                    )

            # Get synchronization status before changes
            try:
                status_before = self.synchronizer.get_synchronization_status()
                self._log(
                    f"Before sync: {status_before['total_findings']} findings, "
                    f"{status_before['total_plans']} plans, "
                    f"{status_before['sync_percentage']:.1f}% in sync"
                )
            except Exception as e:
                if self.yaml_safe:
                    self._log(f"WARNING: Could not get sync status (YAML issues): {e}")
                    status_before = {"total_findings": 0, "total_plans": 0, "sync_percentage": 0.0}
                else:
                    raise

            # Perform synchronization
            try:
                sync_stats = self.synchronizer.synchronize_findings(preserve_manual_edits=True)
            except Exception as e:
                if self.yaml_safe:
                    self._log(f"WARNING: Synchronization failed (YAML issues): {e}")
                    sync_stats = {"added": 0, "removed": 0, "preserved": 0, "errors": [str(e)]}
                else:
                    raise

            # Get status after synchronization
            try:
                status_after = self.synchronizer.get_synchronization_status()
                self._log(
                    f"After sync: {status_after['total_findings']} findings, "
                    f"{status_after['total_plans']} plans, "
                    f"{status_after['sync_percentage']:.1f}% in sync"
                )
            except Exception as e:
                if self.yaml_safe:
                    self._log(f"WARNING: Could not get post-sync status (YAML issues): {e}")
                    status_after = status_before  # Use previous status as fallback
                else:
                    raise

            # Validate synchronization
            try:
                validation_errors = self.synchronizer.validate_synchronization()
                if validation_errors:
                    self._log(
                        f"WARNING: Synchronization validation found {len(validation_errors)} issues"
                    )
                    for error in validation_errors:
                        self._log(f"  - {error}")
            except Exception as e:
                if self.yaml_safe:
                    self._log(f"WARNING: Synchronization validation failed (YAML issues): {e}")
                    validation_errors = [f"Validation failed due to YAML issues: {e}"]
                else:
                    raise

            return {
                "before": status_before,
                "after": status_after,
                "changes": sync_stats,
                "validation_errors": validation_errors,
            }

        except Exception as e:
            error_msg = f"Failed to synchronize remediation plans: {e}"
            self._log(f"ERROR: {error_msg}")
            raise RuntimeError(error_msg) from e

    def _generate_findings_document(self) -> bool:
        """Generate the findings document.

        Returns:
            True if document was generated successfully
        """
        try:
            # Ensure output directory exists
            self.findings_file.parent.mkdir(parents=True, exist_ok=True)

            # Generate document with YAML error handling
            try:
                self.generator.generate_document()
            except Exception as e:
                if self.yaml_safe:
                    self._log(f"WARNING: Document generation failed (YAML issues): {e}")
                    # Create a minimal fallback document
                    self._create_fallback_findings_document()
                else:
                    raise

            # Verify document was created
            if self.findings_file.exists():
                file_size = self.findings_file.stat().st_size
                self._log(f"Generated findings document: {self.findings_file} ({file_size} bytes)")
                return True
            self._log("ERROR: Findings document was not created")
            return False

        except Exception as e:
            error_msg = f"Failed to generate findings document: {e}"
            self._log(f"ERROR: {error_msg}")

            # In YAML-safe mode, try to create a minimal document
            if self.yaml_safe:
                try:
                    self._create_fallback_findings_document()
                    return True
                except Exception as fallback_error:
                    self._log(f"ERROR: Fallback document creation also failed: {fallback_error}")

            raise RuntimeError(error_msg) from e

    def _create_fallback_findings_document(self) -> None:
        """Create a minimal fallback findings document when YAML processing fails.

        This method creates a basic findings document that can be used when
        the normal document generation process fails due to YAML corruption.
        """
        try:
            timestamp = datetime.now(timezone.utc).isoformat()

            fallback_content = f"""# Security Findings Summary

**Generated:** {timestamp}
**Status:** FALLBACK MODE - YAML Issues Detected
**Mode:** Graceful Degradation Active

## ⚠️ Important Notice

This document was generated in fallback mode due to YAML file corruption or parsing issues.
Some information may be incomplete or missing. Manual review is recommended.

## Current Status

- **YAML Validation:** Issues detected
- **Document Generation:** Fallback mode active
- **Data Integrity:** Potentially compromised

## Recommended Actions

1. **Review YAML Files:** Check security YAML files for corruption
2. **Restore from Backup:** If available, restore corrupted files from backup
3. **Manual Verification:** Manually verify security findings and remediation plans
4. **Re-run Automation:** After fixing YAML issues, re-run the automation workflow

## Fallback Data

This document contains minimal information due to YAML processing issues.
For complete security findings, resolve YAML corruption and regenerate this document.

---

*This document was automatically generated in fallback mode due to YAML processing errors.*
*For complete and accurate security findings, please resolve YAML file issues and regenerate.*
"""

            # Write the fallback document
            with open(self.findings_file, "w", encoding="utf-8") as f:
                f.write(fallback_content)

            self._log(f"Created fallback findings document: {self.findings_file}")

        except Exception as e:
            self._log(f"ERROR: Failed to create fallback document: {e}")
            raise

    def _archive_scan_results(self) -> bool:
        """Archive current scan results for historical tracking.

        Returns:
            True if archival was successful
        """
        try:
            if not self.reports_dir.exists():
                self._log("WARNING: No reports directory to archive")
                return False

            # Archive scan results
            archive_dir = self.historical_manager.archive_scan_results()
            self._log(f"Archived scan results to: {archive_dir}")
            return True

        except Exception as e:
            error_msg = f"Failed to archive scan results: {e}"
            self._log(f"ERROR: {error_msg}")
            return False

    def _validate_workflow_results(self) -> list[str]:
        """Validate the results of the workflow execution.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        try:
            # Validate findings document exists and is readable
            if not self.findings_file.exists():
                errors.append(f"Findings document not found: {self.findings_file}")
            else:
                try:
                    content = self.findings_file.read_text(encoding="utf-8")
                    if len(content) < 100:  # Minimum expected content
                        errors.append("Findings document appears to be empty or too short")
                except Exception as e:
                    errors.append(f"Cannot read findings document: {e}")

            # Validate remediation registry
            registry_errors = self.datastore.validate_registry_structure()
            errors.extend(registry_errors)

            # Validate synchronization state
            sync_errors = self.synchronizer.validate_synchronization()
            errors.extend(sync_errors)

        except Exception as e:
            errors.append(f"Validation failed: {e}")

        return errors

    def _validate_security_yaml_files(self) -> dict[str, any]:
        """Validate security YAML files and handle errors gracefully.

        Returns:
            Dictionary with YAML validation results
        """
        try:
            # Import YAML validation functionality
            try:
                from validate_security_yaml import GracefulDegradation, SecurityFileValidator
            except ImportError:
                self._log("WARNING: YAML validation module not available - skipping validation")
                return {
                    "yaml_validation_status": "skipped",
                    "yaml_validation_errors": ["YAML validation module not available"],
                    "yaml_validation_warnings": [],
                }

            # Run YAML validation
            validator = SecurityFileValidator(verbose=self.verbose)
            summary = validator.validate_security_files(repair=True)

            self._log(
                f"YAML validation completed: {summary.valid_files}/{summary.total_files} files valid"
            )

            # Handle graceful degradation if needed
            if summary.invalid_files > 0:
                self._log(
                    f"WARNING: {summary.invalid_files} YAML files are invalid - activating graceful degradation"
                )

                degradation = GracefulDegradation(verbose=self.verbose)
                level = degradation.determine_functionality_level(summary.results)

                corrupted_files = [r.file_path for r in summary.results if not r.is_valid]
                strategy = degradation.create_fallback_strategy(level, corrupted_files)

                self._log(f"Graceful degradation level: {level.value}")
                self._log(f"Strategy: {strategy.description}")

                # Store validation results for later use
                self.yaml_validation_results = {
                    "summary": summary,
                    "degradation_level": level,
                    "strategy": strategy,
                }

                return {
                    "yaml_validation_status": "degraded",
                    "yaml_validation_errors": [r.errors for r in summary.results if r.errors],
                    "yaml_validation_warnings": [r.warnings for r in summary.results if r.warnings],
                    "degradation_level": level.value,
                    "corrupted_files": corrupted_files,
                }
            return {
                "yaml_validation_status": "success",
                "yaml_validation_errors": [],
                "yaml_validation_warnings": [],
            }

        except Exception as e:
            error_msg = f"YAML validation failed: {e}"
            self._log(f"ERROR: {error_msg}")

            # In YAML-safe mode, we continue with warnings rather than failing
            return {
                "yaml_validation_status": "error",
                "yaml_validation_errors": [error_msg],
                "yaml_validation_warnings": ["Continuing with reduced YAML safety"],
            }

    def _determine_operational_mode(self) -> str:
        """Determine the operational mode based on configuration flags.

        Returns:
            String describing the operational mode
        """
        if self.minimal_mode:
            return "minimal"
        if self.degraded_mode:
            return "degraded"
        if self.reduced_mode:
            return "reduced"
        return "full"

    def _validate_security_yaml_files_with_error_handling(self) -> dict[str, any]:
        """Validate security YAML files with comprehensive error handling.

        Returns:
            Dictionary with YAML validation results and error handling status
        """
        try:
            # Import YAML validation functionality
            try:
                from validate_security_yaml import GracefulDegradation, SecurityFileValidator
            except ImportError:
                self._log("WARNING: YAML validation module not available - using basic validation")
                return {
                    "yaml_validation_status": "basic_only",
                    "yaml_validation_errors": [],
                    "yaml_validation_warnings": ["Advanced YAML validation not available"],
                    "fallback_actions": ["Using basic file existence checks"],
                }

            # Run comprehensive YAML validation
            validator = SecurityFileValidator(verbose=self.verbose)
            summary = validator.validate_security_files(repair=True)

            self._log(
                f"YAML validation completed: {summary.valid_files}/{summary.total_files} files valid"
            )

            result = {
                "yaml_validation_status": "success"
                if summary.invalid_files == 0
                else "issues_detected",
                "yaml_validation_errors": [],
                "yaml_validation_warnings": [],
                "fallback_actions": [],
            }

            # Handle validation issues with graceful degradation
            if summary.invalid_files > 0:
                self._log(
                    f"WARNING: {summary.invalid_files} YAML files have issues - activating error handling"
                )

                degradation = GracefulDegradation(verbose=self.verbose)
                level = degradation.determine_functionality_level(summary.results)

                corrupted_files = [r.file_path for r in summary.results if not r.is_valid]
                strategy = degradation.create_fallback_strategy(level, corrupted_files)

                self._log(f"Graceful degradation level: {level.value}")
                self._log(f"Strategy: {strategy.description}")

                # Store validation results for later use
                self.yaml_validation_results = {
                    "summary": summary,
                    "degradation_level": level,
                    "strategy": strategy,
                }

                # Create fallback files if needed
                if level.value in ["minimal", "emergency"]:
                    try:
                        if level.value == "emergency":
                            created_files = degradation.create_emergency_fallback_files()
                        else:
                            created_files = degradation.create_minimal_valid_files(corrupted_files)

                        result["fallback_actions"].append(
                            f"Created {len(created_files)} fallback files"
                        )
                        self._log(
                            f"Created {len(created_files)} fallback files for {level.value} mode"
                        )
                    except Exception as e:
                        result["yaml_validation_warnings"].append(
                            f"Fallback file creation failed: {e}"
                        )

                result.update(
                    {
                        "yaml_validation_status": "degraded",
                        "degradation_level": level.value,
                        "corrupted_files": corrupted_files,
                        "strategy_description": strategy.description,
                    }
                )

            return result

        except Exception as e:
            error_msg = f"YAML validation with error handling failed: {e}"
            self._log(f"ERROR: {error_msg}")

            # Return error status but allow workflow to continue in YAML-safe mode
            return {
                "yaml_validation_status": "error",
                "yaml_validation_errors": [error_msg],
                "yaml_validation_warnings": ["Continuing with basic error handling"],
                "fallback_actions": ["Using emergency mode operations"],
            }

    def _process_scanner_outputs_with_fallback(self) -> dict[str, any]:
        """Process security scanner outputs with fallback handling for corrupted files.

        Returns:
            Dictionary with processing results and fallback actions
        """
        try:
            # First try normal processing
            if self.operational_mode == "full":
                return self._process_scanner_outputs()

            # For degraded modes, use fallback processing
            self._log(f"Processing scanner outputs in {self.operational_mode} mode")

            if not self.reports_dir.exists():
                self._log(f"WARNING: Reports directory not found: {self.reports_dir}")

                # Create fallback report data
                fallback_result = self._create_fallback_scanner_data()
                return {
                    "reports_processed": 0,
                    "findings_extracted": 0,
                    "fallback_data_created": True,
                    "warnings": ["Reports directory not found, using fallback data"],
                    "fallback_actions": ["Created minimal scanner data for workflow continuation"],
                }

            # Try to process available reports with error tolerance
            expected_files = {
                "pip-audit.json": "pip-audit",
                "bandit.json": "bandit",
                "secrets-scan.json": "secrets",
            }

            reports_found = []
            for filename, scanner_type in expected_files.items():
                file_path = self.reports_dir / filename
                if file_path.exists():
                    try:
                        # Validate file is readable and not corrupted
                        with open(file_path) as f:
                            json.load(f)  # Basic JSON validation
                        reports_found.append((file_path, scanner_type))
                        self._log(f"Found valid {scanner_type} report: {file_path}")
                    except Exception as e:
                        self._log(f"WARNING: Corrupted report file {file_path}: {e}")
                        if self.yaml_safe:
                            # Create fallback data for corrupted report
                            fallback_path = self._create_fallback_report(file_path, scanner_type)
                            if fallback_path:
                                reports_found.append((fallback_path, scanner_type))

            if not reports_found:
                self._log("WARNING: No valid scanner output files found")
                fallback_result = self._create_fallback_scanner_data()
                return {
                    "reports_processed": 0,
                    "findings_extracted": 0,
                    "fallback_data_created": True,
                    "warnings": ["No valid scanner output files found"],
                    "fallback_actions": ["Created minimal scanner data"],
                }

            # Extract findings with error tolerance
            try:
                all_findings = extract_all_findings(self.reports_dir)
                self._log(
                    f"Extracted {len(all_findings)} findings from {len(reports_found)} reports"
                )

                return {
                    "reports_processed": len(reports_found),
                    "findings_extracted": len(all_findings),
                    "scanner_types": [scanner_type for _, scanner_type in reports_found],
                    "operational_mode": self.operational_mode,
                }

            except Exception as e:
                error_msg = f"Failed to parse scanner outputs: {e}"
                self._log(f"ERROR: {error_msg}")

                # Create fallback findings data
                if self.yaml_safe:
                    fallback_result = self._create_fallback_scanner_data()
                    return {
                        "reports_processed": len(reports_found),
                        "findings_extracted": 0,
                        "fallback_data_created": True,
                        "warnings": [f"Scanner parsing failed, using fallback: {error_msg}"],
                        "fallback_actions": ["Created fallback findings data"],
                    }

                return {
                    "reports_processed": 0,
                    "findings_extracted": 0,
                    "errors": [error_msg],
                }

        except Exception as e:
            error_msg = f"Failed to process scanner outputs with fallback: {e}"
            self._log(f"ERROR: {error_msg}")

            if self.yaml_safe:
                # Emergency fallback
                fallback_result = self._create_fallback_scanner_data()
                return {
                    "reports_processed": 0,
                    "findings_extracted": 0,
                    "fallback_data_created": True,
                    "errors": [error_msg],
                    "fallback_actions": ["Emergency fallback data created"],
                }

            raise RuntimeError(error_msg) from e

    def _synchronize_remediation_plans_with_recovery(self) -> dict[str, any]:
        """Synchronize remediation plans with error recovery mechanisms.

        Returns:
            Dictionary with synchronization statistics and recovery actions
        """
        try:
            if not self.synchronizer:
                self._log("WARNING: Synchronizer not available, using fallback")
                return {
                    "skipped": True,
                    "reason": "synchronizer_unavailable",
                    "fallback_actions": ["Manual synchronization required"],
                }

            # Check if we're in degraded mode due to YAML issues
            recovery_actions = []
            if self.yaml_safe and self.yaml_validation_results:
                degradation_level = self.yaml_validation_results.get("degradation_level")
                if degradation_level and degradation_level.value in ["minimal", "emergency"]:
                    self._log(
                        "WARNING: Operating in degraded mode - synchronization may be limited"
                    )
                    recovery_actions.append("Limited synchronization due to YAML degradation")

            # Get synchronization status with error handling
            try:
                status_before = self.synchronizer.get_synchronization_status()
                self._log(
                    f"Before sync: {status_before['total_findings']} findings, "
                    f"{status_before['total_plans']} plans, "
                    f"{status_before['sync_percentage']:.1f}% in sync"
                )
            except Exception as e:
                if self.yaml_safe:
                    self._log(f"WARNING: Could not get sync status (YAML issues): {e}")
                    status_before = {"total_findings": 0, "total_plans": 0, "sync_percentage": 0.0}
                    recovery_actions.append("Using fallback sync status")
                else:
                    raise

            # Perform synchronization with retry logic
            sync_stats = None
            for attempt in range(3):  # Up to 3 attempts
                try:
                    sync_stats = self.synchronizer.synchronize_findings(preserve_manual_edits=True)
                    break
                except Exception as e:
                    self._log(f"Synchronization attempt {attempt + 1} failed: {e}")
                    if attempt == 2:  # Last attempt
                        if self.yaml_safe:
                            self._log(
                                "WARNING: All synchronization attempts failed, using fallback"
                            )
                            sync_stats = {
                                "added": 0,
                                "removed": 0,
                                "preserved": 0,
                                "errors": [str(e)],
                            }
                            recovery_actions.append(
                                "Synchronization failed, manual review required"
                            )
                        else:
                            raise

            # Get status after synchronization
            try:
                status_after = self.synchronizer.get_synchronization_status()
                self._log(
                    f"After sync: {status_after['total_findings']} findings, "
                    f"{status_after['total_plans']} plans, "
                    f"{status_after['sync_percentage']:.1f}% in sync"
                )
            except Exception as e:
                if self.yaml_safe:
                    self._log(f"WARNING: Could not get post-sync status (YAML issues): {e}")
                    status_after = status_before  # Use previous status as fallback
                    recovery_actions.append("Using fallback post-sync status")
                else:
                    raise

            # Validate synchronization with error tolerance
            try:
                validation_errors = self.synchronizer.validate_synchronization()
                if validation_errors:
                    self._log(
                        f"WARNING: Synchronization validation found {len(validation_errors)} issues"
                    )
                    for error in validation_errors:
                        self._log(f"  - {error}")
            except Exception as e:
                if self.yaml_safe:
                    self._log(f"WARNING: Synchronization validation failed (YAML issues): {e}")
                    validation_errors = [f"Validation failed due to YAML issues: {e}"]
                    recovery_actions.append("Synchronization validation failed")
                else:
                    raise

            return {
                "before": status_before,
                "after": status_after,
                "changes": sync_stats,
                "validation_errors": validation_errors,
                "recovery_actions": recovery_actions,
                "operational_mode": self.operational_mode,
            }

        except Exception as e:
            error_msg = f"Failed to synchronize remediation plans with recovery: {e}"
            self._log(f"ERROR: {error_msg}")

            if self.yaml_safe:
                return {
                    "failed": True,
                    "error": error_msg,
                    "recovery_actions": [
                        "Manual synchronization required",
                        "Check YAML file integrity",
                    ],
                    "fallback_status": "emergency_mode_active",
                }

            raise RuntimeError(error_msg) from e

    def _generate_findings_document_with_fallback(self) -> bool:
        """Generate the findings document with fallback support for corrupted data.

        Returns:
            True if document was generated successfully (including fallback)
        """
        try:
            # Ensure output directory exists
            self.findings_file.parent.mkdir(parents=True, exist_ok=True)

            # Try normal document generation first
            if self.generator and self.operational_mode == "full":
                try:
                    self.generator.generate_document()
                    if self.findings_file.exists():
                        file_size = self.findings_file.stat().st_size
                        self._log(
                            f"Generated findings document: {self.findings_file} ({file_size} bytes)"
                        )
                        return True
                except Exception as e:
                    self._log(f"WARNING: Normal document generation failed: {e}")

            # Use fallback document generation
            self._log("Using fallback document generation due to errors or degraded mode")
            self._create_fallback_findings_document_enhanced()

            if self.findings_file.exists():
                file_size = self.findings_file.stat().st_size
                self._log(
                    f"Generated fallback findings document: {self.findings_file} ({file_size} bytes)"
                )
                return True

            self._log("ERROR: Fallback document generation also failed")
            return False

        except Exception as e:
            error_msg = f"Failed to generate findings document with fallback: {e}"
            self._log(f"ERROR: {error_msg}")

            # Emergency document creation
            if self.yaml_safe:
                try:
                    self._create_emergency_findings_document()
                    return True
                except Exception as emergency_error:
                    self._log(f"ERROR: Emergency document creation also failed: {emergency_error}")

            return False

    def _create_fallback_scanner_data(self) -> dict[str, any]:
        """Create fallback scanner data when reports are corrupted or missing.

        Returns:
            Dictionary with fallback data creation results
        """
        try:
            self._log("Creating fallback scanner data...")

            # Ensure reports directory exists
            self.reports_dir.mkdir(parents=True, exist_ok=True)

            # Create minimal valid scanner reports
            fallback_reports = {
                "pip-audit.json": {
                    "vulnerabilities": [],
                    "metadata": {"timestamp": datetime.now().isoformat(), "fallback": True},
                },
                "bandit.json": {
                    "results": [],
                    "metadata": {"timestamp": datetime.now().isoformat(), "fallback": True},
                },
                "secrets-scan.json": {
                    "results": [],
                    "metadata": {"timestamp": datetime.now().isoformat(), "fallback": True},
                },
            }

            created_files = []
            for filename, data in fallback_reports.items():
                file_path = self.reports_dir / filename
                try:
                    with open(file_path, "w") as f:
                        json.dump(data, f, indent=2)
                    created_files.append(str(file_path))
                    self._log(f"Created fallback report: {file_path}")
                except Exception as e:
                    self._log(f"WARNING: Failed to create fallback report {file_path}: {e}")

            return {
                "created_files": created_files,
                "fallback_type": "minimal_scanner_data",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self._log(f"ERROR: Failed to create fallback scanner data: {e}")
            return {"error": str(e), "created_files": []}

    def _create_fallback_report(self, original_path: Path, scanner_type: str) -> Path | None:
        """Create a fallback report for a corrupted scanner output file.

        Args:
            original_path: Path to the corrupted original file
            scanner_type: Type of scanner (pip-audit, bandit, secrets)

        Returns:
            Path to the created fallback file, or None if creation failed
        """
        try:
            fallback_path = original_path.parent / f"fallback_{original_path.name}"

            # Create minimal valid report based on scanner type
            if scanner_type == "pip-audit":
                fallback_data = {
                    "vulnerabilities": [],
                    "metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "fallback": True,
                        "original_file": str(original_path),
                        "reason": "corrupted_original_file",
                    },
                }
            elif scanner_type == "bandit":
                fallback_data = {
                    "results": [],
                    "metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "fallback": True,
                        "original_file": str(original_path),
                        "reason": "corrupted_original_file",
                    },
                }
            else:  # secrets
                fallback_data = {
                    "results": [],
                    "metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "fallback": True,
                        "original_file": str(original_path),
                        "reason": "corrupted_original_file",
                    },
                }

            with open(fallback_path, "w") as f:
                json.dump(fallback_data, f, indent=2)

            self._log(f"Created fallback report: {fallback_path}")
            return fallback_path

        except Exception as e:
            self._log(f"ERROR: Failed to create fallback report for {original_path}: {e}")
            return None

    def _create_fallback_findings_document_enhanced(self) -> None:
        """Create an enhanced fallback findings document with operational context.

        This method creates a more comprehensive fallback document that includes
        information about the operational mode and recovery actions taken.
        """
        try:
            timestamp = datetime.now(timezone.utc).isoformat()

            # Determine status message based on operational mode
            if self.operational_mode == "emergency":
                status_msg = "EMERGENCY MODE - Critical YAML Issues Detected"
                notice_level = "🚨 CRITICAL EMERGENCY"
            elif self.operational_mode == "minimal":
                status_msg = "MINIMAL MODE - YAML Issues with Limited Recovery"
                notice_level = "⚠️ MINIMAL FUNCTIONALITY"
            elif self.operational_mode == "degraded":
                status_msg = "DEGRADED MODE - YAML Issues with Partial Recovery"
                notice_level = "⚠️ DEGRADED FUNCTIONALITY"
            elif self.operational_mode == "reduced":
                status_msg = "REDUCED MODE - Some YAML Issues Detected"
                notice_level = "⚠️ REDUCED FUNCTIONALITY"
            else:
                status_msg = "FALLBACK MODE - Error Recovery Active"
                notice_level = "⚠️ FALLBACK MODE"

            fallback_content = f"""# Security Findings Summary

**Generated:** {timestamp}
**Status:** {status_msg}
**Operational Mode:** {self.operational_mode.upper()}
**YAML Safe Mode:** {"ENABLED" if self.yaml_safe else "DISABLED"}
**Monitoring:** {"ENABLED" if self.with_monitoring else "DISABLED"}

## {notice_level}

This document was generated in {self.operational_mode} mode due to YAML file corruption, 
parsing issues, or other data integrity problems. Some information may be incomplete 
or missing. Manual review and intervention may be required.

## Current Status

- **YAML Validation:** Issues detected requiring fallback operation
- **Document Generation:** Fallback mode active
- **Data Integrity:** Potentially compromised
- **Operational Mode:** {self.operational_mode}
- **Workflow Continuation:** {"Enabled with limitations" if self.yaml_safe else "May be blocked"}

## Recovery Actions Taken

"""

            # Add recovery actions if available
            if hasattr(self, "yaml_validation_results") and self.yaml_validation_results:
                strategy = self.yaml_validation_results.get("strategy")
                if strategy:
                    fallback_content += f"- **Recovery Strategy:** {strategy.description}\n"

                degradation_level = self.yaml_validation_results.get("degradation_level")
                if degradation_level:
                    fallback_content += f"- **Degradation Level:** {degradation_level.value}\n"

            fallback_content += f"""
- **Fallback Document:** Generated to maintain workflow continuity
- **Error Handling:** {"Comprehensive error recovery active" if self.yaml_safe else "Basic error handling"}
- **Monitoring Integration:** {"Active with limited functionality" if self.with_monitoring else "Not available"}

## Recommended Actions

### Immediate Actions
1. **Review YAML Files:** Check security YAML files for corruption or syntax errors
2. **Check Logs:** Review workflow logs for specific error details
3. **Verify Backups:** Ensure backup systems are functioning properly

### Recovery Actions
1. **Restore from Backup:** If available, restore corrupted files from known good backups
2. **Manual Validation:** Manually verify security findings and remediation plans
3. **Re-run Automation:** After fixing YAML issues, re-run the automation workflow

### Monitoring Actions
1. **Alert Review:** Check for any monitoring alerts generated during this workflow
2. **Data Integrity:** Verify the integrity of security data files
3. **Workflow Status:** Monitor subsequent workflow runs for continued issues

## Operational Mode Details

**{self.operational_mode.upper()} Mode Characteristics:**
"""

            # Add mode-specific information
            if self.operational_mode == "emergency":
                fallback_content += """
- Minimal functionality only
- Critical files corrupted or inaccessible
- Manual intervention required immediately
- Workflow continuation severely limited
"""
            elif self.operational_mode == "minimal":
                fallback_content += """
- Basic functionality available
- Some files corrupted but recoverable
- Limited automation capabilities
- Manual review strongly recommended
"""
            elif self.operational_mode == "degraded":
                fallback_content += """
- Reduced functionality with graceful degradation
- Most files accessible with some corruption
- Automation continues with limitations
- Regular monitoring recommended
"""
            elif self.operational_mode == "reduced":
                fallback_content += """
- Most functionality available
- Minor issues detected and handled
- Automation continues normally
- Periodic review recommended
"""

            fallback_content += f"""

## Fallback Data

This document contains minimal information due to data processing issues.
For complete and accurate security findings, resolve data integrity issues and regenerate this document.

### Data Sources
- **Scanner Reports:** {"Fallback data used" if self.operational_mode in ["emergency", "minimal"] else "Partial data available"}
- **Remediation Plans:** {"Emergency fallback" if self.operational_mode == "emergency" else "Limited availability"}
- **Historical Data:** {"Not available" if self.operational_mode == "emergency" else "Partially available"}

## Technical Details

- **Workflow ID:** {datetime.now().strftime("%Y%m%d_%H%M%S")}
- **Generation Method:** Enhanced fallback with error recovery
- **YAML Validation:** {"Comprehensive with repair attempts" if self.yaml_safe else "Basic validation only"}
- **Error Recovery:** {"Multi-level graceful degradation" if self.yaml_safe else "Standard error handling"}

---

*This document was automatically generated in {self.operational_mode} mode due to data integrity issues.*
*For complete and accurate security findings, please resolve data corruption and regenerate.*
*Monitoring and alerting systems {"are" if self.with_monitoring else "are not"} active for this workflow.*
"""

            # Write the enhanced fallback document
            with open(self.findings_file, "w", encoding="utf-8") as f:
                f.write(fallback_content)

            self._log(f"Created enhanced fallback findings document: {self.findings_file}")

        except Exception as e:
            self._log(f"ERROR: Failed to create enhanced fallback document: {e}")
            # Fall back to basic fallback document
            self._create_fallback_findings_document()

    def _create_emergency_findings_document(self) -> None:
        """Create an emergency findings document when all other methods fail.

        This is the last resort document creation method.
        """
        try:
            timestamp = datetime.now(timezone.utc).isoformat()

            emergency_content = f"""# Security Findings - Emergency Mode

**Generated:** {timestamp}
**Status:** EMERGENCY MODE - Critical System Failure
**Document Type:** Emergency Fallback

## 🚨 CRITICAL ALERT

This is an emergency document generated due to critical system failures.
All normal document generation methods have failed.

## Immediate Actions Required

1. **STOP ALL AUTOMATED PROCESSES**
2. **MANUAL INTERVENTION REQUIRED**
3. **CHECK SYSTEM INTEGRITY**
4. **RESTORE FROM BACKUPS**

## System Status

- All automated security processing has failed
- Data integrity cannot be guaranteed
- Manual security review is mandatory
- Workflow continuation is blocked

## Emergency Contact

Contact system administrators immediately.
Do not proceed with any security-related operations until system integrity is restored.

---

*EMERGENCY DOCUMENT - MANUAL INTERVENTION REQUIRED*
"""

            with open(self.findings_file, "w", encoding="utf-8") as f:
                f.write(emergency_content)

            self._log(f"Created emergency findings document: {self.findings_file}")

        except Exception as e:
            self._log(f"CRITICAL ERROR: Failed to create emergency document: {e}")
            raise

    def _archive_scan_results_safely(self) -> bool:
        """Archive current scan results with error handling.

        Returns:
            True if archival was successful or safely skipped
        """
        try:
            if not self.reports_dir.exists():
                self._log("WARNING: No reports directory to archive")
                return False

            if not self.historical_manager:
                self._log("WARNING: Historical manager not available, skipping archival")
                return False

            # Archive scan results with error handling
            try:
                archive_dir = self.historical_manager.archive_scan_results()
                self._log(f"Archived scan results to: {archive_dir}")
                return True
            except Exception as e:
                if self.yaml_safe:
                    self._log(f"WARNING: Archival failed but continuing: {e}")
                    return False
                raise

        except Exception as e:
            error_msg = f"Failed to archive scan results safely: {e}"
            self._log(f"ERROR: {error_msg}")
            return False

    def _validate_workflow_results_with_tolerance(self) -> list[str]:
        """Validate the results of the workflow execution with error tolerance.

        Returns:
            List of validation errors (empty if valid or acceptable in current mode)
        """
        errors = []

        try:
            # Validate findings document exists and is readable
            if not self.findings_file.exists():
                if self.operational_mode == "emergency":
                    # In emergency mode, missing document is acceptable if we tried to create one
                    errors.append("Findings document missing (acceptable in emergency mode)")
                else:
                    errors.append(f"Findings document not found: {self.findings_file}")
            else:
                try:
                    content = self.findings_file.read_text(encoding="utf-8")
                    min_content_length = 50 if self.operational_mode == "emergency" else 100
                    if len(content) < min_content_length:
                        if self.operational_mode in ["emergency", "minimal"]:
                            # Shorter content acceptable in degraded modes
                            pass
                        else:
                            errors.append("Findings document appears to be empty or too short")
                except Exception as e:
                    errors.append(f"Cannot read findings document: {e}")

            # Validate remediation registry (with tolerance for degraded modes)
            if self.datastore and self.operational_mode not in ["emergency", "minimal"]:
                try:
                    registry_errors = self.datastore.validate_registry_structure()
                    if registry_errors and self.operational_mode == "full":
                        errors.extend(registry_errors)
                    elif registry_errors:
                        # In degraded modes, registry errors are warnings
                        self._log(
                            f"WARNING: Registry validation issues in {self.operational_mode} mode: {len(registry_errors)} issues"
                        )
                except Exception as e:
                    if self.yaml_safe:
                        self._log(f"WARNING: Registry validation failed: {e}")
                    else:
                        errors.append(f"Registry validation failed: {e}")

            # Validate synchronization state (with tolerance)
            if self.synchronizer and self.operational_mode not in ["emergency", "minimal"]:
                try:
                    sync_errors = self.synchronizer.validate_synchronization()
                    if sync_errors and self.operational_mode == "full":
                        errors.extend(sync_errors)
                    elif sync_errors:
                        # In degraded modes, sync errors are warnings
                        self._log(
                            f"WARNING: Synchronization issues in {self.operational_mode} mode: {len(sync_errors)} issues"
                        )
                except Exception as e:
                    if self.yaml_safe:
                        self._log(f"WARNING: Synchronization validation failed: {e}")
                    else:
                        errors.append(f"Synchronization validation failed: {e}")

        except Exception as e:
            if self.yaml_safe:
                self._log(f"WARNING: Validation with tolerance failed: {e}")
                errors.append(f"Validation failed but continuing in safe mode: {e}")
            else:
                errors.append(f"Validation failed: {e}")

        return errors

    def _generate_monitoring_alerts(self, workflow_results: dict[str, any]) -> list[str]:
        """Generate monitoring alerts based on workflow results.

        Args:
            workflow_results: Results from the workflow execution

        Returns:
            List of generated alert messages
        """
        alerts = []

        try:
            # Alert for YAML validation issues
            yaml_status = workflow_results.get("yaml_validation_status", "unknown")
            if yaml_status in ["degraded", "error"]:
                alerts.append(f"YAML validation issues detected: {yaml_status}")

            # Alert for operational mode changes
            if self.operational_mode != "full":
                alerts.append(f"System operating in {self.operational_mode} mode")

            # Alert for fallback actions
            fallback_actions = workflow_results.get("fallback_actions", [])
            if fallback_actions:
                alerts.append(f"Fallback actions taken: {len(fallback_actions)} actions")

            # Alert for validation errors
            validation_errors = workflow_results.get("validation_errors", [])
            if validation_errors:
                alerts.append(f"Validation errors detected: {len(validation_errors)} errors")

            # Alert for critical failures
            if workflow_results.get("emergency_fallback"):
                alerts.append("CRITICAL: Emergency fallback mode activated")

            self._log(f"Generated {len(alerts)} monitoring alerts")
            return alerts

        except Exception as e:
            self._log(f"WARNING: Failed to generate monitoring alerts: {e}")
            return [f"Alert generation failed: {e}"]

    def _create_emergency_fallback(self) -> dict[str, any]:
        """Create emergency fallback when the entire workflow fails.

        Returns:
            Dictionary with emergency fallback results
        """
        try:
            self._log("Creating emergency fallback due to complete workflow failure...")

            # Create emergency findings document
            self._create_emergency_findings_document()

            # Create emergency scanner data
            fallback_scanner_result = self._create_fallback_scanner_data()

            # Create emergency status report
            emergency_report = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "emergency_fallback_active",
                "actions_taken": [
                    "Created emergency findings document",
                    "Created fallback scanner data",
                    "Activated emergency mode",
                ],
                "manual_intervention_required": True,
                "fallback_files": fallback_scanner_result.get("created_files", []),
                "recommendations": [
                    "Check system logs for detailed error information",
                    "Verify YAML file integrity",
                    "Restore from backups if available",
                    "Contact system administrators",
                ],
            }

            self._log("Emergency fallback completed")
            return emergency_report

        except Exception as e:
            self._log(f"CRITICAL: Emergency fallback also failed: {e}")
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "emergency_fallback_failed",
                "error": str(e),
                "critical_failure": True,
            }

    def _log(self, message: str) -> None:
        """Log a message with timestamp.

        Args:
            message: Message to log
        """
        if self.verbose:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            print(f"[{timestamp}] {message}")


def main() -> int:
    """Main entry point for the automation engine."""
    parser = argparse.ArgumentParser(
        description="Security findings automation engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Run with default settings
  %(prog)s --verbose                          # Run with verbose logging
  %(prog)s --reports-dir /path/to/reports     # Use custom reports directory
  %(prog)s --output /path/to/findings.md      # Use custom output file
  %(prog)s --dry-run                          # Show what would be done without making changes
        """,
    )

    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("security/reports/latest"),
        help="Directory containing security scan reports (default: security/reports/latest)",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("security/findings/SECURITY_FINDINGS.md"),
        help="Output file for findings document (default: security/findings/SECURITY_FINDINGS.md)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output results in JSON format",
    )

    parser.add_argument(
        "--yaml-safe",
        action="store_true",
        help="Enable YAML validation and graceful degradation for corrupted files",
    )

    parser.add_argument(
        "--reduced-mode",
        action="store_true",
        help="Enable reduced functionality mode for minor issues",
    )

    parser.add_argument(
        "--degraded-mode",
        action="store_true",
        help="Enable degraded functionality mode for YAML issues",
    )

    parser.add_argument(
        "--minimal-mode",
        action="store_true",
        help="Enable minimal functionality mode for severe issues",
    )

    parser.add_argument(
        "--with-monitoring",
        action="store_true",
        help="Enable monitoring integration and alerting",
    )

    args = parser.parse_args()

    try:
        if args.dry_run:
            print("DRY RUN MODE - No changes will be made")
            print(f"Reports directory: {args.reports_dir}")
            print(f"Output file: {args.output}")

            # Check what files would be processed
            if args.reports_dir.exists():
                scanner_files = ["pip-audit.json", "bandit.json", "secrets-scan.json"]
                found_files = [f for f in scanner_files if (args.reports_dir / f).exists()]
                print(f"Scanner files found: {found_files}")
            else:
                print("Reports directory does not exist")

            # Show operational mode
            if args.minimal_mode:
                print("Operational mode: MINIMAL")
            elif args.degraded_mode:
                print("Operational mode: DEGRADED")
            elif args.reduced_mode:
                print("Operational mode: REDUCED")
            else:
                print("Operational mode: FULL")

            return 0

        # Initialize and run automation engine
        engine = AutomationEngine(
            reports_dir=args.reports_dir,
            findings_file=args.output,
            verbose=args.verbose,
            yaml_safe=args.yaml_safe,
            reduced_mode=args.reduced_mode,
            degraded_mode=args.degraded_mode,
            minimal_mode=args.minimal_mode,
            with_monitoring=args.with_monitoring,
        )

        results = engine.run_complete_workflow()

        # Output results
        if args.json_output:
            print(json.dumps(results, indent=2, default=str))
        else:
            # Human-readable output
            print("Security Findings Automation Results:")

            # YAML validation results
            yaml_status = results.get("yaml_validation_status", "not_performed")
            if yaml_status != "not_performed":
                print(f"  YAML validation: {yaml_status.upper()}")
                if yaml_status == "degraded":
                    degradation_level = results.get("degradation_level", "unknown")
                    print(f"  Degradation level: {degradation_level}")
                    corrupted_files = results.get("corrupted_files", [])
                    if corrupted_files:
                        print(f"  Corrupted files: {len(corrupted_files)}")

            print(f"  Reports processed: {results.get('reports_processed', 0)}")
            print(f"  Findings extracted: {results.get('findings_extracted', 0)}")

            sync_stats = results.get("synchronization_stats", {}).get("changes", {})
            print(f"  Remediation plans added: {sync_stats.get('added', 0)}")
            print(f"  Remediation plans removed: {sync_stats.get('removed', 0)}")
            print(f"  Remediation plans preserved: {sync_stats.get('preserved', 0)}")

            print(f"  Document generated: {results.get('document_generated', False)}")

            validation_errors = results.get("validation_errors", [])
            if validation_errors:
                print(f"  Validation errors: {len(validation_errors)}")
                for error in validation_errors:
                    print(f"    - {error}")
            else:
                print("  Validation: PASSED")

            # YAML validation warnings
            yaml_warnings = results.get("yaml_validation_warnings", [])
            if yaml_warnings:
                print(f"  YAML warnings: {len(yaml_warnings)}")
                for warning in yaml_warnings[:3]:  # Show first 3 warnings
                    print(f"    - {warning}")
                if len(yaml_warnings) > 3:
                    print(f"    ... and {len(yaml_warnings) - 3} more warnings")

        # Return appropriate exit code
        validation_errors = results.get("validation_errors", [])
        errors = results.get("errors", [])
        yaml_status = results.get("yaml_validation_status", "not_performed")

        # In YAML-safe mode, degraded operation is acceptable
        if args.yaml_safe and yaml_status == "degraded":
            print("\n⚠️ Completed with YAML degradation - manual review recommended")
            return 0  # Success with warnings
        if validation_errors or errors:
            return 1
        return 0

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
