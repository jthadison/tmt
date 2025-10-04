/**
 * Performance Metrics Type Definitions
 * Types for win rate, profit factor, trade statistics, and equity tracking
 */

/**
 * Performance metrics data structure
 */
export interface PerformanceMetrics {
  /** Win rate percentage (0-100) */
  winRate: number
  /** Profit factor (gross profit / gross loss) */
  profitFactor: number
  /** Average winning trade amount */
  avgWin: number
  /** Average losing trade amount */
  avgLoss: number
  /** Average risk-reward ratio */
  avgRiskReward: number
  /** Average trade duration in hours */
  avgDurationHours: number
}

/**
 * Profit factor interpretation
 */
export type ProfitFactorRating = 'excellent' | 'good' | 'fair' | 'poor'

/**
 * Profit factor display data
 */
export interface ProfitFactorDisplay {
  /** Profit factor value */
  value: number
  /** Rating based on value */
  rating: ProfitFactorRating
  /** Display color */
  color: string
  /** Interpretation label */
  label: string
}

/**
 * Average trade metrics comparison
 */
export interface TradeMetricsComparison {
  /** Current period average win */
  currentAvgWin: number
  /** Previous period average win */
  previousAvgWin: number
  /** Current period average loss */
  currentAvgLoss: number
  /** Previous period average loss */
  previousAvgLoss: number
  /** Current period average R:R */
  currentAvgRR: number
  /** Previous period average R:R */
  previousAvgRR: number
  /** Current period average duration */
  currentAvgDuration: number
  /** Previous period average duration */
  previousAvgDuration: number
}

/**
 * Equity curve data point
 */
export interface EquityPoint {
  /** Date */
  date: string
  /** Account equity at this date */
  equity: number
  /** Daily P&L */
  dailyPnL: number
  /** Current drawdown percentage */
  drawdown?: number
}

/**
 * Equity curve milestone markers
 */
export interface EquityMilestone {
  /** Date of milestone */
  date: string
  /** Equity value at milestone */
  equity: number
  /** Milestone type */
  type: 'peak' | 'trough' | 'drawdown'
}

/**
 * Equity curve data structure
 */
export interface EquityCurveData {
  /** Array of equity points */
  points: EquityPoint[]
  /** Peak equity point */
  peak: EquityPoint | null
  /** Trough equity point (lowest after peak) */
  trough: EquityPoint | null
  /** Current drawdown percentage */
  currentDrawdown: number
  /** Maximum drawdown percentage */
  maxDrawdown: number
}

/**
 * Win rate gauge zone
 */
export type WinRateZone = 'poor' | 'average' | 'good'

/**
 * Win rate gauge data
 */
export interface WinRateGaugeData {
  /** Win rate percentage */
  percentage: number
  /** Color zone */
  zone: WinRateZone
  /** Display color */
  color: string
}

/**
 * Metrics period for comparison
 */
export type MetricsPeriod = '7d' | '30d' | '90d' | 'all'

/**
 * Performance metrics API response
 */
export interface PerformanceMetricsResponse {
  /** Current period metrics */
  current: PerformanceMetrics
  /** Previous period metrics (for comparison) */
  previous?: PerformanceMetrics
}

/**
 * Equity curve API response
 */
export interface EquityCurveResponse {
  /** Equity curve data */
  data: EquityPoint[]
}

/**
 * CSV export data structure
 */
export interface SessionCSVData {
  session: string
  totalPnL: number
  tradeCount: number
  winRate: number
  confidenceThreshold: number
}
