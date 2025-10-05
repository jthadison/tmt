/**
 * Tests for notification storage utilities
 */

import {
  loadNotifications,
  saveNotifications,
  clearNotifications,
  getStorageStats
} from '@/utils/notificationStorage'
import { Notification, NotificationPriority } from '@/types/notifications'

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value
    },
    removeItem: (key: string) => {
      delete store[key]
    },
    clear: () => {
      store = {}
    }
  }
})()

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
})

describe('notificationStorage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  const createNotification = (daysAgo: number = 0): Notification => {
    const date = new Date()
    date.setDate(date.getDate() - daysAgo)

    return {
      id: `notif_${Math.random()}`,
      priority: NotificationPriority.INFO,
      title: 'Test Notification',
      message: 'Test message',
      timestamp: date,
      read: false,
      dismissed: false
    }
  }

  describe('loadNotifications', () => {
    it('should return empty array if no notifications stored', () => {
      const result = loadNotifications()
      expect(result).toEqual([])
    })

    it('should load and parse stored notifications', () => {
      const notifications = [createNotification(), createNotification()]
      localStorage.setItem('notifications_history', JSON.stringify(notifications))

      const result = loadNotifications()

      expect(result).toHaveLength(2)
      expect(result[0].title).toBe('Test Notification')
    })

    it('should convert timestamp strings back to Date objects', () => {
      const notifications = [createNotification()]
      localStorage.setItem('notifications_history', JSON.stringify(notifications))

      const result = loadNotifications()

      expect(result[0].timestamp).toBeInstanceOf(Date)
    })

    it('should cleanup notifications older than 30 days', () => {
      const notifications = [
        createNotification(0),   // Today
        createNotification(20),  // 20 days ago
        createNotification(35),  // 35 days ago (should be removed)
        createNotification(40)   // 40 days ago (should be removed)
      ]
      localStorage.setItem('notifications_history', JSON.stringify(notifications))

      const result = loadNotifications()

      expect(result).toHaveLength(2)
    })

    it('should handle corrupted data gracefully', () => {
      localStorage.setItem('notifications_history', 'invalid json')

      const result = loadNotifications()

      expect(result).toEqual([])
    })
  })

  describe('saveNotifications', () => {
    it('should save notifications to localStorage', () => {
      const notifications = [createNotification(), createNotification()]

      saveNotifications(notifications)

      const stored = localStorage.getItem('notifications_history')
      expect(stored).toBeTruthy()

      const parsed = JSON.parse(stored!)
      expect(parsed).toHaveLength(2)
    })

    it('should enforce max 500 notification limit', () => {
      const notifications = Array(600).fill(null).map(() => createNotification())

      saveNotifications(notifications)

      const stored = localStorage.getItem('notifications_history')
      const parsed = JSON.parse(stored!)

      expect(parsed).toHaveLength(500)
    })

    it('should keep newest notifications when limiting', () => {
      const notifications = Array(600).fill(null).map((_, i) =>
        createNotification(600 - i) // Older ones have higher index
      )

      saveNotifications(notifications)

      const stored = localStorage.getItem('notifications_history')
      const parsed = JSON.parse(stored!)

      // Should keep the first 500 (newest) notifications
      expect(parsed).toHaveLength(500)
    })
  })

  describe('clearNotifications', () => {
    it('should remove notifications from localStorage', () => {
      const notifications = [createNotification()]
      localStorage.setItem('notifications_history', JSON.stringify(notifications))

      clearNotifications()

      const stored = localStorage.getItem('notifications_history')
      expect(stored).toBeNull()
    })
  })

  describe('getStorageStats', () => {
    it('should return zero stats for empty storage', () => {
      const stats = getStorageStats()

      expect(stats.count).toBe(0)
      expect(stats.oldestTimestamp).toBeNull()
      expect(stats.newestTimestamp).toBeNull()
      expect(stats.unreadCount).toBe(0)
    })

    it('should return correct stats for stored notifications', () => {
      const notifications = [
        createNotification(0),  // Newest
        { ...createNotification(5), read: false },
        { ...createNotification(10), read: true }  // Oldest
      ]
      localStorage.setItem('notifications_history', JSON.stringify(notifications))

      const stats = getStorageStats()

      expect(stats.count).toBe(3)
      expect(stats.unreadCount).toBe(2)
      expect(stats.oldestTimestamp).toBeInstanceOf(Date)
      expect(stats.newestTimestamp).toBeInstanceOf(Date)
    })
  })
})
