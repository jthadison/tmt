'use client'

import { useState } from 'react'
import { Position, TradingPermissions, ManualOverride, OverrideAction } from '@/types/accountDetail'

/**
 * Props for ManualOverridePanel component
 */
interface ManualOverridePanelProps {
  /** Trading permissions */
  tradingPermissions: TradingPermissions
  /** Active positions for position-specific actions */
  positions: Position[]
  /** Loading state indicator */
  loading?: boolean
  /** Callback when override is submitted */
  onOverride?: (override: ManualOverride) => void
  /** Emergency mode for critical overrides */
  emergencyMode?: boolean
}

/**
 * Manual trading override panel for emergency controls
 * Provides secure manual intervention capabilities
 */
export function ManualOverridePanel({
  tradingPermissions,
  positions,
  loading = false,
  onOverride,
  emergencyMode = false
}: ManualOverridePanelProps) {
  const [selectedAction, setSelectedAction] = useState<OverrideAction>('close_position')
  const [selectedPosition, setSelectedPosition] = useState<string>('')
  const [reason, setReason] = useState('')
  const [parameters, setParameters] = useState<Record<string, number | string | boolean | undefined>>({})
  const [requireConfirmation, setRequireConfirmation] = useState(false)
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount)
  }

  const actionConfig: Record<OverrideAction, {
    label: string
    description: string
    severity: 'low' | 'medium' | 'high' | 'critical'
    icon: string
    requiresPosition?: boolean
    emergencyOnly?: boolean
  }> = {
    'close_position': {
      label: 'Close Position',
      description: 'Close a specific position immediately',
      severity: 'medium',
      icon: '⏹',
      requiresPosition: true
    },
    'close_all_positions': {
      label: 'Close All Positions',
      description: 'Close all open positions immediately',
      severity: 'high',
      icon: '🛑'
    },
    'emergency_stop': {
      label: 'Emergency Stop',
      description: 'Stop all trading activity and close positions',
      severity: 'critical',
      icon: '🚨',
      emergencyOnly: true
    },
    'modify_position': {
      label: 'Modify Position',
      description: 'Modify stop loss or take profit levels',
      severity: 'low',
      icon: '⚙',
      requiresPosition: true
    },
    'override_risk_limits': {
      label: 'Override Risk Limits',
      description: 'Temporarily override risk management rules',
      severity: 'high',
      icon: '⚠',
      emergencyOnly: true
    }
  }

  const getSeverityColor = (severity: string): string => {
    switch (severity) {
      case 'low':
        return 'text-blue-400 bg-blue-900/20 border-blue-500'
      case 'medium':
        return 'text-yellow-400 bg-yellow-900/20 border-yellow-500'
      case 'high':
        return 'text-orange-400 bg-orange-900/20 border-orange-500'
      case 'critical':
        return 'text-red-400 bg-red-900/20 border-red-500'
      default:
        return 'text-gray-400 bg-gray-900/20 border-gray-500'
    }
  }

  const canExecuteAction = (action: OverrideAction): boolean => {
    const config = actionConfig[action]
    
    // Check if emergency mode is required
    if (config.emergencyOnly && !emergencyMode) return false
    
    // Check basic trading permissions
    switch (action) {
      case 'close_position':
      case 'close_all_positions':
        return tradingPermissions.canClose
      case 'modify_position':
        return tradingPermissions.canModify
      case 'emergency_stop':
        return true // Always available in emergency
      case 'override_risk_limits':
        return emergencyMode // Only in emergency mode
      default:
        return false
    }
  }

  const handleActionChange = (action: OverrideAction) => {
    setSelectedAction(action)
    setSelectedPosition('')
    setParameters({})
    setReason('')
  }

  const handleParameterChange = (key: string, value: number | string | boolean | undefined) => {
    setParameters(prev => ({ ...prev, [key]: value }))
  }

  const validateOverride = (): string | null => {
    if (!reason.trim()) return 'Reason is required for all overrides'
    
    const config = actionConfig[selectedAction]
    if (config.requiresPosition && !selectedPosition) {
      return 'Position selection is required for this action'
    }
    
    if (selectedAction === 'modify_position') {
      if (!parameters.stopLoss && !parameters.takeProfit) {
        return 'At least one modification (stop loss or take profit) is required'
      }
    }
    
    return null
  }

  const handleSubmit = () => {
    const validationError = validateOverride()
    if (validationError) {
      alert(validationError)
      return
    }

    const override: ManualOverride = {
      action: selectedAction,
      positionId: selectedPosition || undefined,
      reason: reason.trim(),
      parameters,
      confirmed: !requireConfirmation
    }

    if (requireConfirmation || tradingPermissions.requiresConfirmation) {
      setShowConfirmDialog(true)
    } else {
      onOverride?.(override)
      resetForm()
    }
  }

  const handleConfirmedSubmit = () => {
    const override: ManualOverride = {
      action: selectedAction,
      positionId: selectedPosition || undefined,
      reason: reason.trim(),
      parameters,
      confirmed: true
    }

    onOverride?.(override)
    setShowConfirmDialog(false)
    resetForm()
  }

  const resetForm = () => {
    setReason('')
    setParameters({})
    setSelectedPosition('')
    setRequireConfirmation(false)
  }

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-700 rounded w-40"></div>
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-12 bg-gray-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-lg font-semibold text-white">
          Manual Override Panel
        </h3>
        {emergencyMode && (
          <div className="flex items-center gap-2 text-red-400 bg-red-900/20 px-3 py-1 rounded">
            <span>🚨</span>
            <span className="text-sm font-medium">Emergency Mode</span>
          </div>
        )}
      </div>

      {/* Permissions Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6 p-4 bg-gray-750 rounded-lg">
        <div className="text-center">
          <div className={`text-lg ${tradingPermissions.canTrade ? 'text-green-400' : 'text-red-400'}`}>
            {tradingPermissions.canTrade ? '✓' : '✗'}
          </div>
          <div className="text-sm text-gray-400">Can Trade</div>
        </div>
        <div className="text-center">
          <div className={`text-lg ${tradingPermissions.canClose ? 'text-green-400' : 'text-red-400'}`}>
            {tradingPermissions.canClose ? '✓' : '✗'}
          </div>
          <div className="text-sm text-gray-400">Can Close</div>
        </div>
        <div className="text-center">
          <div className={`text-lg ${tradingPermissions.canModify ? 'text-green-400' : 'text-red-400'}`}>
            {tradingPermissions.canModify ? '✓' : '✗'}
          </div>
          <div className="text-sm text-gray-400">Can Modify</div>
        </div>
        <div className="text-center">
          <div className="text-white text-lg">{tradingPermissions.maxPositionSize}</div>
          <div className="text-sm text-gray-400">Max Size</div>
        </div>
      </div>

      {/* Action Selection */}
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Override Action
          </label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {(Object.entries(actionConfig) as [OverrideAction, typeof actionConfig[OverrideAction]][]).map(([action, config]) => {
              const isAvailable = canExecuteAction(action)
              const isSelected = selectedAction === action
              
              return (
                <button
                  key={action}
                  onClick={() => isAvailable && handleActionChange(action)}
                  disabled={!isAvailable}
                  className={`
                    p-3 rounded-lg border text-left transition-all
                    ${isSelected 
                      ? getSeverityColor(config.severity)
                      : isAvailable 
                        ? 'border-gray-600 bg-gray-700 hover:bg-gray-650 text-white'
                        : 'border-gray-700 bg-gray-750 text-gray-500 cursor-not-allowed'
                    }
                  `}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-lg">{config.icon}</span>
                    <span className="font-medium">{config.label}</span>
                  </div>
                  <div className="text-sm opacity-75">{config.description}</div>
                  {!isAvailable && (
                    <div className="text-xs text-red-400 mt-1">
                      {config.emergencyOnly ? 'Emergency mode required' : 'Permission denied'}
                    </div>
                  )}
                </button>
              )
            })}
          </div>
        </div>

        {/* Position Selection */}
        {actionConfig[selectedAction]?.requiresPosition && (
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Select Position
            </label>
            <select
              value={selectedPosition}
              onChange={(e) => setSelectedPosition(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            >
              <option value="">Choose a position...</option>
              {positions.map((position) => (
                <option key={position.id} value={position.id}>
                  {position.symbol} - {position.type.toUpperCase()} {position.size} lots ({formatCurrency(position.pnl)})
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Action-Specific Parameters */}
        {selectedAction === 'modify_position' && selectedPosition && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                New Stop Loss
              </label>
              <input
                type="number"
                step="0.00001"
                value={parameters.stopLoss?.toString() || ''}
                onChange={(e) => handleParameterChange('stopLoss', parseFloat(e.target.value) || undefined)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                placeholder="Enter new stop loss price"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                New Take Profit
              </label>
              <input
                type="number"
                step="0.00001"
                value={parameters.takeProfit?.toString() || ''}
                onChange={(e) => handleParameterChange('takeProfit', parseFloat(e.target.value) || undefined)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                placeholder="Enter new take profit price"
              />
            </div>
          </div>
        )}

        {selectedAction === 'override_risk_limits' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                New Max Position Size
              </label>
              <input
                type="number"
                step="0.1"
                value={parameters.maxPositionSize?.toString() || ''}
                onChange={(e) => handleParameterChange('maxPositionSize', parseFloat(e.target.value) || undefined)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                placeholder="Enter new max size"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Override Duration (minutes)
              </label>
              <input
                type="number"
                value={parameters.duration?.toString() || ''}
                onChange={(e) => handleParameterChange('duration', parseInt(e.target.value) || undefined)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                placeholder="Override duration"
              />
            </div>
          </div>
        )}

        {/* Reason */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Reason for Override *
          </label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            placeholder="Explain why this manual override is necessary..."
            required
          />
        </div>

        {/* Additional Options */}
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-gray-300">
            <input
              type="checkbox"
              checked={requireConfirmation}
              onChange={(e) => setRequireConfirmation(e.target.checked)}
              className="rounded border-gray-600 bg-gray-700 text-blue-600"
            />
            Require additional confirmation
          </label>
        </div>

        {/* Submit Button */}
        <div className="flex justify-end gap-3 pt-4 border-t border-gray-700">
          <button
            onClick={resetForm}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
          >
            Reset
          </button>
          <button
            onClick={handleSubmit}
            disabled={!reason.trim()}
            className={`
              px-6 py-2 rounded font-medium transition-colors
              ${getSeverityColor(actionConfig[selectedAction].severity).replace('text-', 'bg-').replace('bg-', 'text-').replace('/20', '')}
              disabled:opacity-50 disabled:cursor-not-allowed
            `}
          >
            Execute {actionConfig[selectedAction].label}
          </button>
        </div>
      </div>

      {/* Confirmation Dialog */}
      {showConfirmDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 max-w-md w-mx">
            <h4 className="text-lg font-semibold text-white mb-4">
              Confirm Override Action
            </h4>
            <div className="space-y-3 mb-6">
              <div className="flex justify-between">
                <span className="text-gray-400">Action:</span>
                <span className="text-white font-medium">{actionConfig[selectedAction].label}</span>
              </div>
              {selectedPosition && (
                <div className="flex justify-between">
                  <span className="text-gray-400">Position:</span>
                  <span className="text-white">
                    {positions.find(p => p.id === selectedPosition)?.symbol}
                  </span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-gray-400">Reason:</span>
                <span className="text-white text-sm">{reason}</span>
              </div>
            </div>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowConfirmDialog(false)}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmedSubmit}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded transition-colors"
              >
                Confirm Override
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}