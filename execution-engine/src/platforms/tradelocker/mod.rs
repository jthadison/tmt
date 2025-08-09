pub mod auth;
pub mod client;
pub mod websocket;
pub mod orders;
pub mod positions;
pub mod account;
pub mod rate_limiter;
pub mod error;
pub mod config;
pub mod multi_account;
pub mod recovery;

#[cfg(test)]
mod tests;

pub use auth::TradeLockerAuth;
pub use client::TradeLockerClient;
pub use websocket::TradeLockerWebSocket;
pub use error::{TradeLockerError, Result};
pub use config::TradeLockerConfig;
pub use multi_account::{MultiAccountManager, AccountSession, AggregatedMetrics};
pub use orders::OrderManager;
pub use positions::PositionManager;
pub use account::AccountManager;
pub use recovery::{ErrorRecoveryManager, RecoveryState};

use serde::{Deserialize, Serialize};
use rust_decimal::Decimal;
use chrono::{DateTime, Utc};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradeLockerCredentials {
    pub account_id: String,
    pub api_key: String,
    pub api_secret: String,
    pub environment: TradeLockerEnvironment,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TradeLockerEnvironment {
    Production,
    Sandbox,
}

impl TradeLockerEnvironment {
    pub fn base_url(&self) -> &str {
        match self {
            Self::Production => "https://api.tradelocker.com",
            Self::Sandbox => "https://sandbox-api.tradelocker.com",
        }
    }

    pub fn ws_url(&self) -> &str {
        match self {
            Self::Production => "wss://api.tradelocker.com/ws",
            Self::Sandbox => "wss://sandbox-api.tradelocker.com/ws",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderRequest {
    pub symbol: String,
    pub side: OrderSide,
    pub order_type: OrderType,
    pub quantity: Decimal,
    pub price: Option<Decimal>,
    pub stop_price: Option<Decimal>,
    pub take_profit: Option<Decimal>,
    pub stop_loss: Option<Decimal>,
    pub time_in_force: TimeInForce,
    pub client_order_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum OrderSide {
    Buy,
    Sell,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OrderType {
    Market,
    Limit,
    Stop,
    StopLimit,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum TimeInForce {
    Gtc,  // Good Till Canceled
    Ioc,  // Immediate or Cancel
    Fok,  // Fill or Kill
    Day,  // Day Order
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderResponse {
    pub order_id: String,
    pub client_order_id: Option<String>,
    pub status: OrderStatus,
    pub symbol: String,
    pub side: OrderSide,
    pub order_type: OrderType,
    pub quantity: Decimal,
    pub filled_quantity: Decimal,
    pub price: Option<Decimal>,
    pub average_price: Option<Decimal>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum OrderStatus {
    Pending,
    New,
    PartiallyFilled,
    Filled,
    Canceled,
    Rejected,
    Expired,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Position {
    pub position_id: String,
    pub symbol: String,
    pub side: PositionSide,
    pub quantity: Decimal,
    pub entry_price: Decimal,
    pub current_price: Decimal,
    pub unrealized_pnl: Decimal,
    pub realized_pnl: Decimal,
    pub margin_used: Decimal,
    pub stop_loss: Option<Decimal>,
    pub take_profit: Option<Decimal>,
    pub opened_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum PositionSide {
    Long,
    Short,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AccountInfo {
    pub account_id: String,
    pub currency: String,
    pub balance: Decimal,
    pub equity: Decimal,
    pub margin_used: Decimal,
    pub margin_available: Decimal,
    pub unrealized_pnl: Decimal,
    pub realized_pnl: Decimal,
    pub margin_level: Option<Decimal>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarketData {
    pub symbol: String,
    pub bid: Decimal,
    pub ask: Decimal,
    pub spread: Decimal,
    pub timestamp: DateTime<Utc>,
}