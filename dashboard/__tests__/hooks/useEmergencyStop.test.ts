/**
 * Tests for useEmergencyStop hook
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { useEmergencyStop } from '@/hooks/useEmergencyStop';
import * as emergencyApi from '@/api/emergency';

jest.mock('@/api/emergency');

describe('useEmergencyStop', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  it('should initialize with correct default state', () => {
    const { result } = renderHook(() => useEmergencyStop());

    expect(result.current.isExecuting).toBe(false);
    expect(result.current.canExecute).toBe(true);
    expect(result.current.error).toBe(null);
    expect(result.current.cooldownRemaining).toBe(0);
  });

  it('should execute emergency stop successfully', async () => {
    const mockResponse = {
      success: true,
      message: 'Trading stopped successfully',
      positions_closed: 0,
      timestamp: new Date().toISOString(),
    };

    (emergencyApi.emergencyStopTrading as jest.Mock).mockResolvedValue(mockResponse);
    (emergencyApi.logEmergencyAction as jest.Mock).mockResolvedValue(undefined);

    const { result } = renderHook(() => useEmergencyStop());

    let response;
    await act(async () => {
      response = await result.current.executeEmergencyStop(false);
    });

    expect(emergencyApi.emergencyStopTrading).toHaveBeenCalledWith({ closePositions: false });
    expect(emergencyApi.logEmergencyAction).toHaveBeenCalledWith({
      action: 'emergency_stop',
      user: 'anonymous',
      closePositions: false,
      positionsClosed: 0,
      success: true,
    });
    expect(response).toEqual(mockResponse);
    expect(result.current.isExecuting).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('should handle emergency stop failure', async () => {
    const mockError = new Error('Network error');
    (emergencyApi.emergencyStopTrading as jest.Mock).mockRejectedValue(mockError);
    (emergencyApi.logEmergencyAction as jest.Mock).mockResolvedValue(undefined);

    const { result } = renderHook(() => useEmergencyStop());

    await act(async () => {
      try {
        await result.current.executeEmergencyStop(false);
      } catch (err) {
        // Expected error
      }
    });

    expect(result.current.error).toBe('Network error');
    expect(emergencyApi.logEmergencyAction).toHaveBeenCalledWith({
      action: 'emergency_stop',
      user: 'anonymous',
      closePositions: false,
      success: false,
      error: 'Network error',
    });
  });

  it('should enforce cooldown period', async () => {
    const mockResponse = {
      success: true,
      message: 'Trading stopped successfully',
      positions_closed: 0,
      timestamp: new Date().toISOString(),
    };

    (emergencyApi.emergencyStopTrading as jest.Mock).mockResolvedValue(mockResponse);
    (emergencyApi.logEmergencyAction as jest.Mock).mockResolvedValue(undefined);

    const { result } = renderHook(() => useEmergencyStop());

    // First execution
    await act(async () => {
      await result.current.executeEmergencyStop(false);
    });

    expect(result.current.canExecute).toBe(false);
    expect(result.current.cooldownRemaining).toBeGreaterThan(0);

    // Attempt second execution during cooldown
    await act(async () => {
      try {
        await result.current.executeEmergencyStop(false);
      } catch (err) {
        expect(err).toEqual(new Error('Emergency stop cooldown active'));
      }
    });
  });

  it('should execute resume trading successfully', async () => {
    const mockResponse = {
      success: true,
      message: 'Trading resumed successfully',
      positions_closed: 0,
      timestamp: new Date().toISOString(),
    };

    (emergencyApi.resumeTrading as jest.Mock).mockResolvedValue(mockResponse);
    (emergencyApi.logEmergencyAction as jest.Mock).mockResolvedValue(undefined);

    const { result } = renderHook(() => useEmergencyStop());

    let response;
    await act(async () => {
      response = await result.current.executeResumeTrading();
    });

    expect(emergencyApi.resumeTrading).toHaveBeenCalled();
    expect(emergencyApi.logEmergencyAction).toHaveBeenCalledWith({
      action: 'resume_trading',
      user: 'anonymous',
      success: true,
    });
    expect(response).toEqual(mockResponse);
  });
});
