'use client'

import React from 'react'
import { AggregatedAccountMetrics, CurrencyCode, AccountHealthStatus } from '@/types/oanda'
import Card from '@/components/ui/Card'

/**
 * Props for MultiAccountSummary component
 */
interface MultiAccountSummaryProps {
  /** Aggregated metrics for all accounts */
  aggregatedMetrics: AggregatedAccountMetrics
  /** Loading state */
  loading?: boolean
  /** Show detailed breakdown */
  detailed?: boolean
  /** Callback for drilling down to specific accounts */
  onDrillDown?: (filter: { healthStatus?: AccountHealthStatus; currency?: CurrencyCode }) => void
}

/**
 * Multi-account summary showing aggregated metrics and breakdowns
 */
export function MultiAccountSummary({
  aggregatedMetrics,
  loading = false,
  detailed = false,
  onDrillDown
}: MultiAccountSummaryProps) {
  const formatCurrency = (amount: number, currency: CurrencyCode = 'USD'): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount)
  }

  const formatPercentage = (value: number): string => {
    return `${value.toFixed(1)}%`
  }

  const formatNumber = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value)
  }

  const getHealthStatusColor = (status: AccountHealthStatus): string => {
    switch (status) {
      case 'healthy':
        return 'text-green-400 bg-green-900/20'
      case 'warning':
        return 'text-yellow-400 bg-yellow-900/20'
      case 'danger':
        return 'text-orange-400 bg-orange-900/20'
      case 'margin_call':
        return 'text-red-400 bg-red-900/20'
      default:
        return 'text-gray-400 bg-gray-900/20'
    }
  }

  const getRiskScoreColor = (score: number): string => {
    if (score > 75) return 'text-red-400'
    if (score > 50) return 'text-yellow-400'
    if (score > 25) return 'text-orange-400'
    return 'text-green-400'
  }

  const plColor = aggregatedMetrics.totalUnrealizedPL >= 0 ? 'text-green-400' : 'text-red-400'
  const dailyPlColor = aggregatedMetrics.totalDailyPL >= 0 ? 'text-green-400' : 'text-red-400'

  if (loading) {
    return (
      <div className="space-y-6">
        <Card>
          <div className="animate-pulse space-y-4">
            <div className="h-6 bg-gray-700 rounded w-48"></div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-16 bg-gray-700 rounded"></div>
              ))}
            </div>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Main Summary Card */}
      <Card>
        <div className="flex justify-between items-start mb-6">
          <h2 className="text-xl font-bold text-white">Portfolio Overview</h2>
          <div className="text-sm text-gray-400">
            Last updated: {aggregatedMetrics.lastUpdate.toLocaleTimeString()}
          </div>
        </div>

        {/* Key Portfolio Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-white mb-1">
              {formatCurrency(aggregatedMetrics.totalBalance)}
            </div>
            <div className="text-sm text-gray-400">Total Balance</div>
          </div>
          
          <div className="text-center">
            <div className="text-2xl font-bold text-white mb-1">
              {formatCurrency(aggregatedMetrics.totalEquity)}
            </div>
            <div className="text-sm text-gray-400">Total Equity</div>
          </div>
          
          <div className="text-center">
            <div className={`text-2xl font-bold mb-1 ${plColor}`}>
              {aggregatedMetrics.totalUnrealizedPL >= 0 ? '+' : ''}
              {formatCurrency(aggregatedMetrics.totalUnrealizedPL)}
            </div>
            <div className="text-sm text-gray-400">Unrealized P&L</div>
          </div>
          
          <div className="text-center">
            <div className={`text-2xl font-bold mb-1 ${dailyPlColor}`}>
              {aggregatedMetrics.totalDailyPL >= 0 ? '+' : ''}
              {formatCurrency(aggregatedMetrics.totalDailyPL)}
            </div>
            <div className="text-sm text-gray-400">Daily P&L</div>
          </div>
        </div>

        {/* Account Status and Risk */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h3 className="text-lg font-semibold text-white mb-3">Account Status</h3>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-400">Total Accounts</span>
                <span className="text-white font-medium">{aggregatedMetrics.totalAccounts}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Active Accounts</span>
                <span className="text-green-400 font-medium">{aggregatedMetrics.activeAccounts}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Margin Utilization</span>
                <span className={`font-medium ${
                  aggregatedMetrics.averageMarginUtilization > 80 ? 'text-red-400' :
                  aggregatedMetrics.averageMarginUtilization > 60 ? 'text-yellow-400' : 'text-green-400'
                }`}>
                  {formatPercentage(aggregatedMetrics.averageMarginUtilization)}
                </span>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-white mb-3">Risk Assessment</h3>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-400">Portfolio Risk Score</span>
                <span className={`font-medium ${getRiskScoreColor(aggregatedMetrics.portfolioRiskScore)}`}>
                  {aggregatedMetrics.portfolioRiskScore.toFixed(0)}/100
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Total Open Positions</span>
                <span className="text-white font-medium">{aggregatedMetrics.totalOpenPositions}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Total Margin Used</span>
                <span className="text-white font-medium">{formatCurrency(aggregatedMetrics.totalMarginUsed)}</span>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Health Status Breakdown */}
      <Card>
        <h3 className="text-lg font-semibold text-white mb-4">Account Health Breakdown</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(aggregatedMetrics.healthStatusBreakdown).map(([status, count]) => {
            const healthStatus = status as keyof typeof aggregatedMetrics.healthStatusBreakdown
            const displayStatus = status === 'marginCall' ? 'margin_call' : status as AccountHealthStatus
            
            return (
              <div
                key={status}
                className={`p-4 rounded-lg border cursor-pointer transition-all hover:border-gray-500 ${getHealthStatusColor(displayStatus)}`}
                onClick={() => onDrillDown?.({ healthStatus: displayStatus })}
              >
                <div className="text-center">
                  <div className="text-2xl font-bold mb-1">{count}</div>
                  <div className="text-sm capitalize">
                    {status === 'marginCall' ? 'Margin Call' : status}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </Card>

      {/* Currency Breakdown */}
      {Object.keys(aggregatedMetrics.currencyBreakdown).length > 0 && (
        <Card>
          <h3 className="text-lg font-semibold text-white mb-4">Currency Breakdown</h3>
          <div className="space-y-4">
            {Object.entries(aggregatedMetrics.currencyBreakdown)
              .filter(([_, data]) => data && data.accountCount > 0)
              .sort(([, a], [, b]) => (b?.totalBalance || 0) - (a?.totalBalance || 0))
              .map(([currency, data]) => {
                if (!data) return null
                
                const balancePercent = aggregatedMetrics.totalBalance > 0 ? 
                  (data.totalBalance / aggregatedMetrics.totalBalance) * 100 : 0
                
                return (
                  <div
                    key={currency}
                    className="p-4 bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-750 transition-colors"
                    onClick={() => onDrillDown?.({ currency: currency as CurrencyCode })}
                  >
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-white font-medium">{currency}</span>
                      <span className="text-gray-400 text-sm">{data.accountCount} accounts</span>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 mb-3">
                      <div>
                        <div className="text-gray-400 text-sm">Balance</div>
                        <div className="text-white font-medium">
                          {formatCurrency(data.totalBalance, currency as CurrencyCode)}
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-400 text-sm">Equity</div>
                        <div className="text-white font-medium">
                          {formatCurrency(data.totalEquity, currency as CurrencyCode)}
                        </div>
                      </div>
                    </div>
                    
                    {/* Balance percentage bar */}
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-400">Portfolio allocation</span>
                        <span className="text-white">{formatPercentage(balancePercent)}</span>
                      </div>
                      <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-blue-500 transition-all duration-300"
                          style={{ width: `${Math.min(100, balancePercent)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                )
              })}
          </div>
        </Card>
      )}

      {/* Detailed Metrics (if detailed view) */}
      {detailed && (
        <Card>
          <h3 className="text-lg font-semibold text-white mb-4">Detailed Metrics</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div>
              <h4 className="text-white font-medium mb-3">Margin Information</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Total Margin Used</span>
                  <span className="text-white">{formatCurrency(aggregatedMetrics.totalMarginUsed)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Total Margin Available</span>
                  <span className="text-white">{formatCurrency(aggregatedMetrics.totalMarginAvailable)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Average Utilization</span>
                  <span className="text-white">{formatPercentage(aggregatedMetrics.averageMarginUtilization)}</span>
                </div>
              </div>
            </div>

            <div>
              <h4 className="text-white font-medium mb-3">Position Summary</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Total Open Positions</span>
                  <span className="text-white">{aggregatedMetrics.totalOpenPositions}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Average per Account</span>
                  <span className="text-white">
                    {aggregatedMetrics.activeAccounts > 0 ? 
                      (aggregatedMetrics.totalOpenPositions / aggregatedMetrics.activeAccounts).toFixed(1) : '0'
                    }
                  </span>
                </div>
              </div>
            </div>

            <div>
              <h4 className="text-white font-medium mb-3">Performance</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Total P&L</span>
                  <span className={`${plColor}`}>
                    {aggregatedMetrics.totalUnrealizedPL >= 0 ? '+' : ''}
                    {formatCurrency(aggregatedMetrics.totalUnrealizedPL)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Daily P&L</span>
                  <span className={`${dailyPlColor}`}>
                    {aggregatedMetrics.totalDailyPL >= 0 ? '+' : ''}
                    {formatCurrency(aggregatedMetrics.totalDailyPL)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Return on Equity</span>
                  <span className="text-white">
                    {aggregatedMetrics.totalEquity > 0 ? 
                      formatPercentage((aggregatedMetrics.totalUnrealizedPL / aggregatedMetrics.totalEquity) * 100) : 
                      '0%'
                    }
                  </span>
                </div>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Quick Actions */}
      <Card>
        <h3 className="text-lg font-semibold text-white mb-4">Quick Actions</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <button
            onClick={() => onDrillDown?.({})}
            className="p-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm font-medium"
          >
            View All Accounts
          </button>
          <button
            onClick={() => onDrillDown?.({ healthStatus: 'warning' })}
            className="p-3 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg transition-colors text-sm font-medium"
          >
            View Warnings
          </button>
          <button
            onClick={() => onDrillDown?.({ healthStatus: 'danger' })}
            className="p-3 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors text-sm font-medium"
          >
            View High Risk
          </button>
          <button
            onClick={() => onDrillDown?.({ healthStatus: 'margin_call' })}
            className="p-3 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors text-sm font-medium"
          >
            View Margin Calls
          </button>
        </div>
      </Card>
    </div>
  )
}

export default MultiAccountSummary