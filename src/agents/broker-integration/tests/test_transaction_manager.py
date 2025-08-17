"""
Tests for Transaction Manager
Story 8.8 - Task 1 tests
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from transaction_manager import (
    OandaTransactionManager, TransactionRecord, TransactionType
)
from oanda_auth_handler import AccountContext, Environment


class TestOandaTransactionManager:
    """Test suite for OandaTransactionManager"""
    
    @pytest.fixture
    def auth_handler(self):
        """Mock auth handler"""
        auth_handler = MagicMock()
        
        # Create mock account context
        context = AccountContext(
            user_id="test_user",
            account_id="test_account",
            environment=Environment.PRACTICE,
            api_key="test_api_key",
            base_url="https://api-fxpractice.oanda.com",
            authenticated_at=datetime.utcnow(),
            last_refresh=datetime.utcnow()
        )
        
        auth_handler.active_sessions = {"test_account": context}
        return auth_handler
        
    @pytest.fixture
    def connection_pool(self):
        """Mock connection pool"""
        pool = MagicMock()
        
        # Mock session context manager
        session = MagicMock()
        response = MagicMock()
        response.status = 200
        response.json = AsyncMock(return_value={
            'transactions': [
                {
                    'id': '1',
                    'type': 'ORDER_FILL',
                    'instrument': 'EUR_USD',
                    'units': '1000',
                    'price': '1.1000',
                    'pl': '10.50',
                    'commission': '0.50',
                    'financing': '0.00',
                    'time': '2024-01-15T10:00:00.000000Z',
                    'accountBalance': '1000.00',
                    'reason': 'MARKET_ORDER'
                }
            ],
            'lastTransactionID': '1',
            'pages': []
        })
        
        session.get = AsyncMock(return_value=response)
        pool.get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        pool.get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        return pool
        
    @pytest.fixture
    def transaction_manager(self, auth_handler, connection_pool):
        """Transaction manager instance"""
        return OandaTransactionManager(auth_handler, connection_pool)
        
    @pytest.mark.asyncio
    async def test_get_transaction_history(self, transaction_manager):
        """Test getting transaction history"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        result = await transaction_manager.get_transaction_history(
            "test_account", start_date, end_date
        )
        
        assert result['count'] == 1
        assert len(result['transactions']) == 1
        
        transaction = result['transactions'][0]
        assert transaction.transaction_id == '1'
        assert transaction.transaction_type == 'ORDER_FILL'
        assert transaction.instrument == 'EUR_USD'
        assert transaction.units == Decimal('1000')
        assert transaction.price == Decimal('1.1000')
        assert transaction.pl == Decimal('10.50')
        
    @pytest.mark.asyncio
    async def test_parse_transaction(self, transaction_manager):
        """Test transaction parsing"""
        tx_data = {
            'id': '123',
            'type': 'TRADE_CLOSE',
            'instrument': 'GBP_USD',
            'units': '-500',
            'price': '1.2500',
            'pl': '-5.25',
            'commission': '0.25',
            'financing': '0.10',
            'time': '2024-01-15T15:30:00.000000Z',
            'accountBalance': '995.00',
            'reason': 'STOP_LOSS',
            'tradeID': 'T123'
        }
        
        transaction = await transaction_manager._parse_transaction(tx_data)
        
        assert transaction.transaction_id == '123'
        assert transaction.transaction_type == 'TRADE_CLOSE'
        assert transaction.instrument == 'GBP_USD'
        assert transaction.units == Decimal('-500')
        assert transaction.price == Decimal('1.2500')
        assert transaction.pl == Decimal('-5.25')
        assert transaction.commission == Decimal('0.25')
        assert transaction.financing == Decimal('0.10')
        assert transaction.account_balance == Decimal('995.00')
        assert transaction.reason == 'STOP_LOSS'
        assert transaction.trade_id == 'T123'
        
    @pytest.mark.asyncio
    async def test_get_transaction_by_id(self, transaction_manager, connection_pool):
        """Test getting specific transaction by ID"""
        # Mock single transaction response
        session = MagicMock()
        response = MagicMock()
        response.status = 200
        response.json = AsyncMock(return_value={
            'transaction': {
                'id': '456',
                'type': 'LIMIT_ORDER',
                'instrument': 'USD_JPY',
                'units': '0',
                'price': '110.00',
                'pl': '0.00',
                'commission': '0.00',
                'financing': '0.00',
                'time': '2024-01-15T12:00:00.000000Z',
                'accountBalance': '1000.00',
                'reason': 'CLIENT_ORDER'
            }
        })
        
        session.get = AsyncMock(return_value=response)
        connection_pool.get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        
        transaction = await transaction_manager.get_transaction_by_id("test_account", "456")
        
        assert transaction is not None
        assert transaction.transaction_id == '456'
        assert transaction.transaction_type == 'LIMIT_ORDER'
        assert transaction.instrument == 'USD_JPY'
        
    @pytest.mark.asyncio
    async def test_get_transaction_by_id_not_found(self, transaction_manager, connection_pool):
        """Test getting non-existent transaction"""
        # Mock 404 response
        session = MagicMock()
        response = MagicMock()
        response.status = 404
        
        session.get = AsyncMock(return_value=response)
        connection_pool.get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        
        transaction = await transaction_manager.get_transaction_by_id("test_account", "999")
        
        assert transaction is None
        
    @pytest.mark.asyncio
    async def test_cache_functionality(self, transaction_manager):
        """Test transaction caching"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        # First call should populate cache
        result1 = await transaction_manager.get_transaction_history(
            "test_account", start_date, end_date
        )
        
        cache_key = f"test_account:{start_date.isoformat()}:{end_date.isoformat()}"
        assert cache_key in transaction_manager.transaction_cache
        assert len(transaction_manager.transaction_cache[cache_key]) == 1
        
        # Clear cache
        transaction_manager.clear_cache("test_account")
        assert cache_key not in transaction_manager.transaction_cache
        
    @pytest.mark.asyncio
    async def test_error_handling(self, transaction_manager, connection_pool):
        """Test error handling for API failures"""
        # Mock error response
        session = MagicMock()
        response = MagicMock()
        response.status = 500
        response.text = AsyncMock(return_value="Internal Server Error")
        
        session.get = AsyncMock(return_value=response)
        connection_pool.get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        with pytest.raises(Exception) as exc_info:
            await transaction_manager.get_transaction_history(
                "test_account", start_date, end_date
            )
        
        assert "API Error: 500" in str(exc_info.value)
        
    def test_transaction_record_to_dict(self):
        """Test TransactionRecord serialization"""
        transaction = TransactionRecord(
            transaction_id="123",
            transaction_type="ORDER_FILL",
            instrument="EUR_USD",
            units=Decimal("1000"),
            price=Decimal("1.1000"),
            pl=Decimal("10.50"),
            commission=Decimal("0.50"),
            financing=Decimal("0.00"),
            timestamp=datetime(2024, 1, 15, 10, 0),
            account_balance=Decimal("1000.00"),
            reason="MARKET_ORDER"
        )
        
        data = transaction.to_dict()
        
        assert data['transaction_id'] == "123"
        assert data['units'] == "1000"
        assert data['price'] == "1.1000"
        assert data['pl'] == "10.50"
        assert '2024-01-15T10:00:00' in data['timestamp']
        
    @pytest.mark.asyncio
    async def test_transaction_filtering_by_type(self, transaction_manager):
        """Test filtering by transaction type"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        result = await transaction_manager.get_transaction_history(
            "test_account", start_date, end_date,
            transaction_types=[TransactionType.ORDER_FILL]
        )
        
        # Mock should be called with type parameter
        assert result['count'] == 1
        
    @pytest.mark.asyncio 
    async def test_pagination_support(self, transaction_manager):
        """Test pagination with page tokens"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        result = await transaction_manager.get_transaction_history(
            "test_account", start_date, end_date,
            page_token="test_token"
        )
        
        assert result['hasMore'] is False
        assert result['pageToken'] is None