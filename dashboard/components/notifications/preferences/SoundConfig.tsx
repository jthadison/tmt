/**
 * Sound alert configuration component
 * Manages volume, enable/disable, and per-priority sound selection
 */

'use client'

import { SoundPreferences } from '@/types/notificationPreferences'
import { NotificationPriority, PRIORITY_CONFIG } from '@/types/notifications'

interface SoundConfigProps {
  sounds: SoundPreferences
  onChange: (sounds: SoundPreferences) => void
  onPlayPreview: (priority: NotificationPriority) => void
}

const AVAILABLE_SOUNDS: Record<NotificationPriority, { value: string; label: string }[]> = {
  [NotificationPriority.CRITICAL]: [
    { value: 'critical-beep', label: 'Urgent Beep' },
    { value: 'critical-alarm', label: 'Alarm' },
    { value: 'critical-siren', label: 'Siren' }
  ],
  [NotificationPriority.WARNING]: [
    { value: 'warning-beep', label: 'Medium Beep' },
    { value: 'warning-chime', label: 'Warning Chime' },
    { value: 'warning-ding', label: 'Ding' }
  ],
  [NotificationPriority.SUCCESS]: [
    { value: 'success-chime', label: 'Positive Chime' },
    { value: 'success-ding', label: 'Success Ding' },
    { value: 'success-tada', label: 'Ta-da' }
  ],
  [NotificationPriority.INFO]: [
    { value: 'info-notification', label: 'Soft Notification' },
    { value: 'info-pop', label: 'Pop' },
    { value: 'info-gentle', label: 'Gentle Tone' }
  ]
}

export function SoundConfig({ sounds, onChange, onPlayPreview }: SoundConfigProps) {
  const priorities: NotificationPriority[] = [
    NotificationPriority.CRITICAL,
    NotificationPriority.WARNING,
    NotificationPriority.SUCCESS,
    NotificationPriority.INFO
  ]

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold text-white">Sound Alerts</h3>
        <p className="text-sm text-gray-400 mt-1">
          Configure audio notifications for different priority levels
        </p>
      </div>

      <div className="space-y-4">
        {/* Enable/Disable Toggle */}
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={sounds.enabled}
            onChange={(e) =>
              onChange({
                ...sounds,
                enabled: e.target.checked
              })
            }
            className="w-4 h-4 rounded border-gray-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-900"
          />
          <span className="font-medium text-white">Enable Sound Alerts</span>
        </label>

        {/* Volume Control */}
        {sounds.enabled && (
          <div className="space-y-4 pl-7">
            <div>
              <label className="block">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-300">Volume</span>
                  <span className="text-sm text-gray-400">{sounds.volume}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="5"
                  value={sounds.volume}
                  onChange={(e) =>
                    onChange({
                      ...sounds,
                      volume: parseInt(e.target.value, 10)
                    })
                  }
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                />
              </label>
            </div>

            {/* Per-Priority Sound Selection */}
            <div className="space-y-3">
              <h4 className="text-sm font-medium text-gray-300">Sound per Priority</h4>
              {priorities.map((priority) => (
                <div
                  key={priority}
                  className="p-3 bg-gray-800 border border-gray-700 rounded"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-lg ${PRIORITY_CONFIG[priority].textColor}`}
                        aria-label={priority}
                      >
                        {PRIORITY_CONFIG[priority].icon}
                      </span>
                      <span className="text-sm font-medium text-white capitalize">
                        {priority}
                      </span>
                    </div>
                    <button
                      onClick={() => onPlayPreview(priority)}
                      disabled={!sounds.enabled}
                      className="px-3 py-1 text-xs bg-blue-500 hover:bg-blue-600 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Preview
                    </button>
                  </div>
                  <select
                    value={sounds.perPriority[priority]}
                    onChange={(e) =>
                      onChange({
                        ...sounds,
                        perPriority: {
                          ...sounds.perPriority,
                          [priority]: e.target.value
                        }
                      })
                    }
                    disabled={!sounds.enabled}
                    className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {AVAILABLE_SOUNDS[priority].map((sound) => (
                      <option key={sound.value} value={sound.value}>
                        {sound.label}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded">
        <p className="text-sm text-blue-400">
          <strong>Tip:</strong> Use distinct sounds for different priority levels to quickly
          identify notification importance without looking.
        </p>
      </div>
    </div>
  )
}
