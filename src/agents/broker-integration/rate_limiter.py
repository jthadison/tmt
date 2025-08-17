"""
OANDA Rate Limiting System
Story 8.9 - Task 3: Create rate limiting system
"""
import asyncio
import logging
import time
import functools
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from collections import deque

logger = logging.getLogger(__name__)


class RateLimitResult(Enum):
    """Rate limit check results"""
    ALLOWED = "allowed"
    RATE_LIMITED = "rate_limited"
    QUEUED = "queued"


@dataclass
class RateLimitEvent:
    """Rate limit event for monitoring"""
    event_id: str
    timestamp: datetime
    endpoint: str
    result: RateLimitResult
    tokens_requested: int
    tokens_available: int
    wait_time_ms: float
    client_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'endpoint': self.endpoint,
            'result': self.result.value,
            'tokens_requested': self.tokens_requested,
            'tokens_available': self.tokens_available,
            'wait_time_ms': self.wait_time_ms,
            'client_id': self.client_id
        }


@dataclass
class RateLimitMetrics:
    """Rate limit metrics for monitoring"""
    total_requests: int
    allowed_requests: int
    rate_limited_requests: int
    queued_requests: int
    average_wait_time_ms: float
    max_wait_time_ms: float
    current_tokens: float
    requests_per_second: float
    recent_events: List[RateLimitEvent]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'total_requests': self.total_requests,
            'allowed_requests': self.allowed_requests,
            'rate_limited_requests': self.rate_limited_requests,
            'queued_requests': self.queued_requests,
            'success_rate': (self.allowed_requests / self.total_requests * 100) if self.total_requests > 0 else 0,
            'average_wait_time_ms': self.average_wait_time_ms,
            'max_wait_time_ms': self.max_wait_time_ms,
            'current_tokens': self.current_tokens,
            'requests_per_second': self.requests_per_second,
            'recent_events': [event.to_dict() for event in self.recent_events[-100:]]  # Last 100 events
        }


class TokenBucketRateLimiter:
    """Token bucket rate limiter implementation"""
    
    def __init__(self,
                 rate: float = 100.0,
                 burst_capacity: int = 100,
                 name: str = "default"):
        self.name = name
        self.rate = rate  # tokens per second
        self.burst_capacity = burst_capacity  # max tokens in bucket
        self.tokens = float(burst_capacity)  # current tokens
        self.last_refill = time.perf_counter()
        self._lock = asyncio.Lock()
        
        # Metrics
        self.metrics = RateLimitMetrics(
            total_requests=0,
            allowed_requests=0,
            rate_limited_requests=0,
            queued_requests=0,
            average_wait_time_ms=0.0,
            max_wait_time_ms=0.0,
            current_tokens=self.tokens,
            requests_per_second=0.0,
            recent_events=[]
        )
        
        # Request tracking for RPS calculation
        self.request_timestamps = deque(maxlen=1000)
        
    async def acquire(self, 
                     tokens: int = 1,
                     endpoint: str = "unknown",
                     client_id: Optional[str] = None,
                     wait_if_needed: bool = True) -> RateLimitResult:
        """
        Acquire tokens from the bucket
        
        Args:
            tokens: Number of tokens to acquire
            endpoint: Endpoint name for tracking
            client_id: Optional client identifier
            wait_if_needed: Whether to wait if tokens are not available
            
        Returns:
            RateLimitResult indicating the outcome
        """
        start_time = time.perf_counter()
        
        async with self._lock:
            self._refill_tokens()
            
            # Update metrics
            self.metrics.total_requests += 1
            self.metrics.current_tokens = self.tokens
            self.request_timestamps.append(time.perf_counter())
            self._update_rps()
            
            # Check if tokens are available
            if self.tokens >= tokens:
                # Tokens available, grant immediately
                self.tokens -= tokens
                self.metrics.allowed_requests += 1
                
                wait_time = (time.perf_counter() - start_time) * 1000
                
                event = RateLimitEvent(
                    event_id=str(uuid.uuid4()),
                    timestamp=datetime.now(timezone.utc),
                    endpoint=endpoint,
                    result=RateLimitResult.ALLOWED,
                    tokens_requested=tokens,
                    tokens_available=int(self.tokens),
                    wait_time_ms=wait_time,
                    client_id=client_id
                )
                
                self.metrics.recent_events.append(event)
                return RateLimitResult.ALLOWED
                
            elif wait_if_needed:
                # Tokens not available, but we can wait
                self.metrics.queued_requests += 1
                
                # Calculate wait time
                tokens_needed = tokens - self.tokens
                wait_time_seconds = tokens_needed / self.rate
                
                logger.debug(f"Rate limiting {endpoint}: waiting {wait_time_seconds:.2f}s for {tokens} tokens")
                
        # Wait outside the lock to allow other operations
        if wait_if_needed and tokens > self.tokens:
            await asyncio.sleep(wait_time_seconds)
            
            # Try again after waiting
            async with self._lock:
                self._refill_tokens()
                
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    total_wait_time = (time.perf_counter() - start_time) * 1000
                    
                    # Update wait time metrics
                    self._update_wait_time_metrics(total_wait_time)
                    
                    event = RateLimitEvent(
                        event_id=str(uuid.uuid4()),
                        timestamp=datetime.now(timezone.utc),
                        endpoint=endpoint,
                        result=RateLimitResult.QUEUED,
                        tokens_requested=tokens,
                        tokens_available=int(self.tokens),
                        wait_time_ms=total_wait_time,
                        client_id=client_id
                    )
                    
                    self.metrics.recent_events.append(event)
                    return RateLimitResult.QUEUED
                    
        # Rate limited
        self.metrics.rate_limited_requests += 1
        
        event = RateLimitEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            endpoint=endpoint,
            result=RateLimitResult.RATE_LIMITED,
            tokens_requested=tokens,
            tokens_available=int(self.tokens),
            wait_time_ms=0.0,
            client_id=client_id
        )
        
        self.metrics.recent_events.append(event)
        return RateLimitResult.RATE_LIMITED
        
    def _refill_tokens(self):
        """Refill tokens based on elapsed time"""
        now = time.perf_counter()
        time_elapsed = now - self.last_refill
        
        # Add tokens based on rate and time elapsed
        tokens_to_add = time_elapsed * self.rate
        self.tokens = min(self.burst_capacity, self.tokens + tokens_to_add)
        self.last_refill = now
        
    def _update_rps(self):
        """Update requests per second calculation"""
        now = time.perf_counter()
        
        # Remove timestamps older than 1 second
        while self.request_timestamps and now - self.request_timestamps[0] > 1.0:
            self.request_timestamps.popleft()
            
        self.metrics.requests_per_second = len(self.request_timestamps)
        
    def _update_wait_time_metrics(self, wait_time_ms: float):
        """Update wait time metrics"""
        if wait_time_ms > self.metrics.max_wait_time_ms:
            self.metrics.max_wait_time_ms = wait_time_ms
            
        # Update rolling average wait time
        queued_count = self.metrics.queued_requests
        if queued_count > 0:
            total_wait_time = self.metrics.average_wait_time_ms * (queued_count - 1)
            total_wait_time += wait_time_ms
            self.metrics.average_wait_time_ms = total_wait_time / queued_count
            
    def get_status(self) -> Dict[str, Any]:
        """Get current rate limiter status"""
        return {
            'name': self.name,
            'rate': self.rate,
            'burst_capacity': self.burst_capacity,
            'current_tokens': self.tokens,
            'utilization_percentage': ((self.burst_capacity - self.tokens) / self.burst_capacity * 100),
            'requests_per_second': self.metrics.requests_per_second,
            'is_rate_limiting': self.tokens < 1
        }
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get rate limiter metrics"""
        return self.metrics.to_dict()
        
    async def wait_for_tokens(self, tokens: int = 1) -> float:
        """
        Wait until tokens are available
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            Wait time in seconds
        """
        start_time = time.perf_counter()
        
        while True:
            async with self._lock:
                self._refill_tokens()
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    break
                    
            # Calculate wait time
            tokens_needed = tokens - self.tokens
            wait_time = tokens_needed / self.rate
            await asyncio.sleep(min(wait_time, 0.1))  # Check at least every 100ms
            
        return time.perf_counter() - start_time


class OandaRateLimitManager:
    """Manages rate limiting for different OANDA endpoints"""
    
    def __init__(self):
        self.limiters: Dict[str, TokenBucketRateLimiter] = {}
        self.global_limiter = TokenBucketRateLimiter(
            rate=100.0,  # 100 requests per second global limit
            burst_capacity=100,
            name="global_oanda"
        )
        
        # Default rate limits per endpoint
        self.default_limits = {
            'transactions': TokenBucketRateLimiter(rate=50.0, burst_capacity=50, name="transactions"),
            'accounts': TokenBucketRateLimiter(rate=30.0, burst_capacity=30, name="accounts"),
            'pricing': TokenBucketRateLimiter(rate=200.0, burst_capacity=200, name="pricing"),
            'orders': TokenBucketRateLimiter(rate=100.0, burst_capacity=100, name="orders"),
            'positions': TokenBucketRateLimiter(rate=50.0, burst_capacity=50, name="positions"),
            'streaming': TokenBucketRateLimiter(rate=10.0, burst_capacity=10, name="streaming")
        }
        
        self.limiters.update(self.default_limits)
        
        # Critical operations that can bypass some limits
        self.critical_endpoints = {'emergency_close', 'risk_check', 'account_balance'}
        
    async def check_rate_limit(self,
                              endpoint: str,
                              tokens: int = 1,
                              client_id: Optional[str] = None,
                              is_critical: bool = False) -> RateLimitResult:
        """
        Check rate limit for endpoint
        
        Args:
            endpoint: Endpoint name
            tokens: Number of tokens needed
            client_id: Optional client identifier
            is_critical: Whether this is a critical operation
            
        Returns:
            RateLimitResult
        """
        # Critical operations get priority
        if is_critical and endpoint in self.critical_endpoints:
            logger.debug(f"Bypassing rate limit for critical operation: {endpoint}")
            return RateLimitResult.ALLOWED
            
        # Check global rate limit first
        global_result = await self.global_limiter.acquire(
            tokens, f"global:{endpoint}", client_id, wait_if_needed=False
        )
        
        if global_result == RateLimitResult.RATE_LIMITED:
            logger.warning(f"Global rate limit exceeded for {endpoint}")
            return global_result
            
        # Check endpoint-specific rate limit
        limiter = self.limiters.get(endpoint)
        if limiter:
            endpoint_result = await limiter.acquire(
                tokens, endpoint, client_id, wait_if_needed=False
            )
            
            if endpoint_result == RateLimitResult.RATE_LIMITED:
                logger.warning(f"Endpoint rate limit exceeded for {endpoint}")
                return endpoint_result
                
        return RateLimitResult.ALLOWED
        
    async def acquire_with_wait(self,
                               endpoint: str,
                               tokens: int = 1,
                               client_id: Optional[str] = None,
                               max_wait_time: float = 30.0) -> bool:
        """
        Acquire tokens with waiting, respecting max wait time
        
        Args:
            endpoint: Endpoint name
            tokens: Number of tokens needed
            client_id: Optional client identifier
            max_wait_time: Maximum time to wait in seconds
            
        Returns:
            True if tokens were acquired, False if max wait time exceeded
        """
        start_time = time.perf_counter()
        
        # Check if we can proceed immediately
        result = await self.check_rate_limit(endpoint, tokens, client_id)
        if result == RateLimitResult.ALLOWED:
            return True
            
        # Wait for tokens if needed
        limiter = self.limiters.get(endpoint, self.global_limiter)
        
        try:
            wait_time = await asyncio.wait_for(
                limiter.wait_for_tokens(tokens),
                timeout=max_wait_time
            )
            
            logger.debug(f"Acquired tokens for {endpoint} after {wait_time:.2f}s wait")
            return True
            
        except asyncio.TimeoutError:
            logger.warning(f"Rate limit wait timeout for {endpoint} ({max_wait_time}s)")
            return False
            
    def add_endpoint_limiter(self,
                           endpoint: str,
                           rate: float,
                           burst_capacity: int):
        """Add custom rate limiter for endpoint"""
        self.limiters[endpoint] = TokenBucketRateLimiter(
            rate=rate,
            burst_capacity=burst_capacity,
            name=endpoint
        )
        
        logger.info(f"Added rate limiter for {endpoint}: {rate}/s, burst {burst_capacity}")
        
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all rate limiters"""
        return {
            name: limiter.get_status()
            for name, limiter in self.limiters.items()
        }
        
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all rate limiters"""
        return {
            name: limiter.get_metrics()
            for name, limiter in self.limiters.items()
        }
        
    async def reset_limiter(self, endpoint: str) -> bool:
        """Reset specific rate limiter"""
        if endpoint in self.limiters:
            limiter = self.limiters[endpoint]
            limiter.tokens = float(limiter.burst_capacity)
            limiter.last_refill = time.perf_counter()
            logger.info(f"Reset rate limiter for {endpoint}")
            return True
        return False
        
    async def reset_all_limiters(self):
        """Reset all rate limiters"""
        for endpoint in self.limiters:
            await self.reset_limiter(endpoint)
        logger.info("Reset all rate limiters")


class RequestQueue:
    """Queue for handling burst requests when rate limited"""
    
    def __init__(self, max_queue_size: int = 1000):
        self.max_queue_size = max_queue_size
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.processing = False
        self.processed_count = 0
        self.dropped_count = 0
        
    async def enqueue_request(self,
                            func: Callable,
                            args: tuple,
                            kwargs: dict,
                            priority: int = 0) -> Any:
        """
        Enqueue request for processing
        
        Args:
            func: Function to execute
            args: Function arguments
            kwargs: Function keyword arguments
            priority: Request priority (higher = more priority)
            
        Returns:
            Future that will contain the result
        """
        request_item = {
            'func': func,
            'args': args,
            'kwargs': kwargs,
            'priority': priority,
            'future': asyncio.Future(),
            'queued_at': time.perf_counter()
        }
        
        try:
            await self.queue.put(request_item)
            
            # Start processing if not already running
            if not self.processing:
                asyncio.create_task(self._process_queue())
                
            return await request_item['future']
            
        except asyncio.QueueFull:
            self.dropped_count += 1
            raise Exception(f"Request queue full ({self.max_queue_size}), request dropped")
            
    async def _process_queue(self):
        """Process queued requests"""
        self.processing = True
        
        try:
            while not self.queue.empty():
                try:
                    # Get request from queue
                    request = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                    
                    # Execute request
                    try:
                        result = await request['func'](*request['args'], **request['kwargs'])
                        request['future'].set_result(result)
                        self.processed_count += 1
                        
                    except Exception as e:
                        request['future'].set_exception(e)
                        
                    finally:
                        self.queue.task_done()
                        
                except asyncio.TimeoutError:
                    # No more requests in queue
                    break
                    
        finally:
            self.processing = False
            
    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status"""
        return {
            'queue_size': self.queue.qsize(),
            'max_queue_size': self.max_queue_size,
            'processing': self.processing,
            'processed_count': self.processed_count,
            'dropped_count': self.dropped_count,
            'utilization': (self.queue.qsize() / self.max_queue_size * 100)
        }


def rate_limit_protected(endpoint: str, 
                        tokens: int = 1,
                        max_wait_time: float = 30.0,
                        critical: bool = False):
    """
    Decorator for automatic rate limiting protection
    
    Args:
        endpoint: Endpoint name for rate limiting
        tokens: Number of tokens required
        max_wait_time: Maximum time to wait for tokens
        critical: Whether this is a critical operation
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get or create rate limit manager from class instance
            if hasattr(args[0], '_rate_limit_manager'):
                manager = args[0]._rate_limit_manager
            else:
                # Create manager if it doesn't exist
                manager = OandaRateLimitManager()
                args[0]._rate_limit_manager = manager
                
            # Check rate limit
            if critical:
                result = await manager.check_rate_limit(endpoint, tokens, is_critical=True)
            else:
                acquired = await manager.acquire_with_wait(endpoint, tokens, max_wait_time=max_wait_time)
                if not acquired:
                    raise Exception(f"Rate limit timeout for {endpoint} after {max_wait_time}s")
                    
            return await func(*args, **kwargs)
            
        return wrapper
    return decorator


# Global rate limit manager instance
_global_rate_limit_manager = OandaRateLimitManager()


def get_global_rate_limit_manager() -> OandaRateLimitManager:
    """Get global rate limit manager instance"""
    return _global_rate_limit_manager