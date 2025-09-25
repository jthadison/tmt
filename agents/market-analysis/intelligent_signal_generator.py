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

        # Performance monitoring
        self.pattern_detection_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_response_time": 0.0,
            "average_response_time": 0.0
        }

        # Signal quality metrics
        self.signal_quality_metrics = {
            "total_signals_generated": 0,
            "signals_by_confidence": {"75-80": 0, "80-85": 0, "85-90": 0, "90+": 0},
            "signals_by_pattern": {},
            "signals_by_instrument": {},
            "average_confidence": 0.0,
            "average_risk_reward": 0.0,
            "pattern_success_rate": {},
            "total_confidence_sum": 0.0,
            "total_risk_reward_sum": 0.0
        }

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
        start_time = asyncio.get_event_loop().time()

        try:
            self.pattern_detection_stats["total_calls"] += 1

            url = f"{self.pattern_detection_url}/detect_patterns"
            payload = {
                "instrument": instrument,
                "timeframe": "1h",
                "lookback_periods": 100
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        self.pattern_detection_stats["successful_calls"] += 1
                        result = await response.json()

                        # Record response time
                        response_time = asyncio.get_event_loop().time() - start_time
                        self.pattern_detection_stats["total_response_time"] += response_time
                        self.pattern_detection_stats["average_response_time"] = (
                            self.pattern_detection_stats["total_response_time"] /
                            self.pattern_detection_stats["total_calls"]
                        )

                        return result
                    else:
                        self.pattern_detection_stats["failed_calls"] += 1
                        logger.warning(f"Pattern detection failed for {instrument}: {response.status}")
                        return {"patterns_found": [], "pattern_count": 0}

        except Exception as e:
            self.pattern_detection_stats["failed_calls"] += 1
            logger.error(f"Error calling pattern detection for {instrument}: {e}")
            return {"patterns_found": [], "pattern_count": 0}

    async def _get_vpa_analysis(self, instrument: str) -> Dict:
        """Get Volume Price Analysis from Pattern Detection agent"""
        start_time = asyncio.get_event_loop().time()

        try:
            self.pattern_detection_stats["total_calls"] += 1

            url = f"{self.pattern_detection_url}/analyze_volume"
            payload = {
                "instrument": instrument,
                "timeframe": "1h"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        self.pattern_detection_stats["successful_calls"] += 1
                        result = await response.json()

                        # Record response time
                        response_time = asyncio.get_event_loop().time() - start_time
                        self.pattern_detection_stats["total_response_time"] += response_time
                        self.pattern_detection_stats["average_response_time"] = (
                            self.pattern_detection_stats["total_response_time"] /
                            self.pattern_detection_stats["total_calls"]
                        )

                        return result
                    else:
                        self.pattern_detection_stats["failed_calls"] += 1
                        logger.warning(f"VPA analysis failed for {instrument}: {response.status}")
                        return {"confidence_score": 0.0, "volume_analysis": {}}

        except Exception as e:
            self.pattern_detection_stats["failed_calls"] += 1
            logger.error(f"Error calling VPA analysis for {instrument}: {e}")
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
        overall_confidence = self._calculate_overall_confidence(strong_patterns, vpa_confidence)
        pattern_type = self._get_primary_pattern(strong_patterns, vpa_signals)

        signal = {
            "id": f"intelligent_signal_{self.signal_counter:06d}",
            "instrument": instrument,
            "direction": direction,
            "confidence": overall_confidence,
            "entry_price": entry_data["entry"],
            "stop_loss": entry_data["stop_loss"],
            "take_profit": entry_data["take_profit"],
            "units": units,
            "risk_reward_ratio": round(risk_reward, 2),
            "pattern_type": pattern_type,
            "timeframe": "1H",
            "timestamp": datetime.now().isoformat(),
            "source": "intelligent_analysis",
            "analysis": {
                "wyckoff_patterns": len(strong_patterns),
                "vpa_confidence": vpa_confidence,
                "smart_money_flow": vpa_analysis.get("smart_money_flow"),
                "volume_trend": vpa_analysis.get("volume_trend"),
                "stop_distance_pips": entry_data.get("stop_distance_pips", 0)
            }
        }

        # Track signal quality metrics
        self._track_signal_quality(signal)

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
        """Calculate entry, stop loss, and take profit levels with improved pip accuracy"""

        # Accurate pip values for different instrument types
        pip_info = self._get_pip_info(instrument)
        pip_value = pip_info["pip_value"]
        precision = pip_info["precision"]

        # Dynamic stop loss based on analysis
        base_stop_pips = 25  # Base stop in pips

        if patterns and patterns[0].get("atr_multiple"):
            # Use ATR-based stops if available from pattern analysis
            base_stop_pips = max(15, min(50, int(patterns[0]["atr_multiple"] * 20)))

        # Adjust stop distance based on VPA strength and volatility
        volatility_multiplier = self._get_volatility_multiplier(vpa_analysis)
        stop_distance_pips = base_stop_pips * volatility_multiplier
        stop_distance = stop_distance_pips * pip_value

        # Calculate levels with proper precision
        if direction == "long":
            entry = current_price
            stop_loss = entry - stop_distance
            take_profit = entry + (stop_distance * self.min_risk_reward)
        else:  # short
            entry = current_price
            stop_loss = entry + stop_distance
            take_profit = entry - (stop_distance * self.min_risk_reward)

        return {
            "entry": round(entry, precision),
            "stop_loss": round(stop_loss, precision),
            "take_profit": round(take_profit, precision),
            "stop_distance_pips": round(stop_distance_pips, 1)
        }

    def _get_pip_info(self, instrument: str) -> Dict[str, Any]:
        """Get accurate pip value and precision for different instrument types"""
        if "JPY" in instrument:
            # JPY pairs: 1 pip = 0.01
            return {"pip_value": 0.01, "precision": 3}
        elif any(major in instrument for major in ["XAU", "XAG", "GOLD", "SILVER"]):
            # Precious metals: 1 pip = 0.01 for gold, 0.001 for silver
            if "XAU" in instrument or "GOLD" in instrument:
                return {"pip_value": 0.01, "precision": 2}
            else:
                return {"pip_value": 0.001, "precision": 3}
        elif any(crypto in instrument for crypto in ["BTC", "ETH", "LTC"]):
            # Crypto pairs: 1 pip = 0.1 or 1.0 depending on pair
            return {"pip_value": 1.0, "precision": 1}
        else:
            # Standard forex pairs: 1 pip = 0.0001
            return {"pip_value": 0.0001, "precision": 5}

    def _get_volatility_multiplier(self, vpa_analysis: Dict) -> float:
        """Calculate volatility multiplier based on VPA analysis"""
        strength = vpa_analysis.get("strength", "medium").lower()
        volume_trend = vpa_analysis.get("volume_trend", "normal").lower()

        multiplier = 1.0

        # Adjust based on strength
        if strength == "very_strong":
            multiplier *= 1.4
        elif strength == "strong":
            multiplier *= 1.2
        elif strength == "weak":
            multiplier *= 0.8
        elif strength == "very_weak":
            multiplier *= 0.6

        # Adjust based on volume trend
        if volume_trend in ["climactic", "high"]:
            multiplier *= 1.3
        elif volume_trend == "low":
            multiplier *= 0.7

        return max(0.5, min(2.0, multiplier))  # Cap between 0.5x and 2.0x

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
        """Get current market price from OANDA API"""
        try:
            # Use OANDA API to get real-time pricing
            oanda_api_key = os.getenv("OANDA_API_KEY")
            oanda_account_id = os.getenv("OANDA_ACCOUNT_ID")

            if not oanda_api_key or not oanda_account_id:
                logger.warning("OANDA credentials not available, using fallback price")
                return self._get_fallback_price(instrument)

            url = f"https://api-fxpractice.oanda.com/v3/accounts/{oanda_account_id}/pricing"
            params = {"instruments": instrument}
            headers = {
                "Authorization": f"Bearer {oanda_api_key}",
                "Content-Type": "application/json"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        prices = data.get("prices", [])
                        if prices:
                            bid = float(prices[0].get("bids", [{}])[0].get("price", 0))
                            ask = float(prices[0].get("asks", [{}])[0].get("price", 0))
                            mid_price = (bid + ask) / 2
                            return mid_price

            logger.warning(f"Failed to fetch price for {instrument}, using fallback")
            return self._get_fallback_price(instrument)

        except Exception as e:
            logger.error(f"Error fetching current price for {instrument}: {e}")
            return self._get_fallback_price(instrument)

    def _get_fallback_price(self, instrument: str) -> float:
        """Get fallback price for instruments when OANDA API is unavailable"""
        fallback_prices = {
            "EUR_USD": 1.0850,
            "GBP_USD": 1.2650,
            "USD_JPY": 149.50,
            "AUD_USD": 0.6750,
            "USD_CHF": 0.9150,
            "EUR_GBP": 0.8580,
            "USD_CAD": 1.3650
        }
        return fallback_prices.get(instrument, 1.0000)

    def _track_signal_quality(self, signal: Dict):
        """Track signal quality metrics for performance monitoring"""
        metrics = self.signal_quality_metrics

        # Update counters
        metrics["total_signals_generated"] += 1
        confidence = signal["confidence"]
        risk_reward = signal["risk_reward_ratio"]
        pattern_type = signal["pattern_type"]
        instrument = signal["instrument"]

        # Track confidence distribution
        if confidence >= 90:
            metrics["signals_by_confidence"]["90+"] += 1
        elif confidence >= 85:
            metrics["signals_by_confidence"]["85-90"] += 1
        elif confidence >= 80:
            metrics["signals_by_confidence"]["80-85"] += 1
        else:
            metrics["signals_by_confidence"]["75-80"] += 1

        # Track by pattern type
        metrics["signals_by_pattern"][pattern_type] = metrics["signals_by_pattern"].get(pattern_type, 0) + 1

        # Track by instrument
        metrics["signals_by_instrument"][instrument] = metrics["signals_by_instrument"].get(instrument, 0) + 1

        # Update running averages
        metrics["total_confidence_sum"] += confidence
        metrics["total_risk_reward_sum"] += risk_reward
        metrics["average_confidence"] = metrics["total_confidence_sum"] / metrics["total_signals_generated"]
        metrics["average_risk_reward"] = metrics["total_risk_reward_sum"] / metrics["total_signals_generated"]

    def get_performance_stats(self) -> Dict:
        """Get comprehensive performance statistics"""
        return {
            "pattern_detection_stats": self.pattern_detection_stats.copy(),
            "signal_quality_metrics": self.signal_quality_metrics.copy(),
            "hourly_limits": {
                "signals_sent_this_hour": self.signals_sent_this_hour,
                "max_signals_per_hour": self.max_signals_per_hour,
                "current_hour": self.current_hour
            }
        }

    def _reset_hourly_limits(self):
        """Reset hourly signal limits if hour has changed"""
        current_hour = datetime.now().hour
        if current_hour != self.current_hour:
            self.signals_sent_this_hour = 0
            self.current_hour = current_hour
            logger.info(f"🕐 New hour started - signal count reset")