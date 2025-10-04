/**
 * Close Position Confirmation Modal
 * Confirms position close with P&L impact preview
 */

import React, { useState } from 'react'
import { AlertTriangle, X } from 'lucide-react'
import Modal from '@/components/ui/Modal'
import { Position } from '@/types/positions'
import { formatInstrument, formatPrice } from '@/utils/positionCalculations'

interface ClosePositionConfirmProps {
  /** Position to close */
  position: Position | null
  /** Is modal open */
  isOpen: boolean
  /** Close modal callback */
  onClose: () => void
  /** Confirm close callback */
  onConfirm: (positionId: string) => Promise<void>
}

/**
 * Close position confirmation modal
 */
export function ClosePositionConfirm({
  position,
  isOpen,
  onClose,
  onConfirm,
}: ClosePositionConfirmProps) {
  const [isClosing, setIsClosing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!position) return null

  const handleConfirm = async () => {
    setIsClosing(true)
    setError(null)

    try {
      await onConfirm(position.id)
      onClose()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to close position'
      setError(errorMessage)
    } finally {
      setIsClosing(false)
    }
  }

  const isWinning = position.unrealizedPL > 0

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Close Position" size="sm">
      <div className="space-y-4">
        {/* Warning */}
        <div className="flex items-start gap-3 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded">
          <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-yellow-200">
            This will close your {formatInstrument(position.instrument)}{' '}
            {position.direction.toUpperCase()} position and realize the current P&L.
          </div>
        </div>

        {/* Position Summary */}
        <div className="bg-gray-800 rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-gray-400">Instrument</span>
            <span className="text-white font-semibold">
              {formatInstrument(position.instrument)}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-400">Direction</span>
            <span className="text-white font-semibold">{position.direction.toUpperCase()}</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-400">Size</span>
            <span className="text-white">{position.units.toLocaleString()} units</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-400">Entry Price</span>
            <span className="text-white">
              {formatPrice(position.entryPrice, position.instrument)}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-400">Current Price</span>
            <span className="text-white font-semibold">
              {formatPrice(position.currentPrice, position.instrument)}
            </span>
          </div>

          <div className="border-t border-gray-700 pt-3">
            <div className="flex items-center justify-between">
              <span className="text-gray-400 font-semibold">Realized P&L</span>
              <div className="text-right">
                <div
                  className={`text-xl font-bold ${
                    isWinning ? 'text-green-400' : 'text-red-400'
                  }`}
                >
                  {isWinning ? '+' : ''}${Math.abs(position.unrealizedPL).toFixed(2)}
                </div>
                <div className="text-sm text-gray-400">
                  ({isWinning ? '+' : ''}
                  {position.unrealizedPLPercentage.toFixed(2)}%)
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/30 rounded text-sm text-red-400">
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3 pt-2">
          <button
            onClick={onClose}
            disabled={isClosing}
            className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={isClosing}
            className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isClosing ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Closing...
              </>
            ) : (
              <>
                <X className="w-4 h-4" />
                Close Position
              </>
            )}
          </button>
        </div>
      </div>
    </Modal>
  )
}

export default ClosePositionConfirm
