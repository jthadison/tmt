"""
Stability Integration Module
Orchestrates all September 2025 degradation fixes and stability improvements
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import pandas as pd

# Import our new stability components
from agents.market_analysis.parameter_robustness import (
    ParameterRegularizer, EnsembleParameterManager, get_emergency_parameters
)
from agents.market_analysis.market_regime_detector import (
    MarketRegimeDetector, MarketRegime, RegimeChangeAlert
)
from validation.enhanced_validation_framework import (
    EnhancedValidator, ValidationResult, ValidationReport
)
from monitoring.realtime_performance_monitor import (
    RealTimePerformanceMonitor, AlertLevel, PerformanceAlert
)
from agents.market_analysis.config import (
    ParameterMode, set_parameter_mode, emergency_rollback,
    STABILIZED_V1_PARAMETERS, EMERGENCY_CONSERVATIVE_PARAMETERS
)

logger = logging.getLogger(__name__)

class StabilityStatus(Enum):
    """Overall stability system status"""
    HEALTHY = "healthy"
    MONITORING = "monitoring"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class StabilityManager:
    """Main stability management system"""

    def __init__(self, config: Dict):
        self.config = config
        self.is_active = False

        # Initialize components
        self.parameter_regularizer = ParameterRegularizer(config)
        self.ensemble_manager = EnsembleParameterManager()
        self.regime_detector = MarketRegimeDetector(config.get('instruments', ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CHF']))
        self.validator = EnhancedValidator(config)
        self.performance_monitor = RealTimePerformanceMonitor(config)

        # System state
        self.current_status = StabilityStatus.HEALTHY
        self.current_parameter_mode = ParameterMode.SESSION_TARGETED
        self.emergency_mode_active = False
        self.last_validation_report: Optional[ValidationReport] = None

        # Auto-response settings
        self.auto_emergency_response = config.get('auto_emergency_response', True)
        self.auto_regime_adaptation = config.get('auto_regime_adaptation', True)
        self.auto_parameter_adjustment = config.get('auto_parameter_adjustment', False)

        # Setup alert callbacks
        self.performance_monitor.add_alert_callback(self._handle_performance_alert)

    async def initialize(self):
        """Initialize the stability management system"""

        logger.info("Initializing stability management system...")

        try:
            # Start performance monitoring
            self.performance_monitor.start_monitoring()

            # Initialize validation baseline
            await self._run_initial_validation()

            # Set initial status
            self.current_status = StabilityStatus.HEALTHY
            self.is_active = True

            logger.info("Stability management system initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize stability system: {str(e)}")
            raise

    async def shutdown(self):
        """Shutdown the stability management system"""

        logger.info("Shutting down stability management system...")

        # Stop performance monitoring
        self.performance_monitor.stop_monitoring()

        # Save final state
        await self._save_stability_state()

        self.is_active = False
        logger.info("Stability management system shutdown complete")

    async def process_market_data(self, instrument: str, price_data: pd.DataFrame):
        """Process new market data through stability pipeline"""

        if not self.is_active:
            return

        try:
            # Update regime detection
            await self.regime_detector.update_regime_analysis(instrument, price_data)

            # Check for regime changes
            current_regime = self.regime_detector.current_regimes.get(instrument)
            if current_regime:
                await self._handle_regime_update(instrument, current_regime)

            # Check if trading should be halted
            should_halt, reason = self.regime_detector.should_halt_trading(instrument)
            if should_halt:
                await self._handle_trading_halt(instrument, reason)

        except Exception as e:
            logger.error(f"Error processing market data for {instrument}: {str(e)}")

    async def record_trade_result(self, trade_data: Dict):
        """Record trade result and update stability metrics"""

        if not self.is_active:
            return

        try:
            # Record in performance monitor
            self.performance_monitor.record_trade(trade_data)

            # Update parameter regularizer
            regime = trade_data.get('regime', 'unknown')
            pnl = trade_data.get('pnl', 0)

            # Update ensemble performance if applicable
            parameter_set = trade_data.get('parameter_set', 'default')
            self.ensemble_manager.update_ensemble_performance(parameter_set, pnl)

            # Update regime-specific performance
            instrument = trade_data.get('instrument', 'Unknown')
            self.regime_detector.update_regime_performance(instrument, pnl)

        except Exception as e:
            logger.error(f"Error recording trade result: {str(e)}")

    async def get_current_parameters(self, force_mode: Optional[ParameterMode] = None) -> Dict:
        """Get current trading parameters with stability adjustments"""

        try:
            # Use forced mode if provided, otherwise use current mode
            mode = force_mode or self.current_parameter_mode

            if self.emergency_mode_active or mode == ParameterMode.EMERGENCY_CONSERVATIVE:
                return EMERGENCY_CONSERVATIVE_PARAMETERS.copy()

            elif mode == ParameterMode.STABILIZED_V1:
                # Get stabilized parameters for current session
                from agents.market_analysis.config import get_current_session
                session = get_current_session()
                session_key = session.value.lower()

                if session_key in STABILIZED_V1_PARAMETERS:
                    params = STABILIZED_V1_PARAMETERS[session_key].copy()

                    # Apply any runtime adjustments
                    if self.auto_parameter_adjustment:
                        params = await self._apply_stability_adjustments(params, session_key)

                    return params

            # Fallback to standard parameter retrieval
            from agents.market_analysis.config import get_current_parameters
            return get_current_parameters()

        except Exception as e:
            logger.error(f"Error getting current parameters: {str(e)}")
            # Return emergency parameters as failsafe
            return EMERGENCY_CONSERVATIVE_PARAMETERS.copy()

    async def _apply_stability_adjustments(self, params: Dict, session: str) -> Dict:
        """Apply runtime stability adjustments to parameters"""

        try:
            # Get current regime for adjustment
            regime_summary = self.regime_detector.get_current_regime_summary()

            # Apply regime-based adjustments
            for instrument, regime_data in regime_summary.items():
                regime = regime_data.get('regime', 'unknown')
                confidence = regime_data.get('confidence', 0)

                # Adjust parameters based on regime confidence
                if confidence < 0.5:  # Low regime confidence
                    params['confidence_threshold'] = min(95.0, params.get('confidence_threshold', 70.0) + 5.0)
                elif confidence > 0.8:  # High regime confidence
                    params['confidence_threshold'] = max(50.0, params.get('confidence_threshold', 70.0) - 2.0)

            # Apply volatility adjustments
            if 'volatility_adjustment' in params:
                vol_adj = params['volatility_adjustment']
                params['position_size_multiplier'] = 1.0 - vol_adj

            return params

        except Exception as e:
            logger.error(f"Error applying stability adjustments: {str(e)}")
            return params

    async def _handle_performance_alert(self, alert: PerformanceAlert):
        """Handle performance monitoring alerts"""

        logger.warning(f"Stability system received alert: {alert.level.value} - {alert.message}")

        if alert.level == AlertLevel.EMERGENCY and self.auto_emergency_response:
            await self._trigger_emergency_response(alert)

        elif alert.level == AlertLevel.CRITICAL:
            await self._handle_critical_alert(alert)

        elif alert.level == AlertLevel.WARNING:
            await self._handle_warning_alert(alert)

        # Update system status
        await self._update_system_status(alert.level)

    async def _trigger_emergency_response(self, alert: PerformanceAlert):
        """Trigger emergency response procedures"""

        logger.critical(f"EMERGENCY RESPONSE TRIGGERED: {alert.message}")

        try:
            # Switch to emergency conservative mode
            emergency_rollback(f"Emergency response to: {alert.message}")
            self.current_parameter_mode = ParameterMode.EMERGENCY_CONSERVATIVE
            self.emergency_mode_active = True

            # Update system status
            self.current_status = StabilityStatus.EMERGENCY

            # Log emergency action
            logger.critical("System switched to EMERGENCY CONSERVATIVE mode")

            # Notify external systems (trading halt, notifications, etc.)
            await self._notify_emergency_systems(alert)

        except Exception as e:
            logger.error(f"Error in emergency response: {str(e)}")

    async def _handle_critical_alert(self, alert: PerformanceAlert):
        """Handle critical alerts"""

        logger.error(f"CRITICAL ALERT: {alert.message}")

        try:
            # Switch to stabilized parameters if not already in emergency
            if not self.emergency_mode_active:
                self.current_parameter_mode = ParameterMode.STABILIZED_V1
                set_parameter_mode(ParameterMode.STABILIZED_V1, f"Critical alert response: {alert.message}")

            # Update status
            self.current_status = StabilityStatus.CRITICAL

        except Exception as e:
            logger.error(f"Error handling critical alert: {str(e)}")

    async def _handle_warning_alert(self, alert: PerformanceAlert):
        """Handle warning alerts"""

        logger.warning(f"WARNING ALERT: {alert.message}")

        # Update status to monitoring/warning
        if self.current_status == StabilityStatus.HEALTHY:
            self.current_status = StabilityStatus.WARNING

    async def _handle_regime_update(self, instrument: str, regime: MarketRegime):
        """Handle regime detection updates"""

        if not self.auto_regime_adaptation:
            return

        try:
            # Check regime change alerts
            alerts = list(self.regime_detector.regime_change_alerts)
            recent_alerts = [
                alert for alert in alerts
                if alert.timestamp > datetime.utcnow() - timedelta(hours=1)
            ]

            if recent_alerts:
                latest_alert = recent_alerts[-1]
                if latest_alert.confidence > 0.7:
                    logger.info(f"High confidence regime change detected: {latest_alert.recommended_action}")

                    # Apply recommended actions
                    if latest_alert.recommended_action == "SWITCH_TO_CONSERVATIVE_PARAMETERS":
                        if self.current_parameter_mode != ParameterMode.EMERGENCY_CONSERVATIVE:
                            self.current_parameter_mode = ParameterMode.STABILIZED_V1

        except Exception as e:
            logger.error(f"Error handling regime update: {str(e)}")

    async def _handle_trading_halt(self, instrument: str, reason: str):
        """Handle trading halt recommendations"""

        logger.critical(f"TRADING HALT RECOMMENDED for {instrument}: {reason}")

        # This would integrate with actual trading system
        # For now, just log and update status
        if self.current_status not in [StabilityStatus.EMERGENCY, StabilityStatus.CRITICAL]:
            self.current_status = StabilityStatus.CRITICAL

    async def _update_system_status(self, alert_level: AlertLevel):
        """Update overall system status based on alerts"""

        if alert_level == AlertLevel.EMERGENCY:
            self.current_status = StabilityStatus.EMERGENCY
        elif alert_level == AlertLevel.CRITICAL and self.current_status != StabilityStatus.EMERGENCY:
            self.current_status = StabilityStatus.CRITICAL
        elif alert_level == AlertLevel.WARNING and self.current_status == StabilityStatus.HEALTHY:
            self.current_status = StabilityStatus.WARNING

    async def _notify_emergency_systems(self, alert: PerformanceAlert):
        """Notify external systems of emergency"""

        # This would integrate with actual notification systems
        logger.critical(f"EMERGENCY NOTIFICATION: {alert.message}")
        logger.critical(f"Recommended Action: {alert.recommended_action}")

    async def _run_initial_validation(self):
        """Run initial validation to establish baseline"""

        try:
            # Create mock data for initial validation
            # In production, this would use recent trading data
            mock_data = pd.DataFrame({
                'pnl': [100, -50, 200, -30, 150] * 20,  # Sample trade data
                'timestamp': pd.date_range('2025-09-01', periods=100, freq='H')
            })

            mock_parameters = {
                'confidence_threshold': 70.0,
                'min_risk_reward': 2.8
            }

            # Run validation
            self.last_validation_report = await self.validator.comprehensive_validation(
                mock_data, mock_parameters
            )

            logger.info(f"Initial validation complete: {self.last_validation_report.overall_result.value}")

        except Exception as e:
            logger.error(f"Initial validation failed: {str(e)}")

    async def _save_stability_state(self):
        """Save current stability state"""

        try:
            state_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'current_status': self.current_status.value,
                'current_parameter_mode': self.current_parameter_mode.value,
                'emergency_mode_active': self.emergency_mode_active,
                'performance_monitor_status': self.performance_monitor.get_current_status(),
                'regime_summary': self.regime_detector.get_current_regime_summary(),
                'recent_alerts': self.performance_monitor.get_recent_alerts(hours=24)
            }

            # Save to file
            import json
            from pathlib import Path

            stability_dir = Path("stability_reports")
            stability_dir.mkdir(exist_ok=True)

            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"stability_state_{timestamp}.json"

            with open(stability_dir / filename, 'w') as f:
                json.dump(state_data, f, indent=2, default=str)

            logger.info(f"Stability state saved to {filename}")

        except Exception as e:
            logger.error(f"Failed to save stability state: {str(e)}")

    async def run_comprehensive_validation(self, recent_trades: pd.DataFrame) -> ValidationReport:
        """Run comprehensive validation on recent performance"""

        if not self.is_active:
            raise RuntimeError("Stability system not active")

        try:
            parameters = await self.get_current_parameters()
            report = await self.validator.comprehensive_validation(recent_trades, parameters)

            self.last_validation_report = report

            # Take action based on validation results
            if report.overall_result == ValidationResult.CRITICAL:
                logger.critical("Validation shows critical issues - triggering emergency response")
                await self._trigger_emergency_response(
                    PerformanceAlert(
                        metric="validation",
                        level=AlertLevel.EMERGENCY,
                        current_value=report.metrics.deployment_readiness,
                        threshold_value=70.0,
                        message="Comprehensive validation failed critically"
                    )
                )
            elif report.overall_result == ValidationResult.FAIL:
                logger.error("Validation failed - switching to stabilized parameters")
                self.current_parameter_mode = ParameterMode.STABILIZED_V1

            return report

        except Exception as e:
            logger.error(f"Comprehensive validation failed: {str(e)}")
            raise

    def get_system_status(self) -> Dict:
        """Get comprehensive system status"""

        return {
            'timestamp': datetime.utcnow().isoformat(),
            'is_active': self.is_active,
            'current_status': self.current_status.value,
            'current_parameter_mode': self.current_parameter_mode.value,
            'emergency_mode_active': self.emergency_mode_active,
            'components': {
                'parameter_regularizer': 'active',
                'ensemble_manager': 'active',
                'regime_detector': 'active',
                'validator': 'active',
                'performance_monitor': 'active' if self.performance_monitor.is_monitoring else 'inactive'
            },
            'performance_monitor': self.performance_monitor.get_current_status(),
            'regime_summary': self.regime_detector.get_current_regime_summary(),
            'last_validation': {
                'timestamp': self.last_validation_report.timestamp.isoformat() if self.last_validation_report else None,
                'result': self.last_validation_report.overall_result.value if self.last_validation_report else None,
                'deployment_readiness': self.last_validation_report.metrics.deployment_readiness if self.last_validation_report else None
            },
            'configuration': {
                'auto_emergency_response': self.auto_emergency_response,
                'auto_regime_adaptation': self.auto_regime_adaptation,
                'auto_parameter_adjustment': self.auto_parameter_adjustment
            }
        }

    async def force_parameter_mode(self, mode: ParameterMode, reason: str = "Manual override") -> Dict:
        """Force change to specific parameter mode"""

        try:
            previous_mode = self.current_parameter_mode
            self.current_parameter_mode = mode

            # Handle emergency mode flag
            if mode == ParameterMode.EMERGENCY_CONSERVATIVE:
                self.emergency_mode_active = True
                self.current_status = StabilityStatus.EMERGENCY
            else:
                self.emergency_mode_active = False
                if self.current_status == StabilityStatus.EMERGENCY:
                    self.current_status = StabilityStatus.MONITORING

            # Use the config function to log the change
            change_info = set_parameter_mode(mode, reason)

            logger.info(f"Parameter mode forced: {previous_mode.value} → {mode.value} ({reason})")

            return {
                **change_info,
                'emergency_mode_active': self.emergency_mode_active,
                'system_status': self.current_status.value
            }

        except Exception as e:
            logger.error(f"Error forcing parameter mode: {str(e)}")
            raise

# Global stability manager instance
_stability_manager: Optional[StabilityManager] = None

async def initialize_stability_system(config: Dict) -> StabilityManager:
    """Initialize global stability system"""

    global _stability_manager

    if _stability_manager is not None:
        logger.warning("Stability system already initialized")
        return _stability_manager

    _stability_manager = StabilityManager(config)
    await _stability_manager.initialize()

    logger.info("Global stability system initialized")
    return _stability_manager

def get_stability_manager() -> Optional[StabilityManager]:
    """Get global stability manager instance"""
    return _stability_manager

async def shutdown_stability_system():
    """Shutdown global stability system"""

    global _stability_manager

    if _stability_manager is not None:
        await _stability_manager.shutdown()
        _stability_manager = None

    logger.info("Global stability system shutdown")