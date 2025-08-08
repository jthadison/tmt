"""OANDA API client for real-time and historical forex market data."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, AsyncGenerator, Dict, List, Optional, Set
from urllib.parse import urljoin

import aiohttp
import backoff
from aiohttp import ClientSession, ClientTimeout

logger = logging.getLogger(__name__)

FOREX_PAIRS = {
    "EUR_USD", "GBP_USD", "USD_JPY", "USD_CHF", "AUD_USD", 
    "USD_CAD", "NZD_USD", "EUR_GBP", "EUR_JPY", "GBP_JPY"
}


class OANDAClient:
    """
    OANDA API client for forex market data integration.
    
    Handles both WebSocket streaming for real-time data and REST API
    for historical data with proper authentication and rate limiting.
    """
    
    def __init__(
        self,
        api_key: str,
        account_id: str,
        environment: str = "practice",
        max_retries: int = 3,
        timeout: int = 30
    ):
        """
        Initialize OANDA client.
        
        @param api_key: OANDA API key for authentication
        @param account_id: OANDA account ID
        @param environment: Trading environment ('practice' or 'live')
        @param max_retries: Maximum number of retry attempts
        @param timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.account_id = account_id
        self.environment = environment
        self.max_retries = max_retries
        self.timeout = ClientTimeout(total=timeout)
        
        # Set base URLs based on environment
        if environment == "practice":
            self.rest_url = "https://api-fxpractice.oanda.com"
            self.stream_url = "https://stream-fxpractice.oanda.com"
        else:
            self.rest_url = "https://api-fxtrade.oanda.com"
            self.stream_url = "https://stream-fxtrade.oanda.com"
        
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept-Datetime-Format": "RFC3339"
        }
        
        # Rate limiting for REST API (120 requests per minute)
        self.rate_limiter = asyncio.Semaphore(2)  # 2 requests per second
        self.last_request_time = datetime.now()
        
        # WebSocket connection management
        self.ws_session: Optional[ClientSession] = None
        self.ws_connection = None
        self.subscribed_instruments: Set[str] = set()
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
        
    async def connect(self):
        """Initialize HTTP session for API calls."""
        if not self.ws_session:
            self.ws_session = ClientSession(
                headers=self.headers,
                timeout=self.timeout
            )
            
    async def disconnect(self):
        """Close all connections and cleanup resources."""
        if self.ws_connection:
            await self.ws_connection.close()
            self.ws_connection = None
            
        if self.ws_session:
            await self.ws_session.close()
            self.ws_session = None
            
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        max_time=60
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to OANDA REST API with rate limiting.
        
        @param method: HTTP method (GET, POST, etc.)
        @param endpoint: API endpoint path
        @param params: Query parameters
        @param data: Request body data
        @returns: JSON response as dictionary
        @throws: aiohttp.ClientError on request failure
        """
        async with self.rate_limiter:
            # Enforce rate limit (120 requests per minute = 2 per second)
            now = datetime.now()
            elapsed = (now - self.last_request_time).total_seconds()
            if elapsed < 0.5:  # 2 requests per second
                await asyncio.sleep(0.5 - elapsed)
            self.last_request_time = datetime.now()
            
            url = urljoin(self.rest_url, endpoint)
            
            async with self.ws_session.request(
                method=method,
                url=url,
                params=params,
                json=data
            ) as response:
                response.raise_for_status()
                return await response.json()
                
    async def get_instruments(self) -> List[Dict[str, Any]]:
        """
        Get list of tradeable instruments for the account.
        
        @returns: List of instrument details
        """
        endpoint = f"/v3/accounts/{self.account_id}/instruments"
        response = await self._make_request("GET", endpoint)
        return response.get("instruments", [])
        
    async def get_candles(
        self,
        instrument: str,
        granularity: str = "M1",
        count: Optional[int] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        price_type: str = "MBA"
    ) -> List[Dict[str, Any]]:
        """
        Get historical candlestick data.
        
        @param instrument: Instrument name (e.g., "EUR_USD")
        @param granularity: Time granularity (M1, M5, H1, etc.)
        @param count: Number of candles to retrieve
        @param from_time: Start time for historical data
        @param to_time: End time for historical data
        @param price_type: Price type (M=Mid, B=Bid, A=Ask)
        @returns: List of OHLCV candles
        """
        endpoint = f"/v3/instruments/{instrument}/candles"
        
        params = {
            "granularity": granularity,
            "price": price_type
        }
        
        if count:
            params["count"] = count
        if from_time:
            params["from"] = from_time.isoformat()
        if to_time:
            params["to"] = to_time.isoformat()
            
        response = await self._make_request("GET", endpoint, params=params)
        return response.get("candles", [])
        
    async def stream_prices(
        self,
        instruments: List[str],
        snapshot: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream real-time price data via WebSocket.
        
        @param instruments: List of instruments to stream
        @param snapshot: Include current price snapshot
        @yields: Price tick data dictionaries
        """
        if not self.ws_session:
            await self.connect()
            
        # Update subscribed instruments
        self.subscribed_instruments = set(instruments)
        
        # Build streaming endpoint
        endpoint = f"/v3/accounts/{self.account_id}/pricing/stream"
        url = urljoin(self.stream_url, endpoint)
        
        params = {
            "instruments": ",".join(instruments),
            "snapshot": str(snapshot).lower()
        }
        
        while self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                async with self.ws_session.get(
                    url,
                    params=params,
                    headers=self.headers
                ) as response:
                    self.ws_connection = response
                    self.reconnect_attempts = 0
                    logger.info(f"Connected to OANDA stream for {instruments}")
                    
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line.decode('utf-8'))
                                
                                # Handle different message types
                                if data.get("type") == "PRICE":
                                    yield self._normalize_price_tick(data)
                                elif data.get("type") == "HEARTBEAT":
                                    logger.debug("Received heartbeat")
                                    
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse stream data: {e}")
                                continue
                                
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.error(f"Stream connection error: {e}")
                self.reconnect_attempts += 1
                
                if self.reconnect_attempts < self.max_reconnect_attempts:
                    wait_time = min(2 ** self.reconnect_attempts, 60)
                    logger.info(f"Reconnecting in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Max reconnection attempts reached")
                    raise
                    
    def _normalize_price_tick(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize OANDA price tick to standard format.
        
        @param data: Raw OANDA price data
        @returns: Normalized price tick
        """
        instrument = data.get("instrument", "")
        time = data.get("time", "")
        
        # Extract bid/ask prices
        bids = data.get("bids", [])
        asks = data.get("asks", [])
        
        bid_price = Decimal(bids[0]["price"]) if bids else Decimal("0")
        ask_price = Decimal(asks[0]["price"]) if asks else Decimal("0")
        
        # Calculate mid price
        mid_price = (bid_price + ask_price) / 2 if bid_price and ask_price else Decimal("0")
        
        return {
            "symbol": instrument,
            "timestamp": time,
            "bid": float(bid_price),
            "ask": float(ask_price),
            "mid": float(mid_price),
            "source": "oanda",
            "type": "tick"
        }
        
    async def get_account_summary(self) -> Dict[str, Any]:
        """
        Get account summary including balance and margin.
        
        @returns: Account summary data
        """
        endpoint = f"/v3/accounts/{self.account_id}/summary"
        return await self._make_request("GET", endpoint)
        
    async def subscribe_instruments(self, instruments: List[str]):
        """
        Add instruments to the streaming subscription.
        
        @param instruments: List of instruments to add
        """
        self.subscribed_instruments.update(instruments)
        logger.info(f"Updated subscription: {self.subscribed_instruments}")
        
    async def unsubscribe_instruments(self, instruments: List[str]):
        """
        Remove instruments from the streaming subscription.
        
        @param instruments: List of instruments to remove
        """
        for instrument in instruments:
            self.subscribed_instruments.discard(instrument)
        logger.info(f"Updated subscription: {self.subscribed_instruments}")
        
    def is_connected(self) -> bool:
        """
        Check if WebSocket connection is active.
        
        @returns: True if connected, False otherwise
        """
        return self.ws_connection is not None and not self.ws_connection.closed