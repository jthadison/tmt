/**
 * Custom hook for learning agent status monitoring
 */

'use client'

import { useState, useEffect, useCallback } from 'react'

interface LearningCycleStatus {
  cycleState: string
  lastRun: string | null
  nextRun: string | null
  suggestionsCount: number
  activeTestsCount: number
}

interface UseLearningStatusReturn {
  data: LearningCycleStatus | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

/**
 * Hook for fetching learning agent status
 */
export function useLearningStatus(): UseLearningStatusReturn {
  const [data, setData] = useState<LearningCycleStatus | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch('http://localhost:8004/api/v1/learning/status')

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      setData(result)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch learning status'
      setError(message)
      console.error('Error fetching learning status:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()

    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchData, 30000)

    return () => clearInterval(interval)
  }, [fetchData])

  return { data, loading, error, refetch: fetchData }
}
