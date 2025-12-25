#!/usr/bin/env python3
"""CI/CD Error Handling System.

Comprehensive error handling for security data files in CI/CD workflows.
Implements corruption detection, recovery mechanisms, and monitoring integration.

Requirements addressed: 18.1, 18.2
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sys
from typing import Any

# Add project root to Python path for imports

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import existing error handling and monitoring infrastructure
try:
    # Try to import from scripts package first, then fallback to direct import
    try:
        from scripts.validate_security_yaml import (
            FunctionalityLevel,
            GracefulDegradation,
            SecurityFileValidator,
            ValidationSummary,
        )
    except ImportError:
        # Fallback: add scripts directory to path and import directly
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from validate_security_yaml import (
            FunctionalityLevel,
            GracefulDegradation,
            SecurityFileValidator,
            ValidationSummary,
        )

    from security.error_handling import (
        CorruptionSeverity,
        FileIntegrityInfo,
        RecoveryResult,
        RecoveryStrategy,
        SecurityFileErrorHandler,
        detect_file_corruption,
        recover_corrupted_file,
    )
    from security.monitoring import (
        AlertChannel,
        AlertConfig,
        AlertSeverity,
        DataIntegrityMonitor,
        alert_manual_intervention,
        log_recovery_result,
        log_validation_result,
    )
except ImportError as e:
    print(f"ERROR: Required modules not available: {e}", file=sys.stderr)
    print("Ensure security modules are properly installed", file=sys.stderr)
    sys.exit(1)


@dataclass
class CICDErrorConfig:
    """Configuration for CI/CD error handling."""

    enable_monitoring: bool = True
    enable_recovery: bool = True
    enable_graceful_degradation: bool = True
    fail_on_critical_corruption: bool = True
    create_backups: bool = True
    verbose_logging: bool = False
    alert_channels: list[AlertChannel] = field(
        default_factory=lambda: [AlertChannel.LOG, AlertChannel.CONSOLE, AlertChannel.FILE]
    )
    max_recovery_attempts: int = 3
    workflow_name: str = "cicd-workflow"


@dataclass
class CICDErrorResult:
    """Result of CI/CD error handling operation."""

    success: bool
    workflow_can_continue: bool
    functionality_level: FunctionalityLevel
    files_processed: int = 0
    files_corrupted: int = 0
    files_recovered: int = 0
    files_failed_recovery: int = 0
    critical_failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recovery_actions: list[str] = field(default_factory=list)
    fallback_files_created: list[str] = field(default_factory=list)
    monitoring_alerts: int = 0


class CICDErrorHandler:
    """Comprehensive error handler for CI/CD workflows."""

    def __init__(self, config: CICDErrorConfig | None = None) -> None:
        """Initialize the CI/CD error handler.

        Args:
            config: Error handling configuration (uses defaults if None)
        """
        self.config = config or CICDErrorConfig()

        # Initialize components
        self.error_handler = SecurityFileErrorHandler(verbose=self.config.verbose_logging)
        self.validator = SecurityFileValidator(verbose=self.config.verbose_logging)
        self.degradation = GracefulDegradation(verbose=self.config.verbose_logging)

        # Initialize monitoring if enabled
        self.monitor = None
        if self.config.enable_monitoring:
            alert_config = AlertConfig(
                enabled=True,
                channels=self.config.alert_channels,
                min_severity=AlertSeverity.WARNING,
            )
            self.monitor = DataIntegrityMonitor(
                alert_config=alert_config, verbose=self.config.verbose_logging
            )

        # Set up logging
        self.logger = self._setup_logger()

        # Track workflow state
        self.workflow_state = {
            "start_time": datetime.now(timezone.utc),
            "files_processed": [],
            "errors_encountered": [],
            "recovery_attempts": [],
            "alerts_generated": [],
        }

        # YAML validation context (set by external processes)
        self.yaml_context = None

    def _setup_logger(self) -> logging.Logger:
        """Set up logging for CI/CD error handler.

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger("cicd_error_handler")
        logger.setLevel(logging.DEBUG if self.config.verbose_logging else logging.INFO)

        if not logger.handlers:
            # Console handler for CI/CD output
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - CICD-ERROR - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def process_security_files(self, file_paths: list[str | Path] | None = None) -> CICDErrorResult:
        """Process security files with comprehensive error handling.

        Args:
            file_paths: Specific files to process (processes all security files if None)

        Returns:
            CICDErrorResult with processing details
        """
        result = CICDErrorResult(
            success=True, workflow_can_continue=True, functionality_level=FunctionalityLevel.FULL
        )

        try:
            self.logger.info(
                f"🔍 Starting CI/CD error handling for workflow: {self.config.workflow_name}"
            )

            # Determine files to process
            if file_paths is None:
                file_paths = self._find_security_files()
            else:
                file_paths = [Path(p) for p in file_paths]

            result.files_processed = len(file_paths)
            self.logger.info(f"📊 Processing {result.files_processed} security files")

            # Create backups if enabled
            if self.config.create_backups:
                self._create_workflow_backups(file_paths)

            # Process each file with error handling
            corrupted_files = []
            recovery_failures = []

            for file_path in file_paths:
                try:
                    file_result = self._process_single_file(file_path)

                    if file_result.is_corrupted:
                        result.files_corrupted += 1
                        corrupted_files.append(str(file_path))

                        # Attempt recovery if enabled
                        if self.config.enable_recovery:
                            recovery_result = self._attempt_file_recovery(file_path, file_result)

                            if recovery_result.success:
                                result.files_recovered += 1
                                result.recovery_actions.append(
                                    f"Recovered {file_path} using {recovery_result.strategy_used.value}"
                                )
                            else:
                                result.files_failed_recovery += 1
                                recovery_failures.append(str(file_path))

                                # Check if this is a critical failure
                                if self._is_critical_file(file_path):
                                    result.critical_failures.append(str(file_path))

                except Exception as e:
                    self.logger.exception(f"❌ Error processing {file_path}: {e}")
                    result.warnings.append(f"Processing error for {file_path}: {e}")

            # Determine functionality level and workflow continuation
            if corrupted_files:
                validation_results = [self.validator.validate_file(f) for f in corrupted_files]
                result.functionality_level = self.degradation.determine_functionality_level(
                    validation_results
                )

                # Adjust functionality level based on YAML validation context
                if self.yaml_context:
                    yaml_level = self.yaml_context.get("validation_level", "unknown")
                    yaml_degraded = self.yaml_context.get("degraded_mode", False)

                    if yaml_degraded:
                        self.logger.warning(
                            f"YAML validation in degraded mode (level: {yaml_level})"
                        )

                        # Adjust functionality level to be more conservative when YAML is degraded
                        if yaml_level == "emergency":
                            result.functionality_level = FunctionalityLevel.EMERGENCY
                        elif (
                            yaml_level == "minimal"
                            and result.functionality_level != FunctionalityLevel.EMERGENCY
                        ):
                            result.functionality_level = FunctionalityLevel.MINIMAL
                        elif (
                            yaml_level == "degraded"
                            and result.functionality_level == FunctionalityLevel.FULL
                        ):
                            result.functionality_level = FunctionalityLevel.REDUCED

                # Handle graceful degradation if enabled
                if self.config.enable_graceful_degradation:
                    degradation_result = self._handle_graceful_degradation(
                        corrupted_files, result.functionality_level
                    )
                    result.fallback_files_created.extend(
                        degradation_result.get("created_files", [])
                    )
                    result.warnings.extend(degradation_result.get("warnings", []))

            # Determine if workflow can continue
            result.workflow_can_continue = self._can_workflow_continue(result)

            # Update success status
            if result.critical_failures and self.config.fail_on_critical_corruption:
                result.success = False
                self.logger.error("❌ Critical file corruption detected - workflow cannot continue")
            elif result.files_failed_recovery > 0:
                result.success = result.functionality_level != FunctionalityLevel.EMERGENCY
                if result.success:
                    self.logger.warning(
                        "⚠️ Some files failed recovery but workflow can continue with degraded functionality"
                    )

            # Generate final summary
            self._log_processing_summary(result)

            return result

        except Exception as e:
            self.logger.exception(f"💥 Critical error in CI/CD error handling: {e}")
            result.success = False
            result.workflow_can_continue = False
            result.critical_failures.append(f"Critical error: {e}")
            return result

    def _find_security_files(self) -> list[Path]:
        """Find all security data files in the project.

        Returns:
            List of Path objects for security files
        """
        security_paths = [
            "security/findings",
            "security/config",
            "security/reports",
            "security/scripts",
        ]

        files = []
        for security_path in security_paths:
            path = Path(security_path)
            if path.exists():
                # Find YAML, JSON, and Markdown files
                for pattern in ["*.yml", "*.yaml", "*.json", "*.md"]:
                    files.extend(path.rglob(pattern))

        return sorted(files)

    def _create_workflow_backups(self, file_paths: list[Path]) -> None:
        """Create backups of files before processing.

        Args:
            file_paths: List of files to backup
        """
        try:
            backup_dir = Path("security/backups/cicd")
            backup_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            workflow_backup_dir = backup_dir / f"{self.config.workflow_name}_{timestamp}"
            workflow_backup_dir.mkdir(exist_ok=True)

            backup_count = 0
            for file_path in file_paths:
                if file_path.exists():
                    try:
                        import shutil

                        backup_path = workflow_backup_dir / file_path.name
                        shutil.copy2(file_path, backup_path)
                        backup_count += 1
                    except Exception as e:
                        self.logger.warning(f"Failed to backup {file_path}: {e}")

            self.logger.info(f"📦 Created {backup_count} backup files in {workflow_backup_dir}")

        except Exception as e:
            self.logger.warning(f"Backup creation failed: {e}")

    def _process_single_file(self, file_path: Path) -> FileIntegrityInfo:
        """Process a single file with error detection and monitoring.

        Args:
            file_path: Path to the file to process

        Returns:
            FileIntegrityInfo with corruption details
        """
        try:
            # Detect corruption
            integrity_info = detect_file_corruption(file_path, verbose=self.config.verbose_logging)

            # Log to monitoring system if enabled
            if self.monitor:
                log_validation_result(file_path, integrity_info, self.monitor)

            # Track in workflow state
            self.workflow_state["files_processed"].append(str(file_path))

            if integrity_info.is_corrupted:
                self.workflow_state["errors_encountered"].append(
                    {
                        "file": str(file_path),
                        "severity": integrity_info.corruption_severity.value,
                        "details": integrity_info.corruption_details,
                    }
                )

                self.logger.warning(
                    f"⚠️ Corruption detected in {file_path}: {integrity_info.corruption_severity.value}"
                )
            else:
                self.logger.debug(f"✅ File integrity verified: {file_path}")

            return integrity_info

        except Exception as e:
            self.logger.exception(f"Error processing {file_path}: {e}")
            # Create a basic integrity info for error case
            return FileIntegrityInfo(
                file_path=str(file_path),
                file_type="unknown",
                is_corrupted=True,
                corruption_severity=CorruptionSeverity.CRITICAL,
                corruption_details=[f"Processing error: {e}"],
            )

    def _attempt_file_recovery(
        self, file_path: Path, integrity_info: FileIntegrityInfo
    ) -> RecoveryResult:
        """Attempt to recover a corrupted file.

        Args:
            file_path: Path to the corrupted file
            integrity_info: File integrity information

        Returns:
            RecoveryResult with recovery details
        """
        try:
            self.logger.info(f"🔧 Attempting recovery of {file_path}")

            # Attempt recovery with retry logic
            recovery_result = None
            for attempt in range(self.config.max_recovery_attempts):
                try:
                    recovery_result = recover_corrupted_file(
                        file_path, verbose=self.config.verbose_logging
                    )

                    if recovery_result.success:
                        break

                    self.logger.warning(f"Recovery attempt {attempt + 1} failed for {file_path}")

                except Exception as e:
                    self.logger.warning(
                        f"Recovery attempt {attempt + 1} error for {file_path}: {e}"
                    )

            # Log recovery result to monitoring
            if self.monitor and recovery_result:
                log_recovery_result(file_path, recovery_result, self.monitor)

            # Track recovery attempt
            self.workflow_state["recovery_attempts"].append(
                {
                    "file": str(file_path),
                    "success": recovery_result.success if recovery_result else False,
                    "strategy": recovery_result.strategy_used.value
                    if recovery_result
                    else "unknown",
                    "attempts": self.config.max_recovery_attempts,
                }
            )

            if recovery_result and recovery_result.success:
                self.logger.info(f"✅ Successfully recovered {file_path}")
            else:
                self.logger.error(f"❌ Failed to recover {file_path}")

                # Alert for manual intervention if monitoring enabled
                if self.monitor:
                    alert_manual_intervention(
                        file_path,
                        f"File recovery failed after {self.config.max_recovery_attempts} attempts",
                        {"integrity_info": integrity_info.__dict__},
                        self.monitor,
                    )

            return recovery_result or RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.FAIL_GRACEFULLY,
                original_file=str(file_path),
                errors=["Recovery failed after all attempts"],
            )

        except Exception as e:
            self.logger.exception(f"Critical error during recovery of {file_path}: {e}")
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.FAIL_GRACEFULLY,
                original_file=str(file_path),
                errors=[f"Critical recovery error: {e}"],
            )

    def _is_critical_file(self, file_path: Path) -> bool:
        """Check if a file is critical for workflow operation.

        Args:
            file_path: Path to check

        Returns:
            True if file is critical, False otherwise
        """
        critical_files = {
            "remediation-timeline.yml",
            "remediation-plans.yml",
            "SECURITY_FINDINGS.md",
            "security-config.yml",
        }

        return file_path.name in critical_files

    def _handle_graceful_degradation(
        self, corrupted_files: list[str], functionality_level: FunctionalityLevel
    ) -> dict[str, Any]:
        """Handle graceful degradation for corrupted files.

        Args:
            corrupted_files: List of corrupted file paths
            functionality_level: Determined functionality level

        Returns:
            Dictionary with degradation results
        """
        try:
            self.logger.info(
                f"🔄 Activating graceful degradation (level: {functionality_level.value})"
            )

            # Create fallback strategy
            strategy = self.degradation.create_fallback_strategy(
                functionality_level, corrupted_files
            )

            result = {
                "success": True,
                "level": functionality_level.value,
                "strategy": strategy.description,
                "created_files": [],
                "warnings": [],
            }

            # Create fallback files if needed
            if functionality_level in [FunctionalityLevel.MINIMAL, FunctionalityLevel.EMERGENCY]:
                try:
                    if functionality_level == FunctionalityLevel.EMERGENCY:
                        created_files = self.degradation.create_emergency_fallback_files()
                    else:
                        created_files = self.degradation.create_minimal_valid_files(corrupted_files)

                    result["created_files"] = created_files
                    self.logger.info(f"✅ Created {len(created_files)} fallback files")

                except Exception as e:
                    self.logger.warning(f"Failed to create fallback files: {e}")
                    result["warnings"].append(f"Fallback file creation failed: {e}")

            # Execute degraded workflow
            workflow_result = self.degradation.execute_degraded_workflow(strategy)
            result["workflow_execution"] = workflow_result

            if workflow_result.get("warnings"):
                result["warnings"].extend(workflow_result["warnings"])

            return result

        except Exception as e:
            self.logger.exception(f"Graceful degradation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "created_files": [],
                "warnings": [f"Graceful degradation failed: {e}"],
            }

    def _can_workflow_continue(self, result: CICDErrorResult) -> bool:
        """Determine if the workflow can continue based on error handling results.

        Args:
            result: Current error handling result

        Returns:
            True if workflow can continue, False otherwise
        """
        # Critical failures always block workflow if configured to fail
        if result.critical_failures and self.config.fail_on_critical_corruption:
            return False

        # Emergency level requires manual intervention unless graceful degradation is enabled
        if result.functionality_level == FunctionalityLevel.EMERGENCY:
            return self.config.enable_graceful_degradation

        # Other levels can continue
        return True

    def _log_processing_summary(self, result: CICDErrorResult) -> None:
        """Log a summary of the processing results.

        Args:
            result: Processing result to summarize
        """
        self.logger.info("📊 CI/CD Error Handling Summary:")
        self.logger.info(f"   Files Processed: {result.files_processed}")
        self.logger.info(f"   Files Corrupted: {result.files_corrupted}")
        self.logger.info(f"   Files Recovered: {result.files_recovered}")
        self.logger.info(f"   Recovery Failures: {result.files_failed_recovery}")
        self.logger.info(f"   Critical Failures: {len(result.critical_failures)}")
        self.logger.info(f"   Functionality Level: {result.functionality_level.value}")
        self.logger.info(f"   Workflow Can Continue: {result.workflow_can_continue}")

        if result.fallback_files_created:
            self.logger.info(f"   Fallback Files Created: {len(result.fallback_files_created)}")

        if result.warnings:
            self.logger.warning("⚠️ Warnings:")
            for warning in result.warnings:
                self.logger.warning(f"   - {warning}")

        if result.critical_failures:
            self.logger.error("❌ Critical Failures:")
            for failure in result.critical_failures:
                self.logger.error(f"   - {failure}")

    def generate_cicd_report(self, result: CICDErrorResult) -> dict[str, Any]:
        """Generate a comprehensive report for CI/CD systems.

        Args:
            result: Error handling result

        Returns:
            Dictionary with CI/CD report data
        """
        # Create a JSON-serializable copy of workflow_state
        workflow_state_serializable = self.workflow_state.copy()
        if "start_time" in workflow_state_serializable:
            workflow_state_serializable["start_time"] = workflow_state_serializable[
                "start_time"
            ].isoformat()

        report_data = {
            "workflow_name": self.config.workflow_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": result.success,
            "workflow_can_continue": result.workflow_can_continue,
            "functionality_level": result.functionality_level.value,
            "statistics": {
                "files_processed": result.files_processed,
                "files_corrupted": result.files_corrupted,
                "files_recovered": result.files_recovered,
                "files_failed_recovery": result.files_failed_recovery,
                "critical_failures": len(result.critical_failures),
                "fallback_files_created": len(result.fallback_files_created),
            },
            "details": {
                "critical_failures": result.critical_failures,
                "warnings": result.warnings,
                "recovery_actions": result.recovery_actions,
                "fallback_files_created": result.fallback_files_created,
            },
            "workflow_state": workflow_state_serializable,
            "recommendations": self._generate_recommendations(result),
        }

        # Include YAML validation context if available
        if self.yaml_context:
            report_data["yaml_validation_context"] = {
                "degraded_mode": self.yaml_context.get("degraded_mode", False),
                "validation_level": self.yaml_context.get("validation_level", "unknown"),
                "integration_active": True,
            }

        return report_data

    def _generate_recommendations(self, result: CICDErrorResult) -> list[str]:
        """Generate recommendations based on error handling results.

        Args:
            result: Error handling result

        Returns:
            List of recommendation strings
        """
        recommendations = []

        if result.critical_failures:
            recommendations.append(
                "Immediate manual intervention required for critical file failures"
            )
            recommendations.append("Check backup systems and restore corrupted critical files")

        if result.files_failed_recovery > 0:
            recommendations.append(
                "Review failed recovery attempts and consider manual file restoration"
            )

        if result.functionality_level == FunctionalityLevel.EMERGENCY:
            recommendations.append(
                "System is in emergency mode - restore security data files immediately"
            )
        elif result.functionality_level == FunctionalityLevel.MINIMAL:
            recommendations.append("System is in minimal mode - consider restoring corrupted files")
        elif result.functionality_level == FunctionalityLevel.REDUCED:
            recommendations.append("System is in reduced mode - monitor for additional issues")

        if result.fallback_files_created:
            recommendations.append(
                "Fallback files were created - review and replace with proper data when possible"
            )

        if not result.success and result.workflow_can_continue:
            recommendations.append(
                "Workflow can continue with degraded functionality - monitor closely"
            )

        return recommendations


def main() -> int:
    """Main entry point for CI/CD error handling."""
    import argparse

    parser = argparse.ArgumentParser(description="CI/CD Error Handling for Security Data Files")
    parser.add_argument(
        "--workflow-name", default="cicd-workflow", help="Name of the CI/CD workflow"
    )
    parser.add_argument(
        "--files",
        nargs="*",
        help="Specific files to process (processes all security files if not specified)",
    )
    parser.add_argument(
        "--no-recovery", action="store_true", help="Disable automatic recovery attempts"
    )
    parser.add_argument(
        "--no-degradation", action="store_true", help="Disable graceful degradation"
    )
    parser.add_argument(
        "--no-monitoring", action="store_true", help="Disable monitoring and alerting"
    )
    parser.add_argument(
        "--fail-on-any-corruption",
        action="store_true",
        help="Fail workflow on any file corruption (not just critical files)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--output-report", help="Path to write CI/CD report JSON file")
    parser.add_argument(
        "--yaml-degraded-mode",
        action="store_true",
        help="Indicate YAML validation is in degraded mode",
    )
    parser.add_argument(
        "--yaml-level", help="YAML validation level (full, reduced, minimal, emergency)"
    )

    args = parser.parse_args()

    try:
        # Configure error handling
        config = CICDErrorConfig(
            workflow_name=args.workflow_name,
            enable_recovery=not args.no_recovery,
            enable_graceful_degradation=not args.no_degradation,
            enable_monitoring=not args.no_monitoring,
            fail_on_critical_corruption=True,  # Always fail on critical corruption
            verbose_logging=args.verbose,
        )

        # Override critical failure behavior if requested
        if args.fail_on_any_corruption:
            config.fail_on_critical_corruption = True

        # Initialize handler and process files
        handler = CICDErrorHandler(config)

        # Set YAML validation context if provided
        if args.yaml_degraded_mode or args.yaml_level:
            handler.yaml_context = {
                "degraded_mode": args.yaml_degraded_mode,
                "validation_level": args.yaml_level or "unknown",
            }

        result = handler.process_security_files(args.files)

        # Generate and optionally save report
        report = handler.generate_cicd_report(result)

        if args.output_report:
            with open(args.output_report, "w") as f:
                json.dump(report, f, indent=2)
            print(f"📄 Report saved to: {args.output_report}")

        # Print summary
        print("\n" + "=" * 60)
        print("🔍 CI/CD Error Handling Summary")
        print("=" * 60)
        print(f"Workflow: {config.workflow_name}")
        print(f"Success: {'✅ YES' if result.success else '❌ NO'}")
        print(f"Can Continue: {'✅ YES' if result.workflow_can_continue else '❌ NO'}")
        print(f"Functionality Level: {result.functionality_level.value.upper()}")
        print(f"Files Processed: {result.files_processed}")
        print(f"Files Corrupted: {result.files_corrupted}")
        print(f"Files Recovered: {result.files_recovered}")

        if result.critical_failures:
            print(f"❌ Critical Failures: {len(result.critical_failures)}")
            for failure in result.critical_failures:
                print(f"   - {failure}")

        if result.warnings:
            print(f"⚠️ Warnings: {len(result.warnings)}")
            if args.verbose:
                for warning in result.warnings:
                    print(f"   - {warning}")

        # Set exit code based on results
        if not result.success:
            if result.workflow_can_continue:
                print("\n⚠️ Workflow can continue with degraded functionality")
                return 0  # Allow workflow to continue
            print("\n❌ Workflow cannot continue due to critical failures")
            return 1  # Block workflow
        print("\n✅ All error handling completed successfully")
        return 0

    except KeyboardInterrupt:
        print("\n⚠️ CI/CD error handling interrupted by user", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"💥 Critical error in CI/CD error handling: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
