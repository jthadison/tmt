use rand::Rng;
use rust_decimal::prelude::ToPrimitive;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant, SystemTime};
use tokio::sync::RwLock;
use tracing::{debug, error, info, warn};
use uuid::Uuid;

use crate::platforms::abstraction::{
    interfaces::ITradingPlatform,
    models::{UnifiedOrder, UnifiedOrderSide, UnifiedOrderType},
};
// Temporarily disabled complex risk dependencies
// use crate::risk::{DrawdownTracker, ExposureMonitor, MarginMonitor};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AccountStatus {
    pub account_id: String,
    pub platform: String,
    pub available_margin: f64,
    pub risk_budget_remaining: f64,
    pub daily_drawdown: f64,
    pub max_drawdown: f64,
    pub open_positions: usize,
    pub last_trade_time: Option<SystemTime>,
    pub is_active: bool,
    pub correlation_score: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradeSignal {
    pub id: String,
    pub symbol: String,
    pub side: UnifiedOrderSide,
    pub entry_price: f64,
    pub stop_loss: f64,
    pub take_profit: f64,
    pub confidence: f64,
    pub risk_reward_ratio: f64,
    pub signal_time: SystemTime,
    pub metadata: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionPlan {
    pub signal_id: String,
    pub account_assignments: Vec<AccountAssignment>,
    pub timing_variance: HashMap<String, Duration>,
    pub size_variance: HashMap<String, f64>,
    pub rationale: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AccountAssignment {
    pub account_id: String,
    pub position_size: f64,
    pub entry_timing_delay: Duration,
    pub priority: u8,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionResult {
    pub signal_id: String,
    pub account_id: String,
    pub order_id: Option<String>,
    pub success: bool,
    pub error_message: Option<String>,
    pub execution_time: Duration,
    pub actual_entry_price: Option<f64>,
    pub slippage: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionAuditEntry {
    pub id: String,
    pub timestamp: SystemTime,
    pub signal_id: String,
    pub account_id: String,
    pub action: String,
    pub decision_rationale: String,
    pub result: Option<ExecutionResult>,
    pub metadata: HashMap<String, String>,
}

pub struct TradeExecutionOrchestrator {
    accounts: Arc<RwLock<HashMap<String, AccountStatus>>>,
    platforms: Arc<RwLock<HashMap<String, Arc<dyn ITradingPlatform + Send + Sync>>>>,
    // Temporarily disabled complex risk dependencies
    // drawdown_trackers: Arc<RwLock<HashMap<String, DrawdownTracker>>>,
    // exposure_monitors: Arc<RwLock<HashMap<String, ExposureMonitor>>>,
    // margin_monitors: Arc<RwLock<HashMap<String, MarginMonitor>>>,
    execution_history: Arc<RwLock<Vec<ExecutionAuditEntry>>>,
    active_executions: Arc<RwLock<HashMap<String, ExecutionPlan>>>,
    correlation_matrix: Arc<RwLock<HashMap<(String, String), f64>>>,
    max_correlation_threshold: f64,
    min_timing_variance_ms: u64,
    max_timing_variance_ms: u64,
    min_size_variance_pct: f64,
    max_size_variance_pct: f64,
}

impl TradeExecutionOrchestrator {
    pub fn new() -> Self {
        Self {
            accounts: Arc::new(RwLock::new(HashMap::new())),
            platforms: Arc::new(RwLock::new(HashMap::new())),
            // Temporarily disabled
            // drawdown_trackers: Arc::new(RwLock::new(HashMap::new())),
            // exposure_monitors: Arc::new(RwLock::new(HashMap::new())),
            // margin_monitors: Arc::new(RwLock::new(HashMap::new())),
            execution_history: Arc::new(RwLock::new(Vec::new())),
            active_executions: Arc::new(RwLock::new(HashMap::new())),
            correlation_matrix: Arc::new(RwLock::new(HashMap::new())),
            max_correlation_threshold: 0.7,
            min_timing_variance_ms: 1000,
            max_timing_variance_ms: 30000,
            min_size_variance_pct: 0.05,
            max_size_variance_pct: 0.15,
        }
    }

    pub async fn register_account(
        &self,
        account_id: String,
        platform: Arc<dyn ITradingPlatform + Send + Sync>,
        initial_balance: f64,
    ) -> Result<(), String> {
        let mut accounts = self.accounts.write().await;
        let mut platforms = self.platforms.write().await;

        let account_info = platform
            .get_account_info()
            .await
            .map_err(|e| format!("Failed to get account info: {}", e))?;

        let status = AccountStatus {
            account_id: account_id.clone(),
            platform: platform.platform_name().to_string(),
            available_margin: account_info.margin_available.to_f64().unwrap_or(0.0),
            risk_budget_remaining: initial_balance * 0.02,
            daily_drawdown: 0.0,
            max_drawdown: 0.0,
            open_positions: 0,
            last_trade_time: None,
            is_active: true,
            correlation_score: 0.0,
        };

        accounts.insert(account_id.clone(), status);
        platforms.insert(account_id.clone(), platform);

        info!(
            "Registered account {} with initial balance {}",
            account_id, initial_balance
        );
        Ok(())
    }

    pub async fn process_signal(&self, signal: TradeSignal) -> Result<ExecutionPlan, String> {
        info!("Processing signal {} for {}", signal.id, signal.symbol);

        let accounts = self.accounts.read().await;
        let eligible_accounts = self.select_eligible_accounts(&accounts, &signal).await?;

        if eligible_accounts.is_empty() {
            return Err("No eligible accounts for signal execution".to_string());
        }

        let mut plan = self
            .create_execution_plan(signal.clone(), eligible_accounts)
            .await?;

        plan = self.apply_anti_correlation(&plan).await?;

        let mut active = self.active_executions.write().await;
        active.insert(signal.id.clone(), plan.clone());

        self.log_audit_entry(
            signal.id.clone(),
            "PLAN_CREATED".to_string(),
            format!(
                "Created execution plan with {} accounts",
                plan.account_assignments.len()
            ),
            None,
        )
        .await;

        Ok(plan)
    }

    async fn select_eligible_accounts(
        &self,
        accounts: &HashMap<String, AccountStatus>,
        _signal: &TradeSignal,
    ) -> Result<Vec<String>, String> {
        let mut eligible = Vec::new();

        for (account_id, status) in accounts.iter() {
            if !status.is_active {
                debug!("Account {} is inactive", account_id);
                continue;
            }

            if status.available_margin < 1000.0 {
                debug!("Account {} has insufficient margin", account_id);
                continue;
            }

            if status.risk_budget_remaining <= 0.0 {
                debug!("Account {} has no risk budget remaining", account_id);
                continue;
            }

            if status.daily_drawdown > 0.04 {
                debug!("Account {} exceeds daily drawdown limit", account_id);
                continue;
            }

            if status.open_positions >= 3 {
                debug!("Account {} has maximum positions open", account_id);
                continue;
            }

            eligible.push(account_id.clone());
        }

        Ok(eligible)
    }

    async fn create_execution_plan(
        &self,
        signal: TradeSignal,
        eligible_accounts: Vec<String>,
    ) -> Result<ExecutionPlan, String> {
        let mut rng = rand::thread_rng();
        let mut assignments = Vec::new();

        for (priority, account_id) in eligible_accounts.iter().enumerate() {
            let base_delay_ms =
                rng.gen_range(self.min_timing_variance_ms..=self.max_timing_variance_ms);
            let delay = Duration::from_millis(base_delay_ms);

            let variance_pct =
                rng.gen_range(self.min_size_variance_pct..=self.max_size_variance_pct);
            let sign = if rng.gen_bool(0.5) { 1.0 } else { -1.0 };
            let size_multiplier = 1.0 + (variance_pct * sign);

            let accounts = self.accounts.read().await;
            let account = accounts
                .get(account_id)
                .ok_or_else(|| format!("Account {} not found", account_id))?;

            let base_size = self.calculate_position_size(account, &signal);
            let adjusted_size = (base_size * size_multiplier * 100.0).round() / 100.0;

            assignments.push(AccountAssignment {
                account_id: account_id.clone(),
                position_size: adjusted_size,
                entry_timing_delay: delay,
                priority: priority as u8,
            });
        }

        let mut timing_variance = HashMap::new();
        let mut size_variance = HashMap::new();

        for assignment in &assignments {
            timing_variance.insert(assignment.account_id.clone(), assignment.entry_timing_delay);
            size_variance.insert(assignment.account_id.clone(), assignment.position_size);
        }

        Ok(ExecutionPlan {
            signal_id: signal.id,
            account_assignments: assignments,
            timing_variance,
            size_variance,
            rationale: format!(
                "Distributed signal across {} accounts with variance",
                eligible_accounts.len()
            ),
        })
    }

    fn calculate_position_size(&self, account: &AccountStatus, signal: &TradeSignal) -> f64 {
        let risk_per_trade = account
            .risk_budget_remaining
            .min(account.available_margin * 0.01);

        let stop_distance = (signal.entry_price - signal.stop_loss).abs();
        let position_size = risk_per_trade / stop_distance;

        let volatility_adjustment = 1.0 - (account.daily_drawdown / 0.05).min(0.5);
        let adjusted_size = position_size * volatility_adjustment;

        (adjusted_size * 100.0).round() / 100.0
    }

    async fn apply_anti_correlation(&self, plan: &ExecutionPlan) -> Result<ExecutionPlan, String> {
        let correlation_matrix = self.correlation_matrix.read().await;
        let mut modified_plan = plan.clone();

        let assignments_len = modified_plan.account_assignments.len();
        for i in 0..assignments_len {
            for j in i + 1..assignments_len {
                let (acc1, acc2) = {
                    let acc1 = modified_plan.account_assignments[i].account_id.clone();
                    let acc2 = modified_plan.account_assignments[j].account_id.clone();
                    (acc1, acc2)
                };
                let key = if acc1 < acc2 {
                    (acc1.clone(), acc2.clone())
                } else {
                    (acc2.clone(), acc1.clone())
                };

                if let Some(&correlation) = correlation_matrix.get(&key) {
                    if correlation > self.max_correlation_threshold {
                        let additional_delay = Duration::from_millis(
                            ((correlation - self.max_correlation_threshold) * 10000.0) as u64,
                        );
                        modified_plan.account_assignments[j].entry_timing_delay += additional_delay;
                        modified_plan.account_assignments[j].position_size *= 0.9;

                        info!(
                            "Applied anti-correlation adjustment between {} and {} (correlation: {:.2})",
                            acc1, acc2, correlation
                        );
                    }
                }
            }
        }

        Ok(modified_plan)
    }

    pub async fn execute_plan(&self, plan: &ExecutionPlan) -> Vec<ExecutionResult> {
        let mut results = Vec::new();
        let mut handles = Vec::new();

        for assignment in &plan.account_assignments {
            let assignment = assignment.clone();
            let platforms = self.platforms.clone();
            let _execution_history = self.execution_history.clone();
            let accounts = self.accounts.clone();
            let signal_id = plan.signal_id.clone();

            let handle = tokio::spawn(async move {
                tokio::time::sleep(assignment.entry_timing_delay).await;

                let start_time = Instant::now();
                let platforms = platforms.read().await;

                if let Some(platform) = platforms.get(&assignment.account_id) {
                    let order = UnifiedOrder {
                        client_order_id: Uuid::new_v4().to_string(),
                        symbol: "EURUSD".to_string(),
                        order_type: UnifiedOrderType::Market,
                        side: UnifiedOrderSide::Buy,
                        quantity: rust_decimal::Decimal::from_f64_retain(assignment.position_size)
                            .unwrap(),
                        price: None,
                        stop_price: None,
                        stop_loss: Some(rust_decimal::Decimal::from_f64_retain(1.0800).unwrap()),
                        take_profit: Some(rust_decimal::Decimal::from_f64_retain(1.1000).unwrap()),
                        time_in_force:
                            crate::platforms::abstraction::models::UnifiedTimeInForce::Gtc,
                        account_id: Some(assignment.account_id.clone()),
                        metadata: crate::platforms::abstraction::models::OrderMetadata {
                            strategy_id: Some(signal_id.clone()),
                            signal_id: Some(signal_id.clone()),
                            risk_parameters: HashMap::new(),
                            tags: vec![],
                            expires_at: None,
                        },
                    };

                    match platform.place_order(order).await {
                        Ok(placed_order) => {
                            let mut accounts = accounts.write().await;
                            if let Some(account) = accounts.get_mut(&assignment.account_id) {
                                account.last_trade_time = Some(SystemTime::now());
                                account.open_positions += 1;
                            }

                            ExecutionResult {
                                signal_id: signal_id.clone(),
                                account_id: assignment.account_id.clone(),
                                order_id: Some(placed_order.platform_order_id),
                                success: true,
                                error_message: None,
                                execution_time: start_time.elapsed(),
                                actual_entry_price: placed_order
                                    .price
                                    .map(|p| p.to_f64().unwrap_or(0.0)),
                                slippage: None,
                            }
                        }
                        Err(e) => {
                            error!(
                                "Failed to execute order for account {}: {}",
                                assignment.account_id, e
                            );
                            ExecutionResult {
                                signal_id: signal_id.clone(),
                                account_id: assignment.account_id.clone(),
                                order_id: None,
                                success: false,
                                error_message: Some(e.to_string()),
                                execution_time: start_time.elapsed(),
                                actual_entry_price: None,
                                slippage: None,
                            }
                        }
                    }
                } else {
                    ExecutionResult {
                        signal_id: signal_id.clone(),
                        account_id: assignment.account_id.clone(),
                        order_id: None,
                        success: false,
                        error_message: Some("Platform not found".to_string()),
                        execution_time: start_time.elapsed(),
                        actual_entry_price: None,
                        slippage: None,
                    }
                }
            });

            handles.push(handle);
        }

        for handle in handles {
            if let Ok(result) = handle.await {
                self.log_execution_result(&result).await;
                results.push(result);
            }
        }

        results
    }

    pub async fn handle_failed_execution(
        &self,
        result: &ExecutionResult,
        plan: &ExecutionPlan,
    ) -> Result<ExecutionResult, String> {
        warn!(
            "Handling failed execution for signal {} on account {}",
            result.signal_id, result.account_id
        );

        let alternative_accounts = self
            .find_alternative_accounts(&result.account_id, plan)
            .await?;

        if alternative_accounts.is_empty() {
            return Err("No alternative accounts available for retry".to_string());
        }

        let selected_account = &alternative_accounts[0];
        let assignment = plan
            .account_assignments
            .iter()
            .find(|a| a.account_id == result.account_id)
            .ok_or("Original assignment not found")?;

        let new_assignment = AccountAssignment {
            account_id: selected_account.clone(),
            position_size: assignment.position_size * 0.95,
            entry_timing_delay: Duration::from_millis(500),
            priority: 99,
        };

        let retry_plan = ExecutionPlan {
            signal_id: plan.signal_id.clone(),
            account_assignments: vec![new_assignment],
            timing_variance: HashMap::new(),
            size_variance: HashMap::new(),
            rationale: format!(
                "Retry execution on alternative account {}",
                selected_account
            ),
        };

        let retry_results = self.execute_plan(&retry_plan).await;

        retry_results
            .into_iter()
            .next()
            .ok_or_else(|| "Retry execution failed".to_string())
    }

    async fn find_alternative_accounts(
        &self,
        failed_account: &str,
        plan: &ExecutionPlan,
    ) -> Result<Vec<String>, String> {
        let accounts = self.accounts.read().await;
        let mut alternatives = Vec::new();

        let used_accounts: Vec<String> = plan
            .account_assignments
            .iter()
            .map(|a| a.account_id.clone())
            .collect();

        for (account_id, status) in accounts.iter() {
            if account_id == failed_account {
                continue;
            }

            if used_accounts.contains(account_id) {
                continue;
            }

            if status.is_active && status.available_margin > 1000.0 {
                alternatives.push(account_id.clone());
            }
        }

        Ok(alternatives)
    }

    async fn log_audit_entry(
        &self,
        signal_id: String,
        action: String,
        rationale: String,
        result: Option<ExecutionResult>,
    ) {
        let entry = ExecutionAuditEntry {
            id: Uuid::new_v4().to_string(),
            timestamp: SystemTime::now(),
            signal_id,
            account_id: result
                .as_ref()
                .map(|r| r.account_id.clone())
                .unwrap_or_default(),
            action,
            decision_rationale: rationale,
            result,
            metadata: HashMap::new(),
        };

        let mut history = self.execution_history.write().await;
        history.push(entry);

        if history.len() > 10000 {
            history.drain(0..1000);
        }
    }

    async fn log_execution_result(&self, result: &ExecutionResult) {
        let action = if result.success {
            "EXECUTION_SUCCESS"
        } else {
            "EXECUTION_FAILED"
        };
        let rationale = result
            .error_message
            .clone()
            .unwrap_or_else(|| format!("Order executed in {:?}", result.execution_time));

        self.log_audit_entry(
            result.signal_id.clone(),
            action.to_string(),
            rationale,
            Some(result.clone()),
        )
        .await;
    }

    pub async fn update_correlation_matrix(
        &self,
        account1: &str,
        account2: &str,
        correlation: f64,
    ) {
        let mut matrix = self.correlation_matrix.write().await;
        let key = if account1 < account2 {
            (account1.to_string(), account2.to_string())
        } else {
            (account2.to_string(), account1.to_string())
        };
        matrix.insert(key, correlation);
    }

    pub async fn get_execution_history(&self, limit: usize) -> Vec<ExecutionAuditEntry> {
        let history = self.execution_history.read().await;
        let start = if history.len() > limit {
            history.len() - limit
        } else {
            0
        };
        history[start..].to_vec()
    }

    pub async fn get_account_status(&self, account_id: &str) -> Option<AccountStatus> {
        let accounts = self.accounts.read().await;
        accounts.get(account_id).cloned()
    }

    pub async fn pause_account(&self, account_id: &str) -> Result<(), String> {
        let mut accounts = self.accounts.write().await;
        if let Some(account) = accounts.get_mut(account_id) {
            account.is_active = false;
            info!("Paused account {}", account_id);
            Ok(())
        } else {
            Err(format!("Account {} not found", account_id))
        }
    }

    pub async fn resume_account(&self, account_id: &str) -> Result<(), String> {
        let mut accounts = self.accounts.write().await;
        if let Some(account) = accounts.get_mut(account_id) {
            account.is_active = true;
            info!("Resumed account {}", account_id);
            Ok(())
        } else {
            Err(format!("Account {} not found", account_id))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_orchestrator_creation() {
        let orchestrator = TradeExecutionOrchestrator::new();
        assert_eq!(orchestrator.max_correlation_threshold, 0.7);
        assert_eq!(orchestrator.min_timing_variance_ms, 1000);
        assert_eq!(orchestrator.max_timing_variance_ms, 30000);
    }
}
