use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tokio::sync::mpsc;
use uuid::Uuid;

use super::models::*;

/// Unified event system for all platform events
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlatformEvent {
    pub event_id: Uuid,
    pub event_type: EventType,
    pub platform_type: crate::platforms::PlatformType,
    pub account_id: String,
    pub timestamp: chrono::DateTime<chrono::Utc>,
    pub sequence_number: u64,
    pub data: EventData,
    pub correlation_id: Option<Uuid>,
    pub metadata: HashMap<String, serde_json::Value>,
}

impl PlatformEvent {
    pub fn new(
        event_type: EventType,
        platform_type: crate::platforms::PlatformType,
        account_id: String,
        data: EventData,
    ) -> Self {
        Self {
            event_id: Uuid::new_v4(),
            event_type,
            platform_type,
            account_id,
            timestamp: chrono::Utc::now(),
            sequence_number: 0, // Will be set by event bus
            data,
            correlation_id: None,
            metadata: HashMap::new(),
        }
    }

    pub fn with_correlation_id(mut self, correlation_id: Uuid) -> Self {
        self.correlation_id = Some(correlation_id);
        self
    }

    pub fn with_metadata(mut self, key: String, value: serde_json::Value) -> Self {
        self.metadata.insert(key, value);
        self
    }
}

/// Event types enumeration
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum EventType {
    // Connection events
    ConnectionEstablished,
    ConnectionLost,
    ConnectionRestored,
    AuthenticationSuccess,
    AuthenticationFailed,

    // Order events
    OrderPlaced,
    OrderModified,
    OrderCancelled,
    OrderFilled,
    OrderPartiallyFilled,
    OrderRejected,
    OrderExpired,

    // Position events
    PositionOpened,
    PositionClosed,
    PositionModified,
    PositionMarginCall,
    PositionStopOut,

    // Market data events
    MarketDataUpdate,
    MarketDataSubscribed,
    MarketDataUnsubscribed,
    MarketDataError,

    // Account events
    AccountBalanceUpdate,
    AccountMarginUpdate,
    AccountEquityUpdate,
    AccountStatusChange,

    // Platform events
    PlatformStatusChange,
    PlatformMaintenance,
    PlatformError,

    // Trading session events
    SessionOpened,
    SessionClosed,
    TradingHalted,
    TradingResumed,

    // Risk management events
    RiskLimitBreached,
    MarginCallTriggered,
    StopOutTriggered,

    // System events
    Heartbeat,
    Diagnostic,
    PerformanceMetric,

    // Custom events
    Custom(String),
}

/// Event data union
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum EventData {
    Connection(ConnectionEventData),
    Order(OrderEventData),
    Position(PositionEventData),
    MarketData(MarketDataEventData),
    Account(AccountEventData),
    Platform(PlatformEventData),
    TradingSession(TradingSessionEventData),
    Risk(RiskEventData),
    System(SystemEventData),
    Custom(CustomEventData),
}

// Event data structures
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConnectionEventData {
    pub status: ConnectionStatus,
    pub reason: Option<String>,
    pub server_info: Option<String>,
    pub latency_ms: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ConnectionStatus {
    Connected,
    Disconnected,
    Reconnecting,
    Failed,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderEventData {
    pub order: UnifiedOrderResponse,
    pub previous_status: Option<UnifiedOrderStatus>,
    pub fill_price: Option<rust_decimal::Decimal>,
    pub fill_quantity: Option<rust_decimal::Decimal>,
    pub remaining_quantity: Option<rust_decimal::Decimal>,
    pub rejection_reason: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PositionEventData {
    pub position: UnifiedPosition,
    pub previous_state: Option<UnifiedPosition>,
    pub trigger_price: Option<rust_decimal::Decimal>,
    pub pnl_change: Option<rust_decimal::Decimal>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarketDataEventData {
    pub market_data: UnifiedMarketData,
    pub data_type: MarketDataType,
    pub subscription_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum MarketDataType {
    Quote,
    Tick,
    Candle,
    OrderBook,
    TradeReport,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AccountEventData {
    pub account_info: UnifiedAccountInfo,
    pub previous_balance: Option<rust_decimal::Decimal>,
    pub balance_change: Option<rust_decimal::Decimal>,
    pub change_reason: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlatformEventData {
    pub status: PlatformStatus,
    pub message: String,
    pub affected_services: Vec<String>,
    pub estimated_resolution: Option<chrono::DateTime<chrono::Utc>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PlatformStatus {
    Online,
    Degraded,
    Offline,
    Maintenance,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradingSessionEventData {
    pub session_type: TradingSessionType,
    pub symbol: Option<String>,
    pub reason: Option<String>,
    pub duration: Option<chrono::Duration>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TradingSessionType {
    Regular,
    Extended,
    PreMarket,
    AfterMarket,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskEventData {
    pub risk_type: RiskType,
    pub current_value: rust_decimal::Decimal,
    pub limit_value: rust_decimal::Decimal,
    pub severity: RiskSeverity,
    pub affected_positions: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RiskType {
    MaxDrawdown,
    MarginLevel,
    DailyLoss,
    PositionSize,
    Leverage,
    Exposure,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RiskSeverity {
    Warning,
    Critical,
    Emergency,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemEventData {
    pub metric_name: String,
    pub metric_value: serde_json::Value,
    pub previous_value: Option<serde_json::Value>,
    pub threshold: Option<serde_json::Value>,
    pub unit: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CustomEventData {
    pub event_name: String,
    pub payload: HashMap<String, serde_json::Value>,
}

/// Unified event bus for aggregating events from multiple platforms
pub struct UnifiedEventBus {
    publishers: Vec<mpsc::UnboundedSender<PlatformEvent>>,
    sequence_counter: std::sync::atomic::AtomicU64,
    event_store: Option<Box<dyn EventStore>>,
    filters: Vec<EventFilter>,
}

impl UnifiedEventBus {
    pub fn new() -> Self {
        Self {
            publishers: Vec::new(),
            sequence_counter: std::sync::atomic::AtomicU64::new(0),
            event_store: None,
            filters: Vec::new(),
        }
    }

    pub fn with_event_store(mut self, store: Box<dyn EventStore>) -> Self {
        self.event_store = Some(store);
        self
    }

    pub fn subscribe(&mut self) -> mpsc::UnboundedReceiver<PlatformEvent> {
        let (tx, rx) = mpsc::unbounded_channel();
        self.publishers.push(tx);
        rx
    }

    pub async fn publish(&self, mut event: PlatformEvent) {
        // Set sequence number
        event.sequence_number = self
            .sequence_counter
            .fetch_add(1, std::sync::atomic::Ordering::SeqCst);

        // Apply filters
        if !self.should_publish(&event) {
            return;
        }

        // Store event if store is configured
        if let Some(store) = &self.event_store {
            if let Err(e) = store.store_event(&event).await {
                eprintln!("Failed to store event: {}", e);
            }
        }

        // Publish to all subscribers
        for publisher in &self.publishers {
            if let Err(_) = publisher.send(event.clone()) {
                // Subscriber disconnected, could remove from list
            }
        }
    }

    pub fn add_filter(&mut self, filter: EventFilter) {
        self.filters.push(filter);
    }

    fn should_publish(&self, event: &PlatformEvent) -> bool {
        if self.filters.is_empty() {
            return true;
        }

        self.filters.iter().any(|filter| filter.matches(event))
    }
}

impl Default for UnifiedEventBus {
    fn default() -> Self {
        Self::new()
    }
}

/// Event filter for selective event processing
#[derive(Debug, Clone)]
pub struct EventFilter {
    pub event_types: Option<Vec<EventType>>,
    pub platforms: Option<Vec<crate::platforms::PlatformType>>,
    pub accounts: Option<Vec<String>>,
    pub symbols: Option<Vec<String>>,
    pub severity_filter: Option<EventSeverity>,
}

impl EventFilter {
    pub fn new() -> Self {
        Self {
            event_types: None,
            platforms: None,
            accounts: None,
            symbols: None,
            severity_filter: None,
        }
    }

    pub fn with_event_types(mut self, types: Vec<EventType>) -> Self {
        self.event_types = Some(types);
        self
    }

    pub fn with_platforms(mut self, platforms: Vec<crate::platforms::PlatformType>) -> Self {
        self.platforms = Some(platforms);
        self
    }

    pub fn with_accounts(mut self, accounts: Vec<String>) -> Self {
        self.accounts = Some(accounts);
        self
    }

    pub fn matches(&self, event: &PlatformEvent) -> bool {
        if let Some(types) = &self.event_types {
            if !types.contains(&event.event_type) {
                return false;
            }
        }

        if let Some(platforms) = &self.platforms {
            if !platforms.contains(&event.platform_type) {
                return false;
            }
        }

        if let Some(accounts) = &self.accounts {
            if !accounts.contains(&event.account_id) {
                return false;
            }
        }

        true
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum EventSeverity {
    Debug,
    Info,
    Warning,
    Error,
    Critical,
}

/// Event statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventStats {
    pub total_events: u64,
    pub events_by_type: HashMap<String, u64>,
    pub events_by_platform: HashMap<String, u64>,
    pub events_per_second: f64,
    pub error_rate: f64,
    pub last_event_timestamp: Option<chrono::DateTime<chrono::Utc>>,
}

/// Event store trait for persistence
#[async_trait::async_trait]
pub trait EventStore: Send + Sync {
    async fn store_event(&self, event: &PlatformEvent) -> Result<(), Box<dyn std::error::Error>>;
    async fn get_events(
        &self,
        filter: &EventFilter,
        limit: Option<usize>,
    ) -> Result<Vec<PlatformEvent>, Box<dyn std::error::Error>>;
    async fn get_event_stats(
        &self,
        from: chrono::DateTime<chrono::Utc>,
    ) -> Result<EventStats, Box<dyn std::error::Error>>;
}

/// Event deduplication utility
pub struct EventDeduplicator {
    recent_events: std::collections::HashMap<String, chrono::DateTime<chrono::Utc>>,
    dedup_window: chrono::Duration,
}

impl EventDeduplicator {
    pub fn new(window_seconds: i64) -> Self {
        Self {
            recent_events: std::collections::HashMap::new(),
            dedup_window: chrono::Duration::seconds(window_seconds),
        }
    }

    pub fn should_process(&mut self, event: &PlatformEvent) -> bool {
        let key = self.create_dedup_key(event);
        let now = chrono::Utc::now();

        // Clean up old entries
        self.recent_events
            .retain(|_, timestamp| now - *timestamp < self.dedup_window);

        // Check if we've seen this event recently
        if let Some(last_seen) = self.recent_events.get(&key) {
            if now - *last_seen < self.dedup_window {
                return false; // Duplicate event
            }
        }

        self.recent_events.insert(key, now);
        true
    }

    fn create_dedup_key(&self, event: &PlatformEvent) -> String {
        match &event.data {
            EventData::Order(data) => {
                format!(
                    "order:{}:{}:{:?}",
                    event.account_id, data.order.platform_order_id, data.order.status
                )
            }
            EventData::Position(data) => {
                format!(
                    "position:{}:{}:{}",
                    event.account_id, data.position.symbol, data.position.quantity
                )
            }
            EventData::MarketData(data) => {
                format!(
                    "market:{}:{}:{}",
                    event.account_id,
                    data.market_data.symbol,
                    event.timestamp.timestamp_millis() / 1000 // Second-level deduplication
                )
            }
            _ => format!(
                "{}:{}:{}",
                format!("{:?}", event.event_type),
                event.account_id,
                event.timestamp.timestamp_millis() / 5000 // 5-second window for other events
            ),
        }
    }
}
