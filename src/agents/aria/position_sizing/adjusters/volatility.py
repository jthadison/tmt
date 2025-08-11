"""
Volatility-Based Position Size Adjuster
=======================================

This module implements volatility-based position size adjustments using
Average True Range (ATR) and volatility percentile ranking to dynamically
adjust position sizes based on market volatility conditions.
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional
import statistics

from ..models import VolatilityRegime, MarketContext

logger = logging.getLogger(__name__)


class VolatilityAdjuster:
    """
    Adjusts position sizes based on market volatility using ATR analysis
    and volatility regime classification.
    """
    
    def __init__(self, atr_period: int = 14, lookback_days: int = 252):
        self.atr_period = atr_period  # ATR calculation period
        self.lookback_days = lookback_days  # Historical data for percentile calculation
        
        # Volatility adjustment factors by regime
        self.adjustment_factors = {
            VolatilityRegime.LOW: Decimal("1.10"),         # Increase size in low volatility
            VolatilityRegime.BELOW_NORMAL: Decimal("1.05"),
            VolatilityRegime.NORMAL: Decimal("1.00"),      # No adjustment
            VolatilityRegime.ABOVE_NORMAL: Decimal("0.90"),
            VolatilityRegime.HIGH: Decimal("0.70"),        # Reduce size in high volatility
            VolatilityRegime.EXTREME: Decimal("0.50")      # Significant reduction
        }
    
    async def adjust_size(self, base_size: Decimal, symbol: str) -> Decimal:
        """
        Apply volatility-based adjustment to position size.
        
        Args:
            base_size: Base position size to adjust
            symbol: Trading symbol
            
        Returns:
            Volatility-adjusted position size
        """
        try:
            # Get market context for the symbol
            market_context = await self._get_market_context(symbol)
            
            # Calculate current ATR
            current_atr = await self._calculate_atr(symbol, self.atr_period)
            
            # Get historical ATR for percentile calculation
            historical_atr = await self._get_historical_atr(symbol, self.lookback_days)
            
            # Calculate volatility percentile
            volatility_percentile = self._calculate_percentile(current_atr, historical_atr)
            
            # Classify volatility regime
            regime = self._classify_volatility_regime(volatility_percentile)
            
            # Get adjustment factor
            adjustment_factor = self.adjustment_factors[regime]
            
            # Apply adjustment
            adjusted_size = base_size * adjustment_factor
            
            logger.info(f"Volatility adjustment for {symbol}: ATR={current_atr:.5f}, "
                       f"percentile={volatility_percentile:.1f}%, regime={regime.value}, "
                       f"factor={adjustment_factor}, size: {base_size} -> {adjusted_size}")
            
            return adjusted_size
            
        except Exception as e:
            logger.error(f"Volatility adjustment failed for {symbol}: {str(e)}")
            # Return base size if adjustment fails
            return base_size
    
    async def _calculate_atr(self, symbol: str, period: int) -> Decimal:
        """
        Calculate Average True Range for the given symbol and period.
        
        In a full implementation, this would fetch real market data.
        For now, we'll simulate ATR calculation.
        """
        # Placeholder implementation - in production this would fetch real OHLC data
        # and calculate true range for each period
        
        # Simulate ATR based on symbol (different volatility profiles)
        base_atr_values = {
            "EURUSD": Decimal("0.0008"),
            "GBPUSD": Decimal("0.0012"),
            "USDJPY": Decimal("0.08"),
            "AUDUSD": Decimal("0.0010"),
            "NZDUSD": Decimal("0.0012"),
            "USDCHF": Decimal("0.0009"),
            "USDCAD": Decimal("0.0011"),
            "XAUUSD": Decimal("1.20"),
            "XAGUSD": Decimal("0.15")
        }
        
        base_atr = base_atr_values.get(symbol, Decimal("0.0010"))
        
        # Add some random variation (in production, this would be real calculation)
        import random
        random.seed(hash(symbol))  # Deterministic for testing
        variation = Decimal(str(random.uniform(0.8, 1.3)))
        
        return base_atr * variation
    
    async def _get_historical_atr(self, symbol: str, days: int) -> List[Decimal]:
        """
        Get historical ATR values for volatility percentile calculation.
        
        In production, this would query the database for historical ATR values.
        """
        # Placeholder implementation - simulate historical ATR data
        current_atr = await self._calculate_atr(symbol, self.atr_period)
        
        # Generate realistic historical ATR distribution
        historical_data = []
        import random
        random.seed(hash(symbol + str(days)))
        
        for i in range(days):
            # Create realistic ATR distribution around current value
            variation = random.gauss(1.0, 0.3)  # Normal distribution with some spread
            variation = max(0.3, min(2.0, variation))  # Clamp to reasonable range
            historical_atr = current_atr * Decimal(str(variation))
            historical_data.append(historical_atr)
        
        return historical_data
    
    def _calculate_percentile(self, current_value: Decimal, historical_values: List[Decimal]) -> Decimal:
        """Calculate percentile ranking of current value in historical distribution."""
        if not historical_values:
            return Decimal("50.0")  # Default to 50th percentile
        
        # Convert to floats for percentile calculation
        current_float = float(current_value)
        historical_floats = [float(val) for val in historical_values]
        
        # Count how many historical values are less than current
        count_below = sum(1 for val in historical_floats if val < current_float)
        
        # Calculate percentile
        percentile = (count_below / len(historical_floats)) * 100
        
        return Decimal(str(round(percentile, 1)))
    
    def _classify_volatility_regime(self, percentile: Decimal) -> VolatilityRegime:
        """Classify volatility regime based on percentile ranking."""
        percentile_float = float(percentile)
        
        if percentile_float < 20.0:
            return VolatilityRegime.LOW
        elif percentile_float < 40.0:
            return VolatilityRegime.BELOW_NORMAL
        elif percentile_float < 60.0:
            return VolatilityRegime.NORMAL
        elif percentile_float < 80.0:
            return VolatilityRegime.ABOVE_NORMAL
        elif percentile_float < 95.0:
            return VolatilityRegime.HIGH
        else:
            return VolatilityRegime.EXTREME
    
    async def _get_market_context(self, symbol: str) -> MarketContext:
        """Get comprehensive market context for the symbol."""
        # Placeholder implementation
        current_atr = await self._calculate_atr(symbol, self.atr_period)
        historical_atr = await self._get_historical_atr(symbol, self.lookback_days)
        volatility_percentile = self._calculate_percentile(current_atr, historical_atr)
        regime = self._classify_volatility_regime(volatility_percentile)
        
        return MarketContext(
            symbol=symbol,
            current_atr=current_atr,
            volatility_percentile=volatility_percentile,
            volatility_regime=regime,
            pip_value=Decimal("10.0"),  # Simplified
            contract_value=Decimal("100000"),  # Standard lot
            margin_requirement=Decimal("0.01")  # 1% margin
        )
    
    def get_volatility_regime(self, symbol: str) -> VolatilityRegime:
        """Get current volatility regime for the symbol (synchronous version)."""
        # This could be used for quick regime checks without full adjustment calculation
        return VolatilityRegime.NORMAL  # Placeholder
    
    def get_adjustment_factor(self, regime: VolatilityRegime) -> Decimal:
        """Get adjustment factor for a specific volatility regime."""
        return self.adjustment_factors.get(regime, Decimal("1.0"))