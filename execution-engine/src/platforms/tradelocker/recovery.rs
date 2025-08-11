use std::sync::Arc;
use std::time::Duration;
use tokio::sync::RwLock;
use tracing::{debug, error, info, warn};
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};

use super::{
    TradeLockerError, Result, MultiAccountManager,
    OrderResponse, Position,
};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecoveryState {
    pub account_id: String,
    pub last_known_state: DateTime<Utc>,
    pub pending_orders: Vec<OrderResponse>,
    pub open_positions: Vec<Position>,
    pub last_balance: rust_decimal::Decimal,
    pub recovery_attempts: u32,
    pub last_recovery_attempt: Option<DateTime<Utc>>,
}

pub struct ErrorRecoveryManager {
    multi_account_manager: Arc<MultiAccountManager>,
    recovery_states: Arc<RwLock<Vec<RecoveryState>>>,
    max_recovery_attempts: u32,
    recovery_backoff_ms: u64,
}

impl ErrorRecoveryManager {
    pub fn new(multi_account_manager: Arc<MultiAccountManager>) -> Self {
        Self {
            multi_account_manager,
            recovery_states: Arc::new(RwLock::new(Vec::new())),
            max_recovery_attempts: 5,
            recovery_backoff_ms: 1000,
        }
    }

    pub async fn handle_error(&self, account_id: &str, error: &TradeLockerError) -> Result<()> {
        match error {
            TradeLockerError::Auth(_) => {
                self.handle_auth_error(account_id).await
            }
            TradeLockerError::Connection(_) | TradeLockerError::WebSocket(_) => {
                self.handle_connection_error(account_id).await
            }
            TradeLockerError::RateLimit { retry_after } => {
                self.handle_rate_limit(account_id, *retry_after).await
            }
            TradeLockerError::OrderRejected(reason) => {
                self.handle_order_rejection(account_id, reason).await
            }
            TradeLockerError::InsufficientMargin { .. } => {
                self.handle_margin_error(account_id).await
            }
            TradeLockerError::Timeout(_) => {
                self.handle_timeout(account_id).await
            }
            _ => {
                warn!("Unhandled error type for {}: {:?}", account_id, error);
                Ok(())
            }
        }
    }

    async fn handle_auth_error(&self, account_id: &str) -> Result<()> {
        info!("Handling authentication error for account: {}", account_id);
        
        // Close existing session
        self.multi_account_manager.close_session(account_id).await?;
        
        // Wait before retry
        tokio::time::sleep(Duration::from_millis(self.recovery_backoff_ms)).await;
        
        // Try to create new session with fresh authentication
        match self.multi_account_manager.create_session(account_id).await {
            Ok(_) => {
                info!("Successfully re-authenticated account: {}", account_id);
                self.recover_state(account_id).await?;
                Ok(())
            }
            Err(e) => {
                error!("Failed to re-authenticate account {}: {}", account_id, e);
                Err(e)
            }
        }
    }

    async fn handle_connection_error(&self, account_id: &str) -> Result<()> {
        info!("Handling connection error for account: {}", account_id);
        
        // Save current state
        self.save_state(account_id).await?;
        
        let mut attempts = 0;
        let mut backoff = self.recovery_backoff_ms;
        
        while attempts < self.max_recovery_attempts {
            attempts += 1;
            info!("Connection recovery attempt {} for account: {}", attempts, account_id);
            
            tokio::time::sleep(Duration::from_millis(backoff)).await;
            
            // Try to reconnect
            match self.multi_account_manager.get_session(account_id).await {
                Ok(session) => {
                    // Check if WebSocket needs reconnection
                    if !session.websocket.is_connected().await {
                        if let Err(e) = session.websocket.reconnect(account_id).await {
                            warn!("WebSocket reconnection failed: {}", e);
                            backoff = (backoff * 2).min(30000); // Max 30 seconds
                            continue;
                        }
                    }
                    
                    info!("Connection recovered for account: {}", account_id);
                    self.recover_state(account_id).await?;
                    return Ok(());
                }
                Err(_) => {
                    // Try to create new session
                    if let Ok(_) = self.multi_account_manager.create_session(account_id).await {
                        info!("New session created for account: {}", account_id);
                        self.recover_state(account_id).await?;
                        return Ok(());
                    }
                }
            }
            
            backoff = (backoff * 2).min(30000); // Exponential backoff with max
        }
        
        error!("Failed to recover connection after {} attempts", attempts);
        Err(TradeLockerError::Connection(format!(
            "Failed to recover after {} attempts", attempts
        )))
    }

    async fn handle_rate_limit(&self, account_id: &str, retry_after: u64) -> Result<()> {
        warn!("Rate limit hit for account: {}. Waiting {} seconds", account_id, retry_after);
        
        // Wait for the specified time
        tokio::time::sleep(Duration::from_secs(retry_after)).await;
        
        info!("Resuming operations for account: {}", account_id);
        Ok(())
    }

    async fn handle_order_rejection(&self, account_id: &str, reason: &str) -> Result<()> {
        error!("Order rejected for account {}: {}", account_id, reason);
        
        // Check if it's a recoverable rejection
        if reason.contains("insufficient funds") || reason.contains("margin") {
            self.handle_margin_error(account_id).await?;
        } else if reason.contains("market closed") {
            info!("Market closed - will retry when market opens");
            // Could implement market hours checking here
        } else if reason.contains("invalid price") {
            info!("Invalid price - need to refresh market data");
            // Refresh market data and retry with updated prices
        }
        
        Ok(())
    }

    async fn handle_margin_error(&self, account_id: &str) -> Result<()> {
        warn!("Margin error for account: {}", account_id);
        
        if let Ok(session) = self.multi_account_manager.get_session(account_id).await {
            // Check current margin situation
            let is_margin_call = session.account_manager.is_margin_call(account_id).await?;
            let is_stop_out = session.account_manager.is_stop_out(account_id).await?;
            
            if is_stop_out {
                error!("🚨 STOP OUT LEVEL for account: {}", account_id);
                // Emergency: Close all positions
                self.emergency_close_all(account_id).await?;
            } else if is_margin_call {
                warn!("⚠️ MARGIN CALL for account: {}", account_id);
                // Close losing positions to free up margin
                self.close_losing_positions(account_id).await?;
            } else {
                // Just insufficient margin for new order
                info!("Insufficient margin for new order on account: {}", account_id);
            }
        }
        
        Ok(())
    }

    async fn handle_timeout(&self, account_id: &str) -> Result<()> {
        warn!("Request timeout for account: {}", account_id);
        
        // Check if the operation actually completed
        // This would involve checking order status, position status, etc.
        
        Ok(())
    }

    async fn save_state(&self, account_id: &str) -> Result<()> {
        if let Ok(session) = self.multi_account_manager.get_session(account_id).await {
            let orders = session.order_manager.get_active_orders().await;
            let positions = session.position_manager.get_all_positions().await;
            let account_info = session.account_manager.get_account_info(account_id, false).await?;
            
            let state = RecoveryState {
                account_id: account_id.to_string(),
                last_known_state: Utc::now(),
                pending_orders: orders,
                open_positions: positions,
                last_balance: account_info.balance,
                recovery_attempts: 0,
                last_recovery_attempt: None,
            };
            
            let mut states = self.recovery_states.write().await;
            states.retain(|s| s.account_id != account_id);
            states.push(state);
            
            debug!("State saved for account: {}", account_id);
        }
        
        Ok(())
    }

    async fn recover_state(&self, account_id: &str) -> Result<()> {
        let states = self.recovery_states.read().await;
        
        if let Some(state) = states.iter().find(|s| s.account_id == account_id) {
            info!("Recovering state for account: {} from {}", account_id, state.last_known_state);
            
            if let Ok(session) = self.multi_account_manager.get_session(account_id).await {
                // Refresh current state
                session.position_manager.refresh_positions(account_id).await?;
                session.account_manager.refresh_account_info(account_id).await?;
                
                // Compare and reconcile
                let current_positions = session.position_manager.get_all_positions().await;
                let current_orders = session.order_manager.get_active_orders().await;
                
                // Log discrepancies
                for saved_pos in &state.open_positions {
                    if !current_positions.iter().any(|p| p.position_id == saved_pos.position_id) {
                        warn!("Position {} was closed during disconnection", saved_pos.position_id);
                    }
                }
                
                for saved_order in &state.pending_orders {
                    if !current_orders.iter().any(|o| o.order_id == saved_order.order_id) {
                        warn!("Order {} status changed during disconnection", saved_order.order_id);
                    }
                }
            }
        }
        
        Ok(())
    }

    async fn emergency_close_all(&self, account_id: &str) -> Result<()> {
        error!("🚨 EMERGENCY: Closing all positions for account: {}", account_id);
        
        if let Ok(session) = self.multi_account_manager.get_session(account_id).await {
            // Cancel all pending orders
            let canceled = session.order_manager.cancel_all_orders(account_id).await?;
            info!("Canceled {} pending orders", canceled.len());
            
            // Close all positions
            let closed = session.position_manager.close_all_positions(account_id).await?;
            info!("Closed {} positions", closed.len());
        }
        
        Ok(())
    }

    async fn close_losing_positions(&self, account_id: &str) -> Result<()> {
        info!("Closing losing positions to free margin for account: {}", account_id);
        
        if let Ok(session) = self.multi_account_manager.get_session(account_id).await {
            let positions = session.position_manager.get_all_positions().await;
            
            // Sort by loss (most negative first)
            let mut losing_positions: Vec<_> = positions
                .into_iter()
                .filter(|p| p.unrealized_pnl < rust_decimal::Decimal::ZERO)
                .collect();
            
            losing_positions.sort_by(|a, b| a.unrealized_pnl.cmp(&b.unrealized_pnl));
            
            // Close worst positions first
            for position in losing_positions.iter().take(3) {
                info!("Closing losing position: {} with P&L: {}", 
                    position.position_id, position.unrealized_pnl);
                
                if let Err(e) = session.position_manager
                    .close_position(account_id, &position.position_id, None).await {
                    error!("Failed to close position {}: {}", position.position_id, e);
                }
            }
        }
        
        Ok(())
    }

    pub async fn monitor_recovery_states(&self) {
        let mut interval = tokio::time::interval(Duration::from_secs(60));
        
        loop {
            interval.tick().await;
            
            let states = self.recovery_states.read().await.clone();
            
            for state in states {
                if let Some(last_attempt) = state.last_recovery_attempt {
                    let time_since = Utc::now() - last_attempt;
                    
                    if time_since > chrono::Duration::minutes(5) {
                        info!("Retrying recovery for account: {}", state.account_id);
                        
                        if let Err(e) = self.recover_state(&state.account_id).await {
                            error!("Recovery failed for {}: {}", state.account_id, e);
                        }
                    }
                }
            }
        }
    }
}