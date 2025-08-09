use std::sync::Arc;
use std::collections::HashMap;
use tokio::sync::RwLock;
use rust_decimal::Decimal;
use chrono::{DateTime, Utc};
use tracing::{debug, error, info, warn};

use super::{
    TradeLockerClient, OrderRequest, OrderResponse, OrderStatus,
    TradeLockerError, Result
};

#[derive(Debug, Clone)]
pub struct OrderManager {
    client: Arc<TradeLockerClient>,
    active_orders: Arc<RwLock<HashMap<String, OrderResponse>>>,
    order_history: Arc<RwLock<Vec<OrderResponse>>>,
}

impl OrderManager {
    pub fn new(client: Arc<TradeLockerClient>) -> Self {
        Self {
            client,
            active_orders: Arc::new(RwLock::new(HashMap::new())),
            order_history: Arc::new(RwLock::new(Vec::new())),
        }
    }

    pub async fn place_market_order(
        &self,
        account_id: &str,
        symbol: &str,
        side: super::OrderSide,
        quantity: Decimal,
        stop_loss: Option<Decimal>,
        take_profit: Option<Decimal>,
    ) -> Result<OrderResponse> {
        let order = OrderRequest {
            symbol: symbol.to_string(),
            side,
            order_type: super::OrderType::Market,
            quantity,
            price: None,
            stop_price: None,
            stop_loss,
            take_profit,
            time_in_force: super::TimeInForce::Ioc,
            client_order_id: Some(Self::generate_client_order_id()),
        };

        self.execute_order(account_id, order).await
    }

    pub async fn place_limit_order(
        &self,
        account_id: &str,
        symbol: &str,
        side: super::OrderSide,
        quantity: Decimal,
        price: Decimal,
        stop_loss: Option<Decimal>,
        take_profit: Option<Decimal>,
        time_in_force: super::TimeInForce,
    ) -> Result<OrderResponse> {
        let order = OrderRequest {
            symbol: symbol.to_string(),
            side,
            order_type: super::OrderType::Limit,
            quantity,
            price: Some(price),
            stop_price: None,
            stop_loss,
            take_profit,
            time_in_force,
            client_order_id: Some(Self::generate_client_order_id()),
        };

        self.execute_order(account_id, order).await
    }

    pub async fn place_stop_order(
        &self,
        account_id: &str,
        symbol: &str,
        side: super::OrderSide,
        quantity: Decimal,
        stop_price: Decimal,
        stop_loss: Option<Decimal>,
        take_profit: Option<Decimal>,
    ) -> Result<OrderResponse> {
        let order = OrderRequest {
            symbol: symbol.to_string(),
            side,
            order_type: super::OrderType::Stop,
            quantity,
            price: None,
            stop_price: Some(stop_price),
            stop_loss,
            take_profit,
            time_in_force: super::TimeInForce::Gtc,
            client_order_id: Some(Self::generate_client_order_id()),
        };

        self.execute_order(account_id, order).await
    }

    pub async fn place_stop_limit_order(
        &self,
        account_id: &str,
        symbol: &str,
        side: super::OrderSide,
        quantity: Decimal,
        stop_price: Decimal,
        limit_price: Decimal,
        stop_loss: Option<Decimal>,
        take_profit: Option<Decimal>,
    ) -> Result<OrderResponse> {
        let order = OrderRequest {
            symbol: symbol.to_string(),
            side,
            order_type: super::OrderType::StopLimit,
            quantity,
            price: Some(limit_price),
            stop_price: Some(stop_price),
            stop_loss,
            take_profit,
            time_in_force: super::TimeInForce::Gtc,
            client_order_id: Some(Self::generate_client_order_id()),
        };

        self.execute_order(account_id, order).await
    }

    async fn execute_order(&self, account_id: &str, order: OrderRequest) -> Result<OrderResponse> {
        info!("Placing {} order for {}: {:?}", order.order_type, order.symbol, order.side);
        
        let response = self.client.place_order(account_id, order).await?;
        
        // Store in active orders if not immediately filled
        if !matches!(response.status, OrderStatus::Filled | OrderStatus::Rejected | OrderStatus::Canceled) {
            let mut active = self.active_orders.write().await;
            active.insert(response.order_id.clone(), response.clone());
        } else {
            // Store in history if completed
            let mut history = self.order_history.write().await;
            history.push(response.clone());
        }

        Ok(response)
    }

    pub async fn modify_order(
        &self,
        account_id: &str,
        order_id: &str,
        new_price: Option<Decimal>,
        new_quantity: Option<Decimal>,
        new_stop_loss: Option<Decimal>,
        new_take_profit: Option<Decimal>,
    ) -> Result<OrderResponse> {
        let modifications = serde_json::json!({
            "price": new_price,
            "quantity": new_quantity,
            "stop_loss": new_stop_loss,
            "take_profit": new_take_profit,
        });

        let response = self.client.modify_order(account_id, order_id, modifications).await?;
        
        // Update in active orders
        let mut active = self.active_orders.write().await;
        if let Some(order) = active.get_mut(order_id) {
            *order = response.clone();
        }

        Ok(response)
    }

    pub async fn cancel_order(&self, account_id: &str, order_id: &str) -> Result<()> {
        self.client.cancel_order(account_id, order_id).await?;
        
        // Move from active to history
        let mut active = self.active_orders.write().await;
        if let Some(mut order) = active.remove(order_id) {
            order.status = OrderStatus::Canceled;
            let mut history = self.order_history.write().await;
            history.push(order);
        }

        Ok(())
    }

    pub async fn cancel_all_orders(&self, account_id: &str) -> Result<Vec<String>> {
        let active = self.active_orders.read().await;
        let order_ids: Vec<String> = active.keys().cloned().collect();
        drop(active);

        let mut canceled = Vec::new();
        for order_id in order_ids {
            match self.cancel_order(account_id, &order_id).await {
                Ok(_) => {
                    canceled.push(order_id);
                }
                Err(e) => {
                    warn!("Failed to cancel order {}: {}", order_id, e);
                }
            }
        }

        Ok(canceled)
    }

    pub async fn update_order_status(&self, order_update: OrderResponse) {
        let order_id = &order_update.order_id;
        
        if matches!(order_update.status, OrderStatus::Filled | OrderStatus::Rejected | OrderStatus::Canceled | OrderStatus::Expired) {
            // Move from active to history
            let mut active = self.active_orders.write().await;
            active.remove(order_id);
            
            let mut history = self.order_history.write().await;
            history.push(order_update);
        } else {
            // Update in active orders
            let mut active = self.active_orders.write().await;
            active.insert(order_id.clone(), order_update);
        }
    }

    pub async fn get_active_orders(&self) -> Vec<OrderResponse> {
        self.active_orders.read().await.values().cloned().collect()
    }

    pub async fn get_order_history(&self, limit: Option<usize>) -> Vec<OrderResponse> {
        let history = self.order_history.read().await;
        match limit {
            Some(n) => history.iter().rev().take(n).cloned().collect(),
            None => history.clone(),
        }
    }

    pub async fn get_order(&self, order_id: &str) -> Option<OrderResponse> {
        // Check active orders first
        let active = self.active_orders.read().await;
        if let Some(order) = active.get(order_id) {
            return Some(order.clone());
        }
        drop(active);

        // Check history
        let history = self.order_history.read().await;
        history.iter().find(|o| o.order_id == order_id).cloned()
    }

    fn generate_client_order_id() -> String {
        use uuid::Uuid;
        format!("TL_{}", Uuid::new_v4().to_string())
    }

    pub async fn clear_history(&self) {
        let mut history = self.order_history.write().await;
        let old_count = history.len();
        history.clear();
        info!("Cleared {} orders from history", old_count);
    }
}