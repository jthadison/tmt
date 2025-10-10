/**
 * Pattern Performance Card Component (Story 12.2 - Task 5)
 *
 * Displays win rate by Wyckoff pattern type with horizontal bars and significance markers
 */

'use client'

import React from 'react'
import { PatternPerformanceData, getWinRateColor, WyckoffPattern } from '@/types/analytics122'

interface PatternPerformanceCardProps {
  data: PatternPerformanceData | null
  loading: boolean
  error: Error | null
}

const PATTERNS: WyckoffPattern[] = ['Spring', 'Upthrust', 'Accumulation', 'Distribution']

/**
 * Get color for win rate
 */
function getBarColor(winRate: number): string {
  const color = getWinRateColor(winRate)
  switch (color) {
    case 'green': return 'bg-green-500'
    case 'yellow': return 'bg-yellow-500'
    case 'red': return 'bg-red-500'
  }
}

/**
 * Pattern Performance Card Component
 */
export default function PatternPerformanceCard({
  data,
  loading,
  error
}: PatternPerformanceCardProps) {
  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">
        Win Rate by Pattern Type
      </h2>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
          <p className="text-sm text-red-800">
            <span className="font-semibold">Error:</span> {error.message}
          </p>
        </div>
      )}

      {loading && (
        <div className="space-y-4">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="animate-pulse">
              <div className="flex items-center justify-between mb-2">
                <div className="h-4 w-32 bg-gray-200 rounded"></div>
                <div className="h-4 w-16 bg-gray-200 rounded"></div>
              </div>
              <div className="h-6 bg-gray-200 rounded"></div>
            </div>
          ))}
        </div>
      )}

      {!loading && !error && data && (
        <div className="space-y-4">
          {PATTERNS.map(pattern => {
            const metrics = data[pattern] || {
              win_rate: 0,
              sample_size: 0,
              significant: false
            }

            const barColor = getBarColor(metrics.win_rate)
            const hasData = metrics.sample_size > 0

            return (
              <div key={pattern} className={!hasData ? 'opacity-50' : ''}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">{pattern}</span>
                    <span className="text-xs text-gray-500">n={metrics.sample_size}</span>
                    {metrics.significant && (
                      <span
                        className="text-green-600 text-sm"
                        title="Statistically significant (n≥20)"
                      >
                        ✓
                      </span>
                    )}
                  </div>
                  <span className="text-sm font-semibold text-gray-700">
                    {metrics.win_rate.toFixed(1)}%
                  </span>
                </div>

                <div className="relative">
                  <div className="w-full bg-gray-200 rounded-full h-6 overflow-hidden">
                    <div
                      className={`h-6 rounded-full transition-all duration-300 ${barColor} flex items-center justify-end pr-2`}
                      style={{ width: `${Math.min(metrics.win_rate, 100)}%` }}
                    >
                      {metrics.win_rate > 15 && (
                        <span className="text-xs text-white font-medium">
                          {metrics.win_rate.toFixed(1)}%
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {hasData && (
                  <div className="mt-1 text-xs text-gray-500">
                    {metrics.sample_size >= 20
                      ? 'Statistically significant sample'
                      : `Need ${20 - metrics.sample_size} more trades for significance`}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {!loading && !error && data && Object.keys(data).length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p>No pattern data available</p>
          <p className="text-sm mt-2">Try adjusting the date range filter</p>
        </div>
      )}

      <div className="mt-4 pt-4 border-t border-gray-200">
        <p className="text-xs text-gray-600">
          <span className="text-green-600">✓</span> indicates statistically significant sample (n≥20 trades)
        </p>
      </div>
    </div>
  )
}
