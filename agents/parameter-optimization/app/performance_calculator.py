"""
30-Day Rolling Performance Calculator

Calculates rolling performance metrics for parameter optimization analysis.
"""

import math
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

from .models import PerformanceMetrics, MarketRegime

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """Individual trade record for performance calculation"""
    trade_id: str
    account_id: str
    symbol: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    position_size: float
    pnl: float
    pnl_pips: float
    commission: float
    slippage: float
    trade_type: str  # "long" or "short"
    exit_reason: str  # "stop_loss", "take_profit", "manual", "timeout"
    signal_confidence: float
    market_regime: MarketRegime = MarketRegime.UNKNOWN


@dataclass
class PerformancePeriod:
    """Performance metrics for a specific time period"""
    start_date: datetime
    end_date: datetime
    trades: List[TradeRecord]
    metrics: PerformanceMetrics


class RollingPerformanceCalculator:
    """
    Calculates rolling performance metrics for optimization analysis
    """
    
    def __init__(self, rolling_window_days: int = 30):
        self.rolling_window_days = rolling_window_days
        self.cache = {}  # Cache for performance calculations
        
    def calculate_rolling_performance(self, account_id: str, 
                                    trades: List[TradeRecord],
                                    end_date: Optional[datetime] = None) -> List[PerformancePeriod]:
        """
        Calculate rolling performance metrics for the specified period
        
        Args:
            account_id: Account identifier
            trades: List of trade records
            end_date: End date for calculation (default: now)
            
        Returns:
            List of performance periods with metrics
        """
        try:
            if not trades:
                logger.warning(f"No trades provided for account {account_id}")
                return []
            
            if end_date is None:
                end_date = datetime.utcnow()
            
            # Sort trades by exit time
            sorted_trades = sorted(trades, key=lambda t: t.exit_time)
            
            # Calculate rolling periods
            periods = []
            current_date = end_date
            
            while current_date >= sorted_trades[0].exit_time:
                period_start = current_date - timedelta(days=self.rolling_window_days)
                period_end = current_date
                
                # Get trades in this period
                period_trades = [
                    trade for trade in sorted_trades
                    if period_start <= trade.exit_time <= period_end
                ]
                
                if len(period_trades) >= 5:  # Minimum trades for meaningful analysis
                    metrics = self._calculate_period_metrics(
                        account_id, period_trades, period_start, period_end
                    )
                    
                    period = PerformancePeriod(
                        start_date=period_start,
                        end_date=period_end,
                        trades=period_trades,
                        metrics=metrics
                    )
                    periods.append(period)
                
                # Move back by one day
                current_date -= timedelta(days=1)
            
            logger.info(f"Calculated {len(periods)} rolling performance periods for {account_id}")
            return periods
            
        except Exception as e:
            logger.error(f"Failed to calculate rolling performance for {account_id}: {e}")
            raise
    
    def calculate_current_performance(self, account_id: str,
                                    trades: List[TradeRecord]) -> PerformanceMetrics:
        """
        Calculate current 30-day performance metrics
        
        Args:
            account_id: Account identifier
            trades: List of trade records
            
        Returns:
            Current performance metrics
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=self.rolling_window_days)
            
            # Filter trades to current period
            current_trades = [
                trade for trade in trades
                if start_date <= trade.exit_time <= end_date
            ]
            
            if not current_trades:
                logger.warning(f"No trades in current period for {account_id}")
                return self._create_empty_metrics(account_id, start_date, end_date)
            
            return self._calculate_period_metrics(
                account_id, current_trades, start_date, end_date
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate current performance for {account_id}: {e}")
            raise
    
    def _calculate_period_metrics(self, account_id: str, trades: List[TradeRecord],
                                start_date: datetime, end_date: datetime) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics for a period"""
        try:
            if not trades:
                return self._create_empty_metrics(account_id, start_date, end_date)
            
            # Basic trade statistics
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t.pnl > 0])
            losing_trades = len([t for t in trades if t.pnl < 0])
            
            # PnL calculations
            pnl_values = [t.pnl for t in trades]
            total_pnl = sum(pnl_values)
            
            # Win/Loss statistics
            wins = [t.pnl for t in trades if t.pnl > 0]
            losses = [t.pnl for t in trades if t.pnl < 0]
            
            avg_win = statistics.mean(wins) if wins else 0.0
            avg_loss = statistics.mean(losses) if losses else 0.0
            largest_win = max(wins) if wins else 0.0
            largest_loss = min(losses) if losses else 0.0
            
            # Win rate and expectancy
            win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
            expectancy = avg_win * win_rate + avg_loss * (1 - win_rate)
            
            # Profit factor
            gross_profit = sum(wins) if wins else 0.0
            gross_loss = abs(sum(losses)) if losses else 0.0
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0.0
            
            # Drawdown calculations
            max_drawdown, current_drawdown = self._calculate_drawdown(trades)
            
            # Risk-adjusted returns
            returns = self._calculate_returns(trades)
            volatility = self._calculate_volatility(returns)
            sharpe_ratio = self._calculate_sharpe_ratio(returns, volatility)
            calmar_ratio = self._calculate_calmar_ratio(total_pnl, max_drawdown, len(trades))
            sortino_ratio = self._calculate_sortino_ratio(returns)
            
            # Risk metrics
            var_95 = self._calculate_var(pnl_values, 0.95)
            expected_shortfall = self._calculate_expected_shortfall(pnl_values, 0.95)
            
            # Market regime analysis
            market_regime = self._determine_market_regime(trades)
            
            return PerformanceMetrics(
                timestamp=datetime.utcnow(),
                account_id=account_id,
                sharpe_ratio=sharpe_ratio,
                calmar_ratio=calmar_ratio,
                sortino_ratio=sortino_ratio,
                profit_factor=profit_factor,
                win_rate=win_rate,
                max_drawdown=max_drawdown,
                current_drawdown=current_drawdown,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                avg_win=avg_win,
                avg_loss=avg_loss,
                largest_win=largest_win,
                largest_loss=largest_loss,
                expectancy=expectancy,
                volatility=volatility,
                var_95=var_95,
                expected_shortfall=expected_shortfall,
                period_start=start_date,
                period_end=end_date,
                market_regime=market_regime
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate period metrics: {e}")
            raise
    
    def _calculate_drawdown(self, trades: List[TradeRecord]) -> Tuple[float, float]:
        """Calculate maximum and current drawdown"""
        if not trades:
            return 0.0, 0.0
        
        # Calculate cumulative PnL
        cumulative_pnl = []
        running_total = 0.0
        
        for trade in sorted(trades, key=lambda t: t.exit_time):
            running_total += trade.pnl
            cumulative_pnl.append(running_total)
        
        # Calculate drawdown from peak
        peak = cumulative_pnl[0]
        max_drawdown = 0.0
        current_drawdown = 0.0
        
        for i, pnl in enumerate(cumulative_pnl):
            if pnl > peak:
                peak = pnl
            
            drawdown = (peak - pnl) / abs(peak) if peak != 0 else 0.0
            max_drawdown = max(max_drawdown, drawdown)
            
            # Current drawdown is the drawdown at the end
            if i == len(cumulative_pnl) - 1:
                current_drawdown = drawdown
        
        return max_drawdown, current_drawdown
    
    def _calculate_returns(self, trades: List[TradeRecord]) -> List[float]:
        """Calculate trade returns as percentages"""
        returns = []
        for trade in trades:
            if trade.position_size > 0:
                # Calculate return as percentage of position size
                return_pct = trade.pnl / trade.position_size
                returns.append(return_pct)
        return returns
    
    def _calculate_volatility(self, returns: List[float]) -> float:
        """Calculate return volatility (standard deviation)"""
        if len(returns) < 2:
            return 0.0
        
        try:
            return statistics.stdev(returns)
        except statistics.StatisticsError:
            return 0.0
    
    def _calculate_sharpe_ratio(self, returns: List[float], volatility: float,
                              risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        if not returns or volatility == 0:
            return 0.0
        
        avg_return = statistics.mean(returns)
        excess_return = avg_return - risk_free_rate / 252  # Daily risk-free rate
        
        return excess_return / volatility if volatility > 0 else 0.0
    
    def _calculate_calmar_ratio(self, total_pnl: float, max_drawdown: float,
                              num_trades: int) -> float:
        """Calculate Calmar ratio (annual return / max drawdown)"""
        if max_drawdown == 0 or num_trades == 0:
            return 0.0
        
        # Annualize the return (rough approximation)
        annual_return = total_pnl * (252 / num_trades) if num_trades > 0 else 0.0
        
        return annual_return / max_drawdown if max_drawdown > 0 else 0.0
    
    def _calculate_sortino_ratio(self, returns: List[float],
                               target_return: float = 0.0) -> float:
        """Calculate Sortino ratio (downside deviation)"""
        if not returns:
            return 0.0
        
        avg_return = statistics.mean(returns)
        downside_returns = [r for r in returns if r < target_return]
        
        if not downside_returns:
            return float('inf') if avg_return > target_return else 0.0
        
        downside_deviation = math.sqrt(statistics.mean([(r - target_return) ** 2 for r in downside_returns]))
        
        return (avg_return - target_return) / downside_deviation if downside_deviation > 0 else 0.0
    
    def _calculate_var(self, pnl_values: List[float], confidence: float) -> float:
        """Calculate Value at Risk"""
        if not pnl_values:
            return 0.0
        
        sorted_pnl = sorted(pnl_values)
        index = int((1 - confidence) * len(sorted_pnl))
        
        return sorted_pnl[index] if index < len(sorted_pnl) else sorted_pnl[-1]
    
    def _calculate_expected_shortfall(self, pnl_values: List[float], confidence: float) -> float:
        """Calculate Expected Shortfall (Conditional VaR)"""
        if not pnl_values:
            return 0.0
        
        var = self._calculate_var(pnl_values, confidence)
        tail_losses = [pnl for pnl in pnl_values if pnl <= var]
        
        return statistics.mean(tail_losses) if tail_losses else 0.0
    
    def _determine_market_regime(self, trades: List[TradeRecord]) -> MarketRegime:
        """Determine the primary market regime during the period"""
        if not trades:
            return MarketRegime.UNKNOWN
        
        # Count regime occurrences
        regime_counts = {}
        for trade in trades:
            regime = trade.market_regime
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
        
        # Return the most common regime
        if regime_counts:
            most_common = max(regime_counts.items(), key=lambda x: x[1])
            return most_common[0]
        
        return MarketRegime.UNKNOWN
    
    def _create_empty_metrics(self, account_id: str, start_date: datetime,
                            end_date: datetime) -> PerformanceMetrics:
        """Create empty metrics for periods with no trades"""
        return PerformanceMetrics(
            timestamp=datetime.utcnow(),
            account_id=account_id,
            sharpe_ratio=0.0,
            calmar_ratio=0.0,
            sortino_ratio=0.0,
            profit_factor=0.0,
            win_rate=0.0,
            max_drawdown=0.0,
            current_drawdown=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            avg_win=0.0,
            avg_loss=0.0,
            largest_win=0.0,
            largest_loss=0.0,
            expectancy=0.0,
            volatility=0.0,
            var_95=0.0,
            expected_shortfall=0.0,
            period_start=start_date,
            period_end=end_date,
            market_regime=MarketRegime.UNKNOWN
        )
    
    def get_performance_comparison(self, current_period: PerformancePeriod,
                                 historical_periods: List[PerformancePeriod]) -> Dict[str, float]:
        """
        Compare current performance against historical averages
        
        Args:
            current_period: Current period performance
            historical_periods: List of historical periods for comparison
            
        Returns:
            Dictionary of performance comparisons (current vs historical)
        """
        try:
            if not historical_periods:
                return {}
            
            # Calculate historical averages
            historical_sharpe = statistics.mean([p.metrics.sharpe_ratio for p in historical_periods])
            historical_calmar = statistics.mean([p.metrics.calmar_ratio for p in historical_periods])
            historical_profit_factor = statistics.mean([p.metrics.profit_factor for p in historical_periods])
            historical_win_rate = statistics.mean([p.metrics.win_rate for p in historical_periods])
            historical_max_drawdown = statistics.mean([p.metrics.max_drawdown for p in historical_periods])
            
            # Calculate comparisons
            current = current_period.metrics
            
            return {
                "sharpe_ratio_delta": current.sharpe_ratio - historical_sharpe,
                "calmar_ratio_delta": current.calmar_ratio - historical_calmar,
                "profit_factor_delta": current.profit_factor - historical_profit_factor,
                "win_rate_delta": current.win_rate - historical_win_rate,
                "max_drawdown_delta": current.max_drawdown - historical_max_drawdown,
                "sharpe_ratio_improvement": (current.sharpe_ratio / historical_sharpe - 1) if historical_sharpe > 0 else 0.0,
                "calmar_ratio_improvement": (current.calmar_ratio / historical_calmar - 1) if historical_calmar > 0 else 0.0,
                "profit_factor_improvement": (current.profit_factor / historical_profit_factor - 1) if historical_profit_factor > 0 else 0.0
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate performance comparison: {e}")
            return {}
    
    def clear_cache(self):
        """Clear the performance calculation cache"""
        self.cache.clear()
        logger.info("Performance calculation cache cleared")