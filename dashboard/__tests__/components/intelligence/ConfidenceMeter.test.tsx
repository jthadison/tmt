/**
 * ConfidenceMeter Component Tests
 *
 * Story 7.1: AC4 - Test confidence meter with 5 color levels
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { ConfidenceMeter } from '@/components/intelligence/ConfidenceMeter';

describe('ConfidenceMeter', () => {
  describe('Color Level Mapping', () => {
    it('displays very low confidence (0-29%) in red', () => {
      render(<ConfidenceMeter confidence={25} />);

      const bar = screen.getByTestId('confidence-bar');
      expect(bar).toHaveStyle({ backgroundColor: '#ef4444' });
      expect(screen.getByText(/25% - Very Low/)).toBeInTheDocument();
    });

    it('displays low confidence (30-49%) in orange', () => {
      render(<ConfidenceMeter confidence={45} />);

      const bar = screen.getByTestId('confidence-bar');
      expect(bar).toHaveStyle({ backgroundColor: '#f59e0b' });
      expect(screen.getByText(/45% - Low/)).toBeInTheDocument();
    });

    it('displays medium confidence (50-69%) in yellow', () => {
      render(<ConfidenceMeter confidence={65} />);

      const bar = screen.getByTestId('confidence-bar');
      expect(bar).toHaveStyle({ backgroundColor: '#eab308' });
      expect(screen.getByText(/65% - Medium/)).toBeInTheDocument();
    });

    it('displays high confidence (70-89%) in light green', () => {
      render(<ConfidenceMeter confidence={85} />);

      const bar = screen.getByTestId('confidence-bar');
      expect(bar).toHaveStyle({ backgroundColor: '#84cc16' });
      expect(screen.getByText(/85% - High/)).toBeInTheDocument();
    });

    it('displays very high confidence (90-100%) in dark green', () => {
      render(<ConfidenceMeter confidence={95} />);

      const bar = screen.getByTestId('confidence-bar');
      expect(bar).toHaveStyle({ backgroundColor: '#22c55e' });
      expect(screen.getByText(/95% - Very High/)).toBeInTheDocument();
    });
  });

  describe('Width Calculation', () => {
    it('sets bar width to match confidence percentage', () => {
      render(<ConfidenceMeter confidence={75} />);

      const bar = screen.getByTestId('confidence-bar');
      expect(bar).toHaveStyle({ width: '75%' });
    });

    it('handles 0% confidence', () => {
      render(<ConfidenceMeter confidence={0} />);

      const bar = screen.getByTestId('confidence-bar');
      expect(bar).toHaveStyle({ width: '0%' });
    });

    it('handles 100% confidence', () => {
      render(<ConfidenceMeter confidence={100} />);

      const bar = screen.getByTestId('confidence-bar');
      expect(bar).toHaveStyle({ width: '100%' });
    });
  });

  describe('Label Display', () => {
    it('shows label by default', () => {
      render(<ConfidenceMeter confidence={75} />);

      expect(screen.getByText('Confidence')).toBeInTheDocument();
      expect(screen.getByText('75% - High')).toBeInTheDocument();
    });

    it('hides label when showLabel is false', () => {
      render(<ConfidenceMeter confidence={75} showLabel={false} />);

      expect(screen.queryByText('Confidence')).not.toBeInTheDocument();
      expect(screen.queryByText('75% - High')).not.toBeInTheDocument();
    });
  });

  describe('Size Variants', () => {
    it('renders small size', () => {
      const { container } = render(<ConfidenceMeter confidence={75} size="sm" />);

      const meter = container.querySelector('.h-2');
      expect(meter).toBeInTheDocument();
    });

    it('renders medium size by default', () => {
      const { container } = render(<ConfidenceMeter confidence={75} />);

      const meter = container.querySelector('.h-4');
      expect(meter).toBeInTheDocument();
    });

    it('renders large size', () => {
      const { container } = render(<ConfidenceMeter confidence={75} size="lg" />);

      const meter = container.querySelector('.h-6');
      expect(meter).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('includes proper ARIA attributes', () => {
      render(<ConfidenceMeter confidence={75} />);

      const bar = screen.getByTestId('confidence-bar');
      expect(bar).toHaveAttribute('role', 'progressbar');
      expect(bar).toHaveAttribute('aria-valuenow', '75');
      expect(bar).toHaveAttribute('aria-valuemin', '0');
      expect(bar).toHaveAttribute('aria-valuemax', '100');
      expect(bar).toHaveAttribute('aria-label', 'Confidence: 75% - High');
    });
  });

  describe('Edge Cases', () => {
    it.each([
      [0, 'very-low', '#ef4444'],
      [29, 'very-low', '#ef4444'],
      [30, 'low', '#f59e0b'],
      [49, 'low', '#f59e0b'],
      [50, 'medium', '#eab308'],
      [69, 'medium', '#eab308'],
      [70, 'high', '#84cc16'],
      [89, 'high', '#84cc16'],
      [90, 'very-high', '#22c55e'],
      [100, 'very-high', '#22c55e']
    ])('confidence %i maps to %s level with color %s', (confidence, level, color) => {
      render(<ConfidenceMeter confidence={confidence} />);

      const bar = screen.getByTestId('confidence-bar');
      expect(bar).toHaveStyle({ backgroundColor: color });
    });
  });
});
