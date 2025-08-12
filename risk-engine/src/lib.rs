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
