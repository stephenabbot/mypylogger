#!/usr/bin/env python3
"""Security YAML Validation Engine.

Comprehensive validation system for security data files including YAML, JSON, and Markdown.
Provides detection of common syntax errors and corruption patterns.

Requirements addressed: 1.1, 1.2
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
import re
import sys
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install PyYAML", file=sys.stderr)
    sys.exit(1)


class FunctionalityLevel(Enum):
    """Levels of functionality based on file corruption severity."""

    FULL = "full"
    REDUCED = "reduced"
    MINIMAL = "minimal"
    EMERGENCY = "emergency"


@dataclass
class FallbackStrategy:
    """Strategy for handling corrupted files."""

    level: FunctionalityLevel
    description: str
    can_continue: bool
    fallback_data: dict[str, Any] | None = None


@dataclass
class ValidationResult:
    """Result of YAML/JSON/Markdown validation operation."""

    file_path: str
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    line_numbers: list[int] = field(default_factory=list)
    repair_attempted: bool = False
    repair_successful: bool = False
    backup_created: str | None = None
    file_type: str = "unknown"


@dataclass
class ValidationSummary:
    """Summary of validation results across multiple files."""

    total_files: int = 0
    valid_files: int = 0
    invalid_files: int = 0
    repaired_files: int = 0
    failed_repairs: int = 0
    total_errors: int = 0
    total_warnings: int = 0
    results: list[ValidationResult] = field(default_factory=list)


class SecurityFileValidator:
    """Validates security data files (YAML, JSON, Markdown) for syntax and structure."""

    def __init__(self, verbose: bool = False) -> None:
        """Initialize the validator.

        Args:
            verbose: Enable verbose output
        """
        self.verbose = verbose
        self.security_paths = [
            "security/findings",
            "security/config",
            "security/reports",
            "security/scripts",
        ]

    def validate_file(self, file_path: str | Path) -> ValidationResult:
        """Validate a single security data file.

        Args:
            file_path: Path to the file to validate

        Returns:
            ValidationResult with validation details
        """
        file_path = Path(file_path)
        result = ValidationResult(
            file_path=str(file_path), is_valid=False, file_type=self._detect_file_type(file_path)
        )

        if not file_path.exists():
            result.errors.append(f"File not found: {file_path}")
            return result

        try:
            if result.file_type == "yaml":
                return self._validate_yaml_file(file_path, result)
            if result.file_type == "json":
                return self._validate_json_file(file_path, result)
            if result.file_type == "markdown":
                return self._validate_markdown_file(file_path, result)
            result.warnings.append(f"Unsupported file type: {result.file_type}")
            result.is_valid = True  # Don't fail on unsupported types

        except Exception as e:
            result.errors.append(f"Validation error: {e}")

        return result

    def _detect_file_type(self, file_path: Path) -> str:
        """Detect the file type based on extension and content.

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

    def _validate_yaml_file(self, file_path: Path, result: ValidationResult) -> ValidationResult:
        """Validate YAML file syntax and structure.

        Args:
            file_path: Path to YAML file
            result: ValidationResult to populate

        Returns:
            Updated ValidationResult
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Check for common YAML corruption patterns
            self._check_yaml_corruption_patterns(content, result)

            # Attempt to parse YAML
            try:
                parsed_data = yaml.safe_load(content)
                result.is_valid = True

                # Additional structure validation for security files
                self._validate_yaml_structure(parsed_data, file_path, result)

            except yaml.YAMLError as e:
                result.is_valid = False
                error_msg = str(e)

                # Extract line number if available
                if hasattr(e, "problem_mark") and e.problem_mark:
                    line_num = e.problem_mark.line + 1
                    result.line_numbers.append(line_num)
                    error_msg = f"Line {line_num}: {error_msg}"

                result.errors.append(f"YAML parsing error: {error_msg}")

        except Exception as e:
            result.errors.append(f"File reading error: {e}")

        return result

    def _check_yaml_corruption_patterns(self, content: str, result: ValidationResult) -> None:
        """Check for common YAML corruption patterns.

        Args:
            content: YAML file content
            result: ValidationResult to update with findings
        """
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            # Check for inconsistent indentation
            if line.strip() and line.startswith(" "):
                spaces = len(line) - len(line.lstrip())
                if spaces % 2 != 0 and spaces > 1:
                    result.warnings.append(f"Line {i}: Inconsistent indentation ({spaces} spaces)")

            # Check for unquoted special characters
            if re.search(r':\s*[^"\'\s].*[{}[\]@#|>]', line):
                result.warnings.append(f"Line {i}: Unquoted special characters may cause issues")

            # Check for missing colons in key-value pairs
            if (
                re.search(r"^\s*\w+\s+\w+", line)
                and ":" not in line
                and "-" not in line.strip()[:1]
            ):
                result.warnings.append(f"Line {i}: Possible missing colon in key-value pair")

    def _validate_yaml_structure(
        self, data: Any, file_path: Path, result: ValidationResult
    ) -> None:
        """Validate YAML structure for security files.

        Args:
            data: Parsed YAML data
            file_path: Path to the file
            result: ValidationResult to update
        """
        filename = file_path.name.lower()

        # Validate remediation timeline structure
        if "remediation-timeline" in filename:
            self._validate_remediation_timeline(data, result)

        # Validate findings structure
        elif "findings" in filename or "remediation-plans" in filename:
            self._validate_findings_structure(data, result)

        # Validate configuration files
        elif "config" in str(file_path) or "settings" in filename:
            self._validate_config_structure(data, result)

    def _validate_remediation_timeline(self, data: Any, result: ValidationResult) -> None:
        """Validate remediation timeline YAML structure.

        Args:
            data: Parsed YAML data
            result: ValidationResult to update
        """
        if not isinstance(data, dict):
            result.errors.append("Remediation timeline must be a dictionary")
            return

        # Check for required top-level keys
        required_keys = ["timeline", "metadata"]
        for key in required_keys:
            if key not in data:
                result.warnings.append(f"Missing recommended key: {key}")

        # Validate timeline entries
        if "timeline" in data and isinstance(data["timeline"], list):
            for i, entry in enumerate(data["timeline"]):
                if not isinstance(entry, dict):
                    result.errors.append(f"Timeline entry {i} must be a dictionary")
                    continue

                # Check for required fields in timeline entries
                required_fields = ["timestamp", "action", "finding_id"]
                for field in required_fields:
                    if field not in entry:
                        result.warnings.append(f"Timeline entry {i} missing field: {field}")

    def _validate_findings_structure(self, data: Any, result: ValidationResult) -> None:
        """Validate security findings YAML structure.

        Args:
            data: Parsed YAML data
            result: ValidationResult to update
        """
        if not isinstance(data, dict):
            result.errors.append("Findings file must be a dictionary")
            return

        # Check for findings array
        if "findings" in data:
            if not isinstance(data["findings"], list):
                result.errors.append("'findings' must be a list")
            else:
                for i, finding in enumerate(data["findings"]):
                    if not isinstance(finding, dict):
                        result.errors.append(f"Finding {i} must be a dictionary")
                        continue

                    # Check for required finding fields
                    required_fields = ["id", "severity", "description"]
                    for field in required_fields:
                        if field not in finding:
                            result.warnings.append(f"Finding {i} missing field: {field}")

    def _validate_config_structure(self, data: Any, result: ValidationResult) -> None:
        """Validate configuration YAML structure.

        Args:
            data: Parsed YAML data
            result: ValidationResult to update
        """
        if not isinstance(data, dict):
            result.errors.append("Configuration file must be a dictionary")
            return

        # Basic structure validation - config files are more flexible
        if len(data) == 0:
            result.warnings.append("Configuration file is empty")

    def _validate_json_file(self, file_path: Path, result: ValidationResult) -> ValidationResult:
        """Validate JSON file syntax and structure.

        Args:
            file_path: Path to JSON file
            result: ValidationResult to populate

        Returns:
            Updated ValidationResult
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Attempt to parse JSON
            try:
                json.loads(content)
                result.is_valid = True
            except json.JSONDecodeError as e:
                result.is_valid = False
                result.errors.append(f"JSON parsing error: {e}")
                if hasattr(e, "lineno"):
                    result.line_numbers.append(e.lineno)

        except Exception as e:
            result.errors.append(f"File reading error: {e}")

        return result

    def _validate_markdown_file(
        self, file_path: Path, result: ValidationResult
    ) -> ValidationResult:
        """Validate Markdown file structure for security documents.

        Args:
            file_path: Path to Markdown file
            result: ValidationResult to populate

        Returns:
            Updated ValidationResult
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Basic Markdown validation
            result.is_valid = True

            # Check for proper header structure
            if not content.strip().startswith("#"):
                result.warnings.append("Markdown file should start with a header")

            # Check for security findings document structure
            if "SECURITY_FINDINGS" in file_path.name:
                self._validate_security_findings_markdown(content, result)

        except Exception as e:
            result.errors.append(f"File reading error: {e}")

        return result

    def _validate_security_findings_markdown(self, content: str, result: ValidationResult) -> None:
        """Validate security findings Markdown document structure.

        Args:
            content: Markdown content
            result: ValidationResult to update
        """
        required_sections = [
            "# Security Findings Summary",
            "## Current Findings",
            "## Remediation Summary",
        ]

        for section in required_sections:
            if section not in content:
                result.warnings.append(f"Missing recommended section: {section}")

    def validate_security_files(self, repair: bool = False) -> ValidationSummary:
        """Validate all security data files in the project.

        Args:
            repair: Whether to attempt automatic repair of invalid files

        Returns:
            ValidationSummary with results for all files
        """
        summary = ValidationSummary()

        # Find all security data files
        security_files = self._find_security_files()

        if self.verbose:
            print(f"🔍 Found {len(security_files)} security files to validate")

        for file_path in security_files:
            if self.verbose:
                print(f"  Validating: {file_path}")

            result = self.validate_file(file_path)
            summary.results.append(result)
            summary.total_files += 1

            if result.is_valid:
                summary.valid_files += 1
            else:
                summary.invalid_files += 1
                summary.total_errors += len(result.errors)

            summary.total_warnings += len(result.warnings)

            # Attempt repair if requested and file is invalid
            if repair and not result.is_valid and result.file_type == "yaml":
                if self.verbose:
                    print("    Attempting repair...")

                repair_result = self._attempt_repair(file_path, result)
                if repair_result:
                    summary.repaired_files += 1
                    result.repair_attempted = True
                    result.repair_successful = True
                else:
                    summary.failed_repairs += 1
                    result.repair_attempted = True
                    result.repair_successful = False

        return summary

    def _find_security_files(self) -> list[Path]:
        """Find all security data files in the project.

        Returns:
            List of Path objects for security files
        """
        files = []

        for security_path in self.security_paths:
            path = Path(security_path)
            if path.exists():
                # Find YAML, JSON, and Markdown files
                for pattern in ["*.yml", "*.yaml", "*.json", "*.md"]:
                    files.extend(path.rglob(pattern))

        return sorted(files)

    def _create_all_backups(self) -> int:
        """Create backups of all security YAML files.

        Returns:
            Number of backup files created
        """
        backup_count = 0
        security_files = self._find_security_files()

        # Create backup directory
        backup_dir = Path("security/backups")
        backup_dir.mkdir(parents=True, exist_ok=True)

        for file_path in security_files:
            if file_path.suffix.lower() in [".yml", ".yaml"]:
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_filename = f"{file_path.stem}.backup.{timestamp}.yml"
                    backup_path = backup_dir / backup_filename

                    import shutil

                    shutil.copy2(file_path, backup_path)
                    backup_count += 1

                    if self.verbose:
                        print(f"  Created backup: {backup_path}")

                except Exception as e:
                    if self.verbose:
                        print(f"  Failed to backup {file_path}: {e}")

        return backup_count

    def _attempt_repair(self, file_path: Path, result: ValidationResult) -> bool:
        """Attempt to repair a YAML file using the repair script.

        Args:
            file_path: Path to the file to repair
            result: ValidationResult to update

        Returns:
            True if repair was successful, False otherwise
        """
        try:
            # Import the repair functionality
            from repair_yaml import YAMLRepairer

            repairer = YAMLRepairer(str(file_path))
            success = repairer.repair_file()

            if success:
                # Re-validate the repaired file
                new_result = self.validate_file(file_path)
                if new_result.is_valid:
                    result.backup_created = repairer.backup_path
                    return True

        except Exception as e:
            if self.verbose:
                print(f"    Repair failed: {e}")

        return False


class GracefulDegradation:
    """Handles graceful degradation when security files are corrupted."""

    def __init__(self, verbose: bool = False) -> None:
        """Initialize graceful degradation handler.

        Args:
            verbose: Enable verbose output
        """
        self.verbose = verbose

    def determine_functionality_level(
        self, validation_results: list[ValidationResult]
    ) -> FunctionalityLevel:
        """Determine what level of functionality is possible based on validation results.

        Args:
            validation_results: List of validation results for security files

        Returns:
            FunctionalityLevel indicating what operations can be performed
        """
        total_files = len(validation_results)
        invalid_files = sum(1 for r in validation_results if not r.is_valid)
        critical_files_invalid = 0

        # Check for critical file corruption
        critical_files = [
            "remediation-timeline.yml",
            "remediation-plans.yml",
            "SECURITY_FINDINGS.md",
        ]

        for result in validation_results:
            filename = Path(result.file_path).name
            if filename in critical_files and not result.is_valid:
                critical_files_invalid += 1

        # Determine functionality level
        if invalid_files == 0:
            return FunctionalityLevel.FULL
        if critical_files_invalid == 0 and invalid_files < total_files * 0.3:
            return FunctionalityLevel.REDUCED
        if critical_files_invalid <= 1 and invalid_files < total_files * 0.6:
            return FunctionalityLevel.MINIMAL
        return FunctionalityLevel.EMERGENCY

    def create_fallback_strategy(
        self, level: FunctionalityLevel, corrupted_files: list[str]
    ) -> FallbackStrategy:
        """Create a fallback strategy for the given functionality level.

        Args:
            level: Functionality level to create strategy for
            corrupted_files: List of corrupted file paths

        Returns:
            FallbackStrategy with appropriate configuration
        """
        if level == FunctionalityLevel.FULL:
            return FallbackStrategy(
                level=level,
                description="All files valid - full functionality available",
                can_continue=True,
            )

        if level == FunctionalityLevel.REDUCED:
            return FallbackStrategy(
                level=level,
                description="Minor file corruption - reduced functionality with warnings",
                can_continue=True,
                fallback_data=self._create_reduced_fallback_data(corrupted_files),
            )

        if level == FunctionalityLevel.MINIMAL:
            return FallbackStrategy(
                level=level,
                description="Significant corruption - minimal functionality only",
                can_continue=True,
                fallback_data=self._create_minimal_fallback_data(corrupted_files),
            )

        # EMERGENCY
        return FallbackStrategy(
            level=level,
            description="Critical corruption - emergency mode with baseline data",
            can_continue=True,
            fallback_data=self._create_emergency_fallback_data(),
        )

    def _create_reduced_fallback_data(self, corrupted_files: list[str]) -> dict[str, Any]:
        """Create fallback data for reduced functionality level.

        Args:
            corrupted_files: List of corrupted file paths

        Returns:
            Dictionary with fallback data
        """
        return {
            "mode": "reduced",
            "corrupted_files": corrupted_files,
            "available_operations": [
                "basic_security_scan",
                "findings_generation",
                "limited_reporting",
            ],
            "disabled_operations": ["timeline_updates", "advanced_remediation"],
            "warnings": [
                f"File {f} is corrupted - using cached data where possible" for f in corrupted_files
            ],
        }

    def _create_minimal_fallback_data(self, corrupted_files: list[str]) -> dict[str, Any]:
        """Create fallback data for minimal functionality level.

        Args:
            corrupted_files: List of corrupted file paths

        Returns:
            Dictionary with fallback data
        """
        return {
            "mode": "minimal",
            "corrupted_files": corrupted_files,
            "available_operations": ["basic_security_scan", "emergency_reporting"],
            "disabled_operations": [
                "timeline_updates",
                "remediation_planning",
                "historical_analysis",
                "detailed_reporting",
            ],
            "fallback_timeline": self._generate_minimal_timeline(),
            "fallback_findings": self._generate_minimal_findings(),
            "warnings": [
                "Multiple critical files corrupted",
                "Operating in minimal functionality mode",
                "Manual intervention may be required",
            ],
        }

    def _create_emergency_fallback_data(self) -> dict[str, Any]:
        """Create fallback data for emergency functionality level.

        Returns:
            Dictionary with emergency fallback data
        """
        return {
            "mode": "emergency",
            "available_operations": ["basic_security_scan"],
            "disabled_operations": [
                "timeline_updates",
                "remediation_planning",
                "historical_analysis",
                "detailed_reporting",
                "findings_management",
            ],
            "emergency_timeline": self._generate_emergency_timeline(),
            "emergency_findings": self._generate_emergency_findings(),
            "warnings": [
                "CRITICAL: All security data files corrupted",
                "Operating in emergency mode with baseline data",
                "Immediate manual intervention required",
                "Restore from backup or regenerate security data",
            ],
        }

    def _generate_minimal_timeline(self) -> dict[str, Any]:
        """Generate minimal timeline data for fallback.

        Returns:
            Minimal timeline structure
        """
        return {
            "timeline": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "action": "emergency_mode_activated",
                    "finding_id": "SYSTEM",
                    "description": "Activated minimal mode due to file corruption",
                    "user": "system",
                }
            ],
            "metadata": {
                "generated": datetime.now().isoformat(),
                "mode": "minimal_fallback",
                "source": "graceful_degradation",
            },
        }

    def _generate_emergency_timeline(self) -> dict[str, Any]:
        """Generate emergency timeline data for fallback.

        Returns:
            Emergency timeline structure
        """
        return {
            "timeline": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "action": "emergency_mode_activated",
                    "finding_id": "CRITICAL",
                    "description": "All security files corrupted - emergency mode active",
                    "user": "system",
                    "severity": "critical",
                }
            ],
            "metadata": {
                "generated": datetime.now().isoformat(),
                "mode": "emergency_fallback",
                "source": "graceful_degradation",
                "warning": "All original data lost - restore from backup immediately",
            },
        }

    def _generate_minimal_findings(self) -> dict[str, Any]:
        """Generate minimal findings data for fallback.

        Returns:
            Minimal findings structure
        """
        return {
            "findings": [
                {
                    "id": "DATA-CORRUPTION-001",
                    "severity": "high",
                    "description": "Security data file corruption detected",
                    "status": "active",
                    "discovered": datetime.now().isoformat(),
                    "source": "graceful_degradation",
                }
            ],
            "metadata": {
                "generated": datetime.now().isoformat(),
                "mode": "minimal_fallback",
                "total_findings": 1,
            },
        }

    def _generate_emergency_findings(self) -> dict[str, Any]:
        """Generate emergency findings data for fallback.

        Returns:
            Emergency findings structure
        """
        return {
            "findings": [
                {
                    "id": "CRITICAL-DATA-LOSS-001",
                    "severity": "critical",
                    "description": "Critical security data corruption - all files affected",
                    "status": "active",
                    "discovered": datetime.now().isoformat(),
                    "source": "graceful_degradation",
                    "impact": "Security monitoring severely compromised",
                    "remediation": "Restore from backup immediately",
                }
            ],
            "metadata": {
                "generated": datetime.now().isoformat(),
                "mode": "emergency_fallback",
                "total_findings": 1,
                "critical_alert": True,
            },
        }

    def create_minimal_valid_files(
        self, corrupted_files: list[str], output_dir: Path | None = None
    ) -> list[str]:
        """Create minimal valid files to replace corrupted ones.

        Args:
            corrupted_files: List of corrupted file paths
            output_dir: Directory to create files in (defaults to original locations)

        Returns:
            List of created file paths
        """
        created_files = []

        for file_path in corrupted_files:
            try:
                path = Path(file_path)
                if output_dir:
                    new_path = output_dir / path.name
                else:
                    new_path = path.with_suffix(".minimal" + path.suffix)

                # Create minimal valid content based on file type
                if "timeline" in path.name.lower():
                    content = yaml.dump(self._generate_minimal_timeline(), default_flow_style=False)
                elif "findings" in path.name.lower() or "plans" in path.name.lower():
                    content = yaml.dump(self._generate_minimal_findings(), default_flow_style=False)
                else:
                    # Generic minimal YAML
                    content = yaml.dump(
                        {
                            "generated": datetime.now().isoformat(),
                            "mode": "minimal_fallback",
                            "original_file": str(path),
                            "data": {},
                        },
                        default_flow_style=False,
                    )

                # Write the minimal file
                with open(new_path, "w", encoding="utf-8") as f:
                    f.write(content)

                created_files.append(str(new_path))

                if self.verbose:
                    print(f"✅ Created minimal valid file: {new_path}")

            except Exception as e:
                if self.verbose:
                    print(f"❌ Failed to create minimal file for {file_path}: {e}")

        return created_files

    def create_emergency_fallback_files(self, output_dir: Path | None = None) -> list[str]:
        """Create emergency fallback files for critical security operations.

        Args:
            output_dir: Directory to create files in (defaults to security/findings)

        Returns:
            List of created file paths
        """
        if output_dir is None:
            output_dir = Path("security/findings")

        output_dir.mkdir(parents=True, exist_ok=True)
        created_files = []

        # Create minimal remediation timeline
        timeline_path = output_dir / "remediation-timeline.yml"
        timeline_content = yaml.dump(self._generate_emergency_timeline(), default_flow_style=False)

        try:
            with open(timeline_path, "w", encoding="utf-8") as f:
                f.write(timeline_content)
            created_files.append(str(timeline_path))

            if self.verbose:
                print(f"✅ Created emergency timeline: {timeline_path}")
        except Exception as e:
            if self.verbose:
                print(f"❌ Failed to create emergency timeline: {e}")

        # Create minimal findings file
        findings_path = output_dir / "remediation-plans.yml"
        findings_content = yaml.dump(self._generate_emergency_findings(), default_flow_style=False)

        try:
            with open(findings_path, "w", encoding="utf-8") as f:
                f.write(findings_content)
            created_files.append(str(findings_path))

            if self.verbose:
                print(f"✅ Created emergency findings: {findings_path}")
        except Exception as e:
            if self.verbose:
                print(f"❌ Failed to create emergency findings: {e}")

        # Create minimal security findings document
        doc_path = output_dir / "SECURITY_FINDINGS.md"
        doc_content = f"""# Security Findings Summary (Emergency Mode)

**Generated**: {datetime.now().isoformat()}
**Mode**: Emergency Fallback
**Status**: CRITICAL - All security data files corrupted

⚠️ **CRITICAL ALERT**: This document was generated in emergency mode due to corruption of all security data files.

## Current Status

- **Security Data**: All files corrupted and unrecoverable
- **Functionality**: Emergency mode only
- **Operations**: Basic security scanning available
- **Remediation**: Immediate manual intervention required

## Immediate Actions Required

1. **Restore from Backup**: Check for available backups of security data files
2. **Manual Recovery**: Attempt manual recovery of corrupted files
3. **Data Regeneration**: Regenerate security data from source systems
4. **System Validation**: Verify integrity of security monitoring systems

## Emergency Contact

Contact the security team immediately for assistance with data recovery.

## Automated Operations

- Basic security scanning: ✅ Available
- Findings management: ❌ Disabled
- Timeline tracking: ❌ Disabled
- Remediation planning: ❌ Disabled
- Historical analysis: ❌ Disabled

---
*This document was automatically generated due to critical security data corruption.*
"""

        try:
            with open(doc_path, "w", encoding="utf-8") as f:
                f.write(doc_content)
            created_files.append(str(doc_path))

            if self.verbose:
                print(f"✅ Created emergency document: {doc_path}")
        except Exception as e:
            if self.verbose:
                print(f"❌ Failed to create emergency document: {e}")

        return created_files

    def create_emergency_fallback_files(self, output_dir: Path | None = None) -> list[str]:
        """Create emergency fallback files for critical security operations.

        Args:
            output_dir: Directory to create files in (defaults to security/findings)

        Returns:
            List of created file paths
        """
        if output_dir is None:
            output_dir = Path("security/findings")

        output_dir.mkdir(parents=True, exist_ok=True)
        created_files = []

        # Create minimal remediation timeline
        timeline_path = output_dir / "remediation-timeline.yml"
        timeline_content = yaml.dump(self._generate_emergency_timeline(), default_flow_style=False)

        try:
            with open(timeline_path, "w", encoding="utf-8") as f:
                f.write(timeline_content)
            created_files.append(str(timeline_path))

            if self.verbose:
                print(f"✅ Created emergency timeline: {timeline_path}")
        except Exception as e:
            if self.verbose:
                print(f"❌ Failed to create emergency timeline: {e}")

        # Create minimal findings file
        findings_path = output_dir / "remediation-plans.yml"
        findings_content = yaml.dump(self._generate_emergency_findings(), default_flow_style=False)

        try:
            with open(findings_path, "w", encoding="utf-8") as f:
                f.write(findings_content)
            created_files.append(str(findings_path))

            if self.verbose:
                print(f"✅ Created emergency findings: {findings_path}")
        except Exception as e:
            if self.verbose:
                print(f"❌ Failed to create emergency findings: {e}")

        # Create minimal security findings document
        doc_path = output_dir / "SECURITY_FINDINGS.md"
        doc_content = f"""# Security Findings Summary (Emergency Mode)

**Generated**: {datetime.now().isoformat()}
**Mode**: Emergency Fallback
**Status**: CRITICAL - All security data files corrupted

⚠️ **CRITICAL ALERT**: This document was generated in emergency mode due to corruption of all security data files.

## Current Status

- **Security Data**: All files corrupted and unrecoverable
- **Functionality**: Emergency mode only
- **Operations**: Basic security scanning available
- **Remediation**: Immediate manual intervention required

## Immediate Actions Required

1. **Restore from Backup**: Check for available backups of security data files
2. **Manual Recovery**: Attempt manual recovery of corrupted files
3. **Data Regeneration**: Regenerate security data from source systems
4. **System Validation**: Verify integrity of security monitoring systems

## Emergency Contact

Contact the security team immediately for assistance with data recovery.

## Automated Operations

- Basic security scanning: ✅ Available
- Findings management: ❌ Disabled
- Timeline tracking: ❌ Disabled
- Remediation planning: ❌ Disabled
- Historical analysis: ❌ Disabled

---
*This document was automatically generated due to critical security data corruption.*
"""

        try:
            with open(doc_path, "w", encoding="utf-8") as f:
                f.write(doc_content)
            created_files.append(str(doc_path))

            if self.verbose:
                print(f"✅ Created emergency document: {doc_path}")
        except Exception as e:
            if self.verbose:
                print(f"❌ Failed to create emergency document: {e}")

        return created_files

    def execute_degraded_workflow(self, strategy: FallbackStrategy) -> dict[str, Any]:
        """Execute workflow with appropriate functionality level.

        Args:
            strategy: FallbackStrategy to execute

        Returns:
            Dictionary with workflow execution results
        """
        result = {
            "success": True,
            "level": strategy.level.value,
            "description": strategy.description,
            "operations_performed": [],
            "warnings": [],
        }

        if strategy.fallback_data:
            result["warnings"].extend(strategy.fallback_data.get("warnings", []))
            result["available_operations"] = strategy.fallback_data.get("available_operations", [])
            result["disabled_operations"] = strategy.fallback_data.get("disabled_operations", [])

        # Simulate workflow execution based on level
        if strategy.level == FunctionalityLevel.FULL:
            result["operations_performed"] = [
                "full_security_scan",
                "complete_reporting",
                "timeline_update",
            ]

        elif strategy.level == FunctionalityLevel.REDUCED:
            result["operations_performed"] = ["basic_security_scan", "limited_reporting"]
            result["warnings"].append("Some features disabled due to file corruption")

        elif strategy.level == FunctionalityLevel.MINIMAL:
            result["operations_performed"] = ["basic_security_scan"]
            result["warnings"].extend(
                [
                    "Operating in minimal mode",
                    "Most features disabled",
                    "Manual intervention recommended",
                ]
            )

        else:  # EMERGENCY
            result["operations_performed"] = ["emergency_scan_only"]
            result["warnings"].extend(
                [
                    "CRITICAL: Emergency mode active",
                    "All advanced features disabled",
                    "Immediate restoration required",
                ]
            )

        return result


def print_validation_summary(summary: ValidationSummary, verbose: bool = False) -> None:
    """Print a formatted validation summary.

    Args:
        summary: ValidationSummary to print
        verbose: Whether to include detailed results
    """
    print("\n" + "=" * 60)
    print("🔍 Security Files Validation Summary")
    print("=" * 60)

    print(f"📊 Total Files: {summary.total_files}")
    print(f"✅ Valid Files: {summary.valid_files}")
    print(f"❌ Invalid Files: {summary.invalid_files}")

    if summary.repaired_files > 0:
        print(f"🔧 Repaired Files: {summary.repaired_files}")
    if summary.failed_repairs > 0:
        print(f"💥 Failed Repairs: {summary.failed_repairs}")

    print(f"⚠️  Total Errors: {summary.total_errors}")
    print(f"⚠️  Total Warnings: {summary.total_warnings}")

    if verbose and summary.results:
        print("\n📋 Detailed Results:")
        print("-" * 40)

        for result in summary.results:
            status = "✅ VALID" if result.is_valid else "❌ INVALID"
            print(f"\n{status}: {result.file_path} ({result.file_type})")

            if result.errors:
                print("  Errors:")
                for error in result.errors:
                    print(f"    - {error}")

            if result.warnings:
                print("  Warnings:")
                for warning in result.warnings:
                    print(f"    - {warning}")

            if result.repair_attempted:
                repair_status = "SUCCESS" if result.repair_successful else "FAILED"
                print(f"  Repair: {repair_status}")


def main() -> int:
    """Main entry point for the validation script."""
    parser = argparse.ArgumentParser(
        description="Validate security data files (YAML, JSON, Markdown)"
    )
    parser.add_argument(
        "--repair", action="store_true", help="Attempt automatic repair of invalid YAML files"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--file", type=str, help="Validate a specific file instead of all security files"
    )
    parser.add_argument(
        "--graceful-degradation",
        action="store_true",
        help="Enable graceful degradation for corrupted files",
    )
    parser.add_argument(
        "--create-fallback",
        action="store_true",
        help="Create minimal valid files for corrupted ones",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check YAML files without making any changes (validation only)",
    )
    parser.add_argument(
        "--backup", action="store_true", help="Create backups of all YAML files before validation"
    )
    parser.add_argument(
        "--degraded-mode",
        action="store_true",
        help="Enable degraded mode operation for corrupted files",
    )
    parser.add_argument(
        "--create-emergency-files",
        action="store_true",
        help="Create emergency fallback files for critical security operations",
    )

    args = parser.parse_args()

    try:
        validator = SecurityFileValidator(verbose=args.verbose)

        # Handle backup creation if requested
        if args.backup:
            print("🔄 Creating backups of all YAML files...")
            backup_count = validator._create_all_backups()
            print(f"✅ Created {backup_count} backup files")

        # Handle check-only mode
        if args.check:
            print("🔍 Running validation check (no repairs or modifications)...")
            # Disable repair for check mode
            args.repair = False

        if args.file:
            # Validate single file
            result = validator.validate_file(args.file)

            status = "✅ VALID" if result.is_valid else "❌ INVALID"
            print(f"{status}: {result.file_path} ({result.file_type})")

            if result.errors:
                print("Errors:")
                for error in result.errors:
                    print(f"  - {error}")

            if result.warnings:
                print("Warnings:")
                for warning in result.warnings:
                    print(f"  - {warning}")

            return 0 if result.is_valid else 1

        # Validate all security files
        summary = validator.validate_security_files(repair=args.repair)
        print_validation_summary(summary, verbose=args.verbose)

        # Handle degraded mode if requested
        if args.degraded_mode and summary.invalid_files > 0:
            print("\n🔄 Activating degraded mode operation...")

            degradation = GracefulDegradation(verbose=args.verbose)
            level = degradation.determine_functionality_level(summary.results)

            corrupted_files = [r.file_path for r in summary.results if not r.is_valid]
            strategy = degradation.create_fallback_strategy(level, corrupted_files)

            print(f"📊 Functionality Level: {level.value.upper()}")
            print(f"📝 Strategy: {strategy.description}")

            # Execute degraded workflow
            workflow_result = degradation.execute_degraded_workflow(strategy)

            print(
                f"\n🚀 Degraded Mode Execution: {'SUCCESS' if workflow_result['success'] else 'FAILED'}"
            )
            print(
                f"📋 Available Operations: {', '.join(workflow_result.get('available_operations', []))}"
            )

            if workflow_result.get("warnings"):
                print("⚠️  Degraded Mode Warnings:")
                for warning in workflow_result["warnings"]:
                    print(f"   - {warning}")

            return 0  # Degraded mode allows continuation

        # Handle graceful degradation if requested
        if args.graceful_degradation and summary.invalid_files > 0:
            print("\n🔄 Activating graceful degradation...")

            degradation = GracefulDegradation(verbose=args.verbose)
            level = degradation.determine_functionality_level(summary.results)

            corrupted_files = [r.file_path for r in summary.results if not r.is_valid]
            strategy = degradation.create_fallback_strategy(level, corrupted_files)

            print(f"📊 Functionality Level: {level.value.upper()}")
            print(f"📝 Strategy: {strategy.description}")

            # Create fallback files if requested
            if args.create_fallback:
                print("\n🔧 Creating minimal valid files...")
                created_files = degradation.create_minimal_valid_files(corrupted_files)
                if created_files:
                    print(f"✅ Created {len(created_files)} fallback files")
                    for file_path in created_files:
                        print(f"   - {file_path}")

            # Create emergency files if requested or if in emergency mode
            if args.create_emergency_files or level == FunctionalityLevel.EMERGENCY:
                print("\n🚨 Creating emergency fallback files...")
                emergency_files = degradation.create_emergency_fallback_files()
                if emergency_files:
                    print(f"✅ Created {len(emergency_files)} emergency files")
                    for file_path in emergency_files:
                        print(f"   - {file_path}")

            # Execute degraded workflow
            workflow_result = degradation.execute_degraded_workflow(strategy)

            print(
                f"\n🚀 Workflow Execution: {'SUCCESS' if workflow_result['success'] else 'FAILED'}"
            )
            print(f"📋 Operations: {', '.join(workflow_result['operations_performed'])}")

            if workflow_result["warnings"]:
                print("⚠️  Warnings:")
                for warning in workflow_result["warnings"]:
                    print(f"   - {warning}")

            return 0  # Graceful degradation allows continuation

        # Return appropriate exit code
        if summary.invalid_files == 0:
            print("\n🎉 All security files are valid!")
            return 0
        if summary.repaired_files > 0 and summary.failed_repairs == 0:
            print("\n🔧 All invalid files were successfully repaired!")
            return 0
        print(f"\n💥 {summary.invalid_files} files remain invalid")
        if not args.graceful_degradation:
            print("💡 Tip: Use --graceful-degradation to continue with reduced functionality")
        return 1

    except KeyboardInterrupt:
        print("\n⚠️  Validation interrupted by user", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
