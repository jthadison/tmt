use chrono::Utc;
use rust_decimal_macros::dec;
use uuid::Uuid;
use execution_engine::risk::{
    RiskResponseSystem, RiskEvent, RiskSeverity, ResponseAction,
    ReductionPriority, EmergencyStopScope, ResponseExecutionResult,
    RiskThresholds, PositionManager, CircuitBreakerClient,
    RiskAuditLogger, ResponseExecutor
};
use std::sync::Arc;

#[tokio::test]
async fn test_margin_risk_critical_response() {
    let risk_thresholds = Arc::new(RiskThresholds::default());
    let position_manager = Arc::new(PositionManager::new());
    let circuit_breaker = Arc::new(CircuitBreakerClient);
    let risk_logger = Arc::new(RiskAuditLogger::new());
    let response_executor = Arc::new(ResponseExecutor);
    
    let system = RiskResponseSystem::new(
        risk_thresholds,
        position_manager,
        circuit_breaker,
        risk_logger,
        response_executor,
    );
    
    let account_id = Uuid::new_v4();
    let risk_event = RiskEvent {
        event_id: Uuid::new_v4(),
        account_id,
        risk_type: "margin_level".to_string(),
        description: "Margin level critically low".to_string(),
        metric_value: dec!(110),
        threshold_value: dec!(120),
        timestamp: Utc::now(),
    };
    
    let response = system.evaluate_and_respond(risk_event).await.unwrap();
    
    assert_eq!(response.severity, RiskSeverity::Critical);
    
    match response.action_taken {
        ResponseAction::ReducePositions { reduction_percentage, priority, .. } => {
            assert_eq!(reduction_percentage, dec!(50));
            assert_eq!(priority, ReductionPriority::LargestLoss);
        },
        _ => panic!("Expected ReducePositions action"),
    }
    
    match response.execution_result {
        ResponseExecutionResult::PositionsReduced { positions_affected, .. } => {
            assert_eq!(positions_affected, 3);
        },
        _ => panic!("Expected PositionsReduced result"),
    }
}

#[tokio::test]
async fn test_margin_risk_extreme_response() {
    let risk_thresholds = Arc::new(RiskThresholds::default());
    let position_manager = Arc::new(PositionManager::new());
    let circuit_breaker = Arc::new(CircuitBreakerClient);
    let risk_logger = Arc::new(RiskAuditLogger::new());
    let response_executor = Arc::new(ResponseExecutor);
    
    let system = RiskResponseSystem::new(
        risk_thresholds,
        position_manager,
        circuit_breaker,
        risk_logger,
        response_executor,
    );
    
    let account_id = Uuid::new_v4();
    let risk_event = RiskEvent {
        event_id: Uuid::new_v4(),
        account_id,
        risk_type: "margin_level".to_string(),
        description: "Margin level extremely low".to_string(),
        metric_value: dec!(90),
        threshold_value: dec!(120),
        timestamp: Utc::now(),
    };
    
    let response = system.evaluate_and_respond(risk_event).await.unwrap();
    
    assert_eq!(response.severity, RiskSeverity::Extreme);
    
    match response.action_taken {
        ResponseAction::EmergencyStop { scope, .. } => {
            assert_eq!(scope, EmergencyStopScope::Account(account_id));
        },
        _ => panic!("Expected EmergencyStop action"),
    }
}

#[tokio::test]
async fn test_drawdown_risk_response() {
    let risk_thresholds = Arc::new(RiskThresholds::default());
    let position_manager = Arc::new(PositionManager::new());
    let circuit_breaker = Arc::new(CircuitBreakerClient);
    let risk_logger = Arc::new(RiskAuditLogger::new());
    let response_executor = Arc::new(ResponseExecutor);
    
    let system = RiskResponseSystem::new(
        risk_thresholds,
        position_manager,
        circuit_breaker,
        risk_logger,
        response_executor,
    );
    
    let account_id = Uuid::new_v4();
    let risk_event = RiskEvent {
        event_id: Uuid::new_v4(),
        account_id,
        risk_type: "drawdown_exceeded".to_string(),
        description: "Maximum drawdown exceeded".to_string(),
        metric_value: dec!(25),
        threshold_value: dec!(20),
        timestamp: Utc::now(),
    };
    
    let response = system.evaluate_and_respond(risk_event).await.unwrap();
    
    assert_eq!(response.severity, RiskSeverity::High);
    
    match response.action_taken {
        ResponseAction::ReducePositionSize { new_risk_percentage, .. } => {
            assert_eq!(new_risk_percentage, dec!(1));
        },
        _ => panic!("Expected ReducePositionSize action"),
    }
}

#[tokio::test]
async fn test_exposure_concentration_response() {
    let risk_thresholds = Arc::new(RiskThresholds::default());
    let position_manager = Arc::new(PositionManager::new());
    let circuit_breaker = Arc::new(CircuitBreakerClient);
    let risk_logger = Arc::new(RiskAuditLogger::new());
    let response_executor = Arc::new(ResponseExecutor);
    
    let system = RiskResponseSystem::new(
        risk_thresholds,
        position_manager,
        circuit_breaker,
        risk_logger,
        response_executor,
    );
    
    let account_id = Uuid::new_v4();
    let risk_event = RiskEvent {
        event_id: Uuid::new_v4(),
        account_id,
        risk_type: "exposure_concentration".to_string(),
        description: "High exposure concentration".to_string(),
        metric_value: dec!(60),
        threshold_value: dec!(25),
        timestamp: Utc::now(),
    };
    
    let response = system.evaluate_and_respond(risk_event).await.unwrap();
    
    assert_eq!(response.severity, RiskSeverity::High);
    
    match response.action_taken {
        ResponseAction::ReducePositions { reduction_percentage, priority, .. } => {
            assert_eq!(reduction_percentage, dec!(30));
            assert_eq!(priority, ReductionPriority::LargestPosition);
        },
        _ => panic!("Expected ReducePositions action"),
    }
}

#[tokio::test]
async fn test_correlation_risk_response() {
    let risk_thresholds = Arc::new(RiskThresholds::default());
    let position_manager = Arc::new(PositionManager::new());
    let circuit_breaker = Arc::new(CircuitBreakerClient);
    let risk_logger = Arc::new(RiskAuditLogger::new());
    let response_executor = Arc::new(ResponseExecutor);
    
    let system = RiskResponseSystem::new(
        risk_thresholds,
        position_manager,
        circuit_breaker,
        risk_logger,
        response_executor,
    );
    
    let account_id = Uuid::new_v4();
    let risk_event = RiskEvent {
        event_id: Uuid::new_v4(),
        account_id,
        risk_type: "correlation_risk".to_string(),
        description: "High correlation between positions".to_string(),
        metric_value: dec!(0.9),
        threshold_value: dec!(0.8),
        timestamp: Utc::now(),
    };
    
    let response = system.evaluate_and_respond(risk_event).await.unwrap();
    
    assert_eq!(response.severity, RiskSeverity::Medium);
    
    match response.action_taken {
        ResponseAction::ReduceCorrelatedPositions { correlation_threshold, reduction_factor, .. } => {
            assert_eq!(correlation_threshold, dec!(0.7));
            assert_eq!(reduction_factor, dec!(0.5));
        },
        _ => panic!("Expected ReduceCorrelatedPositions action"),
    }
}

#[tokio::test]
async fn test_handle_pnl_risk() {
    let risk_thresholds = Arc::new(RiskThresholds::default());
    let position_manager = Arc::new(PositionManager::new());
    let circuit_breaker = Arc::new(CircuitBreakerClient);
    let risk_logger = Arc::new(RiskAuditLogger::new());
    let response_executor = Arc::new(ResponseExecutor);
    
    let system = RiskResponseSystem::new(
        risk_thresholds,
        position_manager,
        circuit_breaker,
        risk_logger,
        response_executor,
    );
    
    let account_id = Uuid::new_v4();
    let current_pnl = dec!(-1500);
    let max_loss_threshold = dec!(-1000);
    
    let response = system.handle_pnl_risk(account_id, current_pnl, max_loss_threshold).await.unwrap();
    
    assert!(response.is_some());
    let response = response.unwrap();
    assert_eq!(response.risk_event.risk_type, "pnl_threshold");
    assert_eq!(response.risk_event.account_id, account_id);
}

#[tokio::test]
async fn test_handle_drawdown_risk() {
    let risk_thresholds = Arc::new(RiskThresholds::default());
    let position_manager = Arc::new(PositionManager::new());
    let circuit_breaker = Arc::new(CircuitBreakerClient);
    let risk_logger = Arc::new(RiskAuditLogger::new());
    let response_executor = Arc::new(ResponseExecutor);
    
    let system = RiskResponseSystem::new(
        risk_thresholds,
        position_manager,
        circuit_breaker,
        risk_logger,
        response_executor,
    );
    
    let account_id = Uuid::new_v4();
    let current_drawdown = dec!(15);
    let max_drawdown_threshold = dec!(10);
    
    let response = system.handle_drawdown_risk(account_id, current_drawdown, max_drawdown_threshold).await.unwrap();
    
    assert!(response.is_some());
    let response = response.unwrap();
    assert_eq!(response.risk_event.risk_type, "drawdown_exceeded");
}

#[tokio::test]
async fn test_handle_margin_risk() {
    let risk_thresholds = Arc::new(RiskThresholds::default());
    let position_manager = Arc::new(PositionManager::new());
    let circuit_breaker = Arc::new(CircuitBreakerClient);
    let risk_logger = Arc::new(RiskAuditLogger::new());
    let response_executor = Arc::new(ResponseExecutor);
    
    let system = RiskResponseSystem::new(
        risk_thresholds,
        position_manager,
        circuit_breaker,
        risk_logger,
        response_executor,
    );
    
    let account_id = Uuid::new_v4();
    let current_margin_level = dec!(115);
    let critical_threshold = dec!(120);
    
    let response = system.handle_margin_risk(account_id, current_margin_level, critical_threshold).await.unwrap();
    
    assert!(response.is_some());
    let response = response.unwrap();
    assert_eq!(response.risk_event.risk_type, "margin_level");
}