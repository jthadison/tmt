'use client'

import { useState, useEffect } from 'react'
import { DegradationThresholds, DEFAULT_THRESHOLDS } from '@/types/analytics'

interface ThresholdSliderProps {
  label: string
  description: string
  value: number
  onChange: (value: number) => void
  min: number
  max: number
  step: number
  unit?: string
}

function ThresholdSlider({
  label,
  description,
  value,
  onChange,
  min,
  max,
  step,
  unit = ''
}: ThresholdSliderProps) {
  return (
    <div className="threshold-slider">
      <div className="flex items-center justify-between mb-2">
        <label className="text-sm font-medium text-gray-900 dark:text-white">
          {label}
        </label>
        <span className="text-sm font-mono font-semibold text-gray-900 dark:text-white">
          {value}
          {unit}
        </span>
      </div>
      <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">{description}</p>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
        aria-label={label}
      />
      <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
        <span>
          {min}
          {unit}
        </span>
        <span>
          {max}
          {unit}
        </span>
      </div>
    </div>
  )
}

interface ThresholdInputProps {
  label: string
  description: string
  value: number
  onChange: (value: number) => void
  type?: 'number'
  min?: number
  max?: number
}

function ThresholdInput({
  label,
  description,
  value,
  onChange,
  type = 'number',
  min,
  max
}: ThresholdInputProps) {
  return (
    <div className="threshold-input">
      <label className="text-sm font-medium text-gray-900 dark:text-white mb-2 block">
        {label}
      </label>
      <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">{description}</p>
      <input
        type={type}
        value={value}
        onChange={e => onChange(parseInt(e.target.value))}
        min={min}
        max={max}
        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      />
    </div>
  )
}

export function AlertConfigurationPanel() {
  const [thresholds, setThresholds] = useState<DegradationThresholds>(DEFAULT_THRESHOLDS)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load current thresholds on mount
  useEffect(() => {
    const loadThresholds = async () => {
      try {
        const response = await fetch('/api/analytics/degradation-alerts/config')
        if (response.ok) {
          const data = await response.json()
          setThresholds(data)
        }
      } catch (err) {
        console.error('Error loading thresholds:', err)
      }
    }

    loadThresholds()
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    setSaved(false)

    try {
      const response = await fetch('/api/analytics/degradation-alerts/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(thresholds)
      })

      if (!response.ok) throw new Error('Failed to save thresholds')

      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    setThresholds(DEFAULT_THRESHOLDS)
  }

  return (
    <div className="alert-config-panel p-6 bg-white dark:bg-gray-800 rounded-lg shadow-sm">
      <h3 className="text-lg font-semibold mb-6 text-gray-900 dark:text-white">
        Alert Configuration
      </h3>

      <div className="space-y-6">
        <ThresholdSlider
          label="Profit Factor Decline"
          description="Alert when profit factor drops by this percentage"
          value={thresholds.profitFactorDecline}
          onChange={v => setThresholds({ ...thresholds, profitFactorDecline: v })}
          min={5}
          max={30}
          step={1}
          unit="%"
        />

        <ThresholdSlider
          label="Sharpe Ratio Threshold"
          description="Alert when Sharpe ratio falls below this value"
          value={thresholds.sharpeThreshold}
          onChange={v => setThresholds({ ...thresholds, sharpeThreshold: v })}
          min={0}
          max={2}
          step={0.1}
        />

        <ThresholdInput
          label="Days Below Sharpe Threshold"
          description="Number of consecutive days before alerting"
          value={thresholds.sharpeDaysBelow}
          onChange={v => setThresholds({ ...thresholds, sharpeDaysBelow: v })}
          type="number"
          min={1}
          max={7}
        />

        <ThresholdSlider
          label="Overfitting Threshold"
          description="Alert when overfitting score exceeds this value"
          value={thresholds.overfittingThreshold}
          onChange={v => setThresholds({ ...thresholds, overfittingThreshold: v })}
          min={0.3}
          max={1}
          step={0.05}
        />

        <ThresholdSlider
          label="Walk-Forward Stability Threshold"
          description="Alert when stability score falls below this value"
          value={thresholds.walkForwardThreshold}
          onChange={v => setThresholds({ ...thresholds, walkForwardThreshold: v })}
          min={10}
          max={70}
          step={5}
        />

        <ThresholdSlider
          label="Sharpe Drop Percentage"
          description="Alert when 7-day Sharpe drops by this % vs 30-day"
          value={thresholds.sharpeDropPercent}
          onChange={v => setThresholds({ ...thresholds, sharpeDropPercent: v })}
          min={10}
          max={50}
          step={5}
          unit="%"
        />

        <ThresholdSlider
          label="Win Rate Decline"
          description="Alert when win rate drops by this percentage"
          value={thresholds.winRateDecline}
          onChange={v => setThresholds({ ...thresholds, winRateDecline: v })}
          min={5}
          max={30}
          step={1}
          unit="%"
        />
      </div>

      {error && (
        <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg text-sm">
          {error}
        </div>
      )}

      {saved && (
        <div className="mt-4 p-3 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 rounded-lg text-sm">
          Alert thresholds updated successfully
        </div>
      )}

      <div className="mt-6 flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {saving ? 'Saving...' : 'Save Configuration'}
        </button>
        <button
          onClick={handleReset}
          className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-gray-700 dark:text-gray-300"
        >
          Reset to Defaults
        </button>
      </div>
    </div>
  )
}
