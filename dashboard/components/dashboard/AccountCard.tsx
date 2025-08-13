'use client'

import React from 'react'
import { AccountOverview } from '@/types/account'
import { StatusIndicator } from './StatusIndicator'
import { PnLDisplay } from './PnLDisplay'
import { DrawdownBar } from './DrawdownBar'
import { PositionMetrics } from './PositionMetrics'

/**
 * Props for AccountCard component
 */
interface AccountCardProps {
  /** Account data to display */
  account: AccountOverview
  /** Click handler for navigation to account details */
  onClick?: () => void
  /** Loading state indicator */
  loading?: boolean
}

/**
 * Individual account card component displaying key metrics
 * Optimized with React.memo for performance with large account lists
 */
export const AccountCard = React.memo<AccountCardProps>(function AccountCard({
  account,
  onClick,
  loading = false
}) {
  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount)
  }

  const formatLastUpdate = (date: Date): string => {
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / (1000 * 60))
    
    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours}h ago`
    
    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays}d ago`
  }

  return (
    <div
      className={`
        bg-gray-800 rounded-lg border border-gray-700 p-6 space-y-4 
        transition-all duration-200 hover:border-gray-600 hover:bg-gray-750
        ${onClick ? 'cursor-pointer hover:shadow-lg' : ''}
        ${loading ? 'opacity-60' : ''}
      `}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick()
        }
      } : undefined}
      aria-label={onClick ? `View details for ${account.accountName}` : undefined}
    >
      {/* Header with Account Name and Status */}
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-semibold text-white truncate">
            {account.accountName}
          </h3>
          <p className="text-sm text-gray-400 truncate">
            {account.propFirm}
          </p>
        </div>
        <StatusIndicator 
          status={account.status}
          className="flex-shrink-0 ml-2"
        />
      </div>

      {/* Balance and Equity */}
      <div className="space-y-2">
        <div className="flex justify-between">
          <span className="text-sm text-gray-400">Balance</span>
          <span className="text-sm font-medium text-white">
            {formatCurrency(account.balance)}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-sm text-gray-400">Equity</span>
          <span className="text-sm font-medium text-white">
            {formatCurrency(account.equity)}
          </span>
        </div>
      </div>

      {/* P&L Display */}
      <PnLDisplay pnl={account.pnl} />

      {/* Drawdown Visualization */}
      <DrawdownBar drawdown={account.drawdown} />

      {/* Position and Exposure Metrics */}
      <PositionMetrics 
        positions={account.positions}
        exposure={account.exposure}
      />

      {/* Footer with Last Update */}
      <div className="pt-2 border-t border-gray-700">
        <div className="flex justify-between items-center text-xs text-gray-500">
          <span>Last update</span>
          <span>{formatLastUpdate(account.lastUpdate)}</span>
        </div>
      </div>

      {/* Accessibility enhancement for clickable cards */}
      {onClick && (
        <div className="sr-only">
          Click to view detailed information for {account.accountName} account
        </div>
      )}
    </div>
  )
})

