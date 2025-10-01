'use client';

/**
 * Emergency Stop Modal Component
 * Modal with typed confirmation for emergency stop
 */

import React, { useState, useEffect } from 'react';
import Modal from '@/components/ui/Modal';
import { getSystemStatus } from '@/api/emergency';
import type { SystemStatus } from '@/types/emergency';

interface EmergencyStopModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (closePositions: boolean) => Promise<void>;
  isExecuting: boolean;
  executionResult: {
    success: boolean;
    message: string;
    positionsClosed: number;
  } | null;
  error: string | null;
  onResumeTrading: () => Promise<void>;
}

export default function EmergencyStopModal({
  isOpen,
  onClose,
  onConfirm,
  isExecuting,
  executionResult,
  error,
  onResumeTrading,
}: EmergencyStopModalProps) {
  const [confirmText, setConfirmText] = useState('');
  const [closePositions, setClosePositions] = useState(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [showResumeButton, setShowResumeButton] = useState(false);

  const isConfirmValid = confirmText.trim().toUpperCase() === 'STOP';

  // Fetch system status when modal opens
  useEffect(() => {
    if (isOpen && !executionResult) {
      setLoadingStatus(true);
      getSystemStatus()
        .then(setSystemStatus)
        .catch((err) => console.error('Failed to fetch system status:', err))
        .finally(() => setLoadingStatus(false));
    }
  }, [isOpen, executionResult]);

  // Show resume button after successful stop
  useEffect(() => {
    if (executionResult?.success) {
      setShowResumeButton(true);
    }
  }, [executionResult]);

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setTimeout(() => {
        setConfirmText('');
        setClosePositions(false);
        setShowResumeButton(false);
      }, 300); // Delay to allow modal close animation
    }
  }, [isOpen]);

  const handleConfirm = async () => {
    if (!isConfirmValid) return;
    await onConfirm(closePositions);
  };

  const handleResume = async () => {
    await onResumeTrading();
    setShowResumeButton(false);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="⚠️ Emergency Stop Trading" size="lg" showCloseButton={!isExecuting}>
      <div className="space-y-6">
        {/* System Status */}
        {!executionResult && (
          <>
            {loadingStatus ? (
              <div className="p-4 bg-gray-800 rounded-lg">
                <p className="text-gray-400 text-center">Loading system status...</p>
              </div>
            ) : systemStatus ? (
              <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
                <h3 className="text-lg font-semibold text-white mb-3">Current System Status</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-400">Active Positions</p>
                    <p className="text-2xl font-bold text-white">{systemStatus.active_positions}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Daily P&L</p>
                    <p className={`text-2xl font-bold ${systemStatus.daily_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      ${systemStatus.daily_pnl.toFixed(2)}
                    </p>
                  </div>
                </div>

                {systemStatus.open_trades.length > 0 && (
                  <div className="mt-4">
                    <p className="text-sm text-gray-400 mb-2">Open Trades</p>
                    <div className="space-y-2 max-h-32 overflow-y-auto">
                      {systemStatus.open_trades.map((trade, idx) => (
                        <div key={idx} className="flex justify-between items-center text-sm bg-gray-900 p-2 rounded">
                          <span className="text-white">
                            {trade.instrument} - {trade.direction.toUpperCase()}
                          </span>
                          <span className={trade.pnl >= 0 ? 'text-green-500' : 'text-red-500'}>
                            ${trade.pnl.toFixed(2)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-4 bg-yellow-900/20 border border-yellow-500/50 rounded-lg">
                <p className="text-yellow-500 text-sm">
                  Unable to fetch system status. You can still proceed with emergency stop.
                </p>
              </div>
            )}

            {/* Typed Confirmation */}
            <div>
              <label htmlFor="confirm-input" className="block text-sm font-medium text-gray-300 mb-2">
                Type <span className="font-bold text-red-500">&quot;STOP&quot;</span> to confirm:
              </label>
              <input
                id="confirm-input"
                type="text"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                className={`w-full px-4 py-2 bg-gray-800 border rounded-lg text-white focus:outline-none focus:ring-2 ${
                  isConfirmValid
                    ? 'border-green-500 focus:ring-green-500'
                    : 'border-gray-600 focus:ring-red-500'
                }`}
                placeholder="Type STOP"
                autoFocus
                disabled={isExecuting}
              />
            </div>

            {/* Close Positions Option */}
            <label className="flex items-start space-x-3 cursor-pointer">
              <input
                type="checkbox"
                checked={closePositions}
                onChange={(e) => setClosePositions(e.target.checked)}
                className="mt-1 w-4 h-4 text-red-600 bg-gray-800 border-gray-600 rounded focus:ring-red-500"
                disabled={isExecuting}
              />
              <div>
                <span className="text-white font-medium">Also close all open positions immediately</span>
                <p className="text-sm text-gray-400 mt-1">
                  This will immediately close all {systemStatus?.active_positions || 0} open positions at market price.
                </p>
              </div>
            </label>
          </>
        )}

        {/* Success State */}
        {executionResult?.success && (
          <div className="p-4 bg-green-900/20 border border-green-500/50 rounded-lg">
            <div className="flex items-start space-x-3">
              <svg className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <div className="flex-1">
                <h4 className="text-lg font-semibold text-green-500 mb-1">Trading Stopped Successfully</h4>
                <p className="text-sm text-gray-300">
                  {executionResult.positionsClosed > 0
                    ? `All ${executionResult.positionsClosed} positions have been closed.`
                    : `${systemStatus?.active_positions || 0} positions remain open.`}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && !executionResult?.success && (
          <div className="p-4 bg-red-900/20 border border-red-500/50 rounded-lg">
            <div className="flex items-start space-x-3">
              <svg className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="flex-1">
                <h4 className="text-lg font-semibold text-red-500 mb-1">Emergency Stop Failed</h4>
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
                aria-label="Confirm emergency stop"
              >
                {isExecuting ? (
                  <span className="flex items-center space-x-2">
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <span>Stopping...</span>
                  </span>
                ) : (
                  'Confirm Emergency Stop'
                )}
              </button>
            </>
          )}

          {showResumeButton && executionResult?.success && (
            <button
              onClick={handleResume}
              className="px-6 py-2 bg-green-600 text-white font-bold rounded-lg hover:bg-green-700 transition-colors shadow-lg"
              aria-label="Resume trading"
            >
              Resume Trading
            </button>
          )}

          {executionResult && !showResumeButton && (
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
