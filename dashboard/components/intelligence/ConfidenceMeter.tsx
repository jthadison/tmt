/**
 * Confidence Meter Component
 *
 * Displays confidence level as a color-coded progress bar with 5 levels:
 * - 0-29%: Very Low (Red)
 * - 30-49%: Low (Orange)
 * - 50-69%: Medium (Yellow)
 * - 70-89%: High (Light Green)
 * - 90-100%: Very High (Dark Green)
 *
 * Story 7.1: AC4
 */

import React from 'react';
import { getConfidenceLevel, confidenceLevelConfig } from '@/types/intelligence';

export interface ConfidenceMeterProps {
  confidence: number; // 0-100
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

/**
 * ConfidenceMeter component displays a visual confidence indicator
 *
 * @param confidence - Confidence value from 0-100
 * @param showLabel - Whether to display label text (default: true)
 * @param size - Size variant: sm, md, lg (default: md)
 *
 * @example
 * <ConfidenceMeter confidence={85} />
 * <ConfidenceMeter confidence={45} showLabel={false} size="sm" />
 */
export function ConfidenceMeter({
  confidence,
  showLabel = true,
  size = 'md'
}: ConfidenceMeterProps) {
  const level = getConfidenceLevel(confidence);
  const { color, label } = confidenceLevelConfig[level];

  const heights = {
    sm: 'h-2',
    md: 'h-4',
    lg: 'h-6'
  };

  return (
    <div className="confidence-meter" data-testid="confidence-meter">
      {showLabel && (
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-foreground">Confidence</span>
          <span className="text-sm font-semibold" style={{ color }}>
            {confidence}% - {label}
          </span>
        </div>
      )}

      <div className={`w-full ${heights[size]} bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden`}>
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{
            width: `${confidence}%`,
            backgroundColor: color
          }}
          data-testid="confidence-bar"
          aria-valuenow={confidence}
          aria-valuemin={0}
          aria-valuemax={100}
          role="progressbar"
          aria-label={`Confidence: ${confidence}% - ${label}`}
        />
      </div>
    </div>
  );
}
