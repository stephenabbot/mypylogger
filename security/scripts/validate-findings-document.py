#!/usr/bin/env python3
"""Validation script for SECURITY_FINDINGS.md document.

This script validates that the generated security findings document meets
CI/CD requirements and has the proper structure and content format.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import sys


class DocumentValidationError(Exception):
    """Exception raised when document validation fails."""


class FindingsDocumentValidator:
    """Validates the structure and content of SECURITY_FINDINGS.md."""

    def __init__(self, document_path: Path | str | None = None) -> None:
        """Initialize the validator.

        Args:
            document_path: Path to the SECURITY_FINDINGS.md file.
                          Defaults to security/findings/SECURITY_FINDINGS.md
        """
        if document_path is None:
            document_path = Path("security/findings/SECURITY_FINDINGS.md")

        self.document_path = Path(document_path)
        self.content = ""
        self.lines = []
        self.validation_errors = []

    def validate_document(self) -> bool:
        """Validate the complete document.

        Returns:
            True if document is valid, False otherwise

        Raises:
            DocumentValidationError: If critical validation errors are found
        """
        try:
            self._load_document()
            self._validate_structure()
            self._validate_header()
            self._validate_findings_sections()
            self._validate_remediation_summary()
            self._validate_format_compliance()

            if self.validation_errors:
                error_msg = (
                    f"Document validation failed with {len(self.validation_errors)} errors:\n"
                )
                error_msg += "\n".join(f"- {error}" for error in self.validation_errors)
                raise DocumentValidationError(error_msg)

            return True

        except Exception as e:
            if isinstance(e, DocumentValidationError):
                raise
            msg = f"Validation failed with error: {e}"
            raise DocumentValidationError(msg) from e

    def _load_document(self) -> None:
        """Load the document content."""
        if not self.document_path.exists():
            msg = f"Document not found: {self.document_path}"
            raise DocumentValidationError(msg)

        try:
            with self.document_path.open("r", encoding="utf-8") as f:
                self.content = f.read()
            self.lines = self.content.split("\n")
        except Exception as e:
            msg = f"Failed to read document: {e}"
            raise DocumentValidationError(msg) from e

    def _validate_structure(self) -> None:
        """Validate the overall document structure."""
        required_sections = [
            "# Security Findings Summary",
            "## Current Findings",
            "## Remediation Summary",
        ]

        for section in required_sections:
            if section not in self.content:
                self.validation_errors.append(f"Missing required section: {section}")

    def _validate_header(self) -> None:
        """Validate the document header information."""
        # Check for required header fields
        required_fields = [
            r"\*\*Last Updated\*\*:",
            r"\*\*Total Active Findings\*\*:",
            r"\*\*Days Since Last Scan\*\*:",
            r"\*\*Severity Breakdown\*\*:",
        ]

        for field_pattern in required_fields:
            if not re.search(field_pattern, self.content):
                self.validation_errors.append(f"Missing header field: {field_pattern}")

        # Validate timestamp format
        timestamp_match = re.search(r"\*\*Last Updated\*\*: (.+)", self.content)
        if timestamp_match:
            timestamp_str = timestamp_match.group(1)
            try:
                # Try to parse the timestamp
                datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S UTC")
            except ValueError:
                self.validation_errors.append(f"Invalid timestamp format: {timestamp_str}")

    def _validate_findings_sections(self) -> None:
        """Validate the findings sections."""
        # Check for severity sections
        severity_sections = re.findall(r"### (\w+) Severity", self.content)

        if not severity_sections:
            # If no findings, should have appropriate message
            if (
                "No active security findings" not in self.content
                and "Total Active Findings**: 0" not in self.content
            ):
                self.validation_errors.append(
                    "Document should have severity sections or indicate no findings"
                )

        # Validate finding entries
        finding_entries = re.findall(r"#### ([A-Z0-9-]+) - (.+)", self.content)

        for finding_id, title in finding_entries:
            self._validate_finding_entry(finding_id, title)

    def _validate_finding_entry(self, finding_id: str, title: str) -> None:
        """Validate a single finding entry.

        Args:
            finding_id: The finding identifier
            title: The finding title
        """
        # Check for required finding fields
        finding_section = self._extract_finding_section(finding_id)
        if not finding_section:
            self.validation_errors.append(f"Could not extract section for finding: {finding_id}")
            return

        required_fields = [
            "Package",
            "Source",
            "Discovered",
            "Description",
            "Impact",
            "Fix Available",
        ]

        for field in required_fields:
            if f"**{field}**:" not in finding_section:
                self.validation_errors.append(f"Missing field '{field}' in finding {finding_id}")

    def _extract_finding_section(self, finding_id: str) -> str:
        """Extract the content section for a specific finding.

        Args:
            finding_id: The finding identifier

        Returns:
            The content section for the finding
        """
        # Find the start of this finding
        start_pattern = f"#### {finding_id} -"
        start_idx = self.content.find(start_pattern)
        if start_idx == -1:
            return ""

        # Find the end (next finding or section)
        remaining_content = self.content[start_idx:]
        next_finding = re.search(r"\n#### [A-Z0-9-]+ -", remaining_content[1:])
        next_section = re.search(r"\n## ", remaining_content[1:])

        if next_finding and next_section:
            end_idx = min(next_finding.start() + 1, next_section.start() + 1)
        elif next_finding:
            end_idx = next_finding.start() + 1
        elif next_section:
            end_idx = next_section.start() + 1
        else:
            end_idx = len(remaining_content)

        return remaining_content[:end_idx]

    def _validate_remediation_summary(self) -> None:
        """Validate the remediation summary section."""
        remediation_section = self._extract_remediation_section()

        if not remediation_section:
            self.validation_errors.append("Could not find remediation summary section")
            return

        # Check for summary statistics
        if "**Total Plans**:" not in remediation_section:
            self.validation_errors.append("Missing 'Total Plans' in remediation summary")

    def _extract_remediation_section(self) -> str:
        """Extract the remediation summary section.

        Returns:
            The remediation summary section content
        """
        start_idx = self.content.find("## Remediation Summary")
        if start_idx == -1:
            return ""

        # Find the end (next section or end of document)
        remaining_content = self.content[start_idx:]
        next_section = re.search(r"\n## ", remaining_content[1:])

        end_idx = next_section.start() + 1 if next_section else len(remaining_content)

        return remaining_content[:end_idx]

    def _validate_format_compliance(self) -> None:
        """Validate format compliance for automated processing."""
        # Check for proper markdown formatting
        if not self.content.startswith("# "):
            self.validation_errors.append("Document should start with H1 header")

        # Check for consistent bullet point formatting
        bullet_lines = [line for line in self.lines if line.strip().startswith("- **")]
        for line in bullet_lines:
            if not re.match(r"- \*\*[^*]+\*\*:", line.strip()):
                self.validation_errors.append(f"Inconsistent bullet format: {line.strip()}")

        # Check for proper link formatting
        links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", self.content)
        for _link_text, url in links:
            if not url.startswith(("http://", "https://")):
                self.validation_errors.append(f"Invalid URL format: {url}")

    def get_validation_report(self) -> dict[str, any]:
        """Get a detailed validation report.

        Returns:
            Dictionary containing validation results and statistics
        """
        try:
            self._load_document()
        except Exception as e:
            return {"valid": False, "error": str(e), "statistics": {}}

        # Extract statistics
        total_findings = self._extract_statistic(r"\*\*Total Active Findings\*\*: (\d+)")
        last_updated = self._extract_statistic(r"\*\*Last Updated\*\*: (.+)")

        severity_breakdown = {}
        severity_matches = re.findall(r"- \*\*(\w+)\*\*: (\d+)", self.content)
        for severity, count in severity_matches:
            severity_breakdown[severity.lower()] = int(count)

        return {
            "valid": len(self.validation_errors) == 0,
            "errors": self.validation_errors,
            "statistics": {
                "total_findings": int(total_findings) if total_findings else 0,
                "last_updated": last_updated,
                "severity_breakdown": severity_breakdown,
                "document_size": len(self.content),
                "line_count": len(self.lines),
            },
        }

    def _extract_statistic(self, pattern: str) -> str | None:
        """Extract a statistic using regex pattern.

        Args:
            pattern: Regex pattern to match

        Returns:
            Matched value or None
        """
        match = re.search(pattern, self.content)
        return match.group(1) if match else None


def main() -> int | None:
    """Main validation function."""
    print("🔍 Security Findings Document Validation")
    print("=" * 45)

    try:
        validator = FindingsDocumentValidator()

        print("📄 Validating document structure and content...")
        is_valid = validator.validate_document()

        if is_valid:
            print("✅ Document validation passed!")

            # Get detailed report
            report = validator.get_validation_report()
            stats = report["statistics"]

            print("\n📊 Document Statistics:")
            print(f"  Total Findings: {stats['total_findings']}")
            print(f"  Last Updated: {stats['last_updated']}")
            print(f"  Document Size: {stats['document_size']} bytes")
            print(f"  Line Count: {stats['line_count']}")

            if stats["severity_breakdown"]:
                print("  Severity Breakdown:")
                for severity, count in stats["severity_breakdown"].items():
                    print(f"    {severity.title()}: {count}")

            print("\n🎉 Document is ready for CI/CD processing!")
            return 0

    except DocumentValidationError as e:
        print("❌ Document validation failed:")
        print(f"   {e}")
        return 1

    except Exception as e:
        print(f"❌ Validation error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
