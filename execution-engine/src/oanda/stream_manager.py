"""
OANDA Stream Manager Interface

Handles real-time price streaming and market data from OANDA.
Provides a consistent interface for price updates across the trading system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List
from decimal import Decimal
from datetime import datetime, timezone
import asyncio
import logging

logger = logging.getLogger(__name__)


class PriceUpdate:
    """Price update data structure"""
    
    def __init__(self, instrument: str, bid: Decimal, ask: Decimal, timestamp: datetime):
        self.instrument = instrument
        self.bid = bid
        self.ask = ask
        self.timestamp = timestamp
        self.mid = (bid + ask) / 2
    
    def __repr__(self):
        return f"PriceUpdate({self.instrument}, bid={self.bid}, ask={self.ask}, mid={self.mid})"


class StreamManagerInterface(ABC):
    """Interface for price streaming"""
    
    @abstractmethod
    async def start_streaming(self, instruments: List[str]) -> bool:
        """Start price streaming for instruments"""
        pass
    
    @abstractmethod
    async def stop_streaming(self) -> bool:
        """Stop price streaming"""
        pass
    
    @abstractmethod
    def subscribe_to_prices(self, callback: Callable[[PriceUpdate], None]) -> str:
        """Subscribe to price updates"""
        pass
    
    @abstractmethod
    def unsubscribe_from_prices(self, subscription_id: str) -> bool:
        """Unsubscribe from price updates"""
        pass
    
    @abstractmethod
    async def get_current_price(self, instrument: str) -> Optional[PriceUpdate]:
        """Get current price for instrument"""
        pass
    
    @property
    @abstractmethod
    def is_streaming(self) -> bool:
        """Check if streaming is active"""
        pass


class MockStreamManager(StreamManagerInterface):
    """
    Mock stream manager for testing and development.
    
    Simulates real-time price updates for testing without requiring OANDA stream API.
    """
    
    def __init__(self):
        self._is_streaming = False
        self._subscriptions: Dict[str, Callable[[PriceUpdate], None]] = {}
        self._current_prices: Dict[str, PriceUpdate] = {}
        self._stream_task: Optional[asyncio.Task] = None
        self._instruments: List[str] = []
        
        # Mock price data
        self._base_prices = {
            'EUR_USD': {'bid': Decimal('1.0575'), 'ask': Decimal('1.0577')},
            'GBP_USD': {'bid': Decimal('1.2485'), 'ask': Decimal('1.2487')},
            'USD_JPY': {'bid': Decimal('150.25'), 'ask': Decimal('150.27')},
            'AUD_USD': {'bid': Decimal('0.6575'), 'ask': Decimal('0.6577')},
            'USD_CAD': {'bid': Decimal('1.3625'), 'ask': Decimal('1.3627')},
            'EUR_GBP': {'bid': Decimal('0.8525'), 'ask': Decimal('0.8527')},
        }
        
        self._subscription_counter = 0
    
    async def start_streaming(self, instruments: List[str]) -> bool:
        """Start mock price streaming"""
        try:
            if self._is_streaming:
                logger.warning("Streaming already active")
                return True
            
            self._instruments = instruments
            self._is_streaming = True
            
            # Initialize current prices
            for instrument in instruments:
                if instrument in self._base_prices:
                    base = self._base_prices[instrument]
                    self._current_prices[instrument] = PriceUpdate(
                        instrument=instrument,
                        bid=base['bid'],
                        ask=base['ask'],
                        timestamp=datetime.now(timezone.utc)
                    )
            
            # Start price update task
            self._stream_task = asyncio.create_task(self._simulate_price_updates())
            
            logger.info(f"Started mock streaming for {len(instruments)} instruments")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start streaming: {e}")
            return False
    
    async def stop_streaming(self) -> bool:
        """Stop mock price streaming"""
        try:
            if not self._is_streaming:
                return True
            
            self._is_streaming = False
            
            if self._stream_task:
                self._stream_task.cancel()
                try:
                    await self._stream_task
                except asyncio.CancelledError:
                    pass
                self._stream_task = None
            
            logger.info("Stopped mock streaming")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop streaming: {e}")
            return False
    
    def subscribe_to_prices(self, callback: Callable[[PriceUpdate], None]) -> str:
        """Subscribe to price updates"""
        self._subscription_counter += 1
        subscription_id = f"sub_{self._subscription_counter}"
        self._subscriptions[subscription_id] = callback
        
        logger.info(f"Added price subscription: {subscription_id}")
        return subscription_id
    
    def unsubscribe_from_prices(self, subscription_id: str) -> bool:
        """Unsubscribe from price updates"""
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]
            logger.info(f"Removed price subscription: {subscription_id}")
            return True
        return False
    
    async def get_current_price(self, instrument: str) -> Optional[PriceUpdate]:
        """Get current price for instrument"""
        return self._current_prices.get(instrument)
    
    @property
    def is_streaming(self) -> bool:
        """Check if streaming is active"""
        return self._is_streaming
    
    async def _simulate_price_updates(self):
        """Simulate realistic price movements"""
        import random
        
        try:
            while self._is_streaming:
                await asyncio.sleep(1.0)  # Update every second
                
                for instrument in self._instruments:
                    if instrument not in self._current_prices:
                        continue
                    
                    current = self._current_prices[instrument]
                    
                    # Generate small random price movements (0.0001 to 0.0005 for major pairs)
                    if 'JPY' in instrument:
                        # JPY pairs move in 0.01 increments
                        movement = Decimal(random.uniform(-0.05, 0.05))
                    else:
                        # Major pairs move in 0.0001 increments
                        movement = Decimal(random.uniform(-0.0005, 0.0005))
                    
                    # Apply movement to both bid and ask
                    new_bid = current.bid + movement
                    new_ask = current.ask + movement
                    
                    # Ensure bid < ask
                    if new_bid >= new_ask:
                        spread = Decimal('0.0002') if 'JPY' not in instrument else Decimal('0.02')
                        new_ask = new_bid + spread
                    
                    # Create new price update
                    new_price = PriceUpdate(
                        instrument=instrument,
                        bid=new_bid,
                        ask=new_ask,
                        timestamp=datetime.now(timezone.utc)
                    )
                    
                    self._current_prices[instrument] = new_price
                    
                    # Notify subscribers
                    for callback in self._subscriptions.values():
                        try:
                            callback(new_price)
                        except Exception as e:
                            logger.error(f"Error in price update callback: {e}")
                
        except asyncio.CancelledError:
            logger.info("Price simulation task cancelled")
        except Exception as e:
            logger.error(f"Error in price simulation: {e}")


# For backwards compatibility, provide the original class name
OandaStreamManager = MockStreamManager