/**
 * Custom hook for pending suggestions monitoring
 */

'use client'

import { useState, useEffect, useCallback } from 'react'

interface PendingSuggestion {
  suggestionId: string
  title: string
  description: string
  expectedImprovement: number
  riskLevel: string
  status: string
  createdAt: string
}

interface UsePendingSuggestionsReturn {
  data: PendingSuggestion[]
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

/**
 * Hook for fetching pending parameter suggestions
 */
export function usePendingSuggestions(): UsePendingSuggestionsReturn {
  const [data, setData] = useState<PendingSuggestion[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch('http://localhost:8007/api/v1/improvement/pending-suggestions')

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      setData(result)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch pending suggestions'
      setError(message)
      console.error('Error fetching pending suggestions:', err)
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
