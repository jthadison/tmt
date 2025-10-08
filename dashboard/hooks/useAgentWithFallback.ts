/**
 * Agent with Fallback Hook
 *
 * Implements graceful degradation for agent failures:
 * - Displays last known data when agent is offline
 * - Automatic retry every 30 seconds (configurable)
 * - Status indicators for online/offline state
 * - Timestamp tracking for last successful update
 *
 * Features:
 * - Automatic background retries
 * - Fallback data support
 * - Last seen timestamp
 * - Online/offline status
 */

import { useEffect, useState, useCallback, useRef } from 'react'

export interface AgentStatus {
  online: boolean
  lastSeen: Date | null
  usingFallback: boolean
}

export interface UseAgentWithFallbackOptions {
  retryIntervalMs?: number
  timeout?: number
  enabled?: boolean
}

export interface UseAgentWithFallbackResult<T> {
  data: T | null
  status: AgentStatus
  refetch: () => Promise<void>
  isLoading: boolean
}

export function useAgentWithFallback<T>(
  agentUrl: string,
  fallbackData: T | null = null,
  options: UseAgentWithFallbackOptions = {}
): UseAgentWithFallbackResult<T> {
  const {
    retryIntervalMs = 30000,
    timeout = 5000,
    enabled = true,
  } = options

  const [data, setData] = useState<T | null>(fallbackData)
  const [isLoading, setIsLoading] = useState(true)
  const [status, setStatus] = useState<AgentStatus>({
    online: true,
    lastSeen: null,
    usingFallback: false,
  })

  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const fetchData = useCallback(async () => {
    if (!enabled) return

    // Cancel any pending request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }

    // Create new AbortController for this request
    abortControllerRef.current = new AbortController()

    try {
      setIsLoading(true)

      const response = await fetch(agentUrl, {
        signal: abortControllerRef.current.signal,
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const newData = await response.json()
      setData(newData)
      setStatus({
        online: true,
        lastSeen: new Date(),
        usingFallback: false,
      })
    } catch (error) {
      // Ignore abort errors
      if (error instanceof Error && error.name === 'AbortError') {
        return
      }

      console.error(`Agent ${agentUrl} offline:`, error)

      setStatus(prev => ({
        online: false,
        lastSeen: prev.lastSeen,
        usingFallback: fallbackData !== null,
      }))

      // Retry after interval
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current)
      }
      retryTimeoutRef.current = setTimeout(fetchData, retryIntervalMs)
    } finally {
      setIsLoading(false)
    }
  }, [agentUrl, enabled, fallbackData, retryIntervalMs])

  useEffect(() => {
    if (enabled) {
      fetchData()
    }

    return () => {
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current)
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [fetchData, enabled])

  return {
    data,
    status,
    refetch: fetchData,
    isLoading,
  }
}
