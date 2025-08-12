/// Simple integration test for exit management system
/// Tests basic compilation and instantiation without complex mocking

use std::sync::Arc;
use execution_engine::execution::exit_management::{
    ExitManagementIntegration,
    TrailingConfig,
    BreakEvenConfig,
    PartialProfitConfig,
    TimeExitConfig,
    NewsProtectionConfig,
};
use execution_engine::execution::MockTradingPlatform;

#[tokio::test]
async fn test_exit_management_system_creation() {
    // Create a mock platform
    let platform = Arc::new(MockTradingPlatform::new("test_platform"));
    
    // Create exit management system
    let exit_management_result = ExitManagementIntegration::create_with_platform(platform);
    assert!(exit_management_result.is_ok(), "Should create exit management system successfully");
    
    let exit_management = exit_management_result.unwrap();
    
    // Test that the system was created successfully
    assert!(exit_management.is_enabled(), "Exit management should be enabled by default");
    
    println!("✓ Exit management system created and configured successfully");
}

#[tokio::test]
async fn test_exit_management_components_creation() {
    let platform = Arc::new(MockTradingPlatform::new("config_test_platform"));
    
    // Test components creation
    let components_result = ExitManagementIntegration::create_components(platform);
    assert!(components_result.is_ok(), "Should create components successfully");
    
    let components = components_result.unwrap();
    
    // Test that we can get individual managers
    let trailing_manager = components.trailing_stop_manager;
    let break_even_manager = components.break_even_manager;
    let partial_profit_manager = components.partial_profit_manager;
    let time_exit_manager = components.time_exit_manager;
    let news_protection = components.news_protection;
    let exit_logger = components.exit_logger;
    
    // Verify we can access the individual components
    // (This is a basic test that the components were successfully created)
    
    // Test building exit management system from components
    let exit_management = components.build();
    assert!(exit_management.is_enabled(), "Built system should be enabled");
    
    println!("✓ All exit management components created successfully");
}

#[tokio::test]
async fn test_exit_management_with_failing_platform() {
    // Create a platform configured to fail
    let failing_platform = Arc::new(MockTradingPlatform::with_failure("failing_platform"));
    
    // System should still create successfully
    let exit_management_result = ExitManagementIntegration::create_with_platform(failing_platform);
    assert!(exit_management_result.is_ok(), "Should create system even with failing platform");
    
    // Test that system can be enabled/disabled
    let mut exit_management = exit_management_result.unwrap();
    exit_management.disable();
    assert!(!exit_management.is_enabled(), "System should be disabled");
    
    exit_management.enable();
    assert!(exit_management.is_enabled(), "System should be enabled");
    
    println!("✓ Exit management system handles failing platforms gracefully");
}

#[tokio::test]
async fn test_exit_management_adapter_creation() {
    // Test that we can create the adapter and integration components
    let platform = Arc::new(MockTradingPlatform::new("adapter_test"));
    
    let components_result = ExitManagementIntegration::create_components(platform.clone());
    assert!(components_result.is_ok(), "Should create exit management components");
    
    let components = components_result.unwrap();
    
    // Verify components were created (Arc references are not null by definition)
    // Test that we can build a system from components
    let exit_management = components.build();
    assert!(exit_management.is_enabled(), "System built from components should be enabled");
    
    println!("✓ All exit management components created successfully");
}

#[tokio::test]  
async fn test_exit_management_performance() {
    let platform = Arc::new(MockTradingPlatform::new("performance_test"));
    
    // Measure system creation time
    let start = std::time::Instant::now();
    let exit_management = ExitManagementIntegration::create_with_platform(platform).unwrap();
    let creation_time = start.elapsed();
    
    // System creation should be fast
    assert!(creation_time.as_millis() < 1000, "System creation should complete within 1 second");
    
    // Test basic system operations
    assert!(exit_management.is_enabled(), "System should be enabled by default");
    
    println!("✓ Exit management system performance tests passed");
    println!("  - Creation time: {:?}", creation_time);
}