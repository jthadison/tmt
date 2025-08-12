use crate::risk::config::DrawdownThresholds;
use anyhow::Result;
use chrono::{DateTime, Duration, NaiveDate, Utc};
use dashmap::DashMap;
use risk_types::*;
use rust_decimal::Decimal;
use rust_decimal_macros::dec;
use std::sync::Arc;
use tracing::{error, info, warn};

pub struct DrawdownTracker {
    equity_history: Arc<EquityHistoryManager>,
    drawdown_cache: Arc<DashMap<AccountId, DrawdownMetrics>>,
    drawdown_alerts: Arc<DrawdownAlertManager>,
    thresholds: DrawdownThresholds,
}

impl DrawdownTracker {
    pub fn new(
        equity_history: Arc<EquityHistoryManager>,
        drawdown_alerts: Arc<DrawdownAlertManager>,
        thresholds: DrawdownThresholds,
    ) -> Self {
        Self {
            equity_history,
            drawdown_cache: Arc::new(DashMap::new()),
            drawdown_alerts,
            thresholds,
        }
    }

    pub async fn calculate_drawdowns(&self, account_id: AccountId) -> Result<DrawdownMetrics> {
        // Check cache first for performance
        if let Some(cached_metrics) = self.drawdown_cache.get(&account_id) {
            let cache_age = Utc::now() - cached_metrics.last_updated;
            if cache_age < Duration::minutes(5) {
                // Cache valid for 5 minutes
                return Ok(cached_metrics.clone());
            }
        }

        let equity_history = self
            .equity_history
            .get_history(account_id, Duration::days(30))
            .await?;

        if equity_history.is_empty() {
            return Ok(DrawdownMetrics {
                daily_drawdown: DrawdownData {
                    amount: dec!(0),
                    percentage: dec!(0),
                    peak_equity: dec!(0),
                    current_equity: dec!(0),
                    start_time: Utc::now(),
                    duration: Duration::zero(),
                },
                weekly_drawdown: DrawdownData {
                    amount: dec!(0),
                    percentage: dec!(0),
                    peak_equity: dec!(0),
                    current_equity: dec!(0),
                    start_time: Utc::now(),
                    duration: Duration::zero(),
                },
                maximum_drawdown: DrawdownData {
                    amount: dec!(0),
                    percentage: dec!(0),
                    peak_equity: dec!(0),
                    current_equity: dec!(0),
                    start_time: Utc::now(),
                    duration: Duration::zero(),
                },
                current_underwater_period: Duration::zero(),
                recovery_factor: dec!(0),
                last_updated: Utc::now(),
            });
        }

        // Optimize: Calculate all metrics in single pass for better performance
        let metrics = self.calculate_all_drawdown_metrics(&equity_history).await?;

        self.drawdown_cache.insert(account_id, metrics.clone());

        self.check_drawdown_alerts(account_id, &metrics).await?;

        Ok(metrics)
    }

    /// Optimized single-pass calculation of all drawdown metrics
    async fn calculate_all_drawdown_metrics(
        &self,
        equity_history: &[EquityPoint],
    ) -> Result<DrawdownMetrics> {
        let now = Utc::now();
        let today = now.date_naive();
        let one_week_ago = now - Duration::days(7);

        let mut daily_peak = dec!(0);
        let mut daily_current = dec!(0);
        let mut daily_start_time = now;

        let mut weekly_peak = dec!(0);
        let mut weekly_current = dec!(0);
        let mut weekly_start_time = now;

        let mut max_drawdown_amount = dec!(0);
        let mut max_drawdown_peak = dec!(0);
        let mut max_drawdown_pct = dec!(0);
        let mut max_drawdown_start: Option<DateTime<Utc>> = None;
        let mut max_drawdown_duration = Duration::zero();

        let mut global_peak = dec!(0);
        let mut underwater_start: Option<DateTime<Utc>> = None;
        let mut is_daily_set = false;
        let mut is_weekly_set = false;

        // Single pass through data for optimal performance
        for point in equity_history {
            let equity = point.equity;
            let timestamp = point.timestamp;

            // Daily calculations
            if timestamp.date_naive() == today {
                if !is_daily_set {
                    daily_current = equity;
                    daily_peak = equity;
                    daily_start_time = timestamp;
                    is_daily_set = true;
                } else {
                    daily_current = equity;
                    if equity > daily_peak {
                        daily_peak = equity;
                    }
                }
            }

            // Weekly calculations
            if timestamp >= one_week_ago {
                if !is_weekly_set {
                    weekly_current = equity;
                    weekly_peak = equity;
                    weekly_start_time = timestamp;
                    is_weekly_set = true;
                } else {
                    weekly_current = equity;
                    if equity > weekly_peak {
                        weekly_peak = equity;
                    }
                }
            }

            // Maximum drawdown calculations
            if equity > global_peak {
                global_peak = equity;
                underwater_start = None;
            } else {
                if underwater_start.is_none() {
                    underwater_start = Some(timestamp);
                }

                let current_drawdown = global_peak - equity;
                if current_drawdown > max_drawdown_amount {
                    max_drawdown_amount = current_drawdown;
                    max_drawdown_peak = global_peak;
                    max_drawdown_pct = if global_peak > dec!(0) {
                        (current_drawdown / global_peak) * dec!(100)
                    } else {
                        dec!(0)
                    };

                    if let Some(start_time) = underwater_start {
                        max_drawdown_duration = timestamp - start_time;
                        max_drawdown_start = Some(start_time);
                    }
                }
            }
        }

        // Calculate recovery factor
        let initial_equity = equity_history.first().map(|p| p.equity).unwrap_or(dec!(0));
        let current_equity = equity_history.last().map(|p| p.equity).unwrap_or(dec!(0));
        let recovery_factor = if max_drawdown_amount > dec!(0) {
            let profit = current_equity - initial_equity;
            profit / max_drawdown_amount
        } else {
            let profit = current_equity - initial_equity;
            if profit > dec!(0) {
                Decimal::MAX
            } else {
                dec!(0)
            }
        };

        // Calculate current underwater period
        let current_underwater_period = if let Some(start) = underwater_start {
            now - start
        } else {
            Duration::zero()
        };

        Ok(DrawdownMetrics {
            daily_drawdown: DrawdownData {
                amount: daily_peak - daily_current,
                percentage: if daily_peak > dec!(0) {
                    ((daily_peak - daily_current) / daily_peak) * dec!(100)
                } else {
                    dec!(0)
                },
                peak_equity: daily_peak,
                current_equity: daily_current,
                start_time: daily_start_time,
                duration: now - daily_start_time,
            },
            weekly_drawdown: DrawdownData {
                amount: weekly_peak - weekly_current,
                percentage: if weekly_peak > dec!(0) {
                    ((weekly_peak - weekly_current) / weekly_peak) * dec!(100)
                } else {
                    dec!(0)
                },
                peak_equity: weekly_peak,
                current_equity: weekly_current,
                start_time: weekly_start_time,
                duration: now - weekly_start_time,
            },
            maximum_drawdown: DrawdownData {
                amount: max_drawdown_amount,
                percentage: max_drawdown_pct,
                peak_equity: max_drawdown_peak,
                current_equity: current_equity,
                start_time: max_drawdown_start.unwrap_or(now),
                duration: max_drawdown_duration,
            },
            current_underwater_period,
            recovery_factor,
            last_updated: now,
        })
    }

    async fn calculate_daily_drawdown(
        &self,
        equity_history: &[EquityPoint],
    ) -> Result<DrawdownData> {
        let today = Utc::now().date_naive();
        let today_points: Vec<_> = equity_history
            .iter()
            .filter(|point| point.timestamp.date_naive() == today)
            .collect();

        if today_points.is_empty() {
            return Ok(DrawdownData {
                amount: dec!(0),
                percentage: dec!(0),
                peak_equity: dec!(0),
                current_equity: dec!(0),
                start_time: Utc::now(),
                duration: Duration::zero(),
            });
        }

        let starting_equity = today_points[0].equity;
        let current_equity = today_points.last().unwrap().equity;
        let peak_equity = today_points
            .iter()
            .map(|p| p.equity)
            .max()
            .unwrap_or(dec!(0));

        let drawdown_amount = peak_equity - current_equity;
        let drawdown_percentage = if peak_equity != dec!(0) {
            (drawdown_amount / peak_equity) * dec!(100)
        } else {
            dec!(0)
        };

        Ok(DrawdownData {
            amount: drawdown_amount,
            percentage: drawdown_percentage,
            peak_equity,
            current_equity,
            start_time: today_points[0].timestamp,
            duration: Utc::now() - today_points[0].timestamp,
        })
    }

    async fn calculate_weekly_drawdown(
        &self,
        equity_history: &[EquityPoint],
    ) -> Result<DrawdownData> {
        let one_week_ago = Utc::now() - Duration::days(7);
        let week_points: Vec<_> = equity_history
            .iter()
            .filter(|point| point.timestamp >= one_week_ago)
            .collect();

        if week_points.is_empty() {
            return Ok(DrawdownData {
                amount: dec!(0),
                percentage: dec!(0),
                peak_equity: dec!(0),
                current_equity: dec!(0),
                start_time: Utc::now(),
                duration: Duration::zero(),
            });
        }

        let peak_equity = week_points
            .iter()
            .map(|p| p.equity)
            .max()
            .unwrap_or(dec!(0));
        let current_equity = week_points.last().unwrap().equity;

        let drawdown_amount = peak_equity - current_equity;
        let drawdown_percentage = if peak_equity != dec!(0) {
            (drawdown_amount / peak_equity) * dec!(100)
        } else {
            dec!(0)
        };

        let peak_time = week_points
            .iter()
            .find(|p| p.equity == peak_equity)
            .map(|p| p.timestamp)
            .unwrap_or_else(|| Utc::now());

        Ok(DrawdownData {
            amount: drawdown_amount,
            percentage: drawdown_percentage,
            peak_equity,
            current_equity,
            start_time: peak_time,
            duration: Utc::now() - peak_time,
        })
    }

    async fn calculate_maximum_drawdown(
        &self,
        equity_history: &[EquityPoint],
    ) -> Result<DrawdownData> {
        let mut max_drawdown = dec!(0);
        let mut max_drawdown_pct = dec!(0);
        let mut peak_equity = dec!(0);
        let mut drawdown_start: Option<DateTime<Utc>> = None;
        let mut max_drawdown_period = Duration::zero();
        let mut max_drawdown_peak = dec!(0);

        for point in equity_history {
            if point.equity > peak_equity {
                peak_equity = point.equity;
                drawdown_start = None;
            } else {
                if drawdown_start.is_none() {
                    drawdown_start = Some(point.timestamp);
                }

                let current_drawdown = peak_equity - point.equity;
                let current_drawdown_pct = if peak_equity != dec!(0) {
                    (current_drawdown / peak_equity) * dec!(100)
                } else {
                    dec!(0)
                };

                if current_drawdown > max_drawdown {
                    max_drawdown = current_drawdown;
                    max_drawdown_pct = current_drawdown_pct;
                    max_drawdown_peak = peak_equity;

                    if let Some(start_time) = drawdown_start {
                        max_drawdown_period = point.timestamp - start_time;
                    }
                }
            }
        }

        let current_equity = equity_history.last().map(|p| p.equity).unwrap_or(dec!(0));

        Ok(DrawdownData {
            amount: max_drawdown,
            percentage: max_drawdown_pct,
            peak_equity: max_drawdown_peak,
            current_equity,
            start_time: drawdown_start.unwrap_or_else(|| Utc::now()),
            duration: max_drawdown_period,
        })
    }

    async fn calculate_underwater_period(
        &self,
        equity_history: &[EquityPoint],
    ) -> Result<Duration> {
        if equity_history.is_empty() {
            return Ok(Duration::zero());
        }

        let mut peak_equity = dec!(0);
        let mut underwater_start: Option<DateTime<Utc>> = None;

        for point in equity_history {
            if point.equity >= peak_equity {
                peak_equity = point.equity;
                underwater_start = None;
            } else if underwater_start.is_none() {
                underwater_start = Some(point.timestamp);
            }
        }

        if let Some(start) = underwater_start {
            Ok(Utc::now() - start)
        } else {
            Ok(Duration::zero())
        }
    }

    async fn calculate_recovery_factor(&self, equity_history: &[EquityPoint]) -> Result<Decimal> {
        if equity_history.len() < 2 {
            return Ok(dec!(0));
        }

        let initial_equity = equity_history.first().unwrap().equity;
        let current_equity = equity_history.last().unwrap().equity;
        let max_drawdown = self
            .calculate_maximum_drawdown(equity_history)
            .await?
            .amount;

        // Proper handling of division by zero - no magic numbers
        if max_drawdown <= dec!(0) {
            // If there was no drawdown and we have profit, recovery is infinite (represented as max value)
            let profit = current_equity - initial_equity;
            if profit > dec!(0) {
                return Ok(Decimal::MAX); // Infinite recovery (no drawdown but profit exists)
            } else {
                return Ok(dec!(0)); // No drawdown, no profit = no recovery factor
            }
        }

        let profit = current_equity - initial_equity;
        Ok(profit / max_drawdown)
    }

    async fn check_drawdown_alerts(
        &self,
        account_id: AccountId,
        metrics: &DrawdownMetrics,
    ) -> Result<()> {
        if metrics.daily_drawdown.percentage > self.thresholds.daily_threshold {
            self.drawdown_alerts
                .send_alert(DrawdownAlert {
                    account_id,
                    alert_type: DrawdownAlertType::Daily,
                    drawdown_percentage: metrics.daily_drawdown.percentage,
                    threshold: self.thresholds.daily_threshold,
                    message: format!(
                        "Daily drawdown exceeds threshold: {:.2}% > {:.2}%",
                        metrics.daily_drawdown.percentage, self.thresholds.daily_threshold
                    ),
                    timestamp: Utc::now(),
                })
                .await?;
        }

        if metrics.weekly_drawdown.percentage > self.thresholds.weekly_threshold {
            self.drawdown_alerts
                .send_alert(DrawdownAlert {
                    account_id,
                    alert_type: DrawdownAlertType::Weekly,
                    drawdown_percentage: metrics.weekly_drawdown.percentage,
                    threshold: self.thresholds.weekly_threshold,
                    message: format!(
                        "Weekly drawdown exceeds threshold: {:.2}% > {:.2}%",
                        metrics.weekly_drawdown.percentage, self.thresholds.weekly_threshold
                    ),
                    timestamp: Utc::now(),
                })
                .await?;
        }

        if metrics.maximum_drawdown.percentage > self.thresholds.max_threshold {
            self.drawdown_alerts
                .send_alert(DrawdownAlert {
                    account_id,
                    alert_type: DrawdownAlertType::Maximum,
                    drawdown_percentage: metrics.maximum_drawdown.percentage,
                    threshold: self.thresholds.max_threshold,
                    message: format!(
                        "Maximum drawdown exceeds threshold: {:.2}% > {:.2}%",
                        metrics.maximum_drawdown.percentage, self.thresholds.max_threshold
                    ),
                    timestamp: Utc::now(),
                })
                .await?;
        }

        Ok(())
    }

    pub async fn trigger_drawdown_based_position_sizing(
        &self,
        account_id: AccountId,
    ) -> Result<Decimal> {
        let metrics = self
            .drawdown_cache
            .get(&account_id)
            .map(|m| m.clone())
            .unwrap_or_else(|| DrawdownMetrics {
                daily_drawdown: DrawdownData {
                    amount: dec!(0),
                    percentage: dec!(0),
                    peak_equity: dec!(0),
                    current_equity: dec!(0),
                    start_time: Utc::now(),
                    duration: Duration::zero(),
                },
                weekly_drawdown: DrawdownData {
                    amount: dec!(0),
                    percentage: dec!(0),
                    peak_equity: dec!(0),
                    current_equity: dec!(0),
                    start_time: Utc::now(),
                    duration: Duration::zero(),
                },
                maximum_drawdown: DrawdownData {
                    amount: dec!(0),
                    percentage: dec!(0),
                    peak_equity: dec!(0),
                    current_equity: dec!(0),
                    start_time: Utc::now(),
                    duration: Duration::zero(),
                },
                current_underwater_period: Duration::zero(),
                recovery_factor: dec!(0),
                last_updated: Utc::now(),
            });

        let base_risk = dec!(2);

        let adjustment_factor = if metrics.maximum_drawdown.percentage > dec!(15) {
            dec!(0.5)
        } else if metrics.maximum_drawdown.percentage > dec!(10) {
            dec!(0.75)
        } else if metrics.maximum_drawdown.percentage > dec!(5) {
            dec!(0.9)
        } else {
            dec!(1)
        };

        Ok(base_risk * adjustment_factor)
    }
}

// Removed Default implementations for external types (DrawdownMetrics, DrawdownData)
// These should be defined in the risk_types crate where the types are declared

pub struct EquityHistoryManager {
    history: Arc<DashMap<AccountId, Vec<EquityPoint>>>,
}

impl EquityHistoryManager {
    pub fn new() -> Self {
        Self {
            history: Arc::new(DashMap::new()),
        }
    }

    pub async fn get_history(
        &self,
        account_id: AccountId,
        duration: Duration,
    ) -> Result<Vec<EquityPoint>> {
        let cutoff_time = Utc::now() - duration;

        let history = self
            .history
            .get(&account_id)
            .map(|h| h.clone())
            .unwrap_or_default();

        Ok(history
            .into_iter()
            .filter(|point| point.timestamp >= cutoff_time)
            .collect())
    }

    pub async fn record_equity(
        &self,
        account_id: AccountId,
        equity: Decimal,
        balance: Decimal,
    ) -> Result<()> {
        let point = EquityPoint {
            equity,
            balance,
            timestamp: Utc::now(),
        };

        self.history
            .entry(account_id)
            .or_insert_with(Vec::new)
            .push(point);

        Ok(())
    }
}

pub struct DrawdownAlertManager {
    alerts: Arc<DashMap<AccountId, Vec<DrawdownAlert>>>,
}

impl DrawdownAlertManager {
    pub fn new() -> Self {
        Self {
            alerts: Arc::new(DashMap::new()),
        }
    }

    pub async fn send_alert(&self, alert: DrawdownAlert) -> Result<()> {
        warn!("Drawdown Alert: {}", alert.message);

        self.alerts
            .entry(alert.account_id)
            .or_insert_with(Vec::new)
            .push(alert);

        Ok(())
    }
}

#[derive(Debug, Clone)]
pub struct DrawdownAlert {
    pub account_id: AccountId,
    pub alert_type: DrawdownAlertType,
    pub drawdown_percentage: Decimal,
    pub threshold: Decimal,
    pub message: String,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Copy)]
pub enum DrawdownAlertType {
    Daily,
    Weekly,
    Maximum,
}
