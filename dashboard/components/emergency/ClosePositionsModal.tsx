'use client';

/**
 * Close Positions Modal Component
 * Modal with typed confirmation for closing all open positions
 */

import React, { useState, useEffect } from 'react';
import Modal from '@/components/ui/Modal';
import { useClosePositions } from '@/hooks/useClosePositions';
import type { ClosePositionsResponse } from '@/types/execution';

interface ClosePositionsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (result: ClosePositionsResponse) => void;
}

export default function ClosePositionsModal({
  isOpen,
  onClose,
  onSuccess,
}: ClosePositionsModalProps) {
  const [confirmText, setConfirmText] = useState('');
  const [executionResult, setExecutionResult] = useState<ClosePositionsResponse | null>(null);

  const {
    executeCloseAll,
    fetchPositions,
    positions,
    isExecuting,
    loadingPositions,
    error: hookError,
  } = useClosePositions();

  const [error, setError] = useState<string | null>(null);
  const isConfirmValid = confirmText.trim().toUpperCase() === 'CLOSE';

  // Fetch positions when modal opens
  useEffect(() => {
    if (isOpen && !executionResult) {
      fetchPositions();
    }
  }, [isOpen, executionResult, fetchPositions]);

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

    try {
      setError(null);
      const result = await executeCloseAll('User emergency close via dashboard');
      setExecutionResult(result);

      if (result.success && onSuccess) {
        onSuccess(result);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  const totalPnL = positions.reduce((sum, pos) => sum + pos.pnl, 0);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="⚠️ Close All Positions"
      size="lg"
      showCloseButton={!isExecuting}
    >
      <div className="space-y-6">
        {/* Position Status */}
        {!executionResult && (
          <>
            {loadingPositions ? (
              <div className="p-4 bg-gray-800 rounded-lg">
                <p className="text-gray-400 text-center">Loading positions...</p>
              </div>
            ) : (
              <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
                <h3 className="text-lg font-semibold text-white mb-3">Current Open Positions</h3>
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <p className="text-sm text-gray-400">Open Positions</p>
                    <p className="text-2xl font-bold text-white">{positions.length}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Total Unrealized P&L</p>
                    <p
                      className={`text-2xl font-bold ${
                        totalPnL >= 0 ? 'text-green-500' : 'text-red-500'
                      }`}
                    >
                      ${totalPnL.toFixed(2)}
                    </p>
                  </div>
                </div>

                {positions.length > 0 && (
                  <div className="mt-4">
                    <p className="text-sm text-gray-400 mb-2">Positions</p>
                    <div className="space-y-2 max-h-40 overflow-y-auto">
                      {positions.map((position) => (
                        <div
                          key={position.id}
                          className="flex justify-between items-center text-sm bg-gray-900 p-2 rounded"
                        >
                          <div className="flex flex-col">
                            <span className="text-white font-medium">
                              {position.instrument}
                            </span>
                            <span className="text-xs text-gray-500">
                              {position.direction.toUpperCase()} • {position.size} units
                            </span>
                          </div>
                          <span
                            className={`font-bold ${
                              position.pnl >= 0 ? 'text-green-500' : 'text-red-500'
                            }`}
                          >
                            ${position.pnl.toFixed(2)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {positions.length === 0 && (
                  <div className="p-4 bg-blue-900/20 border border-blue-500/50 rounded-lg mt-4">
                    <p className="text-blue-400 text-sm text-center">
                      No open positions to close.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Warning */}
            {positions.length > 0 && (
              <div className="p-4 bg-orange-900/20 border border-orange-500/50 rounded-lg">
                <div className="flex items-start space-x-3">
                  <svg
                    className="w-6 h-6 text-orange-500 flex-shrink-0 mt-0.5"
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
                    <h4 className="text-orange-500 font-semibold">Warning</h4>
                    <p className="text-sm text-gray-300 mt-1">
                      This will close ALL {positions.length} open positions immediately at market
                      price. This action cannot be undone.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Typed Confirmation */}
            {positions.length > 0 && (
              <div>
                <label htmlFor="close-confirm-input" className="block text-sm font-medium text-gray-300 mb-2">
                  Type <span className="font-bold text-orange-500">&quot;CLOSE&quot;</span> to confirm:
                </label>
                <input
                  id="close-confirm-input"
                  type="text"
                  value={confirmText}
                  onChange={(e) => setConfirmText(e.target.value)}
                  className={`w-full px-4 py-2 bg-gray-800 border rounded-lg text-white focus:outline-none focus:ring-2 ${
                    isConfirmValid
                      ? 'border-green-500 focus:ring-green-500'
                      : 'border-gray-600 focus:ring-orange-500'
                  }`}
                  placeholder="Type CLOSE"
                  autoFocus
                  disabled={isExecuting}
                />
              </div>
            )}
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
                  Positions Closed Successfully
                </h4>
                <p className="text-sm text-gray-300">
                  {executionResult.positions_closed} positions have been closed.
                </p>
                {executionResult.errors.length > 0 && (
                  <p className="text-sm text-yellow-400 mt-2">
                    {executionResult.errors.length} errors occurred during closure.
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Error State */}
        {(error || hookError || (!executionResult?.success && executionResult)) && (
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
                <h4 className="text-lg font-semibold text-red-500 mb-1">Close Positions Failed</h4>
                <p className="text-sm text-gray-300 mb-3">
                  {error || hookError || 'Failed to close positions'}
                </p>
                <button
                  onClick={handleConfirm}
                  disabled={!isConfirmValid || isExecuting}
                  className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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
                disabled={!isConfirmValid || isExecuting || positions.length === 0}
                className="px-6 py-2 bg-orange-600 text-white font-bold rounded-lg hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-lg"
                aria-label="Confirm close all positions"
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
                    <span>Closing...</span>
                  </span>
                ) : (
                  'Close All Positions'
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
