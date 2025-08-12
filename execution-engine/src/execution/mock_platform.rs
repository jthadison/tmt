use async_trait::async_trait;
use chrono::{DateTime, Utc};
use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::{mpsc, RwLock};

use crate::platforms::abstraction::{
    capabilities::{PlatformCapabilities, PlatformFeature},
    errors::PlatformError,
    events::PlatformEvent,
    interfaces::{DiagnosticsInfo, HealthStatus, ITradingPlatform, OrderFilter},
    models::{
        AccountType, MarginInfo, OrderMetadata, UnifiedAccountInfo, UnifiedMarketData,
        UnifiedOrder, UnifiedOrderResponse, UnifiedOrderSide, UnifiedOrderStatus, UnifiedOrderType,
        UnifiedPosition, UnifiedTimeInForce,
    },
};
use crate::platforms::PlatformType;

#[derive(Clone)]
pub struct MockTradingPlatform {
    pub name: String,
    pub should_fail: bool,
    pub execution_delay_ms: u64,
    pub orders: Arc<RwLock<Vec<UnifiedOrderResponse>>>,
    pub account_balance: Decimal,
}

impl MockTradingPlatform {
    pub fn new(name: &str) -> Self {
        Self {
            name: name.to_string(),
            should_fail: false,
            execution_delay_ms: 10,
            orders: Arc::new(RwLock::new(Vec::new())),
            account_balance: Decimal::from(10000),
        }
    }

    pub fn with_failure(name: &str) -> Self {
        let mut platform = Self::new(name);
        platform.should_fail = true;
        platform
    }

    pub fn with_delay(name: &str, delay_ms: u64) -> Self {
        let mut platform = Self::new(name);
        platform.execution_delay_ms = delay_ms;
        platform
    }
}

#[async_trait]
impl ITradingPlatform for MockTradingPlatform {
    fn platform_type(&self) -> PlatformType {
        PlatformType::Mock
    }

    fn platform_name(&self) -> &str {
        &self.name
    }

    fn platform_version(&self) -> &str {
        "1.0.0-mock"
    }

    async fn connect(&mut self) -> Result<(), PlatformError> {
        if self.should_fail {
            return Err(PlatformError::ConnectionFailed {
                reason: "Mock connection failure".to_string(),
            });
        }
        Ok(())
    }

    async fn disconnect(&mut self) -> Result<(), PlatformError> {
        Ok(())
    }

    async fn is_connected(&self) -> bool {
        !self.should_fail
    }

    async fn ping(&self) -> Result<u64, PlatformError> {
        if self.should_fail {
            return Err(PlatformError::NetworkError {
                reason: "Mock ping failure".to_string(),
            });
        }
        Ok(self.execution_delay_ms)
    }

    async fn place_order(
        &self,
        mut order: UnifiedOrder,
    ) -> Result<UnifiedOrderResponse, PlatformError> {
        if self.should_fail {
            return Err(PlatformError::OrderRejected {
                reason: "Mock order failure".to_string(),
                platform_code: None,
            });
        }

        tokio::time::sleep(std::time::Duration::from_millis(self.execution_delay_ms)).await;

        let response = UnifiedOrderResponse {
            platform_order_id: format!("MOCK_{}", order.client_order_id),
            client_order_id: order.client_order_id,
            status: UnifiedOrderStatus::Filled,
            symbol: order.symbol,
            side: order.side,
            order_type: order.order_type,
            quantity: order.quantity,
            filled_quantity: order.quantity,
            remaining_quantity: Decimal::ZERO,
            price: order
                .price
                .or(Some(Decimal::from_f64_retain(1.0900).unwrap())),
            average_fill_price: Some(Decimal::from_f64_retain(1.0900).unwrap()),
            commission: Some(Decimal::from_f64_retain(2.0).unwrap()),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            filled_at: Some(Utc::now()),
            platform_specific: HashMap::new(),
        };

        let mut orders = self.orders.write().await;
        orders.push(response.clone());

        Ok(response)
    }

    async fn modify_order(
        &self,
        _order_id: &str,
        _modifications: crate::platforms::abstraction::models::OrderModification,
    ) -> Result<UnifiedOrderResponse, PlatformError> {
        if self.should_fail {
            return Err(PlatformError::OrderModificationFailed {
                reason: "Mock modify failure".to_string(),
            });
        }

        // Return a mock modified order
        Ok(UnifiedOrderResponse {
            platform_order_id: "MOCK_MODIFIED".to_string(),
            client_order_id: "modified".to_string(),
            status: UnifiedOrderStatus::New,
            symbol: "EURUSD".to_string(),
            side: UnifiedOrderSide::Buy,
            order_type: UnifiedOrderType::Limit,
            quantity: Decimal::from(100),
            filled_quantity: Decimal::ZERO,
            remaining_quantity: Decimal::from(100),
            price: Some(Decimal::from_f64_retain(1.0900).unwrap()),
            average_fill_price: None,
            commission: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
            filled_at: None,
            platform_specific: HashMap::new(),
        })
    }

    async fn cancel_order(&self, _order_id: &str) -> Result<(), PlatformError> {
        if self.should_fail {
            return Err(PlatformError::OrderRejected {
                reason: "Mock cancel failure".to_string(),
                platform_code: None,
            });
        }
        Ok(())
    }

    async fn get_order(&self, order_id: &str) -> Result<UnifiedOrderResponse, PlatformError> {
        let orders = self.orders.read().await;
        orders
            .iter()
            .find(|o| o.platform_order_id == order_id || o.client_order_id == order_id)
            .cloned()
            .ok_or_else(|| PlatformError::OrderNotFound {
                order_id: order_id.to_string(),
            })
    }

    async fn get_orders(
        &self,
        filter: Option<OrderFilter>,
    ) -> Result<Vec<UnifiedOrderResponse>, PlatformError> {
        let orders = self.orders.read().await;

        if let Some(filter) = filter {
            let filtered: Vec<UnifiedOrderResponse> = orders
                .iter()
                .filter(|order| {
                    if let Some(ref order_id) = filter.order_id {
                        return order.platform_order_id == *order_id
                            || order.client_order_id == *order_id;
                    }
                    if let Some(ref symbol) = filter.symbol {
                        if order.symbol != *symbol {
                            return false;
                        }
                    }
                    if let Some(ref status) = filter.status {
                        if order.status != *status {
                            return false;
                        }
                    }
                    true
                })
                .cloned()
                .collect();

            let limit = filter.limit.unwrap_or(filtered.len());
            Ok(filtered.into_iter().take(limit).collect())
        } else {
            Ok(orders.clone())
        }
    }

    async fn get_positions(&self) -> Result<Vec<UnifiedPosition>, PlatformError> {
        // Return empty positions for mock
        Ok(Vec::new())
    }

    async fn get_position(&self, _symbol: &str) -> Result<Option<UnifiedPosition>, PlatformError> {
        Ok(None)
    }

    async fn close_position(
        &self,
        _symbol: &str,
        _quantity: Option<Decimal>,
    ) -> Result<UnifiedOrderResponse, PlatformError> {
        if self.should_fail {
            return Err(PlatformError::PositionCloseFailed {
                reason: "Mock close position failure".to_string(),
            });
        }

        Ok(UnifiedOrderResponse {
            platform_order_id: "MOCK_CLOSE".to_string(),
            client_order_id: "close".to_string(),
            status: UnifiedOrderStatus::Filled,
            symbol: "EURUSD".to_string(),
            side: UnifiedOrderSide::Sell,
            order_type: UnifiedOrderType::Market,
            quantity: Decimal::from(100),
            filled_quantity: Decimal::from(100),
            remaining_quantity: Decimal::ZERO,
            price: Some(Decimal::from_f64_retain(1.0900).unwrap()),
            average_fill_price: Some(Decimal::from_f64_retain(1.0900).unwrap()),
            commission: Some(Decimal::from_f64_retain(2.0).unwrap()),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            filled_at: Some(Utc::now()),
            platform_specific: HashMap::new(),
        })
    }

    async fn get_account_info(&self) -> Result<UnifiedAccountInfo, PlatformError> {
        if self.should_fail {
            return Err(PlatformError::AccountNotFound {
                account_id: "Mock account info failure".to_string(),
            });
        }

        Ok(UnifiedAccountInfo {
            account_id: self.name.clone(),
            account_name: Some(self.name.clone()),
            currency: "USD".to_string(),
            balance: self.account_balance,
            equity: self.account_balance,
            margin_used: Decimal::ZERO,
            margin_available: self.account_balance,
            buying_power: self.account_balance,
            unrealized_pnl: Decimal::ZERO,
            realized_pnl: Decimal::ZERO,
            margin_level: Some(Decimal::ZERO),
            account_type: AccountType::Demo,
            last_updated: Utc::now(),
            platform_specific: HashMap::new(),
        })
    }

    async fn get_balance(&self) -> Result<Decimal, PlatformError> {
        Ok(self.account_balance)
    }

    async fn get_margin_info(&self) -> Result<MarginInfo, PlatformError> {
        Ok(MarginInfo {
            initial_margin: Decimal::ZERO,
            maintenance_margin: Decimal::ZERO,
            margin_call_level: None,
            stop_out_level: None,
            margin_requirements: HashMap::new(),
        })
    }

    async fn get_market_data(&self, _symbol: &str) -> Result<UnifiedMarketData, PlatformError> {
        Ok(UnifiedMarketData {
            symbol: "EURUSD".to_string(),
            bid: Decimal::from_f64_retain(1.0899).unwrap(),
            ask: Decimal::from_f64_retain(1.0901).unwrap(),
            spread: Decimal::from_f64_retain(0.0002).unwrap(),
            last_price: Some(Decimal::from_f64_retain(1.0900).unwrap()),
            volume: Some(Decimal::from(1000)),
            high: Some(Decimal::from_f64_retain(1.0920).unwrap()),
            low: Some(Decimal::from_f64_retain(1.0880).unwrap()),
            timestamp: Utc::now(),
            session: None,
            platform_specific: HashMap::new(),
        })
    }

    async fn subscribe_market_data(
        &self,
        _symbols: Vec<String>,
    ) -> Result<mpsc::Receiver<UnifiedMarketData>, PlatformError> {
        let (_tx, rx) = mpsc::channel(100);
        Ok(rx)
    }

    async fn unsubscribe_market_data(&self, _symbols: Vec<String>) -> Result<(), PlatformError> {
        Ok(())
    }

    fn capabilities(&self) -> PlatformCapabilities {
        PlatformCapabilities::new(self.name.clone())
    }

    async fn subscribe_events(&self) -> Result<mpsc::Receiver<PlatformEvent>, PlatformError> {
        let (_tx, rx) = mpsc::channel(100);
        Ok(rx)
    }

    async fn get_event_history(
        &self,
        _filter: crate::platforms::abstraction::interfaces::EventFilter,
    ) -> Result<Vec<PlatformEvent>, PlatformError> {
        Ok(Vec::new())
    }

    async fn health_check(&self) -> Result<HealthStatus, PlatformError> {
        Ok(HealthStatus {
            is_healthy: !self.should_fail,
            last_ping: Some(Utc::now()),
            latency_ms: Some(self.execution_delay_ms),
            error_rate: if self.should_fail { 1.0 } else { 0.0 },
            uptime_seconds: 3600,
            issues: if self.should_fail {
                vec!["Mock platform configured to fail".to_string()]
            } else {
                Vec::new()
            },
        })
    }

    async fn get_diagnostics(&self) -> Result<DiagnosticsInfo, PlatformError> {
        Ok(DiagnosticsInfo {
            connection_status: if self.should_fail {
                "FAILED".to_string()
            } else {
                "CONNECTED".to_string()
            },
            api_limits: HashMap::new(),
            performance_metrics: HashMap::new(),
            last_errors: if self.should_fail {
                vec!["Mock error".to_string()]
            } else {
                Vec::new()
            },
            platform_specific: HashMap::new(),
        })
    }
}
