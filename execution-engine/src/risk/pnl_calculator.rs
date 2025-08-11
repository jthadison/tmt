use risk_types::*;
use anyhow::{Result, anyhow};
use chrono::{DateTime, Utc};
use dashmap::DashMap;
use rust_decimal::Decimal;
use rust_decimal_macros::dec;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::broadcast;
use tracing::{error, info, warn};
use futures_util;

#[derive(Debug, thiserror::Error)]
pub enum PnLCalculationError {
    #[error("Invalid entry price: cannot be zero or negative")]
    InvalidEntryPrice,
    #[error("Invalid position size: cannot be zero")]
    InvalidPositionSize,
    #[error("Currency conversion failed for {from} to {to}: {reason}")]
    CurrencyConversionFailed { from: String, to: String, reason: String },
    #[error("Position data inconsistent: {details}")]
    InconsistentPositionData { details: String },
    #[error("Market data unavailable for symbol: {symbol}")]
    MarketDataUnavailable { symbol: String },
}

pub struct RealTimePnLCalculator {
    position_tracker: Arc<PositionTracker>,
    market_data_stream: Arc<MarketDataStream>,
    pnl_cache: Arc<DashMap<PositionId, PnLSnapshot>>,
    websocket_publisher: Arc<WebSocketPublisher>,
    kafka_producer: Arc<KafkaProducer>,
    pip_values: Arc<DashMap<String, Decimal>>,
    currency_converter: Arc<CurrencyConverter>,
}

impl RealTimePnLCalculator {
    pub fn new(
        position_tracker: Arc<PositionTracker>,
        market_data_stream: Arc<MarketDataStream>,
        websocket_publisher: Arc<WebSocketPublisher>,
        kafka_producer: Arc<KafkaProducer>,
        currency_converter: Arc<CurrencyConverter>,
    ) -> Self {
        Self {
            position_tracker,
            market_data_stream,
            pnl_cache: Arc::new(DashMap::new()),
            websocket_publisher,
            kafka_producer,
            pip_values: Arc::new(DashMap::new()),
            currency_converter,
        }
    }

    pub async fn start_pnl_monitoring(&self) -> Result<()> {
        let mut market_data_rx = self.market_data_stream.subscribe().await?;
        info!("Started real-time P&L monitoring");
        
        while let Ok(tick) = market_data_rx.recv().await {
            if let Err(e) = self.process_tick_update(&tick).await {
                error!("Failed to process tick update: {}", e);
                continue;
            }
        }
        
        Ok(())
    }
    
    async fn process_tick_update(&self, tick: &MarketTick) -> Result<()> {
        let positions = self.position_tracker
            .get_positions_by_symbol(&tick.symbol).await?;
        
        if positions.is_empty() {
            return Ok(()); // Early exit for performance
        }
        
        // Batch process all positions for this symbol for better performance
        let mut pnl_updates = Vec::with_capacity(positions.len());
        let mut significant_changes = Vec::new();
        
        // Process all positions in parallel for better performance
        let results = futures_util::future::join_all(
            positions.iter().map(|position| self.calculate_position_pnl(position, tick))
        ).await;
        
        for (position, result) in positions.iter().zip(results.into_iter()) {
            let updated_pnl = result?;
            
            // Cache the result
            self.pnl_cache.insert(position.id, updated_pnl.clone());
            
            // Prepare batch update
            pnl_updates.push(PnLUpdate {
                position_id: position.id,
                account_id: position.account_id,
                symbol: position.symbol.clone(),
                unrealized_pnl: updated_pnl.unrealized_pnl,
                unrealized_pnl_percentage: updated_pnl.unrealized_pnl_percentage,
                current_price: tick.price,
                timestamp: tick.timestamp,
            });
            
            // Check for significant changes
            if self.is_significant_pnl_change(&updated_pnl, position).await? {
                significant_changes.push((position.clone(), updated_pnl));
            }
        }
        
        // Batch publish updates for better performance
        for update in pnl_updates {
            self.websocket_publisher.publish_pnl_update(update).await?;
        }
        
        // Batch publish alerts
        for (position, pnl) in significant_changes {
            self.publish_pnl_alert(&position, &pnl).await?;
        }
        
        self.update_aggregate_pnl(&tick.symbol).await?;
        
        Ok(())
    }
    
    async fn calculate_position_pnl(&self, position: &Position, tick: &MarketTick) -> Result<PnLSnapshot> {
        // Input validation
        if position.entry_price <= Decimal::ZERO {
            return Err(anyhow!(PnLCalculationError::InvalidEntryPrice));
        }
        if position.size == Decimal::ZERO {
            return Err(anyhow!(PnLCalculationError::InvalidPositionSize));
        }
        if tick.price <= Decimal::ZERO {
            return Err(anyhow!(PnLCalculationError::MarketDataUnavailable { 
                symbol: position.symbol.clone() 
            }));
        }

        let current_price = tick.price;
        let entry_price = position.entry_price;
        let position_size = position.size;
        
        // Get pip value with proper currency conversion
        let pip_value = self.get_pip_value_with_conversion(&position.symbol, position.account_id).await?;
        
        // Calculate price difference based on position type
        let price_diff = match position.position_type {
            PositionType::Long => current_price - entry_price,
            PositionType::Short => entry_price - current_price,
        };
        
        // Calculate P&L with currency conversion
        let raw_pnl = price_diff * position_size;
        let unrealized_pnl = self.currency_converter
            .convert_to_account_currency(raw_pnl, &position.symbol, position.account_id)
            .await
            .map_err(|e| anyhow!(PnLCalculationError::CurrencyConversionFailed {
                from: position.symbol.clone(),
                to: "USD".to_string(), // Assuming USD base currency
                reason: e.to_string(),
            }))?;
        
        // Safe percentage calculation with proper error handling
        let unrealized_pnl_percentage = {
            let percentage_base = entry_price * position_size;
            if percentage_base > Decimal::ZERO {
                (unrealized_pnl / percentage_base) * dec!(100)
            } else {
                return Err(anyhow!(PnLCalculationError::InconsistentPositionData {
                    details: "Cannot calculate percentage: position value is zero".to_string()
                }));
            }
        };
        
        // Update MFE/MAE with proper comparison
        let mut max_favorable = position.max_favorable_excursion;
        let mut max_adverse = position.max_adverse_excursion;
        
        if unrealized_pnl > max_favorable {
            max_favorable = unrealized_pnl;
        }
        if unrealized_pnl < max_adverse {
            max_adverse = unrealized_pnl;
        }
        
        Ok(PnLSnapshot {
            position_id: position.id,
            unrealized_pnl,
            unrealized_pnl_percentage,
            max_favorable_excursion: max_favorable,
            max_adverse_excursion: max_adverse,
            current_price,
            timestamp: tick.timestamp,
        })
    }
    
    
    async fn get_pip_value_with_conversion(&self, symbol: &str, account_id: AccountId) -> Result<Decimal> {
        if let Some(pip_value) = self.pip_values.get(symbol) {
            return Ok(*pip_value);
        }
        
        let pip_value = self.calculate_pip_value_with_conversion(symbol, account_id).await?;
        self.pip_values.insert(symbol.to_string(), pip_value);
        Ok(pip_value)
    }
    
    async fn calculate_pip_value_with_conversion(&self, symbol: &str, account_id: AccountId) -> Result<Decimal> {
        // Base pip size calculation
        let base_pip_size = if symbol.ends_with("JPY") {
            dec!(0.01) // 1 pip = 0.01 for JPY pairs
        } else {
            dec!(0.0001) // 1 pip = 0.0001 for most major pairs
        };
        
        // Convert pip value to account currency
        let account_currency = self.get_account_currency(account_id).await?;
        let pip_value = self.currency_converter
            .convert_pip_value(base_pip_size, symbol, &account_currency)
            .await
            .map_err(|e| anyhow!(PnLCalculationError::CurrencyConversionFailed {
                from: symbol.to_string(),
                to: account_currency,
                reason: e.to_string(),
            }))?;
        
        Ok(pip_value)
    }
    
    async fn get_account_currency(&self, account_id: AccountId) -> Result<String> {
        // This should come from account configuration
        // For now, defaulting to USD
        Ok("USD".to_string())
    }
    
    async fn is_significant_pnl_change(&self, pnl: &PnLSnapshot, position: &Position) -> Result<bool> {
        let change_threshold = Decimal::from(5);
        
        if let Some(cached_pnl) = self.pnl_cache.get(&position.id) {
            let pnl_change = (pnl.unrealized_pnl_percentage - cached_pnl.unrealized_pnl_percentage).abs();
            return Ok(pnl_change >= change_threshold);
        }
        
        Ok(pnl.unrealized_pnl_percentage.abs() >= change_threshold)
    }
    
    async fn publish_pnl_alert(&self, position: &Position, pnl: &PnLSnapshot) -> Result<()> {
        let alert_message = format!(
            "Significant P&L change for position {} in {}: {}% ({})",
            position.id,
            position.symbol,
            pnl.unrealized_pnl_percentage,
            pnl.unrealized_pnl
        );
        
        info!("{}", alert_message);
        
        self.kafka_producer.send_event("risk.pnl.alert", &alert_message).await?;
        
        Ok(())
    }
    
    async fn update_aggregate_pnl(&self, symbol: &str) -> Result<()> {
        let positions = self.position_tracker.get_positions_by_symbol(symbol).await?;
        
        let mut total_unrealized_pnl = Decimal::ZERO;
        let mut total_position_value = Decimal::ZERO;
        
        for position in positions {
            if let Some(pnl_snapshot) = self.pnl_cache.get(&position.id) {
                total_unrealized_pnl += pnl_snapshot.unrealized_pnl;
                total_position_value += position.size * position.entry_price;
            }
        }
        
        let aggregate_pnl_percentage = if total_position_value > Decimal::ZERO {
            (total_unrealized_pnl / total_position_value) * dec!(100)
        } else {
            warn!("Cannot calculate aggregate P&L percentage: total position value is zero for symbol {}", symbol);
            Decimal::ZERO
        };
        
        info!(
            "Aggregate P&L for {}: {} ({}%)",
            symbol, total_unrealized_pnl, aggregate_pnl_percentage
        );
        
        Ok(())
    }
    
    pub async fn get_account_pnl(&self, account_id: AccountId) -> Result<AccountPnL> {
        let positions = self.position_tracker.get_account_positions(account_id).await?;
        
        let mut unrealized_pnl = Decimal::ZERO;
        let mut realized_pnl_today = Decimal::ZERO;
        let mut position_pnls = Vec::new();
        
        for position in positions {
            if let Some(pnl_snapshot) = self.pnl_cache.get(&position.id) {
                unrealized_pnl += pnl_snapshot.unrealized_pnl;
                position_pnls.push(pnl_snapshot.clone());
            }
        }
        
        realized_pnl_today = self.position_tracker
            .get_realized_pnl_today(account_id)
            .await?;
        
        Ok(AccountPnL {
            account_id,
            unrealized_pnl,
            realized_pnl_today,
            total_pnl: unrealized_pnl + realized_pnl_today,
            position_pnls,
            timestamp: Utc::now(),
        })
    }
}

pub struct PositionTracker {
    positions: Arc<DashMap<PositionId, Position>>,
    account_positions: Arc<DashMap<AccountId, Vec<PositionId>>>,
    symbol_positions: Arc<DashMap<String, Vec<PositionId>>>,
}

impl PositionTracker {
    pub fn new() -> Self {
        Self {
            positions: Arc::new(DashMap::new()),
            account_positions: Arc::new(DashMap::new()),
            symbol_positions: Arc::new(DashMap::new()),
        }
    }
    
    pub async fn get_positions_by_symbol(&self, symbol: &str) -> Result<Vec<Position>> {
        let position_ids = self.symbol_positions
            .get(symbol)
            .map(|ids| ids.clone())
            .unwrap_or_default();
        
        let mut positions = Vec::new();
        for id in position_ids {
            if let Some(position) = self.positions.get(&id) {
                positions.push(position.clone());
            }
        }
        
        Ok(positions)
    }
    
    pub async fn get_account_positions(&self, account_id: AccountId) -> Result<Vec<Position>> {
        let position_ids = self.account_positions
            .get(&account_id)
            .map(|ids| ids.clone())
            .unwrap_or_default();
        
        let mut positions = Vec::new();
        for id in position_ids {
            if let Some(position) = self.positions.get(&id) {
                positions.push(position.clone());
            }
        }
        
        Ok(positions)
    }
    
    pub async fn get_all_open_positions(&self) -> Result<Vec<Position>> {
        Ok(self.positions.iter().map(|entry| entry.value().clone()).collect())
    }
    
    pub async fn get_realized_pnl_today(&self, _account_id: AccountId) -> Result<Decimal> {
        Ok(Decimal::ZERO)
    }
}

pub struct MarketDataStream {
    sender: broadcast::Sender<MarketTick>,
}

impl MarketDataStream {
    pub fn new() -> Self {
        let (sender, _) = broadcast::channel(1000);
        Self { sender }
    }
    
    pub async fn subscribe(&self) -> Result<broadcast::Receiver<MarketTick>> {
        Ok(self.sender.subscribe())
    }
    
    pub async fn publish_tick(&self, tick: MarketTick) -> Result<()> {
        self.sender.send(tick).map_err(|e| anyhow::anyhow!("Failed to send tick: {:?}", e))?;
        Ok(())
    }
}

pub struct WebSocketPublisher {
    connections: Arc<DashMap<AccountId, tokio::sync::mpsc::Sender<String>>>,
}

impl WebSocketPublisher {
    pub fn new() -> Self {
        Self {
            connections: Arc::new(DashMap::new()),
        }
    }
    
    pub async fn publish_pnl_update(&self, update: PnLUpdate) -> Result<()> {
        let message = serde_json::to_string(&update)?;
        
        if let Some(sender) = self.connections.get(&update.account_id) {
            if let Err(e) = sender.send(message).await {
                warn!("Failed to send P&L update to account {}: {}", update.account_id, e);
            }
        }
        
        Ok(())
    }
}

pub struct KafkaProducer;

impl KafkaProducer {
    pub async fn send_event(&self, topic: &str, message: &str) -> Result<()> {
        info!("Kafka event to {}: {}", topic, message);
        Ok(())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AccountPnL {
    pub account_id: AccountId,
    pub unrealized_pnl: Decimal,
    pub realized_pnl_today: Decimal,
    pub total_pnl: Decimal,
    pub position_pnls: Vec<PnLSnapshot>,
    pub timestamp: DateTime<Utc>,
}

/// Currency converter for handling multi-currency P&L calculations
pub struct CurrencyConverter {
    exchange_rates: Arc<DashMap<String, Decimal>>,
    rate_cache_duration: chrono::Duration,
}

impl CurrencyConverter {
    pub fn new() -> Self {
        Self {
            exchange_rates: Arc::new(DashMap::new()),
            rate_cache_duration: chrono::Duration::minutes(1), // Cache rates for 1 minute
        }
    }
    
    pub async fn convert_to_account_currency(
        &self, 
        amount: Decimal, 
        from_symbol: &str, 
        account_id: AccountId
    ) -> Result<Decimal> {
        // Extract currencies from symbol (e.g., "EURUSD" -> base: EUR, quote: USD)
        let (base_currency, quote_currency) = self.parse_currency_pair(from_symbol)?;
        let account_currency = "USD"; // This should come from account configuration
        
        // If already in account currency, no conversion needed
        if quote_currency == account_currency {
            return Ok(amount);
        }
        
        // Get conversion rate
        let rate = self.get_exchange_rate(&quote_currency, account_currency).await?;
        Ok(amount * rate)
    }
    
    pub async fn convert_pip_value(
        &self,
        base_pip_size: Decimal,
        symbol: &str,
        target_currency: &str,
    ) -> Result<Decimal> {
        let (_, quote_currency) = self.parse_currency_pair(symbol)?;
        
        if quote_currency == target_currency {
            return Ok(base_pip_size);
        }
        
        let rate = self.get_exchange_rate(&quote_currency, target_currency).await?;
        Ok(base_pip_size * rate)
    }
    
    fn parse_currency_pair(&self, symbol: &str) -> Result<(String, String)> {
        if symbol.len() != 6 {
            return Err(anyhow!("Invalid currency pair format: {}", symbol));
        }
        
        let base = symbol[0..3].to_uppercase();
        let quote = symbol[3..6].to_uppercase();
        
        Ok((base, quote))
    }
    
    async fn get_exchange_rate(&self, from: &str, to: &str) -> Result<Decimal> {
        let rate_key = format!("{}/{}", from, to);
        
        // Check cache first
        if let Some(cached_rate) = self.exchange_rates.get(&rate_key) {
            return Ok(*cached_rate);
        }
        
        // Fetch fresh rate (in production, this would call external API)
        let rate = self.fetch_exchange_rate(from, to).await?;
        
        // Cache the rate
        self.exchange_rates.insert(rate_key, rate);
        
        Ok(rate)
    }
    
    async fn fetch_exchange_rate(&self, from: &str, to: &str) -> Result<Decimal> {
        // In production, this would call external exchange rate API
        // For now, return mock rates
        match (from, to) {
            ("EUR", "USD") => Ok(dec!(1.0850)),
            ("GBP", "USD") => Ok(dec!(1.2650)),
            ("JPY", "USD") => Ok(dec!(0.0067)),
            ("USD", "EUR") => Ok(dec!(0.9217)),
            ("USD", "GBP") => Ok(dec!(0.7905)),
            ("USD", "JPY") => Ok(dec!(149.50)),
            _ => {
                warn!("Exchange rate not available for {}/{}, using 1.0", from, to);
                Ok(dec!(1.0))
            }
        }
    }
}