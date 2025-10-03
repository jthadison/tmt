/**
 * Performance and P&L Type Definitions
 * Types for real-time P&L tracking, performance metrics, and trade analytics
 */

/**
 * Period types for performance comparison
 */
export type PeriodType = 'today' | 'week' | 'month' | 'all'

/**
 * P&L breakdown data structure
 */
export interface PnLBreakdown {
  /** Realized profit/loss */
  realizedPnL: number
  /** Unrealized profit/loss (open positions) */
  unrealizedPnL: number
  /** Total P&L (realized + unrealized) */
  totalPnL: number
  /** P&L as percentage of account balance */
  pnLPercentage: number
}

/**
 * Period performance metrics
 */
export interface PeriodPerformance {
  /** Period identifier */
  period: PeriodType
  /** Total P&L for period */
  totalPnL: number
  /** P&L percentage */
  pnLPercentage: number
  /** Number of trades executed */
  tradeCount: number
  /** Win rate percentage */
  winRate: number
  /** Average P&L per trade */
  avgPnL: number
  /** Start date of period */
  startDate: Date
  /** End date of period */
  endDate: Date
}

/**
 * Individual trade information
 */
export interface TradeInfo {
  /** Trade ID */
  id: string
  /** Account ID */
  accountId: string
  /** Trading instrument (e.g., EUR_USD) */
  instrument: string
  /** Trade direction */
  direction: 'long' | 'short'
  /** Profit/loss */
  pnL: number
  /** Entry price */
  entryPrice: number
  /** Exit price */
  exitPrice: number
  /** Position size */
  units: number
  /** Entry timestamp */
  entryTime: Date
  /** Exit timestamp */
  exitTime: Date
  /** Trade duration in seconds */
  duration: number
}

/**
 * Best and worst trade pair
 */
export interface BestWorstTrades {
  /** Best performing trade */
  bestTrade: TradeInfo | null
  /** Worst performing trade */
  worstTrade: TradeInfo | null
}

/**
 * Account-level P&L breakdown
 */
export interface AccountPnL {
  /** Account ID */
  accountId: string
  /** Account alias/name */
  accountName: string
  /** Account P&L */
  pnL: number
  /** Realized P&L */
  realizedPnL: number
  /** Unrealized P&L */
  unrealizedPnL: number
  /** Account balance */
  balance: number
}

/**
 * P&L history point for sparkline
 */
export interface PnLHistoryPoint {
  /** Timestamp of snapshot */
  timestamp: Date
  /** P&L value at this point */
  value: number
}

/**
 * Live P&L ticker state
 */
export interface LivePnLState {
  /** Current daily P&L */
  dailyPnL: number
  /** P&L as percentage */
  pnLPercentage: number
  /** P&L history for sparkline (last 20 points) */
  pnLHistory: number[]
  /** Realized P&L */
  realizedPnL: number
  /** Unrealized P&L */
  unrealizedPnL: number
  /** Is data loading */
  isLoading: boolean
  /** Error message if any */
  error: string | null
  /** Last update timestamp */
  lastUpdate: Date | null
}

/**
 * WebSocket P&L update message
 */
export interface PnLUpdateMessage {
  /** Message type */
  type: 'pnl_update'
  /** Account ID */
  accountId: string
  /** Updated P&L data */
  data: {
    pnL: number
    realizedPnL: number
    unrealizedPnL: number
    balance: number
  }
  /** Update timestamp */
  timestamp: Date
}
