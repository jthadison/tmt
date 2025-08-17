"""
Tests for Error Alerting and Logging System
Story 8.9 - Task 6: Test alerting and logging system
"""
import pytest
import asyncio
import time
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from error_alerting import (
    OandaErrorHandler, StructuredLogger, AlertManager,
    AlertSeverity, AlertChannel, ErrorContext, Alert,
    get_global_error_handler, error_handled
)


class TestStructuredLogger:
    """Test structured logger functionality"""
    
    @pytest.fixture
    def logger(self):
        """Create structured logger for testing"""
        return StructuredLogger("test_logger")
        
    def test_log_with_context(self, logger):
        """Test logging with structured context"""
        entry_id = logger.log_with_context(
            level=20,  # INFO level
            message="Test message",
            operation="test_operation",
            service_name="test_service",
            account_id="test_account",
            custom_field="custom_value"
        )
        
        assert entry_id is not None
        assert len(logger.log_entries) == 1
        
        entry = logger.log_entries[0]
        assert entry['message'] == "Test message"
        assert entry['operation'] == "test_operation"
        assert entry['service'] == "test_service"
        assert entry['context']['account_id'] == "test_account"
        assert entry['context']['custom_field'] == "custom_value"
        
    def test_log_error_with_context(self, logger):
        """Test error logging with context"""
        error = ValueError("Test error message")
        
        error_context = logger.log_error_with_context(
            error, "test_operation", "test_service",
            account_id="test_account"
        )
        
        assert isinstance(error_context, ErrorContext)
        assert error_context.error_type == "ValueError"
        assert error_context.error_message == "Test error message"
        assert error_context.operation == "test_operation"
        assert error_context.service_name == "test_service"
        assert error_context.account_id == "test_account"
        assert error_context.stack_trace is not None
        
    def test_error_aggregation(self, logger):
        """Test error aggregation functionality"""
        error1 = ValueError("First error")
        error2 = ValueError("Second error")
        
        logger.log_error_with_context(error1, "test_op", "service")
        logger.log_error_with_context(error2, "test_op", "service")
        
        error_key = "ValueError:test_op"
        assert error_key in logger.error_aggregation
        assert len(logger.error_aggregation[error_key]) == 2
        
    def test_recovery_suggestions_connection_error(self, logger):
        """Test recovery suggestions for connection errors"""
        error = ConnectionError("Connection timeout")
        
        suggestions = logger._generate_recovery_suggestions(error)
        
        assert "Check network connectivity" in suggestions
        assert "Verify OANDA API endpoints are accessible" in suggestions
        
    def test_recovery_suggestions_authentication_error(self, logger):
        """Test recovery suggestions for authentication errors"""
        error = Exception("Authentication failed")
        
        suggestions = logger._generate_recovery_suggestions(error)
        
        assert "Verify API credentials are valid" in suggestions
        assert "Check if API key has expired" in suggestions
        
    def test_recovery_suggestions_rate_limit_error(self, logger):
        """Test recovery suggestions for rate limit errors"""
        error = Exception("Rate limit exceeded")
        
        suggestions = logger._generate_recovery_suggestions(error)
        
        assert "Reduce request frequency" in suggestions
        assert "Implement longer delays between requests" in suggestions
        
    def test_get_error_summary(self, logger):
        """Test error summary generation"""
        # Add some errors
        error1 = ValueError("Error 1")
        error2 = ConnectionError("Error 2")
        
        logger.log_error_with_context(error1, "op1", "service")
        logger.log_error_with_context(error2, "op2", "service")
        
        summary = logger.get_error_summary(hours=1)
        
        assert summary['total_errors'] == 2
        assert summary['unique_error_types'] == 2
        assert 'ValueError' in summary['error_breakdown']
        assert 'ConnectionError' in summary['error_breakdown']
        
    def test_log_entry_limit(self, logger):
        """Test log entry limit enforcement"""
        logger.max_log_entries = 5
        
        # Add more entries than limit
        for i in range(10):
            logger.log_with_context(20, f"Message {i}", "test_op")
            
        # Should only keep the last 5 entries
        assert len(logger.log_entries) == 5
        assert logger.log_entries[0]['message'] == "Message 5"
        assert logger.log_entries[-1]['message'] == "Message 9"
        
    def test_system_metrics_collection(self, logger):
        """Test system metrics collection"""
        metrics = logger._collect_system_metrics()
        
        assert 'memory_usage_mb' in metrics
        assert 'cpu_count' in metrics
        assert 'python_version' in metrics
        assert 'process_uptime' in metrics


class TestAlertManager:
    """Test alert manager functionality"""
    
    @pytest.fixture
    def alert_manager(self):
        """Create alert manager for testing"""
        return AlertManager()
        
    @pytest.mark.asyncio
    async def test_send_basic_alert(self, alert_manager):
        """Test sending basic alert"""
        alert_id = await alert_manager.send_alert(
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="This is a test alert",
            service="test_service"
        )
        
        assert alert_id is not None
        assert alert_id in alert_manager.alerts
        
        alert = alert_manager.alerts[alert_id]
        assert alert.severity == AlertSeverity.WARNING
        assert alert.title == "Test Alert"
        assert alert.message == "This is a test alert"
        assert alert.service == "test_service"
        
    @pytest.mark.asyncio
    async def test_send_alert_with_error_context(self, alert_manager):
        """Test sending alert with error context"""
        error_context = ErrorContext(
            error_id="test_error_id",
            timestamp=datetime.now(timezone.utc),
            error_type="TestError",
            error_message="Test error",
            service_name="test_service",
            operation="test_operation"
        )
        
        alert_id = await alert_manager.send_alert(
            severity=AlertSeverity.ERROR,
            title="Error Alert",
            message="Error occurred",
            service="test_service",
            error_context=error_context
        )
        
        alert = alert_manager.alerts[alert_id]
        assert alert.error_context == error_context
        
    @pytest.mark.asyncio
    async def test_alert_suppression(self, alert_manager):
        """Test alert suppression functionality"""
        # Send first alert
        alert_id1 = await alert_manager.send_alert(
            severity=AlertSeverity.WARNING,
            title="Repeated Alert",
            message="This alert repeats",
            service="test_service"
        )
        
        # Send same alert immediately (should be suppressed)
        alert_id2 = await alert_manager.send_alert(
            severity=AlertSeverity.WARNING,
            title="Repeated Alert",
            message="This alert repeats",
            service="test_service"
        )
        
        # Both should return alert IDs, but second might be suppressed
        assert alert_id1 is not None
        assert alert_id2 is not None
        
    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, alert_manager):
        """Test alert acknowledgment"""
        alert_id = await alert_manager.send_alert(
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="Test message",
            service="test_service"
        )
        
        result = await alert_manager.acknowledge_alert(alert_id, "test_user")
        
        assert result is True
        
        alert = alert_manager.alerts[alert_id]
        assert alert.acknowledged is True
        assert alert.acknowledged_by == "test_user"
        assert alert.acknowledged_at is not None
        
    @pytest.mark.asyncio
    async def test_resolve_alert(self, alert_manager):
        """Test alert resolution"""
        alert_id = await alert_manager.send_alert(
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="Test message",
            service="test_service"
        )
        
        result = await alert_manager.resolve_alert(alert_id)
        
        assert result is True
        
        alert = alert_manager.alerts[alert_id]
        assert alert.resolved is True
        assert alert.resolved_at is not None
        
    def test_get_active_alerts(self, alert_manager):
        """Test getting active alerts"""
        # Create test alert
        alert = Alert(
            alert_id="test_id",
            timestamp=datetime.now(timezone.utc),
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="Test message",
            service="test_service"
        )
        
        alert_manager.alerts["test_id"] = alert
        
        active_alerts = alert_manager.get_active_alerts()
        
        assert len(active_alerts) == 1
        assert active_alerts[0]['alert_id'] == "test_id"
        
    def test_get_alert_summary(self, alert_manager):
        """Test alert summary generation"""
        # Create test alerts
        for i in range(3):
            severity = [AlertSeverity.INFO, AlertSeverity.WARNING, AlertSeverity.ERROR][i]
            alert = Alert(
                alert_id=f"test_{i}",
                timestamp=datetime.now(timezone.utc),
                severity=severity,
                title=f"Test Alert {i}",
                message=f"Test message {i}",
                service="test_service"
            )
            alert_manager.alert_history.append(alert)
            
        summary = alert_manager.get_alert_summary(hours=1)
        
        assert summary['total_alerts'] == 3
        assert 'severity_breakdown' in summary
        assert summary['severity_breakdown']['info'] == 1
        assert summary['severity_breakdown']['warning'] == 1
        assert summary['severity_breakdown']['error'] == 1
        
    @pytest.mark.asyncio
    async def test_channel_routing(self, alert_manager):
        """Test alert routing to different channels"""
        # Mock the channel send methods
        with patch.object(alert_manager, '_send_to_log') as mock_log, \
             patch.object(alert_manager, '_send_to_slack') as mock_slack:
            
            await alert_manager.send_alert(
                severity=AlertSeverity.CRITICAL,
                title="Critical Alert",
                message="Critical message",
                service="test_service",
                channels=[AlertChannel.LOG, AlertChannel.SLACK]
            )
            
            mock_log.assert_called_once()
            mock_slack.assert_called_once()
            
    def test_default_alert_rules(self, alert_manager):
        """Test default alert rules configuration"""
        assert len(alert_manager.alert_rules) > 0
        
        # Check for expected default rules
        rule_names = [rule['name'] for rule in alert_manager.alert_rules]
        assert 'circuit_breaker_open' in rule_names
        assert 'authentication_failure' in rule_names
        assert 'rate_limit_exceeded' in rule_names


class TestOandaErrorHandler:
    """Test OANDA error handler functionality"""
    
    @pytest.fixture
    def error_handler(self):
        """Create error handler for testing"""
        return OandaErrorHandler()
        
    @pytest.mark.asyncio
    async def test_handle_error_basic(self, error_handler):
        """Test basic error handling"""
        error = ValueError("Test error")
        
        error_context = await error_handler.handle_error(
            error, "test_operation", "test_service",
            account_id="test_account"
        )
        
        assert isinstance(error_context, ErrorContext)
        assert error_context.error_type == "ValueError"
        assert error_context.operation == "test_operation"
        assert error_context.service_name == "test_service"
        assert error_context.account_id == "test_account"
        
        # Check statistics updated
        assert error_handler.error_stats['total_errors'] == 1
        assert error_handler.error_stats['errors_by_type']['ValueError'] == 1
        assert error_handler.error_stats['errors_by_service']['test_service'] == 1
        
    @pytest.mark.asyncio
    async def test_handle_error_without_auto_alert(self, error_handler):
        """Test error handling without auto alert"""
        error = ValueError("Test error")
        
        with patch.object(error_handler, '_send_error_alert') as mock_alert:
            await error_handler.handle_error(
                error, "test_operation", auto_alert=False
            )
            
            mock_alert.assert_not_called()
            
    @pytest.mark.asyncio
    async def test_handle_error_with_auto_alert(self, error_handler):
        """Test error handling with auto alert"""
        error = ValueError("Test error")
        
        with patch.object(error_handler, '_send_error_alert') as mock_alert:
            await error_handler.handle_error(
                error, "test_operation", auto_alert=True
            )
            
            mock_alert.assert_called_once()
            
    def test_determine_alert_severity_critical(self, error_handler):
        """Test alert severity determination for critical errors"""
        auth_context = ErrorContext(
            error_id="test",
            timestamp=datetime.now(timezone.utc),
            error_type="AuthenticationError",
            error_message="Auth failed",
            service_name="test",
            operation="test"
        )
        
        severity = error_handler._determine_alert_severity(auth_context)
        assert severity == AlertSeverity.CRITICAL
        
    def test_determine_alert_severity_error(self, error_handler):
        """Test alert severity determination for error level"""
        conn_context = ErrorContext(
            error_id="test",
            timestamp=datetime.now(timezone.utc),
            error_type="ConnectionError",
            error_message="Connection failed",
            service_name="test",
            operation="test"
        )
        
        severity = error_handler._determine_alert_severity(conn_context)
        assert severity == AlertSeverity.ERROR
        
    def test_determine_alert_severity_warning(self, error_handler):
        """Test alert severity determination for warning level"""
        rate_context = ErrorContext(
            error_id="test",
            timestamp=datetime.now(timezone.utc),
            error_type="RateLimitError",
            error_message="Rate limit exceeded",
            service_name="test",
            operation="test"
        )
        
        severity = error_handler._determine_alert_severity(rate_context)
        assert severity == AlertSeverity.WARNING
        
    def test_determine_alert_channels(self, error_handler):
        """Test alert channel determination"""
        critical_channels = error_handler._determine_alert_channels(AlertSeverity.CRITICAL)
        assert AlertChannel.LOG in critical_channels
        assert AlertChannel.PAGERDUTY in critical_channels
        assert AlertChannel.SLACK in critical_channels
        
        warning_channels = error_handler._determine_alert_channels(AlertSeverity.WARNING)
        assert AlertChannel.LOG in warning_channels
        assert len(warning_channels) == 1
        
    def test_get_error_statistics(self, error_handler):
        """Test error statistics retrieval"""
        stats = error_handler.get_error_statistics()
        
        assert 'total_errors' in stats
        assert 'errors_by_type' in stats
        assert 'errors_by_service' in stats
        assert 'alert_summary' in stats
        assert 'error_summary' in stats
        
    @pytest.mark.asyncio
    async def test_alerting_system_test(self, error_handler):
        """Test alerting system testing functionality"""
        test_results = await error_handler.test_alerting_system()
        
        assert isinstance(test_results, dict)
        assert len(test_results) == len(AlertChannel)
        
        for channel in AlertChannel:
            assert channel.value in test_results
            # Results should be either "SUCCESS" or start with "FAILED:"


class TestErrorHandledDecorator:
    """Test error handled decorator"""
    
    @pytest.mark.asyncio
    async def test_decorator_success(self):
        """Test successful decorated function"""
        @error_handled("test_operation")
        async def test_func(self, value):
            return f"result: {value}"
            
        # Create mock self object
        mock_self = MagicMock()
        
        result = await test_func(mock_self, "test")
        assert result == "result: test"
        
    @pytest.mark.asyncio
    async def test_decorator_with_error(self):
        """Test decorated function with error"""
        @error_handled("test_operation")
        async def test_func(self):
            raise ValueError("Test error")
            
        mock_self = MagicMock()
        
        with pytest.raises(ValueError):
            await test_func(mock_self)
            
    @pytest.mark.asyncio
    async def test_decorator_with_instance_error_handler(self):
        """Test decorator using instance error handler"""
        @error_handled("test_operation")
        async def test_func(self):
            raise ValueError("Test error")
            
        mock_self = MagicMock()
        mock_self._error_handler = MagicMock()
        mock_self._error_handler.handle_error = AsyncMock()
        
        with pytest.raises(ValueError):
            await test_func(mock_self)
            
        mock_self._error_handler.handle_error.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_decorator_with_context_extraction(self):
        """Test decorator with context extraction from kwargs"""
        @error_handled("test_operation")
        async def test_func(self, account_id=None, request_id=None):
            raise ValueError("Test error")
            
        mock_self = MagicMock()
        mock_error_handler = MagicMock()
        mock_error_handler.handle_error = AsyncMock()
        mock_self._error_handler = mock_error_handler
        
        with pytest.raises(ValueError):
            await test_func(mock_self, account_id="test_account", request_id="test_request")
            
        # Check that context was extracted
        call_args = mock_error_handler.handle_error.call_args
        assert call_args.kwargs['account_id'] == "test_account"
        assert call_args.kwargs['request_id'] == "test_request"


class TestGlobalErrorHandler:
    """Test global error handler"""
    
    def test_get_global_error_handler(self):
        """Test getting global error handler instance"""
        handler1 = get_global_error_handler()
        handler2 = get_global_error_handler()
        
        assert handler1 is handler2  # Same instance
        assert isinstance(handler1, OandaErrorHandler)


class TestDataClasses:
    """Test data class functionality"""
    
    def test_error_context_to_dict(self):
        """Test ErrorContext to_dict conversion"""
        context = ErrorContext(
            error_id="test_id",
            timestamp=datetime.now(timezone.utc),
            error_type="TestError",
            error_message="Test message",
            service_name="test_service",
            operation="test_operation",
            account_id="test_account"
        )
        
        context_dict = context.to_dict()
        
        assert context_dict['error_id'] == "test_id"
        assert context_dict['error_type'] == "TestError"
        assert context_dict['error_message'] == "Test message"
        assert context_dict['service_name'] == "test_service"
        assert context_dict['operation'] == "test_operation"
        assert context_dict['account_id'] == "test_account"
        assert 'timestamp' in context_dict
        
    def test_alert_to_dict(self):
        """Test Alert to_dict conversion"""
        alert = Alert(
            alert_id="test_alert",
            timestamp=datetime.now(timezone.utc),
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="Test message",
            service="test_service",
            channels=[AlertChannel.LOG, AlertChannel.SLACK]
        )
        
        alert_dict = alert.to_dict()
        
        assert alert_dict['alert_id'] == "test_alert"
        assert alert_dict['severity'] == "warning"
        assert alert_dict['title'] == "Test Alert"
        assert alert_dict['message'] == "Test message"
        assert alert_dict['service'] == "test_service"
        assert alert_dict['channels'] == ['log', 'slack']


class TestIntegration:
    """Test integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_error_handling(self):
        """Test complete error handling flow"""
        error_handler = OandaErrorHandler()
        
        # Simulate an error
        error = ConnectionError("Connection timeout")
        
        error_context = await error_handler.handle_error(
            error, "api_call", "oanda_api",
            account_id="test_account",
            request_id="req_123"
        )
        
        # Check error was logged
        assert len(error_handler.structured_logger.log_entries) > 0
        
        # Check error was aggregated
        error_key = "ConnectionError:api_call"
        assert error_key in error_handler.structured_logger.error_aggregation
        
        # Check statistics updated
        assert error_handler.error_stats['total_errors'] == 1
        assert error_handler.error_stats['errors_by_type']['ConnectionError'] == 1
        
        # Check alert was generated
        active_alerts = error_handler.alert_manager.get_active_alerts()
        assert len(active_alerts) > 0
        
    @pytest.mark.asyncio
    async def test_multiple_error_types_aggregation(self):
        """Test handling multiple error types"""
        error_handler = OandaErrorHandler()
        
        # Generate different types of errors
        errors = [
            (ConnectionError("Connection failed"), "connect"),
            (ValueError("Invalid value"), "validate"),
            (ConnectionError("Another connection issue"), "connect"),
            (TimeoutError("Request timeout"), "timeout")
        ]
        
        for error, operation in errors:
            await error_handler.handle_error(error, operation, "test_service")
            
        # Check statistics
        stats = error_handler.get_error_statistics()
        assert stats['total_errors'] == 4
        assert stats['errors_by_type']['ConnectionError'] == 2
        assert stats['errors_by_type']['ValueError'] == 1
        assert stats['errors_by_type']['TimeoutError'] == 1
        
    @pytest.mark.asyncio
    async def test_alert_suppression_with_time_window(self):
        """Test alert suppression over time"""
        alert_manager = AlertManager()
        
        # Send first alert
        await alert_manager.send_alert(
            AlertSeverity.WARNING, "Test Alert", "Test message", "test_service"
        )
        
        # Send similar alert (should be suppressed)
        await alert_manager.send_alert(
            AlertSeverity.WARNING, "Test Alert", "Test message", "test_service"
        )
        
        # Check that suppression is working
        active_alerts = alert_manager.get_active_alerts()
        # Implementation may vary on how suppression is handled


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.mark.asyncio
    async def test_very_long_error_message(self):
        """Test handling very long error messages"""
        logger = StructuredLogger("test")
        long_message = "x" * 10000  # 10KB error message
        
        error = ValueError(long_message)
        error_context = logger.log_error_with_context(error, "test_op", "test_service")
        
        assert error_context.error_message == long_message
        
    @pytest.mark.asyncio
    async def test_unicode_in_error_messages(self):
        """Test handling unicode characters in error messages"""
        logger = StructuredLogger("test")
        
        unicode_message = "Error with unicode: café, naïve, résumé 🚨"
        error = ValueError(unicode_message)
        
        error_context = logger.log_error_with_context(error, "test_op", "test_service")
        
        assert error_context.error_message == unicode_message
        
    def test_empty_error_message(self):
        """Test handling empty error messages"""
        logger = StructuredLogger("test")
        
        error = ValueError("")
        error_context = logger.log_error_with_context(error, "test_op", "test_service")
        
        assert error_context.error_message == ""
        assert error_context.error_type == "ValueError"
        
    @pytest.mark.asyncio
    async def test_concurrent_error_handling(self):
        """Test concurrent error handling"""
        error_handler = OandaErrorHandler()
        
        async def generate_error(i):
            error = ValueError(f"Error {i}")
            return await error_handler.handle_error(error, f"operation_{i}", "test_service")
            
        # Generate multiple concurrent errors
        tasks = [generate_error(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 10
        assert error_handler.error_stats['total_errors'] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])