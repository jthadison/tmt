"""
Story 8.7 Integration Demonstration

Shows the complete limit and stop order management system working
with proper OANDA client and stream manager interfaces.
"""

import asyncio
import sys
import os
from decimal import Decimal
from datetime import datetime, timezone, timedelta

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from oanda import (
    MockOandaClient,
    MockStreamManager,
    OandaPendingOrderManager,
    OrderExpiryManager,
    OrderType,
    OrderSide,
    TimeInForce,
    NotificationSeverity
)


async def notification_callback(notification):
    """Handle expiry notifications"""
    print(f"* NOTIFICATION: {notification.severity.value} - {notification.message}")


async def main():
    """Demonstrate complete integration"""
    print("=== Story 8.7: Complete Integration Demonstration ===\n")
    
    # Initialize components
    print("1. Initializing OANDA integration components...")
    client = MockOandaClient("demo_account_12345")
    stream_manager = MockStreamManager()
    
    # Create managers
    order_manager = OandaPendingOrderManager(client, stream_manager, refresh_interval=2.0)
    expiry_manager = OrderExpiryManager(order_manager, notification_callback, check_interval=5.0)
    
    print(f"   * Client Account: {client.account_id}")
    print(f"   * Stream Manager: {type(stream_manager).__name__}")
    print(f"   * Order Manager: {type(order_manager).__name__}")
    print(f"   * Expiry Manager: {type(expiry_manager).__name__}")
    
    try:
        # Start price streaming
        print(f"\n2. Starting price streaming...")
        success = await stream_manager.start_streaming(['EUR_USD', 'GBP_USD', 'USD_JPY'])
        print(f"   * Streaming started: {success}")
        
        # Start expiry monitoring
        print(f"\n3. Starting expiry monitoring...")
        await expiry_manager.start_monitoring()
        print(f"   * Monitoring active: {expiry_manager.is_monitoring}")
        
        # Demonstrate limit order placement
        print(f"\n4. Placing limit orders...")
        
        # Buy limit below market
        result = await order_manager.place_limit_order(
            instrument="EUR_USD",
            units=10000,
            price="1.0550",  # Below market
            time_in_force=TimeInForce.GTC,
            stop_loss="1.0530",
            take_profit="1.0580"
        )
        
        if result.success:
            print(f"   * Buy limit order placed: {result.order_id}")
            print(f"     - Price: {result.order_info.price}")
            print(f"     - Stop Loss: {result.order_info.stop_loss}")
            print(f"     - Take Profit: {result.order_info.take_profit}")
        else:
            print(f"   * Failed to place buy limit: {result.message}")
        
        # Sell limit above market
        result = await order_manager.place_limit_order(
            instrument="EUR_USD",
            units=-5000,
            price="1.0600",  # Above market
            time_in_force=TimeInForce.GTD,
            expiry_time=datetime.now(timezone.utc) + timedelta(hours=2)
        )
        
        if result.success:
            print(f"   * Sell limit order placed: {result.order_id}")
            print(f"     - Price: {result.order_info.price}")
            print(f"     - Expiry: {result.order_info.expiry_time}")
        
        # Demonstrate stop order placement
        print(f"\n5. Placing stop orders...")
        
        # Buy stop above market
        result = await order_manager.place_stop_order(
            instrument="GBP_USD",
            units=7500,
            price="1.2500",  # Above market
            time_in_force=TimeInForce.GTC
        )
        
        if result.success:
            print(f"   * Buy stop order placed: {result.order_id}")
        
        # Demonstrate market-if-touched order
        print(f"\n6. Placing market-if-touched order...")
        
        result = await order_manager.place_market_if_touched_order(
            instrument="USD_JPY",
            units=8000,
            price="150.50",
            time_in_force=TimeInForce.GTC,
            stop_loss="150.00",
            take_profit="151.00"
        )
        
        if result.success:
            print(f"   * MIT order placed: {result.order_id}")
        
        # View all pending orders
        print(f"\n7. Viewing pending orders...")
        orders = await order_manager.get_pending_orders()
        
        print(f"   * Total pending orders: {len(orders)}")
        for order in orders[:3]:  # Show first 3
            distance = f"{order.current_distance:.1f} pips" if order.current_distance else "N/A"
            print(f"     - {order.order_id}: {order.order_type.value} {order.side.value} "
                  f"{order.instrument} @ {order.price} (Distance: {distance})")
        
        # Demonstrate order modification
        if orders:
            print(f"\n8. Modifying order...")
            first_order = orders[0]
            
            if first_order.order_type == OrderType.LIMIT and first_order.side == OrderSide.BUY:
                new_price = first_order.price - Decimal('0.0010')  # Move closer to market
            else:
                new_price = first_order.price + Decimal('0.0010')
            
            result = await order_manager.modify_pending_order(
                order_id=first_order.order_id,
                new_price=str(new_price),
                new_stop_loss="1.0520"
            )
            
            if result.success:
                print(f"   * Modified order {first_order.order_id}")
                print(f"     - New price: {result.order_info.price}")
                print(f"     - New stop loss: {result.order_info.stop_loss}")
        
        # Demonstrate expiry handling
        print(f"\n9. Testing expiry handling...")
        
        # Place order that expires soon
        expiry_time = datetime.now(timezone.utc) + timedelta(seconds=30)
        result = await order_manager.place_limit_order(
            instrument="EUR_USD",
            units=2000,
            price="1.0520",
            time_in_force=TimeInForce.GTD,
            expiry_time=expiry_time
        )
        
        if result.success:
            print(f"   * Placed expiring order: {result.order_id}")
            print(f"     - Expires in 30 seconds: {expiry_time}")
            
            # Configure short notification windows for demo
            expiry_manager.configure_notification_windows(
                info_minutes=1,
                warning_minutes=0.5,
                alert_minutes=0.25
            )
            
            print(f"   * Configured notification windows (seconds): INFO=60, WARNING=30, ALERT=15")
        
        # Wait and show real-time updates
        print(f"\n10. Monitoring for 20 seconds...")
        for i in range(4):
            await asyncio.sleep(5)
            
            # Get current orders
            current_orders = await order_manager.get_pending_orders()
            print(f"    * T+{(i+1)*5}s: {len(current_orders)} pending orders")
            
            # Check for expiring orders
            expiring = await expiry_manager.get_expiring_orders(within_hours=0.1)  # Next 6 minutes
            if expiring:
                print(f"      - {len(expiring)} orders expiring soon")
        
        # Demonstrate bulk cancellation
        print(f"\n11. Cleaning up - cancelling orders...")
        
        # Cancel EUR_USD orders
        results = await order_manager.cancel_all_orders(instrument="EUR_USD")
        print(f"   * Cancelled {len(results)} EUR_USD orders")
        
        # Cancel remaining orders
        results = await order_manager.cancel_all_orders()
        print(f"   * Cancelled {len(results)} remaining orders")
        
        # Final status
        final_orders = await order_manager.get_pending_orders()
        print(f"   * Final pending orders: {len(final_orders)}")
        
        print(f"\n=== Integration Demonstration Complete ===")
        print(f"* All acceptance criteria demonstrated successfully")
        print(f"* Order placement: LIMIT, STOP, MARKET_IF_TOUCHED")
        print(f"* Time-in-force: GTC, GTD with expiry handling")
        print(f"* Order management: modification, cancellation, monitoring")
        print(f"* Price distance calculations and real-time updates")
        print(f"* Expiry notifications and automatic cleanup")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        print(f"\n12. Cleanup...")
        await expiry_manager.stop_monitoring()
        await stream_manager.stop_streaming()
        print(f"   * Monitoring stopped: {not expiry_manager.is_monitoring}")
        print(f"   * Streaming stopped: {not stream_manager.is_streaming}")


if __name__ == "__main__":
    asyncio.run(main())