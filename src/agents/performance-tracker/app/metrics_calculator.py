"""Performance metrics calculator for trading analytics."""

import logging
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from .models import (
    TradePerformance, PerformanceMetrics, PerformanceSnapshot,
    PeriodType, TradeStatus, PerformanceMetricsData
)

logger = logging.getLogger(__name__)


class PerformanceCalculator:
    """Core performance metrics calculation engine."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.risk_free_rate = Decimal('0.02')  # 2% annual risk-free rate
        
    def calculate_win_rate(self, trades: List[TradePerformance]) -> Decimal:
        """Calculate win rate: profitable trades / total trades."""
        if not trades:
            return Decimal('0')
        
        try:
            profitable_trades = len([t for t in trades if t.pnl and t.pnl > 0])
            total_trades = len(trades)
            
            win_rate = (Decimal(profitable_trades) / Decimal(total_trades)) * 100
            return win_rate.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            logger.error(f"Error calculating win rate: {e}")
            return Decimal('0')
    
    def calculate_profit_factor(self, trades: List[TradePerformance]) -> Decimal:
        """Calculate profit factor: gross profit / gross loss."""
        if not trades:
            return Decimal('0')
        
        try:
            gross_profit = sum([t.pnl for t in trades if t.pnl and t.pnl > 0])
            gross_loss = abs(sum([t.pnl for t in trades if t.pnl and t.pnl < 0]))
            
            if gross_loss == 0:
                return Decimal('999.99') if gross_profit > 0 else Decimal('0')
            
            profit_factor = gross_profit / gross_loss
            return profit_factor.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            logger.error(f"Error calculating profit factor: {e}")
            return Decimal('0')
    
    def calculate_sharpe_ratio(
        self, 
        returns: List[Decimal], 
        risk_free_rate: Optional[Decimal] = None
    ) -> Optional[Decimal]:
        """Calculate Sharpe ratio: (mean return - risk-free rate) / std deviation."""
        if not returns or len(returns) < 2:
            return None
        
        try:
            if risk_free_rate is None:
                risk_free_rate = self.risk_free_rate
            
            # Convert to numpy array for calculations
            returns_array = np.array([float(r) for r in returns])
            
            # Calculate daily risk-free rate
            daily_rf_rate = float(risk_free_rate) / 252
            
            # Calculate excess returns
            excess_returns = returns_array - daily_rf_rate
            
            # Calculate Sharpe ratio
            mean_excess_return = np.mean(excess_returns)
            std_excess_return = np.std(excess_returns, ddof=1)
            
            if std_excess_return == 0:
                return None
            
            # Annualize the Sharpe ratio
            sharpe_ratio = (mean_excess_return / std_excess_return) * np.sqrt(252)
            
            return Decimal(str(sharpe_ratio)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            return None
    
    def calculate_sortino_ratio(
        self, 
        returns: List[Decimal], 
        risk_free_rate: Optional[Decimal] = None
    ) -> Optional[Decimal]:
        """Calculate Sortino ratio: excess return / downside deviation."""
        if not returns or len(returns) < 2:
            return None
        
        try:
            if risk_free_rate is None:
                risk_free_rate = self.risk_free_rate
            
            returns_array = np.array([float(r) for r in returns])
            daily_rf_rate = float(risk_free_rate) / 252
            
            # Calculate excess returns
            excess_returns = returns_array - daily_rf_rate
            mean_excess_return = np.mean(excess_returns)
            
            # Calculate downside deviation (only negative returns)
            negative_returns = excess_returns[excess_returns < 0]
            
            if len(negative_returns) == 0:
                return None
            
            downside_deviation = np.sqrt(np.mean(negative_returns ** 2))
            
            if downside_deviation == 0:
                return None
            
            # Annualize the Sortino ratio
            sortino_ratio = (mean_excess_return / downside_deviation) * np.sqrt(252)
            
            return Decimal(str(sortino_ratio)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            logger.error(f"Error calculating Sortino ratio: {e}")
            return None
    
    def calculate_calmar_ratio(
        self, 
        annual_return: Decimal, 
        max_drawdown: Decimal
    ) -> Optional[Decimal]:
        """Calculate Calmar ratio: annual return / maximum drawdown."""
        try:
            if max_drawdown == 0:
                return None
            
            calmar_ratio = annual_return / abs(max_drawdown)
            return calmar_ratio.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            logger.error(f"Error calculating Calmar ratio: {e}")
            return None
    
    def calculate_maximum_drawdown(self, equity_curve: List[Tuple[datetime, Decimal]]) -> Decimal:
        """Calculate maximum drawdown from equity curve."""
        if not equity_curve or len(equity_curve) < 2:
            return Decimal('0')
        
        try:
            # Extract equity values
            equity_values = [float(eq[1]) for eq in equity_curve]
            equity_array = np.array(equity_values)
            
            # Calculate running maximum
            running_max = np.maximum.accumulate(equity_array)
            
            # Calculate drawdown at each point
            drawdown = (equity_array - running_max) / running_max * 100
            
            # Get maximum drawdown
            max_drawdown = np.min(drawdown)
            
            return Decimal(str(abs(max_drawdown))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            logger.error(f"Error calculating maximum drawdown: {e}")
            return Decimal('0')
    
    def calculate_var(self, returns: List[Decimal], confidence_level: Decimal = Decimal('0.95')) -> Optional[Decimal]:
        """Calculate Value at Risk at given confidence level."""
        if not returns or len(returns) < 10:
            return None
        
        try:
            returns_array = np.array([float(r) for r in returns])
            var_percentile = (1 - float(confidence_level)) * 100
            var = np.percentile(returns_array, var_percentile)
            
            return Decimal(str(abs(var))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            logger.error(f"Error calculating VaR: {e}")
            return None
    
    def calculate_beta(
        self, 
        portfolio_returns: List[Decimal], 
        benchmark_returns: List[Decimal]
    ) -> Optional[Decimal]:
        """Calculate beta relative to benchmark."""
        if not portfolio_returns or not benchmark_returns or len(portfolio_returns) != len(benchmark_returns):
            return None
        
        try:
            port_array = np.array([float(r) for r in portfolio_returns])
            bench_array = np.array([float(r) for r in benchmark_returns])
            
            # Calculate covariance and variance
            covariance = np.cov(port_array, bench_array)[0][1]
            benchmark_variance = np.var(bench_array, ddof=1)
            
            if benchmark_variance == 0:
                return None
            
            beta = covariance / benchmark_variance
            
            return Decimal(str(beta)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            logger.error(f"Error calculating beta: {e}")
            return None
    
    def get_trade_statistics(self, trades: List[TradePerformance]) -> Dict[str, Decimal]:
        """Calculate comprehensive trade statistics."""
        if not trades:
            return {
                'total_trades': Decimal('0'),
                'winning_trades': Decimal('0'),
                'losing_trades': Decimal('0'),
                'average_win': Decimal('0'),
                'average_loss': Decimal('0'),
                'largest_win': Decimal('0'),
                'largest_loss': Decimal('0'),
                'average_trade_duration': Decimal('0'),
                'total_commission': Decimal('0'),
                'total_swap': Decimal('0')
            }
        
        try:
            closed_trades = [t for t in trades if t.pnl is not None]
            winning_trades = [t for t in closed_trades if t.pnl > 0]
            losing_trades = [t for t in closed_trades if t.pnl < 0]
            
            # Basic counts
            total_trades = len(closed_trades)
            win_count = len(winning_trades)
            loss_count = len(losing_trades)
            
            # P&L statistics
            winning_pnls = [t.pnl for t in winning_trades] if winning_trades else [Decimal('0')]
            losing_pnls = [t.pnl for t in losing_trades] if losing_trades else [Decimal('0')]
            all_pnls = [t.pnl for t in closed_trades] if closed_trades else [Decimal('0')]
            
            average_win = sum(winning_pnls) / len(winning_pnls) if winning_trades else Decimal('0')
            average_loss = sum(losing_pnls) / len(losing_pnls) if losing_trades else Decimal('0')
            largest_win = max(all_pnls) if all_pnls else Decimal('0')
            largest_loss = min(all_pnls) if all_pnls else Decimal('0')
            
            # Duration statistics
            trades_with_duration = [t for t in closed_trades if t.trade_duration_seconds]
            average_duration = (
                sum([t.trade_duration_seconds for t in trades_with_duration]) / len(trades_with_duration)
                if trades_with_duration else 0
            )
            
            # Cost statistics
            total_commission = sum([t.commission or Decimal('0') for t in trades])
            total_swap = sum([t.swap or Decimal('0') for t in trades])
            
            return {
                'total_trades': Decimal(str(total_trades)),
                'winning_trades': Decimal(str(win_count)),
                'losing_trades': Decimal(str(loss_count)),
                'average_win': average_win.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'average_loss': average_loss.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'largest_win': largest_win,
                'largest_loss': largest_loss,
                'average_trade_duration': Decimal(str(average_duration)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'total_commission': total_commission,
                'total_swap': total_swap
            }
            
        except Exception as e:
            logger.error(f"Error calculating trade statistics: {e}")
            return {}


class PerformanceMetricsCalculator:
    """High-level performance metrics calculator and storage."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.calculator = PerformanceCalculator(db_session)
    
    async def calculate_period_metrics(
        self, 
        account_id: UUID, 
        period_start: datetime, 
        period_end: datetime,
        period_type: PeriodType
    ) -> PerformanceMetricsData:
        """Calculate comprehensive performance metrics for a period."""
        try:
            # Get trades for the period
            trades = self.db.query(TradePerformance).filter(
                and_(
                    TradePerformance.account_id == account_id,
                    TradePerformance.entry_time >= period_start,
                    TradePerformance.entry_time < period_end,
                    TradePerformance.status == TradeStatus.CLOSED.value
                )
            ).all()
            
            # Get basic trade statistics
            trade_stats = self.calculator.get_trade_statistics(trades)
            
            # Calculate performance metrics
            win_rate = self.calculator.calculate_win_rate(trades)
            profit_factor = self.calculator.calculate_profit_factor(trades)
            
            # Get equity curve for period
            equity_curve = await self._get_equity_curve(account_id, period_start, period_end)
            
            # Calculate risk metrics
            returns = self._calculate_daily_returns(equity_curve)
            sharpe_ratio = self.calculator.calculate_sharpe_ratio(returns)
            sortino_ratio = self.calculator.calculate_sortino_ratio(returns)
            max_drawdown = self.calculator.calculate_maximum_drawdown(equity_curve)
            
            # Calculate total P&L
            total_pnl = sum([t.pnl for t in trades if t.pnl]) if trades else Decimal('0')
            
            # Calculate annual return for Calmar ratio
            days_in_period = (period_end - period_start).days
            if days_in_period > 0:
                annualized_return = (total_pnl / days_in_period * 365) if total_pnl != 0 else Decimal('0')
                calmar_ratio = self.calculator.calculate_calmar_ratio(annualized_return, max_drawdown)
            else:
                calmar_ratio = None
            
            # Create metrics data
            metrics = PerformanceMetricsData(
                account_id=account_id,
                period_type=period_type,
                period_start=period_start,
                period_end=period_end,
                total_trades=int(trade_stats['total_trades']),
                winning_trades=int(trade_stats['winning_trades']),
                losing_trades=int(trade_stats['losing_trades']),
                win_rate=win_rate,
                profit_factor=profit_factor,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                calmar_ratio=calmar_ratio,
                max_drawdown=max_drawdown,
                total_pnl=total_pnl,
                average_win=trade_stats['average_win'],
                average_loss=trade_stats['average_loss'],
                largest_win=trade_stats['largest_win'],
                largest_loss=trade_stats['largest_loss']
            )
            
            # Store in database
            await self._store_metrics(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating period metrics for account {account_id}: {e}")
            raise
    
    async def calculate_all_periods_metrics(
        self, 
        account_id: UUID, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[PeriodType, List[PerformanceMetricsData]]:
        """Calculate metrics for all period types (daily, weekly, monthly)."""
        results = {}
        
        try:
            # Calculate daily metrics
            daily_metrics = []
            current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            while current_date < end_date:
                period_end = current_date + timedelta(days=1)
                if period_end > end_date:
                    period_end = end_date
                
                metrics = await self.calculate_period_metrics(
                    account_id, current_date, period_end, PeriodType.DAILY
                )
                daily_metrics.append(metrics)
                
                current_date += timedelta(days=1)
            
            results[PeriodType.DAILY] = daily_metrics
            
            # Calculate weekly metrics
            weekly_metrics = []
            current_week = start_date - timedelta(days=start_date.weekday())  # Start of week
            
            while current_week < end_date:
                week_end = current_week + timedelta(days=7)
                if week_end > end_date:
                    week_end = end_date
                
                metrics = await self.calculate_period_metrics(
                    account_id, current_week, week_end, PeriodType.WEEKLY
                )
                weekly_metrics.append(metrics)
                
                current_week += timedelta(days=7)
            
            results[PeriodType.WEEKLY] = weekly_metrics
            
            # Calculate monthly metrics
            monthly_metrics = []
            current_month = start_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            while current_month < end_date:
                # Get end of month
                if current_month.month == 12:
                    month_end = current_month.replace(year=current_month.year + 1, month=1)
                else:
                    month_end = current_month.replace(month=current_month.month + 1)
                
                if month_end > end_date:
                    month_end = end_date
                
                metrics = await self.calculate_period_metrics(
                    account_id, current_month, month_end, PeriodType.MONTHLY
                )
                monthly_metrics.append(metrics)
                
                current_month = month_end
            
            results[PeriodType.MONTHLY] = monthly_metrics
            
            return results
            
        except Exception as e:
            logger.error(f"Error calculating all period metrics: {e}")
            raise
    
    async def get_metrics_summary(
        self, 
        account_id: UUID, 
        period_type: PeriodType, 
        limit: int = 10
    ) -> List[PerformanceMetricsData]:
        """Get latest performance metrics summary."""
        try:
            metrics = self.db.query(PerformanceMetrics).filter(
                and_(
                    PerformanceMetrics.account_id == account_id,
                    PerformanceMetrics.period_type == period_type.value
                )
            ).order_by(desc(PerformanceMetrics.period_start)).limit(limit).all()
            
            result = []
            for metric in metrics:
                result.append(PerformanceMetricsData(
                    account_id=metric.account_id,
                    period_type=PeriodType(metric.period_type),
                    period_start=metric.period_start,
                    period_end=metric.period_end,
                    total_trades=metric.total_trades,
                    winning_trades=metric.winning_trades,
                    losing_trades=metric.losing_trades,
                    win_rate=metric.win_rate or Decimal('0'),
                    profit_factor=metric.profit_factor or Decimal('0'),
                    sharpe_ratio=metric.sharpe_ratio,
                    sortino_ratio=metric.sortino_ratio,
                    calmar_ratio=metric.calmar_ratio,
                    max_drawdown=metric.max_drawdown or Decimal('0'),
                    total_pnl=metric.total_pnl,
                    average_win=metric.average_win or Decimal('0'),
                    average_loss=metric.average_loss or Decimal('0'),
                    largest_win=metric.largest_win or Decimal('0'),
                    largest_loss=metric.largest_loss or Decimal('0')
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting metrics summary: {e}")
            return []
    
    async def _get_equity_curve(
        self, 
        account_id: UUID, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Tuple[datetime, Decimal]]:
        """Get equity curve for the period."""
        try:
            snapshots = self.db.query(PerformanceSnapshot).filter(
                and_(
                    PerformanceSnapshot.account_id == account_id,
                    PerformanceSnapshot.snapshot_time >= start_date,
                    PerformanceSnapshot.snapshot_time <= end_date
                )
            ).order_by(PerformanceSnapshot.snapshot_time).all()
            
            return [(snapshot.snapshot_time, snapshot.equity) for snapshot in snapshots]
            
        except Exception as e:
            logger.error(f"Error getting equity curve: {e}")
            return []
    
    def _calculate_daily_returns(self, equity_curve: List[Tuple[datetime, Decimal]]) -> List[Decimal]:
        """Calculate daily returns from equity curve."""
        if len(equity_curve) < 2:
            return []
        
        returns = []
        for i in range(1, len(equity_curve)):
            prev_equity = equity_curve[i-1][1]
            curr_equity = equity_curve[i][1]
            
            if prev_equity > 0:
                daily_return = (curr_equity - prev_equity) / prev_equity
                returns.append(daily_return)
        
        return returns
    
    async def _store_metrics(self, metrics: PerformanceMetricsData):
        """Store calculated metrics in database."""
        try:
            # Check if metrics already exist
            existing = self.db.query(PerformanceMetrics).filter(
                and_(
                    PerformanceMetrics.account_id == metrics.account_id,
                    PerformanceMetrics.period_type == metrics.period_type.value,
                    PerformanceMetrics.period_start == metrics.period_start
                )
            ).first()
            
            if existing:
                # Update existing metrics
                existing.total_trades = metrics.total_trades
                existing.winning_trades = metrics.winning_trades
                existing.losing_trades = metrics.losing_trades
                existing.win_rate = metrics.win_rate
                existing.profit_factor = metrics.profit_factor
                existing.sharpe_ratio = metrics.sharpe_ratio
                existing.sortino_ratio = metrics.sortino_ratio
                existing.calmar_ratio = metrics.calmar_ratio
                existing.max_drawdown = metrics.max_drawdown
                existing.total_pnl = metrics.total_pnl
                existing.average_win = metrics.average_win
                existing.average_loss = metrics.average_loss
                existing.largest_win = metrics.largest_win
                existing.largest_loss = metrics.largest_loss
            else:
                # Create new metrics record
                db_metrics = PerformanceMetrics(
                    account_id=metrics.account_id,
                    period_type=metrics.period_type.value,
                    period_start=metrics.period_start,
                    period_end=metrics.period_end,
                    total_trades=metrics.total_trades,
                    winning_trades=metrics.winning_trades,
                    losing_trades=metrics.losing_trades,
                    win_rate=metrics.win_rate,
                    profit_factor=metrics.profit_factor,
                    sharpe_ratio=metrics.sharpe_ratio,
                    sortino_ratio=metrics.sortino_ratio,
                    calmar_ratio=metrics.calmar_ratio,
                    max_drawdown=metrics.max_drawdown,
                    total_pnl=metrics.total_pnl,
                    average_win=metrics.average_win,
                    average_loss=metrics.average_loss,
                    largest_win=metrics.largest_win,
                    largest_loss=metrics.largest_loss
                )
                
                self.db.add(db_metrics)
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error storing metrics: {e}")
            self.db.rollback()
            raise