"""
Tests for Price Distribution Server
Story 8.5: Real-Time Price Streaming - Task 5 Tests
"""
import pytest
import asyncio
import json
import gzip
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from price_distribution_server import (
    PriceDistributionServer,
    PriceMessage,
    MessageType,
    CompressionLevel,
    ClientConnection,
    UpdateFrequencyManager,
    SelectiveUpdateFilter
)
from oanda_price_stream import PriceTick, OandaStreamManager
from market_session_handler import MarketSessionHandler, SessionEvent, MarketStatus

class TestPriceMessage:
    """Test price message functionality"""
    
    def test_price_message_creation(self):
        """Test creating a price message"""
        data = {'instrument': 'EUR_USD', 'bid': '1.1234', 'ask': '1.1236'}
        msg = PriceMessage(MessageType.PRICE_UPDATE, data)
        
        assert msg.type == MessageType.PRICE_UPDATE
        assert msg.data == data
        assert msg.timestamp is not None
        
    def test_price_message_to_dict(self):
        """Test converting price message to dictionary"""
        data = {'test': 'data'}
        msg = PriceMessage(MessageType.PING, data)
        
        result = msg.to_dict()
        
        assert result['type'] == 'ping'
        assert result['data'] == data
        assert 'timestamp' in result
        
    def test_price_message_to_json(self):
        """Test converting price message to JSON"""
        data = {'instrument': 'EUR_USD'}
        msg = PriceMessage(MessageType.PRICE_UPDATE, data)
        
        json_str = msg.to_json()
        parsed = json.loads(json_str)
        
        assert parsed['type'] == 'price_update'
        assert parsed['data'] == data
        
    def test_price_message_compression(self):
        """Test message compression"""
        data = {'large_data': 'x' * 1000}  # Large data to test compression
        msg = PriceMessage(MessageType.BATCH_UPDATE, data)
        
        # Test no compression
        uncompressed = msg.compress(CompressionLevel.NONE)
        assert isinstance(uncompressed, bytes)
        
        # Test compression levels
        low_compressed = msg.compress(CompressionLevel.LOW)
        medium_compressed = msg.compress(CompressionLevel.MEDIUM)
        high_compressed = msg.compress(CompressionLevel.HIGH)
        
        # Compressed should be smaller than uncompressed
        assert len(low_compressed) < len(uncompressed)
        assert len(medium_compressed) < len(uncompressed)
        assert len(high_compressed) < len(uncompressed)
        
        # Higher compression should generally be smaller
        assert len(high_compressed) <= len(medium_compressed) <= len(low_compressed)

class TestUpdateFrequencyManager:
    """Test update frequency management"""
    
    @pytest.fixture
    def frequency_manager(self):
        return UpdateFrequencyManager()
        
    def test_frequency_manager_creation(self, frequency_manager):
        """Test creating frequency manager"""
        assert len(frequency_manager.client_frequencies) == 0
        assert len(frequency_manager.last_update_times) == 0
        
    def test_can_send_update_first_time(self, frequency_manager):
        """Test first update is always allowed"""
        result = frequency_manager.can_send_update('client1', 1.0)
        assert result is True
        
    def test_can_send_update_frequency_limit(self, frequency_manager):
        """Test frequency limiting"""
        # First update
        assert frequency_manager.can_send_update('client1', 2.0) is True  # 2 updates/sec
        
        # Immediate second update should be blocked
        assert frequency_manager.can_send_update('client1', 2.0) is False
        
    @pytest.mark.asyncio
    async def test_can_send_update_after_interval(self, frequency_manager):
        """Test update allowed after time interval"""
        # First update at 2 Hz (0.5 second interval)
        assert frequency_manager.can_send_update('client1', 2.0) is True
        
        # Wait for interval
        await asyncio.sleep(0.6)
        
        # Should now be allowed
        assert frequency_manager.can_send_update('client1', 2.0) is True
        
    def test_get_metrics(self, frequency_manager):
        """Test getting frequency metrics"""
        frequency_manager.can_send_update('client1', 1.0)
        frequency_manager.can_send_update('client2', 2.0)
        
        metrics = frequency_manager.get_metrics()
        
        assert metrics['clients'] == 2
        assert metrics['total_updates'] >= 2

class TestSelectiveUpdateFilter:
    """Test selective update filtering"""
    
    @pytest.fixture
    def update_filter(self):
        return SelectiveUpdateFilter()
        
    @pytest.fixture
    def sample_price_tick(self):
        return PriceTick(
            instrument="EUR_USD",
            bid=Decimal("1.1234"),
            ask=Decimal("1.1236"),
            spread_pips=Decimal("2.0"),
            timestamp=datetime.now(timezone.utc),
            tradeable=True,
            latency_ms=50.0
        )
        
    def test_first_update_always_sent(self, update_filter, sample_price_tick):
        """Test first update is always sent"""
        result = update_filter.should_send_update('client1', 'EUR_USD', sample_price_tick)
        assert result is True
        
    def test_small_price_change_filtered(self, update_filter, sample_price_tick):
        """Test small price changes are filtered"""
        # Send first update
        update_filter.should_send_update('client1', 'EUR_USD', sample_price_tick)
        
        # Create tick with small change (0.05 pips)
        small_change_tick = PriceTick(
            instrument="EUR_USD",
            bid=Decimal("1.12345"),  # 0.5 pip change
            ask=Decimal("1.12365"),
            spread_pips=Decimal("2.0"),
            timestamp=datetime.now(timezone.utc),
            tradeable=True,
            latency_ms=50.0
        )
        
        # Should be filtered (below default 0.1 pip threshold)
        result = update_filter.should_send_update('client1', 'EUR_USD', small_change_tick)
        assert result is False
        
    def test_large_price_change_sent(self, update_filter, sample_price_tick):
        """Test large price changes are sent"""
        # Send first update
        update_filter.should_send_update('client1', 'EUR_USD', sample_price_tick)
        
        # Create tick with large change (2 pips) and sufficient time gap
        large_change_tick = PriceTick(
            instrument="EUR_USD",
            bid=Decimal("1.1254"),  # 2 pip change
            ask=Decimal("1.1256"),
            spread_pips=Decimal("2.0"),
            timestamp=datetime.now(timezone.utc) + timedelta(seconds=1),  # Add time gap
            tradeable=True,
            latency_ms=50.0
        )
        
        # Should be sent (above default 0.1 pip threshold)
        result = update_filter.should_send_update('client1', 'EUR_USD', large_change_tick)
        assert result is True
        
    def test_set_client_thresholds(self, update_filter):
        """Test setting custom thresholds"""
        update_filter.set_client_thresholds('client1', 'EUR_USD', 5.0, 1.0)
        
        assert update_filter.price_thresholds['client1_EUR_USD'] == 5.0
        assert update_filter.time_thresholds['client1_EUR_USD'] == 1.0

class TestPriceDistributionServer:
    """Test price distribution server"""
    
    @pytest.fixture
    def mock_stream_manager(self):
        """Mock OANDA stream manager"""
        manager = Mock(spec=OandaStreamManager)
        manager.subscription_manager = Mock()
        manager.subscription_manager.active_subscriptions = {'EUR_USD', 'GBP_USD'}
        manager.add_price_callback = Mock()
        return manager
        
    @pytest.fixture
    def mock_session_handler(self):
        """Mock market session handler"""
        handler = Mock(spec=MarketSessionHandler)
        handler.add_status_change_callback = Mock()
        return handler
        
    @pytest.fixture
    def server(self, mock_stream_manager, mock_session_handler):
        """Create price distribution server"""
        return PriceDistributionServer(
            stream_manager=mock_stream_manager,
            session_handler=mock_session_handler,
            host="localhost",
            port=0  # Use random port for testing
        )
        
    def test_server_creation(self, server):
        """Test creating price distribution server"""
        assert server.host == "localhost"
        assert server.port == 0
        assert server.is_running is False
        assert len(server.clients) == 0
        
    def test_setup_callbacks(self, server, mock_stream_manager, mock_session_handler):
        """Test callback setup"""
        # Verify callbacks were registered
        mock_stream_manager.add_price_callback.assert_called_once()
        mock_session_handler.add_status_change_callback.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_on_price_update(self, server):
        """Test handling price updates"""
        # Add mock client
        mock_websocket = AsyncMock()
        client = ClientConnection(
            websocket=mock_websocket,
            client_id='test_client',
            subscriptions={'EUR_USD'},
            last_activity=datetime.now(timezone.utc)
        )
        server.clients['test_client'] = client
        
        # Create price tick
        price_tick = PriceTick(
            instrument="EUR_USD",
            bid=Decimal("1.1234"),
            ask=Decimal("1.1236"),
            spread_pips=Decimal("2.0"),
            timestamp=datetime.now(timezone.utc),
            tradeable=True,
            latency_ms=50.0
        )
        
        # Handle price update
        await server._on_price_update(price_tick)
        
        # Verify message was queued
        assert len(server.message_queues['test_client']) > 0
        
    @pytest.mark.asyncio
    async def test_on_market_status_change(self, server):
        """Test handling market status changes"""
        # Add mock client
        mock_websocket = AsyncMock()
        client = ClientConnection(
            websocket=mock_websocket,
            client_id='test_client',
            subscriptions={'EUR_USD'},
            last_activity=datetime.now(timezone.utc)
        )
        server.clients['test_client'] = client
        
        # Create session event
        event = SessionEvent(
            instrument='EUR_USD',
            status=MarketStatus.CLOSED,
            timestamp=datetime.now(timezone.utc),
            message='Market closed'
        )
        
        # Handle market status change
        await server._on_market_status_change(event)
        
        # Verify message was sent
        mock_websocket.send.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_handle_subscribe_message(self, server):
        """Test handling subscription messages"""
        # Add mock client
        mock_websocket = AsyncMock()
        client = ClientConnection(
            websocket=mock_websocket,
            client_id='test_client',
            subscriptions=set(),
            last_activity=datetime.now(timezone.utc)
        )
        server.clients['test_client'] = client
        
        # Handle subscribe message
        data = {'instruments': ['EUR_USD', 'GBP_USD']}
        await server._handle_subscribe('test_client', data)
        
        # Verify subscriptions were added
        assert 'EUR_USD' in client.subscriptions
        assert 'GBP_USD' in client.subscriptions
        
        # Verify acknowledgment was sent
        mock_websocket.send.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_handle_unsubscribe_message(self, server):
        """Test handling unsubscription messages"""
        # Add mock client with existing subscriptions
        mock_websocket = AsyncMock()
        client = ClientConnection(
            websocket=mock_websocket,
            client_id='test_client',
            subscriptions={'EUR_USD', 'GBP_USD', 'USD_JPY'},
            last_activity=datetime.now(timezone.utc)
        )
        server.clients['test_client'] = client
        
        # Handle unsubscribe message
        data = {'instruments': ['EUR_USD', 'GBP_USD']}
        await server._handle_unsubscribe('test_client', data)
        
        # Verify subscriptions were removed
        assert 'EUR_USD' not in client.subscriptions
        assert 'GBP_USD' not in client.subscriptions
        assert 'USD_JPY' in client.subscriptions  # Should remain
        
        # Verify acknowledgment was sent
        mock_websocket.send.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_handle_set_frequency_message(self, server):
        """Test handling frequency setting messages"""
        # Add mock client
        mock_websocket = AsyncMock()
        client = ClientConnection(
            websocket=mock_websocket,
            client_id='test_client',
            subscriptions=set(),
            last_activity=datetime.now(timezone.utc),
            update_frequency=1.0
        )
        server.clients['test_client'] = client
        
        # Handle set frequency message
        data = {'frequency': 5.0}
        await server._handle_set_frequency('test_client', data)
        
        # Verify frequency was updated
        assert client.update_frequency == 5.0
        
        # Verify confirmation was sent
        mock_websocket.send.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_handle_set_compression_message(self, server):
        """Test handling compression setting messages"""
        # Add mock client
        mock_websocket = AsyncMock()
        client = ClientConnection(
            websocket=mock_websocket,
            client_id='test_client',
            subscriptions=set(),
            last_activity=datetime.now(timezone.utc)
        )
        server.clients['test_client'] = client
        
        # Handle set compression message
        data = {'enabled': True, 'level': 'high'}
        await server._handle_set_compression('test_client', data)
        
        # Verify compression settings were updated
        assert client.compression_enabled is True
        assert client.compression_level == CompressionLevel.HIGH
        
    @pytest.mark.asyncio
    async def test_handle_ping_message(self, server):
        """Test handling ping messages"""
        # Add mock client
        mock_websocket = AsyncMock()
        client = ClientConnection(
            websocket=mock_websocket,
            client_id='test_client',
            subscriptions=set(),
            last_activity=datetime.now(timezone.utc)
        )
        server.clients['test_client'] = client
        
        # Handle ping message
        await server._handle_ping('test_client', {})
        
        # Verify last ping was updated
        assert client.last_ping is not None
        
        # Verify pong was sent
        mock_websocket.send.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_send_message_to_client_uncompressed(self, server):
        """Test sending uncompressed message to client"""
        # Add mock client
        mock_websocket = AsyncMock()
        client = ClientConnection(
            websocket=mock_websocket,
            client_id='test_client',
            subscriptions=set(),
            last_activity=datetime.now(timezone.utc),
            compression_enabled=False
        )
        server.clients['test_client'] = client
        
        # Send message
        message = PriceMessage(MessageType.PING, {'test': 'data'})
        await server._send_message_to_client('test_client', message)
        
        # Verify message was sent
        mock_websocket.send.assert_called_once()
        sent_data = mock_websocket.send.call_args[0][0]
        assert isinstance(sent_data, str)
        
    @pytest.mark.asyncio
    async def test_send_message_to_client_compressed(self, server):
        """Test sending compressed message to client"""
        # Add mock client with compression enabled
        mock_websocket = AsyncMock()
        client = ClientConnection(
            websocket=mock_websocket,
            client_id='test_client',
            subscriptions=set(),
            last_activity=datetime.now(timezone.utc),
            compression_enabled=True,
            compression_level=CompressionLevel.MEDIUM
        )
        server.clients['test_client'] = client
        
        # Send message
        message = PriceMessage(MessageType.PING, {'test': 'data'})
        await server._send_message_to_client('test_client', message)
        
        # Verify message was sent
        mock_websocket.send.assert_called_once()
        sent_data = mock_websocket.send.call_args[0][0]
        assert isinstance(sent_data, bytes)
        
        # Verify it's compressed by trying to decompress
        decompressed = gzip.decompress(sent_data).decode('utf-8')
        parsed = json.loads(decompressed)
        assert parsed['type'] == 'ping'
        
    def test_get_metrics(self, server):
        """Test getting server metrics"""
        # Add some test data
        server.metrics['total_messages_sent'] = 100
        server.metrics['connections'] = 5
        
        metrics = server.get_metrics()
        
        assert 'server' in metrics
        assert 'messages' in metrics
        assert 'bandwidth' in metrics
        assert 'latency' in metrics
        assert 'frequency' in metrics
        assert 'clients' in metrics
        
        assert metrics['server']['connected_clients'] == 0
        assert metrics['messages']['total_sent'] == 100

@pytest.mark.asyncio
async def test_integration_price_distribution():
    """Test complete price distribution integration"""
    # Create mock dependencies
    mock_stream_manager = Mock(spec=OandaStreamManager)
    mock_stream_manager.subscription_manager = Mock()
    mock_stream_manager.subscription_manager.active_subscriptions = {'EUR_USD'}
    mock_stream_manager.add_price_callback = Mock()
    
    # Create server
    server = PriceDistributionServer(
        stream_manager=mock_stream_manager,
        host="localhost",
        port=0
    )
    
    # Verify initialization
    assert server.is_running is False
    assert len(server.clients) == 0
    
    # Verify callbacks were set up
    mock_stream_manager.add_price_callback.assert_called_once()
    
    # Test metrics
    metrics = server.get_metrics()
    assert metrics['server']['connected_clients'] == 0

if __name__ == "__main__":
    pytest.main([__file__])