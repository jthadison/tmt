"""
Volume Profile Support/Resistance Detection Module

Implements volume-based level identification using Volume Profile analysis:
- Volume profile calculation for price levels
- Support/resistance zone identification using volume clusters  
- Dynamic zone strength calculation based on volume and touches
- Zone expansion/contraction tracking
- Zone break detection with volume confirmation
- Historical zone performance tracking
"""

from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@dataclass
class VolumeZone:
    """Represents a volume-based support/resistance zone"""
    level: float
    zone_type: str  # support, resistance, value_area_high, value_area_low, poc
    strength: Decimal  # 0-100 strength score
    volume: float
    touches: int
    first_established: datetime
    last_touched: datetime
    zone_range: Tuple[float, float]  # (low, high) of the zone
    

@dataclass
class VolumeProfileResult:
    """Complete volume profile analysis result"""
    point_of_control: float  # Price level with highest volume
    value_area_high: float
    value_area_low: float
    volume_zones: List[VolumeZone]
    profile_data: Dict  # Raw volume profile data
    analysis_period: Tuple[datetime, datetime]


class VolumeProfileAnalyzer:
    """Analyzes volume profile to identify support/resistance zones"""
    
    def __init__(self, 
                 bins: int = 50,
                 value_area_percentage: float = 0.70,
                 min_zone_strength: float = 20.0):
        self.bins = bins
        self.value_area_percentage = value_area_percentage
        self.min_zone_strength = min_zone_strength
        self.zone_history = []
    
    def calculate_volume_profile(self,
                               price_data: pd.DataFrame,
                               volume_data: pd.Series,
                               period_start: Optional[datetime] = None,
                               period_end: Optional[datetime] = None) -> VolumeProfileResult:
        """
        Calculate volume profile to identify high-volume price levels
        These levels act as support/resistance zones
        """
        if len(price_data) != len(volume_data):
            raise ValueError("Price data and volume data must have same length")
        
        if len(price_data) < 10:
            raise ValueError("Insufficient data for volume profile calculation")
        
        # Filter data by period if specified
        if period_start or period_end:
            mask = pd.Series([True] * len(price_data), index=price_data.index)
            if period_start:
                mask = mask & (price_data.index >= period_start)
            if period_end:
                mask = mask & (price_data.index <= period_end)
            price_data = price_data[mask]
            volume_data = volume_data[mask]
        
        # Calculate price range and bin size
        price_high = price_data['high'].max()
        price_low = price_data['low'].min()
        price_range = price_high - price_low
        bin_size = price_range / self.bins
        
        # Initialize volume profile
        volume_by_price = {}
        
        # Distribute volume across price levels for each candle
        for i, (idx, candle) in enumerate(price_data.iterrows()):
            volume = volume_data.iloc[i]
            
            # Distribute volume across the candle's price range
            price_levels = self._distribute_volume_across_range(
                candle['low'], candle['high'], volume, bin_size, price_low
            )
            
            for price_level, vol in price_levels.items():
                volume_by_price[price_level] = volume_by_price.get(price_level, 0) + vol
        
        # Identify high-volume nodes and calculate metrics
        profile_analysis = self._analyze_volume_profile(volume_by_price, price_low, bin_size)
        
        # Calculate value area
        value_area = self._calculate_value_area(volume_by_price, profile_analysis['poc'])
        
        # Identify volume zones
        volume_zones = self._identify_volume_zones(
            volume_by_price, price_data, volume_data, bin_size, price_low
        )
        
        return VolumeProfileResult(
            point_of_control=profile_analysis['poc'],
            value_area_high=value_area['high'],
            value_area_low=value_area['low'],
            volume_zones=volume_zones,
            profile_data={
                'volume_by_price': volume_by_price,
                'bin_size': bin_size,
                'price_range': (price_low, price_high),
                'total_volume': sum(volume_by_price.values())
            },
            analysis_period=(
                price_data.index[0] if len(price_data) > 0 else datetime.now(),
                price_data.index[-1] if len(price_data) > 0 else datetime.now()
            )
        )
    
    def identify_support_resistance_zones(self,
                                        price_data: pd.DataFrame,
                                        volume_data: pd.Series) -> Dict[str, List[VolumeZone]]:
        """
        Identify support and resistance zones using volume clusters
        
        Returns:
            Dict with 'support' and 'resistance' keys containing zone lists
        """
        volume_profile = self.calculate_volume_profile(price_data, volume_data)
        
        current_price = price_data['close'].iloc[-1]
        support_zones = []
        resistance_zones = []
        
        for zone in volume_profile.volume_zones:
            if zone.level < current_price:
                zone.zone_type = 'support'
                support_zones.append(zone)
            else:
                zone.zone_type = 'resistance'
                resistance_zones.append(zone)
        
        # Sort zones by strength (highest first)
        support_zones.sort(key=lambda x: x.strength, reverse=True)
        resistance_zones.sort(key=lambda x: x.strength, reverse=True)
        
        return {
            'support': support_zones,
            'resistance': resistance_zones,
            'all_zones': volume_profile.volume_zones
        }
    
    def calculate_zone_strength(self,
                               zone_level: float,
                               price_data: pd.DataFrame,
                               volume_data: pd.Series,
                               zone_range: Optional[Tuple[float, float]] = None) -> Dict:
        """
        Calculate dynamic zone strength based on volume and touches
        
        Factors:
        - Volume concentration at the level
        - Number of touches/tests
        - Reaction strength from the level
        - Time since last touch
        - Historical performance
        """
        if zone_range is None:
            tolerance = zone_level * 0.001  # 0.1% default tolerance
            zone_range = (zone_level - tolerance, zone_level + tolerance)
        
        # Find touches within the zone range
        touches = self._find_zone_touches(price_data, volume_data, zone_range)
        
        # Calculate volume strength
        volume_strength = self._calculate_volume_strength_at_zone(
            touches, volume_data.mean()
        )
        
        # Calculate reaction strength
        reaction_strength = self._calculate_reaction_strength(touches, price_data)
        
        # Calculate recency factor
        recency_factor = self._calculate_recency_factor(touches)
        
        # Calculate historical performance
        historical_performance = self._calculate_historical_performance(zone_level)
        
        # Overall strength score (0-100)
        strength_components = {
            'volume_strength': volume_strength,
            'touch_count': min(100, len(touches) * 15),  # 15 points per touch
            'reaction_strength': reaction_strength,
            'recency_factor': recency_factor,
            'historical_performance': historical_performance
        }
        
        # Weighted combination
        total_strength = (
            strength_components['volume_strength'] * 0.30 +
            strength_components['touch_count'] * 0.25 +
            strength_components['reaction_strength'] * 0.25 +
            strength_components['recency_factor'] * 0.10 +
            strength_components['historical_performance'] * 0.10
        )
        
        return {
            'strength': Decimal(str(round(total_strength, 2))),
            'components': strength_components,
            'touches': touches,
            'zone_range': zone_range
        }
    
    def track_zone_expansion_contraction(self,
                                       zones: List[VolumeZone],
                                       price_data: pd.DataFrame,
                                       volume_data: pd.Series) -> Dict:
        """
        Track zone expansion/contraction over time
        
        Zones can expand (become wider) or contract (become narrower)
        based on recent price action and volume distribution
        """
        zone_changes = {}
        
        for zone in zones:
            # Calculate recent volume distribution around the zone
            recent_period = min(20, len(price_data))
            recent_data = price_data.iloc[-recent_period:]
            recent_volume = volume_data.iloc[-recent_period:]
            
            # Find current zone boundaries based on recent activity
            current_boundaries = self._calculate_current_zone_boundaries(
                zone.level, recent_data, recent_volume
            )
            
            # Compare with historical boundaries
            original_width = zone.zone_range[1] - zone.zone_range[0]
            current_width = current_boundaries[1] - current_boundaries[0]
            
            expansion_ratio = current_width / original_width if original_width > 0 else 1.0
            
            zone_changes[zone.level] = {
                'original_range': zone.zone_range,
                'current_range': current_boundaries,
                'expansion_ratio': expansion_ratio,
                'change_type': self._classify_zone_change(expansion_ratio),
                'strength_change': self._calculate_strength_change(zone, expansion_ratio)
            }
        
        return zone_changes
    
    def detect_zone_breaks(self,
                          zones: List[VolumeZone],
                          price_data: pd.DataFrame,
                          volume_data: pd.Series) -> List[Dict]:
        """
        Detect zone breaks with volume confirmation
        
        A zone break occurs when:
        - Price closes decisively outside the zone
        - Volume confirms the break
        - Follow-through price action validates the break
        """
        zone_breaks = []
        
        if len(price_data) < 5:
            return zone_breaks
        
        # Analyze recent price action for breaks
        recent_period = min(10, len(price_data))
        
        for zone in zones:
            break_analysis = self._analyze_zone_break(
                zone, price_data.iloc[-recent_period:], volume_data.iloc[-recent_period:]
            )
            
            if break_analysis['break_detected']:
                zone_breaks.append({
                    'zone': zone,
                    'break_type': break_analysis['break_type'],  # upward, downward
                    'break_strength': break_analysis['strength'],
                    'volume_confirmation': break_analysis['volume_confirmation'],
                    'follow_through': break_analysis['follow_through'],
                    'break_time': break_analysis['break_time']
                })
        
        return zone_breaks
    
    def _distribute_volume_across_range(self,
                                       low: float,
                                       high: float,
                                       volume: float,
                                       bin_size: float,
                                       price_low: float) -> Dict[float, float]:
        """Distribute candle volume across its price range"""
        if high == low:
            # Single price level
            bin_index = int((low - price_low) / bin_size)
            price_level = price_low + (bin_index * bin_size)
            return {price_level: volume}
        
        # Multiple price levels
        price_levels = {}
        range_size = high - low
        
        # Determine how many bins this candle spans
        start_bin = int((low - price_low) / bin_size)
        end_bin = int((high - price_low) / bin_size)
        
        if start_bin == end_bin:
            # Single bin
            price_level = price_low + (start_bin * bin_size)
            price_levels[price_level] = volume
        else:
            # Multiple bins - distribute volume proportionally
            bins_spanned = end_bin - start_bin + 1
            volume_per_bin = volume / bins_spanned
            
            for bin_idx in range(start_bin, end_bin + 1):
                price_level = price_low + (bin_idx * bin_size)
                price_levels[price_level] = volume_per_bin
        
        return price_levels
    
    def _analyze_volume_profile(self, volume_by_price: Dict[float, float], price_low: float, bin_size: float) -> Dict:
        """Analyze volume profile to find key levels"""
        if not volume_by_price:
            return {'poc': price_low, 'max_volume': 0}
        
        # Find Point of Control (POC) - highest volume price level
        poc_price = max(volume_by_price.keys(), key=lambda x: volume_by_price[x])
        max_volume = volume_by_price[poc_price]
        
        return {
            'poc': poc_price,
            'max_volume': max_volume,
            'total_volume': sum(volume_by_price.values()),
            'price_levels': len(volume_by_price)
        }
    
    def _calculate_value_area(self, volume_by_price: Dict[float, float], poc: float) -> Dict[str, float]:
        """Calculate value area (area containing specified percentage of volume)"""
        if not volume_by_price:
            return {'high': poc, 'low': poc}
        
        total_volume = sum(volume_by_price.values())
        target_volume = total_volume * self.value_area_percentage
        
        # Sort price levels by volume (descending)
        sorted_levels = sorted(volume_by_price.items(), key=lambda x: x[1], reverse=True)
        
        # Build value area starting from highest volume levels
        value_area_volume = 0
        value_area_levels = []
        
        for price, volume in sorted_levels:
            value_area_volume += volume
            value_area_levels.append(price)
            
            if value_area_volume >= target_volume:
                break
        
        value_area_high = max(value_area_levels) if value_area_levels else poc
        value_area_low = min(value_area_levels) if value_area_levels else poc
        
        return {
            'high': value_area_high,
            'low': value_area_low,
            'volume': value_area_volume,
            'percentage': (value_area_volume / total_volume) * 100 if total_volume > 0 else 0
        }
    
    def _identify_volume_zones(self,
                              volume_by_price: Dict[float, float],
                              price_data: pd.DataFrame,
                              volume_data: pd.Series,
                              bin_size: float,
                              price_low: float) -> List[VolumeZone]:
        """Identify significant volume zones that can act as support/resistance"""
        if not volume_by_price:
            return []
        
        zones = []
        avg_volume = sum(volume_by_price.values()) / len(volume_by_price)
        
        # Sort by volume to find significant levels
        sorted_levels = sorted(volume_by_price.items(), key=lambda x: x[1], reverse=True)
        
        # Take top volume levels that exceed minimum threshold
        significant_levels = [
            (price, vol) for price, vol in sorted_levels 
            if vol >= avg_volume * 1.5  # At least 50% above average
        ]
        
        for i, (price_level, volume) in enumerate(significant_levels[:10]):  # Top 10 levels
            # Calculate zone strength
            zone_range = (price_level - bin_size/2, price_level + bin_size/2)
            strength_data = self.calculate_zone_strength(price_level, price_data, volume_data, zone_range)
            
            # Only include zones that meet minimum strength requirement
            if strength_data['strength'] >= self.min_zone_strength:
                zone = VolumeZone(
                    level=price_level,
                    zone_type='volume_cluster',
                    strength=strength_data['strength'],
                    volume=volume,
                    touches=len(strength_data['touches']),
                    first_established=price_data.index[0] if len(price_data) > 0 else datetime.now(),
                    last_touched=self._find_last_touch_time(strength_data['touches'], price_data),
                    zone_range=zone_range
                )
                zones.append(zone)
        
        return zones
    
    def _find_zone_touches(self,
                          price_data: pd.DataFrame,
                          volume_data: pd.Series,
                          zone_range: Tuple[float, float]) -> List[Dict]:
        """Find all touches of a zone within the price data"""
        touches = []
        zone_low, zone_high = zone_range
        
        for i, (idx, candle) in enumerate(price_data.iterrows()):
            # Check if candle touched the zone
            if (candle['low'] <= zone_high and candle['high'] >= zone_low):
                touch_info = {
                    'index': i,
                    'timestamp': idx,
                    'candle': candle,
                    'volume': volume_data.iloc[i] if i < len(volume_data) else 0,
                    'touch_type': self._classify_touch_type(candle, zone_range)
                }
                touches.append(touch_info)
        
        return touches
    
    def _classify_touch_type(self, candle: pd.Series, zone_range: Tuple[float, float]) -> str:
        """Classify the type of zone touch"""
        zone_low, zone_high = zone_range
        
        if candle['close'] > zone_high:
            return 'bounce_up'  # Touched zone from below and bounced up
        elif candle['close'] < zone_low:
            return 'bounce_down'  # Touched zone from above and bounced down
        elif zone_low <= candle['close'] <= zone_high:
            return 'inside'  # Closed inside the zone
        else:
            return 'test'  # General test of the zone
    
    def _calculate_volume_strength_at_zone(self, touches: List[Dict], avg_volume: float) -> float:
        """Calculate volume strength at zone touches"""
        if not touches or avg_volume == 0:
            return 0
        
        touch_volumes = [touch['volume'] for touch in touches]
        avg_touch_volume = sum(touch_volumes) / len(touch_volumes)
        volume_ratio = avg_touch_volume / avg_volume
        
        # Score based on volume expansion at touches
        return min(100, (volume_ratio - 0.5) * 100)  # Scale to 0-100
    
    def _calculate_reaction_strength(self, touches: List[Dict], price_data: pd.DataFrame) -> float:
        """Calculate reaction strength from zone touches"""
        if not touches:
            return 0
        
        reaction_scores = []
        
        for touch in touches:
            # Look for price reaction in next few candles
            touch_idx = touch['index']
            if touch_idx >= len(price_data) - 3:
                continue
            
            touch_price = touch['candle']['close']
            
            # Check reaction in next 1-3 candles
            max_reaction = 0
            for i in range(1, min(4, len(price_data) - touch_idx)):
                future_candle = price_data.iloc[touch_idx + i]
                
                # Calculate reaction size
                if touch['touch_type'] == 'bounce_up':
                    reaction = (future_candle['high'] - touch_price) / touch_price
                elif touch['touch_type'] == 'bounce_down':
                    reaction = (touch_price - future_candle['low']) / touch_price
                else:
                    reaction = abs(future_candle['close'] - touch_price) / touch_price
                
                max_reaction = max(max_reaction, reaction)
            
            reaction_scores.append(max_reaction * 1000)  # Scale to percentage points
        
        avg_reaction = sum(reaction_scores) / len(reaction_scores) if reaction_scores else 0
        return min(100, avg_reaction * 10)  # Scale to 0-100
    
    def _calculate_recency_factor(self, touches: List[Dict]) -> float:
        """Calculate recency factor for zone relevance"""
        if not touches:
            return 0
        
        # Find most recent touch
        try:
            most_recent = max(touches, key=lambda x: x['timestamp'])
            time_since_touch = datetime.now() - most_recent['timestamp']
        except (ValueError, KeyError):
            return 0
        
        # Score based on how recent the touch was (higher score for recent touches)
        days_since = time_since_touch.total_seconds() / (24 * 3600)
        
        if days_since <= 1:
            return 100
        elif days_since <= 7:
            return 80
        elif days_since <= 30:
            return 60
        elif days_since <= 90:
            return 40
        else:
            return 20
    
    def _calculate_historical_performance(self, zone_level: float) -> float:
        """Calculate historical performance of this zone"""
        # This would query historical data - simplified for now
        # In full implementation, would check historical success rate
        return 50  # Default neutral score
    
    def _find_last_touch_time(self, touches: List[Dict], price_data: pd.DataFrame) -> datetime:
        """Find timestamp of last touch"""
        if not touches:
            return price_data.index[0] if len(price_data) > 0 else datetime.now()
        
        return max(touch['timestamp'] for touch in touches)
    
    def _calculate_current_zone_boundaries(self,
                                         zone_level: float,
                                         price_data: pd.DataFrame,
                                         volume_data: pd.Series) -> Tuple[float, float]:
        """Calculate current zone boundaries based on recent activity"""
        # Find recent price action around the zone level
        tolerance = zone_level * 0.002  # 0.2% initial tolerance
        
        # Look for recent touches and calculate spread
        touches = []
        for i, (idx, candle) in enumerate(price_data.iterrows()):
            if abs(candle['low'] - zone_level) <= tolerance or abs(candle['high'] - zone_level) <= tolerance:
                touches.extend([candle['low'], candle['high']])
        
        if not touches:
            # No recent touches, use default range
            return (zone_level - tolerance, zone_level + tolerance)
        
        # Calculate boundaries based on recent touch spread
        touch_low = min(touches)
        touch_high = max(touches)
        
        # Add small buffer
        buffer = (touch_high - touch_low) * 0.1
        return (touch_low - buffer, touch_high + buffer)
    
    def _classify_zone_change(self, expansion_ratio: float) -> str:
        """Classify zone expansion/contraction"""
        if expansion_ratio > 1.2:
            return 'expanding'
        elif expansion_ratio < 0.8:
            return 'contracting'
        else:
            return 'stable'
    
    def _calculate_strength_change(self, zone: VolumeZone, expansion_ratio: float) -> Decimal:
        """Calculate how zone strength changes with expansion/contraction"""
        # Generally, contracting zones become stronger, expanding zones become weaker
        if expansion_ratio < 0.8:  # Contracting
            strength_change = (1.0 - expansion_ratio) * 20  # Up to 20% stronger
        elif expansion_ratio > 1.2:  # Expanding
            strength_change = -(expansion_ratio - 1.0) * 15  # Up to 15% weaker
        else:
            strength_change = 0
        
        new_strength = float(zone.strength) + strength_change
        return Decimal(str(max(0, min(100, new_strength))))
    
    def _analyze_zone_break(self,
                           zone: VolumeZone,
                           price_data: pd.DataFrame,
                           volume_data: pd.Series) -> Dict:
        """Analyze if a zone has been broken with confirmation"""
        zone_low, zone_high = zone.zone_range
        avg_volume = volume_data.mean()
        
        break_detected = False
        break_type = None
        break_strength = 0
        volume_confirmation = 0
        follow_through = 0
        break_time = None
        
        # Check each candle for potential breaks
        for i, (idx, candle) in enumerate(price_data.iterrows()):
            volume = volume_data.iloc[i]
            
            # Check for downward break (close below zone)
            if candle['close'] < zone_low:
                break_detected = True
                break_type = 'downward'
                break_time = idx
                
                # Calculate break strength
                penetration = (zone_low - candle['close']) / zone_low
                break_strength = min(100, penetration * 500)  # Scale to 0-100
                
                # Volume confirmation
                volume_confirmation = min(100, (volume / avg_volume) * 50) if avg_volume > 0 else 0
                
                # Check follow-through in remaining candles
                if i < len(price_data) - 1:
                    follow_through = self._calculate_follow_through(
                        price_data.iloc[i+1:], candle['close'], 'downward'
                    )
                break
                
            # Check for upward break (close above zone)
            elif candle['close'] > zone_high:
                break_detected = True
                break_type = 'upward'
                break_time = idx
                
                # Calculate break strength
                penetration = (candle['close'] - zone_high) / zone_high
                break_strength = min(100, penetration * 500)
                
                # Volume confirmation
                volume_confirmation = min(100, (volume / avg_volume) * 50) if avg_volume > 0 else 0
                
                # Check follow-through
                if i < len(price_data) - 1:
                    follow_through = self._calculate_follow_through(
                        price_data.iloc[i+1:], candle['close'], 'upward'
                    )
                break
        
        return {
            'break_detected': break_detected,
            'break_type': break_type,
            'strength': break_strength,
            'volume_confirmation': volume_confirmation,
            'follow_through': follow_through,
            'break_time': break_time
        }
    
    def _calculate_follow_through(self,
                                 future_data: pd.DataFrame,
                                 break_price: float,
                                 break_direction: str) -> float:
        """Calculate follow-through strength after zone break"""
        if len(future_data) == 0:
            return 0
        
        follow_through_scores = []
        
        for i, (idx, candle) in enumerate(future_data.iterrows()):
            if break_direction == 'upward':
                # Look for continued upward movement
                if candle['close'] > break_price:
                    score = ((candle['close'] - break_price) / break_price) * 100
                else:
                    score = -10  # Penalty for failure to follow through
            else:  # downward
                # Look for continued downward movement
                if candle['close'] < break_price:
                    score = ((break_price - candle['close']) / break_price) * 100
                else:
                    score = -10
            
            follow_through_scores.append(score)
            
            # Stop after 3 candles
            if i >= 2:
                break
        
        return sum(follow_through_scores) / len(follow_through_scores) if follow_through_scores else 0