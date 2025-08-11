// Temporarily disabled due to missing dependencies
// pub mod tradelocker;
pub mod dxtrade;
pub mod abstraction;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum PlatformType {
    TradeLocker,
    MetaTrader4,
    MetaTrader5,
    DXTrade,
    #[cfg(test)]
    Mock,
}

pub trait TradingPlatform: Send + Sync {
    fn platform_type(&self) -> PlatformType;
    // Add common trading platform interface methods here
}

// Re-export key abstractions for easier usage
pub use abstraction::{
    ITradingPlatform,
    UnifiedOrder,
    UnifiedAccountInfo,
    UnifiedMarketData,
    PlatformError,
    PlatformAbstractionLayer,
    PlatformCapabilities,
    // Temporarily disabled missing types
    // UnifiedOrderResponse,
    // UnifiedPosition, 
    // PlatformFactory,
    // PlatformRegistry,
    // PerformanceMonitor,
};