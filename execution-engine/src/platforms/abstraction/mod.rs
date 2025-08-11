pub mod interfaces;
pub mod models;
pub mod events;
pub mod errors;
pub mod capabilities;

// Temporarily disabled problematic modules
// pub mod factory;
// pub mod adapters;
// pub mod performance;
// pub mod circuit_breaker;
// pub mod connection_pool;
// pub mod resilient_adapter;
// pub mod integration_tests;

pub use interfaces::{
    ITradingPlatform, OrderFilter, HealthStatus, DiagnosticsInfo,
    IOrderManager, IPositionManager, IAccountManager, IMarketDataProvider, IPlatformEvents
};
pub use models::*;
pub use events::{PlatformEvent, UnifiedEventBus};
pub use errors::*;
pub use capabilities::*;

// Temporarily disabled re-exports
// pub use factory::*;
// pub use adapters::*; 
// pub use performance::*;
// pub use circuit_breaker::*;
// pub use connection_pool::*;

#[cfg(test)]
pub mod basic_test;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

/// Core abstraction layer for unified platform access
pub struct PlatformAbstractionLayer {
    platforms: Arc<RwLock<HashMap<String, Box<dyn ITradingPlatform + Send + Sync>>>>,
    event_bus: UnifiedEventBus,
    // Temporarily disabled
    // factory: PlatformFactory,
    // performance_monitor: PerformanceMonitor,
}

impl PlatformAbstractionLayer {
    pub fn new() -> Self {
        Self {
            platforms: Arc::new(RwLock::new(HashMap::new())),
            event_bus: UnifiedEventBus::new(),
            // Temporarily disabled
            // factory: PlatformFactory::new(),
            // performance_monitor: PerformanceMonitor::new(),
        }
    }

    pub async fn register_platform(&self, account_id: String, platform: Box<dyn ITradingPlatform + Send + Sync>) -> Result<(), PlatformError> {
        let mut platforms = self.platforms.write().await;
        platforms.insert(account_id, platform);
        Ok(())
    }

    pub async fn get_platform(&self, account_id: &str) -> Result<&Box<dyn ITradingPlatform + Send + Sync>, PlatformError> {
        Err(PlatformError::PlatformNotFound { platform_id: account_id.to_string() })
    }

    pub async fn remove_platform(&self, account_id: &str) -> Result<(), PlatformError> {
        let mut platforms = self.platforms.write().await;
        platforms.remove(account_id)
            .ok_or_else(|| PlatformError::PlatformNotFound { platform_id: account_id.to_string() })?;
        Ok(())
    }

    pub fn event_bus(&self) -> &UnifiedEventBus {
        &self.event_bus
    }
}

impl Default for PlatformAbstractionLayer {
    fn default() -> Self {
        Self::new()
    }
}