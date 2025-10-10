/**
 * Pattern Performance Card Component Tests (Story 12.2)
 */

import { describe, it, expect } from '@jest/globals'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import PatternPerformanceCard from './PatternPerformanceCard'
import { PatternPerformanceData } from '@/types/analytics122'

describe('PatternPerformanceCard', () => {
  const mockData: PatternPerformanceData = {
    Spring: { win_rate: 75.5, sample_size: 42, significant: true },
    Upthrust: { win_rate: 62.1, sample_size: 25, significant: true },
    Accumulation: { win_rate: 48.5, sample_size: 15, significant: false },
    Distribution: { win_rate: 35.2, sample_size: 8, significant: false },
  }

  it('should render all pattern types', () => {
    render(<PatternPerformanceCard data={mockData} loading={false} error={null} />)

    expect(screen.getByText('Spring')).toBeInTheDocument()
    expect(screen.getByText('Upthrust')).toBeInTheDocument()
    expect(screen.getByText('Accumulation')).toBeInTheDocument()
    expect(screen.getByText('Distribution')).toBeInTheDocument()
  })

  it('should display correct win rates', () => {
    render(<PatternPerformanceCard data={mockData} loading={false} error={null} />)

    expect(screen.getAllByText('75.5%')[0]).toBeInTheDocument()
    expect(screen.getAllByText('62.1%')[0]).toBeInTheDocument()
    expect(screen.getAllByText('48.5%')[0]).toBeInTheDocument()
    expect(screen.getAllByText('35.2%')[0]).toBeInTheDocument()
  })

  it('should display sample sizes', () => {
    render(<PatternPerformanceCard data={mockData} loading={false} error={null} />)

    expect(screen.getByText('n=42')).toBeInTheDocument()
    expect(screen.getByText('n=25')).toBeInTheDocument()
    expect(screen.getByText('n=15')).toBeInTheDocument()
    expect(screen.getByText('n=8')).toBeInTheDocument()
  })

  it('should show significance markers for n>=20', () => {
    render(<PatternPerformanceCard data={mockData} loading={false} error={null} />)

    // Spring and Upthrust should have ✓ markers (n>=20)
    const checkmarks = screen.getAllByText('✓')
    expect(checkmarks.length).toBeGreaterThanOrEqual(2)
  })

  it('should show loading state', () => {
    render(<PatternPerformanceCard data={null} loading={true} error={null} />)

    const skeletons = screen.getAllByRole('generic', { hidden: true }).filter(
      el => el.classList.contains('animate-pulse')
    )

    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('should show error state', () => {
    const error = new Error('API error')
    render(<PatternPerformanceCard data={null} loading={false} error={error} />)

    expect(screen.getByText(/API error/i)).toBeInTheDocument()
  })

  it('should show empty state when no data', () => {
    render(<PatternPerformanceCard data={{}} loading={false} error={null} />)

    expect(screen.getByText(/No pattern data available/i)).toBeInTheDocument()
  })

  it('should show significance legend', () => {
    render(<PatternPerformanceCard data={mockData} loading={false} error={null} />)

    expect(screen.getByText(/indicates statistically significant/i)).toBeInTheDocument()
  })
})
