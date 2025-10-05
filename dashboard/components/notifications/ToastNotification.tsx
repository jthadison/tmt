/**
 * Toast notification component with auto-dismiss and progress bar
 * Displays brief alerts that automatically disappear based on priority
 */

'use client'

import { useEffect, useState, useCallback } from 'react'
import { Notification, NotificationPriority, PRIORITY_CONFIG } from '@/types/notifications'
import { X } from 'lucide-react'

interface ToastNotificationProps {
  notification: Notification
  onDismiss: (id: string) => void
  onClick?: (notification: Notification) => void
}

// Auto-dismiss times based on priority (in milliseconds)
const AUTO_DISMISS_MS: Record<NotificationPriority, number | null> = {
  [NotificationPriority.CRITICAL]: null, // Manual dismiss only
  [NotificationPriority.WARNING]: 10000, // 10 seconds
  [NotificationPriority.SUCCESS]: 5000,  // 5 seconds
  [NotificationPriority.INFO]: 3000      // 3 seconds
}

export function ToastNotification({ notification, onDismiss, onClick }: ToastNotificationProps) {
  const [progress, setProgress] = useState(100)
  const [isExiting, setIsExiting] = useState(false)

  const config = PRIORITY_CONFIG[notification.priority]
  const dismissTime = AUTO_DISMISS_MS[notification.priority]

  const handleDismiss = useCallback(() => {
    setIsExiting(true)
    // Wait for exit animation before removing
    setTimeout(() => {
      onDismiss(notification.id)
    }, 300) // Match animation duration
  }, [notification.id, onDismiss])

  // Handle auto-dismiss countdown
  useEffect(() => {
    if (!dismissTime) return // Critical notifications don't auto-dismiss

    const interval = setInterval(() => {
      setProgress(prev => {
        const decrement = 100 / (dismissTime / 100)
        const newProgress = prev - decrement
        return newProgress > 0 ? newProgress : 0
      })
    }, 100)

    const timeout = setTimeout(() => {
      handleDismiss()
    }, dismissTime)

    return () => {
      clearInterval(interval)
      clearTimeout(timeout)
    }
  }, [dismissTime, handleDismiss])

  const handleClick = useCallback(() => {
    if (onClick) {
      onClick(notification)
    }
  }, [notification, onClick])

  // Handle Escape key for dismissal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        handleDismiss()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleDismiss])

  return (
    <div
      role="alert"
      aria-live={notification.priority === NotificationPriority.CRITICAL ? 'assertive' : 'polite'}
      aria-atomic="true"
      className={`
        relative overflow-hidden
        bg-gray-800 rounded-lg shadow-lg
        border-l-4 ${config.borderColor}
        w-96 max-w-full
        cursor-pointer
        transition-all duration-300 ease-in-out
        ${isExiting ? 'translate-x-full opacity-0' : 'translate-x-0 opacity-100'}
        hover:shadow-xl hover:scale-[1.02]
      `}
      onClick={handleClick}
    >
      {/* Main content */}
      <div className="p-4 pr-12">
        {/* Header with icon and title */}
        <div className="flex items-start gap-3 mb-2">
          <span className="text-2xl flex-shrink-0" aria-hidden="true">
            {notification.icon || config.icon}
          </span>
          <div className="flex-1 min-w-0">
            <h4 className={`font-semibold ${config.textColor} text-sm`}>
              {notification.title}
            </h4>
          </div>
        </div>

        {/* Message */}
        <p className="text-gray-300 text-sm ml-11 line-clamp-2">
          {notification.message}
        </p>

        {/* Timestamp */}
        <time className="text-gray-500 text-xs ml-11 mt-1 block">
          {notification.timestamp.toLocaleTimeString()}
        </time>

        {/* Actions */}
        {notification.actions && notification.actions.length > 0 && (
          <div className="flex gap-2 ml-11 mt-3">
            {notification.actions.map((action, idx) => (
              <button
                key={idx}
                onClick={(e) => {
                  e.stopPropagation()
                  action.action()
                }}
                className={`
                  px-3 py-1 rounded text-xs font-medium
                  transition-colors
                  ${action.variant === 'primary'
                    ? `${config.bgColor} ${config.textColor} hover:opacity-80`
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }
                `}
                aria-label={action.label}
              >
                {action.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Close button */}
      <button
        onClick={(e) => {
          e.stopPropagation()
          handleDismiss()
        }}
        className="
          absolute top-3 right-3
          p-1 rounded-full
          text-gray-400 hover:text-gray-200
          hover:bg-gray-700
          transition-colors
          focus:outline-none focus:ring-2 focus:ring-gray-500
        "
        aria-label="Dismiss notification"
      >
        <X size={16} />
      </button>

      {/* Progress bar */}
      {dismissTime && (
        <div
          className="absolute bottom-0 left-0 right-0 h-1 bg-gray-700"
          aria-hidden="true"
        >
          <div
            className={`h-full ${config.bgColor} transition-all duration-100 ease-linear`}
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  )
}
