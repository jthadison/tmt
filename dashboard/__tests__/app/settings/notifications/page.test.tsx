/**
 * Tests for notification preferences page
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import NotificationPreferencesPage from '@/app/settings/notifications/page'
import { NotificationProvider } from '@/context/NotificationContext'

// Mock hooks
jest.mock('@/hooks/useNotificationPreferences')
jest.mock('@/hooks/useToasts')

const mockUpdateDeliveryMethod = jest.fn()
const mockUpdateDeliveryMethodConfig = jest.fn()
const mockUpdatePriorityMatrix = jest.fn()
const mockUpdateEventToggle = jest.fn()
const mockResetDefaults = jest.fn()
const mockExportPreferences = jest.fn()
const mockImportPreferences = jest.fn()
const mockValidateConfig = jest.fn()

const mockPreferences = {
  deliveryMethods: {
    inApp: true,
    browserPush: false,
    email: false,
    slack: false,
    sms: false
  },
  deliveryMethodConfig: {},
  priorityMatrix: {
    inApp: {
      critical: true,
      warning: true,
      success: true,
      info: true
    },
    browserPush: {
      critical: true,
      warning: true,
      success: false,
      info: false
    },
    email: {
      critical: true,
      warning: false,
      success: false,
      info: false
    },
    slack: {
      critical: true,
      warning: false,
      success: false,
      info: false
    },
    sms: {
      critical: true,
      warning: false,
      success: false,
      info: false
    }
  },
  quietHours: {
    enabled: true,
    startTime: '22:00',
    endTime: '07:00',
    criticalOnly: true
  },
  grouping: {
    enabled: true,
    windowMinutes: 30 as 30
  },
  eventToggles: {
    trade_opened: true,
    trade_closed_profit: true,
    trade_closed_loss: true,
    trade_rejected: true,
    system_error: true,
    system_recovered: true,
    agent_started: true,
    agent_stopped: true,
    agent_healthy: true,
    agent_degraded: true,
    agent_failed: true,
    performance_alert: true,
    breaker_triggered: true,
    threshold_warning: true,
    breaker_reset: true
  },
  sounds: {
    enabled: true,
    volume: 70,
    perPriority: {
      critical: 'critical-beep',
      warning: 'warning-beep',
      success: 'success-chime',
      info: 'info-notification'
    }
  },
  digest: {
    enabled: false,
    frequencyMinutes: 30 as 30,
    priorities: []
  }
}

const mockAddToast = jest.fn()

beforeEach(() => {
  jest.clearAllMocks()

  const { useNotificationPreferences } = require('@/hooks/useNotificationPreferences')
  const { useToasts } = require('@/hooks/useToasts')

  useNotificationPreferences.mockReturnValue({
    preferences: mockPreferences,
    updatePreference: jest.fn(),
    updateDeliveryMethod: mockUpdateDeliveryMethod,
    updateDeliveryMethodConfig: mockUpdateDeliveryMethodConfig,
    updatePriorityMatrix: mockUpdatePriorityMatrix,
    updateEventToggle: mockUpdateEventToggle,
    resetDefaults: mockResetDefaults,
    exportPreferences: mockExportPreferences,
    importPreferences: mockImportPreferences,
    validateConfig: mockValidateConfig
  })

  useToasts.mockReturnValue({
    toasts: [],
    showToast: mockAddToast,
    dismissToast: jest.fn(),
    dismissAll: jest.fn()
  })

  mockValidateConfig.mockReturnValue({ valid: true })
})

describe('NotificationPreferencesPage', () => {
  const renderPage = () => {
    return render(
      <NotificationProvider>
        <NotificationPreferencesPage />
      </NotificationProvider>
    )
  }

  it('should render page title and description', () => {
    renderPage()
    expect(screen.getByText('Notification Preferences')).toBeInTheDocument()
    expect(
      screen.getByText(/Customize how and when you receive notifications/i)
    ).toBeInTheDocument()
  })

  it('should render action buttons', () => {
    renderPage()
    expect(screen.getByText('Reset to Defaults')).toBeInTheDocument()
    expect(screen.getByText('Export Preferences')).toBeInTheDocument()
    expect(screen.getByText('Import Preferences')).toBeInTheDocument()
  })

  it('should render all preference sections', () => {
    renderPage()
    expect(screen.getByText('Delivery Methods')).toBeInTheDocument()
    expect(screen.getByText('Priority Filtering')).toBeInTheDocument()
    expect(screen.getByText('Quiet Hours')).toBeInTheDocument()
    expect(screen.getByText('Smart Grouping')).toBeInTheDocument()
    expect(screen.getByText('Event-Specific Filters')).toBeInTheDocument()
    expect(screen.getByText('Sound Alerts')).toBeInTheDocument()
  })

  it('should handle reset to defaults', () => {
    global.confirm = jest.fn().mockReturnValue(true)
    renderPage()

    const resetButton = screen.getByText('Reset to Defaults')
    fireEvent.click(resetButton)

    expect(mockResetDefaults).toHaveBeenCalled()
  })

  it('should not reset if user cancels', () => {
    global.confirm = jest.fn().mockReturnValue(false)
    renderPage()

    const resetButton = screen.getByText('Reset to Defaults')
    fireEvent.click(resetButton)

    expect(mockResetDefaults).not.toHaveBeenCalled()
  })

  it('should handle export preferences', () => {
    mockExportPreferences.mockReturnValue(JSON.stringify(mockPreferences))

    // Mock URL.createObjectURL and related functions
    global.URL.createObjectURL = jest.fn()
    global.URL.revokeObjectURL = jest.fn()

    renderPage()

    const exportButton = screen.getByText('Export Preferences')
    fireEvent.click(exportButton)

    expect(mockExportPreferences).toHaveBeenCalled()
  })

  it('should show delivery method controls', () => {
    renderPage()
    expect(screen.getAllByText('In-App')[0]).toBeInTheDocument()
    expect(screen.getAllByText('Browser Push')[0]).toBeInTheDocument()
    expect(screen.getAllByText('Email')[0]).toBeInTheDocument()
  })

  it('should show priority matrix', () => {
    renderPage()
    expect(screen.getByText('Priority Filtering')).toBeInTheDocument()
  })

  it('should show quiet hours configuration', () => {
    renderPage()
    expect(screen.getByText('Quiet Hours')).toBeInTheDocument()
    expect(screen.getByText('Enable Quiet Hours')).toBeInTheDocument()
  })

  it('should show event toggles', () => {
    renderPage()
    expect(screen.getByText('Event-Specific Filters')).toBeInTheDocument()
  })

  it('should show sound configuration', () => {
    renderPage()
    expect(screen.getByText('Sound Alerts')).toBeInTheDocument()
    expect(screen.getByText('Enable Sound Alerts')).toBeInTheDocument()
  })
})
