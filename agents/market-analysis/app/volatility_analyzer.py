"""
Volatility Measurement System - Comprehensive volatility analysis and forecasting
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from dataclasses import dataclass
from decimal import Decimal
import logging
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)


class VolatilityRegime(Enum):
    """Volatility regime classifications"""
    VERY_LOW = "very_low"
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    VERY_HIGH = "very_high"
    EXTREME = "extreme"


@dataclass
class VolatilityMetrics:
    """Comprehensive volatility metrics"""
    atr_values: Dict[int, float]
    historical_volatility: float
    volatility_percentile: float
    volatility_regime: VolatilityRegime
    expansion_detected: bool
    contraction_detected: bool
    garch_forecast: Optional[float] = None
    volatility_clusters: Optional[List[Tuple[datetime, datetime]]] = None


class VolatilityAnalyzer:
    """Advanced volatility analysis and forecasting system"""
    
    def __init__(self):
        self.atr_periods = [14, 21, 50]
        self.historical_vol_period = 252  # 1 year of daily data
        self.vol_lookback_period = 500  # For percentile calculation
        
        # Volatility thresholds
        self.percentile_thresholds = {
            'very_low': 10,
            'low': 25,
            'normal_low': 40,
            'normal_high': 60,
            'high': 75,
            'very_high': 90,
            'extreme': 95
        }
        
        # Historical volatility storage
        self.volatility_history: deque = deque(maxlen=self.vol_lookback_period)
        
        # GARCH model parameters (simplified)
        self.garch_params = {
            'omega': 0.000001,  # Long-term variance
            'alpha': 0.1,       # ARCH coefficient
            'beta': 0.85        # GARCH coefficient
        }
    
    def calculate_comprehensive_volatility(
        self, 
        price_data: List[Dict]
    ) -> VolatilityMetrics:
        """
        Calculate multiple volatility measures
        
        Args:
            price_data: List of price candles
            
        Returns:
            Comprehensive volatility metrics
        """
        if len(price_data) < 2:
            return VolatilityMetrics(
                atr_values={},
                historical_volatility=0.0,
                volatility_percentile=50.0,
                volatility_regime=VolatilityRegime.NORMAL,
                expansion_detected=False,
                contraction_detected=False
            )
        
        # Calculate ATR values
        atr_values = {}
        for period in self.atr_periods:
            atr_values[period] = self.calculate_atr(price_data, period)
        
        # Calculate historical volatility
        returns = self.calculate_returns(price_data)
        historical_vol = self.calculate_historical_volatility(returns)
        
        # Calculate volatility percentile
        vol_percentile = self.calculate_volatility_percentile(historical_vol)
        
        # Classify volatility regime
        vol_regime = self.classify_volatility_regime(vol_percentile)
        
        # Detect expansion/contraction
        expansion = self.detect_volatility_expansion(returns)
        contraction = self.detect_volatility_contraction(returns)
        
        # GARCH forecast
        garch_forecast = self.calculate_garch_forecast(returns)
        
        # Detect volatility clusters
        clusters = self.detect_volatility_clusters(price_data)
        
        return VolatilityMetrics(
            atr_values=atr_values,
            historical_volatility=historical_vol,
            volatility_percentile=vol_percentile,
            volatility_regime=vol_regime,
            expansion_detected=expansion,
            contraction_detected=contraction,
            garch_forecast=garch_forecast,
            volatility_clusters=clusters
        )
    
    def calculate_atr(self, price_data: List[Dict], period: int = 14) -> float:
        """
        Calculate Average True Range
        
        Args:
            price_data: List of price candles
            period: ATR period
            
        Returns:
            ATR value
        """
        if len(price_data) < period + 1:
            return 0.0
        
        true_ranges = []
        
        for i in range(1, len(price_data)):
            high = float(price_data[i]['high'])
            low = float(price_data[i]['low'])
            prev_close = float(price_data[i-1]['close'])
            
            # True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        if len(true_ranges) < period:
            return 0.0
        
        # Calculate ATR using Wilder's smoothing
        atr = np.mean(true_ranges[:period])
        
        for i in range(period, len(true_ranges)):
            atr = ((atr * (period - 1)) + true_ranges[i]) / period
        
        return round(atr, 5)
    
    def calculate_returns(self, price_data: List[Dict]) -> List[float]:
        """
        Calculate log returns from price data
        
        Args:
            price_data: List of price candles
            
        Returns:
            List of log returns
        """
        if len(price_data) < 2:
            return []
        
        closes = [float(candle['close']) for candle in price_data]
        returns = []
        
        for i in range(1, len(closes)):
            if closes[i-1] > 0:
                log_return = np.log(closes[i] / closes[i-1])
                returns.append(log_return)
        
        return returns
    
    def calculate_historical_volatility(
        self, 
        returns: List[float],
        annualize: bool = True
    ) -> float:
        """
        Calculate historical volatility from returns
        
        Args:
            returns: List of returns
            annualize: Whether to annualize the volatility
            
        Returns:
            Historical volatility (as percentage)
        """
        if len(returns) < 2:
            return 0.0
        
        vol = np.std(returns)
        
        if annualize:
            # Annualize assuming 252 trading days
            vol = vol * np.sqrt(252) * 100
        else:
            vol = vol * 100
        
        # Update history
        self.volatility_history.append(vol)
        
        return round(vol, 2)
    
    def calculate_volatility_percentile(self, current_vol: float) -> float:
        """
        Calculate volatility percentile ranking
        
        Args:
            current_vol: Current volatility value
            
        Returns:
            Percentile ranking (0-100)
        """
        if len(self.volatility_history) < 20:
            return 50.0
        
        history = list(self.volatility_history)
        below_current = sum(1 for v in history if v < current_vol)
        percentile = (below_current / len(history)) * 100
        
        return round(percentile, 1)
    
    def classify_volatility_regime(self, percentile: float) -> VolatilityRegime:
        """
        Classify current volatility regime based on percentile
        
        Args:
            percentile: Volatility percentile
            
        Returns:
            Volatility regime classification
        """
        if percentile < self.percentile_thresholds['very_low']:
            return VolatilityRegime.VERY_LOW
        elif percentile < self.percentile_thresholds['low']:
            return VolatilityRegime.LOW
        elif percentile < self.percentile_thresholds['normal_high']:
            return VolatilityRegime.NORMAL
        elif percentile < self.percentile_thresholds['high']:
            return VolatilityRegime.HIGH
        elif percentile < self.percentile_thresholds['extreme']:
            return VolatilityRegime.VERY_HIGH
        else:
            return VolatilityRegime.EXTREME
    
    def detect_volatility_expansion(
        self, 
        returns: List[float],
        lookback: int = 20
    ) -> bool:
        """
        Detect if volatility is expanding
        
        Args:
            returns: List of returns
            lookback: Period to look back
            
        Returns:
            True if volatility is expanding
        """
        if len(returns) < lookback * 2:
            return False
        
        # Compare recent volatility to previous period
        recent_vol = np.std(returns[-lookback:])
        previous_vol = np.std(returns[-lookback*2:-lookback])
        
        # Expansion if recent vol is 50% higher
        return recent_vol > previous_vol * 1.5
    
    def detect_volatility_contraction(
        self, 
        returns: List[float],
        lookback: int = 20
    ) -> bool:
        """
        Detect if volatility is contracting
        
        Args:
            returns: List of returns
            lookback: Period to look back
            
        Returns:
            True if volatility is contracting
        """
        if len(returns) < lookback * 2:
            return False
        
        # Compare recent volatility to previous period
        recent_vol = np.std(returns[-lookback:])
        previous_vol = np.std(returns[-lookback*2:-lookback])
        
        # Contraction if recent vol is 30% lower
        return recent_vol < previous_vol * 0.7
    
    def calculate_garch_forecast(
        self, 
        returns: List[float],
        horizon: int = 1
    ) -> Optional[float]:
        """
        Calculate GARCH volatility forecast (simplified implementation)
        
        Args:
            returns: List of returns
            horizon: Forecast horizon
            
        Returns:
            Forecasted volatility
        """
        if len(returns) < 20:
            return None
        
        # Simplified GARCH(1,1) forecast
        # sigma²(t+1) = omega + alpha * r²(t) + beta * sigma²(t)
        
        omega = self.garch_params['omega']
        alpha = self.garch_params['alpha']
        beta = self.garch_params['beta']
        
        # Calculate current variance
        current_variance = np.var(returns[-20:])
        last_return_squared = returns[-1] ** 2
        
        # One-step ahead forecast
        forecast_variance = omega + alpha * last_return_squared + beta * current_variance
        
        # Convert to volatility (annualized percentage)
        forecast_vol = np.sqrt(forecast_variance) * np.sqrt(252) * 100
        
        return round(forecast_vol, 2)
    
    def detect_volatility_clusters(
        self, 
        price_data: List[Dict],
        threshold_multiplier: float = 2.0
    ) -> List[Tuple[datetime, datetime]]:
        """
        Detect periods of volatility clustering
        
        Args:
            price_data: List of price candles
            threshold_multiplier: Multiplier for cluster detection
            
        Returns:
            List of volatility cluster periods
        """
        if len(price_data) < 50:
            return []
        
        # Calculate rolling volatility
        window = 10
        volatilities = []
        timestamps = []
        
        for i in range(window, len(price_data)):
            window_data = price_data[i-window:i]
            returns = self.calculate_returns(window_data)
            
            if returns:
                vol = np.std(returns)
                volatilities.append(vol)
                timestamps.append(price_data[i]['timestamp'])
        
        if not volatilities:
            return []
        
        # Identify clusters
        mean_vol = np.mean(volatilities)
        threshold = mean_vol * threshold_multiplier
        
        clusters = []
        in_cluster = False
        cluster_start = None
        
        for i, (vol, timestamp) in enumerate(zip(volatilities, timestamps)):
            if vol > threshold:
                if not in_cluster:
                    in_cluster = True
                    cluster_start = timestamp
            else:
                if in_cluster:
                    in_cluster = False
                    if cluster_start:
                        clusters.append((cluster_start, timestamps[i-1]))
        
        # Close any open cluster
        if in_cluster and cluster_start:
            clusters.append((cluster_start, timestamps[-1]))
        
        return clusters
    
    def calculate_volatility_surface(
        self, 
        price_data: List[Dict],
        periods: List[int] = None
    ) -> Dict[int, float]:
        """
        Calculate volatility surface across multiple periods
        
        Args:
            price_data: List of price candles
            periods: List of periods to calculate
            
        Returns:
            Volatility values for each period
        """
        if periods is None:
            periods = [5, 10, 20, 30, 60, 90]
        
        surface = {}
        returns = self.calculate_returns(price_data)
        
        for period in periods:
            if len(returns) >= period:
                period_returns = returns[-period:]
                vol = self.calculate_historical_volatility(period_returns, annualize=True)
                surface[period] = vol
            else:
                surface[period] = 0.0
        
        return surface
    
    def get_volatility_recommendations(
        self, 
        metrics: VolatilityMetrics
    ) -> Dict[str, Any]:
        """
        Get trading recommendations based on volatility analysis
        
        Args:
            metrics: Volatility metrics
            
        Returns:
            Trading recommendations
        """
        recommendations = {
            'position_size_adjustment': 1.0,
            'stop_loss_adjustment': 1.0,
            'signal_threshold_adjustment': 0,
            'recommendations': []
        }
        
        # Adjust based on regime
        if metrics.volatility_regime == VolatilityRegime.VERY_LOW:
            recommendations['position_size_adjustment'] = 1.2
            recommendations['stop_loss_adjustment'] = 0.8
            recommendations['signal_threshold_adjustment'] = 5
            recommendations['recommendations'].append(
                "Low volatility environment - consider larger positions with tighter stops"
            )
        
        elif metrics.volatility_regime == VolatilityRegime.LOW:
            recommendations['position_size_adjustment'] = 1.1
            recommendations['stop_loss_adjustment'] = 0.9
            recommendations['recommendations'].append(
                "Below-average volatility - standard position sizing appropriate"
            )
        
        elif metrics.volatility_regime == VolatilityRegime.HIGH:
            recommendations['position_size_adjustment'] = 0.8
            recommendations['stop_loss_adjustment'] = 1.3
            recommendations['signal_threshold_adjustment'] = -5
            recommendations['recommendations'].append(
                "High volatility - reduce position size and widen stops"
            )
        
        elif metrics.volatility_regime == VolatilityRegime.VERY_HIGH:
            recommendations['position_size_adjustment'] = 0.6
            recommendations['stop_loss_adjustment'] = 1.5
            recommendations['signal_threshold_adjustment'] = -10
            recommendations['recommendations'].append(
                "Very high volatility - significantly reduce risk exposure"
            )
        
        elif metrics.volatility_regime == VolatilityRegime.EXTREME:
            recommendations['position_size_adjustment'] = 0.3
            recommendations['stop_loss_adjustment'] = 2.0
            recommendations['signal_threshold_adjustment'] = -15
            recommendations['recommendations'].append(
                "Extreme volatility - minimal positions or stay out of market"
            )
        
        # Add expansion/contraction recommendations
        if metrics.expansion_detected:
            recommendations['recommendations'].append(
                "Volatility expanding - expect larger price movements"
            )
        
        if metrics.contraction_detected:
            recommendations['recommendations'].append(
                "Volatility contracting - potential breakout incoming"
            )
        
        return recommendations