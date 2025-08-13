/**
 * Loading skeleton components for different UI elements
 */

interface SkeletonProps {
  className?: string
}

/**
 * Basic skeleton element
 */
export function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div className={`animate-pulse bg-gray-200 dark:bg-gray-700 rounded ${className}`} />
  )
}

/**
 * Card loading skeleton
 */
export function CardSkeleton({ className = '' }: SkeletonProps) {
  return (
    <div className={`bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6 shadow-sm ${className}`}>
      <div className="space-y-4">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-8 w-24" />
        <Skeleton className="h-4 w-40" />
      </div>
    </div>
  )
}

/**
 * Table row loading skeleton
 */
export function TableRowSkeleton() {
  return (
    <tr>
      <td className="px-6 py-4">
        <Skeleton className="h-4 w-24" />
      </td>
      <td className="px-6 py-4">
        <Skeleton className="h-4 w-16" />
      </td>
      <td className="px-6 py-4">
        <Skeleton className="h-4 w-20" />
      </td>
      <td className="px-6 py-4">
        <Skeleton className="h-4 w-12" />
      </td>
    </tr>
  )
}

/**
 * List item loading skeleton
 */
export function ListItemSkeleton() {
  return (
    <div className="flex justify-between py-2 border-b border-gray-200 dark:border-gray-800">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="h-4 w-16" />
    </div>
  )
}

/**
 * Dashboard grid loading skeleton
 */
export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div>
        <Skeleton className="h-8 w-64 mb-2" />
        <Skeleton className="h-4 w-96" />
      </div>
      
      <div className="grid gap-6 grid-cols-1 md:grid-cols-2 xl:grid-cols-4">
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
      </div>
      
      <div className="grid gap-6 grid-cols-1 lg:grid-cols-2">
        <CardSkeleton className="h-64" />
        <CardSkeleton className="h-64" />
      </div>
    </div>
  )
}

/**
 * Generic loading skeleton for flexible use
 */
export function LoadingSkeleton({ className = '' }: SkeletonProps) {
  return <Skeleton className={className} />
}