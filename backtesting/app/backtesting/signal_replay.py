"""
Signal Generation Replay - Story 11.2

Recreates Wyckoff pattern detection and VPA analysis from historical data.
Ensures no data leakage by only using information available at decision time.
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import logging
from decimal import Decimal

from .models import TradingSession
from .session_detector import TradingSessionDetector

logger = logging.getLogger(__name__)


class SignalReplayEngine:
    """
    Replays signal generation using historical data

    Recreates the pattern detection and signal generation process
    that would have occurred in live trading, using only data that
    was available at each point in time (no look-ahead bias).

    Integrates with existing Wyckoff and VPA analysis logic.
    """

    def __init__(
        self,
        min_confidence: float = 55.0,
        min_risk_reward: float = 1.8,
        max_risk_reward: float = 5.0,
        use_session_params: bool = False
    ):
        """
        Initialize signal replay engine

        Args:
            min_confidence: Minimum confidence threshold for signals
            min_risk_reward: Minimum risk-reward ratio
            max_risk_reward: Maximum risk-reward ratio
            use_session_params: Use session-specific parameters
        """

        self.min_confidence = min_confidence
        self.min_risk_reward = min_risk_reward
        self.max_risk_reward = max_risk_reward
        self.use_session_params = use_session_params

        self.session_detector = TradingSessionDetector()

        logger.info(
            f"SignalReplayEngine initialized: "
            f"min_confidence={min_confidence}, "
            f"min_rr={min_risk_reward}"
        )

    def generate_signal(
        self,
        symbol: str,
        historical_data: pd.DataFrame,
        current_timestamp: datetime,
        universal_params: Dict,
        session_params: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Generate trading signal from historical data

        Args:
            symbol: Trading instrument
            historical_data: ALL previous CLOSED candles
            current_timestamp: Current timestamp (for session detection)
            universal_params: Universal parameters
            session_params: Optional session-specific parameters

        Returns:
            Signal dict if valid signal found, None otherwise

        CRITICAL: Only uses historical_data (closed candles).
                  Current bar data is NOT available for decisions.
        """

        # Detect current session
        session = self.session_detector.detect_session(current_timestamp)

        # Get appropriate parameters for this session
        if self.use_session_params and session_params:
            params = self.session_detector.get_session_parameters(
                current_timestamp, universal_params, session_params
            )
        else:
            params = universal_params

        # Extract parameters
        confidence_threshold = params.get('confidence_threshold', self.min_confidence)
        min_rr = params.get('min_risk_reward', self.min_risk_reward)

        # Validate we have enough data
        if len(historical_data) < 50:
            logger.debug(f"Insufficient data for signal generation: {len(historical_data)} bars")
            return None

        # Detect Wyckoff patterns using historical data
        pattern = self._detect_wyckoff_pattern(historical_data, symbol)

        if not pattern:
            return None

        # Check confidence threshold
        if pattern['confidence'] < confidence_threshold:
            logger.debug(
                f"Pattern confidence {pattern['confidence']:.1f} below threshold "
                f"{confidence_threshold:.1f}"
            )
            return None

        # Perform VPA analysis
        vpa_score = self._calculate_vpa_score(historical_data)

        # Calculate combined confidence
        combined_confidence = self._calculate_combined_confidence(
            pattern['confidence'], vpa_score
        )

        if combined_confidence < confidence_threshold:
            return None

        # Calculate entry, stop-loss, and take-profit
        signal_levels = self._calculate_signal_levels(
            pattern, historical_data, min_rr
        )

        if not signal_levels:
            return None

        # Validate risk-reward ratio
        risk_reward = signal_levels['risk_reward_ratio']
        if risk_reward < min_rr or risk_reward > self.max_risk_reward:
            logger.debug(
                f"Risk-reward {risk_reward:.2f} outside valid range "
                f"[{min_rr}, {self.max_risk_reward}]"
            )
            return None

        # Build signal
        signal = {
            'symbol': symbol,
            'timestamp': current_timestamp,
            'direction': pattern['direction'],
            'entry_price': signal_levels['entry'],
            'stop_loss': signal_levels['stop_loss'],
            'take_profit': signal_levels['take_profit'],
            'confidence': combined_confidence,
            'risk_reward_ratio': risk_reward,
            'pattern_type': pattern['type'],
            'wyckoff_phase': pattern.get('phase'),
            'vpa_score': vpa_score,
            'trading_session': session,
            'parameters_used': params
        }

        logger.info(
            f"Signal generated: {signal['direction']} {symbol} @ {signal['entry_price']:.5f} "
            f"(confidence: {combined_confidence:.1f}, R:R: {risk_reward:.2f}, "
            f"session: {session.value})"
        )

        return signal

    def _detect_wyckoff_pattern(
        self,
        historical_data: pd.DataFrame,
        symbol: str
    ) -> Optional[Dict]:
        """
        Detect Wyckoff patterns from historical data

        Simplified pattern detection for backtesting.
        In production, this would integrate with the full
        EnhancedWyckoffDetector from market-analysis agent.

        Args:
            historical_data: Historical OHLCV data
            symbol: Trading instrument

        Returns:
            Pattern dict or None
        """

        # Use recent data for pattern detection (last 30 bars)
        recent_bars = min(30, len(historical_data))
        analysis_data = historical_data.iloc[-recent_bars:].copy()

        if len(analysis_data) < 15:
            return None

        # Detect accumulation pattern (simplified)
        accumulation = self._detect_accumulation(analysis_data)
        if accumulation:
            return accumulation

        # Detect distribution pattern (simplified)
        distribution = self._detect_distribution(analysis_data)
        if distribution:
            return distribution

        # Detect spring pattern (simplified)
        spring = self._detect_spring(analysis_data)
        if spring:
            return spring

        # Detect upthrust pattern (simplified)
        upthrust = self._detect_upthrust(analysis_data)
        if upthrust:
            return upthrust

        return None

    def _detect_accumulation(self, data: pd.DataFrame) -> Optional[Dict]:
        """Detect accumulation pattern (simplified version)"""

        # Calculate price range contraction
        ranges = data['high'] - data['low']
        avg_range = ranges.mean()

        recent_range = ranges.iloc[-5:].mean()
        range_contraction = recent_range / avg_range if avg_range > 0 else 1.0

        # Look for sideways movement with support holding
        lows = data['low'].values
        support_level = np.percentile(lows, 20)
        touches = np.sum(np.abs(lows - support_level) < (support_level * 0.003))

        # Volume analysis
        volume = data['volume'].values
        avg_volume = volume[:len(volume)//2].mean()
        recent_volume = volume[len(volume)//2:].mean()
        volume_increase = recent_volume / avg_volume if avg_volume > 0 else 1.0

        # Scoring
        criteria_met = 0
        if range_contraction < 0.8:
            criteria_met += 1
        if touches >= 3:
            criteria_met += 1
        if volume_increase > 1.1:
            criteria_met += 1

        if criteria_met >= 2:
            confidence = 50 + (criteria_met * 10)
            resistance = np.percentile(data['high'].values, 80)

            return {
                'type': 'accumulation',
                'phase': 'accumulation',
                'direction': 'long',
                'confidence': confidence,
                'support': support_level,
                'resistance': resistance
            }

        return None

    def _detect_distribution(self, data: pd.DataFrame) -> Optional[Dict]:
        """Detect distribution pattern (simplified version)"""

        # Look for resistance testing
        highs = data['high'].values
        resistance_level = np.percentile(highs, 80)
        touches = np.sum(np.abs(highs - resistance_level) < (resistance_level * 0.003))

        # Volume on rallies vs declines
        up_bars = data[data['close'] > data['open']]
        down_bars = data[data['close'] < data['open']]

        if len(up_bars) > 0 and len(down_bars) > 0:
            up_volume = up_bars['volume'].mean()
            down_volume = down_bars['volume'].mean()
            volume_ratio = down_volume / up_volume if up_volume > 0 else 1.0
        else:
            volume_ratio = 1.0

        # Scoring
        criteria_met = 0
        if touches >= 3:
            criteria_met += 1
        if volume_ratio > 1.2:
            criteria_met += 1

        if criteria_met >= 2:
            confidence = 50 + (criteria_met * 10)
            support = np.percentile(data['low'].values, 20)

            return {
                'type': 'distribution',
                'phase': 'distribution',
                'direction': 'short',
                'confidence': confidence,
                'support': support,
                'resistance': resistance_level
            }

        return None

    def _detect_spring(self, data: pd.DataFrame) -> Optional[Dict]:
        """Detect spring pattern (simplified version)"""

        lows = data['low'].values

        # Look for false breakdown
        if len(lows) < 10:
            return None

        support = np.min(lows[-10:-2])
        recent_low = lows[-2]
        current_close = data['close'].iloc[-1]

        # Check for breakdown and recovery
        if recent_low < support * 0.998 and current_close > recent_low * 1.002:
            confidence = 65

            resistance = data['high'].iloc[-10:].max()

            return {
                'type': 'spring',
                'phase': 'spring',
                'direction': 'long',
                'confidence': confidence,
                'support': support,
                'resistance': resistance
            }

        return None

    def _detect_upthrust(self, data: pd.DataFrame) -> Optional[Dict]:
        """Detect upthrust pattern (simplified version)"""

        highs = data['high'].values

        # Look for false breakout
        if len(highs) < 10:
            return None

        resistance = np.max(highs[-10:-2])
        recent_high = highs[-2]
        current_close = data['close'].iloc[-1]

        # Check for breakout and rejection
        if recent_high > resistance * 1.002 and current_close < recent_high * 0.998:
            confidence = 65

            support = data['low'].iloc[-10:].min()

            return {
                'type': 'upthrust',
                'phase': 'upthrust',
                'direction': 'short',
                'confidence': confidence,
                'support': support,
                'resistance': resistance
            }

        return None

    def _calculate_vpa_score(self, historical_data: pd.DataFrame) -> float:
        """
        Calculate Volume Price Analysis score

        Simplified VPA scoring for backtesting.

        Args:
            historical_data: Historical OHLCV data

        Returns:
            VPA score (0-100)
        """

        if len(historical_data) < 10:
            return 50.0

        recent_data = historical_data.iloc[-10:].copy()

        # Analyze volume on up vs down moves
        up_bars = recent_data[recent_data['close'] > recent_data['open']]
        down_bars = recent_data[recent_data['close'] < recent_data['open']]

        if len(up_bars) > 0 and len(down_bars) > 0:
            up_volume = up_bars['volume'].mean()
            down_volume = down_bars['volume'].mean()

            # Higher volume on up moves = bullish VPA
            # Higher volume on down moves = bearish VPA
            if up_volume > down_volume:
                vpa_score = 50 + min(30, (up_volume / down_volume - 1) * 30)
            else:
                vpa_score = 50 - min(30, (down_volume / up_volume - 1) * 30)
        else:
            vpa_score = 50.0

        return max(0, min(100, vpa_score))

    def _calculate_combined_confidence(
        self,
        pattern_confidence: float,
        vpa_score: float
    ) -> float:
        """
        Calculate combined confidence from pattern and VPA

        Args:
            pattern_confidence: Pattern detection confidence
            vpa_score: VPA score

        Returns:
            Combined confidence score
        """

        # Weighted combination: 70% pattern, 30% VPA
        combined = (pattern_confidence * 0.7) + (vpa_score * 0.3)
        return round(combined, 1)

    def _calculate_signal_levels(
        self,
        pattern: Dict,
        historical_data: pd.DataFrame,
        min_risk_reward: float
    ) -> Optional[Dict]:
        """
        Calculate entry, stop-loss, and take-profit levels

        Args:
            pattern: Detected pattern
            historical_data: Historical data
            min_risk_reward: Minimum risk-reward ratio

        Returns:
            Dict with entry, stop_loss, take_profit, risk_reward_ratio
        """

        direction = pattern['direction']
        current_price = historical_data['close'].iloc[-1]

        if direction == 'long':
            # Long trade levels
            support = pattern.get('support', current_price * 0.998)
            resistance = pattern.get('resistance', current_price * 1.002)

            # Entry near support
            entry = support * 1.001

            # Stop below support
            range_size = resistance - support
            stop_loss = support - (range_size * 0.2)

            # Take profit based on risk-reward
            risk = entry - stop_loss
            take_profit = entry + (risk * min_risk_reward * 1.2)  # 20% buffer

        else:  # short
            # Short trade levels
            support = pattern.get('support', current_price * 0.998)
            resistance = pattern.get('resistance', current_price * 1.002)

            # Entry near resistance
            entry = resistance * 0.999

            # Stop above resistance
            range_size = resistance - support
            stop_loss = resistance + (range_size * 0.2)

            # Take profit based on risk-reward
            risk = stop_loss - entry
            take_profit = entry - (risk * min_risk_reward * 1.2)

        # Calculate actual risk-reward
        if direction == 'long':
            risk = entry - stop_loss
            reward = take_profit - entry
        else:
            risk = stop_loss - entry
            reward = entry - take_profit

        if risk <= 0:
            return None

        risk_reward_ratio = reward / risk

        return {
            'entry': entry,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_reward_ratio': risk_reward_ratio
        }
