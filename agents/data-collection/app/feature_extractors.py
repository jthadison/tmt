"""
Feature extractors for comprehensive trade data collection.

This module implements extractors that capture all 50+ features from trade events,
market conditions, signal context, execution quality, and personality impact.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime
import logging
import statistics

from .data_models import (
    TradeEvent,
    TradeDetails,
    SignalContext,
    MarketConditions,
    ExecutionQuality,
    PersonalityImpact,
    Performance,
    LearningMetadata,
    TradeDirection,
    TradeStatus,
    MarketSession,
    MarketRegime,
)


logger = logging.getLogger(__name__)


class BaseFeatureExtractor(ABC):
    """Base class for feature extractors."""
    
    @abstractmethod
    def extract(self, trade_event: TradeEvent) -> Dict[str, Any]:
        """Extract features from trade event."""
        pass
    
    def _safe_decimal(self, value: Any, default: Decimal = Decimal("0")) -> Decimal:
        """Safely convert value to Decimal."""
        try:
            if value is None:
                return default
            return Decimal(str(value))
        except (ValueError, TypeError):
            logger.warning(f"Failed to convert {value} to Decimal, using default {default}")
            return default
    
    def _safe_int(self, value: Any, default: int = 0) -> int:
        """Safely convert value to int."""
        try:
            if value is None:
                return default
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"Failed to convert {value} to int, using default {default}")
            return default


class MarketConditionExtractor(BaseFeatureExtractor):
    """Extracts market condition features (20+ features)."""
    
    def extract(self, trade_event: TradeEvent) -> Dict[str, Any]:
        """Extract market condition features."""
        market_data = trade_event.market_data
        
        # Determine market session based on time
        session = self._determine_session(trade_event.timestamp)
        
        # Determine market regime from volatility and trend indicators
        regime = self._classify_market_regime(market_data)
        
        return {
            "atr14": self._safe_decimal(market_data.get("atr_14")),
            "volatility": self._safe_decimal(market_data.get("volatility")),
            "volume": self._safe_decimal(market_data.get("volume")),
            "spread": self._safe_decimal(market_data.get("spread")),
            "liquidity": self._safe_decimal(market_data.get("liquidity")),
            "session": session,
            "day_of_week": trade_event.timestamp.weekday(),
            "hour_of_day": trade_event.timestamp.hour,
            "market_regime": regime,
            "vix_level": self._safe_decimal(market_data.get("vix")),
            "correlation_environment": self._safe_decimal(market_data.get("correlation_env")),
            "seasonality": self._calculate_seasonality(trade_event.timestamp),
            "economic_calendar_risk": self._safe_decimal(market_data.get("econ_risk")),
            "support_resistance_proximity": self._safe_decimal(market_data.get("sr_proximity")),
            "fibonacci_level": self._safe_decimal(market_data.get("fib_level")),
            "moving_average_alignment": self._safe_decimal(market_data.get("ma_alignment")),
            "rsi_level": self._safe_decimal(market_data.get("rsi")),
            "macd_signal": self._safe_decimal(market_data.get("macd_signal")),
            "bollinger_position": self._safe_decimal(market_data.get("bb_position")),
            "ichimoku_signal": self._safe_decimal(market_data.get("ichimoku")),
        }
    
    def _determine_session(self, timestamp: datetime) -> MarketSession:
        """Determine market session based on UTC time."""
        hour = timestamp.hour
        
        if 0 <= hour < 7:
            return MarketSession.ASIAN
        elif 7 <= hour < 12:
            if hour <= 9:  # London-Asian overlap
                return MarketSession.OVERLAP
            return MarketSession.LONDON
        elif 12 <= hour < 17:
            if hour <= 15:  # London-NY overlap
                return MarketSession.OVERLAP
            return MarketSession.NEWYORK
        else:
            return MarketSession.NEWYORK
    
    def _classify_market_regime(self, market_data: Dict[str, Any]) -> MarketRegime:
        """Classify market regime based on volatility and trend indicators."""
        volatility = self._safe_decimal(market_data.get("volatility"))
        atr = self._safe_decimal(market_data.get("atr_14"))
        trend_strength = self._safe_decimal(market_data.get("trend_strength", 0))
        
        # Simple regime classification logic
        if volatility > Decimal("0.8"):
            return MarketRegime.VOLATILE
        elif trend_strength > Decimal("0.6"):
            return MarketRegime.TRENDING
        elif volatility < Decimal("0.3"):
            return MarketRegime.QUIET
        else:
            return MarketRegime.RANGING
    
    def _calculate_seasonality(self, timestamp: datetime) -> Decimal:
        """Calculate seasonality factor based on time patterns."""
        # Simple seasonality based on day of week and hour
        day_factor = Decimal("1.0") - abs(timestamp.weekday() - 2) * Decimal("0.1")  # Mid-week peak
        hour_factor = Decimal("1.0") if 8 <= timestamp.hour <= 16 else Decimal("0.8")  # Trading hours
        
        return day_factor * hour_factor


class SignalContextExtractor(BaseFeatureExtractor):
    """Extracts signal generation context (15+ features)."""
    
    def extract(self, trade_event: TradeEvent) -> Dict[str, Any]:
        """Extract signal context features."""
        signal_data = trade_event.signal_data
        
        return {
            "signal_id": signal_data.get("signal_id", ""),
            "confidence": self._safe_decimal(signal_data.get("confidence")),
            "strength": self._safe_decimal(signal_data.get("strength")),
            "pattern_type": signal_data.get("pattern_type", ""),
            "pattern_subtype": signal_data.get("pattern_subtype", ""),
            "signal_source": signal_data.get("source", ""),
            "previous_signals": self._safe_int(signal_data.get("previous_signals")),
            "signal_cluster_size": self._safe_int(signal_data.get("cluster_size")),
            "cross_confirmation": bool(signal_data.get("cross_confirmation", False)),
            "divergence_present": bool(signal_data.get("divergence", False)),
            "volume_confirmation": bool(signal_data.get("volume_confirmation", False)),
            "news_event_proximity": self._safe_int(signal_data.get("news_proximity")),
            "technical_score": self._safe_decimal(signal_data.get("technical_score")),
            "fundamental_score": self._safe_decimal(signal_data.get("fundamental_score")),
            "sentiment_score": self._safe_decimal(signal_data.get("sentiment_score")),
        }


class ExecutionQualityExtractor(BaseFeatureExtractor):
    """Extracts execution quality metrics (10+ features)."""
    
    def extract(self, trade_event: TradeEvent) -> Dict[str, Any]:
        """Extract execution quality features."""
        execution_data = trade_event.execution_data
        
        # Calculate execution latency if timestamps available
        latency = 0
        placement_time = execution_data.get("order_placement_time")
        fill_time = execution_data.get("fill_time")
        
        if placement_time and fill_time:
            if isinstance(placement_time, str):
                placement_time = datetime.fromisoformat(placement_time)
            if isinstance(fill_time, str):
                fill_time = datetime.fromisoformat(fill_time)
            
            latency = int((fill_time - placement_time).total_seconds() * 1000)
        
        return {
            "order_placement_time": placement_time or trade_event.timestamp,
            "fill_time": fill_time,
            "execution_latency": latency,
            "slippage": self._safe_decimal(execution_data.get("slippage")),
            "slippage_percentage": self._safe_decimal(execution_data.get("slippage_percentage")),
            "partial_fill_count": self._safe_int(execution_data.get("partial_fills")),
            "rejection_count": self._safe_int(execution_data.get("rejections")),
            "requote_count": self._safe_int(execution_data.get("requotes")),
            "market_impact": self._safe_decimal(execution_data.get("market_impact")),
            "liquidity_at_execution": self._safe_decimal(execution_data.get("liquidity")),
            "spread_at_execution": self._safe_decimal(execution_data.get("spread")),
            "price_improvement_opportunity": self._safe_decimal(execution_data.get("price_improvement")),
        }


class PersonalityImpactExtractor(BaseFeatureExtractor):
    """Extracts personality and variance impact features."""
    
    def extract(self, trade_event: TradeEvent) -> Dict[str, Any]:
        """Extract personality impact features."""
        event_data = trade_event.event_data
        personality_data = event_data.get("personality", {})
        
        return {
            "personality_id": personality_data.get("personality_id", ""),
            "variance_applied": bool(personality_data.get("variance_applied", False)),
            "timing_variance": self._safe_decimal(personality_data.get("timing_variance")),
            "sizing_variance": self._safe_decimal(personality_data.get("sizing_variance")),
            "level_variance": self._safe_decimal(personality_data.get("level_variance")),
            "disagreement_factor": self._safe_decimal(personality_data.get("disagreement_factor")),
            "human_behavior_modifiers": personality_data.get("behavior_modifiers", []),
        }


class PerformanceCalculator(BaseFeatureExtractor):
    """Calculates performance metrics and trade outcomes."""
    
    def extract(self, trade_event: TradeEvent) -> Dict[str, Any]:
        """Calculate performance metrics."""
        event_data = trade_event.event_data
        trade_data = event_data.get("trade", {})
        
        # Extract basic trade information
        entry_price = self._safe_decimal(trade_data.get("entry_price"))
        exit_price = self._safe_decimal(trade_data.get("exit_price"))
        position_size = self._safe_decimal(trade_data.get("size"))
        
        # Calculate PnL if trade is closed
        actual_pnl = Decimal("0")
        if exit_price > 0:
            direction_multiplier = 1 if trade_data.get("direction") == "long" else -1
            actual_pnl = (exit_price - entry_price) * position_size * direction_multiplier
        
        expected_pnl = self._safe_decimal(trade_data.get("expected_pnl"))
        performance_ratio = actual_pnl / expected_pnl if expected_pnl != 0 else Decimal("0")
        
        # Determine outcome
        actual_outcome = "win" if actual_pnl > 0 else "loss" if actual_pnl < 0 else "neutral"
        
        return {
            "expected_pnl": expected_pnl,
            "actual_pnl": actual_pnl,
            "performance_ratio": performance_ratio,
            "risk_adjusted_return": self._safe_decimal(trade_data.get("risk_adjusted_return")),
            "sharpe_contribution": self._safe_decimal(trade_data.get("sharpe_contribution")),
            "max_drawdown_contribution": self._safe_decimal(trade_data.get("drawdown_contribution")),
            "win_probability": self._safe_decimal(trade_data.get("win_probability")),
            "actual_outcome": actual_outcome,
            "exit_reason": trade_data.get("exit_reason", ""),
            "holding_period_return": self._safe_decimal(trade_data.get("holding_period_return")),
        }


class LearningMetadataExtractor(BaseFeatureExtractor):
    """Extracts learning metadata and data quality indicators."""
    
    def extract(self, trade_event: TradeEvent) -> Dict[str, Any]:
        """Extract learning metadata."""
        # Basic data quality assessment
        completeness = self._assess_data_completeness(trade_event)
        
        return {
            "data_quality": completeness,
            "learning_eligible": completeness > Decimal("0.8"),
            "anomaly_score": Decimal("0"),  # Will be updated by validators
            "feature_completeness": completeness,
            "validation_errors": [],
            "learning_weight": Decimal("1.0"),
        }
    
    def _assess_data_completeness(self, trade_event: TradeEvent) -> Decimal:
        """Assess data completeness based on available fields."""
        total_fields = 0
        filled_fields = 0
        
        # Count fields in each data section
        for data_section in [trade_event.event_data, trade_event.market_data, 
                           trade_event.signal_data, trade_event.execution_data]:
            for value in data_section.values():
                total_fields += 1
                if value is not None and value != "":
                    filled_fields += 1
        
        return Decimal(str(filled_fields / total_fields)) if total_fields > 0 else Decimal("0")