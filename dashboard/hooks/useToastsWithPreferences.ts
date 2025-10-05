/**
 * Enhanced toast hook with notification preferences integration
 * Wraps useToasts with preference-aware delivery
 */

'use client'

import { useCallback } from 'react'
import { Notification } from '@/types/notifications'
import { EventType } from '@/types/notificationPreferences'
import { useToasts as useBaseToasts } from './useToasts'
import { useNotificationPreferences } from './useNotificationPreferences'
import { shouldDeliverNotification, deliverNotification } from '@/services/notificationDeliveryService'

export interface AddToastOptions {
  eventType?: EventType
}

/**
 * Hook for managing toast notifications with preferences
 */
export function useToastsWithPreferences() {
  const baseToasts = useBaseToasts()
  const { preferences } = useNotificationPreferences()

  /**
   * Add a toast notification with preference filtering
   */
  const addToast = useCallback(
    (
      notification: Omit<Notification, 'id' | 'read' | 'dismissed'>,
      options?: AddToastOptions
    ) => {
      const toast: Notification = {
        ...notification,
        id: `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        timestamp: notification.timestamp || new Date(),
        read: false,
        dismissed: false
      }

      // Check if should show in-app toast based on preferences
      const shouldShowInApp = shouldDeliverNotification(
        toast,
        preferences,
        'inApp',
        options?.eventType
      )

      // If allowed, show the toast using base hook
      if (shouldShowInApp) {
        baseToasts.showToast(notification)
      }

      // Deliver to other channels (browser push, email, slack, sms)
      deliverNotification(toast, preferences, options?.eventType)

      return toast.id
    },
    [baseToasts, preferences]
  )

  return {
    ...baseToasts,
    addToast
  }
}

// Export backward compatible version
export { useToasts } from './useToasts'
