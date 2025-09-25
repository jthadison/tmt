"""
Automatic Rollback Monitoring Service
Continuously monitors performance metrics and triggers automatic rollbacks when conditions are met
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import json

from .emergency_rollback import get_emergency_rollback_system, RollbackTrigger

logger = logging.getLogger(__name__)

class RollbackMonitorService:
    """
    Service that continuously monitors system performance and automatically triggers
    emergency rollbacks when predefined conditions are met
    """

    def __init__(self, orchestrator=None, check_interval: int = 300):  # 5 minutes default
        self.orchestrator = orchestrator
        self.check_interval = check_interval  # seconds
        self.emergency_rollback = get_emergency_rollback_system(orchestrator)
        self.monitoring_active = False
        self.last_check_timestamp = None
        self.consecutive_trigger_counts = {}

    async def start_monitoring(self):
        """Start the automatic monitoring service"""
        if self.monitoring_active:
            logger.warning("Rollback monitoring already active")
            return

        self.monitoring_active = True
        logger.info(f"🎯 Starting automatic rollback monitoring (check interval: {self.check_interval}s)")

        while self.monitoring_active:
            try:
                await self._perform_rollback_check()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in rollback monitoring cycle: {e}")
                await asyncio.sleep(60)  # Shorter sleep on error

    async def stop_monitoring(self):
        """Stop the automatic monitoring service"""
        self.monitoring_active = False
        logger.info("🛑 Automatic rollback monitoring stopped")

    async def _perform_rollback_check(self):
        """Perform a single rollback condition check"""
        self.last_check_timestamp = datetime.now(timezone.utc)

        try:
            # Gather current performance metrics
            performance_data = await self._gather_performance_metrics()

            # Check for trigger conditions
            trigger = await self.emergency_rollback.check_automatic_triggers(performance_data)

            if trigger:
                # Track consecutive triggers for stability
                self.consecutive_trigger_counts[trigger] = self.consecutive_trigger_counts.get(trigger, 0) + 1

                # Require multiple consecutive detections for stability-sensitive triggers
                required_consecutive = self._get_required_consecutive_count(trigger)
                current_consecutive = self.consecutive_trigger_counts[trigger]

                if current_consecutive >= required_consecutive:
                    logger.warning(f"🚨 AUTOMATIC ROLLBACK TRIGGERED: {trigger.value}")
                    logger.warning(f"Consecutive detections: {current_consecutive}/{required_consecutive}")

                    await self._execute_automatic_rollback(trigger, performance_data)

                    # Reset consecutive counts after rollback
                    self.consecutive_trigger_counts.clear()
                else:
                    logger.warning(f"⚠️ Rollback condition detected but insufficient consecutive count: {trigger.value}")
                    logger.warning(f"Count: {current_consecutive}/{required_consecutive}")
            else:
                # Reset consecutive counts when no triggers detected
                self.consecutive_trigger_counts.clear()

        except Exception as e:
            logger.error(f"Error performing rollback check: {e}")

    async def _gather_performance_metrics(self) -> Dict[str, Any]:
        """Gather current system performance metrics for rollback evaluation"""

        performance_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data_source": "real_time_monitoring"
        }

        try:
            # Get real-time metrics from orchestrator if available
            if self.orchestrator:
                try:
                    system_metrics = await self.orchestrator.get_system_metrics()

                    # Extract relevant performance data
                    performance_data.update({
                        "consecutive_losses": getattr(system_metrics, 'consecutive_losses', 0),
                        "max_drawdown_percent": getattr(system_metrics, 'max_drawdown_percent', 0.0),
                        "daily_pnl_percent": getattr(system_metrics, 'daily_pnl_percent', 0.0),
                        "trading_enabled": getattr(system_metrics, 'trading_enabled', True),
                    })

                except Exception as e:
                    logger.warning(f"Could not get orchestrator metrics: {e}")

            # Add static performance data from forward testing analysis
            # (In production, this would be dynamically calculated)
            performance_data.update({
                "walk_forward_stability": 34.4,  # From forward testing document
                "overfitting_score": 0.634,      # From forward testing document
                "out_of_sample_validation": 17.4, # From forward testing document
            })

            # Calculate additional metrics
            performance_data.update({
                "confidence_interval_breach_days": await self._calculate_confidence_interval_breaches(),
                "performance_decline_percent": await self._calculate_performance_decline(),
                "system_stability_score": await self._calculate_system_stability()
            })

        except Exception as e:
            logger.error(f"Error gathering performance metrics: {e}")
            # Use fallback metrics to ensure monitoring continues
            performance_data.update({
                "consecutive_losses": 0,
                "max_drawdown_percent": 0.0,
                "walk_forward_stability": 50.0,
                "overfitting_score": 0.3,
                "error": str(e)
            })

        return performance_data

    async def _calculate_confidence_interval_breaches(self) -> int:
        """Calculate number of days performance has been outside confidence intervals"""
        # Placeholder - in production, this would analyze historical performance
        # against Monte Carlo projections
        return 1

    async def _calculate_performance_decline(self) -> float:
        """Calculate percentage decline in performance vs expectations"""
        # Placeholder - in production, this would compare actual vs projected performance
        return 5.5

    async def _calculate_system_stability(self) -> float:
        """Calculate overall system stability score"""
        # Placeholder - in production, this would be a composite stability metric
        return 45.0

    def _get_required_consecutive_count(self, trigger: RollbackTrigger) -> int:
        """Get required consecutive detections for each trigger type"""
        requirements = {
            RollbackTrigger.WALK_FORWARD_FAILURE: 2,      # High severity - require 2 consecutive
            RollbackTrigger.OVERFITTING_DETECTED: 3,      # High impact - require 3 consecutive
            RollbackTrigger.CONSECUTIVE_LOSSES: 1,        # Direct metric - immediate trigger
            RollbackTrigger.DRAWDOWN_BREACH: 2,           # Severe - require 2 consecutive
            RollbackTrigger.CONFIDENCE_INTERVAL_BREACH: 3, # Statistical - require 3 consecutive
            RollbackTrigger.PERFORMANCE_DEGRADATION: 2,   # Gradual decline - require 2 consecutive
            RollbackTrigger.SYSTEM_STABILITY_FAILURE: 2   # System health - require 2 consecutive
        }
        return requirements.get(trigger, 2)  # Default to 2 consecutive

    async def _execute_automatic_rollback(self, trigger: RollbackTrigger, performance_data: Dict[str, Any]):
        """Execute automatic rollback with detailed logging"""

        rollback_reason = self._generate_rollback_reason(trigger, performance_data)

        try:
            logger.critical(f"🚨 EXECUTING AUTOMATIC EMERGENCY ROLLBACK: {trigger.value}")
            logger.critical(f"Reason: {rollback_reason}")
            logger.critical(f"Performance data: {json.dumps(performance_data, indent=2)}")

            # Execute the rollback
            rollback_event = await self.emergency_rollback.execute_emergency_rollback(
                trigger_type=trigger,
                reason=f"AUTOMATIC: {rollback_reason}",
                notify_contacts=True  # Always notify for automatic rollbacks
            )

            logger.critical(f"✅ AUTOMATIC ROLLBACK COMPLETED: Event ID {rollback_event.event_id}")

            # Stop monitoring after rollback (require manual restart)
            await self.stop_monitoring()

        except Exception as e:
            logger.critical(f"❌ AUTOMATIC ROLLBACK FAILED: {e}")
            # Continue monitoring even if rollback fails
            raise

    def _generate_rollback_reason(self, trigger: RollbackTrigger, performance_data: Dict[str, Any]) -> str:
        """Generate detailed reason for automatic rollback"""

        if trigger == RollbackTrigger.WALK_FORWARD_FAILURE:
            stability = performance_data.get("walk_forward_stability", 0)
            return f"Walk-forward stability critical: {stability}/100 (threshold: 40.0)"

        elif trigger == RollbackTrigger.OVERFITTING_DETECTED:
            overfitting = performance_data.get("overfitting_score", 0)
            return f"Overfitting score excessive: {overfitting} (threshold: 0.5)"

        elif trigger == RollbackTrigger.CONSECUTIVE_LOSSES:
            losses = performance_data.get("consecutive_losses", 0)
            return f"Consecutive losses exceeded: {losses} trades (threshold: 5)"

        elif trigger == RollbackTrigger.DRAWDOWN_BREACH:
            drawdown = performance_data.get("max_drawdown_percent", 0)
            return f"Maximum drawdown breached: {drawdown}% (threshold: 5.0%)"

        elif trigger == RollbackTrigger.CONFIDENCE_INTERVAL_BREACH:
            days = performance_data.get("confidence_interval_breach_days", 0)
            return f"Confidence interval breach: {days} consecutive days (threshold: 3)"

        elif trigger == RollbackTrigger.PERFORMANCE_DEGRADATION:
            decline = performance_data.get("performance_decline_percent", 0)
            return f"Performance degradation: {decline}% decline (threshold: 10.0%)"

        else:
            return f"Automatic trigger condition met: {trigger.value}"

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring service status"""
        return {
            "monitoring_active": self.monitoring_active,
            "check_interval_seconds": self.check_interval,
            "last_check": self.last_check_timestamp.isoformat() if self.last_check_timestamp else None,
            "consecutive_trigger_counts": dict(self.consecutive_trigger_counts),
            "uptime_seconds": (
                (datetime.now(timezone.utc) - self.last_check_timestamp).total_seconds()
                if self.last_check_timestamp else 0
            )
        }


# Global monitoring service instance
rollback_monitor_service: Optional[RollbackMonitorService] = None

def get_rollback_monitor_service(orchestrator=None) -> RollbackMonitorService:
    """Get or create the global rollback monitoring service"""
    global rollback_monitor_service
    if rollback_monitor_service is None:
        rollback_monitor_service = RollbackMonitorService(orchestrator)
    return rollback_monitor_service