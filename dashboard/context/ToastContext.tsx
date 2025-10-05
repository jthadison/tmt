/**
 * Toast notification context provider
 * Manages toast state and event subscriptions globally
 */

'use client'

import { createContext, useContext, ReactNode } from 'react'
import { useToasts } from '@/hooks/useToasts'
import { useEventSubscription } from '@/hooks/useEventSubscription'
import { ToastContainer } from '@/components/notifications/ToastContainer'
import { Notification } from '@/types/notifications'

interface ToastContextType {
  showToast: (notification: Omit<Notification, 'id' | 'read' | 'dismissed'>) => string
  dismissToast: (id: string) => void
  dismissAll: () => void
  connectionStatus: 'connected' | 'disconnected' | 'connecting'
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

export function ToastProvider({ children }: { children: ReactNode }) {
  const { toasts, showToast, dismissToast, dismissAll } = useToasts()
  const { connectionStatus } = useEventSubscription()

  const handleToastClick = (notification: Notification) => {
    // Click toast to focus it in notification center
    // This will be implemented when integrating with NotificationCenter
    console.log('Toast clicked:', notification.id)
  }

  return (
    <ToastContext.Provider value={{ showToast, dismissToast, dismissAll, connectionStatus }}>
      {children}
      <ToastContainer
        toasts={toasts}
        onDismiss={dismissToast}
        onToastClick={handleToastClick}
      />
    </ToastContext.Provider>
  )
}

export function useToastContext() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToastContext must be used within ToastProvider')
  }
  return context
}
