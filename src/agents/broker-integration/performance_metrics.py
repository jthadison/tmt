"""
Performance Metrics Comparison System
Story 8.10 - Task 6: Implement performance metrics comparison (AC8)
"""
import asyncio
import logging
import statistics
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from decimal import Decimal
import json
import numpy as np

try:
    from .broker_adapter import BrokerAdapter, OrderResult, UnifiedOrder, PriceTick
    from .ab_testing_framework import MetricType, OrderExecution
    from .unified_errors import StandardBrokerError
except ImportError:
    from broker_adapter import BrokerAdapter, OrderResult, UnifiedOrder, PriceTick
    from ab_testing_framework import MetricType, OrderExecution
    from unified_errors import StandardBrokerError

logger = logging.getLogger(__name__)


class BenchmarkType(Enum):
    """Types of performance benchmarks"""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    RELIABILITY = "reliability"
    COST = "cost"
    ACCURACY = "accuracy"
    AVAILABILITY = "availability"


class ComparisonPeriod(Enum):
    """Time periods for comparison"""
    LAST_HOUR = "last_hour"
    LAST_DAY = "last_day"
    LAST_WEEK = "last_week"
    LAST_MONTH = "last_month"
    CUSTOM = "custom"


@dataclass
class MetricSnapshot:
    """Performance metric snapshot at a point in time"""
    broker_name: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    sample_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'broker_name': self.broker_name,
            'metric_type': self.metric_type.value,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'sample_count': self.sample_count,
            'metadata': self.metadata
        }


@dataclass
class BrokerBenchmark:
    """Comprehensive performance benchmark for a broker"""
    broker_name: str
    benchmark_timestamp: datetime
    
    # Latency metrics (milliseconds)
    avg_order_latency: float
    p95_order_latency: float
    p99_order_latency: float
    avg_price_feed_latency: float
    
    # Throughput metrics (per second)
    max_orders_per_second: float
    avg_orders_per_second: float
    max_price_updates_per_second: float
    
    # Reliability metrics (percentages)
    uptime_percentage: float
    success_rate: float
    error_rate: float
    connection_stability: float
    
    # Cost metrics
    avg_commission_per_trade: float
    avg_spread: float
    total_fees: float
    
    # Accuracy metrics
    price_accuracy_score: float
    execution_accuracy_score: float
    slippage_average: float
    
    # Additional metrics
    market_data_coverage: float
    instrument_availability: int
    api_feature_completeness: float
    
    # Derived scores (0-100)
    overall_performance_score: float
    cost_efficiency_score: float
    reliability_score: float
    speed_score: float
    
    sample_size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BrokerComparison:
    """Comparison between multiple brokers"""
    comparison_id: str
    broker_names: List[str]
    comparison_period: ComparisonPeriod
    start_time: datetime
    end_time: datetime
    benchmarks: Dict[str, BrokerBenchmark]  # broker_name -> benchmark
    rankings: Dict[BenchmarkType, List[Tuple[str, float]]]  # type -> [(broker, score), ...]
    recommendations: List[str]
    winner: Optional[str] = None
    confidence_level: float = 0.95
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'comparison_id': self.comparison_id,
            'broker_names': self.broker_names,
            'comparison_period': self.comparison_period.value,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'benchmarks': {name: benchmark.to_dict() for name, benchmark in self.benchmarks.items()},
            'rankings': {
                benchmark_type.value: rankings 
                for benchmark_type, rankings in self.rankings.items()
            },
            'recommendations': self.recommendations,
            'winner': self.winner,
            'confidence_level': self.confidence_level,
            'metadata': self.metadata
        }


class PerformanceMetricsCollector:
    """Collects and analyzes broker performance metrics"""
    
    def __init__(self):
        self.broker_adapters: Dict[str, BrokerAdapter] = {}
        self.metric_history: Dict[str, List[MetricSnapshot]] = {}  # broker_name -> snapshots
        self.execution_history: Dict[str, List[OrderExecution]] = {}  # broker_name -> executions
        self.price_feed_history: Dict[str, List[Tuple[datetime, float]]] = {}  # broker_name -> (timestamp, latency)
        
        # Collection settings
        self.max_history_size = 10000
        self.collection_interval = 60  # seconds
        self.benchmark_interval = 3600  # 1 hour
        
        # Performance thresholds
        self.latency_thresholds = {
            'excellent': 100,  # ms
            'good': 500,
            'acceptable': 1000,
            'poor': 2000
        }
        
        self.success_rate_thresholds = {
            'excellent': 0.999,  # 99.9%
            'good': 0.995,
            'acceptable': 0.99,
            'poor': 0.95
        }
        
        # Background collection task
        self._collection_task: Optional[asyncio.Task] = None
        
    def register_broker(self, broker_name: str, adapter: BrokerAdapter):
        """Register broker for performance monitoring"""
        self.broker_adapters[broker_name] = adapter
        if broker_name not in self.metric_history:
            self.metric_history[broker_name] = []
            self.execution_history[broker_name] = []
            self.price_feed_history[broker_name] = []
        logger.info(f"Registered broker for performance monitoring: {broker_name}")
        
    def start_collection(self):
        """Start background metric collection"""
        if self._collection_task is None or self._collection_task.done():
            self._collection_task = asyncio.create_task(self._collection_loop())
            logger.info("Started performance metrics collection")
            
    def stop_collection(self):
        """Stop background metric collection"""
        if self._collection_task and not self._collection_task.done():
            self._collection_task.cancel()
            logger.info("Stopped performance metrics collection")
            
    async def _collection_loop(self):
        """Background loop for collecting metrics"""
        while True:
            try:
                await asyncio.sleep(self.collection_interval)
                await self._collect_all_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(60)  # Wait before retrying
                
    async def _collect_all_metrics(self):
        """Collect metrics from all registered brokers"""
        for broker_name, adapter in self.broker_adapters.items():
            try:
                await self._collect_broker_metrics(broker_name, adapter)
            except Exception as e:
                logger.error(f"Failed to collect metrics for {broker_name}: {e}")
                
    async def _collect_broker_metrics(self, broker_name: str, adapter: BrokerAdapter):
        """Collect performance metrics for a specific broker"""
        timestamp = datetime.now(timezone.utc)
        
        # Test latency with health check
        latency_start = datetime.now()
        try:
            health_status = await asyncio.wait_for(adapter.health_check(), timeout=30)
            latency_ms = (datetime.now() - latency_start).total_seconds() * 1000
            
            # Record latency metric
            self._add_metric_snapshot(
                broker_name,
                MetricSnapshot(
                    broker_name=broker_name,
                    metric_type=MetricType.LATENCY,
                    value=latency_ms,
                    timestamp=timestamp,
                    sample_count=1,
                    metadata={'test_type': 'health_check'}
                )
            )
            
            # Record availability
            availability = 1.0 if health_status.get('status') == 'healthy' else 0.0
            self._add_metric_snapshot(
                broker_name,
                MetricSnapshot(
                    broker_name=broker_name,
                    metric_type=MetricType.AVAILABILITY,
                    value=availability,
                    timestamp=timestamp,
                    sample_count=1
                )
            )
            
        except asyncio.TimeoutError:
            # Record timeout as high latency and unavailability
            self._add_metric_snapshot(
                broker_name,
                MetricSnapshot(
                    broker_name=broker_name,
                    metric_type=MetricType.LATENCY,
                    value=30000,  # 30 second timeout
                    timestamp=timestamp,
                    sample_count=1,
                    metadata={'test_type': 'timeout'}
                )
            )
            
            self._add_metric_snapshot(
                broker_name,
                MetricSnapshot(
                    broker_name=broker_name,
                    metric_type=MetricType.AVAILABILITY,
                    value=0.0,
                    timestamp=timestamp,
                    sample_count=1
                )
            )
            
        # Test price feed latency
        await self._test_price_feed_latency(broker_name, adapter)
        
        # Calculate success/error rates from recent executions
        self._calculate_reliability_metrics(broker_name, timestamp)
        
    async def _test_price_feed_latency(self, broker_name: str, adapter: BrokerAdapter):
        """Test price feed latency"""
        try:
            # Get supported instruments
            instruments = adapter.supported_instruments
            if not instruments:
                return
                
            test_instrument = instruments[0]  # Use first available instrument
            
            # Test price feed latency
            price_start = datetime.now()
            price_tick = await asyncio.wait_for(
                adapter.get_current_price(test_instrument), 
                timeout=10
            )
            
            if price_tick:
                latency_ms = (datetime.now() - price_start).total_seconds() * 1000
                self.price_feed_history[broker_name].append((datetime.now(timezone.utc), latency_ms))
                
                # Keep history bounded
                if len(self.price_feed_history[broker_name]) > self.max_history_size:
                    self.price_feed_history[broker_name] = self.price_feed_history[broker_name][-self.max_history_size:]
                    
        except Exception as e:
            logger.debug(f"Price feed test failed for {broker_name}: {e}")
            
    def _calculate_reliability_metrics(self, broker_name: str, timestamp: datetime):
        """Calculate reliability metrics from execution history"""
        executions = self.execution_history[broker_name]
        
        # Get recent executions (last hour)
        recent_cutoff = timestamp - timedelta(hours=1)
        recent_executions = [
            exec for exec in executions 
            if exec.execution_time >= recent_cutoff
        ]
        
        if not recent_executions:
            return
            
        # Calculate success rate
        success_count = sum(1 for exec in recent_executions if exec.success)
        success_rate = success_count / len(recent_executions)
        
        self._add_metric_snapshot(
            broker_name,
            MetricSnapshot(
                broker_name=broker_name,
                metric_type=MetricType.SUCCESS_RATE,
                value=success_rate,
                timestamp=timestamp,
                sample_count=len(recent_executions)
            )
        )
        
        # Calculate error rate
        error_rate = 1.0 - success_rate
        self._add_metric_snapshot(
            broker_name,
            MetricSnapshot(
                broker_name=broker_name,
                metric_type=MetricType.ERROR_RATE,
                value=error_rate,
                timestamp=timestamp,
                sample_count=len(recent_executions)
            )
        )
        
        # Calculate throughput
        if len(recent_executions) > 0:
            time_span = (recent_executions[-1].execution_time - recent_executions[0].execution_time).total_seconds()
            if time_span > 0:
                throughput = len(recent_executions) / time_span
                self._add_metric_snapshot(
                    broker_name,
                    MetricSnapshot(
                        broker_name=broker_name,
                        metric_type=MetricType.THROUGHPUT,
                        value=throughput,
                        timestamp=timestamp,
                        sample_count=len(recent_executions)
                    )
                )
                
    def _add_metric_snapshot(self, broker_name: str, snapshot: MetricSnapshot):
        """Add metric snapshot to history"""
        self.metric_history[broker_name].append(snapshot)
        
        # Keep history bounded
        if len(self.metric_history[broker_name]) > self.max_history_size:
            self.metric_history[broker_name] = self.metric_history[broker_name][-self.max_history_size:]
            
    def record_execution(self, execution: OrderExecution):
        """Record order execution for metrics"""
        broker_name = execution.broker_name
        if broker_name in self.execution_history:
            self.execution_history[broker_name].append(execution)
            
            # Keep history bounded
            if len(self.execution_history[broker_name]) > self.max_history_size:
                self.execution_history[broker_name] = self.execution_history[broker_name][-self.max_history_size:]
                
    async def generate_broker_benchmark(self, 
                                       broker_name: str,
                                       period: ComparisonPeriod = ComparisonPeriod.LAST_DAY) -> BrokerBenchmark:
        """
        Generate comprehensive benchmark for a broker
        
        Args:
            broker_name: Name of broker to benchmark
            period: Time period for analysis
            
        Returns:
            BrokerBenchmark with performance metrics
        """
        if broker_name not in self.broker_adapters:
            raise ValueError(f"Broker {broker_name} not registered")
            
        # Determine time range
        end_time = datetime.now(timezone.utc)
        if period == ComparisonPeriod.LAST_HOUR:
            start_time = end_time - timedelta(hours=1)
        elif period == ComparisonPeriod.LAST_DAY:
            start_time = end_time - timedelta(days=1)
        elif period == ComparisonPeriod.LAST_WEEK:
            start_time = end_time - timedelta(weeks=1)
        elif period == ComparisonPeriod.LAST_MONTH:
            start_time = end_time - timedelta(days=30)
        else:
            start_time = end_time - timedelta(days=1)  # Default to last day
            
        # Get metrics for the period
        metrics = self._get_metrics_for_period(broker_name, start_time, end_time)
        executions = self._get_executions_for_period(broker_name, start_time, end_time)
        price_feeds = self._get_price_feeds_for_period(broker_name, start_time, end_time)
        
        # Calculate latency metrics
        latency_values = [m.value for m in metrics if m.metric_type == MetricType.LATENCY]
        avg_order_latency = statistics.mean(latency_values) if latency_values else 0
        p95_order_latency = np.percentile(latency_values, 95) if latency_values else 0
        p99_order_latency = np.percentile(latency_values, 99) if latency_values else 0
        
        price_latencies = [latency for _, latency in price_feeds]
        avg_price_feed_latency = statistics.mean(price_latencies) if price_latencies else 0
        
        # Calculate throughput metrics
        throughput_values = [m.value for m in metrics if m.metric_type == MetricType.THROUGHPUT]
        max_orders_per_second = max(throughput_values) if throughput_values else 0
        avg_orders_per_second = statistics.mean(throughput_values) if throughput_values else 0
        
        # Calculate reliability metrics
        success_rates = [m.value for m in metrics if m.metric_type == MetricType.SUCCESS_RATE]
        error_rates = [m.value for m in metrics if m.metric_type == MetricType.ERROR_RATE]
        availability_values = [m.value for m in metrics if m.metric_type == MetricType.AVAILABILITY]
        
        success_rate = statistics.mean(success_rates) if success_rates else 0
        error_rate = statistics.mean(error_rates) if error_rates else 0
        uptime_percentage = statistics.mean(availability_values) * 100 if availability_values else 0
        
        # Calculate cost metrics (simplified)
        avg_commission = self._calculate_average_commission(executions)
        avg_spread = self._calculate_average_spread(executions)
        total_fees = sum(getattr(e.result, 'commission', 0) or 0 for e in executions)
        
        # Calculate accuracy metrics
        slippage_average = self._calculate_average_slippage(executions)
        
        # Calculate derived scores
        speed_score = self._calculate_speed_score(avg_order_latency, p95_order_latency)
        reliability_score = self._calculate_reliability_score(success_rate, uptime_percentage)
        cost_efficiency_score = self._calculate_cost_score(avg_commission, avg_spread)
        
        # Calculate overall performance score
        overall_score = (speed_score * 0.3 + reliability_score * 0.4 + cost_efficiency_score * 0.3)
        
        # Get broker adapter info
        adapter = self.broker_adapters[broker_name]
        
        benchmark = BrokerBenchmark(
            broker_name=broker_name,
            benchmark_timestamp=end_time,
            avg_order_latency=avg_order_latency,
            p95_order_latency=p95_order_latency,
            p99_order_latency=p99_order_latency,
            avg_price_feed_latency=avg_price_feed_latency,
            max_orders_per_second=max_orders_per_second,
            avg_orders_per_second=avg_orders_per_second,
            max_price_updates_per_second=len(price_feeds) / 3600 if price_feeds else 0,  # per hour
            uptime_percentage=uptime_percentage,
            success_rate=success_rate,
            error_rate=error_rate,
            connection_stability=uptime_percentage / 100,
            avg_commission_per_trade=avg_commission,
            avg_spread=avg_spread,
            total_fees=total_fees,
            price_accuracy_score=95.0,  # Placeholder
            execution_accuracy_score=success_rate * 100,
            slippage_average=slippage_average,
            market_data_coverage=100.0,  # Placeholder
            instrument_availability=len(adapter.supported_instruments),
            api_feature_completeness=len(adapter.capabilities) / len(list(adapter.capabilities)) * 100,
            overall_performance_score=overall_score,
            cost_efficiency_score=cost_efficiency_score,
            reliability_score=reliability_score,
            speed_score=speed_score,
            sample_size=len(executions),
            metadata={
                'period': period.value,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }
        )
        
        return benchmark
        
    def _get_metrics_for_period(self, 
                               broker_name: str, 
                               start_time: datetime, 
                               end_time: datetime) -> List[MetricSnapshot]:
        """Get metrics for specific time period"""
        if broker_name not in self.metric_history:
            return []
            
        return [
            metric for metric in self.metric_history[broker_name]
            if start_time <= metric.timestamp <= end_time
        ]
        
    def _get_executions_for_period(self,
                                  broker_name: str,
                                  start_time: datetime,
                                  end_time: datetime) -> List[OrderExecution]:
        """Get executions for specific time period"""
        if broker_name not in self.execution_history:
            return []
            
        return [
            execution for execution in self.execution_history[broker_name]
            if start_time <= execution.execution_time <= end_time
        ]
        
    def _get_price_feeds_for_period(self,
                                   broker_name: str,
                                   start_time: datetime,
                                   end_time: datetime) -> List[Tuple[datetime, float]]:
        """Get price feeds for specific time period"""
        if broker_name not in self.price_feed_history:
            return []
            
        return [
            (timestamp, latency) for timestamp, latency in self.price_feed_history[broker_name]
            if start_time <= timestamp <= end_time
        ]
        
    def _calculate_average_commission(self, executions: List[OrderExecution]) -> float:
        """Calculate average commission from executions"""
        commissions = [
            getattr(e.result, 'commission', 0) or 0 
            for e in executions 
            if e.success and hasattr(e.result, 'commission')
        ]
        return statistics.mean(commissions) if commissions else 0
        
    def _calculate_average_spread(self, executions: List[OrderExecution]) -> float:
        """Calculate average spread from executions"""
        # This is a simplified calculation - would need bid/ask data
        return 0.0001  # Placeholder: 1 pip for forex
        
    def _calculate_average_slippage(self, executions: List[OrderExecution]) -> float:
        """Calculate average slippage from executions"""
        # Simplified calculation
        slippages = []
        for execution in executions:
            if (execution.success and 
                hasattr(execution.result, 'fill_price') and 
                execution.result.fill_price and 
                execution.order.price):
                slippage = abs(float(execution.result.fill_price) - float(execution.order.price))
                slippages.append(slippage)
                
        return statistics.mean(slippages) if slippages else 0
        
    def _calculate_speed_score(self, avg_latency: float, p95_latency: float) -> float:
        """Calculate speed score (0-100)"""
        # Score based on latency thresholds
        if avg_latency <= self.latency_thresholds['excellent']:
            base_score = 95
        elif avg_latency <= self.latency_thresholds['good']:
            base_score = 80
        elif avg_latency <= self.latency_thresholds['acceptable']:
            base_score = 60
        elif avg_latency <= self.latency_thresholds['poor']:
            base_score = 30
        else:
            base_score = 10
            
        # Adjust for P95 latency
        if p95_latency > avg_latency * 2:
            base_score *= 0.8  # Penalize high variance
            
        return max(0, min(100, base_score))
        
    def _calculate_reliability_score(self, success_rate: float, uptime_percentage: float) -> float:
        """Calculate reliability score (0-100)"""
        # Weight success rate and uptime equally
        success_score = success_rate * 100
        uptime_score = uptime_percentage
        
        return (success_score + uptime_score) / 2
        
    def _calculate_cost_score(self, avg_commission: float, avg_spread: float) -> float:
        """Calculate cost efficiency score (0-100)"""
        # Simplified scoring - lower costs = higher score
        # This would need broker-specific benchmarks in practice
        commission_score = max(0, 100 - (avg_commission * 1000))  # Assuming commission in dollars
        spread_score = max(0, 100 - (avg_spread * 10000))  # Assuming spread in decimal
        
        return (commission_score + spread_score) / 2
        
    async def compare_brokers(self,
                            broker_names: List[str],
                            period: ComparisonPeriod = ComparisonPeriod.LAST_DAY) -> BrokerComparison:
        """
        Compare performance across multiple brokers
        
        Args:
            broker_names: List of broker names to compare
            period: Time period for comparison
            
        Returns:
            BrokerComparison with detailed analysis
        """
        comparison_id = f"comp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Generate benchmarks for all brokers
        benchmarks = {}
        for broker_name in broker_names:
            if broker_name in self.broker_adapters:
                benchmarks[broker_name] = await self.generate_broker_benchmark(broker_name, period)
            else:
                logger.warning(f"Broker {broker_name} not registered, skipping")
                
        # Generate rankings
        rankings = self._generate_rankings(benchmarks)
        
        # Determine overall winner
        winner = self._determine_winner(benchmarks)
        
        # Generate recommendations
        recommendations = self._generate_comparison_recommendations(benchmarks, rankings)
        
        end_time = datetime.now(timezone.utc)
        if period == ComparisonPeriod.LAST_HOUR:
            start_time = end_time - timedelta(hours=1)
        elif period == ComparisonPeriod.LAST_DAY:
            start_time = end_time - timedelta(days=1)
        elif period == ComparisonPeriod.LAST_WEEK:
            start_time = end_time - timedelta(weeks=1)
        elif period == ComparisonPeriod.LAST_MONTH:
            start_time = end_time - timedelta(days=30)
        else:
            start_time = end_time - timedelta(days=1)
            
        comparison = BrokerComparison(
            comparison_id=comparison_id,
            broker_names=list(benchmarks.keys()),
            comparison_period=period,
            start_time=start_time,
            end_time=end_time,
            benchmarks=benchmarks,
            rankings=rankings,
            recommendations=recommendations,
            winner=winner,
            metadata={
                'total_brokers': len(benchmarks),
                'comparison_timestamp': end_time.isoformat()
            }
        )
        
        return comparison
        
    def _generate_rankings(self, benchmarks: Dict[str, BrokerBenchmark]) -> Dict[BenchmarkType, List[Tuple[str, float]]]:
        """Generate rankings for different benchmark types"""
        rankings = {}
        
        # Speed ranking (based on latency - lower is better)
        speed_scores = [(name, benchmark.speed_score) for name, benchmark in benchmarks.items()]
        rankings[BenchmarkType.LATENCY] = sorted(speed_scores, key=lambda x: x[1], reverse=True)
        
        # Reliability ranking
        reliability_scores = [(name, benchmark.reliability_score) for name, benchmark in benchmarks.items()]
        rankings[BenchmarkType.RELIABILITY] = sorted(reliability_scores, key=lambda x: x[1], reverse=True)
        
        # Cost ranking
        cost_scores = [(name, benchmark.cost_efficiency_score) for name, benchmark in benchmarks.items()]
        rankings[BenchmarkType.COST] = sorted(cost_scores, key=lambda x: x[1], reverse=True)
        
        # Throughput ranking
        throughput_scores = [(name, benchmark.avg_orders_per_second) for name, benchmark in benchmarks.items()]
        rankings[BenchmarkType.THROUGHPUT] = sorted(throughput_scores, key=lambda x: x[1], reverse=True)
        
        # Overall ranking
        overall_scores = [(name, benchmark.overall_performance_score) for name, benchmark in benchmarks.items()]
        rankings[BenchmarkType.ACCURACY] = sorted(overall_scores, key=lambda x: x[1], reverse=True)
        
        return rankings
        
    def _determine_winner(self, benchmarks: Dict[str, BrokerBenchmark]) -> Optional[str]:
        """Determine overall winner based on performance scores"""
        if not benchmarks:
            return None
            
        # Find broker with highest overall performance score
        winner = max(benchmarks.items(), key=lambda x: x[1].overall_performance_score)
        return winner[0]
        
    def _generate_comparison_recommendations(self, 
                                           benchmarks: Dict[str, BrokerBenchmark],
                                           rankings: Dict[BenchmarkType, List[Tuple[str, float]]]) -> List[str]:
        """Generate recommendations based on comparison"""
        recommendations = []
        
        if not benchmarks:
            return ["No broker data available for comparison"]
            
        # Overall winner recommendation
        overall_ranking = rankings.get(BenchmarkType.ACCURACY, [])
        if overall_ranking:
            winner = overall_ranking[0]
            recommendations.append(f"Overall best performer: {winner[0]} (score: {winner[1]:.1f})")
            
        # Speed recommendation
        speed_ranking = rankings.get(BenchmarkType.LATENCY, [])
        if speed_ranking:
            fastest = speed_ranking[0]
            recommendations.append(f"Fastest execution: {fastest[0]} (latency score: {fastest[1]:.1f})")
            
        # Reliability recommendation
        reliability_ranking = rankings.get(BenchmarkType.RELIABILITY, [])
        if reliability_ranking:
            most_reliable = reliability_ranking[0]
            recommendations.append(f"Most reliable: {most_reliable[0]} (reliability: {most_reliable[1]:.1f}%)")
            
        # Cost recommendation
        cost_ranking = rankings.get(BenchmarkType.COST, [])
        if cost_ranking:
            most_cost_effective = cost_ranking[0]
            recommendations.append(f"Most cost-effective: {most_cost_effective[0]} (cost score: {most_cost_effective[1]:.1f})")
            
        # Specific recommendations based on scores
        for name, benchmark in benchmarks.items():
            if benchmark.success_rate < 0.95:
                recommendations.append(f"WARNING: {name} has low success rate ({benchmark.success_rate:.1%})")
            if benchmark.avg_order_latency > 1000:
                recommendations.append(f"WARNING: {name} has high latency ({benchmark.avg_order_latency:.0f}ms)")
            if benchmark.uptime_percentage < 95:
                recommendations.append(f"WARNING: {name} has low uptime ({benchmark.uptime_percentage:.1f}%)")
                
        return recommendations
        
    def export_comparison(self, comparison: BrokerComparison, file_path: str):
        """Export broker comparison to file"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(comparison.to_dict(), f, indent=2, default=str)
        logger.info(f"Exported broker comparison to {file_path}")
        
    def get_broker_performance_summary(self, broker_name: str) -> Dict[str, Any]:
        """Get performance summary for a specific broker"""
        if broker_name not in self.metric_history:
            return {}
            
        recent_metrics = self.metric_history[broker_name][-100:]  # Last 100 metrics
        
        summary = {
            'broker_name': broker_name,
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'metrics_count': len(recent_metrics),
            'performance': {}
        }
        
        # Group metrics by type
        for metric_type in MetricType:
            type_metrics = [m.value for m in recent_metrics if m.metric_type == metric_type]
            if type_metrics:
                summary['performance'][metric_type.value] = {
                    'current': type_metrics[-1],
                    'average': statistics.mean(type_metrics),
                    'min': min(type_metrics),
                    'max': max(type_metrics),
                    'trend': 'improving' if len(type_metrics) > 1 and type_metrics[-1] < statistics.mean(type_metrics[:-1]) else 'stable'
                }
                
        return summary


# Global performance metrics collector
_global_metrics_collector: Optional[PerformanceMetricsCollector] = None


def get_global_metrics_collector() -> PerformanceMetricsCollector:
    """Get global performance metrics collector instance"""
    global _global_metrics_collector
    if _global_metrics_collector is None:
        _global_metrics_collector = PerformanceMetricsCollector()
    return _global_metrics_collector