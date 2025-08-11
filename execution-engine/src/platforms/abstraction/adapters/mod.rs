pub mod tradelocker;
pub mod dxtrade;

pub use tradelocker::TradeLockerAdapter;
pub use dxtrade::DXTradeAdapter;

use async_trait::async_trait;
use std::time::Duration;
use tokio::time::sleep;

use super::errors::PlatformError;
use super::factory::RetryConfig;

/// Retry logic utility for platform operations
pub struct RetryHandler {
    config: RetryConfig,
}

impl RetryHandler {
    pub fn new(config: RetryConfig) -> Self {
        Self { config }
    }

    pub async fn execute_with_retry<T, F, Fut>(&self, mut operation: F) -> Result<T, PlatformError>
    where
        F: FnMut() -> Fut,
        Fut: std::future::Future<Output = Result<T, PlatformError>>,
    {
        let mut attempt = 0;
        let mut delay = self.config.initial_delay_ms;

        loop {
            match operation().await {
                Ok(result) => return Ok(result),
                Err(error) => {
                    attempt += 1;

                    // Check if error is recoverable and we haven't exceeded max retries
                    if !error.is_recoverable() || attempt > self.config.max_retries {
                        return Err(error);
                    }

                    // Calculate delay with exponential backoff
                    let actual_delay = if self.config.jitter {
                        self.add_jitter(delay)
                    } else {
                        delay
                    };

                    // Sleep before retry
                    sleep(Duration::from_millis(actual_delay)).await;

                    // Update delay for next attempt
                    delay = (delay as f64 * self.config.backoff_multiplier) as u64;
                    if delay > self.config.max_delay_ms {
                        delay = self.config.max_delay_ms;
                    }
                }
            }
        }
    }

    fn add_jitter(&self, delay_ms: u64) -> u64 {
        use rand::Rng;
        let jitter_range = (delay_ms as f64 * 0.1) as u64; // 10% jitter
        let mut rng = rand::thread_rng();
        delay_ms + rng.gen_range(0..=jitter_range)
    }
}

/// Common adapter functionality
#[async_trait]
pub trait PlatformAdapter {
    async fn initialize(&mut self) -> Result<(), PlatformError>;
    async fn cleanup(&mut self) -> Result<(), PlatformError>;
    async fn reset_connection(&mut self) -> Result<(), PlatformError>;
    fn adapter_info(&self) -> AdapterInfo;
}

/// Information about a platform adapter
#[derive(Debug, Clone)]
pub struct AdapterInfo {
    pub name: String,
    pub version: String,
    pub supported_features: Vec<String>,
    pub performance_characteristics: PerformanceCharacteristics,
}

#[derive(Debug, Clone)]
pub struct PerformanceCharacteristics {
    pub typical_latency_ms: u64,
    pub max_throughput_rps: u32,
    pub memory_usage_estimate_mb: u64,
    pub cpu_usage_estimate_percent: f64,
}

/// Base adapter implementation with common functionality
pub struct BaseAdapter {
    retry_handler: RetryHandler,
    is_connected: bool,
    connection_start_time: Option<std::time::Instant>,
    operation_count: std::sync::atomic::AtomicU64,
    error_count: std::sync::atomic::AtomicU64,
}

impl BaseAdapter {
    pub fn new(retry_config: RetryConfig) -> Self {
        Self {
            retry_handler: RetryHandler::new(retry_config),
            is_connected: false,
            connection_start_time: None,
            operation_count: std::sync::atomic::AtomicU64::new(0),
            error_count: std::sync::atomic::AtomicU64::new(0),
        }
    }

    pub fn retry_handler(&self) -> &RetryHandler {
        &self.retry_handler
    }

    pub fn is_connected(&self) -> bool {
        self.is_connected
    }

    pub fn set_connected(&mut self, connected: bool) {
        self.is_connected = connected;
        if connected {
            self.connection_start_time = Some(std::time::Instant::now());
        } else {
            self.connection_start_time = None;
        }
    }

    pub fn uptime_seconds(&self) -> u64 {
        self.connection_start_time
            .map(|start| start.elapsed().as_secs())
            .unwrap_or(0)
    }

    pub fn increment_operation_count(&self) {
        self.operation_count.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
    }

    pub fn increment_error_count(&self) {
        self.error_count.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
    }

    pub fn get_operation_count(&self) -> u64 {
        self.operation_count.load(std::sync::atomic::Ordering::Relaxed)
    }

    pub fn get_error_count(&self) -> u64 {
        self.error_count.load(std::sync::atomic::Ordering::Relaxed)
    }

    pub fn get_error_rate(&self) -> f64 {
        let operations = self.get_operation_count();
        let errors = self.get_error_count();
        
        if operations == 0 {
            0.0
        } else {
            errors as f64 / operations as f64
        }
    }
}

/// Utility functions for type conversion between platform-specific and unified types
pub mod conversion_utils {
    use rust_decimal::Decimal;
    use super::super::models::*;

    /// Convert TradeLocker order side to unified order side
    pub fn convert_tl_order_side(side: crate::platforms::tradelocker::OrderSide) -> UnifiedOrderSide {
        match side {
            crate::platforms::tradelocker::OrderSide::Buy => UnifiedOrderSide::Buy,
            crate::platforms::tradelocker::OrderSide::Sell => UnifiedOrderSide::Sell,
        }
    }

    /// Convert unified order side to TradeLocker order side
    pub fn convert_to_tl_order_side(side: UnifiedOrderSide) -> crate::platforms::tradelocker::OrderSide {
        match side {
            UnifiedOrderSide::Buy => crate::platforms::tradelocker::OrderSide::Buy,
            UnifiedOrderSide::Sell => crate::platforms::tradelocker::OrderSide::Sell,
        }
    }

    /// Convert TradeLocker order type to unified order type
    pub fn convert_tl_order_type(order_type: crate::platforms::tradelocker::OrderType) -> UnifiedOrderType {
        match order_type {
            crate::platforms::tradelocker::OrderType::Market => UnifiedOrderType::Market,
            crate::platforms::tradelocker::OrderType::Limit => UnifiedOrderType::Limit,
            crate::platforms::tradelocker::OrderType::Stop => UnifiedOrderType::Stop,
            crate::platforms::tradelocker::OrderType::StopLimit => UnifiedOrderType::StopLimit,
        }
    }

    /// Convert unified order type to TradeLocker order type
    pub fn convert_to_tl_order_type(order_type: UnifiedOrderType) -> Option<crate::platforms::tradelocker::OrderType> {
        match order_type {
            UnifiedOrderType::Market => Some(crate::platforms::tradelocker::OrderType::Market),
            UnifiedOrderType::Limit => Some(crate::platforms::tradelocker::OrderType::Limit),
            UnifiedOrderType::Stop => Some(crate::platforms::tradelocker::OrderType::Stop),
            UnifiedOrderType::StopLimit => Some(crate::platforms::tradelocker::OrderType::StopLimit),
            UnifiedOrderType::TrailingStop => None, // TradeLocker handles this differently
            UnifiedOrderType::MarketIfTouched => None, // Not supported
            UnifiedOrderType::Oco => None, // Handled as separate orders
        }
    }

    /// Convert TradeLocker time in force to unified time in force
    pub fn convert_tl_time_in_force(tif: crate::platforms::tradelocker::TimeInForce) -> UnifiedTimeInForce {
        match tif {
            crate::platforms::tradelocker::TimeInForce::Gtc => UnifiedTimeInForce::Gtc,
            crate::platforms::tradelocker::TimeInForce::Ioc => UnifiedTimeInForce::Ioc,
            crate::platforms::tradelocker::TimeInForce::Fok => UnifiedTimeInForce::Fok,
            crate::platforms::tradelocker::TimeInForce::Day => UnifiedTimeInForce::Day,
        }
    }

    /// Convert unified time in force to TradeLocker time in force
    pub fn convert_to_tl_time_in_force(tif: UnifiedTimeInForce) -> Option<crate::platforms::tradelocker::TimeInForce> {
        match tif {
            UnifiedTimeInForce::Gtc => Some(crate::platforms::tradelocker::TimeInForce::Gtc),
            UnifiedTimeInForce::Ioc => Some(crate::platforms::tradelocker::TimeInForce::Ioc),
            UnifiedTimeInForce::Fok => Some(crate::platforms::tradelocker::TimeInForce::Fok),
            UnifiedTimeInForce::Day => Some(crate::platforms::tradelocker::TimeInForce::Day),
            UnifiedTimeInForce::Gtd => None, // Not directly supported
        }
    }

    /// Convert TradeLocker order status to unified order status
    pub fn convert_tl_order_status(status: crate::platforms::tradelocker::OrderStatus) -> UnifiedOrderStatus {
        match status {
            crate::platforms::tradelocker::OrderStatus::Pending => UnifiedOrderStatus::Pending,
            crate::platforms::tradelocker::OrderStatus::New => UnifiedOrderStatus::New,
            crate::platforms::tradelocker::OrderStatus::PartiallyFilled => UnifiedOrderStatus::PartiallyFilled,
            crate::platforms::tradelocker::OrderStatus::Filled => UnifiedOrderStatus::Filled,
            crate::platforms::tradelocker::OrderStatus::Canceled => UnifiedOrderStatus::Canceled,
            crate::platforms::tradelocker::OrderStatus::Rejected => UnifiedOrderStatus::Rejected,
            crate::platforms::tradelocker::OrderStatus::Expired => UnifiedOrderStatus::Expired,
        }
    }

    /// Convert TradeLocker position side to unified position side
    pub fn convert_tl_position_side(side: crate::platforms::tradelocker::PositionSide) -> UnifiedPositionSide {
        match side {
            crate::platforms::tradelocker::PositionSide::Long => UnifiedPositionSide::Long,
            crate::platforms::tradelocker::PositionSide::Short => UnifiedPositionSide::Short,
        }
    }

    // DXTrade conversion functions
    /// Convert DXTrade order side to unified order side
    pub fn convert_dx_order_side(side: crate::platforms::dxtrade::OrderSide) -> UnifiedOrderSide {
        match side {
            crate::platforms::dxtrade::OrderSide::Buy => UnifiedOrderSide::Buy,
            crate::platforms::dxtrade::OrderSide::Sell => UnifiedOrderSide::Sell,
        }
    }

    /// Convert unified order side to DXTrade order side
    pub fn convert_to_dx_order_side(side: UnifiedOrderSide) -> crate::platforms::dxtrade::OrderSide {
        match side {
            UnifiedOrderSide::Buy => crate::platforms::dxtrade::OrderSide::Buy,
            UnifiedOrderSide::Sell => crate::platforms::dxtrade::OrderSide::Sell,
        }
    }

    /// Convert DXTrade order type to unified order type
    pub fn convert_dx_order_type(order_type: crate::platforms::dxtrade::OrderType) -> UnifiedOrderType {
        match order_type {
            crate::platforms::dxtrade::OrderType::Market => UnifiedOrderType::Market,
            crate::platforms::dxtrade::OrderType::Limit => UnifiedOrderType::Limit,
            crate::platforms::dxtrade::OrderType::Stop => UnifiedOrderType::Stop,
            crate::platforms::dxtrade::OrderType::StopLimit => UnifiedOrderType::StopLimit,
            crate::platforms::dxtrade::OrderType::MarketIfTouched => UnifiedOrderType::MarketIfTouched,
        }
    }

    /// Convert unified order type to DXTrade order type
    pub fn convert_to_dx_order_type(order_type: UnifiedOrderType) -> Option<crate::platforms::dxtrade::OrderType> {
        match order_type {
            UnifiedOrderType::Market => Some(crate::platforms::dxtrade::OrderType::Market),
            UnifiedOrderType::Limit => Some(crate::platforms::dxtrade::OrderType::Limit),
            UnifiedOrderType::Stop => Some(crate::platforms::dxtrade::OrderType::Stop),
            UnifiedOrderType::StopLimit => Some(crate::platforms::dxtrade::OrderType::StopLimit),
            UnifiedOrderType::MarketIfTouched => Some(crate::platforms::dxtrade::OrderType::MarketIfTouched),
            UnifiedOrderType::TrailingStop => None, // Not directly supported
            UnifiedOrderType::Oco => None, // Not directly supported
        }
    }

    /// Convert DXTrade time in force to unified time in force
    pub fn convert_dx_time_in_force(tif: crate::platforms::dxtrade::TimeInForce) -> UnifiedTimeInForce {
        match tif {
            crate::platforms::dxtrade::TimeInForce::Day => UnifiedTimeInForce::Day,
            crate::platforms::dxtrade::TimeInForce::GoodTillCancel => UnifiedTimeInForce::Gtc,
            crate::platforms::dxtrade::TimeInForce::ImmediateOrCancel => UnifiedTimeInForce::Ioc,
            crate::platforms::dxtrade::TimeInForce::FillOrKill => UnifiedTimeInForce::Fok,
            crate::platforms::dxtrade::TimeInForce::GoodTillDate => UnifiedTimeInForce::Gtd,
        }
    }

    /// Convert unified time in force to DXTrade time in force
    pub fn convert_to_dx_time_in_force(tif: UnifiedTimeInForce) -> Option<crate::platforms::dxtrade::TimeInForce> {
        match tif {
            UnifiedTimeInForce::Day => Some(crate::platforms::dxtrade::TimeInForce::Day),
            UnifiedTimeInForce::Gtc => Some(crate::platforms::dxtrade::TimeInForce::GoodTillCancel),
            UnifiedTimeInForce::Ioc => Some(crate::platforms::dxtrade::TimeInForce::ImmediateOrCancel),
            UnifiedTimeInForce::Fok => Some(crate::platforms::dxtrade::TimeInForce::FillOrKill),
            UnifiedTimeInForce::Gtd => Some(crate::platforms::dxtrade::TimeInForce::GoodTillDate),
        }
    }

    /// Convert DXTrade order status to unified order status
    pub fn convert_dx_order_status(status: crate::platforms::dxtrade::OrderStatus) -> UnifiedOrderStatus {
        match status {
            crate::platforms::dxtrade::OrderStatus::New => UnifiedOrderStatus::New,
            crate::platforms::dxtrade::OrderStatus::PartiallyFilled => UnifiedOrderStatus::PartiallyFilled,
            crate::platforms::dxtrade::OrderStatus::Filled => UnifiedOrderStatus::Filled,
            crate::platforms::dxtrade::OrderStatus::DoneForDay => UnifiedOrderStatus::Canceled,
            crate::platforms::dxtrade::OrderStatus::Canceled => UnifiedOrderStatus::Canceled,
            crate::platforms::dxtrade::OrderStatus::Replaced => UnifiedOrderStatus::New, // Treat as new order
            crate::platforms::dxtrade::OrderStatus::PendingCancel => UnifiedOrderStatus::PendingCancel,
            crate::platforms::dxtrade::OrderStatus::Stopped => UnifiedOrderStatus::Canceled,
            crate::platforms::dxtrade::OrderStatus::Rejected => UnifiedOrderStatus::Rejected,
            crate::platforms::dxtrade::OrderStatus::Suspended => UnifiedOrderStatus::Suspended,
            crate::platforms::dxtrade::OrderStatus::PendingNew => UnifiedOrderStatus::Pending,
            crate::platforms::dxtrade::OrderStatus::Calculated => UnifiedOrderStatus::New,
            crate::platforms::dxtrade::OrderStatus::Expired => UnifiedOrderStatus::Expired,
            crate::platforms::dxtrade::OrderStatus::AcceptedForBidding => UnifiedOrderStatus::New,
            crate::platforms::dxtrade::OrderStatus::PendingReplace => UnifiedOrderStatus::PendingReplace,
        }
    }

    /// Convert DXTrade position side to unified position side
    pub fn convert_dx_position_side(side: crate::platforms::dxtrade::PositionSide) -> UnifiedPositionSide {
        match side {
            crate::platforms::dxtrade::PositionSide::Long => UnifiedPositionSide::Long,
            crate::platforms::dxtrade::PositionSide::Short => UnifiedPositionSide::Short,
        }
    }

    /// Safely convert decimal values between platforms
    pub fn safe_decimal_conversion(value: Option<Decimal>) -> Option<Decimal> {
        value.filter(|d| !d.is_zero() && d.is_sign_positive())
    }

    /// Convert platform-specific error to unified platform error
    pub fn convert_platform_error(platform_type: crate::platforms::PlatformType, error_msg: &str) -> super::super::errors::PlatformError {
        match platform_type {
            crate::platforms::PlatformType::TradeLocker => {
                super::super::errors::PlatformError::TradeLocker { error: error_msg.to_string() }
            }
            crate::platforms::PlatformType::DXTrade => {
                super::super::errors::PlatformError::DXTrade { error: error_msg.to_string() }
            }
            crate::platforms::PlatformType::MetaTrader4 | 
            crate::platforms::PlatformType::MetaTrader5 => {
                super::super::errors::PlatformError::MetaTrader { error: error_msg.to_string() }
            }
        }
    }
}