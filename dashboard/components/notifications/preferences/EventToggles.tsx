/**
 * Event-specific toggles component
 * Organized by category with expand/collapse functionality
 */

'use client'

import { useState } from 'react'
import {
  EventToggles as EventTogglesType,
  EventType,
  EVENT_CATEGORIES,
  EVENT_TYPE_LABELS
} from '@/types/notificationPreferences'

interface EventTogglesProps {
  eventToggles: EventTogglesType
  onToggle: (event: EventType, enabled: boolean) => void
}

export function EventToggles({ eventToggles, onToggle }: EventTogglesProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(Object.keys(EVENT_CATEGORIES))
  )

  const toggleCategory = (category: string) => {
    const newExpanded = new Set(expandedCategories)
    if (newExpanded.has(category)) {
      newExpanded.delete(category)
    } else {
      newExpanded.add(category)
    }
    setExpandedCategories(newExpanded)
  }

  const toggleAllInCategory = (category: string, enabled: boolean) => {
    const events = EVENT_CATEGORIES[category as keyof typeof EVENT_CATEGORIES]
    events.forEach((event) => onToggle(event, enabled))
  }

  const getCategoryStatus = (category: string): {
    enabled: number
    total: number
    allEnabled: boolean
  } => {
    const events = EVENT_CATEGORIES[category as keyof typeof EVENT_CATEGORIES]
    const enabled = events.filter((event) => eventToggles[event]).length
    const total = events.length
    return {
      enabled,
      total,
      allEnabled: enabled === total
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold text-white">Event-Specific Filters</h3>
        <p className="text-sm text-gray-400 mt-1">
          Control which event types trigger notifications
        </p>
      </div>

      <div className="space-y-3">
        {Object.entries(EVENT_CATEGORIES).map(([category, events]) => {
          const status = getCategoryStatus(category)
          const isExpanded = expandedCategories.has(category)

          return (
            <div
              key={category}
              className="border border-gray-700 rounded-lg bg-gray-800/50 overflow-hidden"
            >
              {/* Category Header */}
              <div className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3 flex-1">
                  <button
                    onClick={() => toggleCategory(category)}
                    className="text-gray-400 hover:text-white transition-colors"
                    aria-label={`${isExpanded ? 'Collapse' : 'Expand'} ${category}`}
                  >
                    {isExpanded ? '▼' : '▶'}
                  </button>
                  <span className="font-medium text-white">{category}</span>
                  <span className="text-sm text-gray-400">
                    ({status.enabled}/{status.total})
                  </span>
                </div>
                <button
                  onClick={() => toggleAllInCategory(category, !status.allEnabled)}
                  className={`px-3 py-1 text-xs rounded transition-colors ${
                    status.allEnabled
                      ? 'bg-green-500/10 text-green-500 hover:bg-green-500/20'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  {status.allEnabled ? 'Disable All' : 'Enable All'}
                </button>
              </div>

              {/* Event Toggles */}
              {isExpanded && (
                <div className="px-4 pb-4 border-t border-gray-700">
                  <div className="pt-4 space-y-2">
                    {events.map((event) => (
                      <label
                        key={event}
                        className="flex items-center gap-3 p-2 rounded hover:bg-gray-700/30 cursor-pointer transition-colors"
                      >
                        <input
                          type="checkbox"
                          checked={eventToggles[event]}
                          onChange={(e) => onToggle(event, e.target.checked)}
                          className="w-4 h-4 rounded border-gray-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-900"
                        />
                        <span className="text-sm text-gray-300">
                          {EVENT_TYPE_LABELS[event]}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      <div className="p-3 bg-yellow-500/10 border border-yellow-500/20 rounded">
        <p className="text-sm text-yellow-400">
          <strong>Note:</strong> Disabled events will not generate any notifications, regardless
          of other settings.
        </p>
      </div>
    </div>
  )
}
