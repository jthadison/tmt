/**
 * Modify Position Modal
 * Edit stop loss and take profit for existing position
 */

import React, { useState, useEffect } from 'react'
import { Save, AlertCircle } from 'lucide-react'
import Modal from '@/components/ui/Modal'
import { Position } from '@/types/positions'
import { formatInstrument, formatPrice, getPipValue } from '@/utils/positionCalculations'

interface ModifyPositionModalProps {
  /** Position to modify */
  position: Position | null
  /** Is modal open */
  isOpen: boolean
  /** Close modal callback */
  onClose: () => void
  /** Confirm modification callback */
  onConfirm: (positionId: string, stopLoss?: number, takeProfit?: number) => Promise<void>
}

/**
 * Modify position modal
 */
export function ModifyPositionModal({
  position,
  isOpen,
  onClose,
  onConfirm,
}: ModifyPositionModalProps) {
  const [stopLoss, setStopLoss] = useState('')
  const [takeProfit, setTakeProfit] = useState('')
  const [isModifying, setIsModifying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [validationError, setValidationError] = useState<string | null>(null)

  // Initialize form with current values
  useEffect(() => {
    if (position) {
      setStopLoss(position.stopLoss ? String(position.stopLoss) : '')
      setTakeProfit(position.takeProfit ? String(position.takeProfit) : '')
      setError(null)
      setValidationError(null)
    }
  }, [position])

  if (!position) return null

  // Validate SL/TP values
  const validateInputs = (): boolean => {
    const slValue = stopLoss ? parseFloat(stopLoss) : undefined
    const tpValue = takeProfit ? parseFloat(takeProfit) : undefined

    // Check if values are valid numbers
    if (stopLoss && (isNaN(slValue!) || slValue! <= 0)) {
      setValidationError('Stop Loss must be a positive number')
      return false
    }

    if (takeProfit && (isNaN(tpValue!) || tpValue! <= 0)) {
      setValidationError('Take Profit must be a positive number')
      return false
    }

    // Validate based on direction
    if (position.direction === 'long') {
      // For LONG positions:
      // SL must be below entry price
      // TP must be above entry price
      if (slValue && slValue >= position.entryPrice) {
        setValidationError('Stop Loss must be below entry price for LONG positions')
        return false
      }

      if (tpValue && tpValue <= position.entryPrice) {
        setValidationError('Take Profit must be above entry price for LONG positions')
        return false
      }
    } else {
      // For SHORT positions:
      // SL must be above entry price
      // TP must be below entry price
      if (slValue && slValue <= position.entryPrice) {
        setValidationError('Stop Loss must be above entry price for SHORT positions')
        return false
      }

      if (tpValue && tpValue >= position.entryPrice) {
        setValidationError('Take Profit must be below entry price for SHORT positions')
        return false
      }
    }

    setValidationError(null)
    return true
  }

  const handleConfirm = async () => {
    if (!validateInputs()) return

    setIsModifying(true)
    setError(null)

    try {
      const slValue = stopLoss ? parseFloat(stopLoss) : undefined
      const tpValue = takeProfit ? parseFloat(takeProfit) : undefined

      await onConfirm(position.id, slValue, tpValue)
      onClose()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to modify position'
      setError(errorMessage)
    } finally {
      setIsModifying(false)
    }
  }

  const pipValue = getPipValue(position.instrument)

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Modify Position" size="md">
      <div className="space-y-4">
        {/* Position Info */}
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400">Position</span>
            <span className="text-white font-semibold">
              {formatInstrument(position.instrument)} {position.direction.toUpperCase()}
            </span>
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
        </div>

        {/* Form Fields */}
        <div className="space-y-4">
          {/* Stop Loss */}
          <div>
            <label htmlFor="stopLoss" className="block text-sm font-medium text-gray-300 mb-2">
              Stop Loss
              <span className="text-gray-500 ml-2 font-normal">
                (must be {position.direction === 'long' ? 'below' : 'above'} entry)
              </span>
            </label>
            <input
              id="stopLoss"
              type="number"
              step={pipValue}
              value={stopLoss}
              onChange={(e) => setStopLoss(e.target.value)}
              placeholder={`e.g., ${formatPrice(
                position.direction === 'long'
                  ? position.entryPrice - 0.01
                  : position.entryPrice + 0.01,
                position.instrument
              )}`}
              className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
            />
            {position.stopLoss && (
              <div className="mt-1 text-xs text-gray-400">
                Current: {formatPrice(position.stopLoss, position.instrument)}
              </div>
            )}
          </div>

          {/* Take Profit */}
          <div>
            <label htmlFor="takeProfit" className="block text-sm font-medium text-gray-300 mb-2">
              Take Profit
              <span className="text-gray-500 ml-2 font-normal">
                (must be {position.direction === 'long' ? 'above' : 'below'} entry)
              </span>
            </label>
            <input
              id="takeProfit"
              type="number"
              step={pipValue}
              value={takeProfit}
              onChange={(e) => setTakeProfit(e.target.value)}
              placeholder={`e.g., ${formatPrice(
                position.direction === 'long'
                  ? position.entryPrice + 0.01
                  : position.entryPrice - 0.01,
                position.instrument
              )}`}
              className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
            />
            {position.takeProfit && (
              <div className="mt-1 text-xs text-gray-400">
                Current: {formatPrice(position.takeProfit, position.instrument)}
              </div>
            )}
          </div>
        </div>

        {/* Validation Error */}
        {validationError && (
          <div className="flex items-start gap-2 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded text-sm text-yellow-400">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <span>{validationError}</span>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/30 rounded text-sm text-red-400">
            {error}
          </div>
        )}

        {/* Help Text */}
        <div className="text-xs text-gray-500 bg-gray-800/50 rounded p-3">
          <div className="font-semibold text-gray-400 mb-1">Tips:</div>
          <ul className="space-y-1 list-disc list-inside">
            <li>Leave fields empty to remove SL/TP</li>
            <li>Use pip increments: {pipValue} for {formatInstrument(position.instrument)}</li>
            <li>Changes take effect immediately</li>
          </ul>
        </div>

        {/* Actions */}
        <div className="flex gap-3 pt-2">
          <button
            onClick={onClose}
            disabled={isModifying}
            className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={isModifying || !!validationError}
            className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isModifying ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save Changes
              </>
            )}
          </button>
        </div>
      </div>
    </Modal>
  )
}

export default ModifyPositionModal
