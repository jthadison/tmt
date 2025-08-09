use std::sync::Arc;
use std::collections::HashMap;
use tokio::sync::RwLock;
use tracing::{debug, error, info, warn};
use serde::{Deserialize, Serialize};

use super::{
    TradeLockerAuth, TradeLockerClient, TradeLockerWebSocket,
    TradeLockerConfig, TradeLockerEnvironment, TradeLockerError, Result,
    OrderManager, PositionManager, AccountManager,
};
use super::rate_limiter::AccountRateLimiter;
use crate::utils::vault::VaultClient;

#[derive(Debug, Clone)]
pub struct AccountSession {
    pub account_id: String,
    pub client: Arc<TradeLockerClient>,
    pub websocket: Arc<TradeLockerWebSocket>,
    pub order_manager: Arc<OrderManager>,
    pub position_manager: Arc<PositionManager>,
    pub account_manager: Arc<AccountManager>,
    pub is_active: bool,
    pub last_activity: chrono::DateTime<chrono::Utc>,
}

pub struct MultiAccountManager {
    auth: Arc<TradeLockerAuth>,
    sessions: Arc<RwLock<HashMap<String, AccountSession>>>,
    rate_limiter: Arc<AccountRateLimiter>,
    config: TradeLockerConfig,
    environment: TradeLockerEnvironment,
    max_sessions_per_account: usize,
}

impl MultiAccountManager {
    pub async fn new(
        vault_client: Arc<VaultClient>,
        config: TradeLockerConfig,
        environment: TradeLockerEnvironment,
    ) -> Result<Self> {
        let auth = Arc::new(TradeLockerAuth::new(vault_client).await?);
        auth.load_credentials().await?;

        let rate_limiter = Arc::new(AccountRateLimiter::new(config.rate_limit_per_second));

        Ok(Self {
            auth,
            sessions: Arc::new(RwLock::new(HashMap::new())),
            rate_limiter,
            config,
            environment,
            max_sessions_per_account: 3,
        })
    }

    pub async fn create_session(&self, account_id: &str) -> Result<AccountSession> {
        info!("Creating session for account: {}", account_id);

        // Check if we already have a session
        let sessions = self.sessions.read().await;
        if let Some(existing) = sessions.get(account_id) {
            if existing.is_active {
                debug!("Reusing existing session for account: {}", account_id);
                return Ok(existing.clone());
            }
        }
        drop(sessions);

        // Authenticate and create new session
        let token = self.auth.authenticate(account_id).await?;

        // Create client
        let client = Arc::new(TradeLockerClient::new(
            self.auth.clone(),
            self.config.clone(),
            self.environment.clone(),
        )?);

        // Create WebSocket
        let websocket = Arc::new(TradeLockerWebSocket::new(
            self.auth.clone(),
            self.config.clone(),
            self.environment.clone(),
        ));
        
        // Connect WebSocket
        websocket.connect(account_id).await?;

        // Create managers
        let order_manager = Arc::new(OrderManager::new(client.clone()));
        let position_manager = Arc::new(PositionManager::new(client.clone()));
        let account_manager = Arc::new(AccountManager::new(client.clone()));

        // Initialize account data
        account_manager.refresh_account_info(account_id).await?;
        position_manager.refresh_positions(account_id).await?;

        let session = AccountSession {
            account_id: account_id.to_string(),
            client,
            websocket,
            order_manager,
            position_manager,
            account_manager,
            is_active: true,
            last_activity: chrono::Utc::now(),
        };

        // Store session
        let mut sessions = self.sessions.write().await;
        sessions.insert(account_id.to_string(), session.clone());

        info!("Session created successfully for account: {}", account_id);
        Ok(session)
    }

    pub async fn get_session(&self, account_id: &str) -> Result<AccountSession> {
        let sessions = self.sessions.read().await;
        
        sessions
            .get(account_id)
            .filter(|s| s.is_active)
            .cloned()
            .ok_or_else(|| TradeLockerError::AccountNotFound(account_id.to_string()))
    }

    pub async fn close_session(&self, account_id: &str) -> Result<()> {
        let mut sessions = self.sessions.write().await;
        
        if let Some(mut session) = sessions.get_mut(account_id) {
            session.is_active = false;
            session.websocket.disconnect().await;
            info!("Session closed for account: {}", account_id);
        }
        
        Ok(())
    }

    pub async fn close_all_sessions(&self) -> Result<()> {
        let mut sessions = self.sessions.write().await;
        
        for (account_id, session) in sessions.iter_mut() {
            session.is_active = false;
            session.websocket.disconnect().await;
            info!("Session closed for account: {}", account_id);
        }
        
        sessions.clear();
        Ok(())
    }

    pub async fn get_active_sessions(&self) -> Vec<String> {
        self.sessions
            .read()
            .await
            .iter()
            .filter(|(_, s)| s.is_active)
            .map(|(id, _)| id.clone())
            .collect()
    }

    pub async fn refresh_all_sessions(&self) -> Result<()> {
        let sessions = self.sessions.read().await.clone();
        
        for (account_id, session) in sessions {
            if session.is_active {
                // Refresh account info
                if let Err(e) = session.account_manager.refresh_account_info(&account_id).await {
                    error!("Failed to refresh account info for {}: {}", account_id, e);
                }
                
                // Refresh positions
                if let Err(e) = session.position_manager.refresh_positions(&account_id).await {
                    error!("Failed to refresh positions for {}: {}", account_id, e);
                }
            }
        }
        
        Ok(())
    }

    pub async fn load_balance_order(&self, accounts: Vec<String>) -> Result<String> {
        // Simple round-robin load balancing
        // In production, this would consider account health, margin, etc.
        
        let mut best_account = None;
        let mut min_positions = usize::MAX;
        
        for account_id in accounts {
            if let Ok(session) = self.get_session(&account_id).await {
                let position_count = session.position_manager.get_position_count().await;
                
                if position_count < min_positions {
                    min_positions = position_count;
                    best_account = Some(account_id);
                }
            }
        }
        
        best_account.ok_or_else(|| TradeLockerError::Internal("No suitable account found".into()))
    }

    pub async fn get_aggregated_metrics(&self) -> AggregatedMetrics {
        let sessions = self.sessions.read().await;
        let mut metrics = AggregatedMetrics::default();
        
        for (_, session) in sessions.iter() {
            if session.is_active {
                // Get position metrics
                let pos_metrics = session.position_manager.get_metrics().await;
                metrics.total_positions += pos_metrics.total_positions;
                metrics.total_unrealized_pnl += pos_metrics.total_unrealized_pnl;
                metrics.total_realized_pnl += pos_metrics.total_realized_pnl;
                metrics.total_margin_used += pos_metrics.total_margin_used;
                
                // Get account info
                if let Ok(info) = session.account_manager.get_account_info(&session.account_id, false).await {
                    metrics.total_balance += info.balance;
                    metrics.total_equity += info.equity;
                    metrics.total_margin_available += info.margin_available;
                }
                
                metrics.active_accounts += 1;
            }
        }
        
        metrics
    }

    pub async fn monitor_session_health(&self) {
        let mut interval = tokio::time::interval(tokio::time::Duration::from_secs(60));
        
        loop {
            interval.tick().await;
            
            let sessions = self.sessions.read().await.clone();
            
            for (account_id, session) in sessions {
                if session.is_active {
                    // Check WebSocket connection
                    if !session.websocket.is_connected().await {
                        warn!("WebSocket disconnected for account: {}", account_id);
                        
                        // Try to reconnect
                        if let Err(e) = session.websocket.reconnect(&account_id).await {
                            error!("Failed to reconnect WebSocket for {}: {}", account_id, e);
                        }
                    }
                    
                    // Check for margin issues
                    if let Ok(true) = session.account_manager.is_margin_call(&account_id).await {
                        warn!("⚠️ Margin call detected for account: {}", account_id);
                    }
                    
                    // Check session timeout (e.g., 30 minutes of inactivity)
                    let idle_duration = chrono::Utc::now() - session.last_activity;
                    if idle_duration > chrono::Duration::minutes(30) {
                        info!("Session idle for {} minutes, considering cleanup: {}", 
                            idle_duration.num_minutes(), account_id);
                    }
                }
            }
        }
    }

    pub async fn set_account_rate_limit(&self, account_id: &str, limit: u32) {
        self.rate_limiter.set_account_limit(account_id, limit).await;
        info!("Set rate limit for account {} to {} req/s", account_id, limit);
    }

    pub async fn get_rate_limit_status(&self) -> HashMap<String, usize> {
        self.rate_limiter.get_all_rates().await
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct AggregatedMetrics {
    pub active_accounts: usize,
    pub total_positions: usize,
    pub total_balance: rust_decimal::Decimal,
    pub total_equity: rust_decimal::Decimal,
    pub total_margin_used: rust_decimal::Decimal,
    pub total_margin_available: rust_decimal::Decimal,
    pub total_unrealized_pnl: rust_decimal::Decimal,
    pub total_realized_pnl: rust_decimal::Decimal,
}

impl AggregatedMetrics {
    pub fn total_pnl(&self) -> rust_decimal::Decimal {
        self.total_unrealized_pnl + self.total_realized_pnl
    }

    pub fn margin_utilization(&self) -> rust_decimal::Decimal {
        if self.total_margin_available + self.total_margin_used > rust_decimal::Decimal::ZERO {
            (self.total_margin_used / (self.total_margin_available + self.total_margin_used)) 
                * rust_decimal::Decimal::from(100)
        } else {
            rust_decimal::Decimal::ZERO
        }
    }
}