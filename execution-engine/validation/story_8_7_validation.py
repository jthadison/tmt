"""
Story 8.7 Validation Script

Validates all acceptance criteria for Limit & Stop Order Management.
Tests order placement, modification, cancellation, and expiry handling.
"""

import asyncio
import sys
import traceback
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock

# Add src to path for imports
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from oanda.pending_order_manager import (
    OandaPendingOrderManager,
    OrderType,
    OrderSide,
    TimeInForce,
    OrderStatus
)
from oanda.order_expiry_manager import (
    OrderExpiryManager,
    NotificationSeverity
)


class Story87Validator:
    """Validates Story 8.7 implementation"""
    
    def __init__(self):
        self.results = []
        self.setup_mocks()
    
    def setup_mocks(self):
        """Setup mock dependencies"""
        # Mock OANDA client
        self.mock_client = Mock()
        self.mock_client.account_id = "test_account"
        self.mock_client.get = AsyncMock()
        self.mock_client.post = AsyncMock()
        self.mock_client.put = AsyncMock()
        
        # Mock price stream
        self.mock_stream = Mock()
        
        # Setup price responses
        self.mock_client.get.return_value = {
            "prices": [{
                "closeoutBid": "1.0575",
                "closeoutAsk": "1.0577"
            }]
        }
        
        # Initialize managers
        self.order_manager = OandaPendingOrderManager(
            self.mock_client,
            self.mock_stream,
            refresh_interval=1.0
        )
        
        self.expiry_manager = OrderExpiryManager(
            self.order_manager,
            self.mock_notification_callback
        )
    
    async def mock_notification_callback(self, notification):
        """Mock notification callback"""
        print(f"* Notification: {notification.severity.value} - {notification.message}")
    
    def log_result(self, ac_number: str, test_name: str, success: bool, message: str = ""):
        """Log validation result"""
        status = "PASS" if success else "FAIL"
        result = {
            "acceptance_criteria": ac_number,
            "test_name": test_name,
            "status": status,
            "message": message
        }
        self.results.append(result)
        print(f"[{status}] AC {ac_number}: {test_name}")
        if message:
            print(f"    {message}")
    
    async def validate_ac1_limit_orders(self):
        """AC 1: Place limit orders (buy below/sell above market)"""
        print("\n=== AC 1: Limit Order Placement ===")
        
        try:
            # Mock successful order response
            self.mock_client.post.return_value = {
                "orderCreateTransaction": {
                    "id": "limit_12345",
                    "type": "ORDER_CREATE",
                    "instrument": "EUR_USD",
                    "units": "10000",
                    "price": "1.0550"
                }
            }
            
            # Test buy limit order (below market)
            result = await self.order_manager.place_limit_order(
                instrument="EUR_USD",
                units=10000,
                price="1.0550",  # Below market price of 1.0576
                time_in_force=TimeInForce.GTC
            )
            
            success = (result.success and 
                      result.order_info.order_type == OrderType.LIMIT and
                      result.order_info.side == OrderSide.BUY)
            
            self.log_result("1", "Buy limit order placement", success,
                          f"Order ID: {result.order_id}" if success else result.message)
            
            # Test sell limit order (above market)
            self.mock_client.post.return_value["orderCreateTransaction"]["units"] = "-5000"
            
            result = await self.order_manager.place_limit_order(
                instrument="EUR_USD",
                units=-5000,
                price="1.0600",  # Above market price
                time_in_force=TimeInForce.GTC
            )
            
            success = (result.success and 
                      result.order_info.side == OrderSide.SELL)
            
            self.log_result("1", "Sell limit order placement", success,
                          f"Order ID: {result.order_id}" if success else result.message)
            
            # Test invalid limit order (buy above market)
            result = await self.order_manager.place_limit_order(
                instrument="EUR_USD",
                units=10000,
                price="1.0600",  # Above market (invalid for buy limit)
                time_in_force=TimeInForce.GTC
            )
            
            success = not result.success and "Invalid limit order price" in result.message
            
            self.log_result("1", "Invalid limit order rejection", success,
                          "Correctly rejected invalid price")
            
        except Exception as e:
            self.log_result("1", "Limit order placement", False, f"Exception: {str(e)}")
    
    async def validate_ac2_stop_orders(self):
        """AC 2: Place stop orders (buy above/sell below market)"""
        print("\n=== AC 2: Stop Order Placement ===")
        
        try:
            # Mock successful stop order response
            self.mock_client.post.return_value = {
                "orderCreateTransaction": {
                    "id": "stop_12346",
                    "type": "ORDER_CREATE",
                    "instrument": "EUR_USD",
                    "units": "10000",
                    "price": "1.0600"
                }
            }
            
            # Test buy stop order (above market)
            result = await self.order_manager.place_stop_order(
                instrument="EUR_USD",
                units=10000,
                price="1.0600",  # Above market price of 1.0576
                time_in_force=TimeInForce.GTC
            )
            
            success = (result.success and 
                      result.order_info.order_type == OrderType.STOP and
                      result.order_info.side == OrderSide.BUY)
            
            self.log_result("2", "Buy stop order placement", success,
                          f"Order ID: {result.order_id}" if success else result.message)
            
            # Test sell stop order (below market)
            self.mock_client.post.return_value["orderCreateTransaction"]["units"] = "-5000"
            self.mock_client.post.return_value["orderCreateTransaction"]["price"] = "1.0550"
            
            result = await self.order_manager.place_stop_order(
                instrument="EUR_USD",
                units=-5000,
                price="1.0550",  # Below market price
                time_in_force=TimeInForce.GTC
            )
            
            success = (result.success and 
                      result.order_info.side == OrderSide.SELL)
            
            self.log_result("2", "Sell stop order placement", success,
                          f"Order ID: {result.order_id}" if success else result.message)
            
            # Test invalid stop order (buy below market)
            result = await self.order_manager.place_stop_order(
                instrument="EUR_USD",
                units=10000,
                price="1.0550",  # Below market (invalid for buy stop)
                time_in_force=TimeInForce.GTC
            )
            
            success = not result.success and "Invalid stop order price" in result.message
            
            self.log_result("2", "Invalid stop order rejection", success,
                          "Correctly rejected invalid price")
            
        except Exception as e:
            self.log_result("2", "Stop order placement", False, f"Exception: {str(e)}")
    
    async def validate_ac3_time_in_force(self):
        """AC 3: Good Till Cancelled (GTC) and Good Till Date (GTD) support"""
        print("\n=== AC 3: Time-in-Force Support ===")
        
        try:
            # Test GTC order
            self.mock_client.post.return_value = {
                "orderCreateTransaction": {
                    "id": "gtc_12347",
                    "type": "ORDER_CREATE"
                }
            }
            
            result = await self.order_manager.place_limit_order(
                instrument="EUR_USD",
                units=10000,
                price="1.0550",
                time_in_force=TimeInForce.GTC
            )
            
            success = (result.success and 
                      result.order_info.time_in_force == TimeInForce.GTC)
            
            self.log_result("3", "GTC order placement", success,
                          "GTC order created successfully")
            
            # Test GTD order
            expiry_time = datetime.now(timezone.utc) + timedelta(hours=24)
            
            result = await self.order_manager.place_limit_order(
                instrument="EUR_USD",
                units=10000,
                price="1.0550",
                time_in_force=TimeInForce.GTD,
                expiry_time=expiry_time
            )
            
            success = (result.success and 
                      result.order_info.time_in_force == TimeInForce.GTD and
                      result.order_info.expiry_time == expiry_time)
            
            self.log_result("3", "GTD order placement", success,
                          f"GTD order expires at {expiry_time}")
            
        except Exception as e:
            self.log_result("3", "Time-in-force support", False, f"Exception: {str(e)}")
    
    async def validate_ac4_pending_order_viewer(self):
        """AC 4: View all pending orders with distance from current price"""
        print("\n=== AC 4: Pending Order Viewer ===")
        
        try:
            # Setup mock orders response
            self.mock_client.get.return_value = {
                "orders": [
                    {"id": "order1", "state": "PENDING"},
                    {"id": "order2", "state": "PENDING"}
                ]
            }
            
            # Add some orders to manager for testing
            from oanda.pending_order_manager import OrderInfo
            
            order1 = OrderInfo(
                order_id="order1",
                instrument="EUR_USD",
                order_type=OrderType.LIMIT,
                side=OrderSide.BUY,
                units=Decimal('10000'),
                price=Decimal('1.0550'),
                time_in_force=TimeInForce.GTC,
                status=OrderStatus.PENDING
            )
            
            order2 = OrderInfo(
                order_id="order2",
                instrument="GBP_USD",
                order_type=OrderType.STOP,
                side=OrderSide.SELL,
                units=Decimal('5000'),
                price=Decimal('1.2480'),
                time_in_force=TimeInForce.GTC,
                status=OrderStatus.PENDING
            )
            
            self.order_manager.pending_orders["order1"] = order1
            self.order_manager.pending_orders["order2"] = order2
            
            # Get pending orders
            orders = await self.order_manager.get_pending_orders()
            
            success = (len(orders) == 2 and 
                      all(order.current_distance is not None for order in orders))
            
            self.log_result("4", "Pending orders retrieval", success,
                          f"Retrieved {len(orders)} orders with distance calculations")
            
            # Test filtering by instrument
            eur_orders = await self.order_manager.get_pending_orders(instrument="EUR_USD")
            
            success = (len(eur_orders) == 1 and 
                      eur_orders[0].instrument == "EUR_USD")
            
            self.log_result("4", "Pending orders filtering", success,
                          f"Filtered to {len(eur_orders)} EUR_USD orders")
            
        except Exception as e:
            self.log_result("4", "Pending order viewer", False, f"Exception: {str(e)}")
    
    async def validate_ac5_order_modification(self):
        """AC 5: Modify pending order price, stop loss, take profit"""
        print("\n=== AC 5: Order Modification ===")
        
        try:
            # Setup existing order
            from oanda.pending_order_manager import OrderInfo
            
            order = OrderInfo(
                order_id="modify_test",
                instrument="EUR_USD",
                order_type=OrderType.LIMIT,
                side=OrderSide.BUY,
                units=Decimal('10000'),
                price=Decimal('1.0550'),
                time_in_force=TimeInForce.GTC,
                status=OrderStatus.PENDING,
                stop_loss=Decimal('1.0530'),
                take_profit=Decimal('1.0570')
            )
            
            self.order_manager.pending_orders["modify_test"] = order
            
            # Mock modification response
            self.mock_client.put.return_value = {
                "orderCreateTransaction": {
                    "id": "modify_test",
                    "type": "ORDER_CREATE"
                }
            }
            
            # Test price modification
            result = await self.order_manager.modify_pending_order(
                order_id="modify_test",
                new_price="1.0540"
            )
            
            success = (result.success and 
                      result.order_info.price == Decimal('1.0540'))
            
            self.log_result("5", "Order price modification", success,
                          f"Price updated to {result.order_info.price}")
            
            # Test stop loss modification
            result = await self.order_manager.modify_pending_order(
                order_id="modify_test",
                new_stop_loss="1.0520"
            )
            
            success = (result.success and 
                      result.order_info.stop_loss == Decimal('1.0520'))
            
            self.log_result("5", "Stop loss modification", success,
                          f"Stop loss updated to {result.order_info.stop_loss}")
            
            # Test take profit modification
            result = await self.order_manager.modify_pending_order(
                order_id="modify_test",
                new_take_profit="1.0580"
            )
            
            success = (result.success and 
                      result.order_info.take_profit == Decimal('1.0580'))
            
            self.log_result("5", "Take profit modification", success,
                          f"Take profit updated to {result.order_info.take_profit}")
            
        except Exception as e:
            self.log_result("5", "Order modification", False, f"Exception: {str(e)}")
    
    async def validate_ac6_order_cancellation(self):
        """AC 6: Cancel individual or all pending orders"""
        print("\n=== AC 6: Order Cancellation ===")
        
        try:
            # Setup test orders
            from oanda.pending_order_manager import OrderInfo
            
            order1 = OrderInfo(
                order_id="cancel1",
                instrument="EUR_USD",
                order_type=OrderType.LIMIT,
                side=OrderSide.BUY,
                units=Decimal('10000'),
                price=Decimal('1.0550'),
                time_in_force=TimeInForce.GTC,
                status=OrderStatus.PENDING
            )
            
            order2 = OrderInfo(
                order_id="cancel2",
                instrument="GBP_USD",
                order_type=OrderType.STOP,
                side=OrderSide.SELL,
                units=Decimal('5000'),
                price=Decimal('1.2480'),
                time_in_force=TimeInForce.GTC,
                status=OrderStatus.PENDING
            )
            
            self.order_manager.pending_orders["cancel1"] = order1
            self.order_manager.pending_orders["cancel2"] = order2
            
            # Mock cancellation response
            self.mock_client.put.return_value = {
                "orderCancelTransaction": {
                    "id": "cancel_tx",
                    "type": "ORDER_CANCEL"
                }
            }
            
            # Test single order cancellation
            result = await self.order_manager.cancel_pending_order("cancel1")
            
            success = (result.success and 
                      "cancel1" not in self.order_manager.pending_orders)
            
            self.log_result("6", "Individual order cancellation", success,
                          "Order cancelled and removed from tracking")
            
            # Test cancel all orders
            results = await self.order_manager.cancel_all_orders()
            
            success = (len(results) == 1 and  # Only cancel2 remaining
                      all(result.success for result in results.values()) and
                      len(self.order_manager.pending_orders) == 0)
            
            self.log_result("6", "Cancel all orders", success,
                          f"Cancelled {len(results)} remaining orders")
            
        except Exception as e:
            self.log_result("6", "Order cancellation", False, f"Exception: {str(e)}")
    
    async def validate_ac7_expiry_handling(self):
        """AC 7: Order expiry handling and notifications"""
        print("\n=== AC 7: Order Expiry Handling ===")
        
        try:
            # Setup expiring order
            from oanda.pending_order_manager import OrderInfo
            
            expiring_order = OrderInfo(
                order_id="expiring_test",
                instrument="EUR_USD",
                order_type=OrderType.LIMIT,
                side=OrderSide.BUY,
                units=Decimal('10000'),
                price=Decimal('1.0550'),
                time_in_force=TimeInForce.GTD,
                status=OrderStatus.PENDING,
                expiry_time=datetime.now(timezone.utc) + timedelta(minutes=30)
            )
            
            self.order_manager.pending_orders["expiring_test"] = expiring_order
            
            # Setup expiry manager
            self.expiry_manager.expiring_orders["expiring_test"] = expiring_order.expiry_time
            
            # Test notification configuration
            self.expiry_manager.configure_notification_windows(
                info_minutes=60,
                warning_minutes=15,
                alert_minutes=5
            )
            
            success = (self.expiry_manager.notification_windows[NotificationSeverity.INFO] == 60 and
                      self.expiry_manager.notification_windows[NotificationSeverity.WARNING] == 15 and
                      self.expiry_manager.notification_windows[NotificationSeverity.ALERT] == 5)
            
            self.log_result("7", "Notification window configuration", success,
                          "Notification windows configured correctly")
            
            # Test getting expiring orders
            expiring_orders = await self.expiry_manager.get_expiring_orders(within_hours=1.0)
            
            success = (len(expiring_orders) == 1 and 
                      expiring_orders[0]["order_id"] == "expiring_test")
            
            self.log_result("7", "Expiring orders retrieval", success,
                          f"Found {len(expiring_orders)} expiring orders")
            
            # Test expired order handling
            expired_order = OrderInfo(
                order_id="expired_test",
                instrument="EUR_USD",
                order_type=OrderType.LIMIT,
                side=OrderSide.BUY,
                units=Decimal('10000'),
                price=Decimal('1.0550'),
                time_in_force=TimeInForce.GTD,
                status=OrderStatus.PENDING,
                expiry_time=datetime.now(timezone.utc) - timedelta(minutes=5)
            )
            
            self.order_manager.pending_orders["expired_test"] = expired_order
            self.expiry_manager.expiring_orders["expired_test"] = expired_order.expiry_time
            
            # Mock cancellation for expired order
            self.mock_client.put.return_value = {
                "orderCancelTransaction": {
                    "id": "cancel_expired",
                    "type": "ORDER_CANCEL"
                }
            }
            
            # Handle expired order
            await self.expiry_manager._handle_expired_order(
                "expired_test",
                expired_order.expiry_time
            )
            
            success = "expired_test" not in self.expiry_manager.expiring_orders
            
            self.log_result("7", "Expired order cleanup", success,
                          "Expired order removed from tracking")
            
        except Exception as e:
            self.log_result("7", "Expiry handling", False, f"Exception: {str(e)}")
    
    async def validate_ac8_market_if_touched(self):
        """AC 8: Market-if-touched order type support"""
        print("\n=== AC 8: Market-If-Touched Orders ===")
        
        try:
            # Mock MIT order response
            self.mock_client.post.return_value = {
                "orderCreateTransaction": {
                    "id": "mit_12348",
                    "type": "ORDER_CREATE",
                    "instrument": "EUR_USD",
                    "units": "10000",
                    "price": "1.0580"
                }
            }
            
            # Test MIT order placement
            result = await self.order_manager.place_market_if_touched_order(
                instrument="EUR_USD",
                units=10000,
                price="1.0580",
                time_in_force=TimeInForce.GTC
            )
            
            success = (result.success and 
                      result.order_info.order_type == OrderType.MARKET_IF_TOUCHED)
            
            self.log_result("8", "Market-if-touched order placement", success,
                          f"MIT order created: {result.order_id}")
            
            # Test MIT order with stop loss and take profit
            result = await self.order_manager.place_market_if_touched_order(
                instrument="EUR_USD",
                units=10000,
                price="1.0580",
                stop_loss="1.0560",
                take_profit="1.0600"
            )
            
            success = (result.success and 
                      result.order_info.stop_loss == Decimal('1.0560') and
                      result.order_info.take_profit == Decimal('1.0600'))
            
            self.log_result("8", "MIT order with SL/TP", success,
                          "MIT order with stop loss and take profit")
            
        except Exception as e:
            self.log_result("8", "Market-if-touched orders", False, f"Exception: {str(e)}")
    
    async def run_validation(self):
        """Run all validation tests"""
        print("=== Story 8.7: Limit & Stop Order Management Validation ===")
        print("Testing all acceptance criteria...\n")
        
        try:
            await self.validate_ac1_limit_orders()
            await self.validate_ac2_stop_orders()
            await self.validate_ac3_time_in_force()
            await self.validate_ac4_pending_order_viewer()
            await self.validate_ac5_order_modification()
            await self.validate_ac6_order_cancellation()
            await self.validate_ac7_expiry_handling()
            await self.validate_ac8_market_if_touched()
            
        except Exception as e:
            print(f"Critical error during validation: {e}")
            traceback.print_exc()
    
    def print_summary(self):
        """Print validation summary"""
        print("\n" + "="*60)
        print("VALIDATION SUMMARY")
        print("="*60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["status"] == "PASS")
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\nFAILED TESTS:")
            for result in self.results:
                if result["status"] == "FAIL":
                    print(f"  - AC {result['acceptance_criteria']}: {result['test_name']}")
                    if result["message"]:
                        print(f"    {result['message']}")
        
        print("\nAC COVERAGE:")
        acs_tested = set(r["acceptance_criteria"] for r in self.results)
        for ac in sorted(acs_tested):
            ac_results = [r for r in self.results if r["acceptance_criteria"] == ac]
            ac_passed = sum(1 for r in ac_results if r["status"] == "PASS")
            ac_total = len(ac_results)
            status = "PASS" if ac_passed == ac_total else "FAIL"
            print(f"  AC {ac}: {status} ({ac_passed}/{ac_total})")


async def main():
    """Main validation function"""
    validator = Story87Validator()
    await validator.run_validation()
    validator.print_summary()


if __name__ == "__main__":
    asyncio.run(main())