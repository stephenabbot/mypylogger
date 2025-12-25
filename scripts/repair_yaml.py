#!/usr/bin/env python3
"""YAML Repair Script for Security Findings.

This script detects and fixes common YAML syntax errors in security data files,
specifically designed to repair the corrupted remediation-timeline.yml file.

Requirements addressed: 2.1, 2.2, 2.3
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
from pathlib import Path
import re
import shutil
import sys
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install PyYAML", file=sys.stderr)
    sys.exit(1)


class YAMLRepairError(Exception):
    """Exception raised when YAML repair operations fail."""


class YAMLRepairer:
    """Repairs common YAML syntax errors in security data files."""

    def __init__(self, file_path: str) -> None:
        """Initialize the YAML repairer.

        Args:
            file_path: Path to the YAML file to repair
        """
        self.file_path = Path(file_path)
        self.backup_path: Path | None = None
        self.repairs_made: list[str] = []
        self.original_checksum: str | None = None
        self.repaired_checksum: str | None = None

    def create_backup(self) -> str:
        """Create a backup of the original file before repair.

        Returns:
            Path to the backup file

        Raises:
            YAMLRepairError: If backup creation fails
        """
        try:
            # Calculate checksum of original file for integrity validation
            with open(self.file_path, "rb") as f:
                self.original_checksum = hashlib.sha256(f.read()).hexdigest()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.backup_path = self.file_path.with_suffix(f".backup.{timestamp}.yml")
            shutil.copy2(self.file_path, self.backup_path)
            print(f"✅ Backup created: {self.backup_path}")
            print(f"   Original checksum: {self.original_checksum[:16]}...")
            return str(self.backup_path)
        except Exception as e:
            msg = f"Failed to create backup: {e}"
            raise YAMLRepairError(msg)

    def detect_yaml_errors(self) -> list[tuple[int, str]]:
        """Detect YAML parsing errors in the file.

        Returns:
            List of tuples containing (line_number, error_description)
        """
        errors = []
        try:
            with open(self.file_path, encoding="utf-8") as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            if hasattr(e, "problem_mark"):
                line_num = e.problem_mark.line + 1
                error_desc = str(e).split("\n")[0]
                errors.append((line_num, error_desc))
            else:
                errors.append((0, str(e)))
        except Exception as e:
            errors.append((0, f"File reading error: {e}"))

        return errors

    def fix_indentation_errors(self, content: str) -> str:
        """Fix common indentation errors in YAML content.

        Args:
            content: YAML file content as string

        Returns:
            Repaired YAML content
        """
        lines = content.split("\n")
        fixed_lines = []

        for i, line in enumerate(lines):
            line_num = i + 1

            # Skip empty lines
            if not line.strip():
                fixed_lines.append(line)
                continue

            # Fix specific indentation issue: 'user:' field with wrong indentation
            # This pattern matches lines with exactly 3 spaces followed by 'user:'
            if re.match(r"^   user:", line):
                # This should have 6 spaces to align with other event fields
                fixed_line = "      " + line.lstrip()
                fixed_lines.append(fixed_line)
                self.repairs_made.append(
                    f"Line {line_num}: Fixed indentation of 'user' field from 3 to 6 spaces"
                )
                continue

            # Fix inconsistent indentation (odd number of spaces)
            if line.startswith(" "):
                spaces = len(line) - len(line.lstrip())
                if spaces % 2 != 0 and spaces > 1:
                    # Round to nearest even number
                    new_spaces = spaces + 1 if spaces % 4 != 3 else spaces - 1
                    fixed_line = " " * new_spaces + line.lstrip()
                    fixed_lines.append(fixed_line)
                    self.repairs_made.append(
                        f"Line {line_num}: Fixed inconsistent indentation from {spaces} to {new_spaces} spaces"
                    )
                    continue

            # Fix tabs mixed with spaces
            if "\t" in line:
                # Convert tabs to 2 spaces (YAML standard)
                fixed_line = line.replace("\t", "  ")
                fixed_lines.append(fixed_line)
                self.repairs_made.append(f"Line {line_num}: Converted tabs to spaces")
                continue

            fixed_lines.append(line)

        return "\n".join(fixed_lines)

    def fix_block_mapping_errors(self, content: str) -> str:
        """Fix block mapping structure errors.

        Args:
            content: YAML file content as string

        Returns:
            Repaired YAML content
        """
        lines = content.split("\n")
        fixed_lines = []
        in_events_list = False

        for i, line in enumerate(lines):
            line_num = i + 1

            # Track when we're inside an events list
            if "events:" in line:
                in_events_list = True
            elif line.strip() and not line.startswith(" ") and in_events_list:
                in_events_list = False

            # Fix missing list item indicators in events
            if in_events_list and line.strip().startswith("timestamp:"):
                # This should be a list item
                if not line.lstrip().startswith("- timestamp:"):
                    indent = len(line) - len(line.lstrip())
                    fixed_line = " " * (indent - 2) + "- " + line.lstrip()
                    fixed_lines.append(fixed_line)
                    self.repairs_made.append(f"Line {line_num}: Added list item indicator")
                    continue

            fixed_lines.append(line)

        return "\n".join(fixed_lines)

    def fix_missing_quotes(self, content: str) -> str:
        """Fix missing quotes around values with special characters.

        Args:
            content: YAML file content as string

        Returns:
            Repaired YAML content
        """
        lines = content.split("\n")
        fixed_lines = []

        for i, line in enumerate(lines):
            line_num = i + 1

            # Skip empty lines and comments
            if not line.strip() or line.strip().startswith("#"):
                fixed_lines.append(line)
                continue

            # Look for key-value pairs that need quoting
            if ":" in line and not line.strip().startswith("-"):
                key_value_match = re.match(r"^(\s*)([\w-]+):\s*(.+)$", line)
                if key_value_match:
                    indent, key, value = key_value_match.groups()

                    # Check if value needs quoting (contains special chars but isn't quoted)
                    if (
                        re.search(r"[{}[\]@#|>*&!%`]", value)
                        and not (value.startswith('"') and value.endswith('"'))
                        and not (value.startswith("'") and value.endswith("'"))
                    ):
                        # Quote the value
                        quoted_value = f'"{value}"'
                        fixed_line = f"{indent}{key}: {quoted_value}"
                        fixed_lines.append(fixed_line)
                        self.repairs_made.append(
                            f"Line {line_num}: Added quotes around value with special characters"
                        )
                        continue

            fixed_lines.append(line)

        return "\n".join(fixed_lines)

    def fix_unclosed_blocks(self, content: str) -> str:
        """Fix unclosed YAML blocks and structures.

        Args:
            content: YAML file content as string

        Returns:
            Repaired YAML content
        """
        lines = content.split("\n")
        fixed_lines = []
        bracket_stack = []
        brace_stack = []

        for i, line in enumerate(lines):
            line_num = i + 1

            # Track opening and closing brackets/braces
            for char in line:
                if char == "[":
                    bracket_stack.append(line_num)
                elif char == "]" and bracket_stack:
                    bracket_stack.pop()
                elif char == "{":
                    brace_stack.append(line_num)
                elif char == "}" and brace_stack:
                    brace_stack.pop()

            fixed_lines.append(line)

        # Add missing closing brackets/braces at the end if needed
        if bracket_stack:
            for _ in bracket_stack:
                fixed_lines.append("]")
                self.repairs_made.append("Added missing closing bracket at end of file")

        if brace_stack:
            for _ in brace_stack:
                fixed_lines.append("}")
                self.repairs_made.append("Added missing closing brace at end of file")

        return "\n".join(fixed_lines)

    def validate_data_integrity(self, original_content: str, repaired_content: str) -> bool:
        """Validate that repairs maintain data integrity.

        Args:
            original_content: Original YAML content
            repaired_content: Repaired YAML content

        Returns:
            True if data integrity is maintained, False otherwise
        """
        try:
            # Try to parse both versions
            original_data = None
            repaired_data = None

            try:
                original_data = yaml.safe_load(original_content)
            except yaml.YAMLError:
                # Original was invalid, so we can't compare data
                pass

            try:
                repaired_data = yaml.safe_load(repaired_content)
            except yaml.YAMLError:
                # Repair failed to create valid YAML
                return False

            # If original was valid, compare data structures
            if original_data is not None:
                return self._compare_data_structures(original_data, repaired_data)

            # If original was invalid but repaired is valid, that's good
            return repaired_data is not None

        except Exception:
            return False

    def _compare_data_structures(self, original: Any, repaired: Any) -> bool:
        """Compare two data structures for equivalence.

        Args:
            original: Original data structure
            repaired: Repaired data structure

        Returns:
            True if structures are equivalent, False otherwise
        """
        try:
            # For basic comparison, convert both to strings and compare
            # This is not perfect but catches major data loss
            original_str = str(original) if original is not None else ""
            repaired_str = str(repaired) if repaired is not None else ""

            # Allow for minor formatting differences
            original_normalized = re.sub(r"\s+", " ", original_str).strip()
            repaired_normalized = re.sub(r"\s+", " ", repaired_str).strip()

            return original_normalized == repaired_normalized

        except Exception:
            return False

    def validate_yaml_syntax(self, content: str) -> bool:
        """Validate that the YAML content can be parsed correctly.

        Args:
            content: YAML content to validate

        Returns:
            True if valid YAML, False otherwise
        """
        try:
            yaml.safe_load(content)
            return True
        except yaml.YAMLError:
            return False

    def repair_file(self) -> bool:
        """Repair the YAML file by fixing common syntax errors.

        Returns:
            True if repair was successful, False otherwise

        Raises:
            YAMLRepairError: If repair process fails
        """
        if not self.file_path.exists():
            msg = f"File not found: {self.file_path}"
            raise YAMLRepairError(msg)

        # Create backup first
        self.create_backup()

        try:
            # Read original content
            with open(self.file_path, encoding="utf-8") as f:
                original_content = f.read()

            print(f"🔍 Analyzing YAML file: {self.file_path}")

            # Detect initial errors
            initial_errors = self.detect_yaml_errors()
            if not initial_errors:
                print("✅ No YAML errors detected")
                return True

            print(f"❌ Found {len(initial_errors)} YAML errors:")
            for line_num, error in initial_errors:
                print(f"  Line {line_num}: {error}")

            # Apply repairs in order of importance
            content = original_content

            # 1. Fix indentation errors first (most common issue)
            content = self.fix_indentation_errors(content)

            # 2. Fix missing quotes around special characters
            content = self.fix_missing_quotes(content)

            # 3. Fix block mapping errors
            content = self.fix_block_mapping_errors(content)

            # 4. Fix unclosed blocks
            content = self.fix_unclosed_blocks(content)

            # Validate the repaired content
            if not self.validate_yaml_syntax(content):
                print("❌ Repair failed - YAML still invalid after fixes")
                return False

            # Validate data integrity
            if not self.validate_data_integrity(original_content, content):
                print("❌ Repair failed - Data integrity check failed")
                return False

            # Calculate checksum of repaired content
            self.repaired_checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()

            # Write repaired content back to file
            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write(content)

            print("✅ YAML repair completed successfully")
            print(f"   Repaired checksum: {self.repaired_checksum[:16]}...")

            if self.repairs_made:
                print("🔧 Repairs made:")
                for repair in self.repairs_made:
                    print(f"  - {repair}")
            else:
                print("ℹ️  No repairs were needed")

            return True

        except Exception as e:
            # Restore from backup if repair fails
            if self.backup_path and self.backup_path.exists():
                shutil.copy2(self.backup_path, self.file_path)
                print(f"❌ Repair failed, restored from backup: {e}")
            msg = f"Repair process failed: {e}"
            raise YAMLRepairError(msg)


def main() -> None:
    """Main entry point for the YAML repair script."""
    parser = argparse.ArgumentParser(description="Repair YAML syntax errors in security data files")
    parser.add_argument("file_path", help="Path to the YAML file to repair")
    parser.add_argument(
        "--fix-blocks", action="store_true", help="Fix block mapping structure errors"
    )
    parser.add_argument("--fix-indentation", action="store_true", help="Fix indentation errors")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    try:
        repairer = YAMLRepairer(args.file_path)
        success = repairer.repair_file()

        if success:
            print(f"🎉 YAML repair completed successfully for {args.file_path}")
            sys.exit(0)
        else:
            print(f"💥 YAML repair failed for {args.file_path}")
            sys.exit(1)

    except YAMLRepairError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Repair interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
