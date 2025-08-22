"""
Order Management System

High-performance order manager with sub-100ms execution targets.
Handles all order lifecycle operations including placement, modification, and cancellation.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Set
from uuid import UUID

import structlog
from cachetools import TTLCache

from ..core.models import (
    ExecutionResult,
    Order,
    OrderRequest,
    OrderResult,
    OrderStatus,
    OrderType,
)
from ..integrations.oanda_client import OandaExecutionClient
from ..monitoring.metrics import ExecutionMetrics
from ..risk.risk_manager import RiskManager

logger = structlog.get_logger(__name__)


class OrderManager:
    """
    High-performance order manager for sub-100ms execution.
    
    Features:
    - Async order processing with connection pooling
    - Order validation and risk checks
    - Real-time order state management
    - Performance monitoring and metrics
    - Error handling with retry logic
    """
    
    def __init__(
        self,
        oanda_client: OandaExecutionClient,
        risk_manager: RiskManager,
        metrics_collector: ExecutionMetrics,
        max_concurrent_orders: int = 50,
        order_cache_ttl: int = 300,  # 5 minutes
    ) -> None:
        self.oanda_client = oanda_client
        self.risk_manager = risk_manager
        self.metrics = metrics_collector
        
        # Order storage and caching
        self.active_orders: Dict[UUID, Order] = {}
        self.completed_orders: TTLCache = TTLCache(maxsize=10000, ttl=order_cache_ttl)
        
        # Async execution setup
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_orders)
        self.order_queue = asyncio.Queue(maxsize=max_concurrent_orders * 2)
        self.processing_orders: Set[UUID] = set()
        
        # Performance tracking
        self.execution_times: List[float] = []
        self.success_count = 0
        self.error_count = 0
        
        # Start order processing task
        self._processing_task: Optional[asyncio.Task] = None
        
        logger.info("OrderManager initialized", 
                   max_concurrent=max_concurrent_orders,
                   cache_ttl=order_cache_ttl)
    
    async def start(self) -> None:
        """Start the order processing system."""
        if self._processing_task is None or self._processing_task.done():
            self._processing_task = asyncio.create_task(self._process_order_queue())
            logger.info("Order processing started")
    
    async def stop(self) -> None:
        """Stop the order processing system."""
        if self._processing_task and not self._processing_task.done():
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        
        self.executor.shutdown(wait=True)
        logger.info("Order processing stopped")
    
    async def submit_order(self, order_request: OrderRequest) -> OrderResult:
        """
        Submit a new order for execution.
        
        Target: < 100ms for market orders (95th percentile)
        """
        start_time = time.perf_counter()
        
        try:
            # Convert request to order
            order = order_request.to_order()
            
            # Pre-execution validation
            validation_result = await self._validate_order(order)
            if not validation_result.is_valid:
                return OrderResult(
                    order_id=order.id,
                    client_order_id=order.client_order_id,
                    result=ExecutionResult.REJECTED,
                    status=OrderStatus.REJECTED,
                    error_code="VALIDATION_FAILED",
                    error_message=validation_result.error_message,
                )
            
            # Add to active orders
            self.active_orders[order.id] = order
            
            # Queue for processing
            await self.order_queue.put(order)
            
            # For market orders, wait for immediate execution
            if order.is_market_order():
                result = await self._execute_market_order(order)
            else:
                # For other orders, return pending status
                result = OrderResult(
                    order_id=order.id,
                    client_order_id=order.client_order_id,
                    result=ExecutionResult.SUCCESS,
                    status=OrderStatus.SUBMITTED,
                )
            
            # Record execution time
            execution_time = (time.perf_counter() - start_time) * 1000  # Convert to ms
            self.execution_times.append(execution_time)
            
            # Update metrics
            await self.metrics.record_order_execution(
                order.instrument,
                execution_time,
                result.result == ExecutionResult.SUCCESS
            )
            
            return result
            
        except Exception as e:
            self.error_count += 1
            logger.error("Order submission failed", 
                        order_id=order.id if 'order' in locals() else None,
                        error=str(e))
            
            return OrderResult(
                order_id=order.id if 'order' in locals() else UUID(),
                result=ExecutionResult.FAILED,
                status=OrderStatus.REJECTED,
                error_code="EXECUTION_ERROR",
                error_message=str(e),
            )
    
    async def modify_order(self, order_id: UUID, modifications: Dict) -> bool:
        """
        Modify an existing order.
        
        Target: < 50ms modification latency
        """
        start_time = time.perf_counter()
        
        try:
            order = self.active_orders.get(order_id)
            if not order:
                logger.warning("Order not found for modification", order_id=order_id)
                return False
            
            if order.status not in {OrderStatus.PENDING, OrderStatus.SUBMITTED}:
                logger.warning("Cannot modify order in current status", 
                             order_id=order_id, status=order.status)
                return False
            
            # Apply modifications
            for key, value in modifications.items():
                if hasattr(order, key):
                    setattr(order, key, value)
            
            # Submit modification to OANDA
            success = await self.oanda_client.modify_order(order)
            
            if success:
                logger.info("Order modified successfully", order_id=order_id)
            else:
                logger.error("Order modification failed", order_id=order_id)
            
            # Record modification time
            modification_time = (time.perf_counter() - start_time) * 1000
            await self.metrics.record_order_modification(
                order.instrument,
                modification_time,
                success
            )
            
            return success
            
        except Exception as e:
            logger.error("Order modification error", order_id=order_id, error=str(e))
            return False
    
    async def cancel_order(self, order_id: UUID) -> bool:
        """
        Cancel a pending order.
        
        Target: < 50ms cancellation latency
        """
        start_time = time.perf_counter()
        
        try:
            order = self.active_orders.get(order_id)
            if not order:
                logger.warning("Order not found for cancellation", order_id=order_id)
                return False
            
            if order.status not in {OrderStatus.PENDING, OrderStatus.SUBMITTED}:
                logger.warning("Cannot cancel order in current status", 
                             order_id=order_id, status=order.status)
                return False
            
            # Submit cancellation to OANDA
            success = await self.oanda_client.cancel_order(order)
            
            if success:
                order.status = OrderStatus.CANCELLED
                order.cancelled_at = time.time()
                self._move_to_completed(order)
                logger.info("Order cancelled successfully", order_id=order_id)
            else:
                logger.error("Order cancellation failed", order_id=order_id)
            
            # Record cancellation time
            cancellation_time = (time.perf_counter() - start_time) * 1000
            await self.metrics.record_order_cancellation(
                order.instrument,
                cancellation_time,
                success
            )
            
            return success
            
        except Exception as e:
            logger.error("Order cancellation error", order_id=order_id, error=str(e))
            return False
    
    async def get_order_status(self, order_id: UUID) -> Optional[Order]:
        """Get current order status."""
        # Check active orders first
        if order_id in self.active_orders:
            return self.active_orders[order_id]
        
        # Check completed orders cache
        if order_id in self.completed_orders:
            return self.completed_orders[order_id]
        
        # Query from OANDA if not found locally
        try:
            order = await self.oanda_client.get_order_details(order_id)
            if order:
                # Update local cache
                if order.is_active():
                    self.active_orders[order_id] = order
                else:
                    self.completed_orders[order_id] = order
            return order
        except Exception as e:
            logger.error("Failed to fetch order status", order_id=order_id, error=str(e))
            return None
    
    async def get_active_orders(self, account_id: Optional[str] = None) -> List[Order]:
        """Get all active orders, optionally filtered by account."""
        orders = list(self.active_orders.values())
        
        if account_id:
            orders = [o for o in orders if o.account_id == account_id]
        
        return orders
    
    async def get_order_history(
        self, 
        account_id: Optional[str] = None,
        instrument: Optional[str] = None,
        limit: int = 100
    ) -> List[Order]:
        """Get order history with optional filtering."""
        try:
            return await self.oanda_client.get_order_history(
                account_id=account_id,
                instrument=instrument,
                limit=limit
            )
        except Exception as e:
            logger.error("Failed to fetch order history", error=str(e))
            return []
    
    def get_performance_metrics(self) -> Dict:
        """Get order manager performance metrics."""
        if not self.execution_times:
            return {
                "total_orders": 0,
                "success_rate": 0.0,
                "avg_execution_time_ms": 0.0,
                "p95_execution_time_ms": 0.0,
                "active_orders": len(self.active_orders),
            }
        
        sorted_times = sorted(self.execution_times)
        total_orders = len(sorted_times)
        p95_index = int(0.95 * total_orders)
        
        return {
            "total_orders": total_orders,
            "success_rate": self.success_count / (self.success_count + self.error_count) if (self.success_count + self.error_count) > 0 else 0.0,
            "avg_execution_time_ms": sum(sorted_times) / total_orders,
            "p95_execution_time_ms": sorted_times[p95_index] if p95_index < total_orders else sorted_times[-1],
            "active_orders": len(self.active_orders),
            "queue_size": self.order_queue.qsize(),
            "processing_orders": len(self.processing_orders),
        }
    
    # Private methods
    
    async def _process_order_queue(self) -> None:
        """Background task to process queued orders."""
        logger.info("Order queue processing started")
        
        while True:
            try:
                # Get order from queue (blocks if empty)
                order = await self.order_queue.get()
                
                # Skip if already processing
                if order.id in self.processing_orders:
                    continue
                
                self.processing_orders.add(order.id)
                
                # Process order asynchronously
                asyncio.create_task(self._process_single_order(order))
                
            except asyncio.CancelledError:
                logger.info("Order queue processing cancelled")
                break
            except Exception as e:
                logger.error("Order queue processing error", error=str(e))
    
    async def _process_single_order(self, order: Order) -> None:
        """Process a single order."""
        try:
            if order.is_market_order():
                await self._execute_market_order(order)
            else:
                await self._submit_pending_order(order)
                
        finally:
            self.processing_orders.discard(order.id)
    
    async def _execute_market_order(self, order: Order) -> OrderResult:
        """Execute a market order immediately."""
        try:
            order.status = OrderStatus.SUBMITTED
            order.submitted_at = time.time()
            
            # Execute with OANDA
            execution_result = await self.oanda_client.execute_market_order(order)
            
            if execution_result.success:
                order.status = OrderStatus.FILLED
                order.filled_at = time.time()
                order.fill_price = execution_result.fill_price
                order.execution_time_ms = execution_result.execution_time_ms
                order.slippage = execution_result.slippage
                order.commission = execution_result.commission
                order.oanda_order_id = execution_result.oanda_order_id
                
                self.success_count += 1
                self._move_to_completed(order)
                
                logger.info("Market order executed successfully", 
                           order_id=order.id,
                           fill_price=order.fill_price,
                           execution_time_ms=order.execution_time_ms)
                
                return OrderResult(
                    order_id=order.id,
                    client_order_id=order.client_order_id,
                    oanda_order_id=order.oanda_order_id,
                    result=ExecutionResult.SUCCESS,
                    status=order.status,
                    fill_price=order.fill_price,
                    fill_time=order.filled_at,
                    execution_time_ms=order.execution_time_ms,
                    slippage=order.slippage,
                    commission=order.commission,
                )
            else:
                order.status = OrderStatus.REJECTED
                order.rejection_reason = execution_result.error_message
                self.error_count += 1
                self._move_to_completed(order)
                
                logger.error("Market order execution failed",
                           order_id=order.id,
                           error=execution_result.error_message)
                
                return OrderResult(
                    order_id=order.id,
                    client_order_id=order.client_order_id,
                    result=ExecutionResult.FAILED,
                    status=order.status,
                    error_code=execution_result.error_code,
                    error_message=execution_result.error_message,
                )
                
        except Exception as e:
            order.status = OrderStatus.REJECTED
            order.rejection_reason = str(e)
            self.error_count += 1
            self._move_to_completed(order)
            
            logger.error("Market order execution exception", 
                        order_id=order.id, error=str(e))
            
            return OrderResult(
                order_id=order.id,
                client_order_id=order.client_order_id,
                result=ExecutionResult.FAILED,
                status=order.status,
                error_code="EXECUTION_EXCEPTION",
                error_message=str(e),
            )
    
    async def _submit_pending_order(self, order: Order) -> None:
        """Submit a pending order (limit, stop, etc.)."""
        try:
            result = await self.oanda_client.submit_pending_order(order)
            
            if result.success:
                order.status = OrderStatus.SUBMITTED
                order.submitted_at = time.time()
                order.oanda_order_id = result.oanda_order_id
                
                logger.info("Pending order submitted successfully", 
                           order_id=order.id,
                           oanda_order_id=order.oanda_order_id)
            else:
                order.status = OrderStatus.REJECTED
                order.rejection_reason = result.error_message
                self._move_to_completed(order)
                
                logger.error("Pending order submission failed",
                           order_id=order.id,
                           error=result.error_message)
                
        except Exception as e:
            order.status = OrderStatus.REJECTED
            order.rejection_reason = str(e)
            self._move_to_completed(order)
            
            logger.error("Pending order submission exception", 
                        order_id=order.id, error=str(e))
    
    async def _validate_order(self, order: Order):
        """Validate order before execution."""
        # Use risk manager for validation
        return await self.risk_manager.validate_order(order)
    
    def _move_to_completed(self, order: Order) -> None:
        """Move order from active to completed."""
        if order.id in self.active_orders:
            del self.active_orders[order.id]
        self.completed_orders[order.id] = order