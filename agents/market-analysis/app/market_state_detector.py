"""
Market State Detection Agent - Comprehensive market condition analysis
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional, Any
from decimal import Decimal
import numpy as np
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class MarketState:
    """Comprehensive market state representation"""
    regime: str  # trending, ranging, volatile, quiet, transitional
    confidence: float
    session: Dict[str, Any]
    volatility: Dict[str, Any]
    correlations: Dict[str, Any]
    economic_events: List[Dict[str, Any]]
    timestamp: datetime
    indicators: Dict[str, float]
    parameter_adjustments: Dict[str, float]


class MarketRegimeClassifier:
    """Advanced market regime classification using multiple indicators"""
    
    def __init__(self):
        self.adx_threshold = 25  # ADX > 25 indicates trend
        self.volatility_percentiles = {'low': 20, 'high': 80}
        self.range_detection_period = 50
        self.ma_periods = [20, 50, 200]
        
    def classify_market_regime(
        self, 
        price_data: List[Dict], 
        volume_data: List[Dict]
    ) -> Dict[str, Any]:
        """
        Classify market regime using multiple factors
        
        Args:
            price_data: List of price candles
            volume_data: List of volume data
            
        Returns:
            Market regime classification with confidence
        """
        if len(price_data) < self.range_detection_period:
            return {
                'regime': 'insufficient_data',
                'confidence': 0.0,
                'timestamp': datetime.now(timezone.utc),
                'indicators': {},
                'characteristics': {}
            }
            
        current_time = price_data[-1]['timestamp']
        
        # Calculate indicators
        adx = self.calculate_adx(price_data)
        volatility = self.calculate_historical_volatility(price_data)
        volatility_percentile = self.get_volatility_percentile(volatility, price_data)
        range_factor = self.calculate_range_factor(price_data)
        volume_profile = self.analyze_volume_profile(volume_data)
        ma_slopes = self.calculate_ma_slopes(price_data)
        
        # Classification logic
        regime = self.determine_regime(
            adx, volatility_percentile, range_factor, volume_profile, ma_slopes
        )
        
        confidence = self.calculate_regime_confidence(
            adx, volatility_percentile, range_factor, ma_slopes
        )
        
        return {
            'regime': regime,
            'confidence': confidence,
            'timestamp': current_time,
            'indicators': {
                'adx': adx,
                'volatility_percentile': volatility_percentile,
                'range_factor': range_factor,
                'volume_profile': volume_profile,
                'ma_slopes': ma_slopes
            },
            'characteristics': self.get_regime_characteristics(regime)
        }
    
    def calculate_adx(self, price_data: List[Dict], period: int = 14) -> float:
        """Calculate Average Directional Index"""
        if len(price_data) < period * 2:
            return 0.0
            
        # Calculate True Range
        tr_values = []
        for i in range(1, len(price_data)):
            high_low = price_data[i]['high'] - price_data[i]['low']
            high_close = abs(price_data[i]['high'] - price_data[i-1]['close'])
            low_close = abs(price_data[i]['low'] - price_data[i-1]['close'])
            tr_values.append(max(high_low, high_close, low_close))
        
        # Calculate directional movements
        plus_dm = []
        minus_dm = []
        for i in range(1, len(price_data)):
            up_move = price_data[i]['high'] - price_data[i-1]['high']
            down_move = price_data[i-1]['low'] - price_data[i]['low']
            
            if up_move > down_move and up_move > 0:
                plus_dm.append(up_move)
            else:
                plus_dm.append(0)
                
            if down_move > up_move and down_move > 0:
                minus_dm.append(down_move)
            else:
                minus_dm.append(0)
        
        # Calculate smoothed averages
        atr = self._calculate_smoothed_average(tr_values, period)
        plus_di = self._calculate_smoothed_average(plus_dm, period) / atr * 100 if atr > 0 else 0
        minus_di = self._calculate_smoothed_average(minus_dm, period) / atr * 100 if atr > 0 else 0
        
        # Calculate ADX
        dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) > 0 else 0
        
        return dx
    
    def _calculate_smoothed_average(self, values: List[float], period: int) -> float:
        """Calculate smoothed average for ADX components"""
        if len(values) < period:
            return 0.0
        return sum(values[-period:]) / period
    
    def calculate_historical_volatility(self, price_data: List[Dict], period: int = 20) -> float:
        """Calculate historical volatility using log returns"""
        if len(price_data) < period + 1:
            return 0.0
            
        closes = [candle['close'] for candle in price_data[-(period+1):]]
        log_returns = [np.log(closes[i] / closes[i-1]) for i in range(1, len(closes))]
        
        return np.std(log_returns) * np.sqrt(252) * 100  # Annualized volatility %
    
    def get_volatility_percentile(self, current_vol: float, price_data: List[Dict]) -> float:
        """Calculate volatility percentile ranking"""
        # Calculate volatility over rolling windows for the past year
        if len(price_data) < 252:  # Less than a year of data
            return 50.0
            
        historical_vols = []
        for i in range(252, len(price_data)):
            vol = self.calculate_historical_volatility(price_data[i-20:i])
            historical_vols.append(vol)
        
        if not historical_vols:
            return 50.0
            
        percentile = (sum(1 for v in historical_vols if v < current_vol) / len(historical_vols)) * 100
        return percentile
    
    def calculate_range_factor(self, price_data: List[Dict]) -> float:
        """Calculate range factor to detect ranging markets"""
        period = min(self.range_detection_period, len(price_data))
        recent_data = price_data[-period:]
        
        highest = max(candle['high'] for candle in recent_data)
        lowest = min(candle['low'] for candle in recent_data)
        avg_range = sum(candle['high'] - candle['low'] for candle in recent_data) / period
        
        if highest == lowest:
            return 1.0  # Complete range
            
        # Calculate how much price has oscillated within the range
        total_movement = sum(abs(recent_data[i]['close'] - recent_data[i-1]['close']) 
                           for i in range(1, len(recent_data)))
        theoretical_trend_movement = abs(recent_data[-1]['close'] - recent_data[0]['close'])
        
        if total_movement == 0:
            return 1.0
            
        range_factor = 1 - (theoretical_trend_movement / total_movement)
        return max(0, min(1, range_factor))
    
    def analyze_volume_profile(self, volume_data: List[Dict]) -> str:
        """Analyze volume profile for regime confirmation"""
        if not volume_data or len(volume_data) < 20:
            return 'unknown'
            
        recent_volume = [v['volume'] for v in volume_data[-20:]]
        historical_volume = [v['volume'] for v in volume_data[-100:-20]] if len(volume_data) > 100 else recent_volume
        
        avg_recent = np.mean(recent_volume)
        avg_historical = np.mean(historical_volume)
        
        if avg_recent > avg_historical * 1.5:
            return 'high'
        elif avg_recent < avg_historical * 0.5:
            return 'low'
        else:
            return 'normal'
    
    def calculate_ma_slopes(self, price_data: List[Dict]) -> Dict[int, float]:
        """Calculate moving average slopes for trend detection"""
        slopes = {}
        
        for period in self.ma_periods:
            if len(price_data) < period + 10:
                slopes[period] = 0.0
                continue
                
            # Calculate MA values
            ma_values = []
            for i in range(period, len(price_data)):
                ma = sum(price_data[j]['close'] for j in range(i-period, i)) / period
                ma_values.append(ma)
            
            # Calculate slope over last 10 periods
            if len(ma_values) >= 10:
                recent_ma = ma_values[-10:]
                x = np.arange(len(recent_ma))
                slope = np.polyfit(x, recent_ma, 1)[0]
                
                # Normalize slope by price level
                avg_price = np.mean(recent_ma)
                normalized_slope = (slope / avg_price) * 100 if avg_price > 0 else 0
                slopes[period] = normalized_slope
            else:
                slopes[period] = 0.0
                
        return slopes
    
    def determine_regime(
        self, 
        adx: float, 
        vol_percentile: float, 
        range_factor: float, 
        volume_profile: str,
        ma_slopes: Dict[int, float]
    ) -> str:
        """
        Determine market regime based on indicator combination
        """
        # Check for strong trend
        avg_slope = np.mean(list(ma_slopes.values()))
        
        if adx > self.adx_threshold and abs(avg_slope) > 0.5:
            if vol_percentile > self.volatility_percentiles['high']:
                return 'volatile_trending'
            else:
                return 'trending'
        
        # Check for ranging market
        elif range_factor > 0.7:
            if vol_percentile > self.volatility_percentiles['high']:
                return 'volatile_ranging'
            else:
                return 'ranging'
        
        # Check for quiet market
        elif vol_percentile < self.volatility_percentiles['low'] and volume_profile == 'low':
            return 'quiet'
        
        # Check for high volatility without clear direction
        elif vol_percentile > self.volatility_percentiles['high']:
            return 'volatile'
        
        # Transitional state
        else:
            return 'transitional'
    
    def calculate_regime_confidence(
        self, 
        adx: float, 
        vol_percentile: float, 
        range_factor: float,
        ma_slopes: Dict[int, float]
    ) -> float:
        """Calculate confidence in regime classification"""
        confidence_factors = []
        
        # ADX confidence
        if adx > 40:
            confidence_factors.append(0.95)
        elif adx > 25:
            confidence_factors.append(0.80)
        elif adx < 20:
            confidence_factors.append(0.90)  # High confidence in no trend
        else:
            confidence_factors.append(0.60)
        
        # Volatility percentile confidence
        if vol_percentile < 20 or vol_percentile > 80:
            confidence_factors.append(0.90)
        elif vol_percentile < 40 or vol_percentile > 60:
            confidence_factors.append(0.75)
        else:
            confidence_factors.append(0.60)
        
        # Range factor confidence
        if range_factor > 0.8 or range_factor < 0.2:
            confidence_factors.append(0.90)
        else:
            confidence_factors.append(0.70)
        
        # MA slope agreement
        slope_values = list(ma_slopes.values())
        if slope_values:
            slope_agreement = 1 - (np.std(slope_values) / (abs(np.mean(slope_values)) + 0.1))
            confidence_factors.append(max(0.5, min(0.95, slope_agreement)))
        
        return np.mean(confidence_factors) * 100
    
    def get_regime_characteristics(self, regime: str) -> Dict[str, Any]:
        """Get characteristics for the identified regime"""
        characteristics = {
            'trending': {
                'expected_behavior': 'Directional movement with momentum',
                'risk_level': 'moderate',
                'recommended_strategy': 'Trend following with wider stops',
                'typical_duration': '2-8 weeks'
            },
            'ranging': {
                'expected_behavior': 'Price oscillation between support and resistance',
                'risk_level': 'low',
                'recommended_strategy': 'Mean reversion with tight stops',
                'typical_duration': '1-4 weeks'
            },
            'volatile': {
                'expected_behavior': 'Sharp unpredictable movements',
                'risk_level': 'high',
                'recommended_strategy': 'Reduced position size, wider stops',
                'typical_duration': '1-2 weeks'
            },
            'volatile_trending': {
                'expected_behavior': 'Strong directional movement with high volatility',
                'risk_level': 'high',
                'recommended_strategy': 'Trend following with reduced size',
                'typical_duration': '1-3 weeks'
            },
            'volatile_ranging': {
                'expected_behavior': 'Wide range oscillation with sharp moves',
                'risk_level': 'high',
                'recommended_strategy': 'Avoid or use very small positions',
                'typical_duration': '1-2 weeks'
            },
            'quiet': {
                'expected_behavior': 'Low volatility and volume',
                'risk_level': 'low',
                'recommended_strategy': 'Wait for better opportunities',
                'typical_duration': 'Variable'
            },
            'transitional': {
                'expected_behavior': 'Regime change in progress',
                'risk_level': 'moderate',
                'recommended_strategy': 'Reduced activity, wait for confirmation',
                'typical_duration': '2-5 days'
            }
        }
        
        return characteristics.get(regime, {
            'expected_behavior': 'Unknown',
            'risk_level': 'unknown',
            'recommended_strategy': 'Exercise caution',
            'typical_duration': 'Unknown'
        })