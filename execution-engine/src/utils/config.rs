// Configuration utilities
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionConfig {
    pub tradelocker: super::super::platforms::tradelocker::TradeLockerConfig,
    pub vault_endpoint: String,
    pub max_concurrent_orders: usize,
}

impl Default for ExecutionConfig {
    fn default() -> Self {
        Self {
            tradelocker: Default::default(),
            vault_endpoint: "http://localhost:8200".to_string(),
            max_concurrent_orders: 100,
        }
    }
}