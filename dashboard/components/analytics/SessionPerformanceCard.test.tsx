/**
 * Session Performance Card Component Tests (Story 12.2)
 */

import { describe, it, expect } from '@jest/globals'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import SessionPerformanceCard from './SessionPerformanceCard'
import { SessionPerformanceData } from '@/types/analytics122'

describe('SessionPerformanceCard', () => {
  const mockData: SessionPerformanceData = {
    TOKYO: { win_rate: 72.5, total_trades: 40, winning_trades: 29, losing_trades: 11 },
    LONDON: { win_rate: 68.3, total_trades: 35, winning_trades: 24, losing_trades: 11 },
    NY: { win_rate: 55.0, total_trades: 20, winning_trades: 11, losing_trades: 9 },
    SYDNEY: { win_rate: 42.1, total_trades: 15, winning_trades: 6, losing_trades: 9 },
    OVERLAP: { win_rate: 80.0, total_trades: 10, winning_trades: 8, losing_trades: 2 },
  }

  it('should render all trading sessions', () => {
    render(<SessionPerformanceCard data={mockData} loading={false} error={null} />)

    expect(screen.getByText('TOKYO')).toBeInTheDocument()
    expect(screen.getByText('LONDON')).toBeInTheDocument()
    expect(screen.getByText('NY')).toBeInTheDocument()
    expect(screen.getByText('SYDNEY')).toBeInTheDocument()
    expect(screen.getByText('OVERLAP')).toBeInTheDocument()
  })

  it('should display correct win rates', () => {
    render(<SessionPerformanceCard data={mockData} loading={false} error={null} />)

    expect(screen.getByText('72.5%')).toBeInTheDocument()
    expect(screen.getByText('68.3%')).toBeInTheDocument()
    expect(screen.getByText('55.0%')).toBeInTheDocument()
    expect(screen.getByText('42.1%')).toBeInTheDocument()
    expect(screen.getByText('80.0%')).toBeInTheDocument()
  })

  it('should display trade counts', () => {
    render(<SessionPerformanceCard data={mockData} loading={false} error={null} />)

    expect(screen.getByText('n=40')).toBeInTheDocument()
    expect(screen.getByText('n=35')).toBeInTheDocument()
    expect(screen.getByText('n=20')).toBeInTheDocument()
  })

  it('should show loading state', () => {
    render(<SessionPerformanceCard data={null} loading={true} error={null} />)

    const skeletons = screen.getAllByRole('generic', { hidden: true }).filter(
      el => el.classList.contains('animate-pulse')
    )

    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('should show error state', () => {
    const error = new Error('Failed to load data')
    render(<SessionPerformanceCard data={null} loading={false} error={error} />)

    expect(screen.getByText(/Failed to load data/i)).toBeInTheDocument()
  })

  it('should show empty state when no data', () => {
    render(<SessionPerformanceCard data={{}} loading={false} error={null} />)

    expect(screen.getByText(/No session data available/i)).toBeInTheDocument()
    expect(screen.getByText(/Try adjusting the date range filter/i)).toBeInTheDocument()
  })

  it('should apply correct color coding for win rates', () => {
    const { container } = render(<SessionPerformanceCard data={mockData} loading={false} error={null} />)

    // TOKYO (72.5%) should be green (>55%)
    const tokyoRow = container.querySelector('[class*="bg-green"]')
    expect(tokyoRow).toBeInTheDocument()

    // NY (55.0%) should be yellow (45-55%)
    const nyRow = container.querySelector('[class*="bg-yellow"]')
    expect(nyRow).toBeInTheDocument()

    // SYDNEY (42.1%) should be red (<45%)
    const sydneyRow = container.querySelector('[class*="bg-red"]')
    expect(sydneyRow).toBeInTheDocument()
  })
})
