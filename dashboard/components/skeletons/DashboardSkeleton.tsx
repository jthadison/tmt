/**
 * Dashboard Skeleton Component
 * Story 9.1: Full dashboard skeleton with header, stats, charts, and cards
 */

import { ChartSkeleton } from './ChartSkeleton';
import { PositionCardSkeleton } from './PositionCardSkeleton';
import { AgentCardSkeleton } from './AgentCardSkeleton';

export function DashboardSkeleton() {
  return (
    <div
      className="min-h-screen bg-gray-50 dark:bg-gray-900"
      data-testid="dashboard-skeleton"
    >
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center justify-between">
          <div className="skeleton h-8 w-32 rounded" />
          <div className="flex items-center gap-4">
            <div className="skeleton h-10 w-10 rounded-full" />
            <div className="skeleton h-10 w-10 rounded-full" />
          </div>
        </div>
      </header>

      {/* Main content */}
      <div className="container mx-auto p-6">
        {/* Stats row */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          {[...Array(4)].map((_, i) => (
            <div
              key={i}
              className="bg-white dark:bg-gray-800 rounded-lg p-4"
            >
              <div className="skeleton h-4 w-24 rounded mb-2" />
              <div className="skeleton h-8 w-20 rounded" />
            </div>
          ))}
        </div>

        {/* Chart */}
        <div className="mb-6">
          <ChartSkeleton />
        </div>

        {/* Position cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
          {[...Array(6)].map((_, i) => (
            <PositionCardSkeleton key={i} />
          ))}
        </div>

        {/* Agent status */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
          <div className="skeleton h-6 w-32 rounded mb-4" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(8)].map((_, i) => (
              <AgentCardSkeleton key={i} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
