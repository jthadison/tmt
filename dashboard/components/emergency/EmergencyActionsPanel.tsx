'use client';

/**
 * Emergency Actions Panel Component
 * Slide-out panel from right side with emergency actions and circuit breaker widget
 */

import React, { useState, useEffect } from 'react';
import { useKeyboardShortcut } from '@/hooks/useKeyboardShortcut';
import EmergencyStopModal from './EmergencyStopModal';
import ClosePositionsModal from './ClosePositionsModal';
import EmergencyRollbackModal from './EmergencyRollbackModal';
import CircuitBreakerWidget from './CircuitBreakerWidget';
import { useEmergencyStop } from '@/hooks/useEmergencyStop';

interface EmergencyActionsPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

// Heroicons
const XMarkIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

const QuestionMarkCircleIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const StopIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
  </svg>
);

const XCircleIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const ArrowUturnLeftIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 15L3 9m0 0l6-6M3 9h12a6 6 0 010 12h-3" />
  </svg>
);

interface QuickActionButtonProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  shortcut: string;
  color: 'red' | 'orange' | 'purple';
  onClick: () => void;
  disabled?: boolean;
}

function QuickActionButton({ icon: Icon, label, shortcut, color, onClick, disabled }: QuickActionButtonProps) {
  const colorClasses = {
    red: 'bg-red-600 hover:bg-red-700 border-red-500 text-white',
    orange: 'bg-orange-600 hover:bg-orange-700 border-orange-500 text-white',
    purple: 'bg-purple-600 hover:bg-purple-700 border-purple-500 text-white',
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`w-full flex items-center justify-between p-3 rounded-lg border-2 transition-all ${colorClasses[color]} disabled:opacity-50 disabled:cursor-not-allowed hover:scale-[1.02] active:scale-[0.98]`}
      aria-label={label}
    >
      <div className="flex items-center space-x-3">
        <Icon className="w-5 h-5" />
        <span className="font-semibold">{label}</span>
      </div>
      <span className="text-xs bg-black/20 px-2 py-1 rounded font-mono">{shortcut}</span>
    </button>
  );
}

export default function EmergencyActionsPanel({ isOpen, onClose }: EmergencyActionsPanelProps) {
  const [isStopModalOpen, setIsStopModalOpen] = useState(false);
  const [isCloseModalOpen, setIsCloseModalOpen] = useState(false);
  const [isRollbackModalOpen, setIsRollbackModalOpen] = useState(false);
  const [showHelp, setShowHelp] = useState(false);

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
  } = useEmergencyStop();

  // Keyboard shortcuts
  useKeyboardShortcut(['Control', 'Shift', 'C'], () => {
    if (isOpen && !isCloseModalOpen) {
      setIsCloseModalOpen(true);
    }
  }, { enabled: isOpen });

  useKeyboardShortcut(['Control', 'Shift', 'R'], () => {
    if (isOpen && !isRollbackModalOpen) {
      setIsRollbackModalOpen(true);
    }
  }, { enabled: isOpen });

  // Close panel on Escape key
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen, onClose]);

  const handleEmergencyStop = async (closePositions: boolean) => {
    try {
      const result = await executeEmergencyStop(closePositions);
      setExecutionResult({
        success: result.success,
        message: result.message,
        positionsClosed: result.positions_closed,
      });
    } catch (err) {
      console.error('Emergency stop error:', err);
    }
  };

  const handleResumeTrading = async () => {
    try {
      await executeResumeTrading();
      setIsStopModalOpen(false);
      setExecutionResult(null);
    } catch (err) {
      console.error('Resume trading error:', err);
    }
  };

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 backdrop-blur-sm"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Slide-out panel */}
      <div
        className={`fixed right-0 top-0 h-full w-96 bg-gray-900 border-l border-gray-700 shadow-2xl z-50 transform transition-transform duration-300 ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="emergency-panel-title"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700 bg-gray-800">
          <h2 id="emergency-panel-title" className="text-xl font-bold text-white">
            Emergency Actions
          </h2>
          <div className="flex items-center space-x-2">
            {/* Help Button */}
            <button
              onClick={() => setShowHelp(!showHelp)}
              className="p-2 text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-gray-700"
              aria-label="Show keyboard shortcuts"
              title="Show keyboard shortcuts"
            >
              <QuestionMarkCircleIcon className="w-5 h-5" />
            </button>

            {/* Close Button */}
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-gray-700"
              aria-label="Close panel"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Help Tooltip */}
        {showHelp && (
          <div className="p-4 bg-blue-900/20 border-b border-blue-700/50">
            <h3 className="text-sm font-semibold text-blue-400 mb-2">Keyboard Shortcuts</h3>
            <div className="space-y-1 text-xs text-gray-300">
              <div className="flex justify-between">
                <span>Toggle Panel:</span>
                <span className="font-mono bg-gray-800 px-2 py-0.5 rounded">Alt+E</span>
              </div>
              <div className="flex justify-between">
                <span>Emergency Stop:</span>
                <span className="font-mono bg-gray-800 px-2 py-0.5 rounded">Ctrl+Shift+S</span>
              </div>
              <div className="flex justify-between">
                <span>Close Positions:</span>
                <span className="font-mono bg-gray-800 px-2 py-0.5 rounded">Ctrl+Shift+C</span>
              </div>
              <div className="flex justify-between">
                <span>Emergency Rollback:</span>
                <span className="font-mono bg-gray-800 px-2 py-0.5 rounded">Ctrl+Shift+R</span>
              </div>
              <div className="flex justify-between">
                <span>Close Panel:</span>
                <span className="font-mono bg-gray-800 px-2 py-0.5 rounded">Escape</span>
              </div>
            </div>
          </div>
        )}

        {/* Content */}
        <div className="p-4 space-y-6 overflow-y-auto h-full pb-20">
          {/* Quick Actions Section */}
          <section>
            <h3 className="text-lg font-semibold text-white mb-3">Quick Actions</h3>
            <div className="space-y-3">
              <QuickActionButton
                icon={StopIcon}
                label="Stop Trading"
                shortcut="Ctrl+Shift+S"
                color="red"
                onClick={() => setIsStopModalOpen(true)}
                disabled={!canExecute}
              />
              <QuickActionButton
                icon={XCircleIcon}
                label="Close All Positions"
                shortcut="Ctrl+Shift+C"
                color="orange"
                onClick={() => setIsCloseModalOpen(true)}
              />
              <QuickActionButton
                icon={ArrowUturnLeftIcon}
                label="Emergency Rollback"
                shortcut="Ctrl+Shift+R"
                color="purple"
                onClick={() => setIsRollbackModalOpen(true)}
              />
            </div>
          </section>

          {/* Circuit Breaker Widget */}
          <section>
            <h3 className="text-lg font-semibold text-white mb-3">Circuit Breakers</h3>
            <CircuitBreakerWidget />
          </section>
        </div>
      </div>

      {/* Modals */}
      <EmergencyStopModal
        isOpen={isStopModalOpen}
        onClose={() => setIsStopModalOpen(false)}
        onConfirm={handleEmergencyStop}
        isExecuting={isExecuting}
        executionResult={executionResult}
        error={error}
        onResumeTrading={handleResumeTrading}
      />

      <ClosePositionsModal
        isOpen={isCloseModalOpen}
        onClose={() => setIsCloseModalOpen(false)}
        onSuccess={() => setIsCloseModalOpen(false)}
      />

      <EmergencyRollbackModal
        isOpen={isRollbackModalOpen}
        onClose={() => setIsRollbackModalOpen(false)}
        onSuccess={() => setIsRollbackModalOpen(false)}
      />
    </>
  );
}
