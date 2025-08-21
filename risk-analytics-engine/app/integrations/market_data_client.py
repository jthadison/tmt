"""
Market Data Integration Client for Risk Analytics.

Provides real-time market data integration for pricing, volatility
calculation, and risk analysis with the Market Analysis Agent.
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Callable, Tuple
from collections import defaultdict, deque

import structlog

logger = structlog.get_logger(__name__)


class MarketDataClient:
    """
    Client for integrating with the Market Analysis Agent for real-time
    market data, pricing updates, and volatility calculations.
    """
    
    def __init__(
        self,
        market_data_url: str = "http://localhost:8002",
        timeout: float = 5.0
    ):
        self.market_data_url = market_data_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        
        # Connection management
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_connected = False
        
        # Price data cache
        self.current_prices: Dict[str, Decimal] = {}
        self.price_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.last_price_update: Dict[str, datetime] = {}
        
        # Volatility cache
        self.volatility_cache: Dict[str, Tuple[datetime, float]] = {}
        self.correlation_cache: Dict[Tuple[str, str], Tuple[datetime, float]] = {}
        
        # Event callbacks
        self.price_update_callbacks: List[Callable] = []
        self.volatility_update_callbacks: List[Callable] = []
        
        # Performance tracking
        self.request_count = 0
        self.error_count = 0
        self.avg_response_time = 0.0
        
        # Subscription management
        self.subscribed_instruments: set = set()
        self.websocket_task: Optional[asyncio.Task] = None
    
    async def connect(self) -> bool:
        """Establish connection to market data service."""
        try:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
            
            # Test connection
            health_status = await self.get_health_status()
            if health_status and health_status.get('status') == 'healthy':
                self.is_connected = True
                logger.info("Connected to market data service", url=self.market_data_url)
                return True
            else:
                logger.error("Market data service health check failed")
                return False
                
        except Exception as e:
            logger.error("Failed to connect to market data service", error=str(e))
            return False
    
    async def disconnect(self):
        """Close connection to market data service."""
        if self.websocket_task:
            self.websocket_task.cancel()
            self.websocket_task = None
        
        if self.session:
            await self.session.close()
            self.session = None
        
        self.is_connected = False
        logger.info("Disconnected from market data service")
    
    async def get_health_status(self) -> Optional[Dict]:
        """Get market data service health status."""
        try:
            start_time = time.perf_counter()
            
            async with self.session.get(f"{self.market_data_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Track performance
                    response_time = (time.perf_counter() - start_time) * 1000
                    self._update_performance_metrics(response_time, success=True)
                    
                    return data
                else:
                    logger.warning("Market data health check failed", status=response.status)
                    self._update_performance_metrics(0, success=False)
                    return None
                    
        except Exception as e:
            logger.error("Market data health check error", error=str(e))
            self._update_performance_metrics(0, success=False)
            return None
    
    async def get_current_price(self, instrument: str) -> Optional[Decimal]:
        """Get current price for an instrument."""
        try:
            start_time = time.perf_counter()
            
            url = f"{self.market_data_url}/api/v1/prices/{instrument}/current"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    price_data = await response.json()
                    price = Decimal(str(price_data.get('price', price_data.get('mid', 0))))
                    
                    # Update cache
                    self.current_prices[instrument] = price
                    self.last_price_update[instrument] = datetime.now()
                    
                    # Add to price history
                    self.price_history[instrument].append((datetime.now(), price))
                    
                    # Track performance
                    response_time = (time.perf_counter() - start_time) * 1000
                    self._update_performance_metrics(response_time, success=True)
                    
                    # Notify callbacks
                    await self._notify_price_callbacks(instrument, price)
                    
                    return price
                    
                else:
                    logger.warning("Failed to get current price", 
                                 instrument=instrument, 
                                 status=response.status)
                    self._update_performance_metrics(0, success=False)
                    return None
                    
        except Exception as e:
            logger.error("Error getting current price", 
                        instrument=instrument, 
                        error=str(e))
            self._update_performance_metrics(0, success=False)
            return None
    
    async def get_current_prices(self, instruments: List[str]) -> Dict[str, Decimal]:
        """Get current prices for multiple instruments."""
        try:
            start_time = time.perf_counter()
            
            url = f"{self.market_data_url}/api/v1/prices/current"
            payload = {"instruments": instruments}
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    prices_data = await response.json()
                    prices = {}
                    
                    for instrument, price_info in prices_data.items():
                        if isinstance(price_info, dict):
                            price = Decimal(str(price_info.get('price', price_info.get('mid', 0))))
                        else:
                            price = Decimal(str(price_info))
                        
                        prices[instrument] = price
                        
                        # Update cache
                        self.current_prices[instrument] = price
                        self.last_price_update[instrument] = datetime.now()
                        
                        # Add to price history
                        self.price_history[instrument].append((datetime.now(), price))
                    
                    # Track performance
                    response_time = (time.perf_counter() - start_time) * 1000
                    self._update_performance_metrics(response_time, success=True)
                    
                    # Notify callbacks
                    for instrument, price in prices.items():
                        await self._notify_price_callbacks(instrument, price)
                    
                    return prices
                    
                else:
                    logger.warning("Failed to get current prices", status=response.status)
                    self._update_performance_metrics(0, success=False)
                    return {}
                    
        except Exception as e:
            logger.error("Error getting current prices", error=str(e))
            self._update_performance_metrics(0, success=False)
            return {}
    
    async def get_historical_prices(
        self,
        instrument: str,
        timeframe: str = "M1",
        count: int = 100
    ) -> List[Dict]:
        """Get historical price data."""
        try:
            start_time = time.perf_counter()
            
            url = f"{self.market_data_url}/api/v1/prices/{instrument}/history"
            params = {"timeframe": timeframe, "count": count}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    history_data = await response.json()
                    
                    # Track performance
                    response_time = (time.perf_counter() - start_time) * 1000
                    self._update_performance_metrics(response_time, success=True)
                    
                    return history_data.get('candles', [])
                    
                else:
                    logger.warning("Failed to get historical prices", 
                                 instrument=instrument, 
                                 status=response.status)
                    self._update_performance_metrics(0, success=False)
                    return []
                    
        except Exception as e:
            logger.error("Error getting historical prices", 
                        instrument=instrument, 
                        error=str(e))
            self._update_performance_metrics(0, success=False)
            return []
    
    async def calculate_volatility(
        self,
        instrument: str,
        periods: int = 20,
        use_cache: bool = True
    ) -> Optional[float]:
        """Calculate volatility for an instrument."""
        
        # Check cache first
        if use_cache and instrument in self.volatility_cache:
            cached_time, cached_vol = self.volatility_cache[instrument]
            if (datetime.now() - cached_time).total_seconds() < 300:  # 5-minute cache
                return cached_vol
        
        try:
            start_time = time.perf_counter()
            
            url = f"{self.market_data_url}/api/v1/analysis/{instrument}/volatility"
            params = {"periods": periods}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    vol_data = await response.json()
                    volatility = vol_data.get('volatility', 0.0)
                    
                    # Cache result
                    self.volatility_cache[instrument] = (datetime.now(), volatility)
                    
                    # Track performance
                    response_time = (time.perf_counter() - start_time) * 1000
                    self._update_performance_metrics(response_time, success=True)
                    
                    # Notify callbacks
                    await self._notify_volatility_callbacks(instrument, volatility)
                    
                    return volatility
                    
                else:
                    logger.warning("Failed to calculate volatility", 
                                 instrument=instrument, 
                                 status=response.status)
                    self._update_performance_metrics(0, success=False)
                    return None
                    
        except Exception as e:
            logger.error("Error calculating volatility", 
                        instrument=instrument, 
                        error=str(e))
            self._update_performance_metrics(0, success=False)
            return None
    
    async def calculate_correlation(
        self,
        instrument1: str,
        instrument2: str,
        periods: int = 50,
        use_cache: bool = True
    ) -> Optional[float]:
        """Calculate correlation between two instruments."""
        
        # Check cache first
        cache_key = tuple(sorted([instrument1, instrument2]))
        if use_cache and cache_key in self.correlation_cache:
            cached_time, cached_corr = self.correlation_cache[cache_key]
            if (datetime.now() - cached_time).total_seconds() < 600:  # 10-minute cache
                return cached_corr
        
        try:
            start_time = time.perf_counter()
            
            url = f"{self.market_data_url}/api/v1/analysis/correlation"
            payload = {
                "instrument1": instrument1,
                "instrument2": instrument2,
                "periods": periods
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    corr_data = await response.json()
                    correlation = corr_data.get('correlation', 0.0)
                    
                    # Cache result
                    self.correlation_cache[cache_key] = (datetime.now(), correlation)
                    
                    # Track performance
                    response_time = (time.perf_counter() - start_time) * 1000
                    self._update_performance_metrics(response_time, success=True)
                    
                    return correlation
                    
                else:
                    logger.warning("Failed to calculate correlation", 
                                 instrument1=instrument1,
                                 instrument2=instrument2,
                                 status=response.status)
                    self._update_performance_metrics(0, success=False)
                    return None
                    
        except Exception as e:
            logger.error("Error calculating correlation", 
                        instrument1=instrument1,
                        instrument2=instrument2,
                        error=str(e))
            self._update_performance_metrics(0, success=False)
            return None
    
    async def get_market_analysis(self, instrument: str) -> Optional[Dict]:
        """Get comprehensive market analysis for an instrument."""
        try:
            start_time = time.perf_counter()
            
            url = f"{self.market_data_url}/api/v1/analysis/{instrument}/comprehensive"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    analysis_data = await response.json()
                    
                    # Track performance
                    response_time = (time.perf_counter() - start_time) * 1000
                    self._update_performance_metrics(response_time, success=True)
                    
                    return analysis_data
                    
                else:
                    logger.warning("Failed to get market analysis", 
                                 instrument=instrument, 
                                 status=response.status)
                    self._update_performance_metrics(0, success=False)
                    return None
                    
        except Exception as e:
            logger.error("Error getting market analysis", 
                        instrument=instrument, 
                        error=str(e))
            self._update_performance_metrics(0, success=False)
            return None
    
    async def subscribe_to_prices(self, instruments: List[str]) -> bool:
        """Subscribe to real-time price updates via WebSocket."""
        try:
            self.subscribed_instruments.update(instruments)
            
            # Start WebSocket connection if not already running
            if not self.websocket_task:
                self.websocket_task = asyncio.create_task(self._websocket_price_stream())
            
            logger.info("Subscribed to price updates", instruments=instruments)
            return True
            
        except Exception as e:
            logger.error("Error subscribing to prices", error=str(e))
            return False
    
    async def _websocket_price_stream(self):
        """Handle WebSocket price streaming."""
        try:
            ws_url = f"{self.market_data_url.replace('http', 'ws')}/ws/prices"
            
            async with self.session.ws_connect(ws_url) as ws:
                # Send subscription message
                subscription = {
                    "action": "subscribe",
                    "instruments": list(self.subscribed_instruments)
                }
                await ws.send_str(json.dumps(subscription))
                
                logger.info("WebSocket price stream connected")
                
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)
                            
                            if data.get('type') == 'price_update':
                                instrument = data.get('instrument')
                                price = Decimal(str(data.get('price', 0)))
                                
                                # Update cache
                                self.current_prices[instrument] = price
                                self.last_price_update[instrument] = datetime.now()
                                
                                # Add to price history
                                self.price_history[instrument].append((datetime.now(), price))
                                
                                # Notify callbacks
                                await self._notify_price_callbacks(instrument, price)
                                
                        except Exception as e:
                            logger.error("Error processing WebSocket message", error=str(e))
                    
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error("WebSocket error", error=ws.exception())
                        break
                        
        except Exception as e:
            logger.error("WebSocket connection error", error=str(e))
        finally:
            logger.info("WebSocket price stream disconnected")
    
    def get_cached_price(self, instrument: str) -> Optional[Decimal]:
        """Get cached price for an instrument."""
        return self.current_prices.get(instrument)
    
    def get_cached_prices(self) -> Dict[str, Decimal]:
        """Get all cached prices."""
        return self.current_prices.copy()
    
    def get_price_history(self, instrument: str, hours: int = 24) -> List[Tuple[datetime, Decimal]]:
        """Get price history for an instrument."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        history = list(self.price_history.get(instrument, []))
        return [(ts, price) for ts, price in history if ts >= cutoff_time]
    
    async def _notify_price_callbacks(self, instrument: str, price: Decimal):
        """Notify registered callbacks of price updates."""
        for callback in self.price_update_callbacks:
            try:
                await callback(instrument, price)
            except Exception as e:
                logger.error("Error in price update callback", error=str(e))
    
    async def _notify_volatility_callbacks(self, instrument: str, volatility: float):
        """Notify registered callbacks of volatility updates."""
        for callback in self.volatility_update_callbacks:
            try:
                await callback(instrument, volatility)
            except Exception as e:
                logger.error("Error in volatility update callback", error=str(e))
    
    def _update_performance_metrics(self, response_time: float, success: bool):
        """Update client performance metrics."""
        self.request_count += 1
        
        if not success:
            self.error_count += 1
        
        if response_time > 0:
            # Calculate running average
            if self.avg_response_time == 0:
                self.avg_response_time = response_time
            else:
                self.avg_response_time = (self.avg_response_time * 0.9 + response_time * 0.1)
    
    def register_price_callback(self, callback: Callable):
        """Register callback for price updates."""
        self.price_update_callbacks.append(callback)
        logger.debug("Registered price update callback")
    
    def register_volatility_callback(self, callback: Callable):
        """Register callback for volatility updates."""
        self.volatility_update_callbacks.append(callback)
        logger.debug("Registered volatility update callback")
    
    async def start_price_monitoring(self, instruments: List[str], interval_seconds: float = 1.0):
        """Start continuous price monitoring for specified instruments."""
        logger.info("Starting price monitoring", 
                   instruments=instruments, 
                   interval=interval_seconds)
        
        async def monitor_prices():
            while self.is_connected:
                try:
                    await self.get_current_prices(instruments)
                    await asyncio.sleep(interval_seconds)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("Error in price monitoring", error=str(e))
                    await asyncio.sleep(interval_seconds)
        
        # Start monitoring task
        asyncio.create_task(monitor_prices())
    
    def get_client_performance(self) -> Dict:
        """Get client performance metrics."""
        success_rate = (self.request_count - self.error_count) / self.request_count if self.request_count > 0 else 1.0
        
        return {
            "is_connected": self.is_connected,
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "success_rate": success_rate,
            "avg_response_time_ms": self.avg_response_time,
            "cached_instruments": len(self.current_prices),
            "subscribed_instruments": len(self.subscribed_instruments),
            "volatility_cache_size": len(self.volatility_cache),
            "correlation_cache_size": len(self.correlation_cache),
            "websocket_active": self.websocket_task is not None and not self.websocket_task.done()
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()