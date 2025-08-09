"""
VWAP Analysis System

Implements comprehensive VWAP analysis as specified in Story 3.3, Task 4:
- Intraday VWAP calculation using volume-weighted price averages
- VWAP standard deviation bands (1σ, 2σ, 3σ)
- VWAP trend identification (above/below VWAP)
- VWAP mean reversion signals at band extremes
- Anchored VWAP for significant price levels
- VWAP breakout and pullback signals
"""

from typing import Dict, List, Tuple, Optional, Union
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime, time
import logging

logger = logging.getLogger(__name__)


class VWAPAnalyzer:
    """
    Advanced VWAP analysis with standard deviation bands and signal generation.
    
    Calculates multiple VWAP variants including intraday, anchored, and rolling VWAP
    with comprehensive signal analysis.
    """
    
    def __init__(self, 
                 session_start: time = time(9, 30),
                 session_end: time = time(16, 0),
                 band_multipliers: List[float] = None):
        """
        Initialize VWAP analyzer.
        
        Args:
            session_start: Trading session start time for intraday VWAP
            session_end: Trading session end time for intraday VWAP
            band_multipliers: Standard deviation multipliers for bands [1.0, 2.0, 3.0]
        """
        self.session_start = session_start
        self.session_end = session_end
        self.band_multipliers = band_multipliers or [1.0, 2.0, 3.0]
        
    def calculate_vwap_with_bands(self, 
                                price_data: pd.DataFrame, 
                                volume_data: pd.Series,
                                vwap_type: str = 'intraday') -> Dict:
        """
        Calculate comprehensive VWAP analysis with standard deviation bands.
        
        Args:
            price_data: DataFrame with OHLC and timestamp data
            volume_data: Series with volume data
            vwap_type: Type of VWAP ('intraday', 'rolling', 'session')
            
        Returns:
            Dict containing VWAP values, bands, and analysis
        """
        if len(price_data) != len(volume_data):
            return {'error': 'Price and volume data length mismatch'}
        
        if len(price_data) < 10:
            return {'error': 'Insufficient data for VWAP calculation'}
        
        # Calculate base VWAP
        if vwap_type == 'intraday':
            vwap_data = self._calculate_intraday_vwap(price_data, volume_data)
        elif vwap_type == 'rolling':
            vwap_data = self._calculate_rolling_vwap(price_data, volume_data, window=50)
        else:  # session
            vwap_data = self._calculate_session_vwap(price_data, volume_data)
        
        # Calculate standard deviation bands
        bands_data = self._calculate_vwap_bands(vwap_data)
        
        # Generate trading signals
        signals = self.generate_vwap_signals(price_data, vwap_data, bands_data)
        
        # Analyze trend relationship
        trend_analysis = self._analyze_vwap_trend(price_data, vwap_data)
        
        # Calculate support/resistance levels
        sr_levels = self._identify_vwap_sr_levels(vwap_data, bands_data)
        
        # Mean reversion analysis
        mean_reversion = self._analyze_mean_reversion_opportunities(price_data, vwap_data, bands_data)
        
        return {
            'vwap_type': vwap_type,
            'vwap_data': vwap_data,
            'bands_data': bands_data,
            'signals': signals,
            'trend_analysis': trend_analysis,
            'support_resistance_levels': sr_levels,
            'mean_reversion_analysis': mean_reversion,
            'current_position': self._analyze_current_position(price_data, vwap_data, bands_data),
            'alerts': self._generate_vwap_alerts(signals, trend_analysis)
        }
    
    def calculate_anchored_vwap(self,
                              price_data: pd.DataFrame,
                              volume_data: pd.Series,
                              anchor_points: List[Union[int, datetime]]) -> Dict:
        """
        Calculate anchored VWAP from significant price levels or events.
        
        Args:
            anchor_points: List of indices or timestamps to anchor VWAP calculation
            
        Returns:
            Dict with anchored VWAP calculations for each anchor point
        """
        if not anchor_points:
            return {'error': 'No anchor points provided'}
        
        anchored_vwaps = {}
        
        for i, anchor in enumerate(anchor_points):
            # Find anchor index
            if isinstance(anchor, datetime):
                try:
                    anchor_idx = price_data.index.get_loc(anchor)
                except KeyError:
                    # Find nearest timestamp
                    anchor_idx = price_data.index.get_indexer([anchor], method='nearest')[0]
            else:
                anchor_idx = anchor
            
            if anchor_idx >= len(price_data):
                continue
            
            # Calculate VWAP from anchor point forward
            anchored_data = price_data.iloc[anchor_idx:]
            anchored_volume = volume_data.iloc[anchor_idx:]
            
            if len(anchored_data) < 2:
                continue
            
            # Calculate anchored VWAP
            typical_prices = (anchored_data['high'] + anchored_data['low'] + anchored_data['close']) / 3
            cumulative_pv = (typical_prices * anchored_volume).cumsum()
            cumulative_volume = anchored_volume.cumsum()
            
            anchored_vwap = cumulative_pv / cumulative_volume
            anchored_vwap = anchored_vwap.fillna(method='forward')
            
            # Calculate bands for anchored VWAP
            anchored_bands = self._calculate_anchored_vwap_bands(
                anchored_data, anchored_volume, anchored_vwap
            )
            
            # Analyze anchored VWAP signals
            anchored_signals = self._analyze_anchored_vwap_signals(
                anchored_data, anchored_vwap, anchored_bands
            )
            
            anchored_vwaps[f'anchor_{i}'] = {
                'anchor_point': anchor,
                'anchor_index': anchor_idx,
                'vwap_values': anchored_vwap.tolist(),
                'bands': anchored_bands,
                'signals': anchored_signals,
                'current_vwap': float(anchored_vwap.iloc[-1]) if len(anchored_vwap) > 0 else 0,
                'periods_since_anchor': len(anchored_data)
            }
        
        return {
            'anchored_vwaps': anchored_vwaps,
            'total_anchors': len(anchored_vwaps),
            'consensus_analysis': self._analyze_anchored_vwap_consensus(anchored_vwaps, price_data)
        }
    
    def _calculate_intraday_vwap(self, price_data: pd.DataFrame, volume_data: pd.Series) -> List[Dict]:
        """
        Calculate intraday VWAP that resets at the start of each trading session.
        """
        vwap_data = []
        
        # Group data by trading day
        if hasattr(price_data.index, 'date'):
            price_data_with_date = price_data.copy()
            price_data_with_date['date'] = price_data.index.date
            daily_groups = price_data_with_date.groupby('date')
        else:
            # If no datetime index, treat all as single session
            daily_groups = [('single_session', price_data)]
        
        for date, day_data in daily_groups:
            if isinstance(daily_groups, list):
                day_volume = volume_data
            else:
                day_volume = volume_data[day_data.index]
            
            # Calculate typical price for each period
            typical_prices = (day_data['high'] + day_data['low'] + day_data['close']) / 3
            
            # Calculate cumulative VWAP for the day
            cumulative_pv = 0
            cumulative_volume = 0
            
            for i, (idx, row) in enumerate(day_data.iterrows()):
                if isinstance(daily_groups, list):
                    volume = day_volume.iloc[i]
                else:
                    volume = day_volume.loc[idx]
                
                typical_price = typical_prices.loc[idx]
                
                cumulative_pv += typical_price * volume
                cumulative_volume += volume
                
                vwap = cumulative_pv / cumulative_volume if cumulative_volume > 0 else typical_price
                
                vwap_entry = {
                    'timestamp': idx,
                    'vwap': float(vwap),
                    'typical_price': float(typical_price),
                    'volume': float(volume),
                    'cumulative_pv': float(cumulative_pv),
                    'cumulative_volume': float(cumulative_volume),
                    'session_start': True if i == 0 else False
                }
                
                vwap_data.append(vwap_entry)
        
        return vwap_data
    
    def _calculate_rolling_vwap(self, price_data: pd.DataFrame, volume_data: pd.Series, window: int) -> List[Dict]:
        """
        Calculate rolling VWAP over a specified window period.
        """
        vwap_data = []
        
        typical_prices = (price_data['high'] + price_data['low'] + price_data['close']) / 3
        
        for i in range(len(price_data)):
            start_idx = max(0, i - window + 1)
            end_idx = i + 1
            
            window_prices = typical_prices.iloc[start_idx:end_idx]
            window_volume = volume_data.iloc[start_idx:end_idx]
            
            # Calculate VWAP for this window
            pv_sum = (window_prices * window_volume).sum()
            volume_sum = window_volume.sum()
            
            vwap = pv_sum / volume_sum if volume_sum > 0 else window_prices.iloc[-1]
            
            vwap_entry = {
                'timestamp': price_data.index[i],
                'vwap': float(vwap),
                'typical_price': float(typical_prices.iloc[i]),
                'volume': float(volume_data.iloc[i]),
                'window_volume_sum': float(volume_sum),
                'window_periods': end_idx - start_idx
            }
            
            vwap_data.append(vwap_entry)
        
        return vwap_data
    
    def _calculate_session_vwap(self, price_data: pd.DataFrame, volume_data: pd.Series) -> List[Dict]:
        """
        Calculate session VWAP for specific trading hours.
        """
        # For now, use intraday VWAP - could be enhanced with session filtering
        return self._calculate_intraday_vwap(price_data, volume_data)
    
    def _calculate_vwap_bands(self, vwap_data: List[Dict]) -> List[Dict]:
        """
        Calculate standard deviation bands around VWAP.
        """
        if len(vwap_data) < 20:
            return [{'error': 'Insufficient data for band calculation'}]
        
        bands_data = []
        
        for i, vwap_entry in enumerate(vwap_data):
            # Use recent periods for standard deviation calculation
            lookback = min(20, i + 1)
            recent_vwap_values = [vwap_data[j]['vwap'] for j in range(i - lookback + 1, i + 1)]
            recent_typical_prices = [vwap_data[j]['typical_price'] for j in range(i - lookback + 1, i + 1)]
            
            # Calculate standard deviation of price deviations from VWAP
            price_deviations = [abs(price - vwap_data[i]['vwap']) for price in recent_typical_prices]
            std_dev = np.std(price_deviations) if len(price_deviations) > 1 else 0
            
            # Alternative: Calculate VWAP variance using volume-weighted formula
            vwap_variance = self._calculate_vwap_variance(vwap_data[:i+1])
            vwap_std_dev = np.sqrt(vwap_variance)
            
            current_vwap = vwap_entry['vwap']
            
            # Create bands using both methods
            bands_entry = {
                'timestamp': vwap_entry['timestamp'],
                'vwap': current_vwap,
                'std_dev': float(std_dev),
                'vwap_std_dev': float(vwap_std_dev),
                'bands': {}
            }
            
            # Calculate bands for each multiplier
            for multiplier in self.band_multipliers:
                bands_entry['bands'][f'upper_{multiplier}'] = current_vwap + (vwap_std_dev * multiplier)
                bands_entry['bands'][f'lower_{multiplier}'] = current_vwap - (vwap_std_dev * multiplier)
            
            bands_data.append(bands_entry)
        
        return bands_data
    
    def _calculate_vwap_variance(self, vwap_data: List[Dict]) -> float:
        """
        Calculate volume-weighted variance for VWAP standard deviation.
        """
        if len(vwap_data) < 2:
            return 0.0
        
        # Use recent periods for variance calculation
        recent_data = vwap_data[-20:] if len(vwap_data) >= 20 else vwap_data
        
        total_pv_squared = 0.0
        total_pv = 0.0
        total_volume = 0.0
        
        current_vwap = vwap_data[-1]['vwap']
        
        for entry in recent_data:
            typical_price = entry['typical_price']
            volume = entry['volume']
            
            total_pv_squared += (typical_price ** 2) * volume
            total_pv += typical_price * volume
            total_volume += volume
        
        if total_volume == 0:
            return 0.0
        
        # Volume-weighted variance formula
        mean_price_squared = (total_pv / total_volume) ** 2
        mean_squared_price = total_pv_squared / total_volume
        
        variance = mean_squared_price - mean_price_squared
        return max(0.0, variance)  # Ensure non-negative
    
    def generate_vwap_signals(self,
                            price_data: pd.DataFrame,
                            vwap_data: List[Dict],
                            bands_data: List[Dict]) -> Dict:
        """
        Generate comprehensive VWAP trading signals.
        """
        signals = {
            'mean_reversion': [],
            'trend_following': [],
            'breakout': [],
            'pullback': [],
            'support_resistance': []
        }
        
        if len(vwap_data) < 10:
            return {'error': 'Insufficient data for signal generation'}
        
        for i in range(5, len(vwap_data)):  # Start after some data points
            current_price = price_data.iloc[i]['close']
            current_vwap = vwap_data[i]['vwap']
            current_bands = bands_data[i] if i < len(bands_data) else None
            
            if not current_bands:
                continue
            
            # Mean reversion signals at band extremes
            upper_2sigma = current_bands['bands'].get('upper_2.0', current_vwap)
            lower_2sigma = current_bands['bands'].get('lower_2.0', current_vwap)
            upper_3sigma = current_bands['bands'].get('upper_3.0', current_vwap)
            lower_3sigma = current_bands['bands'].get('lower_3.0', current_vwap)
            
            # Strong mean reversion signals (3σ)
            if current_price >= upper_3sigma:
                signals['mean_reversion'].append({
                    'timestamp': vwap_data[i]['timestamp'],
                    'type': 'mean_reversion_short',
                    'entry_price': current_price,
                    'vwap_level': current_vwap,
                    'target': current_vwap,
                    'stop_loss': upper_3sigma * 1.01,
                    'strength': min(100, ((current_price - upper_3sigma) / current_bands['vwap_std_dev']) * 20),
                    'band_level': '3_sigma'
                })
            
            elif current_price <= lower_3sigma:
                signals['mean_reversion'].append({
                    'timestamp': vwap_data[i]['timestamp'],
                    'type': 'mean_reversion_long',
                    'entry_price': current_price,
                    'vwap_level': current_vwap,
                    'target': current_vwap,
                    'stop_loss': lower_3sigma * 0.99,
                    'strength': min(100, ((lower_3sigma - current_price) / current_bands['vwap_std_dev']) * 20),
                    'band_level': '3_sigma'
                })
            
            # Trend following signals (VWAP crosses)
            if i > 0:
                prev_price = price_data.iloc[i-1]['close']
                prev_vwap = vwap_data[i-1]['vwap']
                
                # Bullish VWAP cross
                if prev_price <= prev_vwap and current_price > current_vwap:
                    signals['trend_following'].append({
                        'timestamp': vwap_data[i]['timestamp'],
                        'type': 'bullish_vwap_cross',
                        'entry_price': current_price,
                        'vwap_level': current_vwap,
                        'strength': self._calculate_cross_strength(price_data, vwap_data, i),
                        'confirmation': self._check_volume_confirmation(vwap_data, i)
                    })
                
                # Bearish VWAP cross
                elif prev_price >= prev_vwap and current_price < current_vwap:
                    signals['trend_following'].append({
                        'timestamp': vwap_data[i]['timestamp'],
                        'type': 'bearish_vwap_cross',
                        'entry_price': current_price,
                        'vwap_level': current_vwap,
                        'strength': self._calculate_cross_strength(price_data, vwap_data, i),
                        'confirmation': self._check_volume_confirmation(vwap_data, i)
                    })
            
            # Breakout signals (band breaks with momentum)
            breakout_signal = self._detect_vwap_breakouts(price_data, vwap_data, bands_data, i)
            if breakout_signal:
                signals['breakout'].append(breakout_signal)
            
            # Pullback signals (return to VWAP after band extension)
            pullback_signal = self._detect_vwap_pullbacks(price_data, vwap_data, bands_data, i)
            if pullback_signal:
                signals['pullback'].append(pullback_signal)
            
            # Support/Resistance signals at VWAP
            sr_signal = self._detect_vwap_sr_signals(price_data, vwap_data, i)
            if sr_signal:
                signals['support_resistance'].append(sr_signal)
        
        # Calculate signal quality metrics
        signal_quality = self._calculate_signal_quality(signals)
        
        return {
            'signals': signals,
            'total_signals': sum(len(signal_list) for signal_list in signals.values()),
            'signal_quality': signal_quality,
            'signal_distribution': {k: len(v) for k, v in signals.items()}
        }
    
    def _calculate_anchored_vwap_bands(self,
                                     price_data: pd.DataFrame,
                                     volume_data: pd.Series,
                                     anchored_vwap: pd.Series) -> Dict:
        """
        Calculate standard deviation bands for anchored VWAP.
        """
        if len(anchored_vwap) < 10:
            return {'error': 'Insufficient data for anchored VWAP bands'}
        
        typical_prices = (price_data['high'] + price_data['low'] + price_data['close']) / 3
        
        # Calculate volume-weighted variance for anchored VWAP
        cumulative_volume = volume_data.cumsum()
        price_deviations_squared = ((typical_prices - anchored_vwap) ** 2) * volume_data
        cumulative_variance = price_deviations_squared.cumsum() / cumulative_volume
        
        # Standard deviation
        std_dev = np.sqrt(cumulative_variance)
        
        # Create bands
        bands = {}
        for multiplier in self.band_multipliers:
            bands[f'upper_{multiplier}'] = (anchored_vwap + std_dev * multiplier).tolist()
            bands[f'lower_{multiplier}'] = (anchored_vwap - std_dev * multiplier).tolist()
        
        return {
            'std_dev': std_dev.tolist(),
            'bands': bands,
            'current_std_dev': float(std_dev.iloc[-1]) if len(std_dev) > 0 else 0
        }
    
    def _analyze_anchored_vwap_signals(self,
                                     price_data: pd.DataFrame,
                                     anchored_vwap: pd.Series,
                                     anchored_bands: Dict) -> List[Dict]:
        """
        Analyze signals from anchored VWAP.
        """
        signals = []
        
        if len(price_data) < 5 or 'bands' not in anchored_bands:
            return signals
        
        closes = price_data['close']
        
        for i in range(1, len(closes)):
            current_price = closes.iloc[i]
            current_vwap = anchored_vwap.iloc[i]
            
            # Check for significant moves relative to anchored VWAP
            distance_from_vwap = abs(current_price - current_vwap) / current_vwap * 100
            
            if distance_from_vwap > 2.0:  # 2% threshold
                signal_type = 'above_anchored_vwap' if current_price > current_vwap else 'below_anchored_vwap'
                
                signals.append({
                    'timestamp': price_data.index[i],
                    'type': signal_type,
                    'price': float(current_price),
                    'anchored_vwap': float(current_vwap),
                    'distance_pct': float(distance_from_vwap),
                    'strength': min(100, distance_from_vwap * 10)
                })
        
        return signals
    
    def _analyze_anchored_vwap_consensus(self,
                                       anchored_vwaps: Dict,
                                       price_data: pd.DataFrame) -> Dict:
        """
        Analyze consensus across multiple anchored VWAPs.
        """
        if not anchored_vwaps:
            return {'consensus': 'no_data'}
        
        current_price = price_data['close'].iloc[-1]
        
        # Check position relative to each anchored VWAP
        positions = []
        for anchor_key, anchor_data in anchored_vwaps.items():
            current_vwap = anchor_data['current_vwap']
            if current_vwap > 0:
                position = 'above' if current_price > current_vwap else 'below'
                positions.append(position)
        
        # Calculate consensus
        above_count = positions.count('above')
        below_count = positions.count('below')
        total_count = len(positions)
        
        if above_count > below_count * 1.5:
            consensus = 'strongly_above'
        elif above_count > below_count:
            consensus = 'above'
        elif below_count > above_count * 1.5:
            consensus = 'strongly_below'
        elif below_count > above_count:
            consensus = 'below'
        else:
            consensus = 'mixed'
        
        return {
            'consensus': consensus,
            'above_count': above_count,
            'below_count': below_count,
            'total_anchors': total_count,
            'consensus_strength': max(above_count, below_count) / total_count if total_count > 0 else 0
        }
    
    # Helper methods for signal generation
    def _calculate_cross_strength(self, price_data: pd.DataFrame, vwap_data: List[Dict], index: int) -> float:
        """Calculate strength of VWAP cross signal."""
        if index < 5:
            return 50.0  # Default moderate strength
        
        # Look at volume and price momentum
        recent_volumes = [vwap_data[i]['volume'] for i in range(index-4, index+1)]
        avg_volume = sum(recent_volumes) / len(recent_volumes)
        current_volume = vwap_data[index]['volume']
        
        volume_strength = min(50, (current_volume / avg_volume - 1) * 25) if avg_volume > 0 else 0
        
        # Price momentum
        price_change = abs(price_data.iloc[index]['close'] - price_data.iloc[index-1]['close'])
        avg_price = (price_data.iloc[index]['close'] + price_data.iloc[index-1]['close']) / 2
        price_momentum = (price_change / avg_price) * 1000 if avg_price > 0 else 0
        
        return min(100, 50 + volume_strength + min(25, price_momentum))
    
    def _check_volume_confirmation(self, vwap_data: List[Dict], index: int) -> Dict:
        """Check if volume confirms the VWAP signal."""
        if index < 5:
            return {'confirmed': False, 'reason': 'Insufficient data'}
        
        recent_volumes = [vwap_data[i]['volume'] for i in range(index-4, index)]
        current_volume = vwap_data[index]['volume']
        avg_recent_volume = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 1
        
        volume_ratio = current_volume / avg_recent_volume if avg_recent_volume > 0 else 1
        confirmed = volume_ratio > 1.2  # 20% above recent average
        
        return {
            'confirmed': confirmed,
            'volume_ratio': volume_ratio,
            'current_volume': current_volume,
            'avg_recent_volume': avg_recent_volume
        }
    
    def _detect_vwap_breakouts(self,
                             price_data: pd.DataFrame,
                             vwap_data: List[Dict],
                             bands_data: List[Dict],
                             index: int) -> Optional[Dict]:
        """Detect VWAP band breakouts with momentum."""
        if index < 5 or index >= len(bands_data):
            return None
        
        current_price = price_data.iloc[index]['close']
        current_bands = bands_data[index]
        
        upper_2sigma = current_bands['bands'].get('upper_2.0')
        lower_2sigma = current_bands['bands'].get('lower_2.0')
        
        if not upper_2sigma or not lower_2sigma:
            return None
        
        # Check for breakout with momentum
        if index >= 3:
            price_momentum = current_price - price_data.iloc[index-2]['close']
            momentum_threshold = abs(current_price) * 0.01  # 1% momentum threshold
            
            if current_price > upper_2sigma and price_momentum > momentum_threshold:
                return {
                    'timestamp': vwap_data[index]['timestamp'],
                    'type': 'bullish_breakout',
                    'entry_price': current_price,
                    'breakout_level': upper_2sigma,
                    'momentum': price_momentum,
                    'strength': min(100, ((current_price - upper_2sigma) / current_bands['vwap_std_dev']) * 15)
                }
            
            elif current_price < lower_2sigma and price_momentum < -momentum_threshold:
                return {
                    'timestamp': vwap_data[index]['timestamp'],
                    'type': 'bearish_breakout',
                    'entry_price': current_price,
                    'breakout_level': lower_2sigma,
                    'momentum': price_momentum,
                    'strength': min(100, ((lower_2sigma - current_price) / current_bands['vwap_std_dev']) * 15)
                }
        
        return None
    
    def _detect_vwap_pullbacks(self,
                             price_data: pd.DataFrame,
                             vwap_data: List[Dict],
                             bands_data: List[Dict],
                             index: int) -> Optional[Dict]:
        """Detect pullback to VWAP after band extension."""
        if index < 10 or index >= len(bands_data):
            return None
        
        current_price = price_data.iloc[index]['close']
        current_vwap = vwap_data[index]['vwap']
        
        # Look for recent extension beyond bands followed by return to VWAP
        lookback = min(5, index)
        recent_prices = [price_data.iloc[i]['close'] for i in range(index-lookback, index)]
        recent_vwaps = [vwap_data[i]['vwap'] for i in range(index-lookback, index)]
        
        # Check if price was recently extended and now near VWAP
        max_extension = max(abs(price - vwap) for price, vwap in zip(recent_prices, recent_vwaps))
        current_distance = abs(current_price - current_vwap)
        
        vwap_threshold = current_vwap * 0.005  # 0.5% threshold for "near VWAP"
        
        if max_extension > current_vwap * 0.02 and current_distance < vwap_threshold:
            pullback_direction = 'bullish' if current_price > current_vwap else 'bearish'
            
            return {
                'timestamp': vwap_data[index]['timestamp'],
                'type': f'{pullback_direction}_pullback',
                'entry_price': current_price,
                'vwap_level': current_vwap,
                'max_extension': max_extension,
                'strength': min(100, (max_extension / current_vwap) * 200)
            }
        
        return None
    
    def _detect_vwap_sr_signals(self,
                              price_data: pd.DataFrame,
                              vwap_data: List[Dict],
                              index: int) -> Optional[Dict]:
        """Detect support/resistance signals at VWAP level."""
        if index < 5:
            return None
        
        current_price = price_data.iloc[index]['close']
        current_vwap = vwap_data[index]['vwap']
        
        # Check for multiple touches near VWAP
        lookback = min(10, index)
        recent_prices = [price_data.iloc[i]['close'] for i in range(index-lookback, index+1)]
        recent_vwaps = [vwap_data[i]['vwap'] for i in range(index-lookback, index+1)]
        
        # Count touches within 0.5% of VWAP
        touches = 0
        for price, vwap in zip(recent_prices, recent_vwaps):
            if abs(price - vwap) < vwap * 0.005:
                touches += 1
        
        if touches >= 3:  # Multiple touches indicate S/R
            sr_type = 'support' if current_price >= current_vwap else 'resistance'
            
            return {
                'timestamp': vwap_data[index]['timestamp'],
                'type': f'vwap_{sr_type}',
                'price': current_price,
                'vwap_level': current_vwap,
                'touch_count': touches,
                'strength': min(100, touches * 20)
            }
        
        return None
    
    def _analyze_vwap_trend(self, price_data: pd.DataFrame, vwap_data: List[Dict]) -> Dict:
        """Analyze price trend relative to VWAP."""
        if len(vwap_data) < 20:
            return {'trend': 'insufficient_data'}
        
        # Recent 20 periods
        recent_count = 20
        recent_prices = price_data['close'].iloc[-recent_count:]
        recent_vwaps = [vwap_data[i]['vwap'] for i in range(-recent_count, 0)]
        
        # Count periods above/below VWAP
        above_vwap = sum(1 for price, vwap in zip(recent_prices, recent_vwaps) if price > vwap)
        below_vwap = recent_count - above_vwap
        
        # Trend classification
        if above_vwap >= recent_count * 0.75:
            trend = 'strong_bullish'
        elif above_vwap >= recent_count * 0.6:
            trend = 'bullish'
        elif below_vwap >= recent_count * 0.75:
            trend = 'strong_bearish'
        elif below_vwap >= recent_count * 0.6:
            trend = 'bearish'
        else:
            trend = 'neutral'
        
        # Calculate trend strength
        trend_strength = max(above_vwap, below_vwap) / recent_count * 100
        
        return {
            'trend': trend,
            'trend_strength': round(trend_strength, 2),
            'periods_above_vwap': above_vwap,
            'periods_below_vwap': below_vwap,
            'total_periods': recent_count,
            'current_position': 'above' if recent_prices.iloc[-1] > recent_vwaps[-1] else 'below'
        }
    
    def _identify_vwap_sr_levels(self, vwap_data: List[Dict], bands_data: List[Dict]) -> Dict:
        """Identify key support/resistance levels from VWAP analysis."""
        if len(vwap_data) < 20 or len(bands_data) < 20:
            return {'levels': []}
        
        recent_data = vwap_data[-20:]
        recent_bands = bands_data[-20:]
        
        # Key levels
        current_vwap = recent_data[-1]['vwap']
        avg_std_dev = np.mean([band['vwap_std_dev'] for band in recent_bands[-10:]])
        
        levels = [
            {'level': current_vwap, 'type': 'vwap', 'strength': 'high'},
            {'level': current_vwap + avg_std_dev, 'type': 'resistance', 'strength': 'medium'},
            {'level': current_vwap - avg_std_dev, 'type': 'support', 'strength': 'medium'},
            {'level': current_vwap + 2 * avg_std_dev, 'type': 'strong_resistance', 'strength': 'high'},
            {'level': current_vwap - 2 * avg_std_dev, 'type': 'strong_support', 'strength': 'high'}
        ]
        
        return {
            'levels': levels,
            'current_vwap': current_vwap,
            'avg_std_dev': avg_std_dev
        }
    
    def _analyze_mean_reversion_opportunities(self,
                                            price_data: pd.DataFrame,
                                            vwap_data: List[Dict],
                                            bands_data: List[Dict]) -> Dict:
        """Analyze mean reversion trading opportunities."""
        if len(bands_data) < 10:
            return {'opportunities': []}
        
        opportunities = []
        recent_count = min(20, len(bands_data))
        
        for i in range(-recent_count, 0):
            price = price_data.iloc[i]['close']
            bands = bands_data[i]
            vwap = vwap_data[i]['vwap']
            
            upper_2sigma = bands['bands'].get('upper_2.0', vwap)
            lower_2sigma = bands['bands'].get('lower_2.0', vwap)
            
            # Strong mean reversion opportunities
            if price >= upper_2sigma:
                distance = (price - vwap) / vwap * 100
                opportunities.append({
                    'timestamp': vwap_data[i]['timestamp'],
                    'type': 'mean_reversion_short',
                    'entry_price': price,
                    'target': vwap,
                    'distance_from_vwap_pct': distance,
                    'strength': min(100, distance * 10)
                })
            
            elif price <= lower_2sigma:
                distance = (vwap - price) / vwap * 100
                opportunities.append({
                    'timestamp': vwap_data[i]['timestamp'],
                    'type': 'mean_reversion_long',
                    'entry_price': price,
                    'target': vwap,
                    'distance_from_vwap_pct': distance,
                    'strength': min(100, distance * 10)
                })
        
        return {
            'opportunities': opportunities,
            'total_opportunities': len(opportunities),
            'avg_strength': np.mean([opp['strength'] for opp in opportunities]) if opportunities else 0
        }
    
    def _analyze_current_position(self,
                                price_data: pd.DataFrame,
                                vwap_data: List[Dict],
                                bands_data: List[Dict]) -> Dict:
        """Analyze current price position relative to VWAP and bands."""
        if not vwap_data or not bands_data:
            return {'position': 'unknown'}
        
        current_price = price_data['close'].iloc[-1]
        current_vwap = vwap_data[-1]['vwap']
        current_bands = bands_data[-1]
        
        # Position relative to VWAP
        distance_from_vwap = (current_price - current_vwap) / current_vwap * 100
        
        # Position relative to bands
        upper_1sigma = current_bands['bands'].get('upper_1.0', current_vwap)
        lower_1sigma = current_bands['bands'].get('lower_1.0', current_vwap)
        upper_2sigma = current_bands['bands'].get('upper_2.0', current_vwap)
        lower_2sigma = current_bands['bands'].get('lower_2.0', current_vwap)
        
        if current_price >= upper_2sigma:
            position = 'extreme_overbought'
        elif current_price >= upper_1sigma:
            position = 'overbought'
        elif current_price > current_vwap:
            position = 'above_vwap'
        elif current_price <= lower_2sigma:
            position = 'extreme_oversold'
        elif current_price <= lower_1sigma:
            position = 'oversold'
        else:
            position = 'below_vwap'
        
        return {
            'position': position,
            'current_price': float(current_price),
            'current_vwap': float(current_vwap),
            'distance_from_vwap_pct': round(distance_from_vwap, 2),
            'band_position': {
                'upper_2sigma': float(upper_2sigma),
                'upper_1sigma': float(upper_1sigma),
                'lower_1sigma': float(lower_1sigma),
                'lower_2sigma': float(lower_2sigma)
            }
        }
    
    def _calculate_signal_quality(self, signals: Dict) -> Dict:
        """Calculate overall quality metrics for generated signals."""
        total_signals = sum(len(signal_list) for signal_list in signals.values())
        
        if total_signals == 0:
            return {'quality': 'no_signals', 'score': 0}
        
        # Calculate average strength across all signals
        all_strengths = []
        for signal_type, signal_list in signals.items():
            for signal in signal_list:
                strength = signal.get('strength', 50)
                all_strengths.append(strength)
        
        avg_strength = np.mean(all_strengths) if all_strengths else 0
        
        # Signal diversity bonus
        signal_types_count = sum(1 for signal_list in signals.values() if len(signal_list) > 0)
        diversity_bonus = signal_types_count * 5
        
        quality_score = min(100, avg_strength + diversity_bonus)
        
        if quality_score >= 75:
            quality = 'high'
        elif quality_score >= 50:
            quality = 'medium'
        else:
            quality = 'low'
        
        return {
            'quality': quality,
            'score': round(quality_score, 2),
            'total_signals': total_signals,
            'avg_strength': round(avg_strength, 2),
            'signal_types_active': signal_types_count
        }
    
    def _generate_vwap_alerts(self, signals: Dict, trend_analysis: Dict) -> List[Dict]:
        """Generate trading alerts from VWAP analysis."""
        alerts = []
        
        # High-strength signal alerts
        for signal_type, signal_list in signals.items():
            if isinstance(signal_list, list):
                high_strength_signals = [s for s in signal_list if s.get('strength', 0) >= 70]
                
                for signal in high_strength_signals:
                    alerts.append({
                        'type': 'vwap_signal',
                        'signal_type': signal['type'],
                        'strength': signal.get('strength', 0),
                        'timestamp': signal.get('timestamp'),
                        'message': f"High-strength {signal['type']} VWAP signal detected",
                        'priority': 'high' if signal.get('strength', 0) >= 85 else 'medium'
                    })
        
        # Trend change alerts
        if trend_analysis.get('trend_strength', 0) >= 80:
            alerts.append({
                'type': 'vwap_trend',
                'trend': trend_analysis['trend'],
                'strength': trend_analysis['trend_strength'],
                'message': f"Strong {trend_analysis['trend']} trend relative to VWAP",
                'priority': 'medium'
            })
        
        return alerts