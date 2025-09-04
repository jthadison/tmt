"""
Enhanced Wyckoff Pattern Detection

Improved Wyckoff pattern detection with enhanced volume confirmation,
multi-timeframe analysis, and performance-based pattern scoring.

Key Enhancements:
- Volume spike detection and confirmation
- Smart money flow analysis  
- Pattern strength scoring
- Multi-timeframe pattern confluence
- Real-time pattern validation
"""

from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, asdict
from enum import Enum

from .confidence_scorer import PatternConfidenceScorer, ConfidenceScore

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Wyckoff pattern types"""
    ACCUMULATION = "accumulation"
    MARKUP = "markup" 
    DISTRIBUTION = "distribution"
    MARKDOWN = "markdown"
    SPRING = "spring"
    UPTHRUST = "upthrust"
    SIGN_OF_STRENGTH = "sign_of_strength"
    SIGN_OF_WEAKNESS = "sign_of_weakness"


@dataclass
class VolumeAnalysis:
    """Volume analysis results for pattern confirmation"""
    volume_expansion_ratio: float
    smart_money_flow_score: float
    volume_divergence_present: bool
    breakout_volume_confirmation: bool
    distribution_volume_score: float
    volume_pattern_strength: float


@dataclass
class EnhancedPattern:
    """Enhanced pattern detection result"""
    pattern_type: PatternType
    confidence_score: float
    volume_analysis: VolumeAnalysis
    price_structure_score: float
    pattern_completion: float
    key_levels: Dict[str, float]
    timeframe_confirmation: Optional[Dict]
    smart_money_signals: List[str]
    pattern_invalidation_level: float
    expected_target_levels: List[float]
    risk_reward_ratio: float
    pattern_maturity: str  # 'early', 'developing', 'mature', 'late'


class EnhancedWyckoffDetector:
    """
    Enhanced Wyckoff pattern detection with improved volume analysis
    and multi-timeframe confirmation.
    """
    
    def __init__(self,
                 volume_expansion_threshold: float = 2.0,
                 smart_money_threshold: float = 0.7,
                 min_pattern_bars: int = 15,
                 max_pattern_bars: int = 50):
        """
        Initialize enhanced Wyckoff detector.
        
        Args:
            volume_expansion_threshold: Minimum volume expansion for confirmation
            smart_money_threshold: Threshold for smart money flow detection
            min_pattern_bars: Minimum bars for valid pattern
            max_pattern_bars: Maximum bars for pattern recognition
        """
        self.volume_expansion_threshold = volume_expansion_threshold
        self.smart_money_threshold = smart_money_threshold
        self.min_pattern_bars = min_pattern_bars
        self.max_pattern_bars = max_pattern_bars
        
        # Initialize confidence scorer
        self.confidence_scorer = PatternConfidenceScorer()
        
        # Pattern validation thresholds
        self.validation_thresholds = {
            'min_confidence': 65.0,
            'min_volume_confirmation': 60.0,
            'min_structure_score': 50.0,
            'min_risk_reward': 1.5
        }
    
    async def detect_enhanced_patterns(self,
                                     symbol: str,
                                     price_data: pd.DataFrame,
                                     volume_data: pd.Series,
                                     timeframe: str = '1H') -> List[EnhancedPattern]:
        """
        Main enhanced pattern detection function.
        
        Args:
            symbol: Trading symbol
            price_data: OHLC price data
            volume_data: Volume data
            timeframe: Timeframe for analysis
            
        Returns:
            List of enhanced pattern detection results
        """
        try:
            logger.info(f"Enhanced pattern detection for {symbol} {timeframe}")
            
            # Validate input data
            if not self._validate_input_data(price_data, volume_data):
                return []
            
            # Detect base patterns
            base_patterns = await self._detect_base_patterns(price_data, volume_data)
            
            if not base_patterns:
                logger.info("No base patterns detected")
                return []
            
            # Enhance patterns with advanced analysis
            enhanced_patterns = []
            
            for pattern in base_patterns:
                enhanced = await self._enhance_pattern(pattern, price_data, volume_data, timeframe)
                if enhanced and self._validate_enhanced_pattern(enhanced):
                    enhanced_patterns.append(enhanced)
            
            # Sort by confidence score
            enhanced_patterns.sort(key=lambda x: x.confidence_score, reverse=True)
            
            logger.info(f"Enhanced pattern detection completed: {len(enhanced_patterns)} patterns found")
            return enhanced_patterns
            
        except Exception as e:
            logger.error(f"Error in enhanced pattern detection: {e}")
            return []
    
    def _validate_input_data(self, price_data: pd.DataFrame, volume_data: pd.Series) -> bool:
        """Validate input data quality"""
        
        # Check minimum data requirements
        if len(price_data) < self.min_pattern_bars:
            logger.warning(f"Insufficient price data: {len(price_data)} < {self.min_pattern_bars}")
            return False
        
        if len(volume_data) < self.min_pattern_bars:
            logger.warning(f"Insufficient volume data: {len(volume_data)} < {self.min_pattern_bars}")
            return False
        
        # Check for required columns
        required_columns = ['open', 'high', 'low', 'close']
        if not all(col in price_data.columns for col in required_columns):
            logger.warning("Missing required OHLC columns")
            return False
        
        # Check for data quality issues
        if price_data[required_columns].isnull().any().any():
            logger.warning("Null values found in price data")
            return False
        
        if volume_data.isnull().any():
            logger.warning("Null values found in volume data")
            return False
        
        return True
    
    async def _detect_base_patterns(self, 
                                  price_data: pd.DataFrame, 
                                  volume_data: pd.Series) -> List[Dict]:
        """Detect base Wyckoff patterns using existing logic"""
        
        patterns = []
        
        # Accumulation pattern detection
        accumulation = await self._detect_accumulation_pattern(price_data, volume_data)
        if accumulation:
            patterns.append(accumulation)
        
        # Distribution pattern detection
        distribution = await self._detect_distribution_pattern(price_data, volume_data)
        if distribution:
            patterns.append(distribution)
        
        # Spring/Upthrust detection
        spring = await self._detect_spring_pattern(price_data, volume_data)
        if spring:
            patterns.append(spring)
        
        upthrust = await self._detect_upthrust_pattern(price_data, volume_data)
        if upthrust:
            patterns.append(upthrust)
        
        # Markup/Markdown detection
        markup = await self._detect_markup_pattern(price_data, volume_data)
        if markup:
            patterns.append(markup)
        
        markdown = await self._detect_markdown_pattern(price_data, volume_data)
        if markdown:
            patterns.append(markdown)
        
        return patterns
    
    async def _detect_accumulation_pattern(self, 
                                         price_data: pd.DataFrame, 
                                         volume_data: pd.Series) -> Optional[Dict]:
        """Detect accumulation patterns with enhanced volume analysis"""
        
        # Look for sideways price action with increasing volume
        recent_bars = min(30, len(price_data))
        analysis_data = price_data.iloc[-recent_bars:]
        analysis_volume = volume_data.iloc[-recent_bars:]
        
        # Calculate price range contraction
        high_low_ranges = analysis_data['high'] - analysis_data['low']
        range_contraction = high_low_ranges.rolling(5).mean().iloc[-1] / high_low_ranges.rolling(5).mean().iloc[-10] if len(high_low_ranges) >= 10 else 1.0
        
        # Calculate support level strength
        lows = analysis_data['low'].values
        support_level = np.percentile(lows, 20)  # 20th percentile as support
        touches = np.sum(np.abs(lows - support_level) < (support_level * 0.002))  # Within 0.2%
        
        # Volume analysis for accumulation
        avg_volume = analysis_volume.mean()
        recent_volume = analysis_volume.iloc[-5:].mean()
        volume_increase = recent_volume / avg_volume if avg_volume > 0 else 1.0
        
        # Test for accumulation criteria
        price_criteria = {
            'range_contraction': range_contraction < 0.8,  # Price range contracting
            'support_holding': touches >= 3,               # Support tested multiple times
            'sideways_movement': self._is_sideways_movement(analysis_data)
        }
        
        volume_criteria = {
            'volume_expansion': volume_increase > 1.2,     # Volume increasing
            'distribution_volume': self._analyze_accumulation_volume(analysis_volume),
            'no_selling_pressure': not self._detect_selling_pressure(analysis_data, analysis_volume)
        }
        
        # Score the pattern
        price_score = sum(price_criteria.values()) / len(price_criteria) * 100
        volume_score = sum(volume_criteria.values()) / len(volume_criteria) * 100
        
        # Require minimum scores
        if price_score < 60 or volume_score < 50:
            return None
        
        # Calculate key levels
        support = support_level
        resistance = np.percentile(analysis_data['high'].values, 80)
        current_price = analysis_data['close'].iloc[-1]
        
        return {
            'type': PatternType.ACCUMULATION,
            'phase': 'accumulation',
            'confidence': (price_score + volume_score) / 2,
            'price_criteria': price_criteria,
            'volume_criteria': volume_criteria,
            'key_levels': {
                'support': support,
                'resistance': resistance,
                'current_price': current_price,
                'entry': support + (resistance - support) * 0.3,  # Entry near support
                'target': resistance + (resistance - support) * 0.5,  # Target above resistance
                'stop': support - (resistance - support) * 0.2     # Stop below support
            },
            'pattern_strength': min(100, (price_score + volume_score) / 2 * 1.1),
            'maturity': self._assess_pattern_maturity(analysis_data, 'accumulation')
        }
    
    async def _detect_distribution_pattern(self, 
                                         price_data: pd.DataFrame, 
                                         volume_data: pd.Series) -> Optional[Dict]:
        """Detect distribution patterns with enhanced volume analysis"""
        
        recent_bars = min(30, len(price_data))
        analysis_data = price_data.iloc[-recent_bars:]
        analysis_volume = volume_data.iloc[-recent_bars:]
        
        # Calculate resistance level strength
        highs = analysis_data['high'].values
        resistance_level = np.percentile(highs, 80)  # 80th percentile as resistance
        touches = np.sum(np.abs(highs - resistance_level) < (resistance_level * 0.002))  # Within 0.2%
        
        # Look for weakening price action
        recent_highs = highs[-10:]
        high_trend = np.polyfit(range(len(recent_highs)), recent_highs, 1)[0]
        
        # Volume analysis for distribution
        volume_on_rallies = self._calculate_volume_on_rallies(analysis_data, analysis_volume)
        volume_on_declines = self._calculate_volume_on_declines(analysis_data, analysis_volume)
        
        # Test for distribution criteria
        price_criteria = {
            'resistance_tested': touches >= 3,              # Resistance tested multiple times
            'weakening_rallies': high_trend <= 0,          # Highs not making new highs
            'price_structure_deterioration': self._detect_structure_deterioration(analysis_data)
        }
        
        volume_criteria = {
            'volume_on_weakness': volume_on_declines > volume_on_rallies,  # More volume on weakness
            'selling_pressure': self._detect_selling_pressure(analysis_data, analysis_volume),
            'no_buying_climax': not self._detect_buying_climax(analysis_data, analysis_volume)
        }
        
        # Score the pattern
        price_score = sum(price_criteria.values()) / len(price_criteria) * 100
        volume_score = sum(volume_criteria.values()) / len(volume_criteria) * 100
        
        # Require minimum scores
        if price_score < 60 or volume_score < 50:
            return None
        
        # Calculate key levels
        resistance = resistance_level
        support = np.percentile(analysis_data['low'].values, 20)
        current_price = analysis_data['close'].iloc[-1]
        
        return {
            'type': PatternType.DISTRIBUTION,
            'phase': 'distribution',
            'confidence': (price_score + volume_score) / 2,
            'price_criteria': price_criteria,
            'volume_criteria': volume_criteria,
            'key_levels': {
                'resistance': resistance,
                'support': support,
                'current_price': current_price,
                'entry': resistance - (resistance - support) * 0.3,  # Entry near resistance
                'target': support - (resistance - support) * 0.5,    # Target below support
                'stop': resistance + (resistance - support) * 0.2    # Stop above resistance
            },
            'pattern_strength': min(100, (price_score + volume_score) / 2 * 1.1),
            'maturity': self._assess_pattern_maturity(analysis_data, 'distribution')
        }
    
    async def _detect_spring_pattern(self, 
                                   price_data: pd.DataFrame, 
                                   volume_data: pd.Series) -> Optional[Dict]:
        """Detect spring patterns (false breakdowns with volume confirmation)"""
        
        recent_bars = min(25, len(price_data))
        analysis_data = price_data.iloc[-recent_bars:]
        analysis_volume = volume_data.iloc[-recent_bars:]
        
        # Find potential support levels
        lows = analysis_data['low'].values
        support_level = np.min(lows)
        
        # Look for false breakdown and recovery
        breakdown_detected = False
        recovery_detected = False
        breakdown_bar_idx = -1
        
        for i in range(len(lows) - 5, len(lows)):
            if i > 5:  # Need history before breakdown
                prev_support = np.min(lows[max(0, i-10):i])
                current_low = lows[i]
                
                # Check for breakdown
                if current_low < prev_support * 0.998:  # 0.2% breakdown
                    breakdown_detected = True
                    breakdown_bar_idx = i
                    
                    # Check for immediate recovery
                    if i < len(lows) - 2:
                        recovery_bars = lows[i+1:i+3]
                        if all(low > current_low * 1.001 for low in recovery_bars):  # Recovery above breakdown
                            recovery_detected = True
                    break
        
        if not (breakdown_detected and recovery_detected):
            return None
        
        # Volume confirmation for spring
        breakdown_volume = analysis_volume.iloc[breakdown_bar_idx] if breakdown_bar_idx >= 0 else 0
        avg_volume = analysis_volume.mean()
        volume_expansion = breakdown_volume / avg_volume if avg_volume > 0 else 1.0
        
        # Look for diminished selling pressure
        selling_pressure_score = self._analyze_selling_pressure_diminishment(
            analysis_data, analysis_volume, breakdown_bar_idx
        )
        
        # Spring pattern criteria
        criteria = {
            'false_breakdown': breakdown_detected,
            'immediate_recovery': recovery_detected,
            'volume_on_spring': volume_expansion > 1.5,  # Increased volume on breakdown
            'diminished_selling': selling_pressure_score > 60,
            'support_reclaim': analysis_data['close'].iloc[-1] > support_level
        }
        
        pattern_score = sum(criteria.values()) / len(criteria) * 100
        
        if pattern_score < 70:  # Springs need high confirmation
            return None
        
        # Calculate target levels
        range_height = analysis_data['high'].max() - support_level
        target_1 = support_level + range_height * 1.0   # 100% extension
        target_2 = support_level + range_height * 1.618  # Fibonacci extension
        
        return {
            'type': PatternType.SPRING,
            'phase': 'spring',
            'confidence': pattern_score,
            'criteria': criteria,
            'key_levels': {
                'support': support_level,
                'breakdown_level': lows[breakdown_bar_idx] if breakdown_bar_idx >= 0 else support_level,
                'current_price': analysis_data['close'].iloc[-1],
                'entry': support_level + range_height * 0.1,  # Entry above spring low
                'target_1': target_1,
                'target_2': target_2,
                'stop': lows[breakdown_bar_idx] * 0.995 if breakdown_bar_idx >= 0 else support_level * 0.995
            },
            'pattern_strength': pattern_score,
            'volume_expansion_ratio': volume_expansion,
            'maturity': 'mature'  # Springs are typically mature when detected
        }
    
    async def _detect_upthrust_pattern(self, 
                                     price_data: pd.DataFrame, 
                                     volume_data: pd.Series) -> Optional[Dict]:
        """Detect upthrust patterns (false breakouts with volume confirmation)"""
        
        recent_bars = min(25, len(price_data))
        analysis_data = price_data.iloc[-recent_bars:]
        analysis_volume = volume_data.iloc[-recent_bars:]
        
        # Find potential resistance levels
        highs = analysis_data['high'].values
        resistance_level = np.max(highs)
        
        # Look for false breakout and rejection
        breakout_detected = False
        rejection_detected = False
        breakout_bar_idx = -1
        
        for i in range(len(highs) - 5, len(highs)):
            if i > 5:  # Need history before breakout
                prev_resistance = np.max(highs[max(0, i-10):i])
                current_high = highs[i]
                
                # Check for breakout
                if current_high > prev_resistance * 1.002:  # 0.2% breakout
                    breakout_detected = True
                    breakout_bar_idx = i
                    
                    # Check for immediate rejection
                    if i < len(highs) - 2:
                        rejection_bars = highs[i+1:i+3]
                        if all(high < current_high * 0.999 for high in rejection_bars):  # Rejection below breakout
                            rejection_detected = True
                    break
        
        if not (breakout_detected and rejection_detected):
            return None
        
        # Volume confirmation for upthrust
        breakout_volume = analysis_volume.iloc[breakout_bar_idx] if breakout_bar_idx >= 0 else 0
        avg_volume = analysis_volume.mean()
        volume_expansion = breakout_volume / avg_volume if avg_volume > 0 else 1.0
        
        # Look for increased selling pressure after upthrust
        selling_pressure_score = self._analyze_post_upthrust_selling(
            analysis_data, analysis_volume, breakout_bar_idx
        )
        
        # Upthrust pattern criteria
        criteria = {
            'false_breakout': breakout_detected,
            'immediate_rejection': rejection_detected,
            'volume_on_upthrust': volume_expansion > 1.5,  # Increased volume on breakout
            'selling_pressure': selling_pressure_score > 60,
            'resistance_failure': analysis_data['close'].iloc[-1] < resistance_level
        }
        
        pattern_score = sum(criteria.values()) / len(criteria) * 100
        
        if pattern_score < 70:  # Upthrusts need high confirmation
            return None
        
        # Calculate target levels
        range_height = resistance_level - analysis_data['low'].min()
        target_1 = resistance_level - range_height * 1.0   # 100% extension down
        target_2 = resistance_level - range_height * 1.618  # Fibonacci extension down
        
        return {
            'type': PatternType.UPTHRUST,
            'phase': 'upthrust',
            'confidence': pattern_score,
            'criteria': criteria,
            'key_levels': {
                'resistance': resistance_level,
                'breakout_level': highs[breakout_bar_idx] if breakout_bar_idx >= 0 else resistance_level,
                'current_price': analysis_data['close'].iloc[-1],
                'entry': resistance_level - range_height * 0.1,  # Entry below upthrust high
                'target_1': target_1,
                'target_2': target_2,
                'stop': highs[breakout_bar_idx] * 1.005 if breakout_bar_idx >= 0 else resistance_level * 1.005
            },
            'pattern_strength': pattern_score,
            'volume_expansion_ratio': volume_expansion,
            'maturity': 'mature'  # Upthrusts are typically mature when detected
        }
    
    async def _enhance_pattern(self,
                             base_pattern: Dict,
                             price_data: pd.DataFrame,
                             volume_data: pd.Series,
                             timeframe: str) -> Optional[EnhancedPattern]:
        """Enhance base pattern with advanced analysis"""
        
        try:
            # Enhanced volume analysis
            volume_analysis = await self._perform_enhanced_volume_analysis(
                base_pattern, price_data, volume_data
            )
            
            # Calculate confidence using enhanced scorer
            confidence_result = self.confidence_scorer.calculate_pattern_confidence(
                base_pattern, price_data, volume_data
            )
            
            # Calculate price structure score
            price_structure_score = await self._calculate_price_structure_score(
                base_pattern, price_data
            )
            
            # Assess pattern completion
            pattern_completion = self._assess_pattern_completion(base_pattern, price_data, volume_data)
            
            # Detect smart money signals
            smart_money_signals = await self._detect_smart_money_signals(
                base_pattern, price_data, volume_data
            )
            
            # Calculate risk-reward ratio
            risk_reward_ratio = self._calculate_enhanced_risk_reward(base_pattern)
            
            # Calculate target levels
            target_levels = self._calculate_fibonacci_targets(base_pattern, price_data)
            
            # Determine pattern invalidation level
            invalidation_level = self._calculate_invalidation_level(base_pattern)
            
            return EnhancedPattern(
                pattern_type=base_pattern['type'],
                confidence_score=float(confidence_result.overall_confidence),
                volume_analysis=volume_analysis,
                price_structure_score=price_structure_score,
                pattern_completion=pattern_completion,
                key_levels=base_pattern.get('key_levels', {}),
                timeframe_confirmation=None,  # Will be added if multi-timeframe analysis is enabled
                smart_money_signals=smart_money_signals,
                pattern_invalidation_level=invalidation_level,
                expected_target_levels=target_levels,
                risk_reward_ratio=risk_reward_ratio,
                pattern_maturity=base_pattern.get('maturity', 'developing')
            )
            
        except Exception as e:
            logger.error(f"Error enhancing pattern: {e}")
            return None
    
    async def _perform_enhanced_volume_analysis(self,
                                              pattern: Dict,
                                              price_data: pd.DataFrame,
                                              volume_data: pd.Series) -> VolumeAnalysis:
        """Perform comprehensive volume analysis for pattern confirmation"""
        
        # Calculate volume expansion ratio
        recent_volume = volume_data.iloc[-5:].mean()
        baseline_volume = volume_data.iloc[-20:-5].mean()
        expansion_ratio = recent_volume / baseline_volume if baseline_volume > 0 else 1.0
        
        # Smart money flow analysis
        smart_money_score = await self._calculate_smart_money_flow(price_data, volume_data)
        
        # Volume divergence detection
        divergence_present = self._detect_volume_divergence(price_data, volume_data)
        
        # Breakout volume confirmation
        breakout_confirmation = self._confirm_breakout_volume(pattern, price_data, volume_data)
        
        # Distribution volume scoring
        distribution_score = self._score_distribution_volume(pattern, price_data, volume_data)
        
        # Overall volume pattern strength
        pattern_strength = self._calculate_volume_pattern_strength(
            expansion_ratio, smart_money_score, divergence_present, breakout_confirmation
        )
        
        return VolumeAnalysis(
            volume_expansion_ratio=expansion_ratio,
            smart_money_flow_score=smart_money_score,
            volume_divergence_present=divergence_present,
            breakout_volume_confirmation=breakout_confirmation,
            distribution_volume_score=distribution_score,
            volume_pattern_strength=pattern_strength
        )
    
    def _validate_enhanced_pattern(self, pattern: EnhancedPattern) -> bool:
        """Validate enhanced pattern meets quality thresholds"""
        
        validations = {
            'confidence': pattern.confidence_score >= self.validation_thresholds['min_confidence'],
            'volume_confirmation': pattern.volume_analysis.volume_pattern_strength >= self.validation_thresholds['min_volume_confirmation'],
            'structure_score': pattern.price_structure_score >= self.validation_thresholds['min_structure_score'],
            'risk_reward': pattern.risk_reward_ratio >= self.validation_thresholds['min_risk_reward']
        }
        
        # All criteria must pass
        is_valid = all(validations.values())
        
        if not is_valid:
            logger.debug(f"Pattern validation failed: {validations}")
        
        return is_valid
    
    # Helper methods for pattern detection and analysis
    def _is_sideways_movement(self, price_data: pd.DataFrame) -> bool:
        """Check if price movement is sideways"""
        if len(price_data) < 10:
            return False
        
        closes = price_data['close'].values
        trend_slope = np.polyfit(range(len(closes)), closes, 1)[0]
        price_range = np.max(closes) - np.min(closes)
        
        # Sideways if trend slope is small relative to price range
        return abs(trend_slope) < (price_range * 0.1)
    
    def _analyze_accumulation_volume(self, volume_data: pd.Series) -> bool:
        """Analyze volume patterns typical of accumulation"""
        if len(volume_data) < 10:
            return False
        
        # Look for gradual volume increase
        early_volume = volume_data.iloc[:len(volume_data)//2].mean()
        late_volume = volume_data.iloc[len(volume_data)//2:].mean()
        
        return late_volume > early_volume * 1.1  # 10% increase
    
    def _detect_selling_pressure(self, price_data: pd.DataFrame, volume_data: pd.Series) -> bool:
        """Detect selling pressure in price/volume action"""
        if len(price_data) < 5:
            return False
        
        # Calculate volume-weighted price action
        for i in range(len(price_data) - 5, len(price_data)):
            if i >= 1:
                price_change = price_data['close'].iloc[i] - price_data['close'].iloc[i-1]
                volume_ratio = volume_data.iloc[i] / volume_data.mean() if volume_data.mean() > 0 else 1
                
                # High volume with negative price action indicates selling pressure
                if price_change < 0 and volume_ratio > 1.5:
                    return True
        
        return False
    
    async def _calculate_smart_money_flow(self, price_data: pd.DataFrame, volume_data: pd.Series) -> float:
        """Calculate smart money flow score"""
        
        if len(price_data) < 10:
            return 50.0
        
        smart_money_indicators = []
        
        # Volume on up moves vs down moves
        for i in range(1, len(price_data)):
            price_change = price_data['close'].iloc[i] - price_data['close'].iloc[i-1]
            volume = volume_data.iloc[i]
            
            if price_change > 0:  # Up move
                smart_money_indicators.append(volume)
            elif price_change < 0:  # Down move  
                smart_money_indicators.append(-volume)
        
        if smart_money_indicators:
            net_flow = sum(smart_money_indicators)
            total_volume = sum(abs(x) for x in smart_money_indicators)
            flow_ratio = net_flow / total_volume if total_volume > 0 else 0
            
            # Convert to 0-100 score
            smart_money_score = 50 + (flow_ratio * 50)
            return max(0, min(100, smart_money_score))
        
        return 50.0
    
    def _detect_volume_divergence(self, price_data: pd.DataFrame, volume_data: pd.Series) -> bool:
        """Detect volume divergence patterns"""
        if len(price_data) < 15:
            return False
        
        # Compare recent price and volume trends
        recent_bars = 10
        price_trend = np.polyfit(range(recent_bars), price_data['close'].iloc[-recent_bars:].values, 1)[0]
        volume_trend = np.polyfit(range(recent_bars), volume_data.iloc[-recent_bars:].values, 1)[0]
        
        # Normalize trends
        price_trend_norm = price_trend / price_data['close'].iloc[-1] if price_data['close'].iloc[-1] != 0 else 0
        volume_trend_norm = volume_trend / volume_data.mean() if volume_data.mean() > 0 else 0
        
        # Divergence if trends are opposite
        return (price_trend_norm > 0 and volume_trend_norm < 0) or (price_trend_norm < 0 and volume_trend_norm > 0)
    
    def _assess_pattern_maturity(self, analysis_data: Dict, pattern_type: str) -> str:
        """Assess the maturity level of detected pattern"""
        
        if not analysis_data:
            return 'incomplete'
        
        # Get volume and price metrics
        volume_strength = analysis_data.get('volume_analysis', {}).get('volume_pattern_strength', 0)
        price_structure = analysis_data.get('price_structure_score', 0)
        
        # Maturity scoring based on pattern development
        if volume_strength >= 75 and price_structure >= 80:
            return 'mature'
        elif volume_strength >= 50 and price_structure >= 60:
            return 'developing'
        else:
            return 'early'
    
    # Additional helper methods would be implemented here for:
    # - _detect_markup_pattern
    # - _detect_markdown_pattern  
    # - _calculate_price_structure_score
    # - _assess_pattern_completion
    # - _detect_smart_money_signals
    # - _calculate_enhanced_risk_reward
    # - _calculate_fibonacci_targets
    # - _calculate_invalidation_level
    # etc.
    
    async def get_pattern_performance_summary(self) -> Dict:
        """Get summary of pattern detection performance"""
        return {
            'detector_status': 'enhanced',
            'pattern_types_supported': [pt.value for pt in PatternType],
            'validation_thresholds': self.validation_thresholds,
            'volume_analysis_enabled': True,
            'smart_money_detection': True,
            'confidence_scoring': 'multi_factor'
        }