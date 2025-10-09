/**
 * AlertDashboard Component Tests - Story 11.8
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { AlertDashboard } from '@/components/validation/AlertDashboard';
import type { ValidationAlert } from '@/types/validation';
import { AlertLevel } from '@/types/validation';

const mockAlerts: ValidationAlert[] = [
  {
    id: '1',
    alert_type: 'OVERFITTING',
    severity: AlertLevel.CRITICAL,
    message: 'Overfitting score exceeded critical threshold',
    timestamp: '2025-10-09T10:00:00Z',
    acknowledged: false,
    resolved: false,
  },
  {
    id: '2',
    alert_type: 'PERFORMANCE_DEGRADATION',
    severity: AlertLevel.WARNING,
    message: 'Live performance 15% below backtest',
    timestamp: '2025-10-09T11:00:00Z',
    acknowledged: true,
    resolved: false,
  },
  {
    id: '3',
    alert_type: 'PARAMETER_DRIFT',
    severity: AlertLevel.INFO,
    message: 'Parameter drift detected',
    timestamp: '2025-10-09T12:00:00Z',
    acknowledged: false,
    resolved: false,
  },
];

describe('AlertDashboard', () => {
  it('renders loading state', () => {
    render(<AlertDashboard alerts={[]} loading={true} />);
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('displays all alerts', () => {
    render(<AlertDashboard alerts={mockAlerts} />);
    expect(screen.getByText(/Overfitting score exceeded critical threshold/i)).toBeInTheDocument();
    expect(screen.getByText(/Live performance 15% below backtest/i)).toBeInTheDocument();
    expect(screen.getByText(/Parameter drift detected/i)).toBeInTheDocument();
  });

  it('shows correct alert counts', () => {
    render(<AlertDashboard alerts={mockAlerts} />);
    expect(screen.getByText('3 of 3 alerts')).toBeInTheDocument();
  });

  it('filters unacknowledged alerts', async () => {
    render(<AlertDashboard alerts={mockAlerts} />);

    const filterSelect = screen.getAllByRole('combobox')[0];
    fireEvent.change(filterSelect, { target: { value: 'unacknowledged' } });

    await waitFor(() => {
      expect(screen.getByText('2 of 3 alerts')).toBeInTheDocument();
    });
  });

  it('filters critical alerts', async () => {
    render(<AlertDashboard alerts={mockAlerts} />);

    const filterSelect = screen.getAllByRole('combobox')[0];
    fireEvent.change(filterSelect, { target: { value: 'critical' } });

    await waitFor(() => {
      expect(screen.getByText('1 of 3 alerts')).toBeInTheDocument();
    });
  });

  it('calls onAcknowledge when acknowledge button clicked', async () => {
    const mockAcknowledge = jest.fn().mockResolvedValue(undefined);
    render(<AlertDashboard alerts={mockAlerts} onAcknowledge={mockAcknowledge} />);

    const acknowledgeButtons = screen.getAllByText('Acknowledge');
    fireEvent.click(acknowledgeButtons[0]);

    await waitFor(() => {
      expect(mockAcknowledge).toHaveBeenCalledWith('1');
    });
  });

  it('calls onDismiss when dismiss button clicked', async () => {
    const mockDismiss = jest.fn().mockResolvedValue(undefined);
    render(<AlertDashboard alerts={mockAlerts} onDismiss={mockDismiss} />);

    const dismissButtons = screen.getAllByText('Dismiss');
    fireEvent.click(dismissButtons[0]);

    await waitFor(() => {
      expect(mockDismiss).toHaveBeenCalledWith('1');
    });
  });

  it('displays summary statistics', () => {
    render(<AlertDashboard alerts={mockAlerts} />);

    // Critical count
    expect(screen.getByText('1', { selector: '.text-red-600' })).toBeInTheDocument();
    // Warning count
    expect(screen.getByText('1', { selector: '.text-yellow-600' })).toBeInTheDocument();
    // Acknowledged count
    expect(screen.getByText('1', { selector: '.text-green-600' })).toBeInTheDocument();
  });

  it('shows empty state when no alerts', () => {
    render(<AlertDashboard alerts={[]} />);
    expect(screen.getByText(/No alerts matching your filters/i)).toBeInTheDocument();
  });

  it('displays severity badges with correct colors', () => {
    render(<AlertDashboard alerts={mockAlerts} />);

    const criticalBadge = screen.getByText('CRITICAL');
    expect(criticalBadge).toHaveClass('text-red-700');

    const warningBadge = screen.getByText('WARNING');
    expect(warningBadge).toHaveClass('text-yellow-700');

    const infoBadge = screen.getByText('INFO');
    expect(infoBadge).toHaveClass('text-blue-700');
  });
});
