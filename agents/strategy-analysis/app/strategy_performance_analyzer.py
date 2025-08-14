"""
Main Strategy Performance Analyzer for evaluating strategy effectiveness.
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import asyncio
from dataclasses import asdict

from .models import (
    TradingStrategy, StrategyPerformance, PerformanceMetrics,
    StatisticalSignificance, TimeBasedPerformance, RegimePerformance,
    PerformanceTrend, TrendDirection, StrategyType, MarketRegime,
    DailyPerformance, WeeklyPerformance, MonthlyPerformance
)
from .statistical_tester import StatisticalSignificanceTester
from .regime_analyzer import MarketRegimeAnalyzer
from .correlation_analyzer import CorrelationAnalyzer
from .underperformance_detector import UnderperformanceDetector

logger = logging.getLogger(__name__)


class Trade:
    """Simplified trade model for analysis."""
    def __init__(self, strategy_id: str, timestamp: datetime, pnl: Decimal, 
                 win: bool, hold_time: timedelta, volume: Decimal = Decimal('0')):
        self.strategy_id = strategy_id
        self.timestamp = timestamp
        self.pnl = pnl
        self.win = win
        self.hold_time = hold_time
        self.volume = volume


class StrategyPerformanceAnalyzer:
    """
    Main analyzer for strategy performance evaluation.
    Implements comprehensive strategy analysis including statistical significance,
    regime-based performance, and trend detection.
    """
    
    def __init__(self):
        self.significance_tester = StatisticalSignificanceTester()
        self.regime_analyzer = MarketRegimeAnalyzer()
        self.correlation_analyzer = CorrelationAnalyzer()
        self.underperformance_detector = UnderperformanceDetector()
        
        # Performance calculation parameters
        self.min_trades_for_analysis = 30
        self.confidence_level = Decimal('0.95')  # 95% confidence
        
    async def analyze_strategy_performance(self, strategy_id: str, 
                                         evaluation_period: timedelta) -> StrategyPerformance:
        """
        Analyze comprehensive strategy performance over evaluation period.
        
        Args:
            strategy_id: Unique strategy identifier
            evaluation_period: Time period for analysis
            
        Returns:
            Complete strategy performance analysis
        """
        logger.info(f"Analyzing performance for strategy {strategy_id} over {evaluation_period}")
        
        try:
            # Gather strategy trade data
            trades = await self._get_strategy_trades(strategy_id, evaluation_period)
            
            if len(trades) < self.min_trades_for_analysis:
                logger.warning(f"Insufficient trades ({len(trades)}) for strategy {strategy_id}")
                # Return minimal performance analysis
                return await self._create_minimal_performance(strategy_id, trades)
            
            # Calculate overall performance metrics
            overall_performance = self._calculate_performance_metrics(trades)
            
            # Test statistical significance
            significance = await self.significance_tester.test_significance(
                trades, self.confidence_level
            )
            
            # Analyze time-based performance
            time_based = await self._analyze_time_based_performance(trades)
            
            # Analyze regime-specific performance
            regime_performance = await self._analyze_regime_performance(trades)
            
            # Detect performance trends
            trend = await self._detect_performance_trend(trades)
            
            performance = StrategyPerformance(
                strategy_id=strategy_id,
                overall=overall_performance,
                significance=significance,
                time_based=time_based,
                regime_performance=regime_performance,
                trend=trend,
                last_updated=datetime.utcnow()
            )
            
            logger.info(f"Completed performance analysis for strategy {strategy_id}")
            return performance
            
        except Exception as e:
            logger.error(f"Error analyzing strategy {strategy_id}: {str(e)}")
            raise
    
    def _calculate_performance_metrics(self, trades: List[Trade]) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics from trades."""
        if not trades:
            return self._empty_performance_metrics()
        
        total_trades = len(trades)
        wins = [t for t in trades if t.win]
        losses = [t for t in trades if not t.win]
        
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = Decimal(win_count) / Decimal(total_trades) if total_trades > 0 else Decimal('0')
        
        # PnL calculations
        total_pnl = sum(t.pnl for t in trades)
        winning_pnl = sum(t.pnl for t in wins) if wins else Decimal('0')
        losing_pnl = abs(sum(t.pnl for t in losses)) if losses else Decimal('0')
        
        average_win = winning_pnl / Decimal(win_count) if win_count > 0 else Decimal('0')
        average_loss = losing_pnl / Decimal(loss_count) if loss_count > 0 else Decimal('0')
        
        # Profit factor and expectancy
        profit_factor = winning_pnl / losing_pnl if losing_pnl > 0 else Decimal('1000')  # Cap at 1000 for infinite
        expectancy = (win_rate * average_win) - ((Decimal('1') - win_rate) * average_loss)
        
        # Time-based calculations
        average_hold_time = timedelta(seconds=sum(t.hold_time.total_seconds() for t in trades) / total_trades)
        
        # Risk metrics (simplified calculations)
        max_drawdown = self._calculate_max_drawdown(trades)
        sharpe_ratio = self._calculate_sharpe_ratio(trades)
        calmar_ratio = self._calculate_calmar_ratio(total_pnl, max_drawdown, len(trades))
        
        # Returns
        total_return = total_pnl  # Simplified - would need account balance for proper calculation
        days_traded = (trades[-1].timestamp - trades[0].timestamp).days if len(trades) > 1 else 1
        annualized_return = total_return * Decimal('365') / Decimal(days_traded) if days_traded > 0 else Decimal('0')
        
        return PerformanceMetrics(
            total_trades=total_trades,
            win_count=win_count,
            loss_count=loss_count,
            win_rate=win_rate,
            profit_factor=profit_factor,
            expectancy=expectancy,
            sharpe_ratio=sharpe_ratio,
            calmar_ratio=calmar_ratio,
            max_drawdown=max_drawdown,
            average_win=average_win,
            average_loss=average_loss,
            average_hold_time=average_hold_time,
            total_return=total_return,
            annualized_return=annualized_return
        )
    
    def _calculate_max_drawdown(self, trades: List[Trade]) -> Decimal:
        """Calculate maximum drawdown from trade sequence."""
        if not trades:
            return Decimal('0')
        
        running_pnl = Decimal('0')
        peak = Decimal('0')
        max_drawdown = Decimal('0')
        
        for trade in trades:
            running_pnl += trade.pnl
            peak = max(peak, running_pnl)
            drawdown = peak - running_pnl
            max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown
    
    def _calculate_sharpe_ratio(self, trades: List[Trade]) -> Decimal:
        """Calculate Sharpe ratio (simplified version)."""
        if not trades or len(trades) < 2:
            return Decimal('0')
        
        returns = [trade.pnl for trade in trades]
        mean_return = sum(returns) / len(returns)
        
        # Calculate standard deviation
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = variance ** Decimal('0.5')
        
        if std_dev == 0:
            return Decimal('0')
        
        # Simplified Sharpe (assuming risk-free rate = 0)
        sharpe = mean_return / std_dev
        return sharpe
    
    def _calculate_calmar_ratio(self, total_return: Decimal, max_drawdown: Decimal, num_trades: int) -> Decimal:
        """Calculate Calmar ratio."""
        if max_drawdown == 0 or num_trades == 0:
            return Decimal('0')
        
        # Simplified Calmar ratio
        annualized_return = total_return * Decimal('252') / Decimal(num_trades)  # 252 trading days
        calmar = annualized_return / max_drawdown if max_drawdown > 0 else Decimal('0')
        return calmar
    
    async def _analyze_time_based_performance(self, trades: List[Trade]) -> TimeBasedPerformance:
        """Analyze performance across different time periods."""
        daily_performance = self._calculate_daily_performance(trades)
        weekly_performance = self._calculate_weekly_performance(trades)
        monthly_performance = self._calculate_monthly_performance(trades)
        
        # Rolling period calculations
        now = datetime.utcnow()
        rolling_30_trades = [t for t in trades if (now - t.timestamp).days <= 30]
        rolling_90_trades = [t for t in trades if (now - t.timestamp).days <= 90]
        rolling_365_trades = [t for t in trades if (now - t.timestamp).days <= 365]
        
        return TimeBasedPerformance(
            daily=daily_performance,
            weekly=weekly_performance,
            monthly=monthly_performance,
            rolling_30_day=self._calculate_performance_metrics(rolling_30_trades),
            rolling_90_day=self._calculate_performance_metrics(rolling_90_trades),
            rolling_365_day=self._calculate_performance_metrics(rolling_365_trades)
        )
    
    def _calculate_daily_performance(self, trades: List[Trade]) -> Dict[str, DailyPerformance]:
        """Calculate daily performance metrics."""
        daily_trades = {}
        
        for trade in trades:
            date_key = trade.timestamp.strftime('%Y-%m-%d')
            if date_key not in daily_trades:
                daily_trades[date_key] = []
            daily_trades[date_key].append(trade)
        
        daily_performance = {}
        for date, day_trades in daily_trades.items():
            wins = len([t for t in day_trades if t.win])
            total = len(day_trades)
            win_rate = Decimal(wins) / Decimal(total) if total > 0 else Decimal('0')
            
            pnl = sum(t.pnl for t in day_trades)
            
            # Calculate daily drawdown (simplified)
            running_pnl = Decimal('0')
            peak = Decimal('0')
            max_dd = Decimal('0')
            for trade in day_trades:
                running_pnl += trade.pnl
                peak = max(peak, running_pnl)
                max_dd = max(max_dd, peak - running_pnl)
            
            daily_performance[date] = DailyPerformance(
                date=datetime.strptime(date, '%Y-%m-%d'),
                trades=total,
                pnl=pnl,
                win_rate=win_rate,
                drawdown=max_dd
            )
        
        return daily_performance
    
    def _calculate_weekly_performance(self, trades: List[Trade]) -> Dict[str, WeeklyPerformance]:
        """Calculate weekly performance metrics."""
        weekly_trades = {}
        
        for trade in trades:
            # Get ISO week
            year, week, _ = trade.timestamp.isocalendar()
            week_key = f"{year:04d}-{week:02d}"
            if week_key not in weekly_trades:
                weekly_trades[week_key] = []
            weekly_trades[week_key].append(trade)
        
        weekly_performance = {}
        for week, week_trades in weekly_trades.items():
            metrics = self._calculate_performance_metrics(week_trades)
            weekly_performance[week] = WeeklyPerformance(
                week=week,
                trades=metrics.total_trades,
                pnl=metrics.total_return,
                win_rate=metrics.win_rate,
                sharpe_ratio=metrics.sharpe_ratio
            )
        
        return weekly_performance
    
    def _calculate_monthly_performance(self, trades: List[Trade]) -> Dict[str, MonthlyPerformance]:
        """Calculate monthly performance metrics."""
        monthly_trades = {}
        
        for trade in trades:
            month_key = trade.timestamp.strftime('%Y-%m')
            if month_key not in monthly_trades:
                monthly_trades[month_key] = []
            monthly_trades[month_key].append(trade)
        
        monthly_performance = {}
        for month, month_trades in monthly_trades.items():
            metrics = self._calculate_performance_metrics(month_trades)
            monthly_performance[month] = MonthlyPerformance(
                month=month,
                trades=metrics.total_trades,
                pnl=metrics.total_return,
                win_rate=metrics.win_rate,
                sharpe_ratio=metrics.sharpe_ratio,
                max_drawdown=metrics.max_drawdown
            )
        
        return monthly_performance
    
    async def _analyze_regime_performance(self, trades: List[Trade]) -> Dict[MarketRegime, RegimePerformance]:
        """Analyze strategy performance in different market regimes."""
        # This would integrate with the regime analyzer
        return await self.regime_analyzer.analyze_regime_performance(trades)
    
    async def _detect_performance_trend(self, trades: List[Trade]) -> PerformanceTrend:
        """Detect performance trends over time."""
        if len(trades) < 10:  # Need minimum trades for trend analysis
            return PerformanceTrend(
                direction=TrendDirection.STABLE,
                trend_strength=Decimal('0'),
                trend_duration=0,
                change_rate=Decimal('0'),
                projected_performance=Decimal('0')
            )
        
        # Split trades into recent and historical for comparison
        mid_point = len(trades) // 2
        historical_trades = trades[:mid_point]
        recent_trades = trades[mid_point:]
        
        historical_metrics = self._calculate_performance_metrics(historical_trades)
        recent_metrics = self._calculate_performance_metrics(recent_trades)
        
        # Compare key metrics to determine trend
        performance_change = recent_metrics.expectancy - historical_metrics.expectancy
        
        if performance_change > Decimal('0.1'):
            direction = TrendDirection.IMPROVING
            trend_strength = min(abs(performance_change), Decimal('1'))
        elif performance_change < Decimal('-0.1'):
            direction = TrendDirection.DECLINING
            trend_strength = min(abs(performance_change), Decimal('1'))
        else:
            direction = TrendDirection.STABLE
            trend_strength = Decimal('0.1')
        
        # Calculate trend duration (simplified)
        trend_duration = (trades[-1].timestamp - trades[mid_point].timestamp).days
        
        # Calculate change rate (performance change per day)
        change_rate = performance_change / Decimal(trend_duration) if trend_duration > 0 else Decimal('0')
        
        # Project 30-day performance
        projected_performance = recent_metrics.expectancy + (change_rate * Decimal('30'))
        
        return PerformanceTrend(
            direction=direction,
            trend_strength=trend_strength,
            trend_duration=trend_duration,
            change_rate=change_rate,
            projected_performance=projected_performance
        )
    
    async def _get_strategy_trades(self, strategy_id: str, evaluation_period: timedelta) -> List[Trade]:
        """
        Retrieve strategy trades for analysis.
        This would typically query a database or data service.
        """
        # Mock implementation - in production this would query actual trade data
        logger.info(f"Retrieving trades for strategy {strategy_id} over {evaluation_period}")
        
        # For now, return empty list - would be replaced with actual data retrieval
        return []
    
    async def _create_minimal_performance(self, strategy_id: str, trades: List[Trade]) -> StrategyPerformance:
        """Create minimal performance analysis when insufficient data."""
        return StrategyPerformance(
            strategy_id=strategy_id,
            overall=self._calculate_performance_metrics(trades),
            significance=StatisticalSignificance(
                sample_size=len(trades),
                confidence_level=self.confidence_level,
                p_value=Decimal('1.0'),  # Not significant
                confidence_interval=(Decimal('0'), Decimal('0')),
                statistically_significant=False,
                required_sample_size=self.min_trades_for_analysis,
                current_significance_level=Decimal('0')
            ),
            time_based=await self._analyze_time_based_performance(trades),
            regime_performance={},
            trend=PerformanceTrend(
                direction=TrendDirection.STABLE,
                trend_strength=Decimal('0'),
                trend_duration=0,
                change_rate=Decimal('0'),
                projected_performance=Decimal('0')
            ),
            last_updated=datetime.utcnow()
        )
    
    def _empty_performance_metrics(self) -> PerformanceMetrics:
        """Create empty performance metrics."""
        return PerformanceMetrics(
            total_trades=0,
            win_count=0,
            loss_count=0,
            win_rate=Decimal('0'),
            profit_factor=Decimal('0'),
            expectancy=Decimal('0'),
            sharpe_ratio=Decimal('0'),
            calmar_ratio=Decimal('0'),
            max_drawdown=Decimal('0'),
            average_win=Decimal('0'),
            average_loss=Decimal('0'),
            average_hold_time=timedelta(0),
            total_return=Decimal('0'),
            annualized_return=Decimal('0')
        )