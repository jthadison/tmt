/**
 * Tests for EmergencyStopButton component
 */

import React from 'react';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../../testUtils';
import EmergencyStopButton from '@/components/emergency/EmergencyStopButton';
import * as emergencyApi from '@/api/emergency';

jest.mock('@/api/emergency');

describe('EmergencyStopButton', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  it('should render emergency stop button', () => {
    renderWithProviders(<EmergencyStopButton />);

    const button = screen.getByRole('button', { name: /emergency stop trading button/i });
    expect(button).toBeInTheDocument();
  });

  it('should open modal when clicked', async () => {
    renderWithProviders(<EmergencyStopButton />);

    const button = screen.getByRole('button', { name: /emergency stop trading button/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText(/Emergency Stop Trading/i)).toBeInTheDocument();
    });
  });

  it('should show tooltip on hover', () => {
    renderWithProviders(<EmergencyStopButton />);

    const button = screen.getByRole('button', { name: /emergency stop trading button/i });
    expect(button).toHaveAttribute('title', expect.stringContaining('Emergency Stop Trading'));
  });

  it('should be disabled during cooldown', async () => {
    const mockResponse = {
      success: true,
      message: 'Trading stopped successfully',
      positions_closed: 0,
      timestamp: new Date().toISOString(),
    };

    (emergencyApi.emergencyStopTrading as jest.Mock).mockResolvedValue(mockResponse);
    (emergencyApi.getSystemStatus as jest.Mock).mockResolvedValue({
      trading_enabled: true,
      active_positions: 0,
      daily_pnl: 0,
      open_trades: [],
      timestamp: new Date().toISOString(),
    });
    (emergencyApi.logEmergencyAction as jest.Mock).mockResolvedValue(undefined);

    renderWithProviders(<EmergencyStopButton />);

    const button = screen.getByRole('button', { name: /emergency stop trading button/i });
    fireEvent.click(button);

    // Wait for modal and confirm
    await waitFor(() => {
      expect(screen.getByText(/Type "STOP" to confirm/i)).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText('Type STOP');
    fireEvent.change(input, { target: { value: 'STOP' } });

    const confirmButton = screen.getByRole('button', { name: /Confirm emergency stop/i });
    fireEvent.click(confirmButton);

    // Wait for execution to complete
    await waitFor(() => {
      expect(screen.getByText(/Trading Stopped Successfully/i)).toBeInTheDocument();
    });

    // Close modal
    const closeButton = screen.getByRole('button', { name: /Close/i });
    fireEvent.click(closeButton);

    // Button should now be disabled during cooldown
    await waitFor(() => {
      expect(button).toBeDisabled();
    });
  });

  it('should show error state when stop fails', async () => {
    const mockError = new Error('Network error');
    (emergencyApi.emergencyStopTrading as jest.Mock).mockRejectedValue(mockError);
    (emergencyApi.getSystemStatus as jest.Mock).mockResolvedValue({
      trading_enabled: true,
      active_positions: 0,
      daily_pnl: 0,
      open_trades: [],
      timestamp: new Date().toISOString(),
    });
    (emergencyApi.logEmergencyAction as jest.Mock).mockResolvedValue(undefined);

    renderWithProviders(<EmergencyStopButton />);

    const button = screen.getByRole('button', { name: /emergency stop trading button/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText(/Type "STOP" to confirm/i)).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText('Type STOP');
    fireEvent.change(input, { target: { value: 'STOP' } });

    const confirmButton = screen.getByRole('button', { name: /Confirm emergency stop/i });
    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(screen.getByText(/Emergency Stop Failed/i)).toBeInTheDocument();
      expect(screen.getByText(/Network error/i)).toBeInTheDocument();
    });
  });
});
