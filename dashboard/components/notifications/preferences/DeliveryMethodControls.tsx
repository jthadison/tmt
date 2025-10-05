/**
 * Delivery method controls for notification preferences
 * Manages toggles and configuration for each delivery channel
 */

'use client'

import { useState } from 'react'
import {
  DeliveryMethod,
  DELIVERY_METHOD_LABELS,
  DeliveryMethods,
  DeliveryMethodConfig
} from '@/types/notificationPreferences'

interface DeliveryMethodControlsProps {
  deliveryMethods: DeliveryMethods
  deliveryMethodConfig: DeliveryMethodConfig
  onToggle: (method: DeliveryMethod, enabled: boolean) => void
  onConfigUpdate: (method: 'email' | 'slack' | 'sms', value: string) => void
  onRequestBrowserPermission: () => void
  browserPermissionStatus: 'granted' | 'denied' | 'default'
  validateConfig: (method: DeliveryMethod) => { valid: boolean; message?: string }
}

export function DeliveryMethodControls({
  deliveryMethods,
  deliveryMethodConfig,
  onToggle,
  onConfigUpdate,
  onRequestBrowserPermission,
  browserPermissionStatus,
  validateConfig
}: DeliveryMethodControlsProps) {
  const [expandedMethod, setExpandedMethod] = useState<DeliveryMethod | null>(null)

  const getStatusBadge = (method: DeliveryMethod) => {
    if (!deliveryMethods[method]) {
      return (
        <span className="px-2 py-1 text-xs rounded bg-gray-500/10 text-gray-500">
          Disabled
        </span>
      )
    }

    const validation = validateConfig(method)
    if (!validation.valid) {
      return (
        <span className="px-2 py-1 text-xs rounded bg-red-500/10 text-red-500">
          {validation.message || 'Configuration Required'}
        </span>
      )
    }

    return (
      <span className="px-2 py-1 text-xs rounded bg-green-500/10 text-green-500">
        Enabled
      </span>
    )
  }

  const renderConfig = (method: DeliveryMethod) => {
    if (method === 'inApp') {
      return (
        <p className="text-sm text-gray-500">
          In-app notifications are always enabled and cannot be disabled.
        </p>
      )
    }

    if (method === 'browserPush') {
      return (
        <div className="space-y-2">
          <p className="text-sm text-gray-500">
            Enable browser push notifications to receive alerts even when the dashboard is not
            open.
          </p>
          {browserPermissionStatus === 'denied' && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded">
              <p className="text-sm text-red-500">
                Browser notification permission was denied. Please enable it in your browser
                settings.
              </p>
            </div>
          )}
          {browserPermissionStatus === 'default' && deliveryMethods.browserPush && (
            <button
              onClick={onRequestBrowserPermission}
              className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded transition-colors"
            >
              Request Permission
            </button>
          )}
          {browserPermissionStatus === 'granted' && (
            <div className="p-3 bg-green-500/10 border border-green-500/20 rounded">
              <p className="text-sm text-green-500">
                ✓ Browser notification permission granted
              </p>
            </div>
          )}
        </div>
      )
    }

    if (method === 'email') {
      return (
        <div className="space-y-2">
          <label className="block">
            <span className="text-sm font-medium text-gray-300">Email Address</span>
            <input
              type="email"
              value={deliveryMethodConfig.email || ''}
              onChange={(e) => onConfigUpdate('email', e.target.value)}
              placeholder="your.email@example.com"
              className="mt-1 block w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </label>
          <p className="text-xs text-gray-500">
            Critical notifications will be sent to this email address.
          </p>
        </div>
      )
    }

    if (method === 'slack') {
      return (
        <div className="space-y-2">
          <label className="block">
            <span className="text-sm font-medium text-gray-300">Slack Webhook URL</span>
            <input
              type="url"
              value={deliveryMethodConfig.slackWebhook || ''}
              onChange={(e) => onConfigUpdate('slack', e.target.value)}
              placeholder="https://hooks.slack.com/services/..."
              className="mt-1 block w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </label>
          <p className="text-xs text-gray-500">
            Get your Slack webhook URL from{' '}
            <a
              href="https://api.slack.com/messaging/webhooks"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 hover:text-blue-300 underline"
            >
              Slack Incoming Webhooks
            </a>
          </p>
        </div>
      )
    }

    if (method === 'sms') {
      return (
        <div className="space-y-2">
          <label className="block">
            <span className="text-sm font-medium text-gray-300">Phone Number</span>
            <input
              type="tel"
              value={deliveryMethodConfig.phone || ''}
              onChange={(e) => onConfigUpdate('sms', e.target.value)}
              placeholder="+1234567890"
              className="mt-1 block w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </label>
          <p className="text-xs text-gray-500">
            SMS notifications require Twilio integration (contact administrator).
          </p>
        </div>
      )
    }

    return null
  }

  const methods: DeliveryMethod[] = ['inApp', 'browserPush', 'email', 'slack', 'sms']

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-white">Delivery Methods</h3>
      <div className="space-y-3">
        {methods.map((method) => (
          <div
            key={method}
            className="border border-gray-700 rounded-lg bg-gray-800/50 overflow-hidden"
          >
            <div className="p-4 flex items-center justify-between">
              <div className="flex items-center gap-3 flex-1">
                <label className="flex items-center gap-3 cursor-pointer flex-1">
                  <input
                    type="checkbox"
                    checked={deliveryMethods[method]}
                    onChange={(e) => onToggle(method, e.target.checked)}
                    disabled={method === 'inApp'}
                    className="w-4 h-4 rounded border-gray-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                  <span className="font-medium text-white">
                    {DELIVERY_METHOD_LABELS[method]}
                  </span>
                </label>
                {getStatusBadge(method)}
              </div>
              {method !== 'inApp' && (
                <button
                  onClick={() =>
                    setExpandedMethod(expandedMethod === method ? null : method)
                  }
                  className="ml-3 text-gray-400 hover:text-white transition-colors"
                  aria-label={`${expandedMethod === method ? 'Collapse' : 'Expand'} ${DELIVERY_METHOD_LABELS[method]} settings`}
                >
                  {expandedMethod === method ? '▲' : '▼'}
                </button>
              )}
            </div>

            {(expandedMethod === method || method === 'inApp') && (
              <div className="px-4 pb-4 border-t border-gray-700">
                <div className="pt-4">{renderConfig(method)}</div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
