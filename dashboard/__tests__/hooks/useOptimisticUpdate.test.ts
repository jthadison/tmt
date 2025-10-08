/**
 * Unit Tests for useOptimisticUpdate Hook
 *
 * Tests:
 * - Optimistic UI update
 * - Rollback on error
 * - Success confirmation
 * - Callback invocations
 * - Reset functionality
 */

import { renderHook, act, waitFor } from '@testing-library/react'
import { useOptimisticUpdate } from '@/hooks/useOptimisticUpdate'

describe('useOptimisticUpdate', () => {
  it('should update state optimistically', async () => {
    const onUpdate = jest.fn().mockResolvedValue(undefined)

    const { result } = renderHook(() =>
      useOptimisticUpdate({ value: 10 }, { onUpdate })
    )

    expect(result.current.state.value).toBe(10)

    act(() => {
      result.current.update({ value: 20 })
    })

    // Should update immediately (optimistic)
    expect(result.current.state.value).toBe(20)
    expect(result.current.isUpdating).toBe(true)

    await waitFor(() => {
      expect(result.current.isUpdating).toBe(false)
    })

    expect(onUpdate).toHaveBeenCalledWith({ value: 20 })
  })

  it('should rollback on error', async () => {
    const onUpdate = jest.fn().mockRejectedValue(new Error('Update failed'))

    const { result } = renderHook(() =>
      useOptimisticUpdate({ value: 10 }, { onUpdate })
    )

    act(() => {
      result.current.update({ value: 20 })
    })

    // Should update optimistically
    expect(result.current.state.value).toBe(20)

    // Wait for server response (fails)
    await waitFor(() => {
      expect(result.current.error).toBeTruthy()
    })

    // Should rollback to original value
    expect(result.current.state.value).toBe(10)
    expect(result.current.error?.message).toBe('Update failed')
  })

  it('should call onSuccess callback on successful update', async () => {
    const onUpdate = jest.fn().mockResolvedValue(undefined)
    const onSuccess = jest.fn()

    const { result } = renderHook(() =>
      useOptimisticUpdate({ value: 10 }, { onUpdate, onSuccess })
    )

    act(() => {
      result.current.update({ value: 20 })
    })

    await waitFor(() => {
      expect(result.current.isUpdating).toBe(false)
    })

    expect(onSuccess).toHaveBeenCalledWith({ value: 20 })
    expect(result.current.state.value).toBe(20)
    expect(result.current.error).toBeNull()
  })

  it('should call onError callback on failed update', async () => {
    const error = new Error('Update failed')
    const onUpdate = jest.fn().mockRejectedValue(error)
    const onError = jest.fn()

    const { result } = renderHook(() =>
      useOptimisticUpdate({ value: 10 }, { onUpdate, onError })
    )

    act(() => {
      result.current.update({ value: 20 })
    })

    await waitFor(() => {
      expect(result.current.error).toBeTruthy()
    })

    expect(onError).toHaveBeenCalledWith(error, { value: 10 })
    expect(result.current.state.value).toBe(10)
  })

  it('should handle multiple rapid updates correctly', async () => {
    let updateCount = 0
    const onUpdate = jest.fn().mockImplementation(() => {
      updateCount++
      if (updateCount === 1) {
        return Promise.reject(new Error('First update failed'))
      }
      return Promise.resolve()
    })

    const { result } = renderHook(() =>
      useOptimisticUpdate({ value: 10 }, { onUpdate })
    )

    // First update (will fail)
    act(() => {
      result.current.update({ value: 20 })
    })

    await waitFor(() => {
      expect(result.current.error).toBeTruthy()
    })

    // Should rollback to 10
    expect(result.current.state.value).toBe(10)

    // Second update (will succeed)
    act(() => {
      result.current.update({ value: 30 })
    })

    await waitFor(() => {
      expect(result.current.isUpdating).toBe(false)
    })

    // Should commit to 30
    expect(result.current.state.value).toBe(30)
    expect(result.current.error).toBeNull()
  })

  it('should support manual rollback', () => {
    const onUpdate = jest.fn().mockResolvedValue(undefined)

    const { result } = renderHook(() =>
      useOptimisticUpdate({ value: 10 }, { onUpdate })
    )

    act(() => {
      result.current.update({ value: 20 })
    })

    // Update optimistically
    expect(result.current.state.value).toBe(20)

    // Manual rollback
    act(() => {
      result.current.rollback()
    })

    expect(result.current.state.value).toBe(10)
    expect(result.current.error).toBeNull()
  })

  it('should support reset to initial state', async () => {
    const onUpdate = jest.fn().mockResolvedValue(undefined)

    const { result } = renderHook(() =>
      useOptimisticUpdate({ value: 10 }, { onUpdate })
    )

    act(() => {
      result.current.update({ value: 20 })
    })

    await waitFor(() => {
      expect(result.current.isUpdating).toBe(false)
    })

    expect(result.current.state.value).toBe(20)

    // Reset to initial state
    act(() => {
      result.current.reset()
    })

    expect(result.current.state.value).toBe(10)
    expect(result.current.error).toBeNull()
    expect(result.current.isUpdating).toBe(false)
  })

  it('should handle complex state objects', async () => {
    const onUpdate = jest.fn().mockResolvedValue(undefined)

    interface ComplexState {
      id: string
      name: string
      count: number
      nested: {
        value: number
      }
    }

    const initialState: ComplexState = {
      id: '1',
      name: 'Test',
      count: 0,
      nested: { value: 100 },
    }

    const { result } = renderHook(() =>
      useOptimisticUpdate(initialState, { onUpdate })
    )

    act(() => {
      result.current.update({
        ...initialState,
        count: 5,
        nested: { value: 200 },
      })
    })

    expect(result.current.state.count).toBe(5)
    expect(result.current.state.nested.value).toBe(200)

    await waitFor(() => {
      expect(result.current.isUpdating).toBe(false)
    })

    expect(onUpdate).toHaveBeenCalledWith({
      id: '1',
      name: 'Test',
      count: 5,
      nested: { value: 200 },
    })
  })
})
