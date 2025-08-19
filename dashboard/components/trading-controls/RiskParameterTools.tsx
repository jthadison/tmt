/**
 * Risk Parameter Tools Component - AC4
 * Story 9.5: Risk parameter modification tools with validation against compliance rules
 * 
 * SECURITY: Administrator access only - all parameter changes require admin authentication and audit logging
 */

'use client'

import React, { useState, useMemo } from 'react'
import {
  RiskParameters,
  RiskCategory,
  RiskParameterHistory,
  ComplianceCheck
} from '@/types/tradingControls'
import Card from '@/components/ui/Card'
import Modal from '@/components/ui/Modal'

/**
 * Props for RiskParameterTools component
 */
interface RiskParameterToolsProps {
  /** Array of risk parameters */
  riskParameters: RiskParameters[]
  /** Loading state */
  loading?: boolean
  /** Error message */
  error?: string
  /** Callback to update risk parameter */
  onUpdateParameter?: (parameterId: string, newValue: number, justification: string) => Promise<boolean>
  /** Callback to refresh parameters */
  onRefresh?: () => void
}

/**
 * Individual risk parameter card component
 */
function RiskParameterCard({
  parameter,
  onUpdate
}: {
  parameter: RiskParameters
  onUpdate?: (parameterId: string, newValue: number, justification: string) => Promise<boolean>
}) {
  const [showEditModal, setShowEditModal] = useState(false)
  const [newValue, setNewValue] = useState(parameter.currentValue.toString())
  const [justification, setJustification] = useState('')
  const [updating, setUpdating] = useState(false)
  const [showHistory, setShowHistory] = useState(false)

  const getCategoryColor = (category: RiskCategory): string => {
    switch (category) {
      case 'position_sizing': return 'text-blue-400 bg-blue-900/20'
      case 'daily_limits': return 'text-red-400 bg-red-900/20'
      case 'drawdown_limits': return 'text-orange-400 bg-orange-900/20'
      case 'exposure_limits': return 'text-purple-400 bg-purple-900/20'
      case 'volatility_controls': return 'text-yellow-400 bg-yellow-900/20'
      case 'correlation_limits': return 'text-green-400 bg-green-900/20'
      case 'leverage_controls': return 'text-pink-400 bg-pink-900/20'
      default: return 'text-gray-400 bg-gray-900/20'
    }
  }

  const getCategoryIcon = (category: RiskCategory): string => {
    switch (category) {
      case 'position_sizing': return '📊'
      case 'daily_limits': return '📅'
      case 'drawdown_limits': return '📉'
      case 'exposure_limits': return '🎯'
      case 'volatility_controls': return '📈'
      case 'correlation_limits': return '🔗'
      case 'leverage_controls': return '⚖️'
      default: return '⚙️'
    }
  }

  const formatValue = (value: number): string => {
    if (parameter.unit === 'USD') {
      return `$${value.toLocaleString()}`
    } else if (parameter.unit === '%') {
      return `${value}%`
    } else {
      return `${value} ${parameter.unit}`
    }
  }

  const validateNewValue = (value: number): { valid: boolean; message?: string } => {
    if (isNaN(value)) {
      return { valid: false, message: 'Please enter a valid number' }
    }
    
    if (value < parameter.minValue) {
      return { valid: false, message: `Value must be at least ${formatValue(parameter.minValue)}` }
    }
    
    if (value > parameter.maxValue) {
      return { valid: false, message: `Value must not exceed ${formatValue(parameter.maxValue)}` }
    }
    
    return { valid: true }
  }

  const handleUpdateSubmit = async () => {
    if (!onUpdate) return

    const numericValue = parseFloat(newValue)
    const validation = validateNewValue(numericValue)
    
    if (!validation.valid) {
      alert(validation.message)
      return
    }

    if (!justification.trim()) {
      alert('Justification is required for parameter changes')
      return
    }

    setUpdating(true)
    try {
      const success = await onUpdate(parameter.id, numericValue, justification.trim())
      if (success) {
        setShowEditModal(false)
        setJustification('')
        setNewValue(parameter.currentValue.toString())
      }
    } finally {
      setUpdating(false)
    }
  }

  const calculateChangeImpact = (): { percentage: number; direction: 'increase' | 'decrease' | 'none' } => {
    const numericValue = parseFloat(newValue)
    if (isNaN(numericValue) || numericValue === parameter.currentValue) {
      return { percentage: 0, direction: 'none' }
    }
    
    const percentage = ((numericValue - parameter.currentValue) / parameter.currentValue) * 100
    return {
      percentage: Math.abs(percentage),
      direction: numericValue > parameter.currentValue ? 'increase' : 'decrease'
    }
  }

  const change = calculateChangeImpact()
  const isSignificantChange = change.percentage > 25
  const isDangerousChange = change.percentage > 50

  return (
    <>
      <Card>
        <div className="space-y-4">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div className="flex items-start space-x-3">
              <span className="text-2xl">{getCategoryIcon(parameter.category)}</span>
              <div>
                <h3 className="text-lg font-semibold text-white">{parameter.name}</h3>
                <p className="text-sm text-gray-400">{parameter.description}</p>
                <div className={`inline-flex px-2 py-1 rounded text-xs font-medium mt-1 ${getCategoryColor(parameter.category)}`}>
                  {parameter.category.replace('_', ' ').toUpperCase()}
                </div>
              </div>
            </div>
            
            {parameter.complianceRequired && (
              <div className="text-orange-400 text-sm">
                <span className="mr-1">⚠</span>
                Compliance Required
              </div>
            )}
          </div>

          {/* Current Value Display */}
          <div className="bg-gray-800 p-4 rounded-lg">
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <div className="text-green-400 font-medium text-sm">Default</div>
                <div className="text-white text-lg font-bold">{formatValue(parameter.defaultValue)}</div>
              </div>
              <div>
                <div className="text-blue-400 font-medium text-sm">Current</div>
                <div className="text-white text-xl font-bold">{formatValue(parameter.currentValue)}</div>
              </div>
              <div>
                <div className="text-gray-400 font-medium text-sm">Range</div>
                <div className="text-white text-sm">
                  {formatValue(parameter.minValue)} - {formatValue(parameter.maxValue)}
                </div>
              </div>
            </div>
          </div>

          {/* Modification Info */}
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Last Modified:</span>
              <span className="text-white">{parameter.lastModified.toLocaleDateString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Modified By:</span>
              <span className="text-white">{parameter.lastModifiedBy}</span>
            </div>
            {parameter.history.length > 0 && (
              <div className="flex justify-between">
                <span className="text-gray-400">History:</span>
                <button
                  onClick={() => setShowHistory(true)}
                  className="text-blue-400 hover:text-blue-300 text-sm underline"
                >
                  View {parameter.history.length} changes
                </button>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex space-x-2">
            <button
              onClick={() => {
                setNewValue(parameter.currentValue.toString())
                setShowEditModal(true)
              }}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded font-medium"
            >
              Modify Parameter
            </button>
            <button
              onClick={() => {
                setNewValue(parameter.defaultValue.toString())
                setJustification(`Reset ${parameter.name} to default value`)
                setShowEditModal(true)
              }}
              className="bg-gray-600 hover:bg-gray-700 text-white py-2 px-4 rounded font-medium"
            >
              Reset to Default
            </button>
          </div>
        </div>
      </Card>

      {/* Edit Parameter Modal */}
      <Modal isOpen={showEditModal} onClose={() => setShowEditModal(false)} size="md">
        <div className="bg-gray-900 p-6">
          <h2 className="text-xl font-bold text-white mb-4">
            Modify {parameter.name}
          </h2>
          
          {/* Current vs New Value */}
          <div className="mb-6 p-4 bg-gray-800 rounded-lg">
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center">
                <div className="text-gray-400 text-sm mb-1">Current Value</div>
                <div className="text-white text-lg font-bold">{formatValue(parameter.currentValue)}</div>
              </div>
              <div className="text-center">
                <div className="text-gray-400 text-sm mb-1">New Value</div>
                <div className="text-blue-400 text-lg font-bold">
                  {isNaN(parseFloat(newValue)) ? '-' : formatValue(parseFloat(newValue))}
                </div>
              </div>
            </div>
            
            {change.direction !== 'none' && (
              <div className="mt-3 text-center">
                <div className={`text-sm font-medium ${
                  isDangerousChange ? 'text-red-400' :
                  isSignificantChange ? 'text-yellow-400' : 'text-blue-400'
                }`}>
                  {change.direction === 'increase' ? '↗' : '↘'} {change.percentage.toFixed(1)}% {change.direction}
                  {isDangerousChange && ' - High Impact Change'}
                  {isSignificantChange && !isDangerousChange && ' - Significant Change'}
                </div>
              </div>
            )}
          </div>

          {/* New Value Input */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              New Value ({parameter.unit})
            </label>
            <input
              type="number"
              value={newValue}
              onChange={(e) => setNewValue(e.target.value)}
              min={parameter.minValue}
              max={parameter.maxValue}
              step="any"
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              placeholder={`Enter value between ${parameter.minValue} and ${parameter.maxValue}`}
            />
            <div className="text-xs text-gray-400 mt-1">
              Allowed range: {formatValue(parameter.minValue)} - {formatValue(parameter.maxValue)}
            </div>
          </div>

          {/* Justification */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Change Justification (Required)
            </label>
            <textarea
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white resize-none"
              rows={3}
              placeholder="Explain why this parameter change is necessary..."
              required
            />
          </div>

          {/* Compliance Warning */}
          {parameter.complianceRequired && (
            <div className="mb-4 p-3 bg-yellow-900/20 border border-yellow-500/30 rounded">
              <p className="text-yellow-300 text-sm">
                <span className="font-medium">⚠ Compliance Required</span>
              </p>
              <p className="text-yellow-200 text-sm mt-1">
                This parameter change requires compliance validation and may need additional approval.
              </p>
            </div>
          )}

          {/* High Impact Warning */}
          {isDangerousChange && (
            <div className="mb-4 p-3 bg-red-900/20 border border-red-500/30 rounded">
              <p className="text-red-300 text-sm">
                <span className="font-medium">🚨 High Impact Change</span>
              </p>
              <p className="text-red-200 text-sm mt-1">
                This change represents a {change.percentage.toFixed(1)}% {change.direction} and could significantly impact risk exposure.
              </p>
            </div>
          )}

          <div className="flex justify-end space-x-3">
            <button
              onClick={() => setShowEditModal(false)}
              className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded"
              disabled={updating}
            >
              Cancel
            </button>
            <button
              onClick={handleUpdateSubmit}
              disabled={!justification.trim() || updating || isNaN(parseFloat(newValue))}
              className={`px-4 py-2 rounded font-medium disabled:opacity-50 ${
                isDangerousChange
                  ? 'bg-red-600 hover:bg-red-700 text-white'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
            >
              {updating ? 'Updating...' : 'Update Parameter'}
            </button>
          </div>
        </div>
      </Modal>

      {/* History Modal */}
      <Modal isOpen={showHistory} onClose={() => setShowHistory(false)} size="lg">
        <div className="bg-gray-900 p-6">
          <h2 className="text-xl font-bold text-white mb-4">
            Change History - {parameter.name}
          </h2>
          
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {parameter.history.length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                No change history available
              </div>
            ) : (
              parameter.history.map((historyItem) => (
                <div key={historyItem.id} className="p-3 bg-gray-800 rounded-lg">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center space-x-4">
                      <span className="text-gray-400">
                        {formatValue(historyItem.previousValue)}
                      </span>
                      <span className="text-blue-400">→</span>
                      <span className="text-white font-medium">
                        {formatValue(historyItem.newValue)}
                      </span>
                    </div>
                    <div className="text-xs text-gray-400">
                      {historyItem.modifiedAt.toLocaleString()}
                    </div>
                  </div>
                  <div className="text-sm">
                    <div className="text-gray-400">
                      By: <span className="text-white">{historyItem.modifiedBy}</span>
                    </div>
                    <div className="text-gray-400 mt-1">
                      Reason: <span className="text-white">{historyItem.justification}</span>
                    </div>
                    {historyItem.approvedBy && (
                      <div className="text-gray-400 mt-1">
                        Approved by: <span className="text-green-400">{historyItem.approvedBy}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="flex justify-end mt-4">
            <button
              onClick={() => setShowHistory(false)}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
            >
              Close
            </button>
          </div>
        </div>
      </Modal>
    </>
  )
}

/**
 * Parameter category filter
 */
function CategoryFilter({
  parameters,
  onFilterChange,
  currentFilter
}: {
  parameters: RiskParameters[]
  onFilterChange: (filter: string) => void
  currentFilter: string
}) {
  const categoryCounts = useMemo(() => {
    const counts = { all: parameters.length }
    parameters.forEach(param => {
      counts[param.category] = (counts[param.category] || 0) + 1
    })
    return counts
  }, [parameters])

  const categories = [
    { value: 'all', label: 'All Categories' },
    { value: 'position_sizing', label: 'Position Sizing' },
    { value: 'daily_limits', label: 'Daily Limits' },
    { value: 'drawdown_limits', label: 'Drawdown Limits' },
    { value: 'exposure_limits', label: 'Exposure Limits' },
    { value: 'volatility_controls', label: 'Volatility Controls' },
    { value: 'correlation_limits', label: 'Correlation Limits' },
    { value: 'leverage_controls', label: 'Leverage Controls' }
  ]

  return (
    <div className="flex flex-wrap gap-2">
      {categories.map(category => {
        const count = categoryCounts[category.value] || 0
        if (count === 0 && category.value !== 'all') return null
        
        return (
          <button
            key={category.value}
            onClick={() => onFilterChange(category.value)}
            className={`px-3 py-1 rounded text-sm transition-colors ${
              currentFilter === category.value
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-400 hover:text-white'
            }`}
          >
            {category.label} ({count})
          </button>
        )
      })}
    </div>
  )
}

/**
 * Risk overview summary
 */
function RiskOverview({
  parameters
}: {
  parameters: RiskParameters[]
}) {
  const stats = useMemo(() => {
    const total = parameters.length
    const modified = parameters.filter(p => p.currentValue !== p.defaultValue).length
    const complianceRequired = parameters.filter(p => p.complianceRequired).length
    const recentlyModified = parameters.filter(p => {
      const daysSince = (new Date().getTime() - p.lastModified.getTime()) / (1000 * 60 * 60 * 24)
      return daysSince <= 7
    }).length

    return { total, modified, complianceRequired, recentlyModified }
  }, [parameters])

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <Card>
        <div className="text-center">
          <div className="text-2xl font-bold text-white">{stats.total}</div>
          <div className="text-sm text-gray-400">Total Parameters</div>
        </div>
      </Card>

      <Card>
        <div className="text-center">
          <div className="text-2xl font-bold text-yellow-400">{stats.modified}</div>
          <div className="text-sm text-gray-400">Modified from Default</div>
        </div>
      </Card>

      <Card>
        <div className="text-center">
          <div className="text-2xl font-bold text-orange-400">{stats.complianceRequired}</div>
          <div className="text-sm text-gray-400">Require Compliance</div>
        </div>
      </Card>

      <Card>
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-400">{stats.recentlyModified}</div>
          <div className="text-sm text-gray-400">Modified This Week</div>
        </div>
      </Card>
    </div>
  )
}

/**
 * Main RiskParameterTools component
 */
export function RiskParameterTools({
  riskParameters,
  loading = false,
  error,
  onUpdateParameter,
  onRefresh
}: RiskParameterToolsProps) {
  const [categoryFilter, setCategoryFilter] = useState('all')

  const filteredParameters = useMemo(() => {
    if (categoryFilter === 'all') return riskParameters
    return riskParameters.filter(param => param.category === categoryFilter)
  }, [riskParameters, categoryFilter])

  if (loading && riskParameters.length === 0) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-700 rounded w-48"></div>
          <div className="grid grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-20 bg-gray-700 rounded"></div>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-6">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-64 bg-gray-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <div className="text-center py-8">
          <div className="text-red-400 text-lg mb-2">Error Loading Risk Parameters</div>
          <p className="text-gray-400 mb-4">{error}</p>
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
            >
              Retry
            </button>
          )}
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-white mb-1">Risk Parameter Management</h2>
          <p className="text-sm text-gray-400">Modify risk parameters with compliance validation - Administrator access only</p>
        </div>
        
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={loading}
            className="bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white px-4 py-2 rounded text-sm font-medium"
          >
            {loading ? 'Refreshing...' : 'Refresh Parameters'}
          </button>
        )}
      </div>

      {/* Risk Overview */}
      <RiskOverview parameters={riskParameters} />

      {/* Category Filter */}
      <div>
        <h3 className="text-lg font-semibold text-white mb-3">Filter by Category</h3>
        <CategoryFilter 
          parameters={riskParameters}
          onFilterChange={setCategoryFilter}
          currentFilter={categoryFilter}
        />
      </div>

      {/* Parameters Grid */}
      {filteredParameters.length === 0 ? (
        <Card>
          <div className="text-center py-12">
            <div className="text-gray-400 text-lg mb-2">No Parameters Found</div>
            <p className="text-gray-500">
              {categoryFilter === 'all' 
                ? 'No risk parameters are currently available'
                : `No parameters found in category '${categoryFilter.replace('_', ' ')}'`
              }
            </p>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {filteredParameters.map(parameter => (
            <RiskParameterCard
              key={parameter.id}
              parameter={parameter}
              onUpdate={onUpdateParameter}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default RiskParameterTools