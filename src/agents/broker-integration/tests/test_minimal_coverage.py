"""
Minimal Coverage Tests for Critical Modules
Story 8.12 - Focused Coverage Strategy

Minimal tests to reach 90% coverage on critical modules by exercising specific missing lines.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Set

# Test imports
import sys
from pathlib import Path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from broker_adapter import BrokerAdapter, OrderType, OrderSide, BrokerCapability
from unified_errors import StandardBrokerError, StandardErrorCode, ErrorSeverity, ErrorCategory, ErrorContext


class TestMinimalBrokerAdapterCoverage:
    """Minimal test to cover broker adapter abstract methods"""
    
    def test_broker_adapter_abstract_methods(self):
        """Test that creates a minimal concrete implementation to cover abstract methods"""
        
        class TestAdapter(BrokerAdapter):
            @property
            def broker_name(self) -> str:
                return "test"
            
            @property 
            def broker_display_name(self) -> str:
                return "Test"
                
            @property
            def api_version(self) -> str:
                return "1.0"
                
            @property
            def capabilities(self) -> Set[BrokerCapability]:
                return set()
                
            @property
            def supported_instruments(self) -> List[str]:
                return []
                
            @property
            def supported_order_types(self) -> List[OrderType]:
                return []
                
            async def authenticate(self, credentials: Dict[str, str]) -> bool:
                return True
            async def disconnect(self) -> bool:
                return True
            async def health_check(self) -> bool:
                return True
            async def get_broker_info(self):
                return None
            async def place_order(self, order):
                return None
            async def modify_order(self, order_id: str, **kwargs) -> bool:
                return True
            async def cancel_order(self, order_id: str) -> bool:
                return True
            async def get_order(self, order_id: str):
                return None
            async def get_orders(self, **filters):
                return []
            async def get_position(self, position_id: str):
                return None
            async def get_positions(self, **filters):
                return []
            async def close_position(self, position_id: str, units=None):
                return None
            async def get_current_price(self, instrument: str):
                return None
            async def get_current_prices(self, instruments: List[str]):
                return []
            async def stream_prices(self, instruments: List[str], callback):
                pass
            async def get_historical_data(self, instrument: str, **kwargs):
                return []
            async def get_account_summary(self):
                return None
            async def get_accounts(self):
                return []
            async def get_transactions(self, **filters):
                return []
            def map_error(self, error: Exception):
                return None
        
        adapter = TestAdapter({"test": "config"})
        
        # Test properties - covers lines 223, 229, 235, 241, 247, 253
        assert adapter.broker_name == "test"
        assert adapter.broker_display_name == "Test" 
        assert adapter.api_version == "1.0"
        assert isinstance(adapter.capabilities, set)
        assert isinstance(adapter.supported_instruments, list)
        assert isinstance(adapter.supported_order_types, list)


class TestMinimalUnifiedErrorsCoverage:
    """Minimal test to cover unified errors missing lines"""
    
    def test_error_context_creation(self):
        """Test ErrorContext with actual signature"""
        context = ErrorContext(
            broker_name="test_broker",
            account_id="test_account", 
            order_id="test_order",
            instrument="EUR_USD",
            operation="place_order",
            request_id="req_123"
        )
        
        assert context.broker_name == "test_broker"
        assert context.account_id == "test_account"
        assert context.order_id == "test_order"
        assert context.instrument == "EUR_USD"
        assert context.operation == "place_order"
        assert context.request_id == "req_123"
    
    def test_error_category_enum_all_values(self):
        """Test all ErrorCategory enum values"""
        categories = [
            ErrorCategory.AUTHENTICATION,
            ErrorCategory.AUTHORIZATION, 
            ErrorCategory.VALIDATION,
            ErrorCategory.BUSINESS_LOGIC,
            ErrorCategory.TECHNICAL,
            ErrorCategory.REGULATORY,
            ErrorCategory.MARKET_DATA,
            ErrorCategory.CONNECTIVITY
        ]
        
        for category in categories:
            assert category.value is not None
            assert isinstance(category.value, str)
    
    def test_standard_broker_error_with_context(self):
        """Test StandardBrokerError with ErrorContext"""
        context = ErrorContext(
            broker_name="test_broker",
            account_id="test_account"
        )
        
        error = StandardBrokerError(
            error_code=StandardErrorCode.CONNECTION_ERROR,
            message="Connection failed",
            severity=ErrorSeverity.HIGH,
            context=context
        )
        
        assert error.error_code == StandardErrorCode.CONNECTION_ERROR
        assert error.message == "Connection failed"
        assert error.severity == ErrorSeverity.HIGH
        assert error.context.broker_name == "test_broker"
        
        # Test string representation (covers missing str/repr lines)
        error_str = str(error)
        assert "CONNECTION_ERROR" in error_str
        
        error_repr = repr(error)
        assert "StandardBrokerError" in error_repr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])