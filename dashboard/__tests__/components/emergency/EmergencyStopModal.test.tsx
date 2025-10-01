/**
 * Tests for EmergencyStopModal component
 */

import React from 'react';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../../testUtils';
import EmergencyStopModal from '@/components/emergency/EmergencyStopModal';
import * as emergencyApi from '@/api/emergency';

jest.mock('@/api/emergency');

describe('EmergencyStopModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: jest.fn(),
    onConfirm: jest.fn(),
    isExecuting: false,
    executionResult: null,
    error: null,
    onResumeTrading: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (emergencyApi.getSystemStatus as jest.Mock).mockResolvedValue({
      trading_enabled: true,
      active_positions: 2,
      daily_pnl: -25.5,
      open_trades: [
        { instrument: 'EUR_USD', direction: 'long', pnl: -10.5 },
        { instrument: 'GBP_USD', direction: 'short', pnl: -15.0 },
      ],
      timestamp: new Date().toISOString(),
    });
  });

  it('should render modal when open', async () => {
    renderWithProviders(<EmergencyStopModal {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText(/Emergency Stop Trading/i)).toBeInTheDocument();
    });
  });

  it('should not render when closed', () => {
    renderWithProviders(<EmergencyStopModal {...defaultProps} isOpen={false} />);

    expect(screen.queryByText(/Emergency Stop Trading/i)).not.toBeInTheDocument();
  });

  it('should display system status', async () => {
    renderWithProviders(<EmergencyStopModal {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Current System Status')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument(); // Active positions
      expect(screen.getByText('$-25.50')).toBeInTheDocument(); // Daily P&L
    });
  });

  it('should enable confirm button only when "STOP" is typed', async () => {
    renderWithProviders(<EmergencyStopModal {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Type STOP')).toBeInTheDocument();
    });

    const confirmButton = screen.getByRole('button', { name: /Confirm emergency stop/i });
    expect(confirmButton).toBeDisabled();

    const input = screen.getByPlaceholderText('Type STOP');
    fireEvent.change(input, { target: { value: 'STO' } });
    expect(confirmButton).toBeDisabled();

    fireEvent.change(input, { target: { value: 'STOP' } });
    expect(confirmButton).not.toBeDisabled();
  });

  it('should accept case-insensitive "STOP" text', async () => {
    renderWithProviders(<EmergencyStopModal {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Type STOP')).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText('Type STOP');
    const confirmButton = screen.getByRole('button', { name: /Confirm emergency stop/i });

    fireEvent.change(input, { target: { value: 'stop' } });
    expect(confirmButton).not.toBeDisabled();

    fireEvent.change(input, { target: { value: 'Stop' } });
    expect(confirmButton).not.toBeDisabled();
  });

  it('should call onConfirm when confirmed', async () => {
    const onConfirm = jest.fn();
    renderWithProviders(<EmergencyStopModal {...defaultProps} onConfirm={onConfirm} />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Type STOP')).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText('Type STOP');
    fireEvent.change(input, { target: { value: 'STOP' } });

    const confirmButton = screen.getByRole('button', { name: /Confirm emergency stop/i });
    fireEvent.click(confirmButton);

    expect(onConfirm).toHaveBeenCalledWith(false);
  });

  it('should pass closePositions option when checkbox is selected', async () => {
    const onConfirm = jest.fn();
    renderWithProviders(<EmergencyStopModal {...defaultProps} onConfirm={onConfirm} />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Type STOP')).toBeInTheDocument();
    });

    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);

    const input = screen.getByPlaceholderText('Type STOP');
    fireEvent.change(input, { target: { value: 'STOP' } });

    const confirmButton = screen.getByRole('button', { name: /Confirm emergency stop/i });
    fireEvent.click(confirmButton);

    expect(onConfirm).toHaveBeenCalledWith(true);
  });

  it('should display success message after successful stop', () => {
    const executionResult = {
      success: true,
      message: 'Trading stopped successfully',
      positionsClosed: 2,
    };

    renderWithProviders(<EmergencyStopModal {...defaultProps} executionResult={executionResult} />);

    expect(screen.getByText(/Trading Stopped Successfully/i)).toBeInTheDocument();
    expect(screen.getByText(/All 2 positions have been closed/i)).toBeInTheDocument();
  });

  it('should display error message when stop fails', () => {
    renderWithProviders(<EmergencyStopModal {...defaultProps} error="Network connection failed" />);

    expect(screen.getByText(/Emergency Stop Failed/i)).toBeInTheDocument();
    expect(screen.getByText(/Network connection failed/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument();
  });

  it('should show resume button after successful stop', async () => {
    const executionResult = {
      success: true,
      message: 'Trading stopped successfully',
      positionsClosed: 0,
    };

    renderWithProviders(<EmergencyStopModal {...defaultProps} executionResult={executionResult} />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Resume trading/i })).toBeInTheDocument();
    });
  });

  it('should call onResumeTrading when resume button clicked', async () => {
    const onResumeTrading = jest.fn();
    const executionResult = {
      success: true,
      message: 'Trading stopped successfully',
      positionsClosed: 0,
    };

    renderWithProviders(
      <EmergencyStopModal
        {...defaultProps}
        executionResult={executionResult}
        onResumeTrading={onResumeTrading}
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Resume trading/i })).toBeInTheDocument();
    });

    const resumeButton = screen.getByRole('button', { name: /Resume trading/i });
    fireEvent.click(resumeButton);

    expect(onResumeTrading).toHaveBeenCalled();
  });

  it('should call onClose when cancel button clicked', async () => {
    const onClose = jest.fn();
    renderWithProviders(<EmergencyStopModal {...defaultProps} onClose={onClose} />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument();
    });

    const cancelButton = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelButton);

    expect(onClose).toHaveBeenCalled();
  });
});
