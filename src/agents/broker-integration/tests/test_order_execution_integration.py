"""
Integration Tests for Order Execution System
Story 8.3 - Full system integration tests

Tests the complete order execution flow including:
- Order execution with SL/TP
- Slippage monitoring
- Order tracking and correlation
- Partial fill handling
- Error recovery
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from decimal import Decimal

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from order_executor import OandaOrderExecutor, OrderSide, OrderStatus
from slippage_monitor import SlippageMonitor
from order_tracker import OrderTracker, TMTSignalCorrelation
from partial_fill_handler import PartialFillHandler
from stop_loss_take_profit import StopLossTakeProfitManager, StopLossConfig, StopType
from oanda_auth_handler import OandaAuthHandler, AccountContext, Environment

class TestOrderExecutionIntegration:
    """Integration tests for complete order execution system"""
    
    @pytest.fixture
    async def integrated_system(self):
        """Set up complete integrated order execution system"""
        
        # Mock auth handler
        auth_handler = Mock(spec=OandaAuthHandler)
        context = AccountContext(
            user_id="test_user",
            account_id="test_account", 
            environment=Environment.PRACTICE,
            api_key="test_api_key",
            base_url="https://api-fxpractice.oanda.com",
            authenticated_at=datetime.utcnow(),
            last_refresh=datetime.utcnow(),
            session_valid=True
        )
        auth_handler.get_session_context = AsyncMock(return_value=context)
        
        # Create system components
        order_executor = OandaOrderExecutor(auth_handler)
        slippage_monitor = SlippageMonitor()
        order_tracker = OrderTracker(":memory:")
        await order_tracker.initialize()
        partial_fill_handler = PartialFillHandler(auth_handler, order_executor)
        sl_tp_manager = StopLossTakeProfitManager(auth_handler)
        
        # Wire up components
        system = {
            'auth_handler': auth_handler,
            'order_executor': order_executor,
            'slippage_monitor': slippage_monitor,
            'order_tracker': order_tracker,
            'partial_fill_handler': partial_fill_handler,
            'sl_tp_manager': sl_tp_manager
        }
        
        yield system
        
        # Cleanup
        await order_executor.close()
        await partial_fill_handler.close()
        await sl_tp_manager.close()
    
    @pytest.mark.asyncio
    async def test_complete_order_execution_flow(self, integrated_system):
        """Test complete order execution with all components"""
        
        # Mock successful order execution response
        mock_response = {
            'orderFillTransaction': {
                'id': 'fill_12345',
                'orderID': 'order_67890',
                'price': '1.12050',  # Slight slippage from expected 1.12000
                'units': '10000',
                'type': 'ORDER_FILL',
                'instrument': 'EUR_USD'
            },
            'orderCreateTransaction': {
                'id': 'order_67890',
                'type': 'MARKET_ORDER'
            }
        }
        
        with patch.object(integrated_system['order_executor'], '_send_order_request',
                         return_value=mock_response):
            
            # 1. Create TMT signal correlation
            signal_correlation = TMTSignalCorrelation(
                signal_id="wyckoff_accumulation_123",
                signal_timestamp=datetime.utcnow(),
                signal_type="wyckoff_accumulation_break",
                signal_confidence=0.92,
                instrument="EUR_USD",
                signal_side=OrderSide.BUY,
                signal_entry_price=1.12000,
                signal_stop_loss=1.11500,
                signal_take_profit=1.13000,
                correlation_created=datetime.utcnow()
            )
            
            # 2. Execute market order with stop loss and take profit
            order_result = await integrated_system['order_executor'].execute_market_order(
                user_id="test_user",
                account_id="test_account",
                instrument="EUR_USD",
                units=10000,
                side=OrderSide.BUY,
                stop_loss=Decimal('1.11500'),
                take_profit=Decimal('1.13000'),
                tmt_signal_id="wyckoff_accumulation_123"
            )
            
            # 3. Verify order execution
            assert order_result.status == OrderStatus.FILLED
            assert order_result.fill_price == Decimal('1.12050')
            assert order_result.execution_time_ms < 100
            assert "wyckoff_accumulation_123" in order_result.client_order_id
            
            # 4. Track order with signal correlation
            await integrated_system['order_tracker'].track_order(
                order_result, signal_correlation
            )
            
            # 5. Record slippage (expected price vs actual)
            expected_price = Decimal('1.12000')
            await integrated_system['slippage_monitor'].record_execution(
                order_result, expected_price
            )
            
            # 6. Verify order tracking
            tracked_order = integrated_system['order_tracker'].get_order_by_id(
                order_result.client_order_id
            )
            assert tracked_order is not None
            assert tracked_order.status == OrderStatus.FILLED
            
            # 7. Verify signal correlation
            correlation = integrated_system['order_tracker'].get_signal_correlation(
                order_result.client_order_id
            )
            assert correlation is not None
            assert correlation.signal_id == "wyckoff_accumulation_123"
            assert correlation.signal_confidence == 0.92
            
            # 8. Verify slippage monitoring
            slippage_stats = integrated_system['slippage_monitor'].get_slippage_stats("EUR_USD")
            assert slippage_stats is not None
            assert slippage_stats.total_trades == 1
            assert slippage_stats.average_slippage_bps > 0  # Positive slippage (paid more)
            
            # 9. Verify execution metrics
            metrics = integrated_system['order_tracker'].get_execution_metrics()
            assert metrics['total_orders'] == 1
            assert metrics['filled_orders'] == 1
            assert metrics['fill_rate'] == 100.0
            assert metrics['sub_100ms_rate'] == 100.0
    
    @pytest.mark.asyncio
    async def test_partial_fill_integration(self, integrated_system):
        """Test partial fill handling integration"""
        
        # Mock partial fill response
        partial_fill_response = {
            'orderFillTransaction': {
                'id': 'partial_fill_123',
                'orderID': 'order_456',
                'price': '1.25000',
                'units': '3000',  # Only 3000 of 5000 filled
                'type': 'ORDER_FILL',
                'instrument': 'GBP_USD'
            },
            'orderCreateTransaction': {
                'id': 'order_456',
                'type': 'MARKET_ORDER'
            }
        }
        
        with patch.object(integrated_system['order_executor'], '_send_order_request',
                         return_value=partial_fill_response):
            
            # Execute order that will be partially filled
            order_result = await integrated_system['order_executor'].execute_market_order(
                user_id="test_user",
                account_id="test_account",
                instrument="GBP_USD",
                units=5000,
                side=OrderSide.BUY
            )
            
            # Simulate partial fill handling
            fill_transaction = {
                'id': 'partial_fill_123',
                'units': '3000',
                'price': '1.25000',
                'type': 'ORDER_FILL'
            }
            
            # Handle partial fill
            await integrated_system['partial_fill_handler'].handle_partial_fill(
                order_result, fill_transaction
            )
            
            # Verify partial fill tracking
            assert order_result.status == OrderStatus.PARTIALLY_FILLED
            assert order_result.filled_units == 3000
            assert order_result.remaining_units == 2000
            
            partial_fills = integrated_system['partial_fill_handler'].get_partial_fills(
                order_result.client_order_id
            )
            assert len(partial_fills) == 1
            assert partial_fills[0].remaining_units == 2000
            
            pending_qty = integrated_system['partial_fill_handler'].get_pending_quantity(
                order_result.client_order_id
            )
            assert pending_qty == 2000
    
    @pytest.mark.asyncio
    async def test_order_rejection_and_retry_integration(self, integrated_system):
        """Test order rejection and retry mechanism"""
        
        # Mock rejection response
        rejection_response = {
            'errorCode': 'RATE_LIMITED',
            'errorMessage': 'Request rate limit exceeded'
        }
        
        with patch.object(integrated_system['order_executor'], '_send_order_request',
                         side_effect=Exception("RATE_LIMITED - Request rate limit exceeded")):
            
            # Execute order that will be rejected
            order_result = await integrated_system['order_executor'].execute_market_order(
                user_id="test_user",
                account_id="test_account",
                instrument="USD_JPY",
                units=10000,
                side=OrderSide.SELL
            )
            
            # Verify rejection
            assert order_result.status == OrderStatus.REJECTED
            assert "RATE_LIMITED" in order_result.rejection_reason
            
            # Handle rejection
            rejection = await integrated_system['partial_fill_handler'].handle_order_rejection(
                order_result, rejection_response
            )
            
            # Verify retry strategy
            assert rejection.retry_strategy.name == "EXPONENTIAL_BACKOFF"
            
            # Check retry queue status
            retry_status = integrated_system['partial_fill_handler'].get_retry_queue_status()
            assert retry_status['queue_size'] >= 1
            assert retry_status['total_rejections'] >= 1
    
    @pytest.mark.asyncio
    async def test_stop_loss_take_profit_integration(self, integrated_system):
        """Test stop loss and take profit creation after order fill"""
        
        # Mock order fill
        mock_response = {
            'orderFillTransaction': {
                'id': 'fill_789',
                'orderID': 'order_123',
                'price': '1.12000',
                'units': '10000',
                'type': 'ORDER_FILL'
            }
        }
        
        # Mock SL/TP creation responses
        sl_response = {
            'orderCreateTransaction': {
                'id': 'sl_order_456',
                'type': 'STOP_LOSS'
            }
        }
        
        tp_response = {
            'orderCreateTransaction': {
                'id': 'tp_order_789',
                'type': 'TAKE_PROFIT'
            }
        }
        
        with patch.object(integrated_system['order_executor'], '_send_order_request',
                         return_value=mock_response), \
             patch.object(integrated_system['sl_tp_manager'], '_send_order_request',
                         side_effect=[sl_response, tp_response]):
            
            # 1. Execute main order
            order_result = await integrated_system['order_executor'].execute_market_order(
                user_id="test_user",
                account_id="test_account",
                instrument="EUR_USD",
                units=10000,
                side=OrderSide.BUY
            )
            
            assert order_result.status == OrderStatus.FILLED
            
            # 2. Create stop loss order
            stop_loss_config = StopLossConfig(
                price=Decimal('1.11500'),
                stop_type=StopType.FIXED,
                guaranteed=False
            )
            
            sl_order_id = await integrated_system['sl_tp_manager'].create_stop_loss_order(
                user_id="test_user",
                account_id="test_account",
                trade_id="order_123",
                instrument="EUR_USD",
                units=-10000,  # Negative to close long position
                stop_config=stop_loss_config
            )
            
            assert sl_order_id == 'sl_order_456'
            
            # 3. Create take profit order
            from stop_loss_take_profit import TakeProfitConfig
            
            take_profit_config = TakeProfitConfig(
                price=Decimal('1.13000')
            )
            
            tp_order_id = await integrated_system['sl_tp_manager'].create_take_profit_order(
                user_id="test_user",
                account_id="test_account",
                trade_id="order_123",
                instrument="EUR_USD",
                units=-10000,
                tp_config=take_profit_config
            )
            
            assert tp_order_id == 'tp_order_789'
            
            # 4. Verify SL/TP tracking
            stop_orders = integrated_system['sl_tp_manager'].get_stop_loss_orders("order_123")
            assert len(stop_orders) == 1
            assert stop_orders[0].stop_price == Decimal('1.11500')
    
    @pytest.mark.asyncio
    async def test_high_frequency_order_execution(self, integrated_system):
        """Test system performance under high-frequency order execution"""
        
        mock_response = {
            'orderFillTransaction': {
                'id': 'fill_{i}',
                'orderID': 'order_{i}',
                'price': '1.12000',
                'units': '1000',
                'type': 'ORDER_FILL'
            }
        }
        
        with patch.object(integrated_system['order_executor'], '_send_order_request',
                         return_value=mock_response):
            
            # Execute multiple orders concurrently
            order_tasks = []
            for i in range(10):
                task = integrated_system['order_executor'].execute_market_order(
                    user_id="test_user",
                    account_id="test_account",
                    instrument="EUR_USD",
                    units=1000,
                    side=OrderSide.BUY,
                    tmt_signal_id=f"signal_{i}"
                )
                order_tasks.append(task)
            
            # Wait for all orders to complete
            order_results = await asyncio.gather(*order_tasks)
            
            # Verify all orders executed successfully
            assert len(order_results) == 10
            for result in order_results:
                assert result.status == OrderStatus.FILLED
                assert result.execution_time_ms < 100  # Sub-100ms requirement
            
            # Verify performance metrics
            metrics = integrated_system['order_executor'].get_execution_metrics()
            assert metrics['total_orders'] == 10
            assert metrics['filled_orders'] == 10
            assert metrics['sub_100ms_rate'] == 100.0
    
    @pytest.mark.asyncio
    async def test_error_recovery_and_circuit_breaker(self, integrated_system):
        """Test error recovery and circuit breaker functionality"""
        
        # Simulate multiple consecutive failures
        failure_count = 0
        
        def mock_failing_request(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 3:
                raise Exception("TEMPORARY_ERROR - Service temporarily unavailable")
            else:
                # Success after 3 failures
                return {
                    'orderFillTransaction': {
                        'id': 'recovery_fill',
                        'orderID': 'recovery_order',
                        'price': '1.12000',
                        'units': '5000',
                        'type': 'ORDER_FILL'
                    }
                }
        
        with patch.object(integrated_system['order_executor'], '_send_order_request',
                         side_effect=mock_failing_request):
            
            # Execute orders that will initially fail
            results = []
            for i in range(5):
                result = await integrated_system['order_executor'].execute_market_order(
                    user_id="test_user",
                    account_id="test_account",
                    instrument="EUR_USD",
                    units=5000,
                    side=OrderSide.BUY
                )
                results.append(result)
                
                # Small delay between attempts
                await asyncio.sleep(0.1)
            
            # Verify failure and recovery pattern
            failed_orders = [r for r in results if r.status == OrderStatus.REJECTED]
            successful_orders = [r for r in results if r.status == OrderStatus.FILLED]
            
            assert len(failed_orders) == 3  # First 3 should fail
            assert len(successful_orders) == 2  # Last 2 should succeed
    
    @pytest.mark.asyncio
    async def test_latency_requirements_compliance(self, integrated_system):
        """Test compliance with sub-100ms latency requirements"""
        
        # Mock very fast response
        mock_response = {
            'orderFillTransaction': {
                'id': 'fast_fill',
                'orderID': 'fast_order', 
                'price': '1.12000',
                'units': '10000',
                'type': 'ORDER_FILL'
            }
        }
        
        with patch.object(integrated_system['order_executor'], '_send_order_request',
                         return_value=mock_response):
            
            # Measure execution times for multiple orders
            execution_times = []
            
            for _ in range(20):
                start_time = datetime.utcnow()
                
                result = await integrated_system['order_executor'].execute_market_order(
                    user_id="test_user",
                    account_id="test_account",
                    instrument="EUR_USD",
                    units=10000,
                    side=OrderSide.BUY
                )
                
                execution_times.append(result.execution_time_ms)
            
            # Verify latency requirements
            average_latency = sum(execution_times) / len(execution_times)
            max_latency = max(execution_times)
            sub_100ms_count = sum(1 for t in execution_times if t < 100)
            
            assert average_latency < 100, f"Average latency {average_latency}ms exceeds 100ms"
            assert max_latency < 150, f"Max latency {max_latency}ms too high"
            assert sub_100ms_count >= 18, f"Only {sub_100ms_count}/20 orders under 100ms"  # 90% target

if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "-x",
        "--tb=short"
    ])