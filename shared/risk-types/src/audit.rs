use chrono::{DateTime, Utc};
use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;
use anyhow::Result;

/// Comprehensive audit logging for risk management decisions
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskAuditLog {
    /// Unique identifier for this audit entry
    pub entry_id: Uuid,
    /// Account ID associated with the risk decision
    pub account_id: Uuid,
    /// Type of risk decision made
    pub decision_type: RiskDecisionType,
    /// Details of the risk decision
    pub decision_details: RiskDecisionDetails,
    /// Context that led to the decision
    pub decision_context: DecisionContext,
    /// Who/what made the decision (AI agent, user, system)
    pub decision_maker: String,
    /// Outcome of the decision
    pub outcome: Option<DecisionOutcome>,
    /// Timestamp when decision was made
    pub timestamp: DateTime<Utc>,
    /// Additional metadata
    pub metadata: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RiskDecisionType {
    /// Position size adjustment
    PositionSizeAdjustment {
        position_id: Uuid,
        original_size: Decimal,
        new_size: Decimal,
        reason: String,
    },
    /// Position closure
    PositionClosure {
        position_id: Uuid,
        closure_reason: String,
        pnl_at_closure: Decimal,
    },
    /// Emergency stop triggered
    EmergencyStop {
        scope: String, // Account, Position, System
        trigger_reason: String,
        affected_positions: Vec<Uuid>,
    },
    /// Risk limit modification
    RiskLimitChange {
        limit_type: String,
        previous_value: Decimal,
        new_value: Decimal,
        justification: String,
    },
    /// Margin call response
    MarginCallResponse {
        margin_level: Decimal,
        action_taken: String,
        positions_affected: Vec<Uuid>,
    },
    /// Drawdown response
    DrawdownResponse {
        drawdown_percentage: Decimal,
        max_drawdown: Decimal,
        response_action: String,
    },
    /// Exposure limit violation
    ExposureViolation {
        violation_type: String,
        current_exposure: Decimal,
        limit_exceeded: Decimal,
        corrective_action: String,
    },
    /// Correlation-based adjustment
    CorrelationAdjustment {
        correlation_coefficient: Decimal,
        positions_affected: Vec<Uuid>,
        adjustment_reason: String,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskDecisionDetails {
    /// Risk metrics at time of decision
    pub risk_metrics: RiskMetricsSnapshot,
    /// Account status at time of decision
    pub account_status: AccountStatusSnapshot,
    /// Market conditions at time of decision
    pub market_conditions: MarketConditionsSnapshot,
    /// Previous related decisions (for tracking patterns)
    pub related_decisions: Vec<Uuid>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskMetricsSnapshot {
    /// P&L metrics
    pub unrealized_pnl: Decimal,
    pub realized_pnl: Decimal,
    /// Drawdown metrics
    pub current_drawdown: Decimal,
    pub max_drawdown: Decimal,
    /// Exposure metrics
    pub total_exposure: Decimal,
    pub largest_position_exposure: Decimal,
    /// Margin metrics
    pub margin_level: Decimal,
    pub free_margin: Decimal,
    /// Risk/reward metrics
    pub average_risk_reward: Decimal,
    pub win_rate: Decimal,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AccountStatusSnapshot {
    pub account_balance: Decimal,
    pub account_equity: Decimal,
    pub positions_count: usize,
    pub active_orders_count: usize,
    pub account_age_days: i64,
    pub trading_activity_score: Decimal,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarketConditionsSnapshot {
    pub volatility_index: Decimal,
    pub market_session: String, // Asian, European, American
    pub news_impact_score: Decimal, // High impact news events
    pub liquidity_score: Decimal,
    pub correlation_environment: String, // High, Normal, Low correlation
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecisionContext {
    /// What triggered this decision
    pub trigger_event: String,
    /// Threshold values that were breached
    pub threshold_breaches: Vec<ThresholdBreach>,
    /// Time since last similar decision
    pub time_since_last_decision: Option<chrono::Duration>,
    /// Urgency level of the decision
    pub urgency_level: UrgencyLevel,
    /// Whether this was an automated or manual decision
    pub decision_mode: DecisionMode,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThresholdBreach {
    pub threshold_name: String,
    pub threshold_value: Decimal,
    pub current_value: Decimal,
    pub breach_severity: BreachSeverity,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum BreachSeverity {
    Minor,      // 0-10% over threshold
    Moderate,   // 10-25% over threshold
    Severe,     // 25-50% over threshold
    Critical,   // 50%+ over threshold
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum UrgencyLevel {
    Low,        // Can be delayed
    Normal,     // Process normally
    High,       // Process quickly
    Critical,   // Process immediately
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum DecisionMode {
    Automated,  // Made by AI/system
    SemiAuto,   // AI recommendation, human approval
    Manual,     // Human decision
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecisionOutcome {
    /// Whether the decision was executed successfully
    pub execution_success: bool,
    /// Time taken to execute the decision
    pub execution_time_ms: u64,
    /// Any errors encountered during execution
    pub execution_errors: Vec<String>,
    /// Impact on account metrics
    pub impact_metrics: ImpactMetrics,
    /// Follow-up actions required
    pub follow_up_actions: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImpactMetrics {
    /// Change in P&L after decision
    pub pnl_impact: Decimal,
    /// Change in risk exposure
    pub exposure_impact: Decimal,
    /// Change in margin utilization
    pub margin_impact: Decimal,
    /// Number of positions affected
    pub positions_affected: usize,
    /// Estimated financial impact (USD)
    pub estimated_financial_impact: Decimal,
}

/// Audit logger for risk decisions
pub struct RiskAuditLogger {
    /// Storage backend for audit logs
    log_entries: Vec<RiskAuditLog>,
    /// Configuration for audit logging
    config: AuditConfig,
}

#[derive(Debug, Clone)]
pub struct AuditConfig {
    /// Maximum number of audit entries to keep in memory
    pub max_entries: usize,
    /// Whether to log all decisions or only significant ones
    pub log_level: AuditLogLevel,
    /// Retention period for audit logs
    pub retention_days: u32,
    /// Whether to encrypt audit logs
    pub encrypt_logs: bool,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum AuditLogLevel {
    /// Log only critical decisions
    Critical,
    /// Log important decisions
    Important,
    /// Log all decisions
    All,
}

impl Default for AuditConfig {
    fn default() -> Self {
        Self {
            max_entries: 10000,
            log_level: AuditLogLevel::All,
            retention_days: 2555, // 7 years for compliance
            encrypt_logs: true,
        }
    }
}

impl RiskAuditLogger {
    pub fn new(config: AuditConfig) -> Self {
        Self {
            log_entries: Vec::new(),
            config,
        }
    }

    /// Log a risk decision with full context
    pub fn log_decision(&mut self, mut log_entry: RiskAuditLog) -> Result<()> {
        // Add unique ID if not provided
        if log_entry.entry_id == Uuid::nil() {
            log_entry.entry_id = Uuid::new_v4();
        }

        // Validate the log entry
        self.validate_log_entry(&log_entry)?;

        // Check if we should log this entry based on config
        if !self.should_log(&log_entry) {
            return Ok(());
        }

        // Add to storage
        self.log_entries.push(log_entry);

        // Maintain size limits
        if self.log_entries.len() > self.config.max_entries {
            self.log_entries.remove(0); // Remove oldest entry
        }

        Ok(())
    }

    /// Log a position size adjustment decision
    pub fn log_position_adjustment(
        &mut self,
        account_id: Uuid,
        position_id: Uuid,
        original_size: Decimal,
        new_size: Decimal,
        reason: String,
        context: DecisionContext,
        outcome: Option<DecisionOutcome>,
    ) -> Result<()> {
        let log_entry = RiskAuditLog {
            entry_id: Uuid::new_v4(),
            account_id,
            decision_type: RiskDecisionType::PositionSizeAdjustment {
                position_id,
                original_size,
                new_size,
                reason,
            },
            decision_details: RiskDecisionDetails {
                risk_metrics: RiskMetricsSnapshot::default(),
                account_status: AccountStatusSnapshot::default(),
                market_conditions: MarketConditionsSnapshot::default(),
                related_decisions: Vec::new(),
            },
            decision_context: context,
            decision_maker: "RiskManagementSystem".to_string(),
            outcome,
            timestamp: Utc::now(),
            metadata: HashMap::new(),
        };

        self.log_decision(log_entry)
    }

    /// Log an emergency stop decision
    pub fn log_emergency_stop(
        &mut self,
        account_id: Uuid,
        scope: String,
        trigger_reason: String,
        affected_positions: Vec<Uuid>,
        context: DecisionContext,
        outcome: Option<DecisionOutcome>,
    ) -> Result<()> {
        let log_entry = RiskAuditLog {
            entry_id: Uuid::new_v4(),
            account_id,
            decision_type: RiskDecisionType::EmergencyStop {
                scope,
                trigger_reason,
                affected_positions,
            },
            decision_details: RiskDecisionDetails {
                risk_metrics: RiskMetricsSnapshot::default(),
                account_status: AccountStatusSnapshot::default(),
                market_conditions: MarketConditionsSnapshot::default(),
                related_decisions: Vec::new(),
            },
            decision_context: context,
            decision_maker: "EmergencyStopSystem".to_string(),
            outcome,
            timestamp: Utc::now(),
            metadata: HashMap::new(),
        };

        self.log_decision(log_entry)
    }

    /// Query audit logs by account
    pub fn get_account_audit_history(&self, account_id: Uuid) -> Vec<&RiskAuditLog> {
        self.log_entries
            .iter()
            .filter(|entry| entry.account_id == account_id)
            .collect()
    }

    /// Query audit logs by decision type
    pub fn get_decisions_by_type(&self, decision_type: &str) -> Vec<&RiskAuditLog> {
        self.log_entries
            .iter()
            .filter(|entry| {
                match &entry.decision_type {
                    RiskDecisionType::PositionSizeAdjustment { .. } => decision_type == "position_size",
                    RiskDecisionType::PositionClosure { .. } => decision_type == "position_closure",
                    RiskDecisionType::EmergencyStop { .. } => decision_type == "emergency_stop",
                    RiskDecisionType::RiskLimitChange { .. } => decision_type == "risk_limit",
                    RiskDecisionType::MarginCallResponse { .. } => decision_type == "margin_call",
                    RiskDecisionType::DrawdownResponse { .. } => decision_type == "drawdown",
                    RiskDecisionType::ExposureViolation { .. } => decision_type == "exposure",
                    RiskDecisionType::CorrelationAdjustment { .. } => decision_type == "correlation",
                }
            })
            .collect()
    }

    /// Get decisions within a time range
    pub fn get_decisions_in_range(
        &self,
        start: DateTime<Utc>,
        end: DateTime<Utc>,
    ) -> Vec<&RiskAuditLog> {
        self.log_entries
            .iter()
            .filter(|entry| entry.timestamp >= start && entry.timestamp <= end)
            .collect()
    }

    /// Generate audit report
    pub fn generate_audit_report(&self, account_id: Option<Uuid>) -> AuditReport {
        let entries = if let Some(account_id) = account_id {
            self.get_account_audit_history(account_id)
        } else {
            self.log_entries.iter().collect()
        };

        AuditReport::new(entries)
    }

    /// Export audit logs for compliance
    pub fn export_for_compliance(&self) -> Result<String> {
        let export_data = serde_json::to_string_pretty(&self.log_entries)?;
        Ok(export_data)
    }

    fn validate_log_entry(&self, entry: &RiskAuditLog) -> Result<()> {
        if entry.account_id == Uuid::nil() {
            return Err(anyhow::anyhow!("Account ID cannot be nil"));
        }

        if entry.decision_maker.is_empty() {
            return Err(anyhow::anyhow!("Decision maker must be specified"));
        }

        Ok(())
    }

    fn should_log(&self, entry: &RiskAuditLog) -> bool {
        match self.config.log_level {
            AuditLogLevel::All => true,
            AuditLogLevel::Important => {
                matches!(
                    entry.decision_type,
                    RiskDecisionType::EmergencyStop { .. }
                        | RiskDecisionType::MarginCallResponse { .. }
                        | RiskDecisionType::DrawdownResponse { .. }
                )
            },
            AuditLogLevel::Critical => {
                matches!(entry.decision_type, RiskDecisionType::EmergencyStop { .. })
            },
        }
    }
}

/// Audit report for compliance and analysis
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditReport {
    pub report_id: Uuid,
    pub generated_at: DateTime<Utc>,
    pub total_decisions: usize,
    pub decisions_by_type: HashMap<String, usize>,
    pub decisions_by_urgency: HashMap<String, usize>,
    pub execution_success_rate: f64,
    pub average_execution_time_ms: f64,
    pub most_common_triggers: Vec<(String, usize)>,
    pub high_impact_decisions: Vec<Uuid>,
}

impl AuditReport {
    fn new(entries: Vec<&RiskAuditLog>) -> Self {
        let mut decisions_by_type = HashMap::new();
        let mut decisions_by_urgency = HashMap::new();
        let mut execution_times = Vec::new();
        let mut successful_executions = 0;
        let mut trigger_counts = HashMap::new();
        let mut high_impact_decisions = Vec::new();

        for entry in &entries {
            // Count by type
            let type_key = match &entry.decision_type {
                RiskDecisionType::PositionSizeAdjustment { .. } => "position_size",
                RiskDecisionType::PositionClosure { .. } => "position_closure",
                RiskDecisionType::EmergencyStop { .. } => "emergency_stop",
                RiskDecisionType::RiskLimitChange { .. } => "risk_limit",
                RiskDecisionType::MarginCallResponse { .. } => "margin_call",
                RiskDecisionType::DrawdownResponse { .. } => "drawdown",
                RiskDecisionType::ExposureViolation { .. } => "exposure",
                RiskDecisionType::CorrelationAdjustment { .. } => "correlation",
            };
            *decisions_by_type.entry(type_key.to_string()).or_insert(0) += 1;

            // Count by urgency
            let urgency_key = format!("{:?}", entry.decision_context.urgency_level);
            *decisions_by_urgency.entry(urgency_key).or_insert(0) += 1;

            // Track execution metrics
            if let Some(outcome) = &entry.outcome {
                if outcome.execution_success {
                    successful_executions += 1;
                }
                execution_times.push(outcome.execution_time_ms);

                // Check for high impact
                if outcome.impact_metrics.estimated_financial_impact.abs() > Decimal::from(1000) {
                    high_impact_decisions.push(entry.entry_id);
                }
            }

            // Count triggers
            *trigger_counts.entry(entry.decision_context.trigger_event.clone()).or_insert(0) += 1;
        }

        let execution_success_rate = if entries.is_empty() {
            0.0
        } else {
            successful_executions as f64 / entries.len() as f64 * 100.0
        };

        let average_execution_time_ms = if execution_times.is_empty() {
            0.0
        } else {
            execution_times.iter().sum::<u64>() as f64 / execution_times.len() as f64
        };

        let mut most_common_triggers: Vec<_> = trigger_counts.into_iter().collect();
        most_common_triggers.sort_by(|a, b| b.1.cmp(&a.1));
        most_common_triggers.truncate(10); // Top 10 triggers

        Self {
            report_id: Uuid::new_v4(),
            generated_at: Utc::now(),
            total_decisions: entries.len(),
            decisions_by_type,
            decisions_by_urgency,
            execution_success_rate,
            average_execution_time_ms,
            most_common_triggers,
            high_impact_decisions,
        }
    }
}

impl Default for RiskMetricsSnapshot {
    fn default() -> Self {
        Self {
            unrealized_pnl: Decimal::ZERO,
            realized_pnl: Decimal::ZERO,
            current_drawdown: Decimal::ZERO,
            max_drawdown: Decimal::ZERO,
            total_exposure: Decimal::ZERO,
            largest_position_exposure: Decimal::ZERO,
            margin_level: Decimal::ZERO,
            free_margin: Decimal::ZERO,
            average_risk_reward: Decimal::ZERO,
            win_rate: Decimal::ZERO,
        }
    }
}

impl Default for AccountStatusSnapshot {
    fn default() -> Self {
        Self {
            account_balance: Decimal::ZERO,
            account_equity: Decimal::ZERO,
            positions_count: 0,
            active_orders_count: 0,
            account_age_days: 0,
            trading_activity_score: Decimal::ZERO,
        }
    }
}

impl Default for MarketConditionsSnapshot {
    fn default() -> Self {
        Self {
            volatility_index: Decimal::ZERO,
            market_session: "Unknown".to_string(),
            news_impact_score: Decimal::ZERO,
            liquidity_score: Decimal::ZERO,
            correlation_environment: "Normal".to_string(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_audit_logger_creation() {
        let config = AuditConfig::default();
        let logger = RiskAuditLogger::new(config);
        assert_eq!(logger.log_entries.len(), 0);
    }

    #[test]
    fn test_position_adjustment_logging() {
        let mut logger = RiskAuditLogger::new(AuditConfig::default());
        let account_id = Uuid::new_v4();
        let position_id = Uuid::new_v4();

        let context = DecisionContext {
            trigger_event: "Risk limit exceeded".to_string(),
            threshold_breaches: vec![],
            time_since_last_decision: None,
            urgency_level: UrgencyLevel::High,
            decision_mode: DecisionMode::Automated,
        };

        logger.log_position_adjustment(
            account_id,
            position_id,
            Decimal::from(100000),
            Decimal::from(75000),
            "Reduce exposure".to_string(),
            context,
            None,
        ).unwrap();

        assert_eq!(logger.log_entries.len(), 1);
        assert_eq!(logger.log_entries[0].account_id, account_id);
    }

    #[test]
    fn test_audit_report_generation() {
        let logger = RiskAuditLogger::new(AuditConfig::default());
        let report = logger.generate_audit_report(None);
        
        assert_eq!(report.total_decisions, 0);
        assert!(report.decisions_by_type.is_empty());
    }

    #[test]
    fn test_compliance_export() {
        let logger = RiskAuditLogger::new(AuditConfig::default());
        let export = logger.export_for_compliance().unwrap();
        
        // Should be valid JSON
        let _: Vec<RiskAuditLog> = serde_json::from_str(&export).unwrap();
    }
}