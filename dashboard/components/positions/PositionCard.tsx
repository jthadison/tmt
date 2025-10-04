/**
 * Position Card Component
 * Displays individual position with real-time P&L updates
 */

import React from 'react'
import { ArrowUp, ArrowDown, Pencil, X } from 'lucide-react'
import { Position } from '@/types/positions'
import { Badge } from '@/components/ui/Badge'
import { ProgressBar } from '@/components/ui/ProgressBar'
import { AnimatedNumber } from '@/components/ui/AnimatedNumber'
import { formatInstrument, formatPrice } from '@/utils/positionCalculations'
import { cn } from '@/lib/utils'

interface PositionCardProps {
  /** Position data */
  position: Position
  /** Close position callback */
  onClose: (positionId: string) => void
  /** Modify position callback */
  onModify: (positionId: string) => void
  /** Click handler for card */
  onClick: (position: Position) => void
}

/**
 * Position card component with real-time updates
 */
export const PositionCard = React.memo(({
  position,
  onClose,
  onModify,
  onClick,
}: PositionCardProps) => {
  const isWinning = position.unrealizedPL > 0
  const isNearTP = position.isNearTP
  const isNearSL = position.isNearSL

  // Format currency
  const formatCurrency = (value: number): string => {
    const formatted = Math.abs(value).toFixed(2)
    return value >= 0 ? `$${formatted}` : `-$${formatted}`
  }

  return (
    <div
      className={cn(
        'bg-gray-800 rounded-lg p-4 cursor-pointer transition-all duration-200',
        'hover:scale-[1.02] hover:shadow-lg',
        'border-2',
        isWinning ? 'border-green-500 shadow-green-500/30' : 'border-red-500 shadow-red-500/30',
        isNearTP && 'animate-pulse-yellow',
        isNearSL && 'animate-pulse-orange'
      )}
      onClick={() => onClick(position)}
      role="article"
      aria-label={`Position ${formatInstrument(position.instrument)} ${position.direction}`}
    >
      {/* Header: Instrument + Direction */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-lg font-bold text-white">
          {formatInstrument(position.instrument)}
        </span>
        <Badge
          variant={position.direction === 'long' ? 'success' : 'danger'}
          icon={position.direction === 'long' ? ArrowUp : ArrowDown}
        >
          {position.direction.toUpperCase()}
        </Badge>
      </div>

      {/* P&L */}
      <div className="mb-4">
        <div
          className={cn(
            'text-3xl font-bold',
            isWinning ? 'text-green-400' : 'text-red-400'
          )}
        >
          <AnimatedNumber value={position.unrealizedPL} format={formatCurrency} />
        </div>
        <div className="text-sm text-gray-400">
          ({position.unrealizedPLPercentage >= 0 ? '+' : ''}
          {position.unrealizedPLPercentage.toFixed(2)}%)
        </div>
      </div>

      {/* Prices Grid */}
      <div className="grid grid-cols-2 gap-2 mb-3 text-sm">
        <div>
          <span className="text-gray-500">Entry:</span>{' '}
          <span className="text-white">
            {formatPrice(position.entryPrice, position.instrument)}
          </span>
        </div>
        <div>
          <span className="text-gray-500">Current:</span>{' '}
          <span className="text-white font-bold">
            {formatPrice(position.currentPrice, position.instrument)}
          </span>
        </div>
        {position.stopLoss && (
          <div>
            <span className="text-red-400">SL:</span>{' '}
            <span className="text-white">
              {formatPrice(position.stopLoss, position.instrument)}
            </span>
          </div>
        )}
        {position.takeProfit && (
          <div>
            <span className="text-green-400">TP:</span>{' '}
            <span className="text-white">
              {formatPrice(position.takeProfit, position.instrument)}
            </span>
          </div>
        )}
      </div>

      {/* Progress Bars */}
      {position.takeProfit && (
        <div className="mb-2">
          <ProgressBar
            value={position.progressToTP}
            color="green"
            label={`${position.progressToTP.toFixed(0)}% to TP`}
            height="sm"
          />
        </div>
      )}
      {position.stopLoss && (
        <div className="mb-3">
          <ProgressBar
            value={position.progressToSL}
            color="red"
            label={`${position.progressToSL.toFixed(0)}% to SL`}
            height="sm"
          />
        </div>
      )}

      {/* Metadata */}
      <div className="flex justify-between text-xs text-gray-400 mb-3">
        <span title="Position size">{position.units.toLocaleString()} units</span>
        <span title="Position age">{position.positionAge}</span>
        <span title="Signal source">{position.agentSource}</span>
      </div>

      {/* Quick Actions */}
      <div className="flex justify-end space-x-2">
        <button
          onClick={(e) => {
            e.stopPropagation()
            onModify(position.id)
          }}
          className="p-2 text-blue-400 hover:bg-blue-500/10 rounded transition-colors"
          aria-label="Modify position"
          title="Modify Stop Loss / Take Profit"
        >
          <Pencil className="w-4 h-4" />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation()
            onClose(position.id)
          }}
          className="p-2 text-red-400 hover:bg-red-500/10 rounded transition-colors"
          aria-label="Close position"
          title="Close position"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
})

PositionCard.displayName = 'PositionCard'

export default PositionCard
