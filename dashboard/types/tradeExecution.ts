/**
 * TypeScript types and interfaces for Trade Execution Monitoring
 * Story 9.4: Trade Execution Monitoring Interface
 */

export type ExecutionStatus = 
  | 'pending' 
  | 'submitted' 
  | 'acknowledged' 
  | 'partial' 
  | 'filled' 
  | 'rejected' 
  | 'cancelled' 
  | 'expired'

export type OrderDirection = 'buy' | 'sell'

export type AlertSeverity = 'info' | 'warning' | 'error' | 'critical'

export type ExecutionAlertType = 
  | 'execution_failed'
  | 'high_slippage'
  | 'partial_fill'
  | 'execution_delay'
  | 'rejection'
  | 'timeout'

export type TimeframePeriod = '1h' | '1d' | '1w' | '1m' | 'custom'

/**
 * Individual partial fill within an order
 */
export interface PartialFill {
  id: string
  timestamp: Date
  size: number
  price: number
  fees: number
  venue?: string
}

/**
 * Timestamps tracking order lifecycle
 */
export interface OrderTimestamps {
  created: Date
  submitted: Date
  acknowledged?: Date
  partialFills: PartialFill[]
  completed?: Date
  cancelled?: Date
  lastUpdate: Date
}

/**
 * Trading fees and commissions
 */
export interface TradeFees {
  commission: number
  spread: number
  swapFee?: number
  regulatoryFee?: number
  total: number
  currency: string
}

/**
 * Core trade execution data
 */
export interface TradeExecution {
  id: string
  accountId: string
  accountAlias: string
  orderId: string
  instrument: string
  direction: OrderDirection
  requestedSize: number
  executedSize: number
  remainingSize: number
  requestedPrice?: number
  averagePrice?: number
  executedPrice?: number
  marketPrice?: number
  slippage: number
  slippagePercent: number
  status: ExecutionStatus
  timestamps: OrderTimestamps
  broker: string
  platform: string
  fees: TradeFees
  relatedOrders: string[]
  parentOrderId?: string
  tags: string[]
  metadata: Record<string, any>
  reasonCode?: string
  reasonMessage?: string
  venue?: string
  priority: 'low' | 'normal' | 'high' | 'urgent'
}

/**
 * Execution quality metrics for analysis
 */
export interface ExecutionMetrics {
  // Basic metrics
  totalExecutions: number
  successfulExecutions: number
  failedExecutions: number
  partialExecutions: number
  cancelledExecutions: number
  
  // Quality metrics
  fillRate: number
  averageSlippage: number
  averageSlippagePercent: number
  averageExecutionSpeed: number
  rejectionRate: number
  
  // Performance metrics
  fastestExecution: number
  slowestExecution: number
  medianExecutionSpeed: number
  
  // Volume metrics
  totalVolumeTraded: number
  averageTradeSize: number
  
  // Cost metrics
  totalFees: number
  averageFees: number
  
  // Time-based metrics
  periodStart: Date
  periodEnd: Date
  executionsPerHour: number
}

/**
 * Aggregated metrics by different dimensions
 */
export interface AggregatedMetrics {
  overall: ExecutionMetrics
  byAccount: Map<string, ExecutionMetrics>
  byInstrument: Map<string, ExecutionMetrics>
  byBroker: Map<string, ExecutionMetrics>
  byStatus: Map<ExecutionStatus, number>
  byHour: Map<number, ExecutionMetrics>
  timeframe: TimeframePeriod
  lastUpdate: Date
}

/**
 * Execution alert configuration
 */
export interface ExecutionAlertRule {
  id: string
  name: string
  type: ExecutionAlertType
  severity: AlertSeverity
  enabled: boolean
  conditions: {
    slippageThreshold?: number
    delayThreshold?: number
    rejectionRateThreshold?: number
    volumeThreshold?: number
    accountIds?: string[]
    instruments?: string[]
    brokers?: string[]
  }
  notifications: {
    email?: boolean
    sms?: boolean
    dashboard?: boolean
    webhook?: string
  }
  cooldownPeriod: number // minutes
  createdAt: Date
  updatedAt: Date
}

/**
 * Individual execution alert
 */
export interface ExecutionAlert {
  id: string
  ruleId: string
  ruleName: string
  type: ExecutionAlertType
  severity: AlertSeverity
  title: string
  message: string
  executionId?: string
  accountId?: string
  instrument?: string
  broker?: string
  timestamp: Date
  acknowledged: boolean
  acknowledgedBy?: string
  acknowledgedAt?: Date
  resolved: boolean
  resolvedAt?: Date
  metadata: Record<string, any>
}

/**
 * Filter configuration for trade execution feed
 */
export interface ExecutionFilter {
  accounts?: string[]
  instruments?: string[]
  statuses?: ExecutionStatus[]
  brokers?: string[]
  directions?: OrderDirection[]
  timeRange?: {
    start: Date
    end: Date
  }
  minSize?: number
  maxSize?: number
  minSlippage?: number
  maxSlippage?: number
  searchQuery?: string
  priorities?: ('low' | 'normal' | 'high' | 'urgent')[]
}

/**
 * Sort configuration for executions
 */
export interface ExecutionSort {
  field: 'timestamp' | 'instrument' | 'size' | 'slippage' | 'status' | 'account'
  direction: 'asc' | 'desc'
}

/**
 * Real-time execution update via WebSocket
 */
export interface ExecutionUpdate {
  type: 'execution_created' | 'execution_updated' | 'execution_completed' | 'alert_triggered'
  execution?: TradeExecution
  alert?: ExecutionAlert
  timestamp: Date
  accountId?: string
}

/**
 * Export configuration for execution data
 */
export interface ExecutionExportConfig {
  format: 'csv' | 'json' | 'xlsx'
  filter: ExecutionFilter
  fields: string[]
  timeRange: {
    start: Date
    end: Date
  }
  includeFees: boolean
  includeMetadata: boolean
}

/**
 * Order lifecycle stage for tracking
 */
export interface OrderLifecycleStage {
  id: string
  name: string
  timestamp: Date
  duration?: number
  status: 'completed' | 'current' | 'pending' | 'failed'
  details?: string
  latencyMs?: number
  expected: boolean
}

/**
 * Complete order lifecycle tracking
 */
export interface OrderLifecycle {
  orderId: string
  executionId: string
  stages: OrderLifecycleStage[]
  totalDuration: number
  currentStage: string
  isComplete: boolean
  hasErrors: boolean
  warnings: string[]
  expectedStages: string[]
  actualStages: string[]
}

/**
 * Real-time feed configuration
 */
export interface ExecutionFeedConfig {
  maxItems: number
  autoScroll: boolean
  showNotifications: boolean
  soundEnabled: boolean
  filter: ExecutionFilter
  sort: ExecutionSort
  refreshInterval: number // seconds
  pauseUpdates: boolean
}

/**
 * Chart data point for execution metrics visualization
 */
export interface MetricsDataPoint {
  timestamp: Date
  value: number
  label?: string
  metadata?: Record<string, any>
}

/**
 * Execution metrics chart configuration
 */
export interface MetricsChartConfig {
  type: 'line' | 'bar' | 'area' | 'pie'
  metric: keyof ExecutionMetrics
  timeframe: TimeframePeriod
  aggregation: 'sum' | 'average' | 'min' | 'max' | 'count'
  groupBy?: 'account' | 'instrument' | 'broker' | 'hour'
  showTrend: boolean
  compareWithPrevious: boolean
}

/**
 * API response wrapper for execution data
 */
export interface ExecutionApiResponse<T> {
  success: boolean
  data?: T
  error?: string
  timestamp: Date
  requestId: string
  pagination?: {
    page: number
    pageSize: number
    total: number
    hasNext: boolean
    hasPrevious: boolean
  }
}

/**
 * WebSocket connection status
 */
export interface WebSocketStatus {
  connected: boolean
  url: string
  lastMessage?: Date
  reconnectAttempts: number
  error?: string
  latency?: number
}

/**
 * Hook state for trade execution data management
 */
export interface UseTradeExecutionState {
  executions: TradeExecution[]
  metrics: AggregatedMetrics | null
  alerts: ExecutionAlert[]
  alertRules: ExecutionAlertRule[]
  isLoading: boolean
  error: string | null
  lastUpdate: Date | null
  wsStatus: WebSocketStatus
  filter: ExecutionFilter
  sort: ExecutionSort
  feedConfig: ExecutionFeedConfig
}

/**
 * Performance benchmarks for optimization
 */
export interface PerformanceBenchmarks {
  renderTime: number // ms
  updateLatency: number // ms
  memoryUsage: number // MB
  wsMessageRate: number // messages/second
  apiResponseTime: number // ms
  targetRenderTime: number // <100ms
  targetUpdateLatency: number // <50ms
}