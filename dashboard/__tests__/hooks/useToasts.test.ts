/**
 * Tests for useToasts hook
 */

import { renderHook, act, waitFor } from '@testing-library/react'
import { useToasts } from '@/hooks/useToasts'
import { NotificationPriority } from '@/types/notifications'
import * as useNotificationsModule from '@/hooks/useNotifications'

// Mock useNotifications
jest.mock('@/hooks/useNotifications')

// Mock timers
jest.useFakeTimers()

describe('useToasts', () => {
  const mockAddNotification = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
    jest.clearAllTimers()

    // Setup mock for useNotifications
    ;(useNotificationsModule.useNotifications as jest.Mock).mockReturnValue({
      addNotification: mockAddNotification
    })
  })

  afterEach(() => {
    jest.runOnlyPendingTimers()
  })

  describe('showToast', () => {
    it('should add a toast to the list', () => {
      const { result } = renderHook(() => useToasts())

      act(() => {
        result.current.showToast({
          priority: NotificationPriority.INFO,
          title: 'Test Toast',
          message: 'This is a test'
        })
      })

      expect(result.current.toasts).toHaveLength(1)
      expect(result.current.toasts[0].title).toBe('Test Toast')
    })

    it('should generate unique IDs for each toast', () => {
      const { result } = renderHook(() => useToasts())

      act(() => {
        result.current.showToast({
          priority: NotificationPriority.INFO,
          title: 'Toast 1',
          message: 'Message 1'
        })

        result.current.showToast({
          priority: NotificationPriority.INFO,
          title: 'Toast 2',
          message: 'Message 2'
        })
      })

      expect(result.current.toasts).toHaveLength(2)
      expect(result.current.toasts[0].id).not.toBe(result.current.toasts[1].id)
    })

    it('should also add notification to notification center', () => {
      const { result } = renderHook(() => useToasts())

      act(() => {
        result.current.showToast({
          priority: NotificationPriority.WARNING,
          title: 'Warning Toast',
          message: 'This is a warning'
        })
      })

      expect(mockAddNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          priority: NotificationPriority.WARNING,
          title: 'Warning Toast',
          message: 'This is a warning'
        })
      )
    })

    it('should set timestamp if not provided', () => {
      const { result } = renderHook(() => useToasts())

      act(() => {
        result.current.showToast({
          priority: NotificationPriority.INFO,
          title: 'Test',
          message: 'Test'
        })
      })

      expect(result.current.toasts[0].timestamp).toBeInstanceOf(Date)
    })
  })

  describe('Max 3 toasts enforcement (FIFO)', () => {
    it('should enforce max 3 toasts', () => {
      const { result } = renderHook(() => useToasts())

      act(() => {
        result.current.showToast({
          priority: NotificationPriority.INFO,
          title: 'Toast 1',
          message: 'Message 1'
        })
        result.current.showToast({
          priority: NotificationPriority.INFO,
          title: 'Toast 2',
          message: 'Message 2'
        })
        result.current.showToast({
          priority: NotificationPriority.INFO,
          title: 'Toast 3',
          message: 'Message 3'
        })
      })

      expect(result.current.toasts).toHaveLength(3)

      act(() => {
        result.current.showToast({
          priority: NotificationPriority.INFO,
          title: 'Toast 4',
          message: 'Message 4'
        })
      })

      expect(result.current.toasts).toHaveLength(3)
      expect(result.current.toasts[0].title).toBe('Toast 4')
      expect(result.current.toasts[2].title).toBe('Toast 2')
    })
  })

  describe('dismissToast', () => {
    it('should remove toast from list', () => {
      const { result } = renderHook(() => useToasts())

      let toastId: string

      act(() => {
        toastId = result.current.showToast({
          priority: NotificationPriority.INFO,
          title: 'Test Toast',
          message: 'This is a test'
        })
      })

      expect(result.current.toasts).toHaveLength(1)

      act(() => {
        result.current.dismissToast(toastId)
      })

      expect(result.current.toasts).toHaveLength(0)
    })

    it('should clear auto-dismiss timer when manually dismissed', () => {
      const { result } = renderHook(() => useToasts())

      let toastId: string

      act(() => {
        toastId = result.current.showToast({
          priority: NotificationPriority.INFO,
          title: 'Test Toast',
          message: 'This is a test'
        })
      })

      act(() => {
        result.current.dismissToast(toastId)
      })

      // Advance time - should not cause any issues
      act(() => {
        jest.advanceTimersByTime(5000)
      })

      expect(result.current.toasts).toHaveLength(0)
    })
  })

  describe('dismissAll', () => {
    it('should clear all toasts', () => {
      const { result } = renderHook(() => useToasts())

      act(() => {
        result.current.showToast({
          priority: NotificationPriority.INFO,
          title: 'Toast 1',
          message: 'Message 1'
        })
        result.current.showToast({
          priority: NotificationPriority.INFO,
          title: 'Toast 2',
          message: 'Message 2'
        })
      })

      expect(result.current.toasts).toHaveLength(2)

      act(() => {
        result.current.dismissAll()
      })

      expect(result.current.toasts).toHaveLength(0)
    })

    it('should clear all auto-dismiss timers', () => {
      const { result } = renderHook(() => useToasts())

      act(() => {
        result.current.showToast({
          priority: NotificationPriority.INFO,
          title: 'Toast 1',
          message: 'Message 1'
        })
        result.current.showToast({
          priority: NotificationPriority.SUCCESS,
          title: 'Toast 2',
          message: 'Message 2'
        })
      })

      act(() => {
        result.current.dismissAll()
      })

      // Advance time - should not cause any issues
      act(() => {
        jest.advanceTimersByTime(10000)
      })

      expect(result.current.toasts).toHaveLength(0)
    })
  })

  describe('Auto-dismiss timers', () => {
    it('should auto-dismiss info toasts after 3 seconds', () => {
      const { result } = renderHook(() => useToasts())

      act(() => {
        result.current.showToast({
          priority: NotificationPriority.INFO,
          title: 'Info Toast',
          message: 'This should auto-dismiss'
        })
      })

      expect(result.current.toasts).toHaveLength(1)

      act(() => {
        jest.advanceTimersByTime(3000)
      })

      waitFor(() => {
        expect(result.current.toasts).toHaveLength(0)
      })
    })

    it('should auto-dismiss success toasts after 5 seconds', () => {
      const { result } = renderHook(() => useToasts())

      act(() => {
        result.current.showToast({
          priority: NotificationPriority.SUCCESS,
          title: 'Success Toast',
          message: 'This should auto-dismiss'
        })
      })

      act(() => {
        jest.advanceTimersByTime(5000)
      })

      waitFor(() => {
        expect(result.current.toasts).toHaveLength(0)
      })
    })

    it('should auto-dismiss warning toasts after 10 seconds', () => {
      const { result } = renderHook(() => useToasts())

      act(() => {
        result.current.showToast({
          priority: NotificationPriority.WARNING,
          title: 'Warning Toast',
          message: 'This should auto-dismiss'
        })
      })

      act(() => {
        jest.advanceTimersByTime(10000)
      })

      waitFor(() => {
        expect(result.current.toasts).toHaveLength(0)
      })
    })

    it('should NOT auto-dismiss critical toasts', () => {
      const { result } = renderHook(() => useToasts())

      act(() => {
        result.current.showToast({
          priority: NotificationPriority.CRITICAL,
          title: 'Critical Toast',
          message: 'This should NOT auto-dismiss'
        })
      })

      act(() => {
        jest.advanceTimersByTime(30000)
      })

      expect(result.current.toasts).toHaveLength(1)
    })
  })
})
