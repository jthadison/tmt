# Trade Execution Orchestrator API Documentation

## Overview

The Trade Execution Orchestrator is a sophisticated system for managing trade execution across multiple prop firm accounts with built-in anti-correlation, timing variance, and failure recovery mechanisms. It implements Story 4.4 of the Trading System requirements.

## Core Components

### 1. TradeExecutionOrchestrator

The main orchestrator responsible for coordinating trade execution across multiple accounts.

#### Key Features
- Account selection based on available margin and risk budget
- Trade distribution with anti-correlation logic
- Execution timing variance (1-30 seconds) between accounts
- Partial fill handling with completion monitoring
- Failed execution recovery with alternative account routing
- Comprehensive audit logging with timestamps and decision rationale

### 2. ExecutionCoordinator

Handles monitoring and recovery of partial fills and failed executions.

## API Reference

### TradeExecutionOrchestrator

#### `new() -> Self`
Creates a new instance of the Trade Execution Orchestrator.

```rust
let orchestrator = TradeExecutionOrchestrator::new();
```

#### `register_account(account_id: String, platform: Arc<dyn TradingPlatform>, initial_balance: f64) -> Result<(), String>`
Registers a new trading account with the orchestrator.

```rust
orchestrator.register_account(
    "account_1".to_string(),
    platform,
    10000.0,
).await?;
```

#### `process_signal(signal: TradeSignal) -> Result<ExecutionPlan, String>`
Processes a trading signal and creates an execution plan.

```rust
let signal = TradeSignal {
    id: "signal_001".to_string(),
    symbol: "EURUSD".to_string(),
    side: OrderSide::Buy,
    entry_price: 1.0900,
    stop_loss: 1.0850,
    take_profit: 1.1000,
    confidence: 0.85,
    risk_reward_ratio: 2.0,
    signal_time: SystemTime::now(),
    metadata: HashMap::new(),
};

let plan = orchestrator.process_signal(signal).await?;
```

#### `execute_plan(plan: &ExecutionPlan) -> Vec<ExecutionResult>`
Executes a trading plan across assigned accounts.

```rust
let results = orchestrator.execute_plan(&plan).await;
for result in results {
    if result.success {
        println!("Order {} executed successfully", result.order_id.unwrap());
    }
}
```

#### `handle_failed_execution(result: &ExecutionResult, plan: &ExecutionPlan) -> Result<ExecutionResult, String>`
Handles failed executions by routing to alternative accounts.

```rust
if !result.success {
    let recovery = orchestrator.handle_failed_execution(&result, &plan).await?;
    println!("Recovered on account: {}", recovery.account_id);
}
```

#### `update_correlation_matrix(account1: &str, account2: &str, correlation: f64)`
Updates the correlation between two accounts for anti-correlation logic.

```rust
orchestrator.update_correlation_matrix("account1", "account2", 0.75).await;
```

#### `pause_account(account_id: &str) -> Result<(), String>`
Pauses trading on a specific account.

```rust
orchestrator.pause_account("account_1").await?;
```

#### `resume_account(account_id: &str) -> Result<(), String>`
Resumes trading on a paused account.

```rust
orchestrator.resume_account("account_1").await?;
```

### ExecutionCoordinator

#### `monitor_execution(order_id: String, account_id: String, expected_quantity: f64) -> Result<ExecutionMonitor, String>`
Monitors an order execution for completion and partial fills.

```rust
let monitor = coordinator.monitor_execution(
    "order_123".to_string(),
    "account_1".to_string(),
    100.0,
).await?;
```

#### `handle_partial_fill(monitor: &ExecutionMonitor) -> Result<String, String>`
Handles partial fills by placing completion orders.

```rust
if monitor.status == OrderStatus::PartiallyFilled {
    let completion_order_id = coordinator.handle_partial_fill(&monitor).await?;
}
```

## Data Structures

### TradeSignal
```rust
pub struct TradeSignal {
    pub id: String,
    pub symbol: String,
    pub side: OrderSide,
    pub entry_price: f64,
    pub stop_loss: f64,
    pub take_profit: f64,
    pub confidence: f64,
    pub risk_reward_ratio: f64,
    pub signal_time: SystemTime,
    pub metadata: HashMap<String, String>,
}
```

### ExecutionPlan
```rust
pub struct ExecutionPlan {
    pub signal_id: String,
    pub account_assignments: Vec<AccountAssignment>,
    pub timing_variance: HashMap<String, Duration>,
    pub size_variance: HashMap<String, f64>,
    pub rationale: String,
}
```

### AccountAssignment
```rust
pub struct AccountAssignment {
    pub account_id: String,
    pub position_size: f64,
    pub entry_timing_delay: Duration,
    pub priority: u8,
}
```

### ExecutionResult
```rust
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
```

## Usage Examples

### Basic Signal Execution
```rust
use execution_engine::execution::{TradeExecutionOrchestrator, TradeSignal};
use std::collections::HashMap;
use std::time::SystemTime;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize orchestrator
    let orchestrator = TradeExecutionOrchestrator::new();
    
    // Register accounts
    for i in 1..=3 {
        let platform = create_platform(&format!("account_{}", i));
        orchestrator.register_account(
            format!("account_{}", i),
            platform,
            10000.0,
        ).await?;
    }
    
    // Create trading signal
    let signal = TradeSignal {
        id: "signal_001".to_string(),
        symbol: "EURUSD".to_string(),
        side: OrderSide::Buy,
        entry_price: 1.0900,
        stop_loss: 1.0850,
        take_profit: 1.1000,
        confidence: 0.85,
        risk_reward_ratio: 2.0,
        signal_time: SystemTime::now(),
        metadata: HashMap::from([
            ("strategy".to_string(), "wyckoff_spring".to_string()),
        ]),
    };
    
    // Process signal and create execution plan
    let plan = orchestrator.process_signal(signal).await?;
    println!("Created plan for {} accounts", plan.account_assignments.len());
    
    // Execute the plan
    let results = orchestrator.execute_plan(&plan).await;
    
    // Check results
    for result in results {
        if result.success {
            println!(
                "✓ Account {} executed order {} in {:?}",
                result.account_id,
                result.order_id.unwrap(),
                result.execution_time
            );
        } else {
            println!(
                "✗ Account {} failed: {}",
                result.account_id,
                result.error_message.unwrap()
            );
        }
    }
    
    Ok(())
}
```

### Handling Correlated Accounts
```rust
// Set correlation between accounts
orchestrator.update_correlation_matrix("account_1", "account_2", 0.85).await;
orchestrator.update_correlation_matrix("account_2", "account_3", 0.45).await;

// Process signal - highly correlated accounts will have increased timing variance
let plan = orchestrator.process_signal(signal).await?;

// The system automatically applies anti-correlation adjustments:
// - Additional timing delays for correlated accounts
// - Position size reductions to maintain independence
```

### Failure Recovery
```rust
let results = orchestrator.execute_plan(&plan).await;

for result in &results {
    if !result.success {
        // Attempt recovery on alternative account
        match orchestrator.handle_failed_execution(result, &plan).await {
            Ok(recovery) => {
                println!(
                    "Recovered failed execution on account {}",
                    recovery.account_id
                );
            }
            Err(e) => {
                println!("Recovery failed: {}", e);
            }
        }
    }
}
```

### Monitoring Partial Fills
```rust
use execution_engine::execution::ExecutionCoordinator;

let coordinator = ExecutionCoordinator::new();

// Register platform for monitoring
coordinator.register_platform("account_1".to_string(), platform).await;

// Monitor order execution
let monitor = coordinator.monitor_execution(
    "order_123".to_string(),
    "account_1".to_string(),
    100.0, // Expected quantity
).await?;

// Check for partial fills
if monitor.status == OrderStatus::PartiallyFilled {
    println!(
        "Order partially filled: {:.2}/{:.2}",
        monitor.filled_quantity,
        monitor.expected_quantity
    );
    
    // Handle partial fill by placing completion order
    let completion_order = coordinator.handle_partial_fill(&monitor).await?;
    println!("Placed completion order: {}", completion_order);
}
```

### Account Management
```rust
// Check account status
let status = orchestrator.get_account_status("account_1").await;
if let Some(account) = status {
    println!("Account {} status:", account.account_id);
    println!("  Available margin: ${:.2}", account.available_margin);
    println!("  Risk budget: ${:.2}", account.risk_budget_remaining);
    println!("  Daily drawdown: {:.2}%", account.daily_drawdown * 100.0);
    println!("  Open positions: {}", account.open_positions);
}

// Pause account during high-risk periods
orchestrator.pause_account("account_1").await?;
println!("Account paused");

// Resume when conditions improve
orchestrator.resume_account("account_1").await?;
println!("Account resumed");
```

### Audit Trail
```rust
// Get execution history
let history = orchestrator.get_execution_history(50).await;

for entry in history {
    println!("[{}] {} - {}: {}",
        entry.timestamp.duration_since(SystemTime::UNIX_EPOCH)?.as_secs(),
        entry.signal_id,
        entry.action,
        entry.decision_rationale
    );
    
    if let Some(result) = entry.result {
        println!("  Result: {} on account {}",
            if result.success { "SUCCESS" } else { "FAILED" },
            result.account_id
        );
    }
}
```

## Configuration

### Default Parameters
- `max_correlation_threshold`: 0.7
- `min_timing_variance_ms`: 1000 (1 second)
- `max_timing_variance_ms`: 30000 (30 seconds)
- `min_size_variance_pct`: 0.05 (5%)
- `max_size_variance_pct`: 0.15 (15%)

### Risk Management
- Position sizing based on account balance and risk budget
- Automatic reduction during drawdown periods
- Correlation-based size adjustments
- Prop firm maximum position limits enforcement

## Best Practices

1. **Account Registration**: Register all accounts before processing signals
2. **Correlation Updates**: Update correlation matrix regularly based on historical data
3. **Monitor Executions**: Always monitor critical executions for partial fills
4. **Audit Logging**: Review audit logs regularly for compliance and optimization
5. **Error Handling**: Implement proper error handling for failed executions
6. **Testing**: Test with paper trading accounts before live deployment

## Performance Considerations

- Execution latency: < 100ms per order
- Concurrent execution support for multiple accounts
- Efficient correlation matrix lookups
- Minimal memory footprint for audit trail (auto-pruning at 10,000 entries)

## Compliance Features

- Complete audit trail with timestamps and rationale
- Account-level risk limits enforcement
- Anti-correlation to avoid detection
- Timing variance for human-like behavior
- Position size variance between accounts