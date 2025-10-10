/**
 * Parameter Evolution Timeline Component (Story 12.2 - Task 9)
 *
 * Displays vertical timeline of parameter changes with color-coded indicators
 */

'use client'

import React, { useState } from 'react'
import { ParameterChange, getParameterChangeIndicator } from '@/types/analytics122'
import { format } from 'date-fns'

interface ParameterEvolutionTimelineProps {
  data: ParameterChange[] | null
  loading: boolean
  error: Error | null
}

/**
 * Get timeline marker color classes
 */
function getMarkerClasses(changedBy: ParameterChange['changed_by']): string {
  const indicator = getParameterChangeIndicator(changedBy)
  switch (indicator.color) {
    case 'blue': return 'bg-blue-500 border-blue-600'
    case 'green': return 'bg-green-500 border-green-600'
    case 'orange': return 'bg-orange-500 border-orange-600'
    case 'red': return 'bg-red-500 border-red-600'
  }
}

/**
 * Get badge color classes
 */
function getBadgeClasses(changedBy: ParameterChange['changed_by']): string {
  const indicator = getParameterChangeIndicator(changedBy)
  switch (indicator.color) {
    case 'blue': return 'bg-blue-100 text-blue-800 border-blue-300'
    case 'green': return 'bg-green-100 text-green-800 border-green-300'
    case 'orange': return 'bg-orange-100 text-orange-800 border-orange-300'
    case 'red': return 'bg-red-100 text-red-800 border-red-300'
  }
}

/**
 * Parameter Evolution Timeline Component
 */
export default function ParameterEvolutionTimeline({
  data,
  loading,
  error
}: ParameterEvolutionTimelineProps) {
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set())

  const toggleExpanded = (index: number) => {
    const newExpanded = new Set(expandedItems)
    if (newExpanded.has(index)) {
      newExpanded.delete(index)
    } else {
      newExpanded.add(index)
    }
    setExpandedItems(newExpanded)
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">
        Parameter Evolution Timeline
      </h2>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
          <p className="text-sm text-red-800">
            <span className="font-semibold">Error:</span> {error.message}
          </p>
        </div>
      )}

      {loading && (
        <div className="space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="flex gap-4 animate-pulse">
              <div className="flex flex-col items-center">
                <div className="w-4 h-4 rounded-full bg-gray-200"></div>
                <div className="w-0.5 h-20 bg-gray-200"></div>
              </div>
              <div className="flex-1 space-y-2">
                <div className="h-4 w-32 bg-gray-200 rounded"></div>
                <div className="h-3 w-full bg-gray-200 rounded"></div>
                <div className="h-3 w-3/4 bg-gray-200 rounded"></div>
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && !error && data && data.length > 0 && (
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-2 top-0 bottom-0 w-0.5 bg-gray-200"></div>

          {/* Timeline items */}
          <div className="space-y-6">
            {data.map((change, index) => {
              const isExpanded = expandedItems.has(index)
              const markerClasses = getMarkerClasses(change.changed_by)
              const badgeClasses = getBadgeClasses(change.changed_by)
              const indicator = getParameterChangeIndicator(change.changed_by)

              return (
                <div key={index} className="relative flex gap-4">
                  {/* Timeline marker */}
                  <div className="relative z-10 flex flex-col items-center">
                    <div
                      className={`w-4 h-4 rounded-full border-2 ${markerClasses}`}
                    ></div>
                  </div>

                  {/* Content */}
                  <div className="flex-1 pb-6">
                    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                      {/* Header */}
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm font-semibold text-gray-900">
                              {change.parameter_mode}
                              {change.session && ` - ${change.session}`}
                            </span>
                            <span
                              className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${badgeClasses}`}
                            >
                              {indicator.label}
                            </span>
                          </div>
                          <div className="text-xs text-gray-500">
                            {format(new Date(change.change_time), 'MMM dd, yyyy HH:mm:ss')}
                          </div>
                        </div>

                        <button
                          onClick={() => toggleExpanded(index)}
                          className="text-gray-400 hover:text-gray-600 text-sm"
                        >
                          {isExpanded ? '▼' : '▶'}
                        </button>
                      </div>

                      {/* Summary */}
                      <div className="grid grid-cols-2 gap-4 mt-3">
                        {change.confidence_threshold !== null && (
                          <div>
                            <div className="text-xs text-gray-600">Confidence Threshold</div>
                            <div className="text-sm font-medium text-gray-900">
                              {change.confidence_threshold.toFixed(1)}%
                            </div>
                          </div>
                        )}
                        {change.min_risk_reward !== null && (
                          <div>
                            <div className="text-xs text-gray-600">Min Risk:Reward</div>
                            <div className="text-sm font-medium text-gray-900">
                              1:{change.min_risk_reward.toFixed(1)}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Expanded details */}
                      {isExpanded && change.reason && (
                        <div className="mt-3 pt-3 border-t border-gray-200">
                          <div className="text-xs text-gray-600 mb-1">Reason for Change:</div>
                          <div className="text-sm text-gray-800">{change.reason}</div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {!loading && !error && (!data || data.length === 0) && (
        <div className="text-center py-8 text-gray-500">
          <p>No parameter changes recorded</p>
          <p className="text-sm mt-2">Parameter evolution will appear here as the system learns</p>
        </div>
      )}

      {/* Legend */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="text-xs font-semibold text-gray-700 mb-2">Change Types:</div>
        <div className="grid grid-cols-2 gap-2">
          {(['system_auto', 'learning_agent', 'manual', 'emergency'] as const).map(type => {
            const indicator = getParameterChangeIndicator(type)
            const badgeClasses = getBadgeClasses(type)
            return (
              <div key={type} className="flex items-center gap-2">
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${badgeClasses}`}
                >
                  {indicator.label}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
