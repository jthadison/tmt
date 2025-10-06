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
    // Text appears in both the main display and the legend, use getAllByText
    expect(screen.getAllByText('Outstanding').length).toBeGreaterThan(0)
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
    // Text appears in both the main display and the legend, use getAllByText
    expect(screen.getAllByText('Excellent').length).toBeGreaterThan(0)
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
    // Text appears in both the main display and the legend, use getAllByText
    expect(screen.getAllByText('Good').length).toBeGreaterThan(0)
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
    // Text appears in both the main display and the legend, use getAllByText
    expect(screen.getAllByText('Acceptable').length).toBeGreaterThan(0)
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
    // Text appears in both the main display and the legend, use getAllByText
    expect(screen.getAllByText('Poor').length).toBeGreaterThan(0)
  })

  it('displays all threshold labels in legend', () => {
    render(
      <SharpeRatioGauge
        value={1.5}
        thresholdLevel="excellent"
        interpretation="Test interpretation"
      />
    )

    // All labels appear in the legend, check they exist
    expect(screen.getAllByText('Outstanding').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Excellent').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Good').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Acceptable').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Poor').length).toBeGreaterThan(0)
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
