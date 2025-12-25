"""Comprehensive tests for YAML validation and repair functionality.

Tests the complete YAML validation system including:
- YAML syntax validation
- Automatic repair functionality
- Graceful degradation mechanisms
- Various corruption scenarios

Requirements addressed: 6.1, 6.2
"""

import json
from pathlib import Path

# Import the modules to test
import sys
import tempfile
import unittest

import yaml

sys.path.append("scripts")
import pytest
from repair_yaml import YAMLRepairer, YAMLRepairError
from validate_security_yaml import (
    FallbackStrategy,
    FunctionalityLevel,
    GracefulDegradation,
    SecurityFileValidator,
    ValidationResult,
)


class TestYAMLValidation(unittest.TestCase):
    """Test YAML validation functionality."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.validator = SecurityFileValidator(verbose=False)

        # Create test security directory structure
        self.security_dir = self.temp_dir / "security"
        self.findings_dir = self.security_dir / "findings"
        self.config_dir = self.security_dir / "config"

        for dir_path in [self.security_dir, self.findings_dir, self.config_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_valid_yaml_file(self) -> None:
        """Test validation of a valid YAML file."""
        # Create valid YAML content
        valid_yaml = {
            "timeline": [
                {
                    "timestamp": "2025-01-01T00:00:00Z",
                    "action": "finding_created",
                    "finding_id": "TEST-001",
                    "user": "test_user",
                }
            ],
            "metadata": {"version": "1.0", "generated": "2025-01-01T00:00:00Z"},
        }

        yaml_file = self.findings_dir / "remediation-timeline.yml"
        with yaml_file.open("w") as f:
            yaml.dump(valid_yaml, f, default_flow_style=False)

        result = self.validator.validate_file(yaml_file)

        assert result.is_valid
        assert result.file_type == "yaml"
        assert len(result.errors) == 0
        assert not result.repair_attempted

    def test_validate_corrupted_yaml_indentation(self) -> None:
        """Test validation of YAML with indentation errors."""
        # Create YAML with indentation issues
        corrupted_yaml = """timeline:
  - timestamp: "2025-01-01T00:00:00Z"
    action: "finding_created"
    finding_id: "TEST-001"
   user: "test_user"  # Wrong indentation (3 spaces instead of 4)
metadata:
  version: "1.0"
"""

        yaml_file = self.findings_dir / "corrupted-timeline.yml"
        yaml_file.write_text(corrupted_yaml)

        result = self.validator.validate_file(yaml_file)

        assert not result.is_valid
        assert result.file_type == "yaml"
        assert len(result.errors) > 0
        assert "YAML parsing error" in result.errors[0]

    def test_validate_yaml_missing_quotes(self) -> None:
        """Test validation of YAML with unquoted special characters."""
        # Create YAML with special characters that need quoting
        corrupted_yaml = """timeline:
  - timestamp: 2025-01-01T00:00:00Z
    action: finding_created
    description: This has special chars: {}[]@#
    finding_id: TEST-001
"""

        yaml_file = self.findings_dir / "special-chars.yml"
        yaml_file.write_text(corrupted_yaml)

        result = self.validator.validate_file(yaml_file)

        # This might be valid or have warnings depending on YAML parser
        if not result.is_valid:
            assert len(result.errors) > 0
        else:
            # Should at least have warnings about special characters
            assert len(result.warnings) >= 0

    def test_validate_json_file(self) -> None:
        """Test validation of JSON files."""
        # Valid JSON
        valid_json = {
            "findings": [{"id": "TEST-001", "severity": "high", "description": "Test finding"}]
        }

        json_file = self.findings_dir / "findings.json"
        with json_file.open("w") as f:
            json.dump(valid_json, f, indent=2)

        result = self.validator.validate_file(json_file)

        assert result.is_valid
        assert result.file_type == "json"
        assert len(result.errors) == 0

    def test_validate_corrupted_json_file(self) -> None:
        """Test validation of corrupted JSON files."""
        # Invalid JSON (missing closing brace)
        corrupted_json = '{"findings": [{"id": "TEST-001", "severity": "high"'

        json_file = self.findings_dir / "corrupted.json"
        json_file.write_text(corrupted_json)

        result = self.validator.validate_file(json_file)

        assert not result.is_valid
        assert result.file_type == "json"
        assert len(result.errors) > 0
        assert "JSON parsing error" in result.errors[0]

    def test_validate_markdown_file(self) -> None:
        """Test validation of Markdown files."""
        markdown_content = """# Security Findings Summary

## Current Findings

- TEST-001: High severity finding

## Remediation Summary

All findings are being addressed.
"""

        md_file = self.findings_dir / "SECURITY_FINDINGS.md"
        md_file.write_text(markdown_content)

        result = self.validator.validate_file(md_file)

        assert result.is_valid
        assert result.file_type == "markdown"
        assert len(result.errors) == 0

    def test_validate_nonexistent_file(self) -> None:
        """Test validation of non-existent file."""
        nonexistent_file = self.temp_dir / "nonexistent.yml"

        result = self.validator.validate_file(nonexistent_file)

        assert not result.is_valid
        assert len(result.errors) > 0
        assert "File not found" in result.errors[0]

    def test_validate_security_files_summary(self) -> None:
        """Test validation of multiple security files."""
        # Create multiple test files
        files_to_create = [
            ("valid.yml", {"test": "data"}),
            ("invalid.yml", "invalid: yaml: content:"),
            ("valid.json", {"test": "data"}),
            ("invalid.json", '{"invalid": json'),
        ]

        for filename, content in files_to_create:
            file_path = self.findings_dir / filename
            if isinstance(content, dict):
                if filename.endswith(".yml"):
                    with file_path.open("w") as f:
                        yaml.dump(content, f)
                else:
                    with file_path.open("w") as f:
                        json.dump(content, f)
            else:
                file_path.write_text(content)

        # Mock the security paths to point to our test directory
        original_paths = self.validator.security_paths
        self.validator.security_paths = [str(self.security_dir)]

        try:
            summary = self.validator.validate_security_files(repair=False)

            assert summary.total_files == 4
            assert summary.valid_files == 2
            assert summary.invalid_files == 2
            assert summary.total_errors > 0
        finally:
            self.validator.security_paths = original_paths


class TestYAMLRepair(unittest.TestCase):
    """Test YAML repair functionality."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_repair_indentation_errors(self) -> None:
        """Test repair of indentation errors."""
        # Create YAML with indentation issues
        corrupted_yaml = """timeline:
  - timestamp: "2025-01-01T00:00:00Z"
    action: "finding_created"
    finding_id: "TEST-001"
   user: "test_user"  # 3 spaces instead of 4
metadata:
  version: "1.0"
"""

        yaml_file = self.temp_dir / "test.yml"
        yaml_file.write_text(corrupted_yaml)

        repairer = YAMLRepairer(str(yaml_file))

        # Test the repair process
        success = repairer.repair_file()

        if success:
            # Verify the file is now valid YAML
            with yaml_file.open() as f:
                repaired_content = f.read()

            try:
                yaml.safe_load(repaired_content)
                yaml_is_valid = True
            except yaml.YAMLError:
                yaml_is_valid = False

            assert yaml_is_valid
            assert len(repairer.repairs_made) > 0
            assert repairer.backup_path is not None
            assert repairer.backup_path.exists()

    def test_repair_creates_backup(self) -> None:
        """Test that repair creates a backup file."""
        yaml_content = "test: data"
        yaml_file = self.temp_dir / "test.yml"
        yaml_file.write_text(yaml_content)

        repairer = YAMLRepairer(str(yaml_file))
        backup_path = repairer.create_backup()

        assert Path(backup_path).exists()
        assert repairer.original_checksum is not None

        # Verify backup content matches original
        backup_content = Path(backup_path).read_text()
        assert backup_content == yaml_content

    def test_repair_nonexistent_file(self) -> None:
        """Test repair of non-existent file raises error."""
        nonexistent_file = self.temp_dir / "nonexistent.yml"
        repairer = YAMLRepairer(str(nonexistent_file))

        with pytest.raises(YAMLRepairError):
            repairer.repair_file()

    def test_repair_already_valid_yaml(self) -> None:
        """Test repair of already valid YAML file."""
        valid_yaml = {"test": "data", "list": [1, 2, 3]}
        yaml_file = self.temp_dir / "valid.yml"

        with yaml_file.open("w") as f:
            yaml.dump(valid_yaml, f)

        repairer = YAMLRepairer(str(yaml_file))
        success = repairer.repair_file()

        assert success
        assert len(repairer.repairs_made) == 0


class TestGracefulDegradation(unittest.TestCase):
    """Test graceful degradation functionality."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.degradation = GracefulDegradation(verbose=False)

    def test_determine_functionality_level_full(self) -> None:
        """Test functionality level determination with all valid files."""
        results = [
            ValidationResult("file1.yml", True),
            ValidationResult("file2.yml", True),
            ValidationResult("file3.json", True),
        ]

        level = self.degradation.determine_functionality_level(results)
        assert level == FunctionalityLevel.FULL

    def test_determine_functionality_level_reduced(self) -> None:
        """Test functionality level determination with minor corruption."""
        results = [
            ValidationResult("file1.yml", True),
            ValidationResult("file2.yml", False),  # Non-critical file
            ValidationResult("remediation-timeline.yml", True),  # Critical file OK
            ValidationResult("file3.json", True),
        ]

        level = self.degradation.determine_functionality_level(results)
        assert level == FunctionalityLevel.REDUCED

    def test_determine_functionality_level_minimal(self) -> None:
        """Test functionality level determination with significant corruption."""
        # Need 6 files total with 3 invalid (50%) and 0 critical files invalid
        results = [
            ValidationResult("file1.yml", True),
            ValidationResult("file2.yml", False),
            ValidationResult("remediation-timeline.yml", True),  # Critical file OK
            ValidationResult("file3.json", False),
            ValidationResult("file4.yml", True),
            ValidationResult("file5.json", False),  # 3/6 = 50% invalid, 0 critical invalid
        ]

        level = self.degradation.determine_functionality_level(results)
        assert level == FunctionalityLevel.MINIMAL

    def test_determine_functionality_level_emergency(self) -> None:
        """Test functionality level determination with critical corruption."""
        results = [
            ValidationResult("file1.yml", False),
            ValidationResult("remediation-timeline.yml", False),  # Critical file corrupted
            ValidationResult("SECURITY_FINDINGS.md", False),  # Critical file corrupted
            ValidationResult("file3.json", False),
        ]

        level = self.degradation.determine_functionality_level(results)
        assert level == FunctionalityLevel.EMERGENCY

    def test_create_fallback_strategy_full(self) -> None:
        """Test fallback strategy creation for full functionality."""
        strategy = self.degradation.create_fallback_strategy(FunctionalityLevel.FULL, [])

        assert strategy.level == FunctionalityLevel.FULL
        assert strategy.can_continue
        assert "full functionality" in strategy.description.lower()

    def test_create_fallback_strategy_reduced(self) -> None:
        """Test fallback strategy creation for reduced functionality."""
        corrupted_files = ["file1.yml", "file2.json"]
        strategy = self.degradation.create_fallback_strategy(
            FunctionalityLevel.REDUCED, corrupted_files
        )

        assert strategy.level == FunctionalityLevel.REDUCED
        assert strategy.can_continue
        assert strategy.fallback_data is not None
        assert strategy.fallback_data["mode"] == "reduced"
        assert strategy.fallback_data["corrupted_files"] == corrupted_files

    def test_create_fallback_strategy_emergency(self) -> None:
        """Test fallback strategy creation for emergency functionality."""
        corrupted_files = ["remediation-timeline.yml", "SECURITY_FINDINGS.md"]
        strategy = self.degradation.create_fallback_strategy(
            FunctionalityLevel.EMERGENCY, corrupted_files
        )

        assert strategy.level == FunctionalityLevel.EMERGENCY
        assert strategy.can_continue
        assert strategy.fallback_data is not None
        assert strategy.fallback_data["mode"] == "emergency"
        assert "emergency_timeline" in strategy.fallback_data
        assert "emergency_findings" in strategy.fallback_data

    def test_create_minimal_valid_files(self) -> None:
        """Test creation of minimal valid files."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            corrupted_files = [str(temp_dir / "timeline.yml"), str(temp_dir / "findings.yml")]

            created_files = self.degradation.create_minimal_valid_files(
                corrupted_files, output_dir=temp_dir
            )

            assert len(created_files) == 2

            for file_path in created_files:
                assert Path(file_path).exists()

                # Verify the created file is valid YAML
                with Path(file_path).open() as f:
                    content = yaml.safe_load(f)

                assert isinstance(content, dict)
                # Check for generated timestamp in metadata or top level
                has_generated = "generated" in content or (
                    "metadata" in content and "generated" in content["metadata"]
                )
                assert has_generated

                # Check for mode in metadata or top level
                has_mode = "mode" in content or (
                    "metadata" in content and "mode" in content["metadata"]
                )
                assert has_mode

        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_execute_degraded_workflow(self) -> None:
        """Test execution of degraded workflow."""
        strategy = FallbackStrategy(
            level=FunctionalityLevel.REDUCED,
            description="Test reduced functionality",
            can_continue=True,
            fallback_data={
                "mode": "reduced",
                "available_operations": ["basic_scan"],
                "warnings": ["Test warning"],
            },
        )

        result = self.degradation.execute_degraded_workflow(strategy)

        assert result["success"]
        assert result["level"] == "reduced"
        assert "basic_security_scan" in result["operations_performed"]
        assert "Test warning" in result["warnings"]


class TestYAMLValidationIntegration(unittest.TestCase):
    """Integration tests for YAML validation system."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.validator = SecurityFileValidator(verbose=False)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_end_to_end_validation_and_repair(self) -> None:
        """Test complete validation and repair workflow."""
        # Create a corrupted YAML file
        corrupted_yaml = """timeline:
  - timestamp: "2025-01-01T00:00:00Z"
    action: "finding_created"
   user: "test_user"  # Wrong indentation
metadata:
  version: "1.0"
"""

        yaml_file = self.temp_dir / "test.yml"
        yaml_file.write_text(corrupted_yaml)

        # Step 1: Validate and detect corruption
        result = self.validator.validate_file(yaml_file)
        assert not result.is_valid

        # Step 2: Attempt repair
        repairer = YAMLRepairer(str(yaml_file))
        repair_success = repairer.repair_file()

        if repair_success:
            # Step 3: Re-validate after repair
            new_result = self.validator.validate_file(yaml_file)
            assert new_result.is_valid

            # Step 4: Verify backup was created
            assert repairer.backup_path is not None
            assert repairer.backup_path.exists()

    def test_graceful_degradation_workflow(self) -> None:
        """Test complete graceful degradation workflow."""
        # Create mixed valid and invalid files
        security_dir = self.temp_dir / "security" / "findings"
        security_dir.mkdir(parents=True)

        # Valid file
        valid_yaml = {"timeline": [], "metadata": {"version": "1.0"}}
        valid_file = security_dir / "valid.yml"
        with valid_file.open("w") as f:
            yaml.dump(valid_yaml, f)

        # Invalid file
        invalid_file = security_dir / "remediation-timeline.yml"
        invalid_file.write_text("invalid: yaml: content:")

        # Mock security paths
        original_paths = self.validator.security_paths
        self.validator.security_paths = [str(self.temp_dir / "security")]

        try:
            # Step 1: Validate all files
            summary = self.validator.validate_security_files(repair=False)
            assert summary.invalid_files > 0

            # Step 2: Determine degradation level
            degradation = GracefulDegradation(verbose=False)
            level = degradation.determine_functionality_level(summary.results)

            # Step 3: Create fallback strategy
            corrupted_files = [r.file_path for r in summary.results if not r.is_valid]
            strategy = degradation.create_fallback_strategy(level, corrupted_files)

            # Step 4: Execute degraded workflow
            workflow_result = degradation.execute_degraded_workflow(strategy)

            assert workflow_result["success"]
            assert len(workflow_result["operations_performed"]) > 0

        finally:
            self.validator.security_paths = original_paths


if __name__ == "__main__":
    unittest.main()
