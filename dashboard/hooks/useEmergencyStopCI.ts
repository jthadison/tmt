/**
 * Custom hook for CI pipeline emergency stop
 */

'use client'

import { useState, useCallback } from 'react'

interface UseEmergencyStopReturn {
  triggerEmergencyStop: (reason: string, authorizedBy: string) => Promise<boolean>
  loading: boolean
  error: string | null
}

/**
 * Hook for triggering CI pipeline emergency stop
 */
export function useEmergencyStopCI(): UseEmergencyStopReturn {
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  const triggerEmergencyStop = useCallback(async (reason: string, authorizedBy: string): Promise<boolean> => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch('http://localhost:8007/api/v1/improvement/pipeline/emergency-stop', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ reason, authorized_by: authorizedBy }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()

      if (!result.success) {
        throw new Error('Emergency stop failed')
      }

      console.log('Emergency stop successful:', result)
      return true
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to trigger emergency stop'
      setError(message)
      console.error('Error triggering emergency stop:', err)
      return false
    } finally {
      setLoading(false)
    }
  }, [])

  return { triggerEmergencyStop, loading, error }
}
