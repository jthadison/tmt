pub mod config;
// Use shared types instead of local types
pub use risk_types;
pub mod pnl_calculator;
pub mod drawdown_tracker;
pub mod exposure_monitor;
pub mod risk_reward_tracker;
pub mod margin_monitor;
pub mod risk_response;

pub use config::{RiskConfig, load_config, DrawdownThresholds, MarginThresholds, ExposureLimits, RiskResponseConfig};
pub use risk_types::*;
pub use pnl_calculator::{RealTimePnLCalculator, PositionTracker, MarketDataStream, WebSocketPublisher, KafkaProducer, AccountPnL};
pub use drawdown_tracker::{DrawdownTracker, EquityHistoryManager, DrawdownAlertManager, DrawdownAlert, DrawdownAlertType};
pub use exposure_monitor::{ExposureMonitor, CurrencyExposureCalculator, ExposureAlertManager, AccountExposure, RebalanceRecommendation, RebalanceAction, RebalancePriority};
pub use risk_reward_tracker::{RiskRewardTracker, MarketDataProvider, RiskRewardAlertManager, RiskRewardAlert, RRAlertType, PortfolioRRSummary, TargetOptimization};
pub use margin_monitor::{MarginMonitor, AccountManager, MarginCalculator, MarginAlertManager, MarginProtectionSystem, Account, ProposedPosition, MarginRequirements, MarginImpact};
pub use risk_response::{RiskResponseSystem, RiskThresholds, PositionManager, CircuitBreakerClient, RiskAuditLogger, ResponseExecutor, AuditEntry, PositionReductionResult, PositionClosureResult};