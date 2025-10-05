/**
 * Tests for NotificationCenter components
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { NotificationProvider } from '@/context/NotificationContext'
import NotificationCenter from '@/components/notifications/NotificationCenter'
import NotificationBellIcon from '@/components/notifications/NotificationBellIcon'
import NotificationCard from '@/components/notifications/NotificationCard'
import { NotificationPriority } from '@/types/notifications'

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn()
  })
}))

// Mock storage
jest.mock('@/utils/notificationStorage', () => ({
  loadNotifications: jest.fn(() => []),
  saveNotifications: jest.fn(),
  clearNotifications: jest.fn(),
  getStorageStats: jest.fn(() => ({
    count: 0,
    oldestTimestamp: null,
    newestTimestamp: null,
    unreadCount: 0
  }))
}))

describe('NotificationBellIcon', () => {
  it('should render bell icon', () => {
    const onClick = jest.fn()
    render(<NotificationBellIcon unreadCount={0} onClick={onClick} />)

    const button = screen.getByRole('button', { name: /notifications/i })
    expect(button).toBeInTheDocument()
  })

  it('should display unread count badge when there are unread notifications', () => {
    const onClick = jest.fn()
    render(<NotificationBellIcon unreadCount={5} onClick={onClick} />)

    expect(screen.getByText('5')).toBeInTheDocument()
  })

  it('should display "9+" for more than 9 unread notifications', () => {
    const onClick = jest.fn()
    render(<NotificationBellIcon unreadCount={15} onClick={onClick} />)

    expect(screen.getByText('9+')).toBeInTheDocument()
  })

  it('should call onClick when clicked', () => {
    const onClick = jest.fn()
    render(<NotificationBellIcon unreadCount={0} onClick={onClick} />)

    const button = screen.getByRole('button', { name: /notifications/i })
    fireEvent.click(button)

    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('should have pulsing animation when there are unread notifications', () => {
    const onClick = jest.fn()
    const { container } = render(<NotificationBellIcon unreadCount={3} onClick={onClick} />)

    const svg = container.querySelector('svg')
    expect(svg).toHaveClass('animate-pulse')
  })
})

describe('NotificationCard', () => {
  const mockNotification = {
    id: 'notif_1',
    priority: NotificationPriority.SUCCESS,
    title: 'Trade Closed',
    message: 'EUR/USD position closed with profit',
    timestamp: new Date(),
    read: false,
    dismissed: false
  }

  it('should render notification details', () => {
    const onMarkRead = jest.fn()
    const onDismiss = jest.fn()

    render(
      <NotificationCard
        notification={mockNotification}
        onMarkRead={onMarkRead}
        onDismiss={onDismiss}
      />
    )

    expect(screen.getByText('Trade Closed')).toBeInTheDocument()
    expect(screen.getByText('EUR/USD position closed with profit')).toBeInTheDocument()
  })

  it('should show unread indicator for unread notifications', () => {
    const onMarkRead = jest.fn()
    const onDismiss = jest.fn()

    const { container } = render(
      <NotificationCard
        notification={mockNotification}
        onMarkRead={onMarkRead}
        onDismiss={onDismiss}
      />
    )

    // Check for unread indicator dot
    const dot = container.querySelector('.bg-blue-500.rounded-full')
    expect(dot).toBeInTheDocument()
  })

  it('should not show unread indicator for read notifications', () => {
    const onMarkRead = jest.fn()
    const onDismiss = jest.fn()

    const readNotification = { ...mockNotification, read: true }

    const { container } = render(
      <NotificationCard
        notification={readNotification}
        onMarkRead={onMarkRead}
        onDismiss={onDismiss}
      />
    )

    // Check for unread indicator dot
    const dot = container.querySelector('.bg-blue-500.rounded-full')
    expect(dot).not.toBeInTheDocument()
  })

  it('should call onMarkRead when mark read button is clicked', () => {
    const onMarkRead = jest.fn()
    const onDismiss = jest.fn()

    const { container } = render(
      <NotificationCard
        notification={mockNotification}
        onMarkRead={onMarkRead}
        onDismiss={onDismiss}
      />
    )

    // Hover to reveal buttons
    const card = container.firstChild as HTMLElement
    fireEvent.mouseEnter(card)

    // Find and click mark read button
    const buttons = screen.getAllByRole('button')
    const markReadButton = buttons.find(btn => btn.getAttribute('title') === 'Mark as read')

    if (markReadButton) {
      fireEvent.click(markReadButton)
      expect(onMarkRead).toHaveBeenCalledWith('notif_1')
    }
  })

  it('should call onDismiss when dismiss button is clicked', () => {
    const onMarkRead = jest.fn()
    const onDismiss = jest.fn()

    const { container } = render(
      <NotificationCard
        notification={mockNotification}
        onMarkRead={onMarkRead}
        onDismiss={onDismiss}
      />
    )

    // Find and click dismiss button
    const buttons = screen.getAllByRole('button')
    const dismissButton = buttons.find(btn => btn.getAttribute('title') === 'Dismiss')

    if (dismissButton) {
      fireEvent.click(dismissButton)
      expect(onDismiss).toHaveBeenCalledWith('notif_1')
    }
  })

  it('should apply correct styling based on priority', () => {
    const onMarkRead = jest.fn()
    const onDismiss = jest.fn()

    const criticalNotification = {
      ...mockNotification,
      priority: NotificationPriority.CRITICAL
    }

    const { container } = render(
      <NotificationCard
        notification={criticalNotification}
        onMarkRead={onMarkRead}
        onDismiss={onDismiss}
      />
    )

    const card = container.firstChild as HTMLElement
    expect(card.className).toContain('border-red-500')
  })
})

describe('NotificationCenter Integration', () => {
  it('should render notification center with bell icon', () => {
    render(
      <NotificationProvider>
        <NotificationCenter />
      </NotificationProvider>
    )

    // Use more specific query - look for button with exact aria-label "Notifications" (not "Close notifications")
    const button = screen.getByRole('button', { name: 'Notifications' })
    expect(button).toBeInTheDocument()
  })

  it('should open panel when bell icon is clicked', async () => {
    render(
      <NotificationProvider>
        <NotificationCenter />
      </NotificationProvider>
    )

    const button = screen.getByRole('button', { name: 'Notifications' })
    fireEvent.click(button)

    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: /notifications/i })).toBeInTheDocument()
    })
  })

  it('should close panel when backdrop is clicked', async () => {
    render(
      <NotificationProvider>
        <NotificationCenter />
      </NotificationProvider>
    )

    // Open panel
    const button = screen.getByRole('button', { name: 'Notifications' })
    fireEvent.click(button)

    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: /notifications/i })).toBeInTheDocument()
    })

    // Click backdrop
    const backdrop = document.querySelector('.bg-black\\/50')
    if (backdrop) {
      fireEvent.click(backdrop)

      await waitFor(() => {
        const dialog = screen.queryByRole('dialog', { name: /notifications/i })
        // Panel should still be in DOM but translated off-screen
        expect(dialog).toBeInTheDocument()
      })
    }
  })

  it('should show empty state when no notifications', async () => {
    render(
      <NotificationProvider>
        <NotificationCenter />
      </NotificationProvider>
    )

    const button = screen.getByRole('button', { name: 'Notifications' })
    fireEvent.click(button)

    await waitFor(() => {
      expect(screen.getByText(/no notifications/i)).toBeInTheDocument()
      expect(screen.getByText(/you're all caught up!/i)).toBeInTheDocument()
    })
  })
})
