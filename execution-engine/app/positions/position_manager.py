"""
Position Management System

Manages all trading positions with real-time P&L tracking and risk controls.
Provides position lifecycle management from open to close.
"""

import asyncio
import time
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

import structlog

from ..core.models import (
    AccountSummary,
    Order,
    Position,
    PositionCloseRequest,
    PositionSide,
)
from ..integrations.oanda_client import OandaExecutionClient
from ..monitoring.metrics import ExecutionMetrics

logger = structlog.get_logger(__name__)


class PositionManager:
    """
    High-performance position manager with real-time P&L tracking.
    
    Features:
    - Real-time position tracking and P&L calculation
    - Position aggregation across multiple orders
    - Margin calculation and monitoring
    - Position close with partial/full support
    - Multi-account position management
    """
    
    def __init__(
        self,
        oanda_client: OandaExecutionClient,
        metrics_collector: ExecutionMetrics,
        price_update_interval: float = 1.0,  # seconds
    ) -> None:
        self.oanda_client = oanda_client
        self.metrics = metrics_collector
        self.price_update_interval = price_update_interval
        
        # Position storage by account and instrument
        self.positions: Dict[str, Dict[str, Position]] = {}  # account_id -> instrument -> position
        
        # Current market prices for P&L calculation
        self.current_prices: Dict[str, Decimal] = {}  # instrument -> price
        
        # Account summaries cache
        self.account_summaries: Dict[str, AccountSummary] = {}
        
        # Position update tasks
        self._price_update_task: Optional[asyncio.Task] = None
        self._position_sync_task: Optional[asyncio.Task] = None
        
        logger.info("PositionManager initialized", 
                   price_update_interval=price_update_interval)
    
    async def start(self) -> None:
        """Start position monitoring and price updates."""
        if self._price_update_task is None or self._price_update_task.done():
            self._price_update_task = asyncio.create_task(self._update_prices_loop())
        
        if self._position_sync_task is None or self._position_sync_task.done():
            self._position_sync_task = asyncio.create_task(self._sync_positions_loop())
        
        logger.info("Position monitoring started")
    
    async def stop(self) -> None:
        """Stop position monitoring."""
        if self._price_update_task and not self._price_update_task.done():
            self._price_update_task.cancel()
            try:
                await self._price_update_task
            except asyncio.CancelledError:
                pass
        
        if self._position_sync_task and not self._position_sync_task.done():
            self._position_sync_task.cancel()
            try:
                await self._position_sync_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Position monitoring stopped")
    
    async def open_position(self, order: Order, fill_price: Decimal) -> Position:
        """
        Open a new position or add to existing position.
        Called when an order is filled.
        """
        account_id = order.account_id
        instrument = order.instrument
        
        # Initialize account positions if not exists
        if account_id not in self.positions:
            self.positions[account_id] = {}
        
        existing_position = self.positions[account_id].get(instrument)
        
        if existing_position and existing_position.is_open():
            # Add to existing position
            return await self._add_to_position(existing_position, order, fill_price)
        else:
            # Create new position
            return await self._create_new_position(order, fill_price)
    
    async def close_position(self, request: PositionCloseRequest) -> bool:
        """
        Close a position partially or completely.
        
        Target: < 100ms position close latency
        """
        start_time = time.perf_counter()
        
        try:
            position = await self._get_position_for_close(request)
            if not position:
                logger.warning("Position not found for close", request=request)
                return False
            
            if not position.is_open():
                logger.warning("Position already closed", position_id=position.id)
                return False
            
            # Determine units to close
            units_to_close = request.units or position.units
            if abs(units_to_close) > abs(position.units):
                logger.warning("Cannot close more units than available",
                             requested=units_to_close,
                             available=position.units)
                return False
            
            # Execute close order with OANDA
            close_result = await self.oanda_client.close_position(
                account_id=position.account_id,
                instrument=position.instrument,
                units=units_to_close
            )
            
            if close_result.success:
                # Update position
                if abs(units_to_close) == abs(position.units):
                    # Full close
                    position.closed_at = time.time()
                    position.realized_pl = close_result.realized_pl
                    
                    logger.info("Position closed completely",
                               position_id=position.id,
                               realized_pl=position.realized_pl)
                else:
                    # Partial close
                    position.units -= units_to_close
                    position.realized_pl += close_result.realized_pl
                    
                    logger.info("Position partially closed",
                               position_id=position.id,
                               units_closed=units_to_close,
                               remaining_units=position.units,
                               partial_pl=close_result.realized_pl)
                
                # Update metrics
                close_time = (time.perf_counter() - start_time) * 1000
                await self.metrics.record_position_close(
                    position.instrument,
                    close_time,
                    True
                )
                
                return True
            else:
                logger.error("Position close failed",
                           position_id=position.id,
                           error=close_result.error_message)
                return False
                
        except Exception as e:
            logger.error("Position close exception", error=str(e))
            return False
    
    async def get_positions(self, account_id: str) -> List[Position]:
        """Get all positions for an account."""
        if account_id not in self.positions:
            await self._sync_positions_for_account(account_id)
        
        return list(self.positions.get(account_id, {}).values())
    
    async def get_position(self, position_id: UUID) -> Optional[Position]:
        """Get a specific position by ID."""
        for account_positions in self.positions.values():
            for position in account_positions.values():
                if position.id == position_id:
                    return position
        return None
    
    async def get_positions_by_instrument(self, account_id: str, instrument: str) -> Optional[Position]:
        """Get position for a specific instrument."""
        if account_id not in self.positions:
            await self._sync_positions_for_account(account_id)
        
        return self.positions.get(account_id, {}).get(instrument)
    
    async def calculate_unrealized_pl(self, account_id: str) -> Decimal:
        """Calculate total unrealized P&L for an account."""
        total_pl = Decimal("0")
        
        if account_id not in self.positions:
            return total_pl
        
        for position in self.positions[account_id].values():
            if position.is_open():
                current_price = self.current_prices.get(position.instrument)
                if current_price:
                    position.current_price = current_price
                    position.unrealized_pl = position.calculate_unrealized_pl(current_price)
                    total_pl += position.unrealized_pl
        
        return total_pl
    
    async def get_account_summary(self, account_id: str) -> AccountSummary:
        """Get comprehensive account summary."""
        # Update cached summary
        await self._update_account_summary(account_id)
        return self.account_summaries.get(account_id)
    
    async def get_margin_used(self, account_id: str) -> Decimal:
        """Calculate total margin used for an account."""
        total_margin = Decimal("0")
        
        if account_id not in self.positions:
            return total_margin
        
        for position in self.positions[account_id].values():
            if position.is_open() and position.margin_used:
                total_margin += position.margin_used
        
        return total_margin
    
    def get_position_count(self, account_id: str, instrument: Optional[str] = None) -> int:
        """Get count of open positions."""
        if account_id not in self.positions:
            return 0
        
        positions = self.positions[account_id]
        
        if instrument:
            position = positions.get(instrument)
            return 1 if position and position.is_open() else 0
        else:
            return sum(1 for pos in positions.values() if pos.is_open())
    
    def get_performance_metrics(self) -> Dict:
        """Get position manager performance metrics."""
        total_positions = 0
        open_positions = 0
        total_realized_pl = Decimal("0")
        total_unrealized_pl = Decimal("0")
        
        for account_positions in self.positions.values():
            for position in account_positions.values():
                total_positions += 1
                if position.is_open():
                    open_positions += 1
                    if position.unrealized_pl:
                        total_unrealized_pl += position.unrealized_pl
                
                total_realized_pl += position.realized_pl
        
        return {
            "total_positions": total_positions,
            "open_positions": open_positions,
            "total_realized_pl": float(total_realized_pl),
            "total_unrealized_pl": float(total_unrealized_pl),
            "tracked_instruments": len(self.current_prices),
            "accounts_monitored": len(self.positions),
        }
    
    # Private methods
    
    async def _create_new_position(self, order: Order, fill_price: Decimal) -> Position:
        """Create a new position from an order fill."""
        # Determine position side
        if order.is_buy():
            side = PositionSide.LONG if order.units > 0 else PositionSide.SHORT
        else:
            side = PositionSide.SHORT if order.units > 0 else PositionSide.LONG
        
        position = Position(
            account_id=order.account_id,
            instrument=order.instrument,
            units=order.units if order.is_buy() else -order.units,
            side=side,
            average_price=fill_price,
            opening_order_id=order.id,
        )
        
        # Store position
        if order.account_id not in self.positions:
            self.positions[order.account_id] = {}
        
        self.positions[order.account_id][order.instrument] = position
        
        # Calculate margin if available
        await self._update_position_margin(position)
        
        logger.info("New position created",
                   position_id=position.id,
                   instrument=position.instrument,
                   units=position.units,
                   side=position.side,
                   average_price=position.average_price)
        
        return position
    
    async def _add_to_position(self, position: Position, order: Order, fill_price: Decimal) -> Position:
        """Add to an existing position (pyramiding)."""
        old_units = position.units
        old_avg_price = position.average_price
        
        # Calculate new average price
        order_value = abs(order.units) * fill_price
        position_value = abs(position.units) * position.average_price
        total_value = position_value + order_value
        total_units = abs(position.units) + abs(order.units)
        
        new_avg_price = total_value / total_units
        
        # Update position
        if (order.is_buy() and position.is_long()) or (order.is_sell() and position.is_short()):
            # Adding to same side
            position.units += order.units if order.is_buy() else -order.units
            position.average_price = new_avg_price
        else:
            # Reducing or reversing position
            if abs(order.units) <= abs(position.units):
                # Reducing position
                position.units += order.units if order.is_buy() else -order.units
                # Keep same average price for reduction
            else:
                # Reversing position
                remaining_units = abs(order.units) - abs(position.units)
                position.units = remaining_units if order.is_buy() else -remaining_units
                position.side = PositionSide.LONG if order.is_buy() else PositionSide.SHORT
                position.average_price = fill_price
        
        position.last_updated = time.time()
        
        # Update margin
        await self._update_position_margin(position)
        
        logger.info("Position updated",
                   position_id=position.id,
                   old_units=old_units,
                   new_units=position.units,
                   old_avg_price=old_avg_price,
                   new_avg_price=position.average_price)
        
        return position
    
    async def _update_position_margin(self, position: Position) -> None:
        """Update position margin information."""
        try:
            margin_info = await self.oanda_client.get_margin_info(
                account_id=position.account_id,
                instrument=position.instrument,
                units=abs(position.units)
            )
            
            if margin_info:
                position.margin_used = margin_info.margin_used
                position.margin_rate = margin_info.margin_rate
                
        except Exception as e:
            logger.warning("Failed to update position margin",
                          position_id=position.id,
                          error=str(e))
    
    async def _get_position_for_close(self, request: PositionCloseRequest) -> Optional[Position]:
        """Get position for close request."""
        if request.position_id:
            return await self.get_position(request.position_id)
        elif request.instrument:
            # Find position by instrument (assume first account if multiple)
            for account_positions in self.positions.values():
                position = account_positions.get(request.instrument)
                if position and position.is_open():
                    return position
        
        return None
    
    async def _update_prices_loop(self) -> None:
        """Background task to update current prices."""
        logger.info("Price update loop started")
        
        while True:
            try:
                # Get all unique instruments
                instruments = set()
                for account_positions in self.positions.values():
                    instruments.update(account_positions.keys())
                
                if instruments:
                    # Fetch current prices
                    prices = await self.oanda_client.get_current_prices(list(instruments))
                    self.current_prices.update(prices)
                
                await asyncio.sleep(self.price_update_interval)
                
            except asyncio.CancelledError:
                logger.info("Price update loop cancelled")
                break
            except Exception as e:
                logger.error("Price update error", error=str(e))
                await asyncio.sleep(self.price_update_interval)
    
    async def _sync_positions_loop(self) -> None:
        """Background task to synchronize positions with OANDA."""
        logger.info("Position sync loop started")
        
        while True:
            try:
                # Sync all accounts
                for account_id in list(self.positions.keys()):
                    await self._sync_positions_for_account(account_id)
                
                await asyncio.sleep(30)  # Sync every 30 seconds
                
            except asyncio.CancelledError:
                logger.info("Position sync loop cancelled")
                break
            except Exception as e:
                logger.error("Position sync error", error=str(e))
                await asyncio.sleep(30)
    
    async def _sync_positions_for_account(self, account_id: str) -> None:
        """Sync positions for a specific account with OANDA."""
        try:
            oanda_positions = await self.oanda_client.get_positions(account_id)
            
            if account_id not in self.positions:
                self.positions[account_id] = {}
            
            # Update local positions with OANDA data
            for oanda_pos in oanda_positions:
                local_pos = self.positions[account_id].get(oanda_pos.instrument)
                
                if local_pos:
                    # Update existing position
                    local_pos.units = oanda_pos.units
                    local_pos.unrealized_pl = oanda_pos.unrealized_pl
                    local_pos.margin_used = oanda_pos.margin_used
                    local_pos.last_updated = time.time()
                else:
                    # Add missing position
                    self.positions[account_id][oanda_pos.instrument] = oanda_pos
            
            logger.debug("Positions synced", account_id=account_id, 
                        positions=len(self.positions[account_id]))
                        
        except Exception as e:
            logger.error("Position sync failed", account_id=account_id, error=str(e))
    
    async def _update_account_summary(self, account_id: str) -> None:
        """Update account summary cache."""
        try:
            account_info = await self.oanda_client.get_account_summary(account_id)
            
            if account_info:
                # Calculate P&L
                unrealized_pl = await self.calculate_unrealized_pl(account_id)
                margin_used = await self.get_margin_used(account_id)
                
                summary = AccountSummary(
                    account_id=account_id,
                    balance=account_info.balance,
                    unrealized_pl=unrealized_pl,
                    margin_used=margin_used,
                    margin_available=account_info.margin_available,
                    open_positions=self.get_position_count(account_id),
                    pending_orders=account_info.pending_orders or 0,
                )
                
                self.account_summaries[account_id] = summary
                
        except Exception as e:
            logger.error("Account summary update failed", 
                        account_id=account_id, error=str(e))