"""
Comprehensive tests for Order Expiry Manager functionality.

Tests expiry monitoring, notifications, automatic cleanup,
and expiry alert systems.
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.oanda.order_expiry_manager import (
    OrderExpiryManager,
    ExpiryNotification,
    NotificationSeverity
)
from src.oanda.pending_order_manager import (
    OandaPendingOrderManager,
    OrderInfo,
    OrderType,
    OrderSide,
    TimeInForce,
    OrderStatus,
    OrderResult
)


@pytest.fixture
def mock_order_manager():
    """Mock pending order manager"""
    from src.oanda.client import MockOandaClient
    from src.oanda.stream_manager import MockStreamManager
    from src.oanda.pending_order_manager import OandaPendingOrderManager
    
    # Create real manager with mock dependencies for testing
    client = MockOandaClient("test_account")
    stream = MockStreamManager()
    return OandaPendingOrderManager(client, stream)


@pytest.fixture
def mock_notification_callback():
    """Mock notification callback"""
    return AsyncMock()


@pytest.fixture
def expiry_manager(mock_order_manager, mock_notification_callback):
    """Order expiry manager instance for testing"""
    return OrderExpiryManager(
        mock_order_manager,
        mock_notification_callback,
        check_interval=1.0
    )


@pytest.fixture
def sample_expiring_order():
    """Sample order that will expire soon"""
    return OrderInfo(
        order_id="expiring_order",
        instrument="EUR_USD",
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        units=Decimal('10000'),
        price=Decimal('1.0550'),
        time_in_force=TimeInForce.GTD,
        status=OrderStatus.PENDING,
        expiry_time=datetime.now(timezone.utc) + timedelta(minutes=30),
        created_at=datetime.now(timezone.utc) - timedelta(hours=2)
    )


@pytest.fixture
def sample_expired_order():
    """Sample order that has already expired"""
    return OrderInfo(
        order_id="expired_order",
        instrument="GBP_USD",
        order_type=OrderType.STOP,
        side=OrderSide.SELL,
        units=Decimal('5000'),
        price=Decimal('1.2480'),
        time_in_force=TimeInForce.GTD,
        status=OrderStatus.PENDING,
        expiry_time=datetime.now(timezone.utc) - timedelta(minutes=5),
        created_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )


class TestExpiryManagerSetup:
    """Test suite for expiry manager initialization and configuration"""
    
    def test_expiry_manager_initialization(self, expiry_manager):
        """Test expiry manager initialization"""
        assert expiry_manager.is_monitoring is False
        assert expiry_manager._monitor_task is None
        assert len(expiry_manager.expiring_orders) == 0
        assert len(expiry_manager.sent_notifications) == 0
        
    def test_default_notification_windows(self, expiry_manager):
        """Test default notification windows"""
        windows = expiry_manager.notification_windows
        assert windows[NotificationSeverity.INFO] == 60
        assert windows[NotificationSeverity.WARNING] == 15
        assert windows[NotificationSeverity.ALERT] == 5
        
    def test_configure_notification_windows(self, expiry_manager):
        """Test configuring notification windows"""
        expiry_manager.configure_notification_windows(
            info_minutes=120,
            warning_minutes=30,
            alert_minutes=10
        )
        
        windows = expiry_manager.notification_windows
        assert windows[NotificationSeverity.INFO] == 120
        assert windows[NotificationSeverity.WARNING] == 30
        assert windows[NotificationSeverity.ALERT] == 10


class TestExpiryMonitoring:
    """Test suite for expiry monitoring functionality"""
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, expiry_manager):
        """Test starting and stopping expiry monitoring"""
        # Initially not monitoring
        assert expiry_manager.is_monitoring is False
        
        # Start monitoring
        await expiry_manager.start_monitoring()
        assert expiry_manager.is_monitoring is True
        assert expiry_manager._monitor_task is not None
        
        # Stop monitoring
        await expiry_manager.stop_monitoring()
        assert expiry_manager.is_monitoring is False
        assert expiry_manager._monitor_task is None
        
    @pytest.mark.asyncio
    async def test_update_expiring_orders(
        self,
        expiry_manager,
        mock_order_manager,
        sample_expiring_order
    ):
        """Test updating expiring orders tracking"""
        # Setup pending orders
        mock_order_manager.get_pending_orders.return_value = [sample_expiring_order]
        
        # Update expiring orders
        expiry_manager._update_expiring_orders([sample_expiring_order])
        
        # Verify order was added to tracking
        assert sample_expiring_order.order_id in expiry_manager.expiring_orders
        assert expiry_manager.expiring_orders[sample_expiring_order.order_id] == sample_expiring_order.expiry_time
        
    @pytest.mark.asyncio
    async def test_remove_non_pending_orders(
        self,
        expiry_manager,
        sample_expiring_order
    ):
        """Test removing orders that are no longer pending"""
        # Setup initial tracking
        expiry_manager.expiring_orders["old_order"] = datetime.now(timezone.utc)
        expiry_manager.sent_notifications["old_order"] = [NotificationSeverity.INFO]
        
        # Update with new orders (not including old_order)
        expiry_manager._update_expiring_orders([sample_expiring_order])
        
        # Verify old order was removed
        assert "old_order" not in expiry_manager.expiring_orders
        assert "old_order" not in expiry_manager.sent_notifications


class TestExpiryNotifications:
    """Test suite for expiry notification system"""
    
    @pytest.mark.asyncio
    async def test_send_info_notification(
        self,
        expiry_manager,
        mock_order_manager,
        mock_notification_callback,
        sample_expiring_order
    ):
        """Test sending INFO level notification"""
        # Setup order expiring in 90 minutes (within INFO window)
        sample_expiring_order.expiry_time = datetime.now(timezone.utc) + timedelta(minutes=90)
        mock_order_manager.get_order_status.return_value = sample_expiring_order
        
        # Process expiry
        await expiry_manager._process_order_expiry(
            sample_expiring_order.order_id,
            sample_expiring_order.expiry_time,
            datetime.now(timezone.utc)
        )
        
        # Verify notification was sent
        mock_notification_callback.assert_called_once()
        notification = mock_notification_callback.call_args[0][0]
        assert isinstance(notification, ExpiryNotification)
        assert notification.severity == NotificationSeverity.INFO
        assert notification.order_id == sample_expiring_order.order_id
        
    @pytest.mark.asyncio
    async def test_send_warning_notification(
        self,
        expiry_manager,
        mock_order_manager,
        mock_notification_callback,
        sample_expiring_order
    ):
        """Test sending WARNING level notification"""
        # Setup order expiring in 10 minutes (within WARNING window)
        sample_expiring_order.expiry_time = datetime.now(timezone.utc) + timedelta(minutes=10)
        mock_order_manager.get_order_status.return_value = sample_expiring_order
        
        # Process expiry
        await expiry_manager._process_order_expiry(
            sample_expiring_order.order_id,
            sample_expiring_order.expiry_time,
            datetime.now(timezone.utc)
        )
        
        # Verify WARNING notification was sent
        mock_notification_callback.assert_called_once()
        notification = mock_notification_callback.call_args[0][0]
        assert notification.severity == NotificationSeverity.WARNING
        
    @pytest.mark.asyncio
    async def test_send_alert_notification(
        self,
        expiry_manager,
        mock_order_manager,
        mock_notification_callback,
        sample_expiring_order
    ):
        """Test sending ALERT level notification"""
        # Setup order expiring in 3 minutes (within ALERT window)
        sample_expiring_order.expiry_time = datetime.now(timezone.utc) + timedelta(minutes=3)
        mock_order_manager.get_order_status.return_value = sample_expiring_order
        
        # Process expiry
        await expiry_manager._process_order_expiry(
            sample_expiring_order.order_id,
            sample_expiring_order.expiry_time,
            datetime.now(timezone.utc)
        )
        
        # Verify ALERT notification was sent
        mock_notification_callback.assert_called_once()
        notification = mock_notification_callback.call_args[0][0]
        assert notification.severity == NotificationSeverity.ALERT
        
    @pytest.mark.asyncio
    async def test_no_duplicate_notifications(
        self,
        expiry_manager,
        mock_order_manager,
        mock_notification_callback,
        sample_expiring_order
    ):
        """Test that duplicate notifications are not sent"""
        # Setup order expiring in 10 minutes
        sample_expiring_order.expiry_time = datetime.now(timezone.utc) + timedelta(minutes=10)
        mock_order_manager.get_order_status.return_value = sample_expiring_order
        
        # Process expiry twice
        await expiry_manager._process_order_expiry(
            sample_expiring_order.order_id,
            sample_expiring_order.expiry_time,
            datetime.now(timezone.utc)
        )
        
        await expiry_manager._process_order_expiry(
            sample_expiring_order.order_id,
            sample_expiring_order.expiry_time,
            datetime.now(timezone.utc)
        )
        
        # Verify notification was only sent once
        assert mock_notification_callback.call_count == 1
        
    @pytest.mark.asyncio
    async def test_notification_message_formatting(
        self,
        expiry_manager,
        mock_order_manager,
        mock_notification_callback,
        sample_expiring_order
    ):
        """Test notification message formatting"""
        # Setup order expiring in 90 minutes
        sample_expiring_order.expiry_time = datetime.now(timezone.utc) + timedelta(minutes=90)
        mock_order_manager.get_order_status.return_value = sample_expiring_order
        
        # Process expiry
        await expiry_manager._process_order_expiry(
            sample_expiring_order.order_id,
            sample_expiring_order.expiry_time,
            datetime.now(timezone.utc)
        )
        
        # Verify message formatting
        notification = mock_notification_callback.call_args[0][0]
        assert "1.5 hours" in notification.message  # 90 minutes = 1.5 hours
        assert sample_expiring_order.order_id in notification.message
        assert sample_expiring_order.instrument in notification.message


class TestExpiredOrderHandling:
    """Test suite for expired order handling"""
    
    @pytest.mark.asyncio
    async def test_handle_expired_order_success(
        self,
        expiry_manager,
        mock_order_manager,
        mock_notification_callback,
        sample_expired_order
    ):
        """Test successful handling of expired order"""
        # Setup order manager responses
        mock_order_manager.get_order_status.return_value = sample_expired_order
        mock_order_manager.cancel_pending_order.return_value = OrderResult(
            success=True,
            order_id=sample_expired_order.order_id,
            message="Order cancelled"
        )
        
        # Setup tracking
        expiry_manager.expiring_orders[sample_expired_order.order_id] = sample_expired_order.expiry_time
        
        # Handle expired order
        await expiry_manager._handle_expired_order(
            sample_expired_order.order_id,
            sample_expired_order.expiry_time
        )
        
        # Verify order was cancelled
        mock_order_manager.cancel_pending_order.assert_called_once_with(sample_expired_order.order_id)
        
        # Verify expiry notification was sent
        mock_notification_callback.assert_called_once()
        notification = mock_notification_callback.call_args[0][0]
        assert notification.severity == NotificationSeverity.ALERT
        assert "expired and was cancelled" in notification.message
        
        # Verify order removed from tracking
        assert sample_expired_order.order_id not in expiry_manager.expiring_orders
        
    @pytest.mark.asyncio
    async def test_handle_expired_order_not_found(
        self,
        expiry_manager,
        mock_order_manager,
        sample_expired_order
    ):
        """Test handling expired order that's not found"""
        # Setup order not found
        mock_order_manager.get_order_status.return_value = None
        
        # Setup tracking
        expiry_manager.expiring_orders[sample_expired_order.order_id] = sample_expired_order.expiry_time
        
        # Handle expired order
        await expiry_manager._handle_expired_order(
            sample_expired_order.order_id,
            sample_expired_order.expiry_time
        )
        
        # Verify no cancellation attempted
        mock_order_manager.cancel_pending_order.assert_not_called()
        
        # Verify order removed from tracking
        assert sample_expired_order.order_id not in expiry_manager.expiring_orders
        
    @pytest.mark.asyncio
    async def test_handle_expired_order_cancellation_failure(
        self,
        expiry_manager,
        mock_order_manager,
        sample_expired_order
    ):
        """Test handling expired order when cancellation fails"""
        # Setup order manager responses
        mock_order_manager.get_order_status.return_value = sample_expired_order
        mock_order_manager.cancel_pending_order.return_value = OrderResult(
            success=False,
            message="Cancellation failed"
        )
        
        # Setup tracking
        expiry_manager.expiring_orders[sample_expired_order.order_id] = sample_expired_order.expiry_time
        
        # Handle expired order
        await expiry_manager._handle_expired_order(
            sample_expired_order.order_id,
            sample_expired_order.expiry_time
        )
        
        # Verify cancellation was attempted
        mock_order_manager.cancel_pending_order.assert_called_once()
        
        # Verify order still removed from tracking (even on failure)
        assert sample_expired_order.order_id not in expiry_manager.expiring_orders


class TestExpiryQueries:
    """Test suite for expiry query functions"""
    
    @pytest.mark.asyncio
    async def test_get_expiring_orders_within_timeframe(
        self,
        expiry_manager,
        mock_order_manager,
        sample_expiring_order
    ):
        """Test getting orders expiring within timeframe"""
        # Setup expiring order
        expiry_manager.expiring_orders[sample_expiring_order.order_id] = sample_expiring_order.expiry_time
        mock_order_manager.get_order_status.return_value = sample_expiring_order
        
        # Get expiring orders within 24 hours
        expiring_orders = await expiry_manager.get_expiring_orders(within_hours=24.0)
        
        # Verify order included
        assert len(expiring_orders) == 1
        order_info = expiring_orders[0]
        assert order_info["order_id"] == sample_expiring_order.order_id
        assert order_info["instrument"] == sample_expiring_order.instrument
        assert order_info["order_type"] == sample_expiring_order.order_type.value
        assert "hours_to_expiry" in order_info
        assert "expiry_time" in order_info
        
    @pytest.mark.asyncio
    async def test_get_expiring_orders_sorted_by_time(
        self,
        expiry_manager,
        mock_order_manager
    ):
        """Test that expiring orders are sorted by time to expiry"""
        # Setup multiple orders with different expiry times
        order1 = OrderInfo(
            order_id="order1", instrument="EUR_USD", order_type=OrderType.LIMIT,
            side=OrderSide.BUY, units=Decimal('10000'), price=Decimal('1.0550'),
            time_in_force=TimeInForce.GTD, status=OrderStatus.PENDING,
            expiry_time=datetime.now(timezone.utc) + timedelta(hours=2)
        )
        order2 = OrderInfo(
            order_id="order2", instrument="GBP_USD", order_type=OrderType.STOP,
            side=OrderSide.SELL, units=Decimal('5000'), price=Decimal('1.2480'),
            time_in_force=TimeInForce.GTD, status=OrderStatus.PENDING,
            expiry_time=datetime.now(timezone.utc) + timedelta(hours=1)  # Expires sooner
        )
        
        # Setup tracking
        expiry_manager.expiring_orders["order1"] = order1.expiry_time
        expiry_manager.expiring_orders["order2"] = order2.expiry_time
        
        # Mock order status responses
        def mock_get_order_status(order_id):
            if order_id == "order1":
                return order1
            elif order_id == "order2":
                return order2
            return None
        
        mock_order_manager.get_order_status.side_effect = mock_get_order_status
        
        # Get expiring orders
        expiring_orders = await expiry_manager.get_expiring_orders(within_hours=24.0)
        
        # Verify sorted by time (order2 should be first as it expires sooner)
        assert len(expiring_orders) == 2
        assert expiring_orders[0]["order_id"] == "order2"
        assert expiring_orders[1]["order_id"] == "order1"
        assert expiring_orders[0]["hours_to_expiry"] < expiring_orders[1]["hours_to_expiry"]
        
    @pytest.mark.asyncio
    async def test_force_expiry_check(
        self,
        expiry_manager,
        mock_order_manager,
        sample_expired_order
    ):
        """Test forcing an immediate expiry check"""
        # Setup expired order
        expiry_manager.expiring_orders[sample_expired_order.order_id] = sample_expired_order.expiry_time
        mock_order_manager.get_order_status.return_value = sample_expired_order
        mock_order_manager.cancel_pending_order.return_value = OrderResult(
            success=True,
            order_id=sample_expired_order.order_id
        )
        
        # Force expiry check
        result = await expiry_manager.force_expiry_check()
        
        # Verify result
        assert "initial_expiring_orders" in result
        assert "final_expiring_orders" in result
        assert "orders_processed" in result
        assert "timestamp" in result
        assert result["orders_processed"] == 1


class TestNotificationCallbacks:
    """Test suite for notification callback handling"""
    
    @pytest.mark.asyncio
    async def test_async_notification_callback(
        self,
        expiry_manager,
        mock_order_manager,
        sample_expiring_order
    ):
        """Test async notification callback"""
        # Setup async callback
        async_callback = AsyncMock()
        expiry_manager.notification_callback = async_callback
        
        # Setup order expiring within notification window
        sample_expiring_order.expiry_time = datetime.now(timezone.utc) + timedelta(minutes=10)
        mock_order_manager.get_order_status.return_value = sample_expiring_order
        
        # Process expiry
        await expiry_manager._process_order_expiry(
            sample_expiring_order.order_id,
            sample_expiring_order.expiry_time,
            datetime.now(timezone.utc)
        )
        
        # Verify async callback was called
        async_callback.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_sync_notification_callback(
        self,
        expiry_manager,
        mock_order_manager,
        sample_expiring_order
    ):
        """Test sync notification callback"""
        # Setup sync callback
        sync_callback = Mock()
        expiry_manager.notification_callback = sync_callback
        
        # Setup order expiring within notification window
        sample_expiring_order.expiry_time = datetime.now(timezone.utc) + timedelta(minutes=10)
        mock_order_manager.get_order_status.return_value = sample_expiring_order
        
        # Process expiry
        await expiry_manager._process_order_expiry(
            sample_expiring_order.order_id,
            sample_expiring_order.expiry_time,
            datetime.now(timezone.utc)
        )
        
        # Verify sync callback was called
        sync_callback.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_notification_callback_exception_handling(
        self,
        expiry_manager,
        mock_order_manager,
        sample_expiring_order
    ):
        """Test handling of notification callback exceptions"""
        # Setup callback that raises exception
        def failing_callback(notification):
            raise Exception("Callback failed")
        
        expiry_manager.notification_callback = failing_callback
        
        # Setup order expiring within notification window
        sample_expiring_order.expiry_time = datetime.now(timezone.utc) + timedelta(minutes=10)
        mock_order_manager.get_order_status.return_value = sample_expiring_order
        
        # Process expiry should not raise exception
        await expiry_manager._process_order_expiry(
            sample_expiring_order.order_id,
            sample_expiring_order.expiry_time,
            datetime.now(timezone.utc)
        )
        
        # Should continue processing despite callback failure


class TestCleanupOperations:
    """Test suite for cleanup operations"""
    
    @pytest.mark.asyncio
    async def test_cleanup_old_notifications(self, expiry_manager):
        """Test cleaning up old notification tracking"""
        # Setup old notification tracking
        expiry_manager.sent_notifications["old_order"] = [NotificationSeverity.INFO]
        expiry_manager.sent_notifications["current_order"] = [NotificationSeverity.WARNING]
        
        # Keep one order in current tracking
        expiry_manager.expiring_orders["current_order"] = datetime.now(timezone.utc)
        
        # Cleanup old notifications
        await expiry_manager.cleanup_old_notifications()
        
        # Verify old tracking removed
        assert "old_order" not in expiry_manager.sent_notifications
        assert "current_order" in expiry_manager.sent_notifications


class TestErrorHandling:
    """Test suite for error handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_monitoring_exception_handling(
        self,
        expiry_manager,
        mock_order_manager
    ):
        """Test handling of exceptions during monitoring"""
        # Setup order manager to raise exception
        mock_order_manager.get_pending_orders.side_effect = Exception("API error")
        
        # Check expiry should not raise exception
        await expiry_manager._check_order_expiry()
        
        # Should continue despite error
        
    @pytest.mark.asyncio
    async def test_force_expiry_check_exception_handling(
        self,
        expiry_manager,
        mock_order_manager
    ):
        """Test error handling in forced expiry check"""
        # Setup order manager to raise exception
        mock_order_manager.get_pending_orders.side_effect = Exception("API error")
        
        # Force expiry check
        result = await expiry_manager.force_expiry_check()
        
        # Verify error result
        assert "error" in result
        assert "timestamp" in result


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])