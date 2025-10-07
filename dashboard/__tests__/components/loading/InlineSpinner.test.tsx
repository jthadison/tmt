/**
 * Inline Spinner Tests
 * Story 9.1: AC3 - Inline spinner for component-level loading
 */

import { render, screen } from '@testing-library/react';
import { InlineSpinner } from '@/components/loading/InlineSpinner';

describe('InlineSpinner', () => {
  it('renders with default props', () => {
    render(<InlineSpinner />);
    expect(screen.getByTestId('inline-spinner')).toBeInTheDocument();
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('renders with custom text', () => {
    render(<InlineSpinner text="Fetching data..." />);
    expect(screen.getByText('Fetching data...')).toBeInTheDocument();
  });

  it('renders with small size', () => {
    const { container } = render(<InlineSpinner size="sm" />);
    const spinner = container.querySelector('svg');
    expect(spinner).toHaveClass('h-4', 'w-4');
  });

  it('renders with medium size (default)', () => {
    const { container } = render(<InlineSpinner size="md" />);
    const spinner = container.querySelector('svg');
    expect(spinner).toHaveClass('h-5', 'w-5');
  });

  it('renders with large size', () => {
    const { container } = render(<InlineSpinner size="lg" />);
    const spinner = container.querySelector('svg');
    expect(spinner).toHaveClass('h-6', 'w-6');
  });

  it('has accessible markup', () => {
    render(<InlineSpinner text="Loading content" />);
    const spinner = screen.getByTestId('inline-spinner');
    expect(spinner).toHaveAttribute('role', 'status');
    expect(spinner).toHaveAttribute('aria-label', 'Loading content');
  });

  it('renders spinner icon', () => {
    render(<InlineSpinner />);
    expect(screen.getByTestId('spinner-icon')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<InlineSpinner className="custom-class" />);
    const spinner = screen.getByTestId('inline-spinner');
    expect(spinner).toHaveClass('custom-class');
  });

  it('has spinning animation', () => {
    const { container } = render(<InlineSpinner />);
    const spinner = container.querySelector('svg');
    expect(spinner).toHaveClass('animate-spin');
  });
});
