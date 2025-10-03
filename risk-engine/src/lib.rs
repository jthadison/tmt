#![allow(clippy::too_many_arguments)]
#![allow(clippy::redundant_field_names)]
#![allow(clippy::uninlined_format_args)]
#![allow(clippy::new_without_default)]
#![allow(clippy::unwrap_or_default)]
#![allow(clippy::should_implement_trait)]
#![allow(clippy::to_string_trait_impl)]
#![allow(clippy::unnecessary_map_or)]
#![allow(clippy::redundant_closure)]
#![allow(dead_code)]
#![allow(unused_imports)]
#![allow(unused_variables)]
#![allow(unused_mut)]
#![allow(unused_assignments)]

pub mod config;
// Use shared types instead of local types
pub use risk_types;
pub mod drawdown_tracker;
pub mod exposure_monitor;
pub mod margin_monitor;
pub mod pnl_calculator;
pub mod risk_response;
pub mod risk_reward_tracker;

pub use config::{
    load_config, DrawdownThresholds, ExposureLimits, MarginThresholds, RiskConfig,
    RiskResponseConfig,
};
pub use drawdown_tracker::{
    DrawdownAlert, DrawdownAlertManager, DrawdownAlertType, DrawdownTracker, EquityHistoryManager,
};
pub use exposure_monitor::{
    AccountExposure, CurrencyExposureCalculator, ExposureAlertManager, ExposureMonitor,
    RebalanceAction, RebalancePriority, RebalanceRecommendation,
};
pub use margin_monitor::{
    Account, AccountManager, MarginAlertManager, MarginCalculator, MarginImpact, MarginMonitor,
    MarginProtectionSystem, MarginRequirements, ProposedPosition,
};
pub use pnl_calculator::{
    AccountPnL, KafkaProducer, MarketDataStream, PositionTracker, RealTimePnLCalculator,
    WebSocketPublisher,
};
pub use risk_response::{
    AuditEntry, CircuitBreakerClient, PositionClosureResult, PositionManager,
    PositionReductionResult, ResponseExecutor, RiskAuditLogger, RiskResponseSystem, RiskThresholds,
};
pub use risk_reward_tracker::{
    MarketDataProvider, PortfolioRRSummary, RRAlertType, RiskRewardAlert, RiskRewardAlertManager,
    RiskRewardTracker, TargetOptimization,
};
pub use risk_types::*;
