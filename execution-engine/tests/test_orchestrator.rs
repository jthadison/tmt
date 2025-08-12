use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, SystemTime};
use tokio::sync::RwLock;

use execution_engine::execution::{
    AccountStatus, ExecutionPlan, TradeExecutionOrchestrator, TradeSignal,
};
use execution_engine::platforms::abstraction::{
    errors::TradingError,
    interfaces::{AccountInfo, TradingPlatform},
    models::{Order, OrderSide, OrderStatus, Position},
};

#[derive(Clone)]
struct MockPlatform {
    name: String,
    should_fail: bool,
    execution_delay_ms: u64,
    account_info: AccountInfo,
    orders: Arc<RwLock<Vec<Order>>>,
}

#[async_trait]
impl TradingPlatform for MockPlatform {
    fn platform_name(&self) -> String {
        self.name.clone()
    }

    async fn connect(&mut self) -> Result<(), TradingError> {
        Ok(())
    }

    async fn disconnect(&mut self) -> Result<(), TradingError> {
        Ok(())
    }

    async fn is_connected(&self) -> bool {
        true
    }

    async fn get_account_info(&self) -> Result<AccountInfo, TradingError> {
        Ok(self.account_info.clone())
    }

    async fn get_positions(&self) -> Result<Vec<Position>, TradingError> {
        Ok(Vec::new())
    }

    async fn get_orders(&self) -> Result<Vec<Order>, TradingError> {
        let orders = self.orders.read().await;
        Ok(orders.clone())
    }

    async fn place_order(&self, mut order: Order) -> Result<Order, TradingError> {
        if self.should_fail {
            return Err(TradingError::OrderFailed("Mock failure".to_string()));
        }

        tokio::time::sleep(Duration::from_millis(self.execution_delay_ms)).await;

        order.status = OrderStatus::Filled;
        order.platform_order_id = Some(format!("MOCK_{}", order.id));
        order.price = Some(1.0900);

        let mut orders = self.orders.write().await;
        orders.push(order.clone());

        Ok(order)
    }

    async fn modify_order(&self, order_id: &str, new_order: Order) -> Result<Order, TradingError> {
        Ok(new_order)
    }

    async fn cancel_order(&self, order_id: &str) -> Result<(), TradingError> {
        let mut orders = self.orders.write().await;
        orders.retain(|o| o.id != order_id);
        Ok(())
    }

    async fn close_position(&self, position_id: &str) -> Result<(), TradingError> {
        Ok(())
    }

    async fn get_order(&self, order_id: &str) -> Result<Order, TradingError> {
        let orders = self.orders.read().await;
        orders
            .iter()
            .find(|o| o.id == order_id)
            .cloned()
            .ok_or_else(|| TradingError::OrderNotFound(order_id.to_string()))
    }

    async fn get_position(&self, position_id: &str) -> Result<Position, TradingError> {
        Err(TradingError::PositionNotFound(position_id.to_string()))
    }
}

fn create_mock_platform(name: &str, should_fail: bool) -> Arc<MockPlatform> {
    Arc::new(MockPlatform {
        name: name.to_string(),
        should_fail,
        execution_delay_ms: 10,
        account_info: AccountInfo {
            account_id: name.to_string(),
            balance: 10000.0,
            equity: 10000.0,
            margin: 0.0,
            free_margin: 10000.0,
            margin_level: 0.0,
            currency: "USD".to_string(),
        },
        orders: Arc::new(RwLock::new(Vec::new())),
    })
}

fn create_test_signal() -> TradeSignal {
    TradeSignal {
        id: "signal_001".to_string(),
        symbol: "EURUSD".to_string(),
        side: OrderSide::Buy,
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

    let result = orchestrator
        .register_account("account1".to_string(), platform.clone(), 10000.0)
        .await;

    assert!(result.is_ok());

    let status = orchestrator.get_account_status("account1").await;
    assert!(status.is_some());

    let account = status.unwrap();
    assert_eq!(account.account_id, "account1");
    assert_eq!(account.platform, "test_account");
    assert!(account.is_active);
}

#[tokio::test]
async fn test_signal_processing_with_eligible_accounts() {
    let orchestrator = TradeExecutionOrchestrator::new();

    for i in 1..=3 {
        let platform = create_mock_platform(&format!("platform_{}", i), false);
        orchestrator
            .register_account(format!("account_{}", i), platform, 10000.0)
            .await
            .unwrap();
    }

    let signal = create_test_signal();
    let plan = orchestrator.process_signal(signal).await;

    assert!(plan.is_ok());
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

    let platform = create_mock_platform("platform_1", false);
    orchestrator
        .register_account("account_1".to_string(), platform, 10000.0)
        .await
        .unwrap();

    orchestrator.pause_account("account_1").await.unwrap();

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
        let platform = create_mock_platform(&format!("platform_{}", i), false);
        orchestrator
            .register_account(format!("account_{}", i), platform, 10000.0)
            .await
            .unwrap();
    }

    let signal = create_test_signal();
    let plan = orchestrator.process_signal(signal).await.unwrap();

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
        let platform = create_mock_platform(&format!("platform_{}", i), false);
        orchestrator
            .register_account(format!("account_{}", i), platform, 10000.0)
            .await
            .unwrap();
    }

    let signal = create_test_signal();
    let plan = orchestrator.process_signal(signal).await.unwrap();

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
        let platform = create_mock_platform(&format!("platform_{}", i), false);
        orchestrator
            .register_account(format!("account{}", i), platform, 10000.0)
            .await
            .unwrap();
    }

    let signal = create_test_signal();
    let plan = orchestrator.process_signal(signal).await.unwrap();

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
    let platform = create_mock_platform("platform_1", false);

    orchestrator
        .register_account("account_1".to_string(), platform, 10000.0)
        .await
        .unwrap();

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
async fn test_execution_history_logging() {
    let orchestrator = TradeExecutionOrchestrator::new();

    let platform = create_mock_platform("platform_1", false);
    orchestrator
        .register_account("account_1".to_string(), platform, 10000.0)
        .await
        .unwrap();

    let signal = create_test_signal();
    let _ = orchestrator.process_signal(signal).await.unwrap();

    let history = orchestrator.get_execution_history(10).await;
    assert!(history.len() > 0);

    let first_entry = &history[0];
    assert_eq!(first_entry.action, "PLAN_CREATED");
    assert!(first_entry
        .decision_rationale
        .contains("Created execution plan"));
}

#[tokio::test]
async fn test_failed_execution_recovery() {
    let orchestrator = TradeExecutionOrchestrator::new();

    let failing_platform = Arc::new(MockPlatform {
        name: "failing_platform".to_string(),
        should_fail: true,
        execution_delay_ms: 10,
        account_info: AccountInfo {
            account_id: "failing_account".to_string(),
            balance: 10000.0,
            equity: 10000.0,
            margin: 0.0,
            free_margin: 10000.0,
            margin_level: 0.0,
            currency: "USD".to_string(),
        },
        orders: Arc::new(RwLock::new(Vec::new())),
    });

    let success_platform = create_mock_platform("success_platform", false);

    orchestrator
        .register_account("failing_account".to_string(), failing_platform, 10000.0)
        .await
        .unwrap();

    orchestrator
        .register_account("backup_account".to_string(), success_platform, 10000.0)
        .await
        .unwrap();

    let signal = create_test_signal();
    let plan = orchestrator.process_signal(signal).await.unwrap();
    let results = orchestrator.execute_plan(&plan).await;

    let failed_result = results.iter().find(|r| r.account_id == "failing_account");

    if let Some(failed) = failed_result {
        assert!(!failed.success);

        let recovery = orchestrator.handle_failed_execution(failed, &plan).await;
        assert!(recovery.is_ok());

        let recovered = recovery.unwrap();
        assert!(recovered.success);
        assert_eq!(recovered.account_id, "backup_account");
    }
}

#[tokio::test]
async fn test_position_size_calculation_with_drawdown() {
    let orchestrator = TradeExecutionOrchestrator::new();
    let platform = create_mock_platform("platform_1", false);

    orchestrator
        .register_account("account_1".to_string(), platform, 10000.0)
        .await
        .unwrap();

    {
        let mut accounts = orchestrator.accounts.write().await;
        if let Some(account) = accounts.get_mut("account_1") {
            account.daily_drawdown = 0.025;
        }
    }

    let signal = create_test_signal();
    let plan1 = orchestrator.process_signal(signal.clone()).await.unwrap();
    let size1 = plan1.account_assignments[0].position_size;

    {
        let mut accounts = orchestrator.accounts.write().await;
        if let Some(account) = accounts.get_mut("account_1") {
            account.daily_drawdown = 0.04;
        }
    }

    let plan2 = orchestrator.process_signal(signal).await.unwrap();
    let size2 = plan2.account_assignments[0].position_size;

    assert!(
        size2 < size1,
        "Higher drawdown should result in smaller position size"
    );
}
