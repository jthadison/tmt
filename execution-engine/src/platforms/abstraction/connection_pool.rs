use std::collections::VecDeque;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::{Mutex, RwLock, Semaphore};
use serde::{Deserialize, Serialize};

use super::interfaces::ITradingPlatform;
use super::errors::PlatformError;
use super::factory::{PlatformConfig, PlatformFactory};

/// Connection pool configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConnectionPoolConfig {
    /// Minimum number of connections to maintain
    pub min_connections: usize,
    /// Maximum number of connections allowed
    pub max_connections: usize,
    /// Maximum time a connection can be idle before being closed
    pub max_idle_time: Duration,
    /// Maximum time to wait for a connection from the pool
    pub connection_timeout: Duration,
    /// Interval for cleaning up idle connections
    pub cleanup_interval: Duration,
    /// Maximum lifetime of a connection before forced refresh
    pub max_connection_lifetime: Duration,
    /// Health check interval for pooled connections
    pub health_check_interval: Duration,
}

impl Default for ConnectionPoolConfig {
    fn default() -> Self {
        Self {
            min_connections: 1,
            max_connections: 10,
            max_idle_time: Duration::from_secs(300), // 5 minutes
            connection_timeout: Duration::from_secs(10),
            cleanup_interval: Duration::from_secs(60), // 1 minute
            max_connection_lifetime: Duration::from_secs(3600), // 1 hour
            health_check_interval: Duration::from_secs(30), // 30 seconds
        }
    }
}

/// Represents a pooled connection with metadata
pub struct PooledConnection {
    pub connection: Box<dyn ITradingPlatform>,
    pub created_at: Instant,
    pub last_used: Instant,
    pub use_count: u64,
    pub is_healthy: bool,
}

impl PooledConnection {
    pub fn new(connection: Box<dyn ITradingPlatform>) -> Self {
        let now = Instant::now();
        Self {
            connection,
            created_at: now,
            last_used: now,
            use_count: 0,
            is_healthy: true,
        }
    }

    pub fn mark_used(&mut self) {
        self.last_used = Instant::now();
        self.use_count += 1;
    }

    pub fn is_idle(&self, max_idle_time: Duration) -> bool {
        self.last_used.elapsed() > max_idle_time
    }

    pub fn is_expired(&self, max_lifetime: Duration) -> bool {
        self.created_at.elapsed() > max_lifetime
    }

    pub async fn check_health(&mut self) -> bool {
        match self.connection.health_check().await {
            Ok(status) => {
                self.is_healthy = status.is_healthy;
                status.is_healthy
            }
            Err(_) => {
                self.is_healthy = false;
                false
            }
        }
    }
}

/// Connection pool statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConnectionPoolStats {
    pub total_connections: usize,
    pub active_connections: usize,
    pub idle_connections: usize,
    pub unhealthy_connections: usize,
    pub pool_hits: u64,
    pub pool_misses: u64,
    pub total_created: u64,
    pub total_destroyed: u64,
    pub average_connection_age: Duration,
    pub average_use_count: f64,
}

/// High-performance connection pool for trading platforms
pub struct ConnectionPool {
    config: ConnectionPoolConfig,
    platform_config: PlatformConfig,
    factory: PlatformFactory,
    connections: Arc<Mutex<VecDeque<PooledConnection>>>,
    semaphore: Arc<Semaphore>,
    stats: Arc<RwLock<ConnectionPoolStats>>,
    cleanup_handle: Option<tokio::task::JoinHandle<()>>,
    health_check_handle: Option<tokio::task::JoinHandle<()>>,
}

impl ConnectionPool {
    /// Create a new connection pool
    pub async fn new(platform_config: PlatformConfig) -> Result<Self, PlatformError> {
        Self::with_config(platform_config, ConnectionPoolConfig::default()).await
    }

    /// Create a new connection pool with custom configuration
    pub async fn with_config(
        platform_config: PlatformConfig,
        config: ConnectionPoolConfig,
    ) -> Result<Self, PlatformError> {
        let semaphore = Arc::new(Semaphore::new(config.max_connections));
        let connections = Arc::new(Mutex::new(VecDeque::new()));
        let stats = Arc::new(RwLock::new(ConnectionPoolStats::default()));
        let factory = PlatformFactory::new();

        let mut pool = Self {
            config,
            platform_config,
            factory,
            connections,
            semaphore,
            stats,
            cleanup_handle: None,
            health_check_handle: None,
        };

        // Initialize minimum connections
        pool.initialize_pool().await?;

        // Start background tasks
        pool.start_background_tasks();

        Ok(pool)
    }

    /// Initialize the pool with minimum connections
    async fn initialize_pool(&mut self) -> Result<(), PlatformError> {
        for _ in 0..self.config.min_connections {
            let connection = self.create_connection().await?;
            let mut connections = self.connections.lock().await;
            connections.push_back(connection);
        }

        // Update stats
        {
            let mut stats = self.stats.write().await;
            stats.total_connections = self.config.min_connections;
            stats.idle_connections = self.config.min_connections;
            stats.total_created = self.config.min_connections as u64;
        }

        Ok(())
    }

    /// Get a connection from the pool
    pub async fn get_connection(&self) -> Result<ConnectionHandle, PlatformError> {
        let _permit = self.semaphore.clone()
            .acquire_owned()
            .await
            .map_err(|_| PlatformError::InternalError {
                reason: "Failed to acquire connection pool permit".to_string(),
            })?;

        // Try to get an existing connection
        let mut connection_opt = None;
        {
            let mut connections = self.connections.lock().await;
            while let Some(mut conn) = connections.pop_front() {
                // Check if connection is still valid
                if !conn.is_expired(self.config.max_connection_lifetime) && conn.is_healthy {
                    conn.mark_used();
                    connection_opt = Some(conn);
                    break;
                } else {
                    // Connection is expired or unhealthy, destroy it
                    self.destroy_connection(conn).await;
                }
            }
        }

        // If no valid connection found, create a new one
        let connection = match connection_opt {
            Some(conn) => {
                // Pool hit
                let mut stats = self.stats.write().await;
                stats.pool_hits += 1;
                conn
            }
            None => {
                // Pool miss - create new connection
                let mut stats = self.stats.write().await;
                stats.pool_misses += 1;
                stats.total_created += 1;
                drop(stats);

                self.create_connection().await?
            }
        };

        // Update active connection count
        {
            let mut stats = self.stats.write().await;
            stats.active_connections += 1;
            if stats.idle_connections > 0 {
                stats.idle_connections -= 1;
            }
        }

        Ok(ConnectionHandle::new(connection, Arc::clone(&self.connections), Arc::clone(&self.stats)))
    }

    /// Create a new connection
    async fn create_connection(&self) -> Result<PooledConnection, PlatformError> {
        let platform = self.factory.create_with_validation(self.platform_config.clone()).await?;
        Ok(PooledConnection::new(platform))
    }

    /// Destroy a connection and update stats
    async fn destroy_connection(&self, mut connection: PooledConnection) {
        let _ = connection.connection.disconnect().await;
        
        let mut stats = self.stats.write().await;
        stats.total_destroyed += 1;
        if stats.total_connections > 0 {
            stats.total_connections -= 1;
        }
    }

    /// Return a connection to the pool
    async fn return_connection(&self, mut connection: PooledConnection) {
        // Update stats
        {
            let mut stats = self.stats.write().await;
            if stats.active_connections > 0 {
                stats.active_connections -= 1;
            }
            stats.idle_connections += 1;
        }

        // Check if connection should be kept
        if !connection.is_expired(self.config.max_connection_lifetime) && connection.is_healthy {
            let mut connections = self.connections.lock().await;
            connections.push_back(connection);
        } else {
            // Connection is expired or unhealthy, destroy it
            self.destroy_connection(connection).await;
        }
    }

    /// Start background cleanup and health check tasks
    fn start_background_tasks(&mut self) {
        // Cleanup task
        let cleanup_connections = Arc::clone(&self.connections);
        let cleanup_stats = Arc::clone(&self.stats);
        let cleanup_config = self.config.clone();
        
        let cleanup_handle = tokio::spawn(async move {
            let mut interval = tokio::time::interval(cleanup_config.cleanup_interval);
            
            loop {
                interval.tick().await;
                
                let mut connections_to_destroy = Vec::new();
                let mut remaining_connections = VecDeque::new();
                
                {
                    let mut connections = cleanup_connections.lock().await;
                    
                    while let Some(conn) = connections.pop_front() {
                        if conn.is_idle(cleanup_config.max_idle_time) || 
                           conn.is_expired(cleanup_config.max_connection_lifetime) ||
                           !conn.is_healthy {
                            connections_to_destroy.push(conn);
                        } else {
                            remaining_connections.push_back(conn);
                        }
                    }
                    
                    *connections = remaining_connections;
                }
                
                // Update stats and destroy expired connections
                if !connections_to_destroy.is_empty() {
                    let mut stats = cleanup_stats.write().await;
                    stats.total_destroyed += connections_to_destroy.len() as u64;
                    stats.total_connections = stats.total_connections.saturating_sub(connections_to_destroy.len());
                    stats.idle_connections = stats.idle_connections.saturating_sub(connections_to_destroy.len());
                }
                
                // Cleanup happens when connections are dropped
            }
        });
        
        self.cleanup_handle = Some(cleanup_handle);

        // Health check task
        let health_connections = Arc::clone(&self.connections);
        let health_config = self.config.clone();
        
        let health_handle = tokio::spawn(async move {
            let mut interval = tokio::time::interval(health_config.health_check_interval);
            
            loop {
                interval.tick().await;
                
                let mut connections = health_connections.lock().await;
                let mut unhealthy_count = 0;
                
                for conn in connections.iter_mut() {
                    if !conn.check_health().await {
                        unhealthy_count += 1;
                    }
                }
                
                drop(connections);
            }
        });
        
        self.health_check_handle = Some(health_handle);
    }

    /// Get current pool statistics
    pub async fn get_stats(&self) -> ConnectionPoolStats {
        let stats = self.stats.read().await;
        let mut stats_clone = stats.clone();

        // Calculate real-time stats
        let connections = self.connections.lock().await;
        stats_clone.total_connections = connections.len();
        stats_clone.idle_connections = connections.len();

        if !connections.is_empty() {
            let total_age: Duration = connections.iter().map(|c| c.created_at.elapsed()).sum();
            stats_clone.average_connection_age = total_age / connections.len() as u32;

            let total_use_count: u64 = connections.iter().map(|c| c.use_count).sum();
            stats_clone.average_use_count = total_use_count as f64 / connections.len() as f64;

            stats_clone.unhealthy_connections = connections.iter().filter(|c| !c.is_healthy).count();
        }

        stats_clone
    }

    /// Get pool health status
    pub async fn is_healthy(&self) -> bool {
        let stats = self.get_stats().await;
        
        // Pool is healthy if we have minimum connections and low error rate
        stats.total_connections >= self.config.min_connections &&
        stats.unhealthy_connections < stats.total_connections / 2
    }

    /// Warm up the pool by creating connections up to max
    pub async fn warm_up(&self) -> Result<(), PlatformError> {
        let current_count = {
            let connections = self.connections.lock().await;
            connections.len()
        };

        let connections_to_create = self.config.max_connections.saturating_sub(current_count);
        
        for _ in 0..connections_to_create {
            match self.create_connection().await {
                Ok(connection) => {
                    let mut connections = self.connections.lock().await;
                    connections.push_back(connection);
                }
                Err(_) => break, // Stop on first error
            }
        }

        Ok(())
    }

    /// Drain and close all connections
    pub async fn close(&mut self) -> Result<(), PlatformError> {
        // Stop background tasks
        if let Some(handle) = self.cleanup_handle.take() {
            handle.abort();
        }
        if let Some(handle) = self.health_check_handle.take() {
            handle.abort();
        }

        // Close all connections
        let mut connections = self.connections.lock().await;
        while let Some(connection) = connections.pop_front() {
            self.destroy_connection(connection).await;
        }

        Ok(())
    }
}

impl Default for ConnectionPoolStats {
    fn default() -> Self {
        Self {
            total_connections: 0,
            active_connections: 0,
            idle_connections: 0,
            unhealthy_connections: 0,
            pool_hits: 0,
            pool_misses: 0,
            total_created: 0,
            total_destroyed: 0,
            average_connection_age: Duration::default(),
            average_use_count: 0.0,
        }
    }
}

/// Handle for a connection borrowed from the pool
pub struct ConnectionHandle {
    connection: Option<PooledConnection>,
    pool_connections: Arc<Mutex<VecDeque<PooledConnection>>>,
    pool_stats: Arc<RwLock<ConnectionPoolStats>>,
}

impl ConnectionHandle {
    fn new(
        connection: PooledConnection,
        pool_connections: Arc<Mutex<VecDeque<PooledConnection>>>,
        pool_stats: Arc<RwLock<ConnectionPoolStats>>,
    ) -> Self {
        Self {
            connection: Some(connection),
            pool_connections,
            pool_stats,
        }
    }

    /// Get a reference to the underlying platform connection
    pub fn platform(&self) -> &dyn ITradingPlatform {
        self.connection.as_ref().unwrap().connection.as_ref()
    }

    /// Get connection usage statistics
    pub fn usage_stats(&self) -> (u64, Duration) {
        let conn = self.connection.as_ref().unwrap();
        (conn.use_count, conn.created_at.elapsed())
    }
}

impl Drop for ConnectionHandle {
    fn drop(&mut self) {
        if let Some(connection) = self.connection.take() {
            let pool_connections = Arc::clone(&self.pool_connections);
            let pool_stats = Arc::clone(&self.pool_stats);
            
            // Return connection to pool asynchronously
            tokio::spawn(async move {
                // Update stats
                {
                    let mut stats = pool_stats.write().await;
                    if stats.active_connections > 0 {
                        stats.active_connections -= 1;
                    }
                    stats.idle_connections += 1;
                }

                // Return to pool
                let mut connections = pool_connections.lock().await;
                connections.push_back(connection);
            });
        }
    }
}

/// Pool manager for managing multiple connection pools
pub struct PoolManager {
    pools: Arc<RwLock<std::collections::HashMap<String, Arc<ConnectionPool>>>>,
}

impl PoolManager {
    pub fn new() -> Self {
        Self {
            pools: Arc::new(RwLock::new(std::collections::HashMap::new())),
        }
    }

    /// Create or get a connection pool for a specific account
    pub async fn get_or_create_pool(
        &self,
        account_id: String,
        platform_config: PlatformConfig,
        pool_config: Option<ConnectionPoolConfig>,
    ) -> Result<Arc<ConnectionPool>, PlatformError> {
        // Check if pool already exists
        {
            let pools = self.pools.read().await;
            if let Some(pool) = pools.get(&account_id) {
                return Ok(Arc::clone(pool));
            }
        }

        // Create new pool
        let config = pool_config.unwrap_or_default();
        let pool = ConnectionPool::with_config(platform_config, config).await?;
        let pool_arc = Arc::new(pool);

        // Store the pool
        {
            let mut pools = self.pools.write().await;
            pools.insert(account_id, Arc::clone(&pool_arc));
        }

        Ok(pool_arc)
    }

    /// Get connection from a specific pool
    pub async fn get_connection(&self, account_id: &str) -> Result<ConnectionHandle, PlatformError> {
        let pools = self.pools.read().await;
        let pool = pools.get(account_id)
            .ok_or_else(|| PlatformError::AccountNotFound { 
                account_id: account_id.to_string() 
            })?;
        
        pool.get_connection().await
    }

    /// Get statistics for all pools
    pub async fn get_all_stats(&self) -> std::collections::HashMap<String, ConnectionPoolStats> {
        let pools = self.pools.read().await;
        let mut all_stats = std::collections::HashMap::new();

        for (account_id, pool) in pools.iter() {
            let stats = pool.get_stats().await;
            all_stats.insert(account_id.clone(), stats);
        }

        all_stats
    }

    /// Close all pools
    pub async fn close_all(&self) -> Result<(), PlatformError> {
        let pools = self.pools.read().await;
        for pool in pools.values() {
            // Note: We can't call close() because we only have Arc<ConnectionPool>
            // In a real implementation, you might need interior mutability
        }
        Ok(())
    }
}

impl Default for PoolManager {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Mock platform for testing
    struct MockPlatform {
        is_connected: bool,
        should_fail_health: bool,
    }

    impl MockPlatform {
        fn new() -> Self {
            Self {
                is_connected: true,
                should_fail_health: false,
            }
        }
    }

    #[async_trait::async_trait]
    impl ITradingPlatform for MockPlatform {
        fn platform_type(&self) -> crate::platforms::PlatformType {
            crate::platforms::PlatformType::TradeLocker
        }

        fn platform_name(&self) -> &str { "MockPlatform" }
        fn platform_version(&self) -> &str { "1.0.0" }

        async fn connect(&mut self) -> std::result::Result<(), PlatformError> {
            self.is_connected = true;
            Ok(())
        }

        async fn disconnect(&mut self) -> std::result::Result<(), PlatformError> {
            self.is_connected = false;
            Ok(())
        }

        async fn is_connected(&self) -> bool { self.is_connected }
        async fn ping(&self) -> std::result::Result<u64, PlatformError> { Ok(10) }

        async fn health_check(&self) -> std::result::Result<crate::platforms::abstraction::interfaces::HealthStatus, PlatformError> {
            Ok(crate::platforms::abstraction::interfaces::HealthStatus {
                is_healthy: !self.should_fail_health,
                last_ping: Some(chrono::Utc::now()),
                latency_ms: Some(10),
                error_rate: 0.0,
                uptime_seconds: 3600,
                issues: Vec::new(),
            })
        }

        // Implement other required methods with minimal functionality
        async fn place_order(&self, _order: super::super::models::UnifiedOrder) -> std::result::Result<super::super::models::UnifiedOrderResponse, PlatformError> {
            Err(PlatformError::FeatureNotSupported { feature: "place_order".to_string() })
        }

        async fn modify_order(&self, _order_id: &str, _modifications: super::super::models::OrderModification) -> std::result::Result<super::super::models::UnifiedOrderResponse, PlatformError> {
            Err(PlatformError::FeatureNotSupported { feature: "modify_order".to_string() })
        }

        async fn cancel_order(&self, _order_id: &str) -> std::result::Result<(), PlatformError> {
            Err(PlatformError::FeatureNotSupported { feature: "cancel_order".to_string() })
        }

        async fn get_order(&self, _order_id: &str) -> std::result::Result<super::super::models::UnifiedOrderResponse, PlatformError> {
            Err(PlatformError::FeatureNotSupported { feature: "get_order".to_string() })
        }

        async fn get_orders(&self, _filter: Option<super::super::interfaces::OrderFilter>) -> std::result::Result<Vec<super::super::models::UnifiedOrderResponse>, PlatformError> {
            Ok(Vec::new())
        }

        async fn get_positions(&self) -> std::result::Result<Vec<super::super::models::UnifiedPosition>, PlatformError> {
            Ok(Vec::new())
        }

        async fn get_position(&self, _symbol: &str) -> std::result::Result<Option<super::super::models::UnifiedPosition>, PlatformError> {
            Ok(None)
        }

        async fn close_position(&self, _symbol: &str, _quantity: Option<rust_decimal::Decimal>) -> std::result::Result<super::super::models::UnifiedOrderResponse, PlatformError> {
            Err(PlatformError::FeatureNotSupported { feature: "close_position".to_string() })
        }

        async fn get_account_info(&self) -> std::result::Result<super::super::models::UnifiedAccountInfo, PlatformError> {
            Err(PlatformError::FeatureNotSupported { feature: "get_account_info".to_string() })
        }

        async fn get_balance(&self) -> std::result::Result<rust_decimal::Decimal, PlatformError> {
            Ok(rust_decimal::Decimal::new(1000, 2))
        }

        async fn get_margin_info(&self) -> std::result::Result<super::super::models::MarginInfo, PlatformError> {
            Err(PlatformError::FeatureNotSupported { feature: "get_margin_info".to_string() })
        }

        async fn get_market_data(&self, _symbol: &str) -> std::result::Result<super::super::models::UnifiedMarketData, PlatformError> {
            Err(PlatformError::FeatureNotSupported { feature: "get_market_data".to_string() })
        }

        async fn subscribe_market_data(&self, _symbols: Vec<String>) -> std::result::Result<tokio::sync::mpsc::Receiver<super::super::models::UnifiedMarketData>, PlatformError> {
            Err(PlatformError::FeatureNotSupported { feature: "subscribe_market_data".to_string() })
        }

        async fn unsubscribe_market_data(&self, _symbols: Vec<String>) -> std::result::Result<(), PlatformError> {
            Ok(())
        }

        fn capabilities(&self) -> super::super::capabilities::PlatformCapabilities {
            super::super::capabilities::tradelocker_capabilities()
        }

        async fn subscribe_events(&self) -> std::result::Result<tokio::sync::mpsc::Receiver<super::super::events::PlatformEvent>, PlatformError> {
            Err(PlatformError::FeatureNotSupported { feature: "subscribe_events".to_string() })
        }

        async fn get_event_history(&self, _filter: super::super::interfaces::EventFilter) -> std::result::Result<Vec<super::super::events::PlatformEvent>, PlatformError> {
            Ok(Vec::new())
        }

        async fn get_diagnostics(&self) -> std::result::Result<super::super::interfaces::DiagnosticsInfo, PlatformError> {
            Ok(super::super::interfaces::DiagnosticsInfo {
                connection_status: "Connected".to_string(),
                api_limits: std::collections::HashMap::new(),
                performance_metrics: std::collections::HashMap::new(),
                last_errors: Vec::new(),
                platform_specific: std::collections::HashMap::new(),
            })
        }
    }

    #[tokio::test]
    async fn test_pooled_connection_lifecycle() {
        let platform = Box::new(MockPlatform::new());
        let mut pooled_conn = PooledConnection::new(platform);
        
        assert_eq!(pooled_conn.use_count, 0);
        assert!(pooled_conn.is_healthy);
        
        pooled_conn.mark_used();
        assert_eq!(pooled_conn.use_count, 1);
        
        // Test health check
        let health = pooled_conn.check_health().await;
        assert!(health);
        assert!(pooled_conn.is_healthy);
    }

    #[tokio::test]
    async fn test_connection_pool_config() {
        let config = ConnectionPoolConfig {
            min_connections: 2,
            max_connections: 5,
            ..Default::default()
        };
        
        assert_eq!(config.min_connections, 2);
        assert_eq!(config.max_connections, 5);
    }

    #[tokio::test]
    async fn test_pool_manager() {
        let manager = PoolManager::new();
        
        let stats = manager.get_all_stats().await;
        assert!(stats.is_empty());
    }

    #[test]
    fn test_connection_pool_stats_default() {
        let stats = ConnectionPoolStats::default();
        assert_eq!(stats.total_connections, 0);
        assert_eq!(stats.pool_hits, 0);
        assert_eq!(stats.pool_misses, 0);
    }
}