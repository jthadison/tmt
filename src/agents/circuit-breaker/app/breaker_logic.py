"""
Circuit Breaker Logic Implementation

Implements the three-tier circuit breaker system (agent/account/system level)
with state management, trigger conditions, and recovery logic.
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque

import structlog
from .models import (
    BreakerLevel, BreakerState, TriggerReason, BreakerStatus,
    SystemHealth, MarketConditions, AccountMetrics
)
from .config import config

logger = structlog.get_logger(__name__)


class CircuitBreakerManager:
    """
    Manages the three-tier circuit breaker system with state persistence
    and automatic recovery logic.
    """
    
    def __init__(self):
        self.agent_breakers: Dict[str, BreakerStatus] = {}
        self.account_breakers: Dict[str, BreakerStatus] = {}
        self.system_breaker = BreakerStatus(
            level=BreakerLevel.SYSTEM,
            state=BreakerState.NORMAL
        )
        
        # Metrics tracking
        self.error_counters: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.response_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.health_history: deque = deque(maxlen=1000)
        
        # Recovery tasks
        self._recovery_tasks: Dict[str, asyncio.Task] = {}
        
        logger.info("Circuit breaker manager initialized")
    
    async def check_and_update_breakers(
        self, 
        health_metrics: SystemHealth,
        market_conditions: Optional[MarketConditions] = None,
        account_metrics: Optional[Dict[str, AccountMetrics]] = None
    ) -> Dict[str, Any]:
        """
        Check all breaker conditions and update states accordingly.
        
        Args:
            health_metrics: Current system health metrics
            market_conditions: Current market conditions
            account_metrics: Per-account metrics
            
        Returns:
            Dictionary with update results and triggered breakers
        """
        start_time = time.time()
        
        try:
            # Store health metrics for trending
            self.health_history.append({
                'timestamp': datetime.now(timezone.utc),
                'metrics': health_metrics
            })
            
            triggered_breakers = []
            
            # Check system-level conditions first (highest priority)
            system_result = await self._check_system_breakers(
                health_metrics, market_conditions, account_metrics
            )
            if system_result:
                triggered_breakers.append(system_result)
            
            # Check account-level breakers if system is not tripped
            if self.system_breaker.state != BreakerState.TRIPPED:
                account_results = await self._check_account_breakers(
                    account_metrics or {}
                )
                triggered_breakers.extend(account_results)
            
            # Check agent-level breakers if system is not tripped
            if self.system_breaker.state != BreakerState.TRIPPED:
                agent_results = await self._check_agent_breakers(health_metrics)
                triggered_breakers.extend(agent_results)
            
            # Update recovery states
            await self._update_recovery_states()
            
            response_time = int((time.time() - start_time) * 1000)
            
            return {
                'triggered_breakers': triggered_breakers,
                'system_state': self.system_breaker.state.value,
                'response_time_ms': response_time,
                'total_breakers_tripped': len([
                    b for b in self.agent_breakers.values() 
                    if b.state == BreakerState.TRIPPED
                ]) + len([
                    b for b in self.account_breakers.values() 
                    if b.state == BreakerState.TRIPPED
                ]) + (1 if self.system_breaker.state == BreakerState.TRIPPED else 0)
            }
            
        except Exception as e:
            logger.exception("Error checking circuit breakers", error=str(e))
            raise
    
    async def _check_system_breakers(
        self,
        health_metrics: SystemHealth,
        market_conditions: Optional[MarketConditions],
        account_metrics: Optional[Dict[str, AccountMetrics]]
    ) -> Optional[Dict[str, Any]]:
        """Check system-level breaker conditions"""
        
        # Check max drawdown across all accounts
        if account_metrics:
            max_drawdown = max(
                (metrics.max_drawdown for metrics in account_metrics.values()),
                default=0.0
            )
            
            if max_drawdown > config.max_drawdown_threshold:
                await self._trigger_breaker(
                    BreakerLevel.SYSTEM,
                    "system",
                    TriggerReason.MAX_DRAWDOWN,
                    {"max_drawdown": max_drawdown, "threshold": config.max_drawdown_threshold}
                )
                return {
                    "level": "system",
                    "reason": "max_drawdown",
                    "details": {"drawdown": max_drawdown}
                }
        
        # Check system error rate
        if health_metrics.error_rate > config.error_rate_threshold:
            await self._trigger_breaker(
                BreakerLevel.SYSTEM,
                "system",
                TriggerReason.ERROR_RATE,
                {"error_rate": health_metrics.error_rate, "threshold": config.error_rate_threshold}
            )
            return {
                "level": "system", 
                "reason": "error_rate",
                "details": {"error_rate": health_metrics.error_rate}
            }
        
        # Check response time
        if health_metrics.response_time > config.response_time_threshold:
            await self._trigger_breaker(
                BreakerLevel.SYSTEM,
                "system",
                TriggerReason.RESPONSE_TIME,
                {"response_time": health_metrics.response_time, "threshold": config.response_time_threshold}
            )
            return {
                "level": "system",
                "reason": "response_time", 
                "details": {"response_time": health_metrics.response_time}
            }
        
        # Check market conditions
        if market_conditions:
            if market_conditions.volatility > config.volatility_spike_threshold:
                await self._trigger_breaker(
                    BreakerLevel.SYSTEM,
                    "system",
                    TriggerReason.VOLATILITY_SPIKE,
                    {"volatility": market_conditions.volatility, "threshold": config.volatility_spike_threshold}
                )
                return {
                    "level": "system",
                    "reason": "volatility_spike",
                    "details": {"volatility": market_conditions.volatility}
                }
            
            if market_conditions.gap_detected and market_conditions.gap_size and market_conditions.gap_size > 0.05:
                await self._trigger_breaker(
                    BreakerLevel.SYSTEM,
                    "system",
                    TriggerReason.GAP_DETECTION,
                    {"gap_size": market_conditions.gap_size}
                )
                return {
                    "level": "system",
                    "reason": "gap_detection",
                    "details": {"gap_size": market_conditions.gap_size}
                }
        
        return None
    
    async def _check_account_breakers(
        self, 
        account_metrics: Dict[str, AccountMetrics]
    ) -> List[Dict[str, Any]]:
        """Check account-level breaker conditions"""
        triggered = []
        
        for account_id, metrics in account_metrics.items():
            # Check daily drawdown
            if metrics.daily_drawdown > config.daily_drawdown_threshold:
                await self._trigger_breaker(
                    BreakerLevel.ACCOUNT,
                    account_id,
                    TriggerReason.DAILY_DRAWDOWN,
                    {
                        "daily_drawdown": metrics.daily_drawdown,
                        "threshold": config.daily_drawdown_threshold
                    }
                )
                triggered.append({
                    "level": "account",
                    "account_id": account_id,
                    "reason": "daily_drawdown",
                    "details": {"drawdown": metrics.daily_drawdown}
                })
        
        return triggered
    
    async def _check_agent_breakers(
        self, 
        health_metrics: SystemHealth
    ) -> List[Dict[str, Any]]:
        """Check agent-level breaker conditions"""
        triggered = []
        
        # For now, we'll check general system health for agent breakers
        # In a full implementation, this would check individual agent metrics
        
        if health_metrics.cpu_usage > 90:
            await self._trigger_breaker(
                BreakerLevel.AGENT,
                "system-agent",
                TriggerReason.SYSTEM_FAILURE,
                {"cpu_usage": health_metrics.cpu_usage}
            )
            triggered.append({
                "level": "agent",
                "agent_id": "system-agent",
                "reason": "high_cpu",
                "details": {"cpu_usage": health_metrics.cpu_usage}
            })
        
        if health_metrics.memory_usage > 90:
            await self._trigger_breaker(
                BreakerLevel.AGENT,
                "system-agent",
                TriggerReason.SYSTEM_FAILURE,
                {"memory_usage": health_metrics.memory_usage}
            )
            triggered.append({
                "level": "agent",
                "agent_id": "system-agent", 
                "reason": "high_memory",
                "details": {"memory_usage": health_metrics.memory_usage}
            })
        
        return triggered
    
    async def _trigger_breaker(
        self,
        level: BreakerLevel,
        identifier: str,
        reason: TriggerReason,
        details: Dict[str, Any]
    ) -> None:
        """
        Trigger a circuit breaker with the specified parameters.
        
        Args:
            level: Breaker level (agent/account/system)
            identifier: Agent ID, account ID, or "system"
            reason: Trigger reason
            details: Additional details
        """
        now = datetime.now(timezone.utc)
        
        # Determine timeout based on level
        timeout_seconds = {
            BreakerLevel.AGENT: config.agent_breaker_timeout,
            BreakerLevel.ACCOUNT: config.account_breaker_timeout,
            BreakerLevel.SYSTEM: config.system_breaker_timeout
        }[level]
        
        recovery_timeout = now + timedelta(seconds=timeout_seconds)
        
        breaker_status = BreakerStatus(
            level=level,
            state=BreakerState.TRIPPED,
            triggered_at=now,
            trigger_reason=reason,
            trigger_details=details,
            failure_count=1,
            recovery_timeout=recovery_timeout
        )
        
        # Store in appropriate collection
        if level == BreakerLevel.AGENT:
            self.agent_breakers[identifier] = breaker_status
        elif level == BreakerLevel.ACCOUNT:
            self.account_breakers[identifier] = breaker_status
        else:  # SYSTEM
            self.system_breaker = breaker_status
        
        # Schedule recovery task
        task_key = f"{level.value}-{identifier}"
        if task_key in self._recovery_tasks:
            self._recovery_tasks[task_key].cancel()
        
        self._recovery_tasks[task_key] = asyncio.create_task(
            self._schedule_recovery(level, identifier, timeout_seconds)
        )
        
        logger.critical(
            "Circuit breaker triggered",
            level=level.value,
            identifier=identifier,
            reason=reason.value,
            details=details,
            recovery_timeout=recovery_timeout.isoformat()
        )
    
    async def _schedule_recovery(
        self, 
        level: BreakerLevel, 
        identifier: str, 
        timeout_seconds: int
    ) -> None:
        """Schedule automatic recovery after timeout"""
        try:
            await asyncio.sleep(timeout_seconds)
            await self._attempt_recovery(level, identifier)
        except asyncio.CancelledError:
            logger.info(
                "Recovery task cancelled",
                level=level.value,
                identifier=identifier
            )
        except Exception as e:
            logger.exception(
                "Error in recovery task",
                level=level.value,
                identifier=identifier,
                error=str(e)
            )
    
    async def _attempt_recovery(self, level: BreakerLevel, identifier: str) -> None:
        """Attempt to recover a circuit breaker to half-open state"""
        now = datetime.now(timezone.utc)
        
        # Get current breaker status
        breaker = None
        if level == BreakerLevel.AGENT and identifier in self.agent_breakers:
            breaker = self.agent_breakers[identifier]
        elif level == BreakerLevel.ACCOUNT and identifier in self.account_breakers:
            breaker = self.account_breakers[identifier]
        elif level == BreakerLevel.SYSTEM:
            breaker = self.system_breaker
        
        if not breaker or breaker.state != BreakerState.TRIPPED:
            return
        
        # Transition to half-open state
        breaker.state = BreakerState.HALF_OPEN
        breaker.reset_at = now
        breaker.success_count = 0
        
        logger.info(
            "Circuit breaker moved to half-open state",
            level=level.value,
            identifier=identifier
        )
    
    async def _update_recovery_states(self) -> None:
        """Update breakers in half-open state based on success/failure counts"""
        now = datetime.now(timezone.utc)
        
        # Check all breakers in half-open state
        for breakers in [self.agent_breakers.values(), self.account_breakers.values(), [self.system_breaker]]:
            for breaker in breakers:
                if breaker.state == BreakerState.HALF_OPEN:
                    # If we have 3 consecutive successes, fully recover
                    if breaker.success_count >= 3:
                        breaker.state = BreakerState.NORMAL
                        breaker.reset_at = now
                        breaker.failure_count = 0
                        breaker.success_count = 0
                        
                        logger.info(
                            "Circuit breaker fully recovered",
                            level=breaker.level.value
                        )
    
    async def manual_trigger(
        self, 
        level: BreakerLevel, 
        identifier: str = "manual",
        reason: str = "manual_intervention"
    ) -> bool:
        """
        Manually trigger a circuit breaker.
        
        Args:
            level: Breaker level to trigger
            identifier: Identifier for the breaker
            reason: Reason for manual trigger
            
        Returns:
            True if successfully triggered
        """
        try:
            await self._trigger_breaker(
                level,
                identifier,
                TriggerReason.MANUAL_TRIGGER,
                {"reason": reason, "triggered_by": "manual"}
            )
            return True
        except Exception as e:
            logger.exception("Failed to manually trigger circuit breaker", error=str(e))
            return False
    
    async def manual_reset(
        self, 
        level: BreakerLevel, 
        identifier: str = "system"
    ) -> bool:
        """
        Manually reset a circuit breaker to normal state.
        
        Args:
            level: Breaker level to reset
            identifier: Identifier for the breaker
            
        Returns:
            True if successfully reset
        """
        try:
            now = datetime.now(timezone.utc)
            
            if level == BreakerLevel.AGENT and identifier in self.agent_breakers:
                breaker = self.agent_breakers[identifier]
            elif level == BreakerLevel.ACCOUNT and identifier in self.account_breakers:
                breaker = self.account_breakers[identifier]
            elif level == BreakerLevel.SYSTEM:
                breaker = self.system_breaker
            else:
                return False
            
            breaker.state = BreakerState.NORMAL
            breaker.reset_at = now
            breaker.failure_count = 0
            breaker.success_count = 0
            breaker.last_failure_at = None
            
            logger.info(
                "Circuit breaker manually reset",
                level=level.value,
                identifier=identifier
            )
            return True
            
        except Exception as e:
            logger.exception("Failed to manually reset circuit breaker", error=str(e))
            return False
    
    def get_all_breaker_status(self) -> Dict[str, Any]:
        """Get status of all circuit breakers"""
        return {
            "agent_breakers": {
                agent_id: breaker.dict() 
                for agent_id, breaker in self.agent_breakers.items()
            },
            "account_breakers": {
                account_id: breaker.dict() 
                for account_id, breaker in self.account_breakers.items()
            },
            "system_breaker": self.system_breaker.dict(),
            "overall_healthy": (
                self.system_breaker.state == BreakerState.NORMAL and
                all(b.state == BreakerState.NORMAL for b in self.agent_breakers.values()) and
                all(b.state == BreakerState.NORMAL for b in self.account_breakers.values())
            )
        }
    
    def record_success(self, level: BreakerLevel, identifier: str) -> None:
        """Record a successful operation for recovery tracking"""
        breaker = None
        
        if level == BreakerLevel.AGENT and identifier in self.agent_breakers:
            breaker = self.agent_breakers[identifier]
        elif level == BreakerLevel.ACCOUNT and identifier in self.account_breakers:
            breaker = self.account_breakers[identifier]
        elif level == BreakerLevel.SYSTEM:
            breaker = self.system_breaker
        
        if breaker and breaker.state == BreakerState.HALF_OPEN:
            breaker.success_count += 1
    
    def record_failure(self, level: BreakerLevel, identifier: str) -> None:
        """Record a failed operation"""
        now = datetime.now(timezone.utc)
        breaker = None
        
        if level == BreakerLevel.AGENT:
            if identifier not in self.agent_breakers:
                self.agent_breakers[identifier] = BreakerStatus(
                    level=level,
                    state=BreakerState.NORMAL
                )
            breaker = self.agent_breakers[identifier]
        elif level == BreakerLevel.ACCOUNT:
            if identifier not in self.account_breakers:
                self.account_breakers[identifier] = BreakerStatus(
                    level=level,
                    state=BreakerState.NORMAL
                )
            breaker = self.account_breakers[identifier]
        elif level == BreakerLevel.SYSTEM:
            breaker = self.system_breaker
        
        if breaker:
            breaker.failure_count += 1
            breaker.last_failure_at = now
            
            # If in half-open state and we get a failure, go back to tripped
            if breaker.state == BreakerState.HALF_OPEN:
                breaker.state = BreakerState.TRIPPED
                breaker.success_count = 0