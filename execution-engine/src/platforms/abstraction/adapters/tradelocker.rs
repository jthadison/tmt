use async_trait::async_trait;
use tokio::sync::mpsc;
use std::collections::HashMap;

use crate::platforms::{PlatformType, tradelocker::*};
use super::super::interfaces::*;
use super::super::models::*;
use super::super::errors::*;
use super::super::events::*;
use super::super::capabilities::*;
use super::{BaseAdapter, PlatformAdapter, AdapterInfo, PerformanceCharacteristics};
use super::conversion_utils::*;
use super::super::factory::RetryConfig;

/// TradeLocker platform adapter implementing the unified interface
pub struct TradeLockerAdapter {
    client: TradeLockerClient,
    base: BaseAdapter,
    event_sender: Option<mpsc::UnboundedSender<PlatformEvent>>,
    capabilities: PlatformCapabilities,
    account_id: String,
}

impl TradeLockerAdapter {
    pub fn new(client: TradeLockerClient, retry_config: RetryConfig) -> Self {
        let account_id = client.account_id().to_string();
        
        Self {
            client,
            base: BaseAdapter::new(retry_config),
            event_sender: None,
            capabilities: tradelocker_capabilities(),
            account_id,
        }
    }

    async fn emit_event(&self, event_type: EventType, data: EventData) {
        if let Some(sender) = &self.event_sender {
            let event = PlatformEvent::new(
                event_type,
                PlatformType::TradeLocker,
                self.account_id.clone(),
                data,
            );
            let _ = sender.send(event);
        }
    }

    fn convert_order_to_unified(&self, order: OrderResponse) -> UnifiedOrderResponse {
        UnifiedOrderResponse {
            platform_order_id: order.order_id,
            client_order_id: order.client_order_id.unwrap_or_default(),
            status: convert_tl_order_status(order.status),
            symbol: order.symbol,
            side: convert_tl_order_side(order.side),
            order_type: convert_tl_order_type(order.order_type),
            quantity: order.quantity,
            filled_quantity: order.filled_quantity,
            remaining_quantity: order.quantity - order.filled_quantity,
            price: order.price,
            average_fill_price: order.average_price,
            commission: None, // TradeLocker doesn't provide this directly
            created_at: order.created_at,
            updated_at: order.updated_at,
            filled_at: if order.filled_quantity == order.quantity { Some(order.updated_at) } else { None },
            platform_specific: HashMap::new(),
        }
    }

    fn convert_position_to_unified(&self, position: Position) -> UnifiedPosition {
        UnifiedPosition {
            position_id: position.position_id,
            symbol: position.symbol,
            side: convert_tl_position_side(position.side),
            quantity: position.quantity,
            entry_price: position.entry_price,
            current_price: position.current_price,
            unrealized_pnl: position.unrealized_pnl,
            realized_pnl: position.realized_pnl,
            margin_used: position.margin_used,
            commission: rust_decimal::Decimal::ZERO, // Not provided directly
            stop_loss: position.stop_loss,
            take_profit: position.take_profit,
            opened_at: position.opened_at,
            updated_at: chrono::Utc::now(),
            account_id: self.account_id.clone(),
            platform_specific: HashMap::new(),
        }
    }

    fn convert_account_to_unified(&self, account: AccountInfo) -> UnifiedAccountInfo {
        UnifiedAccountInfo {
            account_id: account.account_id,
            account_name: None,
            currency: account.currency,
            balance: account.balance,
            equity: account.equity,
            margin_used: account.margin_used,
            margin_available: account.margin_available,
            buying_power: account.margin_available, // Approximate
            unrealized_pnl: account.unrealized_pnl,
            realized_pnl: account.realized_pnl,
            margin_level: account.margin_level,
            account_type: AccountType::Live, // Assume live, could be determined from environment
            last_updated: chrono::Utc::now(),
            platform_specific: HashMap::new(),
        }
    }

    fn convert_market_data_to_unified(&self, data: MarketData) -> UnifiedMarketData {
        UnifiedMarketData {
            symbol: data.symbol,
            bid: data.bid,
            ask: data.ask,
            spread: data.spread,
            last_price: None,
            volume: None,
            high: None,
            low: None,
            timestamp: data.timestamp,
            session: None, // Could be determined from timestamp
            platform_specific: HashMap::new(),
        }
    }

    fn convert_unified_order_request(&self, order: UnifiedOrder) -> Result<OrderRequest, PlatformError> {
        let order_type = convert_to_tl_order_type(order.order_type)
            .ok_or_else(|| PlatformError::FeatureNotSupported {
                feature: format!("Order type {:?}", order.order_type)
            })?;

        let time_in_force = convert_to_tl_time_in_force(order.time_in_force)
            .ok_or_else(|| PlatformError::FeatureNotSupported {
                feature: format!("Time in force {:?}", order.time_in_force)
            })?;

        Ok(OrderRequest {
            symbol: order.symbol,
            side: convert_to_tl_order_side(order.side),
            order_type,
            quantity: order.quantity,
            price: order.price,
            stop_price: order.stop_price,
            take_profit: order.take_profit,
            stop_loss: order.stop_loss,
            time_in_force,
            client_order_id: Some(order.client_order_id),
        })
    }
}

#[async_trait]
impl ITradingPlatform for TradeLockerAdapter {
    fn platform_type(&self) -> PlatformType {
        PlatformType::TradeLocker
    }

    fn platform_name(&self) -> &str {
        "TradeLocker"
    }

    fn platform_version(&self) -> &str {
        "1.0.0"
    }

    async fn connect(&mut self) -> std::result::Result<(), PlatformError> {
        self.base.increment_operation_count();
        
        let result = self.base.retry_handler().execute_with_retry(|| async {
            self.client.connect().await.map_err(|e| {
                PlatformError::ConnectionFailed { reason: e.to_string() }
            })
        }).await;

        match result {
            Ok(_) => {
                self.base.set_connected(true);
                self.emit_event(
                    EventType::ConnectionEstablished,
                    EventData::Connection(ConnectionEventData {
                        status: ConnectionStatus::Connected,
                        reason: None,
                        server_info: Some("TradeLocker".to_string()),
                        latency_ms: None,
                    }),
                ).await;
                Ok(())
            }
            Err(e) => {
                self.base.increment_error_count();
                self.base.set_connected(false);
                self.emit_event(
                    EventType::ConnectionLost,
                    EventData::Connection(ConnectionEventData {
                        status: ConnectionStatus::Failed,
                        reason: Some(e.to_string()),
                        server_info: None,
                        latency_ms: None,
                    }),
                ).await;
                Err(e)
            }
        }
    }

    async fn disconnect(&mut self) -> std::result::Result<(), PlatformError> {
        self.base.increment_operation_count();
        
        // TradeLocker client doesn't have explicit disconnect, but we can mark as disconnected
        self.base.set_connected(false);
        
        self.emit_event(
            EventType::ConnectionLost,
            EventData::Connection(ConnectionEventData {
                status: ConnectionStatus::Disconnected,
                reason: Some("Manual disconnect".to_string()),
                server_info: None,
                latency_ms: None,
            }),
        ).await;
        
        Ok(())
    }

    async fn is_connected(&self) -> bool {
        self.base.is_connected()
    }

    async fn ping(&self) -> std::result::Result<u64, PlatformError> {
        self.base.increment_operation_count();
        
        let start = std::time::Instant::now();
        
        // Use account info request as ping
        let result = self.client.get_account().await.map_err(|e| {
            PlatformError::NetworkError { reason: e.to_string() }
        });

        let latency = start.elapsed().as_millis() as u64;

        match result {
            Ok(_) => Ok(latency),
            Err(e) => {
                self.base.increment_error_count();
                Err(e)
            }
        }
    }

    async fn place_order(&self, order: UnifiedOrder) -> std::result::Result<UnifiedOrderResponse, PlatformError> {
        self.base.increment_operation_count();
        
        let tl_order = self.convert_unified_order_request(order)?;
        
        let result = self.base.retry_handler().execute_with_retry(|| async {
            self.client.place_order(tl_order.clone()).await.map_err(|e| {
                PlatformError::OrderRejected { 
                    reason: e.to_string(),
                    platform_code: None,
                }
            })
        }).await;

        match result {
            Ok(response) => {
                let unified_response = self.convert_order_to_unified(response);
                
                self.emit_event(
                    EventType::OrderPlaced,
                    EventData::Order(OrderEventData {
                        order: unified_response.clone(),
                        previous_status: None,
                        fill_price: None,
                        fill_quantity: None,
                        remaining_quantity: Some(unified_response.remaining_quantity),
                        rejection_reason: None,
                    }),
                ).await;
                
                Ok(unified_response)
            }
            Err(e) => {
                self.base.increment_error_count();
                Err(e)
            }
        }
    }

    async fn modify_order(&self, order_id: &str, modifications: OrderModification) -> std::result::Result<UnifiedOrderResponse, PlatformError> {
        self.base.increment_operation_count();
        
        // TradeLocker modify order implementation would go here
        // For now, return not supported
        Err(PlatformError::FeatureNotSupported {
            feature: "Order modification".to_string()
        })
    }

    async fn cancel_order(&self, order_id: &str) -> std::result::Result<(), PlatformError> {
        self.base.increment_operation_count();
        
        let result = self.base.retry_handler().execute_with_retry(|| async {
            self.client.cancel_order(order_id).await.map_err(|e| {
                PlatformError::OrderModificationFailed { reason: e.to_string() }
            })
        }).await;

        match result {
            Ok(_) => {
                self.emit_event(
                    EventType::OrderCancelled,
                    EventData::Order(OrderEventData {
                        order: UnifiedOrderResponse {
                            platform_order_id: order_id.to_string(),
                            client_order_id: String::new(),
                            status: UnifiedOrderStatus::Canceled,
                            symbol: String::new(),
                            side: UnifiedOrderSide::Buy,
                            order_type: UnifiedOrderType::Market,
                            quantity: rust_decimal::Decimal::ZERO,
                            filled_quantity: rust_decimal::Decimal::ZERO,
                            remaining_quantity: rust_decimal::Decimal::ZERO,
                            price: None,
                            average_fill_price: None,
                            commission: None,
                            created_at: chrono::Utc::now(),
                            updated_at: chrono::Utc::now(),
                            filled_at: None,
                            platform_specific: HashMap::new(),
                        },
                        previous_status: Some(UnifiedOrderStatus::New),
                        fill_price: None,
                        fill_quantity: None,
                        remaining_quantity: None,
                        rejection_reason: None,
                    }),
                ).await;
                Ok(())
            }
            Err(e) => {
                self.base.increment_error_count();
                Err(e)
            }
        }
    }

    async fn get_order(&self, order_id: &str) -> std::result::Result<UnifiedOrderResponse, PlatformError> {
        self.base.increment_operation_count();
        
        // TradeLocker get specific order implementation would go here
        Err(PlatformError::FeatureNotSupported {
            feature: "Get specific order".to_string()
        })
    }

    async fn get_orders(&self, _filter: Option<OrderFilter>) -> std::result::Result<Vec<UnifiedOrderResponse>, PlatformError> {
        self.base.increment_operation_count();
        
        let result = self.base.retry_handler().execute_with_retry(|| async {
            self.client.get_orders().await.map_err(|e| {
                PlatformError::InternalError { reason: e.to_string() }
            })
        }).await;

        match result {
            Ok(orders) => {
                let unified_orders = orders.into_iter()
                    .map(|order| self.convert_order_to_unified(order))
                    .collect();
                Ok(unified_orders)
            }
            Err(e) => {
                self.base.increment_error_count();
                Err(e)
            }
        }
    }

    async fn get_positions(&self) -> std::result::Result<Vec<UnifiedPosition>, PlatformError> {
        self.base.increment_operation_count();
        
        let result = self.base.retry_handler().execute_with_retry(|| async {
            self.client.get_positions().await.map_err(|e| {
                PlatformError::InternalError { reason: e.to_string() }
            })
        }).await;

        match result {
            Ok(positions) => {
                let unified_positions = positions.into_iter()
                    .map(|position| self.convert_position_to_unified(position))
                    .collect();
                Ok(unified_positions)
            }
            Err(e) => {
                self.base.increment_error_count();
                Err(e)
            }
        }
    }

    async fn get_position(&self, symbol: &str) -> std::result::Result<Option<UnifiedPosition>, PlatformError> {
        let positions = self.get_positions().await?;
        Ok(positions.into_iter().find(|p| p.symbol == symbol))
    }

    async fn close_position(&self, symbol: &str, quantity: Option<rust_decimal::Decimal>) -> std::result::Result<UnifiedOrderResponse, PlatformError> {
        self.base.increment_operation_count();
        
        // Get current position to determine close parameters
        let position = self.get_position(symbol).await?
            .ok_or_else(|| PlatformError::PositionNotFound { symbol: symbol.to_string() })?;

        let close_quantity = quantity.unwrap_or(position.quantity);
        let close_side = match position.side {
            UnifiedPositionSide::Long => UnifiedOrderSide::Sell,
            UnifiedPositionSide::Short => UnifiedOrderSide::Buy,
        };

        let close_order = UnifiedOrder {
            client_order_id: format!("close_{}", uuid::Uuid::new_v4()),
            symbol: symbol.to_string(),
            side: close_side,
            order_type: UnifiedOrderType::Market,
            quantity: close_quantity,
            price: None,
            stop_price: None,
            take_profit: None,
            stop_loss: None,
            time_in_force: UnifiedTimeInForce::Ioc,
            account_id: Some(self.account_id.clone()),
            metadata: OrderMetadata {
                strategy_id: None,
                signal_id: None,
                risk_parameters: HashMap::new(),
                tags: vec!["position_close".to_string()],
                expires_at: None,
            },
        };

        self.place_order(close_order).await
    }

    async fn get_account_info(&self) -> std::result::Result<UnifiedAccountInfo, PlatformError> {
        self.base.increment_operation_count();
        
        let result = self.base.retry_handler().execute_with_retry(|| async {
            self.client.get_account().await.map_err(|e| {
                PlatformError::InternalError { reason: e.to_string() }
            })
        }).await;

        match result {
            Ok(account) => Ok(self.convert_account_to_unified(account)),
            Err(e) => {
                self.base.increment_error_count();
                Err(e)
            }
        }
    }

    async fn get_balance(&self) -> std::result::Result<rust_decimal::Decimal, PlatformError> {
        let account = self.get_account_info().await?;
        Ok(account.balance)
    }

    async fn get_margin_info(&self) -> std::result::Result<MarginInfo, PlatformError> {
        let account = self.get_account_info().await?;
        Ok(MarginInfo {
            initial_margin: account.margin_used,
            maintenance_margin: account.margin_used,
            margin_call_level: account.margin_level,
            stop_out_level: None,
            margin_requirements: HashMap::new(),
        })
    }

    async fn get_market_data(&self, symbol: &str) -> std::result::Result<UnifiedMarketData, PlatformError> {
        self.base.increment_operation_count();
        
        let result = self.base.retry_handler().execute_with_retry(|| async {
            self.client.get_market_data(symbol).await.map_err(|e| {
                PlatformError::MarketDataUnavailable { reason: e.to_string() }
            })
        }).await;

        match result {
            Ok(data) => Ok(self.convert_market_data_to_unified(data)),
            Err(e) => {
                self.base.increment_error_count();
                Err(e)
            }
        }
    }

    async fn subscribe_market_data(&self, _symbols: Vec<String>) -> std::result::Result<mpsc::Receiver<UnifiedMarketData>, PlatformError> {
        // TradeLocker WebSocket subscription would go here
        Err(PlatformError::FeatureNotSupported {
            feature: "Market data subscription".to_string()
        })
    }

    async fn unsubscribe_market_data(&self, _symbols: Vec<String>) -> std::result::Result<(), PlatformError> {
        Ok(())
    }

    fn capabilities(&self) -> PlatformCapabilities {
        self.capabilities.clone()
    }

    async fn subscribe_events(&self) -> std::result::Result<mpsc::Receiver<PlatformEvent>, PlatformError> {
        let (tx, rx) = mpsc::unbounded_channel();
        // Store the sender for event emission
        // Note: This is simplified - in a real implementation, you'd need interior mutability
        Ok(rx)
    }

    async fn get_event_history(&self, _filter: crate::platforms::abstraction::interfaces::EventFilter) -> std::result::Result<Vec<PlatformEvent>, PlatformError> {
        // Event history retrieval would be implemented here
        Ok(Vec::new())
    }

    async fn health_check(&self) -> std::result::Result<HealthStatus, PlatformError> {
        let is_connected = self.is_connected().await;
        let error_rate = self.base.get_error_rate();
        let uptime = self.base.uptime_seconds();
        
        let ping_result = if is_connected {
            self.ping().await.ok()
        } else {
            None
        };

        Ok(HealthStatus {
            is_healthy: is_connected && error_rate < 0.1,
            last_ping: if ping_result.is_some() { Some(chrono::Utc::now()) } else { None },
            latency_ms: ping_result,
            error_rate,
            uptime_seconds: uptime,
            issues: if !is_connected { 
                vec!["Not connected".to_string()] 
            } else if error_rate >= 0.1 {
                vec!["High error rate".to_string()]
            } else {
                Vec::new()
            },
        })
    }

    async fn get_diagnostics(&self) -> std::result::Result<DiagnosticsInfo, PlatformError> {
        let mut performance_metrics = HashMap::new();
        performance_metrics.insert("operation_count".to_string(), serde_json::Value::Number(self.base.get_operation_count().into()));
        performance_metrics.insert("error_count".to_string(), serde_json::Value::Number(self.base.get_error_count().into()));
        performance_metrics.insert("error_rate".to_string(), serde_json::Value::Number(serde_json::Number::from_f64(self.base.get_error_rate()).unwrap()));
        performance_metrics.insert("uptime_seconds".to_string(), serde_json::Value::Number(self.base.uptime_seconds().into()));

        Ok(DiagnosticsInfo {
            connection_status: if self.is_connected().await { "Connected".to_string() } else { "Disconnected".to_string() },
            api_limits: HashMap::new(),
            performance_metrics,
            last_errors: Vec::new(),
            platform_specific: HashMap::new(),
        })
    }
}

#[async_trait]
impl PlatformAdapter for TradeLockerAdapter {
    async fn initialize(&mut self) -> std::result::Result<(), PlatformError> {
        self.connect().await
    }

    async fn cleanup(&mut self) -> std::result::Result<(), PlatformError> {
        self.disconnect().await
    }

    async fn reset_connection(&mut self) -> std::result::Result<(), PlatformError> {
        self.disconnect().await?;
        tokio::time::sleep(std::time::Duration::from_millis(1000)).await;
        self.connect().await
    }

    fn adapter_info(&self) -> AdapterInfo {
        AdapterInfo {
            name: "TradeLocker Adapter".to_string(),
            version: "1.0.0".to_string(),
            supported_features: vec![
                "Market Orders".to_string(),
                "Limit Orders".to_string(),
                "Stop Orders".to_string(),
                "Position Management".to_string(),
                "Account Information".to_string(),
                "Market Data".to_string(),
            ],
            performance_characteristics: PerformanceCharacteristics {
                typical_latency_ms: 50,
                max_throughput_rps: 10,
                memory_usage_estimate_mb: 10,
                cpu_usage_estimate_percent: 5.0,
            },
        }
    }
}