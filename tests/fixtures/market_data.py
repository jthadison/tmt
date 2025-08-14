"""
Market data fixtures for testing
"""
from datetime import datetime, timedelta
from typing import Dict, List
import random


def generate_ohlcv_data(
    symbol: str = "EURUSD",
    start_price: float = 1.0850,
    bars: int = 100,
    timeframe: str = "M15"
) -> List[Dict]:
    """Generate OHLCV data for testing"""
    
    data = []
    current_price = start_price
    current_time = datetime.now()
    
    for i in range(bars):
        # Generate realistic price movement
        change = random.uniform(-0.0020, 0.0020)  # ±20 pips
        
        open_price = current_price
        close_price = current_price + change
        
        # Ensure high >= max(open, close) and low <= min(open, close)
        high_offset = random.uniform(0, 0.0010)  # Up to 10 pips above
        low_offset = random.uniform(0, 0.0010)   # Up to 10 pips below
        
        high_price = max(open_price, close_price) + high_offset
        low_price = min(open_price, close_price) - low_offset
        
        volume = random.randint(1000, 10000)
        
        bar = {
            "symbol": symbol,
            "timestamp": current_time.isoformat(),
            "timeframe": timeframe,
            "open": round(open_price, 5),
            "high": round(high_price, 5),
            "low": round(low_price, 5),
            "close": round(close_price, 5),
            "volume": volume
        }
        
        data.append(bar)
        current_price = close_price
        current_time += timedelta(minutes=15)
    
    return data


def generate_tick_data(
    symbol: str = "EURUSD",
    base_price: float = 1.0850,
    ticks: int = 1000,
    spread: float = 0.00015
) -> List[Dict]:
    """Generate tick data for testing"""
    
    data = []
    current_price = base_price
    current_time = datetime.now()
    
    for i in range(ticks):
        # Small price movements typical of forex ticks
        change = random.uniform(-0.00005, 0.00005)  # ±0.5 pips
        current_price += change
        
        bid = round(current_price, 5)
        ask = round(current_price + spread, 5)
        
        tick = {
            "symbol": symbol,
            "timestamp": current_time.isoformat(),
            "bid": bid,
            "ask": ask,
            "volume": random.randint(1, 100)
        }
        
        data.append(tick)
        current_time += timedelta(milliseconds=100)
    
    return data


def generate_wyckoff_accumulation_pattern() -> List[Dict]:
    """Generate market data showing Wyckoff accumulation pattern"""
    
    # Accumulation phases
    phases = [
        {"name": "Phase A - Selling Climax", "bars": 20, "trend": "down", "volume": "high"},
        {"name": "Phase B - Building Cause", "bars": 40, "trend": "sideways", "volume": "declining"},
        {"name": "Phase C - Spring", "bars": 10, "trend": "down_fake", "volume": "low"},
        {"name": "Phase D - Signs of Strength", "bars": 15, "trend": "up", "volume": "increasing"},
        {"name": "Phase E - Mark Up", "bars": 25, "trend": "strong_up", "volume": "high"}
    ]
    
    data = []
    current_price = 1.0900
    current_time = datetime.now()
    
    for phase in phases:
        for i in range(phase["bars"]):
            if phase["trend"] == "down":
                change = random.uniform(-0.0050, -0.0010)
            elif phase["trend"] == "up":
                change = random.uniform(0.0010, 0.0030)
            elif phase["trend"] == "strong_up":
                change = random.uniform(0.0030, 0.0080)
            elif phase["trend"] == "down_fake":
                change = random.uniform(-0.0080, -0.0030)
            else:  # sideways
                change = random.uniform(-0.0015, 0.0015)
            
            open_price = current_price
            close_price = current_price + change
            
            # Volume characteristics
            if phase["volume"] == "high":
                volume = random.randint(5000, 15000)
            elif phase["volume"] == "low":
                volume = random.randint(500, 2000)
            elif phase["volume"] == "increasing":
                volume = random.randint(2000 + i*100, 8000 + i*200)
            else:  # declining
                volume = random.randint(5000 - i*50, 8000 - i*100)
            
            high_price = max(open_price, close_price) + random.uniform(0, 0.0005)
            low_price = min(open_price, close_price) - random.uniform(0, 0.0005)
            
            bar = {
                "symbol": "EURUSD",
                "timestamp": current_time.isoformat(),
                "timeframe": "H1",
                "open": round(open_price, 5),
                "high": round(high_price, 5),
                "low": round(low_price, 5),
                "close": round(close_price, 5),
                "volume": volume,
                "wyckoff_phase": phase["name"]
            }
            
            data.append(bar)
            current_price = close_price
            current_time += timedelta(hours=1)
    
    return data


def generate_news_events() -> List[Dict]:
    """Generate news events for testing"""
    
    return [
        {
            "timestamp": datetime.now().isoformat(),
            "currency": "USD",
            "event": "Non-Farm Payrolls",
            "impact": "high",
            "forecast": "150K",
            "actual": "180K",
            "previous": "140K"
        },
        {
            "timestamp": (datetime.now() + timedelta(hours=2)).isoformat(),
            "currency": "EUR",
            "event": "ECB Interest Rate Decision",
            "impact": "high",
            "forecast": "4.50%",
            "actual": None,
            "previous": "4.50%"
        },
        {
            "timestamp": (datetime.now() + timedelta(hours=4)).isoformat(),
            "currency": "GBP",
            "event": "GDP Growth Rate",
            "impact": "medium",
            "forecast": "0.2%",
            "actual": None,
            "previous": "0.1%"
        }
    ]


# Market state fixtures
TRENDING_MARKET = {
    "state": "trending",
    "direction": "bullish",
    "strength": 0.75,
    "volatility": "normal",
    "volume_profile": "increasing"
}

RANGING_MARKET = {
    "state": "ranging",
    "direction": "sideways",
    "strength": 0.25,
    "volatility": "low",
    "volume_profile": "declining"
}

VOLATILE_MARKET = {
    "state": "volatile",
    "direction": "uncertain",
    "strength": 0.45,
    "volatility": "high",
    "volume_profile": "erratic"
}


def get_market_state_fixture(state_type: str) -> Dict:
    """Get market state fixture by type"""
    states = {
        "trending": TRENDING_MARKET,
        "ranging": RANGING_MARKET,
        "volatile": VOLATILE_MARKET
    }
    return states.get(state_type, TRENDING_MARKET)


# Symbol configurations for testing
TEST_SYMBOLS = {
    "EURUSD": {
        "pip_value": 0.00001,
        "min_lot": 0.01,
        "max_lot": 100.0,
        "spread_avg": 0.00015,
        "session_active": ["london", "newyork"]
    },
    "GBPUSD": {
        "pip_value": 0.00001,
        "min_lot": 0.01,
        "max_lot": 100.0,
        "spread_avg": 0.00020,
        "session_active": ["london", "newyork"]
    },
    "USDJPY": {
        "pip_value": 0.001,
        "min_lot": 0.01,
        "max_lot": 100.0,
        "spread_avg": 0.015,
        "session_active": ["asian", "newyork"]
    },
    "XAUUSD": {
        "pip_value": 0.01,
        "min_lot": 0.01,
        "max_lot": 10.0,
        "spread_avg": 0.50,
        "session_active": ["london", "newyork"]
    }
}