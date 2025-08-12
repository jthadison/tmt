use std::sync::Arc;
use anyhow::{Result, Context};
use async_trait::async_trait;
use rust_decimal::Decimal;
use rust_decimal::prelude::ToPrimitive;
use uuid::Uuid;

use crate::platforms::abstraction::{ITradingPlatform, UnifiedPosition, UnifiedMarketData, OrderModification, UnifiedOrderResponse, PlatformError};
use crate::platforms::abstraction::interfaces::EventFilter;
use crate::platforms::abstraction::events::PlatformEvent;
use super::TradingPlatform;
use super::types::*;

/// Platform adapter that bridges the exit management system with the actual platform abstraction
pub struct ExitManagementPlatformAdapter {
    platform: Arc<dyn ITradingPlatform + Send + Sync>,
}

impl std::fmt::Debug for ExitManagementPlatformAdapter {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ExitManagementPlatformAdapter")
            .field("platform_name", &self.platform.platform_name())
            .field("platform_version", &self.platform.platform_version())
            .finish()
    }
}

impl ExitManagementPlatformAdapter {
    pub fn new(platform: Arc<dyn ITradingPlatform + Send + Sync>) -> Self {
        Self { platform }
    }

    /// Convert UnifiedPosition to our exit management Position
    fn convert_position(&self, unified_pos: &UnifiedPosition) -> Position {
        Position {
            id: Uuid::parse_str(&unified_pos.position_id).unwrap_or_else(|_| Uuid::new_v4()),
            order_id: unified_pos.position_id.clone(), // Using position_id as order_id for now
            symbol: unified_pos.symbol.clone(),
            position_type: unified_pos.side.clone(), // UnifiedPositionSide is already compatible
            volume: unified_pos.quantity,
            entry_price: unified_pos.entry_price.to_f64().unwrap_or(0.0),
            current_price: unified_pos.current_price.to_f64().unwrap_or(0.0),
            stop_loss: unified_pos.stop_loss.map(|sl| sl.to_f64().unwrap_or(0.0)),
            take_profit: unified_pos.take_profit.map(|tp| tp.to_f64().unwrap_or(0.0)),
            unrealized_pnl: unified_pos.unrealized_pnl.to_f64().unwrap_or(0.0),
            swap: 0.0, // Not available in UnifiedPosition
            commission: unified_pos.commission.to_f64().unwrap_or(0.0),
            open_time: unified_pos.opened_at,
            magic_number: None, // Not available in UnifiedPosition
            comment: None, // Not available in UnifiedPosition
        }
    }

    /// Convert UnifiedMarketData to our exit management MarketData
    fn convert_market_data(&self, unified_data: &UnifiedMarketData) -> MarketData {
        MarketData {
            symbol: unified_data.symbol.clone(),
            bid: unified_data.bid.to_f64().unwrap_or(0.0),
            ask: unified_data.ask.to_f64().unwrap_or(0.0),
            spread: unified_data.spread.to_f64().unwrap_or(0.0),
            timestamp: unified_data.timestamp,
        }
    }
}

#[async_trait]
impl TradingPlatform for ExitManagementPlatformAdapter {
    async fn get_positions(&self) -> Result<Vec<Position>> {
        let unified_positions = self.platform.get_positions().await
            .map_err(|e| anyhow::anyhow!("Platform error getting positions: {:?}", e))?;
        
        let positions = unified_positions
            .iter()
            .map(|pos| self.convert_position(pos))
            .collect();
        
        Ok(positions)
    }

    async fn get_market_data(&self, symbol: &str) -> Result<MarketData> {
        let unified_data = self.platform.get_market_data(symbol).await
            .map_err(|e| anyhow::anyhow!("Platform error getting market data: {:?}", e))?;
        
        Ok(self.convert_market_data(&unified_data))
    }

    async fn modify_order(&self, request: OrderModifyRequest) -> Result<OrderModifyResult> {
        let modification = OrderModification {
            quantity: None, // Not modifying quantity for exit management
            price: None, // Not modifying price for exit management
            stop_price: None, // Not using stop_price
            take_profit: request.new_take_profit.map(Decimal::from_f64_retain).flatten(),
            stop_loss: request.new_stop_loss.map(Decimal::from_f64_retain).flatten(),
            time_in_force: None, // Not modifying time in force
        };

        let response = self.platform.modify_order(&request.order_id, modification).await
            .map_err(|e| anyhow::anyhow!("Platform error modifying order: {:?}", e))?;

        Ok(OrderModifyResult {
            order_id: response.platform_order_id,
            success: matches!(response.status, crate::platforms::abstraction::UnifiedOrderStatus::New | 
                                              crate::platforms::abstraction::UnifiedOrderStatus::PartiallyFilled |
                                              crate::platforms::abstraction::UnifiedOrderStatus::Filled),
            message: format!("Order modified: {:?}", response.status),
        })
    }

    async fn close_position(&self, request: ClosePositionRequest) -> Result<ClosePositionResult> {
        // Find the position to get its symbol
        let positions = self.get_positions().await?;
        let position = positions.iter().find(|p| p.id == request.position_id)
            .ok_or_else(|| anyhow::anyhow!("Position not found: {}", request.position_id))?;

        let response = self.platform.close_position(&position.symbol, None).await
            .map_err(|e| anyhow::anyhow!("Platform error closing position: {:?}", e))?;

        Ok(ClosePositionResult {
            position_id: request.position_id,
            close_price: response.average_fill_price.unwrap_or_default().to_f64().unwrap_or(0.0),
            realized_pnl: Some(Decimal::ZERO), // Would need to calculate this
            close_time: chrono::Utc::now(),
        })
    }

    async fn close_position_partial(&self, request: PartialCloseRequest) -> Result<ClosePositionResult> {
        // Find the position to get its symbol
        let positions = self.get_positions().await?;
        let position = positions.iter().find(|p| p.id == request.position_id)
            .ok_or_else(|| anyhow::anyhow!("Position not found: {}", request.position_id))?;

        let response = self.platform.close_position(&position.symbol, Some(request.volume)).await
            .map_err(|e| anyhow::anyhow!("Platform error partially closing position: {:?}", e))?;

        Ok(ClosePositionResult {
            position_id: request.position_id,
            close_price: response.average_fill_price.unwrap_or_default().to_f64().unwrap_or(0.0),
            realized_pnl: Some(Decimal::ZERO), // Would need to calculate this
            close_time: chrono::Utc::now(),
        })
    }
}

/// Factory for creating platform adapters
pub struct PlatformAdapterFactory;

impl PlatformAdapterFactory {
    pub fn create_exit_management_adapter(
        platform: Arc<dyn ITradingPlatform + Send + Sync>
    ) -> Arc<dyn TradingPlatform> {
        Arc::new(ExitManagementPlatformAdapter::new(platform))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::platforms::abstraction::{UnifiedPositionSide, UnifiedMarketData};
    use chrono::Utc;
    use rust_decimal::Decimal;
    use std::collections::HashMap;

    struct MockPlatform;

    #[async_trait]
    impl ITradingPlatform for MockPlatform {
        fn platform_type(&self) -> crate::platforms::PlatformType {
            crate::platforms::PlatformType::MetaTrader4
        }

        fn platform_name(&self) -> &str { "MockPlatform" }
        fn platform_version(&self) -> &str { "1.0.0" }

        async fn connect(&mut self) -> Result<(), PlatformError> { Ok(()) }
        async fn disconnect(&mut self) -> Result<(), PlatformError> { Ok(()) }
        async fn is_connected(&self) -> bool { true }
        async fn ping(&self) -> Result<u64, PlatformError> { Ok(10) }

        async fn place_order(&self, _order: crate::platforms::abstraction::UnifiedOrder) -> Result<UnifiedOrderResponse, PlatformError> {
            unimplemented!()
        }

        async fn modify_order(&self, order_id: &str, _modifications: OrderModification) -> Result<UnifiedOrderResponse, PlatformError> {
            Ok(UnifiedOrderResponse {
                platform_order_id: order_id.to_string(),
                client_order_id: order_id.to_string(),
                status: crate::platforms::abstraction::UnifiedOrderStatus::New,
                symbol: "EURUSD".to_string(),
                side: crate::platforms::abstraction::UnifiedOrderSide::Buy,
                order_type: crate::platforms::abstraction::UnifiedOrderType::Market,
                quantity: Decimal::from(1),
                filled_quantity: Decimal::ZERO,
                remaining_quantity: Decimal::from(1),
                price: None,
                average_fill_price: Some(Decimal::from_f64_retain(1.1000).unwrap()),
                commission: Some(Decimal::ZERO),
                created_at: Utc::now(),
                updated_at: Utc::now(),
                filled_at: None,
                platform_specific: HashMap::new(),
            })
        }

        async fn cancel_order(&self, _order_id: &str) -> Result<(), PlatformError> { Ok(()) }

        async fn get_order(&self, _order_id: &str) -> Result<UnifiedOrderResponse, PlatformError> {
            unimplemented!()
        }

        async fn get_orders(&self, _filter: Option<crate::platforms::abstraction::OrderFilter>) -> Result<Vec<UnifiedOrderResponse>, PlatformError> {
            Ok(Vec::new())
        }

        async fn get_positions(&self) -> Result<Vec<UnifiedPosition>, PlatformError> {
            Ok(vec![UnifiedPosition {
                position_id: "test-position-1".to_string(),
                symbol: "EURUSD".to_string(),
                side: UnifiedPositionSide::Long,
                quantity: Decimal::from(1),
                entry_price: Decimal::from_f64_retain(1.1000).unwrap(),
                current_price: Decimal::from_f64_retain(1.1050).unwrap(),
                unrealized_pnl: Decimal::from_f64_retain(50.0).unwrap(),
                realized_pnl: Decimal::ZERO,
                margin_used: Decimal::from(100),
                commission: Decimal::from_f64_retain(2.0).unwrap(),
                stop_loss: Some(Decimal::from_f64_retain(1.0950).unwrap()),
                take_profit: Some(Decimal::from_f64_retain(1.1100).unwrap()),
                opened_at: Utc::now(),
                updated_at: Utc::now(),
                account_id: "test-account".to_string(),
                platform_specific: HashMap::new(),
            }])
        }

        async fn get_position(&self, _symbol: &str) -> Result<Option<UnifiedPosition>, PlatformError> {
            Ok(None)
        }

        async fn close_position(&self, _symbol: &str, _quantity: Option<Decimal>) -> Result<UnifiedOrderResponse, PlatformError> {
            Ok(UnifiedOrderResponse {
                platform_order_id: "close-order-1".to_string(),
                client_order_id: "close-order-1".to_string(),
                status: crate::platforms::abstraction::UnifiedOrderStatus::Filled,
                symbol: "EURUSD".to_string(),
                side: crate::platforms::abstraction::UnifiedOrderSide::Sell,
                order_type: crate::platforms::abstraction::UnifiedOrderType::Market,
                quantity: Decimal::from(1),
                filled_quantity: Decimal::from(1),
                remaining_quantity: Decimal::ZERO,
                price: None,
                average_fill_price: Some(Decimal::from_f64_retain(1.1050).unwrap()),
                commission: Some(Decimal::from_f64_retain(2.0).unwrap()),
                created_at: Utc::now(),
                updated_at: Utc::now(),
                filled_at: Some(Utc::now()),
                platform_specific: HashMap::new(),
            })
        }

        async fn get_account_info(&self) -> Result<crate::platforms::abstraction::UnifiedAccountInfo, PlatformError> {
            unimplemented!()
        }

        async fn get_balance(&self) -> Result<Decimal, PlatformError> { Ok(Decimal::from(10000)) }

        async fn get_margin_info(&self) -> Result<crate::platforms::abstraction::MarginInfo, PlatformError> {
            unimplemented!()
        }

        async fn get_market_data(&self, symbol: &str) -> Result<UnifiedMarketData, PlatformError> {
            Ok(UnifiedMarketData {
                symbol: symbol.to_string(),
                bid: Decimal::from_f64_retain(1.1049).unwrap(),
                ask: Decimal::from_f64_retain(1.1051).unwrap(),
                spread: Decimal::from_f64_retain(0.0002).unwrap(),
                last_price: Some(Decimal::from_f64_retain(1.1050).unwrap()),
                volume: Some(Decimal::from(1000)),
                high: Some(Decimal::from_f64_retain(1.1080).unwrap()),
                low: Some(Decimal::from_f64_retain(1.1020).unwrap()),
                timestamp: Utc::now(),
                session: Some(crate::platforms::abstraction::TradingSession::Regular),
                platform_specific: HashMap::new(),
            })
        }

        async fn subscribe_market_data(&self, _symbols: Vec<String>) -> Result<tokio::sync::mpsc::Receiver<UnifiedMarketData>, PlatformError> {
            unimplemented!()
        }

        async fn unsubscribe_market_data(&self, _symbols: Vec<String>) -> Result<(), PlatformError> {
            Ok(())
        }

        fn capabilities(&self) -> crate::platforms::abstraction::PlatformCapabilities {
            unimplemented!()
        }

        async fn subscribe_events(&self) -> Result<tokio::sync::mpsc::Receiver<crate::platforms::abstraction::PlatformEvent>, PlatformError> {
            unimplemented!()
        }

        async fn get_event_history(&self, _filter: EventFilter) -> Result<Vec<PlatformEvent>, PlatformError> {
            Ok(Vec::new())
        }

        async fn health_check(&self) -> Result<crate::platforms::abstraction::HealthStatus, PlatformError> {
            unimplemented!()
        }

        async fn get_diagnostics(&self) -> Result<crate::platforms::abstraction::DiagnosticsInfo, PlatformError> {
            unimplemented!()
        }
    }

    #[tokio::test]
    async fn test_platform_adapter_get_positions() {
        let mock_platform = Arc::new(MockPlatform);
        let adapter = ExitManagementPlatformAdapter::new(mock_platform);

        let positions = adapter.get_positions().await.unwrap();
        assert_eq!(positions.len(), 1);
        assert_eq!(positions[0].symbol, "EURUSD");
        assert_eq!(positions[0].entry_price, 1.1000);
        assert_eq!(positions[0].current_price, 1.1050);
    }

    #[tokio::test]
    async fn test_platform_adapter_get_market_data() {
        let mock_platform = Arc::new(MockPlatform);
        let adapter = ExitManagementPlatformAdapter::new(mock_platform);

        let market_data = adapter.get_market_data("EURUSD").await.unwrap();
        assert_eq!(market_data.symbol, "EURUSD");
        assert_eq!(market_data.bid, 1.1049);
        assert_eq!(market_data.ask, 1.1051);
        assert_eq!(market_data.spread, 0.0002);
    }

    #[tokio::test]
    async fn test_platform_adapter_modify_order() {
        let mock_platform = Arc::new(MockPlatform);
        let adapter = ExitManagementPlatformAdapter::new(mock_platform);

        let request = OrderModifyRequest {
            order_id: "test-order".to_string(),
            new_stop_loss: Some(1.0950),
            new_take_profit: Some(1.1100),
        };

        let result = adapter.modify_order(request).await.unwrap();
        assert!(result.success);
        assert_eq!(result.order_id, "test-order");
    }
}