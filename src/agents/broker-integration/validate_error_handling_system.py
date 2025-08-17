"""
Validation Script for Error Handling & Circuit Breaker System
Story 8.9 - Task 7: Comprehensive validation of all error handling components

This script validates the complete error handling system including:
- Retry mechanism with exponential backoff
- Circuit breaker system
- Rate limiting system
- Graceful degradation
- Alerting and logging

Usage:
    python validate_error_handling_system.py [--verbose] [--component COMPONENT]
"""
import asyncio
import sys
import time
import traceback
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Import all error handling components
from retry_handler import (
    OandaRetryHandler, RetryConfiguration, RetryExhaustedError,
    OANDA_API_RETRY_CONFIG, retry_on_failure
)
from circuit_breaker import (
    OandaCircuitBreaker, CircuitBreakerState, CircuitBreakerOpenError,
    CircuitBreakerManager, circuit_breaker_protected
)
from rate_limiter import (
    TokenBucketRateLimiter, RateLimitResult, OandaRateLimitManager,
    RequestQueue, rate_limit_protected
)
from graceful_degradation import (
    GracefulDegradationManager, DegradationLevel, ServiceHealth,
    graceful_degradation_protected
)
from error_alerting import (
    OandaErrorHandler, StructuredLogger, AlertManager,
    AlertSeverity, AlertChannel, error_handled
)


class ValidationResult:
    """Represents validation result for a component or test"""
    
    def __init__(self, component: str, test_name: str, success: bool, 
                 message: str = "", execution_time: float = 0.0, 
                 details: Optional[Dict] = None):
        self.component = component
        self.test_name = test_name
        self.success = success
        self.message = message
        self.execution_time = execution_time
        self.details = details or {}
        self.timestamp = datetime.now(timezone.utc)
        
    def __str__(self) -> str:
        status = "[PASS]" if self.success else "[FAIL]"
        return f"{status} {self.component}::{self.test_name} ({self.execution_time:.3f}s)"


class ErrorHandlingValidator:
    """Comprehensive validator for error handling system"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[ValidationResult] = []
        self.start_time = time.perf_counter()
        
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        if self.verbose or level in ["ERROR", "CRITICAL"]:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] {level}: {message}")
            
    async def run_test(self, component: str, test_name: str, test_func) -> ValidationResult:
        """Run a single test and capture result"""
        start_time = time.perf_counter()
        
        try:
            self.log(f"Running {component}::{test_name}")
            await test_func()
            
            execution_time = time.perf_counter() - start_time
            result = ValidationResult(component, test_name, True, 
                                    "Test completed successfully", execution_time)
            self.log(f"[PASS] {component}::{test_name} ({execution_time:.3f}s)")
            
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            error_msg = f"{type(e).__name__}: {str(e)}"
            result = ValidationResult(component, test_name, False, 
                                    error_msg, execution_time)
            self.log(f"[FAIL] {component}::{test_name} - {error_msg}", "ERROR")
            if self.verbose:
                self.log(traceback.format_exc(), "ERROR")
                
        self.results.append(result)
        return result
        
    async def validate_retry_handler(self) -> List[ValidationResult]:
        """Validate retry handler functionality"""
        results = []
        
        # Test 1: Basic retry functionality
        async def test_basic_retry():
            config = RetryConfiguration(max_attempts=3, base_delay=0.1, max_delay=1.0)
            retry_handler = OandaRetryHandler(config)
            
            call_count = 0
            async def flaky_function():
                nonlocal call_count
                call_count += 1
                if call_count < 2:
                    raise ConnectionError("Temporary failure")
                return "success"
                
            result = await retry_handler.retry_with_backoff(flaky_function)
            assert result == "success"
            assert call_count == 2
            
        results.append(await self.run_test("RetryHandler", "basic_retry", test_basic_retry))
        
        # Test 2: Retry exhaustion
        async def test_retry_exhaustion():
            retry_handler = OandaRetryHandler(RetryConfiguration(max_attempts=2, base_delay=0.01))
            
            async def always_fail():
                raise ConnectionError("Always fails")
                
            try:
                await retry_handler.retry_with_backoff(always_fail)
                assert False, "Should have raised RetryExhaustedError"
            except RetryExhaustedError:
                pass
                
        results.append(await self.run_test("RetryHandler", "retry_exhaustion", test_retry_exhaustion))
        
        # Test 3: Non-retryable error
        async def test_non_retryable_error():
            retry_handler = OandaRetryHandler()
            
            async def non_retryable_error():
                raise ValueError("Non-retryable error")
                
            try:
                await retry_handler.retry_with_backoff(non_retryable_error)
                assert False, "Should have raised ValueError"
            except ValueError:
                pass
                
        results.append(await self.run_test("RetryHandler", "non_retryable_error", test_non_retryable_error))
        
        # Test 4: Exponential backoff timing
        async def test_exponential_backoff():
            retry_handler = OandaRetryHandler(RetryConfiguration(
                max_attempts=3, base_delay=0.1, backoff_multiplier=2.0, jitter_factor=0.0
            ))
            
            call_times = []
            async def timing_function():
                call_times.append(time.perf_counter())
                if len(call_times) < 3:
                    raise ConnectionError("Timing test")
                return "success"
                
            result = await retry_handler.retry_with_backoff(timing_function)
            assert result == "success"
            assert len(call_times) == 3
            
            # Check backoff intervals (allowing for some timing variance)
            interval1 = call_times[1] - call_times[0]
            interval2 = call_times[2] - call_times[1]
            assert 0.08 <= interval1 <= 0.12  # ~0.1s
            assert 0.18 <= interval2 <= 0.22  # ~0.2s
            
        results.append(await self.run_test("RetryHandler", "exponential_backoff", test_exponential_backoff))
        
        # Test 5: Metrics collection
        async def test_metrics():
            retry_handler = OandaRetryHandler()
            
            # Generate some metrics
            try:
                await retry_handler.retry_with_backoff(lambda: (_ for _ in ()).throw(ConnectionError("Test")))
            except RetryExhaustedError:
                pass
                
            metrics = retry_handler.get_retry_metrics()
            assert metrics['total_attempts'] > 0
            assert metrics['failed_attempts'] > 0
            assert 'retry_attempts' in metrics
            
        results.append(await self.run_test("RetryHandler", "metrics_collection", test_metrics))
        
        return results
        
    async def validate_circuit_breaker(self) -> List[ValidationResult]:
        """Validate circuit breaker functionality"""
        results = []
        
        # Test 1: Basic circuit breaker operation
        async def test_basic_circuit_breaker():
            circuit_breaker = OandaCircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
            
            # Success should work normally
            result = await circuit_breaker.call(lambda: "success")
            assert result == "success"
            assert circuit_breaker.state == CircuitBreakerState.CLOSED
            
        results.append(await self.run_test("CircuitBreaker", "basic_operation", test_basic_circuit_breaker))
        
        # Test 2: Circuit opening on failures
        async def test_circuit_opening():
            circuit_breaker = OandaCircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
            
            # Generate failures to open circuit
            for i in range(3):
                try:
                    await circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception(f"Failure {i}")))
                except Exception:
                    pass
                    
            assert circuit_breaker.state == CircuitBreakerState.OPEN
            
        results.append(await self.run_test("CircuitBreaker", "circuit_opening", test_circuit_opening))
        
        # Test 3: Fast failure when open
        async def test_fast_failure():
            circuit_breaker = OandaCircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
            
            # Open the circuit
            for i in range(2):
                try:
                    await circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception("Open circuit")))
                except Exception:
                    pass
                    
            # Should fail fast
            try:
                await circuit_breaker.call(lambda: "should not execute")
                assert False, "Should have raised CircuitBreakerOpenError"
            except CircuitBreakerOpenError:
                pass
                
        results.append(await self.run_test("CircuitBreaker", "fast_failure", test_fast_failure))
        
        # Test 4: Recovery mechanism
        async def test_recovery():
            circuit_breaker = OandaCircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
            
            # Open circuit
            for i in range(2):
                try:
                    await circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception("Test")))
                except Exception:
                    pass
                    
            assert circuit_breaker.state == CircuitBreakerState.OPEN
            
            # Wait for recovery timeout
            await asyncio.sleep(0.15)
            
            # Should recover on success
            result = await circuit_breaker.call(lambda: "recovered")
            assert result == "recovered"
            assert circuit_breaker.state == CircuitBreakerState.CLOSED
            
        results.append(await self.run_test("CircuitBreaker", "recovery_mechanism", test_recovery))
        
        # Test 5: Manual reset
        async def test_manual_reset():
            circuit_breaker = OandaCircuitBreaker(failure_threshold=2)
            
            # Open circuit
            for i in range(2):
                try:
                    await circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception("Test")))
                except Exception:
                    pass
                    
            assert circuit_breaker.state == CircuitBreakerState.OPEN
            
            # Manual reset
            result = await circuit_breaker.manual_reset("Test reset")
            assert result is True
            assert circuit_breaker.state == CircuitBreakerState.CLOSED
            
        results.append(await self.run_test("CircuitBreaker", "manual_reset", test_manual_reset))
        
        return results
        
    async def validate_rate_limiter(self) -> List[ValidationResult]:
        """Validate rate limiter functionality"""
        results = []
        
        # Test 1: Basic rate limiting
        async def test_basic_rate_limiting():
            rate_limiter = TokenBucketRateLimiter(rate=10.0, burst_capacity=5)
            
            # Should allow initial requests
            for i in range(5):
                result = await rate_limiter.acquire(1, "test")
                assert result == RateLimitResult.ALLOWED
                
            # Should rate limit next request
            result = await rate_limiter.acquire(1, "test", wait_if_needed=False)
            assert result == RateLimitResult.RATE_LIMITED
            
        results.append(await self.run_test("RateLimiter", "basic_rate_limiting", test_basic_rate_limiting))
        
        # Test 2: Token refill over time
        async def test_token_refill():
            rate_limiter = TokenBucketRateLimiter(rate=100.0, burst_capacity=5)  # Fast refill for testing
            
            # Exhaust tokens
            for i in range(5):
                await rate_limiter.acquire(1, "test")
                
            # Wait for refill
            await asyncio.sleep(0.1)  # Should add ~10 tokens
            
            # Should allow requests again
            result = await rate_limiter.acquire(1, "test")
            assert result == RateLimitResult.ALLOWED
            
        results.append(await self.run_test("RateLimiter", "token_refill", test_token_refill))
        
        # Test 3: Wait for tokens
        async def test_wait_for_tokens():
            rate_limiter = TokenBucketRateLimiter(rate=100.0, burst_capacity=2)
            
            # Exhaust tokens
            await rate_limiter.acquire(2, "test")
            
            # Should wait and succeed
            start_time = time.perf_counter()
            result = await rate_limiter.acquire(1, "test", wait_if_needed=True)
            wait_time = time.perf_counter() - start_time
            
            assert result == RateLimitResult.QUEUED
            assert wait_time > 0.005  # Should have waited some time
            
        results.append(await self.run_test("RateLimiter", "wait_for_tokens", test_wait_for_tokens))
        
        # Test 4: Rate limit manager
        async def test_rate_limit_manager():
            manager = OandaRateLimitManager()
            
            # Should allow normal requests
            result = await manager.check_rate_limit("test_endpoint", 1)
            assert result == RateLimitResult.ALLOWED
            
            # Critical operations should bypass limits
            manager.global_limiter.tokens = 0
            result = await manager.check_rate_limit("emergency_close", 1, is_critical=True)
            assert result == RateLimitResult.ALLOWED
            
        results.append(await self.run_test("RateLimiter", "rate_limit_manager", test_rate_limit_manager))
        
        # Test 5: Metrics tracking
        async def test_metrics_tracking():
            rate_limiter = TokenBucketRateLimiter(rate=10.0, burst_capacity=5)
            
            # Generate some activity
            for i in range(7):  # More than capacity
                await rate_limiter.acquire(1, "test", wait_if_needed=False)
                
            metrics = rate_limiter.get_metrics()
            assert metrics['total_requests'] == 7
            assert metrics['allowed_requests'] == 5
            assert metrics['rate_limited_requests'] == 2
            assert metrics['success_rate'] == (5/7 * 100)
            
        results.append(await self.run_test("RateLimiter", "metrics_tracking", test_metrics_tracking))
        
        return results
        
    async def validate_graceful_degradation(self) -> List[ValidationResult]:
        """Validate graceful degradation functionality"""
        results = []
        
        # Test 1: Basic degradation triggers
        async def test_degradation_triggers():
            manager = GracefulDegradationManager()
            manager.auto_recovery_enabled = False
            
            # Connection error should trigger READ_ONLY
            error = ConnectionError("Connection failed")
            level = await manager.handle_api_failure("test_service", error)
            assert level == DegradationLevel.READ_ONLY
            
        results.append(await self.run_test("GracefulDegradation", "degradation_triggers", test_degradation_triggers))
        
        # Test 2: Cache functionality
        async def test_cache_functionality():
            manager = GracefulDegradationManager()
            
            test_data = {"price": 1.2345, "timestamp": "2023-01-01T12:00:00Z"}
            
            # Cache data
            await manager.cache_data("pricing", "EUR_USD", test_data)
            
            # Retrieve data
            cached_data = await manager.get_cached_data("pricing", "EUR_USD")
            assert cached_data == test_data
            
        results.append(await self.run_test("GracefulDegradation", "cache_functionality", test_cache_functionality))
        
        # Test 3: Operation permissions
        async def test_operation_permissions():
            manager = GracefulDegradationManager()
            manager.auto_recovery_enabled = False
            
            # Normal mode - all operations allowed
            assert manager.is_operation_allowed("place_order") is True
            assert manager.is_operation_allowed("get_account") is True
            
            # Read-only mode - limited operations
            await manager._transition_to_degradation_level(DegradationLevel.READ_ONLY, "Test")
            assert manager.is_operation_allowed("place_order") is False
            assert manager.is_operation_allowed("get_account") is True
            
        results.append(await self.run_test("GracefulDegradation", "operation_permissions", test_operation_permissions))
        
        # Test 4: Fallback execution
        async def test_fallback_execution():
            manager = GracefulDegradationManager()
            
            # Cache fallback data
            fallback_data = {"cached": "result"}
            await manager.cache_data("api", "test_key", fallback_data)
            
            # Primary function fails, should use cache
            async def failing_primary():
                raise Exception("Primary failed")
                
            result = await manager.execute_with_fallback(
                "get_data", failing_primary, cache_key="test_key"
            )
            
            assert result == fallback_data
            
        results.append(await self.run_test("GracefulDegradation", "fallback_execution", test_fallback_execution))
        
        # Test 5: Manual recovery
        async def test_manual_recovery():
            manager = GracefulDegradationManager()
            manager.auto_recovery_enabled = False
            
            # Degrade system
            await manager._transition_to_degradation_level(DegradationLevel.READ_ONLY, "Test")
            assert manager.current_level == DegradationLevel.READ_ONLY
            
            # Manual recovery
            result = await manager.manual_recovery("Test recovery")
            assert result is True
            assert manager.current_level == DegradationLevel.NONE
            
        results.append(await self.run_test("GracefulDegradation", "manual_recovery", test_manual_recovery))
        
        return results
        
    async def validate_error_alerting(self) -> List[ValidationResult]:
        """Validate error alerting and logging functionality"""
        results = []
        
        # Test 1: Structured logging
        async def test_structured_logging():
            logger = StructuredLogger("test_logger")
            
            error = ValueError("Test error")
            error_context = logger.log_error_with_context(
                error, "test_operation", "test_service",
                account_id="test_account"
            )
            
            assert error_context.error_type == "ValueError"
            assert error_context.error_message == "Test error"
            assert error_context.operation == "test_operation"
            assert error_context.service_name == "test_service"
            assert error_context.account_id == "test_account"
            
        results.append(await self.run_test("ErrorAlerting", "structured_logging", test_structured_logging))
        
        # Test 2: Alert management
        async def test_alert_management():
            alert_manager = AlertManager()
            
            alert_id = await alert_manager.send_alert(
                severity=AlertSeverity.WARNING,
                title="Test Alert",
                message="Test message",
                service="test_service"
            )
            
            assert alert_id is not None
            assert alert_id in alert_manager.alerts
            
            # Test acknowledgment
            result = await alert_manager.acknowledge_alert(alert_id, "test_user")
            assert result is True
            
        results.append(await self.run_test("ErrorAlerting", "alert_management", test_alert_management))
        
        # Test 3: Error handler integration
        async def test_error_handler():
            error_handler = OandaErrorHandler()
            
            error = ConnectionError("Test connection error")
            error_context = await error_handler.handle_error(
                error, "test_operation", "test_service",
                account_id="test_account"
            )
            
            assert error_context.error_type == "ConnectionError"
            assert error_handler.error_stats['total_errors'] == 1
            
        results.append(await self.run_test("ErrorAlerting", "error_handler", test_error_handler))
        
        # Test 4: Recovery suggestions
        async def test_recovery_suggestions():
            logger = StructuredLogger("test_logger")
            
            # Connection error should have connection-related suggestions
            conn_error = ConnectionError("Connection timeout")
            suggestions = logger._generate_recovery_suggestions(conn_error)
            assert any("network" in s.lower() for s in suggestions)
            
            # Rate limit error should have rate limit suggestions
            rate_error = Exception("Rate limit exceeded")
            suggestions = logger._generate_recovery_suggestions(rate_error)
            assert any("request frequency" in s.lower() for s in suggestions)
            
        results.append(await self.run_test("ErrorAlerting", "recovery_suggestions", test_recovery_suggestions))
        
        # Test 5: Alert severity determination
        async def test_alert_severity():
            error_handler = OandaErrorHandler()
            
            from error_alerting import ErrorContext
            
            # Critical error
            auth_context = ErrorContext(
                error_id="test", timestamp=datetime.now(timezone.utc),
                error_type="AuthenticationError", error_message="Auth failed",
                service_name="test", operation="test"
            )
            severity = error_handler._determine_alert_severity(auth_context)
            assert severity == AlertSeverity.CRITICAL
            
            # Warning error  
            rate_context = ErrorContext(
                error_id="test", timestamp=datetime.now(timezone.utc),
                error_type="RateLimitError", error_message="Rate limit exceeded",
                service_name="test", operation="test"
            )
            severity = error_handler._determine_alert_severity(rate_context)
            assert severity == AlertSeverity.WARNING
            
        results.append(await self.run_test("ErrorAlerting", "alert_severity", test_alert_severity))
        
        return results
        
    async def validate_integration(self) -> List[ValidationResult]:
        """Validate integration between components"""
        results = []
        
        # Test 1: Retry with circuit breaker
        async def test_retry_with_circuit_breaker():
            retry_handler = OandaRetryHandler(RetryConfiguration(max_attempts=3, base_delay=0.01))
            circuit_breaker = OandaCircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
            
            call_count = 0
            async def protected_failing_function():
                nonlocal call_count
                call_count += 1
                return await circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception(f"Failure {call_count}")))
                
            try:
                await retry_handler.retry_with_backoff(protected_failing_function)
                assert False, "Should have failed"
            except Exception:
                pass
                
            # Circuit should be open after failures
            assert circuit_breaker.state == CircuitBreakerState.OPEN
            
        results.append(await self.run_test("Integration", "retry_with_circuit_breaker", test_retry_with_circuit_breaker))
        
        # Test 2: Rate limiting with degradation
        async def test_rate_limiting_with_degradation():
            rate_manager = OandaRateLimitManager()
            degradation_manager = GracefulDegradationManager()
            degradation_manager.auto_recovery_enabled = False
            
            # Exhaust rate limit
            rate_manager.global_limiter.tokens = 0
            
            # Trigger degradation due to rate limiting
            rate_error = Exception("Rate limit exceeded")
            level = await degradation_manager.handle_api_failure("test_service", rate_error)
            
            assert level == DegradationLevel.RATE_LIMITED
            assert degradation_manager.cache_manager.default_ttl > 300  # Extended TTL
            
        results.append(await self.run_test("Integration", "rate_limiting_with_degradation", test_rate_limiting_with_degradation))
        
        # Test 3: Error handling with all components
        async def test_comprehensive_error_handling():
            error_handler = OandaErrorHandler()
            degradation_manager = GracefulDegradationManager()
            degradation_manager.auto_recovery_enabled = False
            
            # Generate error that triggers degradation
            error = ConnectionError("Service unavailable")
            error_context = await error_handler.handle_error(error, "test_operation")
            await degradation_manager.handle_api_failure("test_service", error)
            
            # Verify error was handled
            assert error_context.error_type == "ConnectionError"
            assert error_handler.error_stats['total_errors'] == 1
            
            # Verify degradation was triggered
            assert degradation_manager.current_level == DegradationLevel.READ_ONLY
            
        results.append(await self.run_test("Integration", "comprehensive_error_handling", test_comprehensive_error_handling))
        
        return results
        
    async def validate_performance(self) -> List[ValidationResult]:
        """Validate performance characteristics"""
        results = []
        
        # Test 1: Retry handler performance
        async def test_retry_performance():
            retry_handler = OandaRetryHandler(RetryConfiguration(max_attempts=1, base_delay=0.001))
            
            async def fast_success():
                return "success"
                
            start_time = time.perf_counter()
            for _ in range(100):
                await retry_handler.retry_with_backoff(fast_success)
            end_time = time.perf_counter()
            
            # Should handle 100 operations quickly
            assert (end_time - start_time) < 1.0  # Less than 1 second
            
        results.append(await self.run_test("Performance", "retry_handler_performance", test_retry_performance))
        
        # Test 2: Rate limiter performance
        async def test_rate_limiter_performance():
            rate_limiter = TokenBucketRateLimiter(rate=1000.0, burst_capacity=1000)
            
            start_time = time.perf_counter()
            for _ in range(500):  # Half the capacity
                await rate_limiter.acquire(1, "test")
            end_time = time.perf_counter()
            
            # Should handle 500 operations very quickly
            assert (end_time - start_time) < 0.5  # Less than 0.5 seconds
            
        results.append(await self.run_test("Performance", "rate_limiter_performance", test_rate_limiter_performance))
        
        # Test 3: Circuit breaker performance
        async def test_circuit_breaker_performance():
            circuit_breaker = OandaCircuitBreaker()
            
            async def fast_operation():
                return "success"
                
            start_time = time.perf_counter()
            for _ in range(1000):
                await circuit_breaker.call(fast_operation)
            end_time = time.perf_counter()
            
            # Should handle 1000 operations quickly
            assert (end_time - start_time) < 1.0  # Less than 1 second
            
        results.append(await self.run_test("Performance", "circuit_breaker_performance", test_circuit_breaker_performance))
        
        return results
        
    def generate_report(self) -> str:
        """Generate comprehensive validation report"""
        total_time = time.perf_counter() - self.start_time
        
        # Group results by component
        components = {}
        for result in self.results:
            if result.component not in components:
                components[result.component] = {'passed': 0, 'failed': 0, 'tests': []}
            
            if result.success:
                components[result.component]['passed'] += 1
            else:
                components[result.component]['failed'] += 1
                
            components[result.component]['tests'].append(result)
            
        # Generate report
        report = []
        report.append("=" * 80)
        report.append("ERROR HANDLING SYSTEM VALIDATION REPORT")
        report.append("=" * 80)
        report.append(f"Validation completed in {total_time:.2f} seconds")
        report.append(f"Total tests: {len(self.results)}")
        report.append(f"Passed: {sum(1 for r in self.results if r.success)}")
        report.append(f"Failed: {sum(1 for r in self.results if not r.success)}")
        report.append("")
        
        # Component summaries
        for component, data in components.items():
            total = data['passed'] + data['failed']
            success_rate = (data['passed'] / total * 100) if total > 0 else 0
            
            report.append(f"{component}:")
            report.append(f"  Tests: {total} | Passed: {data['passed']} | Failed: {data['failed']} | Success Rate: {success_rate:.1f}%")
            
            # Show failed tests
            failed_tests = [t for t in data['tests'] if not t.success]
            if failed_tests:
                report.append("  Failed Tests:")
                for test in failed_tests:
                    report.append(f"    - {test.test_name}: {test.message}")
            report.append("")
            
        # Detailed results
        if self.verbose:
            report.append("DETAILED TEST RESULTS")
            report.append("-" * 40)
            for result in self.results:
                status = "PASS" if result.success else "FAIL"
                report.append(f"[{status}] {result.component}::{result.test_name}")
                report.append(f"  Time: {result.execution_time:.3f}s")
                if not result.success:
                    report.append(f"  Error: {result.message}")
                report.append("")
                
        # Overall assessment
        overall_success_rate = sum(1 for r in self.results if r.success) / len(self.results) * 100
        report.append("OVERALL ASSESSMENT")
        report.append("-" * 20)
        
        if overall_success_rate >= 95:
            report.append("[EXCELLENT] System validation passed with high confidence")
        elif overall_success_rate >= 85:
            report.append("[GOOD] System validation passed with minor issues")
        elif overall_success_rate >= 70:
            report.append("[ACCEPTABLE] System validation passed with some concerns")
        else:
            report.append("[POOR] System validation failed - requires attention")
            
        report.append(f"Overall Success Rate: {overall_success_rate:.1f}%")
        report.append("")
        
        return "\n".join(report)
        
    async def run_validation(self, components: Optional[List[str]] = None):
        """Run complete validation suite"""
        self.log("Starting Error Handling System Validation", "INFO")
        
        # Define component validation mapping
        component_validators = {
            'retry': self.validate_retry_handler,
            'circuit_breaker': self.validate_circuit_breaker,
            'rate_limiter': self.validate_rate_limiter,
            'graceful_degradation': self.validate_graceful_degradation,
            'error_alerting': self.validate_error_alerting,
            'integration': self.validate_integration,
            'performance': self.validate_performance
        }
        
        # Run specified components or all
        to_validate = components or list(component_validators.keys())
        
        for component in to_validate:
            if component in component_validators:
                self.log(f"Validating {component}...", "INFO")
                await component_validators[component]()
            else:
                self.log(f"Unknown component: {component}", "ERROR")
                
        self.log("Validation completed", "INFO")


async def main():
    """Main validation entry point"""
    parser = argparse.ArgumentParser(description="Validate Error Handling System")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose output")
    parser.add_argument("--component", "-c", action="append",
                       choices=['retry', 'circuit_breaker', 'rate_limiter', 
                               'graceful_degradation', 'error_alerting', 
                               'integration', 'performance'],
                       help="Validate specific component(s)")
    
    args = parser.parse_args()
    
    validator = ErrorHandlingValidator(verbose=args.verbose)
    
    try:
        await validator.run_validation(args.component)
        
        # Generate and display report
        report = validator.generate_report()
        print(report)
        
        # Exit with appropriate code
        failed_count = sum(1 for r in validator.results if not r.success)
        sys.exit(0 if failed_count == 0 else 1)
        
    except Exception as e:
        print(f"Validation failed with error: {e}", file=sys.stderr)
        if args.verbose:
            traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())