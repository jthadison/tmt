use std::sync::Arc;
use tokio::sync::RwLock;
use rust_decimal::Decimal;
use chrono::{DateTime, Utc};
use tracing::{debug, info, warn};

use super::{
    TradeLockerClient, AccountInfo,
    TradeLockerError, Result
};

#[derive(Debug, Clone)]
pub struct AccountManager {
    client: Arc<TradeLockerClient>,
    account_info: Arc<RwLock<Option<AccountInfo>>>,
    last_update: Arc<RwLock<DateTime<Utc>>>,
    update_interval_secs: u64,
}

impl AccountManager {
    pub fn new(client: Arc<TradeLockerClient>) -> Self {
        Self {
            client,
            account_info: Arc::new(RwLock::new(None)),
            last_update: Arc::new(RwLock::new(Utc::now())),
            update_interval_secs: 5, // Update every 5 seconds max
        }
    }

    pub async fn get_account_info(&self, account_id: &str, force_refresh: bool) -> Result<AccountInfo> {
        let should_refresh = if force_refresh {
            true
        } else {
            let last = *self.last_update.read().await;
            (Utc::now() - last).num_seconds() > self.update_interval_secs as i64
        };

        if should_refresh {
            self.refresh_account_info(account_id).await?;
        }

        self.account_info
            .read()
            .await
            .clone()
            .ok_or_else(|| TradeLockerError::AccountNotFound(account_id.to_string()))
    }

    pub async fn refresh_account_info(&self, account_id: &str) -> Result<AccountInfo> {
        debug!("Refreshing account info for: {}", account_id);
        
        let info = self.client.get_account_info(account_id).await?;
        
        *self.account_info.write().await = Some(info.clone());
        *self.last_update.write().await = Utc::now();
        
        self.log_account_status(&info);
        
        Ok(info)
    }

    pub async fn get_balance(&self, account_id: &str) -> Result<Decimal> {
        let info = self.get_account_info(account_id, false).await?;
        Ok(info.balance)
    }

    pub async fn get_equity(&self, account_id: &str) -> Result<Decimal> {
        let info = self.get_account_info(account_id, false).await?;
        Ok(info.equity)
    }

    pub async fn get_margin_available(&self, account_id: &str) -> Result<Decimal> {
        let info = self.get_account_info(account_id, false).await?;
        Ok(info.margin_available)
    }

    pub async fn get_margin_level(&self, account_id: &str) -> Result<Option<Decimal>> {
        let info = self.get_account_info(account_id, false).await?;
        Ok(info.margin_level)
    }

    pub async fn check_margin_for_order(
        &self,
        account_id: &str,
        symbol: &str,
        quantity: Decimal,
        leverage: Decimal,
    ) -> Result<bool> {
        let info = self.get_account_info(account_id, false).await?;
        
        // Simplified margin calculation - in production this would be more complex
        let required_margin = quantity / leverage;
        
        if required_margin > info.margin_available {
            warn!(
                "Insufficient margin for {}: required={}, available={}",
                symbol, required_margin, info.margin_available
            );
            return Ok(false);
        }
        
        Ok(true)
    }

    pub async fn is_margin_call(&self, account_id: &str) -> Result<bool> {
        let info = self.get_account_info(account_id, false).await?;
        
        if let Some(margin_level) = info.margin_level {
            // Typical margin call level is 100% or below
            Ok(margin_level <= Decimal::from(100))
        } else {
            Ok(false)
        }
    }

    pub async fn is_stop_out(&self, account_id: &str) -> Result<bool> {
        let info = self.get_account_info(account_id, false).await?;
        
        if let Some(margin_level) = info.margin_level {
            // Typical stop out level is 50% or below
            Ok(margin_level <= Decimal::from(50))
        } else {
            Ok(false)
        }
    }

    pub async fn get_profit_loss(&self, account_id: &str) -> Result<(Decimal, Decimal)> {
        let info = self.get_account_info(account_id, false).await?;
        Ok((info.unrealized_pnl, info.realized_pnl))
    }

    pub async fn update_from_websocket(&self, account_update: AccountInfo) {
        *self.account_info.write().await = Some(account_update.clone());
        *self.last_update.write().await = Utc::now();
        
        self.log_account_status(&account_update);
    }

    fn log_account_status(&self, info: &AccountInfo) {
        info!(
            "Account {}: Balance={}, Equity={}, Margin Used={}, Available={}, Unrealized P&L={}",
            info.account_id,
            info.balance,
            info.equity,
            info.margin_used,
            info.margin_available,
            info.unrealized_pnl
        );

        if let Some(margin_level) = info.margin_level {
            if margin_level <= Decimal::from(100) {
                warn!("⚠️ MARGIN WARNING: Account {} margin level at {}%", info.account_id, margin_level);
            }
        }
    }

    pub async fn monitor_account_health(&self, account_id: String) {
        let mut interval = tokio::time::interval(tokio::time::Duration::from_secs(30));
        
        loop {
            interval.tick().await;
            
            match self.refresh_account_info(&account_id).await {
                Ok(info) => {
                    // Check for critical conditions
                    if let Some(margin_level) = info.margin_level {
                        if margin_level <= Decimal::from(50) {
                            warn!("🚨 CRITICAL: Account {} approaching stop-out level: {}%", 
                                account_id, margin_level);
                        }
                    }
                    
                    // Check for excessive losses
                    let total_loss = info.unrealized_pnl + info.realized_pnl;
                    let loss_percentage = if info.balance > Decimal::ZERO {
                        (total_loss.abs() / info.balance) * Decimal::from(100)
                    } else {
                        Decimal::ZERO
                    };
                    
                    if loss_percentage > Decimal::from(10) {
                        warn!("⚠️ Account {} has lost {}% of balance", account_id, loss_percentage);
                    }
                }
                Err(e) => {
                    warn!("Failed to monitor account health for {}: {}", account_id, e);
                }
            }
        }
    }
}