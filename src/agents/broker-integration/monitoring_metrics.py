"""
Enhanced Monitoring Metrics for Broker Integration
Story 8.13: Production Deployment & Monitoring
"""
import time
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from prometheus_client import (
    Counter, Histogram, Gauge, Info, Enum,
    start_http_server, REGISTRY, CollectorRegistry
)

logger = logging.getLogger(__name__)

# Core Business Metrics
ORDER_METRICS = Counter(
    'broker_orders_total',
    'Total orders processed by broker',
    ['broker', 'instrument', 'order_type', 'status']
)

ORDER_LATENCY = Histogram(
    'broker_order_execution_seconds',
    'Order execution latency in seconds',
    ['broker', 'order_type'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

TRADE_VOLUME = Counter(
    'broker_trade_volume_total',
    'Total trade volume processed',
    ['broker', 'instrument', 'direction']
)

SLIPPAGE_HISTOGRAM = Histogram(
    'broker_slippage_pips',
    'Order slippage in pips',
    ['broker', 'instrument'],
    buckets=[0, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0]
)

# API Performance Metrics
API_REQUEST_DURATION = Histogram(
    'broker_api_request_seconds',
    'API request duration',
    ['broker', 'endpoint', 'method'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]
)

API_ERROR_RATE = Counter(
    'broker_api_errors_total',
    'API error count',
    ['broker', 'endpoint', 'error_code', 'error_type']
)

RATE_LIMIT_HITS = Counter(
    'broker_rate_limit_hits_total',
    'Rate limit violations',
    ['broker', 'endpoint', 'limit_type']
)

# Connection and Authentication Metrics
CONNECTION_STATUS = Gauge(
    'broker_connection_status',
    'Connection status (1=connected, 0=disconnected)',
    ['broker', 'account_id', 'environment']
)

CONNECTION_DURATION = Histogram(
    'broker_connection_duration_seconds',
    'Connection establishment time',
    ['broker'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

AUTH_ATTEMPTS = Counter(
    'broker_auth_attempts_total',
    'Authentication attempts',
    ['broker', 'status', 'reason']
)

SESSION_DURATION = Histogram(
    'broker_session_duration_seconds',
    'Session duration',
    ['broker', 'termination_reason'],
    buckets=[60, 300, 900, 1800, 3600, 7200, 14400, 28800]
)

# Circuit Breaker and Error Recovery Metrics
CIRCUIT_BREAKER_STATE = Enum(
    'broker_circuit_breaker_state',
    'Circuit breaker state',
    ['broker', 'component'],
    states=['closed', 'open', 'half_open']
)

RECONNECTION_ATTEMPTS = Counter(
    'broker_reconnection_attempts_total',
    'Reconnection attempts',
    ['broker', 'trigger', 'status']
)

RECOVERY_TIME = Histogram(
    'broker_recovery_seconds',
    'Time to recover from failure',
    ['broker', 'failure_type'],
    buckets=[1, 5, 15, 30, 60, 120, 300, 600]
)

# Resource Utilization Metrics
CONNECTION_POOL_SIZE = Gauge(
    'broker_connection_pool_size',
    'Connection pool size',
    ['broker', 'pool_type']
)

CONNECTION_POOL_ACTIVE = Gauge(
    'broker_connection_pool_active',
    'Active connections in pool',
    ['broker', 'pool_type']
)

MEMORY_USAGE = Gauge(
    'broker_memory_usage_bytes',
    'Memory usage by component',
    ['broker', 'component']
)

# Business KPI Metrics
UPTIME = Gauge(
    'broker_uptime_seconds',
    'Service uptime in seconds',
    ['broker']
)

SLA_COMPLIANCE = Gauge(
    'broker_sla_compliance_ratio',
    'SLA compliance ratio (0-1)',
    ['broker', 'sla_type']
)

THROUGHPUT = Gauge(
    'broker_throughput_ops_per_second',
    'Operations throughput',
    ['broker', 'operation_type']
)

# Data Quality Metrics
DATA_FRESHNESS = Gauge(
    'broker_data_freshness_seconds',
    'Age of last data update',
    ['broker', 'data_type']
)

MARKET_DATA_GAPS = Counter(
    'broker_market_data_gaps_total',
    'Market data gaps detected',
    ['broker', 'instrument', 'gap_type']
)

@dataclass
class MetricsConfig:
    """Configuration for metrics collection"""
    collection_interval: int = 15
    retention_period: int = 86400  # 24 hours
    enable_detailed_metrics: bool = True
    enable_business_metrics: bool = True
    enable_sla_tracking: bool = True

class BrokerMetricsCollector:
    """Enhanced metrics collector for broker integration"""
    
    def __init__(self, config: MetricsConfig = None):
        self.config = config or MetricsConfig()
        self.start_time = time.time()
        self.last_collection = time.time()
        self.metrics_cache: Dict[str, Any] = {}
        self.running = False
        
    async def start_collection(self, port: int = 9090):
        """Start metrics collection server"""
        try:
            start_http_server(port)
            self.running = True
            logger.info(f"Metrics server started on port {port}")
            
            # Start background collection tasks
            asyncio.create_task(self._collect_system_metrics())
            asyncio.create_task(self._calculate_sla_metrics())
            asyncio.create_task(self._update_business_kpis())
            
        except Exception as e:
            logger.error(f"Failed to start metrics collection: {e}")
            raise
    
    def stop_collection(self):
        """Stop metrics collection"""
        self.running = False
        logger.info("Metrics collection stopped")
    
    # Order and Trading Metrics
    def record_order_placed(self, broker: str, instrument: str, order_type: str, status: str):
        """Record order placement"""
        ORDER_METRICS.labels(
            broker=broker,
            instrument=instrument, 
            order_type=order_type,
            status=status
        ).inc()
    
    def record_order_execution_time(self, broker: str, order_type: str, duration: float):
        """Record order execution latency"""
        ORDER_LATENCY.labels(broker=broker, order_type=order_type).observe(duration)
    
    def record_trade_volume(self, broker: str, instrument: str, direction: str, volume: float):
        """Record trade volume"""
        TRADE_VOLUME.labels(
            broker=broker,
            instrument=instrument,
            direction=direction
        ).inc(volume)
    
    def record_slippage(self, broker: str, instrument: str, slippage_pips: float):
        """Record trade slippage"""
        SLIPPAGE_HISTOGRAM.labels(broker=broker, instrument=instrument).observe(slippage_pips)
    
    # API Performance Metrics
    def record_api_request(self, broker: str, endpoint: str, method: str, duration: float, status_code: int = None):
        """Record API request metrics"""
        API_REQUEST_DURATION.labels(
            broker=broker,
            endpoint=endpoint,
            method=method
        ).observe(duration)
        
        if status_code and status_code >= 400:
            error_type = 'client_error' if status_code < 500 else 'server_error'
            API_ERROR_RATE.labels(
                broker=broker,
                endpoint=endpoint,
                error_code=str(status_code),
                error_type=error_type
            ).inc()
    
    def record_rate_limit_hit(self, broker: str, endpoint: str, limit_type: str):
        """Record rate limit violation"""
        RATE_LIMIT_HITS.labels(
            broker=broker,
            endpoint=endpoint,
            limit_type=limit_type
        ).inc()
    
    # Connection Metrics
    def update_connection_status(self, broker: str, account_id: str, environment: str, connected: bool):
        """Update connection status"""
        CONNECTION_STATUS.labels(
            broker=broker,
            account_id=account_id,
            environment=environment
        ).set(1 if connected else 0)
    
    def record_connection_time(self, broker: str, duration: float):
        """Record connection establishment time"""
        CONNECTION_DURATION.labels(broker=broker).observe(duration)
    
    def record_auth_attempt(self, broker: str, status: str, reason: str = ""):
        """Record authentication attempt"""
        AUTH_ATTEMPTS.labels(
            broker=broker,
            status=status,
            reason=reason or 'normal'
        ).inc()
    
    def record_session_end(self, broker: str, duration: float, reason: str):
        """Record session termination"""
        SESSION_DURATION.labels(
            broker=broker,
            termination_reason=reason
        ).observe(duration)
    
    # Circuit Breaker Metrics
    def update_circuit_breaker_state(self, broker: str, component: str, state: str):
        """Update circuit breaker state"""
        CIRCUIT_BREAKER_STATE.labels(
            broker=broker,
            component=component
        ).state(state)
    
    def record_reconnection_attempt(self, broker: str, trigger: str, status: str):
        """Record reconnection attempt"""
        RECONNECTION_ATTEMPTS.labels(
            broker=broker,
            trigger=trigger,
            status=status
        ).inc()
    
    def record_recovery_time(self, broker: str, failure_type: str, duration: float):
        """Record recovery time from failure"""
        RECOVERY_TIME.labels(
            broker=broker,
            failure_type=failure_type
        ).observe(duration)
    
    # Resource Utilization
    def update_connection_pool_metrics(self, broker: str, pool_type: str, total_size: int, active_connections: int):
        """Update connection pool metrics"""
        CONNECTION_POOL_SIZE.labels(broker=broker, pool_type=pool_type).set(total_size)
        CONNECTION_POOL_ACTIVE.labels(broker=broker, pool_type=pool_type).set(active_connections)
    
    def update_memory_usage(self, broker: str, component: str, memory_bytes: int):
        """Update memory usage metrics"""
        MEMORY_USAGE.labels(broker=broker, component=component).set(memory_bytes)
    
    # Data Quality Metrics
    def update_data_freshness(self, broker: str, data_type: str, age_seconds: float):
        """Update data freshness metrics"""
        DATA_FRESHNESS.labels(broker=broker, data_type=data_type).set(age_seconds)
    
    def record_market_data_gap(self, broker: str, instrument: str, gap_type: str):
        """Record market data gap"""
        MARKET_DATA_GAPS.labels(
            broker=broker,
            instrument=instrument,
            gap_type=gap_type
        ).inc()
    
    # Background Collection Tasks
    async def _collect_system_metrics(self):
        """Collect system-level metrics periodically"""
        while self.running:
            try:
                current_time = time.time()
                uptime = current_time - self.start_time
                
                # Update uptime for all brokers
                for broker in ['oanda', 'tradelocker', 'dxtrade']:
                    UPTIME.labels(broker=broker).set(uptime)
                
                await asyncio.sleep(self.config.collection_interval)
                
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
                await asyncio.sleep(30)
    
    async def _calculate_sla_metrics(self):
        """Calculate SLA compliance metrics"""
        while self.running:
            try:
                if self.config.enable_sla_tracking:
                    # Calculate availability SLA (target: 99.5%)
                    # Calculate latency SLA (target: p95 < 1s)
                    # Calculate error rate SLA (target: < 0.1%)
                    
                    for broker in ['oanda', 'tradelocker', 'dxtrade']:
                        # Placeholder calculations - would use actual metrics
                        availability_sla = 0.995  # 99.5%
                        latency_sla = 0.98       # 98% meeting latency target
                        error_rate_sla = 0.999   # 99.9% under error threshold
                        
                        SLA_COMPLIANCE.labels(broker=broker, sla_type='availability').set(availability_sla)
                        SLA_COMPLIANCE.labels(broker=broker, sla_type='latency').set(latency_sla)
                        SLA_COMPLIANCE.labels(broker=broker, sla_type='error_rate').set(error_rate_sla)
                
                await asyncio.sleep(60)  # Update SLA metrics every minute
                
            except Exception as e:
                logger.error(f"Error calculating SLA metrics: {e}")
                await asyncio.sleep(60)
    
    async def _update_business_kpis(self):
        """Update business KPI metrics"""
        while self.running:
            try:
                if self.config.enable_business_metrics:
                    # Calculate throughput metrics
                    # Calculate business performance indicators
                    
                    for broker in ['oanda', 'tradelocker', 'dxtrade']:
                        # Placeholder calculations
                        orders_per_second = 50.0
                        trades_per_second = 25.0
                        api_calls_per_second = 100.0
                        
                        THROUGHPUT.labels(broker=broker, operation_type='orders').set(orders_per_second)
                        THROUGHPUT.labels(broker=broker, operation_type='trades').set(trades_per_second)
                        THROUGHPUT.labels(broker=broker, operation_type='api_calls').set(api_calls_per_second)
                
                await asyncio.sleep(30)  # Update KPIs every 30 seconds
                
            except Exception as e:
                logger.error(f"Error updating business KPIs: {e}")
                await asyncio.sleep(60)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get current metrics summary"""
        return {
            'uptime_seconds': time.time() - self.start_time,
            'collection_running': self.running,
            'last_collection': self.last_collection,
            'config': {
                'collection_interval': self.config.collection_interval,
                'detailed_metrics_enabled': self.config.enable_detailed_metrics,
                'business_metrics_enabled': self.config.enable_business_metrics,
                'sla_tracking_enabled': self.config.enable_sla_tracking
            }
        }

# Global metrics collector instance
metrics_collector: Optional[BrokerMetricsCollector] = None

def get_metrics_collector() -> BrokerMetricsCollector:
    """Get or create global metrics collector"""
    global metrics_collector
    if metrics_collector is None:
        metrics_collector = BrokerMetricsCollector()
    return metrics_collector

def initialize_metrics(config: MetricsConfig = None, port: int = 9090):
    """Initialize metrics collection"""
    global metrics_collector
    metrics_collector = BrokerMetricsCollector(config)
    return metrics_collector.start_collection(port)