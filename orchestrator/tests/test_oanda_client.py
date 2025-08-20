"""
Tests for OANDA Client
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from decimal import Decimal

from app.oanda_client import (
    OandaClient, OandaAccount, OandaPosition, 
    OandaTrade, OandaOrder
)
from app.models import TradeSignal, TradeResult
from app.exceptions import OandaException, TimeoutException


class TestOandaModels:
    """Test OANDA data models"""
    
    def test_oanda_account_creation(self):
        """Test creating OandaAccount"""
        account = OandaAccount(
            account_id="test_123",
            balance=100000.0,
            unrealized_pnl=250.0,
            margin_used=5000.0,
            margin_available=95000.0,
            open_trade_count=3,
            currency="USD"
        )
        
        assert account.account_id == "test_123"
        assert account.balance == 100000.0
        assert account.unrealized_pnl == 250.0
        assert account.open_trade_count == 3
    
    def test_oanda_position_creation(self):
        """Test creating OandaPosition"""
        position = OandaPosition(
            instrument="EUR_USD",
            units=1000.0,
            average_price=1.0500,
            unrealized_pnl=25.0,
            margin_used=250.0
        )
        
        assert position.instrument == "EUR_USD"
        assert position.units == 1000.0
        assert position.average_price == 1.0500
    
    def test_oanda_trade_creation(self):
        """Test creating OandaTrade"""
        trade = OandaTrade(
            trade_id="12345",
            instrument="GBP_USD",
            units=2000.0,
            price=1.2500,
            unrealized_pnl=-15.0,
            open_time=datetime.utcnow()
        )
        
        assert trade.trade_id == "12345"
        assert trade.instrument == "GBP_USD"
        assert trade.units == 2000.0
        assert trade.unrealized_pnl == -15.0


class TestOandaClient:
    """Test OandaClient functionality"""
    
    @pytest.fixture
    async def oanda_client(self, test_settings, mock_httpx_client):
        """Create OandaClient instance for testing"""
        with patch('app.oanda_client.get_settings', return_value=test_settings):
            with patch('app.oanda_client.httpx.AsyncClient', return_value=mock_httpx_client):
                client = OandaClient()
                yield client
                await client.close()
    
    @pytest.mark.asyncio
    async def test_oanda_client_initialization(self, oanda_client, test_settings):
        """Test OandaClient initialization"""
        assert oanda_client.base_url == test_settings.oanda_api_url
        assert oanda_client.client is not None
    
    @pytest.mark.asyncio
    async def test_get_account_info_success(self, oanda_client, mock_httpx_client, mock_oanda_account_data):
        """Test successfully getting account info"""
        # Mock successful response
        response = Mock()
        response.status_code = 200
        response.json.return_value = mock_oanda_account_data
        mock_httpx_client.get.return_value = response
        
        account = await oanda_client.get_account_info("test_account_123")
        
        assert isinstance(account, OandaAccount)
        assert account.account_id == "test_account_123"
        assert account.balance == 99935.05
        assert account.unrealized_pnl == 125.50
        assert account.open_trade_count == 2
    
    @pytest.mark.asyncio
    async def test_get_account_info_failure(self, oanda_client, mock_httpx_client):
        """Test account info request failure"""
        response = Mock()
        response.status_code = 404
        mock_httpx_client.get.return_value = response
        
        with pytest.raises(OandaException) as excinfo:
            await oanda_client.get_account_info("invalid_account")
        
        assert "Failed to get account info" in str(excinfo.value)
    
    @pytest.mark.asyncio
    async def test_get_account_info_timeout(self, oanda_client, mock_httpx_client):
        """Test account info request timeout"""
        import httpx
        mock_httpx_client.get.side_effect = httpx.TimeoutException("Request timed out")
        
        with pytest.raises(TimeoutException) as excinfo:
            await oanda_client.get_account_info("test_account")
        
        assert "get_account_info" in str(excinfo.value)
    
    @pytest.mark.asyncio
    async def test_get_all_accounts_info(self, oanda_client, mock_httpx_client, mock_oanda_account_data, test_settings):
        """Test getting info for all accounts"""
        response = Mock()
        response.status_code = 200
        response.json.return_value = mock_oanda_account_data
        mock_httpx_client.get.return_value = response
        
        accounts = await oanda_client.get_all_accounts_info()
        
        # Should get info for each account in settings
        assert len(accounts) == len(test_settings.account_ids_list)
        for account_id in test_settings.account_ids_list:
            assert account_id in accounts
            assert isinstance(accounts[account_id], OandaAccount)
    
    @pytest.mark.asyncio
    async def test_get_positions_success(self, oanda_client, mock_httpx_client, mock_oanda_positions_data):
        """Test successfully getting positions"""
        response = Mock()
        response.status_code = 200
        response.json.return_value = mock_oanda_positions_data
        mock_httpx_client.get.return_value = response
        
        positions = await oanda_client.get_positions("test_account")
        
        assert len(positions) == 1
        assert isinstance(positions[0], OandaPosition)
        assert positions[0].instrument == "EUR_USD"
        assert positions[0].units == 1000.0
        assert positions[0].unrealized_pnl == 50.0
    
    @pytest.mark.asyncio
    async def test_get_positions_empty(self, oanda_client, mock_httpx_client):
        """Test getting positions when none exist"""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"positions": []}
        mock_httpx_client.get.return_value = response
        
        positions = await oanda_client.get_positions("test_account")
        
        assert positions == []
    
    @pytest.mark.asyncio
    async def test_get_trades_success(self, oanda_client, mock_httpx_client, mock_oanda_trades_data):
        """Test successfully getting trades"""
        response = Mock()
        response.status_code = 200
        response.json.return_value = mock_oanda_trades_data
        mock_httpx_client.get.return_value = response
        
        trades = await oanda_client.get_trades("test_account")
        
        assert len(trades) == 1
        assert isinstance(trades[0], OandaTrade)
        assert trades[0].trade_id == "12345"
        assert trades[0].instrument == "EUR_USD"
        assert trades[0].units == 1000.0
    
    @pytest.mark.asyncio
    async def test_place_market_order_success(self, oanda_client, mock_httpx_client):
        """Test successfully placing a market order"""
        response = Mock()
        response.status_code = 201
        response.json.return_value = {
            "orderFillTransaction": {
                "id": "54321",
                "price": "1.0505",
                "units": "1000",
                "tradeOpened": {"tradeID": "67890"},
                "commission": "2.50",
                "financing": "0.25"
            }
        }
        mock_httpx_client.post.return_value = response
        
        result = await oanda_client.place_market_order(
            "test_account",
            "EUR_USD",
            1000.0,
            stop_loss=1.0450,
            take_profit=1.0600
        )
        
        assert result["orderFillTransaction"]["id"] == "54321"
        assert result["orderFillTransaction"]["tradeOpened"]["tradeID"] == "67890"
    
    @pytest.mark.asyncio
    async def test_place_market_order_failure(self, oanda_client, mock_httpx_client):
        """Test market order placement failure"""
        response = Mock()
        response.status_code = 400
        response.json.return_value = {
            "errorMessage": "Insufficient margin"
        }
        mock_httpx_client.post.return_value = response
        
        with pytest.raises(OandaException) as excinfo:
            await oanda_client.place_market_order(
                "test_account",
                "EUR_USD",
                10000.0
            )
        
        assert "Insufficient margin" in str(excinfo.value)
    
    @pytest.mark.asyncio
    async def test_close_trade_success(self, oanda_client, mock_httpx_client):
        """Test successfully closing a trade"""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "orderFillTransaction": {
                "id": "98765",
                "price": "1.0510",
                "pl": "10.00"
            }
        }
        mock_httpx_client.put.return_value = response
        
        result = await oanda_client.close_trade("test_account", "12345")
        
        assert result["orderFillTransaction"]["id"] == "98765"
        assert result["orderFillTransaction"]["pl"] == "10.00"
    
    @pytest.mark.asyncio
    async def test_close_trade_partial(self, oanda_client, mock_httpx_client):
        """Test partially closing a trade"""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "orderFillTransaction": {
                "id": "98765",
                "units": "500"
            }
        }
        mock_httpx_client.put.return_value = response
        
        result = await oanda_client.close_trade("test_account", "12345", units=500.0)
        
        assert result["orderFillTransaction"]["units"] == "500"
    
    @pytest.mark.asyncio
    async def test_close_all_positions(self, oanda_client, mock_httpx_client):
        """Test closing all positions"""
        # Mock getting positions
        positions_response = Mock()
        positions_response.status_code = 200
        positions_response.json.return_value = {
            "positions": [
                {
                    "instrument": "EUR_USD",
                    "long": {"units": "1000", "averagePrice": "1.0500"},
                    "short": {"units": "0", "averagePrice": "0"},
                    "unrealizedPL": "50.00",
                    "marginUsed": "250.00"
                },
                {
                    "instrument": "GBP_USD",
                    "long": {"units": "0", "averagePrice": "0"},
                    "short": {"units": "-2000", "averagePrice": "1.2500"},
                    "unrealizedPL": "-25.00",
                    "marginUsed": "500.00"
                }
            ]
        }
        
        # Mock closing positions
        close_response = Mock()
        close_response.status_code = 201
        close_response.json.return_value = {"orderFillTransaction": {"id": "12345"}}
        
        mock_httpx_client.get.return_value = positions_response
        mock_httpx_client.post.return_value = close_response
        
        results = await oanda_client.close_all_positions("test_account")
        
        assert len(results) == 2
        assert all("orderFillTransaction" in r for r in results)
    
    @pytest.mark.asyncio
    async def test_get_current_price(self, oanda_client, mock_httpx_client):
        """Test getting current price"""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "candles": [
                {
                    "bid": {"c": "1.0495"},
                    "ask": {"c": "1.0505"}
                }
            ]
        }
        mock_httpx_client.get.return_value = response
        
        prices = await oanda_client.get_current_price("EUR_USD")
        
        assert prices["bid"] == 1.0495
        assert prices["ask"] == 1.0505
        assert prices["mid"] == 1.0500
    
    @pytest.mark.asyncio
    async def test_execute_trade_signal_success(self, oanda_client, mock_httpx_client, sample_trade_signal):
        """Test successfully executing a trade signal"""
        # Mock account info
        account_response = Mock()
        account_response.status_code = 200
        account_response.json.return_value = {
            "account": {
                "id": "test_account",
                "balance": "100000.00",
                "currency": "USD"
            }
        }
        
        # Mock price data
        price_response = Mock()
        price_response.status_code = 200
        price_response.json.return_value = {
            "candles": [{"bid": {"c": "1.0495"}, "ask": {"c": "1.0505"}}]
        }
        
        # Mock order execution
        order_response = Mock()
        order_response.status_code = 201
        order_response.json.return_value = {
            "orderFillTransaction": {
                "id": "12345",
                "price": "1.0505",
                "units": "1000",
                "tradeOpened": {"tradeID": "67890"},
                "commission": "2.50",
                "financing": "0.25"
            }
        }
        
        # Set up mock responses in sequence
        mock_httpx_client.get.side_effect = [account_response, price_response]
        mock_httpx_client.post.return_value = order_response
        
        result = await oanda_client.execute_trade_signal("test_account", sample_trade_signal)
        
        assert isinstance(result, TradeResult)
        assert result.success is True
        assert result.trade_id == "67890"
        assert result.executed_price == 1.0505
        assert result.executed_units == 1000.0
    
    @pytest.mark.asyncio
    async def test_execute_trade_signal_failure(self, oanda_client, mock_httpx_client, sample_trade_signal):
        """Test trade signal execution failure"""
        # Mock account info failure
        mock_httpx_client.get.side_effect = Exception("Account request failed")
        
        result = await oanda_client.execute_trade_signal("test_account", sample_trade_signal)
        
        assert isinstance(result, TradeResult)
        assert result.success is False
        assert "Account request failed" in result.message
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, oanda_client, mock_httpx_client):
        """Test successful health check"""
        response = Mock()
        response.status_code = 200
        mock_httpx_client.get.return_value = response
        
        is_healthy = await oanda_client.health_check()
        
        assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, oanda_client, mock_httpx_client):
        """Test failed health check"""
        response = Mock()
        response.status_code = 500
        mock_httpx_client.get.return_value = response
        
        is_healthy = await oanda_client.health_check()
        
        assert is_healthy is False


class TestOandaClientIntegration:
    """Integration tests for OANDA client"""
    
    @pytest.mark.asyncio
    async def test_full_trade_lifecycle(self, test_settings, mock_httpx_client):
        """Test full trade lifecycle: signal -> execution -> close"""
        with patch('app.oanda_client.get_settings', return_value=test_settings):
            with patch('app.oanda_client.httpx.AsyncClient', return_value=mock_httpx_client):
                client = OandaClient()
                
                try:
                    # Create signal
                    signal = TradeSignal(
                        id="test_signal",
                        instrument="EUR_USD",
                        direction="long",
                        confidence=0.85,
                        stop_loss=1.0450,
                        take_profit=1.0600
                    )
                    
                    # Mock successful execution flow
                    account_response = Mock()
                    account_response.status_code = 200
                    account_response.json.return_value = {
                        "account": {"id": "test", "balance": "100000.00"}
                    }
                    
                    price_response = Mock()
                    price_response.status_code = 200
                    price_response.json.return_value = {
                        "candles": [{"bid": {"c": "1.0495"}, "ask": {"c": "1.0505"}}]
                    }
                    
                    order_response = Mock()
                    order_response.status_code = 201
                    order_response.json.return_value = {
                        "orderFillTransaction": {
                            "id": "12345",
                            "price": "1.0505",
                            "units": "1000",
                            "tradeOpened": {"tradeID": "67890"},
                            "commission": "2.50"
                        }
                    }
                    
                    close_response = Mock()
                    close_response.status_code = 200
                    close_response.json.return_value = {
                        "orderFillTransaction": {
                            "id": "54321",
                            "pl": "50.00"
                        }
                    }
                    
                    mock_httpx_client.get.side_effect = [account_response, price_response]
                    mock_httpx_client.post.return_value = order_response
                    mock_httpx_client.put.return_value = close_response
                    
                    # Execute trade
                    result = await client.execute_trade_signal("test_account", signal)
                    assert result.success is True
                    assert result.trade_id == "67890"
                    
                    # Close trade
                    close_result = await client.close_trade("test_account", "67890")
                    assert close_result["orderFillTransaction"]["pl"] == "50.00"
                    
                finally:
                    await client.close()