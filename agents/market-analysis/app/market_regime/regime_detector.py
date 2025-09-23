"""
Market Regime Detection for Trading System Optimization
=======================================================
Detects market conditions to filter trading signals and improve win rates.

CYCLE 3: Multi-timeframe precision with regime filtering
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    """Market regime classifications"""
    TRENDING_BULLISH = "trending_bullish"
    TRENDING_BEARISH = "trending_bearish"
    CONSOLIDATING = "consolidating"
    VOLATILE_CHOPPY = "volatile_choppy"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT_PENDING = "breakout_pending"

@dataclass
class RegimeAnalysis:
    """Market regime analysis results"""
    regime: MarketRegime
    confidence: float
    trend_strength: float
    volatility_level: float
    volume_quality: float
    trading_favorability: float  # 0-100 score for trading conditions

    # Specific metrics
    atr_normalized: float
    rsi_regime: float
    volume_trend: float
    price_momentum: float

    # Multi-timeframe alignment
    timeframe_alignment: float

    # Recommendations
    should_trade: bool
    recommended_position_size_multiplier: float

class MarketRegimeDetector:
    """
    Advanced market regime detection for signal filtering.

    CYCLE 3 Features:
    - Multi-timeframe regime analysis
    - Volume quality assessment
    - Trend strength measurement
    - Trading favorability scoring
    """

    def __init__(self,
                 lookback_period: int = 50,
                 volatility_threshold: float = 0.8,
                 trend_threshold: float = 0.6):
        """
        Initialize regime detector.

        Args:
            lookback_period: Bars to analyze for regime detection
            volatility_threshold: Minimum volatility for trading
            trend_threshold: Minimum trend strength for directional trades
        """
        self.lookback_period = lookback_period
        self.volatility_threshold = volatility_threshold
        self.trend_threshold = trend_threshold

        logger.info(f"Initialized Market Regime Detector with {lookback_period} bar lookback")

    def detect_regime(self,
                     price_data: pd.DataFrame,
                     volume_data: pd.Series,
                     timeframe: str = "1H") -> RegimeAnalysis:
        """
        Detect current market regime.

        Args:
            price_data: OHLC price data
            volume_data: Volume series
            timeframe: Chart timeframe

        Returns:
            RegimeAnalysis with complete regime assessment
        """
        try:
            # Calculate technical indicators
            indicators = self._calculate_indicators(price_data, volume_data)

            # Assess trend strength
            trend_strength = self._calculate_trend_strength(price_data, indicators)

            # Measure volatility
            volatility_level = self._calculate_volatility_level(price_data, indicators)

            # Analyze volume quality
            volume_quality = self._analyze_volume_quality(price_data, volume_data, indicators)

            # Determine regime
            regime = self._classify_regime(trend_strength, volatility_level, volume_quality, indicators)

            # Calculate confidence
            confidence = self._calculate_regime_confidence(regime, indicators, trend_strength, volatility_level)

            # Assess trading favorability
            trading_favorability = self._calculate_trading_favorability(
                regime, trend_strength, volatility_level, volume_quality
            )

            # Multi-timeframe alignment (simplified for this cycle)
            timeframe_alignment = self._calculate_timeframe_alignment(indicators)

            # Trading recommendations
            should_trade, position_multiplier = self._generate_trading_recommendations(
                regime, confidence, trading_favorability, trend_strength
            )

            return RegimeAnalysis(
                regime=regime,
                confidence=confidence,
                trend_strength=trend_strength,
                volatility_level=volatility_level,
                volume_quality=volume_quality,
                trading_favorability=trading_favorability,
                atr_normalized=indicators.get('atr_normalized', 0.0),
                rsi_regime=indicators.get('rsi', 50.0),
                volume_trend=indicators.get('volume_trend', 0.0),
                price_momentum=indicators.get('momentum', 0.0),
                timeframe_alignment=timeframe_alignment,
                should_trade=should_trade,
                recommended_position_size_multiplier=position_multiplier
            )

        except Exception as e:
            logger.error(f"Regime detection failed: {e}")

            # Return conservative default
            return RegimeAnalysis(
                regime=MarketRegime.CONSOLIDATING,
                confidence=0.3,
                trend_strength=0.4,
                volatility_level=0.5,
                volume_quality=0.4,
                trading_favorability=25.0,
                atr_normalized=1.0,
                rsi_regime=50.0,
                volume_trend=0.0,
                price_momentum=0.0,
                timeframe_alignment=50.0,
                should_trade=False,
                recommended_position_size_multiplier=0.5
            )

    def _calculate_indicators(self, price_data: pd.DataFrame, volume_data: pd.Series) -> Dict:
        """Calculate technical indicators for regime analysis"""
        indicators = {}

        # Price-based indicators
        indicators['sma_20'] = price_data['close'].rolling(20).mean()
        indicators['sma_50'] = price_data['close'].rolling(50).mean()
        indicators['ema_12'] = price_data['close'].ewm(span=12).mean()
        indicators['ema_26'] = price_data['close'].ewm(span=26).mean()

        # ATR for volatility
        high_low = price_data['high'] - price_data['low']
        high_close_prev = np.abs(price_data['high'] - price_data['close'].shift(1))
        low_close_prev = np.abs(price_data['low'] - price_data['close'].shift(1))
        true_range = np.maximum(high_low, np.maximum(high_close_prev, low_close_prev))
        indicators['atr'] = true_range.rolling(14).mean()
        indicators['atr_normalized'] = indicators['atr'] / price_data['close']

        # RSI
        delta = price_data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        indicators['rsi'] = 100 - (100 / (1 + rs))

        # Momentum
        indicators['momentum'] = (price_data['close'] / price_data['close'].shift(14) - 1) * 100

        # Volume trend
        volume_sma = volume_data.rolling(20).mean()
        indicators['volume_trend'] = (volume_data / volume_sma - 1) * 100

        # MACD
        indicators['macd'] = indicators['ema_12'] - indicators['ema_26']
        indicators['macd_signal'] = indicators['macd'].ewm(span=9).mean()
        indicators['macd_histogram'] = indicators['macd'] - indicators['macd_signal']

        return indicators

    def _calculate_trend_strength(self, price_data: pd.DataFrame, indicators: Dict) -> float:
        """Calculate trend strength (0-1 scale)"""

        # Price vs moving averages
        price = price_data['close'].iloc[-1]
        sma_20 = indicators['sma_20'].iloc[-1]
        sma_50 = indicators['sma_50'].iloc[-1]

        # Trend direction consistency
        price_above_sma20 = price > sma_20
        sma20_above_sma50 = sma_20 > sma_50

        # Moving average slope
        sma20_slope = (indicators['sma_20'].iloc[-1] - indicators['sma_20'].iloc[-5]) / 5
        sma50_slope = (indicators['sma_50'].iloc[-1] - indicators['sma_50'].iloc[-10]) / 10

        # MACD confirmation
        macd_bullish = indicators['macd'].iloc[-1] > indicators['macd_signal'].iloc[-1]
        macd_histogram_increasing = indicators['macd_histogram'].iloc[-1] > indicators['macd_histogram'].iloc[-2]

        # Combine factors
        trend_factors = []

        # Direction consistency (40% weight)
        if price_above_sma20 and sma20_above_sma50:
            trend_factors.append(0.8)  # Strong bullish alignment
        elif not price_above_sma20 and not sma20_above_sma50:
            trend_factors.append(0.8)  # Strong bearish alignment
        else:
            trend_factors.append(0.3)  # Mixed signals

        # Slope strength (30% weight)
        slope_strength = min(1.0, abs(sma20_slope) / (price * 0.001))  # Normalize to price
        trend_factors.append(slope_strength)

        # MACD confirmation (30% weight)
        if (price_above_sma20 and macd_bullish) or (not price_above_sma20 and not macd_bullish):
            macd_factor = 0.8 if macd_histogram_increasing else 0.6
        else:
            macd_factor = 0.2
        trend_factors.append(macd_factor)

        # Weighted average
        weights = [0.4, 0.3, 0.3]
        trend_strength = sum(f * w for f, w in zip(trend_factors, weights))

        return min(1.0, max(0.0, trend_strength))

    def _calculate_volatility_level(self, price_data: pd.DataFrame, indicators: Dict) -> float:
        """Calculate volatility level (0-1 scale)"""

        # ATR-based volatility
        current_atr = indicators['atr_normalized'].iloc[-1]
        avg_atr = indicators['atr_normalized'].rolling(50).mean().iloc[-1]

        # Volatility ratio
        volatility_ratio = current_atr / avg_atr if avg_atr > 0 else 1.0

        # Recent price movement
        recent_range = (price_data['high'].iloc[-5:].max() - price_data['low'].iloc[-5:].min()) / price_data['close'].iloc[-1]

        # Combine measures
        volatility_level = min(1.0, (volatility_ratio * 0.7 + recent_range * 30 * 0.3))

        return volatility_level

    def _analyze_volume_quality(self, price_data: pd.DataFrame, volume_data: pd.Series, indicators: Dict) -> float:
        """Analyze volume quality and confirmation (0-1 scale)"""

        # Volume trend
        volume_trend = indicators['volume_trend'].iloc[-1]

        # Volume-price relationship
        price_change = (price_data['close'].iloc[-1] / price_data['close'].iloc[-5] - 1) * 100
        volume_change = (volume_data.iloc[-5:].mean() / volume_data.iloc[-10:-5].mean() - 1) * 100

        # Quality factors
        volume_factors = []

        # Volume confirmation of price moves
        if abs(price_change) > 1:  # Significant price move
            if (price_change > 0 and volume_change > 0) or (price_change < 0 and volume_change > 0):
                volume_factors.append(0.8)  # Good confirmation
            else:
                volume_factors.append(0.3)  # Poor confirmation
        else:
            volume_factors.append(0.5)  # Neutral

        # Recent volume trend
        if volume_trend > 10:
            volume_factors.append(0.7)  # Strong volume
        elif volume_trend > 0:
            volume_factors.append(0.6)  # Moderate volume
        else:
            volume_factors.append(0.4)  # Weak volume

        # Average the factors
        volume_quality = sum(volume_factors) / len(volume_factors)

        return min(1.0, max(0.0, volume_quality))

    def _classify_regime(self, trend_strength: float, volatility_level: float,
                        volume_quality: float, indicators: Dict) -> MarketRegime:
        """Classify market regime based on analysis"""

        price = indicators['sma_20'].iloc[-1]  # Use SMA as price proxy
        sma_50 = indicators['sma_50'].iloc[-1]
        rsi = indicators['rsi'].iloc[-1]

        # Decision logic
        if trend_strength > 0.7 and volatility_level > 0.6:
            if price > sma_50 and rsi > 45:
                return MarketRegime.TRENDING_BULLISH
            elif price < sma_50 and rsi < 55:
                return MarketRegime.TRENDING_BEARISH
            else:
                return MarketRegime.VOLATILE_CHOPPY

        elif trend_strength > 0.5 and volatility_level < 0.4:
            return MarketRegime.LOW_VOLATILITY

        elif volatility_level > 0.8:
            return MarketRegime.VOLATILE_CHOPPY

        elif trend_strength < 0.4:
            if volatility_level > 0.6:
                return MarketRegime.BREAKOUT_PENDING
            else:
                return MarketRegime.CONSOLIDATING

        else:
            return MarketRegime.CONSOLIDATING

    def _calculate_regime_confidence(self, regime: MarketRegime, indicators: Dict,
                                   trend_strength: float, volatility_level: float) -> float:
        """Calculate confidence in regime classification"""

        # Base confidence from indicator alignment
        rsi = indicators['rsi'].iloc[-1]
        macd_aligned = (indicators['macd'].iloc[-1] > indicators['macd_signal'].iloc[-1])

        confidence_factors = []

        # Trend strength contributes to confidence
        confidence_factors.append(trend_strength)

        # RSI regime alignment
        if regime in [MarketRegime.TRENDING_BULLISH, MarketRegime.BREAKOUT_PENDING]:
            rsi_factor = min(1.0, (rsi - 30) / 40) if rsi > 30 else 0.2
        elif regime == MarketRegime.TRENDING_BEARISH:
            rsi_factor = min(1.0, (70 - rsi) / 40) if rsi < 70 else 0.2
        else:
            rsi_factor = 1.0 - abs(rsi - 50) / 50

        confidence_factors.append(rsi_factor)

        # MACD alignment
        if regime in [MarketRegime.TRENDING_BULLISH, MarketRegime.BREAKOUT_PENDING]:
            confidence_factors.append(0.8 if macd_aligned else 0.4)
        elif regime == MarketRegime.TRENDING_BEARISH:
            confidence_factors.append(0.8 if not macd_aligned else 0.4)
        else:
            confidence_factors.append(0.6)

        # Average confidence
        confidence = sum(confidence_factors) / len(confidence_factors)

        return min(1.0, max(0.2, confidence))

    def _calculate_trading_favorability(self, regime: MarketRegime, trend_strength: float,
                                      volatility_level: float, volume_quality: float) -> float:
        """Calculate trading favorability score (0-100)"""

        # Base scores by regime
        regime_scores = {
            MarketRegime.TRENDING_BULLISH: 85.0,
            MarketRegime.TRENDING_BEARISH: 85.0,
            MarketRegime.BREAKOUT_PENDING: 70.0,
            MarketRegime.CONSOLIDATING: 45.0,
            MarketRegime.LOW_VOLATILITY: 30.0,
            MarketRegime.VOLATILE_CHOPPY: 25.0
        }

        base_score = regime_scores.get(regime, 40.0)

        # Adjust for quality factors
        trend_adjustment = (trend_strength - 0.5) * 20  # -10 to +10
        volatility_adjustment = (volatility_level - 0.5) * 10 if volatility_level > 0.3 else -20
        volume_adjustment = (volume_quality - 0.5) * 15  # -7.5 to +7.5

        final_score = base_score + trend_adjustment + volatility_adjustment + volume_adjustment

        return min(100.0, max(0.0, final_score))

    def _calculate_timeframe_alignment(self, indicators: Dict) -> float:
        """Calculate multi-timeframe alignment (simplified)"""

        # Compare short and long-term trends
        sma_20 = indicators['sma_20'].iloc[-1]
        sma_50 = indicators['sma_50'].iloc[-1]

        # Slope alignment
        sma20_slope = indicators['sma_20'].diff().iloc[-5:].mean()
        sma50_slope = indicators['sma_50'].diff().iloc[-10:].mean()

        # Direction alignment
        both_rising = sma20_slope > 0 and sma50_slope > 0
        both_falling = sma20_slope < 0 and sma50_slope < 0

        if both_rising or both_falling:
            alignment = 80.0
        elif sma_20 > sma_50:
            alignment = 60.0
        else:
            alignment = 40.0

        return alignment

    def _generate_trading_recommendations(self, regime: MarketRegime, confidence: float,
                                        trading_favorability: float, trend_strength: float) -> Tuple[bool, float]:
        """Generate trading recommendations"""

        # Should trade decision
        should_trade = (
            trading_favorability >= 60.0 and
            confidence >= 0.6 and
            trend_strength >= self.trend_threshold and
            regime in [MarketRegime.TRENDING_BULLISH, MarketRegime.TRENDING_BEARISH, MarketRegime.BREAKOUT_PENDING]
        )

        # Position size multiplier
        if trading_favorability >= 80.0:
            multiplier = 1.2
        elif trading_favorability >= 60.0:
            multiplier = 1.0
        elif trading_favorability >= 40.0:
            multiplier = 0.7
        else:
            multiplier = 0.3

        # Adjust for confidence
        multiplier *= confidence

        return should_trade, max(0.1, min(1.5, multiplier))

    def should_trade_regime(self, regime_analysis: RegimeAnalysis) -> bool:
        """Determine if current regime is suitable for trading"""
        return (
            regime_analysis.should_trade and
            regime_analysis.trading_favorability >= 60.0 and
            regime_analysis.confidence >= 0.6
        )