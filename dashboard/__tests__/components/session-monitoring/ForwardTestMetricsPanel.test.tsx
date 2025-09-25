import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ForwardTestMetricsPanel from '@/components/session-monitoring/ForwardTestMetricsPanel'
import { renderWithProviders } from '@/__tests__/testUtils'

// Mock fetch globally
global.fetch = jest.fn()

const mockForwardTestMetrics = {
  walkForwardStability: 34.4,
  outOfSampleValidation: 17.4,
  overfittingScore: 0.634,
  kurtosisExposure: 20.316,
  monthsOfData: 6
}

describe('ForwardTestMetricsPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    ;(fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ success: true })
    })
  })

  it('renders forward test metrics correctly', () => {
    renderWithProviders(
      <ForwardTestMetricsPanel forwardTestMetrics={mockForwardTestMetrics} />
    )

    expect(screen.getByText('Forward Test Metrics')).toBeInTheDocument()
    expect(screen.getByText('Walk-Forward Stability')).toBeInTheDocument()
    expect(screen.getByText('34.4/100')).toBeInTheDocument()
    expect(screen.getByText('Out-of-Sample Validation')).toBeInTheDocument()
    expect(screen.getByText('17.4/100')).toBeInTheDocument()
  })

  it('displays overfitting score and status', () => {
    renderWithProviders(
      <ForwardTestMetricsPanel forwardTestMetrics={mockForwardTestMetrics} />
    )

    expect(screen.getByText('Overfitting Score')).toBeInTheDocument()
    expect(screen.getByText('0.634')).toBeInTheDocument()
    expect(screen.getByText('HIGH OVERFITTING')).toBeInTheDocument()
  })

  it('displays kurtosis exposure with warning', () => {
    renderWithProviders(
      <ForwardTestMetricsPanel forwardTestMetrics={mockForwardTestMetrics} />
    )

    expect(screen.getByText('Kurtosis Exposure')).toBeInTheDocument()
    expect(screen.getByText('20.32')).toBeInTheDocument()
    expect(screen.getByText('HIGH KURTOSIS')).toBeInTheDocument()
  })

  it('shows months of data information', () => {
    renderWithProviders(
      <ForwardTestMetricsPanel forwardTestMetrics={mockForwardTestMetrics} />
    )

    expect(screen.getByText('Data Period')).toBeInTheDocument()
    expect(screen.getByText('6 months')).toBeInTheDocument()
    expect(screen.getByText('INSUFFICIENT')).toBeInTheDocument()
  })

  it('displays critical recommendations section', () => {
    renderWithProviders(
      <ForwardTestMetricsPanel forwardTestMetrics={mockForwardTestMetrics} />
    )

    expect(screen.getByText('🚨 Critical Recommendations')).toBeInTheDocument()
    expect(screen.getByText(/Stability below 60/)).toBeInTheDocument()
    expect(screen.getByText(/Validation below 50/)).toBeInTheDocument()
    expect(screen.getByText(/Overfitting score above 0.5/)).toBeInTheDocument()
    expect(screen.getByText(/High kurtosis exposure/)).toBeInTheDocument()
  })

  it('shows metric update form', () => {
    renderWithProviders(
      <ForwardTestMetricsPanel forwardTestMetrics={mockForwardTestMetrics} />
    )

    expect(screen.getByText('Update Metrics')).toBeInTheDocument()
    expect(screen.getByLabelText('Walk-Forward Stability')).toBeInTheDocument()
    expect(screen.getByLabelText('Out-of-Sample Validation')).toBeInTheDocument()
    expect(screen.getByLabelText('Overfitting Score')).toBeInTheDocument()
    expect(screen.getByLabelText('Kurtosis Exposure')).toBeInTheDocument()
  })

  it('allows metric values to be updated', () => {
    renderWithProviders(
      <ForwardTestMetricsPanel forwardTestMetrics={mockForwardTestMetrics} />
    )

    const stabilityInput = screen.getByLabelText('Walk-Forward Stability')
    fireEvent.change(stabilityInput, { target: { value: '65.5' } })

    expect(stabilityInput).toHaveValue(65.5)
  })

  it('submits updated metrics successfully', async () => {
    renderWithProviders(
      <ForwardTestMetricsPanel forwardTestMetrics={mockForwardTestMetrics} />
    )

    const stabilityInput = screen.getByLabelText('Walk-Forward Stability')
    const updateButton = screen.getByText('Update Metrics')

    fireEvent.change(stabilityInput, { target: { value: '65.5' } })
    fireEvent.click(updateButton)

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/position-sizing/forward-test/update-metrics', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          walkForwardStability: 65.5,
          outOfSampleValidation: 17.4,
          overfittingScore: 0.634,
          kurtosisExposure: 20.316,
          monthsOfData: 6
        })
      })
    })
  })

  it('handles API errors gracefully', async () => {
    ;(fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error'
    })

    renderWithProviders(
      <ForwardTestMetricsPanel forwardTestMetrics={mockForwardTestMetrics} />
    )

    const updateButton = screen.getByText('Update Metrics')
    fireEvent.click(updateButton)

    await waitFor(() => {
      expect(screen.getByText(/Error updating metrics/)).toBeInTheDocument()
    })
  })

  it('shows loading state during update', async () => {
    ;(fetch as jest.Mock).mockImplementation(() =>
      new Promise(resolve => setTimeout(() => resolve({ ok: true, json: async () => ({ success: true }) }), 100))
    )

    renderWithProviders(
      <ForwardTestMetricsPanel forwardTestMetrics={mockForwardTestMetrics} />
    )

    const updateButton = screen.getByText('Update Metrics')
    fireEvent.click(updateButton)

    expect(screen.getByText('Updating...')).toBeInTheDocument()
  })

  it('applies correct color coding for metrics', () => {
    renderWithProviders(
      <ForwardTestMetricsPanel forwardTestMetrics={mockForwardTestMetrics} />
    )

    // Poor stability (34.4) should be red
    const stabilityValue = screen.getByText('34.4/100')
    expect(stabilityValue).toHaveClass('text-red-400')

    // Poor validation (17.4) should be red
    const validationValue = screen.getByText('17.4/100')
    expect(validationValue).toHaveClass('text-red-400')

    // High overfitting (0.634) status should be red
    const overfittingStatus = screen.getByText('HIGH OVERFITTING')
    expect(overfittingStatus).toHaveClass('text-red-400')

    // High kurtosis status should be red
    const kurtosisStatus = screen.getByText('HIGH KURTOSIS')
    expect(kurtosisStatus).toHaveClass('text-red-400')
  })

  it('shows progress bars for metrics', () => {
    const { container } = renderWithProviders(
      <ForwardTestMetricsPanel forwardTestMetrics={mockForwardTestMetrics} />
    )

    // Should have progress bars for stability and validation
    const progressBars = container.querySelectorAll('.bg-gray-700.rounded-full.h-3')
    expect(progressBars.length).toBeGreaterThanOrEqual(2)
  })

  it('displays emergency rollback toggle', () => {
    renderWithProviders(
      <ForwardTestMetricsPanel forwardTestMetrics={mockForwardTestMetrics} />
    )

    expect(screen.getByText('Emergency Rollback to Cycle 4')).toBeInTheDocument()
    expect(screen.getByLabelText('Enable Emergency Rollback')).toBeInTheDocument()
  })

  it('handles emergency rollback toggle', async () => {
    renderWithProviders(
      <ForwardTestMetricsPanel forwardTestMetrics={mockForwardTestMetrics} />
    )

    const rollbackToggle = screen.getByLabelText('Enable Emergency Rollback')
    fireEvent.click(rollbackToggle)

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/position-sizing/forward-test/toggle', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ useForwardTestSizing: false })
      })
    })
  })

  it('validates input ranges', () => {
    renderWithProviders(
      <ForwardTestMetricsPanel forwardTestMetrics={mockForwardTestMetrics} />
    )

    const stabilityInput = screen.getByLabelText('Walk-Forward Stability')

    // Test invalid range
    fireEvent.change(stabilityInput, { target: { value: '150' } })
    expect(stabilityInput).toHaveValue(100) // Should be clamped to max

    fireEvent.change(stabilityInput, { target: { value: '-10' } })
    expect(stabilityInput).toHaveValue(0) // Should be clamped to min
  })

  it('shows good metrics with appropriate styling', () => {
    const goodMetrics = {
      walkForwardStability: 75.5,
      outOfSampleValidation: 68.2,
      overfittingScore: 0.25,
      kurtosisExposure: 8.5,
      monthsOfData: 12
    }

    renderWithProviders(
      <ForwardTestMetricsPanel forwardTestMetrics={goodMetrics} />
    )

    // Good stability should be green
    const stabilityValue = screen.getByText('75.5/100')
    expect(stabilityValue).toHaveClass('text-green-400')

    // Good validation should be green
    const validationValue = screen.getByText('68.2/100')
    expect(validationValue).toHaveClass('text-green-400')

    // Low overfitting should show "LOW OVERFITTING"
    expect(screen.getByText('LOW OVERFITTING')).toBeInTheDocument()

    // Normal kurtosis should show "NORMAL KURTOSIS"
    expect(screen.getByText('NORMAL KURTOSIS')).toBeInTheDocument()

    // Sufficient data should show "SUFFICIENT"
    expect(screen.getByText('SUFFICIENT')).toBeInTheDocument()
  })

  it('shows deployment readiness assessment', () => {
    renderWithProviders(
      <ForwardTestMetricsPanel forwardTestMetrics={mockForwardTestMetrics} />
    )

    expect(screen.getByText('⛔ NOT READY FOR DEPLOYMENT')).toBeInTheDocument()
    expect(screen.getByText('Multiple critical issues require immediate attention')).toBeInTheDocument()
  })
})