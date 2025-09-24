"""
Tail Risk Control System
Addresses high kurtosis exposure (20.316) identified in September 2025 analysis
Implements comprehensive protection against extreme market events
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from collections import deque
import asyncio

logger = logging.getLogger(__name__)

class TailRiskLevel(Enum):
    """Tail risk severity levels"""
    LOW = "low"           # Kurtosis < 3 (normal or thin tails)
    MODERATE = "moderate" # Kurtosis 3-6 (slightly elevated)
    HIGH = "high"         # Kurtosis 6-12 (significant tail risk)
    EXTREME = "extreme"   # Kurtosis 12-20 (dangerous)
    CRITICAL = "critical" # Kurtosis > 20 (emergency - like Sept 2025)

class VolatilityRegime(Enum):
    """Volatility regimes for position sizing"""
    CALM = "calm"               # <0.5% daily vol
    NORMAL = "normal"           # 0.5-1.0% daily vol
    ELEVATED = "elevated"       # 1.0-2.0% daily vol
    HIGH = "high"               # 2.0-3.0% daily vol
    EXTREME = "extreme"         # >3.0% daily vol

@dataclass
class TailRiskMetrics:
    """Real-time tail risk metrics"""
    kurtosis: float
    skewness: float
    max_drawdown_24h: float
    volatility_percentile: float
    jump_risk_score: float
    concentration_risk: float
    tail_risk_level: TailRiskLevel
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class PositionSizeAdjustment:
    """Dynamic position size adjustment based on tail risk"""
    base_size: float
    volatility_scalar: float
    kurtosis_scalar: float
    regime_scalar: float
    final_size: float
    max_allowed_size: float
    reduction_reason: str

@dataclass
class DynamicStopLoss:
    """Adaptive stop loss based on tail risk conditions"""
    base_stop_distance: float
    volatility_buffer: float
    kurtosis_buffer: float
    jump_protection: float
    final_stop_distance: float
    stop_price: float
    protection_level: str

class TailRiskController:
    """Main tail risk control system"""

    def __init__(self, config: Dict):
        self.config = config

        # Risk parameters calibrated to address 20.316 kurtosis issue
        self.KURTOSIS_THRESHOLDS = {
            TailRiskLevel.LOW: 3.0,
            TailRiskLevel.MODERATE: 6.0,
            TailRiskLevel.HIGH: 12.0,
            TailRiskLevel.EXTREME: 20.0,
            TailRiskLevel.CRITICAL: 30.0
        }

        # Position size multipliers by tail risk level
        self.POSITION_SIZE_MULTIPLIERS = {
            TailRiskLevel.LOW: 1.0,       # Full size
            TailRiskLevel.MODERATE: 0.8,  # 20% reduction
            TailRiskLevel.HIGH: 0.5,      # 50% reduction
            TailRiskLevel.EXTREME: 0.25,  # 75% reduction
            TailRiskLevel.CRITICAL: 0.1   # 90% reduction (emergency)
        }

        # Stop loss buffers by tail risk level (in ATR multiples)
        self.STOP_LOSS_BUFFERS = {
            TailRiskLevel.LOW: 1.5,       # 1.5x ATR
            TailRiskLevel.MODERATE: 2.0,  # 2x ATR
            TailRiskLevel.HIGH: 3.0,      # 3x ATR
            TailRiskLevel.EXTREME: 4.0,   # 4x ATR
            TailRiskLevel.CRITICAL: 5.0   # 5x ATR (wide stops)
        }

        # Historical data storage
        self.returns_history = deque(maxlen=1000)
        self.volatility_history = deque(maxlen=500)
        self.kurtosis_history = deque(maxlen=100)
        self.drawdown_history = deque(maxlen=30)

        # Current state
        self.current_metrics: Optional[TailRiskMetrics] = None
        self.position_limits = {}
        self.emergency_mode = False

        # Monitoring
        self.extreme_events_24h = 0
        self.last_extreme_event: Optional[datetime] = None
        self.consecutive_losses = 0

    def calculate_tail_risk_metrics(self, returns: pd.Series) -> TailRiskMetrics:
        """Calculate comprehensive tail risk metrics"""

        if len(returns) < 30:
            # Insufficient data - assume high risk
            return TailRiskMetrics(
                kurtosis=10.0,
                skewness=0.0,
                max_drawdown_24h=0.0,
                volatility_percentile=50.0,
                jump_risk_score=0.5,
                concentration_risk=0.5,
                tail_risk_level=TailRiskLevel.HIGH
            )

        # Calculate kurtosis (excess kurtosis, where normal = 0)
        kurtosis = returns.kurtosis()

        # Calculate skewness (asymmetry of returns)
        skewness = returns.skew()

        # Calculate 24h maximum drawdown
        cumulative_returns = (1 + returns.tail(24)).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown_24h = drawdown.min()

        # Calculate volatility percentile (where does current vol rank historically)
        current_vol = returns.tail(20).std()
        if self.volatility_history:
            vol_percentile = np.percentile(list(self.volatility_history),
                                         [i for i in range(101)]).tolist()
            volatility_percentile = np.searchsorted(vol_percentile, current_vol)
        else:
            volatility_percentile = 50.0

        self.volatility_history.append(current_vol)

        # Calculate jump risk (large sudden moves)
        jump_risk_score = self._calculate_jump_risk(returns)

        # Calculate concentration risk (are returns concentrated in few big trades)
        concentration_risk = self._calculate_concentration_risk(returns)

        # Determine tail risk level based on kurtosis
        tail_risk_level = self._classify_tail_risk_level(kurtosis)

        # Store metrics
        metrics = TailRiskMetrics(
            kurtosis=kurtosis,
            skewness=skewness,
            max_drawdown_24h=max_drawdown_24h,
            volatility_percentile=volatility_percentile,
            jump_risk_score=jump_risk_score,
            concentration_risk=concentration_risk,
            tail_risk_level=tail_risk_level
        )

        self.current_metrics = metrics
        self.kurtosis_history.append(kurtosis)

        return metrics

    def _calculate_jump_risk(self, returns: pd.Series) -> float:
        """Calculate jump risk score (0-1, higher = more jump risk)"""

        if len(returns) < 20:
            return 0.5

        # Calculate the ratio of large moves to normal moves
        std = returns.std()
        if std == 0:
            return 0.0

        # Count returns beyond 2 standard deviations
        extreme_returns = returns[abs(returns) > 2 * std]
        jump_frequency = len(extreme_returns) / len(returns)

        # Calculate average magnitude of jumps
        if len(extreme_returns) > 0:
            jump_magnitude = abs(extreme_returns).mean() / std
        else:
            jump_magnitude = 0.0

        # Combine frequency and magnitude
        jump_risk = min(1.0, jump_frequency * 5 + jump_magnitude / 10)

        return jump_risk

    def _calculate_concentration_risk(self, returns: pd.Series) -> float:
        """Calculate concentration risk (0-1, higher = more concentrated)"""

        if len(returns) < 10:
            return 0.5

        # Sort returns by absolute value
        sorted_returns = returns.abs().sort_values(ascending=False)

        # Calculate what percentage of total P&L comes from top 10% of trades
        top_10_pct = int(len(sorted_returns) * 0.1)
        if top_10_pct == 0:
            top_10_pct = 1

        top_10_contribution = sorted_returns.head(top_10_pct).sum()
        total_contribution = sorted_returns.sum()

        if total_contribution == 0:
            return 0.0

        concentration = top_10_contribution / total_contribution

        # High concentration (>50% from top 10%) is risky
        concentration_risk = min(1.0, concentration * 1.5)

        return concentration_risk

    def _classify_tail_risk_level(self, kurtosis: float) -> TailRiskLevel:
        """Classify tail risk level based on kurtosis"""

        # Note: Using excess kurtosis (normal = 0, not 3)
        excess_kurtosis = kurtosis

        if excess_kurtosis < 0:
            return TailRiskLevel.LOW
        elif excess_kurtosis < 3:
            return TailRiskLevel.MODERATE
        elif excess_kurtosis < 9:
            return TailRiskLevel.HIGH
        elif excess_kurtosis < 17:
            return TailRiskLevel.EXTREME
        else:
            return TailRiskLevel.CRITICAL

    def calculate_position_size_adjustment(self,
                                          base_position_size: float,
                                          instrument: str,
                                          current_price: float) -> PositionSizeAdjustment:
        """Calculate dynamic position size based on tail risk"""

        if not self.current_metrics:
            # No metrics available - be conservative
            return PositionSizeAdjustment(
                base_size=base_position_size,
                volatility_scalar=0.5,
                kurtosis_scalar=0.5,
                regime_scalar=1.0,
                final_size=base_position_size * 0.25,
                max_allowed_size=base_position_size * 0.5,
                reduction_reason="No risk metrics available - conservative sizing"
            )

        metrics = self.current_metrics

        # 1. Kurtosis-based scaling
        kurtosis_scalar = self.POSITION_SIZE_MULTIPLIERS[metrics.tail_risk_level]

        # 2. Volatility-based scaling
        if metrics.volatility_percentile > 90:
            volatility_scalar = 0.3  # 70% reduction in extreme volatility
        elif metrics.volatility_percentile > 75:
            volatility_scalar = 0.5  # 50% reduction in high volatility
        elif metrics.volatility_percentile > 60:
            volatility_scalar = 0.7  # 30% reduction in elevated volatility
        else:
            volatility_scalar = 1.0  # Normal volatility

        # 3. Regime-based scaling (additional safety layer)
        if metrics.jump_risk_score > 0.7:
            regime_scalar = 0.5  # High jump risk
        elif metrics.concentration_risk > 0.7:
            regime_scalar = 0.6  # High concentration risk
        elif metrics.max_drawdown_24h < -0.05:
            regime_scalar = 0.4  # Recent significant drawdown
        else:
            regime_scalar = 1.0

        # 4. Emergency overrides
        if self.emergency_mode:
            emergency_scalar = 0.1  # 90% reduction in emergency
        elif self.extreme_events_24h >= 3:
            emergency_scalar = 0.3  # Multiple extreme events today
        elif self.consecutive_losses >= 5:
            emergency_scalar = 0.5  # Consecutive loss protection
        else:
            emergency_scalar = 1.0

        # Calculate final position size
        combined_scalar = kurtosis_scalar * volatility_scalar * regime_scalar * emergency_scalar
        final_size = base_position_size * combined_scalar

        # Apply absolute maximum based on tail risk level
        max_sizes = {
            TailRiskLevel.LOW: base_position_size,
            TailRiskLevel.MODERATE: base_position_size * 0.8,
            TailRiskLevel.HIGH: base_position_size * 0.5,
            TailRiskLevel.EXTREME: base_position_size * 0.3,
            TailRiskLevel.CRITICAL: base_position_size * 0.1
        }
        max_allowed_size = max_sizes[metrics.tail_risk_level]

        final_size = min(final_size, max_allowed_size)

        # Generate reduction reason
        reasons = []
        if kurtosis_scalar < 1.0:
            reasons.append(f"Kurtosis risk ({metrics.kurtosis:.1f})")
        if volatility_scalar < 1.0:
            reasons.append(f"High volatility (P{metrics.volatility_percentile:.0f})")
        if regime_scalar < 1.0:
            reasons.append("Adverse regime")
        if emergency_scalar < 1.0:
            reasons.append("Emergency conditions")

        reduction_reason = ", ".join(reasons) if reasons else "Normal conditions"

        return PositionSizeAdjustment(
            base_size=base_position_size,
            volatility_scalar=volatility_scalar,
            kurtosis_scalar=kurtosis_scalar,
            regime_scalar=regime_scalar,
            final_size=final_size,
            max_allowed_size=max_allowed_size,
            reduction_reason=reduction_reason
        )

    def calculate_dynamic_stop_loss(self,
                                   entry_price: float,
                                   direction: str,  # 'long' or 'short'
                                   atr: float,
                                   base_stop_distance: Optional[float] = None) -> DynamicStopLoss:
        """Calculate adaptive stop loss based on tail risk"""

        if not self.current_metrics:
            # No metrics - use conservative stop
            base_distance = base_stop_distance or atr * 2
            return DynamicStopLoss(
                base_stop_distance=base_distance,
                volatility_buffer=atr,
                kurtosis_buffer=atr,
                jump_protection=atr * 0.5,
                final_stop_distance=base_distance + atr * 2.5,
                stop_price=entry_price - (base_distance + atr * 2.5) if direction == 'long'
                          else entry_price + (base_distance + atr * 2.5),
                protection_level="Conservative (no metrics)"
            )

        metrics = self.current_metrics

        # Base stop distance (if not provided, use 1.5 ATR)
        if base_stop_distance is None:
            base_stop_distance = atr * 1.5

        # 1. Kurtosis buffer (wider stops for fat tails)
        kurtosis_buffer = atr * self.STOP_LOSS_BUFFERS[metrics.tail_risk_level]

        # 2. Volatility buffer
        if metrics.volatility_percentile > 90:
            volatility_buffer = atr * 2.0  # Double buffer in extreme volatility
        elif metrics.volatility_percentile > 75:
            volatility_buffer = atr * 1.5
        elif metrics.volatility_percentile > 60:
            volatility_buffer = atr * 1.2
        else:
            volatility_buffer = atr * 1.0

        # 3. Jump protection (additional buffer for gap risk)
        if metrics.jump_risk_score > 0.7:
            jump_protection = atr * 1.5  # Large buffer for high jump risk
        elif metrics.jump_risk_score > 0.5:
            jump_protection = atr * 1.0
        elif metrics.jump_risk_score > 0.3:
            jump_protection = atr * 0.5
        else:
            jump_protection = atr * 0.25

        # 4. Skewness adjustment (asymmetric risk)
        if abs(metrics.skewness) > 1.0:
            skewness_buffer = atr * 0.5
        else:
            skewness_buffer = 0.0

        # Calculate final stop distance
        # Use the maximum of kurtosis and volatility buffers, then add jump protection
        primary_buffer = max(kurtosis_buffer, volatility_buffer)
        final_stop_distance = base_stop_distance + primary_buffer + jump_protection + skewness_buffer

        # Ensure minimum stop distance based on tail risk
        min_distances = {
            TailRiskLevel.LOW: atr * 1.5,
            TailRiskLevel.MODERATE: atr * 2.0,
            TailRiskLevel.HIGH: atr * 3.0,
            TailRiskLevel.EXTREME: atr * 4.0,
            TailRiskLevel.CRITICAL: atr * 5.0
        }
        min_distance = min_distances[metrics.tail_risk_level]
        final_stop_distance = max(final_stop_distance, min_distance)

        # Calculate actual stop price
        if direction == 'long':
            stop_price = entry_price - final_stop_distance
        else:  # short
            stop_price = entry_price + final_stop_distance

        # Determine protection level
        if metrics.tail_risk_level == TailRiskLevel.CRITICAL:
            protection_level = "EMERGENCY - Maximum protection"
        elif metrics.tail_risk_level == TailRiskLevel.EXTREME:
            protection_level = "Extreme - Wide stops for tail events"
        elif metrics.tail_risk_level == TailRiskLevel.HIGH:
            protection_level = "High - Enhanced protection"
        elif metrics.tail_risk_level == TailRiskLevel.MODERATE:
            protection_level = "Moderate - Standard protection"
        else:
            protection_level = "Normal - Base protection"

        return DynamicStopLoss(
            base_stop_distance=base_stop_distance,
            volatility_buffer=volatility_buffer,
            kurtosis_buffer=kurtosis_buffer,
            jump_protection=jump_protection,
            final_stop_distance=final_stop_distance,
            stop_price=stop_price,
            protection_level=protection_level
        )

    def check_max_consecutive_losses(self, trade_result: Dict) -> bool:
        """Track consecutive losses and trigger protection if needed"""

        if trade_result['pnl'] <= 0:
            self.consecutive_losses += 1

            if self.consecutive_losses >= 12:
                # Critical threshold from September analysis
                logger.critical(f"TAIL RISK: {self.consecutive_losses} consecutive losses - EMERGENCY MODE")
                self.emergency_mode = True
                return False  # Block new trades
            elif self.consecutive_losses >= 8:
                logger.warning(f"TAIL RISK: {self.consecutive_losses} consecutive losses - reducing exposure")
                return True  # Allow trades but with reduced size
            elif self.consecutive_losses >= 5:
                logger.info(f"Tail risk alert: {self.consecutive_losses} consecutive losses")
                return True
        else:
            self.consecutive_losses = 0  # Reset on winning trade

            # Check if we can exit emergency mode
            if self.emergency_mode and self.consecutive_losses == 0:
                logger.info("Exiting emergency mode after winning trade")
                self.emergency_mode = False

        return True  # Allow trading

    def detect_extreme_event(self, return_value: float, threshold_sigmas: float = 3.0) -> bool:
        """Detect if a return qualifies as an extreme event"""

        if len(self.returns_history) < 30:
            self.returns_history.append(return_value)
            return False

        # Calculate rolling statistics
        recent_returns = list(self.returns_history)[-30:]
        mean_return = np.mean(recent_returns)
        std_return = np.std(recent_returns)

        if std_return == 0:
            self.returns_history.append(return_value)
            return False

        # Check if return is extreme (beyond threshold sigmas)
        z_score = abs((return_value - mean_return) / std_return)
        is_extreme = z_score > threshold_sigmas

        if is_extreme:
            self.extreme_events_24h += 1
            self.last_extreme_event = datetime.utcnow()
            logger.warning(f"EXTREME EVENT DETECTED: Z-score {z_score:.2f}, Return: {return_value:.2%}")

            # Check if we've had too many extreme events
            if self.extreme_events_24h >= 3:
                logger.critical("Multiple extreme events in 24h - entering protective mode")

        self.returns_history.append(return_value)

        # Reset counter if 24h have passed
        if self.last_extreme_event and \
           datetime.utcnow() - self.last_extreme_event > timedelta(hours=24):
            self.extreme_events_24h = 0

        return is_extreme

    def calculate_volatility_regime(self, returns: pd.Series) -> VolatilityRegime:
        """Classify current volatility regime"""

        if len(returns) < 20:
            return VolatilityRegime.NORMAL

        # Calculate annualized volatility (assuming daily returns)
        daily_vol = returns.tail(20).std()
        annualized_vol = daily_vol * np.sqrt(252) * 100  # As percentage

        if annualized_vol < 8:
            return VolatilityRegime.CALM
        elif annualized_vol < 16:
            return VolatilityRegime.NORMAL
        elif annualized_vol < 32:
            return VolatilityRegime.ELEVATED
        elif annualized_vol < 48:
            return VolatilityRegime.HIGH
        else:
            return VolatilityRegime.EXTREME

    def get_early_warning_signals(self) -> Dict[str, Any]:
        """Get early warning signals for tail risk"""

        if not self.current_metrics:
            return {"status": "No data available"}

        warnings = []
        risk_score = 0

        # Check kurtosis trend
        if len(self.kurtosis_history) >= 5:
            recent_kurtosis = list(self.kurtosis_history)[-5:]
            kurtosis_trend = recent_kurtosis[-1] - recent_kurtosis[0]

            if kurtosis_trend > 5:
                warnings.append("Rapidly increasing kurtosis")
                risk_score += 30
            elif kurtosis_trend > 2:
                warnings.append("Rising kurtosis trend")
                risk_score += 15

        # Check current kurtosis level
        if self.current_metrics.kurtosis > 20:
            warnings.append(f"CRITICAL kurtosis level: {self.current_metrics.kurtosis:.1f}")
            risk_score += 40
        elif self.current_metrics.kurtosis > 12:
            warnings.append(f"Extreme kurtosis level: {self.current_metrics.kurtosis:.1f}")
            risk_score += 25
        elif self.current_metrics.kurtosis > 6:
            warnings.append(f"High kurtosis level: {self.current_metrics.kurtosis:.1f}")
            risk_score += 15

        # Check jump risk
        if self.current_metrics.jump_risk_score > 0.7:
            warnings.append(f"High jump risk: {self.current_metrics.jump_risk_score:.2f}")
            risk_score += 20

        # Check concentration risk
        if self.current_metrics.concentration_risk > 0.7:
            warnings.append(f"High concentration risk: {self.current_metrics.concentration_risk:.2f}")
            risk_score += 15

        # Check recent drawdown
        if self.current_metrics.max_drawdown_24h < -0.03:
            warnings.append(f"Recent drawdown: {self.current_metrics.max_drawdown_24h:.1%}")
            risk_score += 20

        # Check extreme events
        if self.extreme_events_24h >= 2:
            warnings.append(f"{self.extreme_events_24h} extreme events in 24h")
            risk_score += 25

        # Check consecutive losses
        if self.consecutive_losses >= 5:
            warnings.append(f"{self.consecutive_losses} consecutive losses")
            risk_score += 20

        # Determine overall risk level
        if risk_score >= 70:
            overall_risk = "CRITICAL - Consider halting trading"
        elif risk_score >= 50:
            overall_risk = "HIGH - Reduce exposure significantly"
        elif risk_score >= 30:
            overall_risk = "ELEVATED - Monitor closely"
        elif risk_score >= 15:
            overall_risk = "MODERATE - Some caution advised"
        else:
            overall_risk = "LOW - Normal conditions"

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "warnings": warnings,
            "risk_score": risk_score,
            "overall_risk": overall_risk,
            "current_kurtosis": self.current_metrics.kurtosis,
            "tail_risk_level": self.current_metrics.tail_risk_level.value,
            "emergency_mode": self.emergency_mode,
            "consecutive_losses": self.consecutive_losses,
            "extreme_events_24h": self.extreme_events_24h
        }

    def should_halt_trading(self) -> Tuple[bool, str]:
        """Determine if trading should be halted due to tail risk"""

        if self.emergency_mode:
            return True, "Emergency mode active - tail risk critical"

        if not self.current_metrics:
            return False, "Insufficient data to assess"

        # Critical kurtosis level (like September 2025)
        if self.current_metrics.kurtosis > 20:
            return True, f"Critical kurtosis level: {self.current_metrics.kurtosis:.1f}"

        # Multiple extreme events
        if self.extreme_events_24h >= 5:
            return True, f"Too many extreme events: {self.extreme_events_24h} in 24h"

        # Severe consecutive losses
        if self.consecutive_losses >= 12:
            return True, f"Excessive consecutive losses: {self.consecutive_losses}"

        # Combination of high risk factors
        risk_factors = 0
        if self.current_metrics.kurtosis > 15:
            risk_factors += 1
        if self.current_metrics.jump_risk_score > 0.8:
            risk_factors += 1
        if self.current_metrics.max_drawdown_24h < -0.05:
            risk_factors += 1
        if self.consecutive_losses >= 8:
            risk_factors += 1
        if self.extreme_events_24h >= 3:
            risk_factors += 1

        if risk_factors >= 3:
            return True, f"Multiple high-risk conditions active ({risk_factors} factors)"

        return False, "Trading conditions acceptable"

    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive tail risk summary"""

        if not self.current_metrics:
            return {
                "status": "No metrics available",
                "timestamp": datetime.utcnow().isoformat()
            }

        # Calculate position size for standard trade
        sample_adjustment = self.calculate_position_size_adjustment(1.0, "TEST", 100.0)

        return {
            "timestamp": self.current_metrics.timestamp.isoformat(),
            "tail_risk_level": self.current_metrics.tail_risk_level.value,
            "kurtosis": self.current_metrics.kurtosis,
            "skewness": self.current_metrics.skewness,
            "metrics": {
                "max_drawdown_24h": self.current_metrics.max_drawdown_24h,
                "volatility_percentile": self.current_metrics.volatility_percentile,
                "jump_risk_score": self.current_metrics.jump_risk_score,
                "concentration_risk": self.current_metrics.concentration_risk
            },
            "position_sizing": {
                "current_multiplier": sample_adjustment.final_size,
                "max_allowed": sample_adjustment.max_allowed_size,
                "reduction_reason": sample_adjustment.reduction_reason
            },
            "risk_state": {
                "emergency_mode": self.emergency_mode,
                "consecutive_losses": self.consecutive_losses,
                "extreme_events_24h": self.extreme_events_24h,
                "trading_allowed": not self.should_halt_trading()[0]
            },
            "early_warnings": self.get_early_warning_signals()
        }

# Example usage and testing
async def test_tail_risk_controls():
    """Test the tail risk control system"""

    print("TAIL RISK CONTROL SYSTEM TEST")
    print("=" * 50)

    config = {
        'max_kurtosis': 20.0,
        'max_consecutive_losses': 12,
        'extreme_event_threshold': 3.0
    }

    controller = TailRiskController(config)

    # Simulate returns with high kurtosis (like September 2025)
    np.random.seed(42)

    # Generate returns with fat tails
    normal_returns = np.random.normal(0.001, 0.01, 900)  # Normal days
    extreme_returns = np.random.normal(0, 0.05, 50) * np.random.choice([-1, 1], 50)  # Extreme events
    extreme_returns[0] = -0.08  # Add a severe loss
    extreme_returns[1] = 0.12   # Add a huge gain

    all_returns = np.concatenate([normal_returns, extreme_returns])
    np.random.shuffle(all_returns)

    returns_series = pd.Series(all_returns)

    # Calculate tail risk metrics
    metrics = controller.calculate_tail_risk_metrics(returns_series)

    print(f"\nTAIL RISK METRICS:")
    print(f"  Kurtosis: {metrics.kurtosis:.2f}")
    print(f"  Skewness: {metrics.skewness:.2f}")
    print(f"  Tail Risk Level: {metrics.tail_risk_level.value}")
    print(f"  Jump Risk Score: {metrics.jump_risk_score:.2f}")
    print(f"  Concentration Risk: {metrics.concentration_risk:.2f}")

    # Test position sizing
    base_size = 10000  # $10,000 base position
    adjustment = controller.calculate_position_size_adjustment(base_size, "EUR_USD", 1.1000)

    print(f"\nPOSITION SIZE ADJUSTMENT:")
    print(f"  Base Size: ${base_size:,.0f}")
    print(f"  Adjusted Size: ${adjustment.final_size:,.0f}")
    print(f"  Reduction: {(1 - adjustment.final_size/base_size)*100:.1f}%")
    print(f"  Reason: {adjustment.reduction_reason}")

    # Test dynamic stop loss
    entry_price = 1.1000
    atr = 0.0010
    stop_loss = controller.calculate_dynamic_stop_loss(entry_price, 'long', atr)

    print(f"\nDYNAMIC STOP LOSS:")
    print(f"  Entry Price: {entry_price:.4f}")
    print(f"  Stop Price: {stop_loss.stop_price:.4f}")
    print(f"  Stop Distance: {stop_loss.final_stop_distance:.4f} ({stop_loss.final_stop_distance/atr:.1f}x ATR)")
    print(f"  Protection Level: {stop_loss.protection_level}")

    # Check early warning signals
    warnings = controller.get_early_warning_signals()

    print(f"\nEARLY WARNING SIGNALS:")
    print(f"  Risk Score: {warnings['risk_score']}/100")
    print(f"  Overall Risk: {warnings['overall_risk']}")
    if warnings['warnings']:
        print(f"  Warnings:")
        for warning in warnings['warnings']:
            print(f"    - {warning}")

    # Check if trading should halt
    should_halt, reason = controller.should_halt_trading()

    print(f"\nTRADING STATUS:")
    print(f"  Should Halt: {'YES' if should_halt else 'NO'}")
    print(f"  Reason: {reason}")

    # Get risk summary
    summary = controller.get_risk_summary()

    print(f"\nRISK SUMMARY:")
    print(f"  Tail Risk Level: {summary['tail_risk_level']}")
    print(f"  Position Multiplier: {summary['position_sizing']['current_multiplier']:.2f}")
    print(f"  Trading Allowed: {summary['risk_state']['trading_allowed']}")

    print("\n" + "=" * 50)
    print("Tail risk control system test complete")

if __name__ == "__main__":
    asyncio.run(test_tail_risk_controls())