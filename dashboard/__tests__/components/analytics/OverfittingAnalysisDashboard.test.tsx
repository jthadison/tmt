import { render, screen } from '@testing-library/react'
import { OverfittingAnalysisDashboard } from '@/components/analytics/OverfittingAnalysisDashboard'
import { OverfittingAnalysis } from '@/app/api/analytics/overfitting-analysis/route'

describe('OverfittingAnalysisDashboard', () => {
  const mockAnalysisLowRisk: OverfittingAnalysis = {
    overfittingScore: 0.25,
    degradationPercentage: 8.5,
    riskLevel: 'low',
    metricDegradation: {
      winRate: { backtest: 70, forward: 68, degradation: -2.8 },
      profitFactor: { backtest: 2.4, forward: 2.3, degradation: -4.2 }
    },
    interpretation: 'Low overfitting risk (8.5% degradation). Strategy generalizes well to unseen data and shows stable performance.',
    recommendations: [
      'Strategy performing well - continue monitoring',
      'Consider gradual position size increases if stability maintains'
    ],
    stabilityScore: 82
  }

  const mockAnalysisHighRisk: OverfittingAnalysis = {
    overfittingScore: 0.85,
    degradationPercentage: 32,
    riskLevel: 'high',
    metricDegradation: {
      winRate: { backtest: 70, forward: 45, degradation: -35.7 },
      profitFactor: { backtest: 2.5, forward: 1.2, degradation: -52 }
    },
    interpretation: 'High overfitting risk (32.0% degradation). Strategy may be overfit to historical data with unstable live performance.',
    recommendations: [
      'Consider rolling back to previous strategy version',
      'Re-optimize parameters with walk-forward analysis'
    ],
    stabilityScore: 25
  }

  it('renders the overfitting analysis dashboard', () => {
    render(<OverfittingAnalysisDashboard analysis={mockAnalysisLowRisk} />)

    expect(screen.getByText('Overfitting Analysis')).toBeInTheDocument()
    expect(screen.getByText('Strategy performance validation and overfitting detection')).toBeInTheDocument()
  })

  it('displays overfitting score correctly', () => {
    render(<OverfittingAnalysisDashboard analysis={mockAnalysisLowRisk} />)

    expect(screen.getByText('0.25')).toBeInTheDocument()
    expect(screen.getByText('0 = None, 1 = Severe')).toBeInTheDocument()
  })

  it('displays degradation percentage', () => {
    render(<OverfittingAnalysisDashboard analysis={mockAnalysisLowRisk} />)

    expect(screen.getByText('8.5%')).toBeInTheDocument()
    expect(screen.getByText('Across all metrics')).toBeInTheDocument()
  })

  it('shows correct risk level for low risk', () => {
    render(<OverfittingAnalysisDashboard analysis={mockAnalysisLowRisk} />)

    expect(screen.getByText('Low Risk')).toBeInTheDocument()
  })

  it('shows correct risk level for high risk', () => {
    render(<OverfittingAnalysisDashboard analysis={mockAnalysisHighRisk} />)

    expect(screen.getByText('High Risk')).toBeInTheDocument()
  })

  it('displays stability score with progress bar', () => {
    render(<OverfittingAnalysisDashboard analysis={mockAnalysisLowRisk} />)

    expect(screen.getByText('Performance Stability')).toBeInTheDocument()
    expect(screen.getByText('82')).toBeInTheDocument()
    expect(screen.getByText('/ 100')).toBeInTheDocument()
  })

  it('displays interpretation text', () => {
    render(<OverfittingAnalysisDashboard analysis={mockAnalysisLowRisk} />)

    expect(screen.getByText(/Low overfitting risk/)).toBeInTheDocument()
    expect(screen.getByText(/Strategy generalizes well/)).toBeInTheDocument()
  })

  it('displays metric degradation breakdown', () => {
    render(<OverfittingAnalysisDashboard analysis={mockAnalysisLowRisk} />)

    expect(screen.getByText('Metric Degradation Breakdown')).toBeInTheDocument()
    expect(screen.getByText('win Rate')).toBeInTheDocument() // Formatted with space after capital
    expect(screen.getByText('profit Factor')).toBeInTheDocument() // Formatted with space after capital
  })

  it('displays recommendations', () => {
    render(<OverfittingAnalysisDashboard analysis={mockAnalysisLowRisk} />)

    expect(screen.getByText('💡')).toBeInTheDocument()
    expect(screen.getByText('Recommendations')).toBeInTheDocument()
    expect(screen.getByText(/Strategy performing well/)).toBeInTheDocument()
  })

  it('shows high risk recommendations', () => {
    render(<OverfittingAnalysisDashboard analysis={mockAnalysisHighRisk} />)

    expect(screen.getByText(/Consider rolling back/)).toBeInTheDocument()
    expect(screen.getByText(/Re-optimize parameters/)).toBeInTheDocument()
  })

  it('color codes degradation values correctly', () => {
    const { container } = render(<OverfittingAnalysisDashboard analysis={mockAnalysisLowRisk} />)

    // Negative degradation should be red
    const degradationCells = container.querySelectorAll('.text-red-500')
    expect(degradationCells.length).toBeGreaterThan(0)
  })

  it('handles moderate risk level', () => {
    const moderateAnalysis: OverfittingAnalysis = {
      ...mockAnalysisLowRisk,
      overfittingScore: 0.5,
      degradationPercentage: 20,
      riskLevel: 'moderate'
    }

    render(<OverfittingAnalysisDashboard analysis={moderateAnalysis} />)

    expect(screen.getByText('Moderate Risk')).toBeInTheDocument()
  })
})
