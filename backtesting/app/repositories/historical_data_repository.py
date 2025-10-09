"""
Historical Data Repository

Central repository for accessing and managing historical market data,
trade executions, and trading signals.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd
import structlog

from ..models.market_data import (
    MarketCandle,
    TradeExecution,
    TradingSignal,
    MarketCandleSchema,
    TradeExecutionSchema,
    TradingSignalSchema,
)

logger = structlog.get_logger()


class HistoricalDataRepository:
    """Repository for historical market and execution data"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_market_data(
        self,
        instrument: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "H1",
    ) -> pd.DataFrame:
        """
        Retrieve OHLCV data for specified period

        Args:
            instrument: Trading instrument
            start_date: Start of date range
            end_date: End of date range
            timeframe: Candle timeframe

        Returns:
            DataFrame with OHLCV data indexed by timestamp
        """
        logger.info(
            "Fetching market data from database",
            instrument=instrument,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            timeframe=timeframe,
        )

        # Query candles
        stmt = (
            select(MarketCandle)
            .where(
                and_(
                    MarketCandle.instrument == instrument,
                    MarketCandle.timeframe == timeframe,
                    MarketCandle.timestamp >= start_date,
                    MarketCandle.timestamp <= end_date,
                    MarketCandle.complete == True,
                )
            )
            .order_by(MarketCandle.timestamp)
        )

        result = await self.session.execute(stmt)
        candles = result.scalars().all()

        logger.info(f"Retrieved {len(candles)} candles from database")

        # Convert to DataFrame
        if not candles:
            return pd.DataFrame(
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )

        data = {
            "timestamp": [c.timestamp for c in candles],
            "open": [c.open for c in candles],
            "high": [c.high for c in candles],
            "low": [c.low for c in candles],
            "close": [c.close for c in candles],
            "volume": [c.volume for c in candles],
        }

        df = pd.DataFrame(data)
        df.set_index("timestamp", inplace=True)

        return df

    async def get_execution_history(
        self,
        start_date: datetime,
        end_date: datetime,
        instrument: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> List[TradeExecutionSchema]:
        """
        Retrieve historical trades

        Args:
            start_date: Start of date range
            end_date: End of date range
            instrument: Optional filter by instrument
            account_id: Optional filter by account

        Returns:
            List of trade executions
        """
        logger.info(
            "Fetching execution history",
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            instrument=instrument,
            account_id=account_id,
        )

        # Build query conditions
        conditions = [
            TradeExecution.entry_time >= start_date,
            TradeExecution.entry_time <= end_date,
        ]

        if instrument:
            conditions.append(TradeExecution.instrument == instrument)

        if account_id:
            conditions.append(TradeExecution.account_id == account_id)

        # Execute query
        stmt = (
            select(TradeExecution)
            .where(and_(*conditions))
            .order_by(TradeExecution.entry_time)
        )

        result = await self.session.execute(stmt)
        trades = result.scalars().all()

        logger.info(f"Retrieved {len(trades)} trade executions")

        return [TradeExecutionSchema.model_validate(trade) for trade in trades]

    async def get_signal_history(
        self,
        start_date: datetime,
        end_date: datetime,
        min_confidence: float = 0.0,
        executed_only: bool = False,
        instrument: Optional[str] = None,
    ) -> List[TradingSignalSchema]:
        """
        Retrieve historical signals (executed and rejected)

        Args:
            start_date: Start of date range
            end_date: End of date range
            min_confidence: Minimum signal confidence filter
            executed_only: If True, only return executed signals
            instrument: Optional filter by instrument

        Returns:
            List of trading signals
        """
        logger.info(
            "Fetching signal history",
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            min_confidence=min_confidence,
            executed_only=executed_only,
        )

        # Build query conditions
        conditions = [
            TradingSignal.timestamp >= start_date,
            TradingSignal.timestamp <= end_date,
            TradingSignal.confidence >= min_confidence,
        ]

        if executed_only:
            conditions.append(TradingSignal.executed == True)

        if instrument:
            conditions.append(TradingSignal.instrument == instrument)

        # Execute query
        stmt = (
            select(TradingSignal)
            .where(and_(*conditions))
            .order_by(TradingSignal.timestamp)
        )

        result = await self.session.execute(stmt)
        signals = result.scalars().all()

        logger.info(f"Retrieved {len(signals)} signals")

        return [TradingSignalSchema.model_validate(signal) for signal in signals]

    async def store_market_data(
        self, candles: List[MarketCandleSchema]
    ) -> int:
        """
        Store market data in database (bulk insert)

        Args:
            candles: List of market candles to store

        Returns:
            Number of candles stored
        """
        if not candles:
            return 0

        logger.info(f"Storing {len(candles)} candles in database")

        # Convert to ORM models
        candle_models = [
            MarketCandle(
                timestamp=c.timestamp,
                instrument=c.instrument,
                timeframe=c.timeframe,
                open=c.open,
                high=c.high,
                low=c.low,
                close=c.close,
                volume=c.volume,
                complete=c.complete,
            )
            for c in candles
        ]

        # Bulk insert
        self.session.add_all(candle_models)
        await self.session.flush()

        logger.info(f"Stored {len(candle_models)} candles successfully")

        return len(candle_models)

    async def store_trade_execution(
        self, trade: TradeExecutionSchema
    ) -> None:
        """Store single trade execution"""
        logger.info("Storing trade execution", trade_id=trade.trade_id)

        trade_model = TradeExecution(
            trade_id=trade.trade_id,
            instrument=trade.instrument,
            side=trade.side,
            entry_time=trade.entry_time,
            exit_time=trade.exit_time,
            entry_price=trade.entry_price,
            exit_price=trade.exit_price,
            units=trade.units,
            stop_loss=trade.stop_loss,
            take_profit=trade.take_profit,
            entry_slippage=trade.entry_slippage,
            exit_slippage=trade.exit_slippage,
            pnl=trade.pnl,
            pnl_pips=trade.pnl_pips,
            signal_id=trade.signal_id,
            signal_confidence=trade.signal_confidence,
            account_id=trade.account_id,
        )

        self.session.add(trade_model)
        await self.session.flush()

        logger.info("Trade execution stored successfully")

    async def store_signal(self, signal: TradingSignalSchema) -> None:
        """Store single trading signal"""
        logger.info("Storing trading signal", signal_id=signal.signal_id)

        signal_model = TradingSignal(
            signal_id=signal.signal_id,
            instrument=signal.instrument,
            side=signal.side,
            timestamp=signal.timestamp,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            confidence=signal.confidence,
            risk_reward_ratio=signal.risk_reward_ratio,
            executed=signal.executed,
            rejection_reason=signal.rejection_reason,
            pattern_type=signal.pattern_type,
            vpa_score=signal.vpa_score,
            wyckoff_phase=signal.wyckoff_phase,
            trading_session=signal.trading_session,
        )

        self.session.add(signal_model)
        await self.session.flush()

        logger.info("Trading signal stored successfully")

    async def get_data_statistics(
        self, instrument: str, timeframe: str = "H1"
    ) -> dict:
        """
        Get statistics about stored data for an instrument

        Returns:
            Dictionary with data coverage statistics
        """
        logger.info(
            "Fetching data statistics", instrument=instrument, timeframe=timeframe
        )

        # Count total candles
        count_stmt = select(func.count(MarketCandle.id)).where(
            and_(
                MarketCandle.instrument == instrument,
                MarketCandle.timeframe == timeframe,
            )
        )
        count_result = await self.session.execute(count_stmt)
        total_candles = count_result.scalar_one()

        # Get date range
        date_stmt = select(
            func.min(MarketCandle.timestamp),
            func.max(MarketCandle.timestamp),
        ).where(
            and_(
                MarketCandle.instrument == instrument,
                MarketCandle.timeframe == timeframe,
            )
        )
        date_result = await self.session.execute(date_stmt)
        min_date, max_date = date_result.one()

        stats = {
            "instrument": instrument,
            "timeframe": timeframe,
            "total_candles": total_candles,
            "earliest_date": min_date.isoformat() if min_date else None,
            "latest_date": max_date.isoformat() if max_date else None,
            "coverage_days": (max_date - min_date).days if min_date and max_date else 0,
        }

        logger.info("Data statistics retrieved", **stats)

        return stats

    async def delete_candles_in_range(
        self,
        instrument: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "H1",
    ) -> int:
        """
        Delete candles in specified date range (for data refresh)

        Returns:
            Number of candles deleted
        """
        logger.warning(
            "Deleting candles in range",
            instrument=instrument,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            timeframe=timeframe,
        )

        # Get count before deletion
        count_stmt = select(func.count(MarketCandle.id)).where(
            and_(
                MarketCandle.instrument == instrument,
                MarketCandle.timeframe == timeframe,
                MarketCandle.timestamp >= start_date,
                MarketCandle.timestamp <= end_date,
            )
        )
        count_result = await self.session.execute(count_stmt)
        count = count_result.scalar_one()

        # Delete candles
        from sqlalchemy import delete

        delete_stmt = delete(MarketCandle).where(
            and_(
                MarketCandle.instrument == instrument,
                MarketCandle.timeframe == timeframe,
                MarketCandle.timestamp >= start_date,
                MarketCandle.timestamp <= end_date,
            )
        )

        await self.session.execute(delete_stmt)
        await self.session.flush()

        logger.info(f"Deleted {count} candles")

        return count
