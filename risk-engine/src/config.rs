use rust_decimal::Decimal;
use rust_decimal_macros::dec;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskConfig {
    pub margin_thresholds: MarginThresholds,
    pub drawdown_thresholds: DrawdownThresholds,
    pub exposure_limits: ExposureLimits,
    pub risk_response_config: RiskResponseConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarginThresholds {
    pub warning_level: Decimal,
    pub critical_level: Decimal,
    pub stop_out_level: Decimal,
    pub monitoring_interval_secs: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DrawdownThresholds {
    pub daily_threshold: Decimal,
    pub weekly_threshold: Decimal,
    pub max_threshold: Decimal,
    pub recovery_factor_threshold: Decimal,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExposureLimits {
    pub max_exposure_per_symbol: Decimal,
    pub max_currency_exposure: Decimal,
    pub concentration_hhi_threshold: Decimal,
    pub pair_limits: HashMap<String, Decimal>,
    pub currency_limits: HashMap<String, Decimal>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskResponseConfig {
    pub enable_automated_responses: bool,
    pub position_reduction_percentage: Decimal,
    pub margin_protection_enabled: bool,
    pub circuit_breaker_enabled: bool,
    pub escalation_delay_minutes: u64,
}

impl Default for RiskConfig {
    fn default() -> Self {
        let mut pair_limits = HashMap::new();
        pair_limits.insert("EURUSD".to_string(), dec!(100000));
        pair_limits.insert("GBPUSD".to_string(), dec!(80000));
        pair_limits.insert("USDJPY".to_string(), dec!(90000));
        pair_limits.insert("AUDUSD".to_string(), dec!(70000));
        pair_limits.insert("USDCAD".to_string(), dec!(75000));

        let mut currency_limits = HashMap::new();
        currency_limits.insert("USD".to_string(), dec!(200000));
        currency_limits.insert("EUR".to_string(), dec!(150000));
        currency_limits.insert("GBP".to_string(), dec!(100000));
        currency_limits.insert("JPY".to_string(), dec!(120000));
        currency_limits.insert("AUD".to_string(), dec!(80000));

        Self {
            margin_thresholds: MarginThresholds {
                warning_level: dec!(150),
                critical_level: dec!(120),
                stop_out_level: dec!(100),
                monitoring_interval_secs: 1,
            },
            drawdown_thresholds: DrawdownThresholds {
                daily_threshold: dec!(5),
                weekly_threshold: dec!(10),
                max_threshold: dec!(20),
                recovery_factor_threshold: dec!(2),
            },
            exposure_limits: ExposureLimits {
                max_exposure_per_symbol: dec!(25),
                max_currency_exposure: dec!(30),
                concentration_hhi_threshold: dec!(0.25),
                pair_limits,
                currency_limits,
            },
            risk_response_config: RiskResponseConfig {
                enable_automated_responses: true,
                position_reduction_percentage: dec!(50),
                margin_protection_enabled: true,
                circuit_breaker_enabled: true,
                escalation_delay_minutes: 5,
            },
        }
    }
}

impl RiskConfig {
    pub fn from_file(path: &str) -> Result<Self, Box<dyn std::error::Error>> {
        let content = std::fs::read_to_string(path)?;
        let config: RiskConfig = toml::from_str(&content)?;
        Ok(config)
    }

    pub fn from_env() -> Self {
        let mut config = Self::default();
        
        if let Ok(warning_level) = std::env::var("RISK_MARGIN_WARNING_LEVEL") {
            if let Ok(level) = warning_level.parse::<f64>() {
                config.margin_thresholds.warning_level = Decimal::from_f64_retain(level).unwrap_or(dec!(150));
            }
        }

        if let Ok(critical_level) = std::env::var("RISK_MARGIN_CRITICAL_LEVEL") {
            if let Ok(level) = critical_level.parse::<f64>() {
                config.margin_thresholds.critical_level = Decimal::from_f64_retain(level).unwrap_or(dec!(120));
            }
        }

        if let Ok(daily_threshold) = std::env::var("RISK_DAILY_DRAWDOWN_THRESHOLD") {
            if let Ok(threshold) = daily_threshold.parse::<f64>() {
                config.drawdown_thresholds.daily_threshold = Decimal::from_f64_retain(threshold).unwrap_or(dec!(5));
            }
        }

        if let Ok(max_threshold) = std::env::var("RISK_MAX_DRAWDOWN_THRESHOLD") {
            if let Ok(threshold) = max_threshold.parse::<f64>() {
                config.drawdown_thresholds.max_threshold = Decimal::from_f64_retain(threshold).unwrap_or(dec!(20));
            }
        }

        if let Ok(max_exposure) = std::env::var("RISK_MAX_EXPOSURE_PER_SYMBOL") {
            if let Ok(exposure) = max_exposure.parse::<f64>() {
                config.exposure_limits.max_exposure_per_symbol = Decimal::from_f64_retain(exposure).unwrap_or(dec!(25));
            }
        }

        if let Ok(enabled) = std::env::var("RISK_AUTOMATED_RESPONSES_ENABLED") {
            config.risk_response_config.enable_automated_responses = enabled.parse().unwrap_or(true);
        }

        config
    }

    pub fn to_file(&self, path: &str) -> Result<(), Box<dyn std::error::Error>> {
        let content = toml::to_string_pretty(self)?;
        std::fs::write(path, content)?;
        Ok(())
    }

    pub fn validate(&self) -> Result<(), String> {
        if self.margin_thresholds.warning_level <= self.margin_thresholds.critical_level {
            return Err("Margin warning level must be greater than critical level".to_string());
        }

        if self.margin_thresholds.critical_level <= self.margin_thresholds.stop_out_level {
            return Err("Margin critical level must be greater than stop out level".to_string());
        }

        if self.drawdown_thresholds.daily_threshold <= dec!(0) || self.drawdown_thresholds.daily_threshold >= dec!(100) {
            return Err("Daily drawdown threshold must be between 0% and 100%".to_string());
        }

        if self.drawdown_thresholds.max_threshold <= dec!(0) || self.drawdown_thresholds.max_threshold >= dec!(100) {
            return Err("Maximum drawdown threshold must be between 0% and 100%".to_string());
        }

        if self.exposure_limits.max_exposure_per_symbol <= dec!(0) || self.exposure_limits.max_exposure_per_symbol > dec!(100) {
            return Err("Max exposure per symbol must be between 0% and 100%".to_string());
        }

        Ok(())
    }
}

pub fn load_config() -> RiskConfig {
    if let Ok(config_path) = std::env::var("RISK_CONFIG_PATH") {
        if let Ok(config) = RiskConfig::from_file(&config_path) {
            if config.validate().is_ok() {
                return config;
            }
        }
    }
    
    let config = RiskConfig::from_env();
    if config.validate().is_ok() {
        config
    } else {
        RiskConfig::default()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config_validation() {
        let config = RiskConfig::default();
        assert!(config.validate().is_ok());
    }

    #[test]
    fn test_invalid_margin_thresholds() {
        let mut config = RiskConfig::default();
        config.margin_thresholds.warning_level = dec!(100);
        config.margin_thresholds.critical_level = dec!(120);
        
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_config_serialization() {
        let config = RiskConfig::default();
        let toml_string = toml::to_string(&config).unwrap();
        let deserialized: RiskConfig = toml::from_str(&toml_string).unwrap();
        
        assert_eq!(config.margin_thresholds.warning_level, deserialized.margin_thresholds.warning_level);
    }
}