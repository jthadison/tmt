/**
 * Tests for useEventSubscription hook
 */

import { renderHook, waitFor } from '@testing-library/react'
import { useEventSubscription } from '@/hooks/useEventSubscription'
import * as useToastsModule from '@/hooks/useToasts'
import * as eventStreamService from '@/services/eventStreamService'
import { NotificationPriority } from '@/types/notifications'

// Mock dependencies
jest.mock('@/hooks/useToasts')
jest.mock('@/services/eventStreamService')

describe('useEventSubscription', () => {
  const mockShowToast = jest.fn()
  const mockEventStream = {
    connect: jest.fn(),
    disconnect: jest.fn(),
    subscribe: jest.fn(() => jest.fn()), // Returns unsubscribe function
    getConnectionStatus: jest.fn(() => true)
  }

  beforeEach(() => {
    jest.clearAllMocks()

    // Setup mocks
    ;(useToastsModule.useToasts as jest.Mock).mockReturnValue({
      showToast: mockShowToast
    })
    ;(eventStreamService.getOrchestratorEventStream as jest.Mock).mockReturnValue(mockEventStream)
  })

  describe('WebSocket connection', () => {
    it('should connect to event stream on mount', () => {
      renderHook(() => useEventSubscription())

      expect(mockEventStream.connect).toHaveBeenCalled()
    })

    it('should disconnect on unmount', () => {
      const { unmount } = renderHook(() => useEventSubscription())

      unmount()

      expect(mockEventStream.disconnect).toHaveBeenCalled()
    })

    it('should subscribe to events', () => {
      renderHook(() => useEventSubscription())

      expect(mockEventStream.subscribe).toHaveBeenCalled()
    })
  })

  describe('Event handling - Circuit Breaker', () => {
    it('should create critical notification for circuit breaker triggered', () => {
      let eventHandler: ((event: unknown) => void) | undefined

      mockEventStream.subscribe.mockImplementation((handler: (event: unknown) => void) => {
        eventHandler = handler
        return jest.fn()
      })

      renderHook(() => useEventSubscription())

      const event = {
        type: 'circuit_breaker.triggered',
        priority: 'critical',
        timestamp: '2025-01-01T12:00:00Z',
        data: { reason: 'Daily loss exceeded', threshold: 5.0 }
      }

      eventHandler?.(event)

      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          priority: NotificationPriority.CRITICAL,
          title: 'Circuit Breaker Triggered',
          message: 'Trading halted: Daily loss exceeded'
        })
      )
    })

    it('should create warning notification for circuit breaker threshold warning', () => {
      let eventHandler: ((event: any) => void) | undefined

      mockEventStream.subscribe.mockImplementation((handler) => {
        eventHandler = handler
        return jest.fn()
      })

      renderHook(() => useEventSubscription())

      const event = {
        type: 'circuit_breaker.threshold_warning',
        priority: 'warning',
        timestamp: '2025-01-01T12:00:00Z',
        data: { metric: 'daily_loss', value: 80 }
      }

      eventHandler?.(event)

      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          priority: NotificationPriority.WARNING,
          title: 'Circuit Breaker Warning'
        })
      )
    })
  })

  describe('Event handling - Trades', () => {
    it('should create info notification for trade opened', () => {
      let eventHandler: ((event: any) => void) | undefined

      mockEventStream.subscribe.mockImplementation((handler) => {
        eventHandler = handler
        return jest.fn()
      })

      renderHook(() => useEventSubscription())

      const event = {
        type: 'trade.opened',
        priority: 'info',
        timestamp: '2025-01-01T12:00:00Z',
        data: {
          instrument: 'EUR_USD',
          direction: 'LONG',
          units: 1000,
          price: 1.0950,
          trade_id: 'trade-123'
        }
      }

      eventHandler?.(event)

      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          priority: NotificationPriority.INFO,
          title: 'Trade Opened: EUR_USD',
          message: 'LONG 1000 units at 1.095'
        })
      )
    })

    it('should create success notification for profitable trade closed', () => {
      let eventHandler: ((event: any) => void) | undefined

      mockEventStream.subscribe.mockImplementation((handler) => {
        eventHandler = handler
        return jest.fn()
      })

      renderHook(() => useEventSubscription())

      const event = {
        type: 'trade.closed',
        priority: 'success',
        timestamp: '2025-01-01T12:00:00Z',
        data: {
          instrument: 'GBP_USD',
          pnl: 125.50,
          pnl_percent: 2.5,
          trade_id: 'trade-456'
        }
      }

      eventHandler?.(event)

      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          priority: NotificationPriority.SUCCESS,
          title: 'Trade Closed: GBP_USD',
          message: 'P&L: +$125.50 (+2.50%)'
        })
      )
    })

    it('should create warning notification for losing trade closed', () => {
      let eventHandler: ((event: any) => void) | undefined

      mockEventStream.subscribe.mockImplementation((handler) => {
        eventHandler = handler
        return jest.fn()
      })

      renderHook(() => useEventSubscription())

      const event = {
        type: 'trade.closed',
        priority: 'warning',
        timestamp: '2025-01-01T12:00:00Z',
        data: {
          instrument: 'USD_JPY',
          pnl: -45.25,
          pnl_percent: -1.2,
          trade_id: 'trade-789'
        }
      }

      eventHandler?.(event)

      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          priority: NotificationPriority.WARNING,
          title: 'Trade Closed: USD_JPY',
          message: 'P&L: -$45.25 (-1.20%)'
        })
      )
    })
  })

  describe('Event handling - Agent Health', () => {
    it('should create critical notification for agent failure', () => {
      let eventHandler: ((event: any) => void) | undefined

      mockEventStream.subscribe.mockImplementation((handler) => {
        eventHandler = handler
        return jest.fn()
      })

      renderHook(() => useEventSubscription())

      const event = {
        type: 'agent.health.changed',
        priority: 'critical',
        timestamp: '2025-01-01T12:00:00Z',
        data: {
          agent_name: 'Market Analysis',
          status: 'failed',
          reason: 'Connection timeout'
        }
      }

      eventHandler?.(event)

      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          priority: NotificationPriority.CRITICAL,
          title: 'Market Analysis: failed',
          message: 'Connection timeout'
        })
      )
    })

    it('should create success notification for agent recovery', () => {
      let eventHandler: ((event: any) => void) | undefined

      mockEventStream.subscribe.mockImplementation((handler) => {
        eventHandler = handler
        return jest.fn()
      })

      renderHook(() => useEventSubscription())

      const event = {
        type: 'agent.health.changed',
        priority: 'success',
        timestamp: '2025-01-01T12:00:00Z',
        data: {
          agent_name: 'Strategy Analysis',
          status: 'healthy',
          reason: 'Agent recovered'
        }
      }

      eventHandler?.(event)

      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          priority: NotificationPriority.SUCCESS,
          title: 'Strategy Analysis: healthy'
        })
      )
    })
  })

  describe('Unknown events', () => {
    it('should log warning for unknown event types', () => {
      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation()

      let eventHandler: ((event: any) => void) | undefined

      mockEventStream.subscribe.mockImplementation((handler) => {
        eventHandler = handler
        return jest.fn()
      })

      renderHook(() => useEventSubscription())

      const event = {
        type: 'unknown.event.type',
        priority: 'info',
        timestamp: '2025-01-01T12:00:00Z',
        data: {}
      }

      eventHandler?.(event)

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Unknown event type: unknown.event.type')
      )

      consoleSpy.mockRestore()
    })
  })

  describe('Connection status', () => {
    it('should track connection status', () => {
      const { result } = renderHook(() => useEventSubscription())

      waitFor(() => {
        expect(result.current.connectionStatus).toBe('connected')
      })
    })

    it('should update connection status when disconnected', () => {
      mockEventStream.getConnectionStatus.mockReturnValue(false)

      const { result } = renderHook(() => useEventSubscription())

      waitFor(() => {
        expect(result.current.connectionStatus).toBe('disconnected')
      })
    })
  })
})
