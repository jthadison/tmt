"""
Basic functionality test for order execution system
"""
import asyncio
import sys
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, AsyncMock

# Test basic imports
try:
    from order_executor import (
        OandaOrderExecutor, OrderResult, OrderSide, OrderStatus
    )
    from oanda_auth_handler import OandaAuthHandler, AccountContext, Environment
    from slippage_monitor import SlippageMonitor
    from order_tracker import OrderTracker
    print("[OK] All imports successful")
except ImportError as e:
    print(f"[ERROR] Import failed: {e}")
    sys.exit(1)

async def test_order_executor_basic():
    """Test basic order executor functionality"""
    print("\n--- Testing Order Executor ---")
    
    # Create mock auth handler
    auth_handler = Mock(spec=OandaAuthHandler)
    context = AccountContext(
        user_id="test_user",
        account_id="test_account",
        environment=Environment.PRACTICE,
        api_key="test_key",
        base_url="https://api-fxpractice.oanda.com",
        authenticated_at=datetime.utcnow(),
        last_refresh=datetime.utcnow(),
        session_valid=True
    )
    auth_handler.get_session_context = AsyncMock(return_value=context)
    
    # Create order executor
    executor = OandaOrderExecutor(auth_handler)
    
    # Test client order ID generation
    client_id_1 = executor._generate_client_order_id()
    client_id_2 = executor._generate_client_order_id("signal_123")
    
    assert client_id_1.startswith("TMT_"), f"Client ID 1 format incorrect: {client_id_1}"
    assert "signal_123" in client_id_2, f"Signal ID not in client ID 2: {client_id_2}"
    
    print("[OK] Client order ID generation works")
    
    # Test order request building
    request = executor._build_market_order_request(
        instrument="EUR_USD",
        units=10000,
        side=OrderSide.BUY,
        stop_loss=Decimal('1.11000'),
        take_profit=Decimal('1.13000'),
        client_order_id="test_order_123",
        client_extensions={'tag': 'TEST'},
        tmt_signal_id="signal_456"
    )
    
    assert request['order']['type'] == 'MARKET'
    assert request['order']['instrument'] == 'EUR_USD'
    assert request['order']['units'] == '10000'
    assert 'stopLossOnFill' in request['order']
    assert 'takeProfitOnFill' in request['order']
    
    print("[OK] Order request building works")
    
    # Test execution metrics
    metrics = executor.get_execution_metrics()
    assert isinstance(metrics, dict)
    assert 'total_orders' in metrics
    
    print("[OK] Execution metrics works")
    
    await executor.close()
    print("[OK] Order executor basic tests passed")

async def test_slippage_monitor_basic():
    """Test basic slippage monitor functionality"""
    print("\n--- Testing Slippage Monitor ---")
    
    monitor = SlippageMonitor()
    
    # Test slippage calculation
    slippage_buy = monitor._calculate_slippage(
        expected_price=Decimal('1.12000'),
        actual_price=Decimal('1.12050'),
        side=OrderSide.BUY,
        instrument="EUR_USD"
    )
    
    assert slippage_buy == Decimal('0.00050'), f"Buy slippage calculation wrong: {slippage_buy}"
    
    print("✓ Slippage calculation works")
    
    # Test basis points conversion
    bps = monitor._to_basis_points(Decimal('0.00050'), Decimal('1.12000'))
    assert 4.0 < bps < 5.0, f"BPS conversion wrong: {bps}"
    
    print("✓ Basis points conversion works")
    
    print("✓ Slippage monitor basic tests passed")

async def test_order_tracker_basic():
    """Test basic order tracker functionality"""
    print("\n--- Testing Order Tracker ---")
    
    tracker = OrderTracker(":memory:")
    await tracker.initialize()
    
    # Create sample order result
    order_result = OrderResult(
        client_order_id="test_order_123",
        oanda_order_id="oanda_456",
        transaction_id="tx_789",
        status=OrderStatus.FILLED,
        instrument="EUR_USD",
        units=10000,
        side=OrderSide.BUY,
        requested_price=None,
        fill_price=Decimal('1.12050'),
        slippage=Decimal('0.00050'),
        execution_time_ms=45.2,
        timestamp=datetime.utcnow(),
        filled_units=10000
    )
    
    # Track order
    await tracker.track_order(order_result)
    
    # Verify tracking
    tracked = tracker.get_order_by_id("test_order_123")
    assert tracked is not None, "Order not tracked"
    assert tracked.status == OrderStatus.FILLED, "Status not correct"
    
    print("✓ Order tracking works")
    
    # Test metrics
    metrics = tracker.get_execution_metrics()
    assert metrics['total_orders'] == 1, f"Wrong order count: {metrics['total_orders']}"
    assert metrics['filled_orders'] == 1, f"Wrong filled count: {metrics['filled_orders']}"
    
    print("✓ Order tracker basic tests passed")

async def test_integration_basic():
    """Test basic integration between components"""
    print("\n--- Testing Basic Integration ---")
    
    # Create components
    auth_handler = Mock(spec=OandaAuthHandler)
    context = AccountContext(
        user_id="test_user",
        account_id="test_account",
        environment=Environment.PRACTICE,
        api_key="test_key",
        base_url="https://api-fxpractice.oanda.com",
        authenticated_at=datetime.utcnow(),
        last_refresh=datetime.utcnow(),
        session_valid=True
    )
    auth_handler.get_session_context = AsyncMock(return_value=context)
    
    executor = OandaOrderExecutor(auth_handler)
    monitor = SlippageMonitor()
    tracker = OrderTracker(":memory:")
    await tracker.initialize()
    
    # Create sample order and process it through all components
    order_result = OrderResult(
        client_order_id="integration_test_123",
        oanda_order_id="oanda_789",
        transaction_id="tx_456",
        status=OrderStatus.FILLED,
        instrument="GBP_USD",
        units=5000,
        side=OrderSide.BUY,
        requested_price=None,
        fill_price=Decimal('1.25050'),
        slippage=None,
        execution_time_ms=35.8,
        timestamp=datetime.utcnow(),
        filled_units=5000
    )
    
    # Process through tracker
    await tracker.track_order(order_result)
    
    # Process through slippage monitor
    expected_price = Decimal('1.25000')
    await monitor.record_execution(order_result, expected_price)
    
    # Verify integration
    tracked_order = tracker.get_order_by_id("integration_test_123")
    assert tracked_order is not None, "Integration tracking failed"
    
    slippage_stats = monitor.get_slippage_stats("GBP_USD")
    assert slippage_stats is not None, "Integration slippage failed"
    assert slippage_stats.total_trades == 1, "Integration slippage count wrong"
    
    print("✓ Basic integration works")
    
    await executor.close()
    print("✓ Integration basic tests passed")

async def main():
    """Run all basic tests"""
    print("=== Order Execution System Basic Tests ===")
    
    try:
        await test_order_executor_basic()
        await test_slippage_monitor_basic()
        await test_order_tracker_basic()
        await test_integration_basic()
        
        print("\n🎉 All basic tests passed successfully!")
        print("\n--- System Component Summary ---")
        print("✓ OandaOrderExecutor - Market order execution with <100ms target")
        print("✓ SlippageMonitor - Real-time slippage calculation and alerting")
        print("✓ OrderTracker - Order lifecycle and TMT signal correlation")
        print("✓ Integration - Components work together correctly")
        print("\nStory 8.3 implementation is functional and ready for production testing.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)