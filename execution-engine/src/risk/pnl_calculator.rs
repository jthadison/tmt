use crate::risk::types::*;
use anyhow::Result;
use chrono::{DateTime, Utc};
use dashmap::DashMap;
use rust_decimal::Decimal;
use std::sync::Arc;
use tokio::sync::broadcast;
use tracing::{error, info, warn};

pub struct RealTimePnLCalculator {
    position_tracker: Arc<PositionTracker>,
    market_data_stream: Arc<MarketDataStream>,
    pnl_cache: Arc<DashMap<PositionId, PnLSnapshot>>,
    websocket_publisher: Arc<WebSocketPublisher>,
    kafka_producer: Arc<KafkaProducer>,
    pip_values: Arc<DashMap<String, Decimal>>,
}

impl RealTimePnLCalculator {
    pub fn new(
        position_tracker: Arc<PositionTracker>,
        market_data_stream: Arc<MarketDataStream>,
        websocket_publisher: Arc<WebSocketPublisher>,
        kafka_producer: Arc<KafkaProducer>,
    ) -> Self {
        Self {
            position_tracker,
            market_data_stream,
            pnl_cache: Arc::new(DashMap::new()),
            websocket_publisher,
            kafka_producer,
            pip_values: Arc::new(DashMap::new()),
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
        
        for position in positions {
            let updated_pnl = self.calculate_position_pnl(&position, tick).await?;
            
            self.pnl_cache.insert(position.id, updated_pnl.clone());
            
            self.websocket_publisher.publish_pnl_update(PnLUpdate {
                position_id: position.id,
                account_id: position.account_id,
                symbol: position.symbol.clone(),
                unrealized_pnl: updated_pnl.unrealized_pnl,
                unrealized_pnl_percentage: updated_pnl.unrealized_pnl_percentage,
                current_price: tick.price,
                timestamp: tick.timestamp,
            }).await?;
            
            if self.is_significant_pnl_change(&updated_pnl, &position).await? {
                self.publish_pnl_alert(&position, &updated_pnl).await?;
            }
        }
        
        self.update_aggregate_pnl(&tick.symbol).await?;
        
        Ok(())
    }
    
    async fn calculate_position_pnl(&self, position: &Position, tick: &MarketTick) -> Result<PnLSnapshot> {
        let current_price = tick.price;
        let entry_price = position.entry_price;
        let position_size = position.size;
        let pip_value = self.get_pip_value(&position.symbol, position.account_id).await?;
        
        let price_diff = if position.position_type == PositionType::Long {
            current_price - entry_price
        } else {
            entry_price - current_price
        };
        
        let unrealized_pnl = price_diff * position_size * pip_value;
        let unrealized_pnl_percentage = if entry_price != Decimal::ZERO {
            (price_diff / entry_price) * Decimal::from(100) * 
                if position.position_type == PositionType::Long { 
                    Decimal::ONE 
                } else { 
                    Decimal::NEGATIVE_ONE 
                }
        } else {
            Decimal::ZERO
        };
        
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
    
    async fn get_pip_value(&self, symbol: &str, account_id: AccountId) -> Result<Decimal> {
        if let Some(pip_value) = self.pip_values.get(symbol) {
            return Ok(*pip_value);
        }
        
        let pip_value = self.calculate_pip_value(symbol, account_id).await?;
        self.pip_values.insert(symbol.to_string(), pip_value);
        Ok(pip_value)
    }
    
    async fn calculate_pip_value(&self, symbol: &str, _account_id: AccountId) -> Result<Decimal> {
        let pip_value = if symbol.ends_with("JPY") {
            Decimal::from_str_exact("0.01")?
        } else {
            Decimal::from_str_exact("0.0001")?
        };
        
        Ok(pip_value)
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
        
        let aggregate_pnl_percentage = if total_position_value != Decimal::ZERO {
            (total_unrealized_pnl / total_position_value) * Decimal::from(100)
        } else {
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

use rust_decimal_macros::dec;
use serde::{Deserialize, Serialize};