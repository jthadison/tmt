use crate::pnl_calculator::PositionTracker;
use anyhow::Result;
use chrono::{DateTime, Utc};
use dashmap::DashMap;
use risk_types::*;
use rust_decimal::Decimal;
use rust_decimal_macros::dec;
use std::collections::HashMap;
use std::sync::Arc;
use tracing::{error, info, warn};

pub struct ExposureMonitor {
    position_tracker: Arc<PositionTracker>,
    currency_exposure_calculator: Arc<CurrencyExposureCalculator>,
    exposure_limits: Arc<ExposureLimits>,
    exposure_alerts: Arc<ExposureAlertManager>,
}

impl ExposureMonitor {
    pub fn new(
        position_tracker: Arc<PositionTracker>,
        currency_exposure_calculator: Arc<CurrencyExposureCalculator>,
        exposure_limits: Arc<ExposureLimits>,
        exposure_alerts: Arc<ExposureAlertManager>,
    ) -> Self {
        Self {
            position_tracker,
            currency_exposure_calculator,
            exposure_limits,
            exposure_alerts,
        }
    }

    pub async fn calculate_total_exposure(&self) -> Result<ExposureReport> {
        let all_positions = self.position_tracker.get_all_open_positions().await?;

        let pair_exposure = self.calculate_pair_exposure(&all_positions).await?;

        let currency_exposure = self
            .currency_exposure_calculator
            .calculate_net_exposure(&all_positions)
            .await?;

        let total_exposure = self
            .calculate_total_portfolio_exposure(&all_positions)
            .await?;

        let limit_violations = self
            .check_exposure_limits(&pair_exposure, &currency_exposure)
            .await?;

        let report = ExposureReport {
            pair_exposure,
            currency_exposure,
            total_exposure,
            limit_violations,
            concentration_risk: self.calculate_concentration_risk(&all_positions).await?,
            diversification_score: self.calculate_diversification_score(&all_positions).await?,
            timestamp: Utc::now(),
        };

        if !report.limit_violations.is_empty() {
            self.exposure_alerts.send_violation_alert(&report).await?;
        }

        Ok(report)
    }

    async fn calculate_pair_exposure(
        &self,
        positions: &[Position],
    ) -> Result<HashMap<String, ExposureData>> {
        let mut pair_exposure = HashMap::new();

        for position in positions {
            let exposure_value = self.calculate_position_exposure_value(position).await?;

            let entry = pair_exposure
                .entry(position.symbol.clone())
                .or_insert(ExposureData {
                    long_exposure: dec!(0),
                    short_exposure: dec!(0),
                    net_exposure: dec!(0),
                    total_exposure: dec!(0),
                    position_count: 0,
                });

            match position.position_type {
                PositionType::Long => {
                    entry.long_exposure += exposure_value;
                }
                PositionType::Short => {
                    entry.short_exposure += exposure_value;
                }
            }

            entry.net_exposure = entry.long_exposure - entry.short_exposure;
            entry.total_exposure = entry.long_exposure + entry.short_exposure;
            entry.position_count += 1;
        }

        Ok(pair_exposure)
    }

    async fn calculate_position_exposure_value(&self, position: &Position) -> Result<Decimal> {
        Ok(position.size * position.entry_price)
    }

    async fn calculate_total_portfolio_exposure(&self, positions: &[Position]) -> Result<Decimal> {
        let mut total = dec!(0);
        for position in positions {
            total += self.calculate_position_exposure_value(position).await?;
        }
        Ok(total)
    }

    async fn check_exposure_limits(
        &self,
        pair_exposure: &HashMap<String, ExposureData>,
        currency_exposure: &HashMap<String, Decimal>,
    ) -> Result<Vec<ExposureLimitViolation>> {
        let mut violations = Vec::new();

        for (pair, exposure) in pair_exposure {
            if let Some(limit) = self.exposure_limits.get_pair_limit(pair).await {
                if exposure.total_exposure > limit {
                    violations.push(ExposureLimitViolation {
                        limit_type: format!("pair_exposure_{}", pair),
                        current_value: exposure.total_exposure,
                        limit_value: limit,
                        severity: self.determine_severity(exposure.total_exposure, limit),
                    });
                }
            }

            if exposure.position_count > 3 {
                violations.push(ExposureLimitViolation {
                    limit_type: format!("pair_position_count_{}", pair),
                    current_value: Decimal::from(exposure.position_count),
                    limit_value: dec!(3),
                    severity: "warning".to_string(),
                });
            }
        }

        for (currency, exposure) in currency_exposure {
            if let Some(limit) = self.exposure_limits.get_currency_limit(currency).await {
                if *exposure > limit {
                    violations.push(ExposureLimitViolation {
                        limit_type: format!("currency_exposure_{}", currency),
                        current_value: *exposure,
                        limit_value: limit,
                        severity: self.determine_severity(*exposure, limit),
                    });
                }
            }
        }

        Ok(violations)
    }

    fn determine_severity(&self, current: Decimal, limit: Decimal) -> String {
        let ratio = current / limit;
        if ratio > dec!(1.5) {
            "critical".to_string()
        } else if ratio > dec!(1.2) {
            "high".to_string()
        } else {
            "warning".to_string()
        }
    }

    async fn calculate_concentration_risk(
        &self,
        positions: &[Position],
    ) -> Result<ConcentrationRisk> {
        let total_exposure: Decimal = positions.iter().map(|p| p.size * p.entry_price).sum();

        if total_exposure == dec!(0) {
            return Ok(ConcentrationRisk {
                herfindahl_index: dec!(0),
                concentration_level: ConcentrationLevel::Low,
                largest_position_percentage: dec!(0),
            });
        }

        let mut symbol_exposures = HashMap::new();
        for position in positions {
            let exposure = position.size * position.entry_price;
            *symbol_exposures.entry(&position.symbol).or_insert(dec!(0)) += exposure;
        }

        let hhi: Decimal = symbol_exposures
            .values()
            .map(|&exposure| {
                let market_share = exposure / total_exposure;
                market_share * market_share
            })
            .sum();

        let concentration_level = match hhi {
            h if h < dec!(0.15) => ConcentrationLevel::Low,
            h if h < dec!(0.25) => ConcentrationLevel::Moderate,
            _ => ConcentrationLevel::High,
        };

        let largest_position_percentage = symbol_exposures
            .values()
            .map(|&exp| exp / total_exposure * dec!(100))
            .max()
            .unwrap_or(dec!(0));

        Ok(ConcentrationRisk {
            herfindahl_index: hhi,
            concentration_level,
            largest_position_percentage,
        })
    }

    async fn calculate_diversification_score(&self, positions: &[Position]) -> Result<Decimal> {
        if positions.is_empty() {
            return Ok(dec!(0));
        }

        let unique_symbols: std::collections::HashSet<_> =
            positions.iter().map(|p| &p.symbol).collect();

        let unique_count = Decimal::from(unique_symbols.len());
        let total_count = Decimal::from(positions.len());

        let diversity_ratio = unique_count / total_count;

        let concentration = self.calculate_concentration_risk(positions).await?;
        let concentration_score = dec!(1) - concentration.herfindahl_index;

        Ok((diversity_ratio + concentration_score) / dec!(2) * dec!(100))
    }

    pub async fn get_exposure_by_account(&self, account_id: AccountId) -> Result<AccountExposure> {
        let positions = self
            .position_tracker
            .get_account_positions(account_id)
            .await?;

        let mut total_long_exposure = dec!(0);
        let mut total_short_exposure = dec!(0);
        let mut symbol_exposure = HashMap::new();

        for position in &positions {
            let exposure = self.calculate_position_exposure_value(position).await?;

            match position.position_type {
                PositionType::Long => total_long_exposure += exposure,
                PositionType::Short => total_short_exposure += exposure,
            }

            *symbol_exposure
                .entry(position.symbol.clone())
                .or_insert(dec!(0)) += exposure;
        }

        Ok(AccountExposure {
            account_id,
            total_long_exposure,
            total_short_exposure,
            net_exposure: total_long_exposure - total_short_exposure,
            total_exposure: total_long_exposure + total_short_exposure,
            symbol_exposure,
            position_count: positions.len(),
            timestamp: Utc::now(),
        })
    }

    pub async fn rebalance_exposure_recommendations(&self) -> Result<Vec<RebalanceRecommendation>> {
        let mut recommendations = Vec::new();
        let all_positions = self.position_tracker.get_all_open_positions().await?;

        let pair_exposure = self.calculate_pair_exposure(&all_positions).await?;
        let total_exposure = self
            .calculate_total_portfolio_exposure(&all_positions)
            .await?;

        for (pair, exposure) in pair_exposure {
            let exposure_percentage = if total_exposure != dec!(0) {
                (exposure.total_exposure / total_exposure) * dec!(100)
            } else {
                dec!(0)
            };

            if exposure_percentage > dec!(30) {
                recommendations.push(RebalanceRecommendation {
                    symbol: pair.clone(),
                    current_exposure: exposure.total_exposure,
                    current_percentage: exposure_percentage,
                    target_exposure: total_exposure * dec!(0.20),
                    target_percentage: dec!(20),
                    action: RebalanceAction::Reduce,
                    priority: if exposure_percentage > dec!(40) {
                        RebalancePriority::High
                    } else {
                        RebalancePriority::Medium
                    },
                });
            }

            if exposure.net_exposure.abs() > exposure.total_exposure * dec!(0.8) {
                recommendations.push(RebalanceRecommendation {
                    symbol: pair.clone(),
                    current_exposure: exposure.net_exposure,
                    current_percentage: exposure_percentage,
                    target_exposure: dec!(0),
                    target_percentage: dec!(0),
                    action: RebalanceAction::Hedge,
                    priority: RebalancePriority::Medium,
                });
            }
        }

        Ok(recommendations)
    }
}

pub struct CurrencyExposureCalculator;

impl CurrencyExposureCalculator {
    pub async fn calculate_net_exposure(
        &self,
        positions: &[Position],
    ) -> Result<HashMap<String, Decimal>> {
        let mut currency_exposure = HashMap::new();

        for position in positions {
            let (base_currency, quote_currency) = self.parse_currency_pair(&position.symbol)?;
            let exposure_value = position.size * position.entry_price;

            match position.position_type {
                PositionType::Long => {
                    *currency_exposure.entry(base_currency).or_insert(dec!(0)) += exposure_value;
                    *currency_exposure.entry(quote_currency).or_insert(dec!(0)) -= exposure_value;
                }
                PositionType::Short => {
                    *currency_exposure.entry(base_currency).or_insert(dec!(0)) -= exposure_value;
                    *currency_exposure.entry(quote_currency).or_insert(dec!(0)) += exposure_value;
                }
            }
        }

        Ok(currency_exposure)
    }

    fn parse_currency_pair(&self, symbol: &str) -> Result<(String, String)> {
        if symbol.len() >= 6 {
            Ok((symbol[..3].to_string(), symbol[3..6].to_string()))
        } else {
            Err(anyhow::anyhow!("Invalid currency pair: {}", symbol))
        }
    }
}

pub struct ExposureLimits {
    pair_limits: Arc<DashMap<String, Decimal>>,
    currency_limits: Arc<DashMap<String, Decimal>>,
    default_pair_limit: Decimal,
    default_currency_limit: Decimal,
}

impl ExposureLimits {
    pub fn new() -> Self {
        let mut pair_limits = DashMap::new();
        pair_limits.insert("EURUSD".to_string(), dec!(100000));
        pair_limits.insert("GBPUSD".to_string(), dec!(80000));
        pair_limits.insert("USDJPY".to_string(), dec!(90000));

        let mut currency_limits = DashMap::new();
        currency_limits.insert("USD".to_string(), dec!(200000));
        currency_limits.insert("EUR".to_string(), dec!(150000));
        currency_limits.insert("GBP".to_string(), dec!(100000));

        Self {
            pair_limits: Arc::new(pair_limits),
            currency_limits: Arc::new(currency_limits),
            default_pair_limit: dec!(50000),
            default_currency_limit: dec!(100000),
        }
    }

    pub async fn get_pair_limit(&self, pair: &str) -> Option<Decimal> {
        self.pair_limits
            .get(pair)
            .map(|limit| *limit)
            .or(Some(self.default_pair_limit))
    }

    pub async fn get_currency_limit(&self, currency: &str) -> Option<Decimal> {
        self.currency_limits
            .get(currency)
            .map(|limit| *limit)
            .or(Some(self.default_currency_limit))
    }
}

pub struct ExposureAlertManager;

impl ExposureAlertManager {
    pub async fn send_violation_alert(&self, report: &ExposureReport) -> Result<()> {
        for violation in &report.limit_violations {
            warn!(
                "Exposure limit violation: {} - Current: {}, Limit: {}, Severity: {}",
                violation.limit_type,
                violation.current_value,
                violation.limit_value,
                violation.severity
            );
        }
        Ok(())
    }
}

#[derive(Debug, Clone)]
pub struct AccountExposure {
    pub account_id: AccountId,
    pub total_long_exposure: Decimal,
    pub total_short_exposure: Decimal,
    pub net_exposure: Decimal,
    pub total_exposure: Decimal,
    pub symbol_exposure: HashMap<String, Decimal>,
    pub position_count: usize,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone)]
pub struct RebalanceRecommendation {
    pub symbol: String,
    pub current_exposure: Decimal,
    pub current_percentage: Decimal,
    pub target_exposure: Decimal,
    pub target_percentage: Decimal,
    pub action: RebalanceAction,
    pub priority: RebalancePriority,
}

#[derive(Debug, Clone, Copy)]
pub enum RebalanceAction {
    Reduce,
    Increase,
    Hedge,
    Close,
}

#[derive(Debug, Clone, Copy)]
pub enum RebalancePriority {
    Low,
    Medium,
    High,
    Critical,
}
