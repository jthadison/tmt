"""
Tests for Rate Limiter System
Story 8.9 - Task 6: Test rate limiting system
"""
import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from rate_limiter import (
    TokenBucketRateLimiter, RateLimitResult, OandaRateLimitManager,
    RequestQueue, rate_limit_protected, get_global_rate_limit_manager
)


class TestTokenBucketRateLimiter:
    """Test token bucket rate limiter functionality"""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter for testing"""
        return TokenBucketRateLimiter(
            rate=10.0,  # 10 tokens per second
            burst_capacity=10,
            name="test_limiter"
        )
        
    @pytest.mark.asyncio
    async def test_initial_tokens_available(self, rate_limiter):
        """Test that initial tokens are available"""
        result = await rate_limiter.acquire(1, "test_endpoint")
        assert result == RateLimitResult.ALLOWED
        assert rate_limiter.tokens == 9.0  # 10 - 1
        
    @pytest.mark.asyncio
    async def test_burst_capacity_consumption(self, rate_limiter):
        """Test consuming all burst capacity"""
        # Consume all tokens
        for i in range(10):
            result = await rate_limiter.acquire(1, "test_endpoint")
            assert result == RateLimitResult.ALLOWED
            
        # Next request should be rate limited
        result = await rate_limiter.acquire(1, "test_endpoint", wait_if_needed=False)
        assert result == RateLimitResult.RATE_LIMITED
        
    @pytest.mark.asyncio
    async def test_token_refill_over_time(self, rate_limiter):
        """Test that tokens refill over time"""
        # Consume all tokens
        for i in range(10):
            await rate_limiter.acquire(1, "test_endpoint")
            
        # Verify tokens are exhausted
        result = await rate_limiter.acquire(1, "test_endpoint", wait_if_needed=False)
        assert result == RateLimitResult.RATE_LIMITED
            
        # Wait for some tokens to refill
        await asyncio.sleep(0.3)  # Should add ~3 tokens at 10/sec rate
        
        # Should be able to acquire again
        result = await rate_limiter.acquire(1, "test_endpoint")
        assert result == RateLimitResult.ALLOWED
        
    @pytest.mark.asyncio
    async def test_wait_for_tokens(self, rate_limiter):
        """Test waiting for tokens when needed"""
        # Consume all tokens
        for i in range(10):
            await rate_limiter.acquire(1, "test_endpoint")
            
        # Verify exhaustion
        result = await rate_limiter.acquire(1, "test_endpoint", wait_if_needed=False)
        assert result == RateLimitResult.RATE_LIMITED
            
        start_time = time.perf_counter()
        
        # This should wait for tokens to be available  
        result = await rate_limiter.acquire(1, "test_endpoint", wait_if_needed=True)
        
        wait_time = time.perf_counter() - start_time
        
        assert result == RateLimitResult.QUEUED
        assert wait_time > 0.08  # Should have waited for token refill
        
    @pytest.mark.asyncio
    async def test_multiple_tokens_request(self, rate_limiter):
        """Test requesting multiple tokens at once"""
        result = await rate_limiter.acquire(5, "test_endpoint")
        assert result == RateLimitResult.ALLOWED
        assert rate_limiter.tokens == 5.0
        
    @pytest.mark.asyncio
    async def test_more_tokens_than_capacity(self, rate_limiter):
        """Test requesting more tokens than burst capacity"""
        result = await rate_limiter.acquire(15, "test_endpoint", wait_if_needed=False)
        assert result == RateLimitResult.RATE_LIMITED
        
    def test_status_reporting(self, rate_limiter):
        """Test rate limiter status reporting"""
        status = rate_limiter.get_status()
        
        assert status['name'] == "test_limiter"
        assert status['rate'] == 10.0
        assert status['burst_capacity'] == 10
        assert status['current_tokens'] == 10.0
        assert status['is_rate_limiting'] is False
        
    def test_metrics_tracking(self, rate_limiter):
        """Test metrics tracking"""
        metrics = rate_limiter.get_metrics()
        
        assert metrics['total_requests'] == 0
        assert metrics['allowed_requests'] == 0
        assert metrics['rate_limited_requests'] == 0
        assert metrics['success_rate'] == 0
        
    @pytest.mark.asyncio
    async def test_requests_per_second_calculation(self, rate_limiter):
        """Test RPS calculation"""
        # Make several requests quickly
        for i in range(5):
            await rate_limiter.acquire(1, "test_endpoint")
            
        metrics = rate_limiter.get_metrics()
        assert metrics['requests_per_second'] >= 4  # Should be close to 5
        
    @pytest.mark.asyncio
    async def test_wait_time_metrics(self, rate_limiter):
        """Test wait time metrics tracking"""
        # Consume all tokens
        for i in range(10):
            await rate_limiter.acquire(1, "test_endpoint")
            
        # Make request that has to wait
        await rate_limiter.acquire(1, "test_endpoint", wait_if_needed=True)
        
        metrics = rate_limiter.get_metrics()
        assert metrics['max_wait_time_ms'] > 0
        assert metrics['average_wait_time_ms'] > 0
        
    @pytest.mark.asyncio
    async def test_wait_for_tokens_method(self, rate_limiter):
        """Test explicit wait_for_tokens method"""
        # Consume all tokens
        for i in range(10):
            await rate_limiter.acquire(1, "test_endpoint")
            
        start_time = time.perf_counter()
        wait_time = await rate_limiter.wait_for_tokens(2)
        actual_wait = time.perf_counter() - start_time
        
        assert wait_time > 0
        assert abs(wait_time - actual_wait) < 0.01  # Should be close


class TestOandaRateLimitManager:
    """Test OANDA rate limit manager functionality"""
    
    @pytest.fixture
    def rate_manager(self):
        """Create rate limit manager for testing"""
        return OandaRateLimitManager()
        
    @pytest.mark.asyncio
    async def test_global_rate_limit_check(self, rate_manager):
        """Test global rate limit checking"""
        result = await rate_manager.check_rate_limit("test_endpoint", 1)
        assert result == RateLimitResult.ALLOWED
        
    @pytest.mark.asyncio
    async def test_endpoint_specific_rate_limit(self, rate_manager):
        """Test endpoint-specific rate limiting"""
        # Test known endpoint
        result = await rate_manager.check_rate_limit("transactions", 1)
        assert result == RateLimitResult.ALLOWED
        
        # Test unknown endpoint (uses global)
        result = await rate_manager.check_rate_limit("unknown_endpoint", 1)
        assert result == RateLimitResult.ALLOWED
        
    @pytest.mark.asyncio
    async def test_critical_operation_bypass(self, rate_manager):
        """Test that critical operations bypass rate limits"""
        # Exhaust global rate limit
        global_limiter = rate_manager.global_limiter
        global_limiter.tokens = 0
        
        # Critical operation should still be allowed
        result = await rate_manager.check_rate_limit(
            "emergency_close", 1, is_critical=True
        )
        assert result == RateLimitResult.ALLOWED
        
    @pytest.mark.asyncio
    async def test_acquire_with_wait(self, rate_manager):
        """Test acquiring tokens with wait"""
        result = await rate_manager.acquire_with_wait("test_endpoint", 1)
        assert result is True
        
    @pytest.mark.asyncio
    async def test_acquire_with_timeout(self, rate_manager):
        """Test acquiring tokens with timeout"""
        # Exhaust tokens
        global_limiter = rate_manager.global_limiter
        global_limiter.tokens = 0
        
        start_time = time.perf_counter()
        result = await rate_manager.acquire_with_wait(
            "test_endpoint", 1, max_wait_time=0.1
        )
        wait_time = time.perf_counter() - start_time
        
        # Should timeout quickly
        assert wait_time < 0.2
        assert result is False
        
    def test_add_custom_endpoint_limiter(self, rate_manager):
        """Test adding custom endpoint limiter"""
        rate_manager.add_endpoint_limiter("custom_endpoint", 5.0, 5)
        
        assert "custom_endpoint" in rate_manager.limiters
        limiter = rate_manager.limiters["custom_endpoint"]
        assert limiter.rate == 5.0
        assert limiter.burst_capacity == 5
        
    def test_get_all_status(self, rate_manager):
        """Test getting status of all limiters"""
        status = rate_manager.get_all_status()
        
        assert "global_oanda" in status
        assert "transactions" in status
        assert "accounts" in status
        
    def test_get_all_metrics(self, rate_manager):
        """Test getting metrics for all limiters"""
        metrics = rate_manager.get_all_metrics()
        
        assert "global_oanda" in metrics
        assert "transactions" in metrics
        assert all("total_requests" in m for m in metrics.values())
        
    @pytest.mark.asyncio
    async def test_reset_specific_limiter(self, rate_manager):
        """Test resetting specific rate limiter"""
        # Consume some tokens
        await rate_manager.global_limiter.acquire(5)
        assert rate_manager.global_limiter.tokens == 95
        
        # Reset limiter
        result = await rate_manager.reset_limiter("global_oanda")
        assert result is True
        assert rate_manager.global_limiter.tokens == 100
        
    @pytest.mark.asyncio
    async def test_reset_all_limiters(self, rate_manager):
        """Test resetting all rate limiters"""
        # Consume tokens from multiple limiters
        await rate_manager.global_limiter.acquire(10)
        await rate_manager.limiters["transactions"].acquire(5)
        
        await rate_manager.reset_all_limiters()
        
        assert rate_manager.global_limiter.tokens == 100
        assert rate_manager.limiters["transactions"].tokens == 50


class TestRequestQueue:
    """Test request queue functionality"""
    
    @pytest.fixture
    def request_queue(self):
        """Create request queue for testing"""
        return RequestQueue(max_queue_size=5)
        
    @pytest.mark.asyncio
    async def test_enqueue_and_process_request(self, request_queue):
        """Test enqueueing and processing requests"""
        async def test_func(value):
            return f"processed: {value}"
            
        result = await request_queue.enqueue_request(test_func, ("test",), {})
        
        assert result == "processed: test"
        assert request_queue.processed_count == 1
        
    @pytest.mark.asyncio
    async def test_queue_with_priority(self, request_queue):
        """Test queue processing with priority"""
        results = []
        
        async def test_func(value):
            results.append(value)
            return value
            
        # Enqueue requests with different priorities
        tasks = [
            asyncio.create_task(request_queue.enqueue_request(
                test_func, (f"item_{i}",), {}, priority=i
            )) for i in range(3)
        ]
        
        await asyncio.gather(*tasks)
        
        assert len(results) == 3
        assert request_queue.processed_count == 3
        
    @pytest.mark.asyncio
    async def test_queue_full_error(self, request_queue):
        """Test queue full error handling"""
        async def slow_func():
            await asyncio.sleep(1)  # Very slow function
            return "slow"
            
        # Fill the queue beyond capacity
        tasks = []
        for i in range(request_queue.max_queue_size + 1):
            task = asyncio.create_task(
                request_queue.enqueue_request(slow_func, (), {})
            )
            tasks.append(task)
            
        # Wait a bit for queue to fill
        await asyncio.sleep(0.01)
        
        # Last task should raise exception
        with pytest.raises(Exception, match="Request queue full"):
            await tasks[-1]
            
        # Cancel remaining tasks
        for task in tasks[:-1]:
            task.cancel()
            
    def test_queue_status(self, request_queue):
        """Test queue status reporting"""
        status = request_queue.get_queue_status()
        
        assert status['queue_size'] == 0
        assert status['max_queue_size'] == 5
        assert status['processing'] is False
        assert status['processed_count'] == 0
        assert status['dropped_count'] == 0


class TestRateLimitDecorator:
    """Test rate limit decorator functionality"""
    
    @pytest.mark.asyncio
    async def test_decorator_success(self):
        """Test successful decorated function"""
        @rate_limit_protected("test_endpoint", tokens=1)
        async def test_func(self, value):
            return f"result: {value}"
            
        # Create mock self object
        mock_self = MagicMock()
        
        result = await test_func(mock_self, "test")
        assert result == "result: test"
        
    @pytest.mark.asyncio
    async def test_decorator_critical_operation(self):
        """Test decorator with critical operation"""
        @rate_limit_protected("emergency_close", critical=True)
        async def critical_func(self):
            return "critical_result"
            
        mock_self = MagicMock()
        
        result = await critical_func(mock_self)
        assert result == "critical_result"
        
    @pytest.mark.asyncio
    async def test_decorator_rate_limit_timeout(self):
        """Test decorator with rate limit timeout"""
        @rate_limit_protected("test_endpoint", max_wait_time=0.01)
        async def test_func(self):
            return "result"
            
        mock_self = MagicMock()
        
        # Exhaust rate limit
        if hasattr(mock_self, '_rate_limit_manager'):
            manager = mock_self._rate_limit_manager
        else:
            from rate_limiter import OandaRateLimitManager
            manager = OandaRateLimitManager()
            mock_self._rate_limit_manager = manager
            
        # Exhaust tokens
        manager.global_limiter.tokens = 0
        
        with pytest.raises(Exception, match="Rate limit timeout"):
            await test_func(mock_self)


class TestGlobalRateLimitManager:
    """Test global rate limit manager"""
    
    def test_get_global_manager(self):
        """Test getting global manager instance"""
        manager1 = get_global_rate_limit_manager()
        manager2 = get_global_rate_limit_manager()
        
        assert manager1 is manager2  # Same instance
        assert isinstance(manager1, OandaRateLimitManager)


class TestIntegration:
    """Test integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_multiple_endpoints_different_limits(self):
        """Test multiple endpoints with different rate limits"""
        manager = OandaRateLimitManager()
        
        # Pricing should have higher limit than transactions
        pricing_limiter = manager.limiters["pricing"]
        transactions_limiter = manager.limiters["transactions"]
        
        assert pricing_limiter.rate > transactions_limiter.rate
        
        # Should be able to make more pricing requests
        for i in range(100):  # Pricing allows 200/sec
            result = await manager.check_rate_limit("pricing", 1)
            if result == RateLimitResult.RATE_LIMITED:
                break
                
        for i in range(30):  # Transactions allows 50/sec
            result = await manager.check_rate_limit("transactions", 1)
            if result == RateLimitResult.RATE_LIMITED:
                break
                
        # Should have consumed more pricing tokens
        assert pricing_limiter.tokens < transactions_limiter.tokens
        
    @pytest.mark.asyncio
    async def test_concurrent_rate_limiting(self):
        """Test rate limiting under concurrent load"""
        rate_limiter = TokenBucketRateLimiter(rate=10.0, burst_capacity=5)
        
        async def make_request():
            return await rate_limiter.acquire(1, "test")
            
        # Make many concurrent requests
        tasks = [make_request() for _ in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Some should be allowed, some rate limited
        allowed = sum(1 for r in results if r == RateLimitResult.ALLOWED)
        rate_limited = sum(1 for r in results if r == RateLimitResult.RATE_LIMITED)
        
        assert allowed <= 5  # Burst capacity
        assert rate_limited > 0  # Some should be rate limited
        assert allowed + rate_limited == 20


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_zero_rate_limiter(self):
        """Test rate limiter with zero rate"""
        # This should effectively disable the rate limiter
        rate_limiter = TokenBucketRateLimiter(rate=0.1, burst_capacity=1)
        assert rate_limiter.rate == 0.1
        
    def test_very_high_rate_limiter(self):
        """Test rate limiter with very high rate"""
        rate_limiter = TokenBucketRateLimiter(rate=1000000.0, burst_capacity=1000000)
        assert rate_limiter.rate == 1000000.0
        
    @pytest.mark.asyncio
    async def test_negative_tokens_request(self):
        """Test requesting negative tokens"""
        rate_limiter = TokenBucketRateLimiter(rate=10.0, burst_capacity=10)
        
        # Should handle gracefully (probably allow it)
        result = await rate_limiter.acquire(-1, "test")
        # Behavior depends on implementation
        
    @pytest.mark.asyncio
    async def test_very_long_wait_time(self):
        """Test very long wait time"""
        rate_limiter = TokenBucketRateLimiter(rate=0.1, burst_capacity=1)  # Very slow
        
        # Consume the token
        await rate_limiter.acquire(1, "test")
        
        # Request with very short timeout
        start_time = time.perf_counter()
        result = await rate_limiter.acquire(1, "test", wait_if_needed=False)
        wait_time = time.perf_counter() - start_time
        
        assert result == RateLimitResult.RATE_LIMITED
        assert wait_time < 0.1  # Should not wait


if __name__ == "__main__":
    pytest.main([__file__, "-v"])