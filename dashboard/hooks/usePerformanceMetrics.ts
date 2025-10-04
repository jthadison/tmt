'use client'

import { useState, useEffect, useCallback } from 'react'
import { PerformanceMetrics, MetricsPeriod, PerformanceMetricsResponse } from '@/types/metrics'

interface UsePerformanceMetricsOptions {
  period?: MetricsPeriod
  orchestratorUrl?: string
}

interface UsePerformanceMetricsReturn {
  metrics: PerformanceMetrics | null
  previousMetrics: PerformanceMetrics | null
  isLoading: boolean
  error: string | null
  refetch: () => Promise<void>
}

/**
 * Hook for fetching performance metrics (win rate, profit factor, etc.)
 * @param options - Configuration options including time period
 * @returns Performance metrics state and methods
 */
export function usePerformanceMetrics({
  period = '30d',
  orchestratorUrl = 'http://localhost:8089'
}: UsePerformanceMetricsOptions = {}): UsePerformanceMetricsReturn {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null)
  const [previousMetrics, setPreviousMetrics] = useState<PerformanceMetrics | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  /**
   * Fetch performance metrics from orchestrator
   */
  const fetchMetrics = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)

      const response = await fetch(`${orchestratorUrl}/api/performance/metrics?period=${period}`)

      if (!response.ok) {
        throw new Error(`Failed to fetch metrics: ${response.statusText}`)
      }

      const data: PerformanceMetricsResponse = await response.json()

      // Map API response to PerformanceMetrics
      const currentMetrics: PerformanceMetrics = {
        winRate: data.current.win_rate || data.current.winRate || 0,
        profitFactor: data.current.profit_factor || data.current.profitFactor || 0,
        avgWin: data.current.avg_win || data.current.avgWin || 0,
        avgLoss: Math.abs(data.current.avg_loss || data.current.avgLoss || 0),
        avgRiskReward: data.current.avg_risk_reward || data.current.avgRiskReward ||
                      (data.current.avg_win && data.current.avg_loss
                        ? Math.abs(data.current.avg_win / data.current.avg_loss)
                        : 0),
        avgDurationHours: data.current.avg_duration_hours || data.current.avgDurationHours || 0
      }

      setMetrics(currentMetrics)

      // Set previous metrics if available (for comparison)
      if (data.previous) {
        const prevMetrics: PerformanceMetrics = {
          winRate: data.previous.win_rate || data.previous.winRate || 0,
          profitFactor: data.previous.profit_factor || data.previous.profitFactor || 0,
          avgWin: data.previous.avg_win || data.previous.avgWin || 0,
          avgLoss: Math.abs(data.previous.avg_loss || data.previous.avgLoss || 0),
          avgRiskReward: data.previous.avg_risk_reward || data.previous.avgRiskReward ||
                        (data.previous.avg_win && data.previous.avg_loss
                          ? Math.abs(data.previous.avg_win / data.previous.avg_loss)
                          : 0),
          avgDurationHours: data.previous.avg_duration_hours || data.previous.avgDurationHours || 0
        }
        setPreviousMetrics(prevMetrics)
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      console.error('Error fetching performance metrics:', err)
    } finally {
      setIsLoading(false)
    }
  }, [period, orchestratorUrl])

  /**
   * Initial fetch on mount and when period changes
   */
  useEffect(() => {
    fetchMetrics()
  }, [fetchMetrics])

  return {
    metrics,
    previousMetrics,
    isLoading,
    error,
    refetch: fetchMetrics
  }
}
