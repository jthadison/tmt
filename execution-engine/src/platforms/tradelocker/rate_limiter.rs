use std::sync::Arc;
use std::time::{Duration, Instant};
use std::collections::VecDeque;
use tokio::sync::{Mutex, Semaphore};
use tokio::time::sleep;
use tracing::{debug, warn, info};

use super::{TradeLockerError, Result};

#[derive(Debug)]
pub struct RateLimiter {
    requests_per_second: u32,
    window: Arc<Mutex<VecDeque<Instant>>>,
    semaphore: Arc<Semaphore>,
    circuit_breaker: Arc<Mutex<CircuitBreaker>>,
}

#[derive(Debug)]
struct CircuitBreaker {
    failure_count: u32,
    last_failure: Option<Instant>,
    state: CircuitState,
    threshold: u32,
    reset_timeout: Duration,
}

#[derive(Debug, Clone, Copy, PartialEq)]
enum CircuitState {
    Closed,     // Normal operation
    Open,       // Blocking requests
    HalfOpen,   // Testing recovery
}

impl RateLimiter {
    pub fn new(requests_per_second: u32) -> Self {
        let circuit_breaker = CircuitBreaker {
            failure_count: 0,
            last_failure: None,
            state: CircuitState::Closed,
            threshold: 5,
            reset_timeout: Duration::from_secs(30),
        };

        Self {
            requests_per_second,
            window: Arc::new(Mutex::new(VecDeque::new())),
            semaphore: Arc::new(Semaphore::new(requests_per_second as usize)),
            circuit_breaker: Arc::new(Mutex::new(circuit_breaker)),
        }
    }

    pub async fn acquire(&self) -> Result<RateLimitGuard<'_>> {
        // Check circuit breaker first
        self.check_circuit_breaker().await?;

        // Acquire semaphore permit
        let permit = self.semaphore
            .acquire()
            .await
            .map_err(|e| TradeLockerError::Internal(format!("Semaphore error: {}", e)))?;

        // Clean old timestamps and check rate
        let mut window = self.window.lock().await;
        let now = Instant::now();
        let one_second_ago = now - Duration::from_secs(1);

        // Remove timestamps older than 1 second
        while let Some(&front) = window.front() {
            if front < one_second_ago {
                window.pop_front();
            } else {
                break;
            }
        }

        // Check if we're at the limit
        if window.len() >= self.requests_per_second as usize {
            // Calculate how long to wait
            if let Some(&oldest) = window.front() {
                let wait_time = Duration::from_secs(1) - (now - oldest);
                if wait_time > Duration::ZERO {
                    drop(window);
                    debug!("Rate limit reached, waiting {:?}", wait_time);
                    sleep(wait_time).await;
                    
                    // Re-acquire the lock and clean again
                    window = self.window.lock().await;
                    while let Some(&front) = window.front() {
                        if front < now - Duration::from_secs(1) {
                            window.pop_front();
                        } else {
                            break;
                        }
                    }
                }
            }
        }

        // Add current timestamp
        window.push_back(now);
        
        Ok(RateLimitGuard {
            _permit: permit,
            limiter: self.clone(),
        })
    }

    async fn check_circuit_breaker(&self) -> Result<()> {
        let mut breaker = self.circuit_breaker.lock().await;

        match breaker.state {
            CircuitState::Closed => Ok(()),
            CircuitState::Open => {
                if let Some(last_failure) = breaker.last_failure {
                    if Instant::now() - last_failure > breaker.reset_timeout {
                        info!("Circuit breaker transitioning to half-open");
                        breaker.state = CircuitState::HalfOpen;
                        breaker.failure_count = 0;
                        Ok(())
                    } else {
                        Err(TradeLockerError::RateLimit {
                            retry_after: breaker.reset_timeout.as_secs(),
                        })
                    }
                } else {
                    Ok(())
                }
            }
            CircuitState::HalfOpen => {
                // Allow one request through for testing
                Ok(())
            }
        }
    }

    pub async fn record_success(&self) {
        let mut breaker = self.circuit_breaker.lock().await;
        
        if breaker.state == CircuitState::HalfOpen {
            info!("Circuit breaker closing after successful request");
            breaker.state = CircuitState::Closed;
            breaker.failure_count = 0;
        }
    }

    pub async fn record_failure(&self) {
        let mut breaker = self.circuit_breaker.lock().await;
        
        breaker.failure_count += 1;
        breaker.last_failure = Some(Instant::now());

        match breaker.state {
            CircuitState::Closed => {
                if breaker.failure_count >= breaker.threshold {
                    warn!("Circuit breaker opening after {} failures", breaker.failure_count);
                    breaker.state = CircuitState::Open;
                }
            }
            CircuitState::HalfOpen => {
                warn!("Circuit breaker reopening after failure in half-open state");
                breaker.state = CircuitState::Open;
            }
            CircuitState::Open => {
                // Already open, just update failure count
            }
        }
    }

    pub async fn get_current_rate(&self) -> usize {
        let window = self.window.lock().await;
        let now = Instant::now();
        let one_second_ago = now - Duration::from_secs(1);
        
        window.iter()
            .filter(|&&timestamp| timestamp >= one_second_ago)
            .count()
    }

    pub async fn get_remaining_capacity(&self) -> usize {
        let current = self.get_current_rate().await;
        (self.requests_per_second as usize).saturating_sub(current)
    }

    pub async fn is_circuit_open(&self) -> bool {
        let breaker = self.circuit_breaker.lock().await;
        breaker.state == CircuitState::Open
    }

    pub async fn reset_circuit_breaker(&self) {
        let mut breaker = self.circuit_breaker.lock().await;
        breaker.state = CircuitState::Closed;
        breaker.failure_count = 0;
        breaker.last_failure = None;
        info!("Circuit breaker manually reset");
    }
}

impl Clone for RateLimiter {
    fn clone(&self) -> Self {
        Self {
            requests_per_second: self.requests_per_second,
            window: self.window.clone(),
            semaphore: self.semaphore.clone(),
            circuit_breaker: self.circuit_breaker.clone(),
        }
    }
}

#[derive(Debug)]
pub struct RateLimitGuard<'a> {
    _permit: tokio::sync::SemaphorePermit<'a>,
    limiter: RateLimiter,
}

impl<'a> Drop for RateLimitGuard<'a> {
    fn drop(&mut self) {
        // Permit is automatically released when dropped
    }
}

#[derive(Debug)]
pub struct AccountRateLimiter {
    limiters: Arc<Mutex<std::collections::HashMap<String, RateLimiter>>>,
    default_limit: u32,
}

impl AccountRateLimiter {
    pub fn new(default_limit: u32) -> Self {
        Self {
            limiters: Arc::new(Mutex::new(std::collections::HashMap::new())),
            default_limit,
        }
    }

    pub async fn get_limiter(&self, account_id: &str) -> RateLimiter {
        let mut limiters = self.limiters.lock().await;
        
        limiters.entry(account_id.to_string())
            .or_insert_with(|| RateLimiter::new(self.default_limit))
            .clone()
    }

    pub async fn set_account_limit(&self, account_id: &str, limit: u32) {
        let mut limiters = self.limiters.lock().await;
        limiters.insert(account_id.to_string(), RateLimiter::new(limit));
    }

    pub async fn get_all_rates(&self) -> std::collections::HashMap<String, usize> {
        let limiters = self.limiters.lock().await;
        let mut rates = std::collections::HashMap::new();
        
        for (account_id, limiter) in limiters.iter() {
            rates.insert(account_id.clone(), limiter.get_current_rate().await);
        }
        
        rates
    }
}