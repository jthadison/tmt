use thiserror::Error;

#[derive(Error, Debug)]
pub enum TradeLockerError {
    #[error("Authentication error: {0}")]
    Auth(String),
    
    #[error("Connection error: {0}")]
    Connection(String),
    
    #[error("API error: {code} - {message}")]
    Api { code: String, message: String },
    
    #[error("Rate limit exceeded: retry after {retry_after} seconds")]
    RateLimit { retry_after: u64 },
    
    #[error("Order rejected: {0}")]
    OrderRejected(String),
    
    #[error("Invalid request: {0}")]
    InvalidRequest(String),
    
    #[error("WebSocket error: {0}")]
    WebSocket(String),
    
    #[error("Timeout error: operation took longer than {0} ms")]
    Timeout(u64),
    
    #[error("Serialization error: {0}")]
    Serialization(String),
    
    #[error("Account not found: {0}")]
    AccountNotFound(String),
    
    #[error("Insufficient margin: required {required}, available {available}")]
    InsufficientMargin { required: String, available: String },
    
    #[error("Symbol not found: {0}")]
    SymbolNotFound(String),
    
    #[error("Internal error: {0}")]
    Internal(String),
}

pub type Result<T> = std::result::Result<T, TradeLockerError>;

impl From<serde_json::Error> for TradeLockerError {
    fn from(err: serde_json::Error) -> Self {
        TradeLockerError::Serialization(err.to_string())
    }
}

impl From<reqwest::Error> for TradeLockerError {
    fn from(err: reqwest::Error) -> Self {
        if err.is_timeout() {
            TradeLockerError::Timeout(30000) // Default 30s timeout
        } else if err.is_connect() {
            TradeLockerError::Connection(format!("Failed to connect: {}", err))
        } else {
            TradeLockerError::Connection(err.to_string())
        }
    }
}