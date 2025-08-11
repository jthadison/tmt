pub mod orchestrator;
pub mod coordinator;

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

#[cfg(test)]
pub use mock_platform::MockTradingPlatform;