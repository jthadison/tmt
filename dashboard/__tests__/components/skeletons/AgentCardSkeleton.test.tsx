/**
 * Agent Card Skeleton Tests
 * Story 9.1: AC1 - Skeleton screens for major components
 */

import { render } from '@testing-library/react';
import { AgentCardSkeleton } from '@/components/skeletons/AgentCardSkeleton';

describe('AgentCardSkeleton', () => {
  it('renders with data-testid', () => {
    const { getByTestId } = render(<AgentCardSkeleton />);
    expect(getByTestId('agent-card-skeleton')).toBeInTheDocument();
  });

  it('renders with shimmer animation', () => {
    const { container } = render(<AgentCardSkeleton />);
    const skeletons = container.querySelectorAll('.skeleton');

    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('matches agent card layout structure', () => {
    const { container } = render(<AgentCardSkeleton />);
    const skeletons = container.querySelectorAll('.skeleton');

    // Agent name + status indicator + confidence label + confidence meter + 3 reasoning lines = 7 total
    expect(skeletons.length).toBe(7);
  });

  it('renders agent name and status indicator placeholders', () => {
    const { container } = render(<AgentCardSkeleton />);

    // Name placeholder
    const namePlaceholder = container.querySelector('.skeleton.h-5.w-32');
    expect(namePlaceholder).toBeInTheDocument();

    // Status indicator (circular)
    const statusPlaceholder = container.querySelector('.skeleton.h-3.w-3.rounded-full');
    expect(statusPlaceholder).toBeInTheDocument();
  });

  it('renders confidence meter placeholders', () => {
    const { container } = render(<AgentCardSkeleton />);

    // Confidence label
    const confidenceLabel = container.querySelector('.skeleton.h-4.w-24');
    expect(confidenceLabel).toBeInTheDocument();

    // Confidence meter bar
    const confidenceMeter = container.querySelector('.skeleton.h-2.w-full');
    expect(confidenceMeter).toBeInTheDocument();
  });

  it('renders reasoning text line placeholders', () => {
    const { container } = render(<AgentCardSkeleton />);

    // 3 reasoning text lines with different widths
    const reasoningLines = container.querySelectorAll('.space-y-2 .skeleton');
    expect(reasoningLines.length).toBe(3);
  });
});
