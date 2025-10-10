/**
 * Session Performance Card Component (Story 12.2 - Task 4)
 *
 * Displays win rate breakdown by trading session with color-coded indicators
 */

'use client'

import React from 'react'
import { SessionPerformanceData, getWinRateColor, TradingSession } from '@/types/analytics122'

interface SessionPerformanceCardProps {
  data: SessionPerformanceData | null
  loading: boolean
  error: Error | null
}

const SESSIONS: TradingSession[] = ['TOKYO', 'LONDON', 'NY', 'SYDNEY', 'OVERLAP']

/**
 * Get Tailwind CSS color classes based on win rate
 */
function getColorClasses(winRate: number): { bg: string; text: string; border: string } {
  const color = getWinRateColor(winRate)

  switch (color) {
    case 'green':
      return { bg: 'bg-green-100', text: 'text-green-800', border: 'border-green-500' }
    case 'yellow':
      return { bg: 'bg-yellow-100', text: 'text-yellow-800', border: 'border-yellow-500' }
    case 'red':
      return { bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-500' }
  }
}

/**
 * Skeleton loader for session row
 */
function SessionRowSkeleton() {
  return (
    <div className="flex items-center justify-between py-3 border-b border-gray-200 animate-pulse">
      <div className="flex items-center gap-3 flex-1">
        <div className="h-4 w-20 bg-gray-200 rounded"></div>
        <div className="h-4 w-12 bg-gray-200 rounded"></div>
      </div>
      <div className="flex items-center gap-4">
        <div className="h-6 w-16 bg-gray-200 rounded"></div>
        <div className="h-6 w-24 bg-gray-200 rounded"></div>
      </div>
    </div>
  )
}

/**
 * Session Performance Card Component
 */
export default function SessionPerformanceCard({
  data,
  loading,
  error
}: SessionPerformanceCardProps) {
  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">
        Win Rate by Trading Session
      </h2>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
          <p className="text-sm text-red-800">
            <span className="font-semibold">Error loading data:</span> {error.message}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
          >
            Retry
          </button>
        </div>
      )}

      {loading && (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map(i => (
            <SessionRowSkeleton key={i} />
          ))}
        </div>
      )}

      {!loading && !error && data && (
        <div className="space-y-2">
          {SESSIONS.map(session => {
            const metrics = data[session] || {
              win_rate: 0,
              total_trades: 0,
              winning_trades: 0,
              losing_trades: 0
            }

            const colors = getColorClasses(metrics.win_rate)
            const hasData = metrics.total_trades > 0

            return (
              <div
                key={session}
                className={`flex items-center justify-between py-3 border-b border-gray-200 last:border-b-0 ${
                  !hasData ? 'opacity-50' : ''
                }`}
              >
                <div className="flex items-center gap-3 flex-1">
                  <span className="font-semibold text-gray-900 w-24">
                    {session}
                  </span>
                  <span className="text-sm text-gray-500">
                    n={metrics.total_trades}
                  </span>
                </div>

                <div className="flex items-center gap-4">
                  <span
                    className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${colors.bg} ${colors.text}`}
                  >
                    {metrics.win_rate.toFixed(1)}%
                  </span>

                  <div className="w-48 bg-gray-200 rounded-full h-2.5 overflow-hidden">
                    <div
                      className={`h-2.5 rounded-full transition-all duration-300 ${colors.border.replace('border-', 'bg-')}`}
                      style={{ width: `${Math.min(metrics.win_rate, 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {!loading && !error && data && Object.keys(data).length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p>No session data available</p>
          <p className="text-sm mt-2">Try adjusting the date range filter</p>
        </div>
      )}
    </div>
  )
}
