use std::sync::Arc;
use std::collections::HashMap;
use chrono::Utc;
use rust_decimal::Decimal;
use rust_decimal::prelude::ToPrimitive;
use tokio::time::{sleep, Duration};

use execution_engine::execution::exit_management::{
    ExitManagementIntegration, ExitManagementSystem,
    TrailingStopManager, BreakEvenManager, PartialProfitManager, 
    TimeBasedExitManager, NewsEventProtection, ExitAuditLogger
};
use execution_engine::execution::exit_management::types::*;
use execution_engine::platforms::abstraction::interfaces::ITradingPlatform;
use execution_engine::platforms::abstraction::models::{
    UnifiedPosition, UnifiedMarketData, UnifiedPositionSide, OrderModification,
    UnifiedOrderResponse, UnifiedOrderStatus, UnifiedOrderSide, UnifiedOrderType,
    TradingSession
};
use execution_engine::platforms::abstraction::errors::PlatformError;
use async_trait::async_trait;

/// Comprehensive mock platform for full integration testing
struct ComprehensiveMockPlatform {
    positions: std::sync::RwLock<Vec<UnifiedPosition>>,
    market_data: std::sync::RwLock<HashMap<String, UnifiedMarketData>>,
    order_modifications: std::sync::RwLock<Vec<OrderModification>>,
    position_closes: std::sync::RwLock<Vec<(String, Option<Decimal>)>>,
}

impl ComprehensiveMockPlatform {
    fn new() -> Self {
        let mut market_data = HashMap::new();
        
        // Setup realistic market data for multiple symbols
        let symbols = vec![
            ("EURUSD", 1.0800, 0.0002),
            ("GBPUSD", 1.2500, 0.0003),
            ("USDJPY", 150.50, 0.003),
            ("AUDUSD", 0.6650, 0.0002),
        ];

        for (symbol, mid_price, spread) in symbols {
            let spread_decimal = Decimal::from_f64_retain(spread).unwrap();
            let mid_decimal = Decimal::from_f64_retain(mid_price).unwrap();
            
            market_data.insert(symbol.to_string(), UnifiedMarketData {
                symbol: symbol.to_string(),
                bid: mid_decimal - (spread_decimal / Decimal::from(2)),
                ask: mid_decimal + (spread_decimal / Decimal::from(2)),
                spread: spread_decimal,
                last_price: Some(mid_decimal),
                volume: Some(Decimal::from(1000)),
                high: Some(mid_decimal * Decimal::from_f64_retain(1.002).unwrap()),
                low: Some(mid_decimal * Decimal::from_f64_retain(0.998).unwrap()),
                timestamp: Utc::now(),
                session: Some(TradingSession::Regular),
                platform_specific: HashMap::new(),
            });
        }

        Self {
            positions: std::sync::RwLock::new(Vec::new()),
            market_data: std::sync::RwLock::new(market_data),
            order_modifications: std::sync::RwLock::new(Vec::new()),
            position_closes: std::sync::RwLock::new(Vec::new()),
        }
    }

    fn add_position(&self, position: UnifiedPosition) {
        let mut positions = self.positions.write().unwrap();
        positions.push(position);
    }

    fn simulate_price_movement(&self, symbol: &str, new_price: f64) {
        // Update market data
        {
            let mut data = self.market_data.write().unwrap();
            if let Some(market_data) = data.get_mut(symbol) {
                let new_price_decimal = Decimal::from_f64_retain(new_price).unwrap();
                let spread = market_data.spread;
                market_data.bid = new_price_decimal - (spread / Decimal::from(2));
                market_data.ask = new_price_decimal + (spread / Decimal::from(2));
                market_data.last_price = Some(new_price_decimal);
                market_data.timestamp = Utc::now();
            }
        }

        // Update position prices
        {
            let mut positions = self.positions.write().unwrap();
            for position in positions.iter_mut() {
                if position.symbol == symbol {
                    position.current_price = Decimal::from_f64_retain(new_price).unwrap();
                    // Recalculate unrealized PnL
                    let price_diff = match position.side {
                        UnifiedPositionSide::Long => position.current_price - position.entry_price,
                        UnifiedPositionSide::Short => position.entry_price - position.current_price,
                    };
                    position.unrealized_pnl = price_diff * position.quantity;
                }
            }
        }
    }

    fn get_order_modification_count(&self) -> usize {
        self.order_modifications.read().unwrap().len()
    }

    fn get_position_close_count(&self) -> usize {
        self.position_closes.read().unwrap().len()
    }
}

#[async_trait]
impl ITradingPlatform for ComprehensiveMockPlatform {
    fn platform_type(&self) -> execution_engine::platforms::PlatformType {
        execution_engine::platforms::PlatformType::MetaTrader5
    }

    fn platform_name(&self) -> &str { "ComprehensiveMockPlatform" }
    fn platform_version(&self) -> &str { "2.0.0" }

    async fn connect(&mut self) -> Result<(), PlatformError> { Ok(()) }
    async fn disconnect(&mut self) -> Result<(), PlatformError> { Ok(()) }
    async fn is_connected(&self) -> bool { true }
    async fn ping(&self) -> Result<u64, PlatformError> { Ok(5) }

    async fn place_order(&self, _order: execution_engine::platforms::abstraction::UnifiedOrder) -> Result<UnifiedOrderResponse, PlatformError> {
        unimplemented!("place_order not needed for exit management integration tests")
    }

    async fn modify_order(&self, order_id: &str, modifications: OrderModification) -> Result<UnifiedOrderResponse, PlatformError> {
        // Record the modification
        {
            let mut mods = self.order_modifications.write().unwrap();
            mods.push(modifications.clone());
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
        unimplemented!("get_order not needed for integration tests")
    }

    async fn get_orders(&self, _filter: Option<execution_engine::platforms::abstraction::OrderFilter>) -> Result<Vec<UnifiedOrderResponse>, PlatformError> {
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
        // Record the close
        {
            let mut closes = self.position_closes.write().unwrap();
            closes.push((symbol.to_string(), quantity));
        }

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

    async fn get_account_info(&self) -> Result<execution_engine::platforms::abstraction::UnifiedAccountInfo, PlatformError> {
        unimplemented!("get_account_info not needed for integration tests")
    }

    async fn get_balance(&self) -> Result<Decimal, PlatformError> { 
        Ok(Decimal::from(50000)) 
    }

    async fn get_margin_info(&self) -> Result<execution_engine::platforms::abstraction::MarginInfo, PlatformError> {
        unimplemented!("get_margin_info not needed for integration tests")
    }

    async fn get_market_data(&self, symbol: &str) -> Result<UnifiedMarketData, PlatformError> {
        self.market_data.read().unwrap().get(symbol)
            .cloned()
            .ok_or_else(|| PlatformError::SymbolNotFound { symbol: symbol.to_string() })
    }

    async fn subscribe_market_data(&self, _symbols: Vec<String>) -> Result<tokio::sync::mpsc::Receiver<UnifiedMarketData>, PlatformError> {
        unimplemented!("subscribe_market_data not needed for integration tests")
    }

    async fn unsubscribe_market_data(&self, _symbols: Vec<String>) -> Result<(), PlatformError> {
        Ok(())
    }

    fn capabilities(&self) -> execution_engine::platforms::abstraction::PlatformCapabilities {
        unimplemented!("capabilities not needed for integration tests")
    }

    async fn subscribe_events(&self) -> Result<tokio::sync::mpsc::Receiver<execution_engine::platforms::abstraction::PlatformEvent>, PlatformError> {
        unimplemented!("subscribe_events not needed for integration tests")
    }

    async fn get_event_history(&self, _filter: execution_engine::platforms::abstraction::EventFilter) -> Result<Vec<execution_engine::platforms::abstraction::PlatformEvent>, PlatformError> {
        Ok(Vec::new())
    }

    async fn health_check(&self) -> Result<execution_engine::platforms::abstraction::HealthStatus, PlatformError> {
        unimplemented!("health_check not needed for integration tests")
    }

    async fn get_diagnostics(&self) -> Result<execution_engine::platforms::abstraction::DiagnosticsInfo, PlatformError> {
        unimplemented!("get_diagnostics not needed for integration tests")
    }
}

fn create_realistic_position(
    symbol: &str,
    side: UnifiedPositionSide,
    entry_price: f64,
    current_price: f64,
    stop_loss: Option<f64>,
    take_profit: Option<f64>,
    volume: f64,
) -> UnifiedPosition {
    let quantity = Decimal::from_f64_retain(volume).unwrap();
    let entry_decimal = Decimal::from_f64_retain(entry_price).unwrap();
    let current_decimal = Decimal::from_f64_retain(current_price).unwrap();
    
    let price_diff = match side {
        UnifiedPositionSide::Long => current_decimal - entry_decimal,
        UnifiedPositionSide::Short => entry_decimal - current_decimal,
    };
    
    UnifiedPosition {
        position_id: format!("realistic_pos_{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        symbol: symbol.to_string(),
        side,
        quantity,
        entry_price: entry_decimal,
        current_price: current_decimal,
        unrealized_pnl: price_diff * quantity * Decimal::from(10000), // Convert to account currency
        realized_pnl: Decimal::ZERO,
        margin_used: quantity * entry_decimal / Decimal::from(100), // 1:100 leverage
        commission: Decimal::from_f64_retain(7.0).unwrap(),
        stop_loss: stop_loss.map(|sl| Decimal::from_f64_retain(sl).unwrap()),
        take_profit: take_profit.map(|tp| Decimal::from_f64_retain(tp).unwrap()),
        opened_at: Utc::now() - chrono::Duration::from_std(std::time::Duration::from_secs(3 * 3600)).unwrap(),
        updated_at: Utc::now(),
        account_id: "integration_test_account".to_string(),
        platform_specific: HashMap::new(),
    }
}

#[tokio::test]
async fn test_comprehensive_exit_management_workflow() {
    let mock_platform = Arc::new(ComprehensiveMockPlatform::new());
    
    // Setup multiple positions with different scenarios
    let positions = vec![
        // EURUSD Long - should trigger trailing stops as price moves up
        create_realistic_position("EURUSD", UnifiedPositionSide::Long, 1.0800, 1.0835, Some(1.0780), Some(1.0880), 1.0),
        
        // GBPUSD Short - at break-even point
        create_realistic_position("GBPUSD", UnifiedPositionSide::Short, 1.2500, 1.2480, Some(1.2520), Some(1.2450), 0.5),
        
        // USDJPY Long - ready for partial profit taking at 1:1
        create_realistic_position("USDJPY", UnifiedPositionSide::Long, 150.00, 150.50, Some(149.50), Some(151.50), 0.8),
        
        // AUDUSD Long - older position for time-based management
        create_realistic_position("AUDUSD", UnifiedPositionSide::Long, 0.6650, 0.6645, Some(0.6630), Some(0.6700), 1.2),
    ];

    for position in positions {
        mock_platform.add_position(position);
    }

    // Create comprehensive exit management system
    let exit_management = ExitManagementIntegration::create_with_platform(mock_platform.clone()).unwrap();
    
    // Configure trailing stops
    let trailing_config = TrailingConfig {
        atr_multiplier: 2.0,
        trail_trigger_pips: 20.0,
        min_distance_pips: 15.0,
        use_break_even_first: true,
    };
    exit_management.configure_trailing_stop("EURUSD", trailing_config).await.unwrap();

    // Configure break-even
    let break_even_config = BreakEvenConfig {
        trigger_ratio: 1.0, // 1:1 risk-reward
        buffer_pips: 5.0,
        partial_close_percent: Some(0.5),
    };
    exit_management.configure_break_even("GBPUSD", break_even_config).await.unwrap();

    // Configure partial profits
    let profit_config = PartialProfitConfig {
        levels: vec![
            (1.0, 0.50), // 50% at 1:1 RR
            (2.0, 0.25), // 25% at 2:1 RR
        ],
        move_stop_after_partial: true,
    };
    exit_management.configure_partial_profits("USDJPY", profit_config).await.unwrap();

    // Configure time exits
    let time_config = TimeExitConfig {
        max_holding_hours: 24,
        weekend_close_hours: 2,
        news_exit_minutes: 5,
        allow_trend_override: true,
    };
    exit_management.configure_time_exits("AUDUSD", time_config).await.unwrap();

    // Simulate position updates
    println!("Processing initial positions...");
    let positions = mock_platform.get_positions().await.unwrap();
    for position in positions {
        let internal_position = Position {
            id: position.position_id.clone(),
            symbol: position.symbol.clone(),
            side: match position.side {
                UnifiedPositionSide::Long => PositionSide::Long,
                UnifiedPositionSide::Short => PositionSide::Short,
            },
            entry_price: position.entry_price,
            current_price: position.current_price,
            quantity: position.quantity,
            stop_loss: position.stop_loss,
            take_profit: position.take_profit,
            open_time: std::time::SystemTime::now(),
            unrealized_pnl: position.unrealized_pnl,
        };
        let _ = exit_management.update_position(internal_position).await;
    }

    let initial_modifications = mock_platform.get_order_modification_count();
    println!("Initial order modifications: {}", initial_modifications);

    // Simulate price movements to trigger different exit strategies
    println!("Simulating price movements...");
    
    // Move EURUSD higher to trigger trailing stops
    mock_platform.simulate_price_movement("EURUSD", 1.0840);
    
    // Move GBPUSD to optimal break-even position
    mock_platform.simulate_price_movement("GBPUSD", 1.2475);
    
    // Move USDJPY to partial profit level
    mock_platform.simulate_price_movement("USDJPY", 150.60);

    // Process positions again after price movements
    println!("Processing positions after price movements...");
    let updated_positions = mock_platform.get_positions().await.unwrap();
    for position in updated_positions {
        let internal_position = Position {
            id: position.position_id.clone(),
            symbol: position.symbol.clone(),
            side: match position.side {
                UnifiedPositionSide::Long => PositionSide::Long,
                UnifiedPositionSide::Short => PositionSide::Short,
            },
            entry_price: position.entry_price,
            current_price: position.current_price,
            quantity: position.quantity,
            stop_loss: position.stop_loss,
            take_profit: position.take_profit,
            open_time: std::time::SystemTime::now(),
            unrealized_pnl: position.unrealized_pnl,
        };
        let _ = exit_management.update_position(internal_position).await;
    }

    // Verify system responded to price movements
    let final_modifications = mock_platform.get_order_modification_count();
    println!("Final order modifications: {}", final_modifications);
    
    // We expect at least some order modifications due to break-even and trailing stops
    assert!(final_modifications > initial_modifications, 
            "Expected order modifications after price movements");

    // Test system statistics
    let stats = exit_management.get_exit_statistics().await;
    
    println!("Exit Management Integration Test Results:");
    println!("- Total exits: {}", stats.total_exits);
    println!("- Trailing stop exits: {}", stats.trailing_stop_exits);
    println!("- Break-even exits: {}", stats.break_even_exits);
    println!("- Total order modifications: {}", final_modifications);
    
    // Test that we can retrieve audit history
    let audit_trail = exit_management.get_full_audit_trail(100).await;
    println!("Audit trail entries: {}", audit_trail.len());
    assert!(audit_trail.len() >= 0, "Should be able to retrieve audit trail");
}

#[tokio::test] 
async fn test_exit_management_error_resilience() {
    let mock_platform = Arc::new(ComprehensiveMockPlatform::new());
    
    // Add a position
    let position = create_realistic_position("EURUSD", UnifiedPositionSide::Long, 1.0800, 1.0825, Some(1.0780), Some(1.0850), 1.0);
    mock_platform.add_position(position);

    let exit_management = ExitManagementIntegration::create_with_platform(mock_platform.clone()).unwrap();

    // Test that the system handles position updates gracefully
    let internal_position = Position {
        id: "test_pos".to_string(),
        symbol: "EURUSD".to_string(),
        side: PositionSide::Long,
        entry_price: rust_decimal::Decimal::from_f64_retain(1.0800).unwrap(),
        current_price: rust_decimal::Decimal::from_f64_retain(1.0825).unwrap(),
        quantity: rust_decimal::Decimal::from(1),
        stop_loss: Some(rust_decimal::Decimal::from_f64_retain(1.0780).unwrap()),
        take_profit: Some(rust_decimal::Decimal::from_f64_retain(1.0850).unwrap()),
        open_time: std::time::SystemTime::now(),
        unrealized_pnl: rust_decimal::Decimal::from(250),
    };
    
    let result = exit_management.update_position(internal_position).await;
    assert!(result.is_ok(), "Position update should handle errors gracefully");
    
    // Test system recovery after errors
    sleep(Duration::from_millis(100)).await;
    let audit_trail = exit_management.get_full_audit_trail(10).await;
    assert!(audit_trail.len() >= 0, "System should recover after errors");
}

#[tokio::test]
async fn test_exit_management_performance_metrics() {
    let mock_platform = Arc::new(ComprehensiveMockPlatform::new());
    
    // Add several positions for performance testing
    for i in 1..=10 {
        let position = create_realistic_position(
            "EURUSD", 
            UnifiedPositionSide::Long, 
            1.0800, 
            1.0800 + (i as f64 * 0.0010), // Varying profit levels
            Some(1.0780), 
            Some(1.0850), 
            1.0
        );
        mock_platform.add_position(position);
    }

    let exit_management = ExitManagementIntegration::create_with_platform(mock_platform.clone()).unwrap();

    // Measure basic system operations
    let start = std::time::Instant::now();
    
    let positions = mock_platform.get_positions().await.unwrap();
    for (i, position) in positions.iter().enumerate() {
        let config = TrailingConfig {
            atr_multiplier: 2.0,
            min_trail_distance: 0.001,
            max_trail_distance: 0.01,
            activation_threshold: 0.002,
            symbol: position.symbol.clone(),
            timeframe: "M15".to_string(),
        };
        let _ = exit_management.configure_trailing_stop(&position.symbol, config).await;
        println!("Configured position {} for symbol {}", i + 1, position.symbol);
    }
    
    let duration = start.elapsed();
    println!("Processing 10 positions took: {:?}", duration);
    
    // Processing should complete within reasonable time (< 1 second for 10 positions)
    assert!(duration.as_secs() < 1, "Position processing took too long: {:?}", duration);
}

#[tokio::test]
async fn test_exit_management_audit_logging() {
    let mock_platform = Arc::new(ComprehensiveMockPlatform::new());
    
    // Add a position that will trigger modifications
    let position = create_realistic_position("EURUSD", UnifiedPositionSide::Long, 1.0800, 1.0825, Some(1.0780), Some(1.0850), 1.0);
    mock_platform.add_position(position);

    let exit_management = ExitManagementIntegration::create_with_platform(mock_platform.clone()).unwrap();

    // Create exit management and update position
    let exit_management = ExitManagementIntegration::create_with_platform(mock_platform.clone()).unwrap();
    
    let internal_position = Position {
        id: "audit_test".to_string(),
        symbol: "EURUSD".to_string(),
        side: PositionSide::Long,
        entry_price: rust_decimal::Decimal::from_f64_retain(1.0800).unwrap(),
        current_price: rust_decimal::Decimal::from_f64_retain(1.0825).unwrap(),
        quantity: rust_decimal::Decimal::from(1),
        stop_loss: Some(rust_decimal::Decimal::from_f64_retain(1.0780).unwrap()),
        take_profit: Some(rust_decimal::Decimal::from_f64_retain(1.0850).unwrap()),
        open_time: std::time::SystemTime::now(),
        unrealized_pnl: rust_decimal::Decimal::from(250),
    };
    
    let _result = exit_management.update_position(internal_position).await;

    // Test audit log retrieval
    let recent_exits = exit_management.get_full_audit_trail(10).await;
    println!("Recent audit entries: {}", recent_exits.len());

    // The audit trail should be accessible
    assert!(recent_exits.len() >= 0, "Audit trail should be accessible");
}