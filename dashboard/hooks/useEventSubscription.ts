/**
 * Hook for subscribing to WebSocket events and converting them to notifications
 * Integrates with Circuit Breaker, Orchestrator, AI Agents, and Execution Engine
 */

'use client'

import { useEffect, useCallback, useState } from 'react'
import { NotificationPriority } from '@/types/notifications'
import { useToasts } from './useToasts'
import { getOrchestratorEventStream, SystemEvent } from '@/services/eventStreamService'

// Event data type
type EventData = Record<string, unknown>

// Event type to notification configuration mapping
const EVENT_CONFIG: Record<string, {
  priority: NotificationPriority | ((data: EventData) => NotificationPriority)
  title: string | ((data: EventData) => string)
  icon?: string | ((data: EventData) => string)
  groupKey?: string | null
  formatMessage: (data: EventData) => string
  actions?: (data: EventData) => Array<{ label: string; action: () => void; variant: 'primary' | 'secondary' }>
}> = {
  // Circuit Breaker Events
  'circuit_breaker.triggered': {
    priority: NotificationPriority.CRITICAL,
    title: 'Circuit Breaker Triggered',
    icon: '⚠️',
    groupKey: null, // Never group
    formatMessage: (data) => `Trading halted: ${(data.reason as string) || 'Safety threshold exceeded'}`,
    actions: () => [{
      label: 'View Status',
      action: () => window.location.href = '/system-control',
      variant: 'primary'
    }]
  },
  'circuit_breaker.threshold_warning': {
    priority: NotificationPriority.WARNING,
    title: 'Circuit Breaker Warning',
    icon: '⚡',
    groupKey: 'circuit_breaker',
    formatMessage: (data) => `Approaching threshold: ${data.metric} at ${data.value}%`,
  },
  'circuit_breaker.reset': {
    priority: NotificationPriority.SUCCESS,
    title: 'Circuit Breaker Reset',
    icon: '✓',
    groupKey: 'circuit_breaker',
    formatMessage: () => 'Trading resumed - all safety checks passed',
  },

  // Trade Events
  'trade.opened': {
    priority: NotificationPriority.INFO,
    title: (data) => `Trade Opened: ${data.instrument}`,
    icon: '📈',
    groupKey: 'trade_opened',
    formatMessage: (data) => `${data.direction} ${data.units} units at ${data.price}`,
    actions: (data) => [{
      label: 'View Trade',
      action: () => window.location.href = `/trades/${data.trade_id}`,
      variant: 'secondary'
    }]
  },
  'trade.closed': {
    priority: (data) => data.pnl > 0 ? NotificationPriority.SUCCESS : NotificationPriority.WARNING,
    title: (data) => `Trade Closed: ${data.instrument}`,
    icon: (data) => data.pnl > 0 ? '✓' : '⚠️',
    groupKey: 'trade_closed',
    formatMessage: (data) => {
      const pnl = data.pnl as number
      const pnlPercent = data.pnl_percent as number
      return `P&L: ${pnl >= 0 ? '+' : '-'}$${Math.abs(pnl).toFixed(2)} (${pnlPercent >= 0 ? '+' : ''}${pnlPercent.toFixed(2)}%)`
    },
    actions: (data) => [{
      label: 'View Trade',
      action: () => window.location.href = `/trades/${data.trade_id}`,
      variant: 'secondary'
    }]
  },
  'trade.rejected': {
    priority: NotificationPriority.WARNING,
    title: 'Trade Rejected',
    icon: '⚠️',
    groupKey: 'trade_rejected',
    formatMessage: (data) => `${data.instrument}: ${data.reason || 'Order rejected by broker'}`,
  },

  // Agent Health Events
  'agent.health.changed': {
    priority: (data) => {
      if (data.status === 'failed') return NotificationPriority.CRITICAL
      if (data.status === 'degraded') return NotificationPriority.WARNING
      return NotificationPriority.SUCCESS
    },
    title: (data) => `${data.agent_name as string}: ${data.status as string}`,
    icon: (data) => data.status === 'healthy' ? '✓' : '⚠️',
    groupKey: 'agent_health',
    formatMessage: (data) => (data.reason as string) || `Agent ${data.status as string}`,
    actions: (data) => data.status !== 'healthy' ? [{
      label: 'View Health',
      action: () => window.location.href = '/system-control',
      variant: 'primary'
    }] : undefined
  },

  // Execution Engine Events
  'order.filled': {
    priority: NotificationPriority.SUCCESS,
    title: 'Order Filled',
    icon: '✓',
    groupKey: 'order_filled',
    formatMessage: (data) => `${data.instrument}: ${data.units} units at ${data.price}`,
  },
  'order.rejected': {
    priority: NotificationPriority.WARNING,
    title: 'Order Rejected',
    icon: '⚠️',
    groupKey: 'order_rejected',
    formatMessage: (data) => `${data.instrument}: ${data.reason || 'Order rejected'}`,
  },
  'position.closed': {
    priority: NotificationPriority.INFO,
    title: 'Position Closed',
    icon: 'ℹ️',
    groupKey: 'position_closed',
    formatMessage: (data) => `${data.instrument}: Position closed`,
  },

  // System Events
  'system.error': {
    priority: NotificationPriority.CRITICAL,
    title: 'System Error',
    icon: '⚠️',
    groupKey: null,
    formatMessage: (data) => (data.message as string) || 'An unexpected error occurred',
    actions: () => [{
      label: 'View Logs',
      action: () => window.location.href = '/system-control',
      variant: 'primary'
    }]
  },
  'system.warning': {
    priority: NotificationPriority.WARNING,
    title: 'System Warning',
    icon: '⚡',
    groupKey: 'system_warning',
    formatMessage: (data) => data.message || 'System warning detected',
  }
}

export function useEventSubscription() {
  const { showToast } = useToasts()
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'connecting'>('connecting')

  const handleEvent = useCallback((event: SystemEvent) => {
    const config = EVENT_CONFIG[event.type]

    if (!config) {
      console.warn(`[EventSubscription] Unknown event type: ${event.type}`)
      return
    }

    // Resolve dynamic values
    const priority = typeof config.priority === 'function'
      ? config.priority(event.data)
      : config.priority

    const title = typeof config.title === 'function'
      ? config.title(event.data)
      : config.title

    const icon = config.icon
      ? typeof config.icon === 'function'
        ? config.icon(event.data)
        : config.icon
      : undefined

    const message = config.formatMessage(event.data)

    const actions = config.actions?.(event.data)

    // Show toast notification
    showToast({
      priority,
      title,
      message,
      icon,
      timestamp: new Date(event.timestamp),
      groupKey: config.groupKey,
      actions
    })
  }, [showToast])

  useEffect(() => {
    const eventStream = getOrchestratorEventStream()

    // Subscribe to events
    const unsubscribe = eventStream.subscribe(handleEvent)

    // Connect to WebSocket
    eventStream.connect()

    // Monitor connection status
    const statusInterval = setInterval(() => {
      const isConnected = eventStream.getConnectionStatus()
      setConnectionStatus(isConnected ? 'connected' : 'disconnected')
    }, 1000)

    return () => {
      unsubscribe()
      clearInterval(statusInterval)
      eventStream.disconnect()
    }
  }, [handleEvent])

  return {
    connectionStatus
  }
}
