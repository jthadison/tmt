"""
OANDA Retry Handler with Exponential Backoff
Story 8.9 - Task 1: Implement retry mechanism with backoff
"""
import asyncio
import logging
import random
import time
from typing import Callable, Any, Optional, Dict, List
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
import functools

logger = logging.getLogger(__name__)


class RetryableError(Exception):
    """Base class for retryable errors"""
    pass


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted"""
    pass


class RetryDecision(Enum):
    """Retry decision types"""
    RETRY = "retry"
    FAIL_FAST = "fail_fast"
    CIRCUIT_BREAK = "circuit_break"


@dataclass
class RetryAttempt:
    """Represents a single retry attempt"""
    attempt_number: int
    timestamp: datetime
    error: Optional[str]
    delay_ms: float
    success: bool
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'attempt_number': self.attempt_number,
            'timestamp': self.timestamp.isoformat(),
            'error': self.error,
            'delay_ms': self.delay_ms,
            'success': self.success
        }


@dataclass
class RetryMetrics:
    """Retry metrics for monitoring"""
    total_attempts: int
    successful_attempts: int
    failed_attempts: int
    average_attempts_per_success: float
    total_retry_time_ms: float
    retry_attempts: List[RetryAttempt]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'total_attempts': self.total_attempts,
            'successful_attempts': self.successful_attempts,
            'failed_attempts': self.failed_attempts,
            'average_attempts_per_success': self.average_attempts_per_success,
            'total_retry_time_ms': self.total_retry_time_ms,
            'success_rate': (self.successful_attempts / self.total_attempts * 100) if self.total_attempts > 0 else 0,
            'retry_attempts': [attempt.to_dict() for attempt in self.retry_attempts[-50:]]  # Last 50 attempts
        }


class RetryConfiguration:
    """Configuration for retry behavior"""
    
    def __init__(self,
                 max_attempts: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 jitter_factor: float = 0.1,
                 backoff_multiplier: float = 2.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter_factor = jitter_factor
        self.backoff_multiplier = backoff_multiplier
        
        # Validate configuration
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if base_delay <= 0:
            raise ValueError("base_delay must be positive")
        if backoff_multiplier <= 1:
            raise ValueError("backoff_multiplier must be greater than 1")


class OandaRetryHandler:
    """Handles retries for OANDA API calls with exponential backoff"""
    
    def __init__(self, config: Optional[RetryConfiguration] = None):
        self.config = config or RetryConfiguration()
        self.metrics = RetryMetrics(
            total_attempts=0,
            successful_attempts=0,
            failed_attempts=0,
            average_attempts_per_success=0.0,
            total_retry_time_ms=0.0,
            retry_attempts=[]
        )
        self.retryable_errors = {
            'ConnectionError', 'TimeoutError', 'HTTPError',
            'ServiceUnavailable', 'TooManyRequests', 'InternalServerError'
        }
        
    async def retry_with_backoff(self, 
                                func: Callable, 
                                *args, 
                                **kwargs) -> Any:
        """
        Retry function with exponential backoff
        
        Args:
            func: Async function to retry
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result on success
            
        Raises:
            RetryExhaustedError: When all retry attempts are exhausted
        """
        start_time = time.perf_counter()
        last_exception = None
        attempt_records = []
        
        for attempt in range(self.config.max_attempts):
            attempt_start = time.perf_counter()
            
            try:
                # Execute the function
                result = await func(*args, **kwargs)
                
                # Record successful attempt
                attempt_record = RetryAttempt(
                    attempt_number=attempt + 1,
                    timestamp=datetime.now(timezone.utc),
                    error=None,
                    delay_ms=0.0,
                    success=True
                )
                attempt_records.append(attempt_record)
                
                # Update metrics
                self._update_success_metrics(attempt_records, start_time)
                
                logger.info(f"Operation succeeded on attempt {attempt + 1}")
                return result
                
            except Exception as e:
                last_exception = e
                error_name = type(e).__name__
                
                # Check if error is retryable
                if not self._is_retryable_error(e):
                    logger.error(f"Non-retryable error on attempt {attempt + 1}: {error_name}")
                    self._update_failure_metrics(attempt_records, start_time)
                    raise
                
                # Record failed attempt
                attempt_record = RetryAttempt(
                    attempt_number=attempt + 1,
                    timestamp=datetime.now(timezone.utc),
                    error=str(e),
                    delay_ms=0.0,
                    success=False
                )
                attempt_records.append(attempt_record)
                
                # Check if this was the last attempt
                if attempt == self.config.max_attempts - 1:
                    logger.error(f"All {self.config.max_attempts} attempts failed. Last error: {error_name}")
                    self._update_failure_metrics(attempt_records, start_time)
                    break
                    
                # Calculate backoff delay
                delay = self._calculate_backoff_delay(attempt)
                attempt_record.delay_ms = delay * 1000
                
                logger.warning(f"Attempt {attempt + 1} failed with {error_name}, retrying in {delay:.2f}s")
                
                # Wait before retry
                await asyncio.sleep(delay)
                
        # All attempts failed
        total_time = (time.perf_counter() - start_time) * 1000
        error_summary = f"All {self.config.max_attempts} attempts failed over {total_time:.1f}ms"
        
        raise RetryExhaustedError(error_summary) from last_exception
        
    def _calculate_backoff_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay with jitter
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff: base_delay * (multiplier ^ attempt)
        delay = self.config.base_delay * (self.config.backoff_multiplier ** attempt)
        
        # Cap at max_delay
        delay = min(delay, self.config.max_delay)
        
        # Add jitter to prevent thundering herd
        jitter = random.uniform(0, delay * self.config.jitter_factor)
        
        return delay + jitter
        
    def _is_retryable_error(self, error: Exception) -> bool:
        """
        Determine if an error should be retried
        
        Args:
            error: Exception to check
            
        Returns:
            True if error is retryable
        """
        error_name = type(error).__name__
        
        # Check by error type
        if error_name in self.retryable_errors:
            return True
            
        # Check by HTTP status code if available
        if hasattr(error, 'status') or hasattr(error, 'status_code'):
            status = getattr(error, 'status', getattr(error, 'status_code', None))
            
            # Retry on server errors (5xx) and rate limiting (429)
            if status in [429, 500, 502, 503, 504]:
                return True
                
        # Check error message for known retryable patterns
        error_msg = str(error).lower()
        retryable_patterns = [
            'timeout', 'connection', 'unavailable', 'overloaded',
            'rate limit', 'too many requests', 'server error'
        ]
        
        return any(pattern in error_msg for pattern in retryable_patterns)
        
    def _update_success_metrics(self, attempts: List[RetryAttempt], start_time: float):
        """Update metrics after successful operation"""
        self.metrics.total_attempts += len(attempts)
        self.metrics.successful_attempts += 1
        
        total_time = (time.perf_counter() - start_time) * 1000
        self.metrics.total_retry_time_ms += total_time
        
        # Update average attempts per success
        if self.metrics.successful_attempts > 0:
            self.metrics.average_attempts_per_success = (
                self.metrics.total_attempts / self.metrics.successful_attempts
            )
            
        # Store attempt records
        self.metrics.retry_attempts.extend(attempts)
        
    def _update_failure_metrics(self, attempts: List[RetryAttempt], start_time: float):
        """Update metrics after failed operation"""
        self.metrics.total_attempts += len(attempts)
        self.metrics.failed_attempts += 1
        
        total_time = (time.perf_counter() - start_time) * 1000
        self.metrics.total_retry_time_ms += total_time
        
        # Store attempt records
        self.metrics.retry_attempts.extend(attempts)
        
    def get_retry_metrics(self) -> Dict[str, Any]:
        """Get current retry metrics"""
        return self.metrics.to_dict()
        
    def reset_metrics(self):
        """Reset retry metrics"""
        self.metrics = RetryMetrics(
            total_attempts=0,
            successful_attempts=0,
            failed_attempts=0,
            average_attempts_per_success=0.0,
            total_retry_time_ms=0.0,
            retry_attempts=[]
        )
        
    def configure_retryable_errors(self, error_types: List[str]):
        """Configure which error types should be retried"""
        self.retryable_errors = set(error_types)
        
    async def retry_operation(self, operation_name: str, func: Callable, *args, **kwargs) -> Any:
        """
        Retry operation with logging and metrics
        
        Args:
            operation_name: Name of operation for logging
            func: Function to retry
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
        """
        logger.info(f"Starting retry operation: {operation_name}")
        
        try:
            result = await self.retry_with_backoff(func, *args, **kwargs)
            logger.info(f"Retry operation completed successfully: {operation_name}")
            return result
            
        except RetryExhaustedError as e:
            logger.error(f"Retry operation failed after all attempts: {operation_name} - {e}")
            raise
            
        except Exception as e:
            logger.error(f"Retry operation failed with non-retryable error: {operation_name} - {e}")
            raise


def retry_on_failure(max_attempts: int = 3, 
                    base_delay: float = 1.0,
                    max_delay: float = 60.0,
                    jitter_factor: float = 0.1):
    """
    Decorator for automatic retry with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        jitter_factor: Jitter factor (0.0 to 1.0)
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            config = RetryConfiguration(
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                jitter_factor=jitter_factor
            )
            
            retry_handler = OandaRetryHandler(config)
            return await retry_handler.retry_with_backoff(func, *args, **kwargs)
            
        return wrapper
    return decorator


# Predefined configurations for common scenarios
OANDA_API_RETRY_CONFIG = RetryConfiguration(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    jitter_factor=0.1,
    backoff_multiplier=2.0
)

OANDA_STREAMING_RETRY_CONFIG = RetryConfiguration(
    max_attempts=5,
    base_delay=0.5,
    max_delay=10.0,
    jitter_factor=0.2,
    backoff_multiplier=1.5
)

OANDA_CRITICAL_RETRY_CONFIG = RetryConfiguration(
    max_attempts=5,
    base_delay=2.0,
    max_delay=60.0,
    jitter_factor=0.05,
    backoff_multiplier=2.5
)


class RetryContext:
    """Context manager for retry operations"""
    
    def __init__(self, retry_handler: OandaRetryHandler, operation_name: str):
        self.retry_handler = retry_handler
        self.operation_name = operation_name
        self.start_time = None
        
    async def __aenter__(self):
        self.start_time = time.perf_counter()
        logger.debug(f"Starting retry context: {self.operation_name}")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (time.perf_counter() - self.start_time) * 1000
            if exc_type is None:
                logger.debug(f"Retry context completed successfully: {self.operation_name} ({duration:.1f}ms)")
            else:
                logger.error(f"Retry context failed: {self.operation_name} ({duration:.1f}ms) - {exc_type.__name__}")
                
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry"""
        return await self.retry_handler.retry_operation(
            self.operation_name, func, *args, **kwargs
        )