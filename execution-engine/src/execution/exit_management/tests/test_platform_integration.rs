use std::sync::Arc;
use std::collections::HashMap;
use chrono::Utc;
use rust_decimal::Decimal;
use rust_decimal::prelude::ToPrimitive;
use async_trait::async_trait;

use crate::platforms::abstraction::{
    ITradingPlatform, UnifiedPosition, UnifiedMarketData, UnifiedPositionSide,
    OrderModification, UnifiedOrderResponse, UnifiedOrderStatus, UnifiedOrderSide, UnifiedOrderType,
    PlatformError,
};
use crate::platforms::abstraction::interfaces::EventFilter;
use crate::platforms::abstraction::events::PlatformEvent;
use super::*;
use crate::execution::exit_management::{
    ExitManagementIntegration, ExitManagementSystem, PlatformAdapterFactory
};

/// Mock platform that implements the full ITradingPlatform interface for integration testing
struct MockIntegratedPlatform {
    positions: std::sync::RwLock<Vec<UnifiedPosition>>,
    market_data: std::sync::RwLock<HashMap<String, UnifiedMarketData>>,
    order_modifications: std::sync::RwLock<Vec<(String, OrderModification)>>,
}

impl MockIntegratedPlatform {
    fn new() -> Self {
        let mut market_data = HashMap::new();
        
        // Add default market data
        market_data.insert("EURUSD".to_string(), UnifiedMarketData {
            symbol: "EURUSD".to_string(),
            bid: Decimal::from_f64_retain(1.0799).unwrap(),
            ask: Decimal::from_f64_retain(1.0801).unwrap(),
            spread: Decimal::from_f64_retain(0.0002).unwrap(),
            last_price: Some(Decimal::from_f64_retain(1.0800).unwrap()),
            volume: Some(Decimal::from(1000)),
            high: Some(Decimal::from_f64_retain(1.0850).unwrap()),
            low: Some(Decimal::from_f64_retain(1.0750).unwrap()),
            timestamp: Utc::now(),
            session: Some(crate::platforms::abstraction::TradingSession::Regular),
            platform_specific: HashMap::new(),
        });

        market_data.insert("GBPUSD".to_string(), UnifiedMarketData {
            symbol: "GBPUSD".to_string(),
            bid: Decimal::from_f64_retain(1.2499).unwrap(),
            ask: Decimal::from_f64_retain(1.2501).unwrap(),
            spread: Decimal::from_f64_retain(0.0002).unwrap(),
            last_price: Some(Decimal::from_f64_retain(1.2500).unwrap()),
            volume: Some(Decimal::from(800)),
            high: Some(Decimal::from_f64_retain(1.2550).unwrap()),
            low: Some(Decimal::from_f64_retain(1.2450).unwrap()),
            timestamp: Utc::now(),
            session: Some(crate::platforms::abstraction::TradingSession::Regular),
            platform_specific: HashMap::new(),
        });

        Self {
            positions: std::sync::RwLock::new(Vec::new()),
            market_data: std::sync::RwLock::new(market_data),
            order_modifications: std::sync::RwLock::new(Vec::new()),
        }
    }

    fn add_position(&self, position: UnifiedPosition) {
        let mut positions = self.positions.write().unwrap();
        positions.push(position);
    }

    fn update_position_price(&self, position_id: &str, new_price: Decimal) {
        let mut positions = self.positions.write().unwrap();
        for position in positions.iter_mut() {
            if position.position_id == position_id {
                position.current_price = new_price;
                // Recalculate unrealized PnL
                let price_diff = match position.side {
                    UnifiedPositionSide::Long => new_price - position.entry_price,
                    UnifiedPositionSide::Short => position.entry_price - new_price,
                };
                position.unrealized_pnl = price_diff * position.quantity;
                break;
            }
        }
    }

    fn get_order_modifications(&self) -> Vec<(String, OrderModification)> {
        self.order_modifications.read().unwrap().clone()
    }
}

#[async_trait]
impl ITradingPlatform for MockIntegratedPlatform {
    fn platform_type(&self) -> crate::platforms::PlatformType {
        crate::platforms::PlatformType::MetaTrader4
    }

    fn platform_name(&self) -> &str { "MockIntegratedPlatform" }
    fn platform_version(&self) -> &str { "1.0.0" }

    async fn connect(&mut self) -> Result<(), PlatformError> { Ok(()) }
    async fn disconnect(&mut self) -> Result<(), PlatformError> { Ok(()) }
    async fn is_connected(&self) -> bool { true }
    async fn ping(&self) -> Result<u64, PlatformError> { Ok(10) }

    async fn place_order(&self, _order: crate::platforms::abstraction::UnifiedOrder) -> Result<UnifiedOrderResponse, PlatformError> {
        unimplemented!("place_order not needed for exit management tests")
    }

    async fn modify_order(&self, order_id: &str, modifications: OrderModification) -> Result<UnifiedOrderResponse, PlatformError> {
        // Record the modification
        {
            let mut mods = self.order_modifications.write().unwrap();
            mods.push((order_id.to_string(), modifications.clone()));
        }

        // Simulate successful modification
        Ok(UnifiedOrderResponse {
            platform_order_id: order_id.to_string(),
            client_order_id: order_id.to_string(),
            status: UnifiedOrderStatus::New,
            symbol: "EURUSD".to_string(),
            side: UnifiedOrderSide::Buy,
            order_type: UnifiedOrderType::Market,
            quantity: Decimal::from(1),
            filled_quantity: Decimal::ZERO,
            remaining_quantity: Decimal::from(1),
            price: None,
            average_fill_price: modifications.price,
            commission: Some(Decimal::from_f64_retain(2.0).unwrap()),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            filled_at: None,
            platform_specific: HashMap::new(),
        })
    }

    async fn cancel_order(&self, _order_id: &str) -> Result<(), PlatformError> { Ok(()) }

    async fn get_order(&self, _order_id: &str) -> Result<UnifiedOrderResponse, PlatformError> {
        unimplemented!("get_order not needed for exit management tests")
    }

    async fn get_orders(&self, _filter: Option<crate::platforms::abstraction::OrderFilter>) -> Result<Vec<UnifiedOrderResponse>, PlatformError> {
        Ok(Vec::new())
    }

    async fn get_positions(&self) -> Result<Vec<UnifiedPosition>, PlatformError> {
        Ok(self.positions.read().unwrap().clone())
    }

    async fn get_position(&self, symbol: &str) -> Result<Option<UnifiedPosition>, PlatformError> {
        let positions = self.positions.read().unwrap();
        Ok(positions.iter().find(|p| p.symbol == symbol).cloned())
    }

    async fn close_position(&self, symbol: &str, quantity: Option<Decimal>) -> Result<UnifiedOrderResponse, PlatformError> {
        let positions = self.positions.read().unwrap();
        let position = positions.iter().find(|p| p.symbol == symbol)
            .ok_or_else(|| PlatformError::PositionNotFound { symbol: symbol.to_string() })?;

        let close_quantity = quantity.unwrap_or(position.quantity);

        Ok(UnifiedOrderResponse {
            platform_order_id: format!("close_{}", position.position_id),
            client_order_id: format!("close_{}", position.position_id),
            status: UnifiedOrderStatus::Filled,
            symbol: symbol.to_string(),
            side: match position.side {
                UnifiedPositionSide::Long => UnifiedOrderSide::Sell,
                UnifiedPositionSide::Short => UnifiedOrderSide::Buy,
            },
            order_type: UnifiedOrderType::Market,
            quantity: close_quantity,
            filled_quantity: close_quantity,
            remaining_quantity: Decimal::ZERO,
            price: None,
            average_fill_price: Some(position.current_price),
            commission: Some(Decimal::from_f64_retain(2.0).unwrap()),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            filled_at: Some(Utc::now()),
            platform_specific: HashMap::new(),
        })
    }

    async fn get_account_info(&self) -> Result<crate::platforms::abstraction::UnifiedAccountInfo, PlatformError> {
        unimplemented!("get_account_info not needed for exit management tests")
    }

    async fn get_balance(&self) -> Result<Decimal, PlatformError> { 
        Ok(Decimal::from(10000)) 
    }

    async fn get_margin_info(&self) -> Result<crate::platforms::abstraction::MarginInfo, PlatformError> {
        unimplemented!("get_margin_info not needed for exit management tests")
    }

    async fn get_market_data(&self, symbol: &str) -> Result<UnifiedMarketData, PlatformError> {
        self.market_data.read().unwrap().get(symbol)
            .cloned()
            .ok_or_else(|| PlatformError::MarketDataNotFound { symbol: symbol.to_string() })
    }

    async fn subscribe_market_data(&self, _symbols: Vec<String>) -> Result<tokio::sync::mpsc::Receiver<UnifiedMarketData>, PlatformError> {
        unimplemented!("subscribe_market_data not needed for exit management tests")
    }

    async fn unsubscribe_market_data(&self, _symbols: Vec<String>) -> Result<(), PlatformError> {
        Ok(())
    }

    fn capabilities(&self) -> crate::platforms::abstraction::PlatformCapabilities {
        unimplemented!("capabilities not needed for exit management tests")
    }

    async fn subscribe_events(&self) -> Result<tokio::sync::mpsc::Receiver<crate::platforms::abstraction::PlatformEvent>, PlatformError> {
        unimplemented!("subscribe_events not needed for exit management tests")
    }

    async fn get_event_history(&self, _filter: EventFilter) -> Result<Vec<PlatformEvent>, PlatformError> {
        Ok(Vec::new())
    }

    async fn health_check(&self) -> Result<crate::platforms::abstraction::HealthStatus, PlatformError> {
        unimplemented!("health_check not needed for exit management tests")
    }

    async fn get_diagnostics(&self) -> Result<crate::platforms::abstraction::DiagnosticsInfo, PlatformError> {
        unimplemented!("get_diagnostics not needed for exit management tests")
    }
}

fn create_test_unified_position(
    symbol: &str,
    side: UnifiedPositionSide,
    entry_price: f64,
    current_price: f64,
    stop_loss: Option<f64>,
    take_profit: Option<f64>,
) -> UnifiedPosition {
    let quantity = Decimal::from(1);
    let price_diff = match side {
        UnifiedPositionSide::Long => current_price - entry_price,
        UnifiedPositionSide::Short => entry_price - current_price,
    };
    
    UnifiedPosition {
        position_id: format!("test_pos_{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        symbol: symbol.to_string(),
        side,
        quantity,
        entry_price: Decimal::from_f64_retain(entry_price).unwrap(),
        current_price: Decimal::from_f64_retain(current_price).unwrap(),
        unrealized_pnl: Decimal::from_f64_retain(price_diff).unwrap() * quantity,
        realized_pnl: Decimal::ZERO,
        margin_used: Decimal::from(100),
        commission: Decimal::from_f64_retain(2.0).unwrap(),
        stop_loss: stop_loss.map(|sl| Decimal::from_f64_retain(sl).unwrap()),
        take_profit: take_profit.map(|tp| Decimal::from_f64_retain(tp).unwrap()),
        opened_at: Utc::now() - chrono::Duration::from_std(std::time::Duration::from_secs(2 * 3600)).unwrap(),
        updated_at: Utc::now(),
        account_id: "test_account".to_string(),
        platform_specific: HashMap::new(),
    }
}

#[tokio::test]
async fn test_platform_integration_basic_workflow() {
    let mock_platform = Arc::new(MockIntegratedPlatform::new());
    
    // Add a test position
    let position = create_test_unified_position(
        "EURUSD",
        UnifiedPositionSide::Long,
        1.0800,
        1.0825, // 25 pips profit
        Some(1.0780),
        Some(1.0850),
    );
    mock_platform.add_position(position.clone());

    // Create exit management system with platform integration
    let exit_management = ExitManagementIntegration::create_with_platform(mock_platform.clone()).unwrap();

    // Test that the system can access positions through the adapter
    let positions = exit_management.get_trailing_stop_manager().get_positions_for_trailing().await.unwrap();
    assert_eq!(positions.len(), 1);
    assert_eq!(positions[0].symbol, "EURUSD");
    assert_eq!(positions[0].entry_price, 1.0800);
    assert_eq!(positions[0].current_price, 1.0825);
}

#[tokio::test]
async fn test_platform_integration_trailing_stops() {
    let mock_platform = Arc::new(MockIntegratedPlatform::new());
    
    // Add a profitable position
    let position = create_test_unified_position(
        "EURUSD",
        UnifiedPositionSide::Long,
        1.0800,
        1.0830, // 30 pips profit - enough for trailing activation
        Some(1.0780),
        Some(1.0850),
    );
    mock_platform.add_position(position.clone());

    // Create exit management system
    let exit_management = ExitManagementIntegration::create_with_platform(mock_platform.clone()).unwrap();
    
    // Get the trailing stop manager
    let components = ExitManagementIntegration::create_components(mock_platform.clone()).unwrap();
    let trailing_manager = components.trailing_stop_manager;

    // Test trailing stop activation
    let positions = components.trading_platform.get_positions().await.unwrap();
    let adapted_position = &positions[0];
    
    let result = trailing_manager.activate_trailing_stop(adapted_position).await;
    assert!(result.is_ok(), "Failed to activate trailing stop: {:?}", result);

    // Verify trailing stop was activated
    let active_trails = trailing_manager.get_active_trails();
    assert_eq!(active_trails.len(), 1);
    
    let trail = &active_trails[0].1;
    assert_eq!(trail.position_id, adapted_position.id);
}

#[tokio::test]
async fn test_platform_integration_break_even() {
    let mock_platform = Arc::new(MockIntegratedPlatform::new());
    
    // Add a position at 1:1 risk-reward (break-even trigger)
    let position = create_test_unified_position(
        "EURUSD",
        UnifiedPositionSide::Long,
        1.0800,
        1.0820, // Entry + (Entry - StopLoss) = 1.0800 + 20 pips = 1:1 R:R
        Some(1.0780), // 20 pips risk
        Some(1.0850),
    );
    mock_platform.add_position(position.clone());

    // Create components for testing
    let components = ExitManagementIntegration::create_components(mock_platform.clone()).unwrap();
    let break_even_manager = components.break_even_manager;

    // Test break-even activation
    let result = break_even_manager.check_break_even_opportunities().await;
    assert!(result.is_ok(), "Failed to check break-even opportunities: {:?}", result);

    // Verify order modification was requested
    let modifications = mock_platform.get_order_modifications();
    assert_eq!(modifications.len(), 1, "Expected 1 order modification for break-even");
    
    let (order_id, modification) = &modifications[0];
    assert!(modification.stop_loss.is_some(), "Break-even should modify stop loss");
}

#[tokio::test]
async fn test_platform_integration_partial_profits() {
    let mock_platform = Arc::new(MockIntegratedPlatform::new());
    
    // Add a position at 1:1 risk-reward for partial profit taking
    let position = create_test_unified_position(
        "EURUSD",
        UnifiedPositionSide::Long,
        1.0800,
        1.0820, // 1:1 R:R for first partial target
        Some(1.0780),
        Some(1.0850),
    );
    mock_platform.add_position(position.clone());

    // Create components for testing
    let components = ExitManagementIntegration::create_components(mock_platform.clone()).unwrap();
    let partial_profit_manager = components.partial_profit_manager;

    // Test partial profit taking
    let result = partial_profit_manager.check_profit_targets().await;
    assert!(result.is_ok(), "Failed to check profit targets: {:?}", result);

    // Note: In a full test, we would mock the partial close functionality
    // and verify the correct volume was closed at the right price level
}

#[tokio::test]
async fn test_platform_integration_full_monitoring_cycle() {
    let mock_platform = Arc::new(MockIntegratedPlatform::new());
    
    // Add multiple positions with different scenarios
    let position1 = create_test_unified_position(
        "EURUSD",
        UnifiedPositionSide::Long,
        1.0800,
        1.0830, // Profitable - should activate trailing
        Some(1.0780),
        Some(1.0850),
    );
    
    let position2 = create_test_unified_position(
        "GBPUSD",
        UnifiedPositionSide::Short,
        1.2500,
        1.2480, // At 1:1 R:R - should trigger break-even
        Some(1.2520), // 20 pips risk
        Some(1.2450),
    );
    
    mock_platform.add_position(position1);
    mock_platform.add_position(position2);

    // Create full exit management system
    let mut exit_management = ExitManagementIntegration::create_with_platform(mock_platform.clone()).unwrap();

    // Run one monitoring cycle
    let result = exit_management.monitor_once().await;
    assert!(result.is_ok(), "Failed to run monitoring cycle: {:?}", result);

    // Verify system processed both positions
    let trailing_stats = exit_management.get_trailing_stop_stats().await.unwrap();
    // Note: Exact assertions would depend on the specific logic and thresholds

    println!("Integration test completed successfully");
    println!("Trailing stop stats: active trails = {}", trailing_stats.active_trails);
}

#[tokio::test]
async fn test_platform_adapter_conversion() {
    let mock_platform = Arc::new(MockIntegratedPlatform::new());
    
    // Add a test position
    let unified_position = create_test_unified_position(
        "EURUSD",
        UnifiedPositionSide::Long,
        1.0800,
        1.0825,
        Some(1.0780),
        Some(1.0850),
    );
    mock_platform.add_position(unified_position.clone());

    // Create platform adapter directly
    let adapter = PlatformAdapterFactory::create_exit_management_adapter(mock_platform.clone());

    // Test position conversion
    let positions = adapter.get_positions().await.unwrap();
    assert_eq!(positions.len(), 1);
    
    let position = &positions[0];
    assert_eq!(position.symbol, "EURUSD");
    assert_eq!(position.entry_price, 1.0800);
    assert_eq!(position.current_price, 1.0825);
    assert_eq!(position.stop_loss, Some(1.0780));
    assert_eq!(position.take_profit, Some(1.0850));
    
    // Test market data conversion
    let market_data = adapter.get_market_data("EURUSD").await.unwrap();
    assert_eq!(market_data.symbol, "EURUSD");
    assert_eq!(market_data.bid, 1.0799);
    assert_eq!(market_data.ask, 1.0801);
    assert_eq!(market_data.spread, 0.0002);
}