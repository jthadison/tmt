"""
Parameter Robustness Framework
Addresses September 2025 performance degradation through regularization and ensemble methods
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from enum import Enum
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ParameterRegime(Enum):
    """Market regime classifications for adaptive parameters"""
    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE = "volatile"
    QUIET = "quiet"
    UNKNOWN = "unknown"

@dataclass
class RobustParameters:
    """Regularized parameter set with confidence bounds"""
    confidence_threshold: float
    min_risk_reward: float
    max_risk_reward: float
    position_size_multiplier: float
    volatility_adjustment: float
    regime: ParameterRegime
    confidence_interval: Tuple[float, float]
    last_updated: datetime

class ParameterRegularizer:
    """Implements parameter regularization to prevent overfitting"""

    def __init__(self, base_config: Dict):
        self.base_config = base_config
        self.performance_history = []
        self.regime_history = []

        # Regularization constraints
        self.MIN_CONFIDENCE = 50.0
        self.MAX_CONFIDENCE = 90.0
        self.MIN_RISK_REWARD = 1.5
        self.MAX_RISK_REWARD = 5.0
        self.PERFORMANCE_WINDOW = 100  # trades for evaluation

    def regularize_parameters(self, raw_params: Dict, regime: ParameterRegime) -> RobustParameters:
        """Apply regularization constraints to prevent overfitting"""

        # Apply confidence bounds
        confidence = np.clip(
            raw_params.get("confidence_threshold", 70.0),
            self.MIN_CONFIDENCE,
            self.MAX_CONFIDENCE
        )

        # Apply risk-reward bounds
        min_rr = np.clip(
            raw_params.get("min_risk_reward", 2.0),
            self.MIN_RISK_REWARD,
            self.MAX_RISK_REWARD
        )

        # Add regime-specific adjustments
        if regime == ParameterRegime.VOLATILE:
            confidence += 5.0  # Higher selectivity in volatile markets
            min_rr += 0.5     # Higher risk-reward requirement
        elif regime == ParameterRegime.QUIET:
            confidence -= 3.0  # Lower selectivity in quiet markets
            min_rr -= 0.2     # Accept lower risk-reward

        # Calculate volatility adjustment based on recent performance
        volatility_adj = self._calculate_volatility_adjustment()

        # Generate confidence interval based on historical performance
        confidence_interval = self._calculate_confidence_interval()

        return RobustParameters(
            confidence_threshold=np.clip(confidence, self.MIN_CONFIDENCE, self.MAX_CONFIDENCE),
            min_risk_reward=np.clip(min_rr, self.MIN_RISK_REWARD, self.MAX_RISK_REWARD),
            max_risk_reward=min_rr * 1.5,  # Cap maximum R:R
            position_size_multiplier=1.0 - volatility_adj,  # Reduce size in high volatility
            volatility_adjustment=volatility_adj,
            regime=regime,
            confidence_interval=confidence_interval,
            last_updated=datetime.utcnow()
        )

    def _calculate_volatility_adjustment(self) -> float:
        """Calculate position size adjustment based on recent volatility"""
        if len(self.performance_history) < 10:
            return 0.0

        recent_performance = self.performance_history[-20:]
        volatility = np.std(recent_performance)

        # Scale adjustment from 0 to 0.3 (max 30% reduction)
        max_volatility = 1000  # Calibrated threshold
        adjustment = min(volatility / max_volatility, 0.3)

        return adjustment

    def _calculate_confidence_interval(self) -> Tuple[float, float]:
        """Calculate 90% confidence interval for expected performance"""
        if len(self.performance_history) < 30:
            return (0.0, 0.0)

        recent_performance = np.array(self.performance_history[-100:])
        mean_perf = np.mean(recent_performance)
        std_perf = np.std(recent_performance)

        # 90% confidence interval
        lower = mean_perf - 1.645 * std_perf
        upper = mean_perf + 1.645 * std_perf

        return (lower, upper)

    def update_performance(self, trade_pnl: float, regime: ParameterRegime):
        """Update performance history for adaptive adjustments"""
        self.performance_history.append(trade_pnl)
        self.regime_history.append(regime)

        # Keep only recent history
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-500:]
            self.regime_history = self.regime_history[-500:]

class EnsembleParameterManager:
    """Manages multiple parameter sets for ensemble trading"""

    def __init__(self):
        self.parameter_sets = self._initialize_parameter_sets()
        self.performance_tracker = {}
        self.active_sets = list(self.parameter_sets.keys())

    def _initialize_parameter_sets(self) -> Dict[str, Dict]:
        """Initialize diverse parameter sets for ensemble approach"""
        return {
            "conservative": {
                "confidence_threshold": 80.0,
                "min_risk_reward": 3.0,
                "description": "High selectivity, conservative approach",
                "target_regime": ParameterRegime.VOLATILE
            },
            "balanced": {
                "confidence_threshold": 65.0,
                "min_risk_reward": 2.5,
                "description": "Balanced approach for most conditions",
                "target_regime": ParameterRegime.TRENDING
            },
            "aggressive": {
                "confidence_threshold": 55.0,
                "min_risk_reward": 2.0,
                "description": "Higher frequency, lower selectivity",
                "target_regime": ParameterRegime.RANGING
            },
            "adaptive": {
                "confidence_threshold": 70.0,
                "min_risk_reward": 2.8,
                "description": "Regime-adaptive parameters",
                "target_regime": ParameterRegime.UNKNOWN
            }
        }

    def get_ensemble_parameters(self, current_regime: ParameterRegime) -> Dict[str, RobustParameters]:
        """Get all active parameter sets for ensemble trading"""
        regularizer = ParameterRegularizer({})
        ensemble = {}

        for set_name, params in self.parameter_sets.items():
            if set_name in self.active_sets:
                robust_params = regularizer.regularize_parameters(params, current_regime)
                ensemble[set_name] = robust_params

        return ensemble

    def update_ensemble_performance(self, set_name: str, trade_pnl: float):
        """Track performance of each parameter set"""
        if set_name not in self.performance_tracker:
            self.performance_tracker[set_name] = []

        self.performance_tracker[set_name].append(trade_pnl)

        # Deactivate underperforming sets
        if len(self.performance_tracker[set_name]) >= 50:
            recent_performance = self.performance_tracker[set_name][-50:]
            avg_performance = np.mean(recent_performance)

            if avg_performance < -100:  # Threshold for deactivation
                if set_name in self.active_sets:
                    self.active_sets.remove(set_name)
                    logger.warning(f"Deactivated parameter set {set_name} due to poor performance")

    def get_best_performing_set(self) -> Optional[str]:
        """Identify the best performing parameter set"""
        if not self.performance_tracker:
            return "balanced"  # Default

        best_set = None
        best_performance = float('-inf')

        for set_name, performance in self.performance_tracker.items():
            if len(performance) >= 20:  # Minimum trades for evaluation
                avg_performance = np.mean(performance[-20:])
                if avg_performance > best_performance:
                    best_performance = avg_performance
                    best_set = set_name

        return best_set or "balanced"

# Conservative parameter backup for emergency rollback
EMERGENCY_PARAMETERS = {
    "confidence_threshold": 85.0,
    "min_risk_reward": 3.5,
    "max_trades_per_day": 5,
    "max_risk_per_trade": 0.5,
    "description": "Ultra-conservative emergency parameters"
}

def get_emergency_parameters() -> Dict:
    """Get ultra-conservative parameters for emergency situations"""
    return EMERGENCY_PARAMETERS.copy()