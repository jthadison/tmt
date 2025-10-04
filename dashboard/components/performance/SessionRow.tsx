/**
 * Session Row Component
 * Individual session performance row with P&L, metrics, and progress bar
 */

'use client'

import React from 'react'
import { SessionPerformance, SESSION_CONFIG } from '@/types/session'
import { Badge } from '@/components/ui/Badge'
import { formatCurrency } from '@/utils/formatCurrency'
import { cn } from '@/lib/utils'

interface SessionRowProps {
  /** Session performance data */
  session: SessionPerformance
  /** Maximum P&L across all sessions for bar scaling */
  maxPnL: number
  /** Is this session currently active */
  isActive: boolean
  /** Click handler for drill-down */
  onClick: () => void
}

/**
 * Session row component displaying performance metrics
 */
export function SessionRow({ session, maxPnL, isActive, onClick }: SessionRowProps) {
  const config = SESSION_CONFIG[session.session]

  // Calculate bar width (percentage of max P&L)
  const barWidth = maxPnL > 0 ? (Math.abs(session.totalPnL) / maxPnL) * 100 : 0

  // Determine bar color based on P&L
  const barColorClass = session.tradeCount === 0
    ? 'bg-gray-500'
    : session.totalPnL > 0
    ? 'bg-green-500'
    : 'bg-red-500'

  // Determine text color
  const pnlColorClass = session.totalPnL > 0
    ? 'text-green-400'
    : session.totalPnL < 0
    ? 'text-red-400'
    : 'text-gray-400'

  // Win rate badge variant
  const winRateVariant = session.winRate >= 60
    ? 'success'
    : session.winRate >= 40
    ? 'warning'
    : 'danger'

  // Format session hours
  const sessionHours = `${String(config.startHour).padStart(2, '0')}:00-${String(config.endHour).padStart(2, '0')}:00 GMT`

  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-center space-x-4 p-4 rounded-lg transition-all',
        'bg-gray-700 hover:bg-gray-650 cursor-pointer',
        'border border-transparent hover:border-gray-600'
      )}
      aria-label={`${config.name} session performance. Total P&L: ${formatCurrency(session.totalPnL)}. Click for details.`}
    >
      {/* Session Name + Active Indicator */}
      <div className="flex items-center space-x-2 w-40 flex-shrink-0">
        {isActive && (
          <span
            className="w-2 h-2 bg-green-400 rounded-full animate-pulse"
            aria-label="Currently active session"
          />
        )}
        <div className="flex flex-col items-start">
          <span className="font-semibold text-white text-sm">{config.name}</span>
          <span className="text-xs text-gray-400">{sessionHours}</span>
        </div>
      </div>

      {/* P&L Amount */}
      <div className={cn('text-lg font-bold w-28 text-right flex-shrink-0', pnlColorClass)}>
        {formatCurrency(session.totalPnL)}
      </div>

      {/* Trade Count Badge */}
      <Badge variant="neutral" className="flex-shrink-0">
        {session.tradeCount} {session.tradeCount === 1 ? 'trade' : 'trades'}
      </Badge>

      {/* Win Rate Badge */}
      <Badge variant={winRateVariant} className="flex-shrink-0">
        {session.winRate.toFixed(0)}% WR
      </Badge>

      {/* Confidence Threshold Badge */}
      <Badge variant="info" className="flex-shrink-0">
        {session.confidenceThreshold}% conf
      </Badge>

      {/* Horizontal Bar Chart */}
      <div className="flex-1 min-w-0">
        <div className="h-6 bg-gray-600 rounded-full overflow-hidden">
          <div
            className={cn(
              'h-full transition-all duration-500 ease-out',
              barColorClass
            )}
            style={{ width: `${barWidth}%` }}
            aria-label={`Performance bar representing ${session.totalPnL > 0 ? 'profit' : 'loss'} of ${formatCurrency(session.totalPnL)}`}
          />
        </div>
      </div>
    </button>
  )
}

export default SessionRow
