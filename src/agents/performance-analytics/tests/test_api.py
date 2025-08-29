"""
Tests for Performance Analytics API
===================================

Test suite for validating the performance analytics API endpoints,
data models, and business logic.
"""

import pytest
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the FastAPI app
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from api.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_realtime_request():
    """Sample request data for real-time P&L endpoint."""
    return {
        "accountId": "test_account_001",
        "agentId": "market_analysis"
    }


@pytest.fixture
def sample_analytics_query():
    """Sample analytics query request."""
    return {
        "accountIds": ["test_account_001", "test_account_002"],
        "startDate": "2024-01-01",
        "endDate": "2024-01-31",
        "granularity": "daily",
        "metrics": ["pnl", "sharpe_ratio", "drawdown"]
    }


@pytest.fixture
def sample_compliance_request():
    """Sample compliance report request."""
    return {
        "accountIds": ["test_account_001", "test_account_002"],
        "startDate": "2024-01-01", 
        "endDate": "2024-01-31",
        "reportType": "standard"
    }


class TestHealthEndpoint:
    """Test suite for health check endpoint."""

    def test_health_check_success(self, client):
        """Test health check returns healthy status."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"

    def test_health_check_response_format(self, client):
        """Test health check response format."""
        response = client.get("/health")
        data = response.json()
        
        # Validate response structure
        required_fields = ["status", "timestamp", "version"]
        for field in required_fields:
            assert field in data
        
        # Validate timestamp format
        timestamp = data["timestamp"]
        assert isinstance(timestamp, str)
        # Should be valid ISO format
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))


class TestRealtimePnLEndpoint:
    """Test suite for real-time P&L endpoint."""

    def test_realtime_pnl_success(self, client, sample_realtime_request):
        """Test successful real-time P&L request."""
        response = client.post("/api/analytics/realtime-pnl", json=sample_realtime_request)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        required_fields = [
            "accountId", "agentId", "currentPnL", "realizedPnL", "unrealizedPnL",
            "dailyPnL", "weeklyPnL", "monthlyPnL", "trades", "lastUpdate",
            "highWaterMark", "currentDrawdown"
        ]
        for field in required_fields:
            assert field in data
        
        # Validate data types
        assert isinstance(data["currentPnL"], (int, float))
        assert isinstance(data["trades"], list)
        assert data["accountId"] == sample_realtime_request["accountId"]
        assert data["agentId"] == sample_realtime_request["agentId"]

    def test_realtime_pnl_without_agent(self, client):
        """Test real-time P&L request without agent filter."""
        request_data = {"accountId": "test_account_001"}
        response = client.post("/api/analytics/realtime-pnl", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["agentId"] == "all"

    def test_realtime_pnl_invalid_account(self, client):
        """Test real-time P&L with invalid account ID."""
        request_data = {"accountId": ""}
        response = client.post("/api/analytics/realtime-pnl", json=request_data)
        
        # Should still work with empty string (handled by mock data generator)
        assert response.status_code == 200

    def test_realtime_pnl_trade_structure(self, client, sample_realtime_request):
        """Test trade breakdown structure in P&L response."""
        response = client.post("/api/analytics/realtime-pnl", json=sample_realtime_request)
        data = response.json()
        
        if data["trades"]:
            trade = data["trades"][0]
            required_trade_fields = [
                "tradeId", "symbol", "entryTime", "entryPrice", "size",
                "direction", "pnl", "pnlPercent", "commission", "netPnL",
                "agentId", "agentName"
            ]
            for field in required_trade_fields:
                assert field in trade


class TestTradeBreakdownEndpoint:
    """Test suite for trade breakdown endpoint."""

    def test_trade_breakdown_success(self, client):
        """Test successful trade breakdown request."""
        response = client.post("/api/analytics/trades?accountId=test_account_001")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_trade_breakdown_with_agent_filter(self, client):
        """Test trade breakdown with agent filter."""
        response = client.post("/api/analytics/trades?accountId=test_account_001&agentId=market_analysis")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_trade_breakdown_with_date_range(self, client):
        """Test trade breakdown with date range filter."""
        date_range = {
            "start": "2024-01-01T00:00:00",
            "end": "2024-01-31T23:59:59"
        }
        response = client.post(
            "/api/analytics/trades?accountId=test_account_001",
            json={"dateRange": date_range}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestHistoricalPerformanceEndpoint:
    """Test suite for historical performance endpoint."""

    def test_historical_performance_success(self, client, sample_analytics_query):
        """Test successful historical performance request."""
        response = client.post("/api/analytics/historical", json=sample_analytics_query)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "daily" in data
        assert "weekly" in data
        assert "monthly" in data
        assert isinstance(data["daily"], list)
        assert isinstance(data["weekly"], list)
        assert isinstance(data["monthly"], list)

    def test_historical_performance_data_structure(self, client, sample_analytics_query):
        """Test historical performance data structure."""
        response = client.post("/api/analytics/historical", json=sample_analytics_query)
        data = response.json()
        
        if data["daily"]:
            daily_item = data["daily"][0]
            required_fields = [
                "period", "totalPnL", "trades", "winRate", 
                "sharpeRatio", "maxDrawdown", "volume"
            ]
            for field in required_fields:
                assert field in daily_item

    def test_historical_performance_invalid_date_range(self, client):
        """Test historical performance with invalid date range."""
        invalid_query = {
            "accountIds": ["test_account_001"],
            "startDate": "2024-12-31",  # End before start
            "endDate": "2024-01-01",
            "granularity": "daily"
        }
        
        # API should handle this gracefully
        response = client.post("/api/analytics/historical", json=invalid_query)
        assert response.status_code in [200, 400]  # Either works or proper error


class TestRiskMetricsEndpoint:
    """Test suite for risk metrics endpoint."""

    def test_risk_metrics_success(self, client):
        """Test successful risk metrics calculation."""
        response = client.post(
            "/api/analytics/risk-metrics?accountId=test_account_001&startDate=2024-01-01&endDate=2024-01-31"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        risk_fields = [
            "sharpeRatio", "sortinoRatio", "calmarRatio", "maxDrawdown",
            "volatility", "winLossRatio", "profitFactor", "expectancy"
        ]
        for field in risk_fields:
            assert field in data
            assert isinstance(data[field], (int, float))

    def test_risk_metrics_data_ranges(self, client):
        """Test risk metrics data are within reasonable ranges."""
        response = client.post(
            "/api/analytics/risk-metrics?accountId=test_account_001&startDate=2024-01-01&endDate=2024-01-31"
        )
        data = response.json()
        
        # Basic sanity checks
        assert -10 <= data["sharpeRatio"] <= 10  # Reasonable Sharpe ratio range
        assert 0 <= data["winLossRatio"] <= 1    # Win rate should be between 0 and 1
        assert data["profitFactor"] >= 0         # Profit factor should be non-negative

    def test_risk_metrics_missing_parameters(self, client):
        """Test risk metrics with missing parameters."""
        response = client.post("/api/analytics/risk-metrics?accountId=test_account_001")
        assert response.status_code == 422  # Validation error


class TestAgentComparisonEndpoint:
    """Test suite for agent comparison endpoint."""

    def test_agent_comparison_success(self, client):
        """Test successful agent comparison request."""
        request_data = {
            "accountIds": ["test_account_001", "test_account_002"],
            "startDate": "2024-01-01",
            "endDate": "2024-01-31"
        }
        response = client.post("/api/analytics/agents", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_agent_comparison_data_structure(self, client):
        """Test agent comparison data structure."""
        request_data = {
            "accountIds": ["test_account_001"],
            "startDate": "2024-01-01", 
            "endDate": "2024-01-31"
        }
        response = client.post("/api/analytics/agents", json=request_data)
        data = response.json()
        
        if data:
            agent = data[0]
            required_fields = [
                "agentId", "agentName", "agentType", "totalTrades",
                "winRate", "totalPnL", "sharpeRatio", "contribution"
            ]
            for field in required_fields:
                assert field in agent

    def test_agent_comparison_performance_metrics(self, client):
        """Test agent comparison performance metrics."""
        request_data = {
            "accountIds": ["test_account_001"],
            "startDate": "2024-01-01",
            "endDate": "2024-01-31"
        }
        response = client.post("/api/analytics/agents", json=request_data)
        data = response.json()
        
        for agent in data:
            # Validate performance metrics
            assert 0 <= agent["winRate"] <= 100
            assert 0 <= agent["contribution"] <= 100
            assert 0 <= agent["consistency"] <= 100
            assert 0 <= agent["reliability"] <= 100


class TestComplianceReportEndpoint:
    """Test suite for compliance report endpoint."""

    def test_compliance_report_success(self, client, sample_compliance_request):
        """Test successful compliance report generation."""
        response = client.post("/api/analytics/compliance/report", json=sample_compliance_request)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        required_fields = [
            "reportId", "generatedAt", "period", "accounts",
            "aggregateMetrics", "violations", "auditTrail", 
            "regulatoryMetrics", "signature"
        ]
        for field in required_fields:
            assert field in data

    def test_compliance_report_id_uniqueness(self, client, sample_compliance_request):
        """Test compliance report IDs are unique."""
        response1 = client.post("/api/analytics/compliance/report", json=sample_compliance_request)
        response2 = client.post("/api/analytics/compliance/report", json=sample_compliance_request)
        
        data1 = response1.json()
        data2 = response2.json()
        
        assert data1["reportId"] != data2["reportId"]

    def test_compliance_report_account_data(self, client, sample_compliance_request):
        """Test compliance report account data structure."""
        response = client.post("/api/analytics/compliance/report", json=sample_compliance_request)
        data = response.json()
        
        if data["accounts"]:
            account = data["accounts"][0]
            required_fields = [
                "accountId", "propFirm", "startBalance", "endBalance",
                "maxDrawdown", "tradingDays", "averageDailyVolume", "violations"
            ]
            for field in required_fields:
                assert field in account

    def test_compliance_report_different_types(self, client):
        """Test compliance reports for different report types."""
        base_request = {
            "accountIds": ["test_account_001"],
            "startDate": "2024-01-01",
            "endDate": "2024-01-31"
        }
        
        report_types = ["standard", "detailed", "executive", "regulatory"]
        
        for report_type in report_types:
            request_data = {**base_request, "reportType": report_type}
            response = client.post("/api/analytics/compliance/report", json=request_data)
            assert response.status_code == 200


class TestExportEndpoint:
    """Test suite for export endpoint."""

    def test_export_json_success(self, client):
        """Test successful JSON export."""
        report_data = {"test": "data"}
        response = client.post("/api/analytics/export?format=json", json={"report": report_data})
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "downloadUrl" in data

    def test_export_different_formats(self, client):
        """Test export with different formats."""
        report_data = {"test": "data"}
        formats = ["json", "pdf", "csv", "excel"]
        
        for fmt in formats:
            response = client.post(f"/api/analytics/export?format={fmt}", json={"report": report_data})
            assert response.status_code == 200

    def test_export_invalid_format(self, client):
        """Test export with invalid format."""
        report_data = {"test": "data"}
        response = client.post("/api/analytics/export?format=invalid", json={"report": report_data})
        assert response.status_code == 400


class TestErrorHandling:
    """Test suite for error handling scenarios."""

    def test_malformed_json(self, client):
        """Test handling of malformed JSON requests."""
        response = client.post(
            "/api/analytics/realtime-pnl",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_missing_required_fields(self, client):
        """Test handling of missing required fields."""
        response = client.post("/api/analytics/realtime-pnl", json={})
        assert response.status_code == 422

    def test_invalid_data_types(self, client):
        """Test handling of invalid data types."""
        invalid_request = {
            "accountId": 123,  # Should be string
            "agentId": ["invalid"]  # Should be string or null
        }
        response = client.post("/api/analytics/realtime-pnl", json=invalid_request)
        assert response.status_code == 422


class TestPerformanceAndScaling:
    """Test suite for performance and scaling considerations."""

    def test_response_time_realtime_pnl(self, client, sample_realtime_request):
        """Test response time for real-time P&L endpoint."""
        import time
        
        start_time = time.time()
        response = client.post("/api/analytics/realtime-pnl", json=sample_realtime_request)
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 5.0  # Should respond within 5 seconds

    def test_large_date_range_handling(self, client):
        """Test handling of large date ranges."""
        large_range_query = {
            "accountIds": ["test_account_001"],
            "startDate": "2020-01-01",  # 4+ years of data
            "endDate": "2024-12-31",
            "granularity": "daily"
        }
        
        response = client.post("/api/analytics/historical", json=large_range_query)
        assert response.status_code == 200
        
        # Should handle large responses gracefully
        data = response.json()
        assert isinstance(data, dict)

    def test_multiple_accounts_handling(self, client):
        """Test handling of multiple accounts."""
        many_accounts_query = {
            "accountIds": [f"account_{i:03d}" for i in range(1, 21)],  # 20 accounts
            "startDate": "2024-01-01",
            "endDate": "2024-01-31"
        }
        
        response = client.post("/api/analytics/agents", json=many_accounts_query)
        assert response.status_code == 200


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])