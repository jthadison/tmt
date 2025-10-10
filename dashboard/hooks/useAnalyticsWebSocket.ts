/**
 * Analytics WebSocket Hook (Story 12.2 - Task 12)
 *
 * WebSocket integration for real-time analytics updates when new trades are executed
 */

'use client'

import { useEffect, useCallback, useRef } from 'react'
import { useWebSocket } from './useWebSocket'

interface UseAnalyticsWebSocketOptions {
  onTradeExecuted?: () => void
  enabled?: boolean
}

/**
 * Hook for WebSocket real-time analytics updates
 * @param options Configuration options
 * @returns WebSocket connection status
 */
export function useAnalyticsWebSocket({
  onTradeExecuted,
  enabled = true
}: UseAnalyticsWebSocketOptions = {}) {
  const onTradeExecutedRef = useRef(onTradeExecuted)
  const lastNotificationRef = useRef<number>(0)

  // Update ref when callback changes
  useEffect(() => {
    onTradeExecutedRef.current = onTradeExecuted
  }, [onTradeExecuted])

  // WebSocket connection
  const { connectionStatus, lastMessage, isConnected } = useWebSocket({
    url: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8089/ws',
    reconnectAttempts: 5,
    reconnectInterval: 5000,
    enableHeartbeat: true,
  })

  // Handle incoming WebSocket messages
  useEffect(() => {
    if (!enabled || !lastMessage) return

    try {
      // Check for trade execution events (type is string, not MessageType enum)
      const messageType = lastMessage.type?.toString() || ''
      if (
        messageType === 'trade_executed' ||
        messageType === 'trade.executed' ||
        messageType === 'trade_closed' ||
        messageType === 'trade.closed'
      ) {
        const now = Date.now()

        // Debounce notifications (max 1 per second)
        if (now - lastNotificationRef.current < 1000) {
          return
        }

        lastNotificationRef.current = now

        // Show toast notification
        if (typeof window !== 'undefined' && 'Notification' in window) {
          if (Notification.permission === 'granted') {
            new Notification('New Trade Recorded', {
              body: 'Analytics data updated with new trade',
              icon: '/icon-192.png',
              tag: 'trade-notification',
            })
          }
        }

        // Trigger callback
        if (onTradeExecutedRef.current) {
          onTradeExecutedRef.current()
        }
      }
    } catch (error) {
      console.error('Error handling WebSocket message:', error)
    }
  }, [lastMessage, enabled])

  // Request notification permission on mount
  useEffect(() => {
    if (
      enabled &&
      typeof window !== 'undefined' &&
      'Notification' in window &&
      Notification.permission === 'default'
    ) {
      Notification.requestPermission()
    }
  }, [enabled])

  return {
    connectionStatus,
    isConnected,
  }
}

/**
 * Hook for auto-refreshing analytics data on WebSocket events
 * @param refetchFunctions Array of refetch functions to call
 * @param enabled Whether to enable WebSocket updates
 */
export function useAnalyticsAutoRefresh(
  refetchFunctions: Array<() => Promise<void>>,
  enabled: boolean = true
) {
  const refetchAll = useCallback(async () => {
    await Promise.all(refetchFunctions.map(fn => fn()))
  }, [refetchFunctions])

  const { connectionStatus, isConnected } = useAnalyticsWebSocket({
    onTradeExecuted: refetchAll,
    enabled,
  })

  return {
    connectionStatus,
    isConnected,
    refetchAll,
  }
}
