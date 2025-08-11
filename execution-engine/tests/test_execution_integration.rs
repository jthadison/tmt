use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, SystemTime};
use tokio::sync::RwLock;
use execution_engine::execution::{
    TradeExecutionOrchestrator,
    TradeSignal,
    ExecutionCoordinator,
    ExecutionMonitor,
    PartialFill,
};
use execution_engine::platforms::abstraction::models::{OrderSide, OrderStatus};

async fn setup_orchestrator_with_accounts(num_accounts: usize) -> TradeExecutionOrchestrator {
    let orchestrator = TradeExecutionOrchestrator::new();
    
    for i in 1..=num_accounts {
        let platform = create_integration_test_platform(&format!("platform_{}", i));
        orchestrator.register_account(
            format!("account_{}", i),
            platform,
            10000.0,
        ).await.expect("Failed to register account");
    }
    
    orchestrator
}

fn create_integration_test_platform(name: &str) -> Arc<dyn execution_engine::platforms::abstraction::interfaces::TradingPlatform + Send + Sync> {
    use async_trait::async_trait;
    use execution_engine::platforms::abstraction::{
        interfaces::{TradingPlatform, AccountInfo},
        models::{Order, Position},
        errors::TradingError,
    };
    
    #[derive(Clone)]
    struct TestPlatform {
        name: String,
        orders: Arc<RwLock<Vec<Order>>>,
    }
    
    #[async_trait]
    impl TradingPlatform for TestPlatform {
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
            Ok(AccountInfo {
                account_id: self.name.clone(),
                balance: 10000.0,
                equity: 10000.0,
                margin: 0.0,
                free_margin: 10000.0,
                margin_level: 0.0,
                currency: "USD".to_string(),
            })
        }
        
        async fn get_positions(&self) -> Result<Vec<Position>, TradingError> {
            Ok(Vec::new())
        }
        
        async fn get_orders(&self) -> Result<Vec<Order>, TradingError> {
            let orders = self.orders.read().await;
            Ok(orders.clone())
        }
        
        async fn place_order(&self, mut order: Order) -> Result<Order, TradingError> {
            tokio::time::sleep(Duration::from_millis(rand::random::<u64>() % 100)).await;
            order.status = OrderStatus::Filled;
            order.price = Some(1.0900 + (rand::random::<f64>() * 0.001));
            
            let mut orders = self.orders.write().await;
            orders.push(order.clone());
            
            Ok(order)
        }
        
        async fn modify_order(&self, _order_id: &str, new_order: Order) -> Result<Order, TradingError> {
            Ok(new_order)
        }
        
        async fn cancel_order(&self, order_id: &str) -> Result<(), TradingError> {
            let mut orders = self.orders.write().await;
            orders.retain(|o| o.id != order_id);
            Ok(())
        }
        
        async fn close_position(&self, _position_id: &str) -> Result<(), TradingError> {
            Ok(())
        }
        
        async fn get_order(&self, order_id: &str) -> Result<Order, TradingError> {
            let orders = self.orders.read().await;
            orders.iter()
                .find(|o| o.id == order_id)
                .cloned()
                .ok_or_else(|| TradingError::OrderNotFound(order_id.to_string()))
        }
        
        async fn get_position(&self, position_id: &str) -> Result<Position, TradingError> {
            Err(TradingError::PositionNotFound(position_id.to_string()))
        }
    }
    
    Arc::new(TestPlatform {
        name: name.to_string(),
        orders: Arc::new(RwLock::new(Vec::new())),
    })
}

#[tokio::test]
async fn test_end_to_end_signal_execution() {
    let orchestrator = setup_orchestrator_with_accounts(3).await;
    
    let signal = TradeSignal {
        id: "integration_signal_001".to_string(),
        symbol: "EURUSD".to_string(),
        side: OrderSide::Buy,
        entry_price: 1.0900,
        stop_loss: 1.0850,
        take_profit: 1.1000,
        confidence: 0.85,
        risk_reward_ratio: 2.0,
        signal_time: SystemTime::now(),
        metadata: HashMap::new(),
    };
    
    let plan = orchestrator.process_signal(signal.clone()).await
        .expect("Failed to process signal");
    
    assert_eq!(plan.account_assignments.len(), 3);
    assert_eq!(plan.signal_id, "integration_signal_001");
    
    let results = orchestrator.execute_plan(&plan).await;
    
    assert_eq!(results.len(), 3);
    for result in &results {
        assert!(result.success, "Execution should succeed for account {}", result.account_id);
        assert!(result.order_id.is_some());
        assert!(result.actual_entry_price.is_some());
        assert!(result.execution_time < Duration::from_secs(35));
    }
    
    let history = orchestrator.get_execution_history(100).await;
    assert!(history.len() >= 4);
    
    let plan_created = history.iter().find(|e| e.action == "PLAN_CREATED");
    assert!(plan_created.is_some());
    
    let successful_executions = history.iter()
        .filter(|e| e.action == "EXECUTION_SUCCESS")
        .count();
    assert_eq!(successful_executions, 3);
}

#[tokio::test]
async fn test_concurrent_signal_processing() {
    let orchestrator = Arc::new(setup_orchestrator_with_accounts(5).await);
    
    let signals = vec![
        TradeSignal {
            id: "concurrent_signal_001".to_string(),
            symbol: "EURUSD".to_string(),
            side: OrderSide::Buy,
            entry_price: 1.0900,
            stop_loss: 1.0850,
            take_profit: 1.1000,
            confidence: 0.80,
            risk_reward_ratio: 2.0,
            signal_time: SystemTime::now(),
            metadata: HashMap::new(),
        },
        TradeSignal {
            id: "concurrent_signal_002".to_string(),
            symbol: "GBPUSD".to_string(),
            side: OrderSide::Sell,
            entry_price: 1.2500,
            stop_loss: 1.2550,
            take_profit: 1.2400,
            confidence: 0.75,
            risk_reward_ratio: 2.0,
            signal_time: SystemTime::now(),
            metadata: HashMap::new(),
        },
    ];
    
    let mut handles = Vec::new();
    
    for signal in signals {
        let orchestrator_clone = orchestrator.clone();
        let handle = tokio::spawn(async move {
            let plan = orchestrator_clone.process_signal(signal).await
                .expect("Failed to process signal");
            orchestrator_clone.execute_plan(&plan).await
        });
        handles.push(handle);
    }
    
    let mut all_results = Vec::new();
    for handle in handles {
        let results = handle.await.expect("Task panicked");
        all_results.extend(results);
    }
    
    let successful = all_results.iter().filter(|r| r.success).count();
    assert!(successful > 0, "At least some executions should succeed");
    
    let unique_accounts: std::collections::HashSet<_> = all_results.iter()
        .map(|r| r.account_id.clone())
        .collect();
    assert!(unique_accounts.len() >= 2, "Multiple accounts should be used");
}

#[tokio::test]
async fn test_partial_fill_handling() {
    let coordinator = ExecutionCoordinator::new();
    
    let mut monitor = ExecutionMonitor::new(
        "partial_order_001".to_string(),
        "account_1".to_string(),
        100.0,
    );
    
    let fill1 = PartialFill {
        order_id: "partial_order_001".to_string(),
        filled_quantity: 30.0,
        remaining_quantity: 70.0,
        filled_price: 1.0900,
        timestamp: SystemTime::now(),
    };
    
    monitor.add_partial_fill(fill1);
    assert_eq!(monitor.status, OrderStatus::PartiallyFilled);
    assert_eq!(monitor.remaining_quantity(), 70.0);
    
    let fill2 = PartialFill {
        order_id: "partial_order_001".to_string(),
        filled_quantity: 40.0,
        remaining_quantity: 30.0,
        filled_price: 1.0901,
        timestamp: SystemTime::now(),
    };
    
    monitor.add_partial_fill(fill2);
    assert_eq!(monitor.remaining_quantity(), 30.0);
    
    let fill3 = PartialFill {
        order_id: "partial_order_001".to_string(),
        filled_quantity: 30.0,
        remaining_quantity: 0.0,
        filled_price: 1.0902,
        timestamp: SystemTime::now(),
    };
    
    monitor.add_partial_fill(fill3);
    assert_eq!(monitor.status, OrderStatus::Filled);
    assert!(monitor.is_complete());
    assert_eq!(monitor.remaining_quantity(), 0.0);
    assert_eq!(monitor.partial_fills.len(), 3);
}

#[tokio::test]
async fn test_correlation_based_execution_distribution() {
    let orchestrator = setup_orchestrator_with_accounts(4).await;
    
    orchestrator.update_correlation_matrix("account_1", "account_2", 0.85).await;
    orchestrator.update_correlation_matrix("account_3", "account_4", 0.90).await;
    
    let signal = TradeSignal {
        id: "correlation_test_signal".to_string(),
        symbol: "EURUSD".to_string(),
        side: OrderSide::Buy,
        entry_price: 1.0900,
        stop_loss: 1.0850,
        take_profit: 1.1000,
        confidence: 0.85,
        risk_reward_ratio: 2.0,
        signal_time: SystemTime::now(),
        metadata: HashMap::new(),
    };
    
    let plan = orchestrator.process_signal(signal).await
        .expect("Failed to process signal");
    
    let account_1_timing = plan.account_assignments.iter()
        .find(|a| a.account_id == "account_1")
        .map(|a| a.entry_timing_delay);
    
    let account_2_timing = plan.account_assignments.iter()
        .find(|a| a.account_id == "account_2")
        .map(|a| a.entry_timing_delay);
    
    if let (Some(t1), Some(t2)) = (account_1_timing, account_2_timing) {
        let time_diff = if t1 > t2 { t1 - t2 } else { t2 - t1 };
        assert!(
            time_diff > Duration::from_millis(1500),
            "High correlation accounts should have significant timing variance"
        );
    }
}

#[tokio::test]
async fn test_risk_budget_enforcement() {
    let orchestrator = setup_orchestrator_with_accounts(2).await;
    
    {
        let mut accounts = orchestrator.accounts.write().await;
        if let Some(account) = accounts.get_mut("account_1") {
            account.risk_budget_remaining = 0.0;
        }
        if let Some(account) = accounts.get_mut("account_2") {
            account.risk_budget_remaining = 100.0;
        }
    }
    
    let signal = TradeSignal {
        id: "risk_budget_test".to_string(),
        symbol: "EURUSD".to_string(),
        side: OrderSide::Buy,
        entry_price: 1.0900,
        stop_loss: 1.0850,
        take_profit: 1.1000,
        confidence: 0.85,
        risk_reward_ratio: 2.0,
        signal_time: SystemTime::now(),
        metadata: HashMap::new(),
    };
    
    let plan = orchestrator.process_signal(signal).await
        .expect("Failed to process signal");
    
    assert_eq!(plan.account_assignments.len(), 1);
    assert_eq!(plan.account_assignments[0].account_id, "account_2");
}

#[tokio::test]
async fn test_execution_audit_trail() {
    let orchestrator = setup_orchestrator_with_accounts(2).await;
    
    let signal = TradeSignal {
        id: "audit_test_signal".to_string(),
        symbol: "EURUSD".to_string(),
        side: OrderSide::Buy,
        entry_price: 1.0900,
        stop_loss: 1.0850,
        take_profit: 1.1000,
        confidence: 0.85,
        risk_reward_ratio: 2.0,
        signal_time: SystemTime::now(),
        metadata: HashMap::from([
            ("strategy".to_string(), "wyckoff_spring".to_string()),
            ("timeframe".to_string(), "H1".to_string()),
        ]),
    };
    
    let plan = orchestrator.process_signal(signal).await
        .expect("Failed to process signal");
    
    let results = orchestrator.execute_plan(&plan).await;
    
    tokio::time::sleep(Duration::from_millis(100)).await;
    
    let history = orchestrator.get_execution_history(50).await;
    
    let plan_entry = history.iter()
        .find(|e| e.signal_id == "audit_test_signal" && e.action == "PLAN_CREATED");
    assert!(plan_entry.is_some());
    
    let execution_entries: Vec<_> = history.iter()
        .filter(|e| e.signal_id == "audit_test_signal" && e.action.contains("EXECUTION"))
        .collect();
    assert_eq!(execution_entries.len(), results.len());
    
    for entry in execution_entries {
        assert!(entry.timestamp > SystemTime::now() - Duration::from_secs(10));
        assert!(!entry.account_id.is_empty());
        assert!(entry.result.is_some());
    }
}

#[tokio::test]
async fn test_emergency_stop_during_execution() {
    let orchestrator = setup_orchestrator_with_accounts(3).await;
    
    let signal = TradeSignal {
        id: "emergency_stop_test".to_string(),
        symbol: "EURUSD".to_string(),
        side: OrderSide::Buy,
        entry_price: 1.0900,
        stop_loss: 1.0850,
        take_profit: 1.1000,
        confidence: 0.85,
        risk_reward_ratio: 2.0,
        signal_time: SystemTime::now(),
        metadata: HashMap::new(),
    };
    
    let plan = orchestrator.process_signal(signal).await
        .expect("Failed to process signal");
    
    let execution_handle = tokio::spawn({
        let orchestrator = orchestrator.clone();
        let plan = plan.clone();
        async move {
            orchestrator.execute_plan(&plan).await
        }
    });
    
    tokio::time::sleep(Duration::from_millis(500)).await;
    
    for i in 1..=3 {
        let _ = orchestrator.pause_account(&format!("account_{}", i)).await;
    }
    
    let results = execution_handle.await.expect("Execution task panicked");
    
    for i in 1..=3 {
        let status = orchestrator.get_account_status(&format!("account_{}", i)).await;
        assert!(status.is_some());
        assert!(!status.unwrap().is_active, "Account should be paused");
    }
}