"""
Market Data Interface

Abstract interface for market data providers, allowing seamless switching
between mock data (development/testing) and real market data (production).
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class MarketDataPoint:
    """Represents a single market data point"""
    timestamp: datetime
    price: Decimal
    volume: Decimal
    volatility: Decimal
    trend_strength: Decimal


@dataclass 
class MarketRegimeData:
    """Represents market regime analysis data"""
    regime_type: str  # 'trending', 'ranging', 'volatile'
    confidence: float
    trend_direction: Optional[str]  # 'up', 'down', None for ranging
    volatility_level: str  # 'low', 'medium', 'high'
    last_updated: datetime


class MarketDataInterface(ABC):
    """Abstract interface for market data providers"""
    
    @abstractmethod
    async def get_current_price(self, symbol: str) -> Decimal:
        """Get current market price for a symbol"""
        pass
    
    @abstractmethod
    async def get_market_data_point(self, symbol: str) -> MarketDataPoint:
        """Get comprehensive market data for a symbol"""
        pass
    
    @abstractmethod
    async def get_regime_analysis(self, symbol: str) -> MarketRegimeData:
        """Get market regime analysis for a symbol"""
        pass
    
    @abstractmethod
    async def get_historical_data(self, symbol: str, timeframe: str, count: int) -> List[MarketDataPoint]:
        """Get historical market data"""
        pass


class MockMarketDataProvider(MarketDataInterface):
    """Mock implementation for development and testing"""
    
    def __init__(self):
        self._mock_prices = {
            'EURUSD': Decimal('1.1000'),
            'GBPUSD': Decimal('1.2500'), 
            'USDJPY': Decimal('150.00'),
            'USDCHF': Decimal('0.9000')
        }
    
    async def get_current_price(self, symbol: str) -> Decimal:
        """Return mock current price"""
        return self._mock_prices.get(symbol, Decimal('1.0000'))
    
    async def get_market_data_point(self, symbol: str) -> MarketDataPoint:
        """Return mock market data point"""
        return MarketDataPoint(
            timestamp=datetime.now(),
            price=await self.get_current_price(symbol),
            volume=Decimal('1000000'),  # Mock volume
            volatility=Decimal('0.015'),  # Mock volatility  
            trend_strength=Decimal('0.01')  # Mock trend strength
        )
    
    async def get_regime_analysis(self, symbol: str) -> MarketRegimeData:
        """Return mock regime analysis"""
        return MarketRegimeData(
            regime_type='trending',
            confidence=0.75,
            trend_direction='up',
            volatility_level='medium',
            last_updated=datetime.now()
        )
    
    async def get_historical_data(self, symbol: str, timeframe: str, count: int) -> List[MarketDataPoint]:
        """Return mock historical data"""
        base_price = await self.get_current_price(symbol)
        data_points = []
        
        for i in range(count):
            # Create mock price variation
            price_variation = Decimal(str(0.001 * (i % 10 - 5)))  # Simple variation
            price = base_price + price_variation
            
            data_points.append(MarketDataPoint(
                timestamp=datetime.now(),
                price=price,
                volume=Decimal('1000000'),
                volatility=Decimal('0.015'),
                trend_strength=Decimal('0.01')
            ))
        
        return data_points