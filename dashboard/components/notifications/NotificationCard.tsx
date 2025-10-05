/**
 * Individual notification card component
 * Displays notification with priority styling, actions, and read/dismiss controls
 */

'use client'

import { Notification, PRIORITY_CONFIG } from '@/types/notifications'
import { formatDistanceToNow } from 'date-fns'
import { useRouter } from 'next/navigation'

interface NotificationCardProps {
  notification: Notification
  onMarkRead: (id: string) => void
  onDismiss: (id: string) => void
  onClick?: () => void
}

export default function NotificationCard({
  notification,
  onMarkRead,
  onDismiss,
  onClick
}: NotificationCardProps) {
  const router = useRouter()
  const config = PRIORITY_CONFIG[notification.priority]

  const handleClick = () => {
    // Mark as read when clicked
    if (!notification.read) {
      onMarkRead(notification.id)
    }

    // Navigate to related URL if provided
    if (notification.relatedUrl) {
      router.push(notification.relatedUrl)
    }

    // Call custom onClick handler
    onClick?.()
  }

  const handleMarkRead = (e: React.MouseEvent) => {
    e.stopPropagation()
    onMarkRead(notification.id)
  }

  const handleDismiss = (e: React.MouseEvent) => {
    e.stopPropagation()
    onDismiss(notification.id)
  }

  const timeAgo = formatDistanceToNow(notification.timestamp, { addSuffix: true })

  return (
    <div
      className={`
        group relative p-4 border-l-4 cursor-pointer transition-all duration-200
        ${config.borderColor} ${config.bgColor}
        ${notification.read ? 'opacity-60' : ''}
        hover:opacity-100 hover:shadow-md
      `}
      onClick={handleClick}
    >
      {/* Unread indicator dot */}
      {!notification.read && (
        <div className="absolute top-2 left-2 w-2 h-2 bg-blue-500 rounded-full" />
      )}

      <div className="flex items-start space-x-3">
        {/* Icon */}
        <div className="flex-shrink-0 text-2xl">
          {notification.icon || config.icon}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Title */}
          <div className={`font-semibold ${notification.read ? '' : 'font-bold'} ${config.textColor}`}>
            {notification.title}
          </div>

          {/* Message */}
          <div className="mt-1 text-sm text-gray-300">
            {notification.message}
          </div>

          {/* Timestamp */}
          <div className="mt-2 text-xs text-gray-500">
            {timeAgo}
          </div>

          {/* Action buttons */}
          {notification.actions && notification.actions.length > 0 && (
            <div className="mt-3 flex space-x-2">
              {notification.actions.map((action, index) => (
                <button
                  key={index}
                  onClick={(e) => {
                    e.stopPropagation()
                    action.action()
                  }}
                  className={`
                    px-3 py-1 text-xs font-medium rounded transition-colors
                    ${action.variant === 'primary'
                      ? `${config.textColor} bg-opacity-20 hover:bg-opacity-30`
                      : 'text-gray-400 hover:text-gray-300'
                    }
                  `}
                >
                  {action.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Context menu (visible on hover) */}
        <div className="flex-shrink-0 flex flex-col space-y-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {!notification.read && (
            <button
              onClick={handleMarkRead}
              className="p-1 text-gray-400 hover:text-blue-400 transition-colors"
              title="Mark as read"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </button>
          )}
          <button
            onClick={handleDismiss}
            className="p-1 text-gray-400 hover:text-red-400 transition-colors"
            title="Dismiss"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}
