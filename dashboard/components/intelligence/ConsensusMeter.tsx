/**
 * Consensus Meter Component
 *
 * Displays agent consensus as a circular progress indicator with:
 * - Percentage in center
 * - Circular progress bar filling clockwise
 * - Color based on consensus strength
 * - Optional threshold indicator
 *
 * Story 7.1: AC6
 */

import React from 'react';

export interface ConsensusMeterProps {
  percentage: number; // 0-100
  threshold?: number; // Required threshold (e.g., 70)
}

/**
 * ConsensusMeter displays circular consensus gauge
 *
 * Color mapping:
 * - <50%: Red (low consensus)
 * - 50-69%: Yellow (moderate consensus)
 * - 70-89%: Light Green (good consensus)
 * - 90-100%: Dark Green (strong consensus)
 *
 * @param percentage - Consensus percentage 0-100
 * @param threshold - Optional threshold to display (dotted line indicator)
 *
 * @example
 * <ConsensusMeter percentage={75} threshold={70} />
 */
export function ConsensusMeter({ percentage, threshold }: ConsensusMeterProps) {
  const getColor = (pct: number): string => {
    if (pct < 50) return '#ef4444'; // Red
    if (pct < 70) return '#eab308'; // Yellow
    if (pct < 90) return '#84cc16'; // Light Green
    return '#22c55e'; // Dark Green
  };

  const color = getColor(percentage);
  const radius = 70;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;
  const thresholdOffset = threshold
    ? circumference - (threshold / 100) * circumference
    : 0;

  return (
    <div className="consensus-meter relative w-40 h-40" data-testid="consensus-meter">
      <svg
        className="w-full h-full transform -rotate-90"
        viewBox="0 0 160 160"
        aria-label={`Consensus: ${percentage}%`}
      >
        {/* Background circle */}
        <circle
          cx="80"
          cy="80"
          r={radius}
          fill="none"
          stroke="#e5e7eb"
          strokeWidth="12"
          className="dark:stroke-gray-600"
        />

        {/* Progress circle */}
        <circle
          cx="80"
          cy="80"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          className="transition-all duration-500"
          data-testid="consensus-progress"
        />

        {/* Threshold indicator (dotted line) */}
        {threshold !== undefined && (
          <circle
            cx="80"
            cy="80"
            r={radius}
            fill="none"
            stroke="#9ca3af"
            strokeWidth="2"
            strokeDasharray="4 4"
            strokeDashoffset={thresholdOffset}
            data-testid="consensus-threshold"
          />
        )}
      </svg>

      {/* Center text */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div
          className="text-3xl font-bold"
          style={{ color }}
          data-testid="consensus-percentage"
        >
          {percentage}%
        </div>
        {threshold !== undefined && (
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Threshold: {threshold}%
          </div>
        )}
      </div>
    </div>
  );
}
