"""
Simplified Execution Engine Starter
Handles missing dependencies gracefully and provides basic functionality.
"""

import os
import sys
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

# Import notification service
try:
    sys.path.append('..')
    from notification_service import notify_trade, notify_alert
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    print("Notification service not available")
    NOTIFICATIONS_AVAILABLE = False
    
    async def notify_trade(data):
        """Fallback notification function"""
        pass
    
    async def notify_alert(alert_type, message, severity="info"):
        """Fallback alert function"""
        pass

# Import trade journal service
try:
    sys.path.append('..')
    from trade_journal import record_trade_execution, record_trade_close, export_csv, get_trading_summary
    TRADE_JOURNAL_AVAILABLE = True
except ImportError:
    print("Trade journal service not available")
    TRADE_JOURNAL_AVAILABLE = False
    
    def record_trade_execution(data):
        """Fallback trade journal function"""
        pass
    
    def record_trade_close(trade_id, close_data):
        """Fallback trade close function"""
        pass
    
    def export_csv(filename=None, days_back=None):
        """Fallback CSV export function"""
        return "trade_journal_not_available.csv"
    
    def get_trading_summary():
        """Fallback summary function"""
        return {"error": "Trade journal not available"}

# Try to load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    DOTENV_AVAILABLE = True
except ImportError:
    # Fallback: manually read .env file
    DOTENV_AVAILABLE = False
    try:
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
    except Exception:
        pass

# Try to import dependencies, fallback gracefully if missing
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    FASTAPI_AVAILABLE = True
except ImportError:
    print("FastAPI not available - running in minimal mode")
    FASTAPI_AVAILABLE = False

try:
    import uvicorn
    UVICORN_AVAILABLE = True
except ImportError:
    print("Uvicorn not available")
    UVICORN_AVAILABLE = False

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    print("Structlog not available - using basic logging")
    STRUCTLOG_AVAILABLE = False

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    print("aiohttp not available - FIFO checking disabled")
    AIOHTTP_AVAILABLE = False

# Basic logging setup
if STRUCTLOG_AVAILABLE:
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logger = structlog.get_logger(__name__)
else:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

def format_oanda_price(price: float, instrument: str) -> str:
    """
    Format price according to OANDA's precision requirements.

    OANDA precision rules:
    - JPY pairs (USD/JPY, EUR/JPY, GBP/JPY, etc.): 3 decimal places
    - Most other major pairs: 5 decimal places
    - Some exotic pairs: 4 decimal places
    """
    if not price:
        return None

    # JPY pairs use 3 decimal places
    if 'JPY' in instrument.upper():
        return f"{float(price):.3f}"

    # Exotic pairs that use 4 decimal places
    exotic_4_decimal = ['USD_TRY', 'EUR_TRY', 'GBP_TRY', 'USD_ZAR', 'EUR_ZAR',
                       'USD_MXN', 'EUR_MXN', 'USD_PLN', 'EUR_PLN']

    if instrument.upper() in exotic_4_decimal:
        return f"{float(price):.4f}"

    # Most major pairs use 5 decimal places
    return f"{float(price):.5f}"

async def check_fifo_violations(instrument: str, side: str, units: int, account_id: str) -> Dict[str, Any]:
    """
    Check for potential FIFO violations before placing an order.
    FIFO (First In, First Out) rule requires closing the oldest position first
    before opening a new position in the opposite direction.
    """
    if not AIOHTTP_AVAILABLE:
        return {"fifo_violation": False, "error": "aiohttp not available"}

    try:
        api_key = os.getenv("OANDA_API_KEY")
        base_url = "https://api-fxpractice.oanda.com"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Get current positions for this instrument
        async with aiohttp.ClientSession() as session:
            url = f"{base_url}/v3/accounts/{account_id}/positions/{instrument}"
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    position = data.get("position", {})

                    current_long_units = float(position.get("long", {}).get("units", 0))
                    current_short_units = float(position.get("short", {}).get("units", 0))

                    # Check for FIFO violations
                    new_units = units if side == "buy" else -units

                    # If we have existing positions and trying to open opposite direction
                    if ((current_long_units > 0 and new_units < 0) or
                        (current_short_units < 0 and new_units > 0)):

                        return {
                            "fifo_violation": True,
                            "current_long": current_long_units,
                            "current_short": current_short_units,
                            "new_units": new_units,
                            "suggestion": "Close existing position first or adjust order size"
                        }

                    return {
                        "fifo_violation": False,
                        "current_long": current_long_units,
                        "current_short": current_short_units,
                        "new_units": new_units
                    }

                return {"fifo_violation": False, "error": f"Could not check positions: {response.status}"}

    except Exception as e:
        logger.error(f"Error checking FIFO violations: {e}")
        return {"fifo_violation": False, "error": str(e)}

class PositionMonitor:
    """Position monitoring service for exit conditions"""
    
    def __init__(self):
        self.monitoring_positions = {}
        self.monitor_task = None
        self.running = False
    
    async def start_monitoring(self):
        """Start position monitoring task"""
        if not self.running:
            self.running = True
            self.monitor_task = asyncio.create_task(self._monitor_positions())
            logger.info("Position monitoring started")
    
    async def stop_monitoring(self):
        """Stop position monitoring task"""
        self.running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            logger.info("Position monitoring stopped")
    
    def add_position(self, trade_id: str, signal_data: Dict):
        """Add position to monitoring"""
        self.monitoring_positions[trade_id] = {
            'signal_data': signal_data,
            'monitored_since': datetime.now(),
            'last_check': None,
            'pattern_invalidated': False
        }
        logger.info(f"Added position {trade_id} to monitoring")
    
    async def _monitor_positions(self):
        """Main monitoring loop"""
        while self.running:
            try:
                await self._check_all_positions()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in position monitoring: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _check_all_positions(self):
        """Check all monitored positions for exit conditions"""
        if not self.monitoring_positions:
            return
        
        # Get current positions from OANDA
        try:
            import httpx
            api_key = os.getenv("OANDA_API_KEY")
            account_id = os.getenv("OANDA_ACCOUNT_ID")
            
            if not api_key or not account_id:
                return
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f'https://api-fxpractice.oanda.com/v3/accounts/{account_id}/trades',
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    current_trades = {trade['id']: trade for trade in data.get('trades', [])}
                    
                    # Check monitored positions
                    positions_to_remove = []
                    for trade_id, monitor_data in self.monitoring_positions.items():
                        if trade_id not in current_trades:
                            # Position was closed (by stop loss, take profit, or manual close)
                            logger.info(f"Position {trade_id} was closed - removing from monitoring")
                            positions_to_remove.append(trade_id)
                            
                            # Send notification for closed position
                            try:
                                signal_data = monitor_data.get('signal_data', {})
                                instrument = signal_data.get('instrument', 'Unknown')
                                await notify_alert("position_auto_closed", 
                                                 f"Position {trade_id} ({instrument}) automatically closed (Stop Loss/Take Profit triggered)", 
                                                 "info")
                            except Exception as e:
                                logger.error(f"Error sending position close notification: {e}")
                        else:
                            # Position still open - check for pattern invalidation
                            trade = current_trades[trade_id]
                            await self._check_pattern_invalidation(trade_id, trade, monitor_data)
                    
                    # Remove closed positions from monitoring
                    for trade_id in positions_to_remove:
                        del self.monitoring_positions[trade_id]
                        
        except Exception as e:
            logger.error(f"Error checking positions: {e}")
    
    async def _check_pattern_invalidation(self, trade_id: str, trade_data: Dict, monitor_data: Dict):
        """Check if trading pattern has been invalidated"""
        try:
            signal_data = monitor_data['signal_data']
            current_price = float(trade_data.get('unrealizedPL', 0))
            
            # Simple pattern invalidation rules
            hold_time = datetime.now() - monitor_data['monitored_since']
            max_hold_hours = signal_data.get('max_hold_time_hours', 48)  # Default 48 hours
            
            if hold_time > timedelta(hours=max_hold_hours):
                logger.warning(f"Position {trade_id} held beyond maximum time ({max_hold_hours}h) - pattern may be invalidated")
                monitor_data['pattern_invalidated'] = True
            
            monitor_data['last_check'] = datetime.now()
            
        except Exception as e:
            logger.error(f"Error checking pattern invalidation for {trade_id}: {e}")


class ExecutionEngineState:
    """Simplified execution engine state"""
    
    def __init__(self):
        self.initialized = False
        self.start_time = datetime.now()
        self.oanda_configured = bool(os.getenv("OANDA_API_KEY"))
        self.environment = os.getenv("OANDA_ENVIRONMENT", "practice")
        self.paper_trading_mode = os.getenv("PAPER_TRADING_MODE", "false").lower() == "true"
        self.paper_trading_balance = float(os.getenv("PAPER_TRADING_BALANCE", "100000"))
        self.position_monitor = PositionMonitor()
        
    def get_status(self) -> Dict[str, Any]:
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "service": "execution-engine",
            "status": "running",
            "mode": "simplified" if not FASTAPI_AVAILABLE else "full",
            "uptime_seconds": int(uptime),
            "oanda_configured": self.oanda_configured,
            "environment": self.environment,
            "paper_trading_mode": self.paper_trading_mode,
            "paper_trading_balance": self.paper_trading_balance,
            "dependencies": {
                "fastapi": FASTAPI_AVAILABLE,
                "uvicorn": UVICORN_AVAILABLE,
                "structlog": STRUCTLOG_AVAILABLE,
                "dotenv": DOTENV_AVAILABLE
            },
            "timestamp": datetime.now().isoformat()
        }

# Global state
app_state = ExecutionEngineState()

if FASTAPI_AVAILABLE:
    # Full FastAPI application
    app = FastAPI(
        title="TMT Execution Engine",
        description="High-performance execution engine for automated trading",
        version="1.0.0"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return JSONResponse(content=app_state.get_status())
    
    @app.get("/status")
    async def status():
        """Detailed status endpoint"""
        return JSONResponse(content=app_state.get_status())
    
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {"message": "TMT Execution Engine - Simplified Mode", "status": "running"}
    
    @app.post("/orders/market")
    async def create_market_order(order_data: dict):
        """Market order endpoint - supports both paper trading and real OANDA practice orders"""
        logger.info("Market order received", order_data=order_data)
        
        # VALIDATION: Check for risk parameters on significant orders
        units = order_data.get("units", 0)
        if abs(units) > 10000 and not app_state.paper_trading_mode:
            # Large positions must have stop-loss unless explicitly bypassed
            if not order_data.get("stop_loss_price") and not order_data.get("allow_no_sl", False):
                logger.error(f"Rejected order: Large position ({units} units) without stop-loss")
                return JSONResponse({
                    "error": "Large positions (>10000 units) require stop_loss_price or explicit allow_no_sl=true flag",
                    "units": units,
                    "instrument": order_data.get("instrument"),
                    "recommendation": "Add stop_loss_price to order or set allow_no_sl=true to bypass (not recommended)"
                }, status_code=400)
            
            # Warn about missing take-profit but don't block
            if not order_data.get("take_profit_price"):
                logger.warning(f"Large position ({units} units) without take-profit - allowing but not recommended")
        
        if app_state.paper_trading_mode:
            # Paper trading mode - simulate order
            order_id = f"paper_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
            # Prepare notification data for paper trading
            notification_data = {
                "success": True,
                "mode": "paper_trading",
                "instrument": order_data.get("instrument", "Unknown"),
                "fill_price": order_data.get("price", 1.0000),
                "units_filled": order_data.get("units", 1000) if order_data.get("side", "buy") == "buy" else -order_data.get("units", 1000),
                "trade_id": order_id,
                "stop_loss_set": bool(order_data.get("stop_loss_price")),
                "take_profit_set": bool(order_data.get("take_profit_price")),
                "pl": 0.0  # No P&L for paper trades yet
            }
            
            # Send notification and record in journal
            try:
                logger.info(f"Sending notification for trade: {notification_data}")
                await notify_trade(notification_data)
                logger.info("Notification sent successfully")
                record_trade_execution(notification_data)
                logger.info("Trade recorded in journal")
            except Exception as e:
                logger.error(f"Error sending notification or recording trade: {e}")
                import traceback
                traceback.print_exc()
            
            return {
                "success": True,
                "mode": "paper_trading",
                "order_id": order_id,
                "status": "filled",
                "fill_price": order_data.get("price", 1.0000),
                "message": "Paper trading order simulated",
                "order_data": order_data,
                "paper_trading_balance": app_state.paper_trading_balance
            }
        else:
            # Real OANDA practice trading mode
            try:
                import httpx
                
                # Extract order details
                account_id = order_data.get("account_id", os.getenv("OANDA_ACCOUNT_ID"))
                instrument = order_data.get("instrument")
                side = order_data.get("side", "buy")
                units = order_data.get("units", 1000)
                stop_loss_price = order_data.get("stop_loss_price")
                take_profit_price = order_data.get("take_profit_price")
                
                # CRITICAL SAFETY: Calculate default TP/SL if not provided
                if not stop_loss_price or not take_profit_price:
                    logger.warning(f"Missing TP/SL for {instrument} - calculating defaults")
                    
                    # Get current price (use entry price from order as estimate)
                    entry_price = order_data.get("entry_price")
                    if not entry_price:
                        # Fetch current price from OANDA
                        try:
                            api_key = os.getenv("OANDA_API_KEY")
                            price_url = f"https://api-fxpractice.oanda.com/v3/accounts/{account_id}/pricing?instruments={instrument}"
                            price_headers = {"Authorization": f"Bearer {api_key}"}
                            price_response = requests.get(price_url, headers=price_headers)
                            if price_response.status_code == 200:
                                prices = price_response.json()["prices"][0]
                                entry_price = float(prices["bids"][0]["price"]) if side == "sell" else float(prices["asks"][0]["price"])
                            else:
                                logger.error(f"Could not fetch price for {instrument}")
                                return JSONResponse({"error": "Cannot place order without price and TP/SL"}, status_code=400)
                        except Exception as e:
                            logger.error(f"Price fetch error: {e}")
                            return JSONResponse({"error": "Cannot place order without TP/SL"}, status_code=400)
                    else:
                        entry_price = float(entry_price)
                    
                    # Calculate default stops based on instrument type
                    if "JPY" in instrument:
                        pip_size = 0.01
                        default_sl_pips = 30  # Conservative 30 pip stop for JPY pairs
                        default_tp_pips = 45  # 1.5:1 R:R ratio
                    else:
                        pip_size = 0.0001
                        default_sl_pips = 30  # Conservative 30 pip stop
                        default_tp_pips = 45  # 1.5:1 R:R ratio
                    
                    # Calculate actual prices with proper precision
                    precision = 3 if 'JPY' in instrument.upper() else 5

                    if side == "buy":
                        if not stop_loss_price:
                            stop_loss_price = round(entry_price - (default_sl_pips * pip_size), precision)
                        if not take_profit_price:
                            take_profit_price = round(entry_price + (default_tp_pips * pip_size), precision)
                    else:  # sell
                        if not stop_loss_price:
                            stop_loss_price = round(entry_price + (default_sl_pips * pip_size), precision)
                        if not take_profit_price:
                            take_profit_price = round(entry_price - (default_tp_pips * pip_size), precision)

                    logger.warning(f"Using default TP/SL for {instrument}: SL={stop_loss_price}, TP={take_profit_price}")
                
                # Convert side to units (OANDA uses positive/negative units)
                oanda_units = units if side == "buy" else -units
                
                # Prepare OANDA order data with stop loss and take profit
                oanda_order_data = {
                    "order": {
                        "type": "MARKET",
                        "instrument": instrument,
                        "units": str(oanda_units),
                        "timeInForce": "IOC"  # Immediate or Cancel
                    }
                }
                
                # Check for FIFO violations before placing order
                account_id = order_data.get("account_id", os.getenv("OANDA_ACCOUNT_ID", "101-001-21040028-001"))
                fifo_check = await check_fifo_violations(instrument, side, units, account_id)

                if fifo_check.get("fifo_violation"):
                    logger.warning(f"FIFO violation detected for {instrument}: {fifo_check}")
                    # Continue with order but log the warning - OANDA will handle the violation

                # Add stop loss order if provided (with proper price formatting)
                if stop_loss_price:
                    formatted_sl = format_oanda_price(stop_loss_price, instrument)
                    oanda_order_data["order"]["stopLossOnFill"] = {
                        "price": formatted_sl,
                        "timeInForce": "GTC",
                        "triggerMode": "TOP_OF_BOOK"
                    }
                    logger.info(f"Adding stop loss at {formatted_sl} (formatted from {stop_loss_price})")

                # Add take profit order if provided (with proper price formatting)
                if take_profit_price:
                    formatted_tp = format_oanda_price(take_profit_price, instrument)
                    oanda_order_data["order"]["takeProfitOnFill"] = {
                        "price": formatted_tp,
                        "timeInForce": "GTC"
                    }
                    logger.info(f"Adding take profit at {formatted_tp} (formatted from {take_profit_price})")
                
                # OANDA API configuration
                api_key = os.getenv("OANDA_API_KEY")
                base_url = "https://api-fxpractice.oanda.com"

                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }

                # Check for FIFO violations before placing order
                fifo_violations = await check_fifo_violations(instrument, side, units, account_id)
                if fifo_violations:
                    logger.warning(f"FIFO violations detected for {instrument}: {fifo_violations}")
                    logger.info(f"Proceeding with order placement despite FIFO warnings (may be rejected by OANDA)")

                # Place order with OANDA
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{base_url}/v3/accounts/{account_id}/orders",
                        headers=headers,
                        json=oanda_order_data,
                        timeout=10.0
                    )
                    
                    if response.status_code == 201:
                        result = response.json()
                        order_fill = result.get("orderFillTransaction", {})
                        trade_opened = result.get("tradeOpened", {})
                        
                        # Add position to monitoring if trade was opened
                        if trade_opened:
                            trade_id = trade_opened.get("tradeID")
                            if trade_id:
                                signal_data = {
                                    'instrument': instrument,
                                    'entry_price': float(order_fill.get("price", 0.0)),
                                    'stop_loss': stop_loss_price,
                                    'take_profit': take_profit_price,
                                    'max_hold_time_hours': order_data.get('max_hold_time_hours', 48),
                                    'signal_id': order_data.get('signal_id'),
                                    'units': float(order_fill.get("units", 0))
                                }
                                app_state.position_monitor.add_position(trade_id, signal_data)
                        
                        # Prepare notification data for successful OANDA trade
                        notification_data = {
                            "success": True,
                            "mode": "oanda_practice",
                            "instrument": order_fill.get("instrument"),
                            "fill_price": float(order_fill.get("price", 0.0)),
                            "units_filled": float(order_fill.get("units", 0)),
                            "trade_id": trade_opened.get("tradeID") if trade_opened else order_fill.get("id", "unknown"),
                            "stop_loss_set": bool(stop_loss_price),
                            "take_profit_set": bool(take_profit_price),
                            "pl": float(order_fill.get("pl", 0.0)),
                            "commission": float(order_fill.get("commission", 0.0)),
                            "financing": float(order_fill.get("financing", 0.0))
                        }
                        
                        # Send notification and record in journal
                        try:
                            await notify_trade(notification_data)
                            record_trade_execution(notification_data)
                        except Exception as e:
                            logger.error(f"Error sending notification or recording trade: {e}")
                        
                        return {
                            "success": True,
                            "mode": "oanda_practice",
                            "order_id": order_fill.get("id", "unknown"),
                            "trade_id": trade_opened.get("tradeID") if trade_opened else None,
                            "status": "filled",
                            "fill_price": float(order_fill.get("price", 0.0)),
                            "units_filled": float(order_fill.get("units", 0)),
                            "instrument": order_fill.get("instrument"),
                            "pl": float(order_fill.get("pl", 0.0)),
                            "commission": float(order_fill.get("commission", 0.0)),
                            "financing": float(order_fill.get("financing", 0.0)),
                            "stop_loss_set": bool(stop_loss_price),
                            "take_profit_set": bool(take_profit_price),
                            "monitoring_enabled": True,
                            "message": "OANDA practice order executed successfully with monitoring",
                            "order_data": order_data,
                            "oanda_response": result
                        }
                    else:
                        error_text = response.text
                        
                        # Prepare notification data for failed trade
                        notification_data = {
                            "success": False,
                            "mode": "oanda_practice",
                            "instrument": instrument,
                            "message": f"OANDA order failed: {response.status_code} - {error_text}"
                        }
                        
                        # Send notification and record in journal
                        try:
                            await notify_trade(notification_data)
                            record_trade_execution(notification_data)
                        except Exception as e:
                            logger.error(f"Error sending notification or recording trade: {e}")
                        
                        return {
                            "success": False,
                            "mode": "oanda_practice",
                            "message": f"OANDA order failed: {response.status_code} - {error_text}",
                            "order_data": order_data
                        }
                        
            except Exception as e:
                # Prepare notification data for exception error
                notification_data = {
                    "success": False,
                    "mode": "oanda_practice",
                    "instrument": order_data.get("instrument", "Unknown"),
                    "message": f"OANDA order error: {str(e)}"
                }
                
                # Send notification
                try:
                    await notify_trade(notification_data)
                    await notify_alert("execution_error", f"Trade execution failed: {str(e)}", "error")
                except Exception as notify_error:
                    logger.error(f"Error sending notification: {notify_error}")
                
                return {
                    "success": False,
                    "mode": "oanda_practice",
                    "message": f"OANDA order error: {str(e)}",
                    "order_data": order_data
                }
    
    @app.get("/positions")
    async def get_positions():
        """Get current positions from OANDA"""
        if app_state.paper_trading_mode:
            return {
                "positions": [],
                "mode": "paper_trading",
                "message": "Paper trading mode - no real positions"
            }
        
        try:
            import httpx
            api_key = os.getenv("OANDA_API_KEY")
            account_id = os.getenv("OANDA_ACCOUNT_ID")
            
            if not api_key or not account_id:
                return {"error": "OANDA credentials not configured"}
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f'https://api-fxpractice.oanda.com/v3/accounts/{account_id}/trades',
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    trades = data.get('trades', [])
                    
                    positions = []
                    for trade in trades:
                        positions.append({
                            'trade_id': trade.get('id'),
                            'instrument': trade.get('instrument'),
                            'units': trade.get('currentUnits'),
                            'entry_price': trade.get('price'),
                            'unrealized_pl': trade.get('unrealizedPL'),
                            'open_time': trade.get('openTime'),
                            'stop_loss': trade.get('stopLossOrder', {}).get('price') if trade.get('stopLossOrder') else None,
                            'take_profit': trade.get('takeProfitOrder', {}).get('price') if trade.get('takeProfitOrder') else None,
                            'monitored': trade.get('id') in app_state.position_monitor.monitoring_positions
                        })
                    
                    return {
                        "positions": positions,
                        "mode": "oanda_practice",
                        "total_positions": len(positions),
                        "monitoring_active": app_state.position_monitor.running
                    }
                else:
                    return {"error": f"OANDA API error: {response.status_code}"}
                    
        except Exception as e:
            return {"error": f"Failed to get positions: {str(e)}"}
    
    @app.post("/positions/close/{trade_id}")
    async def close_position(trade_id: str, close_data: dict = {}):
        """Emergency position close endpoint"""
        logger.warning(f"Emergency close requested for trade {trade_id}")
        
        if app_state.paper_trading_mode:
            return {
                "success": True,
                "mode": "paper_trading",
                "message": f"Paper trade {trade_id} closed (simulated)"
            }
        
        try:
            import httpx
            api_key = os.getenv("OANDA_API_KEY")
            account_id = os.getenv("OANDA_ACCOUNT_ID")
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # Close the trade
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f'https://api-fxpractice.oanda.com/v3/accounts/{account_id}/trades/{trade_id}/close',
                    headers=headers,
                    json={"units": "ALL"}  # Close entire position
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Remove from monitoring
                    if trade_id in app_state.position_monitor.monitoring_positions:
                        del app_state.position_monitor.monitoring_positions[trade_id]
                    
                    # Send position close notification
                    try:
                        await notify_alert("position_closed", f"Position {trade_id} closed successfully", "info")
                    except Exception as e:
                        logger.error(f"Error sending close notification: {e}")
                    
                    return {
                        "success": True,
                        "mode": "oanda_practice",
                        "trade_id": trade_id,
                        "message": "Position closed successfully",
                        "close_result": result
                    }
                else:
                    return {
                        "success": False,
                        "mode": "oanda_practice",
                        "message": f"Failed to close position: {response.status_code}",
                        "error": response.text
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "message": f"Error closing position: {str(e)}"
            }
    
    @app.post("/emergency/close_all")
    async def emergency_close_all():
        """Emergency close all positions"""
        logger.critical("EMERGENCY: Close all positions requested")
        
        if app_state.paper_trading_mode:
            return {
                "success": True,
                "mode": "paper_trading",
                "message": "All paper positions closed (simulated)"
            }
        
        try:
            import httpx
            api_key = os.getenv("OANDA_API_KEY")
            account_id = os.getenv("OANDA_ACCOUNT_ID")
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # Get all open trades first
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f'https://api-fxpractice.oanda.com/v3/accounts/{account_id}/trades',
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    trades = data.get('trades', [])
                    
                    closed_trades = []
                    failed_trades = []
                    
                    # Close each trade
                    for trade in trades:
                        trade_id = trade.get('id')
                        try:
                            close_response = await client.put(
                                f'https://api-fxpractice.oanda.com/v3/accounts/{account_id}/trades/{trade_id}/close',
                                headers=headers,
                                json={"units": "ALL"}
                            )
                            
                            if close_response.status_code == 200:
                                closed_trades.append(trade_id)
                                # Remove from monitoring
                                if trade_id in app_state.position_monitor.monitoring_positions:
                                    del app_state.position_monitor.monitoring_positions[trade_id]
                            else:
                                failed_trades.append(trade_id)
                                
                        except Exception as e:
                            failed_trades.append(trade_id)
                            logger.error(f"Failed to close trade {trade_id}: {e}")
                    
                    return {
                        "success": len(failed_trades) == 0,
                        "mode": "oanda_practice",
                        "total_trades": len(trades),
                        "closed_trades": closed_trades,
                        "failed_trades": failed_trades,
                        "message": f"Emergency close completed: {len(closed_trades)} closed, {len(failed_trades)} failed"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to get trades list: {response.status_code}"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "message": f"Emergency close failed: {str(e)}"
            }
    
    @app.get("/monitoring/status")
    async def get_monitoring_status():
        """Get position monitoring status"""
        return {
            "monitoring_active": app_state.position_monitor.running,
            "positions_monitored": len(app_state.position_monitor.monitoring_positions),
            "monitor_details": {
                trade_id: {
                    'instrument': data['signal_data'].get('instrument'),
                    'monitored_since': data['monitored_since'].isoformat(),
                    'last_check': data['last_check'].isoformat() if data['last_check'] else None,
                    'pattern_invalidated': data['pattern_invalidated']
                }
                for trade_id, data in app_state.position_monitor.monitoring_positions.items()
            }
        }
    
    @app.post("/monitoring/start")
    async def start_monitoring():
        """Manually start position monitoring"""
        try:
            await app_state.position_monitor.start_monitoring()
            return {
                "success": True,
                "message": "Position monitoring started",
                "monitoring_active": app_state.position_monitor.running
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to start monitoring: {str(e)}"
            }
    
    @app.post("/monitoring/add_existing_positions")
    async def add_existing_positions():
        """Add existing OANDA positions to monitoring"""
        if app_state.paper_trading_mode:
            return {
                "success": True,
                "message": "Paper trading mode - no positions to monitor"
            }
        
        try:
            import httpx
            api_key = os.getenv("OANDA_API_KEY")
            account_id = os.getenv("OANDA_ACCOUNT_ID")
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f'https://api-fxpractice.oanda.com/v3/accounts/{account_id}/trades',
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    trades = data.get('trades', [])
                    
                    added_count = 0
                    for trade in trades:
                        trade_id = trade.get('id')
                        if trade_id not in app_state.position_monitor.monitoring_positions:
                            # Add existing position to monitoring with default data
                            signal_data = {
                                'instrument': trade.get('instrument'),
                                'entry_price': float(trade.get('price', 0)),
                                'stop_loss': trade.get('stopLossOrder', {}).get('price') if trade.get('stopLossOrder') else None,
                                'take_profit': trade.get('takeProfitOrder', {}).get('price') if trade.get('takeProfitOrder') else None,
                                'max_hold_time_hours': 48,  # Default
                                'signal_id': f'existing_{trade_id}',
                                'units': float(trade.get('currentUnits', 0))
                            }
                            app_state.position_monitor.add_position(trade_id, signal_data)
                            added_count += 1
                    
                    return {
                        "success": True,
                        "message": f"Added {added_count} existing positions to monitoring",
                        "total_trades": len(trades),
                        "added_to_monitoring": added_count
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to get trades: {response.status_code}"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "message": f"Error adding existing positions: {str(e)}"
            }
    
    @app.get("/journal/summary")
    async def get_journal_summary():
        """Get trading journal summary"""
        try:
            summary = get_trading_summary()
            return {
                "success": True,
                "summary": summary,
                "journal_available": TRADE_JOURNAL_AVAILABLE
            }
        except Exception as e:
            logger.error(f"Error getting journal summary: {e}")
            return {
                "success": False,
                "message": f"Failed to get summary: {str(e)}"
            }
    
    @app.post("/journal/export")
    async def export_journal_csv(export_params: dict = {}):
        """Export trade journal to CSV"""
        try:
            filename = export_params.get("filename")
            days_back = export_params.get("days_back")
            
            exported_file = export_csv(filename, days_back)
            
            return {
                "success": True,
                "message": "Trade journal exported successfully",
                "filename": exported_file,
                "journal_available": TRADE_JOURNAL_AVAILABLE
            }
        except Exception as e:
            logger.error(f"Error exporting journal: {e}")
            return {
                "success": False,
                "message": f"Failed to export journal: {str(e)}"
            }
    
    @app.get("/metrics")
    async def get_metrics():
        """Comprehensive metrics endpoint for monitoring"""
        try:
            # Get current time and uptime
            current_time = datetime.now()
            uptime_seconds = (current_time - app_state.start_time).total_seconds()
            
            # Get OANDA account info if available
            oanda_metrics = {"account_balance": "N/A", "unrealized_pl": "N/A", "open_trades": 0}
            
            if not app_state.paper_trading_mode and app_state.oanda_configured:
                try:
                    import httpx
                    api_key = os.getenv("OANDA_API_KEY")
                    account_id = os.getenv("OANDA_ACCOUNT_ID")
                    
                    headers = {
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json'
                    }
                    
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            f'https://api-fxpractice.oanda.com/v3/accounts/{account_id}',
                            headers=headers
                        )
                        
                        if response.status_code == 200:
                            account_data = response.json()
                            account = account_data.get('account', {})
                            oanda_metrics = {
                                "account_balance": float(account.get('balance', 0)),
                                "unrealized_pl": float(account.get('unrealizedPL', 0)),
                                "open_trades": int(account.get('openTradeCount', 0)),
                                "margin_used": float(account.get('marginUsed', 0)),
                                "margin_available": float(account.get('marginAvailable', 0))
                            }
                except Exception as e:
                    logger.warning(f"Could not fetch OANDA metrics: {e}")
            
            # Get trade journal metrics
            journal_metrics = get_trading_summary()
            
            # Position monitoring metrics
            monitoring_metrics = {
                "monitoring_active": app_state.position_monitor.running,
                "positions_monitored": len(app_state.position_monitor.monitoring_positions),
                "monitoring_uptime_seconds": uptime_seconds if app_state.position_monitor.running else 0
            }
            
            # System health metrics
            system_metrics = {
                "service_uptime_seconds": uptime_seconds,
                "service_uptime_hours": round(uptime_seconds / 3600, 2),
                "mode": "paper_trading" if app_state.paper_trading_mode else "oanda_practice",
                "oanda_configured": app_state.oanda_configured,
                "environment": app_state.environment,
                "dependencies": {
                    "fastapi": FASTAPI_AVAILABLE,
                    "notifications": NOTIFICATIONS_AVAILABLE,
                    "trade_journal": TRADE_JOURNAL_AVAILABLE
                },
                "timestamp": current_time.isoformat(),
                "start_time": app_state.start_time.isoformat()
            }
            
            return {
                "success": True,
                "metrics": {
                    "system": system_metrics,
                    "oanda_account": oanda_metrics,
                    "trading_journal": journal_metrics,
                    "position_monitoring": monitoring_metrics
                },
                "health_status": "healthy" if uptime_seconds > 30 else "starting"
            }
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return {
                "success": False,
                "message": f"Failed to collect metrics: {str(e)}",
                "health_status": "error"
            }

def run_http_server():
    """Run a simple HTTP server if FastAPI is not available"""
    import http.server
    import socketserver
    from urllib.parse import urlparse, parse_qs
    
    class SimpleHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed_path = urlparse(self.path)
            
            if parsed_path.path in ['/health', '/status']:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps(app_state.get_status())
                self.wfile.write(response.encode())
            
            elif parsed_path.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps({
                    "message": "TMT Execution Engine - Minimal Mode",
                    "status": "running",
                    "note": "FastAPI not available - using basic HTTP server"
                })
                self.wfile.write(response.encode())
            
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = json.dumps({"error": "Not found"})
                self.wfile.write(response.encode())
        
        def log_message(self, format, *args):
            # Suppress default logging
            pass
    
    PORT = 8082
    print(f"Starting minimal HTTP server on port {PORT}")
    print("Available endpoints:")
    print(f"  http://localhost:{PORT}/")
    print(f"  http://localhost:{PORT}/health")
    print(f"  http://localhost:{PORT}/status")
    
    with socketserver.TCPServer(("", PORT), SimpleHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")

async def startup_monitoring():
    """Start position monitoring on application startup"""
    logger.info("Starting position monitoring service")
    await app_state.position_monitor.start_monitoring()

async def shutdown_monitoring():
    """Stop position monitoring on application shutdown"""
    logger.info("Stopping position monitoring service")
    await app_state.position_monitor.stop_monitoring()

def main():
    """Main entry point"""
    logger.info("Starting TMT Execution Engine")
    
    app_state.initialized = True
    
    if FASTAPI_AVAILABLE and UVICORN_AVAILABLE:
        # Add startup and shutdown events for monitoring
        app.add_event_handler("startup", startup_monitoring)
        app.add_event_handler("shutdown", shutdown_monitoring)
        
        logger.info("Starting with FastAPI and Uvicorn")
        uvicorn.run(
            "simple_main:app",
            host="0.0.0.0",
            port=8082,
            reload=False,
            log_level="info"
        )
    else:
        logger.info("Starting with minimal HTTP server")
        run_http_server()

if __name__ == "__main__":
    main()