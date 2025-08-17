"""
Integration Test Framework for OANDA Practice Account
Story 8.12 - Task 2: Create integration test framework (AC: 2)
"""
import pytest
import asyncio
import os
import logging
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

# Test imports
import sys
from pathlib import Path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from broker_adapter import (
    BrokerAdapter, UnifiedOrder, UnifiedPosition, UnifiedAccountSummary,
    OrderType, OrderSide, OrderState, PositionSide, TimeInForce,
    BrokerCapability, PriceTick, OrderResult
)
from unified_errors import StandardBrokerError, StandardErrorCode, ErrorSeverity
from oanda_auth_handler import OandaAuthHandler, AccountContext, Environment
from credential_manager import OandaCredentialManager

logger = logging.getLogger(__name__)


class OandaIntegrationAdapter(BrokerAdapter):
    """Real OANDA adapter for integration testing with practice account"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._broker_name = "oanda"
        self.api_key = config.get('api_key')
        self.environment = config.get('environment', 'practice')
        self.base_url = self._get_base_url()
        self._session = None
        
    def _get_base_url(self) -> str:
        """Get base URL for OANDA API"""
        if self.environment == 'practice':
            return 'https://api-fxpractice.oanda.com'
        else:
            return 'https://api-fxtrade.oanda.com'
            
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
        return {
            BrokerCapability.MARKET_ORDERS,
            BrokerCapability.LIMIT_ORDERS,
            BrokerCapability.STOP_ORDERS,
            BrokerCapability.STOP_LOSS_ORDERS,
            BrokerCapability.TAKE_PROFIT_ORDERS,
            BrokerCapability.FRACTIONAL_UNITS,
            BrokerCapability.NETTING,
            BrokerCapability.REAL_TIME_STREAMING,
            BrokerCapability.HISTORICAL_DATA
        }
        
    @property
    def supported_instruments(self) -> List[str]:
        return ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CHF", "USD_CAD"]
        
    @property
    def supported_order_types(self) -> List[OrderType]:
        return [
            OrderType.MARKET, OrderType.LIMIT, OrderType.STOP,
            OrderType.STOP_LOSS, OrderType.TAKE_PROFIT
        ]
        
    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        """Authenticate with OANDA API"""
        try:
            import aiohttp
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/v3/accounts/{self.account_id}"
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        self.is_authenticated = True
                        self.connection_status = 'connected'
                        return True
                    else:
                        logger.error(f"Authentication failed: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
            
    async def disconnect(self) -> bool:
        """Disconnect from OANDA API"""
        self.is_authenticated = False
        self.connection_status = 'disconnected'
        if self._session and not self._session.closed:
            await self._session.close()
        return True
        
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        try:
            import aiohttp
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/v3/accounts/{self.account_id}"
                start_time = datetime.now(timezone.utc)
                
                async with session.get(url, headers=headers, timeout=5) as response:
                    end_time = datetime.now(timezone.utc)
                    latency = (end_time - start_time).total_seconds() * 1000
                    
                    return {
                        'status': 'healthy' if response.status == 200 else 'unhealthy',
                        'status_code': response.status,
                        'latency_ms': latency,
                        'timestamp': start_time.isoformat(),
                        'connection_status': self.connection_status
                    }
                    
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'connection_status': 'error'
            }
            
    async def get_broker_info(self):
        """Get broker information - basic implementation"""
        return {
            'name': self.broker_name,
            'display_name': self.broker_display_name,
            'version': self.api_version,
            'environment': self.environment
        }
        
    # Simplified implementations for integration testing
    async def get_account_summary(self, account_id: Optional[str] = None) -> UnifiedAccountSummary:
        """Get account summary from OANDA"""
        try:
            import aiohttp
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            target_account = account_id or self.account_id
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/v3/accounts/{target_account}/summary"
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        account_data = data['account']
                        
                        return UnifiedAccountSummary(
                            account_id=account_data['id'],
                            account_name=f"OANDA {self.environment.title()} Account",
                            currency=account_data['currency'],
                            balance=Decimal(account_data['balance']),
                            available_margin=Decimal(account_data.get('marginAvailable', '0')),
                            used_margin=Decimal(account_data.get('marginUsed', '0')),
                            unrealized_pl=Decimal(account_data.get('unrealizedPL', '0')),
                            nav=Decimal(account_data.get('NAV', account_data['balance'])),
                            position_count=int(account_data.get('openPositionCount', 0)),
                            open_order_count=int(account_data.get('pendingOrderCount', 0))
                        )
                    else:
                        error_text = await response.text()
                        raise StandardBrokerError(
                            error_code=StandardErrorCode.ACCOUNT_NOT_FOUND,
                            message=f"Failed to get account summary: {error_text}"
                        )
                        
        except Exception as e:
            if isinstance(e, StandardBrokerError):
                raise
            raise StandardBrokerError(
                error_code=StandardErrorCode.CONNECTION_ERROR,
                message=f"Error getting account summary: {str(e)}"
            )
            
    async def get_accounts(self) -> List[UnifiedAccountSummary]:
        """Get all accounts"""
        return [await self.get_account_summary()]
        
    async def place_order(self, order: UnifiedOrder) -> OrderResult:
        """Place order with OANDA (simplified for integration testing)"""
        # For integration testing, we'll use a mock implementation
        # In a real scenario, this would make actual API calls
        logger.info(f"Integration test: Placing order {order.order_id} for {order.instrument}")
        
        # Simulate successful order placement
        return OrderResult(
            success=True,
            order_id=f"integration_order_{order.order_id}",
            client_order_id=order.client_order_id,
            order_state=OrderState.FILLED,
            fill_price=Decimal("1.1000"),  # Mock price
            filled_units=order.units,
            transaction_id=f"integration_txn_{order.order_id}"
        )
        
    async def modify_order(self, order_id: str, modifications: Dict[str, Any]) -> OrderResult:
        """Modify order (mock implementation)"""
        return OrderResult(success=True, order_id=order_id)
        
    async def cancel_order(self, order_id: str, reason: Optional[str] = None) -> OrderResult:
        """Cancel order (mock implementation)"""
        return OrderResult(success=True, order_id=order_id)
        
    async def get_order(self, order_id: str) -> Optional[UnifiedOrder]:
        """Get order (mock implementation)"""
        return None
        
    async def get_orders(self, **kwargs) -> List[UnifiedOrder]:
        """Get orders (mock implementation)"""
        return []
        
    async def get_position(self, instrument: str, account_id: Optional[str] = None) -> Optional[UnifiedPosition]:
        """Get position (mock implementation)"""
        return None
        
    async def get_positions(self, account_id: Optional[str] = None) -> List[UnifiedPosition]:
        """Get positions (mock implementation)"""
        return []
        
    async def close_position(self, instrument: str, units: Optional[Decimal] = None, account_id: Optional[str] = None) -> OrderResult:
        """Close position (mock implementation)"""
        return OrderResult(success=True, order_id="close_order")
        
    async def get_current_price(self, instrument: str) -> Optional[PriceTick]:
        """Get current price from OANDA"""
        try:
            import aiohttp
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/v3/accounts/{self.account_id}/pricing"
                params = {'instruments': instrument}
                
                async with session.get(url, headers=headers, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        prices = data.get('prices', [])
                        
                        if prices:
                            price_data = prices[0]
                            return PriceTick(
                                instrument=instrument,
                                bid=Decimal(price_data['bids'][0]['price']),
                                ask=Decimal(price_data['asks'][0]['price']),
                                timestamp=datetime.now(timezone.utc)
                            )
                            
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting price for {instrument}: {e}")
            return None
            
    async def get_current_prices(self, instruments: List[str]) -> Dict[str, PriceTick]:
        """Get current prices for multiple instruments"""
        if not instruments:
            raise ValueError("Instruments list is required and cannot be empty")
            
        prices = {}
        for instrument in instruments:
            price = await self.get_current_price(instrument)
            if price:
                prices[instrument] = price
                
        return prices
        
    async def stream_prices(self, instruments: List[str]):
        """Stream prices (simplified implementation)"""
        for instrument in instruments:
            price = await self.get_current_price(instrument)
            if price:
                yield price
                
    async def get_historical_data(self, **kwargs) -> List[Dict[str, Any]]:
        """Get historical data (mock implementation)"""
        return []
        
    async def get_transactions(self, **kwargs) -> List[Dict[str, Any]]:
        """Get transactions (mock implementation)"""
        return []
        
    def map_error(self, broker_error: Exception) -> StandardBrokerError:
        """Map OANDA error to standard error"""
        return StandardBrokerError(
            error_code=StandardErrorCode.UNKNOWN_ERROR,
            message=str(broker_error)
        )


# Global fixtures for integration tests
@pytest.fixture(scope="session")
def integration_config():
    """Configuration for integration tests"""
    # Check for environment variables first
    api_key = os.getenv('OANDA_PRACTICE_API_KEY')
    account_id = os.getenv('OANDA_PRACTICE_ACCOUNT_ID')
    
    if not api_key or not account_id:
        pytest.skip("OANDA practice account credentials not provided")
        
    return {
        'api_key': api_key,
        'account_id': account_id,
        'environment': 'practice'
    }
    
@pytest.fixture(scope="session")
async def integration_adapter(integration_config):
    """Set up integration adapter for testing"""
    adapter = OandaIntegrationAdapter(integration_config)
    
    # Authenticate
    auth_success = await adapter.authenticate(integration_config)
    if not auth_success:
        pytest.skip("Failed to authenticate with OANDA practice account")
        
    yield adapter
    
    # Cleanup
    await adapter.disconnect()
    
@pytest.fixture
def mock_integration_adapter():
    """Mock integration adapter for tests without real API"""
    config = {
        'api_key': 'mock_key',
        'account_id': 'mock_account',
        'environment': 'practice'
    }
    return OandaIntegrationAdapter(config)


class TestIntegrationBase:
    """Base class for integration tests"""
    pass


class TestIntegrationFramework:
    """Test the integration test framework itself"""
    
    def test_integration_adapter_creation(self, mock_integration_adapter):
        """Test integration adapter can be created"""
        assert mock_integration_adapter.broker_name == "oanda"
        assert mock_integration_adapter.environment == "practice"
        assert not mock_integration_adapter.is_authenticated
        
    def test_integration_adapter_capabilities(self, mock_integration_adapter):
        """Test integration adapter has expected capabilities"""
        capabilities = mock_integration_adapter.capabilities
        assert BrokerCapability.MARKET_ORDERS in capabilities
        assert BrokerCapability.LIMIT_ORDERS in capabilities
        assert BrokerCapability.REAL_TIME_STREAMING in capabilities
        
    def test_integration_adapter_instruments(self, mock_integration_adapter):
        """Test integration adapter supports expected instruments"""
        instruments = mock_integration_adapter.supported_instruments
        assert "EUR_USD" in instruments
        assert "GBP_USD" in instruments
        assert len(instruments) >= 4
        
    @pytest.mark.asyncio
    async def test_health_check_structure(self, mock_integration_adapter):
        """Test health check returns expected structure"""
        health = await mock_integration_adapter.health_check()
        
        assert 'status' in health
        assert 'timestamp' in health
        assert 'connection_status' in health
        assert health['status'] in ['healthy', 'unhealthy']


@pytest.mark.integration
class TestOandaIntegration:
    """Integration tests with real OANDA practice account"""
    
    @pytest.mark.asyncio
    async def test_authentication_success(self, integration_adapter):
        """Test successful authentication with OANDA practice account"""
        assert integration_adapter.is_authenticated
        assert integration_adapter.connection_status == 'connected'
        
    @pytest.mark.asyncio
    async def test_health_check_real_account(self, integration_adapter):
        """Test health check with real OANDA account"""
        health = await integration_adapter.health_check()
        
        assert health['status'] == 'healthy'
        assert health['status_code'] == 200
        assert 'latency_ms' in health
        assert health['latency_ms'] > 0
        assert health['connection_status'] == 'connected'
        
    @pytest.mark.asyncio
    async def test_get_account_summary_real(self, integration_adapter):
        """Test getting account summary from real OANDA account"""
        summary = await integration_adapter.get_account_summary()
        
        assert isinstance(summary, UnifiedAccountSummary)
        assert summary.account_id == integration_adapter.account_id
        assert summary.currency in ['USD', 'EUR', 'GBP']  # Common practice account currencies
        assert isinstance(summary.balance, Decimal)
        assert summary.balance >= 0
        
    @pytest.mark.asyncio
    async def test_get_current_price_real(self, integration_adapter):
        """Test getting current price from real OANDA feed"""
        price = await integration_adapter.get_current_price("EUR_USD")
        
        if price:  # Market might be closed
            assert isinstance(price, PriceTick)
            assert price.instrument == "EUR_USD"
            assert price.bid > 0
            assert price.ask > price.bid
            assert price.spread == price.ask - price.bid
            assert isinstance(price.timestamp, datetime)
            
    @pytest.mark.asyncio
    async def test_get_multiple_prices_real(self, integration_adapter):
        """Test getting multiple prices from real OANDA feed"""
        instruments = ["EUR_USD", "GBP_USD"]
        prices = await integration_adapter.get_current_prices(instruments)
        
        # Prices might not be available if market is closed
        assert isinstance(prices, dict)
        
        for instrument, price in prices.items():
            assert instrument in instruments
            assert isinstance(price, PriceTick)
            assert price.instrument == instrument
            
    @pytest.mark.asyncio
    async def test_broker_info_real(self, integration_adapter):
        """Test getting broker info"""
        info = await integration_adapter.get_broker_info()
        
        assert info['name'] == 'oanda'
        assert info['display_name'] == 'OANDA'
        assert info['version'] == 'v3'
        assert info['environment'] == 'practice'
        
    @pytest.mark.asyncio
    async def test_disconnect_real(self, integration_adapter):
        """Test disconnection from OANDA"""
        result = await integration_adapter.disconnect()
        
        assert result is True
        assert not integration_adapter.is_authenticated
        assert integration_adapter.connection_status == 'disconnected'


@pytest.mark.integration
class TestOrderIntegration:
    """Integration tests for order operations (using mock for safety)"""
    
    @pytest.mark.asyncio
    async def test_place_market_order_integration(self, integration_adapter):
        """Test placing market order in integration environment"""
        order = UnifiedOrder(
            order_id="integration_test_1",
            client_order_id="client_integration_1",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("1")  # Smallest possible size for safety
        )
        
        result = await integration_adapter.place_order(order)
        
        assert result.success is True
        assert result.order_id is not None
        assert result.client_order_id == order.client_order_id
        assert result.transaction_id is not None
        
    @pytest.mark.asyncio
    async def test_place_limit_order_integration(self, integration_adapter):
        """Test placing limit order in integration environment"""
        # Get current price first
        current_price = await integration_adapter.get_current_price("EUR_USD")
        
        if current_price:
            # Place limit order below current bid
            limit_price = current_price.bid - Decimal("0.0100")
            
            order = UnifiedOrder(
                order_id="integration_test_2",
                client_order_id="client_integration_2",
                instrument="EUR_USD",
                order_type=OrderType.LIMIT,
                side=OrderSide.BUY,
                units=Decimal("1"),
                price=limit_price
            )
            
            result = await integration_adapter.place_order(order)
            
            assert result.success is True
            assert result.order_id is not None


class TestIntegrationErrorHandling:
    """Test error handling in integration environment"""
    
    @pytest.mark.asyncio
    async def test_invalid_api_key_error(self):
        """Test handling of invalid API key"""
        config = {
            'api_key': 'invalid_key',
            'account_id': 'invalid_account',
            'environment': 'practice'
        }
        
        adapter = OandaIntegrationAdapter(config)
        auth_result = await adapter.authenticate(config)
        
        assert auth_result is False
        assert not adapter.is_authenticated
        
    @pytest.mark.asyncio
    async def test_invalid_account_error(self, integration_config):
        """Test handling of invalid account ID"""
        invalid_config = integration_config.copy()
        invalid_config['account_id'] = 'invalid_account_id'
        
        adapter = OandaIntegrationAdapter(invalid_config)
        
        with pytest.raises(StandardBrokerError) as exc_info:
            await adapter.get_account_summary("invalid_account_id")
            
        assert exc_info.value.error_code in [
            StandardErrorCode.ACCOUNT_NOT_FOUND,
            StandardErrorCode.CONNECTION_ERROR
        ]
        
    @pytest.mark.asyncio
    async def test_invalid_instrument_price(self, mock_integration_adapter):
        """Test handling of invalid instrument"""
        price = await mock_integration_adapter.get_current_price("INVALID_INSTRUMENT")
        assert price is None


class TestIntegrationPerformance:
    """Basic performance tests for integration"""
    
    @pytest.mark.asyncio
    async def test_health_check_latency(self, integration_adapter):
        """Test that health check completes within reasonable time"""
        import time
        
        start_time = time.perf_counter()
        health = await integration_adapter.health_check()
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        
        assert health['status'] == 'healthy'
        assert latency_ms < 5000  # Should complete within 5 seconds
        
    @pytest.mark.asyncio
    async def test_price_fetch_latency(self, integration_adapter):
        """Test that price fetching completes within reasonable time"""
        import time
        
        start_time = time.perf_counter()
        price = await integration_adapter.get_current_price("EUR_USD")
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        
        # Price might be None if market is closed, but should still be fast
        assert latency_ms < 3000  # Should complete within 3 seconds


class TestIntegrationCleanup:
    """Test cleanup and resource management"""
    
    @pytest.mark.asyncio
    async def test_proper_disconnect(self, mock_integration_adapter):
        """Test proper disconnect and cleanup"""
        # Simulate connection
        mock_integration_adapter.is_authenticated = True
        mock_integration_adapter.connection_status = 'connected'
        
        result = await mock_integration_adapter.disconnect()
        
        assert result is True
        assert not mock_integration_adapter.is_authenticated
        assert mock_integration_adapter.connection_status == 'disconnected'


if __name__ == "__main__":
    # Run integration tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "integration"
    ])