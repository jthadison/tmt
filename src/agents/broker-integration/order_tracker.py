"""
Order Tracking and Correlation System
Story 8.3 - Task 3: Build order tracking and correlation

Manages order lifecycle tracking, TMT signal correlation, and database persistence.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json
import sqlite3
import aiosqlite

try:
    from .order_executor import OrderResult, OrderStatus, OrderSide
except ImportError:
    from order_executor import OrderResult, OrderStatus, OrderSide

logger = logging.getLogger(__name__)

@dataclass 
class TMTSignalCorrelation:
    """Correlation between TMT signal and OANDA order"""
    signal_id: str
    signal_timestamp: datetime
    signal_type: str  # e.g., "wyckoff_break", "volume_spike"
    signal_confidence: float
    instrument: str
    signal_side: OrderSide
    signal_entry_price: Optional[float]
    signal_stop_loss: Optional[float] 
    signal_take_profit: Optional[float]
    correlation_created: datetime

@dataclass
class OrderLifecycleEvent:
    """Order lifecycle tracking event"""
    order_id: str
    event_type: str  # created, filled, partially_filled, rejected, cancelled, modified
    timestamp: datetime
    details: Dict[str, Any]
    execution_time_ms: Optional[float] = None

class OrderTracker:
    """Comprehensive order tracking and correlation system"""
    
    def __init__(self, db_path: str = "order_tracking.db"):
        self.db_path = db_path
        self.active_orders: Dict[str, OrderResult] = {}
        self.signal_correlations: Dict[str, TMTSignalCorrelation] = {}
        self.order_lifecycle: Dict[str, List[OrderLifecycleEvent]] = {}
        
        # Performance metrics
        self.execution_metrics = {
            'total_orders': 0,
            'filled_orders': 0,
            'rejected_orders': 0,
            'average_execution_time': 0.0,
            'sub_100ms_count': 0
        }
    
    async def initialize(self):
        """Initialize database and create tables"""
        await self._create_database_tables()
        logger.info("Order tracker initialized")
    
    async def _create_database_tables(self):
        """Create database tables for order tracking"""
        async with aiosqlite.connect(self.db_path) as db:
            # Orders table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    client_order_id TEXT PRIMARY KEY,
                    oanda_order_id TEXT,
                    transaction_id TEXT,
                    status TEXT NOT NULL,
                    instrument TEXT NOT NULL,
                    units INTEGER NOT NULL,
                    side TEXT NOT NULL,
                    requested_price DECIMAL,
                    fill_price DECIMAL,
                    slippage DECIMAL,
                    execution_time_ms REAL NOT NULL,
                    timestamp DATETIME NOT NULL,
                    stop_loss DECIMAL,
                    take_profit DECIMAL,
                    filled_units INTEGER DEFAULT 0,
                    remaining_units INTEGER DEFAULT 0,
                    rejection_reason TEXT,
                    error_code TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # TMT signal correlations table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS signal_correlations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id TEXT NOT NULL,
                    order_id TEXT NOT NULL,
                    signal_timestamp DATETIME NOT NULL,
                    signal_type TEXT NOT NULL,
                    signal_confidence REAL,
                    instrument TEXT NOT NULL,
                    signal_side TEXT NOT NULL,
                    signal_entry_price DECIMAL,
                    signal_stop_loss DECIMAL,
                    signal_take_profit DECIMAL,
                    correlation_created DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders (client_order_id)
                )
            """)
            
            # Order lifecycle events table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS order_lifecycle (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    details TEXT,
                    execution_time_ms REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders (client_order_id)
                )
            """)
            
            # Create indexes
            await db.execute("CREATE INDEX IF NOT EXISTS idx_orders_timestamp ON orders (timestamp)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_orders_instrument ON orders (instrument)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_signal_correlations_signal_id ON signal_correlations (signal_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_lifecycle_order_id ON order_lifecycle (order_id)")
            
            await db.commit()
    
    async def track_order(self, order: OrderResult, signal_correlation: Optional[TMTSignalCorrelation] = None):
        """
        Track new order with optional TMT signal correlation
        
        Args:
            order: Order execution result
            signal_correlation: Optional TMT signal correlation data
        """
        # Store in memory
        self.active_orders[order.client_order_id] = order
        
        # Initialize lifecycle tracking
        if order.client_order_id not in self.order_lifecycle:
            self.order_lifecycle[order.client_order_id] = []
        
        # Record creation event
        await self._record_lifecycle_event(
            order.client_order_id,
            "created",
            order.timestamp,
            {
                "instrument": order.instrument,
                "units": order.units,
                "side": order.side.value,
                "stop_loss": float(order.stop_loss) if order.stop_loss else None,
                "take_profit": float(order.take_profit) if order.take_profit else None
            },
            order.execution_time_ms
        )
        
        # Record fill/rejection event
        if order.status == OrderStatus.FILLED:
            await self._record_lifecycle_event(
                order.client_order_id,
                "filled",
                order.timestamp,
                {
                    "fill_price": float(order.fill_price) if order.fill_price else None,
                    "filled_units": order.filled_units,
                    "slippage": float(order.slippage) if order.slippage else None
                }
            )
        elif order.status == OrderStatus.REJECTED:
            await self._record_lifecycle_event(
                order.client_order_id,
                "rejected",
                order.timestamp,
                {
                    "rejection_reason": order.rejection_reason,
                    "error_code": order.error_code
                }
            )
        
        # Store signal correlation if provided
        if signal_correlation:
            self.signal_correlations[order.client_order_id] = signal_correlation
            await self._store_signal_correlation(order.client_order_id, signal_correlation)
        
        # Store order in database
        await self._store_order(order)
        
        # Update metrics
        await self._update_execution_metrics(order)
        
        logger.debug(f"Tracking order {order.client_order_id}: {order.status.value}")
    
    async def update_order_status(self, client_order_id: str, new_status: OrderStatus, details: Dict[str, Any]):
        """Update order status and record lifecycle event"""
        if client_order_id not in self.active_orders:
            logger.warning(f"Cannot update unknown order: {client_order_id}")
            return
        
        order = self.active_orders[client_order_id]
        old_status = order.status
        order.status = new_status
        
        # Record lifecycle event
        await self._record_lifecycle_event(
            client_order_id,
            new_status.value,
            datetime.utcnow(),
            {**details, "previous_status": old_status.value}
        )
        
        # Update database
        await self._update_order_status_in_db(client_order_id, new_status, details)
        
        logger.info(f"Updated order {client_order_id} status: {old_status.value} -> {new_status.value}")
    
    async def _record_lifecycle_event(
        self, 
        order_id: str, 
        event_type: str, 
        timestamp: datetime,
        details: Dict[str, Any],
        execution_time_ms: Optional[float] = None
    ):
        """Record order lifecycle event"""
        event = OrderLifecycleEvent(
            order_id=order_id,
            event_type=event_type,
            timestamp=timestamp,
            details=details,
            execution_time_ms=execution_time_ms
        )
        
        if order_id not in self.order_lifecycle:
            self.order_lifecycle[order_id] = []
        
        self.order_lifecycle[order_id].append(event)
        
        # Store in database
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO order_lifecycle 
                (order_id, event_type, timestamp, details, execution_time_ms)
                VALUES (?, ?, ?, ?, ?)
            """, (
                order_id,
                event_type,
                timestamp.isoformat(),
                json.dumps(details),
                execution_time_ms
            ))
            await db.commit()
    
    async def _store_order(self, order: OrderResult):
        """Store order in database"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO orders (
                    client_order_id, oanda_order_id, transaction_id, status,
                    instrument, units, side, requested_price, fill_price, slippage,
                    execution_time_ms, timestamp, stop_loss, take_profit,
                    filled_units, remaining_units, rejection_reason, error_code
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order.client_order_id,
                order.oanda_order_id,
                order.transaction_id,
                order.status.value,
                order.instrument,
                order.units,
                order.side.value,
                float(order.requested_price) if order.requested_price else None,
                float(order.fill_price) if order.fill_price else None,
                float(order.slippage) if order.slippage else None,
                order.execution_time_ms,
                order.timestamp.isoformat(),
                float(order.stop_loss) if order.stop_loss else None,
                float(order.take_profit) if order.take_profit else None,
                order.filled_units,
                order.remaining_units,
                order.rejection_reason,
                order.error_code
            ))
            await db.commit()
    
    async def _store_signal_correlation(self, order_id: str, correlation: TMTSignalCorrelation):
        """Store TMT signal correlation in database"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO signal_correlations (
                    signal_id, order_id, signal_timestamp, signal_type, signal_confidence,
                    instrument, signal_side, signal_entry_price, signal_stop_loss, 
                    signal_take_profit
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                correlation.signal_id,
                order_id,
                correlation.signal_timestamp.isoformat(),
                correlation.signal_type,
                correlation.signal_confidence,
                correlation.instrument,
                correlation.signal_side.value,
                correlation.signal_entry_price,
                correlation.signal_stop_loss,
                correlation.signal_take_profit
            ))
            await db.commit()
    
    async def _update_order_status_in_db(self, order_id: str, status: OrderStatus, details: Dict[str, Any]):
        """Update order status in database"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE orders SET status = ? WHERE client_order_id = ?
            """, (status.value, order_id))
            
            # Update specific fields based on status
            if status == OrderStatus.FILLED and "fill_price" in details:
                await db.execute("""
                    UPDATE orders SET fill_price = ?, filled_units = ? 
                    WHERE client_order_id = ?
                """, (details["fill_price"], details.get("filled_units", 0), order_id))
            
            await db.commit()
    
    async def _update_execution_metrics(self, order: OrderResult):
        """Update execution performance metrics"""
        self.execution_metrics['total_orders'] += 1
        
        if order.status == OrderStatus.FILLED:
            self.execution_metrics['filled_orders'] += 1
        elif order.status == OrderStatus.REJECTED:
            self.execution_metrics['rejected_orders'] += 1
        
        # Update average execution time
        current_avg = self.execution_metrics['average_execution_time']
        total_orders = self.execution_metrics['total_orders']
        new_avg = ((current_avg * (total_orders - 1)) + order.execution_time_ms) / total_orders
        self.execution_metrics['average_execution_time'] = new_avg
        
        # Count sub-100ms executions
        if order.execution_time_ms < 100:
            self.execution_metrics['sub_100ms_count'] += 1
    
    def get_order_by_id(self, client_order_id: str) -> Optional[OrderResult]:
        """Get order by client order ID"""
        return self.active_orders.get(client_order_id)
    
    def get_orders_by_instrument(self, instrument: str) -> List[OrderResult]:
        """Get all orders for an instrument"""
        return [
            order for order in self.active_orders.values()
            if order.instrument == instrument
        ]
    
    def get_orders_by_tmt_signal(self, signal_id: str) -> List[OrderResult]:
        """Get all orders correlated to a TMT signal"""
        matching_orders = []
        for order_id, correlation in self.signal_correlations.items():
            if correlation.signal_id == signal_id:
                order = self.active_orders.get(order_id)
                if order:
                    matching_orders.append(order)
        return matching_orders
    
    def get_signal_correlation(self, order_id: str) -> Optional[TMTSignalCorrelation]:
        """Get TMT signal correlation for order"""
        return self.signal_correlations.get(order_id)
    
    def get_order_lifecycle(self, order_id: str) -> List[OrderLifecycleEvent]:
        """Get complete lifecycle for an order"""
        return self.order_lifecycle.get(order_id, [])
    
    async def get_orders_by_status(self, status: OrderStatus, limit: int = 100) -> List[OrderResult]:
        """Get orders by status from database"""
        orders = []
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT * FROM orders WHERE status = ? 
                ORDER BY timestamp DESC LIMIT ?
            """, (status.value, limit)) as cursor:
                async for row in cursor:
                    order = self._row_to_order_result(row)
                    orders.append(order)
        return orders
    
    async def get_orders_in_timerange(
        self, 
        start_time: datetime, 
        end_time: datetime,
        instrument: Optional[str] = None
    ) -> List[OrderResult]:
        """Get orders within time range"""
        orders = []
        
        query = "SELECT * FROM orders WHERE timestamp BETWEEN ? AND ?"
        params = [start_time.isoformat(), end_time.isoformat()]
        
        if instrument:
            query += " AND instrument = ?"
            params.append(instrument)
        
        query += " ORDER BY timestamp DESC"
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params) as cursor:
                async for row in cursor:
                    order = self._row_to_order_result(row)
                    orders.append(order)
        return orders
    
    def _row_to_order_result(self, row) -> OrderResult:
        """Convert database row to OrderResult"""
        return OrderResult(
            client_order_id=row[0],
            oanda_order_id=row[1],
            transaction_id=row[2],
            status=OrderStatus(row[3]),
            instrument=row[4],
            units=row[5],
            side=OrderSide(row[6]),
            requested_price=Decimal(str(row[7])) if row[7] else None,
            fill_price=Decimal(str(row[8])) if row[8] else None,
            slippage=Decimal(str(row[9])) if row[9] else None,
            execution_time_ms=row[10],
            timestamp=datetime.fromisoformat(row[11]),
            stop_loss=Decimal(str(row[12])) if row[12] else None,
            take_profit=Decimal(str(row[13])) if row[13] else None,
            filled_units=row[14],
            remaining_units=row[15],
            rejection_reason=row[16],
            error_code=row[17]
        )
    
    def get_execution_metrics(self) -> Dict[str, Any]:
        """Get current execution metrics"""
        metrics = self.execution_metrics.copy()
        
        if metrics['total_orders'] > 0:
            metrics['fill_rate'] = (metrics['filled_orders'] / metrics['total_orders']) * 100
            metrics['rejection_rate'] = (metrics['rejected_orders'] / metrics['total_orders']) * 100
            metrics['sub_100ms_rate'] = (metrics['sub_100ms_count'] / metrics['total_orders']) * 100
        else:
            metrics['fill_rate'] = 0.0
            metrics['rejection_rate'] = 0.0
            metrics['sub_100ms_rate'] = 0.0
        
        return metrics
    
    async def get_signal_performance(self, signal_id: str) -> Dict[str, Any]:
        """Get performance analysis for a TMT signal"""
        orders = self.get_orders_by_tmt_signal(signal_id)
        
        if not orders:
            return {}
        
        filled_orders = [o for o in orders if o.status == OrderStatus.FILLED]
        total_pnl = Decimal('0')
        
        # This would require position tracking to calculate actual PnL
        # For now, return basic statistics
        
        return {
            'signal_id': signal_id,
            'total_orders': len(orders),
            'filled_orders': len(filled_orders),
            'rejected_orders': len([o for o in orders if o.status == OrderStatus.REJECTED]),
            'average_execution_time': sum(o.execution_time_ms for o in orders) / len(orders),
            'instruments': list(set(o.instrument for o in orders)),
            'total_units_traded': sum(abs(o.filled_units) for o in filled_orders)
        }
    
    async def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old order data"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Remove from memory (keep recent orders)
        orders_to_remove = []
        for order_id, order in self.active_orders.items():
            if order.timestamp < cutoff_date:
                orders_to_remove.append(order_id)
        
        for order_id in orders_to_remove:
            del self.active_orders[order_id]
            if order_id in self.signal_correlations:
                del self.signal_correlations[order_id]
            if order_id in self.order_lifecycle:
                del self.order_lifecycle[order_id]
        
        # Archive old database records (in production, move to archive table)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                DELETE FROM order_lifecycle WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))
            
            await db.execute("""
                DELETE FROM signal_correlations WHERE correlation_created < ?
            """, (cutoff_date.isoformat(),))
            
            await db.execute("""
                DELETE FROM orders WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))
            
            await db.commit()
        
        logger.info(f"Cleaned up order data older than {days_to_keep} days")