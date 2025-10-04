/**
 * Tests for useSessionPerformance hook
 */

import { renderHook, waitFor } from '@testing-library/react'
import { useSessionPerformance } from '@/hooks/useSessionPerformance'
import { useWebSocket } from '@/hooks/useWebSocket'
import { TradingSession } from '@/types/session'

// Mock dependencies
jest.mock('@/hooks/useWebSocket')

global.fetch = jest.fn()

const mockUseWebSocket = useWebSocket as jest.MockedFunction<typeof useWebSocket>

describe('useSessionPerformance', () => {
  const mockDateRange = {
    start: new Date('2025-01-01'),
    end: new Date('2025-01-31')
  }

  beforeEach(() => {
    jest.clearAllMocks()
    mockUseWebSocket.mockReturnValue({
      connectionStatus: 'CONNECTED' as any,
      lastMessage: null,
      sendMessage: jest.fn(),
      connect: jest.fn(),
      disconnect: jest.fn(),
      isConnected: true,
      reconnectCount: 0,
      lastError: null
    })
  })

  it('fetches session performance data on mount', async () => {
    const mockResponse = {
      sessions: [
        {
          session: 'london',
          total_pnl: 1000,
          trade_count: 10,
          win_count: 7,
          win_rate: 70,
          confidence_threshold: 72
        }
      ]
    }

    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse
    })

    const { result } = renderHook(() =>
      useSessionPerformance({ dateRange: mockDateRange })
    )

    expect(result.current.isLoading).toBe(true)

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.sessions).toHaveLength(1)
    expect(result.current.sessions[0].session).toBe(TradingSession.LONDON)
    expect(result.current.sessions[0].totalPnL).toBe(1000)
  })

  it('sets error state when fetch fails', async () => {
    ;(global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'))

    const { result } = renderHook(() =>
      useSessionPerformance({ dateRange: mockDateRange })
    )

    await waitFor(() => {
      expect(result.current.error).toBe('Network error')
    })
  })

  it('determines active session correctly', async () => {
    // Mock current time to be in London session (14:00 GMT)
    jest.useFakeTimers()
    jest.setSystemTime(new Date('2025-01-15T14:00:00Z'))

    const mockResponse = {
      sessions: [
        {
          session: 'london',
          total_pnl: 1000,
          trade_count: 10,
          win_count: 7,
          win_rate: 70,
          confidence_threshold: 72
        }
      ]
    }

    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse
    })

    const { result } = renderHook(() =>
      useSessionPerformance({ dateRange: mockDateRange })
    )

    await waitFor(() => {
      expect(result.current.activeSession).toBe(TradingSession.LONDON)
      expect(result.current.sessions[0].isActive).toBe(true)
    })

    jest.useRealTimers()
  })

  it('handles WebSocket trade completion messages', async () => {
    const mockResponse = {
      sessions: [
        {
          session: 'london',
          total_pnl: 1000,
          trade_count: 10,
          win_count: 7,
          win_rate: 70,
          confidence_threshold: 72
        }
      ]
    }

    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse
    })

    const { result, rerender } = renderHook(() =>
      useSessionPerformance({ dateRange: mockDateRange })
    )

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    // Simulate WebSocket trade completion message
    mockUseWebSocket.mockReturnValue({
      connectionStatus: 'CONNECTED' as any,
      lastMessage: {
        type: 'trade.completed',
        data: {
          session: 'london',
          pnL: 150,
          timestamp: new Date().toISOString()
        }
      } as any,
      sendMessage: jest.fn(),
      connect: jest.fn(),
      disconnect: jest.fn(),
      isConnected: true,
      reconnectCount: 0,
      lastError: null
    })

    rerender()

    await waitFor(() => {
      const londonSession = result.current.sessions.find(s => s.session === TradingSession.LONDON)
      expect(londonSession?.totalPnL).toBe(1150) // 1000 + 150
      expect(londonSession?.tradeCount).toBe(11) // 10 + 1
    })
  })

  it('refetches data when refetch is called', async () => {
    const mockResponse = {
      sessions: [
        {
          session: 'london',
          total_pnl: 1000,
          trade_count: 10,
          win_count: 7,
          win_rate: 70,
          confidence_threshold: 72
        }
      ]
    }

    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockResponse
    })

    const { result } = renderHook(() =>
      useSessionPerformance({ dateRange: mockDateRange })
    )

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(global.fetch).toHaveBeenCalledTimes(1)

    // Call refetch
    result.current.refetch()

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(2)
    })
  })
})
