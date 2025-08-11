// Standalone types for the risk module that don't depend on platform abstraction
use chrono::{DateTime, Utc};
use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

pub type AccountId = Uuid;
pub type PositionId = Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StandalonePosition {
    pub id: PositionId,
    pub account_id: AccountId,
    pub symbol: String,
    pub position_type: StandalonePositionType,
    pub size: Decimal,
    pub entry_price: Decimal,
    pub current_price: Option<Decimal>,
    pub unrealized_pnl: Option<Decimal>,
    pub max_favorable_excursion: Decimal,
    pub max_adverse_excursion: Decimal,
    pub stop_loss: Option<Decimal>,
    pub take_profit: Option<Decimal>,
    pub opened_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum StandalonePositionType {
    Long,
    Short,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StandaloneAccount {
    pub id: AccountId,
    pub balance: Decimal,
    pub equity: Decimal,
    pub active: bool,
    pub last_updated: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StandaloneMarketTick {
    pub symbol: String,
    pub bid: Decimal,
    pub ask: Decimal,
    pub price: Decimal,
    pub volume: Decimal,
    pub timestamp: DateTime<Utc>,
}

// Convert from platform types to standalone types
impl From<risk_types::Position> for StandalonePosition {
    fn from(pos: risk_types::Position) -> Self {
        Self {
            id: pos.id,
            account_id: pos.account_id,
            symbol: pos.symbol,
            position_type: match pos.position_type {
                risk_types::PositionType::Long => StandalonePositionType::Long,
                risk_types::PositionType::Short => StandalonePositionType::Short,
            },
            size: pos.size,
            entry_price: pos.entry_price,
            current_price: pos.current_price,
            unrealized_pnl: pos.unrealized_pnl,
            max_favorable_excursion: pos.max_favorable_excursion,
            max_adverse_excursion: pos.max_adverse_excursion,
            stop_loss: pos.stop_loss,
            take_profit: pos.take_profit,
            opened_at: pos.opened_at,
        }
    }
}

impl From<StandalonePosition> for risk_types::Position {
    fn from(pos: StandalonePosition) -> Self {
        Self {
            id: pos.id,
            account_id: pos.account_id,
            symbol: pos.symbol,
            position_type: match pos.position_type {
                StandalonePositionType::Long => risk_types::PositionType::Long,
                StandalonePositionType::Short => risk_types::PositionType::Short,
            },
            size: pos.size,
            entry_price: pos.entry_price,
            current_price: pos.current_price,
            unrealized_pnl: pos.unrealized_pnl,
            max_favorable_excursion: pos.max_favorable_excursion,
            max_adverse_excursion: pos.max_adverse_excursion,
            stop_loss: pos.stop_loss,
            take_profit: pos.take_profit,
            opened_at: pos.opened_at,
        }
    }
}

impl From<risk_types::MarketTick> for StandaloneMarketTick {
    fn from(tick: risk_types::MarketTick) -> Self {
        Self {
            symbol: tick.symbol,
            bid: tick.bid,
            ask: tick.ask,
            price: tick.price,
            volume: tick.volume,
            timestamp: tick.timestamp,
        }
    }
}

impl From<StandaloneMarketTick> for risk_types::MarketTick {
    fn from(tick: StandaloneMarketTick) -> Self {
        Self {
            symbol: tick.symbol,
            bid: tick.bid,
            ask: tick.ask,
            price: tick.price,
            volume: tick.volume,
            timestamp: tick.timestamp,
        }
    }
}