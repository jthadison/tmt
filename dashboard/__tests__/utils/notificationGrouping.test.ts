/**
 * Tests for notification grouping logic
 */

import {
  groupNotifications,
  getMostRecentNotification,
  hasUnreadNotifications,
  getUnreadCount,
  getGroupTitle
} from '@/utils/notificationGrouping'
import { Notification, NotificationPriority, NotificationGroup } from '@/types/notifications'

describe('notificationGrouping', () => {
  const createNotification = (
    overrides: Partial<Notification> = {}
  ): Notification => ({
    id: `notif_${Math.random()}`,
    priority: NotificationPriority.INFO,
    title: 'Test Notification',
    message: 'Test message',
    timestamp: new Date(),
    read: false,
    dismissed: false,
    groupKey: 'test_group',
    ...overrides
  })

  describe('groupNotifications', () => {
    it('should return empty array for empty input', () => {
      const result = groupNotifications([])
      expect(result).toEqual([])
    })

    it('should never group CRITICAL notifications', () => {
      const now = new Date()
      const notifications: Notification[] = [
        createNotification({
          priority: NotificationPriority.CRITICAL,
          groupKey: 'critical_events',
          timestamp: now
        }),
        createNotification({
          priority: NotificationPriority.CRITICAL,
          groupKey: 'critical_events',
          timestamp: new Date(now.getTime() + 1000)
        })
      ]

      const result = groupNotifications(notifications)

      expect(result).toHaveLength(2)
      expect(result[0].isGrouped).toBe(false)
      expect(result[1].isGrouped).toBe(false)
    })

    it('should group similar notifications within 30-minute window', () => {
      const now = new Date()
      const notifications: Notification[] = [
        createNotification({
          groupKey: 'trade_closed',
          timestamp: now
        }),
        createNotification({
          groupKey: 'trade_closed',
          timestamp: new Date(now.getTime() + 10 * 60 * 1000) // 10 minutes later
        }),
        createNotification({
          groupKey: 'trade_closed',
          timestamp: new Date(now.getTime() + 20 * 60 * 1000) // 20 minutes later
        })
      ]

      const result = groupNotifications(notifications)

      expect(result).toHaveLength(1)
      expect(result[0].count).toBe(3)
      expect(result[0].isGrouped).toBe(true)
    })

    it('should not group notifications outside 30-minute window', () => {
      const now = new Date()
      const notifications: Notification[] = [
        createNotification({
          groupKey: 'trade_closed',
          timestamp: now
        }),
        createNotification({
          groupKey: 'trade_closed',
          timestamp: new Date(now.getTime() + 35 * 60 * 1000) // 35 minutes later
        })
      ]

      const result = groupNotifications(notifications)

      expect(result).toHaveLength(2)
      expect(result[0].isGrouped).toBe(false)
      expect(result[1].isGrouped).toBe(false)
    })

    it('should not group notifications with different groupKeys', () => {
      const now = new Date()
      const notifications: Notification[] = [
        createNotification({
          groupKey: 'trade_closed',
          timestamp: now
        }),
        createNotification({
          groupKey: 'trade_opened',
          timestamp: new Date(now.getTime() + 1000)
        })
      ]

      const result = groupNotifications(notifications)

      expect(result).toHaveLength(2)
      expect(result[0].isGrouped).toBe(false)
      expect(result[1].isGrouped).toBe(false)
    })

    it('should not group notifications with null groupKey', () => {
      const now = new Date()
      const notifications: Notification[] = [
        createNotification({
          groupKey: null,
          timestamp: now
        }),
        createNotification({
          groupKey: null,
          timestamp: new Date(now.getTime() + 1000)
        })
      ]

      const result = groupNotifications(notifications)

      expect(result).toHaveLength(2)
      expect(result[0].isGrouped).toBe(false)
      expect(result[1].isGrouped).toBe(false)
    })
  })

  describe('getMostRecentNotification', () => {
    it('should return first notification from group', () => {
      const notifications: Notification[] = [
        createNotification({ id: 'first', timestamp: new Date() }),
        createNotification({ id: 'second', timestamp: new Date() })
      ]

      const group: NotificationGroup = {
        notifications,
        count: 2,
        isGrouped: true
      }

      const result = getMostRecentNotification(group)
      expect(result.id).toBe('first')
    })
  })

  describe('hasUnreadNotifications', () => {
    it('should return true if any notification is unread', () => {
      const group: NotificationGroup = {
        notifications: [
          createNotification({ read: false }),
          createNotification({ read: true })
        ],
        count: 2,
        isGrouped: true
      }

      expect(hasUnreadNotifications(group)).toBe(true)
    })

    it('should return false if all notifications are read', () => {
      const group: NotificationGroup = {
        notifications: [
          createNotification({ read: true }),
          createNotification({ read: true })
        ],
        count: 2,
        isGrouped: true
      }

      expect(hasUnreadNotifications(group)).toBe(false)
    })
  })

  describe('getUnreadCount', () => {
    it('should count unread notifications', () => {
      const group: NotificationGroup = {
        notifications: [
          createNotification({ read: false }),
          createNotification({ read: true }),
          createNotification({ read: false })
        ],
        count: 3,
        isGrouped: true
      }

      expect(getUnreadCount(group)).toBe(2)
    })
  })

  describe('getGroupTitle', () => {
    it('should return title without count for single notification', () => {
      const group: NotificationGroup = {
        notifications: [
          createNotification({ title: 'Trade Closed' })
        ],
        count: 1,
        isGrouped: false
      }

      expect(getGroupTitle(group)).toBe('Trade Closed')
    })

    it('should return title with count for grouped notifications', () => {
      const group: NotificationGroup = {
        notifications: [
          createNotification({ title: 'Trade Closed' }),
          createNotification({ title: 'Trade Closed' }),
          createNotification({ title: 'Trade Closed' })
        ],
        count: 3,
        isGrouped: true
      }

      expect(getGroupTitle(group)).toBe('Trade Closed (3)')
    })
  })
})
