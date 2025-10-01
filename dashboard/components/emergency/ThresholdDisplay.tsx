'use client';

/**
 * Threshold Display Component
 * Displays a single threshold metric with progress bar and color-coding
 */

import React from 'react';

interface ThresholdDisplayProps {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  current: number;
  threshold: number;
  limit: number;
  unit: string;
  formatValue?: (value: number) => string;
}

export default function ThresholdDisplay({
  label,
  icon: Icon,
  current,
  threshold,
  limit,
  unit,
  formatValue,
}: ThresholdDisplayProps) {
  // Calculate percentage for progress bar (based on limit)
  const percentage = Math.min((current / limit) * 100, 100);

  // Determine color based on thresholds
  const getColor = () => {
    if (current >= limit) return 'red';
    if (current >= threshold) return 'yellow';
    return 'green';
  };

  const color = getColor();

  const colorClasses = {
    green: {
      text: 'text-green-400',
      bg: 'bg-green-500',
      marker: 'bg-green-600',
    },
    yellow: {
      text: 'text-yellow-400',
      bg: 'bg-yellow-500',
      marker: 'bg-yellow-600',
    },
    red: {
      text: 'text-red-400',
      bg: 'bg-red-500',
      marker: 'bg-red-600',
    },
  };

  const formatVal = formatValue || ((val: number) => {
    if (unit === '$') return `${unit}${val.toFixed(2)}`;
    if (unit === '%') return `${val.toFixed(1)}${unit}`;
    return `${val}${unit}`;
  });

  return (
    <div className="space-y-2">
      {/* Label and Current Value */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Icon className={`w-5 h-5 ${colorClasses[color].text}`} />
          <span className="text-gray-300 text-sm">{label}</span>
        </div>
        <span className={`font-bold text-lg ${colorClasses[color].text}`}>
          {formatVal(current)}
        </span>
      </div>

      {/* Progress Bar */}
      <div className="relative h-2 bg-gray-700 rounded-full overflow-hidden">
        {/* Current value fill */}
        <div
          className={`absolute inset-y-0 left-0 ${colorClasses[color].bg} transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />

        {/* Threshold marker (vertical line) */}
        {threshold < limit && (
          <div
            className="absolute inset-y-0 w-0.5 bg-yellow-400 z-10"
            style={{ left: `${(threshold / limit) * 100}%` }}
            title={`Threshold: ${formatVal(threshold)}`}
          />
        )}
      </div>

      {/* Text labels */}
      <div className="flex justify-between text-xs text-gray-400">
        <span>{formatVal(current)}</span>
        <span className="text-yellow-400">{formatVal(threshold)} threshold</span>
        <span className="text-red-400">{formatVal(limit)} limit</span>
      </div>
    </div>
  );
}
