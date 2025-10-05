/**
 * Custom hook for managing notifications
 * Handles state, localStorage persistence, and grouping logic
 */

'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { Notification, NotificationGroup, DateGroupedNotifications } from '@/types/notifications'
import { loadNotifications, saveNotifications } from '@/utils/notificationStorage'
import { groupNotifications } from '@/utils/notificationGrouping'
import * as dateFns from 'date-fns'

const { startOfDay, subDays, isAfter, isBefore, isWithinInterval } = dateFns

export function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [isLoaded, setIsLoaded] = useState(false)

  // Load from localStorage on mount
  useEffect(() => {
    const loaded = loadNotifications()
    setNotifications(loaded)
    setIsLoaded(true)
  }, [])

  // Save to localStorage whenever notifications change (but only after initial load)
  useEffect(() => {
    if (isLoaded) {
      saveNotifications(notifications)
    }
  }, [notifications, isLoaded])

  /**
   * Add a new notification
   */
  const addNotification = useCallback((notification: Omit<Notification, 'id' | 'read' | 'dismissed'>) => {
    const newNotification: Notification = {
      ...notification,
      id: `notif_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: notification.timestamp || new Date(),
      read: false,
      dismissed: false
    }

    setNotifications(prev => [newNotification, ...prev])
  }, [])

  /**
   * Mark a specific notification as read
   */
  const markRead = useCallback((id: string) => {
    setNotifications(prev =>
      prev.map(n => n.id === id ? { ...n, read: true } : n)
    )
  }, [])

  /**
   * Mark all notifications as read
   */
  const markAllRead = useCallback(() => {
    setNotifications(prev =>
      prev.map(n => ({ ...n, read: true }))
    )
  }, [])

  /**
   * Dismiss a specific notification
   */
  const dismiss = useCallback((id: string) => {
    setNotifications(prev =>
      prev.map(n => n.id === id ? { ...n, dismissed: true } : n)
    )
  }, [])

  /**
   * Clear (dismiss) all notifications
   */
  const clearAll = useCallback(() => {
    setNotifications(prev =>
      prev.map(n => ({ ...n, dismissed: true }))
    )
  }, [])

  /**
   * Mark all notifications in a group as read
   */
  const markGroupRead = useCallback((group: NotificationGroup) => {
    const ids = group.notifications.map(n => n.id)
    setNotifications(prev =>
      prev.map(n => ids.includes(n.id) ? { ...n, read: true } : n)
    )
  }, [])

  /**
   * Get only visible (non-dismissed) notifications
   */
  const visibleNotifications = useMemo(
    () => notifications.filter(n => !n.dismissed),
    [notifications]
  )

  /**
   * Calculate unread count
   */
  const unreadCount = useMemo(
    () => visibleNotifications.filter(n => !n.read).length,
    [visibleNotifications]
  )

  /**
   * Group notifications by date sections
   */
  const groupedByDate = useMemo((): DateGroupedNotifications => {
    const now = new Date()
    const todayStart = startOfDay(now)
    const yesterdayStart = startOfDay(subDays(now, 1))
    const thisWeekStart = startOfDay(subDays(now, 7))

    const today = visibleNotifications.filter(n =>
      isAfter(n.timestamp, todayStart) || n.timestamp.getTime() === todayStart.getTime()
    )

    const yesterday = visibleNotifications.filter(n =>
      isWithinInterval(n.timestamp, {
        start: yesterdayStart,
        end: todayStart
      })
    )

    const thisWeek = visibleNotifications.filter(n =>
      isWithinInterval(n.timestamp, {
        start: thisWeekStart,
        end: yesterdayStart
      })
    )

    const older = visibleNotifications.filter(n =>
      isBefore(n.timestamp, thisWeekStart)
    )

    // Apply smart grouping to each date section
    return {
      today: groupNotifications(today),
      yesterday: groupNotifications(yesterday),
      thisWeek: groupNotifications(thisWeek),
      older: groupNotifications(older)
    }
  }, [visibleNotifications])

  /**
   * Check if there are any notifications
   */
  const hasNotifications = useMemo(
    () => visibleNotifications.length > 0,
    [visibleNotifications]
  )

  return {
    // State
    notifications: visibleNotifications,
    groupedByDate,
    unreadCount,
    hasNotifications,
    isLoaded,

    // Actions
    addNotification,
    markRead,
    markAllRead,
    markGroupRead,
    dismiss,
    clearAll
  }
}
