'use client'

import { PnLMetrics } from '@/types/account'

/**
 * Props for PnLDisplay component
 */
interface PnLDisplayProps {
  /** P&L metrics to display */
  pnl: PnLMetrics
  /** Show detailed breakdown */
  detailed?: boolean
  /** Additional CSS classes */
  className?: string
}

/**
 * P&L (Profit and Loss) display component with color coding
 * Shows percentage and dollar amounts with positive/negative styling
 */
export function PnLDisplay({ pnl, detailed = false, className = '' }: PnLDisplayProps) {
  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      signDisplay: 'always'
    }).format(amount)
  }

  const formatPercentage = (percentage: number): string => {
    return `${percentage >= 0 ? '+' : ''}${percentage.toFixed(2)}%`
  }

  const getPnLColorClass = (value: number): string => {
    if (value > 0) return 'text-green-400'
    if (value < 0) return 'text-red-400'
    return 'text-gray-400'
  }

  const getPnLBackgroundClass = (value: number): string => {
    if (value > 0) return 'bg-green-500/10 border-green-500/20'
    if (value < 0) return 'bg-red-500/10 border-red-500/20'
    return 'bg-gray-500/10 border-gray-500/20'
  }

  const getTrendIcon = (value: number): string => {
    if (value > 0) return '↗'
    if (value < 0) return '↘'
    return '→'
  }

  if (detailed) {
    return (
      <div className={`space-y-3 ${className}`}>
        <div className="text-sm font-medium text-gray-300 mb-2">Profit & Loss</div>
        
        {/* Total P&L - Primary Display */}
        <div className={`
          p-3 rounded-lg border ${getPnLBackgroundClass(pnl.total)}
          transition-all duration-200
        `}>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Total P&L</span>
            <div className="flex items-center gap-2">
              <span className={`text-lg font-bold ${getPnLColorClass(pnl.total)}`}>
                {formatCurrency(pnl.total)}
              </span>
              <span className={`text-sm ${getPnLColorClass(pnl.percentage)}`}>
                {formatPercentage(pnl.percentage)}
              </span>
              <span className={`text-lg ${getPnLColorClass(pnl.total)}`}>
                {getTrendIcon(pnl.total)}
              </span>
            </div>
          </div>
        </div>

        {/* Daily and Weekly Breakdown */}
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-400">Daily</span>
            <div className="flex items-center gap-2">
              <span className={`text-sm font-medium ${getPnLColorClass(pnl.daily)}`}>
                {formatCurrency(pnl.daily)}
              </span>
              <span className={`text-xs ${getPnLColorClass(pnl.daily)}`}>
                {getTrendIcon(pnl.daily)}
              </span>
            </div>
          </div>
          
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-400">Weekly</span>
            <div className="flex items-center gap-2">
              <span className={`text-sm font-medium ${getPnLColorClass(pnl.weekly)}`}>
                {formatCurrency(pnl.weekly)}
              </span>
              <span className={`text-xs ${getPnLColorClass(pnl.weekly)}`}>
                {getTrendIcon(pnl.weekly)}
              </span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Compact display for account cards
  return (
    <div className={`space-y-2 ${className}`}>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-400">P&L</span>
        <div className="flex items-center gap-2">
          <span className={`text-sm font-bold ${getPnLColorClass(pnl.total)}`}>
            {formatCurrency(pnl.total)}
          </span>
          <span className={`text-xs ${getPnLColorClass(pnl.percentage)}`}>
            {formatPercentage(pnl.percentage)}
          </span>
        </div>
      </div>
      
      {/* Daily P&L */}
      <div className="flex justify-between items-center">
        <span className="text-xs text-gray-500">Today</span>
        <span className={`text-xs font-medium ${getPnLColorClass(pnl.daily)}`}>
          {formatCurrency(pnl.daily)}
        </span>
      </div>
    </div>
  )
}

/**
 * Animated P&L display for real-time updates
 * Shows smooth transitions when values change
 */
export function AnimatedPnLDisplay({ 
  pnl, 
  previousPnL, 
  className = '' 
}: {
  pnl: PnLMetrics
  previousPnL?: PnLMetrics
  className?: string
}) {
  const hasChanged = previousPnL && (
    pnl.total !== previousPnL.total ||
    pnl.daily !== previousPnL.daily ||
    pnl.percentage !== previousPnL.percentage
  )

  return (
    <div className={`
      ${className}
      ${hasChanged ? 'animate-pulse' : ''}
      transition-all duration-500
    `}>
      <PnLDisplay pnl={pnl} />
      
      {/* Real-time update indicator */}
      {hasChanged && (
        <div className="flex items-center justify-center mt-1">
          <div className="w-1 h-1 bg-blue-400 rounded-full animate-ping"></div>
        </div>
      )}
    </div>
  )
}