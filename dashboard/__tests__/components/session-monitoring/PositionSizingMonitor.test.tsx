import { render, screen, fireEvent } from '@testing-library/react'
import PositionSizingMonitor from '@/components/session-monitoring/PositionSizingMonitor'
import { renderWithProviders } from '@/__tests__/testUtils'

const mockSessionData = [
  {
    session: 'london' as const,
    name: 'London Session',
    positionSizing: {
      stabilityFactor: 0.45,
      validationFactor: 0.25,
      volatilityFactor: 0.85,
      totalReduction: 0.35, // 35% reduction
      maxPosition: 3.5,
      currentRisk: 1.0
    },
    metrics: {
      positionSizeReduction: 65, // 65% reduction from base
      currentPhase: 2,
      capitalAllocation: 25
    }
  }
]

describe('PositionSizingMonitor', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders position sizing monitor with session data', () => {
    renderWithProviders(
      <PositionSizingMonitor
        sessionData={mockSessionData}
        currentSession="london"
      />
    )

    expect(screen.getByText('Position Sizing Monitor - London Session')).toBeInTheDocument()
    expect(screen.getByText('Position Size Impact')).toBeInTheDocument()
  })

  it('displays factor view toggle buttons', () => {
    renderWithProviders(
      <PositionSizingMonitor
        sessionData={mockSessionData}
        currentSession="london"
      />
    )

    expect(screen.getByText('All')).toBeInTheDocument()
    expect(screen.getByText('Stability')).toBeInTheDocument()
    expect(screen.getByText('Validation')).toBeInTheDocument()
    expect(screen.getByText('Volatility')).toBeInTheDocument()
  })

  it('switches factor views when buttons are clicked', () => {
    renderWithProviders(
      <PositionSizingMonitor
        sessionData={mockSessionData}
        currentSession="london"
      />
    )

    const stabilityButton = screen.getByText('Stability')
    fireEvent.click(stabilityButton)

    // Button should become active
    expect(stabilityButton).toHaveClass('bg-blue-600', 'text-white')

    // Should show stability-specific content
    expect(screen.getByText('Stability Factor Impact')).toBeInTheDocument()
    // Should not show validation section when stability is selected
    expect(screen.queryByText('Validation Factor Impact')).not.toBeInTheDocument()
  })

  it('displays position size reduction visualization', () => {
    renderWithProviders(
      <PositionSizingMonitor
        sessionData={mockSessionData}
        currentSession="london"
      />
    )

    expect(screen.getByText('Base Size')).toBeInTheDocument()
    expect(screen.getByText('10,000')).toBeInTheDocument() // Base position size
    expect(screen.getByText('Final Size')).toBeInTheDocument()
    expect(screen.getByText('3,500')).toBeInTheDocument() // Reduced size (10,000 * 0.35)

    // Reduction percentage
    expect(screen.getByText('-65.0%')).toBeInTheDocument()
  })

  it('shows forward test metrics correctly', () => {
    renderWithProviders(
      <PositionSizingMonitor
        sessionData={mockSessionData}
        currentSession="london"
      />
    )

    // Forward test metrics should be displayed
    expect(screen.getByText('Walk-Forward Stability:')).toBeInTheDocument()
    expect(screen.getByText('34.4/100')).toBeInTheDocument()
    expect(screen.getByText('Out-of-Sample Validation:')).toBeInTheDocument()
    expect(screen.getByText('17.4/100')).toBeInTheDocument()
  })

  it('displays stability factor information', () => {
    renderWithProviders(
      <PositionSizingMonitor
        sessionData={mockSessionData}
        currentSession="london"
      />
    )

    expect(screen.getByText('Stability Factor Impact')).toBeInTheDocument()
    expect(screen.getByText('LOW STABILITY')).toBeInTheDocument()
    expect(screen.getByText('45%')).toBeInTheDocument() // Stability factor percentage
    expect(screen.getByText('Reduces position size by 55% due to poor walk-forward performance')).toBeInTheDocument()
  })

  it('displays validation factor information', () => {
    renderWithProviders(
      <PositionSizingMonitor
        sessionData={mockSessionData}
        currentSession="london"
      />
    )

    expect(screen.getByText('Validation Factor Impact')).toBeInTheDocument()
    expect(screen.getByText('POOR VALIDATION')).toBeInTheDocument()
    expect(screen.getByText('25%')).toBeInTheDocument() // Validation factor percentage
    expect(screen.getByText('Reduces position size by 75% due to poor out-of-sample results')).toBeInTheDocument()
  })

  it('displays volatility factor information', () => {
    renderWithProviders(
      <PositionSizingMonitor
        sessionData={mockSessionData}
        currentSession="london"
      />
    )

    expect(screen.getByText('Volatility Factor Impact')).toBeInTheDocument()
    expect(screen.getByText('NORMAL VOLATILITY')).toBeInTheDocument()
    expect(screen.getByText('85%')).toBeInTheDocument() // Volatility factor percentage
    expect(screen.getByText('Reduces position size by 15% due to elevated volatility')).toBeInTheDocument()
  })

  it('shows capital allocation phase information', () => {
    renderWithProviders(
      <PositionSizingMonitor
        sessionData={mockSessionData}
        currentSession="london"
      />
    )

    expect(screen.getByText('Capital Allocation Phase')).toBeInTheDocument()
    expect(screen.getByText('Phase 2')).toBeInTheDocument()
    expect(screen.getByText('25%')).toBeInTheDocument() // Capital allocation
    expect(screen.getByText('Stability ≥60, Validation ≥60')).toBeInTheDocument() // Phase 2 requirements
  })

  it('displays phase progression indicators', () => {
    renderWithProviders(
      <PositionSizingMonitor
        sessionData={mockSessionData}
        currentSession="london"
      />
    )

    // Should show 4 phase indicators
    expect(screen.getByText('Phase 1')).toBeInTheDocument()
    expect(screen.getByText('Phase 2')).toBeInTheDocument()
    expect(screen.getByText('Phase 3')).toBeInTheDocument()
    expect(screen.getByText('Phase 4')).toBeInTheDocument()

    // Phase percentages
    expect(screen.getByText('10%')).toBeInTheDocument() // Phase 1
    expect(screen.getByText('25%')).toBeInTheDocument() // Phase 2
    expect(screen.getByText('50%')).toBeInTheDocument() // Phase 3
    expect(screen.getByText('100%')).toBeInTheDocument() // Phase 4
  })

  it('shows phase advancement requirements', () => {
    renderWithProviders(
      <PositionSizingMonitor
        sessionData={mockSessionData}
        currentSession="london"
      />
    )

    expect(screen.getByText('⚠️ Phase Advancement Requirements')).toBeInTheDocument()
    expect(screen.getByText(/To advance to Phase 3/)).toBeInTheDocument()
    expect(screen.getByText(/Walk-forward stability ≥70/)).toBeInTheDocument()
    expect(screen.getByText(/out-of-sample validation ≥70/)).toBeInTheDocument()
  })

  it('displays current metrics vs requirements', () => {
    renderWithProviders(
      <PositionSizingMonitor
        sessionData={mockSessionData}
        currentSession="london"
      />
    )

    expect(screen.getByText('Current: Stability 34.4, Validation 17.4')).toBeInTheDocument()
  })

  it('shows quick action buttons', () => {
    renderWithProviders(
      <PositionSizingMonitor
        sessionData={mockSessionData}
        currentSession="london"
      />
    )

    expect(screen.getByText('Update Metrics')).toBeInTheDocument()
    expect(screen.getByText('View Forward Tests')).toBeInTheDocument()
    expect(screen.getByText('Emergency Rollback')).toBeInTheDocument()
    expect(screen.getByText('Export Report')).toBeInTheDocument()
  })

  it('applies correct color coding for factors', () => {
    renderWithProviders(
      <PositionSizingMonitor
        sessionData={mockSessionData}
        currentSession="london"
      />
    )

    // Stability factor (45% = 0.45) should be red (< 0.5)
    const stabilityPercentage = screen.getByText('45%')
    expect(stabilityPercentage).toHaveClass('text-red-400')

    // Validation factor (25% = 0.25) should be red (< 0.5)
    const validationPercentage = screen.getByText('25%')
    expect(validationPercentage).toHaveClass('text-red-400')

    // Volatility factor (85% = 0.85) should be green (> 0.8)
    const volatilityPercentage = screen.getByText('85%')
    expect(volatilityPercentage).toHaveClass('text-green-400')
  })

  it('shows detailed position sizing breakdown', () => {
    renderWithProviders(
      <PositionSizingMonitor
        sessionData={mockSessionData}
        currentSession="london"
      />
    )

    expect(screen.getByText('Total Reduction')).toBeInTheDocument()
    expect(screen.getByText('Max Position')).toBeInTheDocument()
    expect(screen.getByText('3.5%')).toBeInTheDocument() // Max position size
    expect(screen.getByText('Risk Per Trade')).toBeInTheDocument()
    expect(screen.getByText('1%')).toBeInTheDocument() // Current risk
    expect(screen.getByText('Capital Phase')).toBeInTheDocument()
  })

  it('handles missing session data gracefully', () => {
    renderWithProviders(
      <PositionSizingMonitor
        sessionData={mockSessionData}
        currentSession="tokyo" // Session not in data
      />
    )

    // Component should not render when session is not found
    expect(screen.queryByText('Position Sizing Monitor')).not.toBeInTheDocument()
  })

  it('shows correct progress bars for factors', () => {
    const { container } = renderWithProviders(
      <PositionSizingMonitor
        sessionData={mockSessionData}
        currentSession="london"
      />
    )

    // Check for progress bar elements
    const progressBars = container.querySelectorAll('.bg-gray-700.rounded-full.h-2')
    expect(progressBars.length).toBeGreaterThan(0)

    // Check for colored progress indicators
    const redBars = container.querySelectorAll('.bg-red-500')
    const greenBars = container.querySelectorAll('.bg-green-500')
    expect(redBars.length).toBeGreaterThan(0) // For low stability/validation
    expect(greenBars.length).toBeGreaterThan(0) // For volatility
  })

  it('handles volatility factor at 100%', () => {
    const sessionWithNormalVolatility = [{
      ...mockSessionData[0],
      positionSizing: {
        ...mockSessionData[0].positionSizing,
        volatilityFactor: 1.0 // 100% - no reduction
      }
    }]

    renderWithProviders(
      <PositionSizingMonitor
        sessionData={sessionWithNormalVolatility}
        currentSession="london"
      />
    )

    expect(screen.getByText('Normal volatility - no size reduction applied')).toBeInTheDocument()
  })
})