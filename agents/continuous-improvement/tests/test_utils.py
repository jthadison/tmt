"""
Test utilities for continuous improvement pipeline testing
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Import our mock data interfaces
from mock_data_interfaces import (
    MockTradeDataProvider, 
    MockPerformanceDataProvider,
    MockMarketDataProvider
)

def setup_test_environment():
    """Setup the test environment with proper mocking"""
    
    # Create mock module for data interfaces
    mock_data_interfaces = Mock()
    mock_data_interfaces.TradeDataInterface = Mock()
    mock_data_interfaces.MockTradeDataProvider = MockTradeDataProvider
    mock_data_interfaces.PerformanceDataInterface = Mock()
    mock_data_interfaces.MockPerformanceDataProvider = MockPerformanceDataProvider
    mock_data_interfaces.MarketDataInterface = Mock()
    mock_data_interfaces.MockMarketDataProvider = MockMarketDataProvider
    
    # Mock the shared utilities module path
    sys.modules['src'] = Mock()
    sys.modules['src.shared'] = Mock()
    sys.modules['src.shared.python_utils'] = Mock()
    sys.modules['src.shared.python_utils.data_interfaces'] = mock_data_interfaces
    
    return mock_data_interfaces

def patch_relative_imports():
    """Patch relative imports to work in test environment"""
    import importlib.util
    import importlib.machinery
    
    # Patch the import system to handle relative imports during testing
    original_import = __builtins__.__import__
    
    def patched_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level > 0 and globals and '__name__' in globals:
            # This is a relative import
            module_name = globals['__name__']
            if module_name and '.' not in module_name:
                # We're in a top-level module, convert relative to absolute
                if name == 'models':
                    name = 'models'
                    level = 0
        
        return original_import(name, globals, locals, fromlist, level)
    
    __builtins__.__import__ = patched_import

def get_mock_data_providers():
    """Get mock data provider instances for testing"""
    return {
        'trade_data_provider': MockTradeDataProvider(),
        'performance_data_provider': MockPerformanceDataProvider(),
        'market_data_provider': MockMarketDataProvider()
    }