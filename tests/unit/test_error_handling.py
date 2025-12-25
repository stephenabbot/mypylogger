"""Unit tests for security data file error handling system.

Tests the comprehensive error handling functionality for YAML, JSON, and Markdown files.
"""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import yaml

from security.error_handling import (
    CorruptionSeverity,
    FileIntegrityInfo,
    RecoveryResult,
    RecoveryStrategy,
    SecurityFileErrorHandler,
    detect_file_corruption,
    recover_corrupted_file,
    verify_file_integrity,
)


class TestSecurityFileErrorHandler(unittest.TestCase):
    """Test cases for SecurityFileErrorHandler class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.handler = SecurityFileErrorHandler(backup_dir=self.temp_dir / "backups", verbose=False)

        # Create test files
        self.yaml_file = self.temp_dir / "test.yml"
        self.json_file = self.temp_dir / "test.json"
        self.markdown_file = self.temp_dir / "test.md"

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detect_file_type(self) -> None:
        """Test file type detection."""
        # Test YAML files
        assert self.handler._detect_file_type(Path("test.yml")) == "yaml"
        assert self.handler._detect_file_type(Path("test.yaml")) == "yaml"

        # Test JSON files
        assert self.handler._detect_file_type(Path("test.json")) == "json"

        # Test Markdown files
        assert self.handler._detect_file_type(Path("test.md")) == "markdown"
        assert self.handler._detect_file_type(Path("test.markdown")) == "markdown"

        # Test unknown files
        assert self.handler._detect_file_type(Path("test.txt")) == "unknown"

    def test_calculate_checksum(self) -> None:
        """Test checksum calculation."""
        # Create a test file
        test_content = "test content"
        self.yaml_file.write_text(test_content)

        checksum = self.handler._calculate_checksum(self.yaml_file)
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA256 hex length

        # Same content should produce same checksum
        checksum2 = self.handler._calculate_checksum(self.yaml_file)
        assert checksum == checksum2

    def test_detect_corruption_nonexistent_file(self) -> None:
        """Test corruption detection for non-existent file."""
        nonexistent_file = self.temp_dir / "nonexistent.yml"

        info = self.handler.detect_corruption(nonexistent_file)

        assert info.is_corrupted
        assert info.corruption_severity == CorruptionSeverity.CRITICAL
        assert "File does not exist" in info.corruption_details

    def test_detect_corruption_valid_yaml(self) -> None:
        """Test corruption detection for valid YAML file."""
        valid_yaml = {
            "timeline": [
                {
                    "timestamp": "2024-01-01T00:00:00Z",
                    "action": "test_action",
                    "finding_id": "TEST-001",
                }
            ]
        }

        self.yaml_file.write_text(yaml.dump(valid_yaml))

        info = self.handler.detect_corruption(self.yaml_file)

        assert not info.is_corrupted
        assert info.corruption_severity == CorruptionSeverity.NONE
        assert info.file_type == "yaml"

    def test_detect_corruption_invalid_yaml(self) -> None:
        """Test corruption detection for invalid YAML file."""
        invalid_yaml = """
timeline:
  - timestamp: 2024-01-01T00:00:00Z
    action: test_action
   user: invalid_indentation
"""

        self.yaml_file.write_text(invalid_yaml)

        info = self.handler.detect_corruption(self.yaml_file)

        assert info.is_corrupted
        assert len(info.corruption_details) > 0
        assert info.file_type == "yaml"

    def test_detect_corruption_valid_json(self) -> None:
        """Test corruption detection for valid JSON file."""
        valid_json = {"findings": [], "metadata": {"generated": "2024-01-01T00:00:00Z"}}

        self.json_file.write_text(json.dumps(valid_json, indent=2))

        info = self.handler.detect_corruption(self.json_file)

        assert not info.is_corrupted
        assert info.corruption_severity == CorruptionSeverity.NONE
        assert info.file_type == "json"

    def test_detect_corruption_invalid_json(self) -> None:
        """Test corruption detection for invalid JSON file."""
        # Missing closing brace
        invalid_json = '{"findings": [], "metadata": {"generated": "2024-01-01T00:00:00Z"'

        self.json_file.write_text(invalid_json)

        info = self.handler.detect_corruption(self.json_file)

        assert info.is_corrupted
        assert len(info.corruption_details) > 0
        assert info.file_type == "json"

    def test_detect_corruption_valid_markdown(self) -> None:
        """Test corruption detection for valid Markdown file."""
        valid_markdown = """# Security Findings Summary

## Current Findings

No active findings.

## Remediation Summary

No remediation plans.
"""

        self.markdown_file.write_text(valid_markdown)

        info = self.handler.detect_corruption(self.markdown_file)

        assert not info.is_corrupted
        assert info.corruption_severity == CorruptionSeverity.NONE
        assert info.file_type == "markdown"

    def test_detect_corruption_invalid_markdown(self) -> None:
        """Test corruption detection for invalid Markdown file."""
        # Create a security findings file without required sections
        invalid_markdown = "Some content without proper headers"

        security_findings_file = self.temp_dir / "SECURITY_FINDINGS.md"
        security_findings_file.write_text(invalid_markdown)

        info = self.handler.detect_corruption(security_findings_file)

        assert info.is_corrupted
        assert len(info.corruption_details) > 0
        assert info.file_type == "markdown"

    def test_assess_corruption_severity(self) -> None:
        """Test corruption severity assessment."""
        # Test no corruption
        info = FileIntegrityInfo(file_path="test.yml", file_type="yaml", is_corrupted=False)
        severity = self.handler._assess_corruption_severity(info)
        assert severity == CorruptionSeverity.NONE

        # Test critical corruption (file doesn't exist)
        info.is_corrupted = True
        info.corruption_details = ["File does not exist"]
        severity = self.handler._assess_corruption_severity(info)
        assert severity == CorruptionSeverity.CRITICAL

        # Test severe corruption (parsing error in critical file)
        info.file_path = "remediation-timeline.yml"
        info.corruption_details = ["YAML parsing error: invalid syntax"]
        severity = self.handler._assess_corruption_severity(info)
        assert severity == CorruptionSeverity.SEVERE

    def test_select_recovery_strategy(self) -> None:
        """Test recovery strategy selection."""
        # Test strategy for severe corruption with backup
        info = FileIntegrityInfo(
            file_path="test.yml",
            file_type="yaml",
            is_corrupted=True,
            corruption_severity=CorruptionSeverity.SEVERE,
            backup_available=True,
            backup_path="/path/to/backup.yml",
        )

        strategy = self.handler._select_recovery_strategy(info)
        assert strategy == RecoveryStrategy.RESTORE_FROM_BACKUP

        # Test strategy for moderate corruption
        info.corruption_severity = CorruptionSeverity.MODERATE
        strategy = self.handler._select_recovery_strategy(info)
        assert strategy == RecoveryStrategy.REPAIR_IN_PLACE

        # Test strategy for critical corruption without backup
        info.corruption_severity = CorruptionSeverity.CRITICAL
        info.backup_available = False
        strategy = self.handler._select_recovery_strategy(info)
        assert strategy == RecoveryStrategy.REGENERATE_FROM_BASELINE

    def test_create_backup(self) -> None:
        """Test backup creation."""
        # Create a test file
        test_content = "test content for backup"
        self.yaml_file.write_text(test_content)

        backup_path = self.handler._create_backup(self.yaml_file)

        assert backup_path.exists()
        assert backup_path.read_text() == test_content
        assert "recovery" in backup_path.name

    def test_generate_baseline_content_yaml(self) -> None:
        """Test baseline content generation for YAML files."""
        # Test timeline file
        timeline_file = self.temp_dir / "remediation-timeline.yml"
        content = self.handler._generate_baseline_content(timeline_file, "yaml")

        parsed_content = yaml.safe_load(content)
        assert "timeline" in parsed_content
        assert "metadata" in parsed_content

        # Test findings file
        findings_file = self.temp_dir / "findings.yml"
        content = self.handler._generate_baseline_content(findings_file, "yaml")

        parsed_content = yaml.safe_load(content)
        assert "findings" in parsed_content
        assert parsed_content["findings"] == []

    def test_generate_baseline_content_json(self) -> None:
        """Test baseline content generation for JSON files."""
        content = self.handler._generate_baseline_content(self.json_file, "json")

        parsed_content = json.loads(content)
        assert "generated" in parsed_content
        assert "mode" in parsed_content
        assert parsed_content["mode"] == "baseline_regeneration"

    def test_generate_baseline_content_markdown(self) -> None:
        """Test baseline content generation for Markdown files."""
        content = self.handler._generate_baseline_content(self.markdown_file, "markdown")

        assert "# Test" in content
        assert "Generated" in content
        assert "baseline" in content.lower()

    @patch("scripts.repair_yaml.YAMLRepairer")
    def test_repair_in_place_yaml_success(self, mock_repairer_class: MagicMock) -> None:
        """Test successful in-place repair for YAML files."""
        # Mock the YAMLRepairer
        mock_repairer = MagicMock()
        mock_repairer.repair_file.return_value = True
        mock_repairer_class.return_value = mock_repairer

        # Create a corrupted YAML file
        corrupted_yaml = "invalid: yaml: content:"
        self.yaml_file.write_text(corrupted_yaml)

        integrity_info = FileIntegrityInfo(
            file_path=str(self.yaml_file),
            file_type="yaml",
            is_corrupted=True,
            corruption_severity=CorruptionSeverity.MODERATE,
        )

        result = RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.REPAIR_IN_PLACE,
            original_file=str(self.yaml_file),
        )

        updated_result = self.handler._repair_in_place(self.yaml_file, integrity_info, result)

        assert updated_result.success
        assert updated_result.data_integrity_verified
        mock_repairer.repair_file.assert_called_once()

    def test_regenerate_from_baseline(self) -> None:
        """Test baseline regeneration recovery."""
        integrity_info = FileIntegrityInfo(
            file_path=str(self.yaml_file),
            file_type="yaml",
            is_corrupted=True,
            corruption_severity=CorruptionSeverity.CRITICAL,
        )

        result = RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.REGENERATE_FROM_BASELINE,
            original_file=str(self.yaml_file),
        )

        updated_result = self.handler._regenerate_from_baseline(
            self.yaml_file, integrity_info, result
        )

        assert updated_result.success
        assert self.yaml_file.exists()

        # Verify the generated content is valid YAML
        content = self.yaml_file.read_text()
        parsed_content = yaml.safe_load(content)
        assert isinstance(parsed_content, dict)

    def test_use_fallback_data(self) -> None:
        """Test fallback data creation."""
        integrity_info = FileIntegrityInfo(
            file_path=str(self.yaml_file),
            file_type="yaml",
            is_corrupted=True,
            corruption_severity=CorruptionSeverity.MODERATE,
        )

        result = RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.USE_FALLBACK_DATA,
            original_file=str(self.yaml_file),
        )

        updated_result = self.handler._use_fallback_data(self.yaml_file, integrity_info, result)

        assert updated_result.success

        # Check that fallback file was created
        fallback_file = Path(updated_result.recovered_file)
        assert fallback_file.exists()
        assert "fallback" in fallback_file.name

        # Verify fallback content is valid
        content = fallback_file.read_text()
        parsed_content = yaml.safe_load(content)
        assert parsed_content.get("fallback_mode", False)


class TestConvenienceFunctions(unittest.TestCase):
    """Test cases for convenience functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_file = self.temp_dir / "test.yml"

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detect_file_corruption(self) -> None:
        """Test detect_file_corruption convenience function."""
        # Create a valid YAML file
        valid_yaml = {"test": "data"}
        self.test_file.write_text(yaml.dump(valid_yaml))

        info = detect_file_corruption(self.test_file)

        assert isinstance(info, FileIntegrityInfo)
        assert not info.is_corrupted

    def test_verify_file_integrity(self) -> None:
        """Test verify_file_integrity convenience function."""
        # Create a valid YAML file
        valid_yaml = {"test": "data"}
        self.test_file.write_text(yaml.dump(valid_yaml))

        is_intact = verify_file_integrity(self.test_file)
        assert is_intact

        # Test with corrupted file
        self.test_file.write_text("invalid: yaml: content:")
        is_intact = verify_file_integrity(self.test_file)
        assert not is_intact

    @patch("security.error_handling.SecurityFileErrorHandler.recover_file")
    def test_recover_corrupted_file(self, mock_recover: MagicMock) -> None:
        """Test recover_corrupted_file convenience function."""
        mock_result = RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.REPAIR_IN_PLACE,
            original_file=str(self.test_file),
        )
        mock_recover.return_value = mock_result

        result = recover_corrupted_file(self.test_file)

        assert isinstance(result, RecoveryResult)
        assert result.success
        mock_recover.assert_called_once()


if __name__ == "__main__":
    unittest.main()
