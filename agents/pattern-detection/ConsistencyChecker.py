"""
Win rate consistency monitoring for detecting unnatural performance patterns
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from decimal import Decimal
import numpy as np
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConsistencyAnalysis:
    """Complete consistency analysis results"""
    win_rate_consistency: float
    profit_factor_consistency: float
    drawdown_consistency: float
    overall_consistency_score: float
    suspicious: bool
    suspicious_patterns: List[str]
    recommendations: List[str]
    variance_metrics: Dict[str, float]


@dataclass
class ConsistencyThresholds:
    """Configuration thresholds for consistency monitoring"""
    # Consistency thresholds (lower = more suspicious)
    max_win_rate_stability: float = 0.05  # Max 5% win rate standard deviation
    max_performance_consistency: float = 0.10  # Max 10% performance consistency
    max_drawdown_consistency: float = 0.08  # Max 8% drawdown consistency
    
    # Window settings
    analysis_window: timedelta = field(default_factory=lambda: timedelta(days=30))
    min_trades_for_analysis: int = 20
    
    # Human variability minimums
    human_win_rate_variance: float = 0.10  # Humans should have at least 10% variance
    human_performance_variance: float = 0.15  # Humans should have 15% performance variance
    
    # Alert thresholds
    suspicious_threshold: float = 0.20  # Overall consistency threshold
    critical_threshold: float = 0.35  # Critical alert threshold


class ConsistencyChecker:
    """Monitors trading consistency for suspicious patterns"""
    
    def __init__(self, thresholds: Optional[ConsistencyThresholds] = None):
        self.thresholds = thresholds or ConsistencyThresholds()
        self.consistency_history: deque = deque(maxlen=1000)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def analyze_consistency(
        self,
        trades: List[Any],
        analysis_window: Optional[timedelta] = None
    ) -> ConsistencyAnalysis:
        """
        Perform complete consistency analysis
        """
        if len(trades) < self.thresholds.min_trades_for_analysis:
            return self._create_insufficient_data_analysis()
        
        window = analysis_window or self.thresholds.analysis_window
        filtered_trades = self._filter_trades_by_window(trades, window)
        
        if len(filtered_trades) < self.thresholds.min_trades_for_analysis:
            return self._create_insufficient_data_analysis()
        
        # Calculate different consistency metrics
        win_rate_consistency = self.calculate_win_rate_consistency(filtered_trades)
        profit_factor_consistency = self.calculate_profit_factor_consistency(filtered_trades)
        drawdown_consistency = self.calculate_drawdown_consistency(filtered_trades)
        
        # Calculate variance metrics
        variance_metrics = self.calculate_variance_metrics(filtered_trades)
        
        # Calculate overall consistency score
        overall_score = self._calculate_overall_consistency(
            win_rate_consistency, profit_factor_consistency, drawdown_consistency
        )
        
        # Detect suspicious patterns
        suspicious_patterns = self._detect_suspicious_patterns(
            win_rate_consistency, profit_factor_consistency, 
            drawdown_consistency, variance_metrics
        )
        
        # Determine if suspicious
        suspicious = overall_score > self.thresholds.suspicious_threshold
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            overall_score, suspicious_patterns, variance_metrics
        )
        
        return ConsistencyAnalysis(
            win_rate_consistency=win_rate_consistency,
            profit_factor_consistency=profit_factor_consistency,
            drawdown_consistency=drawdown_consistency,
            overall_consistency_score=overall_score,
            suspicious=suspicious,
            suspicious_patterns=suspicious_patterns,
            recommendations=recommendations,
            variance_metrics=variance_metrics
        )
    
    def calculate_win_rate_consistency(self, trades: List[Any]) -> float:
        """
        Calculate win rate consistency over time windows
        """
        if len(trades) < 10:
            return 0.0
        
        # Sort trades by timestamp
        trades.sort(key=lambda t: t.timestamp if hasattr(t, 'timestamp') else t.entry_time)
        
        # Calculate win rates in sliding windows
        window_size = max(5, len(trades) // 8)  # Adaptive window size
        win_rates = []
        
        for i in range(len(trades) - window_size + 1):
            window_trades = trades[i:i + window_size]
            wins = sum(1 for t in window_trades if self._is_winning_trade(t))
            win_rate = wins / len(window_trades)
            win_rates.append(win_rate)
        
        if len(win_rates) < 2:
            return 0.0
        
        # Calculate consistency (inverse of coefficient of variation)
        mean_win_rate = np.mean(win_rates)
        std_win_rate = np.std(win_rates)
        
        if mean_win_rate == 0:
            return 1.0  # Perfect consistency (suspicious)
        
        cv = std_win_rate / mean_win_rate
        consistency = max(0, 1 - cv)
        
        return min(1.0, consistency)
    
    def calculate_profit_factor_consistency(self, trades: List[Any]) -> float:
        """
        Calculate profit factor consistency over time windows
        """
        if len(trades) < 10:
            return 0.0
        
        trades.sort(key=lambda t: t.timestamp if hasattr(t, 'timestamp') else t.entry_time)
        
        # Calculate profit factors in sliding windows
        window_size = max(10, len(trades) // 6)
        profit_factors = []
        
        for i in range(len(trades) - window_size + 1):
            window_trades = trades[i:i + window_size]
            gross_profit = sum(max(0, self._calculate_trade_pnl(t)) for t in window_trades)
            gross_loss = abs(sum(min(0, self._calculate_trade_pnl(t)) for t in window_trades))
            
            if gross_loss > 0:
                pf = gross_profit / gross_loss
                profit_factors.append(pf)
        
        if len(profit_factors) < 2:
            return 0.0
        
        # Calculate consistency
        mean_pf = np.mean(profit_factors)
        std_pf = np.std(profit_factors)
        
        if mean_pf == 0:
            return 1.0
        
        cv = std_pf / mean_pf
        consistency = max(0, 1 - cv / 2)  # Scale for profit factor variance
        
        return min(1.0, consistency)
    
    def calculate_drawdown_consistency(self, trades: List[Any]) -> float:
        """
        Calculate drawdown pattern consistency
        """
        if len(trades) < 10:
            return 0.0
        
        # Calculate running P&L
        trades.sort(key=lambda t: t.timestamp if hasattr(t, 'timestamp') else t.entry_time)
        
        cumulative_pnl = []
        running_total = 0.0
        
        for trade in trades:
            pnl = self._calculate_trade_pnl(trade)
            running_total += pnl
            cumulative_pnl.append(running_total)
        
        # Find drawdown periods
        drawdowns = []
        peak = cumulative_pnl[0]
        in_drawdown = False
        drawdown_start_idx = 0
        
        for i, pnl in enumerate(cumulative_pnl):
            if pnl > peak:
                if in_drawdown:
                    # End of drawdown period
                    drawdown_length = i - drawdown_start_idx
                    drawdown_depth = peak - min(cumulative_pnl[drawdown_start_idx:i])
                    if drawdown_depth > 0:
                        drawdowns.append({
                            'length': drawdown_length,
                            'depth': drawdown_depth,
                            'recovery_time': i - drawdown_start_idx
                        })
                    in_drawdown = False
                peak = pnl
            elif pnl < peak and not in_drawdown:
                in_drawdown = True
                drawdown_start_idx = i
        
        if len(drawdowns) < 3:
            return 0.0
        
        # Analyze drawdown consistency
        lengths = [dd['length'] for dd in drawdowns]
        depths = [dd['depth'] for dd in drawdowns]
        
        # Calculate coefficient of variation for lengths and depths
        length_cv = np.std(lengths) / (np.mean(lengths) + 1) if lengths else 0
        depth_cv = np.std(depths) / (np.mean(depths) + 0.0001) if depths else 0
        
        # Lower CV = more consistent = more suspicious
        consistency = (1 - min(1, length_cv)) * 0.5 + (1 - min(1, depth_cv)) * 0.5
        
        return consistency
    
    def calculate_variance_metrics(self, trades: List[Any]) -> Dict[str, float]:
        """
        Calculate various variance metrics
        """
        metrics = {}
        
        # Daily win rate variance
        daily_results = self._group_trades_by_day(trades)
        daily_win_rates = []
        
        for day_trades in daily_results.values():
            if len(day_trades) >= 2:
                wins = sum(1 for t in day_trades if self._is_winning_trade(t))
                win_rate = wins / len(day_trades)
                daily_win_rates.append(win_rate)
        
        if len(daily_win_rates) >= 2:
            metrics['daily_win_rate_variance'] = np.std(daily_win_rates)
        
        # Weekly performance variance
        weekly_results = self._group_trades_by_week(trades)
        weekly_profits = []
        
        for week_trades in weekly_results.values():
            if week_trades:
                week_profit = sum(self._calculate_trade_pnl(t) for t in week_trades)
                weekly_profits.append(week_profit)
        
        if len(weekly_profits) >= 2:
            mean_profit = np.mean(weekly_profits)
            if mean_profit != 0:
                metrics['weekly_performance_variance'] = np.std(weekly_profits) / abs(mean_profit)
            else:
                metrics['weekly_performance_variance'] = np.std(weekly_profits)
        
        # Trade size variance
        sizes = []
        for trade in trades:
            if hasattr(trade, 'size'):
                sizes.append(float(trade.size))
        
        if len(sizes) >= 2:
            metrics['trade_size_variance'] = np.std(sizes) / (np.mean(sizes) + 0.0001)
        
        # Trade duration variance
        durations = []
        for trade in trades:
            if (hasattr(trade, 'entry_time') and hasattr(trade, 'exit_time') 
                and trade.exit_time):
                duration = (trade.exit_time - trade.entry_time).total_seconds() / 60
                durations.append(duration)
        
        if len(durations) >= 2:
            metrics['trade_duration_variance'] = np.std(durations) / (np.mean(durations) + 1)
        
        return metrics
    
    def _is_winning_trade(self, trade: Any) -> bool:
        """
        Determine if a trade was a winner
        """
        pnl = self._calculate_trade_pnl(trade)
        return pnl > 0
    
    def _calculate_trade_pnl(self, trade: Any) -> float:
        """
        Calculate trade P&L
        """
        if hasattr(trade, 'pnl'):
            return float(trade.pnl)
        
        if (hasattr(trade, 'entry_price') and hasattr(trade, 'exit_price') 
            and trade.exit_price):
            entry = float(trade.entry_price)
            exit_price = float(trade.exit_price)
            
            pnl = exit_price - entry
            
            if hasattr(trade, 'direction') and trade.direction == 'short':
                pnl = -pnl
            
            if hasattr(trade, 'size'):
                pnl *= float(trade.size)
            
            return pnl
        
        return 0.0
    
    def _group_trades_by_day(self, trades: List[Any]) -> Dict[str, List[Any]]:
        """
        Group trades by day
        """
        daily_groups = defaultdict(list)
        
        for trade in trades:
            timestamp = trade.timestamp if hasattr(trade, 'timestamp') else trade.entry_time
            day_key = timestamp.strftime('%Y-%m-%d')
            daily_groups[day_key].append(trade)
        
        return dict(daily_groups)
    
    def _group_trades_by_week(self, trades: List[Any]) -> Dict[str, List[Any]]:
        """
        Group trades by week
        """
        weekly_groups = defaultdict(list)
        
        for trade in trades:
            timestamp = trade.timestamp if hasattr(trade, 'timestamp') else trade.entry_time
            # Get Monday of the week
            monday = timestamp - timedelta(days=timestamp.weekday())
            week_key = monday.strftime('%Y-%m-%d')
            weekly_groups[week_key].append(trade)
        
        return dict(weekly_groups)
    
    def _calculate_overall_consistency(
        self, 
        win_rate_consistency: float,
        profit_factor_consistency: float,
        drawdown_consistency: float
    ) -> float:
        """
        Calculate weighted overall consistency score
        """
        weights = {
            'win_rate': 0.4,
            'profit_factor': 0.35,
            'drawdown': 0.25
        }
        
        overall = (
            win_rate_consistency * weights['win_rate'] +
            profit_factor_consistency * weights['profit_factor'] +
            drawdown_consistency * weights['drawdown']
        )
        
        return min(1.0, overall)
    
    def _detect_suspicious_patterns(
        self,
        win_rate_consistency: float,
        profit_factor_consistency: float,
        drawdown_consistency: float,
        variance_metrics: Dict[str, float]
    ) -> List[str]:
        """
        Detect specific suspicious consistency patterns
        """
        patterns = []
        
        # Win rate too consistent
        if win_rate_consistency > (1 - self.thresholds.max_win_rate_stability):
            patterns.append(f"Win rate is too consistent ({win_rate_consistency:.3f})")
        
        # Performance too consistent
        if profit_factor_consistency > (1 - self.thresholds.max_performance_consistency):
            patterns.append(f"Profit factor is too consistent ({profit_factor_consistency:.3f})")
        
        # Drawdown patterns too regular
        if drawdown_consistency > (1 - self.thresholds.max_drawdown_consistency):
            patterns.append(f"Drawdown patterns are too regular ({drawdown_consistency:.3f})")
        
        # Insufficient variance in key metrics
        if variance_metrics.get('daily_win_rate_variance', 1) < self.thresholds.human_win_rate_variance:
            patterns.append("Daily win rate variance is below human levels")
        
        if variance_metrics.get('weekly_performance_variance', 1) < self.thresholds.human_performance_variance:
            patterns.append("Weekly performance variance is below human levels")
        
        # Perfect consistency across multiple metrics
        consistent_metrics = 0
        if win_rate_consistency > 0.8:
            consistent_metrics += 1
        if profit_factor_consistency > 0.8:
            consistent_metrics += 1
        if drawdown_consistency > 0.8:
            consistent_metrics += 1
        
        if consistent_metrics >= 2:
            patterns.append("Multiple metrics show unnatural consistency")
        
        return patterns
    
    def _generate_recommendations(
        self,
        overall_score: float,
        suspicious_patterns: List[str],
        variance_metrics: Dict[str, float]
    ) -> List[str]:
        """
        Generate recommendations to reduce consistency
        """
        recommendations = []
        
        # Overall recommendations
        if overall_score > self.thresholds.critical_threshold:
            recommendations.append("CRITICAL: Trading consistency is unnatural - immediate variance injection needed")
            recommendations.append("Implement all randomization mechanisms across win rate, sizing, and timing")
        elif overall_score > self.thresholds.suspicious_threshold:
            recommendations.append("WARNING: Consistency levels approaching suspicious thresholds")
            recommendations.append("Add variance to performance metrics")
        
        # Pattern-specific recommendations
        if "Win rate is too consistent" in str(suspicious_patterns):
            recommendations.append("Introduce intentional losing trades periodically")
            recommendations.append("Vary exit criteria to create more natural win/loss distribution")
        
        if "Profit factor is too consistent" in str(suspicious_patterns):
            recommendations.append("Vary risk/reward ratios between trades")
            recommendations.append("Implement dynamic exit strategies")
        
        if "Drawdown patterns are too regular" in str(suspicious_patterns):
            recommendations.append("Add randomness to drawdown recovery patterns")
            recommendations.append("Vary position sizing during different market conditions")
        
        # Variance-specific recommendations
        if variance_metrics.get('daily_win_rate_variance', 1) < self.thresholds.human_win_rate_variance:
            recommendations.append("Increase daily win rate variation - aim for human-like inconsistency")
        
        if variance_metrics.get('weekly_performance_variance', 1) < self.thresholds.human_performance_variance:
            recommendations.append("Add weekly performance variation - humans have good and bad weeks")
        
        if variance_metrics.get('trade_size_variance', 1) < 0.2:
            recommendations.append("Increase position size variation")
        
        if variance_metrics.get('trade_duration_variance', 1) < 0.3:
            recommendations.append("Vary trade holding periods more significantly")
        
        return recommendations
    
    def _filter_trades_by_window(
        self, 
        trades: List[Any], 
        window: timedelta
    ) -> List[Any]:
        """
        Filter trades to analysis window
        """
        if not trades:
            return []
        
        cutoff_time = datetime.now() - window
        
        return [
            t for t in trades 
            if (hasattr(t, 'timestamp') and t.timestamp >= cutoff_time) or
               (hasattr(t, 'entry_time') and t.entry_time >= cutoff_time)
        ]
    
    def _create_insufficient_data_analysis(self) -> ConsistencyAnalysis:
        """
        Create analysis result when insufficient data
        """
        return ConsistencyAnalysis(
            win_rate_consistency=0.0,
            profit_factor_consistency=0.0,
            drawdown_consistency=0.0,
            overall_consistency_score=0.0,
            suspicious=False,
            suspicious_patterns=[],
            recommendations=[f"Insufficient data for consistency analysis - need at least {self.thresholds.min_trades_for_analysis} trades"],
            variance_metrics={}
        )