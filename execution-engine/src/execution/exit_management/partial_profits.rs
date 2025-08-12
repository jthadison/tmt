use std::collections::HashMap;
use std::sync::Arc;
use dashmap::DashMap;
use anyhow::{Result, Context};
use chrono::{DateTime, Utc};
use tracing::{info, warn, error};
use rust_decimal::Decimal;

use super::TradingPlatform;
use super::types::*;
use super::exit_logger::ExitAuditLogger;

#[derive(Debug, Clone)]
pub struct PositionTargetStatus {
    pub position_id: PositionId,
    pub targets_hit: Vec<u32>, // Which target levels have been hit
    pub remaining_volume: Decimal,
    pub total_partial_profit: Decimal,
    pub last_target_hit: Option<DateTime<Utc>>,
}

#[derive(Debug)]
pub struct PartialProfitManager {
    trading_platform: Arc<dyn TradingPlatform>,
    exit_logger: Arc<ExitAuditLogger>,
    profit_configs: HashMap<String, ProfitTakingConfig>,
    position_targets: Arc<DashMap<PositionId, PositionTargetStatus>>,
}

impl PartialProfitManager {
    pub fn new(
        trading_platform: Arc<dyn TradingPlatform>,
        exit_logger: Arc<ExitAuditLogger>,
    ) -> Self {
        Self {
            trading_platform,
            exit_logger,
            profit_configs: HashMap::new(),
            position_targets: Arc::new(DashMap::new()),
        }
    }

    pub fn configure_symbol(&mut self, symbol: String, config: ProfitTakingConfig) {
        self.profit_configs.insert(symbol, config);
    }

    pub async fn check_profit_targets(&self) -> Result<()> {
        let positions_with_targets = self.get_positions_with_remaining_targets().await?;

        for position in positions_with_targets {
            let targets_hit = match self.evaluate_profit_targets(&position).await {
                Ok(targets) => targets,
                Err(e) => {
                    error!("Failed to evaluate profit targets for position {}: {}", position.id, e);
                    continue;
                }
            };

            for target in targets_hit {
                if let Err(e) = self.execute_partial_close(&position, &target).await {
                    error!("Failed to execute partial close for position {}: {}", position.id, e);
                }
            }
        }

        Ok(())
    }

    async fn evaluate_profit_targets(&self, position: &Position) -> Result<Vec<ProfitTarget>> {
        let current_price = self.get_current_price(&position.symbol).await?;
        let entry_price = position.entry_price;
        let initial_stop = position.stop_loss.unwrap_or(0.0);

        if initial_stop == 0.0 {
            return Ok(Vec::new()); // Can't calculate R:R without stop loss
        }

        // Calculate current risk-reward ratio
        let current_rr = self.calculate_risk_reward_ratio(
            entry_price,
            current_price,
            initial_stop,
            &position.position_type
        );

        let default_config = ProfitTakingConfig::default();
        let config = self.profit_configs.get(&position.symbol)
            .unwrap_or(&default_config);

        if !config.enabled {
            return Ok(Vec::new());
        }

        let mut targets_hit = Vec::new();

        // Get current position status
        let position_status = self.position_targets.get(&position.id);
        let already_hit: Vec<u32> = match position_status {
            Some(status) => status.targets_hit.clone(),
            None => {
                // Initialize position target tracking
                let initial_status = PositionTargetStatus {
                    position_id: position.id,
                    targets_hit: Vec::new(),
                    remaining_volume: position.volume,
                    total_partial_profit: Decimal::ZERO,
                    last_target_hit: None,
                };
                self.position_targets.insert(position.id, initial_status);
                Vec::new()
            }
        };

        // Check each profit target
        for target in &config.profit_targets {
            if current_rr >= target.risk_reward_ratio && !already_hit.contains(&target.level) {
                targets_hit.push(target.clone());
                info!(
                    "Profit target {} hit for position {}: R:R {:.2} >= {:.2}",
                    target.level, position.id, current_rr, target.risk_reward_ratio
                );
            }
        }

        Ok(targets_hit)
    }

    async fn execute_partial_close(&self, position: &Position, target: &ProfitTarget) -> Result<()> {
        // Get current remaining volume
        let current_volume = match self.position_targets.get(&position.id) {
            Some(status) => status.remaining_volume,
            None => position.volume,
        };

        // Calculate volume to close
        let close_volume = current_volume * Decimal::from_f64_retain(target.close_percentage).unwrap();
        let min_volume = Decimal::from_f64_retain(self.get_minimum_volume(&position.symbol).await?).unwrap();

        // Validate minimum volume requirements
        if close_volume < min_volume {
            warn!(
                "Partial close volume {:.4} too small for position {}, minimum {:.4}",
                close_volume, position.id, min_volume
            );
            return Ok(());
        }

        // Execute partial close
        let close_request = PartialCloseRequest {
            position_id: position.id,
            volume: close_volume,
            reason: format!("Partial profit taking at {} R:R", target.risk_reward_ratio),
        };

        let close_result = self.trading_platform.close_position_partial(close_request).await
            .context("Failed to execute partial close")?;

        // Calculate profit for this partial close
        let profit_per_unit = match position.position_type {
            UnifiedPositionSide::Long => close_result.close_price - position.entry_price,
            UnifiedPositionSide::Short => position.entry_price - close_result.close_price,
        };

        let partial_profit = Decimal::from_f64_retain(profit_per_unit).unwrap() * close_volume;

        // Update position tracking
        self.update_position_target_status(position.id, target, close_volume, partial_profit).await?;

        // Log partial profit taking
        self.log_partial_profit_taking(position, target, close_volume, close_result.close_price, partial_profit).await?;

        info!(
            "Partial profit taken for position {}: {:.1}% at {:.2} R:R (Volume: {:.4}, Profit: {:.2})",
            position.id,
            target.close_percentage * 100.0,
            target.risk_reward_ratio,
            close_volume,
            partial_profit
        );

        Ok(())
    }

    async fn update_position_target_status(
        &self,
        position_id: PositionId,
        target: &ProfitTarget,
        closed_volume: Decimal,
        profit: Decimal,
    ) -> Result<()> {
        if let Some(mut status) = self.position_targets.get_mut(&position_id) {
            status.targets_hit.push(target.level);
            status.remaining_volume -= closed_volume;
            status.total_partial_profit += profit;
            status.last_target_hit = Some(Utc::now());
        }
        Ok(())
    }

    fn calculate_risk_reward_ratio(
        &self,
        entry_price: f64,
        current_price: f64,
        stop_loss: f64,
        position_type: &UnifiedPositionSide,
    ) -> f64 {
        let profit = match position_type {
            UnifiedPositionSide::Long => current_price - entry_price,
            UnifiedPositionSide::Short => entry_price - current_price,
        };

        let risk = match position_type {
            UnifiedPositionSide::Long => entry_price - stop_loss,
            UnifiedPositionSide::Short => stop_loss - entry_price,
        };

        if risk > 0.0 {
            profit / risk
        } else {
            0.0
        }
    }

    async fn get_positions_with_remaining_targets(&self) -> Result<Vec<Position>> {
        let all_positions = self.trading_platform.get_positions().await?;
        
        // Filter to positions that still have profit targets to hit
        let positions_with_targets: Vec<Position> = all_positions
            .into_iter()
            .filter(|pos| {
                if let Some(config) = self.profit_configs.get(&pos.symbol) {
                    if !config.enabled {
                        return false;
                    }
                    
                    let status = self.position_targets.get(&pos.id);
                    let targets_hit = match status {
                        Some(ref s) => &s.targets_hit,
                        None => return true, // No targets hit yet
                    };
                    
                    // Check if there are remaining targets
                    config.profit_targets.iter().any(|target| !targets_hit.contains(&target.level))
                } else {
                    false
                }
            })
            .collect();

        Ok(positions_with_targets)
    }

    async fn get_current_price(&self, symbol: &str) -> Result<f64> {
        let market_data = self.trading_platform.get_market_data(symbol).await?;
        Ok((market_data.bid + market_data.ask) / 2.0)
    }

    async fn get_minimum_volume(&self, symbol: &str) -> Result<f64> {
        // This would typically come from broker specifications
        // For now, using a standard minimum
        Ok(0.01) // 0.01 lots
    }

    async fn log_partial_profit_taking(
        &self,
        position: &Position,
        target: &ProfitTarget,
        volume: Decimal,
        close_price: f64,
        profit: Decimal,
    ) -> Result<()> {
        let current_price = self.get_current_price(&position.symbol).await?;
        
        let market_context = MarketContext {
            current_price,
            atr_14: 0.0015, // Simplified
            trend_strength: 0.5,
            volatility: 0.02,
            spread: 0.0001,
            timestamp: Utc::now(),
        };

        let modification = ExitModification {
            position_id: position.id,
            modification_type: ExitModificationType::PartialProfit,
            old_value: f64::try_from(position.volume).unwrap_or(0.0),
            new_value: f64::try_from(volume).unwrap_or(0.0),
            reasoning: format!(
                "Partial profit taking: {}% at {:.2} R:R, Volume: {:.4}, Profit: {:.2}",
                target.close_percentage * 100.0,
                target.risk_reward_ratio,
                volume,
                profit
            ),
            market_context,
        };

        self.exit_logger.log_exit_modification(modification).await?;
        Ok(())
    }

    pub fn get_position_target_status(&self, position_id: PositionId) -> Option<PositionTargetStatus> {
        self.position_targets.get(&position_id).map(|s| s.clone())
    }

    pub fn remove_position_tracking(&self, position_id: PositionId) {
        self.position_targets.remove(&position_id);
    }

    pub async fn get_partial_profit_stats(&self) -> Result<PartialProfitStats> {
        let mut total_partials = 0u32;
        let mut total_volume_closed = Decimal::ZERO;
        let mut total_profit = Decimal::ZERO;
        let mut target_hits: HashMap<u32, u32> = HashMap::new();

        for status_ref in self.position_targets.iter() {
            let status = status_ref.value();
            total_partials += status.targets_hit.len() as u32;
            total_profit += status.total_partial_profit;
            
            let original_volume = status.remaining_volume + 
                (status.total_partial_profit / Decimal::from_f64_retain(1.0).unwrap()); // Simplified
            let volume_closed = original_volume - status.remaining_volume;
            total_volume_closed += volume_closed;
            
            for &target_level in &status.targets_hit {
                *target_hits.entry(target_level).or_insert(0) += 1;
            }
        }

        let average_profit = if total_partials > 0 {
            total_profit / Decimal::from(total_partials)
        } else {
            Decimal::ZERO
        };

        // Calculate hit rates
        let target_hit_rates: HashMap<u32, f64> = target_hits
            .into_iter()
            .map(|(level, hits)| {
                let total_opportunities = self.position_targets.len() as u32;
                let hit_rate = if total_opportunities > 0 {
                    hits as f64 / total_opportunities as f64
                } else {
                    0.0
                };
                (level, hit_rate)
            })
            .collect();

        Ok(PartialProfitStats {
            total_partials,
            total_volume_closed,
            average_profit_per_partial: average_profit,
            target_hit_rates: target_hit_rates,
        })
    }

    pub fn get_tracked_positions_count(&self) -> usize {
        self.position_targets.len()
    }

    pub async fn validate_partial_profit_logic(&self, position: &Position) -> Result<PartialProfitValidation> {
        let current_price = self.get_current_price(&position.symbol).await?;
        let default_config = ProfitTakingConfig::default();
        let config = self.profit_configs.get(&position.symbol)
            .unwrap_or(&default_config);
        
        let mut validation = PartialProfitValidation {
            is_enabled: config.enabled,
            current_risk_reward: 0.0,
            available_targets: Vec::new(),
            targets_already_hit: Vec::new(),
        };

        if let Some(stop_loss) = position.stop_loss {
            validation.current_risk_reward = self.calculate_risk_reward_ratio(
                position.entry_price,
                current_price,
                stop_loss,
                &position.position_type
            );

            let status = self.position_targets.get(&position.id);
            let targets_hit = match status {
                Some(ref s) => s.targets_hit.clone(),
                None => Vec::new(),
            };

            for target in &config.profit_targets {
                if targets_hit.contains(&target.level) {
                    validation.targets_already_hit.push(target.clone());
                } else if validation.current_risk_reward >= target.risk_reward_ratio {
                    validation.available_targets.push(target.clone());
                }
            }
        }

        Ok(validation)
    }
}

#[derive(Debug, Clone)]
pub struct PartialProfitValidation {
    pub is_enabled: bool,
    pub current_risk_reward: f64,
    pub available_targets: Vec<ProfitTarget>,
    pub targets_already_hit: Vec<ProfitTarget>,
}