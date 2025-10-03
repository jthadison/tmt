#!/usr/bin/env python3
"""
Performance Regression Checker
Analyzes pytest-benchmark results to detect performance regressions
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional


class PerformanceChecker:
    """Check for performance regressions in benchmark results"""

    def __init__(self, threshold_percent: float = 20.0):
        """
        Initialize checker

        Args:
            threshold_percent: Maximum allowed performance degradation (%)
        """
        self.threshold = threshold_percent / 100.0
        self.baseline_file = Path("benchmark_baseline.json")

    def load_benchmark(self, file_path: Path) -> Dict:
        """Load benchmark JSON file"""
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️  Benchmark file not found: {file_path}")
            return {}
        except json.JSONDecodeError as e:
            print(f"✗ Invalid JSON in {file_path}: {e}")
            sys.exit(1)

    def save_baseline(self, benchmark: Dict) -> None:
        """Save current benchmark as baseline"""
        with open(self.baseline_file, "w") as f:
            json.dump(benchmark, f, indent=2)
        print(f"✓ Saved baseline to {self.baseline_file}")

    def compare_benchmarks(
        self, current: Dict, baseline: Dict
    ) -> List[Dict]:
        """Compare current benchmark against baseline"""
        regressions = []

        if not baseline or "benchmarks" not in baseline:
            print("ℹ️  No baseline found, skipping regression check")
            return []

        current_benchmarks = {
            b["fullname"]: b for b in current.get("benchmarks", [])
        }
        baseline_benchmarks = {
            b["fullname"]: b for b in baseline.get("benchmarks", [])
        }

        for name, current_bench in current_benchmarks.items():
            if name not in baseline_benchmarks:
                print(f"ℹ️  New benchmark: {name}")
                continue

            baseline_bench = baseline_benchmarks[name]

            # Compare mean execution time
            current_mean = current_bench["stats"]["mean"]
            baseline_mean = baseline_bench["stats"]["mean"]

            if baseline_mean == 0:
                continue

            # Calculate regression percentage
            regression = (current_mean - baseline_mean) / baseline_mean

            if regression > self.threshold:
                regressions.append({
                    "name": name,
                    "current_mean": current_mean,
                    "baseline_mean": baseline_mean,
                    "regression_pct": regression * 100,
                    "threshold_pct": self.threshold * 100,
                })

        return regressions

    def print_report(self, regressions: List[Dict]) -> None:
        """Print regression report"""
        print("\n" + "=" * 70)
        print("Performance Regression Report")
        print("=" * 70)

        if not regressions:
            print("\n✅ No performance regressions detected!")
            print(f"   All benchmarks within {self.threshold * 100}% threshold")
            return

        print(f"\n❌ Found {len(regressions)} performance regression(s):\n")

        for reg in regressions:
            print(f"  Test: {reg['name']}")
            print(f"    Baseline: {reg['baseline_mean']:.6f}s")
            print(f"    Current:  {reg['current_mean']:.6f}s")
            print(f"    Regression: {reg['regression_pct']:.1f}% "
                  f"(threshold: {reg['threshold_pct']:.1f}%)")
            print()

    def check(self, benchmark_file: Path, save_as_baseline: bool = False) -> bool:
        """
        Run performance regression check

        Args:
            benchmark_file: Path to current benchmark results
            save_as_baseline: Save current results as new baseline

        Returns:
            True if no regressions, False otherwise
        """
        print("=" * 70)
        print("TMT Performance Regression Checker")
        print("=" * 70)
        print()

        # Load current benchmark
        current = self.load_benchmark(benchmark_file)

        if not current:
            print("✗ No benchmark data to analyze")
            return False

        # Load baseline if it exists
        baseline = self.load_benchmark(self.baseline_file)

        # Compare
        regressions = self.compare_benchmarks(current, baseline)

        # Print report
        self.print_report(regressions)

        # Save baseline if requested
        if save_as_baseline:
            print()
            self.save_baseline(current)

        print("\n" + "=" * 70)

        return len(regressions) == 0


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Check for performance regressions in benchmark results"
    )
    parser.add_argument(
        "benchmark_file",
        type=Path,
        help="Path to benchmark JSON file",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=20.0,
        help="Regression threshold percentage (default: 20%%)",
    )
    parser.add_argument(
        "--save-baseline",
        action="store_true",
        help="Save current results as new baseline",
    )
    parser.add_argument(
        "--baseline-file",
        type=Path,
        default=None,
        help="Path to baseline file (default: benchmark_baseline.json)",
    )

    args = parser.parse_args()

    checker = PerformanceChecker(threshold_percent=args.threshold)

    if args.baseline_file:
        checker.baseline_file = args.baseline_file

    # Run check
    success = checker.check(args.benchmark_file, save_as_baseline=args.save_baseline)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
