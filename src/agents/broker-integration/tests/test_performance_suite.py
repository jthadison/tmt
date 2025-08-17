"""
Performance Test Suite for Broker Integration
Story 8.12 - Task 3: Build performance test suite (<100ms latency, 100 concurrent orders)
"""
import pytest
import asyncio
import time
import statistics
import logging
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

# Test imports
import sys
from pathlib import Path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from broker_adapter import (
    BrokerAdapter, UnifiedOrder, UnifiedPosition, UnifiedAccountSummary,
    OrderType, OrderSide, OrderState, PositionSide, TimeInForce,
    BrokerCapability, PriceTick, OrderResult
)
from unified_errors import StandardBrokerError, StandardErrorCode

logger = logging.getLogger(__name__)


class PerformanceTestAdapter(BrokerAdapter):
    """High-performance test adapter for performance testing"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._broker_name = "performance_test"
        self.latency_simulation = config.get('latency_ms', 0)
        self.failure_rate = config.get('failure_rate', 0.0)
        self.order_counter = 0
        self.concurrent_orders = 0
        self.max_concurrent_orders = config.get('max_concurrent', 1000)
        
        # Performance metrics
        self.order_latencies = []
        self.price_latencies = []
        self.throughput_metrics = []
        
    @property
    def broker_name(self) -> str:
        return self._broker_name
        
    @property
    def broker_display_name(self) -> str:
        return "Performance Test Adapter"
        
    @property
    def api_version(self) -> str:
        return "test_v1"
        
    @property
    def capabilities(self) -> set:
        return {
            BrokerCapability.MARKET_ORDERS,
            BrokerCapability.LIMIT_ORDERS,
            BrokerCapability.STOP_ORDERS,
            BrokerCapability.REAL_TIME_STREAMING,
            BrokerCapability.FRACTIONAL_UNITS
        }
        
    @property
    def supported_instruments(self) -> List[str]:
        return ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CHF"]
        
    @property
    def supported_order_types(self) -> List[OrderType]:
        return [OrderType.MARKET, OrderType.LIMIT, OrderType.STOP]
        
    async def _simulate_latency(self):
        """Simulate network latency"""
        if self.latency_simulation > 0:
            await asyncio.sleep(self.latency_simulation / 1000.0)
            
    async def _simulate_failure(self):
        """Simulate random failures"""
        if self.failure_rate > 0:
            import random
            if random.random() < self.failure_rate:
                raise StandardBrokerError(
                    error_code=StandardErrorCode.SERVER_ERROR,
                    message="Simulated server error"
                )
                
    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        await self._simulate_latency()
        return True
        
    async def disconnect(self) -> bool:
        return True
        
    async def health_check(self) -> Dict[str, Any]:
        start_time = time.perf_counter()
        await self._simulate_latency()
        end_time = time.perf_counter()
        
        return {
            'status': 'healthy',
            'latency_ms': (end_time - start_time) * 1000,
            'concurrent_orders': self.concurrent_orders,
            'total_orders': self.order_counter
        }
        
    async def get_broker_info(self):
        return {
            'name': self.broker_name,
            'display_name': self.broker_display_name,
            'version': self.api_version
        }
        
    async def get_account_summary(self, account_id: Optional[str] = None) -> UnifiedAccountSummary:
        await self._simulate_latency()
        
        return UnifiedAccountSummary(
            account_id=account_id or "test_account",
            account_name="Performance Test Account",
            currency="USD",
            balance=Decimal("1000000.00"),  # Large balance for testing
            available_margin=Decimal("950000.00"),
            used_margin=Decimal("50000.00"),
            unrealized_pl=Decimal("1000.00"),
            nav=Decimal("1001000.00")
        )
        
    async def get_accounts(self) -> List[UnifiedAccountSummary]:
        return [await self.get_account_summary()]
        
    async def place_order(self, order: UnifiedOrder) -> OrderResult:
        """High-performance order placement with metrics tracking"""
        start_time = time.perf_counter()
        
        try:
            # Track concurrent orders
            self.concurrent_orders += 1
            
            # Check concurrent order limit
            if self.concurrent_orders > self.max_concurrent_orders:
                raise StandardBrokerError(
                    error_code=StandardErrorCode.RATE_LIMITED,
                    message="Too many concurrent orders"
                )
                
            # Simulate failure
            await self._simulate_failure()
            
            # Simulate processing time
            await self._simulate_latency()
            
            # Generate order result
            self.order_counter += 1
            
            result = OrderResult(
                success=True,
                order_id=f"perf_order_{self.order_counter}",
                client_order_id=order.client_order_id,
                order_state=OrderState.FILLED,
                fill_price=Decimal("1.1000") + Decimal(str(self.order_counter * 0.0001)),
                filled_units=order.units,
                commission=Decimal("2.50"),
                transaction_id=f"perf_txn_{self.order_counter}"
            )
            
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            self.order_latencies.append(latency_ms)
            
            return result
            
        finally:
            self.concurrent_orders -= 1
            
    async def modify_order(self, order_id: str, modifications: Dict[str, Any]) -> OrderResult:
        await self._simulate_latency()
        return OrderResult(success=True, order_id=order_id)
        
    async def cancel_order(self, order_id: str, reason: Optional[str] = None) -> OrderResult:
        await self._simulate_latency()
        return OrderResult(success=True, order_id=order_id)
        
    async def get_order(self, order_id: str) -> Optional[UnifiedOrder]:
        await self._simulate_latency()
        return None
        
    async def get_orders(self, **kwargs) -> List[UnifiedOrder]:
        await self._simulate_latency()
        return []
        
    async def get_position(self, instrument: str, account_id: Optional[str] = None) -> Optional[UnifiedPosition]:
        await self._simulate_latency()
        return None
        
    async def get_positions(self, account_id: Optional[str] = None) -> List[UnifiedPosition]:
        await self._simulate_latency()
        return []
        
    async def close_position(self, instrument: str, units: Optional[Decimal] = None, account_id: Optional[str] = None) -> OrderResult:
        await self._simulate_latency()
        return OrderResult(success=True, order_id="close_order")
        
    async def get_current_price(self, instrument: str) -> Optional[PriceTick]:
        """High-performance price fetching with metrics tracking"""
        start_time = time.perf_counter()
        
        await self._simulate_latency()
        await self._simulate_failure()
        
        price = PriceTick(
            instrument=instrument,
            bid=Decimal("1.1000"),
            ask=Decimal("1.1002"),
            timestamp=datetime.now(timezone.utc)
        )
        
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000
        self.price_latencies.append(latency_ms)
        
        return price
        
    async def get_current_prices(self, instruments: List[str]) -> Dict[str, PriceTick]:
        if not instruments:
            raise ValueError("Instruments list is required and cannot be empty")
            
        prices = {}
        start_time = time.perf_counter()
        
        # Simulate batch price fetching
        await self._simulate_latency()
        
        for instrument in instruments:
            prices[instrument] = PriceTick(
                instrument=instrument,
                bid=Decimal("1.1000"),
                ask=Decimal("1.1002"),
                timestamp=datetime.now(timezone.utc)
            )
            
        end_time = time.perf_counter()
        batch_latency_ms = (end_time - start_time) * 1000
        self.price_latencies.append(batch_latency_ms)
        
        return prices
        
    async def stream_prices(self, instruments: List[str]):
        for instrument in instruments:
            yield await self.get_current_price(instrument)
            
    async def get_historical_data(self, **kwargs) -> List[Dict[str, Any]]:
        await self._simulate_latency()
        return []
        
    async def get_transactions(self, **kwargs) -> List[Dict[str, Any]]:
        await self._simulate_latency()
        return []
        
    def map_error(self, broker_error: Exception) -> StandardBrokerError:
        return StandardBrokerError(
            error_code=StandardErrorCode.UNKNOWN_ERROR,
            message=str(broker_error)
        )
        
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        return {
            'order_metrics': {
                'total_orders': len(self.order_latencies),
                'avg_latency_ms': statistics.mean(self.order_latencies) if self.order_latencies else 0,
                'min_latency_ms': min(self.order_latencies) if self.order_latencies else 0,
                'max_latency_ms': max(self.order_latencies) if self.order_latencies else 0,
                'p95_latency_ms': statistics.quantiles(self.order_latencies, n=20)[18] if len(self.order_latencies) >= 20 else 0,
                'p99_latency_ms': statistics.quantiles(self.order_latencies, n=100)[98] if len(self.order_latencies) >= 100 else 0
            },
            'price_metrics': {
                'total_requests': len(self.price_latencies),
                'avg_latency_ms': statistics.mean(self.price_latencies) if self.price_latencies else 0,
                'min_latency_ms': min(self.price_latencies) if self.price_latencies else 0,
                'max_latency_ms': max(self.price_latencies) if self.price_latencies else 0
            },
            'concurrent_metrics': {
                'max_concurrent_orders': self.max_concurrent_orders,
                'current_concurrent_orders': self.concurrent_orders
            }
        }
        
    def reset_metrics(self):
        """Reset performance metrics"""
        self.order_latencies.clear()
        self.price_latencies.clear()
        self.throughput_metrics.clear()
        self.order_counter = 0


class TestOrderLatencyPerformance:
    """Test order execution latency requirements"""
    
    @pytest.fixture
    def fast_adapter(self):
        """Adapter with minimal latency simulation"""
        return PerformanceTestAdapter({
            'latency_ms': 10,  # 10ms simulated latency
            'failure_rate': 0.0
        })
        
    @pytest.fixture
    def slow_adapter(self):
        """Adapter with higher latency simulation"""
        return PerformanceTestAdapter({
            'latency_ms': 50,  # 50ms simulated latency
            'failure_rate': 0.0
        })
        
    @pytest.mark.asyncio
    async def test_single_order_latency(self, fast_adapter):
        """Test single order execution latency < 100ms"""
        order = UnifiedOrder(
            order_id="latency_test_1",
            client_order_id="client_latency_1",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("1000")
        )
        
        start_time = time.perf_counter()
        result = await fast_adapter.place_order(order)
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        
        assert result.success is True
        assert latency_ms < 100, f"Order latency {latency_ms:.2f}ms exceeds 100ms target"
        
    @pytest.mark.asyncio
    async def test_batch_order_latency(self, fast_adapter):
        """Test batch order execution latency"""
        orders = []
        for i in range(10):
            orders.append(UnifiedOrder(
                order_id=f"batch_test_{i}",
                client_order_id=f"client_batch_{i}",
                instrument="EUR_USD",
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                units=Decimal("1000")
            ))
            
        start_time = time.perf_counter()
        
        # Execute orders concurrently
        tasks = [fast_adapter.place_order(order) for order in orders]
        results = await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        avg_latency_ms = total_time_ms / len(orders)
        
        assert all(result.success for result in results)
        assert avg_latency_ms < 100, f"Average order latency {avg_latency_ms:.2f}ms exceeds 100ms target"
        
    @pytest.mark.asyncio
    async def test_order_latency_statistics(self, fast_adapter):
        """Test order latency statistical analysis"""
        orders = []
        for i in range(50):
            orders.append(UnifiedOrder(
                order_id=f"stats_test_{i}",
                client_order_id=f"client_stats_{i}",
                instrument="EUR_USD",
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                units=Decimal("1000")
            ))
            
        # Execute orders
        tasks = [fast_adapter.place_order(order) for order in orders]
        results = await asyncio.gather(*tasks)
        
        metrics = fast_adapter.get_performance_metrics()
        order_metrics = metrics['order_metrics']
        
        assert all(result.success for result in results)
        assert order_metrics['total_orders'] == 50
        assert order_metrics['avg_latency_ms'] < 100
        assert order_metrics['max_latency_ms'] < 200  # Allow some variance
        assert order_metrics['p95_latency_ms'] < 150  # 95th percentile < 150ms


class TestConcurrentOrderHandling:
    """Test concurrent order handling capability"""
    
    @pytest.fixture
    def concurrent_adapter(self):
        """Adapter configured for concurrent testing"""
        return PerformanceTestAdapter({
            'latency_ms': 5,  # Low latency for concurrent testing
            'failure_rate': 0.02,  # 2% failure rate
            'max_concurrent': 200  # Allow up to 200 concurrent orders
        })
        
    @pytest.mark.asyncio
    async def test_100_concurrent_orders(self, concurrent_adapter):
        """Test handling 100 concurrent orders"""
        orders = []
        for i in range(100):
            orders.append(UnifiedOrder(
                order_id=f"concurrent_test_{i}",
                client_order_id=f"client_concurrent_{i}",
                instrument="EUR_USD",
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                units=Decimal("1000")
            ))
            
        start_time = time.perf_counter()
        
        # Execute all 100 orders concurrently
        tasks = [concurrent_adapter.place_order(order) for order in orders]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Analyze results
        successful_orders = [r for r in results if isinstance(r, OrderResult) and r.success]
        failed_orders = [r for r in results if isinstance(r, Exception)]
        
        throughput = len(successful_orders) / total_time
        
        assert len(successful_orders) >= 95, f"Only {len(successful_orders)}/100 orders succeeded"
        assert throughput >= 10, f"Throughput {throughput:.2f} orders/sec too low"
        assert total_time < 30, f"Total time {total_time:.2f}s too high for 100 orders"
        
    @pytest.mark.asyncio
    async def test_200_concurrent_orders(self, concurrent_adapter):
        """Test handling 200 concurrent orders"""
        orders = []
        for i in range(200):
            orders.append(UnifiedOrder(
                order_id=f"concurrent_200_test_{i}",
                client_order_id=f"client_200_concurrent_{i}",
                instrument="EUR_USD",
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                units=Decimal("500")  # Smaller size for stress test
            ))
            
        start_time = time.perf_counter()
        
        # Execute all 200 orders concurrently
        tasks = [concurrent_adapter.place_order(order) for order in orders]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Analyze results
        successful_orders = [r for r in results if isinstance(r, OrderResult) and r.success]
        rate_limited_orders = [
            r for r in results 
            if isinstance(r, StandardBrokerError) and r.error_code == StandardErrorCode.RATE_LIMITED
        ]
        
        throughput = len(successful_orders) / total_time
        
        assert len(successful_orders) >= 190, f"Only {len(successful_orders)}/200 orders succeeded"
        assert throughput >= 8, f"Throughput {throughput:.2f} orders/sec too low for 200 orders"
        
    @pytest.mark.asyncio
    async def test_concurrent_order_bursts(self, concurrent_adapter):
        """Test handling bursts of concurrent orders"""
        burst_size = 50
        num_bursts = 3
        burst_interval = 0.1  # 100ms between bursts
        
        all_results = []
        burst_times = []
        
        for burst in range(num_bursts):
            orders = []
            for i in range(burst_size):
                orders.append(UnifiedOrder(
                    order_id=f"burst_{burst}_order_{i}",
                    client_order_id=f"client_burst_{burst}_{i}",
                    instrument="EUR_USD",
                    order_type=OrderType.MARKET,
                    side=OrderSide.BUY,
                    units=Decimal("1000")
                ))
                
            burst_start = time.perf_counter()
            
            # Execute burst
            tasks = [concurrent_adapter.place_order(order) for order in orders]
            burst_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            burst_end = time.perf_counter()
            burst_time = burst_end - burst_start
            
            all_results.extend(burst_results)
            burst_times.append(burst_time)
            
            # Wait before next burst
            if burst < num_bursts - 1:
                await asyncio.sleep(burst_interval)
                
        # Analyze overall results
        successful_orders = [r for r in all_results if isinstance(r, OrderResult) and r.success]
        total_orders = burst_size * num_bursts
        
        assert len(successful_orders) >= total_orders * 0.95, f"Only {len(successful_orders)}/{total_orders} orders succeeded across all bursts"
        assert all(burst_time < 10 for burst_time in burst_times), f"Some bursts took too long: {burst_times}"


class TestPriceFeedPerformance:
    """Test price feed performance"""
    
    @pytest.fixture
    def price_adapter(self):
        """Adapter optimized for price feed testing"""
        return PerformanceTestAdapter({
            'latency_ms': 2,  # Very low latency for price feeds
            'failure_rate': 0.001  # Minimal failure rate
        })
        
    @pytest.mark.asyncio
    async def test_single_price_latency(self, price_adapter):
        """Test single price fetch latency"""
        start_time = time.perf_counter()
        price = await price_adapter.get_current_price("EUR_USD")
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        
        assert price is not None
        assert latency_ms < 50, f"Price fetch latency {latency_ms:.2f}ms too high"
        
    @pytest.mark.asyncio
    async def test_batch_price_latency(self, price_adapter):
        """Test batch price fetch latency"""
        instruments = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CHF"]
        
        start_time = time.perf_counter()
        prices = await price_adapter.get_current_prices(instruments)
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        
        assert len(prices) == len(instruments)
        assert latency_ms < 100, f"Batch price fetch latency {latency_ms:.2f}ms too high"
        
    @pytest.mark.asyncio
    async def test_concurrent_price_requests(self, price_adapter):
        """Test concurrent price requests"""
        instruments = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CHF"]
        num_concurrent = 20
        
        start_time = time.perf_counter()
        
        # Create concurrent price requests
        tasks = []
        for i in range(num_concurrent):
            instrument = instruments[i % len(instruments)]
            tasks.append(price_adapter.get_current_price(instrument))
            
        prices = await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        successful_prices = [p for p in prices if p is not None]
        
        assert len(successful_prices) >= num_concurrent * 0.95
        assert total_time < 5, f"Concurrent price requests took {total_time:.2f}s"
        
    @pytest.mark.asyncio
    async def test_price_feed_throughput(self, price_adapter):
        """Test price feed throughput"""
        num_requests = 100
        
        start_time = time.perf_counter()
        
        # Sequential price requests to measure throughput
        for i in range(num_requests):
            await price_adapter.get_current_price("EUR_USD")
            
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        throughput = num_requests / total_time
        
        assert throughput >= 20, f"Price feed throughput {throughput:.2f} requests/sec too low"


class TestThroughputBenchmarks:
    """Test overall system throughput benchmarks"""
    
    @pytest.fixture
    def benchmark_adapter(self):
        """Adapter for benchmark testing"""
        return PerformanceTestAdapter({
            'latency_ms': 8,  # Realistic latency
            'failure_rate': 0.01,  # 1% failure rate
            'max_concurrent': 500
        })
        
    @pytest.mark.asyncio
    async def test_sustained_throughput(self, benchmark_adapter):
        """Test sustained order throughput over time"""
        duration_seconds = 5
        target_rate = 50  # orders per second
        total_orders = duration_seconds * target_rate
        
        orders = []
        for i in range(total_orders):
            orders.append(UnifiedOrder(
                order_id=f"sustained_test_{i}",
                client_order_id=f"client_sustained_{i}",
                instrument="EUR_USD",
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                units=Decimal("1000")
            ))
            
        start_time = time.perf_counter()
        
        # Execute orders with rate limiting
        tasks = []
        for i, order in enumerate(orders):
            # Stagger order submissions to maintain rate
            if i > 0 and i % 10 == 0:
                await asyncio.sleep(0.2)  # Brief pause every 10 orders
            tasks.append(benchmark_adapter.place_order(order))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.perf_counter()
        actual_duration = end_time - start_time
        
        successful_orders = [r for r in results if isinstance(r, OrderResult) and r.success]
        actual_rate = len(successful_orders) / actual_duration
        
        assert len(successful_orders) >= total_orders * 0.95
        assert actual_rate >= target_rate * 0.8, f"Actual rate {actual_rate:.2f} orders/sec below target"
        
    @pytest.mark.asyncio
    async def test_peak_throughput(self, benchmark_adapter):
        """Test peak throughput capability"""
        num_orders = 300
        
        orders = []
        for i in range(num_orders):
            orders.append(UnifiedOrder(
                order_id=f"peak_test_{i}",
                client_order_id=f"client_peak_{i}",
                instrument="EUR_USD",
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                units=Decimal("500")
            ))
            
        start_time = time.perf_counter()
        
        # Execute all orders as fast as possible
        tasks = [benchmark_adapter.place_order(order) for order in orders]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        successful_orders = [r for r in results if isinstance(r, OrderResult) and r.success]
        peak_throughput = len(successful_orders) / total_time
        
        assert len(successful_orders) >= num_orders * 0.9
        assert peak_throughput >= 30, f"Peak throughput {peak_throughput:.2f} orders/sec too low"


class TestPerformanceRegression:
    """Test for performance regressions"""
    
    @pytest.fixture
    def baseline_adapter(self):
        """Baseline adapter for regression testing"""
        return PerformanceTestAdapter({
            'latency_ms': 5,
            'failure_rate': 0.0
        })
        
    @pytest.mark.asyncio
    async def test_performance_regression_detection(self, baseline_adapter):
        """Test that performance hasn't regressed"""
        # Baseline measurements
        baseline_orders = 50
        orders = []
        
        for i in range(baseline_orders):
            orders.append(UnifiedOrder(
                order_id=f"regression_test_{i}",
                client_order_id=f"client_regression_{i}",
                instrument="EUR_USD",
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                units=Decimal("1000")
            ))
            
        # Measure performance
        start_time = time.perf_counter()
        tasks = [baseline_adapter.place_order(order) for order in orders]
        results = await asyncio.gather(*tasks)
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        avg_latency = total_time / baseline_orders * 1000  # Convert to ms
        throughput = baseline_orders / total_time
        
        metrics = baseline_adapter.get_performance_metrics()
        
        # Performance assertions (these would be compared against historical baselines)
        assert avg_latency < 50, f"Average latency {avg_latency:.2f}ms exceeds baseline"
        assert throughput > 20, f"Throughput {throughput:.2f} orders/sec below baseline"
        assert metrics['order_metrics']['max_latency_ms'] < 100, "Max latency exceeds baseline"
        assert all(result.success for result in results), "Some orders failed unexpectedly"
        
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, baseline_adapter):
        """Test that memory usage remains stable under load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate load
        for batch in range(5):
            orders = []
            for i in range(20):
                orders.append(UnifiedOrder(
                    order_id=f"memory_test_{batch}_{i}",
                    client_order_id=f"client_memory_{batch}_{i}",
                    instrument="EUR_USD",
                    order_type=OrderType.MARKET,
                    side=OrderSide.BUY,
                    units=Decimal("1000")
                ))
                
            tasks = [baseline_adapter.place_order(order) for order in orders]
            await asyncio.gather(*tasks)
            
            # Reset metrics to prevent accumulation
            baseline_adapter.reset_metrics()
            
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory should not increase significantly (allow 50MB increase)
        assert memory_increase < 50, f"Memory increased by {memory_increase:.2f}MB during testing"


if __name__ == "__main__":
    # Run performance tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--durations=10"  # Show 10 slowest tests
    ])