use std::sync::Arc;
use async_trait::async_trait;
use tokio::sync::mpsc;

use super::{
    ITradingPlatform, PlatformError, CircuitBreaker, ConnectionPool, 
    UnifiedOrder, UnifiedOrderResponse, UnifiedPosition, UnifiedAccountInfo,
    UnifiedMarketData, OrderModification, PlatformEvent, MarginInfo,
    PlatformConfig, ConnectionPoolConfig, CircuitBreakerConfig,
    ConnectionPoolStats, CircuitBreakerStats, CircuitBreakerState
};
use super::interfaces::{OrderFilter, HealthStatus, DiagnosticsInfo};
use super::capabilities::PlatformCapabilities;
use super::interfaces::EventFilter;
use crate::platforms::PlatformType;

/// Resilient adapter that combines circuit breaker and connection pooling
/// for high-frequency trading scenarios with fault tolerance
pub struct ResilientPlatformAdapter {
    account_id: String,
    platform_type: PlatformType,
    connection_pool: Arc<ConnectionPool>,
    circuit_breaker: CircuitBreaker,
    capabilities: PlatformCapabilities,
}

impl ResilientPlatformAdapter {
    /// Create a new resilient adapter with default configurations
    pub async fn new(
        account_id: String,
        platform_config: PlatformConfig,
    ) -> Result<Self, PlatformError> {
        Self::with_configs(
            account_id,
            platform_config,
            ConnectionPoolConfig::default(),
            CircuitBreakerConfig::default(),
        ).await
    }

    /// Create a new resilient adapter with custom configurations
    pub async fn with_configs(
        account_id: String,
        platform_config: PlatformConfig,
        pool_config: ConnectionPoolConfig,
        circuit_config: CircuitBreakerConfig,
    ) -> Result<Self, PlatformError> {
        let platform_type = platform_config.platform_type();
        
        // Create connection pool
        let connection_pool = ConnectionPool::with_config(platform_config, pool_config).await?;
        let connection_pool = Arc::new(connection_pool);
        
        // Create circuit breaker
        let circuit_breaker = CircuitBreaker::with_config(circuit_config);
        
        // Get capabilities from a test connection
        let test_handle = connection_pool.get_connection().await?;
        let capabilities = test_handle.platform().capabilities();
        drop(test_handle);

        Ok(Self {
            account_id,
            platform_type,
            connection_pool,
            circuit_breaker,
            capabilities,
        })
    }

    /// Execute an operation with both circuit breaker and connection pooling
    async fn execute_with_resilience<T, F, Fut>(&self, operation: F) -> Result<T, PlatformError>
    where
        F: FnOnce(&dyn ITradingPlatform) -> Fut,
        Fut: std::future::Future<Output = Result<T, PlatformError>>,
    {
        self.circuit_breaker.execute(|| async {
            let connection_handle = self.connection_pool.get_connection().await?;
            let platform = connection_handle.platform();
            operation(platform).await
        }).await
    }

    /// Get connection pool statistics
    pub async fn get_pool_stats(&self) -> ConnectionPoolStats {
        self.connection_pool.get_stats().await
    }

    /// Get circuit breaker statistics
    pub fn get_circuit_breaker_stats(&self) -> CircuitBreakerStats {
        self.circuit_breaker.get_stats()
    }

    /// Check if the adapter is in a healthy state
    pub async fn is_adapter_healthy(&self) -> bool {
        self.connection_pool.is_healthy().await && self.circuit_breaker.is_healthy()
    }

    /// Warm up the connection pool
    pub async fn warm_up(&self) -> Result<(), PlatformError> {
        self.connection_pool.warm_up().await
    }

    /// Reset the circuit breaker (for recovery scenarios)
    pub fn reset_circuit_breaker(&self) {
        self.circuit_breaker.reset();
    }

    /// Force circuit breaker open (for emergency scenarios)
    pub fn emergency_stop(&self) {
        self.circuit_breaker.force_open();
    }

    /// Get comprehensive health and performance metrics
    pub async fn get_comprehensive_diagnostics(&self) -> ResilientAdapterDiagnostics {
        let pool_stats = self.get_pool_stats().await;
        let circuit_stats = self.get_circuit_breaker_stats();
        let is_healthy = self.is_adapter_healthy().await;

        ResilientAdapterDiagnostics {
            account_id: self.account_id.clone(),
            platform_type: self.platform_type.clone(),
            is_healthy,
            pool_stats,
            circuit_stats,
            timestamp: chrono::Utc::now(),
        }
    }
}

#[async_trait]
impl ITradingPlatform for ResilientPlatformAdapter {
    fn platform_type(&self) -> PlatformType {
        self.platform_type.clone()
    }

    fn platform_name(&self) -> &str {
        "ResilientAdapter"
    }

    fn platform_version(&self) -> &str {
        "2.0.0"
    }

    async fn connect(&mut self) -> Result<(), PlatformError> {
        // Connection management is handled by the pool
        // This is a no-op for the resilient adapter
        Ok(())
    }

    async fn disconnect(&mut self) -> Result<(), PlatformError> {
        // Graceful shutdown of pool would happen here
        Ok(())
    }

    async fn is_connected(&self) -> bool {
        self.connection_pool.is_healthy().await
    }

    async fn ping(&self) -> Result<u64, PlatformError> {
        self.execute_with_resilience(|platform| async move {
            platform.ping().await
        }).await
    }

    async fn place_order(&self, order: UnifiedOrder) -> Result<UnifiedOrderResponse, PlatformError> {
        self.execute_with_resilience(|platform| async move {
            platform.place_order(order).await
        }).await
    }

    async fn modify_order(&self, order_id: &str, modifications: OrderModification) -> Result<UnifiedOrderResponse, PlatformError> {
        let order_id = order_id.to_string();
        self.execute_with_resilience(|platform| async move {
            platform.modify_order(&order_id, modifications).await
        }).await
    }

    async fn cancel_order(&self, order_id: &str) -> Result<(), PlatformError> {
        let order_id = order_id.to_string();
        self.execute_with_resilience(|platform| async move {
            platform.cancel_order(&order_id).await
        }).await
    }

    async fn get_order(&self, order_id: &str) -> Result<UnifiedOrderResponse, PlatformError> {
        let order_id = order_id.to_string();
        self.execute_with_resilience(|platform| async move {
            platform.get_order(&order_id).await
        }).await
    }

    async fn get_orders(&self, filter: Option<OrderFilter>) -> Result<Vec<UnifiedOrderResponse>, PlatformError> {
        self.execute_with_resilience(|platform| async move {
            platform.get_orders(filter).await
        }).await
    }

    async fn get_positions(&self) -> Result<Vec<UnifiedPosition>, PlatformError> {
        self.execute_with_resilience(|platform| async move {
            platform.get_positions().await
        }).await
    }

    async fn get_position(&self, symbol: &str) -> Result<Option<UnifiedPosition>, PlatformError> {
        let symbol = symbol.to_string();
        self.execute_with_resilience(|platform| async move {
            platform.get_position(&symbol).await
        }).await
    }

    async fn close_position(&self, symbol: &str, quantity: Option<rust_decimal::Decimal>) -> Result<UnifiedOrderResponse, PlatformError> {
        let symbol = symbol.to_string();
        self.execute_with_resilience(|platform| async move {
            platform.close_position(&symbol, quantity).await
        }).await
    }

    async fn get_account_info(&self) -> Result<UnifiedAccountInfo, PlatformError> {
        self.execute_with_resilience(|platform| async move {
            platform.get_account_info().await
        }).await
    }

    async fn get_balance(&self) -> Result<rust_decimal::Decimal, PlatformError> {
        self.execute_with_resilience(|platform| async move {
            platform.get_balance().await
        }).await
    }

    async fn get_margin_info(&self) -> Result<MarginInfo, PlatformError> {
        self.execute_with_resilience(|platform| async move {
            platform.get_margin_info().await
        }).await
    }

    async fn get_market_data(&self, symbol: &str) -> Result<UnifiedMarketData, PlatformError> {
        let symbol = symbol.to_string();
        self.execute_with_resilience(|platform| async move {
            platform.get_market_data(&symbol).await
        }).await
    }

    async fn subscribe_market_data(&self, symbols: Vec<String>) -> Result<mpsc::Receiver<UnifiedMarketData>, PlatformError> {
        self.execute_with_resilience(|platform| async move {
            platform.subscribe_market_data(symbols).await
        }).await
    }

    async fn unsubscribe_market_data(&self, symbols: Vec<String>) -> Result<(), PlatformError> {
        self.execute_with_resilience(|platform| async move {
            platform.unsubscribe_market_data(symbols).await
        }).await
    }

    fn capabilities(&self) -> PlatformCapabilities {
        self.capabilities.clone()
    }

    async fn subscribe_events(&self) -> Result<mpsc::Receiver<PlatformEvent>, PlatformError> {
        self.execute_with_resilience(|platform| async move {
            platform.subscribe_events().await
        }).await
    }

    async fn get_event_history(&self, filter: EventFilter) -> Result<Vec<PlatformEvent>, PlatformError> {
        self.execute_with_resilience(|platform| async move {
            platform.get_event_history(filter).await
        }).await
    }

    async fn health_check(&self) -> Result<HealthStatus, PlatformError> {
        // Combine platform health with adapter health
        let platform_health = self.execute_with_resilience(|platform| async move {
            platform.health_check().await
        }).await?;

        let adapter_healthy = self.is_adapter_healthy().await;
        let circuit_stats = self.circuit_breaker.get_stats();
        let pool_stats = self.connection_pool.get_stats().await;

        let mut issues = platform_health.issues.clone();
        
        if !adapter_healthy {
            issues.push("Adapter not healthy".to_string());
        }
        
        if circuit_stats.state != super::CircuitBreakerState::Closed {
            issues.push(format!("Circuit breaker is {:?}", circuit_stats.state));
        }
        
        if pool_stats.unhealthy_connections > 0 {
            issues.push(format!("{} unhealthy connections in pool", pool_stats.unhealthy_connections));
        }

        Ok(HealthStatus {
            is_healthy: platform_health.is_healthy && adapter_healthy,
            last_ping: platform_health.last_ping,
            latency_ms: platform_health.latency_ms,
            error_rate: circuit_stats.failure_count as f64 / (circuit_stats.total_operations.max(1) as f64),
            uptime_seconds: platform_health.uptime_seconds,
            issues,
        })
    }

    async fn get_diagnostics(&self) -> Result<DiagnosticsInfo, PlatformError> {
        let platform_diagnostics = self.execute_with_resilience(|platform| async move {
            platform.get_diagnostics().await
        }).await?;

        let pool_stats = self.get_pool_stats().await;
        let circuit_stats = self.get_circuit_breaker_stats();

        let mut performance_metrics = platform_diagnostics.performance_metrics;
        performance_metrics.insert("pool_total_connections".to_string(), serde_json::Value::Number((pool_stats.total_connections as u64).into()));
        performance_metrics.insert("pool_active_connections".to_string(), serde_json::Value::Number((pool_stats.active_connections as u64).into()));
        performance_metrics.insert("pool_hit_rate".to_string(), serde_json::Value::Number(
            serde_json::Number::from_f64(
                pool_stats.pool_hits as f64 / (pool_stats.pool_hits + pool_stats.pool_misses).max(1) as f64
            ).unwrap_or(serde_json::Number::from(0))
        ));
        performance_metrics.insert("circuit_breaker_state".to_string(), serde_json::Value::String(format!("{:?}", circuit_stats.state)));
        performance_metrics.insert("circuit_breaker_failure_count".to_string(), serde_json::Value::Number(circuit_stats.failure_count.into()));

        Ok(DiagnosticsInfo {
            connection_status: if self.is_adapter_healthy().await { "Healthy".to_string() } else { "Degraded".to_string() },
            api_limits: platform_diagnostics.api_limits,
            performance_metrics,
            last_errors: platform_diagnostics.last_errors,
            platform_specific: platform_diagnostics.platform_specific,
        })
    }
}

/// Comprehensive diagnostics for the resilient adapter
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ResilientAdapterDiagnostics {
    pub account_id: String,
    pub platform_type: PlatformType,
    pub is_healthy: bool,
    pub pool_stats: ConnectionPoolStats,
    pub circuit_stats: CircuitBreakerStats,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

impl ResilientAdapterDiagnostics {
    /// Calculate overall performance score (0-100)
    pub fn performance_score(&self) -> f64 {
        let mut score = 100.0;

        // Reduce score based on circuit breaker failures
        if self.circuit_stats.total_operations > 0 {
            let failure_rate = self.circuit_stats.failure_count as f64 / self.circuit_stats.total_operations as f64;
            score -= failure_rate * 50.0; // Max 50 point reduction for failures
        }

        // Reduce score for circuit breaker being open
        match self.circuit_stats.state {
            CircuitBreakerState::Closed => {}, // No reduction
            CircuitBreakerState::HalfOpen => score -= 10.0,
            CircuitBreakerState::Open => score -= 30.0,
        }

        // Reduce score for unhealthy connections
        if self.pool_stats.total_connections > 0 {
            let unhealthy_ratio = self.pool_stats.unhealthy_connections as f64 / self.pool_stats.total_connections as f64;
            score -= unhealthy_ratio * 20.0; // Max 20 point reduction for unhealthy connections
        }

        // Bonus for good pool hit rate
        if self.pool_stats.pool_hits + self.pool_stats.pool_misses > 0 {
            let hit_rate = self.pool_stats.pool_hits as f64 / (self.pool_stats.pool_hits + self.pool_stats.pool_misses) as f64;
            if hit_rate > 0.9 {
                score += 5.0; // Bonus for high hit rate
            }
        }

        score.max(0.0).min(100.0)
    }

    /// Get a human-readable status summary
    pub fn status_summary(&self) -> String {
        if !self.is_healthy {
            return "UNHEALTHY".to_string();
        }

        match self.circuit_stats.state {
            CircuitBreakerState::Closed => {
                if self.pool_stats.unhealthy_connections == 0 {
                    "HEALTHY"
                } else {
                    "DEGRADED"
                }
            }
            CircuitBreakerState::HalfOpen => "RECOVERING",
            CircuitBreakerState::Open => "CIRCUIT_OPEN",
        }.to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_resilient_adapter_diagnostics() {
        let diagnostics = ResilientAdapterDiagnostics {
            account_id: "test_account".to_string(),
            platform_type: PlatformType::TradeLocker,
            is_healthy: true,
            pool_stats: ConnectionPoolStats::default(),
            circuit_stats: CircuitBreakerStats {
                state: CircuitBreakerState::Closed,
                failure_count: 0,
                success_count: 10,
                total_operations: 10,
                last_failure_time: None,
                last_state_change: chrono::Utc::now(),
                current_failure_window_count: 0,
            },
            timestamp: chrono::Utc::now(),
        };

        assert_eq!(diagnostics.status_summary(), "HEALTHY");
        assert!(diagnostics.performance_score() >= 95.0);
    }

    #[test]
    fn test_performance_score_calculation() {
        let mut diagnostics = ResilientAdapterDiagnostics {
            account_id: "test".to_string(),
            platform_type: PlatformType::TradeLocker,
            is_healthy: false,
            pool_stats: ConnectionPoolStats {
                total_connections: 10,
                unhealthy_connections: 2,
                ..Default::default()
            },
            circuit_stats: CircuitBreakerStats {
                state: CircuitBreakerState::Open,
                failure_count: 5,
                total_operations: 100,
                ..Default::default()
            },
            timestamp: chrono::Utc::now(),
        };

        let score = diagnostics.performance_score();
        assert!(score < 100.0); // Should be reduced due to issues
        assert!(score > 0.0);   // But not zero

        // Test healthy scenario
        diagnostics.is_healthy = true;
        diagnostics.circuit_stats.state = CircuitBreakerState::Closed;
        diagnostics.circuit_stats.failure_count = 0;
        diagnostics.pool_stats.unhealthy_connections = 0;
        
        let healthy_score = diagnostics.performance_score();
        assert!(healthy_score > score); // Should be better
    }
}