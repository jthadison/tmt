"""
Tests for Historical Data Repository
"""

import pytest
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.historical_data_repository import HistoricalDataRepository
from app.models.market_data import (
    MarketCandleSchema,
    TradeExecutionSchema,
    TradingSignalSchema,
)


class TestHistoricalDataRepository:
    """Test historical data repository"""

    @pytest.mark.asyncio
    async def test_store_and_retrieve_market_data(
        self, db_session: AsyncSession, sample_candles: List[MarketCandleSchema]
    ):
        """Test storing and retrieving market candles"""
        repo = HistoricalDataRepository(db_session)

        # Store candles
        stored_count = await repo.store_market_data(sample_candles)
        assert stored_count == len(sample_candles)

        # Retrieve candles
        start = sample_candles[0].timestamp
        end = sample_candles[-1].timestamp

        df = await repo.get_market_data("EUR_USD", start, end, "H1")

        assert not df.empty
        assert len(df) == len(sample_candles)
        assert "open" in df.columns
        assert "high" in df.columns
        assert "low" in df.columns
        assert "close" in df.columns
        assert "volume" in df.columns

    @pytest.mark.asyncio
    async def test_store_empty_candles(self, db_session: AsyncSession):
        """Test storing empty candle list"""
        repo = HistoricalDataRepository(db_session)

        stored_count = await repo.store_market_data([])
        assert stored_count == 0

    @pytest.mark.asyncio
    async def test_store_trade_execution(self, db_session: AsyncSession):
        """Test storing trade execution"""
        repo = HistoricalDataRepository(db_session)

        trade = TradeExecutionSchema(
            trade_id="TRADE-001",
            instrument="EUR_USD",
            side="long",
            entry_time=datetime(2024, 1, 1, 10, 0, 0),
            exit_time=datetime(2024, 1, 1, 14, 0, 0),
            entry_price=1.1000,
            exit_price=1.1050,
            units=10000,
            stop_loss=1.0950,
            take_profit=1.1100,
            pnl=50.0,
            pnl_pips=50.0,
            account_id="ACC-001",
        )

        await repo.store_trade_execution(trade)

        # Retrieve trade
        trades = await repo.get_execution_history(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2),
            account_id="ACC-001",
        )

        assert len(trades) == 1
        assert trades[0].trade_id == "TRADE-001"
        assert trades[0].pnl == 50.0

    @pytest.mark.asyncio
    async def test_store_trading_signal(self, db_session: AsyncSession):
        """Test storing trading signal"""
        repo = HistoricalDataRepository(db_session)

        signal = TradingSignalSchema(
            signal_id="SIGNAL-001",
            instrument="EUR_USD",
            side="long",
            timestamp=datetime(2024, 1, 1, 10, 0, 0),
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
            confidence=0.75,
            risk_reward_ratio=2.0,
            executed=True,
            pattern_type="Wyckoff Spring",
            trading_session="London",
        )

        await repo.store_signal(signal)

        # Retrieve signal
        signals = await repo.get_signal_history(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2),
            executed_only=True,
        )

        assert len(signals) == 1
        assert signals[0].signal_id == "SIGNAL-001"
        assert signals[0].confidence == 0.75
        assert signals[0].executed == True

    @pytest.mark.asyncio
    async def test_get_data_statistics(
        self, db_session: AsyncSession, sample_candles: List[MarketCandleSchema]
    ):
        """Test getting data statistics"""
        repo = HistoricalDataRepository(db_session)

        # Store candles
        await repo.store_market_data(sample_candles)

        # Get statistics
        stats = await repo.get_data_statistics("EUR_USD", "H1")

        assert stats["instrument"] == "EUR_USD"
        assert stats["timeframe"] == "H1"
        assert stats["total_candles"] == len(sample_candles)
        assert stats["earliest_date"] is not None
        assert stats["latest_date"] is not None
        assert stats["coverage_days"] >= 0

    @pytest.mark.asyncio
    async def test_delete_candles_in_range(
        self, db_session: AsyncSession, sample_candles: List[MarketCandleSchema]
    ):
        """Test deleting candles in date range"""
        repo = HistoricalDataRepository(db_session)

        # Store candles
        await repo.store_market_data(sample_candles)

        # Delete middle portion
        delete_start = sample_candles[25].timestamp
        delete_end = sample_candles[75].timestamp

        deleted_count = await repo.delete_candles_in_range(
            "EUR_USD", delete_start, delete_end, "H1"
        )

        assert deleted_count > 0

        # Verify deletion
        df = await repo.get_market_data(
            "EUR_USD", sample_candles[0].timestamp, sample_candles[-1].timestamp, "H1"
        )

        # Should have fewer candles now
        assert len(df) < len(sample_candles)

    @pytest.mark.asyncio
    async def test_filter_executions_by_instrument(self, db_session: AsyncSession):
        """Test filtering executions by instrument"""
        repo = HistoricalDataRepository(db_session)

        # Store trades for different instruments
        for instrument in ["EUR_USD", "GBP_USD"]:
            trade = TradeExecutionSchema(
                trade_id=f"TRADE-{instrument}",
                instrument=instrument,
                side="long",
                entry_time=datetime(2024, 1, 1, 10, 0, 0),
                entry_price=1.1000,
                units=10000,
                account_id="ACC-001",
            )
            await repo.store_trade_execution(trade)

        # Filter by EUR_USD only
        trades = await repo.get_execution_history(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2),
            instrument="EUR_USD",
        )

        assert len(trades) == 1
        assert trades[0].instrument == "EUR_USD"

    @pytest.mark.asyncio
    async def test_filter_signals_by_confidence(self, db_session: AsyncSession):
        """Test filtering signals by confidence"""
        repo = HistoricalDataRepository(db_session)

        # Store signals with different confidence levels
        for i, confidence in enumerate([0.5, 0.7, 0.9]):
            signal = TradingSignalSchema(
                signal_id=f"SIGNAL-{i}",
                instrument="EUR_USD",
                side="long",
                timestamp=datetime(2024, 1, 1, 10 + i, 0, 0),
                entry_price=1.1000,
                stop_loss=1.0950,
                take_profit=1.1100,
                confidence=confidence,
                risk_reward_ratio=2.0,
            )
            await repo.store_signal(signal)

        # Filter by confidence >= 0.7
        signals = await repo.get_signal_history(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2),
            min_confidence=0.7,
        )

        assert len(signals) == 2  # 0.7 and 0.9
        assert all(s.confidence >= 0.7 for s in signals)
