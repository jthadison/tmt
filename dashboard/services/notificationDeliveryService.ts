/**
 * Notification delivery service
 * Handles multi-channel notification delivery with preference filtering
 */

import type { Notification } from '@/types/notifications'
import { NotificationPriority } from '@/types/notifications'
import {
  NotificationPreferences,
  DeliveryMethod,
  EventType
} from '@/types/notificationPreferences'
import { soundAlertService } from './soundAlertService'

/**
 * Check if current time is within quiet hours
 */
function isInQuietHours(quietHours: NotificationPreferences['quietHours']): boolean {
  if (!quietHours.enabled) return false

  const now = new Date()
  const currentTime = `${now.getHours().toString().padStart(2, '0')}:${now
    .getMinutes()
    .toString()
    .padStart(2, '0')}`
  const { startTime, endTime } = quietHours

  // Handle quiet hours that cross midnight
  if (startTime > endTime) {
    return currentTime >= startTime || currentTime < endTime
  } else {
    return currentTime >= startTime && currentTime < endTime
  }
}

/**
 * Check if notification should be delivered via a specific method
 */
export function shouldDeliverNotification(
  notification: Notification,
  preferences: NotificationPreferences,
  deliveryMethod: DeliveryMethod,
  eventType?: EventType
): boolean {
  // Check if delivery method is enabled
  if (!preferences.deliveryMethods[deliveryMethod]) {
    return false
  }

  // Check priority matrix
  if (!preferences.priorityMatrix[deliveryMethod]?.[notification.priority]) {
    return false
  }

  // Check quiet hours
  if (isInQuietHours(preferences.quietHours)) {
    if (
      notification.priority !== NotificationPriority.CRITICAL &&
      preferences.quietHours.criticalOnly
    ) {
      return false
    }
  }

  // Check event-specific toggle if event type is provided
  if (eventType && !preferences.eventToggles[eventType]) {
    return false
  }

  return true
}

/**
 * Deliver notification via in-app method
 */
function deliverInApp(notification: Notification): void {
  // In-app delivery is handled by the NotificationContext
  // This is just a passthrough
  console.log('In-app notification delivered:', notification)
}

/**
 * Deliver notification via browser push
 */
function deliverBrowserPush(notification: Notification): void {
  if (typeof Notification === 'undefined') {
    console.warn('Browser notifications not supported')
    return
  }

  if (Notification.permission !== 'granted') {
    console.warn('Browser notification permission not granted')
    return
  }

  try {
    new Notification(notification.title, {
      body: notification.message,
      icon: notification.icon || '/favicon.ico',
      badge: '/badge-icon.png',
      tag: notification.id,
      requireInteraction: notification.priority === NotificationPriority.CRITICAL,
      silent: false
    })
  } catch (error) {
    console.error('Error sending browser push notification:', error)
  }
}

/**
 * Deliver notification via email (requires backend)
 */
async function deliverEmail(
  notification: Notification,
  email: string
): Promise<void> {
  try {
    // In production, this would call the backend API
    console.log('Email notification would be sent to:', email, notification)
    // await fetch('/api/notifications/email/send', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ email, notification })
    // })
  } catch (error) {
    console.error('Error sending email notification:', error)
  }
}

/**
 * Deliver notification via Slack (requires backend)
 */
async function deliverSlack(
  notification: Notification,
  webhookUrl: string
): Promise<void> {
  try {
    // In production, this would call the backend API
    console.log('Slack notification would be sent to:', webhookUrl, notification)
    // await fetch('/api/notifications/slack/send', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ webhookUrl, notification })
    // })
  } catch (error) {
    console.error('Error sending Slack notification:', error)
  }
}

/**
 * Deliver notification via SMS (requires backend)
 */
async function deliverSMS(
  notification: Notification,
  phone: string
): Promise<void> {
  try {
    // In production, this would call the backend API
    console.log('SMS notification would be sent to:', phone, notification)
    // await fetch('/api/notifications/sms/send', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ phone, notification })
    // })
  } catch (error) {
    console.error('Error sending SMS notification:', error)
  }
}

/**
 * Deliver notification to all enabled channels
 */
export async function deliverNotification(
  notification: Notification,
  preferences: NotificationPreferences,
  eventType?: EventType
): Promise<void> {
  const deliveryMethods: DeliveryMethod[] = [
    'inApp',
    'browserPush',
    'email',
    'slack',
    'sms'
  ]

  // Play sound if enabled
  if (preferences.sounds.enabled) {
    const soundName = preferences.sounds.perPriority[notification.priority]
    await soundAlertService.playNotificationSound(
      notification.priority,
      soundName,
      preferences.sounds.volume
    )
  }

  // Deliver to each enabled channel
  for (const method of deliveryMethods) {
    if (shouldDeliverNotification(notification, preferences, method, eventType)) {
      switch (method) {
        case 'inApp':
          deliverInApp(notification)
          break

        case 'browserPush':
          deliverBrowserPush(notification)
          break

        case 'email':
          if (preferences.deliveryMethodConfig.email) {
            await deliverEmail(notification, preferences.deliveryMethodConfig.email)
          }
          break

        case 'slack':
          if (preferences.deliveryMethodConfig.slackWebhook) {
            await deliverSlack(
              notification,
              preferences.deliveryMethodConfig.slackWebhook
            )
          }
          break

        case 'sms':
          if (preferences.deliveryMethodConfig.phone) {
            await deliverSMS(notification, preferences.deliveryMethodConfig.phone)
          }
          break
      }
    }
  }
}

/**
 * Calculate estimated notification frequency based on preferences
 */
export function calculateNotificationFrequency(
  preferences: NotificationPreferences
): {
  estimatedPerHour: number
  level: 'low' | 'medium' | 'high'
} {
  // Count enabled event types
  const enabledEvents = Object.values(preferences.eventToggles).filter(
    (enabled) => enabled
  ).length

  // Base frequency assumes 1 event per hour per enabled event type
  let baseFrequency = enabledEvents

  // Adjust for grouping
  if (preferences.grouping.enabled) {
    baseFrequency *= 0.7 // 30% reduction with grouping
  }

  // Adjust for digest
  if (preferences.digest.enabled) {
    baseFrequency *= 0.5 // 50% reduction with digest
  }

  // Adjust for quiet hours
  if (preferences.quietHours.enabled) {
    baseFrequency *= 0.8 // 20% reduction for quiet hours
  }

  const estimatedPerHour = Math.round(baseFrequency)
  const level =
    estimatedPerHour < 3 ? 'low' : estimatedPerHour < 10 ? 'medium' : 'high'

  return { estimatedPerHour, level }
}
