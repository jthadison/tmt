/**
 * Position Detail Modal
 * Comprehensive view of position information
 */

import React from 'react'
import { X, Pencil, TrendingUp, TrendingDown, Clock, BarChart3 } from 'lucide-react'
import Modal from '@/components/ui/Modal'
import { Position } from '@/types/positions'
import { Badge } from '@/components/ui/Badge'
import { ProgressBar } from '@/components/ui/ProgressBar'
import { formatInstrument, formatPrice } from '@/utils/positionCalculations'
import { cn } from '@/lib/utils'

interface PositionDetailModalProps {
  /** Position to display */
  position: Position | null
  /** Is modal open */
  isOpen: boolean
  /** Close modal callback */
  onClose: () => void
  /** Close position callback */
  onClosePosition: (positionId: string) => void
  /** Modify position callback */
  onModifyPosition: (positionId: string) => void
}

/**
 * Position detail modal
 */
export function PositionDetailModal({
  position,
  isOpen,
  onClose,
  onClosePosition,
  onModifyPosition,
}: PositionDetailModalProps) {
  if (!position) return null

  const isWinning = position.unrealizedPL > 0

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white mb-2">
              {formatInstrument(position.instrument)}
            </h2>
            <div className="flex items-center gap-2">
              <Badge
                variant={position.direction === 'long' ? 'success' : 'danger'}
                icon={position.direction === 'long' ? TrendingUp : TrendingDown}
              >
                {position.direction.toUpperCase()}
              </Badge>
              <span className="text-sm text-gray-400">
                {position.units.toLocaleString()} units
              </span>
            </div>
          </div>
        </div>

        {/* P&L Summary */}
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="text-sm text-gray-400 mb-2">Unrealized P&L</div>
          <div
            className={cn(
              'text-4xl font-bold mb-1',
              isWinning ? 'text-green-400' : 'text-red-400'
            )}
          >
            {isWinning ? '+' : ''}${Math.abs(position.unrealizedPL).toFixed(2)}
          </div>
          <div className="text-lg text-gray-400">
            {isWinning ? '+' : ''}
            {position.unrealizedPLPercentage.toFixed(2)}%
          </div>
        </div>

        {/* Price Information */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="text-sm text-gray-400 mb-1">Entry Price</div>
            <div className="text-xl font-semibold text-white">
              {formatPrice(position.entryPrice, position.instrument)}
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-4">
            <div className="text-sm text-gray-400 mb-1">Current Price</div>
            <div className="text-xl font-semibold text-white">
              {formatPrice(position.currentPrice, position.instrument)}
            </div>
          </div>

          {position.stopLoss && (
            <div className="bg-gray-800 rounded-lg p-4">
              <div className="text-sm text-red-400 mb-1">Stop Loss</div>
              <div className="text-xl font-semibold text-white">
                {formatPrice(position.stopLoss, position.instrument)}
              </div>
            </div>
          )}

          {position.takeProfit && (
            <div className="bg-gray-800 rounded-lg p-4">
              <div className="text-sm text-green-400 mb-1">Take Profit</div>
              <div className="text-xl font-semibold text-white">
                {formatPrice(position.takeProfit, position.instrument)}
              </div>
            </div>
          )}
        </div>

        {/* Progress Bars */}
        {(position.takeProfit || position.stopLoss) && (
          <div className="bg-gray-800 rounded-lg p-4 space-y-3">
            <div className="text-sm font-semibold text-gray-300 mb-3">Target Progress</div>

            {position.takeProfit && (
              <div>
                <ProgressBar
                  value={position.progressToTP}
                  color="green"
                  label="Progress to Take Profit"
                  showPercentage
                  height="md"
                />
                {position.isNearTP && (
                  <div className="mt-2 text-xs text-yellow-400 flex items-center gap-1">
                    <BarChart3 className="w-3 h-3" />
                    Near take profit target
                  </div>
                )}
              </div>
            )}

            {position.stopLoss && (
              <div>
                <ProgressBar
                  value={position.progressToSL}
                  color="red"
                  label="Progress to Stop Loss"
                  showPercentage
                  height="md"
                />
                {position.isNearSL && (
                  <div className="mt-2 text-xs text-orange-400 flex items-center gap-1">
                    <BarChart3 className="w-3 h-3" />
                    Near stop loss target
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Position Metadata */}
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="text-sm font-semibold text-gray-300 mb-3">Position Details</div>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-400 flex items-center gap-2">
                <Clock className="w-4 h-4" />
                Position Age
              </span>
              <span className="text-white">{position.positionAge}</span>
            </div>

            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-400">Open Time</span>
              <span className="text-white">
                {new Date(position.openTime).toLocaleString()}
              </span>
            </div>

            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-400">Signal Source</span>
              <span className="text-white">{position.agentSource}</span>
            </div>

            {position.accountId && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-400">Account ID</span>
                <span className="text-white font-mono text-xs">{position.accountId}</span>
              </div>
            )}

            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-400">Position ID</span>
              <span className="text-white font-mono text-xs">{position.id}</span>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 pt-4 border-t border-gray-700">
          <button
            onClick={() => {
              onModifyPosition(position.id)
              onClose()
            }}
            className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors flex items-center justify-center gap-2"
          >
            <Pencil className="w-4 h-4" />
            Modify SL/TP
          </button>
          <button
            onClick={() => {
              onClosePosition(position.id)
              onClose()
            }}
            className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded transition-colors flex items-center justify-center gap-2"
          >
            <X className="w-4 h-4" />
            Close Position
          </button>
        </div>
      </div>
    </Modal>
  )
}

export default PositionDetailModal
