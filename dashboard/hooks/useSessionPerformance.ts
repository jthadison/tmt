'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { TradingSession, SessionPerformance, DateRange, SESSION_CONFIG, TradeCompletedMessage } from '@/types/session'
import { useWebSocket } from './useWebSocket'

interface UseSessionPerformanceOptions {
  dateRange: DateRange
  orchestratorUrl?: string
  enableRealtime?: boolean
}

interface UseSessionPerformanceReturn {
  sessions: SessionPerformance[]
  activeSession: TradingSession | null
  isLoading: boolean
  error: string | null
  refetch: () => Promise<void>
}

/**
 * Hook for fetching and managing session performance data
 * @param options - Configuration options including date range
 * @returns Session performance state and methods
 */
export function useSessionPerformance({
  dateRange,
  orchestratorUrl = 'http://localhost:8089',
  enableRealtime = true
}: UseSessionPerformanceOptions): UseSessionPerformanceReturn {
  const [sessions, setSessions] = useState<SessionPerformance[]>([])
  const [activeSession, setActiveSession] = useState<TradingSession | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // WebSocket for real-time updates
  const { lastMessage } = useWebSocket({
    url: orchestratorUrl.replace('http', 'ws'),
    reconnectAttempts: 5
  })

  // Throttle ref for WebSocket updates (5-second interval)
  const lastUpdateRef = useRef<number>(0)
  const throttleDelay = 5000

  /**
   * Determine current active session based on GMT time
   */
  const determineActiveSession = useCallback((): TradingSession | null => {
    const now = new Date()
    const gmtHour = now.getUTCHours()

    for (const [sessionKey, config] of Object.entries(SESSION_CONFIG)) {
      const { startHour, endHour } = config

      // Handle sessions that cross midnight (e.g., Sydney 18:00-03:00)
      const isActive = startHour <= endHour
        ? gmtHour >= startHour && gmtHour < endHour
        : gmtHour >= startHour || gmtHour < endHour

      if (isActive) {
        return sessionKey as TradingSession
      }
    }

    return null
  }, [])

  /**
   * Fetch session performance data from orchestrator
   */
  const fetchSessionData = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)

      const params = new URLSearchParams({
        start_date: dateRange.start.toISOString(),
        end_date: dateRange.end.toISOString()
      })

      const response = await fetch(`${orchestratorUrl}/api/performance/sessions?${params}`)

      if (!response.ok) {
        throw new Error(`Failed to fetch session data: ${response.statusText}`)
      }

      const data = await response.json()

      // Determine active session
      const currentActiveSession = determineActiveSession()

      // Map API response to SessionPerformance with active flag
      const sessionData: SessionPerformance[] = data.sessions.map((s: any) => ({
        session: s.session as TradingSession,
        totalPnL: s.total_pnl || s.totalPnL || 0,
        tradeCount: s.trade_count || s.tradeCount || 0,
        winCount: s.win_count || s.winCount || 0,
        winRate: s.win_rate || s.winRate || 0,
        confidenceThreshold: s.confidence_threshold || s.confidenceThreshold || SESSION_CONFIG[s.session as TradingSession].confidenceThreshold,
        isActive: s.session === currentActiveSession
      }))

      setSessions(sessionData)
      setActiveSession(currentActiveSession)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      console.error('Error fetching session data:', err)
    } finally {
      setIsLoading(false)
    }
  }, [dateRange, orchestratorUrl, determineActiveSession])

  /**
   * Handle real-time WebSocket updates (throttled)
   */
  useEffect(() => {
    if (!enableRealtime || !lastMessage) return

    const now = Date.now()

    // Throttle updates to 5-second intervals
    if (now - lastUpdateRef.current < throttleDelay) {
      return
    }

    // Check if message is trade completion
    if (lastMessage.type === 'trade.completed') {
      const tradeData = lastMessage as unknown as TradeCompletedMessage
      const { session, pnL } = tradeData.data

      lastUpdateRef.current = now

      setSessions(prev => prev.map(s =>
        s.session === session
          ? {
              ...s,
              totalPnL: s.totalPnL + pnL,
              tradeCount: s.tradeCount + 1,
              winCount: pnL > 0 ? s.winCount + 1 : s.winCount,
              winRate: pnL > 0
                ? ((s.winCount + 1) / (s.tradeCount + 1)) * 100
                : (s.winCount / (s.tradeCount + 1)) * 100
            }
          : s
      ))
    }
  }, [lastMessage, enableRealtime])

  /**
   * Update active session every minute
   */
  useEffect(() => {
    const interval = setInterval(() => {
      const currentActiveSession = determineActiveSession()

      if (currentActiveSession !== activeSession) {
        setActiveSession(currentActiveSession)

        // Update isActive flag for all sessions
        setSessions(prev => prev.map(s => ({
          ...s,
          isActive: s.session === currentActiveSession
        })))
      }
    }, 60000) // Check every minute

    return () => clearInterval(interval)
  }, [activeSession, determineActiveSession])

  /**
   * Initial fetch and refetch on date range change
   */
  useEffect(() => {
    fetchSessionData()
  }, [fetchSessionData])

  return {
    sessions,
    activeSession,
    isLoading,
    error,
    refetch: fetchSessionData
  }
}
