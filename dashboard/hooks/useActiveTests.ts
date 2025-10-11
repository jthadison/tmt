/**
 * Custom hook for active shadow tests monitoring
 */

'use client'

import { useState, useEffect, useCallback } from 'react'

interface ActiveTest {
  testId: string
  parameter: string
  session: string
  startDate: string
  currentMetrics: Record<string, any>
}

interface UseActiveTestsReturn {
  data: ActiveTest[]
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

/**
 * Hook for fetching active shadow tests
 */
export function useActiveTests(): UseActiveTestsReturn {
  const [data, setData] = useState<ActiveTest[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch('http://localhost:8007/api/v1/improvement/active-tests')

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      setData(result)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch active tests'
      setError(message)
      console.error('Error fetching active tests:', err)
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
