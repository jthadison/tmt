"""
Tests for Trade Synchronization System

Tests the trade database, sync service, and reconciliation functionality.
"""

import asyncio
import pytest
import json
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime, timedelta

# Add parent directory to path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from orchestrator.app.trade_sync.trade_database import TradeDatabase, TradeStatus
from orchestrator.app.trade_sync.sync_service import TradeSyncService
from orchestrator.app.trade_sync.reconciliation import TradeReconciliation


@pytest.fixture
async def test_db():
    """Create a test database"""
    db = TradeDatabase(":memory:")  # Use in-memory SQLite for tests
    await db.initialize()
    yield db
    await db.close()


@pytest.fixture
def mock_oanda_client():
    """Create a mock OANDA client"""
    client = Mock()

    # Mock settings with account IDs
    client.settings = Mock()
    client.settings.account_ids_list = ["test-account-001"]

    # Mock OandaTrade objects
    from orchestrator.app.oanda_client import OandaTrade
    mock_trade_1 = OandaTrade(
        trade_id="1001",
        instrument="EUR_USD",
        units=1000.0,
        price=1.1250,
        unrealized_pnl=50.0,
        open_time=datetime(2025, 9, 25, 10, 0, 0)
    )
    mock_trade_2 = OandaTrade(
        trade_id="1002",
        instrument="GBP_USD",
        units=-500.0,
        price=1.3500,
        unrealized_pnl=-25.0,
        open_time=datetime(2025, 9, 25, 11, 0, 0)
    )

    # Mock get_trades method
    client.get_trades = AsyncMock(return_value=[mock_trade_1, mock_trade_2])

    # Mock get_account_info method
    from orchestrator.app.oanda_client import OandaAccount
    mock_account = OandaAccount(
        account_id="test-account-001",
        balance=100000.0,
        unrealized_pnl=150.50,
        margin_used=1000.0,
        margin_available=99000.0,
        open_trade_count=2,
        currency="USD"
    )
    client.get_account_info = AsyncMock(return_value=mock_account)

    # Mock reconciliation methods
    client.get_open_trades = AsyncMock(return_value={
        "trades": [
            {
                "id": "1001",
                "instrument": "EUR_USD",
                "currentUnits": "1000",
                "unrealizedPL": "50.0",
                "stopLossOrder": None,
                "takeProfitOrder": None
            },
            {
                "id": "1002",
                "instrument": "GBP_USD",
                "currentUnits": "-500",
                "unrealizedPL": "-25.0",
                "stopLossOrder": None,
                "takeProfitOrder": None
            }
        ]
    })

    client.get_account = AsyncMock(return_value={
        "account": {
            "id": "test-account-001",
            "unrealizedPL": "25.0",
            "balance": "100000.0"
        }
    })

    return client


@pytest.fixture
def mock_event_bus():
    """Create a mock EventBus"""
    event_bus = Mock()
    event_bus.publish = AsyncMock()
    return event_bus


@pytest.mark.asyncio
async def test_database_operations(test_db):
    """Test basic database operations"""
    # Insert a trade
    trade_data = {
        "trade_id": "1001",
        "internal_id": "internal-1001",
        "account_id": "test-account",
        "instrument": "EUR/USD",
        "direction": "buy",
        "units": 1000,
        "entry_price": 1.1250,
        "entry_time": datetime.now().isoformat(),
        "stop_loss": 1.1200,
        "take_profit": 1.1300,
        "status": TradeStatus.OPEN
    }

    result = await test_db.upsert_trade(trade_data)
    assert result == True

    # Get the trade
    trade = await test_db.get_trade_by_id("1001")
    assert trade is not None
    assert trade["instrument"] == "EUR/USD"
    assert trade["units"] == 1000

    # Update the trade
    trade_data["pnl_unrealized"] = 50.0
    result = await test_db.upsert_trade(trade_data)
    assert result == True

    # Get active trades
    active_trades = await test_db.get_active_trades()
    assert len(active_trades) == 1
    assert active_trades[0]["trade_id"] == "1001"

    # Close the trade
    trade_data["status"] = TradeStatus.CLOSED
    trade_data["close_price"] = 1.1280
    trade_data["close_time"] = datetime.now().isoformat()
    trade_data["pnl_realized"] = 30.0
    result = await test_db.upsert_trade(trade_data)
    assert result == True

    # Check closed trades
    closed_trades = await test_db.get_closed_trades(days=1)
    assert len(closed_trades) == 1
    assert closed_trades[0]["pnl_realized"] == 30.0


@pytest.mark.asyncio
async def test_sync_service(mock_oanda_client, mock_event_bus, test_db):
    """Test trade synchronization service"""
    sync_service = TradeSyncService(
        oanda_client=mock_oanda_client,
        event_bus=mock_event_bus,
        sync_interval=30
    )

    # Override with test database
    sync_service.db = test_db
    # Don't call initialize as that would create tables again
    # await sync_service.initialize()

    # Perform sync
    result = await sync_service.sync_trades()

    assert result["status"] == "success"
    assert result["trades_synced"] == 2
    assert result["trades_added"] == 2

    # Check database has trades
    active_trades = await sync_service.db.get_active_trades()
    assert len(active_trades) == 2

    # Find EUR/USD trade
    eur_trade = next((t for t in active_trades if t["instrument"] == "EUR/USD"), None)
    assert eur_trade is not None
    assert eur_trade["direction"] == "buy"
    assert eur_trade["units"] == 1000

    # Find GBP/USD trade
    gbp_trade = next((t for t in active_trades if t["instrument"] == "GBP/USD"), None)
    assert gbp_trade is not None
    assert gbp_trade["direction"] == "sell"
    assert gbp_trade["units"] == 500

    # Verify events were published
    assert mock_event_bus.publish.call_count == 2

    # Don't close the database - it's managed by the test fixture


@pytest.mark.asyncio
async def test_reconciliation(mock_oanda_client, test_db):
    """Test reconciliation service"""
    reconciliation = TradeReconciliation(
        oanda_client=mock_oanda_client,
        auto_fix=True
    )

    # Override with test database
    reconciliation.db = test_db
    # Don't call initialize as that would create tables again
    # await reconciliation.initialize()

    # Add a trade that doesn't exist in OANDA (orphaned)
    orphaned_trade = {
        "trade_id": "9999",
        "internal_id": "internal-9999",
        "account_id": "test-account",
        "instrument": "USD/JPY",
        "direction": "buy",
        "units": 2000,
        "status": TradeStatus.OPEN
    }
    await reconciliation.db.upsert_trade(orphaned_trade)

    # Perform reconciliation
    result = await reconciliation.perform_reconciliation()

    assert result["status"] == "success"
    assert "trade_count" in result["checks_performed"]
    assert result["issues_found"] > 0  # Should find orphaned trade

    # Check if orphaned trade was fixed (marked as closed)
    if reconciliation.auto_fix:
        fixed_trade = await reconciliation.db.get_trade_by_id("9999")
        # Auto-fix should mark it as closed
        assert fixed_trade["status"] == TradeStatus.CLOSED

    # Don't close the database - it's managed by the test fixture


@pytest.mark.asyncio
async def test_performance_stats(test_db):
    """Test performance statistics calculation"""
    # Add some test trades
    trades = [
        {
            "trade_id": "1",
            "account_id": "test",
            "instrument": "EUR/USD",
            "direction": "buy",
            "units": 1000,
            "status": TradeStatus.CLOSED,
            "pnl_realized": 50.0,
            "close_time": datetime.now().isoformat()
        },
        {
            "trade_id": "2",
            "account_id": "test",
            "instrument": "GBP/USD",
            "direction": "sell",
            "units": 500,
            "status": TradeStatus.CLOSED,
            "pnl_realized": -30.0,
            "close_time": datetime.now().isoformat()
        },
        {
            "trade_id": "3",
            "account_id": "test",
            "instrument": "USD/JPY",
            "direction": "buy",
            "units": 2000,
            "status": TradeStatus.CLOSED,
            "pnl_realized": 100.0,
            "close_time": datetime.now().isoformat()
        }
    ]

    for trade in trades:
        await test_db.upsert_trade(trade)

    # Get performance stats
    stats = await test_db.get_performance_stats(days=30)

    assert stats["total_trades"] == 3
    assert stats["winning_trades"] == 2
    assert stats["losing_trades"] == 1
    assert stats["total_pnl"] == 120.0  # 50 - 30 + 100
    assert stats["win_rate"] == pytest.approx(66.67, rel=0.01)
    assert stats["best_trade"] == 100.0
    assert stats["worst_trade"] == -30.0


@pytest.mark.asyncio
async def test_sync_history(test_db):
    """Test sync history recording"""
    sync_data = {
        "sync_time": datetime.now().isoformat(),
        "trades_synced": 5,
        "trades_added": 2,
        "trades_updated": 1,
        "trades_closed": 1,
        "sync_duration_ms": 250,
        "status": "success"
    }

    await test_db.record_sync_history(sync_data)

    # Verify history was recorded (would need to add a method to retrieve history)
    # For now, just check no exceptions were raised
    assert True


@pytest.mark.asyncio
async def test_trade_events(test_db):
    """Test trade event recording"""
    trade_id = "1001"

    # First create a trade
    await test_db.upsert_trade({
        "trade_id": trade_id,
        "account_id": "test",
        "instrument": "EUR/USD",
        "direction": "buy",
        "units": 1000,
        "status": TradeStatus.OPEN
    })

    # Add events
    await test_db.add_trade_event(trade_id, "trade_opened", {"price": 1.1250})
    await test_db.add_trade_event(trade_id, "sl_modified", {"old_sl": 1.1200, "new_sl": 1.1210})
    await test_db.add_trade_event(trade_id, "trade_closed", {"close_price": 1.1280, "pnl": 30.0})

    # Events should be recorded without errors
    assert True


@pytest.mark.asyncio
async def test_pnl_calculation(test_db):
    """Test P&L calculation"""
    # Add trades with different statuses
    trades = [
        {
            "trade_id": "1",
            "account_id": "test",
            "instrument": "EUR/USD",
            "direction": "buy",
            "units": 1000,
            "status": TradeStatus.CLOSED,
            "pnl_realized": 100.0
        },
        {
            "trade_id": "2",
            "account_id": "test",
            "instrument": "GBP/USD",
            "direction": "sell",
            "units": 500,
            "status": TradeStatus.CLOSED,
            "pnl_realized": -50.0
        },
        {
            "trade_id": "3",
            "account_id": "test",
            "instrument": "USD/JPY",
            "direction": "buy",
            "units": 2000,
            "status": TradeStatus.OPEN,
            "pnl_unrealized": 25.0
        }
    ]

    for trade in trades:
        await test_db.upsert_trade(trade)

    # Calculate total P&L
    pnl = await test_db.calculate_total_pnl()

    assert pnl["realized_pnl"] == 50.0  # 100 - 50
    assert pnl["unrealized_pnl"] == 25.0
    assert pnl["total_pnl"] == 75.0  # 50 + 25


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])