/**
 * Dashboard Skeleton Tests
 * Story 9.1: AC1 - Skeleton screens for major components
 */

import { render } from '@testing-library/react';
import { DashboardSkeleton } from '@/components/skeletons/DashboardSkeleton';

describe('DashboardSkeleton', () => {
  it('renders with data-testid', () => {
    const { getByTestId } = render(<DashboardSkeleton />);
    expect(getByTestId('dashboard-skeleton')).toBeInTheDocument();
  });

  it('renders header skeleton', () => {
    const { container } = render(<DashboardSkeleton />);

    const header = container.querySelector('header');
    expect(header).toBeInTheDocument();

    // Header should have logo placeholder and action buttons
    const headerSkeletons = header?.querySelectorAll('.skeleton');
    expect(headerSkeletons && headerSkeletons.length).toBeGreaterThan(0);
  });

  it('renders stats row with 4 cards', () => {
    const { container } = render(<DashboardSkeleton />);

    // Stats row should have 4 stat cards
    const statsGrid = container.querySelector('.grid.grid-cols-1.md\\:grid-cols-4');
    const statCards = statsGrid?.querySelectorAll('.bg-white');
    expect(statCards?.length).toBe(4);
  });

  it('renders chart skeleton', () => {
    const { getByTestId } = render(<DashboardSkeleton />);
    expect(getByTestId('chart-skeleton')).toBeInTheDocument();
  });

  it('renders 6 position card skeletons', () => {
    const { container } = render(<DashboardSkeleton />);

    const positionCardSkeletons = container.querySelectorAll('[data-testid="position-card-skeleton"]');
    expect(positionCardSkeletons.length).toBe(6);
  });

  it('renders 8 agent card skeletons', () => {
    const { container } = render(<DashboardSkeleton />);

    const agentCardSkeletons = container.querySelectorAll('[data-testid="agent-card-skeleton"]');
    expect(agentCardSkeletons.length).toBe(8);
  });

  it('has full dashboard structure', () => {
    const { container } = render(<DashboardSkeleton />);

    // Check for main sections
    expect(container.querySelector('header')).toBeInTheDocument();
    expect(container.querySelector('.container')).toBeInTheDocument();

    // All skeleton elements should have shimmer animation
    const allSkeletons = container.querySelectorAll('.skeleton');
    expect(allSkeletons.length).toBeGreaterThan(20);
  });
});
