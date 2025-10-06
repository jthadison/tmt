/**
 * Tests for RollingWindowCard Component - Story 8.1
 */

import React from 'react'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { RollingWindowCard } from '@/components/analytics/RollingWindowCard'

describe('RollingWindowCard', () => {
  it('renders with upward trend', () => {
    render(
      <RollingWindowCard
        period="7d"
        value={1.82}
        trend="up"
        changePercent={8.2}
      />
    )

    expect(screen.getByText('7d')).toBeInTheDocument()
    expect(screen.getByText('1.82')).toBeInTheDocument()
    expect(screen.getByText('+8.2%')).toBeInTheDocument()
    expect(screen.getByText('Improving')).toBeInTheDocument()
  })

  it('renders with downward trend', () => {
    render(
      <RollingWindowCard
        period="30d"
        value={1.45}
        trend="down"
        changePercent={-3.5}
      />
    )

    expect(screen.getByText('30d')).toBeInTheDocument()
    expect(screen.getByText('1.45')).toBeInTheDocument()
    expect(screen.getByText('-3.5%')).toBeInTheDocument()
    expect(screen.getByText('Declining')).toBeInTheDocument()
  })

  it('renders with stable trend', () => {
    render(
      <RollingWindowCard
        period="14d"
        value={1.67}
        trend="stable"
        changePercent={0.8}
      />
    )

    expect(screen.getByText('14d')).toBeInTheDocument()
    expect(screen.getByText('1.67')).toBeInTheDocument()
    expect(screen.getByText('+0.8%')).toBeInTheDocument()
    expect(screen.getByText('Stable')).toBeInTheDocument()
  })

  it('formats value to 2 decimal places', () => {
    render(
      <RollingWindowCard
        period="90d"
        value={1.678945}
        trend="up"
        changePercent={5.234}
      />
    )

    expect(screen.getByText('1.68')).toBeInTheDocument()
    expect(screen.getByText('+5.2%')).toBeInTheDocument()
  })

  it('displays negative change without plus sign', () => {
    render(
      <RollingWindowCard
        period="7d"
        value={1.2}
        trend="down"
        changePercent={-10.5}
      />
    )

    expect(screen.getByText('-10.5%')).toBeInTheDocument()
  })

  it('displays outstanding value in correct color', () => {
    const { container } = render(
      <RollingWindowCard
        period="30d"
        value={2.5}
        trend="up"
        changePercent={15}
      />
    )

    const valueElement = screen.getByText('2.50')
    expect(valueElement).toHaveClass('text-emerald-700')
  })

  it('displays poor value in correct color', () => {
    const { container } = render(
      <RollingWindowCard
        period="7d"
        value={0.3}
        trend="down"
        changePercent={-20}
      />
    )

    const valueElement = screen.getByText('0.30')
    expect(valueElement).toHaveClass('text-red-600')
  })
})
