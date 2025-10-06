/**
 * Tests for StabilityScores Component - Story 8.1
 */

import React from 'react'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { StabilityScores } from '@/components/analytics/StabilityScores'
import { StabilityMetrics } from '@/types/analytics'

describe('StabilityScores', () => {
  it('renders all three metrics', () => {
    const metrics: StabilityMetrics = {
      walkForwardScore: 75,
      overfittingScore: 0.25,
      outOfSampleValidation: 88,
    }

    render(<StabilityScores metrics={metrics} />)

    expect(screen.getByText('Walk-Forward Stability')).toBeInTheDocument()
    expect(screen.getByText('Overfitting Score')).toBeInTheDocument()
    expect(screen.getByText('Out-of-Sample Validation')).toBeInTheDocument()
  })

  it('shows excellent walk-forward stability', () => {
    const metrics: StabilityMetrics = {
      walkForwardScore: 80,
      overfittingScore: 0.2,
      outOfSampleValidation: 90,
    }

    render(<StabilityScores metrics={metrics} />)

    expect(screen.getByText('80')).toBeInTheDocument()
    expect(screen.getByText('Excellent consistency across time periods')).toBeInTheDocument()
    expect(screen.getByText('✓ Performance consistent over time')).toBeInTheDocument()
  })

  it('shows acceptable walk-forward stability', () => {
    const metrics: StabilityMetrics = {
      walkForwardScore: 50,
      overfittingScore: 0.5,
      outOfSampleValidation: 75,
    }

    render(<StabilityScores metrics={metrics} />)

    expect(screen.getByText('50')).toBeInTheDocument()
    expect(screen.getByText('Acceptable performance stability')).toBeInTheDocument()
    expect(screen.getByText('⚠ Some performance variation')).toBeInTheDocument()
  })

  it('shows poor walk-forward stability', () => {
    const metrics: StabilityMetrics = {
      walkForwardScore: 20,
      overfittingScore: 0.9,
      outOfSampleValidation: 50,
    }

    render(<StabilityScores metrics={metrics} />)

    expect(screen.getByText('20')).toBeInTheDocument()
    expect(screen.getByText('Needs improvement - inconsistent performance')).toBeInTheDocument()
    expect(screen.getByText('✗ High performance inconsistency')).toBeInTheDocument()
  })

  it('shows low overfitting risk', () => {
    const metrics: StabilityMetrics = {
      walkForwardScore: 75,
      overfittingScore: 0.2,
      outOfSampleValidation: 88,
    }

    render(<StabilityScores metrics={metrics} />)

    expect(screen.getByText('0.20')).toBeInTheDocument()
    expect(screen.getByText('Low overfitting risk - good generalization')).toBeInTheDocument()
    expect(screen.getByText('✓ Low overfitting risk')).toBeInTheDocument()
  })

  it('shows moderate overfitting risk', () => {
    const metrics: StabilityMetrics = {
      walkForwardScore: 60,
      overfittingScore: 0.5,
      outOfSampleValidation: 70,
    }

    render(<StabilityScores metrics={metrics} />)

    expect(screen.getByText('0.50')).toBeInTheDocument()
    expect(screen.getByText('Moderate overfitting risk - monitor closely')).toBeInTheDocument()
    expect(screen.getByText('⚠ Moderate overfitting risk')).toBeInTheDocument()
  })

  it('shows high overfitting risk', () => {
    const metrics: StabilityMetrics = {
      walkForwardScore: 40,
      overfittingScore: 0.85,
      outOfSampleValidation: 60,
    }

    render(<StabilityScores metrics={metrics} />)

    expect(screen.getByText('0.85')).toBeInTheDocument()
    expect(screen.getByText('High overfitting risk - strategy may not generalize')).toBeInTheDocument()
    expect(screen.getByText('✗ High overfitting detected')).toBeInTheDocument()
  })

  it('shows strong out-of-sample validation', () => {
    const metrics: StabilityMetrics = {
      walkForwardScore: 75,
      overfittingScore: 0.25,
      outOfSampleValidation: 90,
    }

    render(<StabilityScores metrics={metrics} />)

    expect(screen.getByText('90%')).toBeInTheDocument()
    expect(screen.getByText('Strong generalization to unseen data')).toBeInTheDocument()
    expect(screen.getByText('✓ Strong generalization')).toBeInTheDocument()
  })

  it('shows good out-of-sample validation', () => {
    const metrics: StabilityMetrics = {
      walkForwardScore: 65,
      overfittingScore: 0.4,
      outOfSampleValidation: 75,
    }

    render(<StabilityScores metrics={metrics} />)

    expect(screen.getByText('75%')).toBeInTheDocument()
    expect(screen.getByText('Good out-of-sample performance')).toBeInTheDocument()
    expect(screen.getByText('✓ Good validation')).toBeInTheDocument()
  })

  it('shows limited out-of-sample validation', () => {
    const metrics: StabilityMetrics = {
      walkForwardScore: 50,
      overfittingScore: 0.6,
      outOfSampleValidation: 65,
    }

    render(<StabilityScores metrics={metrics} />)

    expect(screen.getByText('65%')).toBeInTheDocument()
    expect(screen.getByText('Limited out-of-sample validation')).toBeInTheDocument()
    expect(screen.getByText('⚠ Limited validation')).toBeInTheDocument()
  })

  it('displays explanation section', () => {
    const metrics: StabilityMetrics = {
      walkForwardScore: 75,
      overfittingScore: 0.25,
      outOfSampleValidation: 88,
    }

    render(<StabilityScores metrics={metrics} />)

    expect(screen.getByText('Understanding These Metrics')).toBeInTheDocument()
  })
})
