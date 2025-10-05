/**
 * Digest notification configuration component
 * Controls batching of low-priority notifications
 */

'use client'

import { DigestPreferences } from '@/types/notificationPreferences'
import { NotificationPriority, PRIORITY_CONFIG } from '@/types/notifications'

interface DigestConfigProps {
  digest: DigestPreferences
  onChange: (digest: DigestPreferences) => void
}

export function DigestConfig({ digest, onChange }: DigestConfigProps) {
  const frequencyOptions = [
    { value: 15, label: '15 minutes' },
    { value: 30, label: '30 minutes' },
    { value: 60, label: '1 hour' }
  ] as const

  const priorityOptions: NotificationPriority[] = [
    NotificationPriority.WARNING,
    NotificationPriority.SUCCESS,
    NotificationPriority.INFO
  ]

  const isPrioritySelected = (priority: NotificationPriority): boolean => {
    return digest.priorities.includes(priority)
  }

  const togglePriority = (priority: NotificationPriority) => {
    const newPriorities = isPrioritySelected(priority)
      ? digest.priorities.filter((p) => p !== priority)
      : [...digest.priorities, priority]

    onChange({
      ...digest,
      priorities: newPriorities
    })
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold text-white">Digest Notifications</h3>
        <p className="text-sm text-gray-400 mt-1">
          Bundle low-priority notifications to reduce interruptions
        </p>
      </div>

      <div className="space-y-4">
        {/* Enable/Disable Toggle */}
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={digest.enabled}
            onChange={(e) =>
              onChange({
                ...digest,
                enabled: e.target.checked
              })
            }
            className="w-4 h-4 rounded border-gray-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-900"
          />
          <span className="font-medium text-white">Enable Digest Mode</span>
        </label>

        {/* Digest Configuration */}
        {digest.enabled && (
          <div className="pl-7 space-y-4">
            {/* Frequency */}
            <label className="block">
              <span className="text-sm font-medium text-gray-300">Digest Frequency</span>
              <select
                value={digest.frequencyMinutes}
                onChange={(e) =>
                  onChange({
                    ...digest,
                    frequencyMinutes: parseInt(e.target.value, 10) as 15 | 30 | 60
                  })
                }
                className="mt-1 block w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {frequencyOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <p className="mt-2 text-xs text-gray-400">
                How often to bundle and deliver digest notifications
              </p>
            </label>

            {/* Priority Selection */}
            <div>
              <span className="text-sm font-medium text-gray-300 block mb-2">
                Priorities to Bundle
              </span>
              <div className="space-y-2">
                {priorityOptions.map((priority) => (
                  <label
                    key={priority}
                    className="flex items-center gap-3 p-2 rounded hover:bg-gray-700/30 cursor-pointer transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={isPrioritySelected(priority)}
                      onChange={() => togglePriority(priority)}
                      className="w-4 h-4 rounded border-gray-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-900"
                    />
                    <span
                      className={`text-lg ${PRIORITY_CONFIG[priority].textColor}`}
                      aria-label={priority}
                    >
                      {PRIORITY_CONFIG[priority].icon}
                    </span>
                    <span className="text-sm text-gray-300 capitalize">{priority}</span>
                  </label>
                ))}
              </div>
              <p className="mt-2 text-xs text-gray-400">
                Selected priorities will be batched and delivered together
              </p>
            </div>

            {/* Preview */}
            <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded">
              <p className="text-sm text-blue-400">
                {digest.priorities.length > 0 ? (
                  <>
                    <strong>Preview:</strong> {digest.priorities.join(', ')} notifications
                    bundled every {digest.frequencyMinutes} minutes
                  </>
                ) : (
                  <>
                    <strong>Note:</strong> Select at least one priority level to enable digest
                    mode
                  </>
                )}
              </p>
            </div>
          </div>
        )}

        {/* Critical Warning */}
        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded">
          <p className="text-sm text-red-400">
            <strong>Important:</strong> Critical priority notifications are never bundled and
            always delivered immediately.
          </p>
        </div>
      </div>
    </div>
  )
}
