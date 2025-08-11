use std::sync::Arc;
use std::time::{Duration, Instant};
use reqwest::{Client, RequestBuilder};
use serde::Deserialize;
use serde_json::Value;
use tracing::{info, warn};
use tokio::sync::Semaphore;

use super::{
    TradeLockerAuth, TradeLockerConfig, TradeLockerError, Result,
    TradeLockerEnvironment, OrderRequest, OrderResponse, 
    Position, AccountInfo
};
use crate::monitoring::metrics::{TRADELOCKER_REQUEST_DURATION, TRADELOCKER_REQUEST_COUNT};

#[derive(Debug)]
pub struct TradeLockerClient {
    client: Client,
    auth: Arc<TradeLockerAuth>,
    config: TradeLockerConfig,
    environment: TradeLockerEnvironment,
    request_semaphore: Arc<Semaphore>,
}

impl TradeLockerClient {
    pub fn new(
        auth: Arc<TradeLockerAuth>,
        config: TradeLockerConfig,
        environment: TradeLockerEnvironment,
    ) -> Result<Self> {
        let client = Client::builder()
            .pool_max_idle_per_host(config.max_connections_per_account)
            .pool_idle_timeout(Duration::from_secs(60))
            .connect_timeout(config.connection_timeout())
            .timeout(config.request_timeout())
            .build()
            .map_err(|e| TradeLockerError::Connection(e.to_string()))?;

        let request_semaphore = Arc::new(Semaphore::new(config.max_concurrent_orders));

        Ok(Self {
            client,
            auth,
            config,
            environment,
            request_semaphore,
        })
    }

    async fn execute_request<T>(&self, account_id: &str, request: RequestBuilder) -> Result<T>
    where
        T: for<'de> Deserialize<'de>,
    {
        let start = Instant::now();
        let mut retries = 0;

        loop {
            let token = self.auth.get_token(account_id).await?;
            
            let req = request
                .try_clone()
                .ok_or_else(|| TradeLockerError::Internal("Failed to clone request".into()))?
                .header("Authorization", format!("Bearer {}", token))
                .header("Content-Type", "application/json");

            match req.send().await {
                Ok(response) => {
                    let status = response.status();
                    let elapsed = start.elapsed().as_millis() as f64;
                    
                    TRADELOCKER_REQUEST_DURATION.observe(elapsed);
                    TRADELOCKER_REQUEST_COUNT.with_label_values(&[
                        &status.as_u16().to_string()
                    ]).inc();

                    if status.is_success() {
                        return response.json::<T>().await
                            .map_err(|e| TradeLockerError::Serialization(e.to_string()));
                    }

                    // Handle specific error codes
                    if status.as_u16() == 429 {
                        let retry_after = response
                            .headers()
                            .get("Retry-After")
                            .and_then(|v| v.to_str().ok())
                            .and_then(|v| v.parse::<u64>().ok())
                            .unwrap_or(60);

                        return Err(TradeLockerError::RateLimit { retry_after });
                    }

                    if status.as_u16() == 401 {
                        // Token might be invalid, try to refresh
                        self.auth.invalidate_token(account_id).await;
                        
                        if retries < self.config.max_retries {
                            retries += 1;
                            tokio::time::sleep(self.config.retry_delay()).await;
                            continue;
                        }
                    }

                    let error_body = response.text().await.unwrap_or_default();
                    return Err(TradeLockerError::Api {
                        code: status.to_string(),
                        message: error_body,
                    });
                }
                Err(e) => {
                    if retries < self.config.max_retries {
                        retries += 1;
                        warn!("Request failed (attempt {}): {}", retries, e);
                        tokio::time::sleep(self.config.retry_delay()).await;
                        continue;
                    }
                    return Err(e.into());
                }
            }
        }
    }

    pub async fn place_order(&self, account_id: &str, order: OrderRequest) -> Result<OrderResponse> {
        let _permit = self.request_semaphore.acquire().await
            .map_err(|e| TradeLockerError::Internal(e.to_string()))?;

        if self.config.pre_validate_orders {
            self.validate_order(&order)?;
        }

        let url = format!("{}/api/v1/orders", self.environment.base_url());
        let request = self.client.post(&url).json(&order);

        let start = Instant::now();
        let response = self.execute_request::<OrderResponse>(account_id, request).await?;
        let elapsed = start.elapsed().as_millis();

        if elapsed > self.config.order_execution_timeout_ms as u128 {
            warn!("Order execution took {}ms, exceeding target of {}ms", 
                elapsed, self.config.order_execution_timeout_ms);
        }

        info!("Order placed in {}ms: {:?}", elapsed, response.order_id);
        Ok(response)
    }

    pub async fn modify_order(
        &self, 
        account_id: &str, 
        order_id: &str, 
        modifications: Value
    ) -> Result<OrderResponse> {
        let url = format!("{}/api/v1/orders/{}", self.environment.base_url(), order_id);
        let request = self.client.put(&url).json(&modifications);

        self.execute_request::<OrderResponse>(account_id, request).await
    }

    pub async fn cancel_order(&self, account_id: &str, order_id: &str) -> Result<()> {
        let url = format!("{}/api/v1/orders/{}", self.environment.base_url(), order_id);
        let request = self.client.delete(&url);

        self.execute_request::<Value>(account_id, request).await?;
        Ok(())
    }

    pub async fn get_positions(&self, account_id: &str) -> Result<Vec<Position>> {
        let url = format!("{}/api/v1/positions", self.environment.base_url());
        let request = self.client.get(&url);

        self.execute_request::<Vec<Position>>(account_id, request).await
    }

    pub async fn close_position(
        &self, 
        account_id: &str, 
        position_id: &str,
        quantity: Option<f64>
    ) -> Result<()> {
        let url = format!("{}/api/v1/positions/{}/close", self.environment.base_url(), position_id);
        
        let body = if let Some(qty) = quantity {
            serde_json::json!({ "quantity": qty })
        } else {
            serde_json::json!({})
        };

        let request = self.client.post(&url).json(&body);
        self.execute_request::<Value>(account_id, request).await?;
        Ok(())
    }

    pub async fn modify_position(
        &self,
        account_id: &str,
        position_id: &str,
        stop_loss: Option<f64>,
        take_profit: Option<f64>
    ) -> Result<Position> {
        let url = format!("{}/api/v1/positions/{}", self.environment.base_url(), position_id);
        
        let body = serde_json::json!({
            "stop_loss": stop_loss,
            "take_profit": take_profit
        });

        let request = self.client.put(&url).json(&body);
        self.execute_request::<Position>(account_id, request).await
    }

    pub async fn get_account_info(&self, account_id: &str) -> Result<AccountInfo> {
        let url = format!("{}/api/v1/account", self.environment.base_url());
        let request = self.client.get(&url);

        self.execute_request::<AccountInfo>(account_id, request).await
    }

    pub async fn get_account_balance(&self, account_id: &str) -> Result<Value> {
        let url = format!("{}/api/v1/account/balance", self.environment.base_url());
        let request = self.client.get(&url);

        self.execute_request::<Value>(account_id, request).await
    }

    fn validate_order(&self, order: &OrderRequest) -> Result<()> {
        use rust_decimal::Decimal;
        use std::str::FromStr;

        // Validate quantity
        if order.quantity <= Decimal::from_str("0").unwrap() {
            return Err(TradeLockerError::InvalidRequest(
                "Order quantity must be positive".into()
            ));
        }

        // Validate limit orders have price
        if matches!(order.order_type, super::OrderType::Limit | super::OrderType::StopLimit) {
            if order.price.is_none() || order.price == Some(Decimal::from_str("0").unwrap()) {
                return Err(TradeLockerError::InvalidRequest(
                    "Limit orders require a valid price".into()
                ));
            }
        }

        // Validate stop orders have stop price
        if matches!(order.order_type, super::OrderType::Stop | super::OrderType::StopLimit) {
            if order.stop_price.is_none() || order.stop_price == Some(Decimal::from_str("0").unwrap()) {
                return Err(TradeLockerError::InvalidRequest(
                    "Stop orders require a valid stop price".into()
                ));
            }
        }

        // Validate stop loss and take profit
        if let Some(sl) = order.stop_loss {
            if sl <= Decimal::from_str("0").unwrap() {
                return Err(TradeLockerError::InvalidRequest(
                    "Stop loss must be positive".into()
                ));
            }
        }

        if let Some(tp) = order.take_profit {
            if tp <= Decimal::from_str("0").unwrap() {
                return Err(TradeLockerError::InvalidRequest(
                    "Take profit must be positive".into()
                ));
            }
        }

        Ok(())
    }

    pub async fn health_check(&self) -> Result<bool> {
        let url = format!("{}/health", self.environment.base_url());
        let response = self.client
            .get(&url)
            .timeout(Duration::from_secs(5))
            .send()
            .await?;

        Ok(response.status().is_success())
    }
}