"""
Pytest configuration and fixtures for overfitting monitor tests
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any


@pytest.fixture
def baseline_parameters() -> Dict[str, Any]:
    """Baseline parameters fixture"""
    return {
        "confidence_threshold": 55.0,
        "min_risk_reward": 1.8,
        "vpa_threshold": 0.6
    }


@pytest.fixture
def session_parameters() -> Dict[str, Dict[str, Any]]:
    """Session-specific parameters fixture"""
    return {
        "London": {
            "confidence_threshold": 72.0,
            "min_risk_reward": 3.2,
            "vpa_threshold": 0.65
        },
        "NY": {
            "confidence_threshold": 70.0,
            "min_risk_reward": 2.8,
            "vpa_threshold": 0.62
        },
        "Tokyo": {
            "confidence_threshold": 85.0,
            "min_risk_reward": 4.0,
            "vpa_threshold": 0.7
        }
    }


@pytest.fixture
def current_timestamp():
    """Current UTC timestamp fixture"""
    return datetime.now(timezone.utc)
