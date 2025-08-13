/**
 * System control panel data types for monitoring and controlling the trading system
 */

/**
 * Agent types in the trading system
 */
export type AgentType = 
  | 'circuit_breaker'
  | 'wyckoff_analyzer' 
  | 'risk_manager'
  | 'execution_controller'
  | 'anti_correlation'
  | 'performance_tracker'
  | 'compliance_monitor'
  | 'personality_engine'

/**
 * Agent status levels
 */
export type AgentStatus = 'active' | 'idle' | 'error' | 'stopped' | 'restarting'

/**
 * Circuit breaker states
 */
export type CircuitBreakerStatus = 'closed' | 'open' | 'half-open'

/**
 * Trading session states
 */
export type TradingSessionStatus = 'active' | 'paused' | 'stopped'

/**
 * System log severity levels
 */
export type LogLevel = 'debug' | 'info' | 'warn' | 'error' | 'critical'

/**
 * Risk parameter categories
 */
export type RiskParameterCategory = 'position_sizing' | 'drawdown' | 'exposure' | 'time_limits'

/**
 * Emergency stop reasons
 */
export type EmergencyStopReason = 
  | 'market_volatility'
  | 'system_error'
  | 'compliance_violation'
  | 'manual_intervention'
  | 'external_event'
  | 'scheduled_maintenance'

/**
 * Individual AI agent status and performance metrics
 */
export interface AgentStatusInfo {
  /** Unique agent identifier */
  id: string
  /** Human-readable agent name */
  name: string
  /** Type of agent (specialized function) */
  type: AgentType
  /** Current operational status */
  status: AgentStatus
  /** Uptime in milliseconds */
  uptime: number
  /** Last heartbeat received */
  lastHeartbeat: Date
  /** Performance metrics */
  performanceMetrics: {
    /** Total tasks completed */
    tasksCompleted: number
    /** Error count */
    errors: number
    /** Average response time in ms */
    avgResponseTime: number
    /** Success rate percentage */
    successRate: number
  }
  /** Resource usage statistics */
  resourceUsage: {
    /** CPU usage percentage */
    cpu: number
    /** Memory usage in MB */
    memory: number
    /** Memory usage percentage */
    memoryPercentage: number
  }
  /** Agent configuration */
  config: {
    /** Maximum concurrent tasks */
    maxConcurrentTasks: number
    /** Timeout for tasks in ms */
    taskTimeout: number
    /** Restart policy */
    restartPolicy: 'never' | 'on-failure' | 'always'
  }
  /** Last error message if any */
  lastError?: string
  /** Version information */
  version: string
}

/**
 * Circuit breaker configuration and status
 */
export interface CircuitBreakerInfo {
  /** Unique circuit breaker identifier */
  id: string
  /** Human-readable name */
  name: string
  /** Current state */
  status: CircuitBreakerStatus
  /** Failure threshold before opening */
  threshold: number
  /** Current failure count */
  failures: number
  /** Last time the breaker was triggered */
  lastTriggered?: Date
  /** Automatic reset time */
  resetTime?: Date
  /** Manual override is active */
  isManualOverride: boolean
  /** Success rate percentage */
  successRate: number
  /** Description of what this breaker protects */
  description: string
  /** Category/component this breaker belongs to */
  category: string
}

/**
 * Risk parameter definition and current value
 */
export interface RiskParameter {
  /** Unique parameter identifier */
  id: string
  /** Parameter name */
  name: string
  /** Parameter category */
  category: RiskParameterCategory
  /** Current value */
  value: number | string | boolean
  /** Minimum allowed value */
  minValue?: number
  /** Maximum allowed value */
  maxValue?: number
  /** Unit of measurement */
  unit?: string
  /** Parameter description */
  description: string
  /** Last modification timestamp */
  lastModified: Date
  /** User who last modified */
  modifiedBy: string
  /** Whether parameter requires system restart */
  requiresRestart: boolean
  /** Validation regex for string values */
  validationPattern?: string
}

/**
 * System log entry
 */
export interface SystemLogEntry {
  /** Unique log entry identifier */
  id: string
  /** Log timestamp */
  timestamp: Date
  /** Log severity level */
  level: LogLevel
  /** Component that generated the log */
  component: string
  /** Log message */
  message: string
  /** Additional context data */
  context?: Record<string, any>
  /** Related account ID if applicable */
  accountId?: string
  /** User ID if user-initiated */
  userId?: string
  /** Error stack trace if applicable */
  stackTrace?: string
  /** Request ID for correlation */
  requestId?: string
}

/**
 * Trading session information for an account
 */
export interface TradingSession {
  /** Account identifier */
  accountId: string
  /** Account name for display */
  accountName: string
  /** Current trading status */
  status: TradingSessionStatus
  /** User who paused the session */
  pausedBy?: string
  /** Reason for pause */
  pauseReason?: string
  /** Timestamp when paused */
  pausedAt?: Date
  /** Scheduled resume time */
  scheduledResume?: Date
  /** Active position count */
  activePositions: number
  /** Current P&L */
  currentPnL: number
  /** Daily trade count */
  dailyTrades: number
  /** Last trade time */
  lastTradeTime?: Date
}

/**
 * Emergency stop configuration and status
 */
export interface EmergencyStopStatus {
  /** Whether emergency stop is active */
  isActive: boolean
  /** Who triggered the emergency stop */
  triggeredBy?: string
  /** Reason for emergency stop */
  reason?: EmergencyStopReason
  /** Custom reason description */
  customReason?: string
  /** Timestamp when triggered */
  triggeredAt?: Date
  /** Estimated time to full stop */
  estimatedStopTime?: Date
  /** Number of accounts affected */
  affectedAccounts: number
  /** Number of positions being closed */
  positionsClosing: number
  /** Emergency contacts notified */
  contactsNotified: string[]
}

/**
 * System health overview
 */
export interface SystemHealthStatus {
  /** Overall system status */
  overallStatus: 'healthy' | 'warning' | 'critical' | 'emergency'
  /** System uptime in milliseconds */
  uptime: number
  /** Number of active agents */
  activeAgents: number
  /** Number of agents with errors */
  errorAgents: number
  /** Active trading accounts */
  activeTradingAccounts: number
  /** Paused trading accounts */
  pausedTradingAccounts: number
  /** Open circuit breakers */
  openCircuitBreakers: number
  /** Critical log count in last hour */
  criticalLogs: number
  /** System performance metrics */
  performance: {
    /** CPU usage percentage */
    cpu: number
    /** Memory usage percentage */
    memory: number
    /** Disk usage percentage */
    disk: number
    /** Network latency in ms */
    networkLatency: number
  }
}

/**
 * Risk parameter update request
 */
export interface RiskParameterUpdate {
  /** Parameter ID to update */
  parameterId: string
  /** New value */
  newValue: number | string | boolean
  /** Reason for change */
  changeReason: string
  /** Whether to apply immediately */
  applyImmediately: boolean
}

/**
 * Emergency stop request
 */
export interface EmergencyStopRequest {
  /** Reason for emergency stop */
  reason: EmergencyStopReason
  /** Custom reason description */
  customReason?: string
  /** Confirmation code */
  confirmationCode: string
  /** Whether to notify emergency contacts */
  notifyContacts: boolean
}

/**
 * Agent control actions
 */
export type AgentAction = 'restart' | 'stop' | 'start' | 'reset_errors'

/**
 * Agent control request
 */
export interface AgentControlRequest {
  /** Agent ID to control */
  agentId: string
  /** Action to perform */
  action: AgentAction
  /** Reason for action */
  reason: string
}

/**
 * Circuit breaker control request
 */
export interface CircuitBreakerControlRequest {
  /** Circuit breaker ID */
  breakerId: string
  /** Action (open, close, reset) */
  action: 'open' | 'close' | 'reset'
  /** Reason for manual override */
  reason: string
  /** Duration for manual override (minutes) */
  overrideDuration?: number
}

/**
 * Trading session control request
 */
export interface TradingSessionControlRequest {
  /** Account ID or 'global' for all accounts */
  accountId: string
  /** Action to perform */
  action: 'pause' | 'resume' | 'stop'
  /** Reason for action */
  reason: string
  /** Scheduled resume time for pause action */
  scheduledResume?: Date
}

/**
 * Log filter options
 */
export interface LogFilter {
  /** Filter by log level */
  level?: LogLevel[]
  /** Filter by component */
  component?: string[]
  /** Filter by account ID */
  accountId?: string
  /** Filter by user ID */
  userId?: string
  /** Filter by time range */
  timeRange?: {
    start: Date
    end: Date
  }
  /** Search in message content */
  searchQuery?: string
  /** Maximum number of results */
  limit?: number
  /** Offset for pagination */
  offset?: number
}

/**
 * System notification
 */
export interface SystemNotification {
  /** Notification ID */
  id: string
  /** Notification type */
  type: 'info' | 'warning' | 'error' | 'success'
  /** Notification title */
  title: string
  /** Notification message */
  message: string
  /** Timestamp */
  timestamp: Date
  /** Whether notification has been read */
  isRead: boolean
  /** Related component or entity */
  source: string
  /** Action URL if applicable */
  actionUrl?: string
}

/**
 * Complete system control panel state
 */
export interface SystemControlPanelData {
  /** Overall system health */
  systemHealth: SystemHealthStatus
  /** Emergency stop status */
  emergencyStop: EmergencyStopStatus
  /** All agent statuses */
  agents: AgentStatusInfo[]
  /** Circuit breaker statuses */
  circuitBreakers: CircuitBreakerInfo[]
  /** Trading session statuses */
  tradingSessions: TradingSession[]
  /** Current risk parameters */
  riskParameters: RiskParameter[]
  /** Recent system logs */
  recentLogs: SystemLogEntry[]
  /** System notifications */
  notifications: SystemNotification[]
  /** Last update timestamp */
  lastUpdate: Date
}