"""
Tests for Order Execution System
Story 8.3 - Market Order Execution Tests

Comprehensive test suite for order execution, slippage monitoring,
order tracking, and partial fill handling.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from decimal import Decimal

import sys
import os

# Add the parent directory to the path so we can import modules
parent_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, parent_dir)

try:
    from order_executor import (
        OandaOrderExecutor, OrderResult, OrderSide, OrderStatus, OrderType
    )
    from oanda_auth_handler import OandaAuthHandler, AccountContext, Environment
    from slippage_monitor import SlippageMonitor, SlippageStats
    from order_tracker import OrderTracker, TMTSignalCorrelation
    from partial_fill_handler import PartialFillHandler, RejectionReason
    from stop_loss_take_profit import (
        StopLossTakeProfitManager, StopLossConfig, TakeProfitConfig, StopType
    )
except ImportError as e:
    # Alternative import approach
    print(f"Import error: {e}")
    print(f"Python path: {sys.path}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Parent directory: {parent_dir}")
    print(f"Files in parent: {os.listdir(parent_dir) if os.path.exists(parent_dir) else 'Directory not found'}")
    raise

class TestOandaOrderExecutor:
    """Test cases for OANDA order executor"""
    
    @pytest.fixture
    async def mock_auth_handler(self):
        """Mock authentication handler"""
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
        return auth_handler
    
    @pytest.fixture
    async def order_executor(self, mock_auth_handler):
        """Create order executor instance"""
        executor = OandaOrderExecutor(mock_auth_handler)
        yield executor
        await executor.close()
    
    @pytest.mark.asyncio
    async def test_successful_market_order(self, order_executor):
        """Test successful market order execution"""
        
        # Mock API response
        mock_response = {
            'orderFillTransaction': {
                'id': '12345',
                'orderID': '67890',
                'price': '1.12345',
                'units': '10000',
                'type': 'ORDER_FILL'
            },
            'orderCreateTransaction': {
                'id': '67890',
                'type': 'MARKET_ORDER'
            }
        }
        
        with patch.object(order_executor, '_send_order_request', 
                         return_value=mock_response):
            
            result = await order_executor.execute_market_order(
                user_id="test_user",
                account_id="test_account",
                instrument="EUR_USD",
                units=10000,
                side=OrderSide.BUY,
                tmt_signal_id="test_signal_123"
            )
            
            assert result.status == OrderStatus.FILLED
            assert result.instrument == "EUR_USD"
            assert result.units == 10000
            assert result.side == OrderSide.BUY
            assert result.fill_price == Decimal('1.12345')
            assert result.transaction_id == '12345'
            assert result.execution_time_ms < 100  # Should be under 100ms target
            assert "test_signal_123" in result.client_order_id
    
    @pytest.mark.asyncio 
    async def test_order_with_stop_loss_take_profit(self, order_executor):
        """Test market order with stop loss and take profit"""
        
        mock_response = {
            'orderFillTransaction': {
                'id': '12345',
                'orderID': '67890',
                'price': '1.12000',
                'units': '5000'
            }
        }
        
        with patch.object(order_executor, '_send_order_request',
                         return_value=mock_response):
            
            result = await order_executor.execute_market_order(
                user_id="test_user",
                account_id="test_account", 
                instrument="EUR_USD",
                units=5000,
                side=OrderSide.BUY,
                stop_loss=Decimal('1.11000'),
                take_profit=Decimal('1.13000')
            )
            
            assert result.status == OrderStatus.FILLED
            assert result.stop_loss == Decimal('1.11000')
            assert result.take_profit == Decimal('1.13000')
    
    @pytest.mark.asyncio
    async def test_order_rejection(self, order_executor):
        """Test order rejection handling"""
        
        with patch.object(order_executor, '_send_order_request',
                         side_effect=Exception("INSUFFICIENT_MARGIN - Not enough margin")):
            
            result = await order_executor.execute_market_order(
                user_id="test_user",
                account_id="test_account",
                instrument="EUR_USD", 
                units=1000000,  # Very large order
                side=OrderSide.BUY
            )
            
            assert result.status == OrderStatus.REJECTED
            assert "INSUFFICIENT_MARGIN" in result.rejection_reason
            assert result.fill_price is None
    
    @pytest.mark.asyncio
    async def test_execution_latency_target(self, order_executor):
        """Test that execution meets latency target"""
        
        mock_response = {
            'orderFillTransaction': {
                'id': '12345',
                'price': '1.12345',
                'units': '1000'
            }
        }
        
        with patch.object(order_executor, '_send_order_request',
                         return_value=mock_response):
            
            result = await order_executor.execute_market_order(
                user_id="test_user",
                account_id="test_account",
                instrument="EUR_USD",
                units=1000,
                side=OrderSide.BUY
            )
            
            # Should execute in under 100ms
            assert result.execution_time_ms < 100
    
    def test_client_order_id_generation(self, order_executor):
        """Test client order ID generation and TMT signal correlation"""
        
        # Without TMT signal ID
        order_id_1 = order_executor._generate_client_order_id()
        assert order_id_1.startswith("TMT_")
        assert len(order_id_1.split('_')) == 3  # TMT_timestamp_uuid
        
        # With TMT signal ID
        order_id_2 = order_executor._generate_client_order_id("signal_456")
        assert "signal_456" in order_id_2
        assert order_id_2.startswith("TMT_signal_456")
    
    def test_build_market_order_request(self, order_executor):
        """Test market order request building"""
        
        request = order_executor._build_market_order_request(
            instrument="GBP_USD",
            units=5000,
            side=OrderSide.SELL,
            stop_loss=Decimal('1.25000'),
            take_profit=Decimal('1.23000'),
            client_order_id="test_order_123",
            client_extensions={'tag': 'TEST'},
            tmt_signal_id="signal_789"
        )
        
        order = request['order']
        assert order['type'] == 'MARKET'
        assert order['instrument'] == 'GBP_USD'
        assert order['units'] == '-5000'  # Negative for sell
        assert order['clientExtensions']['id'] == 'test_order_123'
        assert order['stopLossOnFill']['price'] == '1.25000'
        assert order['takeProfitOnFill']['price'] == '1.23000'

class TestSlippageMonitor:
    """Test cases for slippage monitoring"""
    
    @pytest.fixture
    def slippage_monitor(self):
        """Create slippage monitor instance"""
        return SlippageMonitor()
    
    @pytest.fixture
    def sample_order_result(self):
        """Sample filled order result"""
        return OrderResult(
            client_order_id="test_order_123",
            oanda_order_id="oanda_456",
            transaction_id="tx_789",
            status=OrderStatus.FILLED,
            instrument="EUR_USD",
            units=10000,
            side=OrderSide.BUY,
            requested_price=None,
            fill_price=Decimal('1.12350'),
            slippage=None,
            execution_time_ms=45.5,
            timestamp=datetime.utcnow(),
            filled_units=10000
        )
    
    @pytest.mark.asyncio
    async def test_record_execution_buy_positive_slippage(
        self, slippage_monitor, sample_order_result
    ):
        """Test recording execution with positive slippage (buy order)"""
        
        expected_price = Decimal('1.12300')  # Better than fill price
        
        await slippage_monitor.record_execution(
            sample_order_result, expected_price
        )
        
        stats = slippage_monitor.get_slippage_stats("EUR_USD")
        assert stats is not None
        assert stats.total_trades == 1
        # Positive slippage = paid more than expected (worse execution)
        assert stats.average_slippage_bps > 0
    
    @pytest.mark.asyncio
    async def test_record_execution_sell_negative_slippage(
        self, slippage_monitor
    ):
        """Test recording execution with negative slippage (sell order - better execution)"""
        
        sell_order = OrderResult(
            client_order_id="sell_order_123",
            oanda_order_id="oanda_456",
            transaction_id="tx_789",
            status=OrderStatus.FILLED,
            instrument="GBP_USD",
            units=-5000,
            side=OrderSide.SELL,
            requested_price=None,
            fill_price=Decimal('1.25350'),  # Got better price than expected
            slippage=None,
            execution_time_ms=35.2,
            timestamp=datetime.utcnow(),
            filled_units=-5000
        )
        
        expected_price = Decimal('1.25300')  # Expected worse price
        
        await slippage_monitor.record_execution(sell_order, expected_price)
        
        stats = slippage_monitor.get_slippage_stats("GBP_USD")
        assert stats.total_trades == 1
        # Negative slippage = received more than expected (better execution)
        assert stats.average_slippage_bps < 0
        assert stats.negative_slippage_count == 1
    
    def test_slippage_calculation(self, slippage_monitor):
        """Test slippage calculation logic"""
        
        # Buy order - positive slippage (paid more)
        slippage_buy = slippage_monitor._calculate_slippage(
            expected_price=Decimal('1.12000'),
            actual_price=Decimal('1.12050'),  # Paid 5 pips more
            side=OrderSide.BUY,
            instrument="EUR_USD"
        )
        assert slippage_buy == Decimal('0.00050')
        
        # Sell order - positive slippage (received less)  
        slippage_sell = slippage_monitor._calculate_slippage(
            expected_price=Decimal('1.25000'),
            actual_price=Decimal('1.24950'),  # Received 5 pips less
            side=OrderSide.SELL,
            instrument="EUR_USD"
        )
        assert slippage_sell == Decimal('0.00050')
    
    def test_basis_points_conversion(self, slippage_monitor):
        """Test conversion to basis points"""
        
        # 5 pips on EUR/USD at 1.12000
        slippage = Decimal('0.00050')
        price = Decimal('1.12000')
        
        bps = slippage_monitor._to_basis_points(slippage, price)
        
        # 0.00050 / 1.12000 * 10000 = ~4.46 bps
        assert 4.0 < bps < 5.0
    
    @pytest.mark.asyncio
    async def test_slippage_alerts(self, slippage_monitor):
        """Test slippage alert generation"""
        
        alert_triggered = False
        
        async def alert_callback(alert):
            nonlocal alert_triggered
            alert_triggered = True
            assert alert.slippage_bps >= 10  # INFO threshold
        
        slippage_monitor.add_alert_callback(alert_callback)
        
        # Create order with high slippage
        high_slippage_order = OrderResult(
            client_order_id="high_slippage_order",
            oanda_order_id="oanda_789",
            transaction_id="tx_123",
            status=OrderStatus.FILLED,
            instrument="EUR_USD",
            units=10000,
            side=OrderSide.BUY,
            requested_price=None,
            fill_price=Decimal('1.12200'),  # Much higher than expected
            slippage=None,
            execution_time_ms=75.0,
            timestamp=datetime.utcnow(),
            filled_units=10000
        )
        
        expected_price = Decimal('1.12000')  # 20 pips difference
        
        await slippage_monitor.record_execution(high_slippage_order, expected_price)
        
        # Allow async alert processing
        await asyncio.sleep(0.1)
        
        assert alert_triggered

class TestOrderTracker:
    """Test cases for order tracking and correlation"""
    
    @pytest.fixture
    async def order_tracker(self):
        """Create order tracker instance"""
        tracker = OrderTracker(":memory:")  # In-memory database for tests
        await tracker.initialize()
        return tracker
    
    @pytest.fixture
    def sample_signal_correlation(self):
        """Sample TMT signal correlation"""
        return TMTSignalCorrelation(
            signal_id="wyckoff_break_123",
            signal_timestamp=datetime.utcnow(),
            signal_type="wyckoff_accumulation_break",
            signal_confidence=0.85,
            instrument="EUR_USD",
            signal_side=OrderSide.BUY,
            signal_entry_price=1.12000,
            signal_stop_loss=1.11500,
            signal_take_profit=1.13000,
            correlation_created=datetime.utcnow()
        )
    
    @pytest.mark.asyncio
    async def test_track_order_with_correlation(
        self, order_tracker, sample_signal_correlation
    ):
        """Test tracking order with TMT signal correlation"""
        
        order_result = OrderResult(
            client_order_id="TMT_wyckoff_break_123_1634567890_abc123",
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
        
        await order_tracker.track_order(order_result, sample_signal_correlation)
        
        # Verify order is tracked
        tracked_order = order_tracker.get_order_by_id(order_result.client_order_id)
        assert tracked_order is not None
        assert tracked_order.status == OrderStatus.FILLED
        
        # Verify signal correlation
        correlation = order_tracker.get_signal_correlation(order_result.client_order_id)
        assert correlation is not None
        assert correlation.signal_id == "wyckoff_break_123"
        assert correlation.signal_confidence == 0.85
        
        # Verify lifecycle events
        lifecycle = order_tracker.get_order_lifecycle(order_result.client_order_id)
        assert len(lifecycle) >= 2  # created and filled events
        assert any(event.event_type == "created" for event in lifecycle)
        assert any(event.event_type == "filled" for event in lifecycle)
    
    @pytest.mark.asyncio
    async def test_get_orders_by_tmt_signal(self, order_tracker, sample_signal_correlation):
        """Test retrieving orders by TMT signal ID"""
        
        # Create multiple orders for same signal
        order_1 = OrderResult(
            client_order_id="order_1_signal_123",
            oanda_order_id="oanda_1",
            transaction_id="tx_1",
            status=OrderStatus.FILLED,
            instrument="EUR_USD",
            units=5000,
            side=OrderSide.BUY,
            requested_price=None,
            fill_price=Decimal('1.12000'),
            slippage=None,
            execution_time_ms=40.0,
            timestamp=datetime.utcnow(),
            filled_units=5000
        )
        
        order_2 = OrderResult(
            client_order_id="order_2_signal_123", 
            oanda_order_id="oanda_2",
            transaction_id="tx_2",
            status=OrderStatus.FILLED,
            instrument="EUR_USD",
            units=5000,
            side=OrderSide.BUY,
            requested_price=None,
            fill_price=Decimal('1.12010'),
            slippage=None,
            execution_time_ms=42.0,
            timestamp=datetime.utcnow(),
            filled_units=5000
        )
        
        await order_tracker.track_order(order_1, sample_signal_correlation)
        await order_tracker.track_order(order_2, sample_signal_correlation)
        
        # Retrieve orders by signal
        signal_orders = order_tracker.get_orders_by_tmt_signal("wyckoff_break_123")
        assert len(signal_orders) == 2
        
        # Verify both orders are returned
        order_ids = [order.client_order_id for order in signal_orders]
        assert "order_1_signal_123" in order_ids
        assert "order_2_signal_123" in order_ids
    
    @pytest.mark.asyncio
    async def test_execution_metrics(self, order_tracker):
        """Test execution metrics tracking"""
        
        # Track multiple orders with different outcomes
        filled_order = OrderResult(
            client_order_id="filled_order",
            oanda_order_id="oanda_1",
            transaction_id="tx_1",
            status=OrderStatus.FILLED,
            instrument="EUR_USD",
            units=10000,
            side=OrderSide.BUY,
            requested_price=None,
            fill_price=Decimal('1.12000'),
            slippage=None,
            execution_time_ms=45.0,
            timestamp=datetime.utcnow(),
            filled_units=10000
        )
        
        rejected_order = OrderResult(
            client_order_id="rejected_order",
            oanda_order_id=None,
            transaction_id=None,
            status=OrderStatus.REJECTED,
            instrument="GBP_USD",
            units=5000,
            side=OrderSide.SELL,
            requested_price=None,
            fill_price=None,
            slippage=None,
            execution_time_ms=120.0,  # Slower execution
            timestamp=datetime.utcnow(),
            rejection_reason="INSUFFICIENT_MARGIN"
        )
        
        await order_tracker.track_order(filled_order)
        await order_tracker.track_order(rejected_order)
        
        metrics = order_tracker.get_execution_metrics()
        
        assert metrics['total_orders'] == 2
        assert metrics['filled_orders'] == 1
        assert metrics['rejected_orders'] == 1
        assert metrics['fill_rate'] == 50.0
        assert metrics['rejection_rate'] == 50.0
        assert 45.0 < metrics['average_execution_time'] < 120.0

class TestPartialFillHandler:
    """Test cases for partial fill handling"""
    
    @pytest.fixture
    async def partial_fill_handler(self):
        """Create partial fill handler"""
        auth_handler = Mock(spec=OandaAuthHandler)
        order_executor = Mock()
        handler = PartialFillHandler(auth_handler, order_executor)
        yield handler
        await handler.close()
    
    @pytest.mark.asyncio
    async def test_handle_partial_fill(self, partial_fill_handler):
        """Test partial fill handling"""
        
        order_result = OrderResult(
            client_order_id="partial_order_123",
            oanda_order_id="oanda_456",
            transaction_id="tx_789",
            status=OrderStatus.FILLED,  # Will be updated to PARTIALLY_FILLED
            instrument="EUR_USD",
            units=10000,
            side=OrderSide.BUY,
            requested_price=None,
            fill_price=Decimal('1.12000'),
            slippage=None,
            execution_time_ms=50.0,
            timestamp=datetime.utcnow(),
            filled_units=0  # Will be updated
        )
        
        fill_transaction = {
            'id': 'fill_tx_123',
            'units': '6000',  # Partial fill - only 6000 of 10000
            'price': '1.12000',
            'type': 'ORDER_FILL'
        }
        
        result = await partial_fill_handler.handle_partial_fill(
            order_result, fill_transaction
        )
        
        assert result is True
        assert order_result.status == OrderStatus.PARTIALLY_FILLED
        assert order_result.filled_units == 6000
        assert order_result.remaining_units == 4000
        
        # Check tracking
        partial_fills = partial_fill_handler.get_partial_fills("partial_order_123")
        assert len(partial_fills) == 1
        assert partial_fills[0].filled_units == 6000
        assert partial_fills[0].remaining_units == 4000
        
        pending_qty = partial_fill_handler.get_pending_quantity("partial_order_123")
        assert pending_qty == 4000
    
    @pytest.mark.asyncio  
    async def test_handle_order_rejection(self, partial_fill_handler):
        """Test order rejection handling"""
        
        order_result = OrderResult(
            client_order_id="rejected_order_456",
            oanda_order_id=None,
            transaction_id=None,
            status=OrderStatus.REJECTED,
            instrument="GBP_USD",
            units=5000,
            side=OrderSide.SELL,
            requested_price=None,
            fill_price=None,
            slippage=None,
            execution_time_ms=25.0,
            timestamp=datetime.utcnow()
        )
        
        error_response = {
            'errorCode': 'INSUFFICIENT_MARGIN',
            'errorMessage': 'Insufficient margin to place order'
        }
        
        rejection = await partial_fill_handler.handle_order_rejection(
            order_result, error_response
        )
        
        assert rejection.order_id == "rejected_order_456"
        assert rejection.rejection_reason == RejectionReason.INSUFFICIENT_MARGIN
        assert rejection.error_code == "INSUFFICIENT_MARGIN"
        assert rejection.retry_strategy.name == "NO_RETRY"  # Should not retry margin issues
    
    def test_determine_retry_strategy(self, partial_fill_handler):
        """Test retry strategy determination"""
        
        # Rate limit should use exponential backoff
        strategy = partial_fill_handler._determine_retry_strategy(
            RejectionReason.RATE_LIMIT, "RATE_LIMITED"
        )
        assert strategy.name == "EXPONENTIAL_BACKOFF"
        
        # Market closed should wait for market hours
        strategy = partial_fill_handler._determine_retry_strategy(
            RejectionReason.MARKET_CLOSED, "MARKET_HALTED"
        )
        assert strategy.name == "MARKET_HOURS_ONLY"
        
        # Invalid instrument should not retry
        strategy = partial_fill_handler._determine_retry_strategy(
            RejectionReason.INVALID_INSTRUMENT, "INSTRUMENT_NOT_TRADEABLE"
        )
        assert strategy.name == "NO_RETRY"

class TestStopLossTakeProfitManager:
    """Test cases for stop loss and take profit management"""
    
    @pytest.fixture
    def sl_tp_manager(self):
        """Create SL/TP manager instance"""
        auth_handler = Mock(spec=OandaAuthHandler)
        return StopLossTakeProfitManager(auth_handler)
    
    def test_calculate_stop_loss_price(self, sl_tp_manager):
        """Test stop loss price calculation"""
        
        # Buy order - stop loss below entry price
        entry_price = Decimal('1.12000')
        stop_price = sl_tp_manager.calculate_stop_loss_price(
            entry_price=entry_price,
            side=OrderSide.BUY,
            stop_distance_pips=50,  # 50 pips
            instrument="EUR_USD"
        )
        
        expected_stop = entry_price - (50 * Decimal('0.0001'))  # 50 pips below
        assert stop_price == expected_stop
        
        # Sell order - stop loss above entry price
        stop_price_sell = sl_tp_manager.calculate_stop_loss_price(
            entry_price=entry_price,
            side=OrderSide.SELL,
            stop_distance_pips=50,
            instrument="EUR_USD" 
        )
        
        expected_stop_sell = entry_price + (50 * Decimal('0.0001'))  # 50 pips above
        assert stop_price_sell == expected_stop_sell
    
    def test_calculate_take_profit_price(self, sl_tp_manager):
        """Test take profit price calculation"""
        
        # Buy order - take profit above entry price
        entry_price = Decimal('1.12000')
        tp_price = sl_tp_manager.calculate_take_profit_price(
            entry_price=entry_price,
            side=OrderSide.BUY,
            profit_distance_pips=100,  # 100 pips
            instrument="EUR_USD"
        )
        
        expected_tp = entry_price + (100 * Decimal('0.0001'))  # 100 pips above
        assert tp_price == expected_tp
        
        # Sell order - take profit below entry price
        tp_price_sell = sl_tp_manager.calculate_take_profit_price(
            entry_price=entry_price,
            side=OrderSide.SELL,
            profit_distance_pips=100,
            instrument="EUR_USD"
        )
        
        expected_tp_sell = entry_price - (100 * Decimal('0.0001'))  # 100 pips below
        assert tp_price_sell == expected_tp_sell
    
    def test_guaranteed_stop_fee_calculation(self, sl_tp_manager):
        """Test guaranteed stop loss fee calculation"""
        
        # 100,000 units = 1 lot
        fee = sl_tp_manager.get_guaranteed_stop_fee("EUR_USD", 100000)
        
        # Should be 0.5 pips * 1 lot = 0.5 fee
        assert fee == Decimal('0.5')
        
        # 50,000 units = 0.5 lots
        fee_half_lot = sl_tp_manager.get_guaranteed_stop_fee("EUR_USD", 50000)
        assert fee_half_lot == Decimal('0.25')

if __name__ == "__main__":
    # Run specific test categories
    pytest.main([
        __file__,
        "-v",
        "-x",  # Stop on first failure
        "--tb=short"  # Short traceback format
    ])