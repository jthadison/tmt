/**
 * Real-time Updates Hook
 * Manages WebSocket/SSE connection for live trading system updates
 */

'use client'

import { useState, useEffect, useCallback, useRef } from 'react'

export interface RealtimeUpdate {
  type: 'connected' | 'update' | 'error' | 'heartbeat'
  timestamp: number
  message?: string
  error?: string
  data?: {
    systemStatus?: any
    recentTrades?: any[]
    openTradeCount?: number
    totalPnL?: number
  }
}

interface UseRealtimeUpdatesOptions {
  /** Enable real-time updates */
  enabled?: boolean
  /** Callback when update received */
  onUpdate?: (update: RealtimeUpdate) => void
  /** Callback when error occurs */
  onError?: (error: Error) => void
  /** Callback when connection status changes */
  onConnectionChange?: (connected: boolean) => void
}

interface UseRealtimeUpdatesReturn {
  /** Connection status */
  connected: boolean
  /** Latest update */
  lastUpdate: RealtimeUpdate | null
  /** Connection error */
  error: string | null
  /** Manually reconnect */
  reconnect: () => void
  /** Disconnect */
  disconnect: () => void
  /** Recent updates history */
  updateHistory: RealtimeUpdate[]
}

export function useRealtimeUpdates({
  enabled = true,
  onUpdate,
  onError,
  onConnectionChange
}: UseRealtimeUpdatesOptions = {}): UseRealtimeUpdatesReturn {
  const [connected, setConnected] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<RealtimeUpdate | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [updateHistory, setUpdateHistory] = useState<RealtimeUpdate[]>([])
  
  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttemptsRef = useRef(0)
  
  const MAX_RECONNECT_ATTEMPTS = 5
  const RECONNECT_DELAY = 5000
  const MAX_HISTORY_SIZE = 50
  
  /**
   * Connect to real-time updates
   */
  const connect = useCallback(() => {
    if (!enabled || eventSourceRef.current) return
    
    try {
      console.log('Connecting to real-time updates...')
      
      const eventSource = new EventSource('/api/websocket')
      eventSourceRef.current = eventSource
      
      eventSource.onopen = () => {
        console.log('Real-time connection opened')
        setConnected(true)
        setError(null)
        reconnectAttemptsRef.current = 0
        
        if (onConnectionChange) {
          onConnectionChange(true)
        }
      }
      
      eventSource.onmessage = (event) => {
        try {
          const update: RealtimeUpdate = JSON.parse(event.data)
          
          setLastUpdate(update)
          
          // Add to history
          setUpdateHistory(prev => {
            const newHistory = [update, ...prev].slice(0, MAX_HISTORY_SIZE)
            return newHistory
          })
          
          if (onUpdate) {
            onUpdate(update)
          }
          
          // Reset error on successful message
          if (error) {
            setError(null)
          }
          
        } catch (err) {
          console.error('Failed to parse update:', err)
          setError('Failed to parse update data')
        }
      }
      
      eventSource.onerror = (event) => {
        console.error('Real-time connection error:', event)
        setConnected(false)
        setError('Connection error')
        
        if (onConnectionChange) {
          onConnectionChange(false)
        }
        
        if (onError) {
          onError(new Error('Real-time connection error'))
        }
        
        // Attempt reconnection
        attemptReconnect()
      }
      
    } catch (err) {
      console.error('Failed to create EventSource:', err)
      setError('Failed to create connection')
      
      if (onError) {
        onError(err instanceof Error ? err : new Error('Connection failed'))
      }
    }
  }, [enabled, error, onUpdate, onError, onConnectionChange])
  
  /**
   * Disconnect from real-time updates
   */
  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    
    setConnected(false)
    
    if (onConnectionChange) {
      onConnectionChange(false)
    }
  }, [onConnectionChange])
  
  /**
   * Attempt to reconnect
   */
  const attemptReconnect = useCallback(() => {
    if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
      console.log('Max reconnection attempts reached')
      setError('Connection failed - max attempts reached')
      return
    }
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    
    reconnectAttemptsRef.current++
    
    console.log(`Attempting reconnection (${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})`)
    
    reconnectTimeoutRef.current = setTimeout(() => {
      disconnect()
      connect()
    }, RECONNECT_DELAY)
    
  }, [connect, disconnect])
  
  /**
   * Manual reconnect
   */
  const reconnect = useCallback(() => {
    reconnectAttemptsRef.current = 0
    disconnect()
    setTimeout(connect, 1000)
  }, [connect, disconnect])
  
  /**
   * Setup and cleanup effects
   */
  useEffect(() => {
    if (enabled) {
      connect()
    } else {
      disconnect()
    }
    
    return () => {
      disconnect()
    }
  }, [enabled, connect, disconnect])
  
  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [])
  
  return {
    connected,
    lastUpdate,
    error,
    reconnect,
    disconnect,
    updateHistory
  }
}