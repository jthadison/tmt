pub mod break_even;
pub mod exit_logger;
pub mod integration;
pub mod news_protection;
pub mod partial_profits;
pub mod platform_adapter;
pub mod time_exits;
pub mod trailing_stops;
pub mod types;

#[cfg(test)]
pub mod tests;

pub use break_even::BreakEvenManager;
pub use exit_logger::ExitAuditLogger;
pub use integration::{ExitManagementComponents, ExitManagementIntegration};
pub use news_protection::NewsEventProtection;
pub use partial_profits::PartialProfitManager;
pub use platform_adapter::{ExitManagementPlatformAdapter, PlatformAdapterFactory};
pub use time_exits::TimeBasedExitManager;
pub use trailing_stops::TrailingStopManager;
pub use types::*;

use async_trait::async_trait;
use std::sync::Arc;
use tokio::time::{interval, Duration};
// Simple trading platform trait for exit management
#[async_trait::async_trait]
pub trait TradingPlatform: Send + Sync + std::fmt::Debug {
    async fn get_positions(&self) -> Result<Vec<types::Position>>;
    async fn get_market_data(&self, symbol: &str) -> Result<types::MarketData>;
    async fn modify_order(
        &self,
        request: types::OrderModifyRequest,
    ) -> Result<types::OrderModifyResult>;
    async fn close_position(
        &self,
        request: types::ClosePositionRequest,
    ) -> Result<types::ClosePositionResult>;
    async fn close_position_partial(
        &self,
        request: types::PartialCloseRequest,
    ) -> Result<types::ClosePositionResult>;
}
use anyhow::Result;
use chrono::{DateTime, Utc};
use uuid::Uuid;

#[derive(Debug, Clone)]
pub struct ExitManagementSystem {
    trailing_stop_manager: Arc<TrailingStopManager>,
    break_even_manager: Arc<BreakEvenManager>,
    partial_profit_manager: Arc<PartialProfitManager>,
    time_exit_manager: Arc<TimeBasedExitManager>,
    news_protection: Arc<NewsEventProtection>,
    exit_logger: Arc<ExitAuditLogger>,
    enabled: bool,
}

impl ExitManagementSystem {
    pub fn new(
        trading_platform: Arc<dyn TradingPlatform>,
        exit_logger: Arc<ExitAuditLogger>,
    ) -> Self {
        let trailing_stop_manager = Arc::new(TrailingStopManager::new(
            trading_platform.clone(),
            exit_logger.clone(),
        ));

        let break_even_manager = Arc::new(BreakEvenManager::new(
            trading_platform.clone(),
            exit_logger.clone(),
        ));

        let partial_profit_manager = Arc::new(PartialProfitManager::new(
            trading_platform.clone(),
            exit_logger.clone(),
        ));

        let time_exit_manager = Arc::new(TimeBasedExitManager::new(
            trading_platform.clone(),
            exit_logger.clone(),
        ));

        let news_protection = Arc::new(NewsEventProtection::new(
            trading_platform.clone(),
            exit_logger.clone(),
        ));

        Self {
            trailing_stop_manager,
            break_even_manager,
            partial_profit_manager,
            time_exit_manager,
            news_protection,
            exit_logger,
            enabled: true,
        }
    }

    /// Create ExitManagementSystem from pre-existing components
    pub fn from_components(
        trailing_stop_manager: Arc<TrailingStopManager>,
        break_even_manager: Arc<BreakEvenManager>,
        partial_profit_manager: Arc<PartialProfitManager>,
        time_exit_manager: Arc<TimeBasedExitManager>,
        news_protection: Arc<NewsEventProtection>,
        exit_logger: Arc<ExitAuditLogger>,
    ) -> Self {
        Self {
            trailing_stop_manager,
            break_even_manager,
            partial_profit_manager,
            time_exit_manager,
            news_protection,
            exit_logger,
            enabled: true,
        }
    }

    pub async fn start_exit_monitoring(&self) -> Result<()> {
        if !self.enabled {
            return Ok(());
        }

        let trailing_manager = self.trailing_stop_manager.clone();
        let break_even_manager = self.break_even_manager.clone();
        let partial_manager = self.partial_profit_manager.clone();
        let time_manager = self.time_exit_manager.clone();
        let news_manager = self.news_protection.clone();

        tokio::spawn(async move {
            let mut interval = interval(Duration::from_millis(500)); // Check every 500ms

            loop {
                interval.tick().await;

                if let Err(e) = trailing_manager.update_trailing_stops().await {
                    tracing::error!("Error updating trailing stops: {}", e);
                }

                if let Err(e) = break_even_manager.check_break_even_triggers().await {
                    tracing::error!("Error checking break-even triggers: {}", e);
                }

                if let Err(e) = partial_manager.check_profit_targets().await {
                    tracing::error!("Error checking profit targets: {}", e);
                }
            }
        });

        tokio::spawn(async move {
            let mut interval = interval(Duration::from_secs(30)); // Check every 30 seconds

            loop {
                interval.tick().await;

                if let Err(e) = time_manager.check_time_based_exits().await {
                    tracing::error!("Error checking time-based exits: {}", e);
                }

                if let Err(e) = news_manager.monitor_upcoming_news().await {
                    tracing::error!("Error monitoring news events: {}", e);
                }

                if let Err(e) = news_manager.restore_post_news_stops().await {
                    tracing::error!("Error restoring post-news stops: {}", e);
                }
            }
        });

        tracing::info!("Exit management system monitoring started");
        Ok(())
    }

    pub fn enable(&mut self) {
        self.enabled = true;
    }

    pub fn disable(&mut self) {
        self.enabled = false;
    }

    pub fn is_enabled(&self) -> bool {
        self.enabled
    }

    pub async fn emergency_close_all_positions(&self, reason: String) -> Result<Vec<ExitResult>> {
        tracing::warn!("Emergency close triggered: {}", reason);

        let mut results = Vec::new();

        // Get all open positions - this would need to be implemented based on your position tracking
        // For now, returning empty results

        self.exit_logger.log_emergency_close_event(reason).await?;

        Ok(results)
    }

    pub fn get_trailing_stop_manager(&self) -> Arc<TrailingStopManager> {
        self.trailing_stop_manager.clone()
    }

    pub fn get_break_even_manager(&self) -> Arc<BreakEvenManager> {
        self.break_even_manager.clone()
    }

    pub fn get_partial_profit_manager(&self) -> Arc<PartialProfitManager> {
        self.partial_profit_manager.clone()
    }
}
