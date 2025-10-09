"""
Visualization Data Generator - Story 11.3, Task 9

Generates chart-ready data for frontend visualization:
- Equity curve comparisons
- Rolling Sharpe ratio charts
- Parameter evolution charts
- Overfitting score trends
"""

from typing import List, Dict, Any
import numpy as np
from datetime import datetime
import logging

from .models import WalkForwardResult, WindowResult, EquityPoint

logger = logging.getLogger(__name__)


class VisualizationDataGenerator:
    """
    Generates data formatted for frontend charting libraries

    Outputs are compatible with Chart.js, Recharts, and other common charting libraries.
    """

    def __init__(self):
        """Initialize visualization data generator"""
        pass

    def generate_equity_curve_comparison(
        self,
        result: WalkForwardResult
    ) -> Dict[str, Any]:
        """
        Generate equity curve comparison data (optimized vs baseline)

        Format compatible with Chart.js line charts.

        Args:
            result: Walk-forward optimization result

        Returns:
            Dict with chart data
        """

        # Extract equity points
        optimized_points = result.equity_curve_optimized
        baseline_points = result.equity_curve_baseline

        # Format for charting
        chart_data = {
            'labels': [
                point.timestamp.isoformat()
                for point in optimized_points
            ],
            'datasets': [
                {
                    'label': 'Optimized Parameters',
                    'data': [
                        point.equity
                        for point in optimized_points
                    ],
                    'borderColor': 'rgb(75, 192, 192)',
                    'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                    'fill': False
                },
                {
                    'label': 'Baseline Parameters',
                    'data': [
                        point.equity
                        for point in baseline_points
                    ],
                    'borderColor': 'rgb(255, 99, 132)',
                    'backgroundColor': 'rgba(255, 99, 132, 0.2)',
                    'fill': False
                }
            ]
        }

        logger.debug(
            f"Generated equity curve comparison with "
            f"{len(optimized_points)} points"
        )

        return chart_data

    def generate_rolling_sharpe_chart(
        self,
        windows: List[WindowResult]
    ) -> Dict[str, Any]:
        """
        Generate rolling Sharpe ratio chart data

        Shows in-sample vs out-of-sample Sharpe ratios across windows.

        Args:
            windows: List of window results

        Returns:
            Dict with chart data
        """

        chart_data = {
            'labels': [
                f"Window {w.window_index + 1}"
                for w in windows
            ],
            'datasets': [
                {
                    'label': 'In-Sample Sharpe',
                    'data': [w.in_sample_sharpe for w in windows],
                    'borderColor': 'rgb(54, 162, 235)',
                    'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                    'fill': False
                },
                {
                    'label': 'Out-of-Sample Sharpe',
                    'data': [w.out_of_sample_sharpe for w in windows],
                    'borderColor': 'rgb(255, 206, 86)',
                    'backgroundColor': 'rgba(255, 206, 86, 0.2)',
                    'fill': False
                }
            ]
        }

        logger.debug(f"Generated rolling Sharpe chart for {len(windows)} windows")

        return chart_data

    def generate_parameter_evolution_chart(
        self,
        parameter_evolution: Dict[str, List[float]],
        param_name: str
    ) -> Dict[str, Any]:
        """
        Generate parameter evolution chart for a specific parameter

        Args:
            parameter_evolution: Dict mapping parameter name to values
            param_name: Parameter to chart

        Returns:
            Dict with chart data
        """

        if param_name not in parameter_evolution:
            raise ValueError(f"Parameter '{param_name}' not found in evolution data")

        values = parameter_evolution[param_name]

        chart_data = {
            'labels': [f"Window {i + 1}" for i in range(len(values))],
            'datasets': [
                {
                    'label': param_name,
                    'data': values,
                    'borderColor': 'rgb(153, 102, 255)',
                    'backgroundColor': 'rgba(153, 102, 255, 0.2)',
                    'fill': False
                }
            ]
        }

        logger.debug(
            f"Generated parameter evolution chart for '{param_name}' "
            f"({len(values)} windows)"
        )

        return chart_data

    def generate_all_parameter_evolution_charts(
        self,
        parameter_evolution: Dict[str, List[float]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate evolution charts for all parameters

        Args:
            parameter_evolution: Dict mapping parameter name to values

        Returns:
            Dict mapping parameter name to chart data
        """

        charts = {}

        for param_name in parameter_evolution.keys():
            charts[param_name] = self.generate_parameter_evolution_chart(
                parameter_evolution, param_name
            )

        logger.debug(f"Generated evolution charts for {len(charts)} parameters")

        return charts

    def generate_overfitting_score_trend(
        self,
        windows: List[WindowResult]
    ) -> Dict[str, Any]:
        """
        Generate overfitting score trend chart

        Args:
            windows: List of window results

        Returns:
            Dict with chart data
        """

        chart_data = {
            'labels': [f"Window {w.window_index + 1}" for w in windows],
            'datasets': [
                {
                    'label': 'Overfitting Score',
                    'data': [w.overfitting_score for w in windows],
                    'borderColor': 'rgb(255, 99, 132)',
                    'backgroundColor': 'rgba(255, 99, 132, 0.2)',
                    'fill': False
                },
                {
                    'label': 'Warning Threshold (0.3)',
                    'data': [0.3] * len(windows),
                    'borderColor': 'rgb(255, 206, 86)',
                    'borderDash': [5, 5],
                    'fill': False,
                    'pointRadius': 0
                },
                {
                    'label': 'Critical Threshold (0.5)',
                    'data': [0.5] * len(windows),
                    'borderColor': 'rgb(255, 0, 0)',
                    'borderDash': [5, 5],
                    'fill': False,
                    'pointRadius': 0
                }
            ]
        }

        logger.debug(f"Generated overfitting trend chart for {len(windows)} windows")

        return chart_data

    def generate_performance_metrics_comparison(
        self,
        windows: List[WindowResult]
    ) -> Dict[str, Any]:
        """
        Generate performance metrics comparison (IS vs OOS)

        Shows multiple metrics: Sharpe, Drawdown, Win Rate

        Args:
            windows: List of window results

        Returns:
            Dict with multiple chart datasets
        """

        labels = [f"Window {w.window_index + 1}" for w in windows]

        charts = {
            'sharpe_ratio': {
                'labels': labels,
                'datasets': [
                    {
                        'label': 'In-Sample',
                        'data': [w.in_sample_sharpe for w in windows]
                    },
                    {
                        'label': 'Out-of-Sample',
                        'data': [w.out_of_sample_sharpe for w in windows]
                    }
                ]
            },
            'max_drawdown': {
                'labels': labels,
                'datasets': [
                    {
                        'label': 'In-Sample',
                        'data': [abs(w.in_sample_drawdown) for w in windows]
                    },
                    {
                        'label': 'Out-of-Sample',
                        'data': [abs(w.out_of_sample_drawdown) for w in windows]
                    }
                ]
            },
            'win_rate': {
                'labels': labels,
                'datasets': [
                    {
                        'label': 'In-Sample',
                        'data': [w.in_sample_win_rate * 100 for w in windows]
                    },
                    {
                        'label': 'Out-of-Sample',
                        'data': [w.out_of_sample_win_rate * 100 for w in windows]
                    }
                ]
            },
            'total_return': {
                'labels': labels,
                'datasets': [
                    {
                        'label': 'In-Sample',
                        'data': [w.in_sample_total_return for w in windows]
                    },
                    {
                        'label': 'Out-of-Sample',
                        'data': [w.out_of_sample_total_return for w in windows]
                    }
                ]
            }
        }

        logger.debug(f"Generated performance comparison charts for {len(windows)} windows")

        return charts

    def generate_heatmap_data(
        self,
        windows: List[WindowResult],
        metric: str = 'overfitting_score'
    ) -> Dict[str, Any]:
        """
        Generate heatmap data for window analysis

        Args:
            windows: List of window results
            metric: Metric to visualize ('overfitting_score', 'out_of_sample_sharpe', etc.)

        Returns:
            Dict with heatmap data
        """

        # Extract metric values
        if metric == 'overfitting_score':
            values = [w.overfitting_score for w in windows]
        elif metric == 'out_of_sample_sharpe':
            values = [w.out_of_sample_sharpe for w in windows]
        elif metric == 'out_of_sample_drawdown':
            values = [abs(w.out_of_sample_drawdown) for w in windows]
        else:
            raise ValueError(f"Unknown metric: {metric}")

        # Format for heatmap
        heatmap_data = {
            'data': [
                {
                    'window': w.window_index + 1,
                    'value': values[w.window_index],
                    'date_range': f"{w.test_start.date()} to {w.test_end.date()}"
                }
                for w in windows
            ],
            'metric': metric,
            'min_value': min(values),
            'max_value': max(values),
            'avg_value': sum(values) / len(values)
        }

        logger.debug(f"Generated heatmap for metric '{metric}'")

        return heatmap_data

    def generate_all_visualization_data(
        self,
        result: WalkForwardResult
    ) -> Dict[str, Any]:
        """
        Generate all visualization data at once

        Args:
            result: Walk-forward optimization result

        Returns:
            Dict with all chart data
        """

        viz_data = {
            'equity_curve_comparison': self.generate_equity_curve_comparison(result),
            'rolling_sharpe': self.generate_rolling_sharpe_chart(result.windows),
            'overfitting_trend': self.generate_overfitting_score_trend(result.windows),
            'parameter_evolution': self.generate_all_parameter_evolution_charts(
                result.parameter_evolution
            ),
            'performance_comparison': self.generate_performance_metrics_comparison(
                result.windows
            ),
            'heatmaps': {
                'overfitting_score': self.generate_heatmap_data(
                    result.windows, 'overfitting_score'
                ),
                'oos_sharpe': self.generate_heatmap_data(
                    result.windows, 'out_of_sample_sharpe'
                ),
                'oos_drawdown': self.generate_heatmap_data(
                    result.windows, 'out_of_sample_drawdown'
                )
            }
        }

        logger.info("Generated all visualization data")

        return viz_data
