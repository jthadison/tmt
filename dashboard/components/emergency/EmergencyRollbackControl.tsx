'use client';

import React, { useState, useEffect } from 'react';
import { executeRollback, getCurrentTradingMode } from '@/api/rollback';
import RollbackConfirmationModal from './RollbackConfirmationModal';
import useKeyboardShortcut from '@/hooks/useKeyboardShortcut';

export default function EmergencyRollbackControl() {
  const [currentMode, setCurrentMode] = useState<string>('Loading...');
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCurrentMode();
  }, []);

  // Keyboard shortcut: Ctrl+Shift+R for rollback
  useKeyboardShortcut(
    'r',
    () => {
      const isUniversalMode = currentMode.toLowerCase().includes('universal') ||
                             currentMode.toLowerCase().includes('cycle 4');
      if (!isUniversalMode && !loading) {
        handleRollbackClick();
      }
    },
    { ctrlKey: true, shiftKey: true }
  );

  const fetchCurrentMode = async () => {
    try {
      const mode = await getCurrentTradingMode();
      setCurrentMode(mode);
    } catch (err) {
      setCurrentMode('Unknown');
      console.error('Failed to fetch trading mode:', err);
    }
  };

  const handleRollbackClick = () => {
    setShowModal(true);
  };

  const handleConfirmRollback = async (reason: string) => {
    try {
      setLoading(true);
      setError(null);
      await executeRollback(reason);

      // Refresh current mode after successful rollback
      await fetchCurrentMode();

      setShowModal(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Rollback failed');
    } finally {
      setLoading(false);
    }
  };

  const isUniversalMode = currentMode.toLowerCase().includes('universal') ||
                         currentMode.toLowerCase().includes('cycle 4');

  return (
    <>
      <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
        <div className="p-6 space-y-6">
          {/* Current Mode Display */}
          <div>
            <h3 className="text-sm font-medium text-gray-400 mb-2">Current Trading Mode</h3>
            <div className="flex items-center space-x-3">
              <span
                className={`inline-flex items-center px-4 py-2 rounded-lg text-lg font-medium border ${
                  isUniversalMode
                    ? 'bg-green-500/10 text-green-400 border-green-500/20'
                    : 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                }`}
              >
                {currentMode}
              </span>
              {!isUniversalMode && (
                <span className="text-sm text-gray-400">
                  (Session-Targeted Mode Active)
                </span>
              )}
            </div>
          </div>

          {/* Mode Parameters */}
          {!isUniversalMode && (
            <div className="bg-gray-750 rounded-lg p-4 border border-gray-600">
              <h4 className="text-sm font-semibold text-white mb-3">Current Mode Parameters</h4>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-400">Confidence Threshold:</span>
                  <span className="ml-2 text-white font-medium">Session-specific</span>
                </div>
                <div>
                  <span className="text-gray-400">Risk-Reward Ratio:</span>
                  <span className="ml-2 text-white font-medium">Session-optimized</span>
                </div>
                <div className="col-span-2">
                  <span className="text-gray-400">Active Sessions:</span>
                  <span className="ml-2 text-white font-medium">All sessions monitored</span>
                </div>
              </div>
            </div>
          )}

          {/* Rollback Button */}
          <div className="pt-4 border-t border-gray-700">
            <button
              onClick={handleRollbackClick}
              disabled={isUniversalMode || loading}
              className={`w-full px-6 py-4 rounded-lg font-bold text-lg shadow-lg transition-all ${
                isUniversalMode
                  ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                  : 'bg-orange-600 hover:bg-orange-700 text-white hover:shadow-xl'
              }`}
            >
              {isUniversalMode
                ? 'Already in Universal Cycle 4 Mode'
                : '🔄 Rollback to Universal Cycle 4'}
            </button>
            {!isUniversalMode && (
              <p className="mt-2 text-sm text-gray-400 text-center">
                This will switch all trading parameters to the proven Universal Cycle 4 configuration
              </p>
            )}
          </div>

          {/* Error Display */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}
        </div>
      </div>

      {/* Rollback Confirmation Modal */}
      {showModal && (
        <RollbackConfirmationModal
          currentMode={currentMode}
          onConfirm={handleConfirmRollback}
          onCancel={() => setShowModal(false)}
          loading={loading}
        />
      )}
    </>
  );
}
