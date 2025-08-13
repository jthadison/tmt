"""
Performance Anomaly Detection

Detects suspicious patterns in trading performance that could indicate
data poisoning, manipulation, or other learning corruption scenarios.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass
from enum import Enum
import logging
from statistics import mean, stdev
import math

from market_condition_detector import MarketConditionAnomaly, MarketConditionType, Severity

logger = logging.getLogger(__name__)


class PerformanceMetricType(Enum):
    """Types of performance metrics"""
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"
    SHARPE_RATIO = "sharpe_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    AVERAGE_WIN = "average_win"
    AVERAGE_LOSS = "average_loss"
    CONSECUTIVE_WINS = "consecutive_wins"
    CONSECUTIVE_LOSSES = "consecutive_losses"


@dataclass
class TradeResult:
    """Individual trade result"""
    trade_id: str
    timestamp: datetime
    symbol: str
    side: str  # 'buy' or 'sell'
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal
    profit_loss: Decimal
    duration_minutes: int
    
    @property
    def is_winner(self) -> bool:
        """Check if trade was profitable"""
        return self.profit_loss > 0
    
    @property
    def return_percentage(self) -> float:
        """Calculate return percentage"""
        return float(self.profit_loss / (self.entry_price * self.quantity)) if self.entry_price > 0 else 0.0


@dataclass
class PerformanceWindow:
    """Performance metrics for a time window"""
    start_time: datetime
    end_time: datetime
    trades: List[TradeResult]
    
    # Calculated metrics
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    total_profit_loss: Decimal
    average_win: Decimal
    average_loss: Decimal
    
    # Risk metrics
    consecutive_wins: int
    consecutive_losses: int
    largest_win: Decimal
    largest_loss: Decimal
    
    @classmethod
    def from_trades(cls, trades: List[TradeResult], start_time: datetime, end_time: datetime) -> 'PerformanceWindow':
        """Create performance window from trade list"""
        if not trades:
            return cls(
                start_time=start_time,
                end_time=end_time,
                trades=[],
                win_rate=0.0,
                profit_factor=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                total_profit_loss=Decimal('0'),
                average_win=Decimal('0'),
                average_loss=Decimal('0'),
                consecutive_wins=0,
                consecutive_losses=0,
                largest_win=Decimal('0'),
                largest_loss=Decimal('0')
            )
        
        # Calculate basic metrics
        winners = [t for t in trades if t.is_winner]
        losers = [t for t in trades if not t.is_winner]
        
        win_rate = len(winners) / len(trades) if trades else 0.0
        
        total_wins = sum(t.profit_loss for t in winners)
        total_losses = abs(sum(t.profit_loss for t in losers))
        
        profit_factor = float(total_wins / total_losses) if total_losses > 0 else float('inf') if total_wins > 0 else 0.0
        
        # Calculate Sharpe ratio (simplified)
        returns = [t.return_percentage for t in trades]
        avg_return = mean(returns) if returns else 0.0
        return_std = stdev(returns) if len(returns) > 1 else 0.0
        sharpe_ratio = avg_return / return_std if return_std > 0 else 0.0
        
        # Calculate drawdown
        cumulative_pnl = []
        running_total = Decimal('0')
        for trade in trades:
            running_total += trade.profit_loss
            cumulative_pnl.append(running_total)
        
        peak = cumulative_pnl[0] if cumulative_pnl else Decimal('0')
        max_drawdown = 0.0
        for pnl in cumulative_pnl:
            if pnl > peak:
                peak = pnl
            drawdown = float((peak - pnl) / peak) if peak > 0 else 0.0
            max_drawdown = max(max_drawdown, drawdown)
        
        # Calculate consecutive streaks
        consecutive_wins = consecutive_losses = 0
        current_win_streak = current_loss_streak = 0
        
        for trade in trades:
            if trade.is_winner:
                current_win_streak += 1
                current_loss_streak = 0
                consecutive_wins = max(consecutive_wins, current_win_streak)
            else:
                current_loss_streak += 1
                current_win_streak = 0
                consecutive_losses = max(consecutive_losses, current_loss_streak)
        
        return cls(
            start_time=start_time,
            end_time=end_time,
            trades=trades,
            win_rate=win_rate,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            total_profit_loss=sum(t.profit_loss for t in trades),
            average_win=total_wins / len(winners) if winners else Decimal('0'),
            average_loss=total_losses / len(losers) if losers else Decimal('0'),
            consecutive_wins=consecutive_wins,
            consecutive_losses=consecutive_losses,
            largest_win=max((t.profit_loss for t in winners), default=Decimal('0')),
            largest_loss=min((t.profit_loss for t in losers), default=Decimal('0'))
        )


@dataclass
class PerformanceThresholds:
    """Thresholds for performance anomaly detection"""
    # Win rate anomaly detection
    max_win_rate_increase: float = 0.15  # 15% increase over baseline
    min_sample_size_for_anomaly_check: int = 50  # 50 trades minimum
    
    # Performance consistency
    max_sharpe_improvement: float = 0.50  # 50% Sharpe ratio increase
    max_profit_factor_increase: float = 0.30  # 30% profit factor increase
    
    # Statistical significance
    min_p_value_for_suspicion: float = 0.01  # p < 0.01 is suspicious
    confidence_interval_threshold: float = 0.95  # 95% confidence required
    
    # Performance degradation (also suspicious if sudden)
    max_drawdown_increase: float = 0.20  # 20% drawdown increase
    max_consecutive_losses: int = 10  # 10 consecutive losses
    
    # Improvement velocity (too fast = suspicious)
    max_improvement_velocity: float = 0.05  # 5% per day max improvement


class WinRateAnomalyDetector:
    """Detects suspicious win rate improvements"""
    
    def __init__(self, thresholds: PerformanceThresholds):
        self.thresholds = thresholds
        self.baseline_windows: Dict[str, List[PerformanceWindow]] = {}
        
    def add_baseline_period(self, account_id: str, window: PerformanceWindow) -> None:
        """Add a baseline performance window"""
        if account_id not in self.baseline_windows:
            self.baseline_windows[account_id] = []
        self.baseline_windows[account_id].append(window)
        
        # Keep only last 10 windows for baseline
        self.baseline_windows[account_id] = self.baseline_windows[account_id][-10:]
    
    def detect_anomaly(self, account_id: str, current_window: PerformanceWindow) -> Optional[MarketConditionAnomaly]:
        """Detect win rate anomalies"""
        if account_id not in self.baseline_windows or not self.baseline_windows[account_id]:
            return None
            
        if len(current_window.trades) < self.thresholds.min_sample_size_for_anomaly_check:
            return None
        
        # Calculate baseline win rate
        baseline_windows = self.baseline_windows[account_id]
        baseline_win_rates = [w.win_rate for w in baseline_windows if len(w.trades) >= 10]
        
        if not baseline_win_rates:
            return None
            
        baseline_win_rate = mean(baseline_win_rates)
        win_rate_increase = current_window.win_rate - baseline_win_rate
        
        if win_rate_increase > self.thresholds.max_win_rate_increase:
            # Perform statistical significance test
            p_value = self._statistical_test(baseline_win_rates, current_window.win_rate)
            
            # Debug logging
            logger.info(f"Win rate anomaly check: increase={win_rate_increase:.3f}, threshold={self.thresholds.max_win_rate_increase:.3f}, p_value={p_value:.6f}")
            
            if p_value < self.thresholds.min_p_value_for_suspicion:
                severity = self._calculate_severity(win_rate_increase, self.thresholds.max_win_rate_increase)
                
                return MarketConditionAnomaly(
                    detection_id=f"win_rate_{account_id}_{current_window.end_time.isoformat()}",
                    timestamp=current_window.end_time,
                    condition_type=MarketConditionType.FLASH_CRASH,  # Reusing enum, would need PerformanceAnomaly type
                    severity=severity,
                    confidence=1 - p_value,
                    observed_value=current_window.win_rate,
                    expected_value=baseline_win_rate,
                    threshold=baseline_win_rate + self.thresholds.max_win_rate_increase,
                    deviation_magnitude=win_rate_increase,
                    symbol=account_id,
                    description=f"Suspicious win rate improvement: {win_rate_increase:.2%} increase",
                    potential_causes=["Data poisoning", "Market manipulation", "System error", "Lucky streak"],
                    learning_safe=False,
                    quarantine_recommended=True,
                    lockout_duration_minutes=120  # 2 hour lockout for performance anomalies
                )
        
        return None
    
    def _statistical_test(self, baseline_rates: List[float], current_rate: float) -> float:
        """Simplified statistical test for win rate significance"""
        baseline_mean = mean(baseline_rates)
        baseline_std = stdev(baseline_rates) if len(baseline_rates) > 1 else 0.1
        
        # Z-test approximation
        z_score = abs(current_rate - baseline_mean) / baseline_std if baseline_std > 0 else 0
        
        # Convert z-score to p-value (simplified)
        p_value = max(0.001, 2 * (1 - self._norm_cdf(z_score)))
        return p_value
    
    def _norm_cdf(self, z: float) -> float:
        """Approximate normal CDF"""
        return 0.5 * (1 + math.erf(z / math.sqrt(2)))
    
    def _calculate_severity(self, increase: float, threshold: float) -> Severity:
        """Calculate severity based on improvement magnitude"""
        ratio = increase / threshold
        if ratio >= 2.0:
            return Severity.CRITICAL
        elif ratio >= 1.5:
            return Severity.HIGH
        elif ratio >= 1.2:
            return Severity.MEDIUM
        else:
            return Severity.LOW


class SharpeRatioAnomalyDetector:
    """Detects suspicious Sharpe ratio improvements"""
    
    def __init__(self, thresholds: PerformanceThresholds):
        self.thresholds = thresholds
        self.baseline_windows: Dict[str, List[PerformanceWindow]] = {}
    
    def add_baseline_period(self, account_id: str, window: PerformanceWindow) -> None:
        """Add a baseline performance window"""
        if account_id not in self.baseline_windows:
            self.baseline_windows[account_id] = []
        self.baseline_windows[account_id].append(window)
        self.baseline_windows[account_id] = self.baseline_windows[account_id][-10:]
    
    def detect_anomaly(self, account_id: str, current_window: PerformanceWindow) -> Optional[MarketConditionAnomaly]:
        """Detect Sharpe ratio anomalies"""
        if account_id not in self.baseline_windows or not self.baseline_windows[account_id]:
            return None
            
        baseline_windows = self.baseline_windows[account_id]
        baseline_sharpes = [w.sharpe_ratio for w in baseline_windows if w.sharpe_ratio != 0]
        
        if not baseline_sharpes or current_window.sharpe_ratio == 0:
            return None
            
        baseline_sharpe = mean(baseline_sharpes)
        sharpe_improvement = (current_window.sharpe_ratio - baseline_sharpe) / abs(baseline_sharpe) if baseline_sharpe != 0 else 0
        
        if sharpe_improvement > self.thresholds.max_sharpe_improvement:
            severity = self._calculate_severity(sharpe_improvement, self.thresholds.max_sharpe_improvement)
            
            return MarketConditionAnomaly(
                detection_id=f"sharpe_{account_id}_{current_window.end_time.isoformat()}",
                timestamp=current_window.end_time,
                condition_type=MarketConditionType.FLASH_CRASH,  # Placeholder
                severity=severity,
                confidence=min(1.0, sharpe_improvement / self.thresholds.max_sharpe_improvement),
                observed_value=current_window.sharpe_ratio,
                expected_value=baseline_sharpe,
                threshold=baseline_sharpe * (1 + self.thresholds.max_sharpe_improvement),
                deviation_magnitude=sharpe_improvement,
                symbol=account_id,
                description=f"Suspicious Sharpe ratio improvement: {sharpe_improvement:.2%}",
                potential_causes=["Performance manipulation", "Data corruption", "Model overfitting"],
                learning_safe=False,
                quarantine_recommended=severity in [Severity.HIGH, Severity.CRITICAL],
                lockout_duration_minutes=60 if severity == Severity.MEDIUM else 120
            )
        
        return None
    
    def _calculate_severity(self, improvement: float, threshold: float) -> Severity:
        """Calculate severity based on improvement magnitude"""
        ratio = improvement / threshold
        if ratio >= 2.0:
            return Severity.CRITICAL
        elif ratio >= 1.5:
            return Severity.HIGH
        elif ratio >= 1.2:
            return Severity.MEDIUM
        else:
            return Severity.LOW


class PerformanceConsistencyMonitor:
    """Monitors performance consistency for suspicious patterns"""
    
    def __init__(self, thresholds: PerformanceThresholds):
        self.thresholds = thresholds
        self.performance_history: Dict[str, List[PerformanceWindow]] = {}
    
    def add_performance_window(self, account_id: str, window: PerformanceWindow) -> None:
        """Add performance window to history"""
        if account_id not in self.performance_history:
            self.performance_history[account_id] = []
        self.performance_history[account_id].append(window)
        
        # Keep last 20 windows
        self.performance_history[account_id] = self.performance_history[account_id][-20:]
    
    def detect_anomalies(self, account_id: str) -> List[MarketConditionAnomaly]:
        """Detect consistency anomalies"""
        if account_id not in self.performance_history:
            return []
            
        windows = self.performance_history[account_id]
        if len(windows) < 5:  # Need enough history
            return []
        
        anomalies = []
        
        # Check for improvement velocity anomaly
        velocity_anomaly = self._check_improvement_velocity(account_id, windows)
        if velocity_anomaly:
            anomalies.append(velocity_anomaly)
        
        # Check for consecutive loss anomaly
        consecutive_loss_anomaly = self._check_consecutive_losses(account_id, windows)
        if consecutive_loss_anomaly:
            anomalies.append(consecutive_loss_anomaly)
        
        return anomalies
    
    def _check_improvement_velocity(self, account_id: str, windows: List[PerformanceWindow]) -> Optional[MarketConditionAnomaly]:
        """Check if performance is improving too quickly"""
        logger.info(f"Checking velocity for {account_id}: {len(windows)} windows")
        if len(windows) < 3:
            logger.info(f"Not enough windows for velocity check: {len(windows)} < 3")
            return None
            
        # Calculate daily improvement rate (simplified)
        recent_windows = windows[-3:]
        win_rates = [w.win_rate for w in recent_windows]
        
        if len(set(win_rates)) == 1:  # No change
            return None
            
        # Calculate velocity (improvement per day)
        time_span = recent_windows[-1].end_time - recent_windows[0].start_time
        time_span_days = time_span.total_seconds() / (24 * 3600)  # Convert to fractional days
        if time_span_days == 0:
            time_span_days = 1
            
        win_rate_change = win_rates[-1] - win_rates[0]
        velocity = win_rate_change / time_span_days
        
        # Debug logging
        logger.info(f"Velocity check: win_rates={win_rates}, time_span={time_span_days}, change={win_rate_change:.3f}, velocity={velocity:.3f}, threshold={self.thresholds.max_improvement_velocity:.3f}")
        
        if velocity > self.thresholds.max_improvement_velocity:
            return MarketConditionAnomaly(
                detection_id=f"velocity_{account_id}_{recent_windows[-1].end_time.isoformat()}",
                timestamp=recent_windows[-1].end_time,
                condition_type=MarketConditionType.FLASH_CRASH,  # Placeholder
                severity=Severity.HIGH,
                confidence=min(1.0, velocity / self.thresholds.max_improvement_velocity),
                observed_value=velocity,
                expected_value=self.thresholds.max_improvement_velocity / 2,
                threshold=self.thresholds.max_improvement_velocity,
                deviation_magnitude=velocity - self.thresholds.max_improvement_velocity,
                symbol=account_id,
                description=f"Suspicious improvement velocity: {velocity:.2%} per day",
                potential_causes=["Artificial performance boost", "Data manipulation", "System error"],
                learning_safe=False,
                quarantine_recommended=True,
                lockout_duration_minutes=180  # 3 hour lockout
            )
        
        return None
    
    def _check_consecutive_losses(self, account_id: str, windows: List[PerformanceWindow]) -> Optional[MarketConditionAnomaly]:
        """Check for suspicious consecutive loss patterns"""
        latest_window = windows[-1]
        
        if latest_window.consecutive_losses > self.thresholds.max_consecutive_losses:
            return MarketConditionAnomaly(
                detection_id=f"consecutive_losses_{account_id}_{latest_window.end_time.isoformat()}",
                timestamp=latest_window.end_time,
                condition_type=MarketConditionType.FLASH_CRASH,  # Placeholder
                severity=Severity.MEDIUM,
                confidence=min(1.0, latest_window.consecutive_losses / self.thresholds.max_consecutive_losses),
                observed_value=latest_window.consecutive_losses,
                expected_value=self.thresholds.max_consecutive_losses / 2,
                threshold=self.thresholds.max_consecutive_losses,
                deviation_magnitude=latest_window.consecutive_losses - self.thresholds.max_consecutive_losses,
                symbol=account_id,
                description=f"Excessive consecutive losses: {latest_window.consecutive_losses}",
                potential_causes=["System malfunction", "Model degradation", "Market regime change"],
                learning_safe=False,
                quarantine_recommended=False,  # Degradation doesn't need quarantine
                lockout_duration_minutes=60
            )
        
        return None


class PerformanceAnomalyDetector:
    """Main performance anomaly detector coordinating all checks"""
    
    def __init__(self, thresholds: Optional[PerformanceThresholds] = None):
        self.thresholds = thresholds or PerformanceThresholds()
        self.win_rate_detector = WinRateAnomalyDetector(self.thresholds)
        self.sharpe_detector = SharpeRatioAnomalyDetector(self.thresholds)
        self.consistency_monitor = PerformanceConsistencyMonitor(self.thresholds)
        
    def add_baseline_performance(self, account_id: str, window: PerformanceWindow) -> None:
        """Add baseline performance data"""
        self.win_rate_detector.add_baseline_period(account_id, window)
        self.sharpe_detector.add_baseline_period(account_id, window)
        self.consistency_monitor.add_performance_window(account_id, window)
    
    def detect_anomalies(self, account_id: str, current_window: PerformanceWindow) -> List[MarketConditionAnomaly]:
        """Detect all performance anomalies"""
        anomalies = []
        
        try:
            # Win rate anomaly detection
            win_rate_anomaly = self.win_rate_detector.detect_anomaly(account_id, current_window)
            if win_rate_anomaly:
                anomalies.append(win_rate_anomaly)
                
            # Sharpe ratio anomaly detection
            sharpe_anomaly = self.sharpe_detector.detect_anomaly(account_id, current_window)
            if sharpe_anomaly:
                anomalies.append(sharpe_anomaly)
                
            # Add current window to consistency monitor
            self.consistency_monitor.add_performance_window(account_id, current_window)
            
            # Performance consistency checks
            consistency_anomalies = self.consistency_monitor.detect_anomalies(account_id)
            anomalies.extend(consistency_anomalies)
            
            # Log detected anomalies
            if anomalies:
                logger.warning(f"Performance anomalies detected for {account_id}: "
                             f"{len(anomalies)} anomalies")
                
        except Exception as e:
            logger.error(f"Error detecting performance anomalies for {account_id}: {e}")
            
        return anomalies