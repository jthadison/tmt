"""
Execution Engine Metrics and Monitoring

Comprehensive performance monitoring with Prometheus integration.
Tracks execution times, success rates, and system performance.
"""

import time
from typing import Dict, List, Optional

import structlog
from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server

from ..core.models import ExecutionMetrics, ExecutionResult, OrderStatus

logger = structlog.get_logger(__name__)


# Execution Performance Metrics
order_execution_duration = Histogram(
    'execution_order_duration_seconds',
    'Order execution duration in seconds',
    ['order_type', 'instrument', 'result'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
)

order_execution_total = Counter(
    'execution_orders_total',
    'Total number of order executions',
    ['order_type', 'instrument', 'status', 'result']
)

position_operations_duration = Histogram(
    'execution_position_duration_seconds',
    'Position operation duration in seconds',
    ['operation', 'instrument'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
)

position_operations_total = Counter(
    'execution_positions_total',
    'Total number of position operations',
    ['operation', 'instrument', 'result']
)

# Order Quality Metrics
order_slippage_basis_points = Histogram(
    'execution_slippage_basis_points',
    'Order slippage in basis points',
    ['instrument', 'order_type'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0]
)

order_fill_rate = Gauge(
    'execution_fill_rate_percent',
    'Order fill rate percentage',
    ['instrument', 'order_type']
)

order_rejection_rate = Gauge(
    'execution_rejection_rate_percent',
    'Order rejection rate percentage',
    ['instrument', 'error_type']
)

# Risk Management Metrics
risk_validation_duration = Histogram(
    'execution_risk_validation_seconds',
    'Risk validation duration in seconds',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.2]
)

risk_violations_total = Counter(
    'execution_risk_violations_total',
    'Total number of risk violations',
    ['account_id', 'violation_type']
)

kill_switch_activations = Counter(
    'execution_kill_switch_activations_total',
    'Total number of kill switch activations',
    ['account_id', 'reason']
)

# System Performance Metrics
active_orders_gauge = Gauge(
    'execution_active_orders',
    'Number of active orders',
    ['account_id']
)

open_positions_gauge = Gauge(
    'execution_open_positions',
    'Number of open positions',
    ['account_id', 'instrument']
)

memory_usage_bytes = Gauge(
    'execution_memory_usage_bytes',
    'Memory usage in bytes',
    ['component']
)

cpu_usage_percent = Gauge(
    'execution_cpu_usage_percent',
    'CPU usage percentage',
    ['component']
)

# OANDA Integration Metrics
oanda_request_duration = Histogram(
    'execution_oanda_request_seconds',
    'OANDA API request duration in seconds',
    ['endpoint', 'method', 'result'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
)

oanda_requests_total = Counter(
    'execution_oanda_requests_total',
    'Total number of OANDA API requests',
    ['endpoint', 'method', 'status_code']
)

oanda_connection_errors = Counter(
    'execution_oanda_connection_errors_total',
    'Total number of OANDA connection errors',
    ['error_type']
)

# Account Metrics
account_balance_gauge = Gauge(
    'execution_account_balance',
    'Account balance',
    ['account_id']
)

account_unrealized_pl_gauge = Gauge(
    'execution_account_unrealized_pl',
    'Account unrealized P&L',
    ['account_id']
)

account_margin_used_gauge = Gauge(
    'execution_account_margin_used',
    'Account margin used',
    ['account_id']
)

# System Info
system_info = Info(
    'execution_system_info',
    'System information'
)


class ExecutionMetricsCollector:
    """
    Comprehensive metrics collection for execution engine.
    
    Features:
    - Real-time performance tracking
    - Prometheus metrics export
    - Execution quality monitoring
    - System resource monitoring
    """
    
    def __init__(self, prometheus_port: int = 8091):
        self.prometheus_port = prometheus_port
        self.monitoring_active = False
        
        # Performance tracking
        self.execution_history: List[Dict] = []
        self.start_time = time.time()
        
        # Fill rate tracking
        self.fill_rates: Dict[str, Dict] = {}  # instrument -> {filled: int, total: int}
        
        logger.info("ExecutionMetricsCollector initialized", 
                   prometheus_port=prometheus_port)
    
    def start_monitoring(self) -> None:
        """Start Prometheus metrics server."""
        try:
            start_http_server(self.prometheus_port)
            self.monitoring_active = True
            
            # Set system info
            system_info.info({
                'version': '1.0.0',
                'component': 'execution-engine',
                'start_time': str(int(self.start_time))
            })
            
            logger.info("Metrics monitoring started", port=self.prometheus_port)
            
        except Exception as e:
            logger.error("Failed to start metrics monitoring", error=str(e))
    
    def stop_monitoring(self) -> None:
        """Stop metrics monitoring."""
        self.monitoring_active = False
        logger.info("Metrics monitoring stopped")
    
    async def record_order_execution(
        self,
        instrument: str,
        order_type: str,
        execution_time_ms: float,
        success: bool,
        result: ExecutionResult = None,
        status: OrderStatus = None,
        slippage_pips: Optional[float] = None
    ) -> None:
        """Record order execution metrics."""
        execution_time_seconds = execution_time_ms / 1000.0
        
        # Record execution duration
        result_label = "success" if success else "failure"
        order_execution_duration.labels(
            order_type=order_type,
            instrument=instrument,
            result=result_label
        ).observe(execution_time_seconds)
        
        # Record execution count
        status_label = status.value if status else "unknown"
        order_execution_total.labels(
            order_type=order_type,
            instrument=instrument,
            status=status_label,
            result=result_label
        ).inc()
        
        # Record slippage if available
        if slippage_pips is not None:
            slippage_bp = slippage_pips * 10  # Convert pips to basis points
            order_slippage_basis_points.labels(
                instrument=instrument,
                order_type=order_type
            ).observe(slippage_bp)
        
        # Update fill rate tracking
        self._update_fill_rate(instrument, order_type, success)
        
        # Store in execution history
        execution_record = {
            'timestamp': time.time(),
            'instrument': instrument,
            'order_type': order_type,
            'execution_time_ms': execution_time_ms,
            'success': success,
            'slippage_pips': slippage_pips,
        }
        self.execution_history.append(execution_record)
        
        # Keep only last 10000 records
        if len(self.execution_history) > 10000:
            self.execution_history = self.execution_history[-10000:]
        
        logger.debug("Order execution recorded",
                    instrument=instrument,
                    execution_time_ms=execution_time_ms,
                    success=success)
    
    async def record_order_modification(
        self,
        instrument: str,
        modification_time_ms: float,
        success: bool
    ) -> None:
        """Record order modification metrics."""
        modification_time_seconds = modification_time_ms / 1000.0
        result_label = "success" if success else "failure"
        
        order_execution_duration.labels(
            order_type="modification",
            instrument=instrument,
            result=result_label
        ).observe(modification_time_seconds)
        
        logger.debug("Order modification recorded",
                    instrument=instrument,
                    modification_time_ms=modification_time_ms,
                    success=success)
    
    async def record_order_cancellation(
        self,
        instrument: str,
        cancellation_time_ms: float,
        success: bool
    ) -> None:
        """Record order cancellation metrics."""
        cancellation_time_seconds = cancellation_time_ms / 1000.0
        result_label = "success" if success else "failure"
        
        order_execution_duration.labels(
            order_type="cancellation",
            instrument=instrument,
            result=result_label
        ).observe(cancellation_time_seconds)
        
        logger.debug("Order cancellation recorded",
                    instrument=instrument,
                    cancellation_time_ms=cancellation_time_ms,
                    success=success)
    
    async def record_position_operation(
        self,
        operation: str,  # "open", "close", "modify"
        instrument: str,
        duration_ms: float,
        success: bool
    ) -> None:
        """Record position operation metrics."""
        duration_seconds = duration_ms / 1000.0
        result_label = "success" if success else "failure"
        
        position_operations_duration.labels(
            operation=operation,
            instrument=instrument
        ).observe(duration_seconds)
        
        position_operations_total.labels(
            operation=operation,
            instrument=instrument,
            result=result_label
        ).inc()
        
        logger.debug("Position operation recorded",
                    operation=operation,
                    instrument=instrument,
                    duration_ms=duration_ms,
                    success=success)
    
    async def record_position_close(
        self,
        instrument: str,
        close_time_ms: float,
        success: bool
    ) -> None:
        """Record position close operation."""
        await self.record_position_operation("close", instrument, close_time_ms, success)
    
    def record_risk_validation(
        self,
        duration_ms: float,
        violation_type: Optional[str] = None,
        account_id: Optional[str] = None
    ) -> None:
        """Record risk validation metrics."""
        duration_seconds = duration_ms / 1000.0
        
        risk_validation_duration.observe(duration_seconds)
        
        if violation_type and account_id:
            risk_violations_total.labels(
                account_id=account_id,
                violation_type=violation_type
            ).inc()
        
        logger.debug("Risk validation recorded",
                    duration_ms=duration_ms,
                    violation_type=violation_type)
    
    def record_kill_switch_activation(self, account_id: str, reason: str) -> None:
        """Record kill switch activation."""
        kill_switch_activations.labels(
            account_id=account_id,
            reason=reason
        ).inc()
        
        logger.critical("Kill switch activation recorded",
                       account_id=account_id,
                       reason=reason)
    
    def update_active_orders(self, account_id: str, count: int) -> None:
        """Update active orders gauge."""
        active_orders_gauge.labels(account_id=account_id).set(count)
    
    def update_open_positions(self, account_id: str, instrument: str, count: int) -> None:
        """Update open positions gauge."""
        open_positions_gauge.labels(
            account_id=account_id,
            instrument=instrument
        ).set(count)
    
    def update_account_metrics(
        self,
        account_id: str,
        balance: float,
        unrealized_pl: float,
        margin_used: float
    ) -> None:
        """Update account financial metrics."""
        account_balance_gauge.labels(account_id=account_id).set(balance)
        account_unrealized_pl_gauge.labels(account_id=account_id).set(unrealized_pl)
        account_margin_used_gauge.labels(account_id=account_id).set(margin_used)
    
    def update_system_resources(
        self,
        component: str,
        memory_bytes: int,
        cpu_percent: float
    ) -> None:
        """Update system resource metrics."""
        memory_usage_bytes.labels(component=component).set(memory_bytes)
        cpu_usage_percent.labels(component=component).set(cpu_percent)
    
    def record_oanda_request(
        self,
        endpoint: str,
        method: str,
        duration_ms: float,
        status_code: int,
        success: bool
    ) -> None:
        """Record OANDA API request metrics."""
        duration_seconds = duration_ms / 1000.0
        result_label = "success" if success else "failure"
        
        oanda_request_duration.labels(
            endpoint=endpoint,
            method=method,
            result=result_label
        ).observe(duration_seconds)
        
        oanda_requests_total.labels(
            endpoint=endpoint,
            method=method,
            status_code=str(status_code)
        ).inc()
        
        logger.debug("OANDA request recorded",
                    endpoint=endpoint,
                    method=method,
                    duration_ms=duration_ms,
                    status_code=status_code)
    
    def record_oanda_connection_error(self, error_type: str) -> None:
        """Record OANDA connection error."""
        oanda_connection_errors.labels(error_type=error_type).inc()
        logger.error("OANDA connection error recorded", error_type=error_type)
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary statistics."""
        if not self.execution_history:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_execution_time_ms": 0.0,
                "p95_execution_time_ms": 0.0,
                "avg_slippage_pips": 0.0,
            }
        
        # Calculate statistics
        recent_executions = self.execution_history[-1000:]  # Last 1000 executions
        
        total_executions = len(recent_executions)
        successful_executions = sum(1 for e in recent_executions if e['success'])
        success_rate = successful_executions / total_executions if total_executions > 0 else 0.0
        
        execution_times = [e['execution_time_ms'] for e in recent_executions]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0.0
        
        # Calculate P95
        sorted_times = sorted(execution_times)
        p95_index = int(0.95 * len(sorted_times))
        p95_execution_time = sorted_times[p95_index] if sorted_times else 0.0
        
        # Calculate average slippage
        slippages = [e['slippage_pips'] for e in recent_executions if e.get('slippage_pips') is not None]
        avg_slippage = sum(slippages) / len(slippages) if slippages else 0.0
        
        return {
            "total_executions": total_executions,
            "success_rate": success_rate,
            "avg_execution_time_ms": avg_execution_time,
            "p95_execution_time_ms": p95_execution_time,
            "avg_slippage_pips": avg_slippage,
            "monitoring_active": self.monitoring_active,
            "uptime_seconds": time.time() - self.start_time,
        }
    
    def get_fill_rates(self) -> Dict[str, Dict]:
        """Get fill rates by instrument and order type."""
        fill_rate_data = {}
        
        for key, data in self.fill_rates.items():
            if data['total'] > 0:
                fill_rate = (data['filled'] / data['total']) * 100
                fill_rate_data[key] = {
                    'fill_rate_percent': fill_rate,
                    'filled_orders': data['filled'],
                    'total_orders': data['total']
                }
        
        return fill_rate_data
    
    # Private methods
    
    def _update_fill_rate(self, instrument: str, order_type: str, filled: bool) -> None:
        """Update fill rate tracking."""
        key = f"{instrument}_{order_type}"
        
        if key not in self.fill_rates:
            self.fill_rates[key] = {'filled': 0, 'total': 0}
        
        self.fill_rates[key]['total'] += 1
        if filled:
            self.fill_rates[key]['filled'] += 1
        
        # Update Prometheus gauge
        if self.fill_rates[key]['total'] > 0:
            fill_rate_percent = (self.fill_rates[key]['filled'] / self.fill_rates[key]['total']) * 100
            order_fill_rate.labels(
                instrument=instrument,
                order_type=order_type
            ).set(fill_rate_percent)