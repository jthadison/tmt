use chrono::Utc;
use rust_decimal::Decimal;
use rust_decimal_macros::dec;
use uuid::Uuid;

// Import only the types we need for testing the risk calculations
use execution_engine::risk::types::{
    Position, PositionType, MarketTick, PnLSnapshot, DrawdownMetrics, 
    DrawdownData, EquityPoint, AccountId, PositionId
};

#[tokio::test]
async fn test_basic_risk_types() {
    // Test basic position creation
    let position = Position {
        id: Uuid::new_v4(),
        account_id: Uuid::new_v4(),
        symbol: "EURUSD".to_string(),
        position_type: PositionType::Long,
        size: dec!(1.0),
        entry_price: dec!(1.1000),
        current_price: Some(dec!(1.1050)),
        unrealized_pnl: Some(dec!(50.0)),
        max_favorable_excursion: dec!(0),
        max_adverse_excursion: dec!(0),
        stop_loss: Some(dec!(1.0950)),
        take_profit: Some(dec!(1.1100)),
        opened_at: Utc::now(),
    };

    assert_eq!(position.symbol, "EURUSD");
    assert_eq!(position.position_type, PositionType::Long);
    assert_eq!(position.size, dec!(1.0));
    assert_eq!(position.entry_price, dec!(1.1000));
}

#[tokio::test]
async fn test_market_tick_creation() {
    let tick = MarketTick {
        symbol: "GBPUSD".to_string(),
        bid: dec!(1.2549),
        ask: dec!(1.2551),
        price: dec!(1.2550),
        volume: dec!(100),
        timestamp: Utc::now(),
    };

    assert_eq!(tick.symbol, "GBPUSD");
    assert_eq!(tick.price, dec!(1.2550));
    assert!(tick.bid < tick.ask);
}

#[tokio::test]
async fn test_pnl_snapshot_creation() {
    let pnl_snapshot = PnLSnapshot {
        position_id: Uuid::new_v4(),
        unrealized_pnl: dec!(75.5),
        unrealized_pnl_percentage: dec!(2.3),
        max_favorable_excursion: dec!(100.0),
        max_adverse_excursion: dec!(-25.0),
        current_price: dec!(1.1075),
        timestamp: Utc::now(),
    };

    assert_eq!(pnl_snapshot.unrealized_pnl, dec!(75.5));
    assert_eq!(pnl_snapshot.unrealized_pnl_percentage, dec!(2.3));
    assert!(pnl_snapshot.max_favorable_excursion > dec!(0));
    assert!(pnl_snapshot.max_adverse_excursion < dec!(0));
}

#[tokio::test]
async fn test_drawdown_data_default() {
    let drawdown_data = DrawdownData::default();
    
    assert_eq!(drawdown_data.amount, dec!(0));
    assert_eq!(drawdown_data.percentage, dec!(0));
    assert_eq!(drawdown_data.peak_equity, dec!(0));
    assert_eq!(drawdown_data.current_equity, dec!(0));
}

#[tokio::test]
async fn test_equity_point_creation() {
    let equity_point = EquityPoint {
        equity: dec!(10500.75),
        balance: dec!(10000.00),
        timestamp: Utc::now(),
    };

    assert_eq!(equity_point.equity, dec!(10500.75));
    assert_eq!(equity_point.balance, dec!(10000.00));
    assert!(equity_point.equity > equity_point.balance); // Positive unrealized P&L
}

#[test]
fn test_position_type_serialization() {
    // Test that position types can be serialized/deserialized
    let long_pos = PositionType::Long;
    let short_pos = PositionType::Short;

    assert_ne!(long_pos, short_pos);
    
    // Test JSON serialization
    let long_json = serde_json::to_string(&long_pos).unwrap();
    let short_json = serde_json::to_string(&short_pos).unwrap();
    
    assert_eq!(long_json, "\"Long\"");
    assert_eq!(short_json, "\"Short\"");
    
    // Test deserialization
    let deserialized_long: PositionType = serde_json::from_str(&long_json).unwrap();
    let deserialized_short: PositionType = serde_json::from_str(&short_json).unwrap();
    
    assert_eq!(deserialized_long, PositionType::Long);
    assert_eq!(deserialized_short, PositionType::Short);
}