/**
 * Position Calculation Utilities
 * Helper functions for position progress, age, and enrichment
 */

import { Position, RawPosition } from '@/types/positions'

/**
 * Calculate progress towards a target price
 * @param entryPrice - Position entry price
 * @param currentPrice - Current market price
 * @param targetPrice - Target price (TP or SL)
 * @param direction - Position direction
 * @returns Progress percentage (0-100)
 */
export function calculateProgressToTarget(
  entryPrice: number,
  currentPrice: number,
  targetPrice: number,
  direction: 'long' | 'short'
): number {
  if (direction === 'long') {
    const totalMove = targetPrice - entryPrice
    const currentMove = currentPrice - entryPrice

    if (totalMove === 0) return 0

    const progress = (currentMove / totalMove) * 100
    return Math.max(0, Math.min(100, progress))
  } else {
    // For short positions, price moving down is profit
    const totalMove = entryPrice - targetPrice
    const currentMove = entryPrice - currentPrice

    if (totalMove === 0) return 0

    const progress = (currentMove / totalMove) * 100
    return Math.max(0, Math.min(100, progress))
  }
}

/**
 * Calculate human-readable position age
 * @param openTime - ISO timestamp when position was opened
 * @returns Human-readable duration (e.g., "2h 34m", "3 days")
 */
export function calculatePositionAge(openTime: string): string {
  const now = new Date()
  const opened = new Date(openTime)
  const diffMs = now.getTime() - opened.getTime()

  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
  const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))

  if (days >= 1) {
    return `${days} day${days > 1 ? 's' : ''}`
  } else if (hours > 0) {
    return `${hours}h ${minutes}m`
  } else {
    return `${minutes}m`
  }
}

/**
 * Check if price is near a target (within threshold)
 * @param currentPrice - Current market price
 * @param targetPrice - Target price
 * @param instrument - Trading instrument
 * @returns True if near target
 */
export function isNearTarget(
  currentPrice: number,
  targetPrice: number,
  instrument: string
): boolean {
  // Define "near" as within 10 pips
  // JPY pairs have different pip values (0.01 vs 0.0001)
  const threshold = instrument.includes('JPY') ? 0.10 : 0.0010
  return Math.abs(currentPrice - targetPrice) <= threshold
}

/**
 * Calculate P&L percentage
 * @param unrealizedPL - Unrealized P&L amount
 * @param entryPrice - Entry price
 * @param units - Position size
 * @returns P&L as percentage
 */
export function calculatePLPercentage(
  unrealizedPL: number,
  entryPrice: number,
  units: number
): number {
  const positionValue = Math.abs(entryPrice * units)
  if (positionValue === 0) return 0
  return (unrealizedPL / positionValue) * 100
}

/**
 * Enrich raw position data with calculated fields
 * @param rawPosition - Raw position from API
 * @param currentPrice - Current market price (optional, defaults to entry price)
 * @returns Enriched position with all calculated fields
 */
export function enrichPosition(
  rawPosition: RawPosition,
  currentPrice?: number
): Position {
  const units = parseFloat(rawPosition.units)
  const direction: 'long' | 'short' = units > 0 ? 'long' : 'short'
  const absUnits = Math.abs(units)
  const entryPrice = parseFloat(rawPosition.price)
  const current = currentPrice || entryPrice
  const unrealizedPL = parseFloat(rawPosition.unrealizedPL)

  const stopLoss = rawPosition.stopLoss ? parseFloat(rawPosition.stopLoss) : undefined
  const takeProfit = rawPosition.takeProfit ? parseFloat(rawPosition.takeProfit) : undefined

  const progressToTP = takeProfit
    ? calculateProgressToTarget(entryPrice, current, takeProfit, direction)
    : 0

  const progressToSL = stopLoss
    ? calculateProgressToTarget(entryPrice, current, stopLoss, direction)
    : 0

  const isNearTP = takeProfit
    ? isNearTarget(current, takeProfit, rawPosition.instrument)
    : false

  const isNearSL = stopLoss
    ? isNearTarget(current, stopLoss, rawPosition.instrument)
    : false

  const unrealizedPLPercentage = calculatePLPercentage(
    unrealizedPL,
    entryPrice,
    absUnits
  )

  return {
    id: rawPosition.id,
    accountId: '', // Will be filled by hook
    instrument: rawPosition.instrument,
    direction,
    units: absUnits,
    entryPrice,
    currentPrice: current,
    stopLoss,
    takeProfit,
    unrealizedPL,
    unrealizedPLPercentage,
    openTime: rawPosition.openTime,
    agentSource: rawPosition.clientExtensions?.agent || 'Unknown',
    positionAge: calculatePositionAge(rawPosition.openTime),
    progressToTP,
    progressToSL,
    isNearTP,
    isNearSL,
  }
}

/**
 * Format instrument name for display
 * @param instrument - Raw instrument name (e.g., "EUR_USD")
 * @returns Formatted name (e.g., "EUR/USD")
 */
export function formatInstrument(instrument: string): string {
  return instrument.replace('_', '/')
}

/**
 * Format price with appropriate precision
 * @param price - Price to format
 * @param instrument - Trading instrument
 * @returns Formatted price string
 */
export function formatPrice(price: number, instrument: string): string {
  // JPY pairs typically use 3 decimal places, others use 5
  const decimals = instrument.includes('JPY') ? 3 : 5
  return price.toFixed(decimals)
}

/**
 * Get pip value for instrument
 * @param instrument - Trading instrument
 * @returns Pip value
 */
export function getPipValue(instrument: string): number {
  return instrument.includes('JPY') ? 0.01 : 0.0001
}
