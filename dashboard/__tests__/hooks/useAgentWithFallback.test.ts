/**
 * Unit Tests for useAgentWithFallback Hook
 *
 * Tests:
 * - Agent online/offline status
 * - Fallback data usage
 * - Automatic retry
 * - Last seen timestamp
 * - Refetch functionality
 */

import { renderHook, waitFor } from '@testing-library/react'
import { useAgentWithFallback } from '@/hooks/useAgentWithFallback'

describe('useAgentWithFallback', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    jest.useFakeTimers()
  })

  afterEach(() => {
    jest.useRealTimers()
  })

  it('should fetch data when agent is online', async () => {
    const mockData = { patterns: ['Pattern 1', 'Pattern 2'] }

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    })

    const { result } = renderHook(() =>
      useAgentWithFallback('http://localhost:8008/patterns', null)
    )

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.data).toEqual(mockData)
    expect(result.current.status.online).toBe(true)
    expect(result.current.status.usingFallback).toBe(false)
    expect(result.current.status.lastSeen).toBeInstanceOf(Date)
  })

  it('should use fallback data when agent is offline', async () => {
    const fallbackData = { patterns: ['Cached Pattern'] }

    global.fetch = jest.fn().mockRejectedValue(new Error('Agent offline'))

    const { result } = renderHook(() =>
      useAgentWithFallback('http://localhost:8008/patterns', fallbackData)
    )

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.data).toEqual(fallbackData)
    expect(result.current.status.online).toBe(false)
    expect(result.current.status.usingFallback).toBe(true)
  })

  it('should retry every 30 seconds when agent is offline', async () => {
    let fetchCount = 0

    global.fetch = jest.fn().mockImplementation(() => {
      fetchCount++
      if (fetchCount < 3) {
        return Promise.reject(new Error('Agent offline'))
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ patterns: ['New Pattern'] }),
      })
    })

    const { result } = renderHook(() =>
      useAgentWithFallback('http://localhost:8008/patterns', null, {
        retryIntervalMs: 30000,
      })
    )

    // Initial fetch fails
    await waitFor(() => {
      expect(result.current.status.online).toBe(false)
    })

    expect(fetchCount).toBe(1)

    // Wait 30 seconds - first retry
    jest.advanceTimersByTime(30000)
    await waitFor(() => {
      expect(fetchCount).toBe(2)
    })

    // Wait 30 seconds - second retry (succeeds)
    jest.advanceTimersByTime(30000)
    await waitFor(() => {
      expect(result.current.status.online).toBe(true)
    })

    expect(fetchCount).toBe(3)
    expect(result.current.data).toEqual({ patterns: ['New Pattern'] })
  })

  it('should update lastSeen timestamp on successful fetch', async () => {
    const mockData = { patterns: ['Pattern 1'] }

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    })

    const { result } = renderHook(() =>
      useAgentWithFallback('http://localhost:8008/patterns', null)
    )

    await waitFor(() => {
      expect(result.current.status.lastSeen).toBeInstanceOf(Date)
    })

    const firstLastSeen = result.current.status.lastSeen

    // Wait and refetch
    jest.advanceTimersByTime(1000)

    await waitFor(() => {
      if (result.current.status.lastSeen && firstLastSeen) {
        expect(result.current.status.lastSeen.getTime()).toBeGreaterThanOrEqual(
          firstLastSeen.getTime()
        )
      }
    })
  })

  it('should support manual refetch', async () => {
    let fetchCount = 0
    const mockData = { patterns: ['Pattern 1'] }

    global.fetch = jest.fn().mockImplementation(() => {
      fetchCount++
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockData),
      })
    })

    const { result } = renderHook(() =>
      useAgentWithFallback('http://localhost:8008/patterns', null)
    )

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(fetchCount).toBe(1)

    // Manual refetch
    await result.current.refetch()

    expect(fetchCount).toBe(2)
  })

  it('should handle enabled/disabled state', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ patterns: [] }),
    })

    const { result, rerender } = renderHook(
      ({ enabled }) => useAgentWithFallback('http://localhost:8008/patterns', null, { enabled }),
      { initialProps: { enabled: false } }
    )

    // Should not fetch when disabled
    expect(global.fetch).not.toHaveBeenCalled()

    // Enable
    rerender({ enabled: true })

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalled()
    })
  })

  it('should handle HTTP error responses', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
    })

    const fallbackData = { patterns: ['Fallback'] }

    const { result } = renderHook(() =>
      useAgentWithFallback('http://localhost:8008/patterns', fallbackData)
    )

    await waitFor(() => {
      expect(result.current.status.online).toBe(false)
    })

    expect(result.current.status.usingFallback).toBe(true)
    expect(result.current.data).toEqual(fallbackData)
  })

  it('should cancel pending requests on unmount', async () => {
    const abortSpy = jest.spyOn(AbortController.prototype, 'abort')

    global.fetch = jest.fn().mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 10000))
    )

    const { unmount } = renderHook(() =>
      useAgentWithFallback('http://localhost:8008/patterns', null)
    )

    unmount()

    expect(abortSpy).toHaveBeenCalled()
    abortSpy.mockRestore()
  })

  it('should handle custom retry interval', async () => {
    let fetchCount = 0

    global.fetch = jest.fn().mockImplementation(() => {
      fetchCount++
      return Promise.reject(new Error('Agent offline'))
    })

    renderHook(() =>
      useAgentWithFallback('http://localhost:8008/patterns', null, {
        retryIntervalMs: 10000, // 10 seconds
      })
    )

    // Initial fetch
    await waitFor(() => {
      expect(fetchCount).toBe(1)
    })

    // Wait 10 seconds
    jest.advanceTimersByTime(10000)

    await waitFor(() => {
      expect(fetchCount).toBe(2)
    })
  })
})
