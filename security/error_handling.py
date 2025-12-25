#!/usr/bin/env python3
"""Comprehensive Error Handling System for Security Data Files.

This module provides robust error handling for all security data file formats
including YAML, JSON, and Markdown files. It implements corruption detection,
recovery mechanisms, and fallback strategies.

Requirements addressed: 5.1, 5.2
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import logging
from pathlib import Path
import re
import shutil
import sys

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install PyYAML", file=sys.stderr)
    sys.exit(1)


class CorruptionSeverity(Enum):
    """Severity levels for data corruption."""

    NONE = "none"
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


class RecoveryStrategy(Enum):
    """Available recovery strategies for corrupted files."""

    REPAIR_IN_PLACE = "repair_in_place"
    RESTORE_FROM_BACKUP = "restore_from_backup"
    REGENERATE_FROM_BASELINE = "regenerate_from_baseline"
    USE_FALLBACK_DATA = "use_fallback_data"
    FAIL_GRACEFULLY = "fail_gracefully"


@dataclass
class FileIntegrityInfo:
    """Information about file integrity and corruption status."""

    file_path: str
    file_type: str
    checksum: str | None = None
    size_bytes: int = 0
    last_modified: datetime | None = None
    is_corrupted: bool = False
    corruption_severity: CorruptionSeverity = CorruptionSeverity.NONE
    corruption_details: list[str] = field(default_factory=list)
    backup_available: bool = False
    backup_path: str | None = None


@dataclass
class RecoveryResult:
    """Result of a file recovery operation."""

    success: bool
    strategy_used: RecoveryStrategy
    original_file: str
    recovered_file: str | None = None
    backup_created: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    data_integrity_verified: bool = False


class SecurityDataFileError(Exception):
    """Base exception for security data file operations."""


class CorruptionDetectionError(SecurityDataFileError):
    """Exception raised when corruption detection fails."""


class RecoveryError(SecurityDataFileError):
    """Exception raised when file recovery fails."""


class SecurityFileErrorHandler:
    """Comprehensive error handler for security data files."""

    def __init__(self, backup_dir: Path | None = None, verbose: bool = False) -> None:
        """Initialize the error handler.

        Args:
            backup_dir: Directory for storing backup files (defaults to security/backups)
            verbose: Enable verbose logging
        """
        self.backup_dir = backup_dir or Path("security/backups")
        self.verbose = verbose
        self.logger = self._setup_logger()

        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Known security file patterns
        self.security_file_patterns = {
            "yaml": ["*.yml", "*.yaml"],
            "json": ["*.json"],
            "markdown": ["*.md", "*.markdown"],
        }

        # Critical security files that require special handling
        self.critical_files = {
            "remediation-timeline.yml",
            "remediation-plans.yml",
            "SECURITY_FINDINGS.md",
            "security-config.yml",
        }

    def _setup_logger(self) -> logging.Logger:
        """Set up logging for the error handler.

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger("security_error_handler")
        logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def detect_corruption(self, file_path: str | Path) -> FileIntegrityInfo:
        """Detect corruption in a security data file.

        Args:
            file_path: Path to the file to check

        Returns:
            FileIntegrityInfo with corruption details

        Raises:
            CorruptionDetectionError: If corruption detection fails
        """
        file_path = Path(file_path)

        try:
            info = FileIntegrityInfo(
                file_path=str(file_path), file_type=self._detect_file_type(file_path)
            )

            if not file_path.exists():
                info.is_corrupted = True
                info.corruption_severity = CorruptionSeverity.CRITICAL
                info.corruption_details.append("File does not exist")
                return info

            # Calculate file checksum and basic info
            info.checksum = self._calculate_checksum(file_path)
            info.size_bytes = file_path.stat().st_size
            info.last_modified = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)

            # Check for backup availability
            info.backup_available, info.backup_path = self._find_backup(file_path)

            # Perform format-specific corruption detection
            if info.file_type == "yaml":
                self._detect_yaml_corruption(file_path, info)
            elif info.file_type == "json":
                self._detect_json_corruption(file_path, info)
            elif info.file_type == "markdown":
                self._detect_markdown_corruption(file_path, info)

            # Determine overall corruption severity
            info.corruption_severity = self._assess_corruption_severity(info)

            self.logger.info(
                f"Corruption detection completed for {file_path}: {info.corruption_severity.value}"
            )

            return info

        except Exception as e:
            msg = f"Failed to detect corruption in {file_path}: {e}"
            raise CorruptionDetectionError(msg)

    def _detect_file_type(self, file_path: Path) -> str:
        """Detect the file type based on extension.

        Args:
            file_path: Path to the file

        Returns:
            File type string (yaml, json, markdown, unknown)
        """
        suffix = file_path.suffix.lower()

        if suffix in [".yml", ".yaml"]:
            return "yaml"
        if suffix == ".json":
            return "json"
        if suffix in [".md", ".markdown"]:
            return "markdown"
        return "unknown"

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file.

        Args:
            file_path: Path to the file

        Returns:
            Hexadecimal checksum string
        """
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            self.logger.warning(f"Failed to calculate checksum for {file_path}: {e}")
            return ""

    def _find_backup(self, file_path: Path) -> tuple[bool, str | None]:
        """Find the most recent backup for a file.

        Args:
            file_path: Path to the original file

        Returns:
            Tuple of (backup_exists, backup_path)
        """
        try:
            # Look for backup files in backup directory
            backup_pattern = f"{file_path.stem}.backup.*.{file_path.suffix.lstrip('.')}"
            backup_files = list(self.backup_dir.glob(backup_pattern))

            if backup_files:
                # Return the most recent backup
                latest_backup = max(backup_files, key=lambda p: p.stat().st_mtime)
                return True, str(latest_backup)

            # Also check for backups in the same directory
            same_dir_pattern = f"{file_path.stem}.backup.*{file_path.suffix}"
            same_dir_backups = list(file_path.parent.glob(same_dir_pattern))

            if same_dir_backups:
                latest_backup = max(same_dir_backups, key=lambda p: p.stat().st_mtime)
                return True, str(latest_backup)

            return False, None

        except Exception as e:
            self.logger.warning(f"Error finding backup for {file_path}: {e}")
            return False, None

    def _detect_yaml_corruption(self, file_path: Path, info: FileIntegrityInfo) -> None:
        """Detect YAML-specific corruption patterns.

        Args:
            file_path: Path to the YAML file
            info: FileIntegrityInfo to update with findings
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Check if file is empty
            if not content.strip():
                info.is_corrupted = True
                info.corruption_details.append("File is empty")
                return

            # Try to parse YAML
            try:
                yaml.safe_load(content)
            except yaml.YAMLError as e:
                info.is_corrupted = True
                error_msg = str(e)
                if hasattr(e, "problem_mark") and e.problem_mark:
                    line_num = e.problem_mark.line + 1
                    error_msg = f"Line {line_num}: {error_msg}"
                info.corruption_details.append(f"YAML parsing error: {error_msg}")

            # Check for common corruption patterns
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                # Check for inconsistent indentation
                if line.strip() and line.startswith(" "):
                    spaces = len(line) - len(line.lstrip())
                    if spaces % 2 != 0 and spaces > 1:
                        info.corruption_details.append(
                            f"Line {i}: Inconsistent indentation ({spaces} spaces)"
                        )

                # Check for unquoted special characters
                if ":" in line and any(char in line for char in "{}[]@#|>*&!%`"):
                    if not ('"' in line or "'" in line):
                        info.corruption_details.append(
                            f"Line {i}: Unquoted special characters may cause issues"
                        )

        except Exception as e:
            info.is_corrupted = True
            info.corruption_details.append(f"File reading error: {e}")

    def _detect_json_corruption(self, file_path: Path, info: FileIntegrityInfo) -> None:
        """Detect JSON-specific corruption patterns.

        Args:
            file_path: Path to the JSON file
            info: FileIntegrityInfo to update with findings
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Check if file is empty
            if not content.strip():
                info.is_corrupted = True
                info.corruption_details.append("File is empty")
                return

            # Try to parse JSON
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                info.is_corrupted = True
                error_msg = f"JSON parsing error: {e}"
                if hasattr(e, "lineno"):
                    error_msg = f"Line {e.lineno}: {error_msg}"
                info.corruption_details.append(error_msg)

            # Check for common JSON corruption patterns
            if content.count("{") != content.count("}"):
                info.corruption_details.append("Mismatched braces")

            if content.count("[") != content.count("]"):
                info.corruption_details.append("Mismatched brackets")

        except Exception as e:
            info.is_corrupted = True
            info.corruption_details.append(f"File reading error: {e}")

    def _detect_markdown_corruption(self, file_path: Path, info: FileIntegrityInfo) -> None:
        """Detect Markdown-specific corruption patterns.

        Args:
            file_path: Path to the Markdown file
            info: FileIntegrityInfo to update with findings
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Check if file is empty
            if not content.strip():
                info.is_corrupted = True
                info.corruption_details.append("File is empty")
                return

            # Basic Markdown validation
            # Check for proper header structure
            if not content.strip().startswith("#"):
                info.corruption_details.append("Missing main header")

            # Check for security findings document structure
            if "SECURITY_FINDINGS" in file_path.name:
                required_sections = [
                    "# Security Findings Summary",
                    "## Current Findings",
                    "## Remediation Summary",
                ]

                for section in required_sections:
                    if section not in content:
                        info.corruption_details.append(f"Missing section: {section}")

            # If we found issues, mark as corrupted
            if info.corruption_details:
                info.is_corrupted = True

        except Exception as e:
            info.is_corrupted = True
            info.corruption_details.append(f"File reading error: {e}")

    def _assess_corruption_severity(self, info: FileIntegrityInfo) -> CorruptionSeverity:
        """Assess the overall corruption severity based on detected issues.

        Args:
            info: FileIntegrityInfo with corruption details

        Returns:
            CorruptionSeverity level
        """
        if not info.is_corrupted:
            return CorruptionSeverity.NONE

        # File doesn't exist or is empty
        if any(
            "does not exist" in detail or "is empty" in detail for detail in info.corruption_details
        ):
            return CorruptionSeverity.CRITICAL

        # Critical files get higher severity
        filename = Path(info.file_path).name
        is_critical = filename in self.critical_files

        # Parsing errors are severe
        parsing_errors = any(
            "parsing error" in detail.lower() for detail in info.corruption_details
        )

        if parsing_errors:
            return CorruptionSeverity.SEVERE if is_critical else CorruptionSeverity.MODERATE

        # Multiple issues indicate moderate corruption
        if len(info.corruption_details) > 3:
            return CorruptionSeverity.MODERATE if is_critical else CorruptionSeverity.MINOR

        # Single issues are minor
        return CorruptionSeverity.MINOR

    def recover_file(
        self, file_path: str | Path, strategy: RecoveryStrategy | None = None
    ) -> RecoveryResult:
        """Recover a corrupted security data file.

        Args:
            file_path: Path to the corrupted file
            strategy: Recovery strategy to use (auto-selected if None)

        Returns:
            RecoveryResult with recovery details

        Raises:
            RecoveryError: If recovery fails
        """
        file_path = Path(file_path)

        try:
            # First, detect corruption to understand the problem
            integrity_info = self.detect_corruption(file_path)

            result = RecoveryResult(
                success=False,
                strategy_used=strategy or RecoveryStrategy.REPAIR_IN_PLACE,
                original_file=str(file_path),
            )

            # If file is not corrupted, no recovery needed
            if not integrity_info.is_corrupted:
                result.success = True
                result.warnings.append("File is not corrupted - no recovery needed")
                return result

            # Auto-select strategy if not provided
            if strategy is None:
                strategy = self._select_recovery_strategy(integrity_info)
                result.strategy_used = strategy

            self.logger.info(f"Attempting recovery of {file_path} using strategy: {strategy.value}")

            # Execute the selected recovery strategy
            if strategy == RecoveryStrategy.REPAIR_IN_PLACE:
                return self._repair_in_place(file_path, integrity_info, result)
            if strategy == RecoveryStrategy.RESTORE_FROM_BACKUP:
                return self._restore_from_backup(file_path, integrity_info, result)
            if strategy == RecoveryStrategy.REGENERATE_FROM_BASELINE:
                return self._regenerate_from_baseline(file_path, integrity_info, result)
            if strategy == RecoveryStrategy.USE_FALLBACK_DATA:
                return self._use_fallback_data(file_path, integrity_info, result)
            if strategy == RecoveryStrategy.FAIL_GRACEFULLY:
                return self._fail_gracefully(file_path, integrity_info, result)
            msg = f"Unknown recovery strategy: {strategy}"
            raise RecoveryError(msg)

        except Exception as e:
            msg = f"Recovery failed for {file_path}: {e}"
            raise RecoveryError(msg)

    def _select_recovery_strategy(self, integrity_info: FileIntegrityInfo) -> RecoveryStrategy:
        """Select the best recovery strategy based on corruption assessment.

        Args:
            integrity_info: File integrity information

        Returns:
            Recommended RecoveryStrategy
        """
        # If backup is available and corruption is severe, restore from backup
        if integrity_info.backup_available and integrity_info.corruption_severity in [
            CorruptionSeverity.SEVERE,
            CorruptionSeverity.CRITICAL,
        ]:
            return RecoveryStrategy.RESTORE_FROM_BACKUP

        # For moderate corruption, try repair first
        if integrity_info.corruption_severity == CorruptionSeverity.MODERATE:
            return RecoveryStrategy.REPAIR_IN_PLACE

        # For minor corruption, try repair
        if integrity_info.corruption_severity == CorruptionSeverity.MINOR:
            return RecoveryStrategy.REPAIR_IN_PLACE

        # For critical corruption without backup, regenerate
        if integrity_info.corruption_severity == CorruptionSeverity.CRITICAL:
            if integrity_info.backup_available:
                return RecoveryStrategy.RESTORE_FROM_BACKUP
            return RecoveryStrategy.REGENERATE_FROM_BASELINE

        # Default to repair
        return RecoveryStrategy.REPAIR_IN_PLACE

    def _repair_in_place(
        self, file_path: Path, integrity_info: FileIntegrityInfo, result: RecoveryResult
    ) -> RecoveryResult:
        """Attempt to repair the file in place.

        Args:
            file_path: Path to the file to repair
            integrity_info: File integrity information
            result: RecoveryResult to update

        Returns:
            Updated RecoveryResult
        """
        try:
            # Create backup before repair
            backup_path = self._create_backup(file_path)
            result.backup_created = str(backup_path)

            # Use existing repair functionality for YAML files
            if integrity_info.file_type == "yaml":
                from scripts.repair_yaml import YAMLRepairer

                repairer = YAMLRepairer(str(file_path))
                repair_success = repairer.repair_file()

                if repair_success:
                    result.success = True
                    result.recovered_file = str(file_path)
                    result.data_integrity_verified = True
                else:
                    result.errors.append("YAML repair failed")

            elif integrity_info.file_type == "json":
                # Basic JSON repair (limited capabilities)
                result.success = self._repair_json_file(file_path)
                if result.success:
                    result.recovered_file = str(file_path)

            elif integrity_info.file_type == "markdown":
                # Basic Markdown repair
                result.success = self._repair_markdown_file(file_path)
                if result.success:
                    result.recovered_file = str(file_path)

            else:
                result.errors.append(
                    f"Repair not supported for file type: {integrity_info.file_type}"
                )

            return result

        except Exception as e:
            result.errors.append(f"Repair in place failed: {e}")
            return result

    def _restore_from_backup(
        self, file_path: Path, integrity_info: FileIntegrityInfo, result: RecoveryResult
    ) -> RecoveryResult:
        """Restore file from backup.

        Args:
            file_path: Path to the file to restore
            integrity_info: File integrity information
            result: RecoveryResult to update

        Returns:
            Updated RecoveryResult
        """
        try:
            if not integrity_info.backup_available or not integrity_info.backup_path:
                result.errors.append("No backup available for restoration")
                return result

            backup_path = Path(integrity_info.backup_path)

            # Verify backup integrity before restoration
            backup_integrity = self.detect_corruption(backup_path)
            if backup_integrity.is_corrupted:
                result.errors.append("Backup file is also corrupted")
                return result

            # Create backup of current corrupted file
            corrupted_backup = self._create_backup(file_path, suffix="corrupted")
            result.backup_created = str(corrupted_backup)

            # Restore from backup
            shutil.copy2(backup_path, file_path)

            result.success = True
            result.recovered_file = str(file_path)
            result.data_integrity_verified = True

            self.logger.info(f"Successfully restored {file_path} from backup {backup_path}")

            return result

        except Exception as e:
            result.errors.append(f"Backup restoration failed: {e}")
            return result

    def _regenerate_from_baseline(
        self, file_path: Path, integrity_info: FileIntegrityInfo, result: RecoveryResult
    ) -> RecoveryResult:
        """Regenerate file from baseline data.

        Args:
            file_path: Path to the file to regenerate
            integrity_info: File integrity information
            result: RecoveryResult to update

        Returns:
            Updated RecoveryResult
        """
        try:
            # Create backup of corrupted file
            if file_path.exists():
                corrupted_backup = self._create_backup(file_path, suffix="corrupted")
                result.backup_created = str(corrupted_backup)

            # Generate baseline content based on file type and name
            baseline_content = self._generate_baseline_content(file_path, integrity_info.file_type)

            # Write baseline content to file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(baseline_content)

            result.success = True
            result.recovered_file = str(file_path)
            result.warnings.append("File regenerated from baseline - original data may be lost")

            self.logger.info(f"Successfully regenerated {file_path} from baseline")

            return result

        except Exception as e:
            result.errors.append(f"Baseline regeneration failed: {e}")
            return result

    def _use_fallback_data(
        self, file_path: Path, integrity_info: FileIntegrityInfo, result: RecoveryResult
    ) -> RecoveryResult:
        """Use fallback data for the corrupted file.

        Args:
            file_path: Path to the file
            integrity_info: File integrity information
            result: RecoveryResult to update

        Returns:
            Updated RecoveryResult
        """
        try:
            # Create a fallback file with minimal valid data
            fallback_path = file_path.with_suffix(".fallback" + file_path.suffix)
            fallback_content = self._generate_fallback_content(file_path, integrity_info.file_type)

            with open(fallback_path, "w", encoding="utf-8") as f:
                f.write(fallback_content)

            result.success = True
            result.recovered_file = str(fallback_path)
            result.warnings.append(f"Created fallback file: {fallback_path}")
            result.warnings.append("Original file remains corrupted - using fallback data")

            return result

        except Exception as e:
            result.errors.append(f"Fallback data creation failed: {e}")
            return result

    def _fail_gracefully(
        self, file_path: Path, integrity_info: FileIntegrityInfo, result: RecoveryResult
    ) -> RecoveryResult:
        """Fail gracefully with detailed error information.

        Args:
            file_path: Path to the file
            integrity_info: File integrity information
            result: RecoveryResult to update

        Returns:
            Updated RecoveryResult
        """
        result.success = False
        result.errors.append(f"File {file_path} is corrupted and cannot be recovered")
        result.errors.extend(integrity_info.corruption_details)
        result.warnings.append("Manual intervention required")

        if integrity_info.backup_available:
            result.warnings.append(f"Backup available at: {integrity_info.backup_path}")

        return result

    def _create_backup(self, file_path: Path, suffix: str = "recovery") -> Path:
        """Create a backup of a file.

        Args:
            file_path: Path to the file to backup
            suffix: Suffix to add to backup filename

        Returns:
            Path to the created backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{file_path.stem}.{suffix}.{timestamp}{file_path.suffix}"
        backup_path = self.backup_dir / backup_filename

        shutil.copy2(file_path, backup_path)
        self.logger.info(f"Created backup: {backup_path}")

        return backup_path

    def _repair_json_file(self, file_path: Path) -> bool:
        """Attempt basic JSON file repair.

        Args:
            file_path: Path to the JSON file

        Returns:
            True if repair was successful, False otherwise
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Try to fix common JSON issues
            # Remove trailing commas
            content = re.sub(r",(\s*[}\]])", r"\1", content)

            # Try to parse the repaired content
            json.loads(content)

            # Write back the repaired content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return True

        except Exception:
            return False

    def _repair_markdown_file(self, file_path: Path) -> bool:
        """Attempt basic Markdown file repair.

        Args:
            file_path: Path to the Markdown file

        Returns:
            True if repair was successful, False otherwise
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Add main header if missing
            if not content.strip().startswith("#"):
                filename_title = file_path.stem.replace("_", " ").replace("-", " ").title()
                content = f"# {filename_title}\n\n{content}"

            # Write back the repaired content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return True

        except Exception:
            return False

    def _generate_baseline_content(self, file_path: Path, file_type: str) -> str:
        """Generate baseline content for a file.

        Args:
            file_path: Path to the file
            file_type: Type of the file (yaml, json, markdown)

        Returns:
            Baseline content as string
        """
        filename = file_path.name.lower()
        timestamp = datetime.now(timezone.utc).isoformat()

        if file_type == "yaml":
            if "timeline" in filename:
                baseline_data = {
                    "timeline": [
                        {
                            "timestamp": timestamp,
                            "action": "baseline_regenerated",
                            "finding_id": "SYSTEM",
                            "description": "File regenerated from baseline due to corruption",
                            "user": "system",
                        }
                    ],
                    "metadata": {
                        "generated": timestamp,
                        "mode": "baseline_regeneration",
                        "original_file": str(file_path),
                    },
                }
            elif "findings" in filename or "plans" in filename:
                baseline_data = {
                    "findings": [],
                    "metadata": {
                        "generated": timestamp,
                        "mode": "baseline_regeneration",
                        "total_findings": 0,
                    },
                }
            else:
                baseline_data = {
                    "generated": timestamp,
                    "mode": "baseline_regeneration",
                    "original_file": str(file_path),
                    "data": {},
                }

            return yaml.dump(baseline_data, default_flow_style=False)

        if file_type == "json":
            baseline_data = {
                "generated": timestamp,
                "mode": "baseline_regeneration",
                "original_file": str(file_path),
                "data": {},
            }
            return json.dumps(baseline_data, indent=2)

        if file_type == "markdown":
            title = file_path.stem.replace("_", " ").replace("-", " ").title()
            return f"""# {title}

**Generated**: {timestamp}
**Mode**: Baseline Regeneration
**Original File**: {file_path}

This file was regenerated from baseline due to corruption in the original file.
Original data may have been lost. Please restore from backup if available.

## Status

- File regenerated successfully
- Original data not preserved
- Manual review recommended
"""

        return (
            f"# Generated baseline content\n\nGenerated: {timestamp}\nOriginal file: {file_path}\n"
        )

    def _generate_fallback_content(self, file_path: Path, file_type: str) -> str:
        """Generate fallback content for a file.

        Args:
            file_path: Path to the file
            file_type: Type of the file (yaml, json, markdown)

        Returns:
            Fallback content as string
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        if file_type == "yaml":
            fallback_data = {
                "fallback_mode": True,
                "generated": timestamp,
                "original_file": str(file_path),
                "warning": "This is fallback data - original file is corrupted",
                "data": {},
            }
            return yaml.dump(fallback_data, default_flow_style=False)

        if file_type == "json":
            fallback_data = {
                "fallback_mode": True,
                "generated": timestamp,
                "original_file": str(file_path),
                "warning": "This is fallback data - original file is corrupted",
                "data": {},
            }
            return json.dumps(fallback_data, indent=2)

        if file_type == "markdown":
            title = file_path.stem.replace("_", " ").replace("-", " ").title()
            return f"""# {title} (Fallback)

**Generated**: {timestamp}
**Mode**: Fallback Data
**Original File**: {file_path}

⚠️ **WARNING**: This is fallback data. The original file is corrupted and could not be recovered.

## Status

- Original file is corrupted
- Using fallback data for continued operation
- Manual intervention required to restore original data

## Next Steps

1. Check for available backups
2. Attempt manual recovery of original file
3. Regenerate data from source systems if possible
"""

        return f"# Fallback content\n\nGenerated: {timestamp}\nOriginal file: {file_path}\nWarning: Original file corrupted\n"


# Convenience functions for common operations
def detect_file_corruption(file_path: str | Path, verbose: bool = False) -> FileIntegrityInfo:
    """Detect corruption in a security data file.

    Args:
        file_path: Path to the file to check
        verbose: Enable verbose logging

    Returns:
        FileIntegrityInfo with corruption details
    """
    handler = SecurityFileErrorHandler(verbose=verbose)
    return handler.detect_corruption(file_path)


def recover_corrupted_file(
    file_path: str | Path, strategy: RecoveryStrategy | None = None, verbose: bool = False
) -> RecoveryResult:
    """Recover a corrupted security data file.

    Args:
        file_path: Path to the corrupted file
        strategy: Recovery strategy to use (auto-selected if None)
        verbose: Enable verbose logging

    Returns:
        RecoveryResult with recovery details
    """
    handler = SecurityFileErrorHandler(verbose=verbose)
    return handler.recover_file(file_path, strategy)


def verify_file_integrity(file_path: str | Path) -> bool:
    """Quick check if a file has integrity issues.

    Args:
        file_path: Path to the file to check

    Returns:
        True if file is intact, False if corrupted
    """
    try:
        info = detect_file_corruption(file_path)
        return not info.is_corrupted
    except Exception:
        return False
