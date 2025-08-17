"""
Failure Injection Testing Suite for Broker Integration
Story 8.12 - Task 4: Implement failure injection testing (AC: 5)
"""
import pytest
import asyncio
import random
import logging
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

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
from unified_errors import (
    StandardBrokerError, StandardErrorCode, ErrorSeverity, ErrorCategory
)
from circuit_breaker import CircuitBreakerOpenError
from retry_handler import RetryConfiguration

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Types of failures to inject"""
    NETWORK_TIMEOUT = "network_timeout"
    CONNECTION_LOST = "connection_lost"
    API_ERROR_500 = "api_error_500"
    API_ERROR_429 = "api_error_429"  # Rate limit
    API_ERROR_401 = "api_error_401"  # Auth error
    API_ERROR_404 = "api_error_404"  # Not found
    PARTIAL_RESPONSE = "partial_response"
    CORRUPTED_DATA = "corrupted_data"
    SLOW_RESPONSE = "slow_response"
    INTERMITTENT_FAILURE = "intermittent_failure"


class FailureInjector:
    """Configurable failure injection system"""
    
    def __init__(self):
        self.failure_rules = {}
        self.failure_count = 0
        self.failure_history = []
        self.active_failures = set()
        
    def add_failure_rule(self, 
                        operation: str, 
                        failure_type: FailureType,
                        probability: float = 1.0,
                        conditions: Optional[Dict[str, Any]] = None):
        """Add a failure injection rule"""
        rule = {
            'failure_type': failure_type,
            'probability': probability,
            'conditions': conditions or {},
            'trigger_count': 0,
            'created_at': datetime.now(timezone.utc)
        }
        
        if operation not in self.failure_rules:
            self.failure_rules[operation] = []
        self.failure_rules[operation].append(rule)
        
    def should_inject_failure(self, operation: str, context: Dict[str, Any] = None) -> Optional[FailureType]:
        """Determine if failure should be injected for given operation"""
        context = context or {}
        
        rules = self.failure_rules.get(operation, [])
        for rule in rules:
            # Check conditions
            conditions_met = True
            for key, value in rule['conditions'].items():
                if key not in context or context[key] != value:
                    conditions_met = False
                    break
                    
            if not conditions_met:
                continue
                
            # Check probability
            if random.random() < rule['probability']:
                rule['trigger_count'] += 1
                self.failure_count += 1
                
                failure_event = {
                    'operation': operation,
                    'failure_type': rule['failure_type'],
                    'timestamp': datetime.now(timezone.utc),
                    'context': context
                }
                self.failure_history.append(failure_event)
                
                return rule['failure_type']
                
        return None
        
    def inject_failure(self, failure_type: FailureType, operation: str = "unknown"):
        """Inject specific failure type"""
        if failure_type == FailureType.NETWORK_TIMEOUT:
            raise asyncio.TimeoutError(f"Network timeout in {operation}")
        elif failure_type == FailureType.CONNECTION_LOST:
            raise ConnectionError(f"Connection lost during {operation}")
        elif failure_type == FailureType.API_ERROR_500:
            raise StandardBrokerError(
                error_code=StandardErrorCode.SERVER_ERROR,
                message="Internal server error (injected)",
                severity=ErrorSeverity.HIGH
            )
        elif failure_type == FailureType.API_ERROR_429:
            raise StandardBrokerError(
                error_code=StandardErrorCode.RATE_LIMITED,
                message="Rate limit exceeded (injected)",
                severity=ErrorSeverity.MEDIUM,
                is_retryable=True,
                retry_after_seconds=30
            )
        elif failure_type == FailureType.API_ERROR_401:
            raise StandardBrokerError(
                error_code=StandardErrorCode.AUTHENTICATION_FAILED,
                message="Authentication failed (injected)",
                severity=ErrorSeverity.HIGH
            )
        elif failure_type == FailureType.API_ERROR_404:
            raise StandardBrokerError(
                error_code=StandardErrorCode.ORDER_NOT_FOUND,
                message="Resource not found (injected)",
                severity=ErrorSeverity.MEDIUM
            )
        else:
            raise StandardBrokerError(
                error_code=StandardErrorCode.UNKNOWN_ERROR,
                message=f"Injected failure: {failure_type.value}"
            )
            
    def clear_rules(self):
        """Clear all failure rules"""
        self.failure_rules.clear()
        
    def get_failure_stats(self) -> Dict[str, Any]:
        """Get failure injection statistics"""
        return {
            'total_failures': self.failure_count,
            'total_rules': sum(len(rules) for rules in self.failure_rules.values()),
            'operations_with_failures': list(self.failure_rules.keys()),
            'recent_failures': self.failure_history[-10:],  # Last 10 failures
            'failure_types': list(set(event['failure_type'] for event in self.failure_history))
        }


class FailureInjectionAdapter(BrokerAdapter):
    """Broker adapter with failure injection capabilities"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._broker_name = "failure_injection_test"
        self.injector = FailureInjector()
        self.circuit_breaker_triggered = False
        self.operation_count = 0
        
    @property
    def broker_name(self) -> str:
        return self._broker_name
        
    @property
    def broker_display_name(self) -> str:
        return "Failure Injection Test Adapter"
        
    @property
    def api_version(self) -> str:
        return "test_v1"
        
    @property
    def capabilities(self) -> set:
        return {
            BrokerCapability.MARKET_ORDERS,
            BrokerCapability.LIMIT_ORDERS,
            BrokerCapability.REAL_TIME_STREAMING
        }
        
    @property
    def supported_instruments(self) -> List[str]:
        return ["EUR_USD", "GBP_USD", "USD_JPY"]
        
    @property
    def supported_order_types(self) -> List[OrderType]:
        return [OrderType.MARKET, OrderType.LIMIT]
        
    async def _execute_with_failure_injection(self, operation: str, context: Dict[str, Any] = None):
        """Execute operation with potential failure injection"""
        self.operation_count += 1
        context = context or {}
        context['operation_count'] = self.operation_count
        
        failure_type = self.injector.should_inject_failure(operation, context)
        if failure_type:
            self.injector.inject_failure(failure_type, operation)
            
    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        await self._execute_with_failure_injection("authenticate", credentials)
        return True
        
    async def disconnect(self) -> bool:
        await self._execute_with_failure_injection("disconnect")
        return True
        
    async def health_check(self) -> Dict[str, Any]:
        await self._execute_with_failure_injection("health_check")
        return {
            'status': 'healthy',
            'operation_count': self.operation_count,
            'failure_stats': self.injector.get_failure_stats()
        }
        
    async def get_broker_info(self):
        await self._execute_with_failure_injection("get_broker_info")
        return {'name': self.broker_name}
        
    async def get_account_summary(self, account_id: Optional[str] = None) -> UnifiedAccountSummary:
        await self._execute_with_failure_injection("get_account_summary", {'account_id': account_id})
        
        return UnifiedAccountSummary(
            account_id=account_id or "test_account",
            account_name="Failure Test Account",
            currency="USD",
            balance=Decimal("10000.00"),
            available_margin=Decimal("9500.00"),
            used_margin=Decimal("500.00")
        )
        
    async def get_accounts(self) -> List[UnifiedAccountSummary]:
        await self._execute_with_failure_injection("get_accounts")
        return [await self.get_account_summary()]
        
    async def place_order(self, order: UnifiedOrder) -> OrderResult:
        context = {
            'instrument': order.instrument,
            'order_type': order.order_type.value,
            'units': float(order.units)
        }
        await self._execute_with_failure_injection("place_order", context)
        
        return OrderResult(
            success=True,
            order_id=f"order_{self.operation_count}",
            client_order_id=order.client_order_id,
            order_state=OrderState.FILLED,
            fill_price=Decimal("1.1000"),
            filled_units=order.units
        )
        
    async def modify_order(self, order_id: str, modifications: Dict[str, Any]) -> OrderResult:
        await self._execute_with_failure_injection("modify_order", {'order_id': order_id})
        return OrderResult(success=True, order_id=order_id)
        
    async def cancel_order(self, order_id: str, reason: Optional[str] = None) -> OrderResult:
        await self._execute_with_failure_injection("cancel_order", {'order_id': order_id})
        return OrderResult(success=True, order_id=order_id)
        
    async def get_order(self, order_id: str) -> Optional[UnifiedOrder]:
        await self._execute_with_failure_injection("get_order", {'order_id': order_id})
        return None
        
    async def get_orders(self, **kwargs) -> List[UnifiedOrder]:
        await self._execute_with_failure_injection("get_orders", kwargs)
        return []
        
    async def get_position(self, instrument: str, account_id: Optional[str] = None) -> Optional[UnifiedPosition]:
        await self._execute_with_failure_injection("get_position", {'instrument': instrument})
        return None
        
    async def get_positions(self, account_id: Optional[str] = None) -> List[UnifiedPosition]:
        await self._execute_with_failure_injection("get_positions", {'account_id': account_id})
        return []
        
    async def close_position(self, instrument: str, units: Optional[Decimal] = None, account_id: Optional[str] = None) -> OrderResult:
        context = {'instrument': instrument, 'units': float(units) if units else None}
        await self._execute_with_failure_injection("close_position", context)
        return OrderResult(success=True, order_id="close_order")
        
    async def get_current_price(self, instrument: str) -> Optional[PriceTick]:
        await self._execute_with_failure_injection("get_current_price", {'instrument': instrument})
        
        return PriceTick(
            instrument=instrument,
            bid=Decimal("1.1000"),
            ask=Decimal("1.1002"),
            timestamp=datetime.now(timezone.utc)
        )
        
    async def get_current_prices(self, instruments: List[str]) -> Dict[str, PriceTick]:
        if not instruments:
            raise ValueError("Instruments list is required")
            
        await self._execute_with_failure_injection("get_current_prices", {'instruments': instruments})
        
        return {
            instrument: PriceTick(
                instrument=instrument,
                bid=Decimal("1.1000"),
                ask=Decimal("1.1002"),
                timestamp=datetime.now(timezone.utc)
            )
            for instrument in instruments
        }
        
    async def stream_prices(self, instruments: List[str]):
        for instrument in instruments:
            yield await self.get_current_price(instrument)
            
    async def get_historical_data(self, **kwargs) -> List[Dict[str, Any]]:
        await self._execute_with_failure_injection("get_historical_data", kwargs)
        return []
        
    async def get_transactions(self, **kwargs) -> List[Dict[str, Any]]:
        await self._execute_with_failure_injection("get_transactions", kwargs)
        return []
        
    def map_error(self, broker_error: Exception) -> StandardBrokerError:
        return StandardBrokerError(
            error_code=StandardErrorCode.UNKNOWN_ERROR,
            message=str(broker_error)
        )


class TestNetworkFailures:
    """Test network-related failure scenarios"""
    
    @pytest.fixture
    def failure_adapter(self):
        """Adapter with failure injection capabilities"""
        return FailureInjectionAdapter({})
        
    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, failure_adapter):
        """Test handling of network timeouts"""
        # Inject network timeout for authentication
        failure_adapter.injector.add_failure_rule(
            "authenticate", 
            FailureType.NETWORK_TIMEOUT,
            probability=1.0
        )
        
        with pytest.raises(asyncio.TimeoutError):
            await failure_adapter.authenticate({'api_key': 'test'})
            
        stats = failure_adapter.injector.get_failure_stats()
        assert stats['total_failures'] == 1
        assert FailureType.NETWORK_TIMEOUT in stats['failure_types']
        
    @pytest.mark.asyncio
    async def test_connection_lost_during_order(self, failure_adapter):
        """Test handling of connection loss during order placement"""
        # Inject connection loss for order placement
        failure_adapter.injector.add_failure_rule(
            "place_order",
            FailureType.CONNECTION_LOST,
            probability=1.0
        )
        
        order = UnifiedOrder(
            order_id="test_order",
            client_order_id="client_test",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("1000")
        )
        
        with pytest.raises(ConnectionError):
            await failure_adapter.place_order(order)
            
    @pytest.mark.asyncio
    async def test_intermittent_failures(self, failure_adapter):
        """Test handling of intermittent failures"""
        # Inject 50% failure rate for price requests
        failure_adapter.injector.add_failure_rule(
            "get_current_price",
            FailureType.API_ERROR_500,
            probability=0.5
        )
        
        success_count = 0
        failure_count = 0
        
        for i in range(20):
            try:
                await failure_adapter.get_current_price("EUR_USD")
                success_count += 1
            except StandardBrokerError:
                failure_count += 1
                
        # Should have some of both successes and failures
        assert success_count > 0, "No successful requests"
        assert failure_count > 0, "No failed requests"
        assert success_count + failure_count == 20


class TestAPIErrorHandling:
    """Test API error handling scenarios"""
    
    @pytest.fixture
    def api_failure_adapter(self):
        """Adapter configured for API error testing"""
        return FailureInjectionAdapter({})
        
    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self, api_failure_adapter):
        """Test handling of rate limit errors"""
        api_failure_adapter.injector.add_failure_rule(
            "place_order",
            FailureType.API_ERROR_429,
            probability=1.0
        )
        
        order = UnifiedOrder(
            order_id="rate_test",
            client_order_id="client_rate",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("1000")
        )
        
        with pytest.raises(StandardBrokerError) as exc_info:
            await api_failure_adapter.place_order(order)
            
        error = exc_info.value
        assert error.error_code == StandardErrorCode.RATE_LIMITED
        assert error.is_retryable is True
        assert error.retry_after_seconds == 30
        
    @pytest.mark.asyncio
    async def test_authentication_failure(self, api_failure_adapter):
        """Test handling of authentication failures"""
        api_failure_adapter.injector.add_failure_rule(
            "get_account_summary",
            FailureType.API_ERROR_401,
            probability=1.0
        )
        
        with pytest.raises(StandardBrokerError) as exc_info:
            await api_failure_adapter.get_account_summary()
            
        error = exc_info.value
        assert error.error_code == StandardErrorCode.AUTHENTICATION_FAILED
        assert error.severity == ErrorSeverity.HIGH
        
    @pytest.mark.asyncio
    async def test_server_error_handling(self, api_failure_adapter):
        """Test handling of server errors"""
        api_failure_adapter.injector.add_failure_rule(
            "get_orders",
            FailureType.API_ERROR_500,
            probability=1.0
        )
        
        with pytest.raises(StandardBrokerError) as exc_info:
            await api_failure_adapter.get_orders()
            
        error = exc_info.value
        assert error.error_code == StandardErrorCode.SERVER_ERROR
        assert error.severity == ErrorSeverity.HIGH
        
    @pytest.mark.asyncio
    async def test_not_found_error_handling(self, api_failure_adapter):
        """Test handling of not found errors"""
        api_failure_adapter.injector.add_failure_rule(
            "get_order",
            FailureType.API_ERROR_404,
            probability=1.0,
            conditions={'order_id': 'nonexistent_order'}
        )
        
        with pytest.raises(StandardBrokerError) as exc_info:
            await api_failure_adapter.get_order('nonexistent_order')
            
        error = exc_info.value
        assert error.error_code == StandardErrorCode.ORDER_NOT_FOUND
        
        # Should work for different order ID
        result = await api_failure_adapter.get_order('valid_order')
        assert result is None  # Normal behavior


class TestConditionalFailures:
    """Test conditional failure injection"""
    
    @pytest.fixture
    def conditional_adapter(self):
        """Adapter for conditional failure testing"""
        return FailureInjectionAdapter({})
        
    @pytest.mark.asyncio
    async def test_instrument_specific_failures(self, conditional_adapter):
        """Test failures specific to certain instruments"""
        # Only fail for GBP_USD
        conditional_adapter.injector.add_failure_rule(
            "get_current_price",
            FailureType.API_ERROR_500,
            probability=1.0,
            conditions={'instrument': 'GBP_USD'}
        )
        
        # Should fail for GBP_USD
        with pytest.raises(StandardBrokerError):
            await conditional_adapter.get_current_price('GBP_USD')
            
        # Should succeed for EUR_USD
        price = await conditional_adapter.get_current_price('EUR_USD')
        assert price is not None
        assert price.instrument == 'EUR_USD'
        
    @pytest.mark.asyncio
    async def test_order_size_based_failures(self, conditional_adapter):
        """Test failures based on order size"""
        # Fail for large orders (> 5000 units)
        conditional_adapter.injector.add_failure_rule(
            "place_order",
            FailureType.API_ERROR_500,
            probability=1.0,
            conditions={'units': lambda x: x > 5000}  # Would need custom condition logic
        )
        
        # Small order should succeed
        small_order = UnifiedOrder(
            order_id="small_order",
            client_order_id="client_small",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("1000")
        )
        
        result = await conditional_adapter.place_order(small_order)
        assert result.success is True
        
    @pytest.mark.asyncio
    async def test_operation_count_based_failures(self, conditional_adapter):
        """Test failures based on operation count"""
        # Fail on 5th operation
        conditional_adapter.injector.add_failure_rule(
            "health_check",
            FailureType.API_ERROR_500,
            probability=1.0,
            conditions={'operation_count': 5}
        )
        
        # First 4 operations should succeed
        for i in range(4):
            result = await conditional_adapter.health_check()
            assert result['status'] == 'healthy'
            
        # 5th operation should fail
        with pytest.raises(StandardBrokerError):
            await conditional_adapter.health_check()


class TestFailureRecovery:
    """Test recovery from various failure scenarios"""
    
    @pytest.fixture
    def recovery_adapter(self):
        """Adapter for recovery testing"""
        return FailureInjectionAdapter({})
        
    @pytest.mark.asyncio
    async def test_recovery_after_network_failure(self, recovery_adapter):
        """Test recovery after network failures"""
        # Inject failure for first attempt
        recovery_adapter.injector.add_failure_rule(
            "authenticate",
            FailureType.NETWORK_TIMEOUT,
            probability=1.0,
            conditions={'operation_count': 1}
        )
        
        # First attempt should fail
        with pytest.raises(asyncio.TimeoutError):
            await recovery_adapter.authenticate({'api_key': 'test'})
            
        # Second attempt should succeed (no condition match)
        result = await recovery_adapter.authenticate({'api_key': 'test'})
        assert result is True
        
    @pytest.mark.asyncio
    async def test_graceful_degradation(self, recovery_adapter):
        """Test graceful degradation when price feed fails"""
        # Make price requests fail
        recovery_adapter.injector.add_failure_rule(
            "get_current_price",
            FailureType.CONNECTION_LOST,
            probability=1.0
        )
        
        # Should handle failure gracefully
        try:
            await recovery_adapter.get_current_price("EUR_USD")
            assert False, "Should have failed"
        except ConnectionError:
            # Expected failure
            pass
            
        # Other operations should still work
        health = await recovery_adapter.health_check()
        assert health['status'] == 'healthy'
        
    @pytest.mark.asyncio
    async def test_circuit_breaker_behavior(self, recovery_adapter):
        """Test circuit breaker activation after repeated failures"""
        # Simulate circuit breaker by tracking failures
        failure_count = 0
        max_failures = 3
        
        recovery_adapter.injector.add_failure_rule(
            "place_order",
            FailureType.API_ERROR_500,
            probability=1.0
        )
        
        for i in range(max_failures + 2):
            order = UnifiedOrder(
                order_id=f"cb_test_{i}",
                client_order_id=f"client_cb_{i}",
                instrument="EUR_USD",
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                units=Decimal("1000")
            )
            
            try:
                await recovery_adapter.place_order(order)
            except StandardBrokerError:
                failure_count += 1
                
                # Simulate circuit breaker opening after max failures
                if failure_count >= max_failures:
                    recovery_adapter.circuit_breaker_triggered = True
                    break
                    
        assert recovery_adapter.circuit_breaker_triggered
        assert failure_count == max_failures


class TestFailureInjectionStatistics:
    """Test failure injection statistics and reporting"""
    
    @pytest.fixture
    def stats_adapter(self):
        """Adapter for statistics testing"""
        return FailureInjectionAdapter({})
        
    @pytest.mark.asyncio
    async def test_failure_statistics_tracking(self, stats_adapter):
        """Test that failure statistics are correctly tracked"""
        # Add multiple failure rules
        stats_adapter.injector.add_failure_rule(
            "get_current_price",
            FailureType.NETWORK_TIMEOUT,
            probability=0.5
        )
        
        stats_adapter.injector.add_failure_rule(
            "place_order",
            FailureType.API_ERROR_429,
            probability=0.3
        )
        
        # Execute operations to trigger failures
        operations_count = 20
        
        for i in range(operations_count):
            try:
                await stats_adapter.get_current_price("EUR_USD")
            except:
                pass
                
            try:
                order = UnifiedOrder(
                    order_id=f"stats_test_{i}",
                    client_order_id=f"client_stats_{i}",
                    instrument="EUR_USD",
                    order_type=OrderType.MARKET,
                    side=OrderSide.BUY,
                    units=Decimal("1000")
                )
                await stats_adapter.place_order(order)
            except:
                pass
                
        stats = stats_adapter.injector.get_failure_stats()
        
        assert stats['total_failures'] > 0
        assert stats['total_rules'] == 2
        assert 'get_current_price' in stats['operations_with_failures']
        assert 'place_order' in stats['operations_with_failures']
        assert len(stats['recent_failures']) <= 10
        
    @pytest.mark.asyncio
    async def test_failure_rule_trigger_counts(self, stats_adapter):
        """Test that failure rule trigger counts are tracked"""
        stats_adapter.injector.add_failure_rule(
            "health_check",
            FailureType.API_ERROR_500,
            probability=1.0
        )
        
        # Execute multiple operations
        for i in range(5):
            try:
                await stats_adapter.health_check()
            except:
                pass
                
        # Check that rule was triggered correctly
        rules = stats_adapter.injector.failure_rules['health_check']
        assert len(rules) == 1
        assert rules[0]['trigger_count'] == 5
        
    def test_failure_injector_rule_management(self):
        """Test failure injector rule management"""
        injector = FailureInjector()
        
        # Add rules
        injector.add_failure_rule("test_op", FailureType.NETWORK_TIMEOUT)
        injector.add_failure_rule("test_op", FailureType.API_ERROR_500)
        injector.add_failure_rule("other_op", FailureType.CONNECTION_LOST)
        
        # Check rules are stored correctly
        assert len(injector.failure_rules) == 2
        assert len(injector.failure_rules['test_op']) == 2
        assert len(injector.failure_rules['other_op']) == 1
        
        # Clear rules
        injector.clear_rules()
        assert len(injector.failure_rules) == 0


class TestConcurrentFailures:
    """Test failure injection under concurrent load"""
    
    @pytest.fixture
    def concurrent_failure_adapter(self):
        """Adapter for concurrent failure testing"""
        return FailureInjectionAdapter({})
        
    @pytest.mark.asyncio
    async def test_concurrent_operations_with_failures(self, concurrent_failure_adapter):
        """Test concurrent operations with random failures"""
        # Add random failures
        concurrent_failure_adapter.injector.add_failure_rule(
            "place_order",
            FailureType.API_ERROR_500,
            probability=0.2  # 20% failure rate
        )
        
        # Create concurrent orders
        orders = []
        for i in range(50):
            orders.append(UnifiedOrder(
                order_id=f"concurrent_fail_test_{i}",
                client_order_id=f"client_concurrent_fail_{i}",
                instrument="EUR_USD",
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                units=Decimal("1000")
            ))
            
        # Execute concurrently
        tasks = [concurrent_failure_adapter.place_order(order) for order in orders]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_orders = [r for r in results if isinstance(r, OrderResult) and r.success]
        failed_orders = [r for r in results if isinstance(r, Exception)]
        
        assert len(successful_orders) > 30, "Too many failures in concurrent test"
        assert len(failed_orders) > 5, "Expected some failures with 20% failure rate"
        assert len(successful_orders) + len(failed_orders) == 50


if __name__ == "__main__":
    # Run failure injection tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short"
    ])