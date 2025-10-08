/**
 * Real-time Data with Fallback Hook
 *
 * Implements WebSocket with polling fallback:
 * - Primary: WebSocket for real-time updates
 * - Fallback: HTTP polling when WebSocket fails
 * - Automatic WebSocket reconnection attempts
 * - Seamless switching between modes
 *
 * Features:
 * - WebSocket → Polling fallback
 * - Automatic reconnection
 * - Mode status tracking
 * - Configurable intervals
 */

import { useEffect, useState, useRef, useCallback } from 'react'
import { ReconnectingWebSocket, WebSocketStatus } from '@/lib/websocket/reconnectingWebSocket'

export type DataMode = 'websocket' | 'polling'

export interface RealtimeDataOptions {
  wsUrl: string
  pollingUrl: string
  pollingIntervalMs?: number
  wsReconnectIntervalMs?: number
  enabled?: boolean
}

export interface UseRealtimeDataWithFallbackResult<T> {
  data: T | null
  mode: DataMode
  status: WebSocketStatus
  isLoading: boolean
  refetch: () => Promise<void>
}

export function useRealtimeDataWithFallback<T>({
  wsUrl,
  pollingUrl,
  pollingIntervalMs = 5000,
  wsReconnectIntervalMs = 60000,
  enabled = true,
}: RealtimeDataOptions): UseRealtimeDataWithFallbackResult<T> {
  const [data, setData] = useState<T | null>(null)
  const [mode, setMode] = useState<DataMode>('websocket')
  const [status, setStatus] = useState<WebSocketStatus>('connecting')
  const [isLoading, setIsLoading] = useState(true)

  const wsRef = useRef<ReconnectingWebSocket | null>(null)
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const wsReconnectIntervalRef = useRef<NodeJS.Timeout | null>(null)

  const poll = useCallback(async () => {
    try {
      const response = await fetch(pollingUrl)
      if (response.ok) {
        const newData = await response.json()
        setData(newData)
        setIsLoading(false)
      }
    } catch (error) {
      console.error('Polling failed:', error)
    }
  }, [pollingUrl])

  const startPolling = useCallback(() => {
    if (pollingIntervalRef.current) return

    setMode('polling')

    // Initial poll
    poll()

    // Start polling interval
    pollingIntervalRef.current = setInterval(poll, pollingIntervalMs)
  }, [poll, pollingIntervalMs])

  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current)
      pollingIntervalRef.current = null
    }
  }, [])

  const startWebSocket = useCallback(() => {
    if (!enabled) return

    const ws = new ReconnectingWebSocket(wsUrl)

    ws.onMessage((newData) => {
      setData(newData)
      setIsLoading(false)
      if (mode !== 'websocket') {
        setMode('websocket')
      }
    })

    ws.onStatusChange((newStatus) => {
      setStatus(newStatus)
    })

    ws.onOpen(() => {
      setIsLoading(false)
    })

    ws.onReconnect(() => {
      console.log('WebSocket reconnected - stopping polling')
      stopPolling()
      setMode('websocket')

      // Stop WebSocket reconnection attempts
      if (wsReconnectIntervalRef.current) {
        clearInterval(wsReconnectIntervalRef.current)
        wsReconnectIntervalRef.current = null
      }
    })

    ws.onFallback(() => {
      console.log('WebSocket fallback triggered - starting polling')
      startPolling()

      // Attempt WebSocket reconnection periodically
      wsReconnectIntervalRef.current = setInterval(() => {
        console.log('Attempting WebSocket reconnection...')

        // Close old WebSocket
        ws.close()

        // Start new WebSocket
        const newWs = new ReconnectingWebSocket(wsUrl)

        newWs.onMessage((newData) => {
          setData(newData)
          setIsLoading(false)
          setMode('websocket')
          stopPolling()

          if (wsReconnectIntervalRef.current) {
            clearInterval(wsReconnectIntervalRef.current)
            wsReconnectIntervalRef.current = null
          }

          // Replace old WebSocket reference
          wsRef.current = newWs
        })

        newWs.onStatusChange((newStatus) => {
          setStatus(newStatus)
        })
      }, wsReconnectIntervalMs)
    })

    wsRef.current = ws
  }, [wsUrl, enabled, mode, stopPolling, startPolling, wsReconnectIntervalMs])

  useEffect(() => {
    if (enabled) {
      startWebSocket()
    }

    return () => {
      wsRef.current?.close()
      stopPolling()
      if (wsReconnectIntervalRef.current) {
        clearInterval(wsReconnectIntervalRef.current)
      }
    }
  }, [enabled, startWebSocket, stopPolling])

  const refetch = useCallback(async () => {
    if (mode === 'polling') {
      await poll()
    }
  }, [mode, poll])

  return {
    data,
    mode,
    status,
    isLoading,
    refetch,
  }
}
