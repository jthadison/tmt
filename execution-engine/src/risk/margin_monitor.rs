use crate::risk::config::MarginThresholds;
use anyhow::Result;
use chrono::{DateTime, Utc};
use dashmap::DashMap;
use risk_types::*;
use rust_decimal::Decimal;
use rust_decimal_macros::dec;
use std::sync::Arc;
use tokio::time::{interval, Duration};
use tracing::{error, info, warn};

pub struct MarginMonitor {
    account_manager: Arc<AccountManager>,
    margin_calculator: Arc<MarginCalculator>,
    margin_alerts: Arc<MarginAlertManager>,
    margin_thresholds: MarginThresholds,
    margin_cache: Arc<DashMap<AccountId, MarginInfo>>,
    margin_protection: Arc<MarginProtectionSystem>,
}

impl MarginMonitor {
    pub fn new(
        account_manager: Arc<AccountManager>,
        margin_calculator: Arc<MarginCalculator>,
        margin_alerts: Arc<MarginAlertManager>,
        margin_protection: Arc<MarginProtectionSystem>,
        margin_thresholds: MarginThresholds,
    ) -> Self {
        Self {
            account_manager,
            margin_calculator,
            margin_alerts,
            margin_thresholds,
            margin_cache: Arc::new(DashMap::new()),
            margin_protection,
        }
    }

    pub async fn start_monitoring(&self) -> Result<()> {
        let mut ticker = interval(Duration::from_secs(
            self.margin_thresholds.monitoring_interval_secs,
        ));
        info!(
            "Started margin monitoring with {}-second intervals",
            self.margin_thresholds.monitoring_interval_secs
        );

        loop {
            ticker.tick().await;

            if let Err(e) = self.check_all_account_margins().await {
                error!("Failed to check margin levels: {}", e);
            }
        }
    }

    async fn check_all_account_margins(&self) -> Result<()> {
        let accounts = self.account_manager.get_all_active_accounts().await?;

        for account in accounts {
            let margin_info = self.calculate_account_margin(&account).await?;

            self.check_margin_thresholds(&account, &margin_info).await?;

            self.update_margin_cache(&account.id, &margin_info).await?;

            self.publish_margin_update(&margin_info).await?;
        }

        Ok(())
    }

    pub async fn calculate_account_margin(&self, account: &Account) -> Result<MarginInfo> {
        let positions = self
            .account_manager
            .get_account_positions(&account.id)
            .await?;

        let mut used_margin = dec!(0);
        for position in &positions {
            used_margin += self
                .margin_calculator
                .calculate_position_margin(position)
                .await?;
        }

        let account_balance = account.balance;
        let account_equity = account_balance
            + positions
                .iter()
                .filter_map(|p| p.unrealized_pnl)
                .sum::<Decimal>();

        let free_margin = account_equity - used_margin;
        let margin_level = if used_margin > dec!(0) {
            (account_equity / used_margin) * dec!(100)
        } else {
            // No margin used - account has infinite margin level (safe state)
            // Using MAX value to represent infinite margin level
            Decimal::MAX
        };

        Ok(MarginInfo {
            account_id: account.id,
            balance: account_balance,
            equity: account_equity,
            used_margin,
            free_margin,
            margin_level,
            positions_count: positions.len(),
            timestamp: Utc::now(),
        })
    }

    async fn check_margin_thresholds(
        &self,
        account: &Account,
        margin_info: &MarginInfo,
    ) -> Result<()> {
        if margin_info.margin_level <= self.margin_thresholds.warning_level
            && margin_info.margin_level > self.margin_thresholds.critical_level
        {
            self.margin_alerts
                .send_warning_alert(MarginAlert {
                    account_id: account.id,
                    level: AlertLevel::Warning,
                    margin_level: margin_info.margin_level,
                    threshold: self.margin_thresholds.warning_level,
                    message: format!(
                        "Margin level at {:.2}% - approaching warning threshold",
                        margin_info.margin_level
                    ),
                    timestamp: Utc::now(),
                })
                .await?;
        }

        if margin_info.margin_level <= self.margin_thresholds.critical_level
            && margin_info.margin_level > self.margin_thresholds.stop_out_level
        {
            self.margin_alerts
                .send_critical_alert(MarginAlert {
                    account_id: account.id,
                    level: AlertLevel::Critical,
                    margin_level: margin_info.margin_level,
                    threshold: self.margin_thresholds.critical_level,
                    message: format!(
                        "CRITICAL: Margin level at {:.2}% - immediate action required",
                        margin_info.margin_level
                    ),
                    timestamp: Utc::now(),
                })
                .await?;

            self.trigger_margin_protection(account.id, margin_info)
                .await?;
        }

        if margin_info.margin_level <= self.margin_thresholds.stop_out_level {
            self.margin_alerts
                .send_emergency_alert(MarginAlert {
                    account_id: account.id,
                    level: AlertLevel::Emergency,
                    margin_level: margin_info.margin_level,
                    threshold: self.margin_thresholds.stop_out_level,
                    message: format!(
                        "EMERGENCY: Margin level at {:.2}% - stop out imminent",
                        margin_info.margin_level
                    ),
                    timestamp: Utc::now(),
                })
                .await?;

            self.trigger_emergency_stop_out(account.id, margin_info)
                .await?;
        }

        Ok(())
    }

    async fn trigger_margin_protection(
        &self,
        account_id: AccountId,
        margin_info: &MarginInfo,
    ) -> Result<()> {
        info!(
            "Triggering margin protection for account {} at {:.2}% margin level",
            account_id, margin_info.margin_level
        );

        self.margin_protection
            .protect_account(account_id, margin_info)
            .await?;

        Ok(())
    }

    async fn trigger_emergency_stop_out(
        &self,
        account_id: AccountId,
        margin_info: &MarginInfo,
    ) -> Result<()> {
        warn!(
            "EMERGENCY STOP OUT: Account {} at {:.2}% margin level - closing all positions",
            account_id, margin_info.margin_level
        );

        self.margin_protection
            .emergency_stop_out(account_id, margin_info)
            .await?;

        Ok(())
    }

    async fn update_margin_cache(
        &self,
        account_id: &AccountId,
        margin_info: &MarginInfo,
    ) -> Result<()> {
        self.margin_cache.insert(*account_id, margin_info.clone());
        Ok(())
    }

    async fn publish_margin_update(&self, margin_info: &MarginInfo) -> Result<()> {
        let _update = RiskUpdate {
            account_id: margin_info.account_id,
            update_type: "margin".to_string(),
            current_value: margin_info.margin_level,
            previous_value: self
                .margin_cache
                .get(&margin_info.account_id)
                .map(|prev| prev.margin_level),
            threshold_status: self.determine_threshold_status(margin_info.margin_level),
            timestamp: Utc::now(),
        };

        info!(
            "Margin update for account {}: {:.2}%",
            margin_info.account_id, margin_info.margin_level
        );

        Ok(())
    }

    fn determine_threshold_status(&self, margin_level: Decimal) -> String {
        if margin_level > self.margin_thresholds.warning_level {
            "safe".to_string()
        } else if margin_level > self.margin_thresholds.critical_level {
            "warning".to_string()
        } else if margin_level > self.margin_thresholds.stop_out_level {
            "critical".to_string()
        } else {
            "emergency".to_string()
        }
    }

    pub async fn get_margin_requirements(
        &self,
        account_id: AccountId,
    ) -> Result<MarginRequirements> {
        let margin_info = self
            .margin_cache
            .get(&account_id)
            .map(|m| m.clone())
            .ok_or_else(|| anyhow::anyhow!("No margin info for account"))?;

        let margin_to_maintain_150 = margin_info.equity / dec!(1.5);
        let margin_to_maintain_120 = margin_info.equity / dec!(1.2);
        let available_for_new_positions = margin_info.free_margin;

        let max_position_size_at_100_1 = available_for_new_positions * dec!(100);
        let max_position_size_at_50_1 = available_for_new_positions * dec!(50);

        Ok(MarginRequirements {
            account_id,
            current_margin_level: margin_info.margin_level,
            margin_to_maintain_150,
            margin_to_maintain_120,
            available_for_new_positions,
            max_position_size_at_100_1,
            max_position_size_at_50_1,
            timestamp: Utc::now(),
        })
    }

    pub async fn simulate_margin_impact(
        &self,
        account_id: AccountId,
        new_position: &ProposedPosition,
    ) -> Result<MarginImpact> {
        let current_margin_info = self
            .margin_cache
            .get(&account_id)
            .map(|m| m.clone())
            .ok_or_else(|| anyhow::anyhow!("No margin info for account"))?;

        let additional_margin = self
            .margin_calculator
            .calculate_proposed_position_margin(new_position)
            .await?;

        let new_used_margin = current_margin_info.used_margin + additional_margin;
        let new_free_margin = current_margin_info.equity - new_used_margin;
        let new_margin_level = if new_used_margin != dec!(0) {
            (current_margin_info.equity / new_used_margin) * dec!(100)
        } else {
            dec!(999999)
        };

        let impact_acceptable = new_margin_level >= self.margin_thresholds.warning_level;

        Ok(MarginImpact {
            current_margin_level: current_margin_info.margin_level,
            projected_margin_level: new_margin_level,
            additional_margin_required: additional_margin,
            remaining_free_margin: new_free_margin,
            impact_acceptable,
            warning_message: if !impact_acceptable {
                Some(format!(
                    "Position would reduce margin level to {:.2}% - below warning threshold",
                    new_margin_level
                ))
            } else {
                None
            },
        })
    }
}

pub struct AccountManager {
    accounts: Arc<DashMap<AccountId, Account>>,
    account_positions: Arc<DashMap<AccountId, Vec<Position>>>,
}

impl AccountManager {
    pub fn new() -> Self {
        Self {
            accounts: Arc::new(DashMap::new()),
            account_positions: Arc::new(DashMap::new()),
        }
    }

    pub async fn get_all_active_accounts(&self) -> Result<Vec<Account>> {
        Ok(self
            .accounts
            .iter()
            .filter(|entry| entry.active)
            .map(|entry| entry.value().clone())
            .collect())
    }

    pub async fn get_account_positions(&self, account_id: &AccountId) -> Result<Vec<Position>> {
        Ok(self
            .account_positions
            .get(account_id)
            .map(|positions| positions.clone())
            .unwrap_or_default())
    }

    pub async fn add_account(&self, account: Account) {
        self.accounts.insert(account.id, account);
    }

    pub async fn add_position(&self, position: Position) {
        self.account_positions
            .entry(position.account_id)
            .or_insert_with(Vec::new)
            .push(position);
    }
}

pub struct MarginCalculator {
    leverage_map: Arc<DashMap<String, Decimal>>,
    default_leverage: Decimal,
}

impl MarginCalculator {
    pub fn new() -> Self {
        let mut leverage_map = DashMap::new();
        leverage_map.insert("EURUSD".to_string(), dec!(100));
        leverage_map.insert("GBPUSD".to_string(), dec!(100));
        leverage_map.insert("USDJPY".to_string(), dec!(100));
        leverage_map.insert("GOLD".to_string(), dec!(20));

        Self {
            leverage_map: Arc::new(leverage_map),
            default_leverage: dec!(50),
        }
    }

    pub async fn calculate_position_margin(&self, position: &Position) -> Result<Decimal> {
        let leverage = self
            .leverage_map
            .get(&position.symbol)
            .map(|l| *l)
            .unwrap_or(self.default_leverage);

        let nominal_value = position.size * position.entry_price;
        Ok(nominal_value / leverage)
    }

    pub async fn calculate_proposed_position_margin(
        &self,
        proposed: &ProposedPosition,
    ) -> Result<Decimal> {
        let leverage = self
            .leverage_map
            .get(&proposed.symbol)
            .map(|l| *l)
            .unwrap_or(self.default_leverage);

        let nominal_value = proposed.size * proposed.expected_entry_price;
        Ok(nominal_value / leverage)
    }
}

pub struct MarginAlertManager {
    alerts: Arc<DashMap<AccountId, Vec<MarginAlert>>>,
}

impl MarginAlertManager {
    pub fn new() -> Self {
        Self {
            alerts: Arc::new(DashMap::new()),
        }
    }

    pub async fn send_warning_alert(&self, alert: MarginAlert) -> Result<()> {
        warn!("Margin Warning: {}", alert.message);
        self.store_alert(alert).await
    }

    pub async fn send_critical_alert(&self, alert: MarginAlert) -> Result<()> {
        error!("Margin Critical: {}", alert.message);
        self.store_alert(alert).await
    }

    pub async fn send_emergency_alert(&self, alert: MarginAlert) -> Result<()> {
        error!("MARGIN EMERGENCY: {}", alert.message);
        self.store_alert(alert).await
    }

    async fn store_alert(&self, alert: MarginAlert) -> Result<()> {
        self.alerts
            .entry(alert.account_id)
            .or_insert_with(Vec::new)
            .push(alert);
        Ok(())
    }
}

pub struct MarginProtectionSystem;

impl MarginProtectionSystem {
    pub async fn protect_account(
        &self,
        account_id: AccountId,
        margin_info: &MarginInfo,
    ) -> Result<()> {
        info!(
            "Protecting account {} with margin level {:.2}%",
            account_id, margin_info.margin_level
        );

        Ok(())
    }

    pub async fn emergency_stop_out(
        &self,
        account_id: AccountId,
        margin_info: &MarginInfo,
    ) -> Result<()> {
        warn!(
            "Emergency stop out for account {} at margin level {:.2}%",
            account_id, margin_info.margin_level
        );

        Ok(())
    }
}

#[derive(Debug, Clone)]
pub struct Account {
    pub id: AccountId,
    pub balance: Decimal,
    pub active: bool,
}

#[derive(Debug, Clone)]
pub struct ProposedPosition {
    pub symbol: String,
    pub size: Decimal,
    pub expected_entry_price: Decimal,
}

#[derive(Debug, Clone)]
pub struct MarginRequirements {
    pub account_id: AccountId,
    pub current_margin_level: Decimal,
    pub margin_to_maintain_150: Decimal,
    pub margin_to_maintain_120: Decimal,
    pub available_for_new_positions: Decimal,
    pub max_position_size_at_100_1: Decimal,
    pub max_position_size_at_50_1: Decimal,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone)]
pub struct MarginImpact {
    pub current_margin_level: Decimal,
    pub projected_margin_level: Decimal,
    pub additional_margin_required: Decimal,
    pub remaining_free_margin: Decimal,
    pub impact_acceptable: bool,
    pub warning_message: Option<String>,
}
