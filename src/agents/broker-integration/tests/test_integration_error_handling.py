"""
Integration Tests for Error Handling System
Story 8.9 - Task 6: Test complete error handling integration
"""
import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from retry_handler import OandaRetryHandler, RetryConfiguration
from circuit_breaker import OandaCircuitBreaker, CircuitBreakerManager, CircuitBreakerState
from rate_limiter import OandaRateLimitManager, TokenBucketRateLimiter, RateLimitResult
from graceful_degradation import GracefulDegradationManager, DegradationLevel
from error_alerting import OandaErrorHandler, AlertSeverity


class TestIntegratedErrorHandling:
    """Test integrated error handling across all components"""
    
    @pytest.fixture
    def integrated_system(self):
        """Create integrated error handling system"""
        system = {
            'retry_handler': OandaRetryHandler(RetryConfiguration(
                max_attempts=3, base_delay=0.1, max_delay=1.0
            )),
            'circuit_breaker': OandaCircuitBreaker(
                failure_threshold=3, recovery_timeout=0.5
            ),
            'rate_limiter': OandaRateLimitManager(),
            'degradation_manager': GracefulDegradationManager(),
            'error_handler': OandaErrorHandler()
        }
        system['degradation_manager'].auto_recovery_enabled = False
        return system
        
    @pytest.mark.asyncio
    async def test_retry_with_circuit_breaker_protection(self, integrated_system):
        """Test retry mechanism with circuit breaker protection"""
        retry_handler = integrated_system['retry_handler']
        circuit_breaker = integrated_system['circuit_breaker']
        
        # Create function that fails consistently
        call_count = 0
        async def failing_function():
            nonlocal call_count
            call_count += 1
            raise ConnectionError(f"Connection failed {call_count}")
            
        # Wrap with circuit breaker
        async def protected_function():
            return await circuit_breaker.call(failing_function)
            
        # First set of retries should fail and open circuit
        with pytest.raises(ConnectionError):
            await retry_handler.retry_with_backoff(protected_function)
            
        # Circuit should be open after failures
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
        # Subsequent calls should fail fast with circuit breaker
        from circuit_breaker import CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            await retry_handler.retry_with_backoff(protected_function)
            
        # Verify retry handler didn't make additional calls
        assert call_count == 3  # Only from first retry attempt
        
    @pytest.mark.asyncio
    async def test_rate_limiting_with_graceful_degradation(self, integrated_system):
        """Test rate limiting triggering graceful degradation"""
        rate_limiter = integrated_system['rate_limiter']
        degradation_manager = integrated_system['degradation_manager']
        
        # Exhaust rate limit
        global_limiter = rate_limiter.global_limiter
        global_limiter.tokens = 0
        
        # Simulate rate limit error
        rate_limit_error = Exception("Rate limit exceeded")
        
        degradation_level = await degradation_manager.handle_api_failure(
            "oanda_api", rate_limit_error
        )
        
        assert degradation_level == DegradationLevel.RATE_LIMITED
        assert degradation_manager.current_level == DegradationLevel.RATE_LIMITED
        
        # Cache should have extended TTL
        assert degradation_manager.cache_manager.default_ttl > 300
        
    @pytest.mark.asyncio
    async def test_error_alerting_integration(self, integrated_system):
        """Test error alerting integration with other components"""
        error_handler = integrated_system['error_handler']
        circuit_breaker = integrated_system['circuit_breaker']
        
        # Set up alert tracking
        alerts_sent = []
        
        async def mock_send_alert(*args, **kwargs):
            alerts_sent.append((args, kwargs))
            return "test_alert_id"
            
        with patch.object(error_handler.alert_manager, 'send_alert', side_effect=mock_send_alert):
            # Generate errors that should trigger circuit breaker
            for i in range(3):
                error = ConnectionError(f"Connection failed {i}")
                await error_handler.handle_error(error, "test_operation")
                
                # Also fail the circuit breaker
                try:
                    await circuit_breaker.call(lambda: (_ for _ in ()).throw(error))
                except ConnectionError:
                    pass
                    
        # Should have generated alerts for each error
        assert len(alerts_sent) >= 3
        
        # Circuit breaker should be open
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
    @pytest.mark.asyncio
    async def test_cascading_failure_handling(self, integrated_system):
        """Test handling cascading failures across components"""
        retry_handler = integrated_system['retry_handler']
        circuit_breaker = integrated_system['circuit_breaker']
        degradation_manager = integrated_system['degradation_manager']
        error_handler = integrated_system['error_handler']
        
        failure_sequence = []
        
        async def cascading_failure():
            failure_sequence.append("attempt")
            if len(failure_sequence) <= 3:
                raise ConnectionError("Initial connection failure")
            elif len(failure_sequence) <= 6:
                raise TimeoutError("Timeout after connection issues")
            else:
                return "success"
                
        # Track errors
        errors_handled = []
        
        async def track_error_handling(error, operation, *args, **kwargs):
            errors_handled.append((type(error).__name__, operation))
            return await error_handler.handle_error(error, operation, *args, **kwargs)
            
        # First attempt - should fail with retries
        with pytest.raises(ConnectionError):
            try:
                await retry_handler.retry_with_backoff(cascading_failure)
            except Exception as e:
                await track_error_handling(e, "cascading_test")
                raise
                
        # Circuit breaker should still be closed (not enough failures)
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        
        # Trigger degradation due to connection errors
        await degradation_manager.handle_api_failure("test_service", ConnectionError("Persistent connection issue"))
        
        assert degradation_manager.current_level == DegradationLevel.READ_ONLY
        
    @pytest.mark.asyncio
    async def test_recovery_coordination(self, integrated_system):
        """Test coordinated recovery across components"""
        circuit_breaker = integrated_system['circuit_breaker']
        degradation_manager = integrated_system['degradation_manager']
        rate_limiter = integrated_system['rate_limiter']
        
        # Put system in degraded state
        await degradation_manager._transition_to_degradation_level(
            DegradationLevel.READ_ONLY, "Test degradation"
        )
        
        # Open circuit breaker
        for i in range(circuit_breaker.failure_threshold):
            try:
                await circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception("Test error")))
            except:
                pass
                
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
        # Exhaust rate limiter
        rate_limiter.global_limiter.tokens = 0
        
        # Manual recovery
        await circuit_breaker.manual_reset("Coordinated recovery")
        await degradation_manager.manual_recovery("Coordinated recovery")
        await rate_limiter.reset_all_limiters()
        
        # Verify all components are healthy
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert degradation_manager.current_level == DegradationLevel.NONE
        assert rate_limiter.global_limiter.tokens == 100
        
    @pytest.mark.asyncio
    async def test_performance_under_load(self, integrated_system):
        """Test system performance under concurrent load"""
        retry_handler = integrated_system['retry_handler']
        circuit_breaker = integrated_system['circuit_breaker']
        rate_limiter = integrated_system['rate_limiter']
        
        success_count = 0
        failure_count = 0
        
        async def load_test_operation(operation_id):
            nonlocal success_count, failure_count
            
            try:
                # Check rate limit
                rate_result = await rate_limiter.check_rate_limit(f"test_endpoint_{operation_id % 3}")
                if rate_result != RateLimitResult.ALLOWED:
                    failure_count += 1
                    return
                    
                # Execute with circuit breaker
                result = await circuit_breaker.call(lambda: f"success_{operation_id}")
                success_count += 1
                return result
                
            except Exception:
                failure_count += 1
                
        # Execute concurrent operations
        start_time = time.perf_counter()
        tasks = [load_test_operation(i) for i in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.perf_counter()
        
        execution_time = end_time - start_time
        
        # Performance assertions
        assert execution_time < 5.0  # Should complete within 5 seconds
        assert success_count > 0  # Some operations should succeed
        
        # System should still be functional
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        
    @pytest.mark.asyncio
    async def test_error_correlation_and_tracking(self, integrated_system):
        """Test error correlation across components"""
        error_handler = integrated_system['error_handler']
        degradation_manager = integrated_system['degradation_manager']
        
        correlation_id = "test_correlation_123"
        
        # Generate correlated errors
        errors = [
            ConnectionError("Primary connection failed"),
            TimeoutError("Request timeout"),
            ConnectionError("Secondary connection failed")
        ]
        
        error_contexts = []
        for i, error in enumerate(errors):
            context = await error_handler.handle_error(
                error, f"operation_{i}", "test_service",
                correlation_id=correlation_id,
                request_id=f"req_{i}"
            )
            error_contexts.append(context)
            
            # Also trigger degradation
            await degradation_manager.handle_api_failure("test_service", error)
            
        # Verify correlation tracking
        for context in error_contexts:
            assert context.correlation_id == correlation_id
            
        # Verify degradation progression
        assert degradation_manager.current_level == DegradationLevel.READ_ONLY
        
        # Check error summary includes correlated errors
        error_summary = error_handler.structured_logger.get_error_summary(hours=1)
        assert error_summary['total_errors'] == 3
        assert 'ConnectionError' in error_summary['error_breakdown']
        assert 'TimeoutError' in error_summary['error_breakdown']


class TestErrorHandlingPatterns:
    """Test common error handling patterns"""
    
    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff_pattern(self):
        """Test retry with exponential backoff pattern"""
        retry_handler = OandaRetryHandler(RetryConfiguration(
            max_attempts=4, base_delay=0.1, backoff_multiplier=2.0, jitter_factor=0.0
        ))
        
        call_times = []
        
        async def time_tracked_failure():
            call_times.append(time.perf_counter())
            if len(call_times) < 3:
                raise ConnectionError("Temporary failure")
            return "success"
            
        start_time = time.perf_counter()
        result = await retry_handler.retry_with_backoff(time_tracked_failure)
        
        assert result == "success"
        assert len(call_times) == 3
        
        # Verify exponential backoff timing (allowing for timing variance)
        if len(call_times) >= 2:
            interval1 = call_times[1] - call_times[0]
            assert 0.08 <= interval1 <= 0.15  # ~0.1s with variance
        if len(call_times) >= 3:
            interval2 = call_times[2] - call_times[1]
            assert 0.18 <= interval2 <= 0.25  # ~0.2s with variance
        
    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self):
        """Test circuit breaker pattern implementation"""
        circuit_breaker = OandaCircuitBreaker(failure_threshold=3, recovery_timeout=0.2)
        
        # Phase 1: Normal operation (CLOSED)
        result = await circuit_breaker.call(lambda: "success")
        assert result == "success"
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        
        # Phase 2: Failures leading to OPEN
        for i in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception("Failure")))
                
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
        # Phase 3: Fast failure (OPEN)
        from circuit_breaker import CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            await circuit_breaker.call(lambda: "should not execute")
            
        # Phase 4: Recovery attempt (HALF_OPEN)
        await asyncio.sleep(circuit_breaker.recovery_timeout + 0.1)
        
        result = await circuit_breaker.call(lambda: "recovered")
        assert result == "recovered"
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        
    @pytest.mark.asyncio
    async def test_bulkhead_pattern_with_rate_limiting(self):
        """Test bulkhead pattern using rate limiting"""
        rate_manager = OandaRateLimitManager()
        
        # Different endpoints have different rate limits (bulkheads)
        high_priority_results = []
        low_priority_results = []
        
        async def high_priority_operation(i):
            result = await rate_manager.check_rate_limit("accounts", 1, is_critical=True)
            if result == RateLimitResult.ALLOWED:
                high_priority_results.append(f"high_{i}")
                
        async def low_priority_operation(i):
            result = await rate_manager.check_rate_limit("transactions", 1)
            if result == RateLimitResult.ALLOWED:
                low_priority_results.append(f"low_{i}")
                
        # Execute mixed priority operations with some delay to avoid race conditions
        tasks = []
        for i in range(5):  # Reduced count to avoid overwhelming rate limiter
            tasks.append(high_priority_operation(i))
            tasks.append(low_priority_operation(i))
            
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # High priority should have some results (critical operations bypass some limits)
        assert len(high_priority_results) > 0
        
    @pytest.mark.asyncio
    async def test_graceful_degradation_pattern(self):
        """Test graceful degradation pattern"""
        degradation_manager = GracefulDegradationManager()
        
        # Cache some data for fallback
        cached_data = {"price": 1.2345, "timestamp": "2023-01-01T12:00:00Z"}
        await degradation_manager.cache_data("pricing", "EUR_USD", cached_data)
        
        # Simulate primary function failure
        async def primary_pricing_function():
            raise ConnectionError("Pricing service unavailable")
            
        async def fallback_pricing_function():
            return await degradation_manager.get_cached_data("pricing", "EUR_USD")
            
        # Execute with fallback
        result = await degradation_manager.execute_with_fallback(
            "get_prices", primary_pricing_function, fallback_pricing_function
        )
        
        assert result == cached_data
        
        # System should be in degraded state
        assert degradation_manager.current_level != DegradationLevel.NONE


class TestErrorHandlingMetrics:
    """Test error handling metrics and monitoring"""
    
    @pytest.mark.asyncio
    async def test_comprehensive_metrics_collection(self):
        """Test comprehensive metrics across all components"""
        # Create all components
        retry_handler = OandaRetryHandler()
        circuit_breaker = OandaCircuitBreaker()
        rate_limiter = OandaRateLimitManager()
        degradation_manager = GracefulDegradationManager()
        error_handler = OandaErrorHandler()
        
        # Generate some activity
        try:
            await retry_handler.retry_with_backoff(lambda: (_ for _ in ()).throw(ConnectionError("Test")))
        except:
            pass
            
        try:
            await circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception("Test")))
        except:
            pass
            
        await rate_limiter.check_rate_limit("test_endpoint")
        await degradation_manager.handle_api_failure("test_service", Exception("Test"))
        await error_handler.handle_error(Exception("Test"), "test_operation")
        
        # Collect metrics
        retry_metrics = retry_handler.get_retry_metrics()
        circuit_metrics = circuit_breaker.get_metrics()
        rate_metrics = rate_limiter.get_all_metrics()
        degradation_status = degradation_manager.get_system_status()
        error_stats = error_handler.get_error_statistics()
        
        # Verify metrics structure
        assert 'total_attempts' in retry_metrics
        assert 'total_requests' in circuit_metrics
        assert 'global_oanda' in rate_metrics
        assert 'degradation_level' in degradation_status
        assert 'total_errors' in error_stats
        
    @pytest.mark.asyncio
    async def test_health_check_integration(self):
        """Test integrated health checking"""
        circuit_breaker = OandaCircuitBreaker()
        degradation_manager = GracefulDegradationManager()
        
        # Initial health should be good
        circuit_health = await circuit_breaker.health_check()
        system_status = degradation_manager.get_system_status()
        
        assert circuit_health['healthy'] is True
        assert system_status['degradation_level'] == DegradationLevel.NONE.value
        
        # Degrade system
        for i in range(3):
            try:
                await circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception("Test")))
            except:
                pass
                
        await degradation_manager._transition_to_degradation_level(
            DegradationLevel.READ_ONLY, "Test"
        )
        
        # Health should reflect degradation
        circuit_health = await circuit_breaker.health_check()
        system_status = degradation_manager.get_system_status()
        
        assert circuit_health['healthy'] is False
        assert system_status['degradation_level'] == DegradationLevel.READ_ONLY.value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])