"""
Tests for Latency Monitor
Story 8.5: Real-Time Price Streaming - Task 6 Tests (Missing Implementation)
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from latency_monitor import (
    LatencyMonitor,
    LatencyStats,
    NetworkPerformanceMonitor,
    LatencyOptimizer,
    LatencyMeasurement,
    EndToEndTrace,
    LatencyAlert,
    AlertSeverity,
    LatencyThreshold
)

class TestLatencyStats:
    """Test latency statistics functionality"""
    
    @pytest.fixture
    def latency_stats(self):
        return LatencyStats(window_size=100)
        
    def test_latency_stats_creation(self, latency_stats):
        """Test creating latency stats"""
        assert latency_stats.window_size == 100
        assert len(latency_stats.measurements) == 0
        
    def test_add_measurement(self, latency_stats):
        """Test adding latency measurements"""
        latency_stats.add_measurement(50.0)
        latency_stats.add_measurement(75.0)
        latency_stats.add_measurement(100.0)
        
        assert len(latency_stats.measurements) == 3
        
    def test_get_stats_empty(self, latency_stats):
        """Test getting stats when no measurements"""
        stats = latency_stats.get_stats()
        
        assert stats['count'] == 0
        assert stats['mean'] == 0.0
        assert stats['median'] == 0.0
        assert stats['p95'] == 0.0
        assert stats['p99'] == 0.0
        assert stats['min'] == 0.0
        assert stats['max'] == 0.0
        assert stats['std_dev'] == 0.0
        
    def test_get_stats_with_data(self, latency_stats):
        """Test getting stats with measurements"""
        measurements = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        for m in measurements:
            latency_stats.add_measurement(m)
            
        stats = latency_stats.get_stats()
        
        assert stats['count'] == 10
        assert stats['mean'] == 55.0
        assert stats['median'] == 55.0
        assert stats['min'] == 10.0
        assert stats['max'] == 100.0
        assert abs(stats['p95'] - 95.5) < 0.1  # 95th percentile
        assert abs(stats['p99'] - 99.1) < 0.1  # 99th percentile
        assert stats['std_dev'] > 0
        
    def test_window_size_limit(self, latency_stats):
        """Test window size limiting"""
        # Add more measurements than window size
        for i in range(150):
            latency_stats.add_measurement(float(i))
            
        # Should only keep last 100 measurements
        assert len(latency_stats.measurements) == 100
        assert min(latency_stats.measurements) == 50.0  # First 50 should be dropped
        assert max(latency_stats.measurements) == 149.0
        
    def test_percentile_calculation(self, latency_stats):
        """Test percentile calculation accuracy"""
        # Add sorted data for predictable percentiles
        for i in range(1, 101):  # 1 to 100
            latency_stats.add_measurement(float(i))
            
        stats = latency_stats.get_stats()
        
        # For 1-100, 95th percentile should be around 95
        assert abs(stats['p95'] - 95.0) < 1.0
        # 99th percentile should be around 99
        assert abs(stats['p99'] - 99.0) < 1.0

class TestEndToEndTrace:
    """Test end-to-end latency tracing"""
    
    @pytest.fixture
    def trace(self):
        return EndToEndTrace(
            trace_id="test_trace_123",
            instrument="EUR_USD",
            start_time=datetime.now(timezone.utc)
        )
        
    def test_trace_creation(self, trace):
        """Test creating end-to-end trace"""
        assert trace.trace_id == "test_trace_123"
        assert trace.instrument == "EUR_USD"
        assert trace.start_time is not None
        assert len(trace.points) == 0
        
    def test_add_point(self, trace):
        """Test adding measurement points"""
        trace.add_point("oanda_received")
        trace.add_point("processed")
        trace.add_point("distributed")
        
        assert len(trace.points) == 3
        assert trace.points[0].name == "oanda_received"
        assert trace.points[1].name == "processed"
        assert trace.points[2].name == "distributed"
        
    def test_add_point_with_timestamp(self, trace):
        """Test adding point with specific timestamp"""
        custom_time = datetime.now(timezone.utc)
        trace.add_point("custom_point", custom_time)
        
        assert len(trace.points) == 1
        assert trace.points[0].timestamp == custom_time
        
    def test_get_total_latency(self, trace):
        """Test calculating total latency"""
        start_time = datetime.now(timezone.utc)
        trace.start_time = start_time
        
        # Add first point
        trace.add_point("start", start_time + timedelta(milliseconds=50))
        # Add second point 100ms later
        end_time = start_time + timedelta(milliseconds=100)
        trace.add_point("end", end_time)
        
        total_latency = trace.get_total_latency()
        assert total_latency >= 99.0  # Should be ~100ms
        
    def test_get_total_latency_no_points(self, trace):
        """Test total latency with no points"""
        assert trace.get_total_latency() == 0.0
        
    def test_get_segment_latencies(self, trace):
        """Test calculating segment latencies"""
        start_time = datetime.now(timezone.utc)
        trace.start_time = start_time
        
        # Add points with increasing timestamps
        trace.add_point("point1", start_time + timedelta(milliseconds=50))
        trace.add_point("point2", start_time + timedelta(milliseconds=100))
        trace.add_point("point3", start_time + timedelta(milliseconds=150))
        
        segments = trace.get_segment_latencies()
        
        assert len(segments) == 3
        assert abs(segments["point1"] - 50.0) < 1.0
        assert abs(segments["point2"] - 50.0) < 1.0
        assert abs(segments["point3"] - 50.0) < 1.0

class TestNetworkPerformanceMonitor:
    """Test network performance monitoring"""
    
    @pytest.fixture
    def network_monitor(self):
        return NetworkPerformanceMonitor()
        
    def test_network_monitor_creation(self, network_monitor):
        """Test creating network monitor"""
        assert len(network_monitor.connection_tests) == 0
        assert len(network_monitor.packet_loss_history) == 0
        assert len(network_monitor.jitter_history) == 0
        
    @pytest.mark.asyncio
    async def test_test_connectivity_success(self, network_monitor):
        """Test successful connectivity test"""
        # Mock successful connection
        with patch('asyncio.open_connection') as mock_connect:
            mock_reader = AsyncMock()
            mock_writer = AsyncMock()
            mock_writer.close = Mock()  # Make close() synchronous
            mock_writer.wait_closed = AsyncMock()
            mock_connect.return_value = (mock_reader, mock_writer)
            
            result = await network_monitor.test_connectivity("example.com", 443, timeout=1.0)
            
            assert result['success'] is True
            assert 'latency_ms' in result
            assert result['host'] == "example.com"
            assert result['port'] == 443
            assert len(network_monitor.connection_tests) == 1
            
    @pytest.mark.asyncio
    async def test_test_connectivity_timeout(self, network_monitor):
        """Test connectivity test timeout"""
        with patch('asyncio.open_connection') as mock_connect:
            mock_connect.side_effect = asyncio.TimeoutError()
            
            result = await network_monitor.test_connectivity("example.com", 443, timeout=0.1)
            
            assert result['success'] is False
            assert result['error'] == 'timeout'
            assert result['host'] == "example.com"
            assert len(network_monitor.connection_tests) == 1
            
    @pytest.mark.asyncio
    async def test_test_connectivity_error(self, network_monitor):
        """Test connectivity test with connection error"""
        with patch('asyncio.open_connection') as mock_connect:
            mock_connect.side_effect = ConnectionRefusedError("Connection refused")
            
            result = await network_monitor.test_connectivity("example.com", 443, timeout=1.0)
            
            assert result['success'] is False
            assert 'Connection refused' in result['error']
            assert len(network_monitor.connection_tests) == 1
            
    def test_get_network_stats_empty(self, network_monitor):
        """Test network stats with no tests"""
        stats = network_monitor.get_network_stats()
        
        assert stats['connection_success_rate'] == 0.0
        assert stats['avg_latency_ms'] == 0.0
        assert stats['tests_count'] == 0
        assert stats['last_test'] is None
        
    def test_get_network_stats_with_data(self, network_monitor):
        """Test network stats with test data"""
        # Add mock test data
        network_monitor.connection_tests.extend([
            {'success': True, 'latency_ms': 50.0},
            {'success': True, 'latency_ms': 75.0},
            {'success': False, 'error': 'timeout'},
            {'success': True, 'latency_ms': 100.0}
        ])
        
        stats = network_monitor.get_network_stats()
        
        assert stats['connection_success_rate'] == 0.75  # 3 out of 4 successful
        assert stats['avg_latency_ms'] == 75.0  # Average of successful tests
        assert stats['tests_count'] == 4

class TestLatencyOptimizer:
    """Test latency optimization recommendations"""
    
    @pytest.fixture
    def optimizer(self):
        return LatencyOptimizer()
        
    def test_optimizer_creation(self, optimizer):
        """Test creating latency optimizer"""
        assert len(optimizer.recommendations_cache) == 0
        
    def test_analyze_latency_profile_good_performance(self, optimizer):
        """Test analysis with good performance"""
        # Create stats with good latency
        stats_dict = {
            'oanda_stream': Mock(),
            'price_processing': Mock()
        }
        
        # Mock good stats
        stats_dict['oanda_stream'].get_stats.return_value = {
            'count': 100,
            'mean': 50.0,  # Good latency
            'p99': 100.0,  # Good p99
            'std_dev': 10.0  # Low variability
        }
        
        stats_dict['price_processing'].get_stats.return_value = {
            'count': 100,
            'mean': 25.0,  # Good latency
            'p99': 50.0,   # Good p99
            'std_dev': 5.0  # Low variability
        }
        
        recommendations = optimizer.analyze_latency_profile(stats_dict)
        
        # Should recommend monitoring since performance is good
        assert len(recommendations) == 1
        assert "acceptable ranges" in recommendations[0]
        
    def test_analyze_latency_profile_high_latency(self, optimizer):
        """Test analysis with high latency"""
        stats_dict = {
            'oanda_stream': Mock()
        }
        
        # Mock high latency stats
        stats_dict['oanda_stream'].get_stats.return_value = {
            'count': 100,
            'mean': 300.0,  # High latency
            'p99': 600.0,   # High p99
            'std_dev': 100.0  # High variability
        }
        
        recommendations = optimizer.analyze_latency_profile(stats_dict)
        
        # Should have recommendations for high latency and variability
        assert len(recommendations) >= 2
        assert any("Mean latency" in rec for rec in recommendations)
        assert any("variability" in rec for rec in recommendations)
        
    def test_get_optimization_suggestions_oanda_stream(self, optimizer):
        """Test optimization suggestions for OANDA stream"""
        suggestions = optimizer.get_optimization_suggestions("oanda_stream", 150.0)
        
        assert len(suggestions) > 0
        assert any("internet connection" in sugg for sugg in suggestions)
        assert any("WebSocket message" in sugg for sugg in suggestions)
        
    def test_get_optimization_suggestions_price_processing(self, optimizer):
        """Test optimization suggestions for price processing"""
        suggestions = optimizer.get_optimization_suggestions("price_processing", 75.0)
        
        assert len(suggestions) > 0
        assert any("calculation algorithms" in sugg for sugg in suggestions)
        assert any("caching" in sugg for sugg in suggestions)
        
    def test_get_optimization_suggestions_distribution_server(self, optimizer):
        """Test optimization suggestions for distribution server"""
        suggestions = optimizer.get_optimization_suggestions("distribution_server", 50.0)
        
        assert len(suggestions) > 0
        assert any("compression" in sugg for sugg in suggestions)
        assert any("batching" in sugg for sugg in suggestions)

class TestLatencyMonitor:
    """Test main latency monitor functionality"""
    
    @pytest.fixture
    def latency_monitor(self):
        return LatencyMonitor()
        
    def test_latency_monitor_creation(self, latency_monitor):
        """Test creating latency monitor"""
        assert len(latency_monitor.component_stats) == 0
        assert len(latency_monitor.active_traces) == 0
        assert len(latency_monitor.alert_callbacks) == 0
        assert latency_monitor.is_running is False
        
    def test_add_measurement(self, latency_monitor):
        """Test adding latency measurement"""
        latency_monitor.add_measurement("oanda_stream", "connection", 75.0)
        
        assert "oanda_stream" in latency_monitor.component_stats
        stats = latency_monitor.component_stats["oanda_stream"].get_stats()
        assert stats['count'] == 1
        assert stats['mean'] == 75.0
        
    def test_add_measurement_with_metadata(self, latency_monitor):
        """Test adding measurement with metadata"""
        metadata = {"instrument": "EUR_USD", "client_count": 5}
        latency_monitor.add_measurement("price_processing", "calculation", 25.0, metadata)
        
        assert "price_processing" in latency_monitor.component_stats
        
    def test_start_trace(self, latency_monitor):
        """Test starting end-to-end trace"""
        trace = latency_monitor.start_trace("trace_123", "EUR_USD")
        
        assert trace.trace_id == "trace_123"
        assert trace.instrument == "EUR_USD"
        assert "trace_123" in latency_monitor.active_traces
        
    def test_add_trace_point(self, latency_monitor):
        """Test adding points to trace"""
        trace = latency_monitor.start_trace("trace_123", "EUR_USD")
        latency_monitor.add_trace_point("trace_123", "oanda_received")
        latency_monitor.add_trace_point("trace_123", "processed")
        
        assert len(trace.points) == 2
        assert trace.points[0].name == "oanda_received"
        assert trace.points[1].name == "processed"
        
    def test_complete_trace(self, latency_monitor):
        """Test completing trace"""
        trace = latency_monitor.start_trace("trace_123", "EUR_USD")
        latency_monitor.add_trace_point("trace_123", "end")
        
        completed_trace = latency_monitor.complete_trace("trace_123")
        
        assert completed_trace is not None
        assert "trace_123" not in latency_monitor.active_traces
        assert len(latency_monitor.completed_traces) == 1
        assert "end_to_end" in latency_monitor.component_stats
        
    def test_complete_nonexistent_trace(self, latency_monitor):
        """Test completing non-existent trace"""
        result = latency_monitor.complete_trace("nonexistent")
        assert result is None
        
    def test_add_alert_callback(self, latency_monitor):
        """Test adding alert callback"""
        callback = Mock()
        latency_monitor.add_alert_callback(callback)
        
        assert len(latency_monitor.alert_callbacks) == 1
        assert callback in latency_monitor.alert_callbacks
        
    def test_threshold_checking_warning(self, latency_monitor):
        """Test threshold checking generates warning alert"""
        callback = Mock()
        latency_monitor.add_alert_callback(callback)
        
        # Add measurement that exceeds warning threshold
        latency_monitor.add_measurement("oanda_stream", "connection", 150.0)  # Above 100ms warning
        
        # Should generate warning alert
        assert len(latency_monitor.alert_history) == 1
        alert = latency_monitor.alert_history[0]
        assert alert.severity == AlertSeverity.WARNING
        assert alert.component == "oanda_stream"
        assert alert.latency_ms == 150.0
        
    def test_threshold_checking_critical(self, latency_monitor):
        """Test threshold checking generates critical alert"""
        callback = Mock()
        latency_monitor.add_alert_callback(callback)
        
        # Add measurement that exceeds critical threshold
        latency_monitor.add_measurement("oanda_stream", "connection", 400.0)  # Above 300ms critical
        
        # Should generate critical alert
        assert len(latency_monitor.alert_history) == 1
        alert = latency_monitor.alert_history[0]
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.component == "oanda_stream"
        assert alert.latency_ms == 400.0
        
    def test_get_latency_stats(self, latency_monitor):
        """Test getting latency statistics"""
        latency_monitor.add_measurement("oanda_stream", "connection", 75.0)
        latency_monitor.add_measurement("price_processing", "calculation", 25.0)
        
        stats = latency_monitor.get_latency_stats()
        
        assert "oanda_stream" in stats
        assert "price_processing" in stats
        assert stats["oanda_stream"]["count"] == 1
        assert stats["price_processing"]["count"] == 1
        
    def test_get_latency_visualization_data(self, latency_monitor):
        """Test getting visualization data"""
        # Add some measurements
        for i in range(10):
            latency_monitor.add_measurement("oanda_stream", "connection", float(50 + i))
            
        viz_data = latency_monitor.get_latency_visualization_data("oanda_stream", window_minutes=60)
        
        assert viz_data["component"] == "oanda_stream"
        assert len(viz_data["data_points"]) == 10
        assert viz_data["time_range"] == 60
        assert "stats" in viz_data
        assert "threshold" in viz_data
        
    def test_get_latency_visualization_data_nonexistent(self, latency_monitor):
        """Test getting visualization data for non-existent component"""
        viz_data = latency_monitor.get_latency_visualization_data("nonexistent")
        
        assert viz_data["component"] == "nonexistent"
        assert len(viz_data["data_points"]) == 0
        assert viz_data["stats"] == {}
        
    def test_get_system_health_summary(self, latency_monitor):
        """Test getting system health summary"""
        # Add some measurements
        latency_monitor.add_measurement("oanda_stream", "connection", 75.0)
        latency_monitor.add_measurement("price_processing", "calculation", 25.0)
        
        health = latency_monitor.get_system_health_summary()
        
        assert "health_score" in health
        assert "status" in health
        assert "latency_stats" in health
        assert "network_stats" in health
        assert "active_traces" in health
        assert "recent_alerts" in health
        assert "recommendations" in health
        
        # Should have good health score
        assert health["health_score"] >= 70  # Good performance
        assert health["status"] in ["excellent", "good"]
        
    def test_get_system_health_summary_poor_performance(self, latency_monitor):
        """Test health summary with poor performance"""
        # Add measurements that exceed critical thresholds
        latency_monitor.add_measurement("oanda_stream", "connection", 400.0)  # Critical
        latency_monitor.add_measurement("price_processing", "calculation", 200.0)  # Critical
        
        health = latency_monitor.get_system_health_summary()
        
        # Should have degraded health score
        assert health["health_score"] < 50
        assert health["status"] in ["poor", "critical"]

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, latency_monitor):
        """Test starting and stopping monitoring"""
        assert latency_monitor.is_running is False
        
        # Start monitoring
        await latency_monitor.start_monitoring()
        assert latency_monitor.is_running is True
        assert latency_monitor.monitoring_task is not None
        assert latency_monitor.network_test_task is not None
        
        # Stop monitoring
        await latency_monitor.stop_monitoring()
        assert latency_monitor.is_running is False

@pytest.mark.asyncio
async def test_integration_latency_monitoring():
    """Test complete latency monitoring integration"""
    monitor = LatencyMonitor()
    
    # Test end-to-end trace
    trace = monitor.start_trace("integration_test", "EUR_USD")
    monitor.add_trace_point("integration_test", "oanda_received")
    
    # Simulate some processing time
    await asyncio.sleep(0.01)  # 10ms
    
    monitor.add_trace_point("integration_test", "processed")
    monitor.add_trace_point("integration_test", "distributed")
    
    # Complete trace
    completed_trace = monitor.complete_trace("integration_test")
    
    # Verify trace was processed
    assert completed_trace is not None
    assert completed_trace.get_total_latency() > 0
    assert "end_to_end" in monitor.component_stats
    
    # Add some component measurements
    monitor.add_measurement("oanda_stream", "connection", 85.0)
    monitor.add_measurement("price_processing", "calculation", 15.0)
    monitor.add_measurement("distribution_server", "broadcast", 10.0)
    
    # Get health summary
    health = monitor.get_system_health_summary()
    assert health["health_score"] >= 70  # Good performance
    
    # Get optimization recommendations
    stats = monitor.get_latency_stats()
    optimizer = LatencyOptimizer()
    recommendations = optimizer.analyze_latency_profile(monitor.component_stats)
    
    assert len(recommendations) > 0

if __name__ == "__main__":
    pytest.main([__file__])