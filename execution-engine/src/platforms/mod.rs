pub mod tradelocker;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PlatformType {
    TradeLocker,
    MetaTrader4,
    MetaTrader5,
    DXTrade,
}

pub trait TradingPlatform: Send + Sync {
    fn platform_type(&self) -> PlatformType;
    // Add common trading platform interface methods here
}