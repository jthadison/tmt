"""
Trade Synchronization Service

Manages real-time synchronization between OANDA trades and local database.
Runs periodic sync loops and handles trade lifecycle events.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from decimal import Decimal
import json
import uuid

from ..oanda_client import OandaClient
from ..event_bus import EventBus
from .trade_database import TradeDatabase, TradeStatus, CloseReason

logger = logging.getLogger(__name__)


class TradeSyncService:
    """Handles trade synchronization between OANDA and local database"""

    def __init__(
        self,
        oanda_client: Optional[OandaClient] = None,
        event_bus: Optional[EventBus] = None,
        sync_interval: int = 30,
        fast_sync_on_trade: bool = True
    ):
        self.oanda_client = oanda_client or OandaClient()
        self.event_bus = event_bus or EventBus()
        self.db = TradeDatabase()
        self.sync_interval = sync_interval
        self.fast_sync_on_trade = fast_sync_on_trade
        self.is_running = False
        self.sync_task = None
        self.last_sync = None
        self.sync_stats = {
            "total_syncs": 0,
            "successful_syncs": 0,
            "failed_syncs": 0,
            "last_error": None
        }

    async def initialize(self):
        """Initialize the sync service"""
        await self.db.initialize()
        logger.info(f"Trade sync service initialized (interval: {self.sync_interval}s)")

    async def start(self):
        """Start the synchronization loop"""
        if self.is_running:
            logger.warning("Sync service already running")
            return

        self.is_running = True
        self.sync_task = asyncio.create_task(self._sync_loop())
        logger.info("Trade sync service started")

        # Perform initial sync
        await self.sync_trades()

    async def stop(self):
        """Stop the synchronization loop"""
        self.is_running = False
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
        await self.db.close()
        logger.info("Trade sync service stopped")

    async def _sync_loop(self):
        """Main synchronization loop"""
        while self.is_running:
            try:
                await asyncio.sleep(self.sync_interval)
                await self.sync_trades()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
                self.sync_stats["failed_syncs"] += 1
                self.sync_stats["last_error"] = str(e)
                await asyncio.sleep(5)  # Brief pause on error

    async def sync_trades(self) -> Dict[str, Any]:
        """Perform trade synchronization with OANDA"""
        sync_start = datetime.now()
        sync_result = {
            "sync_time": sync_start.isoformat(),
            "trades_synced": 0,
            "trades_added": 0,
            "trades_updated": 0,
            "trades_closed": 0,
            "status": "success",
            "error_message": None
        }

        try:
            # Get trades from OANDA
            oanda_trades = await self._fetch_oanda_trades()

            # Get trades from database
            db_trades = await self.db.get_active_trades()
            db_trade_map = {t["trade_id"]: t for t in db_trades}

            # Process each OANDA trade
            for oanda_trade in oanda_trades:
                trade_id = str(oanda_trade.get("id"))

                if trade_id in db_trade_map:
                    # Update existing trade
                    if await self._update_trade(oanda_trade, db_trade_map[trade_id]):
                        sync_result["trades_updated"] += 1
                else:
                    # Add new trade
                    if await self._add_trade(oanda_trade):
                        sync_result["trades_added"] += 1
                        await self._emit_trade_event(trade_id, "trade_opened", oanda_trade)

                sync_result["trades_synced"] += 1

            # Check for closed trades
            oanda_trade_ids = {str(t.get("id")) for t in oanda_trades}
            for db_trade in db_trades:
                if db_trade["trade_id"] not in oanda_trade_ids and db_trade["status"] == TradeStatus.OPEN:
                    # Trade was closed
                    await self._close_trade(db_trade["trade_id"])
                    sync_result["trades_closed"] += 1
                    await self._emit_trade_event(db_trade["trade_id"], "trade_closed", db_trade)

            # Update sync stats
            self.sync_stats["total_syncs"] += 1
            self.sync_stats["successful_syncs"] += 1
            self.last_sync = sync_start

            # Calculate sync duration
            sync_duration = (datetime.now() - sync_start).total_seconds() * 1000
            sync_result["sync_duration_ms"] = int(sync_duration)

            # Record sync history
            await self.db.record_sync_history(sync_result)

            logger.info(
                f"Sync completed: {sync_result['trades_synced']} trades, "
                f"{sync_result['trades_added']} added, {sync_result['trades_updated']} updated, "
                f"{sync_result['trades_closed']} closed"
            )

        except Exception as e:
            logger.error(f"Sync error: {e}")
            sync_result["status"] = "failed"
            sync_result["error_message"] = str(e)
            self.sync_stats["failed_syncs"] += 1
            self.sync_stats["last_error"] = str(e)
            await self.db.record_sync_history(sync_result)

        return sync_result

    async def _fetch_oanda_trades(self) -> List[Dict[str, Any]]:
        """Fetch all trades from OANDA"""
        try:
            # Get account details first
            account_info = await self.oanda_client.get_account()
            account_id = account_info.get("account", {}).get("id")

            # Get open trades
            open_trades = await self.oanda_client.get_open_trades()
            trades_list = open_trades.get("trades", [])

            # Get recent closed trades (last 7 days)
            # Note: This would need to be implemented in OandaClient
            # For now, we'll only sync open trades

            return trades_list

        except Exception as e:
            logger.error(f"Error fetching OANDA trades: {e}")
            return []

    async def _add_trade(self, oanda_trade: Dict[str, Any]) -> bool:
        """Add a new trade to database"""
        trade_data = self._convert_oanda_to_db_format(oanda_trade)
        trade_data["status"] = TradeStatus.OPEN
        return await self.db.upsert_trade(trade_data)

    async def _update_trade(self, oanda_trade: Dict[str, Any], db_trade: Dict[str, Any]) -> bool:
        """Update an existing trade"""
        trade_data = self._convert_oanda_to_db_format(oanda_trade)

        # Check if there are actual changes
        changed = False
        for key in ["units", "stop_loss", "take_profit", "pnl_unrealized"]:
            if trade_data.get(key) != db_trade.get(key):
                changed = True
                break

        if changed:
            return await self.db.upsert_trade(trade_data)
        return False

    async def _close_trade(self, trade_id: str) -> bool:
        """Mark a trade as closed"""
        # Fetch final details from OANDA if possible
        # For now, just mark as closed
        trade_data = {
            "trade_id": trade_id,
            "status": TradeStatus.CLOSED,
            "close_time": datetime.now().isoformat(),
            "close_reason": CloseReason.UNKNOWN
        }
        return await self.db.upsert_trade(trade_data)

    def _convert_oanda_to_db_format(self, oanda_trade: Dict[str, Any]) -> Dict[str, Any]:
        """Convert OANDA trade format to database format"""
        return {
            "trade_id": str(oanda_trade.get("id")),
            "internal_id": str(uuid.uuid4()),
            "account_id": self.oanda_client.account_id if self.oanda_client else "unknown",
            "instrument": oanda_trade.get("instrument", "").replace("_", "/"),
            "direction": "buy" if float(oanda_trade.get("currentUnits", 0)) > 0 else "sell",
            "units": abs(int(float(oanda_trade.get("currentUnits", 0)))),
            "entry_price": float(oanda_trade.get("price", 0)),
            "entry_time": oanda_trade.get("openTime"),
            "stop_loss": float(oanda_trade.get("stopLossOrder", {}).get("price", 0)) if oanda_trade.get("stopLossOrder") else None,
            "take_profit": float(oanda_trade.get("takeProfitOrder", {}).get("price", 0)) if oanda_trade.get("takeProfitOrder") else None,
            "pnl_unrealized": float(oanda_trade.get("unrealizedPL", 0)),
            "commission": float(oanda_trade.get("financing", 0)),
            "metadata": {
                "oanda_state": oanda_trade.get("state"),
                "margin_used": oanda_trade.get("marginUsed"),
                "initial_units": oanda_trade.get("initialUnits")
            }
        }

    async def _emit_trade_event(self, trade_id: str, event_type: str, event_data: Dict[str, Any]):
        """Emit a trade event to the event bus"""
        if self.event_bus and hasattr(self.event_bus, 'publish'):
            event = {
                "trade_id": trade_id,
                "event_type": event_type,
                "timestamp": datetime.now().isoformat(),
                "data": event_data
            }
            # EventBus.publish only takes event data, not topic name
            await self.event_bus.publish(event)

        # Also record in database for audit trail
        await self.db.add_trade_event(trade_id, event_type, event_data)

    async def force_sync(self) -> Dict[str, Any]:
        """Force an immediate synchronization"""
        logger.info("Forcing trade synchronization")
        return await self.sync_trades()

    async def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status and statistics"""
        trade_counts = await self.db.get_trade_count()
        pnl_data = await self.db.calculate_total_pnl()

        return {
            "is_running": self.is_running,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "sync_interval": self.sync_interval,
            "sync_stats": self.sync_stats,
            "trade_counts": trade_counts,
            "pnl": pnl_data,
            "database_path": self.db.db_path
        }

    async def handle_signal_execution(self, signal_data: Dict[str, Any]):
        """Handle a new signal being executed"""
        # Create preliminary trade record
        trade_data = {
            "trade_id": f"pending_{uuid.uuid4()}",
            "internal_id": str(uuid.uuid4()),
            "signal_id": signal_data.get("signal_id"),
            "account_id": signal_data.get("account_id"),
            "instrument": signal_data.get("instrument"),
            "direction": signal_data.get("direction"),
            "units": signal_data.get("units"),
            "status": TradeStatus.PENDING,
            "metadata": {"signal_data": signal_data}
        }

        await self.db.upsert_trade(trade_data)

        # If fast sync is enabled, trigger immediate sync after brief delay
        if self.fast_sync_on_trade:
            await asyncio.sleep(2)  # Allow time for OANDA to process
            await self.force_sync()