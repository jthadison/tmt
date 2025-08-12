use anyhow::{Context, Result};
use chrono::{DateTime, Duration, Utc};
use dashmap::DashSet;
use rust_decimal::Decimal;
use std::collections::HashMap;
use std::sync::Arc;
use tracing::{error, info, warn};

use super::exit_logger::ExitAuditLogger;
use super::types::*;
use super::TradingPlatform;

#[derive(Debug)]
pub struct BreakEvenManager {
    trading_platform: Arc<dyn TradingPlatform>,
    exit_logger: Arc<ExitAuditLogger>,
    break_even_configs: HashMap<String, BreakEvenConfig>,
    break_even_positions: Arc<DashSet<PositionId>>,
}

impl BreakEvenManager {
    pub fn new(
        trading_platform: Arc<dyn TradingPlatform>,
        exit_logger: Arc<ExitAuditLogger>,
    ) -> Self {
        Self {
            trading_platform,
            exit_logger,
            break_even_configs: HashMap::new(),
            break_even_positions: Arc::new(DashSet::new()),
        }
    }

    pub fn configure_symbol(&mut self, symbol: String, config: BreakEvenConfig) {
        self.break_even_configs.insert(symbol, config);
    }

    pub async fn check_break_even_triggers(&self) -> Result<()> {
        let open_positions = self.get_positions_without_breakeven().await?;

        for position in open_positions {
            if self.is_break_even_triggered(&position).await? {
                if let Err(e) = self.execute_break_even(&position).await {
                    error!(
                        "Failed to execute break-even for position {}: {}",
                        position.id, e
                    );
                }
            }
        }

        Ok(())
    }

    async fn is_break_even_triggered(&self, position: &Position) -> Result<bool> {
        let current_price = self.get_current_price(&position.symbol).await?;
        let entry_price = position.entry_price;
        let initial_stop = position.stop_loss.unwrap_or(0.0);

        if initial_stop == 0.0 {
            return Ok(false); // No stop loss set, can't calculate break-even
        }

        // Calculate current profit in pips
        let profit_pips = match position.position_type {
            UnifiedPositionSide::Long => (current_price - entry_price) * 10000.0,
            UnifiedPositionSide::Short => (entry_price - current_price) * 10000.0,
        };

        // Calculate initial risk in pips
        let risk_pips = match position.position_type {
            UnifiedPositionSide::Long => (entry_price - initial_stop) * 10000.0,
            UnifiedPositionSide::Short => (initial_stop - entry_price) * 10000.0,
        };

        if risk_pips <= 0.0 {
            return Ok(false); // Invalid risk calculation
        }

        let default_config = BreakEvenConfig::default();
        let config = self
            .break_even_configs
            .get(&position.symbol)
            .unwrap_or(&default_config);

        if !config.enabled {
            return Ok(false);
        }

        // Check if risk-reward threshold achieved
        let break_even_threshold = risk_pips * config.trigger_ratio;
        let triggered = profit_pips >= break_even_threshold;

        if triggered {
            info!(
                "Break-even triggered for position {}: Profit {:.1} pips >= Threshold {:.1} pips",
                position.id, profit_pips, break_even_threshold
            );
        }

        Ok(triggered)
    }

    async fn execute_break_even(&self, position: &Position) -> Result<()> {
        let default_config = BreakEvenConfig::default();
        let config = self
            .break_even_configs
            .get(&position.symbol)
            .unwrap_or(&default_config);

        // Calculate break-even level with buffer
        let buffer = config.break_even_buffer_pips / 10000.0; // Convert pips to price
        let break_even_level = match position.position_type {
            UnifiedPositionSide::Long => position.entry_price + buffer,
            UnifiedPositionSide::Short => position.entry_price - buffer,
        };

        let modify_request = OrderModifyRequest {
            order_id: position.order_id.clone(),
            new_stop_loss: Some(break_even_level),
            new_take_profit: position.take_profit,
        };

        let result = self
            .trading_platform
            .modify_order(modify_request)
            .await
            .context("Failed to modify order for break-even stop")?;

        // Mark position as having break-even stop
        self.break_even_positions.insert(position.id);

        // Log break-even activation
        self.log_break_even_activation(position, break_even_level)
            .await?;

        info!(
            "Break-even stop activated for position {}: {} -> {} (+{} pip buffer)",
            position.id,
            position.stop_loss.unwrap_or(0.0),
            break_even_level,
            config.break_even_buffer_pips
        );

        Ok(())
    }

    pub async fn force_break_even(&self, position_id: PositionId) -> Result<()> {
        let positions = self.trading_platform.get_positions().await?;

        if let Some(position) = positions.iter().find(|p| p.id == position_id) {
            self.execute_break_even(position).await?;
        } else {
            return Err(anyhow::anyhow!("Position {} not found", position_id));
        }

        Ok(())
    }

    pub fn is_break_even_active(&self, position_id: PositionId) -> bool {
        self.break_even_positions.contains(&position_id)
    }

    pub fn remove_break_even_tracking(&self, position_id: PositionId) {
        self.break_even_positions.remove(&position_id);
    }

    async fn get_positions_without_breakeven(&self) -> Result<Vec<Position>> {
        let all_positions = self.trading_platform.get_positions().await?;

        // Filter to positions that don't already have break-even activated
        let positions_without_breakeven: Vec<Position> = all_positions
            .into_iter()
            .filter(|pos| !self.break_even_positions.contains(&pos.id))
            .filter(|pos| pos.stop_loss.is_some()) // Must have a stop loss
            .collect();

        Ok(positions_without_breakeven)
    }

    async fn get_current_price(&self, symbol: &str) -> Result<f64> {
        let market_data = self.trading_platform.get_market_data(symbol).await?;
        Ok((market_data.bid + market_data.ask) / 2.0)
    }

    async fn log_break_even_activation(
        &self,
        position: &Position,
        break_even_level: f64,
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
            modification_type: ExitModificationType::BreakEven,
            old_value: position.stop_loss.unwrap_or(0.0),
            new_value: break_even_level,
            reasoning: format!(
                "Break-even stop activated at 1:1 R:R with {} pip buffer",
                self.break_even_configs
                    .get(&position.symbol)
                    .unwrap_or(&BreakEvenConfig::default())
                    .break_even_buffer_pips
            ),
            market_context,
        };

        self.exit_logger.log_exit_modification(modification).await?;
        Ok(())
    }

    pub async fn get_break_even_stats(&self) -> Result<BreakEvenStats> {
        // This would typically query from historical data
        // For now, returning basic stats
        Ok(BreakEvenStats {
            break_even_activations: self.break_even_positions.len() as u32,
            successful_break_evens: 0, // Would be calculated from historical data
            losses_prevented: Decimal::ZERO,
            average_time_to_break_even: Duration::from_std(std::time::Duration::from_secs(
                2 * 3600,
            ))
            .unwrap(),
        })
    }

    pub fn get_break_even_positions(&self) -> Vec<PositionId> {
        self.break_even_positions.iter().map(|id| *id).collect()
    }

    pub fn get_break_even_count(&self) -> usize {
        self.break_even_positions.len()
    }

    pub async fn validate_break_even_logic(
        &self,
        position: &Position,
    ) -> Result<BreakEvenValidation> {
        let current_price = self.get_current_price(&position.symbol).await?;
        let entry_price = position.entry_price;
        let stop_loss = position.stop_loss.unwrap_or(0.0);

        if stop_loss == 0.0 {
            return Ok(BreakEvenValidation {
                is_valid: false,
                reason: "No stop loss set".to_string(),
                current_profit_pips: 0.0,
                required_profit_pips: 0.0,
                risk_reward_ratio: 0.0,
            });
        }

        let profit_pips = match position.position_type {
            UnifiedPositionSide::Long => (current_price - entry_price) * 10000.0,
            UnifiedPositionSide::Short => (entry_price - current_price) * 10000.0,
        };

        let risk_pips = match position.position_type {
            UnifiedPositionSide::Long => (entry_price - stop_loss) * 10000.0,
            UnifiedPositionSide::Short => (stop_loss - entry_price) * 10000.0,
        };

        let default_config = BreakEvenConfig::default();
        let config = self
            .break_even_configs
            .get(&position.symbol)
            .unwrap_or(&default_config);

        let required_profit_pips = risk_pips * config.trigger_ratio;
        let current_rr = if risk_pips > 0.0 {
            profit_pips / risk_pips
        } else {
            0.0
        };

        Ok(BreakEvenValidation {
            is_valid: profit_pips >= required_profit_pips,
            reason: if profit_pips >= required_profit_pips {
                "Break-even criteria met".to_string()
            } else {
                format!(
                    "Need {:.1} more pips profit",
                    required_profit_pips - profit_pips
                )
            },
            current_profit_pips: profit_pips,
            required_profit_pips,
            risk_reward_ratio: current_rr,
        })
    }
}

#[derive(Debug, Clone)]
pub struct BreakEvenValidation {
    pub is_valid: bool,
    pub reason: String,
    pub current_profit_pips: f64,
    pub required_profit_pips: f64,
    pub risk_reward_ratio: f64,
}
