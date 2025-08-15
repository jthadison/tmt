"""
Real-Time Account Update System
Story 8.2 - Task 3: Create real-time update system
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Set
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass, asdict
from enum import Enum
import json
import hashlib

from account_manager import OandaAccountManager, AccountSummary
from instrument_service import OandaInstrumentService, InstrumentSpread

logger = logging.getLogger(__name__)

class UpdateType(Enum):
    ACCOUNT_SUMMARY = "account_summary"
    POSITIONS = "positions"
    ORDERS = "orders"
    BALANCE = "balance"
    MARGIN = "margin"
    SPREADS = "spreads"
    TRADE_EXECUTED = "trade_executed"
    ORDER_FILLED = "order_filled"
    POSITION_CLOSED = "position_closed"

@dataclass
class AccountUpdate:
    """Represents an account update event"""
    update_type: UpdateType
    timestamp: datetime
    data: Dict[str, Any]
    changed_fields: List[str]
    account_id: str
    
    def to_json(self) -> str:
        """Convert to JSON for WebSocket transmission"""
        return json.dumps({
            'type': self.update_type.value,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'changed_fields': self.changed_fields,
            'account_id': self.account_id
        }, default=str)

class ChangeDetector:
    """Detects changes in account data"""
    
    def __init__(self):
        self.previous_hashes: Dict[str, str] = {}
        self.previous_data: Dict[str, Any] = {}
    
    def _calculate_hash(self, data: Any) -> str:
        """Calculate hash of data for change detection"""
        json_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(json_str.encode()).hexdigest()
    
    def has_changed(self, key: str, data: Any) -> bool:
        """Check if data has changed since last check"""
        current_hash = self._calculate_hash(data)
        
        if key not in self.previous_hashes:
            self.previous_hashes[key] = current_hash
            self.previous_data[key] = data
            return True
        
        if self.previous_hashes[key] != current_hash:
            self.previous_hashes[key] = current_hash
            self.previous_data[key] = data
            return True
        
        return False
    
    def get_changed_fields(self, key: str, new_data: Dict) -> List[str]:
        """Get list of fields that changed"""
        if key not in self.previous_data:
            return list(new_data.keys())
        
        old_data = self.previous_data.get(key, {})
        changed = []
        
        for field, value in new_data.items():
            if field not in old_data or old_data[field] != value:
                changed.append(field)
        
        return changed

class UpdateBatcher:
    """Batches updates for efficient transmission"""
    
    def __init__(self, batch_size: int = 10, batch_timeout: float = 0.5):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_updates: List[AccountUpdate] = []
        self.last_batch_time = datetime.utcnow()
        self._lock = asyncio.Lock()
    
    async def add_update(self, update: AccountUpdate) -> Optional[List[AccountUpdate]]:
        """
        Add update to batch, returns batch if ready
        
        Args:
            update: Update to add
            
        Returns:
            Batch of updates if ready, None otherwise
        """
        async with self._lock:
            self.pending_updates.append(update)
            
            # Check if batch is ready
            time_since_last = (datetime.utcnow() - self.last_batch_time).total_seconds()
            
            if len(self.pending_updates) >= self.batch_size or time_since_last >= self.batch_timeout:
                batch = self.pending_updates.copy()
                self.pending_updates.clear()
                self.last_batch_time = datetime.utcnow()
                return batch
        
        return None
    
    async def flush(self) -> List[AccountUpdate]:
        """Force flush all pending updates"""
        async with self._lock:
            batch = self.pending_updates.copy()
            self.pending_updates.clear()
            self.last_batch_time = datetime.utcnow()
            return batch

class AccountUpdateService:
    """Real-time account update service"""
    
    def __init__(self, 
                 account_manager: OandaAccountManager,
                 instrument_service: OandaInstrumentService,
                 update_interval: int = 5):
        
        self.account_manager = account_manager
        self.instrument_service = instrument_service
        self.update_interval = update_interval
        
        # Change detection
        self.change_detector = ChangeDetector()
        
        # Update batching
        self.batcher = UpdateBatcher()
        
        # WebSocket clients
        self.websocket_clients: Set[Any] = set()
        
        # Update callbacks
        self.update_callbacks: Dict[UpdateType, List[Callable]] = {
            update_type: [] for update_type in UpdateType
        }
        
        # Watched instruments for spread tracking
        self.watched_instruments: Set[str] = set()
        
        # Background tasks
        self.update_task: Optional[asyncio.Task] = None
        self.spread_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        # Metrics
        self.metrics = {
            'updates_sent': 0,
            'batches_sent': 0,
            'errors': 0,
            'last_update': None,
            'connected_clients': 0
        }
        
        # Last known state for trade execution detection
        self.last_transaction_id: Optional[str] = None
        self.last_position_count: int = 0
        self.last_order_count: int = 0
    
    async def start(self):
        """Start the real-time update service"""
        if self.is_running:
            return
        
        logger.info("Starting real-time update service")
        self.is_running = True
        
        # Start background tasks
        self.update_task = asyncio.create_task(self._account_update_loop())
        self.spread_task = asyncio.create_task(self._spread_update_loop())
        
        logger.info(f"Real-time updates started with {self.update_interval}s interval")
    
    async def stop(self):
        """Stop the real-time update service"""
        if not self.is_running:
            return
        
        logger.info("Stopping real-time update service")
        self.is_running = False
        
        # Cancel background tasks
        if self.update_task:
            self.update_task.cancel()
        if self.spread_task:
            self.spread_task.cancel()
        
        # Flush pending updates
        await self._send_batch(await self.batcher.flush())
        
        logger.info("Real-time update service stopped")
    
    def add_websocket_client(self, client):
        """Add a WebSocket client for updates"""
        self.websocket_clients.add(client)
        self.metrics['connected_clients'] = len(self.websocket_clients)
        logger.debug(f"WebSocket client added. Total: {len(self.websocket_clients)}")
    
    def remove_websocket_client(self, client):
        """Remove a WebSocket client"""
        self.websocket_clients.discard(client)
        self.metrics['connected_clients'] = len(self.websocket_clients)
        logger.debug(f"WebSocket client removed. Total: {len(self.websocket_clients)}")
    
    def subscribe_to_updates(self, update_type: UpdateType, callback: Callable):
        """Subscribe to specific update types"""
        self.update_callbacks[update_type].append(callback)
    
    def watch_instrument(self, instrument: str):
        """Add instrument to spread watch list"""
        self.watched_instruments.add(instrument)
    
    def unwatch_instrument(self, instrument: str):
        """Remove instrument from spread watch list"""
        self.watched_instruments.discard(instrument)
    
    async def _account_update_loop(self):
        """Main loop for account updates"""
        while self.is_running:
            try:
                # Fetch account summary
                summary = await self.account_manager.get_account_summary(use_cache=False)
                
                # Check for changes
                summary_dict = asdict(summary)
                if self.change_detector.has_changed('account_summary', summary_dict):
                    changed_fields = self.change_detector.get_changed_fields('account_summary', summary_dict)
                    
                    # Create update event
                    update = AccountUpdate(
                        update_type=UpdateType.ACCOUNT_SUMMARY,
                        timestamp=datetime.utcnow(),
                        data=summary_dict,
                        changed_fields=changed_fields,
                        account_id=summary.account_id
                    )
                    
                    await self._process_update(update)
                    
                    # Check for specific changes
                    if 'balance' in changed_fields or 'unrealized_pl' in changed_fields:
                        await self._process_update(AccountUpdate(
                            update_type=UpdateType.BALANCE,
                            timestamp=datetime.utcnow(),
                            data={
                                'balance': float(summary.balance),
                                'unrealized_pl': float(summary.unrealized_pl),
                                'equity': float(summary.account_equity)
                            },
                            changed_fields=['balance', 'unrealized_pl', 'equity'],
                            account_id=summary.account_id
                        ))
                    
                    if any(field.startswith('margin') for field in changed_fields):
                        await self._process_update(AccountUpdate(
                            update_type=UpdateType.MARGIN,
                            timestamp=datetime.utcnow(),
                            data=await self.account_manager.get_margin_status(),
                            changed_fields=[f for f in changed_fields if f.startswith('margin')],
                            account_id=summary.account_id
                        ))
                
                # Check for trade execution
                if self.last_transaction_id and summary.last_transaction_id != self.last_transaction_id:
                    await self._check_for_trade_execution(summary)
                
                self.last_transaction_id = summary.last_transaction_id
                
                # Fetch positions
                positions = await self.account_manager.get_open_positions()
                positions_data = [asdict(pos) for pos in positions]
                
                if self.change_detector.has_changed('positions', positions_data):
                    update = AccountUpdate(
                        update_type=UpdateType.POSITIONS,
                        timestamp=datetime.utcnow(),
                        data={'positions': positions_data},
                        changed_fields=['positions'],
                        account_id=summary.account_id
                    )
                    await self._process_update(update)
                    
                    # Check for position changes
                    if len(positions) != self.last_position_count:
                        if len(positions) < self.last_position_count:
                            await self._process_update(AccountUpdate(
                                update_type=UpdateType.POSITION_CLOSED,
                                timestamp=datetime.utcnow(),
                                data={'position_count': len(positions)},
                                changed_fields=['position_count'],
                                account_id=summary.account_id
                            ))
                
                self.last_position_count = len(positions)
                
                # Fetch orders
                orders = await self.account_manager.get_pending_orders()
                orders_data = [asdict(order) for order in orders]
                
                if self.change_detector.has_changed('orders', orders_data):
                    update = AccountUpdate(
                        update_type=UpdateType.ORDERS,
                        timestamp=datetime.utcnow(),
                        data={'orders': orders_data},
                        changed_fields=['orders'],
                        account_id=summary.account_id
                    )
                    await self._process_update(update)
                    
                    # Check for order fills
                    if len(orders) < self.last_order_count:
                        await self._process_update(AccountUpdate(
                            update_type=UpdateType.ORDER_FILLED,
                            timestamp=datetime.utcnow(),
                            data={'order_count': len(orders)},
                            changed_fields=['order_count'],
                            account_id=summary.account_id
                        ))
                
                self.last_order_count = len(orders)
                
                # Update metrics
                self.metrics['last_update'] = datetime.utcnow()
                
                # Wait for next update
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                self.metrics['errors'] += 1
                logger.error(f"Error in account update loop: {e}")
                await asyncio.sleep(1)  # Short delay before retry
    
    async def _spread_update_loop(self):
        """Loop for spread updates"""
        while self.is_running:
            try:
                if self.watched_instruments:
                    # Fetch current spreads
                    spreads = await self.instrument_service.get_current_prices(list(self.watched_instruments))
                    
                    spreads_data = {
                        instrument: {
                            'bid': float(spread.bid),
                            'ask': float(spread.ask),
                            'spread': float(spread.spread),
                            'spread_pips': float(spread.spread_pips),
                            'tradeable': spread.tradeable
                        }
                        for instrument, spread in spreads.items()
                    }
                    
                    if self.change_detector.has_changed('spreads', spreads_data):
                        update = AccountUpdate(
                            update_type=UpdateType.SPREADS,
                            timestamp=datetime.utcnow(),
                            data={'spreads': spreads_data},
                            changed_fields=list(spreads_data.keys()),
                            account_id=self.account_manager.account_id
                        )
                        await self._process_update(update)
                
                # Spread updates can be more frequent
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error in spread update loop: {e}")
                await asyncio.sleep(1)
    
    async def _check_for_trade_execution(self, summary: AccountSummary):
        """Check for trade execution based on transaction ID change"""
        try:
            # Get account changes since last transaction
            changes = await self.account_manager.get_account_changes(self.last_transaction_id)
            
            if changes:
                await self._process_update(AccountUpdate(
                    update_type=UpdateType.TRADE_EXECUTED,
                    timestamp=datetime.utcnow(),
                    data=changes,
                    changed_fields=['transactions'],
                    account_id=summary.account_id
                ))
                
        except Exception as e:
            logger.error(f"Error checking for trade execution: {e}")
    
    async def _process_update(self, update: AccountUpdate):
        """Process and send update"""
        # Call registered callbacks
        for callback in self.update_callbacks.get(update.update_type, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(update)
                else:
                    callback(update)
            except Exception as e:
                logger.error(f"Error in update callback: {e}")
        
        # Add to batch
        batch = await self.batcher.add_update(update)
        if batch:
            await self._send_batch(batch)
    
    async def _send_batch(self, batch: List[AccountUpdate]):
        """Send batch of updates to WebSocket clients"""
        if not batch or not self.websocket_clients:
            return
        
        try:
            # Create batch message
            batch_message = json.dumps({
                'type': 'batch_update',
                'updates': [json.loads(update.to_json()) for update in batch],
                'timestamp': datetime.utcnow().isoformat()
            }, default=str)
            
            # Send to all clients
            disconnected = []
            for client in self.websocket_clients:
                try:
                    await client.send(batch_message)
                except Exception:
                    disconnected.append(client)
            
            # Remove disconnected clients
            for client in disconnected:
                self.remove_websocket_client(client)
            
            self.metrics['updates_sent'] += len(batch)
            self.metrics['batches_sent'] += 1
            
        except Exception as e:
            logger.error(f"Error sending batch: {e}")
    
    async def force_update(self):
        """Force an immediate update"""
        # Clear change detection to force updates
        self.change_detector.previous_hashes.clear()
        self.change_detector.previous_data.clear()
        
        # Trigger immediate updates
        if self.update_task:
            # This will be picked up in next loop iteration
            pass
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics"""
        return self.metrics.copy()