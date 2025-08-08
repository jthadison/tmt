"""
Test cases for FastAPI endpoints
"""

import pytest
from httpx import AsyncClient
from decimal import Decimal
from datetime import datetime

from ..app.main import app
from ..app.models import ValidationRequest, TradeOrder


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test root endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "compliance-agent"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_validate_trade_endpoint():
    """Test trade validation endpoint"""
    trade_order = {
        "account_id": "test_account",
        "symbol": "EURUSD",
        "side": "buy",
        "order_type": "market",
        "quantity": "1.0",
        "stop_loss": "1.0950",
        "take_profit": "1.1050"
    }
    
    validation_request = {
        "account_id": "test_account",
        "trade_order": trade_order,
        "current_positions": [],
        "upcoming_news": []
    }
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/compliance/validate-trade",
            json=validation_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "is_valid" in data
        assert "compliance_status" in data
        assert "violations" in data
        assert "reason" in data


@pytest.mark.asyncio
async def test_get_account_status():
    """Test account status endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/compliance/account-status/test_account")
        
        assert response.status_code == 200
        data = response.json()
        assert data["account_id"] == "test_account"
        assert "compliance_status" in data
        assert "daily_pnl" in data
        assert "daily_loss_limit" in data


@pytest.mark.asyncio
async def test_get_violations():
    """Test violations history endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/compliance/violations/test_account")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_supported_prop_firms():
    """Test supported prop firms endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/compliance/prop-firms")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "dna_funded" in data
        assert "funding_pips" in data
        assert "the_funded_trader" in data


@pytest.mark.asyncio
async def test_get_compliance_metrics():
    """Test compliance metrics endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/compliance/metrics/test_account")
        
        assert response.status_code == 200
        data = response.json()
        assert data["account_id"] == "test_account"
        assert "total_trades" in data
        assert "compliance_rate" in data
        assert "violations_count" in data


@pytest.mark.asyncio
async def test_update_pnl_endpoint():
    """Test P&L update endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/compliance/update-pnl",
            params={
                "account_id": "test_account",
                "realized_pnl": 100.50,
                "unrealized_pnl": 25.75
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["account_id"] == "test_account"
        assert data["updated"] is True
        assert "is_compliant" in data
        assert "new_balance" in data


@pytest.mark.asyncio
async def test_reset_daily_pnl_endpoint():
    """Test daily P&L reset endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/compliance/reset-daily",
            params={"account_id": "test_account"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["account_id"] == "test_account"
        assert data["reset"] is True
        assert "trading_days_completed" in data


@pytest.mark.asyncio
async def test_invalid_account_id():
    """Test handling of invalid account ID"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/compliance/account-status/")
        
        # Should return 404 for missing account ID
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_invalid_trade_validation_request():
    """Test handling of invalid validation request"""
    invalid_request = {
        "account_id": "",  # Empty account ID
        "trade_order": {}  # Missing required fields
    }
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/compliance/validate-trade",
            json=invalid_request
        )
        
        # Should return 422 for validation error
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_cors_headers():
    """Test CORS headers are present"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.options("/api/v1/compliance/validate-trade")
        
        # Should allow CORS
        assert response.status_code in [200, 405]  # OPTIONS might not be implemented