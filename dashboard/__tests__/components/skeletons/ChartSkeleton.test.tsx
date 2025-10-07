/**
 * Chart Skeleton Tests
 * Story 9.1: AC1 - Skeleton screens for major components
 */

import { render } from '@testing-library/react';
import { ChartSkeleton } from '@/components/skeletons/ChartSkeleton';

describe('ChartSkeleton', () => {
  it('renders with data-testid', () => {
    const { getByTestId } = render(<ChartSkeleton />);
    expect(getByTestId('chart-skeleton')).toBeInTheDocument();
  });

  it('renders with shimmer animation elements', () => {
    const { container } = render(<ChartSkeleton />);
    const skeletons = container.querySelectorAll('.skeleton');

    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('includes chart structure elements', () => {
    const { container } = render(<ChartSkeleton />);

    // Should have title placeholder
    const skeletons = container.querySelectorAll('.skeleton');
    expect(skeletons.length).toBeGreaterThan(10); // Title + Y-axis labels + X-axis labels + legend items

    // Should have grid structure
    const gridLines = container.querySelectorAll('.border-t');
    expect(gridLines.length).toBeGreaterThan(0);
  });

  it('renders Y-axis label placeholders', () => {
    const { container } = render(<ChartSkeleton />);

    // 5 Y-axis labels expected
    const yAxisLabels = container.querySelectorAll('.absolute.left-0 .skeleton');
    expect(yAxisLabels.length).toBe(5);
  });

  it('renders X-axis label placeholders', () => {
    const { container } = render(<ChartSkeleton />);

    // 4 X-axis labels expected
    const xAxisContainer = container.querySelector('.absolute.bottom-0.left-16');
    const xAxisLabels = xAxisContainer?.querySelectorAll('.skeleton');
    expect(xAxisLabels?.length).toBe(4);
  });

  it('renders legend placeholders', () => {
    const { container } = render(<ChartSkeleton />);

    // 2 legend items with circle + text each
    const legendCircles = container.querySelectorAll('.skeleton.h-3.w-3');
    expect(legendCircles.length).toBeGreaterThanOrEqual(2);
  });
});
