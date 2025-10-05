/**
 * Notification Preferences Page
 * Comprehensive settings for notification delivery, filtering, and behavior
 */

'use client'

import { useState, useCallback } from 'react'
import { useNotificationPreferences } from '@/hooks/useNotificationPreferences'
import { DeliveryMethodControls } from '@/components/notifications/preferences/DeliveryMethodControls'
import { PriorityMatrix } from '@/components/notifications/preferences/PriorityMatrix'
import { QuietHoursConfig } from '@/components/notifications/preferences/QuietHoursConfig'
import { EventToggles } from '@/components/notifications/preferences/EventToggles'
import { SoundConfig } from '@/components/notifications/preferences/SoundConfig'
import { GroupingConfig } from '@/components/notifications/preferences/GroupingConfig'
import { DigestConfig } from '@/components/notifications/preferences/DigestConfig'
import { useToasts } from '@/hooks/useToasts'
import { NotificationPriority } from '@/types/notifications'
import { DeliveryMethod } from '@/types/notificationPreferences'

export default function NotificationPreferencesPage() {
  const {
    preferences,
    updatePreference,
    updateDeliveryMethod,
    updateDeliveryMethodConfig,
    updatePriorityMatrix,
    updateEventToggle,
    resetDefaults,
    exportPreferences,
    importPreferences,
    validateConfig
  } = useNotificationPreferences()

  const { showToast } = useToasts()
  const [browserPermission, setBrowserPermission] = useState<NotificationPermission>(
    typeof Notification !== 'undefined' ? Notification.permission : 'default'
  )

  // Request browser notification permission
  const handleRequestBrowserPermission = useCallback(async () => {
    if (typeof Notification === 'undefined') {
      showToast({ timestamp: new Date(),
        title: 'Not Supported',
        message: 'Browser notifications are not supported in this browser',
        priority: NotificationPriority.WARNING
      })
      return
    }

    try {
      const permission = await Notification.requestPermission()
      setBrowserPermission(permission)

      if (permission === 'granted') {
        showToast({ timestamp: new Date(),
          title: 'Permission Granted',
          message: 'Browser notifications have been enabled',
          priority: NotificationPriority.SUCCESS
        })
      } else if (permission === 'denied') {
        showToast({ timestamp: new Date(),
          title: 'Permission Denied',
          message: 'Browser notification permission was denied',
          priority: NotificationPriority.WARNING
        })
      }
    } catch (error) {
      console.error('Error requesting notification permission:', error)
      showToast({ timestamp: new Date(),
        title: 'Error',
        message: 'Failed to request notification permission',
        priority: NotificationPriority.WARNING
      })
    }
  }, [showToast])

  // Play sound preview
  const handlePlaySoundPreview = useCallback(
    (priority: NotificationPriority) => {
      if (!preferences.sounds.enabled) return

      // Create a simple beep sound using Web Audio API
      const audioContext = new (window.AudioContext ||
        (window as any).webkitAudioContext)()
      const oscillator = audioContext.createOscillator()
      const gainNode = audioContext.createGain()

      oscillator.connect(gainNode)
      gainNode.connect(audioContext.destination)

      // Different frequencies for different priorities
      const frequencies = {
        [NotificationPriority.CRITICAL]: 880,
        [NotificationPriority.WARNING]: 659,
        [NotificationPriority.SUCCESS]: 523,
        [NotificationPriority.INFO]: 440
      }

      oscillator.frequency.value = frequencies[priority]
      oscillator.type = 'sine'

      // Apply volume
      gainNode.gain.value = preferences.sounds.volume / 100

      oscillator.start()
      oscillator.stop(audioContext.currentTime + 0.2)

      showToast({ timestamp: new Date(),
        title: 'Sound Preview',
        message: `Playing ${priority} notification sound`,
        priority: NotificationPriority.INFO
      })
    },
    [preferences.sounds.enabled, preferences.sounds.volume, showToast]
  )

  // Reset to defaults
  const handleResetDefaults = useCallback(() => {
    if (
      confirm(
        'Are you sure you want to reset all notification preferences to default values?'
      )
    ) {
      resetDefaults()
      showToast({ timestamp: new Date(),
        title: 'Preferences Reset',
        message: 'All notification preferences have been reset to defaults',
        priority: NotificationPriority.SUCCESS
      })
    }
  }, [resetDefaults, showToast])

  // Export preferences
  const handleExport = useCallback(() => {
    try {
      const json = exportPreferences()
      const blob = new Blob([json], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `notification_preferences_${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      showToast({ timestamp: new Date(),
        title: 'Preferences Exported',
        message: 'Notification preferences have been exported successfully',
        priority: NotificationPriority.SUCCESS
      })
    } catch (error) {
      console.error('Error exporting preferences:', error)
      showToast({ timestamp: new Date(),
        title: 'Export Failed',
        message: 'Failed to export notification preferences',
        priority: NotificationPriority.WARNING
      })
    }
  }, [exportPreferences, showToast])

  // Import preferences
  const handleImport = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0]
      if (!file) return

      const reader = new FileReader()
      reader.onload = (e) => {
        try {
          const json = e.target?.result as string
          const success = importPreferences(json)

          if (success) {
            showToast({ timestamp: new Date(),
              title: 'Preferences Imported',
              message: 'Notification preferences have been imported successfully',
              priority: NotificationPriority.SUCCESS
            })
          } else {
            showToast({ timestamp: new Date(),
              title: 'Import Failed',
              message: 'Invalid preferences file format',
              priority: NotificationPriority.WARNING
            })
          }
        } catch (error) {
          console.error('Error importing preferences:', error)
          showToast({ timestamp: new Date(),
            title: 'Import Failed',
            message: 'Failed to import notification preferences',
            priority: NotificationPriority.WARNING
          })
        }
      }
      reader.readAsText(file)

      // Reset input value to allow re-importing the same file
      event.target.value = ''
    },
    [importPreferences, showToast]
  )

  // Test notification
  const handleTestNotification = useCallback(
    (method: DeliveryMethod) => {
      const validation = validateConfig(method)
      if (!validation.valid) {
        showToast({ timestamp: new Date(),
          title: 'Configuration Required',
          message: validation.message || 'Please configure this delivery method first',
          priority: NotificationPriority.WARNING
        })
        return
      }

      // For now, just show a toast for in-app and browser push
      // Email/Slack/SMS would require backend integration
      if (method === 'inApp') {
        showToast({ timestamp: new Date(),
          title: 'Test Notification',
          message: 'This is a test notification from Trading Dashboard',
          priority: NotificationPriority.INFO
        })
      } else if (method === 'browserPush') {
        if (browserPermission === 'granted') {
          new Notification('Test Notification', {
            body: 'This is a test notification from Trading Dashboard',
            icon: '/favicon.ico'
          })
          showToast({ timestamp: new Date(),
            title: 'Browser Push Sent',
            message: 'Check your system notifications',
            priority: NotificationPriority.SUCCESS
          })
        }
      } else {
        showToast({ timestamp: new Date(),
          title: 'Feature Not Implemented',
          message: `${method} test notifications require backend integration`,
          priority: NotificationPriority.INFO
        })
      }
    },
    [validateConfig, showToast, browserPermission]
  )

  return (
    <div className="min-h-screen bg-gray-900 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Notification Preferences</h1>
          <p className="text-gray-400">
            Customize how and when you receive notifications from the trading dashboard
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 mb-8">
          <button
            onClick={handleResetDefaults}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
          >
            Reset to Defaults
          </button>
          <button
            onClick={handleExport}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
          >
            Export Preferences
          </button>
          <label className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded transition-colors cursor-pointer">
            Import Preferences
            <input
              type="file"
              accept=".json"
              onChange={handleImport}
              className="hidden"
            />
          </label>
        </div>

        {/* Preferences Sections */}
        <div className="space-y-8">
          {/* Delivery Methods */}
          <section className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <DeliveryMethodControls
              deliveryMethods={preferences.deliveryMethods}
              deliveryMethodConfig={preferences.deliveryMethodConfig}
              onToggle={updateDeliveryMethod}
              onConfigUpdate={updateDeliveryMethodConfig}
              onRequestBrowserPermission={handleRequestBrowserPermission}
              browserPermissionStatus={browserPermission}
              validateConfig={validateConfig}
            />
            <div className="mt-4 pt-4 border-t border-gray-700">
              <h4 className="text-sm font-medium text-gray-300 mb-2">
                Test Delivery Methods
              </h4>
              <div className="flex gap-2">
                {(['inApp', 'browserPush', 'email', 'slack', 'sms'] as DeliveryMethod[]).map(
                  (method) => (
                    <button
                      key={method}
                      onClick={() => handleTestNotification(method)}
                      disabled={!preferences.deliveryMethods[method]}
                      className="px-3 py-1 text-xs bg-blue-500 hover:bg-blue-600 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Test {method}
                    </button>
                  )
                )}
              </div>
            </div>
          </section>

          {/* Priority Matrix */}
          <section className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <PriorityMatrix
              priorityMatrix={preferences.priorityMatrix}
              onToggle={updatePriorityMatrix}
            />
          </section>

          {/* Quiet Hours */}
          <section className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <QuietHoursConfig
              quietHours={preferences.quietHours}
              onChange={(quietHours) => updatePreference('quietHours', quietHours)}
            />
          </section>

          {/* Grouping */}
          <section className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <GroupingConfig
              grouping={preferences.grouping}
              onChange={(grouping) => updatePreference('grouping', grouping)}
            />
          </section>

          {/* Digest */}
          <section className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <DigestConfig
              digest={preferences.digest}
              onChange={(digest) => updatePreference('digest', digest)}
            />
          </section>

          {/* Event Toggles */}
          <section className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <EventToggles
              eventToggles={preferences.eventToggles}
              onToggle={updateEventToggle}
            />
          </section>

          {/* Sound Configuration */}
          <section className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <SoundConfig
              sounds={preferences.sounds}
              onChange={(sounds) => updatePreference('sounds', sounds)}
              onPlayPreview={handlePlaySoundPreview}
            />
          </section>
        </div>

        {/* Footer Info */}
        <div className="mt-8 p-4 bg-gray-800 rounded-lg border border-gray-700">
          <p className="text-sm text-gray-400 text-center">
            All preferences are automatically saved to your browser's local storage
          </p>
        </div>
      </div>
    </div>
  )
}
