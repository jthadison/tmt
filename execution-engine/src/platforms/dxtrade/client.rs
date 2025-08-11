use super::config::DXTradeConfig;
use super::error::{DXTradeError, Result};
use super::fix_client::FIXClient;
use super::rest_client::RestClient;
use crate::platforms::{PlatformType, TradingPlatform};

pub struct DXTradeClient {
    config: DXTradeConfig,
    fix_client: FIXClient,
    rest_client: RestClient,
}

impl DXTradeClient {
    pub fn new(config: DXTradeConfig) -> Result<Self> {
        let fix_client = FIXClient::new(config.clone())?;
        let rest_client = RestClient::new(config.clone())?;
        
        Ok(Self {
            config,
            fix_client,
            rest_client,
        })
    }
    
    pub async fn connect(&self) -> Result<()> {
        self.fix_client.connect().await
    }
    
    pub async fn disconnect(&self) -> Result<()> {
        self.fix_client.disconnect().await
    }
}

impl TradingPlatform for DXTradeClient {
    fn platform_type(&self) -> PlatformType {
        PlatformType::DXTrade
    }
}