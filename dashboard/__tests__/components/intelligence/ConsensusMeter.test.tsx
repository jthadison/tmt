/**
 * ConsensusMeter Component Tests
 *
 * Story 7.1: AC6 - Test consensus meter with circular progress
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { ConsensusMeter } from '@/components/intelligence/ConsensusMeter';

describe('ConsensusMeter', () => {
  describe('Percentage Display', () => {
    it('displays correct percentage in center', () => {
      render(<ConsensusMeter percentage={75} threshold={70} />);

      expect(screen.getByTestId('consensus-percentage')).toHaveTextContent('75%');
    });

    it('displays threshold text when provided', () => {
      render(<ConsensusMeter percentage={75} threshold={70} />);

      expect(screen.getByText('Threshold: 70%')).toBeInTheDocument();
    });

    it('does not display threshold when not provided', () => {
      render(<ConsensusMeter percentage={75} />);

      expect(screen.queryByText(/Threshold:/)).not.toBeInTheDocument();
    });
  });

  describe('Color Mapping', () => {
    it('displays red for low consensus (<50%)', () => {
      render(<ConsensusMeter percentage={45} threshold={70} />);

      const percentage = screen.getByTestId('consensus-percentage');
      expect(percentage).toHaveStyle({ color: '#ef4444' });
    });

    it('displays yellow for moderate consensus (50-69%)', () => {
      render(<ConsensusMeter percentage={65} threshold={70} />);

      const percentage = screen.getByTestId('consensus-percentage');
      expect(percentage).toHaveStyle({ color: '#eab308' });
    });

    it('displays light green for good consensus (70-89%)', () => {
      render(<ConsensusMeter percentage={85} threshold={70} />);

      const percentage = screen.getByTestId('consensus-percentage');
      expect(percentage).toHaveStyle({ color: '#84cc16' });
    });

    it('displays dark green for strong consensus (90-100%)', () => {
      render(<ConsensusMeter percentage={95} threshold={70} />);

      const percentage = screen.getByTestId('consensus-percentage');
      expect(percentage).toHaveStyle({ color: '#22c55e' });
    });
  });

  describe('Progress Circle', () => {
    it('renders progress circle', () => {
      render(<ConsensusMeter percentage={75} />);

      const progressCircle = screen.getByTestId('consensus-progress');
      expect(progressCircle).toBeInTheDocument();
    });

    it('calculates correct stroke-dashoffset for percentage', () => {
      render(<ConsensusMeter percentage={75} />);

      const radius = 70;
      const circumference = 2 * Math.PI * radius;
      const expectedOffset = circumference - (75 / 100) * circumference;

      const progressCircle = screen.getByTestId('consensus-progress');
      expect(progressCircle).toHaveAttribute('stroke-dashoffset', expectedOffset.toString());
    });
  });

  describe('Threshold Indicator', () => {
    it('renders threshold indicator when threshold provided', () => {
      render(<ConsensusMeter percentage={75} threshold={70} />);

      const thresholdIndicator = screen.getByTestId('consensus-threshold');
      expect(thresholdIndicator).toBeInTheDocument();
    });

    it('does not render threshold indicator without threshold', () => {
      render(<ConsensusMeter percentage={75} />);

      expect(screen.queryByTestId('consensus-threshold')).not.toBeInTheDocument();
    });

    it('calculates correct threshold position', () => {
      render(<ConsensusMeter percentage={75} threshold={70} />);

      const radius = 70;
      const circumference = 2 * Math.PI * radius;
      const expectedOffset = circumference - (70 / 100) * circumference;

      const thresholdIndicator = screen.getByTestId('consensus-threshold');
      expect(thresholdIndicator).toHaveAttribute('stroke-dashoffset', expectedOffset.toString());
    });
  });

  describe('Accessibility', () => {
    it('includes aria-label on SVG', () => {
      render(<ConsensusMeter percentage={75} threshold={70} />);

      const svg = screen.getByLabelText('Consensus: 75%');
      expect(svg).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles 0% consensus', () => {
      render(<ConsensusMeter percentage={0} threshold={70} />);

      expect(screen.getByTestId('consensus-percentage')).toHaveTextContent('0%');
    });

    it('handles 100% consensus', () => {
      render(<ConsensusMeter percentage={100} threshold={70} />);

      expect(screen.getByTestId('consensus-percentage')).toHaveTextContent('100%');
    });

    it.each([
      [45, '#ef4444'],
      [65, '#eab308'],
      [85, '#84cc16'],
      [95, '#22c55e']
    ])('percentage %i displays color %s', (percentage, expectedColor) => {
      render(<ConsensusMeter percentage={percentage} />);

      const percentageElement = screen.getByTestId('consensus-percentage');
      expect(percentageElement).toHaveStyle({ color: expectedColor });
    });
  });
});
