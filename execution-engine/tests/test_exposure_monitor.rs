use chrono::Utc;
use execution_engine::risk::{
    ConcentrationLevel, CurrencyExposureCalculator, ExposureAlertManager, ExposureLimits,
    ExposureMonitor, Position, PositionTracker, PositionType,
};
use rust_decimal_macros::dec;
use std::sync::Arc;
use uuid::Uuid;

#[tokio::test]
async fn test_pair_exposure_calculation() {
    let position_tracker = Arc::new(PositionTracker::new());
    let currency_calculator = Arc::new(CurrencyExposureCalculator);
    let exposure_limits = Arc::new(ExposureLimits::new());
    let alert_manager = Arc::new(ExposureAlertManager);

    let monitor = ExposureMonitor::new(
        position_tracker.clone(),
        currency_calculator,
        exposure_limits,
        alert_manager,
    );

    let positions = vec![
        Position {
            id: Uuid::new_v4(),
            account_id: Uuid::new_v4(),
            symbol: "EURUSD".to_string(),
            position_type: PositionType::Long,
            size: dec!(10000),
            entry_price: dec!(1.1000),
            current_price: None,
            unrealized_pnl: None,
            max_favorable_excursion: dec!(0),
            max_adverse_excursion: dec!(0),
            stop_loss: None,
            take_profit: None,
            opened_at: Utc::now(),
        },
        Position {
            id: Uuid::new_v4(),
            account_id: Uuid::new_v4(),
            symbol: "EURUSD".to_string(),
            position_type: PositionType::Short,
            size: dec!(5000),
            entry_price: dec!(1.1050),
            current_price: None,
            unrealized_pnl: None,
            max_favorable_excursion: dec!(0),
            max_adverse_excursion: dec!(0),
            stop_loss: None,
            take_profit: None,
            opened_at: Utc::now(),
        },
    ];

    for position in &positions {
        position_tracker
            .positions
            .insert(position.id, position.clone());
    }

    let report = monitor.calculate_total_exposure().await.unwrap();

    assert!(report.pair_exposure.contains_key("EURUSD"));
    let eurusd_exposure = &report.pair_exposure["EURUSD"];
    assert_eq!(eurusd_exposure.long_exposure, dec!(11000));
    assert_eq!(eurusd_exposure.short_exposure, dec!(5525));
    assert_eq!(eurusd_exposure.net_exposure, dec!(5475));
    assert_eq!(eurusd_exposure.position_count, 2);
}

#[tokio::test]
async fn test_concentration_risk_calculation() {
    let position_tracker = Arc::new(PositionTracker::new());
    let currency_calculator = Arc::new(CurrencyExposureCalculator);
    let exposure_limits = Arc::new(ExposureLimits::new());
    let alert_manager = Arc::new(ExposureAlertManager);

    let monitor = ExposureMonitor::new(
        position_tracker.clone(),
        currency_calculator,
        exposure_limits,
        alert_manager,
    );

    let positions = vec![
        Position {
            id: Uuid::new_v4(),
            account_id: Uuid::new_v4(),
            symbol: "EURUSD".to_string(),
            position_type: PositionType::Long,
            size: dec!(50000),
            entry_price: dec!(1.1000),
            current_price: None,
            unrealized_pnl: None,
            max_favorable_excursion: dec!(0),
            max_adverse_excursion: dec!(0),
            stop_loss: None,
            take_profit: None,
            opened_at: Utc::now(),
        },
        Position {
            id: Uuid::new_v4(),
            account_id: Uuid::new_v4(),
            symbol: "GBPUSD".to_string(),
            position_type: PositionType::Long,
            size: dec!(10000),
            entry_price: dec!(1.3000),
            current_price: None,
            unrealized_pnl: None,
            max_favorable_excursion: dec!(0),
            max_adverse_excursion: dec!(0),
            stop_loss: None,
            take_profit: None,
            opened_at: Utc::now(),
        },
    ];

    for position in &positions {
        position_tracker
            .positions
            .insert(position.id, position.clone());
    }

    let report = monitor.calculate_total_exposure().await.unwrap();

    assert!(report.concentration_risk.herfindahl_index > dec!(0.5));
    assert_eq!(
        report.concentration_risk.concentration_level,
        ConcentrationLevel::High
    );
}

#[tokio::test]
async fn test_currency_exposure_calculation() {
    let currency_calculator = CurrencyExposureCalculator;

    let positions = vec![
        Position {
            id: Uuid::new_v4(),
            account_id: Uuid::new_v4(),
            symbol: "EURUSD".to_string(),
            position_type: PositionType::Long,
            size: dec!(10000),
            entry_price: dec!(1.1000),
            current_price: None,
            unrealized_pnl: None,
            max_favorable_excursion: dec!(0),
            max_adverse_excursion: dec!(0),
            stop_loss: None,
            take_profit: None,
            opened_at: Utc::now(),
        },
        Position {
            id: Uuid::new_v4(),
            account_id: Uuid::new_v4(),
            symbol: "GBPUSD".to_string(),
            position_type: PositionType::Short,
            size: dec!(5000),
            entry_price: dec!(1.3000),
            current_price: None,
            unrealized_pnl: None,
            max_favorable_excursion: dec!(0),
            max_adverse_excursion: dec!(0),
            stop_loss: None,
            take_profit: None,
            opened_at: Utc::now(),
        },
    ];

    let currency_exposure = currency_calculator
        .calculate_net_exposure(&positions)
        .await
        .unwrap();

    assert_eq!(currency_exposure["EUR"], dec!(11000));
    assert_eq!(currency_exposure["USD"], dec!(-11000) + dec!(6500));
    assert_eq!(currency_exposure["GBP"], dec!(-6500));
}

#[tokio::test]
async fn test_diversification_score() {
    let position_tracker = Arc::new(PositionTracker::new());
    let currency_calculator = Arc::new(CurrencyExposureCalculator);
    let exposure_limits = Arc::new(ExposureLimits::new());
    let alert_manager = Arc::new(ExposureAlertManager);

    let monitor = ExposureMonitor::new(
        position_tracker.clone(),
        currency_calculator,
        exposure_limits,
        alert_manager,
    );

    let positions = vec![
        Position {
            id: Uuid::new_v4(),
            account_id: Uuid::new_v4(),
            symbol: "EURUSD".to_string(),
            position_type: PositionType::Long,
            size: dec!(10000),
            entry_price: dec!(1.1000),
            current_price: None,
            unrealized_pnl: None,
            max_favorable_excursion: dec!(0),
            max_adverse_excursion: dec!(0),
            stop_loss: None,
            take_profit: None,
            opened_at: Utc::now(),
        },
        Position {
            id: Uuid::new_v4(),
            account_id: Uuid::new_v4(),
            symbol: "GBPUSD".to_string(),
            position_type: PositionType::Long,
            size: dec!(10000),
            entry_price: dec!(1.3000),
            current_price: None,
            unrealized_pnl: None,
            max_favorable_excursion: dec!(0),
            max_adverse_excursion: dec!(0),
            stop_loss: None,
            take_profit: None,
            opened_at: Utc::now(),
        },
        Position {
            id: Uuid::new_v4(),
            account_id: Uuid::new_v4(),
            symbol: "USDJPY".to_string(),
            position_type: PositionType::Long,
            size: dec!(10000),
            entry_price: dec!(110.00),
            current_price: None,
            unrealized_pnl: None,
            max_favorable_excursion: dec!(0),
            max_adverse_excursion: dec!(0),
            stop_loss: None,
            take_profit: None,
            opened_at: Utc::now(),
        },
    ];

    for position in &positions {
        position_tracker
            .positions
            .insert(position.id, position.clone());
    }

    let report = monitor.calculate_total_exposure().await.unwrap();

    assert!(report.diversification_score > dec!(50));
}
