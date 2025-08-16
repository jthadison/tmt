"""
Order Expiry Management

Handles order expiry monitoring, notifications, and automatic cleanup
for pending orders in the OANDA trading system.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pending_order_manager import OandaPendingOrderManager, OrderInfo
else:
    # Import at runtime to avoid circular imports
    from typing import Any
    OandaPendingOrderManager = Any
    OrderInfo = Any


class NotificationSeverity(Enum):
    """Notification severity levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    ALERT = "ALERT"


@dataclass
class ExpiryNotification:
    """Order expiry notification"""
    order_id: str
    instrument: str
    order_type: str
    expiry_time: datetime
    severity: NotificationSeverity
    message: str
    timestamp: datetime


class OrderExpiryManager:
    """
    Manages order expiry monitoring and notifications.
    
    Features:
    - Real-time expiry monitoring
    - Configurable notification windows
    - Automatic order cleanup
    - Expiry alerts and warnings
    """
    
    def __init__(
        self, 
        order_manager: "OandaPendingOrderManager",
        notification_callback: Optional[Callable[[ExpiryNotification], None]] = None,
        check_interval: float = 60.0
    ):
        self.order_manager = order_manager
        self.notification_callback = notification_callback
        self.check_interval = check_interval
        
        # Notification windows (in minutes before expiry)
        self.notification_windows = {
            NotificationSeverity.INFO: 60,      # 1 hour before
            NotificationSeverity.WARNING: 15,   # 15 minutes before
            NotificationSeverity.ALERT: 5       # 5 minutes before
        }
        
        # Tracking
        self.expiring_orders: Dict[str, datetime] = {}
        self.sent_notifications: Dict[str, List[NotificationSeverity]] = {}
        
        # Monitoring
        self.is_monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Logger
        self.logger = logging.getLogger(__name__)
    
    async def start_monitoring(self):
        """Start expiry monitoring"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self._monitor_task = asyncio.create_task(self._monitor_expiry())
            self.logger.info("Order expiry monitoring started")
    
    async def stop_monitoring(self):
        """Stop expiry monitoring"""
        self.is_monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        self.logger.info("Order expiry monitoring stopped")
    
    async def _monitor_expiry(self):
        """Monitor orders for expiry"""
        try:
            while self.is_monitoring:
                await self._check_order_expiry()
                await asyncio.sleep(self.check_interval)
                
        except Exception as e:
            self.logger.error(f"Error in expiry monitoring: {e}")
        finally:
            self.is_monitoring = False
    
    async def _check_order_expiry(self):
        """Check all orders for expiry conditions"""
        current_time = datetime.now(timezone.utc)
        
        # Get all pending orders
        pending_orders = await self.order_manager.get_pending_orders()
        
        # Update expiring orders tracking
        self._update_expiring_orders(pending_orders)
        
        # Check each expiring order
        for order_id, expiry_time in list(self.expiring_orders.items()):
            try:
                await self._process_order_expiry(order_id, expiry_time, current_time)
            except Exception as e:
                self.logger.error(f"Error processing expiry for order {order_id}: {e}")
    
    def _update_expiring_orders(self, pending_orders: List[OrderInfo]):
        """Update the list of expiring orders"""
        current_expiring = {}
        
        for order in pending_orders:
            if order.expiry_time:
                current_expiring[order.order_id] = order.expiry_time
        
        # Remove orders that are no longer pending
        for order_id in list(self.expiring_orders.keys()):
            if order_id not in current_expiring:
                del self.expiring_orders[order_id]
                if order_id in self.sent_notifications:
                    del self.sent_notifications[order_id]
        
        # Update with current orders
        self.expiring_orders.update(current_expiring)
    
    async def _process_order_expiry(
        self, 
        order_id: str, 
        expiry_time: datetime, 
        current_time: datetime
    ):
        """Process expiry for a specific order"""
        time_to_expiry = expiry_time - current_time
        minutes_to_expiry = time_to_expiry.total_seconds() / 60
        
        # Check if order has already expired
        if minutes_to_expiry <= 0:
            await self._handle_expired_order(order_id, expiry_time)
            return
        
        # Send notifications based on time windows
        for severity, window_minutes in self.notification_windows.items():
            if (minutes_to_expiry <= window_minutes and 
                not self._notification_sent(order_id, severity)):
                
                await self._send_expiry_notification(order_id, severity, minutes_to_expiry)
    
    async def _handle_expired_order(self, order_id: str, expiry_time: datetime):
        """Handle an expired order"""
        try:
            # Get order details
            order = await self.order_manager.get_order_status(order_id)
            if not order:
                # Order not found, remove from tracking
                if order_id in self.expiring_orders:
                    del self.expiring_orders[order_id]
                return
            
            # Cancel the expired order
            result = await self.order_manager.cancel_pending_order(order_id)
            
            if result.success:
                # Send expiry notification
                notification = ExpiryNotification(
                    order_id=order_id,
                    instrument=order.instrument,
                    order_type=order.order_type.value,
                    expiry_time=expiry_time,
                    severity=NotificationSeverity.ALERT,
                    message=f"Order {order_id} expired and was cancelled",
                    timestamp=datetime.now(timezone.utc)
                )
                
                await self._send_notification(notification)
                
                self.logger.info(f"Expired order {order_id} cancelled successfully")
            else:
                self.logger.error(f"Failed to cancel expired order {order_id}: {result.message}")
            
            # Remove from tracking
            if order_id in self.expiring_orders:
                del self.expiring_orders[order_id]
            if order_id in self.sent_notifications:
                del self.sent_notifications[order_id]
                
        except Exception as e:
            self.logger.error(f"Error handling expired order {order_id}: {e}")
    
    async def _send_expiry_notification(
        self, 
        order_id: str, 
        severity: NotificationSeverity, 
        minutes_to_expiry: float
    ):
        """Send expiry notification"""
        try:
            # Get order details
            order = await self.order_manager.get_order_status(order_id)
            if not order:
                return
            
            # Create notification message
            if minutes_to_expiry > 60:
                time_str = f"{minutes_to_expiry / 60:.1f} hours"
            else:
                time_str = f"{minutes_to_expiry:.0f} minutes"
            
            message = f"Order {order_id} ({order.instrument}) expires in {time_str}"
            
            notification = ExpiryNotification(
                order_id=order_id,
                instrument=order.instrument,
                order_type=order.order_type.value,
                expiry_time=order.expiry_time,
                severity=severity,
                message=message,
                timestamp=datetime.now(timezone.utc)
            )
            
            await self._send_notification(notification)
            
            # Mark notification as sent
            if order_id not in self.sent_notifications:
                self.sent_notifications[order_id] = []
            self.sent_notifications[order_id].append(severity)
            
            self.logger.info(f"Sent {severity.value} notification for order {order_id}")
            
        except Exception as e:
            self.logger.error(f"Error sending expiry notification for {order_id}: {e}")
    
    def _notification_sent(self, order_id: str, severity: NotificationSeverity) -> bool:
        """Check if notification has already been sent"""
        return (order_id in self.sent_notifications and 
                severity in self.sent_notifications[order_id])
    
    async def _send_notification(self, notification: ExpiryNotification):
        """Send notification via callback"""
        try:
            if self.notification_callback:
                # If callback is async
                if asyncio.iscoroutinefunction(self.notification_callback):
                    await self.notification_callback(notification)
                else:
                    self.notification_callback(notification)
        except Exception as e:
            self.logger.error(f"Error in notification callback: {e}")
    
    def configure_notification_windows(
        self, 
        info_minutes: int = 60,
        warning_minutes: int = 15,
        alert_minutes: int = 5
    ):
        """
        Configure notification time windows.
        
        Args:
            info_minutes: Minutes before expiry for INFO notifications
            warning_minutes: Minutes before expiry for WARNING notifications
            alert_minutes: Minutes before expiry for ALERT notifications
        """
        self.notification_windows = {
            NotificationSeverity.INFO: info_minutes,
            NotificationSeverity.WARNING: warning_minutes,
            NotificationSeverity.ALERT: alert_minutes
        }
        
        self.logger.info(f"Updated notification windows: INFO={info_minutes}, WARNING={warning_minutes}, ALERT={alert_minutes}")
    
    async def get_expiring_orders(
        self, 
        within_hours: float = 24.0
    ) -> List[Dict[str, Any]]:
        """
        Get orders expiring within specified timeframe.
        
        Args:
            within_hours: Time window in hours
            
        Returns:
            List of order information dictionaries
        """
        current_time = datetime.now(timezone.utc)
        cutoff_time = current_time + timedelta(hours=within_hours)
        
        expiring_orders = []
        
        for order_id, expiry_time in self.expiring_orders.items():
            if expiry_time <= cutoff_time:
                try:
                    order = await self.order_manager.get_order_status(order_id)
                    if order:
                        time_to_expiry = expiry_time - current_time
                        
                        expiring_orders.append({
                            "order_id": order_id,
                            "instrument": order.instrument,
                            "order_type": order.order_type.value,
                            "side": order.side.value,
                            "price": float(order.price),
                            "expiry_time": expiry_time.isoformat(),
                            "hours_to_expiry": time_to_expiry.total_seconds() / 3600,
                            "notifications_sent": self.sent_notifications.get(order_id, [])
                        })
                except Exception as e:
                    self.logger.error(f"Error getting expiring order info for {order_id}: {e}")
        
        # Sort by time to expiry
        expiring_orders.sort(key=lambda x: x["hours_to_expiry"])
        
        return expiring_orders
    
    async def force_expiry_check(self) -> Dict[str, Any]:
        """
        Force an immediate expiry check.
        
        Returns:
            Summary of expiry check results
        """
        try:
            self.logger.info("Forcing expiry check")
            
            initial_count = len(self.expiring_orders)
            
            await self._check_order_expiry()
            
            final_count = len(self.expiring_orders)
            processed_count = initial_count - final_count
            
            return {
                "initial_expiring_orders": initial_count,
                "final_expiring_orders": final_count,
                "orders_processed": processed_count,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error in forced expiry check: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def cleanup_old_notifications(self, hours_old: float = 24.0):
        """
        Clean up notification tracking for old orders.
        
        Args:
            hours_old: Remove notification tracking older than this
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_old)
        
        # This would need order creation time tracking for full implementation
        # For now, just clean up notifications for orders no longer in expiring_orders
        for order_id in list(self.sent_notifications.keys()):
            if order_id not in self.expiring_orders:
                del self.sent_notifications[order_id]
        
        self.logger.info(f"Cleaned up old notification tracking")