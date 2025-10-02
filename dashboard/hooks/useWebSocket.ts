'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { WebSocketMessage, ConnectionStatus, MessageType } from '@/types/websocket'
import { intervalConfig } from '@/config/intervals'

interface UseWebSocketOptions {
  url: string
  protocols?: string | string[]
  reconnectAttempts?: number
  reconnectInterval?: number
  heartbeatInterval?: number
  onError?: (error: Event | Error) => void
  onReconnectFailed?: () => void
  enableHeartbeat?: boolean
}

interface UseWebSocketReturn {
  connectionStatus: ConnectionStatus
  lastMessage: WebSocketMessage | null
  sendMessage: (message: any) => void
  connect: () => void
  disconnect: () => void
  isConnected: boolean
  reconnectCount: number
  lastError: Error | null
}

/**
 * Custom hook for WebSocket connection management with auto-reconnection
 * @param options - WebSocket configuration options
 * @returns WebSocket connection state and methods
 */
export function useWebSocket({
  url,
  protocols,
  reconnectAttempts = 5,
  reconnectInterval = intervalConfig.websocketReconnect,
  heartbeatInterval = intervalConfig.websocketHeartbeat,
  onError,
  onReconnectFailed,
  enableHeartbeat = true
}: UseWebSocketOptions): UseWebSocketReturn {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>(ConnectionStatus.DISCONNECTED)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const [lastError, setLastError] = useState<Error | null>(null)
  const [reconnectCount, setReconnectCount] = useState(0)
  
  const ws = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const heartbeatTimeoutRef = useRef<NodeJS.Timeout>()
  const reconnectAttemptsRef = useRef(0)
  const isManualDisconnect = useRef(false)

  // Use ref to avoid infinite loop in connect callback
  const startHeartbeatRef = useRef<() => void>()
  const onErrorRef = useRef(onError)
  const onReconnectFailedRef = useRef(onReconnectFailed)

  // Update refs when callbacks change
  useEffect(() => {
    onErrorRef.current = onError
    onReconnectFailedRef.current = onReconnectFailed
  }, [onError, onReconnectFailed])

  const startHeartbeat = useCallback(() => {
    if (!enableHeartbeat) return

    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current)
    }

    heartbeatTimeoutRef.current = setTimeout(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        try {
          ws.current.send(JSON.stringify({
            type: MessageType.HEARTBEAT,
            timestamp: new Date().toISOString(),
            correlation_id: crypto.randomUUID()
          }))
          // Use ref to call itself
          startHeartbeatRef.current?.()
        } catch (error) {
          console.error('Failed to send heartbeat:', error)
          setLastError(error as Error)
        }
      }
    }, heartbeatInterval)
  }, [heartbeatInterval, enableHeartbeat])

  // Update ref whenever startHeartbeat changes - use useEffect to avoid infinite loop
  useEffect(() => {
    startHeartbeatRef.current = startHeartbeat
  }, [startHeartbeat])

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already open, skipping connect')
      return
    }

    console.log('Attempting to connect WebSocket to:', url)
    isManualDisconnect.current = false
    setConnectionStatus(ConnectionStatus.CONNECTING)

    try {
      ws.current = new WebSocket(url, protocols)
      console.log('WebSocket instance created, waiting for connection...')

      ws.current.onopen = () => {
        console.log('✅ WebSocket connected to:', url)
        setConnectionStatus(ConnectionStatus.CONNECTED)
        setLastError(null)
        reconnectAttemptsRef.current = 0
        setReconnectCount(0)
        startHeartbeat()
      }
      
      ws.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          setLastMessage(message)
          
          // Reset error on successful message
          setLastError(null)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
          setLastError(error as Error)
        }
      }
      
      ws.current.onclose = (event) => {
        setConnectionStatus(ConnectionStatus.DISCONNECTED)
        
        if (heartbeatTimeoutRef.current) {
          clearTimeout(heartbeatTimeoutRef.current)
        }
        
        // Auto-reconnect if not manual disconnect and within retry limit
        if (!isManualDisconnect.current && reconnectAttemptsRef.current < reconnectAttempts) {
          reconnectAttemptsRef.current++
          setReconnectCount(reconnectAttemptsRef.current)
          setConnectionStatus(ConnectionStatus.RECONNECTING)
          
          const backoffDelay = reconnectInterval * Math.pow(1.5, reconnectAttemptsRef.current - 1)
          console.log(`Attempting reconnection ${reconnectAttemptsRef.current}/${reconnectAttempts} in ${backoffDelay}ms`)
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, Math.min(backoffDelay, 30000)) // Max 30 second backoff
        } else if (!isManualDisconnect.current && reconnectAttemptsRef.current >= reconnectAttempts) {
          console.error('Maximum reconnection attempts reached')
          onReconnectFailedRef.current?.()
        }
      }
      
      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error)
        const errorObj = new Error('WebSocket connection failed')
        setLastError(errorObj)
        setConnectionStatus(ConnectionStatus.ERROR)
        onErrorRef.current?.(error)
      }
      
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      setLastError(error as Error)
      setConnectionStatus(ConnectionStatus.ERROR)
      onErrorRef.current?.(error as Error)
    }
  }, [url, protocols, reconnectAttempts, reconnectInterval, startHeartbeat])

  const disconnect = useCallback(() => {
    isManualDisconnect.current = true
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current)
    }
    
    if (ws.current) {
      ws.current.close()
      ws.current = null
    }
    
    setConnectionStatus(ConnectionStatus.DISCONNECTED)
  }, [])

  const sendMessage = useCallback((message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      const wsMessage = {
        ...message,
        timestamp: new Date().toISOString(),
        correlation_id: crypto.randomUUID()
      }
      ws.current.send(JSON.stringify(wsMessage))
    } else {
      console.warn('WebSocket is not connected. Message not sent:', message)
    }
  }, [])

  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])

  return {
    connectionStatus,
    lastMessage,
    sendMessage,
    connect,
    disconnect,
    isConnected: connectionStatus === ConnectionStatus.CONNECTED,
    reconnectCount,
    lastError
  }
}