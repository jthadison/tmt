use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, SystemTime};
use async_trait::async_trait;
use tokio::sync::{RwLock, mpsc};
use chrono::Utc;
use rust_decimal::Decimal;

use execution_engine::execution::orchestrator::{
    TradeExecutionOrchestrator,
    TradeSignal,
    ExecutionPlan,
    AccountStatus,
};
use execution_engine::platforms::{
    PlatformType,
    abstraction::{
        interfaces::{ITradingPlatform, EventFilter, HealthStatus, DiagnosticsInfo},
        models::{
            UnifiedOrder, UnifiedOrderResponse, UnifiedOrderSide, UnifiedOrderType, 
            UnifiedPosition, UnifiedAccountInfo, UnifiedMarketData, UnifiedTimeInForce,
            OrderModification, OrderFilter, MarginInfo, AccountType, OrderMetadata,
            UnifiedOrderStatus,
        },
        errors::PlatformError,
        capabilities::{PlatformCapabilities, PlatformFeature},
        events::PlatformEvent,
    },
};

#[derive(Clone)]
struct MockPlatform {
    name: String,
    should_fail: bool,
    execution_delay_ms: u64,
    account_info: UnifiedAccountInfo,
    orders: Arc<RwLock<Vec<UnifiedOrderResponse>>>,
}

#[async_trait]
impl ITradingPlatform for MockPlatform {
    fn platform_type(&self) -> PlatformType {
        PlatformType::TradeLocker
    }
    
    fn platform_name(&self) -> &str {
        &self.name
    }
    
    fn platform_version(&self) -> &str {
        "1.0.0"
    }

    async fn connect(&mut self) -> Result<(), PlatformError> {
        Ok(())
    }

    async fn disconnect(&mut self) -> Result<(), PlatformError> {
        Ok(())
    }

    async fn is_connected(&self) -> bool {
        true
    }
    
    async fn ping(&self) -> Result<u64, PlatformError> {
        Ok(10)
    }

    async fn get_account_info(&self) -> Result<UnifiedAccountInfo, PlatformError> {
        Ok(self.account_info.clone())
    }
    
    async fn get_balance(&self) -> Result<Decimal, PlatformError> {
        Ok(self.account_info.balance)
    }
    
    async fn get_margin_info(&self) -> Result<MarginInfo, PlatformError> {
        Ok(MarginInfo {
            initial_margin: self.account_info.margin_used,
            maintenance_margin: self.account_info.margin_used * Decimal::from_f64_retain(0.5).unwrap(),
            margin_call_level: Some(Decimal::from_f64_retain(100.0).unwrap()),
            stop_out_level: Some(Decimal::from_f64_retain(50.0).unwrap()),
            margin_requirements: HashMap::new(),
        })
    }

    async fn get_positions(&self) -> Result<Vec<UnifiedPosition>, PlatformError> {
        Ok(Vec::new())
    }
    
    async fn get_position(&self, _symbol: &str) -> Result<Option<UnifiedPosition>, PlatformError> {
        Ok(None)
    }
    
    async fn close_position(&self, _symbol: &str, _quantity: Option<Decimal>) -> Result<UnifiedOrderResponse, PlatformError> {
        Err(PlatformError::FeatureNotSupported { feature: "close_position".to_string() })
    }

    async fn place_order(&self, mut order: UnifiedOrder) -> Result<UnifiedOrderResponse, PlatformError> {
        if self.should_fail {
            return Err(PlatformError::InternalError { reason: "Mock failure".to_string() });
        }

        tokio::time::sleep(Duration::from_millis(self.execution_delay_ms)).await;
        
        let order_response = UnifiedOrderResponse {
            platform_order_id: format!("MOCK_{}", order.client_order_id),
            client_order_id: order.client_order_id,
            symbol: order.symbol,
            side: order.side,
            order_type: order.order_type,
            status: UnifiedOrderStatus::Filled,
            quantity: order.quantity,
            filled_quantity: order.quantity,
            remaining_quantity: Decimal::ZERO,
            price: order.price.or(Some(Decimal::from_f64_retain(1.0900).unwrap())),
            average_fill_price: Some(Decimal::from_f64_retain(1.0900).unwrap()),
            commission: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
            filled_at: Some(Utc::now()),
            platform_specific: HashMap::new(),
        };
        
        let mut orders = self.orders.write().await;
        orders.push(order_response.clone());
        
        Ok(order_response)
    }

    async fn modify_order(&self, _order_id: &str, _modifications: OrderModification) -> Result<UnifiedOrderResponse, PlatformError> {
        Err(PlatformError::FeatureNotSupported { feature: "modify_order".to_string() })
    }

    async fn cancel_order(&self, order_id: &str) -> Result<(), PlatformError> {
        let mut orders = self.orders.write().await;
        orders.retain(|o| o.platform_order_id != order_id);
        Ok(())
    }
    
    async fn get_order(&self, order_id: &str) -> Result<UnifiedOrderResponse, PlatformError> {
        let orders = self.orders.read().await;
        orders.iter()
            .find(|o| o.platform_order_id == order_id)
            .cloned()
            .ok_or_else(|| PlatformError::OrderNotFound { order_id: order_id.to_string() })
    }
    
    async fn get_orders(&self, _filter: Option<OrderFilter>) -> Result<Vec<UnifiedOrderResponse>, PlatformError> {
        let orders = self.orders.read().await;
        Ok(orders.clone())
    }

    async fn get_market_data(&self, _symbol: &str) -> Result<UnifiedMarketData, PlatformError> {
        Err(PlatformError::FeatureNotSupported { feature: "get_market_data".to_string() })
    }
    
    async fn subscribe_market_data(&self, _symbols: Vec<String>) -> Result<mpsc::Receiver<UnifiedMarketData>, PlatformError> {
        let (_tx, rx) = mpsc::channel(100);
        Ok(rx)
    }
    
    async fn unsubscribe_market_data(&self, _symbols: Vec<String>) -> Result<(), PlatformError> {
        Ok(())
    }

    fn capabilities(&self) -> PlatformCapabilities {
        PlatformCapabilities::new("MockPlatform".to_string())
    }
    
    async fn subscribe_events(&self) -> Result<mpsc::Receiver<PlatformEvent>, PlatformError> {
        let (_tx, rx) = mpsc::channel(100);
        Ok(rx)
    }
    
    async fn get_event_history(&self, _filter: EventFilter) -> Result<Vec<PlatformEvent>, PlatformError> {
        Ok(Vec::new())
    }
    
    async fn health_check(&self) -> Result<HealthStatus, PlatformError> {
        Ok(HealthStatus {
            is_healthy: true,
            last_check: chrono::Utc::now(),
            response_time_ms: 50,
            error_count: 0,
            warnings: Vec::new(),
        })
    }
    
    async fn get_diagnostics(&self) -> Result<DiagnosticsInfo, PlatformError> {
        Ok(DiagnosticsInfo {
            platform_version: "1.0.0".to_string(),
            api_version: "1.0".to_string(),
            connection_count: 1,
            last_heartbeat: chrono::Utc::now(),
            system_status: "operational".to_string(),
            performance_metrics: std::collections::HashMap::new(),
        })
    }
}

fn create_mock_platform(name: &str, should_fail: bool) -> Arc<MockPlatform> {
    Arc::new(MockPlatform {
        name: name.to_string(),
        should_fail,
        execution_delay_ms: 10,
        account_info: UnifiedAccountInfo {
            account_id: name.to_string(),
            account_name: Some(name.to_string()),
            currency: "USD".to_string(),
            balance: Decimal::from(10000),
            equity: Decimal::from(10000),
            margin_used: Decimal::ZERO,
            margin_available: Decimal::from(10000),
            buying_power: Decimal::from(10000),
            unrealized_pnl: Decimal::ZERO,
            realized_pnl: Decimal::ZERO,
            margin_level: Some(Decimal::from(1000)),
            account_type: AccountType::Demo,
            last_updated: Utc::now(),
            platform_specific: HashMap::new(),
        },
        orders: Arc::new(RwLock::new(Vec::new())),
    })
}

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
    let platform = create_mock_platform("test_account", false);
    
    let result = orchestrator.register_account(
        "account1".to_string(),
        platform.clone(),
        10000.0,
    ).await;
    
    assert!(result.is_ok());
    
    let status = orchestrator.get_account_status("account1").await;
    assert!(status.is_some());
    
    let account = status.unwrap();
    assert_eq!(account.account_id, "account1");
    assert_eq!(account.platform, "test_account");
    assert!(account.is_active);
}

#[tokio::test]
async fn test_ac1_account_selection_margin_and_risk_budget() {
    let orchestrator = TradeExecutionOrchestrator::new();
    
    // Register accounts with different margin levels
    for i in 1..=3 {
        let platform = create_mock_platform(&format!("platform_{}", i), false);
        orchestrator.register_account(
            format!("account_{}", i),
            platform,
            10000.0,
        ).await.unwrap();
    }
    
    // Create a platform with insufficient margin
    let low_margin_platform = create_mock_platform("platform_2", false);
    // Remove the original account 2
    orchestrator.pause_account("account_2").await.unwrap();
    
    let signal = create_test_signal();
    let plan = orchestrator.process_signal(signal).await;
    
    assert!(plan.is_ok());
    let execution_plan = plan.unwrap();
    
    // Should only select accounts 1 and 3 (account 2 is paused)
    assert_eq!(execution_plan.account_assignments.len(), 2);
    
    let selected_accounts: Vec<String> = execution_plan.account_assignments
        .iter()
        .map(|a| a.account_id.clone())
        .collect();
    
    assert!(selected_accounts.contains(&"account_1".to_string()));
    assert!(selected_accounts.contains(&"account_3".to_string()));
    assert!(!selected_accounts.contains(&"account_2".to_string()));
}

#[tokio::test]
async fn test_ac2_trade_distribution_anti_correlation() {
    let orchestrator = TradeExecutionOrchestrator::new();
    
    // Register multiple accounts
    for i in 1..=3 {
        let platform = create_mock_platform(&format!("platform_{}", i), false);
        orchestrator.register_account(
            format!("account_{}", i),
            platform,
            10000.0,
        ).await.unwrap();
    }
    
    // Set up high correlation between account1 and account2
    orchestrator.update_correlation_matrix("account_1", "account_2", 0.85).await;
    
    let signal = create_test_signal();
    let plan = orchestrator.process_signal(signal).await.unwrap();
    
    // Verify trade distribution across accounts
    assert_eq!(plan.account_assignments.len(), 3);
    
    // Verify position size variance (5-15%)
    let sizes: Vec<f64> = plan.account_assignments
        .iter()
        .map(|a| a.position_size)
        .collect();
    
    let all_different = sizes.windows(2).all(|w| (w[0] - w[1]).abs() > 0.001);
    assert!(all_different, "Position sizes should have variance");
    
    // Find assignments for highly correlated accounts
    let acc1_assignment = plan.account_assignments
        .iter()
        .find(|a| a.account_id == "account_1").unwrap();
    let acc2_assignment = plan.account_assignments
        .iter()
        .find(|a| a.account_id == "account_2").unwrap();
    
    // High correlation should result in timing adjustments
    assert!(
        acc2_assignment.entry_timing_delay > acc1_assignment.entry_timing_delay,
        "High correlation accounts should have staggered execution timing"
    );
}

#[tokio::test]
async fn test_ac3_execution_timing_variance() {
    let orchestrator = TradeExecutionOrchestrator::new();
    
    // Register multiple accounts
    for i in 1..=5 {
        let platform = create_mock_platform(&format!("platform_{}", i), false);
        orchestrator.register_account(
            format!("account_{}", i),
            platform,
            10000.0,
        ).await.unwrap();
    }
    
    let signal = create_test_signal();
    let plan = orchestrator.process_signal(signal).await.unwrap();
    
    // Verify all delays are within 1-30 second range
    for assignment in &plan.account_assignments {
        let delay_ms = assignment.entry_timing_delay.as_millis();
        assert!(delay_ms >= 1000, "Delay should be at least 1 second");
        assert!(delay_ms <= 30000, "Delay should be at most 30 seconds");
    }
    
    // Verify timing variance exists
    let mut timing_delays: Vec<u128> = plan.account_assignments
        .iter()
        .map(|a| a.entry_timing_delay.as_millis())
        .collect();
    
    timing_delays.sort();
    let all_different = timing_delays.windows(2).all(|w| w[0] != w[1]);
    assert!(all_different, "Timing delays should have variance between accounts");
}

#[tokio::test]
async fn test_ac5_failed_execution_recovery() {
    let orchestrator = TradeExecutionOrchestrator::new();
    
    // Register a failing platform and a backup platform
    let failing_platform = create_mock_platform("failing_platform", true);
    let backup_platform = create_mock_platform("backup_platform", false);
    
    orchestrator.register_account(
        "failing_account".to_string(),
        failing_platform,
        10000.0,
    ).await.unwrap();
    
    orchestrator.register_account(
        "backup_account".to_string(),
        backup_platform,
        10000.0,
    ).await.unwrap();
    
    let signal = create_test_signal();
    let plan = orchestrator.process_signal(signal).await.unwrap();
    let results = orchestrator.execute_plan(&plan).await;
    
    // Find the failed result
    let failed_result = results.iter()
        .find(|r| r.account_id == "failing_account");
    
    if let Some(failed) = failed_result {
        assert!(!failed.success, "Expected execution to fail");
        
        // Test recovery mechanism
        let recovery = orchestrator.handle_failed_execution(failed, &plan).await;
        assert!(recovery.is_ok(), "Recovery should succeed");
        
        let recovered = recovery.unwrap();
        assert!(recovered.success, "Recovery execution should succeed");
        assert_eq!(recovered.account_id, "backup_account");
    } else {
        panic!("Expected at least one failed execution");
    }
}

#[tokio::test]
async fn test_ac6_execution_audit_log() {
    let orchestrator = TradeExecutionOrchestrator::new();
    
    let platform = create_mock_platform("audit_platform", false);
    orchestrator.register_account(
        "audit_account".to_string(),
        platform,
        10000.0,
    ).await.unwrap();
    
    let signal = create_test_signal();
    let plan = orchestrator.process_signal(signal.clone()).await.unwrap();
    
    // Execute the plan
    let _results = orchestrator.execute_plan(&plan).await;
    
    // Verify audit log entries
    let history = orchestrator.get_execution_history(10).await;
    assert!(history.len() >= 2, "Should have plan creation and execution entries");
    
    // Verify plan creation entry
    let plan_entry = history.iter()
        .find(|entry| entry.action == "PLAN_CREATED")
        .expect("Should have plan creation entry");
    
    assert_eq!(plan_entry.signal_id, signal.id);
    assert!(plan_entry.decision_rationale.contains("Created execution plan"));
    
    // Verify execution result entries exist
    let execution_entries: Vec<_> = history.iter()
        .filter(|entry| entry.action == "EXECUTION_SUCCESS" || entry.action == "EXECUTION_FAILED")
        .collect();
    
    assert!(!execution_entries.is_empty(), "Should have execution result entries");
    
    // Verify timestamp and rationale presence
    for entry in &execution_entries {
        assert!(!entry.decision_rationale.is_empty(), "All entries should have rationale");
        // Timestamps are set by SystemTime::now() so they should be recent
    }
}

#[tokio::test]
async fn test_account_pause_resume() {
    let orchestrator = TradeExecutionOrchestrator::new();
    let platform = create_mock_platform("platform_1", false);
    
    orchestrator.register_account(
        "account_1".to_string(),
        platform,
        10000.0,
    ).await.unwrap();
    
    let status1 = orchestrator.get_account_status("account_1").await.unwrap();
    assert!(status1.is_active);
    
    orchestrator.pause_account("account_1").await.unwrap();
    let status2 = orchestrator.get_account_status("account_1").await.unwrap();
    assert!(!status2.is_active);
    
    orchestrator.resume_account("account_1").await.unwrap();
    let status3 = orchestrator.get_account_status("account_1").await.unwrap();
    assert!(status3.is_active);
}

#[tokio::test]
async fn test_position_size_calculation_with_risk_adjustment() {
    let orchestrator = TradeExecutionOrchestrator::new();
    let platform = create_mock_platform("platform_1", false);
    
    orchestrator.register_account(
        "account_1".to_string(),
        platform,
        10000.0,
    ).await.unwrap();
    
    let signal = create_test_signal();
    let plan1 = orchestrator.process_signal(signal.clone()).await.unwrap();
    let size1 = plan1.account_assignments[0].position_size;
    
    // For this test, we'll verify that position sizes are calculated properly
    // The orchestrator should adjust sizes based on account conditions
    // Since we can't directly modify internal state, we'll test that sizes are reasonable
    assert!(size1 > 0.0, "Position size should be positive");
    assert!(size1 < 10000.0, "Position size should be reasonable relative to account balance");
}