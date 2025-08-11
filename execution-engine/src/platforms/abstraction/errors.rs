use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

/// Unified platform error types
#[derive(Error, Debug, Clone, Serialize, Deserialize)]
pub enum PlatformError {
    /// Connection related errors
    #[error("Connection failed: {reason}")]
    ConnectionFailed { reason: String },
    
    #[error("Connection timeout after {timeout_ms}ms")]
    ConnectionTimeout { timeout_ms: u64 },
    
    #[error("Platform disconnected: {reason}")]
    Disconnected { reason: String },
    
    #[error("Authentication failed: {reason}")]
    AuthenticationFailed { reason: String },
    
    /// Order related errors
    #[error("Order validation failed: {violations:?}")]
    OrderValidationFailed { violations: Vec<ValidationError> },
    
    #[error("Order rejected by platform: {reason}")]
    OrderRejected { reason: String, platform_code: Option<String> },
    
    #[error("Order not found: {order_id}")]
    OrderNotFound { order_id: String },
    
    #[error("Order modification failed: {reason}")]
    OrderModificationFailed { reason: String },
    
    /// Position related errors
    #[error("Position not found: {symbol}")]
    PositionNotFound { symbol: String },
    
    #[error("Insufficient margin: required {required}, available {available}")]
    InsufficientMargin { required: rust_decimal::Decimal, available: rust_decimal::Decimal },
    
    #[error("Position close failed: {reason}")]
    PositionCloseFailed { reason: String },
    
    /// Market data errors
    #[error("Symbol not found: {symbol}")]
    SymbolNotFound { symbol: String },
    
    #[error("Market data unavailable: {reason}")]
    MarketDataUnavailable { reason: String },
    
    #[error("Subscription failed: {reason}")]
    SubscriptionFailed { reason: String },
    
    /// Account related errors
    #[error("Account not found: {account_id}")]
    AccountNotFound { account_id: String },
    
    #[error("Insufficient funds: required {required}, available {available}")]
    InsufficientFunds { required: rust_decimal::Decimal, available: rust_decimal::Decimal },
    
    #[error("Trading not allowed: {reason}")]
    TradingNotAllowed { reason: String },
    
    /// Platform specific errors
    #[error("Platform not supported: {platform}")]
    PlatformNotSupported { platform: String },
    
    #[error("Platform not found: {platform_id}")]
    PlatformNotFound { platform_id: String },
    
    #[error("Feature not supported: {feature}")]
    FeatureNotSupported { feature: String },
    
    /// Rate limiting errors
    #[error("Rate limit exceeded: retry after {retry_after_ms}ms")]
    RateLimitExceeded { retry_after_ms: u64 },
    
    #[error("API limit reached: {limit_type}")]
    ApiLimitReached { limit_type: String },
    
    /// Network and communication errors
    #[error("Network error: {reason}")]
    NetworkError { reason: String },
    
    #[error("Request timeout after {timeout_ms}ms")]
    RequestTimeout { timeout_ms: u64 },
    
    #[error("Invalid response: {reason}")]
    InvalidResponse { reason: String },
    
    /// Configuration and setup errors
    #[error("Configuration error: {reason}")]
    ConfigurationError { reason: String },
    
    #[error("Invalid credentials: {reason}")]
    InvalidCredentials { reason: String },
    
    #[error("Platform initialization failed: {reason}")]
    InitializationFailed { reason: String },
    
    /// Generic errors
    #[error("Internal error: {reason}")]
    InternalError { reason: String },
    
    #[error("Unknown error: {reason}")]
    Unknown { reason: String },
    
    /// Wrapped platform-specific errors
    #[error("TradeLocker error: {error}")]
    TradeLocker { error: String },
    
    #[error("DXTrade error: {error}")]
    DXTrade { error: String },
    
    #[error("MetaTrader error: {error}")]
    MetaTrader { error: String },
}

impl PlatformError {
    /// Check if error is recoverable (can be retried)
    pub fn is_recoverable(&self) -> bool {
        matches!(self, 
            PlatformError::ConnectionTimeout { .. } |
            PlatformError::NetworkError { .. } |
            PlatformError::RequestTimeout { .. } |
            PlatformError::RateLimitExceeded { .. } |
            PlatformError::MarketDataUnavailable { .. }
        )
    }

    /// Get error severity level
    pub fn severity(&self) -> ErrorSeverity {
        match self {
            PlatformError::ConnectionFailed { .. } => ErrorSeverity::Critical,
            PlatformError::AuthenticationFailed { .. } => ErrorSeverity::Critical,
            PlatformError::Disconnected { .. } => ErrorSeverity::High,
            PlatformError::OrderValidationFailed { .. } => ErrorSeverity::Medium,
            PlatformError::InsufficientMargin { .. } => ErrorSeverity::High,
            PlatformError::InsufficientFunds { .. } => ErrorSeverity::High,
            PlatformError::RateLimitExceeded { .. } => ErrorSeverity::Medium,
            PlatformError::NetworkError { .. } => ErrorSeverity::Medium,
            PlatformError::RequestTimeout { .. } => ErrorSeverity::Low,
            _ => ErrorSeverity::Medium,
        }
    }

    /// Get suggested retry delay in milliseconds
    pub fn retry_delay(&self) -> Option<u64> {
        match self {
            PlatformError::ConnectionTimeout { .. } => Some(5000),
            PlatformError::NetworkError { .. } => Some(2000),
            PlatformError::RequestTimeout { .. } => Some(1000),
            PlatformError::RateLimitExceeded { retry_after_ms } => Some(*retry_after_ms),
            _ => None,
        }
    }

    /// Convert to standardized error code
    pub fn error_code(&self) -> String {
        match self {
            PlatformError::ConnectionFailed { .. } => "E001".to_string(),
            PlatformError::ConnectionTimeout { .. } => "E002".to_string(),
            PlatformError::Disconnected { .. } => "E003".to_string(),
            PlatformError::AuthenticationFailed { .. } => "E004".to_string(),
            PlatformError::OrderValidationFailed { .. } => "E101".to_string(),
            PlatformError::OrderRejected { .. } => "E102".to_string(),
            PlatformError::OrderNotFound { .. } => "E103".to_string(),
            PlatformError::OrderModificationFailed { .. } => "E104".to_string(),
            PlatformError::PositionNotFound { .. } => "E201".to_string(),
            PlatformError::InsufficientMargin { .. } => "E202".to_string(),
            PlatformError::PositionCloseFailed { .. } => "E203".to_string(),
            PlatformError::SymbolNotFound { .. } => "E301".to_string(),
            PlatformError::MarketDataUnavailable { .. } => "E302".to_string(),
            PlatformError::SubscriptionFailed { .. } => "E303".to_string(),
            PlatformError::AccountNotFound { .. } => "E401".to_string(),
            PlatformError::InsufficientFunds { .. } => "E402".to_string(),
            PlatformError::TradingNotAllowed { .. } => "E403".to_string(),
            PlatformError::PlatformNotSupported { .. } => "E501".to_string(),
            PlatformError::PlatformNotFound { .. } => "E502".to_string(),
            PlatformError::FeatureNotSupported { .. } => "E503".to_string(),
            PlatformError::RateLimitExceeded { .. } => "E601".to_string(),
            PlatformError::ApiLimitReached { .. } => "E602".to_string(),
            PlatformError::NetworkError { .. } => "E701".to_string(),
            PlatformError::RequestTimeout { .. } => "E702".to_string(),
            PlatformError::InvalidResponse { .. } => "E703".to_string(),
            PlatformError::ConfigurationError { .. } => "E801".to_string(),
            PlatformError::InvalidCredentials { .. } => "E802".to_string(),
            PlatformError::InitializationFailed { .. } => "E803".to_string(),
            PlatformError::InternalError { .. } => "E901".to_string(),
            PlatformError::Unknown { .. } => "E999".to_string(),
            PlatformError::TradeLocker { .. } => "E_TL".to_string(),
            PlatformError::DXTrade { .. } => "E_DX".to_string(),
            PlatformError::MetaTrader { .. } => "E_MT".to_string(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ErrorSeverity {
    Low,
    Medium,
    High,
    Critical,
}

/// Order validation errors
#[derive(Error, Debug, Clone, Serialize, Deserialize)]
pub enum ValidationError {
    #[error("Invalid symbol: {symbol}")]
    InvalidSymbol { symbol: String },
    
    #[error("Invalid quantity: {quantity}")]
    InvalidQuantity { quantity: rust_decimal::Decimal },
    
    #[error("Invalid price: {price}")]
    InvalidPrice { price: rust_decimal::Decimal },
    
    #[error("Order size too small: minimum {min_size}")]
    OrderTooSmall { min_size: rust_decimal::Decimal },
    
    #[error("Order size too large: maximum {max_size}")]
    OrderTooLarge { max_size: rust_decimal::Decimal },
    
    #[error("Invalid order type for symbol")]
    InvalidOrderTypeForSymbol,
    
    #[error("Market closed for symbol: {symbol}")]
    MarketClosed { symbol: String },
    
    #[error("Invalid time in force for order type")]
    InvalidTimeInForce,
    
    #[error("Missing required field: {field}")]
    MissingRequiredField { field: String },
    
    #[error("Conflicting parameters: {reason}")]
    ConflictingParameters { reason: String },
}

/// Error recovery strategy
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorRecoveryStrategy {
    pub max_retries: u32,
    pub base_delay_ms: u64,
    pub max_delay_ms: u64,
    pub backoff_multiplier: f64,
    pub recoverable_errors: Vec<String>,
}

impl Default for ErrorRecoveryStrategy {
    fn default() -> Self {
        Self {
            max_retries: 3,
            base_delay_ms: 1000,
            max_delay_ms: 30000,
            backoff_multiplier: 2.0,
            recoverable_errors: vec![
                "E002".to_string(), // ConnectionTimeout
                "E701".to_string(), // NetworkError
                "E702".to_string(), // RequestTimeout
                "E601".to_string(), // RateLimitExceeded
                "E302".to_string(), // MarketDataUnavailable
            ],
        }
    }
}

/// Error context for enriched error reporting
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorContext {
    pub timestamp: chrono::DateTime<chrono::Utc>,
    pub operation: String,
    pub platform_type: String,
    pub account_id: Option<String>,
    pub symbol: Option<String>,
    pub order_id: Option<String>,
    pub request_id: Option<String>,
    pub additional_data: HashMap<String, serde_json::Value>,
}

/// Enriched error with full context
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EnrichedError {
    pub error: PlatformError,
    pub context: ErrorContext,
    pub recovery_suggestion: Option<String>,
    pub user_message: Option<String>,
    pub platform_specific_code: Option<String>,
    pub stack_trace: Option<String>,
}

impl EnrichedError {
    pub fn new(error: PlatformError, context: ErrorContext) -> Self {
        let recovery_suggestion = Self::suggest_recovery(&error);
        let user_message = Self::generate_user_message(&error);
        
        Self {
            error,
            context,
            recovery_suggestion,
            user_message,
            platform_specific_code: None,
            stack_trace: None,
        }
    }

    fn suggest_recovery(error: &PlatformError) -> Option<String> {
        match error {
            PlatformError::ConnectionTimeout { .. } => Some("Check network connection and retry".to_string()),
            PlatformError::RateLimitExceeded { retry_after_ms } => Some(format!("Wait {}ms and retry", retry_after_ms)),
            PlatformError::InsufficientMargin { .. } => Some("Reduce position size or add margin".to_string()),
            PlatformError::MarketClosed { .. } => Some("Wait for market to open".to_string()),
            _ => None,
        }
    }

    fn generate_user_message(error: &PlatformError) -> Option<String> {
        match error {
            PlatformError::InsufficientMargin { .. } => Some("Not enough margin to place this order".to_string()),
            PlatformError::InsufficientFunds { .. } => Some("Insufficient account balance".to_string()),
            PlatformError::MarketDataUnavailable { .. } => Some("Market data temporarily unavailable".to_string()),
            PlatformError::TradingNotAllowed { .. } => Some("Trading is currently disabled for this account".to_string()),
            _ => None,
        }
    }
}