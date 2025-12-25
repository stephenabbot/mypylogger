"""Integration script for security-driven release automation.

This script integrates the security scanning system with the release automation
engine to provide a complete security-driven release workflow.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import TYPE_CHECKING, Any

from scripts.release_automation_engine import ReleaseAutomationEngine
from scripts.security_change_detector import SecurityChangeDetector
from security.generator import generate_findings_document
from security.parsers import extract_all_findings

if TYPE_CHECKING:
    from security.models import SecurityFinding


class SecurityReleaseIntegrator:
    """Integrates security scanning with release automation."""

    def __init__(
        self,
        reports_dir: Path | None = None,
        findings_file: Path | None = None,
    ) -> None:
        """Initialize the security release integrator.

        Args:
            reports_dir: Directory containing security reports
            findings_file: Path to security findings document
        """
        self.reports_dir = reports_dir or Path("security/reports/latest")
        self.findings_file = findings_file or Path("security/findings/SECURITY_FINDINGS.md")
        self.detector = SecurityChangeDetector(reports_dir=self.reports_dir)
        self.engine = ReleaseAutomationEngine()

    def run_security_scan_and_analysis(
        self,
        force_release: bool = False,
        custom_notes: str | None = None,
    ) -> dict[str, Any]:
        """Run complete security scan and release analysis.

        Args:
            force_release: Whether to force a release regardless of changes
            custom_notes: Custom release notes to include

        Returns:
            Dictionary with complete analysis results
        """
        try:
            # Step 1: Load current security findings
            print("🔍 Loading current security findings...")
            current_findings = self._load_current_findings()
            print(f"Found {len(current_findings)} current security findings")

            # Step 2: Load previous findings for comparison
            print("📊 Loading previous findings for comparison...")
            previous_findings = self.detector.load_previous_findings()
            print(f"Found {len(previous_findings)} previous security findings")

            # Step 3: Detect security changes
            print("🔄 Detecting security changes...")
            changes = self.detector.detect_changes(previous_findings, current_findings)
            print(f"Detected {len(changes)} security changes")

            # Step 4: Make release decision
            print("🤔 Making release decision...")
            decision = self.engine.make_release_decision(
                changes, manual_trigger=force_release, custom_notes=custom_notes
            )

            # Step 5: Generate security posture analysis
            print("📈 Analyzing security posture...")
            posture_analysis = self.detector.analyze_security_posture_change(
                previous_findings, current_findings
            )

            # Step 6: Update findings document
            print("📝 Updating security findings document...")
            self._update_findings_document()

            # Compile results
            results = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "current_findings_count": len(current_findings),
                "previous_findings_count": len(previous_findings),
                "changes_detected": len(changes),
                "release_decision": {
                    "should_release": decision.should_release,
                    "release_type": decision.trigger_type.value,
                    "justification": decision.justification,
                    "release_notes": decision.release_notes,
                },
                "security_changes": [
                    {
                        "type": change.change_type.value,
                        "finding_id": change.finding_id,
                        "impact_level": change.impact_level,
                        "old_state": change.old_state,
                        "new_state": change.new_state,
                    }
                    for change in changes
                ],
                "security_posture": posture_analysis,
                "force_release": force_release,
                "custom_notes": custom_notes,
            }

            print("✅ Security scan and analysis completed successfully")
            return results

        except Exception as e:
            error_msg = f"Failed to run security scan and analysis: {e}"
            print(f"❌ {error_msg}")
            raise RuntimeError(error_msg) from e

    def _load_current_findings(self) -> list[SecurityFinding]:
        """Load current security findings."""
        try:
            if not self.reports_dir.exists():
                print(f"⚠️  Reports directory {self.reports_dir} does not exist")
                return []

            return extract_all_findings(self.reports_dir)

        except Exception as e:
            print(f"⚠️  Failed to load current findings: {e}")
            return []

    def _update_findings_document(self) -> None:
        """Update the security findings document."""
        try:
            generate_findings_document()
            print(f"✅ Updated findings document: {self.findings_file}")

        except Exception as e:
            print(f"⚠️  Failed to update findings document: {e}")

    def generate_release_summary(self, results: dict[str, Any]) -> str:
        """Generate a human-readable release summary.

        Args:
            results: Results from security scan and analysis

        Returns:
            Formatted release summary
        """
        decision = results["release_decision"]
        changes = results["security_changes"]
        posture = results["security_posture"]

        summary = f"""# Security-Driven Release Analysis

## Release Decision
- **Should Release**: {decision["should_release"]}
- **Release Type**: {decision["release_type"]}
- **Justification**: {decision["justification"]}

## Security Changes Detected
- **Total Changes**: {len(changes)}
- **Current Findings**: {results["current_findings_count"]}
- **Previous Findings**: {results["previous_findings_count"]}

"""

        if changes:
            summary += "### Change Details\n"
            for change in changes:
                summary += f"- **{change['finding_id']}**: {change['type']} ({change['impact_level']} severity)\n"
            summary += "\n"

        summary += f"""## Security Posture
- **Trend**: {posture["posture_trend"]}
- **Requires Attention**: {posture["requires_attention"]}
- **High/Critical Change**: {posture["high_critical_change"]}

## Timestamp
{results["timestamp"]}
"""

        return summary


def main() -> None:
    """Main entry point for security release integration."""
    import argparse

    parser = argparse.ArgumentParser(description="Security-driven release integration")
    parser.add_argument(
        "--force-release", action="store_true", help="Force release regardless of security changes"
    )
    parser.add_argument("--custom-notes", type=str, help="Custom release notes")
    parser.add_argument(
        "--output-file",
        type=str,
        default="release_analysis.json",
        help="Output file for analysis results",
    )
    parser.add_argument(
        "--summary-file",
        type=str,
        default="release_summary.md",
        help="Output file for human-readable summary",
    )

    args = parser.parse_args()

    try:
        # Run the integration
        integrator = SecurityReleaseIntegrator()
        results = integrator.run_security_scan_and_analysis(
            force_release=args.force_release,
            custom_notes=args.custom_notes,
        )

        # Save results to JSON file
        with open(args.output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"📄 Analysis results saved to: {args.output_file}")

        # Generate and save summary
        summary = integrator.generate_release_summary(results)
        with open(args.summary_file, "w") as f:
            f.write(summary)
        print(f"📋 Release summary saved to: {args.summary_file}")

        # Print key results
        decision = results["release_decision"]
        print(f"\n🎯 Release Decision: {decision['should_release']}")
        print(f"📝 Justification: {decision['justification']}")
        print(f"🔄 Changes Detected: {results['changes_detected']}")

        # Exit with appropriate code
        if decision["should_release"]:
            print("🚀 Release recommended - triggering PyPI publishing")
            sys.exit(0)
        else:
            print("⏭️  No release needed - security posture is stable")
            sys.exit(0)

    except Exception as e:
        print(f"❌ Error in security release integration: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
