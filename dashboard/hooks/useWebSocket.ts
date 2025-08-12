'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { WebSocketMessage, ConnectionStatus, MessageType } from '@/types/websocket'

interface UseWebSocketOptions {
  url: string
  protocols?: string | string[]
  reconnectAttempts?: number
  reconnectInterval?: number
  heartbeatInterval?: number
}

interface UseWebSocketReturn {
  connectionStatus: ConnectionStatus
  lastMessage: WebSocketMessage | null
  sendMessage: (message: any) => void
  connect: () => void
  disconnect: () => void
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
  reconnectInterval = 5000,
  heartbeatInterval = 30000
}: UseWebSocketOptions): UseWebSocketReturn {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>(ConnectionStatus.DISCONNECTED)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  
  const ws = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const heartbeatTimeoutRef = useRef<NodeJS.Timeout>()
  const reconnectAttemptsRef = useRef(0)
  const isManualDisconnect = useRef(false)

  const startHeartbeat = useCallback(() => {
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current)
    }
    
    heartbeatTimeoutRef.current = setTimeout(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({
          type: MessageType.HEARTBEAT,
          timestamp: new Date().toISOString(),
          correlation_id: crypto.randomUUID()
        }))
        startHeartbeat()
      }
    }, heartbeatInterval)
  }, [heartbeatInterval])

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return
    
    isManualDisconnect.current = false
    setConnectionStatus(ConnectionStatus.CONNECTING)
    
    try {
      ws.current = new WebSocket(url, protocols)
      
      ws.current.onopen = () => {
        setConnectionStatus(ConnectionStatus.CONNECTED)
        reconnectAttemptsRef.current = 0
        startHeartbeat()
      }
      
      ws.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          setLastMessage(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
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
          setConnectionStatus(ConnectionStatus.RECONNECTING)
          
          const backoffDelay = reconnectInterval * Math.pow(1.5, reconnectAttemptsRef.current - 1)
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, Math.min(backoffDelay, 30000)) // Max 30 second backoff
        }
      }
      
      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error)
        setConnectionStatus(ConnectionStatus.ERROR)
      }
      
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      setConnectionStatus(ConnectionStatus.ERROR)
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
    disconnect
  }
}