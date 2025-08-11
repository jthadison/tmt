use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use crate::platforms::{PlatformType, TradingPlatform};
use super::interfaces::ITradingPlatform;
use super::adapters::{TradeLockerAdapter, DXTradeAdapter};
use super::errors::PlatformError;

/// Platform configuration union
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "platform_type")]
pub enum PlatformConfig {
    TradeLocker {
        account_id: String,
        api_key: String,
        api_secret: String,
        environment: crate::platforms::tradelocker::TradeLockerEnvironment,
        rate_limit_rps: Option<u32>,
        connection_timeout_ms: Option<u64>,
        retry_config: Option<RetryConfig>,
    },
    DXTrade {
        sender_comp_id: String,
        target_comp_id: String,
        ssl_cert_path: String,
        ssl_key_path: String,
        environment: crate::platforms::dxtrade::DXTradeEnvironment,
        fix_version: String,
        heartbeat_interval: Option<u32>,
        retry_config: Option<RetryConfig>,
    },
    MetaTrader4 {
        server: String,
        login: String,
        password: String,
        expert_advisor_path: Option<String>,
        retry_config: Option<RetryConfig>,
    },
    MetaTrader5 {
        server: String,
        login: String,
        password: String,
        expert_advisor_path: Option<String>,
        retry_config: Option<RetryConfig>,
    },
}

impl PlatformConfig {
    pub fn platform_type(&self) -> PlatformType {
        match self {
            PlatformConfig::TradeLocker { .. } => PlatformType::TradeLocker,
            PlatformConfig::DXTrade { .. } => PlatformType::DXTrade,
            PlatformConfig::MetaTrader4 { .. } => PlatformType::MetaTrader4,
            PlatformConfig::MetaTrader5 { .. } => PlatformType::MetaTrader5,
        }
    }

    pub fn account_identifier(&self) -> String {
        match self {
            PlatformConfig::TradeLocker { account_id, .. } => account_id.clone(),
            PlatformConfig::DXTrade { sender_comp_id, .. } => sender_comp_id.clone(),
            PlatformConfig::MetaTrader4 { login, .. } => login.clone(),
            PlatformConfig::MetaTrader5 { login, .. } => login.clone(),
        }
    }

    pub fn retry_config(&self) -> RetryConfig {
        match self {
            PlatformConfig::TradeLocker { retry_config, .. } |
            PlatformConfig::DXTrade { retry_config, .. } |
            PlatformConfig::MetaTrader4 { retry_config, .. } |
            PlatformConfig::MetaTrader5 { retry_config, .. } => {
                retry_config.clone().unwrap_or_default()
            }
        }
    }
}

/// Retry configuration for platform operations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetryConfig {
    pub max_retries: u32,
    pub initial_delay_ms: u64,
    pub max_delay_ms: u64,
    pub backoff_multiplier: f64,
    pub jitter: bool,
}

impl Default for RetryConfig {
    fn default() -> Self {
        Self {
            max_retries: 3,
            initial_delay_ms: 1000,
            max_delay_ms: 30000,
            backoff_multiplier: 2.0,
            jitter: true,
        }
    }
}

/// Factory for creating platform instances
pub struct PlatformFactory {
    builders: HashMap<PlatformType, Box<dyn PlatformBuilder>>,
}

impl PlatformFactory {
    pub fn new() -> Self {
        let mut factory = Self {
            builders: HashMap::new(),
        };

        // Register platform builders
        factory.register_builder(PlatformType::TradeLocker, Box::new(TradeLockerBuilder));
        factory.register_builder(PlatformType::DXTrade, Box::new(DXTradeBuilder));
        
        factory
    }

    pub fn register_builder(&mut self, platform_type: PlatformType, builder: Box<dyn PlatformBuilder>) {
        self.builders.insert(platform_type, builder);
    }

    pub async fn create_platform(&self, config: PlatformConfig) -> Result<Box<dyn ITradingPlatform>, PlatformError> {
        let platform_type = config.platform_type();
        
        match self.builders.get(&platform_type) {
            Some(builder) => builder.build(config).await,
            None => Err(PlatformError::PlatformNotSupported { 
                platform: format!("{:?}", platform_type) 
            }),
        }
    }

    pub fn supported_platforms(&self) -> Vec<PlatformType> {
        self.builders.keys().cloned().collect()
    }

    pub async fn create_with_validation(&self, config: PlatformConfig) -> Result<Box<dyn ITradingPlatform>, PlatformError> {
        // Validate configuration first
        self.validate_config(&config)?;
        
        // Create platform
        let mut platform = self.create_platform(config).await?;
        
        // Test connection
        platform.connect().await?;
        
        // Verify basic functionality
        match platform.health_check().await {
            Ok(health) => {
                if !health.is_healthy {
                    return Err(PlatformError::InitializationFailed {
                        reason: format!("Health check failed: {:?}", health.issues)
                    });
                }
            }
            Err(e) => {
                return Err(PlatformError::InitializationFailed {
                    reason: format!("Health check error: {}", e)
                });
            }
        }

        Ok(platform)
    }

    fn validate_config(&self, config: &PlatformConfig) -> Result<(), PlatformError> {
        match config {
            PlatformConfig::TradeLocker { account_id, api_key, api_secret, .. } => {
                if account_id.is_empty() {
                    return Err(PlatformError::ConfigurationError {
                        reason: "TradeLocker account_id cannot be empty".to_string()
                    });
                }
                if api_key.is_empty() {
                    return Err(PlatformError::ConfigurationError {
                        reason: "TradeLocker api_key cannot be empty".to_string()
                    });
                }
                if api_secret.is_empty() {
                    return Err(PlatformError::ConfigurationError {
                        reason: "TradeLocker api_secret cannot be empty".to_string()
                    });
                }
            }
            PlatformConfig::DXTrade { sender_comp_id, target_comp_id, ssl_cert_path, ssl_key_path, .. } => {
                if sender_comp_id.is_empty() {
                    return Err(PlatformError::ConfigurationError {
                        reason: "DXTrade sender_comp_id cannot be empty".to_string()
                    });
                }
                if target_comp_id.is_empty() {
                    return Err(PlatformError::ConfigurationError {
                        reason: "DXTrade target_comp_id cannot be empty".to_string()
                    });
                }
                if ssl_cert_path.is_empty() || ssl_key_path.is_empty() {
                    return Err(PlatformError::ConfigurationError {
                        reason: "DXTrade SSL certificate paths cannot be empty".to_string()
                    });
                }
                
                // Verify SSL files exist
                if !std::path::Path::new(ssl_cert_path).exists() {
                    return Err(PlatformError::ConfigurationError {
                        reason: format!("SSL certificate file not found: {}", ssl_cert_path)
                    });
                }
                if !std::path::Path::new(ssl_key_path).exists() {
                    return Err(PlatformError::ConfigurationError {
                        reason: format!("SSL key file not found: {}", ssl_key_path)
                    });
                }
            }
            PlatformConfig::MetaTrader4 { login, password, server, .. } |
            PlatformConfig::MetaTrader5 { login, password, server, .. } => {
                if login.is_empty() {
                    return Err(PlatformError::ConfigurationError {
                        reason: "MetaTrader login cannot be empty".to_string()
                    });
                }
                if password.is_empty() {
                    return Err(PlatformError::ConfigurationError {
                        reason: "MetaTrader password cannot be empty".to_string()
                    });
                }
                if server.is_empty() {
                    return Err(PlatformError::ConfigurationError {
                        reason: "MetaTrader server cannot be empty".to_string()
                    });
                }
            }
        }
        
        Ok(())
    }
}

impl Default for PlatformFactory {
    fn default() -> Self {
        Self::new()
    }
}

/// Platform builder trait
#[async_trait]
pub trait PlatformBuilder: Send + Sync {
    async fn build(&self, config: PlatformConfig) -> Result<Box<dyn ITradingPlatform>, PlatformError>;
    fn supports(&self, platform_type: PlatformType) -> bool;
}

/// TradeLocker platform builder
pub struct TradeLockerBuilder;

#[async_trait]
impl PlatformBuilder for TradeLockerBuilder {
    async fn build(&self, config: PlatformConfig) -> Result<Box<dyn ITradingPlatform>, PlatformError> {
        match config {
            PlatformConfig::TradeLocker { 
                account_id, 
                api_key, 
                api_secret, 
                environment,
                rate_limit_rps,
                connection_timeout_ms,
                retry_config,
            } => {
                let credentials = crate::platforms::tradelocker::TradeLockerCredentials {
                    account_id,
                    api_key,
                    api_secret,
                    environment,
                };

                let mut config_builder = crate::platforms::tradelocker::TradeLockerConfig::new(credentials);
                
                if let Some(rps) = rate_limit_rps {
                    config_builder = config_builder.with_rate_limit(rps);
                }
                
                if let Some(timeout) = connection_timeout_ms {
                    config_builder = config_builder.with_connection_timeout(std::time::Duration::from_millis(timeout));
                }

                let tl_config = config_builder.build();
                let client = crate::platforms::tradelocker::TradeLockerClient::new(tl_config).await
                    .map_err(|e| PlatformError::InitializationFailed {
                        reason: format!("TradeLocker client creation failed: {}", e)
                    })?;

                let adapter = TradeLockerAdapter::new(client, retry_config.unwrap_or_default());
                Ok(Box::new(adapter))
            }
            _ => Err(PlatformError::ConfigurationError {
                reason: "Invalid configuration for TradeLocker platform".to_string()
            }),
        }
    }

    fn supports(&self, platform_type: PlatformType) -> bool {
        matches!(platform_type, PlatformType::TradeLocker)
    }
}

/// DXTrade platform builder
pub struct DXTradeBuilder;

#[async_trait]
impl PlatformBuilder for DXTradeBuilder {
    async fn build(&self, config: PlatformConfig) -> Result<Box<dyn ITradingPlatform>, PlatformError> {
        match config {
            PlatformConfig::DXTrade { 
                sender_comp_id, 
                target_comp_id, 
                ssl_cert_path, 
                ssl_key_path, 
                environment,
                fix_version,
                heartbeat_interval,
                retry_config,
            } => {
                let credentials = crate::platforms::dxtrade::DXTradeCredentials {
                    sender_comp_id,
                    target_comp_id,
                    ssl_cert_path,
                    ssl_key_path,
                    environment,
                    fix_version,
                };

                let mut config_builder = crate::platforms::dxtrade::DXTradeConfig::new(credentials);
                
                if let Some(interval) = heartbeat_interval {
                    config_builder = config_builder.with_heartbeat_interval(interval);
                }

                let dx_config = config_builder.build();
                let client = crate::platforms::dxtrade::DXTradeClient::new(dx_config).await
                    .map_err(|e| PlatformError::InitializationFailed {
                        reason: format!("DXTrade client creation failed: {}", e)
                    })?;

                let adapter = DXTradeAdapter::new(client, retry_config.unwrap_or_default());
                Ok(Box::new(adapter))
            }
            _ => Err(PlatformError::ConfigurationError {
                reason: "Invalid configuration for DXTrade platform".to_string()
            }),
        }
    }

    fn supports(&self, platform_type: PlatformType) -> bool {
        matches!(platform_type, PlatformType::DXTrade)
    }
}

/// Platform registry for managing multiple platform instances
pub struct PlatformRegistry {
    platforms: HashMap<String, Box<dyn ITradingPlatform>>,
    factory: PlatformFactory,
}

impl PlatformRegistry {
    pub fn new() -> Self {
        Self {
            platforms: HashMap::new(),
            factory: PlatformFactory::new(),
        }
    }

    pub async fn register(&mut self, account_id: String, config: PlatformConfig) -> Result<(), PlatformError> {
        let platform = self.factory.create_with_validation(config).await?;
        self.platforms.insert(account_id, platform);
        Ok(())
    }

    pub fn get(&self, account_id: &str) -> Option<&dyn ITradingPlatform> {
        self.platforms.get(account_id).map(|p| p.as_ref())
    }

    pub fn get_mut(&mut self, account_id: &str) -> Option<&mut dyn ITradingPlatform> {
        self.platforms.get_mut(account_id).map(|p| p.as_mut())
    }

    pub async fn remove(&mut self, account_id: &str) -> Result<(), PlatformError> {
        if let Some(mut platform) = self.platforms.remove(account_id) {
            platform.disconnect().await?;
        }
        Ok(())
    }

    pub fn list_accounts(&self) -> Vec<String> {
        self.platforms.keys().cloned().collect()
    }

    pub async fn health_check_all(&self) -> HashMap<String, Result<super::interfaces::HealthStatus, PlatformError>> {
        let mut results = HashMap::new();
        
        for (account_id, platform) in &self.platforms {
            let health = platform.health_check().await;
            results.insert(account_id.clone(), health);
        }
        
        results
    }

    pub async fn disconnect_all(&mut self) -> Vec<(String, Result<(), PlatformError>)> {
        let mut results = Vec::new();
        
        for (account_id, platform) in &mut self.platforms {
            let result = platform.disconnect().await;
            results.push((account_id.clone(), result));
        }
        
        results
    }
}

impl Default for PlatformRegistry {
    fn default() -> Self {
        Self::new()
    }
}