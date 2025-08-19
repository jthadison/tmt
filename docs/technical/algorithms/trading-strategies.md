# Trading Strategy Logic

## Overview

The TMT system employs a sophisticated multi-layered trading strategy based on Wyckoff methodology combined with Volume Price Analysis (VPA) and Smart Money Concepts (SMC). This document details the core trading logic, decision trees, and strategy implementation.

## Core Trading Philosophy

### Wyckoff Methodology Foundation
The system is built on Wyckoff principles of market structure analysis:

1. **Supply and Demand**: Understanding accumulation and distribution phases
2. **Cause and Effect**: Market movements have underlying causes reflected in volume
3. **Effort vs Result**: Analyzing volume in relation to price movement
4. **Market Structure**: Identifying phases of accumulation, markup, distribution, and markdown

### Smart Money Concepts Integration
- **Order Blocks**: Identifying institutional order placement zones
- **Fair Value Gaps**: Detecting imbalances requiring price retracement
- **Liquidity Zones**: Understanding where stop losses and orders cluster
- **Market Structure Breaks**: Confirming trend changes through structure analysis

## Strategy Decision Tree

```
Market Data Input
│
├─ Volume Price Analysis
│  ├─ Volume Spike Detection
│  ├─ Divergence Analysis
│  └─ Volume Profile Analysis
│
├─ Wyckoff Phase Detection
│  ├─ Accumulation Phase
│  │  ├─ Phase A: Stopping Action
│  │  ├─ Phase B: Building Cause
│  │  ├─ Phase C: Spring Test
│  │  └─ Phase D: Signs of Strength
│  │
│  ├─ Markup Phase
│  │  ├─ Phase E: Markup Begins
│  │  └─ Trend Continuation Signals
│  │
│  ├─ Distribution Phase
│  │  ├─ Phase A: Preliminary Supply
│  │  ├─ Phase B: Public Participation
│  │  ├─ Phase C: Upthrust Test
│  │  └─ Phase D: Signs of Weakness
│  │
│  └─ Markdown Phase
│      ├─ Phase E: Markdown Begins
│      └─ Trend Continuation Signals
│
├─ Smart Money Concepts
│  ├─ Order Block Identification
│  ├─ Fair Value Gap Detection
│  ├─ Liquidity Zone Mapping
│  └─ Break of Structure Analysis
│
├─ Market State Assessment
│  ├─ Trending Market
│  ├─ Ranging Market
│  ├─ High Volatility
│  └─ Low Volatility
│
└─ Signal Generation
   ├─ Entry Signal Confirmation
   ├─ Risk Assessment
   ├─ Position Sizing Calculation
   └─ Exit Strategy Definition
```

## Signal Generation Logic

### Entry Signal Requirements

#### Long Entry Criteria
```python
def generate_long_signal(market_data):
    """
    Generate long entry signal based on Wyckoff and SMC analysis
    """
    criteria = {
        'wyckoff_bullish': check_wyckoff_bullish_conditions(market_data),
        'volume_confirmation': verify_volume_support(market_data),
        'order_block_support': identify_bullish_order_block(market_data),
        'structure_break': confirm_bullish_structure_break(market_data),
        'fair_value_gap': check_bullish_fvg(market_data),
        'risk_reward_ratio': calculate_risk_reward(market_data) >= 2.0
    }
    
    # Require at least 4 out of 6 criteria for signal generation
    confirmed_criteria = sum(criteria.values())
    
    if confirmed_criteria >= 4:
        return generate_entry_signal('LONG', market_data, criteria)
    
    return None
```

#### Short Entry Criteria
```python
def generate_short_signal(market_data):
    """
    Generate short entry signal based on Wyckoff and SMC analysis
    """
    criteria = {
        'wyckoff_bearish': check_wyckoff_bearish_conditions(market_data),
        'volume_confirmation': verify_volume_resistance(market_data),
        'order_block_resistance': identify_bearish_order_block(market_data),
        'structure_break': confirm_bearish_structure_break(market_data),
        'fair_value_gap': check_bearish_fvg(market_data),
        'risk_reward_ratio': calculate_risk_reward(market_data) >= 2.0
    }
    
    # Require at least 4 out of 6 criteria for signal generation
    confirmed_criteria = sum(criteria.values())
    
    if confirmed_criteria >= 4:
        return generate_entry_signal('SHORT', market_data, criteria)
    
    return None
```

### Wyckoff Phase Detection Algorithms

#### Accumulation Phase Detection
```python
class AccumulationDetector:
    def __init__(self):
        self.lookback_period = 100
        self.volume_threshold = 1.5  # 150% of average volume
        
    def detect_phase_a(self, price_data, volume_data):
        """
        Phase A: Preliminary Support and Selling Climax
        """
        # Look for high volume selling with support appearing
        selling_climax = self.identify_selling_climax(price_data, volume_data)
        preliminary_support = self.find_preliminary_support(price_data)
        
        return selling_climax and preliminary_support
    
    def detect_phase_b(self, price_data, volume_data):
        """
        Phase B: Building the Cause
        """
        # Look for sideways movement with decreasing volume
        sideways_movement = self.check_sideways_movement(price_data)
        decreasing_volume = self.analyze_volume_trend(volume_data, 'decreasing')
        
        return sideways_movement and decreasing_volume
    
    def detect_phase_c(self, price_data, volume_data):
        """
        Phase C: Spring Test
        """
        # Look for break below support on low volume followed by recovery
        spring_action = self.identify_spring(price_data, volume_data)
        return spring_action
    
    def detect_phase_d(self, price_data, volume_data):
        """
        Phase D: Signs of Strength
        """
        # Look for higher highs and lows with increasing volume
        higher_highs = self.check_higher_highs(price_data)
        higher_lows = self.check_higher_lows(price_data)
        increasing_volume = self.analyze_volume_trend(volume_data, 'increasing')
        
        return higher_highs and higher_lows and increasing_volume
```

#### Distribution Phase Detection
```python
class DistributionDetector:
    def __init__(self):
        self.lookback_period = 100
        self.volume_threshold = 1.5
        
    def detect_phase_a(self, price_data, volume_data):
        """
        Phase A: Preliminary Supply and Buying Climax
        """
        buying_climax = self.identify_buying_climax(price_data, volume_data)
        preliminary_supply = self.find_preliminary_supply(price_data)
        
        return buying_climax and preliminary_supply
    
    def detect_phase_b(self, price_data, volume_data):
        """
        Phase B: Public Participation
        """
        sideways_movement = self.check_sideways_movement(price_data)
        mixed_volume = self.analyze_volume_pattern(volume_data, 'mixed')
        
        return sideways_movement and mixed_volume
    
    def detect_phase_c(self, price_data, volume_data):
        """
        Phase C: Upthrust Test
        """
        upthrust_action = self.identify_upthrust(price_data, volume_data)
        return upthrust_action
    
    def detect_phase_d(self, price_data, volume_data):
        """
        Phase D: Signs of Weakness
        """
        lower_highs = self.check_lower_highs(price_data)
        lower_lows = self.check_lower_lows(price_data)
        increasing_volume = self.analyze_volume_trend(volume_data, 'increasing')
        
        return lower_highs and lower_lows and increasing_volume
```

### Volume Price Analysis Implementation

#### Volume Divergence Detection
```python
class VolumeDivergenceAnalyzer:
    def __init__(self):
        self.period = 20
        self.divergence_threshold = 0.3
    
    def detect_bullish_divergence(self, price_data, volume_data):
        """
        Detect bullish divergence: Price making lower lows, volume making higher lows
        """
        price_trend = self.calculate_trend(price_data[-self.period:])
        volume_trend = self.calculate_trend(volume_data[-self.period:])
        
        if price_trend < -self.divergence_threshold and volume_trend > 0:
            return True
        return False
    
    def detect_bearish_divergence(self, price_data, volume_data):
        """
        Detect bearish divergence: Price making higher highs, volume making lower highs
        """
        price_trend = self.calculate_trend(price_data[-self.period:])
        volume_trend = self.calculate_trend(volume_data[-self.period:])
        
        if price_trend > self.divergence_threshold and volume_trend < 0:
            return True
        return False
```

#### Volume Profile Analysis
```python
class VolumeProfileAnalyzer:
    def __init__(self):
        self.profile_period = 50
        self.poc_threshold = 0.3  # Point of Control threshold
    
    def calculate_volume_profile(self, price_data, volume_data):
        """
        Calculate volume profile for the given period
        """
        price_levels = self.create_price_levels(price_data)
        volume_at_price = self.aggregate_volume_by_price(price_data, volume_data, price_levels)
        
        poc = self.find_point_of_control(volume_at_price)
        value_area = self.calculate_value_area(volume_at_price, 0.68)  # 68% of volume
        
        return {
            'poc': poc,
            'value_area_high': value_area['high'],
            'value_area_low': value_area['low'],
            'volume_profile': volume_at_price
        }
    
    def identify_support_resistance(self, volume_profile):
        """
        Identify key support and resistance levels from volume profile
        """
        high_volume_nodes = self.find_high_volume_nodes(volume_profile)
        low_volume_nodes = self.find_low_volume_nodes(volume_profile)
        
        return {
            'support_levels': high_volume_nodes,
            'resistance_levels': high_volume_nodes,
            'breakout_levels': low_volume_nodes
        }
```

### Smart Money Concepts Implementation

#### Order Block Detection
```python
class OrderBlockDetector:
    def __init__(self):
        self.min_impulse_strength = 0.5  # Minimum pip movement for impulse
        self.retracement_threshold = 0.618  # Fibonacci retracement level
    
    def identify_bullish_order_block(self, price_data):
        """
        Identify bullish order blocks (institutional buying zones)
        """
        # Find strong bullish impulse moves
        impulse_moves = self.find_bullish_impulses(price_data)
        
        order_blocks = []
        for impulse in impulse_moves:
            # Order block is the last bearish candle before the impulse
            order_block = self.find_last_bearish_candle(price_data, impulse['start'])
            if order_block:
                order_blocks.append({
                    'high': order_block['high'],
                    'low': order_block['low'],
                    'strength': impulse['strength'],
                    'timestamp': order_block['timestamp']
                })
        
        return order_blocks
    
    def identify_bearish_order_block(self, price_data):
        """
        Identify bearish order blocks (institutional selling zones)
        """
        # Find strong bearish impulse moves
        impulse_moves = self.find_bearish_impulses(price_data)
        
        order_blocks = []
        for impulse in impulse_moves:
            # Order block is the last bullish candle before the impulse
            order_block = self.find_last_bullish_candle(price_data, impulse['start'])
            if order_block:
                order_blocks.append({
                    'high': order_block['high'],
                    'low': order_block['low'],
                    'strength': impulse['strength'],
                    'timestamp': order_block['timestamp']
                })
        
        return order_blocks
```

#### Fair Value Gap Detection
```python
class FairValueGapDetector:
    def __init__(self):
        self.min_gap_size = 0.0010  # Minimum gap size in price units
    
    def detect_bullish_fvg(self, price_data):
        """
        Detect bullish fair value gaps (imbalances to the upside)
        """
        gaps = []
        
        for i in range(2, len(price_data)):
            current = price_data[i]
            previous = price_data[i-1]
            two_back = price_data[i-2]
            
            # Bullish FVG: Current low > Two periods back high
            if current['low'] > two_back['high']:
                gap_size = current['low'] - two_back['high']
                if gap_size >= self.min_gap_size:
                    gaps.append({
                        'high': current['low'],
                        'low': two_back['high'],
                        'size': gap_size,
                        'timestamp': current['timestamp'],
                        'filled': False
                    })
        
        return gaps
    
    def detect_bearish_fvg(self, price_data):
        """
        Detect bearish fair value gaps (imbalances to the downside)
        """
        gaps = []
        
        for i in range(2, len(price_data)):
            current = price_data[i]
            previous = price_data[i-1]
            two_back = price_data[i-2]
            
            # Bearish FVG: Current high < Two periods back low
            if current['high'] < two_back['low']:
                gap_size = two_back['low'] - current['high']
                if gap_size >= self.min_gap_size:
                    gaps.append({
                        'high': two_back['low'],
                        'low': current['high'],
                        'size': gap_size,
                        'timestamp': current['timestamp'],
                        'filled': False
                    })
        
        return gaps
```

## Risk Management Integration

### Position Sizing Algorithm
```python
def calculate_position_size(account_balance, risk_percentage, entry_price, stop_loss_price):
    """
    Calculate position size based on risk management rules
    """
    risk_amount = account_balance * (risk_percentage / 100)
    stop_loss_distance = abs(entry_price - stop_loss_price)
    
    if stop_loss_distance == 0:
        return 0
    
    position_size = risk_amount / stop_loss_distance
    
    # Apply maximum position size limits
    max_position = account_balance * 0.1  # Maximum 10% of account per trade
    position_size = min(position_size, max_position)
    
    return round(position_size, 2)
```

### Dynamic Stop Loss Management
```python
class DynamicStopLossManager:
    def __init__(self):
        self.atr_period = 14
        self.breakeven_threshold = 1.0  # Move to breakeven after 1:1 RR
        
    def calculate_initial_stop_loss(self, entry_price, direction, atr_value):
        """
        Calculate initial stop loss based on ATR
        """
        stop_multiplier = 1.5  # 1.5x ATR for stop loss
        
        if direction == 'LONG':
            stop_loss = entry_price - (atr_value * stop_multiplier)
        else:  # SHORT
            stop_loss = entry_price + (atr_value * stop_multiplier)
            
        return stop_loss
    
    def update_trailing_stop(self, current_price, entry_price, current_stop, direction, atr_value):
        """
        Update trailing stop loss
        """
        trail_distance = atr_value * 1.0  # 1x ATR for trailing
        
        if direction == 'LONG':
            new_stop = current_price - trail_distance
            return max(current_stop, new_stop)  # Only move stop up
        else:  # SHORT
            new_stop = current_price + trail_distance
            return min(current_stop, new_stop)  # Only move stop down
```

## Strategy Performance Metrics

### Key Performance Indicators
- **Win Rate**: Target ≥ 55%
- **Risk-Reward Ratio**: Target ≥ 1:2
- **Maximum Drawdown**: Target ≤ 8%
- **Profit Factor**: Target ≥ 1.5
- **Sharpe Ratio**: Target ≥ 1.2

### Strategy Validation Requirements
1. **Backtesting Period**: Minimum 2 years of historical data
2. **Walk-Forward Analysis**: 6-month training, 3-month testing periods
3. **Monte Carlo Simulation**: 1000+ iterations for robustness testing
4. **Out-of-Sample Testing**: 20% of data reserved for final validation

## Continuous Improvement Framework

### Strategy Adaptation Triggers
- Performance degradation below thresholds
- Market regime changes detected
- New pattern discoveries through machine learning
- External market event impacts

### Learning Integration Points
- Pattern recognition improvements
- Parameter optimization through genetic algorithms
- Market state detection enhancements
- Risk management rule refinements

For implementation details and code examples, see the corresponding agent documentation in `/src/agents/`.