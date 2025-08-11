use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};

/// Platform capability detection and management
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlatformCapabilities {
    pub platform_name: String,
    pub platform_version: String,
    pub api_version: String,
    pub features: HashSet<PlatformFeature>,
    pub order_types: HashSet<crate::platforms::abstraction::models::UnifiedOrderType>,
    pub time_in_force_options: HashSet<crate::platforms::abstraction::models::UnifiedTimeInForce>,
    pub supported_instruments: HashSet<crate::platforms::abstraction::models::InstrumentType>,
    pub max_positions: Option<u32>,
    pub max_orders_per_second: Option<u32>,
    pub max_order_size: Option<rust_decimal::Decimal>,
    pub min_order_size: Option<rust_decimal::Decimal>,
    pub supports_partial_fills: bool,
    pub supports_market_data_subscription: bool,
    pub supports_historical_data: bool,
    pub max_historical_range_days: Option<u32>,
    pub rate_limits: HashMap<String, RateLimit>,
    pub latency_sla: Option<LatencySLA>,
    pub additional_capabilities: HashMap<String, serde_json::Value>,
}

impl PlatformCapabilities {
    pub fn new(platform_name: String) -> Self {
        Self {
            platform_name,
            platform_version: "1.0.0".to_string(),
            api_version: "1.0".to_string(),
            features: HashSet::new(),
            order_types: HashSet::new(),
            time_in_force_options: HashSet::new(),
            supported_instruments: HashSet::new(),
            max_positions: None,
            max_orders_per_second: None,
            max_order_size: None,
            min_order_size: None,
            supports_partial_fills: false,
            supports_market_data_subscription: false,
            supports_historical_data: false,
            max_historical_range_days: None,
            rate_limits: HashMap::new(),
            latency_sla: None,
            additional_capabilities: HashMap::new(),
        }
    }

    pub fn supports_feature(&self, feature: PlatformFeature) -> bool {
        self.features.contains(&feature)
    }

    pub fn supports_order_type(&self, order_type: &crate::platforms::abstraction::models::UnifiedOrderType) -> bool {
        self.order_types.contains(order_type)
    }

    pub fn supports_time_in_force(&self, tif: &crate::platforms::abstraction::models::UnifiedTimeInForce) -> bool {
        self.time_in_force_options.contains(tif)
    }

    pub fn supports_instrument_type(&self, instrument_type: &crate::platforms::abstraction::models::InstrumentType) -> bool {
        self.supported_instruments.contains(instrument_type)
    }

    pub fn get_rate_limit(&self, operation: &str) -> Option<&RateLimit> {
        self.rate_limits.get(operation)
    }

    pub fn validate_order_size(&self, size: rust_decimal::Decimal) -> Result<(), super::errors::ValidationError> {
        if let Some(min) = self.min_order_size {
            if size < min {
                return Err(super::errors::ValidationError::OrderTooSmall { min_size: min });
            }
        }
        
        if let Some(max) = self.max_order_size {
            if size > max {
                return Err(super::errors::ValidationError::OrderTooLarge { max_size: max });
            }
        }

        Ok(())
    }

    pub fn estimate_latency(&self, operation: PlatformOperation) -> Option<u64> {
        self.latency_sla.as_ref().map(|sla| sla.get_expected_latency(operation))
    }
}

/// Platform features enumeration
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum PlatformFeature {
    // Order Management
    MarketOrders,
    LimitOrders,
    StopOrders,
    StopLimitOrders,
    TrailingStopOrders,
    OcoOrders,
    BracketOrders,
    ConditionalOrders,
    OrderModification,
    OrderCancellation,
    PartialFills,
    
    // Position Management
    NetPositions,
    HedgedPositions,
    PositionNetting,
    PositionHedging,
    StopLossManagement,
    TakeProfitManagement,
    TrailingStops,
    
    // Market Data
    RealtimeQuotes,
    Level2Data,
    HistoricalData,
    TickData,
    CandlestickData,
    VolumeData,
    MarketDepth,
    TimeAndSales,
    MarketDataSubscription,
    MarketDataStreaming,
    
    // Account Features
    MultiAccount,
    SubAccounts,
    AccountSegregation,
    MarginTrading,
    LeverageControl,
    RiskManagement,
    
    // Connectivity
    RestApi,
    WebSocketApi,
    FixProtocol,
    FtpReporting,
    
    // Advanced Features
    AlgorithmicTrading,
    StrategyBacktesting,
    PaperTrading,
    SandboxEnvironment,
    WebHooks,
    CustomIndicators,
    
    // Compliance & Reporting
    AuditTrail,
    ComplianceReporting,
    RegulatoryReporting,
    TradingPermissions,
    
    // Platform Specific
    TradeLockerMultiAccount,
    DXTradeFixProtocol,
    MetaTraderExpertAdvisors,
}

/// Rate limiting configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RateLimit {
    pub requests_per_second: u32,
    pub requests_per_minute: u32,
    pub requests_per_hour: u32,
    pub burst_limit: Option<u32>,
    pub reset_period_seconds: u32,
}

impl RateLimit {
    pub fn new(rps: u32, rpm: u32, rph: u32) -> Self {
        Self {
            requests_per_second: rps,
            requests_per_minute: rpm,
            requests_per_hour: rph,
            burst_limit: None,
            reset_period_seconds: 60,
        }
    }

    pub fn is_rate_limited(&self, current_requests: u32, time_window_seconds: u32) -> bool {
        let max_requests = match time_window_seconds {
            1 => self.requests_per_second,
            60 => self.requests_per_minute,
            3600 => self.requests_per_hour,
            _ => self.requests_per_second * time_window_seconds,
        };
        
        current_requests >= max_requests
    }
}

/// SLA for platform latency expectations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LatencySLA {
    pub order_placement_ms: u64,
    pub order_modification_ms: u64,
    pub order_cancellation_ms: u64,
    pub market_data_ms: u64,
    pub account_info_ms: u64,
    pub position_query_ms: u64,
    pub historical_data_ms: u64,
}

impl LatencySLA {
    pub fn get_expected_latency(&self, operation: PlatformOperation) -> u64 {
        match operation {
            PlatformOperation::PlaceOrder => self.order_placement_ms,
            PlatformOperation::ModifyOrder => self.order_modification_ms,
            PlatformOperation::CancelOrder => self.order_cancellation_ms,
            PlatformOperation::GetMarketData => self.market_data_ms,
            PlatformOperation::GetAccountInfo => self.account_info_ms,
            PlatformOperation::GetPositions => self.position_query_ms,
            PlatformOperation::GetHistoricalData => self.historical_data_ms,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PlatformOperation {
    PlaceOrder,
    ModifyOrder,
    CancelOrder,
    GetMarketData,
    GetAccountInfo,
    GetPositions,
    GetHistoricalData,
}

/// TradeLocker specific capabilities
pub fn tradelocker_capabilities() -> PlatformCapabilities {
    let mut caps = PlatformCapabilities::new("TradeLocker".to_string());
    
    // Features
    caps.features.insert(PlatformFeature::MarketOrders);
    caps.features.insert(PlatformFeature::LimitOrders);
    caps.features.insert(PlatformFeature::StopOrders);
    caps.features.insert(PlatformFeature::StopLimitOrders);
    caps.features.insert(PlatformFeature::TrailingStopOrders);
    caps.features.insert(PlatformFeature::OcoOrders);
    caps.features.insert(PlatformFeature::OrderModification);
    caps.features.insert(PlatformFeature::OrderCancellation);
    caps.features.insert(PlatformFeature::PartialFills);
    caps.features.insert(PlatformFeature::NetPositions);
    caps.features.insert(PlatformFeature::RealtimeQuotes);
    caps.features.insert(PlatformFeature::HistoricalData);
    caps.features.insert(PlatformFeature::MarketDataStreaming);
    caps.features.insert(PlatformFeature::WebSocketApi);
    caps.features.insert(PlatformFeature::MultiAccount);
    caps.features.insert(PlatformFeature::TradeLockerMultiAccount);

    // Order types
    caps.order_types.insert(crate::platforms::abstraction::models::UnifiedOrderType::Market);
    caps.order_types.insert(crate::platforms::abstraction::models::UnifiedOrderType::Limit);
    caps.order_types.insert(crate::platforms::abstraction::models::UnifiedOrderType::Stop);
    caps.order_types.insert(crate::platforms::abstraction::models::UnifiedOrderType::StopLimit);
    caps.order_types.insert(crate::platforms::abstraction::models::UnifiedOrderType::TrailingStop);
    caps.order_types.insert(crate::platforms::abstraction::models::UnifiedOrderType::Oco);

    // Time in force
    caps.time_in_force_options.insert(crate::platforms::abstraction::models::UnifiedTimeInForce::Gtc);
    caps.time_in_force_options.insert(crate::platforms::abstraction::models::UnifiedTimeInForce::Ioc);
    caps.time_in_force_options.insert(crate::platforms::abstraction::models::UnifiedTimeInForce::Fok);
    caps.time_in_force_options.insert(crate::platforms::abstraction::models::UnifiedTimeInForce::Day);

    // Instruments
    caps.supported_instruments.insert(crate::platforms::abstraction::models::InstrumentType::Forex);
    caps.supported_instruments.insert(crate::platforms::abstraction::models::InstrumentType::Stock);
    caps.supported_instruments.insert(crate::platforms::abstraction::models::InstrumentType::Index);
    caps.supported_instruments.insert(crate::platforms::abstraction::models::InstrumentType::Commodity);

    // Limits
    caps.max_orders_per_second = Some(10);
    caps.supports_partial_fills = true;
    caps.supports_market_data_subscription = true;
    caps.supports_historical_data = true;
    caps.max_historical_range_days = Some(365);

    // Rate limits
    caps.rate_limits.insert("orders".to_string(), RateLimit::new(10, 600, 36000));
    caps.rate_limits.insert("market_data".to_string(), RateLimit::new(50, 3000, 180000));

    // SLA
    caps.latency_sla = Some(LatencySLA {
        order_placement_ms: 50,
        order_modification_ms: 30,
        order_cancellation_ms: 20,
        market_data_ms: 10,
        account_info_ms: 100,
        position_query_ms: 50,
        historical_data_ms: 500,
    });

    caps
}

/// DXTrade specific capabilities  
pub fn dxtrade_capabilities() -> PlatformCapabilities {
    let mut caps = PlatformCapabilities::new("DXTrade".to_string());
    
    // Features
    caps.features.insert(PlatformFeature::MarketOrders);
    caps.features.insert(PlatformFeature::LimitOrders);
    caps.features.insert(PlatformFeature::StopOrders);
    caps.features.insert(PlatformFeature::StopLimitOrders);
    caps.features.insert(PlatformFeature::OrderModification);
    caps.features.insert(PlatformFeature::OrderCancellation);
    caps.features.insert(PlatformFeature::PartialFills);
    caps.features.insert(PlatformFeature::NetPositions);
    caps.features.insert(PlatformFeature::RealtimeQuotes);
    caps.features.insert(PlatformFeature::HistoricalData);
    caps.features.insert(PlatformFeature::FixProtocol);
    caps.features.insert(PlatformFeature::DXTradeFixProtocol);

    // Order types
    caps.order_types.insert(crate::platforms::abstraction::models::UnifiedOrderType::Market);
    caps.order_types.insert(crate::platforms::abstraction::models::UnifiedOrderType::Limit);
    caps.order_types.insert(crate::platforms::abstraction::models::UnifiedOrderType::Stop);
    caps.order_types.insert(crate::platforms::abstraction::models::UnifiedOrderType::StopLimit);
    caps.order_types.insert(crate::platforms::abstraction::models::UnifiedOrderType::MarketIfTouched);

    // Time in force
    caps.time_in_force_options.insert(crate::platforms::abstraction::models::UnifiedTimeInForce::Day);
    caps.time_in_force_options.insert(crate::platforms::abstraction::models::UnifiedTimeInForce::Gtc);
    caps.time_in_force_options.insert(crate::platforms::abstraction::models::UnifiedTimeInForce::Ioc);
    caps.time_in_force_options.insert(crate::platforms::abstraction::models::UnifiedTimeInForce::Fok);
    caps.time_in_force_options.insert(crate::platforms::abstraction::models::UnifiedTimeInForce::Gtd);

    // Instruments
    caps.supported_instruments.insert(crate::platforms::abstraction::models::InstrumentType::Forex);
    caps.supported_instruments.insert(crate::platforms::abstraction::models::InstrumentType::Stock);
    caps.supported_instruments.insert(crate::platforms::abstraction::models::InstrumentType::Index);
    caps.supported_instruments.insert(crate::platforms::abstraction::models::InstrumentType::Commodity);
    caps.supported_instruments.insert(crate::platforms::abstraction::models::InstrumentType::Future);

    // Limits
    caps.max_orders_per_second = Some(20);
    caps.supports_partial_fills = true;
    caps.supports_market_data_subscription = false; // Uses FIX for streaming
    caps.supports_historical_data = true;
    caps.max_historical_range_days = Some(1000);

    // Rate limits
    caps.rate_limits.insert("orders".to_string(), RateLimit::new(20, 1200, 72000));
    caps.rate_limits.insert("market_data".to_string(), RateLimit::new(100, 6000, 360000));

    // SLA
    caps.latency_sla = Some(LatencySLA {
        order_placement_ms: 30,
        order_modification_ms: 25,
        order_cancellation_ms: 15,
        market_data_ms: 5,
        account_info_ms: 80,
        position_query_ms: 40,
        historical_data_ms: 300,
    });

    caps
}

/// Capability negotiation and runtime detection
pub struct CapabilityDetector;

impl CapabilityDetector {
    pub async fn detect_capabilities(platform_type: crate::platforms::PlatformType) -> Result<PlatformCapabilities, super::errors::PlatformError> {
        match platform_type {
            crate::platforms::PlatformType::TradeLocker => Ok(tradelocker_capabilities()),
            crate::platforms::PlatformType::DXTrade => Ok(dxtrade_capabilities()),
            _ => Err(super::errors::PlatformError::PlatformNotSupported { 
                platform: format!("{:?}", platform_type) 
            }),
        }
    }

    pub async fn runtime_capability_check(platform: &dyn crate::platforms::abstraction::interfaces::ITradingPlatform) -> PlatformCapabilities {
        let mut caps = platform.capabilities();
        
        // Perform runtime checks to update capabilities based on actual platform state
        // This could include API version detection, feature availability tests, etc.
        
        caps
    }
}