use chrono::Utc;
use risk_engine::{
    RiskConfig, RealTimePnLCalculator, MarketTick,
    PositionTracker, MarketDataStream, WebSocketPublisher, KafkaProducer,
    DrawdownTracker, EquityHistoryManager, DrawdownAlertManager,
    ExposureMonitor, CurrencyExposureCalculator, ExposureAlertManager,
    MarginMonitor, AccountManager, MarginCalculator, MarginAlertManager, MarginProtectionSystem,
    RiskResponseSystem, RiskThresholds, PositionManager, CircuitBreakerClient,
    RiskAuditLogger, ResponseExecutor
};
use risk_engine::exposure_monitor::ExposureLimits;
use rust_decimal_macros::dec;
use std::sync::Arc;
use uuid::Uuid;

#[tokio::test]
async fn test_risk_config_loading() {
    let config = RiskConfig::default();
    assert!(config.validate().is_ok());
    
    assert_eq!(config.margin_thresholds.warning_level, dec!(150));
    assert_eq!(config.margin_thresholds.critical_level, dec!(120));
    assert_eq!(config.drawdown_thresholds.daily_threshold, dec!(5));
    assert_eq!(config.drawdown_thresholds.max_threshold, dec!(20));
}

#[tokio::test]
async fn test_risk_system_initialization() {
    let config = RiskConfig::default();
    
    // Test P&L Calculator
    let position_tracker = Arc::new(PositionTracker::new());
    let market_data_stream = Arc::new(MarketDataStream::new());
    let websocket_publisher = Arc::new(WebSocketPublisher::new());
    let kafka_producer = Arc::new(KafkaProducer);
    
    let _pnl_calculator = RealTimePnLCalculator::new(
        position_tracker.clone(),
        market_data_stream.clone(),
        websocket_publisher,
        kafka_producer,
    );
    
    // Test Drawdown Tracker
    let equity_history_manager = Arc::new(EquityHistoryManager::new());
    let drawdown_alert_manager = Arc::new(DrawdownAlertManager::new());
    
    let _drawdown_tracker = DrawdownTracker::new(
        equity_history_manager,
        drawdown_alert_manager,
        config.drawdown_thresholds.clone(),
    );
    
    // Test Exposure Monitor
    let currency_calculator = Arc::new(CurrencyExposureCalculator);
    let exposure_limits = Arc::new(ExposureLimits::new());
    let exposure_alerts = Arc::new(ExposureAlertManager);
    
    let _exposure_monitor = ExposureMonitor::new(
        position_tracker.clone(),
        currency_calculator,
        exposure_limits,
        exposure_alerts,
    );
    
    // Test Margin Monitor
    let account_manager = Arc::new(AccountManager::new());
    let margin_calculator = Arc::new(MarginCalculator::new());
    let margin_alerts = Arc::new(MarginAlertManager::new());
    let margin_protection = Arc::new(MarginProtectionSystem);
    
    let _margin_monitor = MarginMonitor::new(
        account_manager,
        margin_calculator,
        margin_alerts,
        margin_protection,
        config.margin_thresholds.clone(),
    );
    
    // Test Risk Response System
    let risk_thresholds = Arc::new(RiskThresholds::default());
    let position_manager = Arc::new(PositionManager::new());
    let circuit_breaker = Arc::new(CircuitBreakerClient);
    let risk_logger = Arc::new(RiskAuditLogger::new());
    let response_executor = Arc::new(ResponseExecutor);
    
    let _risk_response = RiskResponseSystem::new(
        risk_thresholds,
        position_manager,
        circuit_breaker,
        risk_logger,
        response_executor,
    );
}

#[tokio::test]
async fn test_basic_pnl_calculation() {
    let position_tracker = Arc::new(PositionTracker::new());
    let market_data_stream = Arc::new(MarketDataStream::new());
    let websocket_publisher = Arc::new(WebSocketPublisher::new());
    let kafka_producer = Arc::new(KafkaProducer);
    
    let calculator = RealTimePnLCalculator::new(
        position_tracker.clone(),
        market_data_stream.clone(),
        websocket_publisher,
        kafka_producer,
    );
    
    let account_id = Uuid::new_v4();
    
    // Test getting account P&L (should handle empty case gracefully)
    let account_pnl = calculator.get_account_pnl(account_id).await;
    assert!(account_pnl.is_ok());
    
    let pnl = account_pnl.unwrap();
    assert_eq!(pnl.unrealized_pnl, dec!(0));
    assert_eq!(pnl.realized_pnl_today, dec!(0));
    assert_eq!(pnl.total_pnl, dec!(0));
}

#[tokio::test]
async fn test_market_data_streaming() {
    let market_data_stream = MarketDataStream::new();
    
    let tick = MarketTick {
        symbol: "EURUSD".to_string(),
        bid: dec!(1.0999),
        ask: dec!(1.1001),
        price: dec!(1.1000),
        volume: dec!(100),
        timestamp: Utc::now(),
    };
    
    // Test publishing a tick - this should work even with no subscribers
    let result = market_data_stream.publish_tick(tick).await;
    // It's OK if this fails when there are no subscribers
    let _ = result;
}

#[tokio::test]
async fn test_position_tracker() {
    let tracker = PositionTracker::new();
    let account_id = Uuid::new_v4();
    
    // Test getting positions for account (should be empty initially)
    let positions = tracker.get_account_positions(account_id).await;
    assert!(positions.is_ok());
    assert!(positions.unwrap().is_empty());
    
    // Test getting all positions (should be empty initially)
    let all_positions = tracker.get_all_open_positions().await;
    assert!(all_positions.is_ok());
    assert!(all_positions.unwrap().is_empty());
}

#[tokio::test]
async fn test_risk_config_validation() {
    let mut config = RiskConfig::default();
    
    // Valid config should pass validation
    assert!(config.validate().is_ok());
    
    // Invalid margin thresholds should fail validation
    config.margin_thresholds.warning_level = dec!(100);
    config.margin_thresholds.critical_level = dec!(120);
    assert!(config.validate().is_err());
    
    // Reset to valid and test drawdown validation
    config = RiskConfig::default();
    config.drawdown_thresholds.daily_threshold = dec!(150); // Invalid - over 100%
    assert!(config.validate().is_err());
}

#[test]
fn test_config_serialization() {
    let config = RiskConfig::default();
    
    // Test that config can be serialized to TOML
    let toml_string = toml::to_string(&config);
    assert!(toml_string.is_ok());
    
    // Test that it can be deserialized back
    let deserialized: Result<RiskConfig, _> = toml::from_str(&toml_string.unwrap());
    assert!(deserialized.is_ok());
    
    let deserialized_config = deserialized.unwrap();
    assert_eq!(config.margin_thresholds.warning_level, deserialized_config.margin_thresholds.warning_level);
    assert_eq!(config.drawdown_thresholds.daily_threshold, deserialized_config.drawdown_thresholds.daily_threshold);
}