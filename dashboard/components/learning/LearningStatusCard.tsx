/**
 * Learning Status Card Component
 *
 * Displays autonomous learning system status including cycle state,
 * active tests, pending suggestions, and CI pipeline metrics.
 */

'use client'

import React, { useState } from 'react'
import { useLearningStatus } from '@/hooks/useLearningStatus'
import { useCIPipelineStatus } from '@/hooks/useCIPipelineStatus'
import { useActiveTests } from '@/hooks/useActiveTests'
import { usePendingSuggestions } from '@/hooks/usePendingSuggestions'
import { useEmergencyStopCI } from '@/hooks/useEmergencyStopCI'
import Card from '@/components/ui/Card'

/**
 * Learning Status Card Component
 */
export default function LearningStatusCard() {
  const { data: learningStatus, loading: learningLoading, error: learningError } = useLearningStatus()
  const { data: pipelineStatus, loading: pipelineLoading, error: pipelineError } = useCIPipelineStatus()
  const { data: activeTests, loading: testsLoading } = useActiveTests()
  const { data: pendingSuggestions, loading: suggestionsLoading } = usePendingSuggestions()
  const { triggerEmergencyStop, loading: emergencyStopLoading } = useEmergencyStopCI()

  const [showConfirm, setShowConfirm] = useState(false)

  // Determine overall cycle state indicator
  const getCycleStateIndicator = () => {
    if (learningError || pipelineError) {
      return { color: 'bg-red-500', label: 'ERROR' }
    }

    if (pipelineStatus?.pipelineState === 'RUNNING' && learningStatus?.cycleState === 'COMPLETED') {
      return { color: 'bg-green-500', label: 'ACTIVE' }
    }

    if (learningStatus?.cycleState === 'RUNNING' || testsLoading) {
      return { color: 'bg-yellow-500', label: 'PROCESSING' }
    }

    if (learningStatus?.cycleState === 'FAILED') {
      return { color: 'bg-red-500', label: 'FAILED' }
    }

    return { color: 'bg-gray-500', label: 'IDLE' }
  }

  const handleEmergencyStop = async () => {
    const confirmed = window.confirm('Are you sure you want to trigger emergency stop? This will halt all learning activities.')

    if (confirmed) {
      const success = await triggerEmergencyStop('Manual emergency stop from dashboard', 'operator')
      if (success) {
        alert('Emergency stop triggered successfully')
        setShowConfirm(false)
      } else {
        alert('Failed to trigger emergency stop')
      }
    }
  }

  const stateIndicator = getCycleStateIndicator()

  return (
    <Card className="bg-white shadow-lg">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-800">Autonomous Learning Status</h2>
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${stateIndicator.color}`} />
            <span className="text-sm font-medium text-gray-600">{stateIndicator.label}</span>
          </div>
        </div>

        {/* Loading State */}
        {(learningLoading || pipelineLoading) && (
          <div className="space-y-3">
            <div className="h-4 bg-gray-200 rounded animate-pulse" />
            <div className="h-4 bg-gray-200 rounded animate-pulse w-3/4" />
            <div className="h-4 bg-gray-200 rounded animate-pulse w-1/2" />
          </div>
        )}

        {/* Error State */}
        {(learningError || pipelineError) && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-700 text-sm">
              {learningError || pipelineError}
            </p>
          </div>
        )}

        {/* Main Content */}
        {!learningLoading && !pipelineLoading && !learningError && !pipelineError && (
          <div className="space-y-4">
            {/* Learning Cycle Info */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide">Last Cycle</p>
                <p className="text-sm font-medium text-gray-800">
                  {learningStatus?.lastRun
                    ? new Date(learningStatus.lastRun).toLocaleString()
                    : 'Not run yet'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide">Next Cycle</p>
                <p className="text-sm font-medium text-gray-800">
                  {pipelineStatus?.nextCycleTime
                    ? new Date(pipelineStatus.nextCycleTime).toLocaleString()
                    : 'Calculating...'}
                </p>
              </div>
            </div>

            {/* Metrics */}
            <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200">
              {/* Active Tests */}
              <div className="bg-blue-50 rounded-lg p-3 cursor-pointer hover:bg-blue-100 transition-colors">
                <div className="flex items-center justify-between">
                  <span className="text-2xl">🧪</span>
                  <div className="text-right">
                    <p className="text-2xl font-bold text-blue-700">
                      {activeTests.length}
                    </p>
                    <p className="text-xs text-blue-600">Active Tests</p>
                  </div>
                </div>
              </div>

              {/* Pending Suggestions */}
              <div className="bg-purple-50 rounded-lg p-3 cursor-pointer hover:bg-purple-100 transition-colors">
                <div className="flex items-center justify-between">
                  <span className="text-2xl">💡</span>
                  <div className="text-right">
                    <p className="text-2xl font-bold text-purple-700">
                      {pendingSuggestions.length}
                    </p>
                    <p className="text-xs text-purple-600">Pending Suggestions</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Pipeline Stats */}
            <div className="pt-4 border-t border-gray-200">
              <div className="grid grid-cols-3 gap-2 text-center">
                <div>
                  <p className="text-lg font-semibold text-gray-700">
                    {pipelineStatus?.cycleCount || 0}
                  </p>
                  <p className="text-xs text-gray-500">Cycles</p>
                </div>
                <div>
                  <p className="text-lg font-semibold text-gray-700">
                    {pipelineStatus?.suggestionsGenerated || 0}
                  </p>
                  <p className="text-xs text-gray-500">Suggestions</p>
                </div>
                <div>
                  <p className="text-lg font-semibold text-gray-700">
                    {pipelineStatus?.deploymentsActive || 0}
                  </p>
                  <p className="text-xs text-gray-500">Deployments</p>
                </div>
              </div>
            </div>

            {/* Emergency Stop Button */}
            <div className="pt-4 border-t border-gray-200">
              <button
                onClick={handleEmergencyStop}
                disabled={emergencyStopLoading}
                className="w-full bg-red-600 hover:bg-red-700 disabled:bg-gray-400 text-white font-medium py-2 px-4 rounded-lg transition-colors"
              >
                {emergencyStopLoading ? 'Stopping...' : '🛑 Emergency Stop'}
              </button>
            </div>
          </div>
        )}
      </div>
    </Card>
  )
}
