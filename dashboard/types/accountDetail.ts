/**
 * Account detail view data types for individual account analysis
 */

/**
 * Position type for active trades
 */
export type PositionType = 'long' | 'short'

/**
 * Active trading position
 */
export interface Position {
  /** Unique position identifier */
  id: string
  /** Trading symbol (e.g., EUR/USD, AAPL) */
  symbol: string
  /** Position type (long/short) */
  type: PositionType
  /** Position size in lots or shares */
  size: number
  /** Entry price when position was opened */
  entryPrice: number
  /** Current market price */
  currentPrice: number
  /** Current profit/loss in account currency */
  pnl: number
  /** P&L as percentage of position value */
  pnlPercentage: number
  /** Timestamp when position was opened */
  openTime: Date
  /** Duration position has been held (in minutes) */
  duration: number
  /** Stop loss price (optional) */
  stopLoss?: number
  /** Take profit price (optional) */
  takeProfit?: number
  /** Commission paid for this position */
  commission: number
  /** Risk amount (percentage of account) */
  riskPercentage: number
}

/**
 * Completed trade record
 */
export interface Trade {
  /** Unique trade identifier */
  id: string
  /** Account ID associated with trade */
  accountId?: string
  /** Account name for display */
  accountName?: string
  /** Trading symbol/instrument (symbol for compatibility, instrument for API) */
  symbol?: string
  instrument?: string
  /** Trade type (long/short for compatibility, market/limit for API) */
  type: PositionType | 'market' | 'limit'
  /** Trade direction (buy/sell for API) */
  side?: 'buy' | 'sell'
  /** Trade size in lots or shares (size for compatibility, units for API) */
  size?: number
  units?: number
  /** Entry price (entryPrice for compatibility, price for API) */
  entryPrice?: number
  price?: number
  /** Exit price */
  exitPrice?: number
  /** Stop loss price */
  stopLoss?: number
  /** Take profit price */
  takeProfit?: number
  /** Final profit/loss */
  pnl: number
  /** Total commission paid */
  commission: number
  /** Swap fees */
  swap?: number
  /** Trade open timestamp */
  openTime: Date
  /** Trade close timestamp */
  closeTime?: Date | null
  /** Trade status */
  status?: 'open' | 'closed' | 'pending'
  /** Trade duration in minutes */
  duration?: number
  /** Trading strategy used (optional) */
  strategy?: string
  /** Pattern used to enter the trade (e.g., wyckoff_spring, vpa_confirmation) */
  pattern?: string
  /** Signal confidence when trade was entered (0-100) */
  confidence?: number
  /** Trade notes or comments */
  notes?: string
  /** Trade tags */
  tags?: string[]
}

/**
 * Equity curve data point
 */
export interface EquityPoint {
  /** Timestamp for this data point */
  timestamp: Date
  /** Account equity at this time */
  equity: number
  /** Account balance at this time */
  balance: number
  /** Drawdown from peak at this time */
  drawdown: number
}

/**
 * Risk performance metrics
 */
export interface RiskMetrics {
  /** Sharpe ratio (risk-adjusted return) */
  sharpeRatio: number
  /** Win rate as percentage */
  winRate: number
  /** Profit factor (gross profit / gross loss) */
  profitFactor: number
  /** Maximum drawdown percentage */
  maxDrawdown: number
  /** Average winning trade amount */
  averageWin: number
  /** Average losing trade amount */
  averageLoss: number
  /** Total number of trades */
  totalTrades: number
  /** Consecutive wins */
  consecutiveWins: number
  /** Consecutive losses */
  consecutiveLosses: number
  /** Largest win */
  largestWin: number
  /** Largest loss */
  largestLoss: number
}

/**
 * Compliance rule violation
 */
export interface ComplianceViolation {
  /** Violation identifier */
  id: string
  /** Type of rule violated */
  ruleType: string
  /** Violation description */
  description: string
  /** Severity level */
  severity: 'low' | 'medium' | 'high' | 'critical'
  /** Timestamp when violation occurred */
  timestamp: Date
  /** Whether violation has been resolved */
  resolved: boolean
}

/**
 * Prop firm compliance status
 */
export interface ComplianceStatus {
  /** Daily loss limit tracking */
  dailyLossLimit: {
    current: number
    limit: number
    percentage: number
  }
  /** Monthly loss limit tracking */
  monthlyLossLimit: {
    current: number
    limit: number
    percentage: number
  }
  /** Maximum drawdown tracking */
  maxDrawdown: {
    current: number
    limit: number
    percentage: number
  }
  /** Minimum trading days requirement */
  minTradingDays: {
    current: number
    required: number
    percentage: number
  }
  /** Account tier information */
  accountTier: string
  /** List of compliance violations */
  violations: ComplianceViolation[]
  /** Overall compliance status */
  overallStatus: 'compliant' | 'warning' | 'violation'
}

/**
 * Trading permissions and controls
 */
export interface TradingPermissions {
  /** Can place new trades */
  canTrade: boolean
  /** Can close existing positions */
  canClose: boolean
  /** Can modify stop loss/take profit */
  canModify: boolean
  /** Maximum position size allowed */
  maxPositionSize: number
  /** Maximum daily trades allowed */
  maxDailyTrades: number
  /** Requires additional confirmation for trades */
  requiresConfirmation: boolean
}

/**
 * Manual override action types
 */
export type OverrideAction = 
  | 'emergency_stop' 
  | 'close_position' 
  | 'close_all_positions' 
  | 'modify_position' 
  | 'override_risk_limits'

/**
 * Manual override request
 */
export interface ManualOverride {
  /** Override action type */
  action: OverrideAction
  /** Target position ID (if applicable) */
  positionId?: string
  /** Override reason */
  reason: string
  /** Additional parameters for the override */
  parameters?: Record<string, any>
  /** User confirmation required */
  confirmed: boolean
}

/**
 * Complete account detail data structure
 */
export interface AccountDetails {
  /** Account identifier */
  id: string
  /** Account display name */
  accountName: string
  /** Prop firm name */
  propFirm: string
  /** Current account balance */
  balance: number
  /** Current account equity */
  equity: number
  /** Active positions */
  positions: Position[]
  /** Recent completed trades */
  recentTrades: Trade[]
  /** Historical equity curve data */
  equityHistory: EquityPoint[]
  /** Risk performance metrics */
  riskMetrics: RiskMetrics
  /** Compliance status */
  complianceStatus: ComplianceStatus
  /** Trading permissions */
  tradingPermissions: TradingPermissions
  /** Last update timestamp */
  lastUpdate: Date
}

/**
 * Chart timeframe options
 */
export type ChartTimeframe = '1D' | '1W' | '1M' | '3M' | '6M' | '1Y' | 'ALL'

/**
 * Trade history filter options
 */
export interface TradeHistoryFilters {
  /** Filter by symbol */
  symbol?: string
  /** Filter by trade type (buy/sell or long/short) */
  type?: PositionType | 'buy' | 'sell'
  /** Filter by date range */
  dateRange?: {
    start: Date
    end: Date
  }
  /** Filter by P&L range */
  pnlRange?: {
    min: number
    max: number
  }
  /** Filter by strategy */
  strategy?: string
  /** Filter by pattern */
  pattern?: string
}

/**
 * Position table sort options
 */
export interface PositionSortOptions {
  field: keyof Position
  direction: 'asc' | 'desc'
}

/**
 * Trade history sort options
 */
export interface TradeSortOptions {
  field: keyof Trade
  direction: 'asc' | 'desc'
}

/**
 * Trade statistics for analysis
 */
export interface TradeStats {
  /** Total number of trades */
  totalTrades: number
  /** Number of closed trades */
  closedTrades: number
  /** Number of open trades */
  openTrades: number
  /** Number of winning trades */
  winningTrades: number
  /** Number of losing trades */
  losingTrades: number
  /** Total P&L across all trades */
  totalPnL: number
  /** Win rate as percentage */
  winRate: number
  /** Average winning trade amount */
  averageWin: number
  /** Average losing trade amount */
  averageLoss: number
  /** Profit factor (gross profit / gross loss) */
  profitFactor: number
  /** Maximum drawdown */
  maxDrawdown: number
  /** Total commission paid */
  totalCommission: number
  /** Total swap fees */
  totalSwap: number
}

/**
 * Trade filter for API requests
 */
export interface TradeFilter {
  /** Filter by instrument/symbol */
  instrument?: string
  /** Filter by trade status */
  status?: 'open' | 'closed' | 'pending'
  /** Filter by trade type */
  type?: string
  /** Minimum profit filter */
  minProfit?: number
  /** Maximum profit filter */
  maxProfit?: number
}