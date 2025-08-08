"""Polygon.io API client for real-time and historical market data."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, AsyncGenerator, Dict, List, Optional, Set
from urllib.parse import urljoin

import aiohttp
import backoff
import websockets
from aiohttp import ClientSession, ClientTimeout

logger = logging.getLogger(__name__)

MAJOR_INDICES = {
    "US30": "I:DJI",     # Dow Jones Industrial Average
    "NAS100": "I:NDX",   # NASDAQ-100
    "SPX500": "I:SPX",   # S&P 500
    "RUT2000": "I:RUT",  # Russell 2000
    "VIX": "I:VIX"       # Volatility Index
}


class PolygonClient:
    """
    Polygon.io API client for market data integration.
    
    Provides real-time WebSocket streaming and REST API access for
    historical data with proper authentication and rate limiting.
    """
    
    def __init__(
        self,
        api_key: str,
        plan_tier: str = "starter",
        max_retries: int = 3,
        timeout: int = 30
    ):
        """
        Initialize Polygon.io client.
        
        @param api_key: Polygon.io API key for authentication
        @param plan_tier: Subscription plan tier for rate limiting
        @param max_retries: Maximum number of retry attempts
        @param timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.plan_tier = plan_tier
        self.max_retries = max_retries
        self.timeout = ClientTimeout(total=timeout)
        
        # API endpoints
        self.rest_url = "https://api.polygon.io"
        self.ws_url = f"wss://socket.polygon.io/stocks"
        
        # Set rate limits based on plan tier
        self.rate_limits = {
            "starter": 5,      # 5 requests per minute
            "developer": 100,  # 100 requests per minute
            "advanced": 1000   # 1000 requests per minute
        }
        self.requests_per_second = self.rate_limits.get(plan_tier, 5) / 60
        
        # Rate limiting
        self.rate_limiter = asyncio.Semaphore(max(1, int(self.requests_per_second)))
        self.last_request_time = datetime.now()
        
        # HTTP session management
        self.session: Optional[ClientSession] = None
        
        # WebSocket connection management
        self.ws_connection = None
        self.subscribed_symbols: Set[str] = set()
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
        if not self.session:
            self.session = ClientSession(
                timeout=self.timeout
            )
            
    async def disconnect(self):
        """Close all connections and cleanup resources."""
        if self.ws_connection:
            await self.ws_connection.close()
            self.ws_connection = None
            
        if self.session:
            await self.session.close()
            self.session = None
            
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
        Make HTTP request to Polygon REST API with rate limiting.
        
        @param method: HTTP method (GET, POST, etc.)
        @param endpoint: API endpoint path
        @param params: Query parameters
        @param data: Request body data
        @returns: JSON response as dictionary
        @throws: aiohttp.ClientError on request failure
        """
        async with self.rate_limiter:
            # Enforce rate limit
            now = datetime.now()
            elapsed = (now - self.last_request_time).total_seconds()
            min_interval = 1.0 / self.requests_per_second
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
            self.last_request_time = datetime.now()
            
            url = urljoin(self.rest_url, endpoint)
            
            # Add API key to params
            if params is None:
                params = {}
            params["apiKey"] = self.api_key
            
            async with self.session.request(
                method=method,
                url=url,
                params=params,
                json=data
            ) as response:
                response.raise_for_status()
                return await response.json()
                
    async def get_aggregates(
        self,
        ticker: str,
        multiplier: int = 1,
        timespan: str = "minute",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit: int = 5000
    ) -> List[Dict[str, Any]]:
        """
        Get aggregate bars for a ticker over a time range.
        
        @param ticker: Stock/index ticker symbol
        @param multiplier: Size of the time window
        @param timespan: Unit of time (minute, hour, day, etc.)
        @param from_date: Start date (YYYY-MM-DD format)
        @param to_date: End date (YYYY-MM-DD format)
        @param limit: Maximum number of results
        @returns: List of aggregate bars
        """
        endpoint = f"/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
        
        params = {
            "adjusted": "true",
            "sort": "asc",
            "limit": limit
        }
        
        response = await self._make_request("GET", endpoint, params=params)
        return response.get("results", [])
        
    async def get_ticker_details(self, ticker: str) -> Dict[str, Any]:
        """
        Get details about a specific ticker.
        
        @param ticker: Stock/index ticker symbol
        @returns: Ticker details including name and market info
        """
        endpoint = f"/v3/reference/tickers/{ticker}"
        response = await self._make_request("GET", endpoint)
        return response.get("results", {})
        
    async def get_snapshot(self, ticker: str) -> Dict[str, Any]:
        """
        Get current snapshot data for a ticker.
        
        @param ticker: Stock/index ticker symbol
        @returns: Current market snapshot data
        """
        endpoint = f"/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}"
        response = await self._make_request("GET", endpoint)
        return response.get("ticker", {})
        
    async def stream_market_data(
        self,
        symbols: List[str]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream real-time market data via WebSocket.
        
        @param symbols: List of ticker symbols to stream
        @yields: Market data tick dictionaries
        """
        # Update subscribed symbols
        self.subscribed_symbols = set(symbols)
        
        while self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                # Connect to Polygon WebSocket
                async with websockets.connect(self.ws_url) as websocket:
                    self.ws_connection = websocket
                    self.reconnect_attempts = 0
                    logger.info(f"Connected to Polygon WebSocket for {symbols}")
                    
                    # Authenticate
                    auth_message = {
                        "action": "auth",
                        "params": self.api_key
                    }
                    await websocket.send(json.dumps(auth_message))
                    
                    # Wait for authentication response
                    auth_response = await websocket.recv()
                    auth_data = json.loads(auth_response)
                    
                    if auth_data[0]["status"] != "auth_success":
                        raise ConnectionError("Authentication failed")
                    
                    # Subscribe to symbols
                    subscribe_message = {
                        "action": "subscribe",
                        "params": ",".join([f"T.{s}" for s in symbols])  # T. prefix for trades
                    }
                    await websocket.send(json.dumps(subscribe_message))
                    
                    # Stream data
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            
                            for item in data:
                                if item.get("ev") == "T":  # Trade event
                                    yield self._normalize_trade_data(item)
                                elif item.get("ev") == "Q":  # Quote event
                                    yield self._normalize_quote_data(item)
                                    
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse WebSocket data: {e}")
                            continue
                            
            except (websockets.exceptions.WebSocketException, ConnectionError) as e:
                logger.error(f"WebSocket connection error: {e}")
                self.reconnect_attempts += 1
                
                if self.reconnect_attempts < self.max_reconnect_attempts:
                    wait_time = min(2 ** self.reconnect_attempts, 60)
                    logger.info(f"Reconnecting in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Max reconnection attempts reached")
                    raise
                    
    def _normalize_trade_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Polygon trade data to standard format.
        
        @param data: Raw Polygon trade data
        @returns: Normalized trade tick
        """
        return {
            "symbol": data.get("sym", ""),
            "timestamp": datetime.fromtimestamp(data.get("t", 0) / 1000).isoformat(),
            "price": float(data.get("p", 0)),
            "volume": int(data.get("s", 0)),
            "source": "polygon",
            "type": "trade"
        }
        
    def _normalize_quote_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Polygon quote data to standard format.
        
        @param data: Raw Polygon quote data
        @returns: Normalized quote tick
        """
        bid_price = float(data.get("bp", 0))
        ask_price = float(data.get("ap", 0))
        mid_price = (bid_price + ask_price) / 2 if bid_price and ask_price else 0
        
        return {
            "symbol": data.get("sym", ""),
            "timestamp": datetime.fromtimestamp(data.get("t", 0) / 1000).isoformat(),
            "bid": bid_price,
            "ask": ask_price,
            "mid": mid_price,
            "bid_size": int(data.get("bs", 0)),
            "ask_size": int(data.get("as", 0)),
            "source": "polygon",
            "type": "quote"
        }
        
    async def get_market_status(self) -> Dict[str, Any]:
        """
        Get current market status (open/closed).
        
        @returns: Market status information
        """
        endpoint = "/v1/marketstatus/now"
        return await self._make_request("GET", endpoint)
        
    async def subscribe_symbols(self, symbols: List[str]):
        """
        Add symbols to the streaming subscription.
        
        @param symbols: List of symbols to add
        """
        self.subscribed_symbols.update(symbols)
        
        if self.ws_connection:
            subscribe_message = {
                "action": "subscribe",
                "params": ",".join([f"T.{s}" for s in symbols])
            }
            await self.ws_connection.send(json.dumps(subscribe_message))
            
        logger.info(f"Updated subscription: {self.subscribed_symbols}")
        
    async def unsubscribe_symbols(self, symbols: List[str]):
        """
        Remove symbols from the streaming subscription.
        
        @param symbols: List of symbols to remove
        """
        for symbol in symbols:
            self.subscribed_symbols.discard(symbol)
            
        if self.ws_connection:
            unsubscribe_message = {
                "action": "unsubscribe",
                "params": ",".join([f"T.{s}" for s in symbols])
            }
            await self.ws_connection.send(json.dumps(unsubscribe_message))
            
        logger.info(f"Updated subscription: {self.subscribed_symbols}")
        
    def is_connected(self) -> bool:
        """
        Check if WebSocket connection is active.
        
        @returns: True if connected, False otherwise
        """
        return self.ws_connection is not None and self.ws_connection.open
        
    def map_index_symbol(self, symbol: str) -> str:
        """
        Map common index names to Polygon ticker symbols.
        
        @param symbol: Common index name (e.g., "US30")
        @returns: Polygon ticker symbol (e.g., "I:DJI")
        """
        return MAJOR_INDICES.get(symbol, symbol)