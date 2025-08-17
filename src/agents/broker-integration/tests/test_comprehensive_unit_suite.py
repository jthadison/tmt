"""
Comprehensive Unit Test Suite for Broker Integration
Story 8.12 - Task 1: Build comprehensive unit test suite (>90% coverage)
"""
import pytest
import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

# Test imports
import sys
from pathlib import Path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from broker_adapter import (
    BrokerAdapter, UnifiedOrder, UnifiedPosition, UnifiedAccountSummary,
    OrderType, OrderSide, OrderState, PositionSide, TimeInForce,
    BrokerCapability, PriceTick, OrderResult, BrokerInfo
)
from unified_errors import (
    StandardBrokerError, StandardErrorCode, ErrorSeverity, ErrorCategory,
    ErrorContext, ErrorCodeMapper, error_mapper
)
from oanda_auth_handler import OandaAuthHandler, AuthenticationError, AccountContext, Environment
from connection_pool import PooledConnection, ConnectionState, ConnectionMetrics
from credential_manager import OandaCredentialManager, CredentialValidationError


class MockOandaBrokerAdapter(BrokerAdapter):
    """Mock OANDA broker adapter for testing"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._broker_name = "oanda"
        self._capabilities = {
            BrokerCapability.MARKET_ORDERS,
            BrokerCapability.LIMIT_ORDERS,
            BrokerCapability.STOP_ORDERS,
            BrokerCapability.STOP_LOSS_ORDERS,
            BrokerCapability.TAKE_PROFIT_ORDERS,
            BrokerCapability.FRACTIONAL_UNITS,
            BrokerCapability.NETTING,
            BrokerCapability.REAL_TIME_STREAMING
        }
        self._supported_instruments = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD"]
        self._supported_order_types = [
            OrderType.MARKET, OrderType.LIMIT, OrderType.STOP,
            OrderType.STOP_LOSS, OrderType.TAKE_PROFIT
        ]
        
    @property
    def broker_name(self) -> str:
        return self._broker_name
        
    @property
    def broker_display_name(self) -> str:
        return "OANDA"
        
    @property
    def api_version(self) -> str:
        return "v3"
        
    @property
    def capabilities(self) -> set:
        return self._capabilities
        
    @property
    def supported_instruments(self) -> List[str]:
        return self._supported_instruments
        
    @property
    def supported_order_types(self) -> List[OrderType]:
        return self._supported_order_types
        
    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        return True
        
    async def disconnect(self) -> bool:
        return True
        
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy"}
        
    async def get_broker_info(self) -> BrokerInfo:
        return BrokerInfo(
            name=self.broker_name,
            display_name=self.broker_display_name,
            version=self.api_version,
            capabilities=self.capabilities,
            supported_instruments=self.supported_instruments,
            supported_order_types=self.supported_order_types,
            supported_time_in_force=[TimeInForce.GTC, TimeInForce.IOC, TimeInForce.FOK],
            minimum_trade_size={"EUR_USD": Decimal("1")},
            maximum_trade_size={"EUR_USD": Decimal("10000000")},
            commission_structure={"type": "spread"},
            margin_requirements={"EUR_USD": Decimal("0.03")},
            trading_hours={"EUR_USD": {"open": "22:00", "close": "22:00"}},
            api_rate_limits={"orders": 100}
        )
        
    async def get_account_summary(self, account_id: Optional[str] = None) -> UnifiedAccountSummary:
        return UnifiedAccountSummary(
            account_id=account_id or self.account_id or "test_account",
            account_name="Test Account",
            currency="USD",
            balance=Decimal("10000.00"),
            available_margin=Decimal("9500.00"),
            used_margin=Decimal("500.00"),
            unrealized_pl=Decimal("50.00"),
            realized_pl=Decimal("25.00"),
            nav=Decimal("10075.00"),
            equity=Decimal("10050.00")
        )
        
    async def get_accounts(self) -> List[UnifiedAccountSummary]:
        return [await self.get_account_summary()]
        
    async def place_order(self, order: UnifiedOrder) -> OrderResult:
        # Simulate validation
        validation_errors = self.validate_order(order)
        if validation_errors:
            return OrderResult(
                success=False,
                error_code="VALIDATION_ERROR",
                error_message="; ".join(validation_errors)
            )
            
        return OrderResult(
            success=True,
            order_id="test_order_123",
            client_order_id=order.client_order_id,
            order_state=OrderState.FILLED,
            fill_price=Decimal("1.1000"),
            filled_units=order.units,
            commission=Decimal("2.50"),
            transaction_id="test_txn_123"
        )
        
    async def modify_order(self, order_id: str, modifications: Dict[str, Any]) -> OrderResult:
        return OrderResult(success=True, order_id=order_id)
        
    async def cancel_order(self, order_id: str, reason: Optional[str] = None) -> OrderResult:
        return OrderResult(success=True, order_id=order_id)
        
    async def get_order(self, order_id: str) -> Optional[UnifiedOrder]:
        return UnifiedOrder(
            order_id=order_id,
            client_order_id="client_123",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("1000"),
            state=OrderState.FILLED
        )
        
    async def get_orders(self, **kwargs) -> List[UnifiedOrder]:
        return [await self.get_order("test_order")]
        
    async def get_position(self, instrument: str, account_id: Optional[str] = None) -> Optional[UnifiedPosition]:
        return UnifiedPosition(
            position_id="pos_123",
            instrument=instrument,
            side=PositionSide.LONG,
            units=Decimal("1000"),
            average_price=Decimal("1.1000"),
            current_price=Decimal("1.1020"),
            unrealized_pl=Decimal("20.00")
        )
        
    async def get_positions(self, account_id: Optional[str] = None) -> List[UnifiedPosition]:
        return [await self.get_position("EUR_USD")]
        
    async def close_position(self, instrument: str, units: Optional[Decimal] = None, account_id: Optional[str] = None) -> OrderResult:
        return OrderResult(
            success=True,
            order_id="close_order_123",
            fill_price=Decimal("1.1020"),
            filled_units=units or Decimal("1000")
        )
        
    async def get_current_price(self, instrument: str) -> Optional[PriceTick]:
        # Add validation like the base class
        if not instrument:
            raise ValueError("Instrument is required")
        return PriceTick(
            instrument=instrument,
            bid=Decimal("1.1000"),
            ask=Decimal("1.1002"),
            timestamp=datetime.now(timezone.utc)
        )
        
    async def get_current_prices(self, instruments: List[str]) -> Dict[str, PriceTick]:
        # Add validation like the base class
        if not instruments:
            raise ValueError("Instruments list is required and cannot be empty")
        return {
            instrument: await self.get_current_price(instrument)
            for instrument in instruments
        }
        
    async def stream_prices(self, instruments: List[str]):
        for instrument in instruments:
            yield await self.get_current_price(instrument)
            
    async def get_historical_data(self, **kwargs) -> List[Dict[str, Any]]:
        return [{"time": "2023-01-01T12:00:00Z", "o": 1.1000, "h": 1.1020, "l": 1.0980, "c": 1.1010}]
        
    async def get_transactions(self, **kwargs) -> List[Dict[str, Any]]:
        return [{"id": "txn_123", "type": "ORDER_FILL", "amount": "1000"}]
        
    def map_error(self, broker_error: Exception) -> StandardBrokerError:
        return StandardBrokerError(
            error_code=StandardErrorCode.UNKNOWN_ERROR,
            message=str(broker_error)
        )


class TestBrokerAdapterBase:
    """Test base broker adapter functionality"""
    
    @pytest.fixture
    def broker_config(self):
        return {
            'api_key': 'test_key',
            'account_id': 'test_account',
            'environment': 'practice'
        }
        
    @pytest.fixture
    def mock_adapter(self, broker_config):
        return MockOandaBrokerAdapter(broker_config)
        
    def test_adapter_initialization(self, broker_config):
        adapter = MockOandaBrokerAdapter(broker_config)
        assert adapter.config == broker_config
        assert adapter.account_id == 'test_account'
        assert not adapter.is_authenticated
        assert adapter.connection_status == 'disconnected'
        
    def test_broker_properties(self, mock_adapter):
        assert mock_adapter.broker_name == "oanda"
        assert mock_adapter.broker_display_name == "OANDA"
        assert mock_adapter.api_version == "v3"
        assert isinstance(mock_adapter.capabilities, set)
        assert BrokerCapability.MARKET_ORDERS in mock_adapter.capabilities
        
    def test_generate_client_order_id(self, mock_adapter):
        order_id = mock_adapter.generate_client_order_id()
        assert order_id.startswith("oanda_")
        assert len(order_id) == 14  # "oanda_" + 8 hex chars
        
    def test_capability_check(self, mock_adapter):
        assert mock_adapter.is_capability_supported(BrokerCapability.MARKET_ORDERS)
        assert not mock_adapter.is_capability_supported(BrokerCapability.HEDGING)
        
    @pytest.mark.asyncio
    async def test_get_broker_info(self, mock_adapter):
        info = await mock_adapter.get_broker_info()
        assert isinstance(info, BrokerInfo)
        assert info.name == "oanda"
        assert info.display_name == "OANDA"
        assert BrokerCapability.MARKET_ORDERS in info.capabilities
        
    @pytest.mark.asyncio
    async def test_authentication(self, mock_adapter):
        result = await mock_adapter.authenticate({
            'api_key': 'test_key',
            'account_id': 'test_account'
        })
        assert result is True
        
    @pytest.mark.asyncio
    async def test_health_check(self, mock_adapter):
        health = await mock_adapter.health_check()
        assert health['status'] == 'healthy'


class TestOrderValidation:
    """Test order validation functionality"""
    
    @pytest.fixture
    def mock_adapter(self):
        return MockOandaBrokerAdapter({'account_id': 'test'})
        
    def test_valid_market_order(self, mock_adapter):
        order = UnifiedOrder(
            order_id="test_1",
            client_order_id="client_1",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("1000")
        )
        errors = mock_adapter.validate_order(order)
        assert len(errors) == 0
        
    def test_valid_limit_order(self, mock_adapter):
        order = UnifiedOrder(
            order_id="test_2",
            client_order_id="client_2",
            instrument="EUR_USD",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            units=Decimal("1000"),
            price=Decimal("1.1000")
        )
        errors = mock_adapter.validate_order(order)
        assert len(errors) == 0
        
    def test_invalid_instrument(self, mock_adapter):
        order = UnifiedOrder(
            order_id="test_3",
            client_order_id="client_3",
            instrument="INVALID",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("1000")
        )
        errors = mock_adapter.validate_order(order)
        assert len(errors) > 0
        assert any("not supported" in error for error in errors)
        
    def test_invalid_order_type(self, mock_adapter):
        # Mock adapter doesn't support trailing stops
        mock_adapter._supported_order_types = [OrderType.MARKET, OrderType.LIMIT]
        
        order = UnifiedOrder(
            order_id="test_4",
            client_order_id="client_4",
            instrument="EUR_USD",
            order_type=OrderType.TRAILING_STOP,
            side=OrderSide.BUY,
            units=Decimal("1000")
        )
        errors = mock_adapter.validate_order(order)
        assert len(errors) > 0
        assert any("not supported" in error for error in errors)
        
    def test_limit_order_without_price(self, mock_adapter):
        order = UnifiedOrder(
            order_id="test_5",
            client_order_id="client_5",
            instrument="EUR_USD",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            units=Decimal("1000")
            # Missing price
        )
        errors = mock_adapter.validate_order(order)
        assert len(errors) > 0
        assert any("require price" in error for error in errors)
        
    def test_negative_units(self, mock_adapter):
        order = UnifiedOrder(
            order_id="test_6",
            client_order_id="client_6",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("-1000")
        )
        errors = mock_adapter.validate_order(order)
        assert len(errors) > 0
        assert any("positive" in error for error in errors)


class TestOrderOperations:
    """Test order operations"""
    
    @pytest.fixture
    def mock_adapter(self):
        return MockOandaBrokerAdapter({'account_id': 'test'})
        
    @pytest.mark.asyncio
    async def test_place_market_order_success(self, mock_adapter):
        order = UnifiedOrder(
            order_id="test_order",
            client_order_id="client_123",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("1000")
        )
        
        result = await mock_adapter.place_order(order)
        
        assert result.success is True
        assert result.order_id == "test_order_123"
        assert result.client_order_id == "client_123"
        assert result.fill_price == Decimal("1.1000")
        assert result.filled_units == Decimal("1000")
        
    @pytest.mark.asyncio
    async def test_place_invalid_order(self, mock_adapter):
        order = UnifiedOrder(
            order_id="test_order",
            client_order_id="client_123",
            instrument="INVALID",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("1000")
        )
        
        result = await mock_adapter.place_order(order)
        
        assert result.success is False
        assert result.error_code == "VALIDATION_ERROR"
        assert "not supported" in result.error_message
        
    @pytest.mark.asyncio
    async def test_modify_order(self, mock_adapter):
        result = await mock_adapter.modify_order("test_order", {"price": "1.1100"})
        assert result.success is True
        assert result.order_id == "test_order"
        
    @pytest.mark.asyncio
    async def test_cancel_order(self, mock_adapter):
        result = await mock_adapter.cancel_order("test_order", "User requested")
        assert result.success is True
        assert result.order_id == "test_order"
        
    @pytest.mark.asyncio
    async def test_get_order(self, mock_adapter):
        order = await mock_adapter.get_order("test_order")
        assert order is not None
        assert order.order_id == "test_order"
        assert order.instrument == "EUR_USD"
        
    @pytest.mark.asyncio
    async def test_get_orders(self, mock_adapter):
        orders = await mock_adapter.get_orders()
        assert len(orders) >= 1
        assert all(isinstance(order, UnifiedOrder) for order in orders)


class TestPositionOperations:
    """Test position operations"""
    
    @pytest.fixture
    def mock_adapter(self):
        return MockOandaBrokerAdapter({'account_id': 'test'})
        
    @pytest.mark.asyncio
    async def test_get_position(self, mock_adapter):
        position = await mock_adapter.get_position("EUR_USD")
        assert position is not None
        assert position.instrument == "EUR_USD"
        assert position.side == PositionSide.LONG
        assert position.units == Decimal("1000")
        
    @pytest.mark.asyncio
    async def test_get_positions(self, mock_adapter):
        positions = await mock_adapter.get_positions()
        assert len(positions) >= 1
        assert all(isinstance(pos, UnifiedPosition) for pos in positions)
        
    @pytest.mark.asyncio
    async def test_close_position_full(self, mock_adapter):
        result = await mock_adapter.close_position("EUR_USD")
        assert result.success is True
        assert result.filled_units == Decimal("1000")
        
    @pytest.mark.asyncio
    async def test_close_position_partial(self, mock_adapter):
        result = await mock_adapter.close_position("EUR_USD", Decimal("500"))
        assert result.success is True
        assert result.filled_units == Decimal("500")


class TestMarketDataOperations:
    """Test market data operations"""
    
    @pytest.fixture
    def mock_adapter(self):
        return MockOandaBrokerAdapter({'account_id': 'test'})
        
    @pytest.mark.asyncio
    async def test_get_current_price(self, mock_adapter):
        price = await mock_adapter.get_current_price("EUR_USD")
        assert price is not None
        assert price.instrument == "EUR_USD"
        assert price.bid > 0
        assert price.ask > price.bid
        assert price.spread == price.ask - price.bid
        
    @pytest.mark.asyncio
    async def test_get_current_price_validation(self, mock_adapter):
        with pytest.raises(ValueError, match="Instrument is required"):
            await mock_adapter.get_current_price("")
            
    @pytest.mark.asyncio
    async def test_get_current_prices(self, mock_adapter):
        instruments = ["EUR_USD", "GBP_USD"]
        prices = await mock_adapter.get_current_prices(instruments)
        
        assert len(prices) == 2
        assert "EUR_USD" in prices
        assert "GBP_USD" in prices
        assert all(isinstance(price, PriceTick) for price in prices.values())
        
    @pytest.mark.asyncio
    async def test_get_current_prices_validation(self, mock_adapter):
        with pytest.raises(ValueError, match="Instruments list is required"):
            await mock_adapter.get_current_prices([])
            
    @pytest.mark.asyncio
    async def test_stream_prices(self, mock_adapter):
        instruments = ["EUR_USD"]
        price_stream = mock_adapter.stream_prices(instruments)
        
        price = await price_stream.__anext__()
        assert isinstance(price, PriceTick)
        assert price.instrument == "EUR_USD"
        
    @pytest.mark.asyncio
    async def test_get_historical_data(self, mock_adapter):
        data = await mock_adapter.get_historical_data(
            instrument="EUR_USD",
            granularity="H1",
            count=100
        )
        assert len(data) >= 1
        assert "time" in data[0]
        assert "o" in data[0]  # Open price


class TestAccountOperations:
    """Test account operations"""
    
    @pytest.fixture
    def mock_adapter(self):
        return MockOandaBrokerAdapter({'account_id': 'test'})
        
    @pytest.mark.asyncio
    async def test_get_account_summary(self, mock_adapter):
        summary = await mock_adapter.get_account_summary()
        assert isinstance(summary, UnifiedAccountSummary)
        assert summary.account_id == "test"
        assert summary.currency == "USD"
        assert summary.balance > 0
        
    @pytest.mark.asyncio
    async def test_get_accounts(self, mock_adapter):
        accounts = await mock_adapter.get_accounts()
        assert len(accounts) >= 1
        assert all(isinstance(acc, UnifiedAccountSummary) for acc in accounts)


class TestTransactionRecording:
    """Test transaction recording functionality"""
    
    @pytest.fixture
    def mock_adapter(self):
        return MockOandaBrokerAdapter({'account_id': 'test'})
        
    @pytest.mark.asyncio
    async def test_add_transaction_recorder(self, mock_adapter):
        recorded_transactions = []
        
        def recorder(transaction_data):
            recorded_transactions.append(transaction_data)
            
        mock_adapter.add_transaction_recorder(recorder)
        assert len(mock_adapter._transaction_recorders) == 1
        
        # Test recording
        order = UnifiedOrder(
            order_id="test_order",
            client_order_id="client_123",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("1000")
        )
        result = OrderResult(success=True, order_id="test_order_123")
        
        await mock_adapter._record_order_transaction(order, result)
        
        assert len(recorded_transactions) == 1
        transaction = recorded_transactions[0]
        assert transaction['transaction_type'] == 'ORDER_PLACE'
        assert transaction['instrument'] == 'EUR_USD'
        assert transaction['success'] is True
        
    @pytest.mark.asyncio
    async def test_remove_transaction_recorder(self, mock_adapter):
        def recorder(transaction_data):
            pass
            
        mock_adapter.add_transaction_recorder(recorder)
        assert len(mock_adapter._transaction_recorders) == 1
        
        mock_adapter.remove_transaction_recorder(recorder)
        assert len(mock_adapter._transaction_recorders) == 0
        
    @pytest.mark.asyncio
    async def test_async_transaction_recorder(self, mock_adapter):
        recorded_transactions = []
        
        async def async_recorder(transaction_data):
            recorded_transactions.append(transaction_data)
            
        mock_adapter.add_transaction_recorder(async_recorder)
        
        order = UnifiedOrder(
            order_id="test_order",
            client_order_id="client_123",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("1000")
        )
        result = OrderResult(success=True, order_id="test_order_123")
        
        await mock_adapter._record_order_transaction(order, result)
        
        assert len(recorded_transactions) == 1


class TestErrorHandling:
    """Test error handling and mapping"""
    
    def test_standard_broker_error_creation(self):
        error = StandardBrokerError(
            error_code=StandardErrorCode.AUTHENTICATION_FAILED,
            message="Invalid API key",
            severity=ErrorSeverity.HIGH,
            broker_specific_code="401",
            broker_specific_message="Unauthorized"
        )
        
        assert error.error_code == StandardErrorCode.AUTHENTICATION_FAILED
        assert error.message == "Invalid API key"
        assert error.severity == ErrorSeverity.HIGH
        assert error.category == ErrorCategory.AUTHENTICATION
        assert error.broker_specific_code == "401"
        
    def test_error_context(self):
        context = ErrorContext(
            broker_name="oanda",
            account_id="test_account",
            operation="place_order",
            instrument="EUR_USD"
        )
        
        error = StandardBrokerError(
            error_code=StandardErrorCode.INVALID_ORDER,
            message="Invalid order",
            context=context
        )
        
        assert error.context.broker_name == "oanda"
        assert error.context.account_id == "test_account"
        
    def test_error_to_dict(self):
        error = StandardBrokerError(
            error_code=StandardErrorCode.SERVER_ERROR,
            message="Server error",
            is_retryable=True,
            retry_after_seconds=60
        )
        
        error_dict = error.to_dict()
        assert error_dict['error_code'] == 'SERVER_ERROR'
        assert error_dict['message'] == 'Server error'
        assert error_dict['is_retryable'] is True
        assert error_dict['retry_after_seconds'] == 60
        
    def test_error_from_dict(self):
        error_dict = {
            'error_code': 'TIMEOUT',
            'message': 'Request timeout',
            'severity': 'medium',
            'category': 'technical',
            'is_retryable': True
        }
        
        error = StandardBrokerError.from_dict(error_dict)
        assert error.error_code == StandardErrorCode.TIMEOUT
        assert error.message == 'Request timeout'
        assert error.is_retryable is True
        
    def test_error_mapper(self):
        mapper = ErrorCodeMapper()
        
        # Test OANDA error mapping
        error = mapper.map_error(
            broker_name="oanda",
            broker_error_code="UNAUTHORIZED",
            message="Invalid credentials"
        )
        
        assert error.error_code == StandardErrorCode.AUTHENTICATION_FAILED
        assert error.severity == ErrorSeverity.HIGH
        assert error.is_retryable is False
        assert "credentials" in error.suggested_action
        
    def test_error_mapper_unknown_error(self):
        mapper = ErrorCodeMapper()
        
        # Test unknown error mapping
        error = mapper.map_error(
            broker_name="unknown_broker",
            broker_error_code="UNKNOWN_CODE",
            message="Unknown error"
        )
        
        assert error.error_code == StandardErrorCode.UNKNOWN_ERROR
        assert error.severity == ErrorSeverity.MEDIUM


class TestOandaAuthHandler:
    """Test OANDA authentication handler"""
    
    @pytest.fixture
    def mock_credential_manager(self):
        manager = Mock(spec=OandaCredentialManager)
        manager.retrieve_credentials = AsyncMock(return_value={
            'api_key': 'test_api_key',
            'account_id': 'test_account',
            'environment': 'practice'
        })
        return manager
        
    @pytest.fixture
    def auth_handler(self, mock_credential_manager):
        return OandaAuthHandler(mock_credential_manager)
        
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, auth_handler, mock_credential_manager):
        with patch.object(auth_handler, '_test_authentication', return_value=True):
            context = await auth_handler.authenticate_user(
                user_id="test_user",
                account_id="test_account",
                environment="practice"
            )
            
            assert isinstance(context, AccountContext)
            assert context.user_id == "test_user"
            assert context.account_id == "test_account"
            assert context.environment == Environment.PRACTICE
            assert context.session_valid is True
            
    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_environment(self, auth_handler):
        with pytest.raises(AuthenticationError, match="Invalid environment"):
            await auth_handler.authenticate_user(
                user_id="test_user",
                account_id="test_account",
                environment="invalid"
            )
            
    @pytest.mark.asyncio
    async def test_authenticate_user_no_credentials(self, auth_handler, mock_credential_manager):
        mock_credential_manager.retrieve_credentials.return_value = None
        
        with pytest.raises(AuthenticationError, match="No credentials found"):
            await auth_handler.authenticate_user(
                user_id="test_user",
                account_id="test_account",
                environment="practice"
            )
            
    @pytest.mark.asyncio
    async def test_authenticate_user_auth_test_failed(self, auth_handler, mock_credential_manager):
        with patch.object(auth_handler, '_test_authentication', return_value=False):
            with pytest.raises(AuthenticationError, match="Authentication test failed"):
                await auth_handler.authenticate_user(
                    user_id="test_user",
                    account_id="test_account",
                    environment="practice"
                )
                
    @pytest.mark.asyncio
    async def test_get_session_context_valid(self, auth_handler, mock_credential_manager):
        # First authenticate to create session
        with patch.object(auth_handler, '_test_authentication', return_value=True):
            await auth_handler.authenticate_user(
                user_id="test_user",
                account_id="test_account",
                environment="practice"
            )
            
        # Now get the session
        context = await auth_handler.get_session_context("test_user", "test_account")
        assert context is not None
        assert context.session_valid is True
        
    @pytest.mark.asyncio
    async def test_get_session_context_expired(self, auth_handler, mock_credential_manager):
        # Create expired session
        with patch.object(auth_handler, '_test_authentication', return_value=True):
            await auth_handler.authenticate_user(
                user_id="test_user",
                account_id="test_account",
                environment="practice"
            )
            
        # Mock expired session
        session_key = "test_user:test_account"
        context = auth_handler.active_sessions[session_key]
        context.last_refresh = datetime.utcnow() - timedelta(hours=3)
        
        with patch.object(auth_handler, '_refresh_session', return_value=True):
            refreshed_context = await auth_handler.get_session_context("test_user", "test_account")
            assert refreshed_context is not None
            
    def test_get_session_stats(self, auth_handler):
        # Create mock sessions
        auth_handler.active_sessions = {
            "user1:account1": AccountContext(
                user_id="user1",
                account_id="account1",
                environment=Environment.PRACTICE,
                api_key="key1",
                base_url="url1",
                authenticated_at=datetime.utcnow(),
                last_refresh=datetime.utcnow(),
                session_valid=True
            ),
            "user2:account2": AccountContext(
                user_id="user2",
                account_id="account2",
                environment=Environment.LIVE,
                api_key="key2",
                base_url="url2",
                authenticated_at=datetime.utcnow(),
                last_refresh=datetime.utcnow() - timedelta(hours=3),
                session_valid=False
            )
        }
        
        stats = auth_handler.get_session_stats()
        assert stats['total_sessions'] == 2
        assert stats['valid_sessions'] == 1
        assert stats['expired_sessions'] == 1
        assert stats['environments']['practice'] == 1
        assert stats['environments']['live'] == 1


class TestDataClassesAndEnums:
    """Test data classes and enums"""
    
    def test_unified_order_creation(self):
        order = UnifiedOrder(
            order_id="test_order",
            client_order_id="client_123",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("1000")
        )
        
        assert order.order_id == "test_order"
        assert order.remaining_units == Decimal("1000")  # Should be set in __post_init__
        assert order.state == OrderState.PENDING
        assert isinstance(order.creation_time, datetime)
        
    def test_price_tick_spread_calculation(self):
        tick = PriceTick(
            instrument="EUR_USD",
            bid=Decimal("1.1000"),
            ask=Decimal("1.1002"),
            timestamp=datetime.now(timezone.utc)
        )
        
        assert tick.spread == Decimal("0.0002")
        
    def test_order_result_creation(self):
        result = OrderResult(
            success=True,
            order_id="order_123",
            fill_price=Decimal("1.1000"),
            filled_units=Decimal("1000")
        )
        
        assert result.success is True
        assert result.order_id == "order_123"
        
    def test_broker_info_creation(self):
        info = BrokerInfo(
            name="test_broker",
            display_name="Test Broker",
            version="1.0",
            capabilities={BrokerCapability.MARKET_ORDERS},
            supported_instruments=["EUR_USD"],
            supported_order_types=[OrderType.MARKET],
            supported_time_in_force=[TimeInForce.GTC],
            minimum_trade_size={"EUR_USD": Decimal("1")},
            maximum_trade_size={"EUR_USD": Decimal("1000000")},
            commission_structure={"type": "commission"},
            margin_requirements={"EUR_USD": Decimal("0.03")},
            trading_hours={"EUR_USD": {"open": "22:00", "close": "22:00"}},
            api_rate_limits={"orders": 100}
        )
        
        assert info.name == "test_broker"
        assert BrokerCapability.MARKET_ORDERS in info.capabilities
        assert "EUR_USD" in info.supported_instruments


class TestErrorCategories:
    """Test error categorization"""
    
    def test_authentication_errors(self):
        error = StandardBrokerError(
            error_code=StandardErrorCode.AUTHENTICATION_FAILED,
            message="Auth failed"
        )
        assert error.category == ErrorCategory.AUTHENTICATION
        
    def test_validation_errors(self):
        error = StandardBrokerError(
            error_code=StandardErrorCode.INVALID_ORDER,
            message="Invalid order"
        )
        assert error.category == ErrorCategory.VALIDATION
        
    def test_technical_errors(self):
        error = StandardBrokerError(
            error_code=StandardErrorCode.TIMEOUT,
            message="Request timeout"
        )
        assert error.category == ErrorCategory.TECHNICAL
        
    def test_regulatory_errors(self):
        error = StandardBrokerError(
            error_code=StandardErrorCode.FIFO_VIOLATION,
            message="FIFO violation"
        )
        assert error.category == ErrorCategory.REGULATORY


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])