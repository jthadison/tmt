use std::sync::Arc;
use super::*;
use crate::execution::exit_management::{BreakEvenManager, ExitAuditLogger};
use crate::execution::exit_management::types::*;

#[tokio::test]
async fn test_break_even_trigger_detection() {
    let mock_platform = Arc::new(MockTradingPlatform::new());
    let exit_logger = Arc::new(ExitAuditLogger::new());
    let break_even_manager = BreakEvenManager::new(mock_platform.clone(), exit_logger);

    // Create a position at 1:1 R:R (break-even should trigger)
    let position = create_test_position_with_params(
        "EURUSD",
        UnifiedPositionSide::Long,
        1.0800,  // Entry
        1.0820,  // Current (+20 pips)
        Some(1.0780), // Stop (-20 pips), so 1:1 R:R
        1,
    );

    // Check if break-even should trigger
    let result = break_even_manager.check_break_even_triggers().await;
    assert!(result.is_ok());

    // Verify break-even logic
    let validation = break_even_manager.validate_break_even_logic(&position).await.unwrap();
    assert!(validation.is_valid);
    assert!(validation.risk_reward_ratio >= 1.0);
}

#[tokio::test]
async fn test_break_even_insufficient_profit() {
    let mock_platform = Arc::new(MockTradingPlatform::new());
    let exit_logger = Arc::new(ExitAuditLogger::new());
    let break_even_manager = BreakEvenManager::new(mock_platform.clone(), exit_logger);

    // Create a position with insufficient profit for break-even
    let position = create_test_position_with_params(
        "EURUSD",
        UnifiedPositionSide::Long,
        1.0800,  // Entry
        1.0810,  // Current (+10 pips)
        Some(1.0780), // Stop (-20 pips), so only 0.5:1 R:R
        1,
    );

    let validation = break_even_manager.validate_break_even_logic(&position).await.unwrap();
    assert!(!validation.is_valid);
    assert!(validation.risk_reward_ratio < 1.0);
}

#[tokio::test]
async fn test_break_even_short_position() {
    let mock_platform = Arc::new(MockTradingPlatform::new());
    let exit_logger = Arc::new(ExitAuditLogger::new());
    let break_even_manager = BreakEvenManager::new(mock_platform.clone(), exit_logger);

    // Create a profitable short position at 1:1 R:R
    let position = create_test_position_with_params(
        "EURUSD",
        UnifiedPositionSide::Short,
        1.0800,  // Entry
        1.0780,  // Current (-20 pips profit for short)
        Some(1.0820), // Stop (+20 pips risk), so 1:1 R:R
        1,
    );

    let validation = break_even_manager.validate_break_even_logic(&position).await.unwrap();
    assert!(validation.is_valid);
    assert!(validation.risk_reward_ratio >= 1.0);
}

#[tokio::test]
async fn test_break_even_no_stop_loss() {
    let mock_platform = Arc::new(MockTradingPlatform::new());
    let exit_logger = Arc::new(ExitAuditLogger::new());
    let break_even_manager = BreakEvenManager::new(mock_platform.clone(), exit_logger);

    // Position without stop loss
    let position = create_test_position_with_params(
        "EURUSD",
        UnifiedPositionSide::Long,
        1.0800,
        1.0820,
        None, // No stop loss
        1,
    );

    let validation = break_even_manager.validate_break_even_logic(&position).await.unwrap();
    assert!(!validation.is_valid);
    assert_eq!(validation.reason, "No stop loss set");
}

#[tokio::test]
async fn test_break_even_tracking() {
    let mock_platform = Arc::new(MockTradingPlatform::new());
    let exit_logger = Arc::new(ExitAuditLogger::new());
    let break_even_manager = BreakEvenManager::new(mock_platform.clone(), exit_logger);

    let position_id = Uuid::new_v4();

    // Initially not break-even
    assert!(!break_even_manager.is_break_even_active(position_id));

    // Force break-even would need the position to exist in the platform
    // This test demonstrates the tracking functionality
    assert_eq!(break_even_manager.get_break_even_count(), 0);
}

#[tokio::test]
async fn test_break_even_stats() {
    let mock_platform = Arc::new(MockTradingPlatform::new());
    let exit_logger = Arc::new(ExitAuditLogger::new());
    let break_even_manager = BreakEvenManager::new(mock_platform.clone(), exit_logger);

    let result = break_even_manager.get_break_even_stats().await;
    assert!(result.is_ok());

    let stats = result.unwrap();
    assert_eq!(stats.break_even_activations, 0); // No active break-evens
}

#[tokio::test]
async fn test_break_even_configuration() {
    let mock_platform = Arc::new(MockTradingPlatform::new());
    let exit_logger = Arc::new(ExitAuditLogger::new());
    let mut break_even_manager = BreakEvenManager::new(mock_platform.clone(), exit_logger);

    let custom_config = BreakEvenConfig {
        trigger_ratio: 1.5, // Require 1.5:1 R:R instead of 1:1
        break_even_buffer_pips: 10.0, // 10 pip buffer
        enabled: true,
    };

    break_even_manager.configure_symbol("EURUSD".to_string(), custom_config);

    // Test with the custom configuration
    let position = create_test_position_with_params(
        "EURUSD",
        UnifiedPositionSide::Long,
        1.0800,  // Entry
        1.0820,  // Current (+20 pips)
        Some(1.0780), // Stop (-20 pips), so 1:1 R:R
        1,
    );

    let validation = break_even_manager.validate_break_even_logic(&position).await.unwrap();
    // Should not be valid because we need 1.5:1 but only have 1:1
    assert!(!validation.is_valid);
}