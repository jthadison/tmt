'use client'

import { useState, useMemo } from 'react'
import { PerformanceReport, AccountPerformanceComparison } from '@/types/analytics'

/**
 * Props for AccountComparison component
 */
interface AccountComparisonProps {
  /** Performance report data */
  performanceReport?: PerformanceReport
  /** Loading state */
  loading?: boolean
  /** Error message */
  error?: string
}

/**
 * Account performance comparison component
 * Provides side-by-side analysis and ranking of trading accounts
 */
export function AccountComparison({
  performanceReport,
  loading = false,
  error
}: AccountComparisonProps) {
  const [sortBy, setSortBy] = useState<keyof AccountPerformanceComparison['metrics']>('totalReturn')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [selectedAccounts, setSelectedAccounts] = useState<string[]>([])
  const [viewMode, setViewMode] = useState<'table' | 'cards' | 'heatmap'>('cards')

  // Sort and filter accounts
  const sortedAccounts = useMemo(() => {
    if (!performanceReport?.accountComparisons) return []

    const sorted = [...performanceReport.accountComparisons].sort((a, b) => {
      const aValue = a.metrics[sortBy]
      const bValue = b.metrics[sortBy]
      
      if (sortOrder === 'desc') {
        return bValue - aValue
      }
      return aValue - bValue
    })

    return sorted
  }, [performanceReport?.accountComparisons, sortBy, sortOrder])

  // Calculate correlation matrix
  const correlationMatrix = useMemo(() => {
    if (!performanceReport?.accountComparisons) return []

    const accounts = performanceReport.accountComparisons
    const matrix: Array<{
      account1: string
      account2: string
      correlation: number
    }> = []

    for (let i = 0; i < accounts.length; i++) {
      for (let j = i + 1; j < accounts.length; j++) {
        // Mock correlation calculation (would be real correlation in production)
        const correlation = Math.random() * 2 - 1 // Random correlation between -1 and 1
        matrix.push({
          account1: accounts[i].accountName,
          account2: accounts[j].accountName,
          correlation
        })
      }
    }

    return matrix.sort((a, b) => Math.abs(b.correlation) - Math.abs(a.correlation))
  }, [performanceReport?.accountComparisons])


  // Format currency values
  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
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

  // Get performance tier color
  const getPerformanceTier = (account: AccountPerformanceComparison): { color: string; label: string } => {
    const totalReturn = account.metrics.totalReturn
    const winRate = account.metrics.winRate
    const sharpe = account.metrics.sharpeRatio

    if (totalReturn >= 20 && winRate >= 70 && sharpe >= 2.0) {
      return { color: 'text-green-400 bg-green-900/20 border-green-500/30', label: 'Excellent' }
    } else if (totalReturn >= 10 && winRate >= 60 && sharpe >= 1.0) {
      return { color: 'text-blue-400 bg-blue-900/20 border-blue-500/30', label: 'Good' }
    } else if (totalReturn >= 0 && winRate >= 50) {
      return { color: 'text-yellow-400 bg-yellow-900/20 border-yellow-500/30', label: 'Average' }
    } else {
      return { color: 'text-red-400 bg-red-900/20 border-red-500/30', label: 'Poor' }
    }
  }

  // Get risk level color
  const getRiskLevelColor = (level: string): string => {
    switch (level) {
      case 'low': return 'text-green-400'
      case 'medium': return 'text-yellow-400'
      case 'high': return 'text-red-400'
      default: return 'text-gray-400'
    }
  }

  // Handle sort change
  const handleSort = (field: keyof AccountPerformanceComparison['metrics']) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
    } else {
      setSortBy(field)
      setSortOrder('desc')
    }
  }

  // Toggle account selection for comparison
  const toggleAccountSelection = (accountId: string) => {
    setSelectedAccounts(prev => 
      prev.includes(accountId) 
        ? prev.filter(id => id !== accountId)
        : [...prev, accountId]
    )
  }

  // Loading state
  if (loading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-700 rounded w-48 mb-4"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="bg-gray-750 rounded-lg p-6">
                <div className="h-5 bg-gray-700 rounded mb-3"></div>
                <div className="space-y-2">
                  {Array.from({ length: 4 }).map((_, j) => (
                    <div key={j} className="h-4 bg-gray-700 rounded"></div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-6">
        <div className="text-red-400 font-medium">Error Loading Account Comparison</div>
        <div className="text-red-200 text-sm mt-1">{error}</div>
      </div>
    )
  }

  // No data state
  if (!performanceReport?.accountComparisons?.length) {
    return (
      <div className="bg-gray-750 rounded-lg p-8 text-center">
        <div className="text-gray-400 text-lg">No Account Data Available</div>
        <div className="text-gray-500 text-sm mt-2">
          Add trading accounts to view performance comparisons
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h3 className="text-lg font-semibold text-white">Account Performance Comparison</h3>
          <p className="text-gray-400 text-sm">
            Comparing {sortedAccounts.length} trading accounts
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* View Mode Toggle */}
          <div className="flex bg-gray-700 rounded-lg p-1">
            <button
              onClick={() => setViewMode('cards')}
              className={`px-3 py-1 rounded text-sm transition-colors ${
                viewMode === 'cards' ? 'bg-blue-600 text-white' : 'text-gray-300 hover:text-white'
              }`}
            >
              📊 Cards
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`px-3 py-1 rounded text-sm transition-colors ${
                viewMode === 'table' ? 'bg-blue-600 text-white' : 'text-gray-300 hover:text-white'
              }`}
            >
              📋 Table
            </button>
            <button
              onClick={() => setViewMode('heatmap')}
              className={`px-3 py-1 rounded text-sm transition-colors ${
                viewMode === 'heatmap' ? 'bg-blue-600 text-white' : 'text-gray-300 hover:text-white'
              }`}
            >
              🔥 Heatmap
            </button>
          </div>

          {/* Sort Controls */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as keyof AccountPerformanceComparison['metrics'])}
            className="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
          >
            <option value="totalReturn">Total Return</option>
            <option value="totalPnL">Total P&L</option>
            <option value="winRate">Win Rate</option>
            <option value="sharpeRatio">Sharpe Ratio</option>
            <option value="maxDrawdownPercent">Max Drawdown</option>
            <option value="profitFactor">Profit Factor</option>
          </select>

          <button
            onClick={() => setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')}
            className="bg-gray-700 hover:bg-gray-600 border border-gray-600 rounded px-3 py-2 text-white text-sm transition-colors"
          >
            {sortOrder === 'desc' ? '↓' : '↑'}
          </button>
        </div>
      </div>

      {/* Cards View */}
      {viewMode === 'cards' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sortedAccounts.map((account) => {
            const tier = getPerformanceTier(account)
            const isSelected = selectedAccounts.includes(account.accountId)
            
            return (
              <div
                key={account.accountId}
                onClick={() => toggleAccountSelection(account.accountId)}
                className={`
                  bg-gray-750 rounded-lg p-6 border transition-all cursor-pointer
                  ${isSelected ? 'border-blue-500 ring-2 ring-blue-500/20' : 'border-gray-700 hover:border-gray-600'}
                `}
              >
                {/* Header */}
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h4 className="text-white font-medium">{account.accountName}</h4>
                    <div className="text-gray-400 text-sm">{account.propFirm}</div>
                    <div className="text-gray-500 text-xs">
                      {account.accountType.toUpperCase()} • Rank #{account.rank}
                    </div>
                  </div>
                  <div className={`px-2 py-1 rounded text-xs border ${tier.color}`}>
                    {tier.label}
                  </div>
                </div>

                {/* Key Metrics */}
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <div className="text-gray-400 text-xs">Total Return</div>
                    <div className={`font-bold ${account.metrics.totalReturn >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {formatPercentage(account.metrics.totalReturn)}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-400 text-xs">P&L</div>
                    <div className={`font-bold ${account.metrics.totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {formatCurrency(account.metrics.totalPnL)}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-400 text-xs">Win Rate</div>
                    <div className="text-white font-bold">
                      {formatPercentage(account.metrics.winRate)}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-400 text-xs">Sharpe Ratio</div>
                    <div className="text-white font-bold">
                      {account.metrics.sharpeRatio.toFixed(2)}
                    </div>
                  </div>
                </div>

                {/* Status and Risk */}
                <div className="flex justify-between items-center text-sm">
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${
                      account.status === 'active' ? 'bg-green-400' :
                      account.status === 'passed' ? 'bg-blue-400' :
                      account.status === 'failed' ? 'bg-red-400' : 'bg-gray-400'
                    }`}></div>
                    <span className="text-gray-300 capitalize">{account.status}</span>
                  </div>
                  <div className={`${getRiskLevelColor(account.riskLevel)} font-medium`}>
                    {account.riskLevel.toUpperCase()} RISK
                  </div>
                </div>

                {/* Portfolio Correlation */}
                <div className="mt-3 pt-3 border-t border-gray-600">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Portfolio Correlation</span>
                    <span className="text-white font-medium">
                      {(account.correlationToPortfolio * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Table View */}
      {viewMode === 'table' && (
        <div className="bg-gray-750 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Account
                  </th>
                  <th 
                    className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider cursor-pointer hover:text-white"
                    onClick={() => handleSort('totalReturn')}
                  >
                    Return {sortBy === 'totalReturn' && (sortOrder === 'desc' ? '↓' : '↑')}
                  </th>
                  <th 
                    className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider cursor-pointer hover:text-white"
                    onClick={() => handleSort('totalPnL')}
                  >
                    P&L {sortBy === 'totalPnL' && (sortOrder === 'desc' ? '↓' : '↑')}
                  </th>
                  <th 
                    className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider cursor-pointer hover:text-white"
                    onClick={() => handleSort('winRate')}
                  >
                    Win Rate {sortBy === 'winRate' && (sortOrder === 'desc' ? '↓' : '↑')}
                  </th>
                  <th 
                    className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider cursor-pointer hover:text-white"
                    onClick={() => handleSort('sharpeRatio')}
                  >
                    Sharpe {sortBy === 'sharpeRatio' && (sortOrder === 'desc' ? '↓' : '↑')}
                  </th>
                  <th 
                    className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider cursor-pointer hover:text-white"
                    onClick={() => handleSort('maxDrawdownPercent')}
                  >
                    Max DD {sortBy === 'maxDrawdownPercent' && (sortOrder === 'desc' ? '↓' : '↑')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Correlation
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-600">
                {sortedAccounts.map((account) => (
                  <tr key={account.accountId} className="hover:bg-gray-700/50">
                    <td className="px-6 py-4">
                      <div>
                        <div className="text-white font-medium">{account.accountName}</div>
                        <div className="text-gray-400 text-sm">{account.propFirm}</div>
                        <div className="text-gray-500 text-xs">#{account.rank}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className={`font-medium ${account.metrics.totalReturn >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatPercentage(account.metrics.totalReturn)}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className={`font-medium ${account.metrics.totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatCurrency(account.metrics.totalPnL)}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-white font-medium">
                        {formatPercentage(account.metrics.winRate)}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-white font-medium">
                        {account.metrics.sharpeRatio.toFixed(2)}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-red-400 font-medium">
                        {formatPercentage(account.metrics.maxDrawdownPercent)}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${
                          account.status === 'active' ? 'bg-green-400' :
                          account.status === 'passed' ? 'bg-blue-400' :
                          account.status === 'failed' ? 'bg-red-400' : 'bg-gray-400'
                        }`}></div>
                        <span className="text-gray-300 capitalize text-sm">{account.status}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-white font-medium">
                        {(account.correlationToPortfolio * 100).toFixed(1)}%
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Heatmap View */}
      {viewMode === 'heatmap' && (
        <div className="space-y-6">
          {/* Performance Heatmap */}
          <div className="bg-gray-750 rounded-lg p-6">
            <h4 className="text-white font-medium mb-4">Performance Heatmap</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
              {sortedAccounts.map((account) => {
                const intensity = Math.abs(account.metrics.totalReturn) / 50 // Normalize to 0-1
                const isPositive = account.metrics.totalReturn >= 0
                
                return (
                  <div
                    key={account.accountId}
                    className={`
                      p-3 rounded text-center transition-all hover:scale-105 cursor-pointer
                      ${isPositive 
                        ? `bg-green-500` 
                        : `bg-red-500`
                      }
                    `}
                    style={{ 
                      opacity: Math.max(0.3, intensity),
                      backgroundColor: isPositive 
                        ? `rgba(34, 197, 94, ${Math.max(0.3, intensity)})` 
                        : `rgba(239, 68, 68, ${Math.max(0.3, intensity)})`
                    }}
                    title={`${account.accountName}: ${formatPercentage(account.metrics.totalReturn)}`}
                  >
                    <div className="text-white text-xs font-medium truncate">
                      {account.accountName}
                    </div>
                    <div className="text-white text-sm font-bold mt-1">
                      {formatPercentage(account.metrics.totalReturn)}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Correlation Matrix */}
          <div className="bg-gray-750 rounded-lg p-6">
            <h4 className="text-white font-medium mb-4">Account Correlations</h4>
            <div className="space-y-2">
              {correlationMatrix.slice(0, 10).map((item, index) => (
                <div key={index} className="flex justify-between items-center py-2">
                  <div className="text-gray-300 text-sm">
                    {item.account1} ↔ {item.account2}
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-32 bg-gray-600 rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full ${item.correlation >= 0 ? 'bg-green-500' : 'bg-red-500'}`}
                        style={{ 
                          width: `${Math.abs(item.correlation) * 100}%`,
                          marginLeft: item.correlation < 0 ? `${(1 + item.correlation) * 100}%` : '0'
                        }}
                      ></div>
                    </div>
                    <div className={`text-sm font-medium w-16 text-right ${
                      item.correlation >= 0.5 ? 'text-green-400' :
                      item.correlation <= -0.5 ? 'text-red-400' : 'text-gray-300'
                    }`}>
                      {(item.correlation * 100).toFixed(0)}%
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Selected Accounts Summary */}
      {selectedAccounts.length > 0 && (
        <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-6">
          <h4 className="text-blue-400 font-medium mb-3">
            Selected Accounts Comparison ({selectedAccounts.length})
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {['totalReturn', 'winRate', 'sharpeRatio'].map((metric) => {
              const selectedAccountData = sortedAccounts.filter(acc => 
                selectedAccounts.includes(acc.accountId)
              )
              const values = selectedAccountData.map(acc => 
                acc.metrics[metric as keyof typeof acc.metrics]
              )
              const avg = values.reduce((sum, val) => sum + val, 0) / values.length
              const best = Math.max(...values)
              const worst = Math.min(...values)

              return (
                <div key={metric} className="bg-gray-750 rounded p-4">
                  <div className="text-gray-400 text-sm mb-2 capitalize">
                    {metric.replace(/([A-Z])/g, ' $1').trim()}
                  </div>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-300">Average</span>
                      <span className="text-white font-medium">
                        {metric.includes('Rate') || metric.includes('Return') 
                          ? formatPercentage(avg) 
                          : avg.toFixed(2)
                        }
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-300">Best</span>
                      <span className="text-green-400 font-medium">
                        {metric.includes('Rate') || metric.includes('Return') 
                          ? formatPercentage(best) 
                          : best.toFixed(2)
                        }
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-300">Worst</span>
                      <span className="text-red-400 font-medium">
                        {metric.includes('Rate') || metric.includes('Return') 
                          ? formatPercentage(worst) 
                          : worst.toFixed(2)
                        }
                      </span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}