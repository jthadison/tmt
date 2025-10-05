/**
 * Notification system types for the trading dashboard
 * Supports priority-based alerts with smart grouping
 */

export enum NotificationPriority {
  CRITICAL = 'critical',
  WARNING = 'warning',
  SUCCESS = 'success',
  INFO = 'info'
}

export interface NotificationAction {
  label: string
  action: () => void
  variant: 'primary' | 'secondary'
}

export interface Notification {
  id: string
  priority: NotificationPriority
  title: string
  message: string
  timestamp: Date
  read: boolean
  dismissed: boolean
  icon?: string
  actions?: NotificationAction[]
  relatedUrl?: string
  groupKey?: string // For smart grouping (e.g., 'trade_closed', 'agent_health')
}

export interface NotificationGroup {
  notifications: Notification[]
  count: number
  isGrouped: boolean
}

export interface DateGroupedNotifications {
  today: NotificationGroup[]
  yesterday: NotificationGroup[]
  thisWeek: NotificationGroup[]
  older: NotificationGroup[]
}

/**
 * Priority configuration for visual styling
 */
export const PRIORITY_CONFIG = {
  [NotificationPriority.CRITICAL]: {
    color: 'red',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500',
    textColor: 'text-red-500',
    icon: '⚠️'
  },
  [NotificationPriority.WARNING]: {
    color: 'yellow',
    bgColor: 'bg-yellow-500/10',
    borderColor: 'border-yellow-500',
    textColor: 'text-yellow-500',
    icon: '⚡'
  },
  [NotificationPriority.SUCCESS]: {
    color: 'green',
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500',
    textColor: 'text-green-500',
    icon: '✓'
  },
  [NotificationPriority.INFO]: {
    color: 'blue',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500',
    textColor: 'text-blue-500',
    icon: 'ℹ️'
  }
} as const

/**
 * Notification event source configurations
 */
export const NOTIFICATION_SOURCES = {
  // Critical - never grouped
  circuit_breaker: {
    priority: NotificationPriority.CRITICAL,
    title: 'Circuit Breaker Triggered',
    groupKey: null
  },
  system_failure: {
    priority: NotificationPriority.CRITICAL,
    title: 'System Failure',
    groupKey: null
  },
  agent_crashed: {
    priority: NotificationPriority.CRITICAL,
    title: 'Agent Crashed',
    groupKey: null
  },

  // Warning - can be grouped
  threshold_approaching: {
    priority: NotificationPriority.WARNING,
    title: 'Threshold Approaching',
    groupKey: 'threshold'
  },
  agent_degraded: {
    priority: NotificationPriority.WARNING,
    title: 'Agent Degraded',
    groupKey: 'agent_health'
  },
  high_latency: {
    priority: NotificationPriority.WARNING,
    title: 'High Latency Detected',
    groupKey: 'performance'
  },

  // Success - can be grouped
  trade_closed_profit: {
    priority: NotificationPriority.SUCCESS,
    title: 'Trade Closed Profitably',
    groupKey: 'trade_closed'
  },
  system_recovered: {
    priority: NotificationPriority.SUCCESS,
    title: 'System Recovered',
    groupKey: 'recovery'
  },
  agent_healthy: {
    priority: NotificationPriority.SUCCESS,
    title: 'Agent Healthy',
    groupKey: 'agent_health'
  },

  // Info - can be grouped
  trade_opened: {
    priority: NotificationPriority.INFO,
    title: 'Trade Opened',
    groupKey: 'trade_opened'
  },
  agent_started: {
    priority: NotificationPriority.INFO,
    title: 'Agent Started',
    groupKey: 'agent_lifecycle'
  },
  position_modified: {
    priority: NotificationPriority.INFO,
    title: 'Position Modified',
    groupKey: 'position_mod'
  }
} as const
