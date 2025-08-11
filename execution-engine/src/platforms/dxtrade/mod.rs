pub mod auth;
pub mod client;
pub mod config;
pub mod error;
pub mod fix_client;
pub mod fix_messages;
pub mod fix_session;
pub mod order_manager;
pub mod position_manager;
pub mod rest_client;
pub mod session_manager;
pub mod ssl_handler;

#[cfg(test)]
mod tests;

pub use auth::DXTradeAuth;
pub use client::DXTradeClient;
pub use config::DXTradeConfig;
pub use error::{DXTradeError, Result};
pub use fix_client::FIXClient;
pub use fix_messages::{FIXMessage, MessageType};
pub use fix_session::FIXSession;
pub use order_manager::OrderManager;
pub use position_manager::PositionManager;
pub use rest_client::RestClient;
pub use session_manager::SessionManager;

use crate::platforms::{PlatformType, TradingPlatform};
use serde::{Deserialize, Serialize};
use rust_decimal::Decimal;
use chrono::{DateTime, Utc};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DXTradeCredentials {
    pub sender_comp_id: String,
    pub target_comp_id: String,
    pub ssl_cert_path: String,
    pub ssl_key_path: String,
    pub environment: DXTradeEnvironment,
    pub fix_version: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DXTradeEnvironment {
    Production,
    Test,
    Staging,
}

impl DXTradeEnvironment {
    pub fn fix_host(&self) -> &str {
        match self {
            Self::Production => "fix.dxtrade.com",
            Self::Test => "fix-test.dxtrade.com", 
            Self::Staging => "fix-staging.dxtrade.com",
        }
    }

    pub fn fix_port(&self) -> u16 {
        443
    }

    pub fn rest_base_url(&self) -> &str {
        match self {
            Self::Production => "https://api.dxtrade.com/v2",
            Self::Test => "https://api-test.dxtrade.com/v2",
            Self::Staging => "https://api-staging.dxtrade.com/v2",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DXTradeOrderRequest {
    pub symbol: String,
    pub side: OrderSide,
    pub order_type: OrderType,
    pub quantity: Decimal,
    pub price: Option<Decimal>,
    pub stop_price: Option<Decimal>,
    pub time_in_force: TimeInForce,
    pub client_order_id: String,
    pub account_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum OrderSide {
    Buy,
    Sell,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum OrderType {
    Market,
    Limit,
    Stop,
    StopLimit,
    MarketIfTouched,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TimeInForce {
    Day,
    GoodTillCancel,
    ImmediateOrCancel,
    FillOrKill,
    GoodTillDate,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DXTradeOrderResponse {
    pub order_id: String,
    pub client_order_id: String,
    pub status: OrderStatus,
    pub symbol: String,
    pub side: OrderSide,
    pub order_type: OrderType,
    pub quantity: Decimal,
    pub filled_quantity: Decimal,
    pub leaves_quantity: Decimal,
    pub price: Option<Decimal>,
    pub average_price: Option<Decimal>,
    pub transaction_time: DateTime<Utc>,
    pub fix_session_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum OrderStatus {
    New,
    PartiallyFilled,
    Filled,
    DoneForDay,
    Canceled,
    Replaced,
    PendingCancel,
    Stopped,
    Rejected,
    Suspended,
    PendingNew,
    Calculated,
    Expired,
    AcceptedForBidding,
    PendingReplace,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DXTradePosition {
    pub position_id: String,
    pub symbol: String,
    pub side: PositionSide,
    pub quantity: Decimal,
    pub entry_price: Decimal,
    pub current_price: Decimal,
    pub unrealized_pnl: Decimal,
    pub realized_pnl: Decimal,
    pub margin_used: Decimal,
    pub account_id: String,
    pub opened_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PositionSide {
    Long,
    Short,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DXTradeAccountInfo {
    pub account_id: String,
    pub currency: String,
    pub balance: Decimal,
    pub equity: Decimal,
    pub margin_used: Decimal,
    pub margin_available: Decimal,
    pub unrealized_pnl: Decimal,
    pub realized_pnl: Decimal,
    pub margin_level: Option<Decimal>,
    pub buying_power: Decimal,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DXTradeMarketData {
    pub symbol: String,
    pub bid: Decimal,
    pub ask: Decimal,
    pub spread: Decimal,
    pub timestamp: DateTime<Utc>,
    pub volume: Option<Decimal>,
    pub high: Option<Decimal>,
    pub low: Option<Decimal>,
    pub last_price: Option<Decimal>,
}

pub struct DXTradePlatform {
    client: DXTradeClient,
}

impl DXTradePlatform {
    pub fn new(client: DXTradeClient) -> Self {
        Self { client }
    }
}

impl TradingPlatform for DXTradePlatform {
    fn platform_type(&self) -> PlatformType {
        PlatformType::DXTrade
    }
}