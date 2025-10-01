'use client';

/**
 * Circuit Breaker Widget Component
 * Displays real-time circuit breaker status with thresholds and reset functionality
 */

import React, { useState } from 'react';
import { useCircuitBreaker } from '@/hooks/useCircuitBreaker';
import ThresholdDisplay from './ThresholdDisplay';
import ResetBreakersModal from './ResetBreakersModal';

// Heroicons
const TrendingDownIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
  </svg>
);

const ChartBarIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
  </svg>
);

const ExclamationTriangleIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
  </svg>
);

export default function CircuitBreakerWidget() {
  const { status, loading, error, refresh } = useCircuitBreaker();
  const [isResetModalOpen, setIsResetModalOpen] = useState(false);

  if (loading && !status) {
    return (
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="flex items-center justify-center space-x-2 text-gray-400">
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
          <span>Loading circuit breaker status...</span>
        </div>
      </div>
    );
  }

  if (error && !status) {
    return (
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="flex flex-col items-center space-y-2">
          <p className="text-red-400 text-sm text-center">{error}</p>
          <button
            onClick={refresh}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!status) return null;

  return (
    <>
      <div className="bg-gray-800 rounded-lg p-4 space-y-4">
        {/* Daily Loss */}
        <ThresholdDisplay
          label="Daily Loss"
          icon={TrendingDownIcon}
          current={Math.abs(status.daily_loss.current)}
          threshold={status.daily_loss.threshold}
          limit={status.daily_loss.limit}
          unit="$"
        />

        {/* Account Drawdown */}
        <ThresholdDisplay
          label="Account Drawdown"
          icon={ChartBarIcon}
          current={status.account_drawdown.current}
          threshold={status.account_drawdown.threshold}
          limit={status.account_drawdown.limit}
          unit="%"
        />

        {/* Consecutive Losses */}
        <ThresholdDisplay
          label="Consecutive Losses"
          icon={ExclamationTriangleIcon}
          current={status.consecutive_losses.current}
          threshold={status.consecutive_losses.threshold}
          limit={status.consecutive_losses.limit}
          unit=""
          formatValue={(val) => val.toString()}
        />

        {/* Breaker State Indicator */}
        <div className="pt-3 border-t border-gray-700">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Breaker State</span>
            <span
              className={`text-sm font-bold uppercase px-2 py-1 rounded ${
                status.state === 'open'
                  ? 'bg-red-900/50 text-red-400'
                  : status.state === 'half_open'
                  ? 'bg-yellow-900/50 text-yellow-400'
                  : 'bg-green-900/50 text-green-400'
              }`}
            >
              {status.state}
            </span>
          </div>
        </div>

        {/* Last Triggered */}
        {status.last_triggered && (
          <div className="text-xs text-yellow-400 border-t border-gray-700 pt-3">
            <div className="flex items-start space-x-2">
              <ExclamationTriangleIcon className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Last Triggered</p>
                <p className="text-gray-400">
                  {status.last_triggered.type} at{' '}
                  {new Date(status.last_triggered.timestamp).toLocaleString()}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Reset Button */}
        <button
          onClick={() => setIsResetModalOpen(true)}
          className="w-full bg-gray-700 hover:bg-gray-600 text-white py-2 rounded transition-colors text-sm font-medium"
          aria-label="Reset circuit breakers"
        >
          Reset Circuit Breakers
        </button>
      </div>

      {/* Reset Modal */}
      <ResetBreakersModal
        isOpen={isResetModalOpen}
        onClose={() => setIsResetModalOpen(false)}
        onSuccess={() => {
          setIsResetModalOpen(false);
          refresh();
        }}
      />
    </>
  );
}
