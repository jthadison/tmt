"""
Tests for OANDA Price Streaming Manager
Story 8.5: Real-Time Price Streaming - Task 1 Tests
"""
import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from oanda_price_stream import (
    OandaStreamManager, 
    PriceTick, 
    StreamState, 
    SubscriptionManager,
    HeartbeatMonitor,
    RateLimiter
)
from credential_manager import OandaCredentialManager

class TestPriceTick:
    """Test PriceTick data class"""
    
    def test_price_tick_creation(self):
        """Test creating a price tick"""
        tick = PriceTick(
            instrument="EUR_USD",
            bid=Decimal("1.1234"),
            ask=Decimal("1.1236"),
            spread_pips=Decimal("2.0"),
            timestamp=datetime.now(timezone.utc),
            tradeable=True,
            latency_ms=50.0
        )
        
        assert tick.instrument == "EUR_USD"
        assert tick.bid == Decimal("1.1234")
        assert tick.ask == Decimal("1.1236")
        assert tick.spread_pips == Decimal("2.0")
        assert tick.tradeable is True
        assert tick.latency_ms == 50.0
        
    def test_price_tick_to_dict(self):
        """Test converting price tick to dictionary"""
        tick = PriceTick(
            instrument="GBP_JPY",
            bid=Decimal("156.123"),
            ask=Decimal("156.143"),
            spread_pips=Decimal("2.0"),
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            tradeable=True,
            latency_ms=25.5
        )
        
        result = tick.to_dict()
        
        assert result['instrument'] == "GBP_JPY"
        assert result['bid'] == "156.123"
        assert result['ask'] == "156.143"
        assert result['spread_pips'] == "2.0"
        assert result['tradeable'] is True
        assert result['latency_ms'] == 25.5
        assert 'timestamp' in result

class TestHeartbeatMonitor:
    """Test heartbeat monitoring"""
    
    def test_heartbeat_monitor_creation(self):
        """Test creating heartbeat monitor"""
        monitor = HeartbeatMonitor(timeout=30.0)
        assert monitor.timeout == 30.0
        assert monitor.last_heartbeat is None
        assert monitor.is_healthy is True
        
    def test_update_heartbeat(self):
        """Test updating heartbeat"""
        monitor = HeartbeatMonitor()
        monitor.update_heartbeat()
        
        assert monitor.last_heartbeat is not None
        assert monitor.is_healthy is True
        
    def test_health_check_no_heartbeat(self):
        """Test health check with no heartbeat"""
        monitor = HeartbeatMonitor()
        assert monitor.check_health() is True  # No heartbeat received yet
        
    def test_health_check_recent_heartbeat(self):
        """Test health check with recent heartbeat"""
        monitor = HeartbeatMonitor(timeout=30.0)
        monitor.update_heartbeat()
        
        assert monitor.check_health() is True
        
    def test_health_check_timeout(self):
        """Test health check with timeout"""
        monitor = HeartbeatMonitor(timeout=0.1)  # Very short timeout
        monitor.last_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=1)
        
        assert monitor.check_health() is False

class TestSubscriptionManager:
    """Test subscription management"""
    
    @pytest.fixture
    def subscription_manager(self):
        return SubscriptionManager()
        
    @pytest.mark.asyncio
    async def test_add_subscriptions(self, subscription_manager):
        """Test adding subscriptions"""
        instruments = ["EUR_USD", "GBP_USD"]
        new_instruments = await subscription_manager.add_subscriptions(instruments)
        
        assert new_instruments == set(instruments)
        assert subscription_manager.pending_subscriptions == set(instruments)
        
    @pytest.mark.asyncio
    async def test_add_duplicate_subscriptions(self, subscription_manager):
        """Test adding duplicate subscriptions"""
        instruments = ["EUR_USD", "GBP_USD"]
        
        # Add first time
        new1 = await subscription_manager.add_subscriptions(instruments)
        await subscription_manager.confirm_subscriptions(instruments)
        
        # Add again
        new2 = await subscription_manager.add_subscriptions(instruments)
        
        assert new1 == set(instruments)
        assert new2 == set()  # No new instruments
        
    @pytest.mark.asyncio
    async def test_confirm_subscriptions(self, subscription_manager):
        """Test confirming subscriptions"""
        instruments = ["EUR_USD", "GBP_USD"]
        
        await subscription_manager.add_subscriptions(instruments)
        await subscription_manager.confirm_subscriptions(instruments)
        
        assert subscription_manager.active_subscriptions == set(instruments)
        assert subscription_manager.pending_subscriptions == set()
        
    @pytest.mark.asyncio
    async def test_remove_subscriptions(self, subscription_manager):
        """Test removing subscriptions"""
        instruments = ["EUR_USD", "GBP_USD", "USD_JPY"]
        
        # Add and confirm
        await subscription_manager.add_subscriptions(instruments)
        await subscription_manager.confirm_subscriptions(instruments)
        
        # Remove subset
        removed = await subscription_manager.remove_subscriptions(["EUR_USD", "GBP_USD"])
        
        assert removed == {"EUR_USD", "GBP_USD"}
        assert subscription_manager.active_subscriptions == {"USD_JPY"}
        
    def test_price_callbacks(self, subscription_manager):
        """Test price callback management"""
        callback1 = Mock()
        callback2 = Mock()
        
        # Add callbacks
        subscription_manager.add_price_callback("EUR_USD", callback1)
        subscription_manager.add_price_callback("EUR_USD", callback2)
        
        assert len(subscription_manager.subscription_callbacks["EUR_USD"]) == 2
        
        # Remove callback
        subscription_manager.remove_price_callback("EUR_USD", callback1)
        assert len(subscription_manager.subscription_callbacks["EUR_USD"]) == 1
        
    def test_update_price_stats(self, subscription_manager):
        """Test updating price statistics"""
        # Initialize stats
        subscription_manager.subscription_stats["EUR_USD"] = {
            'price_updates': 0,
            'last_update': None,
            'subscribers': 0
        }
        
        subscription_manager.update_price_stats("EUR_USD")
        
        assert subscription_manager.subscription_stats["EUR_USD"]['price_updates'] == 1
        assert subscription_manager.subscription_stats["EUR_USD"]['last_update'] is not None

class TestRateLimiter:
    """Test rate limiting"""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests(self):
        """Test rate limiter allows requests within limit"""
        limiter = RateLimiter(requests_per_second=2)
        
        # Should allow first two requests
        assert await limiter.can_proceed() is True
        assert await limiter.can_proceed() is True
        
        # Should block third request
        assert await limiter.can_proceed() is False
        
    @pytest.mark.asyncio
    async def test_rate_limiter_resets(self):
        """Test rate limiter resets after time window"""
        limiter = RateLimiter(requests_per_second=1)
        
        # Use up the limit
        assert await limiter.can_proceed() is True
        assert await limiter.can_proceed() is False
        
        # Wait and try again
        await asyncio.sleep(1.1)
        assert await limiter.can_proceed() is True

class TestOandaStreamManager:
    """Test OANDA streaming manager"""
    
    @pytest.fixture
    def credential_manager(self):
        """Mock credential manager"""
        mock_manager = Mock(spec=OandaCredentialManager)
        mock_manager.retrieve_credentials = AsyncMock(return_value={
            'api_key': 'test-api-key',
            'account_id': '101-001-12345678-001',
            'environment': 'practice'
        })
        return mock_manager
        
    @pytest.fixture
    def stream_manager(self, credential_manager):
        """Create stream manager with mocked dependencies"""
        return OandaStreamManager(
            credential_manager=credential_manager,
            account_id="101-001-12345678-001",
            environment="practice"
        )
        
    def test_stream_manager_creation(self, stream_manager):
        """Test creating stream manager"""
        assert stream_manager.account_id == "101-001-12345678-001"
        assert stream_manager.environment == "practice"
        assert stream_manager.state == StreamState.DISCONNECTED
        assert stream_manager.is_running is False
        
    def test_build_stream_url(self, stream_manager):
        """Test building stream URL"""
        expected_url = "wss://stream-fxpractice.oanda.com/v3/accounts/101-001-12345678-001/pricing/stream"
        assert stream_manager.connection_url == expected_url
        
    def test_calculate_spread_pips_standard(self, stream_manager):
        """Test calculating spread in pips for standard pairs"""
        bid = Decimal("1.1234")
        ask = Decimal("1.1236")
        
        spread_pips = stream_manager._calculate_spread_pips("EUR_USD", bid, ask)
        assert spread_pips == Decimal("2.0")
        
    def test_calculate_spread_pips_jpy(self, stream_manager):
        """Test calculating spread in pips for JPY pairs"""
        bid = Decimal("156.12")
        ask = Decimal("156.14")
        
        spread_pips = stream_manager._calculate_spread_pips("USD_JPY", bid, ask)
        assert spread_pips == Decimal("2.0")
        
    def test_calculate_latency(self, stream_manager):
        """Test calculating latency"""
        # Create timestamp 100ms ago
        oanda_time = datetime.now(timezone.utc) - timedelta(milliseconds=100)
        
        latency = stream_manager._calculate_latency(oanda_time)
        
        # Should be approximately 100ms (allow some variance)
        assert 90 <= latency <= 110
        
    def test_calculate_latency_negative(self, stream_manager):
        """Test latency calculation with future timestamp"""
        # Future timestamp
        oanda_time = datetime.now(timezone.utc) + timedelta(milliseconds=100)
        
        latency = stream_manager._calculate_latency(oanda_time)
        
        # Should be 0 (no negative latency)
        assert latency == 0
        
    @pytest.mark.asyncio
    async def test_subscribe_when_disconnected(self, stream_manager):
        """Test subscribing when disconnected"""
        instruments = ["EUR_USD", "GBP_USD"]
        
        result = await stream_manager.subscribe(instruments)
        
        assert result is True
        assert stream_manager.subscription_manager.pending_subscriptions == set(instruments)
        
    @pytest.mark.asyncio
    async def test_unsubscribe(self, stream_manager):
        """Test unsubscribing from instruments"""
        instruments = ["EUR_USD", "GBP_USD", "USD_JPY"]
        
        # Subscribe first
        await stream_manager.subscribe(instruments)
        await stream_manager.subscription_manager.confirm_subscriptions(instruments)
        
        # Unsubscribe subset
        result = await stream_manager.unsubscribe(["EUR_USD", "GBP_USD"])
        
        assert result is True
        assert stream_manager.subscription_manager.active_subscriptions == {"USD_JPY"}
        
    def test_price_callback_management(self, stream_manager):
        """Test adding/removing price callbacks"""
        callback1 = Mock()
        callback2 = Mock()
        
        # Add callbacks
        stream_manager.add_price_callback(callback1)
        stream_manager.add_price_callback(callback2)
        
        assert len(stream_manager.price_callbacks) == 2
        
        # Remove callback
        stream_manager.remove_price_callback(callback1)
        assert len(stream_manager.price_callbacks) == 1
        
    def test_market_status_callback_management(self, stream_manager):
        """Test market status callback management"""
        callback = Mock()
        
        stream_manager.add_market_status_callback(callback)
        assert len(stream_manager.market_status_callbacks) == 1
        
    @pytest.mark.asyncio
    async def test_process_price_update(self, stream_manager):
        """Test processing price update message"""
        # Mock callback
        price_callback = AsyncMock()
        stream_manager.add_price_callback(price_callback)
        
        # Sample price data
        price_data = {
            "type": "PRICE",
            "instrument": "EUR_USD",
            "time": "2024-01-01T12:00:00.000000Z",
            "closeoutBid": "1.1234",
            "closeoutAsk": "1.1236",
            "tradeable": True
        }
        
        await stream_manager._process_price_update(price_data)
        
        # Verify callback was called
        price_callback.assert_called_once()
        
        # Verify price tick was created correctly
        price_tick = price_callback.call_args[0][0]
        assert isinstance(price_tick, PriceTick)
        assert price_tick.instrument == "EUR_USD"
        assert price_tick.bid == Decimal("1.1234")
        assert price_tick.ask == Decimal("1.1236")
        assert price_tick.tradeable is True
        
    @pytest.mark.asyncio
    async def test_process_heartbeat(self, stream_manager):
        """Test processing heartbeat message"""
        heartbeat_data = {
            "type": "HEARTBEAT",
            "time": "2024-01-01T12:00:00.000000Z"
        }
        
        initial_heartbeats = stream_manager.metrics.heartbeats_received
        
        await stream_manager._process_heartbeat(heartbeat_data)
        
        assert stream_manager.metrics.heartbeats_received == initial_heartbeats + 1
        assert stream_manager.heartbeat_monitor.last_heartbeat is not None
        
    def test_get_metrics(self, stream_manager):
        """Test getting stream metrics"""
        # Add some test data
        stream_manager.subscription_manager.active_subscriptions.add("EUR_USD")
        stream_manager.subscription_manager.pending_subscriptions.add("GBP_USD")
        stream_manager.metrics.messages_received = 100
        stream_manager.metrics.errors = 2
        
        metrics = stream_manager.get_metrics()
        
        assert metrics['state'] == StreamState.DISCONNECTED.value
        assert metrics['subscriptions']['active'] == 1
        assert metrics['subscriptions']['pending'] == 1
        assert metrics['metrics']['messages_received'] == 100
        assert metrics['metrics']['errors'] == 2
        
    def test_get_price_history(self, stream_manager):
        """Test getting price history"""
        # Add some price history
        tick1 = PriceTick("EUR_USD", Decimal("1.1234"), Decimal("1.1236"), 
                         Decimal("2.0"), datetime.now(timezone.utc), True, 50.0)
        tick2 = PriceTick("EUR_USD", Decimal("1.1235"), Decimal("1.1237"), 
                         Decimal("2.0"), datetime.now(timezone.utc), True, 45.0)
        
        stream_manager.price_history["EUR_USD"].extend([tick1, tick2])
        
        history = stream_manager.get_price_history("EUR_USD")
        
        assert len(history) == 2
        assert all(isinstance(h, dict) for h in history)
        
    def test_get_price_history_limit(self, stream_manager):
        """Test getting price history with limit"""
        # Add multiple ticks
        for i in range(15):
            tick = PriceTick("EUR_USD", Decimal("1.1234"), Decimal("1.1236"), 
                           Decimal("2.0"), datetime.now(timezone.utc), True, 50.0)
            stream_manager.price_history["EUR_USD"].append(tick)
            
        history = stream_manager.get_price_history("EUR_USD", limit=5)
        
        assert len(history) == 5

@pytest.mark.asyncio
async def test_integration_subscription_flow():
    """Test complete subscription flow"""
    # Mock credential manager
    credential_manager = Mock(spec=OandaCredentialManager)
    credential_manager.retrieve_credentials = AsyncMock(return_value={
        'api_key': 'test-key',
        'account_id': 'test-account',
        'environment': 'practice'
    })
    
    # Create stream manager
    stream_manager = OandaStreamManager(
        credential_manager=credential_manager,
        account_id="test-account",
        environment="practice"
    )
    
    # Test subscription when disconnected
    instruments = ["EUR_USD", "GBP_USD"]
    result = await stream_manager.subscribe(instruments)
    
    assert result is True
    assert len(stream_manager.subscription_manager.pending_subscriptions) == 2
    
    # Confirm subscriptions
    await stream_manager.subscription_manager.confirm_subscriptions(instruments)
    assert len(stream_manager.subscription_manager.active_subscriptions) == 2
    
    # Test unsubscription
    result = await stream_manager.unsubscribe(["EUR_USD"])
    assert result is True
    assert stream_manager.subscription_manager.active_subscriptions == {"GBP_USD"}

if __name__ == "__main__":
    pytest.main([__file__])