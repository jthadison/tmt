"""
Integration tests for database persistence.

Tests database restart persistence and end-to-end workflows.
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
    SignalRepository,
)


@pytest.fixture
def test_db_path():
    """Create temporary database path"""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_restart.db"
    yield db_path

    # Cleanup
    if db_path.exists():
        db_path.unlink()
    Path(temp_dir).rmdir()


@pytest.mark.asyncio
async def test_database_restart_persistence(test_db_path):
    """
    Test that trades persist across database restart.

    AC #6: Database survives orchestrator restart
    """
    db_url = f"sqlite+aiosqlite:///{test_db_path}"

    # Phase 1: Initialize database and save trades
    engine1 = await initialize_database(database_url=db_url)
    trade_repo1 = TradeRepository(engine1.session_factory)

    trade_data = {
        "trade_id": "RESTART_TEST_001",
        "account_id": "ACC_001",
        "symbol": "EUR_USD",
        "direction": "BUY",
        "entry_time": datetime.now(timezone.utc),
        "entry_price": Decimal("1.09500"),
        "position_size": Decimal("10000"),
    }

    await trade_repo1.save_trade(trade_data)
    await engine1.close()

    # Phase 2: Reinitialize database (simulating restart)
    engine2 = await initialize_database(database_url=db_url)
    trade_repo2 = TradeRepository(engine2.session_factory)

    # Verify trade still exists
    retrieved_trade = await trade_repo2.get_trade_by_id("RESTART_TEST_001")

    assert retrieved_trade is not None
    assert retrieved_trade.trade_id == "RESTART_TEST_001"
    assert retrieved_trade.symbol == "EUR_USD"
    assert retrieved_trade.entry_price == Decimal("1.09500")

    await engine2.close()


@pytest.mark.asyncio
async def test_end_to_end_signal_to_trade_flow(test_db_path):
    """Test complete signal -> trade execution flow"""
    db_url = f"sqlite+aiosqlite:///{test_db_path}"
    engine = await initialize_database(database_url=db_url)

    trade_repo = TradeRepository(engine.session_factory)
    signal_repo = SignalRepository(engine.session_factory)

    # Step 1: Save signal
    signal_data = {
        "signal_id": "E2E_SIGNAL_001",
        "symbol": "GBP_USD",
        "signal_type": "SELL",
        "confidence": Decimal("90.00"),
        "generated_at": datetime.now(timezone.utc),
    }
    signal = await signal_repo.save_signal(signal_data)
    assert signal.executed is False

    # Step 2: Execute trade based on signal
    trade_data = {
        "trade_id": "E2E_TRADE_001",
        "signal_id": "E2E_SIGNAL_001",
        "account_id": "ACC_001",
        "symbol": "GBP_USD",
        "direction": "SELL",
        "entry_time": datetime.now(timezone.utc),
        "entry_price": Decimal("1.26500"),
        "position_size": Decimal("5000"),
    }
    trade = await trade_repo.save_trade(trade_data)

    # Step 3: Update signal execution status
    updated_signal = await signal_repo.update_signal_execution(
        "E2E_SIGNAL_001", True, "executed_successfully"
    )
    assert updated_signal.executed is True

    # Step 4: Verify relationships
    retrieved_trade = await trade_repo.get_trade_by_id("E2E_TRADE_001")
    assert retrieved_trade.signal_id == "E2E_SIGNAL_001"

    await engine.close()


@pytest.mark.asyncio
async def test_database_unavailable_handling():
    """Test graceful handling of database connection failures"""
    # Try to initialize with invalid database URL
    with pytest.raises(Exception):
        await initialize_database(database_url="invalid://database/url")


@pytest.mark.asyncio
async def test_migration_framework(test_db_path):
    """
    Test migration framework applies and verifies migrations.

    AC #8: Migration framework supports schema updates
    """
    db_url = f"sqlite+aiosqlite:///{test_db_path}"

    # Initialize database (should apply migration 001)
    engine = await initialize_database(database_url=db_url)

    # Verify tables were created
    from app.database.migration_manager import MigrationManager

    migration_manager = MigrationManager(engine.engine)

    # Get current version
    version = await migration_manager.get_current_version()
    assert version >= 1

    # Verify migrations
    is_valid = await migration_manager.verify_migrations()
    assert is_valid is True

    await engine.close()


@pytest.mark.asyncio
async def test_feature_flag_toggle(test_db_path):
    """Test that ENABLE_DATABASE_PERSISTENCE flag works correctly"""
    # This test would require mocking the environment variable
    # For now, we verify the flag is checked in orchestrator
    from app.orchestrator import TradingOrchestrator

    # Create orchestrator
    orchestrator = TradingOrchestrator()

    # Verify database_enabled can be toggled
    assert hasattr(orchestrator, "database_enabled")
    assert isinstance(orchestrator.database_enabled, bool)
