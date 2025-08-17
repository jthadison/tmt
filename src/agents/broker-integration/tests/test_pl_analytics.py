"""
Tests for P&L Analytics Engine
Story 8.8 - Task 4 tests
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pl_analytics import (
    PLAnalyticsEngine, DailyPLSummary, WeeklyPLSummary, MonthlyPLSummary, PerformanceTrend
)
from transaction_manager import TransactionRecord


class TestPLAnalyticsEngine:
    """Test suite for PLAnalyticsEngine"""
    
    @pytest.fixture
    def analytics_engine(self):
        """Analytics engine instance"""
        return PLAnalyticsEngine()
        
    @pytest.fixture
    def sample_transactions(self):
        """Sample transaction data for testing"""
        base_time = datetime(2024, 1, 15, 10, 0)
        
        return [
            TransactionRecord(
                transaction_id="1",
                transaction_type="ORDER_FILL",
                instrument="EUR_USD",
                units=Decimal("1000"),
                price=Decimal("1.1000"),
                pl=Decimal("10.50"),
                commission=Decimal("0.50"),
                financing=Decimal("0.00"),
                timestamp=base_time,
                account_balance=Decimal("1010.00"),
                reason="MARKET_ORDER"
            ),
            TransactionRecord(
                transaction_id="2",
                transaction_type="TRADE_CLOSE",
                instrument="GBP_USD",
                units=Decimal("-500"),
                price=Decimal("1.2500"),
                pl=Decimal("-5.25"),
                commission=Decimal("0.25"),
                financing=Decimal("0.10"),
                timestamp=base_time + timedelta(hours=1),
                account_balance=Decimal("1004.50"),
                reason="STOP_LOSS"
            ),
            TransactionRecord(
                transaction_id="3",
                transaction_type="ORDER_FILL",
                instrument="USD_JPY",
                units=Decimal("2000"),
                price=Decimal("110.00"),
                pl=Decimal("15.75"),
                commission=Decimal("0.75"),
                financing=Decimal("0.00"),
                timestamp=base_time + timedelta(hours=2),
                account_balance=Decimal("1019.50"),
                reason="MARKET_ORDER"
            ),
            TransactionRecord(
                transaction_id="4",
                transaction_type="DAILY_FINANCING",
                instrument=None,
                units=Decimal("0"),
                price=Decimal("0"),
                pl=Decimal("0"),
                commission=Decimal("0"),
                financing=Decimal("-1.50"),
                timestamp=base_time + timedelta(hours=3),
                account_balance=Decimal("1018.00"),
                reason="DAILY_FINANCING"
            )
        ]
        
    @pytest.mark.asyncio
    async def test_calculate_daily_pl(self, analytics_engine, sample_transactions):
        """Test daily P&L calculation"""
        target_date = date(2024, 1, 15)
        
        daily_summary = await analytics_engine.calculate_daily_pl(
            sample_transactions, target_date
        )
        
        assert daily_summary.date == target_date
        assert daily_summary.gross_pl == Decimal("21.00")  # 10.50 - 5.25 + 15.75
        assert daily_summary.commission == Decimal("1.50")  # 0.50 + 0.25 + 0.75
        assert daily_summary.financing == Decimal("-1.40")  # 0.00 + 0.10 + 0.00 + (-1.50)
        assert daily_summary.net_pl == Decimal("18.10")  # 21.00 - 1.50 + 1.40
        assert daily_summary.trade_count == 3  # Excluding financing
        assert daily_summary.winning_trades == 2
        assert daily_summary.losing_trades == 1
        assert daily_summary.largest_win == Decimal("15.75")
        assert daily_summary.largest_loss == Decimal("-5.25")
        assert daily_summary.win_rate == pytest.approx(66.67, rel=1e-2)
        
    @pytest.mark.asyncio
    async def test_calculate_daily_pl_no_trades(self, analytics_engine):
        """Test daily P&L calculation with no trades"""
        target_date = date(2024, 1, 16)
        
        daily_summary = await analytics_engine.calculate_daily_pl([], target_date)
        
        assert daily_summary.date == target_date
        assert daily_summary.gross_pl == Decimal("0")
        assert daily_summary.commission == Decimal("0")
        assert daily_summary.financing == Decimal("0")
        assert daily_summary.net_pl == Decimal("0")
        assert daily_summary.trade_count == 0
        assert daily_summary.winning_trades == 0
        assert daily_summary.losing_trades == 0
        assert daily_summary.win_rate == 0
        
    @pytest.mark.asyncio
    async def test_calculate_weekly_pl(self, analytics_engine, sample_transactions):
        """Test weekly P&L calculation"""
        week_start = date(2024, 1, 15)  # Monday
        
        weekly_summary = await analytics_engine.calculate_weekly_pl(
            sample_transactions, week_start
        )
        
        assert weekly_summary.week_start == week_start
        assert weekly_summary.week_end == week_start + timedelta(days=6)
        assert weekly_summary.gross_pl == Decimal("21.00")
        assert weekly_summary.commission == Decimal("1.50")
        assert weekly_summary.financing == Decimal("-1.40")
        assert weekly_summary.net_pl == Decimal("18.10")
        assert weekly_summary.trade_count == 3
        assert len(weekly_summary.daily_summaries) == 7  # Full week
        
        # Check best/worst days
        assert weekly_summary.best_day is not None
        assert weekly_summary.worst_day is not None
        assert weekly_summary.best_day.net_pl >= weekly_summary.worst_day.net_pl
        
    @pytest.mark.asyncio
    async def test_calculate_monthly_pl(self, analytics_engine, sample_transactions):
        """Test monthly P&L calculation"""
        year = 2024
        month = 1
        
        monthly_summary = await analytics_engine.calculate_monthly_pl(
            sample_transactions, year, month
        )
        
        assert monthly_summary.year == year
        assert monthly_summary.month == month
        assert monthly_summary.gross_pl == Decimal("21.00")
        assert monthly_summary.commission == Decimal("1.50")
        assert monthly_summary.financing == Decimal("-1.40")
        assert monthly_summary.net_pl == Decimal("18.10")
        assert monthly_summary.trade_count == 3
        
        # Check daily summaries for full month
        assert len(monthly_summary.daily_summaries) == 31  # January has 31 days
        
        # Check that we have winning/losing days counts
        assert monthly_summary.winning_days >= 0
        assert monthly_summary.losing_days >= 0
        
        # Check advanced metrics
        assert isinstance(monthly_summary.sharpe_ratio, float)
        assert isinstance(monthly_summary.max_drawdown, Decimal)
        assert isinstance(monthly_summary.profit_factor, float)
        
    def test_calculate_sharpe_ratio(self, analytics_engine):
        """Test Sharpe ratio calculation"""
        daily_summaries = [
            DailyPLSummary(
                date=date(2024, 1, 1),
                gross_pl=Decimal("10"),
                commission=Decimal("1"),
                financing=Decimal("0"),
                net_pl=Decimal("9"),
                trade_count=1,
                winning_trades=1,
                losing_trades=0,
                largest_win=Decimal("10"),
                largest_loss=Decimal("0"),
                win_rate=100.0
            ),
            DailyPLSummary(
                date=date(2024, 1, 2),
                gross_pl=Decimal("-5"),
                commission=Decimal("1"),
                financing=Decimal("0"),
                net_pl=Decimal("-6"),
                trade_count=1,
                winning_trades=0,
                losing_trades=1,
                largest_win=Decimal("0"),
                largest_loss=Decimal("-5"),
                win_rate=0.0
            ),
            DailyPLSummary(
                date=date(2024, 1, 3),
                gross_pl=Decimal("15"),
                commission=Decimal("1"),
                financing=Decimal("0"),
                net_pl=Decimal("14"),
                trade_count=1,
                winning_trades=1,
                losing_trades=0,
                largest_win=Decimal("15"),
                largest_loss=Decimal("0"),
                win_rate=100.0
            )
        ]
        
        sharpe_ratio = analytics_engine._calculate_sharpe_ratio(daily_summaries)
        
        # Should be a reasonable positive number for profitable trading
        assert isinstance(sharpe_ratio, float)
        assert sharpe_ratio > 0
        
    def test_calculate_max_drawdown(self, analytics_engine):
        """Test maximum drawdown calculation"""
        daily_summaries = [
            DailyPLSummary(
                date=date(2024, 1, 1),
                gross_pl=Decimal("0"),
                commission=Decimal("0"),
                financing=Decimal("0"),
                net_pl=Decimal("10"),  # Cumulative: 10
                trade_count=1,
                winning_trades=1,
                losing_trades=0,
                largest_win=Decimal("10"),
                largest_loss=Decimal("0"),
                win_rate=100.0
            ),
            DailyPLSummary(
                date=date(2024, 1, 2),
                gross_pl=Decimal("0"),
                commission=Decimal("0"),
                financing=Decimal("0"),
                net_pl=Decimal("20"),  # Cumulative: 30 (new peak)
                trade_count=1,
                winning_trades=1,
                losing_trades=0,
                largest_win=Decimal("20"),
                largest_loss=Decimal("0"),
                win_rate=100.0
            ),
            DailyPLSummary(
                date=date(2024, 1, 3),
                gross_pl=Decimal("0"),
                commission=Decimal("0"),
                financing=Decimal("0"),
                net_pl=Decimal("-15"),  # Cumulative: 15 (drawdown of 15 from peak)
                trade_count=1,
                winning_trades=0,
                losing_trades=1,
                largest_win=Decimal("0"),
                largest_loss=Decimal("-15"),
                win_rate=0.0
            )
        ]
        
        max_drawdown = analytics_engine._calculate_max_drawdown(daily_summaries)
        
        assert max_drawdown == Decimal("15")
        
    def test_calculate_profit_factor(self, analytics_engine):
        """Test profit factor calculation"""
        transactions = [
            TransactionRecord(
                transaction_id="1",
                transaction_type="ORDER_FILL",
                instrument="EUR_USD",
                units=Decimal("1000"),
                price=Decimal("1.1000"),
                pl=Decimal("20.00"),  # Profit
                commission=Decimal("0.50"),
                financing=Decimal("0.00"),
                timestamp=datetime(2024, 1, 15, 10, 0),
                account_balance=Decimal("1020.00"),
                reason="MARKET_ORDER"
            ),
            TransactionRecord(
                transaction_id="2",
                transaction_type="TRADE_CLOSE",
                instrument="GBP_USD",
                units=Decimal("-500"),
                price=Decimal("1.2500"),
                pl=Decimal("-10.00"),  # Loss
                commission=Decimal("0.25"),
                financing=Decimal("0.00"),
                timestamp=datetime(2024, 1, 15, 11, 0),
                account_balance=Decimal("1009.75"),
                reason="STOP_LOSS"
            )
        ]
        
        profit_factor = analytics_engine._calculate_profit_factor(transactions)
        
        # Profit factor = 20.00 / 10.00 = 2.0
        assert profit_factor == 2.0
        
    def test_analyze_performance_trend(self, analytics_engine, sample_transactions):
        """Test performance trend analysis"""
        trend = analytics_engine.analyze_performance_trend(sample_transactions, period_days=1)
        
        assert isinstance(trend, PerformanceTrend)
        assert trend.trend_direction in ['improving', 'declining', 'stable']
        assert isinstance(trend.pl_growth_rate, float)
        assert isinstance(trend.win_rate_trend, float)
        assert isinstance(trend.consistency_score, float)
        assert 0 <= trend.consistency_score <= 100
        
    def test_analyze_performance_trend_empty(self, analytics_engine):
        """Test trend analysis with no transactions"""
        trend = analytics_engine.analyze_performance_trend([], period_days=30)
        
        assert trend.trend_direction == 'stable'
        assert trend.pl_growth_rate == 0.0
        assert trend.win_rate_trend == 0.0
        assert trend.consistency_score == 0.0
        
    def test_calculate_consistency_score(self, analytics_engine):
        """Test consistency score calculation"""
        # Create transactions with consistent daily P&L
        transactions = []
        base_time = datetime(2024, 1, 1, 10, 0)
        
        for i in range(10):
            transactions.append(
                TransactionRecord(
                    transaction_id=str(i),
                    transaction_type="ORDER_FILL",
                    instrument="EUR_USD",
                    units=Decimal("1000"),
                    price=Decimal("1.1000"),
                    pl=Decimal("10.00"),  # Consistent profit
                    commission=Decimal("0.50"),
                    financing=Decimal("0.00"),
                    timestamp=base_time + timedelta(days=i),
                    account_balance=Decimal("1000.00"),
                    reason="MARKET_ORDER"
                )
            )
            
        consistency_score = analytics_engine._calculate_consistency_score(transactions)
        
        # Should be high for consistent performance
        assert consistency_score > 80
        
    def test_serialization(self):
        """Test that summary objects can be serialized to dict"""
        daily_summary = DailyPLSummary(
            date=date(2024, 1, 15),
            gross_pl=Decimal("10.50"),
            commission=Decimal("0.50"),
            financing=Decimal("0.00"),
            net_pl=Decimal("10.00"),
            trade_count=1,
            winning_trades=1,
            losing_trades=0,
            largest_win=Decimal("10.50"),
            largest_loss=Decimal("0"),
            win_rate=100.0
        )
        
        data = daily_summary.to_dict()
        
        assert data['date'] == '2024-01-15'
        assert data['gross_pl'] == 10.50
        assert data['net_pl'] == 10.00
        assert data['win_rate'] == 100.0
        
    @pytest.mark.asyncio
    async def test_december_month_calculation(self, analytics_engine):
        """Test monthly calculation for December (edge case)"""
        # Test that December correctly calculates to end of year
        year = 2024
        month = 12
        
        # Create sample transactions for December
        transactions = [
            TransactionRecord(
                transaction_id="1",
                transaction_type="ORDER_FILL",
                instrument="EUR_USD",
                units=Decimal("1000"),
                price=Decimal("1.1000"),
                pl=Decimal("10.00"),
                commission=Decimal("0.50"),
                financing=Decimal("0.00"),
                timestamp=datetime(2024, 12, 15, 10, 0),
                account_balance=Decimal("1010.00"),
                reason="MARKET_ORDER"
            )
        ]
        
        monthly_summary = await analytics_engine.calculate_monthly_pl(
            transactions, year, month
        )
        
        assert monthly_summary.year == 2024
        assert monthly_summary.month == 12
        assert len(monthly_summary.daily_summaries) == 31  # December has 31 days