use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, SystemTime};
use tokio::sync::RwLock;
use tokio::time::{interval, timeout};
use serde::{Deserialize, Serialize};
use tracing::{info, warn, error};
use uuid::Uuid;
use rust_decimal::prelude::ToPrimitive;

use crate::platforms::abstraction::{
    interfaces::{ITradingPlatform, OrderFilter},
    models::{UnifiedOrder, UnifiedOrderStatus, UnifiedOrderType, UnifiedOrderSide, UnifiedTimeInForce, OrderMetadata, UnifiedOrderResponse},
};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PartialFill {
    pub order_id: String,
    pub filled_quantity: f64,
    pub remaining_quantity: f64,
    pub filled_price: f64,
    pub timestamp: SystemTime,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionMonitor {
    pub order_id: String,
    pub account_id: String,
    pub expected_quantity: f64,
    pub filled_quantity: f64,
    pub status: UnifiedOrderStatus,
    pub partial_fills: Vec<PartialFill>,
    pub start_time: SystemTime,
    pub completion_time: Option<SystemTime>,
    pub retry_count: u32,
    pub max_retries: u32,
}

impl ExecutionMonitor {
    pub fn new(order_id: String, account_id: String, expected_quantity: f64) -> Self {
        Self {
            order_id,
            account_id,
            expected_quantity,
            filled_quantity: 0.0,
            status: UnifiedOrderStatus::Pending,
            partial_fills: Vec::new(),
            start_time: SystemTime::now(),
            completion_time: None,
            retry_count: 0,
            max_retries: 3,
        }
    }

    pub fn add_partial_fill(&mut self, fill: PartialFill) {
        self.filled_quantity += fill.filled_quantity;
        self.partial_fills.push(fill);
        
        if self.filled_quantity >= self.expected_quantity {
            self.status = UnifiedOrderStatus::Filled;
            self.completion_time = Some(SystemTime::now());
        } else {
            self.status = UnifiedOrderStatus::PartiallyFilled;
        }
    }

    pub fn is_complete(&self) -> bool {
        matches!(self.status, UnifiedOrderStatus::Filled | UnifiedOrderStatus::Canceled | UnifiedOrderStatus::Rejected)
    }

    pub fn remaining_quantity(&self) -> f64 {
        (self.expected_quantity - self.filled_quantity).max(0.0)
    }
}

pub struct ExecutionCoordinator {
    monitors: Arc<RwLock<HashMap<String, ExecutionMonitor>>>,
    platforms: Arc<RwLock<HashMap<String, Arc<dyn ITradingPlatform + Send + Sync>>>>,
    monitoring_interval: Duration,
    partial_fill_timeout: Duration,
}

impl ExecutionCoordinator {
    pub fn new() -> Self {
        Self {
            monitors: Arc::new(RwLock::new(HashMap::new())),
            platforms: Arc::new(RwLock::new(HashMap::new())),
            monitoring_interval: Duration::from_secs(1),
            partial_fill_timeout: Duration::from_secs(30),
        }
    }

    pub async fn register_platform(
        &self,
        account_id: String,
        platform: Arc<dyn ITradingPlatform + Send + Sync>,
    ) {
        let mut platforms = self.platforms.write().await;
        platforms.insert(account_id, platform);
    }

    pub async fn monitor_execution(
        &self,
        order_id: String,
        account_id: String,
        expected_quantity: f64,
    ) -> Result<ExecutionMonitor, String> {
        let monitor = ExecutionMonitor::new(order_id.clone(), account_id.clone(), expected_quantity);
        
        {
            let mut monitors = self.monitors.write().await;
            monitors.insert(order_id.clone(), monitor.clone());
        }

        let monitoring_task = self.start_monitoring_task(order_id.clone());
        
        tokio::select! {
            result = monitoring_task => result,
            _ = tokio::time::sleep(Duration::from_secs(60)) => {
                Err("Execution monitoring timeout".to_string())
            }
        }
    }

    async fn start_monitoring_task(&self, order_id: String) -> Result<ExecutionMonitor, String> {
        let monitors = self.monitors.clone();
        let platforms = self.platforms.clone();
        let monitoring_interval = self.monitoring_interval;
        
        let mut ticker = interval(monitoring_interval);
        
        loop {
            ticker.tick().await;
            
            let mut monitors_lock = monitors.write().await;
            let monitor = monitors_lock.get_mut(&order_id)
                .ok_or_else(|| "Monitor not found".to_string())?;
            
            if monitor.is_complete() {
                return Ok(monitor.clone());
            }
            
            let platforms_lock = platforms.read().await;
            let platform = platforms_lock.get(&monitor.account_id)
                .ok_or_else(|| "Platform not found".to_string())?;
            
            let order_filter = OrderFilter {
                order_id: Some(order_id.clone()),
                symbol: None,
                status: None,
                side: None,
                order_type: None,
                from: None,
                to: None,
                limit: Some(1),
            };
            
            match platform.get_orders(Some(order_filter)).await {
                Ok(orders) if !orders.is_empty() => {
                    let order = &orders[0];
                    monitor.status = order.status.clone();
                    
                    if let Some(filled_qty) = Self::calculate_filled_quantity(order) {
                        if filled_qty > monitor.filled_quantity {
                            let partial_fill = PartialFill {
                                order_id: order_id.clone(),
                                filled_quantity: filled_qty - monitor.filled_quantity,
                                remaining_quantity: monitor.expected_quantity - filled_qty,
                                filled_price: order.average_fill_price.map(|p| p.to_f64().unwrap_or(0.0)).unwrap_or(0.0),
                                timestamp: SystemTime::now(),
                            };
                            monitor.add_partial_fill(partial_fill);
                            
                            info!(
                                "Partial fill for order {}: {:.2}/{:.2}",
                                order_id, monitor.filled_quantity, monitor.expected_quantity
                            );
                        }
                    }
                    
                    if monitor.is_complete() {
                        info!("Order {} completed with status {:?}", order_id, monitor.status);
                        return Ok(monitor.clone());
                    }
                }
                Ok(_) => {
                    warn!("Order {} not found", order_id);
                    monitor.retry_count += 1;
                }
                Err(e) => {
                    warn!("Failed to get order status for {}: {}", order_id, e);
                    monitor.retry_count += 1;
                    
                    if monitor.retry_count >= monitor.max_retries {
                        error!("Max retries exceeded for order {}", order_id);
                        monitor.status = UnifiedOrderStatus::Rejected;
                        return Err("Max retries exceeded".to_string());
                    }
                }
            }
        }
    }

    fn calculate_filled_quantity(order: &UnifiedOrderResponse) -> Option<f64> {
        match order.status {
            UnifiedOrderStatus::Filled => Some(order.quantity.to_f64().unwrap_or(0.0)),
            UnifiedOrderStatus::PartiallyFilled => {
                Some(order.filled_quantity.to_f64().unwrap_or(0.0))
            }
            _ => Some(0.0),
        }
    }

    pub async fn handle_partial_fill(
        &self,
        monitor: &ExecutionMonitor,
    ) -> Result<String, String> {
        if monitor.remaining_quantity() <= 0.0 {
            return Ok("No remaining quantity to fill".to_string());
        }

        info!(
            "Handling partial fill for order {}. Remaining: {:.2}",
            monitor.order_id,
            monitor.remaining_quantity()
        );

        let platforms = self.platforms.read().await;
        let platform = platforms.get(&monitor.account_id)
            .ok_or_else(|| "Platform not found".to_string())?;

        let completion_order = UnifiedOrder {
            client_order_id: Uuid::new_v4().to_string(),
            symbol: "EURUSD".to_string(),
            order_type: UnifiedOrderType::Market,
            side: UnifiedOrderSide::Buy,
            quantity: rust_decimal::Decimal::from_f64_retain(monitor.remaining_quantity()).unwrap(),
            price: None,
            stop_price: None,
            stop_loss: None,
            take_profit: None,
            time_in_force: UnifiedTimeInForce::Gtc,
            account_id: Some(monitor.account_id.clone()),
            metadata: OrderMetadata {
                strategy_id: None,
                signal_id: None,
                risk_parameters: HashMap::new(),
                tags: vec!["partial_fill_completion".to_string()],
                expires_at: None,
            },
        };

        match timeout(self.partial_fill_timeout, platform.place_order(completion_order)).await {
            Ok(Ok(placed_order)) => {
                info!("Completion order placed: {}", placed_order.platform_order_id);
                self.monitor_execution(
                    placed_order.platform_order_id.clone(),
                    monitor.account_id.clone(),
                    monitor.remaining_quantity(),
                ).await?;
                Ok(placed_order.platform_order_id)
            }
            Ok(Err(e)) => {
                error!("Failed to place completion order: {}", e);
                Err(format!("Failed to place completion order: {}", e))
            }
            Err(_) => {
                error!("Timeout placing completion order");
                Err("Timeout placing completion order".to_string())
            }
        }
    }

    pub async fn cancel_incomplete_orders(&self) -> Vec<Result<String, String>> {
        let monitors = self.monitors.read().await;
        let platforms = self.platforms.read().await;
        let mut results = Vec::new();

        for (order_id, monitor) in monitors.iter() {
            if !monitor.is_complete() && monitor.status == UnifiedOrderStatus::PartiallyFilled {
                if let Some(platform) = platforms.get(&monitor.account_id) {
                    match platform.cancel_order(order_id).await {
                        Ok(_) => {
                            info!("Cancelled incomplete order {}", order_id);
                            results.push(Ok(order_id.clone()));
                        }
                        Err(e) => {
                            error!("Failed to cancel order {}: {}", order_id, e);
                            results.push(Err(format!("Failed to cancel {}: {}", order_id, e)));
                        }
                    }
                }
            }
        }

        results
    }

    pub async fn get_execution_summary(&self) -> HashMap<String, ExecutionSummary> {
        let monitors = self.monitors.read().await;
        let mut summary = HashMap::new();

        for (order_id, monitor) in monitors.iter() {
            let exec_summary = ExecutionSummary {
                order_id: order_id.clone(),
                account_id: monitor.account_id.clone(),
                status: monitor.status.clone(),
                fill_rate: monitor.filled_quantity / monitor.expected_quantity,
                partial_fills_count: monitor.partial_fills.len(),
                duration: monitor.completion_time
                    .and_then(|ct| ct.duration_since(monitor.start_time).ok())
                    .map(|d| d.as_secs()),
                retry_count: monitor.retry_count,
            };
            summary.insert(order_id.clone(), exec_summary);
        }

        summary
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionSummary {
    pub order_id: String,
    pub account_id: String,
    pub status: UnifiedOrderStatus,
    pub fill_rate: f64,
    pub partial_fills_count: usize,
    pub duration: Option<u64>,
    pub retry_count: u32,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_execution_monitor() {
        let mut monitor = ExecutionMonitor::new(
            "order123".to_string(),
            "account1".to_string(),
            100.0,
        );

        assert_eq!(monitor.remaining_quantity(), 100.0);
        assert!(!monitor.is_complete());

        let fill = PartialFill {
            order_id: "order123".to_string(),
            filled_quantity: 50.0,
            remaining_quantity: 50.0,
            filled_price: 1.0900,
            timestamp: SystemTime::now(),
        };

        monitor.add_partial_fill(fill);
        assert_eq!(monitor.filled_quantity, 50.0);
        assert_eq!(monitor.remaining_quantity(), 50.0);
        assert_eq!(monitor.status, UnifiedOrderStatus::PartiallyFilled);

        let fill2 = PartialFill {
            order_id: "order123".to_string(),
            filled_quantity: 50.0,
            remaining_quantity: 0.0,
            filled_price: 1.0901,
            timestamp: SystemTime::now(),
        };

        monitor.add_partial_fill(fill2);
        assert_eq!(monitor.filled_quantity, 100.0);
        assert_eq!(monitor.remaining_quantity(), 0.0);
        assert_eq!(monitor.status, UnifiedOrderStatus::Filled);
        assert!(monitor.is_complete());
    }

    #[tokio::test]
    async fn test_coordinator_creation() {
        let coordinator = ExecutionCoordinator::new();
        assert_eq!(coordinator.monitoring_interval, Duration::from_secs(1));
        assert_eq!(coordinator.partial_fill_timeout, Duration::from_secs(30));
    }
}