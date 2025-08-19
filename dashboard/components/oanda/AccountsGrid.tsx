'use client'

import React, { useState, useMemo } from 'react'
import { OandaAccount, AccountMetrics, AccountFilter, AccountHealthStatus, CurrencyCode } from '@/types/oanda'
import { AccountOverviewCard } from './AccountOverviewCard'
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton'

/**
 * Props for AccountsGrid component
 */
interface AccountsGridProps {
  /** Array of OANDA accounts */
  accounts: OandaAccount[]
  /** Real-time metrics for accounts */
  accountMetrics: Map<string, AccountMetrics>
  /** Alert counts per account */
  alertCounts?: Map<string, number>
  /** Loading state */
  loading?: boolean
  /** Error message */
  error?: string
  /** Callback when account is clicked */
  onAccountClick?: (accountId: string) => void
  /** Filter configuration */
  filter?: AccountFilter
  /** Callback when filter changes */
  onFilterChange?: (filter: AccountFilter) => void
  /** Show filter controls */
  showFilters?: boolean
  /** Grid layout (auto, 1, 2, 3, 4 columns) */
  columns?: 'auto' | 1 | 2 | 3 | 4
  /** Show detailed cards */
  detailed?: boolean
}

/**
 * Grid component for displaying multiple OANDA account overview cards
 */
export function AccountsGrid({
  accounts,
  accountMetrics,
  alertCounts = new Map(),
  loading = false,
  error,
  onAccountClick,
  filter = {},
  onFilterChange,
  showFilters = true,
  columns = 'auto',
  detailed = false
}: AccountsGridProps) {
  const [sortField, setSortField] = useState<AccountFilter['sortBy']>('balance')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')

  // Available filter options
  const availableAccountTypes: { value: string; label: string }[] = [
    { value: 'live', label: 'Live' },
    { value: 'demo', label: 'Demo' },
    { value: 'mt4', label: 'MT4' }
  ]

  const availableCurrencies: { value: CurrencyCode; label: string }[] = [
    { value: 'USD', label: 'USD' },
    { value: 'EUR', label: 'EUR' },
    { value: 'GBP', label: 'GBP' },
    { value: 'JPY', label: 'JPY' },
    { value: 'CHF', label: 'CHF' },
    { value: 'CAD', label: 'CAD' },
    { value: 'AUD', label: 'AUD' },
    { value: 'NZD', label: 'NZD' }
  ]

  const availableHealthStatuses: { value: AccountHealthStatus; label: string; color: string }[] = [
    { value: 'healthy', label: 'Healthy', color: 'text-green-400' },
    { value: 'warning', label: 'Warning', color: 'text-yellow-400' },
    { value: 'danger', label: 'Danger', color: 'text-orange-400' },
    { value: 'margin_call', label: 'Margin Call', color: 'text-red-400' }
  ]

  // Filter and sort accounts
  const filteredAndSortedAccounts = useMemo(() => {
    let filtered = [...accounts]

    // Apply filters
    if (filter.accountTypes && filter.accountTypes.length > 0) {
      filtered = filtered.filter(account => filter.accountTypes!.includes(account.type))
    }

    if (filter.currencies && filter.currencies.length > 0) {
      filtered = filtered.filter(account => filter.currencies!.includes(account.currency))
    }

    if (filter.healthStatus && filter.healthStatus.length > 0) {
      filtered = filtered.filter(account => filter.healthStatus!.includes(account.healthStatus))
    }

    if (filter.minBalance !== undefined) {
      filtered = filtered.filter(account => account.balance >= filter.minBalance!)
    }

    if (filter.maxBalance !== undefined) {
      filtered = filtered.filter(account => account.balance <= filter.maxBalance!)
    }

    if (filter.searchQuery && filter.searchQuery.trim()) {
      const query = filter.searchQuery.toLowerCase()
      filtered = filtered.filter(account => 
        account.alias.toLowerCase().includes(query) ||
        account.id.toLowerCase().includes(query)
      )
    }

    // Apply sorting
    const sortBy = filter.sortBy || sortField
    const direction = filter.sortDirection || sortDirection

    filtered.sort((a, b) => {
      let aValue: number | string
      let bValue: number | string

      switch (sortBy) {
        case 'balance':
          aValue = a.balance
          bValue = b.balance
          break
        case 'equity':
          aValue = a.NAV
          bValue = b.NAV
          break
        case 'unrealizedPL':
          aValue = a.unrealizedPL
          bValue = b.unrealizedPL
          break
        case 'marginUtilization':
          const aTotal = a.marginUsed + a.marginAvailable
          const bTotal = b.marginUsed + b.marginAvailable
          aValue = aTotal > 0 ? (a.marginUsed / aTotal) * 100 : 0
          bValue = bTotal > 0 ? (b.marginUsed / bTotal) * 100 : 0
          break
        case 'riskScore':
          // Calculate basic risk score
          const aMarginLevel = a.marginUsed > 0 ? (a.NAV / a.marginUsed) * 100 : 999999
          const bMarginLevel = b.marginUsed > 0 ? (b.NAV / b.marginUsed) * 100 : 999999
          aValue = aMarginLevel < 200 ? 100 : aMarginLevel < 300 ? 75 : 25
          bValue = bMarginLevel < 200 ? 100 : bMarginLevel < 300 ? 75 : 25
          break
        case 'alias':
          aValue = a.alias.toLowerCase()
          bValue = b.alias.toLowerCase()
          break
        default:
          aValue = a.balance
          bValue = b.balance
      }

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return direction === 'asc' ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue)
      }

      return direction === 'asc' ? 
        (aValue as number) - (bValue as number) : 
        (bValue as number) - (aValue as number)
    })

    return filtered
  }, [accounts, filter, sortField, sortDirection])

  // Handle filter changes
  const handleFilterChange = (newFilter: Partial<AccountFilter>) => {
    const updatedFilter = { ...filter, ...newFilter }
    onFilterChange?.(updatedFilter)
  }

  // Handle sort changes
  const handleSort = (field: AccountFilter['sortBy']) => {
    const newDirection = field === sortField && sortDirection === 'desc' ? 'asc' : 'desc'
    setSortField(field)
    setSortDirection(newDirection)
    handleFilterChange({ sortBy: field, sortDirection: newDirection })
  }

  // Get grid columns class
  const getGridClass = () => {
    if (columns === 'auto') {
      return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'
    }
    return `grid-cols-${columns}`
  }

  // Loading state
  if (loading) {
    return (
      <div className="space-y-6">
        {showFilters && (
          <div className="bg-gray-800 rounded-lg p-4">
            <LoadingSkeleton className="h-6 w-32 mb-4" />
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <LoadingSkeleton key={i} className="h-10" />
              ))}
            </div>
          </div>
        )}
        <div className={`grid ${getGridClass()} gap-6`}>
          {Array.from({ length: 6 }).map((_, i) => (
            <AccountOverviewCard
              key={i}
              account={{} as OandaAccount}
              loading={true}
            />
          ))}
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-400 text-xl mb-2">Error Loading Accounts</div>
        <p className="text-gray-400">{error}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Filter Controls */}
      {showFilters && (
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Filter & Sort</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            {/* Account Type Filter */}
            <div>
              <label className="block text-gray-300 text-sm mb-2">Account Type</label>
              <select
                value={filter.accountTypes?.[0] || ''}
                onChange={(e) => handleFilterChange({ 
                  accountTypes: e.target.value ? [e.target.value as any] : undefined 
                })}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
              >
                <option value="">All Types</option>
                {availableAccountTypes.map(type => (
                  <option key={type.value} value={type.value}>{type.label}</option>
                ))}
              </select>
            </div>

            {/* Currency Filter */}
            <div>
              <label className="block text-gray-300 text-sm mb-2">Currency</label>
              <select
                value={filter.currencies?.[0] || ''}
                onChange={(e) => handleFilterChange({ 
                  currencies: e.target.value ? [e.target.value as CurrencyCode] : undefined 
                })}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
              >
                <option value="">All Currencies</option>
                {availableCurrencies.map(currency => (
                  <option key={currency.value} value={currency.value}>{currency.label}</option>
                ))}
              </select>
            </div>

            {/* Health Status Filter */}
            <div>
              <label className="block text-gray-300 text-sm mb-2">Health Status</label>
              <select
                value={filter.healthStatus?.[0] || ''}
                onChange={(e) => handleFilterChange({ 
                  healthStatus: e.target.value ? [e.target.value as AccountHealthStatus] : undefined 
                })}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
              >
                <option value="">All Statuses</option>
                {availableHealthStatuses.map(status => (
                  <option key={status.value} value={status.value}>{status.label}</option>
                ))}
              </select>
            </div>

            {/* Sort By */}
            <div>
              <label className="block text-gray-300 text-sm mb-2">Sort By</label>
              <select
                value={sortField}
                onChange={(e) => handleSort(e.target.value as AccountFilter['sortBy'])}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
              >
                <option value="balance">Balance</option>
                <option value="equity">Equity</option>
                <option value="unrealizedPL">Unrealized P&L</option>
                <option value="marginUtilization">Margin Utilization</option>
                <option value="riskScore">Risk Score</option>
                <option value="alias">Account Name</option>
              </select>
            </div>
          </div>

          {/* Search and Balance Range */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-gray-300 text-sm mb-2">Search</label>
              <input
                type="text"
                value={filter.searchQuery || ''}
                onChange={(e) => handleFilterChange({ searchQuery: e.target.value })}
                placeholder="Search accounts..."
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
              />
            </div>
            
            <div>
              <label className="block text-gray-300 text-sm mb-2">Min Balance</label>
              <input
                type="number"
                value={filter.minBalance || ''}
                onChange={(e) => handleFilterChange({ 
                  minBalance: e.target.value ? parseFloat(e.target.value) : undefined 
                })}
                placeholder="0"
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
              />
            </div>
            
            <div>
              <label className="block text-gray-300 text-sm mb-2">Max Balance</label>
              <input
                type="number"
                value={filter.maxBalance || ''}
                onChange={(e) => handleFilterChange({ 
                  maxBalance: e.target.value ? parseFloat(e.target.value) : undefined 
                })}
                placeholder="No limit"
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
              />
            </div>
          </div>

          {/* Clear Filters */}
          <div className="flex justify-between items-center mt-4">
            <div className="text-sm text-gray-400">
              Showing {filteredAndSortedAccounts.length} of {accounts.length} accounts
            </div>
            <button
              onClick={() => {
                setSortField('balance')
                setSortDirection('desc')
                onFilterChange?.({})
              }}
              className="text-blue-400 hover:text-blue-300 text-sm transition-colors"
            >
              Clear All Filters
            </button>
          </div>
        </div>
      )}

      {/* Accounts Grid */}
      {filteredAndSortedAccounts.length === 0 ? (
        <div className="text-center py-12 bg-gray-800 rounded-lg">
          <div className="text-gray-400 text-lg mb-2">No accounts found</div>
          <p className="text-gray-500">
            {accounts.length === 0 
              ? 'No OANDA accounts are configured' 
              : 'Try adjusting your filter criteria'
            }
          </p>
        </div>
      ) : (
        <div className={`grid ${getGridClass()} gap-6`}>
          {filteredAndSortedAccounts.map((account) => (
            <AccountOverviewCard
              key={account.id}
              account={account}
              metrics={accountMetrics.get(account.id)}
              alertCount={alertCounts.get(account.id) || 0}
              detailed={detailed}
              onClick={onAccountClick}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default AccountsGrid