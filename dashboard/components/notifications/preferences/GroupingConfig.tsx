/**
 * Notification grouping configuration component
 * Controls smart grouping and grouping window settings
 */

'use client'

import { GroupingPreferences } from '@/types/notificationPreferences'

interface GroupingConfigProps {
  grouping: GroupingPreferences
  onChange: (grouping: GroupingPreferences) => void
}

export function GroupingConfig({ grouping, onChange }: GroupingConfigProps) {
  const windowOptions = [
    { value: 15, label: '15 minutes' },
    { value: 30, label: '30 minutes' },
    { value: 60, label: '60 minutes' }
  ] as const

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold text-white">Smart Grouping</h3>
        <p className="text-sm text-gray-400 mt-1">
          Group similar notifications together to reduce clutter
        </p>
      </div>

      <div className="space-y-4">
        {/* Enable/Disable Toggle */}
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={grouping.enabled}
            onChange={(e) =>
              onChange({
                ...grouping,
                enabled: e.target.checked
              })
            }
            className="w-4 h-4 rounded border-gray-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-900"
          />
          <span className="font-medium text-white">Enable Smart Grouping</span>
        </label>

        {/* Grouping Window */}
        {grouping.enabled && (
          <div className="pl-7 space-y-4">
            <label className="block">
              <span className="text-sm font-medium text-gray-300">Grouping Window</span>
              <select
                value={grouping.windowMinutes}
                onChange={(e) =>
                  onChange({
                    ...grouping,
                    windowMinutes: parseInt(e.target.value, 10) as 15 | 30 | 60
                  })
                }
                className="mt-1 block w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {windowOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <p className="mt-2 text-xs text-gray-400">
                Notifications of the same type occurring within this time window will be grouped
                together
              </p>
            </label>

            {/* Critical Never Grouped Info */}
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded">
              <p className="text-sm text-red-400">
                <strong>Important:</strong> Critical priority notifications are never grouped and
                always appear individually.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
