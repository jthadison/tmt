"""
Unit tests for SignalRepository.

Tests signal persistence and execution status tracking.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import tempfile

from app.database import (
    initialize_database,
    SignalRepository,
    Signal,
)


@pytest.fixture
async def test_db_engine():
    """Create a temporary test database"""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_trading_system.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"

    engine = await initialize_database(database_url=db_url)
    yield engine

    await engine.close()
    if db_path.exists():
        db_path.unlink()
    Path(temp_dir).rmdir()


@pytest.fixture
async def signal_repo(test_db_engine):
    """Create SignalRepository instance"""
    return SignalRepository(test_db_engine.session_factory)


@pytest.fixture
def sample_signal_data():
    """Sample signal data for testing"""
    return {
        "signal_id": "SIG_001",
        "symbol": "EUR_USD",
        "timeframe": "H1",
        "signal_type": "BUY",
        "confidence": Decimal("85.50"),
        "entry_price": Decimal("1.09500"),
        "stop_loss": Decimal("1.09000"),
        "take_profit": Decimal("1.10000"),
        "session": "LONDON",
        "pattern_type": "WYCKOFF_ACCUMULATION",
        "generated_at": datetime.now(timezone.utc),
    }


@pytest.mark.asyncio
async def test_save_signal(signal_repo, sample_signal_data):
    """Test saving a signal to the database"""
    signal = await signal_repo.save_signal(sample_signal_data)

    assert signal is not None
    assert signal.signal_id == "SIG_001"
    assert signal.symbol == "EUR_USD"
    assert signal.signal_type == "BUY"
    assert signal.confidence == Decimal("85.50")
    assert signal.executed is False
    assert signal.execution_status is None


@pytest.mark.asyncio
async def test_update_signal_execution(signal_repo, sample_signal_data):
    """Test updating signal execution status"""
    # Save signal
    await signal_repo.save_signal(sample_signal_data)

    # Update execution status
    updated_signal = await signal_repo.update_signal_execution(
        "SIG_001", True, "executed_successfully"
    )

    assert updated_signal is not None
    assert updated_signal.executed is True
    assert updated_signal.execution_status == "executed_successfully"


@pytest.mark.asyncio
async def test_get_recent_signals(signal_repo, sample_signal_data):
    """Test retrieving recent signals"""
    # Save multiple signals
    for i in range(5):
        signal_data = sample_signal_data.copy()
        signal_data["signal_id"] = f"SIG_{i:03d}"
        await signal_repo.save_signal(signal_data)

    recent_signals = await signal_repo.get_recent_signals(limit=3)

    assert len(recent_signals) == 3
    # Should be ordered by generated_at DESC


@pytest.mark.asyncio
async def test_get_signals_by_status(signal_repo, sample_signal_data):
    """Test filtering signals by execution status"""
    # Create signals with different execution statuses
    for i in range(5):
        signal_data = sample_signal_data.copy()
        signal_data["signal_id"] = f"SIG_{i:03d}"
        await signal_repo.save_signal(signal_data)

        # Execute some signals
        if i % 2 == 0:
            await signal_repo.update_signal_execution(
                f"SIG_{i:03d}", True, "executed"
            )

    # Get executed signals
    executed_signals = await signal_repo.get_signals_by_status(True)
    pending_signals = await signal_repo.get_signals_by_status(False)

    assert len(executed_signals) == 3  # 0, 2, 4
    assert len(pending_signals) == 2  # 1, 3


@pytest.mark.asyncio
async def test_get_signal_by_id(signal_repo, sample_signal_data):
    """Test retrieving a specific signal by ID"""
    await signal_repo.save_signal(sample_signal_data)

    signal = await signal_repo.get_signal_by_id("SIG_001")

    assert signal is not None
    assert signal.signal_id == "SIG_001"


@pytest.mark.asyncio
async def test_get_signals_by_symbol(signal_repo, sample_signal_data):
    """Test filtering signals by symbol"""
    symbols = ["EUR_USD", "GBP_USD", "EUR_USD", "USD_JPY"]
    for i, symbol in enumerate(symbols):
        signal_data = sample_signal_data.copy()
        signal_data["signal_id"] = f"SIG_{i:03d}"
        signal_data["symbol"] = symbol
        await signal_repo.save_signal(signal_data)

    eur_signals = await signal_repo.get_signals_by_symbol("EUR_USD")

    assert len(eur_signals) == 2
    for signal in eur_signals:
        assert signal.symbol == "EUR_USD"
