"""Tests for performance metrics calculator."""

import pytest
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..app.models import Base, TradePerformance, PeriodType, TradeStatus
from ..app.metrics_calculator import PerformanceMetricsCalculator


@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_trades(db_session):
    """Create sample trades for testing."""
    account_id = uuid4()
    trades = []
    
    # Create winning trades
    for i in range(6):  # 60% win rate
        trade = TradePerformance(
            trade_id=uuid4(),
            account_id=account_id,
            symbol="EURUSD",
            entry_time=datetime.utcnow() - timedelta(days=i),
            exit_time=datetime.utcnow() - timedelta(days=i) + timedelta(hours=2),
            entry_price=Decimal("1.1000"),
            exit_price=Decimal("1.1050"),
            position_size=Decimal("1.0"),
            pnl=Decimal("50.0"),
            commission=Decimal("2.0"),
            status=TradeStatus.CLOSED.value
        )
        trades.append(trade)
        db_session.add(trade)
    
    # Create losing trades
    for i in range(4):  # 40% loss rate
        trade = TradePerformance(
            trade_id=uuid4(),
            account_id=account_id,
            symbol="GBPUSD",
            entry_time=datetime.utcnow() - timedelta(days=i+6),
            exit_time=datetime.utcnow() - timedelta(days=i+6) + timedelta(hours=1),
            entry_price=Decimal("1.3000"),
            exit_price=Decimal("1.2950"),
            position_size=Decimal("1.0"),
            pnl=Decimal("-50.0"),
            commission=Decimal("2.0"),
            status=TradeStatus.CLOSED.value
        )
        trades.append(trade)
        db_session.add(trade)
    
    db_session.commit()
    return account_id, trades


@pytest.mark.asyncio
async def test_calculate_win_rate(db_session, sample_trades):
    """Test win rate calculation."""
    account_id, trades = sample_trades
    calculator = PerformanceMetricsCalculator(db_session)
    
    start_date = datetime.utcnow() - timedelta(days=15)
    end_date = datetime.utcnow()
    
    metrics = await calculator.calculate_period_metrics(
        account_id, start_date, end_date, PeriodType.DAILY
    )
    
    # Should be 60% win rate (6 wins out of 10 trades)
    assert metrics.win_rate == Decimal("60.0")
    assert metrics.total_trades == 10
    assert metrics.winning_trades == 6
    assert metrics.losing_trades == 4


@pytest.mark.asyncio
async def test_calculate_profit_factor(db_session, sample_trades):
    """Test profit factor calculation."""
    account_id, trades = sample_trades
    calculator = PerformanceMetricsCalculator(db_session)
    
    start_date = datetime.utcnow() - timedelta(days=15)
    end_date = datetime.utcnow()
    
    metrics = await calculator.calculate_period_metrics(
        account_id, start_date, end_date, PeriodType.DAILY
    )
    
    # Gross profit: 6 * 50 = 300
    # Gross loss: 4 * 50 = 200  
    # Profit factor: 300 / 200 = 1.5
    assert metrics.profit_factor == Decimal("1.50")


@pytest.mark.asyncio
async def test_calculate_sharpe_ratio(db_session):
    """Test Sharpe ratio calculation."""
    calculator = PerformanceMetricsCalculator(db_session)
    
    # Test with known returns
    returns = [Decimal("0.01"), Decimal("0.02"), Decimal("-0.01"), Decimal("0.03")]
    
    sharpe = calculator.calculate_sharpe_ratio(returns)
    
    # Should calculate annualized Sharpe ratio
    assert sharpe is not None
    assert isinstance(sharpe, Decimal)


def test_calculate_maximum_drawdown():
    """Test maximum drawdown calculation."""
    calculator = PerformanceMetricsCalculator(None)
    
    # Test equity curve with known drawdown
    equity_curve = [1000, 1100, 1050, 950, 900, 1000, 1200]
    
    max_dd = calculator.calculate_maximum_drawdown(equity_curve)
    
    # Maximum drawdown should be from 1100 to 900 = 18.18%
    expected_dd = ((900 - 1100) / 1100) * 100
    assert abs(float(max_dd) - expected_dd) < 0.1


def test_calculate_sortino_ratio():
    """Test Sortino ratio calculation."""
    calculator = PerformanceMetricsCalculator(None)
    
    # Returns with downside volatility
    returns = [Decimal("0.02"), Decimal("-0.01"), Decimal("0.03"), Decimal("-0.02")]
    
    sortino = calculator.calculate_sortino_ratio(returns)
    
    assert sortino is not None
    assert isinstance(sortino, Decimal)


def test_calculate_calmar_ratio():
    """Test Calmar ratio calculation.""" 
    calculator = PerformanceMetricsCalculator(None)
    
    annual_return = Decimal("0.15")  # 15%
    max_drawdown = Decimal("0.05")   # 5%
    
    calmar = calculator.calculate_calmar_ratio(annual_return, max_drawdown)
    
    # Calmar = 0.15 / 0.05 = 3.0
    assert calmar == Decimal("3.00")


def test_edge_cases():
    """Test edge cases and error handling."""
    calculator = PerformanceMetricsCalculator(None)
    
    # Empty returns
    assert calculator.calculate_sharpe_ratio([]) is None
    
    # Single return
    single_return = [Decimal("0.01")]
    assert calculator.calculate_sharpe_ratio(single_return) is None
    
    # Zero drawdown
    calmar = calculator.calculate_calmar_ratio(Decimal("0.10"), Decimal("0"))
    assert calmar is None
    
    # Empty equity curve
    max_dd = calculator.calculate_maximum_drawdown([])
    assert max_dd == Decimal("0")


@pytest.mark.asyncio
async def test_calculate_period_metrics_no_trades(db_session):
    """Test metrics calculation when no trades exist."""
    calculator = PerformanceMetricsCalculator(db_session)
    account_id = uuid4()
    
    start_date = datetime.utcnow() - timedelta(days=30)
    end_date = datetime.utcnow()
    
    metrics = await calculator.calculate_period_metrics(
        account_id, start_date, end_date, PeriodType.DAILY
    )
    
    # Should return zero metrics
    assert metrics.total_trades == 0
    assert metrics.win_rate == Decimal("0")
    assert metrics.total_pnl == Decimal("0")
    assert metrics.profit_factor == Decimal("0")


@pytest.mark.asyncio 
async def test_calculate_advanced_metrics(db_session, sample_trades):
    """Test advanced metrics calculations."""
    account_id, trades = sample_trades
    calculator = PerformanceMetricsCalculator(db_session)
    
    start_date = datetime.utcnow() - timedelta(days=15)
    end_date = datetime.utcnow()
    
    metrics = await calculator.calculate_period_metrics(
        account_id, start_date, end_date, PeriodType.DAILY
    )
    
    # Check all metrics are calculated
    assert metrics.average_win > 0
    assert metrics.average_loss < 0  # Should be negative
    assert metrics.largest_win >= metrics.average_win
    assert metrics.largest_loss <= metrics.average_loss
    
    # Verify Sharpe and Sortino ratios
    assert metrics.sharpe_ratio is not None
    assert metrics.sortino_ratio is not None
    
    # Max drawdown should be reasonable
    assert metrics.max_drawdown >= 0