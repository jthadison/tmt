"""Tests for P&L tracking functionality."""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..app.models import Base, TradePerformance, PositionData, MarketTick, TradeStatus
from ..app.pnl_tracker import PnLCalculationEngine, PnLTracker
from ..app.market_data import MarketDataFeed


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
def sample_position():
    """Create sample position data."""
    return PositionData(
        account_id=uuid4(),
        symbol="EURUSD",
        position_size=Decimal("1.0"),
        entry_price=Decimal("1.1000"),
        entry_time=datetime.utcnow() - timedelta(hours=2),
        stop_loss=Decimal("1.0950"),
        take_profit=Decimal("1.1100")
    )


@pytest.fixture
def market_tick():
    """Create sample market tick."""
    return MarketTick(
        symbol="EURUSD",
        bid=Decimal("1.1025"),
        ask=Decimal("1.1027"),
        timestamp=datetime.utcnow(),
        volume=100
    )


def test_calculate_unrealized_pnl_long(sample_position, market_tick):
    """Test unrealized P&L calculation for long position."""
    engine = PnLCalculationEngine()
    
    # Long position: profit when price goes up
    pnl = engine.calculate_unrealized_pnl(sample_position, market_tick.bid)
    
    # Expected: (1.1025 - 1.1000) * 1.0 = 0.0025 * 100000 = 25 pips = $25
    expected_pnl = Decimal("25.0")
    assert pnl == expected_pnl


def test_calculate_unrealized_pnl_short():
    """Test unrealized P&L calculation for short position."""
    engine = PnLCalculationEngine()
    
    # Short position
    position = PositionData(
        account_id=uuid4(),
        symbol="EURUSD",
        position_size=Decimal("-1.0"),  # Negative for short
        entry_price=Decimal("1.1000"),
        entry_time=datetime.utcnow(),
        stop_loss=Decimal("1.1050"),
        take_profit=Decimal("1.0950")
    )
    
    current_price = Decimal("1.0975")  # Price went down (profitable for short)
    
    pnl = engine.calculate_unrealized_pnl(position, current_price)
    
    # Expected: (1.1000 - 1.0975) * 1.0 = 0.0025 * 100000 = $25
    expected_pnl = Decimal("25.0")
    assert pnl == expected_pnl


def test_calculate_realized_pnl():
    """Test realized P&L calculation."""
    engine = PnLCalculationEngine()
    
    trade = TradePerformance(
        trade_id=uuid4(),
        account_id=uuid4(),
        symbol="EURUSD",
        entry_price=Decimal("1.1000"),
        exit_price=Decimal("1.1050"),
        position_size=Decimal("1.0"),
        commission=Decimal("2.0"),
        swap=Decimal("0.5"),
        status=TradeStatus.CLOSED.value
    )
    
    pnl = engine.calculate_realized_pnl(trade)
    
    # Expected: (1.1050 - 1.1000) * 1.0 * 100000 - 2.0 - 0.5 = 50 - 2.5 = 47.5
    expected_pnl = Decimal("47.5")
    assert pnl == expected_pnl


def test_calculate_swap_cost():
    """Test swap cost calculation."""
    engine = PnLCalculationEngine()
    
    position = PositionData(
        account_id=uuid4(),
        symbol="EURUSD",
        position_size=Decimal("1.0"),
        entry_price=Decimal("1.1000"),
        entry_time=datetime.utcnow() - timedelta(days=3)  # 3 days old
    )
    
    # Mock swap rates
    base_swap_rate = Decimal("0.25")  # Per day per lot
    
    swap_cost = engine.calculate_swap_cost(position, base_swap_rate)
    
    # Expected: 3 days * 0.25 per day * 1 lot = 0.75
    expected_swap = Decimal("0.75")
    assert swap_cost == expected_swap


def test_calculate_commission():
    """Test commission calculation."""
    engine = PnLCalculationEngine()
    
    position_size = Decimal("1.5")  # 1.5 lots
    commission_per_lot = Decimal("3.0")
    
    commission = engine.calculate_commission(position_size, commission_per_lot)
    
    # Expected: 1.5 * 3.0 = 4.5
    expected_commission = Decimal("4.5")
    assert commission == expected_commission


@pytest.mark.asyncio
async def test_pnl_tracker_integration(db_session):
    """Test P&L tracker with mock market data."""
    # Create mock market data feed
    market_feed = MarketDataFeed()
    
    # Create P&L tracker
    tracker = PnLTracker(db_session, market_feed)
    
    # Add a test position
    account_id = uuid4()
    position = PositionData(
        account_id=account_id,
        symbol="EURUSD",
        position_size=Decimal("1.0"),
        entry_price=Decimal("1.1000"),
        entry_time=datetime.utcnow()
    )
    
    await tracker.add_position(position)
    
    # Simulate price update
    tick = MarketTick(
        symbol="EURUSD",
        bid=Decimal("1.1025"),
        ask=Decimal("1.1027"),
        timestamp=datetime.utcnow()
    )
    
    await tracker.update_positions_pnl(tick)
    
    # Get current P&L
    pnl_snapshot = await tracker.get_current_pnl(account_id)
    
    assert pnl_snapshot is not None
    assert pnl_snapshot.unrealized_pnl > 0  # Should be profitable


@pytest.mark.asyncio
async def test_aggregate_account_pnl(db_session):
    """Test aggregating P&L across multiple positions."""
    market_feed = MarketDataFeed()
    tracker = PnLTracker(db_session, market_feed)
    
    account_id = uuid4()
    
    # Add multiple positions
    positions = [
        PositionData(
            account_id=account_id,
            symbol="EURUSD",
            position_size=Decimal("1.0"),
            entry_price=Decimal("1.1000"),
            entry_time=datetime.utcnow()
        ),
        PositionData(
            account_id=account_id,
            symbol="GBPUSD", 
            position_size=Decimal("0.5"),
            entry_price=Decimal("1.3000"),
            entry_time=datetime.utcnow()
        )
    ]
    
    for position in positions:
        await tracker.add_position(position)
    
    # Simulate market updates
    ticks = [
        MarketTick(symbol="EURUSD", bid=Decimal("1.1025"), ask=Decimal("1.1027"), timestamp=datetime.utcnow()),
        MarketTick(symbol="GBPUSD", bid=Decimal("1.3020"), ask=Decimal("1.3022"), timestamp=datetime.utcnow())
    ]
    
    for tick in ticks:
        await tracker.update_positions_pnl(tick)
    
    # Get aggregated P&L
    total_pnl = await tracker.calculate_account_total_pnl(account_id)
    
    assert total_pnl > 0  # Both positions should be profitable


def test_risk_metrics_calculation():
    """Test risk metrics calculation."""
    engine = PnLCalculationEngine()
    
    position = PositionData(
        account_id=uuid4(),
        symbol="EURUSD",
        position_size=Decimal("1.0"),
        entry_price=Decimal("1.1000"),
        entry_time=datetime.utcnow(),
        stop_loss=Decimal("1.0950")  # 50 pips risk
    )
    
    current_price = Decimal("1.1025")
    
    risk_metrics = engine.calculate_position_risk_metrics(position, current_price)
    
    assert "max_risk" in risk_metrics
    assert "unrealized_pnl" in risk_metrics
    assert "risk_reward_ratio" in risk_metrics
    
    # Max risk should be 50 pips = $50
    assert risk_metrics["max_risk"] == Decimal("50.0")


def test_pnl_calculation_edge_cases():
    """Test P&L calculation edge cases."""
    engine = PnLCalculationEngine()
    
    # Zero position size
    position = PositionData(
        account_id=uuid4(),
        symbol="EURUSD",
        position_size=Decimal("0"),
        entry_price=Decimal("1.1000"),
        entry_time=datetime.utcnow()
    )
    
    pnl = engine.calculate_unrealized_pnl(position, Decimal("1.1050"))
    assert pnl == Decimal("0")
    
    # Same entry and current price
    position.position_size = Decimal("1.0")
    pnl = engine.calculate_unrealized_pnl(position, Decimal("1.1000"))
    assert pnl == Decimal("0")


@pytest.mark.asyncio
async def test_position_lifecycle(db_session):
    """Test complete position lifecycle from open to close."""
    market_feed = MarketDataFeed()
    tracker = PnLTracker(db_session, market_feed)
    
    account_id = uuid4()
    
    # Open position
    position = PositionData(
        account_id=account_id,
        symbol="EURUSD",
        position_size=Decimal("1.0"),
        entry_price=Decimal("1.1000"),
        entry_time=datetime.utcnow()
    )
    
    await tracker.add_position(position)
    
    # Update with profitable price
    tick = MarketTick(
        symbol="EURUSD",
        bid=Decimal("1.1050"),
        ask=Decimal("1.1052"),
        timestamp=datetime.utcnow()
    )
    
    await tracker.update_positions_pnl(tick)
    
    # Close position
    await tracker.close_position(position.account_id, position.symbol, tick.bid)
    
    # Verify position is closed
    pnl_snapshot = await tracker.get_current_pnl(account_id)
    
    # Should have realized P&L but no unrealized P&L
    assert pnl_snapshot.realized_pnl > 0
    assert pnl_snapshot.unrealized_pnl == Decimal("0")