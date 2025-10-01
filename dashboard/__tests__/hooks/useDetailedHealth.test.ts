/**
 * Tests for useDetailedHealth hook
 */

import { renderHook, waitFor, act } from '@testing-library/react'
import { useDetailedHealth } from '@/hooks/useDetailedHealth'
import { useWebSocket } from '@/hooks/useWebSocket'
import { DetailedHealthData } from '@/types/health'
import { ConnectionStatus } from '@/types/websocket'

// Mock the useWebSocket hook
jest.mock('@/hooks/useWebSocket')

// Mock fetch
global.fetch = jest.fn()

const mockUseWebSocket = useWebSocket as jest.MockedFunction<typeof useWebSocket>
const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>

describe('useDetailedHealth Hook', () => {
  const mockHealthData: DetailedHealthData = {
    agents: [
      {
        name: 'Market Analysis',
        port: 8001,
        status: 'healthy',
        latency_ms: 45,
        last_check: new Date().toISOString(),
      },
    ],
    services: [
      {
        name: 'Orchestrator',
        port: 8089,
        status: 'healthy',
        latency_ms: 20,
        last_check: new Date().toISOString(),
      },
    ],
    external_services: [
      {
        name: 'OANDA API',
        status: 'connected',
        latency_ms: 120,
        last_check: new Date().toISOString(),
      },
    ],
    circuit_breaker: {
      max_drawdown: { current: 2.5, threshold: 5.0, limit: 10.0 },
      daily_loss: { current: 150.0, threshold: 500.0, limit: 1000.0 },
      consecutive_losses: { current: 2, threshold: 5, limit: 10 },
    },
    system_metrics: {
      avg_latency_ms: 55,
      active_positions: 3,
      daily_pnl: 250.75,
    },
    timestamp: new Date().toISOString(),
  }

  const defaultWebSocketReturn = {
    connectionStatus: ConnectionStatus.CONNECTED,
    lastMessage: null,
    sendMessage: jest.fn(),
    connect: jest.fn(),
    disconnect: jest.fn(),
    isConnected: true,
    reconnectCount: 0,
    lastError: null,
  }

  beforeEach(() => {
    jest.clearAllMocks()
    jest.useFakeTimers()

    mockUseWebSocket.mockReturnValue(defaultWebSocketReturn)

    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockHealthData,
    } as Response)
  })

  afterEach(() => {
    jest.useRealTimers()
  })

  describe('Initialization', () => {
    it('should initialize with default values', () => {
      const { result } = renderHook(() => useDetailedHealth())

      expect(result.current.healthData).toBeNull()
      expect(result.current.loading).toBe(true)
      expect(result.current.error).toBeNull()
      expect(result.current.lastUpdate).toBeNull()
    })

    it('should connect to WebSocket when enabled', () => {
      const connect = jest.fn()
      mockUseWebSocket.mockReturnValue({
        ...defaultWebSocketReturn,
        connect,
      })

      renderHook(() => useDetailedHealth({ enableWebSocket: true }))

      expect(connect).toHaveBeenCalled()
    })

    it('should start polling when WebSocket is disabled', async () => {
      renderHook(() =>
        useDetailedHealth({ enableWebSocket: false, pollingInterval: 1000 })
      )

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/health/detailed'),
          expect.any(Object)
        )
      })
    })
  })

  describe('Data Fetching', () => {
    it('should fetch health data successfully', async () => {
      const { result } = renderHook(() => useDetailedHealth({ enableWebSocket: false }))

      await waitFor(() => {
        expect(result.current.healthData).not.toBeNull()
        expect(result.current.loading).toBe(false)
        expect(result.current.error).toBeNull()
      })

      expect(result.current.healthData?.agents).toHaveLength(1)
      expect(result.current.healthData?.services).toHaveLength(1)
      expect(result.current.healthData?.system_metrics.avg_latency_ms).toBe(55)
    })

    it('should handle fetch errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'))

      const { result } = renderHook(() => useDetailedHealth({ enableWebSocket: false }))

      await waitFor(() => {
        expect(result.current.error).toBe('Network error')
        expect(result.current.loading).toBe(false)
        expect(result.current.healthData).toBeNull()
      })
    })

    it('should handle non-ok responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: 'Internal Server Error',
      } as Response)

      const { result } = renderHook(() => useDetailedHealth({ enableWebSocket: false }))

      await waitFor(() => {
        expect(result.current.error).toContain('Internal Server Error')
        expect(result.current.loading).toBe(false)
      })
    })
  })

  describe('WebSocket Integration', () => {
    it('should process WebSocket messages', async () => {
      const { result, rerender } = renderHook(() => useDetailedHealth())

      // Simulate WebSocket message
      mockUseWebSocket.mockReturnValue({
        ...defaultWebSocketReturn,
        lastMessage: {
          type: 'health.detailed',
          data: mockHealthData,
          timestamp: new Date().toISOString(),
          correlation_id: 'test-123',
        },
      })

      rerender()

      await waitFor(() => {
        expect(result.current.healthData).not.toBeNull()
        expect(result.current.healthData?.agents).toHaveLength(1)
      })
    })

    it('should fall back to polling when WebSocket disconnects', async () => {
      const { rerender } = renderHook(() => useDetailedHealth({ pollingInterval: 1000 }))

      // Start with connected WebSocket
      mockUseWebSocket.mockReturnValue({
        ...defaultWebSocketReturn,
        isConnected: true,
      })

      rerender()

      // Disconnect WebSocket
      mockUseWebSocket.mockReturnValue({
        ...defaultWebSocketReturn,
        isConnected: false,
        connectionStatus: ConnectionStatus.ERROR,
      })

      rerender()

      // Should start polling
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/health/detailed'),
          expect.any(Object)
        )
      })
    })
  })

  describe('Latency History', () => {
    it('should track latency history for agents', async () => {
      const { result } = renderHook(() => useDetailedHealth({ enableWebSocket: false }))

      await waitFor(() => {
        expect(result.current.healthData).not.toBeNull()
      })

      // Check latency history
      const agentKey = 'agent-8001'
      expect(result.current.latencyHistory.has(agentKey)).toBe(true)
      expect(result.current.latencyHistory.get(agentKey)).toContain(45)
    })

    it('should limit latency history to 20 entries', async () => {
      const { result, rerender } = renderHook(() => useDetailedHealth())

      // Simulate multiple updates
      for (let i = 0; i < 25; i++) {
        mockUseWebSocket.mockReturnValue({
          ...defaultWebSocketReturn,
          lastMessage: {
            type: 'health.detailed',
            data: {
              ...mockHealthData,
              agents: [
                {
                  ...mockHealthData.agents[0],
                  latency_ms: 40 + i,
                },
              ],
            },
            timestamp: new Date().toISOString(),
            correlation_id: `test-${i}`,
          },
        })

        rerender()
      }

      await waitFor(() => {
        const agentKey = 'agent-8001'
        const history = result.current.latencyHistory.get(agentKey)
        expect(history).toBeDefined()
        expect(history!.length).toBeLessThanOrEqual(20)
      })
    })
  })

  describe('Manual Refresh', () => {
    it('should refresh data when refreshData is called', async () => {
      const { result } = renderHook(() => useDetailedHealth({ enableWebSocket: false }))

      await waitFor(() => {
        expect(result.current.healthData).not.toBeNull()
      })

      mockFetch.mockClear()

      await act(async () => {
        await result.current.refreshData()
      })

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/health/detailed'),
        expect.any(Object)
      )
    })

    it('should set loading state during refresh', async () => {
      const { result } = renderHook(() => useDetailedHealth({ enableWebSocket: false }))

      await waitFor(() => {
        expect(result.current.healthData).not.toBeNull()
      })

      act(() => {
        result.current.refreshData()
      })

      expect(result.current.loading).toBe(true)

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })
    })
  })

  describe('Polling Behavior', () => {
    it('should poll at specified interval', async () => {
      renderHook(() =>
        useDetailedHealth({ enableWebSocket: false, pollingInterval: 5000 })
      )

      // Initial fetch
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(1)
      })

      mockFetch.mockClear()

      // Advance timers by polling interval
      act(() => {
        jest.advanceTimersByTime(5000)
      })

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(1)
      })
    })

    it('should stop polling when component unmounts', async () => {
      const { unmount } = renderHook(() =>
        useDetailedHealth({ enableWebSocket: false, pollingInterval: 5000 })
      )

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled()
      })

      mockFetch.mockClear()

      unmount()

      // Advance timers - should not fetch after unmount
      act(() => {
        jest.advanceTimersByTime(5000)
      })

      expect(mockFetch).not.toHaveBeenCalled()
    })
  })

  describe('Last Update Tracking', () => {
    it('should update lastUpdate timestamp on data fetch', async () => {
      const { result } = renderHook(() => useDetailedHealth({ enableWebSocket: false }))

      await waitFor(() => {
        expect(result.current.lastUpdate).not.toBeNull()
      })

      expect(result.current.lastUpdate instanceof Date).toBe(true)
    })

    it('should update lastUpdate on WebSocket message', async () => {
      const { result, rerender } = renderHook(() => useDetailedHealth())

      mockUseWebSocket.mockReturnValue({
        ...defaultWebSocketReturn,
        lastMessage: {
          type: 'health.detailed',
          data: mockHealthData,
          timestamp: new Date().toISOString(),
          correlation_id: 'test-123',
        },
      })

      rerender()

      await waitFor(() => {
        expect(result.current.lastUpdate).not.toBeNull()
      })
    })
  })

  describe('Connection Status', () => {
    it('should expose WebSocket connection status', () => {
      mockUseWebSocket.mockReturnValue({
        ...defaultWebSocketReturn,
        connectionStatus: ConnectionStatus.RECONNECTING,
      })

      const { result } = renderHook(() => useDetailedHealth())

      expect(result.current.connectionStatus).toBe(ConnectionStatus.RECONNECTING)
    })
  })
})
