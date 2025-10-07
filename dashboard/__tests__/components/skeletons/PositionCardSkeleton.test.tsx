/**
 * Position Card Skeleton Tests
 * Story 9.1: AC1 - Skeleton screens for major components
 */

import { render } from '@testing-library/react';
import { PositionCardSkeleton } from '@/components/skeletons/PositionCardSkeleton';

describe('PositionCardSkeleton', () => {
  it('renders with shimmer animation', () => {
    const { container } = render(<PositionCardSkeleton />);
    const skeletons = container.querySelectorAll('.skeleton');

    expect(skeletons.length).toBeGreaterThan(0);

    // Check that skeleton elements exist
    skeletons.forEach((skeleton) => {
      expect(skeleton).toHaveClass('skeleton');
    });
  });

  it('matches position card layout structure', () => {
    const { container } = render(<PositionCardSkeleton />);

    // Should have symbol placeholder
    expect(container.querySelector('[data-testid="symbol-skeleton"]')).toBeInTheDocument();

    // Should have price placeholder
    expect(container.querySelector('[data-testid="price-skeleton"]')).toBeInTheDocument();

    // Should have profit/loss placeholder
    expect(container.querySelector('[data-testid="pnl-skeleton"]')).toBeInTheDocument();
  });

  it('renders with correct data-testid', () => {
    const { getByTestId } = render(<PositionCardSkeleton />);
    expect(getByTestId('position-card-skeleton')).toBeInTheDocument();
  });

  it('has correct number of skeleton elements', () => {
    const { container } = render(<PositionCardSkeleton />);
    const skeletons = container.querySelectorAll('.skeleton');

    // Symbol (1) + Badge (1) + Price (1) + PnL label (1) + PnL value (1) = 5 total
    expect(skeletons.length).toBe(5);
  });
});
