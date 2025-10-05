/**
 * Notification storage utilities using localStorage
 * Handles persistence, cleanup, and retention policies
 */

import { Notification } from '@/types/notifications'

const STORAGE_KEY = 'notifications_history'
const MAX_NOTIFICATIONS = 500
const RETENTION_DAYS = 30

/**
 * Load notifications from localStorage
 * Automatically cleans up notifications older than 30 days
 */
export function loadNotifications(): Notification[] {
  if (typeof window === 'undefined') {
    return []
  }

  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) {
      return []
    }

    const parsed = JSON.parse(stored) as Notification[]

    // Convert timestamp strings back to Date objects
    const notifications = parsed.map(n => ({
      ...n,
      timestamp: new Date(n.timestamp)
    }))

    // Cleanup old notifications (>30 days)
    const cutoffDate = new Date()
    cutoffDate.setDate(cutoffDate.getDate() - RETENTION_DAYS)

    const cleaned = notifications.filter(n => n.timestamp >= cutoffDate)

    // If we cleaned up any notifications, save the cleaned list
    if (cleaned.length !== notifications.length) {
      saveNotifications(cleaned)
    }

    return cleaned
  } catch (error) {
    console.error('Error loading notifications from localStorage:', error)
    return []
  }
}

/**
 * Save notifications to localStorage
 * Enforces max 500 notifications (FIFO when exceeded)
 */
export function saveNotifications(notifications: Notification[]): void {
  if (typeof window === 'undefined') {
    return
  }

  try {
    // Enforce max limit (FIFO - keep newest)
    const limited = notifications.slice(0, MAX_NOTIFICATIONS)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(limited))
  } catch (error) {
    console.error('Error saving notifications to localStorage:', error)

    // If we hit storage quota, try to save fewer notifications
    if (error instanceof DOMException && error.name === 'QuotaExceededError') {
      try {
        const reduced = notifications.slice(0, Math.floor(MAX_NOTIFICATIONS / 2))
        localStorage.setItem(STORAGE_KEY, JSON.stringify(reduced))
      } catch (retryError) {
        console.error('Failed to save reduced notifications:', retryError)
      }
    }
  }
}

/**
 * Clear all notifications from storage
 */
export function clearNotifications(): void {
  if (typeof window === 'undefined') {
    return
  }

  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch (error) {
    console.error('Error clearing notifications from localStorage:', error)
  }
}

/**
 * Get storage statistics
 */
export function getStorageStats(): {
  count: number
  oldestTimestamp: Date | null
  newestTimestamp: Date | null
  unreadCount: number
} {
  const notifications = loadNotifications()

  if (notifications.length === 0) {
    return {
      count: 0,
      oldestTimestamp: null,
      newestTimestamp: null,
      unreadCount: 0
    }
  }

  return {
    count: notifications.length,
    oldestTimestamp: notifications[notifications.length - 1].timestamp,
    newestTimestamp: notifications[0].timestamp,
    unreadCount: notifications.filter(n => !n.read && !n.dismissed).length
  }
}
