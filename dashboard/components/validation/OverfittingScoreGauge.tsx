/**
 * OverfittingScoreGauge Component - Story 11.8, Task 2
 *
 * Displays current overfitting score with color-coded gauge (green/yellow/red zones)
 */

'use client';

import React from 'react';
import Card from '@/components/ui/Card';

interface OverfittingScoreGaugeProps {
  score: number;
  thresholds?: {
    warning: number;
    critical: number;
  };
  loading?: boolean;
}

export function OverfittingScoreGauge({
  score,
  thresholds = { warning: 0.3, critical: 0.5 },
  loading = false,
}: OverfittingScoreGaugeProps) {
  const getStatus = (score: number) => {
    if (score < thresholds.warning) {
      return { color: 'text-green-500', bg: 'bg-green-50', label: '✅ Healthy', status: 'green' };
    }
    if (score < thresholds.critical) {
      return { color: 'text-yellow-600', bg: 'bg-yellow-50', label: '⚠️ Warning', status: 'yellow' };
    }
    return { color: 'text-red-600', bg: 'bg-red-50', label: '❌ Critical', status: 'red' };
  };

  const status = getStatus(score);

  // Calculate gauge position (0-100%)
  const gaugePosition = Math.min(score * 100, 100);

  // Create gradient colors for gauge zones
  const getGaugeColor = () => {
    if (score < thresholds.warning) return '#10b981'; // green-500
    if (score < thresholds.critical) return '#f59e0b'; // yellow-500
    return '#ef4444'; // red-500
  };

  if (loading) {
    return (
      <Card className="p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6 hover:shadow-lg transition-shadow">
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-gray-900">Overfitting Score</h3>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${status.bg} ${status.color}`}>
            {status.label}
          </span>
        </div>

        {/* Score Display */}
        <div className="flex-1 flex flex-col items-center justify-center mb-6">
          <div className="relative w-48 h-48 mb-4">
            {/* Background circle */}
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
              {/* Background arc */}
              <circle
                cx="50"
                cy="50"
                r="40"
                fill="none"
                stroke="#e5e7eb"
                strokeWidth="8"
                strokeDasharray="251.2"
                strokeDashoffset="0"
              />

              {/* Score arc */}
              <circle
                cx="50"
                cy="50"
                r="40"
                fill="none"
                stroke={getGaugeColor()}
                strokeWidth="8"
                strokeDasharray="251.2"
                strokeDashoffset={251.2 - (gaugePosition / 100) * 251.2}
                strokeLinecap="round"
                className="transition-all duration-500"
              />
            </svg>

            {/* Center score text */}
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className={`text-4xl font-bold ${status.color}`}>
                {score.toFixed(3)}
              </span>
              <span className="text-sm text-gray-500 mt-1">Score</span>
            </div>
          </div>
        </div>

        {/* Threshold indicators */}
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-gray-600">Warning Threshold:</span>
            <span className="font-medium text-yellow-600">{thresholds.warning.toFixed(2)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-600">Critical Threshold:</span>
            <span className="font-medium text-red-600">{thresholds.critical.toFixed(2)}</span>
          </div>
        </div>

        {/* Description */}
        <div className="mt-4 p-3 bg-gray-50 rounded-lg">
          <p className="text-xs text-gray-600">
            Overfitting score measures the difference between in-sample and out-of-sample performance.
            Lower scores indicate better generalization.
          </p>
        </div>
      </div>
    </Card>
  );
}
