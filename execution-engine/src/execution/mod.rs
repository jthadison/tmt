pub mod orchestrator;
pub mod coordinator;
pub mod exit_management;

#[cfg(test)]
pub mod mock_platform;

#[cfg(test)]
mod simple_test;

pub use orchestrator::{
    TradeExecutionOrchestrator,
    TradeSignal,
    ExecutionPlan,
    ExecutionResult,
    AccountStatus,
    AccountAssignment,
    ExecutionAuditEntry,
};

pub use coordinator::{
    ExecutionCoordinator,
    ExecutionMonitor,
    PartialFill,
    ExecutionSummary,
};

pub use exit_management::{
    ExitManagementSystem,
    TrailingStopManager,
    BreakEvenManager,
    PartialProfitManager,
    TimeBasedExitManager,
    NewsEventProtection,
    ExitAuditLogger,
};

#[cfg(test)]
pub use mock_platform::MockTradingPlatform;