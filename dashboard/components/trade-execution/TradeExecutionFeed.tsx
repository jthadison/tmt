'use client'

import React, { useState, useEffect, useRef, useMemo } from 'react'
import { 
  TradeExecution, 
  ExecutionStatus, 
  OrderDirection,
  ExecutionFilter,
  ExecutionSort
} from '@/types/tradeExecution'
import Card from '@/components/ui/Card'
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton'

/**
 * Props for TradeExecutionFeed component
 */
interface TradeExecutionFeedProps {
  /** Array of trade executions to display */
  executions: TradeExecution[]
  /** Loading state */
  loading?: boolean
  /** Error message */
  error?: string
  /** Current filter settings */
  filter?: ExecutionFilter
  /** Current sort settings */
  sort?: ExecutionSort
  /** Whether to auto-scroll to newest trades */
  autoScroll?: boolean
  /** Maximum height for the feed */
  maxHeight?: number
  /** Callback when execution is clicked */
  onExecutionClick?: (execution: TradeExecution) => void
  /** Callback when filter changes */
  onFilterChange?: (filter: ExecutionFilter) => void
  /** Callback when sort changes */
  onSortChange?: (sort: ExecutionSort) => void
  /** Callback to load more executions */
  onLoadMore?: () => void
  /** Whether there are more executions to load */
  hasMore?: boolean
  /** Show compact view */
  compact?: boolean
}

/**
 * Individual execution row component
 */
function ExecutionRow({ 
  execution, 
  onClick, 
  compact = false 
}: { 
  execution: TradeExecution
  onClick?: (execution: TradeExecution) => void
  compact?: boolean
}) {
  const getStatusColor = (status: ExecutionStatus): string => {
    switch (status) {
      case 'filled':
        return 'text-green-400 bg-green-900/20 border-green-500/30'
      case 'partial':
        return 'text-yellow-400 bg-yellow-900/20 border-yellow-500/30'
      case 'pending':
        return 'text-blue-400 bg-blue-900/20 border-blue-500/30'
      case 'rejected':
        return 'text-red-400 bg-red-900/20 border-red-500/30'
      case 'cancelled':
        return 'text-gray-400 bg-gray-900/20 border-gray-500/30'
      default:
        return 'text-gray-400 bg-gray-900/20 border-gray-500/30'
    }
  }

  const getStatusIcon = (status: ExecutionStatus): string => {
    switch (status) {
      case 'filled': return '✓'
      case 'partial': return '◐'
      case 'pending': return '⋯'
      case 'rejected': return '✗'
      case 'cancelled': return '○'
      default: return '?'
    }
  }

  const getDirectionColor = (direction: OrderDirection): string => {
    return direction === 'buy' ? 'text-green-400' : 'text-red-400'
  }

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 5
    }).format(amount)
  }

  const formatNumber = (num: number): string => {
    return new Intl.NumberFormat('en-US').format(num)
  }

  const formatTime = (date: Date): string => {
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const formatSlippage = (slippage: number): string => {
    const pips = slippage * 10000 // Convert to pips for major pairs
    return `${pips >= 0 ? '+' : ''}${pips.toFixed(1)}p`
  }

  const isNewExecution = () => {
    const executionTime = execution.timestamps.lastUpdate.getTime()
    const now = Date.now()
    return now - executionTime < 10000 // Less than 10 seconds old
  }

  if (compact) {
    return (
      <div 
        className={`flex items-center justify-between p-2 border-b border-gray-700 hover:bg-gray-800/50 transition-colors cursor-pointer ${
          isNewExecution() ? 'bg-blue-900/20 border-l-4 border-l-blue-500' : ''
        }`}
        onClick={() => onClick?.(execution)}
      >
        <div className="flex items-center space-x-3 min-w-0 flex-1">
          {/* Status */}
          <div className={`px-2 py-1 rounded text-xs font-medium border ${getStatusColor(execution.status)}`}>
            <span className="mr-1">{getStatusIcon(execution.status)}</span>
            {execution.status.toUpperCase()}
          </div>
          
          {/* Instrument & Direction */}
          <div className="min-w-0">
            <div className="font-medium text-white">{execution.instrument}</div>
            <div className={`text-sm font-semibold ${getDirectionColor(execution.direction)}`}>
              {execution.direction.toUpperCase()} {formatNumber(execution.executedSize)}
            </div>
          </div>
        </div>
        
        {/* Price & Time */}
        <div className="text-right">
          <div className="text-white font-medium">
            {execution.executedPrice ? formatCurrency(execution.executedPrice) : '-'}
          </div>
          <div className="text-xs text-gray-400">
            {formatTime(execution.timestamps.lastUpdate)}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div 
      className={`p-4 border-b border-gray-700 hover:bg-gray-800/50 transition-colors cursor-pointer ${
        isNewExecution() ? 'bg-blue-900/20 border-l-4 border-l-blue-500' : ''
      }`}
      onClick={() => onClick?.(execution)}
    >
      <div className="grid grid-cols-12 gap-4 items-center">
        {/* Time */}
        <div className="col-span-1">
          <div className="text-xs text-gray-400">
            {formatTime(execution.timestamps.lastUpdate)}
          </div>
        </div>
        
        {/* Status */}
        <div className="col-span-2">
          <div className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium border ${getStatusColor(execution.status)}`}>
            <span className="mr-1">{getStatusIcon(execution.status)}</span>
            {execution.status.toUpperCase()}
          </div>
        </div>
        
        {/* Instrument */}
        <div className="col-span-1">
          <div className="font-medium text-white">{execution.instrument}</div>
        </div>
        
        {/* Direction & Size */}
        <div className="col-span-2">
          <div className={`font-semibold ${getDirectionColor(execution.direction)}`}>
            {execution.direction.toUpperCase()}
          </div>
          <div className="text-sm text-gray-400">
            {formatNumber(execution.executedSize)} / {formatNumber(execution.requestedSize)}
          </div>
        </div>
        
        {/* Price */}
        <div className="col-span-1">
          <div className="text-white font-medium">
            {execution.executedPrice ? formatCurrency(execution.executedPrice) : '-'}
          </div>
          {execution.requestedPrice && (
            <div className="text-xs text-gray-400">
              Req: {formatCurrency(execution.requestedPrice)}
            </div>
          )}
        </div>
        
        {/* Slippage */}
        <div className="col-span-1">
          <div className={`font-medium ${
            execution.slippage > 0.0010 ? 'text-red-400' : 
            execution.slippage > 0.0005 ? 'text-yellow-400' : 'text-green-400'
          }`}>
            {formatSlippage(execution.slippage)}
          </div>
        </div>
        
        {/* Account */}
        <div className="col-span-2">
          <div className="text-sm text-white">{execution.accountAlias}</div>
          <div className="text-xs text-gray-400">{execution.broker}</div>
        </div>
        
        {/* Order ID */}
        <div className="col-span-2">
          <div className="text-xs text-gray-400 font-mono">
            {execution.orderId.length > 12 ? 
              `${execution.orderId.substring(0, 12)}...` : 
              execution.orderId
            }
          </div>
          {execution.reasonMessage && (
            <div className="text-xs text-red-400 truncate">
              {execution.reasonMessage}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/**
 * Filter controls component
 */
function FilterControls({ 
  filter, 
  onFilterChange 
}: { 
  filter: ExecutionFilter
  onFilterChange: (filter: ExecutionFilter) => void
}) {
  const [localFilter, setLocalFilter] = useState(filter)
  
  const statusOptions = [
    { value: 'filled', label: 'Filled' },
    { value: 'partial', label: 'Partial' },
    { value: 'pending', label: 'Pending' },
    { value: 'rejected', label: 'Rejected' },
    { value: 'cancelled', label: 'Cancelled' }
  ]

  const instrumentOptions = [
    { value: 'EURUSD', label: 'EUR/USD' },
    { value: 'GBPUSD', label: 'GBP/USD' },
    { value: 'USDJPY', label: 'USD/JPY' },
    { value: 'AUDUSD', label: 'AUD/USD' },
    { value: 'USDCAD', label: 'USD/CAD' },
    { value: 'NZDUSD', label: 'NZD/USD' }
  ]

  const applyFilter = () => {
    onFilterChange(localFilter)
  }

  const clearFilters = () => {
    const emptyFilter: ExecutionFilter = {}
    setLocalFilter(emptyFilter)
    onFilterChange(emptyFilter)
  }

  return (
    <div className="bg-gray-800 p-4 rounded-lg mb-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Filters</h3>
        <button
          onClick={clearFilters}
          className="text-sm text-blue-400 hover:text-blue-300"
        >
          Clear All
        </button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
        {/* Status Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Status</label>
          <select
            multiple
            value={localFilter.statuses || []}
            onChange={(e) => {
              const values = Array.from(e.target.selectedOptions, option => option.value) as ExecutionStatus[]
              setLocalFilter({ ...localFilter, statuses: values.length > 0 ? values : undefined })
            }}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
          >
            {statusOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        
        {/* Instrument Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Instrument</label>
          <select
            multiple
            value={localFilter.instruments || []}
            onChange={(e) => {
              const values = Array.from(e.target.selectedOptions, option => option.value)
              setLocalFilter({ ...localFilter, instruments: values.length > 0 ? values : undefined })
            }}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
          >
            {instrumentOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        
        {/* Size Range */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Min Size</label>
          <input
            type="number"
            value={localFilter.minSize || ''}
            onChange={(e) => {
              const value = e.target.value ? parseInt(e.target.value) : undefined
              setLocalFilter({ ...localFilter, minSize: value })
            }}
            placeholder="0"
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
          />
        </div>
        
        {/* Search */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Search</label>
          <input
            type="text"
            value={localFilter.searchQuery || ''}
            onChange={(e) => {
              setLocalFilter({ ...localFilter, searchQuery: e.target.value || undefined })
            }}
            placeholder="Order ID, instrument..."
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
          />
        </div>
      </div>
      
      <div className="flex justify-end">
        <button
          onClick={applyFilter}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm font-medium"
        >
          Apply Filters
        </button>
      </div>
    </div>
  )
}

/**
 * Sort controls component
 */
function SortControls({ 
  sort, 
  onSortChange 
}: { 
  sort: ExecutionSort
  onSortChange: (sort: ExecutionSort) => void
}) {
  const sortOptions = [
    { value: 'timestamp', label: 'Time' },
    { value: 'instrument', label: 'Instrument' },
    { value: 'size', label: 'Size' },
    { value: 'slippage', label: 'Slippage' },
    { value: 'status', label: 'Status' },
    { value: 'account', label: 'Account' }
  ]

  return (
    <div className="flex items-center space-x-4 mb-4">
      <div className="flex items-center space-x-2">
        <label className="text-sm text-gray-400">Sort by:</label>
        <select
          value={sort.field}
          onChange={(e) => onSortChange({ ...sort, field: e.target.value as any })}
          className="bg-gray-700 border border-gray-600 rounded px-3 py-1 text-white text-sm"
        >
          {sortOptions.map(option => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      
      <button
        onClick={() => onSortChange({ 
          ...sort, 
          direction: sort.direction === 'asc' ? 'desc' : 'asc' 
        })}
        className="flex items-center space-x-1 text-sm text-blue-400 hover:text-blue-300"
      >
        <span>{sort.direction === 'asc' ? '↑' : '↓'}</span>
        <span>{sort.direction === 'asc' ? 'Ascending' : 'Descending'}</span>
      </button>
    </div>
  )
}

/**
 * Main TradeExecutionFeed component
 */
export function TradeExecutionFeed({
  executions,
  loading = false,
  error,
  filter = {},
  sort = { field: 'timestamp', direction: 'desc' },
  autoScroll = true,
  maxHeight = 600,
  onExecutionClick,
  onFilterChange,
  onSortChange,
  onLoadMore,
  hasMore = false,
  compact = false
}: TradeExecutionFeedProps) {
  const [showFilters, setShowFilters] = useState(false)
  const feedRef = useRef<HTMLDivElement>(null)
  const [isNearBottom, setIsNearBottom] = useState(true)

  // Auto-scroll to bottom when new executions arrive
  useEffect(() => {
    if (autoScroll && isNearBottom && feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight
    }
  }, [executions, autoScroll, isNearBottom])

  // Handle scroll events to determine if user is near bottom
  const handleScroll = (event: React.UIEvent<HTMLDivElement>) => {
    const target = event.target as HTMLDivElement
    const threshold = 100 // pixels from bottom
    const isNearBot = target.scrollHeight - target.scrollTop - target.clientHeight < threshold
    setIsNearBottom(isNearBot)

    // Load more when near bottom
    if (isNearBot && hasMore && onLoadMore) {
      onLoadMore()
    }
  }

  const displayedExecutions = useMemo(() => {
    return executions
  }, [executions])

  if (loading && executions.length === 0) {
    return (
      <Card>
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <LoadingSkeleton className="h-6 w-48" />
            <LoadingSkeleton className="h-8 w-32" />
          </div>
          {Array.from({ length: 10 }).map((_, i) => (
            <LoadingSkeleton key={i} className="h-16" />
          ))}
        </div>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <div className="text-center py-8">
          <div className="text-red-400 text-lg mb-2">Error Loading Executions</div>
          <p className="text-gray-400">{error}</p>
        </div>
      </Card>
    )
  }

  return (
    <Card>
      {/* Header */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 mb-6">
        <div>
          <h2 className="text-xl font-bold text-white mb-1">Trade Execution Feed</h2>
          <p className="text-sm text-gray-400">
            {displayedExecutions.length} executions • Last update: {new Date().toLocaleTimeString()}
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
              showFilters 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Filters {Object.keys(filter).length > 0 && `(${Object.keys(filter).length})`}
          </button>
          
          <div className={`w-3 h-3 rounded-full ${loading ? 'bg-yellow-400' : 'bg-green-400'} animate-pulse`} />
        </div>
      </div>

      {/* Filters */}
      {showFilters && onFilterChange && (
        <FilterControls filter={filter} onFilterChange={onFilterChange} />
      )}

      {/* Sort Controls */}
      {onSortChange && (
        <SortControls sort={sort} onSortChange={onSortChange} />
      )}

      {/* Header Row (for non-compact view) */}
      {!compact && displayedExecutions.length > 0 && (
        <div className="bg-gray-800 p-3 rounded-lg mb-2">
          <div className="grid grid-cols-12 gap-4 text-xs font-medium text-gray-300 uppercase">
            <div className="col-span-1">Time</div>
            <div className="col-span-2">Status</div>
            <div className="col-span-1">Instrument</div>
            <div className="col-span-2">Direction/Size</div>
            <div className="col-span-1">Price</div>
            <div className="col-span-1">Slippage</div>
            <div className="col-span-2">Account/Broker</div>
            <div className="col-span-2">Order ID</div>
          </div>
        </div>
      )}

      {/* Execution Feed */}
      <div 
        ref={feedRef}
        className="overflow-y-auto"
        style={{ maxHeight: `${maxHeight}px` }}
        onScroll={handleScroll}
      >
        {displayedExecutions.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-gray-400 text-lg mb-2">No Executions</div>
            <p className="text-gray-500">No trade executions match your current filters</p>
          </div>
        ) : (
          <>
            {displayedExecutions.map((execution) => (
              <ExecutionRow
                key={execution.id}
                execution={execution}
                onClick={onExecutionClick}
                compact={compact}
              />
            ))}
            
            {loading && (
              <div className="p-4 text-center">
                <div className="text-blue-400">Loading more executions...</div>
              </div>
            )}
            
            {hasMore && onLoadMore && !loading && (
              <div className="p-4 text-center">
                <button
                  onClick={onLoadMore}
                  className="text-blue-400 hover:text-blue-300 text-sm"
                >
                  Load More Executions
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Auto-scroll indicator */}
      {!isNearBottom && autoScroll && (
        <div className="absolute bottom-4 right-4">
          <button
            onClick={() => {
              if (feedRef.current) {
                feedRef.current.scrollTop = feedRef.current.scrollHeight
              }
            }}
            className="bg-blue-600 hover:bg-blue-700 text-white p-2 rounded-full shadow-lg"
          >
            ↓ Scroll to Latest
          </button>
        </div>
      )}
    </Card>
  )
}

export default TradeExecutionFeed