'use client'

import { useState, useEffect, useCallback } from 'react'
import { EquityCurveData, EquityPoint, EquityCurveResponse } from '@/types/metrics'

interface UseEquityCurveOptions {
  days?: number
  orchestratorUrl?: string
}

interface UseEquityCurveReturn {
  equityCurve: EquityCurveData | null
  isLoading: boolean
  error: string | null
  refetch: () => Promise<void>
}

/**
 * Hook for fetching equity curve data
 * @param options - Configuration options including number of days
 * @returns Equity curve state and methods
 */
export function useEquityCurve({
  days = 30,
  orchestratorUrl = 'http://localhost:8089'
}: UseEquityCurveOptions = {}): UseEquityCurveReturn {
  const [equityCurve, setEquityCurve] = useState<EquityCurveData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  /**
   * Calculate peak and trough from equity points
   */
  const calculateMilestones = useCallback((points: EquityPoint[]): EquityCurveData => {
    if (points.length === 0) {
      return {
        points: [],
        peak: null,
        trough: null,
        currentDrawdown: 0,
        maxDrawdown: 0
      }
    }

    // Find peak (highest equity point)
    const peak = points.reduce((max, point) =>
      point.equity > max.equity ? point : max,
      points[0]
    )

    // Find trough (lowest equity point after peak)
    const peakIndex = points.findIndex(p => p.date === peak.date)
    const pointsAfterPeak = points.slice(peakIndex)

    const trough = pointsAfterPeak.length > 1
      ? pointsAfterPeak.reduce((min, point) =>
          point.equity < min.equity ? point : min,
          pointsAfterPeak[1]
        )
      : null

    // Calculate current drawdown
    const currentEquity = points[points.length - 1].equity
    const currentDrawdown = peak.equity > 0
      ? ((currentEquity - peak.equity) / peak.equity) * 100
      : 0

    // Calculate maximum drawdown
    let maxDrawdown = 0
    let runningPeak = points[0].equity

    for (const point of points) {
      if (point.equity > runningPeak) {
        runningPeak = point.equity
      }

      const drawdown = runningPeak > 0
        ? ((point.equity - runningPeak) / runningPeak) * 100
        : 0

      if (drawdown < maxDrawdown) {
        maxDrawdown = drawdown
      }
    }

    return {
      points,
      peak,
      trough,
      currentDrawdown,
      maxDrawdown
    }
  }, [])

  /**
   * Fetch equity curve data from orchestrator
   */
  const fetchEquityCurve = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)

      const response = await fetch(`${orchestratorUrl}/api/performance/equity-curve?days=${days}`)

      if (!response.ok) {
        throw new Error(`Failed to fetch equity curve: ${response.statusText}`)
      }

      const result: EquityCurveResponse = await response.json()

      // Map API response to EquityPoint array
      const points: EquityPoint[] = result.data.map(point => ({
        date: point.date,
        equity: point.equity,
        dailyPnL: point.daily_pnl || point.dailyPnL || 0,
        drawdown: point.drawdown
      }))

      // Calculate milestones and drawdowns
      const curveData = calculateMilestones(points)
      setEquityCurve(curveData)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      console.error('Error fetching equity curve:', err)
    } finally {
      setIsLoading(false)
    }
  }, [days, orchestratorUrl, calculateMilestones])

  /**
   * Initial fetch on mount and when days changes
   */
  useEffect(() => {
    fetchEquityCurve()
  }, [fetchEquityCurve])

  return {
    equityCurve,
    isLoading,
    error,
    refetch: fetchEquityCurve
  }
}
