/**
 * Centralized Trading Instruments Configuration for Dashboard
 * 
 * This module provides the official list of tradeable instruments for the dashboard.
 * Synced with shared/config/instruments.py for consistency.
 */

export enum InstrumentCategory {
  MAJOR_PAIRS = "major_pairs",
  MINOR_PAIRS = "minor_pairs",
  EXOTIC_PAIRS = "exotic_pairs",
  COMMODITIES = "commodities",
  INDICES = "indices"
}

export interface InstrumentInfo {
  symbol: string
  name: string
  category: InstrumentCategory
  pipPrecision: number
  minTradeSize: number
  maxTradeSize: number
  enabled: boolean
}

// Official list of supported trading instruments
export const INSTRUMENTS: Record<string, InstrumentInfo> = {
  // Major Currency Pairs - Primary Focus
  EUR_USD: {
    symbol: "EUR_USD",
    name: "Euro / US Dollar",
    category: InstrumentCategory.MAJOR_PAIRS,
    pipPrecision: 4,
    minTradeSize: 0.01,
    maxTradeSize: 100.0,
    enabled: true
  },
  GBP_USD: {
    symbol: "GBP_USD", 
    name: "British Pound / US Dollar",
    category: InstrumentCategory.MAJOR_PAIRS,
    pipPrecision: 4,
    minTradeSize: 0.01,
    maxTradeSize: 100.0,
    enabled: true
  },
  USD_CHF: {
    symbol: "USD_CHF",
    name: "US Dollar / Swiss Franc", 
    category: InstrumentCategory.MAJOR_PAIRS,
    pipPrecision: 4,
    minTradeSize: 0.01,
    maxTradeSize: 100.0,
    enabled: true
  },
  AUD_USD: {
    symbol: "AUD_USD",
    name: "Australian Dollar / US Dollar",
    category: InstrumentCategory.MAJOR_PAIRS,
    pipPrecision: 4,
    minTradeSize: 0.01,
    maxTradeSize: 100.0,
    enabled: true
  },
  USD_CAD: {
    symbol: "USD_CAD",
    name: "US Dollar / Canadian Dollar",
    category: InstrumentCategory.MAJOR_PAIRS,
    pipPrecision: 4,
    minTradeSize: 0.01,
    maxTradeSize: 100.0,
    enabled: true
  },
  NZD_USD: {
    symbol: "NZD_USD",
    name: "New Zealand Dollar / US Dollar",
    category: InstrumentCategory.MAJOR_PAIRS,
    pipPrecision: 4,
    minTradeSize: 0.01,
    maxTradeSize: 100.0,
    enabled: true
  },
  
  // USD_JPY - Special precision handling (2 decimal places)
  USD_JPY: {
    symbol: "USD_JPY",
    name: "US Dollar / Japanese Yen", 
    category: InstrumentCategory.MAJOR_PAIRS,
    pipPrecision: 2,  // JPY pairs use 2 decimal places
    minTradeSize: 0.01,
    maxTradeSize: 100.0,
    enabled: true  // Re-enabled: precision handling is properly implemented
  },
  
  // Cross Currency Pairs
  EUR_GBP: {
    symbol: "EUR_GBP",
    name: "Euro / British Pound",
    category: InstrumentCategory.MINOR_PAIRS,
    pipPrecision: 4,
    minTradeSize: 0.01,
    maxTradeSize: 100.0,
    enabled: true
  }
}

/**
 * Get list of currently enabled instrument symbols
 */
export function getActiveInstruments(): string[] {
  return Object.keys(INSTRUMENTS).filter(symbol => INSTRUMENTS[symbol].enabled)
}

/**
 * Get instruments filtered by category
 */
export function getInstrumentsByCategory(category: InstrumentCategory): string[] {
  return Object.keys(INSTRUMENTS).filter(symbol => 
    INSTRUMENTS[symbol].category === category && INSTRUMENTS[symbol].enabled
  )
}

/**
 * Get list of major currency pairs
 */
export function getMajorPairs(): string[] {
  return getInstrumentsByCategory(InstrumentCategory.MAJOR_PAIRS)
}

/**
 * Get detailed information about an instrument
 */
export function getInstrumentInfo(symbol: string): InstrumentInfo {
  if (!(symbol in INSTRUMENTS)) {
    throw new Error(`Unknown instrument: ${symbol}`)
  }
  return INSTRUMENTS[symbol]
}

/**
 * Check if an instrument is enabled for trading
 */
export function isInstrumentEnabled(symbol: string): boolean {
  return symbol in INSTRUMENTS && INSTRUMENTS[symbol].enabled
}

/**
 * Get pip precision for an instrument
 */
export function getInstrumentPrecision(symbol: string): number {
  return getInstrumentInfo(symbol).pipPrecision
}

// Constants for backward compatibility
export const DEFAULT_INSTRUMENTS = getActiveInstruments()
export const MAJOR_PAIRS = getMajorPairs()

// Active monitoring instruments (for market analysis agents)
export const ACTIVE_MONITORING_INSTRUMENTS = [
  "EUR_USD", "GBP_USD", "USD_JPY", "USD_CHF", "AUD_USD", "NZD_USD", "EUR_GBP"
]

// Core trading instruments (most reliable for signal generation)
export const CORE_TRADING_INSTRUMENTS = [
  "EUR_USD", "GBP_USD", "USD_JPY", "USD_CHF", "AUD_USD"
]