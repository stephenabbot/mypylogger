#!/usr/bin/env python3
"""Migration script to move legacy security-reports/ to new security/reports/ structure.

This script:
1. Moves existing security-reports/ content to security/reports/archived/ with date organization
2. Copies latest scan outputs to security/reports/latest/ for current data
3. Generates initial findings document from existing vulnerability data
4. Creates initial remediation registry with current known vulnerabilities
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import sys
from typing import TYPE_CHECKING

# Add security module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from security.generator import FindingsDocumentGenerator
from security.parsers import parse_scanner_file
from security.synchronizer import RemediationSynchronizer

if TYPE_CHECKING:
    from security.models import SecurityFinding


def extract_date_from_filename(filename: str) -> str | None:
    """Extract date from filename like 'bandit-20251024_142609.json'."""
    try:
        # Extract date part (YYYYMMDD)
        if "_" in filename:
            date_part = filename.split("_")[0].split("-")[-1]
            if len(date_part) == 8 and date_part.isdigit():
                year = date_part[:4]
                month = date_part[4:6]
                day = date_part[6:8]
                return f"{year}-{month}-{day}"
    except (IndexError, ValueError):
        pass
    return None


def organize_files_by_date(source_dir: Path) -> dict[str, list[Path]]:
    """Organize files by extracted dates."""
    files_by_date = {}

    for file_path in source_dir.glob("*"):
        if file_path.is_file():
            date_str = extract_date_from_filename(file_path.name)
            if date_str:
                if date_str not in files_by_date:
                    files_by_date[date_str] = []
                files_by_date[date_str].append(file_path)
            else:
                # Use today's date for files without date
                today = datetime.now().strftime("%Y-%m-%d")
                if today not in files_by_date:
                    files_by_date[today] = []
                files_by_date[today].append(file_path)

    return files_by_date


def get_latest_files(files_by_date: dict[str, list[Path]]) -> dict[str, Path]:
    """Get the latest version of each file type."""
    if not files_by_date:
        return {}

    # Get the most recent date
    latest_date = max(files_by_date.keys())
    latest_files = files_by_date[latest_date]

    # Organize by file type
    latest_by_type = {}
    for file_path in latest_files:
        if "pip-audit" in file_path.name:
            latest_by_type["pip-audit"] = file_path
        elif "bandit" in file_path.name:
            latest_by_type["bandit"] = file_path
        elif "dependency-tree" in file_path.name:
            latest_by_type["dependency-tree"] = file_path
        elif "security-summary" in file_path.name:
            latest_by_type["security-summary"] = file_path

    return latest_by_type


def migrate_reports() -> bool:
    """Main migration function."""
    print("🔄 Starting security reports migration...")

    # Define paths
    legacy_dir = Path("security-reports")
    new_archived_dir = Path("security/reports/archived")
    new_latest_dir = Path("security/reports/latest")

    if not legacy_dir.exists():
        print("❌ Legacy security-reports/ directory not found")
        return False

    # Ensure target directories exist
    new_archived_dir.mkdir(parents=True, exist_ok=True)
    new_latest_dir.mkdir(parents=True, exist_ok=True)

    # Organize files by date
    files_by_date = organize_files_by_date(legacy_dir)
    print(f"📅 Found files for {len(files_by_date)} dates")

    # Move files to archived directories organized by date
    for date_str, files in files_by_date.items():
        date_dir = new_archived_dir / date_str
        date_dir.mkdir(exist_ok=True)

        for file_path in files:
            target_path = date_dir / file_path.name
            print(f"📁 Moving {file_path} -> {target_path}")
            shutil.copy2(file_path, target_path)

    # Copy latest files to latest directory
    latest_files = get_latest_files(files_by_date)
    print(f"📋 Copying {len(latest_files)} latest files to security/reports/latest/")

    for file_type, file_path in latest_files.items():
        if file_type == "pip-audit":
            target_name = "pip-audit.json"
        elif file_type == "bandit":
            target_name = "bandit.json"
        elif file_type == "dependency-tree":
            target_name = "dependency-tree.txt"
        elif file_type == "security-summary":
            target_name = "security-summary.json"
        else:
            target_name = file_path.name

        target_path = new_latest_dir / target_name
        print(f"📄 Copying {file_path} -> {target_path}")
        shutil.copy2(file_path, target_path)

    return True


def generate_initial_findings():
    """Generate initial findings document from migrated data."""
    print("📝 Generating initial findings document...")

    latest_dir = Path("security/reports/latest")
    pip_audit_file = latest_dir / "pip-audit.json"
    bandit_file = latest_dir / "bandit.json"

    findings = []

    # Parse pip-audit findings
    if pip_audit_file.exists():
        try:
            pip_findings = parse_scanner_file(pip_audit_file, "pip-audit")
            findings.extend(pip_findings)
            print(f"✅ Parsed {len(pip_findings)} pip-audit findings")
        except Exception as e:
            print(f"⚠️ Error parsing pip-audit file: {e}")

    # Parse bandit findings
    if bandit_file.exists():
        try:
            bandit_findings = parse_scanner_file(bandit_file, "bandit")
            findings.extend(bandit_findings)
            print(f"✅ Parsed {len(bandit_findings)} bandit findings")
        except Exception as e:
            print(f"⚠️ Error parsing bandit file: {e}")

    # Generate findings document
    if findings:
        generator = FindingsDocumentGenerator()
        generator.generate_document()
        print(f"📄 Generated findings document with {len(findings)} findings")
    else:
        print("ℹ️ No findings to generate document from")

    return findings


def create_initial_remediation_registry(findings: list[SecurityFinding]) -> None:
    """Create initial remediation registry from findings."""
    print("🔧 Creating initial remediation registry...")

    try:
        synchronizer = RemediationSynchronizer()

        # Sync findings to create remediation entries
        result = synchronizer.synchronize_findings()

        print(f"✅ Created remediation entries: {result}")

    except Exception as e:
        print(f"⚠️ Error creating remediation registry: {e}")


def main() -> int | None:
    """Main migration process."""
    print("🚀 Security Infrastructure Migration")
    print("=" * 40)

    try:
        # Step 1: Migrate reports
        if not migrate_reports():
            print("❌ Migration failed")
            return 1

        # Step 2: Generate initial findings
        findings = generate_initial_findings()

        # Step 3: Create remediation registry
        create_initial_remediation_registry(findings)

        print("\n✅ Migration completed successfully!")
        print("📁 Legacy files archived in security/reports/archived/")
        print("📄 Latest files available in security/reports/latest/")
        print("📝 Initial findings document generated")
        print("🔧 Initial remediation registry created")

        return 0

    except Exception as e:
        print(f"❌ Migration failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
