use chrono::Utc;
use rust_decimal_macros::dec;
use uuid::Uuid;
use execution_engine::risk::{
    RiskRewardTracker, Position, PositionType, PositionTracker,
    MarketDataProvider, RiskRewardAlertManager
};
use std::sync::Arc;

#[tokio::test]
async fn test_risk_reward_calculation_with_targets() {
    let position_tracker = Arc::new(PositionTracker::new());
    let market_data = Arc::new(MarketDataProvider::new());
    let alert_manager = Arc::new(RiskRewardAlertManager::new());
    
    let tracker = RiskRewardTracker::new(
        position_tracker,
        market_data.clone(),
        alert_manager,
    );
    
    market_data.update_price("EURUSD".to_string(), dec!(1.1020)).await;
    
    let position = Position {
        id: Uuid::new_v4(),
        account_id: Uuid::new_v4(),
        symbol: "EURUSD".to_string(),
        position_type: PositionType::Long,
        size: dec!(10000),
        entry_price: dec!(1.1000),
        current_price: Some(dec!(1.1020)),
        unrealized_pnl: Some(dec!(20)),
        max_favorable_excursion: dec!(30),
        max_adverse_excursion: dec!(-10),
        stop_loss: Some(dec!(1.0950)),
        take_profit: Some(dec!(1.1100)),
        opened_at: Utc::now() - chrono::Duration::hours(2),
    };
    
    let metrics = tracker.calculate_risk_reward(&position).await.unwrap();
    
    assert_eq!(metrics.distance_to_stop, dec!(0.0050));
    assert_eq!(metrics.distance_to_target, dec!(0.0100));
    assert_eq!(metrics.current_rr_ratio, dec!(2));
    assert!(metrics.performance_score > dec!(0));
}

#[tokio::test]
async fn test_risk_reward_without_targets() {
    let position_tracker = Arc::new(PositionTracker::new());
    let market_data = Arc::new(MarketDataProvider::new());
    let alert_manager = Arc::new(RiskRewardAlertManager::new());
    
    let tracker = RiskRewardTracker::new(
        position_tracker,
        market_data.clone(),
        alert_manager,
    );
    
    market_data.update_price("GBPUSD".to_string(), dec!(1.3020)).await;
    
    let position = Position {
        id: Uuid::new_v4(),
        account_id: Uuid::new_v4(),
        symbol: "GBPUSD".to_string(),
        position_type: PositionType::Short,
        size: dec!(10000),
        entry_price: dec!(1.3000),
        current_price: Some(dec!(1.3020)),
        unrealized_pnl: Some(dec!(-20)),
        max_favorable_excursion: dec!(0),
        max_adverse_excursion: dec!(-20),
        stop_loss: None,
        take_profit: None,
        opened_at: Utc::now() - chrono::Duration::hours(1),
    };
    
    let metrics = tracker.calculate_risk_reward(&position).await.unwrap();
    
    assert_eq!(metrics.distance_to_stop, dec!(0.0260));
    assert_eq!(metrics.distance_to_target, dec!(0.0520));
    assert_eq!(metrics.current_rr_ratio, dec!(2));
}

#[tokio::test]
async fn test_performance_score_calculation() {
    let position_tracker = Arc::new(PositionTracker::new());
    let market_data = Arc::new(MarketDataProvider::new());
    let alert_manager = Arc::new(RiskRewardAlertManager::new());
    
    let tracker = RiskRewardTracker::new(
        position_tracker,
        market_data.clone(),
        alert_manager,
    );
    
    market_data.update_price("USDJPY".to_string(), dec!(110.50)).await;
    
    let position = Position {
        id: Uuid::new_v4(),
        account_id: Uuid::new_v4(),
        symbol: "USDJPY".to_string(),
        position_type: PositionType::Long,
        size: dec!(10000),
        entry_price: dec!(110.00),
        current_price: Some(dec!(110.50)),
        unrealized_pnl: Some(dec!(50)),
        max_favorable_excursion: dec!(60),
        max_adverse_excursion: dec!(-20),
        stop_loss: Some(dec!(109.50)),
        take_profit: Some(dec!(111.00)),
        opened_at: Utc::now() - chrono::Duration::hours(10),
    };
    
    let metrics = tracker.calculate_risk_reward(&position).await.unwrap();
    
    assert!(metrics.performance_score > dec!(0));
    assert!(metrics.performance_score <= dec!(100));
}

#[tokio::test]
async fn test_recommendation_generation() {
    let position_tracker = Arc::new(PositionTracker::new());
    let market_data = Arc::new(MarketDataProvider::new());
    let alert_manager = Arc::new(RiskRewardAlertManager::new());
    
    let tracker = RiskRewardTracker::new(
        position_tracker,
        market_data.clone(),
        alert_manager,
    );
    
    market_data.update_price("EURUSD".to_string(), dec!(1.1025)).await;
    
    let position = Position {
        id: Uuid::new_v4(),
        account_id: Uuid::new_v4(),
        symbol: "EURUSD".to_string(),
        position_type: PositionType::Long,
        size: dec!(10000),
        entry_price: dec!(1.1000),
        current_price: Some(dec!(1.1025)),
        unrealized_pnl: Some(dec!(250)),
        max_favorable_excursion: dec!(300),
        max_adverse_excursion: dec!(0),
        stop_loss: Some(dec!(1.0950)),
        take_profit: Some(dec!(1.1100)),
        opened_at: Utc::now(),
    };
    
    let metrics = tracker.calculate_risk_reward(&position).await.unwrap();
    
    assert!(metrics.recommendation.is_some());
    let recommendation = metrics.recommendation.unwrap();
    assert!(recommendation.contains("partial profits"));
}

#[tokio::test]
async fn test_target_optimization() {
    let position_tracker = Arc::new(PositionTracker::new());
    let market_data = Arc::new(MarketDataProvider::new());
    let alert_manager = Arc::new(RiskRewardAlertManager::new());
    
    let tracker = RiskRewardTracker::new(
        position_tracker,
        market_data.clone(),
        alert_manager,
    );
    
    market_data.update_price("GBPUSD".to_string(), dec!(1.3000)).await;
    market_data.update_atr("GBPUSD".to_string(), dec!(0.0080)).await;
    
    let position = Position {
        id: Uuid::new_v4(),
        account_id: Uuid::new_v4(),
        symbol: "GBPUSD".to_string(),
        position_type: PositionType::Long,
        size: dec!(10000),
        entry_price: dec!(1.3000),
        current_price: Some(dec!(1.3000)),
        unrealized_pnl: Some(dec!(0)),
        max_favorable_excursion: dec!(0),
        max_adverse_excursion: dec!(0),
        stop_loss: Some(dec!(1.2950)),
        take_profit: Some(dec!(1.3050)),
        opened_at: Utc::now(),
    };
    
    let optimization = tracker.optimize_targets(&position).await.unwrap();
    
    assert!(optimization.optimal_stop.is_some());
    assert!(optimization.optimal_target.is_some());
    assert_eq!(optimization.optimal_stop.unwrap(), dec!(1.2840));
    assert_eq!(optimization.optimal_target.unwrap(), dec!(1.3240));
    assert!(optimization.optimal_rr_ratio >= dec!(1.5));
    assert!(optimization.atr_based);
}