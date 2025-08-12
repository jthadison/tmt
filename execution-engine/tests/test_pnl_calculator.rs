use chrono::Utc;
use execution_engine::risk::{
    CurrencyConverter, KafkaProducer, MarketDataStream, MarketTick, Position, PositionTracker,
    PositionType, RealTimePnLCalculator, WebSocketPublisher,
};
use rust_decimal::Decimal;
use rust_decimal_macros::dec;
use std::sync::Arc;
use uuid::Uuid;

#[tokio::test]
async fn test_pnl_calculation_long_position() {
    let position_tracker = Arc::new(PositionTracker::new());
    let market_data_stream = Arc::new(MarketDataStream::new());
    let websocket_publisher = Arc::new(WebSocketPublisher::new());
    let kafka_producer = Arc::new(KafkaProducer);

    let currency_converter = Arc::new(CurrencyConverter::new());
    let calculator = RealTimePnLCalculator::new(
        position_tracker.clone(),
        market_data_stream.clone(),
        websocket_publisher,
        kafka_producer,
        currency_converter,
    );

    let position = Position {
        id: Uuid::new_v4(),
        account_id: Uuid::new_v4(),
        symbol: "EURUSD".to_string(),
        position_type: PositionType::Long,
        size: dec!(1.0),
        entry_price: dec!(1.1000),
        current_price: None,
        unrealized_pnl: None,
        max_favorable_excursion: dec!(0),
        max_adverse_excursion: dec!(0),
        stop_loss: Some(dec!(1.0950)),
        take_profit: Some(dec!(1.1100)),
        opened_at: Utc::now(),
    };

    let tick = MarketTick {
        symbol: "EURUSD".to_string(),
        bid: dec!(1.1049),
        ask: dec!(1.1051),
        price: dec!(1.1050),
        volume: dec!(100),
        timestamp: Utc::now(),
    };

    let pnl = calculator
        .calculate_position_pnl(&position, &tick)
        .await
        .unwrap();

    assert_eq!(pnl.current_price, dec!(1.1050));
    assert!(pnl.unrealized_pnl > dec!(0));
    assert!(pnl.unrealized_pnl_percentage > dec!(0));
}

#[tokio::test]
async fn test_pnl_calculation_short_position() {
    let position_tracker = Arc::new(PositionTracker::new());
    let market_data_stream = Arc::new(MarketDataStream::new());
    let websocket_publisher = Arc::new(WebSocketPublisher::new());
    let kafka_producer = Arc::new(KafkaProducer);

    let currency_converter = Arc::new(CurrencyConverter::new());
    let calculator = RealTimePnLCalculator::new(
        position_tracker.clone(),
        market_data_stream.clone(),
        websocket_publisher,
        kafka_producer,
        currency_converter,
    );

    let position = Position {
        id: Uuid::new_v4(),
        account_id: Uuid::new_v4(),
        symbol: "GBPUSD".to_string(),
        position_type: PositionType::Short,
        size: dec!(1.0),
        entry_price: dec!(1.3000),
        current_price: None,
        unrealized_pnl: None,
        max_favorable_excursion: dec!(0),
        max_adverse_excursion: dec!(0),
        stop_loss: Some(dec!(1.3050)),
        take_profit: Some(dec!(1.2900)),
        opened_at: Utc::now(),
    };

    let tick = MarketTick {
        symbol: "GBPUSD".to_string(),
        bid: dec!(1.2949),
        ask: dec!(1.2951),
        price: dec!(1.2950),
        volume: dec!(100),
        timestamp: Utc::now(),
    };

    let pnl = calculator
        .calculate_position_pnl(&position, &tick)
        .await
        .unwrap();

    assert_eq!(pnl.current_price, dec!(1.2950));
    assert!(pnl.unrealized_pnl > dec!(0));
    assert!(pnl.unrealized_pnl_percentage > dec!(0));
}

#[tokio::test]
async fn test_max_favorable_adverse_excursion() {
    let position_tracker = Arc::new(PositionTracker::new());
    let market_data_stream = Arc::new(MarketDataStream::new());
    let websocket_publisher = Arc::new(WebSocketPublisher::new());
    let kafka_producer = Arc::new(KafkaProducer);

    let currency_converter = Arc::new(CurrencyConverter::new());
    let calculator = RealTimePnLCalculator::new(
        position_tracker.clone(),
        market_data_stream.clone(),
        websocket_publisher,
        kafka_producer,
        currency_converter,
    );

    let mut position = Position {
        id: Uuid::new_v4(),
        account_id: Uuid::new_v4(),
        symbol: "USDJPY".to_string(),
        position_type: PositionType::Long,
        size: dec!(1.0),
        entry_price: dec!(110.00),
        current_price: None,
        unrealized_pnl: None,
        max_favorable_excursion: dec!(0),
        max_adverse_excursion: dec!(0),
        stop_loss: None,
        take_profit: None,
        opened_at: Utc::now(),
    };

    let tick_favorable = MarketTick {
        symbol: "USDJPY".to_string(),
        bid: dec!(110.49),
        ask: dec!(110.51),
        price: dec!(110.50),
        volume: dec!(100),
        timestamp: Utc::now(),
    };

    let pnl_favorable = calculator
        .calculate_position_pnl(&position, &tick_favorable)
        .await
        .unwrap();
    assert!(pnl_favorable.max_favorable_excursion > dec!(0));

    position.max_favorable_excursion = pnl_favorable.max_favorable_excursion;

    let tick_adverse = MarketTick {
        symbol: "USDJPY".to_string(),
        bid: dec!(109.49),
        ask: dec!(109.51),
        price: dec!(109.50),
        volume: dec!(100),
        timestamp: Utc::now(),
    };

    let pnl_adverse = calculator
        .calculate_position_pnl(&position, &tick_adverse)
        .await
        .unwrap();
    assert!(pnl_adverse.max_adverse_excursion < dec!(0));
    assert_eq!(
        pnl_adverse.max_favorable_excursion,
        position.max_favorable_excursion
    );
}
