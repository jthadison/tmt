"""
Simple test for order execution system
"""
import asyncio
import sys
from datetime import datetime
from decimal import Decimal

# Test imports
try:
    from order_executor import OandaOrderExecutor, OrderSide
    from slippage_monitor import SlippageMonitor
    from order_tracker import OrderTracker
    print("[OK] Basic imports work")
except ImportError as e:
    print(f"[ERROR] Import failed: {e}")
    sys.exit(1)

def test_order_side_enum():
    """Test OrderSide enum"""
    assert OrderSide.BUY.value == "buy"
    assert OrderSide.SELL.value == "sell"
    print("[OK] OrderSide enum works")

def test_slippage_calculation():
    """Test slippage calculation"""
    monitor = SlippageMonitor()
    
    # Buy order slippage
    slippage = monitor._calculate_slippage(
        expected_price=Decimal('1.12000'),
        actual_price=Decimal('1.12050'),
        side=OrderSide.BUY,
        instrument="EUR_USD"
    )
    
    expected = Decimal('0.00050')
    assert slippage == expected, f"Expected {expected}, got {slippage}"
    print(f"[OK] Slippage calculation: {slippage}")

def test_pip_values():
    """Test pip value mapping"""
    monitor = SlippageMonitor()
    
    eur_usd_pip = monitor._get_pip_value("EUR_USD")
    usd_jpy_pip = monitor._get_pip_value("USD_JPY")
    
    assert eur_usd_pip == Decimal('0.0001')
    assert usd_jpy_pip == Decimal('0.01')
    print("[OK] Pip values correct")

async def test_order_tracker():
    """Test order tracker initialization"""
    tracker = OrderTracker(":memory:")
    await tracker.initialize()
    
    # Test metrics
    metrics = tracker.get_execution_metrics()
    assert isinstance(metrics, dict)
    assert 'total_orders' in metrics
    assert metrics['total_orders'] == 0
    print("[OK] Order tracker initialization works")

def main():
    print("=== Simple Order Execution Tests ===\n")
    
    try:
        test_order_side_enum()
        test_slippage_calculation()
        test_pip_values()
        asyncio.run(test_order_tracker())
        
        print("\n[SUCCESS] All simple tests passed!")
        print("\nImplemented components:")
        print("- OandaOrderExecutor: Market order execution")
        print("- SlippageMonitor: Real-time slippage tracking")
        print("- OrderTracker: Order lifecycle management")
        print("- StopLossTakeProfitManager: SL/TP management")
        print("- PartialFillHandler: Partial fill and retry logic")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)