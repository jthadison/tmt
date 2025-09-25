"""
Intelligent Signal Generator - Real Market Analysis
Replaces random signal generation with actual Wyckoff and VPA analysis
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import os

logger = logging.getLogger(__name__)


class IntelligentSignalGenerator:
    """Generates trading signals based on real market analysis"""

    def __init__(self):
        # Service endpoints
        self.pattern_detection_url = "http://localhost:8008"
        self.orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://localhost:8089")

        # Trading instruments
        self.instruments = [
            "EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CHF"
        ]

        # Analysis configuration
        self.min_confidence_threshold = float(os.getenv("MIN_CONFIDENCE", "75.0"))
        self.min_risk_reward = float(os.getenv("MIN_RISK_REWARD", "2.5"))
        self.vpa_threshold = float(os.getenv("VPA_THRESHOLD", "0.65"))

        # Position sizing
        self.position_risk_percent = float(os.getenv("POSITION_RISK", "0.02"))  # 2% risk

        # Rate limiting
        self.max_signals_per_hour = int(os.getenv("MAX_SIGNALS_HOUR", "3"))
        self.signals_sent_this_hour = 0
        self.current_hour = datetime.now().hour

        self.signal_counter = 0

    async def analyze_market_and_generate_signals(self) -> List[Dict]:
        """Main analysis method - replaces random signal generation"""
        signals = []

        # Reset hourly counter if needed
        self._reset_hourly_limits()

        if self.signals_sent_this_hour >= self.max_signals_per_hour:
            logger.info(f"Hourly signal limit reached ({self.max_signals_per_hour})")
            return signals

        # Analyze each instrument
        for instrument in self.instruments:
            try:
                signal = await self._analyze_instrument(instrument)
                if signal:
                    signals.append(signal)
                    logger.info(f"🎯 Real signal generated: {instrument} {signal['direction']} - {signal['pattern_type']}")

                    # Respect rate limits
                    if len(signals) >= (self.max_signals_per_hour - self.signals_sent_this_hour):
                        break

            except Exception as e:
                logger.error(f"Error analyzing {instrument}: {e}")

        return signals

    async def _analyze_instrument(self, instrument: str) -> Optional[Dict]:
        """Analyze a single instrument for trading opportunities"""
        try:
            # Get both Wyckoff patterns and VPA analysis
            wyckoff_data, vpa_data = await asyncio.gather(
                self._get_wyckoff_patterns(instrument),
                self._get_vpa_analysis(instrument),
                return_exceptions=True
            )

            if isinstance(wyckoff_data, Exception) or isinstance(vpa_data, Exception):
                logger.warning(f"Analysis failed for {instrument}")
                return None

            # Combine analyses for signal decision
            signal = await self._combine_analyses(instrument, wyckoff_data, vpa_data)

            return signal

        except Exception as e:
            logger.error(f"Instrument analysis error for {instrument}: {e}")
            return None

    async def _get_wyckoff_patterns(self, instrument: str) -> Dict:
        """Get Wyckoff pattern analysis from Pattern Detection agent"""
        url = f"{self.pattern_detection_url}/detect_patterns"
        payload = {
            "instrument": instrument,
            "timeframe": "1h",
            "lookback_periods": 100
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"Pattern detection failed for {instrument}: {response.status}")
                    return {"patterns_found": [], "pattern_count": 0}

    async def _get_vpa_analysis(self, instrument: str) -> Dict:
        """Get Volume Price Analysis from Pattern Detection agent"""
        url = f"{self.pattern_detection_url}/analyze_volume"
        payload = {
            "instrument": instrument,
            "timeframe": "1h"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"VPA analysis failed for {instrument}: {response.status}")
                    return {"confidence_score": 0.0, "volume_analysis": {}}

    async def _combine_analyses(self, instrument: str, wyckoff_data: Dict, vpa_data: Dict) -> Optional[Dict]:
        """Combine Wyckoff and VPA analyses to generate trading signal"""

        # Extract key data
        patterns = wyckoff_data.get("patterns_found", [])
        vpa_confidence = vpa_data.get("confidence_score", 0.0)
        vpa_analysis = vpa_data.get("volume_analysis", {})
        vpa_signals = vpa_data.get("vpa_signals", {})

        # Check minimum VPA confidence
        if vpa_confidence < (self.vpa_threshold / 100):
            return None

        # Look for high-probability Wyckoff patterns
        strong_patterns = [p for p in patterns if p.get("confidence", 0) >= (self.min_confidence_threshold / 100)]

        if not strong_patterns:
            # No strong Wyckoff patterns, check if VPA alone is strong enough
            if not self._is_strong_vpa_signal(vpa_analysis, vpa_signals):
                return None

        # Determine signal direction from strongest analysis
        direction = self._determine_direction(strong_patterns, vpa_analysis, vpa_signals)
        if not direction:
            return None

        # Calculate entry, stop loss, and take profit
        current_price = await self._get_current_price(instrument)
        if not current_price:
            return None

        entry_data = self._calculate_entry_levels(
            instrument, current_price, direction, strong_patterns, vpa_analysis
        )

        if not entry_data:
            return None

        # Check risk/reward ratio
        risk_reward = abs(entry_data["take_profit"] - entry_data["entry"]) / abs(entry_data["entry"] - entry_data["stop_loss"])
        if risk_reward < self.min_risk_reward:
            return None

        # Calculate position size
        units = self._calculate_position_size(instrument, entry_data["entry"], entry_data["stop_loss"])

        # Generate signal
        self.signal_counter += 1
        signal = {
            "id": f"intelligent_signal_{self.signal_counter:06d}",
            "instrument": instrument,
            "direction": direction,
            "confidence": self._calculate_overall_confidence(strong_patterns, vpa_confidence),
            "entry_price": entry_data["entry"],
            "stop_loss": entry_data["stop_loss"],
            "take_profit": entry_data["take_profit"],
            "units": units,
            "risk_reward_ratio": round(risk_reward, 2),
            "pattern_type": self._get_primary_pattern(strong_patterns, vpa_signals),
            "timeframe": "1H",
            "timestamp": datetime.now().isoformat(),
            "source": "intelligent_analysis",
            "analysis": {
                "wyckoff_patterns": len(strong_patterns),
                "vpa_confidence": vpa_confidence,
                "smart_money_flow": vpa_analysis.get("smart_money_flow"),
                "volume_trend": vpa_analysis.get("volume_trend")
            }
        }

        return signal

    def _is_strong_vpa_signal(self, vpa_analysis: Dict, vpa_signals: Dict) -> bool:
        """Check if VPA analysis alone provides strong signal"""

        # Strong VPA conditions
        strong_conditions = [
            vpa_signals.get("stopping_volume", False),
            vpa_signals.get("climax_volume", False) and vpa_analysis.get("effort_vs_result") == "divergence",
            vpa_signals.get("no_demand", False) and vpa_analysis.get("trend") == "bearish",
            vpa_signals.get("no_supply", False) and vpa_analysis.get("trend") == "bullish"
        ]

        return any(strong_conditions)

    def _determine_direction(self, patterns: List[Dict], vpa_analysis: Dict, vpa_signals: Dict) -> Optional[str]:
        """Determine signal direction from combined analysis"""

        bullish_signals = 0
        bearish_signals = 0

        # Count Wyckoff pattern signals
        for pattern in patterns:
            pattern_type = pattern.get("type", "").lower()  # Use 'type' instead of 'pattern'
            if any(bull_term in pattern_type for bull_term in ["spring", "backup", "accumulation"]):
                bullish_signals += pattern.get("confidence", 0)
            elif any(bear_term in pattern_type for bear_term in ["upthrust", "distribution", "markdown"]):
                bearish_signals += pattern.get("confidence", 0)

        # Add VPA signals
        smart_money_flow = vpa_analysis.get("smart_money_flow", "").lower()
        if smart_money_flow == "buying":
            bullish_signals += 0.3
        elif smart_money_flow == "selling":
            bearish_signals += 0.3

        # VPA specific signals
        if vpa_signals.get("no_supply") or vpa_signals.get("test_for_demand"):
            bullish_signals += 0.2
        if vpa_signals.get("no_demand") or vpa_signals.get("test_for_supply"):
            bearish_signals += 0.2

        # Determine direction
        if bullish_signals > bearish_signals and bullish_signals > 0.5:
            return "long"
        elif bearish_signals > bullish_signals and bearish_signals > 0.5:
            return "short"
        else:
            return None

    def _calculate_entry_levels(self, instrument: str, current_price: float, direction: str,
                               patterns: List[Dict], vpa_analysis: Dict) -> Optional[Dict]:
        """Calculate entry, stop loss, and take profit levels"""

        # Base pip value
        pip_value = 0.0001 if "JPY" not in instrument else 0.01

        # Dynamic stop loss based on analysis
        if patterns and patterns[0].get("atr_multiple"):
            # Use ATR-based stops if available from pattern analysis
            stop_distance = patterns[0]["atr_multiple"] * pip_value * 10
        else:
            # Conservative default stops
            stop_distance = pip_value * 25  # 25 pips default

        # Adjust for volatility
        volatility = vpa_analysis.get("strength", "medium").lower()
        if volatility == "high":
            stop_distance *= 1.5
        elif volatility == "low":
            stop_distance *= 0.7

        # Calculate levels
        if direction == "long":
            entry = current_price
            stop_loss = entry - stop_distance
            take_profit = entry + (stop_distance * self.min_risk_reward)
        else:  # short
            entry = current_price
            stop_loss = entry + stop_distance
            take_profit = entry - (stop_distance * self.min_risk_reward)

        return {
            "entry": round(entry, 5),
            "stop_loss": round(stop_loss, 5),
            "take_profit": round(take_profit, 5)
        }

    def _calculate_overall_confidence(self, patterns: List[Dict], vpa_confidence: float) -> float:
        """Calculate overall signal confidence"""

        pattern_confidence = 0.0
        if patterns:
            pattern_confidence = max(p.get("confidence", 0) for p in patterns)

        # Combine confidences (weighted)
        overall = (pattern_confidence * 0.6 + vpa_confidence * 0.4)
        return round(min(overall * 100, 95.0), 1)  # Cap at 95%

    def _get_primary_pattern(self, patterns: List[Dict], vpa_signals: Dict) -> str:
        """Get the primary pattern type for the signal"""

        if patterns and patterns[0].get("pattern"):
            return patterns[0]["pattern"]

        # Use VPA pattern if no Wyckoff
        for signal_type, active in vpa_signals.items():
            if active:
                return f"vpa_{signal_type}"

        return "vpa_confluence"

    def _calculate_position_size(self, instrument: str, entry: float, stop_loss: float) -> int:
        """Calculate position size based on risk management"""

        # Risk per trade in dollars (2% of $100k = $2000)
        risk_amount = 100000 * self.position_risk_percent

        # Calculate pip value for position sizing
        pip_value_usd = 10 if instrument.startswith("USD") else 10  # Simplified

        # Risk in pips
        risk_pips = abs(entry - stop_loss) / (0.0001 if "JPY" not in instrument else 0.01)

        # Position size
        position_size = int(risk_amount / (risk_pips * pip_value_usd))

        # Limits
        return max(1000, min(position_size, 10000))  # Between 1k and 10k units

    async def _get_current_price(self, instrument: str) -> Optional[float]:
        """Get current market price"""
        # This would connect to OANDA API or use cached price data
        # For now, return a placeholder - in real implementation,
        # this would fetch actual market prices
        return 1.1750  # Placeholder price

    def _reset_hourly_limits(self):
        """Reset hourly signal limits if hour has changed"""
        current_hour = datetime.now().hour
        if current_hour != self.current_hour:
            self.signals_sent_this_hour = 0
            self.current_hour = current_hour
            logger.info(f"🕐 New hour started - signal count reset")