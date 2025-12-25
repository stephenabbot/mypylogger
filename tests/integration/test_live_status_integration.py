"""Integration tests for live security status system.

This module provides comprehensive integration tests that verify the complete
live security status workflow from data generation to API endpoints.
"""

from datetime import date, datetime, timezone
import json
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch

import pytest

from badges.dynamic_badges import DynamicBadgeGenerator, ReadmeBadgeUpdater
from badges.github_pages import GitHubPagesGenerator
from badges.live_status import SecurityStatus, SecurityStatusManager, VulnerabilitySummary
from badges.monitoring import PerformanceMetrics, SecurityStatusMonitor
from security.models import SecurityFinding


class TestLiveStatusIntegration:
    """Integration tests for complete live status workflow."""

    def test_complete_status_workflow(self) -> None:
        """Test complete workflow from findings to live status."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            reports_dir = temp_path / "reports"
            status_file = temp_path / "status.json"

            # Create mock security findings
            test_findings = [
                SecurityFinding(
                    finding_id="CVE-2023-0001",
                    package="test-pkg",
                    version="1.0.0",
                    severity="high",
                    source_scanner="pip-audit",
                    discovered_date=date.today(),
                    description="High severity vulnerability",
                    impact="Security risk",
                    fix_available=True,
                    fix_version="1.0.1",
                ),
                SecurityFinding(
                    finding_id="CVE-2023-0002",
                    package="test-pkg",
                    version="1.0.0",
                    severity="medium",
                    source_scanner="pip-audit",
                    discovered_date=date.today(),
                    description="Medium severity vulnerability",
                    impact="Moderate risk",
                    fix_available=False,
                ),
            ]

            # Create status manager and mock the findings extraction
            status_manager = SecurityStatusManager(reports_dir, status_file)

            # Mock the findings extraction at the manager level
            with patch.object(status_manager, "_get_current_findings") as mock_get_findings:
                mock_get_findings.return_value = test_findings
                status = status_manager.update_status()

                # Verify status was created correctly
                assert status.vulnerability_summary.total == 2
                assert status.vulnerability_summary.high == 1
                assert status.vulnerability_summary.medium == 1
                assert status.security_grade == "C"  # High vulnerability = C grade
                assert len(status.findings) == 2

                # Verify status file was created
                assert status_file.exists()

                # Verify status can be loaded back
                loaded_status = status_manager.get_current_status()
                assert loaded_status is not None
                assert loaded_status.vulnerability_summary.total == 2

    def test_github_pages_integration(self) -> None:
        """Test GitHub Pages generation integration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            pages_dir = temp_path / "pages"

            # Create mock status manager
            mock_status_manager = Mock()
            mock_status = self._create_test_status()
            mock_status_manager.update_status.return_value = mock_status
            mock_status_manager.get_current_status.return_value = mock_status

            # Create pages generator
            pages_generator = GitHubPagesGenerator(pages_dir, mock_status_manager)

            # Generate all endpoints
            updated_status = pages_generator.update_all_endpoints()

            # Verify files were created
            assert (pages_dir / "index.json").exists()
            assert (pages_dir / "index.html").exists()
            assert (pages_dir / "status.jsonp").exists()

            # Verify JSON content
            with (pages_dir / "index.json").open("r") as f:
                json_data = json.load(f)
            assert json_data["security_grade"] == "A"
            assert json_data["vulnerability_summary"]["total"] == 0

            # Verify HTML content
            with (pages_dir / "index.html").open("r") as f:
                html_content = f.read()
            assert "Security Status" in html_content
            assert "Grade A" in html_content or "security-grade" in html_content

            # Verify JSONP content
            with (pages_dir / "status.jsonp").open("r") as f:
                jsonp_content = f.read()
            assert "securityStatusCallback(" in jsonp_content

            # Verify returned status
            assert updated_status == mock_status

    def test_dynamic_badge_integration(self) -> None:
        """Test dynamic badge generation integration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            readme_path = temp_path / "README.md"

            # Create test README content
            readme_content = """# Test Project

![Security Status](https://img.shields.io/badge/security-old-red)
![Vulnerabilities](https://img.shields.io/badge/vulnerabilities-old-red)
![Last Scan](https://img.shields.io/badge/last%20scan-old-red)

Some content here.
"""
            with readme_path.open("w") as f:
                f.write(readme_content)

            # Create mock status manager
            mock_status_manager = Mock()
            mock_status = self._create_test_status_with_vulnerabilities()
            mock_status_manager.get_current_status.return_value = mock_status

            # Create badge generator and updater
            badge_generator = DynamicBadgeGenerator(
                mock_status_manager, "https://test.github.io/repo"
            )
            readme_updater = ReadmeBadgeUpdater(readme_path, badge_generator)

            # Update badges
            result = readme_updater.update_security_badges()

            # Verify update was successful
            assert result["success"] is True
            assert "security_status" in result["badges_updated"]

            # Verify README was updated
            with readme_path.open("r") as f:
                updated_content = f.read()

            # Should contain new badge URLs (not the old ones)
            assert "old-red" not in updated_content
            assert "img.shields.io" in updated_content

    def test_monitoring_integration(self) -> None:
        """Test monitoring system integration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            metrics_file = temp_path / "metrics.json"

            # Create monitor with custom config
            monitor = SecurityStatusMonitor(
                base_url="https://test.github.io/repo",
                metrics_file=metrics_file,
            )

            # Mock successful API check
            with patch.object(monitor, "check_api_availability") as mock_check:
                mock_metrics = self._create_test_performance_metrics(success=True)
                mock_check.return_value = mock_metrics

                # Run monitoring check
                result = monitor.run_monitoring_check()

                # Verify monitoring results
                assert result["success"] is True
                assert "metrics" in result
                assert "uptime" in result
                assert result["uptime"]["is_healthy"] is True

                # Verify metrics file was created
                assert metrics_file.exists()

                # Verify metrics can be loaded
                with metrics_file.open("r") as f:
                    saved_data = json.load(f)
                assert "uptime_metrics" in saved_data

    def test_end_to_end_workflow(self) -> None:
        """Test complete end-to-end workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            reports_dir = temp_path / "reports"
            status_file = temp_path / "status.json"
            pages_dir = temp_path / "pages"
            readme_path = temp_path / "README.md"

            # Create test README
            readme_content = """# Test Project

<!-- BADGES -->

Some content here.
"""
            with readme_path.open("w") as f:
                f.write(readme_content)

            # Create test findings
            test_findings = [
                SecurityFinding(
                    finding_id="CVE-2023-0001",
                    package="test-pkg",
                    version="1.0.0",
                    severity="critical",
                    source_scanner="pip-audit",
                    discovered_date=date.today(),
                    description="Critical vulnerability",
                    impact="High risk",
                    fix_available=True,
                ),
            ]

            # Step 1: Update security status
            status_manager = SecurityStatusManager(reports_dir, status_file)

            # Mock findings extraction at the manager level
            with patch.object(status_manager, "_get_current_findings") as mock_get_findings:
                mock_get_findings.return_value = test_findings
                status = status_manager.update_status()

                # Verify status
                assert status.vulnerability_summary.total == 1
                assert status.vulnerability_summary.critical == 1
                assert status.security_grade == "F"  # Critical = F grade

                # Step 2: Generate GitHub Pages
                pages_generator = GitHubPagesGenerator(pages_dir, status_manager)
                pages_generator.update_all_endpoints()

                # Verify pages were created
                assert (pages_dir / "index.json").exists()
                assert (pages_dir / "index.html").exists()

                # Step 3: Update README badges
                badge_generator = DynamicBadgeGenerator(
                    status_manager, "https://test.github.io/repo"
                )
                readme_updater = ReadmeBadgeUpdater(readme_path, badge_generator)
                badge_result = readme_updater.update_security_badges()

                # Verify badge update
                assert badge_result["success"] is True

                # Verify README contains badges
                with readme_path.open("r") as f:
                    updated_readme = f.read()
                assert "[![" in updated_readme  # Badge markdown format

                # Step 4: Monitor the system
                monitor = SecurityStatusMonitor(
                    base_url="https://test.github.io/repo",
                    metrics_file=temp_path / "metrics.json",
                )

                # Mock API check for monitoring
                with patch.object(monitor, "check_api_availability") as mock_check:
                    mock_metrics = self._create_test_performance_metrics(success=True)
                    mock_check.return_value = mock_metrics

                    monitoring_result = monitor.run_monitoring_check()

                # Verify monitoring
                assert monitoring_result["success"] is True

    def test_error_handling_integration(self) -> None:
        """Test error handling across the integrated system."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test status manager with missing reports directory
            status_manager = SecurityStatusManager(
                reports_dir=temp_path / "nonexistent", status_file=temp_path / "status.json"
            )

            # Should handle missing reports gracefully
            status = status_manager.update_status()
            assert status.vulnerability_summary.total == 0
            assert status.security_grade == "A"

            # Test pages generator with status manager error
            mock_status_manager = Mock()
            mock_status_manager.update_status.side_effect = RuntimeError("Status error")

            pages_generator = GitHubPagesGenerator(temp_path / "pages", mock_status_manager)

            # Should raise error for pages generation
            with pytest.raises(RuntimeError, match="Failed to generate API endpoint"):
                pages_generator.generate_api_endpoint()

            # Test badge generator with status error
            mock_status_manager.get_current_status.side_effect = RuntimeError("Status error")
            badge_generator = DynamicBadgeGenerator(mock_status_manager)

            # Should return fallback badge
            result = badge_generator.generate_security_status_badge()
            assert result["status"] == "unknown"
            assert "lightgrey" in result["url"]

    def test_performance_requirements(self) -> None:
        """Test that system meets performance requirements."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test data
            test_findings = [
                SecurityFinding(
                    finding_id=f"CVE-2023-{i:04d}",
                    package="test-pkg",
                    version="1.0.0",
                    severity="medium",
                    source_scanner="pip-audit",
                    discovered_date=date.today(),
                    description=f"Vulnerability {i}",
                    impact="Medium risk",
                    fix_available=True,
                )
                for i in range(10)  # 10 findings
            ]

            # Measure status update time
            start_time = datetime.now()
            status_manager = SecurityStatusManager(temp_path / "reports", temp_path / "status.json")

            # Mock findings extraction at the manager level
            with patch.object(status_manager, "_get_current_findings") as mock_get_findings:
                mock_get_findings.return_value = test_findings
                status = status_manager.update_status()
                status_time = (datetime.now() - start_time).total_seconds()

                # Should complete within reasonable time (< 1 second for 10 findings)
                assert status_time < 1.0
                assert status.vulnerability_summary.total == 10

                # Measure pages generation time
                start_time = datetime.now()
                pages_generator = GitHubPagesGenerator(temp_path / "pages", status_manager)
                pages_generator.update_all_endpoints()
                pages_time = (datetime.now() - start_time).total_seconds()

                # Should complete within reasonable time (< 2 seconds)
                assert pages_time < 2.0

                # Verify all files were created
                assert (temp_path / "pages" / "index.json").exists()
                assert (temp_path / "pages" / "index.html").exists()

    def _create_test_status(self) -> SecurityStatus:
        """Create test SecurityStatus with no vulnerabilities."""
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

    def _create_test_status_with_vulnerabilities(self) -> SecurityStatus:
        """Create test SecurityStatus with vulnerabilities."""
        now = datetime.now(timezone.utc)
        summary = VulnerabilitySummary(total=2, high=1, medium=1)

        return SecurityStatus(
            last_updated=now,
            scan_date=now,
            vulnerability_summary=summary,
            security_grade="C",
            days_since_last_vulnerability=5,
            remediation_status="pending",
        )

    def _create_test_performance_metrics(self, success: bool = True) -> PerformanceMetrics:
        """Create test performance metrics."""
        return PerformanceMetrics(
            response_time_ms=150.0 if success else 5000.0,
            status_code=200 if success else 0,
            content_size_bytes=1024 if success else 0,
            timestamp=datetime.now(timezone.utc),
            endpoint_url="https://test.github.io/repo/security-status/index.json",
            success=success,
            error_message=None if success else "Connection failed",
        )


class TestLiveStatusDataConsistency:
    """Test data consistency across the live status system."""

    def test_status_data_consistency(self) -> None:
        """Test that status data remains consistent across operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            status_file = temp_path / "status.json"

            # Create test findings
            test_findings = [
                SecurityFinding(
                    finding_id="CVE-2023-0001",
                    package="test-pkg",
                    version="1.0.0",
                    severity="high",
                    source_scanner="pip-audit",
                    discovered_date=date(2023, 1, 1),
                    description="Test vulnerability",
                    impact="High risk",
                    fix_available=True,
                    fix_version="1.0.1",
                ),
            ]

            # Create and update status
            status_manager = SecurityStatusManager(status_file=status_file)

            # Mock findings extraction at the manager level
            with patch.object(status_manager, "_get_current_findings") as mock_get_findings:
                mock_get_findings.return_value = test_findings
                original_status = status_manager.update_status()

                # Load status back
                loaded_status = status_manager.get_current_status()

                # Verify consistency
                assert loaded_status is not None
                assert loaded_status.security_grade == original_status.security_grade
                assert (
                    loaded_status.vulnerability_summary.total
                    == original_status.vulnerability_summary.total
                )
                assert (
                    loaded_status.vulnerability_summary.high
                    == original_status.vulnerability_summary.high
                )
                assert len(loaded_status.findings) == len(original_status.findings)

                # Verify finding details
                original_finding = original_status.findings[0]
                loaded_finding = loaded_status.findings[0]
                assert original_finding.finding_id == loaded_finding.finding_id
                assert original_finding.severity == loaded_finding.severity
                assert original_finding.package == loaded_finding.package

    def test_badge_data_consistency(self) -> None:
        """Test that badge data reflects current status consistently."""
        # Create mock status manager
        mock_status_manager = Mock()
        test_status = SecurityStatus(
            last_updated=datetime.now(timezone.utc),
            scan_date=datetime.now(timezone.utc),
            vulnerability_summary=VulnerabilitySummary(total=3, critical=1, high=1, medium=1),
            security_grade="D",
            days_since_last_vulnerability=10,
            remediation_status="pending",
        )
        mock_status_manager.get_current_status.return_value = test_status

        # Create badge generator
        badge_generator = DynamicBadgeGenerator(mock_status_manager, "https://test.github.io/repo")

        # Generate all badge types
        security_badge = badge_generator.generate_security_status_badge()
        vulnerability_badge = badge_generator.generate_vulnerability_count_badge()
        scan_badge = badge_generator.generate_last_scan_badge()

        # Verify consistency across badges
        assert security_badge["status"] == "failing"  # Grade D = failing
        assert vulnerability_badge["status"] == "critical"  # Critical vulns = critical
        assert "Grade D" in security_badge["alt_text"]
        assert (
            "3 vulnerabilities" in vulnerability_badge["alt_text"]
            or "2 critical/high" in vulnerability_badge["alt_text"]
        )

        # All badges should link to the same status page
        assert security_badge["link"] == vulnerability_badge["link"] == scan_badge["link"]

    def test_monitoring_data_consistency(self) -> None:
        """Test that monitoring data remains consistent."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            metrics_file = temp_path / "metrics.json"

            # Create monitor
            monitor = SecurityStatusMonitor(metrics_file=metrics_file)

            # Simulate multiple checks by directly calling the methods
            # First successful check
            metrics1 = self._create_test_performance_metrics(True, 100.0)
            monitor.performance_history.append(metrics1)
            monitor.uptime_metrics.record_success(100.0)

            # Second successful check
            metrics2 = self._create_test_performance_metrics(True, 200.0)
            monitor.performance_history.append(metrics2)
            monitor.uptime_metrics.record_success(200.0)

            # Third failed check
            metrics3 = self._create_test_performance_metrics(False, 0.0)
            monitor.performance_history.append(metrics3)
            monitor.uptime_metrics.record_failure()

            # Save metrics
            monitor._save_metrics()

            # Verify uptime metrics consistency
            assert monitor.uptime_metrics.total_checks == 3
            assert monitor.uptime_metrics.successful_checks == 2
            assert monitor.uptime_metrics.failed_checks == 1
            assert monitor.uptime_metrics.consecutive_failures == 1

            # Verify metrics file consistency
            assert metrics_file.exists()
            with metrics_file.open("r") as f:
                saved_data = json.load(f)
            assert saved_data["uptime_metrics"]["total_checks"] == 3

    def _create_test_performance_metrics(
        self, success: bool, response_time: float
    ) -> PerformanceMetrics:
        """Create test performance metrics."""
        return PerformanceMetrics(
            response_time_ms=response_time,
            status_code=200 if success else 0,
            content_size_bytes=1024 if success else 0,
            timestamp=datetime.now(timezone.utc),
            endpoint_url="https://test.github.io/repo/security-status/index.json",
            success=success,
            error_message=None if success else "Connection failed",
        )
