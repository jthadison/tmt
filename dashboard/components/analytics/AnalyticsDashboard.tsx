'use client'

import { useState, useMemo } from 'react'
import { 
  PerformanceReport, 
  AnalyticsFilters, 
  DateRange, 
  AnalyticsDashboardState 
} from '@/types/analytics'

// Component imports (to be created)
import { AggregateMetrics } from './AggregateMetrics'
import { AccountComparison } from './AccountComparison'
import { TradeAnalysis } from './TradeAnalysis'
import { TimeBreakdown } from './TimeBreakdown'
import { ReportExporter } from './ReportExporter'
import { DateRangePicker } from './DateRangePicker'

/**
 * Props for AnalyticsDashboard component
 */
interface AnalyticsDashboardProps {
  /** Performance report data */
  performanceReport?: PerformanceReport
  /** Available account options */
  availableAccounts: Array<{
    id: string
    name: string
    propFirm: string
    isActive: boolean
  }>
  /** Callback when filters change */
  onFiltersChange: (filters: AnalyticsFilters) => void
  /** Callback when report export is requested */
  onExportReport?: (filters: AnalyticsFilters, format: 'pdf' | 'csv' | 'excel' | 'json') => void
  /** Loading state for data fetching */
  loading?: boolean
  /** Error message if data loading failed */
  error?: string
}

/**
 * Main analytics dashboard container component
 * Provides comprehensive performance analytics and reporting capabilities
 */
export function AnalyticsDashboard({
  performanceReport,
  availableAccounts,
  onFiltersChange,
  onExportReport,
  loading = false,
  error
}: AnalyticsDashboardProps) {
  // Dashboard state management
  const [state, setState] = useState<AnalyticsDashboardState>(() => {
    const defaultDateRange: DateRange = {
      start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // 30 days ago
      end: new Date(),
      label: 'Last 30 days',
      isPreset: true
    }

    return {
      filters: {
        accountIds: availableAccounts.filter(acc => acc.isActive).map(acc => acc.id),
        dateRange: defaultDateRange,
        groupBy: 'account'
      },
      loading: {
        aggregate: false,
        comparison: false,
        tradeAnalysis: false,
        timeBreakdown: false,
        export: false
      },
      errors: {},
      activeTab: 'overview',
      lastRefresh: new Date()
    }
  })

  // Tab configuration
  const tabs = [
    { 
      id: 'overview', 
      label: 'Portfolio Overview', 
      icon: '📊',
      description: 'Aggregate performance metrics and key indicators'
    },
    { 
      id: 'comparison', 
      label: 'Account Comparison', 
      icon: '📈',
      description: 'Side-by-side account performance analysis'
    },
    { 
      id: 'analysis', 
      label: 'Trade Analysis', 
      icon: '🔍',
      description: 'Pattern and timing analysis breakdown'
    },
    { 
      id: 'breakdown', 
      label: 'Time Breakdown', 
      icon: '📅',
      description: 'Monthly, weekly, and daily performance'
    },
    { 
      id: 'reports', 
      label: 'Reports', 
      icon: '📄',
      description: 'Generate and export detailed reports'
    }
  ] as const

  // Update filters and notify parent
  const updateFilters = (newFilters: Partial<AnalyticsFilters>) => {
    const updatedFilters = { ...state.filters, ...newFilters }
    setState(prev => ({
      ...prev,
      filters: updatedFilters,
      lastRefresh: new Date()
    }))
    onFiltersChange(updatedFilters)
  }

  // Handle tab changes
  const handleTabChange = (tabId: typeof tabs[number]['id']) => {
    setState(prev => ({
      ...prev,
      activeTab: tabId
    }))
  }

  // Handle account selection
  const handleAccountSelection = (accountIds: string[]) => {
    updateFilters({ accountIds })
  }

  // Handle date range changes
  const handleDateRangeChange = (dateRange: DateRange) => {
    updateFilters({ dateRange })
  }

  // Calculate summary statistics
  const summaryStats = useMemo(() => {
    if (!performanceReport) return null

    const { aggregateMetrics, accountComparisons } = performanceReport
    
    return {
      totalAccounts: accountComparisons.length,
      activeAccounts: accountComparisons.filter(acc => acc.status === 'active').length,
      totalPnL: aggregateMetrics.totalPnL,
      totalReturn: aggregateMetrics.totalReturn,
      winRate: aggregateMetrics.winRate,
      sharpeRatio: aggregateMetrics.sharpeRatio,
      maxDrawdown: aggregateMetrics.maxDrawdownPercent,
      bestPerformer: accountComparisons.find(acc => acc.rank === 1),
      worstPerformer: accountComparisons.find(acc => acc.rank === accountComparisons.length)
    }
  }, [performanceReport])

  // Format currency values
  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      signDisplay: amount !== 0 ? 'always' : 'never'
    }).format(amount)
  }

  // Format percentage values
  const formatPercentage = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'percent',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      signDisplay: value !== 0 ? 'always' : 'never'
    }).format(value / 100)
  }

  // Loading state
  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-700 rounded w-64"></div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-32 bg-gray-700 rounded"></div>
            ))}
          </div>
          <div className="h-96 bg-gray-700 rounded"></div>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="bg-gray-800 rounded-lg p-8">
        <div className="text-center">
          <div className="text-red-400 text-lg font-medium mb-2">Analytics Error</div>
          <div className="text-gray-300 mb-4">{error}</div>
          <button
            onClick={() => window.location.reload()}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white mb-2">Performance Analytics</h1>
            <p className="text-gray-400">
              Comprehensive trading performance analysis and reporting
            </p>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-400">
              Last updated: {state.lastRefresh.toLocaleTimeString()}
            </div>
            <button
              onClick={() => setState(prev => ({ ...prev, lastRefresh: new Date() }))}
              className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-2 rounded text-sm transition-colors"
            >
              🔄 Refresh
            </button>
          </div>
        </div>

        {/* Quick Stats Summary */}
        {summaryStats && (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 mt-6">
            <div className="bg-gray-750 rounded p-3">
              <div className="text-xs text-gray-400">Active Accounts</div>
              <div className="text-lg font-bold text-white">
                {summaryStats.activeAccounts}/{summaryStats.totalAccounts}
              </div>
            </div>
            <div className="bg-gray-750 rounded p-3">
              <div className="text-xs text-gray-400">Total P&L</div>
              <div className={`text-lg font-bold ${summaryStats.totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {formatCurrency(summaryStats.totalPnL)}
              </div>
            </div>
            <div className="bg-gray-750 rounded p-3">
              <div className="text-xs text-gray-400">Total Return</div>
              <div className={`text-lg font-bold ${summaryStats.totalReturn >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {formatPercentage(summaryStats.totalReturn)}
              </div>
            </div>
            <div className="bg-gray-750 rounded p-3">
              <div className="text-xs text-gray-400">Win Rate</div>
              <div className="text-lg font-bold text-blue-400">
                {formatPercentage(summaryStats.winRate)}
              </div>
            </div>
            <div className="bg-gray-750 rounded p-3">
              <div className="text-xs text-gray-400">Sharpe Ratio</div>
              <div className={`text-lg font-bold ${summaryStats.sharpeRatio >= 1 ? 'text-green-400' : summaryStats.sharpeRatio >= 0.5 ? 'text-yellow-400' : 'text-red-400'}`}>
                {summaryStats.sharpeRatio.toFixed(2)}
              </div>
            </div>
            <div className="bg-gray-750 rounded p-3">
              <div className="text-xs text-gray-400">Max Drawdown</div>
              <div className={`text-lg font-bold ${summaryStats.maxDrawdown <= -20 ? 'text-red-400' : summaryStats.maxDrawdown <= -10 ? 'text-yellow-400' : 'text-green-400'}`}>
                {formatPercentage(summaryStats.maxDrawdown)}
              </div>
            </div>
            <div className="bg-gray-750 rounded p-3">
              <div className="text-xs text-gray-400">Best Performer</div>
              <div className="text-sm font-medium text-white truncate">
                {summaryStats.bestPerformer?.accountName || 'N/A'}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Filters Section */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Analysis Filters</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Account Selection */}
          <div>
            <label className="block text-gray-300 text-sm mb-2">Accounts</label>
            <div className="space-y-2 max-h-32 overflow-y-auto">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={state.filters.accountIds.length === availableAccounts.length}
                  onChange={(e) => {
                    const allIds = availableAccounts.map(acc => acc.id)
                    handleAccountSelection(e.target.checked ? allIds : [])
                  }}
                  className="rounded border-gray-600 bg-gray-700 text-blue-600"
                />
                <span className="text-gray-300 text-sm font-medium">All Accounts</span>
              </label>
              {availableAccounts.map((account) => (
                <label key={account.id} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={state.filters.accountIds.includes(account.id)}
                    onChange={(e) => {
                      const currentIds = state.filters.accountIds
                      const newIds = e.target.checked
                        ? [...currentIds, account.id]
                        : currentIds.filter(id => id !== account.id)
                      handleAccountSelection(newIds)
                    }}
                    className="rounded border-gray-600 bg-gray-700 text-blue-600"
                  />
                  <span className="text-gray-300 text-sm">{account.name}</span>
                  <span className="text-gray-500 text-xs">({account.propFirm})</span>
                </label>
              ))}
            </div>
          </div>

          {/* Date Range Picker */}
          <div>
            <DateRangePicker
              value={state.filters.dateRange}
              onChange={handleDateRangeChange}
              maxRange={730} // 2 years
            />
          </div>

          {/* Group By Selection */}
          <div>
            <label className="block text-gray-300 text-sm mb-2">Group By</label>
            <select
              value={state.filters.groupBy}
              onChange={(e) => updateFilters({ groupBy: e.target.value as AnalyticsFilters['groupBy'] })}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            >
              <option value="account">Account</option>
              <option value="pattern">Pattern</option>
              <option value="symbol">Symbol</option>
              <option value="time">Time Period</option>
              <option value="session">Market Session</option>
            </select>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="bg-gray-800 rounded-lg">
        <div className="flex overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className={`
                flex-shrink-0 px-6 py-4 text-sm font-medium border-b-2 transition-colors
                ${state.activeTab === tab.id
                  ? 'border-blue-500 text-blue-400 bg-gray-750'
                  : 'border-transparent text-gray-400 hover:text-gray-300 hover:bg-gray-750'
                }
              `}
            >
              <div className="flex items-center gap-2">
                <span className="text-lg">{tab.icon}</span>
                <div className="text-left">
                  <div>{tab.label}</div>
                  <div className="text-xs text-gray-500">{tab.description}</div>
                </div>
              </div>
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {state.activeTab === 'overview' && (
            <AggregateMetrics 
              performanceReport={performanceReport}
              loading={state.loading.aggregate}
              error={state.errors.aggregate}
            />
          )}
          
          {state.activeTab === 'comparison' && (
            <AccountComparison 
              performanceReport={performanceReport}
              loading={state.loading.comparison}
              error={state.errors.comparison}
            />
          )}
          
          {state.activeTab === 'analysis' && (
            <TradeAnalysis 
              performanceReport={performanceReport}
              loading={state.loading.tradeAnalysis}
              error={state.errors.tradeAnalysis}
            />
          )}
          
          {state.activeTab === 'breakdown' && (
            <TimeBreakdown 
              performanceReport={performanceReport}
              loading={state.loading.timeBreakdown}
              error={state.errors.timeBreakdown}
            />
          )}
          
          {state.activeTab === 'reports' && (
            <ReportExporter 
              performanceReport={performanceReport}
              filters={state.filters}
              onExport={onExportReport}
              loading={state.loading.export}
              error={state.errors.export}
            />
          )}
        </div>
      </div>
    </div>
  )
}