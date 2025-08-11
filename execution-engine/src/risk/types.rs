use chrono::{DateTime, Utc};
use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

pub type AccountId = Uuid;
pub type PositionId = Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Position {
    pub id: PositionId,
    pub account_id: AccountId,
    pub symbol: String,
    pub position_type: PositionType,
    pub size: Decimal,
    pub entry_price: Decimal,
    pub current_price: Option<Decimal>,
    pub unrealized_pnl: Option<Decimal>,
    pub max_favorable_excursion: Decimal,
    pub max_adverse_excursion: Decimal,
    pub stop_loss: Option<Decimal>,
    pub take_profit: Option<Decimal>,
    pub opened_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum PositionType {
    Long,
    Short,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PnLSnapshot {
    pub position_id: PositionId,
    pub unrealized_pnl: Decimal,
    pub unrealized_pnl_percentage: Decimal,
    pub max_favorable_excursion: Decimal,
    pub max_adverse_excursion: Decimal,
    pub current_price: Decimal,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PnLUpdate {
    pub position_id: PositionId,
    pub account_id: AccountId,
    pub symbol: String,
    pub unrealized_pnl: Decimal,
    pub unrealized_pnl_percentage: Decimal,
    pub current_price: Decimal,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarketTick {
    pub symbol: String,
    pub bid: Decimal,
    pub ask: Decimal,
    pub price: Decimal,
    pub volume: Decimal,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DrawdownMetrics {
    pub daily_drawdown: DrawdownData,
    pub weekly_drawdown: DrawdownData,
    pub maximum_drawdown: DrawdownData,
    pub current_underwater_period: chrono::Duration,
    pub recovery_factor: Decimal,
    pub last_updated: DateTime<Utc>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct DrawdownData {
    pub amount: Decimal,
    pub percentage: Decimal,
    pub peak_equity: Decimal,
    pub current_equity: Decimal,
    pub start_time: DateTime<Utc>,
    pub duration: chrono::Duration,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EquityPoint {
    pub equity: Decimal,
    pub balance: Decimal,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExposureReport {
    pub pair_exposure: HashMap<String, ExposureData>,
    pub currency_exposure: HashMap<String, Decimal>,
    pub total_exposure: Decimal,
    pub limit_violations: Vec<ExposureLimitViolation>,
    pub concentration_risk: ConcentrationRisk,
    pub diversification_score: Decimal,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ExposureData {
    pub long_exposure: Decimal,
    pub short_exposure: Decimal,
    pub net_exposure: Decimal,
    pub total_exposure: Decimal,
    pub position_count: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExposureLimitViolation {
    pub limit_type: String,
    pub current_value: Decimal,
    pub limit_value: Decimal,
    pub severity: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConcentrationRisk {
    pub herfindahl_index: Decimal,
    pub concentration_level: ConcentrationLevel,
    pub largest_position_percentage: Decimal,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum ConcentrationLevel {
    Low,
    Moderate,
    High,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskRewardMetrics {
    pub position_id: PositionId,
    pub current_rr_ratio: Decimal,
    pub max_favorable_excursion: Decimal,
    pub max_adverse_excursion: Decimal,
    pub distance_to_stop: Decimal,
    pub distance_to_target: Decimal,
    pub performance_score: Decimal,
    pub recommendation: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarginInfo {
    pub account_id: AccountId,
    pub balance: Decimal,
    pub equity: Decimal,
    pub used_margin: Decimal,
    pub free_margin: Decimal,
    pub margin_level: Decimal,
    pub positions_count: usize,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone)]
pub struct MarginThresholds {
    pub warning_level: Decimal,
    pub critical_level: Decimal,
    pub stop_out_level: Decimal,
}

impl Default for MarginThresholds {
    fn default() -> Self {
        Self {
            warning_level: Decimal::from(150),
            critical_level: Decimal::from(120),
            stop_out_level: Decimal::from(100),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarginAlert {
    pub account_id: AccountId,
    pub level: AlertLevel,
    pub margin_level: Decimal,
    pub threshold: Decimal,
    pub message: String,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum AlertLevel {
    Info,
    Warning,
    Critical,
    Emergency,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskEvent {
    pub event_id: Uuid,
    pub account_id: AccountId,
    pub risk_type: String,
    pub description: String,
    pub metric_value: Decimal,
    pub threshold_value: Decimal,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum RiskSeverity {
    Low,
    Medium,
    High,
    Critical,
    Extreme,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ResponseAction {
    Monitor,
    ReducePositions {
        account_id: AccountId,
        reduction_percentage: Decimal,
        priority: ReductionPriority,
    },
    ReducePositionSize {
        account_id: AccountId,
        new_risk_percentage: Decimal,
    },
    DiversifyPositions {
        account_id: AccountId,
        max_exposure_per_symbol: Decimal,
    },
    ReduceCorrelatedPositions {
        account_id: AccountId,
        correlation_threshold: Decimal,
        reduction_factor: Decimal,
    },
    EmergencyStop {
        scope: EmergencyStopScope,
        reason: String,
    },
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum ReductionPriority {
    LargestLoss,
    LargestPosition,
    OldestPosition,
    MostCorrelated,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum EmergencyStopScope {
    Position(PositionId),
    Account(AccountId),
    System,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskResponse {
    pub risk_event: RiskEvent,
    pub severity: RiskSeverity,
    pub action_taken: ResponseAction,
    pub execution_result: ResponseExecutionResult,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ResponseExecutionResult {
    MonitoringContinued,
    PositionsReduced {
        positions_affected: usize,
        total_reduction: Decimal,
    },
    EmergencyStopTriggered {
        scope: EmergencyStopScope,
        timestamp: DateTime<Utc>,
    },
    Failed {
        reason: String,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskUpdate {
    pub account_id: AccountId,
    pub update_type: String,
    pub current_value: Decimal,
    pub previous_value: Option<Decimal>,
    pub threshold_status: String,
    pub timestamp: DateTime<Utc>,
}