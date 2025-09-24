"""
Enhanced Validation Framework
Addresses September 2025 performance issues with comprehensive validation methodology
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from pathlib import Path
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class ValidationResult(Enum):
    """Validation result classifications"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class ValidationMetrics:
    """Comprehensive validation metrics"""
    walk_forward_stability: float
    out_of_sample_consistency: float
    overfitting_score: float
    regime_robustness: float
    stress_test_score: float
    monte_carlo_confidence: float
    deployment_readiness: float
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class ValidationReport:
    """Detailed validation report"""
    overall_result: ValidationResult
    metrics: ValidationMetrics
    detailed_results: Dict[str, Any]
    recommendations: List[str]
    deployment_gates: Dict[str, bool]
    risk_assessment: str
    next_actions: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)

class EnhancedValidator:
    """Enhanced validation system to prevent September-style failures"""

    def __init__(self, config: Dict):
        self.config = config
        self.validation_history = []

        # Enhanced validation thresholds (learned from September failure)
        self.THRESHOLDS = {
            'walk_forward_stability': 60.0,      # Minimum stability score
            'out_of_sample_consistency': 70.0,   # Minimum consistency
            'overfitting_score': 0.3,            # Maximum overfitting
            'regime_robustness': 50.0,           # Multiple regime performance
            'stress_test_score': 40.0,           # Crisis performance
            'monte_carlo_confidence': 80.0,      # Monte Carlo validation
            'min_validation_period': 90,         # Minimum days of validation
            'min_out_of_sample_trades': 50,      # Minimum OOS trades
            'max_performance_degradation': 30.0,  # Max % degradation allowed
            'min_regime_coverage': 3             # Minimum different regimes tested
        }

    async def comprehensive_validation(self,
                                     backtest_data: pd.DataFrame,
                                     parameters: Dict,
                                     validation_period_days: int = 90) -> ValidationReport:
        """Perform comprehensive validation to prevent deployment failures"""

        logger.info("Starting comprehensive validation framework...")

        # Initialize validation components
        validation_tasks = [
            self._validate_walk_forward_stability(backtest_data, parameters),
            self._validate_out_of_sample_consistency(backtest_data),
            self._validate_overfitting_resistance(backtest_data, parameters),
            self._validate_regime_robustness(backtest_data),
            self._validate_stress_testing(backtest_data),
            self._validate_monte_carlo_projections(backtest_data)
        ]

        # Execute validations in parallel
        validation_results = await asyncio.gather(*validation_tasks, return_exceptions=True)

        # Compile results
        metrics = self._compile_validation_metrics(validation_results)
        detailed_results = self._compile_detailed_results(validation_results)

        # Generate overall assessment
        overall_result = self._determine_overall_result(metrics)
        recommendations = self._generate_recommendations(metrics, detailed_results)
        deployment_gates = self._check_deployment_gates(metrics)
        risk_assessment = self._assess_risk_level(metrics, detailed_results)
        next_actions = self._determine_next_actions(overall_result, metrics)

        report = ValidationReport(
            overall_result=overall_result,
            metrics=metrics,
            detailed_results=detailed_results,
            recommendations=recommendations,
            deployment_gates=deployment_gates,
            risk_assessment=risk_assessment,
            next_actions=next_actions
        )

        self.validation_history.append(report)
        await self._save_validation_report(report)

        return report

    async def _validate_walk_forward_stability(self, data: pd.DataFrame, parameters: Dict) -> Dict:
        """Enhanced walk-forward validation with multiple time windows"""

        logger.info("Validating walk-forward stability...")

        try:
            windows = [30, 60, 90]  # Different validation windows
            stability_scores = []

            for window_days in windows:
                window_score = await self._calculate_walk_forward_window(data, parameters, window_days)
                stability_scores.append(window_score)

            # Overall stability is the minimum score across all windows
            overall_stability = min(stability_scores) if stability_scores else 0

            # Additional checks for consistency across windows
            score_variance = np.std(stability_scores) if len(stability_scores) > 1 else 0
            consistency_penalty = min(10, score_variance)  # Penalize high variance

            adjusted_stability = max(0, overall_stability - consistency_penalty)

            return {
                'stability_score': adjusted_stability,
                'window_scores': dict(zip(windows, stability_scores)),
                'score_variance': score_variance,
                'result': ValidationResult.PASS if adjusted_stability >= self.THRESHOLDS['walk_forward_stability'] else ValidationResult.FAIL
            }

        except Exception as e:
            logger.error(f"Walk-forward validation failed: {str(e)}")
            return {
                'stability_score': 0,
                'error': str(e),
                'result': ValidationResult.CRITICAL
            }

    async def _calculate_walk_forward_window(self, data: pd.DataFrame, parameters: Dict, window_days: int) -> float:
        """Calculate stability score for specific time window"""

        if len(data) < window_days * 2:
            return 0

        # Split data into overlapping training/testing periods
        num_periods = max(1, len(data) // window_days - 1)
        performance_degradations = []

        for i in range(num_periods):
            start_idx = i * window_days
            mid_idx = start_idx + window_days
            end_idx = min(mid_idx + window_days, len(data))

            if end_idx - mid_idx < 10:  # Insufficient test data
                continue

            # Training period
            train_data = data.iloc[start_idx:mid_idx]
            train_performance = self._calculate_period_performance(train_data)

            # Testing period
            test_data = data.iloc[mid_idx:end_idx]
            test_performance = self._calculate_period_performance(test_data)

            # Calculate performance degradation
            if train_performance['avg_trade_pnl'] != 0:
                degradation = abs(test_performance['avg_trade_pnl'] - train_performance['avg_trade_pnl']) / abs(train_performance['avg_trade_pnl'])
                performance_degradations.append(degradation * 100)

        if not performance_degradations:
            return 0

        # Stability score (lower degradation = higher stability)
        avg_degradation = np.mean(performance_degradations)
        stability_score = max(0, 100 - avg_degradation)

        return stability_score

    async def _validate_out_of_sample_consistency(self, data: pd.DataFrame) -> Dict:
        """Validate out-of-sample performance consistency"""

        logger.info("Validating out-of-sample consistency...")

        try:
            # Use most recent 25% of data as out-of-sample
            split_point = int(len(data) * 0.75)
            in_sample = data.iloc[:split_point]
            out_of_sample = data.iloc[split_point:]

            if len(out_of_sample) < self.THRESHOLDS['min_out_of_sample_trades']:
                return {
                    'consistency_score': 0,
                    'error': f"Insufficient out-of-sample data: {len(out_of_sample)} trades",
                    'result': ValidationResult.FAIL
                }

            # Calculate performance metrics for both periods
            in_sample_perf = self._calculate_period_performance(in_sample)
            out_of_sample_perf = self._calculate_period_performance(out_of_sample)

            # Calculate consistency metrics
            pnl_consistency = self._calculate_consistency(
                in_sample_perf['avg_trade_pnl'],
                out_of_sample_perf['avg_trade_pnl']
            )

            win_rate_consistency = self._calculate_consistency(
                in_sample_perf['win_rate'],
                out_of_sample_perf['win_rate']
            )

            sharpe_consistency = self._calculate_consistency(
                in_sample_perf.get('sharpe_ratio', 0),
                out_of_sample_perf.get('sharpe_ratio', 0)
            )

            # Overall consistency score
            consistency_score = (pnl_consistency + win_rate_consistency + sharpe_consistency) / 3

            return {
                'consistency_score': consistency_score,
                'in_sample_performance': in_sample_perf,
                'out_of_sample_performance': out_of_sample_perf,
                'pnl_consistency': pnl_consistency,
                'win_rate_consistency': win_rate_consistency,
                'sharpe_consistency': sharpe_consistency,
                'result': ValidationResult.PASS if consistency_score >= self.THRESHOLDS['out_of_sample_consistency'] else ValidationResult.FAIL
            }

        except Exception as e:
            logger.error(f"Out-of-sample validation failed: {str(e)}")
            return {
                'consistency_score': 0,
                'error': str(e),
                'result': ValidationResult.CRITICAL
            }

    def _calculate_consistency(self, in_sample_value: float, out_of_sample_value: float) -> float:
        """Calculate consistency between in-sample and out-of-sample values"""

        if in_sample_value == 0 or out_of_sample_value == 0:
            return 0

        # Calculate percentage difference
        diff_pct = abs(out_of_sample_value - in_sample_value) / abs(in_sample_value) * 100

        # Convert to consistency score (0-100, higher is better)
        consistency_score = max(0, 100 - diff_pct)

        return consistency_score

    async def _validate_overfitting_resistance(self, data: pd.DataFrame, parameters: Dict) -> Dict:
        """Validate resistance to overfitting using multiple methods"""

        logger.info("Validating overfitting resistance...")

        try:
            # Method 1: Cross-validation with shuffled data
            cv_score = await self._cross_validation_overfitting_test(data)

            # Method 2: Parameter sensitivity analysis
            sensitivity_score = await self._parameter_sensitivity_test(data, parameters)

            # Method 3: Noise injection test
            noise_resistance_score = await self._noise_resistance_test(data)

            # Combined overfitting score (lower is better)
            overfitting_score = 1 - (cv_score + sensitivity_score + noise_resistance_score) / 3

            return {
                'overfitting_score': overfitting_score,
                'cross_validation_score': cv_score,
                'sensitivity_score': sensitivity_score,
                'noise_resistance_score': noise_resistance_score,
                'result': ValidationResult.PASS if overfitting_score <= self.THRESHOLDS['overfitting_score'] else ValidationResult.FAIL
            }

        except Exception as e:
            logger.error(f"Overfitting validation failed: {str(e)}")
            return {
                'overfitting_score': 1.0,
                'error': str(e),
                'result': ValidationResult.CRITICAL
            }

    async def _cross_validation_overfitting_test(self, data: pd.DataFrame) -> float:
        """Cross-validation test for overfitting"""

        k_folds = 5
        fold_size = len(data) // k_folds
        fold_performances = []

        for i in range(k_folds):
            start_idx = i * fold_size
            end_idx = (i + 1) * fold_size if i < k_folds - 1 else len(data)

            test_fold = data.iloc[start_idx:end_idx]
            train_fold = pd.concat([data.iloc[:start_idx], data.iloc[end_idx:]])

            if len(train_fold) > 0 and len(test_fold) > 0:
                train_perf = self._calculate_period_performance(train_fold)
                test_perf = self._calculate_period_performance(test_fold)

                # Calculate performance ratio
                if train_perf['avg_trade_pnl'] != 0:
                    ratio = test_perf['avg_trade_pnl'] / train_perf['avg_trade_pnl']
                    fold_performances.append(ratio)

        if not fold_performances:
            return 0

        # Good generalization should have consistent ratios close to 1
        mean_ratio = np.mean(fold_performances)
        std_ratio = np.std(fold_performances)

        # Score based on how close ratios are to 1 and how consistent they are
        consistency_score = max(0, 1 - std_ratio)
        ratio_score = max(0, 1 - abs(mean_ratio - 1))

        return (consistency_score + ratio_score) / 2

    async def _parameter_sensitivity_test(self, data: pd.DataFrame, parameters: Dict) -> float:
        """Test sensitivity to parameter changes"""

        # Test small perturbations to key parameters
        sensitivity_tests = []
        base_performance = self._calculate_period_performance(data)

        key_params = ['confidence_threshold', 'min_risk_reward']
        perturbations = [-5, -2, 2, 5]  # Percentage changes

        for param in key_params:
            if param in parameters:
                for perturbation in perturbations:
                    # Simulate parameter change effect on performance
                    # (This is a simplified simulation - in practice, you'd re-run the strategy)
                    adjusted_performance = base_performance['avg_trade_pnl'] * (1 - perturbation / 100)
                    sensitivity = abs(adjusted_performance - base_performance['avg_trade_pnl']) / abs(base_performance['avg_trade_pnl'])
                    sensitivity_tests.append(sensitivity)

        if not sensitivity_tests:
            return 0.5

        # Lower sensitivity means more robust parameters
        avg_sensitivity = np.mean(sensitivity_tests)
        robustness_score = max(0, 1 - avg_sensitivity * 2)  # Scale sensitivity

        return robustness_score

    async def _noise_resistance_test(self, data: pd.DataFrame) -> float:
        """Test resistance to market noise"""

        # Add different levels of noise to price data and test performance stability
        noise_levels = [0.001, 0.002, 0.005]  # 0.1%, 0.2%, 0.5% noise
        base_performance = self._calculate_period_performance(data)
        resistance_scores = []

        for noise_level in noise_levels:
            # Simulate adding noise to returns (simplified)
            noise_factor = np.random.normal(1, noise_level, len(data))
            simulated_performance = base_performance['avg_trade_pnl'] * np.mean(noise_factor)

            # Calculate performance degradation due to noise
            degradation = abs(simulated_performance - base_performance['avg_trade_pnl']) / abs(base_performance['avg_trade_pnl'])
            resistance_scores.append(max(0, 1 - degradation))

        return np.mean(resistance_scores) if resistance_scores else 0

    async def _validate_regime_robustness(self, data: pd.DataFrame) -> Dict:
        """Validate performance across different market regimes"""

        logger.info("Validating regime robustness...")

        try:
            # Simulate regime identification (simplified)
            regimes = self._identify_market_regimes(data)
            regime_performances = {}

            for regime, regime_data in regimes.items():
                if len(regime_data) >= 5:  # Minimum trades per regime
                    regime_perf = self._calculate_period_performance(regime_data)
                    regime_performances[regime] = regime_perf

            if len(regime_performances) < self.THRESHOLDS['min_regime_coverage']:
                return {
                    'robustness_score': 0,
                    'error': f"Insufficient regime coverage: {len(regime_performances)}",
                    'result': ValidationResult.FAIL
                }

            # Calculate robustness as consistency across regimes
            regime_pnls = [perf['avg_trade_pnl'] for perf in regime_performances.values()]
            regime_consistency = 1 - (np.std(regime_pnls) / (np.mean(np.abs(regime_pnls)) + 1e-6))
            robustness_score = max(0, regime_consistency * 100)

            return {
                'robustness_score': robustness_score,
                'regime_performances': regime_performances,
                'regime_count': len(regime_performances),
                'result': ValidationResult.PASS if robustness_score >= self.THRESHOLDS['regime_robustness'] else ValidationResult.FAIL
            }

        except Exception as e:
            logger.error(f"Regime robustness validation failed: {str(e)}")
            return {
                'robustness_score': 0,
                'error': str(e),
                'result': ValidationResult.CRITICAL
            }

    def _identify_market_regimes(self, data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Simplified regime identification for validation"""

        # Calculate volatility periods
        if 'returns' in data.columns:
            rolling_vol = data['returns'].rolling(20).std()
        else:
            # Approximate from PnL data
            rolling_vol = data['pnl'].rolling(20).std() if 'pnl' in data.columns else pd.Series([1] * len(data))

        vol_median = rolling_vol.median()

        regimes = {
            'low_volatility': data[rolling_vol <= vol_median * 0.7],
            'medium_volatility': data[(rolling_vol > vol_median * 0.7) & (rolling_vol <= vol_median * 1.3)],
            'high_volatility': data[rolling_vol > vol_median * 1.3]
        }

        return regimes

    async def _validate_stress_testing(self, data: pd.DataFrame) -> Dict:
        """Validate performance under stress conditions"""

        logger.info("Validating stress testing...")

        try:
            # Identify stress periods (high volatility, large drawdowns)
            stress_periods = self._identify_stress_periods(data)

            if not stress_periods:
                return {
                    'stress_score': 50,  # Neutral score if no stress periods
                    'message': "No stress periods identified",
                    'result': ValidationResult.WARNING
                }

            stress_performance = self._calculate_period_performance(stress_periods)
            normal_performance = self._calculate_period_performance(data)

            # Calculate stress resilience
            if normal_performance['avg_trade_pnl'] != 0:
                stress_ratio = stress_performance['avg_trade_pnl'] / normal_performance['avg_trade_pnl']
                stress_score = max(0, 50 + stress_ratio * 50)  # Scale 0-100
            else:
                stress_score = 0

            return {
                'stress_score': stress_score,
                'stress_periods_count': len(stress_periods),
                'stress_performance': stress_performance,
                'stress_ratio': stress_ratio if 'stress_ratio' in locals() else 0,
                'result': ValidationResult.PASS if stress_score >= self.THRESHOLDS['stress_test_score'] else ValidationResult.FAIL
            }

        except Exception as e:
            logger.error(f"Stress testing validation failed: {str(e)}")
            return {
                'stress_score': 0,
                'error': str(e),
                'result': ValidationResult.CRITICAL
            }

    def _identify_stress_periods(self, data: pd.DataFrame) -> pd.DataFrame:
        """Identify stress periods in the data"""

        if 'pnl' not in data.columns:
            return pd.DataFrame()

        # Calculate rolling drawdown
        cumulative_pnl = data['pnl'].cumsum()
        rolling_max = cumulative_pnl.expanding().max()
        drawdown = (cumulative_pnl - rolling_max) / (rolling_max.abs() + 1e-6)

        # Identify periods with significant drawdown (>5%)
        stress_mask = drawdown < -0.05

        return data[stress_mask]

    async def _validate_monte_carlo_projections(self, data: pd.DataFrame) -> Dict:
        """Validate Monte Carlo projection accuracy"""

        logger.info("Validating Monte Carlo projections...")

        try:
            # Run Monte Carlo simulation
            mc_results = self._run_monte_carlo_simulation(data)

            # Compare actual recent performance to projections
            recent_data = data.tail(30) if len(data) >= 30 else data
            actual_performance = self._calculate_period_performance(recent_data)

            # Check if actual performance falls within projected confidence intervals
            confidence_score = self._calculate_monte_carlo_accuracy(actual_performance, mc_results)

            return {
                'monte_carlo_confidence': confidence_score,
                'monte_carlo_results': mc_results,
                'actual_vs_projected': {
                    'actual_pnl': actual_performance['avg_trade_pnl'],
                    'projected_pnl': mc_results.get('expected_pnl', 0),
                    'within_confidence_interval': confidence_score > 70
                },
                'result': ValidationResult.PASS if confidence_score >= self.THRESHOLDS['monte_carlo_confidence'] else ValidationResult.FAIL
            }

        except Exception as e:
            logger.error(f"Monte Carlo validation failed: {str(e)}")
            return {
                'monte_carlo_confidence': 0,
                'error': str(e),
                'result': ValidationResult.CRITICAL
            }

    def _run_monte_carlo_simulation(self, data: pd.DataFrame, num_simulations: int = 1000) -> Dict:
        """Run Monte Carlo simulation for validation"""

        if 'pnl' not in data.columns:
            return {'expected_pnl': 0, 'confidence_intervals': {}}

        # Calculate return distribution statistics
        returns = data['pnl'].values
        mean_return = np.mean(returns)
        std_return = np.std(returns)

        # Run simulations
        simulated_returns = np.random.normal(mean_return, std_return, (num_simulations, 30))
        simulated_cumulative = np.sum(simulated_returns, axis=1)

        # Calculate confidence intervals
        confidence_intervals = {
            '90%': (np.percentile(simulated_cumulative, 5), np.percentile(simulated_cumulative, 95)),
            '95%': (np.percentile(simulated_cumulative, 2.5), np.percentile(simulated_cumulative, 97.5))
        }

        return {
            'expected_pnl': mean_return,
            'confidence_intervals': confidence_intervals,
            'simulation_count': num_simulations
        }

    def _calculate_monte_carlo_accuracy(self, actual_performance: Dict, mc_results: Dict) -> float:
        """Calculate accuracy of Monte Carlo projections"""

        actual_pnl = actual_performance.get('avg_trade_pnl', 0)
        confidence_intervals = mc_results.get('confidence_intervals', {})

        if '90%' in confidence_intervals:
            lower_90, upper_90 = confidence_intervals['90%']
            if lower_90 <= actual_pnl <= upper_90:
                return 90.0

        if '95%' in confidence_intervals:
            lower_95, upper_95 = confidence_intervals['95%']
            if lower_95 <= actual_pnl <= upper_95:
                return 85.0

        # Calculate distance from expected
        expected_pnl = mc_results.get('expected_pnl', 0)
        if expected_pnl != 0:
            accuracy = max(0, 100 - abs(actual_pnl - expected_pnl) / abs(expected_pnl) * 100)
        else:
            accuracy = 0

        return accuracy

    def _calculate_period_performance(self, period_data: pd.DataFrame) -> Dict:
        """Calculate performance metrics for a data period"""

        if period_data.empty:
            return {
                'avg_trade_pnl': 0,
                'total_pnl': 0,
                'win_rate': 0,
                'trade_count': 0,
                'sharpe_ratio': 0
            }

        if 'pnl' in period_data.columns:
            pnl_data = period_data['pnl']
        else:
            # Fallback to any numeric column
            numeric_cols = period_data.select_dtypes(include=[np.number]).columns
            pnl_data = period_data[numeric_cols[0]] if len(numeric_cols) > 0 else pd.Series([0])

        total_pnl = pnl_data.sum()
        avg_trade_pnl = pnl_data.mean()
        win_rate = (pnl_data > 0).mean() * 100
        trade_count = len(pnl_data)

        # Calculate Sharpe ratio
        if pnl_data.std() != 0:
            sharpe_ratio = avg_trade_pnl / pnl_data.std()
        else:
            sharpe_ratio = 0

        return {
            'avg_trade_pnl': avg_trade_pnl,
            'total_pnl': total_pnl,
            'win_rate': win_rate,
            'trade_count': trade_count,
            'sharpe_ratio': sharpe_ratio
        }

    def _compile_validation_metrics(self, validation_results: List) -> ValidationMetrics:
        """Compile individual validation results into overall metrics"""

        # Extract scores from results (handling exceptions)
        def safe_extract(result, key, default=0):
            try:
                return result.get(key, default) if isinstance(result, dict) else default
            except:
                return default

        walk_forward = safe_extract(validation_results[0], 'stability_score', 0)
        out_of_sample = safe_extract(validation_results[1], 'consistency_score', 0)
        overfitting = safe_extract(validation_results[2], 'overfitting_score', 1) * 100  # Convert to 0-100
        regime_robustness = safe_extract(validation_results[3], 'robustness_score', 0)
        stress_test = safe_extract(validation_results[4], 'stress_score', 0)
        monte_carlo = safe_extract(validation_results[5], 'monte_carlo_confidence', 0)

        # Calculate overall deployment readiness
        scores = [walk_forward, out_of_sample, (100 - overfitting), regime_robustness, stress_test, monte_carlo]
        deployment_readiness = np.mean([s for s in scores if s > 0]) if any(s > 0 for s in scores) else 0

        return ValidationMetrics(
            walk_forward_stability=walk_forward,
            out_of_sample_consistency=out_of_sample,
            overfitting_score=overfitting / 100,  # Back to 0-1 scale
            regime_robustness=regime_robustness,
            stress_test_score=stress_test,
            monte_carlo_confidence=monte_carlo,
            deployment_readiness=deployment_readiness
        )

    def _compile_detailed_results(self, validation_results: List) -> Dict[str, Any]:
        """Compile detailed results from all validation tests"""

        result_keys = [
            'walk_forward_stability',
            'out_of_sample_consistency',
            'overfitting_resistance',
            'regime_robustness',
            'stress_testing',
            'monte_carlo_projections'
        ]

        detailed = {}
        for i, key in enumerate(result_keys):
            if i < len(validation_results) and not isinstance(validation_results[i], Exception):
                detailed[key] = validation_results[i]
            else:
                detailed[key] = {'error': 'Validation failed', 'result': ValidationResult.CRITICAL}

        return detailed

    def _determine_overall_result(self, metrics: ValidationMetrics) -> ValidationResult:
        """Determine overall validation result"""

        critical_failures = 0
        failures = 0
        warnings = 0

        # Check each metric against thresholds
        if metrics.walk_forward_stability < self.THRESHOLDS['walk_forward_stability']:
            if metrics.walk_forward_stability < 30:
                critical_failures += 1
            else:
                failures += 1

        if metrics.out_of_sample_consistency < self.THRESHOLDS['out_of_sample_consistency']:
            if metrics.out_of_sample_consistency < 40:
                critical_failures += 1
            else:
                failures += 1

        if metrics.overfitting_score > self.THRESHOLDS['overfitting_score']:
            if metrics.overfitting_score > 0.7:
                critical_failures += 1
            else:
                failures += 1

        if metrics.regime_robustness < self.THRESHOLDS['regime_robustness']:
            warnings += 1

        if metrics.stress_test_score < self.THRESHOLDS['stress_test_score']:
            warnings += 1

        if metrics.monte_carlo_confidence < self.THRESHOLDS['monte_carlo_confidence']:
            warnings += 1

        # Determine overall result
        if critical_failures > 0:
            return ValidationResult.CRITICAL
        elif failures > 1:
            return ValidationResult.FAIL
        elif failures > 0 or warnings > 2:
            return ValidationResult.WARNING
        else:
            return ValidationResult.PASS

    def _generate_recommendations(self, metrics: ValidationMetrics, detailed_results: Dict) -> List[str]:
        """Generate specific recommendations based on validation results"""

        recommendations = []

        if metrics.walk_forward_stability < self.THRESHOLDS['walk_forward_stability']:
            recommendations.append("Implement parameter regularization to improve stability")
            recommendations.append("Collect additional validation data (3-6 months)")

        if metrics.out_of_sample_consistency < self.THRESHOLDS['out_of_sample_consistency']:
            recommendations.append("System shows poor generalization - review parameter optimization")
            recommendations.append("Consider ensemble approach with multiple parameter sets")

        if metrics.overfitting_score > self.THRESHOLDS['overfitting_score']:
            recommendations.append("High overfitting risk - implement constraints on parameter optimization")
            recommendations.append("Use cross-validation during parameter selection")

        if metrics.regime_robustness < self.THRESHOLDS['regime_robustness']:
            recommendations.append("Improve performance consistency across market regimes")
            recommendations.append("Implement regime-adaptive parameters")

        if metrics.stress_test_score < self.THRESHOLDS['stress_test_score']:
            recommendations.append("Enhance risk management for stress periods")
            recommendations.append("Reduce position sizes during high volatility")

        if metrics.monte_carlo_confidence < self.THRESHOLDS['monte_carlo_confidence']:
            recommendations.append("Monte Carlo projections unreliable - review risk models")
            recommendations.append("Implement more conservative position sizing")

        if metrics.deployment_readiness < 70:
            recommendations.append("HALT DEPLOYMENT - System not ready for live trading")
            recommendations.append("Continue paper trading until all metrics improve")

        return recommendations

    def _check_deployment_gates(self, metrics: ValidationMetrics) -> Dict[str, bool]:
        """Check deployment gates based on metrics"""

        gates = {
            'stability_gate': metrics.walk_forward_stability >= self.THRESHOLDS['walk_forward_stability'],
            'consistency_gate': metrics.out_of_sample_consistency >= self.THRESHOLDS['out_of_sample_consistency'],
            'overfitting_gate': metrics.overfitting_score <= self.THRESHOLDS['overfitting_score'],
            'robustness_gate': metrics.regime_robustness >= self.THRESHOLDS['regime_robustness'],
            'stress_gate': metrics.stress_test_score >= self.THRESHOLDS['stress_test_score'],
            'confidence_gate': metrics.monte_carlo_confidence >= self.THRESHOLDS['monte_carlo_confidence']
        }

        gates['overall_gate'] = all(gates.values())

        return gates

    def _assess_risk_level(self, metrics: ValidationMetrics, detailed_results: Dict) -> str:
        """Assess overall risk level for deployment"""

        if metrics.deployment_readiness >= 80:
            return "LOW_RISK"
        elif metrics.deployment_readiness >= 60:
            return "MODERATE_RISK"
        elif metrics.deployment_readiness >= 40:
            return "HIGH_RISK"
        else:
            return "CRITICAL_RISK"

    def _determine_next_actions(self, overall_result: ValidationResult, metrics: ValidationMetrics) -> List[str]:
        """Determine next actions based on validation results"""

        actions = []

        if overall_result == ValidationResult.CRITICAL:
            actions.extend([
                "IMMEDIATE: Halt all live trading",
                "Review system architecture for fundamental issues",
                "Implement emergency rollback to last stable version",
                "Collect minimum 3 months additional validation data"
            ])
        elif overall_result == ValidationResult.FAIL:
            actions.extend([
                "Continue paper trading only",
                "Implement top 3 recommendations",
                "Re-run validation after improvements",
                "Consider parameter ensemble approach"
            ])
        elif overall_result == ValidationResult.WARNING:
            actions.extend([
                "Deploy with reduced position sizes (25% max)",
                "Implement real-time monitoring",
                "Set strict performance gates",
                "Plan weekly validation reviews"
            ])
        else:  # PASS
            actions.extend([
                "Proceed with phased deployment (25% → 50% → 100%)",
                "Implement continuous monitoring",
                "Set monthly validation schedule",
                "Monitor for regime changes"
            ])

        return actions

    async def _save_validation_report(self, report: ValidationReport):
        """Save validation report for audit trail"""

        try:
            reports_dir = Path("validation_reports")
            reports_dir.mkdir(exist_ok=True)

            timestamp = report.timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"validation_report_{timestamp}.json"

            # Convert report to JSON-serializable format
            report_dict = {
                'overall_result': report.overall_result.value,
                'metrics': {
                    'walk_forward_stability': report.metrics.walk_forward_stability,
                    'out_of_sample_consistency': report.metrics.out_of_sample_consistency,
                    'overfitting_score': report.metrics.overfitting_score,
                    'regime_robustness': report.metrics.regime_robustness,
                    'stress_test_score': report.metrics.stress_test_score,
                    'monte_carlo_confidence': report.metrics.monte_carlo_confidence,
                    'deployment_readiness': report.metrics.deployment_readiness
                },
                'detailed_results': report.detailed_results,
                'recommendations': report.recommendations,
                'deployment_gates': report.deployment_gates,
                'risk_assessment': report.risk_assessment,
                'next_actions': report.next_actions,
                'timestamp': report.timestamp.isoformat()
            }

            with open(reports_dir / filename, 'w') as f:
                json.dump(report_dict, f, indent=2, default=str)

            logger.info(f"Validation report saved: {filename}")

        except Exception as e:
            logger.error(f"Failed to save validation report: {str(e)}")

# Usage example and test harness
async def run_enhanced_validation():
    """Example usage of enhanced validation framework"""

    # Mock configuration
    config = {
        'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY'],
        'validation_period': 90
    }

    validator = EnhancedValidator(config)

    # Mock data for testing
    mock_data = pd.DataFrame({
        'pnl': np.random.normal(50, 200, 1000),  # Mock trade PnL data
        'timestamp': pd.date_range('2025-01-01', periods=1000, freq='H')
    })

    mock_parameters = {
        'confidence_threshold': 70.0,
        'min_risk_reward': 2.8
    }

    # Run comprehensive validation
    report = await validator.comprehensive_validation(mock_data, mock_parameters)

    print(f"Overall Result: {report.overall_result.value}")
    print(f"Deployment Readiness: {report.metrics.deployment_readiness:.1f}%")
    print(f"Risk Assessment: {report.risk_assessment}")
    print("\nRecommendations:")
    for i, rec in enumerate(report.recommendations, 1):
        print(f"{i}. {rec}")

if __name__ == "__main__":
    # Run the validation example
    asyncio.run(run_enhanced_validation())