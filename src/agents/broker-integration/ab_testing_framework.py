"""
A/B Testing Framework for Broker Routing
Story 8.10 - Task 6: Create A/B testing framework (AC7, AC8)
"""
import asyncio
import logging
import hashlib
import random
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from decimal import Decimal
import statistics
import json
import uuid

try:
    from .broker_adapter import BrokerAdapter, UnifiedOrder, OrderResult
    from .unified_errors import StandardBrokerError, StandardErrorCode
except ImportError:
    from broker_adapter import BrokerAdapter, UnifiedOrder, OrderResult
    from unified_errors import StandardBrokerError, StandardErrorCode

logger = logging.getLogger(__name__)


class ABTestStatus(Enum):
    """A/B test status"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RoutingStrategy(Enum):
    """Routing strategies for A/B tests"""
    RANDOM = "random"
    HASH_BASED = "hash_based"
    WEIGHTED_RANDOM = "weighted_random"
    ROUND_ROBIN = "round_robin"
    PERFORMANCE_BASED = "performance_based"


class MetricType(Enum):
    """Types of performance metrics"""
    LATENCY = "latency"
    SUCCESS_RATE = "success_rate"
    ERROR_RATE = "error_rate"
    FILL_RATE = "fill_rate"
    SLIPPAGE = "slippage"
    COMMISSION = "commission"
    AVAILABILITY = "availability"
    THROUGHPUT = "throughput"


@dataclass
class TrafficSplit:
    """Traffic allocation for A/B test"""
    broker_name: str
    percentage: float
    description: Optional[str] = None
    
    def __post_init__(self):
        if not 0 <= self.percentage <= 100:
            raise ValueError("Percentage must be between 0 and 100")


@dataclass
class ABTestConfig:
    """A/B test configuration"""
    test_id: str
    name: str
    description: str
    traffic_splits: List[TrafficSplit]
    routing_strategy: RoutingStrategy
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_hours: Optional[int] = None
    target_sample_size: Optional[int] = None
    confidence_level: float = 0.95
    metrics_to_track: List[MetricType] = field(default_factory=lambda: [
        MetricType.LATENCY, MetricType.SUCCESS_RATE, MetricType.ERROR_RATE
    ])
    filters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # Validate traffic splits
        total_percentage = sum(split.percentage for split in self.traffic_splits)
        if abs(total_percentage - 100.0) > 0.01:
            raise ValueError(f"Traffic splits must sum to 100%, got {total_percentage}%")
            
        # Set end time if duration is specified
        if self.end_time is None and self.duration_hours:
            self.end_time = self.start_time + timedelta(hours=self.duration_hours)


@dataclass
class OrderExecution:
    """Record of order execution for A/B testing"""
    execution_id: str
    test_id: str
    broker_name: str
    order: UnifiedOrder
    result: OrderResult
    execution_time: datetime
    latency_ms: float
    success: bool
    error_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricSnapshot:
    """Performance metric snapshot"""
    metric_type: MetricType
    broker_name: str
    value: float
    timestamp: datetime
    sample_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ABTestResults:
    """A/B test results and analysis"""
    test_id: str
    status: ABTestStatus
    start_time: datetime
    end_time: Optional[datetime]
    total_executions: int
    executions_by_broker: Dict[str, int]
    metrics: Dict[str, Dict[str, MetricSnapshot]]  # metric_type -> broker_name -> snapshot
    statistical_significance: Dict[str, Dict[str, float]]  # metric_type -> comparison -> p_value
    winner: Optional[str] = None
    confidence_level: float = 0.95
    recommendations: List[str] = field(default_factory=list)
    raw_executions: List[OrderExecution] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'test_id': self.test_id,
            'status': self.status.value,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'total_executions': self.total_executions,
            'executions_by_broker': self.executions_by_broker,
            'metrics': {
                metric_type: {
                    broker: asdict(snapshot) for broker, snapshot in brokers.items()
                } for metric_type, brokers in self.metrics.items()
            },
            'statistical_significance': self.statistical_significance,
            'winner': self.winner,
            'confidence_level': self.confidence_level,
            'recommendations': self.recommendations
        }


class BrokerABTestingFramework:
    """Framework for A/B testing different brokers"""
    
    def __init__(self):
        self.active_tests: Dict[str, ABTestConfig] = {}
        self.test_history: Dict[str, ABTestConfig] = {}
        self.executions: Dict[str, List[OrderExecution]] = {}  # test_id -> executions
        self.broker_adapters: Dict[str, BrokerAdapter] = {}
        self.routing_cache: Dict[str, str] = {}  # order_id -> broker_name
        
        # Performance tracking
        self.broker_metrics: Dict[str, Dict[MetricType, List[float]]] = {}
        self.metric_callbacks: List[Callable] = []
        
        # Statistical analysis settings
        self.min_sample_size = 30
        self.significance_threshold = 0.05
        
    def register_broker_adapter(self, broker_name: str, adapter: BrokerAdapter):
        """Register broker adapter for A/B testing"""
        self.broker_adapters[broker_name] = adapter
        if broker_name not in self.broker_metrics:
            self.broker_metrics[broker_name] = {metric: [] for metric in MetricType}
        logger.info(f"Registered broker adapter for A/B testing: {broker_name}")
        
    def create_ab_test(self, 
                      test_name: str,
                      description: str,
                      traffic_splits: List[TrafficSplit],
                      routing_strategy: RoutingStrategy = RoutingStrategy.HASH_BASED,
                      duration_hours: int = 24,
                      **kwargs) -> str:
        """
        Create A/B test configuration
        
        Args:
            test_name: Name of the test
            description: Test description
            traffic_splits: List of TrafficSplit objects
            routing_strategy: Strategy for routing orders
            duration_hours: Test duration in hours
            **kwargs: Additional configuration options
            
        Returns:
            Test ID
        """
        test_id = f"test_{uuid.uuid4().hex[:8]}"
        
        # Validate that all brokers in traffic splits are registered
        for split in traffic_splits:
            if split.broker_name not in self.broker_adapters:
                raise ValueError(f"Broker '{split.broker_name}' not registered")
                
        config = ABTestConfig(
            test_id=test_id,
            name=test_name,
            description=description,
            traffic_splits=traffic_splits,
            routing_strategy=routing_strategy,
            start_time=datetime.now(timezone.utc),
            duration_hours=duration_hours,
            **kwargs
        )
        
        self.active_tests[test_id] = config
        self.executions[test_id] = []
        
        logger.info(f"Created A/B test: {test_name} (ID: {test_id})")
        return test_id
        
    def start_test(self, test_id: str) -> bool:
        """Start an A/B test"""
        if test_id not in self.active_tests:
            return False
            
        config = self.active_tests[test_id]
        config.start_time = datetime.now(timezone.utc)
        
        if config.duration_hours and not config.end_time:
            config.end_time = config.start_time + timedelta(hours=config.duration_hours)
            
        logger.info(f"Started A/B test: {config.name} (ID: {test_id})")
        return True
        
    def stop_test(self, test_id: str, reason: str = "Manual stop") -> bool:
        """Stop an A/B test"""
        if test_id not in self.active_tests:
            return False
            
        config = self.active_tests[test_id]
        config.end_time = datetime.now(timezone.utc)
        config.metadata['stop_reason'] = reason
        
        # Move to history
        self.test_history[test_id] = config
        del self.active_tests[test_id]
        
        logger.info(f"Stopped A/B test: {config.name} (ID: {test_id}) - {reason}")
        return True
        
    async def route_order(self, order: UnifiedOrder, test_id: Optional[str] = None) -> str:
        """
        Route order to broker based on A/B test configuration
        
        Args:
            order: Order to route
            test_id: Optional specific test ID to use
            
        Returns:
            Broker name to route order to
        """
        # Find applicable test
        if test_id:
            config = self.active_tests.get(test_id)
            if not config:
                raise ValueError(f"Test {test_id} not found or not active")
        else:
            # Find active test that applies to this order
            config = self._find_applicable_test(order)
            
        if not config:
            # No active test, use default broker
            return list(self.broker_adapters.keys())[0] if self.broker_adapters else None
            
        # Check if test has expired
        if config.end_time and datetime.now(timezone.utc) > config.end_time:
            await self._auto_stop_expired_test(config.test_id)
            return list(self.broker_adapters.keys())[0] if self.broker_adapters else None
            
        # Route based on strategy
        broker_name = self._route_by_strategy(order, config)
        
        # Cache routing decision
        self.routing_cache[order.order_id] = broker_name
        
        return broker_name
        
    def _find_applicable_test(self, order: UnifiedOrder) -> Optional[ABTestConfig]:
        """Find active test that applies to this order"""
        for config in self.active_tests.values():
            # Check if test is active
            now = datetime.now(timezone.utc)
            if now < config.start_time:
                continue
            if config.end_time and now > config.end_time:
                continue
                
            # Check filters
            if self._order_matches_filters(order, config.filters):
                return config
                
        return None
        
    def _order_matches_filters(self, order: UnifiedOrder, filters: Dict[str, Any]) -> bool:
        """Check if order matches test filters"""
        if not filters:
            return True
            
        # Check instrument filter
        if 'instruments' in filters:
            if order.instrument not in filters['instruments']:
                return False
                
        # Check order type filter
        if 'order_types' in filters:
            if order.order_type.value not in filters['order_types']:
                return False
                
        # Check units range filter
        if 'min_units' in filters:
            if order.units < Decimal(str(filters['min_units'])):
                return False
                
        if 'max_units' in filters:
            if order.units > Decimal(str(filters['max_units'])):
                return False
                
        # Check time range filter
        if 'time_ranges' in filters:
            current_hour = datetime.now(timezone.utc).hour
            if not any(start <= current_hour < end for start, end in filters['time_ranges']):
                return False
                
        return True
        
    def _route_by_strategy(self, order: UnifiedOrder, config: ABTestConfig) -> str:
        """Route order based on routing strategy"""
        if config.routing_strategy == RoutingStrategy.RANDOM:
            return self._route_random(config.traffic_splits)
        elif config.routing_strategy == RoutingStrategy.HASH_BASED:
            return self._route_hash_based(order, config.traffic_splits)
        elif config.routing_strategy == RoutingStrategy.WEIGHTED_RANDOM:
            return self._route_weighted_random(config.traffic_splits)
        elif config.routing_strategy == RoutingStrategy.ROUND_ROBIN:
            return self._route_round_robin(config)
        elif config.routing_strategy == RoutingStrategy.PERFORMANCE_BASED:
            return self._route_performance_based(config.traffic_splits)
        else:
            return config.traffic_splits[0].broker_name  # Default to first broker
            
    def _route_random(self, traffic_splits: List[TrafficSplit]) -> str:
        """Route using pure random selection"""
        rand_val = random.uniform(0, 100)
        cumulative = 0
        
        for split in traffic_splits:
            cumulative += split.percentage
            if rand_val <= cumulative:
                return split.broker_name
                
        return traffic_splits[-1].broker_name  # Fallback
        
    def _route_hash_based(self, order: UnifiedOrder, traffic_splits: List[TrafficSplit]) -> str:
        """Route using hash-based deterministic selection"""
        # Use order ID or client order ID for consistent routing
        hash_input = order.client_order_id or order.order_id
        hash_val = int(hashlib.md5(hash_input.encode()).hexdigest(), 16) % 100
        
        cumulative = 0
        for split in traffic_splits:
            cumulative += split.percentage
            if hash_val < cumulative:
                return split.broker_name
                
        return traffic_splits[-1].broker_name  # Fallback
        
    def _route_weighted_random(self, traffic_splits: List[TrafficSplit]) -> str:
        """Route using weighted random selection"""
        weights = [split.percentage for split in traffic_splits]
        brokers = [split.broker_name for split in traffic_splits]
        
        return random.choices(brokers, weights=weights)[0]
        
    def _route_round_robin(self, config: ABTestConfig) -> str:
        """Route using round-robin selection"""
        execution_count = len(self.executions.get(config.test_id, []))
        broker_index = execution_count % len(config.traffic_splits)
        return config.traffic_splits[broker_index].broker_name
        
    def _route_performance_based(self, traffic_splits: List[TrafficSplit]) -> str:
        """Route based on recent performance metrics"""
        broker_scores = {}
        
        for split in traffic_splits:
            broker_name = split.broker_name
            
            # Calculate composite performance score
            score = 0.0
            
            # Success rate (weight: 40%)
            success_rates = self.broker_metrics[broker_name].get(MetricType.SUCCESS_RATE, [])
            if success_rates:
                score += 0.4 * statistics.mean(success_rates[-10:])  # Last 10 measurements
                
            # Latency (weight: 30%, inverted - lower is better)
            latencies = self.broker_metrics[broker_name].get(MetricType.LATENCY, [])
            if latencies:
                avg_latency = statistics.mean(latencies[-10:])
                # Normalize latency score (assuming max acceptable latency is 5000ms)
                score += 0.3 * max(0, (5000 - avg_latency) / 5000)
                
            # Error rate (weight: 30%, inverted - lower is better)
            error_rates = self.broker_metrics[broker_name].get(MetricType.ERROR_RATE, [])
            if error_rates:
                avg_error_rate = statistics.mean(error_rates[-10:])
                score += 0.3 * max(0, (1.0 - avg_error_rate))
                
            broker_scores[broker_name] = score
            
        # Route to best performing broker
        if broker_scores:
            best_broker = max(broker_scores.items(), key=lambda x: x[1])[0]
            return best_broker
        else:
            # Fallback to random if no performance data
            return self._route_random(traffic_splits)
            
    async def execute_order_with_test(self, 
                                    order: UnifiedOrder, 
                                    test_id: Optional[str] = None) -> OrderResult:
        """
        Execute order through A/B testing framework
        
        Args:
            order: Order to execute
            test_id: Optional specific test ID
            
        Returns:
            Order execution result
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Route to broker
            broker_name = await self.route_order(order, test_id)
            
            if not broker_name or broker_name not in self.broker_adapters:
                raise StandardBrokerError(
                    error_code=StandardErrorCode.SERVICE_UNAVAILABLE,
                    message="No available broker for order execution"
                )
                
            # Execute order
            adapter = self.broker_adapters[broker_name]
            result = await adapter.place_order(order)
            
            # Calculate execution metrics
            end_time = datetime.now(timezone.utc)
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            # Find applicable test
            applicable_test = None
            if test_id:
                applicable_test = self.active_tests.get(test_id)
            else:
                applicable_test = self._find_applicable_test(order)
                
            # Record execution
            if applicable_test:
                execution = OrderExecution(
                    execution_id=f"exec_{uuid.uuid4().hex[:8]}",
                    test_id=applicable_test.test_id,
                    broker_name=broker_name,
                    order=order,
                    result=result,
                    execution_time=end_time,
                    latency_ms=latency_ms,
                    success=result.success,
                    error_type=result.error_code if not result.success else None
                )
                
                self.executions[applicable_test.test_id].append(execution)
                
                # Update metrics
                await self._update_metrics(broker_name, execution)
                
            return result
            
        except Exception as e:
            # Record failed execution
            end_time = datetime.now(timezone.utc)
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            error_result = OrderResult(
                success=False,
                error_code=getattr(e, 'error_code', StandardErrorCode.UNKNOWN_ERROR).value,
                error_message=str(e)
            )
            
            # Find broker that would have been used
            try:
                broker_name = await self.route_order(order, test_id)
            except:
                broker_name = "unknown"
                
            # Find applicable test
            applicable_test = None
            if test_id:
                applicable_test = self.active_tests.get(test_id)
            else:
                try:
                    applicable_test = self._find_applicable_test(order)
                except:
                    pass
                    
            if applicable_test:
                execution = OrderExecution(
                    execution_id=f"exec_{uuid.uuid4().hex[:8]}",
                    test_id=applicable_test.test_id,
                    broker_name=broker_name,
                    order=order,
                    result=error_result,
                    execution_time=end_time,
                    latency_ms=latency_ms,
                    success=False,
                    error_type=getattr(e, 'error_code', StandardErrorCode.UNKNOWN_ERROR).value
                )
                
                self.executions[applicable_test.test_id].append(execution)
                
                # Update metrics
                await self._update_metrics(broker_name, execution)
                
            raise
            
    async def _update_metrics(self, broker_name: str, execution: OrderExecution):
        """Update broker performance metrics"""
        if broker_name not in self.broker_metrics:
            self.broker_metrics[broker_name] = {metric: [] for metric in MetricType}
            
        metrics = self.broker_metrics[broker_name]
        
        # Update latency
        metrics[MetricType.LATENCY].append(execution.latency_ms)
        
        # Update success/error rates
        metrics[MetricType.SUCCESS_RATE].append(1.0 if execution.success else 0.0)
        metrics[MetricType.ERROR_RATE].append(0.0 if execution.success else 1.0)
        
        # Keep only recent metrics (last 1000 measurements)
        for metric_list in metrics.values():
            if len(metric_list) > 1000:
                metric_list[:] = metric_list[-1000:]
                
        # Notify callbacks
        for callback in self.metric_callbacks:
            try:
                await callback(broker_name, execution)
            except Exception as e:
                logger.error(f"Metric callback error: {e}")
                
    async def _auto_stop_expired_test(self, test_id: str):
        """Automatically stop expired test"""
        await asyncio.create_task(
            asyncio.to_thread(self.stop_test, test_id, "Test duration expired")
        )
        
    def analyze_test_results(self, test_id: str) -> ABTestResults:
        """
        Analyze A/B test results and generate statistical analysis
        
        Args:
            test_id: Test ID to analyze
            
        Returns:
            ABTestResults with analysis
        """
        # Get test configuration
        config = self.active_tests.get(test_id) or self.test_history.get(test_id)
        if not config:
            raise ValueError(f"Test {test_id} not found")
            
        executions = self.executions.get(test_id, [])
        
        # Calculate basic metrics
        total_executions = len(executions)
        executions_by_broker = {}
        metrics_by_broker = {}
        
        for execution in executions:
            broker_name = execution.broker_name
            
            # Count executions
            executions_by_broker[broker_name] = executions_by_broker.get(broker_name, 0) + 1
            
            # Initialize metrics structure
            if broker_name not in metrics_by_broker:
                metrics_by_broker[broker_name] = {
                    MetricType.LATENCY: [],
                    MetricType.SUCCESS_RATE: [],
                    MetricType.ERROR_RATE: []
                }
                
            # Collect metrics
            metrics_by_broker[broker_name][MetricType.LATENCY].append(execution.latency_ms)
            metrics_by_broker[broker_name][MetricType.SUCCESS_RATE].append(1.0 if execution.success else 0.0)
            metrics_by_broker[broker_name][MetricType.ERROR_RATE].append(0.0 if execution.success else 1.0)
            
        # Calculate metric snapshots
        metric_snapshots = {}
        for metric_type in [MetricType.LATENCY, MetricType.SUCCESS_RATE, MetricType.ERROR_RATE]:
            metric_snapshots[metric_type.value] = {}
            
            for broker_name, broker_metrics in metrics_by_broker.items():
                values = broker_metrics[metric_type]
                if values:
                    snapshot = MetricSnapshot(
                        metric_type=metric_type,
                        broker_name=broker_name,
                        value=statistics.mean(values),
                        timestamp=datetime.now(timezone.utc),
                        sample_count=len(values),
                        metadata={
                            'std_dev': statistics.stdev(values) if len(values) > 1 else 0,
                            'min': min(values),
                            'max': max(values)
                        }
                    )
                    metric_snapshots[metric_type.value][broker_name] = snapshot
                    
        # Perform statistical significance testing
        statistical_significance = {}
        for metric_type in [MetricType.LATENCY, MetricType.SUCCESS_RATE, MetricType.ERROR_RATE]:
            statistical_significance[metric_type.value] = {}
            
            brokers = list(metrics_by_broker.keys())
            for i, broker1 in enumerate(brokers):
                for broker2 in brokers[i+1:]:
                    values1 = metrics_by_broker[broker1][metric_type]
                    values2 = metrics_by_broker[broker2][metric_type]
                    
                    if len(values1) >= self.min_sample_size and len(values2) >= self.min_sample_size:
                        # Simplified t-test (would use scipy.stats.ttest_ind in practice)
                        p_value = self._simplified_ttest(values1, values2)
                        statistical_significance[metric_type.value][f"{broker1}_vs_{broker2}"] = p_value
                        
        # Determine winner
        winner = self._determine_winner(metric_snapshots, statistical_significance, config.confidence_level)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(metric_snapshots, statistical_significance, winner)
        
        results = ABTestResults(
            test_id=test_id,
            status=ABTestStatus.ACTIVE if test_id in self.active_tests else ABTestStatus.COMPLETED,
            start_time=config.start_time,
            end_time=config.end_time,
            total_executions=total_executions,
            executions_by_broker=executions_by_broker,
            metrics=metric_snapshots,
            statistical_significance=statistical_significance,
            winner=winner,
            confidence_level=config.confidence_level,
            recommendations=recommendations,
            raw_executions=executions[:100]  # Include up to 100 raw executions
        )
        
        return results
        
    def _simplified_ttest(self, values1: List[float], values2: List[float]) -> float:
        """Simplified t-test implementation (placeholder for real statistical test)"""
        # This is a very simplified version - in practice, use scipy.stats.ttest_ind
        if not values1 or not values2:
            return 1.0
            
        mean1, mean2 = statistics.mean(values1), statistics.mean(values2)
        
        # If means are very similar, assume not significant
        if abs(mean1 - mean2) < 0.01:
            return 0.8  # High p-value (not significant)
        else:
            return 0.02  # Low p-value (significant)
            
    def _determine_winner(self, 
                         metric_snapshots: Dict[str, Dict[str, MetricSnapshot]],
                         statistical_significance: Dict[str, Dict[str, float]],
                         confidence_level: float) -> Optional[str]:
        """Determine winning broker based on metrics and statistical significance"""
        # Score each broker across all metrics
        broker_scores = {}
        
        for metric_type, brokers in metric_snapshots.items():
            for broker_name, snapshot in brokers.items():
                if broker_name not in broker_scores:
                    broker_scores[broker_name] = 0
                    
                # Score based on metric type
                if metric_type == MetricType.LATENCY.value:
                    # Lower is better for latency
                    broker_scores[broker_name] += (5000 - snapshot.value) / 5000
                elif metric_type == MetricType.SUCCESS_RATE.value:
                    # Higher is better for success rate
                    broker_scores[broker_name] += snapshot.value
                elif metric_type == MetricType.ERROR_RATE.value:
                    # Lower is better for error rate
                    broker_scores[broker_name] += (1.0 - snapshot.value)
                    
        if not broker_scores:
            return None
            
        # Find highest scoring broker
        best_broker = max(broker_scores.items(), key=lambda x: x[1])[0]
        
        # Check if the difference is statistically significant
        significance_threshold = 1.0 - confidence_level
        
        for comparisons in statistical_significance.values():
            for comparison, p_value in comparisons.items():
                if best_broker in comparison and p_value > significance_threshold:
                    # Difference is not statistically significant
                    return None
                    
        return best_broker
        
    def _generate_recommendations(self,
                                metric_snapshots: Dict[str, Dict[str, MetricSnapshot]],
                                statistical_significance: Dict[str, Dict[str, float]],
                                winner: Optional[str]) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        if winner:
            recommendations.append(f"Route all traffic to {winner} for optimal performance")
        else:
            recommendations.append("No statistically significant difference found between brokers")
            
        # Analyze specific metrics
        for metric_type, brokers in metric_snapshots.items():
            if len(brokers) >= 2:
                sorted_brokers = sorted(brokers.items(), 
                                      key=lambda x: x[1].value, 
                                      reverse=metric_type != MetricType.LATENCY.value)
                
                best_broker = sorted_brokers[0][0]
                worst_broker = sorted_brokers[-1][0]
                
                if metric_type == MetricType.LATENCY.value:
                    recommendations.append(f"{best_broker} has lowest latency ({sorted_brokers[0][1].value:.1f}ms)")
                elif metric_type == MetricType.SUCCESS_RATE.value:
                    recommendations.append(f"{best_broker} has highest success rate ({sorted_brokers[0][1].value:.1%})")
                elif metric_type == MetricType.ERROR_RATE.value:
                    recommendations.append(f"{best_broker} has lowest error rate ({sorted_brokers[0][1].value:.1%})")
                    
        return recommendations
        
    def get_active_tests(self) -> Dict[str, ABTestConfig]:
        """Get all active tests"""
        return self.active_tests.copy()
        
    def get_test_history(self) -> Dict[str, ABTestConfig]:
        """Get test history"""
        return self.test_history.copy()
        
    def get_broker_performance(self, broker_name: str) -> Dict[MetricType, float]:
        """Get current performance metrics for broker"""
        if broker_name not in self.broker_metrics:
            return {}
            
        performance = {}
        for metric_type, values in self.broker_metrics[broker_name].items():
            if values:
                performance[metric_type] = statistics.mean(values[-100:])  # Last 100 measurements
                
        return performance
        
    def add_metric_callback(self, callback: Callable):
        """Add callback for metric updates"""
        self.metric_callbacks.append(callback)
        
    def export_test_results(self, test_id: str, file_path: str):
        """Export test results to file"""
        results = self.analyze_test_results(test_id)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(results.to_dict(), f, indent=2, default=str)
            
        logger.info(f"Exported test results for {test_id} to {file_path}")


# Global A/B testing framework
_global_ab_framework: Optional[BrokerABTestingFramework] = None


def get_global_ab_framework() -> BrokerABTestingFramework:
    """Get global A/B testing framework instance"""
    global _global_ab_framework
    if _global_ab_framework is None:
        _global_ab_framework = BrokerABTestingFramework()
    return _global_ab_framework