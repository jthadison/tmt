/**
 * Custom hook for system health monitoring with WebSocket and polling fallback
 */

'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { SystemHealthStatus, HealthStatus } from '@/types/health'
import { getHealthCheckService, SystemHealth } from '@/services/healthCheck'
import { useWebSocket } from './useWebSocket'
import { MessageType, ConnectionStatus } from '@/types/websocket'
import { intervalConfig } from '@/config/intervals'

interface UseSystemHealthOptions {
  enableWebSocket?: boolean
  pollingInterval?: number
  fallbackDelay?: number
}

interface UseSystemHealthReturn {
  healthStatus: SystemHealthStatus | null
  isLoading: boolean
  error: string | null
  connectionStatus: ConnectionStatus
  refresh: () => Promise<void>
}

/**
 * Convert service health status to our health status enum
 */
function mapServiceStatus(status: string): HealthStatus {
  switch (status) {
    case 'healthy':
      return 'healthy'
    case 'degraded':
      return 'degraded'
    case 'unhealthy':
    case 'unknown':
      return 'critical'
    default:
      return 'critical'
  }
}

/**
 * Transform SystemHealth to SystemHealthStatus
 */
function transformSystemHealth(
  systemHealth: SystemHealth,
  oandaConnected: boolean
): SystemHealthStatus {
  const agents = systemHealth.services.map(service => ({
    name: service.name,
    status: mapServiceStatus(service.status),
    latency: service.latency,
    lastChecked: service.lastChecked,
    message: service.message
  }))

  const healthyAgents = agents.filter(a => a.status === 'healthy').length
  const totalLatency = agents.reduce((sum, a) => sum + (a.latency || 0), 0)
  const averageLatency = agents.length > 0 ? Math.round(totalLatency / agents.length) : 0

  return {
    overall: mapServiceStatus(systemHealth.overall),
    agents,
    totalAgents: agents.length,
    healthyAgents,
    averageLatency,
    oandaConnected,
    lastUpdate: systemHealth.timestamp,
    uptime: systemHealth.uptime
  }
}

/**
 * Hook for monitoring system health with WebSocket + polling fallback
 */
export function useSystemHealth({
  enableWebSocket = true,
  pollingInterval = 5000,
  fallbackDelay = 10000
}: UseSystemHealthOptions = {}): UseSystemHealthReturn {
  const [healthStatus, setHealthStatus] = useState<SystemHealthStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [oandaConnected, setOandaConnected] = useState(false)
  const [usePolling, setUsePolling] = useState(!enableWebSocket)

  const healthService = useRef(getHealthCheckService())
  const pollingIntervalRef = useRef<NodeJS.Timeout>()
  const fallbackTimerRef = useRef<NodeJS.Timeout>()

  // WebSocket connection for real-time updates
  const {
    connectionStatus,
    lastMessage,
    isConnected
  } = useWebSocket({
    url: typeof window !== 'undefined'
      ? `ws://${window.location.hostname}:8089/ws/health`
      : 'ws://localhost:8089/ws/health',
    enableHeartbeat: true,
    reconnectAttempts: 5,
    reconnectInterval: intervalConfig.websocketReconnect,
    onError: (error) => {
      console.error('System health WebSocket error:', error)
    },
    onReconnectFailed: () => {
      console.warn('WebSocket reconnection failed, switching to polling')
      setUsePolling(true)
    }
  })

  /**
   * Fetch health data via HTTP polling
   */
  const fetchHealthData = useCallback(async () => {
    try {
      const systemHealth = await healthService.current.checkNow()

      // For now, assume OANDA is connected if orchestrator is healthy
      const orchestratorService = systemHealth.services.find(s => s.name === 'Orchestrator')
      const oandaStatus = orchestratorService?.status === 'healthy'

      const transformed = transformSystemHealth(systemHealth, oandaStatus)
      setHealthStatus(transformed)
      setOandaConnected(oandaStatus)
      setError(null)
      setIsLoading(false)
    } catch (err) {
      console.error('Error fetching health data:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch health data')
      setIsLoading(false)
    }
  }, [])

  /**
   * Manual refresh
   */
  const refresh = useCallback(async () => {
    setIsLoading(true)
    await fetchHealthData()
  }, [fetchHealthData])

  /**
   * Handle WebSocket messages
   */
  useEffect(() => {
    if (lastMessage && lastMessage.type === MessageType.SYSTEM_STATUS) {
      try {
        const systemHealth: SystemHealth = lastMessage.data
        const orchestratorService = systemHealth.services.find(s => s.name === 'Orchestrator')
        const oandaStatus = orchestratorService?.status === 'healthy'

        const transformed = transformSystemHealth(systemHealth, oandaStatus)
        setHealthStatus(transformed)
        setOandaConnected(oandaStatus)
        setError(null)
        setIsLoading(false)
      } catch (err) {
        console.error('Error processing health message:', err)
      }
    }
  }, [lastMessage])

  /**
   * Monitor WebSocket connection and trigger fallback
   */
  useEffect(() => {
    if (!enableWebSocket) return

    // Clear existing fallback timer
    if (fallbackTimerRef.current) {
      clearTimeout(fallbackTimerRef.current)
    }

    // If disconnected or error, start fallback timer
    if (connectionStatus === ConnectionStatus.ERROR ||
        connectionStatus === ConnectionStatus.DISCONNECTED) {

      fallbackTimerRef.current = setTimeout(() => {
        console.warn('WebSocket disconnected for too long, switching to polling')
        setUsePolling(true)
      }, fallbackDelay)
    } else if (connectionStatus === ConnectionStatus.CONNECTED) {
      // Connected successfully, disable polling
      setUsePolling(false)
    }

    return () => {
      if (fallbackTimerRef.current) {
        clearTimeout(fallbackTimerRef.current)
      }
    }
  }, [connectionStatus, enableWebSocket, fallbackDelay])

  /**
   * Setup polling when enabled
   */
  useEffect(() => {
    if (usePolling) {
      // Initial fetch
      fetchHealthData()

      // Start polling
      pollingIntervalRef.current = setInterval(fetchHealthData, pollingInterval)

      return () => {
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current)
        }
      }
    }
  }, [usePolling, fetchHealthData, pollingInterval])

  /**
   * Initialize health service
   */
  useEffect(() => {
    healthService.current.start()

    return () => {
      healthService.current.stop()
    }
  }, [])

  return {
    healthStatus,
    isLoading,
    error,
    connectionStatus,
    refresh
  }
}
