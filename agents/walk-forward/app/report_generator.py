"""
Walk-Forward Report Generator - Story 11.3, Task 6

Generates comprehensive reports in multiple formats:
- JSON export for API consumption
- CSV export for spreadsheet analysis
- Summary statistics and insights
"""

import json
import csv
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from pathlib import Path

from .models import WalkForwardResult, WindowResult, EquityPoint

logger = logging.getLogger(__name__)


class WalkForwardReportGenerator:
    """
    Generates comprehensive walk-forward optimization reports

    Supports multiple output formats:
    - JSON: Full structured data for API/programmatic access
    - CSV: Tabular data for spreadsheet analysis
    - Summary: Human-readable text summary
    """

    def __init__(self):
        """Initialize report generator"""
        pass

    def generate_json_report(
        self,
        result: WalkForwardResult,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate JSON report

        Args:
            result: Walk-forward optimization result
            output_path: Optional file path to save JSON (if None, returns string only)

        Returns:
            JSON string
        """

        # Convert result to dict (Pydantic model)
        report_dict = result.model_dump(mode='json')

        # Convert to JSON
        json_str = json.dumps(report_dict, indent=2, default=str)

        # Save to file if path provided
        if output_path:
            Path(output_path).write_text(json_str)
            logger.info(f"JSON report saved to: {output_path}")

        return json_str

    def generate_csv_report(
        self,
        result: WalkForwardResult,
        output_dir: str
    ) -> Dict[str, str]:
        """
        Generate CSV reports (multiple files)

        Creates several CSV files:
        - windows.csv: Per-window results
        - parameter_evolution.csv: Parameter values across windows
        - equity_curves.csv: Equity curve data
        - summary.csv: Aggregate statistics

        Args:
            result: Walk-forward optimization result
            output_dir: Directory to save CSV files

        Returns:
            Dict mapping filename to file path
        """

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        files_created = {}

        # 1. Windows CSV
        windows_path = output_path / "windows.csv"
        self._generate_windows_csv(result.windows, windows_path)
        files_created['windows'] = str(windows_path)

        # 2. Parameter Evolution CSV
        param_evo_path = output_path / "parameter_evolution.csv"
        self._generate_parameter_evolution_csv(result.parameter_evolution, param_evo_path)
        files_created['parameter_evolution'] = str(param_evo_path)

        # 3. Summary CSV
        summary_path = output_path / "summary.csv"
        self._generate_summary_csv(result, summary_path)
        files_created['summary'] = str(summary_path)

        logger.info(f"CSV reports saved to: {output_dir}")

        return files_created

    def _generate_windows_csv(
        self,
        windows: List[WindowResult],
        output_path: Path
    ) -> None:
        """Generate per-window results CSV"""

        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'window_index',
                'train_start', 'train_end', 'test_start', 'test_end',
                'in_sample_sharpe', 'in_sample_drawdown', 'in_sample_win_rate',
                'in_sample_total_return', 'in_sample_trades',
                'out_of_sample_sharpe', 'out_of_sample_drawdown', 'out_of_sample_win_rate',
                'out_of_sample_total_return', 'out_of_sample_trades',
                'overfitting_score', 'performance_degradation',
                'combinations_tested', 'optimization_time_seconds'
            ])

            # Data rows
            for window in windows:
                writer.writerow([
                    window.window_index,
                    window.train_start.isoformat(),
                    window.train_end.isoformat(),
                    window.test_start.isoformat(),
                    window.test_end.isoformat(),
                    window.in_sample_sharpe,
                    window.in_sample_drawdown,
                    window.in_sample_win_rate,
                    window.in_sample_total_return,
                    window.in_sample_total_trades,
                    window.out_of_sample_sharpe,
                    window.out_of_sample_drawdown,
                    window.out_of_sample_win_rate,
                    window.out_of_sample_total_return,
                    window.out_of_sample_total_trades,
                    window.overfitting_score,
                    window.performance_degradation,
                    window.total_param_combinations_tested,
                    window.optimization_time_seconds
                ])

    def _generate_parameter_evolution_csv(
        self,
        parameter_evolution: Dict[str, List[float]],
        output_path: Path
    ) -> None:
        """Generate parameter evolution CSV"""

        if not parameter_evolution:
            return

        # Convert to DataFrame for easier CSV generation
        df = pd.DataFrame(parameter_evolution)
        df.index.name = 'window_index'

        df.to_csv(output_path)

    def _generate_summary_csv(
        self,
        result: WalkForwardResult,
        output_path: Path
    ) -> None:
        """Generate summary statistics CSV"""

        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow(['metric', 'value'])

            # Summary metrics
            writer.writerow(['job_id', result.job_id])
            writer.writerow(['acceptance_status', result.acceptance_status])
            writer.writerow(['total_windows', result.total_windows])
            writer.writerow(['total_backtests', result.total_backtests_run])
            writer.writerow(['execution_time_seconds', result.execution_time_seconds])
            writer.writerow(['avg_in_sample_sharpe', result.avg_in_sample_sharpe])
            writer.writerow(['avg_out_of_sample_sharpe', result.avg_out_of_sample_sharpe])
            writer.writerow(['avg_overfitting_score', result.avg_overfitting_score])
            writer.writerow(['parameter_stability_score', result.parameter_stability_score])

            # Recommended parameters
            writer.writerow(['', ''])  # Blank row
            writer.writerow(['recommended_parameters', ''])
            for param_name, param_value in result.recommended_parameters.items():
                writer.writerow([param_name, param_value])

            # Baseline deviations
            writer.writerow(['', ''])  # Blank row
            writer.writerow(['baseline_deviations_pct', ''])
            for param_name, deviation in result.parameter_deviation_from_baseline.items():
                writer.writerow([param_name, f"{deviation:+.1f}%"])

    def generate_text_summary(
        self,
        result: WalkForwardResult
    ) -> str:
        """
        Generate human-readable text summary

        Args:
            result: Walk-forward optimization result

        Returns:
            Multi-line text summary
        """

        lines = []

        lines.append("=" * 80)
        lines.append("WALK-FORWARD OPTIMIZATION REPORT")
        lines.append("=" * 80)
        lines.append(f"Job ID: {result.job_id}")
        lines.append(f"Status: {result.acceptance_status}")
        lines.append(f"Completed: {result.completed_at.isoformat()}")
        lines.append("")

        # Configuration summary
        lines.append("CONFIGURATION")
        lines.append("-" * 80)
        lines.append(f"Date range: {result.config.start_date.date()} to {result.config.end_date.date()}")
        lines.append(f"Window type: {result.config.window_type.value}")
        lines.append(f"Training window: {result.config.training_window_days} days")
        lines.append(f"Testing window: {result.config.testing_window_days} days")
        lines.append(f"Step size: {result.config.step_size_days} days")
        lines.append(f"Instruments: {', '.join(result.config.instruments)}")
        lines.append(f"Optimization method: {result.config.optimization_method.value}")
        lines.append("")

        # Performance summary
        lines.append("PERFORMANCE SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Total windows: {result.total_windows}")
        lines.append(f"Total backtests: {result.total_backtests_run}")
        lines.append(f"Execution time: {result.execution_time_seconds:.1f}s ({result.execution_time_seconds/60:.1f} min)")
        lines.append("")
        lines.append(f"Avg in-sample Sharpe: {result.avg_in_sample_sharpe:.2f}")
        lines.append(f"Avg out-of-sample Sharpe: {result.avg_out_of_sample_sharpe:.2f}")
        lines.append(f"Avg overfitting score: {result.avg_overfitting_score:.3f}")
        lines.append(f"Parameter stability score: {result.parameter_stability_score:.3f}")
        lines.append("")

        # Recommended parameters
        lines.append("RECOMMENDED PARAMETERS")
        lines.append("-" * 80)
        for param_name, param_value in result.recommended_parameters.items():
            baseline_val = result.config.baseline_parameters.get(param_name, 0)
            deviation = result.parameter_deviation_from_baseline.get(param_name, 0)

            lines.append(
                f"{param_name:30s}: {param_value:8.2f}  "
                f"(baseline: {baseline_val:.2f}, deviation: {deviation:+.1f}%)"
            )
        lines.append("")

        # Acceptance criteria
        lines.append("ACCEPTANCE CRITERIA")
        lines.append("-" * 80)
        for message in result.acceptance_messages:
            lines.append(message)
        lines.append("")

        # Best and worst windows
        lines.append("WINDOW ANALYSIS")
        lines.append("-" * 80)

        best_window = max(result.windows, key=lambda w: w.out_of_sample_sharpe)
        worst_window = min(result.windows, key=lambda w: w.out_of_sample_sharpe)

        lines.append(f"Best window (#{best_window.window_index}):")
        lines.append(f"  - Period: {best_window.test_start.date()} to {best_window.test_end.date()}")
        lines.append(f"  - OOS Sharpe: {best_window.out_of_sample_sharpe:.2f}")
        lines.append(f"  - OOS Return: {best_window.out_of_sample_total_return:.2f}%")
        lines.append(f"  - Overfitting: {best_window.overfitting_score:.3f}")
        lines.append("")

        lines.append(f"Worst window (#{worst_window.window_index}):")
        lines.append(f"  - Period: {worst_window.test_start.date()} to {worst_window.test_end.date()}")
        lines.append(f"  - OOS Sharpe: {worst_window.out_of_sample_sharpe:.2f}")
        lines.append(f"  - OOS Return: {worst_window.out_of_sample_total_return:.2f}%")
        lines.append(f"  - Overfitting: {worst_window.overfitting_score:.3f}")
        lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)

    def generate_all_reports(
        self,
        result: WalkForwardResult,
        output_dir: str
    ) -> Dict[str, Any]:
        """
        Generate all report formats

        Args:
            result: Walk-forward optimization result
            output_dir: Directory to save reports

        Returns:
            Dict with paths to all generated files
        """

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        files_created = {}

        # JSON report
        json_path = output_path / f"walk_forward_report_{result.job_id}.json"
        self.generate_json_report(result, str(json_path))
        files_created['json'] = str(json_path)

        # CSV reports
        csv_files = self.generate_csv_report(result, str(output_path))
        files_created.update(csv_files)

        # Text summary
        summary_text = self.generate_text_summary(result)
        summary_path = output_path / f"summary_{result.job_id}.txt"
        summary_path.write_text(summary_text)
        files_created['summary'] = str(summary_path)

        logger.info(f"All reports generated in: {output_dir}")

        return files_created
