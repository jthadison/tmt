"""
Signal Performance Tracker

Comprehensive performance tracking system for trading signals including
win rate analysis, profit factor calculations, and signal attribution
for continuous algorithm improvement.
"""

from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict
import logging
import json

from .signal_metadata import SignalOutcome

logger = logging.getLogger(__name__)


class SignalPerformanceTracker:
    """
    Tracks and analyzes signal performance with comprehensive metrics.
    
    Features:
    - Signal outcome tracking (win/loss/neutral/cancelled)
    - Performance metrics by pattern type, confidence level, market state
    - Attribution analysis to identify successful factors
    - Real-time performance monitoring
    - Statistical significance testing
    """
    
    def __init__(self,
                 min_samples_for_stats: int = 30,
                 significance_level: float = 0.05,
                 track_real_time: bool = True):
        """
        Initialize performance tracker.
        
        Args:
            min_samples_for_stats: Minimum samples for statistical significance
            significance_level: Statistical significance level for tests
            track_real_time: Enable real-time tracking features
        """
        self.min_samples_for_stats = min_samples_for_stats
        self.significance_level = significance_level
        self.track_real_time = track_real_time
        
        # In-memory storage (would be replaced with database in production)
        self.signal_outcomes = {}  # signal_id -> SignalOutcome
        self.signal_metadata = {}  # signal_id -> signal_data
        self.real_time_tracking = defaultdict(dict)  # signal_id -> real-time data
    
    def track_signal_outcome(self, 
                           signal_id: str,
                           outcome_data: Dict,
                           signal_metadata: Dict = None) -> Dict:
        """
        Track the final outcome of a trading signal.
        
        Args:
            signal_id: Unique signal identifier
            outcome_data: Outcome information
            signal_metadata: Original signal data for attribution
            
        Returns:
            Tracking confirmation with updated metrics
        """
        # Create outcome record
        outcome = SignalOutcome(
            signal_id=signal_id,
            outcome_type=outcome_data.get('type', 'unknown'),
            entry_filled=outcome_data.get('entry_filled', False),
            entry_fill_price=Decimal(str(outcome_data['entry_fill_price'])) if outcome_data.get('entry_fill_price') else None,
            entry_fill_time=outcome_data.get('entry_fill_time'),
            exit_price=Decimal(str(outcome_data['exit_price'])) if outcome_data.get('exit_price') else None,
            exit_time=outcome_data.get('exit_time'),
            pnl_points=outcome_data.get('pnl_points', 0.0),
            pnl_percentage=outcome_data.get('pnl_percentage', 0.0),
            hold_duration_hours=outcome_data.get('hold_duration_hours'),
            target_hit=outcome_data.get('target_hit'),
            max_favorable_excursion=outcome_data.get('max_favorable_excursion', 0.0),
            max_adverse_excursion=outcome_data.get('max_adverse_excursion', 0.0),
            notes=outcome_data.get('notes', '')
        )
        
        # Store outcome and metadata
        self.signal_outcomes[signal_id] = outcome
        if signal_metadata:
            self.signal_metadata[signal_id] = signal_metadata
        
        # Update real-time tracking
        if self.track_real_time and signal_id in self.real_time_tracking:
            del self.real_time_tracking[signal_id]
        
        # Calculate updated performance metrics
        updated_metrics = self._calculate_updated_metrics()
        
        logger.info(f"Tracked outcome for signal {signal_id}: {outcome.outcome_type}")
        
        return {
            'outcome_recorded': True,
            'signal_id': signal_id,
            'outcome_type': outcome.outcome_type,
            'pnl_points': outcome.pnl_points,
            'updated_metrics': updated_metrics,
            'tracking_timestamp': datetime.now()
        }
    
    def update_real_time_tracking(self,
                                signal_id: str,
                                current_price: float,
                                timestamp: datetime = None) -> Dict:
        """
        Update real-time tracking for an active signal.
        
        Args:
            signal_id: Signal identifier
            current_price: Current market price
            timestamp: Update timestamp
            
        Returns:
            Real-time tracking update
        """
        if not self.track_real_time:
            return {'tracking_disabled': True}
        
        if signal_id not in self.signal_metadata:
            return {'error': 'Signal not found'}
        
        signal_data = self.signal_metadata[signal_id]
        timestamp = timestamp or datetime.now()
        
        # Calculate current P&L and excursions
        entry_price = float(signal_data.get('entry_price', 0))
        signal_type = signal_data.get('signal_type', 'long')
        
        if entry_price == 0:
            return {'error': 'No entry price available'}
        
        # Calculate current P&L
        if signal_type == 'long':
            current_pnl = current_price - entry_price
        else:
            current_pnl = entry_price - current_price
        
        # Update tracking data
        if signal_id not in self.real_time_tracking:
            self.real_time_tracking[signal_id] = {
                'start_time': timestamp,
                'entry_price': entry_price,
                'signal_type': signal_type,
                'max_favorable': 0.0,
                'max_adverse': 0.0,
                'price_history': [],
                'pnl_history': []
            }
        
        tracking_data = self.real_time_tracking[signal_id]
        
        # Update excursions
        tracking_data['max_favorable'] = max(tracking_data['max_favorable'], current_pnl)
        tracking_data['max_adverse'] = min(tracking_data['max_adverse'], current_pnl)
        
        # Store price and P&L history
        tracking_data['price_history'].append((timestamp, current_price))
        tracking_data['pnl_history'].append((timestamp, current_pnl))
        
        # Limit history size to prevent memory bloat
        max_history_points = 1000
        if len(tracking_data['price_history']) > max_history_points:
            tracking_data['price_history'] = tracking_data['price_history'][-max_history_points:]
            tracking_data['pnl_history'] = tracking_data['pnl_history'][-max_history_points:]
        
        # Calculate duration
        duration = timestamp - tracking_data['start_time']
        duration_hours = duration.total_seconds() / 3600
        
        return {
            'signal_id': signal_id,
            'current_pnl': round(current_pnl, 4),
            'max_favorable_excursion': round(tracking_data['max_favorable'], 4),
            'max_adverse_excursion': round(tracking_data['max_adverse'], 4),
            'duration_hours': round(duration_hours, 2),
            'last_update': timestamp
        }
    
    def calculate_performance_metrics(self, 
                                   filter_criteria: Dict = None,
                                   time_range_days: int = None) -> Dict:
        """
        Calculate comprehensive performance metrics.
        
        Args:
            filter_criteria: Filters for analysis (pattern_type, confidence_range, etc.)
            time_range_days: Limit analysis to recent N days
            
        Returns:
            Comprehensive performance metrics
        """
        # Get filtered signals
        filtered_signals = self._get_filtered_signals(filter_criteria, time_range_days)
        
        if not filtered_signals:
            return {
                'error': 'No signals match filter criteria',
                'filter_criteria': filter_criteria,
                'total_signals_in_database': len(self.signal_outcomes)
            }
        
        # Basic metrics
        total_signals = len(filtered_signals)
        outcomes = [s['outcome'] for s in filtered_signals if s.get('outcome')]
        
        if not outcomes:
            return {
                'total_signals': total_signals,
                'completed_signals': 0,
                'pending_signals': total_signals
            }
        
        # Win/loss analysis
        wins = [o for o in outcomes if o.outcome_type == 'win']
        losses = [o for o in outcomes if o.outcome_type == 'loss']
        neutrals = [o for o in outcomes if o.outcome_type == 'neutral']
        cancelled = [o for o in outcomes if o.outcome_type == 'cancelled']
        
        completed_signals = len(outcomes)
        win_rate = (len(wins) / completed_signals) * 100 if completed_signals > 0 else 0
        
        # P&L analysis
        gross_profit = sum(w.pnl_points for w in wins)
        gross_loss = abs(sum(l.pnl_points for l in losses))
        net_profit = gross_profit - gross_loss
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Average metrics
        avg_win = gross_profit / len(wins) if wins else 0
        avg_loss = gross_loss / len(losses) if losses else 0
        avg_rr_actual = avg_win / avg_loss if avg_loss > 0 else 0
        
        # Hold time analysis
        completed_with_duration = [o for o in outcomes if o.hold_duration_hours is not None]
        avg_hold_time = np.mean([o.hold_duration_hours for o in completed_with_duration]) if completed_with_duration else 0
        
        # Target hit analysis
        target_analysis = self._analyze_target_hits(outcomes)
        
        # Expectancy calculation
        expectancy = (avg_win * (len(wins) / completed_signals)) - (avg_loss * (len(losses) / completed_signals))
        
        # Maximum drawdown
        drawdown_analysis = self._calculate_drawdown(outcomes)
        
        # Statistical significance
        significance_test = self._test_statistical_significance(outcomes)
        
        return {
            'analysis_period': {
                'total_signals': total_signals,
                'completed_signals': completed_signals,
                'pending_signals': total_signals - completed_signals,
                'filter_criteria': filter_criteria,
                'time_range_days': time_range_days
            },
            'win_loss_metrics': {
                'win_rate_percent': round(win_rate, 2),
                'wins': len(wins),
                'losses': len(losses),
                'neutrals': len(neutrals),
                'cancelled': len(cancelled),
                'profit_factor': round(profit_factor, 2) if profit_factor != float('inf') else 'infinite'
            },
            'pnl_metrics': {
                'gross_profit': round(gross_profit, 2),
                'gross_loss': round(gross_loss, 2),
                'net_profit': round(net_profit, 2),
                'average_win': round(avg_win, 2),
                'average_loss': round(avg_loss, 2),
                'actual_avg_rr': round(avg_rr_actual, 2),
                'expectancy': round(expectancy, 4)
            },
            'timing_metrics': {
                'average_hold_time_hours': round(avg_hold_time, 1),
                'target_analysis': target_analysis
            },
            'risk_metrics': {
                'largest_win': max([w.pnl_points for w in wins]) if wins else 0,
                'largest_loss': min([l.pnl_points for l in losses]) if losses else 0,
                'drawdown_analysis': drawdown_analysis
            },
            'statistical_analysis': significance_test,
            'performance_rating': self._rate_overall_performance(win_rate, profit_factor, expectancy)
        }
    
    def get_pattern_performance_breakdown(self) -> Dict:
        """Get performance breakdown by pattern type"""
        pattern_performance = defaultdict(list)
        
        # Group outcomes by pattern type
        for signal_id, outcome in self.signal_outcomes.items():
            signal_data = self.signal_metadata.get(signal_id, {})
            pattern_type = signal_data.get('pattern_type', 'unknown')
            pattern_performance[pattern_type].append(outcome)
        
        results = {}
        for pattern_type, outcomes in pattern_performance.items():
            if len(outcomes) < 5:  # Skip patterns with too few samples
                continue
            
            wins = [o for o in outcomes if o.outcome_type == 'win']
            losses = [o for o in outcomes if o.outcome_type == 'loss']
            
            win_rate = (len(wins) / len(outcomes)) * 100
            gross_profit = sum(w.pnl_points for w in wins)
            gross_loss = abs(sum(l.pnl_points for l in losses))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            results[pattern_type] = {
                'total_signals': len(outcomes),
                'win_rate': round(win_rate, 2),
                'profit_factor': round(profit_factor, 2) if profit_factor != float('inf') else 'infinite',
                'gross_profit': round(gross_profit, 2),
                'gross_loss': round(gross_loss, 2),
                'best_signal_pnl': max([o.pnl_points for o in outcomes]),
                'worst_signal_pnl': min([o.pnl_points for o in outcomes])
            }
        
        # Rank patterns by performance
        pattern_rankings = sorted(results.items(), 
                                key=lambda x: (x[1]['win_rate'] * x[1]['profit_factor']), 
                                reverse=True)
        
        return {
            'pattern_breakdown': results,
            'pattern_rankings': [{'pattern': p[0], 'score': p[1]} for p in pattern_rankings],
            'best_pattern': pattern_rankings[0][0] if pattern_rankings else None,
            'worst_pattern': pattern_rankings[-1][0] if pattern_rankings else None
        }
    
    def get_confidence_level_analysis(self) -> Dict:
        """Analyze performance by confidence level ranges"""
        confidence_ranges = [
            (75, 80, '75-80%'),
            (80, 85, '80-85%'),
            (85, 90, '85-90%'),
            (90, 95, '90-95%'),
            (95, 100, '95-100%')
        ]
        
        results = {}
        
        for min_conf, max_conf, range_label in confidence_ranges:
            # Find signals in this confidence range
            range_outcomes = []
            for signal_id, outcome in self.signal_outcomes.items():
                signal_data = self.signal_metadata.get(signal_id, {})
                confidence = signal_data.get('confidence', 0)
                if min_conf <= confidence < max_conf:
                    range_outcomes.append(outcome)
            
            if len(range_outcomes) < 5:  # Skip ranges with too few samples
                continue
            
            wins = [o for o in range_outcomes if o.outcome_type == 'win']
            losses = [o for o in range_outcomes if o.outcome_type == 'loss']
            
            win_rate = (len(wins) / len(range_outcomes)) * 100
            avg_pnl = np.mean([o.pnl_points for o in range_outcomes])
            
            results[range_label] = {
                'total_signals': len(range_outcomes),
                'win_rate': round(win_rate, 2),
                'average_pnl': round(avg_pnl, 2),
                'confidence_vs_performance_correlation': round(win_rate - 75, 2)  # Deviation from baseline 75%
            }
        
        return results
    
    def get_market_state_analysis(self) -> Dict:
        """Analyze performance by market state"""
        state_performance = defaultdict(list)
        
        for signal_id, outcome in self.signal_outcomes.items():
            signal_data = self.signal_metadata.get(signal_id, {})
            market_context = signal_data.get('market_context', {})
            market_state = market_context.get('market_state', 'unknown')
            state_performance[market_state].append(outcome)
        
        results = {}
        for state, outcomes in state_performance.items():
            if len(outcomes) < 3:  # Skip states with too few samples
                continue
            
            wins = [o for o in outcomes if o.outcome_type == 'win']
            win_rate = (len(wins) / len(outcomes)) * 100
            avg_pnl = np.mean([o.pnl_points for o in outcomes])
            
            results[state] = {
                'total_signals': len(outcomes),
                'win_rate': round(win_rate, 2),
                'average_pnl': round(avg_pnl, 2)
            }
        
        return results
    
    def get_signal_attribution_analysis(self) -> Dict:
        """
        Analyze which signal factors contribute most to success.
        """
        # Prepare data for attribution analysis
        successful_signals = []
        unsuccessful_signals = []
        
        for signal_id, outcome in self.signal_outcomes.items():
            signal_data = self.signal_metadata.get(signal_id, {})
            
            if outcome.outcome_type == 'win':
                successful_signals.append({
                    'signal_id': signal_id,
                    'outcome': outcome,
                    'signal_data': signal_data
                })
            elif outcome.outcome_type == 'loss':
                unsuccessful_signals.append({
                    'signal_id': signal_id,
                    'outcome': outcome,
                    'signal_data': signal_data
                })
        
        if len(successful_signals) < 10 or len(unsuccessful_signals) < 10:
            return {
                'error': 'Insufficient data for attribution analysis',
                'successful_count': len(successful_signals),
                'unsuccessful_count': len(unsuccessful_signals),
                'minimum_required': 10
            }
        
        # Analyze contributing factors
        attribution_factors = {
            'confidence_level': self._analyze_factor_attribution('confidence', successful_signals, unsuccessful_signals),
            'risk_reward_ratio': self._analyze_factor_attribution('risk_reward_ratio', successful_signals, unsuccessful_signals),
            'pattern_type': self._analyze_categorical_factor('pattern_type', successful_signals, unsuccessful_signals),
            'market_state': self._analyze_market_context_factor('market_state', successful_signals, unsuccessful_signals),
            'volatility_regime': self._analyze_market_context_factor('volatility_regime', successful_signals, unsuccessful_signals),
            'trading_session': self._analyze_market_context_factor('session', successful_signals, unsuccessful_signals)
        }
        
        # Generate insights
        insights = self._generate_attribution_insights(attribution_factors)
        
        return {
            'attribution_factors': attribution_factors,
            'key_insights': insights,
            'sample_sizes': {
                'successful_signals': len(successful_signals),
                'unsuccessful_signals': len(unsuccessful_signals)
            }
        }
    
    def _get_filtered_signals(self, filter_criteria: Dict, time_range_days: int) -> List[Dict]:
        """Get signals matching filter criteria"""
        signals = []
        
        # Time range filter
        if time_range_days:
            cutoff_date = datetime.now() - timedelta(days=time_range_days)
        else:
            cutoff_date = None
        
        for signal_id, outcome in self.signal_outcomes.items():
            signal_data = self.signal_metadata.get(signal_id, {})
            
            # Time filter
            if cutoff_date and outcome.created_at < cutoff_date:
                continue
            
            # Apply other filters
            if filter_criteria:
                if 'pattern_type' in filter_criteria:
                    if signal_data.get('pattern_type') != filter_criteria['pattern_type']:
                        continue
                
                if 'confidence_range' in filter_criteria:
                    conf_range = filter_criteria['confidence_range']
                    confidence = signal_data.get('confidence', 0)
                    if not (conf_range[0] <= confidence <= conf_range[1]):
                        continue
                
                if 'market_state' in filter_criteria:
                    market_context = signal_data.get('market_context', {})
                    if market_context.get('market_state') != filter_criteria['market_state']:
                        continue
            
            signals.append({
                'signal_id': signal_id,
                'signal_data': signal_data,
                'outcome': outcome
            })
        
        return signals
    
    def _analyze_target_hits(self, outcomes: List[SignalOutcome]) -> Dict:
        """Analyze which targets are typically hit"""
        target_hits = defaultdict(int)
        total_with_targets = 0
        
        for outcome in outcomes:
            if outcome.target_hit and outcome.outcome_type == 'win':
                target_hits[outcome.target_hit] += 1
                total_with_targets += 1
        
        if total_with_targets == 0:
            return {'no_target_data': True}
        
        target_percentages = {
            target: (count / total_with_targets) * 100 
            for target, count in target_hits.items()
        }
        
        return {
            'target_hit_distribution': dict(target_hits),
            'target_hit_percentages': target_percentages,
            'total_wins_with_target_data': total_with_targets
        }
    
    def _calculate_drawdown(self, outcomes: List[SignalOutcome]) -> Dict:
        """Calculate maximum drawdown"""
        if not outcomes:
            return {'no_data': True}
        
        # Sort outcomes by completion time
        sorted_outcomes = sorted(outcomes, key=lambda x: x.created_at)
        
        # Calculate running P&L
        running_pnl = 0
        running_peak = 0
        max_drawdown = 0
        max_drawdown_duration = 0
        current_drawdown_start = None
        
        pnl_curve = []
        
        for outcome in sorted_outcomes:
            running_pnl += outcome.pnl_points
            
            if running_pnl > running_peak:
                running_peak = running_pnl
                current_drawdown_start = None
            else:
                # In drawdown
                current_drawdown = running_peak - running_pnl
                if current_drawdown > max_drawdown:
                    max_drawdown = current_drawdown
                
                if current_drawdown_start is None:
                    current_drawdown_start = outcome.created_at
                else:
                    duration = outcome.created_at - current_drawdown_start
                    max_drawdown_duration = max(max_drawdown_duration, duration.days)
            
            pnl_curve.append({
                'timestamp': outcome.created_at,
                'running_pnl': running_pnl,
                'running_peak': running_peak,
                'drawdown': running_peak - running_pnl
            })
        
        return {
            'max_drawdown_points': round(max_drawdown, 2),
            'max_drawdown_duration_days': max_drawdown_duration,
            'final_pnl': round(running_pnl, 2),
            'profit_curve_length': len(pnl_curve)
        }
    
    def _test_statistical_significance(self, outcomes: List[SignalOutcome]) -> Dict:
        """Test statistical significance of results"""
        if len(outcomes) < self.min_samples_for_stats:
            return {
                'insufficient_data': True,
                'current_samples': len(outcomes),
                'required_samples': self.min_samples_for_stats
            }
        
        wins = [o for o in outcomes if o.outcome_type == 'win']
        total = len(outcomes)
        win_rate = len(wins) / total
        
        # Binomial test against 50% (random chance)
        from scipy.stats import binom_test
        
        p_value = binom_test(len(wins), total, 0.5, alternative='greater')
        is_significant = p_value < self.significance_level
        
        # Confidence interval for win rate
        from scipy.stats import beta
        alpha = self.significance_level
        lower_ci = beta.ppf(alpha/2, len(wins), total - len(wins))
        upper_ci = beta.ppf(1 - alpha/2, len(wins) + 1, total - len(wins))
        
        return {
            'statistically_significant': is_significant,
            'p_value': round(p_value, 4),
            'significance_level': self.significance_level,
            'win_rate': round(win_rate * 100, 2),
            'confidence_interval_95': [round(lower_ci * 100, 2), round(upper_ci * 100, 2)],
            'sample_size': total
        }
    
    def _rate_overall_performance(self, win_rate: float, profit_factor: float, expectancy: float) -> str:
        """Rate overall performance quality"""
        # Composite score calculation
        score = 0
        
        # Win rate component (0-40 points)
        if win_rate >= 70:
            score += 40
        elif win_rate >= 60:
            score += 30
        elif win_rate >= 50:
            score += 20
        elif win_rate >= 40:
            score += 10
        
        # Profit factor component (0-40 points)
        if profit_factor == float('inf') or profit_factor >= 3.0:
            score += 40
        elif profit_factor >= 2.0:
            score += 30
        elif profit_factor >= 1.5:
            score += 20
        elif profit_factor >= 1.0:
            score += 10
        
        # Expectancy component (0-20 points)
        if expectancy > 0.5:
            score += 20
        elif expectancy > 0.2:
            score += 15
        elif expectancy > 0:
            score += 10
        elif expectancy > -0.1:
            score += 5
        
        # Rating based on score
        if score >= 80:
            return 'excellent'
        elif score >= 60:
            return 'good'
        elif score >= 40:
            return 'average'
        elif score >= 20:
            return 'poor'
        else:
            return 'very_poor'
    
    def _analyze_factor_attribution(self, factor_name: str, successful: List[Dict], unsuccessful: List[Dict]) -> Dict:
        """Analyze numerical factor attribution"""
        successful_values = [s['signal_data'].get(factor_name, 0) for s in successful]
        unsuccessful_values = [u['signal_data'].get(factor_name, 0) for u in unsuccessful]
        
        successful_avg = np.mean(successful_values) if successful_values else 0
        unsuccessful_avg = np.mean(unsuccessful_values) if unsuccessful_values else 0
        
        return {
            'successful_average': round(successful_avg, 2),
            'unsuccessful_average': round(unsuccessful_avg, 2),
            'difference': round(successful_avg - unsuccessful_avg, 2),
            'attribution_strength': 'high' if abs(successful_avg - unsuccessful_avg) > np.std(successful_values + unsuccessful_values) else 'low'
        }
    
    def _analyze_categorical_factor(self, factor_name: str, successful: List[Dict], unsuccessful: List[Dict]) -> Dict:
        """Analyze categorical factor attribution"""
        successful_counts = defaultdict(int)
        unsuccessful_counts = defaultdict(int)
        
        for s in successful:
            value = s['signal_data'].get(factor_name, 'unknown')
            successful_counts[value] += 1
        
        for u in unsuccessful:
            value = u['signal_data'].get(factor_name, 'unknown')
            unsuccessful_counts[value] += 1
        
        # Calculate success rates by category
        success_rates = {}
        for category in set(list(successful_counts.keys()) + list(unsuccessful_counts.keys())):
            total = successful_counts[category] + unsuccessful_counts[category]
            if total > 0:
                success_rates[category] = (successful_counts[category] / total) * 100
        
        return {
            'success_rates_by_category': success_rates,
            'best_category': max(success_rates.items(), key=lambda x: x[1]) if success_rates else None,
            'worst_category': min(success_rates.items(), key=lambda x: x[1]) if success_rates else None
        }
    
    def _analyze_market_context_factor(self, factor_name: str, successful: List[Dict], unsuccessful: List[Dict]) -> Dict:
        """Analyze market context factor attribution"""
        successful_values = []
        unsuccessful_values = []
        
        for s in successful:
            market_context = s['signal_data'].get('market_context', {})
            value = market_context.get(factor_name, 'unknown')
            successful_values.append(value)
        
        for u in unsuccessful:
            market_context = u['signal_data'].get('market_context', {})
            value = market_context.get(factor_name, 'unknown')
            unsuccessful_values.append(value)
        
        return self._analyze_categorical_values(successful_values, unsuccessful_values)
    
    def _analyze_categorical_values(self, successful_values: List, unsuccessful_values: List) -> Dict:
        """Helper to analyze categorical value lists"""
        successful_counts = defaultdict(int)
        unsuccessful_counts = defaultdict(int)
        
        for value in successful_values:
            successful_counts[value] += 1
        
        for value in unsuccessful_values:
            unsuccessful_counts[value] += 1
        
        success_rates = {}
        for category in set(successful_values + unsuccessful_values):
            total = successful_counts[category] + unsuccessful_counts[category]
            if total > 0:
                success_rates[category] = (successful_counts[category] / total) * 100
        
        return {
            'success_rates_by_value': success_rates,
            'best_value': max(success_rates.items(), key=lambda x: x[1]) if success_rates else None,
            'worst_value': min(success_rates.items(), key=lambda x: x[1]) if success_rates else None
        }
    
    def _generate_attribution_insights(self, attribution_factors: Dict) -> List[str]:
        """Generate actionable insights from attribution analysis"""
        insights = []
        
        # Confidence level insights
        conf_data = attribution_factors.get('confidence_level', {})
        if conf_data.get('difference', 0) > 5:
            insights.append(f"Higher confidence signals show {conf_data['difference']:.1f}% better performance on average")
        
        # Risk-reward insights
        rr_data = attribution_factors.get('risk_reward_ratio', {})
        if rr_data.get('difference', 0) > 0.5:
            insights.append(f"Signals with higher R:R ratios perform {rr_data['difference']:.1f} points better")
        
        # Pattern type insights
        pattern_data = attribution_factors.get('pattern_type', {})
        if pattern_data.get('best_category'):
            best_pattern, best_rate = pattern_data['best_category']
            insights.append(f"'{best_pattern}' patterns show highest success rate at {best_rate:.1f}%")
        
        # Market state insights
        market_data = attribution_factors.get('market_state', {})
        if market_data.get('best_value'):
            best_state, best_rate = market_data['best_value']
            insights.append(f"Signals perform best in '{best_state}' market conditions ({best_rate:.1f}% success rate)")
        
        return insights
    
    def _calculate_updated_metrics(self) -> Dict:
        """Calculate updated key metrics after new outcome"""
        recent_outcomes = [
            outcome for outcome in self.signal_outcomes.values()
            if outcome.created_at >= datetime.now() - timedelta(days=30)
        ]
        
        if not recent_outcomes:
            return {'no_recent_data': True}
        
        wins = [o for o in recent_outcomes if o.outcome_type == 'win']
        win_rate = (len(wins) / len(recent_outcomes)) * 100
        
        return {
            'recent_30_days': {
                'total_signals': len(recent_outcomes),
                'win_rate': round(win_rate, 2),
                'last_updated': datetime.now()
            }
        }