"""Tests for GitHub Pages security status API."""

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch

import pytest

from badges.github_pages import (
    GitHubActionsIntegration,
    GitHubPagesGenerator,
    get_default_pages_generator,
    update_github_pages_status,
)
from badges.live_status import SecurityStatus, SecurityStatusFinding, VulnerabilitySummary


class TestGitHubPagesGenerator:
    """Test GitHubPagesGenerator class."""

    def test_init_default_paths(self) -> None:
        """Test initialization with default paths."""
        generator = GitHubPagesGenerator()

        assert generator.pages_dir == Path("security-status")
        assert generator.status_manager is not None

    def test_init_custom_paths(self) -> None:
        """Test initialization with custom paths."""
        pages_dir = Path("/custom/pages")
        status_manager = Mock()

        generator = GitHubPagesGenerator(pages_dir, status_manager)

        assert generator.pages_dir == pages_dir
        assert generator.status_manager == status_manager

    def test_generate_api_endpoint_success(self) -> None:
        """Test successful API endpoint generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            pages_dir = temp_path / "pages"

            # Mock status manager
            mock_status_manager = Mock()
            mock_status = self._create_test_status()
            mock_status_manager.update_status.return_value = mock_status

            generator = GitHubPagesGenerator(pages_dir, mock_status_manager)
            generator.generate_api_endpoint()

            # Verify JSON file was created
            json_file = pages_dir / "index.json"
            assert json_file.exists()

            # Verify JSON content
            with json_file.open("r") as f:
                data = json.load(f)
            assert data["security_grade"] == "A"
            assert data["vulnerability_summary"]["total"] == 0

            # Verify JSONP file was created
            jsonp_file = pages_dir / "status.jsonp"
            assert jsonp_file.exists()

    def test_generate_html_page_success(self) -> None:
        """Test successful HTML page generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            pages_dir = temp_path / "pages"

            # Mock status manager
            mock_status_manager = Mock()
            mock_status = self._create_test_status()
            mock_status_manager.get_current_status.return_value = mock_status

            generator = GitHubPagesGenerator(pages_dir, mock_status_manager)
            generator.generate_html_page()

            # Verify HTML file was created
            html_file = pages_dir / "index.html"
            assert html_file.exists()

            # Verify HTML content
            with html_file.open("r") as f:
                content = f.read()
            assert "Security Status" in content
            assert "security-grade" in content
            assert mock_status.security_grade in content

    def test_generate_html_page_no_current_status(self) -> None:
        """Test HTML page generation when no current status exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            pages_dir = temp_path / "pages"

            # Mock status manager
            mock_status_manager = Mock()
            mock_status = self._create_test_status()
            mock_status_manager.get_current_status.return_value = None
            mock_status_manager.update_status.return_value = mock_status

            generator = GitHubPagesGenerator(pages_dir, mock_status_manager)
            generator.generate_html_page()

            # Verify HTML file was created
            html_file = pages_dir / "index.html"
            assert html_file.exists()

            # Verify update_status was called
            mock_status_manager.update_status.assert_called_once()

    def test_update_all_endpoints_success(self) -> None:
        """Test successful update of all endpoints."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            pages_dir = temp_path / "pages"

            # Mock status manager
            mock_status_manager = Mock()
            mock_status = self._create_test_status()
            mock_status_manager.update_status.return_value = mock_status
            mock_status_manager.get_current_status.return_value = mock_status

            generator = GitHubPagesGenerator(pages_dir, mock_status_manager)
            result_status = generator.update_all_endpoints()

            # Verify all files were created
            assert (pages_dir / "index.json").exists()
            assert (pages_dir / "index.html").exists()
            assert (pages_dir / "status.jsonp").exists()

            # Verify returned status
            assert result_status == mock_status

    def test_update_all_endpoints_no_status(self) -> None:
        """Test update endpoints when status retrieval fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            pages_dir = temp_path / "pages"

            # Mock status manager
            mock_status_manager = Mock()
            mock_status = self._create_test_status()
            mock_status_manager.update_status.return_value = mock_status
            mock_status_manager.get_current_status.return_value = None

            generator = GitHubPagesGenerator(pages_dir, mock_status_manager)

            with pytest.raises(RuntimeError, match="Failed to retrieve updated status"):
                generator.update_all_endpoints()

    def test_generate_html_content_no_vulnerabilities(self) -> None:
        """Test HTML content generation with no vulnerabilities."""
        generator = GitHubPagesGenerator()
        status = self._create_test_status()

        html_content = generator._generate_html_content(status)

        assert "Security Status" in html_content
        assert status.security_grade in html_content
        assert "No vulnerabilities found" in html_content
        assert "No Security Vulnerabilities Found" in html_content

    def test_generate_html_content_with_vulnerabilities(self) -> None:
        """Test HTML content generation with vulnerabilities."""
        generator = GitHubPagesGenerator()

        # Create status with vulnerabilities
        now = datetime.now(timezone.utc)
        summary = VulnerabilitySummary(total=2, high=1, medium=1)
        findings = [
            SecurityStatusFinding(
                finding_id="CVE-2023-0001",
                package="test-pkg",
                version="1.0.0",
                severity="high",
                discovered_date="2023-01-01",
                days_since_discovery=30,
                description="High severity vulnerability",
                fix_available=True,
                fix_version="1.0.1",
                reference_url="https://example.com/cve-2023-0001",
            ),
            SecurityStatusFinding(
                finding_id="CVE-2023-0002",
                package="test-pkg",
                version="1.0.0",
                severity="medium",
                discovered_date="2023-01-15",
                days_since_discovery=15,
                description="Medium severity vulnerability",
                fix_available=False,
            ),
        ]

        status = SecurityStatus(
            last_updated=now,
            scan_date=now,
            vulnerability_summary=summary,
            findings=findings,
            security_grade="C",
            days_since_last_vulnerability=15,
            remediation_status="pending",
        )

        html_content = generator._generate_html_content(status)

        assert "Security Status" in html_content
        assert "CVE-2023-0001" in html_content
        assert "CVE-2023-0002" in html_content
        assert "High severity vulnerability" in html_content
        assert "Medium severity vulnerability" in html_content
        assert "Fix Available" in html_content
        assert "No Fix Available" in html_content

    def test_generate_findings_html_empty(self) -> None:
        """Test findings HTML generation with empty list."""
        generator = GitHubPagesGenerator()

        html = generator._generate_findings_html([])

        assert "Current Findings" in html
        assert "No Security Vulnerabilities Found" in html

    def test_generate_findings_html_with_findings(self) -> None:
        """Test findings HTML generation with findings."""
        generator = GitHubPagesGenerator()

        findings = [
            SecurityStatusFinding(
                finding_id="CVE-2023-0001",
                package="test-pkg",
                version="1.0.0",
                severity="critical",
                discovered_date="2023-01-01",
                days_since_discovery=30,
                description="Critical vulnerability",
                fix_available=True,
                reference_url="https://example.com/cve",
            ),
        ]

        html = generator._generate_findings_html(findings)

        assert "Current Findings" in html
        assert "CVE-2023-0001" in html
        assert "CRITICAL" in html
        assert "Critical vulnerability" in html
        assert "View Details" in html

    def _create_test_status(self) -> SecurityStatus:
        """Create test SecurityStatus object."""
        now = datetime.now(timezone.utc)
        summary = VulnerabilitySummary(total=0)

        return SecurityStatus(
            last_updated=now,
            scan_date=now,
            vulnerability_summary=summary,
            security_grade="A",
            days_since_last_vulnerability=0,
            remediation_status="current",
        )


class TestGitHubActionsIntegration:
    """Test GitHubActionsIntegration class."""

    def test_init_default_generator(self) -> None:
        """Test initialization with default generator."""
        integration = GitHubActionsIntegration()

        assert integration.pages_generator is not None

    def test_init_custom_generator(self) -> None:
        """Test initialization with custom generator."""
        mock_generator = Mock()

        integration = GitHubActionsIntegration(mock_generator)

        assert integration.pages_generator == mock_generator

    def test_update_status_workflow_success(self) -> None:
        """Test successful workflow status update."""
        # Mock pages generator
        mock_generator = Mock()
        mock_status = Mock()
        mock_status.security_grade = "A"
        mock_status.vulnerability_summary.total = 0
        mock_status.remediation_status = "current"
        mock_generator.update_all_endpoints.return_value = mock_status

        integration = GitHubActionsIntegration(mock_generator)
        result = integration.update_status_workflow()

        assert result["success"] is True
        assert "duration_seconds" in result
        assert result["status"]["security_grade"] == "A"
        assert result["status"]["total_vulnerabilities"] == 0
        assert result["status"]["remediation_status"] == "current"
        assert "endpoints_updated" in result
        assert "timestamp" in result

    def test_update_status_workflow_failure(self) -> None:
        """Test workflow status update failure."""
        # Mock pages generator to raise exception
        mock_generator = Mock()
        mock_generator.update_all_endpoints.side_effect = RuntimeError("Update failed")

        integration = GitHubActionsIntegration(mock_generator)
        result = integration.update_status_workflow()

        assert result["success"] is False
        assert "Update failed" in result["error"]
        assert "timestamp" in result

    def test_create_workflow_file_default_path(self) -> None:
        """Test workflow file creation with default path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            workflow_path = temp_path / ".github" / "workflows" / "update-security-status.yml"

            integration = GitHubActionsIntegration()
            integration.create_workflow_file(workflow_path)

            assert workflow_path.exists()

            # Verify workflow content
            with workflow_path.open("r") as f:
                content = f.read()
            assert "name: Update Security Status" in content
            assert "schedule:" in content
            assert "workflow_dispatch:" in content
            assert "update-security-status:" in content

    def test_create_workflow_file_custom_path(self) -> None:
        """Test workflow file creation with custom path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            workflow_path = temp_path / "custom-workflow.yml"

            integration = GitHubActionsIntegration()
            integration.create_workflow_file(workflow_path)

            assert workflow_path.exists()

            # Verify workflow content
            with workflow_path.open("r") as f:
                content = f.read()
            assert "Update Security Status" in content


class TestModuleFunctions:
    """Test module-level functions."""

    def test_get_default_pages_generator(self) -> None:
        """Test getting default pages generator."""
        generator = get_default_pages_generator()

        assert isinstance(generator, GitHubPagesGenerator)
        assert generator.pages_dir == Path("security-status")

    @patch("badges.github_pages.GitHubPagesGenerator")
    def test_update_github_pages_status(self, mock_generator_class: Mock) -> None:
        """Test update_github_pages_status function."""
        mock_generator = Mock()
        mock_status = Mock()
        mock_generator.update_all_endpoints.return_value = mock_status
        mock_generator_class.return_value = mock_generator

        pages_dir = Path("/custom/pages")
        status_manager = Mock()

        result = update_github_pages_status(pages_dir, status_manager)

        mock_generator_class.assert_called_once_with(pages_dir, status_manager)
        mock_generator.update_all_endpoints.assert_called_once()
        assert result == mock_status
