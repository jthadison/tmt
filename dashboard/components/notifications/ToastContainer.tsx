/**
 * Toast container component that manages multiple toast notifications
 * Uses portal rendering and enforces max 3 visible toasts (FIFO)
 */

'use client'

import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { Notification } from '@/types/notifications'
import { ToastNotification } from './ToastNotification'

interface ToastContainerProps {
  toasts: Notification[]
  onDismiss: (id: string) => void
  onToastClick?: (notification: Notification) => void
}

export function ToastContainer({ toasts, onDismiss, onToastClick }: ToastContainerProps) {
  const [mounted, setMounted] = useState(false)

  // Ensure we're mounted before rendering portal (prevents SSR issues)
  useEffect(() => {
    setMounted(true)
    return () => setMounted(false)
  }, [])

  // Only show the 3 most recent toasts (FIFO)
  const visibleToasts = toasts.slice(0, 3)

  if (!mounted) {
    return null
  }

  return createPortal(
    <div
      className="fixed top-4 right-4 z-50 flex flex-col gap-3 pointer-events-none"
      role="region"
      aria-label="Toast notifications"
      aria-live="polite"
    >
      {visibleToasts.map((toast, index) => (
        <div
          key={toast.id}
          className="pointer-events-auto"
          style={{
            animation: `slideInFromRight 0.3s ease-out`,
            animationDelay: `${index * 50}ms`,
            animationFillMode: 'backwards'
          }}
        >
          <ToastNotification
            notification={toast}
            onDismiss={onDismiss}
            onClick={onToastClick}
          />
        </div>
      ))}

      {/* Global styles for animations */}
      <style jsx global>{`
        @keyframes slideInFromRight {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
      `}</style>
    </div>,
    document.body
  )
}
