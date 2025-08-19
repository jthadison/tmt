/**
 * OANDA Account Types and Interfaces
 * Comprehensive type definitions for OANDA account management and display
 */

/**
 * OANDA account types
 */
export type OandaAccountType = 'live' | 'demo' | 'mt4'

/**
 * Account health status based on margin and risk metrics
 */
export type AccountHealthStatus = 'healthy' | 'warning' | 'danger' | 'margin_call'

/**
 * Currency codes supported by OANDA
 */
export type CurrencyCode = 'USD' | 'EUR' | 'GBP' | 'JPY' | 'CHF' | 'CAD' | 'AUD' | 'NZD'

/**
 * Time frame options for historical data
 */
export type TimeFrame = '1H' | '4H' | '1D' | '1W' | '1M'

/**
 * Core OANDA account information
 */
export interface OandaAccount {
  /** OANDA account ID */
  id: string
  /** Account display name */
  alias: string
  /** Account type (live, demo, mt4) */
  type: OandaAccountType
  /** Account currency */
  currency: CurrencyCode
  /** Current account balance */
  balance: number
  /** Net Asset Value (balance + unrealized P&L) */
  NAV: number
  /** Unrealized profit/loss */
  unrealizedPL: number
  /** Realized profit/loss */
  realizedPL: number
  /** Margin used */
  marginUsed: number
  /** Margin available */
  marginAvailable: number
  /** Margin rate */
  marginRate: number
  /** Open trade count */
  openTradeCount: number
  /** Open position count */
  openPositionCount: number
  /** Pending order count */
  pendingOrderCount: number
  /** Account creation time */
  createdTime: string
  /** Last transaction ID */
  lastTransactionID: string
  /** Commission structure */
  commission: {
    homeConversionFactor: number
    unitsAvailable: {
      default: {
        long: string
        short: string
      }
    }
  }
  /** Financing information */
  financing: {
    dividendAdjustment: number
  }
  /** Account health status */
  healthStatus: AccountHealthStatus
  /** Last update timestamp */
  lastUpdate: Date
}

/**
 * Real-time account metrics for monitoring
 */
export interface AccountMetrics {
  /** Account ID */
  accountId: string
  /** Timestamp of metrics */
  timestamp: Date
  /** Current balance */
  balance: number
  /** Current equity (NAV) */
  equity: number
  /** Used margin */
  marginUsed: number
  /** Available margin */
  marginAvailable: number
  /** Margin utilization percentage */
  marginUtilization: number
  /** Free margin */
  freeMargin: number
  /** Margin level percentage */
  marginLevel: number
  /** Daily P&L */
  dailyPL: number
  /** Unrealized P&L */
  unrealizedPL: number
  /** Open positions count */
  openPositions: number
  /** Total exposure */
  totalExposure: number
  /** Risk score (0-100) */
  riskScore: number
}

/**
 * Historical account performance data point
 */
export interface AccountHistoryPoint {
  /** Timestamp */
  timestamp: Date
  /** Account balance at this time */
  balance: number
  /** Account equity at this time */
  equity: number
  /** Unrealized P&L */
  unrealizedPL: number
  /** Realized P&L */
  realizedPL: number
  /** Margin used */
  marginUsed: number
  /** Drawdown from peak */
  drawdown: number
  /** Drawdown percentage */
  drawdownPercent: number
}

/**
 * Account performance summary for a period
 */
export interface AccountPerformanceSummary {
  /** Account ID */
  accountId: string
  /** Period start */
  startDate: Date
  /** Period end */
  endDate: Date
  /** Starting balance */
  startingBalance: number
  /** Ending balance */
  endingBalance: number
  /** Total return */
  totalReturn: number
  /** Total return percentage */
  totalReturnPercent: number
  /** Maximum balance achieved */
  peakBalance: number
  /** Maximum drawdown */
  maxDrawdown: number
  /** Maximum drawdown percentage */
  maxDrawdownPercent: number
  /** Current drawdown from peak */
  currentDrawdown: number
  /** Current drawdown percentage */
  currentDrawdownPercent: number
  /** Win rate */
  winRate: number
  /** Total trades */
  totalTrades: number
  /** Winning trades */
  winningTrades: number
  /** Losing trades */
  losingTrades: number
  /** Average win */
  averageWin: number
  /** Average loss */
  averageLoss: number
  /** Profit factor */
  profitFactor: number
  /** Sharpe ratio */
  sharpeRatio: number
  /** Sortino ratio */
  sortinoRatio: number
}

/**
 * Trading limits and risk management settings
 */
export interface TradingLimits {
  /** Account ID */
  accountId: string
  /** Maximum daily loss limit */
  maxDailyLoss: number
  /** Maximum total loss limit */
  maxTotalLoss: number
  /** Maximum position size */
  maxPositionSize: number
  /** Maximum number of open positions */
  maxOpenPositions: number
  /** Maximum margin utilization percentage */
  maxMarginUtilization: number
  /** Current daily loss */
  currentDailyLoss: number
  /** Current total loss */
  currentTotalLoss: number
  /** Current position count */
  currentPositions: number
  /** Current margin utilization */
  currentMarginUtilization: number
  /** Risk score threshold */
  riskScoreThreshold: number
  /** Current risk score */
  currentRiskScore: number
  /** Limits enabled */
  limitsEnabled: boolean
  /** Last updated */
  lastUpdated: Date
}

/**
 * Multi-account aggregated metrics
 */
export interface AggregatedAccountMetrics {
  /** Total accounts */
  totalAccounts: number
  /** Active accounts */
  activeAccounts: number
  /** Total balance across all accounts */
  totalBalance: number
  /** Total equity across all accounts */
  totalEquity: number
  /** Total unrealized P&L */
  totalUnrealizedPL: number
  /** Total margin used */
  totalMarginUsed: number
  /** Total margin available */
  totalMarginAvailable: number
  /** Average margin utilization */
  averageMarginUtilization: number
  /** Total daily P&L */
  totalDailyPL: number
  /** Total open positions */
  totalOpenPositions: number
  /** Accounts by health status */
  healthStatusBreakdown: {
    healthy: number
    warning: number
    danger: number
    marginCall: number
  }
  /** Overall portfolio risk score */
  portfolioRiskScore: number
  /** Currency breakdown */
  currencyBreakdown: {
    [currency in CurrencyCode]?: {
      accountCount: number
      totalBalance: number
      totalEquity: number
    }
  }
  /** Last update timestamp */
  lastUpdate: Date
}

/**
 * OANDA API response wrapper
 */
export interface OandaApiResponse<T> {
  /** Response data */
  data: T
  /** Request timestamp */
  timestamp: Date
  /** Rate limit information */
  rateLimit: {
    limit: number
    remaining: number
    reset: Date
  }
  /** Response status */
  status: 'success' | 'error' | 'rate_limited'
  /** Error message if any */
  error?: string
}

/**
 * Real-time update message for account data
 */
export interface AccountUpdateMessage {
  /** Message type */
  type: 'account_update'
  /** Account ID */
  accountId: string
  /** Updated metrics */
  metrics: Partial<AccountMetrics>
  /** Update timestamp */
  timestamp: Date
}

/**
 * Account alert configuration
 */
export interface AccountAlert {
  /** Alert ID */
  id: string
  /** Account ID */
  accountId: string
  /** Alert type */
  type: 'margin_warning' | 'drawdown_warning' | 'daily_loss_limit' | 'balance_threshold' | 'risk_score'
  /** Alert threshold */
  threshold: number
  /** Current value */
  currentValue: number
  /** Alert enabled */
  enabled: boolean
  /** Alert triggered */
  triggered: boolean
  /** Last triggered time */
  lastTriggered?: Date
  /** Alert message */
  message: string
  /** Severity level */
  severity: 'info' | 'warning' | 'critical'
  /** Created timestamp */
  createdAt: Date
  /** Updated timestamp */
  updatedAt: Date
}

/**
 * Account connection status
 */
export interface AccountConnectionStatus {
  /** Account ID */
  accountId: string
  /** Connection status */
  status: 'connected' | 'disconnected' | 'error' | 'connecting'
  /** Last connection attempt */
  lastConnectionAttempt: Date
  /** Last successful connection */
  lastSuccessfulConnection?: Date
  /** Connection error message */
  connectionError?: string
  /** Number of connection retries */
  retryCount: number
  /** Next retry attempt */
  nextRetryAttempt?: Date
  /** API rate limit status */
  rateLimitStatus: {
    limited: boolean
    resetTime?: Date
    requestsRemaining: number
  }
}

/**
 * Chart data point for visualizations
 */
export interface ChartDataPoint {
  /** X-axis value (timestamp) */
  x: number
  /** Y-axis value */
  y: number
  /** Additional data for tooltip */
  tooltip?: {
    label: string
    value: string | number
    color?: string
  }
}

/**
 * Chart configuration for account data visualization
 */
export interface AccountChartConfig {
  /** Chart type */
  type: 'line' | 'area' | 'bar' | 'candlestick'
  /** Chart title */
  title: string
  /** Time frame */
  timeFrame: TimeFrame
  /** Y-axis configuration */
  yAxis: {
    label: string
    format: 'currency' | 'percentage' | 'number'
    currency?: CurrencyCode
  }
  /** Data series */
  series: {
    name: string
    data: ChartDataPoint[]
    color: string
    type?: 'line' | 'area'
  }[]
  /** Chart height */
  height?: number
  /** Show grid */
  showGrid?: boolean
  /** Show legend */
  showLegend?: boolean
}

/**
 * Account filter options for multi-account views
 */
export interface AccountFilter {
  /** Account types to include */
  accountTypes?: OandaAccountType[]
  /** Currencies to include */
  currencies?: CurrencyCode[]
  /** Health status to include */
  healthStatus?: AccountHealthStatus[]
  /** Minimum balance */
  minBalance?: number
  /** Maximum balance */
  maxBalance?: number
  /** Search query for account name/alias */
  searchQuery?: string
  /** Sort by field */
  sortBy?: 'balance' | 'equity' | 'unrealizedPL' | 'marginUtilization' | 'riskScore' | 'alias'
  /** Sort direction */
  sortDirection?: 'asc' | 'desc'
}

/**
 * Export configuration for account data
 */
export interface AccountExportConfig {
  /** Export format */
  format: 'csv' | 'excel' | 'pdf' | 'json'
  /** Date range */
  dateRange: {
    start: Date
    end: Date
  }
  /** Account IDs to include */
  accountIds: string[]
  /** Data fields to include */
  fields: (keyof AccountMetrics | keyof AccountPerformanceSummary)[]
  /** Include charts */
  includeCharts: boolean
  /** File name */
  fileName?: string
}