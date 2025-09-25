"""
Forward Test-Based Position Sizing Controls

Implements advanced position sizing controls based on forward testing results,
incorporating:
- Dynamic position sizing based on walk-forward stability scores
- Risk adjustment for out-of-sample performance degradation
- Volatility-adjusted sizing for high kurtosis mitigation
- Session-specific position limits
- Gradual capital allocation framework
"""

import asyncio
import logging
from typing import Dict, Optional, List, Tuple, Any
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum
import math

from .config import get_settings
from .models import TradeSignal, TradingSession
from .position_sizing import AdvancedPositionSizing, PositionSizingResult

logger = logging.getLogger(__name__)


class StabilityLevel(Enum):
    """Walk-forward stability levels"""
    CRITICAL = "critical"  # <30/100
    LOW = "low"           # 30-50/100
    MEDIUM = "medium"     # 50-70/100
    HIGH = "high"         # 70-90/100
    EXCELLENT = "excellent"  # >90/100


class ValidationScore(Enum):
    """Out-of-sample validation levels"""
    POOR = "poor"         # <30/100
    WEAK = "weak"         # 30-50/100
    MODERATE = "moderate" # 50-70/100
    GOOD = "good"         # 70-85/100
    STRONG = "strong"     # >85/100


@dataclass
class ForwardTestMetrics:
    """Forward testing metrics for position sizing"""
    walk_forward_stability: float  # Current: 34.4/100
    out_of_sample_validation: float  # Current: 17.4/100
    overfitting_score: float  # Current: 0.634
    kurtosis_exposure: float  # Current: 20.316
    expected_pnl: float  # Current: $79,563
    confidence_interval_lower: float
    confidence_interval_upper: float
    months_of_data: int  # Current: 6
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class VolatilityMetrics:
    """Real-time volatility measurements"""
    current_volatility: float
    historical_volatility_20d: float
    volatility_percentile: float  # 0-100
    volatility_regime: str  # "low", "normal", "high", "extreme"
    atr_14: float  # Average True Range
    price_kurtosis_20d: float


@dataclass
class SessionPositionLimits:
    """Session-specific position limits"""
    max_position_percent: float
    max_risk_per_trade: float
    confidence_threshold: float
    risk_reward_requirement: float
    max_concurrent_positions: int


@dataclass
class CapitalAllocationPhase:
    """Phased capital allocation settings"""
    phase_number: int
    capital_allocation_percent: float
    required_stability_score: float
    required_validation_score: float
    minimum_data_months: int
    performance_gate_met: bool


@dataclass
class EnhancedSizingResult(PositionSizingResult):
    """Enhanced position sizing result with forward test adjustments"""
    base_units: int
    volatility_adjusted_units: int
    stability_adjusted_units: int
    final_units: int
    stability_reduction_factor: float
    volatility_reduction_factor: float
    validation_reduction_factor: float
    total_reduction_factor: float
    current_allocation_phase: int
    phase_capital_limit_units: int
    session_limit_units: int
    kurtosis_protection_applied: bool
    forward_test_warnings: List[str]


class ForwardTestPositionSizing(AdvancedPositionSizing):
    """
    Position sizing engine enhanced with forward testing controls
    """

    def __init__(self):
        super().__init__()

        # Initialize forward test metrics with current values
        self.forward_metrics = ForwardTestMetrics(
            walk_forward_stability=34.4,
            out_of_sample_validation=17.4,
            overfitting_score=0.634,
            kurtosis_exposure=20.316,
            expected_pnl=79563,
            confidence_interval_lower=45000,
            confidence_interval_upper=115000,
            months_of_data=6
        )

        # Stability-based risk reduction factors
        self.stability_adjustments = {
            StabilityLevel.CRITICAL: 0.25,  # 75% reduction
            StabilityLevel.LOW: 0.40,       # 60% reduction
            StabilityLevel.MEDIUM: 0.60,    # 40% reduction
            StabilityLevel.HIGH: 0.85,      # 15% reduction
            StabilityLevel.EXCELLENT: 1.0   # No reduction
        }

        # Validation score-based adjustments
        self.validation_adjustments = {
            ValidationScore.POOR: 0.20,     # 80% reduction
            ValidationScore.WEAK: 0.35,     # 65% reduction
            ValidationScore.MODERATE: 0.55, # 45% reduction
            ValidationScore.GOOD: 0.80,     # 20% reduction
            ValidationScore.STRONG: 1.0     # No reduction
        }

        # Session-specific limits based on forward test optimization
        self.session_limits = {
            TradingSession.SYDNEY: SessionPositionLimits(
                max_position_percent=15.0,
                max_risk_per_trade=1.5,
                confidence_threshold=78.0,
                risk_reward_requirement=3.5,
                max_concurrent_positions=3
            ),
            TradingSession.TOKYO: SessionPositionLimits(
                max_position_percent=20.0,
                max_risk_per_trade=1.8,
                confidence_threshold=85.0,
                risk_reward_requirement=4.0,
                max_concurrent_positions=4
            ),
            TradingSession.LONDON: SessionPositionLimits(
                max_position_percent=25.0,
                max_risk_per_trade=2.2,
                confidence_threshold=72.0,
                risk_reward_requirement=3.2,
                max_concurrent_positions=5
            ),
            TradingSession.NEW_YORK: SessionPositionLimits(
                max_position_percent=22.0,
                max_risk_per_trade=2.0,
                confidence_threshold=70.0,
                risk_reward_requirement=2.8,
                max_concurrent_positions=4
            ),
            TradingSession.OVERLAP: SessionPositionLimits(
                max_position_percent=18.0,
                max_risk_per_trade=1.6,
                confidence_threshold=70.0,
                risk_reward_requirement=2.8,
                max_concurrent_positions=3
            )
        }

        # Capital allocation phases
        self.allocation_phases = [
            CapitalAllocationPhase(
                phase_number=1,
                capital_allocation_percent=10.0,
                required_stability_score=50.0,
                required_validation_score=50.0,
                minimum_data_months=8,
                performance_gate_met=False
            ),
            CapitalAllocationPhase(
                phase_number=2,
                capital_allocation_percent=25.0,
                required_stability_score=60.0,
                required_validation_score=60.0,
                minimum_data_months=9,
                performance_gate_met=False
            ),
            CapitalAllocationPhase(
                phase_number=3,
                capital_allocation_percent=50.0,
                required_stability_score=70.0,
                required_validation_score=70.0,
                minimum_data_months=10,
                performance_gate_met=False
            ),
            CapitalAllocationPhase(
                phase_number=4,
                capital_allocation_percent=100.0,
                required_stability_score=80.0,
                required_validation_score=80.0,
                minimum_data_months=12,
                performance_gate_met=False
            )
        ]

        # Kurtosis risk thresholds
        self.kurtosis_thresholds = {
            "low": 3.0,      # Normal distribution
            "moderate": 7.0,  # Slightly elevated
            "high": 15.0,    # Significant tail risk
            "extreme": 25.0  # Critical tail risk
        }

        # Volatility adjustment factors
        self.volatility_adjustments = {
            "low": 1.2,      # Can increase size in low volatility
            "normal": 1.0,   # Standard sizing
            "high": 0.7,     # Reduce in high volatility
            "extreme": 0.3   # Significant reduction in extreme volatility
        }

        logger.info("Forward Test Position Sizing Engine initialized with current metrics")

    async def calculate_enhanced_position_size(
        self,
        signal: TradeSignal,
        account_id: str,
        oanda_client,
        current_session: TradingSession,
        current_positions: Optional[List] = None
    ) -> EnhancedSizingResult:
        """
        Calculate position size with forward test-based controls

        Args:
            signal: Trading signal to size
            account_id: OANDA account ID
            oanda_client: OANDA client for account data
            current_session: Current trading session
            current_positions: Optional current positions

        Returns:
            EnhancedSizingResult with comprehensive risk adjustments
        """
        try:
            # Get base position sizing from parent class
            base_result = await super().calculate_position_size(
                signal, account_id, oanda_client, current_positions
            )

            # Get account information
            account_info = await oanda_client.get_account_info(account_id)
            balance = float(account_info.balance)

            # Calculate volatility metrics
            volatility_metrics = await self._calculate_volatility_metrics(
                signal.instrument, oanda_client
            )

            # Get current capital allocation phase
            current_phase = self._get_current_allocation_phase()

            # Calculate all adjustment factors
            stability_factor = self._calculate_stability_adjustment()
            validation_factor = self._calculate_validation_adjustment()
            volatility_factor = self._calculate_volatility_adjustment(volatility_metrics)
            kurtosis_factor = self._calculate_kurtosis_adjustment(volatility_metrics)

            # Get session-specific limits
            session_limit = self.session_limits.get(
                current_session,
                self.session_limits[TradingSession.NEW_YORK]  # Default
            )

            # Calculate various position size limits
            base_units = abs(base_result.recommended_units)

            # Apply forward test adjustments
            stability_adjusted = int(base_units * stability_factor)
            validation_adjusted = int(stability_adjusted * validation_factor)
            volatility_adjusted = int(validation_adjusted * volatility_factor)
            kurtosis_adjusted = int(volatility_adjusted * kurtosis_factor)

            # Apply phase capital limits
            phase_limit_units = self._calculate_phase_limit_units(
                balance, current_phase, signal.entry_price
            )

            # Apply session position limits
            session_limit_units = self._calculate_session_limit_units(
                balance, session_limit, signal.entry_price
            )

            # Take the most conservative limit
            final_units = min(
                kurtosis_adjusted,
                phase_limit_units,
                session_limit_units,
                base_result.max_safe_units
            )

            # Apply direction
            if signal.direction in ["SELL", "short", "sell"]:
                final_units = -final_units

            # Calculate total reduction factor
            total_reduction = (
                stability_factor *
                validation_factor *
                volatility_factor *
                kurtosis_factor
            )

            # Generate forward test specific warnings
            ft_warnings = self._generate_forward_test_warnings(
                stability_factor,
                validation_factor,
                volatility_metrics,
                current_phase,
                session_limit
            )

            # Combine all warnings
            all_warnings = base_result.warning_messages + ft_warnings

            # Determine if trade meets forward test criteria
            is_safe = (
                base_result.is_safe_to_trade and
                self._check_forward_test_criteria(signal, session_limit) and
                current_phase.performance_gate_met
            )

            return EnhancedSizingResult(
                # Base fields
                recommended_units=final_units,
                effective_risk_percent=base_result.effective_risk_percent * total_reduction,
                concentration_after_trade=base_result.concentration_after_trade,
                risk_adjustment_factor=base_result.risk_adjustment_factor,
                warning_messages=all_warnings,
                is_safe_to_trade=is_safe,
                max_safe_units=base_result.max_safe_units,
                # Enhanced fields
                base_units=base_units,
                volatility_adjusted_units=volatility_adjusted,
                stability_adjusted_units=stability_adjusted,
                final_units=abs(final_units),
                stability_reduction_factor=stability_factor,
                volatility_reduction_factor=volatility_factor,
                validation_reduction_factor=validation_factor,
                total_reduction_factor=total_reduction,
                current_allocation_phase=current_phase.phase_number,
                phase_capital_limit_units=phase_limit_units,
                session_limit_units=session_limit_units,
                kurtosis_protection_applied=(kurtosis_factor < 1.0),
                forward_test_warnings=ft_warnings
            )

        except Exception as e:
            logger.error(f"Error in enhanced position sizing: {e}")
            # Return zero-size position on error
            return EnhancedSizingResult(
                recommended_units=0,
                effective_risk_percent=0.0,
                concentration_after_trade=0.0,
                risk_adjustment_factor=0.0,
                warning_messages=[f"Enhanced sizing error: {e}"],
                is_safe_to_trade=False,
                max_safe_units=0,
                base_units=0,
                volatility_adjusted_units=0,
                stability_adjusted_units=0,
                final_units=0,
                stability_reduction_factor=0.0,
                volatility_reduction_factor=0.0,
                validation_reduction_factor=0.0,
                total_reduction_factor=0.0,
                current_allocation_phase=0,
                phase_capital_limit_units=0,
                session_limit_units=0,
                kurtosis_protection_applied=False,
                forward_test_warnings=["Sizing calculation failed"]
            )

    def _get_stability_level(self) -> StabilityLevel:
        """Determine current stability level"""
        score = self.forward_metrics.walk_forward_stability
        if score < 30:
            return StabilityLevel.CRITICAL
        elif score < 50:
            return StabilityLevel.LOW
        elif score < 70:
            return StabilityLevel.MEDIUM
        elif score < 90:
            return StabilityLevel.HIGH
        else:
            return StabilityLevel.EXCELLENT

    def _get_validation_score(self) -> ValidationScore:
        """Determine current validation score level"""
        score = self.forward_metrics.out_of_sample_validation
        if score < 30:
            return ValidationScore.POOR
        elif score < 50:
            return ValidationScore.WEAK
        elif score < 70:
            return ValidationScore.MODERATE
        elif score < 85:
            return ValidationScore.GOOD
        else:
            return ValidationScore.STRONG

    def _calculate_stability_adjustment(self) -> float:
        """Calculate position size adjustment based on walk-forward stability"""
        stability_level = self._get_stability_level()
        adjustment = self.stability_adjustments[stability_level]

        # Additional penalty for very low stability
        if self.forward_metrics.walk_forward_stability < 20:
            adjustment *= 0.5  # Extra 50% reduction

        logger.debug(f"Stability adjustment: {adjustment:.2f} (level: {stability_level.value})")
        return adjustment

    def _calculate_validation_adjustment(self) -> float:
        """Calculate adjustment based on out-of-sample validation"""
        validation_level = self._get_validation_score()
        adjustment = self.validation_adjustments[validation_level]

        # Severe penalty for very poor validation
        if self.forward_metrics.out_of_sample_validation < 10:
            adjustment *= 0.3  # Extra 70% reduction

        logger.debug(f"Validation adjustment: {adjustment:.2f} (level: {validation_level.value})")
        return adjustment

    async def _calculate_volatility_metrics(
        self,
        instrument: str,
        oanda_client
    ) -> VolatilityMetrics:
        """Calculate current volatility metrics for the instrument"""
        try:
            # Get recent price data (simplified for now)
            # In production, this would fetch actual market data
            current_volatility = 0.015  # 1.5% placeholder
            historical_vol = 0.012  # 1.2% placeholder

            # Determine volatility regime
            if current_volatility < 0.008:
                regime = "low"
            elif current_volatility < 0.02:
                regime = "normal"
            elif current_volatility < 0.04:
                regime = "high"
            else:
                regime = "extreme"

            return VolatilityMetrics(
                current_volatility=current_volatility,
                historical_volatility_20d=historical_vol,
                volatility_percentile=65.0,  # Placeholder
                volatility_regime=regime,
                atr_14=0.0015,  # Placeholder
                price_kurtosis_20d=self.forward_metrics.kurtosis_exposure
            )

        except Exception as e:
            logger.error(f"Error calculating volatility metrics: {e}")
            # Return conservative defaults
            return VolatilityMetrics(
                current_volatility=0.03,
                historical_volatility_20d=0.02,
                volatility_percentile=80.0,
                volatility_regime="high",
                atr_14=0.002,
                price_kurtosis_20d=20.0
            )

    def _calculate_volatility_adjustment(self, metrics: VolatilityMetrics) -> float:
        """Calculate position size adjustment based on volatility"""
        base_adjustment = self.volatility_adjustments.get(
            metrics.volatility_regime, 0.5
        )

        # Additional adjustment for volatility percentile
        if metrics.volatility_percentile > 90:
            base_adjustment *= 0.7  # Extra reduction for extreme percentiles
        elif metrics.volatility_percentile > 80:
            base_adjustment *= 0.85

        logger.debug(f"Volatility adjustment: {base_adjustment:.2f} (regime: {metrics.volatility_regime})")
        return base_adjustment

    def _calculate_kurtosis_adjustment(self, metrics: VolatilityMetrics) -> float:
        """Calculate adjustment for high kurtosis (tail risk)"""
        kurtosis = metrics.price_kurtosis_20d

        if kurtosis < self.kurtosis_thresholds["low"]:
            adjustment = 1.0  # No reduction
        elif kurtosis < self.kurtosis_thresholds["moderate"]:
            adjustment = 0.9  # 10% reduction
        elif kurtosis < self.kurtosis_thresholds["high"]:
            adjustment = 0.7  # 30% reduction
        elif kurtosis < self.kurtosis_thresholds["extreme"]:
            adjustment = 0.5  # 50% reduction
        else:
            adjustment = 0.25  # 75% reduction for extreme kurtosis

        logger.debug(f"Kurtosis adjustment: {adjustment:.2f} (kurtosis: {kurtosis:.2f})")
        return adjustment

    def _get_current_allocation_phase(self) -> CapitalAllocationPhase:
        """Determine current capital allocation phase based on metrics"""
        # Check phases in order and return the highest qualifying phase
        for phase in reversed(self.allocation_phases):
            if self._check_phase_requirements(phase):
                return phase

        # Return phase 1 if no phases qualify (conservative default)
        return self.allocation_phases[0]

    def _check_phase_requirements(self, phase: CapitalAllocationPhase) -> bool:
        """Check if current metrics meet phase requirements"""
        meets_stability = self.forward_metrics.walk_forward_stability >= phase.required_stability_score
        meets_validation = self.forward_metrics.out_of_sample_validation >= phase.required_validation_score
        meets_data = self.forward_metrics.months_of_data >= phase.minimum_data_months

        # Update performance gate status
        phase.performance_gate_met = meets_stability and meets_validation and meets_data

        return phase.performance_gate_met

    def _calculate_phase_limit_units(
        self,
        balance: float,
        phase: CapitalAllocationPhase,
        entry_price: Optional[float]
    ) -> int:
        """Calculate maximum units based on capital allocation phase"""
        if not entry_price or entry_price <= 0:
            return 0

        # Maximum capital for this phase
        max_capital = balance * (phase.capital_allocation_percent / 100.0)

        # Maximum units based on phase capital
        max_units = int(max_capital / entry_price)

        logger.debug(f"Phase {phase.phase_number} limit: {max_units} units "
                    f"({phase.capital_allocation_percent}% of capital)")

        return max_units

    def _calculate_session_limit_units(
        self,
        balance: float,
        session_limit: SessionPositionLimits,
        entry_price: Optional[float]
    ) -> int:
        """Calculate maximum units based on session limits"""
        if not entry_price or entry_price <= 0:
            return 0

        # Maximum position value for this session
        max_position_value = balance * (session_limit.max_position_percent / 100.0)

        # Maximum units based on session limit
        max_units = int(max_position_value / entry_price)

        logger.debug(f"Session limit: {max_units} units "
                    f"({session_limit.max_position_percent}% max position)")

        return max_units

    def _check_forward_test_criteria(
        self,
        signal: TradeSignal,
        session_limit: SessionPositionLimits
    ) -> bool:
        """Check if signal meets forward test criteria"""
        # Check confidence threshold
        if signal.confidence < session_limit.confidence_threshold:
            logger.debug(f"Signal confidence {signal.confidence} below session threshold "
                        f"{session_limit.confidence_threshold}")
            return False

        # Check risk-reward ratio
        if signal.stop_loss and signal.take_profit and signal.entry_price:
            risk = abs(signal.entry_price - signal.stop_loss)
            reward = abs(signal.take_profit - signal.entry_price)
            if risk > 0:
                rr_ratio = reward / risk
                if rr_ratio < session_limit.risk_reward_requirement:
                    logger.debug(f"Risk-reward ratio {rr_ratio:.2f} below session requirement "
                               f"{session_limit.risk_reward_requirement}")
                    return False

        # Check overfitting score
        if self.forward_metrics.overfitting_score > 0.5:
            logger.debug(f"Overfitting score {self.forward_metrics.overfitting_score} too high")
            return False

        return True

    def _generate_forward_test_warnings(
        self,
        stability_factor: float,
        validation_factor: float,
        volatility_metrics: VolatilityMetrics,
        current_phase: CapitalAllocationPhase,
        session_limit: SessionPositionLimits
    ) -> List[str]:
        """Generate warnings specific to forward test controls"""
        warnings = []

        # Stability warnings
        if stability_factor < 0.5:
            warnings.append(f"CRITICAL: Walk-forward stability very low ({self.forward_metrics.walk_forward_stability:.1f}/100)")
        elif stability_factor < 0.7:
            warnings.append(f"Low walk-forward stability reducing position ({self.forward_metrics.walk_forward_stability:.1f}/100)")

        # Validation warnings
        if validation_factor < 0.3:
            warnings.append(f"CRITICAL: Out-of-sample validation very poor ({self.forward_metrics.out_of_sample_validation:.1f}/100)")
        elif validation_factor < 0.6:
            warnings.append(f"Weak out-of-sample performance reducing position ({self.forward_metrics.out_of_sample_validation:.1f}/100)")

        # Overfitting warning
        if self.forward_metrics.overfitting_score > 0.5:
            warnings.append(f"High overfitting risk detected (score: {self.forward_metrics.overfitting_score:.3f})")

        # Kurtosis warning
        if volatility_metrics.price_kurtosis_20d > 15:
            warnings.append(f"High tail risk detected (kurtosis: {volatility_metrics.price_kurtosis_20d:.1f})")

        # Phase warnings
        if not current_phase.performance_gate_met:
            warnings.append(f"Phase {current_phase.phase_number} performance gates not met")

        if current_phase.phase_number < 3:
            warnings.append(f"Limited to {current_phase.capital_allocation_percent}% capital allocation (Phase {current_phase.phase_number})")

        # Volatility warnings
        if volatility_metrics.volatility_regime == "extreme":
            warnings.append("Extreme volatility detected - position significantly reduced")
        elif volatility_metrics.volatility_regime == "high":
            warnings.append("High volatility environment - position reduced")

        return warnings

    async def update_forward_metrics(
        self,
        new_metrics: Dict[str, Any]
    ) -> None:
        """Update forward test metrics (called periodically with new test results)"""
        try:
            if "walk_forward_stability" in new_metrics:
                self.forward_metrics.walk_forward_stability = new_metrics["walk_forward_stability"]

            if "out_of_sample_validation" in new_metrics:
                self.forward_metrics.out_of_sample_validation = new_metrics["out_of_sample_validation"]

            if "overfitting_score" in new_metrics:
                self.forward_metrics.overfitting_score = new_metrics["overfitting_score"]

            if "kurtosis_exposure" in new_metrics:
                self.forward_metrics.kurtosis_exposure = new_metrics["kurtosis_exposure"]

            if "months_of_data" in new_metrics:
                self.forward_metrics.months_of_data = new_metrics["months_of_data"]

            self.forward_metrics.last_updated = datetime.now()

            logger.info(f"Forward test metrics updated: stability={self.forward_metrics.walk_forward_stability:.1f}, "
                       f"validation={self.forward_metrics.out_of_sample_validation:.1f}")

        except Exception as e:
            logger.error(f"Error updating forward metrics: {e}")

    async def get_current_sizing_status(self) -> Dict[str, Any]:
        """Get current position sizing status and metrics"""
        current_phase = self._get_current_allocation_phase()
        stability_level = self._get_stability_level()
        validation_level = self._get_validation_score()

        return {
            "forward_metrics": {
                "walk_forward_stability": self.forward_metrics.walk_forward_stability,
                "out_of_sample_validation": self.forward_metrics.out_of_sample_validation,
                "overfitting_score": self.forward_metrics.overfitting_score,
                "kurtosis_exposure": self.forward_metrics.kurtosis_exposure,
                "months_of_data": self.forward_metrics.months_of_data,
                "last_updated": self.forward_metrics.last_updated.isoformat()
            },
            "current_levels": {
                "stability_level": stability_level.value,
                "validation_level": validation_level.value,
                "stability_adjustment": self.stability_adjustments[stability_level],
                "validation_adjustment": self.validation_adjustments[validation_level]
            },
            "capital_allocation": {
                "current_phase": current_phase.phase_number,
                "capital_percent": current_phase.capital_allocation_percent,
                "performance_gate_met": current_phase.performance_gate_met,
                "required_stability": current_phase.required_stability_score,
                "required_validation": current_phase.required_validation_score
            },
            "risk_controls": {
                "base_risk_per_trade": self.base_risk_per_trade,
                "max_position_concentration": self.max_position_concentration,
                "kurtosis_protection_enabled": True,
                "volatility_adjustment_enabled": True
            }
        }


# Global instance
_forward_test_sizing: Optional[ForwardTestPositionSizing] = None


def get_forward_test_sizing() -> ForwardTestPositionSizing:
    """Get global forward test position sizing instance"""
    global _forward_test_sizing
    if _forward_test_sizing is None:
        _forward_test_sizing = ForwardTestPositionSizing()
    return _forward_test_sizing