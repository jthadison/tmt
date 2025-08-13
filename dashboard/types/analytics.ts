/**
 * TypeScript interfaces for analytics and performance data
 * Used across the performance analytics dashboard components
 */

/**
 * Core performance metrics interface
 */
export interface PerformanceMetrics {
  /** Total profit and loss */
  totalPnL: number
  /** Total number of trades executed */
  totalTrades: number
  /** Percentage of winning trades */
  winRate: number
  /** Ratio of gross profit to gross loss */
  profitFactor: number
  /** Risk-adjusted return metric */
  sharpeRatio: number
  /** Maximum drawdown from peak */
  maxDrawdown: number
  /** Average profit per winning trade */
  averageWin: number
  /** Average loss per losing trade */
  averageLoss: number
  /** Largest single winning trade */
  bestTrade: number
  /** Largest single losing trade */
  worstTrade: number
  /** Longest consecutive winning streak */
  longestWinStreak: number
  /** Longest consecutive losing streak */
  longestLossStreak: number
  /** Percent return on initial capital */
  totalReturn: number
  /** Annual percentage return */
  annualizedReturn: number
  /** Maximum peak-to-trough drawdown */
  maxDrawdownPercent: number
  /** Standard deviation of returns */
  volatility: number
  /** Risk-free rate used for calculations */
  riskFreeRate: number
  /** Calmar ratio (annual return / max drawdown) */
  calmarRatio: number
  /** Sortino ratio (downside deviation adjusted) */
  sortinoRatio: number
}

/**
 * Pattern-based trading analysis
 */
export interface PatternAnalysis {
  /** Pattern name/type */
  pattern: string
  /** Number of trades using this pattern */
  count: number
  /** Win rate for this pattern */
  winRate: number
  /** Average P&L per trade */
  avgPnL: number
  /** Total P&L for this pattern */
  totalPnL: number
  /** Success rate trend */
  trend: 'up' | 'down' | 'stable'
  /** Performance rank among patterns */
  rank: number
}

/**
 * Comprehensive trade analysis breakdown
 */
export interface TradeAnalysis {
  /** Analysis by trading pattern */
  byPattern: PatternAnalysis[]
  /** Performance by hour of day (0-23) */
  byTimeOfDay: Record<number, PerformanceMetrics>
  /** Performance by market session */
  byMarketSession: Record<'asian' | 'london' | 'newyork' | 'overlap', PerformanceMetrics>
  /** Performance by trading symbol/pair */
  bySymbol: Record<string, PerformanceMetrics>
  /** Performance by day of week (0=Sunday) */
  byDayOfWeek: Record<number, PerformanceMetrics>
  /** Trade duration analysis */
  byDuration: Record<string, PerformanceMetrics>
  /** Trade size analysis */
  bySize: Record<string, PerformanceMetrics>
}

/**
 * Time-based performance breakdown
 */
export interface TimePerformanceBreakdown {
  /** Monthly performance (YYYY-MM format) */
  monthly: Record<string, PerformanceMetrics>
  /** Weekly performance (ISO week format) */
  weekly: Record<string, PerformanceMetrics>
  /** Daily performance (YYYY-MM-DD format) */
  daily: Record<string, PerformanceMetrics>
  /** Quarterly performance */
  quarterly: Record<string, PerformanceMetrics>
  /** Yearly performance */
  yearly: Record<string, PerformanceMetrics>
}

/**
 * Account performance comparison data
 */
export interface AccountPerformanceComparison {
  /** Account identifier */
  accountId: string
  /** Display name for account */
  accountName: string
  /** Prop firm name */
  propFirm: string
  /** Account type */
  accountType: 'challenge' | 'funded' | 'demo'
  /** Performance metrics for this account */
  metrics: PerformanceMetrics
  /** Ranking among all accounts */
  rank: number
  /** Correlation coefficient to portfolio */
  correlationToPortfolio: number
  /** Account start date */
  startDate: Date
  /** Current account balance */
  currentBalance: number
  /** Initial account balance */
  initialBalance: number
  /** Account status */
  status: 'active' | 'passed' | 'failed' | 'withdrawn'
  /** Risk level classification */
  riskLevel: 'low' | 'medium' | 'high'
}

/**
 * Date range configuration
 */
export interface DateRange {
  /** Start date */
  start: Date
  /** End date */
  end: Date
  /** Preset range label */
  label?: string
  /** Is this a preset range */
  isPreset?: boolean
}

/**
 * Date range preset options
 */
export type DateRangePreset = 
  | 'last_7_days'
  | 'last_30_days' 
  | 'last_90_days'
  | 'last_6_months'
  | 'last_year'
  | 'year_to_date'
  | 'all_time'
  | 'custom'

/**
 * Performance report configuration
 */
export interface PerformanceReport {
  /** Unique report identifier */
  id: string
  /** Title of the report */
  title: string
  /** Account IDs included in report */
  accountIds: string[]
  /** Date range for analysis */
  dateRange: DateRange
  /** Aggregate portfolio metrics */
  aggregateMetrics: PerformanceMetrics
  /** Account comparison data */
  accountComparisons: AccountPerformanceComparison[]
  /** Trade analysis breakdown */
  tradeAnalysis: TradeAnalysis
  /** Time-based performance breakdown */
  timeBreakdown: TimePerformanceBreakdown
  /** When report was generated */
  generatedAt: Date
  /** Report type and detail level */
  reportType: 'standard' | 'detailed' | 'executive' | 'regulatory'
  /** Report format preferences */
  format: {
    includeCharts: boolean
    includeRawData: boolean
    chartResolution: 'low' | 'medium' | 'high'
    currency: string
  }
}

/**
 * Chart configuration and data
 */
export interface ChartData {
  /** Chart labels (x-axis) */
  labels: string[]
  /** Chart datasets */
  datasets: ChartDataset[]
  /** Chart type */
  type: 'line' | 'bar' | 'pie' | 'doughnut' | 'scatter' | 'heatmap'
  /** Chart title */
  title: string
  /** Chart subtitle */
  subtitle?: string
}

/**
 * Chart dataset configuration
 */
export interface ChartDataset {
  /** Dataset label */
  label: string
  /** Data points */
  data: number[]
  /** Background color(s) */
  backgroundColor?: string | string[]
  /** Border color(s) */
  borderColor?: string | string[]
  /** Fill area under line */
  fill?: boolean
  /** Line tension for smooth curves */
  tension?: number
  /** Point radius */
  pointRadius?: number
  /** Dataset type override */
  type?: string
}

/**
 * Analytics dashboard filter options
 */
export interface AnalyticsFilters {
  /** Selected accounts */
  accountIds: string[]
  /** Date range selection */
  dateRange: DateRange
  /** Include only specific patterns */
  patterns?: string[]
  /** Include only specific symbols */
  symbols?: string[]
  /** Minimum trade size filter */
  minTradeSize?: number
  /** Maximum trade size filter */
  maxTradeSize?: number
  /** Include only profitable trades */
  profitableOnly?: boolean
  /** Group by option */
  groupBy: 'account' | 'pattern' | 'symbol' | 'time' | 'session'
}

/**
 * Export options for reports and data
 */
export interface ExportOptions {
  /** Export format */
  format: 'pdf' | 'csv' | 'excel' | 'json'
  /** Include charts in export */
  includeCharts: boolean
  /** Include raw trade data */
  includeRawData: boolean
  /** Page orientation for PDF */
  orientation?: 'portrait' | 'landscape'
  /** Chart image resolution */
  chartResolution?: 'low' | 'medium' | 'high'
  /** Custom filename */
  filename?: string
  /** Email delivery options */
  emailOptions?: {
    recipients: string[]
    subject: string
    message?: string
  }
}

/**
 * Benchmark comparison data
 */
export interface BenchmarkComparison {
  /** Benchmark name */
  name: string
  /** Benchmark symbol/identifier */
  symbol: string
  /** Portfolio return */
  portfolioReturn: number
  /** Benchmark return */
  benchmarkReturn: number
  /** Excess return (portfolio - benchmark) */
  excessReturn: number
  /** Beta coefficient */
  beta: number
  /** Alpha coefficient */
  alpha: number
  /** Correlation coefficient */
  correlation: number
  /** Tracking error */
  trackingError: number
  /** Information ratio */
  informationRatio: number
}

/**
 * Performance streak information
 */
export interface PerformanceStreak {
  /** Streak type */
  type: 'winning' | 'losing'
  /** Current streak length */
  current: number
  /** Longest streak in period */
  longest: number
  /** Streak start date */
  startDate: Date
  /** Streak end date (if ended) */
  endDate?: Date
  /** Total P&L during streak */
  totalPnL: number
  /** Is this streak currently active */
  isActive: boolean
}

/**
 * Drawdown analysis details
 */
export interface DrawdownAnalysis {
  /** Maximum drawdown amount */
  maxDrawdown: number
  /** Maximum drawdown percentage */
  maxDrawdownPercent: number
  /** Drawdown start date */
  startDate: Date
  /** Drawdown end date */
  endDate?: Date
  /** Recovery date (when back to peak) */
  recoveryDate?: Date
  /** Duration in days */
  duration: number
  /** Recovery duration in days */
  recoveryDuration?: number
  /** Is currently in drawdown */
  isActive: boolean
  /** Underwater curve data */
  underwaterCurve: Array<{
    date: Date
    drawdown: number
  }>
}

/**
 * Volatility analysis
 */
export interface VolatilityAnalysis {
  /** Daily volatility */
  daily: number
  /** Weekly volatility */
  weekly: number
  /** Monthly volatility */
  monthly: number
  /** Annualized volatility */
  annualized: number
  /** Downside deviation */
  downsideDeviation: number
  /** Upside deviation */
  upsideDeviation: number
  /** Value at Risk (95% confidence) */
  var95: number
  /** Value at Risk (99% confidence) */
  var99: number
  /** Conditional Value at Risk */
  cvar: number
}

/**
 * Calendar heatmap data point
 */
export interface CalendarHeatmapData {
  /** Date */
  date: Date
  /** Daily P&L */
  value: number
  /** Number of trades */
  trades: number
  /** Day type */
  type: 'profit' | 'loss' | 'neutral'
  /** Intensity level for coloring */
  intensity: number
}

/**
 * Analytics dashboard state
 */
export interface AnalyticsDashboardState {
  /** Current filters */
  filters: AnalyticsFilters
  /** Loading states */
  loading: {
    aggregate: boolean
    comparison: boolean
    tradeAnalysis: boolean
    timeBreakdown: boolean
    export: boolean
  }
  /** Error states */
  errors: {
    aggregate?: string
    comparison?: string
    tradeAnalysis?: string
    timeBreakdown?: string
    export?: string
  }
  /** Active tab */
  activeTab: 'overview' | 'comparison' | 'analysis' | 'breakdown' | 'reports'
  /** Last refresh timestamp */
  lastRefresh: Date
}