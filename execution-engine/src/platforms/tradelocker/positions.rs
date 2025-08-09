use std::sync::Arc;
use std::collections::HashMap;
use tokio::sync::RwLock;
use rust_decimal::Decimal;
use tracing::{debug, error, info, warn};

use super::{
    TradeLockerClient, Position, PositionSide,
    TradeLockerError, Result
};

#[derive(Debug, Clone)]
pub struct PositionManager {
    client: Arc<TradeLockerClient>,
    positions: Arc<RwLock<HashMap<String, Position>>>,
    position_metrics: Arc<RwLock<PositionMetrics>>,
}

#[derive(Debug, Clone, Default)]
pub struct PositionMetrics {
    pub total_positions: usize,
    pub long_positions: usize,
    pub short_positions: usize,
    pub total_unrealized_pnl: Decimal,
    pub total_realized_pnl: Decimal,
    pub total_margin_used: Decimal,
    pub largest_position_size: Decimal,
    pub average_position_size: Decimal,
}

impl PositionManager {
    pub fn new(client: Arc<TradeLockerClient>) -> Self {
        Self {
            client,
            positions: Arc::new(RwLock::new(HashMap::new())),
            position_metrics: Arc::new(RwLock::new(PositionMetrics::default())),
        }
    }

    pub async fn refresh_positions(&self, account_id: &str) -> Result<Vec<Position>> {
        let positions = self.client.get_positions(account_id).await?;
        
        let mut position_map = HashMap::new();
        for position in &positions {
            position_map.insert(position.position_id.clone(), position.clone());
        }

        *self.positions.write().await = position_map;
        self.update_metrics(&positions).await;

        Ok(positions)
    }

    pub async fn get_position(&self, position_id: &str) -> Option<Position> {
        self.positions.read().await.get(position_id).cloned()
    }

    pub async fn get_all_positions(&self) -> Vec<Position> {
        self.positions.read().await.values().cloned().collect()
    }

    pub async fn get_positions_by_symbol(&self, symbol: &str) -> Vec<Position> {
        self.positions
            .read()
            .await
            .values()
            .filter(|p| p.symbol == symbol)
            .cloned()
            .collect()
    }

    pub async fn close_position(
        &self,
        account_id: &str,
        position_id: &str,
        partial_quantity: Option<f64>,
    ) -> Result<()> {
        info!("Closing position {}: quantity={:?}", position_id, partial_quantity);
        
        self.client.close_position(account_id, position_id, partial_quantity).await?;
        
        // Remove or update position locally
        let mut positions = self.positions.write().await;
        if partial_quantity.is_none() {
            positions.remove(position_id);
        } else if let Some(pos) = positions.get_mut(position_id) {
            // Update quantity for partial close
            if let Some(qty) = partial_quantity {
                let closed_qty = Decimal::from_f64_retain(qty).unwrap_or_default();
                pos.quantity = (pos.quantity - closed_qty).max(Decimal::ZERO);
            }
        }

        Ok(())
    }

    pub async fn close_all_positions(&self, account_id: &str) -> Result<Vec<String>> {
        let positions = self.get_all_positions().await;
        let mut closed = Vec::new();

        for position in positions {
            match self.close_position(account_id, &position.position_id, None).await {
                Ok(_) => {
                    closed.push(position.position_id);
                }
                Err(e) => {
                    error!("Failed to close position {}: {}", position.position_id, e);
                }
            }
        }

        Ok(closed)
    }

    pub async fn modify_position(
        &self,
        account_id: &str,
        position_id: &str,
        stop_loss: Option<f64>,
        take_profit: Option<f64>,
    ) -> Result<Position> {
        info!("Modifying position {}: SL={:?}, TP={:?}", position_id, stop_loss, take_profit);
        
        let updated = self.client.modify_position(account_id, position_id, stop_loss, take_profit).await?;
        
        // Update local cache
        let mut positions = self.positions.write().await;
        positions.insert(position_id.to_string(), updated.clone());

        Ok(updated)
    }

    pub async fn update_position(&self, position: Position) {
        let mut positions = self.positions.write().await;
        positions.insert(position.position_id.clone(), position);
        
        // Recalculate metrics
        let all_positions: Vec<Position> = positions.values().cloned().collect();
        drop(positions);
        self.update_metrics(&all_positions).await;
    }

    async fn update_metrics(&self, positions: &[Position]) {
        let mut metrics = PositionMetrics::default();
        
        metrics.total_positions = positions.len();
        
        let mut total_size = Decimal::ZERO;
        let mut max_size = Decimal::ZERO;
        
        for position in positions {
            match position.side {
                PositionSide::Long => metrics.long_positions += 1,
                PositionSide::Short => metrics.short_positions += 1,
            }
            
            metrics.total_unrealized_pnl += position.unrealized_pnl;
            metrics.total_realized_pnl += position.realized_pnl;
            metrics.total_margin_used += position.margin_used;
            
            let position_value = position.quantity * position.entry_price;
            total_size += position_value;
            max_size = max_size.max(position_value);
        }
        
        metrics.largest_position_size = max_size;
        
        if !positions.is_empty() {
            metrics.average_position_size = total_size / Decimal::from(positions.len());
        }
        
        *self.position_metrics.write().await = metrics;
    }

    pub async fn get_metrics(&self) -> PositionMetrics {
        self.position_metrics.read().await.clone()
    }

    pub async fn get_total_exposure(&self) -> Decimal {
        self.positions
            .read()
            .await
            .values()
            .map(|p| p.quantity * p.current_price)
            .sum()
    }

    pub async fn get_net_position(&self, symbol: &str) -> Decimal {
        let positions = self.get_positions_by_symbol(symbol).await;
        
        positions.iter().fold(Decimal::ZERO, |acc, pos| {
            match pos.side {
                PositionSide::Long => acc + pos.quantity,
                PositionSide::Short => acc - pos.quantity,
            }
        })
    }

    pub async fn has_position(&self, symbol: &str) -> bool {
        !self.get_positions_by_symbol(symbol).await.is_empty()
    }

    pub async fn get_position_count(&self) -> usize {
        self.positions.read().await.len()
    }

    pub async fn clear_positions(&self) {
        self.positions.write().await.clear();
        *self.position_metrics.write().await = PositionMetrics::default();
    }
}