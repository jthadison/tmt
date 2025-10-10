"""
Trade repository for database operations on trades.

Implements the repository pattern for trade persistence with async operations,
connection pooling, and comprehensive error handling.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Trade

logger = logging.getLogger(__name__)


class TradeRepository:
    """
    Repository for trade database operations.

    Provides methods for saving and querying trade execution records with
    proper error handling and transaction management.
    """

    def __init__(self, session_factory):
        """
        Initialize trade repository.

        Args:
            session_factory: Async session factory for database operations
        """
        self.session_factory = session_factory

    async def save_trade(self, trade_data: Dict) -> Trade:
        """
        Save a trade to the database.

        Args:
            trade_data: Dictionary containing trade fields:
                - trade_id (str): Unique trade identifier
                - signal_id (str, optional): Associated signal ID
                - account_id (str): Trading account ID
                - symbol (str): Trading instrument symbol
                - direction (str): 'BUY' or 'SELL'
                - entry_time (datetime): Trade entry timestamp
                - entry_price (Decimal): Entry price
                - exit_time (datetime, optional): Trade exit timestamp
                - exit_price (Decimal, optional): Exit price
                - stop_loss (Decimal, optional): Stop loss price
                - take_profit (Decimal, optional): Take profit price
                - position_size (Decimal): Position size in units
                - pnl (Decimal, optional): Profit/loss amount
                - pnl_percentage (Decimal, optional): P&L percentage
                - session (str, optional): Trading session
                - pattern_type (str, optional): Pattern that triggered trade
                - confidence_score (Decimal, optional): Signal confidence
                - risk_reward_ratio (Decimal, optional): Risk/reward ratio

        Returns:
            Trade: Saved trade ORM object

        Raises:
            Exception: If database operation fails
        """
        try:
            async with self.session_factory() as session:
                # Convert numeric fields to Decimal if they're not already
                trade_obj = Trade(
                    trade_id=trade_data["trade_id"],
                    signal_id=trade_data.get("signal_id"),
                    account_id=trade_data["account_id"],
                    symbol=trade_data["symbol"],
                    direction=trade_data["direction"].upper(),
                    entry_time=trade_data["entry_time"],
                    entry_price=self._to_decimal(trade_data["entry_price"]),
                    exit_time=trade_data.get("exit_time"),
                    exit_price=self._to_decimal(trade_data.get("exit_price")),
                    stop_loss=self._to_decimal(trade_data.get("stop_loss")),
                    take_profit=self._to_decimal(trade_data.get("take_profit")),
                    position_size=self._to_decimal(trade_data["position_size"]),
                    pnl=self._to_decimal(trade_data.get("pnl")),
                    pnl_percentage=self._to_decimal(trade_data.get("pnl_percentage")),
                    session=trade_data.get("session"),
                    pattern_type=trade_data.get("pattern_type"),
                    confidence_score=self._to_decimal(trade_data.get("confidence_score")),
                    risk_reward_ratio=self._to_decimal(trade_data.get("risk_reward_ratio")),
                )

                session.add(trade_obj)
                await session.commit()
                await session.refresh(trade_obj)

                logger.info(f"✅ Saved trade to database: {trade_obj.trade_id}")
                return trade_obj

        except Exception as e:
            logger.error(f"❌ Failed to save trade to database: {e}")
            raise

    async def get_recent_trades(self, limit: int = 100) -> List[Trade]:
        """
        Get recent trades ordered by entry time.

        Args:
            limit: Maximum number of trades to return (default: 100)

        Returns:
            List[Trade]: List of recent trade objects
        """
        try:
            async with self.session_factory() as session:
                stmt = (
                    select(Trade)
                    .order_by(Trade.entry_time.desc())
                    .limit(limit)
                )
                result = await session.execute(stmt)
                trades = result.scalars().all()
                logger.info(f"Retrieved {len(trades)} recent trades")
                return list(trades)

        except Exception as e:
            logger.error(f"❌ Failed to get recent trades: {e}")
            raise

    async def get_trades_by_session(
        self,
        session: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Trade]:
        """
        Get trades filtered by trading session and optional date range.

        Args:
            session: Trading session (TOKYO, LONDON, NY, SYDNEY, OVERLAP)
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List[Trade]: List of matching trades
        """
        try:
            async with self.session_factory() as session_db:
                # Build filter conditions
                conditions = [Trade.session == session.upper()]

                if start_date:
                    conditions.append(Trade.entry_time >= start_date)
                if end_date:
                    conditions.append(Trade.entry_time <= end_date)

                stmt = (
                    select(Trade)
                    .where(and_(*conditions))
                    .order_by(Trade.entry_time.desc())
                )
                result = await session_db.execute(stmt)
                trades = result.scalars().all()

                logger.info(
                    f"Retrieved {len(trades)} trades for session {session}"
                )
                return list(trades)

        except Exception as e:
            logger.error(f"❌ Failed to get trades by session: {e}")
            raise

    async def get_trades_by_pattern(
        self,
        pattern_type: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Trade]:
        """
        Get trades filtered by pattern type and optional date range.

        Args:
            pattern_type: Pattern type identifier
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List[Trade]: List of matching trades
        """
        try:
            async with self.session_factory() as session:
                # Build filter conditions
                conditions = [Trade.pattern_type == pattern_type]

                if start_date:
                    conditions.append(Trade.entry_time >= start_date)
                if end_date:
                    conditions.append(Trade.entry_time <= end_date)

                stmt = (
                    select(Trade)
                    .where(and_(*conditions))
                    .order_by(Trade.entry_time.desc())
                )
                result = await session.execute(stmt)
                trades = result.scalars().all()

                logger.info(
                    f"Retrieved {len(trades)} trades for pattern {pattern_type}"
                )
                return list(trades)

        except Exception as e:
            logger.error(f"❌ Failed to get trades by pattern: {e}")
            raise

    async def get_trade_by_id(self, trade_id: str) -> Optional[Trade]:
        """
        Get a specific trade by its ID.

        Args:
            trade_id: Unique trade identifier

        Returns:
            Optional[Trade]: Trade object if found, None otherwise
        """
        try:
            async with self.session_factory() as session:
                stmt = select(Trade).where(Trade.trade_id == trade_id)
                result = await session.execute(stmt)
                trade = result.scalar_one_or_none()

                if trade:
                    logger.info(f"Found trade: {trade_id}")
                else:
                    logger.info(f"Trade not found: {trade_id}")

                return trade

        except Exception as e:
            logger.error(f"❌ Failed to get trade by ID: {e}")
            raise

    async def update_trade(
        self, trade_id: str, update_data: Dict
    ) -> Optional[Trade]:
        """
        Update an existing trade with new data.

        Args:
            trade_id: Trade ID to update
            update_data: Dictionary of fields to update

        Returns:
            Optional[Trade]: Updated trade object if found, None otherwise
        """
        try:
            async with self.session_factory() as session:
                stmt = select(Trade).where(Trade.trade_id == trade_id)
                result = await session.execute(stmt)
                trade = result.scalar_one_or_none()

                if not trade:
                    logger.warning(f"Trade not found for update: {trade_id}")
                    return None

                # Update allowed fields
                for field, value in update_data.items():
                    if hasattr(trade, field):
                        # Convert numeric fields to Decimal
                        if field in ["exit_price", "pnl", "pnl_percentage"]:
                            value = self._to_decimal(value)
                        setattr(trade, field, value)

                await session.commit()
                await session.refresh(trade)

                logger.info(f"✅ Updated trade: {trade_id}")
                return trade

        except Exception as e:
            logger.error(f"❌ Failed to update trade: {e}")
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
