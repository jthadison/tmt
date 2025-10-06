/**
 * Tests for SharpeRatioGauge Component - Story 8.1
 */

import React from 'react'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { SharpeRatioGauge } from '@/components/analytics/SharpeRatioGauge'

describe('SharpeRatioGauge', () => {
  it('renders with outstanding threshold', () => {
    render(
      <SharpeRatioGauge
        value={2.5}
        thresholdLevel="outstanding"
        interpretation="Outstanding risk-adjusted returns"
      />
    )

    expect(screen.getByText('2.50')).toBeInTheDocument()
    expect(screen.getByText('Outstanding')).toBeInTheDocument()
    expect(screen.getByText('Outstanding risk-adjusted returns')).toBeInTheDocument()
  })

  it('renders with excellent threshold', () => {
    render(
      <SharpeRatioGauge
        value={1.67}
        thresholdLevel="excellent"
        interpretation="Excellent risk-adjusted returns"
      />
    )

    expect(screen.getByText('1.67')).toBeInTheDocument()
    expect(screen.getByText('Excellent')).toBeInTheDocument()
    expect(screen.getByText('Excellent risk-adjusted returns')).toBeInTheDocument()
  })

  it('renders with good threshold', () => {
    render(
      <SharpeRatioGauge
        value={1.2}
        thresholdLevel="good"
        interpretation="Good risk-adjusted returns"
      />
    )

    expect(screen.getByText('1.20')).toBeInTheDocument()
    expect(screen.getByText('Good')).toBeInTheDocument()
  })

  it('renders with acceptable threshold', () => {
    render(
      <SharpeRatioGauge
        value={0.75}
        thresholdLevel="acceptable"
        interpretation="Acceptable risk-adjusted returns"
      />
    )

    expect(screen.getByText('0.75')).toBeInTheDocument()
    expect(screen.getByText('Acceptable')).toBeInTheDocument()
  })

  it('renders with poor threshold', () => {
    render(
      <SharpeRatioGauge
        value={0.3}
        thresholdLevel="poor"
        interpretation="Poor risk-adjusted returns"
      />
    )

    expect(screen.getByText('0.30')).toBeInTheDocument()
    expect(screen.getByText('Poor')).toBeInTheDocument()
  })

  it('displays all threshold labels in legend', () => {
    render(
      <SharpeRatioGauge
        value={1.5}
        thresholdLevel="excellent"
        interpretation="Test interpretation"
      />
    )

    expect(screen.getByText('Outstanding')).toBeInTheDocument()
    expect(screen.getByText('Excellent')).toBeInTheDocument()
    expect(screen.getByText('Good')).toBeInTheDocument()
    expect(screen.getByText('Acceptable')).toBeInTheDocument()
    expect(screen.getByText('Poor')).toBeInTheDocument()
  })

  it('renders SVG gauge element', () => {
    const { container } = render(
      <SharpeRatioGauge
        value={1.5}
        thresholdLevel="excellent"
        interpretation="Test"
      />
    )

    const svg = container.querySelector('svg')
    expect(svg).toBeInTheDocument()
    expect(svg).toHaveAttribute('viewBox', '0 0 200 120')
  })

  it('formats value to 2 decimal places', () => {
    render(
      <SharpeRatioGauge
        value={1.678945}
        thresholdLevel="excellent"
        interpretation="Test"
      />
    )

    expect(screen.getByText('1.68')).toBeInTheDocument()
  })
})
