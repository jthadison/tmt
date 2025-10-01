'use client';

/**
 * Emergency Stop Button Component
 * Persistent button in header for emergency trading halt
 */

import React, { useState } from 'react';
import { useEmergencyStop } from '@/hooks/useEmergencyStop';
import { useKeyboardShortcut } from '@/hooks/useKeyboardShortcut';
import EmergencyStopModal from './EmergencyStopModal';

export default function EmergencyStopButton() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [executionResult, setExecutionResult] = useState<{
    success: boolean;
    message: string;
    positionsClosed: number;
  } | null>(null);

  const {
    executeEmergencyStop,
    executeResumeTrading,
    isExecuting,
    canExecute,
    error,
    cooldownRemaining,
  } = useEmergencyStop();

  // Keyboard shortcut: Ctrl+Shift+S
  useKeyboardShortcut(['Control', 'Shift', 'S'], () => {
    if (canExecute && !isModalOpen) {
      setIsModalOpen(true);
    }
  });

  const handleOpenModal = () => {
    if (canExecute) {
      setExecutionResult(null);
      setIsModalOpen(true);
    }
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setExecutionResult(null);
  };

  const handleConfirm = async (closePositions: boolean) => {
    try {
      const result = await executeEmergencyStop(closePositions);
      setExecutionResult({
        success: result.success,
        message: result.message,
        positionsClosed: result.positions_closed,
      });
    } catch (err) {
      // Error is handled by the hook and stored in error state
      console.error('Emergency stop error:', err);
    }
  };

  const handleResumeTrading = async () => {
    try {
      await executeResumeTrading();
      handleCloseModal();
    } catch (err) {
      console.error('Resume trading error:', err);
    }
  };

  const getTooltipText = () => {
    if (!canExecute) {
      return `Emergency Stop (available in ${cooldownRemaining}s)`;
    }
    return 'Emergency Stop Trading (Ctrl+Shift+S)';
  };

  return (
    <>
      <div className="relative group">
        <button
          onClick={handleOpenModal}
          disabled={!canExecute}
          className="flex items-center space-x-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg shadow-lg border-2 border-red-500 transition-all hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
          aria-label="Emergency stop trading button"
          title={getTooltipText()}
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <span className="hidden sm:inline">Emergency Stop</span>
        </button>

        {/* Tooltip */}
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50 border border-gray-700">
          {getTooltipText()}
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1">
            <div className="border-4 border-transparent border-t-gray-900"></div>
          </div>
        </div>

        {/* Cooldown indicator */}
        {!canExecute && cooldownRemaining > 0 && (
          <div className="absolute -top-2 -right-2 bg-yellow-500 text-gray-900 text-xs font-bold rounded-full w-6 h-6 flex items-center justify-center">
            {cooldownRemaining}
          </div>
        )}
      </div>

      <EmergencyStopModal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        onConfirm={handleConfirm}
        isExecuting={isExecuting}
        executionResult={executionResult}
        error={error}
        onResumeTrading={handleResumeTrading}
      />
    </>
  );
}
