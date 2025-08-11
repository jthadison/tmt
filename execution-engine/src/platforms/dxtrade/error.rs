use thiserror::Error;

pub type Result<T> = std::result::Result<T, DXTradeError>;

#[derive(Debug, Error)]
pub enum DXTradeError {
    #[error("SSL authentication failed: {0}")]
    SslAuthenticationFailed(String),
    
    #[error("FIX session error: {0}")]
    FixSessionError(String),
    
    #[error("FIX message error: {0}")]
    FixMessageError(String),
    
    #[error("Order execution error: {0}")]
    OrderExecutionError(String),
    
    #[error("Connection error: {0}")]
    ConnectionError(String),
    
    #[error("Configuration error: {0}")]
    ConfigurationError(String),
    
    #[error("Sequence number error: {0}")]
    SequenceNumberError(String),
    
    #[error("Session management error: {0}")]
    SessionManagementError(String),
    
    #[error("REST API error: {0}")]
    RestApiError(String),
    
    #[error("Market data error: {0}")]
    MarketDataError(String),
    
    #[error("Authentication error: {0}")]
    AuthenticationError(String),
    
    #[error("Timeout error: {0}")]
    TimeoutError(String),
    
    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),
    
    #[error("HTTP client error: {0}")]
    HttpClientError(#[from] reqwest::Error),
    
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
    
    #[error("TLS error: {0}")]
    TlsError(String),
    
    #[error("Parse error: {0}")]
    ParseError(String),
    
    #[error("Business logic error: {0}")]
    BusinessLogicError(String),
}

impl DXTradeError {
    pub fn is_recoverable(&self) -> bool {
        match self {
            Self::ConnectionError(_) => true,
            Self::TimeoutError(_) => true,
            Self::FixSessionError(_) => true,
            Self::SessionManagementError(_) => true,
            Self::RestApiError(_) => true,
            _ => false,
        }
    }
    
    pub fn requires_reconnection(&self) -> bool {
        match self {
            Self::ConnectionError(_) => true,
            Self::FixSessionError(_) => true,
            Self::SslAuthenticationFailed(_) => true,
            Self::SessionManagementError(_) => true,
            _ => false,
        }
    }
    
    pub fn should_retry(&self) -> bool {
        match self {
            Self::TimeoutError(_) => true,
            Self::ConnectionError(_) => true,
            Self::RestApiError(_) => true,
            _ => false,
        }
    }
}