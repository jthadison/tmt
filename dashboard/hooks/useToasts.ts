/**
 * Custom hook for managing toast notifications
 * Handles auto-dismiss logic and max 3 toasts enforcement (FIFO)
 */

'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { Notification, NotificationPriority } from '@/types/notifications'
import { useNotifications } from './useNotifications'

const MAX_TOASTS = 3

// Auto-dismiss times based on priority (in milliseconds)
const AUTO_DISMISS_MS: Record<NotificationPriority, number | null> = {
  [NotificationPriority.CRITICAL]: null, // Manual dismiss only
  [NotificationPriority.WARNING]: 10000, // 10 seconds
  [NotificationPriority.SUCCESS]: 5000,  // 5 seconds
  [NotificationPriority.INFO]: 3000      // 3 seconds
}

export function useToasts() {
  const [toasts, setToasts] = useState<Notification[]>([])
  const { addNotification } = useNotifications()
  const timersRef = useRef<Map<string, NodeJS.Timeout>>(new Map())

  // Cleanup timers on unmount
  useEffect(() => {
    const timers = timersRef.current
    return () => {
      timers.forEach(timer => clearTimeout(timer))
      timers.clear()
    }
  }, [])

  /**
   * Dismiss a specific toast
   */
  const dismissToast = useCallback((id: string) => {
    // Clear auto-dismiss timer if exists
    const timer = timersRef.current.get(id)
    if (timer) {
      clearTimeout(timer)
      timersRef.current.delete(id)
    }

    // Remove from display
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  /**
   * Show a new toast notification
   * Also adds to notification center (Story 4.1)
   */
  const showToast = useCallback((notification: Omit<Notification, 'id' | 'read' | 'dismissed'>) => {
    // Create unique ID
    const id = `toast_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

    const toast: Notification = {
      ...notification,
      id,
      timestamp: notification.timestamp || new Date(),
      read: false,
      dismissed: false
    }

    // Add to notification center (persistent)
    addNotification(notification)

    // Add to toast display (temporary)
    setToasts(prev => {
      const updated = [toast, ...prev]
      // Enforce max 3 toasts (FIFO - oldest removed)
      return updated.slice(0, MAX_TOASTS)
    })

    // Setup auto-dismiss timer if applicable
    const dismissTime = AUTO_DISMISS_MS[notification.priority]
    if (dismissTime !== null) {
      const timer = setTimeout(() => {
        dismissToast(id)
      }, dismissTime)
      timersRef.current.set(id, timer)
    }

    return id
  }, [addNotification, dismissToast])

  /**
   * Dismiss all toasts
   */
  const dismissAll = useCallback(() => {
    // Clear all timers
    timersRef.current.forEach(timer => clearTimeout(timer))
    timersRef.current.clear()

    // Clear all toasts
    setToasts([])
  }, [])

  return {
    toasts,
    showToast,
    dismissToast,
    dismissAll
  }
}
