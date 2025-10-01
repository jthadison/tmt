'use client';

/**
 * Emergency Rollback Modal Component
 * Modal with typed confirmation for emergency rollback between session and universal modes
 */

import React, { useState, useEffect } from 'react';
import Modal from '@/components/ui/Modal';
import { executeRollback } from '@/api/execution';
import { logEmergencyAction } from '@/api/emergency';
import type { RollbackResponse } from '@/types/execution';

interface EmergencyRollbackModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (result: RollbackResponse) => void;
}

export default function EmergencyRollbackModal({
  isOpen,
  onClose,
  onSuccess,
}: EmergencyRollbackModalProps) {
  const [confirmText, setConfirmText] = useState('');
  const [targetMode, setTargetMode] = useState<'session' | 'universal'>('universal');
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<RollbackResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isConfirmValid = confirmText.trim().toUpperCase() === 'ROLLBACK';

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setTimeout(() => {
        setConfirmText('');
        setTargetMode('universal');
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
      const result = await executeRollback({
        target_mode: targetMode,
        reason: 'User emergency rollback via dashboard',
      });

      setExecutionResult(result);

      // Log audit trail
      await logEmergencyAction({
        action: 'emergency_rollback',
        user: 'anonymous',
        success: result.success,
        details: {
          previous_mode: result.previous_mode,
          new_mode: result.new_mode,
        },
      });

      if (result.success && onSuccess) {
        onSuccess(result);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);

      // Log failed attempt
      await logEmergencyAction({
        action: 'emergency_rollback',
        user: 'anonymous',
        success: false,
        error: errorMessage,
      });
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="⚠️ Emergency Rollback"
      size="lg"
      showCloseButton={!isExecuting}
    >
      <div className="space-y-6">
        {!executionResult && (
          <>
            {/* Current Mode Info */}
            <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
              <h3 className="text-lg font-semibold text-white mb-3">Rollback Configuration</h3>
              <div>
                <label htmlFor="target-mode" className="block text-sm font-medium text-gray-300 mb-2">
                  Select Target Mode:
                </label>
                <select
                  id="target-mode"
                  value={targetMode}
                  onChange={(e) => setTargetMode(e.target.value as 'session' | 'universal')}
                  className="w-full px-4 py-2 bg-gray-900 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                  disabled={isExecuting}
                >
                  <option value="universal">Universal Cycle 4 (Safe Mode)</option>
                  <option value="session">Session-Targeted Trading</option>
                </select>
              </div>
              <p className="text-sm text-gray-400 mt-3">
                {targetMode === 'universal'
                  ? 'Switch to universal trading parameters (Cycle 4 configuration)'
                  : 'Switch to session-targeted trading with optimized parameters per session'}
              </p>
            </div>

            {/* Warning */}
            <div className="p-4 bg-purple-900/20 border border-purple-500/50 rounded-lg">
              <div className="flex items-start space-x-3">
                <svg
                  className="w-6 h-6 text-purple-500 flex-shrink-0 mt-0.5"
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
                  <h4 className="text-purple-400 font-semibold">Warning</h4>
                  <p className="text-sm text-gray-300 mt-1">
                    This will immediately switch trading parameters to {targetMode === 'universal' ? 'universal' : 'session-targeted'} mode.
                    All future trades will use the new configuration.
                  </p>
                </div>
              </div>
            </div>

            {/* Typed Confirmation */}
            <div>
              <label htmlFor="rollback-confirm-input" className="block text-sm font-medium text-gray-300 mb-2">
                Type <span className="font-bold text-purple-500">&quot;ROLLBACK&quot;</span> to confirm:
              </label>
              <input
                id="rollback-confirm-input"
                type="text"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                className={`w-full px-4 py-2 bg-gray-800 border rounded-lg text-white focus:outline-none focus:ring-2 ${
                  isConfirmValid
                    ? 'border-green-500 focus:ring-green-500'
                    : 'border-gray-600 focus:ring-purple-500'
                }`}
                placeholder="Type ROLLBACK"
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
                  Rollback Successful
                </h4>
                <p className="text-sm text-gray-300">
                  Successfully switched from {executionResult.previous_mode} to {executionResult.new_mode} mode.
                </p>
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
                <h4 className="text-lg font-semibold text-red-500 mb-1">Rollback Failed</h4>
                <p className="text-sm text-gray-300 mb-3">{error}</p>
                <button
                  onClick={handleConfirm}
                  disabled={!isConfirmValid || isExecuting}
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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
                className="px-6 py-2 bg-purple-600 text-white font-bold rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-lg"
                aria-label="Confirm emergency rollback"
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
                    <span>Executing Rollback...</span>
                  </span>
                ) : (
                  'Execute Rollback'
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
