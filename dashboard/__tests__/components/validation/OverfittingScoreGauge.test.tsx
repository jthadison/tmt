/**
 * OverfittingScoreGauge Component Tests - Story 11.8
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { OverfittingScoreGauge } from '@/components/validation/OverfittingScoreGauge';

describe('OverfittingScoreGauge', () => {
  it('renders loading state', () => {
    render(<OverfittingScoreGauge score={0} loading={true} />);
    const loadingElement = document.querySelector('.animate-pulse');
    expect(loadingElement).toBeInTheDocument();
  });

  it('displays overfitting score correctly', () => {
    render(<OverfittingScoreGauge score={0.274} />);
    expect(screen.getByText('0.274')).toBeInTheDocument();
  });

  it('shows green status for healthy score (< 0.3)', () => {
    render(<OverfittingScoreGauge score={0.25} />);
    expect(screen.getByText('✅ Healthy')).toBeInTheDocument();
  });

  it('shows yellow status for warning score (0.3-0.5)', () => {
    render(<OverfittingScoreGauge score={0.4} />);
    expect(screen.getByText('⚠️ Warning')).toBeInTheDocument();
  });

  it('shows red status for critical score (> 0.5)', () => {
    render(<OverfittingScoreGauge score={0.6} />);
    expect(screen.getByText('❌ Critical')).toBeInTheDocument();
  });

  it('displays custom thresholds', () => {
    const thresholds = { warning: 0.4, critical: 0.6 };
    render(<OverfittingScoreGauge score={0.3} thresholds={thresholds} />);
    expect(screen.getByText('0.40')).toBeInTheDocument();
    expect(screen.getByText('0.60')).toBeInTheDocument();
  });

  it('renders gauge visualization', () => {
    render(<OverfittingScoreGauge score={0.5} />);
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('displays description text', () => {
    render(<OverfittingScoreGauge score={0.2} />);
    expect(screen.getByText(/Overfitting score measures/i)).toBeInTheDocument();
  });
});
