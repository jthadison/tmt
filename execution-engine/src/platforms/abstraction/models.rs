use serde::{Deserialize, Serialize};
use rust_decimal::Decimal;
use chrono::{DateTime, Utc};
use std::collections::HashMap;

/// Unified order model that works across all platforms
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UnifiedOrder {
    pub client_order_id: String,
    pub symbol: String,
    pub side: UnifiedOrderSide,
    pub order_type: UnifiedOrderType,
    pub quantity: Decimal,
    pub price: Option<Decimal>,
    pub stop_price: Option<Decimal>,
    pub take_profit: Option<Decimal>,
    pub stop_loss: Option<Decimal>,
    pub time_in_force: UnifiedTimeInForce,
    pub account_id: Option<String>,
    pub metadata: OrderMetadata,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum UnifiedOrderSide {
    Buy,
    Sell,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
#[serde(rename_all = "snake_case")]
pub enum UnifiedOrderType {
    Market,
    Limit,
    Stop,
    StopLimit,
    MarketIfTouched,
    TrailingStop,
    Oco, // One-Cancels-Other
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
#[serde(rename_all = "UPPERCASE")]
pub enum UnifiedTimeInForce {
    Day,
    Gtc,  // Good Till Canceled
    Ioc,  // Immediate or Cancel
    Fok,  // Fill or Kill
    Gtd,  // Good Till Date
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderMetadata {
    pub strategy_id: Option<String>,
    pub signal_id: Option<String>,
    pub risk_parameters: HashMap<String, serde_json::Value>,
    pub tags: Vec<String>,
    pub expires_at: Option<DateTime<Utc>>,
}

/// Unified order response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UnifiedOrderResponse {
    pub platform_order_id: String,
    pub client_order_id: String,
    pub status: UnifiedOrderStatus,
    pub symbol: String,
    pub side: UnifiedOrderSide,
    pub order_type: UnifiedOrderType,
    pub quantity: Decimal,
    pub filled_quantity: Decimal,
    pub remaining_quantity: Decimal,
    pub price: Option<Decimal>,
    pub average_fill_price: Option<Decimal>,
    pub commission: Option<Decimal>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub filled_at: Option<DateTime<Utc>>,
    pub platform_specific: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum UnifiedOrderStatus {
    Pending,
    New,
    PartiallyFilled,
    Filled,
    Canceled,
    Rejected,
    Expired,
    Suspended,
    PendingCancel,
    PendingReplace,
}

/// Order modification request
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderModification {
    pub quantity: Option<Decimal>,
    pub price: Option<Decimal>,
    pub stop_price: Option<Decimal>,
    pub take_profit: Option<Decimal>,
    pub stop_loss: Option<Decimal>,
    pub time_in_force: Option<UnifiedTimeInForce>,
}

/// Unified position model
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UnifiedPosition {
    pub position_id: String,
    pub symbol: String,
    pub side: UnifiedPositionSide,
    pub quantity: Decimal,
    pub entry_price: Decimal,
    pub current_price: Decimal,
    pub unrealized_pnl: Decimal,
    pub realized_pnl: Decimal,
    pub margin_used: Decimal,
    pub commission: Decimal,
    pub stop_loss: Option<Decimal>,
    pub take_profit: Option<Decimal>,
    pub opened_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub account_id: String,
    pub platform_specific: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum UnifiedPositionSide {
    Long,
    Short,
}

/// Unified account information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UnifiedAccountInfo {
    pub account_id: String,
    pub account_name: Option<String>,
    pub currency: String,
    pub balance: Decimal,
    pub equity: Decimal,
    pub margin_used: Decimal,
    pub margin_available: Decimal,
    pub buying_power: Decimal,
    pub unrealized_pnl: Decimal,
    pub realized_pnl: Decimal,
    pub margin_level: Option<Decimal>,
    pub account_type: AccountType,
    pub last_updated: DateTime<Utc>,
    pub platform_specific: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AccountType {
    Live,
    Demo,
    Simulation,
    Paper,
}

/// Margin information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarginInfo {
    pub initial_margin: Decimal,
    pub maintenance_margin: Decimal,
    pub margin_call_level: Option<Decimal>,
    pub stop_out_level: Option<Decimal>,
    pub margin_requirements: HashMap<String, Decimal>, // Symbol -> margin requirement
}

/// Unified market data
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UnifiedMarketData {
    pub symbol: String,
    pub bid: Decimal,
    pub ask: Decimal,
    pub spread: Decimal,
    pub last_price: Option<Decimal>,
    pub volume: Option<Decimal>,
    pub high: Option<Decimal>,
    pub low: Option<Decimal>,
    pub timestamp: DateTime<Utc>,
    pub session: Option<TradingSession>,
    pub platform_specific: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TradingSession {
    PreMarket,
    Regular,
    AfterMarket,
    Closed,
}

/// Trading permissions
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradingPermissions {
    pub can_trade: bool,
    pub can_short: bool,
    pub can_use_leverage: bool,
    pub max_leverage: Option<Decimal>,
    pub allowed_instruments: Vec<String>,
    pub restricted_instruments: Vec<String>,
    pub allowed_order_types: Vec<UnifiedOrderType>,
}

/// Account limits
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AccountLimits {
    pub max_position_size: Option<Decimal>,
    pub max_order_size: Option<Decimal>,
    pub max_daily_loss: Option<Decimal>,
    pub max_open_positions: Option<u32>,
    pub max_daily_trades: Option<u32>,
    pub min_order_size: Option<Decimal>,
}

/// Transaction record
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Transaction {
    pub transaction_id: String,
    pub transaction_type: TransactionType,
    pub symbol: Option<String>,
    pub amount: Decimal,
    pub currency: String,
    pub description: String,
    pub timestamp: DateTime<Utc>,
    pub related_order_id: Option<String>,
    pub commission: Option<Decimal>,
    pub platform_specific: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TransactionType {
    Trade,
    Deposit,
    Withdrawal,
    Commission,
    Swap,
    Dividend,
    Interest,
    Fee,
    Adjustment,
}

/// Symbol information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Symbol {
    pub symbol: String,
    pub description: String,
    pub instrument_type: InstrumentType,
    pub base_currency: String,
    pub quote_currency: String,
    pub min_trade_size: Decimal,
    pub max_trade_size: Option<Decimal>,
    pub tick_size: Decimal,
    pub contract_size: Option<Decimal>,
    pub trading_hours: Vec<TradingHours>,
    pub is_tradeable: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum InstrumentType {
    Forex,
    Stock,
    Index,
    Commodity,
    Crypto,
    Bond,
    Future,
    Option,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SymbolInfo {
    pub symbol: Symbol,
    pub margin_requirement: Decimal,
    pub swap_long: Option<Decimal>,
    pub swap_short: Option<Decimal>,
    pub commission: CommissionInfo,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommissionInfo {
    pub commission_type: CommissionType,
    pub rate: Decimal,
    pub minimum: Option<Decimal>,
    pub maximum: Option<Decimal>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum CommissionType {
    Fixed,
    Percentage,
    PerLot,
    Spread,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradingHours {
    pub day_of_week: u8, // 1 = Monday, 7 = Sunday
    pub open_time: chrono::NaiveTime,
    pub close_time: chrono::NaiveTime,
    pub timezone: String,
}

/// Order book data
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderBook {
    pub symbol: String,
    pub bids: Vec<PriceLevel>,
    pub asks: Vec<PriceLevel>,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PriceLevel {
    pub price: Decimal,
    pub volume: Decimal,
    pub order_count: Option<u32>,
}

/// Historical data models
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Candle {
    pub timestamp: DateTime<Utc>,
    pub open: Decimal,
    pub high: Decimal,
    pub low: Decimal,
    pub close: Decimal,
    pub volume: Option<Decimal>,
    pub tick_volume: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Tick {
    pub timestamp: DateTime<Utc>,
    pub bid: Decimal,
    pub ask: Decimal,
    pub last: Option<Decimal>,
    pub volume: Option<Decimal>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Timeframe {
    M1,   // 1 minute
    M5,   // 5 minutes
    M15,  // 15 minutes
    M30,  // 30 minutes
    H1,   // 1 hour
    H4,   // 4 hours
    D1,   // 1 day
    W1,   // 1 week
    MN1,  // 1 month
}

/// Position snapshot for history
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PositionSnapshot {
    pub timestamp: DateTime<Utc>,
    pub position: UnifiedPosition,
    pub market_price: Decimal,
    pub unrealized_pnl: Decimal,
}