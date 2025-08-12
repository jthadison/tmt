use chrono::{Duration, Utc};
use risk_engine::*;
use risk_types::*;
use rust_decimal_macros::dec;
use std::sync::Arc;
use uuid::Uuid;

/// Test critical edge cases that could cause financial losses
#[cfg(test)]
mod financial_edge_cases {
    use super::*;

    #[tokio::test]
    async fn test_zero_equity_division_by_zero_protection() {
        let equity_history_manager = Arc::new(EquityHistoryManager::new());
        let drawdown_alert_manager = Arc::new(DrawdownAlertManager::new());
        let thresholds = DrawdownThresholds::default();
        let tracker = DrawdownTracker::new(
            equity_history_manager.clone(),
            drawdown_alert_manager,
            thresholds,
        );

        let account_id = Uuid::new_v4();

        // Edge case: Zero equity scenario
        let equity_points = vec![
            EquityPoint {
                equity: dec!(0),
                balance: dec!(0),
                timestamp: Utc::now() - Duration::hours(2),
            },
            EquityPoint {
                equity: dec!(0),
                balance: dec!(0),
                timestamp: Utc::now() - Duration::hours(1),
            },
            EquityPoint {
                equity: dec!(0),
                balance: dec!(0),
                timestamp: Utc::now(),
            },
        ];

        for point in equity_points {
            equity_history_manager
                .record_equity(account_id, point.equity, point.balance)
                .await
                .unwrap();
        }

        let metrics = tracker.calculate_drawdowns(account_id).await.unwrap();

        // Should not panic or produce infinite/NaN values
        assert!(metrics.maximum_drawdown.percentage.is_finite());
        assert!(metrics.recovery_factor.is_finite());
        assert!(metrics.daily_drawdown.percentage.is_finite());
    }

    #[tokio::test]
    async fn test_negative_equity_scenario() {
        let equity_history_manager = Arc::new(EquityHistoryManager::new());
        let drawdown_alert_manager = Arc::new(DrawdownAlertManager::new());
        let thresholds = DrawdownThresholds::default();
        let tracker = DrawdownTracker::new(
            equity_history_manager.clone(),
            drawdown_alert_manager,
            thresholds,
        );

        let account_id = Uuid::new_v4();

        // Edge case: Account goes negative (margin call scenario)
        let equity_points = vec![
            EquityPoint {
                equity: dec!(10000),
                balance: dec!(10000),
                timestamp: Utc::now() - Duration::hours(4),
            },
            EquityPoint {
                equity: dec!(5000),
                balance: dec!(10000),
                timestamp: Utc::now() - Duration::hours(3),
            },
            EquityPoint {
                equity: dec!(0),
                balance: dec!(10000),
                timestamp: Utc::now() - Duration::hours(2),
            },
            EquityPoint {
                equity: dec!(-2000),
                balance: dec!(10000),
                timestamp: Utc::now() - Duration::hours(1),
            },
            EquityPoint {
                equity: dec!(-5000),
                balance: dec!(10000),
                timestamp: Utc::now(),
            },
        ];

        for point in equity_points {
            equity_history_manager
                .record_equity(account_id, point.equity, point.balance)
                .await
                .unwrap();
        }

        let metrics = tracker.calculate_drawdowns(account_id).await.unwrap();

        // Should handle negative equity correctly
        assert!(metrics.maximum_drawdown.amount > dec!(10000)); // More than 100% drawdown
        assert!(metrics.maximum_drawdown.percentage > dec!(100));
        assert!(metrics.recovery_factor < dec!(0)); // Negative recovery factor
    }

    #[tokio::test]
    async fn test_extreme_market_volatility() {
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

        // Edge case: Extreme price movement (e.g., Swiss franc event, flash crash)
        let position = Position {
            id: Uuid::new_v4(),
            account_id: Uuid::new_v4(),
            symbol: "EURCHF".to_string(),
            position_type: PositionType::Long,
            size: dec!(100000), // Large position
            entry_price: dec!(1.2000),
            current_price: None,
            unrealized_pnl: None,
            max_favorable_excursion: dec!(0),
            max_adverse_excursion: dec!(0),
            stop_loss: Some(dec!(1.1950)),
            take_profit: Some(dec!(1.2100)),
            opened_at: Utc::now() - Duration::hours(1),
        };

        // Flash crash - price drops 15% instantly
        let extreme_tick = MarketTick {
            symbol: "EURCHF".to_string(),
            bid: dec!(1.0199),
            ask: dec!(1.0201),
            price: dec!(1.0200), // 15% drop
            volume: dec!(50000),
            timestamp: Utc::now(),
        };

        let pnl = calculator
            .calculate_position_pnl(&position, &extreme_tick)
            .await
            .unwrap();

        // Should handle extreme losses correctly
        assert!(pnl.unrealized_pnl < dec!(-15000)); // Significant loss
        assert!(pnl.unrealized_pnl_percentage < dec!(-10)); // More than -10%
        assert!(pnl.max_adverse_excursion < dec!(0)); // Negative MFE
    }

    #[tokio::test]
    async fn test_floating_point_precision_edge_cases() {
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

        // Edge case: Very small price movements that could cause precision issues
        let position = Position {
            id: Uuid::new_v4(),
            account_id: Uuid::new_v4(),
            symbol: "USDJPY".to_string(),
            position_type: PositionType::Long,
            size: dec!(1000000),              // Very large position
            entry_price: dec!(149.123456789), // Many decimal places
            current_price: None,
            unrealized_pnl: None,
            max_favorable_excursion: dec!(0),
            max_adverse_excursion: dec!(0),
            stop_loss: None,
            take_profit: None,
            opened_at: Utc::now(),
        };

        // Very small price movement
        let tick = MarketTick {
            symbol: "USDJPY".to_string(),
            bid: dec!(149.123456790),
            ask: dec!(149.123456792),
            price: dec!(149.123456791), // 0.000000002 difference
            volume: dec!(1),
            timestamp: Utc::now(),
        };

        let pnl = calculator
            .calculate_position_pnl(&position, &tick)
            .await
            .unwrap();

        // Should handle precision correctly without overflow/underflow
        assert!(pnl.unrealized_pnl.is_finite());
        assert!(pnl.unrealized_pnl_percentage.is_finite());
        assert!(pnl.unrealized_pnl >= dec!(0)); // Should be positive
    }

    #[tokio::test]
    async fn test_margin_level_extreme_scenarios() {
        let account_manager = Arc::new(AccountManager::new());
        let margin_calculator = Arc::new(MarginCalculator::new());
        let margin_alerts = Arc::new(MarginAlertManager::new());
        let margin_protection = Arc::new(MarginProtectionSystem::new());
        let thresholds = MarginThresholds::default();

        let monitor = MarginMonitor::new(
            account_manager.clone(),
            margin_calculator.clone(),
            margin_alerts,
            margin_protection,
            thresholds,
        );

        // Edge case: Account with zero used margin (no positions)
        let account_no_positions = Account {
            id: Uuid::new_v4(),
            balance: dec!(10000),
            equity: dec!(10000),
            active: true,
            last_updated: Utc::now(),
        };

        let margin_info = monitor
            .calculate_account_margin(&account_no_positions)
            .await
            .unwrap();

        // Should handle infinite margin level correctly
        assert_eq!(margin_info.margin_level, Decimal::MAX);
        assert_eq!(margin_info.used_margin, dec!(0));
        assert_eq!(margin_info.free_margin, dec!(10000));

        // Edge case: Account with negative equity
        let account_negative = Account {
            id: Uuid::new_v4(),
            balance: dec!(10000),
            equity: dec!(-2000), // Negative equity
            active: true,
            last_updated: Utc::now(),
        };

        // This should handle negative equity gracefully
        let margin_info_neg = monitor
            .calculate_account_margin(&account_negative)
            .await
            .unwrap();
        assert!(margin_info_neg.margin_level.is_finite());
        assert!(margin_info_neg.free_margin < dec!(0));
    }

    #[tokio::test]
    async fn test_correlation_calculation_edge_cases() {
        let position_tracker = Arc::new(PositionTracker::new());
        let exposure_calculator = Arc::new(CurrencyExposureCalculator::new());
        let exposure_alerts = Arc::new(ExposureAlertManager::new());
        let limits = ExposureLimits::default();

        let monitor = ExposureMonitor::new(
            position_tracker.clone(),
            exposure_calculator,
            exposure_alerts,
            limits,
        );

        let account_id = Uuid::new_v4();

        // Edge case: Single position (correlation calculation should handle gracefully)
        let positions = vec![Position {
            id: Uuid::new_v4(),
            account_id,
            symbol: "EURUSD".to_string(),
            position_type: PositionType::Long,
            size: dec!(100000),
            entry_price: dec!(1.1000),
            current_price: Some(dec!(1.1050)),
            unrealized_pnl: Some(dec!(500)),
            max_favorable_excursion: dec!(500),
            max_adverse_excursion: dec!(0),
            stop_loss: None,
            take_profit: None,
            opened_at: Utc::now(),
        }];

        let report = monitor
            .calculate_account_exposure(account_id, positions)
            .await
            .unwrap();

        // With only one position, HHI should be 1.0 (maximum concentration)
        assert_eq!(report.concentration_risk.herfindahl_index, dec!(1));
        assert_eq!(
            report.concentration_risk.concentration_level,
            ConcentrationLevel::High
        );
        assert_eq!(
            report.concentration_risk.largest_position_percentage,
            dec!(100)
        );
    }

    #[tokio::test]
    async fn test_risk_reward_calculation_edge_cases() {
        let position_tracker = Arc::new(PositionTracker::new());
        let market_data_provider = Arc::new(MarketDataProvider::new());
        let rr_alerts = Arc::new(RiskRewardAlertManager::new());

        let tracker =
            RiskRewardTracker::new(position_tracker.clone(), market_data_provider, rr_alerts);

        let account_id = Uuid::new_v4();

        // Edge case: Position with no stop loss or take profit
        let position_no_sl_tp = Position {
            id: Uuid::new_v4(),
            account_id,
            symbol: "GBPUSD".to_string(),
            position_type: PositionType::Long,
            size: dec!(100000),
            entry_price: dec!(1.3000),
            current_price: Some(dec!(1.3050)),
            unrealized_pnl: Some(dec!(500)),
            max_favorable_excursion: dec!(500),
            max_adverse_excursion: dec!(-200),
            stop_loss: None,   // No stop loss
            take_profit: None, // No take profit
            opened_at: Utc::now() - Duration::hours(2),
        };

        let metrics = tracker
            .calculate_risk_reward_metrics(&position_no_sl_tp)
            .await
            .unwrap();

        // Should handle missing SL/TP gracefully
        assert!(metrics.current_rr_ratio.is_finite());
        assert_eq!(metrics.distance_to_stop, Decimal::ZERO); // No stop loss
        assert_eq!(metrics.distance_to_target, Decimal::ZERO); // No take profit

        // Edge case: Stop loss above entry price (invalid setup)
        let position_invalid_sl = Position {
            id: Uuid::new_v4(),
            account_id,
            symbol: "GBPUSD".to_string(),
            position_type: PositionType::Long,
            size: dec!(100000),
            entry_price: dec!(1.3000),
            current_price: Some(dec!(1.3050)),
            unrealized_pnl: Some(dec!(500)),
            max_favorable_excursion: dec!(500),
            max_adverse_excursion: dec!(0),
            stop_loss: Some(dec!(1.3100)), // Stop loss above entry for long position (invalid)
            take_profit: Some(dec!(1.3200)),
            opened_at: Utc::now(),
        };

        let metrics_invalid = tracker
            .calculate_risk_reward_metrics(&position_invalid_sl)
            .await
            .unwrap();

        // Should detect invalid setup
        assert!(metrics_invalid.performance_score < dec!(0)); // Poor performance score
        assert!(metrics_invalid.recommendation.is_some()); // Should have a recommendation
    }
}
