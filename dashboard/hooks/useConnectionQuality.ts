/**
 * useConnectionQuality Hook
 * Calculates and monitors connection quality based on WebSocket status,
 * latency, and data freshness
 */

'use client'

import { useState, useEffect, useMemo } from 'react'
import { useHealthData } from '@/context/HealthDataContext'
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

  // Use shared health data from context instead of creating new instance
  const { healthData, lastUpdate, connectionStatus } = useHealthData()

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

      // Debug logging
      console.log('[ConnectionQuality] Calculating:', {
        hasHealthData: !!healthData,
        lastUpdate: lastUpdate?.toISOString(),
        dataAge,
        avgLatency,
        wsStatus
      })

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
  }, [updateInterval, healthData, lastUpdate, wsStatus])

  return {
    quality,
    metrics,
    lastUpdate
  }
}
