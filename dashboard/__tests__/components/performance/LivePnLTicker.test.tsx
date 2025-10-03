/**
 * Tests for LivePnLTicker component
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { LivePnLTicker } from '@/components/performance/LivePnLTicker'
import { usePnLData } from '@/hooks/usePnLData'

// Mock the hooks
jest.mock('@/hooks/usePnLData')
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}))

const mockUsePnLData = usePnLData as jest.MockedFunction<typeof usePnLData>

describe('LivePnLTicker', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders loading state when data is loading', () => {
    mockUsePnLData.mockReturnValue({
      dailyPnL: 0,
      pnLPercentage: 0,
      pnLHistory: [],
      realizedPnL: 0,
      unrealizedPnL: 0,
      isLoading: true,
      error: null,
      lastUpdate: null,
      updatePnL: jest.fn(),
    })

    render(<LivePnLTicker />)
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('renders positive P&L with correct styling', () => {
    mockUsePnLData.mockReturnValue({
      dailyPnL: 450.75,
      pnLPercentage: 2.5,
      pnLHistory: [400, 420, 430, 450.75],
      realizedPnL: 300,
      unrealizedPnL: 150.75,
      isLoading: false,
      error: null,
      lastUpdate: new Date(),
      updatePnL: jest.fn(),
    })

    render(<LivePnLTicker />)

    // Check for up arrow (positive)
    expect(screen.getByText('↑')).toBeInTheDocument()

    // Check for green color class (positive P&L)
    const ticker = screen.getByLabelText(/Live profit and loss ticker/i)
    expect(ticker).toHaveClass('text-green-400')
  })

  it('renders negative P&L with correct styling', () => {
    mockUsePnLData.mockReturnValue({
      dailyPnL: -250.50,
      pnLPercentage: -1.5,
      pnLHistory: [-200, -220, -240, -250.50],
      realizedPnL: -100,
      unrealizedPnL: -150.50,
      isLoading: false,
      error: null,
      lastUpdate: new Date(),
      updatePnL: jest.fn(),
    })

    render(<LivePnLTicker />)

    // Check for down arrow (negative)
    expect(screen.getByText('↓')).toBeInTheDocument()

    // Check for red color class (negative P&L)
    const ticker = screen.getByLabelText(/Live profit and loss ticker/i)
    expect(ticker).toHaveClass('text-red-400')
  })

  it('renders zero P&L with flat arrow', () => {
    mockUsePnLData.mockReturnValue({
      dailyPnL: 0,
      pnLPercentage: 0,
      pnLHistory: [0, 0, 0],
      realizedPnL: 0,
      unrealizedPnL: 0,
      isLoading: false,
      error: null,
      lastUpdate: new Date(),
      updatePnL: jest.fn(),
    })

    render(<LivePnLTicker />)

    // Check for flat arrow (zero)
    expect(screen.getByText('→')).toBeInTheDocument()
  })

  it('opens modal when clicked', async () => {
    mockUsePnLData.mockReturnValue({
      dailyPnL: 450.75,
      pnLPercentage: 2.5,
      pnLHistory: [400, 420, 430, 450.75],
      realizedPnL: 300,
      unrealizedPnL: 150.75,
      isLoading: false,
      error: null,
      lastUpdate: new Date(),
      updatePnL: jest.fn(),
    })

    render(<LivePnLTicker />)

    const ticker = screen.getByLabelText(/Live profit and loss ticker/i)
    fireEvent.click(ticker)

    // Modal should be opened (check for modal title)
    await waitFor(() => {
      expect(screen.getByText('P&L Breakdown')).toBeInTheDocument()
    })
  })

  it('displays sparkline when history has sufficient data', () => {
    mockUsePnLData.mockReturnValue({
      dailyPnL: 450.75,
      pnLPercentage: 2.5,
      pnLHistory: [400, 410, 420, 430, 440, 450.75],
      realizedPnL: 300,
      unrealizedPnL: 150.75,
      isLoading: false,
      error: null,
      lastUpdate: new Date(),
      updatePnL: jest.fn(),
    })

    const { container } = render(<LivePnLTicker />)

    // Check for SVG sparkline
    const svg = container.querySelector('svg')
    expect(svg).toBeInTheDocument()
  })

  it('does not display sparkline when history is insufficient', () => {
    mockUsePnLData.mockReturnValue({
      dailyPnL: 450.75,
      pnLPercentage: 2.5,
      pnLHistory: [450.75], // Only 1 point
      realizedPnL: 300,
      unrealizedPnL: 150.75,
      isLoading: false,
      error: null,
      lastUpdate: new Date(),
      updatePnL: jest.fn(),
    })

    const { container } = render(<LivePnLTicker />)

    // No SVG sparkline should be present
    const svg = container.querySelector('svg')
    expect(svg).not.toBeInTheDocument()
  })

  it('has proper accessibility attributes', () => {
    mockUsePnLData.mockReturnValue({
      dailyPnL: 450.75,
      pnLPercentage: 2.5,
      pnLHistory: [400, 420, 430, 450.75],
      realizedPnL: 300,
      unrealizedPnL: 150.75,
      isLoading: false,
      error: null,
      lastUpdate: new Date(),
      updatePnL: jest.fn(),
    })

    render(<LivePnLTicker />)

    const ticker = screen.getByLabelText(
      /Live profit and loss ticker. Click to see detailed breakdown/i
    )
    expect(ticker).toHaveAttribute('aria-live', 'polite')
  })
})
