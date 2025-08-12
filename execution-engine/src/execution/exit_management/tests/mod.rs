pub mod test_break_even;
pub mod test_platform_integration;
pub mod test_trailing_stops;

use super::{types::*, TradingPlatform};
use chrono::{Duration, Utc};
use rust_decimal::Decimal;
use uuid::Uuid;

// Mock trading platform for testing
#[derive(Debug, Clone)]
pub struct MockTradingPlatform {
    positions: Vec<Position>,
    market_data: std::collections::HashMap<String, MarketData>,
}

impl MockTradingPlatform {
    pub fn new() -> Self {
        let mut market_data = std::collections::HashMap::new();

        // Add default market data
        market_data.insert(
            "EURUSD".to_string(),
            MarketData {
                symbol: "EURUSD".to_string(),
                bid: 1.0800,
                ask: 1.0802,
                spread: 0.0002,
                timestamp: Utc::now(),
            },
        );

        market_data.insert(
            "GBPUSD".to_string(),
            MarketData {
                symbol: "GBPUSD".to_string(),
                bid: 1.2500,
                ask: 1.2502,
                spread: 0.0002,
                timestamp: Utc::now(),
            },
        );

        Self {
            positions: Vec::new(),
            market_data,
        }
    }

    pub fn add_position(&mut self, position: Position) {
        self.positions.push(position);
    }

    pub fn update_market_data(&mut self, symbol: String, market_data: MarketData) {
        self.market_data.insert(symbol, market_data);
    }
}

#[async_trait::async_trait]
impl TradingPlatform for MockTradingPlatform {
    async fn get_positions(&self) -> anyhow::Result<Vec<Position>> {
        Ok(self.positions.clone())
    }

    async fn get_market_data(&self, symbol: &str) -> anyhow::Result<MarketData> {
        self.market_data
            .get(symbol)
            .cloned()
            .ok_or_else(|| anyhow::anyhow!("Market data not found for symbol: {}", symbol))
    }

    async fn modify_order(
        &self,
        _request: OrderModifyRequest,
    ) -> anyhow::Result<OrderModifyResult> {
        Ok(OrderModifyResult {
            order_id: "test_order".to_string(),
            success: true,
            message: "Order modified successfully".to_string(),
        })
    }

    async fn close_position(
        &self,
        _request: ClosePositionRequest,
    ) -> anyhow::Result<ClosePositionResult> {
        Ok(ClosePositionResult {
            position_id: Uuid::new_v4(),
            close_price: 1.0801,
            realized_pnl: Some(Decimal::from_f64_retain(10.0).unwrap()),
            close_time: Utc::now(),
        })
    }

    async fn close_position_partial(
        &self,
        _request: PartialCloseRequest,
    ) -> anyhow::Result<ClosePositionResult> {
        Ok(ClosePositionResult {
            position_id: Uuid::new_v4(),
            close_price: 1.0801,
            realized_pnl: Some(Decimal::from_f64_retain(5.0).unwrap()),
            close_time: Utc::now(),
        })
    }
}

// Helper function to create a test position
pub fn create_test_position() -> Position {
    Position {
        id: Uuid::new_v4(),
        order_id: "test_order_001".to_string(),
        symbol: "EURUSD".to_string(),
        position_type: UnifiedPositionSide::Long,
        volume: Decimal::from_f64_retain(1.0).unwrap(),
        entry_price: 1.0800,
        current_price: 1.0820,
        stop_loss: Some(1.0780),
        take_profit: Some(1.0850),
        unrealized_pnl: 20.0,
        swap: 0.0,
        commission: 5.0,
        open_time: Utc::now()
            - Duration::from_std(std::time::Duration::from_secs(2 * 3600)).unwrap(),
        magic_number: Some(12345),
        comment: Some("Test position".to_string()),
    }
}

pub fn create_test_position_with_params(
    symbol: &str,
    position_type: UnifiedPositionSide,
    entry_price: f64,
    current_price: f64,
    stop_loss: Option<f64>,
    age_hours: i64,
) -> Position {
    Position {
        id: Uuid::new_v4(),
        order_id: format!("test_order_{}", Uuid::new_v4().to_string()[..8].to_string()),
        symbol: symbol.to_string(),
        position_type: position_type.clone(),
        volume: Decimal::from_f64_retain(1.0).unwrap(),
        entry_price,
        current_price,
        stop_loss,
        take_profit: Some(entry_price + 0.0050), // 50 pips TP
        unrealized_pnl: match position_type {
            UnifiedPositionSide::Long => (current_price - entry_price) * 10000.0, // Convert to pips
            UnifiedPositionSide::Short => (entry_price - current_price) * 10000.0,
        },
        swap: 0.0,
        commission: 5.0,
        open_time: Utc::now()
            - Duration::from_std(std::time::Duration::from_hours(age_hours as u64)).unwrap(),
        magic_number: Some(12345),
        comment: Some("Test position".to_string()),
    }
}
