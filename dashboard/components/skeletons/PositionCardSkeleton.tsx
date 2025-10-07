/**
 * Position Card Skeleton Component
 * Story 9.1: Skeleton screen matching position card layout
 */

export function PositionCardSkeleton() {
  return (
    <div
      className="border rounded-lg p-4 bg-white dark:bg-gray-800"
      data-testid="position-card-skeleton"
    >
      {/* Symbol and Badge */}
      <div className="flex items-center gap-2 mb-3">
        <div
          className="skeleton h-6 w-20 rounded"
          data-testid="symbol-skeleton"
        />
        <div className="skeleton h-5 w-12 rounded" />
      </div>

      {/* Price */}
      <div
        className="skeleton h-8 w-24 rounded mb-2"
        data-testid="price-skeleton"
      />

      {/* Profit/Loss */}
      <div className="flex justify-between items-center">
        <div
          className="skeleton h-4 w-16 rounded"
          data-testid="pnl-skeleton"
        />
        <div className="skeleton h-4 w-12 rounded" />
      </div>
    </div>
  );
}
