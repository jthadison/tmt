"""
False signal analysis system.

This module implements comprehensive analysis of rejected signals and false positives
to improve signal quality and identify pattern recognition issues.
"""

from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from datetime import datetime, timedelta
import statistics
import logging
from dataclasses import dataclass, field
from collections import defaultdict

from .data_models import (
    ComprehensiveTradeRecord,
    FalseSignalAnalysis,
    RejectionInfo,
    SignalQuality,
    CounterfactualAnalysis,
    PatternImpact,
    RejectionSource,
)


logger = logging.getLogger(__name__)


@dataclass
class SignalRejectionEvent:
    """Event data for signal rejections."""
    signal_id: str
    timestamp: datetime
    rejection_reason: str
    rejection_source: RejectionSource
    rejection_score: Decimal
    alternative_action: str
    original_signal_data: Dict[str, Any]
    market_context: Dict[str, Any]
    account_context: Dict[str, Any]


class SignalRejectionLogger:
    """Logs and tracks signal rejections for analysis."""
    
    def __init__(self):
        self.rejection_events: List[SignalRejectionEvent] = []
    
    def log_rejection(
        self,
        signal_id: str,
        rejection_reason: str,
        rejection_source: RejectionSource,
        rejection_score: Decimal,
        alternative_action: str = "skip",
        signal_data: Optional[Dict[str, Any]] = None,
        market_context: Optional[Dict[str, Any]] = None,
        account_context: Optional[Dict[str, Any]] = None
    ):
        """Log a signal rejection event."""
        
        event = SignalRejectionEvent(
            signal_id=signal_id,
            timestamp=datetime.now(),
            rejection_reason=rejection_reason,
            rejection_source=rejection_source,
            rejection_score=rejection_score,
            alternative_action=alternative_action,
            original_signal_data=signal_data or {},
            market_context=market_context or {},
            account_context=account_context or {}
        )
        
        self.rejection_events.append(event)
        logger.info(f"Signal rejection logged: {signal_id} - {rejection_reason}")
    
    def get_rejections_by_timeframe(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[SignalRejectionEvent]:
        """Get rejection events within timeframe."""
        return [
            event for event in self.rejection_events
            if start_time <= event.timestamp <= end_time
        ]
    
    def get_rejections_by_source(
        self,
        source: RejectionSource
    ) -> List[SignalRejectionEvent]:
        """Get rejection events by source."""
        return [
            event for event in self.rejection_events
            if event.rejection_source == source
        ]


class RejectedSignalAnalyzer:
    """Analyzes rejected signals to identify patterns and issues."""
    
    def __init__(self):
        self.rejection_logger = SignalRejectionLogger()
    
    def analyze_rejected_signal(
        self,
        rejection_event: SignalRejectionEvent,
        market_data_at_time: Optional[Dict[str, Any]] = None
    ) -> FalseSignalAnalysis:
        """Analyze a single rejected signal."""
        
        # Create rejection info
        rejection_info = RejectionInfo(
            rejection_reason=rejection_event.rejection_reason,
            rejection_source=rejection_event.rejection_source,
            rejection_score=rejection_event.rejection_score,
            alternative_action=rejection_event.alternative_action
        )
        
        # Assess signal quality
        signal_quality = self._assess_signal_quality(rejection_event)
        
        # Perform counterfactual analysis
        counterfactual = self._perform_counterfactual_analysis(
            rejection_event,
            market_data_at_time
        )
        
        # Assess pattern impact
        pattern_impact = self._assess_pattern_impact(rejection_event)
        
        return FalseSignalAnalysis(
            rejected_signal_id=rejection_event.signal_id,
            timestamp=rejection_event.timestamp,
            rejection_info=rejection_info,
            signal_quality=signal_quality,
            counterfactual=counterfactual,
            pattern_impact=pattern_impact
        )
    
    def _assess_signal_quality(self, rejection_event: SignalRejectionEvent) -> SignalQuality:
        """Assess the quality of the rejected signal."""
        signal_data = rejection_event.original_signal_data
        
        # Extract signal quality metrics
        original_confidence = Decimal(str(signal_data.get("confidence", 0)))
        strength_score = Decimal(str(signal_data.get("strength", 0)))
        pattern_clarity = self._calculate_pattern_clarity(signal_data)
        market_support_score = self._calculate_market_support(
            signal_data,
            rejection_event.market_context
        )
        cross_validation_score = self._calculate_cross_validation_score(signal_data)
        
        return SignalQuality(
            original_confidence=original_confidence,
            strength_score=strength_score,
            pattern_clarity=pattern_clarity,
            market_support_score=market_support_score,
            cross_validation_score=cross_validation_score
        )
    
    def _calculate_pattern_clarity(self, signal_data: Dict[str, Any]) -> Decimal:
        """Calculate how clear/well-defined the pattern was."""
        # Factors that contribute to pattern clarity
        factors = []
        
        # Volume confirmation adds clarity
        if signal_data.get("volume_confirmation", False):
            factors.append(0.3)
        
        # Cross confirmation adds clarity
        if signal_data.get("cross_confirmation", False):
            factors.append(0.3)
        
        # Divergence presence can add or reduce clarity
        if signal_data.get("divergence_present", False):
            factors.append(0.2)
        
        # Pattern subtype specificity
        if signal_data.get("pattern_subtype"):
            factors.append(0.2)
        
        # Base clarity from signal strength
        strength = signal_data.get("strength", 0)
        if strength > 0.7:
            factors.append(0.4)
        elif strength > 0.5:
            factors.append(0.2)
        
        total_clarity = sum(factors)
        return Decimal(str(min(total_clarity, 1.0)))
    
    def _calculate_market_support(
        self,
        signal_data: Dict[str, Any],
        market_context: Dict[str, Any]
    ) -> Decimal:
        """Calculate how well market conditions supported the signal."""
        support_factors = []
        
        # Volatility support - signals need appropriate volatility
        volatility = market_context.get("volatility", 0.5)
        if 0.3 <= volatility <= 0.8:  # Good volatility range
            support_factors.append(0.3)
        
        # Liquidity support
        liquidity = market_context.get("liquidity", 0.5)
        if liquidity > 0.7:
            support_factors.append(0.2)
        
        # Session support - some patterns work better in certain sessions
        session = market_context.get("session", "")
        pattern_type = signal_data.get("pattern_type", "")
        if self._is_session_pattern_match(session, pattern_type):
            support_factors.append(0.2)
        
        # Economic calendar support - low risk periods are better
        econ_risk = market_context.get("economic_calendar_risk", 0.5)
        if econ_risk < 0.3:
            support_factors.append(0.3)
        
        total_support = sum(support_factors)
        return Decimal(str(min(total_support, 1.0)))
    
    def _is_session_pattern_match(self, session: str, pattern_type: str) -> bool:
        """Check if pattern type is suitable for trading session."""
        # Simplified session-pattern matching logic
        session_preferences = {
            "asian": ["accumulation", "quiet_patterns"],
            "london": ["breakout", "trend_continuation"],
            "newyork": ["reversal", "momentum"],
            "overlap": ["volatile_patterns", "quick_scalp"]
        }
        
        preferred_patterns = session_preferences.get(session, [])
        return any(pref in pattern_type.lower() for pref in preferred_patterns)
    
    def _calculate_cross_validation_score(self, signal_data: Dict[str, Any]) -> Decimal:
        """Calculate cross-validation score across different indicators."""
        validation_factors = []
        
        # Technical score validation
        tech_score = signal_data.get("technical_score", 0)
        if tech_score > 0.7:
            validation_factors.append(0.4)
        elif tech_score > 0.5:
            validation_factors.append(0.2)
        
        # Fundamental alignment
        fundamental_score = signal_data.get("fundamental_score", 0)
        if fundamental_score > 0.6:
            validation_factors.append(0.3)
        
        # Sentiment alignment
        sentiment_score = signal_data.get("sentiment_score", 0)
        if sentiment_score > 0.6:
            validation_factors.append(0.3)
        
        total_validation = sum(validation_factors)
        return Decimal(str(min(total_validation, 1.0)))
    
    def _perform_counterfactual_analysis(
        self,
        rejection_event: SignalRejectionEvent,
        market_data: Optional[Dict[str, Any]]
    ) -> CounterfactualAnalysis:
        """Perform counterfactual analysis - what if we had taken the trade?"""
        
        # This is a simplified simulation - in reality would need more sophisticated modeling
        signal_data = rejection_event.original_signal_data
        
        # Simulate trade outcome based on signal characteristics
        simulated_outcome = self._simulate_trade_outcome(signal_data, market_data)
        simulated_pnl = self._estimate_pnl(signal_data, simulated_outcome)
        
        # Determine if rejection was correct
        rejection_correctness = self._assess_rejection_correctness(
            simulated_outcome,
            simulated_pnl,
            rejection_event.rejection_reason
        )
        
        # Calculate learning value
        learning_value = self._calculate_learning_value(
            rejection_event,
            simulated_outcome,
            rejection_correctness
        )
        
        return CounterfactualAnalysis(
            simulated_outcome=simulated_outcome,
            simulated_pnl=simulated_pnl,
            rejection_correctness=rejection_correctness,
            learning_value=learning_value
        )
    
    def _simulate_trade_outcome(
        self,
        signal_data: Dict[str, Any],
        market_data: Optional[Dict[str, Any]]
    ) -> str:
        """Simulate what the trade outcome would have been."""
        
        # Simple simulation based on signal quality factors
        confidence = signal_data.get("confidence", 0.5)
        strength = signal_data.get("strength", 0.5)
        
        # Market factors
        if market_data:
            volatility = market_data.get("volatility", 0.5)
            trend_alignment = market_data.get("trend_strength", 0.5)
        else:
            volatility = 0.5
            trend_alignment = 0.5
        
        # Calculate win probability
        win_probability = (
            confidence * 0.4 +
            strength * 0.3 +
            (1 - volatility) * 0.2 +  # Lower volatility = higher win probability
            trend_alignment * 0.1
        )
        
        # Add some randomness to simulation
        import random
        random_factor = random.uniform(0.8, 1.2)
        win_probability *= random_factor
        
        if win_probability > 0.55:
            return "win"
        elif win_probability < 0.45:
            return "loss"
        else:
            return "unknown"
    
    def _estimate_pnl(self, signal_data: Dict[str, Any], outcome: str) -> Decimal:
        """Estimate what the PnL would have been."""
        
        # Base PnL estimation based on typical trade sizes
        base_pnl = Decimal("100")  # Base amount
        
        # Adjust based on signal strength
        strength = signal_data.get("strength", 0.5)
        strength_multiplier = Decimal(str(0.5 + strength))
        
        if outcome == "win":
            estimated_pnl = base_pnl * strength_multiplier
        elif outcome == "loss":
            estimated_pnl = -base_pnl * strength_multiplier * Decimal("0.7")  # Assume smaller losses
        else:
            estimated_pnl = Decimal("0")
        
        return estimated_pnl
    
    def _assess_rejection_correctness(
        self,
        simulated_outcome: str,
        simulated_pnl: Decimal,
        rejection_reason: str
    ) -> str:
        """Assess whether the rejection was correct."""
        
        # Risk management rejections
        if "risk" in rejection_reason.lower():
            if simulated_outcome == "loss":
                return "correct_rejection"
            elif simulated_outcome == "win" and simulated_pnl < Decimal("50"):
                return "correct_rejection"  # Small win not worth the risk
            else:
                return "false_positive"
        
        # Correlation rejections
        elif "correlation" in rejection_reason.lower():
            if simulated_outcome == "loss":
                return "correct_rejection"
            else:
                return "uncertain"  # Correlation rejections are more complex to assess
        
        # Personality/variance rejections
        elif "personality" in rejection_reason.lower():
            # These are for variance, so outcome doesn't determine correctness
            return "uncertain"
        
        # Manual rejections
        elif "manual" in rejection_reason.lower():
            if simulated_outcome == "win" and simulated_pnl > Decimal("100"):
                return "false_positive"
            elif simulated_outcome == "loss":
                return "correct_rejection"
            else:
                return "uncertain"
        
        else:
            return "uncertain"
    
    def _calculate_learning_value(
        self,
        rejection_event: SignalRejectionEvent,
        simulated_outcome: str,
        rejection_correctness: str
    ) -> Decimal:
        """Calculate how much this rejection event teaches us."""
        
        learning_factors = []
        
        # High-confidence signals that were rejected provide more learning value
        confidence = rejection_event.original_signal_data.get("confidence", 0.5)
        if confidence > 0.8:
            learning_factors.append(0.4)
        elif confidence > 0.6:
            learning_factors.append(0.2)
        
        # False positives provide high learning value
        if rejection_correctness == "false_positive":
            learning_factors.append(0.5)
        elif rejection_correctness == "correct_rejection":
            learning_factors.append(0.3)
        
        # Rare patterns provide more learning value
        pattern_type = rejection_event.original_signal_data.get("pattern_type", "")
        if "rare" in pattern_type or "complex" in pattern_type:
            learning_factors.append(0.3)
        
        # Edge cases provide learning value
        rejection_score = rejection_event.rejection_score
        if Decimal("0.4") <= rejection_score <= Decimal("0.6"):  # Close calls
            learning_factors.append(0.4)
        
        total_learning_value = sum(learning_factors)
        return Decimal(str(min(total_learning_value, 1.0)))
    
    def _assess_pattern_impact(self, rejection_event: SignalRejectionEvent) -> PatternImpact:
        """Assess impact of rejection on pattern recognition."""
        
        signal_data = rejection_event.original_signal_data
        pattern_type = signal_data.get("pattern_type", "")
        
        # Estimate pattern reliability (would normally be from historical data)
        pattern_reliability = self._estimate_pattern_reliability(pattern_type)
        
        # Generate suggested adjustments
        suggested_adjustment = self._generate_pattern_adjustment(
            rejection_event,
            pattern_reliability
        )
        
        # Estimate pattern frequency
        pattern_frequency = self._estimate_pattern_frequency(pattern_type)
        
        return PatternImpact(
            pattern_type=pattern_type,
            pattern_reliability=pattern_reliability,
            suggested_adjustment=suggested_adjustment,
            pattern_frequency=pattern_frequency
        )
    
    def _estimate_pattern_reliability(self, pattern_type: str) -> Decimal:
        """Estimate pattern reliability (simplified)."""
        # In reality, this would come from historical performance data
        reliability_map = {
            "wyckoff": Decimal("0.75"),
            "breakout": Decimal("0.60"),
            "reversal": Decimal("0.55"),
            "continuation": Decimal("0.70"),
            "accumulation": Decimal("0.80"),
            "distribution": Decimal("0.75"),
        }
        
        for pattern, reliability in reliability_map.items():
            if pattern in pattern_type.lower():
                return reliability
        
        return Decimal("0.60")  # Default reliability
    
    def _generate_pattern_adjustment(
        self,
        rejection_event: SignalRejectionEvent,
        pattern_reliability: Decimal
    ) -> str:
        """Generate suggested pattern adjustments."""
        
        rejection_reason = rejection_event.rejection_reason.lower()
        
        if "confidence" in rejection_reason:
            return "Increase minimum confidence threshold for this pattern"
        elif "risk" in rejection_reason:
            return "Reduce position sizing or tighten stop losses for this pattern"
        elif "correlation" in rejection_reason:
            return "Add correlation filters to pattern detection"
        elif "volatility" in rejection_reason:
            return "Adjust volatility filters for pattern activation"
        elif pattern_reliability < Decimal("0.6"):
            return "Consider removing or significantly modifying this pattern"
        else:
            return "Review pattern parameters and market context requirements"
    
    def _estimate_pattern_frequency(self, pattern_type: str) -> Decimal:
        """Estimate how frequently this pattern occurs."""
        # Simplified frequency estimation
        frequency_map = {
            "wyckoff": Decimal("0.1"),  # Rare but reliable
            "breakout": Decimal("0.3"),  # Common
            "reversal": Decimal("0.2"),  # Moderate
            "continuation": Decimal("0.4"),  # Common
            "accumulation": Decimal("0.1"),  # Rare
            "distribution": Decimal("0.1"),  # Rare
        }
        
        for pattern, frequency in frequency_map.items():
            if pattern in pattern_type.lower():
                return frequency
        
        return Decimal("0.2")  # Default frequency


class FalsePositiveDetector:
    """Detects false positive patterns in signal generation."""
    
    def __init__(self):
        self.rejection_analyzer = RejectedSignalAnalyzer()
    
    def detect_false_positive_patterns(
        self,
        rejection_analyses: List[FalseSignalAnalysis],
        min_sample_size: int = 10
    ) -> List[Dict[str, Any]]:
        """Detect patterns in false positive signals."""
        
        patterns = []
        
        # Group by rejection reason
        reason_groups = defaultdict(list)
        for analysis in rejection_analyses:
            reason_groups[analysis.rejection_info.rejection_reason].append(analysis)
        
        # Analyze each reason group
        for reason, analyses in reason_groups.items():
            if len(analyses) >= min_sample_size:
                pattern = self._analyze_reason_group(reason, analyses)
                if pattern:
                    patterns.append(pattern)
        
        return patterns
    
    def _analyze_reason_group(
        self,
        reason: str,
        analyses: List[FalseSignalAnalysis]
    ) -> Optional[Dict[str, Any]]:
        """Analyze a group of rejections with same reason."""
        
        false_positives = [
            a for a in analyses
            if a.counterfactual.rejection_correctness == "false_positive"
        ]
        
        if len(false_positives) < 3:  # Need minimum false positives
            return None
        
        false_positive_rate = len(false_positives) / len(analyses)
        
        # Extract common characteristics of false positives
        common_characteristics = self._extract_common_characteristics(false_positives)
        
        # Calculate potential improvement
        potential_improvement = self._calculate_potential_improvement(analyses, false_positives)
        
        return {
            "rejection_reason": reason,
            "total_rejections": len(analyses),
            "false_positives": len(false_positives),
            "false_positive_rate": float(false_positive_rate),
            "common_characteristics": common_characteristics,
            "potential_improvement": potential_improvement,
            "recommendation": self._generate_improvement_recommendation(
                reason, common_characteristics, potential_improvement
            )
        }
    
    def _extract_common_characteristics(
        self,
        false_positives: List[FalseSignalAnalysis]
    ) -> Dict[str, Any]:
        """Extract common characteristics of false positive signals."""
        
        characteristics = {}
        
        # Pattern types
        pattern_types = [fp.pattern_impact.pattern_type for fp in false_positives]
        characteristics["common_patterns"] = list(set(pattern_types))
        
        # Signal quality ranges
        confidences = [float(fp.signal_quality.original_confidence) for fp in false_positives]
        if confidences:
            characteristics["confidence_range"] = {
                "min": min(confidences),
                "max": max(confidences),
                "avg": statistics.mean(confidences)
            }
        
        # Time patterns
        hours = [fp.timestamp.hour for fp in false_positives]
        characteristics["common_hours"] = list(set(hours))
        
        return characteristics
    
    def _calculate_potential_improvement(
        self,
        all_analyses: List[FalseSignalAnalysis],
        false_positives: List[FalseSignalAnalysis]
    ) -> Dict[str, Any]:
        """Calculate potential improvement from fixing false positives."""
        
        # Potential PnL recovery
        potential_pnl = sum(fp.counterfactual.simulated_pnl for fp in false_positives)
        
        # Learning value
        total_learning_value = sum(fp.counterfactual.learning_value for fp in false_positives)
        
        return {
            "potential_pnl_recovery": float(potential_pnl),
            "total_learning_value": float(total_learning_value),
            "signal_improvement_opportunity": len(false_positives) / len(all_analyses)
        }
    
    def _generate_improvement_recommendation(
        self,
        reason: str,
        characteristics: Dict[str, Any],
        potential: Dict[str, Any]
    ) -> str:
        """Generate specific recommendations for improvement."""
        
        if potential["signal_improvement_opportunity"] > 0.3:  # High improvement opportunity
            if "confidence" in reason.lower():
                return f"Lower confidence threshold - avg false positive confidence is {characteristics.get('confidence_range', {}).get('avg', 0):.2f}"
            elif "risk" in reason.lower():
                return "Review risk parameters - may be too conservative for these patterns"
            elif "correlation" in reason.lower():
                return "Refine correlation filters - current settings may be rejecting profitable opportunities"
            else:
                return "High improvement opportunity - review rejection criteria"
        else:
            return "Current rejection criteria appear appropriate"


class SignalQualityScorer:
    """Scores signal quality for improvement recommendations."""
    
    def score_signal_quality(
        self,
        rejection_analyses: List[FalseSignalAnalysis]
    ) -> Dict[str, Any]:
        """Score overall signal quality and identify improvement areas."""
        
        if not rejection_analyses:
            return {"overall_score": 0, "improvement_areas": []}
        
        # Calculate component scores
        clarity_scores = [float(a.signal_quality.pattern_clarity) for a in rejection_analyses]
        market_support_scores = [float(a.signal_quality.market_support_score) for a in rejection_analyses]
        validation_scores = [float(a.signal_quality.cross_validation_score) for a in rejection_analyses]
        
        # Calculate overall quality score
        avg_clarity = statistics.mean(clarity_scores)
        avg_market_support = statistics.mean(market_support_scores)
        avg_validation = statistics.mean(validation_scores)
        
        overall_score = (avg_clarity + avg_market_support + avg_validation) / 3
        
        # Identify improvement areas
        improvement_areas = []
        if avg_clarity < 0.6:
            improvement_areas.append("pattern_clarity")
        if avg_market_support < 0.6:
            improvement_areas.append("market_context_analysis")
        if avg_validation < 0.6:
            improvement_areas.append("cross_validation")
        
        # Generate specific recommendations
        recommendations = self._generate_quality_recommendations(
            avg_clarity, avg_market_support, avg_validation
        )
        
        return {
            "overall_score": overall_score,
            "component_scores": {
                "pattern_clarity": avg_clarity,
                "market_support": avg_market_support,
                "cross_validation": avg_validation
            },
            "improvement_areas": improvement_areas,
            "recommendations": recommendations
        }
    
    def _generate_quality_recommendations(
        self,
        clarity: float,
        market_support: float,
        validation: float
    ) -> List[str]:
        """Generate specific quality improvement recommendations."""
        
        recommendations = []
        
        if clarity < 0.6:
            recommendations.append("Improve pattern recognition algorithms to increase signal clarity")
        
        if market_support < 0.6:
            recommendations.append("Enhance market context analysis and timing filters")
        
        if validation < 0.6:
            recommendations.append("Implement better cross-validation across multiple indicators")
        
        if clarity > 0.8 and market_support > 0.8 and validation < 0.6:
            recommendations.append("Focus on cross-indicator validation - patterns and market context are good")
        
        if not recommendations:
            recommendations.append("Signal quality is generally good - focus on fine-tuning")
        
        return recommendations