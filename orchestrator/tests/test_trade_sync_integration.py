"""
Integration Tests for Trade Synchronization System

Tests the complete sync workflow including database operations,
OANDA integration, and event publishing.
"""

import asyncio
import pytest
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

# Add parent directory to path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from orchestrator.app.trade_sync.sync_service import TradeSyncService
from orchestrator.app.trade_sync.reconciliation import TradeReconciliation
from orchestrator.app.trade_sync.trade_database import TradeDatabase, TradeStatus
from orchestrator.app.oanda_client import OandaTrade, OandaAccount


@pytest.fixture
async def integration_test_db():
    """Create a test database for integration tests"""
    db = TradeDatabase("test_integration.db")
    await db.initialize()
    yield db
    await db.close()
    # Clean up test database
    try:
        os.remove("test_integration.db")
    except FileNotFoundError:
        pass


@pytest.fixture
def mock_full_oanda_client():
    """Create a comprehensive mock OANDA client for integration tests"""
    client = Mock()
    client.settings = Mock()
    client.settings.account_ids_list = ["101-001-21040028-001", "101-001-21040028-002"]

    # Create realistic trade data
    trades_account_1 = [
        OandaTrade(
            trade_id="5954",
            instrument="EUR_USD",
            units=1000.0,
            price=1.17146,
            unrealized_pnl=-0.59,
            open_time=datetime(2025, 9, 8, 3, 28, 11)
        )
    ]

    trades_account_2 = [
        OandaTrade(
            trade_id="5955",
            instrument="GBP_USD",
            units=-500.0,
            price=1.35016,
            unrealized_pnl=25.30,
            open_time=datetime(2025, 9, 8, 4, 15, 22)
        )
    ]

    def mock_get_trades(account_id):
        if account_id == "101-001-21040028-001":
            return AsyncMock(return_value=trades_account_1)()
        elif account_id == "101-001-21040028-002":
            return AsyncMock(return_value=trades_account_2)()
        else:
            return AsyncMock(return_value=[])()

    client.get_trades = mock_get_trades

    # Mock account info
    def mock_get_account_info(account_id):
        return AsyncMock(return_value=OandaAccount(
            account_id=account_id,
            balance=100000.0,
            unrealized_pnl=24.71 if account_id == "101-001-21040028-001" else 25.30,
            margin_used=1000.0,
            margin_available=99000.0,
            open_trade_count=1,
            currency="USD"
        ))()

    client.get_account_info = mock_get_account_info

    return client


@pytest.mark.asyncio
async def test_full_sync_workflow(integration_test_db, mock_full_oanda_client):
    """Test complete sync workflow with multiple accounts"""
    # Mock event bus
    mock_event_bus = Mock()
    mock_event_bus.publish = AsyncMock()

    # Create sync service
    sync_service = TradeSyncService(
        oanda_client=mock_full_oanda_client,
        event_bus=mock_event_bus,
        sync_interval=10
    )

    # Override database with our test instance
    sync_service.db = integration_test_db

    # Perform initial sync
    result = await sync_service.sync_trades()

    # Verify sync results
    assert result["status"] == "success"
    assert result["trades_synced"] == 2
    assert result["trades_added"] == 2

    # Verify database state
    active_trades = await integration_test_db.get_active_trades()
    assert len(active_trades) == 2

    # Verify trade details
    trade_ids = {trade["trade_id"] for trade in active_trades}
    assert "5954" in trade_ids
    assert "5955" in trade_ids

    # Verify events were published
    assert mock_event_bus.publish.call_count == 2

    # Test subsequent sync (should be no changes)
    result_2 = await sync_service.sync_trades()
    assert result_2["trades_added"] == 0
    assert result_2["trades_updated"] == 0


@pytest.mark.asyncio
async def test_sync_with_trade_closure(integration_test_db, mock_full_oanda_client):
    """Test sync behavior when trades are closed"""
    mock_event_bus = Mock()
    mock_event_bus.publish = AsyncMock()

    sync_service = TradeSyncService(
        oanda_client=mock_full_oanda_client,
        event_bus=mock_event_bus
    )
    sync_service.db = integration_test_db

    # Initial sync with 2 trades
    await sync_service.sync_trades()
    active_trades = await integration_test_db.get_active_trades()
    assert len(active_trades) == 2

    # Simulate trade closure by removing one trade from mock
    original_get_trades = mock_full_oanda_client.get_trades

    def mock_get_trades_with_closure(account_id):
        if account_id == "101-001-21040028-001":
            # Return empty list (trade closed)
            return AsyncMock(return_value=[])()
        elif account_id == "101-001-21040028-002":
            # Keep original trade
            return original_get_trades(account_id)
        else:
            return AsyncMock(return_value=[])()

    mock_full_oanda_client.get_trades = mock_get_trades_with_closure

    # Sync again
    result = await sync_service.sync_trades()
    assert result["trades_closed"] == 1

    # Verify database state
    active_trades = await integration_test_db.get_active_trades()
    assert len(active_trades) == 1
    assert active_trades[0]["trade_id"] == "5955"


@pytest.mark.asyncio
async def test_reconciliation_with_discrepancies(integration_test_db, mock_full_oanda_client):
    """Test reconciliation service with data discrepancies"""
    reconciliation = TradeReconciliation(
        oanda_client=mock_full_oanda_client,
        reconciliation_interval_hours=1,
        auto_fix=True
    )
    reconciliation.db = integration_test_db

    # Add an orphaned trade to database (doesn't exist in OANDA)
    orphaned_trade = {
        "trade_id": "9999",
        "account_id": "101-001-21040028-001",
        "instrument": "USD/JPY",
        "direction": "buy",
        "units": 2000,
        "status": TradeStatus.OPEN
    }
    await integration_test_db.upsert_trade(orphaned_trade)

    # Perform reconciliation
    result = await reconciliation.perform_reconciliation()

    # Should find issues
    assert result["issues_found"] > 0
    assert "missing_in_oanda" in [issue.issue_type for issue in reconciliation.issues]

    # If auto-fix is enabled, orphaned trade should be closed
    if reconciliation.auto_fix:
        orphaned_trade_after = await integration_test_db.get_trade_by_id("9999")
        assert orphaned_trade_after["status"] == TradeStatus.CLOSED


@pytest.mark.asyncio
async def test_bulk_operations_performance(integration_test_db):
    """Test bulk database operations for performance"""
    # Create a large number of trade records
    num_trades = 100
    trades_data = []

    for i in range(num_trades):
        trade = {
            "trade_id": f"bulk_{i}",
            "account_id": "test_account",
            "instrument": "EUR/USD",
            "direction": "buy",
            "units": 1000,
            "status": TradeStatus.OPEN
        }
        trades_data.append(trade)

    # Test bulk upsert
    start_time = datetime.now()
    result = await integration_test_db.bulk_upsert_trades(trades_data)
    end_time = datetime.now()

    duration = (end_time - start_time).total_seconds()

    assert result == num_trades
    assert duration < 5.0  # Should complete within 5 seconds

    # Verify all trades were inserted
    all_trades = await integration_test_db.get_active_trades()
    bulk_trades = [t for t in all_trades if t["trade_id"].startswith("bulk_")]
    assert len(bulk_trades) == num_trades


@pytest.mark.asyncio
async def test_error_handling_and_recovery(integration_test_db):
    """Test error handling and recovery mechanisms"""
    # Create sync service with invalid OANDA client
    mock_broken_client = Mock()
    mock_broken_client.settings = Mock()
    mock_broken_client.settings.account_ids_list = ["invalid-account"]
    mock_broken_client.get_trades = AsyncMock(side_effect=Exception("OANDA API Error"))

    sync_service = TradeSyncService(
        oanda_client=mock_broken_client,
        sync_interval=1,
        fast_sync_on_trade=False
    )
    sync_service.db = integration_test_db

    # Attempt sync (should handle error gracefully)
    result = await sync_service.sync_trades()
    assert result["status"] == "failed"
    assert "OANDA API Error" in result.get("error_message", "")

    # Verify stats are updated
    assert sync_service.sync_stats["failed_syncs"] == 1
    assert sync_service.sync_stats["last_error"] is not None


@pytest.mark.asyncio
async def test_configuration_integration():
    """Test that configuration values are properly loaded"""
    with patch.dict(os.environ, {
        "TRADE_SYNC_INTERVAL": "60",
        "TRADE_RECONCILIATION_INTERVAL_HOURS": "2",
        "TRADE_SYNC_AUTO_FIX": "false",
        "TRADE_SYNC_MAX_RETRIES": "5"
    }):
        # Import after setting environment variables
        from orchestrator.app.config import get_settings
        settings = get_settings()

        sync_service = TradeSyncService()
        assert sync_service.sync_interval == 60
        assert sync_service.max_retries == 5

        reconciliation = TradeReconciliation()
        assert reconciliation.reconciliation_interval == timedelta(hours=2)
        assert reconciliation.auto_fix == False


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"])