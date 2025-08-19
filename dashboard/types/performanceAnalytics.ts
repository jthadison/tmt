/**
 * Performance Analytics Types and Interfaces
 * Story 9.6: Trading Performance Analytics and Reporting
 * 
 * Comprehensive type definitions for performance tracking, risk analytics,
 * and compliance reporting across multiple trading accounts and AI agents.
 */

/**
 * Trade record from PostgreSQL database
 */
export interface TradeRecord {
  id: string
  accountId: string
  agentId: string
  agentName: string
  symbol: string
  direction: 'buy' | 'sell'
  openTime: Date
  closeTime?: Date
  openPrice: number
  closePrice?: number
  size: number
  commission: number
  swap: number
  profit?: number
  status: 'open' | 'closed' | 'pending'
  stopLoss?: number
  takeProfit?: number
  strategy: string
  metadata?: Record<string, any>
}

/**
 * Real-time P&L tracking data
 */
export interface RealtimePnL {
  accountId: string
  agentId: string
  currentPnL: number
  realizedPnL: number
  unrealizedPnL: number
  dailyPnL: number
  weeklyPnL: number
  monthlyPnL: number
  trades: TradeBreakdown[]
  lastUpdate: Date
  highWaterMark: number
  currentDrawdown: number
}

/**
 * Individual trade breakdown for P&L attribution
 */
export interface TradeBreakdown {
  tradeId: string
  symbol: string
  entryTime: Date
  exitTime?: Date
  entryPrice: number
  exitPrice?: number
  size: number
  direction: 'long' | 'short'
  pnl: number
  pnlPercent: number
  commission: number
  netPnL: number
  duration?: number // in minutes
  agentId: string
  agentName: string
  strategy: string
  riskRewardRatio?: number
}

/**
 * Risk analytics metrics
 */
export interface RiskMetrics {
  sharpeRatio: number
  sortinoRatio: number
  calmarRatio: number
  maxDrawdown: number
  maxDrawdownPercent: number
  currentDrawdown: number
  currentDrawdownPercent: number
  averageDrawdown: number
  drawdownDuration: number // days
  recoveryFactor: number
  volatility: number
  downsideDeviation: number
  valueAtRisk95: number
  valueAtRisk99: number
  conditionalVaR: number
  beta: number
  alpha: number
  correlation: number
  winLossRatio: number
  profitFactor: number
  expectancy: number
  kellyPercentage: number
}

/**
 * Agent performance metrics
 */
export interface AgentPerformance {
  agentId: string
  agentName: string
  agentType: string
  totalTrades: number
  winningTrades: number
  losingTrades: number
  winRate: number
  totalPnL: number
  averagePnL: number
  bestTrade: number
  worstTrade: number
  averageWin: number
  averageLoss: number
  profitFactor: number
  sharpeRatio: number
  maxDrawdown: number
  consistency: number // 0-100 score
  reliability: number // 0-100 score
  contribution: number // % contribution to total P&L
  patterns: string[]
  preferredSymbols: string[]
  activeHours: number[]
  performance: RiskMetrics
}

/**
 * Strategy performance analysis
 */
export interface StrategyPerformance {
  strategyId: string
  strategyName: string
  category: 'trend' | 'reversal' | 'breakout' | 'scalping' | 'arbitrage' | 'other'
  totalTrades: number
  winRate: number
  totalPnL: number
  averagePnL: number
  sharpeRatio: number
  maxDrawdown: number
  bestMarketCondition: string
  worstMarketCondition: string
  optimalTimeframe: string
  symbols: SymbolPerformance[]
  monthlyPerformance: MonthlyBreakdown[]
}

/**
 * Symbol-specific performance
 */
export interface SymbolPerformance {
  symbol: string
  trades: number
  winRate: number
  totalPnL: number
  averagePnL: number
  bestTime: string // hour of day
  worstTime: string
  volatilityImpact: number
}

/**
 * Monthly performance breakdown
 */
export interface MonthlyBreakdown {
  month: string // YYYY-MM
  trades: number
  winRate: number
  pnl: number
  return: number
  drawdown: number
  sharpeRatio: number
}

/**
 * Compliance report data
 */
export interface ComplianceReport {
  reportId: string
  generatedAt: Date
  period: {
    start: Date
    end: Date
  }
  accounts: AccountCompliance[]
  aggregateMetrics: {
    totalPnL: number
    totalTrades: number
    totalVolume: number
    averageDailyVolume: number
    peakExposure: number
    maxDrawdown: number
  }
  violations: ComplianceViolation[]
  auditTrail: AuditEntry[]
  regulatoryMetrics: RegulatoryMetrics
  signature?: string
}

/**
 * Account compliance details
 */
export interface AccountCompliance {
  accountId: string
  propFirm: string
  accountType: string
  startBalance: number
  endBalance: number
  totalReturn: number
  maxDrawdown: number
  dailyLossLimit: number
  maxDailyLossReached: number
  totalLossLimit: number
  maxTotalLossReached: number
  profitTarget?: number
  profitAchieved?: number
  rulesViolated: string[]
  tradingDays: number
  averageDailyVolume: number
}

/**
 * Compliance violation record
 */
export interface ComplianceViolation {
  timestamp: Date
  accountId: string
  ruleId: string
  ruleName: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  description: string
  impact: string
  resolution?: string
}

/**
 * Audit trail entry
 */
export interface AuditEntry {
  timestamp: Date
  userId?: string
  action: string
  entity: string
  entityId: string
  changes?: Record<string, any>
  ipAddress?: string
  userAgent?: string
}

/**
 * Regulatory compliance metrics
 */
export interface RegulatoryMetrics {
  mifidCompliant: boolean
  nfaCompliant: boolean
  esmaCompliant: boolean
  bestExecutionScore: number
  orderToTradeRatio: number
  cancelRatio: number
  messagingRate: number
  marketImpact: number
  slippageCost: number
}

/**
 * Performance comparison data
 */
export interface PerformanceComparison {
  baselineId: string
  baselineName: string
  comparisonId: string
  comparisonName: string
  period: {
    start: Date
    end: Date
  }
  metrics: {
    baseline: RiskMetrics
    comparison: RiskMetrics
    difference: RiskMetrics
    percentChange: RiskMetrics
  }
  correlation: number
  covariance: number
  relativeStrength: number
  outperformanceProbability: number
}

/**
 * Export configuration
 */
export interface ExportConfig {
  format: 'pdf' | 'csv' | 'excel' | 'json'
  includeCharts: boolean
  includeRawData: boolean
  includeAnalysis: boolean
  chartResolution: 'low' | 'medium' | 'high'
  dateFormat: string
  numberFormat: string
  currency: string
  timezone: string
  compression?: boolean
  encryption?: boolean
  password?: string
}

/**
 * Analytics query parameters
 */
export interface AnalyticsQuery {
  accountIds?: string[]
  agentIds?: string[]
  symbols?: string[]
  strategies?: string[]
  dateRange: {
    start: Date
    end: Date
  }
  granularity: 'tick' | 'minute' | 'hour' | 'day' | 'week' | 'month'
  metrics: string[]
  groupBy?: ('account' | 'agent' | 'symbol' | 'strategy' | 'time')[]
  orderBy?: string
  limit?: number
  offset?: number
}

/**
 * Performance alert configuration
 */
export interface PerformanceAlert {
  id: string
  name: string
  condition: {
    metric: string
    operator: '>' | '<' | '=' | '>=' | '<=' | '!='
    value: number
    period?: string
  }
  actions: AlertAction[]
  enabled: boolean
  lastTriggered?: Date
  triggerCount: number
}

/**
 * Alert action definition
 */
export interface AlertAction {
  type: 'email' | 'sms' | 'webhook' | 'dashboard' | 'log'
  target: string
  template?: string
  priority: 'low' | 'medium' | 'high' | 'critical'
}

/**
 * Portfolio analytics state
 */
export interface PortfolioAnalytics {
  totalAccounts: number
  activeAccounts: number
  totalCapital: number
  totalPnL: number
  totalReturn: number
  averageReturn: number
  portfolioSharpe: number
  portfolioDrawdown: number
  diversificationRatio: number
  correlationMatrix: number[][]
  riskContribution: Record<string, number>
  performanceAttribution: Record<string, number>
  optimalWeights: Record<string, number>
}

/**
 * Performance cache entry
 */
export interface PerformanceCache {
  key: string
  data: any
  timestamp: Date
  expiresAt: Date
  hitCount: number
  lastAccessed: Date
}

/**
 * Database query performance metrics
 */
export interface QueryPerformance {
  queryId: string
  query: string
  executionTime: number
  rowsReturned: number
  cached: boolean
  timestamp: Date
}

/**
 * Export format types
 */
export type ExportFormat = 'pdf' | 'csv' | 'excel' | 'json'

/**
 * Export configuration options
 */
export interface ExportConfig {
  format: ExportFormat
  includeCharts: boolean
  includeRawData: boolean
  includeAnalysis: boolean
  chartResolution: 'low' | 'medium' | 'high'
  dateFormat: string
  numberFormat: string
  currency: string
  timezone: string
  compression: boolean
  encryption: boolean
}

/**
 * Audit entry for compliance tracking
 */
export interface AuditEntry {
  id: string
  timestamp: Date
  userId: string
  action: string
  resource: string
  details: Record<string, any>
  severity: 'info' | 'warning' | 'error' | 'critical'
}

/**
 * Regulatory compliance metrics
 */
export interface RegulatoryMetrics {
  mifidCompliant: boolean
  nfaCompliant: boolean
  esmaCompliant: boolean
  bestExecutionScore: number
  orderToTradeRatio: number
  cancelRatio: number
  messagingRate: number
  marketImpact: number
  slippageCost: number
}