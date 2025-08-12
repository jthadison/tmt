/**
 * Account overview data types for multi-account dashboard
 */

/**
 * Account health status indicator
 */
export type AccountStatus = 'healthy' | 'warning' | 'danger'

/**
 * P&L (Profit and Loss) metrics for an account
 */
export interface PnLMetrics {
  /** Daily P&L in account currency */
  daily: number
  /** Weekly P&L in account currency */
  weekly: number
  /** Total P&L in account currency */
  total: number
  /** P&L as percentage of account balance */
  percentage: number
}

/**
 * Drawdown metrics for risk monitoring
 */
export interface DrawdownMetrics {
  /** Current drawdown amount */
  current: number
  /** Maximum allowed drawdown */
  maximum: number
  /** Drawdown as percentage of maximum */
  percentage: number
}

/**
 * Position metrics for account exposure tracking
 */
export interface PositionMetrics {
  /** Total number of active positions */
  active: number
  /** Number of long positions */
  long: number
  /** Number of short positions */
  short: number
}

/**
 * Exposure metrics for risk management
 */
export interface ExposureMetrics {
  /** Total exposure amount */
  total: number
  /** Maximum exposure limit */
  limit: number
  /** Exposure utilization as percentage */
  utilization: number
}

/**
 * Complete account overview data structure
 */
export interface AccountOverview {
  /** Unique account identifier */
  id: string
  /** Display name for the account */
  accountName: string
  /** Name of the prop firm */
  propFirm: string
  /** Current account balance */
  balance: number
  /** Current account equity */
  equity: number
  /** Profit and Loss metrics */
  pnl: PnLMetrics
  /** Drawdown metrics for risk monitoring */
  drawdown: DrawdownMetrics
  /** Position count and breakdown */
  positions: PositionMetrics
  /** Exposure metrics and limits */
  exposure: ExposureMetrics
  /** Overall account health status */
  status: AccountStatus
  /** Last update timestamp */
  lastUpdate: Date
}

/**
 * WebSocket message types for real-time updates
 */
export interface AccountUpdateMessage {
  type: 'account:overview:update'
  accountId: string
  data: Partial<AccountOverview>
  timestamp: string
}

export interface PnLUpdateMessage {
  type: 'account:pnl:update'
  accountId: string
  data: PnLMetrics
  timestamp: string
}

export interface PositionChangeMessage {
  type: 'account:positions:change'
  accountId: string
  data: PositionMetrics
  timestamp: string
}

/**
 * Grid sorting and filtering options
 */
export interface GridFilters {
  status?: AccountStatus[]
  propFirm?: string[]
  minBalance?: number
  maxBalance?: number
}

export interface GridSortOptions {
  field: keyof AccountOverview
  direction: 'asc' | 'desc'
}