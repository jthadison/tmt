/**
 * Modal Overlay Tests
 * Story 9.1: AC4 - Modal overlay for full-page operations
 */

import { render, screen } from '@testing-library/react';
import { ModalOverlay } from '@/components/loading/ModalOverlay';

describe('ModalOverlay', () => {
  it('renders when isOpen is true', () => {
    render(<ModalOverlay message="Processing..." isOpen={true} />);
    expect(screen.getByTestId('modal-overlay')).toBeInTheDocument();
  });

  it('does not render when isOpen is false', () => {
    render(<ModalOverlay message="Processing..." isOpen={false} />);
    expect(screen.queryByTestId('modal-overlay')).not.toBeInTheDocument();
  });

  it('displays custom message', () => {
    render(<ModalOverlay message="Processing trade..." isOpen={true} />);
    expect(screen.getByText('Processing trade...')).toBeInTheDocument();
  });

  it('has dimmed background overlay', () => {
    render(<ModalOverlay message="Processing..." isOpen={true} />);
    const overlay = screen.getByTestId('modal-overlay');
    expect(overlay).toHaveClass('bg-black/50');
  });

  it('has accessible modal markup', () => {
    render(<ModalOverlay message="Processing..." isOpen={true} />);
    const overlay = screen.getByTestId('modal-overlay');
    expect(overlay).toHaveAttribute('role', 'dialog');
    expect(overlay).toHaveAttribute('aria-modal', 'true');
  });

  it('renders spinner icon', () => {
    render(<ModalOverlay message="Processing..." isOpen={true} />);
    expect(screen.getByTestId('modal-spinner')).toBeInTheDocument();
  });

  it('centers content on screen', () => {
    render(<ModalOverlay message="Processing..." isOpen={true} />);
    const overlay = screen.getByTestId('modal-overlay');
    expect(overlay).toHaveClass('flex', 'items-center', 'justify-center');
  });

  it('has fixed positioning to cover entire viewport', () => {
    render(<ModalOverlay message="Processing..." isOpen={true} />);
    const overlay = screen.getByTestId('modal-overlay');
    expect(overlay).toHaveClass('fixed', 'inset-0');
  });

  it('has high z-index for visibility', () => {
    render(<ModalOverlay message="Processing..." isOpen={true} />);
    const overlay = screen.getByTestId('modal-overlay');
    expect(overlay).toHaveClass('z-50');
  });
});
