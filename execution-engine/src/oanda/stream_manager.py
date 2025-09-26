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
import json
import aiohttp
import os

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


class RealOandaStreamManager(StreamManagerInterface):
    """Real OANDA streaming manager that connects to actual OANDA streaming API"""

    def __init__(self, api_key: str = None, environment: str = "practice"):
        self.api_key = api_key or os.getenv("OANDA_API_KEY")
        self.environment = environment

        if self.environment == "live":
            self.stream_base = "https://stream-fxtrade.oanda.com"
        else:
            self.stream_base = "https://stream-fxpractice.oanda.com"

        self._is_streaming = False
        self._instruments: List[str] = []
        self._subscriptions: Dict[str, Callable] = {}
        self._subscription_counter = 0
        self._current_prices: Dict[str, PriceUpdate] = {}
        self._stream_session: Optional[aiohttp.ClientSession] = None
        self._stream_task: Optional[asyncio.Task] = None

        logger.info(f"Initialized Real OANDA StreamManager for {environment} environment")

    async def start_streaming(self, instruments: List[str]) -> bool:
        """Start real-time streaming from OANDA"""
        if not self.api_key:
            logger.error("OANDA API key not provided - cannot start real streaming")
            return False

        if self._is_streaming:
            logger.warning("Streaming already active")
            return True

        try:
            self._instruments = instruments
            self._is_streaming = True

            # Create session with proper headers
            self._stream_session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "application/stream+json"
                },
                timeout=aiohttp.ClientTimeout(total=None, sock_read=30)
            )

            # Start streaming task
            self._stream_task = asyncio.create_task(self._stream_prices())

            logger.info(f"Started real OANDA streaming for {len(instruments)} instruments")
            return True

        except Exception as e:
            logger.error(f"Failed to start OANDA streaming: {e}")
            self._is_streaming = False
            if self._stream_session:
                await self._stream_session.close()
                self._stream_session = None
            return False

    async def stop_streaming(self) -> bool:
        """Stop real-time streaming"""
        if not self._is_streaming:
            return True

        try:
            self._is_streaming = False

            if self._stream_task and not self._stream_task.done():
                self._stream_task.cancel()
                try:
                    await self._stream_task
                except asyncio.CancelledError:
                    pass

            if self._stream_session:
                await self._stream_session.close()
                self._stream_session = None

            logger.info("Stopped OANDA streaming")
            return True

        except Exception as e:
            logger.error(f"Error stopping streaming: {e}")
            return False

    async def _stream_prices(self):
        """Stream prices from OANDA API"""
        account_id = os.getenv("OANDA_ACCOUNT_ID")
        if not account_id:
            logger.error("OANDA account ID not provided")
            return

        instruments_param = ",".join(self._instruments)
        url = f"{self.stream_base}/v3/accounts/{account_id}/pricing/stream"

        try:
            async with self._stream_session.get(
                url,
                params={"instruments": instruments_param}
            ) as response:
                if response.status != 200:
                    logger.error(f"OANDA streaming failed: {response.status}")
                    return

                logger.info(f"Connected to OANDA streaming API")

                async for line in response.content:
                    if not self._is_streaming:
                        break

                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            await self._process_price_update(data)
                        except json.JSONDecodeError:
                            continue
                        except Exception as e:
                            logger.error(f"Error processing price update: {e}")

        except asyncio.CancelledError:
            logger.info("OANDA streaming cancelled")
        except Exception as e:
            logger.error(f"OANDA streaming error: {e}")

    async def _process_price_update(self, data: Dict):
        """Process incoming price update from OANDA"""
        try:
            if data.get("type") == "PRICE":
                instrument = data.get("instrument")
                if not instrument:
                    return

                bids = data.get("bids", [])
                asks = data.get("asks", [])

                if bids and asks:
                    bid = Decimal(str(bids[0]["price"]))
                    ask = Decimal(str(asks[0]["price"]))

                    price_update = PriceUpdate(
                        instrument=instrument,
                        bid=bid,
                        ask=ask,
                        timestamp=datetime.now(timezone.utc)
                    )

                    self._current_prices[instrument] = price_update

                    # Notify subscribers
                    for callback in self._subscriptions.values():
                        try:
                            await callback(price_update)
                        except Exception as e:
                            logger.error(f"Error in price callback: {e}")

        except Exception as e:
            logger.error(f"Error processing OANDA price update: {e}")

    def subscribe_to_prices(self, callback: Callable[[PriceUpdate], None]) -> str:
        """Subscribe to price updates"""
        self._subscription_counter += 1
        subscription_id = f"sub_{self._subscription_counter}"
        self._subscriptions[subscription_id] = callback
        logger.info(f"Added real price subscription: {subscription_id}")
        return subscription_id

    def unsubscribe_from_prices(self, subscription_id: str) -> bool:
        """Unsubscribe from price updates"""
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]
            logger.info(f"Removed real price subscription: {subscription_id}")
            return True
        return False

    async def get_current_price(self, instrument: str) -> Optional[PriceUpdate]:
        """Get current price for instrument"""
        return self._current_prices.get(instrument)

    @property
    def is_streaming(self) -> bool:
        """Check if streaming is active"""
        return self._is_streaming


# Configuration-based factory function
def create_stream_manager(use_mock: bool = None) -> StreamManagerInterface:
    """Create appropriate stream manager based on configuration"""
    if use_mock is None:
        # Try to import trading config, fall back to environment variable
        try:
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../shared'))
            from trading_config import get_trading_config
            config = get_trading_config()
            use_mock = config.use_mock_streaming
            logger.info(f"Using trading config: mock_streaming={use_mock}, mode={config.trading_mode.value}")
        except ImportError:
            # Fallback to environment variable
            use_mock = os.getenv("USE_MOCK_STREAMING", "true").lower() == "true"
            logger.info(f"Using environment variable: USE_MOCK_STREAMING={use_mock}")

    if use_mock:
        logger.info("Creating Mock Stream Manager (for simulation/testing)")
        return MockStreamManager()
    else:
        logger.info("Creating Real OANDA Stream Manager (for live trading)")
        return RealOandaStreamManager()


# For backwards compatibility, but now configurable
OandaStreamManager = create_stream_manager