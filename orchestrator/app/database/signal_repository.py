"""
Signal repository for database operations on trading signals.

Implements the repository pattern for signal persistence with async operations
and execution status tracking.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Signal

logger = logging.getLogger(__name__)


class SignalRepository:
    """
    Repository for signal database operations.

    Provides methods for saving and querying trading signals with
    execution status tracking.
    """

    def __init__(self, session_factory):
        """
        Initialize signal repository.

        Args:
            session_factory: Async session factory for database operations
        """
        self.session_factory = session_factory

    async def save_signal(self, signal_data: Dict) -> Signal:
        """
        Save a trading signal to the database.

        Args:
            signal_data: Dictionary containing signal fields:
                - signal_id (str): Unique signal identifier
                - symbol (str): Trading instrument symbol
                - timeframe (str, optional): Signal timeframe
                - signal_type (str): 'BUY' or 'SELL'
                - confidence (Decimal): Signal confidence score
                - entry_price (Decimal, optional): Suggested entry price
                - stop_loss (Decimal, optional): Suggested stop loss
                - take_profit (Decimal, optional): Suggested take profit
                - session (str, optional): Trading session
                - pattern_type (str, optional): Pattern that generated signal
                - generated_at (datetime): Signal generation timestamp

        Returns:
            Signal: Saved signal ORM object

        Raises:
            Exception: If database operation fails
        """
        try:
            async with self.session_factory() as session:
                signal_obj = Signal(
                    signal_id=signal_data["signal_id"],
                    symbol=signal_data["symbol"],
                    timeframe=signal_data.get("timeframe"),
                    signal_type=signal_data["signal_type"].upper(),
                    confidence=self._to_decimal(signal_data["confidence"]),
                    entry_price=self._to_decimal(signal_data.get("entry_price")),
                    stop_loss=self._to_decimal(signal_data.get("stop_loss")),
                    take_profit=self._to_decimal(signal_data.get("take_profit")),
                    session=signal_data.get("session"),
                    pattern_type=signal_data.get("pattern_type"),
                    generated_at=signal_data.get("generated_at", datetime.now(timezone.utc)),
                    executed=False,  # Default to not executed
                    execution_status=None,
                )

                session.add(signal_obj)
                await session.commit()
                await session.refresh(signal_obj)

                logger.info(f"✅ Saved signal to database: {signal_obj.signal_id}")
                return signal_obj

        except Exception as e:
            logger.error(f"❌ Failed to save signal to database: {e}")
            raise

    async def update_signal_execution(
        self, signal_id: str, executed: bool, execution_status: str
    ) -> Optional[Signal]:
        """
        Update signal execution status.

        Args:
            signal_id: Signal ID to update
            executed: Whether signal was executed
            execution_status: Execution status message

        Returns:
            Optional[Signal]: Updated signal object if found, None otherwise
        """
        try:
            async with self.session_factory() as session:
                stmt = select(Signal).where(Signal.signal_id == signal_id)
                result = await session.execute(stmt)
                signal = result.scalar_one_or_none()

                if not signal:
                    logger.warning(f"Signal not found for update: {signal_id}")
                    return None

                signal.executed = executed
                signal.execution_status = execution_status

                await session.commit()
                await session.refresh(signal)

                logger.info(
                    f"✅ Updated signal execution status: {signal_id} -> {execution_status}"
                )
                return signal

        except Exception as e:
            logger.error(f"❌ Failed to update signal execution: {e}")
            raise

    async def get_recent_signals(self, limit: int = 100) -> List[Signal]:
        """
        Get recent signals ordered by generation time.

        Args:
            limit: Maximum number of signals to return (default: 100)

        Returns:
            List[Signal]: List of recent signal objects
        """
        try:
            async with self.session_factory() as session:
                stmt = (
                    select(Signal)
                    .order_by(Signal.generated_at.desc())
                    .limit(limit)
                )
                result = await session.execute(stmt)
                signals = result.scalars().all()

                logger.info(f"Retrieved {len(signals)} recent signals")
                return list(signals)

        except Exception as e:
            logger.error(f"❌ Failed to get recent signals: {e}")
            raise

    async def get_signals_by_status(self, executed: bool) -> List[Signal]:
        """
        Get signals filtered by execution status.

        Args:
            executed: Filter by executed (True) or pending (False)

        Returns:
            List[Signal]: List of matching signals
        """
        try:
            async with self.session_factory() as session:
                stmt = (
                    select(Signal)
                    .where(Signal.executed == executed)
                    .order_by(Signal.generated_at.desc())
                )
                result = await session.execute(stmt)
                signals = result.scalars().all()

                logger.info(
                    f"Retrieved {len(signals)} {'executed' if executed else 'pending'} signals"
                )
                return list(signals)

        except Exception as e:
            logger.error(f"❌ Failed to get signals by status: {e}")
            raise

    async def get_signal_by_id(self, signal_id: str) -> Optional[Signal]:
        """
        Get a specific signal by its ID.

        Args:
            signal_id: Unique signal identifier

        Returns:
            Optional[Signal]: Signal object if found, None otherwise
        """
        try:
            async with self.session_factory() as session:
                stmt = select(Signal).where(Signal.signal_id == signal_id)
                result = await session.execute(stmt)
                signal = result.scalar_one_or_none()

                if signal:
                    logger.info(f"Found signal: {signal_id}")
                else:
                    logger.info(f"Signal not found: {signal_id}")

                return signal

        except Exception as e:
            logger.error(f"❌ Failed to get signal by ID: {e}")
            raise

    async def get_signals_by_symbol(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Signal]:
        """
        Get signals filtered by symbol and optional date range.

        Args:
            symbol: Trading instrument symbol
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List[Signal]: List of matching signals
        """
        try:
            async with self.session_factory() as session:
                # Build filter conditions
                conditions = [Signal.symbol == symbol]

                if start_date:
                    conditions.append(Signal.generated_at >= start_date)
                if end_date:
                    conditions.append(Signal.generated_at <= end_date)

                stmt = (
                    select(Signal)
                    .where(and_(*conditions))
                    .order_by(Signal.generated_at.desc())
                )
                result = await session.execute(stmt)
                signals = result.scalars().all()

                logger.info(f"Retrieved {len(signals)} signals for symbol {symbol}")
                return list(signals)

        except Exception as e:
            logger.error(f"❌ Failed to get signals by symbol: {e}")
            raise

    @staticmethod
    def _to_decimal(value) -> Optional[Decimal]:
        """
        Convert value to Decimal, handling None and various numeric types.

        Args:
            value: Value to convert (int, float, str, Decimal, or None)

        Returns:
            Optional[Decimal]: Decimal value or None
        """
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float, str)):
            return Decimal(str(value))
        return None
