/**
 * useConnectionQuality Hook
 * Calculates and monitors connection quality based on WebSocket status,
 * latency, and data freshness
 */

'use client'

import { useState, useEffect, useMemo } from 'react'
import { useDetailedHealth } from './useDetailedHealth'
import { ConnectionQuality, ConnectionMetrics, ConnectionQualityData } from '@/types/health'
import { calculateConnectionQuality } from '@/utils/connectionQuality'
import { ConnectionStatus } from '@/types/websocket'

interface UseConnectionQualityOptions {
  updateInterval?: number // milliseconds, default 1000
}

/**
 * Custom hook for monitoring connection quality
 */
export function useConnectionQuality(
  options: UseConnectionQualityOptions = {}
): ConnectionQualityData {
  const { updateInterval = 1000 } = options

  const { healthData, lastUpdate, connectionStatus } = useDetailedHealth({
    enableWebSocket: false,
    pollingInterval: 5000
  })

  const [quality, setQuality] = useState<ConnectionQuality>('good')
  const [metrics, setMetrics] = useState<ConnectionMetrics>({
    wsStatus: 'connecting',
    avgLatency: 0,
    dataAge: 0
  })

  // Map ConnectionStatus to wsStatus
  const wsStatus = useMemo(() => {
    switch (connectionStatus) {
      case ConnectionStatus.CONNECTED:
        return 'connected' as const
      case ConnectionStatus.CONNECTING:
        return 'connecting' as const
      case ConnectionStatus.DISCONNECTED:
        return 'disconnected' as const
      case ConnectionStatus.ERROR:
      case ConnectionStatus.RECONNECTING:
        return 'error' as const
      default:
        return 'disconnected' as const
    }
  }, [connectionStatus])

  /**
   * Calculate connection quality every interval
   */
  useEffect(() => {
    const calculateAndUpdate = () => {
      // Calculate data age
      const dataAge = lastUpdate
        ? (Date.now() - lastUpdate.getTime()) / 1000
        : 999

      // Get average latency from health data
      const avgLatency = healthData?.system_metrics?.avg_latency_ms || 0

      // Build current metrics
      const currentMetrics: ConnectionMetrics = {
        wsStatus,
        avgLatency,
        dataAge
      }

      // Calculate quality
      const currentQuality = calculateConnectionQuality(currentMetrics)

      setMetrics(currentMetrics)
      setQuality(currentQuality)
    }

    // Calculate immediately
    calculateAndUpdate()

    // Then set up interval
    const interval = setInterval(calculateAndUpdate, updateInterval)

    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [updateInterval])

  return {
    quality,
    metrics,
    lastUpdate
  }
}
