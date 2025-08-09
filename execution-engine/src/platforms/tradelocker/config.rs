use serde::{Deserialize, Serialize};
use std::time::Duration;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradeLockerConfig {
    pub max_connections_per_account: usize,
    pub connection_timeout_ms: u64,
    pub request_timeout_ms: u64,
    pub max_retries: u32,
    pub retry_delay_ms: u64,
    pub rate_limit_per_second: u32,
    pub websocket_ping_interval_secs: u64,
    pub websocket_reconnect_delay_ms: u64,
    pub order_execution_timeout_ms: u64,
    pub enable_request_logging: bool,
    pub enable_response_caching: bool,
    pub cache_ttl_seconds: u64,
    pub max_concurrent_orders: usize,
    pub pre_validate_orders: bool,
    pub monitor_rate_limits: bool,
}

impl Default for TradeLockerConfig {
    fn default() -> Self {
        Self {
            max_connections_per_account: 5,
            connection_timeout_ms: 5000,
            request_timeout_ms: 3000,
            max_retries: 3,
            retry_delay_ms: 1000,
            rate_limit_per_second: 100,
            websocket_ping_interval_secs: 30,
            websocket_reconnect_delay_ms: 5000,
            order_execution_timeout_ms: 150,  // Target <150ms execution
            enable_request_logging: true,
            enable_response_caching: true,
            cache_ttl_seconds: 5,
            max_concurrent_orders: 10,
            pre_validate_orders: true,
            monitor_rate_limits: true,
        }
    }
}

impl TradeLockerConfig {
    pub fn connection_timeout(&self) -> Duration {
        Duration::from_millis(self.connection_timeout_ms)
    }

    pub fn request_timeout(&self) -> Duration {
        Duration::from_millis(self.request_timeout_ms)
    }

    pub fn retry_delay(&self) -> Duration {
        Duration::from_millis(self.retry_delay_ms)
    }

    pub fn order_timeout(&self) -> Duration {
        Duration::from_millis(self.order_execution_timeout_ms)
    }

    pub fn ws_ping_interval(&self) -> Duration {
        Duration::from_secs(self.websocket_ping_interval_secs)
    }

    pub fn ws_reconnect_delay(&self) -> Duration {
        Duration::from_millis(self.websocket_reconnect_delay_ms)
    }
}