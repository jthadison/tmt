/**
 * Unit tests for PatternTooltip component
 * Story 7.2: AC6
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { PatternTooltip } from '@/components/intelligence/PatternTooltip';
import { PatternData } from '@/types/intelligence';

describe('PatternTooltip', () => {
  const mockPattern: PatternData = {
    id: 'pattern-123',
    symbol: 'EUR_USD',
    patternType: 'wyckoff-accumulation',
    phase: 'Phase E',
    confidence: 78,
    status: 'confirmed',
    detectedAt: Date.now(),
    coordinates: {
      entryPoint: { price: 1.0850, timestamp: Date.now(), label: 'Entry' }
    },
    description: 'Wyckoff Accumulation Phase E detected',
    keyCharacteristics: [
      'Spring action completed',
      'Sign of Strength (SOS) confirmed',
      'Price above Creek'
    ],
    riskRewardRatio: 3.5
  };

  test('renders when visible is true', () => {
    render(
      <PatternTooltip
        pattern={mockPattern}
        position={{ x: 100, y: 100 }}
        visible={true}
      />
    );

    expect(screen.getByTestId('pattern-tooltip')).toBeInTheDocument();
  });

  test('does not render when visible is false', () => {
    render(
      <PatternTooltip
        pattern={mockPattern}
        position={{ x: 100, y: 100 }}
        visible={false}
      />
    );

    expect(screen.queryByTestId('pattern-tooltip')).not.toBeInTheDocument();
  });

  test('displays formatted pattern type', () => {
    render(
      <PatternTooltip
        pattern={mockPattern}
        position={{ x: 100, y: 100 }}
        visible={true}
      />
    );

    expect(screen.getByText('Wyckoff Accumulation - Phase E')).toBeInTheDocument();
  });

  test('displays pattern status badge', () => {
    render(
      <PatternTooltip
        pattern={mockPattern}
        position={{ x: 100, y: 100 }}
        visible={true}
      />
    );

    expect(screen.getByTestId('pattern-status-badge')).toBeInTheDocument();
    expect(screen.getByText('Confirmed')).toBeInTheDocument();
  });

  test('displays confidence meter', () => {
    render(
      <PatternTooltip
        pattern={mockPattern}
        position={{ x: 100, y: 100 }}
        visible={true}
      />
    );

    expect(screen.getByTestId('confidence-meter')).toBeInTheDocument();
  });

  test('displays all key characteristics', () => {
    render(
      <PatternTooltip
        pattern={mockPattern}
        position={{ x: 100, y: 100 }}
        visible={true}
      />
    );

    expect(screen.getByText(/Spring action completed/)).toBeInTheDocument();
    expect(screen.getByText(/Sign of Strength/)).toBeInTheDocument();
    expect(screen.getByText(/Price above Creek/)).toBeInTheDocument();
  });

  test('displays risk:reward ratio when available', () => {
    render(
      <PatternTooltip
        pattern={mockPattern}
        position={{ x: 100, y: 100 }}
        visible={true}
      />
    );

    expect(screen.getByText(/Risk:Reward:/)).toBeInTheDocument();
    expect(screen.getByText('1:3.5')).toBeInTheDocument();
  });

  test('does not display risk:reward when not available', () => {
    const patternWithoutRR = { ...mockPattern, riskRewardRatio: undefined };

    render(
      <PatternTooltip
        pattern={patternWithoutRR}
        position={{ x: 100, y: 100 }}
        visible={true}
      />
    );

    expect(screen.queryByText(/Risk:Reward:/)).not.toBeInTheDocument();
  });

  test('displays correct status for forming pattern', () => {
    const formingPattern = { ...mockPattern, status: 'forming' as const };

    render(
      <PatternTooltip
        pattern={formingPattern}
        position={{ x: 100, y: 100 }}
        visible={true}
      />
    );

    expect(screen.getByText('Forming')).toBeInTheDocument();
  });

  test('displays correct status for invalidated pattern', () => {
    const invalidatedPattern = { ...mockPattern, status: 'invalidated' as const };

    render(
      <PatternTooltip
        pattern={invalidatedPattern}
        position={{ x: 100, y: 100 }}
        visible={true}
      />
    );

    expect(screen.getByText('Invalidated')).toBeInTheDocument();
  });

  test('positions tooltip correctly', () => {
    const { container } = render(
      <PatternTooltip
        pattern={mockPattern}
        position={{ x: 200, y: 300 }}
        visible={true}
      />
    );

    const tooltip = container.querySelector('.pattern-tooltip');
    expect(tooltip).toHaveStyle({ left: '200px', top: '300px' });
  });
});
