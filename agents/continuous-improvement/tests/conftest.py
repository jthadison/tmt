"""
Test configuration for Continuous Improvement Pipeline tests
"""

import sys
import os
from pathlib import Path

# Add the app directory to the Python path
test_dir = Path(__file__).parent
app_dir = test_dir.parent / "app"
project_root = test_dir.parent.parent.parent  # Get to tmt root

sys.path.insert(0, str(app_dir))
sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import Mock, AsyncMock

# Import test components that work without complex dependencies
try:
    from test_components import (
        ContinuousImprovementOrchestrator,
        ShadowTestingEngine,
        GradualRolloutManager,
        PerformanceComparator,
        AutomaticRollbackManager,
        ImprovementSuggestionEngine,
        OptimizationReportGenerator
    )
    from models import *
except ImportError as e:
    print(f"Import error in conftest.py: {e}")
    # Continue - tests will handle import errors appropriately
    pass

@pytest.fixture
def mock_data_providers():
    """Create mock data providers for testing"""
    return {
        'trade_data_provider': Mock(),
        'performance_data_provider': Mock(),
        'market_data_provider': Mock()
    }

@pytest.fixture 
def clean_test_environment():
    """Provide a clean test environment for each test"""
    # Reset any global state before each test
    yield
    # Cleanup after test if needed