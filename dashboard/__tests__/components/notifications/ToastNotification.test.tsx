/**
 * Tests for ToastNotification component
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ToastNotification } from '@/components/notifications/ToastNotification'
import { Notification, NotificationPriority } from '@/types/notifications'

// Mock timers for auto-dismiss testing
jest.useFakeTimers()

describe('ToastNotification', () => {
  const mockOnDismiss = jest.fn()
  const mockOnClick = jest.fn()

  const createNotification = (priority: NotificationPriority): Notification => ({
    id: 'test-toast-1',
    priority,
    title: 'Test Notification',
    message: 'This is a test message',
    timestamp: new Date('2025-01-01T12:00:00Z'),
    read: false,
    dismissed: false,
    icon: '🔔'
  })

  beforeEach(() => {
    jest.clearAllMocks()
    jest.clearAllTimers()
  })

  afterEach(() => {
    jest.runOnlyPendingTimers()
  })

  describe('Rendering', () => {
    it('should render notification with correct title and message', () => {
      const notification = createNotification(NotificationPriority.INFO)
      render(<ToastNotification notification={notification} onDismiss={mockOnDismiss} />)

      expect(screen.getByText('Test Notification')).toBeInTheDocument()
      expect(screen.getByText('This is a test message')).toBeInTheDocument()
    })

    it('should render custom icon when provided', () => {
      const notification = createNotification(NotificationPriority.INFO)
      render(<ToastNotification notification={notification} onDismiss={mockOnDismiss} />)

      expect(screen.getByText('🔔')).toBeInTheDocument()
    })

    it('should render timestamp', () => {
      const notification = createNotification(NotificationPriority.INFO)
      render(<ToastNotification notification={notification} onDismiss={mockOnDismiss} />)

      // Check for time display (format may vary based on locale)
      const timeElement = screen.getByRole('time')
      expect(timeElement).toBeInTheDocument()
    })

    it('should render close button', () => {
      const notification = createNotification(NotificationPriority.INFO)
      render(<ToastNotification notification={notification} onDismiss={mockOnDismiss} />)

      const closeButton = screen.getByLabelText('Dismiss notification')
      expect(closeButton).toBeInTheDocument()
    })

    it('should render action buttons when provided', () => {
      const notification: Notification = {
        ...createNotification(NotificationPriority.WARNING),
        actions: [
          { label: 'View Details', action: jest.fn(), variant: 'primary' },
          { label: 'Dismiss', action: jest.fn(), variant: 'secondary' }
        ]
      }

      render(<ToastNotification notification={notification} onDismiss={mockOnDismiss} />)

      expect(screen.getByText('View Details')).toBeInTheDocument()
      expect(screen.getByText('Dismiss')).toBeInTheDocument()
    })
  })

  describe('Auto-dismiss behavior', () => {
    it('should NOT auto-dismiss critical notifications', () => {
      const notification = createNotification(NotificationPriority.CRITICAL)
      render(<ToastNotification notification={notification} onDismiss={mockOnDismiss} />)

      // Fast-forward past any possible auto-dismiss time
      jest.advanceTimersByTime(30000)

      expect(mockOnDismiss).not.toHaveBeenCalled()
    })

    it('should auto-dismiss info notifications after 3 seconds', () => {
      const notification = createNotification(NotificationPriority.INFO)
      render(<ToastNotification notification={notification} onDismiss={mockOnDismiss} />)

      jest.advanceTimersByTime(3000)

      waitFor(() => {
        expect(mockOnDismiss).toHaveBeenCalledWith('test-toast-1')
      })
    })

    it('should auto-dismiss success notifications after 5 seconds', () => {
      const notification = createNotification(NotificationPriority.SUCCESS)
      render(<ToastNotification notification={notification} onDismiss={mockOnDismiss} />)

      jest.advanceTimersByTime(5000)

      waitFor(() => {
        expect(mockOnDismiss).toHaveBeenCalledWith('test-toast-1')
      })
    })

    it('should auto-dismiss warning notifications after 10 seconds', () => {
      const notification = createNotification(NotificationPriority.WARNING)
      render(<ToastNotification notification={notification} onDismiss={mockOnDismiss} />)

      jest.advanceTimersByTime(10000)

      waitFor(() => {
        expect(mockOnDismiss).toHaveBeenCalledWith('test-toast-1')
      })
    })
  })

  describe('Progress bar', () => {
    it('should NOT show progress bar for critical notifications', () => {
      const notification = createNotification(NotificationPriority.CRITICAL)
      const { container } = render(
        <ToastNotification notification={notification} onDismiss={mockOnDismiss} />
      )

      const progressBar = container.querySelector('.progress-bar')
      expect(progressBar).not.toBeInTheDocument()
    })

    it('should show progress bar for auto-dismissible notifications', () => {
      const notification = createNotification(NotificationPriority.INFO)
      const { container } = render(
        <ToastNotification notification={notification} onDismiss={mockOnDismiss} />
      )

      const progressBar = container.querySelector('.progress-bar')
      expect(progressBar).toBeInTheDocument()
    })
  })

  describe('User interactions', () => {
    it('should call onDismiss when close button clicked', () => {
      const notification = createNotification(NotificationPriority.INFO)
      render(<ToastNotification notification={notification} onDismiss={mockOnDismiss} />)

      const closeButton = screen.getByLabelText('Dismiss notification')
      fireEvent.click(closeButton)

      waitFor(() => {
        expect(mockOnDismiss).toHaveBeenCalledWith('test-toast-1')
      })
    })

    it('should call onClick when toast is clicked', () => {
      const notification = createNotification(NotificationPriority.INFO)
      render(
        <ToastNotification
          notification={notification}
          onDismiss={mockOnDismiss}
          onClick={mockOnClick}
        />
      )

      const toast = screen.getByRole('alert')
      fireEvent.click(toast)

      expect(mockOnClick).toHaveBeenCalledWith(notification)
    })

    it('should call action callback when action button clicked', () => {
      const mockAction = jest.fn()
      const notification: Notification = {
        ...createNotification(NotificationPriority.WARNING),
        actions: [{ label: 'View Details', action: mockAction, variant: 'primary' }]
      }

      render(<ToastNotification notification={notification} onDismiss={mockOnDismiss} />)

      const actionButton = screen.getByText('View Details')
      fireEvent.click(actionButton)

      expect(mockAction).toHaveBeenCalled()
    })

    it('should not propagate click to toast when action button clicked', () => {
      const mockAction = jest.fn()
      const notification: Notification = {
        ...createNotification(NotificationPriority.WARNING),
        actions: [{ label: 'View Details', action: mockAction, variant: 'primary' }]
      }

      render(
        <ToastNotification
          notification={notification}
          onDismiss={mockOnDismiss}
          onClick={mockOnClick}
        />
      )

      const actionButton = screen.getByText('View Details')
      fireEvent.click(actionButton)

      expect(mockAction).toHaveBeenCalled()
      expect(mockOnClick).not.toHaveBeenCalled()
    })
  })

  describe('Accessibility', () => {
    it('should have correct ARIA role', () => {
      const notification = createNotification(NotificationPriority.INFO)
      render(<ToastNotification notification={notification} onDismiss={mockOnDismiss} />)

      expect(screen.getByRole('alert')).toBeInTheDocument()
    })

    it('should use assertive for critical notifications', () => {
      const notification = createNotification(NotificationPriority.CRITICAL)
      render(<ToastNotification notification={notification} onDismiss={mockOnDismiss} />)

      const alert = screen.getByRole('alert')
      expect(alert).toHaveAttribute('aria-live', 'assertive')
    })

    it('should use polite for non-critical notifications', () => {
      const notification = createNotification(NotificationPriority.INFO)
      render(<ToastNotification notification={notification} onDismiss={mockOnDismiss} />)

      const alert = screen.getByRole('alert')
      expect(alert).toHaveAttribute('aria-live', 'polite')
    })
  })
})
