/**
 * Grouped notification component
 * Shows multiple similar notifications with expand/collapse functionality
 */

'use client'

import { useState } from 'react'
import { NotificationGroup } from '@/types/notifications'
import {
  getMostRecentNotification,
  hasUnreadNotifications,
  getUnreadCount,
  getGroupTitle
} from '@/utils/notificationGrouping'
import NotificationCard from './NotificationCard'

interface GroupedNotificationProps {
  group: NotificationGroup
  onMarkRead: (id: string) => void
  onDismiss: (id: string) => void
  onMarkGroupRead: (group: NotificationGroup) => void
}

export default function GroupedNotification({
  group,
  onMarkRead,
  onDismiss,
  onMarkGroupRead
}: GroupedNotificationProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const mostRecent = getMostRecentNotification(group)
  const hasUnread = hasUnreadNotifications(group)
  const unreadCount = getUnreadCount(group)

  // If not grouped, just render a single card
  if (!group.isGrouped) {
    return (
      <NotificationCard
        notification={mostRecent}
        onMarkRead={onMarkRead}
        onDismiss={onDismiss}
      />
    )
  }

  const handleToggleExpand = () => {
    setIsExpanded(!isExpanded)
  }

  const handleMarkGroupRead = (e: React.MouseEvent) => {
    e.stopPropagation()
    onMarkGroupRead(group)
  }

  return (
    <div className="border-b border-gray-700 last:border-b-0">
      {/* Group header - shows most recent notification */}
      <div
        className="cursor-pointer hover:bg-gray-800/50 transition-colors"
        onClick={handleToggleExpand}
      >
        <NotificationCard
          notification={mostRecent}
          onMarkRead={onMarkRead}
          onDismiss={onDismiss}
        />

        {/* Group indicator */}
        <div className="px-4 pb-3 flex items-center justify-between">
          <div className="flex items-center space-x-2 text-sm text-gray-400">
            <span className="font-medium">{group.count} similar notifications</span>
            {unreadCount > 0 && (
              <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded-full text-xs">
                {unreadCount} unread
              </span>
            )}
          </div>

          <div className="flex items-center space-x-2">
            {hasUnread && (
              <button
                onClick={handleMarkGroupRead}
                className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
              >
                Mark all read
              </button>
            )}
            <button
              className="text-gray-400 hover:text-gray-300 transition-colors"
              aria-label={isExpanded ? 'Collapse' : 'Expand'}
            >
              <svg
                className={`w-5 h-5 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Expanded notifications */}
      {isExpanded && (
        <div className="bg-gray-800/30 border-t border-gray-700">
          <div className="pl-8">
            {group.notifications.slice(1).map((notification) => (
              <div key={notification.id} className="border-t border-gray-700/50">
                <NotificationCard
                  notification={notification}
                  onMarkRead={onMarkRead}
                  onDismiss={onDismiss}
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
