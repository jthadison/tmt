use std::collections::HashMap;
use std::sync::Arc;
use dashmap::DashMap;
use anyhow::{Result, Context};
use chrono::{DateTime, Utc, Duration};
use tracing::{info, warn, error};
use rust_decimal::Decimal;

use super::TradingPlatform;
use super::types::*;
use super::exit_logger::ExitAuditLogger;

#[derive(Debug, Clone)]
pub struct EconomicCalendarClient {
    // This would be a real economic calendar API client
    // For now, it's a placeholder
    api_key: String,
    base_url: String,
}

impl EconomicCalendarClient {
    pub fn new(api_key: String, base_url: String) -> Self {
        Self { api_key, base_url }
    }

    pub async fn get_upcoming_events(&self, lookback: Duration, min_impact: ImpactLevel) -> Result<Vec<NewsEvent>> {
        // In a real implementation, this would make HTTP requests to an economic calendar API
        // For now, returning mock data
        let now = Utc::now();
        
        Ok(vec![
            NewsEvent {
                id: "USD_NFP_001".to_string(),
                description: "US Non-Farm Payrolls".to_string(),
                currency: "USD".to_string(),
                impact: ImpactLevel::High,
                time: now + Duration::from_std(std::time::Duration::from_secs(2 * 3600)).unwrap(),
            },
            NewsEvent {
                id: "EUR_ECB_001".to_string(),
                description: "ECB Interest Rate Decision".to_string(),
                currency: "EUR".to_string(),
                impact: ImpactLevel::High,
                time: now + Duration::from_std(std::time::Duration::from_secs(4 * 3600)).unwrap(),
            },
        ])
    }
}

#[derive(Debug)]
pub struct NewsEventProtection {
    trading_platform: Arc<dyn TradingPlatform>,
    exit_logger: Arc<ExitAuditLogger>,
    economic_calendar: EconomicCalendarClient,
    news_configs: HashMap<String, NewsProtectionConfig>,
    protected_positions: Arc<DashMap<PositionId, NewsProtection>>,
}

impl NewsEventProtection {
    pub fn new(
        trading_platform: Arc<dyn TradingPlatform>,
        exit_logger: Arc<ExitAuditLogger>,
    ) -> Self {
        // In a real implementation, these would come from configuration
        let economic_calendar = EconomicCalendarClient::new(
            "demo_api_key".to_string(),
            "https://api.forexfactory.com".to_string(),
        );

        Self {
            trading_platform,
            exit_logger,
            economic_calendar,
            news_configs: HashMap::new(),
            protected_positions: Arc::new(DashMap::new()),
        }
    }

    pub fn configure_currency(&mut self, currency: String, config: NewsProtectionConfig) {
        self.news_configs.insert(currency, config);
    }

    pub async fn monitor_upcoming_news(&self) -> Result<()> {
        let lookback_duration = Duration::from_std(std::time::Duration::from_secs(4 * 3600)).unwrap();
        let upcoming_events = self.economic_calendar
            .get_upcoming_events(lookback_duration, ImpactLevel::High).await?;

        for event in upcoming_events {
            if let Err(e) = self.apply_news_protection(&event).await {
                error!("Failed to apply news protection for event {}: {}", event.id, e);
            }
        }

        Ok(())
    }

    async fn apply_news_protection(&self, event: &NewsEvent) -> Result<()> {
        let affected_positions = self.get_positions_for_currency(&event.currency).await?;
        let default_config = NewsProtectionConfig::default();
        let config = self.news_configs.get(&event.currency)
            .unwrap_or(&default_config);

        if !config.enabled {
            return Ok(());
        }

        info!(
            "Applying news protection for {} event: {} ({} positions affected)",
            event.currency, event.description, affected_positions.len()
        );

        for position in affected_positions {
            // Check if already protected for this event
            if self.is_position_protected(&position.id, &event.id) {
                continue;
            }

            match config.protection_strategy {
                NewsProtectionStrategy::TightenStops => {
                    self.tighten_stops_for_news(&position, event, config).await?;
                },
                NewsProtectionStrategy::ClosePosition => {
                    self.close_position_for_news(&position, event).await?;
                },
                NewsProtectionStrategy::ReduceSize => {
                    self.reduce_position_for_news(&position, event, config).await?;
                }
            }
        }

        Ok(())
    }

    async fn tighten_stops_for_news(
        &self,
        position: &Position,
        event: &NewsEvent,
        config: &NewsProtectionConfig
    ) -> Result<()> {
        let current_stop = position.stop_loss.unwrap_or(position.entry_price);
        let entry_price = position.entry_price;

        // Calculate tightened stop level
        let normal_risk = match position.position_type {
            UnifiedPositionSide::Long => entry_price - current_stop,
            UnifiedPositionSide::Short => current_stop - entry_price,
        };

        let reduced_risk = normal_risk * config.stop_tighten_factor;
        let new_stop = match position.position_type {
            UnifiedPositionSide::Long => entry_price - reduced_risk,
            UnifiedPositionSide::Short => entry_price + reduced_risk,
        };

        // Apply the tightened stop
        let modify_request = OrderModifyRequest {
            order_id: position.order_id.clone(),
            new_stop_loss: Some(new_stop),
            new_take_profit: position.take_profit,
        };

        self.trading_platform.modify_order(modify_request).await
            .context("Failed to tighten stop for news protection")?;

        // Record news protection
        let protection = NewsProtection {
            position_id: position.id,
            original_stop: current_stop,
            protected_stop: new_stop,
            news_event: event.clone(),
            protection_start: Utc::now(),
            restoration_scheduled: Some(event.time + Duration::from_std(std::time::Duration::from_secs(2 * 3600)).unwrap()),
        };

        self.protected_positions.insert(position.id, protection);

        // Log protection application
        self.log_news_protection(position, event, current_stop, new_stop).await?;

        info!(
            "News protection applied to position {}: Stop tightened from {} to {} for {} event",
            position.id, current_stop, new_stop, event.description
        );

        Ok(())
    }

    async fn close_position_for_news(&self, position: &Position, event: &NewsEvent) -> Result<()> {
        let close_request = ClosePositionRequest {
            position_id: position.id,
            reason: format!("Pre-news closure for {} event: {}", event.currency, event.description),
        };

        let close_result = self.trading_platform.close_position(close_request).await
            .context("Failed to close position for news protection")?;

        // Log news-related closure
        self.log_news_closure(position, event, close_result.close_price).await?;

        info!(
            "Position {} closed for news protection: {} event at price {}",
            position.id, event.description, close_result.close_price
        );

        Ok(())
    }

    async fn reduce_position_for_news(
        &self,
        position: &Position,
        event: &NewsEvent,
        config: &NewsProtectionConfig
    ) -> Result<()> {
        // Reduce position size by 50%
        let reduction_percentage = 0.5;
        let reduce_volume = position.volume * Decimal::from_f64_retain(reduction_percentage).unwrap();

        let close_request = PartialCloseRequest {
            position_id: position.id,
            volume: reduce_volume,
            reason: format!("News protection size reduction for {}: {}", event.currency, event.description),
        };

        let close_result = self.trading_platform.close_position_partial(close_request).await
            .context("Failed to reduce position size for news protection")?;

        // Log size reduction
        self.log_news_size_reduction(position, event, reduce_volume, close_result.close_price).await?;

        info!(
            "Position {} size reduced by {:.1}% for news protection: {} event",
            position.id, reduction_percentage * 100.0, event.description
        );

        Ok(())
    }

    pub async fn restore_post_news_stops(&self) -> Result<()> {
        let now = Utc::now();
        let mut to_restore = Vec::new();

        // Find positions ready for stop restoration
        for protection_ref in self.protected_positions.iter() {
            let protection = protection_ref.value();
            if let Some(restore_time) = protection.restoration_scheduled {
                if now >= restore_time {
                    to_restore.push(protection.clone());
                }
            }
        }

        // Restore original stops
        for protection in to_restore {
            if let Err(e) = self.restore_reasonable_stop(&protection).await {
                error!("Failed to restore stop for position {}: {}", protection.position_id, e);
            }
        }

        Ok(())
    }

    async fn restore_reasonable_stop(&self, protection: &NewsProtection) -> Result<()> {
        // Check if position still exists
        let positions = self.trading_platform.get_positions().await?;
        
        if let Some(position) = positions.iter().find(|p| p.id == protection.position_id) {
            // Calculate a reasonable stop level based on current market conditions
            let reasonable_stop = self.calculate_reasonable_stop_post_news(position).await?;

            let modify_request = OrderModifyRequest {
                order_id: position.order_id.clone(),
                new_stop_loss: Some(reasonable_stop),
                new_take_profit: position.take_profit,
            };

            self.trading_platform.modify_order(modify_request).await
                .context("Failed to restore stop after news event")?;

            // Log restoration
            self.log_stop_restoration(position, protection, reasonable_stop).await?;

            info!(
                "Post-news stop restoration for position {}: {} -> {}",
                position.id, protection.protected_stop, reasonable_stop
            );
        }

        // Remove from protected positions
        self.protected_positions.remove(&protection.position_id);

        Ok(())
    }

    async fn calculate_reasonable_stop_post_news(&self, position: &Position) -> Result<f64> {
        // This would use technical analysis to determine a reasonable stop level
        // For now, using a simple ATR-based calculation
        
        let market_data = self.trading_platform.get_market_data(&position.symbol).await?;
        let current_price = (market_data.bid + market_data.ask) / 2.0;
        
        // Use 2x ATR for stop distance (simplified)
        let atr_distance = market_data.spread * 4.0; // Simplified ATR calculation
        
        let reasonable_stop = match position.position_type {
            UnifiedPositionSide::Long => current_price - atr_distance,
            UnifiedPositionSide::Short => current_price + atr_distance,
        };

        Ok(reasonable_stop)
    }

    async fn get_positions_for_currency(&self, currency: &str) -> Result<Vec<Position>> {
        let all_positions = self.trading_platform.get_positions().await?;
        
        // Filter positions that involve the specified currency
        let affected_positions: Vec<Position> = all_positions
            .into_iter()
            .filter(|pos| {
                // Check if the position's symbol contains the currency
                // e.g., "EURUSD" contains "EUR" and "USD"
                pos.symbol.contains(currency)
            })
            .collect();

        Ok(affected_positions)
    }

    fn is_position_protected(&self, position_id: &PositionId, event_id: &str) -> bool {
        if let Some(protection) = self.protected_positions.get(position_id) {
            protection.news_event.id == event_id
        } else {
            false
        }
    }

    async fn log_news_protection(
        &self,
        position: &Position,
        event: &NewsEvent,
        old_stop: f64,
        new_stop: f64
    ) -> Result<()> {
        let current_price = (self.trading_platform.get_market_data(&position.symbol).await?).ask;
        
        let market_context = MarketContext {
            current_price,
            atr_14: 0.0015, // Simplified
            trend_strength: 0.3, // Reduced during news protection
            volatility: 0.05, // Increased volatility expected
            spread: 0.0002, // Wider spreads during news
            timestamp: Utc::now(),
        };

        let modification = ExitModification {
            position_id: position.id,
            modification_type: ExitModificationType::NewsProtection,
            old_value: old_stop,
            new_value: new_stop,
            reasoning: format!(
                "News protection: Stop tightened for {} {} event (Impact: {:?})",
                event.currency, event.description, event.impact
            ),
            market_context,
        };

        self.exit_logger.log_exit_modification(modification).await?;
        Ok(())
    }

    async fn log_news_closure(&self, position: &Position, event: &NewsEvent, close_price: f64) -> Result<()> {
        let market_context = MarketContext {
            current_price: close_price,
            atr_14: 0.0015,
            trend_strength: 0.0, // Position closed
            volatility: 0.05,
            spread: 0.0002,
            timestamp: Utc::now(),
        };

        let modification = ExitModification {
            position_id: position.id,
            modification_type: ExitModificationType::NewsProtection,
            old_value: position.entry_price,
            new_value: close_price,
            reasoning: format!(
                "News protection: Position closed before {} {} event",
                event.currency, event.description
            ),
            market_context,
        };

        self.exit_logger.log_exit_modification(modification).await?;
        Ok(())
    }

    async fn log_news_size_reduction(
        &self,
        position: &Position,
        event: &NewsEvent,
        reduced_volume: Decimal,
        close_price: f64
    ) -> Result<()> {
        let market_context = MarketContext {
            current_price: close_price,
            atr_14: 0.0015,
            trend_strength: 0.5,
            volatility: 0.05,
            spread: 0.0002,
            timestamp: Utc::now(),
        };

        let modification = ExitModification {
            position_id: position.id,
            modification_type: ExitModificationType::NewsProtection,
            old_value: f64::try_from(position.volume).unwrap_or(0.0),
            new_value: f64::try_from(reduced_volume).unwrap_or(0.0),
            reasoning: format!(
                "News protection: Position size reduced by {:.4} lots for {} {} event",
                reduced_volume, event.currency, event.description
            ),
            market_context,
        };

        self.exit_logger.log_exit_modification(modification).await?;
        Ok(())
    }

    async fn log_stop_restoration(&self, position: &Position, protection: &NewsProtection, new_stop: f64) -> Result<()> {
        let current_price = (self.trading_platform.get_market_data(&position.symbol).await?).ask;
        
        let market_context = MarketContext {
            current_price,
            atr_14: 0.0015,
            trend_strength: 0.5, // Normal conditions restored
            volatility: 0.02, // Normal volatility
            spread: 0.0001, // Normal spreads
            timestamp: Utc::now(),
        };

        let modification = ExitModification {
            position_id: position.id,
            modification_type: ExitModificationType::NewsProtection,
            old_value: protection.protected_stop,
            new_value: new_stop,
            reasoning: format!(
                "News protection: Stop restored post-{} event",
                protection.news_event.description
            ),
            market_context,
        };

        self.exit_logger.log_exit_modification(modification).await?;
        Ok(())
    }

    pub fn get_protected_positions(&self) -> Vec<(PositionId, NewsProtection)> {
        self.protected_positions
            .iter()
            .map(|entry| (*entry.key(), entry.value().clone()))
            .collect()
    }

    pub fn get_protection_count(&self) -> usize {
        self.protected_positions.len()
    }

    pub async fn get_news_protection_stats(&self) -> Result<NewsProtectionStats> {
        // This would typically query historical data
        Ok(NewsProtectionStats {
            protections_applied: self.protected_positions.len() as u32,
            positions_closed_pre_news: 0, // From historical data
            stops_tightened: 0, // From historical data
            protection_effectiveness: 0.85, // From historical analysis
        })
    }

    pub fn remove_protection(&self, position_id: PositionId) {
        self.protected_positions.remove(&position_id);
    }

    pub async fn force_restore_protection(&self, position_id: PositionId) -> Result<()> {
        if let Some((_, protection)) = self.protected_positions.remove(&position_id) {
            self.restore_reasonable_stop(&protection).await?;
            info!("Forced restoration of protection for position {}", position_id);
        } else {
            warn!("No protection found for position {}", position_id);
        }
        Ok(())
    }

    pub async fn get_upcoming_news_events(&self, hours_ahead: u32) -> Result<Vec<NewsEvent>> {
        let lookback = Duration::from_std(std::time::Duration::from_secs(hours_ahead as u64 * 3600)).unwrap();
        self.economic_calendar.get_upcoming_events(lookback, ImpactLevel::Medium).await
    }

    pub fn has_position_protection(&self, position_id: PositionId) -> bool {
        self.protected_positions.contains_key(&position_id)
    }
}