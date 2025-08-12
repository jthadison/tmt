use std::collections::HashMap;
use std::sync::Arc;
use dashmap::DashMap;
use anyhow::{Result, Context};
use chrono::{DateTime, Utc};
use tracing::{info, warn, error};

use super::TradingPlatform;
use super::types::*;
use super::exit_logger::ExitAuditLogger;

#[derive(Debug)]
pub struct TrailingStopManager {
    trading_platform: Arc<dyn TradingPlatform>,
    exit_logger: Arc<ExitAuditLogger>,
    trail_configs: HashMap<String, TrailingConfig>,
    active_trails: Arc<DashMap<PositionId, ActiveTrail>>,
    atr_cache: Arc<DashMap<String, ATRCalculation>>,
}

impl TrailingStopManager {
    pub fn new(
        trading_platform: Arc<dyn TradingPlatform>,
        exit_logger: Arc<ExitAuditLogger>,
    ) -> Self {
        Self {
            trading_platform,
            exit_logger,
            trail_configs: HashMap::new(),
            active_trails: Arc::new(DashMap::new()),
            atr_cache: Arc::new(DashMap::new()),
        }
    }

    pub fn configure_symbol(&mut self, symbol: String, config: TrailingConfig) {
        self.trail_configs.insert(symbol, config);
    }

    pub async fn activate_trailing_stop(&self, position: &Position) -> Result<()> {
        let default_config = TrailingConfig::default();
        let config = self.trail_configs.get(&position.symbol)
            .unwrap_or(&default_config);

        // Check if position has enough profit to activate trailing
        let current_price = self.get_current_price(&position.symbol).await?;
        let entry_price = position.entry_price;
        let initial_stop = position.stop_loss.unwrap_or(0.0);

        let profit = match position.position_type {
            UnifiedPositionSide::Long => current_price - entry_price,
            UnifiedPositionSide::Short => entry_price - current_price,
        };

        if profit < config.activation_threshold {
            return Ok(()); // Not enough profit yet
        }

        // Calculate initial trailing stop level
        let atr = self.calculate_atr(&position.symbol, 14).await?;
        let trail_distance = (atr * config.atr_multiplier)
            .max(config.min_trail_distance)
            .min(config.max_trail_distance);

        let trail_level = match position.position_type {
            UnifiedPositionSide::Long => current_price - trail_distance,
            UnifiedPositionSide::Short => current_price + trail_distance,
        };

        let active_trail = ActiveTrail {
            position_id: position.id,
            trail_level,
            original_stop: initial_stop,
            position_type: position.position_type.clone(),
            last_updated: Utc::now(),
            update_count: 0,
            activation_price: current_price,
        };

        self.active_trails.insert(position.id, active_trail);

        info!(
            "Trailing stop activated for position {}: Trail level {} at price {}",
            position.id, trail_level, current_price
        );

        self.log_trail_activation(position.id, trail_level, current_price).await?;

        Ok(())
    }

    pub async fn update_trailing_stops(&self) -> Result<()> {
        if self.active_trails.is_empty() {
            return Ok(());
        }

        // Get all open positions that have active trails
        let open_positions = self.get_open_positions_with_trails().await?;

        for position in open_positions {
            if let Some(trail_ref) = self.active_trails.get(&position.id) {
                let trail = trail_ref.clone();
                drop(trail_ref); // Release the reference

                match self.calculate_new_trail_level(&position, &trail).await {
                    Ok(update) => {
                        if self.should_update_trail(&trail, &update) {
                            if let Err(e) = self.execute_trail_update(&position, update).await {
                                error!("Failed to execute trail update for position {}: {}", 
                                      position.id, e);
                            }
                        }
                    }
                    Err(e) => {
                        error!("Failed to calculate trail update for position {}: {}", 
                              position.id, e);
                    }
                }
            }
        }

        Ok(())
    }

    async fn calculate_new_trail_level(&self, position: &Position, current_trail: &ActiveTrail) -> Result<TrailUpdate> {
        let current_atr = self.calculate_atr(&position.symbol, 14).await?;
        let default_config = TrailingConfig::default();
        let config = self.trail_configs.get(&position.symbol)
            .unwrap_or(&default_config);

        let trail_distance = (current_atr * config.atr_multiplier)
            .max(config.min_trail_distance)
            .min(config.max_trail_distance);

        let current_price = self.get_current_price(&position.symbol).await?;

        let new_trail_level = match position.position_type {
            UnifiedPositionSide::Long => current_price - trail_distance,
            UnifiedPositionSide::Short => current_price + trail_distance,
        };

        Ok(TrailUpdate {
            position_id: position.id,
            old_level: current_trail.trail_level,
            new_level: new_trail_level,
            atr_used: current_atr,
            distance_pips: trail_distance * 10000.0, // Convert to pips
            trigger_price: current_price,
            update_reason: format!(
                "ATR-based trail: ATR={:.5}, Multiplier={}, Distance={:.1} pips",
                current_atr, config.atr_multiplier, trail_distance * 10000.0
            ),
        })
    }

    fn should_update_trail(&self, current: &ActiveTrail, update: &TrailUpdate) -> bool {
        let improvement = match current.position_type {
            UnifiedPositionSide::Long => update.new_level > current.trail_level,
            UnifiedPositionSide::Short => update.new_level < current.trail_level,
        };

        // Also check minimum movement threshold to avoid excessive updates
        let movement = (update.new_level - current.trail_level).abs();
        let min_movement = 0.0005; // 0.5 pips minimum movement

        improvement && movement >= min_movement
    }

    async fn execute_trail_update(&self, position: &Position, update: TrailUpdate) -> Result<()> {
        let modify_request = OrderModifyRequest {
            order_id: position.order_id.clone(),
            new_stop_loss: Some(update.new_level),
            new_take_profit: position.take_profit,
        };

        let result = self.trading_platform.modify_order(modify_request).await
            .context("Failed to modify order for trailing stop update")?;

        // Update active trail record
        if let Some(mut trail) = self.active_trails.get_mut(&position.id) {
            trail.trail_level = update.new_level;
            trail.last_updated = Utc::now();
            trail.update_count += 1;
        }

        self.log_trail_update(position.id, &update).await?;

        info!(
            "Trailing stop updated for position {}: {} -> {} ({})",
            position.id, update.old_level, update.new_level, update.update_reason
        );

        Ok(())
    }

    pub async fn deactivate_trailing_stop(&self, position_id: PositionId) -> Result<()> {
        if let Some((_, trail)) = self.active_trails.remove(&position_id) {
            self.log_trail_deactivation(position_id, trail.trail_level).await?;
            info!("Trailing stop deactivated for position {}", position_id);
        }
        Ok(())
    }

    async fn calculate_atr(&self, symbol: &str, period: u32) -> Result<f64> {
        // Check cache first
        if let Some(cached_atr) = self.atr_cache.get(symbol) {
            let cache_age = Utc::now() - cached_atr.calculation_time;
            if cache_age.num_seconds() < 300 { // 5 minutes cache
                return Ok(cached_atr.current_atr);
            }
        }

        // Calculate new ATR (this is a simplified implementation)
        // In a real system, you would fetch historical price data and calculate ATR properly
        let market_data = self.trading_platform.get_market_data(symbol).await?;
        
        // Simplified ATR calculation - using current spread as proxy
        // Real implementation should use True Range over specified period
        let atr = market_data.spread * 2.0; // Simplified calculation

        let atr_calc = ATRCalculation {
            symbol: symbol.to_string(),
            period,
            current_atr: atr,
            normalized_atr: atr / market_data.ask, // ATR as percentage of price
            calculation_time: Utc::now(),
        };

        self.atr_cache.insert(symbol.to_string(), atr_calc);

        Ok(atr)
    }

    async fn get_current_price(&self, symbol: &str) -> Result<f64> {
        let market_data = self.trading_platform.get_market_data(symbol).await?;
        Ok((market_data.bid + market_data.ask) / 2.0) // Mid price
    }

    async fn get_open_positions_with_trails(&self) -> Result<Vec<Position>> {
        let all_positions = self.trading_platform.get_positions().await?;
        
        // Filter to only positions with active trails
        let positions_with_trails: Vec<Position> = all_positions
            .into_iter()
            .filter(|pos| self.active_trails.contains_key(&pos.id))
            .collect();

        Ok(positions_with_trails)
    }

    async fn log_trail_activation(&self, position_id: PositionId, trail_level: f64, price: f64) -> Result<()> {
        let market_context = MarketContext {
            current_price: price,
            atr_14: self.calculate_atr(&"EURUSD", 14).await.unwrap_or(0.0), // Simplified
            trend_strength: 0.5, // Simplified
            volatility: 0.02, // Simplified
            spread: 0.0001, // Simplified
            timestamp: Utc::now(),
        };

        let modification = ExitModification {
            position_id,
            modification_type: ExitModificationType::TrailingStop,
            old_value: 0.0,
            new_value: trail_level,
            reasoning: "Trailing stop activated - sufficient profit reached".to_string(),
            market_context,
        };

        self.exit_logger.log_exit_modification(modification).await?;
        Ok(())
    }

    async fn log_trail_update(&self, position_id: PositionId, update: &TrailUpdate) -> Result<()> {
        let market_context = MarketContext {
            current_price: update.trigger_price,
            atr_14: update.atr_used,
            trend_strength: 0.5, // Simplified
            volatility: 0.02, // Simplified
            spread: 0.0001, // Simplified
            timestamp: Utc::now(),
        };

        let modification = ExitModification {
            position_id,
            modification_type: ExitModificationType::TrailingStop,
            old_value: update.old_level,
            new_value: update.new_level,
            reasoning: update.update_reason.clone(),
            market_context,
        };

        self.exit_logger.log_exit_modification(modification).await?;
        Ok(())
    }

    async fn log_trail_deactivation(&self, position_id: PositionId, final_level: f64) -> Result<()> {
        let market_context = MarketContext {
            current_price: 0.0, // Position closed
            atr_14: 0.0,
            trend_strength: 0.0,
            volatility: 0.0,
            spread: 0.0,
            timestamp: Utc::now(),
        };

        let modification = ExitModification {
            position_id,
            modification_type: ExitModificationType::TrailingStop,
            old_value: final_level,
            new_value: 0.0,
            reasoning: "Trailing stop deactivated - position closed".to_string(),
            market_context,
        };

        self.exit_logger.log_exit_modification(modification).await?;
        Ok(())
    }

    pub fn get_active_trails(&self) -> Vec<(PositionId, ActiveTrail)> {
        self.active_trails
            .iter()
            .map(|entry| (*entry.key(), entry.value().clone()))
            .collect()
    }

    pub fn get_trail_count(&self) -> usize {
        self.active_trails.len()
    }

    pub async fn get_trailing_performance_stats(&self) -> Result<TrailingStopStats> {
        // This would typically query from the audit database
        // For now, returning basic stats
        Ok(TrailingStopStats {
            total_trails: self.active_trails.len() as u32,
            successful_exits: 0, // Would be calculated from historical data
            average_trail_distance: 0.0, // Would be calculated from historical data
            profit_captured: rust_decimal::Decimal::ZERO,
            best_trail_profit: rust_decimal::Decimal::ZERO,
            worst_trail_loss: rust_decimal::Decimal::ZERO,
        })
    }
}