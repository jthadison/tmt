"""
Broker Capability Discovery System
Story 8.10 - Task 5: Build broker capability discovery (AC6)
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from decimal import Decimal
import json

try:
    from .broker_adapter import BrokerAdapter, BrokerCapability, OrderType, TimeInForce, UnifiedOrder, OrderSide
    from .unified_errors import StandardBrokerError, StandardErrorCode, ErrorSeverity
except ImportError:
    from broker_adapter import BrokerAdapter, BrokerCapability, OrderType, TimeInForce, UnifiedOrder, OrderSide
    from unified_errors import StandardBrokerError, StandardErrorCode, ErrorSeverity

logger = logging.getLogger(__name__)


class CapabilityTestType(Enum):
    """Types of capability tests"""
    STATIC = "static"  # Based on broker documentation/configuration
    DYNAMIC = "dynamic"  # Real-time testing with broker API
    SYNTHETIC = "synthetic"  # Test orders that are cancelled immediately


@dataclass
class InstrumentInfo:
    """Information about a tradeable instrument"""
    symbol: str
    name: str
    instrument_type: str  # forex, stock, crypto, commodity, etc.
    base_currency: Optional[str] = None
    quote_currency: Optional[str] = None
    min_trade_size: Optional[Decimal] = None
    max_trade_size: Optional[Decimal] = None
    tick_size: Optional[Decimal] = None
    pip_location: Optional[int] = None
    margin_rate: Optional[Decimal] = None
    trading_hours: Optional[Dict[str, str]] = None
    is_tradeable: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CapabilityTestResult:
    """Result of a capability test"""
    capability: BrokerCapability
    supported: bool
    test_type: CapabilityTestType
    confidence_level: float  # 0.0 to 1.0
    test_details: Dict[str, Any]
    error_message: Optional[str] = None
    test_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    test_duration_ms: Optional[float] = None


@dataclass
class BrokerCapabilityProfile:
    """Complete capability profile for a broker"""
    broker_name: str
    capabilities: Set[BrokerCapability]
    supported_instruments: List[InstrumentInfo]
    supported_order_types: List[OrderType]
    supported_time_in_force: List[TimeInForce]
    minimum_trade_sizes: Dict[str, Decimal]  # instrument -> min size
    maximum_trade_sizes: Dict[str, Decimal]  # instrument -> max size
    commission_structure: Dict[str, Any]
    margin_requirements: Dict[str, Decimal]
    trading_hours: Dict[str, Dict[str, str]]  # instrument -> {open, close}
    api_rate_limits: Dict[str, int]  # endpoint -> requests per second
    test_results: List[CapabilityTestResult] = field(default_factory=list)
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    profile_version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'broker_name': self.broker_name,
            'capabilities': [cap.value for cap in self.capabilities],
            'supported_instruments': [asdict(inst) for inst in self.supported_instruments],
            'supported_order_types': [ot.value for ot in self.supported_order_types],
            'supported_time_in_force': [tif.value for tif in self.supported_time_in_force],
            'minimum_trade_sizes': {k: str(v) for k, v in self.minimum_trade_sizes.items()},
            'maximum_trade_sizes': {k: str(v) for k, v in self.maximum_trade_sizes.items()},
            'commission_structure': self.commission_structure,
            'margin_requirements': {k: str(v) for k, v in self.margin_requirements.items()},
            'trading_hours': self.trading_hours,
            'api_rate_limits': self.api_rate_limits,
            'test_results': [asdict(result) for result in self.test_results],
            'last_updated': self.last_updated.isoformat(),
            'profile_version': self.profile_version,
            'metadata': self.metadata
        }


class CapabilityDiscoveryEngine:
    """Engine for discovering and testing broker capabilities"""
    
    def __init__(self):
        self.capability_profiles: Dict[str, BrokerCapabilityProfile] = {}
        self.test_instruments = [
            'EUR_USD', 'GBP_USD', 'USD_JPY',  # Major forex pairs
            'AAPL', 'MSFT', 'GOOGL',  # Major stocks
            'BTC_USD', 'ETH_USD',  # Crypto pairs
            'GOLD', 'SILVER'  # Commodities
        ]
        self.discovery_timeout = 300  # 5 minutes
        
    async def discover_capabilities(self, 
                                  adapter: BrokerAdapter,
                                  test_type: CapabilityTestType = CapabilityTestType.STATIC,
                                  force_refresh: bool = False) -> BrokerCapabilityProfile:
        """
        Discover broker capabilities
        
        Args:
            adapter: BrokerAdapter instance
            test_type: Type of capability testing to perform
            force_refresh: Force rediscovery even if cached
            
        Returns:
            BrokerCapabilityProfile with discovered capabilities
        """
        broker_name = adapter.broker_name
        
        # Check if we have cached profile
        if not force_refresh and broker_name in self.capability_profiles:
            profile = self.capability_profiles[broker_name]
            # Return cached if less than 24 hours old
            if (datetime.now(timezone.utc) - profile.last_updated) < timedelta(hours=24):
                logger.info(f"Using cached capability profile for {broker_name}")
                return profile
                
        logger.info(f"Discovering capabilities for {broker_name} (test_type: {test_type.value})")
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Initialize profile
            profile = BrokerCapabilityProfile(
                broker_name=broker_name,
                capabilities=set(),
                supported_instruments=[],
                supported_order_types=[],
                supported_time_in_force=[],
                minimum_trade_sizes={},
                maximum_trade_sizes={},
                commission_structure={},
                margin_requirements={},
                trading_hours={},
                api_rate_limits={}
            )
            
            # Get basic information from adapter
            await self._discover_basic_info(adapter, profile)
            
            # Discover instruments
            await self._discover_instruments(adapter, profile)
            
            # Test capabilities based on type
            if test_type == CapabilityTestType.STATIC:
                await self._discover_static_capabilities(adapter, profile)
            elif test_type == CapabilityTestType.DYNAMIC:
                await self._discover_dynamic_capabilities(adapter, profile)
            elif test_type == CapabilityTestType.SYNTHETIC:
                await self._discover_synthetic_capabilities(adapter, profile)
                
            # Discover order types and time in force
            await self._discover_order_features(adapter, profile)
            
            # Discover trading constraints
            await self._discover_trading_constraints(adapter, profile)
            
            # Discover rate limits
            await self._discover_rate_limits(adapter, profile)
            
            # Cache the profile
            self.capability_profiles[broker_name] = profile
            
            discovery_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(f"Capability discovery completed for {broker_name} in {discovery_time:.2f}s")
            
            return profile
            
        except Exception as e:
            logger.error(f"Capability discovery failed for {broker_name}: {e}")
            # Return partial profile with error
            error_profile = BrokerCapabilityProfile(
                broker_name=broker_name,
                capabilities=set(),
                supported_instruments=[],
                supported_order_types=[],
                supported_time_in_force=[],
                minimum_trade_sizes={},
                maximum_trade_sizes={},
                commission_structure={},
                margin_requirements={},
                trading_hours={},
                api_rate_limits={},
                metadata={'discovery_error': str(e)}
            )
            return error_profile
            
    async def _discover_basic_info(self, adapter: BrokerAdapter, profile: BrokerCapabilityProfile):
        """Discover basic broker information"""
        try:
            # Get broker info if available
            if hasattr(adapter, 'get_broker_info'):
                broker_info = await adapter.get_broker_info()
                profile.capabilities.update(broker_info.capabilities)
                profile.supported_order_types.extend(broker_info.supported_order_types)
                profile.supported_time_in_force.extend(broker_info.supported_time_in_force)
                profile.minimum_trade_sizes.update(broker_info.minimum_trade_size)
                profile.maximum_trade_sizes.update(broker_info.maximum_trade_size)
                profile.commission_structure = broker_info.commission_structure
                profile.margin_requirements.update(broker_info.margin_requirements)
                profile.trading_hours.update(broker_info.trading_hours)
                profile.api_rate_limits.update(broker_info.api_rate_limits)
            else:
                # Fallback to adapter properties
                profile.capabilities.update(adapter.capabilities)
                profile.supported_order_types.extend(adapter.supported_order_types)
                
        except Exception as e:
            logger.warning(f"Could not get basic broker info: {e}")
            
    async def _discover_instruments(self, adapter: BrokerAdapter, profile: BrokerCapabilityProfile):
        """Discover supported instruments"""
        try:
            supported_instruments = adapter.supported_instruments
            
            for instrument in supported_instruments[:50]:  # Limit to first 50 for performance
                try:
                    # Get trading status to verify instrument is actually tradeable
                    trading_status = await adapter.get_trading_status(instrument)
                    
                    # Try to get current price to verify instrument is active
                    current_price = await asyncio.wait_for(
                        adapter.get_current_price(instrument),
                        timeout=10
                    )
                    
                    instrument_info = InstrumentInfo(
                        symbol=instrument,
                        name=instrument,  # Use symbol as name for now
                        instrument_type=self._infer_instrument_type(instrument),
                        is_tradeable=trading_status.get('tradeable', True)
                    )
                    
                    # Try to extract currency information for forex pairs
                    if '_' in instrument and len(instrument.split('_')) == 2:
                        base, quote = instrument.split('_')
                        instrument_info.base_currency = base
                        instrument_info.quote_currency = quote
                        instrument_info.instrument_type = 'forex'
                        
                    profile.supported_instruments.append(instrument_info)
                    
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout getting price for {instrument}")
                    continue
                except Exception as e:
                    logger.debug(f"Could not verify instrument {instrument}: {e}")
                    continue
                    
        except Exception as e:
            logger.warning(f"Could not discover instruments: {e}")
            
    async def _discover_static_capabilities(self, adapter: BrokerAdapter, profile: BrokerCapabilityProfile):
        """Discover capabilities using static analysis"""
        # Test each capability
        for capability in BrokerCapability:
            test_result = CapabilityTestResult(
                capability=capability,
                supported=adapter.is_capability_supported(capability),
                test_type=CapabilityTestType.STATIC,
                confidence_level=0.9,  # High confidence for static tests
                test_details={'method': 'adapter.is_capability_supported'}
            )
            
            if test_result.supported:
                profile.capabilities.add(capability)
                
            profile.test_results.append(test_result)
            
    async def _discover_dynamic_capabilities(self, adapter: BrokerAdapter, profile: BrokerCapabilityProfile):
        """Discover capabilities using dynamic API testing"""
        # Test real-time streaming capability
        await self._test_streaming_capability(adapter, profile)
        
        # Test order placement capabilities (without actually placing orders)
        await self._test_order_capabilities(adapter, profile)
        
        # Test account information capabilities
        await self._test_account_capabilities(adapter, profile)
        
        # Test position management capabilities
        await self._test_position_capabilities(adapter, profile)
        
    async def _test_streaming_capability(self, adapter: BrokerAdapter, profile: BrokerCapabilityProfile):
        """Test real-time streaming capability"""
        try:
            # Try to start price stream for a common instrument
            test_instrument = 'EUR_USD'
            if test_instrument not in adapter.supported_instruments:
                test_instrument = adapter.supported_instruments[0] if adapter.supported_instruments else None
                
            if test_instrument:
                async def test_stream():
                    count = 0
                    async for price_tick in adapter.stream_prices([test_instrument]):
                        count += 1
                        if count >= 3:  # Test with a few ticks
                            break
                    return count > 0
                    
                # Test with timeout
                streaming_works = await asyncio.wait_for(test_stream(), timeout=30)
                
                test_result = CapabilityTestResult(
                    capability=BrokerCapability.REAL_TIME_STREAMING,
                    supported=streaming_works,
                    test_type=CapabilityTestType.DYNAMIC,
                    confidence_level=0.95,
                    test_details={'method': 'stream_prices', 'instrument': test_instrument}
                )
                
                if streaming_works:
                    profile.capabilities.add(BrokerCapability.REAL_TIME_STREAMING)
                    
                profile.test_results.append(test_result)
                
        except Exception as e:
            test_result = CapabilityTestResult(
                capability=BrokerCapability.REAL_TIME_STREAMING,
                supported=False,
                test_type=CapabilityTestType.DYNAMIC,
                confidence_level=0.8,
                test_details={'method': 'stream_prices'},
                error_message=str(e)
            )
            profile.test_results.append(test_result)
            
    async def _test_order_capabilities(self, adapter: BrokerAdapter, profile: BrokerCapabilityProfile):
        """Test order-related capabilities"""
        # Test if we can validate orders (without placing them)
        test_order = UnifiedOrder(
            order_id="test_order",
            client_order_id=adapter.generate_client_order_id(),
            instrument="EUR_USD" if "EUR_USD" in adapter.supported_instruments else adapter.supported_instruments[0],
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal('1000')
        )
        
        try:
            validation_errors = adapter.validate_order(test_order)
            order_validation_works = len(validation_errors) == 0
            
            test_result = CapabilityTestResult(
                capability=BrokerCapability.MARKET_ORDERS,
                supported=order_validation_works,
                test_type=CapabilityTestType.DYNAMIC,
                confidence_level=0.7,
                test_details={'method': 'validate_order', 'errors': validation_errors}
            )
            
            if order_validation_works:
                profile.capabilities.add(BrokerCapability.MARKET_ORDERS)
                
            profile.test_results.append(test_result)
            
        except Exception as e:
            logger.debug(f"Order validation test failed: {e}")
            
    async def _test_account_capabilities(self, adapter: BrokerAdapter, profile: BrokerCapabilityProfile):
        """Test account information capabilities"""
        try:
            # Test account summary
            account_summary = await asyncio.wait_for(
                adapter.get_account_summary(),
                timeout=10
            )
            
            account_works = account_summary is not None
            
            test_result = CapabilityTestResult(
                capability=BrokerCapability.MULTIPLE_ACCOUNTS,
                supported=account_works,
                test_type=CapabilityTestType.DYNAMIC,
                confidence_level=0.9,
                test_details={'method': 'get_account_summary'}
            )
            
            profile.test_results.append(test_result)
            
            # Test multiple accounts
            try:
                accounts = await asyncio.wait_for(
                    adapter.get_accounts(),
                    timeout=10
                )
                
                multiple_accounts = len(accounts) > 1 if accounts else False
                
                test_result = CapabilityTestResult(
                    capability=BrokerCapability.MULTIPLE_ACCOUNTS,
                    supported=multiple_accounts,
                    test_type=CapabilityTestType.DYNAMIC,
                    confidence_level=0.9,
                    test_details={'method': 'get_accounts', 'account_count': len(accounts) if accounts else 0}
                )
                
                if multiple_accounts:
                    profile.capabilities.add(BrokerCapability.MULTIPLE_ACCOUNTS)
                    
                profile.test_results.append(test_result)
                
            except Exception as e:
                logger.debug(f"Multiple accounts test failed: {e}")
                
        except Exception as e:
            logger.debug(f"Account capabilities test failed: {e}")
            
    async def _test_position_capabilities(self, adapter: BrokerAdapter, profile: BrokerCapabilityProfile):
        """Test position management capabilities"""
        try:
            # Test getting positions
            positions = await asyncio.wait_for(
                adapter.get_positions(),
                timeout=10
            )
            
            positions_work = positions is not None
            
            test_result = CapabilityTestResult(
                capability=BrokerCapability.POSITION_MODIFICATION,
                supported=positions_work,
                test_type=CapabilityTestType.DYNAMIC,
                confidence_level=0.8,
                test_details={'method': 'get_positions'}
            )
            
            profile.test_results.append(test_result)
            
        except Exception as e:
            logger.debug(f"Position capabilities test failed: {e}")
            
    async def _discover_synthetic_capabilities(self, adapter: BrokerAdapter, profile: BrokerCapabilityProfile):
        """Discover capabilities using synthetic orders (placed and immediately cancelled)"""
        # This would require placing actual test orders and cancelling them
        # For now, fall back to static discovery
        await self._discover_static_capabilities(adapter, profile)
        
    async def _discover_order_features(self, adapter: BrokerAdapter, profile: BrokerCapabilityProfile):
        """Discover supported order types and time in force options"""
        # Get from adapter if not already populated
        if not profile.supported_order_types:
            profile.supported_order_types = list(adapter.supported_order_types)
            
        # Infer capabilities from supported order types
        for order_type in profile.supported_order_types:
            if order_type == OrderType.MARKET:
                profile.capabilities.add(BrokerCapability.MARKET_ORDERS)
            elif order_type == OrderType.LIMIT:
                profile.capabilities.add(BrokerCapability.LIMIT_ORDERS)
            elif order_type == OrderType.STOP:
                profile.capabilities.add(BrokerCapability.STOP_ORDERS)
            elif order_type == OrderType.STOP_LOSS:
                profile.capabilities.add(BrokerCapability.STOP_LOSS_ORDERS)
            elif order_type == OrderType.TAKE_PROFIT:
                profile.capabilities.add(BrokerCapability.TAKE_PROFIT_ORDERS)
            elif order_type == OrderType.TRAILING_STOP:
                profile.capabilities.add(BrokerCapability.TRAILING_STOPS)
                
    async def _discover_trading_constraints(self, adapter: BrokerAdapter, profile: BrokerCapabilityProfile):
        """Discover trading constraints and limits"""
        # Try to get constraint information from broker
        for instrument in profile.supported_instruments[:10]:  # Test first 10 instruments
            try:
                # Try to determine minimum trade size by validation
                for test_size in [Decimal('1'), Decimal('100'), Decimal('1000'), Decimal('10000')]:
                    test_order = UnifiedOrder(
                        order_id="test_constraint",
                        client_order_id=adapter.generate_client_order_id(),
                        instrument=instrument.symbol,
                        order_type=OrderType.MARKET,
                        side=OrderSide.BUY,
                        units=test_size
                    )
                    
                    errors = adapter.validate_order(test_order)
                    if not any('units' in error.lower() or 'size' in error.lower() for error in errors):
                        # This size seems acceptable
                        if instrument.symbol not in profile.minimum_trade_sizes:
                            profile.minimum_trade_sizes[instrument.symbol] = test_size
                        break
                        
            except Exception as e:
                logger.debug(f"Could not determine constraints for {instrument.symbol}: {e}")
                
    async def _discover_rate_limits(self, adapter: BrokerAdapter, profile: BrokerCapabilityProfile):
        """Discover API rate limits"""
        # This would require actual rate limit testing
        # For now, use defaults or adapter-provided information
        if hasattr(adapter, 'api_rate_limits'):
            profile.api_rate_limits.update(adapter.api_rate_limits)
        else:
            # Set conservative defaults
            profile.api_rate_limits = {
                'default': 10,  # 10 requests per second
                'streaming': 1,  # 1 stream connection
                'orders': 5,    # 5 orders per second
                'market_data': 20  # 20 market data requests per second
            }
            
    def _infer_instrument_type(self, instrument: str) -> str:
        """Infer instrument type from symbol"""
        if '_' in instrument:
            parts = instrument.split('_')
            if len(parts) == 2 and len(parts[0]) == 3 and len(parts[1]) == 3:
                return 'forex'
            elif 'BTC' in instrument or 'ETH' in instrument or 'CRYPTO' in instrument.upper():
                return 'crypto'
        elif instrument.upper() in ['GOLD', 'SILVER', 'OIL', 'CRUDE']:
            return 'commodity'
        elif len(instrument) <= 5 and instrument.isalpha():
            return 'stock'
        else:
            return 'unknown'
            
    def get_capability_profile(self, broker_name: str) -> Optional[BrokerCapabilityProfile]:
        """Get cached capability profile for broker"""
        return self.capability_profiles.get(broker_name)
        
    def compare_broker_capabilities(self, broker_names: List[str]) -> Dict[str, Any]:
        """
        Compare capabilities across multiple brokers
        
        Args:
            broker_names: List of broker names to compare
            
        Returns:
            Comparison matrix
        """
        comparison = {
            'brokers': broker_names,
            'capabilities': {},
            'instruments': {},
            'order_types': {},
            'summary': {}
        }
        
        all_capabilities = set()
        all_instruments = set()
        all_order_types = set()
        
        # Collect all capabilities, instruments, and order types
        for broker_name in broker_names:
            profile = self.capability_profiles.get(broker_name)
            if profile:
                all_capabilities.update(profile.capabilities)
                all_instruments.update([inst.symbol for inst in profile.supported_instruments])
                all_order_types.update(profile.supported_order_types)
                
        # Build comparison matrix
        for capability in all_capabilities:
            comparison['capabilities'][capability.value] = {}
            for broker_name in broker_names:
                profile = self.capability_profiles.get(broker_name)
                comparison['capabilities'][capability.value][broker_name] = (
                    capability in profile.capabilities if profile else False
                )
                
        for instrument in sorted(all_instruments):
            comparison['instruments'][instrument] = {}
            for broker_name in broker_names:
                profile = self.capability_profiles.get(broker_name)
                supported = False
                if profile:
                    supported = any(inst.symbol == instrument for inst in profile.supported_instruments)
                comparison['instruments'][instrument][broker_name] = supported
                
        for order_type in all_order_types:
            comparison['order_types'][order_type.value] = {}
            for broker_name in broker_names:
                profile = self.capability_profiles.get(broker_name)
                comparison['order_types'][order_type.value][broker_name] = (
                    order_type in profile.supported_order_types if profile else False
                )
                
        # Generate summary
        for broker_name in broker_names:
            profile = self.capability_profiles.get(broker_name)
            if profile:
                comparison['summary'][broker_name] = {
                    'total_capabilities': len(profile.capabilities),
                    'total_instruments': len(profile.supported_instruments),
                    'total_order_types': len(profile.supported_order_types),
                    'last_updated': profile.last_updated.isoformat()
                }
            else:
                comparison['summary'][broker_name] = {
                    'total_capabilities': 0,
                    'total_instruments': 0,
                    'total_order_types': 0,
                    'last_updated': None
                }
                
        return comparison
        
    async def refresh_all_profiles(self, 
                                 adapters: Dict[str, BrokerAdapter],
                                 test_type: CapabilityTestType = CapabilityTestType.STATIC):
        """Refresh capability profiles for all provided adapters"""
        tasks = []
        for broker_name, adapter in adapters.items():
            task = self.discover_capabilities(adapter, test_type, force_refresh=True)
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            broker_name = list(adapters.keys())[i]
            if isinstance(result, Exception):
                logger.error(f"Failed to refresh profile for {broker_name}: {result}")
            else:
                logger.info(f"Refreshed capability profile for {broker_name}")
                
    def export_profiles(self, file_path: str, broker_names: Optional[List[str]] = None):
        """Export capability profiles to file"""
        profiles_to_export = {}
        
        if broker_names:
            for name in broker_names:
                if name in self.capability_profiles:
                    profiles_to_export[name] = self.capability_profiles[name].to_dict()
        else:
            profiles_to_export = {
                name: profile.to_dict() 
                for name, profile in self.capability_profiles.items()
            }
            
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(profiles_to_export, f, indent=2, default=str)
            
        logger.info(f"Exported {len(profiles_to_export)} capability profiles to {file_path}")


# Global capability discovery engine
_global_discovery_engine: Optional[CapabilityDiscoveryEngine] = None


def get_global_discovery_engine() -> CapabilityDiscoveryEngine:
    """Get global capability discovery engine instance"""
    global _global_discovery_engine
    if _global_discovery_engine is None:
        _global_discovery_engine = CapabilityDiscoveryEngine()
    return _global_discovery_engine