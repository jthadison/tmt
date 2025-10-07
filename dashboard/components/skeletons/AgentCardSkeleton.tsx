/**
 * Agent Card Skeleton Component
 * Story 9.1: Skeleton screen matching agent status card layout
 */

export function AgentCardSkeleton() {
  return (
    <div
      className="border rounded-lg p-4 bg-white dark:bg-gray-800"
      data-testid="agent-card-skeleton"
    >
      {/* Agent name and status indicator */}
      <div className="flex items-center justify-between mb-3">
        <div className="skeleton h-5 w-32 rounded" />
        <div className="skeleton h-3 w-3 rounded-full" />
      </div>

      {/* Confidence meter */}
      <div className="mb-3">
        <div className="skeleton h-4 w-24 rounded mb-2" />
        <div className="skeleton h-2 w-full rounded-full" />
      </div>

      {/* Reasoning text lines */}
      <div className="space-y-2">
        <div className="skeleton h-3 w-full rounded" />
        <div className="skeleton h-3 w-5/6 rounded" />
        <div className="skeleton h-3 w-4/6 rounded" />
      </div>
    </div>
  );
}
