/**
 * Main NotificationCenter component
 * Wrapper that manages bell icon and panel state
 */

'use client'

import { useState } from 'react'
import { useNotifications } from '@/context/NotificationContext'
import NotificationBellIcon from './NotificationBellIcon'
import NotificationPanel from './NotificationPanel'

export default function NotificationCenter() {
  const [isOpen, setIsOpen] = useState(false)
  const { unreadCount } = useNotifications()

  const handleToggle = () => {
    setIsOpen(!isOpen)
  }

  const handleClose = () => {
    setIsOpen(false)
  }

  return (
    <>
      <NotificationBellIcon
        unreadCount={unreadCount}
        onClick={handleToggle}
        isOpen={isOpen}
      />
      <NotificationPanel
        isOpen={isOpen}
        onClose={handleClose}
      />
    </>
  )
}
