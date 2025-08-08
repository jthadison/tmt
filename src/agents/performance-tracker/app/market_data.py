"""Market data feed integration for real-time P&L updates."""

import asyncio
import logging
import json
import random
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

import websockets
from .models import MarketTick

logger = logging.getLogger(__name__)


@dataclass
class MarketDataConfig:
    """Market data feed configuration."""
    feed_type: str  # 'simulation', 'mt5', 'ib', 'alpaca'
    symbols: List[str]
    update_frequency: float = 1.0  # seconds
    connection_params: Dict = None


class SimulatedMarketDataFeed:
    """Simulated market data feed for testing."""
    
    def __init__(self, config: MarketDataConfig):
        self.config = config
        self.is_running = False
        self.subscribers = []
        self.current_prices = {}
        
        # Initialize base prices
        self._initialize_base_prices()
    
    def _initialize_base_prices(self):
        """Initialize base prices for simulation."""
        price_map = {
            'EURUSD': Decimal('1.0850'),
            'GBPUSD': Decimal('1.2650'), 
            'USDJPY': Decimal('149.50'),
            'AUDUSD': Decimal('0.6550'),
            'USDCAD': Decimal('1.3450'),
            'USDCHF': Decimal('0.8750'),
            'NZDUSD': Decimal('0.6150'),
            'EURGBP': Decimal('0.8580'),
            'EURJPY': Decimal('162.25'),
            'GBPJPY': Decimal('189.15'),
            'XAUUSD': Decimal('2050.00'),
            'XAGUSD': Decimal('24.50'),
            'US30': Decimal('37500.0'),
            'US500': Decimal('4750.0'),
            'NAS100': Decimal('16800.0'),
            'GER40': Decimal('17200.0')
        }
        
        for symbol in self.config.symbols:
            if symbol in price_map:
                base_price = price_map[symbol]
                spread = self._get_spread(symbol)
                
                self.current_prices[symbol] = {
                    'bid': base_price - spread / 2,
                    'ask': base_price + spread / 2,
                    'last_update': datetime.utcnow()
                }
    
    def _get_spread(self, symbol: str) -> Decimal:
        """Get typical spread for symbol."""
        spread_map = {
            'EURUSD': Decimal('0.00001'),
            'GBPUSD': Decimal('0.00002'),
            'USDJPY': Decimal('0.002'),
            'AUDUSD': Decimal('0.00002'),
            'USDCAD': Decimal('0.00002'),
            'USDCHF': Decimal('0.00002'),
            'NZDUSD': Decimal('0.00003'),
            'EURGBP': Decimal('0.00002'),
            'EURJPY': Decimal('0.003'),
            'GBPJPY': Decimal('0.004'),
            'XAUUSD': Decimal('0.50'),
            'XAGUSD': Decimal('0.05'),
            'US30': Decimal('2.0'),
            'US500': Decimal('0.5'),
            'NAS100': Decimal('1.0'),
            'GER40': Decimal('1.0')
        }
        return spread_map.get(symbol, Decimal('0.00002'))
    
    async def start(self):
        """Start the simulated market data feed."""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info(f"Starting simulated market data feed for {len(self.config.symbols)} symbols")
        
        # Start price generation task
        asyncio.create_task(self._generate_price_updates())
    
    async def stop(self):
        """Stop the market data feed."""
        self.is_running = False
        logger.info("Stopped simulated market data feed")
    
    def subscribe(self, callback: Callable[[MarketTick], None]):
        """Subscribe to market data updates."""
        self.subscribers.append(callback)
        logger.info(f"Added market data subscriber. Total: {len(self.subscribers)}")
    
    def unsubscribe(self, callback: Callable[[MarketTick], None]):
        """Unsubscribe from market data updates."""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
            logger.info(f"Removed market data subscriber. Total: {len(self.subscribers)}")
    
    async def _generate_price_updates(self):
        """Generate simulated price updates."""
        while self.is_running:
            try:
                # Update prices for all symbols
                for symbol in self.config.symbols:
                    await self._update_symbol_price(symbol)
                
                await asyncio.sleep(self.config.update_frequency)
                
            except Exception as e:
                logger.error(f"Error generating price updates: {e}")
                await asyncio.sleep(1)
    
    async def _update_symbol_price(self, symbol: str):
        """Update price for specific symbol."""
        try:
            if symbol not in self.current_prices:
                return
            
            current = self.current_prices[symbol]
            current_bid = current['bid']
            current_ask = current['ask']
            
            # Generate price movement
            volatility = self._get_volatility(symbol)
            direction = random.choice([-1, 1])
            movement = Decimal(str(random.uniform(0, float(volatility)))) * direction
            
            # Apply movement to mid price
            mid_price = (current_bid + current_ask) / 2
            new_mid = mid_price + movement
            
            # Ensure positive prices
            if new_mid <= 0:
                new_mid = mid_price
            
            # Calculate new bid/ask
            spread = self._get_spread(symbol)
            new_bid = new_mid - spread / 2
            new_ask = new_mid + spread / 2
            
            # Update cache
            self.current_prices[symbol] = {
                'bid': new_bid,
                'ask': new_ask,
                'last_update': datetime.utcnow()
            }
            
            # Create tick
            tick = MarketTick(
                symbol=symbol,
                bid_price=new_bid,
                ask_price=new_ask,
                timestamp=datetime.utcnow(),
                volume=random.randint(1, 100)
            )
            
            # Notify subscribers
            for callback in self.subscribers:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(tick)
                    else:
                        callback(tick)
                except Exception as e:
                    logger.error(f"Error calling subscriber: {e}")
                    
        except Exception as e:
            logger.error(f"Error updating price for {symbol}: {e}")
    
    def _get_volatility(self, symbol: str) -> Decimal:
        """Get typical volatility for symbol."""
        volatility_map = {
            'EURUSD': Decimal('0.0001'),
            'GBPUSD': Decimal('0.0002'), 
            'USDJPY': Decimal('0.01'),
            'AUDUSD': Decimal('0.0002'),
            'USDCAD': Decimal('0.0001'),
            'USDCHF': Decimal('0.0001'),
            'NZDUSD': Decimal('0.0003'),
            'EURGBP': Decimal('0.0001'),
            'EURJPY': Decimal('0.02'),
            'GBPJPY': Decimal('0.03'),
            'XAUUSD': Decimal('2.0'),
            'XAGUSD': Decimal('0.2'),
            'US30': Decimal('50.0'),
            'US500': Decimal('10.0'),
            'NAS100': Decimal('25.0'),
            'GER40': Decimal('20.0')
        }
        return volatility_map.get(symbol, Decimal('0.0001'))
    
    def get_current_price(self, symbol: str) -> Optional[MarketTick]:
        """Get current price for symbol."""
        if symbol in self.current_prices:
            price_data = self.current_prices[symbol]
            return MarketTick(
                symbol=symbol,
                bid_price=price_data['bid'],
                ask_price=price_data['ask'],
                timestamp=price_data['last_update']
            )
        return None


class MT5MarketDataFeed:
    """MetaTrader 5 market data feed integration."""
    
    def __init__(self, config: MarketDataConfig):
        self.config = config
        self.is_running = False
        self.subscribers = []
        self.mt5_connection = None
    
    async def start(self):
        """Start MT5 market data feed."""
        try:
            # Import MT5 library (would need to be installed)
            # import MetaTrader5 as mt5
            
            # Initialize MT5 connection
            # if not mt5.initialize():
            #     raise Exception("MT5 initialization failed")
            
            self.is_running = True
            logger.info("Started MT5 market data feed")
            
            # Start price monitoring
            asyncio.create_task(self._monitor_mt5_prices())
            
        except ImportError:
            logger.warning("MetaTrader5 library not available, falling back to simulation")
            # Fall back to simulation
            sim_feed = SimulatedMarketDataFeed(self.config)
            await sim_feed.start()
            return sim_feed
        except Exception as e:
            logger.error(f"Failed to start MT5 feed: {e}")
            raise
    
    async def stop(self):
        """Stop MT5 market data feed."""
        self.is_running = False
        # mt5.shutdown()
        logger.info("Stopped MT5 market data feed")
    
    def subscribe(self, callback: Callable[[MarketTick], None]):
        """Subscribe to market data updates."""
        self.subscribers.append(callback)
    
    async def _monitor_mt5_prices(self):
        """Monitor MT5 prices and broadcast updates."""
        while self.is_running:
            try:
                # Get tick data from MT5
                # for symbol in self.config.symbols:
                #     tick_info = mt5.symbol_info_tick(symbol)
                #     if tick_info:
                #         tick = MarketTick(
                #             symbol=symbol,
                #             bid_price=Decimal(str(tick_info.bid)),
                #             ask_price=Decimal(str(tick_info.ask)),
                #             timestamp=datetime.fromtimestamp(tick_info.time)
                #         )
                #         
                #         for callback in self.subscribers:
                #             await callback(tick)
                
                await asyncio.sleep(self.config.update_frequency)
                
            except Exception as e:
                logger.error(f"Error monitoring MT5 prices: {e}")
                await asyncio.sleep(5)


class MarketDataManager:
    """Manager for market data feeds."""
    
    def __init__(self, config: MarketDataConfig):
        self.config = config
        self.feed = None
        self.is_started = False
    
    async def start(self):
        """Start appropriate market data feed."""
        if self.is_started:
            return
        
        try:
            if self.config.feed_type == 'mt5':
                self.feed = MT5MarketDataFeed(self.config)
            else:
                # Default to simulation
                self.feed = SimulatedMarketDataFeed(self.config)
            
            await self.feed.start()
            self.is_started = True
            logger.info(f"Started {self.config.feed_type} market data feed")
            
        except Exception as e:
            logger.error(f"Failed to start market data feed: {e}")
            # Fall back to simulation
            self.feed = SimulatedMarketDataFeed(self.config)
            await self.feed.start()
            self.is_started = True
    
    async def stop(self):
        """Stop market data feed."""
        if self.feed and self.is_started:
            await self.feed.stop()
            self.is_started = False
    
    def subscribe(self, callback: Callable[[MarketTick], None]):
        """Subscribe to market data updates."""
        if self.feed:
            self.feed.subscribe(callback)
    
    def unsubscribe(self, callback: Callable[[MarketTick], None]):
        """Unsubscribe from market data updates."""
        if self.feed:
            self.feed.unsubscribe(callback)
    
    def get_current_price(self, symbol: str) -> Optional[MarketTick]:
        """Get current price for symbol."""
        if self.feed and hasattr(self.feed, 'get_current_price'):
            return self.feed.get_current_price(symbol)
        return None


class WebSocketStreamer:
    """WebSocket streaming for real-time dashboard updates."""
    
    def __init__(self, host: str = 'localhost', port: int = 8006):
        self.host = host
        self.port = port
        self.clients = set()
        self.server = None
        self.is_running = False
    
    async def start(self):
        """Start WebSocket server."""
        if self.is_running:
            return
        
        try:
            self.server = await websockets.serve(
                self._handle_client,
                self.host,
                self.port
            )
            self.is_running = True
            logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            raise
    
    async def stop(self):
        """Stop WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.is_running = False
            logger.info("WebSocket server stopped")
    
    async def _handle_client(self, websocket, path):
        """Handle WebSocket client connection."""
        self.clients.add(websocket)
        logger.info(f"WebSocket client connected. Total: {len(self.clients)}")
        
        try:
            async for message in websocket:
                # Handle client messages (subscriptions, etc.)
                await self._process_client_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"WebSocket client error: {e}")
        finally:
            self.clients.discard(websocket)
            logger.info(f"WebSocket client disconnected. Total: {len(self.clients)}")
    
    async def _process_client_message(self, websocket, message):
        """Process message from WebSocket client."""
        try:
            data = json.loads(message)
            action = data.get('action')
            
            if action == 'subscribe':
                # Handle subscription request
                channels = data.get('channels', [])
                accounts = data.get('accounts', [])
                
                response = {
                    'type': 'subscription_confirmed',
                    'channels': channels,
                    'accounts': accounts,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                await websocket.send(json.dumps(response))
                
        except Exception as e:
            logger.error(f"Error processing client message: {e}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        if not self.clients:
            return
        
        try:
            message_json = json.dumps(message, default=str)
            
            # Send to all clients
            disconnected = []
            for client in self.clients.copy():
                try:
                    await client.send(message_json)
                except websockets.exceptions.ConnectionClosed:
                    disconnected.append(client)
                except Exception as e:
                    logger.error(f"Error sending to client: {e}")
                    disconnected.append(client)
            
            # Clean up disconnected clients
            for client in disconnected:
                self.clients.discard(client)
                
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")
    
    async def broadcast_pnl_update(self, account_id: str, pnl_data: dict):
        """Broadcast P&L update."""
        message = {
            'channel': 'pnl',
            'type': 'pnl_update',
            'account_id': account_id,
            'data': pnl_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.broadcast(message)
    
    async def broadcast_trade_update(self, account_id: str, trade_data: dict):
        """Broadcast trade update."""
        message = {
            'channel': 'trades',
            'type': 'trade_update', 
            'account_id': account_id,
            'data': trade_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.broadcast(message)
    
    async def broadcast_performance_update(self, account_id: str, metrics_data: dict):
        """Broadcast performance metrics update."""
        message = {
            'channel': 'performance',
            'type': 'metrics_update',
            'account_id': account_id,
            'data': metrics_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.broadcast(message)