"""Tests for workflow validation functionality."""

from __future__ import annotations

from pathlib import Path
import tempfile
from unittest.mock import patch

import pytest
import yaml

from scripts.workflow_validation import WorkflowValidator, validate_repository_context


class TestWorkflowValidator:
    """Test cases for WorkflowValidator class."""

    def test_init(self) -> None:
        """Test WorkflowValidator initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            validator = WorkflowValidator(repo_root)

            assert validator.repo_root == repo_root
            assert validator.workflows_dir == repo_root / ".github" / "workflows"
            assert validator.validation_results == []

    def test_validate_all_workflows_no_directory(self) -> None:
        """Test validation when workflows directory doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            validator = WorkflowValidator(repo_root)

            result = validator.validate_all_workflows()
            assert result is False

    def test_validate_all_workflows_no_files(self) -> None:
        """Test validation when no workflow files exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            workflows_dir = repo_root / ".github" / "workflows"
            workflows_dir.mkdir(parents=True)

            validator = WorkflowValidator(repo_root)
            result = validator.validate_all_workflows()
            assert result is False

    def test_validate_workflow_file_invalid_yaml(self) -> None:
        """Test validation of workflow file with invalid YAML."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            workflows_dir = repo_root / ".github" / "workflows"
            workflows_dir.mkdir(parents=True)

            # Create invalid YAML file
            workflow_file = workflows_dir / "test.yml"
            workflow_file.write_text("invalid: yaml: content: [")

            validator = WorkflowValidator(repo_root)
            result = validator._validate_workflow_file(workflow_file)

            assert result["status"] == "FAIL"
            assert "Invalid YAML syntax" in result["message"]

    def test_validate_workflow_file_valid_basic(self) -> None:
        """Test validation of valid basic workflow file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            workflows_dir = repo_root / ".github" / "workflows"
            workflows_dir.mkdir(parents=True)

            # Create valid basic workflow
            workflow_data = {
                "name": "Test Workflow",
                "on": ["push"],
                "permissions": {"contents": "read"},
                "jobs": {
                    "test": {
                        "runs-on": "ubuntu-latest",
                        "steps": [{"name": "Checkout", "uses": "actions/checkout@v4"}],
                    }
                },
            }

            workflow_file = workflows_dir / "test.yml"
            with workflow_file.open("w") as f:
                yaml.dump(workflow_data, f)

            validator = WorkflowValidator(repo_root)
            result = validator._validate_workflow_file(workflow_file)

            assert result["status"] == "PASS"
            assert "All validations passed" in result["message"]

    def test_validate_basic_structure_missing_fields(self) -> None:
        """Test validation of workflow with missing required fields."""
        with tempfile.TemporaryDirectory() as temp_dir:
            validator = WorkflowValidator(Path(temp_dir))

            # Missing required fields
            workflow_data = {"name": "Test"}
            issues = validator._validate_basic_structure(workflow_data)

            assert len(issues) >= 2  # Missing 'on' and 'jobs'
            assert any("Missing required field: on" in issue for issue in issues)
            assert any("Missing required field: jobs" in issue for issue in issues)

    def test_validate_basic_structure_invalid_job(self) -> None:
        """Test validation of workflow with invalid job structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            validator = WorkflowValidator(Path(temp_dir))

            workflow_data = {
                "name": "Test",
                "on": ["push"],
                "jobs": {
                    "test": "invalid_job_data"  # Should be dict
                },
            }

            issues = validator._validate_basic_structure(workflow_data)
            assert any("Job 'test' must be a dictionary" in issue for issue in issues)

    def test_validate_permissions_git_operations(self) -> None:
        """Test permission validation for workflows with git operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            validator = WorkflowValidator(Path(temp_dir))

            workflow_data = {
                "permissions": {"contents": "read"},  # Should be write
                "jobs": {
                    "test": {
                        "steps": [
                            {"name": "Commit changes", "run": "git commit -m 'update' && git push"}
                        ]
                    }
                },
            }

            issues = validator._validate_permissions(workflow_data)
            assert any("contents: write" in issue for issue in issues)

    def test_validate_permissions_security_operations(self) -> None:
        """Test permission validation for workflows with security operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            validator = WorkflowValidator(Path(temp_dir))

            workflow_data = {
                "permissions": {"security-events": "read"},  # Should be write
                "jobs": {
                    "test": {
                        "steps": [
                            {
                                "name": "Upload security results",
                                "uses": "actions/upload-artifact@v4",
                            }
                        ]
                    }
                },
            }

            issues = validator._validate_permissions(workflow_data)
            assert any("security-events: write" in issue for issue in issues)

    def test_analyze_required_permissions_git_operations(self) -> None:
        """Test analysis of required permissions for git operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            validator = WorkflowValidator(Path(temp_dir))

            workflow_data = {
                "jobs": {
                    "test": {
                        "steps": [{"run": "git commit -m 'test'"}, {"run": "git push origin main"}]
                    }
                }
            }

            permissions = validator._analyze_required_permissions(workflow_data)
            assert permissions["contents_write"] is True
            assert permissions["contents_read"] is True

    def test_analyze_required_permissions_security_operations(self) -> None:
        """Test analysis of required permissions for security operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            validator = WorkflowValidator(Path(temp_dir))

            workflow_data = {
                "jobs": {
                    "test": {
                        "steps": [
                            {
                                "name": "Upload security scan results",
                                "uses": "actions/upload-artifact@v4",
                            }
                        ]
                    }
                }
            }

            permissions = validator._analyze_required_permissions(workflow_data)
            assert permissions["security_events_write"] is True

    def test_validate_repository_operations_missing_git_config(self) -> None:
        """Test validation of repository operations without git config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            validator = WorkflowValidator(Path(temp_dir))

            workflow_data = {
                "jobs": {
                    "test": {
                        "steps": [
                            {"run": "git push origin main"}  # No git config
                        ]
                    }
                }
            }

            issues = validator._validate_repository_operations(workflow_data)
            assert any("git operations but no git config setup" in issue for issue in issues)

    def test_validate_repository_operations_with_git_config(self) -> None:
        """Test validation of repository operations with proper git config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            validator = WorkflowValidator(Path(temp_dir))

            workflow_data = {
                "jobs": {
                    "test": {
                        "steps": [
                            {"run": "git config --local user.email 'test@example.com'"},
                            {"run": "git push origin main"},
                        ]
                    }
                }
            }

            issues = validator._validate_repository_operations(workflow_data)
            # Should not have git config issues
            assert not any("git operations but no git config setup" in issue for issue in issues)

    def test_validate_environment_variables_missing_test_vars(self) -> None:
        """Test validation of environment variables for test steps."""
        with tempfile.TemporaryDirectory() as temp_dir:
            validator = WorkflowValidator(Path(temp_dir))

            workflow_data = {
                "jobs": {
                    "test": {"steps": [{"name": "Run tests", "run": "./scripts/run_tests.sh"}]}
                }
            }

            issues = validator._validate_environment_variables(workflow_data)
            assert any("GITHUB_REPOSITORY" in issue for issue in issues)
            assert any("PYPI_PACKAGE" in issue for issue in issues)

    def test_validate_environment_variables_with_env_vars(self) -> None:
        """Test validation of environment variables when properly set."""
        with tempfile.TemporaryDirectory() as temp_dir:
            validator = WorkflowValidator(Path(temp_dir))

            workflow_data = {
                "jobs": {
                    "test": {
                        "env": {
                            "GITHUB_REPOSITORY": "${{ github.repository }}",
                            "PYPI_PACKAGE": "mypylogger",
                        },
                        "steps": [{"name": "Run tests", "run": "./scripts/run_tests.sh"}],
                    }
                }
            }

            issues = validator._validate_environment_variables(workflow_data)
            # Should not have missing environment variable issues
            test_env_issues = [issue for issue in issues if "missing environment variable" in issue]
            assert len(test_env_issues) == 0

    def test_generate_validation_report(self) -> None:
        """Test generation of validation report."""
        with tempfile.TemporaryDirectory() as temp_dir:
            validator = WorkflowValidator(Path(temp_dir))

            # Add some test results
            validator.validation_results = [
                {"status": "PASS", "workflow": "test1.yml"},
                {"status": "FAIL", "workflow": "test2.yml", "details": {"issues": ["issue1"]}},
                {"status": "PASS", "workflow": "test3.yml"},
            ]

            report = validator.generate_validation_report()

            assert report["summary"]["total_workflows"] == 3
            assert report["summary"]["passed_validations"] == 2
            assert report["summary"]["failed_validations"] == 1
            assert report["summary"]["success_rate"] == pytest.approx(66.67, rel=1e-2)
            assert len(report["validation_results"]) == 3
            assert len(report["recommendations"]) > 0

    def test_generate_recommendations_all_passed(self) -> None:
        """Test recommendation generation when all validations pass."""
        with tempfile.TemporaryDirectory() as temp_dir:
            validator = WorkflowValidator(Path(temp_dir))

            validator.validation_results = [
                {"status": "PASS", "workflow": "test1.yml"},
                {"status": "PASS", "workflow": "test2.yml"},
            ]

            recommendations = validator._generate_recommendations()
            assert "All workflow configurations are valid" in recommendations

    def test_generate_recommendations_with_failures(self) -> None:
        """Test recommendation generation with validation failures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            validator = WorkflowValidator(Path(temp_dir))

            validator.validation_results = [
                {
                    "status": "FAIL",
                    "workflow": "test.yml",
                    "details": {"issues": ["Missing permission", "Invalid config"]},
                }
            ]

            recommendations = validator._generate_recommendations()
            assert any("Fix workflow configuration issues" in rec for rec in recommendations)
            assert any("test.yml: Missing permission" in rec for rec in recommendations)
            assert any("test.yml: Invalid config" in rec for rec in recommendations)


class TestRepositoryContextValidation:
    """Test cases for repository context validation."""

    @patch.dict("os.environ", {}, clear=True)
    def test_validate_repository_context_missing_env_var(self) -> None:
        """Test repository context validation with missing environment variable."""
        result = validate_repository_context()
        assert result is False

    @patch.dict("os.environ", {"GITHUB_REPOSITORY": "wrong/repo"})
    def test_validate_repository_context_wrong_repo(self) -> None:
        """Test repository context validation with wrong repository."""
        result = validate_repository_context()
        assert result is False

    @patch.dict("os.environ", {"GITHUB_REPOSITORY": "stabbotco1/mypylogger"})
    def test_validate_repository_context_correct_repo(self) -> None:
        """Test repository context validation with correct repository."""
        result = validate_repository_context()
        assert result is True


class TestWorkflowValidationIntegration:
    """Integration tests for workflow validation."""

    def test_full_workflow_validation(self) -> None:
        """Test complete workflow validation process."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            workflows_dir = repo_root / ".github" / "workflows"
            workflows_dir.mkdir(parents=True)

            # Create a comprehensive test workflow
            workflow_data = {
                "name": "Test Workflow",
                "on": {"push": {"branches": ["main"]}},
                "permissions": {"contents": "write", "security-events": "write", "actions": "read"},
                "jobs": {
                    "test": {
                        "runs-on": "ubuntu-latest",
                        "env": {
                            "GITHUB_REPOSITORY": "${{ github.repository }}",
                            "PYPI_PACKAGE": "mypylogger",
                        },
                        "steps": [
                            {"name": "Checkout", "uses": "actions/checkout@v4"},
                            {
                                "name": "Configure Git",
                                "run": "git config --local user.email 'test@example.com'",
                            },
                            {"name": "Run tests", "run": "./scripts/run_tests.sh"},
                            {
                                "name": "Commit results",
                                "run": "git commit -m 'test results' && git push",
                            },
                        ],
                    }
                },
            }

            workflow_file = workflows_dir / "test.yml"
            with workflow_file.open("w") as f:
                yaml.dump(workflow_data, f)

            validator = WorkflowValidator(repo_root)
            result = validator.validate_all_workflows()

            assert result is True
            assert len(validator.validation_results) == 1
            assert validator.validation_results[0]["status"] == "PASS"

            # Test report generation
            report = validator.generate_validation_report()
            assert report["summary"]["success_rate"] == 100.0
            assert "All workflow configurations are valid" in report["recommendations"]
