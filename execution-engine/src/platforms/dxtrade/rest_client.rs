use super::config::DXTradeConfig;
use super::error::{DXTradeError, Result};

pub struct RestClient {
    config: DXTradeConfig,
    client: reqwest::Client,
}

impl RestClient {
    pub fn new(config: DXTradeConfig) -> Result<Self> {
        let client = reqwest::Client::builder()
            .timeout(config.connect_timeout())
            .build()
            .map_err(|e| {
                DXTradeError::RestApiError(format!("Failed to create HTTP client: {}", e))
            })?;

        Ok(Self { config, client })
    }
}
