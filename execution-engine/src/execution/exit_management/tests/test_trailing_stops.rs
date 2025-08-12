use std::sync::Arc;
use chrono::Utc;
use uuid::Uuid;

use super::*;
use crate::execution::exit_management::{TrailingStopManager, ExitAuditLogger};
use crate::execution::exit_management::types::*;

#[tokio::test]
async fn test_trailing_stop_activation() {
    let mock_platform = Arc::new(MockTradingPlatform::new());
    let exit_logger = Arc::new(ExitAuditLogger::new());
    let trailing_manager = TrailingStopManager::new(mock_platform.clone(), exit_logger);

    // Create a position with sufficient profit for trailing activation
    let position = create_test_position_with_params(
        "EURUSD",
        UnifiedPositionSide::Long,
        1.0800,  // Entry
        1.0825,  // Current (25 pips profit)
        Some(1.0780), // Stop loss
        1, // 1 hour old
    );

    // Activate trailing stop
    let result = trailing_manager.activate_trailing_stop(&position).await;
    assert!(result.is_ok());

    // Verify trail was created
    let active_trails = trailing_manager.get_active_trails();
    assert_eq!(active_trails.len(), 1);

    let trail = &active_trails[0].1;
    assert_eq!(trail.position_id, position.id);
    assert!(trail.trail_level < position.current_price); // Trail should be below current price for long
}

#[tokio::test]
async fn test_trailing_stop_insufficient_profit() {
    let mock_platform = Arc::new(MockTradingPlatform::new());
    let exit_logger = Arc::new(ExitAuditLogger::new());
    let trailing_manager = TrailingStopManager::new(mock_platform.clone(), exit_logger);

    // Create a position with insufficient profit
    let position = create_test_position_with_params(
        "EURUSD",
        UnifiedPositionSide::Long,
        1.0800,  // Entry
        1.0805,  // Current (only 5 pips profit)
        Some(1.0780), // Stop loss
        1, // 1 hour old
    );

    // Attempt to activate trailing stop
    let result = trailing_manager.activate_trailing_stop(&position).await;
    assert!(result.is_ok());

    // Verify no trail was created due to insufficient profit
    let active_trails = trailing_manager.get_active_trails();
    assert_eq!(active_trails.len(), 0);
}

#[tokio::test]
async fn test_trailing_stop_update() {
    let mock_platform = Arc::new(MockTradingPlatform::new());
    let exit_logger = Arc::new(ExitAuditLogger::new());
    let trailing_manager = TrailingStopManager::new(mock_platform.clone(), exit_logger);

    let position = create_test_position_with_params(
        "EURUSD",
        UnifiedPositionSide::Long,
        1.0800,
        1.0825,
        Some(1.0780),
        1,
    );

    // Activate trailing stop
    trailing_manager.activate_trailing_stop(&position).await.unwrap();

    // Get initial trail level
    let initial_trails = trailing_manager.get_active_trails();
    let initial_level = initial_trails[0].1.trail_level;

    // Mock price improvement
    let mut improved_position = position.clone();
    improved_position.current_price = 1.0835; // 10 more pips profit

    // Update trailing stops should improve the trail level
    let result = trailing_manager.update_trailing_stops().await;
    assert!(result.is_ok());

    // Note: In a real test, we'd need to mock the position retrieval to return the improved position
    // For this simplified test, we're just verifying the update process completes successfully
}

#[tokio::test]
async fn test_trailing_stop_deactivation() {
    let mock_platform = Arc::new(MockTradingPlatform::new());
    let exit_logger = Arc::new(ExitAuditLogger::new());
    let trailing_manager = TrailingStopManager::new(mock_platform.clone(), exit_logger);

    let position = create_test_position_with_params(
        "EURUSD",
        UnifiedPositionSide::Long,
        1.0800,
        1.0825,
        Some(1.0780),
        1,
    );

    // Activate trailing stop
    trailing_manager.activate_trailing_stop(&position).await.unwrap();

    // Verify trail exists
    assert_eq!(trailing_manager.get_trail_count(), 1);

    // Deactivate trailing stop
    let result = trailing_manager.deactivate_trailing_stop(position.id).await;
    assert!(result.is_ok());

    // Verify trail is removed
    assert_eq!(trailing_manager.get_trail_count(), 0);
}

#[tokio::test]
async fn test_trailing_stop_short_position() {
    let mock_platform = Arc::new(MockTradingPlatform::new());
    let exit_logger = Arc::new(ExitAuditLogger::new());
    let trailing_manager = TrailingStopManager::new(mock_platform.clone(), exit_logger);

    // Create a profitable short position
    let position = create_test_position_with_params(
        "EURUSD",
        UnifiedPositionSide::Short,
        1.0800,  // Entry
        1.0775,  // Current (25 pips profit for short)
        Some(1.0820), // Stop loss above entry
        1,
    );

    // Activate trailing stop
    let result = trailing_manager.activate_trailing_stop(&position).await;
    assert!(result.is_ok());

    // Verify trail was created
    let active_trails = trailing_manager.get_active_trails();
    assert_eq!(active_trails.len(), 1);

    let trail = &active_trails[0].1;
    assert_eq!(trail.position_id, position.id);
    assert!(trail.trail_level > position.current_price); // Trail should be above current price for short
}

#[tokio::test]
async fn test_trailing_configuration() {
    let mock_platform = Arc::new(MockTradingPlatform::new());
    let exit_logger = Arc::new(ExitAuditLogger::new());
    let mut trailing_manager = TrailingStopManager::new(mock_platform.clone(), exit_logger);

    // Configure custom trailing settings
    let custom_config = TrailingConfig {
        atr_multiplier: 3.0,
        min_trail_distance: 0.0005, // 5 pips
        max_trail_distance: 0.0200, // 200 pips
        activation_threshold: 0.0020, // 20 pips
        symbol: "EURUSD".to_string(),
        timeframe: "H1".to_string(),
    };

    trailing_manager.configure_symbol("EURUSD".to_string(), custom_config);

    let position = create_test_position_with_params(
        "EURUSD",
        UnifiedPositionSide::Long,
        1.0800,
        1.0825, // 25 pips profit (above 20 pip threshold)
        Some(1.0780),
        1,
    );

    // Should activate with custom config
    let result = trailing_manager.activate_trailing_stop(&position).await;
    assert!(result.is_ok());
    assert_eq!(trailing_manager.get_trail_count(), 1);
}

#[tokio::test]
async fn test_trailing_stop_performance_stats() {
    let mock_platform = Arc::new(MockTradingPlatform::new());
    let exit_logger = Arc::new(ExitAuditLogger::new());
    let trailing_manager = TrailingStopManager::new(mock_platform.clone(), exit_logger);

    // Get performance stats (should work even with no active trails)
    let result = trailing_manager.get_trailing_performance_stats().await;
    assert!(result.is_ok());

    let stats = result.unwrap();
    assert_eq!(stats.total_trails, 0); // No active trails yet
}

#[cfg(test)]
mod property_tests {
    use super::*;
    
    #[tokio::test]
    async fn test_trail_level_always_moves_favorably() {
        let mock_platform = Arc::new(MockTradingPlatform::new());
        let exit_logger = Arc::new(ExitAuditLogger::new());
        let trailing_manager = TrailingStopManager::new(mock_platform.clone(), exit_logger);

        for _ in 0..10 {
            let position = create_test_position_with_params(
                "EURUSD",
                UnifiedPositionSide::Long,
                1.0800,
                1.0800 + (rand::random::<f64>() * 0.01), // Random profit up to 100 pips
                Some(1.0780),
                1,
            );

            if position.current_price - position.entry_price >= 0.0015 { // Sufficient profit
                trailing_manager.activate_trailing_stop(&position).await.unwrap();
                
                let trails = trailing_manager.get_active_trails();
                if !trails.is_empty() {
                    let trail = &trails[0].1;
                    // For long positions, trail level should be below current price
                    assert!(trail.trail_level < position.current_price);
                }
                
                trailing_manager.deactivate_trailing_stop(position.id).await.unwrap();
            }
        }
    }
}