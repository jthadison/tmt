'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import { AccountOverview, GridFilters, GridSortOptions } from '@/types/account'
import { AccountCard } from './AccountCard'
import { CardSkeleton } from '../ui/LoadingSkeleton'

/**
 * Props for AccountOverviewGrid component
 */
interface AccountOverviewGridProps {
  /** Array of account data to display */
  accounts: AccountOverview[]
  /** Loading state indicator */
  loading?: boolean
  /** Error state message */
  error?: string
  /** Callback when account is clicked for drill-down */
  onAccountClick?: (accountId: string) => void
  /** Auto-refresh interval in seconds */
  refreshInterval?: number
  /** Callback to refresh account data */
  onRefresh?: () => void
}

/**
 * Main grid component for displaying account overview cards
 * Implements responsive layout, sorting, filtering, and auto-refresh
 */
export function AccountOverviewGrid({
  accounts,
  loading = false,
  error,
  onAccountClick,
  refreshInterval = 30,
  onRefresh
}: AccountOverviewGridProps) {
  const [filters, setFilters] = useState<GridFilters>({})
  const [sortOptions, setSortOptions] = useState<GridSortOptions>({
    field: 'accountName',
    direction: 'asc'
  })
  const [searchTerm, setSearchTerm] = useState('')

  // Auto-refresh functionality
  useEffect(() => {
    if (!refreshInterval || !onRefresh) return

    const interval = setInterval(() => {
      onRefresh()
    }, refreshInterval * 1000)

    return () => clearInterval(interval)
  }, [refreshInterval, onRefresh])

  // Filter and sort accounts
  const filteredAndSortedAccounts = useMemo(() => {
    const filtered = accounts.filter(account => {
      // Search term filter
      if (searchTerm) {
        const searchLower = searchTerm.toLowerCase()
        if (
          !account.accountName.toLowerCase().includes(searchLower) &&
          !account.propFirm.toLowerCase().includes(searchLower)
        ) {
          return false
        }
      }

      // Status filter
      if (filters.status && filters.status.length > 0) {
        if (!filters.status.includes(account.status)) {
          return false
        }
      }

      // Prop firm filter
      if (filters.propFirm && filters.propFirm.length > 0) {
        if (!filters.propFirm.includes(account.propFirm)) {
          return false
        }
      }

      // Balance range filter
      if (filters.minBalance !== undefined && account.balance < filters.minBalance) {
        return false
      }
      if (filters.maxBalance !== undefined && account.balance > filters.maxBalance) {
        return false
      }

      return true
    })

    // Sort accounts
    const sortedAccounts = [...filtered].sort((a, b) => {
      const { field, direction } = sortOptions
      let aValue: string | number | Date = a[field] as string | number | Date
      let bValue: string | number | Date = b[field] as string | number | Date

      // Handle nested properties
      if (field === 'pnl') {
        aValue = a.pnl.total
        bValue = b.pnl.total
      } else if (field === 'drawdown') {
        aValue = a.drawdown.percentage
        bValue = b.drawdown.percentage
      } else if (field === 'positions') {
        aValue = a.positions.active
        bValue = b.positions.active
      } else if (field === 'exposure') {
        aValue = a.exposure.utilization
        bValue = b.exposure.utilization
      }

      // Handle date comparison
      if (aValue instanceof Date && bValue instanceof Date) {
        return direction === 'asc' 
          ? aValue.getTime() - bValue.getTime()
          : bValue.getTime() - aValue.getTime()
      }

      // Handle numeric comparison
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return direction === 'asc' ? aValue - bValue : bValue - aValue
      }

      // Handle string comparison
      const aStr = String(aValue).toLowerCase()
      const bStr = String(bValue).toLowerCase()
      
      if (direction === 'asc') {
        return aStr.localeCompare(bStr)
      } else {
        return bStr.localeCompare(aStr)
      }
    })

    return sortedAccounts
  }, [accounts, filters, sortOptions, searchTerm])


  // Clear all filters
  const clearFilters = useCallback(() => {
    setFilters({})
    setSearchTerm('')
  }, [])

  // Get unique prop firms for filter dropdown
  const uniquePropFirms = useMemo(() => {
    return Array.from(new Set(accounts.map(account => account.propFirm)))
  }, [accounts])

  if (loading && accounts.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold text-white">Account Overview</h2>
          <div className="animate-pulse bg-gray-700 rounded h-10 w-32"></div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {Array.from({ length: 8 }).map((_, i) => (
            <CardSkeleton key={i} className="h-80" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="text-center">
          <div className="text-red-400 text-xl mb-2">⚠️ Error Loading Accounts</div>
          <p className="text-gray-400 mb-4">{error}</p>
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded transition-colors"
            >
              Try Again
            </button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header with title and controls */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h2 className="text-2xl font-bold text-white">Account Overview</h2>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-400">
            {filteredAndSortedAccounts.length} of {accounts.length} accounts
          </span>
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-2 rounded text-sm transition-colors"
              disabled={loading}
            >
              {loading ? '↻' : '⟳'} Refresh
            </button>
          )}
        </div>
      </div>

      {/* Search and Filter Controls */}
      <div className="bg-gray-800 rounded-lg p-4 space-y-4">
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <div className="flex-1">
            <input
              type="text"
              placeholder="Search accounts or prop firms..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Sort Dropdown */}
          <select
            value={`${sortOptions.field}-${sortOptions.direction}`}
            onChange={(e) => {
              const [field, direction] = e.target.value.split('-')
              setSortOptions({ field: field as keyof AccountOverview, direction: direction as 'asc' | 'desc' })
            }}
            className="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          >
            <option value="accountName-asc">Name A-Z</option>
            <option value="accountName-desc">Name Z-A</option>
            <option value="balance-desc">Balance High-Low</option>
            <option value="balance-asc">Balance Low-High</option>
            <option value="pnl-desc">P&L High-Low</option>
            <option value="pnl-asc">P&L Low-High</option>
            <option value="drawdown-desc">Risk High-Low</option>
            <option value="drawdown-asc">Risk Low-High</option>
          </select>

          {/* Clear Filters */}
          {(Object.keys(filters).length > 0 || searchTerm) && (
            <button
              onClick={clearFilters}
              className="bg-red-600 hover:bg-red-700 text-white px-3 py-2 rounded text-sm transition-colors whitespace-nowrap"
            >
              Clear Filters
            </button>
          )}
        </div>

        {/* Status and Prop Firm Filters */}
        <div className="flex flex-wrap gap-4">
          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-400">Status:</span>
            <div className="flex gap-2">
              {(['healthy', 'warning', 'danger'] as const).map(status => (
                <label key={status} className="flex items-center gap-1 text-sm">
                  <input
                    type="checkbox"
                    checked={filters.status?.includes(status) || false}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setFilters(prev => ({
                          ...prev,
                          status: [...(prev.status || []), status]
                        }))
                      } else {
                        setFilters(prev => ({
                          ...prev,
                          status: prev.status?.filter(s => s !== status)
                        }))
                      }
                    }}
                    className="rounded border-gray-600 bg-gray-700 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-white capitalize">{status}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Prop Firm Filter */}
          {uniquePropFirms.length > 1 && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-400">Prop Firm:</span>
              <select
                multiple
                value={filters.propFirm || []}
                onChange={(e) => {
                  const selected = Array.from(e.target.selectedOptions, option => option.value)
                  setFilters(prev => ({ ...prev, propFirm: selected }))
                }}
                className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-white text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              >
                {uniquePropFirms.map(firm => (
                  <option key={firm} value={firm}>{firm}</option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Account Cards Grid */}
      {filteredAndSortedAccounts.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-gray-400 text-lg">No accounts found</div>
          <p className="text-gray-500 mt-2">Try adjusting your filters or search term</p>
        </div>
      ) : (
        <div 
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"
          role="grid"
          aria-label="Account overview grid"
        >
          {filteredAndSortedAccounts.map((account) => (
            <AccountCard
              key={account.id}
              account={account}
              onClick={() => onAccountClick?.(account.id)}
              loading={loading}
            />
          ))}
        </div>
      )}
    </div>
  )
}