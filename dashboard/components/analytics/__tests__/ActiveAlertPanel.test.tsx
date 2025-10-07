import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { ActiveAlertPanel } from '../ActiveAlertPanel'
import { PerformanceAlert } from '@/types/analytics'

// Mock fetch
global.fetch = jest.fn()

const mockAlerts: PerformanceAlert[] = [
  {
    id: 'alert1',
    type: 'overfitting',
    severity: 'critical',
    timestamp: Date.now(),
    metric: 'overfitting',
    currentValue: 0.85,
    thresholdValue: 0.8,
    message: 'High overfitting detected',
    recommendation: 'Strategy may be overfit to historical data - consider rollback',
    autoRollback: true
  },
  {
    id: 'alert2',
    type: 'profit_decline',
    severity: 'high',
    timestamp: Date.now() - 1000,
    metric: 'profit decline',
    currentValue: 2.0,
    thresholdValue: 2.5,
    message: 'Profit factor declined 20%',
    recommendation: 'Review recent trades for pattern changes',
    autoRollback: false
  }
]

describe('ActiveAlertPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  test('displays active alerts', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockAlerts
    })

    render(<ActiveAlertPanel />)

    await waitFor(() => {
      expect(screen.getByText(/High overfitting detected/)).toBeInTheDocument()
      expect(screen.getByText(/Profit factor declined/)).toBeInTheDocument()
    })
  })

  test('sorts alerts by severity', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockAlerts
    })

    render(<ActiveAlertPanel />)

    await waitFor(() => {
      const alertCards = screen.getAllByTestId('alert-card')
      expect(alertCards).toHaveLength(2)
      // Critical alert should be present
      const hasCritical = Array.from(alertCards).some(card =>
        card.textContent?.includes('CRITICAL')
      )
      expect(hasCritical).toBe(true)
    })
  })

  test('shows empty state when no alerts', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => []
    })

    render(<ActiveAlertPanel />)

    await waitFor(() => {
      expect(screen.getByText(/No active alerts/)).toBeInTheDocument()
      expect(screen.getByText(/System performance is nominal/)).toBeInTheDocument()
    })
  })

  test('acknowledges alert on button click', async () => {
    ;(global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [mockAlerts[0]]
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true })
      })

    render(<ActiveAlertPanel />)

    await waitFor(() => {
      expect(screen.getByText(/High overfitting detected/)).toBeInTheDocument()
    })

    const acknowledgeButton = screen.getByText('Acknowledge')
    fireEvent.click(acknowledgeButton)

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/analytics/degradation-alerts/acknowledge/alert1',
        { method: 'POST' }
      )
    })
  })

  test('displays auto-rollback indicator for critical alerts', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => [mockAlerts[0]]
    })

    render(<ActiveAlertPanel />)

    await waitFor(() => {
      expect(screen.getByText(/Auto-rollback trigger/)).toBeInTheDocument()
    })
  })

  test('shows loading state initially', () => {
    ;(global.fetch as jest.Mock).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    render(<ActiveAlertPanel />)

    // Loading skeleton should be visible
    const container = document.querySelector('.animate-pulse')
    expect(container).toBeInTheDocument()
    expect(container).toHaveClass('animate-pulse')
  })

  test('displays error state on fetch failure', async () => {
    ;(global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'))

    render(<ActiveAlertPanel />)

    await waitFor(() => {
      expect(screen.getByText(/Error loading alerts/)).toBeInTheDocument()
    })
  })
})
