"""Release notes and justification generator for security-driven releases.

This module provides comprehensive release notes generation with templates
for different types of security-driven releases.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

from scripts.release_automation_engine import ReleaseType, SecurityChange, SecurityChangeType


class ReleaseNotesTemplate:
    """Base class for release notes templates."""

    def generate(self, **kwargs: Any) -> str:
        """Generate release notes from template.

        Args:
            **kwargs: Template variables

        Returns:
            Formatted release notes
        """
        raise NotImplementedError


class SecurityDrivenReleaseTemplate(ReleaseNotesTemplate):
    """Template for security-driven automatic releases."""

    def generate(
        self,
        security_changes: list[SecurityChange],
        version: str | None = None,
        timestamp: datetime | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate security-driven release notes.

        Args:
            security_changes: List of security changes
            version: Package version being released
            timestamp: Release timestamp
            **kwargs: Additional template variables

        Returns:
            Formatted release notes
        """
        timestamp = timestamp or datetime.now(timezone.utc)

        notes = f"""# Security-Driven Release{f" v{version}" if version else ""}

**Release Date**: {timestamp.strftime("%Y-%m-%d %H:%M UTC")}
**Release Type**: Automatic Security Release

## Overview

This release was automatically triggered due to changes in the security posture of the project. The release ensures that users have access to the most current security information and documentation.

"""

        # Group changes by type
        new_vulns = [
            c for c in security_changes if c.change_type == SecurityChangeType.NEW_VULNERABILITY
        ]
        resolved_vulns = [
            c
            for c in security_changes
            if c.change_type == SecurityChangeType.RESOLVED_VULNERABILITY
        ]
        severity_changes = [
            c for c in security_changes if c.change_type == SecurityChangeType.SEVERITY_CHANGE
        ]

        if new_vulns:
            notes += "## 🚨 New Security Findings\n\n"
            notes += "The following new security findings have been identified:\n\n"

            # Group by severity
            critical_high = [c for c in new_vulns if c.impact_level.lower() in {"critical", "high"}]
            medium_low = [
                c for c in new_vulns if c.impact_level.lower() in {"medium", "low", "info"}
            ]

            if critical_high:
                notes += "### High/Critical Severity\n"
                for change in critical_high:
                    notes += f"- **{change.finding_id}** ({change.impact_level.upper()} severity)\n"
                notes += "\n"

            if medium_low:
                notes += "### Medium/Low Severity\n"
                for change in medium_low:
                    notes += f"- **{change.finding_id}** ({change.impact_level.title()} severity)\n"
                notes += "\n"

        if resolved_vulns:
            notes += "## ✅ Resolved Security Findings\n\n"
            notes += "The following security findings have been resolved:\n\n"
            for change in resolved_vulns:
                notes += f"- **{change.finding_id}** (Previously {change.old_state})\n"
            notes += "\n"

        if severity_changes:
            notes += "## 📊 Severity Changes\n\n"
            notes += "The following findings have had severity changes:\n\n"
            for change in severity_changes:
                notes += f"- **{change.finding_id}**: {change.old_state} → {change.new_state}\n"
            notes += "\n"

        notes += """## 📋 Security Documentation

For detailed security information and remediation plans, please see:

- [Security Findings Document](security/findings/SECURITY_FINDINGS.md)
- [Live Security Status](https://username.github.io/mypylogger/security-status) *(coming soon)*
- [Security Policy](SECURITY.md)

## 🔄 Automated Release Process

This release was generated automatically by our security-driven release system:

1. **Weekly Security Scan**: Automated security scanning detected changes
2. **Change Analysis**: Security findings were compared with previous scan
3. **Release Decision**: Automatic release triggered based on security changes
4. **Documentation Update**: Security findings document updated with latest information

## 📦 Package Information

- **Package**: mypylogger
- **Installation**: `pip install mypylogger`
- **Documentation**: [GitHub Repository](https://github.com/username/mypylogger)

## 🛡️ Security Commitment

We are committed to transparency in security matters. This automated release system ensures that:

- Security findings are promptly documented and communicated
- Users have access to current security information
- Remediation efforts are tracked and reported
- Security posture changes trigger appropriate notifications

---

*This release was automatically generated by the security-driven release system.*
"""

        return notes


class ManualReleaseTemplate(ReleaseNotesTemplate):
    """Template for manual releases."""

    def generate(
        self,
        custom_notes: str | None = None,
        version: str | None = None,
        timestamp: datetime | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate manual release notes.

        Args:
            custom_notes: Custom release notes provided by user
            version: Package version being released
            timestamp: Release timestamp
            **kwargs: Additional template variables

        Returns:
            Formatted release notes
        """
        timestamp = timestamp or datetime.now(timezone.utc)

        notes = f"""# Manual Release{f" v{version}" if version else ""}

**Release Date**: {timestamp.strftime("%Y-%m-%d %H:%M UTC")}
**Release Type**: Manual Release

## Overview

This release was triggered manually and may include code improvements, bug fixes, feature enhancements, or other updates.

"""

        if custom_notes:
            notes += f"""## Release Notes

{custom_notes}

"""

        notes += """## 🛡️ Security Status

For current security information, please see:

- [Security Findings Document](security/findings/SECURITY_FINDINGS.md)
- [Live Security Status](https://username.github.io/mypylogger/security-status) *(coming soon)*

## 📦 Package Information

- **Package**: mypylogger
- **Installation**: `pip install mypylogger`
- **Documentation**: [GitHub Repository](https://github.com/username/mypylogger)

---

*For questions about this release, please open an issue on GitHub.*
"""

        return notes


class VulnerabilityResolutionTemplate(ReleaseNotesTemplate):
    """Template specifically for vulnerability resolution releases."""

    def generate(
        self,
        resolved_vulnerabilities: list[SecurityChange],
        version: str | None = None,
        timestamp: datetime | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate vulnerability resolution release notes.

        Args:
            resolved_vulnerabilities: List of resolved vulnerabilities
            version: Package version being released
            timestamp: Release timestamp
            **kwargs: Additional template variables

        Returns:
            Formatted release notes
        """
        timestamp = timestamp or datetime.now(timezone.utc)

        notes = f"""# Security Resolution Release{f" v{version}" if version else ""}

**Release Date**: {timestamp.strftime("%Y-%m-%d %H:%M UTC")}
**Release Type**: Vulnerability Resolution

## 🎉 Security Improvements

This release addresses the resolution of security vulnerabilities, improving the overall security posture of the project.

## ✅ Resolved Vulnerabilities

The following security findings have been resolved:

"""

        for vuln in resolved_vulnerabilities:
            notes += f"""### {vuln.finding_id}
- **Previous Status**: {vuln.old_state}
- **Current Status**: {vuln.new_state}
- **Impact Level**: {vuln.impact_level.title()}

"""

        notes += """## 📈 Security Impact

With these resolutions:
- Overall security posture has improved
- Risk exposure has been reduced
- Security documentation has been updated

## 🔄 Next Steps

- Review updated security documentation
- Consider updating dependencies if applicable
- Monitor for any new security findings

## 📋 Security Documentation

For complete security information:

- [Security Findings Document](security/findings/SECURITY_FINDINGS.md)
- [Live Security Status](https://username.github.io/mypylogger/security-status) *(coming soon)*
- [Security Policy](SECURITY.md)

---

*This release was automatically generated due to vulnerability resolution.*
"""

        return notes


class ReleaseJustificationGenerator:
    """Generates release justifications for transparency and audit purposes."""

    def __init__(self) -> None:
        """Initialize the justification generator."""
        self.templates = {
            "security_auto": SecurityDrivenReleaseTemplate(),
            "manual": ManualReleaseTemplate(),
            "vulnerability_resolution": VulnerabilityResolutionTemplate(),
        }

    def generate_justification(
        self,
        release_type: ReleaseType,
        security_changes: list[SecurityChange],
        custom_notes: str | None = None,
    ) -> str:
        """Generate release justification.

        Args:
            release_type: Type of release
            security_changes: List of security changes
            custom_notes: Custom notes if provided

        Returns:
            Release justification text
        """
        if release_type == ReleaseType.MANUAL:
            return self._generate_manual_justification(custom_notes)

        if release_type == ReleaseType.SECURITY_AUTO:
            return self._generate_security_justification(security_changes)

        return "Release justification not available"

    def _generate_manual_justification(self, custom_notes: str | None) -> str:
        """Generate justification for manual releases."""
        base = "Manual release requested by maintainer"

        if custom_notes:
            return f"{base}: {custom_notes}"

        return f"{base}. May include code improvements, bug fixes, or feature updates."

    def _generate_security_justification(self, security_changes: list[SecurityChange]) -> str:
        """Generate justification for security-driven releases."""
        if not security_changes:
            return "Security-driven release triggered (no specific changes detected)"

        # Analyze changes
        new_high = [
            c
            for c in security_changes
            if c.change_type == SecurityChangeType.NEW_VULNERABILITY
            and c.impact_level.lower() in {"critical", "high"}
        ]

        new_other = [
            c
            for c in security_changes
            if c.change_type == SecurityChangeType.NEW_VULNERABILITY
            and c.impact_level.lower() not in {"critical", "high"}
        ]

        resolved = [
            c
            for c in security_changes
            if c.change_type == SecurityChangeType.RESOLVED_VULNERABILITY
        ]

        severity_changes = [
            c for c in security_changes if c.change_type == SecurityChangeType.SEVERITY_CHANGE
        ]

        reasons = []

        if new_high:
            count = len(new_high)
            reasons.append(f"{count} new high/critical vulnerabilit{'y' if count == 1 else 'ies'}")

        if new_other:
            count = len(new_other)
            reasons.append(f"{count} new medium/low vulnerabilit{'y' if count == 1 else 'ies'}")

        if resolved:
            count = len(resolved)
            reasons.append(f"{count} vulnerabilit{'y' if count == 1 else 'ies'} resolved")

        if severity_changes:
            count = len(severity_changes)
            reasons.append(f"{count} severit{'y' if count == 1 else 'ies'} changed")

        if reasons:
            return f"Security-driven release: {', '.join(reasons)}"

        return "Security-driven release triggered by security posture changes"


class ComprehensiveReleaseNotesGenerator:
    """Comprehensive release notes generator with multiple templates."""

    def __init__(self) -> None:
        """Initialize the comprehensive generator."""
        self.templates = {
            ReleaseType.SECURITY_AUTO: SecurityDrivenReleaseTemplate(),
            ReleaseType.MANUAL: ManualReleaseTemplate(),
        }
        self.justification_generator = ReleaseJustificationGenerator()

    def generate_complete_release_notes(
        self,
        release_type: ReleaseType,
        security_changes: list[SecurityChange],
        version: str | None = None,
        custom_notes: str | None = None,
        timestamp: datetime | None = None,
    ) -> dict[str, str]:
        """Generate complete release notes package.

        Args:
            release_type: Type of release
            security_changes: List of security changes
            version: Package version
            custom_notes: Custom release notes
            timestamp: Release timestamp

        Returns:
            Dictionary with release notes, justification, and summary
        """
        timestamp = timestamp or datetime.now(timezone.utc)

        # Generate main release notes
        template = self.templates.get(release_type)
        if template:
            if release_type == ReleaseType.SECURITY_AUTO:
                release_notes = template.generate(
                    security_changes=security_changes,
                    version=version,
                    timestamp=timestamp,
                )
            else:  # Manual release
                release_notes = template.generate(
                    custom_notes=custom_notes,
                    version=version,
                    timestamp=timestamp,
                )
        else:
            release_notes = "Release notes not available for this release type"

        # Generate justification
        justification = self.justification_generator.generate_justification(
            release_type, security_changes, custom_notes
        )

        # Generate summary
        summary = self._generate_summary(release_type, security_changes, version)

        return {
            "release_notes": release_notes,
            "justification": justification,
            "summary": summary,
            "timestamp": timestamp.isoformat(),
            "release_type": release_type.value,
        }

    def _generate_summary(
        self,
        release_type: ReleaseType,
        security_changes: list[SecurityChange],
        version: str | None = None,
    ) -> str:
        """Generate a brief release summary.

        Args:
            release_type: Type of release
            security_changes: List of security changes
            version: Package version

        Returns:
            Brief release summary
        """
        version_text = f" v{version}" if version else ""

        if release_type == ReleaseType.MANUAL:
            return f"Manual release{version_text} with potential code updates and improvements"

        if release_type == ReleaseType.SECURITY_AUTO:
            if not security_changes:
                return f"Security-driven release{version_text} (no specific changes)"

            change_count = len(security_changes)
            high_critical = sum(
                1 for c in security_changes if c.impact_level.lower() in {"critical", "high"}
            )

            if high_critical > 0:
                return f"Security release{version_text}: {high_critical} high/critical findings among {change_count} total changes"
            return f"Security release{version_text}: {change_count} security finding changes"

        return f"Release{version_text}"

    def save_release_notes(
        self,
        release_notes_data: dict[str, str],
        output_dir: Path | None = None,
    ) -> dict[str, Path]:
        """Save release notes to files.

        Args:
            release_notes_data: Release notes data from generate_complete_release_notes
            output_dir: Output directory (defaults to current directory)

        Returns:
            Dictionary mapping content type to file path
        """
        output_dir = output_dir or Path()
        output_dir.mkdir(parents=True, exist_ok=True)

        files_created = {}

        # Save main release notes
        release_notes_file = output_dir / "RELEASE_NOTES.md"
        release_notes_file.write_text(release_notes_data["release_notes"])
        files_created["release_notes"] = release_notes_file

        # Save justification
        justification_file = output_dir / "RELEASE_JUSTIFICATION.txt"
        justification_file.write_text(release_notes_data["justification"])
        files_created["justification"] = justification_file

        # Save summary
        summary_file = output_dir / "RELEASE_SUMMARY.txt"
        summary_file.write_text(release_notes_data["summary"])
        files_created["summary"] = summary_file

        return files_created


def generate_security_release_notes(
    security_changes: list[SecurityChange],
    version: str | None = None,
    custom_notes: str | None = None,
    release_type: ReleaseType = ReleaseType.SECURITY_AUTO,
) -> dict[str, str]:
    """Convenience function to generate security release notes.

    Args:
        security_changes: List of security changes
        version: Package version
        custom_notes: Custom release notes
        release_type: Type of release

    Returns:
        Complete release notes package
    """
    generator = ComprehensiveReleaseNotesGenerator()
    return generator.generate_complete_release_notes(
        release_type=release_type,
        security_changes=security_changes,
        version=version,
        custom_notes=custom_notes,
    )


def main() -> None:
    """Main entry point for release notes generation."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Generate release notes")
    parser.add_argument(
        "--release-type",
        choices=["security_auto", "manual"],
        default="security_auto",
        help="Type of release",
    )
    parser.add_argument("--version", type=str, help="Package version")
    parser.add_argument("--custom-notes", type=str, help="Custom release notes")
    parser.add_argument("--changes-file", type=str, help="JSON file with security changes")
    parser.add_argument("--output-dir", type=str, default=".", help="Output directory")

    args = parser.parse_args()

    try:
        # Load security changes if provided
        security_changes = []
        if args.changes_file:
            with open(args.changes_file) as f:
                changes_data = json.load(f)
                # Convert to SecurityChange objects (simplified for CLI)
                for change_data in changes_data.get("security_changes", []):
                    from scripts.release_automation_engine import SecurityChange, SecurityChangeType

                    security_changes.append(
                        SecurityChange(
                            change_type=SecurityChangeType(change_data["type"]),
                            finding_id=change_data["finding_id"],
                            old_state=change_data.get("old_state"),
                            new_state=change_data["new_state"],
                            impact_level=change_data["impact_level"],
                        )
                    )

        # Generate release notes
        release_type = ReleaseType(args.release_type)
        generator = ComprehensiveReleaseNotesGenerator()

        release_notes_data = generator.generate_complete_release_notes(
            release_type=release_type,
            security_changes=security_changes,
            version=args.version,
            custom_notes=args.custom_notes,
        )

        # Save to files
        output_dir = Path(args.output_dir)
        files_created = generator.save_release_notes(release_notes_data, output_dir)

        print("✅ Release notes generated successfully:")
        for content_type, file_path in files_created.items():
            print(f"  {content_type}: {file_path}")

    except Exception as e:
        print(f"❌ Error generating release notes: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
