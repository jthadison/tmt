"""
Cross-account correlation tracking system for detecting coordinated behavior
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from decimal import Decimal
import numpy as np
from collections import defaultdict, deque
import logging
from scipy.stats import pearsonr, spearmanr
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class CorrelationPair:
    """Represents correlation data between two accounts"""
    account_1: str
    account_2: str
    correlation: float
    p_value: float
    sample_size: int
    window_start: datetime
    window_end: datetime
    correlation_type: str  # 'entry_timing', 'position_size', 'pnl', 'duration'


@dataclass
class CorrelationDataPoint:
    """Single correlation measurement over time"""
    timestamp: datetime
    account_1: str
    account_2: str
    correlation: float
    correlation_type: str
    significance: float  # p-value
    sample_size: int


@dataclass
class CorrelationTrend:
    """Trend analysis of correlation over time"""
    account_pair: Tuple[str, str]
    correlation_type: str
    trend_direction: str  # 'increasing', 'decreasing', 'stable'
    trend_strength: float  # 0-1
    current_correlation: float
    average_correlation: float
    max_correlation: float
    data_points: int
    analysis_period: timedelta


@dataclass
class CorrelationAlert:
    """Alert for suspicious correlation patterns"""
    alert_id: str
    alert_type: str  # 'threshold_exceeded', 'increasing_trend', 'synchronized_behavior'
    severity: str  # 'warning', 'critical', 'emergency'
    account_pair: Tuple[str, str]
    correlation_value: float
    threshold_exceeded: float
    description: str
    recommended_actions: List[str]
    detected_at: datetime
    acknowledged: bool = False


@dataclass
class CorrelationAnalysis:
    """Complete correlation analysis results"""
    account_pairs: List[CorrelationPair]
    correlation_history: List[CorrelationDataPoint]
    trends: List[CorrelationTrend]
    active_alerts: List[CorrelationAlert]
    risk_score: float
    suspicious_pairs: List[Tuple[str, str]]
    recommendations: List[str]


@dataclass
class CorrelationThresholds:
    """Configuration thresholds for correlation monitoring"""
    # Correlation thresholds
    warning_threshold: float = 0.60
    critical_threshold: float = 0.70
    emergency_threshold: float = 0.80
    
    # Rolling window settings
    correlation_window: timedelta = field(default_factory=lambda: timedelta(hours=24))
    min_trades_for_correlation: int = 5
    
    # Trend detection
    trend_analysis_period: timedelta = field(default_factory=lambda: timedelta(days=7))
    significant_trend_threshold: float = 0.1  # Change in correlation to be significant
    
    # Alert settings
    max_allowed_pairs_above_warning: int = 2
    consecutive_alerts_for_escalation: int = 3
    
    # Statistical significance
    max_p_value: float = 0.05  # For statistical significance


class CorrelationTracker:
    """Tracks correlations between trading accounts to detect coordination"""
    
    def __init__(self, thresholds: Optional[CorrelationThresholds] = None):
        self.thresholds = thresholds or CorrelationThresholds()
        self.correlation_history: deque = deque(maxlen=10000)
        self.active_alerts: List[CorrelationAlert] = []
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def analyze_correlations(
        self, 
        account_trades: Dict[str, List[Any]], 
        analysis_window: Optional[timedelta] = None
    ) -> CorrelationAnalysis:
        """
        Perform complete correlation analysis across all account pairs
        """
        if len(account_trades) < 2:
            return self._create_insufficient_accounts_analysis()
        
        window = analysis_window or self.thresholds.correlation_window
        
        # Filter trades by window
        filtered_trades = self._filter_trades_by_window(account_trades, window)
        
        # Calculate correlations for all pairs
        account_pairs = self._calculate_all_correlations(filtered_trades, window)
        
        # Analyze trends
        trends = self._analyze_correlation_trends()
        
        # Generate alerts
        alerts = self._generate_correlation_alerts(account_pairs, trends)
        
        # Calculate overall risk score
        risk_score = self._calculate_correlation_risk(account_pairs, trends)
        
        # Identify suspicious pairs
        suspicious_pairs = self._identify_suspicious_pairs(account_pairs, alerts)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            account_pairs, trends, alerts, risk_score
        )
        
        # Update history and alerts
        self._update_correlation_history(account_pairs)
        self.active_alerts.extend(alerts)
        
        return CorrelationAnalysis(
            account_pairs=account_pairs,
            correlation_history=list(self.correlation_history),
            trends=trends,
            active_alerts=alerts,
            risk_score=risk_score,
            suspicious_pairs=suspicious_pairs,
            recommendations=recommendations
        )
    
    def _calculate_all_correlations(
        self, 
        account_trades: Dict[str, List[Any]], 
        window: timedelta
    ) -> List[CorrelationPair]:
        """
        Calculate correlations between all account pairs
        """
        pairs = []
        accounts = list(account_trades.keys())
        
        for i in range(len(accounts)):
            for j in range(i + 1, len(accounts)):
                acc1, acc2 = accounts[i], accounts[j]
                trades1, trades2 = account_trades[acc1], account_trades[acc2]
                
                if (len(trades1) < self.thresholds.min_trades_for_correlation or 
                    len(trades2) < self.thresholds.min_trades_for_correlation):
                    continue
                
                # Calculate different types of correlations
                pair_correlations = self._calculate_pair_correlations(
                    acc1, acc2, trades1, trades2, window
                )
                pairs.extend(pair_correlations)
        
        return pairs
    
    def _calculate_pair_correlations(
        self,
        account_1: str,
        account_2: str,
        trades_1: List[Any],
        trades_2: List[Any],
        window: timedelta
    ) -> List[CorrelationPair]:
        """
        Calculate various correlations between two accounts
        """
        correlations = []
        window_start = datetime.now() - window
        window_end = datetime.now()
        
        # Entry timing correlation
        timing_corr = self._calculate_entry_timing_correlation(trades_1, trades_2)
        if timing_corr is not None:
            correlations.append(CorrelationPair(
                account_1=account_1,
                account_2=account_2,
                correlation=timing_corr[0],
                p_value=timing_corr[1],
                sample_size=min(len(trades_1), len(trades_2)),
                window_start=window_start,
                window_end=window_end,
                correlation_type='entry_timing'
            ))
        
        # Position size correlation
        size_corr = self._calculate_position_size_correlation(trades_1, trades_2)
        if size_corr is not None:
            correlations.append(CorrelationPair(
                account_1=account_1,
                account_2=account_2,
                correlation=size_corr[0],
                p_value=size_corr[1],
                sample_size=min(len(trades_1), len(trades_2)),
                window_start=window_start,
                window_end=window_end,
                correlation_type='position_size'
            ))
        
        # P&L correlation
        pnl_corr = self._calculate_pnl_correlation(trades_1, trades_2)
        if pnl_corr is not None:
            correlations.append(CorrelationPair(
                account_1=account_1,
                account_2=account_2,
                correlation=pnl_corr[0],
                p_value=pnl_corr[1],
                sample_size=min(len(trades_1), len(trades_2)),
                window_start=window_start,
                window_end=window_end,
                correlation_type='pnl'
            ))
        
        # Trade duration correlation
        duration_corr = self._calculate_duration_correlation(trades_1, trades_2)
        if duration_corr is not None:
            correlations.append(CorrelationPair(
                account_1=account_1,
                account_2=account_2,
                correlation=duration_corr[0],
                p_value=duration_corr[1],
                sample_size=min(len(trades_1), len(trades_2)),
                window_start=window_start,
                window_end=window_end,
                correlation_type='duration'
            ))
        
        return correlations
    
    def _calculate_entry_timing_correlation(
        self, 
        trades_1: List[Any], 
        trades_2: List[Any]
    ) -> Optional[Tuple[float, float]]:
        """
        Calculate correlation in entry timing patterns
        """
        # Create time series of trade entries
        series_1 = self._create_time_series(trades_1, 'entry_time', timedelta(hours=1))
        series_2 = self._create_time_series(trades_2, 'entry_time', timedelta(hours=1))
        
        # Find common time periods
        common_times = set(series_1.keys()) & set(series_2.keys())
        
        if len(common_times) < 5:
            return None
        
        values_1 = [series_1[t] for t in sorted(common_times)]
        values_2 = [series_2[t] for t in sorted(common_times)]
        
        try:
            corr, p_value = pearsonr(values_1, values_2)
            return (corr, p_value) if not np.isnan(corr) else None
        except:
            return None
    
    def _calculate_position_size_correlation(
        self,
        trades_1: List[Any],
        trades_2: List[Any]
    ) -> Optional[Tuple[float, float]]:
        """
        Calculate correlation in position sizes
        """
        # Extract sizes with timestamps
        sizes_1 = [(t.timestamp, float(t.size)) for t in trades_1 if hasattr(t, 'size')]
        sizes_2 = [(t.timestamp, float(t.size)) for t in trades_2 if hasattr(t, 'size')]
        
        if len(sizes_1) < 5 or len(sizes_2) < 5:
            return None
        
        # Align sizes by time windows
        aligned_sizes = self._align_trade_data(sizes_1, sizes_2, timedelta(hours=1))
        
        if len(aligned_sizes) < 5:
            return None
        
        values_1, values_2 = zip(*aligned_sizes)
        
        try:
            corr, p_value = pearsonr(values_1, values_2)
            return (corr, p_value) if not np.isnan(corr) else None
        except:
            return None
    
    def _calculate_pnl_correlation(
        self,
        trades_1: List[Any],
        trades_2: List[Any]
    ) -> Optional[Tuple[float, float]]:
        """
        Calculate correlation in P&L results
        """
        pnl_1 = []
        pnl_2 = []
        
        # Calculate P&L for each trade
        for trade in trades_1:
            if hasattr(trade, 'entry_price') and hasattr(trade, 'exit_price') and trade.exit_price:
                pnl = float(trade.exit_price) - float(trade.entry_price)
                if hasattr(trade, 'direction') and trade.direction == 'short':
                    pnl = -pnl
                pnl_1.append((trade.timestamp, pnl))
        
        for trade in trades_2:
            if hasattr(trade, 'entry_price') and hasattr(trade, 'exit_price') and trade.exit_price:
                pnl = float(trade.exit_price) - float(trade.entry_price)
                if hasattr(trade, 'direction') and trade.direction == 'short':
                    pnl = -pnl
                pnl_2.append((trade.timestamp, pnl))
        
        if len(pnl_1) < 5 or len(pnl_2) < 5:
            return None
        
        # Align P&L by time windows
        aligned_pnl = self._align_trade_data(pnl_1, pnl_2, timedelta(hours=4))
        
        if len(aligned_pnl) < 5:
            return None
        
        values_1, values_2 = zip(*aligned_pnl)
        
        try:
            corr, p_value = pearsonr(values_1, values_2)
            return (corr, p_value) if not np.isnan(corr) else None
        except:
            return None
    
    def _calculate_duration_correlation(
        self,
        trades_1: List[Any],
        trades_2: List[Any]
    ) -> Optional[Tuple[float, float]]:
        """
        Calculate correlation in trade durations
        """
        durations_1 = []
        durations_2 = []
        
        # Calculate durations
        for trade in trades_1:
            if (hasattr(trade, 'entry_time') and hasattr(trade, 'exit_time') and 
                trade.exit_time):
                duration = (trade.exit_time - trade.entry_time).total_seconds() / 60
                durations_1.append((trade.entry_time, duration))
        
        for trade in trades_2:
            if (hasattr(trade, 'entry_time') and hasattr(trade, 'exit_time') and 
                trade.exit_time):
                duration = (trade.exit_time - trade.entry_time).total_seconds() / 60
                durations_2.append((trade.entry_time, duration))
        
        if len(durations_1) < 5 or len(durations_2) < 5:
            return None
        
        # Align durations by time windows
        aligned_durations = self._align_trade_data(durations_1, durations_2, timedelta(hours=2))
        
        if len(aligned_durations) < 5:
            return None
        
        values_1, values_2 = zip(*aligned_durations)
        
        try:
            corr, p_value = pearsonr(values_1, values_2)
            return (corr, p_value) if not np.isnan(corr) else None
        except:
            return None
    
    def _create_time_series(
        self,
        trades: List[Any],
        time_field: str,
        bucket_size: timedelta
    ) -> Dict[datetime, int]:
        """
        Create time series of trade counts in buckets
        """
        series = defaultdict(int)
        
        for trade in trades:
            if hasattr(trade, time_field):
                time_value = getattr(trade, time_field)
                bucket = self._round_to_bucket(time_value, bucket_size)
                series[bucket] += 1
        
        return dict(series)
    
    def _align_trade_data(
        self,
        data_1: List[Tuple[datetime, float]],
        data_2: List[Tuple[datetime, float]],
        window: timedelta
    ) -> List[Tuple[float, float]]:
        """
        Align two datasets by time windows
        """
        aligned = []
        
        # Sort data by time
        data_1.sort()
        data_2.sort()
        
        # Create windows and average values within each window
        if not data_1 or not data_2:
            return aligned
        
        start_time = min(data_1[0][0], data_2[0][0])
        end_time = max(data_1[-1][0], data_2[-1][0])
        
        current_time = start_time
        while current_time < end_time:
            window_end = current_time + window
            
            # Find values in this window
            values_1 = [v for t, v in data_1 if current_time <= t < window_end]
            values_2 = [v for t, v in data_2 if current_time <= t < window_end]
            
            if values_1 and values_2:
                avg_1 = np.mean(values_1)
                avg_2 = np.mean(values_2)
                aligned.append((avg_1, avg_2))
            
            current_time = window_end
        
        return aligned
    
    def _round_to_bucket(self, timestamp: datetime, bucket_size: timedelta) -> datetime:
        """Round timestamp to bucket boundary"""
        bucket_seconds = bucket_size.total_seconds()
        epoch = datetime(1970, 1, 1)
        seconds_since_epoch = (timestamp - epoch).total_seconds()
        rounded_seconds = (seconds_since_epoch // bucket_seconds) * bucket_seconds
        return epoch + timedelta(seconds=rounded_seconds)
    
    def _analyze_correlation_trends(self) -> List[CorrelationTrend]:
        """
        Analyze trends in correlation over time
        """
        trends = []
        
        if len(self.correlation_history) < 10:
            return trends
        
        # Group history by account pair and correlation type
        grouped_data = defaultdict(list)
        
        for data_point in self.correlation_history:
            key = (data_point.account_1, data_point.account_2, data_point.correlation_type)
            grouped_data[key].append(data_point)
        
        # Analyze trend for each group
        for (acc1, acc2, corr_type), data_points in grouped_data.items():
            if len(data_points) < 5:
                continue
            
            # Sort by timestamp
            data_points.sort(key=lambda x: x.timestamp)
            
            # Calculate trend
            correlations = [dp.correlation for dp in data_points]
            x_values = range(len(correlations))
            
            # Linear regression for trend
            if len(correlations) >= 3:
                trend_coeff = np.polyfit(x_values, correlations, 1)[0]
                
                trend_direction = 'stable'
                trend_strength = abs(trend_coeff)
                
                if trend_coeff > self.thresholds.significant_trend_threshold:
                    trend_direction = 'increasing'
                elif trend_coeff < -self.thresholds.significant_trend_threshold:
                    trend_direction = 'decreasing'
                
                trends.append(CorrelationTrend(
                    account_pair=(acc1, acc2),
                    correlation_type=corr_type,
                    trend_direction=trend_direction,
                    trend_strength=trend_strength,
                    current_correlation=correlations[-1],
                    average_correlation=np.mean(correlations),
                    max_correlation=max(correlations),
                    data_points=len(data_points),
                    analysis_period=data_points[-1].timestamp - data_points[0].timestamp
                ))
        
        return trends
    
    def _generate_correlation_alerts(
        self,
        account_pairs: List[CorrelationPair],
        trends: List[CorrelationTrend]
    ) -> List[CorrelationAlert]:
        """
        Generate alerts for suspicious correlation patterns
        """
        alerts = []
        alert_id_counter = len(self.active_alerts)
        
        # Threshold-based alerts
        for pair in account_pairs:
            alert_id_counter += 1
            
            if (pair.correlation >= self.thresholds.emergency_threshold and 
                pair.p_value <= self.thresholds.max_p_value):
                alerts.append(CorrelationAlert(
                    alert_id=f"CORR_{alert_id_counter}",
                    alert_type='threshold_exceeded',
                    severity='emergency',
                    account_pair=(pair.account_1, pair.account_2),
                    correlation_value=pair.correlation,
                    threshold_exceeded=self.thresholds.emergency_threshold,
                    description=f"EMERGENCY: Extremely high correlation ({pair.correlation:.3f}) in {pair.correlation_type} between accounts",
                    recommended_actions=[
                        "Immediately desynchronize accounts",
                        "Add significant random delays",
                        "Review trading parameters for these accounts",
                        "Consider pausing one account temporarily"
                    ],
                    detected_at=datetime.now()
                ))
            
            elif (pair.correlation >= self.thresholds.critical_threshold and 
                  pair.p_value <= self.thresholds.max_p_value):
                alerts.append(CorrelationAlert(
                    alert_id=f"CORR_{alert_id_counter}",
                    alert_type='threshold_exceeded',
                    severity='critical',
                    account_pair=(pair.account_1, pair.account_2),
                    correlation_value=pair.correlation,
                    threshold_exceeded=self.thresholds.critical_threshold,
                    description=f"Critical correlation level ({pair.correlation:.3f}) detected in {pair.correlation_type}",
                    recommended_actions=[
                        "Increase variance in trading parameters",
                        "Add random delays between accounts",
                        "Adjust position sizing patterns"
                    ],
                    detected_at=datetime.now()
                ))
            
            elif (pair.correlation >= self.thresholds.warning_threshold and 
                  pair.p_value <= self.thresholds.max_p_value):
                alerts.append(CorrelationAlert(
                    alert_id=f"CORR_{alert_id_counter}",
                    alert_type='threshold_exceeded',
                    severity='warning',
                    account_pair=(pair.account_1, pair.account_2),
                    correlation_value=pair.correlation,
                    threshold_exceeded=self.thresholds.warning_threshold,
                    description=f"Elevated correlation ({pair.correlation:.3f}) in {pair.correlation_type}",
                    recommended_actions=[
                        "Monitor closely for further increases",
                        "Consider adding minor variance adjustments"
                    ],
                    detected_at=datetime.now()
                ))
        
        # Trend-based alerts
        for trend in trends:
            if (trend.trend_direction == 'increasing' and 
                trend.current_correlation > self.thresholds.warning_threshold):
                alert_id_counter += 1
                alerts.append(CorrelationAlert(
                    alert_id=f"TREND_{alert_id_counter}",
                    alert_type='increasing_trend',
                    severity='critical' if trend.current_correlation > self.thresholds.critical_threshold else 'warning',
                    account_pair=trend.account_pair,
                    correlation_value=trend.current_correlation,
                    threshold_exceeded=self.thresholds.warning_threshold,
                    description=f"Increasing correlation trend in {trend.correlation_type} (current: {trend.current_correlation:.3f})",
                    recommended_actions=[
                        "Investigate cause of increasing correlation",
                        "Implement immediate variance injection",
                        "Review shared parameters or signals"
                    ],
                    detected_at=datetime.now()
                ))
        
        return alerts
    
    def _calculate_correlation_risk(
        self,
        account_pairs: List[CorrelationPair],
        trends: List[CorrelationTrend]
    ) -> float:
        """
        Calculate overall correlation risk score (0-1)
        """
        if not account_pairs:
            return 0.0
        
        risk_components = []
        
        # Direct correlation risk
        high_correlations = [
            p.correlation for p in account_pairs 
            if p.correlation >= self.thresholds.warning_threshold and p.p_value <= self.thresholds.max_p_value
        ]
        
        if high_correlations:
            max_correlation = max(high_correlations)
            correlation_risk = min(1.0, max_correlation / self.thresholds.emergency_threshold)
            risk_components.append(correlation_risk * 0.6)  # 60% weight
        
        # Number of problematic pairs
        problematic_pairs = len([
            p for p in account_pairs 
            if p.correlation >= self.thresholds.warning_threshold and p.p_value <= self.thresholds.max_p_value
        ])
        
        if problematic_pairs > 0:
            pair_risk = min(1.0, problematic_pairs / self.thresholds.max_allowed_pairs_above_warning)
            risk_components.append(pair_risk * 0.25)  # 25% weight
        
        # Trend risk
        increasing_trends = [
            t for t in trends 
            if t.trend_direction == 'increasing' and t.current_correlation > self.thresholds.warning_threshold
        ]
        
        if increasing_trends:
            trend_risk = min(1.0, len(increasing_trends) / 3)
            risk_components.append(trend_risk * 0.15)  # 15% weight
        
        return sum(risk_components) if risk_components else 0.0
    
    def _identify_suspicious_pairs(
        self,
        account_pairs: List[CorrelationPair],
        alerts: List[CorrelationAlert]
    ) -> List[Tuple[str, str]]:
        """
        Identify account pairs with suspicious correlation patterns
        """
        suspicious_pairs = set()
        
        # From high correlations
        for pair in account_pairs:
            if (pair.correlation >= self.thresholds.critical_threshold and 
                pair.p_value <= self.thresholds.max_p_value):
                suspicious_pairs.add((pair.account_1, pair.account_2))
        
        # From alerts
        for alert in alerts:
            if alert.severity in ['critical', 'emergency']:
                suspicious_pairs.add(alert.account_pair)
        
        return list(suspicious_pairs)
    
    def _generate_recommendations(
        self,
        account_pairs: List[CorrelationPair],
        trends: List[CorrelationTrend],
        alerts: List[CorrelationAlert],
        risk_score: float
    ) -> List[str]:
        """
        Generate specific recommendations to reduce correlation
        """
        recommendations = []
        
        # Overall risk recommendations
        if risk_score > 0.8:
            recommendations.append("CRITICAL: Immediate action required to reduce account correlation")
            recommendations.append("Implement emergency desynchronization procedures")
        elif risk_score > 0.6:
            recommendations.append("HIGH RISK: Significant correlation detected - adjust parameters within 24h")
        elif risk_score > 0.4:
            recommendations.append("MEDIUM RISK: Monitor correlations and prepare adjustments")
        
        # Specific correlation type recommendations
        correlation_types = set()
        for pair in account_pairs:
            if pair.correlation >= self.thresholds.warning_threshold:
                correlation_types.add(pair.correlation_type)
        
        if 'entry_timing' in correlation_types:
            recommendations.append("Add random delays (30-180 seconds) between account entry signals")
            recommendations.append("Stagger signal distribution to different accounts")
        
        if 'position_size' in correlation_types:
            recommendations.append("Implement account-specific position sizing multipliers")
            recommendations.append("Add random variation (±10-20%) to position sizes per account")
        
        if 'pnl' in correlation_types:
            recommendations.append("Review shared signals - accounts may be too similar")
            recommendations.append("Consider different risk parameters per account")
        
        if 'duration' in correlation_types:
            recommendations.append("Vary trade exit criteria between accounts")
            recommendations.append("Add random time-based exit variations")
        
        # Alert-based recommendations
        emergency_alerts = [a for a in alerts if a.severity == 'emergency']
        if emergency_alerts:
            recommendations.append("EMERGENCY: Consider temporarily pausing highly correlated accounts")
        
        critical_alerts = [a for a in alerts if a.severity == 'critical']
        if len(critical_alerts) > 2:
            recommendations.append("Multiple critical correlations detected - comprehensive review needed")
        
        # Trend-based recommendations
        increasing_trends = [t for t in trends if t.trend_direction == 'increasing']
        if len(increasing_trends) > 2:
            recommendations.append("Correlation trends are worsening - investigate common factors")
            recommendations.append("Review recent parameter changes that may affect all accounts")
        
        return recommendations
    
    def _filter_trades_by_window(
        self,
        account_trades: Dict[str, List[Any]],
        window: timedelta
    ) -> Dict[str, List[Any]]:
        """
        Filter trades to analysis window
        """
        cutoff_time = datetime.now() - window
        filtered = {}
        
        for account, trades in account_trades.items():
            filtered_trades = [
                t for t in trades 
                if hasattr(t, 'timestamp') and t.timestamp >= cutoff_time
            ]
            filtered[account] = filtered_trades
        
        return filtered
    
    def _update_correlation_history(self, account_pairs: List[CorrelationPair]):
        """
        Update correlation history for trend analysis
        """
        for pair in account_pairs:
            data_point = CorrelationDataPoint(
                timestamp=datetime.now(),
                account_1=pair.account_1,
                account_2=pair.account_2,
                correlation=pair.correlation,
                correlation_type=pair.correlation_type,
                significance=pair.p_value,
                sample_size=pair.sample_size
            )
            self.correlation_history.append(data_point)
    
    def _create_insufficient_accounts_analysis(self) -> CorrelationAnalysis:
        """
        Create analysis result when insufficient accounts
        """
        return CorrelationAnalysis(
            account_pairs=[],
            correlation_history=[],
            trends=[],
            active_alerts=[],
            risk_score=0.0,
            suspicious_pairs=[],
            recommendations=["Need at least 2 accounts for correlation analysis"]
        )
    
    def get_correlation_summary(self, lookback_hours: int = 24) -> Dict[str, Any]:
        """
        Get summary of recent correlation activity
        """
        cutoff_time = datetime.now() - timedelta(hours=lookback_hours)
        
        recent_data = [
            dp for dp in self.correlation_history 
            if dp.timestamp >= cutoff_time
        ]
        
        if not recent_data:
            return {'status': 'no_recent_data'}
        
        # Group by account pairs
        pair_data = defaultdict(list)
        for dp in recent_data:
            pair_key = tuple(sorted([dp.account_1, dp.account_2]))
            pair_data[pair_key].append(dp.correlation)
        
        summary = {
            'status': 'analyzed',
            'period_hours': lookback_hours,
            'account_pairs_analyzed': len(pair_data),
            'total_correlations': len(recent_data),
            'pair_summaries': {}
        }
        
        for pair, correlations in pair_data.items():
            summary['pair_summaries'][pair] = {
                'max_correlation': max(correlations),
                'avg_correlation': np.mean(correlations),
                'correlation_count': len(correlations)
            }
        
        return summary