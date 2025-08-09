"""
Pattern Confidence Scoring System

Implements multi-factor confidence scoring for Wyckoff patterns:
- Volume confirmation weight (30% of score)
- Price structure quality weight (25% of score)  
- Timeframe alignment weight (20% of score)
- Historical performance weight (15% of score)
- Market context weight (10% of score)

Final confidence score ranges from 0-100% with detailed factor breakdown.
"""

from typing import Dict, List, Optional, Any
from decimal import Decimal
from dataclasses import dataclass
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from enum import Enum


class MarketContext(Enum):
    """Market context classifications"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    LOW_VOLATILITY = "low_volatility"


@dataclass
class ConfidenceScore:
    """Complete confidence scoring result"""
    overall_confidence: Decimal  # 0-100 final score
    factor_scores: Dict[str, Decimal]  # Individual factor scores
    factor_weights: Dict[str, Decimal]  # Factor weights used
    pattern_type: str
    confidence_level: str  # low, medium, high, very_high
    risk_assessment: str
    recommended_action: str


class PatternConfidenceScorer:
    """Multi-factor confidence scoring for Wyckoff patterns"""
    
    def __init__(self):
        # Default factor weights (can be adjusted based on market conditions)
        self.default_weights = {
            'volume_confirmation': Decimal('0.30'),
            'price_structure': Decimal('0.25'), 
            'timeframe_alignment': Decimal('0.20'),
            'historical_performance': Decimal('0.15'),
            'market_context': Decimal('0.10')
        }
        
        # Pattern performance database (would be populated from real data)
        self.pattern_performance_db = {
            'accumulation': {'success_rate': 0.72, 'avg_profit': 0.045},
            'markup': {'success_rate': 0.68, 'avg_profit': 0.038},
            'distribution': {'success_rate': 0.74, 'avg_profit': 0.041},
            'markdown': {'success_rate': 0.69, 'avg_profit': 0.036},
            'spring': {'success_rate': 0.78, 'avg_profit': 0.052},
            'upthrust': {'success_rate': 0.76, 'avg_profit': 0.048}
        }
    
    def calculate_pattern_confidence(self,
                                   pattern_data: Dict,
                                   price_data: pd.DataFrame,
                                   volume_data: pd.Series,
                                   timeframe_data: Optional[Dict] = None,
                                   custom_weights: Optional[Dict] = None) -> ConfidenceScore:
        """
        Calculate comprehensive confidence score for a detected pattern
        
        Args:
            pattern_data: Pattern detection results with criteria
            price_data: OHLC price data
            volume_data: Volume data
            timeframe_data: Multi-timeframe analysis results
            custom_weights: Custom factor weights (optional)
        """
        weights = custom_weights if custom_weights else self.default_weights
        pattern_type = pattern_data.get('phase', 'unknown')
        
        # Calculate individual factor scores
        factor_scores = {
            'volume_confirmation': self._score_volume_confirmation(pattern_data, volume_data),
            'price_structure': self._score_price_structure_quality(pattern_data, price_data),
            'timeframe_alignment': self._score_timeframe_alignment(timeframe_data),
            'historical_performance': self._score_historical_performance(pattern_type),
            'market_context': self._score_market_context(pattern_data, price_data, volume_data)
        }
        
        # Calculate weighted overall score
        overall_score = sum(
            factor_scores[factor] * weights[factor]
            for factor in factor_scores
        )
        
        # Classify confidence level
        confidence_level = self._classify_confidence_level(overall_score)
        
        # Generate risk assessment and recommendation
        risk_assessment = self._assess_risk(overall_score, factor_scores, pattern_type)
        recommended_action = self._generate_recommendation(overall_score, factor_scores, pattern_type)
        
        return ConfidenceScore(
            overall_confidence=overall_score,
            factor_scores=factor_scores,
            factor_weights=weights,
            pattern_type=pattern_type,
            confidence_level=confidence_level,
            risk_assessment=risk_assessment,
            recommended_action=recommended_action
        )
    
    def _score_volume_confirmation(self, pattern_data: Dict, volume_data: pd.Series) -> Decimal:
        """
        Score volume confirmation (30% of total score)
        
        Evaluates:
        - Volume expansion on key moves
        - Volume divergence patterns
        - Volume at pattern completion points
        """
        if not pattern_data.get('criteria'):
            return Decimal('0')
        
        criteria = pattern_data['criteria']
        base_score = 0
        components_evaluated = 0
        
        # Check for volume-related criteria in pattern detection
        volume_criteria = [
            'volume_on_strength', 'volume_divergence', 'breakout_volume',
            'selling_pressure', 'volume_confirmation'
        ]
        
        for criterion in volume_criteria:
            if criterion in criteria:
                criterion_data = criteria[criterion]
                if isinstance(criterion_data, dict) and 'score' in criterion_data:
                    base_score += criterion_data['score']
                    components_evaluated += 1
        
        if components_evaluated == 0:
            # Fallback: analyze volume directly
            return self._analyze_volume_directly(volume_data)
        
        # Average the component scores
        volume_score = base_score / components_evaluated
        
        # Apply volume quality multipliers
        volume_multiplier = self._calculate_volume_quality_multiplier(volume_data)
        
        final_score = volume_score * volume_multiplier
        return Decimal(str(round(min(100, max(0, final_score)), 2)))
    
    def _score_price_structure_quality(self, pattern_data: Dict, price_data: pd.DataFrame) -> Decimal:
        """
        Score price structure quality (25% of total score)
        
        Evaluates:
        - Trend structure clarity
        - Support/resistance level quality  
        - Pattern formation completeness
        - Price action consistency
        """
        if not pattern_data.get('criteria'):
            return Decimal('0')
        
        criteria = pattern_data['criteria']
        pattern_type = pattern_data.get('phase', 'unknown')
        
        base_score = 0
        components_evaluated = 0
        
        # Check for structure-related criteria
        structure_criteria = [
            'price_range_contraction', 'structure_quality', 'price_structure',
            'support_holding', 'resistance_holding', 'sideways_movement'
        ]
        
        for criterion in structure_criteria:
            if criterion in criteria:
                criterion_data = criteria[criterion]
                if isinstance(criterion_data, dict) and 'score' in criterion_data:
                    base_score += criterion_data['score']
                    components_evaluated += 1
        
        if components_evaluated > 0:
            structure_score = base_score / components_evaluated
        else:
            # Fallback: analyze structure directly
            structure_score = self._analyze_price_structure_directly(price_data, pattern_type)
        
        # Apply structure quality modifiers
        structure_modifiers = self._calculate_structure_modifiers(price_data, pattern_type)
        final_score = structure_score * structure_modifiers
        
        return Decimal(str(round(min(100, max(0, final_score)), 2)))
    
    def _score_timeframe_alignment(self, timeframe_data: Optional[Dict]) -> Decimal:
        """
        Score timeframe alignment (20% of total score)
        
        Evaluates:
        - Higher timeframe trend confirmation
        - Pattern alignment across timeframes
        - Conflicting signals presence
        - Timeframe hierarchy strength
        """
        if not timeframe_data:
            return Decimal('50')  # Neutral score if no timeframe data
        
        alignment_score = timeframe_data.get('alignment_score', 50)
        conflicts = timeframe_data.get('conflicts', [])
        dominant_tf = timeframe_data.get('dominant_timeframe')
        
        # Start with base alignment score
        score = alignment_score
        
        # Penalty for conflicts
        conflict_penalty = len(conflicts) * 5  # 5 points per conflict
        score -= conflict_penalty
        
        # Bonus for strong dominant timeframe
        if dominant_tf:
            tf_hierarchy = {'1d': 20, '4h': 15, '1h': 10, '15m': 5, '5m': 2}
            score += tf_hierarchy.get(dominant_tf, 0)
        
        return Decimal(str(round(min(100, max(0, score)), 2)))
    
    def _score_historical_performance(self, pattern_type: str) -> Decimal:
        """
        Score based on historical performance (15% of total score)
        
        Evaluates:
        - Historical success rate for this pattern type
        - Average profit/loss statistics
        - Market condition performance variations
        """
        performance_data = self.pattern_performance_db.get(pattern_type)
        
        if not performance_data:
            return Decimal('40')  # Conservative score for unknown patterns
        
        success_rate = performance_data.get('success_rate', 0.5)
        avg_profit = performance_data.get('avg_profit', 0.02)
        
        # Score based on success rate (0-80 points)
        success_score = success_rate * 80
        
        # Bonus for higher average profit (0-20 points)
        profit_bonus = min(20, avg_profit * 400)  # Scale 4% profit = 16 points
        
        total_score = success_score + profit_bonus
        return Decimal(str(round(min(100, max(0, total_score)), 2)))
    
    def _score_market_context(self, pattern_data: Dict, price_data: pd.DataFrame, volume_data: pd.Series) -> Decimal:
        """
        Score market context alignment (10% of total score)
        
        Evaluates:
        - Overall market trend alignment
        - Volatility conditions
        - Market phase suitability
        - External factor considerations
        """
        pattern_type = pattern_data.get('phase', 'unknown')
        market_context = self._determine_market_context(price_data, volume_data)
        
        # Context-pattern alignment scoring
        alignment_matrix = {
            'accumulation': {
                MarketContext.RANGING: 90,
                MarketContext.LOW_VOLATILITY: 80,
                MarketContext.TRENDING_DOWN: 60,
                MarketContext.TRENDING_UP: 40,
                MarketContext.VOLATILE: 30
            },
            'markup': {
                MarketContext.TRENDING_UP: 90,
                MarketContext.VOLATILE: 70,
                MarketContext.RANGING: 50,
                MarketContext.LOW_VOLATILITY: 40,
                MarketContext.TRENDING_DOWN: 20
            },
            'distribution': {
                MarketContext.RANGING: 90,
                MarketContext.VOLATILE: 80,
                MarketContext.TRENDING_UP: 60,
                MarketContext.LOW_VOLATILITY: 50,
                MarketContext.TRENDING_DOWN: 40
            },
            'markdown': {
                MarketContext.TRENDING_DOWN: 90,
                MarketContext.VOLATILE: 70,
                MarketContext.RANGING: 50,
                MarketContext.LOW_VOLATILITY: 40,
                MarketContext.TRENDING_UP: 20
            }
        }
        
        context_score = alignment_matrix.get(pattern_type, {}).get(market_context, 50)
        return Decimal(str(round(context_score, 2)))
    
    def _analyze_volume_directly(self, volume_data: pd.Series) -> Decimal:
        """Fallback volume analysis when pattern criteria unavailable"""
        if len(volume_data) < 10:
            return Decimal('50')
        
        # Calculate volume characteristics
        recent_volume = volume_data.iloc[-5:].mean()
        avg_volume = volume_data.mean()
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
        
        # Calculate volume trend
        volume_trend = np.polyfit(range(len(volume_data)), volume_data.values, 1)[0]
        trend_score = min(50, max(-50, volume_trend * 1000))  # Scale trend
        
        base_score = 50 + trend_score  # 50 baseline + trend component
        volume_score = base_score * min(2.0, volume_ratio)  # Volume expansion factor
        
        return Decimal(str(round(min(100, max(0, volume_score)), 2)))
    
    def _analyze_price_structure_directly(self, price_data: pd.DataFrame, pattern_type: str) -> float:
        """Fallback price structure analysis"""
        if len(price_data) < 10:
            return 50
        
        # Calculate basic structure metrics
        high_low_ratio = (price_data['high'].max() - price_data['low'].min()) / price_data['close'].iloc[-1]
        volatility = price_data['close'].pct_change().std()
        
        # Pattern-specific structure scoring
        if pattern_type in ['accumulation', 'distribution']:
            # Lower volatility is better for these phases
            structure_score = max(20, 80 - (volatility * 1000))
        else:  # markup, markdown
            # Moderate volatility with clear direction is better
            structure_score = 50 + min(30, abs(high_low_ratio) * 500)
        
        return structure_score
    
    def _calculate_volume_quality_multiplier(self, volume_data: pd.Series) -> float:
        """Calculate volume quality multiplier"""
        if len(volume_data) < 5:
            return 1.0
        
        # Check volume consistency (lower standard deviation is better)
        volume_cv = volume_data.std() / volume_data.mean() if volume_data.mean() > 0 else 1
        consistency_multiplier = max(0.8, min(1.2, 2.0 - volume_cv))
        
        # Check for volume spikes (extreme values can reduce quality)
        q75 = volume_data.quantile(0.75)
        q25 = volume_data.quantile(0.25)
        outlier_ratio = (volume_data > q75 + 1.5 * (q75 - q25)).sum() / len(volume_data)
        spike_multiplier = max(0.9, 1.0 - outlier_ratio * 0.5)
        
        return consistency_multiplier * spike_multiplier
    
    def _calculate_structure_modifiers(self, price_data: pd.DataFrame, pattern_type: str) -> float:
        """Calculate price structure quality modifiers"""
        if len(price_data) < 10:
            return 1.0
        
        # Check for clean trend structure
        closes = price_data['close'].values
        trend_slope = np.polyfit(range(len(closes)), closes, 1)[0]
        
        # R-squared for trend fitness
        y_pred = np.poly1d(np.polyfit(range(len(closes)), closes, 1))(range(len(closes)))
        ss_res = np.sum((closes - y_pred) ** 2)
        ss_tot = np.sum((closes - np.mean(closes)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # Pattern-specific modifiers
        if pattern_type in ['markup', 'markdown']:
            # Strong trend with good R-squared is positive
            trend_modifier = 0.8 + (r_squared * 0.4)
        else:  # accumulation, distribution
            # Sideways movement with low R-squared is positive
            trend_modifier = 1.2 - (r_squared * 0.4)
        
        return max(0.6, min(1.4, trend_modifier))
    
    def _determine_market_context(self, price_data: pd.DataFrame, volume_data: pd.Series) -> MarketContext:
        """Determine current market context"""
        if len(price_data) < 20:
            return MarketContext.RANGING
        
        # Calculate trend
        closes = price_data['close'].values
        trend_slope = np.polyfit(range(len(closes)), closes, 1)[0]
        trend_strength = abs(trend_slope) / closes[-1] if closes[-1] != 0 else 0
        
        # Calculate volatility
        returns = price_data['close'].pct_change().dropna()
        volatility = returns.std()
        
        # Classify context
        if trend_strength > 0.0005:  # Strong trend
            if trend_slope > 0:
                return MarketContext.TRENDING_UP
            else:
                return MarketContext.TRENDING_DOWN
        elif volatility > 0.02:  # High volatility
            return MarketContext.VOLATILE
        elif volatility < 0.005:  # Low volatility
            return MarketContext.LOW_VOLATILITY
        else:
            return MarketContext.RANGING
    
    def _classify_confidence_level(self, score: Decimal) -> str:
        """Classify numerical confidence into categorical levels"""
        if score >= 80:
            return "very_high"
        elif score >= 65:
            return "high"
        elif score >= 45:
            return "medium"
        else:
            return "low"
    
    def _assess_risk(self, confidence: Decimal, factor_scores: Dict, pattern_type: str) -> str:
        """Assess risk level based on confidence and factor scores"""
        # Base risk from confidence level
        if confidence >= 75:
            risk_level = "low"
        elif confidence >= 55:
            risk_level = "medium"
        else:
            risk_level = "high"
        
        # Adjust for specific risk factors
        volume_score = factor_scores.get('volume_confirmation', Decimal('50'))
        structure_score = factor_scores.get('price_structure', Decimal('50'))
        
        # High risk if volume or structure is very weak
        if volume_score < 30 or structure_score < 30:
            risk_level = "high"
        
        # Pattern-specific risk adjustments
        historical_score = factor_scores.get('historical_performance', Decimal('50'))
        if historical_score < 40:
            if risk_level == "low":
                risk_level = "medium"
            elif risk_level == "medium":
                risk_level = "high"
        
        return risk_level
    
    def _generate_recommendation(self, confidence: Decimal, factor_scores: Dict, pattern_type: str) -> str:
        """Generate trading recommendation based on confidence analysis"""
        if confidence >= 75:
            if pattern_type in ['accumulation', 'spring']:
                return "Strong BUY signal - Enter long position"
            elif pattern_type in ['distribution', 'upthrust']:
                return "Strong SELL signal - Enter short position"
            elif pattern_type == 'markup':
                return "Continue LONG - Add to position on pullbacks"
            elif pattern_type == 'markdown':
                return "Continue SHORT - Add to position on rallies"
        elif confidence >= 55:
            if pattern_type in ['accumulation', 'spring']:
                return "Moderate BUY signal - Small long position"
            elif pattern_type in ['distribution', 'upthrust']:
                return "Moderate SELL signal - Small short position"
            else:
                return "WAIT - Monitor for pattern development"
        else:
            return "NO ACTION - Insufficient confidence for trade entry"
        
        return "MONITOR - Pattern detected but needs confirmation"
    
    def adjust_weights_for_conditions(self, market_conditions: Dict) -> Dict[str, Decimal]:
        """Adjust factor weights based on current market conditions"""
        adjusted_weights = self.default_weights.copy()
        
        # Increase volume weight in trending markets
        if market_conditions.get('trend_strength', 0) > 0.7:
            adjusted_weights['volume_confirmation'] = Decimal('0.35')
            adjusted_weights['market_context'] = Decimal('0.15')
            adjusted_weights['price_structure'] = Decimal('0.20')
        
        # Increase structure weight in ranging markets
        elif market_conditions.get('trend_strength', 0) < 0.3:
            adjusted_weights['price_structure'] = Decimal('0.30')
            adjusted_weights['volume_confirmation'] = Decimal('0.25')
            adjusted_weights['timeframe_alignment'] = Decimal('0.25')
        
        # Increase historical performance weight in uncertain conditions
        if market_conditions.get('volatility', 0) > 0.03:
            adjusted_weights['historical_performance'] = Decimal('0.20')
            adjusted_weights['volume_confirmation'] = Decimal('0.25')
        
        # Ensure weights sum to 1.0
        total_weight = sum(adjusted_weights.values())
        if total_weight != Decimal('1.0'):
            adjustment_factor = Decimal('1.0') / total_weight
            adjusted_weights = {k: v * adjustment_factor for k, v in adjusted_weights.items()}
        
        return adjusted_weights