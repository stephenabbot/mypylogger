#!/usr/bin/env python3
"""Performance threshold validation script for mypylogger v0.2.8.

This script validates performance benchmark results against defined thresholds
and fails CI/CD builds if performance requirements are not met.

Requirements addressed:
- 9.2: Measure logger initialization time and fail if it exceeds 10ms
- 9.3: Measure single log entry time and fail if it exceeds 1ms with immediate flush
- 9.5: Detect performance regressions and fail builds if performance degrades by more than 20%
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, ClassVar


class PerformanceThresholds:
    """Performance threshold definitions."""

    # Primary thresholds (hard limits)
    LOGGER_INIT_THRESHOLD_MS = 10.0  # 10ms maximum
    LOG_ENTRY_THRESHOLD_MS = 1.0  # 1ms maximum

    # Regression detection threshold
    REGRESSION_THRESHOLD_PERCENT = 20.0  # 20% degradation triggers failure
    WARNING_THRESHOLD = 5.0  # Warning threshold for minor degradation

    # Performance categories for analysis
    INIT_BENCHMARKS: ClassVar[list[str]] = [
        "test_logger_initialization_performance",
        "test_logger_initialization_with_file_config_performance",
    ]

    LOGGING_BENCHMARKS: ClassVar[list[str]] = [
        "test_single_log_entry_performance",
        "test_log_entry_with_extra_fields_performance",
        "test_file_logging_performance",
    ]


class PerformanceValidator:
    """Validates performance benchmark results against thresholds."""

    def __init__(self, benchmark_file: Path) -> None:
        """Initialize validator with benchmark results file.

        Args:
            benchmark_file: Path to pytest-benchmark JSON results file
        """
        self.benchmark_file = benchmark_file
        self.results: dict[str, Any] = {}
        self.failures: list[str] = []
        self.warnings: list[str] = []

    def load_benchmark_results(self) -> bool:
        """Load benchmark results from JSON file.

        Returns:
            True if results loaded successfully, False otherwise
        """
        try:
            with self.benchmark_file.open() as f:
                self.results = json.load(f)
            return True
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"❌ Error loading benchmark results: {e}")
            return False

    def validate_initialization_performance(self) -> None:
        """Validate logger initialization performance against thresholds."""
        print("🔍 Validating Logger Initialization Performance")
        print("=" * 50)

        init_benchmarks = self._get_benchmarks_by_category(PerformanceThresholds.INIT_BENCHMARKS)

        if not init_benchmarks:
            self.failures.append("No initialization benchmarks found")
            return

        for benchmark_name, stats in init_benchmarks.items():
            mean_time_ms = stats["mean"] * 1000  # Convert to milliseconds

            print(f"📊 {benchmark_name}:")
            print(f"   Mean time: {mean_time_ms:.3f}ms")
            print(f"   Threshold: {PerformanceThresholds.LOGGER_INIT_THRESHOLD_MS}ms")

            if mean_time_ms > PerformanceThresholds.LOGGER_INIT_THRESHOLD_MS:
                failure_msg = (
                    f"Logger initialization performance failure: "
                    f"{benchmark_name} took {mean_time_ms:.3f}ms, "
                    f"exceeds {PerformanceThresholds.LOGGER_INIT_THRESHOLD_MS}ms threshold"
                )
                self.failures.append(failure_msg)
                print("   ❌ FAILED: Exceeds threshold")
            else:
                print("   ✅ PASSED: Within threshold")

            print()

    def validate_logging_performance(self) -> None:
        """Validate log entry performance against thresholds."""
        print("🔍 Validating Log Entry Performance")
        print("=" * 40)

        logging_benchmarks = self._get_benchmarks_by_category(
            PerformanceThresholds.LOGGING_BENCHMARKS
        )

        if not logging_benchmarks:
            self.failures.append("No logging performance benchmarks found")
            return

        for benchmark_name, stats in logging_benchmarks.items():
            mean_time_ms = stats["mean"] * 1000  # Convert to milliseconds

            print(f"📊 {benchmark_name}:")
            print(f"   Mean time: {mean_time_ms:.3f}ms")
            print(f"   Threshold: {PerformanceThresholds.LOG_ENTRY_THRESHOLD_MS}ms")

            if mean_time_ms > PerformanceThresholds.LOG_ENTRY_THRESHOLD_MS:
                failure_msg = (
                    f"Log entry performance failure: "
                    f"{benchmark_name} took {mean_time_ms:.3f}ms, "
                    f"exceeds {PerformanceThresholds.LOG_ENTRY_THRESHOLD_MS}ms threshold"
                )
                self.failures.append(failure_msg)
                print("   ❌ FAILED: Exceeds threshold")
            else:
                print("   ✅ PASSED: Within threshold")

            print()

    def validate_performance_regression(self, baseline_file: Path | None = None) -> None:
        """Validate performance against baseline for regression detection.

        Args:
            baseline_file: Path to baseline benchmark results (optional)
        """
        print("🔍 Validating Performance Regression")
        print("=" * 38)

        if not baseline_file or not baseline_file.exists():
            print("⚠️ No baseline file provided or found - skipping regression analysis")
            return

        try:
            with baseline_file.open() as f:
                baseline_results = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.warnings.append(f"Could not load baseline results: {e}")
            return

        # Compare current results with baseline
        current_benchmarks = self._get_all_benchmarks()
        baseline_benchmarks = self._extract_benchmarks_from_results(baseline_results)

        for benchmark_name in current_benchmarks:
            if benchmark_name not in baseline_benchmarks:
                continue

            current_mean = current_benchmarks[benchmark_name]["mean"]
            baseline_mean = baseline_benchmarks[benchmark_name]["mean"]

            # Calculate percentage change
            percent_change = ((current_mean - baseline_mean) / baseline_mean) * 100

            print(f"📊 {benchmark_name}:")
            print(f"   Current: {current_mean * 1000:.3f}ms")
            print(f"   Baseline: {baseline_mean * 1000:.3f}ms")
            print(f"   Change: {percent_change:+.1f}%")

            if percent_change > PerformanceThresholds.REGRESSION_THRESHOLD_PERCENT:
                failure_msg = (
                    f"Performance regression detected: "
                    f"{benchmark_name} degraded by {percent_change:.1f}%, "
                    f"exceeds {PerformanceThresholds.REGRESSION_THRESHOLD_PERCENT}% threshold"
                )
                self.failures.append(failure_msg)
                print("   ❌ REGRESSION: Performance degraded significantly")
            elif percent_change > PerformanceThresholds.WARNING_THRESHOLD:  # Warning threshold
                warning_msg = (
                    f"Performance warning: {benchmark_name} degraded by {percent_change:.1f}%"
                )
                self.warnings.append(warning_msg)
                print("   ⚠️ WARNING: Minor performance degradation")
            else:
                print("   ✅ STABLE: Performance within acceptable range")

            print()

    def generate_performance_summary(self) -> dict[str, Any]:
        """Generate performance summary for reporting.

        Returns:
            Dictionary containing performance summary data
        """
        all_benchmarks = self._get_all_benchmarks()

        # Calculate aggregate statistics
        init_times = []
        log_times = []

        for benchmark_name, stats in all_benchmarks.items():
            if any(
                init_name in benchmark_name for init_name in PerformanceThresholds.INIT_BENCHMARKS
            ):
                init_times.append(stats["mean"] * 1000)  # Convert to ms
            elif any(
                log_name in benchmark_name for log_name in PerformanceThresholds.LOGGING_BENCHMARKS
            ):
                log_times.append(stats["mean"] * 1000)  # Convert to ms

        # Calculate averages
        avg_init_time = sum(init_times) / len(init_times) if init_times else 0
        avg_log_time = sum(log_times) / len(log_times) if log_times else 0

        # Determine overall status
        init_status = (
            "pass" if avg_init_time < PerformanceThresholds.LOGGER_INIT_THRESHOLD_MS else "fail"
        )
        log_status = (
            "pass" if avg_log_time < PerformanceThresholds.LOG_ENTRY_THRESHOLD_MS else "fail"
        )
        overall_status = "pass" if init_status == "pass" and log_status == "pass" else "fail"

        return {
            "logger_initialization": {
                "mean_time_ms": round(avg_init_time, 3),
                "threshold_ms": PerformanceThresholds.LOGGER_INIT_THRESHOLD_MS,
                "status": init_status,
            },
            "single_log_entry": {
                "mean_time_ms": round(avg_log_time, 3),
                "threshold_ms": PerformanceThresholds.LOG_ENTRY_THRESHOLD_MS,
                "status": log_status,
            },
            "overall_status": overall_status,
            "total_benchmarks": len(all_benchmarks),
            "failures": len(self.failures),
            "warnings": len(self.warnings),
            "timestamp": self._get_timestamp(),
        }

    def _get_benchmarks_by_category(
        self, category_benchmarks: list[str]
    ) -> dict[str, dict[str, Any]]:
        """Get benchmarks matching a specific category.

        Args:
            category_benchmarks: List of benchmark name patterns to match

        Returns:
            Dictionary of matching benchmarks and their statistics
        """
        all_benchmarks = self._get_all_benchmarks()
        return {
            name: stats
            for name, stats in all_benchmarks.items()
            if any(pattern in name for pattern in category_benchmarks)
        }

    def _get_all_benchmarks(self) -> dict[str, dict[str, Any]]:
        """Extract all benchmark statistics from results.

        Returns:
            Dictionary of benchmark names to their statistics
        """
        return self._extract_benchmarks_from_results(self.results)

    def _extract_benchmarks_from_results(
        self, results: dict[str, Any]
    ) -> dict[str, dict[str, Any]]:
        """Extract benchmark statistics from pytest-benchmark results.

        Args:
            results: Pytest-benchmark results dictionary

        Returns:
            Dictionary of benchmark names to their statistics
        """
        benchmarks = {}

        if "benchmarks" in results:
            for benchmark in results["benchmarks"]:
                name = benchmark.get("name", "")
                stats = benchmark.get("stats", {})
                if name and stats:
                    benchmarks[name] = stats

        return benchmarks

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat() + "Z"

    def print_summary(self) -> None:
        """Print validation summary."""
        print("\n" + "=" * 60)
        print("📊 PERFORMANCE VALIDATION SUMMARY")
        print("=" * 60)

        if not self.failures and not self.warnings:
            print("✅ ALL PERFORMANCE CHECKS PASSED")
            print("   All benchmarks meet performance requirements")
        else:
            if self.failures:
                print(f"❌ PERFORMANCE FAILURES: {len(self.failures)}")
                for failure in self.failures:
                    print(f"   • {failure}")
                print()

            if self.warnings:
                print(f"⚠️ PERFORMANCE WARNINGS: {len(self.warnings)}")
                for warning in self.warnings:
                    print(f"   • {warning}")
                print()

        # Generate and display performance summary
        summary = self.generate_performance_summary()
        print("📈 Performance Metrics:")
        print(
            f"   Logger Initialization: {summary['logger_initialization']['mean_time_ms']:.3f}ms "
            f"(threshold: {summary['logger_initialization']['threshold_ms']}ms)"
        )
        print(
            f"   Log Entry: {summary['single_log_entry']['mean_time_ms']:.3f}ms "
            f"(threshold: {summary['single_log_entry']['threshold_ms']}ms)"
        )
        print(f"   Overall Status: {summary['overall_status'].upper()}")
        print(f"   Total Benchmarks: {summary['total_benchmarks']}")

        print("\n" + "=" * 60)


def main() -> None:
    """Main entry point for performance validation."""
    min_args = 2
    baseline_arg_index = 2

    if len(sys.argv) < min_args:
        print("Usage: python validate_performance.py <benchmark_results.json> [baseline.json]")
        sys.exit(1)

    benchmark_file = Path(sys.argv[1])
    baseline_file = (
        Path(sys.argv[baseline_arg_index]) if len(sys.argv) > baseline_arg_index else None
    )

    if not benchmark_file.exists():
        print(f"❌ Benchmark results file not found: {benchmark_file}")
        sys.exit(1)

    print("🚀 Performance Validation for mypylogger v0.2.8")
    print("=" * 50)
    print(f"Benchmark file: {benchmark_file}")
    if baseline_file:
        print(f"Baseline file: {baseline_file}")
    print()

    validator = PerformanceValidator(benchmark_file)

    if not validator.load_benchmark_results():
        sys.exit(1)

    # Run all validations
    validator.validate_initialization_performance()
    validator.validate_logging_performance()
    validator.validate_performance_regression(baseline_file)

    # Print summary and determine exit code
    validator.print_summary()

    # Save performance summary for reporting
    summary = validator.generate_performance_summary()
    summary_file = benchmark_file.parent / "performance-summary.json"
    with summary_file.open("w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n📄 Performance summary saved to: {summary_file}")

    # Exit with error code if there are failures
    if validator.failures:
        print(f"\n❌ Performance validation failed with {len(validator.failures)} errors")
        sys.exit(1)
    else:
        print("\n✅ Performance validation passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
