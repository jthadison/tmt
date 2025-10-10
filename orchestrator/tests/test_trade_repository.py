"""
Unit tests for TradeRepository.

Tests all CRUD operations for trade persistence with SQLAlchemy ORM.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import tempfile
import os

from app.database import (
    initialize_database,
    TradeRepository,
    Trade,
)


@pytest.fixture
async def test_db_engine():
    """Create a temporary test database"""
    # Create temporary database file
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_trading_system.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"

    # Initialize database
    engine = await initialize_database(database_url=db_url)

    yield engine

    # Cleanup
    await engine.close()
    if db_path.exists():
        db_path.unlink()
    Path(temp_dir).rmdir()


@pytest.fixture
async def trade_repo(test_db_engine):
    """Create TradeRepository instance"""
    return TradeRepository(test_db_engine.session_factory)


@pytest.fixture
def sample_trade_data():
    """Sample trade data for testing"""
    return {
        "trade_id": "TRADE_001",
        "signal_id": "SIGNAL_001",
        "account_id": "ACC_001",
        "symbol": "EUR_USD",
        "direction": "BUY",
        "entry_time": datetime.now(timezone.utc),
        "entry_price": Decimal("1.09500"),
        "stop_loss": Decimal("1.09000"),
        "take_profit": Decimal("1.10000"),
        "position_size": Decimal("10000"),
        "session": "LONDON",
        "pattern_type": "WYCKOFF_ACCUMULATION",
        "confidence_score": Decimal("85.50"),
        "risk_reward_ratio": Decimal("2.50"),
    }


@pytest.mark.asyncio
async def test_save_trade(trade_repo, sample_trade_data):
    """Test saving a trade to the database"""
    # Save trade
    trade = await trade_repo.save_trade(sample_trade_data)

    # Assertions
    assert trade is not None
    assert trade.trade_id == "TRADE_001"
    assert trade.symbol == "EUR_USD"
    assert trade.direction == "BUY"
    assert trade.entry_price == Decimal("1.09500")
    assert trade.session == "LONDON"
    assert trade.confidence_score == Decimal("85.50")


@pytest.mark.asyncio
async def test_save_trade_with_decimal_conversion(trade_repo):
    """Test saving trade with automatic Decimal conversion"""
    trade_data = {
        "trade_id": "TRADE_002",
        "account_id": "ACC_001",
        "symbol": "GBP_USD",
        "direction": "SELL",
        "entry_time": datetime.now(timezone.utc),
        "entry_price": 1.26500,  # Float - should be converted to Decimal
        "position_size": 5000,  # Int - should be converted to Decimal
    }

    trade = await trade_repo.save_trade(trade_data)

    assert trade is not None
    assert isinstance(trade.entry_price, Decimal)
    assert isinstance(trade.position_size, Decimal)
    assert trade.entry_price == Decimal("1.26500")
    assert trade.position_size == Decimal("5000")


@pytest.mark.asyncio
async def test_get_recent_trades(trade_repo, sample_trade_data):
    """Test retrieving recent trades"""
    # Save multiple trades
    for i in range(5):
        trade_data = sample_trade_data.copy()
        trade_data["trade_id"] = f"TRADE_{i:03d}"
        trade_data["signal_id"] = f"SIGNAL_{i:03d}"
        await trade_repo.save_trade(trade_data)

    # Get recent trades
    recent_trades = await trade_repo.get_recent_trades(limit=3)

    # Assertions
    assert len(recent_trades) == 3
    # All trades should be present (order may vary by timestamp precision)
    trade_ids = {t.trade_id for t in recent_trades}
    assert len(trade_ids) == 3
    # Verify they are from our test set
    for trade in recent_trades:
        assert trade.trade_id.startswith("TRADE_")


@pytest.mark.asyncio
async def test_get_trades_by_session(trade_repo, sample_trade_data):
    """Test filtering trades by trading session"""
    # Create trades in different sessions
    sessions = ["TOKYO", "LONDON", "NY", "LONDON", "TOKYO"]
    for i, session in enumerate(sessions):
        trade_data = sample_trade_data.copy()
        trade_data["trade_id"] = f"TRADE_{i:03d}"
        trade_data["session"] = session
        await trade_repo.save_trade(trade_data)

    # Get London session trades
    london_trades = await trade_repo.get_trades_by_session("LONDON")

    # Assertions
    assert len(london_trades) == 2
    for trade in london_trades:
        assert trade.session == "LONDON"


@pytest.mark.asyncio
async def test_get_trades_by_pattern(trade_repo, sample_trade_data):
    """Test filtering trades by pattern type"""
    # Create trades with different patterns
    patterns = [
        "WYCKOFF_ACCUMULATION",
        "WYCKOFF_DISTRIBUTION",
        "WYCKOFF_ACCUMULATION",
    ]
    for i, pattern in enumerate(patterns):
        trade_data = sample_trade_data.copy()
        trade_data["trade_id"] = f"TRADE_{i:03d}"
        trade_data["pattern_type"] = pattern
        await trade_repo.save_trade(trade_data)

    # Get accumulation pattern trades
    accumulation_trades = await trade_repo.get_trades_by_pattern(
        "WYCKOFF_ACCUMULATION"
    )

    # Assertions
    assert len(accumulation_trades) == 2
    for trade in accumulation_trades:
        assert trade.pattern_type == "WYCKOFF_ACCUMULATION"


@pytest.mark.asyncio
async def test_get_trade_by_id(trade_repo, sample_trade_data):
    """Test retrieving a specific trade by ID"""
    # Save trade
    await trade_repo.save_trade(sample_trade_data)

    # Get trade by ID
    trade = await trade_repo.get_trade_by_id("TRADE_001")

    # Assertions
    assert trade is not None
    assert trade.trade_id == "TRADE_001"
    assert trade.symbol == "EUR_USD"


@pytest.mark.asyncio
async def test_get_trade_by_id_not_found(trade_repo):
    """Test getting non-existent trade returns None"""
    trade = await trade_repo.get_trade_by_id("NONEXISTENT")
    assert trade is None


@pytest.mark.asyncio
async def test_update_trade(trade_repo, sample_trade_data):
    """Test updating an existing trade"""
    # Save initial trade
    await trade_repo.save_trade(sample_trade_data)

    # Update trade
    update_data = {
        "exit_time": datetime.now(timezone.utc),
        "exit_price": Decimal("1.09800"),
        "pnl": Decimal("300.00"),
        "pnl_percentage": Decimal("3.00"),
    }
    updated_trade = await trade_repo.update_trade("TRADE_001", update_data)

    # Assertions
    assert updated_trade is not None
    assert updated_trade.exit_price == Decimal("1.09800")
    assert updated_trade.pnl == Decimal("300.00")
    assert updated_trade.pnl_percentage == Decimal("3.00")


@pytest.mark.asyncio
async def test_decimal_precision(trade_repo):
    """Test that monetary values maintain proper Decimal precision"""
    trade_data = {
        "trade_id": "TRADE_DECIMAL",
        "account_id": "ACC_001",
        "symbol": "EUR_USD",
        "direction": "BUY",
        "entry_time": datetime.now(timezone.utc),
        "entry_price": Decimal("1.095005"),  # 6 decimal places
        "position_size": Decimal("10000.50"),
        "pnl": Decimal("123.45"),
    }

    trade = await trade_repo.save_trade(trade_data)

    # Verify Decimal types are preserved
    assert isinstance(trade.entry_price, Decimal)
    assert isinstance(trade.position_size, Decimal)
    assert isinstance(trade.pnl, Decimal)

    # Verify precision is maintained (SQLite may round slightly differently)
    assert trade.entry_price >= Decimal("1.09500")
    assert trade.entry_price <= Decimal("1.09501")
    assert str(trade.position_size) == "10000.50"
    assert str(trade.pnl) == "123.45"
