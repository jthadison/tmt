pub mod interfaces;
pub mod models;
pub mod factory;
pub mod adapters;
pub mod events;
pub mod errors;
pub mod capabilities;
pub mod performance;
pub mod circuit_breaker;
pub mod connection_pool;
pub mod resilient_adapter;
pub mod integration_tests;

pub use interfaces::*;
pub use models::*;
pub use factory::*;
pub use adapters::*;
pub use events::*;
pub use errors::*;
pub use capabilities::*;
pub use performance::*;
pub use circuit_breaker::*;
pub use connection_pool::*;
pub use resilient_adapter::*;

#[cfg(test)]
pub mod basic_test;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

/// Core abstraction layer for unified platform access
pub struct PlatformAbstractionLayer {
    platforms: Arc<RwLock<HashMap<String, Box<dyn ITradingPlatform>>>>,
    factory: PlatformFactory,
    event_bus: UnifiedEventBus,
    performance_monitor: PerformanceMonitor,
}

impl PlatformAbstractionLayer {
    pub fn new() -> Self {
        Self {
            platforms: Arc::new(RwLock::new(HashMap::new())),
            factory: PlatformFactory::new(),
            event_bus: UnifiedEventBus::new(),
            performance_monitor: PerformanceMonitor::new(),
        }
    }

    pub async fn register_platform(&self, account_id: String, config: PlatformConfig) -> Result<(), PlatformError> {
        let platform = self.factory.create_platform(config).await?;
        let mut platforms = self.platforms.write().await;
        platforms.insert(account_id, platform);
        Ok(())
    }

    pub async fn get_platform(&self, account_id: &str) -> Result<Arc<dyn ITradingPlatform>, PlatformError> {
        let platforms = self.platforms.read().await;
        platforms.get(account_id)
            .ok_or_else(|| PlatformError::PlatformNotFound(account_id.to_string()))
            .map(|p| Arc::from(p.as_ref()))
    }

    pub async fn remove_platform(&self, account_id: &str) -> Result<(), PlatformError> {
        let mut platforms = self.platforms.write().await;
        platforms.remove(account_id)
            .ok_or_else(|| PlatformError::PlatformNotFound(account_id.to_string()))?;
        Ok(())
    }

    pub fn event_bus(&self) -> &UnifiedEventBus {
        &self.event_bus
    }

    pub fn performance_monitor(&self) -> &PerformanceMonitor {
        &self.performance_monitor
    }
}

impl Default for PlatformAbstractionLayer {
    fn default() -> Self {
        Self::new()
    }
}