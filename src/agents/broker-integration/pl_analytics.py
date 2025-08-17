"""
P&L Analytics Engine
Story 8.8 - Task 4: Create P&L analytics
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from dataclasses import dataclass, asdict
from collections import defaultdict
import statistics

try:
    from .transaction_manager import TransactionRecord, OandaTransactionManager
except ImportError:
    from transaction_manager import TransactionRecord, OandaTransactionManager

logger = logging.getLogger(__name__)


@dataclass
class DailyPLSummary:
    """Daily P&L summary statistics"""
    date: date
    gross_pl: Decimal
    commission: Decimal
    financing: Decimal
    net_pl: Decimal
    trade_count: int
    winning_trades: int
    losing_trades: int
    largest_win: Decimal
    largest_loss: Decimal
    win_rate: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        for key, value in result.items():
            if isinstance(value, Decimal):
                result[key] = float(value)
            elif isinstance(value, date):
                result[key] = value.isoformat()
        return result


@dataclass
class WeeklyPLSummary:
    """Weekly P&L summary statistics"""
    week_start: date
    week_end: date
    gross_pl: Decimal
    commission: Decimal
    financing: Decimal
    net_pl: Decimal
    trade_count: int
    daily_summaries: List[DailyPLSummary]
    best_day: Optional[DailyPLSummary]
    worst_day: Optional[DailyPLSummary]
    average_daily_pl: Decimal
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        result = {
            'week_start': self.week_start.isoformat(),
            'week_end': self.week_end.isoformat(),
            'gross_pl': float(self.gross_pl),
            'commission': float(self.commission),
            'financing': float(self.financing),
            'net_pl': float(self.net_pl),
            'trade_count': self.trade_count,
            'daily_summaries': [d.to_dict() for d in self.daily_summaries],
            'best_day': self.best_day.to_dict() if self.best_day else None,
            'worst_day': self.worst_day.to_dict() if self.worst_day else None,
            'average_daily_pl': float(self.average_daily_pl)
        }
        return result


@dataclass
class MonthlyPLSummary:
    """Monthly P&L summary statistics"""
    year: int
    month: int
    gross_pl: Decimal
    commission: Decimal
    financing: Decimal
    net_pl: Decimal
    trade_count: int
    winning_days: int
    losing_days: int
    daily_summaries: List[DailyPLSummary]
    weekly_summaries: List[WeeklyPLSummary]
    best_week: Optional[WeeklyPLSummary]
    worst_week: Optional[WeeklyPLSummary]
    sharpe_ratio: float
    max_drawdown: Decimal
    profit_factor: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        result = {
            'year': self.year,
            'month': self.month,
            'gross_pl': float(self.gross_pl),
            'commission': float(self.commission),
            'financing': float(self.financing),
            'net_pl': float(self.net_pl),
            'trade_count': self.trade_count,
            'winning_days': self.winning_days,
            'losing_days': self.losing_days,
            'daily_summaries': [d.to_dict() for d in self.daily_summaries],
            'weekly_summaries': [w.to_dict() for w in self.weekly_summaries],
            'best_week': self.best_week.to_dict() if self.best_week else None,
            'worst_week': self.worst_week.to_dict() if self.worst_week else None,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': float(self.max_drawdown),
            'profit_factor': self.profit_factor
        }
        return result


@dataclass
class PerformanceTrend:
    """Performance trend analysis"""
    period_start: date
    period_end: date
    trend_direction: str  # 'improving', 'declining', 'stable'
    pl_growth_rate: float
    win_rate_trend: float
    average_trade_size_trend: float
    consistency_score: float  # 0-100
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'trend_direction': self.trend_direction,
            'pl_growth_rate': self.pl_growth_rate,
            'win_rate_trend': self.win_rate_trend,
            'average_trade_size_trend': self.average_trade_size_trend,
            'consistency_score': self.consistency_score
        }


class PLAnalyticsEngine:
    """Analyzes P&L and performance metrics from transactions"""
    
    def __init__(self, transaction_manager: Optional[OandaTransactionManager] = None):
        self.transaction_manager = transaction_manager
        self.cache: Dict[str, Any] = {}
        self.cache_ttl = timedelta(minutes=30)
        self.last_cache_update: Dict[str, datetime] = {}
        
    async def calculate_daily_pl(self, 
                                transactions: List[TransactionRecord],
                                target_date: date) -> DailyPLSummary:
        """
        Calculate P&L for a specific day
        
        Args:
            transactions: List of transactions
            target_date: Date to calculate P&L for
            
        Returns:
            DailyPLSummary object
        """
        # Filter transactions for the target date
        day_transactions = [
            t for t in transactions 
            if t.timestamp.date() == target_date
        ]
        
        # Filter trade transactions
        trades = [
            t for t in day_transactions 
            if t.transaction_type in ['ORDER_FILL', 'TRADE_CLOSE']
        ]
        
        # Calculate metrics
        gross_pl = sum(t.pl for t in trades)
        commission = sum(t.commission for t in day_transactions)
        financing = sum(t.financing for t in day_transactions)
        net_pl = gross_pl - commission - financing
        
        winning_trades = [t for t in trades if t.pl > 0]
        losing_trades = [t for t in trades if t.pl < 0]
        
        largest_win = max((t.pl for t in winning_trades), default=Decimal('0'))
        largest_loss = min((t.pl for t in losing_trades), default=Decimal('0'))
        
        win_rate = len(winning_trades) / len(trades) * 100 if trades else 0
        
        return DailyPLSummary(
            date=target_date,
            gross_pl=gross_pl,
            commission=commission,
            financing=financing,
            net_pl=net_pl,
            trade_count=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            largest_win=largest_win,
            largest_loss=largest_loss,
            win_rate=win_rate
        )
        
    async def calculate_weekly_pl(self,
                                 transactions: List[TransactionRecord],
                                 week_start: date) -> WeeklyPLSummary:
        """
        Calculate weekly P&L summary
        
        Args:
            transactions: List of transactions
            week_start: Start date of the week (Monday)
            
        Returns:
            WeeklyPLSummary object
        """
        week_end = week_start + timedelta(days=6)
        
        # Calculate daily summaries for the week
        daily_summaries = []
        current_date = week_start
        
        while current_date <= week_end:
            daily_summary = await self.calculate_daily_pl(transactions, current_date)
            daily_summaries.append(daily_summary)
            current_date += timedelta(days=1)
            
        # Calculate weekly totals
        gross_pl = sum(d.gross_pl for d in daily_summaries)
        commission = sum(d.commission for d in daily_summaries)
        financing = sum(d.financing for d in daily_summaries)
        net_pl = sum(d.net_pl for d in daily_summaries)
        trade_count = sum(d.trade_count for d in daily_summaries)
        
        # Find best and worst days
        trading_days = [d for d in daily_summaries if d.trade_count > 0]
        best_day = max(trading_days, key=lambda x: x.net_pl) if trading_days else None
        worst_day = min(trading_days, key=lambda x: x.net_pl) if trading_days else None
        
        average_daily_pl = net_pl / len(trading_days) if trading_days else Decimal('0')
        
        return WeeklyPLSummary(
            week_start=week_start,
            week_end=week_end,
            gross_pl=gross_pl,
            commission=commission,
            financing=financing,
            net_pl=net_pl,
            trade_count=trade_count,
            daily_summaries=daily_summaries,
            best_day=best_day,
            worst_day=worst_day,
            average_daily_pl=average_daily_pl
        )
        
    async def calculate_monthly_pl(self,
                                  transactions: List[TransactionRecord],
                                  year: int,
                                  month: int) -> MonthlyPLSummary:
        """
        Calculate monthly P&L summary with advanced metrics
        
        Args:
            transactions: List of transactions
            year: Year
            month: Month (1-12)
            
        Returns:
            MonthlyPLSummary object
        """
        # Determine month boundaries
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)
            
        # Calculate daily summaries
        daily_summaries = []
        current_date = month_start
        
        while current_date <= month_end:
            daily_summary = await self.calculate_daily_pl(transactions, current_date)
            daily_summaries.append(daily_summary)
            current_date += timedelta(days=1)
            
        # Calculate weekly summaries
        weekly_summaries = []
        week_start = month_start - timedelta(days=month_start.weekday())  # Start from Monday
        
        while week_start <= month_end:
            week_summary = await self.calculate_weekly_pl(transactions, week_start)
            weekly_summaries.append(week_summary)
            week_start += timedelta(days=7)
            
        # Calculate monthly totals
        gross_pl = sum(d.gross_pl for d in daily_summaries)
        commission = sum(d.commission for d in daily_summaries)
        financing = sum(d.financing for d in daily_summaries)
        net_pl = sum(d.net_pl for d in daily_summaries)
        trade_count = sum(d.trade_count for d in daily_summaries)
        
        # Count winning/losing days
        winning_days = sum(1 for d in daily_summaries if d.net_pl > 0)
        losing_days = sum(1 for d in daily_summaries if d.net_pl < 0)
        
        # Find best and worst weeks
        trading_weeks = [w for w in weekly_summaries if w.trade_count > 0]
        best_week = max(trading_weeks, key=lambda x: x.net_pl) if trading_weeks else None
        worst_week = min(trading_weeks, key=lambda x: x.net_pl) if trading_weeks else None
        
        # Calculate advanced metrics
        sharpe_ratio = self._calculate_sharpe_ratio(daily_summaries)
        max_drawdown = self._calculate_max_drawdown(daily_summaries)
        profit_factor = self._calculate_profit_factor(transactions)
        
        return MonthlyPLSummary(
            year=year,
            month=month,
            gross_pl=gross_pl,
            commission=commission,
            financing=financing,
            net_pl=net_pl,
            trade_count=trade_count,
            winning_days=winning_days,
            losing_days=losing_days,
            daily_summaries=daily_summaries,
            weekly_summaries=weekly_summaries,
            best_week=best_week,
            worst_week=worst_week,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            profit_factor=profit_factor
        )
        
    def analyze_performance_trend(self,
                                 transactions: List[TransactionRecord],
                                 period_days: int = 30) -> PerformanceTrend:
        """
        Analyze performance trends over a period
        
        Args:
            transactions: List of transactions
            period_days: Number of days to analyze
            
        Returns:
            PerformanceTrend object
        """
        if not transactions:
            return PerformanceTrend(
                period_start=date.today(),
                period_end=date.today(),
                trend_direction='stable',
                pl_growth_rate=0.0,
                win_rate_trend=0.0,
                average_trade_size_trend=0.0,
                consistency_score=0.0
            )
            
        # Sort transactions by date
        sorted_transactions = sorted(transactions, key=lambda x: x.timestamp)
        
        period_end = sorted_transactions[-1].timestamp.date()
        period_start = period_end - timedelta(days=period_days)
        
        # Split period into halves for comparison
        mid_date = period_start + timedelta(days=period_days // 2)
        
        first_half = [t for t in sorted_transactions if period_start <= t.timestamp.date() < mid_date]
        second_half = [t for t in sorted_transactions if mid_date <= t.timestamp.date() <= period_end]
        
        # Calculate metrics for each half
        first_pl = sum(t.pl for t in first_half)
        second_pl = sum(t.pl for t in second_half)
        
        first_wins = len([t for t in first_half if t.pl > 0])
        second_wins = len([t for t in second_half if t.pl > 0])
        
        first_win_rate = first_wins / len(first_half) * 100 if first_half else 0
        second_win_rate = second_wins / len(second_half) * 100 if second_half else 0
        
        # Calculate trends
        pl_growth_rate = ((second_pl - first_pl) / abs(first_pl) * 100) if first_pl else 0
        win_rate_trend = second_win_rate - first_win_rate
        
        # Determine trend direction
        if pl_growth_rate > 10:
            trend_direction = 'improving'
        elif pl_growth_rate < -10:
            trend_direction = 'declining'
        else:
            trend_direction = 'stable'
            
        # Calculate consistency score
        consistency_score = self._calculate_consistency_score(sorted_transactions)
        
        return PerformanceTrend(
            period_start=period_start,
            period_end=period_end,
            trend_direction=trend_direction,
            pl_growth_rate=float(pl_growth_rate),
            win_rate_trend=win_rate_trend,
            average_trade_size_trend=0.0,  # Simplified for now
            consistency_score=consistency_score
        )
        
    def _calculate_sharpe_ratio(self, daily_summaries: List[DailyPLSummary]) -> float:
        """Calculate Sharpe ratio from daily returns"""
        returns = [float(d.net_pl) for d in daily_summaries if d.trade_count > 0]
        
        if len(returns) < 2:
            return 0.0
            
        avg_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)
        
        if std_return == 0:
            return 0.0
            
        # Annualized Sharpe ratio (assuming 252 trading days)
        return (avg_return / std_return) * (252 ** 0.5)
        
    def _calculate_max_drawdown(self, daily_summaries: List[DailyPLSummary]) -> Decimal:
        """Calculate maximum drawdown"""
        cumulative_pl = Decimal('0')
        peak = Decimal('0')
        max_drawdown = Decimal('0')
        
        for summary in daily_summaries:
            cumulative_pl += summary.net_pl
            
            if cumulative_pl > peak:
                peak = cumulative_pl
                
            drawdown = peak - cumulative_pl
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                
        return max_drawdown
        
    def _calculate_profit_factor(self, transactions: List[TransactionRecord]) -> float:
        """Calculate profit factor (gross profit / gross loss)"""
        gross_profit = sum(t.pl for t in transactions if t.pl > 0)
        gross_loss = abs(sum(t.pl for t in transactions if t.pl < 0))
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
            
        return float(gross_profit / gross_loss)
        
    def _calculate_consistency_score(self, transactions: List[TransactionRecord]) -> float:
        """
        Calculate consistency score (0-100)
        Based on win rate stability and P&L variance
        """
        if len(transactions) < 10:
            return 0.0
            
        # Group by day
        daily_pls = defaultdict(Decimal)
        for t in transactions:
            day = t.timestamp.date()
            daily_pls[day] += t.pl
            
        if len(daily_pls) < 5:
            return 0.0
            
        # Calculate coefficient of variation
        pls = list(daily_pls.values())
        mean_pl = statistics.mean(float(p) for p in pls)
        std_pl = statistics.stdev(float(p) for p in pls)
        
        if mean_pl <= 0:
            return 0.0
            
        cv = std_pl / mean_pl
        
        # Lower CV means more consistent
        # Map CV to 0-100 score (CV of 0 = 100, CV of 2+ = 0)
        consistency = max(0, min(100, (2 - cv) * 50))
        
        return consistency