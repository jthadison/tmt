/**
 * Tests for notification delivery service
 */

import {
  shouldDeliverNotification,
  calculateNotificationFrequency
} from '@/services/notificationDeliveryService'
import { Notification, NotificationPriority } from '@/types/notifications'
import {
  NotificationPreferences,
  DEFAULT_PREFERENCES
} from '@/types/notificationPreferences'

describe('notificationDeliveryService', () => {
  const createTestNotification = (
    priority: NotificationPriority = NotificationPriority.INFO
  ): Notification => ({
    id: 'test-1',
    priority,
    title: 'Test Notification',
    message: 'Test message',
    timestamp: new Date(),
    read: false,
    dismissed: false
  })

  describe('shouldDeliverNotification', () => {
    it('should allow in-app delivery when enabled', () => {
      const notification = createTestNotification()
      const result = shouldDeliverNotification(
        notification,
        DEFAULT_PREFERENCES,
        'inApp'
      )
      expect(result).toBe(true)
    })

    it('should block delivery when method is disabled', () => {
      const notification = createTestNotification()
      const preferences: NotificationPreferences = {
        ...DEFAULT_PREFERENCES,
        deliveryMethods: {
          ...DEFAULT_PREFERENCES.deliveryMethods,
          email: false
        }
      }

      const result = shouldDeliverNotification(notification, preferences, 'email')
      expect(result).toBe(false)
    })

    it('should block delivery based on priority matrix', () => {
      const notification = createTestNotification(NotificationPriority.INFO)
      const preferences: NotificationPreferences = {
        ...DEFAULT_PREFERENCES,
        priorityMatrix: {
          ...DEFAULT_PREFERENCES.priorityMatrix,
          email: {
            ...DEFAULT_PREFERENCES.priorityMatrix.email,
            [NotificationPriority.INFO]: false
          }
        }
      }

      const result = shouldDeliverNotification(notification, preferences, 'email')
      expect(result).toBe(false)
    })

    it('should allow critical notifications during quiet hours', () => {
      const notification = createTestNotification(NotificationPriority.CRITICAL)
      const now = new Date()
      const quietStart = new Date(now.getTime() - 60 * 60 * 1000) // 1 hour ago
      const quietEnd = new Date(now.getTime() + 60 * 60 * 1000) // 1 hour from now

      const preferences: NotificationPreferences = {
        ...DEFAULT_PREFERENCES,
        quietHours: {
          enabled: true,
          startTime: `${quietStart.getHours().toString().padStart(2, '0')}:00`,
          endTime: `${quietEnd.getHours().toString().padStart(2, '0')}:00`,
          criticalOnly: true
        }
      }

      const result = shouldDeliverNotification(notification, preferences, 'inApp')
      expect(result).toBe(true)
    })

    it('should block non-critical notifications during quiet hours', () => {
      const notification = createTestNotification(NotificationPriority.INFO)
      const now = new Date()
      const quietStart = new Date(now.getTime() - 60 * 60 * 1000)
      const quietEnd = new Date(now.getTime() + 60 * 60 * 1000)

      const preferences: NotificationPreferences = {
        ...DEFAULT_PREFERENCES,
        quietHours: {
          enabled: true,
          startTime: `${quietStart.getHours().toString().padStart(2, '0')}:00`,
          endTime: `${quietEnd.getHours().toString().padStart(2, '0')}:00`,
          criticalOnly: true
        }
      }

      const result = shouldDeliverNotification(notification, preferences, 'inApp')
      expect(result).toBe(false)
    })

    it('should block notifications for disabled event types', () => {
      const notification = createTestNotification()
      const preferences: NotificationPreferences = {
        ...DEFAULT_PREFERENCES,
        eventToggles: {
          ...DEFAULT_PREFERENCES.eventToggles,
          trade_opened: false
        }
      }

      const result = shouldDeliverNotification(
        notification,
        preferences,
        'inApp',
        'trade_opened'
      )
      expect(result).toBe(false)
    })

    it('should allow notifications for enabled event types', () => {
      const notification = createTestNotification()
      const preferences: NotificationPreferences = {
        ...DEFAULT_PREFERENCES,
        eventToggles: {
          ...DEFAULT_PREFERENCES.eventToggles,
          trade_opened: true
        }
      }

      const result = shouldDeliverNotification(
        notification,
        preferences,
        'inApp',
        'trade_opened'
      )
      expect(result).toBe(true)
    })
  })

  describe('calculateNotificationFrequency', () => {
    it('should calculate base frequency from enabled events', () => {
      const result = calculateNotificationFrequency(DEFAULT_PREFERENCES)
      expect(result.estimatedPerHour).toBeGreaterThan(0)
    })

    it('should reduce frequency with grouping enabled', () => {
      const withoutGrouping = calculateNotificationFrequency({
        ...DEFAULT_PREFERENCES,
        grouping: { enabled: false, windowMinutes: 30 }
      })

      const withGrouping = calculateNotificationFrequency({
        ...DEFAULT_PREFERENCES,
        grouping: { enabled: true, windowMinutes: 30 }
      })

      expect(withGrouping.estimatedPerHour).toBeLessThan(
        withoutGrouping.estimatedPerHour
      )
    })

    it('should reduce frequency with digest enabled', () => {
      const withoutDigest = calculateNotificationFrequency({
        ...DEFAULT_PREFERENCES,
        digest: { enabled: false, frequencyMinutes: 30, priorities: [] }
      })

      const withDigest = calculateNotificationFrequency({
        ...DEFAULT_PREFERENCES,
        digest: {
          enabled: true,
          frequencyMinutes: 30,
          priorities: [NotificationPriority.INFO, NotificationPriority.SUCCESS]
        }
      })

      expect(withDigest.estimatedPerHour).toBeLessThan(
        withoutDigest.estimatedPerHour
      )
    })

    it('should categorize frequency levels correctly', () => {
      const lowFrequency = calculateNotificationFrequency({
        ...DEFAULT_PREFERENCES,
        eventToggles: {
          trade_opened: true,
          trade_closed_profit: false,
          trade_closed_loss: false,
          trade_rejected: false,
          system_error: false,
          system_recovered: false,
          agent_started: false,
          agent_stopped: false,
          agent_healthy: false,
          agent_degraded: false,
          agent_failed: false,
          performance_alert: false,
          breaker_triggered: false,
          threshold_warning: false,
          breaker_reset: false
        }
      })

      expect(lowFrequency.level).toBe('low')
    })
  })
})
