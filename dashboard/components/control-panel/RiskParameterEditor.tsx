'use client'

import { useState, useMemo } from 'react'
import { RiskParameter, RiskParameterUpdate, RiskParameterCategory } from '@/types/systemControl'

/**
 * Props for RiskParameterEditor component
 */
interface RiskParameterEditorProps {
  /** Array of risk parameters */
  riskParameters: RiskParameter[]
  /** Callback when parameter update is requested */
  onParameterUpdate: (update: RiskParameterUpdate) => void
  /** Loading state indicator */
  loading?: boolean
}

/**
 * Risk parameter adjustment interface with validation and change tracking
 * Provides real-time parameter updates with rollback functionality
 */
export function RiskParameterEditor({
  riskParameters,
  onParameterUpdate,
  loading = false
}: RiskParameterEditorProps) {
  const [selectedCategory, setSelectedCategory] = useState<RiskParameterCategory | 'all'>('all')
  const [editingParameter, setEditingParameter] = useState<string | null>(null)
  const [newValue, setNewValue] = useState<string>('')
  const [changeReason, setChangeReason] = useState('')
  const [applyImmediately, setApplyImmediately] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [showChangeHistory, setShowChangeHistory] = useState(false)

  // Filter parameters based on category and search
  const filteredParameters = useMemo(() => {
    let filtered = riskParameters

    if (selectedCategory !== 'all') {
      filtered = filtered.filter(param => param.category === selectedCategory)
    }

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(param =>
        param.name.toLowerCase().includes(query) ||
        param.description.toLowerCase().includes(query)
      )
    }

    return filtered.sort((a, b) => a.name.localeCompare(b.name))
  }, [riskParameters, selectedCategory, searchQuery])

  const categoryOptions: { value: RiskParameterCategory | 'all'; label: string }[] = [
    { value: 'all', label: 'All Categories' },
    { value: 'position_sizing', label: 'Position Sizing' },
    { value: 'drawdown', label: 'Drawdown Limits' },
    { value: 'exposure', label: 'Market Exposure' },
    { value: 'time_limits', label: 'Time Limits' }
  ]

  const getCategoryColor = (category: RiskParameterCategory): string => {
    switch (category) {
      case 'position_sizing':
        return 'text-blue-400 bg-blue-900/20'
      case 'drawdown':
        return 'text-red-400 bg-red-900/20'
      case 'exposure':
        return 'text-yellow-400 bg-yellow-900/20'
      case 'time_limits':
        return 'text-green-400 bg-green-900/20'
      default:
        return 'text-gray-400 bg-gray-900/20'
    }
  }

  const formatValue = (param: RiskParameter): string => {
    if (typeof param.value === 'boolean') {
      return param.value ? 'Enabled' : 'Disabled'
    }
    
    if (typeof param.value === 'number') {
      return param.unit ? `${param.value} ${param.unit}` : param.value.toString()
    }
    
    return param.value.toString()
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

  const validateValue = (param: RiskParameter, value: string): string | null => {
    if (typeof param.value === 'boolean') {
      const boolValue = value.toLowerCase()
      if (!['true', 'false', 'enabled', 'disabled', 'yes', 'no'].includes(boolValue)) {
        return 'Value must be true/false or enabled/disabled'
      }
      return null
    }

    if (typeof param.value === 'number') {
      const numValue = parseFloat(value)
      if (isNaN(numValue)) {
        return 'Value must be a valid number'
      }
      if (param.minValue !== undefined && numValue < param.minValue) {
        return `Value must be at least ${param.minValue}`
      }
      if (param.maxValue !== undefined && numValue > param.maxValue) {
        return `Value must be at most ${param.maxValue}`
      }
      return null
    }

    if (param.validationPattern) {
      const regex = new RegExp(param.validationPattern)
      if (!regex.test(value)) {
        return 'Value format is invalid'
      }
    }

    return null
  }

  const parseValue = (param: RiskParameter, value: string): number | string | boolean => {
    if (typeof param.value === 'boolean') {
      const boolValue = value.toLowerCase()
      return ['true', 'enabled', 'yes'].includes(boolValue)
    }

    if (typeof param.value === 'number') {
      return parseFloat(value)
    }

    return value
  }

  const handleEditParameter = (param: RiskParameter) => {
    setEditingParameter(param.id)
    setNewValue(param.value.toString())
    setChangeReason('')
    setApplyImmediately(!param.requiresRestart)
  }

  const handleSaveParameter = () => {
    if (!editingParameter || !changeReason.trim()) return

    const param = riskParameters.find(p => p.id === editingParameter)
    if (!param) return

    const validationError = validateValue(param, newValue)
    if (validationError) {
      alert(validationError)
      return
    }

    const parsedValue = parseValue(param, newValue)

    const update: RiskParameterUpdate = {
      parameterId: editingParameter,
      newValue: parsedValue,
      changeReason: changeReason.trim(),
      applyImmediately
    }

    onParameterUpdate(update)
    setEditingParameter(null)
    setNewValue('')
    setChangeReason('')
  }

  const handleCancelEdit = () => {
    setEditingParameter(null)
    setNewValue('')
    setChangeReason('')
  }

  const getParametersRequiringRestart = (): RiskParameter[] => {
    return riskParameters.filter(param => param.requiresRestart)
  }

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-700 rounded w-48"></div>
          <div className="grid grid-cols-1 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-16 bg-gray-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 mb-6">
        <h3 className="text-lg font-semibold text-white">Risk Parameter Editor</h3>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowChangeHistory(!showChangeHistory)}
            className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-2 rounded text-sm transition-colors"
          >
            📊 Change History
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div>
          <label className="block text-gray-300 text-sm mb-2">Category Filter</label>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value as RiskParameterCategory | 'all')}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
          >
            {categoryOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        
        <div>
          <label className="block text-gray-300 text-sm mb-2">Search Parameters</label>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by name or description..."
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
          />
        </div>
      </div>

      {/* Warning for parameters requiring restart */}
      {getParametersRequiringRestart().length > 0 && (
        <div className="mb-6 p-4 bg-yellow-900/20 border border-yellow-500/30 rounded">
          <div className="text-yellow-400 font-medium text-sm">⚠️ System Restart Required</div>
          <div className="text-yellow-200 text-sm mt-1">
            {getParametersRequiringRestart().length} parameter(s) require system restart to take effect:
            {' '}{getParametersRequiringRestart().map(p => p.name).join(', ')}
          </div>
        </div>
      )}

      {/* Parameters List */}
      <div className="space-y-4">
        {filteredParameters.map((param) => (
          <div
            key={param.id}
            className={`
              bg-gray-750 rounded-lg p-4 border transition-colors
              ${editingParameter === param.id 
                ? 'border-blue-500' 
                : 'border-gray-700 hover:border-gray-600'
              }
              ${param.requiresRestart ? 'border-l-4 border-l-yellow-500' : ''}
            `}
          >
            <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h4 className="font-medium text-white">{param.name}</h4>
                  <span className={`px-2 py-1 rounded text-xs ${getCategoryColor(param.category)}`}>
                    {param.category.replace('_', ' ').toUpperCase()}
                  </span>
                  {param.requiresRestart && (
                    <span className="px-2 py-1 rounded text-xs bg-yellow-900/30 text-yellow-400 border border-yellow-500/30">
                      RESTART REQUIRED
                    </span>
                  )}
                </div>
                
                <div className="text-sm text-gray-300 mb-2">
                  {param.description}
                </div>

                {editingParameter === param.id ? (
                  <div className="space-y-3 mt-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-gray-300 text-sm mb-1">New Value</label>
                        <input
                          type={typeof param.value === 'number' ? 'number' : 'text'}
                          value={newValue}
                          onChange={(e) => setNewValue(e.target.value)}
                          min={param.minValue}
                          max={param.maxValue}
                          className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                          placeholder={param.unit ? `Value in ${param.unit}` : 'Enter value'}
                        />
                        {param.minValue !== undefined && param.maxValue !== undefined && (
                          <div className="text-xs text-gray-500 mt-1">
                            Range: {param.minValue} - {param.maxValue} {param.unit || ''}
                          </div>
                        )}
                      </div>
                      
                      <div>
                        <label className="block text-gray-300 text-sm mb-1">Change Reason</label>
                        <input
                          type="text"
                          value={changeReason}
                          onChange={(e) => setChangeReason(e.target.value)}
                          placeholder="Why is this change needed?"
                          className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                        />
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id={`apply-${param.id}`}
                        checked={applyImmediately}
                        onChange={(e) => setApplyImmediately(e.target.checked)}
                        disabled={param.requiresRestart}
                        className="rounded border-gray-600 bg-gray-700 text-blue-600"
                      />
                      <label htmlFor={`apply-${param.id}`} className="text-gray-300 text-sm">
                        Apply immediately {param.requiresRestart && '(disabled - restart required)'}
                      </label>
                    </div>
                    
                    <div className="flex gap-3">
                      <button
                        onClick={handleSaveParameter}
                        disabled={!newValue.trim() || !changeReason.trim()}
                        className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white px-4 py-2 rounded text-sm transition-colors"
                      >
                        Save Changes
                      </button>
                      <button
                        onClick={handleCancelEdit}
                        className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded text-sm transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div>
                        <div className="text-sm text-gray-400">Current Value</div>
                        <div className="font-medium text-white text-lg">
                          {formatValue(param)}
                        </div>
                      </div>
                      
                      <div className="text-xs text-gray-500">
                        <div>Modified: {formatTimeAgo(param.lastModified)}</div>
                        <div>By: {param.modifiedBy}</div>
                      </div>
                    </div>
                    
                    <button
                      onClick={() => handleEditParameter(param)}
                      disabled={editingParameter !== null}
                      className="bg-gray-700 hover:bg-gray-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white px-3 py-2 rounded text-sm transition-colors"
                    >
                      Edit
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {filteredParameters.length === 0 && (
        <div className="text-center py-12">
          <div className="text-gray-400 text-lg">No Parameters Found</div>
          <p className="text-gray-500 mt-2">
            {searchQuery ? 'Try adjusting your search criteria' : 'No parameters available for the selected category'}
          </p>
        </div>
      )}

      {/* Change History */}
      {showChangeHistory && (
        <div className="mt-6 pt-6 border-t border-gray-700">
          <h4 className="text-white font-medium mb-4">Recent Parameter Changes</h4>
          <div className="space-y-3">
            {riskParameters
              .sort((a, b) => b.lastModified.getTime() - a.lastModified.getTime())
              .slice(0, 10)
              .map((param) => (
                <div key={`history-${param.id}`} className="bg-gray-750 rounded p-3">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="font-medium text-white">{param.name}</div>
                      <div className="text-sm text-gray-300">
                        Current: {formatValue(param)}
                      </div>
                    </div>
                    <div className="text-right text-xs text-gray-500">
                      <div>{formatTimeAgo(param.lastModified)}</div>
                      <div>By: {param.modifiedBy}</div>
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Summary Statistics */}
      <div className="mt-6 pt-6 border-t border-gray-700">
        <h4 className="text-white font-medium mb-3">Parameter Summary</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <div className="text-gray-400">Total Parameters</div>
            <div className="text-white font-medium">{riskParameters.length}</div>
          </div>
          <div>
            <div className="text-gray-400">Require Restart</div>
            <div className="text-yellow-400 font-medium">
              {getParametersRequiringRestart().length}
            </div>
          </div>
          <div>
            <div className="text-gray-400">Categories</div>
            <div className="text-white font-medium">
              {new Set(riskParameters.map(p => p.category)).size}
            </div>
          </div>
          <div>
            <div className="text-gray-400">Recently Modified</div>
            <div className="text-blue-400 font-medium">
              {riskParameters.filter(p => 
                Date.now() - p.lastModified.getTime() < 24 * 60 * 60 * 1000
              ).length}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}