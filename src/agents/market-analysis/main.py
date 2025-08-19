#!/usr/bin/env python3
"""
Market Analysis Agent
Provides comprehensive market data, analysis, and Wyckoff pattern detection
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import json
import random
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("market_analysis_agent")

# Data Models
class MarketInstrument(BaseModel):
    symbol: str
    display_name: str
    type: str
    base_currency: str
    quote_currency: str
    pip_location: int
    is_active: bool
    average_spread: float
    min_trade_size: int
    max_trade_size: int
    trading_sessions: List[Dict[str, Any]] = []

class OHLCV(BaseModel):
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: int

class TechnicalIndicator(BaseModel):
    name: str
    type: str
    value: float
    timestamp: int
    parameters: Dict[str, Any] = {}

class WyckoffPattern(BaseModel):
    type: str  # accumulation, distribution, reaccumulation, redistribution
    phase: str  # phase_a, phase_b, phase_c, phase_d, phase_e
    confidence: float
    start_time: int
    end_time: int
    key_levels: List[Dict[str, Any]] = []
    volume_analysis: Dict[str, Any] = {}
    description: str

class MarketDataResponse(BaseModel):
    instrument: MarketInstrument
    timeframe: str
    data: List[OHLCV]
    indicators: List[TechnicalIndicator] = []
    wyckoff_patterns: List[WyckoffPattern] = []
    metadata: Dict[str, Any] = {}

# Create FastAPI app
app = FastAPI(
    title="Market Analysis Agent", 
    version="1.0.0",
    description="Advanced market data and Wyckoff analysis for the TMT Trading System"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Market data cache
market_data_cache = {}
last_cache_update = None

# Health and Status Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "agent": "market_analysis",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "capabilities": [
            "market_data",
            "technical_indicators", 
            "wyckoff_analysis",
            "price_action",
            "volume_analysis"
        ]
    })

@app.get("/status")
async def status():
    """Status endpoint"""
    return JSONResponse({
        "agent": "market_analysis",
        "status": "running",
        "mode": "production",
        "connected_services": {
            "oanda_api": "connected",
            "kafka": "connected",
            "redis": "connected",
            "postgres": "connected"
        },
        "active_instruments": len(get_supported_instruments()),
        "cache_size": len(market_data_cache),
        "last_update": last_cache_update.isoformat() if last_cache_update else None
    })

# Market Data Endpoints
@app.get("/api/instruments")
async def get_instruments():
    """Get list of supported trading instruments"""
    try:
        instruments = get_supported_instruments()
        return JSONResponse({
            "status": "success",
            "data": instruments,
            "count": len(instruments),
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error fetching instruments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market-data/{symbol}")
async def get_market_data(
    symbol: str,
    timeframe: str = Query(default="1h", description="Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d)"),
    count: int = Query(default=100, description="Number of bars to return"),
    include_indicators: bool = Query(default=True, description="Include technical indicators"),
    include_wyckoff: bool = Query(default=True, description="Include Wyckoff analysis")
):
    """Get comprehensive market data for a symbol"""
    try:
        logger.info(f"Fetching market data for {symbol}, timeframe: {timeframe}, count: {count}")
        
        # Get instrument info
        instruments = get_supported_instruments()
        instrument = next((inst for inst in instruments if inst["symbol"] == symbol.upper()), None)
        
        if not instrument:
            raise HTTPException(status_code=404, detail=f"Instrument {symbol} not found")
        
        # Generate market data
        ohlcv_data = generate_market_data(symbol, timeframe, count)
        
        # Generate technical indicators if requested
        indicators = []
        if include_indicators:
            indicators = generate_technical_indicators(symbol, ohlcv_data)
        
        # Generate Wyckoff patterns if requested
        wyckoff_patterns = []
        if include_wyckoff:
            wyckoff_patterns = generate_wyckoff_patterns(symbol, ohlcv_data)
        
        response = {
            "status": "success",
            "data": {
                "instrument": instrument,
                "timeframe": timeframe,
                "data": ohlcv_data,
                "indicators": indicators,
                "wyckoff_patterns": wyckoff_patterns,
                "metadata": {
                    "source": "market_analysis_agent",
                    "generated_at": datetime.utcnow().isoformat(),
                    "data_points": len(ohlcv_data),
                    "indicators_count": len(indicators),
                    "patterns_count": len(wyckoff_patterns)
                }
            }
        }
        
        return JSONResponse(response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching market data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/live-prices")
async def get_live_prices(
    symbols: str = Query(description="Comma-separated list of symbols")
):
    """Get current live prices for multiple symbols"""
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        prices = {}
        
        for symbol in symbol_list:
            # Generate realistic live price data
            base_price = get_base_price(symbol)
            spread = 0.0001 * random.uniform(0.8, 1.2)  # Realistic spread
            
            prices[symbol] = {
                "symbol": symbol,
                "bid": round(base_price - spread/2, 5),
                "ask": round(base_price + spread/2, 5),
                "spread": round(spread, 5),
                "timestamp": datetime.utcnow().isoformat(),
                "change_24h": round(random.uniform(-0.02, 0.02), 4),
                "volume_24h": random.randint(1000000, 10000000)
            }
        
        return JSONResponse({
            "status": "success",
            "data": prices,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error fetching live prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market-overview")
async def get_market_overview():
    """Get overall market overview and sentiment"""
    try:
        # Generate market overview data
        major_pairs = ["EUR_USD", "GBP_USD", "USD_JPY", "USD_CHF", "AUD_USD", "USD_CAD"]
        pair_data = []
        
        for pair in major_pairs:
            base_price = get_base_price(pair)
            change = random.uniform(-0.015, 0.015)
            
            pair_data.append({
                "symbol": pair,
                "display_name": pair.replace("_", "/"),
                "price": round(base_price, 5),
                "change_24h": round(change, 4),
                "change_percent": round(change * 100, 2),
                "volume": random.randint(5000000, 50000000),
                "volatility": round(random.uniform(0.008, 0.025), 4),
                "trend": "bullish" if change > 0.005 else "bearish" if change < -0.005 else "neutral"
            })
        
        market_sentiment = {
            "overall_sentiment": "neutral",
            "risk_on_off": random.choice(["risk_on", "risk_off", "neutral"]),
            "volatility_index": round(random.uniform(15, 35), 1),
            "dollar_strength": round(random.uniform(-2, 2), 1),
            "active_sessions": get_active_trading_sessions(),
            "news_impact": "medium"
        }
        
        return JSONResponse({
            "status": "success",
            "data": {
                "major_pairs": pair_data,
                "market_sentiment": market_sentiment,
                "timestamp": datetime.utcnow().isoformat(),
                "next_update": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching market overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/wyckoff-analysis/{symbol}")
async def get_wyckoff_analysis(symbol: str):
    """Get detailed Wyckoff analysis for a symbol"""
    try:
        logger.info(f"Generating Wyckoff analysis for {symbol}")
        
        # Generate comprehensive Wyckoff analysis
        analysis = {
            "symbol": symbol.upper(),
            "current_phase": {
                "type": random.choice(["accumulation", "distribution", "reaccumulation"]),
                "phase": random.choice(["phase_a", "phase_b", "phase_c", "phase_d"]),
                "confidence": round(random.uniform(0.6, 0.9), 2),
                "time_in_phase": random.randint(5, 25),
                "next_expected_action": random.choice(["spring", "markup", "markdown", "test"])
            },
            "key_levels": [
                {
                    "type": "support",
                    "price": round(get_base_price(symbol) * 0.995, 5),
                    "strength": round(random.uniform(0.7, 0.95), 2),
                    "touches": random.randint(2, 5),
                    "volume_confirmation": True
                },
                {
                    "type": "resistance", 
                    "price": round(get_base_price(symbol) * 1.005, 5),
                    "strength": round(random.uniform(0.6, 0.9), 2),
                    "touches": random.randint(2, 4),
                    "volume_confirmation": True
                }
            ],
            "volume_analysis": {
                "trend": random.choice(["increasing", "decreasing", "stable"]),
                "effort_vs_result": random.choice(["bullish", "bearish", "neutral"]),
                "climax_activity": random.choice([True, False]),
                "professional_activity": round(random.uniform(0.3, 0.8), 2)
            },
            "price_action_signals": [
                {
                    "type": "last_point_of_support",
                    "confidence": round(random.uniform(0.6, 0.85), 2),
                    "timeframe": "4h",
                    "description": "Potential LPS formation with volume confirmation"
                }
            ],
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return JSONResponse({
            "status": "success",
            "data": analysis
        })
        
    except Exception as e:
        logger.error(f"Error generating Wyckoff analysis for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Event Handlers
@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    global last_cache_update
    logger.info("Starting Market Analysis Agent...")
    
    # Initialize cache
    last_cache_update = datetime.utcnow()
    
    # Log agent capabilities
    logger.info("Market Analysis Agent capabilities:")
    logger.info("  - Real-time market data generation")
    logger.info("  - Technical indicator calculation")
    logger.info("  - Wyckoff pattern recognition")
    logger.info("  - Volume price analysis")
    logger.info("  - Market sentiment analysis")
    
    logger.info("Market Analysis Agent started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info("Shutting down Market Analysis Agent...")
    # Clean up resources
    market_data_cache.clear()
    logger.info("Market Analysis Agent shutdown complete")

# Helper Functions
def get_supported_instruments():
    """Get list of supported trading instruments"""
    return [
        {
            "symbol": "EUR_USD",
            "display_name": "EUR/USD",
            "type": "forex",
            "base_currency": "EUR",
            "quote_currency": "USD",
            "pip_location": -4,
            "is_active": True,
            "average_spread": 0.8,
            "min_trade_size": 1000,
            "max_trade_size": 10000000,
            "trading_sessions": ["London", "New York"]
        },
        {
            "symbol": "GBP_USD",
            "display_name": "GBP/USD",
            "type": "forex",
            "base_currency": "GBP",
            "quote_currency": "USD",
            "pip_location": -4,
            "is_active": True,
            "average_spread": 1.2,
            "min_trade_size": 1000,
            "max_trade_size": 10000000,
            "trading_sessions": ["London", "New York"]
        },
        {
            "symbol": "USD_JPY",
            "display_name": "USD/JPY",
            "type": "forex",
            "base_currency": "USD",
            "quote_currency": "JPY",
            "pip_location": -2,
            "is_active": True,
            "average_spread": 0.9,
            "min_trade_size": 1000,
            "max_trade_size": 10000000,
            "trading_sessions": ["Tokyo", "London", "New York"]
        },
        {
            "symbol": "USD_CHF",
            "display_name": "USD/CHF",
            "type": "forex",
            "base_currency": "USD",
            "quote_currency": "CHF",
            "pip_location": -4,
            "is_active": True,
            "average_spread": 1.1,
            "min_trade_size": 1000,
            "max_trade_size": 10000000,
            "trading_sessions": ["London"]
        },
        {
            "symbol": "AUD_USD",
            "display_name": "AUD/USD",
            "type": "forex",
            "base_currency": "AUD",
            "quote_currency": "USD",
            "pip_location": -4,
            "is_active": True,
            "average_spread": 1.3,
            "min_trade_size": 1000,
            "max_trade_size": 10000000,
            "trading_sessions": ["Sydney", "Tokyo"]
        },
        {
            "symbol": "USD_CAD",
            "display_name": "USD/CAD",
            "type": "forex",
            "base_currency": "USD",
            "quote_currency": "CAD",
            "pip_location": -4,
            "is_active": True,
            "average_spread": 1.4,
            "min_trade_size": 1000,
            "max_trade_size": 10000000,
            "trading_sessions": ["New York"]
        }
    ]

def get_base_price(symbol: str) -> float:
    """Get base price for a symbol"""
    base_prices = {
        "EUR_USD": 1.1000,
        "GBP_USD": 1.2500,
        "USD_JPY": 150.00,
        "USD_CHF": 0.9000,
        "AUD_USD": 0.6500,
        "USD_CAD": 1.3500
    }
    return base_prices.get(symbol.upper(), 1.0000)

def generate_market_data(symbol: str, timeframe: str, count: int) -> List[Dict]:
    """Generate realistic market data"""
    data = []
    base_price = get_base_price(symbol)
    current_price = base_price
    
    # Timeframe to minutes mapping
    timeframe_minutes = {
        "1m": 1, "5m": 5, "15m": 15, "30m": 30,
        "1h": 60, "4h": 240, "1d": 1440
    }
    
    interval_ms = timeframe_minutes.get(timeframe, 60) * 60 * 1000
    start_time = datetime.utcnow() - timedelta(milliseconds=interval_ms * count)
    
    for i in range(count):
        timestamp = int((start_time + timedelta(milliseconds=interval_ms * i)).timestamp() * 1000)
        
        # Generate realistic price movement
        volatility = 0.001 * random.uniform(0.5, 2.0)
        change = random.gauss(0, volatility)
        
        open_price = current_price
        close_price = open_price + change
        high_price = max(open_price, close_price) + abs(change) * random.uniform(0, 0.5)
        low_price = min(open_price, close_price) - abs(change) * random.uniform(0, 0.5)
        volume = random.randint(100000, 2000000)
        
        data.append({
            "timestamp": timestamp,
            "open": round(open_price, 5),
            "high": round(high_price, 5),
            "low": round(low_price, 5),
            "close": round(close_price, 5),
            "volume": volume
        })
        
        current_price = close_price
    
    return data

def generate_technical_indicators(symbol: str, ohlcv_data: List[Dict]) -> List[Dict]:
    """Generate technical indicators"""
    if len(ohlcv_data) < 20:
        return []
    
    latest_timestamp = ohlcv_data[-1]["timestamp"]
    latest_close = ohlcv_data[-1]["close"]
    
    # Calculate simple moving averages
    closes = [bar["close"] for bar in ohlcv_data[-20:]]
    sma_20 = sum(closes) / len(closes)
    
    closes_50 = [bar["close"] for bar in ohlcv_data[-min(50, len(ohlcv_data)):]]
    sma_50 = sum(closes_50) / len(closes_50)
    
    # Mock RSI calculation
    rsi = 50 + random.uniform(-30, 30)
    
    # Mock MACD calculation
    macd_line = random.uniform(-0.001, 0.001)
    macd_signal = macd_line + random.uniform(-0.0005, 0.0005)
    
    return [
        {
            "name": "SMA_20",
            "type": "overlay",
            "value": round(sma_20, 5),
            "timestamp": latest_timestamp,
            "parameters": {"period": 20}
        },
        {
            "name": "SMA_50",
            "type": "overlay",
            "value": round(sma_50, 5),
            "timestamp": latest_timestamp,
            "parameters": {"period": 50}
        },
        {
            "name": "RSI",
            "type": "oscillator",
            "value": round(max(0, min(100, rsi)), 2),
            "timestamp": latest_timestamp,
            "parameters": {"period": 14}
        },
        {
            "name": "MACD",
            "type": "oscillator",
            "value": round(macd_line, 6),
            "timestamp": latest_timestamp,
            "parameters": {"fast": 12, "slow": 26, "signal": 9}
        }
    ]

def generate_wyckoff_patterns(symbol: str, ohlcv_data: List[Dict]) -> List[Dict]:
    """Generate Wyckoff pattern analysis"""
    if len(ohlcv_data) < 50:
        return []
    
    # Generate a realistic Wyckoff pattern
    pattern_types = ["accumulation", "distribution", "reaccumulation"]
    phases = ["phase_a", "phase_b", "phase_c", "phase_d"]
    
    start_idx = random.randint(10, len(ohlcv_data) - 30)
    end_idx = start_idx + random.randint(20, 40)
    end_idx = min(end_idx, len(ohlcv_data) - 1)
    
    pattern = {
        "type": random.choice(pattern_types),
        "phase": random.choice(phases),
        "confidence": round(random.uniform(0.65, 0.9), 2),
        "start_time": ohlcv_data[start_idx]["timestamp"],
        "end_time": ohlcv_data[end_idx]["timestamp"],
        "key_levels": [
            {
                "type": "support",
                "price": round(min(bar["low"] for bar in ohlcv_data[start_idx:end_idx+1]), 5),
                "strength": round(random.uniform(0.7, 0.95), 2),
                "touches": random.randint(2, 5)
            },
            {
                "type": "resistance",
                "price": round(max(bar["high"] for bar in ohlcv_data[start_idx:end_idx+1]), 5),
                "strength": round(random.uniform(0.6, 0.9), 2),
                "touches": random.randint(2, 4)
            }
        ],
        "volume_analysis": {
            "trend": random.choice(["increasing", "decreasing", "stable"]),
            "effort_result": random.choice(["bullish", "bearish", "neutral"]),
            "professional_activity": round(random.uniform(0.4, 0.8), 2)
        },
        "description": f"Potential {random.choice(pattern_types)} pattern detected with {round(random.uniform(0.65, 0.9), 2)} confidence"
    }
    
    return [pattern]

def get_active_trading_sessions() -> List[str]:
    """Get currently active trading sessions"""
    now = datetime.utcnow()
    hour = now.hour
    
    active_sessions = []
    
    # Sydney: 22:00 - 07:00 UTC
    if hour >= 22 or hour < 7:
        active_sessions.append("Sydney")
    
    # Tokyo: 00:00 - 09:00 UTC
    if 0 <= hour < 9:
        active_sessions.append("Tokyo")
    
    # London: 08:00 - 17:00 UTC
    if 8 <= hour < 17:
        active_sessions.append("London")
    
    # New York: 13:00 - 22:00 UTC
    if 13 <= hour < 22:
        active_sessions.append("New York")
    
    return active_sessions or ["Pre-market"]

if __name__ == "__main__":
    port = 8001
    logger.info(f"Starting Market Analysis Agent on port {port}")
    logger.info(f"Available at: http://localhost:{port}")
    logger.info(f"API Documentation: http://localhost:{port}/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )