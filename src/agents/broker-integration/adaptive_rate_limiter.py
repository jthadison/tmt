"""
Adaptive Rate Limiting System
Future Enhancement: Dynamic rate adjustment based on API response patterns
"""
import asyncio
import logging
import time
import statistics
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from collections import deque

from rate_limiter import TokenBucketRateLimiter, RateLimitResult, OandaRateLimitManager

logger = logging.getLogger(__name__)


class AdaptiveStrategy(Enum):
    """Adaptive rate limiting strategies"""
    CONSERVATIVE = "conservative"  # Reduce rate on any errors
    AGGRESSIVE = "aggressive"      # Push limits until rate limited
    BALANCED = "balanced"          # Balance between throughput and stability
    ML_PREDICTED = "ml_predicted"  # Use ML predictions


@dataclass
class APIResponseMetrics:
    """Metrics from API responses for adaptive adjustment"""
    endpoint: str
    timestamp: datetime
    response_time_ms: float
    status_code: int
    rate_limit_remaining: Optional[int] = None
    rate_limit_reset: Optional[datetime] = None
    error_type: Optional[str] = None
    success: bool = True
    
    def to_dict(self) -> Dict:
        return {
            'endpoint': self.endpoint,
            'timestamp': self.timestamp.isoformat(),
            'response_time_ms': self.response_time_ms,
            'status_code': self.status_code,
            'rate_limit_remaining': self.rate_limit_remaining,
            'rate_limit_reset': self.rate_limit_reset.isoformat() if self.rate_limit_reset else None,
            'error_type': self.error_type,
            'success': self.success
        }


@dataclass
class AdaptiveRateConfig:
    """Configuration for adaptive rate limiting"""
    min_rate: float = 1.0          # Minimum requests per second
    max_rate: float = 1000.0       # Maximum requests per second
    adjustment_factor: float = 0.1  # How aggressively to adjust (0.1 = 10%)
    measurement_window: int = 60    # Seconds to analyze for adjustments
    error_threshold: float = 0.05   # Error rate threshold (5%)
    latency_threshold: float = 1000.0  # Latency threshold in ms
    strategy: AdaptiveStrategy = AdaptiveStrategy.BALANCED


class AdaptiveTokenBucketRateLimiter(TokenBucketRateLimiter):
    """Rate limiter with adaptive rate adjustment capabilities"""
    
    def __init__(self, 
                 initial_rate: float = 100.0,
                 burst_capacity: int = 100,
                 name: str = "adaptive",
                 adaptive_config: Optional[AdaptiveRateConfig] = None):
        super().__init__(initial_rate, burst_capacity, name)
        self.adaptive_config = adaptive_config or AdaptiveRateConfig()
        self.initial_rate = initial_rate
        
        # Metrics collection
        self.response_metrics: deque = deque(maxlen=1000)
        self.rate_adjustments: List[Dict] = []
        self.last_adjustment = datetime.now(timezone.utc)
        self.adjustment_cooldown = timedelta(seconds=30)  # Min time between adjustments
        
        # Performance tracking
        self.current_error_rate = 0.0
        self.current_avg_latency = 0.0
        self.throughput_history: deque = deque(maxlen=100)
        
    async def record_api_response(self, response_metrics: APIResponseMetrics):
        """Record API response metrics for adaptive learning"""
        self.response_metrics.append(response_metrics)
        
        # Update current metrics
        await self._update_current_metrics()
        
        # Check if we should adjust the rate
        if await self._should_adjust_rate():
            await self._adjust_rate()
            
    async def _update_current_metrics(self):
        """Update current performance metrics"""
        if not self.response_metrics:
            return
            
        # Calculate metrics for the measurement window
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=self.adaptive_config.measurement_window)
        
        recent_metrics = [
            m for m in self.response_metrics 
            if m.timestamp >= window_start
        ]
        
        if not recent_metrics:
            return
            
        # Calculate error rate
        total_requests = len(recent_metrics)
        error_count = sum(1 for m in recent_metrics if not m.success)
        self.current_error_rate = error_count / total_requests if total_requests > 0 else 0
        
        # Calculate average latency
        latencies = [m.response_time_ms for m in recent_metrics if m.success]
        self.current_avg_latency = statistics.mean(latencies) if latencies else 0
        
        # Track throughput
        self.throughput_history.append({
            'timestamp': now,
            'requests_per_minute': total_requests,
            'error_rate': self.current_error_rate,
            'avg_latency': self.current_avg_latency
        })
        
    async def _should_adjust_rate(self) -> bool:
        """Determine if rate should be adjusted"""
        now = datetime.now(timezone.utc)
        
        # Cooldown check
        if now - self.last_adjustment < self.adjustment_cooldown:
            return False
            
        # Need sufficient data
        if len(self.response_metrics) < 10:
            return False
            
        # Check if metrics indicate need for adjustment
        config = self.adaptive_config
        
        if self.current_error_rate > config.error_threshold:
            return True  # Too many errors, reduce rate
            
        if self.current_avg_latency > config.latency_threshold:
            return True  # High latency, reduce rate
            
        # Check for opportunity to increase rate
        if (self.current_error_rate < config.error_threshold / 2 and 
            self.current_avg_latency < config.latency_threshold / 2):
            return True  # Good performance, try increasing rate
            
        return False
        
    async def _adjust_rate(self):
        """Adjust the rate based on current metrics and strategy"""
        config = self.adaptive_config
        old_rate = self.rate
        
        # Determine adjustment direction and magnitude
        adjustment = 0.0
        reason = ""
        
        if self.current_error_rate > config.error_threshold:
            # Reduce rate due to errors
            adjustment = -config.adjustment_factor * (self.current_error_rate / config.error_threshold)
            reason = f"High error rate: {self.current_error_rate:.3f}"
            
        elif self.current_avg_latency > config.latency_threshold:
            # Reduce rate due to latency
            latency_factor = self.current_avg_latency / config.latency_threshold
            adjustment = -config.adjustment_factor * latency_factor
            reason = f"High latency: {self.current_avg_latency:.1f}ms"
            
        elif (self.current_error_rate < config.error_threshold / 2 and 
              self.current_avg_latency < config.latency_threshold / 2):
            # Increase rate due to good performance
            if config.strategy == AdaptiveStrategy.AGGRESSIVE:
                adjustment = config.adjustment_factor * 2
            elif config.strategy == AdaptiveStrategy.CONSERVATIVE:
                adjustment = config.adjustment_factor * 0.5
            else:  # BALANCED
                adjustment = config.adjustment_factor
            reason = f"Good performance - Error: {self.current_error_rate:.3f}, Latency: {self.current_avg_latency:.1f}ms"
            
        # Apply adjustment with bounds
        if adjustment != 0:
            new_rate = old_rate * (1 + adjustment)
            new_rate = max(config.min_rate, min(config.max_rate, new_rate))
            
            if abs(new_rate - old_rate) > 0.1:  # Only adjust if significant change
                self.rate = new_rate
                self.last_adjustment = datetime.now(timezone.utc)
                
                # Record adjustment
                adjustment_record = {
                    'timestamp': self.last_adjustment,
                    'old_rate': old_rate,
                    'new_rate': new_rate,
                    'adjustment_factor': adjustment,
                    'reason': reason,
                    'error_rate': self.current_error_rate,
                    'avg_latency': self.current_avg_latency
                }
                self.rate_adjustments.append(adjustment_record)
                
                logger.info(f"Adaptive rate adjustment: {old_rate:.1f} -> {new_rate:.1f} req/s ({reason})")
                
    def get_adaptive_metrics(self) -> Dict[str, Any]:
        """Get adaptive rate limiting metrics"""
        return {
            'current_rate': self.rate,
            'initial_rate': self.initial_rate,
            'current_error_rate': self.current_error_rate,
            'current_avg_latency': self.current_avg_latency,
            'total_adjustments': len(self.rate_adjustments),
            'recent_adjustments': self.rate_adjustments[-10:],  # Last 10 adjustments
            'throughput_history': list(self.throughput_history),
            'adaptive_config': {
                'strategy': self.adaptive_config.strategy.value,
                'min_rate': self.adaptive_config.min_rate,
                'max_rate': self.adaptive_config.max_rate,
                'adjustment_factor': self.adaptive_config.adjustment_factor
            }
        }
        
    async def predict_optimal_rate(self) -> float:
        """Predict optimal rate based on historical data"""
        if len(self.throughput_history) < 5:
            return self.rate
            
        # Simple ML-like prediction based on historical patterns
        recent_performance = list(self.throughput_history)[-10:]
        
        # Find the rate that gave the best throughput with acceptable error rate
        best_throughput = 0
        best_rate = self.rate
        
        for perf in recent_performance:
            if perf['error_rate'] <= self.adaptive_config.error_threshold:
                effective_throughput = perf['requests_per_minute'] * (1 - perf['error_rate'])
                if effective_throughput > best_throughput:
                    best_throughput = effective_throughput
                    # Estimate rate from throughput (simplified)
                    best_rate = effective_throughput / 60  # Convert to per-second
                    
        return min(self.adaptive_config.max_rate, max(self.adaptive_config.min_rate, best_rate))
        
    async def reset_to_baseline(self):
        """Reset rate to initial baseline"""
        old_rate = self.rate
        self.rate = self.initial_rate
        self.last_adjustment = datetime.now(timezone.utc)
        
        adjustment_record = {
            'timestamp': self.last_adjustment,
            'old_rate': old_rate,
            'new_rate': self.rate,
            'adjustment_factor': 0,
            'reason': 'Manual reset to baseline',
            'error_rate': self.current_error_rate,
            'avg_latency': self.current_avg_latency
        }
        self.rate_adjustments.append(adjustment_record)
        
        logger.info(f"Rate reset to baseline: {old_rate:.1f} -> {self.rate:.1f} req/s")


class AdaptiveOandaRateLimitManager(OandaRateLimitManager):
    """OANDA rate limit manager with adaptive capabilities"""
    
    def __init__(self):
        super().__init__()
        
        # Replace static limiters with adaptive ones
        self.adaptive_limiters: Dict[str, AdaptiveTokenBucketRateLimiter] = {}
        
        # Create adaptive limiters for key endpoints
        self._create_adaptive_limiters()
        
    def _create_adaptive_limiters(self):
        """Create adaptive rate limiters for endpoints"""
        # Different strategies for different endpoint types
        configs = {
            'pricing': AdaptiveRateConfig(
                min_rate=50.0, max_rate=500.0,
                strategy=AdaptiveStrategy.AGGRESSIVE,
                adjustment_factor=0.15
            ),
            'orders': AdaptiveRateConfig(
                min_rate=10.0, max_rate=200.0,
                strategy=AdaptiveStrategy.CONSERVATIVE,
                adjustment_factor=0.05
            ),
            'transactions': AdaptiveRateConfig(
                min_rate=5.0, max_rate=100.0,
                strategy=AdaptiveStrategy.BALANCED,
                adjustment_factor=0.1
            ),
            'accounts': AdaptiveRateConfig(
                min_rate=1.0, max_rate=50.0,
                strategy=AdaptiveStrategy.CONSERVATIVE,
                adjustment_factor=0.05
            )
        }
        
        for endpoint, config in configs.items():
            initial_rate = self.limiters[endpoint].rate if endpoint in self.limiters else 100.0
            self.adaptive_limiters[endpoint] = AdaptiveTokenBucketRateLimiter(
                initial_rate=initial_rate,
                burst_capacity=int(initial_rate),
                name=f"adaptive_{endpoint}",
                adaptive_config=config
            )
            
        # Replace in main limiters dict
        self.limiters.update(self.adaptive_limiters)
        
    async def record_api_response(self, 
                                endpoint: str,
                                response_time_ms: float,
                                status_code: int,
                                success: bool = True,
                                error_type: Optional[str] = None,
                                rate_limit_remaining: Optional[int] = None):
        """Record API response for adaptive learning"""
        if endpoint in self.adaptive_limiters:
            metrics = APIResponseMetrics(
                endpoint=endpoint,
                timestamp=datetime.now(timezone.utc),
                response_time_ms=response_time_ms,
                status_code=status_code,
                success=success,
                error_type=error_type,
                rate_limit_remaining=rate_limit_remaining
            )
            
            await self.adaptive_limiters[endpoint].record_api_response(metrics)
            
    async def optimize_all_rates(self):
        """Optimize rates for all adaptive limiters"""
        for endpoint, limiter in self.adaptive_limiters.items():
            optimal_rate = await limiter.predict_optimal_rate()
            if abs(optimal_rate - limiter.rate) > limiter.rate * 0.1:  # 10% difference threshold
                logger.info(f"Optimizing {endpoint} rate: {limiter.rate:.1f} -> {optimal_rate:.1f}")
                limiter.rate = optimal_rate
                
    def get_adaptive_status(self) -> Dict[str, Any]:
        """Get status of all adaptive limiters"""
        return {
            endpoint: limiter.get_adaptive_metrics()
            for endpoint, limiter in self.adaptive_limiters.items()
        }
        
    async def enable_ml_predictions(self):
        """Enable ML-based rate predictions for all limiters"""
        for limiter in self.adaptive_limiters.values():
            limiter.adaptive_config.strategy = AdaptiveStrategy.ML_PREDICTED
            
    async def set_strategy_for_endpoint(self, endpoint: str, strategy: AdaptiveStrategy):
        """Set adaptive strategy for specific endpoint"""
        if endpoint in self.adaptive_limiters:
            self.adaptive_limiters[endpoint].adaptive_config.strategy = strategy
            logger.info(f"Set {endpoint} adaptive strategy to {strategy.value}")


# Context manager for automatic response recording
class AdaptiveRateLimitContext:
    """Context manager for automatic API response recording"""
    
    def __init__(self, 
                 rate_manager: AdaptiveOandaRateLimitManager,
                 endpoint: str,
                 expected_success: bool = True):
        self.rate_manager = rate_manager
        self.endpoint = endpoint
        self.expected_success = expected_success
        self.start_time = None
        
    async def __aenter__(self):
        self.start_time = time.perf_counter()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            response_time = (time.perf_counter() - self.start_time) * 1000
            
            success = exc_type is None and self.expected_success
            status_code = 200 if success else 500
            error_type = exc_type.__name__ if exc_type else None
            
            await self.rate_manager.record_api_response(
                endpoint=self.endpoint,
                response_time_ms=response_time,
                status_code=status_code,
                success=success,
                error_type=error_type
            )


# Decorator for automatic adaptive rate limiting
def adaptive_rate_limited(endpoint: str, 
                         tokens: int = 1,
                         max_wait_time: float = 30.0):
    """Decorator for adaptive rate limiting with automatic response recording"""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get or create adaptive rate limit manager
            if hasattr(args[0], '_adaptive_rate_manager'):
                manager = args[0]._adaptive_rate_manager
            else:
                manager = AdaptiveOandaRateLimitManager()
                args[0]._adaptive_rate_manager = manager
                
            # Check rate limit
            acquired = await manager.acquire_with_wait(endpoint, tokens, max_wait_time=max_wait_time)
            if not acquired:
                raise Exception(f"Adaptive rate limit timeout for {endpoint} after {max_wait_time}s")
                
            # Execute with response recording
            async with AdaptiveRateLimitContext(manager, endpoint):
                return await func(*args, **kwargs)
                
        return wrapper
    return decorator


# Global adaptive rate limit manager instance
_global_adaptive_rate_manager = AdaptiveOandaRateLimitManager()


def get_global_adaptive_rate_manager() -> AdaptiveOandaRateLimitManager:
    """Get global adaptive rate limit manager instance"""
    return _global_adaptive_rate_manager