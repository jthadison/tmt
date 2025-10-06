/**
 * Outcome Badge Component
 * Displays trade outcome (WIN/LOSS/BREAKEVEN) with profit/loss amount
 * Story 7.2: AC2
 */

import React from 'react';

export interface OutcomeBadgeProps {
  outcome: 'WIN' | 'LOSS' | 'BREAKEVEN';
  profitLoss?: number;
}

/**
 * Display trade outcome as a colored badge
 */
export function OutcomeBadge({ outcome, profitLoss }: OutcomeBadgeProps) {
  const outcomeStyles = {
    WIN: {
      bg: 'bg-green-100 dark:bg-green-900/30',
      text: 'text-green-800 dark:text-green-300',
      border: 'border-green-300 dark:border-green-700'
    },
    LOSS: {
      bg: 'bg-red-100 dark:bg-red-900/30',
      text: 'text-red-800 dark:text-red-300',
      border: 'border-red-300 dark:border-red-700'
    },
    BREAKEVEN: {
      bg: 'bg-gray-100 dark:bg-gray-800',
      text: 'text-gray-800 dark:text-gray-300',
      border: 'border-gray-300 dark:border-gray-600'
    }
  };

  const style = outcomeStyles[outcome];

  return (
    <div
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border ${style.bg} ${style.text} ${style.border}`}
      data-testid="outcome-badge"
    >
      <span className="font-semibold text-sm">{outcome}</span>
      {profitLoss !== undefined && (
        <span className="text-sm font-mono">
          {profitLoss >= 0 ? '+' : ''}${profitLoss.toFixed(2)}
        </span>
      )}
    </div>
  );
}
