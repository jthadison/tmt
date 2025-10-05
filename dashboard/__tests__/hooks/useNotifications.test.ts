/**
 * Tests for useNotifications hook
 */

import { renderHook, act, waitFor } from '@testing-library/react'
import { useNotifications } from '@/hooks/useNotifications'
import { NotificationPriority } from '@/types/notifications'
import * as storage from '@/utils/notificationStorage'

// Mock the storage utilities
jest.mock('@/utils/notificationStorage')

const mockLoadNotifications = storage.loadNotifications as jest.MockedFunction<typeof storage.loadNotifications>
const mockSaveNotifications = storage.saveNotifications as jest.MockedFunction<typeof storage.saveNotifications>

describe('useNotifications', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockLoadNotifications.mockReturnValue([])
  })

  it('should initialize with empty notifications', () => {
    const { result } = renderHook(() => useNotifications())

    expect(result.current.notifications).toEqual([])
    expect(result.current.unreadCount).toBe(0)
    expect(result.current.hasNotifications).toBe(false)
  })

  it('should load notifications from storage on mount', () => {
    const storedNotifications = [
      {
        id: 'notif_1',
        priority: NotificationPriority.INFO,
        title: 'Test',
        message: 'Test message',
        timestamp: new Date(),
        read: false,
        dismissed: false
      }
    ]

    mockLoadNotifications.mockReturnValue(storedNotifications)

    const { result } = renderHook(() => useNotifications())

    waitFor(() => {
      expect(result.current.notifications).toHaveLength(1)
      expect(mockLoadNotifications).toHaveBeenCalledTimes(1)
    })
  })

  it('should add new notification', () => {
    const { result } = renderHook(() => useNotifications())

    act(() => {
      result.current.addNotification({
        priority: NotificationPriority.SUCCESS,
        title: 'Trade Closed',
        message: 'EUR/USD position closed with +$150 profit',
        timestamp: new Date()
      })
    })

    expect(result.current.notifications).toHaveLength(1)
    expect(result.current.notifications[0].title).toBe('Trade Closed')
    expect(result.current.notifications[0].read).toBe(false)
    expect(result.current.notifications[0].dismissed).toBe(false)
  })

  it('should mark notification as read', () => {
    mockLoadNotifications.mockReturnValue([
      {
        id: 'notif_1',
        priority: NotificationPriority.INFO,
        title: 'Test',
        message: 'Test message',
        timestamp: new Date(),
        read: false,
        dismissed: false
      }
    ])

    const { result } = renderHook(() => useNotifications())

    act(() => {
      result.current.markRead('notif_1')
    })

    waitFor(() => {
      expect(result.current.notifications[0].read).toBe(true)
    })
  })

  it('should mark all notifications as read', () => {
    const { result } = renderHook(() => useNotifications())

    act(() => {
      result.current.addNotification({
        priority: NotificationPriority.INFO,
        title: 'Test 1',
        message: 'Message 1',
        timestamp: new Date()
      })
      result.current.addNotification({
        priority: NotificationPriority.INFO,
        title: 'Test 2',
        message: 'Message 2',
        timestamp: new Date()
      })
    })

    expect(result.current.unreadCount).toBe(2)

    act(() => {
      result.current.markAllRead()
    })

    expect(result.current.unreadCount).toBe(0)
    expect(result.current.notifications.every(n => n.read)).toBe(true)
  })

  it('should dismiss notification', () => {
    mockLoadNotifications.mockReturnValue([
      {
        id: 'notif_1',
        priority: NotificationPriority.INFO,
        title: 'Test',
        message: 'Test message',
        timestamp: new Date(),
        read: false,
        dismissed: false
      }
    ])

    const { result } = renderHook(() => useNotifications())

    act(() => {
      result.current.dismiss('notif_1')
    })

    waitFor(() => {
      expect(result.current.notifications).toHaveLength(0) // Dismissed notifications are filtered out
    })
  })

  it('should clear all notifications', () => {
    const { result } = renderHook(() => useNotifications())

    act(() => {
      result.current.addNotification({
        priority: NotificationPriority.INFO,
        title: 'Test 1',
        message: 'Message 1',
        timestamp: new Date()
      })
      result.current.addNotification({
        priority: NotificationPriority.INFO,
        title: 'Test 2',
        message: 'Message 2',
        timestamp: new Date()
      })
    })

    expect(result.current.hasNotifications).toBe(true)

    act(() => {
      result.current.clearAll()
    })

    expect(result.current.hasNotifications).toBe(false)
  })

  it('should calculate unread count correctly', () => {
    const { result } = renderHook(() => useNotifications())

    act(() => {
      result.current.addNotification({
        priority: NotificationPriority.INFO,
        title: 'Test 1',
        message: 'Message 1',
        timestamp: new Date()
      })
      result.current.addNotification({
        priority: NotificationPriority.INFO,
        title: 'Test 2',
        message: 'Message 2',
        timestamp: new Date()
      })
      result.current.addNotification({
        priority: NotificationPriority.INFO,
        title: 'Test 3',
        message: 'Message 3',
        timestamp: new Date()
      })
    })

    expect(result.current.unreadCount).toBe(3)

    act(() => {
      result.current.markRead(result.current.notifications[0].id)
    })

    expect(result.current.unreadCount).toBe(2)
  })

  it('should group notifications by date', () => {
    const now = new Date()
    const yesterday = new Date(now)
    yesterday.setDate(yesterday.getDate() - 1)

    const { result } = renderHook(() => useNotifications())

    act(() => {
      result.current.addNotification({
        priority: NotificationPriority.INFO,
        title: 'Today',
        message: 'Today notification',
        timestamp: now
      })
      result.current.addNotification({
        priority: NotificationPriority.INFO,
        title: 'Yesterday',
        message: 'Yesterday notification',
        timestamp: yesterday
      })
    })

    expect(result.current.groupedByDate.today.length).toBeGreaterThan(0)
    expect(result.current.groupedByDate.yesterday.length).toBeGreaterThan(0)
  })

  it('should save to storage after changes', async () => {
    const { result } = renderHook(() => useNotifications())

    await waitFor(() => {
      expect(result.current.isLoaded).toBe(true)
    })

    act(() => {
      result.current.addNotification({
        priority: NotificationPriority.INFO,
        title: 'Test',
        message: 'Test message',
        timestamp: new Date()
      })
    })

    await waitFor(() => {
      expect(mockSaveNotifications).toHaveBeenCalled()
    })
  })

  it('should mark group as read', () => {
    const now = new Date()

    const { result } = renderHook(() => useNotifications())

    act(() => {
      result.current.addNotification({
        priority: NotificationPriority.INFO,
        title: 'Test 1',
        message: 'Message 1',
        timestamp: now,
        groupKey: 'test_group'
      })
      result.current.addNotification({
        priority: NotificationPriority.INFO,
        title: 'Test 2',
        message: 'Message 2',
        timestamp: new Date(now.getTime() + 1000),
        groupKey: 'test_group'
      })
    })

    const group = result.current.groupedByDate.today[0]

    act(() => {
      result.current.markGroupRead(group)
    })

    expect(result.current.unreadCount).toBe(0)
  })
})
