"""
Market Regime Detection System
Real-time identification of market conditions to prevent September-style performance degradation
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from collections import deque
import asyncio

logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    """Market regime classifications"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"
    UNKNOWN = "unknown"
    REGIME_CHANGE = "regime_change"  # Critical alert state

@dataclass
class RegimeIndicators:
    """Market regime indicators and metrics"""
    volatility: float
    trend_strength: float
    range_efficiency: float
    momentum: float
    volume_profile: float
    session_consistency: float
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class RegimeChangeAlert:
    """Alert for significant regime changes"""
    previous_regime: MarketRegime
    new_regime: MarketRegime
    confidence: float
    indicators: RegimeIndicators
    recommended_action: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

class MarketRegimeDetector:
    """Real-time market regime detection and monitoring"""

    def __init__(self, instruments: List[str]):
        self.instruments = instruments
        self.regime_history = {instrument: deque(maxlen=100) for instrument in instruments}
        self.indicator_history = {instrument: deque(maxlen=500) for instrument in instruments}
        self.current_regimes = {instrument: MarketRegime.UNKNOWN for instrument in instruments}

        # Regime detection parameters
        self.VOLATILITY_THRESHOLD_HIGH = 0.015  # 1.5% ATR threshold
        self.VOLATILITY_THRESHOLD_LOW = 0.005   # 0.5% ATR threshold
        self.TREND_STRENGTH_THRESHOLD = 0.7     # ADX-like indicator
        self.RANGE_EFFICIENCY_THRESHOLD = 0.3   # Price efficiency ratio
        self.MOMENTUM_THRESHOLD = 0.02          # Momentum change threshold

        # Performance tracking for regime-specific validation
        self.regime_performance = {}
        self.regime_change_alerts = deque(maxlen=50)

    def calculate_regime_indicators(self, price_data: pd.DataFrame, instrument: str) -> RegimeIndicators:
        """Calculate comprehensive market regime indicators"""

        if len(price_data) < 50:
            return RegimeIndicators(0, 0, 0, 0, 0, 0)

        # Calculate volatility (ATR-based)
        high_low = price_data['high'] - price_data['low']
        high_close = abs(price_data['high'] - price_data['close'].shift(1))
        low_close = abs(price_data['low'] - price_data['close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=14).mean().iloc[-1]
        volatility = atr / price_data['close'].iloc[-1]

        # Calculate trend strength (ADX-like)
        price_change = price_data['close'].pct_change()
        positive_moves = price_change.where(price_change > 0, 0).rolling(14).sum()
        negative_moves = abs(price_change.where(price_change < 0, 0).rolling(14).sum())
        total_moves = positive_moves + negative_moves
        trend_strength = abs(positive_moves - negative_moves) / (total_moves + 1e-6)
        trend_strength = trend_strength.iloc[-1] if not pd.isna(trend_strength.iloc[-1]) else 0

        # Calculate range efficiency
        price_range = price_data['high'].rolling(20).max() - price_data['low'].rolling(20).min()
        net_change = abs(price_data['close'].iloc[-1] - price_data['close'].iloc[-20])
        range_efficiency = net_change / (price_range.iloc[-1] + 1e-6)

        # Calculate momentum
        momentum_short = price_data['close'].rolling(5).mean()
        momentum_long = price_data['close'].rolling(20).mean()
        momentum = ((momentum_short.iloc[-1] - momentum_long.iloc[-1]) / momentum_long.iloc[-1])

        # Calculate volume profile (if available, otherwise use price action proxy)
        if 'volume' in price_data.columns:
            volume_ma = price_data['volume'].rolling(20).mean()
            volume_profile = price_data['volume'].iloc[-1] / volume_ma.iloc[-1]
        else:
            # Use price action as volume proxy
            price_activity = abs(price_change).rolling(20).mean()
            current_activity = abs(price_change.iloc[-1])
            volume_profile = current_activity / (price_activity.iloc[-1] + 1e-6)

        # Calculate session consistency (how consistent patterns are across sessions)
        session_returns = price_data['close'].pct_change().rolling(24).std()  # 24-hour consistency
        session_consistency = 1.0 - (session_returns.iloc[-1] / 0.02)  # Normalize to 0-1

        return RegimeIndicators(
            volatility=volatility,
            trend_strength=trend_strength,
            range_efficiency=range_efficiency,
            momentum=momentum,
            volume_profile=volume_profile,
            session_consistency=max(0, min(1, session_consistency))
        )

    def classify_regime(self, indicators: RegimeIndicators) -> MarketRegime:
        """Classify market regime based on indicators"""

        # High volatility regime
        if indicators.volatility > self.VOLATILITY_THRESHOLD_HIGH:
            if indicators.trend_strength > self.TREND_STRENGTH_THRESHOLD:
                return MarketRegime.BREAKOUT if abs(indicators.momentum) > 0.01 else MarketRegime.HIGH_VOLATILITY
            else:
                return MarketRegime.HIGH_VOLATILITY

        # Low volatility regime
        elif indicators.volatility < self.VOLATILITY_THRESHOLD_LOW:
            return MarketRegime.LOW_VOLATILITY

        # Trending regimes
        elif indicators.trend_strength > self.TREND_STRENGTH_THRESHOLD:
            if indicators.momentum > self.MOMENTUM_THRESHOLD:
                return MarketRegime.TRENDING_UP
            elif indicators.momentum < -self.MOMENTUM_THRESHOLD:
                return MarketRegime.TRENDING_DOWN
            else:
                return MarketRegime.RANGING

        # Ranging regime
        elif indicators.range_efficiency < self.RANGE_EFFICIENCY_THRESHOLD:
            return MarketRegime.RANGING

        # Reversal detection
        elif abs(indicators.momentum) > 0.015 and indicators.trend_strength < 0.3:
            return MarketRegime.REVERSAL

        else:
            return MarketRegime.UNKNOWN

    def detect_regime_change(self, instrument: str, new_regime: MarketRegime) -> Optional[RegimeChangeAlert]:
        """Detect significant regime changes that may impact performance"""

        if instrument not in self.current_regimes:
            self.current_regimes[instrument] = new_regime
            return None

        previous_regime = self.current_regimes[instrument]

        # Critical regime changes that historically caused performance issues
        critical_changes = [
            (MarketRegime.TRENDING_UP, MarketRegime.HIGH_VOLATILITY),
            (MarketRegime.TRENDING_DOWN, MarketRegime.HIGH_VOLATILITY),
            (MarketRegime.RANGING, MarketRegime.BREAKOUT),
            (MarketRegime.LOW_VOLATILITY, MarketRegime.HIGH_VOLATILITY),
            (MarketRegime.TRENDING_UP, MarketRegime.REVERSAL),
            (MarketRegime.TRENDING_DOWN, MarketRegime.REVERSAL),
        ]

        if (previous_regime, new_regime) in critical_changes:
            # Calculate confidence based on indicator strength
            latest_indicators = self.indicator_history[instrument][-1] if self.indicator_history[instrument] else None
            confidence = self._calculate_regime_confidence(latest_indicators) if latest_indicators else 0.5

            # Generate recommended action
            recommended_action = self._get_recommended_action(previous_regime, new_regime, confidence)

            alert = RegimeChangeAlert(
                previous_regime=previous_regime,
                new_regime=new_regime,
                confidence=confidence,
                indicators=latest_indicators,
                recommended_action=recommended_action
            )

            self.regime_change_alerts.append(alert)
            logger.warning(f"Regime change detected for {instrument}: {previous_regime.value} → {new_regime.value} (confidence: {confidence:.2f})")

            return alert

        return None

    def _calculate_regime_confidence(self, indicators: RegimeIndicators) -> float:
        """Calculate confidence in regime classification"""
        if not indicators:
            return 0.0

        # Confidence based on indicator strength and consistency
        volatility_confidence = min(1.0, indicators.volatility / self.VOLATILITY_THRESHOLD_HIGH)
        trend_confidence = indicators.trend_strength
        consistency_confidence = indicators.session_consistency

        # Weighted average
        confidence = (
            volatility_confidence * 0.3 +
            trend_confidence * 0.4 +
            consistency_confidence * 0.3
        )

        return min(1.0, max(0.0, confidence))

    def _get_recommended_action(self, previous: MarketRegime, new: MarketRegime, confidence: float) -> str:
        """Get recommended action for regime change"""

        high_risk_changes = [
            (MarketRegime.TRENDING_UP, MarketRegime.HIGH_VOLATILITY),
            (MarketRegime.RANGING, MarketRegime.BREAKOUT),
            (MarketRegime.LOW_VOLATILITY, MarketRegime.HIGH_VOLATILITY)
        ]

        if (previous, new) in high_risk_changes and confidence > 0.7:
            return "REDUCE_POSITION_SIZE_50%"
        elif confidence > 0.8:
            return "SWITCH_TO_CONSERVATIVE_PARAMETERS"
        elif confidence > 0.6:
            return "INCREASE_SELECTIVITY_10%"
        else:
            return "MONITOR_CLOSELY"

    async def update_regime_analysis(self, instrument: str, price_data: pd.DataFrame):
        """Update regime analysis for instrument"""

        # Calculate current indicators
        indicators = self.calculate_regime_indicators(price_data, instrument)
        self.indicator_history[instrument].append(indicators)

        # Classify current regime
        new_regime = self.classify_regime(indicators)

        # Check for regime change
        regime_change = self.detect_regime_change(instrument, new_regime)

        # Update current regime
        self.current_regimes[instrument] = new_regime
        self.regime_history[instrument].append((new_regime, datetime.utcnow()))

        if regime_change:
            logger.info(f"Regime change alert for {instrument}: {regime_change.recommended_action}")

    def get_current_regime_summary(self) -> Dict[str, Dict]:
        """Get current regime summary for all instruments"""
        summary = {}

        for instrument in self.instruments:
            latest_indicators = self.indicator_history[instrument][-1] if self.indicator_history[instrument] else None
            current_regime = self.current_regimes.get(instrument, MarketRegime.UNKNOWN)

            summary[instrument] = {
                "regime": current_regime.value,
                "indicators": {
                    "volatility": latest_indicators.volatility if latest_indicators else 0,
                    "trend_strength": latest_indicators.trend_strength if latest_indicators else 0,
                    "momentum": latest_indicators.momentum if latest_indicators else 0,
                    "session_consistency": latest_indicators.session_consistency if latest_indicators else 0
                } if latest_indicators else {},
                "confidence": self._calculate_regime_confidence(latest_indicators) if latest_indicators else 0,
                "last_updated": latest_indicators.timestamp if latest_indicators else datetime.utcnow()
            }

        return summary

    def get_regime_performance_stats(self, instrument: str) -> Dict:
        """Get performance statistics by regime for validation"""
        if instrument not in self.regime_performance:
            return {}

        stats = {}
        for regime, performance_list in self.regime_performance[instrument].items():
            if len(performance_list) >= 5:  # Minimum trades for stats
                stats[regime.value] = {
                    "trades": len(performance_list),
                    "avg_pnl": np.mean(performance_list),
                    "win_rate": sum(1 for p in performance_list if p > 0) / len(performance_list),
                    "max_loss": min(performance_list),
                    "max_profit": max(performance_list)
                }

        return stats

    def update_regime_performance(self, instrument: str, trade_pnl: float):
        """Update performance tracking by regime"""
        current_regime = self.current_regimes.get(instrument, MarketRegime.UNKNOWN)

        if instrument not in self.regime_performance:
            self.regime_performance[instrument] = {}

        if current_regime not in self.regime_performance[instrument]:
            self.regime_performance[instrument][current_regime] = []

        self.regime_performance[instrument][current_regime].append(trade_pnl)

        # Keep only recent performance (last 100 trades per regime)
        if len(self.regime_performance[instrument][current_regime]) > 100:
            self.regime_performance[instrument][current_regime] = \
                self.regime_performance[instrument][current_regime][-100:]

    def should_halt_trading(self, instrument: str) -> Tuple[bool, str]:
        """Determine if trading should be halted due to regime uncertainty"""

        # Check recent regime changes
        recent_alerts = [alert for alert in self.regime_change_alerts
                        if alert.timestamp > datetime.utcnow() - timedelta(hours=4)]

        high_confidence_alerts = [alert for alert in recent_alerts if alert.confidence > 0.8]

        if len(high_confidence_alerts) >= 2:
            return True, "Multiple high-confidence regime changes detected in 4 hours"

        # Check regime consistency
        if instrument in self.regime_history and len(self.regime_history[instrument]) >= 10:
            recent_regimes = [regime for regime, _ in list(self.regime_history[instrument])[-10:]]
            unique_regimes = len(set(recent_regimes))

            if unique_regimes >= 5:  # Too many regime changes
                return True, f"Regime instability detected: {unique_regimes} different regimes in recent history"

        # Check current indicators
        if instrument in self.indicator_history and self.indicator_history[instrument]:
            latest = self.indicator_history[instrument][-1]
            if latest.volatility > self.VOLATILITY_THRESHOLD_HIGH * 2:  # Extreme volatility
                return True, f"Extreme volatility detected: {latest.volatility:.4f}"

        return False, "Trading conditions acceptable"