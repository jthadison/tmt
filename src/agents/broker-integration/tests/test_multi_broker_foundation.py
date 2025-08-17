"""
Comprehensive tests for Multi-Broker Support Foundation
Story 8.10 - Test Suite
"""
import pytest
import asyncio
import tempfile
import json
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path

try:
    # Try relative imports first (for when running within package)
    from ..broker_adapter import (
        BrokerAdapter, BrokerCapability, OrderType, OrderSide, TimeInForce,
        UnifiedOrder, UnifiedPosition, UnifiedAccountSummary, OrderResult, PriceTick, BrokerInfo
    )
    from ..unified_errors import (
        StandardBrokerError, StandardErrorCode, ErrorSeverity, ErrorCategory, ErrorContext,
        ErrorCodeMapper, error_mapper, map_broker_error
    )
    from ..broker_factory import (
        BrokerFactory, BrokerRegistration, BrokerInstance, BrokerStatus,
        UnsupportedBrokerError, BrokerAuthenticationError, BrokerConfigurationError
    )
    from ..broker_config import (
        ConfigurationManager, BrokerConfiguration, BrokerCredentials, BrokerEndpoints,
        BrokerLimits, BrokerSettings, ConfigEnvironment
    )
    from ..capability_discovery import (
        CapabilityDiscoveryEngine, CapabilityTestResult, CapabilityTestType, BrokerCapabilityProfile,
        InstrumentInfo
    )
    from ..ab_testing_framework import (
        BrokerABTestingFramework, ABTestConfig, TrafficSplit, RoutingStrategy, ABTestStatus,
        OrderExecution, MetricType as ABMetricType
    )
    from ..performance_metrics import (
        PerformanceMetricsCollector, BrokerBenchmark, BrokerComparison, ComparisonPeriod,
        BenchmarkType, MetricSnapshot
    )
except ImportError:
    # Fall back to absolute imports (for when running tests from project root)
    import sys
    from pathlib import Path
    # Add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from broker_adapter import (
        BrokerAdapter, BrokerCapability, OrderType, OrderSide, TimeInForce,
        UnifiedOrder, UnifiedPosition, UnifiedAccountSummary, OrderResult, PriceTick, BrokerInfo
    )
    from unified_errors import (
        StandardBrokerError, StandardErrorCode, ErrorSeverity, ErrorCategory, ErrorContext,
        ErrorCodeMapper, error_mapper, map_broker_error
    )
    from broker_factory import (
        BrokerFactory, BrokerRegistration, BrokerInstance, BrokerStatus,
        UnsupportedBrokerError, BrokerAuthenticationError, BrokerConfigurationError
    )
    from broker_config import (
        ConfigurationManager, BrokerConfiguration, BrokerCredentials, BrokerEndpoints,
        BrokerLimits, BrokerSettings, ConfigEnvironment
    )
    from capability_discovery import (
        CapabilityDiscoveryEngine, CapabilityTestResult, CapabilityTestType, BrokerCapabilityProfile,
        InstrumentInfo
    )
    from ab_testing_framework import (
        BrokerABTestingFramework, ABTestConfig, TrafficSplit, RoutingStrategy, ABTestStatus,
        OrderExecution, MetricType as ABMetricType
    )
    from performance_metrics import (
        PerformanceMetricsCollector, BrokerBenchmark, BrokerComparison, ComparisonPeriod,
        BenchmarkType, MetricSnapshot
    )


class MockBrokerAdapter(BrokerAdapter):
    """Mock broker adapter for testing"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._broker_name = config.get('broker_name', 'mock_broker')
        self._capabilities = {
            BrokerCapability.MARKET_ORDERS,
            BrokerCapability.LIMIT_ORDERS,
            BrokerCapability.REAL_TIME_STREAMING,
            BrokerCapability.FRACTIONAL_UNITS
        }
        self._supported_instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY']
        self._supported_order_types = [OrderType.MARKET, OrderType.LIMIT]
        self._health_status = {'status': 'healthy'}
        
    @property
    def broker_name(self) -> str:
        return self._broker_name
        
    @property
    def broker_display_name(self) -> str:
        return f"Mock {self._broker_name.title()}"
        
    @property
    def api_version(self) -> str:
        return "1.0.0"
        
    @property
    def capabilities(self) -> Set[BrokerCapability]:
        return self._capabilities.copy()
        
    @property
    def supported_instruments(self) -> List[str]:
        return self._supported_instruments.copy()
        
    @property
    def supported_order_types(self) -> List[OrderType]:
        return self._supported_order_types.copy()
        
    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        if credentials.get('api_key') == 'test_key':
            self.is_authenticated = True
            return True
        return False
        
    async def disconnect(self) -> bool:
        self.is_authenticated = False
        return True
        
    async def health_check(self) -> Dict[str, Any]:
        return self._health_status
        
    async def get_broker_info(self) -> BrokerInfo:
        return BrokerInfo(
            name=self.broker_name,
            display_name=self.broker_display_name,
            version=self.api_version,
            capabilities=self.capabilities,
            supported_instruments=self.supported_instruments,
            supported_order_types=self.supported_order_types,
            supported_time_in_force=[TimeInForce.GTC, TimeInForce.IOC],
            minimum_trade_size={'EUR_USD': Decimal('1000')},
            maximum_trade_size={'EUR_USD': Decimal('1000000')},
            commission_structure={'per_trade': 0.05},
            margin_requirements={'EUR_USD': Decimal('0.02')},
            trading_hours={'EUR_USD': {'open': '22:00', 'close': '22:00'}},
            api_rate_limits={'default': 100}
        )
        
    async def get_account_summary(self, account_id: Optional[str] = None) -> UnifiedAccountSummary:
        return UnifiedAccountSummary(
            account_id=account_id or 'test_account',
            account_name='Test Account',
            currency='USD',
            balance=Decimal('10000'),
            available_margin=Decimal('10000'),
            used_margin=Decimal('0')
        )
        
    async def get_accounts(self) -> List[UnifiedAccountSummary]:
        return [await self.get_account_summary()]
        
    async def place_order(self, order: UnifiedOrder) -> OrderResult:
        return OrderResult(
            success=True,
            order_id=f"order_{order.client_order_id}",
            client_order_id=order.client_order_id
        )
        
    async def modify_order(self, order_id: str, modifications: Dict[str, Any]) -> OrderResult:
        return OrderResult(success=True, order_id=order_id)
        
    async def cancel_order(self, order_id: str, reason: Optional[str] = None) -> OrderResult:
        return OrderResult(success=True, order_id=order_id)
        
    async def get_order(self, order_id: str) -> Optional[UnifiedOrder]:
        return None
        
    async def get_orders(self, **kwargs) -> List[UnifiedOrder]:
        return []
        
    async def get_position(self, instrument: str, account_id: Optional[str] = None) -> Optional[UnifiedPosition]:
        return None
        
    async def get_positions(self, account_id: Optional[str] = None) -> List[UnifiedPosition]:
        return []
        
    async def close_position(self, instrument: str, units: Optional[Decimal] = None, 
                           account_id: Optional[str] = None) -> OrderResult:
        return OrderResult(success=True)
        
    async def get_current_price(self, instrument: str) -> Optional[PriceTick]:
        return PriceTick(
            instrument=instrument,
            bid=Decimal('1.1000'),
            ask=Decimal('1.1001'),
            timestamp=datetime.now(timezone.utc)
        )
        
    async def get_current_prices(self, instruments: List[str]) -> Dict[str, PriceTick]:
        return {
            instrument: await self.get_current_price(instrument)
            for instrument in instruments
        }
        
    async def stream_prices(self, instruments: List[str]):
        for instrument in instruments:
            yield await self.get_current_price(instrument)
            
    async def get_historical_data(self, instrument: str, granularity: str, **kwargs) -> List[Dict[str, Any]]:
        return []
        
    async def get_transactions(self, **kwargs) -> List[Dict[str, Any]]:
        return []
        
    def map_error(self, broker_error: Exception) -> StandardBrokerError:
        return StandardBrokerError(
            error_code=StandardErrorCode.UNKNOWN_ERROR,
            message=str(broker_error)
        )


@pytest.fixture
def mock_adapter():
    """Create mock broker adapter"""
    return MockBrokerAdapter({'broker_name': 'test_broker'})


@pytest.fixture
def broker_factory():
    """Create broker factory"""
    return BrokerFactory()


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def config_manager(temp_config_dir):
    """Create configuration manager with temp directory"""
    return ConfigurationManager(temp_config_dir)


class TestBrokerAdapter:
    """Test broker adapter interface"""
    
    def test_adapter_properties(self, mock_adapter):
        """Test adapter basic properties"""
        assert mock_adapter.broker_name == 'test_broker'
        assert mock_adapter.broker_display_name == 'Mock Test_Broker'
        assert mock_adapter.api_version == '1.0.0'
        assert BrokerCapability.MARKET_ORDERS in mock_adapter.capabilities
        assert 'EUR_USD' in mock_adapter.supported_instruments
        assert OrderType.MARKET in mock_adapter.supported_order_types
        
    @pytest.mark.asyncio
    async def test_authentication(self, mock_adapter):
        """Test broker authentication"""
        # Valid credentials
        result = await mock_adapter.authenticate({'api_key': 'test_key'})
        assert result is True
        assert mock_adapter.is_authenticated is True
        
        # Invalid credentials
        result = await mock_adapter.authenticate({'api_key': 'invalid'})
        assert result is False
        
    @pytest.mark.asyncio
    async def test_health_check(self, mock_adapter):
        """Test health check functionality"""
        health = await mock_adapter.health_check()
        assert health['status'] == 'healthy'
        
    @pytest.mark.asyncio
    async def test_order_validation(self, mock_adapter):
        """Test order validation"""
        valid_order = UnifiedOrder(
            order_id='test_order',
            client_order_id='client_123',
            instrument='EUR_USD',
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal('1000')
        )
        
        errors = mock_adapter.validate_order(valid_order)
        assert len(errors) == 0
        
        # Invalid order (unsupported instrument)
        invalid_order = UnifiedOrder(
            order_id='test_order',
            client_order_id='client_123',
            instrument='INVALID_PAIR',
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal('1000')
        )
        
        errors = mock_adapter.validate_order(invalid_order)
        assert len(errors) > 0
        assert any('not supported' in error for error in errors)
        
    @pytest.mark.asyncio
    async def test_order_operations(self, mock_adapter):
        """Test order placement and management"""
        order = UnifiedOrder(
            order_id='test_order',
            client_order_id='client_123',
            instrument='EUR_USD',
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal('1000')
        )
        
        # Place order
        result = await mock_adapter.place_order(order)
        assert result.success is True
        assert result.order_id is not None
        
        # Modify order
        result = await mock_adapter.modify_order('test_order', {'units': 2000})
        assert result.success is True
        
        # Cancel order
        result = await mock_adapter.cancel_order('test_order')
        assert result.success is True
        
    @pytest.mark.asyncio
    async def test_market_data(self, mock_adapter):
        """Test market data operations"""
        # Current price
        price = await mock_adapter.get_current_price('EUR_USD')
        assert price is not None
        assert price.instrument == 'EUR_USD'
        assert price.bid > 0
        assert price.ask > 0
        assert price.ask > price.bid
        
        # Multiple prices
        prices = await mock_adapter.get_current_prices(['EUR_USD', 'GBP_USD'])
        assert len(prices) == 2
        assert 'EUR_USD' in prices
        assert 'GBP_USD' in prices


class TestUnifiedErrors:
    """Test unified error handling system"""
    
    def test_standard_error_creation(self):
        """Test creating standard broker errors"""
        error = StandardBrokerError(
            error_code=StandardErrorCode.AUTHENTICATION_FAILED,
            message="Invalid API key",
            severity=ErrorSeverity.HIGH,
            broker_specific_code="AUTH001"
        )
        
        assert error.error_code == StandardErrorCode.AUTHENTICATION_FAILED
        assert error.severity == ErrorSeverity.HIGH
        assert error.category == ErrorCategory.AUTHENTICATION
        assert error.broker_specific_code == "AUTH001"
        
    def test_error_mapping(self):
        """Test broker error mapping"""
        # Test OANDA error mapping
        error = map_broker_error(
            broker_name='oanda',
            broker_error_code='INSUFFICIENT_MARGIN',
            message='Not enough margin available'
        )
        
        assert error.error_code == StandardErrorCode.INSUFFICIENT_MARGIN
        assert error.broker_specific_code == 'INSUFFICIENT_MARGIN'
        assert error.suggested_action is not None
        
    def test_error_serialization(self):
        """Test error serialization/deserialization"""
        original_error = StandardBrokerError(
            error_code=StandardErrorCode.CONNECTION_ERROR,
            message="Network timeout",
            context=ErrorContext(broker_name='test_broker')
        )
        
        # Serialize to dict
        error_dict = original_error.to_dict()
        assert error_dict['error_code'] == 'CONNECTION_ERROR'
        assert error_dict['message'] == 'Network timeout'
        
        # Deserialize from dict
        restored_error = StandardBrokerError.from_dict(error_dict)
        assert restored_error.error_code == original_error.error_code
        assert restored_error.message == original_error.message
        
    def test_custom_error_mapping(self):
        """Test adding custom error mappings"""
        mapper = ErrorCodeMapper()
        
        # Add custom mapping
        mapper.add_mapping(
            broker_name='custom_broker',
            broker_error_code='CUSTOM_001',
            standard_error_code=StandardErrorCode.RATE_LIMITED,
            severity=ErrorSeverity.MEDIUM,
            suggested_action='Wait and retry'
        )
        
        # Test mapping
        error = mapper.map_error(
            broker_name='custom_broker',
            broker_error_code='CUSTOM_001',
            message='Custom error occurred'
        )
        
        assert error.error_code == StandardErrorCode.RATE_LIMITED
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.suggested_action == 'Wait and retry'


class TestBrokerFactory:
    """Test broker factory pattern"""
    
    def test_adapter_registration(self, broker_factory):
        """Test broker adapter registration"""
        # Register adapter
        broker_factory.register_adapter(
            name='test_broker',
            adapter_class=MockBrokerAdapter,
            display_name='Test Broker',
            version='1.0.0',
            description='Test broker for unit tests'
        )
        
        # Check registration
        registered_brokers = broker_factory.get_registered_brokers()
        assert 'test_broker' in registered_brokers
        
        registration = broker_factory.get_broker_registration('test_broker')
        assert registration is not None
        assert registration.display_name == 'Test Broker'
        assert registration.version == '1.0.0'
        
    @pytest.mark.asyncio
    async def test_adapter_creation(self, broker_factory):
        """Test broker adapter creation"""
        # Register adapter first
        broker_factory.register_adapter('test_broker', MockBrokerAdapter)
        
        # Create adapter instance
        config = {
            'broker_name': 'test_broker',
            'credentials': {'api_key': 'test_key'}
        }
        
        adapter = await broker_factory.create_adapter('test_broker', config)
        assert adapter is not None
        assert adapter.broker_name == 'test_broker'
        assert adapter.is_authenticated is True
        
    @pytest.mark.asyncio
    async def test_unsupported_broker(self, broker_factory):
        """Test handling of unsupported broker"""
        with pytest.raises(UnsupportedBrokerError):
            await broker_factory.create_adapter('unknown_broker', {})
            
    @pytest.mark.asyncio
    async def test_authentication_failure(self, broker_factory):
        """Test authentication failure handling"""
        broker_factory.register_adapter('test_broker', MockBrokerAdapter)
        
        config = {
            'broker_name': 'test_broker',
            'credentials': {'api_key': 'invalid_key'}
        }
        
        with pytest.raises(BrokerAuthenticationError):
            await broker_factory.create_adapter('test_broker', config)
            
    def test_capability_discovery(self, broker_factory):
        """Test capability discovery"""
        broker_factory.register_adapter('test_broker', MockBrokerAdapter)
        
        capabilities = broker_factory.get_broker_capabilities('test_broker')
        assert BrokerCapability.MARKET_ORDERS in capabilities
        assert BrokerCapability.LIMIT_ORDERS in capabilities
        
        # Test brokers with specific capability
        brokers_with_streaming = broker_factory.get_brokers_with_capability(
            BrokerCapability.REAL_TIME_STREAMING
        )
        assert 'test_broker' in brokers_with_streaming
        
    def test_factory_statistics(self, broker_factory):
        """Test factory statistics"""
        broker_factory.register_adapter('test_broker', MockBrokerAdapter)
        
        stats = broker_factory.get_factory_statistics()
        assert stats['registered_brokers'] >= 1
        assert 'test_broker' in stats['registrations']


class TestBrokerConfiguration:
    """Test multi-broker configuration system"""
    
    def test_configuration_creation(self):
        """Test creating broker configuration"""
        credentials = BrokerCredentials(
            api_key='test_key',
            secret_key='test_secret',
            account_id='test_account'
        )
        
        endpoints = BrokerEndpoints(
            base_url='https://api.test.com',
            stream_url='wss://stream.test.com'
        )
        
        config = BrokerConfiguration(
            broker_name='test_broker',
            display_name='Test Broker',
            credentials=credentials,
            endpoints=endpoints
        )
        
        assert config.broker_name == 'test_broker'
        assert config.credentials.api_key == 'test_key'
        assert config.endpoints.base_url == 'https://api.test.com'
        
    def test_configuration_serialization(self):
        """Test configuration serialization"""
        config = BrokerConfiguration(
            broker_name='test_broker',
            display_name='Test Broker'
        )
        
        # Serialize to dict
        config_dict = config.to_dict()
        assert config_dict['broker_name'] == 'test_broker'
        
        # Deserialize from dict
        restored_config = BrokerConfiguration.from_dict(config_dict)
        assert restored_config.broker_name == config.broker_name
        assert restored_config.display_name == config.display_name
        
    def test_configuration_manager(self, config_manager):
        """Test configuration manager"""
        config = BrokerConfiguration(
            broker_name='test_broker',
            display_name='Test Broker',
            enabled=True
        )
        
        # Set configuration
        success = config_manager.set_configuration('test_broker', config)
        assert success is True
        
        # Get configuration
        retrieved_config = config_manager.get_configuration('test_broker')
        assert retrieved_config is not None
        assert retrieved_config.broker_name == 'test_broker'
        
        # Get all configurations
        all_configs = config_manager.get_all_configurations()
        assert 'test_broker' in all_configs
        
        # Get enabled configurations
        enabled_configs = config_manager.get_enabled_configurations()
        assert 'test_broker' in enabled_configs
        
    def test_configuration_validation(self, config_manager):
        """Test configuration validation"""
        # Valid configuration
        valid_config = BrokerConfiguration(
            broker_name='test_broker',
            display_name='Test Broker'
        )
        
        errors = config_manager.validate_configuration(valid_config)
        assert len(errors) == 0
        
        # Invalid configuration (missing broker name)
        invalid_config = BrokerConfiguration(
            broker_name='',
            display_name='Test Broker'
        )
        
        errors = config_manager.validate_configuration(invalid_config)
        assert len(errors) > 0
        assert any('name is required' in error for error in errors)
        
    def test_configuration_backup_restore(self, config_manager, temp_config_dir):
        """Test configuration backup and restore"""
        config = BrokerConfiguration(
            broker_name='test_broker',
            display_name='Test Broker'
        )
        
        config_manager.set_configuration('test_broker', config)
        
        # Create backup
        backup_path = config_manager.backup_configurations()
        assert Path(backup_path).exists()
        
        # Clear configurations
        config_manager.delete_configuration('test_broker', delete_file=False)
        assert config_manager.get_configuration('test_broker') is None
        
        # Restore from backup
        success = config_manager.restore_configurations(backup_path)
        assert success is True
        
        restored_config = config_manager.get_configuration('test_broker')
        assert restored_config is not None
        assert restored_config.broker_name == 'test_broker'


class TestCapabilityDiscovery:
    """Test broker capability discovery"""
    
    @pytest.mark.asyncio
    async def test_static_capability_discovery(self, mock_adapter):
        """Test static capability discovery"""
        discovery_engine = CapabilityDiscoveryEngine()
        
        profile = await discovery_engine.discover_capabilities(
            mock_adapter,
            CapabilityTestType.STATIC
        )
        
        assert profile.broker_name == 'test_broker'
        assert BrokerCapability.MARKET_ORDERS in profile.capabilities
        assert len(profile.supported_instruments) > 0
        assert len(profile.test_results) > 0
        
    @pytest.mark.asyncio
    async def test_dynamic_capability_discovery(self, mock_adapter):
        """Test dynamic capability discovery"""
        discovery_engine = CapabilityDiscoveryEngine()
        
        profile = await discovery_engine.discover_capabilities(
            mock_adapter,
            CapabilityTestType.DYNAMIC
        )
        
        assert profile.broker_name == 'test_broker'
        # Check that dynamic tests were performed
        streaming_tests = [
            test for test in profile.test_results
            if test.capability == BrokerCapability.REAL_TIME_STREAMING
        ]
        assert len(streaming_tests) > 0
        
    def test_capability_comparison(self):
        """Test capability comparison between brokers"""
        discovery_engine = CapabilityDiscoveryEngine()
        
        # Create mock profiles
        profile1 = BrokerCapabilityProfile(
            broker_name='broker1',
            capabilities={BrokerCapability.MARKET_ORDERS, BrokerCapability.LIMIT_ORDERS},
            supported_instruments=[],
            supported_order_types=[OrderType.MARKET, OrderType.LIMIT],
            supported_time_in_force=[],
            minimum_trade_sizes={},
            maximum_trade_sizes={},
            commission_structure={},
            margin_requirements={},
            trading_hours={},
            api_rate_limits={}
        )
        
        profile2 = BrokerCapabilityProfile(
            broker_name='broker2',
            capabilities={BrokerCapability.MARKET_ORDERS, BrokerCapability.TRAILING_STOPS},
            supported_instruments=[],
            supported_order_types=[OrderType.MARKET, OrderType.TRAILING_STOP],
            supported_time_in_force=[],
            minimum_trade_sizes={},
            maximum_trade_sizes={},
            commission_structure={},
            margin_requirements={},
            trading_hours={},
            api_rate_limits={}
        )
        
        discovery_engine.capability_profiles = {
            'broker1': profile1,
            'broker2': profile2
        }
        
        comparison = discovery_engine.compare_broker_capabilities(['broker1', 'broker2'])
        
        assert 'broker1' in comparison['brokers']
        assert 'broker2' in comparison['brokers']
        assert BrokerCapability.MARKET_ORDERS.value in comparison['capabilities']
        assert comparison['capabilities'][BrokerCapability.MARKET_ORDERS.value]['broker1'] is True
        assert comparison['capabilities'][BrokerCapability.MARKET_ORDERS.value]['broker2'] is True


class TestABTestingFramework:
    """Test A/B testing framework"""
    
    def test_ab_test_creation(self):
        """Test A/B test creation"""
        ab_framework = BrokerABTestingFramework()
        
        # Register brokers
        ab_framework.register_broker_adapter('broker1', MockBrokerAdapter({'broker_name': 'broker1'}))
        ab_framework.register_broker_adapter('broker2', MockBrokerAdapter({'broker_name': 'broker2'}))
        
        # Create A/B test
        traffic_splits = [
            TrafficSplit(broker_name='broker1', percentage=60.0),
            TrafficSplit(broker_name='broker2', percentage=40.0)
        ]
        
        test_id = ab_framework.create_ab_test(
            test_name='Speed Test',
            description='Test broker execution speed',
            traffic_splits=traffic_splits,
            duration_hours=24
        )
        
        assert test_id is not None
        assert test_id in ab_framework.active_tests
        
        config = ab_framework.active_tests[test_id]
        assert config.name == 'Speed Test'
        assert len(config.traffic_splits) == 2
        
    @pytest.mark.asyncio
    async def test_order_routing(self):
        """Test order routing in A/B test"""
        ab_framework = BrokerABTestingFramework()
        
        # Register brokers
        ab_framework.register_broker_adapter('broker1', MockBrokerAdapter({'broker_name': 'broker1'}))
        ab_framework.register_broker_adapter('broker2', MockBrokerAdapter({'broker_name': 'broker2'}))
        
        # Create A/B test
        traffic_splits = [
            TrafficSplit(broker_name='broker1', percentage=50.0),
            TrafficSplit(broker_name='broker2', percentage=50.0)
        ]
        
        test_id = ab_framework.create_ab_test(
            test_name='Routing Test',
            description='Test order routing',
            traffic_splits=traffic_splits,
            routing_strategy=RoutingStrategy.HASH_BASED
        )
        
        # Test order routing
        order = UnifiedOrder(
            order_id='test_order',
            client_order_id='client_123',
            instrument='EUR_USD',
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal('1000')
        )
        
        broker = await ab_framework.route_order(order, test_id)
        assert broker in ['broker1', 'broker2']
        
        # Same order should route to same broker (hash-based)
        broker2 = await ab_framework.route_order(order, test_id)
        assert broker == broker2
        
    @pytest.mark.asyncio
    async def test_order_execution_with_test(self):
        """Test order execution through A/B framework"""
        ab_framework = BrokerABTestingFramework()
        
        # Register brokers
        ab_framework.register_broker_adapter('broker1', MockBrokerAdapter({'broker_name': 'broker1'}))
        ab_framework.register_broker_adapter('broker2', MockBrokerAdapter({'broker_name': 'broker2'}))
        
        # Create A/B test
        traffic_splits = [
            TrafficSplit(broker_name='broker1', percentage=100.0)
        ]
        
        test_id = ab_framework.create_ab_test(
            test_name='Execution Test',
            description='Test order execution',
            traffic_splits=traffic_splits
        )
        
        # Execute order
        order = UnifiedOrder(
            order_id='test_order',
            client_order_id='client_123',
            instrument='EUR_USD',
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal('1000')
        )
        
        result = await ab_framework.execute_order_with_test(order, test_id)
        assert result.success is True
        
        # Check execution was recorded
        executions = ab_framework.executions[test_id]
        assert len(executions) == 1
        assert executions[0].broker_name == 'broker1'
        
    def test_ab_test_analysis(self):
        """Test A/B test results analysis"""
        ab_framework = BrokerABTestingFramework()
        
        # Create test with mock data
        test_id = 'test_123'
        config = ABTestConfig(
            test_id=test_id,
            name='Analysis Test',
            description='Test analysis',
            traffic_splits=[
                TrafficSplit(broker_name='broker1', percentage=50.0),
                TrafficSplit(broker_name='broker2', percentage=50.0)
            ],
            routing_strategy=RoutingStrategy.RANDOM,
            start_time=datetime.now(timezone.utc)
        )
        
        ab_framework.active_tests[test_id] = config
        ab_framework.executions[test_id] = []
        
        # Add mock executions
        for i in range(20):
            broker_name = 'broker1' if i % 2 == 0 else 'broker2'
            execution = OrderExecution(
                execution_id=f'exec_{i}',
                test_id=test_id,
                broker_name=broker_name,
                order=UnifiedOrder(
                    order_id=f'order_{i}',
                    client_order_id=f'client_{i}',
                    instrument='EUR_USD',
                    order_type=OrderType.MARKET,
                    side=OrderSide.BUY,
                    units=Decimal('1000')
                ),
                result=OrderResult(success=True),
                execution_time=datetime.now(timezone.utc),
                latency_ms=100 + i * 5,  # Varying latency
                success=True
            )
            ab_framework.executions[test_id].append(execution)
            
        # Analyze results
        results = ab_framework.analyze_test_results(test_id)
        
        assert results.test_id == test_id
        assert results.total_executions == 20
        assert 'broker1' in results.executions_by_broker
        assert 'broker2' in results.executions_by_broker
        assert len(results.metrics) > 0
        assert len(results.recommendations) > 0


class TestPerformanceMetrics:
    """Test performance metrics comparison"""
    
    def test_metrics_collector_registration(self):
        """Test broker registration for metrics collection"""
        collector = PerformanceMetricsCollector()
        adapter = MockBrokerAdapter({'broker_name': 'test_broker'})
        
        collector.register_broker('test_broker', adapter)
        
        assert 'test_broker' in collector.broker_adapters
        assert 'test_broker' in collector.metric_history
        
    @pytest.mark.asyncio
    async def test_benchmark_generation(self):
        """Test broker benchmark generation"""
        collector = PerformanceMetricsCollector()
        adapter = MockBrokerAdapter({'broker_name': 'test_broker'})
        
        collector.register_broker('test_broker', adapter)
        
        # Add some mock metrics
        from performance_metrics import MetricSnapshot, MetricType
        
        timestamp = datetime.now(timezone.utc)
        collector.metric_history['test_broker'] = [
            MetricSnapshot(
                broker_name='test_broker',
                metric_type=MetricType.LATENCY,
                value=150.0,
                timestamp=timestamp,
                sample_count=1
            ),
            MetricSnapshot(
                broker_name='test_broker',
                metric_type=MetricType.SUCCESS_RATE,
                value=0.95,
                timestamp=timestamp,
                sample_count=1
            )
        ]
        
        # Generate benchmark
        benchmark = await collector.generate_broker_benchmark(
            'test_broker',
            ComparisonPeriod.LAST_HOUR
        )
        
        assert benchmark.broker_name == 'test_broker'
        assert benchmark.avg_order_latency > 0
        assert benchmark.overall_performance_score > 0
        
    @pytest.mark.asyncio
    async def test_broker_comparison(self):
        """Test comparing multiple brokers"""
        collector = PerformanceMetricsCollector()
        
        # Register multiple brokers
        for i in range(2):
            broker_name = f'broker{i+1}'
            adapter = MockBrokerAdapter({'broker_name': broker_name})
            collector.register_broker(broker_name, adapter)
            
            # Add mock metrics
            from performance_metrics import MetricSnapshot, MetricType
            
            timestamp = datetime.now(timezone.utc)
            collector.metric_history[broker_name] = [
                MetricSnapshot(
                    broker_name=broker_name,
                    metric_type=MetricType.LATENCY,
                    value=100.0 + i * 50,  # Different latencies
                    timestamp=timestamp,
                    sample_count=1
                )
            ]
            
        # Compare brokers
        comparison = await collector.compare_brokers(
            ['broker1', 'broker2'],
            ComparisonPeriod.LAST_HOUR
        )
        
        assert len(comparison.broker_names) == 2
        assert len(comparison.benchmarks) == 2
        assert len(comparison.rankings) > 0
        assert comparison.winner is not None
        assert len(comparison.recommendations) > 0


@pytest.mark.asyncio
async def test_integration_multi_broker_workflow():
    """Test complete multi-broker workflow integration"""
    # Initialize components
    factory = BrokerFactory()
    config_manager = ConfigurationManager()
    discovery_engine = CapabilityDiscoveryEngine()
    ab_framework = BrokerABTestingFramework()
    metrics_collector = PerformanceMetricsCollector()
    
    # Register brokers
    factory.register_adapter('broker1', MockBrokerAdapter)
    factory.register_adapter('broker2', MockBrokerAdapter)
    
    # Create configurations
    for i in range(2):
        broker_name = f'broker{i+1}'
        config = BrokerConfiguration(
            broker_name=broker_name,
            display_name=f'Broker {i+1}',
            credentials=BrokerCredentials(api_key='test_key'),
            enabled=True
        )
        config_manager.set_configuration(broker_name, config)
        
    # Create adapter instances
    adapters = {}
    for i in range(2):
        broker_name = f'broker{i+1}'
        config = config_manager.get_configuration(broker_name)
        adapter = await factory.create_adapter(broker_name, config.to_dict(include_secrets=True))
        adapters[broker_name] = adapter
        
        # Register for A/B testing and metrics
        ab_framework.register_broker_adapter(broker_name, adapter)
        metrics_collector.register_broker(broker_name, adapter)
        
    # Discover capabilities
    profiles = {}
    for broker_name, adapter in adapters.items():
        profile = await discovery_engine.discover_capabilities(adapter)
        profiles[broker_name] = profile
        
    # Create A/B test
    traffic_splits = [
        TrafficSplit(broker_name='broker1', percentage=60.0),
        TrafficSplit(broker_name='broker2', percentage=40.0)
    ]
    
    test_id = ab_framework.create_ab_test(
        test_name='Integration Test',
        description='Full workflow integration test',
        traffic_splits=traffic_splits
    )
    
    # Execute orders through A/B framework
    for i in range(10):
        order = UnifiedOrder(
            order_id=f'order_{i}',
            client_order_id=f'client_{i}',
            instrument='EUR_USD',
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal('1000')
        )
        
        result = await ab_framework.execute_order_with_test(order, test_id)
        assert result.success is True
        
    # Analyze A/B test results
    test_results = ab_framework.analyze_test_results(test_id)
    assert test_results.total_executions == 10
    assert len(test_results.executions_by_broker) > 0
    
    # Compare broker performance
    comparison = await metrics_collector.compare_brokers(
        ['broker1', 'broker2'],
        ComparisonPeriod.LAST_HOUR
    )
    
    assert len(comparison.benchmarks) == 2
    assert comparison.winner is not None
    
    # Verify capability profiles
    assert len(profiles) == 2
    for profile in profiles.values():
        assert len(profile.capabilities) > 0
        assert len(profile.supported_instruments) > 0
        
    print("✅ Multi-broker foundation integration test completed successfully")


if __name__ == "__main__":
    # Run integration test
    asyncio.run(test_integration_multi_broker_workflow())