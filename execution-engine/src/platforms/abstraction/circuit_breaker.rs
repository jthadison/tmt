use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use serde::{Deserialize, Serialize};

use super::errors::PlatformError;

/// Circuit breaker states
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum CircuitBreakerState {
    /// Circuit is closed - operations are allowed
    Closed,
    /// Circuit is open - operations are blocked
    Open,
    /// Circuit is half-open - limited operations are allowed for testing
    HalfOpen,
}

/// Circuit breaker configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CircuitBreakerConfig {
    /// Failure threshold to open the circuit
    pub failure_threshold: u32,
    /// Success threshold to close the circuit from half-open
    pub success_threshold: u32,
    /// Time window for counting failures
    pub failure_window: Duration,
    /// Timeout before transitioning from open to half-open
    pub open_timeout: Duration,
    /// Maximum number of operations allowed in half-open state
    pub half_open_max_operations: u32,
}

impl Default for CircuitBreakerConfig {
    fn default() -> Self {
        Self {
            failure_threshold: 5,       // 5 failures to open
            success_threshold: 3,       // 3 successes to close
            failure_window: Duration::from_secs(60), // 1 minute window
            open_timeout: Duration::from_secs(30),   // 30 second timeout
            half_open_max_operations: 3, // Allow 3 test operations
        }
    }
}

/// Circuit breaker statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CircuitBreakerStats {
    pub state: CircuitBreakerState,
    pub failure_count: u32,
    pub success_count: u32,
    pub total_operations: u64,
    pub last_failure_time: Option<chrono::DateTime<chrono::Utc>>,
    pub last_state_change: chrono::DateTime<chrono::Utc>,
    pub current_failure_window_count: u32,
}

/// Internal circuit breaker data
struct CircuitBreakerData {
    state: CircuitBreakerState,
    failure_count: u32,
    success_count: u32,
    total_operations: u64,
    last_failure_time: Option<Instant>,
    last_state_change: Instant,
    failure_window_start: Instant,
    current_failure_window_count: u32,
    half_open_operations: u32,
}

/// Circuit breaker implementation for platform resilience
pub struct CircuitBreaker {
    config: CircuitBreakerConfig,
    data: Arc<Mutex<CircuitBreakerData>>,
}

impl CircuitBreaker {
    /// Create a new circuit breaker with default configuration
    pub fn new() -> Self {
        Self::with_config(CircuitBreakerConfig::default())
    }

    /// Create a new circuit breaker with custom configuration
    pub fn with_config(config: CircuitBreakerConfig) -> Self {
        let now = Instant::now();
        let data = CircuitBreakerData {
            state: CircuitBreakerState::Closed,
            failure_count: 0,
            success_count: 0,
            total_operations: 0,
            last_failure_time: None,
            last_state_change: now,
            failure_window_start: now,
            current_failure_window_count: 0,
            half_open_operations: 0,
        };

        Self {
            config,
            data: Arc::new(Mutex::new(data)),
        }
    }

    /// Execute an operation through the circuit breaker
    pub async fn execute<T, F, Fut>(&self, operation: F) -> Result<T, PlatformError>
    where
        F: FnOnce() -> Fut,
        Fut: std::future::Future<Output = Result<T, PlatformError>>,
    {
        // Check if operation is allowed
        if !self.is_operation_allowed() {
            return Err(PlatformError::InternalError {
                reason: "Circuit breaker is open - operation rejected".to_string(),
            });
        }

        // Execute the operation
        let result = operation().await;

        // Record the result
        match &result {
            Ok(_) => self.record_success(),
            Err(error) => {
                if self.should_count_as_failure(error) {
                    self.record_failure();
                }
            }
        }

        result
    }

    /// Check if an operation is allowed based on current circuit state
    pub fn is_operation_allowed(&self) -> bool {
        let mut data = self.data.lock().unwrap();
        let now = Instant::now();

        match data.state {
            CircuitBreakerState::Closed => true,
            CircuitBreakerState::Open => {
                // Check if enough time has passed to transition to half-open
                if now.duration_since(data.last_state_change) >= self.config.open_timeout {
                    data.state = CircuitBreakerState::HalfOpen;
                    data.last_state_change = now;
                    data.half_open_operations = 0;
                    data.success_count = 0;
                    true
                } else {
                    false
                }
            }
            CircuitBreakerState::HalfOpen => {
                // Allow limited operations in half-open state
                data.half_open_operations < self.config.half_open_max_operations
            }
        }
    }

    /// Record a successful operation
    fn record_success(&self) {
        let mut data = self.data.lock().unwrap();
        let now = Instant::now();
        
        data.total_operations += 1;

        match data.state {
            CircuitBreakerState::Closed => {
                // Reset failure count in closed state
                data.current_failure_window_count = 0;
                data.failure_window_start = now;
            }
            CircuitBreakerState::HalfOpen => {
                data.success_count += 1;
                data.half_open_operations += 1;
                
                // Check if we should transition to closed
                if data.success_count >= self.config.success_threshold {
                    data.state = CircuitBreakerState::Closed;
                    data.last_state_change = now;
                    data.failure_count = 0;
                    data.current_failure_window_count = 0;
                    data.failure_window_start = now;
                    data.half_open_operations = 0;
                }
            }
            CircuitBreakerState::Open => {
                // This shouldn't happen as operations should be blocked
                // But if it does, stay in open state
            }
        }
    }

    /// Record a failed operation
    fn record_failure(&self) {
        let mut data = self.data.lock().unwrap();
        let now = Instant::now();
        
        data.total_operations += 1;
        data.failure_count += 1;
        data.last_failure_time = Some(now);

        match data.state {
            CircuitBreakerState::Closed => {
                // Update failure window if needed
                if now.duration_since(data.failure_window_start) > self.config.failure_window {
                    data.failure_window_start = now;
                    data.current_failure_window_count = 0;
                }
                
                data.current_failure_window_count += 1;
                
                // Check if we should open the circuit
                if data.current_failure_window_count >= self.config.failure_threshold {
                    data.state = CircuitBreakerState::Open;
                    data.last_state_change = now;
                }
            }
            CircuitBreakerState::HalfOpen => {
                data.half_open_operations += 1;
                
                // Transition back to open on any failure in half-open
                data.state = CircuitBreakerState::Open;
                data.last_state_change = now;
                data.success_count = 0;
                data.half_open_operations = 0;
            }
            CircuitBreakerState::Open => {
                // This shouldn't happen as operations should be blocked
                // But if it does, stay in open state
            }
        }
    }

    /// Determine if an error should count as a failure for circuit breaking
    fn should_count_as_failure(&self, error: &PlatformError) -> bool {
        match error {
            // Network and connection errors should trigger circuit breaker
            PlatformError::ConnectionFailed { .. } |
            PlatformError::ConnectionTimeout { .. } |
            PlatformError::Disconnected { .. } |
            PlatformError::NetworkError { .. } |
            PlatformError::RequestTimeout { .. } |
            PlatformError::ApiLimitReached { .. } |
            PlatformError::InternalError { .. } => true,

            // Rate limiting might be temporary, count as failure but with lower weight
            PlatformError::RateLimitExceeded { .. } => true,

            // Authentication failures should trigger circuit breaker
            PlatformError::AuthenticationFailed { .. } |
            PlatformError::InvalidCredentials { .. } => true,

            // Platform-specific errors should trigger circuit breaker
            PlatformError::PlatformNotSupported { .. } |
            PlatformError::InitializationFailed { .. } => true,

            // Business logic errors shouldn't trigger circuit breaker
            PlatformError::OrderValidationFailed { .. } |
            PlatformError::OrderRejected { .. } |
            PlatformError::OrderNotFound { .. } |
            PlatformError::PositionNotFound { .. } |
            PlatformError::InsufficientMargin { .. } |
            PlatformError::InsufficientFunds { .. } |
            PlatformError::TradingNotAllowed { .. } |
            PlatformError::SymbolNotFound { .. } |
            PlatformError::AccountNotFound { .. } |
            PlatformError::FeatureNotSupported { .. } => false,

            // Market data errors depend on context
            PlatformError::MarketDataUnavailable { .. } |
            PlatformError::SubscriptionFailed { .. } => true,

            // Configuration errors should trigger circuit breaker
            PlatformError::ConfigurationError { .. } => true,

            // Platform-specific errors should trigger circuit breaker
            PlatformError::TradeLocker { .. } |
            PlatformError::DXTrade { .. } |
            PlatformError::MetaTrader { .. } => true,

            // Unknown errors should trigger circuit breaker to be safe
            PlatformError::Unknown { .. } => true,

            // Default case
            _ => true,
        }
    }

    /// Get current circuit breaker statistics
    pub fn get_stats(&self) -> CircuitBreakerStats {
        let data = self.data.lock().unwrap();
        
        CircuitBreakerStats {
            state: data.state.clone(),
            failure_count: data.failure_count,
            success_count: data.success_count,
            total_operations: data.total_operations,
            last_failure_time: data.last_failure_time.map(|t| {
                chrono::Utc::now() - chrono::Duration::from_std(t.elapsed()).unwrap_or_default()
            }),
            last_state_change: chrono::Utc::now() - chrono::Duration::from_std(data.last_state_change.elapsed()).unwrap_or_default(),
            current_failure_window_count: data.current_failure_window_count,
        }
    }

    /// Get current circuit breaker state
    pub fn get_state(&self) -> CircuitBreakerState {
        let data = self.data.lock().unwrap();
        data.state.clone()
    }

    /// Manually reset the circuit breaker to closed state
    pub fn reset(&self) {
        let mut data = self.data.lock().unwrap();
        let now = Instant::now();
        
        data.state = CircuitBreakerState::Closed;
        data.failure_count = 0;
        data.success_count = 0;
        data.last_failure_time = None;
        data.last_state_change = now;
        data.failure_window_start = now;
        data.current_failure_window_count = 0;
        data.half_open_operations = 0;
    }

    /// Force the circuit breaker to open state (for testing or emergency)
    pub fn force_open(&self) {
        let mut data = self.data.lock().unwrap();
        data.state = CircuitBreakerState::Open;
        data.last_state_change = Instant::now();
    }

    /// Check if the circuit breaker is healthy
    pub fn is_healthy(&self) -> bool {
        let data = self.data.lock().unwrap();
        match data.state {
            CircuitBreakerState::Closed => true,
            CircuitBreakerState::HalfOpen => data.success_count > 0,
            CircuitBreakerState::Open => false,
        }
    }

    /// Get failure rate in the current window
    pub fn get_failure_rate(&self) -> f64 {
        let data = self.data.lock().unwrap();
        let now = Instant::now();
        
        if data.total_operations == 0 {
            return 0.0;
        }

        // Calculate failure rate in current window
        let window_operations = if now.duration_since(data.failure_window_start) <= self.config.failure_window {
            data.current_failure_window_count as u64
        } else {
            0
        };

        if window_operations == 0 {
            0.0
        } else {
            data.current_failure_window_count as f64 / window_operations as f64
        }
    }
}

impl Default for CircuitBreaker {
    fn default() -> Self {
        Self::new()
    }
}

impl Clone for CircuitBreaker {
    fn clone(&self) -> Self {
        Self {
            config: self.config.clone(),
            data: Arc::clone(&self.data),
        }
    }
}

/// Circuit breaker wrapper for platform adapters
pub struct CircuitBreakerWrapper<T> {
    inner: T,
    circuit_breaker: CircuitBreaker,
    operation_name: String,
}

impl<T> CircuitBreakerWrapper<T> {
    pub fn new(inner: T, operation_name: String) -> Self {
        Self::with_config(inner, operation_name, CircuitBreakerConfig::default())
    }

    pub fn with_config(inner: T, operation_name: String, config: CircuitBreakerConfig) -> Self {
        Self {
            inner,
            circuit_breaker: CircuitBreaker::with_config(config),
            operation_name,
        }
    }

    pub fn get_inner(&self) -> &T {
        &self.inner
    }

    pub fn get_inner_mut(&mut self) -> &mut T {
        &mut self.inner
    }

    pub fn get_circuit_breaker(&self) -> &CircuitBreaker {
        &self.circuit_breaker
    }

    pub async fn execute_with_circuit_breaker<R, F, Fut>(&self, operation: F) -> Result<R, PlatformError>
    where
        F: FnOnce(&T) -> Fut,
        Fut: std::future::Future<Output = Result<R, PlatformError>>,
    {
        self.circuit_breaker.execute(|| operation(&self.inner)).await
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::time::{sleep, Duration as TokioDuration};

    #[tokio::test]
    async fn test_circuit_breaker_closed_state() {
        let circuit_breaker = CircuitBreaker::new();
        
        // Should start in closed state
        assert_eq!(circuit_breaker.get_state(), CircuitBreakerState::Closed);
        assert!(circuit_breaker.is_operation_allowed());
        assert!(circuit_breaker.is_healthy());
    }

    #[tokio::test]
    async fn test_circuit_breaker_opens_on_failures() {
        let config = CircuitBreakerConfig {
            failure_threshold: 3,
            ..Default::default()
        };
        let circuit_breaker = CircuitBreaker::with_config(config);
        
        // Simulate failures
        for i in 0..3 {
            let result: Result<(), PlatformError> = circuit_breaker.execute(|| async {
                Err(PlatformError::ConnectionFailed { 
                    reason: format!("Test failure {}", i) 
                })
            }).await;
            
            assert!(result.is_err());
            
            if i < 2 {
                assert_eq!(circuit_breaker.get_state(), CircuitBreakerState::Closed);
            }
        }
        
        // Circuit should now be open
        assert_eq!(circuit_breaker.get_state(), CircuitBreakerState::Open);
        assert!(!circuit_breaker.is_operation_allowed());
        assert!(!circuit_breaker.is_healthy());
    }

    #[tokio::test]
    async fn test_circuit_breaker_rejects_operations_when_open() {
        let circuit_breaker = CircuitBreaker::new();
        circuit_breaker.force_open();
        
        assert_eq!(circuit_breaker.get_state(), CircuitBreakerState::Open);
        
        // Operations should be rejected
        let result: Result<(), PlatformError> = circuit_breaker.execute(|| async {
            Ok(())
        }).await;
        
        assert!(result.is_err());
        match result.unwrap_err() {
            PlatformError::InternalError { reason } => {
                assert!(reason.contains("Circuit breaker is open"));
            }
            _ => panic!("Expected internal error about circuit breaker"),
        }
    }

    #[tokio::test]
    async fn test_circuit_breaker_transitions_to_half_open() {
        let config = CircuitBreakerConfig {
            failure_threshold: 2,
            open_timeout: Duration::from_millis(100),
            ..Default::default()
        };
        let circuit_breaker = CircuitBreaker::with_config(config);
        
        // Force failures to open the circuit
        for _ in 0..2 {
            let _ = circuit_breaker.execute(|| async {
                Err(PlatformError::ConnectionFailed { 
                    reason: "Test failure".to_string() 
                })
            }).await;
        }
        
        assert_eq!(circuit_breaker.get_state(), CircuitBreakerState::Open);
        
        // Wait for timeout
        sleep(TokioDuration::from_millis(150)).await;
        
        // Next operation should transition to half-open
        assert!(circuit_breaker.is_operation_allowed());
        
        let result: Result<(), PlatformError> = circuit_breaker.execute(|| async {
            Ok(())
        }).await;
        
        assert!(result.is_ok());
        assert_eq!(circuit_breaker.get_state(), CircuitBreakerState::HalfOpen);
    }

    #[tokio::test]
    async fn test_circuit_breaker_closes_after_successful_operations() {
        let config = CircuitBreakerConfig {
            failure_threshold: 2,
            success_threshold: 2,
            open_timeout: Duration::from_millis(50),
            ..Default::default()
        };
        let circuit_breaker = CircuitBreaker::with_config(config);
        
        // Open the circuit
        for _ in 0..2 {
            let _ = circuit_breaker.execute(|| async {
                Err(PlatformError::NetworkError { 
                    reason: "Test failure".to_string() 
                })
            }).await;
        }
        assert_eq!(circuit_breaker.get_state(), CircuitBreakerState::Open);
        
        // Wait and transition to half-open
        sleep(TokioDuration::from_millis(100)).await;
        
        // Successful operations should close the circuit
        for _ in 0..2 {
            let result: Result<(), PlatformError> = circuit_breaker.execute(|| async {
                Ok(())
            }).await;
            assert!(result.is_ok());
        }
        
        assert_eq!(circuit_breaker.get_state(), CircuitBreakerState::Closed);
        assert!(circuit_breaker.is_healthy());
    }

    #[tokio::test]
    async fn test_circuit_breaker_failure_classification() {
        let circuit_breaker = CircuitBreaker::new();
        
        // Connection errors should count as failures
        assert!(circuit_breaker.should_count_as_failure(&PlatformError::ConnectionFailed { 
            reason: "test".to_string() 
        }));
        
        assert!(circuit_breaker.should_count_as_failure(&PlatformError::NetworkError { 
            reason: "test".to_string() 
        }));
        
        // Business logic errors shouldn't count as failures
        assert!(!circuit_breaker.should_count_as_failure(&PlatformError::OrderRejected { 
            reason: "test".to_string(),
            platform_code: None,
        }));
        
        assert!(!circuit_breaker.should_count_as_failure(&PlatformError::InsufficientMargin { 
            required: rust_decimal::Decimal::new(100, 0),
            available: rust_decimal::Decimal::new(50, 0),
        }));
    }

    #[tokio::test]
    async fn test_circuit_breaker_stats() {
        let circuit_breaker = CircuitBreaker::new();
        
        // Initial stats
        let stats = circuit_breaker.get_stats();
        assert_eq!(stats.state, CircuitBreakerState::Closed);
        assert_eq!(stats.total_operations, 0);
        assert_eq!(stats.failure_count, 0);
        
        // Execute some operations
        let _ = circuit_breaker.execute(|| async { Ok(()) }).await;
        let _ = circuit_breaker.execute(|| async { 
            Err(PlatformError::ConnectionFailed { reason: "test".to_string() })
        }).await;
        
        let stats = circuit_breaker.get_stats();
        assert_eq!(stats.total_operations, 2);
        assert_eq!(stats.failure_count, 1);
        assert!(stats.last_failure_time.is_some());
    }

    #[tokio::test]
    async fn test_circuit_breaker_reset() {
        let circuit_breaker = CircuitBreaker::new();
        circuit_breaker.force_open();
        
        assert_eq!(circuit_breaker.get_state(), CircuitBreakerState::Open);
        
        // Reset should close the circuit
        circuit_breaker.reset();
        assert_eq!(circuit_breaker.get_state(), CircuitBreakerState::Closed);
        assert!(circuit_breaker.is_healthy());
        
        let stats = circuit_breaker.get_stats();
        assert_eq!(stats.failure_count, 0);
        assert_eq!(stats.success_count, 0);
    }

    #[tokio::test]
    async fn test_circuit_breaker_wrapper() {
        struct MockService {
            should_fail: bool,
        }

        impl MockService {
            async fn operation(&self) -> Result<String, PlatformError> {
                if self.should_fail {
                    Err(PlatformError::ConnectionFailed { 
                        reason: "Mock failure".to_string() 
                    })
                } else {
                    Ok("Success".to_string())
                }
            }
        }

        let service = MockService { should_fail: false };
        let wrapper = CircuitBreakerWrapper::new(service, "test_operation".to_string());
        
        // Successful operation
        let result = wrapper.execute_with_circuit_breaker(|service| async {
            service.operation().await
        }).await;
        
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), "Success");
        
        // Check circuit breaker is healthy
        assert!(wrapper.get_circuit_breaker().is_healthy());
    }
}