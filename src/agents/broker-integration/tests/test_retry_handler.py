"""
Tests for Retry Handler
Story 8.9 - Task 6: Test retry mechanism with exponential backoff
"""
import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from retry_handler import (
    OandaRetryHandler, RetryConfiguration, RetryExhaustedError,
    retry_on_failure, RetryContext, OANDA_API_RETRY_CONFIG
)


class TestRetryConfiguration:
    """Test retry configuration validation"""
    
    def test_valid_configuration(self):
        """Test creating valid configuration"""
        config = RetryConfiguration(
            max_attempts=3,
            base_delay=1.0,
            max_delay=60.0,
            jitter_factor=0.1,
            backoff_multiplier=2.0
        )
        
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.jitter_factor == 0.1
        assert config.backoff_multiplier == 2.0
        
    def test_invalid_max_attempts(self):
        """Test validation of max_attempts"""
        with pytest.raises(ValueError, match="max_attempts must be at least 1"):
            RetryConfiguration(max_attempts=0)
            
    def test_invalid_base_delay(self):
        """Test validation of base_delay"""
        with pytest.raises(ValueError, match="base_delay must be positive"):
            RetryConfiguration(base_delay=0)
            
    def test_invalid_backoff_multiplier(self):
        """Test validation of backoff_multiplier"""
        with pytest.raises(ValueError, match="backoff_multiplier must be greater than 1"):
            RetryConfiguration(backoff_multiplier=1.0)


class TestOandaRetryHandler:
    """Test retry handler functionality"""
    
    @pytest.fixture
    def retry_handler(self):
        """Create retry handler for testing"""
        config = RetryConfiguration(max_attempts=3, base_delay=0.1, max_delay=1.0)
        return OandaRetryHandler(config)
        
    @pytest.mark.asyncio
    async def test_successful_first_attempt(self, retry_handler):
        """Test successful operation on first attempt"""
        mock_func = AsyncMock(return_value="success")
        
        result = await retry_handler.retry_with_backoff(mock_func, "arg1", kwarg1="value1")
        
        assert result == "success"
        assert mock_func.call_count == 1
        mock_func.assert_called_with("arg1", kwarg1="value1")
        
        metrics = retry_handler.get_retry_metrics()
        assert metrics['total_attempts'] == 1
        assert metrics['successful_attempts'] == 1
        assert metrics['failed_attempts'] == 0
        
    @pytest.mark.asyncio
    async def test_retry_with_eventual_success(self, retry_handler):
        """Test retry with success on second attempt"""
        mock_func = AsyncMock(side_effect=[
            ConnectionError("Connection failed"),
            "success"
        ])
        
        result = await retry_handler.retry_with_backoff(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 2
        
        metrics = retry_handler.get_retry_metrics()
        assert metrics['total_attempts'] == 2
        assert metrics['successful_attempts'] == 1
        assert metrics['failed_attempts'] == 0
        
    @pytest.mark.asyncio
    async def test_retry_exhausted(self, retry_handler):
        """Test retry exhaustion after max attempts"""
        mock_func = AsyncMock(side_effect=ConnectionError("Connection failed"))
        
        with pytest.raises(RetryExhaustedError) as exc_info:
            await retry_handler.retry_with_backoff(mock_func)
            
        assert "All 3 attempts failed" in str(exc_info.value)
        assert mock_func.call_count == 3
        
        metrics = retry_handler.get_retry_metrics()
        assert metrics['total_attempts'] == 3
        assert metrics['successful_attempts'] == 0
        assert metrics['failed_attempts'] == 1
        
    @pytest.mark.asyncio
    async def test_non_retryable_error(self, retry_handler):
        """Test non-retryable error fails immediately"""
        mock_func = AsyncMock(side_effect=ValueError("Invalid value"))
        
        with pytest.raises(ValueError):
            await retry_handler.retry_with_backoff(mock_func)
            
        assert mock_func.call_count == 1
        
    def test_retryable_error_detection(self, retry_handler):
        """Test retryable error detection logic"""
        # Test by error type
        assert retry_handler._is_retryable_error(ConnectionError("test"))
        assert retry_handler._is_retryable_error(TimeoutError("test"))
        
        # Test by HTTP status code
        http_error = Exception("HTTP error")
        http_error.status = 429
        assert retry_handler._is_retryable_error(http_error)
        
        http_error.status_code = 503
        assert retry_handler._is_retryable_error(http_error)
        
        # Test by error message
        rate_limit_error = Exception("Rate limit exceeded")
        assert retry_handler._is_retryable_error(rate_limit_error)
        
        # Test non-retryable error
        assert not retry_handler._is_retryable_error(ValueError("Invalid"))
        
    def test_backoff_delay_calculation(self, retry_handler):
        """Test exponential backoff delay calculation"""
        # Test base case
        delay0 = retry_handler._calculate_backoff_delay(0)
        assert 0.1 <= delay0 <= 0.11  # base_delay + jitter
        
        # Test exponential growth
        delay1 = retry_handler._calculate_backoff_delay(1)
        delay2 = retry_handler._calculate_backoff_delay(2)
        
        # Should roughly double each time (accounting for jitter)
        assert delay1 > delay0
        assert delay2 > delay1
        
        # Test max delay cap
        retry_handler.config.max_delay = 0.5
        long_delay = retry_handler._calculate_backoff_delay(10)
        assert long_delay <= 0.55  # max_delay + jitter
        
    @pytest.mark.asyncio
    async def test_retry_operation_with_name(self, retry_handler):
        """Test named retry operation"""
        mock_func = AsyncMock(return_value="success")
        
        result = await retry_handler.retry_operation("test_op", mock_func, "arg1")
        
        assert result == "success"
        mock_func.assert_called_with("arg1")
        
    def test_metrics_reset(self, retry_handler):
        """Test metrics reset functionality"""
        # Add some metrics
        retry_handler.metrics.total_attempts = 10
        retry_handler.metrics.successful_attempts = 8
        
        retry_handler.reset_metrics()
        
        metrics = retry_handler.get_retry_metrics()
        assert metrics['total_attempts'] == 0
        assert metrics['successful_attempts'] == 0
        
    def test_configure_retryable_errors(self, retry_handler):
        """Test configuring retryable error types"""
        retry_handler.configure_retryable_errors(['CustomError', 'AnotherError'])
        
        assert retry_handler.retryable_errors == {'CustomError', 'AnotherError'}


class TestRetryDecorator:
    """Test retry decorator functionality"""
    
    @pytest.mark.asyncio
    async def test_decorator_success(self):
        """Test successful decorated function"""
        @retry_on_failure(max_attempts=2, base_delay=0.1)
        async def test_func(value):
            return f"result: {value}"
            
        result = await test_func("test")
        assert result == "result: test"
        
    @pytest.mark.asyncio
    async def test_decorator_with_retry(self):
        """Test decorated function with retry"""
        call_count = 0
        
        @retry_on_failure(max_attempts=3, base_delay=0.1)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Failed")
            return "success"
            
        result = await test_func()
        assert result == "success"
        assert call_count == 2


class TestRetryContext:
    """Test retry context manager"""
    
    @pytest.mark.asyncio
    async def test_context_manager_success(self):
        """Test successful context manager usage"""
        retry_handler = OandaRetryHandler()
        mock_func = AsyncMock(return_value="success")
        
        async with RetryContext(retry_handler, "test_operation") as ctx:
            result = await ctx.execute(mock_func, "arg1")
            
        assert result == "success"
        mock_func.assert_called_with("arg1")
        
    @pytest.mark.asyncio
    async def test_context_manager_failure(self):
        """Test context manager with failure"""
        retry_handler = OandaRetryHandler()
        mock_func = AsyncMock(side_effect=ValueError("Test error"))
        
        with pytest.raises(ValueError):
            async with RetryContext(retry_handler, "test_operation") as ctx:
                await ctx.execute(mock_func)


class TestPredefinedConfigurations:
    """Test predefined retry configurations"""
    
    def test_api_config(self):
        """Test OANDA API retry configuration"""
        assert OANDA_API_RETRY_CONFIG.max_attempts == 3
        assert OANDA_API_RETRY_CONFIG.base_delay == 1.0
        assert OANDA_API_RETRY_CONFIG.max_delay == 30.0
        
    def test_config_values_are_valid(self):
        """Test that all predefined configs are valid"""
        from retry_handler import (
            OANDA_API_RETRY_CONFIG,
            OANDA_STREAMING_RETRY_CONFIG,
            OANDA_CRITICAL_RETRY_CONFIG
        )
        
        configs = [
            OANDA_API_RETRY_CONFIG,
            OANDA_STREAMING_RETRY_CONFIG, 
            OANDA_CRITICAL_RETRY_CONFIG
        ]
        
        for config in configs:
            assert config.max_attempts >= 1
            assert config.base_delay > 0
            assert config.backoff_multiplier > 1


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.mark.asyncio
    async def test_zero_jitter_factor(self):
        """Test with zero jitter factor"""
        config = RetryConfiguration(jitter_factor=0.0, base_delay=1.0)
        handler = OandaRetryHandler(config)
        
        delay = handler._calculate_backoff_delay(0)
        assert delay == 1.0  # Exactly base delay with no jitter
        
    @pytest.mark.asyncio
    async def test_high_jitter_factor(self):
        """Test with high jitter factor"""
        config = RetryConfiguration(jitter_factor=0.5, base_delay=1.0)
        handler = OandaRetryHandler(config)
        
        delay = handler._calculate_backoff_delay(0)
        assert 1.0 <= delay <= 1.5  # Base delay + up to 50% jitter
        
    @pytest.mark.asyncio
    async def test_function_with_complex_arguments(self):
        """Test retry with complex function arguments"""
        retry_handler = OandaRetryHandler()
        
        mock_func = AsyncMock(return_value="success")
        
        result = await retry_handler.retry_with_backoff(
            mock_func,
            "positional",
            {"key": "value"},
            keyword_arg="test",
            complex_arg={"nested": {"data": [1, 2, 3]}}
        )
        
        assert result == "success"
        mock_func.assert_called_with(
            "positional",
            {"key": "value"},
            keyword_arg="test",
            complex_arg={"nested": {"data": [1, 2, 3]}}
        )


@pytest.mark.asyncio
async def test_integration_with_real_delays():
    """Test integration with actual delays (shorter for testing)"""
    config = RetryConfiguration(max_attempts=3, base_delay=0.01, max_delay=0.1)
    retry_handler = OandaRetryHandler(config)
    
    call_times = []
    
    async def failing_func():
        call_times.append(time.perf_counter())
        if len(call_times) < 3:
            raise ConnectionError("Simulated failure")
        return "success"
        
    start_time = time.perf_counter()
    result = await retry_handler.retry_with_backoff(failing_func)
    total_time = time.perf_counter() - start_time
    
    assert result == "success"
    assert len(call_times) == 3
    assert total_time > 0.01  # Should have some delay
    
    # Check that delays increased between calls
    assert call_times[1] - call_times[0] > 0.005  # First retry delay
    assert call_times[2] - call_times[1] > call_times[1] - call_times[0]  # Exponential increase


if __name__ == "__main__":
    pytest.main([__file__, "-v"])