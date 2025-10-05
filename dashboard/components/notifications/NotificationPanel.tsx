/**
 * Notification panel slide-out component
 * Displays notifications grouped by date with actions
 */

'use client'

import { useEffect } from 'react'
import { NotificationGroup } from '@/types/notifications'
import { useNotifications } from '@/context/NotificationContext'
import GroupedNotification from './GroupedNotification'

interface NotificationPanelProps {
  isOpen: boolean
  onClose: () => void
}

interface NotificationSectionProps {
  title: string
  groups: NotificationGroup[]
  onMarkRead: (id: string) => void
  onDismiss: (id: string) => void
  onMarkGroupRead: (group: NotificationGroup) => void
}

function NotificationSection({
  title,
  groups,
  onMarkRead,
  onDismiss,
  onMarkGroupRead
}: NotificationSectionProps) {
  if (groups.length === 0) {
    return null
  }

  return (
    <div className="mb-4">
      <div className="sticky top-0 bg-gray-900 px-4 py-2 border-b border-gray-700 z-10">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
          {title}
        </h3>
      </div>
      <div>
        {groups.map((group, index) => (
          <GroupedNotification
            key={group.notifications[0].id}
            group={group}
            onMarkRead={onMarkRead}
            onDismiss={onDismiss}
            onMarkGroupRead={onMarkGroupRead}
          />
        ))}
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-64 text-gray-500">
      <svg className="w-16 h-16 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
        />
      </svg>
      <p className="text-lg font-medium">No notifications</p>
      <p className="text-sm mt-1">You're all caught up!</p>
    </div>
  )
}

export default function NotificationPanel({ isOpen, onClose }: NotificationPanelProps) {
  const {
    groupedByDate,
    unreadCount,
    hasNotifications,
    markRead,
    markAllRead,
    markGroupRead,
    dismiss,
    clearAll
  } = useNotifications()

  // Close panel on Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  // Prevent body scroll when panel is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = 'unset'
    }

    return () => {
      document.body.style.overflow = 'unset'
    }
  }, [isOpen])

  const handleMarkAllRead = () => {
    markAllRead()
  }

  const handleClearAll = () => {
    if (confirm('Are you sure you want to dismiss all notifications?')) {
      clearAll()
    }
  }

  return (
    <>
      {/* Backdrop overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Slide-out panel */}
      <div
        className={`
          fixed right-0 top-0 h-full w-[400px]
          bg-gray-900 shadow-2xl z-50
          transform transition-transform duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : 'translate-x-full'}
          flex flex-col
        `}
        role="dialog"
        aria-modal="true"
        aria-label="Notifications"
      >
        {/* Header */}
        <div className="flex-shrink-0 flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-xl font-bold text-white">Notifications</h2>
          <div className="flex items-center space-x-2">
            <button
              onClick={handleMarkAllRead}
              disabled={unreadCount === 0}
              className="
                text-sm text-blue-400 hover:text-blue-300
                disabled:opacity-50 disabled:cursor-not-allowed
                transition-colors
              "
              title={unreadCount === 0 ? 'No unread notifications' : 'Mark all as read'}
            >
              Mark All Read
            </button>
            <span className="text-gray-600">|</span>
            <button
              onClick={handleClearAll}
              disabled={!hasNotifications}
              className="
                text-sm text-gray-400 hover:text-gray-300
                disabled:opacity-50 disabled:cursor-not-allowed
                transition-colors
              "
              title={!hasNotifications ? 'No notifications to clear' : 'Clear all notifications'}
            >
              Clear All
            </button>
            <button
              onClick={onClose}
              className="ml-2 p-1 text-gray-400 hover:text-white transition-colors"
              aria-label="Close"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Notification list */}
        <div className="flex-1 overflow-y-auto">
          {!hasNotifications ? (
            <EmptyState />
          ) : (
            <div className="pb-4">
              <NotificationSection
                title="Today"
                groups={groupedByDate.today}
                onMarkRead={markRead}
                onDismiss={dismiss}
                onMarkGroupRead={markGroupRead}
              />
              <NotificationSection
                title="Yesterday"
                groups={groupedByDate.yesterday}
                onMarkRead={markRead}
                onDismiss={dismiss}
                onMarkGroupRead={markGroupRead}
              />
              <NotificationSection
                title="This Week"
                groups={groupedByDate.thisWeek}
                onMarkRead={markRead}
                onDismiss={dismiss}
                onMarkGroupRead={markGroupRead}
              />
              <NotificationSection
                title="Older"
                groups={groupedByDate.older}
                onMarkRead={markRead}
                onDismiss={dismiss}
                onMarkGroupRead={markGroupRead}
              />
            </div>
          )}
        </div>
      </div>
    </>
  )
}
