'use client'

import React, { useState, useEffect } from 'react'
import Card from '@/components/ui/Card'

interface ForwardTestMetrics {
  walkForwardStability: number
  outOfSampleValidation: number
  overfittingScore: number
  kurtosisExposure: number
  monthsOfData: number
  expectedPnL: number
  confidenceIntervalLower: number
  confidenceIntervalUpper: number
  lastUpdated: Date
}

interface MetricsUpdateRequest {
  walkForwardStability?: number
  outOfSampleValidation?: number
  overfittingScore?: number
  kurtosisExposure?: number
  monthsOfData?: number
}

const ForwardTestMetricsPanel: React.FC = () => {
  const [metrics, setMetrics] = useState<ForwardTestMetrics>({
    walkForwardStability: 34.4,
    outOfSampleValidation: 17.4,
    overfittingScore: 0.634,
    kurtosisExposure: 20.316,
    monthsOfData: 6,
    expectedPnL: 79563,
    confidenceIntervalLower: 45000,
    confidenceIntervalUpper: 115000,
    lastUpdated: new Date()
  })

  const [isUpdating, setIsUpdating] = useState(false)
  const [updateForm, setUpdateForm] = useState<MetricsUpdateRequest>({})
  const [showUpdateForm, setShowUpdateForm] = useState(false)

  const getMetricStatus = (value: number, thresholds: { good: number, ok: number }, invert = false) => {
    const isGood = invert ? value <= thresholds.good : value >= thresholds.good
    const isOk = invert ? value <= thresholds.ok : value >= thresholds.ok

    if (isGood) return { color: 'text-green-400', bg: 'bg-green-500/20', status: 'GOOD' }
    if (isOk) return { color: 'text-yellow-400', bg: 'bg-yellow-500/20', status: 'OK' }
    return { color: 'text-red-400', bg: 'bg-red-500/20', status: 'POOR' }
  }

  const stabilityStatus = getMetricStatus(metrics.walkForwardStability, { good: 70, ok: 50 })
  const validationStatus = getMetricStatus(metrics.outOfSampleValidation, { good: 70, ok: 50 })
  const overfittingStatus = getMetricStatus(metrics.overfittingScore, { good: 0.3, ok: 0.5 }, true)
  const kurtosisStatus = getMetricStatus(metrics.kurtosisExposure, { good: 5, ok: 15 }, true)

  const handleUpdateMetrics = async () => {
    setIsUpdating(true)
    try {
      // In real implementation, this would call the API
      // const response = await fetch('/api/position-sizing/forward-test/update-metrics', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(updateForm)
      // })

      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000))

      // Update metrics with form values
      setMetrics(prev => ({
        ...prev,
        ...updateForm,
        lastUpdated: new Date()
      }))

      setUpdateForm({})
      setShowUpdateForm(false)

    } catch (error) {
      console.error('Failed to update metrics:', error)
    } finally {
      setIsUpdating(false)
    }
  }

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount)
  }

  return (
    <Card
      title={
        <div className="flex items-center justify-between">
          <span>Forward Test Metrics</span>
          <div className="flex space-x-2">
            <button
              onClick={() => setShowUpdateForm(!showUpdateForm)}
              className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded transition-colors"
            >
              {showUpdateForm ? 'Cancel' : 'Update'}
            </button>
            <div className="text-xs text-gray-400">
              Updated: {metrics.lastUpdated.toLocaleTimeString()}
            </div>
          </div>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Key Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {/* Walk-Forward Stability */}
          <div className={`p-4 rounded-lg border ${stabilityStatus.bg} border-gray-600`}>
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm font-medium text-gray-300">Walk-Forward Stability</div>
              <div className={`px-2 py-1 rounded text-xs font-bold ${stabilityStatus.bg} ${stabilityStatus.color}`}>
                {stabilityStatus.status}
              </div>
            </div>
            <div className={`text-2xl font-bold ${stabilityStatus.color}`}>
              {metrics.walkForwardStability}/100
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Target: ≥60 for Phase 2, ≥70 for Phase 3
            </div>
            <div className="mt-2 bg-gray-700 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all ${
                  stabilityStatus.status === 'GOOD' ? 'bg-green-500' :
                  stabilityStatus.status === 'OK' ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${Math.min(100, metrics.walkForwardStability)}%` }}
              ></div>
            </div>
          </div>

          {/* Out-of-Sample Validation */}
          <div className={`p-4 rounded-lg border ${validationStatus.bg} border-gray-600`}>
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm font-medium text-gray-300">Out-of-Sample Validation</div>
              <div className={`px-2 py-1 rounded text-xs font-bold ${validationStatus.bg} ${validationStatus.color}`}>
                {validationStatus.status}
              </div>
            </div>
            <div className={`text-2xl font-bold ${validationStatus.color}`}>
              {metrics.outOfSampleValidation}/100
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Target: ≥70 for reliable deployment
            </div>
            <div className="mt-2 bg-gray-700 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all ${
                  validationStatus.status === 'GOOD' ? 'bg-green-500' :
                  validationStatus.status === 'OK' ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${Math.min(100, metrics.outOfSampleValidation)}%` }}
              ></div>
            </div>
          </div>

          {/* Overfitting Score */}
          <div className={`p-4 rounded-lg border ${overfittingStatus.bg} border-gray-600`}>
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm font-medium text-gray-300">Overfitting Score</div>
              <div className={`px-2 py-1 rounded text-xs font-bold ${overfittingStatus.bg} ${overfittingStatus.color}`}>
                {overfittingStatus.status}
              </div>
            </div>
            <div className={`text-2xl font-bold ${overfittingStatus.color}`}>
              {metrics.overfittingScore.toFixed(3)}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Target: &lt;0.3 (lower is better)
            </div>
            <div className="mt-2 bg-gray-700 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all ${
                  overfittingStatus.status === 'GOOD' ? 'bg-green-500' :
                  overfittingStatus.status === 'OK' ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${Math.min(100, (1 - Math.min(1, metrics.overfittingScore)) * 100)}%` }}
              ></div>
            </div>
          </div>

          {/* Kurtosis Exposure */}
          <div className={`p-4 rounded-lg border ${kurtosisStatus.bg} border-gray-600`}>
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm font-medium text-gray-300">Kurtosis Exposure</div>
              <div className={`px-2 py-1 rounded text-xs font-bold ${kurtosisStatus.bg} ${kurtosisStatus.color}`}>
                {kurtosisStatus.status}
              </div>
            </div>
            <div className={`text-2xl font-bold ${kurtosisStatus.color}`}>
              {metrics.kurtosisExposure.toFixed(1)}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Target: &lt;5 (tail risk measure)
            </div>
            <div className="mt-2 bg-gray-700 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all ${
                  kurtosisStatus.status === 'GOOD' ? 'bg-green-500' :
                  kurtosisStatus.status === 'OK' ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${Math.min(100, (30 - Math.min(30, metrics.kurtosisExposure)) / 30 * 100)}%` }}
              ></div>
            </div>
          </div>
        </div>

        {/* Performance Projection */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-800 p-4 rounded">
            <div className="text-sm text-gray-400 mb-1">Expected 6-Month P&L</div>
            <div className="text-xl font-bold text-green-400">
              {formatCurrency(metrics.expectedPnL)}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Based on {metrics.monthsOfData} months of data
            </div>
          </div>

          <div className="bg-gray-800 p-4 rounded">
            <div className="text-sm text-gray-400 mb-1">Confidence Interval</div>
            <div className="text-sm text-gray-300">
              {formatCurrency(metrics.confidenceIntervalLower)} - {formatCurrency(metrics.confidenceIntervalUpper)}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              95% probability range
            </div>
          </div>

          <div className="bg-gray-800 p-4 rounded">
            <div className="text-sm text-gray-400 mb-1">Deployment Recommendation</div>
            <div className={`text-sm font-bold ${
              metrics.walkForwardStability >= 70 && metrics.outOfSampleValidation >= 70
                ? 'text-green-400'
                : metrics.walkForwardStability >= 50 && metrics.outOfSampleValidation >= 50
                ? 'text-yellow-400'
                : 'text-red-400'
            }`}>
              {metrics.walkForwardStability >= 70 && metrics.outOfSampleValidation >= 70
                ? 'READY FOR PHASE 3+'
                : metrics.walkForwardStability >= 50 && metrics.outOfSampleValidation >= 50
                ? 'LIMITED DEPLOYMENT'
                : 'FURTHER TESTING REQUIRED'
              }
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Current assessment
            </div>
          </div>
        </div>

        {/* Update Form */}
        {showUpdateForm && (
          <div className="bg-gray-800 p-4 rounded-lg border border-blue-500/30">
            <h4 className="text-sm font-medium text-gray-300 mb-4">Update Forward Test Metrics</h4>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Walk-Forward Stability</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value={updateForm.walkForwardStability ?? ''}
                  onChange={(e) => setUpdateForm(prev => ({
                    ...prev,
                    walkForwardStability: parseFloat(e.target.value) || undefined
                  }))}
                  placeholder={metrics.walkForwardStability.toString()}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
                />
              </div>

              <div>
                <label className="block text-xs text-gray-400 mb-1">Out-of-Sample Validation</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value={updateForm.outOfSampleValidation ?? ''}
                  onChange={(e) => setUpdateForm(prev => ({
                    ...prev,
                    outOfSampleValidation: parseFloat(e.target.value) || undefined
                  }))}
                  placeholder={metrics.outOfSampleValidation.toString()}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
                />
              </div>

              <div>
                <label className="block text-xs text-gray-400 mb-1">Overfitting Score</label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.001"
                  value={updateForm.overfittingScore ?? ''}
                  onChange={(e) => setUpdateForm(prev => ({
                    ...prev,
                    overfittingScore: parseFloat(e.target.value) || undefined
                  }))}
                  placeholder={metrics.overfittingScore.toString()}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
                />
              </div>

              <div>
                <label className="block text-xs text-gray-400 mb-1">Kurtosis Exposure</label>
                <input
                  type="number"
                  min="0"
                  max="50"
                  step="0.1"
                  value={updateForm.kurtosisExposure ?? ''}
                  onChange={(e) => setUpdateForm(prev => ({
                    ...prev,
                    kurtosisExposure: parseFloat(e.target.value) || undefined
                  }))}
                  placeholder={metrics.kurtosisExposure.toString()}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
                />
              </div>

              <div>
                <label className="block text-xs text-gray-400 mb-1">Months of Data</label>
                <input
                  type="number"
                  min="1"
                  max="24"
                  value={updateForm.monthsOfData ?? ''}
                  onChange={(e) => setUpdateForm(prev => ({
                    ...prev,
                    monthsOfData: parseInt(e.target.value) || undefined
                  }))}
                  placeholder={metrics.monthsOfData.toString()}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-2 mt-4">
              <button
                onClick={() => setShowUpdateForm(false)}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleUpdateMetrics}
                disabled={isUpdating || Object.keys(updateForm).length === 0}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm rounded transition-colors"
              >
                {isUpdating ? 'Updating...' : 'Update Metrics'}
              </button>
            </div>
          </div>
        )}

        {/* Recommendations */}
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <div className="text-yellow-400 text-lg">⚠️</div>
            <div className="space-y-2">
              <div className="text-sm font-medium text-yellow-400">Current Recommendations</div>
              <div className="space-y-1 text-sm text-gray-300">
                {metrics.walkForwardStability < 60 && (
                  <div>• Improve walk-forward stability to at least 60/100 before Phase 2 deployment</div>
                )}
                {metrics.outOfSampleValidation < 70 && (
                  <div>• Collect additional out-of-sample data to improve validation score</div>
                )}
                {metrics.overfittingScore > 0.5 && (
                  <div>• Reduce overfitting by simplifying parameters or increasing data diversity</div>
                )}
                {metrics.kurtosisExposure > 15 && (
                  <div>• Implement additional tail risk controls for high kurtosis exposure</div>
                )}
                {metrics.monthsOfData < 8 && (
                  <div>• Collect at least 2 more months of trading data for reliable assessment</div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  )
}

export default ForwardTestMetricsPanel