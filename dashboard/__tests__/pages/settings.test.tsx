import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import SettingsPage from '@/app/settings/page'
import { SettingsProvider } from '@/context/SettingsContext'
import { ThemeProvider } from '@/context/ThemeContext'
import { AuthProvider } from '@/context/AuthContext'

// Mock useRouter from next/navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
  usePathname: () => '/settings',
}))

// Mock the AuthContext to return authenticated state
jest.mock('@/context/AuthContext', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
  useAuth: () => ({
    user: { email: 'test@example.com', name: 'Test User' },
    isAuthenticated: true,
    login: jest.fn(),
    logout: jest.fn(),
    loading: false
  })
}))

// Mock ProtectedRoute to not require authentication in tests
jest.mock('@/components/auth/ProtectedRoute', () => {
  return function ProtectedRoute({ children }: { children: React.ReactNode }) {
    return <>{children}</>
  }
})

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString()
    },
    removeItem: (key: string) => {
      delete store[key]
    },
    clear: () => {
      store = {}
    },
  }
})()

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
})

// Test wrapper with all necessary providers
const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <AuthProvider>
    <SettingsProvider>
      <ThemeProvider>
        {children}
      </ThemeProvider>
    </SettingsProvider>
  </AuthProvider>
)

describe('Settings Page', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('renders settings page with all tabs', () => {
    render(
      <TestWrapper>
        <SettingsPage />
      </TestWrapper>
    )

    expect(screen.getByText('Settings')).toBeInTheDocument()
    expect(screen.getByText('Configure your trading system preferences')).toBeInTheDocument()
    
    // Check tabs
    expect(screen.getByText('General')).toBeInTheDocument()
    expect(screen.getByText('Trading')).toBeInTheDocument()
    expect(screen.getByText('Display')).toBeInTheDocument()
    expect(screen.getByText('Alerts')).toBeInTheDocument()
    expect(screen.getByText('API')).toBeInTheDocument()
  })

  it('shows general tab content by default', () => {
    render(
      <TestWrapper>
        <SettingsPage />
      </TestWrapper>
    )

    expect(screen.getByText('System Preferences')).toBeInTheDocument()
    expect(screen.getByText('Dashboard Preferences')).toBeInTheDocument()
  })

  it('can switch between tabs', () => {
    render(
      <TestWrapper>
        <SettingsPage />
      </TestWrapper>
    )

    // Click on Trading tab
    fireEvent.click(screen.getByText('Trading'))
    expect(screen.getByText('Risk Management')).toBeInTheDocument()
    expect(screen.getByText('Trading Preferences')).toBeInTheDocument()

    // Click on API tab
    fireEvent.click(screen.getByText('API'))
    expect(screen.getByText('API Configuration')).toBeInTheDocument()
    expect(screen.getByText('OANDA Configuration')).toBeInTheDocument()
  })

  it('can update settings and shows unsaved changes', async () => {
    render(
      <TestWrapper>
        <SettingsPage />
      </TestWrapper>
    )

    // Find the notifications checkbox
    const notificationsCheckbox = screen.getByLabelText('Enable Notifications')
    
    // Initially, Save Changes button should be disabled
    const saveButton = screen.getByText('Save Changes')
    expect(saveButton).toBeDisabled()

    // Toggle the checkbox
    fireEvent.click(notificationsCheckbox)

    // Now Save Changes button should be enabled
    await waitFor(() => {
      expect(saveButton).not.toBeDisabled()
    })

    // Reset button should appear
    expect(screen.getByText('Reset')).toBeInTheDocument()
  })

  it('can save settings', async () => {
    render(
      <TestWrapper>
        <SettingsPage />
      </TestWrapper>
    )

    // Find refresh interval select
    const refreshIntervalSelect = screen.getByDisplayValue('30 seconds')
    
    // Change refresh interval
    fireEvent.change(refreshIntervalSelect, { target: { value: '60' } })

    // Save changes
    const saveButton = screen.getByText('Save Changes')
    fireEvent.click(saveButton)

    // Should show saving state
    await waitFor(() => {
      expect(screen.getByText('Saving...')).toBeInTheDocument()
    })

    // Should eventually show saved state
    await waitFor(() => {
      expect(screen.getByText(/Saved/)).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('persists settings to localStorage', async () => {
    render(
      <TestWrapper>
        <SettingsPage />
      </TestWrapper>
    )

    // Change a setting
    const soundAlertsCheckbox = screen.getByLabelText('Sound Alerts')
    fireEvent.click(soundAlertsCheckbox)

    // Save changes
    const saveButton = screen.getByText('Save Changes')
    fireEvent.click(saveButton)

    // Wait for save to complete
    await waitFor(() => {
      expect(screen.getByText(/Saved/)).toBeInTheDocument()
    }, { timeout: 3000 })

    // Check localStorage was updated
    const savedSettings = localStorage.getItem('tradingSystemSettings')
    expect(savedSettings).toBeTruthy()
    
    const parsed = JSON.parse(savedSettings!)
    expect(parsed.soundAlerts).toBe(true)
  })

  it('can reset settings', async () => {
    render(
      <TestWrapper>
        <SettingsPage />
      </TestWrapper>
    )

    // Change a setting
    const notificationsCheckbox = screen.getByLabelText('Enable Notifications')
    fireEvent.click(notificationsCheckbox)

    // Reset button should appear
    await waitFor(() => {
      expect(screen.getByText('Reset')).toBeInTheDocument()
    })

    // Click reset
    fireEvent.click(screen.getByText('Reset'))

    // Setting should be back to default
    expect(notificationsCheckbox).toBeChecked() // Default is true
  })

  it('loads settings from localStorage on mount', () => {
    // Pre-populate localStorage
    const testSettings = {
      theme: 'light',
      refreshInterval: 5,
      notifications: false,
      soundAlerts: true
    }
    localStorage.setItem('tradingSystemSettings', JSON.stringify(testSettings))

    render(
      <TestWrapper>
        <SettingsPage />
      </TestWrapper>
    )

    // Check that settings were loaded
    const notificationsCheckbox = screen.getByLabelText('Enable Notifications')
    expect(notificationsCheckbox).not.toBeChecked()

    const soundAlertsCheckbox = screen.getByLabelText('Sound Alerts')
    expect(soundAlertsCheckbox).toBeChecked()

    const refreshIntervalSelect = screen.getByDisplayValue('5 seconds')
    expect(refreshIntervalSelect).toBeInTheDocument()
  })
})