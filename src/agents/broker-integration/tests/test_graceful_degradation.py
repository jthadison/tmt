"""
Tests for Graceful Degradation System
Story 8.9 - Task 6: Test graceful degradation system
"""
import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from graceful_degradation import (
    GracefulDegradationManager, DegradationLevel, ServiceHealth,
    CacheManager, graceful_degradation_protected,
    get_global_degradation_manager
)


class TestCacheManager:
    """Test cache manager functionality"""
    
    @pytest.fixture
    def cache_manager(self):
        """Create cache manager for testing"""
        return CacheManager(default_ttl=10)  # 10 second TTL
        
    def test_set_and_get_cache(self, cache_manager):
        """Test basic cache set and get operations"""
        cache_manager.set("test_key", "test_value")
        
        result = cache_manager.get("test_key")
        assert result == "test_value"
        
    def test_cache_miss(self, cache_manager):
        """Test cache miss for non-existent key"""
        result = cache_manager.get("nonexistent_key")
        assert result is None
        assert cache_manager.miss_count == 1
        
    def test_cache_hit_tracking(self, cache_manager):
        """Test cache hit/miss tracking"""
        cache_manager.set("test_key", "test_value")
        
        # Hit
        result = cache_manager.get("test_key")
        assert result == "test_value"
        assert cache_manager.hit_count == 1
        
        # Miss
        cache_manager.get("missing_key")
        assert cache_manager.miss_count == 1
        
    def test_cache_expiration(self, cache_manager):
        """Test cache TTL expiration"""
        cache_manager.set("test_key", "test_value", ttl=0.1)  # 100ms TTL
        
        # Should be available immediately
        result = cache_manager.get("test_key")
        assert result == "test_value"
        
        # Wait for expiration
        time.sleep(0.15)
        
        # Should be expired
        result = cache_manager.get("test_key")
        assert result is None
        
    def test_custom_ttl(self, cache_manager):
        """Test setting custom TTL for cache entries"""
        cache_manager.set("short_ttl", "value", ttl=1)
        cache_manager.set("long_ttl", "value", ttl=100)
        
        # Both should be available initially
        assert cache_manager.get("short_ttl") == "value"
        assert cache_manager.get("long_ttl") == "value"
        
    def test_cache_delete(self, cache_manager):
        """Test cache deletion"""
        cache_manager.set("test_key", "test_value")
        
        cache_manager.delete("test_key")
        
        result = cache_manager.get("test_key")
        assert result is None
        
    def test_cache_clear(self, cache_manager):
        """Test clearing all cache entries"""
        cache_manager.set("key1", "value1")
        cache_manager.set("key2", "value2")
        
        cache_manager.clear()
        
        assert cache_manager.get("key1") is None
        assert cache_manager.get("key2") is None
        assert cache_manager.hit_count == 0
        assert cache_manager.miss_count == 0
        
    def test_cache_stats(self, cache_manager):
        """Test cache statistics"""
        cache_manager.set("key1", "value1")
        cache_manager.set("key2", "value2")
        
        cache_manager.get("key1")  # Hit
        cache_manager.get("key1")  # Hit
        cache_manager.get("missing")  # Miss
        
        stats = cache_manager.get_cache_stats()
        
        assert stats['total_entries'] == 2
        assert stats['hit_count'] == 2
        assert stats['miss_count'] == 1
        assert stats['hit_rate'] == (2 / 3 * 100)


class TestGracefulDegradationManager:
    """Test graceful degradation manager functionality"""
    
    @pytest.fixture
    def degradation_manager(self):
        """Create degradation manager for testing"""
        manager = GracefulDegradationManager()
        manager.auto_recovery_enabled = False  # Disable for testing
        return manager
        
    def test_initial_state(self, degradation_manager):
        """Test initial manager state"""
        assert degradation_manager.current_level == DegradationLevel.NONE
        assert len(degradation_manager.service_statuses) > 0
        
    @pytest.mark.asyncio
    async def test_handle_connection_error(self, degradation_manager):
        """Test handling connection errors"""
        error = ConnectionError("Connection failed")
        
        result = await degradation_manager.handle_api_failure("oanda_api", error)
        
        assert result == DegradationLevel.READ_ONLY
        assert degradation_manager.current_level == DegradationLevel.READ_ONLY
        
    @pytest.mark.asyncio
    async def test_handle_rate_limit_error(self, degradation_manager):
        """Test handling rate limit errors"""
        error = Exception("Rate limit exceeded")
        
        result = await degradation_manager.handle_api_failure("oanda_api", error)
        
        assert result == DegradationLevel.RATE_LIMITED
        assert degradation_manager.current_level == DegradationLevel.RATE_LIMITED
        
    @pytest.mark.asyncio
    async def test_handle_authentication_error(self, degradation_manager):
        """Test handling authentication errors"""
        error = Exception("Authentication failed")
        
        result = await degradation_manager.handle_api_failure("oanda_api", error)
        
        assert result == DegradationLevel.EMERGENCY
        assert degradation_manager.current_level == DegradationLevel.EMERGENCY
        
    @pytest.mark.asyncio
    async def test_suggested_degradation_level(self, degradation_manager):
        """Test using suggested degradation level"""
        error = Exception("Some error")
        
        result = await degradation_manager.handle_api_failure(
            "oanda_api", error, suggested_level=DegradationLevel.CACHED_DATA
        )
        
        assert result == DegradationLevel.CACHED_DATA
        assert degradation_manager.current_level == DegradationLevel.CACHED_DATA
        
    @pytest.mark.asyncio
    async def test_degradation_level_escalation(self, degradation_manager):
        """Test that degradation only escalates, not de-escalates"""
        # Start with cached data level
        await degradation_manager._transition_to_degradation_level(
            DegradationLevel.CACHED_DATA, "Test"
        )
        
        # Try to apply a lower degradation level
        error = Exception("Rate limit exceeded")  # Would normally cause RATE_LIMITED
        result = await degradation_manager.handle_api_failure("oanda_api", error)
        
        # Should stay at CACHED_DATA (higher level)
        assert degradation_manager.current_level == DegradationLevel.CACHED_DATA
        
    @pytest.mark.asyncio
    async def test_cache_data_and_retrieval(self, degradation_manager):
        """Test caching and retrieving data"""
        test_data = {"price": 1.2345, "timestamp": "2023-01-01T12:00:00Z"}
        
        await degradation_manager.cache_data("pricing", "EUR_USD", test_data)
        
        retrieved_data = await degradation_manager.get_cached_data("pricing", "EUR_USD")
        assert retrieved_data == test_data
        
    @pytest.mark.asyncio
    async def test_cache_miss_returns_default(self, degradation_manager):
        """Test cache miss returns default value"""
        default_value = {"error": "no data"}
        
        result = await degradation_manager.get_cached_data(
            "pricing", "missing_pair", default=default_value
        )
        
        assert result == default_value
        
    def test_operation_allowed_normal_mode(self, degradation_manager):
        """Test operation permissions in normal mode"""
        assert degradation_manager.is_operation_allowed("get_account")
        assert degradation_manager.is_operation_allowed("place_order")
        assert degradation_manager.is_operation_allowed("get_prices")
        
    @pytest.mark.asyncio
    async def test_operation_allowed_rate_limited_mode(self, degradation_manager):
        """Test operation permissions in rate limited mode"""
        await degradation_manager._transition_to_degradation_level(
            DegradationLevel.RATE_LIMITED, "Test"
        )
        
        # All operations should be allowed but rate limited
        assert degradation_manager.is_operation_allowed("get_account")
        assert degradation_manager.is_operation_allowed("place_order")
        
    @pytest.mark.asyncio
    async def test_operation_allowed_cached_data_mode(self, degradation_manager):
        """Test operation permissions in cached data mode"""
        await degradation_manager._transition_to_degradation_level(
            DegradationLevel.CACHED_DATA, "Test"
        )
        
        # Only read operations allowed
        assert degradation_manager.is_operation_allowed("get_account")
        assert degradation_manager.is_operation_allowed("get_prices")
        assert not degradation_manager.is_operation_allowed("place_order")
        
    @pytest.mark.asyncio
    async def test_operation_allowed_read_only_mode(self, degradation_manager):
        """Test operation permissions in read-only mode"""
        await degradation_manager._transition_to_degradation_level(
            DegradationLevel.READ_ONLY, "Test"
        )
        
        # Only specific read operations allowed
        assert degradation_manager.is_operation_allowed("get_account")
        assert degradation_manager.is_operation_allowed("get_prices")
        assert not degradation_manager.is_operation_allowed("get_transactions")
        assert not degradation_manager.is_operation_allowed("place_order")
        
    @pytest.mark.asyncio
    async def test_operation_allowed_emergency_mode(self, degradation_manager):
        """Test operation permissions in emergency mode"""
        await degradation_manager._transition_to_degradation_level(
            DegradationLevel.EMERGENCY, "Test"
        )
        
        # Only critical operations allowed
        assert degradation_manager.is_operation_allowed("emergency_close")
        assert degradation_manager.is_operation_allowed("risk_check")
        assert not degradation_manager.is_operation_allowed("get_account")
        assert not degradation_manager.is_operation_allowed("place_order")
        
    @pytest.mark.asyncio
    async def test_execute_with_fallback_success(self, degradation_manager):
        """Test successful execution with fallback"""
        mock_func = AsyncMock(return_value="success")
        
        result = await degradation_manager.execute_with_fallback(
            "get_account", mock_func, "arg1", kwarg1="value1"
        )
        
        assert result == "success"
        mock_func.assert_called_with("arg1", kwarg1="value1")
        
    @pytest.mark.asyncio
    async def test_execute_with_fallback_function(self, degradation_manager):
        """Test execution with fallback function"""
        mock_primary = AsyncMock(side_effect=Exception("Primary failed"))
        mock_fallback = AsyncMock(return_value="fallback_success")
        
        result = await degradation_manager.execute_with_fallback(
            "get_account", mock_primary, mock_fallback
        )
        
        assert result == "fallback_success"
        mock_primary.assert_called_once()
        mock_fallback.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_execute_with_cached_fallback(self, degradation_manager):
        """Test execution with cached data fallback"""
        # Cache some data first
        cached_data = {"cached": "result"}
        await degradation_manager.cache_data("api", "test_cache", cached_data)
        
        mock_primary = AsyncMock(side_effect=Exception("Primary failed"))
        
        result = await degradation_manager.execute_with_fallback(
            "get_account", mock_primary, cache_key="test_cache"
        )
        
        assert result == cached_data
        
    @pytest.mark.asyncio
    async def test_execute_with_disallowed_operation(self, degradation_manager):
        """Test execution of disallowed operation"""
        await degradation_manager._transition_to_degradation_level(
            DegradationLevel.EMERGENCY, "Test"
        )
        
        mock_func = AsyncMock(return_value="success")
        
        with pytest.raises(Exception, match="not allowed in degradation level"):
            await degradation_manager.execute_with_fallback(
                "place_order", mock_func
            )
            
        mock_func.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_manual_recovery(self, degradation_manager):
        """Test manual recovery to normal operation"""
        # Set to degraded state
        await degradation_manager._transition_to_degradation_level(
            DegradationLevel.READ_ONLY, "Test"
        )
        
        result = await degradation_manager.manual_recovery("Manual test")
        
        assert result is True
        assert degradation_manager.current_level == DegradationLevel.NONE
        
    @pytest.mark.asyncio
    async def test_automatic_recovery_attempt(self, degradation_manager):
        """Test automatic recovery attempt"""
        # Set to degraded state
        await degradation_manager._transition_to_degradation_level(
            DegradationLevel.READ_ONLY, "Test"
        )
        
        # Mock healthy services
        with patch.object(degradation_manager, '_check_service_health', return_value=True):
            result = await degradation_manager.attempt_recovery()
            
        assert result is True
        assert degradation_manager.current_level == DegradationLevel.NONE
        
    @pytest.mark.asyncio
    async def test_partial_recovery(self, degradation_manager):
        """Test partial recovery when some services are healthy"""
        # Set to emergency state
        await degradation_manager._transition_to_degradation_level(
            DegradationLevel.EMERGENCY, "Test"
        )
        
        # Mock partial service health (60% healthy)
        healthy_count = 0
        async def mock_health_check(service_name):
            nonlocal healthy_count
            healthy_count += 1
            return healthy_count <= 4  # First 4 services healthy, last 2 not
            
        with patch.object(degradation_manager, '_check_service_health', side_effect=mock_health_check):
            result = await degradation_manager.attempt_recovery()
            
        assert result is True
        assert degradation_manager.current_level == DegradationLevel.CACHED_DATA
        
    @pytest.mark.asyncio
    async def test_failed_recovery_attempt(self, degradation_manager):
        """Test failed recovery attempt"""
        # Set to degraded state
        await degradation_manager._transition_to_degradation_level(
            DegradationLevel.READ_ONLY, "Test"
        )
        
        # Mock unhealthy services
        with patch.object(degradation_manager, '_check_service_health', return_value=False):
            result = await degradation_manager.attempt_recovery()
            
        assert result is False
        assert degradation_manager.current_level == DegradationLevel.READ_ONLY
        
    def test_get_system_status(self, degradation_manager):
        """Test system status reporting"""
        status = degradation_manager.get_system_status()
        
        assert 'degradation_level' in status
        assert 'healthy_services' in status
        assert 'total_services' in status
        assert 'cache_stats' in status
        assert status['degradation_level'] == DegradationLevel.NONE.value
        
    def test_get_service_statuses(self, degradation_manager):
        """Test service status reporting"""
        statuses = degradation_manager.get_service_statuses()
        
        assert len(statuses) > 0
        assert 'oanda_api' in statuses
        assert 'pricing_stream' in statuses
        
        for service_status in statuses.values():
            assert 'service_name' in service_status
            assert 'health' in service_status
            assert 'degradation_level' in service_status
            
    @pytest.mark.asyncio
    async def test_update_service_health(self, degradation_manager):
        """Test updating service health status"""
        await degradation_manager.update_service_health(
            "test_service", ServiceHealth.DEGRADED, "Test error"
        )
        
        statuses = degradation_manager.get_service_statuses()
        assert "test_service" in statuses
        assert statuses["test_service"]["health"] == ServiceHealth.DEGRADED.value
        assert statuses["test_service"]["last_error"] == "Test error"
        
    @pytest.mark.asyncio
    async def test_degradation_callbacks(self, degradation_manager):
        """Test degradation event callbacks"""
        callback_events = []
        
        async def test_callback(event):
            callback_events.append(event)
            
        degradation_manager.add_degradation_callback(test_callback)
        
        await degradation_manager._transition_to_degradation_level(
            DegradationLevel.CACHED_DATA, "Test callback"
        )
        
        assert len(callback_events) == 1
        assert callback_events[0].new_level == DegradationLevel.CACHED_DATA
        
    @pytest.mark.asyncio
    async def test_degradation_timeout_configuration(self, degradation_manager):
        """Test degradation timeout configuration"""
        # Check default timeouts are reasonable
        assert degradation_manager.degradation_timeouts[DegradationLevel.RATE_LIMITED] == 300
        assert degradation_manager.degradation_timeouts[DegradationLevel.CACHED_DATA] == 900
        assert degradation_manager.degradation_timeouts[DegradationLevel.READ_ONLY] == 1800
        assert degradation_manager.degradation_timeouts[DegradationLevel.EMERGENCY] == 3600


class TestGracefulDegradationDecorator:
    """Test graceful degradation decorator"""
    
    @pytest.mark.asyncio
    async def test_decorator_success(self):
        """Test successful decorated function"""
        @graceful_degradation_protected("get_data", cache_key="test_data")
        async def test_func(self, value):
            return f"result: {value}"
            
        # Create mock self object
        mock_self = MagicMock()
        
        result = await test_func(mock_self, "test")
        assert result == "result: test"
        
    @pytest.mark.asyncio
    async def test_decorator_with_degradation(self):
        """Test decorator with graceful degradation"""
        call_count = 0
        
        @graceful_degradation_protected("get_data", cache_key="test_data")
        async def test_func(self):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First call fails")
            return "success"
            
        mock_self = MagicMock()
        
        # Should succeed on retry
        result = await test_func(mock_self)
        assert result == "success"
        assert call_count == 2


class TestGlobalDegradationManager:
    """Test global degradation manager"""
    
    def test_get_global_manager(self):
        """Test getting global manager instance"""
        manager1 = get_global_degradation_manager()
        manager2 = get_global_degradation_manager()
        
        assert manager1 is manager2  # Same instance
        assert isinstance(manager1, GracefulDegradationManager)


class TestIntegration:
    """Test integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_full_degradation_and_recovery_cycle(self):
        """Test complete degradation and recovery cycle"""
        manager = GracefulDegradationManager()
        manager.auto_recovery_enabled = False
        
        # Start normal
        assert manager.current_level == DegradationLevel.NONE
        
        # Trigger degradation
        error = ConnectionError("Connection failed")
        await manager.handle_api_failure("oanda_api", error)
        assert manager.current_level == DegradationLevel.READ_ONLY
        
        # Cache some data during degradation
        await manager.cache_data("api", "cached_prices", {"EUR_USD": 1.2345})
        
        # Test operation restrictions
        assert not manager.is_operation_allowed("place_order")
        assert manager.is_operation_allowed("get_prices")
        
        # Recover manually
        await manager.manual_recovery("Manual recovery test")
        assert manager.current_level == DegradationLevel.NONE
        
        # All operations should be allowed again
        assert manager.is_operation_allowed("place_order")
        
    @pytest.mark.asyncio
    async def test_cache_ttl_adjustment_during_degradation(self):
        """Test that cache TTL adjusts during degradation"""
        manager = GracefulDegradationManager()
        
        # Initial TTL
        initial_ttl = manager.cache_manager.default_ttl
        
        # Trigger degradation
        await manager._transition_to_degradation_level(
            DegradationLevel.CACHED_DATA, "Test"
        )
        
        # TTL should be increased
        assert manager.cache_manager.default_ttl > initial_ttl
        
    @pytest.mark.asyncio
    async def test_service_health_tracking_during_failures(self):
        """Test service health tracking during failures"""
        manager = GracefulDegradationManager()
        
        # Initial service health should be unknown
        status = manager.service_statuses["oanda_api"]
        assert status.health == ServiceHealth.UNKNOWN
        assert status.error_count == 0
        
        # Simulate failure
        error = Exception("Service failure")
        await manager.handle_api_failure("oanda_api", error)
        
        # Service should be marked as unavailable
        status = manager.service_statuses["oanda_api"]
        assert status.health == ServiceHealth.UNAVAILABLE
        assert status.error_count == 1
        assert status.last_error == "Service failure"


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.mark.asyncio
    async def test_callback_exception_handling(self):
        """Test that callback exceptions don't break degradation"""
        manager = GracefulDegradationManager()
        
        async def failing_callback(event):
            raise Exception("Callback error")
            
        manager.add_degradation_callback(failing_callback)
        
        # Should still work despite callback failure
        await manager._transition_to_degradation_level(
            DegradationLevel.CACHED_DATA, "Test"
        )
        
        assert manager.current_level == DegradationLevel.CACHED_DATA
        
    @pytest.mark.asyncio
    async def test_unknown_service_health_check(self):
        """Test health check for unknown service"""
        manager = GracefulDegradationManager()
        
        # Should handle gracefully
        result = await manager._check_service_health("unknown_service")
        assert isinstance(result, bool)
        
    def test_empty_service_list(self):
        """Test manager with no services"""
        manager = GracefulDegradationManager()
        manager.service_statuses.clear()
        
        status = manager.get_system_status()
        assert status["total_services"] == 0
        assert status["health_percentage"] == 0
        
    @pytest.mark.asyncio
    async def test_very_large_cache_data(self):
        """Test caching very large data"""
        manager = GracefulDegradationManager()
        
        # Create large data object
        large_data = {"data": "x" * 10000}  # 10KB string
        
        await manager.cache_data("test", "large_data", large_data)
        
        retrieved = await manager.get_cached_data("test", "large_data")
        assert retrieved == large_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])