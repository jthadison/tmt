'use client';

import React, { useState } from 'react';

interface RollbackConfirmationModalProps {
  currentMode: string;
  onConfirm: (reason: string) => Promise<void>;
  onCancel: () => void;
  loading?: boolean;
}

export default function RollbackConfirmationModal({
  currentMode,
  onConfirm,
  onCancel,
  loading = false
}: RollbackConfirmationModalProps) {
  const [confirmationText, setConfirmationText] = useState('');
  const [reason, setReason] = useState('Manual emergency rollback via dashboard');

  const isConfirmed = confirmationText === 'ROLLBACK';

  const handleConfirm = async () => {
    if (isConfirmed && !loading) {
      await onConfirm(reason);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-lg border border-gray-700 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 space-y-6">
          {/* Header */}
          <div>
            <h2 className="text-2xl font-bold text-white mb-2">
              ⚠️ Confirm Emergency Rollback
            </h2>
            <p className="text-gray-400">
              This action will immediately switch trading parameters across all agents
            </p>
          </div>

          {/* Current vs Target Mode Comparison */}
          <div className="space-y-4">
            <div className="bg-gray-750 rounded-lg p-4 border border-gray-600">
              <h3 className="text-sm font-semibold text-red-400 mb-3">Current Mode</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Mode:</span>
                  <span className="text-white font-medium">{currentMode}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Parameters:</span>
                  <span className="text-white font-medium">Session-specific optimization</span>
                </div>
              </div>
            </div>

            <div className="text-center">
              <div className="inline-block bg-gray-700 rounded-full p-2">
                <svg
                  className="w-6 h-6 text-orange-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 14l-7 7m0 0l-7-7m7 7V3"
                  />
                </svg>
              </div>
            </div>

            <div className="bg-gray-750 rounded-lg p-4 border border-green-600">
              <h3 className="text-sm font-semibold text-green-400 mb-3">Target Mode</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Mode:</span>
                  <span className="text-white font-medium">Universal Cycle 4</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Confidence:</span>
                  <span className="text-white font-medium">75%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Risk-Reward:</span>
                  <span className="text-white font-medium">3.0</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Sessions:</span>
                  <span className="text-white font-medium">Universal parameters (all equal)</span>
                </div>
              </div>
            </div>
          </div>

          {/* Impact Summary */}
          <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4">
            <h4 className="text-sm font-semibold text-yellow-400 mb-2">Impact Summary</h4>
            <ul className="text-sm text-gray-300 space-y-1">
              <li>• 8 agents will receive updated parameters</li>
              <li>• Trading will continue with universal parameters</li>
              <li>• No positions will be closed</li>
              <li>• Emergency contacts will be notified</li>
            </ul>
          </div>

          {/* Warning */}
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
            <p className="text-red-400 text-sm font-medium">
              ⚠️ This will immediately switch trading parameters across all agents
            </p>
          </div>

          {/* Reason Input */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Reason for Rollback
            </label>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-orange-500"
              placeholder="Enter reason for rollback..."
            />
          </div>

          {/* Confirmation Input */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Type <code className="bg-gray-700 px-2 py-1 rounded text-orange-400">ROLLBACK</code>{' '}
              to confirm
            </label>
            <input
              type="text"
              value={confirmationText}
              onChange={(e) => setConfirmationText(e.target.value.toUpperCase())}
              className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-orange-500"
              placeholder="Type ROLLBACK"
              autoFocus
            />
          </div>

          {/* Action Buttons */}
          <div className="flex space-x-4 pt-4">
            <button
              onClick={onCancel}
              disabled={loading}
              className="flex-1 px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirm}
              disabled={!isConfirmed || loading}
              className={`flex-1 px-6 py-3 rounded-lg font-bold transition-all ${
                isConfirmed && !loading
                  ? 'bg-orange-600 hover:bg-orange-700 text-white shadow-lg hover:shadow-xl'
                  : 'bg-gray-700 text-gray-500 cursor-not-allowed'
              }`}
            >
              {loading ? 'Executing Rollback...' : 'Confirm Rollback'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
