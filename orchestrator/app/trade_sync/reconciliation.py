"""
Trade Reconciliation System

Validates data consistency between OANDA and local database,
detects discrepancies, and performs automatic corrections.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import json

from ..oanda_client import OandaClient
from ..config import get_settings
from .trade_database import TradeDatabase, TradeStatus

logger = logging.getLogger(__name__)


class ReconciliationIssue:
    """Represents a detected reconciliation issue"""

    def __init__(self, issue_type: str, trade_id: str, details: Dict[str, Any]):
        self.issue_type = issue_type
        self.trade_id = trade_id
        self.details = details
        self.timestamp = datetime.now()
        self.resolved = False
        self.resolution = None


class TradeReconciliation:
    """Handles trade data reconciliation and validation"""

    def __init__(
        self,
        oanda_client: Optional[OandaClient] = None,
        reconciliation_interval_hours: Optional[int] = None,
        auto_fix: Optional[bool] = None
    ):
        self.settings = get_settings()
        self.oanda_client = oanda_client or OandaClient()
        self.db = TradeDatabase()

        # Use configuration values with fallbacks from parameters
        interval_hours = reconciliation_interval_hours if reconciliation_interval_hours is not None else self.settings.trade_reconciliation_interval_hours
        self.reconciliation_interval = timedelta(hours=interval_hours)
        self.auto_fix = auto_fix if auto_fix is not None else self.settings.trade_sync_auto_fix
        self.last_reconciliation = None
        self.issues = []
        self.is_running = False
        self.reconciliation_task = None
        self.stats = {
            "total_reconciliations": 0,
            "issues_detected": 0,
            "issues_fixed": 0,
            "last_issue": None
        }

    async def initialize(self):
        """Initialize the reconciliation service"""
        await self.db.initialize()
        logger.info("Trade reconciliation service initialized")

    async def start(self):
        """Start the reconciliation loop"""
        if self.is_running:
            logger.warning("Reconciliation service already running")
            return

        self.is_running = True
        self.reconciliation_task = asyncio.create_task(self._reconciliation_loop())
        logger.info("Trade reconciliation service started")

    async def stop(self):
        """Stop the reconciliation loop"""
        self.is_running = False
        if self.reconciliation_task:
            self.reconciliation_task.cancel()
            try:
                await self.reconciliation_task
            except asyncio.CancelledError:
                pass
        await self.db.close()
        logger.info("Trade reconciliation service stopped")

    async def _reconciliation_loop(self):
        """Main reconciliation loop"""
        while self.is_running:
            try:
                await asyncio.sleep(self.reconciliation_interval.total_seconds())
                await self.perform_reconciliation()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Reconciliation loop error: {e}")
                await asyncio.sleep(60)  # Pause on error

    async def perform_reconciliation(self) -> Dict[str, Any]:
        """Perform comprehensive reconciliation"""
        logger.info("Starting trade reconciliation")
        reconciliation_start = datetime.now()
        self.issues = []

        results = {
            "timestamp": reconciliation_start.isoformat(),
            "checks_performed": [],
            "issues_found": 0,
            "issues_fixed": 0,
            "status": "success"
        }

        try:
            # Perform various reconciliation checks
            await self._check_trade_counts(results)
            await self._check_pnl_consistency(results)
            await self._check_position_consistency(results)
            await self._check_orphaned_trades(results)
            await self._check_data_integrity(results)

            # Process and fix issues if auto_fix is enabled
            if self.auto_fix and self.issues:
                fixed_count = await self._fix_issues()
                results["issues_fixed"] = fixed_count

            results["issues_found"] = len(self.issues)
            self.stats["total_reconciliations"] += 1
            self.stats["issues_detected"] += len(self.issues)
            self.last_reconciliation = reconciliation_start

            if self.issues:
                self.stats["last_issue"] = reconciliation_start.isoformat()
                logger.warning(f"Reconciliation found {len(self.issues)} issues")
            else:
                logger.info("Reconciliation completed with no issues")

        except Exception as e:
            logger.error(f"Reconciliation error: {e}")
            results["status"] = "failed"
            results["error"] = str(e)

        return results

    async def _check_trade_counts(self, results: Dict[str, Any]):
        """Verify trade counts match between OANDA and database"""
        try:
            # Get OANDA trade count
            oanda_trades = await self.oanda_client.get_open_trades()
            oanda_count = len(oanda_trades.get("trades", []))

            # Get database trade count
            db_counts = await self.db.get_trade_count()
            db_open_count = db_counts.get(TradeStatus.OPEN, 0)

            if oanda_count != db_open_count:
                issue = ReconciliationIssue(
                    "trade_count_mismatch",
                    "N/A",
                    {
                        "oanda_count": oanda_count,
                        "db_count": db_open_count,
                        "difference": oanda_count - db_open_count
                    }
                )
                self.issues.append(issue)
                logger.warning(f"Trade count mismatch: OANDA={oanda_count}, DB={db_open_count}")

            results["checks_performed"].append("trade_count")

        except Exception as e:
            logger.error(f"Error checking trade counts: {e}")

    async def _check_pnl_consistency(self, results: Dict[str, Any]):
        """Verify P&L calculations are consistent"""
        try:
            # Get OANDA account P&L
            account_info = await self.oanda_client.get_account()
            oanda_pnl = float(account_info.get("account", {}).get("unrealizedPL", 0))

            # Get database calculated P&L
            db_pnl = await self.db.calculate_total_pnl()
            db_unrealized = db_pnl.get("unrealized_pnl", 0)

            # Allow small tolerance for floating point differences
            tolerance = 0.01
            if abs(oanda_pnl - db_unrealized) > tolerance:
                issue = ReconciliationIssue(
                    "pnl_mismatch",
                    "N/A",
                    {
                        "oanda_pnl": oanda_pnl,
                        "db_pnl": db_unrealized,
                        "difference": oanda_pnl - db_unrealized
                    }
                )
                self.issues.append(issue)
                logger.warning(f"P&L mismatch: OANDA={oanda_pnl}, DB={db_unrealized}")

            results["checks_performed"].append("pnl_consistency")

        except Exception as e:
            logger.error(f"Error checking P&L consistency: {e}")

    async def _check_position_consistency(self, results: Dict[str, Any]):
        """Verify individual position details match"""
        try:
            # Get OANDA trades
            oanda_response = await self.oanda_client.get_open_trades()
            oanda_trades = {str(t["id"]): t for t in oanda_response.get("trades", [])}

            # Get database trades
            db_trades = await self.db.get_active_trades()

            for db_trade in db_trades:
                trade_id = db_trade["trade_id"]

                if trade_id in oanda_trades:
                    oanda_trade = oanda_trades[trade_id]

                    # Check key fields
                    discrepancies = []

                    # Check units
                    oanda_units = abs(int(float(oanda_trade.get("currentUnits", 0))))
                    if db_trade["units"] != oanda_units:
                        discrepancies.append({
                            "field": "units",
                            "db_value": db_trade["units"],
                            "oanda_value": oanda_units
                        })

                    # Check stop loss
                    oanda_sl = float(oanda_trade.get("stopLossOrder", {}).get("price", 0)) if oanda_trade.get("stopLossOrder") else None
                    if db_trade.get("stop_loss") != oanda_sl:
                        discrepancies.append({
                            "field": "stop_loss",
                            "db_value": db_trade.get("stop_loss"),
                            "oanda_value": oanda_sl
                        })

                    # Check take profit
                    oanda_tp = float(oanda_trade.get("takeProfitOrder", {}).get("price", 0)) if oanda_trade.get("takeProfitOrder") else None
                    if db_trade.get("take_profit") != oanda_tp:
                        discrepancies.append({
                            "field": "take_profit",
                            "db_value": db_trade.get("take_profit"),
                            "oanda_value": oanda_tp
                        })

                    if discrepancies:
                        issue = ReconciliationIssue(
                            "position_discrepancy",
                            trade_id,
                            {"discrepancies": discrepancies}
                        )
                        self.issues.append(issue)

                else:
                    # Trade exists in DB but not in OANDA
                    issue = ReconciliationIssue(
                        "missing_in_oanda",
                        trade_id,
                        {"db_trade": db_trade}
                    )
                    self.issues.append(issue)

            # Check for trades in OANDA but not in DB
            db_trade_ids = {t["trade_id"] for t in db_trades}
            for oanda_id in oanda_trades:
                if oanda_id not in db_trade_ids:
                    issue = ReconciliationIssue(
                        "missing_in_db",
                        oanda_id,
                        {"oanda_trade": oanda_trades[oanda_id]}
                    )
                    self.issues.append(issue)

            results["checks_performed"].append("position_consistency")

        except Exception as e:
            logger.error(f"Error checking position consistency: {e}")

    async def _check_orphaned_trades(self, results: Dict[str, Any]):
        """Check for orphaned or stuck trades"""
        try:
            # Find trades marked as PENDING for too long
            pending_trades = await self.db.get_active_trades()
            current_time = datetime.now()

            for trade in pending_trades:
                if trade["status"] == TradeStatus.PENDING:
                    created_at = datetime.fromisoformat(trade.get("created_at", current_time.isoformat()))
                    age = current_time - created_at

                    if age > timedelta(minutes=5):
                        issue = ReconciliationIssue(
                            "stuck_pending_trade",
                            trade["trade_id"],
                            {"age_minutes": age.total_seconds() / 60}
                        )
                        self.issues.append(issue)

            results["checks_performed"].append("orphaned_trades")

        except Exception as e:
            logger.error(f"Error checking orphaned trades: {e}")

    async def _check_data_integrity(self, results: Dict[str, Any]):
        """Check for data integrity issues"""
        try:
            # Check for trades with missing required fields
            all_trades = await self.db.get_active_trades()

            for trade in all_trades:
                missing_fields = []
                required_fields = ["trade_id", "account_id", "instrument", "direction", "units", "status"]

                for field in required_fields:
                    if not trade.get(field):
                        missing_fields.append(field)

                if missing_fields:
                    issue = ReconciliationIssue(
                        "missing_required_fields",
                        trade["trade_id"],
                        {"missing_fields": missing_fields}
                    )
                    self.issues.append(issue)

                # Check for invalid values
                if trade["status"] == TradeStatus.OPEN:
                    if trade.get("units", 0) <= 0:
                        issue = ReconciliationIssue(
                            "invalid_units",
                            trade["trade_id"],
                            {"units": trade.get("units")}
                        )
                        self.issues.append(issue)

            results["checks_performed"].append("data_integrity")

        except Exception as e:
            logger.error(f"Error checking data integrity: {e}")

    async def _fix_issues(self) -> int:
        """Attempt to fix detected issues"""
        fixed_count = 0

        for issue in self.issues:
            try:
                if issue.issue_type == "missing_in_db":
                    # Add missing trade to database
                    from .sync_service import TradeSyncService
                    sync_service = TradeSyncService(self.oanda_client)
                    await sync_service.initialize()

                    oanda_trade = issue.details["oanda_trade"]
                    trade_data = sync_service._convert_oanda_to_db_format(oanda_trade)
                    trade_data["status"] = TradeStatus.OPEN

                    if await self.db.upsert_trade(trade_data):
                        issue.resolved = True
                        issue.resolution = "Added to database"
                        fixed_count += 1

                elif issue.issue_type == "missing_in_oanda":
                    # Mark trade as closed in database
                    trade_id = issue.trade_id
                    db_trade = issue.details.get("db_trade", {})
                    trade_data = {
                        "trade_id": trade_id,
                        "account_id": db_trade.get("account_id", "unknown"),
                        "instrument": db_trade.get("instrument", ""),
                        "direction": db_trade.get("direction", "buy"),
                        "units": db_trade.get("units", 0),
                        "status": TradeStatus.CLOSED,
                        "close_time": datetime.now().isoformat(),
                        "close_reason": "reconciliation_closed"
                    }

                    if await self.db.upsert_trade(trade_data):
                        issue.resolved = True
                        issue.resolution = "Marked as closed"
                        fixed_count += 1

                elif issue.issue_type == "stuck_pending_trade":
                    # Cancel stuck pending trades
                    trade_id = issue.trade_id
                    trade_data = {
                        "trade_id": trade_id,
                        "status": TradeStatus.CANCELLED,
                        "close_time": datetime.now().isoformat()
                    }

                    if await self.db.upsert_trade(trade_data):
                        issue.resolved = True
                        issue.resolution = "Cancelled stuck trade"
                        fixed_count += 1

                elif issue.issue_type == "position_discrepancy":
                    # Force sync for specific trade
                    from .sync_service import TradeSyncService
                    sync_service = TradeSyncService(self.oanda_client)
                    await sync_service.initialize()
                    await sync_service.force_sync()

                    issue.resolved = True
                    issue.resolution = "Forced sync"
                    fixed_count += 1

            except Exception as e:
                logger.error(f"Error fixing issue {issue.issue_type} for trade {issue.trade_id}: {e}")

        if fixed_count > 0:
            logger.info(f"Fixed {fixed_count} of {len(self.issues)} reconciliation issues")
            self.stats["issues_fixed"] += fixed_count

        return fixed_count

    async def get_reconciliation_status(self) -> Dict[str, Any]:
        """Get current reconciliation status"""
        return {
            "is_running": self.is_running,
            "last_reconciliation": self.last_reconciliation.isoformat() if self.last_reconciliation else None,
            "reconciliation_interval_hours": self.reconciliation_interval.total_seconds() / 3600,
            "auto_fix_enabled": self.auto_fix,
            "current_issues": len(self.issues),
            "stats": self.stats,
            "recent_issues": [
                {
                    "type": issue.issue_type,
                    "trade_id": issue.trade_id,
                    "timestamp": issue.timestamp.isoformat(),
                    "resolved": issue.resolved,
                    "resolution": issue.resolution
                }
                for issue in self.issues[-10:]  # Last 10 issues
            ]
        }

    async def force_reconciliation(self) -> Dict[str, Any]:
        """Force an immediate reconciliation"""
        logger.info("Forcing trade reconciliation")
        return await self.perform_reconciliation()