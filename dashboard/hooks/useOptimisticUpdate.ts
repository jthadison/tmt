/**
 * Optimistic UI Update Hook with Rollback
 *
 * Lifecycle:
 * 1. User action triggers update
 * 2. UI immediately updates (optimistic)
 * 3. API call sent to server
 * 4. On success: Confirm update
 * 5. On error: Rollback to previous state
 *
 * Features:
 * - Immediate UI feedback
 * - Automatic rollback on error
 * - Retry capability
 * - Loading state management
 */

import { useState, useCallback } from 'react'

export interface OptimisticUpdateOptions<T> {
  onUpdate: (data: T) => Promise<void>
  onSuccess?: (data: T) => void
  onError?: (error: Error, previousState: T) => void
}

export interface UseOptimisticUpdateResult<T> {
  state: T
  update: (newState: T) => Promise<void>
  isUpdating: boolean
  error: Error | null
  rollback: () => void
  reset: () => void
}

export function useOptimisticUpdate<T>(
  initialState: T,
  options: OptimisticUpdateOptions<T>
): UseOptimisticUpdateResult<T> {
  const [state, setState] = useState<T>(initialState)
  const [previousState, setPreviousState] = useState<T>(initialState)
  const [isUpdating, setIsUpdating] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const update = useCallback(
    async (newState: T) => {
      // Save current state for rollback
      setPreviousState(state)

      // Optimistically update UI
      setState(newState)
      setIsUpdating(true)
      setError(null)

      try {
        // Send to server
        await options.onUpdate(newState)

        // Success - commit optimistic update
        options.onSuccess?.(newState)
      } catch (error) {
        const err = error as Error
        // Error - rollback to previous state
        setState(previousState)
        setError(err)
        options.onError?.(err, previousState)
      } finally {
        setIsUpdating(false)
      }
    },
    [state, previousState, options]
  )

  const rollback = useCallback(() => {
    setState(previousState)
    setError(null)
  }, [previousState])

  const reset = useCallback(() => {
    setState(initialState)
    setPreviousState(initialState)
    setError(null)
    setIsUpdating(false)
  }, [initialState])

  return {
    state,
    update,
    isUpdating,
    error,
    rollback,
    reset,
  }
}
