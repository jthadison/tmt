/**
 * Progress Bar Tests
 * Story 9.1: AC5 - Progress bar for known-duration tasks
 */

import { render, screen } from '@testing-library/react';
import { ProgressBar } from '@/components/loading/ProgressBar';

describe('ProgressBar', () => {
  it('renders with progress and message', () => {
    render(<ProgressBar progress={50} message="Processing items..." />);
    expect(screen.getByTestId('progress-bar')).toBeInTheDocument();
    expect(screen.getByText('Processing items...')).toBeInTheDocument();
  });

  it('displays percentage by default', () => {
    render(<ProgressBar progress={66} message="Closing positions..." />);
    expect(screen.getByText('66%')).toBeInTheDocument();
  });

  it('hides percentage when showPercentage is false', () => {
    render(<ProgressBar progress={50} message="Loading..." showPercentage={false} />);
    expect(screen.queryByText('50%')).not.toBeInTheDocument();
  });

  it('clamps progress to 0-100 range (too low)', () => {
    render(<ProgressBar progress={-10} message="Loading..." />);
    const progressFill = screen.getByTestId('progress-bar-fill');
    expect(progressFill).toHaveStyle({ width: '0%' });
  });

  it('clamps progress to 0-100 range (too high)', () => {
    render(<ProgressBar progress={150} message="Loading..." />);
    const progressFill = screen.getByTestId('progress-bar-fill');
    expect(progressFill).toHaveStyle({ width: '100%' });
  });

  it('renders progress bar fill with correct width', () => {
    render(<ProgressBar progress={75} message="Loading..." />);
    const progressFill = screen.getByTestId('progress-bar-fill');
    expect(progressFill).toHaveStyle({ width: '75%' });
  });

  it('has accessible progressbar role', () => {
    render(<ProgressBar progress={50} message="Loading..." />);
    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toBeInTheDocument();
    expect(progressBar).toHaveAttribute('aria-valuenow', '50');
    expect(progressBar).toHaveAttribute('aria-valuemin', '0');
    expect(progressBar).toHaveAttribute('aria-valuemax', '100');
  });

  it('rounds progress percentage display', () => {
    render(<ProgressBar progress={66.7} message="Loading..." />);
    expect(screen.getByText('67%')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<ProgressBar progress={50} message="Loading..." className="custom-class" />);
    const progressBar = screen.getByTestId('progress-bar');
    expect(progressBar).toHaveClass('custom-class');
  });

  it('has transition class for smooth animation', () => {
    render(<ProgressBar progress={50} message="Loading..." />);
    const progressFill = screen.getByTestId('progress-bar-fill');
    expect(progressFill).toHaveClass('transition-all', 'duration-300');
  });
});
