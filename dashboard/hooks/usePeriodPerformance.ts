/**
 * Custom hook for period performance data
 * Fetches historical P&L, trade statistics, and best/worst trades
 */

import { useState, useEffect, useCallback } from 'react'
import { PeriodType, PeriodPerformance, BestWorstTrades } from '@/types/performance'

/**
 * Hook for fetching period-specific performance data
 */
export function usePeriodPerformance(period: PeriodType) {
  const [periodData, setPeriodData] = useState<PeriodPerformance | null>(null)
  const [bestWorstTrades, setBestWorstTrades] = useState<BestWorstTrades>({
    bestTrade: null,
    worstTrade: null,
  })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  /**
   * Fetch period performance data from API with retry logic
   */
  const fetchPeriodData = useCallback(async (retryCount = 0) => {
    setIsLoading(true)
    setError(null)

    try {
      // Fetch period performance metrics
      const periodResponse = await fetch(
        `/api/performance/pnl/period?period=${period}`,
        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      )

      if (!periodResponse.ok) {
        const errorData = await periodResponse.json().catch(() => ({}))
        throw new Error(
          errorData.detail || `Failed to fetch period data: ${periodResponse.status}`
        )
      }

      const periodResult = await periodResponse.json()

      // Fetch best/worst trades for period
      const tradesResponse = await fetch(
        `/api/performance/trades/best-worst?period=${period}`,
        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      )

      if (!tradesResponse.ok) {
        const errorData = await tradesResponse.json().catch(() => ({}))
        throw new Error(
          errorData.detail || `Failed to fetch trades data: ${tradesResponse.status}`
        )
      }

      const tradesResult = await tradesResponse.json()

      setPeriodData({
        period: periodResult.period,
        totalPnL: periodResult.total_pnl || 0,
        pnLPercentage: periodResult.pnl_percentage || 0,
        tradeCount: periodResult.trade_count || 0,
        winRate: periodResult.win_rate || 0,
        avgPnL: periodResult.avg_pnl || 0,
        startDate: new Date(periodResult.start_date),
        endDate: new Date(periodResult.end_date),
      })

      setBestWorstTrades({
        bestTrade: tradesResult.best_trade
          ? {
              ...tradesResult.best_trade,
              entryTime: new Date(tradesResult.best_trade.entry_time),
              exitTime: new Date(tradesResult.best_trade.exit_time),
            }
          : null,
        worstTrade: tradesResult.worst_trade
          ? {
              ...tradesResult.worst_trade,
              entryTime: new Date(tradesResult.worst_trade.entry_time),
              exitTime: new Date(tradesResult.worst_trade.exit_time),
            }
          : null,
      })
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'

      // Retry logic: retry up to 2 times with exponential backoff
      if (retryCount < 2) {
        const delay = Math.pow(2, retryCount) * 1000 // 1s, 2s
        console.warn(`Retrying period performance fetch (attempt ${retryCount + 1}/2) in ${delay}ms...`)
        setTimeout(() => fetchPeriodData(retryCount + 1), delay)
        return
      }

      setError(errorMessage)
      console.error('Error fetching period performance:', err)
    } finally {
      setIsLoading(false)
    }
  }, [period])

  // Fetch data when period changes
  useEffect(() => {
    fetchPeriodData()
  }, [fetchPeriodData])

  return {
    periodData,
    bestTrade: bestWorstTrades.bestTrade,
    worstTrade: bestWorstTrades.worstTrade,
    isLoading,
    error,
    refetch: fetchPeriodData,
  }
}
