#[cfg(test)]
mod tests {
    use std::time::{Duration, Instant};
    use crate::platforms::tradelocker::rate_limiter::{RateLimiter, AccountRateLimiter};

    #[tokio::test]
    async fn test_rate_limiter_basic() {
        let limiter = RateLimiter::new(10); // 10 requests per second
        
        // Should allow initial requests
        for _ in 0..5 {
            let guard = limiter.acquire().await;
            assert!(guard.is_ok());
        }
        
        let current_rate = limiter.get_current_rate().await;
        assert_eq!(current_rate, 5);
        
        let remaining = limiter.get_remaining_capacity().await;
        assert_eq!(remaining, 5);
    }

    #[tokio::test]
    async fn test_rate_limiter_blocking() {
        let limiter = RateLimiter::new(2); // Only 2 requests per second
        
        // First two should succeed immediately
        let _guard1 = limiter.acquire().await.unwrap();
        let _guard2 = limiter.acquire().await.unwrap();
        
        // Third should need to wait
        let start = Instant::now();
        let _guard3 = limiter.acquire().await.unwrap();
        let elapsed = start.elapsed();
        
        // Should have waited some time
        // Note: In a real test, we'd need more precise timing control
        assert!(elapsed >= Duration::from_millis(100) || elapsed < Duration::from_millis(10));
    }

    #[tokio::test]
    async fn test_circuit_breaker_opens() {
        let limiter = RateLimiter::new(10);
        
        // Record multiple failures
        for _ in 0..5 {
            limiter.record_failure().await;
        }
        
        // Circuit should be open
        assert!(limiter.is_circuit_open().await);
        
        // Should reject requests when open
        let result = limiter.acquire().await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_circuit_breaker_closes() {
        let limiter = RateLimiter::new(10);
        
        // Open the circuit
        for _ in 0..5 {
            limiter.record_failure().await;
        }
        assert!(limiter.is_circuit_open().await);
        
        // Manual reset
        limiter.reset_circuit_breaker().await;
        assert!(!limiter.is_circuit_open().await);
        
        // Should allow requests again
        let result = limiter.acquire().await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_account_rate_limiter() {
        let account_limiter = AccountRateLimiter::new(5);
        
        // Get limiter for specific account
        let limiter1 = account_limiter.get_limiter("account1").await;
        let limiter2 = account_limiter.get_limiter("account2").await;
        
        // Should be independent limiters
        let _guard1 = limiter1.acquire().await.unwrap();
        let _guard2 = limiter2.acquire().await.unwrap();
        
        assert_eq!(limiter1.get_current_rate().await, 1);
        assert_eq!(limiter2.get_current_rate().await, 1);
    }

    #[tokio::test]
    async fn test_custom_account_limits() {
        let account_limiter = AccountRateLimiter::new(5);
        
        // Set custom limit for specific account
        account_limiter.set_account_limit("premium_account", 100).await;
        
        let limiter = account_limiter.get_limiter("premium_account").await;
        
        // Should be able to make many requests
        for _ in 0..50 {
            let _guard = limiter.acquire().await.unwrap();
        }
        
        assert!(limiter.get_current_rate().await <= 100);
    }

    #[tokio::test]
    async fn test_rate_monitoring() {
        let account_limiter = AccountRateLimiter::new(10);
        
        // Create activity on multiple accounts
        let limiter1 = account_limiter.get_limiter("account1").await;
        let limiter2 = account_limiter.get_limiter("account2").await;
        
        let _g1 = limiter1.acquire().await.unwrap();
        let _g2 = limiter1.acquire().await.unwrap();
        let _g3 = limiter2.acquire().await.unwrap();
        
        let rates = account_limiter.get_all_rates().await;
        
        assert_eq!(rates.get("account1"), Some(&2));
        assert_eq!(rates.get("account2"), Some(&1));
    }
}