"""
Performance Degradation Detector - Story 11.4, Task 4

Tracks live trading performance and compares against backtest expectations.
"""

import logging
import numpy as np
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from collections import deque

from .models import PerformanceMetrics, AlertLevel

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """
    Performance degradation detection system

    Monitors live trading performance metrics and compares against
    backtest expectations to detect regime changes and parameter degradation.
    """

    def __init__(
        self,
        rolling_window_days: int = 7,
        degradation_threshold: float = 0.7,  # 70% of backtest performance
        max_history_size: int = 1000
    ):
        """
        Initialize performance tracker

        @param rolling_window_days: Days for rolling performance calculation (default: 7)
        @param degradation_threshold: Alert when live < threshold * backtest (default: 0.7)
        @param max_history_size: Maximum number of historical data points to retain
        """
        self.rolling_window_days = rolling_window_days
        self.degradation_threshold = degradation_threshold
        self.max_history_size = max_history_size

        # Historical performance data
        self.trade_history: deque = deque(maxlen=max_history_size)
        self.performance_history: deque = deque(maxlen=max_history_size)

    def add_trade(
        self,
        timestamp: datetime,
        pnl: float,
        is_win: bool,
        risk_reward: float
    ):
        """
        Add a completed trade to history

        @param timestamp: Trade completion time
        @param pnl: Profit/loss for trade
        @param is_win: Whether trade was profitable
        @param risk_reward: Actual risk:reward ratio achieved
        """
        self.trade_history.append({
            'timestamp': timestamp,
            'pnl': pnl,
            'is_win': is_win,
            'risk_reward': risk_reward
        })

        logger.debug(
            f"Trade recorded: timestamp={timestamp}, pnl={pnl:.2f}, "
            f"win={is_win}, r:r={risk_reward:.2f}"
        )

    def calculate_rolling_sharpe(
        self,
        window_days: Optional[int] = None
    ) -> Optional[float]:
        """
        Calculate rolling Sharpe ratio for recent trades

        @param window_days: Days to include (default: self.rolling_window_days)
        @returns: Sharpe ratio or None if insufficient data
        """
        window = window_days or self.rolling_window_days

        # Filter trades within window
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=window)
        recent_trades = [
            t for t in self.trade_history
            if t['timestamp'] >= cutoff_time
        ]

        if len(recent_trades) < 5:  # Minimum trades for meaningful calculation
            logger.debug(
                f"Insufficient trades ({len(recent_trades)}) for Sharpe calculation"
            )
            return None

        # Extract returns
        returns = [t['pnl'] for t in recent_trades]

        # Calculate Sharpe ratio
        # Sharpe = mean(returns) / std(returns) * sqrt(252)
        # Using daily returns assumption
        mean_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return None

        # Annualized Sharpe (assuming ~252 trading days)
        sharpe = (mean_return / std_return) * np.sqrt(252)

        logger.debug(
            f"Rolling {window}-day Sharpe: {sharpe:.2f} "
            f"(trades={len(recent_trades)}, mean={mean_return:.2f}, std={std_return:.2f})"
        )

        return float(sharpe)

    def calculate_win_rate(
        self,
        window_days: Optional[int] = None
    ) -> Optional[float]:
        """
        Calculate win rate for recent trades

        @param window_days: Days to include (default: self.rolling_window_days)
        @returns: Win rate percentage or None if no trades
        """
        window = window_days or self.rolling_window_days

        cutoff_time = datetime.now(timezone.utc) - timedelta(days=window)
        recent_trades = [
            t for t in self.trade_history
            if t['timestamp'] >= cutoff_time
        ]

        if not recent_trades:
            return None

        wins = sum(1 for t in recent_trades if t['is_win'])
        win_rate = (wins / len(recent_trades)) * 100

        logger.debug(
            f"Win rate: {win_rate:.1f}% ({wins}/{len(recent_trades)} trades)"
        )

        return win_rate

    def calculate_profit_factor(
        self,
        window_days: Optional[int] = None
    ) -> Optional[float]:
        """
        Calculate profit factor for recent trades

        Profit Factor = Gross Profit / Gross Loss

        @param window_days: Days to include (default: self.rolling_window_days)
        @returns: Profit factor or None if no losing trades
        """
        window = window_days or self.rolling_window_days

        cutoff_time = datetime.now(timezone.utc) - timedelta(days=window)
        recent_trades = [
            t for t in self.trade_history
            if t['timestamp'] >= cutoff_time
        ]

        if not recent_trades:
            return None

        gross_profit = sum(t['pnl'] for t in recent_trades if t['pnl'] > 0)
        gross_loss = abs(sum(t['pnl'] for t in recent_trades if t['pnl'] < 0))

        if gross_loss == 0:
            # All winning trades - return large number
            return 999.99 if gross_profit > 0 else 1.0

        profit_factor = gross_profit / gross_loss

        logger.debug(
            f"Profit factor: {profit_factor:.2f} "
            f"(profit={gross_profit:.2f}, loss={gross_loss:.2f})"
        )

        return profit_factor

    def calculate_average_risk_reward(
        self,
        window_days: Optional[int] = None
    ) -> Optional[float]:
        """
        Calculate average risk:reward ratio achieved

        @param window_days: Days to include (default: self.rolling_window_days)
        @returns: Average R:R ratio or None
        """
        window = window_days or self.rolling_window_days

        cutoff_time = datetime.now(timezone.utc) - timedelta(days=window)
        recent_trades = [
            t for t in self.trade_history
            if t['timestamp'] >= cutoff_time and t['risk_reward'] > 0
        ]

        if not recent_trades:
            return None

        avg_rr = np.mean([t['risk_reward'] for t in recent_trades])

        logger.debug(
            f"Average R:R: {avg_rr:.2f} ({len(recent_trades)} trades)"
        )

        return float(avg_rr)

    def compare_performance(
        self,
        backtest_sharpe: float,
        backtest_win_rate: float,
        backtest_profit_factor: float
    ) -> PerformanceMetrics:
        """
        Compare live performance vs backtest expectations

        @param backtest_sharpe: Expected Sharpe ratio from backtests
        @param backtest_win_rate: Expected win rate %
        @param backtest_profit_factor: Expected profit factor
        @returns: PerformanceMetrics with comparison data
        """
        # Calculate live metrics
        live_sharpe = self.calculate_rolling_sharpe() or 0.0
        live_win_rate = self.calculate_win_rate() or 0.0
        live_profit_factor = self.calculate_profit_factor() or 0.0

        # Calculate performance ratios
        sharpe_ratio = (
            live_sharpe / backtest_sharpe if backtest_sharpe > 0 else 0.0
        )
        win_rate_ratio = (
            live_win_rate / backtest_win_rate if backtest_win_rate > 0 else 0.0
        )
        pf_ratio = (
            live_profit_factor / backtest_profit_factor
            if backtest_profit_factor > 0 else 0.0
        )

        # Overall degradation score (0-1, higher = worse)
        # Weighted: Sharpe 50%, Win Rate 25%, Profit Factor 25%
        degradation_score = 1.0 - (
            sharpe_ratio * 0.5 + win_rate_ratio * 0.25 + pf_ratio * 0.25
        )
        degradation_score = max(0.0, min(1.0, degradation_score))

        logger.info(
            f"Performance comparison: "
            f"Sharpe {live_sharpe:.2f} vs {backtest_sharpe:.2f} ({sharpe_ratio:.1%}), "
            f"WR {live_win_rate:.1f}% vs {backtest_win_rate:.1f}% ({win_rate_ratio:.1%}), "
            f"PF {live_profit_factor:.2f} vs {backtest_profit_factor:.2f} ({pf_ratio:.1%}), "
            f"degradation={degradation_score:.3f}"
        )

        metrics = PerformanceMetrics(
            time=datetime.now(timezone.utc),
            live_sharpe=live_sharpe,
            backtest_sharpe=backtest_sharpe,
            sharpe_ratio=sharpe_ratio,
            live_win_rate=live_win_rate,
            backtest_win_rate=backtest_win_rate,
            live_profit_factor=live_profit_factor,
            backtest_profit_factor=backtest_profit_factor,
            degradation_score=degradation_score
        )

        self.performance_history.append(metrics)

        return metrics

    def detect_regime_change(
        self,
        window_days: int = 7
    ) -> Tuple[bool, Optional[str]]:
        """
        Detect potential regime change affecting strategy performance

        Looks for:
        - Sudden volatility changes
        - Win rate collapse
        - Profit factor degradation

        @param window_days: Days to analyze
        @returns: Tuple of (regime_change_detected, description)
        """
        if len(self.trade_history) < 30:
            return False, None

        cutoff_time = datetime.now(timezone.utc) - timedelta(days=window_days)
        recent_trades = [
            t for t in self.trade_history
            if t['timestamp'] >= cutoff_time
        ]

        if len(recent_trades) < 10:
            return False, None

        # Compare recent vs historical metrics
        recent_pnl = [t['pnl'] for t in recent_trades]
        historical_pnl = [
            t['pnl'] for t in self.trade_history
            if t['timestamp'] < cutoff_time
        ]

        if len(historical_pnl) < 20:
            return False, None

        # Check volatility change
        recent_vol = np.std(recent_pnl)
        historical_vol = np.std(historical_pnl)
        vol_ratio = recent_vol / historical_vol if historical_vol > 0 else 1.0

        # Check win rate change
        recent_win_rate = sum(1 for t in recent_trades if t['is_win']) / len(recent_trades)
        historical_win_rate = sum(
            1 for t in self.trade_history if t['timestamp'] < cutoff_time and t['is_win']
        ) / len(historical_pnl) if historical_pnl else 0.5

        win_rate_change = abs(recent_win_rate - historical_win_rate)

        # Detect regime change
        regime_change = False
        description = None

        if vol_ratio > 2.0:
            regime_change = True
            description = f"Volatility spike detected: {vol_ratio:.1f}x increase"
        elif vol_ratio < 0.5:
            regime_change = True
            description = f"Volatility collapse detected: {1/vol_ratio:.1f}x decrease"
        elif win_rate_change > 0.3:  # 30% change in win rate
            regime_change = True
            direction = "increase" if recent_win_rate > historical_win_rate else "decrease"
            description = f"Win rate {direction}: {win_rate_change*100:.0f}% change"

        if regime_change:
            logger.warning(f"Regime change detected: {description}")

        return regime_change, description

    def is_performance_degraded(
        self,
        backtest_sharpe: float
    ) -> Tuple[bool, float]:
        """
        Check if current performance is significantly degraded

        @param backtest_sharpe: Expected backtest Sharpe ratio
        @returns: Tuple of (is_degraded, degradation_percentage)
        """
        live_sharpe = self.calculate_rolling_sharpe()

        if live_sharpe is None or backtest_sharpe <= 0:
            return False, 0.0

        ratio = live_sharpe / backtest_sharpe
        degradation_pct = (1 - ratio) * 100

        is_degraded = ratio < self.degradation_threshold

        if is_degraded:
            logger.warning(
                f"Performance degradation detected: live Sharpe {live_sharpe:.2f} "
                f"is {ratio*100:.0f}% of backtest {backtest_sharpe:.2f} "
                f"({degradation_pct:.0f}% degradation)"
            )

        return is_degraded, degradation_pct

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get summary of current performance metrics

        @returns: Dictionary with performance summary
        """
        return {
            'total_trades': len(self.trade_history),
            'rolling_sharpe': self.calculate_rolling_sharpe(),
            'win_rate': self.calculate_win_rate(),
            'profit_factor': self.calculate_profit_factor(),
            'avg_risk_reward': self.calculate_average_risk_reward(),
            'window_days': self.rolling_window_days,
            'last_update': datetime.now(timezone.utc).isoformat()
        }
