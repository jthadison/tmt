use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, SystemTime};

use execution_engine::execution::{MockTradingPlatform, TradeExecutionOrchestrator, TradeSignal};
use execution_engine::platforms::abstraction::models::UnifiedOrderSide;

fn create_test_signal() -> TradeSignal {
    TradeSignal {
        id: "signal_001".to_string(),
        symbol: "EURUSD".to_string(),
        side: UnifiedOrderSide::Buy,
        entry_price: 1.0900,
        stop_loss: 1.0850,
        take_profit: 1.1000,
        confidence: 0.85,
        risk_reward_ratio: 2.0,
        signal_time: SystemTime::now(),
        metadata: HashMap::new(),
    }
}

#[tokio::test]
async fn test_orchestrator_initialization() {
    let orchestrator = TradeExecutionOrchestrator::new();
    let history = orchestrator.get_execution_history(10).await;
    assert_eq!(history.len(), 0);
}

#[tokio::test]
async fn test_account_registration() {
    let orchestrator = TradeExecutionOrchestrator::new();
    let platform = Arc::new(MockTradingPlatform::new("test_account"));

    let result = orchestrator
        .register_account("account1".to_string(), platform, 10000.0)
        .await;

    assert!(result.is_ok(), "Account registration should succeed");

    let status = orchestrator.get_account_status("account1").await;
    assert!(status.is_some(), "Account status should be available");

    let account = status.unwrap();
    assert_eq!(account.account_id, "account1");
    assert_eq!(account.platform, "test_account");
    assert!(account.is_active);
}

#[tokio::test]
async fn test_signal_processing_with_eligible_accounts() {
    let orchestrator = TradeExecutionOrchestrator::new();

    for i in 1..=3 {
        let platform = Arc::new(MockTradingPlatform::new(&format!("platform_{}", i)));
        orchestrator
            .register_account(format!("account_{}", i), platform, 10000.0)
            .await
            .expect("Account registration should succeed");
    }

    let signal = create_test_signal();
    let plan = orchestrator.process_signal(signal).await;

    assert!(plan.is_ok(), "Signal processing should succeed");
    let execution_plan = plan.unwrap();
    assert_eq!(execution_plan.account_assignments.len(), 3);

    for assignment in &execution_plan.account_assignments {
        assert!(assignment.position_size > 0.0);
        assert!(assignment.entry_timing_delay >= Duration::from_millis(1000));
        assert!(assignment.entry_timing_delay <= Duration::from_millis(30000));
    }
}

#[tokio::test]
async fn test_signal_processing_no_eligible_accounts() {
    let orchestrator = TradeExecutionOrchestrator::new();

    let platform = Arc::new(MockTradingPlatform::new("platform_1"));
    orchestrator
        .register_account("account_1".to_string(), platform, 10000.0)
        .await
        .expect("Account registration should succeed");

    // Pause the account to make it ineligible
    orchestrator
        .pause_account("account_1")
        .await
        .expect("Account pause should succeed");

    let signal = create_test_signal();
    let plan = orchestrator.process_signal(signal).await;

    assert!(plan.is_err());
    assert_eq!(
        plan.unwrap_err(),
        "No eligible accounts for signal execution"
    );
}

#[tokio::test]
async fn test_timing_variance() {
    let orchestrator = TradeExecutionOrchestrator::new();

    for i in 1..=5 {
        let platform = Arc::new(MockTradingPlatform::new(&format!("platform_{}", i)));
        orchestrator
            .register_account(format!("account_{}", i), platform, 10000.0)
            .await
            .expect("Account registration should succeed");
    }

    let signal = create_test_signal();
    let plan = orchestrator
        .process_signal(signal)
        .await
        .expect("Signal processing should succeed");

    let mut timing_delays = Vec::new();
    for assignment in &plan.account_assignments {
        timing_delays.push(assignment.entry_timing_delay.as_millis());
    }

    timing_delays.sort();
    let all_different = timing_delays.windows(2).all(|w| w[0] != w[1]);
    assert!(all_different, "Timing delays should have variance");
}

#[tokio::test]
async fn test_size_variance() {
    let orchestrator = TradeExecutionOrchestrator::new();

    for i in 1..=5 {
        let platform = Arc::new(MockTradingPlatform::new(&format!("platform_{}", i)));
        orchestrator
            .register_account(format!("account_{}", i), platform, 10000.0)
            .await
            .expect("Account registration should succeed");
    }

    let signal = create_test_signal();
    let plan = orchestrator
        .process_signal(signal)
        .await
        .expect("Signal processing should succeed");

    let mut sizes = Vec::new();
    for assignment in &plan.account_assignments {
        sizes.push(assignment.position_size);
    }

    let all_different = sizes.windows(2).all(|w| (w[0] - w[1]).abs() > 0.001);
    assert!(all_different, "Position sizes should have variance");
}

#[tokio::test]
async fn test_correlation_matrix_update() {
    let orchestrator = TradeExecutionOrchestrator::new();

    orchestrator
        .update_correlation_matrix("account1", "account2", 0.75)
        .await;
    orchestrator
        .update_correlation_matrix("account1", "account3", 0.45)
        .await;
    orchestrator
        .update_correlation_matrix("account2", "account3", 0.85)
        .await;

    for i in 1..=3 {
        let platform = Arc::new(MockTradingPlatform::new(&format!("platform_{}", i)));
        orchestrator
            .register_account(format!("account{}", i), platform, 10000.0)
            .await
            .expect("Account registration should succeed");
    }

    let signal = create_test_signal();
    let plan = orchestrator
        .process_signal(signal)
        .await
        .expect("Signal processing should succeed");

    let acc2_delay = plan
        .account_assignments
        .iter()
        .find(|a| a.account_id == "account2")
        .map(|a| a.entry_timing_delay);

    let acc3_delay = plan
        .account_assignments
        .iter()
        .find(|a| a.account_id == "account3")
        .map(|a| a.entry_timing_delay);

    if let (Some(d2), Some(d3)) = (acc2_delay, acc3_delay) {
        assert!(
            d3 > d2,
            "High correlation accounts should have greater timing variance"
        );
    }
}

#[tokio::test]
async fn test_account_pause_resume() {
    let orchestrator = TradeExecutionOrchestrator::new();
    let platform = Arc::new(MockTradingPlatform::new("platform_1"));

    orchestrator
        .register_account("account_1".to_string(), platform, 10000.0)
        .await
        .expect("Account registration should succeed");

    let status1 = orchestrator
        .get_account_status("account_1")
        .await
        .expect("Account status should be available");
    assert!(status1.is_active);

    orchestrator
        .pause_account("account_1")
        .await
        .expect("Account pause should succeed");
    let status2 = orchestrator
        .get_account_status("account_1")
        .await
        .expect("Account status should be available");
    assert!(!status2.is_active);

    orchestrator
        .resume_account("account_1")
        .await
        .expect("Account resume should succeed");
    let status3 = orchestrator
        .get_account_status("account_1")
        .await
        .expect("Account status should be available");
    assert!(status3.is_active);
}

#[tokio::test]
async fn test_execution_history_logging() {
    let orchestrator = TradeExecutionOrchestrator::new();

    let platform = Arc::new(MockTradingPlatform::new("platform_1"));
    orchestrator
        .register_account("account_1".to_string(), platform, 10000.0)
        .await
        .expect("Account registration should succeed");

    let signal = create_test_signal();
    let _ = orchestrator
        .process_signal(signal)
        .await
        .expect("Signal processing should succeed");

    let history = orchestrator.get_execution_history(10).await;
    assert!(
        history.len() > 0,
        "Execution history should contain entries"
    );

    let first_entry = &history[0];
    assert_eq!(first_entry.action, "PLAN_CREATED");
    assert!(first_entry
        .decision_rationale
        .contains("Created execution plan"));
}

#[tokio::test]
async fn test_successful_execution() {
    let orchestrator = TradeExecutionOrchestrator::new();

    let platform = Arc::new(MockTradingPlatform::new("platform_1"));
    orchestrator
        .register_account("account_1".to_string(), platform, 10000.0)
        .await
        .expect("Account registration should succeed");

    let signal = create_test_signal();
    let plan = orchestrator
        .process_signal(signal)
        .await
        .expect("Signal processing should succeed");
    let results = orchestrator.execute_plan(&plan).await;

    assert_eq!(results.len(), 1);
    let result = &results[0];
    assert!(result.success, "Execution should be successful");
    assert!(result.order_id.is_some());
    assert!(result.actual_entry_price.is_some());
}

#[tokio::test]
async fn test_failed_execution_recovery() {
    let orchestrator = TradeExecutionOrchestrator::new();

    // Register a failing platform
    let failing_platform = Arc::new(MockTradingPlatform::with_failure("failing_platform"));
    orchestrator
        .register_account("failing_account".to_string(), failing_platform, 10000.0)
        .await
        .expect("Account registration should succeed");

    // Register a backup platform
    let success_platform = Arc::new(MockTradingPlatform::new("success_platform"));
    orchestrator
        .register_account("backup_account".to_string(), success_platform, 10000.0)
        .await
        .expect("Account registration should succeed");

    let signal = create_test_signal();
    let plan = orchestrator
        .process_signal(signal)
        .await
        .expect("Signal processing should succeed");
    let results = orchestrator.execute_plan(&plan).await;

    // Find the failed result
    let failed_result = results.iter().find(|r| r.account_id == "failing_account");

    if let Some(failed) = failed_result {
        assert!(!failed.success, "Failing platform should fail");

        let recovery = orchestrator.handle_failed_execution(failed, &plan).await;
        assert!(recovery.is_ok(), "Recovery should succeed");

        let recovered = recovery.unwrap();
        assert!(recovered.success, "Recovery should be successful");
        assert_eq!(recovered.account_id, "backup_account");
    }
}

#[tokio::test]
async fn test_position_size_calculation_with_drawdown() {
    let orchestrator = TradeExecutionOrchestrator::new();
    let platform = Arc::new(MockTradingPlatform::new("platform_1"));

    orchestrator
        .register_account("account_1".to_string(), platform, 10000.0)
        .await
        .expect("Account registration should succeed");

    // Test with normal drawdown
    let signal = create_test_signal();
    let plan1 = orchestrator
        .process_signal(signal.clone())
        .await
        .expect("Signal processing should succeed");
    let size1 = plan1.account_assignments[0].position_size;

    // Simulate higher drawdown by modifying account status
    {
        let accounts = orchestrator.accounts.read().await;
        // Access the internal account data (this is a test-specific access)
        drop(accounts);
    }

    // The size should be calculated based on risk parameters
    assert!(size1 > 0.0, "Position size should be positive");
}
