/**
 * useDetailedHealth Hook
 * Manages detailed health data with WebSocket and polling fallback
 */

'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useWebSocket } from './useWebSocket'
import { DetailedHealthData } from '@/types/health'
import { ConnectionStatus, MessageType } from '@/types/websocket'

interface UseDetailedHealthOptions {
  enableWebSocket?: boolean
  pollingInterval?: number
  orchestratorUrl?: string
}

interface UseDetailedHealthReturn {
  healthData: DetailedHealthData | null
  loading: boolean
  error: string | null
  lastUpdate: Date | null
  refreshData: () => Promise<void>
  connectionStatus: ConnectionStatus
  latencyHistory: Map<string, number[]>
}

const DEFAULT_ORCHESTRATOR_URL = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8089'
const MAX_LATENCY_HISTORY = 20

/**
 * Custom hook for managing detailed health data
 */
export function useDetailedHealth({
  enableWebSocket = true,
  pollingInterval = 5000,
  orchestratorUrl = DEFAULT_ORCHESTRATOR_URL
}: UseDetailedHealthOptions = {}): UseDetailedHealthReturn {
  const [healthData, setHealthData] = useState<DetailedHealthData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const [latencyHistory, setLatencyHistory] = useState<Map<string, number[]>>(new Map())

  const pollingIntervalRef = useRef<NodeJS.Timeout>()
  const isMountedRef = useRef(true)

  // WebSocket connection
  const {
    connectionStatus,
    lastMessage,
    isConnected,
    connect,
    disconnect
  } = useWebSocket({
    url: `${orchestratorUrl.replace('http', 'ws')}/ws`,
    reconnectAttempts: 5,
    reconnectInterval: 3000,
    enableHeartbeat: true,
    onError: (error) => {
      console.error('WebSocket error in useDetailedHealth:', error)
    },
    onReconnectFailed: () => {
      console.warn('WebSocket reconnection failed, falling back to polling')
    }
  })

  /**
   * Fetch detailed health data from REST API
   */
  const fetchHealthData = useCallback(async () => {
    try {
      const response = await fetch(`${orchestratorUrl}/health/detailed`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch health data: ${response.statusText}`)
      }

      const data: DetailedHealthData = await response.json()

      if (isMountedRef.current) {
        setHealthData(data)
        setLastUpdate(new Date(data.timestamp))
        setError(null)
        setLoading(false)

        // Update latency history
        updateLatencyHistory(data)
      }
    } catch (err) {
      console.error('Error fetching detailed health data:', err)
      if (isMountedRef.current) {
        setError(err instanceof Error ? err.message : 'Unknown error')
        setLoading(false)
      }
    }
  }, [orchestratorUrl])

  /**
   * Update latency history with new data points
   */
  const updateLatencyHistory = useCallback((data: DetailedHealthData) => {
    setLatencyHistory((prev) => {
      const updated = new Map(prev)

      // Update agent latencies
      data.agents.forEach((agent) => {
        if (agent.latency_ms !== null) {
          const key = `agent-${agent.port}`
          const history = updated.get(key) || []
          const newHistory = [...history, agent.latency_ms].slice(-MAX_LATENCY_HISTORY)
          updated.set(key, newHistory)
        }
      })

      // Update service latencies
      const allServices = [...data.services, ...data.external_services]
      allServices.forEach((service) => {
        if (service.latency_ms !== null) {
          const key = service.port ? `service-${service.port}` : `service-${service.name}`
          const history = updated.get(key) || []
          const newHistory = [...history, service.latency_ms].slice(-MAX_LATENCY_HISTORY)
          updated.set(key, newHistory)
        }
      })

      return updated
    })
  }, [])

  /**
   * Handle WebSocket messages
   */
  useEffect(() => {
    if (!lastMessage) return

    try {
      // Check if message is health update
      if (lastMessage.type === MessageType.HEALTH_UPDATE || lastMessage.type === 'health.detailed') {
        const data = lastMessage.data as DetailedHealthData

        if (data && isMountedRef.current) {
          setHealthData(data)
          setLastUpdate(new Date(data.timestamp))
          setError(null)
          setLoading(false)
          updateLatencyHistory(data)
        }
      }
    } catch (err) {
      console.error('Error processing WebSocket message:', err)
    }
  }, [lastMessage, updateLatencyHistory])

  /**
   * Start polling fallback
   */
  const startPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current)
    }

    // Initial fetch
    fetchHealthData()

    // Set up polling
    pollingIntervalRef.current = setInterval(() => {
      fetchHealthData()
    }, pollingInterval)
  }, [fetchHealthData, pollingInterval])

  /**
   * Stop polling
   */
  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current)
      pollingIntervalRef.current = undefined
    }
  }, [])

  /**
   * Manual refresh
   */
  const refreshData = useCallback(async () => {
    setLoading(true)
    await fetchHealthData()
  }, [fetchHealthData])

  /**
   * Initialize connection based on settings
   */
  useEffect(() => {
    if (enableWebSocket) {
      connect()
    } else {
      startPolling()
    }

    return () => {
      disconnect()
      stopPolling()
    }
  }, [enableWebSocket, connect, disconnect, startPolling, stopPolling])

  /**
   * Use polling as fallback when WebSocket is not connected
   */
  useEffect(() => {
    if (enableWebSocket && !isConnected && connectionStatus !== ConnectionStatus.CONNECTING) {
      // WebSocket failed, start polling fallback
      console.log('WebSocket not connected, using polling fallback')
      startPolling()
    } else if (enableWebSocket && isConnected) {
      // WebSocket connected, stop polling
      stopPolling()

      // Fetch initial data via REST
      fetchHealthData()
    }
  }, [enableWebSocket, isConnected, connectionStatus, startPolling, stopPolling, fetchHealthData])

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      isMountedRef.current = false
      stopPolling()
    }
  }, [stopPolling])

  return {
    healthData,
    loading,
    error,
    lastUpdate,
    refreshData,
    connectionStatus,
    latencyHistory
  }
}
