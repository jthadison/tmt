# Technical Specification: OANDA v20 API Integration

## Executive Summary

This specification defines the integration of OANDA's v20 REST API as the first broker platform for the TMT system, enabling support for both US and international retail traders alongside existing prop firm capabilities.

### Key Objectives
- Extend TMT to support retail broker accounts (personal capital)
- Leverage OANDA's modern REST API for reliable execution
- Maintain compatibility with existing multi-agent architecture
- Enable US trader support with regulatory compliance

### Scope
- REST API integration for order management
- Streaming API for real-time market data
- Account management and compliance validation
- Performance monitoring and error handling

## Architecture Overview

### Integration Layer Architecture

```
┌─────────────────────────────────────────────────┐
│              TMT Execution Engine               │
├─────────────────────────────────────────────────┤
│            Broker Abstraction Layer             │
├──────────────┬─────────────┬───────────────────┤
│  OANDA v20   │ Trade Locker│   DXTrade API     │
│  Adapter     │   Adapter   │    Adapter        │
└──────────────┴─────────────┴───────────────────┘
```

### Component Structure

```python
src/
├── execution-engine/
│   ├── brokers/
│   │   ├── __init__.py
│   │   ├── base.py              # Abstract broker interface
│   │   ├── oanda/
│   │   │   ├── __init__.py
│   │   │   ├── client.py        # Main OANDA client
│   │   │   ├── auth.py          # Authentication handler
│   │   │   ├── orders.py        # Order management
│   │   │   ├── streaming.py     # Market data streaming
│   │   │   ├── accounts.py      # Account management
│   │   │   ├── compliance.py    # US regulatory compliance
│   │   │   └── models.py        # OANDA-specific models
│   │   └── factory.py           # Broker factory pattern
```

## OANDA v20 API Implementation

### 1. Authentication & Connection Management

```python
from typing import Optional, Dict, Any
import aiohttp
from dataclasses import dataclass
from enum import Enum

class OandaEnvironment(Enum):
    PRACTICE = "https://api-fxpractice.oanda.com/v3"
    LIVE = "https://api-fxtrade.oanda.com/v3"
    STREAM_PRACTICE = "https://stream-fxpractice.oanda.com/v3"
    STREAM_LIVE = "https://stream-fxtrade.oanda.com/v3"

@dataclass
class OandaConfig:
    api_key: str
    account_id: str
    environment: OandaEnvironment = OandaEnvironment.PRACTICE
    timeout: int = 30
    max_retries: int = 3
    rate_limit_per_second: int = 100  # OANDA allows 120/sec

class OandaAuthHandler:
    """Manages authentication and connection pooling"""
    
    def __init__(self, config: OandaConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
            "Accept-Datetime-Format": "RFC3339"
        }
    
    async def initialize(self):
        """Create persistent connection pool"""
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=30,
            ttl_dns_cache=300
        )
        self.session = aiohttp.ClientSession(
            connector=connector,
            headers=self.headers,
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
    
    async def close(self):
        """Cleanup connections"""
        if self.session:
            await self.session.close()
```

### 2. Account Management

```python
class OandaAccountManager:
    """Handles account information and compliance checks"""
    
    def __init__(self, auth: OandaAuthHandler):
        self.auth = auth
        self.base_url = auth.config.environment.value
        self.account_id = auth.config.account_id
    
    async def get_account_summary(self) -> Dict[str, Any]:
        """Fetch account details including balance, margin, P&L"""
        url = f"{self.base_url}/accounts/{self.account_id}/summary"
        async with self.auth.session.get(url) as response:
            return await response.json()
    
    async def get_account_instruments(self) -> List[Dict]:
        """Get tradeable instruments with spreads and margin requirements"""
        url = f"{self.base_url}/accounts/{self.account_id}/instruments"
        async with self.auth.session.get(url) as response:
            data = await response.json()
            return data.get("instruments", [])
    
    async def validate_us_compliance(self, order: Dict) -> Tuple[bool, str]:
        """Validate order against US trading regulations"""
        validations = []
        
        # FIFO compliance check
        if await self._has_opposing_positions(order["instrument"]):
            validations.append("FIFO violation: Close oldest position first")
        
        # Leverage check (max 50:1 for majors, 20:1 for minors)
        leverage = self._calculate_leverage(order)
        max_leverage = 50 if self._is_major_pair(order["instrument"]) else 20
        if leverage > max_leverage:
            validations.append(f"Leverage {leverage}:1 exceeds US limit {max_leverage}:1")
        
        # No hedging check
        if await self._would_create_hedge(order):
            validations.append("Hedging not allowed for US accounts")
        
        return len(validations) == 0, "; ".join(validations)
```

### 3. Order Execution System

```python
from enum import Enum
from decimal import Decimal
from typing import Optional, List

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    MARKET_IF_TOUCHED = "MARKET_IF_TOUCHED"

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

@dataclass
class OandaOrder:
    """OANDA order representation"""
    instrument: str
    units: int  # Positive for buy, negative for sell
    type: OrderType = OrderType.MARKET
    price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    time_in_force: str = "FOK"  # Fill or Kill, GTC, IOC, GTD
    client_extensions: Optional[Dict] = None

class OandaOrderManager:
    """Handles order lifecycle management"""
    
    def __init__(self, auth: OandaAuthHandler, account_manager: OandaAccountManager):
        self.auth = auth
        self.account_manager = account_manager
        self.base_url = auth.config.environment.value
        self.account_id = auth.config.account_id
    
    async def place_order(self, order: OandaOrder) -> Dict[str, Any]:
        """Submit order to OANDA with validation"""
        
        # Pre-trade compliance check
        is_valid, message = await self.account_manager.validate_us_compliance(order.__dict__)
        if not is_valid:
            raise ValueError(f"Compliance validation failed: {message}")
        
        # Build OANDA order request
        order_request = {
            "order": {
                "instrument": order.instrument,
                "units": str(order.units),
                "type": order.type.value,
                "timeInForce": order.time_in_force
            }
        }
        
        # Add optional parameters
        if order.price:
            order_request["order"]["price"] = str(order.price)
        if order.stop_loss:
            order_request["order"]["stopLossOnFill"] = {
                "price": str(order.stop_loss)
            }
        if order.take_profit:
            order_request["order"]["takeProfitOnFill"] = {
                "price": str(order.take_profit)
            }
        if order.client_extensions:
            order_request["order"]["clientExtensions"] = order.client_extensions
        
        # Submit order
        url = f"{self.base_url}/accounts/{self.account_id}/orders"
        async with self.auth.session.post(url, json=order_request) as response:
            result = await response.json()
            
            if response.status == 201:
                return {
                    "success": True,
                    "order_id": result.get("orderFillTransaction", {}).get("orderID"),
                    "fill_price": result.get("orderFillTransaction", {}).get("price"),
                    "transaction_id": result.get("lastTransactionID"),
                    "raw_response": result
                }
            else:
                return {
                    "success": False,
                    "error": result.get("errorMessage", "Unknown error"),
                    "error_code": result.get("errorCode"),
                    "raw_response": result
                }
    
    async def modify_order(self, order_id: str, updates: Dict) -> Dict:
        """Modify existing order (stop loss, take profit, etc)"""
        url = f"{self.base_url}/accounts/{self.account_id}/orders/{order_id}"
        
        order_updates = {}
        if "stop_loss" in updates:
            order_updates["stopLoss"] = {"price": str(updates["stop_loss"])}
        if "take_profit" in updates:
            order_updates["takeProfit"] = {"price": str(updates["take_profit"])}
        
        async with self.auth.session.put(url, json={"order": order_updates}) as response:
            return await response.json()
    
    async def cancel_order(self, order_id: str) -> Dict:
        """Cancel pending order"""
        url = f"{self.base_url}/accounts/{self.account_id}/orders/{order_id}/cancel"
        async with self.auth.session.put(url) as response:
            return await response.json()
    
    async def get_orders(self, state: str = "PENDING") -> List[Dict]:
        """Get orders by state (PENDING, FILLED, CANCELLED)"""
        url = f"{self.base_url}/accounts/{self.account_id}/orders"
        params = {"state": state}
        async with self.auth.session.get(url, params=params) as response:
            data = await response.json()
            return data.get("orders", [])
    
    async def get_positions(self) -> List[Dict]:
        """Get all open positions"""
        url = f"{self.base_url}/accounts/{self.account_id}/positions"
        async with self.auth.session.get(url) as response:
            data = await response.json()
            return data.get("positions", [])
    
    async def close_position(self, instrument: str, units: Optional[str] = None) -> Dict:
        """Close position (all or partial)"""
        url = f"{self.base_url}/accounts/{self.account_id}/positions/{instrument}/close"
        
        data = {}
        if units:
            data["units"] = units  # Partial close
        else:
            data["units"] = "ALL"  # Close entire position
        
        async with self.auth.session.put(url, json=data) as response:
            return await response.json()
```

### 4. Market Data Streaming

```python
import asyncio
import json
from typing import Callable, Set, Optional
from datetime import datetime

class OandaStreamManager:
    """Manages real-time price and transaction streams"""
    
    def __init__(self, auth: OandaAuthHandler):
        self.auth = auth
        self.account_id = auth.config.account_id
        self.stream_url = (
            OandaEnvironment.STREAM_PRACTICE.value 
            if "practice" in auth.config.environment.value 
            else OandaEnvironment.STREAM_LIVE.value
        )
        self.price_stream_task: Optional[asyncio.Task] = None
        self.transaction_stream_task: Optional[asyncio.Task] = None
        self.subscribed_instruments: Set[str] = set()
        self.price_callbacks: List[Callable] = []
        self.transaction_callbacks: List[Callable] = []
    
    async def start_price_stream(self, instruments: List[str], callback: Callable):
        """Stream real-time prices for specified instruments"""
        self.subscribed_instruments.update(instruments)
        self.price_callbacks.append(callback)
        
        if self.price_stream_task and not self.price_stream_task.done():
            # Stream already running, update instruments
            await self._restart_price_stream()
        else:
            self.price_stream_task = asyncio.create_task(self._price_stream_worker())
    
    async def _price_stream_worker(self):
        """Price stream worker with auto-reconnect"""
        url = f"{self.stream_url}/accounts/{self.account_id}/pricing/stream"
        
        while True:
            try:
                params = {
                    "instruments": ",".join(self.subscribed_instruments),
                    "snapshot": "true"
                }
                
                async with self.auth.session.get(url, params=params) as response:
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line.decode('utf-8'))
                                
                                if data.get("type") == "PRICE":
                                    price_update = {
                                        "instrument": data["instrument"],
                                        "time": data["time"],
                                        "bid": float(data["bids"][0]["price"]) if data.get("bids") else None,
                                        "ask": float(data["asks"][0]["price"]) if data.get("asks") else None,
                                        "spread": self._calculate_spread(data),
                                        "tradeable": data.get("tradeable", False)
                                    }
                                    
                                    # Notify all callbacks
                                    for callback in self.price_callbacks:
                                        await callback(price_update)
                                        
                            except json.JSONDecodeError:
                                continue
                                
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error and reconnect after delay
                await asyncio.sleep(5)
    
    async def start_transaction_stream(self, callback: Callable):
        """Stream account transactions (trades, orders, etc)"""
        self.transaction_callbacks.append(callback)
        
        if not self.transaction_stream_task or self.transaction_stream_task.done():
            self.transaction_stream_task = asyncio.create_task(self._transaction_stream_worker())
    
    async def _transaction_stream_worker(self):
        """Transaction stream worker"""
        url = f"{self.stream_url}/accounts/{self.account_id}/transactions/stream"
        
        while True:
            try:
                async with self.auth.session.get(url) as response:
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line.decode('utf-8'))
                                
                                transaction = {
                                    "id": data.get("id"),
                                    "type": data.get("type"),
                                    "time": data.get("time"),
                                    "account_id": data.get("accountID"),
                                    "instrument": data.get("instrument"),
                                    "units": data.get("units"),
                                    "price": data.get("price"),
                                    "pl": data.get("pl"),
                                    "reason": data.get("reason")
                                }
                                
                                # Notify all callbacks
                                for callback in self.transaction_callbacks:
                                    await callback(transaction)
                                    
                            except json.JSONDecodeError:
                                continue
                                
            except asyncio.CancelledError:
                break
            except Exception as e:
                await asyncio.sleep(5)
    
    def _calculate_spread(self, data: Dict) -> float:
        """Calculate spread in pips"""
        if data.get("bids") and data.get("asks"):
            bid = float(data["bids"][0]["price"])
            ask = float(data["asks"][0]["price"])
            
            # Determine pip multiplier based on instrument
            if "JPY" in data["instrument"]:
                pip_multiplier = 100
            else:
                pip_multiplier = 10000
            
            return round((ask - bid) * pip_multiplier, 2)
        return 0.0
    
    async def stop_streams(self):
        """Stop all active streams"""
        if self.price_stream_task:
            self.price_stream_task.cancel()
        if self.transaction_stream_task:
            self.transaction_stream_task.cancel()
```

### 5. Error Handling and Resilience

```python
import backoff
from typing import Type
from enum import Enum

class OandaErrorCode(Enum):
    """OANDA API error codes"""
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    MARKET_CLOSED = "MARKET_CLOSED"
    INVALID_INSTRUMENT = "INVALID_INSTRUMENT"
    INVALID_UNITS = "INVALID_UNITS"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    TIMEOUT = "TIMEOUT"
    SERVER_ERROR = "SERVER_ERROR"

class OandaException(Exception):
    """Base exception for OANDA errors"""
    def __init__(self, message: str, error_code: Optional[str] = None, response: Optional[Dict] = None):
        self.message = message
        self.error_code = error_code
        self.response = response
        super().__init__(self.message)

class OandaRetryHandler:
    """Handles retry logic with exponential backoff"""
    
    @staticmethod
    def is_retryable_error(error_code: str) -> bool:
        """Determine if error should trigger retry"""
        retryable_codes = {
            OandaErrorCode.RATE_LIMIT_EXCEEDED.value,
            OandaErrorCode.TIMEOUT.value,
            OandaErrorCode.SERVER_ERROR.value,
            "503",  # Service unavailable
            "504",  # Gateway timeout
        }
        return error_code in retryable_codes
    
    @staticmethod
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, OandaException),
        max_tries=3,
        max_time=30,
        giveup=lambda e: not OandaRetryHandler.is_retryable_error(str(e))
    )
    async def execute_with_retry(func: Callable, *args, **kwargs):
        """Execute function with automatic retry logic"""
        try:
            return await func(*args, **kwargs)
        except aiohttp.ClientResponseError as e:
            if e.status == 429:  # Rate limit
                await asyncio.sleep(1)  # Rate limit cooldown
                raise OandaException("Rate limit exceeded", OandaErrorCode.RATE_LIMIT_EXCEEDED.value)
            elif e.status >= 500:
                raise OandaException(f"Server error: {e.status}", OandaErrorCode.SERVER_ERROR.value)
            else:
                raise
        except asyncio.TimeoutError:
            raise OandaException("Request timeout", OandaErrorCode.TIMEOUT.value)

class OandaCircuitBreaker:
    """Circuit breaker pattern for API health"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "OPEN":
            if datetime.now().timestamp() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise OandaException("Circuit breaker is OPEN - API unavailable")
        
        try:
            result = await func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now().timestamp()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                raise OandaException(f"Circuit breaker opened after {self.failure_count} failures")
            raise
```

## Integration with TMT System

### 1. Broker Adapter Interface

```python
from abc import ABC, abstractmethod

class BrokerAdapter(ABC):
    """Abstract base class for all broker integrations"""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to broker"""
        pass
    
    @abstractmethod
    async def place_order(self, signal: TradingSignal) -> OrderResult:
        """Execute trading signal"""
        pass
    
    @abstractmethod
    async def get_account_info(self) -> AccountInfo:
        """Get account balance, margin, etc"""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get open positions"""
        pass
    
    @abstractmethod
    async def close_position(self, position_id: str) -> bool:
        """Close specific position"""
        pass

class OandaBrokerAdapter(BrokerAdapter):
    """OANDA-specific implementation"""
    
    def __init__(self, config: OandaConfig):
        self.config = config
        self.auth = OandaAuthHandler(config)
        self.account_manager = None
        self.order_manager = None
        self.stream_manager = None
        self.circuit_breaker = OandaCircuitBreaker()
    
    async def connect(self) -> bool:
        """Initialize OANDA connection"""
        await self.auth.initialize()
        self.account_manager = OandaAccountManager(self.auth)
        self.order_manager = OandaOrderManager(self.auth, self.account_manager)
        self.stream_manager = OandaStreamManager(self.auth)
        
        # Verify connection
        account_info = await self.account_manager.get_account_summary()
        return account_info is not None
    
    async def place_order(self, signal: TradingSignal) -> OrderResult:
        """Convert TMT signal to OANDA order"""
        oanda_order = OandaOrder(
            instrument=self._convert_symbol(signal.symbol),
            units=self._calculate_units(signal),
            type=self._convert_order_type(signal.order_type),
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            client_extensions={
                "id": signal.signal_id,
                "tag": f"TMT_{signal.agent_name}"
            }
        )
        
        # Execute with circuit breaker protection
        result = await self.circuit_breaker.call(
            self.order_manager.place_order,
            oanda_order
        )
        
        return self._convert_result(result)
```

### 2. Compliance Integration

```python
class BrokerComplianceValidator:
    """Validates trades against broker-specific rules"""
    
    def __init__(self, account_type: str, broker_name: str):
        self.account_type = account_type
        self.broker_name = broker_name
        self.rules = self._load_rules()
    
    def _load_rules(self) -> Dict:
        """Load broker-specific compliance rules"""
        if self.broker_name == "OANDA" and self.account_type == "US":
            return {
                "max_leverage": 50,
                "fifo_required": True,
                "hedging_allowed": False,
                "min_trade_size": 1,
                "max_positions": 200
            }
        # Other brokers...
        return {}
    
    async def validate_signal(self, signal: TradingSignal) -> ValidationResult:
        """Validate signal against broker rules"""
        violations = []
        
        if self.rules.get("fifo_required") and signal.violates_fifo:
            violations.append("FIFO violation")
        
        if not self.rules.get("hedging_allowed") and signal.creates_hedge:
            violations.append("Hedging not allowed")
        
        return ValidationResult(
            is_valid=len(violations) == 0,
            violations=violations
        )
```

## Testing Strategy

### 1. Unit Tests

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

class TestOandaOrderManager:
    """Unit tests for order management"""
    
    @pytest.fixture
    async def order_manager(self):
        config = OandaConfig(
            api_key="test_key",
            account_id="test_account",
            environment=OandaEnvironment.PRACTICE
        )
        auth = AsyncMock(spec=OandaAuthHandler)
        account_manager = AsyncMock(spec=OandaAccountManager)
        return OandaOrderManager(auth, account_manager)
    
    @pytest.mark.asyncio
    async def test_place_market_order_success(self, order_manager):
        """Test successful market order placement"""
        order = OandaOrder(
            instrument="EUR_USD",
            units=1000,
            type=OrderType.MARKET
        )
        
        # Mock successful response
        order_manager.auth.session.post.return_value.__aenter__.return_value.json = AsyncMock(
            return_value={
                "orderFillTransaction": {
                    "orderID": "12345",
                    "price": "1.1850"
                },
                "lastTransactionID": "67890"
            }
        )
        order_manager.auth.session.post.return_value.__aenter__.return_value.status = 201
        
        result = await order_manager.place_order(order)
        
        assert result["success"] is True
        assert result["order_id"] == "12345"
        assert result["fill_price"] == "1.1850"
    
    @pytest.mark.asyncio
    async def test_place_order_with_fifo_violation(self, order_manager):
        """Test order rejection due to FIFO violation"""
        order = OandaOrder(
            instrument="EUR_USD",
            units=-1000,  # Sell order
            type=OrderType.MARKET
        )
        
        # Mock FIFO violation
        order_manager.account_manager.validate_us_compliance.return_value = (
            False, 
            "FIFO violation: Close oldest position first"
        )
        
        with pytest.raises(ValueError, match="FIFO violation"):
            await order_manager.place_order(order)
    
    @pytest.mark.asyncio  
    async def test_stream_reconnect_on_failure(self, stream_manager):
        """Test automatic reconnection on stream failure"""
        # Simulate connection failure then success
        responses = [
            asyncio.TimeoutError(),
            AsyncMock()  # Successful reconnection
        ]
        stream_manager.auth.session.get.side_effect = responses
        
        await stream_manager.start_price_stream(["EUR_USD"], AsyncMock())
        
        # Verify reconnection attempted
        assert stream_manager.auth.session.get.call_count == 2
```

### 2. Integration Tests

```python
class TestOandaIntegration:
    """Integration tests with OANDA practice account"""
    
    @pytest.fixture
    async def oanda_adapter(self):
        """Create real OANDA adapter with practice account"""
        config = OandaConfig(
            api_key=os.getenv("OANDA_PRACTICE_API_KEY"),
            account_id=os.getenv("OANDA_PRACTICE_ACCOUNT_ID"),
            environment=OandaEnvironment.PRACTICE
        )
        adapter = OandaBrokerAdapter(config)
        await adapter.connect()
        yield adapter
        await adapter.disconnect()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_trade_lifecycle(self, oanda_adapter):
        """Test complete order flow: place, modify, close"""
        
        # 1. Get initial account balance
        initial_account = await oanda_adapter.get_account_info()
        initial_balance = initial_account.balance
        
        # 2. Place market order
        signal = TradingSignal(
            symbol="EUR/USD",
            side="BUY",
            size=100,  # Minimum size for practice
            stop_loss=1.1700,
            take_profit=1.1900
        )
        
        order_result = await oanda_adapter.place_order(signal)
        assert order_result.success
        position_id = order_result.position_id
        
        # 3. Verify position created
        positions = await oanda_adapter.get_positions()
        eur_usd_position = next(
            (p for p in positions if p.instrument == "EUR_USD"), 
            None
        )
        assert eur_usd_position is not None
        assert eur_usd_position.units == 100
        
        # 4. Modify stop loss
        await oanda_adapter.modify_position(
            position_id,
            stop_loss=1.1750
        )
        
        # 5. Close position
        close_result = await oanda_adapter.close_position(position_id)
        assert close_result.success
        
        # 6. Verify position closed
        positions_after = await oanda_adapter.get_positions()
        eur_usd_after = next(
            (p for p in positions_after if p.instrument == "EUR_USD"),
            None
        )
        assert eur_usd_after is None
```

### 3. Performance Tests

```python
class TestOandaPerformance:
    """Performance and load tests"""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_order_execution_latency(self, oanda_adapter):
        """Measure order execution latency"""
        latencies = []
        
        for _ in range(10):
            start = datetime.now()
            
            signal = TradingSignal(
                symbol="EUR/USD",
                side="BUY",
                size=100
            )
            
            result = await oanda_adapter.place_order(signal)
            
            if result.success:
                latency = (datetime.now() - start).total_seconds() * 1000
                latencies.append(latency)
                
                # Clean up
                await oanda_adapter.close_position(result.position_id)
        
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        
        assert avg_latency < 100  # Average under 100ms
        assert p95_latency < 200  # 95th percentile under 200ms
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_stream_throughput(self, oanda_adapter):
        """Test market data streaming throughput"""
        updates_received = []
        
        async def price_callback(update):
            updates_received.append(update)
        
        # Subscribe to multiple instruments
        instruments = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD"]
        await oanda_adapter.stream_manager.start_price_stream(
            instruments, 
            price_callback
        )
        
        # Collect updates for 10 seconds
        await asyncio.sleep(10)
        
        updates_per_second = len(updates_received) / 10
        assert updates_per_second > 1  # At least 1 update per second per instrument
```

## Implementation Timeline

### Week 1: Foundation & Core Integration
**Day 1-2: Setup & Authentication**
- [ ] Set up project structure and dependencies
- [ ] Implement OandaConfig and OandaAuthHandler
- [ ] Create connection pooling and session management
- [ ] Write unit tests for authentication

**Day 3-4: Account Management**
- [ ] Implement OandaAccountManager
- [ ] Add US compliance validation logic
- [ ] Create account info and instruments endpoints
- [ ] Write tests for account operations

**Day 5: Integration Foundation**
- [ ] Create BrokerAdapter abstract base class
- [ ] Implement OandaBrokerAdapter skeleton
- [ ] Set up configuration management
- [ ] Integration with existing TMT architecture

### Week 2: Order Execution & Streaming
**Day 6-7: Order Management**
- [ ] Implement OandaOrderManager
- [ ] Add all order types (market, limit, stop)
- [ ] Create position management methods
- [ ] Write comprehensive order tests

**Day 8-9: Market Data Streaming**
- [ ] Implement OandaStreamManager
- [ ] Add price streaming with auto-reconnect
- [ ] Add transaction streaming
- [ ] Test streaming reliability

**Day 10: Error Handling**
- [ ] Implement retry logic with backoff
- [ ] Add circuit breaker pattern
- [ ] Create comprehensive error mapping
- [ ] Test failure scenarios

### Week 3: Testing & Production Readiness
**Day 11-12: Integration Testing**
- [ ] Set up OANDA practice account for testing
- [ ] Write end-to-end integration tests
- [ ] Performance testing and optimization
- [ ] Load testing with multiple concurrent orders

**Day 13-14: Production Hardening**
- [ ] Add comprehensive logging
- [ ] Implement monitoring and metrics
- [ ] Security review (API key management)
- [ ] Documentation and code review

**Day 15: Deployment**
- [ ] Deploy to staging environment
- [ ] Run full test suite
- [ ] Performance validation
- [ ] Go-live checklist completion

## Success Metrics

1. **Performance Requirements**
   - Order execution latency: < 100ms average, < 200ms P95
   - Stream reconnection time: < 5 seconds
   - API availability: > 99.9% (via circuit breaker)

2. **Functional Requirements**
   - 100% US compliance validation coverage
   - All OANDA order types supported
   - Automatic FIFO enforcement
   - Real-time position tracking

3. **Quality Requirements**
   - Unit test coverage: > 90%
   - Integration test coverage: > 80%
   - Zero critical security vulnerabilities
   - Complete API documentation

## Configuration Requirements

### Environment Variables
```bash
# OANDA Configuration
OANDA_API_KEY=your_api_key_here
OANDA_ACCOUNT_ID=your_account_id
OANDA_ENVIRONMENT=practice  # or live
OANDA_TIMEOUT=30
OANDA_MAX_RETRIES=3

# US Compliance Settings
ENABLE_US_COMPLIANCE=true
MAX_LEVERAGE_MAJOR_PAIRS=50
MAX_LEVERAGE_MINOR_PAIRS=20
ENFORCE_FIFO=true
ALLOW_HEDGING=false
```

### Sample Configuration File
```yaml
# config/brokers/oanda.yaml
oanda:
  api:
    practice_url: https://api-fxpractice.oanda.com/v3
    live_url: https://api-fxtrade.oanda.com/v3
    stream_practice_url: https://stream-fxpractice.oanda.com/v3
    stream_live_url: https://stream-fxtrade.oanda.com/v3
  
  limits:
    rate_limit_per_second: 100
    max_concurrent_orders: 10
    max_positions: 200
    min_trade_size: 1
    max_trade_size: 10000000
  
  compliance:
    us_accounts:
      max_leverage_majors: 50
      max_leverage_minors: 20
      fifo_required: true
      hedging_allowed: false
    
    non_us_accounts:
      max_leverage: 500
      fifo_required: false
      hedging_allowed: true
  
  retry_policy:
    max_attempts: 3
    backoff_factor: 2
    max_backoff: 30
    retryable_status_codes: [429, 500, 502, 503, 504]
  
  circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 60
    half_open_requests: 3
```

## Dependencies

```python
# requirements.txt
aiohttp>=3.8.0
backoff>=2.2.0
python-dateutil>=2.8.0
pydantic>=2.0.0
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-mock>=3.10.0
```

## Risk Mitigation

1. **API Rate Limiting**: Implement token bucket algorithm with 100 req/sec limit
2. **Connection Failures**: Auto-reconnect with exponential backoff
3. **Order Rejections**: Pre-validation before submission
4. **Data Loss**: Transaction log persistence for recovery
5. **Compliance Violations**: Real-time validation with circuit breaker
6. **Security**: API keys in HashiCorp Vault, never in code

## Next Steps After Implementation

1. **Phase 2 Brokers**: FOREX.com (DXTrade), TD Ameritrade
2. **Advanced Features**: 
   - OCO (One-Cancels-Other) orders
   - Trailing stop losses
   - Partial position closes
3. **Multi-Account Support**: Managing multiple OANDA accounts
4. **Analytics Integration**: Trade performance metrics dashboard

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"id": "1", "content": "Create technical specification document structure", "status": "completed"}, {"id": "2", "content": "Define OANDA v20 API integration architecture", "status": "completed"}, {"id": "3", "content": "Specify authentication and connection management", "status": "in_progress"}, {"id": "4", "content": "Detail order execution and management endpoints", "status": "pending"}, {"id": "5", "content": "Define market data streaming implementation", "status": "pending"}, {"id": "6", "content": "Specify error handling and retry logic", "status": "pending"}, {"id": "7", "content": "Document testing and validation approach", "status": "pending"}, {"id": "8", "content": "Create implementation timeline and milestones", "status": "pending"}]