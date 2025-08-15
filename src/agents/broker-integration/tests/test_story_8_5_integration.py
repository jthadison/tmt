"""
Integration Tests for Story 8.5: Real-Time Price Streaming
Testing integration between all price streaming components
"""
import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from oanda_price_stream import OandaStreamManager, PriceTick
from market_session_handler import MarketSessionHandler, SessionEvent, MarketStatus
from price_distribution_server import PriceDistributionServer, MessageType
from latency_monitor import LatencyMonitor

@pytest.mark.asyncio
async def test_end_to_end_price_streaming():
    """Test complete end-to-end price streaming integration"""
    # Mock credential manager
    mock_credential_manager = Mock()
    mock_credential_manager.retrieve_credentials.return_value = {
        'api_key': 'test_key',
        'account_id': 'test_account'
    }
    
    # Create all components
    stream_manager = OandaStreamManager(
        credential_manager=mock_credential_manager,
        account_id='test_account',
        environment='practice'
    )
    
    session_handler = MarketSessionHandler()
    latency_monitor = LatencyMonitor()
    
    distribution_server = PriceDistributionServer(
        stream_manager=stream_manager,
        session_handler=session_handler,
        host="localhost",
        port=0,
        require_authentication=False
    )
    
    try:
        # Start all components
        await distribution_server.start()
        await latency_monitor.start_monitoring()
        session_handler.add_instrument("EUR_USD")
        
        # Create test client
        test_client_id = "integration_client"
        mock_websocket = AsyncMock()
        
        from price_distribution_server import ClientConnection
        client = ClientConnection(
            websocket=mock_websocket,
            client_id=test_client_id,
            subscriptions={'EUR_USD'},
            last_activity=datetime.now(timezone.utc),
            authenticated=True
        )
        distribution_server.clients[test_client_id] = client
        
        # Start end-to-end latency trace
        trace = latency_monitor.start_trace("e2e_test", "EUR_USD")
        latency_monitor.add_trace_point("e2e_test", "price_received")
        
        # Create and process price tick
        price_tick = PriceTick(
            instrument="EUR_USD",
            bid=Decimal("1.1234"),
            ask=Decimal("1.1236"),
            spread_pips=Decimal("2.0"),
            timestamp=datetime.now(timezone.utc),
            tradeable=True,
            latency_ms=45.0
        )
        
        # Flow price through system
        await distribution_server._on_price_update(price_tick)
        
        # Add more trace points
        latency_monitor.add_trace_point("e2e_test", "price_processed")
        latency_monitor.add_trace_point("e2e_test", "price_distributed")
        
        # Complete trace
        completed_trace = latency_monitor.complete_trace("e2e_test")
        
        # Verify end-to-end flow worked
        assert completed_trace is not None
        assert completed_trace.get_total_latency() > 0
        assert len(completed_trace.points) == 3
        
        # Verify price was queued for distribution
        assert test_client_id in distribution_server.message_queues
        
        # Check system health
        health = latency_monitor.get_system_health_summary()
        assert health["health_score"] > 50  # Should be reasonable
        
        # Verify metrics
        metrics = distribution_server.get_metrics()
        assert metrics['server']['connected_clients'] == 1
        
        # Test market session integration
        market_status = session_handler.get_instrument_status("EUR_USD")
        assert market_status is not None
        
    finally:
        # Cleanup
        await distribution_server.stop()
        await latency_monitor.stop_monitoring()

@pytest.mark.asyncio
async def test_security_integration():
    """Test security features integration"""
    mock_stream_manager = Mock()
    mock_stream_manager.subscription_manager = Mock()
    mock_stream_manager.subscription_manager.active_subscriptions = {'EUR_USD'}
    mock_stream_manager.add_price_callback = Mock()
    
    server = PriceDistributionServer(
        stream_manager=mock_stream_manager,
        host="localhost",
        port=0,
        require_authentication=True,
        max_connections=10
    )
    
    # Test authentication flow
    mock_websocket = AsyncMock()
    mock_websocket.request_headers = {'Authorization': 'Bearer valid_token'}
    
    # Mock JWT validation to return valid payload
    with patch.object(server.security_manager, 'validate_jwt_token') as mock_validate:
        mock_validate.return_value = {'user_id': 'test_user', 'exp': 9999999999}
        
        result = await server._authenticate_client(mock_websocket, "test_client")
        assert result is True

@pytest.mark.asyncio
async def test_performance_integration():
    """Test performance features integration"""
    mock_stream_manager = Mock()
    mock_stream_manager.subscription_manager = Mock()
    mock_stream_manager.subscription_manager.active_subscriptions = {'EUR_USD'}
    mock_stream_manager.add_price_callback = Mock()
    
    server = PriceDistributionServer(
        stream_manager=mock_stream_manager,
        require_authentication=False
    )
    
    # Test frequency management
    frequency_manager = server.frequency_manager
    
    # Test initial update is allowed
    assert frequency_manager.can_send_update("client1", 2.0) is True  # 2 Hz
    
    # Test immediate second update is blocked
    assert frequency_manager.can_send_update("client1", 2.0) is False
    
    # Wait and test update is allowed again
    await asyncio.sleep(0.6)  # Wait for frequency interval
    assert frequency_manager.can_send_update("client1", 2.0) is True

if __name__ == "__main__":
    pytest.main([__file__])