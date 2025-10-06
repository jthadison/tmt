/**
 * Sparkline Chart Component
 * Lightweight performance trend visualization
 * Story 7.3: Supporting component for agent performance cards
 */

'use client';

import React from 'react';

interface SparklineProps {
  data: number[];
  height?: number;
  width?: number;
  color?: string;
  className?: string;
}

export function Sparkline({
  data,
  height = 40,
  width = 100,
  color = '#22c55e',
  className = ''
}: SparklineProps) {
  if (!data || data.length === 0) {
    return (
      <div
        className={`flex items-center justify-center ${className}`}
        style={{ height, width }}
      >
        <span className="text-xs text-gray-400">No data</span>
      </div>
    );
  }

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1; // Avoid division by zero

  // Calculate points for the polyline
  const points = data
    .map((value, index) => {
      const x = (index / (data.length - 1)) * width;
      const y = height - ((value - min) / range) * height;
      return `${x},${y}`;
    })
    .join(' ');

  // Determine color based on trend
  const trend = data[data.length - 1] >= data[0];
  const strokeColor = trend ? color : '#ef4444';

  return (
    <svg
      width={width}
      height={height}
      className={className}
      style={{ display: 'block' }}
    >
      <polyline
        points={points}
        fill="none"
        stroke={strokeColor}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/**
 * Generate sparkline data from agent performance history
 * For now, generates mock data - can be replaced with real data
 */
export function generateSparklineData(
  winRate: number,
  dataPoints: number = 10
): number[] {
  const data: number[] = [];
  let current = winRate;

  for (let i = 0; i < dataPoints; i++) {
    // Random walk with slight mean reversion
    const change = (Math.random() - 0.5) * 10;
    current = Math.max(0, Math.min(100, current + change));
    data.push(current);
  }

  // Ensure last point is close to actual win rate
  data[data.length - 1] = winRate;

  return data;
}
