'use client'

import { useState } from 'react'
import { DateRange, DateRangePreset } from '@/types/analytics'

/**
 * Props for DateRangePicker component
 */
interface DateRangePickerProps {
  /** Current date range value */
  value: DateRange
  /** Callback when date range changes */
  onChange: (dateRange: DateRange) => void
  /** Maximum allowed date range in days */
  maxRange?: number
  /** Minimum allowed date range in days */
  minRange?: number
  /** Disabled state */
  disabled?: boolean
}

/**
 * Custom date range picker with preset options
 * Provides intuitive date selection for analytics filtering
 */
export function DateRangePicker({
  value,
  onChange,
  maxRange = 730, // 2 years
  minRange = 1,
  disabled = false
}: DateRangePickerProps) {
  const [showCustom, setShowCustom] = useState(!value.isPreset)
  const [tempStart, setTempStart] = useState(value.start.toISOString().slice(0, 10))
  const [tempEnd, setTempEnd] = useState(value.end.toISOString().slice(0, 10))

  // Preset date range options
  const presets: Array<{
    id: DateRangePreset
    label: string
    description: string
    getValue: () => DateRange
  }> = [
    {
      id: 'last_7_days',
      label: 'Last 7 days',
      description: 'Past week',
      getValue: () => ({
        start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
        end: new Date(),
        label: 'Last 7 days',
        isPreset: true
      })
    },
    {
      id: 'last_30_days',
      label: 'Last 30 days',
      description: 'Past month',
      getValue: () => ({
        start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
        end: new Date(),
        label: 'Last 30 days',
        isPreset: true
      })
    },
    {
      id: 'last_90_days',
      label: 'Last 90 days',
      description: 'Past quarter',
      getValue: () => ({
        start: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000),
        end: new Date(),
        label: 'Last 90 days',
        isPreset: true
      })
    },
    {
      id: 'last_6_months',
      label: 'Last 6 months',
      description: 'Past 180 days',
      getValue: () => ({
        start: new Date(Date.now() - 180 * 24 * 60 * 60 * 1000),
        end: new Date(),
        label: 'Last 6 months',
        isPreset: true
      })
    },
    {
      id: 'last_year',
      label: 'Last year',
      description: 'Past 365 days',
      getValue: () => ({
        start: new Date(Date.now() - 365 * 24 * 60 * 60 * 1000),
        end: new Date(),
        label: 'Last year',
        isPreset: true
      })
    },
    {
      id: 'year_to_date',
      label: 'Year to date',
      description: 'From Jan 1st',
      getValue: () => {
        const now = new Date()
        const startOfYear = new Date(now.getFullYear(), 0, 1)
        return {
          start: startOfYear,
          end: now,
          label: 'Year to date',
          isPreset: true
        }
      }
    },
    {
      id: 'all_time',
      label: 'All time',
      description: 'All available data',
      getValue: () => ({
        start: new Date('2020-01-01'), // Trading system start date
        end: new Date(),
        label: 'All time',
        isPreset: true
      })
    }
  ]

  // Get current preset if value matches
  const getCurrentPreset = (): DateRangePreset | 'custom' => {
    if (!value.isPreset) return 'custom'
    
    const preset = presets.find(p => p.label === value.label)
    return preset?.id || 'custom'
  }

  // Handle preset selection
  const handlePresetChange = (presetId: DateRangePreset | 'custom') => {
    if (presetId === 'custom') {
      setShowCustom(true)
      return
    }

    const preset = presets.find(p => p.id === presetId)
    if (preset) {
      const newRange = preset.getValue()
      onChange(newRange)
      setShowCustom(false)
    }
  }

  // Validate date range
  const validateDateRange = (start: Date, end: Date): string | null => {
    if (start >= end) {
      return 'Start date must be before end date'
    }

    const diffDays = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24))
    
    if (diffDays < minRange) {
      return `Date range must be at least ${minRange} day${minRange > 1 ? 's' : ''}`
    }

    if (diffDays > maxRange) {
      return `Date range cannot exceed ${maxRange} days`
    }

    if (end > new Date()) {
      return 'End date cannot be in the future'
    }

    return null
  }

  // Handle custom date range application
  const handleApplyCustom = () => {
    const startDate = new Date(tempStart)
    const endDate = new Date(tempEnd)
    
    const error = validateDateRange(startDate, endDate)
    if (error) {
      alert(error)
      return
    }

    const newRange: DateRange = {
      start: startDate,
      end: endDate,
      label: `${startDate.toLocaleDateString()} - ${endDate.toLocaleDateString()}`,
      isPreset: false
    }

    onChange(newRange)
    setShowCustom(false)
  }

  // Format date for display
  const formatDateDisplay = (date: Date): string => {
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    })
  }

  // Calculate range duration
  const getRangeDuration = (): string => {
    const diffMs = value.end.getTime() - value.start.getTime()
    const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24))
    
    if (diffDays === 1) return '1 day'
    if (diffDays < 7) return `${diffDays} days`
    if (diffDays < 30) return `${Math.ceil(diffDays / 7)} weeks`
    if (diffDays < 365) return `${Math.ceil(diffDays / 30)} months`
    return `${Math.ceil(diffDays / 365)} years`
  }

  return (
    <div>
      <label className="block text-gray-300 text-sm mb-2">Date Range</label>
      
      {/* Current Selection Display */}
      <div className="bg-gray-750 rounded p-3 mb-3">
        <div className="flex justify-between items-center">
          <div>
            <div className="text-white font-medium">{value.label}</div>
            <div className="text-gray-400 text-sm">
              {formatDateDisplay(value.start)} - {formatDateDisplay(value.end)}
            </div>
          </div>
          <div className="text-gray-400 text-sm">
            {getRangeDuration()}
          </div>
        </div>
      </div>

      {/* Preset Options */}
      <div className="space-y-2 mb-4">
        <div className="text-gray-300 text-sm font-medium">Quick Select</div>
        <div className="grid grid-cols-2 gap-2">
          {presets.map((preset) => (
            <button
              key={preset.id}
              onClick={() => handlePresetChange(preset.id)}
              disabled={disabled}
              className={`
                text-left px-3 py-2 rounded text-sm transition-colors
                ${getCurrentPreset() === preset.id
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }
                disabled:opacity-50 disabled:cursor-not-allowed
              `}
            >
              <div className="font-medium">{preset.label}</div>
              <div className="text-xs opacity-75">{preset.description}</div>
            </button>
          ))}
          
          <button
            onClick={() => handlePresetChange('custom')}
            disabled={disabled}
            className={`
              text-left px-3 py-2 rounded text-sm transition-colors
              ${getCurrentPreset() === 'custom'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }
              disabled:opacity-50 disabled:cursor-not-allowed
            `}
          >
            <div className="font-medium">Custom Range</div>
            <div className="text-xs opacity-75">Pick specific dates</div>
          </button>
        </div>
      </div>

      {/* Custom Date Selection */}
      {showCustom && (
        <div className="bg-gray-750 rounded p-4 space-y-4">
          <div className="text-gray-300 font-medium">Custom Date Range</div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-gray-400 text-sm mb-1">Start Date</label>
              <input
                type="date"
                value={tempStart}
                onChange={(e) => setTempStart(e.target.value)}
                disabled={disabled}
                max={new Date().toISOString().slice(0, 10)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white disabled:opacity-50"
              />
            </div>
            
            <div>
              <label className="block text-gray-400 text-sm mb-1">End Date</label>
              <input
                type="date"
                value={tempEnd}
                onChange={(e) => setTempEnd(e.target.value)}
                disabled={disabled}
                max={new Date().toISOString().slice(0, 10)}
                min={tempStart}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white disabled:opacity-50"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3">
            <button
              onClick={() => setShowCustom(false)}
              disabled={disabled}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleApplyCustom}
              disabled={disabled}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50"
            >
              Apply Range
            </button>
          </div>
        </div>
      )}

      {/* Range Limits Info */}
      <div className="text-xs text-gray-500 mt-2">
        Range limits: {minRange} day minimum, {maxRange} day maximum
      </div>
    </div>
  )
}