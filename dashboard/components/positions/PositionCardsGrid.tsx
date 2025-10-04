/**
 * Position Cards Grid Component
 * Responsive grid of position cards with sorting and filtering
 */

import React, { useState, useMemo } from 'react'
import { RefreshCw, Filter, ArrowUpDown } from 'lucide-react'
import { Position, PositionSortOption } from '@/types/positions'
import { usePositions } from '@/hooks/usePositions'
import PositionCard from './PositionCard'
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton'
import { cn } from '@/lib/utils'

/**
 * Empty state component
 */
function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-12">
      <div className="text-gray-400 text-lg mb-2">{message}</div>
      <div className="text-gray-500 text-sm">
        Positions will appear here when trades are opened
      </div>
    </div>
  )
}

/**
 * Sort control component
 */
function SortControl({
  value,
  onChange,
}: {
  value: PositionSortOption
  onChange: (value: PositionSortOption) => void
}) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as PositionSortOption)}
        className="appearance-none bg-gray-800 text-white border border-gray-700 rounded px-3 py-2 pr-8 text-sm focus:outline-none focus:border-blue-500"
        aria-label="Sort positions"
      >
        <option value="pnl-high">P&L (Highest)</option>
        <option value="pnl-low">P&L (Lowest)</option>
        <option value="age-new">Newest First</option>
        <option value="age-old">Oldest First</option>
        <option value="instrument">Instrument</option>
      </select>
      <ArrowUpDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
    </div>
  )
}

/**
 * Filter control component
 */
function FilterControl({
  positions,
  activeFilters,
  onChange,
}: {
  positions: Position[]
  activeFilters: string[]
  onChange: (filters: string[]) => void
}) {
  const [isOpen, setIsOpen] = useState(false)

  // Get unique agent sources
  const agentSources = useMemo(() => {
    const sources = new Set(positions.map((p) => p.agentSource))
    return Array.from(sources).sort()
  }, [positions])

  const toggleFilter = (source: string) => {
    if (activeFilters.includes(source)) {
      onChange(activeFilters.filter((f) => f !== source))
    } else {
      onChange([...activeFilters, source])
    }
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="bg-gray-800 text-white border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500 flex items-center gap-2"
        aria-label="Filter positions"
      >
        <Filter className="w-4 h-4" />
        Filters
        {activeFilters.length > 0 && (
          <span className="bg-blue-500 text-white text-xs rounded-full px-2 py-0.5">
            {activeFilters.length}
          </span>
        )}
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
            aria-hidden="true"
          />
          <div className="absolute right-0 mt-2 w-56 bg-gray-800 border border-gray-700 rounded shadow-lg z-20">
            <div className="p-3">
              <div className="text-xs text-gray-400 font-semibold mb-2">Filter by Agent</div>
              {agentSources.length === 0 ? (
                <div className="text-xs text-gray-500">No agents</div>
              ) : (
                <div className="space-y-2">
                  {agentSources.map((source) => (
                    <label key={source} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={activeFilters.includes(source)}
                        onChange={() => toggleFilter(source)}
                        className="rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500"
                      />
                      <span className="text-sm text-white">{source}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
            {activeFilters.length > 0 && (
              <div className="border-t border-gray-700 p-2">
                <button
                  onClick={() => {
                    onChange([])
                    setIsOpen(false)
                  }}
                  className="w-full text-xs text-blue-400 hover:text-blue-300"
                >
                  Clear All
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}

/**
 * Skeleton loading state
 */
function PositionCardsGridSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="bg-gray-800 rounded-lg p-4 border-2 border-gray-700">
          <LoadingSkeleton className="h-6 w-24 mb-3" />
          <LoadingSkeleton className="h-10 w-32 mb-2" />
          <LoadingSkeleton className="h-4 w-20 mb-4" />
          <div className="grid grid-cols-2 gap-2 mb-3">
            <LoadingSkeleton className="h-4 w-20" />
            <LoadingSkeleton className="h-4 w-20" />
            <LoadingSkeleton className="h-4 w-20" />
            <LoadingSkeleton className="h-4 w-20" />
          </div>
          <LoadingSkeleton className="h-2 w-full mb-2" />
          <LoadingSkeleton className="h-2 w-full mb-3" />
          <div className="flex justify-between">
            <LoadingSkeleton className="h-3 w-16" />
            <LoadingSkeleton className="h-3 w-12" />
            <LoadingSkeleton className="h-3 w-20" />
          </div>
        </div>
      ))}
    </div>
  )
}

interface PositionCardsGridProps {
  /** Callback when position detail is requested */
  onPositionClick?: (position: Position) => void
  /** Callback when position close is requested */
  onPositionClose?: (positionId: string) => void
  /** Callback when position modify is requested */
  onPositionModify?: (positionId: string) => void
}

/**
 * Position cards grid component
 */
export function PositionCardsGrid({
  onPositionClick,
  onPositionClose,
  onPositionModify,
}: PositionCardsGridProps) {
  const { positions, isLoading, error, refreshPositions } = usePositions()
  const [sortBy, setSortBy] = useState<PositionSortOption>('pnl-high')
  const [filterBy, setFilterBy] = useState<string[]>([])

  // Sort positions
  const sortedPositions = useMemo(() => {
    const sorted = [...positions]

    switch (sortBy) {
      case 'pnl-high':
        return sorted.sort((a, b) => b.unrealizedPL - a.unrealizedPL)
      case 'pnl-low':
        return sorted.sort((a, b) => a.unrealizedPL - b.unrealizedPL)
      case 'age-new':
        return sorted.sort(
          (a, b) => new Date(b.openTime).getTime() - new Date(a.openTime).getTime()
        )
      case 'age-old':
        return sorted.sort(
          (a, b) => new Date(a.openTime).getTime() - new Date(b.openTime).getTime()
        )
      case 'instrument':
        return sorted.sort((a, b) => a.instrument.localeCompare(b.instrument))
      default:
        return sorted
    }
  }, [positions, sortBy])

  // Filter positions
  const filteredPositions = useMemo(() => {
    if (filterBy.length === 0) return sortedPositions
    return sortedPositions.filter((p) => filterBy.includes(p.agentSource))
  }, [sortedPositions, filterBy])

  // Handle position click
  const handlePositionClick = (position: Position) => {
    onPositionClick?.(position)
  }

  // Handle position close
  const handlePositionClose = (positionId: string) => {
    onPositionClose?.(positionId)
  }

  // Handle position modify
  const handlePositionModify = (positionId: string) => {
    onPositionModify?.(positionId)
  }

  // Error state
  if (error && !isLoading) {
    return (
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-white">Open Positions (0)</h2>
        </div>
        <div className="text-center py-12">
          <p className="text-red-400 mb-4">Failed to load positions: {error}</p>
          <button
            onClick={refreshPositions}
            className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded text-white flex items-center gap-2 mx-auto"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        </div>
      </section>
    )
  }

  // Loading state
  if (isLoading && positions.length === 0) {
    return (
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-white">Open Positions</h2>
        </div>
        <PositionCardsGridSkeleton />
      </section>
    )
  }

  return (
    <section className="space-y-4">
      {/* Header with count and controls */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">
          Open Positions ({positions.length})
        </h2>
        <div className="flex items-center space-x-2">
          <SortControl value={sortBy} onChange={setSortBy} />
          <FilterControl
            positions={positions}
            activeFilters={filterBy}
            onChange={setFilterBy}
          />
          <button
            onClick={refreshPositions}
            className="p-2 bg-gray-800 border border-gray-700 rounded hover:bg-gray-700 transition-colors"
            aria-label="Refresh positions"
            title="Refresh positions"
          >
            <RefreshCw className={cn('w-4 h-4 text-gray-400', isLoading && 'animate-spin')} />
          </button>
        </div>
      </div>

      {/* Grid */}
      {filteredPositions.length === 0 ? (
        <EmptyState
          message={
            filterBy.length > 0
              ? 'No positions match current filters'
              : 'No open positions'
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredPositions.map((position) => (
            <PositionCard
              key={position.id}
              position={position}
              onClose={handlePositionClose}
              onModify={handlePositionModify}
              onClick={handlePositionClick}
            />
          ))}
        </div>
      )}
    </section>
  )
}

export default PositionCardsGrid
