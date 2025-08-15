"""
Partial Fill and Order Rejection Handler
Story 8.3 - Task 5: Handle partial fills and rejections

Manages partial order fills, remaining quantity tracking, order rejections,
and retry logic for recoverable failures.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass
import json

try:
    from .order_executor import OrderResult, OrderStatus, OrderSide
    from .oanda_auth_handler import OandaAuthHandler, AccountContext
except ImportError:
    from order_executor import OrderResult, OrderStatus, OrderSide
    from oanda_auth_handler import OandaAuthHandler, AccountContext

logger = logging.getLogger(__name__)

class RejectionReason(Enum):
    INSUFFICIENT_MARGIN = "insufficient_margin"
    MARKET_CLOSED = "market_closed"
    INVALID_INSTRUMENT = "invalid_instrument"
    INVALID_UNITS = "invalid_units"
    PRICE_TOO_FAR = "price_too_far"
    RATE_LIMIT = "rate_limit"
    ACCOUNT_DISABLED = "account_disabled"
    POSITION_SIZE_EXCEEDED = "position_size_exceeded"
    UNKNOWN_ERROR = "unknown_error"

class RetryStrategy(Enum):
    NO_RETRY = "no_retry"
    IMMEDIATE = "immediate"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    MARKET_HOURS_ONLY = "market_hours_only"

@dataclass
class PartialFill:
    """Partial fill tracking data"""
    order_id: str
    instrument: str
    original_units: int
    filled_units: int
    remaining_units: int
    fill_price: Decimal
    fill_timestamp: datetime
    fill_transaction_id: str

@dataclass
class OrderRejection:
    """Order rejection details"""
    order_id: str
    instrument: str
    units: int
    rejection_reason: RejectionReason
    error_code: str
    error_message: str
    rejection_timestamp: datetime
    retry_strategy: RetryStrategy
    retry_count: int = 0
    next_retry_at: Optional[datetime] = None

@dataclass
class RetryAttempt:
    """Retry attempt tracking"""
    original_order_id: str
    retry_order_id: str
    attempt_number: int
    retry_timestamp: datetime
    result: Optional[OrderResult] = None

class PartialFillHandler:
    """Handles partial fills and order rejections with retry logic"""
    
    def __init__(self, auth_handler: OandaAuthHandler, order_executor):
        self.auth_handler = auth_handler
        self.order_executor = order_executor
        
        # Tracking dictionaries
        self.partial_fills: Dict[str, List[PartialFill]] = {}
        self.pending_quantities: Dict[str, int] = {}  # Remaining quantities to fill
        self.rejections: Dict[str, OrderRejection] = {}
        self.retry_queue: List[OrderRejection] = []
        self.retry_attempts: Dict[str, List[RetryAttempt]] = {}
        
        # Retry configuration
        self.max_retry_attempts = 3
        self.retry_delays = {
            RetryStrategy.IMMEDIATE: 0,
            RetryStrategy.EXPONENTIAL_BACKOFF: [1, 5, 15],  # seconds
            RetryStrategy.MARKET_HOURS_ONLY: 300  # 5 minutes during market hours
        }
        
        # Error code mappings to rejection reasons
        self.error_code_mapping = {
            'INSUFFICIENT_AUTHORIZATION': RejectionReason.ACCOUNT_DISABLED,
            'INSUFFICIENT_MARGIN': RejectionReason.INSUFFICIENT_MARGIN,
            'INSTRUMENT_NOT_TRADEABLE': RejectionReason.INVALID_INSTRUMENT,
            'MARKET_HALTED': RejectionReason.MARKET_CLOSED,
            'ORDER_UNITS_TOO_MANY': RejectionReason.POSITION_SIZE_EXCEEDED,
            'PRICE_INVALID': RejectionReason.PRICE_TOO_FAR,
            'RATE_LIMITED': RejectionReason.RATE_LIMIT,
            'UNITS_INVALID': RejectionReason.INVALID_UNITS,
        }
        
        # Start retry processor
        self._retry_task = None
        self._start_retry_processor()
    
    def _start_retry_processor(self):
        """Start background task for processing retries"""
        if self._retry_task is None or self._retry_task.done():
            self._retry_task = asyncio.create_task(self._retry_processor())
    
    async def _retry_processor(self):
        """Background processor for handling order retries"""
        while True:
            try:
                await asyncio.sleep(1)  # Check every second
                await self._process_retry_queue()
            except Exception as e:
                logger.error(f"Error in retry processor: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    
    async def handle_partial_fill(
        self,
        order_result: OrderResult,
        fill_transaction: Dict[str, Any]
    ) -> bool:
        """
        Handle partial order fill
        
        Args:
            order_result: Original order result
            fill_transaction: OANDA fill transaction data
            
        Returns:
            True if partial fill processed successfully
        """
        filled_units = int(fill_transaction.get('units', 0))
        remaining_units = abs(order_result.units) - abs(filled_units)
        
        if remaining_units <= 0:
            logger.debug(f"Order {order_result.client_order_id} fully filled")
            return True  # Not a partial fill
        
        logger.info(
            f"Partial fill for {order_result.client_order_id}: "
            f"{filled_units}/{order_result.units} units filled, {remaining_units} remaining"
        )
        
        # Create partial fill record
        partial_fill = PartialFill(
            order_id=order_result.client_order_id,
            instrument=order_result.instrument,
            original_units=order_result.units,
            filled_units=filled_units,
            remaining_units=remaining_units,
            fill_price=Decimal(str(fill_transaction.get('price', '0'))),
            fill_timestamp=datetime.utcnow(),
            fill_transaction_id=fill_transaction.get('id', '')
        )
        
        # Track partial fill
        if order_result.client_order_id not in self.partial_fills:
            self.partial_fills[order_result.client_order_id] = []
        
        self.partial_fills[order_result.client_order_id].append(partial_fill)
        self.pending_quantities[order_result.client_order_id] = remaining_units
        
        # Update order result
        order_result.status = OrderStatus.PARTIALLY_FILLED
        order_result.filled_units = filled_units
        order_result.remaining_units = remaining_units
        
        logger.debug(f"Tracked partial fill for {order_result.client_order_id}")
        return True
    
    async def handle_order_rejection(
        self,
        order_result: OrderResult,
        error_response: Dict[str, Any]
    ) -> OrderRejection:
        """
        Handle order rejection and determine retry strategy
        
        Args:
            order_result: Rejected order result
            error_response: OANDA error response
            
        Returns:
            OrderRejection object with retry strategy
        """
        error_code = error_response.get('errorCode', 'UNKNOWN')
        error_message = error_response.get('errorMessage', 'Unknown error')
        
        # Map error code to rejection reason
        rejection_reason = self.error_code_mapping.get(
            error_code, RejectionReason.UNKNOWN_ERROR
        )
        
        # Determine retry strategy based on rejection reason
        retry_strategy = self._determine_retry_strategy(rejection_reason, error_code)
        
        logger.warning(
            f"Order {order_result.client_order_id} rejected: {error_code} - {error_message}"
            f" (retry strategy: {retry_strategy.value})"
        )
        
        # Create rejection record
        rejection = OrderRejection(
            order_id=order_result.client_order_id,
            instrument=order_result.instrument,
            units=order_result.units,
            rejection_reason=rejection_reason,
            error_code=error_code,
            error_message=error_message,
            rejection_timestamp=datetime.utcnow(),
            retry_strategy=retry_strategy
        )
        
        # Store rejection
        self.rejections[order_result.client_order_id] = rejection
        
        # Add to retry queue if retryable
        if retry_strategy != RetryStrategy.NO_RETRY:
            self._schedule_retry(rejection)
        
        return rejection
    
    def _determine_retry_strategy(
        self, 
        rejection_reason: RejectionReason,
        error_code: str
    ) -> RetryStrategy:
        """Determine appropriate retry strategy for rejection reason"""
        
        retry_mapping = {
            RejectionReason.INSUFFICIENT_MARGIN: RetryStrategy.NO_RETRY,
            RejectionReason.MARKET_CLOSED: RetryStrategy.MARKET_HOURS_ONLY,
            RejectionReason.INVALID_INSTRUMENT: RetryStrategy.NO_RETRY,
            RejectionReason.INVALID_UNITS: RetryStrategy.NO_RETRY,
            RejectionReason.PRICE_TOO_FAR: RetryStrategy.IMMEDIATE,
            RejectionReason.RATE_LIMIT: RetryStrategy.EXPONENTIAL_BACKOFF,
            RejectionReason.ACCOUNT_DISABLED: RetryStrategy.NO_RETRY,
            RejectionReason.POSITION_SIZE_EXCEEDED: RetryStrategy.NO_RETRY,
            RejectionReason.UNKNOWN_ERROR: RetryStrategy.EXPONENTIAL_BACKOFF,
        }
        
        return retry_mapping.get(rejection_reason, RetryStrategy.NO_RETRY)
    
    def _schedule_retry(self, rejection: OrderRejection):
        """Schedule retry for rejected order"""
        if rejection.retry_strategy == RetryStrategy.NO_RETRY:
            return
        
        # Calculate next retry time
        if rejection.retry_strategy == RetryStrategy.IMMEDIATE:
            rejection.next_retry_at = datetime.utcnow()
        elif rejection.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            if rejection.retry_count < len(self.retry_delays[RetryStrategy.EXPONENTIAL_BACKOFF]):
                delay = self.retry_delays[RetryStrategy.EXPONENTIAL_BACKOFF][rejection.retry_count]
                rejection.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
        elif rejection.retry_strategy == RetryStrategy.MARKET_HOURS_ONLY:
            # Wait until next market hours (simplified - would need market hours logic)
            delay = self.retry_delays[RetryStrategy.MARKET_HOURS_ONLY]
            rejection.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
        
        if rejection.next_retry_at:
            self.retry_queue.append(rejection)
            logger.debug(f"Scheduled retry for {rejection.order_id} at {rejection.next_retry_at}")
    
    async def _process_retry_queue(self):
        """Process pending retries"""
        if not self.retry_queue:
            return
        
        now = datetime.utcnow()
        ready_for_retry = []
        
        # Find orders ready for retry
        for rejection in self.retry_queue[:]:
            if rejection.next_retry_at and rejection.next_retry_at <= now:
                if rejection.retry_count < self.max_retry_attempts:
                    ready_for_retry.append(rejection)
                    self.retry_queue.remove(rejection)
                else:
                    logger.warning(f"Max retries exceeded for order {rejection.order_id}")
                    self.retry_queue.remove(rejection)
        
        # Process ready retries
        for rejection in ready_for_retry:
            await self._attempt_retry(rejection)
    
    async def _attempt_retry(self, rejection: OrderRejection):
        """Attempt to retry a rejected order"""
        rejection.retry_count += 1
        
        logger.info(
            f"Retrying order {rejection.order_id} (attempt {rejection.retry_count})"
        )
        
        try:
            # Extract user_id and account_id from original order ID
            # This assumes the order ID contains these - in practice, you'd track this separately
            user_id, account_id = self._extract_user_account_from_order_id(rejection.order_id)
            
            # Determine order side from units
            side = OrderSide.BUY if rejection.units > 0 else OrderSide.SELL
            
            # Retry the order with same parameters
            retry_result = await self.order_executor.execute_market_order(
                user_id=user_id,
                account_id=account_id,
                instrument=rejection.instrument,
                units=abs(rejection.units),
                side=side,
                tmt_signal_id=f"retry_{rejection.order_id}_{rejection.retry_count}"
            )
            
            # Track retry attempt
            retry_attempt = RetryAttempt(
                original_order_id=rejection.order_id,
                retry_order_id=retry_result.client_order_id,
                attempt_number=rejection.retry_count,
                retry_timestamp=datetime.utcnow(),
                result=retry_result
            )
            
            if rejection.order_id not in self.retry_attempts:
                self.retry_attempts[rejection.order_id] = []
            
            self.retry_attempts[rejection.order_id].append(retry_attempt)
            
            # Check if retry succeeded
            if retry_result.status == OrderStatus.FILLED:
                logger.info(f"Retry successful for order {rejection.order_id}")
            elif retry_result.status == OrderStatus.REJECTED:
                # Handle retry rejection
                logger.warning(f"Retry failed for order {rejection.order_id}")
                if rejection.retry_count < self.max_retry_attempts:
                    self._schedule_retry(rejection)
            
        except Exception as e:
            logger.error(f"Error during retry of order {rejection.order_id}: {e}")
            # Schedule another retry if within limits
            if rejection.retry_count < self.max_retry_attempts:
                self._schedule_retry(rejection)
    
    def _extract_user_account_from_order_id(self, order_id: str) -> Tuple[str, str]:
        """
        Extract user_id and account_id from order ID
        
        This is a placeholder - in practice, you'd maintain a separate mapping
        of order IDs to user/account information
        """
        # Example: TMT_signal123_1634567890_abc12345
        # In practice, this would be stored in a database or mapping
        return "default_user", "default_account"
    
    async def retry_remaining_quantity(
        self,
        order_id: str,
        user_id: str,
        account_id: str,
        strategy: str = "immediate"
    ) -> Optional[OrderResult]:
        """
        Manually retry remaining quantity for partially filled order
        
        Args:
            order_id: Original order ID with partial fill
            user_id: User identifier
            account_id: Account identifier
            strategy: Retry strategy ("immediate", "market_order")
            
        Returns:
            New order result or None if no remaining quantity
        """
        if order_id not in self.pending_quantities:
            logger.warning(f"No pending quantity found for order {order_id}")
            return None
        
        remaining_units = self.pending_quantities[order_id]
        if remaining_units <= 0:
            logger.debug(f"No remaining quantity for order {order_id}")
            return None
        
        # Get original order details
        partial_fills = self.partial_fills.get(order_id, [])
        if not partial_fills:
            logger.warning(f"No partial fill data for order {order_id}")
            return None
        
        latest_fill = partial_fills[-1]
        
        # Determine side from original units
        side = OrderSide.BUY if latest_fill.original_units > 0 else OrderSide.SELL
        
        logger.info(f"Retrying remaining {remaining_units} units for order {order_id}")
        
        try:
            # Execute order for remaining quantity
            retry_result = await self.order_executor.execute_market_order(
                user_id=user_id,
                account_id=account_id,
                instrument=latest_fill.instrument,
                units=remaining_units,
                side=side,
                tmt_signal_id=f"remaining_{order_id}"
            )
            
            # Update pending quantity if successful
            if retry_result.status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED]:
                self.pending_quantities[order_id] = max(0, remaining_units - abs(retry_result.filled_units))
                
                if self.pending_quantities[order_id] == 0:
                    logger.info(f"Completed filling remaining quantity for order {order_id}")
                    del self.pending_quantities[order_id]
            
            return retry_result
            
        except Exception as e:
            logger.error(f"Error retrying remaining quantity for order {order_id}: {e}")
            return None
    
    def get_partial_fills(self, order_id: str) -> List[PartialFill]:
        """Get all partial fills for an order"""
        return self.partial_fills.get(order_id, [])
    
    def get_pending_quantity(self, order_id: str) -> int:
        """Get remaining quantity for partially filled order"""
        return self.pending_quantities.get(order_id, 0)
    
    def get_rejection_details(self, order_id: str) -> Optional[OrderRejection]:
        """Get rejection details for an order"""
        return self.rejections.get(order_id)
    
    def get_retry_attempts(self, order_id: str) -> List[RetryAttempt]:
        """Get retry attempts for an order"""
        return self.retry_attempts.get(order_id, [])
    
    def get_retry_queue_status(self) -> Dict[str, Any]:
        """Get current retry queue status"""
        now = datetime.utcnow()
        
        pending_retries = []
        for rejection in self.retry_queue:
            pending_retries.append({
                'order_id': rejection.order_id,
                'instrument': rejection.instrument,
                'retry_count': rejection.retry_count,
                'next_retry_at': rejection.next_retry_at.isoformat() if rejection.next_retry_at else None,
                'rejection_reason': rejection.rejection_reason.value
            })
        
        return {
            'queue_size': len(self.retry_queue),
            'pending_retries': pending_retries,
            'total_rejections': len(self.rejections),
            'total_partial_fills': len(self.partial_fills)
        }
    
    def clear_completed_orders(self, days_old: int = 7):
        """Clean up tracking data for old completed orders"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Clean up partial fills for completed orders
        completed_orders = []
        for order_id, fills in self.partial_fills.items():
            if order_id not in self.pending_quantities:  # Fully completed
                latest_fill = max(fills, key=lambda f: f.fill_timestamp)
                if latest_fill.fill_timestamp < cutoff_date:
                    completed_orders.append(order_id)
        
        for order_id in completed_orders:
            if order_id in self.partial_fills:
                del self.partial_fills[order_id]
            if order_id in self.retry_attempts:
                del self.retry_attempts[order_id]
        
        logger.info(f"Cleaned up {len(completed_orders)} completed orders older than {days_old} days")
    
    async def close(self):
        """Clean up resources"""
        if self._retry_task:
            self._retry_task.cancel()
            try:
                await self._retry_task
            except asyncio.CancelledError:
                pass