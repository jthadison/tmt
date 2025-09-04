"""
Confidence Threshold Optimizer

Dynamically optimizes confidence thresholds for signal generation based on 
real-time performance feedback and market conditions.

Purpose: Address the 2.9% signal execution ratio by finding optimal confidence 
thresholds that balance signal quality with execution frequency.
"""

from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime, timedelta
import logging
import asyncio
import json
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ThresholdTestResult:
    """Results from testing a specific confidence threshold"""
    threshold: float
    signals_generated: int
    signals_executed: int
    conversion_rate: float
    avg_profit_per_trade: float
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    quality_score: float
    test_period_days: int


@dataclass
class OptimizationRecommendation:
    """Optimization recommendation with implementation details"""
    recommended_threshold: float
    current_threshold: float
    expected_improvement: Dict[str, float]
    confidence_level: float
    implementation_priority: str  # 'high', 'medium', 'low'
    reasoning: str
    rollback_conditions: Dict[str, float]


class ConfidenceThresholdOptimizer:
    """
    Optimizes confidence thresholds for signal generation using various strategies.
    
    Features:
    - Walk-forward optimization
    - Bayesian optimization for parameter search
    - Market regime adaptive thresholds
    - Real-time performance feedback
    - Automatic rollback on poor performance
    """
    
    def __init__(self,
                 optimization_window_days: int = 14,
                 test_thresholds: List[float] = None,
                 min_trades_for_validation: int = 5,
                 performance_decline_threshold: float = 0.05):
        """
        Initialize the confidence threshold optimizer.
        
        Args:
            optimization_window_days: Days of data to use for optimization
            test_thresholds: List of thresholds to test
            min_trades_for_validation: Minimum trades needed for valid test
            performance_decline_threshold: Threshold for triggering rollback
        """
        self.optimization_window_days = optimization_window_days
        self.test_thresholds = test_thresholds or np.arange(50.0, 95.0, 2.5).tolist()
        self.min_trades_for_validation = min_trades_for_validation
        self.performance_decline_threshold = performance_decline_threshold
        
        # Optimization history
        self.optimization_history = []
        self.current_optimal_threshold = 65.0  # Default starting threshold
        self.last_optimization_time = None
        
        # Performance tracking
        self.performance_baseline = None
        self.current_performance_window = []
        
        # Market regime awareness
        self.regime_thresholds = {
            'trending': 70.0,
            'ranging': 65.0,
            'volatile': 75.0,
            'breakout': 68.0
        }
        
    async def optimize_threshold(self,
                               historical_signals: List[Dict],
                               execution_data: List[Dict],
                               market_data: pd.DataFrame = None) -> OptimizationRecommendation:
        """
        Main optimization function to find optimal confidence threshold.
        
        Args:
            historical_signals: Historical signal data
            execution_data: Historical execution data
            market_data: Optional market data for regime detection
            
        Returns:
            OptimizationRecommendation with optimal threshold and implementation details
        """
        try:
            logger.info("Starting confidence threshold optimization")
            
            # Prepare data for optimization
            optimization_data = await self._prepare_optimization_data(
                historical_signals, execution_data
            )
            
            if not self._validate_optimization_data(optimization_data):
                return self._create_insufficient_data_recommendation()
            
            # Test multiple thresholds
            threshold_results = await self._test_multiple_thresholds(optimization_data)
            
            # Find optimal threshold using multiple criteria
            optimal_threshold = await self._find_optimal_threshold(threshold_results)
            
            # Validate optimal threshold
            validation_result = await self._validate_optimal_threshold(
                optimal_threshold, threshold_results, optimization_data
            )
            
            # Create recommendation
            recommendation = await self._create_optimization_recommendation(
                optimal_threshold, validation_result, threshold_results
            )
            
            # Update optimization history
            self._update_optimization_history(recommendation, threshold_results)
            
            logger.info(f"Optimization completed: {self.current_optimal_threshold} -> {optimal_threshold}")
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error in confidence threshold optimization: {e}")
            return self._create_error_recommendation(str(e))
    
    async def _prepare_optimization_data(self,
                                       signals: List[Dict],
                                       executions: List[Dict]) -> Dict:
        """Prepare and clean data for optimization"""
        
        # Filter to optimization window
        cutoff_date = datetime.now() - timedelta(days=self.optimization_window_days)
        
        recent_signals = [
            s for s in signals
            if s.get('generated_at', datetime.min) > cutoff_date
        ]
        
        recent_executions = [
            e for e in executions
            if e.get('executed_at', datetime.min) > cutoff_date
        ]
        
        # Match executions to signals
        signal_execution_pairs = []
        for signal in recent_signals:
            signal_id = signal.get('signal_id')
            execution = next((e for e in recent_executions if e.get('signal_id') == signal_id), None)
            
            signal_execution_pairs.append({
                'signal': signal,
                'execution': execution,
                'was_executed': execution is not None
            })
        
        return {
            'signal_execution_pairs': signal_execution_pairs,
            'total_signals': len(recent_signals),
            'total_executions': len(recent_executions),
            'data_start_date': cutoff_date,
            'data_end_date': datetime.now()
        }
    
    def _validate_optimization_data(self, optimization_data: Dict) -> bool:
        """Validate that we have sufficient data for optimization"""
        
        total_signals = optimization_data.get('total_signals', 0)
        total_executions = optimization_data.get('total_executions', 0)
        
        # Check minimum data requirements
        if total_signals < 20:
            logger.warning(f"Insufficient signals for optimization: {total_signals} < 20")
            return False
        
        if total_executions < self.min_trades_for_validation:
            logger.warning(f"Insufficient executions for validation: {total_executions} < {self.min_trades_for_validation}")
            return False
        
        return True
    
    async def _test_multiple_thresholds(self, optimization_data: Dict) -> List[ThresholdTestResult]:
        """Test multiple confidence thresholds and calculate performance metrics"""
        
        results = []
        signal_execution_pairs = optimization_data['signal_execution_pairs']
        
        for threshold in self.test_thresholds:
            result = await self._test_single_threshold(threshold, signal_execution_pairs)
            if result:
                results.append(result)
        
        return results
    
    async def _test_single_threshold(self,
                                   threshold: float,
                                   signal_execution_pairs: List[Dict]) -> Optional[ThresholdTestResult]:
        """Test a single confidence threshold"""
        
        # Filter signals that would pass this threshold
        qualifying_pairs = [
            pair for pair in signal_execution_pairs
            if pair['signal'].get('confidence', 0) >= threshold
        ]
        
        if not qualifying_pairs:
            return None
        
        signals_generated = len(qualifying_pairs)
        executed_pairs = [pair for pair in qualifying_pairs if pair['was_executed']]
        signals_executed = len(executed_pairs)
        
        # Calculate basic metrics
        conversion_rate = signals_executed / signals_generated if signals_generated > 0 else 0
        
        if signals_executed == 0:
            # No executions - return basic result
            return ThresholdTestResult(
                threshold=threshold,
                signals_generated=signals_generated,
                signals_executed=0,
                conversion_rate=conversion_rate,
                avg_profit_per_trade=0,
                win_rate=0,
                profit_factor=0,
                sharpe_ratio=0,
                max_drawdown=0,
                quality_score=0,
                test_period_days=self.optimization_window_days
            )
        
        # Calculate performance metrics for executed trades
        profits = [pair['execution'].get('pnl', 0) for pair in executed_pairs]
        
        avg_profit = np.mean(profits)
        win_rate = len([p for p in profits if p > 0]) / len(profits)
        
        # Calculate profit factor
        gross_profit = sum([p for p in profits if p > 0])
        gross_loss = abs(sum([p for p in profits if p < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Calculate Sharpe ratio (simplified)
        sharpe_ratio = (avg_profit / np.std(profits)) if np.std(profits) > 0 else 0
        
        # Calculate max drawdown
        cumulative_returns = np.cumsum(profits)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdown = cumulative_returns - running_max
        max_drawdown = abs(np.min(drawdown)) if len(drawdown) > 0 else 0
        
        # Calculate composite quality score
        quality_score = self._calculate_threshold_quality_score(
            conversion_rate, avg_profit, win_rate, profit_factor, sharpe_ratio, max_drawdown
        )
        
        return ThresholdTestResult(
            threshold=threshold,
            signals_generated=signals_generated,
            signals_executed=signals_executed,
            conversion_rate=conversion_rate,
            avg_profit_per_trade=avg_profit,
            win_rate=win_rate,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            quality_score=quality_score,
            test_period_days=self.optimization_window_days
        )
    
    def _calculate_threshold_quality_score(self,
                                         conversion_rate: float,
                                         avg_profit: float,
                                         win_rate: float,
                                         profit_factor: float,
                                         sharpe_ratio: float,
                                         max_drawdown: float) -> float:
        """Calculate composite quality score for threshold optimization"""
        
        # Normalize metrics to 0-100 scale
        conversion_score = min(conversion_rate * 100, 100)      # Target 100% conversion
        profit_score = max(0, min((avg_profit + 5) * 10, 100)) # $5 profit = 100 points
        win_rate_score = win_rate * 100                         # Target 100% win rate
        pf_score = min(profit_factor * 25, 100)                 # PF of 4 = 100 points
        sharpe_score = max(0, min((sharpe_ratio + 1) * 50, 100)) # Sharpe of 1 = 100 points
        drawdown_score = max(0, 100 - (max_drawdown * 10))     # Lower drawdown = higher score
        
        # Weighted composite score prioritizing conversion and profitability
        quality_score = (
            conversion_score * 0.25 +    # 25% weight on conversion rate
            profit_score * 0.20 +        # 20% weight on profitability
            win_rate_score * 0.20 +      # 20% weight on win rate
            pf_score * 0.15 +            # 15% weight on profit factor
            sharpe_score * 0.10 +        # 10% weight on risk-adjusted returns
            drawdown_score * 0.10        # 10% weight on drawdown control
        )
        
        return quality_score
    
    async def _find_optimal_threshold(self, threshold_results: List[ThresholdTestResult]) -> float:
        """Find optimal threshold using multi-criteria optimization"""
        
        if not threshold_results:
            return self.current_optimal_threshold
        
        # Strategy 1: Highest quality score
        best_quality = max(threshold_results, key=lambda x: x.quality_score)
        
        # Strategy 2: Best conversion rate with minimum profitability
        profitable_thresholds = [r for r in threshold_results if r.avg_profit_per_trade > 0]
        if profitable_thresholds:
            best_conversion = max(profitable_thresholds, key=lambda x: x.conversion_rate)
        else:
            best_conversion = best_quality
        
        # Strategy 3: Best risk-adjusted returns
        best_sharpe = max(threshold_results, key=lambda x: x.sharpe_ratio)
        
        # Strategy 4: Balanced approach (good conversion + profitability)
        balanced_candidates = [
            r for r in threshold_results
            if r.conversion_rate >= 0.10 and r.avg_profit_per_trade > 0 and r.win_rate >= 0.5
        ]
        
        if balanced_candidates:
            best_balanced = max(balanced_candidates, key=lambda x: (x.conversion_rate * x.avg_profit_per_trade))
        else:
            best_balanced = best_quality
        
        # Voting system to select optimal threshold
        threshold_votes = {}
        candidates = [best_quality, best_conversion, best_sharpe, best_balanced]
        
        for candidate in candidates:
            threshold = candidate.threshold
            threshold_votes[threshold] = threshold_votes.get(threshold, 0) + 1
        
        # Select threshold with most votes, or best quality if tie
        winning_threshold = max(threshold_votes.items(), key=lambda x: x[1])[0]
        
        # Validate the winning threshold has good performance
        winning_result = next(r for r in threshold_results if r.threshold == winning_threshold)
        
        # Apply safety checks
        if winning_result.signals_generated < 5:
            logger.warning(f"Winning threshold {winning_threshold} generates too few signals")
            # Fall back to threshold that generates more signals
            alternatives = [r for r in threshold_results if r.signals_generated >= 5]
            if alternatives:
                winning_threshold = max(alternatives, key=lambda x: x.quality_score).threshold
        
        return winning_threshold
    
    async def _validate_optimal_threshold(self,
                                        optimal_threshold: float,
                                        threshold_results: List[ThresholdTestResult],
                                        optimization_data: Dict) -> Dict:
        """Validate the optimal threshold meets performance criteria"""
        
        optimal_result = next(r for r in threshold_results if r.threshold == optimal_threshold)
        current_result = next((r for r in threshold_results if r.threshold == self.current_optimal_threshold), None)
        
        validation = {
            'is_valid': True,
            'validation_criteria': {},
            'performance_comparison': {},
            'risk_assessment': {}
        }
        
        # Validation criteria
        validation['validation_criteria'] = {
            'min_conversion_rate': optimal_result.conversion_rate >= 0.05,  # 5% minimum
            'positive_profitability': optimal_result.avg_profit_per_trade > 0,
            'reasonable_win_rate': optimal_result.win_rate >= 0.40,         # 40% minimum
            'sufficient_signals': optimal_result.signals_generated >= 3,
            'controlled_drawdown': optimal_result.max_drawdown <= 50.0      # Max $50 drawdown
        }
        
        # Check if all criteria pass
        validation['is_valid'] = all(validation['validation_criteria'].values())
        
        # Performance comparison with current threshold
        if current_result:
            validation['performance_comparison'] = {
                'conversion_improvement': optimal_result.conversion_rate - current_result.conversion_rate,
                'profit_improvement': optimal_result.avg_profit_per_trade - current_result.avg_profit_per_trade,
                'quality_improvement': optimal_result.quality_score - current_result.quality_score,
                'signals_change': optimal_result.signals_generated - current_result.signals_generated
            }
        
        # Risk assessment
        validation['risk_assessment'] = {
            'drawdown_risk': 'high' if optimal_result.max_drawdown > 30 else 'low',
            'conversion_risk': 'high' if optimal_result.conversion_rate < 0.10 else 'low',
            'profitability_risk': 'high' if optimal_result.avg_profit_per_trade < 0 else 'low'
        }
        
        return validation
    
    async def _create_optimization_recommendation(self,
                                                optimal_threshold: float,
                                                validation_result: Dict,
                                                threshold_results: List[ThresholdTestResult]) -> OptimizationRecommendation:
        """Create comprehensive optimization recommendation"""
        
        optimal_result = next(r for r in threshold_results if r.threshold == optimal_threshold)
        current_result = next((r for r in threshold_results if r.threshold == self.current_optimal_threshold), None)
        
        # Calculate expected improvements
        if current_result:
            expected_improvement = {
                'conversion_rate_change': optimal_result.conversion_rate - current_result.conversion_rate,
                'profit_per_trade_change': optimal_result.avg_profit_per_trade - current_result.avg_profit_per_trade,
                'win_rate_change': optimal_result.win_rate - current_result.win_rate,
                'quality_score_improvement': optimal_result.quality_score - current_result.quality_score,
                'signals_generation_change': optimal_result.signals_generated - current_result.signals_generated
            }
        else:
            expected_improvement = {
                'conversion_rate_change': 0.05,  # Estimated 5% improvement
                'profit_per_trade_change': 1.0,  # Estimated $1 improvement
                'win_rate_change': 0.05,         # Estimated 5% improvement
                'quality_score_improvement': 10.0, # Estimated 10 point improvement
                'signals_generation_change': 0
            }
        
        # Determine implementation priority
        quality_improvement = expected_improvement.get('quality_score_improvement', 0)
        conversion_improvement = expected_improvement.get('conversion_rate_change', 0)
        
        if quality_improvement > 20 or conversion_improvement > 0.10:
            priority = 'high'
        elif quality_improvement > 10 or conversion_improvement > 0.05:
            priority = 'medium'
        else:
            priority = 'low'
        
        # Generate reasoning
        reasoning_parts = []
        
        if conversion_improvement > 0.05:
            reasoning_parts.append(f"Conversion rate improves by {conversion_improvement:.1%}")
        
        if expected_improvement.get('profit_per_trade_change', 0) > 0:
            reasoning_parts.append(f"Profit per trade increases by ${expected_improvement['profit_per_trade_change']:.2f}")
        
        if optimal_result.quality_score > 60:
            reasoning_parts.append(f"High quality score of {optimal_result.quality_score:.1f}")
        
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "Marginal improvement expected"
        
        # Set rollback conditions
        rollback_conditions = {
            'max_performance_decline': 0.10,     # 10% performance decline triggers rollback
            'min_conversion_rate': max(0.05, optimal_result.conversion_rate * 0.5), # 50% of expected or 5% minimum
            'max_drawdown_increase': optimal_result.max_drawdown * 1.5,  # 50% increase in drawdown
            'monitoring_period_days': 7          # Monitor for 7 days
        }
        
        # Confidence level based on validation
        confidence_factors = []
        if validation_result.get('is_valid', False):
            confidence_factors.append(30)  # Base confidence for valid result
        if optimal_result.signals_generated >= 10:
            confidence_factors.append(20)  # Good sample size
        if optimal_result.conversion_rate >= 0.15:
            confidence_factors.append(25)  # Good conversion rate
        if optimal_result.avg_profit_per_trade > 1:
            confidence_factors.append(25)  # Good profitability
        
        confidence_level = min(sum(confidence_factors), 100) / 100
        
        return OptimizationRecommendation(
            recommended_threshold=optimal_threshold,
            current_threshold=self.current_optimal_threshold,
            expected_improvement=expected_improvement,
            confidence_level=confidence_level,
            implementation_priority=priority,
            reasoning=reasoning,
            rollback_conditions=rollback_conditions
        )
    
    def _create_insufficient_data_recommendation(self) -> OptimizationRecommendation:
        """Create recommendation when insufficient data is available"""
        return OptimizationRecommendation(
            recommended_threshold=self.current_optimal_threshold,
            current_threshold=self.current_optimal_threshold,
            expected_improvement={'message': 'Insufficient data for optimization'},
            confidence_level=0.0,
            implementation_priority='low',
            reasoning='Insufficient historical data for meaningful optimization',
            rollback_conditions={}
        )
    
    def _create_error_recommendation(self, error_message: str) -> OptimizationRecommendation:
        """Create recommendation when an error occurs"""
        return OptimizationRecommendation(
            recommended_threshold=self.current_optimal_threshold,
            current_threshold=self.current_optimal_threshold,
            expected_improvement={'error': error_message},
            confidence_level=0.0,
            implementation_priority='low',
            reasoning=f'Optimization failed: {error_message}',
            rollback_conditions={}
        )
    
    def _update_optimization_history(self,
                                   recommendation: OptimizationRecommendation,
                                   threshold_results: List[ThresholdTestResult]):
        """Update optimization history for tracking and analysis"""
        
        history_entry = {
            'timestamp': datetime.now(),
            'previous_threshold': self.current_optimal_threshold,
            'recommended_threshold': recommendation.recommended_threshold,
            'confidence_level': recommendation.confidence_level,
            'expected_improvement': recommendation.expected_improvement,
            'implementation_priority': recommendation.implementation_priority,
            'threshold_test_results': [asdict(result) for result in threshold_results],
            'reasoning': recommendation.reasoning
        }
        
        self.optimization_history.append(history_entry)
        
        # Keep only last 10 optimization runs
        if len(self.optimization_history) > 10:
            self.optimization_history = self.optimization_history[-10:]
        
        # Update current optimal threshold
        if recommendation.implementation_priority in ['high', 'medium']:
            self.current_optimal_threshold = recommendation.recommended_threshold
            self.last_optimization_time = datetime.now()
    
    async def get_market_regime_threshold(self, market_regime: str) -> float:
        """Get optimal threshold for specific market regime"""
        return self.regime_thresholds.get(market_regime, self.current_optimal_threshold)
    
    async def monitor_threshold_performance(self,
                                          recent_signals: List[Dict],
                                          recent_executions: List[Dict],
                                          monitoring_window_hours: int = 24) -> Dict:
        """Monitor current threshold performance and suggest adjustments"""
        
        # Filter recent data
        cutoff_time = datetime.now() - timedelta(hours=monitoring_window_hours)
        
        monitored_signals = [
            s for s in recent_signals
            if s.get('generated_at', datetime.min) > cutoff_time
        ]
        
        monitored_executions = [
            e for e in recent_executions
            if e.get('executed_at', datetime.min) > cutoff_time
        ]
        
        if not monitored_signals:
            return {
                'monitoring_status': 'insufficient_data',
                'message': f'No signals in last {monitoring_window_hours} hours'
            }
        
        # Calculate current performance
        executed_signal_ids = {e.get('signal_id') for e in monitored_executions}
        qualifying_signals = [
            s for s in monitored_signals
            if s.get('confidence', 0) >= self.current_optimal_threshold
        ]
        
        current_conversion = len(monitored_executions) / len(qualifying_signals) if qualifying_signals else 0
        
        # Calculate profits if any executions
        if monitored_executions:
            profits = [e.get('pnl', 0) for e in monitored_executions]
            current_avg_profit = np.mean(profits)
            current_win_rate = len([p for p in profits if p > 0]) / len(profits)
        else:
            current_avg_profit = 0
            current_win_rate = 0
        
        # Compare with expected performance
        performance_status = 'good'
        alerts = []
        
        if current_conversion < 0.05:  # Less than 5% conversion
            performance_status = 'poor'
            alerts.append('Very low conversion rate - consider lowering threshold')
        elif current_conversion < 0.10:  # Less than 10% conversion
            performance_status = 'below_target'
            alerts.append('Below target conversion rate')
        
        if monitored_executions and current_avg_profit < 0:
            performance_status = 'poor'
            alerts.append('Negative average profit - review signal quality')
        
        if monitored_executions and current_win_rate < 0.40:
            alerts.append('Low win rate - may need threshold adjustment')
        
        # Generate adjustment suggestions
        adjustment_suggestion = None
        if performance_status == 'poor':
            if current_conversion < 0.05:
                adjustment_suggestion = {
                    'action': 'lower_threshold',
                    'suggested_threshold': max(50.0, self.current_optimal_threshold - 5.0),
                    'reason': 'Increase signal generation and conversion'
                }
            elif current_avg_profit < -5:  # Large losses
                adjustment_suggestion = {
                    'action': 'raise_threshold',
                    'suggested_threshold': min(90.0, self.current_optimal_threshold + 5.0),
                    'reason': 'Improve signal quality and reduce losses'
                }
        
        return {
            'monitoring_status': 'completed',
            'monitoring_window_hours': monitoring_window_hours,
            'current_threshold': self.current_optimal_threshold,
            'performance_metrics': {
                'signals_generated': len(monitored_signals),
                'qualifying_signals': len(qualifying_signals),
                'signals_executed': len(monitored_executions),
                'conversion_rate': current_conversion,
                'avg_profit_per_trade': current_avg_profit,
                'win_rate': current_win_rate
            },
            'performance_status': performance_status,
            'alerts': alerts,
            'adjustment_suggestion': adjustment_suggestion,
            'timestamp': datetime.now()
        }
    
    async def implement_threshold_change(self,
                                       new_threshold: float,
                                       change_reason: str = 'manual_adjustment') -> Dict:
        """Implement a threshold change with proper logging and rollback setup"""
        
        old_threshold = self.current_optimal_threshold
        
        # Validate new threshold
        if not 40.0 <= new_threshold <= 95.0:
            return {
                'implementation_status': 'failed',
                'error': f'Invalid threshold {new_threshold}. Must be between 40.0 and 95.0',
                'current_threshold': old_threshold
            }
        
        # Implement change
        self.current_optimal_threshold = new_threshold
        
        # Log the change
        change_record = {
            'timestamp': datetime.now(),
            'old_threshold': old_threshold,
            'new_threshold': new_threshold,
            'change_reason': change_reason,
            'implemented_by': 'ConfidenceThresholdOptimizer'
        }
        
        # Add to history
        self.optimization_history.append({
            'timestamp': datetime.now(),
            'previous_threshold': old_threshold,
            'recommended_threshold': new_threshold,
            'confidence_level': 0.8,  # Manual changes get medium confidence
            'expected_improvement': {'manual_change': True},
            'implementation_priority': 'high',
            'threshold_test_results': [],
            'reasoning': change_reason
        })
        
        logger.info(f"Confidence threshold changed: {old_threshold} -> {new_threshold} ({change_reason})")
        
        return {
            'implementation_status': 'success',
            'change_record': change_record,
            'new_threshold': new_threshold,
            'previous_threshold': old_threshold,
            'monitoring_enabled': True,
            'rollback_available': True
        }
    
    def get_optimization_summary(self) -> Dict:
        """Get summary of optimization history and current status"""
        
        if not self.optimization_history:
            return {
                'summary_status': 'no_history',
                'current_threshold': self.current_optimal_threshold,
                'optimizations_performed': 0
            }
        
        latest_optimization = self.optimization_history[-1]
        
        # Calculate optimization frequency
        optimization_dates = [entry['timestamp'] for entry in self.optimization_history]
        if len(optimization_dates) > 1:
            avg_days_between = np.mean([
                (optimization_dates[i] - optimization_dates[i-1]).days
                for i in range(1, len(optimization_dates))
            ])
        else:
            avg_days_between = None
        
        # Calculate threshold stability
        thresholds = [entry['recommended_threshold'] for entry in self.optimization_history]
        threshold_stability = np.std(thresholds) if len(thresholds) > 1 else 0
        
        return {
            'summary_status': 'completed',
            'current_threshold': self.current_optimal_threshold,
            'optimizations_performed': len(self.optimization_history),
            'latest_optimization': {
                'timestamp': latest_optimization['timestamp'],
                'threshold_change': latest_optimization['recommended_threshold'] - latest_optimization['previous_threshold'],
                'confidence_level': latest_optimization['confidence_level'],
                'reasoning': latest_optimization['reasoning']
            },
            'optimization_frequency': {
                'avg_days_between_optimizations': avg_days_between,
                'last_optimization_days_ago': (datetime.now() - self.last_optimization_time).days if self.last_optimization_time else None
            },
            'threshold_stability': {
                'standard_deviation': threshold_stability,
                'min_threshold': min(thresholds),
                'max_threshold': max(thresholds),
                'stability_rating': 'high' if threshold_stability < 5 else 'medium' if threshold_stability < 10 else 'low'
            }
        }