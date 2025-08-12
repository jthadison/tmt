use std::collections::HashMap;
use std::sync::Arc;
use anyhow::{Result, Context};
use chrono::{DateTime, Utc, Duration};
use tracing::{info, warn, error};
use uuid::Uuid;
use rust_decimal::Decimal;
use tokio::sync::RwLock;

use super::types::*;

// Database interface trait - would be implemented by actual database client
#[async_trait::async_trait]
pub trait AuditDatabase: Send + Sync + std::fmt::Debug {
    async fn store_audit_entry(&self, entry: &AuditEntry) -> Result<()>;
    async fn get_entries_in_range(&self, time_range: TimeRange) -> Result<Vec<AuditEntry>>;
    async fn get_position_exit_history(&self, position_id: PositionId) -> Result<Vec<AuditEntry>>;
    async fn store_emergency_close_event(&self, reason: String, timestamp: DateTime<Utc>) -> Result<()>;
    async fn get_entries_by_type(&self, modification_type: ExitModificationType, limit: Option<u32>) -> Result<Vec<AuditEntry>>;
}

// In-memory implementation for testing/demo
#[derive(Debug)]
pub struct InMemoryAuditDatabase {
    entries: Arc<RwLock<Vec<AuditEntry>>>,
    emergency_events: Arc<RwLock<Vec<EmergencyCloseEvent>>>,
}

impl InMemoryAuditDatabase {
    pub fn new() -> Self {
        Self {
            entries: Arc::new(RwLock::new(Vec::new())),
            emergency_events: Arc::new(RwLock::new(Vec::new())),
        }
    }
}

#[async_trait::async_trait]
impl AuditDatabase for InMemoryAuditDatabase {
    async fn store_audit_entry(&self, entry: &AuditEntry) -> Result<()> {
        let mut entries = self.entries.write().await;
        entries.push(entry.clone());
        Ok(())
    }

    async fn get_entries_in_range(&self, time_range: TimeRange) -> Result<Vec<AuditEntry>> {
        let entries = self.entries.read().await;
        let filtered = entries
            .iter()
            .filter(|entry| entry.timestamp >= time_range.start && entry.timestamp <= time_range.end)
            .cloned()
            .collect();
        Ok(filtered)
    }

    async fn get_position_exit_history(&self, position_id: PositionId) -> Result<Vec<AuditEntry>> {
        let entries = self.entries.read().await;
        let position_entries = entries
            .iter()
            .filter(|entry| entry.position_id == position_id)
            .cloned()
            .collect();
        Ok(position_entries)
    }

    async fn store_emergency_close_event(&self, reason: String, timestamp: DateTime<Utc>) -> Result<()> {
        let mut events = self.emergency_events.write().await;
        events.push(EmergencyCloseEvent {
            id: Uuid::new_v4(),
            reason,
            timestamp,
            positions_affected: 0, // Would be calculated in real implementation
        });
        Ok(())
    }

    async fn get_entries_by_type(&self, modification_type: ExitModificationType, limit: Option<u32>) -> Result<Vec<AuditEntry>> {
        let entries = self.entries.read().await;
        let mut filtered: Vec<AuditEntry> = entries
            .iter()
            .filter(|entry| std::mem::discriminant(&entry.modification_type) == std::mem::discriminant(&modification_type))
            .cloned()
            .collect();
        
        // Sort by timestamp, newest first
        filtered.sort_by(|a, b| b.timestamp.cmp(&a.timestamp));
        
        if let Some(limit) = limit {
            filtered.truncate(limit as usize);
        }
        
        Ok(filtered)
    }
}

#[derive(Debug, Clone)]
pub struct EmergencyCloseEvent {
    pub id: Uuid,
    pub reason: String,
    pub timestamp: DateTime<Utc>,
    pub positions_affected: u32,
}

#[derive(Debug, Clone)]
pub struct TimeRange {
    pub start: DateTime<Utc>,
    pub end: DateTime<Utc>,
}

#[derive(Debug)]
pub struct ExitAnalytics {
    performance_cache: Arc<RwLock<HashMap<String, f64>>>,
    modification_counts: Arc<RwLock<HashMap<ExitModificationType, u32>>>,
}

impl ExitAnalytics {
    pub fn new() -> Self {
        Self {
            performance_cache: Arc::new(RwLock::new(HashMap::new())),
            modification_counts: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub async fn record_modification(&self, modification: &ExitModification) -> Result<()> {
        let mut counts = self.modification_counts.write().await;
        let modification_type = modification.modification_type.clone();
        *counts.entry(modification_type).or_insert(0) += 1;
        
        // Update performance cache
        let performance_key = format!("{:?}_{}", modification.modification_type, modification.position_id);
        let performance_impact = self.calculate_modification_impact(modification).await?;
        
        let mut cache = self.performance_cache.write().await;
        cache.insert(performance_key, performance_impact);
        
        Ok(())
    }

    async fn calculate_modification_impact(&self, modification: &ExitModification) -> Result<f64> {
        // Simplified performance impact calculation
        // In reality, this would consider actual P&L changes, risk reduction, etc.
        match modification.modification_type {
            ExitModificationType::TrailingStop => {
                // Positive impact for trailing stops (protecting profits)
                Ok(0.1 * (modification.new_value - modification.old_value).abs())
            },
            ExitModificationType::BreakEven => {
                // Strong positive impact (risk elimination)
                Ok(0.5)
            },
            ExitModificationType::PartialProfit => {
                // Positive impact (profit realization)
                Ok(0.3 * modification.new_value)
            },
            ExitModificationType::TimeExit => {
                // Neutral to negative impact (forced exit)
                Ok(-0.1)
            },
            ExitModificationType::NewsProtection => {
                // Moderate positive impact (risk reduction)
                Ok(0.2)
            },
        }
    }

    pub async fn get_modification_stats(&self) -> Result<HashMap<ExitModificationType, u32>> {
        let counts = self.modification_counts.read().await;
        Ok(counts.clone())
    }
}

#[derive(Debug)]
pub struct ExitAuditLogger {
    audit_database: Arc<dyn AuditDatabase>,
    exit_analytics: Arc<ExitAnalytics>,
}

impl ExitAuditLogger {
    pub fn new() -> Self {
        let audit_database = Arc::new(InMemoryAuditDatabase::new());
        let exit_analytics = Arc::new(ExitAnalytics::new());
        
        Self {
            audit_database,
            exit_analytics,
        }
    }

    pub fn with_database(audit_database: Arc<dyn AuditDatabase>) -> Self {
        let exit_analytics = Arc::new(ExitAnalytics::new());
        
        Self {
            audit_database,
            exit_analytics,
        }
    }

    pub async fn log_exit_modification(&self, modification: ExitModification) -> Result<AuditEntry> {
        let performance_impact = self.calculate_performance_impact(&modification).await?;
        
        let audit_entry = AuditEntry {
            entry_id: Uuid::new_v4(),
            position_id: modification.position_id,
            modification_type: modification.modification_type.clone(),
            old_value: modification.old_value,
            new_value: modification.new_value,
            reasoning: modification.reasoning.clone(),
            market_context: modification.market_context.clone(),
            performance_impact,
            timestamp: Utc::now(),
        };

        // Store in audit database
        self.audit_database.store_audit_entry(&audit_entry).await
            .context("Failed to store audit entry")?;

        // Update analytics
        self.exit_analytics.record_modification(&modification).await
            .context("Failed to update exit analytics")?;

        info!(
            "Exit modification logged: Position {}, Type: {:?}, {} -> {}, Reason: {}",
            modification.position_id,
            modification.modification_type,
            modification.old_value,
            modification.new_value,
            modification.reasoning
        );

        Ok(audit_entry)
    }

    async fn calculate_performance_impact(&self, modification: &ExitModification) -> Result<f64> {
        // More sophisticated performance impact calculation
        let price_change = modification.new_value - modification.old_value;
        let market_volatility = modification.market_context.volatility;
        
        Ok(match modification.modification_type {
            ExitModificationType::TrailingStop => {
                // Impact based on how much profit protection was increased
                let protection_improvement = price_change.abs() / modification.market_context.current_price;
                protection_improvement * 100.0 // Convert to basis points
            },
            ExitModificationType::BreakEven => {
                // Fixed high positive impact for eliminating downside risk
                50.0 // 50 basis points
            },
            ExitModificationType::PartialProfit => {
                // Impact based on profit realization relative to market volatility
                (modification.new_value / modification.old_value - 1.0) / market_volatility * 10.0
            },
            ExitModificationType::TimeExit => {
                // Negative impact proportional to how far from entry price
                let exit_distance = (modification.new_value - modification.old_value).abs();
                -(exit_distance / modification.market_context.current_price * 100.0)
            },
            ExitModificationType::NewsProtection => {
                // Positive impact for risk reduction, scaled by volatility expectation
                20.0 * market_volatility * 100.0
            },
        })
    }

    pub async fn generate_exit_performance_report(&self, time_range: TimeRange) -> Result<ExitPerformanceReport> {
        let audit_entries = self.audit_database.get_entries_in_range(time_range.clone()).await?;
        
        let mut report = ExitPerformanceReport {
            trailing_stop_stats: TrailingStopStats {
                total_trails: 0,
                successful_exits: 0,
                average_trail_distance: 0.0,
                profit_captured: Decimal::ZERO,
                best_trail_profit: Decimal::ZERO,
                worst_trail_loss: Decimal::ZERO,
            },
            break_even_stats: BreakEvenStats {
                break_even_activations: 0,
                successful_break_evens: 0,
                losses_prevented: Decimal::ZERO,
                average_time_to_break_even: Duration::from_std(std::time::Duration::from_secs(2 * 3600)).unwrap(),
            },
            partial_profit_stats: PartialProfitStats {
                total_partials: 0,
                total_volume_closed: Decimal::ZERO,
                average_profit_per_partial: Decimal::ZERO,
                target_hit_rates: HashMap::new(),
            },
            time_exit_stats: TimeExitStats {
                time_exits_triggered: 0,
                average_hold_time: Duration::from_std(std::time::Duration::from_secs(12 * 3600)).unwrap(),
                trend_overrides: 0,
                time_exit_pnl: Decimal::ZERO,
            },
            news_protection_stats: NewsProtectionStats {
                protections_applied: 0,
                positions_closed_pre_news: 0,
                stops_tightened: 0,
                protection_effectiveness: 0.0,
            },
            overall_performance: 0.0,
            report_period: ReportPeriod {
                start: time_range.start,
                end: time_range.end,
            },
        };

        // Analyze each exit type
        self.analyze_trailing_stop_performance(&audit_entries, &mut report).await?;
        self.analyze_break_even_performance(&audit_entries, &mut report).await?;
        self.analyze_partial_profit_performance(&audit_entries, &mut report).await?;
        self.analyze_time_exit_performance(&audit_entries, &mut report).await?;
        self.analyze_news_protection_performance(&audit_entries, &mut report).await?;

        // Calculate overall performance
        report.overall_performance = self.calculate_overall_performance(&audit_entries).await?;

        Ok(report)
    }

    async fn analyze_trailing_stop_performance(&self, entries: &[AuditEntry], report: &mut ExitPerformanceReport) -> Result<()> {
        let trailing_entries: Vec<&AuditEntry> = entries
            .iter()
            .filter(|e| matches!(e.modification_type, ExitModificationType::TrailingStop))
            .collect();

        report.trailing_stop_stats.total_trails = trailing_entries.len() as u32;
        
        if !trailing_entries.is_empty() {
            let total_distance: f64 = trailing_entries
                .iter()
                .map(|e| (e.new_value - e.old_value).abs())
                .sum();
            
            report.trailing_stop_stats.average_trail_distance = total_distance / trailing_entries.len() as f64;
            
            // Calculate profit captured (simplified)
            let total_impact: f64 = trailing_entries
                .iter()
                .map(|e| e.performance_impact)
                .sum();
            
            report.trailing_stop_stats.profit_captured = Decimal::from_f64_retain(total_impact).unwrap_or(Decimal::ZERO);
        }

        Ok(())
    }

    async fn analyze_break_even_performance(&self, entries: &[AuditEntry], report: &mut ExitPerformanceReport) -> Result<()> {
        let break_even_entries: Vec<&AuditEntry> = entries
            .iter()
            .filter(|e| matches!(e.modification_type, ExitModificationType::BreakEven))
            .collect();

        report.break_even_stats.break_even_activations = break_even_entries.len() as u32;
        
        // Simplified success calculation
        report.break_even_stats.successful_break_evens = break_even_entries.len() as u32;
        
        let total_impact: f64 = break_even_entries
            .iter()
            .map(|e| e.performance_impact)
            .sum();
        
        report.break_even_stats.losses_prevented = Decimal::from_f64_retain(total_impact * 10.0).unwrap_or(Decimal::ZERO);

        Ok(())
    }

    async fn analyze_partial_profit_performance(&self, entries: &[AuditEntry], report: &mut ExitPerformanceReport) -> Result<()> {
        let partial_entries: Vec<&AuditEntry> = entries
            .iter()
            .filter(|e| matches!(e.modification_type, ExitModificationType::PartialProfit))
            .collect();

        report.partial_profit_stats.total_partials = partial_entries.len() as u32;
        
        if !partial_entries.is_empty() {
            let total_volume: f64 = partial_entries
                .iter()
                .map(|e| e.new_value)
                .sum();
            
            report.partial_profit_stats.total_volume_closed = Decimal::from_f64_retain(total_volume).unwrap_or(Decimal::ZERO);
            
            let average_profit = partial_entries
                .iter()
                .map(|e| e.performance_impact)
                .sum::<f64>() / partial_entries.len() as f64;
            
            report.partial_profit_stats.average_profit_per_partial = Decimal::from_f64_retain(average_profit).unwrap_or(Decimal::ZERO);
        }

        Ok(())
    }

    async fn analyze_time_exit_performance(&self, entries: &[AuditEntry], report: &mut ExitPerformanceReport) -> Result<()> {
        let time_exit_entries: Vec<&AuditEntry> = entries
            .iter()
            .filter(|e| matches!(e.modification_type, ExitModificationType::TimeExit))
            .collect();

        report.time_exit_stats.time_exits_triggered = time_exit_entries.len() as u32;
        
        let total_pnl: f64 = time_exit_entries
            .iter()
            .map(|e| e.performance_impact)
            .sum();
        
        report.time_exit_stats.time_exit_pnl = Decimal::from_f64_retain(total_pnl).unwrap_or(Decimal::ZERO);

        Ok(())
    }

    async fn analyze_news_protection_performance(&self, entries: &[AuditEntry], report: &mut ExitPerformanceReport) -> Result<()> {
        let news_entries: Vec<&AuditEntry> = entries
            .iter()
            .filter(|e| matches!(e.modification_type, ExitModificationType::NewsProtection))
            .collect();

        report.news_protection_stats.protections_applied = news_entries.len() as u32;
        
        // Count different types of news protections based on reasoning
        let (tightened, closed) = news_entries
            .iter()
            .fold((0, 0), |(tight, close), entry| {
                if entry.reasoning.contains("tightened") {
                    (tight + 1, close)
                } else if entry.reasoning.contains("closed") {
                    (tight, close + 1)
                } else {
                    (tight, close)
                }
            });
        
        report.news_protection_stats.stops_tightened = tightened;
        report.news_protection_stats.positions_closed_pre_news = closed;
        
        // Calculate effectiveness (simplified)
        if !news_entries.is_empty() {
            let average_impact = news_entries
                .iter()
                .map(|e| e.performance_impact)
                .sum::<f64>() / news_entries.len() as f64;
            
            report.news_protection_stats.protection_effectiveness = (average_impact / 50.0).max(0.0).min(1.0);
        }

        Ok(())
    }

    async fn calculate_overall_performance(&self, entries: &[AuditEntry]) -> Result<f64> {
        if entries.is_empty() {
            return Ok(0.0);
        }

        let total_impact: f64 = entries.iter().map(|e| e.performance_impact).sum();
        let weighted_performance = total_impact / entries.len() as f64;
        
        Ok(weighted_performance)
    }

    pub async fn create_exit_replay(&self, position_id: PositionId) -> Result<ExitReplay> {
        let exit_history = self.audit_database.get_position_exit_history(position_id).await?;
        
        let replay = ExitReplay {
            position_id,
            exit_timeline: self.build_exit_timeline(&exit_history).await?,
            decision_points: self.extract_decision_points(&exit_history).await?,
            market_context_evolution: self.track_market_context_changes(&exit_history).await?,
            performance_attribution: self.calculate_performance_attribution(&exit_history).await?,
            lessons_learned: self.extract_lessons_learned(&exit_history).await?,
        };

        Ok(replay)
    }

    async fn build_exit_timeline(&self, history: &[AuditEntry]) -> Result<Vec<ExitTimelineEvent>> {
        let mut timeline: Vec<ExitTimelineEvent> = history
            .iter()
            .map(|entry| ExitTimelineEvent {
                timestamp: entry.timestamp,
                event_type: entry.modification_type.clone(),
                description: entry.reasoning.clone(),
                old_value: entry.old_value,
                new_value: entry.new_value,
                impact: entry.performance_impact,
                market_price: entry.market_context.current_price,
            })
            .collect();

        timeline.sort_by(|a, b| a.timestamp.cmp(&b.timestamp));
        Ok(timeline)
    }

    async fn extract_decision_points(&self, history: &[AuditEntry]) -> Result<Vec<DecisionPoint>> {
        let decision_points: Vec<DecisionPoint> = history
            .iter()
            .map(|entry| DecisionPoint {
                timestamp: entry.timestamp,
                decision_type: entry.modification_type.clone(),
                reasoning: entry.reasoning.clone(),
                market_conditions: entry.market_context.clone(),
                outcome_impact: entry.performance_impact,
            })
            .collect();

        Ok(decision_points)
    }

    async fn track_market_context_changes(&self, history: &[AuditEntry]) -> Result<Vec<MarketContext>> {
        let contexts: Vec<MarketContext> = history
            .iter()
            .map(|entry| entry.market_context.clone())
            .collect();

        Ok(contexts)
    }

    async fn calculate_performance_attribution(&self, history: &[AuditEntry]) -> Result<PerformanceAttribution> {
        let mut attribution = PerformanceAttribution {
            trailing_stop_contribution: 0.0,
            break_even_contribution: 0.0,
            partial_profit_contribution: 0.0,
            time_exit_contribution: 0.0,
            news_protection_contribution: 0.0,
            total_impact: 0.0,
        };

        for entry in history {
            let impact = entry.performance_impact;
            match entry.modification_type {
                ExitModificationType::TrailingStop => attribution.trailing_stop_contribution += impact,
                ExitModificationType::BreakEven => attribution.break_even_contribution += impact,
                ExitModificationType::PartialProfit => attribution.partial_profit_contribution += impact,
                ExitModificationType::TimeExit => attribution.time_exit_contribution += impact,
                ExitModificationType::NewsProtection => attribution.news_protection_contribution += impact,
            }
            attribution.total_impact += impact;
        }

        Ok(attribution)
    }

    async fn extract_lessons_learned(&self, history: &[AuditEntry]) -> Result<Vec<String>> {
        let mut lessons = Vec::new();

        // Analyze patterns and generate insights
        if history.len() > 5 {
            lessons.push("Position had extensive exit management activity".to_string());
        }

        let trailing_count = history.iter().filter(|e| matches!(e.modification_type, ExitModificationType::TrailingStop)).count();
        if trailing_count > 3 {
            lessons.push("Frequent trailing stop adjustments - consider wider initial trails".to_string());
        }

        let news_protections = history.iter().filter(|e| matches!(e.modification_type, ExitModificationType::NewsProtection)).count();
        if news_protections > 0 {
            lessons.push("Position was exposed to news events - consider news calendar integration".to_string());
        }

        let average_impact: f64 = history.iter().map(|e| e.performance_impact).sum::<f64>() / history.len() as f64;
        if average_impact > 10.0 {
            lessons.push("Exit management added significant value to this position".to_string());
        } else if average_impact < -5.0 {
            lessons.push("Exit management may have been counterproductive - review triggers".to_string());
        }

        Ok(lessons)
    }

    pub async fn log_emergency_close_event(&self, reason: String) -> Result<()> {
        self.audit_database.store_emergency_close_event(reason, Utc::now()).await?;
        Ok(())
    }

    pub async fn get_recent_exits(&self, limit: u32) -> Result<Vec<AuditEntry>> {
        let now = Utc::now();
        let one_week_ago = now - Duration::from_std(std::time::Duration::from_secs(7 * 24 * 3600)).unwrap();
        
        let time_range = TimeRange {
            start: one_week_ago,
            end: now,
        };
        
        let mut entries = self.audit_database.get_entries_in_range(time_range).await?;
        entries.sort_by(|a, b| b.timestamp.cmp(&a.timestamp));
        entries.truncate(limit as usize);
        
        Ok(entries)
    }

    pub async fn get_exits_by_type(&self, modification_type: ExitModificationType, limit: Option<u32>) -> Result<Vec<AuditEntry>> {
        self.audit_database.get_entries_by_type(modification_type, limit).await
    }
}

// Additional types for exit replay functionality
#[derive(Debug, Clone)]
pub struct ExitReplay {
    pub position_id: PositionId,
    pub exit_timeline: Vec<ExitTimelineEvent>,
    pub decision_points: Vec<DecisionPoint>,
    pub market_context_evolution: Vec<MarketContext>,
    pub performance_attribution: PerformanceAttribution,
    pub lessons_learned: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct ExitTimelineEvent {
    pub timestamp: DateTime<Utc>,
    pub event_type: ExitModificationType,
    pub description: String,
    pub old_value: f64,
    pub new_value: f64,
    pub impact: f64,
    pub market_price: f64,
}

#[derive(Debug, Clone)]
pub struct DecisionPoint {
    pub timestamp: DateTime<Utc>,
    pub decision_type: ExitModificationType,
    pub reasoning: String,
    pub market_conditions: MarketContext,
    pub outcome_impact: f64,
}

#[derive(Debug, Clone)]
pub struct PerformanceAttribution {
    pub trailing_stop_contribution: f64,
    pub break_even_contribution: f64,
    pub partial_profit_contribution: f64,
    pub time_exit_contribution: f64,
    pub news_protection_contribution: f64,
    pub total_impact: f64,
}