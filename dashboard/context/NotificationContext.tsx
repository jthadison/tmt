/**
 * Notification context provider
 * Provides notification state and actions throughout the app
 */

'use client'

import { createContext, useContext, ReactNode } from 'react'
import { Notification, NotificationGroup, DateGroupedNotifications } from '@/types/notifications'
import { useNotifications as useNotificationsHook } from '@/hooks/useNotifications'

interface NotificationContextValue {
  notifications: Notification[]
  groupedByDate: DateGroupedNotifications
  unreadCount: number
  hasNotifications: boolean
  isLoaded: boolean
  addNotification: (notification: Omit<Notification, 'id' | 'read' | 'dismissed'>) => void
  markRead: (id: string) => void
  markAllRead: () => void
  markGroupRead: (group: NotificationGroup) => void
  dismiss: (id: string) => void
  clearAll: () => void
}

const NotificationContext = createContext<NotificationContextValue | undefined>(undefined)

export function NotificationProvider({ children }: { children: ReactNode }) {
  const notificationState = useNotificationsHook()

  return (
    <NotificationContext.Provider value={notificationState}>
      {children}
    </NotificationContext.Provider>
  )
}

export function useNotifications() {
  const context = useContext(NotificationContext)
  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider')
  }
  return context
}
