"""
Integration tests for REST API endpoints and WebSocket functionality.

Tests API response formats, performance, error handling, and WebSocket communication.
"""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from fastapi.testclient import TestClient
from fastapi import status

from ..app.main import app
from ..app.models import (
    EmergencyStopRequest, BreakerLevel, TriggerReason,
    StandardAPIResponse
)


@pytest.fixture
def client():
    """Test client for FastAPI application"""
    return TestClient(app)


@pytest.fixture
def mock_components():
    """Mock all application components"""
    with patch('..app.main.breaker_manager') as mock_breaker, \
         patch('..app.main.emergency_stop_manager') as mock_emergency, \
         patch('..app.main.health_monitor') as mock_health, \
         patch('..app.main.kafka_manager') as mock_kafka, \
         patch('..app.main.websocket_manager') as mock_ws:
        
        # Configure mock breaker manager
        mock_breaker.get_all_breaker_status.return_value = {
            'agent_breakers': {},
            'account_breakers': {},
            'system_breaker': {
                'level': 'system',
                'state': 'normal',
                'triggered_at': None,
                'trigger_reason': None
            },
            'overall_healthy': True
        }
        
        # Configure mock health monitor
        mock_health.run_health_check = AsyncMock(return_value=Mock(
            cpu_usage=45.0,
            memory_usage=60.0,
            disk_usage=70.0,
            error_rate=0.02,
            response_time=75,
            active_connections=10,
            timestamp="2024-01-01T00:00:00Z"
        ))
        
        yield {
            'breaker': mock_breaker,
            'emergency': mock_emergency,
            'health': mock_health,
            'kafka': mock_kafka,
            'websocket': mock_ws
        }


@pytest.mark.integration
class TestBreakerStatusEndpoint:
    """Test /api/v1/breaker/status endpoint"""
    
    def test_get_breaker_status_success(self, client, mock_components):
        """Test successful breaker status retrieval"""
        response = client.get("/api/v1/breaker/status")
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "data" in data
        assert "error" in data
        assert "correlation_id" in data
        assert data["error"] is None
        
        # Verify response structure
        breaker_data = data["data"]
        assert "agent_breakers" in breaker_data
        assert "account_breakers" in breaker_data
        assert "system_breaker" in breaker_data
        assert "overall_status" in breaker_data
        assert "health_metrics" in breaker_data
    
    def test_get_breaker_status_correlation_id(self, client, mock_components):
        """Test breaker status endpoint includes correlation ID"""
        response = client.get("/api/v1/breaker/status")
        
        data = response.json()
        correlation_id = data["correlation_id"]
        
        assert correlation_id is not None
        assert len(correlation_id) > 0
        assert isinstance(correlation_id, str)
    
    def test_get_breaker_status_response_time(self, client, mock_components):
        """Test breaker status endpoint response time"""
        import time
        
        start_time = time.time()
        response = client.get("/api/v1/breaker/status")
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        
        assert response.status_code == status.HTTP_200_OK
        # Should be fast for status queries
        assert response_time_ms < 1000, f"Status endpoint took {response_time_ms}ms"
    
    def test_get_breaker_status_unavailable_components(self, client):
        """Test breaker status when components are unavailable"""
        # Test without mocked components (should handle gracefully)
        response = client.get("/api/v1/breaker/status")
        
        # Should return 503 when components not initialized
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@pytest.mark.integration
class TestEmergencyStopEndpoint:
    """Test /api/v1/breaker/trigger endpoint"""
    
    def test_trigger_emergency_stop_success(self, client, mock_components):
        """Test successful emergency stop trigger"""
        # Configure mock emergency stop manager
        mock_response = Mock()
        mock_response.success = True
        mock_response.level = BreakerLevel.SYSTEM
        mock_response.response_time_ms = 85
        mock_response.correlation_id = "test-correlation"
        mock_response.dict.return_value = {
            "success": True,
            "level": "system",
            "response_time_ms": 85,
            "correlation_id": "test-correlation"
        }
        
        mock_components['emergency'].execute_emergency_stop = AsyncMock(return_value=mock_response)
        
        request_data = {
            "level": "system",
            "reason": "manual_trigger",
            "details": {"test": "data"},
            "correlation_id": "test-correlation",
            "requested_by": "test_user"
        }
        
        response = client.post("/api/v1/breaker/trigger", json=request_data)
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["error"] is None
        assert data["data"]["success"] is True
        assert data["data"]["level"] == "system"
    
    def test_trigger_emergency_stop_performance(self, client, mock_components):
        """Test emergency stop trigger meets performance requirements"""
        # Configure fast mock response
        mock_response = Mock()
        mock_response.success = True
        mock_response.response_time_ms = 45
        mock_response.dict.return_value = {"success": True, "response_time_ms": 45}
        
        mock_components['emergency'].execute_emergency_stop = AsyncMock(return_value=mock_response)
        
        request_data = {
            "level": "system",
            "reason": "manual_trigger",
            "correlation_id": "perf-test"
        }
        
        import time
        start_time = time.time()
        response = client.post("/api/v1/breaker/trigger", json=request_data)
        end_time = time.time()
        
        api_response_time_ms = (end_time - start_time) * 1000
        
        assert response.status_code == status.HTTP_200_OK
        # API should add minimal overhead to emergency stop
        assert api_response_time_ms < 200, f"API took {api_response_time_ms}ms"
    
    def test_trigger_emergency_stop_invalid_data(self, client, mock_components):
        """Test emergency stop trigger with invalid data"""
        invalid_request_data = {
            "level": "invalid_level",
            "reason": "manual_trigger"
        }
        
        response = client.post("/api/v1/breaker/trigger", json=invalid_request_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_trigger_emergency_stop_missing_manager(self, client):
        """Test emergency stop trigger when manager unavailable"""
        request_data = {
            "level": "system",
            "reason": "manual_trigger",
            "correlation_id": "test-unavailable"
        }
        
        response = client.post("/api/v1/breaker/trigger", json=request_data)
        
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@pytest.mark.integration
class TestCircuitBreakerResetEndpoint:
    """Test /api/v1/breaker/reset endpoint"""
    
    def test_reset_circuit_breaker_success(self, client, mock_components):
        """Test successful circuit breaker reset"""
        mock_components['breaker'].manual_reset = AsyncMock(return_value=True)
        
        response = client.post("/api/v1/breaker/reset?level=system&identifier=system")
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["error"] is None
        assert data["data"]["success"] is True
        assert data["data"]["level"] == "system"
    
    def test_reset_circuit_breaker_failure(self, client, mock_components):
        """Test circuit breaker reset failure"""
        mock_components['breaker'].manual_reset = AsyncMock(return_value=False)
        
        response = client.post("/api/v1/breaker/reset?level=system&identifier=system")
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["data"]["success"] is False
    
    def test_reset_circuit_breaker_invalid_level(self, client, mock_components):
        """Test circuit breaker reset with invalid level"""
        response = client.post("/api/v1/breaker/reset?level=invalid&identifier=system")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.integration
class TestHealthEndpoints:
    """Test health-related endpoints"""
    
    def test_health_endpoint(self, client):
        """Test basic health check endpoint"""
        response = client.get("/health")
        
        # Should work even without full component initialization
        assert response.status_code in [200, 503]
    
    def test_health_summary_endpoint(self, client, mock_components):
        """Test health summary endpoint"""
        mock_components['health'].get_health_summary.return_value = {
            "monitoring_active": True,
            "callback_count": 1,
            "error_types": [],
            "total_errors": 0
        }
        
        response = client.get("/api/v1/health/summary")
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "data" in data
        assert data["data"]["monitoring_active"] is True


@pytest.mark.integration
class TestWebSocketEndpoint:
    """Test WebSocket endpoint functionality"""
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self, mock_components):
        """Test WebSocket connection establishment"""
        from fastapi.testclient import TestClient
        from ..app.main import app
        
        # This is a simplified test - full WebSocket testing requires more setup
        client = TestClient(app)
        
        # Test that the endpoint exists
        # Full WebSocket testing would require websocket test client
        response = client.get("/ws/breaker/status")
        assert response.status_code == status.HTTP_426_UPGRADE_REQUIRED
    
    def test_websocket_endpoint_exists(self, client):
        """Test WebSocket endpoint route exists"""
        # WebSocket endpoints return 426 when accessed via HTTP
        response = client.get("/ws/breaker/status")
        assert response.status_code == status.HTTP_426_UPGRADE_REQUIRED


@pytest.mark.integration  
class TestAPIErrorHandling:
    """Test API error handling and edge cases"""
    
    def test_api_handles_component_exceptions(self, client, mock_components):
        """Test API handles component exceptions gracefully"""
        mock_components['breaker'].get_all_breaker_status.side_effect = Exception("Component failed")
        
        response = client.get("/api/v1/breaker/status")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    def test_api_correlation_id_consistency(self, client, mock_components):
        """Test API maintains correlation ID consistency"""
        response = client.get("/api/v1/breaker/status")
        
        data = response.json()
        correlation_id = data["correlation_id"]
        
        # Correlation ID should be present and valid UUID format
        import uuid
        try:
            uuid.UUID(correlation_id)
            valid_uuid = True
        except ValueError:
            valid_uuid = False
        
        assert valid_uuid, f"Invalid correlation ID format: {correlation_id}"
    
    def test_api_standard_response_format(self, client, mock_components):
        """Test all endpoints follow standard response format"""
        endpoints = [
            ("/api/v1/breaker/status", "GET"),
            ("/api/v1/health/summary", "GET"),
        ]
        
        for endpoint, method in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            
            if response.status_code == 200:
                data = response.json()
                
                # All successful responses should follow standard format
                assert "data" in data
                assert "error" in data
                assert "correlation_id" in data
                
                # Error should be null for successful responses
                assert data["error"] is None
                
                # Correlation ID should exist
                assert data["correlation_id"] is not None


@pytest.mark.performance
class TestAPIPerformance:
    """Performance tests for API endpoints"""
    
    def test_status_endpoint_performance(self, client, mock_components):
        """Test status endpoint performance under load"""
        import time
        
        # Run multiple requests to test performance
        times = []
        for _ in range(10):
            start_time = time.time()
            response = client.get("/api/v1/breaker/status")
            end_time = time.time()
            
            assert response.status_code == status.HTTP_200_OK
            times.append((end_time - start_time) * 1000)
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Status checks should be fast
        assert avg_time < 100, f"Average status check time: {avg_time}ms"
        assert max_time < 200, f"Maximum status check time: {max_time}ms"
    
    def test_concurrent_api_requests(self, client, mock_components):
        """Test API performance with concurrent requests"""
        import concurrent.futures
        import time
        
        def make_request():
            start_time = time.time()
            response = client.get("/api/v1/breaker/status")
            end_time = time.time()
            return response.status_code, (end_time - start_time) * 1000
        
        # Execute concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        status_codes = [result[0] for result in results]
        response_times = [result[1] for result in results]
        
        assert all(code == 200 for code in status_codes)
        
        # Performance should not degrade significantly under concurrent load
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 500, f"Average concurrent response time: {avg_response_time}ms"