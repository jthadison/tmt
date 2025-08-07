"""
Health Monitor Implementation

Continuous system health monitoring with real-time metrics collection
and breaker condition evaluation.
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
import psutil
import structlog

from .models import SystemHealth, MarketConditions, AccountMetrics
from .config import config

logger = structlog.get_logger(__name__)


class HealthMonitor:
    """
    Continuous health monitoring system that collects metrics
    and evaluates circuit breaker conditions.
    """
    
    def __init__(self, breaker_manager, emergency_stop_manager):
        self.breaker_manager = breaker_manager
        self.emergency_stop_manager = emergency_stop_manager
        self.is_running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._health_callbacks: List[Callable[[SystemHealth], None]] = []
        self._last_health_check = None
        
        # Metrics tracking
        self.response_times: List[float] = []
        self.error_counts: Dict[str, int] = {}
        self.connection_counts: int = 0
        
        logger.info("Health monitor initialized")
    
    def add_health_callback(self, callback: Callable[[SystemHealth], None]) -> None:
        """Add callback to be notified of health updates"""
        self._health_callbacks.append(callback)
    
    async def start_monitoring(self) -> None:
        """Start continuous health monitoring"""
        if self.is_running:
            logger.warning("Health monitoring already running")
            return
        
        self.is_running = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info(
            "Health monitoring started",
            interval_seconds=config.health_check_interval
        )
    
    async def stop_monitoring(self) -> None:
        """Stop health monitoring"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Health monitoring stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        try:
            while self.is_running:
                start_time = time.time()
                
                try:
                    # Collect system health metrics
                    health_metrics = await self._collect_health_metrics()
                    self._last_health_check = health_metrics
                    
                    # Collect market conditions (simulated for now)
                    market_conditions = await self._collect_market_conditions()
                    
                    # Collect account metrics (simulated for now)
                    account_metrics = await self._collect_account_metrics()
                    
                    # Check and update circuit breakers
                    breaker_results = await self.breaker_manager.check_and_update_breakers(
                        health_metrics=health_metrics,
                        market_conditions=market_conditions,
                        account_metrics=account_metrics
                    )
                    
                    # Log significant events
                    if breaker_results['triggered_breakers']:
                        logger.warning(
                            "Circuit breakers triggered",
                            triggered_breakers=breaker_results['triggered_breakers'],
                            response_time_ms=breaker_results['response_time_ms']
                        )
                    
                    # Notify callbacks
                    for callback in self._health_callbacks:
                        try:
                            callback(health_metrics)
                        except Exception as e:
                            logger.exception("Health callback failed", error=str(e))
                    
                    # Calculate loop time and sleep
                    loop_time = time.time() - start_time
                    sleep_time = max(0, config.health_check_interval - loop_time)
                    
                    if loop_time > config.health_check_interval:
                        logger.warning(
                            "Health monitoring loop took longer than interval",
                            loop_time_seconds=loop_time,
                            interval_seconds=config.health_check_interval
                        )
                    
                    await asyncio.sleep(sleep_time)
                    
                except Exception as e:
                    logger.exception("Error in health monitoring loop", error=str(e))
                    await asyncio.sleep(config.health_check_interval)
                    
        except asyncio.CancelledError:
            logger.info("Health monitoring loop cancelled")
        except Exception as e:
            logger.exception("Health monitoring loop failed", error=str(e))
    
    async def _collect_health_metrics(self) -> SystemHealth:
        """Collect current system health metrics"""
        start_time = time.time()
        
        try:
            # Get system metrics
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Calculate error rate (simplified)
            total_operations = sum(self.error_counts.values()) + 100  # Assume some successful ops
            total_errors = sum(self.error_counts.values())
            error_rate = total_errors / total_operations if total_operations > 0 else 0.0
            
            # Calculate response time (use recent average)
            avg_response_time = 50  # Default
            if self.response_times:
                avg_response_time = int(sum(self.response_times[-10:]) / len(self.response_times[-10:]))
            
            collection_time = int((time.time() - start_time) * 1000)
            
            health = SystemHealth(
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=(disk.used / disk.total) * 100,
                error_rate=error_rate,
                response_time=max(avg_response_time, collection_time),
                active_connections=self.connection_counts
            )
            
            # Clean up old response times
            if len(self.response_times) > 100:
                self.response_times = self.response_times[-50:]
            
            return health
            
        except Exception as e:
            logger.exception("Failed to collect health metrics", error=str(e))
            # Return degraded health state
            return SystemHealth(
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                error_rate=1.0,  # 100% error rate
                response_time=5000,  # High response time
                active_connections=0
            )
    
    async def _collect_market_conditions(self) -> Optional[MarketConditions]:
        """
        Collect current market conditions.
        In a real implementation, this would connect to market data feeds.
        """
        try:
            # Simulated market conditions for testing
            import random
            
            # Generate realistic market conditions
            base_volatility = 0.2  # 20% annual volatility
            volatility_spike = random.uniform(0.8, 1.5)  # Normal range
            
            # Occasionally simulate extreme conditions
            if random.random() < 0.01:  # 1% chance
                volatility_spike = random.uniform(3.0, 5.0)  # Extreme volatility
            
            gap_detected = random.random() < 0.001  # 0.1% chance
            gap_size = random.uniform(0.01, 0.1) if gap_detected else None
            
            return MarketConditions(
                volatility=base_volatility * volatility_spike,
                gap_detected=gap_detected,
                gap_size=gap_size,
                correlation_breakdown=random.random() < 0.005,  # 0.5% chance
                unusual_volume=random.random() < 0.02,  # 2% chance
                circuit_breaker_triggered=False  # Will be updated by exchange data
            )
            
        except Exception as e:
            logger.exception("Failed to collect market conditions", error=str(e))
            return None
    
    async def _collect_account_metrics(self) -> Optional[Dict[str, AccountMetrics]]:
        """
        Collect account-specific metrics.
        In a real implementation, this would query the database.
        """
        try:
            # Simulated account metrics for testing
            import random
            
            accounts = {}
            account_ids = ["account_1", "account_2", "account_3"]
            
            for account_id in account_ids:
                # Generate realistic account metrics
                daily_pnl = random.uniform(-1000, 1000)
                
                # Calculate drawdowns (simplified)
                daily_drawdown = max(0, -daily_pnl / 10000) if daily_pnl < 0 else 0
                max_drawdown = random.uniform(0, 0.12)  # Up to 12%
                
                # Occasionally simulate high drawdown scenarios
                if random.random() < 0.02:  # 2% chance
                    daily_drawdown = random.uniform(0.06, 0.15)  # 6-15% drawdown
                
                if random.random() < 0.01:  # 1% chance
                    max_drawdown = random.uniform(0.09, 0.20)  # 9-20% max drawdown
                
                accounts[account_id] = AccountMetrics(
                    account_id=account_id,
                    daily_pnl=daily_pnl,
                    daily_drawdown=daily_drawdown,
                    max_drawdown=max_drawdown,
                    position_count=random.randint(0, 10),
                    total_exposure=random.uniform(5000, 50000),
                    last_trade_time=datetime.now(timezone.utc) - timedelta(minutes=random.randint(1, 30))
                )
            
            return accounts
            
        except Exception as e:
            logger.exception("Failed to collect account metrics", error=str(e))
            return None
    
    def record_response_time(self, response_time_ms: float) -> None:
        """Record a response time measurement"""
        self.response_times.append(response_time_ms)
    
    def record_error(self, error_type: str) -> None:
        """Record an error occurrence"""
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
    
    def update_connection_count(self, count: int) -> None:
        """Update active connection count"""
        self.connection_counts = count
    
    def get_current_health(self) -> Optional[SystemHealth]:
        """Get the most recent health metrics"""
        return self._last_health_check
    
    async def run_health_check(self) -> SystemHealth:
        """Run a one-time health check"""
        return await self._collect_health_metrics()
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get a summary of health monitoring status"""
        return {
            "monitoring_active": self.is_running,
            "last_check": self._last_health_check.timestamp if self._last_health_check else None,
            "callback_count": len(self._health_callbacks),
            "error_types": list(self.error_counts.keys()),
            "total_errors": sum(self.error_counts.values()),
            "active_connections": self.connection_counts,
            "response_time_samples": len(self.response_times)
        }
    
    async def simulate_high_load(self, duration_seconds: int = 60) -> None:
        """
        Simulate high system load for testing purposes.
        WARNING: Only for testing/demo environments!
        """
        if config.is_production:
            logger.error("Load simulation not allowed in production")
            return
        
        logger.warning(
            "Simulating high system load",
            duration_seconds=duration_seconds
        )
        
        # Simulate high CPU usage
        async def cpu_load():
            end_time = time.time() + duration_seconds
            while time.time() < end_time:
                # Busy work to increase CPU usage
                sum(i * i for i in range(10000))
                await asyncio.sleep(0.01)
        
        # Simulate high error rate
        for i in range(50):
            self.record_error("simulated_error")
        
        # Simulate high response times
        for i in range(20):
            self.record_response_time(random.uniform(200, 800))
        
        # Run CPU load simulation
        await cpu_load()
        
        logger.info("Load simulation completed")
    
    async def cleanup(self) -> None:
        """Cleanup health monitor resources"""
        await self.stop_monitoring()
        logger.info("Health monitor cleaned up")