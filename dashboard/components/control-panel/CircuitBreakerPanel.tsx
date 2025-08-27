'use client'

import { useState } from 'react'
import { CircuitBreakerInfo, CircuitBreakerControlRequest } from '@/types/systemControl'

/**
 * Props for CircuitBreakerPanel component
 */
interface CircuitBreakerPanelProps {
  /** Array of circuit breaker information */
  circuitBreakers: CircuitBreakerInfo[]
  /** Callback when circuit breaker action is requested */
  onCircuitBreakerAction: (request: CircuitBreakerControlRequest) => void
  /** Callback when reset all circuit breakers is requested */
  onResetAllBreakers?: () => void
  /** Show compact view */
  compact?: boolean
  /** Loading state indicator */
  loading?: boolean
}

/**
 * Circuit breaker control panel for manual activation/deactivation
 * Displays circuit breaker status and provides manual override controls
 */
export function CircuitBreakerPanel({
  circuitBreakers,
  onCircuitBreakerAction,
  onResetAllBreakers,
  compact = false,
  loading = false
}: CircuitBreakerPanelProps) {
  const [selectedBreaker, setSelectedBreaker] = useState<string | null>(null)
  const [showActionDialog, setShowActionDialog] = useState(false)
  const [selectedAction, setSelectedAction] = useState<'open' | 'close' | 'reset'>('reset')
  const [actionReason, setActionReason] = useState('')
  const [overrideDuration, setOverrideDuration] = useState(30) // minutes

  const getStatusColor = (status: CircuitBreakerInfo['status']): string => {
    switch (status) {
      case 'closed':
        return 'text-green-400'
      case 'open':
        return 'text-red-400'
      case 'half-open':
        return 'text-yellow-400'
      default:
        return 'text-gray-400'
    }
  }

  const getStatusIcon = (status: CircuitBreakerInfo['status']): string => {
    switch (status) {
      case 'closed':
        return '✓'
      case 'open':
        return '✗'
      case 'half-open':
        return '◐'
      default:
        return '?'
    }
  }

  const getStatusBadge = (status: CircuitBreakerInfo['status']): string => {
    switch (status) {
      case 'closed':
        return 'bg-green-900/30 text-green-400 border-green-500/30'
      case 'open':
        return 'bg-red-900/30 text-red-400 border-red-500/30'
      case 'half-open':
        return 'bg-yellow-900/30 text-yellow-400 border-yellow-500/30'
      default:
        return 'bg-gray-900/30 text-gray-400 border-gray-500/30'
    }
  }

  const getHealthColor = (successRate: number): string => {
    if (successRate >= 95) return 'text-green-400'
    if (successRate >= 85) return 'text-yellow-400'
    return 'text-red-400'
  }

  const getStatusDescription = (status: CircuitBreakerInfo['status']): string => {
    switch (status) {
      case 'closed':
        return 'Normal operation - requests allowed'
      case 'open':
        return 'Breaker tripped - blocking requests'
      case 'half-open':
        return 'Testing recovery - limited requests'
      default:
        return 'Unknown status'
    }
  }

  const formatTimeAgo = (date: Date): string => {
    const diff = Date.now() - date.getTime()
    const minutes = Math.floor(diff / (60 * 1000))
    const hours = Math.floor(diff / (60 * 60 * 1000))
    const days = Math.floor(diff / (24 * 60 * 60 * 1000))
    
    if (days > 0) return `${days}d ago`
    if (hours > 0) return `${hours}h ago`
    if (minutes > 0) return `${minutes}m ago`
    return 'Just now'
  }

  const handleBreakerAction = (breakerId: string) => {
    setSelectedBreaker(breakerId)
    setShowActionDialog(true)
  }

  const handleConfirmAction = () => {
    if (!selectedBreaker || !actionReason.trim()) return

    const request: CircuitBreakerControlRequest = {
      breakerId: selectedBreaker,
      action: selectedAction,
      reason: actionReason.trim(),
      overrideDuration: selectedAction !== 'reset' ? overrideDuration : undefined
    }

    onCircuitBreakerAction(request)
    setShowActionDialog(false)
    setSelectedBreaker(null)
    setActionReason('')
  }

  const getActionDescription = (action: 'open' | 'close' | 'reset'): string => {
    switch (action) {
      case 'open':
        return 'Force open the circuit breaker (block all requests)'
      case 'close':
        return 'Force close the circuit breaker (allow all requests)'
      case 'reset':
        return 'Reset failure count and return to automatic operation'
      default:
        return ''
    }
  }

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-700 rounded w-40"></div>
          <div className="grid grid-cols-1 gap-4">
            {Array.from({ length: compact ? 2 : 4 }).map((_, i) => (
              <div key={i} className="h-24 bg-gray-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="bg-gray-800 rounded-lg p-6">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-semibold text-white">
            Circuit Breakers {compact && '(Overview)'}
          </h3>
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-400">
              {circuitBreakers.filter(cb => cb.status === 'closed').length} / {circuitBreakers.length} closed
            </div>
            {onResetAllBreakers && circuitBreakers.some(cb => cb.status === 'open') && (
              <button
                onClick={onResetAllBreakers}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm font-medium transition-colors flex items-center gap-2"
                title="Reset all circuit breakers to closed state and re-enable trading"
              >
                🔄 Reset All
              </button>
            )}
          </div>
        </div>

        {/* Circuit Breaker Grid */}
        <div className={`grid gap-4 ${compact ? 'grid-cols-1' : 'grid-cols-1 lg:grid-cols-2'}`}>
          {circuitBreakers.map((breaker) => (
            <div
              key={breaker.id}
              className={`
                rounded-lg p-4 border transition-colors
                ${breaker.status === 'open' 
                  ? 'bg-red-900/10 border-red-500/30 hover:border-red-500/50'
                  : breaker.status === 'half-open'
                  ? 'bg-yellow-900/10 border-yellow-500/30 hover:border-yellow-500/50'
                  : 'bg-gray-750 border-gray-700 hover:border-gray-600'
                }
              `}
            >
              <div className="flex justify-between items-start mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className={`text-lg ${getStatusColor(breaker.status)}`}>
                      {getStatusIcon(breaker.status)}
                    </span>
                    <h4 className="font-medium text-white">{breaker.name}</h4>
                    <span className={`px-2 py-1 rounded text-xs border ${getStatusBadge(breaker.status)}`}>
                      {breaker.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-sm text-gray-400 mb-1">
                    {breaker.category}
                  </div>
                  <div className="text-sm text-gray-300">
                    {getStatusDescription(breaker.status)}
                  </div>
                </div>
                
                <button
                  onClick={() => handleBreakerAction(breaker.id)}
                  className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-1 rounded text-sm transition-colors"
                >
                  Control
                </button>
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-3 gap-4 mb-3">
                <div>
                  <div className="text-xs text-gray-400">Success Rate</div>
                  <div className={`font-medium ${getHealthColor(breaker.successRate)}`}>
                    {breaker.successRate.toFixed(1)}%
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-400">Failures</div>
                  <div className="font-medium text-white">
                    {breaker.failures} / {breaker.threshold}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-400">Manual Override</div>
                  <div className={`font-medium ${breaker.isManualOverride ? 'text-yellow-400' : 'text-gray-400'}`}>
                    {breaker.isManualOverride ? 'Active' : 'Auto'}
                  </div>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="mb-3">
                <div className="flex justify-between text-xs text-gray-400 mb-1">
                  <span>Failure Threshold</span>
                  <span>{((breaker.failures / breaker.threshold) * 100).toFixed(0)}%</span>
                </div>
                <div className="w-full bg-gray-600 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full transition-all ${
                      breaker.failures >= breaker.threshold 
                        ? 'bg-red-500' 
                        : breaker.failures / breaker.threshold > 0.8 
                        ? 'bg-yellow-500' 
                        : 'bg-green-500'
                    }`}
                    style={{ width: `${Math.min(100, (breaker.failures / breaker.threshold) * 100)}%` }}
                  ></div>
                </div>
              </div>

              {/* Description */}
              {!compact && (
                <div className="text-sm text-gray-400 mb-3">
                  {breaker.description}
                </div>
              )}

              {/* Status Details */}
              <div className="flex justify-between items-center text-xs text-gray-500">
                {breaker.lastTriggered && (
                  <span>
                    Last triggered: {formatTimeAgo(breaker.lastTriggered)}
                  </span>
                )}
                {breaker.resetTime && breaker.status === 'open' && (
                  <span className="text-yellow-400">
                    Reset: {breaker.resetTime.toLocaleTimeString()}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Summary Statistics */}
        {!compact && (
          <div className="mt-6 pt-6 border-t border-gray-700">
            <h4 className="text-white font-medium mb-3">Circuit Breaker Summary</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="text-gray-400">Total Breakers</div>
                <div className="text-white font-medium">{circuitBreakers.length}</div>
              </div>
              <div>
                <div className="text-gray-400">Open (Blocking)</div>
                <div className="text-red-400 font-medium">
                  {circuitBreakers.filter(cb => cb.status === 'open').length}
                </div>
              </div>
              <div>
                <div className="text-gray-400">Manual Overrides</div>
                <div className="text-yellow-400 font-medium">
                  {circuitBreakers.filter(cb => cb.isManualOverride).length}
                </div>
              </div>
              <div>
                <div className="text-gray-400">Average Success Rate</div>
                <div className={`font-medium ${getHealthColor(
                  circuitBreakers.reduce((sum, cb) => sum + cb.successRate, 0) / circuitBreakers.length
                )}`}>
                  {(circuitBreakers.reduce((sum, cb) => sum + cb.successRate, 0) / circuitBreakers.length).toFixed(1)}%
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Circuit Breaker Action Dialog */}
      {showActionDialog && selectedBreaker && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-lg max-w-md w-full border border-gray-700">
            <div className="p-6 border-b border-gray-700">
              <h3 className="text-xl font-bold text-white">Circuit Breaker Control</h3>
              <p className="text-gray-400 text-sm mt-1">
                {circuitBreakers.find(cb => cb.id === selectedBreaker)?.name}
              </p>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="block text-gray-300 text-sm mb-2">Action</label>
                <select
                  value={selectedAction}
                  onChange={(e) => setSelectedAction(e.target.value as 'open' | 'close' | 'reset')}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                >
                  <option value="reset">Reset to Automatic</option>
                  <option value="open">Force Open (Block Requests)</option>
                  <option value="close">Force Close (Allow Requests)</option>
                </select>
                <p className="text-gray-500 text-xs mt-1">
                  {getActionDescription(selectedAction)}
                </p>
              </div>

              {selectedAction !== 'reset' && (
                <div>
                  <label className="block text-gray-300 text-sm mb-2">
                    Override Duration (minutes)
                  </label>
                  <input
                    type="number"
                    value={overrideDuration}
                    onChange={(e) => setOverrideDuration(parseInt(e.target.value) || 30)}
                    min="1"
                    max="1440"
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                  />
                  <p className="text-gray-500 text-xs mt-1">
                    Manual override will automatically reset after this duration
                  </p>
                </div>
              )}

              <div>
                <label className="block text-gray-300 text-sm mb-2">Reason *</label>
                <textarea
                  value={actionReason}
                  onChange={(e) => setActionReason(e.target.value)}
                  placeholder="Explain why this action is necessary..."
                  rows={3}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                  required
                />
              </div>

              {selectedAction === 'open' && (
                <div className="bg-red-900/20 border border-red-500/30 rounded p-3">
                  <div className="text-red-400 text-sm font-medium">🛑 Warning</div>
                  <div className="text-red-200 text-sm mt-1">
                    This will block all requests through this circuit breaker. Ensure this is intentional.
                  </div>
                </div>
              )}

              {selectedAction === 'close' && (
                <div className="bg-yellow-900/20 border border-yellow-500/30 rounded p-3">
                  <div className="text-yellow-400 text-sm font-medium">⚠️ Caution</div>
                  <div className="text-yellow-200 text-sm mt-1">
                    This will allow all requests even if failures exceed the threshold. Monitor closely.
                  </div>
                </div>
              )}
            </div>

            <div className="p-6 border-t border-gray-700 flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowActionDialog(false)
                  setSelectedBreaker(null)
                  setActionReason('')
                }}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmAction}
                disabled={!actionReason.trim()}
                className={`
                  px-4 py-2 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                  ${selectedAction === 'open' 
                    ? 'bg-red-600 hover:bg-red-700' 
                    : selectedAction === 'close'
                    ? 'bg-yellow-600 hover:bg-yellow-700'
                    : 'bg-blue-600 hover:bg-blue-700'
                  }
                `}
              >
                Execute Action
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}