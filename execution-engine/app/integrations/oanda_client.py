"""
OANDA v20 API Integration for Execution Engine

High-performance OANDA client optimized for sub-100ms execution.
Includes connection pooling, retry logic, and comprehensive error handling.
"""

import asyncio
import time
from decimal import Decimal
from typing import Dict, List, Optional, NamedTuple
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from ..core.models import Order, Position, AccountSummary

logger = structlog.get_logger(__name__)


@dataclass
class OandaConfig:
    """OANDA API configuration."""
    api_key: str
    account_id: str
    environment: str = "practice"  # "practice" or "live"
    timeout: float = 5.0
    max_retries: int = 3
    rate_limit_per_second: int = 100


class ExecutionResult(NamedTuple):
    """Result of order execution."""
    success: bool
    oanda_order_id: Optional[str] = None
    fill_price: Optional[Decimal] = None
    execution_time_ms: Optional[int] = None
    slippage: Optional[Decimal] = None
    commission: Optional[Decimal] = None
    realized_pl: Optional[Decimal] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class MarginInfo(NamedTuple):
    """Margin requirement information."""
    margin_used: Decimal
    margin_rate: Decimal


class InstrumentInfo(NamedTuple):
    """Instrument information."""
    name: str
    tradeable: bool
    pip_location: int
    display_precision: int


class ConnectionPool:
    """HTTP connection pool optimized for OANDA API."""
    
    def __init__(self, config: OandaConfig, pool_size: int = 10):
        self.config = config
        self.pool_size = pool_size
        
        # Base URLs
        if config.environment == "live":
            self.api_base = "https://api-fxtrade.oanda.com"
            self.stream_base = "https://stream-fxtrade.oanda.com"
        else:
            self.api_base = "https://api-fxpractice.oanda.com"
            self.stream_base = "https://stream-fxpractice.oanda.com"
        
        # HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(config.timeout),
            limits=httpx.Limits(
                max_keepalive_connections=pool_size,
                max_connections=pool_size * 2,
                keepalive_expiry=30.0,
            ),
        )
        
        # Rate limiting
        self.rate_limiter = asyncio.Semaphore(config.rate_limit_per_second)
        
        logger.info("OANDA connection pool initialized", 
                   environment=config.environment,
                   pool_size=pool_size)
    
    async def close(self):
        """Close connection pool."""
        await self.client.aclose()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Make rate-limited HTTP request with retry logic."""
        async with self.rate_limiter:
            url = urljoin(self.api_base, endpoint)
            response = await self.client.request(method, url, **kwargs)
            
            # Check for rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 1))
                await asyncio.sleep(retry_after)
                raise httpx.HTTPStatusError("Rate limited", request=response.request, response=response)
            
            response.raise_for_status()
            return response


class OandaExecutionClient:
    """
    High-performance OANDA execution client.
    
    Optimized for:
    - Sub-100ms order execution
    - Connection pooling and reuse
    - Comprehensive error handling
    - Real-time position tracking
    """
    
    def __init__(self, config: OandaConfig):
        self.config = config
        self.connection_pool = ConnectionPool(config)
        
        # Performance tracking
        self.execution_times: List[float] = []
        self.success_count = 0
        self.error_count = 0
        
        logger.info("OandaExecutionClient initialized", 
                   account_id=config.account_id,
                   environment=config.environment)
    
    async def close(self):
        """Close OANDA client."""
        await self.connection_pool.close()
    
    async def execute_market_order(self, order: Order) -> ExecutionResult:
        """
        Execute market order with sub-100ms target.
        """
        start_time = time.perf_counter()
        
        try:
            # Prepare order payload
            payload = {
                "order": {
                    "type": "MARKET",
                    "instrument": order.instrument,
                    "units": str(int(order.units)) if order.is_buy() else str(-int(abs(order.units))),
                    "timeInForce": order.time_in_force.value.upper(),
                }
            }
            
            # Add stop loss if specified
            if order.stop_loss:
                payload["order"]["stopLossOnFill"] = {
                    "price": str(order.stop_loss.price),
                    "guaranteed": order.stop_loss.guaranteed,
                }
            
            # Add take profit if specified
            if order.take_profit:
                payload["order"]["takeProfitOnFill"] = {
                    "price": str(order.take_profit.price),
                }
            
            # Add client extensions
            if order.client_extensions:
                payload["order"]["clientExtensions"] = {
                    "id": order.client_extensions.id,
                    "tag": order.client_extensions.tag,
                    "comment": order.client_extensions.comment,
                }
            
            # Execute order
            endpoint = f"/v3/accounts/{self.config.account_id}/orders"
            response = await self.connection_pool.request("POST", endpoint, json=payload)
            
            execution_time_ms = int((time.perf_counter() - start_time) * 1000)
            self.execution_times.append(execution_time_ms)
            
            if response.status_code == 201:
                data = response.json()
                
                # Extract order fill information
                order_fill = data.get("orderFillTransaction", {})
                if order_fill:
                    fill_price = Decimal(order_fill.get("price", "0"))
                    oanda_order_id = order_fill.get("orderID")
                    commission = Decimal(order_fill.get("commission", "0"))
                    
                    # Calculate slippage if we have a requested price
                    slippage = None
                    if order.requested_price:
                        slippage = abs(fill_price - order.requested_price)
                    
                    self.success_count += 1
                    
                    logger.info("Market order executed successfully",
                               order_id=order.id,
                               oanda_order_id=oanda_order_id,
                               fill_price=fill_price,
                               execution_time_ms=execution_time_ms)
                    
                    return ExecutionResult(
                        success=True,
                        oanda_order_id=oanda_order_id,
                        fill_price=fill_price,
                        execution_time_ms=execution_time_ms,
                        slippage=slippage,
                        commission=commission,
                    )
                else:
                    # Order placed but not immediately filled
                    order_create = data.get("orderCreateTransaction", {})
                    oanda_order_id = order_create.get("id")
                    
                    return ExecutionResult(
                        success=True,
                        oanda_order_id=oanda_order_id,
                        execution_time_ms=execution_time_ms,
                    )
            else:
                self.error_count += 1
                error_data = response.json()
                error_message = error_data.get("errorMessage", "Unknown error")
                
                logger.error("Market order execution failed",
                           order_id=order.id,
                           status_code=response.status_code,
                           error=error_message)
                
                return ExecutionResult(
                    success=False,
                    execution_time_ms=execution_time_ms,
                    error_code=str(response.status_code),
                    error_message=error_message,
                )
                
        except Exception as e:
            execution_time_ms = int((time.perf_counter() - start_time) * 1000)
            self.error_count += 1
            
            logger.error("Market order execution exception",
                        order_id=order.id,
                        error=str(e),
                        execution_time_ms=execution_time_ms)
            
            return ExecutionResult(
                success=False,
                execution_time_ms=execution_time_ms,
                error_code="EXECUTION_EXCEPTION",
                error_message=str(e),
            )
    
    async def submit_pending_order(self, order: Order) -> ExecutionResult:
        """Submit pending order (limit, stop, etc.)."""
        try:
            # Determine OANDA order type
            oanda_type_map = {
                "limit": "LIMIT",
                "stop": "STOP",
                "stop_limit": "STOP_LIMIT",
                "trailing_stop": "TRAILING_STOP_LOSS",
                "market_if_touched": "MARKET_IF_TOUCHED",
            }
            
            oanda_type = oanda_type_map.get(order.type.value)
            if not oanda_type:
                return ExecutionResult(
                    success=False,
                    error_code="UNSUPPORTED_ORDER_TYPE",
                    error_message=f"Order type {order.type} not supported",
                )
            
            # Prepare order payload
            payload = {
                "order": {
                    "type": oanda_type,
                    "instrument": order.instrument,
                    "units": str(int(order.units)) if order.is_buy() else str(-int(abs(order.units))),
                    "timeInForce": order.time_in_force.value.upper(),
                }
            }
            
            # Add price for limit orders
            if order.requested_price and order.type.value in ["limit", "stop_limit", "market_if_touched"]:
                payload["order"]["price"] = str(order.requested_price)
            
            # Add stop price for stop orders
            if order.stop_price and order.type.value in ["stop", "stop_limit", "trailing_stop"]:
                payload["order"]["priceBound"] = str(order.stop_price)
            
            # Add expiry time if specified
            if order.expiry_time:
                payload["order"]["gtdTime"] = order.expiry_time.isoformat() + "Z"
            
            # Submit order
            endpoint = f"/v3/accounts/{self.config.account_id}/orders"
            response = await self.connection_pool.request("POST", endpoint, json=payload)
            
            if response.status_code == 201:
                data = response.json()
                order_create = data.get("orderCreateTransaction", {})
                oanda_order_id = order_create.get("id")
                
                logger.info("Pending order submitted successfully",
                           order_id=order.id,
                           oanda_order_id=oanda_order_id)
                
                return ExecutionResult(
                    success=True,
                    oanda_order_id=oanda_order_id,
                )
            else:
                error_data = response.json()
                error_message = error_data.get("errorMessage", "Unknown error")
                
                logger.error("Pending order submission failed",
                           order_id=order.id,
                           error=error_message)
                
                return ExecutionResult(
                    success=False,
                    error_code=str(response.status_code),
                    error_message=error_message,
                )
                
        except Exception as e:
            logger.error("Pending order submission exception",
                        order_id=order.id,
                        error=str(e))
            
            return ExecutionResult(
                success=False,
                error_code="SUBMISSION_EXCEPTION",
                error_message=str(e),
            )
    
    async def modify_order(self, order: Order) -> bool:
        """Modify existing order."""
        try:
            if not order.oanda_order_id:
                logger.warning("Cannot modify order without OANDA order ID", order_id=order.id)
                return False
            
            # Prepare modification payload
            payload = {
                "order": {
                    "type": order.type.value.upper(),
                    "instrument": order.instrument,
                    "units": str(int(order.units)) if order.is_buy() else str(-int(abs(order.units))),
                    "timeInForce": order.time_in_force.value.upper(),
                }
            }
            
            if order.requested_price:
                payload["order"]["price"] = str(order.requested_price)
            
            endpoint = f"/v3/accounts/{self.config.account_id}/orders/{order.oanda_order_id}"
            response = await self.connection_pool.request("PUT", endpoint, json=payload)
            
            return response.status_code == 201
            
        except Exception as e:
            logger.error("Order modification exception", order_id=order.id, error=str(e))
            return False
    
    async def cancel_order(self, order: Order) -> bool:
        """Cancel existing order."""
        try:
            if not order.oanda_order_id:
                logger.warning("Cannot cancel order without OANDA order ID", order_id=order.id)
                return False
            
            endpoint = f"/v3/accounts/{self.config.account_id}/orders/{order.oanda_order_id}/cancel"
            response = await self.connection_pool.request("PUT", endpoint)
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error("Order cancellation exception", order_id=order.id, error=str(e))
            return False
    
    async def close_position(self, account_id: str, instrument: str, units: Optional[Decimal] = None) -> ExecutionResult:
        """Close position."""
        try:
            payload = {}
            if units:
                if units > 0:
                    payload["longUnits"] = str(int(units))
                else:
                    payload["shortUnits"] = str(int(abs(units)))
            else:
                payload["longUnits"] = "ALL"
                payload["shortUnits"] = "ALL"
            
            endpoint = f"/v3/accounts/{account_id}/positions/{instrument}/close"
            response = await self.connection_pool.request("PUT", endpoint, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract realized P&L from close transactions
                realized_pl = Decimal("0")
                for key in ["longOrderFillTransaction", "shortOrderFillTransaction"]:
                    if key in data:
                        pl = data[key].get("pl", "0")
                        realized_pl += Decimal(pl)
                
                return ExecutionResult(
                    success=True,
                    realized_pl=realized_pl,
                )
            else:
                error_data = response.json()
                return ExecutionResult(
                    success=False,
                    error_message=error_data.get("errorMessage", "Unknown error"),
                )
                
        except Exception as e:
            logger.error("Position close exception", error=str(e))
            return ExecutionResult(
                success=False,
                error_message=str(e),
            )
    
    async def get_account_summary(self, account_id: str) -> Optional[AccountSummary]:
        """Get account summary information."""
        try:
            endpoint = f"/v3/accounts/{account_id}"
            response = await self.connection_pool.request("GET", endpoint)
            
            if response.status_code == 200:
                data = response.json()
                account = data.get("account", {})
                
                return AccountSummary(
                    account_id=account_id,
                    balance=Decimal(account.get("balance", "0")),
                    unrealized_pl=Decimal(account.get("unrealizedPL", "0")),
                    margin_used=Decimal(account.get("marginUsed", "0")),
                    margin_available=Decimal(account.get("marginAvailable", "0")),
                    open_positions=int(account.get("openPositionCount", 0)),
                    pending_orders=int(account.get("pendingOrderCount", 0)),
                )
            
            return None
            
        except Exception as e:
            logger.error("Account summary error", account_id=account_id, error=str(e))
            return None
    
    async def get_positions(self, account_id: str) -> List[Position]:
        """Get all positions for account."""
        try:
            endpoint = f"/v3/accounts/{account_id}/positions"
            response = await self.connection_pool.request("GET", endpoint)
            
            if response.status_code == 200:
                data = response.json()
                positions = []
                
                for pos_data in data.get("positions", []):
                    # OANDA returns separate long/short positions
                    long_units = Decimal(pos_data.get("long", {}).get("units", "0"))
                    short_units = Decimal(pos_data.get("short", {}).get("units", "0"))
                    
                    net_units = long_units + short_units
                    if net_units != 0:
                        avg_price_data = pos_data.get("long" if long_units != 0 else "short", {})
                        avg_price = Decimal(avg_price_data.get("averagePrice", "0"))
                        unrealized_pl = Decimal(avg_price_data.get("unrealizedPL", "0"))
                        
                        position = Position(
                            account_id=account_id,
                            instrument=pos_data.get("instrument"),
                            units=net_units,
                            side="long" if net_units > 0 else "short",
                            average_price=avg_price,
                            unrealized_pl=unrealized_pl,
                        )
                        positions.append(position)
                
                return positions
            
            return []
            
        except Exception as e:
            logger.error("Get positions error", account_id=account_id, error=str(e))
            return []
    
    async def get_current_prices(self, instruments: List[str]) -> Dict[str, Decimal]:
        """Get current prices for instruments."""
        try:
            instruments_param = ",".join(instruments)
            endpoint = f"/v3/accounts/{self.config.account_id}/pricing"
            params = {"instruments": instruments_param}
            
            response = await self.connection_pool.request("GET", endpoint, params=params)
            
            if response.status_code == 200:
                data = response.json()
                prices = {}
                
                for price_data in data.get("prices", []):
                    instrument = price_data.get("instrument")
                    # Use mid price (average of bid/ask)
                    bid = Decimal(price_data.get("bids", [{}])[0].get("price", "0"))
                    ask = Decimal(price_data.get("asks", [{}])[0].get("price", "0"))
                    mid_price = (bid + ask) / 2
                    
                    prices[instrument] = mid_price
                
                return prices
            
            return {}
            
        except Exception as e:
            logger.error("Get current prices error", error=str(e))
            return {}
    
    async def get_current_price(self, instrument: str) -> Optional[Decimal]:
        """Get current price for a single instrument."""
        prices = await self.get_current_prices([instrument])
        return prices.get(instrument)
    
    async def get_margin_info(self, account_id: str, instrument: str, units: Decimal) -> Optional[MarginInfo]:
        """Get margin requirements for order."""
        try:
            # This would typically be calculated based on instrument specifications
            # For MVP, we'll use a simplified approach
            current_price = await self.get_current_price(instrument)
            if not current_price:
                return None
            
            # Typical forex margin rate is 2-5%
            margin_rate = Decimal("0.02")  # 2%
            notional_value = abs(units) * current_price
            margin_used = notional_value * margin_rate
            
            return MarginInfo(
                margin_used=margin_used,
                margin_rate=margin_rate,
            )
            
        except Exception as e:
            logger.error("Get margin info error", error=str(e))
            return None
    
    async def get_instrument_info(self, instrument: str) -> Optional[InstrumentInfo]:
        """Get instrument information."""
        try:
            endpoint = f"/v3/accounts/{self.config.account_id}/instruments"
            params = {"instruments": instrument}
            response = await self.connection_pool.request("GET", endpoint, params=params)
            
            if response.status_code == 200:
                data = response.json()
                instruments = data.get("instruments", [])
                
                if instruments:
                    inst_data = instruments[0]
                    return InstrumentInfo(
                        name=inst_data.get("name"),
                        tradeable=inst_data.get("tradeable", False),
                        pip_location=inst_data.get("pipLocation", -4),
                        display_precision=inst_data.get("displayPrecision", 4),
                    )
            
            return None
            
        except Exception as e:
            logger.error("Get instrument info error", instrument=instrument, error=str(e))
            return None
    
    async def get_order_details(self, order_id) -> Optional[Order]:
        """Get order details from OANDA."""
        # Implementation would query OANDA for order details
        # For MVP, return None (order not found locally means it might not exist)
        return None
    
    async def get_order_history(
        self, 
        account_id: Optional[str] = None,
        instrument: Optional[str] = None,
        limit: int = 100
    ) -> List[Order]:
        """Get order history from OANDA."""
        # Implementation would fetch order history from OANDA
        # For MVP, return empty list
        return []
    
    def get_performance_metrics(self) -> Dict:
        """Get OANDA client performance metrics."""
        if not self.execution_times:
            return {
                "total_requests": 0,
                "success_rate": 0.0,
                "avg_execution_time_ms": 0.0,
                "p95_execution_time_ms": 0.0,
            }
        
        sorted_times = sorted(self.execution_times)
        total_requests = len(sorted_times)
        p95_index = int(0.95 * total_requests)
        
        return {
            "total_requests": total_requests,
            "success_rate": self.success_count / (self.success_count + self.error_count) if (self.success_count + self.error_count) > 0 else 0.0,
            "avg_execution_time_ms": sum(sorted_times) / total_requests,
            "p95_execution_time_ms": sorted_times[p95_index] if p95_index < total_requests else sorted_times[-1],
        }