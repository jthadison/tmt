pub use crate::platforms::abstraction::models::UnifiedPositionSide;
use chrono::{DateTime, Duration, Utc};
use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

pub type PositionId = Uuid;
pub type OrderId = String;
pub type Symbol = String;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrailingConfig {
    pub atr_multiplier: f64,
    pub min_trail_distance: f64,
    pub max_trail_distance: f64,
    pub activation_threshold: f64,
    pub symbol: String,
    pub timeframe: String,
}

impl Default for TrailingConfig {
    fn default() -> Self {
        Self {
            atr_multiplier: 2.0,
            min_trail_distance: 0.0010,   // 10 pips for EURUSD
            max_trail_distance: 0.0100,   // 100 pips
            activation_threshold: 0.0015, // 15 pips profit before trailing starts
            symbol: "EURUSD".to_string(),
            timeframe: "H1".to_string(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActiveTrail {
    pub position_id: PositionId,
    pub trail_level: f64,
    pub original_stop: f64,
    pub position_type: UnifiedPositionSide,
    pub last_updated: DateTime<Utc>,
    pub update_count: u32,
    pub activation_price: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrailUpdate {
    pub position_id: PositionId,
    pub old_level: f64,
    pub new_level: f64,
    pub atr_used: f64,
    pub distance_pips: f64,
    pub trigger_price: f64,
    pub update_reason: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BreakEvenConfig {
    pub trigger_ratio: f64, // 1.0 for 1:1 R:R
    pub break_even_buffer_pips: f64,
    pub enabled: bool,
}

impl Default for BreakEvenConfig {
    fn default() -> Self {
        Self {
            trigger_ratio: 1.0,
            break_even_buffer_pips: 5.0,
            enabled: true,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProfitTakingConfig {
    pub profit_targets: Vec<ProfitTarget>,
    pub enabled: bool,
}

impl Default for ProfitTakingConfig {
    fn default() -> Self {
        Self {
            profit_targets: vec![
                ProfitTarget {
                    level: 1,
                    risk_reward_ratio: 1.0,
                    close_percentage: 0.5, // Close 50% at 1:1
                },
                ProfitTarget {
                    level: 2,
                    risk_reward_ratio: 2.0,
                    close_percentage: 0.25, // Close 25% at 2:1
                },
            ],
            enabled: true,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProfitTarget {
    pub level: u32,
    pub risk_reward_ratio: f64,
    pub close_percentage: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimeExitConfig {
    pub max_hold_duration: Duration,
    pub warning_duration: Duration,
    pub enabled: bool,
    pub trend_strength_override_threshold: f64,
}

impl Default for TimeExitConfig {
    fn default() -> Self {
        Self {
            max_hold_duration: Duration::from_std(std::time::Duration::from_secs(24 * 3600))
                .unwrap(),
            warning_duration: Duration::from_std(std::time::Duration::from_secs(20 * 3600))
                .unwrap(),
            enabled: true,
            trend_strength_override_threshold: 0.8,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NewsProtectionConfig {
    pub protection_strategy: NewsProtectionStrategy,
    pub stop_tighten_factor: f64, // 0.5 = reduce stop distance by 50%
    pub lookback_hours: u32,
    pub currencies: Vec<String>,
    pub enabled: bool,
}

impl Default for NewsProtectionConfig {
    fn default() -> Self {
        Self {
            protection_strategy: NewsProtectionStrategy::TightenStops,
            stop_tighten_factor: 0.5,
            lookback_hours: 2,
            currencies: vec!["USD".to_string(), "EUR".to_string()],
            enabled: true,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum NewsProtectionStrategy {
    TightenStops,
    ClosePosition,
    ReduceSize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NewsEvent {
    pub id: String,
    pub description: String,
    pub currency: String,
    pub impact: ImpactLevel,
    pub time: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ImpactLevel {
    Low,
    Medium,
    High,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NewsProtection {
    pub position_id: PositionId,
    pub original_stop: f64,
    pub protected_stop: f64,
    pub news_event: NewsEvent,
    pub protection_start: DateTime<Utc>,
    pub restoration_scheduled: Option<DateTime<Utc>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExitModification {
    pub position_id: PositionId,
    pub modification_type: ExitModificationType,
    pub old_value: f64,
    pub new_value: f64,
    pub reasoning: String,
    pub market_context: MarketContext,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum ExitModificationType {
    TrailingStop,
    BreakEven,
    PartialProfit,
    TimeExit,
    NewsProtection,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarketContext {
    pub current_price: f64,
    pub atr_14: f64,
    pub trend_strength: f64,
    pub volatility: f64,
    pub spread: f64,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExitResult {
    pub position_id: PositionId,
    pub exit_type: ExitModificationType,
    pub success: bool,
    pub exit_price: Option<f64>,
    pub volume_closed: Option<Decimal>,
    pub profit_loss: Option<Decimal>,
    pub message: String,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditEntry {
    pub entry_id: Uuid,
    pub position_id: PositionId,
    pub modification_type: ExitModificationType,
    pub old_value: f64,
    pub new_value: f64,
    pub reasoning: String,
    pub market_context: MarketContext,
    pub performance_impact: f64,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExitPerformanceReport {
    pub trailing_stop_stats: TrailingStopStats,
    pub break_even_stats: BreakEvenStats,
    pub partial_profit_stats: PartialProfitStats,
    pub time_exit_stats: TimeExitStats,
    pub news_protection_stats: NewsProtectionStats,
    pub overall_performance: f64,
    pub report_period: ReportPeriod,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrailingStopStats {
    pub total_trails: u32,
    pub successful_exits: u32,
    pub average_trail_distance: f64,
    pub profit_captured: Decimal,
    pub best_trail_profit: Decimal,
    pub worst_trail_loss: Decimal,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BreakEvenStats {
    pub break_even_activations: u32,
    pub successful_break_evens: u32,
    pub losses_prevented: Decimal,
    pub average_time_to_break_even: Duration,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PartialProfitStats {
    pub total_partials: u32,
    pub total_volume_closed: Decimal,
    pub average_profit_per_partial: Decimal,
    pub target_hit_rates: HashMap<u32, f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimeExitStats {
    pub time_exits_triggered: u32,
    pub average_hold_time: Duration,
    pub trend_overrides: u32,
    pub time_exit_pnl: Decimal,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NewsProtectionStats {
    pub protections_applied: u32,
    pub positions_closed_pre_news: u32,
    pub stops_tightened: u32,
    pub protection_effectiveness: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReportPeriod {
    pub start: DateTime<Utc>,
    pub end: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ATRCalculation {
    pub symbol: String,
    pub period: u32,
    pub current_atr: f64,
    pub normalized_atr: f64, // ATR as percentage of price
    pub calculation_time: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarketConditions {
    pub symbol: String,
    pub trend_strength: f64,
    pub volatility: f64,
    pub volume_profile: f64,
    pub support_resistance_levels: Vec<f64>,
    pub analysis_time: DateTime<Utc>,
}

// Missing platform model types for exit management compatibility
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderModifyRequest {
    pub order_id: String,
    pub new_stop_loss: Option<f64>,
    pub new_take_profit: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderModifyResult {
    pub order_id: String,
    pub success: bool,
    pub message: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClosePositionRequest {
    pub position_id: PositionId,
    pub reason: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PartialCloseRequest {
    pub position_id: PositionId,
    pub volume: Decimal,
    pub reason: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClosePositionResult {
    pub position_id: PositionId,
    pub close_price: f64,
    pub realized_pnl: Option<Decimal>,
    pub close_time: DateTime<Utc>,
}

// Simple position struct for exit management
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Position {
    pub id: PositionId,
    pub order_id: String,
    pub symbol: String,
    pub position_type: UnifiedPositionSide,
    pub volume: Decimal,
    pub entry_price: f64,
    pub current_price: f64,
    pub stop_loss: Option<f64>,
    pub take_profit: Option<f64>,
    pub unrealized_pnl: f64,
    pub swap: f64,
    pub commission: f64,
    pub open_time: DateTime<Utc>,
    pub magic_number: Option<i32>,
    pub comment: Option<String>,
}

// Simple market data for exit management
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarketData {
    pub symbol: String,
    pub bid: f64,
    pub ask: f64,
    pub spread: f64,
    pub timestamp: DateTime<Utc>,
}
