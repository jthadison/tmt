/**
 * Quiet hours configuration component
 * Allows users to set time ranges for suppressing non-critical notifications
 */

'use client'

import { QuietHours } from '@/types/notificationPreferences'

interface QuietHoursConfigProps {
  quietHours: QuietHours
  onChange: (quietHours: QuietHours) => void
}

export function QuietHoursConfig({ quietHours, onChange }: QuietHoursConfigProps) {
  const formatTime = (time: string): string => {
    const [hours, minutes] = time.split(':')
    const hour = parseInt(hours, 10)
    const ampm = hour >= 12 ? 'PM' : 'AM'
    const hour12 = hour % 12 || 12
    return `${hour12}:${minutes} ${ampm}`
  }

  const getPreviewText = (): string => {
    if (!quietHours.enabled) {
      return 'Quiet hours are disabled'
    }

    const startFormatted = formatTime(quietHours.startTime)
    const endFormatted = formatTime(quietHours.endTime)

    if (quietHours.criticalOnly) {
      return `Quiet hours: ${startFormatted} - ${endFormatted} (Critical alerts only)`
    }

    return `Quiet hours: ${startFormatted} - ${endFormatted} (All notifications suppressed)`
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold text-white">Quiet Hours</h3>
        <p className="text-sm text-gray-400 mt-1">
          Suppress notifications during specific hours to avoid disruptions
        </p>
      </div>

      <div className="space-y-4">
        {/* Enable/Disable Toggle */}
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={quietHours.enabled}
            onChange={(e) =>
              onChange({
                ...quietHours,
                enabled: e.target.checked
              })
            }
            className="w-4 h-4 rounded border-gray-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-900"
          />
          <span className="font-medium text-white">Enable Quiet Hours</span>
        </label>

        {/* Time Range Configuration */}
        {quietHours.enabled && (
          <div className="space-y-4 pl-7">
            <div className="grid grid-cols-2 gap-4">
              {/* Start Time */}
              <label className="block">
                <span className="text-sm font-medium text-gray-300">Start Time</span>
                <input
                  type="time"
                  value={quietHours.startTime}
                  onChange={(e) =>
                    onChange({
                      ...quietHours,
                      startTime: e.target.value
                    })
                  }
                  className="mt-1 block w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </label>

              {/* End Time */}
              <label className="block">
                <span className="text-sm font-medium text-gray-300">End Time</span>
                <input
                  type="time"
                  value={quietHours.endTime}
                  onChange={(e) =>
                    onChange({
                      ...quietHours,
                      endTime: e.target.value
                    })
                  }
                  className="mt-1 block w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </label>
            </div>

            {/* Critical Only Mode */}
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={quietHours.criticalOnly}
                onChange={(e) =>
                  onChange({
                    ...quietHours,
                    criticalOnly: e.target.checked
                  })
                }
                className="w-4 h-4 mt-1 rounded border-gray-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-900"
              />
              <div>
                <span className="font-medium text-white">Allow Critical Alerts</span>
                <p className="text-sm text-gray-400 mt-1">
                  Critical priority notifications will still be delivered during quiet hours
                </p>
              </div>
            </label>

            {/* Timezone Display */}
            <div className="p-3 bg-gray-800 border border-gray-700 rounded">
              <p className="text-sm text-gray-300">
                <strong>Timezone:</strong>{' '}
                {Intl.DateTimeFormat().resolvedOptions().timeZone} (
                {new Date().toLocaleString('en-US', { timeZoneName: 'short' }).split(' ').pop()}
                )
              </p>
            </div>
          </div>
        )}

        {/* Preview */}
        <div
          className={`p-4 rounded border ${
            quietHours.enabled
              ? 'bg-blue-500/10 border-blue-500/20'
              : 'bg-gray-800 border-gray-700'
          }`}
        >
          <p
            className={`text-sm font-medium ${
              quietHours.enabled ? 'text-blue-400' : 'text-gray-400'
            }`}
          >
            {getPreviewText()}
          </p>
        </div>
      </div>
    </div>
  )
}
