/**
 * Type definitions for Performance Analytics Dashboard (Story 12.2)
 *
 * Comprehensive types for analytics data, API responses, and component props
 */

/**
 * Date range for filtering analytics data
 */
export interface AnalyticsDateRange {
  start_date: string // ISO format date string
  end_date: string   // ISO format date string
}

/**
 * Session performance metrics
 */
export interface SessionPerformanceMetrics {
  win_rate: number          // Win rate as percentage (0-100)
  total_trades: number      // Total number of trades
  winning_trades: number    // Number of winning trades
  losing_trades: number     // Number of losing trades
}

/**
 * Session performance data mapping
 */
export interface SessionPerformanceData {
  [session: string]: SessionPerformanceMetrics // TOKYO, LONDON, NY, SYDNEY, OVERLAP
}

/**
 * Pattern performance metrics
 */
export interface PatternPerformanceMetrics {
  win_rate: number          // Win rate as percentage (0-100)
  sample_size: number       // Number of trades for this pattern
  significant: boolean      // True if sample_size >= 20
}

/**
 * Pattern performance data mapping
 */
export interface PatternPerformanceData {
  [pattern: string]: PatternPerformanceMetrics // Spring, Upthrust, Accumulation, Distribution
}

/**
 * P&L metrics by currency pair
 */
export interface PnLByPairMetrics {
  total_pnl: number         // Total profit/loss
  trade_count: number       // Number of trades
  avg_pnl: number          // Average P&L per trade
}

/**
 * P&L data mapping by symbol
 */
export interface PnLByPairData {
  [symbol: string]: PnLByPairMetrics // EUR_USD, GBP_USD, USD_JPY, AUD_USD, USD_CHF
}

/**
 * Scatter plot data point for confidence correlation
 */
export interface ConfidenceScatterPoint {
  confidence: number        // Confidence score (0-100)
  outcome: number          // 0 for loss, 1 for win
  symbol: string           // Currency pair
}

/**
 * Confidence correlation data
 */
export interface ConfidenceCorrelationData {
  scatter_data: ConfidenceScatterPoint[]  // Array of data points
  correlation_coefficient: number         // Pearson correlation (-1 to 1)
}

/**
 * Equity curve data point
 */
export interface EquityCurvePoint {
  time: string             // ISO format timestamp
  equity: number           // Account equity at this time
}

/**
 * Drawdown period information
 */
export interface DrawdownPeriod {
  start: string            // ISO format start timestamp
  end: string              // ISO format end timestamp
  amount: number           // Drawdown amount (negative)
  percentage: number       // Drawdown percentage (negative)
}

/**
 * Maximum drawdown information
 */
export interface MaxDrawdown {
  amount: number                  // Max drawdown amount (negative)
  percentage: number              // Max drawdown percentage (negative)
  start: string | null           // ISO format start timestamp
  end: string | null             // ISO format end timestamp
  recovery_duration_days: number // Days to recover from drawdown
}

/**
 * Drawdown analysis data
 */
export interface DrawdownData {
  equity_curve: EquityCurvePoint[]      // Equity curve over time
  drawdown_periods: DrawdownPeriod[]     // All drawdown periods
  max_drawdown: MaxDrawdown              // Maximum drawdown information
}

/**
 * Parameter change record
 */
export interface ParameterChange {
  change_time: string                    // ISO format timestamp
  parameter_mode: string                 // "Session-Targeted" or "Universal"
  session: string | null                // Session name if applicable
  confidence_threshold: number | null   // Confidence threshold value
  min_risk_reward: number | null        // Minimum risk-reward ratio
  reason: string | null                 // Reason for change
  changed_by: 'system_auto' | 'learning_agent' | 'manual' | 'emergency'
}

/**
 * Standard API response wrapper for analytics endpoints
 */
export interface AnalyticsAPIResponse<T> {
  data: T | null
  error: string | null
  correlation_id: string
}

/**
 * Date range preset options
 */
export type DateRangePreset = '7d' | '30d' | '90d' | 'custom'

/**
 * Date range picker state
 */
export interface DateRangePicker {
  preset: DateRangePreset
  custom_start?: string
  custom_end?: string
}

/**
 * Win rate color coding helper type
 */
export type WinRateColor = 'green' | 'yellow' | 'red'

/**
 * Get color based on win rate threshold
 * @param winRate Win rate percentage (0-100)
 * @returns Color classification
 */
export function getWinRateColor(winRate: number): WinRateColor {
  if (winRate > 55) return 'green'
  if (winRate >= 45) return 'yellow'
  return 'red'
}

/**
 * Trading session names
 */
export type TradingSession = 'TOKYO' | 'LONDON' | 'NY' | 'SYDNEY' | 'OVERLAP'

/**
 * Wyckoff pattern types
 */
export type WyckoffPattern = 'Spring' | 'Upthrust' | 'Accumulation' | 'Distribution'

/**
 * Currency pair symbols
 */
export type CurrencyPair = 'EUR_USD' | 'GBP_USD' | 'USD_JPY' | 'AUD_USD' | 'USD_CHF'

/**
 * Correlation strength interpretation
 */
export type CorrelationStrength = 'Strong Positive' | 'Moderate Positive' | 'Weak' | 'Moderate Negative' | 'Strong Negative'

/**
 * Get correlation strength interpretation
 * @param coefficient Pearson correlation coefficient (-1 to 1)
 * @returns Correlation strength description
 */
export function getCorrelationStrength(coefficient: number): CorrelationStrength {
  const abs = Math.abs(coefficient)
  if (abs > 0.7) return coefficient > 0 ? 'Strong Positive' : 'Strong Negative'
  if (abs >= 0.3) return coefficient > 0 ? 'Moderate Positive' : 'Moderate Negative'
  return 'Weak'
}

/**
 * Parameter change type indicator
 */
export interface ParameterChangeIndicator {
  color: 'blue' | 'green' | 'orange' | 'red'
  label: string
}

/**
 * Get parameter change indicator styling
 * @param changedBy Who made the change
 * @returns Color and label for UI display
 */
export function getParameterChangeIndicator(
  changedBy: ParameterChange['changed_by']
): ParameterChangeIndicator {
  switch (changedBy) {
    case 'system_auto':
      return { color: 'blue', label: 'System Auto' }
    case 'learning_agent':
      return { color: 'green', label: 'Learning Agent' }
    case 'manual':
      return { color: 'orange', label: 'Manual' }
    case 'emergency':
      return { color: 'red', label: 'Emergency' }
  }
}

/**
 * Auto-refresh configuration
 */
export interface AutoRefreshConfig {
  enabled: boolean
  interval_seconds: number // Default: 30
}

/**
 * Analytics page state
 */
export interface AnalyticsPageState {
  dateRange: DateRangePicker
  autoRefresh: AutoRefreshConfig
  isExporting: boolean
  lastRefresh: Date | null
}
