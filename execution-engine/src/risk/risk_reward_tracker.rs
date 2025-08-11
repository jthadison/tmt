use crate::risk::types::*;
use crate::risk::pnl_calculator::PositionTracker;
use anyhow::Result;
use chrono::{DateTime, Utc};
use dashmap::DashMap;
use rust_decimal::Decimal;
use rust_decimal_macros::dec;
use std::sync::Arc;
use tracing::{error, info, warn};

pub struct RiskRewardTracker {
    position_tracker: Arc<PositionTracker>,
    market_data: Arc<MarketDataProvider>,
    rr_cache: Arc<DashMap<PositionId, RiskRewardMetrics>>,
    alert_manager: Arc<RiskRewardAlertManager>,
}

impl RiskRewardTracker {
    pub fn new(
        position_tracker: Arc<PositionTracker>,
        market_data: Arc<MarketDataProvider>,
        alert_manager: Arc<RiskRewardAlertManager>,
    ) -> Self {
        Self {
            position_tracker,
            market_data,
            rr_cache: Arc::new(DashMap::new()),
            alert_manager,
        }
    }
    
    pub async fn calculate_risk_reward(&self, position: &Position) -> Result<RiskRewardMetrics> {
        let current_price = self.market_data.get_current_price(&position.symbol).await?;
        
        let distance_to_stop = if let Some(stop_loss) = position.stop_loss {
            match position.position_type {
                PositionType::Long => position.entry_price - stop_loss,
                PositionType::Short => stop_loss - position.entry_price,
            }
        } else {
            position.entry_price * dec!(0.02)
        };
        
        let distance_to_target = if let Some(take_profit) = position.take_profit {
            match position.position_type {
                PositionType::Long => take_profit - position.entry_price,
                PositionType::Short => position.entry_price - take_profit,
            }
        } else {
            position.entry_price * dec!(0.04)
        };
        
        let current_rr_ratio = if distance_to_stop != dec!(0) {
            distance_to_target / distance_to_stop
        } else {
            dec!(0)
        };
        
        let distance_from_entry = match position.position_type {
            PositionType::Long => current_price - position.entry_price,
            PositionType::Short => position.entry_price - current_price,
        };
        
        let performance_score = self.calculate_performance_score(
            position,
            current_price,
            distance_from_entry,
        ).await?;
        
        let recommendation = self.generate_recommendation(
            position,
            current_price,
            &current_rr_ratio,
            distance_from_entry,
        ).await?;
        
        let metrics = RiskRewardMetrics {
            position_id: position.id,
            current_rr_ratio,
            max_favorable_excursion: position.max_favorable_excursion,
            max_adverse_excursion: position.max_adverse_excursion,
            distance_to_stop,
            distance_to_target,
            performance_score,
            recommendation,
        };
        
        self.rr_cache.insert(position.id, metrics.clone());
        
        self.check_rr_alerts(position, &metrics).await?;
        
        Ok(metrics)
    }
    
    async fn calculate_performance_score(
        &self,
        position: &Position,
        _current_price: Decimal,
        distance_from_entry: Decimal,
    ) -> Result<Decimal> {
        let time_in_trade = Utc::now() - position.opened_at;
        let hours_in_trade = Decimal::from(time_in_trade.num_hours().max(1));
        
        let price_progress = if position.take_profit.is_some() && position.stop_loss.is_some() {
            let total_distance = match position.position_type {
                PositionType::Long => {
                    position.take_profit.unwrap() - position.stop_loss.unwrap()
                },
                PositionType::Short => {
                    position.stop_loss.unwrap() - position.take_profit.unwrap()
                }
            };
            
            if total_distance != dec!(0) {
                distance_from_entry / total_distance * dec!(100)
            } else {
                dec!(0)
            }
        } else {
            dec!(0)
        };
        
        let mfe_score = if position.max_favorable_excursion != dec!(0) {
            let current_pnl = distance_from_entry * position.size;
            (current_pnl / position.max_favorable_excursion) * dec!(100)
        } else {
            dec!(50)
        };
        
        let mae_penalty = if position.max_adverse_excursion < dec!(0) {
            let mae_ratio = position.max_adverse_excursion.abs() / (position.entry_price * position.size);
            if mae_ratio > dec!(0.02) {
                dec!(20)
            } else {
                dec!(0)
            }
        } else {
            dec!(0)
        };
        
        let time_decay_factor = if hours_in_trade > dec!(24) {
            dec!(90) / (dec!(1) + hours_in_trade / dec!(24))
        } else {
            dec!(100)
        };
        
        let base_score = (price_progress + mfe_score) / dec!(2);
        let adjusted_score = (base_score - mae_penalty) * time_decay_factor / dec!(100);
        
        Ok(adjusted_score.min(dec!(100)).max(dec!(0)))
    }
    
    async fn generate_recommendation(
        &self,
        position: &Position,
        _current_price: Decimal,
        rr_ratio: &Decimal,
        distance_from_entry: Decimal,
    ) -> Result<Option<String>> {
        let mut recommendations: Vec<String> = Vec::new();
        
        if *rr_ratio < dec!(1) && position.take_profit.is_some() {
            recommendations.push("Poor R:R ratio - consider adjusting targets".to_string());
        }
        
        if distance_from_entry > dec!(0) {
            let profit_percentage = (distance_from_entry / position.entry_price) * dec!(100);
            
            if profit_percentage > dec!(1) && position.stop_loss.is_some() {
                let new_stop = match position.position_type {
                    PositionType::Long => position.entry_price,
                    PositionType::Short => position.entry_price,
                };
                
                if match position.position_type {
                    PositionType::Long => new_stop > position.stop_loss.unwrap(),
                    PositionType::Short => new_stop < position.stop_loss.unwrap(),
                } {
                    recommendations.push(format!(
                        "Move stop to breakeven at {:.5}",
                        new_stop
                    ));
                }
            }
            
            if profit_percentage > dec!(2) {
                recommendations.push("Consider taking partial profits".to_string());
            }
            
            if position.max_favorable_excursion > dec!(0) {
                let retracement = dec!(1) - (distance_from_entry * position.size / position.max_favorable_excursion);
                if retracement > dec!(0.5) {
                    recommendations.push("Position retracing significantly from MFE".to_string());
                }
            }
        } else if distance_from_entry < dec!(0) {
            let loss_percentage = (distance_from_entry.abs() / position.entry_price) * dec!(100);
            
            if loss_percentage > dec!(1.5) && position.stop_loss.is_none() {
                recommendations.push("Add stop loss to limit risk".to_string());
            }
            
            if position.max_adverse_excursion < distance_from_entry * position.size {
                recommendations.push("Position at new MAE - monitor closely".to_string());
            }
        }
        
        let time_in_trade = Utc::now() - position.opened_at;
        if time_in_trade.num_hours() > 48 && distance_from_entry.abs() < position.entry_price * dec!(0.001) {
            recommendations.push("Position stagnant - consider closing".to_string());
        }
        
        if recommendations.is_empty() {
            Ok(None)
        } else {
            Ok(Some(recommendations.join("; ")))
        }
    }
    
    async fn check_rr_alerts(&self, position: &Position, metrics: &RiskRewardMetrics) -> Result<()> {
        if metrics.current_rr_ratio < dec!(0.5) {
            self.alert_manager.send_alert(RiskRewardAlert {
                position_id: position.id,
                account_id: position.account_id,
                alert_type: RRAlertType::PoorRiskReward,
                message: format!(
                    "Poor R:R ratio {:.2} for {} position",
                    metrics.current_rr_ratio,
                    position.symbol
                ),
                timestamp: Utc::now(),
            }).await?;
        }
        
        if metrics.performance_score < dec!(20) {
            self.alert_manager.send_alert(RiskRewardAlert {
                position_id: position.id,
                account_id: position.account_id,
                alert_type: RRAlertType::PoorPerformance,
                message: format!(
                    "Poor performance score {:.1} for {} position",
                    metrics.performance_score,
                    position.symbol
                ),
                timestamp: Utc::now(),
            }).await?;
        }
        
        if position.max_adverse_excursion < dec!(-100) {
            self.alert_manager.send_alert(RiskRewardAlert {
                position_id: position.id,
                account_id: position.account_id,
                alert_type: RRAlertType::HighMAE,
                message: format!(
                    "High MAE {:.2} for {} position - consider exit",
                    position.max_adverse_excursion,
                    position.symbol
                ),
                timestamp: Utc::now(),
            }).await?;
        }
        
        Ok(())
    }
    
    pub async fn get_portfolio_risk_reward_summary(&self) -> Result<PortfolioRRSummary> {
        let positions = self.position_tracker.get_all_open_positions().await?;
        
        let mut total_risk = dec!(0);
        let mut total_reward = dec!(0);
        let mut positions_with_good_rr = 0;
        let mut positions_with_poor_rr = 0;
        let mut total_performance_score = dec!(0);
        
        for position in &positions {
            if let Some(metrics) = self.rr_cache.get(&position.id) {
                total_risk += metrics.distance_to_stop * position.size;
                total_reward += metrics.distance_to_target * position.size;
                
                if metrics.current_rr_ratio >= dec!(2) {
                    positions_with_good_rr += 1;
                } else if metrics.current_rr_ratio < dec!(1) {
                    positions_with_poor_rr += 1;
                }
                
                total_performance_score += metrics.performance_score;
            }
        }
        
        let portfolio_rr_ratio = if total_risk != dec!(0) {
            total_reward / total_risk
        } else {
            dec!(0)
        };
        
        let avg_performance_score = if !positions.is_empty() {
            total_performance_score / Decimal::from(positions.len())
        } else {
            dec!(0)
        };
        
        Ok(PortfolioRRSummary {
            portfolio_rr_ratio,
            avg_performance_score,
            positions_with_good_rr,
            positions_with_poor_rr,
            total_positions: positions.len(),
            timestamp: Utc::now(),
        })
    }
    
    pub async fn optimize_targets(&self, position: &Position) -> Result<TargetOptimization> {
        let current_price = self.market_data.get_current_price(&position.symbol).await?;
        let atr = self.market_data.get_atr(&position.symbol, 14).await?;
        
        let optimal_stop = match position.position_type {
            PositionType::Long => current_price - (atr * dec!(2)),
            PositionType::Short => current_price + (atr * dec!(2)),
        };
        
        let optimal_target = match position.position_type {
            PositionType::Long => current_price + (atr * dec!(3)),
            PositionType::Short => current_price - (atr * dec!(3)),
        };
        
        let optimal_risk = (current_price - optimal_stop).abs() * position.size;
        let optimal_reward = (optimal_target - current_price).abs() * position.size;
        let optimal_rr = if optimal_risk != dec!(0) {
            optimal_reward / optimal_risk
        } else {
            dec!(0)
        };
        
        Ok(TargetOptimization {
            position_id: position.id,
            current_stop: position.stop_loss,
            optimal_stop: Some(optimal_stop),
            current_target: position.take_profit,
            optimal_target: Some(optimal_target),
            current_rr_ratio: self.rr_cache.get(&position.id)
                .map(|m| m.current_rr_ratio)
                .unwrap_or(dec!(0)),
            optimal_rr_ratio: optimal_rr,
            atr_based: true,
            timestamp: Utc::now(),
        })
    }
}

pub struct MarketDataProvider {
    price_cache: Arc<DashMap<String, Decimal>>,
    atr_cache: Arc<DashMap<String, Decimal>>,
}

impl MarketDataProvider {
    pub fn new() -> Self {
        Self {
            price_cache: Arc::new(DashMap::new()),
            atr_cache: Arc::new(DashMap::new()),
        }
    }
    
    pub async fn get_current_price(&self, symbol: &str) -> Result<Decimal> {
        if let Some(price) = self.price_cache.get(symbol) {
            Ok(*price)
        } else {
            Ok(dec!(1.1000))
        }
    }
    
    pub async fn get_atr(&self, symbol: &str, _period: usize) -> Result<Decimal> {
        if let Some(atr) = self.atr_cache.get(symbol) {
            Ok(*atr)
        } else {
            Ok(dec!(0.0050))
        }
    }
    
    pub async fn update_price(&self, symbol: String, price: Decimal) {
        self.price_cache.insert(symbol, price);
    }
    
    pub async fn update_atr(&self, symbol: String, atr: Decimal) {
        self.atr_cache.insert(symbol, atr);
    }
}

pub struct RiskRewardAlertManager {
    alerts: Arc<DashMap<PositionId, Vec<RiskRewardAlert>>>,
}

impl RiskRewardAlertManager {
    pub fn new() -> Self {
        Self {
            alerts: Arc::new(DashMap::new()),
        }
    }
    
    pub async fn send_alert(&self, alert: RiskRewardAlert) -> Result<()> {
        warn!("Risk/Reward Alert: {}", alert.message);
        
        self.alerts.entry(alert.position_id)
            .or_insert_with(Vec::new)
            .push(alert);
        
        Ok(())
    }
}

#[derive(Debug, Clone)]
pub struct RiskRewardAlert {
    pub position_id: PositionId,
    pub account_id: AccountId,
    pub alert_type: RRAlertType,
    pub message: String,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Copy)]
pub enum RRAlertType {
    PoorRiskReward,
    PoorPerformance,
    HighMAE,
    StagnantPosition,
    TargetAdjustmentNeeded,
}

#[derive(Debug, Clone)]
pub struct PortfolioRRSummary {
    pub portfolio_rr_ratio: Decimal,
    pub avg_performance_score: Decimal,
    pub positions_with_good_rr: usize,
    pub positions_with_poor_rr: usize,
    pub total_positions: usize,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone)]
pub struct TargetOptimization {
    pub position_id: PositionId,
    pub current_stop: Option<Decimal>,
    pub optimal_stop: Option<Decimal>,
    pub current_target: Option<Decimal>,
    pub optimal_target: Option<Decimal>,
    pub current_rr_ratio: Decimal,
    pub optimal_rr_ratio: Decimal,
    pub atr_based: bool,
    pub timestamp: DateTime<Utc>,
}