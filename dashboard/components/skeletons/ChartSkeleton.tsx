/**
 * Chart Skeleton Component
 * Story 9.1: Skeleton screen matching chart layout
 */

export function ChartSkeleton() {
  return (
    <div
      className="w-full h-80 bg-white dark:bg-gray-800 rounded-lg p-4"
      data-testid="chart-skeleton"
    >
      {/* Chart title */}
      <div className="skeleton h-6 w-40 rounded mb-4" />

      {/* Chart canvas area */}
      <div className="relative h-64">
        {/* Y-axis labels */}
        <div className="absolute left-0 top-0 bottom-0 flex flex-col justify-between">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="skeleton h-4 w-12 rounded" />
          ))}
        </div>

        {/* Chart grid (light lines) */}
        <div className="ml-16 h-full border-l border-b border-gray-200 dark:border-gray-700 relative">
          <div className="absolute inset-0 flex flex-col justify-between">
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                className="border-t border-gray-100 dark:border-gray-800"
              />
            ))}
          </div>
        </div>

        {/* X-axis labels */}
        <div className="absolute bottom-0 left-16 right-0 flex justify-between mt-2">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="skeleton h-4 w-16 rounded" />
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 mt-4">
        <div className="flex items-center gap-2">
          <div className="skeleton h-3 w-3 rounded-full" />
          <div className="skeleton h-4 w-20 rounded" />
        </div>
        <div className="flex items-center gap-2">
          <div className="skeleton h-3 w-3 rounded-full" />
          <div className="skeleton h-4 w-20 rounded" />
        </div>
      </div>
    </div>
  );
}
