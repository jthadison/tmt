/**
 * Loading Button Tests
 * Story 9.1: AC6 - Button loading states (3-stage transition)
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { LoadingButton } from '@/components/buttons/LoadingButton';

describe('LoadingButton', () => {
  it('renders in idle state initially', () => {
    const mockAction = jest.fn().mockResolvedValue(undefined);
    render(<LoadingButton onClick={mockAction}>Click Me</LoadingButton>);

    const button = screen.getByTestId('loading-button');
    expect(button).toHaveTextContent('Click Me');
    expect(button).not.toBeDisabled();
    expect(button).toHaveAttribute('data-state', 'idle');
  });

  it('transitions to loading state on click', async () => {
    const mockAction = jest.fn(() => new Promise((resolve) => setTimeout(resolve, 100)));
    render(<LoadingButton onClick={mockAction}>Click Me</LoadingButton>);

    const button = screen.getByTestId('loading-button');
    fireEvent.click(button);

    await waitFor(() => {
      expect(button).toHaveAttribute('data-state', 'loading');
      expect(button).toHaveTextContent('Processing...');
      expect(button).toBeDisabled();
      expect(screen.getByTestId('spinner-icon')).toBeInTheDocument();
    });
  });

  it('transitions to success state after successful action', async () => {
    const mockAction = jest.fn().mockResolvedValue(undefined);
    render(<LoadingButton onClick={mockAction}>Click Me</LoadingButton>);

    const button = screen.getByTestId('loading-button');
    fireEvent.click(button);

    await waitFor(() => {
      expect(button).toHaveAttribute('data-state', 'success');
      expect(button).toHaveTextContent('Success!');
      expect(screen.getByTestId('check-icon')).toBeInTheDocument();
    });
  });

  it('returns to idle state after success duration', async () => {
    const mockAction = jest.fn().mockResolvedValue(undefined);
    render(<LoadingButton onClick={mockAction} successDuration={500}>Click Me</LoadingButton>);

    const button = screen.getByTestId('loading-button');
    fireEvent.click(button);

    // Wait for success state
    await waitFor(() => {
      expect(button).toHaveAttribute('data-state', 'success');
    });

    // Wait for return to idle
    await waitFor(() => {
      expect(button).toHaveAttribute('data-state', 'idle');
      expect(button).toHaveTextContent('Click Me');
    }, { timeout: 1000 });
  });

  it('shows custom success message', async () => {
    const mockAction = jest.fn().mockResolvedValue(undefined);
    render(
      <LoadingButton onClick={mockAction} successMessage="Completed!">
        Click Me
      </LoadingButton>
    );

    const button = screen.getByTestId('loading-button');
    fireEvent.click(button);

    await waitFor(() => {
      expect(button).toHaveTextContent('Completed!');
    });
  });

  it('handles errors and shows error state', async () => {
    const mockAction = jest.fn().mockRejectedValue(new Error('Failed'));
    render(<LoadingButton onClick={mockAction}>Click Me</LoadingButton>);

    const button = screen.getByTestId('loading-button');
    fireEvent.click(button);

    await waitFor(() => {
      expect(button).toHaveAttribute('data-state', 'error');
      expect(button).toHaveTextContent('Failed');
      expect(screen.getByTestId('error-icon')).toBeInTheDocument();
    });
  });

  it('returns to idle after error', async () => {
    const mockAction = jest.fn().mockRejectedValue(new Error('Failed'));
    render(<LoadingButton onClick={mockAction}>Click Me</LoadingButton>);

    const button = screen.getByTestId('loading-button');
    fireEvent.click(button);

    // Wait for error state
    await waitFor(() => {
      expect(button).toHaveAttribute('data-state', 'error');
    });

    // Wait for return to idle
    await waitFor(() => {
      expect(button).toHaveAttribute('data-state', 'idle');
    }, { timeout: 2500 });
  });

  it('prevents double-clicks during loading', async () => {
    const mockAction = jest.fn(() => new Promise((resolve) => setTimeout(resolve, 100)));
    render(<LoadingButton onClick={mockAction}>Click Me</LoadingButton>);

    const button = screen.getByTestId('loading-button');
    fireEvent.click(button);
    fireEvent.click(button); // Second click should be ignored

    await waitFor(() => {
      expect(button).toHaveAttribute('data-state', 'loading');
    });

    expect(mockAction).toHaveBeenCalledTimes(1);
  });

  it('respects disabled prop', () => {
    const mockAction = jest.fn();
    render(<LoadingButton onClick={mockAction} disabled={true}>Click Me</LoadingButton>);

    const button = screen.getByTestId('loading-button');
    expect(button).toBeDisabled();

    fireEvent.click(button);
    expect(mockAction).not.toHaveBeenCalled();
  });

  it('applies primary variant styles', () => {
    const mockAction = jest.fn();
    render(<LoadingButton onClick={mockAction} variant="primary">Click Me</LoadingButton>);

    const button = screen.getByTestId('loading-button');
    expect(button).toHaveClass('bg-blue-600');
  });

  it('applies secondary variant styles', () => {
    const mockAction = jest.fn();
    render(<LoadingButton onClick={mockAction} variant="secondary">Click Me</LoadingButton>);

    const button = screen.getByTestId('loading-button');
    expect(button).toHaveClass('bg-gray-200');
  });

  it('applies danger variant styles', () => {
    const mockAction = jest.fn();
    render(<LoadingButton onClick={mockAction} variant="danger">Click Me</LoadingButton>);

    const button = screen.getByTestId('loading-button');
    expect(button).toHaveClass('bg-red-600');
  });

  it('applies custom className', () => {
    const mockAction = jest.fn();
    render(<LoadingButton onClick={mockAction} className="custom-class">Click Me</LoadingButton>);

    const button = screen.getByTestId('loading-button');
    expect(button).toHaveClass('custom-class');
  });
});
