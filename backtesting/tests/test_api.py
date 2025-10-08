"""
Tests for Historical Data API Endpoints
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import pandas as pd

from app.main import app
from app.database import db
from app.models.market_data import MarketCandleSchema


class TestHistoricalDataAPI:
    """Test API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "endpoints" in data

    @pytest.mark.asyncio
    async def test_get_market_data_endpoint(self, client, sample_candles):
        """Test market data retrieval endpoint"""
        # Mock repository
        with patch(
            "app.api.historical_data.HistoricalDataRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()

            # Create DataFrame from sample candles
            df = pd.DataFrame(
                {
                    "timestamp": [c.timestamp for c in sample_candles[:10]],
                    "open": [c.open for c in sample_candles[:10]],
                    "high": [c.high for c in sample_candles[:10]],
                    "low": [c.low for c in sample_candles[:10]],
                    "close": [c.close for c in sample_candles[:10]],
                    "volume": [c.volume for c in sample_candles[:10]],
                }
            )
            df.set_index("timestamp", inplace=True)

            mock_repo.get_market_data.return_value = df
            mock_repo_class.return_value = mock_repo

            response = client.get(
                "/api/historical/market-data",
                params={
                    "instrument": "EUR_USD",
                    "start_date": "2024-01-01T00:00:00",
                    "end_date": "2024-01-02T00:00:00",
                    "timeframe": "H1",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert "count" in data
            assert data["count"] == 10

    def test_get_market_data_missing_params(self, client):
        """Test market data endpoint with missing parameters"""
        response = client.get("/api/historical/market-data")
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_data_statistics_endpoint(self, client):
        """Test data statistics endpoint"""
        with patch(
            "app.api.historical_data.HistoricalDataRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_data_statistics.return_value = {
                "instrument": "EUR_USD",
                "timeframe": "H1",
                "total_candles": 1000,
                "earliest_date": "2024-01-01T00:00:00",
                "latest_date": "2024-02-01T00:00:00",
                "coverage_days": 31,
            }
            mock_repo_class.return_value = mock_repo

            response = client.get(
                "/api/historical/statistics/EUR_USD", params={"timeframe": "H1"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["instrument"] == "EUR_USD"
            assert data["total_candles"] == 1000

    @pytest.mark.asyncio
    async def test_validate_quality_endpoint(self, client, sample_candles):
        """Test data quality validation endpoint"""
        with patch(
            "app.api.historical_data.HistoricalDataRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()

            # Create DataFrame
            df = pd.DataFrame(
                {
                    "timestamp": [c.timestamp for c in sample_candles[:50]],
                    "open": [c.open for c in sample_candles[:50]],
                    "high": [c.high for c in sample_candles[:50]],
                    "low": [c.low for c in sample_candles[:50]],
                    "close": [c.close for c in sample_candles[:50]],
                    "volume": [c.volume for c in sample_candles[:50]],
                }
            )
            df.set_index("timestamp", inplace=True)

            mock_repo.get_market_data.return_value = df
            mock_repo_class.return_value = mock_repo

            response = client.post(
                "/api/historical/validate-quality",
                params={
                    "instrument": "EUR_USD",
                    "start_date": "2024-01-01T00:00:00",
                    "end_date": "2024-01-03T00:00:00",
                    "timeframe": "H1",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "quality_score" in data
            assert "completeness_score" in data
            assert "total_candles" in data
