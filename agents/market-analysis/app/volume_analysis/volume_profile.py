"""
Volume Profile System

Implements comprehensive volume profile analysis as specified in Story 3.3, Task 6:
- Volume profile calculation for any time period
- Point of Control (POC) identification - highest volume price level
- Value Area High (VAH) and Value Area Low (VAL) calculation
- Volume profile-based support/resistance levels
- Profile shape analysis (balanced, trending, double distribution)
- Volume profile breakout and rejection signals
"""

from typing import Dict, List, Tuple, Optional, Union
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime, timedelta
import logging
from collections import defaultdict
from scipy import stats
from scipy.signal import find_peaks

logger = logging.getLogger(__name__)


class VolumeProfileBuilder:
    """
    Advanced volume profile construction and analysis system.
    
    Creates volume profiles showing volume distribution across price levels
    and identifies key levels like POC, VAH, VAL with signal generation.
    """
    
    def __init__(self,
                 default_bins: int = 100,
                 value_area_percentage: float = 0.68,
                 min_volume_threshold: float = 0.01):
        """
        Initialize volume profile builder.
        
        Args:
            default_bins: Default number of price bins for profile construction
            value_area_percentage: Percentage of total volume for value area (0.68 = 68%)
            min_volume_threshold: Minimum volume percentage to consider for analysis
        """
        self.default_bins = default_bins
        self.value_area_percentage = value_area_percentage
        self.min_volume_threshold = min_volume_threshold
        
    def build_volume_profile(self,
                           price_data: pd.DataFrame,
                           volume_data: pd.Series,
                           price_bins: int = None,
                           profile_period: str = 'full') -> Dict:
        """
        Build comprehensive volume profile for the given data.
        
        Args:
            price_data: DataFrame with OHLC data
            volume_data: Series with volume data
            price_bins: Number of price bins (uses default if None)
            profile_period: 'full', 'session', or custom period
            
        Returns:
            Dict containing complete volume profile analysis
        """
        if len(price_data) != len(volume_data):
            return {'error': 'Price and volume data length mismatch'}
        
        if len(price_data) < 10:
            return {'error': 'Insufficient data for volume profile construction'}
        
        bins = price_bins or self.default_bins
        
        # Calculate price range and bin structure
        price_min = price_data['low'].min()
        price_max = price_data['high'].max()
        price_range = price_max - price_min
        
        if price_range == 0:
            return {'error': 'No price movement in data'}
        
        bin_size = price_range / bins
        
        # Build volume profile
        volume_by_price = self._distribute_volume_by_price(
            price_data, volume_data, price_min, price_max, bin_size, bins
        )
        
        # Calculate key levels
        poc_data = self._calculate_poc(volume_by_price, price_min, bin_size)
        value_area_data = self._calculate_value_area(volume_by_price, price_min, bin_size)
        
        # Analyze profile shape
        shape_analysis = self._analyze_profile_shape(volume_by_price)
        
        # Identify support/resistance levels
        sr_levels = self._identify_volume_sr_levels(volume_by_price, price_min, bin_size)
        
        # Generate trading signals
        signals = self._generate_volume_profile_signals(
            price_data, volume_by_price, poc_data, value_area_data, sr_levels
        )
        
        # Calculate profile statistics
        profile_stats = self._calculate_profile_statistics(volume_by_price)
        
        # High-volume node analysis
        hv_nodes = self._identify_high_volume_nodes(volume_by_price, price_min, bin_size)
        
        return {
            'profile_period': profile_period,
            'price_range': {
                'min': float(price_min),
                'max': float(price_max),
                'range': float(price_range),
                'bin_size': float(bin_size),
                'total_bins': bins
            },
            'volume_by_price': self._format_volume_profile_data(volume_by_price, price_min, bin_size),
            'poc': poc_data,
            'value_area': value_area_data,
            'shape_analysis': shape_analysis,
            'support_resistance_levels': sr_levels,
            'high_volume_nodes': hv_nodes,
            'signals': signals,
            'profile_statistics': profile_stats,
            'alerts': self._generate_volume_profile_alerts(signals, poc_data, value_area_data)
        }
    
    def build_session_profiles(self,
                             price_data: pd.DataFrame,
                             volume_data: pd.Series,
                             session_definition: str = 'daily') -> Dict:
        """
        Build volume profiles for multiple sessions/periods.
        
        Args:
            session_definition: 'daily', 'weekly', 'custom' periods
            
        Returns:
            Dict with profiles for each session
        """
        if len(price_data) < 20:
            return {'error': 'Insufficient data for session profiles'}
        
        profiles = {}
        
        if session_definition == 'daily':
            # Group by trading day
            if hasattr(price_data.index, 'date'):
                daily_groups = price_data.groupby(price_data.index.date)
                
                for date, day_data in daily_groups:
                    if len(day_data) >= 5:  # Minimum periods per session
                        day_volume = volume_data[day_data.index]
                        profile = self.build_volume_profile(day_data, day_volume, profile_period=f'daily_{date}')
                        if 'error' not in profile:
                            profiles[str(date)] = profile
                            
        elif session_definition == 'weekly':
            # Group by week
            if hasattr(price_data.index, 'isocalendar'):
                weekly_groups = price_data.groupby([price_data.index.isocalendar().year, 
                                                  price_data.index.isocalendar().week])
                
                for (year, week), week_data in weekly_groups:
                    if len(week_data) >= 10:  # Minimum periods per week
                        week_volume = volume_data[week_data.index]
                        profile = self.build_volume_profile(week_data, week_volume, 
                                                          profile_period=f'weekly_{year}W{week}')
                        if 'error' not in profile:
                            profiles[f'{year}_W{week}'] = profile
        
        # Calculate profile consensus and evolution
        profile_evolution = self._analyze_profile_evolution(profiles)
        
        return {
            'session_profiles': profiles,
            'total_sessions': len(profiles),
            'session_definition': session_definition,
            'profile_evolution': profile_evolution,
            'consensus_levels': self._calculate_consensus_levels(profiles)
        }
    
    def _distribute_volume_by_price(self,
                                  price_data: pd.DataFrame,
                                  volume_data: pd.Series,
                                  price_min: float,
                                  price_max: float,
                                  bin_size: float,
                                  bins: int) -> Dict[int, float]:
        """
        Distribute volume across price bins based on intrabar price action.
        """
        volume_by_price = defaultdict(float)
        
        for i, (idx, candle) in enumerate(price_data.iterrows()):
            high = candle['high']
            low = candle['low']
            volume = volume_data.iloc[i]
            
            if volume <= 0 or high == low:
                # Handle zero volume or doji candles
                mid_price = (high + low) / 2
                bin_index = int((mid_price - price_min) / bin_size)
                bin_index = max(0, min(bins - 1, bin_index))
                volume_by_price[bin_index] += volume
                continue
            
            # Distribute volume across the candle's price range
            candle_range = high - low
            
            # Calculate which bins this candle touches
            start_bin = max(0, int((low - price_min) / bin_size))
            end_bin = min(bins - 1, int((high - price_min) / bin_size))
            
            # More sophisticated volume distribution
            if start_bin == end_bin:
                # Candle fits within single bin
                volume_by_price[start_bin] += volume
            else:
                # Distribute volume proportionally across bins
                # Use tick-by-tick approximation with OHLC
                self._distribute_ohlc_volume(
                    candle, volume, start_bin, end_bin, price_min, bin_size, volume_by_price
                )
        
        return dict(volume_by_price)
    
    def _distribute_ohlc_volume(self,
                              candle: pd.Series,
                              volume: float,
                              start_bin: int,
                              end_bin: int,
                              price_min: float,
                              bin_size: float,
                              volume_by_price: Dict[int, float]) -> None:
        """
        Distribute volume across bins using OHLC approximation.
        
        This method attempts to approximate intrabar volume distribution
        using typical OHLC patterns.
        """
        open_price = candle['open']
        high_price = candle['high']
        low_price = candle['low']
        close_price = candle['close']
        
        # Create price path approximation: Open -> High/Low -> Close
        if close_price >= open_price:  # Bullish candle
            price_path = [open_price, high_price, low_price, close_price]
            volume_weights = [0.25, 0.35, 0.15, 0.25]  # More volume at high
        else:  # Bearish candle
            price_path = [open_price, low_price, high_price, close_price]
            volume_weights = [0.25, 0.35, 0.15, 0.25]  # More volume at low
        
        # Distribute volume along price path
        for price, weight in zip(price_path, volume_weights):
            bin_index = int((price - price_min) / bin_size)
            bin_index = max(start_bin, min(end_bin, bin_index))
            volume_by_price[bin_index] += volume * weight
    
    def _calculate_poc(self, volume_by_price: Dict[int, float], price_min: float, bin_size: float) -> Dict:
        """
        Calculate Point of Control (highest volume price level).
        """
        if not volume_by_price:
            return {'error': 'No volume data'}
        
        # Find bin with maximum volume
        poc_bin = max(volume_by_price.items(), key=lambda x: x[1])[0]
        poc_volume = volume_by_price[poc_bin]
        poc_price = price_min + (poc_bin * bin_size) + (bin_size / 2)  # Bin center
        
        # Calculate POC statistics
        total_volume = sum(volume_by_price.values())
        poc_volume_percentage = (poc_volume / total_volume) * 100 if total_volume > 0 else 0
        
        # Find secondary POC levels
        sorted_volumes = sorted(volume_by_price.items(), key=lambda x: x[1], reverse=True)
        secondary_pocs = []
        
        for bin_idx, volume in sorted_volumes[1:6]:  # Top 5 excluding main POC
            if volume > poc_volume * 0.3:  # At least 30% of main POC volume
                price = price_min + (bin_idx * bin_size) + (bin_size / 2)
                secondary_pocs.append({
                    'price': float(price),
                    'volume': float(volume),
                    'volume_percentage': (volume / total_volume) * 100
                })
        
        return {
            'price': float(poc_price),
            'bin_index': poc_bin,
            'volume': float(poc_volume),
            'volume_percentage': round(poc_volume_percentage, 2),
            'secondary_pocs': secondary_pocs,
            'poc_strength': min(100, poc_volume_percentage * 5)  # Strength score
        }
    
    def _calculate_value_area(self, volume_by_price: Dict[int, float], price_min: float, bin_size: float) -> Dict:
        """
        Calculate Value Area High (VAH) and Value Area Low (VAL).
        
        Value Area contains X% of total volume (default 68%) around POC.
        """
        if not volume_by_price:
            return {'error': 'No volume data'}
        
        # Sort bins by volume (descending)
        sorted_bins = sorted(volume_by_price.items(), key=lambda x: x[1], reverse=True)
        total_volume = sum(volume_by_price.values())
        target_volume = total_volume * self.value_area_percentage
        
        # Start with POC and expand outward
        poc_bin = sorted_bins[0][0]
        value_area_bins = {poc_bin}
        accumulated_volume = sorted_bins[0][1]
        
        # Expand value area by adding bins with highest volume
        for bin_idx, volume in sorted_bins[1:]:
            if accumulated_volume >= target_volume:
                break
            value_area_bins.add(bin_idx)
            accumulated_volume += volume
        
        # Calculate VAH and VAL from the bins in value area
        if value_area_bins:
            min_bin = min(value_area_bins)
            max_bin = max(value_area_bins)
            
            val_price = price_min + (min_bin * bin_size)  # Value Area Low
            vah_price = price_min + ((max_bin + 1) * bin_size)  # Value Area High
            
            # Calculate value area statistics
            value_area_range = vah_price - val_price
            value_area_volume_pct = (accumulated_volume / total_volume) * 100
            
            # Node density in value area
            bins_in_va = len(value_area_bins)
            node_density = accumulated_volume / bins_in_va if bins_in_va > 0 else 0
            
        else:
            val_price = vah_price = price_min
            value_area_range = node_density = value_area_volume_pct = 0
            bins_in_va = 0
        
        return {
            'vah': float(vah_price),
            'val': float(val_price),
            'value_area_range': float(value_area_range),
            'volume_percentage': round(value_area_volume_pct, 2),
            'bins_in_value_area': bins_in_va,
            'node_density': round(node_density, 2),
            'value_area_bins': list(value_area_bins)
        }
    
    def _analyze_profile_shape(self, volume_by_price: Dict[int, float]) -> Dict:
        """
        Analyze volume profile shape characteristics.
        
        Identifies balanced, trending, or double distribution patterns.
        """
        if not volume_by_price:
            return {'shape': 'no_data'}
        
        bins = sorted(volume_by_price.keys())
        volumes = [volume_by_price[bin_idx] for bin_idx in bins]
        
        if len(volumes) < 5:
            return {'shape': 'insufficient_data'}
        
        # Calculate distribution statistics
        total_volume = sum(volumes)
        mean_volume = np.mean(volumes)
        std_volume = np.std(volumes)
        cv = std_volume / mean_volume if mean_volume > 0 else 0  # Coefficient of variation
        
        # Find peaks in the distribution
        peaks, peak_properties = find_peaks(volumes, height=mean_volume * 0.5, distance=3)
        num_peaks = len(peaks)
        
        # Skewness and kurtosis
        skewness = stats.skew(volumes)
        kurtosis = stats.kurtosis(volumes)
        
        # Shape classification
        if num_peaks >= 2 and cv > 0.8:
            # Multiple peaks with high variability
            shape = 'double_distribution'
            balance_score = 30  # Low balance
        elif num_peaks == 1 and abs(skewness) < 0.5 and cv < 0.6:
            # Single peak, symmetric, low variability
            shape = 'balanced'
            balance_score = 85
        elif abs(skewness) > 1.0:
            # Highly skewed distribution
            shape = 'trending'
            balance_score = 40
        elif cv > 1.2:
            # High variability, irregular shape
            shape = 'irregular'
            balance_score = 20
        else:
            # Somewhat balanced but not perfect
            shape = 'semi_balanced'
            balance_score = 65
        
        # Additional shape characteristics
        volume_concentration = self._calculate_volume_concentration(volumes)
        profile_width = self._calculate_profile_width(volumes)
        
        return {
            'shape': shape,
            'balance_score': round(balance_score, 2),
            'num_peaks': num_peaks,
            'skewness': round(skewness, 3),
            'kurtosis': round(kurtosis, 3),
            'coefficient_of_variation': round(cv, 3),
            'volume_concentration': volume_concentration,
            'profile_width': profile_width,
            'shape_strength': min(100, abs(skewness) * 50 + cv * 30)
        }
    
    def _identify_volume_sr_levels(self,
                                 volume_by_price: Dict[int, float],
                                 price_min: float,
                                 bin_size: float) -> List[Dict]:
        """
        Identify support and resistance levels based on volume profile.
        """
        if not volume_by_price:
            return []
        
        # Sort by volume to find significant levels
        sorted_volumes = sorted(volume_by_price.items(), key=lambda x: x[1], reverse=True)
        total_volume = sum(volume_by_price.values())
        
        sr_levels = []
        
        # Take top volume levels as potential S/R
        for bin_idx, volume in sorted_volumes[:10]:  # Top 10 volume levels
            volume_percentage = (volume / total_volume) * 100
            
            # Only consider levels with significant volume
            if volume_percentage >= self.min_volume_threshold * 100:
                price = price_min + (bin_idx * bin_size) + (bin_size / 2)
                
                # Determine level type based on position in profile
                all_bins = sorted(volume_by_price.keys())
                position_pct = (bin_idx - min(all_bins)) / (max(all_bins) - min(all_bins)) * 100
                
                if position_pct > 70:
                    level_type = 'resistance'
                elif position_pct < 30:
                    level_type = 'support'
                else:
                    level_type = 'pivot'
                
                # Calculate level strength
                strength = min(100, volume_percentage * 10)
                
                sr_levels.append({
                    'price': float(price),
                    'volume': float(volume),
                    'volume_percentage': round(volume_percentage, 2),
                    'level_type': level_type,
                    'strength': round(strength, 2),
                    'position_percentile': round(position_pct, 2)
                })
        
        # Sort by strength
        sr_levels.sort(key=lambda x: x['strength'], reverse=True)
        
        return sr_levels[:5]  # Return top 5 levels
    
    def _identify_high_volume_nodes(self,
                                  volume_by_price: Dict[int, float],
                                  price_min: float,
                                  bin_size: float) -> List[Dict]:
        """
        Identify high-volume nodes that act as support/resistance.
        """
        if not volume_by_price:
            return []
        
        bins = sorted(volume_by_price.keys())
        volumes = [volume_by_price[bin_idx] for bin_idx in bins]
        
        # Find peaks in volume distribution
        mean_volume = np.mean(volumes)
        peaks, peak_properties = find_peaks(
            volumes, 
            height=mean_volume * 0.7,  # 70% of mean volume
            distance=2,  # Minimum 2 bins apart
            prominence=mean_volume * 0.3  # Minimum prominence
        )
        
        hv_nodes = []
        
        for peak_idx in peaks:
            bin_idx = bins[peak_idx]
            volume = volume_by_price[bin_idx]
            price = price_min + (bin_idx * bin_size) + (bin_size / 2)
            
            # Calculate node strength
            total_volume = sum(volume_by_price.values())
            volume_percentage = (volume / total_volume) * 100
            strength = min(100, volume_percentage * 8)
            
            # Analyze surrounding volume
            surrounding_volume = self._analyze_surrounding_volume(
                volume_by_price, bin_idx, bins
            )
            
            hv_nodes.append({
                'price': float(price),
                'volume': float(volume),
                'volume_percentage': round(volume_percentage, 2),
                'strength': round(strength, 2),
                'bin_index': bin_idx,
                'surrounding_analysis': surrounding_volume
            })
        
        # Sort by volume percentage
        hv_nodes.sort(key=lambda x: x['volume_percentage'], reverse=True)
        
        return hv_nodes
    
    def _generate_volume_profile_signals(self,
                                       price_data: pd.DataFrame,
                                       volume_by_price: Dict[int, float],
                                       poc_data: Dict,
                                       value_area_data: Dict,
                                       sr_levels: List[Dict]) -> Dict:
        """
        Generate trading signals based on volume profile analysis.
        """
        signals = {
            'breakout_signals': [],
            'rejection_signals': [],
            'rotation_signals': [],
            'profile_edge_signals': []
        }
        
        if len(price_data) < 5:
            return signals
        
        current_price = price_data['close'].iloc[-1]
        
        # POC-based signals
        poc_price = poc_data.get('price', 0)
        vah_price = value_area_data.get('vah', 0)
        val_price = value_area_data.get('val', 0)
        
        if poc_price > 0 and vah_price > 0 and val_price > 0:
            # Value Area breakout/breakdown signals
            if current_price > vah_price:
                distance_pct = ((current_price - vah_price) / vah_price) * 100
                signals['breakout_signals'].append({
                    'type': 'vah_breakout',
                    'price': float(current_price),
                    'level': float(vah_price),
                    'distance_pct': round(distance_pct, 2),
                    'strength': min(100, distance_pct * 20)
                })
            
            elif current_price < val_price:
                distance_pct = ((val_price - current_price) / val_price) * 100
                signals['breakout_signals'].append({
                    'type': 'val_breakdown',
                    'price': float(current_price),
                    'level': float(val_price),
                    'distance_pct': round(distance_pct, 2),
                    'strength': min(100, distance_pct * 20)
                })
            
            # POC rotation signals
            poc_distance_pct = abs(current_price - poc_price) / poc_price * 100
            if poc_distance_pct < 1.0:  # Within 1% of POC
                signals['rotation_signals'].append({
                    'type': 'poc_rotation',
                    'price': float(current_price),
                    'poc_price': float(poc_price),
                    'distance_pct': round(poc_distance_pct, 2),
                    'strength': round(100 - poc_distance_pct * 50, 2)
                })
        
        # Support/Resistance level signals
        for level in sr_levels:
            level_price = level['price']
            distance_pct = abs(current_price - level_price) / level_price * 100
            
            if distance_pct < 0.5:  # Very close to level
                if current_price > level_price and level['level_type'] == 'resistance':
                    signals['breakout_signals'].append({
                        'type': 'resistance_breakout',
                        'price': float(current_price),
                        'level': float(level_price),
                        'level_strength': level['strength'],
                        'distance_pct': round(distance_pct, 2)
                    })
                elif current_price < level_price and level['level_type'] == 'support':
                    signals['breakout_signals'].append({
                        'type': 'support_breakdown',
                        'price': float(current_price),
                        'level': float(level_price),
                        'level_strength': level['strength'],
                        'distance_pct': round(distance_pct, 2)
                    })
        
        # Profile edge signals (outside normal range)
        if volume_by_price:
            price_bins = sorted(volume_by_price.keys())
            total_volume = sum(volume_by_price.values())
            
            # Calculate price percentiles based on volume
            low_volume_threshold = total_volume * 0.1  # Bottom 10% of volume
            high_volume_threshold = total_volume * 0.1  # Top 10% of volume
            
            # Check if price is at profile edges with low volume
            edge_signals = self._detect_profile_edge_signals(
                current_price, volume_by_price, price_data.iloc[-5:]
            )
            signals['profile_edge_signals'].extend(edge_signals)
        
        # Calculate signal quality
        total_signals = sum(len(signal_list) for signal_list in signals.values())
        signal_quality = self._assess_volume_profile_signal_quality(signals, poc_data, value_area_data)
        
        return {
            **signals,
            'total_signals': total_signals,
            'signal_quality': signal_quality
        }
    
    def _calculate_profile_statistics(self, volume_by_price: Dict[int, float]) -> Dict:
        """
        Calculate comprehensive statistics for the volume profile.
        """
        if not volume_by_price:
            return {'total_volume': 0}
        
        bins = sorted(volume_by_price.keys())
        volumes = [volume_by_price[bin_idx] for bin_idx in bins]
        
        total_volume = sum(volumes)
        mean_volume = np.mean(volumes)
        median_volume = np.median(volumes)
        std_volume = np.std(volumes)
        
        # Volume distribution metrics
        max_volume = max(volumes)
        min_volume = min(volumes)
        range_volume = max_volume - min_volume
        
        # Concentration metrics
        top_10_pct_bins = int(len(bins) * 0.1) or 1
        sorted_volumes = sorted(volumes, reverse=True)
        top_10_pct_volume = sum(sorted_volumes[:top_10_pct_bins])
        concentration_ratio = (top_10_pct_volume / total_volume) * 100 if total_volume > 0 else 0
        
        # Profile completeness
        active_bins = sum(1 for vol in volumes if vol > 0)
        completeness = (active_bins / len(bins)) * 100 if len(bins) > 0 else 0
        
        return {
            'total_volume': float(total_volume),
            'mean_volume': round(mean_volume, 2),
            'median_volume': round(median_volume, 2),
            'std_volume': round(std_volume, 2),
            'max_volume': float(max_volume),
            'min_volume': float(min_volume),
            'volume_range': float(range_volume),
            'concentration_ratio': round(concentration_ratio, 2),
            'active_bins': active_bins,
            'total_bins': len(bins),
            'completeness_pct': round(completeness, 2),
            'coefficient_of_variation': round(std_volume / mean_volume, 3) if mean_volume > 0 else 0
        }
    
    # Helper methods
    def _format_volume_profile_data(self,
                                  volume_by_price: Dict[int, float],
                                  price_min: float,
                                  bin_size: float) -> List[Dict]:
        """Format volume profile data for output."""
        formatted_data = []
        
        for bin_idx in sorted(volume_by_price.keys()):
            price = price_min + (bin_idx * bin_size) + (bin_size / 2)
            volume = volume_by_price[bin_idx]
            
            formatted_data.append({
                'bin_index': bin_idx,
                'price_level': round(price, 5),
                'volume': round(volume, 2),
                'price_range': {
                    'low': round(price_min + (bin_idx * bin_size), 5),
                    'high': round(price_min + ((bin_idx + 1) * bin_size), 5)
                }
            })
        
        return formatted_data
    
    def _calculate_volume_concentration(self, volumes: List[float]) -> Dict:
        """Calculate volume concentration metrics."""
        if not volumes:
            return {'gini_coefficient': 0, 'concentration_category': 'no_data'}
        
        # Calculate Gini coefficient for volume concentration
        sorted_volumes = sorted(volumes)
        n = len(sorted_volumes)
        cumulative_volumes = np.cumsum(sorted_volumes)
        
        # Gini coefficient calculation
        gini = (2 * sum((i + 1) * vol for i, vol in enumerate(sorted_volumes))) / (n * sum(sorted_volumes)) - (n + 1) / n
        
        # Concentration category
        if gini > 0.8:
            concentration_category = 'very_high'
        elif gini > 0.6:
            concentration_category = 'high'
        elif gini > 0.4:
            concentration_category = 'moderate'
        elif gini > 0.2:
            concentration_category = 'low'
        else:
            concentration_category = 'very_low'
        
        return {
            'gini_coefficient': round(gini, 3),
            'concentration_category': concentration_category,
            'top_20_pct_volume_share': self._calculate_top_percentile_share(volumes, 0.2)
        }
    
    def _calculate_profile_width(self, volumes: List[float]) -> Dict:
        """Calculate profile width characteristics."""
        if not volumes:
            return {'effective_width': 0, 'width_category': 'no_data'}
        
        total_volume = sum(volumes)
        
        # Calculate effective width (number of bins with >1% of total volume)
        significant_bins = sum(1 for vol in volumes if vol > total_volume * 0.01)
        width_ratio = significant_bins / len(volumes)
        
        if width_ratio > 0.8:
            width_category = 'very_wide'
        elif width_ratio > 0.6:
            width_category = 'wide'
        elif width_ratio > 0.4:
            width_category = 'moderate'
        elif width_ratio > 0.2:
            width_category = 'narrow'
        else:
            width_category = 'very_narrow'
        
        return {
            'effective_width': significant_bins,
            'width_ratio': round(width_ratio, 3),
            'width_category': width_category,
            'total_bins': len(volumes)
        }
    
    def _analyze_surrounding_volume(self,
                                  volume_by_price: Dict[int, float],
                                  center_bin: int,
                                  bins: List[int]) -> Dict:
        """Analyze volume around a specific bin."""
        # Get surrounding bins (±2 bins)
        surrounding_bins = []
        center_index = bins.index(center_bin) if center_bin in bins else -1
        
        if center_index >= 0:
            start_idx = max(0, center_index - 2)
            end_idx = min(len(bins), center_index + 3)
            surrounding_bins = bins[start_idx:end_idx]
        
        surrounding_volume = sum(volume_by_price.get(bin_idx, 0) for bin_idx in surrounding_bins)
        center_volume = volume_by_price.get(center_bin, 0)
        
        # Calculate concentration
        concentration = (center_volume / surrounding_volume) * 100 if surrounding_volume > 0 else 0
        
        return {
            'surrounding_volume': float(surrounding_volume),
            'center_concentration_pct': round(concentration, 2),
            'surrounding_bins': len(surrounding_bins)
        }
    
    def _detect_profile_edge_signals(self,
                                   current_price: float,
                                   volume_by_price: Dict[int, float],
                                   recent_candles: pd.DataFrame) -> List[Dict]:
        """Detect signals at profile edges."""
        signals = []
        
        if not volume_by_price or len(recent_candles) < 3:
            return signals
        
        # Identify low-volume areas (potential profile edges)
        total_volume = sum(volume_by_price.values())
        avg_volume = total_volume / len(volume_by_price)
        
        low_volume_bins = {bin_idx: vol for bin_idx, vol in volume_by_price.items() 
                          if vol < avg_volume * 0.3}
        
        if low_volume_bins:
            # Check if current price is in low-volume area with momentum
            price_momentum = current_price - recent_candles['close'].iloc[0]
            momentum_pct = (price_momentum / current_price) * 100
            
            if abs(momentum_pct) > 1.0:  # Significant momentum
                signal_type = 'edge_momentum_up' if momentum_pct > 0 else 'edge_momentum_down'
                
                signals.append({
                    'type': signal_type,
                    'price': float(current_price),
                    'momentum_pct': round(momentum_pct, 2),
                    'strength': min(100, abs(momentum_pct) * 20),
                    'description': 'Price moving through low-volume area with momentum'
                })
        
        return signals
    
    def _assess_volume_profile_signal_quality(self,
                                            signals: Dict,
                                            poc_data: Dict,
                                            value_area_data: Dict) -> Dict:
        """Assess overall quality of volume profile signals."""
        total_signals = sum(len(signal_list) for signal_list in signals.values() 
                           if isinstance(signal_list, list))
        
        if total_signals == 0:
            return {'quality': 'no_signals', 'score': 0}
        
        # Quality based on POC strength and value area characteristics
        poc_strength = poc_data.get('poc_strength', 0)
        va_volume_pct = value_area_data.get('volume_percentage', 0)
        
        # Base quality on profile characteristics
        profile_quality = (poc_strength + va_volume_pct) / 2
        
        # Signal diversity bonus
        signal_types = sum(1 for signal_list in signals.values() 
                          if isinstance(signal_list, list) and len(signal_list) > 0)
        diversity_bonus = signal_types * 5
        
        quality_score = min(100, profile_quality + diversity_bonus)
        
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
            'signal_diversity': signal_types,
            'profile_strength': round(profile_quality, 2)
        }
    
    def _calculate_top_percentile_share(self, volumes: List[float], percentile: float) -> float:
        """Calculate what percentage of total volume is in top percentile of bins."""
        if not volumes:
            return 0
        
        sorted_volumes = sorted(volumes, reverse=True)
        top_n = int(len(sorted_volumes) * percentile) or 1
        top_volume = sum(sorted_volumes[:top_n])
        total_volume = sum(volumes)
        
        return round((top_volume / total_volume) * 100, 2) if total_volume > 0 else 0
    
    def _analyze_profile_evolution(self, profiles: Dict) -> Dict:
        """Analyze how volume profiles evolve over time."""
        if len(profiles) < 2:
            return {'evolution': 'insufficient_data'}
        
        # Compare POC levels over time
        poc_levels = []
        for profile in profiles.values():
            if 'poc' in profile and 'price' in profile['poc']:
                poc_levels.append(profile['poc']['price'])
        
        if len(poc_levels) < 2:
            return {'evolution': 'insufficient_poc_data'}
        
        # Calculate POC drift
        poc_changes = [poc_levels[i] - poc_levels[i-1] for i in range(1, len(poc_levels))]
        avg_poc_change = np.mean(poc_changes)
        poc_volatility = np.std(poc_changes)
        
        # Trend in POC movement
        if avg_poc_change > 0:
            poc_trend = 'upward_drift'
        elif avg_poc_change < 0:
            poc_trend = 'downward_drift'
        else:
            poc_trend = 'stable'
        
        return {
            'evolution': 'analyzed',
            'poc_trend': poc_trend,
            'avg_poc_change': round(avg_poc_change, 5),
            'poc_volatility': round(poc_volatility, 5),
            'total_sessions': len(profiles),
            'stability_score': round(max(0, 100 - poc_volatility * 1000), 2)
        }
    
    def _calculate_consensus_levels(self, profiles: Dict) -> List[Dict]:
        """Calculate consensus levels across multiple profiles."""
        if len(profiles) < 2:
            return []
        
        all_poc_levels = []
        all_vah_levels = []
        all_val_levels = []
        
        # Collect levels from all profiles
        for profile in profiles.values():
            if 'poc' in profile and 'price' in profile['poc']:
                all_poc_levels.append(profile['poc']['price'])
            if 'value_area' in profile:
                va = profile['value_area']
                if 'vah' in va:
                    all_vah_levels.append(va['vah'])
                if 'val' in va:
                    all_val_levels.append(va['val'])
        
        consensus_levels = []
        
        # Find clustering in POC levels
        if len(all_poc_levels) >= 3:
            poc_clusters = self._find_level_clusters(all_poc_levels)
            for cluster in poc_clusters:
                consensus_levels.append({
                    'level_type': 'consensus_poc',
                    'price': cluster['center'],
                    'frequency': cluster['count'],
                    'strength': round((cluster['count'] / len(all_poc_levels)) * 100, 2)
                })
        
        return consensus_levels[:5]  # Return top 5 consensus levels
    
    def _find_level_clusters(self, levels: List[float], tolerance_pct: float = 1.0) -> List[Dict]:
        """Find clusters of similar price levels."""
        if not levels:
            return []
        
        sorted_levels = sorted(levels)
        clusters = []
        current_cluster = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            # Check if level is within tolerance of current cluster
            cluster_center = np.mean(current_cluster)
            if abs(level - cluster_center) / cluster_center * 100 <= tolerance_pct:
                current_cluster.append(level)
            else:
                # Start new cluster
                if len(current_cluster) >= 2:  # Minimum cluster size
                    clusters.append({
                        'center': np.mean(current_cluster),
                        'count': len(current_cluster),
                        'range': max(current_cluster) - min(current_cluster)
                    })
                current_cluster = [level]
        
        # Add final cluster
        if len(current_cluster) >= 2:
            clusters.append({
                'center': np.mean(current_cluster),
                'count': len(current_cluster),
                'range': max(current_cluster) - min(current_cluster)
            })
        
        return sorted(clusters, key=lambda x: x['count'], reverse=True)
    
    def _generate_volume_profile_alerts(self,
                                       signals: Dict,
                                       poc_data: Dict,
                                       value_area_data: Dict) -> List[Dict]:
        """Generate alerts from volume profile analysis."""
        alerts = []
        
        # High-strength signal alerts
        for signal_type, signal_list in signals.items():
            if isinstance(signal_list, list):
                for signal in signal_list:
                    strength = signal.get('strength', 0)
                    if strength >= 70:
                        alerts.append({
                            'type': 'volume_profile_signal',
                            'signal_type': signal_type,
                            'signal_details': signal.get('type', 'unknown'),
                            'strength': strength,
                            'message': f"High-strength {signal_type} signal detected",
                            'priority': 'high' if strength >= 85 else 'medium'
                        })
        
        # POC strength alert
        poc_strength = poc_data.get('poc_strength', 0)
        if poc_strength >= 75:
            alerts.append({
                'type': 'poc_strength',
                'strength': poc_strength,
                'poc_price': poc_data.get('price', 0),
                'message': f"Strong Point of Control identified at {poc_data.get('price', 0):.5f}",
                'priority': 'medium'
            })
        
        # Value Area characteristics alert
        va_volume_pct = value_area_data.get('volume_percentage', 0)
        if va_volume_pct >= 80:  # Very concentrated value area
            alerts.append({
                'type': 'concentrated_value_area',
                'volume_percentage': va_volume_pct,
                'vah': value_area_data.get('vah', 0),
                'val': value_area_data.get('val', 0),
                'message': f"Highly concentrated value area ({va_volume_pct}% of volume)",
                'priority': 'medium'
            })
        
        return alerts