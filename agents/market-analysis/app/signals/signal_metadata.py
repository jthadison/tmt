"""
Signal Metadata Models

Comprehensive data models for trading signals with all required metadata,
performance tracking, and integration capabilities.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from decimal import Decimal
from datetime import datetime
import uuid
import json


@dataclass
class ConfidenceBreakdown:
    """Detailed breakdown of confidence scoring components"""
    pattern_confidence: float
    volume_confirmation: float
    timeframe_alignment: float
    market_context: float
    trend_strength: float
    support_resistance: float
    total_confidence: float
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for serialization"""
        return asdict(self)


@dataclass
class EntryConfirmation:
    """Entry confirmation requirements for signal execution"""
    volume_spike_required: bool = True
    volume_threshold_multiplier: float = 2.0
    momentum_threshold: float = 0.3
    timeout_minutes: int = 60
    price_confirmation_required: bool = True
    min_candle_close_percentage: float = 0.7  # % of candle range for confirmation
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)


@dataclass
class MarketContext:
    """Market context information at time of signal generation"""
    session: str  # 'asian', 'london', 'new_york', 'overlap'
    volatility_regime: str  # 'low', 'normal', 'high', 'extreme'
    market_state: str  # 'trending', 'ranging', 'choppy', 'breakout'
    trend_direction: str  # 'up', 'down', 'sideways'
    trend_strength: float  # 0-100
    atr_normalized: float  # Current ATR as % of price
    volume_regime: str  # 'low', 'normal', 'high', 'spike'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)


@dataclass
class PatternDetails:
    """Comprehensive pattern information"""
    pattern_type: str  # 'accumulation', 'spring', 'distribution', 'upthrust', etc.
    wyckoff_phase: str  # 'Phase A', 'Phase B', 'Phase C', 'Phase D', 'Phase E'
    pattern_stage: str  # 'early', 'developing', 'mature', 'completion'
    key_levels: Dict[str, float]  # Support, resistance, pivot points
    pattern_duration_bars: int
    pattern_height_points: float
    volume_characteristics: Dict[str, Any]
    invalidation_level: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)


@dataclass
class TradingSignal:
    """
    Comprehensive trading signal with all metadata required for execution
    and performance tracking.
    """
    # Unique identifiers
    signal_id: str
    symbol: str
    timeframe: str
    
    # Signal basics
    signal_type: str  # 'long' or 'short'
    pattern_type: str
    confidence: float
    confidence_breakdown: ConfidenceBreakdown
    
    # Price levels (using Decimal for precision)
    entry_price: Decimal
    stop_loss: Decimal
    take_profit_1: Decimal
    
    # Timing information
    generated_at: datetime
    valid_until: datetime
    expected_hold_time_hours: int
    
    # Context and details
    market_context: MarketContext
    pattern_details: PatternDetails
    entry_confirmation: EntryConfirmation
    
    # Attribution and tracking
    contributing_factors: List[str]
    
    # Optional fields with defaults
    take_profit_2: Optional[Decimal] = None
    take_profit_3: Optional[Decimal] = None
    risk_reward_ratio: float = 0.0
    model_version: str = "1.0"
    quality_score: float = 0.0
    status: str = "active"  # active, filled, cancelled, expired
    priority: str = "medium"  # low, medium, high
    
    def __post_init__(self):
        """Calculate derived fields after initialization"""
        if self.signal_id is None:
            self.signal_id = str(uuid.uuid4())
        
        # Calculate risk-reward ratio
        self.risk_reward_ratio = self._calculate_risk_reward_ratio()
        
        # Calculate quality score
        self.quality_score = self._calculate_quality_score()
    
    def _calculate_risk_reward_ratio(self) -> float:
        """Calculate risk-reward ratio for the signal"""
        if self.signal_type == 'long':
            risk = float(self.entry_price - self.stop_loss)
            reward = float(self.take_profit_1 - self.entry_price)
        else:  # short
            risk = float(self.stop_loss - self.entry_price)
            reward = float(self.entry_price - self.take_profit_1)
        
        return reward / risk if risk > 0 else 0.0
    
    def _calculate_quality_score(self) -> float:
        """Calculate overall signal quality score (0-100)"""
        # Weight different factors
        confidence_weight = 0.4
        rr_weight = 0.3
        pattern_weight = 0.2
        market_context_weight = 0.1
        
        # Normalize R:R ratio (cap at 5:1 for scoring)
        rr_normalized = min(self.risk_reward_ratio, 5.0) * 20  # Scale to 0-100
        
        # Pattern strength based on pattern maturity and type
        pattern_score = self._score_pattern_strength()
        
        # Market context score
        context_score = self._score_market_context()
        
        total_score = (
            self.confidence * confidence_weight +
            rr_normalized * rr_weight +
            pattern_score * pattern_weight +
            context_score * market_context_weight
        )
        
        return round(total_score, 2)
    
    def _score_pattern_strength(self) -> float:
        """Score pattern strength based on type and characteristics"""
        pattern_scores = {
            'spring': 85,
            'upthrust': 85,
            'accumulation': 80,
            'distribution': 80,
            'sign_of_strength': 75,
            'sign_of_weakness': 75,
            'backup': 70,
            'test': 70
        }
        
        base_score = pattern_scores.get(self.pattern_type, 60)
        
        # Adjust based on pattern stage
        stage_multipliers = {
            'completion': 1.0,
            'mature': 0.9,
            'developing': 0.8,
            'early': 0.7
        }
        
        multiplier = stage_multipliers.get(self.pattern_details.pattern_stage, 0.8)
        return base_score * multiplier
    
    def _score_market_context(self) -> float:
        """Score market context favorability"""
        base_score = 50
        
        # Adjust for volatility regime
        volatility_adjustments = {
            'low': -10,
            'normal': 10,
            'high': 5,
            'extreme': -20
        }
        base_score += volatility_adjustments.get(self.market_context.volatility_regime, 0)
        
        # Adjust for market state
        state_adjustments = {
            'trending': 15,
            'breakout': 10,
            'ranging': -5,
            'choppy': -15
        }
        base_score += state_adjustments.get(self.market_context.market_state, 0)
        
        # Adjust for trend alignment
        if self.signal_type == 'long' and self.market_context.trend_direction == 'up':
            base_score += 10
        elif self.signal_type == 'short' and self.market_context.trend_direction == 'down':
            base_score += 10
        elif self.market_context.trend_direction == 'sideways':
            base_score += 0
        else:
            base_score -= 10  # Against trend
        
        return max(0, min(100, base_score))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert signal to dictionary for serialization"""
        return {
            'signal_id': self.signal_id,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'signal_type': self.signal_type,
            'pattern_type': self.pattern_type,
            'confidence': self.confidence,
            'confidence_breakdown': self.confidence_breakdown.to_dict(),
            'entry_price': float(self.entry_price),
            'stop_loss': float(self.stop_loss),
            'take_profit_1': float(self.take_profit_1),
            'take_profit_2': float(self.take_profit_2) if self.take_profit_2 else None,
            'take_profit_3': float(self.take_profit_3) if self.take_profit_3 else None,
            'risk_reward_ratio': self.risk_reward_ratio,
            'generated_at': self.generated_at.isoformat(),
            'valid_until': self.valid_until.isoformat(),
            'expected_hold_time_hours': self.expected_hold_time_hours,
            'market_context': self.market_context.to_dict(),
            'pattern_details': self.pattern_details.to_dict(),
            'entry_confirmation': self.entry_confirmation.to_dict(),
            'contributing_factors': self.contributing_factors,
            'model_version': self.model_version,
            'quality_score': self.quality_score,
            'status': self.status,
            'priority': self.priority
        }
    
    def to_json(self) -> str:
        """Convert signal to JSON string"""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradingSignal':
        """Create TradingSignal from dictionary"""
        # Parse datetime fields
        generated_at = datetime.fromisoformat(data['generated_at'].replace('Z', '+00:00'))
        valid_until = datetime.fromisoformat(data['valid_until'].replace('Z', '+00:00'))
        
        # Parse nested objects
        confidence_breakdown = ConfidenceBreakdown(**data['confidence_breakdown'])
        market_context = MarketContext(**data['market_context'])
        pattern_details = PatternDetails(**data['pattern_details'])
        entry_confirmation = EntryConfirmation(**data['entry_confirmation'])
        
        return cls(
            signal_id=data['signal_id'],
            symbol=data['symbol'],
            timeframe=data['timeframe'],
            signal_type=data['signal_type'],
            pattern_type=data['pattern_type'],
            confidence=data['confidence'],
            confidence_breakdown=confidence_breakdown,
            entry_price=Decimal(str(data['entry_price'])),
            stop_loss=Decimal(str(data['stop_loss'])),
            take_profit_1=Decimal(str(data['take_profit_1'])),
            take_profit_2=Decimal(str(data['take_profit_2'])) if data.get('take_profit_2') else None,
            take_profit_3=Decimal(str(data['take_profit_3'])) if data.get('take_profit_3') else None,
            generated_at=generated_at,
            valid_until=valid_until,
            expected_hold_time_hours=data['expected_hold_time_hours'],
            market_context=market_context,
            pattern_details=pattern_details,
            entry_confirmation=entry_confirmation,
            contributing_factors=data['contributing_factors'],
            model_version=data.get('model_version', '1.0'),
            status=data.get('status', 'active'),
            priority=data.get('priority', 'medium')
        )
    
    def is_valid(self) -> bool:
        """Check if signal is still valid (not expired)"""
        return datetime.now() <= self.valid_until and self.status == 'active'
    
    def get_priority_score(self) -> int:
        """Get numerical priority score for sorting"""
        priority_scores = {'low': 1, 'medium': 2, 'high': 3}
        return priority_scores.get(self.priority, 2)


@dataclass
class SignalOutcome:
    """Track the outcome of a trading signal"""
    signal_id: str
    outcome_type: str  # 'win', 'loss', 'neutral', 'cancelled', 'expired'
    entry_filled: bool = False
    entry_fill_price: Optional[Decimal] = None
    entry_fill_time: Optional[datetime] = None
    exit_price: Optional[Decimal] = None
    exit_time: Optional[datetime] = None
    pnl_points: float = 0.0
    pnl_percentage: float = 0.0
    hold_duration_hours: Optional[int] = None
    target_hit: Optional[str] = None  # 'tp1', 'tp2', 'tp3', 'stop', 'manual'
    max_favorable_excursion: float = 0.0  # MFE
    max_adverse_excursion: float = 0.0   # MAE
    notes: str = ""
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert outcome to dictionary"""
        return {
            'signal_id': self.signal_id,
            'outcome_type': self.outcome_type,
            'entry_filled': self.entry_filled,
            'entry_fill_price': float(self.entry_fill_price) if self.entry_fill_price else None,
            'entry_fill_time': self.entry_fill_time.isoformat() if self.entry_fill_time else None,
            'exit_price': float(self.exit_price) if self.exit_price else None,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'pnl_points': self.pnl_points,
            'pnl_percentage': self.pnl_percentage,
            'hold_duration_hours': self.hold_duration_hours,
            'target_hit': self.target_hit,
            'max_favorable_excursion': self.max_favorable_excursion,
            'max_adverse_excursion': self.max_adverse_excursion,
            'notes': self.notes,
            'created_at': self.created_at.isoformat()
        }


# Convenience type aliases
SignalMetadata = TradingSignal  # For backward compatibility