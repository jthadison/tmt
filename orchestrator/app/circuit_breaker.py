"""
Circuit Breaker System for Trading System Orchestrator

Implements various circuit breakers to prevent losses and maintain system safety.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel
from dataclasses import dataclass

from .config import get_settings
from .exceptions import CircuitBreakerException, SafetyException
from .event_bus import EventBus

logger = logging.getLogger(__name__)


class BreakerType(str, Enum):
    """Types of circuit breakers"""
    ACCOUNT_LOSS = "account_loss"
    DAILY_LOSS = "daily_loss"
    CONSECUTIVE_LOSSES = "consecutive_losses"
    CORRELATION = "correlation"
    VOLATILITY = "volatility"
    POSITION_SIZE = "position_size"
    RATE_LIMIT = "rate_limit"
    SYSTEM_HEALTH = "system_health"


class BreakerState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking all operations
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class BreakerStatus:
    """Circuit breaker status"""
    breaker_type: BreakerType
    state: BreakerState
    failure_count: int
    last_failure: Optional[datetime]
    last_success: Optional[datetime]
    opened_at: Optional[datetime]
    recovery_time: Optional[datetime]
    reason: Optional[str]


class TradingMetrics(BaseModel):
    """Trading metrics for breaker calculations"""
    account_id: str
    current_balance: float
    starting_balance: float
    daily_pnl: float
    consecutive_losses: int
    position_size: float
    trades_this_hour: int
    correlation_with_others: float
    market_volatility: float


class CircuitBreakerManager:
    """Manages all circuit breakers for the trading system"""
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.settings = get_settings()
        self.event_bus = event_bus
        self.breakers: Dict[str, BreakerStatus] = {}
        self.trading_metrics: Dict[str, TradingMetrics] = {}
        self._initialize_breakers()
        
    def _initialize_breakers(self):
        """Initialize all circuit breakers"""
        breaker_types = [
            BreakerType.ACCOUNT_LOSS,
            BreakerType.DAILY_LOSS,
            BreakerType.CONSECUTIVE_LOSSES,
            BreakerType.CORRELATION,
            BreakerType.VOLATILITY,
            BreakerType.POSITION_SIZE,
            BreakerType.RATE_LIMIT,
            BreakerType.SYSTEM_HEALTH
        ]
        
        for breaker_type in breaker_types:
            self.breakers[breaker_type] = BreakerStatus(
                breaker_type=breaker_type,
                state=BreakerState.CLOSED,
                failure_count=0,
                last_failure=None,
                last_success=None,
                opened_at=None,
                recovery_time=None,
                reason=None
            )
    
    async def check_all_breakers(self, account_id: str, operation: str = "trade") -> bool:
        """Check all circuit breakers for an account operation"""
        try:
            # Get current metrics for the account
            metrics = await self._get_trading_metrics(account_id)
            
            # Check each breaker
            breaker_checks = [
                self._check_account_loss_breaker(metrics),
                self._check_daily_loss_breaker(metrics),
                self._check_consecutive_losses_breaker(metrics),
                self._check_correlation_breaker(metrics),
                self._check_volatility_breaker(metrics),
                self._check_position_size_breaker(metrics),
                self._check_rate_limit_breaker(metrics),
                self._check_system_health_breaker()
            ]
            
            # Run all checks
            results = await asyncio.gather(*breaker_checks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Breaker check failed: {result}")
                elif not result:
                    breaker_type = list(BreakerType)[i]
                    await self._trigger_breaker(breaker_type, account_id, f"{operation} blocked")
                    return False
            
            # All checks passed
            await self._record_success(account_id)
            return True
            
        except Exception as e:
            logger.error(f"Circuit breaker check failed: {e}")
            await self._trigger_breaker(BreakerType.SYSTEM_HEALTH, account_id, f"Check failed: {e}")
            return False
    
    async def _check_account_loss_breaker(self, metrics: TradingMetrics) -> bool:
        """Check account loss circuit breaker"""
        loss_percentage = (metrics.starting_balance - metrics.current_balance) / metrics.starting_balance
        threshold = self.settings.get_circuit_breaker_threshold("account_loss")
        
        if loss_percentage >= threshold:
            logger.warning(f"Account loss breaker triggered: {loss_percentage:.2%} >= {threshold:.2%}")
            return False
        
        return True
    
    async def _check_daily_loss_breaker(self, metrics: TradingMetrics) -> bool:
        """Check daily loss circuit breaker"""
        if metrics.daily_pnl < 0:
            loss_percentage = abs(metrics.daily_pnl) / metrics.current_balance
            threshold = self.settings.get_circuit_breaker_threshold("daily_loss")
            
            if loss_percentage >= threshold:
                logger.warning(f"Daily loss breaker triggered: {loss_percentage:.2%} >= {threshold:.2%}")
                return False
        
        return True
    
    async def _check_consecutive_losses_breaker(self, metrics: TradingMetrics) -> bool:
        """Check consecutive losses circuit breaker"""
        threshold = self.settings.circuit_breaker_config.get("consecutive_losses", 5)
        
        if metrics.consecutive_losses >= threshold:
            logger.warning(f"Consecutive losses breaker triggered: {metrics.consecutive_losses} >= {threshold}")
            return False
        
        return True
    
    async def _check_correlation_breaker(self, metrics: TradingMetrics) -> bool:
        """Check correlation circuit breaker"""
        threshold = self.settings.circuit_breaker_config.get("correlation_threshold", 0.8)
        
        if metrics.correlation_with_others >= threshold:
            logger.warning(f"Correlation breaker triggered: {metrics.correlation_with_others:.2f} >= {threshold}")
            return False
        
        return True
    
    async def _check_volatility_breaker(self, metrics: TradingMetrics) -> bool:
        """Check volatility circuit breaker"""
        threshold = self.settings.circuit_breaker_config.get("volatility_threshold", 2.0)
        
        if metrics.market_volatility >= threshold:
            logger.warning(f"Volatility breaker triggered: {metrics.market_volatility:.2f} >= {threshold}")
            return False
        
        return True
    
    async def _check_position_size_breaker(self, metrics: TradingMetrics) -> bool:
        """Check position size circuit breaker"""
        threshold = self.settings.max_position_size
        
        if metrics.position_size >= threshold:
            logger.warning(f"Position size breaker triggered: {metrics.position_size} >= {threshold}")
            return False
        
        return True
    
    async def _check_rate_limit_breaker(self, metrics: TradingMetrics) -> bool:
        """Check rate limiting circuit breaker"""
        threshold = self.settings.max_trades_per_hour
        
        if metrics.trades_this_hour >= threshold:
            logger.warning(f"Rate limit breaker triggered: {metrics.trades_this_hour} >= {threshold}")
            return False
        
        return True
    
    async def _check_system_health_breaker(self) -> bool:
        """Check system health circuit breaker"""
        # Check if system health breaker is already open
        breaker = self.breakers[BreakerType.SYSTEM_HEALTH]
        
        if breaker.state == BreakerState.OPEN:
            # Check if recovery time has passed
            if breaker.recovery_time and datetime.utcnow() > breaker.recovery_time:
                # Try to recover
                await self._attempt_recovery(BreakerType.SYSTEM_HEALTH)
            else:
                return False
        
        return breaker.state != BreakerState.OPEN
    
    async def _trigger_breaker(self, breaker_type: BreakerType, account_id: str, reason: str):
        """Trigger a circuit breaker"""
        breaker = self.breakers[breaker_type]
        
        if breaker.state == BreakerState.CLOSED:
            breaker.state = BreakerState.OPEN
            breaker.opened_at = datetime.utcnow()
            breaker.reason = reason
            
            # Set recovery time
            recovery_minutes = self.settings.circuit_breaker_config.get("recovery_time_minutes", 30)
            breaker.recovery_time = datetime.utcnow() + timedelta(minutes=recovery_minutes)
            
            logger.error(f"Circuit breaker TRIGGERED: {breaker_type} for account {account_id} - {reason}")
            
            # Emit event
            if self.event_bus:
                await self.event_bus.emit_circuit_breaker_triggered(
                    breaker_type.value, account_id, reason
                )
            
            # Handle emergency actions
            await self._handle_emergency_actions(breaker_type, account_id)
        
        breaker.failure_count += 1
        breaker.last_failure = datetime.utcnow()
    
    async def _handle_emergency_actions(self, breaker_type: BreakerType, account_id: str):
        """Handle emergency actions when breaker is triggered"""
        if breaker_type in [BreakerType.ACCOUNT_LOSS, BreakerType.DAILY_LOSS]:
            if self.settings.emergency_close_positions:
                logger.critical(f"EMERGENCY: Closing all positions for account {account_id}")
                # TODO: Implement emergency position closing
                await self._emergency_close_positions(account_id)
        
        elif breaker_type == BreakerType.SYSTEM_HEALTH:
            logger.critical("EMERGENCY: System health breaker triggered - stopping all trading")
            # TODO: Implement system-wide emergency stop
            await self._emergency_system_stop()
    
    async def _emergency_close_positions(self, account_id: str):
        """Emergency close all positions for an account"""
        # TODO: Implement emergency position closing
        # This would integrate with the OANDA client
        logger.info(f"Emergency position closure initiated for account {account_id}")
    
    async def _emergency_system_stop(self):
        """Emergency stop of the entire system"""
        # TODO: Implement system-wide emergency stop
        # This would stop all agents and trading activities
        logger.critical("Emergency system stop initiated")
    
    async def _attempt_recovery(self, breaker_type: BreakerType):
        """Attempt to recover from a circuit breaker state"""
        breaker = self.breakers[breaker_type]
        
        if breaker.state == BreakerState.OPEN:
            breaker.state = BreakerState.HALF_OPEN
            logger.info(f"Circuit breaker {breaker_type} attempting recovery")
            
            # TODO: Implement specific recovery checks for each breaker type
            # For now, assume recovery is successful after timeout
            breaker.state = BreakerState.CLOSED
            breaker.failure_count = 0
            breaker.opened_at = None
            breaker.recovery_time = None
            breaker.reason = None
            
            logger.info(f"Circuit breaker {breaker_type} recovered")
    
    async def _record_success(self, account_id: str):
        """Record successful operation"""
        for breaker in self.breakers.values():
            breaker.last_success = datetime.utcnow()
    
    async def _get_trading_metrics(self, account_id: str) -> TradingMetrics:
        """Get current trading metrics for an account"""
        # TODO: Implement actual metrics collection
        # This would integrate with the trading data and OANDA client
        
        # For now, return mock metrics
        return TradingMetrics(
            account_id=account_id,
            current_balance=100000.0,
            starting_balance=100000.0,
            daily_pnl=0.0,
            consecutive_losses=0,
            position_size=0.0,
            trades_this_hour=0,
            correlation_with_others=0.0,
            market_volatility=1.0
        )
    
    def get_breaker_status(self, breaker_type: BreakerType) -> BreakerStatus:
        """Get status of a specific circuit breaker"""
        return self.breakers[breaker_type]
    
    def get_all_breaker_status(self) -> Dict[str, BreakerStatus]:
        """Get status of all circuit breakers"""
        return {bt.value: status for bt, status in self.breakers.items()}
    
    def is_system_healthy(self) -> bool:
        """Check if the system is healthy (no breakers open)"""
        return all(breaker.state != BreakerState.OPEN for breaker in self.breakers.values())
    
    async def force_open_breaker(self, breaker_type: BreakerType, reason: str):
        """Manually open a circuit breaker"""
        await self._trigger_breaker(breaker_type, "manual", reason)
    
    async def force_close_breaker(self, breaker_type: BreakerType):
        """Manually close a circuit breaker"""
        breaker = self.breakers[breaker_type]
        breaker.state = BreakerState.CLOSED
        breaker.failure_count = 0
        breaker.opened_at = None
        breaker.recovery_time = None
        breaker.reason = None
        
        logger.info(f"Circuit breaker {breaker_type} manually closed")
    
    async def reset_all_breakers(self):
        """Reset all circuit breakers to closed state"""
        for breaker_type in self.breakers:
            await self.force_close_breaker(breaker_type)
        
        logger.info("All circuit breakers reset to closed state")
    
    async def get_status(self) -> any:
        """Get overall circuit breaker system status"""
        from .models import CircuitBreakerStatus
        
        open_breakers = [bt.value for bt, status in self.breakers.items() 
                        if status.state == BreakerState.OPEN]
        
        overall_status = "closed"
        if open_breakers:
            overall_status = "open"
        
        # Convert breakers to string status
        account_breakers = {}
        system_breakers = {}
        
        for bt, status in self.breakers.items():
            status_str = status.state.value
            if bt in [BreakerType.ACCOUNT_LOSS, BreakerType.DAILY_LOSS, BreakerType.CONSECUTIVE_LOSSES]:
                account_breakers[bt.value] = status_str
            else:
                system_breakers[bt.value] = status_str
        
        return CircuitBreakerStatus(
            overall_status=overall_status,
            account_breakers=account_breakers,
            system_breakers=system_breakers,
            triggers_today=sum(1 for status in self.breakers.values() if status.failure_count > 0),
            last_trigger=max((status.last_failure for status in self.breakers.values() if status.last_failure), default=None),
            can_trade=self.can_trade()
        )
    
    def can_trade(self) -> bool:
        """Check if trading is allowed (no critical breakers open)"""
        critical_breakers = [
            BreakerType.ACCOUNT_LOSS,
            BreakerType.DAILY_LOSS, 
            BreakerType.SYSTEM_HEALTH
        ]
        
        for breaker_type in critical_breakers:
            if self.breakers[breaker_type].state == BreakerState.OPEN:
                return False
        
        return True
    
    async def trigger_emergency_stop(self, reason: str):
        """Trigger emergency stop by opening system health breaker"""
        await self._trigger_breaker(BreakerType.SYSTEM_HEALTH, "system", reason)
    
    async def health_check(self):
        """Perform health check on circuit breaker system"""
        # This is called by the orchestrator health check loop
        # Just ensure all breakers are functioning
        pass