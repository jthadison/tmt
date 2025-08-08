"""Tests for main FastAPI application."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from uuid import uuid4
import json

from fastapi.testclient import TestClient
from ..app.main import app


class TestMainAPI:
    """Test cases for main FastAPI application."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def sample_account_ids(self):
        """Sample account IDs for testing."""
        return [str(uuid4()), str(uuid4())]
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "anti-correlation-engine"
        assert "timestamp" in data
    
    def test_calculate_correlation(self, client, sample_account_ids):
        """Test correlation calculation endpoint."""
        request_data = {
            "account_ids": sample_account_ids,
            "time_window": 3600,
            "include_components": True
        }
        
        with patch('..app.main.services') as mock_services:
            mock_correlation_monitor = Mock()
            mock_correlation_monitor.calculate_correlation = AsyncMock(
                return_value=(0.75, 0.02, {"position_correlation": (0.8, 0.01)})
            )
            mock_services.__getitem__.return_value = mock_correlation_monitor
            
            response = client.post("/api/v1/correlation/calculate", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["correlation_coefficient"] == 0.75
            assert data["p_value"] == 0.02
            assert "components" in data
    
    def test_calculate_correlation_invalid_accounts(self, client):
        """Test correlation calculation with invalid number of accounts."""
        request_data = {
            "account_ids": [str(uuid4())],  # Only one account
            "time_window": 3600
        }
        
        response = client.post("/api/v1/correlation/calculate", json=request_data)
        assert response.status_code == 400
        assert "Exactly 2 account IDs required" in response.json()["detail"]
    
    def test_get_correlation_matrix(self, client, sample_account_ids):
        """Test correlation matrix endpoint."""
        account_ids = sample_account_ids + [str(uuid4())]
        
        with patch('..app.main.services') as mock_services:
            mock_correlation_monitor = Mock()
            mock_matrix_result = Mock()
            mock_matrix_result.correlation_matrix = [[1.0, 0.6, 0.4], [0.6, 1.0, 0.7], [0.4, 0.7, 1.0]]
            mock_matrix_result.account_ids = account_ids
            mock_correlation_monitor.update_correlation_matrix = AsyncMock(
                return_value=mock_matrix_result
            )
            mock_services.__getitem__.return_value = mock_correlation_monitor
            
            response = client.post(
                "/api/v1/correlation/matrix",
                params={"time_window": 3600},
                json=account_ids
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["correlation_matrix"]) == 3
    
    def test_get_active_alerts(self, client):
        """Test getting active alerts."""
        with patch('..app.main.services') as mock_services:
            mock_alert_manager = Mock()
            mock_alerts = [
                Mock(
                    alert_id=uuid4(),
                    account_1_id=uuid4(),
                    account_2_id=uuid4(),
                    correlation_coefficient=0.8,
                    severity="warning",
                    alert_time=datetime.utcnow(),
                    message="High correlation detected"
                )
            ]
            mock_alert_manager.get_active_alerts = AsyncMock(return_value=mock_alerts)
            mock_services.__getitem__.return_value = mock_alert_manager
            
            response = client.get("/api/v1/alerts/active")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["correlation_coefficient"] == 0.8
    
    def test_resolve_alert(self, client):
        """Test resolving an alert."""
        alert_id = str(uuid4())
        
        with patch('..app.main.services') as mock_services:
            mock_alert_manager = Mock()
            mock_alert_manager.resolve_alert = AsyncMock(return_value=True)
            mock_services.__getitem__.return_value = mock_alert_manager
            
            response = client.post(
                f"/api/v1/alerts/{alert_id}/resolve",
                params={
                    "resolution_action": "Manual intervention",
                    "correlation_after": 0.4
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Alert resolved successfully"
    
    def test_resolve_nonexistent_alert(self, client):
        """Test resolving non-existent alert."""
        alert_id = str(uuid4())
        
        with patch('..app.main.services') as mock_services:
            mock_alert_manager = Mock()
            mock_alert_manager.resolve_alert = AsyncMock(return_value=False)
            mock_services.__getitem__.return_value = mock_alert_manager
            
            response = client.post(
                f"/api/v1/alerts/{alert_id}/resolve",
                params={"resolution_action": "Manual intervention"}
            )
            
            assert response.status_code == 404
    
    def test_auto_adjust_positions(self, client, sample_account_ids):
        """Test automatic position adjustment."""
        account1_id, account2_id = sample_account_ids
        
        with patch('..app.main.services') as mock_services:
            mock_position_adjuster = Mock()
            mock_adjustments = [
                {
                    "adjustment_id": str(uuid4()),
                    "adjustment_type": "gradual_reduction",
                    "size_change": -0.2,
                    "effectiveness": 0.7
                }
            ]
            mock_position_adjuster.adjust_positions_for_correlation = AsyncMock(
                return_value=mock_adjustments
            )
            mock_services.__getitem__.return_value = mock_position_adjuster
            
            response = client.post(
                "/api/v1/adjustments/auto-adjust",
                params={
                    "account1_id": account1_id,
                    "account2_id": account2_id,
                    "current_correlation": 0.8,
                    "target_correlation": 0.5
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["adjustment_type"] == "gradual_reduction"
    
    def test_calculate_execution_delay(self, client):
        """Test execution delay calculation."""
        request_data = {
            "account_id": str(uuid4()),
            "signal_priority": "normal",
            "symbol": "EURUSD",
            "market_session": "london",
            "base_delay_range": [5, 25]
        }
        
        with patch('..app.main.services') as mock_services:
            mock_execution_delay = Mock()
            mock_response = Mock()
            mock_response.account_id = request_data["account_id"]
            mock_response.calculated_delay = 15.3
            mock_response.session_adjustment = 1.2
            mock_execution_delay.calculate_execution_delay = AsyncMock(
                return_value=mock_response
            )
            mock_services.__getitem__.return_value = mock_execution_delay
            
            response = client.post("/api/v1/execution/calculate-delay", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["calculated_delay"] == 15.3
    
    def test_calculate_size_variance(self, client):
        """Test size variance calculation."""
        request_data = {
            "account_id": str(uuid4()),
            "base_size": 1.0,
            "symbol": "EURUSD",
            "variance_range": [0.05, 0.15]
        }
        
        with patch('..app.main.services') as mock_services:
            mock_size_variance = Mock()
            mock_response = Mock()
            mock_response.account_id = request_data["account_id"]
            mock_response.original_size = 1.0
            mock_response.adjusted_size = 1.1
            mock_response.variance_percentage = 10.0
            mock_size_variance.calculate_size_variance = AsyncMock(
                return_value=mock_response
            )
            mock_services.__getitem__.return_value = mock_size_variance
            
            response = client.post("/api/v1/size/calculate-variance", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["adjusted_size"] == 1.1
            assert data["variance_percentage"] == 10.0
    
    def test_generate_daily_report(self, client, sample_account_ids):
        """Test daily report generation."""
        report_date = datetime.utcnow()
        
        with patch('..app.main.services') as mock_services:
            mock_correlation_reporter = Mock()
            mock_report = Mock()
            mock_report.report_date = report_date
            mock_report.summary = {"total_accounts": 2}
            mock_report.correlation_matrix = [[1.0, 0.6], [0.6, 1.0]]
            mock_report.warnings = []
            mock_report.adjustments = {}
            mock_report.recommendations = ["Continue monitoring"]
            mock_correlation_reporter.generate_daily_report = AsyncMock(
                return_value=mock_report
            )
            mock_services.__getitem__.return_value = mock_correlation_reporter
            
            response = client.post(
                "/api/v1/reports/daily",
                params={
                    "report_date": report_date.isoformat(),
                    "report_type": "detailed"
                },
                json=sample_account_ids
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["summary"]["total_accounts"] == 2
    
    def test_export_report_csv(self, client, sample_account_ids):
        """Test CSV report export."""
        report_date = datetime.utcnow()
        
        with patch('..app.main.services') as mock_services:
            mock_correlation_reporter = Mock()
            mock_report = Mock()
            mock_correlation_reporter.generate_daily_report = AsyncMock(
                return_value=mock_report
            )
            mock_correlation_reporter.export_report_csv = AsyncMock(
                return_value="CSV content here"
            )
            mock_services.__getitem__.return_value = mock_correlation_reporter
            
            response = client.post(
                "/api/v1/reports/export/csv",
                params={"report_date": report_date.isoformat()},
                json=sample_account_ids
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["content"] == "CSV content here"
            assert data["content_type"] == "text/csv"
            assert "correlation_report_" in data["filename"]
    
    def test_start_monitoring(self, client, sample_account_ids):
        """Test starting real-time monitoring."""
        with patch('..app.main.services') as mock_services:
            mock_correlation_monitor = Mock()
            mock_position_adjuster = Mock()
            mock_services.__getitem__.side_effect = [mock_correlation_monitor, mock_position_adjuster]
            
            response = client.post(
                "/api/v1/monitoring/start",
                json=sample_account_ids
            )
            
            assert response.status_code == 200
            data = response.json()
            assert f"Started monitoring for {len(sample_account_ids)} accounts" in data["message"]
    
    def test_get_correlation_heatmap(self, client, sample_account_ids):
        """Test correlation heatmap data."""
        account_ids = sample_account_ids + [str(uuid4())]
        
        with patch('..app.main.services') as mock_services:
            mock_alert_manager = Mock()
            mock_heatmap_data = {
                "matrix": [[1.0, 0.6, 0.4], [0.6, 1.0, 0.7], [0.4, 0.7, 1.0]],
                "accounts": account_ids,
                "timestamp": datetime.utcnow().isoformat()
            }
            mock_alert_manager.generate_correlation_heatmap_data = AsyncMock(
                return_value=mock_heatmap_data
            )
            mock_services.__getitem__.return_value = mock_alert_manager
            
            response = client.get(
                "/api/v1/alerts/heatmap",
                params={"time_window": 3600},
                json=account_ids
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "matrix" in data
            assert len(data["accounts"]) == 3
    
    def test_get_delay_statistics(self, client):
        """Test delay statistics endpoint."""
        account_id = str(uuid4())
        
        with patch('..app.main.services') as mock_services:
            mock_execution_delay = Mock()
            mock_stats = {
                "average_delay": 12.5,
                "min_delay": 5.0,
                "max_delay": 25.0,
                "total_calculations": 100
            }
            mock_execution_delay.get_delay_statistics = AsyncMock(return_value=mock_stats)
            mock_services.__getitem__.return_value = mock_execution_delay
            
            response = client.get(
                "/api/v1/execution/delay-statistics",
                params={"account_id": account_id, "hours": 24}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["average_delay"] == 12.5
            assert data["total_calculations"] == 100
    
    def test_pattern_detection(self, client, sample_account_ids):
        """Test delay pattern detection."""
        with patch('..app.main.services') as mock_services:
            mock_execution_delay = Mock()
            mock_patterns = {
                "suspicious_patterns": 2,
                "pattern_types": ["regular_spacing", "synchronized_timing"],
                "risk_score": 0.3
            }
            mock_execution_delay.detect_delay_patterns = AsyncMock(
                return_value=mock_patterns
            )
            mock_services.__getitem__.return_value = mock_execution_delay
            
            response = client.get(
                "/api/v1/execution/pattern-detection",
                params={"hours": 24},
                json=sample_account_ids
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["suspicious_patterns"] == 2
            assert data["risk_score"] == 0.3
    
    def test_cors_headers(self, client):
        """Test CORS headers are properly set."""
        response = client.options("/api/v1/correlation/calculate")
        
        # Should allow the configured origins
        assert response.status_code == 200
        # CORS headers would be tested in integration tests
    
    def test_invalid_uuid_handling(self, client):
        """Test handling of invalid UUID parameters."""
        response = client.get("/api/v1/alerts/active?account_id=invalid-uuid")
        
        # Should return 422 for invalid UUID format
        assert response.status_code == 422
    
    def test_parameter_validation(self, client):
        """Test parameter validation."""
        # Test invalid time window (too small)
        response = client.post(
            "/api/v1/correlation/matrix",
            params={"time_window": 100},  # Below minimum 300
            json=[str(uuid4()), str(uuid4())]
        )
        assert response.status_code == 422
        
        # Test invalid time window (too large)  
        response = client.post(
            "/api/v1/correlation/matrix", 
            params={"time_window": 100000},  # Above maximum 86400
            json=[str(uuid4()), str(uuid4())]
        )
        assert response.status_code == 422