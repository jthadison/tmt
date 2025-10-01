'use client';

/**
 * Reset Circuit Breakers Modal Component
 * Modal with typed confirmation for resetting all circuit breakers
 */

import React, { useState, useEffect } from 'react';
import Modal from '@/components/ui/Modal';
import { useCircuitBreaker } from '@/hooks/useCircuitBreaker';
import type { ResetBreakersResponse } from '@/types/circuitBreaker';

interface ResetBreakersModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (result: ResetBreakersResponse) => void;
}

export default function ResetBreakersModal({
  isOpen,
  onClose,
  onSuccess,
}: ResetBreakersModalProps) {
  const [confirmText, setConfirmText] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<ResetBreakersResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { status, loading: loadingStatus, reset } = useCircuitBreaker();

  const isConfirmValid = confirmText.trim().toUpperCase() === 'RESET';

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setTimeout(() => {
        setConfirmText('');
        setExecutionResult(null);
        setError(null);
      }, 300); // Delay to allow modal close animation
    }
  }, [isOpen]);

  const handleConfirm = async () => {
    if (!isConfirmValid) return;

    setIsExecuting(true);
    setError(null);

    try {
      const result = await reset();
      setExecutionResult(result);

      if (onSuccess) {
        onSuccess(result);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="⚠️ Reset Circuit Breakers"
      size="lg"
      showCloseButton={!isExecuting}
    >
      <div className="space-y-6">
        {!executionResult && (
          <>
            {/* Current Breaker Status */}
            {loadingStatus ? (
              <div className="p-4 bg-gray-800 rounded-lg">
                <p className="text-gray-400 text-center">Loading circuit breaker status...</p>
              </div>
            ) : status ? (
              <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
                <h3 className="text-lg font-semibold text-white mb-3">Current Circuit Breaker Status</h3>
                <div className="space-y-3">
                  {/* Daily Loss */}
                  <div className="flex justify-between items-center">
                    <span className="text-gray-300">Daily Loss</span>
                    <span
                      className={`font-bold ${
                        status.daily_loss.current >= status.daily_loss.limit
                          ? 'text-red-500'
                          : status.daily_loss.current >= status.daily_loss.threshold
                          ? 'text-yellow-500'
                          : 'text-green-500'
                      }`}
                    >
                      ${status.daily_loss.current.toFixed(2)} / ${status.daily_loss.limit.toFixed(2)}
                    </span>
                  </div>

                  {/* Account Drawdown */}
                  <div className="flex justify-between items-center">
                    <span className="text-gray-300">Account Drawdown</span>
                    <span
                      className={`font-bold ${
                        status.account_drawdown.current >= status.account_drawdown.limit
                          ? 'text-red-500'
                          : status.account_drawdown.current >= status.account_drawdown.threshold
                          ? 'text-yellow-500'
                          : 'text-green-500'
                      }`}
                    >
                      {status.account_drawdown.current.toFixed(1)}% / {status.account_drawdown.limit.toFixed(1)}%
                    </span>
                  </div>

                  {/* Consecutive Losses */}
                  <div className="flex justify-between items-center">
                    <span className="text-gray-300">Consecutive Losses</span>
                    <span
                      className={`font-bold ${
                        status.consecutive_losses.current >= status.consecutive_losses.limit
                          ? 'text-red-500'
                          : status.consecutive_losses.current >= status.consecutive_losses.threshold
                          ? 'text-yellow-500'
                          : 'text-green-500'
                      }`}
                    >
                      {status.consecutive_losses.current} / {status.consecutive_losses.limit}
                    </span>
                  </div>

                  {/* Breaker State */}
                  <div className="flex justify-between items-center pt-2 border-t border-gray-700">
                    <span className="text-gray-300">Breaker State</span>
                    <span
                      className={`font-bold uppercase ${
                        status.state === 'open'
                          ? 'text-red-500'
                          : status.state === 'half_open'
                          ? 'text-yellow-500'
                          : 'text-green-500'
                      }`}
                    >
                      {status.state}
                    </span>
                  </div>

                  {/* Last Triggered */}
                  {status.last_triggered && (
                    <div className="pt-2 border-t border-gray-700">
                      <p className="text-sm text-yellow-400">
                        Last triggered: {status.last_triggered.type} at{' '}
                        {new Date(status.last_triggered.timestamp).toLocaleString()}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="p-4 bg-yellow-900/20 border border-yellow-500/50 rounded-lg">
                <p className="text-yellow-500 text-sm">
                  Unable to fetch circuit breaker status. You can still proceed with reset.
                </p>
              </div>
            )}

            {/* Warning */}
            <div className="p-4 bg-red-900/20 border border-red-500/50 rounded-lg">
              <div className="flex items-start space-x-3">
                <svg
                  className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
                <div>
                  <h4 className="text-red-400 font-semibold">Critical Warning</h4>
                  <p className="text-sm text-gray-300 mt-1">
                    This will reset ALL circuit breaker counters and thresholds. This removes
                    important safety mechanisms. Only do this if you understand the risks.
                  </p>
                </div>
              </div>
            </div>

            {/* Typed Confirmation */}
            <div>
              <label htmlFor="reset-confirm-input" className="block text-sm font-medium text-gray-300 mb-2">
                Type <span className="font-bold text-red-500">&quot;RESET&quot;</span> to confirm:
              </label>
              <input
                id="reset-confirm-input"
                type="text"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                className={`w-full px-4 py-2 bg-gray-800 border rounded-lg text-white focus:outline-none focus:ring-2 ${
                  isConfirmValid
                    ? 'border-green-500 focus:ring-green-500'
                    : 'border-gray-600 focus:ring-red-500'
                }`}
                placeholder="Type RESET"
                autoFocus
                disabled={isExecuting}
              />
            </div>
          </>
        )}

        {/* Success State */}
        {executionResult?.success && (
          <div className="p-4 bg-green-900/20 border border-green-500/50 rounded-lg">
            <div className="flex items-start space-x-3">
              <svg
                className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <div className="flex-1">
                <h4 className="text-lg font-semibold text-green-500 mb-1">
                  Circuit Breakers Reset Successfully
                </h4>
                <p className="text-sm text-gray-300">{executionResult.message}</p>
              </div>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && !executionResult?.success && (
          <div className="p-4 bg-red-900/20 border border-red-500/50 rounded-lg">
            <div className="flex items-start space-x-3">
              <svg
                className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <div className="flex-1">
                <h4 className="text-lg font-semibold text-red-500 mb-1">Reset Failed</h4>
                <p className="text-sm text-gray-300 mb-3">{error}</p>
                <button
                  onClick={handleConfirm}
                  disabled={!isConfirmValid || isExecuting}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Retry
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex justify-end space-x-3 pt-4 border-t border-gray-700">
          {!executionResult && (
            <>
              <button
                onClick={onClose}
                disabled={isExecuting}
                className="px-6 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                disabled={!isConfirmValid || isExecuting}
                className="px-6 py-2 bg-red-600 text-white font-bold rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-lg"
                aria-label="Confirm reset circuit breakers"
              >
                {isExecuting ? (
                  <span className="flex items-center space-x-2">
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                        fill="none"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    <span>Resetting...</span>
                  </span>
                ) : (
                  'Reset Circuit Breakers'
                )}
              </button>
            </>
          )}

          {executionResult && (
            <button
              onClick={onClose}
              className="px-6 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
            >
              Close
            </button>
          )}
        </div>
      </div>
    </Modal>
  );
}
