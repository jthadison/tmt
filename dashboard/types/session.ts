/**
 * Trading Session Type Definitions
 * Types for session-based performance tracking and analysis
 */

/**
 * Trading session identifiers
 */
export enum TradingSession {
  SYDNEY = 'sydney',
  TOKYO = 'tokyo',
  LONDON = 'london',
  NEW_YORK = 'new_york',
  OVERLAP = 'overlap'
}

/**
 * Session configuration and metadata
 */
export interface SessionConfig {
  /** Display name */
  name: string
  /** Session start hour (GMT) */
  startHour: number
  /** Session end hour (GMT) */
  endHour: number
  /** Theme color for UI */
  color: string
  /** Confidence threshold percentage */
  confidenceThreshold: number
}

/**
 * Session configuration mapping
 */
export const SESSION_CONFIG: Record<TradingSession, SessionConfig> = {
  [TradingSession.SYDNEY]: {
    name: 'Sydney',
    startHour: 18,
    endHour: 3,
    color: 'purple',
    confidenceThreshold: 78
  },
  [TradingSession.TOKYO]: {
    name: 'Tokyo',
    startHour: 0,
    endHour: 9,
    color: 'red',
    confidenceThreshold: 85
  },
  [TradingSession.LONDON]: {
    name: 'London',
    startHour: 7,
    endHour: 16,
    color: 'blue',
    confidenceThreshold: 72
  },
  [TradingSession.NEW_YORK]: {
    name: 'New York',
    startHour: 12,
    endHour: 21,
    color: 'green',
    confidenceThreshold: 70
  },
  [TradingSession.OVERLAP]: {
    name: 'Overlap',
    startHour: 12,
    endHour: 16,
    color: 'orange',
    confidenceThreshold: 70
  }
}

/**
 * Session performance data structure
 */
export interface SessionPerformance {
  /** Session identifier */
  session: TradingSession
  /** Total P&L for session */
  totalPnL: number
  /** Number of trades executed */
  tradeCount: number
  /** Number of winning trades */
  winCount: number
  /** Win rate percentage */
  winRate: number
  /** Confidence threshold used */
  confidenceThreshold: number
  /** Is currently active session */
  isActive: boolean
}

/**
 * Date range for filtering
 */
export interface DateRange {
  /** Start date */
  start: Date
  /** End date */
  end: Date
}

/**
 * Date range preset options
 */
export type DateRangePreset = 'today' | 'week' | 'month' | 'custom'

/**
 * Session detail trade information
 */
export interface SessionTrade {
  /** Trade ID */
  id: string
  /** Timestamp */
  timestamp: Date
  /** Trading instrument */
  instrument: string
  /** Trade direction */
  direction: 'long' | 'short'
  /** Profit/loss */
  pnL: number
  /** Trade duration in seconds */
  duration: number
}

/**
 * WebSocket trade completion message
 */
export interface TradeCompletedMessage {
  type: 'trade.completed'
  data: {
    session: string
    pnL: number
    timestamp: string
  }
}
