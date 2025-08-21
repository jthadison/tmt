"""
Safety Monitor for Trading System Orchestrator

Provides real-time monitoring and safety checks for trading operations.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import statistics

from .config import get_settings
from .circuit_breaker import CircuitBreakerManager, TradingMetrics
from .oanda_client import OandaClient
from .event_bus import EventBus
from .exceptions import SafetyException

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """Safety alert levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class SafetyAlert:
    """Safety alert information"""
    alert_id: str
    level: AlertLevel
    title: str
    message: str
    account_id: Optional[str]
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class RiskMetrics:
    """Risk metrics for an account"""
    account_id: str
    current_balance: float
    starting_balance: float
    daily_pnl: float
    unrealized_pnl: float
    total_exposure: float
    position_count: int
    largest_position: float
    correlation_score: float
    volatility_score: float
    drawdown_percentage: float
    consecutive_losses: int
    trades_today: int
    last_trade_time: Optional[datetime]
    risk_score: float = 0.0


class PerformanceTracker:
    """Tracks trading performance metrics"""
    
    def __init__(self):
        self.daily_pnl: Dict[str, List[float]] = {}
        self.trade_outcomes: Dict[str, List[bool]] = {}
        self.position_sizes: Dict[str, List[float]] = {}
        self.correlation_matrix: Dict[str, Dict[str, float]] = {}
        
    def update_daily_pnl(self, account_id: str, pnl: float):
        """Update daily P&L for an account"""
        if account_id not in self.daily_pnl:
            self.daily_pnl[account_id] = []
        
        self.daily_pnl[account_id].append(pnl)
        
        # Keep only last 30 days
        if len(self.daily_pnl[account_id]) > 30:
            self.daily_pnl[account_id] = self.daily_pnl[account_id][-30:]
    
    def update_trade_outcome(self, account_id: str, profitable: bool):
        """Update trade outcome for an account"""
        if account_id not in self.trade_outcomes:
            self.trade_outcomes[account_id] = []
        
        self.trade_outcomes[account_id].append(profitable)
        
        # Keep only last 100 trades
        if len(self.trade_outcomes[account_id]) > 100:
            self.trade_outcomes[account_id] = self.trade_outcomes[account_id][-100:]
    
    def calculate_consecutive_losses(self, account_id: str) -> int:
        """Calculate consecutive losses for an account"""
        if account_id not in self.trade_outcomes:
            return 0
        
        consecutive = 0
        for outcome in reversed(self.trade_outcomes[account_id]):
            if not outcome:  # Loss
                consecutive += 1
            else:
                break
        
        return consecutive
    
    def calculate_win_rate(self, account_id: str) -> float:
        """Calculate win rate for an account"""
        if account_id not in self.trade_outcomes or not self.trade_outcomes[account_id]:
            return 0.0
        
        wins = sum(1 for outcome in self.trade_outcomes[account_id] if outcome)
        total = len(self.trade_outcomes[account_id])
        
        return wins / total if total > 0 else 0.0
    
    def calculate_volatility(self, account_id: str) -> float:
        """Calculate P&L volatility for an account"""
        if account_id not in self.daily_pnl or len(self.daily_pnl[account_id]) < 2:
            return 0.0
        
        return statistics.stdev(self.daily_pnl[account_id])


class SafetyMonitor:
    """Monitors trading system safety and performance"""
    
    def __init__(self, event_bus: Optional[EventBus] = None, oanda_client: Optional[OandaClient] = None):
        self.settings = get_settings()
        self.event_bus = event_bus
        self.oanda_client = oanda_client
        self.circuit_breaker = CircuitBreakerManager(event_bus)
        self.performance_tracker = PerformanceTracker()
        
        self.alerts: Dict[str, SafetyAlert] = {}
        self.risk_metrics: Dict[str, RiskMetrics] = {}
        self.monitoring_active = False
        self._monitor_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start safety monitoring"""
        logger.info("Starting Safety Monitor")
        self.monitoring_active = True
        
        # Start monitoring loop
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("Safety Monitor started")
    
    async def stop(self):
        """Stop safety monitoring"""
        logger.info("Stopping Safety Monitor")
        self.monitoring_active = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Safety Monitor stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                await self._perform_safety_checks()
                await asyncio.sleep(self.settings.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Safety monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def _perform_safety_checks(self):
        """Perform comprehensive safety checks"""
        if not self.oanda_client:
            return
        
        try:
            # Get all account information
            accounts = await self.oanda_client.get_all_accounts_info()
            
            for account_id, account_info in accounts.items():
                # Calculate risk metrics
                risk_metrics = await self._calculate_risk_metrics(account_id, account_info)
                self.risk_metrics[account_id] = risk_metrics
                
                # Perform safety checks
                await self._check_account_safety(risk_metrics)
                
            # Check system-wide safety
            await self._check_system_safety()
            
        except Exception as e:
            logger.error(f"Safety check failed: {e}")
            await self._create_alert(
                AlertLevel.CRITICAL,
                "Safety Check Failed",
                f"Safety monitoring failed: {e}",
                None
            )
    
    async def _calculate_risk_metrics(self, account_id: str, account_info) -> RiskMetrics:
        """Calculate comprehensive risk metrics for an account"""
        try:
            # Get positions and trades
            positions = await self.oanda_client.get_positions(account_id)
            trades = await self.oanda_client.get_trades(account_id)
            
            # Calculate total exposure
            total_exposure = sum(abs(pos.units * pos.average_price) for pos in positions)
            
            # Find largest position
            largest_position = max(
                (abs(pos.units * pos.average_price) for pos in positions),
                default=0.0
            )
            
            # Calculate starting balance (simplified - would need historical data)
            starting_balance = account_info.balance  # TODO: Get actual starting balance
            
            # Calculate drawdown
            peak_balance = starting_balance  # TODO: Track actual peak
            drawdown_percentage = max(0, (peak_balance - account_info.balance) / peak_balance * 100)
            
            # Get performance metrics
            consecutive_losses = self.performance_tracker.calculate_consecutive_losses(account_id)
            volatility_score = self.performance_tracker.calculate_volatility(account_id)
            
            # Calculate correlation (simplified)
            correlation_score = 0.0  # TODO: Implement proper correlation calculation
            
            # Count trades today
            today = datetime.utcnow().date()
            trades_today = len([t for t in trades if t.open_time.date() == today])
            
            # Calculate overall risk score
            risk_score = self._calculate_risk_score(
                drawdown_percentage, consecutive_losses, volatility_score, 
                total_exposure / account_info.balance if account_info.balance > 0 else 0
            )
            
            return RiskMetrics(
                account_id=account_id,
                current_balance=account_info.balance,
                starting_balance=starting_balance,
                daily_pnl=0.0,  # TODO: Calculate actual daily P&L
                unrealized_pnl=account_info.unrealized_pnl,
                total_exposure=total_exposure,
                position_count=len(positions),
                largest_position=largest_position,
                correlation_score=correlation_score,
                volatility_score=volatility_score,
                drawdown_percentage=drawdown_percentage,
                consecutive_losses=consecutive_losses,
                trades_today=trades_today,
                last_trade_time=trades[-1].open_time if trades else None,
                risk_score=risk_score
            )
            
        except Exception as e:
            logger.error(f"Risk calculation failed for {account_id}: {e}")
            raise
    
    def _calculate_risk_score(self, drawdown: float, consecutive_losses: int, 
                            volatility: float, exposure_ratio: float) -> float:
        """Calculate overall risk score (0-100)"""
        # Simple risk scoring algorithm
        score = 0.0
        
        # Drawdown component (0-30 points)
        score += min(30, drawdown * 3)
        
        # Consecutive losses component (0-25 points)
        score += min(25, consecutive_losses * 5)
        
        # Volatility component (0-25 points)
        score += min(25, volatility * 25)
        
        # Exposure component (0-20 points)
        score += min(20, exposure_ratio * 20)
        
        return min(100, score)
    
    async def _check_account_safety(self, metrics: RiskMetrics):
        """Check safety for a specific account"""
        account_id = metrics.account_id
        
        # Check drawdown
        if metrics.drawdown_percentage > 15:
            await self._create_alert(
                AlertLevel.CRITICAL,
                "High Drawdown",
                f"Account {account_id} drawdown: {metrics.drawdown_percentage:.1f}%",
                account_id
            )
        elif metrics.drawdown_percentage > 10:
            await self._create_alert(
                AlertLevel.WARNING,
                "Elevated Drawdown",
                f"Account {account_id} drawdown: {metrics.drawdown_percentage:.1f}%",
                account_id
            )
        
        # Check consecutive losses
        if metrics.consecutive_losses >= 5:
            await self._create_alert(
                AlertLevel.CRITICAL,
                "Consecutive Losses",
                f"Account {account_id} has {metrics.consecutive_losses} consecutive losses",
                account_id
            )
        elif metrics.consecutive_losses >= 3:
            await self._create_alert(
                AlertLevel.WARNING,
                "Multiple Losses",
                f"Account {account_id} has {metrics.consecutive_losses} consecutive losses",
                account_id
            )
        
        # Check risk score
        if metrics.risk_score > 80:
            await self._create_alert(
                AlertLevel.EMERGENCY,
                "Critical Risk Level",
                f"Account {account_id} risk score: {metrics.risk_score:.1f}/100",
                account_id
            )
        elif metrics.risk_score > 60:
            await self._create_alert(
                AlertLevel.CRITICAL,
                "High Risk Level",
                f"Account {account_id} risk score: {metrics.risk_score:.1f}/100",
                account_id
            )
        
        # Check position concentration
        if metrics.position_count > 0:
            largest_percentage = (metrics.largest_position / metrics.current_balance) * 100
            if largest_percentage > 20:
                await self._create_alert(
                    AlertLevel.WARNING,
                    "Position Concentration",
                    f"Account {account_id} largest position: {largest_percentage:.1f}% of balance",
                    account_id
                )
        
        # Check daily trade limit
        if metrics.trades_today > self.settings.max_trades_per_hour:
            await self._create_alert(
                AlertLevel.WARNING,
                "High Trading Frequency",
                f"Account {account_id} has {metrics.trades_today} trades today",
                account_id
            )
    
    async def _check_system_safety(self):
        """Check system-wide safety"""
        if not self.risk_metrics:
            return
        
        # Calculate system-wide metrics
        total_accounts = len(self.risk_metrics)
        high_risk_accounts = sum(1 for m in self.risk_metrics.values() if m.risk_score > 60)
        avg_risk_score = sum(m.risk_score for m in self.risk_metrics.values()) / total_accounts
        
        # Check for system-wide issues
        if high_risk_accounts > total_accounts * 0.5:
            await self._create_alert(
                AlertLevel.EMERGENCY,
                "System-wide Risk",
                f"{high_risk_accounts}/{total_accounts} accounts at high risk",
                None
            )
        
        if avg_risk_score > 70:
            await self._create_alert(
                AlertLevel.CRITICAL,
                "Elevated System Risk",
                f"Average risk score: {avg_risk_score:.1f}/100",
                None
            )
        
        # Check correlation (if accounts are too correlated)
        correlation_threshold = 0.8
        high_correlation_pairs = 0
        account_ids = list(self.risk_metrics.keys())
        
        # TODO: Implement proper correlation calculation
        # This is a placeholder
        
        if high_correlation_pairs > 0:
            await self._create_alert(
                AlertLevel.WARNING,
                "High Account Correlation",
                f"Found {high_correlation_pairs} highly correlated account pairs",
                None
            )
    
    async def _create_alert(self, level: AlertLevel, title: str, message: str, account_id: Optional[str]):
        """Create and process a safety alert"""
        alert_id = f"{level}_{account_id or 'system'}_{datetime.utcnow().timestamp()}"
        
        alert = SafetyAlert(
            alert_id=alert_id,
            level=level,
            title=title,
            message=message,
            account_id=account_id,
            timestamp=datetime.utcnow()
        )
        
        self.alerts[alert_id] = alert
        
        # Log the alert
        log_level = {
            AlertLevel.INFO: logging.info,
            AlertLevel.WARNING: logging.warning,
            AlertLevel.CRITICAL: logging.error,
            AlertLevel.EMERGENCY: logging.critical
        }[level]
        
        log_level(f"SAFETY ALERT [{level}]: {title} - {message}")
        
        # Handle emergency alerts
        if level == AlertLevel.EMERGENCY:
            await self._handle_emergency_alert(alert)
        
        # Emit event
        if self.event_bus:
            await self.event_bus.emit_performance_alert(
                title, float(level == AlertLevel.EMERGENCY), 1.0, account_id or "system"
            )
    
    async def _handle_emergency_alert(self, alert: SafetyAlert):
        """Handle emergency safety alerts"""
        logger.critical(f"EMERGENCY ALERT: {alert.title} - {alert.message}")
        
        if alert.account_id:
            # Account-specific emergency
            await self.circuit_breaker.force_open_breaker(
                self.circuit_breaker.BreakerType.ACCOUNT_LOSS,
                f"Emergency: {alert.title}"
            )
        else:
            # System-wide emergency
            await self.circuit_breaker.force_open_breaker(
                self.circuit_breaker.BreakerType.SYSTEM_HEALTH,
                f"Emergency: {alert.title}"
            )
    
    async def check_trade_safety(self, account_id: str, signal) -> bool:
        """Check if a trade is safe to execute"""
        try:
            # Use circuit breaker for comprehensive checks
            return await self.circuit_breaker.check_all_breakers(account_id, "trade")
        except Exception as e:
            logger.error(f"Trade safety check failed: {e}")
            return False
    
    def get_account_risk_metrics(self, account_id: str) -> Optional[RiskMetrics]:
        """Get risk metrics for a specific account"""
        return self.risk_metrics.get(account_id)
    
    def get_all_risk_metrics(self) -> Dict[str, RiskMetrics]:
        """Get risk metrics for all accounts"""
        return self.risk_metrics.copy()
    
    def get_active_alerts(self, level: Optional[AlertLevel] = None) -> List[SafetyAlert]:
        """Get active safety alerts"""
        alerts = [alert for alert in self.alerts.values() if not alert.resolved]
        
        if level:
            alerts = [alert for alert in alerts if alert.level == level]
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)
    
    async def resolve_alert(self, alert_id: str):
        """Resolve a safety alert"""
        if alert_id in self.alerts:
            self.alerts[alert_id].resolved = True
            self.alerts[alert_id].resolved_at = datetime.utcnow()
            logger.info(f"Resolved safety alert: {alert_id}")
    
    def get_system_health_summary(self) -> Dict[str, any]:
        """Get overall system health summary"""
        if not self.risk_metrics:
            return {"status": "unknown", "message": "No data available"}
        
        total_accounts = len(self.risk_metrics)
        healthy_accounts = sum(1 for m in self.risk_metrics.values() if m.risk_score < 40)
        warning_accounts = sum(1 for m in self.risk_metrics.values() if 40 <= m.risk_score < 70)
        critical_accounts = sum(1 for m in self.risk_metrics.values() if m.risk_score >= 70)
        
        avg_risk_score = sum(m.risk_score for m in self.risk_metrics.values()) / total_accounts
        
        active_alerts = len(self.get_active_alerts())
        critical_alerts = len(self.get_active_alerts(AlertLevel.CRITICAL))
        emergency_alerts = len(self.get_active_alerts(AlertLevel.EMERGENCY))
        
        # Determine overall status
        if emergency_alerts > 0 or critical_accounts > total_accounts * 0.5:
            status = "critical"
        elif critical_alerts > 0 or warning_accounts > total_accounts * 0.3:
            status = "warning"
        elif avg_risk_score < 30:
            status = "healthy"
        else:
            status = "caution"
        
        return {
            "status": status,
            "avg_risk_score": round(avg_risk_score, 1),
            "accounts": {
                "total": total_accounts,
                "healthy": healthy_accounts,
                "warning": warning_accounts,
                "critical": critical_accounts
            },
            "alerts": {
                "total": active_alerts,
                "critical": critical_alerts,
                "emergency": emergency_alerts
            },
            "last_update": datetime.utcnow().isoformat()
        }
    
    async def pre_trading_checks(self) -> bool:
        """Perform pre-trading safety checks before enabling trading"""
        try:
            logger.info("Performing pre-trading safety checks...")
            
            # Check if there are any emergency alerts
            emergency_alerts = self.get_active_alerts(AlertLevel.EMERGENCY)
            if emergency_alerts:
                logger.error(f"Emergency alerts prevent trading: {len(emergency_alerts)} active")
                raise SafetyException("Emergency alerts active - trading blocked")
            
            # Check critical alerts
            critical_alerts = self.get_active_alerts(AlertLevel.CRITICAL)
            if len(critical_alerts) > 3:  # Allow some critical alerts but not too many
                logger.error(f"Too many critical alerts: {len(critical_alerts)} active")
                raise SafetyException("Excessive critical alerts - trading blocked")
            
            # Check OANDA connection if client is available
            if self.oanda_client:
                try:
                    await self.oanda_client.verify_connection()
                    logger.info("OANDA connection verified")
                except Exception as e:
                    logger.error(f"OANDA connection check failed: {e}")
                    raise SafetyException(f"OANDA connection failed: {e}")
            
            # Check if we have any risk metrics (accounts configured)
            if not self.risk_metrics:
                logger.warning("No risk metrics available - first trading session")
            else:
                # Check if any accounts are in critical state
                critical_accounts = [m for m in self.risk_metrics.values() if m.risk_score >= 70]
                if len(critical_accounts) > len(self.risk_metrics) * 0.5:
                    logger.error(f"Too many critical accounts: {len(critical_accounts)}/{len(self.risk_metrics)}")
                    raise SafetyException("Majority of accounts in critical state")
            
            logger.info("Pre-trading safety checks passed")
            return True
            
        except SafetyException:
            raise
        except Exception as e:
            logger.error(f"Pre-trading checks failed with unexpected error: {e}")
            raise SafetyException(f"Pre-trading checks failed: {e}")
    
    async def validate_signal(self, signal) -> bool:
        """Validate a trading signal for safety compliance"""
        try:
            # Basic signal validation
            if not signal.instrument or not signal.direction:
                logger.warning("Invalid signal: missing required fields")
                return False
            
            # Check confidence level
            if signal.confidence < 0.3:  # Minimum confidence threshold
                logger.warning(f"Signal confidence too low: {signal.confidence}")
                return False
            
            # Check if signal has reasonable risk/reward
            if hasattr(signal, 'stop_loss') and hasattr(signal, 'take_profit') and signal.entry_price:
                if signal.stop_loss and signal.take_profit:
                    if signal.direction == "long":
                        risk = abs(signal.entry_price - signal.stop_loss)
                        reward = abs(signal.take_profit - signal.entry_price)
                    else:
                        risk = abs(signal.stop_loss - signal.entry_price)
                        reward = abs(signal.entry_price - signal.take_profit)
                    
                    if risk > 0 and reward / risk < 1.0:  # Min 1:1 risk/reward
                        logger.warning(f"Poor risk/reward ratio: {reward/risk:.2f}")
                        return False
            
            logger.debug(f"Signal validation passed for {signal.id}")
            return True
            
        except Exception as e:
            logger.error(f"Signal validation failed: {e}")
            return False