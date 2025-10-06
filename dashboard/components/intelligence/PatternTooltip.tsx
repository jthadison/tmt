/**
 * Pattern Tooltip Component
 * Displays pattern details on hover
 * Story 7.2: AC6
 */

import React from 'react';
import { PatternData, formatPatternType } from '@/types/intelligence';
import { ConfidenceMeter } from './ConfidenceMeter';

export interface PatternTooltipProps {
  pattern: PatternData;
  position: { x: number; y: number };
  visible: boolean;
}

/**
 * Display pattern details in a tooltip
 */
export function PatternTooltip({ pattern, position, visible }: PatternTooltipProps) {
  if (!visible) return null;

  return (
    <div
      className="pattern-tooltip absolute z-50 bg-card border border-border rounded-lg shadow-xl p-4 max-w-xs pointer-events-none"
      style={{
        left: position.x,
        top: position.y,
        transform: 'translate(-50%, -100%) translateY(-10px)' // Position above cursor
      }}
      data-testid="pattern-tooltip"
    >
      {/* Pattern type and status */}
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-semibold text-sm text-foreground">
          {formatPatternType(pattern.patternType)}
          {pattern.phase && ` - ${pattern.phase}`}
        </h4>
        <StatusBadge status={pattern.status} />
      </div>

      {/* Confidence */}
      <div className="mb-3">
        <ConfidenceMeter confidence={pattern.confidence} size="sm" />
      </div>

      {/* Key characteristics */}
      <div className="mb-3">
        <h5 className="text-xs font-medium text-secondary mb-1">Key Characteristics:</h5>
        <ul className="text-xs space-y-0.5">
          {pattern.keyCharacteristics.map((char, index) => (
            <li key={index} className="flex items-start gap-1">
              <span className="text-primary mt-0.5">•</span>
              <span className="text-foreground">{char}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Risk:Reward */}
      {pattern.riskRewardRatio && (
        <div className="text-xs">
          <span className="text-secondary">Risk:Reward: </span>
          <span className="font-semibold text-success">1:{pattern.riskRewardRatio.toFixed(1)}</span>
        </div>
      )}
    </div>
  );
}

/**
 * Status badge component
 */
function StatusBadge({ status }: { status: 'forming' | 'confirmed' | 'invalidated' }) {
  const statusConfig = {
    forming: {
      label: 'Forming',
      className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300'
    },
    confirmed: {
      label: 'Confirmed',
      className: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
    },
    invalidated: {
      label: 'Invalidated',
      className: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
    }
  };

  const config = statusConfig[status];

  return (
    <span
      className={`px-2 py-0.5 rounded text-xs font-medium ${config.className}`}
      data-testid="pattern-status-badge"
    >
      {config.label}
    </span>
  );
}
