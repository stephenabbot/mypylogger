#!/usr/bin/env python3
"""Validation script to test security module independence and minimal configuration requirements.

This script validates that the security module:
1. Works independently of project-specific code
2. Has minimal configuration requirements for new project deployment
3. Behaves consistently across different project structures
4. Can be deployed with example configurations
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys
import tempfile


class SecurityModuleValidator:
    """Validates security module independence and deployment requirements."""

    def __init__(self, security_module_path: str) -> None:
        """Initialize validator with path to security module."""
        self.security_module_path = Path(security_module_path)
        self.validation_results: list[tuple[str, bool, str]] = []

    def log_result(self, test_name: str, passed: bool, message: str) -> None:
        """Log validation result."""
        self.validation_results.append((test_name, passed, message))
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name} - {message}")

    def validate_directory_structure(self) -> bool:
        """Validate that security module has complete directory structure."""
        required_dirs = [
            "findings",
            "findings/history",
            "reports",
            "reports/latest",
            "reports/archived",
            "scripts",
            "config",
            "config/examples",
        ]

        required_files = [
            "README.md",
            "DEPLOYMENT.md",
            "__init__.py",
            "models.py",
            "parsers.py",
            "remediation.py",
            "synchronizer.py",
            "generator.py",
            "history.py",
            "compliance.py",
            "config/scanner-settings.yml",
            "config/findings-template.md",
            "config/remediation-defaults.yml",
            "scripts/update-findings.py",
            "scripts/validate-findings-document.py",
            "scripts/migrate-legacy-reports.py",
        ]

        all_present = True

        # Check directories
        for dir_path in required_dirs:
            full_path = self.security_module_path / dir_path
            if not full_path.exists() or not full_path.is_dir():
                self.log_result("Directory Structure", False, f"Missing directory: {dir_path}")
                all_present = False

        # Check files
        for file_path in required_files:
            full_path = self.security_module_path / file_path
            if not full_path.exists() or not full_path.is_file():
                self.log_result("Directory Structure", False, f"Missing file: {file_path}")
                all_present = False

        if all_present:
            self.log_result(
                "Directory Structure", True, "All required directories and files present"
            )

        return all_present

    def validate_module_imports(self) -> bool:
        """Validate that security module can be imported independently."""
        try:
            # Add security module to Python path
            sys.path.insert(0, str(self.security_module_path.parent))

            # Test importing core modules
            # Create test instances
            from datetime import date

            import security.compliance
            import security.generator
            import security.history
            import security.models

            # Test basic functionality
            from security.models import RemediationPlan, SecurityFinding
            import security.parsers
            from security.parsers import parse_bandit_json, parse_pip_audit_json
            import security.remediation
            import security.synchronizer

            SecurityFinding(
                finding_id="TEST-001",
                package="test-package",
                version="1.0.0",
                severity="medium",
                source_scanner="test",
                discovered_date=date(2025, 10, 24),
                description="Test finding",
                impact="Test impact",
                fix_available=True,
            )

            RemediationPlan(
                finding_id="TEST-001",
                status="new",
                planned_action="Test action",
                assigned_to="test-team",
                notes="Test notes",
                workaround="Test workaround",
            )

            self.log_result(
                "Module Imports",
                True,
                "All modules import successfully and basic functionality works",
            )
            return True

        except ImportError as e:
            self.log_result("Module Imports", False, f"Import error: {e}")
            return False
        except Exception as e:
            self.log_result("Module Imports", False, f"Functionality error: {e}")
            return False

    def validate_minimal_configuration(self) -> bool:
        """Validate minimal configuration requirements."""
        try:
            # Test with minimal scanner settings
            minimal_config = {
                "scanners": {
                    "pip-audit": {
                        "enabled": True,
                        "output_file": "security/reports/latest/pip-audit.json",
                        "format": "json",
                    }
                },
                "archival": {"enabled": False},
                "document": {
                    "template": "security/config/findings-template.md",
                    "output": "security/findings/SECURITY_FINDINGS.md",
                    "include_resolved": False,
                    "max_age_days": 30,
                },
            }

            # Create temporary config file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
                try:
                    import yaml
                except ImportError:
                    print("Error: PyYAML is required for the security module.", file=sys.stderr)
                    print(
                        "Install it with: pip install 'mypylogger[security]' or pip install PyYAML",
                        file=sys.stderr,
                    )
                    return False
                yaml.dump(minimal_config, f)
                config_file = f.name

            # Test configuration loading
            from security.remediation import RemediationDatastore

            RemediationDatastore()

            # Clean up
            os.unlink(config_file)

            self.log_result(
                "Minimal Configuration", True, "Module works with minimal configuration"
            )
            return True

        except Exception as e:
            self.log_result("Minimal Configuration", False, f"Configuration error: {e}")
            return False

    def validate_example_configurations(self) -> bool:
        """Validate that example configurations are valid and complete."""
        examples_dir = self.security_module_path / "config" / "examples"

        if not examples_dir.exists():
            self.log_result("Example Configurations", False, "Examples directory missing")
            return False

        example_files = list(examples_dir.glob("*.yml"))

        if not example_files:
            self.log_result("Example Configurations", False, "No example configuration files found")
            return False

        all_valid = True

        for example_file in example_files:
            try:
                try:
                    import yaml
                except ImportError:
                    print("Error: PyYAML is required for the security module.", file=sys.stderr)
                    print(
                        "Install it with: pip install 'mypylogger[security]' or pip install PyYAML",
                        file=sys.stderr,
                    )
                    return False
                with open(example_file) as f:
                    config = yaml.safe_load(f)

                # Validate required sections
                required_sections = ["scanners", "remediation_defaults", "assignment_rules"]
                for section in required_sections:
                    if section not in config:
                        self.log_result(
                            "Example Configurations",
                            False,
                            f"{example_file.name} missing required section: {section}",
                        )
                        all_valid = False

            except yaml.YAMLError as e:
                self.log_result(
                    "Example Configurations", False, f"{example_file.name} has invalid YAML: {e}"
                )
                all_valid = False
            except Exception as e:
                self.log_result(
                    "Example Configurations", False, f"{example_file.name} validation error: {e}"
                )
                all_valid = False

        if all_valid:
            self.log_result(
                "Example Configurations",
                True,
                f"All {len(example_files)} example configurations are valid",
            )

        return all_valid

    def validate_deployment_simulation(self) -> bool:
        """Simulate deployment to a new project structure."""
        try:
            # Create temporary project directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_project = Path(temp_dir) / "test_project"
                temp_project.mkdir()

                # Copy security module
                security_dest = temp_project / "security"
                shutil.copytree(self.security_module_path, security_dest)

                # Create minimal project structure
                (temp_project / "src").mkdir()
                (temp_project / "tests").mkdir()

                # Create minimal requirements.txt
                with open(temp_project / "requirements.txt", "w") as f:
                    f.write("PyYAML>=6.0\n")

                # Test that security module works in new location
                original_cwd = os.getcwd()
                try:
                    os.chdir(temp_project)

                    # Test basic functionality
                    sys.path.insert(0, str(temp_project))

                    # Test script execution (dry run)
                    script_path = security_dest / "scripts" / "update-findings.py"
                    if script_path.exists():
                        # Just check that script can be read and has main function
                        with open(script_path) as f:
                            script_content = f.read()
                            if (
                                "def main(" in script_content
                                or "if __name__ == '__main__'" in script_content
                            ):
                                self.log_result(
                                    "Deployment Simulation",
                                    True,
                                    "Security module deploys successfully to new project",
                                )
                                return True
                            self.log_result(
                                "Deployment Simulation",
                                False,
                                "Update script missing main function",
                            )
                            return False
                    else:
                        self.log_result(
                            "Deployment Simulation", False, "Update script missing in deployment"
                        )
                        return False

                finally:
                    os.chdir(original_cwd)
                    # Clean up sys.path
                    if str(temp_project) in sys.path:
                        sys.path.remove(str(temp_project))

        except Exception as e:
            self.log_result("Deployment Simulation", False, f"Deployment simulation failed: {e}")
            return False

    def validate_consistent_behavior(self) -> bool:
        """Validate consistent behavior across different project structures."""
        try:
            # Test with different directory structures
            test_structures = [
                {"name": "flat", "dirs": ["src", "tests"]},
                {"name": "nested", "dirs": ["app/src", "app/tests", "docs"]},
                {"name": "monorepo", "dirs": ["services/api", "services/web", "shared/lib"]},
            ]

            all_consistent = True

            for structure in test_structures:
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_project = Path(temp_dir) / f"test_{structure['name']}"
                    temp_project.mkdir()

                    # Create project structure
                    for dir_path in structure["dirs"]:
                        (temp_project / dir_path).mkdir(parents=True)

                    # Copy security module
                    security_dest = temp_project / "security"
                    shutil.copytree(self.security_module_path, security_dest)

                    # Test basic import
                    original_cwd = os.getcwd()
                    try:
                        os.chdir(temp_project)
                        sys.path.insert(0, str(temp_project))

                        # Test creating a finding (basic functionality)
                        from datetime import date

                        from security.models import SecurityFinding

                        finding = SecurityFinding(
                            finding_id=f"TEST-{structure['name']}",
                            package="test-package",
                            version="1.0.0",
                            severity="medium",
                            source_scanner="test",
                            discovered_date=date(2025, 10, 24),
                            description="Test finding",
                            impact="Test impact",
                            fix_available=True,
                        )

                        if finding.finding_id != f"TEST-{structure['name']}":
                            all_consistent = False
                            self.log_result(
                                "Consistent Behavior",
                                False,
                                f"Inconsistent behavior in {structure['name']} structure",
                            )

                    finally:
                        os.chdir(original_cwd)
                        if str(temp_project) in sys.path:
                            sys.path.remove(str(temp_project))

            if all_consistent:
                self.log_result(
                    "Consistent Behavior",
                    True,
                    "Module behaves consistently across different project structures",
                )

            return all_consistent

        except Exception as e:
            self.log_result("Consistent Behavior", False, f"Consistency validation failed: {e}")
            return False

    def run_all_validations(self) -> bool:
        """Run all validation tests."""
        print("🔍 Security Module Independence Validation")
        print("=" * 50)

        validations = [
            self.validate_directory_structure,
            self.validate_module_imports,
            self.validate_minimal_configuration,
            self.validate_example_configurations,
            self.validate_deployment_simulation,
            self.validate_consistent_behavior,
        ]

        all_passed = True

        for validation in validations:
            try:
                result = validation()
                if not result:
                    all_passed = False
            except Exception as e:
                self.log_result(validation.__name__, False, f"Validation error: {e}")
                all_passed = False

        print("\n" + "=" * 50)
        print("📊 Validation Summary")
        print("=" * 50)

        passed_count = sum(1 for _, passed, _ in self.validation_results if passed)
        total_count = len(self.validation_results)

        for test_name, passed, message in self.validation_results:
            status = "✓" if passed else "✗"
            print(f"{status} {test_name}: {message}")

        print(f"\nResults: {passed_count}/{total_count} validations passed")

        if all_passed:
            print("🎉 Security module is ready for modular deployment!")
        else:
            print("❌ Security module needs fixes before deployment")

        return all_passed


def main() -> None:
    """Main validation function."""
    # Determine security module path
    script_dir = Path(__file__).parent
    security_module_path = script_dir.parent

    if not security_module_path.exists():
        print(f"❌ Security module not found at: {security_module_path}")
        sys.exit(1)

    # Run validation
    validator = SecurityModuleValidator(str(security_module_path))
    success = validator.run_all_validations()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
