/**
 * Custom hook for CI pipeline status monitoring
 */

'use client'

import { useState, useEffect, useCallback } from 'react'

interface CIPipelineStatus {
  pipelineState: string
  lastCycleTime: string | null
  nextCycleTime: string | null
  cycleCount: number
  suggestionsGenerated: number
  testsRunning: number
  deploymentsActive: number
}

interface UseCIPipelineStatusReturn {
  data: CIPipelineStatus | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

/**
 * Hook for fetching CI pipeline status
 */
export function useCIPipelineStatus(): UseCIPipelineStatusReturn {
  const [data, setData] = useState<CIPipelineStatus | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch('http://localhost:8007/api/v1/improvement/pipeline/status')

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      setData(result)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch CI pipeline status'
      setError(message)
      console.error('Error fetching CI pipeline status:', err)
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
