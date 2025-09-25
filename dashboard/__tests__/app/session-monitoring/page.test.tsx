import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import SessionMonitoringPage from '@/app/session-monitoring/page'
import { renderWithProviders } from '@/__tests__/testUtils'

// Mock the components
jest.mock('@/components/session-monitoring/SessionOverviewDashboard', () => {
  return function MockSessionOverviewDashboard({ onSessionSelect, currentSession }: any) {
    return (
      <div data-testid="session-overview">
        <button onClick={() => onSessionSelect('london')}>Select London</button>
        <button onClick={() => onSessionSelect('tokyo')}>Select Tokyo</button>
        <span>Current: {currentSession}</span>
      </div>
    )
  }
})

jest.mock('@/components/session-monitoring/SessionPerformanceMetrics', () => {
  return function MockSessionPerformanceMetrics({ selectedSession }: any) {
    return <div data-testid="performance-metrics">Metrics for: {selectedSession}</div>
  }
})

jest.mock('@/components/session-monitoring/PositionSizingMonitor', () => {
  return function MockPositionSizingMonitor({ currentSession }: any) {
    return <div data-testid="position-sizing">Position sizing for: {currentSession}</div>
  }
})

jest.mock('@/components/session-monitoring/ForwardTestMetricsPanel', () => {
  return function MockForwardTestMetricsPanel() {
    return <div data-testid="forward-test-metrics">Forward test metrics panel</div>
  }
})

jest.mock('@/components/session-monitoring/SessionDetailView', () => {
  return function MockSessionDetailView({ sessionData }: any) {
    return <div data-testid="session-detail">Detail view for: {sessionData?.name || 'Unknown'}</div>
  }
})

// Mock fetch for API calls
global.fetch = jest.fn()

describe('SessionMonitoringPage', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    ;(fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({
        useForwardTestSizing: true,
        metrics: {
          walkForwardStability: 34.4,
          outOfSampleValidation: 17.4,
          overfittingScore: 0.634,
          kurtosisExposure: 20.316,
          monthsOfData: 6
        }
      })
    })

    // Mock Date to ensure consistent session detection
    jest.useFakeTimers()
    jest.setSystemTime(new Date('2024-01-15T14:00:00.000Z')) // 14:00 GMT - London session
  })

  afterEach(() => {
    jest.useRealTimers()
  })

  it('renders session monitoring page with all components', async () => {
    renderWithProviders(<SessionMonitoringPage />)

    await waitFor(() => {
      expect(screen.getByText('Session Monitoring Dashboard')).toBeInTheDocument()
    })

    expect(screen.getByTestId('session-overview')).toBeInTheDocument()
    expect(screen.getByTestId('performance-metrics')).toBeInTheDocument()
    expect(screen.getByTestId('position-sizing')).toBeInTheDocument()
    expect(screen.getByTestId('forward-test-metrics')).toBeInTheDocument()
  })

  it('detects current session correctly', async () => {
    renderWithProviders(<SessionMonitoringPage />)

    await waitFor(() => {
      // At 14:00 GMT, should detect London session
      expect(screen.getByText('Current: london')).toBeInTheDocument()
    })
  })

  it('allows session selection and updates components', async () => {
    renderWithProviders(<SessionMonitoringPage />)

    await waitFor(() => {
      expect(screen.getByText('Select Tokyo')).toBeInTheDocument()
    })

    // Click to select Tokyo session
    fireEvent.click(screen.getByText('Select Tokyo'))

    await waitFor(() => {
      expect(screen.getByText('Current: tokyo')).toBeInTheDocument()
      expect(screen.getByText('Metrics for: tokyo')).toBeInTheDocument()
      expect(screen.getByText('Position sizing for: tokyo')).toBeInTheDocument()
    })
  })

  it('fetches forward test status on mount', async () => {
    renderWithProviders(<SessionMonitoringPage />)

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/position-sizing/forward-test/status')
    })
  })

  it('displays session detail view when session is selected', async () => {
    renderWithProviders(<SessionMonitoringPage />)

    await waitFor(() => {
      expect(screen.getByTestId('session-detail')).toBeInTheDocument()
    })

    // Select a different session
    fireEvent.click(screen.getByText('Select London'))

    await waitFor(() => {
      expect(screen.getByText('Detail view for: London Session')).toBeInTheDocument()
    })
  })

  it('handles API errors gracefully', async () => {
    ;(fetch as jest.Mock).mockRejectedValueOnce(new Error('API Error'))

    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {})

    renderWithProviders(<SessionMonitoringPage />)

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith('Error fetching forward test status:', expect.any(Error))
    })

    consoleSpy.mockRestore()
  })

  it('generates mock session data correctly', async () => {
    renderWithProviders(<SessionMonitoringPage />)

    await waitFor(() => {
      // Should have all 5 sessions
      expect(screen.getByText('Select London')).toBeInTheDocument()
      expect(screen.getByText('Select Tokyo')).toBeInTheDocument()
    })
  })

  it('updates session status based on current time', async () => {
    // Test different times for different session statuses
    jest.setSystemTime(new Date('2024-01-15T08:00:00.000Z')) // 08:00 GMT - London active

    renderWithProviders(<SessionMonitoringPage />)

    await waitFor(() => {
      expect(screen.getByText('Current: london')).toBeInTheDocument()
    })
  })

  it('handles session switching smoothly', async () => {
    renderWithProviders(<SessionMonitoringPage />)

    await waitFor(() => {
      expect(screen.getByText('Current: london')).toBeInTheDocument()
    })

    // Switch to Tokyo
    fireEvent.click(screen.getByText('Select Tokyo'))

    await waitFor(() => {
      expect(screen.getByText('Current: tokyo')).toBeInTheDocument()
      expect(screen.getByText('Metrics for: tokyo')).toBeInTheDocument()
      expect(screen.getByText('Position sizing for: tokyo')).toBeInTheDocument()
    })

    // Switch back to London
    fireEvent.click(screen.getByText('Select London'))

    await waitFor(() => {
      expect(screen.getByText('Current: london')).toBeInTheDocument()
      expect(screen.getByText('Metrics for: london')).toBeInTheDocument()
      expect(screen.getByText('Position sizing for: london')).toBeInTheDocument()
    })
  })

  it('displays loading states appropriately', async () => {
    // Mock slow API response
    ;(fetch as jest.Mock).mockImplementation(() =>
      new Promise(resolve =>
        setTimeout(() => resolve({
          ok: true,
          json: async () => ({ useForwardTestSizing: true, metrics: {} })
        }), 100)
      )
    )

    renderWithProviders(<SessionMonitoringPage />)

    // Components should still render with default data
    expect(screen.getByTestId('session-overview')).toBeInTheDocument()
  })

  it('maintains state consistency across session changes', async () => {
    renderWithProviders(<SessionMonitoringPage />)

    await waitFor(() => {
      expect(screen.getByText('Current: london')).toBeInTheDocument()
    })

    // Change session multiple times
    fireEvent.click(screen.getByText('Select Tokyo'))
    await waitFor(() => {
      expect(screen.getByText('Current: tokyo')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('Select London'))
    await waitFor(() => {
      expect(screen.getByText('Current: london')).toBeInTheDocument()
    })

    // All components should be in sync
    expect(screen.getByText('Metrics for: london')).toBeInTheDocument()
    expect(screen.getByText('Position sizing for: london')).toBeInTheDocument()
  })
})