use std::collections::HashMap;
use std::sync::Arc;
use dashmap::DashSet;
use anyhow::{Result, Context};
use chrono::{DateTime, Utc, Duration};
use tracing::{info, warn, error};
use rust_decimal::Decimal;

use super::TradingPlatform;
use super::types::*;
use super::exit_logger::ExitAuditLogger;

#[derive(Debug)]
pub struct TimeBasedExitManager {
    trading_platform: Arc<dyn TradingPlatform>,
    exit_logger: Arc<ExitAuditLogger>,
    time_configs: HashMap<String, TimeExitConfig>,
    warned_positions: Arc<DashSet<PositionId>>,
}

impl TimeBasedExitManager {
    pub fn new(
        trading_platform: Arc<dyn TradingPlatform>,
        exit_logger: Arc<ExitAuditLogger>,
    ) -> Self {
        Self {
            trading_platform,
            exit_logger,
            time_configs: HashMap::new(),
            warned_positions: Arc::new(DashSet::new()),
        }
    }

    pub fn configure_symbol(&mut self, symbol: String, config: TimeExitConfig) {
        self.time_configs.insert(symbol, config);
    }

    pub async fn check_time_based_exits(&self) -> Result<()> {
        let aged_positions = self.get_aged_positions().await?;

        for position in aged_positions {
            match self.should_exit_on_time(&position).await {
                Ok(should_exit) => {
                    if should_exit {
                        if let Err(e) = self.execute_time_based_exit(&position).await {
                            error!("Failed to execute time-based exit for position {}: {}", position.id, e);
                        }
                    }
                }
                Err(e) => {
                    error!("Error checking time exit for position {}: {}", position.id, e);
                }
            }
        }

        Ok(())
    }

    async fn should_exit_on_time(&self, position: &Position) -> Result<bool> {
        let position_age = Utc::now() - position.open_time;
        let default_config = TimeExitConfig::default();
        let config = self.time_configs.get(&position.symbol)
            .unwrap_or(&default_config);

        if !config.enabled {
            return Ok(false);
        }

        // Check warning threshold first
        if position_age > config.warning_duration && !self.warned_positions.contains(&position.id) {
            self.send_time_warning(position, &config).await?;
            self.warned_positions.insert(position.id);
        }

        // Check if maximum hold time exceeded
        if position_age <= config.max_hold_duration {
            return Ok(false);
        }

        // Check for trend strength override
        if position.unrealized_pnl > 0.0 {
            let market_conditions = self.analyze_market_conditions(&position.symbol).await?;
            
            if market_conditions.trend_strength > config.trend_strength_override_threshold {
                info!(
                    "Time exit overridden for position {} due to strong trend (strength: {:.2}, profit: {:.2})",
                    position.id, market_conditions.trend_strength, position.unrealized_pnl
                );
                return Ok(false);
            }
        }

        info!(
            "Time-based exit triggered for position {}: Age {} hours > Max {} hours",
            position.id,
            position_age.num_hours(),
            config.max_hold_duration.num_hours()
        );

        Ok(true)
    }

    async fn execute_time_based_exit(&self, position: &Position) -> Result<()> {
        let close_request = ClosePositionRequest {
            position_id: position.id,
            reason: format!(
                "Time-based exit: Position held for {} hours",
                (Utc::now() - position.open_time).num_hours()
            ),
        };

        let close_result = self.trading_platform.close_position(close_request).await
            .context("Failed to close position for time-based exit")?;

        // Remove from warned positions
        self.warned_positions.remove(&position.id);

        // Log time-based exit
        self.log_time_based_exit(position, close_result.close_price).await?;

        info!(
            "Time-based exit executed for position {}: Age {} hours, Exit price: {}, P&L: {:.2}",
            position.id,
            (Utc::now() - position.open_time).num_hours(),
            close_result.close_price,
            close_result.realized_pnl.unwrap_or(Decimal::ZERO)
        );

        Ok(())
    }

    async fn send_time_warning(&self, position: &Position, config: &TimeExitConfig) -> Result<()> {
        let position_age = Utc::now() - position.open_time;
        let remaining_time = config.max_hold_duration - position_age;

        warn!(
            "Position {} approaching time exit: {} hours remaining (Age: {} hours, Max: {} hours)",
            position.id,
            remaining_time.num_hours(),
            position_age.num_hours(),
            config.max_hold_duration.num_hours()
        );

        // Log the warning
        self.log_time_warning(position, remaining_time).await?;

        Ok(())
    }

    pub async fn force_time_exit(&self, position_id: PositionId, reason: String) -> Result<()> {
        let positions = self.trading_platform.get_positions().await?;
        
        if let Some(position) = positions.iter().find(|p| p.id == position_id) {
            let close_request = ClosePositionRequest {
                position_id,
                reason: format!("Forced time exit: {}", reason),
            };

            let close_result = self.trading_platform.close_position(close_request).await?;
            
            self.log_forced_time_exit(position, &reason, close_result.close_price).await?;
            
            info!("Forced time exit executed for position {}: {}", position_id, reason);
        } else {
            return Err(anyhow::anyhow!("Position {} not found", position_id));
        }

        Ok(())
    }

    async fn get_aged_positions(&self) -> Result<Vec<Position>> {
        let all_positions = self.trading_platform.get_positions().await?;
        let now = Utc::now();
        
        // Filter positions based on their age and time exit configuration
        let aged_positions: Vec<Position> = all_positions
            .into_iter()
            .filter(|pos| {
                if let Some(config) = self.time_configs.get(&pos.symbol) {
                    if !config.enabled {
                        return false;
                    }
                    let position_age = now - pos.open_time;
                    position_age > config.warning_duration
                } else {
                    // Use default config if no specific config exists
                    let default_config = TimeExitConfig::default();
                    if !default_config.enabled {
                        return false;
                    }
                    let position_age = now - pos.open_time;
                    position_age > default_config.warning_duration
                }
            })
            .collect();

        Ok(aged_positions)
    }

    async fn analyze_market_conditions(&self, symbol: &str) -> Result<MarketConditions> {
        // Simplified market condition analysis
        // In a real implementation, this would analyze:
        // - Trend indicators (ADX, moving averages)
        // - Momentum (RSI, MACD)
        // - Volume analysis
        // - Support/resistance levels

        let market_data = self.trading_platform.get_market_data(symbol).await?;
        
        // Simplified calculation - would need real technical analysis
        let price_change = market_data.ask - market_data.bid; // Simplified
        let trend_strength = (price_change.abs() / market_data.ask).min(1.0);
        
        Ok(MarketConditions {
            symbol: symbol.to_string(),
            trend_strength,
            volatility: 0.02, // Simplified
            volume_profile: 1.0, // Simplified
            support_resistance_levels: vec![market_data.bid - 0.01, market_data.ask + 0.01], // Simplified
            analysis_time: Utc::now(),
        })
    }

    async fn log_time_based_exit(&self, position: &Position, exit_price: f64) -> Result<()> {
        let market_context = MarketContext {
            current_price: exit_price,
            atr_14: 0.0015, // Simplified
            trend_strength: 0.3, // Time exit suggests weak trend
            volatility: 0.02,
            spread: 0.0001,
            timestamp: Utc::now(),
        };

        let modification = ExitModification {
            position_id: position.id,
            modification_type: ExitModificationType::TimeExit,
            old_value: position.entry_price,
            new_value: exit_price,
            reasoning: format!(
                "Time-based exit after {} hours (max {} hours configured)",
                (Utc::now() - position.open_time).num_hours(),
                self.time_configs.get(&position.symbol)
                    .unwrap_or(&TimeExitConfig::default())
                    .max_hold_duration.num_hours()
            ),
            market_context,
        };

        self.exit_logger.log_exit_modification(modification).await?;
        Ok(())
    }

    async fn log_time_warning(&self, position: &Position, remaining_time: Duration) -> Result<()> {
        let current_price = (self.trading_platform.get_market_data(&position.symbol).await?).ask;
        
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
            modification_type: ExitModificationType::TimeExit,
            old_value: 0.0,
            new_value: remaining_time.num_hours() as f64,
            reasoning: format!(
                "Time exit warning: {} hours remaining before automatic close",
                remaining_time.num_hours()
            ),
            market_context,
        };

        self.exit_logger.log_exit_modification(modification).await?;
        Ok(())
    }

    async fn log_forced_time_exit(&self, position: &Position, reason: &str, exit_price: f64) -> Result<()> {
        let market_context = MarketContext {
            current_price: exit_price,
            atr_14: 0.0015, // Simplified
            trend_strength: 0.0, // Forced exit
            volatility: 0.02,
            spread: 0.0001,
            timestamp: Utc::now(),
        };

        let modification = ExitModification {
            position_id: position.id,
            modification_type: ExitModificationType::TimeExit,
            old_value: position.entry_price,
            new_value: exit_price,
            reasoning: format!("Forced time exit: {}", reason),
            market_context,
        };

        self.exit_logger.log_exit_modification(modification).await?;
        Ok(())
    }

    pub fn remove_warning_tracking(&self, position_id: PositionId) {
        self.warned_positions.remove(&position_id);
    }

    pub fn is_position_warned(&self, position_id: PositionId) -> bool {
        self.warned_positions.contains(&position_id)
    }

    pub fn get_warned_positions_count(&self) -> usize {
        self.warned_positions.len()
    }

    pub async fn get_time_exit_stats(&self) -> Result<TimeExitStats> {
        // This would typically query historical data
        // For now, returning basic stats
        Ok(TimeExitStats {
            time_exits_triggered: 0, // Would be from historical data
            average_hold_time: Duration::from_std(std::time::Duration::from_secs(12 * 3600)).unwrap(),
            trend_overrides: 0, // Would be from historical data
            time_exit_pnl: Decimal::ZERO,
        })
    }

    pub async fn validate_time_exit_config(&self, symbol: &str) -> Result<TimeExitConfigValidation> {
        let default_config = TimeExitConfig::default();
        let config = self.time_configs.get(symbol)
            .unwrap_or(&default_config);

        let mut validation = TimeExitConfigValidation {
            is_valid: true,
            warnings: Vec::new(),
            max_hold_hours: config.max_hold_duration.num_hours(),
            warning_hours: config.warning_duration.num_hours(),
            enabled: config.enabled,
        };

        if config.max_hold_duration <= config.warning_duration {
            validation.is_valid = false;
            validation.warnings.push("Max hold duration must be greater than warning duration".to_string());
        }

        if config.max_hold_duration.num_hours() < 1 {
            validation.warnings.push("Very short max hold time may cause excessive exits".to_string());
        }

        if config.trend_strength_override_threshold > 1.0 || config.trend_strength_override_threshold < 0.0 {
            validation.warnings.push("Trend strength override threshold should be between 0.0 and 1.0".to_string());
        }

        Ok(validation)
    }

    pub async fn get_position_time_analysis(&self, position_id: PositionId) -> Result<Option<PositionTimeAnalysis>> {
        let positions = self.trading_platform.get_positions().await?;
        
        if let Some(position) = positions.iter().find(|p| p.id == position_id) {
            let default_config = TimeExitConfig::default();
            let config = self.time_configs.get(&position.symbol)
                .unwrap_or(&default_config);

            let position_age = Utc::now() - position.open_time;
            let remaining_time = config.max_hold_duration - position_age;
            let market_conditions = self.analyze_market_conditions(&position.symbol).await?;

            let analysis = PositionTimeAnalysis {
                position_id,
                current_age_hours: position_age.num_hours(),
                max_hold_hours: config.max_hold_duration.num_hours(),
                warning_threshold_hours: config.warning_duration.num_hours(),
                remaining_hours: remaining_time.num_hours(),
                is_warned: self.warned_positions.contains(&position_id),
                trend_strength: market_conditions.trend_strength,
                will_override_time_exit: position.unrealized_pnl > 0.0 && 
                    market_conditions.trend_strength > config.trend_strength_override_threshold,
                exit_probability: self.calculate_exit_probability(&position, &config, &market_conditions),
            };

            Ok(Some(analysis))
        } else {
            Ok(None)
        }
    }

    fn calculate_exit_probability(&self, position: &Position, config: &TimeExitConfig, market_conditions: &MarketConditions) -> f64 {
        let position_age = Utc::now() - position.open_time;
        let age_factor = position_age.num_seconds() as f64 / config.max_hold_duration.num_seconds() as f64;
        
        // Base probability increases with age
        let mut probability = age_factor.min(1.0);
        
        // Reduce probability if trend is strong and position is profitable
        if position.unrealized_pnl > 0.0 && market_conditions.trend_strength > config.trend_strength_override_threshold {
            probability *= 0.2; // Significantly reduce probability
        }
        
        probability.max(0.0).min(1.0)
    }
}

#[derive(Debug, Clone)]
pub struct TimeExitConfigValidation {
    pub is_valid: bool,
    pub warnings: Vec<String>,
    pub max_hold_hours: i64,
    pub warning_hours: i64,
    pub enabled: bool,
}

#[derive(Debug, Clone)]
pub struct PositionTimeAnalysis {
    pub position_id: PositionId,
    pub current_age_hours: i64,
    pub max_hold_hours: i64,
    pub warning_threshold_hours: i64,
    pub remaining_hours: i64,
    pub is_warned: bool,
    pub trend_strength: f64,
    pub will_override_time_exit: bool,
    pub exit_probability: f64,
}