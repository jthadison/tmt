"""
Signal Database Layer

Provides persistent storage for trading signals, executions, and performance tracking
using SQLite with proper schema design and async support.
"""

import asyncio
import aiosqlite
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import asdict

# Import with absolute path since we're using this from different contexts
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from signals.signal_metadata import TradingSignal

logger = logging.getLogger(__name__)


class SignalDatabase:
    """
    Async SQLite database layer for signal persistence and retrieval.

    Features:
    - Signal storage with comprehensive metadata
    - Execution tracking and signal-to-trade correlation
    - Performance analytics and historical analysis
    - Async operations for non-blocking database access
    """

    def __init__(self, db_path: str = "signals.db"):
        """
        Initialize the signal database.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Ensure we have the full path
        if not self.db_path.is_absolute():
            self.db_path = Path(__file__).parent / self.db_path

        logger.info(f"Signal database initialized: {self.db_path}")

    async def initialize_database(self):
        """Create database tables if they don't exist"""
        async with aiosqlite.connect(self.db_path) as db:
            # Enable foreign key constraints
            await db.execute("PRAGMA foreign_keys = ON")

            # Signals table - main signal storage
            await db.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    signal_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    signal_type TEXT NOT NULL,  -- 'long' or 'short'
                    pattern_type TEXT NOT NULL,
                    confidence REAL NOT NULL,

                    -- Price levels (stored as strings for precision)
                    entry_price TEXT NOT NULL,
                    stop_loss TEXT NOT NULL,
                    take_profit_1 TEXT NOT NULL,
                    take_profit_2 TEXT,
                    take_profit_3 TEXT,

                    -- Timing information
                    generated_at TIMESTAMP NOT NULL,
                    valid_until TIMESTAMP NOT NULL,
                    expected_hold_time_hours INTEGER,

                    -- Status tracking
                    status TEXT DEFAULT 'active',  -- 'active', 'executed', 'expired', 'cancelled'
                    execution_status TEXT DEFAULT 'pending',  -- 'pending', 'filled', 'partial', 'rejected'

                    -- Metadata (stored as JSON)
                    confidence_breakdown TEXT,  -- JSON of ConfidenceBreakdown
                    market_context TEXT,        -- JSON of MarketContext
                    pattern_details TEXT,       -- JSON of PatternDetails
                    entry_confirmation TEXT,    -- JSON of EntryConfirmation
                    contributing_factors TEXT,  -- JSON array of factors

                    -- Performance tracking
                    risk_reward_ratio REAL,
                    position_size REAL,
                    account_id TEXT,

                    -- Audit trail
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Signal executions table - track actual trade executions
            await db.execute("""
                CREATE TABLE IF NOT EXISTS signal_executions (
                    execution_id TEXT PRIMARY KEY,
                    signal_id TEXT NOT NULL,
                    trade_id TEXT,  -- External trade ID (OANDA, MT4, etc.)

                    -- Execution details
                    executed_at TIMESTAMP NOT NULL,
                    execution_price TEXT NOT NULL,
                    executed_quantity REAL NOT NULL,
                    execution_type TEXT,  -- 'market', 'limit', 'stop'

                    -- Fill information
                    fill_status TEXT DEFAULT 'pending',  -- 'pending', 'filled', 'partial', 'rejected'
                    filled_quantity REAL DEFAULT 0,
                    average_fill_price TEXT,
                    slippage_points REAL,

                    -- Performance tracking
                    pnl REAL,
                    pnl_percentage REAL,
                    holding_time_minutes INTEGER,
                    max_favorable_excursion REAL,
                    max_adverse_excursion REAL,

                    -- Metadata
                    broker TEXT,
                    account_id TEXT,
                    commission REAL DEFAULT 0,
                    swap REAL DEFAULT 0,

                    -- Audit trail
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (signal_id) REFERENCES signals (signal_id)
                )
            """)

            # Signal performance table - aggregated performance metrics
            await db.execute("""
                CREATE TABLE IF NOT EXISTS signal_performance (
                    performance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id TEXT NOT NULL,

                    -- Time periods
                    period_start TIMESTAMP NOT NULL,
                    period_end TIMESTAMP,

                    -- Performance metrics
                    total_pnl REAL,
                    win_rate REAL,
                    profit_factor REAL,
                    sharpe_ratio REAL,
                    max_drawdown REAL,
                    average_win REAL,
                    average_loss REAL,

                    -- Signal quality metrics
                    confidence_accuracy REAL,  -- How well confidence predicted success
                    pattern_success_rate REAL,
                    risk_reward_achieved REAL,

                    -- Statistical data
                    total_signals INTEGER DEFAULT 1,
                    winning_signals INTEGER DEFAULT 0,
                    losing_signals INTEGER DEFAULT 0,

                    -- Metadata
                    performance_period TEXT,  -- 'daily', 'weekly', 'monthly'
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (signal_id) REFERENCES signals (signal_id)
                )
            """)

            # Indexes for performance
            await db.execute("CREATE INDEX IF NOT EXISTS idx_signals_symbol_time ON signals (symbol, generated_at)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_signals_status ON signals (status, execution_status)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_signals_pattern ON signals (pattern_type, confidence)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_executions_signal ON signal_executions (signal_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_executions_time ON signal_executions (executed_at)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_performance_period ON signal_performance (period_start, period_end)")

            await db.commit()
            logger.info("Signal database schema initialized successfully")

    async def store_signal(self, signal: TradingSignal, account_id: str = None) -> bool:
        """
        Store a trading signal in the database.

        Args:
            signal: TradingSignal object to store
            account_id: Optional account identifier

        Returns:
            bool: Success status
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Calculate risk-reward ratio
                risk = float(abs(signal.entry_price - signal.stop_loss))
                reward = float(abs(signal.take_profit_1 - signal.entry_price))
                risk_reward_ratio = reward / risk if risk > 0 else 0

                await db.execute("""
                    INSERT INTO signals (
                        signal_id, symbol, timeframe, signal_type, pattern_type, confidence,
                        entry_price, stop_loss, take_profit_1, take_profit_2, take_profit_3,
                        generated_at, valid_until, expected_hold_time_hours,
                        confidence_breakdown, market_context, pattern_details,
                        entry_confirmation, contributing_factors,
                        risk_reward_ratio, account_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    signal.signal_id,
                    signal.symbol,
                    signal.timeframe,
                    signal.signal_type,
                    signal.pattern_type,
                    signal.confidence,
                    str(signal.entry_price),
                    str(signal.stop_loss),
                    str(signal.take_profit_1),
                    str(signal.take_profit_2) if signal.take_profit_2 else None,
                    str(signal.take_profit_3) if signal.take_profit_3 else None,
                    signal.generated_at.isoformat(),
                    signal.valid_until.isoformat(),
                    signal.expected_hold_time_hours,
                    json.dumps(signal.confidence_breakdown.to_dict()),
                    json.dumps(signal.market_context.to_dict()),
                    json.dumps(signal.pattern_details.to_dict()),
                    json.dumps(signal.entry_confirmation.to_dict()),
                    json.dumps(signal.contributing_factors),
                    risk_reward_ratio,
                    account_id
                ))

                await db.commit()
                logger.info(f"Stored signal {signal.signal_id} for {signal.symbol}")
                return True

        except Exception as e:
            logger.error(f"Error storing signal {signal.signal_id}: {e}")
            return False

    async def get_signal_history(self,
                               symbol: str = None,
                               start_date: datetime = None,
                               end_date: datetime = None,
                               pattern_type: str = None,
                               min_confidence: float = None,
                               limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve signal history with optional filtering.

        Args:
            symbol: Filter by symbol
            start_date: Start date for filtering
            end_date: End date for filtering
            pattern_type: Filter by pattern type
            min_confidence: Minimum confidence threshold
            limit: Maximum number of signals to return

        Returns:
            List of signal dictionaries
        """
        try:
            query = "SELECT * FROM signals WHERE 1=1"
            params = []

            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)

            if start_date:
                query += " AND generated_at >= ?"
                params.append(start_date.isoformat())

            if end_date:
                query += " AND generated_at <= ?"
                params.append(end_date.isoformat())

            if pattern_type:
                query += " AND pattern_type = ?"
                params.append(pattern_type)

            if min_confidence:
                query += " AND confidence >= ?"
                params.append(min_confidence)

            query += " ORDER BY generated_at DESC LIMIT ?"
            params.append(limit)

            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()

                signals = []
                for row in rows:
                    signal_dict = dict(row)

                    # Parse JSON fields
                    for json_field in ['confidence_breakdown', 'market_context', 'pattern_details',
                                     'entry_confirmation', 'contributing_factors']:
                        if signal_dict[json_field]:
                            signal_dict[json_field] = json.loads(signal_dict[json_field])

                    # Parse timestamps
                    for timestamp_field in ['generated_at', 'valid_until', 'created_at', 'updated_at']:
                        if signal_dict[timestamp_field]:
                            signal_dict[timestamp_field] = datetime.fromisoformat(signal_dict[timestamp_field])

                    signals.append(signal_dict)

                logger.info(f"Retrieved {len(signals)} signals from history")
                return signals

        except Exception as e:
            logger.error(f"Error retrieving signal history: {e}")
            return []

    async def get_recent_signals(self, hours: int = 24, symbol: str = None) -> List[Dict[str, Any]]:
        """
        Get signals generated in the last N hours.

        Args:
            hours: Number of hours to look back
            symbol: Optional symbol filter

        Returns:
            List of recent signal dictionaries
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date.replace(hour=end_date.hour - hours)

        return await self.get_signal_history(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            limit=50
        )

    async def record_signal_execution(self,
                                    signal_id: str,
                                    trade_id: str,
                                    executed_at: datetime,
                                    execution_price: Decimal,
                                    executed_quantity: float,
                                    broker: str = 'OANDA',
                                    account_id: str = None) -> bool:
        """
        Record a signal execution/trade.

        Args:
            signal_id: ID of the executed signal
            trade_id: External trade ID
            executed_at: Execution timestamp
            execution_price: Price at which trade was executed
            executed_quantity: Quantity/units executed
            broker: Broker name
            account_id: Account identifier

        Returns:
            bool: Success status
        """
        try:
            execution_id = f"exec_{trade_id}_{int(executed_at.timestamp())}"

            async with aiosqlite.connect(self.db_path) as db:
                # Insert execution record
                await db.execute("""
                    INSERT INTO signal_executions (
                        execution_id, signal_id, trade_id, executed_at,
                        execution_price, executed_quantity, fill_status,
                        filled_quantity, broker, account_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution_id,
                    signal_id,
                    trade_id,
                    executed_at.isoformat(),
                    str(execution_price),
                    executed_quantity,
                    'filled',
                    executed_quantity,
                    broker,
                    account_id
                ))

                # Update signal status
                await db.execute("""
                    UPDATE signals
                    SET execution_status = 'filled', updated_at = CURRENT_TIMESTAMP
                    WHERE signal_id = ?
                """, (signal_id,))

                await db.commit()
                logger.info(f"Recorded execution for signal {signal_id}: trade {trade_id}")
                return True

        except Exception as e:
            logger.error(f"Error recording execution for signal {signal_id}: {e}")
            return False

    async def update_signal_performance(self,
                                      signal_id: str,
                                      pnl: float,
                                      pnl_percentage: float = None,
                                      holding_time_minutes: int = None,
                                      max_favorable_excursion: float = None,
                                      max_adverse_excursion: float = None) -> bool:
        """
        Update performance metrics for a signal execution.

        Args:
            signal_id: Signal identifier
            pnl: Profit/loss amount
            pnl_percentage: P&L as percentage
            holding_time_minutes: How long position was held
            max_favorable_excursion: Best profit point reached
            max_adverse_excursion: Worst loss point reached

        Returns:
            bool: Success status
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE signal_executions
                    SET pnl = ?, pnl_percentage = ?, holding_time_minutes = ?,
                        max_favorable_excursion = ?, max_adverse_excursion = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE signal_id = ?
                """, (
                    pnl, pnl_percentage, holding_time_minutes,
                    max_favorable_excursion, max_adverse_excursion, signal_id
                ))

                await db.commit()
                logger.info(f"Updated performance for signal {signal_id}: P&L {pnl}")
                return True

        except Exception as e:
            logger.error(f"Error updating performance for signal {signal_id}: {e}")
            return False

    async def get_signal_statistics(self,
                                  symbol: str = None,
                                  days: int = 30) -> Dict[str, Any]:
        """
        Get aggregated signal statistics.

        Args:
            symbol: Optional symbol filter
            days: Number of days to analyze

        Returns:
            Dictionary with signal statistics
        """
        try:
            start_date = datetime.now(timezone.utc).replace(
                day=datetime.now().day - days
            )

            query_base = """
                SELECT
                    COUNT(*) as total_signals,
                    AVG(confidence) as avg_confidence,
                    COUNT(CASE WHEN execution_status = 'filled' THEN 1 END) as executed_signals,
                    AVG(risk_reward_ratio) as avg_risk_reward
                FROM signals
                WHERE generated_at >= ?
            """
            params = [start_date.isoformat()]

            if symbol:
                query_base += " AND symbol = ?"
                params.append(symbol)

            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query_base, params)
                stats = await cursor.fetchone()

                # Get performance stats
                perf_query = """
                    SELECT
                        AVG(pnl) as avg_pnl,
                        COUNT(CASE WHEN pnl > 0 THEN 1 END) as winning_trades,
                        COUNT(CASE WHEN pnl < 0 THEN 1 END) as losing_trades,
                        AVG(holding_time_minutes) as avg_holding_time
                    FROM signal_executions se
                    JOIN signals s ON se.signal_id = s.signal_id
                    WHERE se.executed_at >= ?
                """
                perf_params = [start_date.isoformat()]

                if symbol:
                    perf_query += " AND s.symbol = ?"
                    perf_params.append(symbol)

                cursor = await db.execute(perf_query, perf_params)
                perf_stats = await cursor.fetchone()

                # Calculate derived metrics
                total_signals = stats[0] if stats[0] else 0
                executed_signals = stats[2] if stats[2] else 0
                winning_trades = perf_stats[1] if perf_stats[1] else 0
                losing_trades = perf_stats[2] if perf_stats[2] else 0
                total_trades = winning_trades + losing_trades

                return {
                    'period_days': days,
                    'symbol': symbol or 'all',
                    'total_signals': total_signals,
                    'executed_signals': executed_signals,
                    'conversion_rate': (executed_signals / total_signals * 100) if total_signals > 0 else 0,
                    'avg_confidence': float(stats[1]) if stats[1] else 0,
                    'avg_risk_reward': float(stats[3]) if stats[3] else 0,
                    'avg_pnl': float(perf_stats[0]) if perf_stats[0] else 0,
                    'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0,
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'losing_trades': losing_trades,
                    'avg_holding_time_hours': float(perf_stats[3]) / 60 if perf_stats[3] else 0
                }

        except Exception as e:
            logger.error(f"Error getting signal statistics: {e}")
            return {}

    async def cleanup_old_signals(self, days_to_keep: int = 90) -> int:
        """
        Remove old signal records to maintain database performance.

        Args:
            days_to_keep: Number of days of data to retain

        Returns:
            int: Number of records deleted
        """
        try:
            cutoff_date = datetime.now(timezone.utc).replace(
                day=datetime.now().day - days_to_keep
            )

            async with aiosqlite.connect(self.db_path) as db:
                # Delete old executions first (foreign key constraint)
                cursor = await db.execute("""
                    DELETE FROM signal_executions
                    WHERE executed_at < ?
                """, (cutoff_date.isoformat(),))
                executions_deleted = cursor.rowcount

                # Delete old signals
                cursor = await db.execute("""
                    DELETE FROM signals
                    WHERE generated_at < ?
                """, (cutoff_date.isoformat(),))
                signals_deleted = cursor.rowcount

                # Delete old performance records
                cursor = await db.execute("""
                    DELETE FROM signal_performance
                    WHERE period_end < ?
                """, (cutoff_date.isoformat(),))
                performance_deleted = cursor.rowcount

                await db.commit()

                total_deleted = executions_deleted + signals_deleted + performance_deleted
                logger.info(f"Cleaned up {total_deleted} old database records")
                return total_deleted

        except Exception as e:
            logger.error(f"Error cleaning up old signals: {e}")
            return 0


# Singleton instance for easy access
_signal_db_instance = None

async def get_signal_database() -> SignalDatabase:
    """Get or create the signal database instance"""
    global _signal_db_instance

    if _signal_db_instance is None:
        _signal_db_instance = SignalDatabase()
        await _signal_db_instance.initialize_database()

    return _signal_db_instance