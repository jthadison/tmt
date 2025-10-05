/**
 * Decision Badge Component
 *
 * Displays final trading decision with threshold explanation:
 * - Large badge with decision (BUY/SELL/NEUTRAL)
 * - Checkmark or warning icon based on threshold met
 * - Explanation text with percentages
 * - Color coding matching action
 *
 * Story 7.1: AC7
 */

import React from 'react';
import { CheckCircle, AlertTriangle } from 'lucide-react';

export interface DecisionBadgeProps {
  decision: 'BUY' | 'SELL' | 'NEUTRAL';
  thresholdMet: boolean;
  threshold: number;
  actualPercentage: number;
}

/**
 * DecisionBadge displays final trading decision with threshold status
 *
 * @param decision - Final decision (BUY/SELL/NEUTRAL)
 * @param thresholdMet - Whether consensus threshold was met
 * @param threshold - Required threshold percentage
 * @param actualPercentage - Actual consensus percentage achieved
 *
 * @example
 * <DecisionBadge
 *   decision="BUY"
 *   thresholdMet={true}
 *   threshold={70}
 *   actualPercentage={75}
 * />
 */
export function DecisionBadge({
  decision,
  thresholdMet,
  threshold,
  actualPercentage
}: DecisionBadgeProps) {
  const config = {
    BUY: {
      bg: 'bg-green-50 dark:bg-green-900/20',
      text: 'text-green-700 dark:text-green-400',
      border: 'border-green-300 dark:border-green-700'
    },
    SELL: {
      bg: 'bg-red-50 dark:bg-red-900/20',
      text: 'text-red-700 dark:text-red-400',
      border: 'border-red-300 dark:border-red-700'
    },
    NEUTRAL: {
      bg: 'bg-gray-50 dark:bg-gray-800/50',
      text: 'text-gray-700 dark:text-gray-400',
      border: 'border-gray-300 dark:border-gray-600'
    }
  };

  const { bg, text, border } = config[decision];

  return (
    <div
      className={`decision-badge p-4 rounded-lg border-2 ${bg} ${border}`}
      data-testid="decision-badge"
    >
      <div className="flex items-center gap-3">
        {thresholdMet ? (
          <CheckCircle className={`w-8 h-8 ${text}`} data-testid="check-icon" />
        ) : (
          <AlertTriangle
            className="w-8 h-8 text-yellow-600 dark:text-yellow-500"
            data-testid="warning-icon"
          />
        )}

        <div>
          <div className={`text-2xl font-bold ${text}`} data-testid="decision-text">
            {decision}
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            {thresholdMet ? (
              <span data-testid="threshold-met">
                ✓ Threshold met ({actualPercentage}% ≥ {threshold}% required)
              </span>
            ) : (
              <span
                className="text-yellow-700 dark:text-yellow-500"
                data-testid="threshold-not-met"
              >
                ⚠ Threshold NOT met ({actualPercentage}% &lt; {threshold}% required)
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
