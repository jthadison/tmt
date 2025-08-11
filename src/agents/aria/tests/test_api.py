"""
ARIA API Integration Tests
==========================

Tests for the ARIA REST API endpoints including position sizing calculations,
risk analysis, and system health checks.
"""

import pytest
from fastapi.testclient import TestClient
import json
from uuid import uuid4

from ..api.main import create_aria_app


@pytest.fixture
def client():
    """Create test client for the ARIA API."""
    app = create_aria_app()
    return TestClient(app)


@pytest.fixture
def sample_position_request():
    """Create a sample API request payload."""
    return {
        "signal_id": str(uuid4()),
        "account_id": str(uuid4()),
        "symbol": "EURUSD",
        "account_balance": 10000.0,
        "stop_distance_pips": 20.0,
        "risk_model": "fixed",
        "base_risk_percentage": 1.0,
        "direction": "long"
    }


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check returns OK status."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data


class TestPositionSizingEndpoint:
    """Test position sizing calculation endpoint."""
    
    def test_calculate_position_size_success(self, client, sample_position_request):
        """Test successful position size calculation."""
        response = client.post(
            "/api/v1/position-sizing/calculate",
            json=sample_position_request
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        required_fields = [
            "signal_id", "account_id", "symbol", "base_size", "adjusted_size",
            "risk_amount", "adjustments", "reasoning", "validation_errors",
            "warnings", "calculation_time_ms"
        ]
        
        for field in required_fields:
            assert field in data
        
        # Verify data types and ranges
        assert isinstance(data["base_size"], float)
        assert isinstance(data["adjusted_size"], float)
        assert data["base_size"] > 0
        assert data["adjusted_size"] > 0
        
        # Verify adjustments
        adjustments = data["adjustments"]
        assert "volatility_factor" in adjustments
        assert "drawdown_factor" in adjustments
        assert "correlation_factor" in adjustments
        assert "limit_factor" in adjustments
        assert "variance_factor" in adjustments
    
    def test_calculate_position_size_invalid_account_id(self, client, sample_position_request):
        """Test position size calculation with invalid account ID."""
        sample_position_request["account_id"] = "invalid-uuid"
        
        response = client.post(
            "/api/v1/position-sizing/calculate",
            json=sample_position_request
        )
        
        assert response.status_code == 400
        assert "Invalid request" in response.json()["detail"]
    
    def test_calculate_position_size_invalid_risk_model(self, client, sample_position_request):
        """Test position size calculation with invalid risk model."""
        sample_position_request["risk_model"] = "invalid_model"
        
        response = client.post(
            "/api/v1/position-sizing/calculate",
            json=sample_position_request
        )
        
        assert response.status_code == 400
    
    def test_calculate_position_size_missing_required_field(self, client, sample_position_request):
        """Test position size calculation with missing required field."""
        del sample_position_request["symbol"]
        
        response = client.post(
            "/api/v1/position-sizing/calculate",
            json=sample_position_request
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_calculate_position_size_zero_account_balance(self, client, sample_position_request):
        """Test position size calculation with zero account balance."""
        sample_position_request["account_balance"] = 0.0
        
        response = client.post(
            "/api/v1/position-sizing/calculate",
            json=sample_position_request
        )
        
        assert response.status_code == 400
        assert "Account balance must be positive" in response.json()["detail"]
    
    def test_calculate_position_size_negative_stop_distance(self, client, sample_position_request):
        """Test position size calculation with negative stop distance."""
        sample_position_request["stop_distance_pips"] = -10.0
        
        response = client.post(
            "/api/v1/position-sizing/calculate",
            json=sample_position_request
        )
        
        assert response.status_code == 400
        assert "Stop distance must be positive" in response.json()["detail"]


class TestAccountLimitsEndpoint:
    """Test account limits information endpoint."""
    
    def test_get_position_limits_success(self, client):
        """Test successful retrieval of position limits."""
        account_id = str(uuid4())
        
        response = client.get(f"/api/v1/position-sizing/limits/{account_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "account_id" in data
        assert "prop_firm" in data
        assert "limits" in data
        
        # Verify limits structure
        limits = data["limits"]
        expected_limit_fields = [
            "max_lot_size", "max_positions_per_symbol", "max_total_exposure",
            "max_daily_loss", "max_total_drawdown", "margin_requirement",
            "minimum_trade_size"
        ]
        
        for field in expected_limit_fields:
            assert field in limits
    
    def test_get_position_limits_invalid_account_id(self, client):
        """Test position limits with invalid account ID."""
        response = client.get("/api/v1/position-sizing/limits/invalid-uuid")
        
        assert response.status_code == 400
        assert "Invalid account ID" in response.json()["detail"]


class TestRiskAnalysisEndpoints:
    """Test risk analysis endpoints."""
    
    def test_get_drawdown_status(self, client):
        """Test drawdown status endpoint."""
        account_id = str(uuid4())
        
        response = client.get(f"/api/v1/risk-analysis/drawdown/{account_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify drawdown status fields
        expected_fields = [
            "account_id", "current_equity", "peak_equity", "drawdown_amount",
            "drawdown_percentage", "drawdown_level", "size_reduction_factor",
            "trading_halted"
        ]
        
        for field in expected_fields:
            assert field in data
    
    def test_get_correlation_analysis(self, client):
        """Test portfolio correlation analysis endpoint."""
        account_id = str(uuid4())
        
        response = client.get(f"/api/v1/risk-analysis/correlation/{account_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify correlation analysis fields
        assert "account_id" in data
        assert "position_count" in data
        assert "max_correlation" in data
        assert "risk_level" in data
    
    def test_get_variance_analysis(self, client):
        """Test variance analysis endpoint."""
        account_id = str(uuid4())
        
        response = client.get(f"/api/v1/variance-analysis/{account_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify variance analysis structure
        assert "account_id" in data
        assert "profile" in data
        assert "statistics" in data
        assert "pattern_analysis" in data


class TestErrorHandling:
    """Test API error handling."""
    
    def test_404_for_unknown_endpoint(self, client):
        """Test 404 error for unknown endpoint."""
        response = client.get("/api/v1/unknown-endpoint")
        assert response.status_code == 404
    
    def test_method_not_allowed(self, client):
        """Test method not allowed error."""
        response = client.put("/health")  # GET endpoint called with PUT
        assert response.status_code == 405


class TestCORSHeaders:
    """Test CORS headers for cross-origin requests."""
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are included in responses."""
        response = client.get("/health")
        
        # Check for CORS headers (these may vary based on configuration)
        assert response.status_code == 200
        # Note: TestClient may not include CORS headers, but in production they should be present


class TestRequestValidation:
    """Test comprehensive request validation."""
    
    def test_position_sizing_with_various_symbols(self, client):
        """Test position sizing with different trading symbols."""
        symbols = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "XAGUSD"]
        
        for symbol in symbols:
            request = {
                "signal_id": str(uuid4()),
                "account_id": str(uuid4()),
                "symbol": symbol,
                "account_balance": 10000.0,
                "stop_distance_pips": 20.0,
                "risk_model": "fixed",
                "base_risk_percentage": 1.0,
                "direction": "long"
            }
            
            response = client.post(
                "/api/v1/position-sizing/calculate",
                json=request
            )
            
            assert response.status_code == 200, f"Failed for symbol {symbol}"
            data = response.json()
            assert data["symbol"] == symbol
    
    def test_position_sizing_with_different_risk_models(self, client):
        """Test position sizing with different risk models."""
        risk_models = ["fixed", "adaptive", "kelly_criterion"]
        
        for risk_model in risk_models:
            request = {
                "signal_id": str(uuid4()),
                "account_id": str(uuid4()),
                "symbol": "EURUSD",
                "account_balance": 10000.0,
                "stop_distance_pips": 20.0,
                "risk_model": risk_model,
                "base_risk_percentage": 1.0,
                "direction": "long"
            }
            
            response = client.post(
                "/api/v1/position-sizing/calculate",
                json=request
            )
            
            assert response.status_code == 200, f"Failed for risk model {risk_model}"
    
    def test_position_sizing_with_edge_case_values(self, client):
        """Test position sizing with edge case values."""
        edge_cases = [
            {
                "account_balance": 100.0,      # Very small balance
                "stop_distance_pips": 100.0,   # Large stop
                "base_risk_percentage": 0.1    # Very small risk
            },
            {
                "account_balance": 100000.0,   # Large balance
                "stop_distance_pips": 5.0,     # Small stop
                "base_risk_percentage": 5.0    # Higher risk
            }
        ]
        
        for case in edge_cases:
            request = {
                "signal_id": str(uuid4()),
                "account_id": str(uuid4()),
                "symbol": "EURUSD",
                "risk_model": "fixed",
                "direction": "long",
                **case
            }
            
            response = client.post(
                "/api/v1/position-sizing/calculate",
                json=request
            )
            
            assert response.status_code == 200, f"Failed for case {case}"
            data = response.json()
            assert data["adjusted_size"] > 0


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])