pub mod coordinator;
pub mod exit_management;
pub mod orchestrator;

#[cfg(test)]
pub mod mock_platform;

#[cfg(test)]
mod simple_test;

pub use orchestrator::{
    AccountAssignment, AccountStatus, ExecutionAuditEntry, ExecutionPlan, ExecutionResult,
    TradeExecutionOrchestrator, TradeSignal,
};

pub use coordinator::{ExecutionCoordinator, ExecutionMonitor, ExecutionSummary, PartialFill};

pub use exit_management::{
    BreakEvenManager, ExitAuditLogger, ExitManagementSystem, NewsEventProtection,
    PartialProfitManager, TimeBasedExitManager, TrailingStopManager,
};

#[cfg(test)]
pub use mock_platform::MockTradingPlatform;
