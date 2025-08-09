"""
Strategy Parameter Adjustment System - Dynamic parameter modification based on market state
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from decimal import Decimal
from dataclasses import dataclass, asdict
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class AdjustmentReason(Enum):
    """Reasons for parameter adjustments"""
    REGIME_CHANGE = "regime_change"
    VOLATILITY_CHANGE = "volatility_change"
    SESSION_CHANGE = "session_change"
    ECONOMIC_EVENT = "economic_event"
    CORRELATION_BREAKDOWN = "correlation_breakdown"
    RISK_LIMIT = "risk_limit"


@dataclass
class TradingParameters:
    """Trading parameters that can be adjusted"""
    stop_loss_atr_multiple: float = 2.0
    take_profit_atr_multiple: float = 3.0
    position_size_percentage: float = 2.0
    signal_confidence_threshold: float = 75.0
    max_signals_per_week: int = 3
    holding_time_multiplier: float = 1.0
    max_correlation_exposure: float = 0.7
    volatility_filter_enabled: bool = True
    session_filter_enabled: bool = True
    economic_filter_enabled: bool = True


@dataclass
class ParameterAdjustment:
    """Parameter adjustment record"""
    timestamp: datetime
    reason: AdjustmentReason
    original_params: TradingParameters
    adjusted_params: TradingParameters
    adjustments: Dict[str, float]
    market_conditions: Dict[str, Any]


class ParameterAdjustmentEngine:
    """Dynamic parameter adjustment based on market conditions"""
    
    def __init__(self):
        self.base_parameters = TradingParameters()
        self.current_parameters = TradingParameters()
        self.adjustment_history: List[ParameterAdjustment] = []
        self.max_history_size = 100
        
        # Adjustment limits to prevent extreme changes
        self.adjustment_limits = {
            'stop_loss_atr_multiple': {'min': 1.0, 'max': 5.0},
            'take_profit_atr_multiple': {'min': 1.5, 'max': 6.0},
            'position_size_percentage': {'min': 0.5, 'max': 3.0},
            'signal_confidence_threshold': {'min': 60.0, 'max': 90.0},
            'max_signals_per_week': {'min': 1, 'max': 5},
            'holding_time_multiplier': {'min': 0.3, 'max': 3.0},
            'max_correlation_exposure': {'min': 0.3, 'max': 0.9}
        }
        
        # Regime-specific adjustments
        self.regime_adjustments = {
            'trending': {
                'stop_loss_atr_multiple': 1.5,
                'take_profit_atr_multiple': 1.3,
                'holding_time_multiplier': 2.0,
                'signal_confidence_threshold': -5.0,
                'max_signals_per_week': 1
            },
            'ranging': {
                'stop_loss_atr_multiple': 0.8,
                'take_profit_atr_multiple': 0.9,
                'holding_time_multiplier': 0.5,
                'signal_confidence_threshold': 5.0,
                'max_signals_per_week': 0
            },
            'volatile': {
                'stop_loss_atr_multiple': 2.0,
                'position_size_percentage': 0.6,
                'signal_confidence_threshold': 10.0,
                'max_signals_per_week': -1
            },
            'volatile_trending': {
                'stop_loss_atr_multiple': 1.8,
                'position_size_percentage': 0.7,
                'holding_time_multiplier': 1.5,
                'signal_confidence_threshold': 5.0
            },
            'volatile_ranging': {
                'stop_loss_atr_multiple': 1.5,
                'position_size_percentage': 0.5,
                'signal_confidence_threshold': 15.0,
                'max_signals_per_week': -2
            },
            'quiet': {
                'signal_confidence_threshold': 10.0,
                'max_signals_per_week': -1,
                'position_size_percentage': 0.8
            },
            'transitional': {
                'position_size_percentage': 0.7,
                'signal_confidence_threshold': 5.0,
                'max_signals_per_week': -1
            }
        }
    
    def adjust_parameters_for_market_state(
        self,
        market_state: Dict[str, Any]
    ) -> ParameterAdjustment:
        """
        Adjust trading parameters based on comprehensive market state
        
        Args:
            market_state: Current market state information
            
        Returns:
            Parameter adjustment record
        """
        original_params = TradingParameters(**asdict(self.current_parameters))
        adjustments = {}
        reasons = []
        
        # Apply regime-based adjustments
        if 'regime' in market_state:
            regime_adj = self._apply_regime_adjustments(market_state['regime'])
            adjustments.update(regime_adj)
            if regime_adj:
                reasons.append(AdjustmentReason.REGIME_CHANGE)
        
        # Apply volatility-based adjustments
        if 'volatility_regime' in market_state:
            vol_adj = self._apply_volatility_adjustments(market_state['volatility_regime'])
            adjustments = self._merge_adjustments(adjustments, vol_adj)
            if vol_adj:
                reasons.append(AdjustmentReason.VOLATILITY_CHANGE)
        
        # Apply session-based adjustments
        if 'session' in market_state:
            session_adj = self._apply_session_adjustments(market_state['session'])
            adjustments = self._merge_adjustments(adjustments, session_adj)
            if session_adj:
                reasons.append(AdjustmentReason.SESSION_CHANGE)
        
        # Apply economic event adjustments
        if market_state.get('economic_events'):
            event_adj = self._apply_economic_event_adjustments(market_state['economic_events'])
            adjustments = self._merge_adjustments(adjustments, event_adj)
            if event_adj:
                reasons.append(AdjustmentReason.ECONOMIC_EVENT)
        
        # Apply correlation breakdown adjustments
        if market_state.get('correlation_breakdown'):
            corr_adj = self._apply_correlation_adjustments(market_state['correlation_breakdown'])
            adjustments = self._merge_adjustments(adjustments, corr_adj)
            if corr_adj:
                reasons.append(AdjustmentReason.CORRELATION_BREAKDOWN)
        
        # Apply adjustments to current parameters
        adjusted_params = self._apply_adjustments(adjustments)
        
        # Create adjustment record
        adjustment = ParameterAdjustment(
            timestamp=datetime.now(timezone.utc),
            reason=reasons[0] if reasons else AdjustmentReason.REGIME_CHANGE,
            original_params=original_params,
            adjusted_params=adjusted_params,
            adjustments=adjustments,
            market_conditions=market_state
        )
        
        # Update current parameters
        self.current_parameters = adjusted_params
        
        # Store in history
        self._add_to_history(adjustment)
        
        return adjustment
    
    def _apply_regime_adjustments(self, regime: str) -> Dict[str, float]:
        """
        Apply regime-specific adjustments
        
        Args:
            regime: Market regime
            
        Returns:
            Adjustment multipliers/changes
        """
        if regime not in self.regime_adjustments:
            return {}
        
        adjustments = {}
        regime_adj = self.regime_adjustments[regime]
        
        for param, value in regime_adj.items():
            if param in ['stop_loss_atr_multiple', 'take_profit_atr_multiple', 
                        'holding_time_multiplier', 'position_size_percentage']:
                # These are multipliers
                adjustments[param] = value
            else:
                # These are additions
                adjustments[param] = value
        
        return adjustments
    
    def _apply_volatility_adjustments(self, volatility_regime: str) -> Dict[str, float]:
        """
        Apply volatility-based adjustments
        
        Args:
            volatility_regime: Volatility regime
            
        Returns:
            Adjustment values
        """
        adjustments = {}
        
        if volatility_regime == 'very_low':
            adjustments['position_size_percentage'] = 1.2
            adjustments['stop_loss_atr_multiple'] = 0.8
        elif volatility_regime == 'low':
            adjustments['position_size_percentage'] = 1.1
            adjustments['stop_loss_atr_multiple'] = 0.9
        elif volatility_regime == 'high':
            adjustments['position_size_percentage'] = 0.8
            adjustments['stop_loss_atr_multiple'] = 1.3
        elif volatility_regime == 'very_high':
            adjustments['position_size_percentage'] = 0.6
            adjustments['stop_loss_atr_multiple'] = 1.5
            adjustments['max_signals_per_week'] = -1
        elif volatility_regime == 'extreme':
            adjustments['position_size_percentage'] = 0.3
            adjustments['stop_loss_atr_multiple'] = 2.0
            adjustments['max_signals_per_week'] = -2
            adjustments['signal_confidence_threshold'] = 15.0
        
        return adjustments
    
    def _apply_session_adjustments(self, session: Dict[str, Any]) -> Dict[str, float]:
        """
        Apply session-based adjustments
        
        Args:
            session: Trading session information
            
        Returns:
            Adjustment values
        """
        adjustments = {}
        
        session_type = session.get('type', 'single')
        
        if session_type == 'overlap':
            # Higher volatility during overlaps
            adjustments['stop_loss_atr_multiple'] = 1.2
            adjustments['position_size_percentage'] = 0.9
        elif session_type == 'quiet' or session.get('name') == 'off_hours':
            # Lower activity periods
            adjustments['signal_confidence_threshold'] = 10.0
            adjustments['max_signals_per_week'] = -1
            adjustments['position_size_percentage'] = 0.7
        elif session.get('is_peak'):
            # Peak hours of major sessions
            adjustments['position_size_percentage'] = 1.1
        
        return adjustments
    
    def _apply_economic_event_adjustments(
        self, 
        events: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Apply economic event adjustments
        
        Args:
            events: List of economic events
            
        Returns:
            Adjustment values
        """
        adjustments = {}
        
        # Check for high-impact events
        high_impact_count = sum(1 for e in events if e.get('importance') == 'high')
        
        if high_impact_count > 0:
            adjustments['position_size_percentage'] = 0.5
            adjustments['stop_loss_atr_multiple'] = 1.5
            adjustments['signal_confidence_threshold'] = 10.0
            
            if high_impact_count > 1:
                # Multiple high-impact events
                adjustments['max_signals_per_week'] = -2
                adjustments['position_size_percentage'] = 0.3
        
        return adjustments
    
    def _apply_correlation_adjustments(
        self, 
        breakdown_info: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Apply correlation breakdown adjustments
        
        Args:
            breakdown_info: Correlation breakdown information
            
        Returns:
            Adjustment values
        """
        adjustments = {}
        
        severity = breakdown_info.get('severity', 'none')
        
        if severity == 'extreme':
            adjustments['position_size_percentage'] = 0.5
            adjustments['max_correlation_exposure'] = 0.5
            adjustments['signal_confidence_threshold'] = 15.0
        elif severity == 'high':
            adjustments['position_size_percentage'] = 0.7
            adjustments['max_correlation_exposure'] = 0.6
            adjustments['signal_confidence_threshold'] = 10.0
        elif severity == 'moderate':
            adjustments['position_size_percentage'] = 0.85
            adjustments['max_correlation_exposure'] = 0.7
        
        return adjustments
    
    def _merge_adjustments(
        self, 
        base: Dict[str, float], 
        new: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Merge adjustment dictionaries
        
        Args:
            base: Base adjustments
            new: New adjustments to merge
            
        Returns:
            Merged adjustments
        """
        merged = base.copy()
        
        for param, value in new.items():
            if param in merged:
                if param in ['stop_loss_atr_multiple', 'take_profit_atr_multiple',
                           'position_size_percentage', 'holding_time_multiplier',
                           'max_correlation_exposure']:
                    # Multiply multipliers
                    merged[param] = merged[param] * value
                else:
                    # Add additions
                    merged[param] = merged[param] + value
            else:
                merged[param] = value
        
        return merged
    
    def _apply_adjustments(self, adjustments: Dict[str, float]) -> TradingParameters:
        """
        Apply adjustments to current parameters
        
        Args:
            adjustments: Adjustments to apply
            
        Returns:
            Adjusted parameters
        """
        params = TradingParameters(**asdict(self.base_parameters))
        
        for param, adjustment in adjustments.items():
            if hasattr(params, param):
                current_value = getattr(params, param)
                
                if param in ['stop_loss_atr_multiple', 'take_profit_atr_multiple',
                           'position_size_percentage', 'holding_time_multiplier',
                           'max_correlation_exposure']:
                    # Apply as multiplier
                    new_value = current_value * adjustment
                elif param in ['max_signals_per_week']:
                    # Apply as addition (integer)
                    new_value = int(current_value + adjustment)
                else:
                    # Apply as addition
                    new_value = current_value + adjustment
                
                # Apply limits
                if param in self.adjustment_limits:
                    limits = self.adjustment_limits[param]
                    new_value = max(limits['min'], min(limits['max'], new_value))
                
                setattr(params, param, new_value)
        
        return params
    
    def _add_to_history(self, adjustment: ParameterAdjustment):
        """
        Add adjustment to history
        
        Args:
            adjustment: Adjustment record
        """
        self.adjustment_history.append(adjustment)
        
        # Trim history if needed
        if len(self.adjustment_history) > self.max_history_size:
            self.adjustment_history = self.adjustment_history[-self.max_history_size:]
    
    def get_adjustment_summary(self) -> Dict[str, Any]:
        """
        Get summary of current adjustments
        
        Returns:
            Adjustment summary
        """
        if not self.adjustment_history:
            return {
                'current_parameters': asdict(self.current_parameters),
                'active_adjustments': {},
                'last_adjustment': None
            }
        
        last_adjustment = self.adjustment_history[-1]
        
        # Calculate active adjustments
        active_adjustments = {}
        base_dict = asdict(self.base_parameters)
        current_dict = asdict(self.current_parameters)
        
        for param in base_dict:
            if current_dict[param] != base_dict[param]:
                if isinstance(base_dict[param], (int, float)):
                    change_pct = ((current_dict[param] - base_dict[param]) / 
                                base_dict[param] * 100) if base_dict[param] != 0 else 0
                    active_adjustments[param] = {
                        'base': base_dict[param],
                        'current': current_dict[param],
                        'change_percent': round(change_pct, 1)
                    }
        
        return {
            'current_parameters': current_dict,
            'active_adjustments': active_adjustments,
            'last_adjustment': {
                'timestamp': last_adjustment.timestamp,
                'reason': last_adjustment.reason.value,
                'adjustments': last_adjustment.adjustments
            }
        }
    
    def reset_to_base_parameters(self):
        """Reset parameters to base values"""
        self.current_parameters = TradingParameters(**asdict(self.base_parameters))
        logger.info("Parameters reset to base values")