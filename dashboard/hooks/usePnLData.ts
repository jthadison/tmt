/**
 * Custom hook for P&L data management
 * Provides real-time P&L calculations, history tracking, and WebSocket updates
 */

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { useOandaData } from './useOandaData'
import { LivePnLState, PnLUpdateMessage } from '@/types/performance'
import { debounce } from '@/utils/debounce'

/**
 * Hook for managing P&L data with real-time updates
 */
export function usePnLData(): LivePnLState & {
  updatePnL: (update: PnLUpdateMessage) => void
} {
  const { accounts, accountMetrics, isLoading, error } = useOandaData()
  const [pnlHistory, setPnlHistory] = useState<number[]>([])
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const prevPnL = useRef<number>(0)

  /**
   * Calculate total daily P&L from all accounts
   */
  const dailyPnL = useMemo(() => {
    const total = accounts.reduce((sum, account) => {
      const realized = account.realizedPL || 0
      const unrealized = account.unrealizedPL || 0
      return sum + realized + unrealized
    }, 0)

    return total
  }, [accounts])

  /**
   * Calculate realized P&L
   */
  const realizedPnL = useMemo(() => {
    return accounts.reduce((sum, acc) => sum + (acc.realizedPL || 0), 0)
  }, [accounts])

  /**
   * Calculate unrealized P&L
   */
  const unrealizedPnL = useMemo(() => {
    return accounts.reduce((sum, acc) => sum + (acc.unrealizedPL || 0), 0)
  }, [accounts])

  /**
   * Calculate P&L percentage based on total balance
   */
  const pnLPercentage = useMemo(() => {
    const totalBalance = accounts.reduce((sum, acc) => sum + acc.balance, 0)
    return totalBalance > 0 ? (dailyPnL / totalBalance) * 100 : 0
  }, [dailyPnL, accounts])

  /**
   * Update P&L history for sparkline (rolling 20 points)
   * Only update if P&L changed significantly (>$0.01)
   */
  useEffect(() => {
    const shouldUpdate = Math.abs(dailyPnL - prevPnL.current) > 0.01

    if (shouldUpdate) {
      setPnlHistory(prev => {
        const newHistory = [...prev, dailyPnL]
        return newHistory.slice(-20) // Keep last 20 points
      })
      prevPnL.current = dailyPnL
      setLastUpdate(new Date())
    }
  }, [dailyPnL])

  /**
   * Debounced P&L update handler for WebSocket messages
   * Prevents excessive re-renders (max 10 updates/sec)
   */
  const debouncedUpdate = useMemo(
    () =>
      debounce((update: PnLUpdateMessage) => {
        // This will trigger the dailyPnL recalculation
        setLastUpdate(update.timestamp)
      }, 100), // 100ms debounce
    []
  )

  /**
   * Public method to update P&L from external sources (WebSocket)
   */
  const updatePnL = useCallback(
    (update: PnLUpdateMessage) => {
      debouncedUpdate(update)
    },
    [debouncedUpdate]
  )

  return {
    dailyPnL,
    pnLPercentage,
    pnLHistory: pnlHistory,
    realizedPnL,
    unrealizedPnL,
    isLoading,
    error: error || null,
    lastUpdate,
    updatePnL,
  }
}
