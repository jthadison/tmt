"""
Focused Coverage Boost Tests for Broker Integration
Story 8.12 - Critical Coverage Gap Resolution

This test suite focuses on exercising existing code paths in the actual modules
to achieve immediate coverage improvements without complex mocking.
"""
import pytest
import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import json
import time

# Test imports
import sys
from pathlib import Path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Import the modules that exist
from broker_adapter import BrokerAdapter, UnifiedOrder, UnifiedPosition, OrderType, OrderSide
from unified_errors import StandardBrokerError, StandardErrorCode, ErrorSeverity
from oanda_auth_handler import OandaAuthHandler, Environment
from connection_pool import OandaConnectionPool, PooledConnection, ConnectionState
from credential_manager import OandaCredentialManager


class TestBrokerAdapterExtended:
    """Extended tests for BrokerAdapter to increase coverage"""
    
    @pytest.fixture
    def mock_broker_adapter(self):
        """Create mock broker adapter instance"""
        config = {
            "broker_name": "test_broker",
            "api_key": "test_key",
            "account_id": "test_account"
        }
        adapter = BrokerAdapter(config)
        return adapter
    
    def test_broker_adapter_config_properties(self, mock_broker_adapter):
        """Test broker adapter configuration properties"""
        assert mock_broker_adapter.broker_name == "test_broker"
        assert mock_broker_adapter.config["api_key"] == "test_key"
        assert mock_broker_adapter.config["account_id"] == "test_account"
    
    def test_unified_order_creation(self):
        """Test UnifiedOrder creation and validation"""
        order = UnifiedOrder(
            order_id="test_order_123",
            client_order_id="client_123",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("1000"),
            price=None,
            stop_loss=Decimal("1.0950"),
            take_profit=Decimal("1.1050")
        )
        
        assert order.order_id == "test_order_123"
        assert order.client_order_id == "client_123"
        assert order.instrument == "EUR_USD"
        assert order.order_type == OrderType.MARKET
        assert order.side == OrderSide.BUY
        assert order.units == Decimal("1000")
        assert order.stop_loss == Decimal("1.0950")
        assert order.take_profit == Decimal("1.1050")
    
    def test_unified_order_limit_order(self):
        """Test UnifiedOrder for limit order"""
        order = UnifiedOrder(
            order_id="limit_order_123",
            client_order_id="client_limit_123",
            instrument="GBP_USD",
            order_type=OrderType.LIMIT,
            side=OrderSide.SELL,
            units=Decimal("1500"),
            price=Decimal("1.2550")
        )
        
        assert order.order_type == OrderType.LIMIT
        assert order.price == Decimal("1.2550")
        assert order.side == OrderSide.SELL
    
    def test_unified_position_creation(self):
        """Test UnifiedPosition creation"""
        position = UnifiedPosition(
            position_id="pos_123",
            instrument="EUR_USD",
            units=Decimal("1000"),
            side=OrderSide.BUY,
            average_price=Decimal("1.1000"),
            current_price=Decimal("1.1025"),
            unrealized_pl=Decimal("25.00"),
            margin_used=Decimal("550.00")
        )
        
        assert position.position_id == "pos_123"
        assert position.instrument == "EUR_USD"
        assert position.units == Decimal("1000")
        assert position.side == OrderSide.BUY
        assert position.unrealized_pl == Decimal("25.00")
    
    def test_order_type_enum_values(self):
        """Test OrderType enum values"""
        assert OrderType.MARKET.value == "MARKET"
        assert OrderType.LIMIT.value == "LIMIT"
        assert OrderType.STOP.value == "STOP"
        assert OrderType.STOP_LOSS.value == "STOP_LOSS"
        assert OrderType.TAKE_PROFIT.value == "TAKE_PROFIT"
    
    def test_order_side_enum_values(self):
        """Test OrderSide enum values"""
        assert OrderSide.BUY.value == "BUY"
        assert OrderSide.SELL.value == "SELL"
    
    @pytest.mark.asyncio
    async def test_broker_adapter_abstract_methods(self, mock_broker_adapter):
        """Test that abstract methods raise NotImplementedError"""
        order = UnifiedOrder(
            order_id="test",
            client_order_id="client",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("1000")
        )
        
        with pytest.raises(NotImplementedError):
            await mock_broker_adapter.authenticate()
        
        with pytest.raises(NotImplementedError):
            await mock_broker_adapter.place_order(order)
        
        with pytest.raises(NotImplementedError):
            await mock_broker_adapter.cancel_order("test_order")
        
        with pytest.raises(NotImplementedError):
            await mock_broker_adapter.get_positions()
        
        with pytest.raises(NotImplementedError):
            await mock_broker_adapter.get_account_summary()


class TestUnifiedErrorsExtended:
    """Extended tests for UnifiedErrors to increase coverage"""
    
    def test_standard_broker_error_creation(self):
        """Test StandardBrokerError creation"""
        error = StandardBrokerError(
            error_code=StandardErrorCode.AUTHENTICATION_FAILED,
            message="Invalid API key",
            severity=ErrorSeverity.HIGH,
            context={"api_key": "****", "account": "test"}
        )
        
        assert error.error_code == StandardErrorCode.AUTHENTICATION_FAILED
        assert error.message == "Invalid API key"
        assert error.severity == ErrorSeverity.HIGH
        assert error.context["account"] == "test"
    
    def test_standard_error_code_enum_values(self):
        """Test StandardErrorCode enum values"""
        assert StandardErrorCode.AUTHENTICATION_FAILED.value == "AUTHENTICATION_FAILED"
        assert StandardErrorCode.INSUFFICIENT_MARGIN.value == "INSUFFICIENT_MARGIN"
        assert StandardErrorCode.INVALID_INSTRUMENT.value == "INVALID_INSTRUMENT"
        assert StandardErrorCode.MARKET_CLOSED.value == "MARKET_CLOSED"
        assert StandardErrorCode.RATE_LIMIT_EXCEEDED.value == "RATE_LIMIT_EXCEEDED"
        assert StandardErrorCode.CONNECTION_FAILED.value == "CONNECTION_FAILED"
    
    def test_error_severity_enum_values(self):
        """Test ErrorSeverity enum values"""
        assert ErrorSeverity.LOW.value == "LOW"
        assert ErrorSeverity.MEDIUM.value == "MEDIUM"  
        assert ErrorSeverity.HIGH.value == "HIGH"
        assert ErrorSeverity.CRITICAL.value == "CRITICAL"
    
    def test_standard_broker_error_string_representation(self):
        """Test string representation of StandardBrokerError"""
        error = StandardBrokerError(
            error_code=StandardErrorCode.CONNECTION_FAILED,
            message="Connection timeout",
            severity=ErrorSeverity.MEDIUM
        )
        
        error_str = str(error)
        assert "CONNECTION_FAILED" in error_str
        assert "Connection timeout" in error_str
        assert "MEDIUM" in error_str
    
    def test_error_with_original_exception(self):
        """Test error with original exception"""
        original_exception = ValueError("Invalid parameter")
        error = StandardBrokerError(
            error_code=StandardErrorCode.INVALID_PARAMETER,
            message="Parameter validation failed",
            severity=ErrorSeverity.MEDIUM,
            original_exception=original_exception
        )
        
        assert error.original_exception == original_exception
        assert isinstance(error.original_exception, ValueError)
    
    def test_error_timestamp(self):
        """Test error timestamp is set"""
        error = StandardBrokerError(
            error_code=StandardErrorCode.RATE_LIMIT_EXCEEDED,
            message="Too many requests",
            severity=ErrorSeverity.HIGH
        )
        
        assert error.timestamp is not None
        assert isinstance(error.timestamp, datetime)
        assert error.timestamp.tzinfo is not None


class TestOandaAuthHandlerExtended:
    """Extended tests for OandaAuthHandler to increase coverage"""
    
    @pytest.fixture
    def auth_handler(self):
        """Create OandaAuthHandler instance"""
        config = {
            "api_key": "test_api_key",
            "account_id": "test_account",
            "environment": Environment.PRACTICE
        }
        return OandaAuthHandler(config)
    
    def test_auth_handler_initialization(self, auth_handler):
        """Test auth handler initialization"""
        assert auth_handler.api_key == "test_api_key"
        assert auth_handler.account_id == "test_account"
        assert auth_handler.environment == Environment.PRACTICE
        assert auth_handler.session_timeout == timedelta(hours=1)
    
    def test_environment_enum_values(self):
        """Test Environment enum values"""
        assert Environment.PRACTICE.value == "practice"
        assert Environment.LIVE.value == "live"
    
    def test_generate_session_id(self, auth_handler):
        """Test session ID generation"""
        session_id = auth_handler._generate_session_id()
        assert session_id is not None
        assert len(session_id) > 0
        assert isinstance(session_id, str)
        
        # Generate another ID and ensure it's different
        session_id2 = auth_handler._generate_session_id()
        assert session_id != session_id2
    
    @pytest.mark.asyncio
    async def test_authenticate_user_with_mock(self, auth_handler):
        """Test user authentication with mock"""
        with patch.object(auth_handler, '_validate_credentials', return_value=True):
            result = await auth_handler.authenticate_user("test_user", "test_pass")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_authenticate_user_failure(self, auth_handler):
        """Test user authentication failure"""
        with patch.object(auth_handler, '_validate_credentials', return_value=False):
            result = await auth_handler.authenticate_user("invalid_user", "invalid_pass")
            assert result is False
    
    def test_get_session_context_no_session(self, auth_handler):
        """Test getting session context when no session exists"""
        context = auth_handler.get_session_context("nonexistent_session")
        assert context is None
    
    def test_session_timeout_property(self, auth_handler):
        """Test session timeout property"""
        assert auth_handler.session_timeout == timedelta(hours=1)
        
        # Test setting new timeout
        auth_handler.session_timeout = timedelta(minutes=30)
        assert auth_handler.session_timeout == timedelta(minutes=30)


class TestConnectionPoolExtended:
    """Extended tests for OandaConnectionPool to increase coverage"""
    
    @pytest.fixture
    def connection_pool(self):
        """Create OandaConnectionPool instance"""
        config = {
            "max_connections": 10,
            "connection_timeout": 30,
            "idle_timeout": 300
        }
        return OandaConnectionPool(config)
    
    def test_connection_pool_initialization(self, connection_pool):
        """Test connection pool initialization"""
        assert connection_pool.max_connections == 10
        assert connection_pool.connection_timeout == 30
        assert connection_pool.idle_timeout == 300
        assert len(connection_pool.active_connections) == 0
        assert len(connection_pool.idle_connections) == 0
    
    def test_pooled_connection_creation(self):
        """Test PooledConnection creation"""
        connection = PooledConnection(
            connection_id="conn_123",
            host="api.oanda.com",
            port=443,
            ssl=True
        )
        
        assert connection.connection_id == "conn_123"
        assert connection.host == "api.oanda.com"
        assert connection.port == 443
        assert connection.ssl is True
        assert connection.state == ConnectionState.IDLE
        assert connection.created_at is not None
    
    def test_connection_state_enum(self):
        """Test ConnectionState enum values"""
        assert ConnectionState.IDLE.value == "idle"
        assert ConnectionState.ACTIVE.value == "active"
        assert ConnectionState.CLOSED.value == "closed"
        assert ConnectionState.ERROR.value == "error"
    
    @pytest.mark.asyncio
    async def test_acquire_connection_empty_pool(self, connection_pool):
        """Test acquiring connection from empty pool"""
        with patch.object(connection_pool, '_create_new_connection') as mock_create:
            mock_connection = PooledConnection("new_conn", "api.oanda.com", 443, True)
            mock_create.return_value = mock_connection
            
            connection = await connection_pool.acquire_connection()
            
            assert connection is not None
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_release_connection(self, connection_pool):
        """Test releasing connection back to pool"""
        connection = PooledConnection("test_conn", "api.oanda.com", 443, True)
        connection.state = ConnectionState.ACTIVE
        
        await connection_pool.release_connection(connection)
        
        assert connection.state == ConnectionState.IDLE
        assert connection in connection_pool.idle_connections
    
    def test_get_pool_statistics(self, connection_pool):
        """Test getting pool statistics"""
        # Add some mock connections
        connection_pool.active_connections = [
            PooledConnection("active_1", "api.oanda.com", 443, True),
            PooledConnection("active_2", "api.oanda.com", 443, True)
        ]
        connection_pool.idle_connections = [
            PooledConnection("idle_1", "api.oanda.com", 443, True)
        ]
        
        stats = connection_pool.get_statistics()
        
        assert stats["active_connections"] == 2
        assert stats["idle_connections"] == 1
        assert stats["total_connections"] == 3
        assert stats["max_connections"] == 10


class TestCredentialManagerExtended:
    """Extended tests for OandaCredentialManager to increase coverage"""
    
    @pytest.fixture
    def credential_manager(self):
        """Create OandaCredentialManager instance"""
        return OandaCredentialManager()
    
    def test_credential_manager_initialization(self, credential_manager):
        """Test credential manager initialization"""
        assert credential_manager is not None
        assert hasattr(credential_manager, 'credentials')
    
    def test_store_credentials(self, credential_manager):
        """Test storing credentials"""
        credentials = {
            "api_key": "test_api_key_123",
            "account_id": "test_account_456",
            "environment": "practice"
        }
        
        success = credential_manager.store_credentials("test_profile", credentials)
        assert success is True
    
    def test_retrieve_credentials(self, credential_manager):
        """Test retrieving credentials"""
        credentials = {
            "api_key": "test_api_key_123",
            "account_id": "test_account_456",
            "environment": "practice"
        }
        
        credential_manager.store_credentials("test_profile", credentials)
        retrieved = credential_manager.retrieve_credentials("test_profile")
        
        assert retrieved is not None
        assert retrieved["api_key"] == "test_api_key_123"
        assert retrieved["account_id"] == "test_account_456"
    
    def test_retrieve_nonexistent_credentials(self, credential_manager):
        """Test retrieving nonexistent credentials"""
        retrieved = credential_manager.retrieve_credentials("nonexistent_profile")
        assert retrieved is None
    
    def test_validate_credentials_format(self, credential_manager):
        """Test credentials format validation"""
        valid_credentials = {
            "api_key": "valid_key_with_sufficient_length",
            "account_id": "123456",
            "environment": "practice"
        }
        
        is_valid = credential_manager.validate_credentials(valid_credentials)
        assert is_valid is True
        
        invalid_credentials = {
            "api_key": "short",  # Too short
            "account_id": "",    # Empty
            "environment": "invalid_env"  # Invalid environment
        }
        
        is_valid = credential_manager.validate_credentials(invalid_credentials)
        assert is_valid is False
    
    def test_list_credential_profiles(self, credential_manager):
        """Test listing credential profiles"""
        # Store some test profiles
        credential_manager.store_credentials("profile1", {"api_key": "key1", "account_id": "acc1", "environment": "practice"})
        credential_manager.store_credentials("profile2", {"api_key": "key2", "account_id": "acc2", "environment": "live"})
        
        profiles = credential_manager.list_profiles()
        
        assert "profile1" in profiles
        assert "profile2" in profiles
        assert len(profiles) >= 2
    
    def test_delete_credentials(self, credential_manager):
        """Test deleting credentials"""
        credentials = {
            "api_key": "test_key_to_delete",
            "account_id": "test_account",
            "environment": "practice"
        }
        
        credential_manager.store_credentials("delete_test", credentials)
        assert credential_manager.retrieve_credentials("delete_test") is not None
        
        success = credential_manager.delete_credentials("delete_test")
        assert success is True
        assert credential_manager.retrieve_credentials("delete_test") is None


# Test utility functions and module-level functionality
class TestModuleFunctionality:
    """Test module-level functionality and utility functions"""
    
    def test_import_all_main_modules(self):
        """Test that all main modules can be imported"""
        try:
            import broker_adapter
            import unified_errors
            import oanda_auth_handler
            import connection_pool
            import credential_manager
            
            # Basic sanity checks
            assert hasattr(broker_adapter, 'BrokerAdapter')
            assert hasattr(unified_errors, 'StandardBrokerError')
            assert hasattr(oanda_auth_handler, 'OandaAuthHandler')
            assert hasattr(connection_pool, 'ConnectionPool')
            assert hasattr(credential_manager, 'OandaCredentialManager')
            
        except ImportError as e:
            pytest.fail(f"Failed to import module: {e}")
    
    def test_decimal_precision_handling(self):
        """Test decimal precision handling in orders"""
        # Test various decimal precisions
        precisions = [
            Decimal("1.0"),
            Decimal("1.00001"),
            Decimal("1.123456789"),
            Decimal("0.0001"),
            Decimal("1000.0")
        ]
        
        for precision in precisions:
            order = UnifiedOrder(
                order_id="precision_test",
                client_order_id="client_precision",
                instrument="EUR_USD", 
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                units=precision
            )
            
            assert order.units == precision
            assert isinstance(order.units, Decimal)
    
    def test_datetime_handling(self):
        """Test datetime handling across modules"""
        current_time = datetime.now(timezone.utc)
        
        error = StandardBrokerError(
            error_code=StandardErrorCode.CONNECTION_FAILED,
            message="Test error",
            severity=ErrorSeverity.LOW,
            timestamp=current_time
        )
        
        assert error.timestamp == current_time
        assert error.timestamp.tzinfo is not None
    
    def test_configuration_dict_handling(self):
        """Test configuration dictionary handling"""
        configs = [
            {"broker_name": "oanda", "api_key": "key1"},
            {"broker_name": "interactive_brokers", "api_key": "key2", "account_id": "acc1"},
            {"environment": "practice", "timeout": 30, "max_retries": 3}
        ]
        
        for config in configs:
            adapter = BrokerAdapter(config)
            assert adapter.config == config
            
            # Test configuration access
            for key, value in config.items():
                assert adapter.config.get(key) == value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])