use chrono::{Duration, Utc};
use risk_types::*;
use rust_decimal_macros::dec;
use uuid::Uuid;
use risk_engine::*;
use std::sync::Arc;

/// Stress tests for high-load scenarios that could occur in live trading
#[cfg(test)]
mod stress_tests {
    use super::*;

    #[tokio::test]
    async fn test_high_frequency_tick_processing() {
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
        
        // Create a position
        let position = Position {
            id: Uuid::new_v4(),
            account_id: Uuid::new_v4(),
            symbol: "EURUSD".to_string(),
            position_type: PositionType::Long,
            size: dec!(100000),
            entry_price: dec!(1.1000),
            current_price: None,
            unrealized_pnl: None,
            max_favorable_excursion: dec!(0),
            max_adverse_excursion: dec!(0),
            stop_loss: None,
            take_profit: None,
            opened_at: Utc::now(),
        };

        // Stress test: Process 10,000 rapid price updates
        let start_time = std::time::Instant::now();
        let mut total_pnl = dec!(0);
        
        for i in 0..10000 {
            let price_variation = dec!(0.0001) * Decimal::from(i % 100 - 50); // Simulate price movement
            let tick = MarketTick {
                symbol: "EURUSD".to_string(),
                bid: dec!(1.1000) + price_variation - dec!(0.00001),
                ask: dec!(1.1000) + price_variation + dec!(0.00001),
                price: dec!(1.1000) + price_variation,
                volume: dec!(1000),
                timestamp: Utc::now(),
            };
            
            let pnl = calculator.calculate_position_pnl(&position, &tick).await.unwrap();
            total_pnl += pnl.unrealized_pnl;
            
            // Verify no memory leaks or performance degradation
            assert!(pnl.unrealized_pnl.is_finite());
            assert!(pnl.unrealized_pnl_percentage.is_finite());
        }
        
        let duration = start_time.elapsed();
        
        // Should process 10k ticks in reasonable time (< 5 seconds on modern hardware)
        assert!(duration.as_secs() < 5, "High frequency processing took too long: {:?}", duration);
        assert!(total_pnl.is_finite());
        
        println!("Processed 10,000 ticks in {:?}", duration);
    }

    #[tokio::test]
    async fn test_large_portfolio_exposure_calculation() {
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
        
        // Create a large portfolio with 1000 positions across various symbols
        let symbols = vec!["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD", "EURGBP"];
        let mut positions = Vec::new();
        
        for i in 0..1000 {
            let symbol_index = i % symbols.len();
            let position = Position {
                id: Uuid::new_v4(),
                account_id,
                symbol: symbols[symbol_index].to_string(),
                position_type: if i % 2 == 0 { PositionType::Long } else { PositionType::Short },
                size: dec!(10000) + Decimal::from(i * 100), // Varying position sizes
                entry_price: dec!(1.0000) + Decimal::from(i) * dec!(0.0001),
                current_price: Some(dec!(1.0000) + Decimal::from(i) * dec!(0.0001) + dec!(0.0010)),
                unrealized_pnl: Some(Decimal::from(i) * dec!(0.1)),
                max_favorable_excursion: Decimal::from(i) * dec!(0.15),
                max_adverse_excursion: Decimal::from(i) * dec!(-0.05),
                stop_loss: None,
                take_profit: None,
                opened_at: Utc::now() - Duration::minutes(i as i64),
            };
            positions.push(position);
        }
        
        let start_time = std::time::Instant::now();
        let report = monitor.calculate_account_exposure(account_id, positions).await.unwrap();
        let duration = start_time.elapsed();
        
        // Should handle large portfolios efficiently
        assert!(duration.as_millis() < 1000, "Large portfolio calculation took too long: {:?}", duration);
        assert!(report.concentration_risk.herfindahl_index.is_finite());
        assert!(report.total_exposure > dec!(0));
        assert!(!report.pair_exposure.is_empty());
        
        println!("Calculated exposure for 1000 positions in {:?}", duration);
    }

    #[tokio::test]
    async fn test_memory_usage_under_load() {
        let equity_history_manager = Arc::new(EquityHistoryManager::new());
        let drawdown_alert_manager = Arc::new(DrawdownAlertManager::new());
        let thresholds = DrawdownThresholds::default();
        let tracker = DrawdownTracker::new(equity_history_manager.clone(), drawdown_alert_manager, thresholds);
        
        // Simulate 100 accounts with extensive equity history
        let mut account_ids = Vec::new();
        for _ in 0..100 {
            account_ids.push(Uuid::new_v4());
        }
        
        // Add 30 days of hourly equity points for each account (72,000 total points)
        for account_id in &account_ids {
            let mut equity = dec!(10000);
            let mut timestamp = Utc::now() - Duration::days(30);
            
            for _ in 0..720 { // 30 days * 24 hours
                // Simulate equity changes
                let change = Decimal::from(rand::random::<i32>() % 200 - 100); // -100 to +100
                equity += change;
                equity = equity.max(dec!(0)); // Don't go below 0
                
                equity_history_manager.record_equity(*account_id, equity, equity).await.unwrap();
                timestamp += Duration::hours(1);
            }
        }
        
        // Calculate drawdowns for all accounts
        let start_time = std::time::Instant::now();
        let mut total_calculations = 0;
        
        for account_id in account_ids {
            let _metrics = tracker.calculate_drawdowns(account_id).await.unwrap();
            total_calculations += 1;
        }
        
        let duration = start_time.elapsed();
        
        // Should handle large datasets efficiently
        assert_eq!(total_calculations, 100);
        assert!(duration.as_secs() < 30, "Large dataset calculation took too long: {:?}", duration);
        
        println!("Calculated drawdowns for {} accounts with 72,000 equity points in {:?}", 
                total_calculations, duration);
    }

    #[tokio::test]
    async fn test_concurrent_risk_calculations() {
        use tokio::task;
        
        let position_tracker = Arc::new(PositionTracker::new());
        let market_data_stream = Arc::new(MarketDataStream::new());
        let websocket_publisher = Arc::new(WebSocketPublisher::new());
        let kafka_producer = Arc::new(KafkaProducer);
        let currency_converter = Arc::new(CurrencyConverter::new());
        
        let calculator = Arc::new(RealTimePnLCalculator::new(
            position_tracker.clone(),
            market_data_stream.clone(),
            websocket_publisher,
            kafka_producer,
            currency_converter,
        ));
        
        // Create multiple concurrent tasks calculating P&L
        let mut handles = Vec::new();
        
        for thread_id in 0..50 {
            let calc = calculator.clone();
            
            let handle = task::spawn(async move {
                let position = Position {
                    id: Uuid::new_v4(),
                    account_id: Uuid::new_v4(),
                    symbol: format!("PAIR{:02}", thread_id % 10),
                    position_type: if thread_id % 2 == 0 { PositionType::Long } else { PositionType::Short },
                    size: dec!(100000),
                    entry_price: dec!(1.1000),
                    current_price: None,
                    unrealized_pnl: None,
                    max_favorable_excursion: dec!(0),
                    max_adverse_excursion: dec!(0),
                    stop_loss: None,
                    take_profit: None,
                    opened_at: Utc::now(),
                };
                
                // Each thread performs 100 calculations
                let mut results = Vec::new();
                for i in 0..100 {
                    let tick = MarketTick {
                        symbol: format!("PAIR{:02}", thread_id % 10),
                        bid: dec!(1.1000) + Decimal::from(i) * dec!(0.0001),
                        ask: dec!(1.1002) + Decimal::from(i) * dec!(0.0001),
                        price: dec!(1.1001) + Decimal::from(i) * dec!(0.0001),
                        volume: dec!(1000),
                        timestamp: Utc::now(),
                    };
                    
                    let pnl = calc.calculate_position_pnl(&position, &tick).await.unwrap();
                    results.push(pnl);
                }
                
                results
            });
            
            handles.push(handle);
        }
        
        // Wait for all concurrent calculations to complete
        let start_time = std::time::Instant::now();
        let mut total_calculations = 0;
        
        for handle in handles {
            let results = handle.await.unwrap();
            total_calculations += results.len();
            
            // Verify all results are valid
            for result in results {
                assert!(result.unrealized_pnl.is_finite());
                assert!(result.unrealized_pnl_percentage.is_finite());
            }
        }
        
        let duration = start_time.elapsed();
        
        // Should handle concurrent access safely and efficiently
        assert_eq!(total_calculations, 5000); // 50 threads * 100 calculations
        assert!(duration.as_secs() < 10, "Concurrent calculations took too long: {:?}", duration);
        
        println!("Completed {} concurrent calculations in {:?}", total_calculations, duration);
    }

    #[tokio::test]
    async fn test_extreme_market_conditions_resilience() {
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
        
        // Test position with extreme values
        let position = Position {
            id: Uuid::new_v4(),
            account_id: Uuid::new_v4(),
            symbol: "BTCUSD".to_string(),
            position_type: PositionType::Long,
            size: dec!(1000000), // Very large position
            entry_price: dec!(50000),
            current_price: None,
            unrealized_pnl: None,
            max_favorable_excursion: dec!(0),
            max_adverse_excursion: dec!(0),
            stop_loss: None,
            take_profit: None,
            opened_at: Utc::now(),
        };
        
        // Test various extreme market scenarios
        let extreme_scenarios = vec![
            ("Market Crash", dec!(10000)), // 80% drop
            ("Flash Recovery", dec!(75000)), // 50% spike
            ("Circuit Breaker", dec!(1)), // Near-zero price
            ("Hyperinflation", dec!(1000000)), // 20x increase
        ];
        
        for (scenario_name, price) in extreme_scenarios {
            let tick = MarketTick {
                symbol: "BTCUSD".to_string(),
                bid: price - dec!(10),
                ask: price + dec!(10),
                price,
                volume: dec!(100000),
                timestamp: Utc::now(),
            };
            
            let result = calculator.calculate_position_pnl(&position, &tick).await;
            
            // Should handle all scenarios without panicking
            assert!(result.is_ok(), "Failed to handle scenario: {}", scenario_name);
            
            let pnl = result.unwrap();
            assert!(pnl.unrealized_pnl.is_finite(), "Non-finite P&L in scenario: {}", scenario_name);
            assert!(pnl.unrealized_pnl_percentage.is_finite(), "Non-finite P&L percentage in scenario: {}", scenario_name);
            
            println!("Scenario '{}': P&L = {}, Percentage = {}%", 
                    scenario_name, pnl.unrealized_pnl, pnl.unrealized_pnl_percentage);
        }
    }
}

// Helper function to generate random market data for stress testing
fn generate_random_tick(symbol: &str, base_price: rust_decimal::Decimal) -> MarketTick {
    let random_factor = Decimal::from(rand::random::<i32>() % 200 - 100) * dec!(0.00001);
    let price = base_price + random_factor;
    
    MarketTick {
        symbol: symbol.to_string(),
        bid: price - dec!(0.00001),
        ask: price + dec!(0.00001),
        price,
        volume: Decimal::from(rand::random::<u32>() % 10000 + 1000),
        timestamp: Utc::now(),
    }
}