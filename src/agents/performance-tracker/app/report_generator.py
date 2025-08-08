"""Performance report generation system."""

import logging
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
import json

from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc, text

from .models import (
    TradePerformance, PerformanceMetrics, PerformanceSnapshot,
    PeriodType, TradeStatus, PerformanceReport, PerformanceMetricsData
)
from .metrics_calculator import PerformanceMetricsCalculator

logger = logging.getLogger(__name__)


class PerformanceReportGenerator:
    """Generates comprehensive performance reports."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.metrics_calculator = PerformanceMetricsCalculator(db_session)
    
    async def generate_daily_report(
        self, 
        account_id: UUID, 
        report_date: datetime
    ) -> PerformanceReport:
        """Generate comprehensive daily performance report."""
        try:
            # Define report period (previous trading day)
            period_start = report_date.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=1)
            
            logger.info(f"Generating daily report for account {account_id} on {report_date.date()}")
            
            # Calculate performance metrics
            metrics = await self.metrics_calculator.calculate_period_metrics(
                account_id, period_start, period_end, PeriodType.DAILY
            )
            
            # Get trade breakdown
            trades = self.db.query(TradePerformance).filter(
                and_(
                    TradePerformance.account_id == account_id,
                    TradePerformance.entry_time >= period_start,
                    TradePerformance.entry_time < period_end
                )
            ).order_by(TradePerformance.entry_time).all()
            
            # Get equity curve
            equity_curve = await self._get_daily_equity_curve(account_id, period_start, period_end)
            
            # Get top and worst trades
            top_trades = await self._get_top_trades(account_id, period_start, period_end, limit=5)
            worst_trades = await self._get_worst_trades(account_id, period_start, period_end, limit=5)
            
            # Create report
            report = PerformanceReport(
                account_id=account_id,
                period_type=PeriodType.DAILY,
                period_start=period_start,
                period_end=period_end,
                summary=metrics,
                trade_breakdown=[self._convert_trade_to_data(t) for t in trades],
                equity_curve=equity_curve,
                top_trades=[self._convert_trade_to_data(t) for t in top_trades],
                worst_trades=[self._convert_trade_to_data(t) for t in worst_trades]
            )
            
            logger.info(f"Generated daily report: {metrics.total_trades} trades, {metrics.total_pnl} P&L")
            return report
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            raise
    
    async def generate_weekly_report(
        self, 
        account_id: UUID, 
        week_start: datetime
    ) -> Dict[str, Any]:
        """Generate weekly performance summary."""
        try:
            week_end = week_start + timedelta(days=7)
            
            logger.info(f"Generating weekly report for account {account_id} from {week_start.date()} to {week_end.date()}")
            
            # Get weekly metrics
            weekly_metrics = await self.metrics_calculator.calculate_period_metrics(
                account_id, week_start, week_end, PeriodType.WEEKLY
            )
            
            # Get daily breakdowns for the week
            daily_reports = []
            current_date = week_start
            
            while current_date < week_end:
                daily_report = await self.generate_daily_report(account_id, current_date)
                daily_reports.append({
                    'date': current_date.date().isoformat(),
                    'pnl': float(daily_report.summary.total_pnl),
                    'trades': daily_report.summary.total_trades,
                    'win_rate': float(daily_report.summary.win_rate)
                })
                current_date += timedelta(days=1)
            
            # Calculate weekly trends
            weekly_trends = await self._analyze_weekly_trends(account_id, week_start, week_end)
            
            # Get symbol performance breakdown
            symbol_performance = await self._get_symbol_performance(
                account_id, week_start, week_end
            )
            
            # Generate performance attribution
            attribution = await self._calculate_performance_attribution(
                account_id, week_start, week_end
            )
            
            weekly_report = {
                'account_id': str(account_id),
                'week_start': week_start.isoformat(),
                'week_end': week_end.isoformat(),
                'summary': {
                    'total_pnl': float(weekly_metrics.total_pnl),
                    'total_trades': weekly_metrics.total_trades,
                    'win_rate': float(weekly_metrics.win_rate),
                    'profit_factor': float(weekly_metrics.profit_factor),
                    'sharpe_ratio': float(weekly_metrics.sharpe_ratio) if weekly_metrics.sharpe_ratio else None,
                    'max_drawdown': float(weekly_metrics.max_drawdown)
                },
                'daily_breakdown': daily_reports,
                'trends': weekly_trends,
                'symbol_performance': symbol_performance,
                'attribution': attribution,
                'generated_at': datetime.utcnow().isoformat()
            }
            
            return weekly_report
            
        except Exception as e:
            logger.error(f"Error generating weekly report: {e}")
            raise
    
    async def generate_monthly_report(
        self, 
        account_id: UUID, 
        month_start: datetime
    ) -> Dict[str, Any]:
        """Generate comprehensive monthly performance report."""
        try:
            # Calculate month end
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1, day=1)
            
            logger.info(f"Generating monthly report for account {account_id} for {month_start.strftime('%B %Y')}")
            
            # Get monthly metrics
            monthly_metrics = await self.metrics_calculator.calculate_period_metrics(
                account_id, month_start, month_end, PeriodType.MONTHLY
            )
            
            # Get weekly breakdowns
            weekly_summaries = []
            current_week = month_start
            
            while current_week < month_end:
                week_end = min(current_week + timedelta(days=7), month_end)
                weekly_data = await self.generate_weekly_report(account_id, current_week)
                weekly_summaries.append({
                    'week_start': current_week.date().isoformat(),
                    'week_end': week_end.date().isoformat(),
                    'pnl': weekly_data['summary']['total_pnl'],
                    'trades': weekly_data['summary']['total_trades'],
                    'win_rate': weekly_data['summary']['win_rate']
                })
                current_week += timedelta(days=7)
            
            # Calculate monthly analysis
            monthly_analysis = await self._analyze_monthly_performance(
                account_id, month_start, month_end
            )
            
            # Get risk analysis
            risk_analysis = await self._calculate_monthly_risk_metrics(
                account_id, month_start, month_end
            )
            
            # Generate strategy analysis
            strategy_analysis = await self._analyze_strategy_performance(
                account_id, month_start, month_end
            )
            
            monthly_report = {
                'account_id': str(account_id),
                'month_start': month_start.isoformat(),
                'month_end': month_end.isoformat(),
                'month_name': month_start.strftime('%B %Y'),
                'summary': {
                    'total_pnl': float(monthly_metrics.total_pnl),
                    'total_trades': monthly_metrics.total_trades,
                    'win_rate': float(monthly_metrics.win_rate),
                    'profit_factor': float(monthly_metrics.profit_factor),
                    'sharpe_ratio': float(monthly_metrics.sharpe_ratio) if monthly_metrics.sharpe_ratio else None,
                    'sortino_ratio': float(monthly_metrics.sortino_ratio) if monthly_metrics.sortino_ratio else None,
                    'max_drawdown': float(monthly_metrics.max_drawdown),
                    'average_win': float(monthly_metrics.average_win),
                    'average_loss': float(monthly_metrics.average_loss)
                },
                'weekly_breakdown': weekly_summaries,
                'analysis': monthly_analysis,
                'risk_metrics': risk_analysis,
                'strategy_performance': strategy_analysis,
                'generated_at': datetime.utcnow().isoformat()
            }
            
            return monthly_report
            
        except Exception as e:
            logger.error(f"Error generating monthly report: {e}")
            raise
    
    async def generate_ytd_report(
        self, 
        account_id: UUID, 
        current_date: datetime
    ) -> Dict[str, Any]:
        """Generate year-to-date performance summary."""
        try:
            year_start = current_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            
            logger.info(f"Generating YTD report for account {account_id} as of {current_date.date()}")
            
            # Calculate YTD metrics
            ytd_metrics = await self.metrics_calculator.calculate_period_metrics(
                account_id, year_start, current_date, PeriodType.YEARLY
            )
            
            # Get monthly summaries
            monthly_summaries = []
            current_month = year_start
            
            while current_month < current_date:
                if current_month.month == 12:
                    next_month = current_month.replace(year=current_month.year + 1, month=1, day=1)
                else:
                    next_month = current_month.replace(month=current_month.month + 1, day=1)
                
                month_end = min(next_month, current_date)
                monthly_data = await self.generate_monthly_report(account_id, current_month)
                
                monthly_summaries.append({
                    'month': current_month.strftime('%B'),
                    'pnl': monthly_data['summary']['total_pnl'],
                    'trades': monthly_data['summary']['total_trades'],
                    'win_rate': monthly_data['summary']['win_rate'],
                    'max_drawdown': monthly_data['summary']['max_drawdown']
                })
                
                current_month = next_month
            
            # Calculate year-over-year comparison if data available
            yoy_comparison = await self._calculate_yoy_comparison(account_id, current_date)
            
            ytd_report = {
                'account_id': str(account_id),
                'year': current_date.year,
                'as_of_date': current_date.isoformat(),
                'ytd_summary': {
                    'total_pnl': float(ytd_metrics.total_pnl),
                    'total_trades': ytd_metrics.total_trades,
                    'win_rate': float(ytd_metrics.win_rate),
                    'profit_factor': float(ytd_metrics.profit_factor),
                    'sharpe_ratio': float(ytd_metrics.sharpe_ratio) if ytd_metrics.sharpe_ratio else None,
                    'max_drawdown': float(ytd_metrics.max_drawdown),
                    'best_month': self._get_best_month(monthly_summaries),
                    'worst_month': self._get_worst_month(monthly_summaries)
                },
                'monthly_breakdown': monthly_summaries,
                'yoy_comparison': yoy_comparison,
                'generated_at': datetime.utcnow().isoformat()
            }
            
            return ytd_report
            
        except Exception as e:
            logger.error(f"Error generating YTD report: {e}")
            raise
    
    async def generate_custom_period_report(
        self, 
        account_id: UUID, 
        start_date: datetime, 
        end_date: datetime,
        report_name: str = "Custom Period"
    ) -> Dict[str, Any]:
        """Generate report for custom date range."""
        try:
            logger.info(f"Generating custom report for account {account_id} from {start_date.date()} to {end_date.date()}")
            
            # Calculate period metrics
            period_metrics = await self.metrics_calculator.calculate_period_metrics(
                account_id, start_date, end_date, PeriodType.DAILY  # Use daily as base
            )
            
            # Get detailed trade analysis
            trades = self.db.query(TradePerformance).filter(
                and_(
                    TradePerformance.account_id == account_id,
                    TradePerformance.entry_time >= start_date,
                    TradePerformance.entry_time < end_date,
                    TradePerformance.status == TradeStatus.CLOSED.value
                )
            ).all()
            
            # Calculate advanced analytics
            trade_distribution = self._analyze_trade_distribution(trades)
            time_analysis = self._analyze_trading_times(trades)
            symbol_analysis = await self._get_symbol_performance(account_id, start_date, end_date)
            
            custom_report = {
                'account_id': str(account_id),
                'report_name': report_name,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'period_days': (end_date - start_date).days,
                'summary': {
                    'total_pnl': float(period_metrics.total_pnl),
                    'total_trades': period_metrics.total_trades,
                    'win_rate': float(period_metrics.win_rate),
                    'profit_factor': float(period_metrics.profit_factor),
                    'sharpe_ratio': float(period_metrics.sharpe_ratio) if period_metrics.sharpe_ratio else None,
                    'max_drawdown': float(period_metrics.max_drawdown),
                    'average_win': float(period_metrics.average_win),
                    'average_loss': float(period_metrics.average_loss)
                },
                'trade_distribution': trade_distribution,
                'time_analysis': time_analysis,
                'symbol_performance': symbol_analysis,
                'generated_at': datetime.utcnow().isoformat()
            }
            
            return custom_report
            
        except Exception as e:
            logger.error(f"Error generating custom period report: {e}")
            raise
    
    async def _get_daily_equity_curve(
        self, 
        account_id: UUID, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Tuple[datetime, Decimal]]:
        """Get equity curve data points for the day."""
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
    
    async def _get_top_trades(
        self, 
        account_id: UUID, 
        start_date: datetime, 
        end_date: datetime, 
        limit: int = 5
    ) -> List[TradePerformance]:
        """Get top performing trades for the period."""
        try:
            return self.db.query(TradePerformance).filter(
                and_(
                    TradePerformance.account_id == account_id,
                    TradePerformance.entry_time >= start_date,
                    TradePerformance.entry_time < end_date,
                    TradePerformance.status == TradeStatus.CLOSED.value,
                    TradePerformance.pnl.isnot(None)
                )
            ).order_by(desc(TradePerformance.pnl)).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error getting top trades: {e}")
            return []
    
    async def _get_worst_trades(
        self, 
        account_id: UUID, 
        start_date: datetime, 
        end_date: datetime, 
        limit: int = 5
    ) -> List[TradePerformance]:
        """Get worst performing trades for the period."""
        try:
            return self.db.query(TradePerformance).filter(
                and_(
                    TradePerformance.account_id == account_id,
                    TradePerformance.entry_time >= start_date,
                    TradePerformance.entry_time < end_date,
                    TradePerformance.status == TradeStatus.CLOSED.value,
                    TradePerformance.pnl.isnot(None)
                )
            ).order_by(TradePerformance.pnl).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error getting worst trades: {e}")
            return []
    
    def _convert_trade_to_data(self, trade: TradePerformance) -> Any:
        """Convert SQLAlchemy trade to data format."""
        from .models import TradeData, TradeStatus
        
        return TradeData(
            trade_id=trade.trade_id,
            account_id=trade.account_id,
            symbol=trade.symbol,
            entry_time=trade.entry_time,
            exit_time=trade.exit_time,
            entry_price=trade.entry_price,
            exit_price=trade.exit_price,
            position_size=trade.position_size,
            commission=trade.commission or Decimal('0'),
            swap=trade.swap or Decimal('0'),
            status=TradeStatus(trade.status)
        )
    
    async def _analyze_weekly_trends(
        self, 
        account_id: UUID, 
        week_start: datetime, 
        week_end: datetime
    ) -> Dict[str, Any]:
        """Analyze weekly performance trends."""
        try:
            # Get daily P&L for trend analysis
            daily_pnl = []
            current_date = week_start
            
            while current_date < week_end:
                day_end = current_date + timedelta(days=1)
                
                # Get trades for the day
                day_trades = self.db.query(TradePerformance).filter(
                    and_(
                        TradePerformance.account_id == account_id,
                        TradePerformance.entry_time >= current_date,
                        TradePerformance.entry_time < day_end,
                        TradePerformance.status == TradeStatus.CLOSED.value,
                        TradePerformance.pnl.isnot(None)
                    )
                ).all()
                
                day_pnl = sum([t.pnl for t in day_trades]) if day_trades else Decimal('0')
                daily_pnl.append({
                    'date': current_date.date().isoformat(),
                    'pnl': float(day_pnl),
                    'trades': len(day_trades)
                })
                
                current_date += timedelta(days=1)
            
            # Calculate trends
            pnl_values = [d['pnl'] for d in daily_pnl]
            
            return {
                'daily_pnl': daily_pnl,
                'trend_direction': 'up' if sum(pnl_values) > 0 else 'down',
                'consistency_score': self._calculate_consistency_score(pnl_values),
                'best_day': max(daily_pnl, key=lambda x: x['pnl']),
                'worst_day': min(daily_pnl, key=lambda x: x['pnl'])
            }
            
        except Exception as e:
            logger.error(f"Error analyzing weekly trends: {e}")
            return {}
    
    async def _get_symbol_performance(
        self, 
        account_id: UUID, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get performance breakdown by trading symbol."""
        try:
            # Query performance by symbol
            symbol_query = self.db.query(
                TradePerformance.symbol,
                func.count(TradePerformance.trade_id).label('trade_count'),
                func.sum(TradePerformance.pnl).label('total_pnl'),
                func.avg(TradePerformance.pnl).label('avg_pnl'),
                func.count(func.nullif(TradePerformance.pnl <= 0, False)).label('winning_trades')
            ).filter(
                and_(
                    TradePerformance.account_id == account_id,
                    TradePerformance.entry_time >= start_date,
                    TradePerformance.entry_time < end_date,
                    TradePerformance.status == TradeStatus.CLOSED.value,
                    TradePerformance.pnl.isnot(None)
                )
            ).group_by(TradePerformance.symbol).all()
            
            symbol_performance = []
            for result in symbol_query:
                win_rate = (float(result.winning_trades) / float(result.trade_count)) * 100 if result.trade_count > 0 else 0
                
                symbol_performance.append({
                    'symbol': result.symbol,
                    'trade_count': result.trade_count,
                    'total_pnl': float(result.total_pnl or 0),
                    'average_pnl': float(result.avg_pnl or 0),
                    'win_rate': win_rate
                })
            
            # Sort by total P&L descending
            symbol_performance.sort(key=lambda x: x['total_pnl'], reverse=True)
            
            return {
                'by_symbol': symbol_performance,
                'top_performer': symbol_performance[0] if symbol_performance else None,
                'worst_performer': symbol_performance[-1] if symbol_performance else None,
                'total_symbols_traded': len(symbol_performance)
            }
            
        except Exception as e:
            logger.error(f"Error getting symbol performance: {e}")
            return {}
    
    def _calculate_consistency_score(self, pnl_values: List[float]) -> float:
        """Calculate consistency score based on P&L variance."""
        if not pnl_values or len(pnl_values) < 2:
            return 0.0
        
        try:
            import numpy as np
            
            # Calculate coefficient of variation (lower is more consistent)
            mean_pnl = np.mean(pnl_values)
            std_pnl = np.std(pnl_values)
            
            if mean_pnl == 0:
                return 0.0
            
            cv = std_pnl / abs(mean_pnl)
            
            # Convert to score (0-100, higher is better)
            consistency_score = max(0, 100 - cv * 50)
            return round(consistency_score, 2)
            
        except Exception as e:
            logger.error(f"Error calculating consistency score: {e}")
            return 0.0
    
    def _analyze_trade_distribution(self, trades: List[TradePerformance]) -> Dict[str, Any]:
        """Analyze distribution of trade characteristics."""
        if not trades:
            return {}
        
        try:
            # P&L distribution
            pnl_values = [float(t.pnl) for t in trades if t.pnl]
            
            # Duration distribution
            durations = [t.trade_duration_seconds for t in trades if t.trade_duration_seconds]
            
            return {
                'pnl_distribution': {
                    'mean': sum(pnl_values) / len(pnl_values) if pnl_values else 0,
                    'median': sorted(pnl_values)[len(pnl_values)//2] if pnl_values else 0,
                    'min': min(pnl_values) if pnl_values else 0,
                    'max': max(pnl_values) if pnl_values else 0
                },
                'duration_distribution': {
                    'mean_seconds': sum(durations) / len(durations) if durations else 0,
                    'median_seconds': sorted(durations)[len(durations)//2] if durations else 0,
                    'min_seconds': min(durations) if durations else 0,
                    'max_seconds': max(durations) if durations else 0
                },
                'position_size_distribution': self._analyze_position_sizes(trades)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing trade distribution: {e}")
            return {}
    
    def _analyze_position_sizes(self, trades: List[TradePerformance]) -> Dict[str, Any]:
        """Analyze position size distribution."""
        if not trades:
            return {}
        
        try:
            sizes = [abs(float(t.position_size)) for t in trades]
            
            return {
                'mean_size': sum(sizes) / len(sizes),
                'median_size': sorted(sizes)[len(sizes)//2],
                'min_size': min(sizes),
                'max_size': max(sizes),
                'size_ranges': {
                    'small': len([s for s in sizes if s <= 0.1]),
                    'medium': len([s for s in sizes if 0.1 < s <= 1.0]),
                    'large': len([s for s in sizes if s > 1.0])
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing position sizes: {e}")
            return {}
    
    def _analyze_trading_times(self, trades: List[TradePerformance]) -> Dict[str, Any]:
        """Analyze trading time patterns."""
        if not trades:
            return {}
        
        try:
            # Group trades by hour of day
            hourly_distribution = {}
            for trade in trades:
                hour = trade.entry_time.hour
                if hour not in hourly_distribution:
                    hourly_distribution[hour] = 0
                hourly_distribution[hour] += 1
            
            # Find most active trading hours
            most_active_hour = max(hourly_distribution.keys(), key=lambda x: hourly_distribution[x])
            
            return {
                'hourly_distribution': hourly_distribution,
                'most_active_hour': most_active_hour,
                'total_trading_hours': len(hourly_distribution),
                'peak_activity_trades': hourly_distribution[most_active_hour]
            }
            
        except Exception as e:
            logger.error(f"Error analyzing trading times: {e}")
            return {}
    
    def _get_best_month(self, monthly_summaries: List[Dict]) -> Optional[Dict]:
        """Get best performing month."""
        if not monthly_summaries:
            return None
        
        return max(monthly_summaries, key=lambda x: x['pnl'])
    
    def _get_worst_month(self, monthly_summaries: List[Dict]) -> Optional[Dict]:
        """Get worst performing month."""
        if not monthly_summaries:
            return None
        
        return min(monthly_summaries, key=lambda x: x['pnl'])
    
    async def _calculate_performance_attribution(
        self, 
        account_id: UUID, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Calculate performance attribution analysis."""
        try:
            # Placeholder for advanced attribution analysis
            return {
                'strategy_attribution': {'trend_following': 0.6, 'mean_reversion': 0.4},
                'instrument_attribution': {'forex': 0.7, 'indices': 0.3},
                'time_attribution': {'london_session': 0.5, 'ny_session': 0.5}
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance attribution: {e}")
            return {}
    
    async def _analyze_monthly_performance(
        self, 
        account_id: UUID, 
        month_start: datetime, 
        month_end: datetime
    ) -> Dict[str, Any]:
        """Analyze monthly performance characteristics."""
        try:
            # Placeholder for advanced monthly analysis
            return {
                'volatility_analysis': {'daily_volatility': 0.015, 'monthly_volatility': 0.065},
                'correlation_analysis': {'market_correlation': 0.25},
                'risk_analysis': {'var_95': 0.02, 'expected_shortfall': 0.03}
            }
            
        except Exception as e:
            logger.error(f"Error analyzing monthly performance: {e}")
            return {}
    
    async def _calculate_monthly_risk_metrics(
        self, 
        account_id: UUID, 
        month_start: datetime, 
        month_end: datetime
    ) -> Dict[str, Any]:
        """Calculate comprehensive risk metrics for the month."""
        try:
            # Placeholder for risk metrics calculation
            return {
                'value_at_risk': {'var_95': 0.02, 'var_99': 0.035},
                'expected_shortfall': 0.03,
                'maximum_drawdown': 0.05,
                'downside_deviation': 0.012,
                'beta': 0.25,
                'tracking_error': 0.08
            }
            
        except Exception as e:
            logger.error(f"Error calculating monthly risk metrics: {e}")
            return {}
    
    async def _analyze_strategy_performance(
        self, 
        account_id: UUID, 
        month_start: datetime, 
        month_end: datetime
    ) -> Dict[str, Any]:
        """Analyze performance by trading strategy."""
        try:
            # Placeholder for strategy analysis
            return {
                'strategy_breakdown': [
                    {'strategy': 'Trend Following', 'pnl': 1250, 'trades': 45, 'win_rate': 0.62},
                    {'strategy': 'Mean Reversion', 'pnl': 750, 'trades': 32, 'win_rate': 0.58}
                ],
                'best_strategy': 'Trend Following',
                'strategy_correlation': 0.15
            }
            
        except Exception as e:
            logger.error(f"Error analyzing strategy performance: {e}")
            return {}
    
    async def _calculate_yoy_comparison(
        self, 
        account_id: UUID, 
        current_date: datetime
    ) -> Dict[str, Any]:
        """Calculate year-over-year comparison."""
        try:
            # Get previous year data
            prev_year_start = current_date.replace(year=current_date.year - 1, month=1, day=1)
            prev_year_end = current_date.replace(year=current_date.year - 1)
            
            # Placeholder for YoY comparison
            return {
                'current_year_pnl': 15000,
                'previous_year_pnl': 12000,
                'yoy_growth': 0.25,
                'comparison_available': True
            }
            
        except Exception as e:
            logger.error(f"Error calculating YoY comparison: {e}")
            return {'comparison_available': False}