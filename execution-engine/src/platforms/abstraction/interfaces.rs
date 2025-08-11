use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tokio::sync::mpsc;

use crate::platforms::PlatformType;
use super::models::*;
use super::errors::*;
use super::capabilities::*;
use super::events::*;

/// Core trait that all trading platforms must implement
#[async_trait]
pub trait ITradingPlatform: Send + Sync {
    /// Platform identification
    fn platform_type(&self) -> PlatformType;
    fn platform_name(&self) -> &str;
    fn platform_version(&self) -> &str;
    
    /// Connection management
    async fn connect(&mut self) -> Result<(), PlatformError>;
    async fn disconnect(&mut self) -> Result<(), PlatformError>;
    async fn is_connected(&self) -> bool;
    async fn ping(&self) -> Result<u64, PlatformError>; // Returns latency in ms
    
    /// Order management
    async fn place_order(&self, order: UnifiedOrder) -> Result<UnifiedOrderResponse, PlatformError>;
    async fn modify_order(&self, order_id: &str, modifications: OrderModification) -> Result<UnifiedOrderResponse, PlatformError>;
    async fn cancel_order(&self, order_id: &str) -> Result<(), PlatformError>;
    async fn get_order(&self, order_id: &str) -> Result<UnifiedOrderResponse, PlatformError>;
    async fn get_orders(&self, filter: Option<OrderFilter>) -> Result<Vec<UnifiedOrderResponse>, PlatformError>;
    
    /// Position management
    async fn get_positions(&self) -> Result<Vec<UnifiedPosition>, PlatformError>;
    async fn get_position(&self, symbol: &str) -> Result<Option<UnifiedPosition>, PlatformError>;
    async fn close_position(&self, symbol: &str, quantity: Option<rust_decimal::Decimal>) -> Result<UnifiedOrderResponse, PlatformError>;
    
    /// Account management
    async fn get_account_info(&self) -> Result<UnifiedAccountInfo, PlatformError>;
    async fn get_balance(&self) -> Result<rust_decimal::Decimal, PlatformError>;
    async fn get_margin_info(&self) -> Result<MarginInfo, PlatformError>;
    
    /// Market data
    async fn get_market_data(&self, symbol: &str) -> Result<UnifiedMarketData, PlatformError>;
    async fn subscribe_market_data(&self, symbols: Vec<String>) -> Result<mpsc::Receiver<UnifiedMarketData>, PlatformError>;
    async fn unsubscribe_market_data(&self, symbols: Vec<String>) -> Result<(), PlatformError>;
    
    /// Platform capabilities
    fn capabilities(&self) -> PlatformCapabilities;
    fn supports_feature(&self, feature: PlatformFeature) -> bool {
        self.capabilities().supports_feature(feature)
    }
    
    /// Event handling
    async fn subscribe_events(&self) -> Result<mpsc::Receiver<PlatformEvent>, PlatformError>;
    async fn get_event_history(&self, filter: EventFilter) -> Result<Vec<PlatformEvent>, PlatformError>;
    
    /// Health and diagnostics
    async fn health_check(&self) -> Result<HealthStatus, PlatformError>;
    async fn get_diagnostics(&self) -> Result<DiagnosticsInfo, PlatformError>;
}

/// Order management interface
#[async_trait]
pub trait IOrderManager: Send + Sync {
    async fn validate_order(&self, order: &UnifiedOrder) -> Result<(), ValidationError>;
    async fn calculate_margin_requirement(&self, order: &UnifiedOrder) -> Result<rust_decimal::Decimal, PlatformError>;
    async fn estimate_commission(&self, order: &UnifiedOrder) -> Result<rust_decimal::Decimal, PlatformError>;
    async fn get_order_book(&self, symbol: &str, depth: Option<u32>) -> Result<OrderBook, PlatformError>;
}

/// Position management interface
#[async_trait]
pub trait IPositionManager: Send + Sync {
    async fn calculate_unrealized_pnl(&self, position: &UnifiedPosition, current_price: rust_decimal::Decimal) -> Result<rust_decimal::Decimal, PlatformError>;
    async fn get_position_history(&self, symbol: &str, from: Option<chrono::DateTime<chrono::Utc>>) -> Result<Vec<PositionSnapshot>, PlatformError>;
    async fn set_stop_loss(&self, symbol: &str, stop_loss: rust_decimal::Decimal) -> Result<(), PlatformError>;
    async fn set_take_profit(&self, symbol: &str, take_profit: rust_decimal::Decimal) -> Result<(), PlatformError>;
}

/// Account management interface
#[async_trait]
pub trait IAccountManager: Send + Sync {
    async fn get_trading_permissions(&self) -> Result<TradingPermissions, PlatformError>;
    async fn get_account_limits(&self) -> Result<AccountLimits, PlatformError>;
    async fn get_transaction_history(&self, from: Option<chrono::DateTime<chrono::Utc>>, to: Option<chrono::DateTime<chrono::Utc>>) -> Result<Vec<Transaction>, PlatformError>;
    async fn calculate_buying_power(&self) -> Result<rust_decimal::Decimal, PlatformError>;
}

/// Market data provider interface
#[async_trait]
pub trait IMarketDataProvider: Send + Sync {
    async fn get_symbols(&self) -> Result<Vec<Symbol>, PlatformError>;
    async fn get_symbol_info(&self, symbol: &str) -> Result<SymbolInfo, PlatformError>;
    async fn get_historical_data(&self, symbol: &str, from: chrono::DateTime<chrono::Utc>, to: chrono::DateTime<chrono::Utc>, timeframe: Timeframe) -> Result<Vec<Candle>, PlatformError>;
    async fn get_tick_data(&self, symbol: &str, from: chrono::DateTime<chrono::Utc>, to: chrono::DateTime<chrono::Utc>) -> Result<Vec<Tick>, PlatformError>;
}

/// Platform events interface
#[async_trait]
pub trait IPlatformEvents: Send + Sync {
    async fn emit_event(&self, event: PlatformEvent) -> Result<(), PlatformError>;
    async fn subscribe_to_event_type(&self, event_type: EventType) -> Result<mpsc::Receiver<PlatformEvent>, PlatformError>;
    async fn get_event_stats(&self) -> Result<EventStats, PlatformError>;
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderFilter {
    pub status: Option<UnifiedOrderStatus>,
    pub symbol: Option<String>,
    pub side: Option<UnifiedOrderSide>,
    pub order_type: Option<UnifiedOrderType>,
    pub from_time: Option<chrono::DateTime<chrono::Utc>>,
    pub to_time: Option<chrono::DateTime<chrono::Utc>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventFilter {
    pub event_type: Option<EventType>,
    pub from_time: Option<chrono::DateTime<chrono::Utc>>,
    pub to_time: Option<chrono::DateTime<chrono::Utc>>,
    pub limit: Option<usize>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthStatus {
    pub is_healthy: bool,
    pub last_ping: Option<chrono::DateTime<chrono::Utc>>,
    pub latency_ms: Option<u64>,
    pub error_rate: f64,
    pub uptime_seconds: u64,
    pub issues: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiagnosticsInfo {
    pub connection_status: String,
    pub api_limits: HashMap<String, String>,
    pub performance_metrics: HashMap<String, serde_json::Value>,
    pub last_errors: Vec<String>,
    pub platform_specific: HashMap<String, serde_json::Value>,
}