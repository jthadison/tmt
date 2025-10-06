/**
 * DecisionBadge Component Tests
 *
 * Story 7.1: AC7 - Test decision badge with threshold explanation
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { DecisionBadge } from '@/components/intelligence/DecisionBadge';

describe('DecisionBadge', () => {
  describe('Threshold Met Scenario', () => {
    it('displays checkmark icon when threshold is met', () => {
      render(
        <DecisionBadge
          decision="BUY"
          thresholdMet={true}
          threshold={70}
          actualPercentage={75}
        />
      );

      expect(screen.getByTestId('check-icon')).toBeInTheDocument();
      expect(screen.queryByTestId('warning-icon')).not.toBeInTheDocument();
    });

    it('displays threshold met message with correct percentages', () => {
      render(
        <DecisionBadge
          decision="BUY"
          thresholdMet={true}
          threshold={70}
          actualPercentage={75}
        />
      );

      expect(screen.getByTestId('threshold-met')).toHaveTextContent(
        '✓ Threshold met (75% ≥ 70% required)'
      );
    });
  });

  describe('Threshold Not Met Scenario', () => {
    it('displays warning icon when threshold is not met', () => {
      render(
        <DecisionBadge
          decision="BUY"
          thresholdMet={false}
          threshold={70}
          actualPercentage={55}
        />
      );

      expect(screen.getByTestId('warning-icon')).toBeInTheDocument();
      expect(screen.queryByTestId('check-icon')).not.toBeInTheDocument();
    });

    it('displays threshold not met message with correct percentages', () => {
      render(
        <DecisionBadge
          decision="BUY"
          thresholdMet={false}
          threshold={70}
          actualPercentage={55}
        />
      );

      expect(screen.getByTestId('threshold-not-met')).toHaveTextContent(
        '⚠ Threshold NOT met (55% < 70% required)'
      );
    });

    it('applies warning color to threshold not met message', () => {
      render(
        <DecisionBadge
          decision="BUY"
          thresholdMet={false}
          threshold={70}
          actualPercentage={55}
        />
      );

      const message = screen.getByTestId('threshold-not-met');
      expect(message).toHaveClass('text-yellow-700');
    });
  });

  describe('Decision Display', () => {
    it('displays BUY decision', () => {
      render(
        <DecisionBadge
          decision="BUY"
          thresholdMet={true}
          threshold={70}
          actualPercentage={75}
        />
      );

      expect(screen.getByTestId('decision-text')).toHaveTextContent('BUY');
    });

    it('displays SELL decision', () => {
      render(
        <DecisionBadge
          decision="SELL"
          thresholdMet={true}
          threshold={70}
          actualPercentage={75}
        />
      );

      expect(screen.getByTestId('decision-text')).toHaveTextContent('SELL');
    });

    it('displays NEUTRAL decision', () => {
      render(
        <DecisionBadge
          decision="NEUTRAL"
          thresholdMet={true}
          threshold={70}
          actualPercentage={75}
        />
      );

      expect(screen.getByTestId('decision-text')).toHaveTextContent('NEUTRAL');
    });
  });

  describe('Color Coding', () => {
    it('applies green styling for BUY decision', () => {
      render(
        <DecisionBadge
          decision="BUY"
          thresholdMet={true}
          threshold={70}
          actualPercentage={75}
        />
      );

      const decisionText = screen.getByTestId('decision-text');
      expect(decisionText).toHaveClass('text-green-700');
    });

    it('applies red styling for SELL decision', () => {
      render(
        <DecisionBadge
          decision="SELL"
          thresholdMet={true}
          threshold={70}
          actualPercentage={75}
        />
      );

      const decisionText = screen.getByTestId('decision-text');
      expect(decisionText).toHaveClass('text-red-700');
    });

    it('applies gray styling for NEUTRAL decision', () => {
      render(
        <DecisionBadge
          decision="NEUTRAL"
          thresholdMet={true}
          threshold={70}
          actualPercentage={75}
        />
      );

      const decisionText = screen.getByTestId('decision-text');
      expect(decisionText).toHaveClass('text-gray-700');
    });
  });

  describe('Badge Structure', () => {
    it('renders with correct data-testid', () => {
      render(
        <DecisionBadge
          decision="BUY"
          thresholdMet={true}
          threshold={70}
          actualPercentage={75}
        />
      );

      expect(screen.getByTestId('decision-badge')).toBeInTheDocument();
    });

    it('applies correct border color for BUY', () => {
      const { container } = render(
        <DecisionBadge
          decision="BUY"
          thresholdMet={true}
          threshold={70}
          actualPercentage={75}
        />
      );

      const badge = screen.getByTestId('decision-badge');
      expect(badge).toHaveClass('border-green-300');
    });

    it('applies correct background for BUY', () => {
      const { container } = render(
        <DecisionBadge
          decision="BUY"
          thresholdMet={true}
          threshold={70}
          actualPercentage={75}
        />
      );

      const badge = screen.getByTestId('decision-badge');
      expect(badge).toHaveClass('bg-green-50');
    });
  });

  describe('Edge Cases', () => {
    it('handles exact threshold match', () => {
      render(
        <DecisionBadge
          decision="BUY"
          thresholdMet={true}
          threshold={70}
          actualPercentage={70}
        />
      );

      expect(screen.getByTestId('threshold-met')).toHaveTextContent(
        '✓ Threshold met (70% ≥ 70% required)'
      );
    });

    it('handles 0% threshold', () => {
      render(
        <DecisionBadge
          decision="BUY"
          thresholdMet={true}
          threshold={0}
          actualPercentage={50}
        />
      );

      expect(screen.getByTestId('threshold-met')).toHaveTextContent(
        '✓ Threshold met (50% ≥ 0% required)'
      );
    });

    it('handles 100% consensus', () => {
      render(
        <DecisionBadge
          decision="BUY"
          thresholdMet={true}
          threshold={90}
          actualPercentage={100}
        />
      );

      expect(screen.getByTestId('threshold-met')).toHaveTextContent(
        '✓ Threshold met (100% ≥ 90% required)'
      );
    });

    it('handles SELL decision with threshold not met', () => {
      render(
        <DecisionBadge
          decision="SELL"
          thresholdMet={false}
          threshold={70}
          actualPercentage={60}
        />
      );

      expect(screen.getByTestId('decision-text')).toHaveTextContent('SELL');
      expect(screen.getByTestId('warning-icon')).toBeInTheDocument();
      expect(screen.getByTestId('threshold-not-met')).toHaveTextContent(
        '⚠ Threshold NOT met (60% < 70% required)'
      );
    });
  });
});
