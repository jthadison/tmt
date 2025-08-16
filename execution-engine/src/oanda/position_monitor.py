"""
Position Monitoring and Alerts System for OANDA Integration

Provides real-time monitoring of position performance, risk levels, and automated
alerts based on configurable thresholds. Includes position optimization suggestions.
"""

from typing import Dict, List, Optional, Any, Callable
from decimal import Decimal
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import asyncio
import logging

from .position_manager import OandaPositionManager, PositionInfo, PositionSide

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Alert type enumeration"""
    PROFIT_TARGET = "profit_target"
    LOSS_THRESHOLD = "loss_threshold"
    AGE_WARNING = "age_warning"
    MARGIN_WARNING = "margin_warning"
    RISK_LEVEL = "risk_level"
    PERFORMANCE = "performance"


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertConfig:
    """Configuration for position alerts"""
    alert_type: AlertType
    threshold: Decimal
    enabled: bool = True
    severity: AlertSeverity = AlertSeverity.WARNING
    cooldown_minutes: int = 30  # Minimum time between same alerts
    
    
@dataclass
class PositionAlert:
    """Position alert notification"""
    position_id: str
    instrument: str
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    current_value: Decimal
    threshold: Decimal
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    

@dataclass
class RiskMetrics:
    """Position risk assessment metrics"""
    position_id: str
    risk_score: Decimal  # 0-100 scale
    margin_utilization: Decimal
    correlation_risk: Decimal
    concentration_risk: Decimal
    time_risk: Decimal
    overall_assessment: str
    
    
@dataclass
class PerformanceMetrics:
    """Position performance tracking"""
    position_id: str
    unrealized_pl: Decimal
    unrealized_pl_percentage: Decimal
    duration_hours: float
    max_favorable_excursion: Decimal  # Best unrealized profit seen
    max_adverse_excursion: Decimal  # Worst unrealized loss seen
    efficiency_ratio: Decimal  # Movement in favor vs against
    

class PositionMonitor:
    """
    Comprehensive position monitoring system with alerts and risk assessment.
    Provides real-time monitoring, automated alerts, and optimization suggestions.
    """
    
    def __init__(
        self,
        position_manager: OandaPositionManager,
        alert_callback: Optional[Callable] = None,
        monitoring_interval: int = 30
    ):
        """
        Initialize position monitor
        
        Args:
            position_manager: OANDA position manager instance
            alert_callback: Optional callback function for alerts
            monitoring_interval: Seconds between monitoring checks
        """
        self.position_manager = position_manager
        self.alert_callback = alert_callback
        self.monitoring_interval = monitoring_interval
        
        # Alert configurations
        self.alert_configs: Dict[AlertType, AlertConfig] = {
            AlertType.PROFIT_TARGET: AlertConfig(
                AlertType.PROFIT_TARGET,
                Decimal('100'),  # Default $100 profit
                severity=AlertSeverity.INFO
            ),
            AlertType.LOSS_THRESHOLD: AlertConfig(
                AlertType.LOSS_THRESHOLD,
                Decimal('-50'),  # Default -$50 loss
                severity=AlertSeverity.WARNING
            ),
            AlertType.AGE_WARNING: AlertConfig(
                AlertType.AGE_WARNING,
                Decimal('24'),  # Default 24 hours
                severity=AlertSeverity.INFO
            ),
            AlertType.MARGIN_WARNING: AlertConfig(
                AlertType.MARGIN_WARNING,
                Decimal('80'),  # Default 80% margin utilization
                severity=AlertSeverity.CRITICAL
            ),
            AlertType.RISK_LEVEL: AlertConfig(
                AlertType.RISK_LEVEL,
                Decimal('75'),  # Default risk score 75
                severity=AlertSeverity.WARNING
            )
        }
        
        # Monitoring state
        self.is_monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._last_alerts: Dict[str, Dict[AlertType, datetime]] = {}
        self._performance_history: Dict[str, List[PerformanceMetrics]] = {}
        self._update_lock = asyncio.Lock()
        
    async def start_monitoring(self):
        """Start position monitoring"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self._monitor_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Position monitoring started")
            
    async def stop_monitoring(self):
        """Stop position monitoring"""
        if self._monitor_task:
            self._monitor_task.cancel()
            await asyncio.gather(self._monitor_task, return_exceptions=True)
            self._monitor_task = None
        self.is_monitoring = False
        logger.info("Position monitoring stopped")
        
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        try:
            while self.is_monitoring:
                await asyncio.sleep(self.monitoring_interval)
                
                try:
                    await self._check_all_positions()
                except Exception as e:
                    logger.error(f"Error in position monitoring: {e}")
                    
        except asyncio.CancelledError:
            logger.info("Position monitoring cancelled")
        except Exception as e:
            logger.error(f"Position monitoring error: {e}")
            
    async def _check_all_positions(self):
        """Check all positions for alerts and updates"""
        async with self._update_lock:
            # Refresh position data
            positions = await self.position_manager.get_open_positions()
            
            for position in positions:
                try:
                    # Update performance metrics
                    await self._update_performance_metrics(position)
                    
                    # Check for alerts
                    await self._check_position_alerts(position)
                    
                    # Update risk assessment
                    await self._assess_position_risk(position)
                    
                except Exception as e:
                    logger.error(f"Error checking position {position.position_id}: {e}")
                    
    async def _update_performance_metrics(self, position: PositionInfo):
        """Update performance tracking for a position"""
        # Initialize history if needed
        if position.position_id not in self._performance_history:
            self._performance_history[position.position_id] = []
            
        history = self._performance_history[position.position_id]
        
        # Calculate metrics
        metrics = PerformanceMetrics(
            position_id=position.position_id,
            unrealized_pl=position.unrealized_pl,
            unrealized_pl_percentage=position.pl_percentage,
            duration_hours=position.age_hours,
            max_favorable_excursion=position.unrealized_pl,
            max_adverse_excursion=position.unrealized_pl,
            efficiency_ratio=Decimal('1.0')
        )
        
        # Update max favorable/adverse excursion from history
        if history:
            max_favorable = max(h.max_favorable_excursion for h in history)
            max_adverse = min(h.max_adverse_excursion for h in history)
            
            metrics.max_favorable_excursion = max(metrics.max_favorable_excursion, max_favorable)
            metrics.max_adverse_excursion = min(metrics.max_adverse_excursion, max_adverse)
            
            # Calculate efficiency ratio
            favorable_movement = max(Decimal('0'), metrics.max_favorable_excursion)
            adverse_movement = abs(min(Decimal('0'), metrics.max_adverse_excursion))
            
            if adverse_movement > 0:
                metrics.efficiency_ratio = favorable_movement / adverse_movement
                
        # Add to history (keep last 100 entries)
        history.append(metrics)
        if len(history) > 100:
            history.pop(0)
            
    async def _check_position_alerts(self, position: PositionInfo):
        """Check position for alert conditions"""
        alerts = []
        
        # Initialize last alerts for position if needed
        if position.position_id not in self._last_alerts:
            self._last_alerts[position.position_id] = {}
            
        last_alerts = self._last_alerts[position.position_id]
        
        # Check profit target
        if self._should_check_alert(AlertType.PROFIT_TARGET, last_alerts):
            config = self.alert_configs[AlertType.PROFIT_TARGET]
            if config.enabled and position.unrealized_pl >= config.threshold:
                alert = PositionAlert(
                    position_id=position.position_id,
                    instrument=position.instrument,
                    alert_type=AlertType.PROFIT_TARGET,
                    severity=config.severity,
                    message=f"Position reached profit target: {position.unrealized_pl:.2f}",
                    current_value=position.unrealized_pl,
                    threshold=config.threshold
                )
                alerts.append(alert)
                last_alerts[AlertType.PROFIT_TARGET] = datetime.now(timezone.utc)
                
        # Check loss threshold
        if self._should_check_alert(AlertType.LOSS_THRESHOLD, last_alerts):
            config = self.alert_configs[AlertType.LOSS_THRESHOLD]
            if config.enabled and position.unrealized_pl <= config.threshold:
                alert = PositionAlert(
                    position_id=position.position_id,
                    instrument=position.instrument,
                    alert_type=AlertType.LOSS_THRESHOLD,
                    severity=config.severity,
                    message=f"Position hit loss threshold: {position.unrealized_pl:.2f}",
                    current_value=position.unrealized_pl,
                    threshold=config.threshold
                )
                alerts.append(alert)
                last_alerts[AlertType.LOSS_THRESHOLD] = datetime.now(timezone.utc)
                
        # Check age warning
        if self._should_check_alert(AlertType.AGE_WARNING, last_alerts):
            config = self.alert_configs[AlertType.AGE_WARNING]
            if config.enabled and position.age_hours >= float(config.threshold):
                alert = PositionAlert(
                    position_id=position.position_id,
                    instrument=position.instrument,
                    alert_type=AlertType.AGE_WARNING,
                    severity=config.severity,
                    message=f"Position aged {position.age_hours:.1f} hours",
                    current_value=Decimal(str(position.age_hours)),
                    threshold=config.threshold
                )
                alerts.append(alert)
                last_alerts[AlertType.AGE_WARNING] = datetime.now(timezone.utc)
                
        # Send alerts
        for alert in alerts:
            await self._send_alert(alert)
            
    def _should_check_alert(self, alert_type: AlertType, last_alerts: Dict[AlertType, datetime]) -> bool:
        """Check if enough time has passed since last alert"""
        if alert_type not in last_alerts:
            return True
            
        config = self.alert_configs[alert_type]
        last_alert_time = last_alerts[alert_type]
        cooldown = timedelta(minutes=config.cooldown_minutes)
        
        return datetime.now(timezone.utc) - last_alert_time > cooldown
        
    async def _send_alert(self, alert: PositionAlert):
        """Send alert notification"""
        logger.info(f"ALERT [{alert.severity.value.upper()}] {alert.message}")
        
        if self.alert_callback:
            try:
                await self.alert_callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
                
    async def _assess_position_risk(self, position: PositionInfo) -> RiskMetrics:
        """Assess risk level for a position"""
        # Calculate various risk components
        margin_util = self._calculate_margin_utilization(position)
        correlation_risk = await self._calculate_correlation_risk(position)
        concentration_risk = await self._calculate_concentration_risk(position)
        time_risk = self._calculate_time_risk(position)
        
        # Calculate overall risk score (0-100)
        risk_score = (
            margin_util * Decimal('0.3') +
            correlation_risk * Decimal('0.25') +
            concentration_risk * Decimal('0.25') +
            time_risk * Decimal('0.2')
        )
        
        # Determine assessment
        if risk_score >= 80:
            assessment = "HIGH RISK"
        elif risk_score >= 60:
            assessment = "MODERATE RISK"
        elif risk_score >= 40:
            assessment = "LOW RISK"
        else:
            assessment = "MINIMAL RISK"
            
        return RiskMetrics(
            position_id=position.position_id,
            risk_score=risk_score,
            margin_utilization=margin_util,
            correlation_risk=correlation_risk,
            concentration_risk=concentration_risk,
            time_risk=time_risk,
            overall_assessment=assessment
        )
        
    def _calculate_margin_utilization(self, position: PositionInfo) -> Decimal:
        """Calculate margin utilization risk (0-100)"""
        # This would typically require account-level margin info
        # For now, use a simplified calculation
        if position.margin_used > 0:
            # Assume available margin and calculate utilization
            # This is a placeholder - real implementation would need account data
            return min(Decimal('100'), position.margin_used / 1000 * 100)
        return Decimal('0')
        
    async def _calculate_correlation_risk(self, position: PositionInfo) -> Decimal:
        """Calculate correlation risk with other positions (0-100)"""
        # Get all positions
        all_positions = await self.position_manager.get_open_positions()
        
        # Count similar instruments/currency exposures
        similar_count = 0
        for other_pos in all_positions:
            if other_pos.position_id != position.position_id:
                if self._instruments_correlated(position.instrument, other_pos.instrument):
                    similar_count += 1
                    
        # Higher correlation count = higher risk
        return min(Decimal('100'), Decimal(str(similar_count)) * 20)
        
    def _instruments_correlated(self, instrument1: str, instrument2: str) -> bool:
        """Check if two instruments are correlated"""
        # Extract currencies
        curr1_base, curr1_quote = instrument1.split('_')
        curr2_base, curr2_quote = instrument2.split('_')
        
        # Check for common currencies
        return (curr1_base in [curr2_base, curr2_quote] or 
                curr1_quote in [curr2_base, curr2_quote])
        
    async def _calculate_concentration_risk(self, position: PositionInfo) -> Decimal:
        """Calculate position concentration risk (0-100)"""
        # Get all positions
        all_positions = await self.position_manager.get_open_positions()
        
        if len(all_positions) <= 1:
            return Decimal('100')  # Single position = high concentration
            
        # Calculate this position's proportion of total exposure
        total_exposure = sum(abs(pos.unrealized_pl) + pos.margin_used for pos in all_positions)
        if total_exposure == 0:
            return Decimal('0')
            
        position_exposure = abs(position.unrealized_pl) + position.margin_used
        concentration = (position_exposure / total_exposure) * 100
        
        return min(Decimal('100'), concentration * 2)  # Amplify concentration risk
        
    def _calculate_time_risk(self, position: PositionInfo) -> Decimal:
        """Calculate time-based risk (0-100)"""
        # Risk increases with position age
        age_hours = position.age_hours
        
        if age_hours < 1:
            return Decimal('0')
        elif age_hours < 24:
            return Decimal('20')
        elif age_hours < 168:  # 1 week
            return Decimal('40')
        elif age_hours < 720:  # 1 month
            return Decimal('70')
        else:
            return Decimal('100')
            
    async def configure_alert(
        self,
        alert_type: AlertType,
        threshold: Decimal,
        enabled: bool = True,
        severity: AlertSeverity = AlertSeverity.WARNING,
        cooldown_minutes: int = 30
    ):
        """Configure an alert type"""
        self.alert_configs[alert_type] = AlertConfig(
            alert_type=alert_type,
            threshold=threshold,
            enabled=enabled,
            severity=severity,
            cooldown_minutes=cooldown_minutes
        )
        logger.info(f"Configured {alert_type.value} alert: threshold={threshold}, enabled={enabled}")
        
    async def get_position_performance(self, position_id: str) -> Optional[PerformanceMetrics]:
        """Get latest performance metrics for a position"""
        history = self._performance_history.get(position_id, [])
        return history[-1] if history else None
        
    async def get_position_risk_assessment(self, position_id: str) -> Optional[RiskMetrics]:
        """Get risk assessment for a position"""
        position = self.position_manager.position_cache.get(position_id)
        if position:
            return await self._assess_position_risk(position)
        return None
        
    async def generate_optimization_suggestions(self, position_id: str) -> List[str]:
        """Generate optimization suggestions for a position"""
        position = self.position_manager.position_cache.get(position_id)
        if not position:
            return ["Position not found"]
            
        suggestions = []
        
        # Get performance and risk metrics
        performance = await self.get_position_performance(position_id)
        risk = await self.get_position_risk_assessment(position_id)
        
        # Profit/loss suggestions
        if position.unrealized_pl > 0:
            if not position.take_profit:
                suggestions.append("Consider setting a take profit to lock in gains")
            elif performance and performance.efficiency_ratio > 2:
                suggestions.append("Position showing strong momentum - consider trailing stop")
        elif position.unrealized_pl < 0:
            if not position.stop_loss:
                suggestions.append("URGENT: Set stop loss to limit further losses")
            elif abs(position.unrealized_pl) > position.margin_used * Decimal('0.5'):
                suggestions.append("Consider reducing position size - large unrealized loss")
                
        # Time-based suggestions
        if position.age_hours > 168:  # 1 week
            suggestions.append("Long-held position - review fundamental reasons for holding")
        elif position.age_hours > 24 and abs(position.unrealized_pl) < 10:
            suggestions.append("Stagnant position - consider closing if no clear direction")
            
        # Risk-based suggestions
        if risk and risk.risk_score > 75:
            suggestions.append(f"HIGH RISK position ({risk.overall_assessment}) - consider reducing exposure")
        if risk and risk.concentration_risk > 60:
            suggestions.append("High concentration risk - diversify across more instruments")
            
        return suggestions if suggestions else ["Position appears well-managed"]