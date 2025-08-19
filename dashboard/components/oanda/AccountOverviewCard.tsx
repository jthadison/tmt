'use client'

import React from 'react'
import { OandaAccount, AccountMetrics, AccountHealthStatus, CurrencyCode } from '@/types/oanda'
import Card from '@/components/ui/Card'

/**
 * Props for AccountOverviewCard component
 */
interface AccountOverviewCardProps {
  /** Account information */
  account: OandaAccount
  /** Real-time metrics */
  metrics?: AccountMetrics
  /** Show detailed view */
  detailed?: boolean
  /** Click handler for drill-down */
  onClick?: (accountId: string) => void
  /** Show alerts count */
  alertCount?: number
  /** Loading state */
  loading?: boolean
}

/**
 * Account overview card displaying key account information and metrics
 */
export function AccountOverviewCard({
  account,
  metrics,
  detailed = false,
  onClick,
  alertCount = 0,
  loading = false
}: AccountOverviewCardProps) {
  const getHealthStatusColor = (status: AccountHealthStatus): string => {
    switch (status) {
      case 'healthy':
        return 'text-green-400 bg-green-900/20 border-green-500/30'
      case 'warning':
        return 'text-yellow-400 bg-yellow-900/20 border-yellow-500/30'
      case 'danger':
        return 'text-orange-400 bg-orange-900/20 border-orange-500/30'
      case 'margin_call':
        return 'text-red-400 bg-red-900/20 border-red-500/30'
      default:
        return 'text-gray-400 bg-gray-900/20 border-gray-500/30'
    }
  }

  const getHealthStatusIcon = (status: AccountHealthStatus): string => {
    switch (status) {
      case 'healthy':
        return '✅'
      case 'warning':
        return '⚠️'
      case 'danger':
        return '🔶'
      case 'margin_call':
        return '🚨'
      default:
        return '❓'
    }
  }

  const formatCurrency = (amount: number, currency: CurrencyCode): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount)
  }

  const formatPercentage = (value: number): string => {
    return `${value.toFixed(1)}%`
  }

  const formatNumber = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2
    }).format(value)
  }

  const currentMetrics = metrics || {
    accountId: account.id,
    timestamp: account.lastUpdate,
    balance: account.balance,
    equity: account.NAV,
    marginUsed: account.marginUsed,
    marginAvailable: account.marginAvailable,
    marginUtilization: account.marginUsed + account.marginAvailable > 0 ? 
      (account.marginUsed / (account.marginUsed + account.marginAvailable)) * 100 : 0,
    freeMargin: account.marginAvailable,
    marginLevel: account.marginUsed > 0 ? (account.NAV / account.marginUsed) * 100 : 999999,
    dailyPL: account.unrealizedPL,
    unrealizedPL: account.unrealizedPL,
    openPositions: account.openPositionCount,
    totalExposure: account.marginUsed * 50,
    riskScore: 25
  }

  const marginLevelColor = currentMetrics.marginLevel < 200 ? 'text-red-400' : 
                          currentMetrics.marginLevel < 300 ? 'text-yellow-400' : 'text-green-400'

  const plColor = currentMetrics.unrealizedPL >= 0 ? 'text-green-400' : 'text-red-400'

  if (loading) {
    return (
      <Card className="animate-pulse">
        <div className="h-6 bg-gray-700 rounded w-32 mb-4"></div>
        <div className="space-y-3">
          {Array.from({ length: detailed ? 6 : 4 }).map((_, i) => (
            <div key={i} className="h-4 bg-gray-700 rounded"></div>
          ))}
        </div>
      </Card>
    )
  }

  return (
    <Card 
      className={`relative transition-all duration-200 ${
        onClick ? 'cursor-pointer hover:border-blue-500/50 hover:bg-gray-800/50' : ''
      }`}
      onClick={onClick ? () => onClick(account.id) : undefined}
    >
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold text-white mb-1">{account.alias}</h3>
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <span>{account.type.toUpperCase()}</span>
            <span>•</span>
            <span>{account.currency}</span>
            <span>•</span>
            <span>ID: {account.id}</span>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {alertCount > 0 && (
            <div className="bg-red-500 text-white text-xs px-2 py-1 rounded-full font-medium">
              {alertCount}
            </div>
          )}
          <div className={`px-3 py-1 rounded-full text-xs font-medium border ${getHealthStatusColor(account.healthStatus)}`}>
            <span className="mr-1">{getHealthStatusIcon(account.healthStatus)}</span>
            {account.healthStatus.replace('_', ' ').toUpperCase()}
          </div>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <div className="text-xs text-gray-400 mb-1">Balance</div>
          <div className="text-lg font-bold text-white">
            {formatCurrency(currentMetrics.balance, account.currency)}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-400 mb-1">Equity (NAV)</div>
          <div className="text-lg font-bold text-white">
            {formatCurrency(currentMetrics.equity, account.currency)}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-400 mb-1">Unrealized P&L</div>
          <div className={`text-lg font-bold ${plColor}`}>
            {currentMetrics.unrealizedPL >= 0 ? '+' : ''}
            {formatCurrency(currentMetrics.unrealizedPL, account.currency)}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-400 mb-1">Margin Level</div>
          <div className={`text-lg font-bold ${marginLevelColor}`}>
            {currentMetrics.marginLevel > 9999 ? '∞' : formatPercentage(currentMetrics.marginLevel)}
          </div>
        </div>
      </div>

      {/* Margin Information */}
      <div className="space-y-3 mb-4">
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-400">Margin Used</span>
            <span className="text-white">{formatCurrency(currentMetrics.marginUsed, account.currency)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">Margin Available</span>
            <span className="text-white">{formatCurrency(currentMetrics.marginAvailable, account.currency)}</span>
          </div>
        </div>
        
        {/* Margin Utilization Bar */}
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-gray-400">Margin Utilization</span>
            <span className="text-white">{formatPercentage(currentMetrics.marginUtilization)}</span>
          </div>
          <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all duration-300 ${
                currentMetrics.marginUtilization > 80 ? 'bg-red-500' :
                currentMetrics.marginUtilization > 60 ? 'bg-yellow-500' : 'bg-green-500'
              }`}
              style={{ width: `${Math.min(100, currentMetrics.marginUtilization)}%` }}
            />
          </div>
        </div>
      </div>

      {/* Position Information */}
      <div className="grid grid-cols-3 gap-4 text-sm">
        <div>
          <div className="text-gray-400">Open Positions</div>
          <div className="text-white font-medium">{currentMetrics.openPositions}</div>
        </div>
        <div>
          <div className="text-gray-400">Open Trades</div>
          <div className="text-white font-medium">{account.openTradeCount}</div>
        </div>
        <div>
          <div className="text-gray-400">Pending Orders</div>
          <div className="text-white font-medium">{account.pendingOrderCount}</div>
        </div>
      </div>

      {/* Detailed View Additional Information */}
      {detailed && (
        <>
          <hr className="border-gray-700 my-4" />
          
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-gray-400">Risk Score</div>
                <div className={`font-medium ${
                  currentMetrics.riskScore > 75 ? 'text-red-400' :
                  currentMetrics.riskScore > 50 ? 'text-yellow-400' : 'text-green-400'
                }`}>
                  {currentMetrics.riskScore.toFixed(0)}/100
                </div>
              </div>
              <div>
                <div className="text-gray-400">Total Exposure</div>
                <div className="text-white font-medium">
                  {formatCurrency(currentMetrics.totalExposure, account.currency)}
                </div>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-gray-400">Account Created</div>
                <div className="text-white font-medium">
                  {new Date(account.createdTime).toLocaleDateString()}
                </div>
              </div>
              <div>
                <div className="text-gray-400">Last Update</div>
                <div className="text-white font-medium">
                  {account.lastUpdate.toLocaleTimeString()}
                </div>
              </div>
            </div>
            
            <div className="text-sm">
              <div className="text-gray-400">Last Transaction ID</div>
              <div className="text-white font-medium font-mono text-xs">
                {account.lastTransactionID}
              </div>
            </div>
          </div>
        </>
      )}

      {/* Quick Actions (if clickable) */}
      {onClick && (
        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <div className="bg-blue-600 text-white p-1 rounded text-xs">
            Click for details
          </div>
        </div>
      )}
    </Card>
  )
}

export default AccountOverviewCard