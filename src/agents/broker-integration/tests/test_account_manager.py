"""
Tests for Account Manager - Story 8.2
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from datetime import datetime
import aiohttp
import json

from ..account_manager import (
    OandaAccountManager,
    AccountSummary,
    PositionSummary,
    OrderSummary,
    AccountCurrency,
    AccountDataCache
)

class TestAccountDataCache:
    """Test AccountDataCache functionality"""
    
    def test_cache_initialization(self):
        """Test cache initialization"""
        cache = AccountDataCache(ttl_seconds=10)
        assert cache.ttl.total_seconds() == 10
        assert len(cache.cache) == 0
        assert len(cache.timestamps) == 0
    
    def test_cache_set_get(self):
        """Test basic cache set/get operations"""
        cache = AccountDataCache(ttl_seconds=10)
        
        # Set data
        test_data = {"balance": "10000", "currency": "USD"}
        cache.set("test_key", test_data)
        
        # Get data
        retrieved = cache.get("test_key")
        assert retrieved == test_data
        assert "test_key" in cache.timestamps
    
    def test_cache_expiration(self):
        """Test cache expiration"""
        cache = AccountDataCache(ttl_seconds=0.1)  # Very short TTL
        
        # Set data
        test_data = {"balance": "10000"}
        cache.set("test_key", test_data)
        
        # Should be available immediately
        assert cache.get("test_key") == test_data
        
        # Wait for expiration
        import time
        time.sleep(0.2)
        
        # Should be expired
        assert cache.get("test_key") is None
        assert "test_key" not in cache.cache
    
    def test_cache_clear(self):
        """Test cache clearing"""
        cache = AccountDataCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        assert len(cache.cache) == 2
        
        cache.clear()
        assert len(cache.cache) == 0
        assert len(cache.timestamps) == 0

class TestAccountSummary:
    """Test AccountSummary functionality"""
    
    def create_test_summary(self):
        """Create test account summary"""
        return AccountSummary(
            account_id="test-account",
            currency=AccountCurrency.USD,
            balance=Decimal("10000.00"),
            unrealized_pl=Decimal("150.50"),
            realized_pl=Decimal("-25.75"),
            margin_used=Decimal("500.00"),
            margin_available=Decimal("9500.00"),
            margin_closeout_percent=Decimal("50.0"),
            margin_call_percent=Decimal("100.0"),
            open_position_count=3,
            pending_order_count=2,
            leverage=50,
            financing=Decimal("5.25"),
            commission=Decimal("2.50"),
            dividend_adjustment=Decimal("0.00"),
            account_equity=Decimal("10150.50"),
            nav=Decimal("10150.50"),
            margin_rate=Decimal("0.02"),
            position_value=Decimal("25000.00"),
            last_transaction_id="12345",
            created_time=datetime.utcnow()
        )
    
    def test_calculate_equity(self):
        """Test equity calculation"""
        summary = self.create_test_summary()
        calculated_equity = summary.calculate_equity()
        expected_equity = summary.balance + summary.unrealized_pl
        
        assert calculated_equity == expected_equity
        assert calculated_equity == Decimal("10150.50")
    
    def test_calculate_margin_level(self):
        """Test margin level calculation"""
        summary = self.create_test_summary()
        margin_level = summary.calculate_margin_level()
        
        # (equity / margin_used) * 100
        expected_level = (summary.account_equity / summary.margin_used) * 100
        assert margin_level == expected_level
        assert margin_level > 2000  # Should be a healthy margin level
    
    def test_margin_call_detection(self):
        """Test margin call detection"""
        summary = self.create_test_summary()
        
        # Healthy account should not be in margin call
        assert not summary.is_margin_call()
        
        # Simulate margin call situation
        summary.account_equity = Decimal("400.00")  # Less than margin call level
        assert summary.is_margin_call()
    
    def test_margin_closeout_detection(self):
        """Test margin closeout detection"""
        summary = self.create_test_summary()
        
        # Healthy account should not be in margin closeout
        assert not summary.is_margin_closeout()
        
        # Simulate margin closeout situation
        summary.account_equity = Decimal("200.00")  # Less than closeout level
        assert summary.is_margin_closeout()

class TestOandaAccountManager:
    """Test OandaAccountManager functionality"""
    
    @pytest.fixture
    def account_manager(self):
        """Create test account manager"""
        return OandaAccountManager(
            api_key="test-api-key",
            account_id="test-account",
            base_url="https://api-test.oanda.com"
        )
    
    @pytest.fixture
    def mock_session(self):
        """Create mock aiohttp session"""
        session = AsyncMock(spec=aiohttp.ClientSession)
        session.closed = False
        return session
    
    def create_mock_account_response(self):
        """Create mock account API response"""
        return {
            "account": {
                "id": "test-account",
                "currency": "USD",
                "balance": "10000.00",
                "unrealizedPL": "150.50",
                "pl": "-25.75",
                "marginUsed": "500.00",
                "marginAvailable": "9500.00",
                "marginCloseoutPercent": "50.0",
                "marginCallPercent": "100.0",
                "openPositionCount": 3,
                "pendingOrderCount": 2,
                "marginRate": "0.02",
                "financing": "5.25",
                "commission": "2.50",
                "dividendAdjustment": "0.00",
                "NAV": "10150.50",
                "positionValue": "25000.00",
                "lastTransactionID": "12345",
                "createdTime": "2024-01-01T12:00:00.000000Z"
            }
        }
    
    @pytest.mark.asyncio
    async def test_initialization(self, account_manager):
        """Test account manager initialization"""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            await account_manager.initialize()
            
            assert account_manager.session is not None
            assert account_manager.metrics['api_calls'] == 0
            assert account_manager.metrics['errors'] == 0
    
    @pytest.mark.asyncio
    async def test_get_account_summary_success(self, account_manager, mock_session):
        """Test successful account summary retrieval"""
        account_manager.session = mock_session
        
        # Mock API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = self.create_mock_account_response()
        
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        # Test
        summary = await account_manager.get_account_summary(use_cache=False)
        
        # Assertions
        assert isinstance(summary, AccountSummary)
        assert summary.account_id == "test-account"
        assert summary.currency == AccountCurrency.USD
        assert summary.balance == Decimal("10000.00")
        assert summary.unrealized_pl == Decimal("150.50")
        assert summary.open_position_count == 3
        assert account_manager.metrics['api_calls'] == 1
        assert account_manager.metrics['cache_misses'] == 1
    
    @pytest.mark.asyncio
    async def test_get_account_summary_api_error(self, account_manager, mock_session):
        """Test account summary retrieval with API error"""
        account_manager.session = mock_session
        
        # Mock API error response
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.text.return_value = "Bad Request"
        
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        # Test
        with pytest.raises(Exception) as exc_info:
            await account_manager.get_account_summary(use_cache=False)
        
        assert "API error 400" in str(exc_info.value)
        assert account_manager.metrics['errors'] == 1
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, account_manager, mock_session):
        """Test caching functionality"""
        account_manager.session = mock_session
        
        # Mock API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = self.create_mock_account_response()
        
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        # First call - should hit API
        summary1 = await account_manager.get_account_summary(use_cache=True)
        assert account_manager.metrics['api_calls'] == 1
        assert account_manager.metrics['cache_misses'] == 1
        assert account_manager.metrics['cache_hits'] == 0
        
        # Second call - should hit cache
        summary2 = await account_manager.get_account_summary(use_cache=True)
        assert account_manager.metrics['api_calls'] == 1  # No additional API call
        assert account_manager.metrics['cache_hits'] == 1
        
        # Both summaries should be identical
        assert summary1.account_id == summary2.account_id
        assert summary1.balance == summary2.balance
    
    @pytest.mark.asyncio
    async def test_get_open_positions(self, account_manager, mock_session):
        """Test getting open positions"""
        account_manager.session = mock_session
        
        # Mock positions response
        positions_response = {
            "positions": [
                {
                    "instrument": "EUR_USD",
                    "long": {
                        "units": "1000",
                        "averagePrice": "1.1000",
                        "unrealizedPL": "10.50",
                        "pl": "5.25",
                        "marginUsed": "22.00",
                        "financing": "0.50",
                        "dividendAdjustment": "0.00",
                        "tradeIDs": ["123", "124"]
                    },
                    "short": {
                        "units": "0"
                    }
                },
                {
                    "instrument": "GBP_USD",
                    "long": {
                        "units": "0"
                    },
                    "short": {
                        "units": "-500",
                        "averagePrice": "1.2500",
                        "unrealizedPL": "-5.25",
                        "pl": "2.75",
                        "marginUsed": "12.50",
                        "financing": "-0.25",
                        "dividendAdjustment": "0.00",
                        "tradeIDs": ["125"]
                    }
                }
            ]
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = positions_response
        
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        # Test
        positions = await account_manager.get_open_positions()
        
        # Assertions
        assert len(positions) == 2
        
        # Check long position
        long_pos = positions[0]
        assert long_pos.instrument == "EUR_USD"
        assert long_pos.side == "buy"
        assert long_pos.units == Decimal("1000")
        assert long_pos.unrealized_pl == Decimal("10.50")
        
        # Check short position
        short_pos = positions[1]
        assert short_pos.instrument == "GBP_USD" 
        assert short_pos.side == "sell"
        assert short_pos.units == Decimal("500")  # Should be absolute value
        assert short_pos.unrealized_pl == Decimal("-5.25")
    
    @pytest.mark.asyncio
    async def test_get_pending_orders(self, account_manager, mock_session):
        """Test getting pending orders"""
        account_manager.session = mock_session
        
        # Mock orders response
        orders_response = {
            "orders": [
                {
                    "id": "order-123",
                    "instrument": "EUR_USD",
                    "units": "1000",
                    "type": "LIMIT",
                    "price": "1.1050",
                    "timeInForce": "GTC",
                    "triggerCondition": "DEFAULT",
                    "takeProfitOnFill": {
                        "price": "1.1100"
                    },
                    "stopLossOnFill": {
                        "price": "1.1000"
                    }
                },
                {
                    "id": "order-124",
                    "instrument": "GBP_USD",
                    "units": "-500",
                    "type": "STOP",
                    "price": "1.2400",
                    "timeInForce": "GTD",
                    "gtdTime": "2024-12-31T23:59:59.000000Z",
                    "triggerCondition": "BID"
                }
            ]
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = orders_response
        
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        # Test
        orders = await account_manager.get_pending_orders()
        
        # Assertions
        assert len(orders) == 2
        
        # Check limit order
        limit_order = orders[0]
        assert limit_order.order_id == "order-123"
        assert limit_order.instrument == "EUR_USD"
        assert limit_order.side == "buy"
        assert limit_order.type == "LIMIT"
        assert limit_order.price == Decimal("1.1050")
        assert limit_order.take_profit_price == Decimal("1.1100")
        assert limit_order.stop_loss_price == Decimal("1.1000")
        
        # Check stop order
        stop_order = orders[1]
        assert stop_order.order_id == "order-124"
        assert stop_order.side == "sell"
        assert stop_order.type == "STOP"
        assert stop_order.expire_time is not None
    
    @pytest.mark.asyncio
    async def test_calculate_total_equity(self, account_manager, mock_session):
        """Test total equity calculation"""
        account_manager.session = mock_session
        
        # Mock API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = self.create_mock_account_response()
        
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        # Test
        equity = await account_manager.calculate_total_equity()
        
        # Should equal balance + unrealized P&L
        assert equity == Decimal("10150.50")
    
    @pytest.mark.asyncio
    async def test_get_margin_status(self, account_manager, mock_session):
        """Test margin status retrieval"""
        account_manager.session = mock_session
        
        # Mock API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = self.create_mock_account_response()
        
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        # Test
        margin_status = await account_manager.get_margin_status()
        
        # Assertions
        assert 'margin_used' in margin_status
        assert 'margin_available' in margin_status
        assert 'margin_level' in margin_status
        assert 'margin_call' in margin_status
        assert 'margin_closeout' in margin_status
        assert 'free_margin' in margin_status
        assert 'leverage' in margin_status
        
        assert margin_status['margin_used'] == 500.0
        assert margin_status['margin_available'] == 9500.0
        assert margin_status['leverage'] == 50
        assert not margin_status['margin_call']  # Healthy account
        assert not margin_status['margin_closeout']  # Healthy account
    
    @pytest.mark.asyncio
    async def test_close(self, account_manager, mock_session):
        """Test account manager cleanup"""
        account_manager.session = mock_session
        
        await account_manager.close()
        
        mock_session.close.assert_called_once()
        assert len(account_manager.cache.cache) == 0

class TestPositionSummary:
    """Test PositionSummary functionality"""
    
    def test_calculate_pips_eur_usd(self):
        """Test pip calculation for EUR/USD"""
        position = PositionSummary(
            instrument="EUR_USD",
            units=Decimal("1000"),
            side="buy",
            average_price=Decimal("1.1000"),
            current_price=Decimal("1.1010"),
            unrealized_pl=Decimal("10.00"),
            realized_pl=Decimal("0.00"),
            margin_used=Decimal("22.00"),
            financing=Decimal("0.50"),
            dividend_adjustment=Decimal("0.00"),
            trade_ids=["123"]
        )
        
        pips = position.calculate_pips()
        
        # (1.1010 - 1.1000) / 0.0001 = 1.0 pip for buy position
        assert pips == Decimal("1.0")
    
    def test_calculate_pips_usd_jpy(self):
        """Test pip calculation for USD/JPY"""
        position = PositionSummary(
            instrument="USD_JPY",
            units=Decimal("1000"),
            side="sell",
            average_price=Decimal("110.00"),
            current_price=Decimal("109.95"),
            unrealized_pl=Decimal("50.00"),
            realized_pl=Decimal("0.00"),
            margin_used=Decimal("22.00"),
            financing=Decimal("0.25"),
            dividend_adjustment=Decimal("0.00"),
            trade_ids=["124"]
        )
        
        pips = position.calculate_pips()
        
        # For sell position, price goes down = profit
        # (110.00 - 109.95) / 0.01 = 5.0 pips for sell position
        assert pips == Decimal("5.0")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])