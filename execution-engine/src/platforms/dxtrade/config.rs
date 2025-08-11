use super::error::{DXTradeError, Result};
use super::DXTradeEnvironment;
use serde::{Deserialize, Serialize};
use std::time::Duration;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DXTradeConfig {
    pub credentials: DXTradeCredentials,
    pub connection: ConnectionConfig,
    pub fix_settings: FIXSettings,
    pub performance: PerformanceConfig,
    pub ssl: SslConfig,
    pub logging: LoggingConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DXTradeCredentials {
    pub sender_comp_id: String,
    pub target_comp_id: String,
    pub sender_sub_id: Option<String>,
    pub target_sub_id: Option<String>,
    pub environment: DXTradeEnvironment,
    pub account_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConnectionConfig {
    pub connect_timeout_ms: u64,
    pub read_timeout_ms: u64,
    pub write_timeout_ms: u64,
    pub heartbeat_interval_s: u32,
    pub test_request_delay_s: u32,
    pub max_reconnect_attempts: u32,
    pub reconnect_backoff_ms: u64,
    pub max_reconnect_delay_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FIXSettings {
    pub fix_version: String,
    pub begin_string: String,
    pub reset_on_logon: bool,
    pub reset_on_logout: bool,
    pub reset_on_disconnect: bool,
    pub validate_length_and_checksum: bool,
    pub validate_fields_out_of_order: bool,
    pub validate_fields_have_values: bool,
    pub validate_user_defined_fields: bool,
    pub allow_unknown_msg_fields: bool,
    pub preserve_message_fields_order: bool,
    pub check_company_id: bool,
    pub check_latency: bool,
    pub max_latency_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceConfig {
    pub message_pool_size: usize,
    pub use_zero_copy: bool,
    pub enable_batching: bool,
    pub max_batch_size: usize,
    pub batch_timeout_ms: u64,
    pub enable_binary_encoding: bool,
    pub pre_allocate_buffers: bool,
    pub buffer_size: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SslConfig {
    pub cert_file_path: String,
    pub key_file_path: String,
    pub ca_file_path: Option<String>,
    pub verify_peer: bool,
    pub verify_hostname: bool,
    pub ssl_version: String,
    pub cipher_list: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LoggingConfig {
    pub enable_fix_logging: bool,
    pub log_incoming_messages: bool,
    pub log_outgoing_messages: bool,
    pub log_heartbeats: bool,
    pub log_test_requests: bool,
    pub log_sequence_resets: bool,
    pub log_directory: String,
    pub max_log_file_size_mb: u64,
    pub max_log_files: u32,
    pub compress_logs: bool,
}

impl Default for DXTradeConfig {
    fn default() -> Self {
        Self {
            credentials: DXTradeCredentials {
                sender_comp_id: String::new(),
                target_comp_id: String::new(),
                sender_sub_id: None,
                target_sub_id: None,
                environment: DXTradeEnvironment::Test,
                account_id: String::new(),
            },
            connection: ConnectionConfig::default(),
            fix_settings: FIXSettings::default(),
            performance: PerformanceConfig::default(),
            ssl: SslConfig::default(),
            logging: LoggingConfig::default(),
        }
    }
}

impl Default for ConnectionConfig {
    fn default() -> Self {
        Self {
            connect_timeout_ms: 5000,
            read_timeout_ms: 30000,
            write_timeout_ms: 5000,
            heartbeat_interval_s: 30,
            test_request_delay_s: 120,
            max_reconnect_attempts: 5,
            reconnect_backoff_ms: 1000,
            max_reconnect_delay_ms: 30000,
        }
    }
}

impl Default for FIXSettings {
    fn default() -> Self {
        Self {
            fix_version: "FIX.4.4".to_string(),
            begin_string: "FIX.4.4".to_string(),
            reset_on_logon: false,
            reset_on_logout: false,
            reset_on_disconnect: false,
            validate_length_and_checksum: true,
            validate_fields_out_of_order: true,
            validate_fields_have_values: true,
            validate_user_defined_fields: true,
            allow_unknown_msg_fields: false,
            preserve_message_fields_order: false,
            check_company_id: true,
            check_latency: true,
            max_latency_ms: 1000,
        }
    }
}

impl Default for PerformanceConfig {
    fn default() -> Self {
        Self {
            message_pool_size: 1000,
            use_zero_copy: true,
            enable_batching: false,
            max_batch_size: 10,
            batch_timeout_ms: 10,
            enable_binary_encoding: false,
            pre_allocate_buffers: true,
            buffer_size: 8192,
        }
    }
}

impl Default for SslConfig {
    fn default() -> Self {
        Self {
            cert_file_path: String::new(),
            key_file_path: String::new(),
            ca_file_path: None,
            verify_peer: true,
            verify_hostname: true,
            ssl_version: "TLSv1.2".to_string(),
            cipher_list: None,
        }
    }
}

impl Default for LoggingConfig {
    fn default() -> Self {
        Self {
            enable_fix_logging: true,
            log_incoming_messages: true,
            log_outgoing_messages: true,
            log_heartbeats: false,
            log_test_requests: false,
            log_sequence_resets: true,
            log_directory: "./logs/dxtrade/fix".to_string(),
            max_log_file_size_mb: 100,
            max_log_files: 30,
            compress_logs: true,
        }
    }
}

impl DXTradeConfig {
    pub fn validate(&self) -> Result<()> {
        if self.credentials.sender_comp_id.is_empty() {
            return Err(DXTradeError::ConfigurationError(
                "sender_comp_id cannot be empty".to_string()
            ));
        }
        
        if self.credentials.target_comp_id.is_empty() {
            return Err(DXTradeError::ConfigurationError(
                "target_comp_id cannot be empty".to_string()
            ));
        }
        
        if self.credentials.account_id.is_empty() {
            return Err(DXTradeError::ConfigurationError(
                "account_id cannot be empty".to_string()
            ));
        }
        
        if self.ssl.cert_file_path.is_empty() {
            return Err(DXTradeError::ConfigurationError(
                "SSL certificate file path cannot be empty".to_string()
            ));
        }
        
        if self.ssl.key_file_path.is_empty() {
            return Err(DXTradeError::ConfigurationError(
                "SSL key file path cannot be empty".to_string()
            ));
        }
        
        if !std::path::Path::new(&self.ssl.cert_file_path).exists() {
            return Err(DXTradeError::ConfigurationError(
                format!("SSL certificate file not found: {}", self.ssl.cert_file_path)
            ));
        }
        
        if !std::path::Path::new(&self.ssl.key_file_path).exists() {
            return Err(DXTradeError::ConfigurationError(
                format!("SSL key file not found: {}", self.ssl.key_file_path)
            ));
        }
        
        if self.connection.heartbeat_interval_s < 10 {
            return Err(DXTradeError::ConfigurationError(
                "heartbeat_interval_s must be at least 10 seconds".to_string()
            ));
        }
        
        if self.connection.connect_timeout_ms > 60000 {
            return Err(DXTradeError::ConfigurationError(
                "connect_timeout_ms should not exceed 60 seconds".to_string()
            ));
        }
        
        Ok(())
    }
    
    pub fn connect_timeout(&self) -> Duration {
        Duration::from_millis(self.connection.connect_timeout_ms)
    }
    
    pub fn read_timeout(&self) -> Duration {
        Duration::from_millis(self.connection.read_timeout_ms)
    }
    
    pub fn write_timeout(&self) -> Duration {
        Duration::from_millis(self.connection.write_timeout_ms)
    }
    
    pub fn heartbeat_interval(&self) -> Duration {
        Duration::from_secs(self.connection.heartbeat_interval_s as u64)
    }
    
    pub fn reconnect_backoff(&self) -> Duration {
        Duration::from_millis(self.connection.reconnect_backoff_ms)
    }
}