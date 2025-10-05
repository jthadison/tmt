/**
 * Notification bell icon with badge counter
 * Displays in header with pulsing animation for unread notifications
 */

'use client'

interface NotificationBellIconProps {
  unreadCount: number
  onClick: () => void
  isOpen?: boolean
}

export default function NotificationBellIcon({
  unreadCount,
  onClick,
  isOpen = false
}: NotificationBellIconProps) {
  const hasUnread = unreadCount > 0
  const displayCount = unreadCount > 9 ? '9+' : unreadCount.toString()

  return (
    <button
      onClick={onClick}
      className={`
        relative p-2 rounded transition-colors
        ${isOpen ? 'bg-gray-700' : 'hover:bg-gray-800 dark:hover:bg-gray-700'}
      `}
      aria-label={`Notifications${hasUnread ? ` (${unreadCount} unread)` : ''}`}
    >
      {/* Bell icon with pulsing animation for unread */}
      <svg
        className={`w-5 h-5 ${hasUnread ? 'animate-pulse' : ''}`}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
        />
      </svg>

      {/* Unread badge */}
      {hasUnread && (
        <span
          className="
            absolute -top-1 -right-1
            bg-red-500 text-white
            text-xs font-bold
            rounded-full
            w-5 h-5
            flex items-center justify-center
            border-2 border-gray-900
          "
          aria-label={`${unreadCount} unread notifications`}
        >
          {displayCount}
        </span>
      )}
    </button>
  )
}
