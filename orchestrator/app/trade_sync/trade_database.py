"""
Trade Database Management

Handles all database operations for trade storage, retrieval, and updates.
Uses SQLite for development, easily upgradeable to PostgreSQL for production.
"""

import aiosqlite
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class TradeStatus(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class CloseReason(str, Enum):
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    MANUAL = "manual"
    SIGNAL = "signal"
    MARGIN_CALL = "margin_call"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class TradeDatabase:
    """Manages trade data persistence and retrieval"""

    def __init__(self, db_path: str = "trades.db"):
        self.db_path = db_path
        self.connection = None

    async def initialize(self):
        """Initialize database connection and create tables if needed"""
        self.connection = await aiosqlite.connect(self.db_path)
        self.connection.row_factory = aiosqlite.Row
        await self.create_tables()
        logger.info(f"Trade database initialized at {self.db_path}")

    async def create_tables(self):
        """Create database tables if they don't exist"""
        await self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                internal_id TEXT UNIQUE NOT NULL,
                signal_id TEXT,
                account_id TEXT NOT NULL,
                instrument TEXT NOT NULL,
                direction TEXT NOT NULL,
                units INTEGER NOT NULL,
                entry_price REAL,
                entry_time TEXT,
                stop_loss REAL,
                take_profit REAL,
                close_price REAL,
                close_time TEXT,
                status TEXT NOT NULL,
                pnl_realized REAL DEFAULT 0,
                pnl_unrealized REAL DEFAULT 0,
                commission REAL DEFAULT 0,
                swap REAL DEFAULT 0,
                close_reason TEXT,
                last_sync_time TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
            CREATE INDEX IF NOT EXISTS idx_trades_account ON trades(account_id);
            CREATE INDEX IF NOT EXISTS idx_trades_instrument ON trades(instrument);
            CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time);
            CREATE INDEX IF NOT EXISTS idx_trades_signal ON trades(signal_id);

            CREATE TABLE IF NOT EXISTS sync_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_time TEXT NOT NULL,
                trades_synced INTEGER DEFAULT 0,
                trades_added INTEGER DEFAULT 0,
                trades_updated INTEGER DEFAULT 0,
                trades_closed INTEGER DEFAULT 0,
                sync_duration_ms INTEGER,
                status TEXT,
                error_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS trade_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trade_id) REFERENCES trades(trade_id)
            );

            CREATE INDEX IF NOT EXISTS idx_events_trade ON trade_events(trade_id);
            CREATE INDEX IF NOT EXISTS idx_events_type ON trade_events(event_type);
        """)
        await self.connection.commit()

    async def upsert_trade(self, trade_data: Dict[str, Any]) -> bool:
        """Insert or update a trade record"""
        try:
            metadata = json.dumps(trade_data.get("metadata", {}))

            await self.connection.execute("""
                INSERT INTO trades (
                    trade_id, internal_id, signal_id, account_id, instrument,
                    direction, units, entry_price, entry_time, stop_loss,
                    take_profit, close_price, close_time, status,
                    pnl_realized, pnl_unrealized, commission, swap,
                    close_reason, last_sync_time, metadata, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(trade_id) DO UPDATE SET
                    status = excluded.status,
                    close_price = excluded.close_price,
                    close_time = excluded.close_time,
                    pnl_realized = excluded.pnl_realized,
                    pnl_unrealized = excluded.pnl_unrealized,
                    commission = excluded.commission,
                    swap = excluded.swap,
                    close_reason = excluded.close_reason,
                    last_sync_time = excluded.last_sync_time,
                    metadata = excluded.metadata,
                    updated_at = excluded.updated_at
            """, (
                trade_data["trade_id"],
                trade_data.get("internal_id", trade_data["trade_id"]),
                trade_data.get("signal_id"),
                trade_data["account_id"],
                trade_data["instrument"],
                trade_data["direction"],
                trade_data["units"],
                trade_data.get("entry_price"),
                trade_data.get("entry_time"),
                trade_data.get("stop_loss"),
                trade_data.get("take_profit"),
                trade_data.get("close_price"),
                trade_data.get("close_time"),
                trade_data["status"],
                trade_data.get("pnl_realized", 0),
                trade_data.get("pnl_unrealized", 0),
                trade_data.get("commission", 0),
                trade_data.get("swap", 0),
                trade_data.get("close_reason"),
                datetime.now().isoformat(),
                metadata,
                datetime.now().isoformat()
            ))

            await self.connection.commit()
            return True

        except Exception as e:
            logger.error(f"Error upserting trade: {e}")
            return False

    async def get_active_trades(self) -> List[Dict[str, Any]]:
        """Get all open trades"""
        cursor = await self.connection.execute("""
            SELECT * FROM trades
            WHERE status IN (?, ?)
            ORDER BY entry_time DESC
        """, (TradeStatus.OPEN, TradeStatus.PENDING))

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_closed_trades(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get closed trades for specified period"""
        since = (datetime.now() - timedelta(days=days)).isoformat()

        cursor = await self.connection.execute("""
            SELECT * FROM trades
            WHERE status = ? AND close_time > ?
            ORDER BY close_time DESC
        """, (TradeStatus.CLOSED, since))

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_trade_by_id(self, trade_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific trade by ID"""
        cursor = await self.connection.execute("""
            SELECT * FROM trades WHERE trade_id = ?
        """, (trade_id,))

        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_trades_by_signal(self, signal_id: str) -> List[Dict[str, Any]]:
        """Get all trades associated with a signal"""
        cursor = await self.connection.execute("""
            SELECT * FROM trades
            WHERE signal_id = ?
            ORDER BY entry_time DESC
        """, (signal_id,))

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_performance_stats(self, days: int = 30) -> Dict[str, Any]:
        """Calculate performance statistics"""
        since = (datetime.now() - timedelta(days=days)).isoformat()

        # Get all closed trades in period
        cursor = await self.connection.execute("""
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl_realized > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN pnl_realized < 0 THEN 1 ELSE 0 END) as losing_trades,
                SUM(pnl_realized) as total_pnl,
                AVG(pnl_realized) as avg_pnl,
                MAX(pnl_realized) as best_trade,
                MIN(pnl_realized) as worst_trade,
                SUM(commission + swap) as total_costs
            FROM trades
            WHERE status = ? AND close_time > ?
        """, (TradeStatus.CLOSED, since))

        stats = dict(await cursor.fetchone())

        # Calculate win rate
        if stats["total_trades"] > 0:
            stats["win_rate"] = (stats["winning_trades"] / stats["total_trades"]) * 100
        else:
            stats["win_rate"] = 0

        # Get open positions
        cursor = await self.connection.execute("""
            SELECT COUNT(*) as open_positions,
                   SUM(pnl_unrealized) as unrealized_pnl
            FROM trades
            WHERE status = ?
        """, (TradeStatus.OPEN,))

        open_stats = dict(await cursor.fetchone())
        stats.update(open_stats)

        return stats

    async def record_sync_history(self, sync_data: Dict[str, Any]):
        """Record synchronization history"""
        await self.connection.execute("""
            INSERT INTO sync_history (
                sync_time, trades_synced, trades_added, trades_updated,
                trades_closed, sync_duration_ms, status, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sync_data["sync_time"],
            sync_data.get("trades_synced", 0),
            sync_data.get("trades_added", 0),
            sync_data.get("trades_updated", 0),
            sync_data.get("trades_closed", 0),
            sync_data.get("sync_duration_ms", 0),
            sync_data.get("status", "success"),
            sync_data.get("error_message")
        ))
        await self.connection.commit()

    async def add_trade_event(self, trade_id: str, event_type: str, event_data: Dict[str, Any]):
        """Add a trade event for audit trail"""
        await self.connection.execute("""
            INSERT INTO trade_events (trade_id, event_type, event_data)
            VALUES (?, ?, ?)
        """, (trade_id, event_type, json.dumps(event_data)))
        await self.connection.commit()

    async def get_trade_count(self) -> Dict[str, int]:
        """Get trade counts by status"""
        cursor = await self.connection.execute("""
            SELECT status, COUNT(*) as count
            FROM trades
            GROUP BY status
        """)

        rows = await cursor.fetchall()
        return {row["status"]: row["count"] for row in rows}

    async def calculate_total_pnl(self) -> Dict[str, float]:
        """Calculate total P&L (realized and unrealized)"""
        cursor = await self.connection.execute("""
            SELECT
                SUM(CASE WHEN status = 'closed' THEN pnl_realized ELSE 0 END) as realized_pnl,
                SUM(CASE WHEN status = 'open' THEN pnl_unrealized ELSE 0 END) as unrealized_pnl
            FROM trades
        """)

        row = await cursor.fetchone()
        return {
            "realized_pnl": row["realized_pnl"] or 0,
            "unrealized_pnl": row["unrealized_pnl"] or 0,
            "total_pnl": (row["realized_pnl"] or 0) + (row["unrealized_pnl"] or 0)
        }

    async def close(self):
        """Close database connection"""
        if self.connection:
            await self.connection.close()
            logger.info("Trade database connection closed")