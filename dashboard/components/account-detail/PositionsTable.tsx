'use client'

import { useState, useMemo } from 'react'
import { Position, PositionSortOptions } from '@/types/accountDetail'

/**
 * Props for PositionsTable component
 */
interface PositionsTableProps {
  /** Array of active positions */
  positions: Position[]
  /** Loading state indicator */
  loading?: boolean
  /** Callback when data needs refresh */
  onRefresh?: () => void
  /** Callback when position is selected for action */
  onPositionSelect?: (position: Position) => void
}

/**
 * Active positions table with real-time updates and sorting
 * Displays comprehensive position information with type indicators
 */
export function PositionsTable({
  positions,
  loading = false,
  onRefresh,
  onPositionSelect
}: PositionsTableProps) {
  const [sortOptions, setSortOptions] = useState<PositionSortOptions>({
    field: 'pnl',
    direction: 'desc'
  })

  // Sort positions based on current sort options
  const sortedPositions = useMemo(() => {
    const sorted = [...positions].sort((a, b) => {
      const { field, direction } = sortOptions
      const aValue = a[field]
      const bValue = b[field]

      // Handle Date objects
      if (aValue instanceof Date && bValue instanceof Date) {
        return direction === 'asc' 
          ? aValue.getTime() - bValue.getTime()
          : bValue.getTime() - aValue.getTime()
      }

      // Handle numeric values
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return direction === 'asc' ? aValue - bValue : bValue - aValue
      }

      // Handle string values
      const aStr = String(aValue).toLowerCase()
      const bStr = String(bValue).toLowerCase()
      
      if (direction === 'asc') {
        return aStr.localeCompare(bStr)
      } else {
        return bStr.localeCompare(aStr)
      }
    })

    return sorted
  }, [positions, sortOptions])

  const handleSort = (field: keyof Position) => {
    setSortOptions(prev => ({
      field,
      direction: prev.field === field && prev.direction === 'asc' ? 'desc' : 'asc'
    }))
  }

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      signDisplay: amount !== 0 ? 'always' : 'never'
    }).format(amount)
  }

  const formatPrice = (price: number, digits: number = 5): string => {
    return price.toFixed(digits)
  }

  const formatDuration = (minutes: number): string => {
    if (minutes < 60) {
      return `${minutes}m`
    }
    const hours = Math.floor(minutes / 60)
    const remainingMinutes = minutes % 60
    if (hours < 24) {
      return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`
    }
    const days = Math.floor(hours / 24)
    const remainingHours = hours % 24
    return remainingHours > 0 ? `${days}d ${remainingHours}h` : `${days}d`
  }

  const getPositionTypeColor = (type: 'long' | 'short'): string => {
    return type === 'long' ? 'text-green-400' : 'text-red-400'
  }

  const getPositionTypeIcon = (type: 'long' | 'short'): string => {
    return type === 'long' ? '↗' : '↘'
  }

  const getPnLColor = (pnl: number): string => {
    if (pnl > 0) return 'text-green-400'
    if (pnl < 0) return 'text-red-400'
    return 'text-gray-400'
  }

  const getSortIcon = (field: keyof Position): string => {
    if (sortOptions.field !== field) return '↕'
    return sortOptions.direction === 'asc' ? '↑' : '↓'
  }

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-700 rounded w-32"></div>
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-12 bg-gray-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gray-800 rounded-lg">
      {/* Header */}
      <div className="flex justify-between items-center p-6 border-b border-gray-700">
        <h3 className="text-lg font-semibold text-white">
          Active Positions ({positions.length})
        </h3>
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-1 rounded text-sm transition-colors"
          >
            ⟳ Refresh
          </button>
        )}
      </div>

      {/* Table */}
      {positions.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-gray-400 text-lg">No Active Positions</div>
          <p className="text-gray-500 mt-2">All positions have been closed</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-700">
                <th 
                  className="text-left py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                  onClick={() => handleSort('symbol')}
                >
                  Symbol {getSortIcon('symbol')}
                </th>
                <th 
                  className="text-left py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                  onClick={() => handleSort('type')}
                >
                  Type {getSortIcon('type')}
                </th>
                <th 
                  className="text-right py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                  onClick={() => handleSort('size')}
                >
                  Size {getSortIcon('size')}
                </th>
                <th 
                  className="text-right py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                  onClick={() => handleSort('entryPrice')}
                >
                  Entry Price {getSortIcon('entryPrice')}
                </th>
                <th 
                  className="text-right py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                  onClick={() => handleSort('currentPrice')}
                >
                  Current Price {getSortIcon('currentPrice')}
                </th>
                <th 
                  className="text-right py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                  onClick={() => handleSort('pnl')}
                >
                  P&L {getSortIcon('pnl')}
                </th>
                <th 
                  className="text-right py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                  onClick={() => handleSort('duration')}
                >
                  Duration {getSortIcon('duration')}
                </th>
                <th 
                  className="text-right py-3 px-4 font-medium text-gray-300 cursor-pointer hover:text-white transition-colors"
                  onClick={() => handleSort('riskPercentage')}
                >
                  Risk % {getSortIcon('riskPercentage')}
                </th>
                <th className="text-center py-3 px-4 font-medium text-gray-300">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedPositions.map((position, index) => (
                <tr 
                  key={position.id}
                  className={`
                    border-b border-gray-700 hover:bg-gray-750 transition-colors
                    ${index % 2 === 0 ? 'bg-gray-800' : 'bg-gray-850'}
                  `}
                >
                  <td className="py-3 px-4">
                    <div className="font-medium text-white">{position.symbol}</div>
                  </td>
                  <td className="py-3 px-4">
                    <div className={`flex items-center gap-1 ${getPositionTypeColor(position.type)}`}>
                      <span>{getPositionTypeIcon(position.type)}</span>
                      <span className="capitalize font-medium">{position.type}</span>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-right text-white">
                    {position.size.toFixed(2)}
                  </td>
                  <td className="py-3 px-4 text-right text-white">
                    {formatPrice(position.entryPrice)}
                  </td>
                  <td className="py-3 px-4 text-right text-white">
                    {formatPrice(position.currentPrice)}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <div className={`font-medium ${getPnLColor(position.pnl)}`}>
                      {formatCurrency(position.pnl)}
                    </div>
                    <div className={`text-xs ${getPnLColor(position.pnlPercentage)}`}>
                      {position.pnlPercentage >= 0 ? '+' : ''}{position.pnlPercentage.toFixed(2)}%
                    </div>
                  </td>
                  <td className="py-3 px-4 text-right text-gray-300">
                    {formatDuration(position.duration)}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <span className={`
                      text-sm font-medium
                      ${position.riskPercentage > 2 ? 'text-red-400' : 
                        position.riskPercentage > 1 ? 'text-yellow-400' : 'text-green-400'}
                    `}>
                      {position.riskPercentage.toFixed(1)}%
                    </span>
                  </td>
                  <td className="py-3 px-4 text-center">
                    <button
                      onClick={() => onPositionSelect?.(position)}
                      className="bg-blue-600 hover:bg-blue-700 text-white px-2 py-1 rounded text-xs transition-colors"
                    >
                      Manage
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Risk Summary */}
      {positions.length > 0 && (
        <div className="p-4 border-t border-gray-700 bg-gray-750">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <div className="text-gray-400">Total Positions</div>
              <div className="text-white font-medium">{positions.length}</div>
            </div>
            <div>
              <div className="text-gray-400">Total P&L</div>
              <div className={`font-medium ${getPnLColor(positions.reduce((sum, p) => sum + p.pnl, 0))}`}>
                {formatCurrency(positions.reduce((sum, p) => sum + p.pnl, 0))}
              </div>
            </div>
            <div>
              <div className="text-gray-400">Total Risk</div>
              <div className="text-white font-medium">
                {positions.reduce((sum, p) => sum + p.riskPercentage, 0).toFixed(1)}%
              </div>
            </div>
            <div>
              <div className="text-gray-400">Avg Duration</div>
              <div className="text-white font-medium">
                {formatDuration(positions.reduce((sum, p) => sum + p.duration, 0) / positions.length)}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}