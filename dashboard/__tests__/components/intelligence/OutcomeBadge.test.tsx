/**
 * Unit tests for OutcomeBadge component
 * Story 7.2: AC2
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { OutcomeBadge } from '@/components/intelligence/OutcomeBadge';

describe('OutcomeBadge', () => {
  test('renders WIN badge with profit', () => {
    render(<OutcomeBadge outcome="WIN" profitLoss={125.50} />);

    expect(screen.getByText('WIN')).toBeInTheDocument();
    expect(screen.getByText('+$125.50')).toBeInTheDocument();
  });

  test('renders LOSS badge with loss', () => {
    render(<OutcomeBadge outcome="LOSS" profitLoss={-45.20} />);

    const badge = screen.getByTestId('outcome-badge');
    expect(screen.getByText('LOSS')).toBeInTheDocument();
    expect(badge.textContent).toContain('-45.20');
  });

  test('renders BREAKEVEN badge', () => {
    render(<OutcomeBadge outcome="BREAKEVEN" profitLoss={0} />);

    expect(screen.getByText('BREAKEVEN')).toBeInTheDocument();
    expect(screen.getByText('+$0.00')).toBeInTheDocument();
  });

  test('renders without profit/loss when not provided', () => {
    render(<OutcomeBadge outcome="WIN" />);

    expect(screen.getByText('WIN')).toBeInTheDocument();
    expect(screen.queryByText(/\$/)).not.toBeInTheDocument();
  });

  test('applies correct styling for WIN', () => {
    render(<OutcomeBadge outcome="WIN" profitLoss={100} />);

    const badge = screen.getByTestId('outcome-badge');
    expect(badge).toHaveClass('bg-green-100');
  });

  test('applies correct styling for LOSS', () => {
    render(<OutcomeBadge outcome="LOSS" profitLoss={-50} />);

    const badge = screen.getByTestId('outcome-badge');
    expect(badge).toHaveClass('bg-red-100');
  });

  test('applies correct styling for BREAKEVEN', () => {
    render(<OutcomeBadge outcome="BREAKEVEN" />);

    const badge = screen.getByTestId('outcome-badge');
    expect(badge).toHaveClass('bg-gray-100');
  });
});
