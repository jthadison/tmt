/**
 * Smart grouping logic for notifications
 * Groups similar events within 30-minute window
 * NEVER groups Critical priority notifications
 */

import { Notification, NotificationGroup, NotificationPriority } from '@/types/notifications'

const GROUPING_WINDOW_MS = 30 * 60 * 1000 // 30 minutes

/**
 * Group notifications by similarity and time window
 * @param notifications - Array of notifications to group (should be pre-sorted by timestamp desc)
 * @returns Array of notification groups
 */
export function groupNotifications(notifications: Notification[]): NotificationGroup[] {
  if (notifications.length === 0) {
    return []
  }

  const groups: NotificationGroup[] = []

  for (const notification of notifications) {
    // CRITICAL priority notifications are NEVER grouped
    if (notification.priority === NotificationPriority.CRITICAL) {
      groups.push({
        notifications: [notification],
        count: 1,
        isGrouped: false
      })
      continue
    }

    // No groupKey means this notification should not be grouped
    if (!notification.groupKey) {
      groups.push({
        notifications: [notification],
        count: 1,
        isGrouped: false
      })
      continue
    }

    // Try to find an existing group within the 30-minute window
    let foundGroup = false

    for (const group of groups) {
      const firstInGroup = group.notifications[0]

      // Can't group with different groupKeys
      if (firstInGroup.groupKey !== notification.groupKey) {
        continue
      }

      // Can't group critical notifications
      if (firstInGroup.priority === NotificationPriority.CRITICAL) {
        continue
      }

      // Check if within 30-minute window
      const timeDiff = Math.abs(
        notification.timestamp.getTime() - firstInGroup.timestamp.getTime()
      )

      if (timeDiff <= GROUPING_WINDOW_MS) {
        group.notifications.push(notification)
        group.count = group.notifications.length
        group.isGrouped = true
        foundGroup = true
        break
      }
    }

    // If no existing group found, create a new one
    if (!foundGroup) {
      groups.push({
        notifications: [notification],
        count: 1,
        isGrouped: false
      })
    }
  }

  return groups
}

/**
 * Get the most recent notification from a group
 */
export function getMostRecentNotification(group: NotificationGroup): Notification {
  return group.notifications[0]
}

/**
 * Check if any notification in the group is unread
 */
export function hasUnreadNotifications(group: NotificationGroup): boolean {
  return group.notifications.some(n => !n.read)
}

/**
 * Get count of unread notifications in a group
 */
export function getUnreadCount(group: NotificationGroup): number {
  return group.notifications.filter(n => !n.read).length
}

/**
 * Get formatted group title
 * Examples:
 * - Single notification: "Trade Closed Profitably"
 * - Grouped notifications: "Trade Closed Profitably (3)"
 */
export function getGroupTitle(group: NotificationGroup): string {
  const notification = getMostRecentNotification(group)
  if (group.isGrouped && group.count > 1) {
    return `${notification.title} (${group.count})`
  }
  return notification.title
}
