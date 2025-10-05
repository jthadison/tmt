/**
 * Hook for managing notification preferences
 * Handles localStorage persistence, validation, and preference updates
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  NotificationPreferences,
  DEFAULT_PREFERENCES,
  DeliveryMethod,
  EventType
} from '@/types/notificationPreferences'
import { NotificationPriority } from '@/types/notifications'

const STORAGE_KEY = 'notification_preferences'

/**
 * Validates email format
 */
function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

/**
 * Validates phone number (basic validation)
 */
function isValidPhone(phone: string): boolean {
  const phoneRegex = /^\+?[\d\s\-()]{10,}$/
  return phoneRegex.test(phone)
}

/**
 * Validates Slack webhook URL
 */
function isValidSlackWebhook(url: string): boolean {
  return url.startsWith('https://hooks.slack.com/services/')
}

/**
 * Validates notification preferences object
 */
function validatePreferences(prefs: Partial<NotificationPreferences>): boolean {
  try {
    if (!prefs || typeof prefs !== 'object') return false

    if (prefs.deliveryMethodConfig) {
      const { email, phone, slackWebhook } = prefs.deliveryMethodConfig
      if (email && !isValidEmail(email)) return false
      if (phone && !isValidPhone(phone)) return false
      if (slackWebhook && !isValidSlackWebhook(slackWebhook)) return false
    }

    if (prefs.quietHours) {
      const timeRegex = /^([0-1][0-9]|2[0-3]):[0-5][0-9]$/
      if (!timeRegex.test(prefs.quietHours.startTime)) return false
      if (!timeRegex.test(prefs.quietHours.endTime)) return false
    }

    if (prefs.grouping) {
      const validWindows = [15, 30, 60]
      if (!validWindows.includes(prefs.grouping.windowMinutes)) return false
    }

    if (prefs.digest) {
      const validFrequencies = [15, 30, 60]
      if (!validFrequencies.includes(prefs.digest.frequencyMinutes)) return false
    }

    if (prefs.sounds) {
      if (prefs.sounds.volume < 0 || prefs.sounds.volume > 100) return false
    }

    return true
  } catch (error) {
    console.error('Preference validation error:', error)
    return false
  }
}

/**
 * Loads preferences from localStorage (SSR-safe)
 */
function loadPreferences(): NotificationPreferences {
  try {
    if (typeof window === 'undefined' || typeof localStorage === 'undefined') {
      return DEFAULT_PREFERENCES
    }

    const stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) return DEFAULT_PREFERENCES

    const parsed = JSON.parse(stored) as Partial<NotificationPreferences>
    if (!validatePreferences(parsed)) {
      console.warn('Invalid stored preferences, using defaults')
      return DEFAULT_PREFERENCES
    }

    return {
      ...DEFAULT_PREFERENCES,
      ...parsed,
      deliveryMethods: {
        ...DEFAULT_PREFERENCES.deliveryMethods,
        ...parsed.deliveryMethods
      },
      deliveryMethodConfig: {
        ...DEFAULT_PREFERENCES.deliveryMethodConfig,
        ...parsed.deliveryMethodConfig
      },
      priorityMatrix: {
        ...DEFAULT_PREFERENCES.priorityMatrix,
        ...parsed.priorityMatrix
      },
      quietHours: {
        ...DEFAULT_PREFERENCES.quietHours,
        ...parsed.quietHours
      },
      grouping: {
        ...DEFAULT_PREFERENCES.grouping,
        ...parsed.grouping
      },
      eventToggles: {
        ...DEFAULT_PREFERENCES.eventToggles,
        ...parsed.eventToggles
      },
      sounds: {
        ...DEFAULT_PREFERENCES.sounds,
        ...parsed.sounds,
        perPriority: {
          ...DEFAULT_PREFERENCES.sounds.perPriority,
          ...parsed.sounds?.perPriority
        }
      },
      digest: {
        ...DEFAULT_PREFERENCES.digest,
        ...parsed.digest
      }
    }
  } catch (error) {
    console.error('Error loading preferences:', error)
    return DEFAULT_PREFERENCES
  }
}

/**
 * Saves preferences to localStorage (SSR-safe)
 */
function savePreferences(prefs: NotificationPreferences): void {
  try {
    if (typeof window === 'undefined' || typeof localStorage === 'undefined') {
      return
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs))
  } catch (error) {
    console.error('Error saving preferences:', error)
  }
}

export interface UseNotificationPreferencesResult {
  preferences: NotificationPreferences
  updatePreference: <K extends keyof NotificationPreferences>(
    key: K,
    value: NotificationPreferences[K]
  ) => void
  updateDeliveryMethod: (method: DeliveryMethod, enabled: boolean) => void
  updateDeliveryMethodConfig: (
    method: 'email' | 'slack' | 'sms',
    value: string
  ) => void
  updatePriorityMatrix: (
    method: DeliveryMethod,
    priority: NotificationPriority,
    enabled: boolean
  ) => void
  updateEventToggle: (event: EventType, enabled: boolean) => void
  resetDefaults: () => void
  exportPreferences: () => string
  importPreferences: (json: string) => boolean
  validateConfig: (method: DeliveryMethod) => { valid: boolean; message?: string }
}

export function useNotificationPreferences(): UseNotificationPreferencesResult {
  const [preferences, setPreferences] = useState<NotificationPreferences>(DEFAULT_PREFERENCES)
  const [isClient, setIsClient] = useState(false)

  useEffect(() => {
    setIsClient(true)
    setPreferences(loadPreferences())
  }, [])

  useEffect(() => {
    if (isClient) {
      savePreferences(preferences)
    }
  }, [preferences, isClient])

  const updatePreference = useCallback(
    <K extends keyof NotificationPreferences>(
      key: K,
      value: NotificationPreferences[K]
    ) => {
      setPreferences((prev) => ({
        ...prev,
        [key]: value
      }))
    },
    []
  )

  const updateDeliveryMethod = useCallback((method: DeliveryMethod, enabled: boolean) => {
    setPreferences((prev) => ({
      ...prev,
      deliveryMethods: {
        ...prev.deliveryMethods,
        [method]: enabled
      }
    }))
  }, [])

  const updateDeliveryMethodConfig = useCallback(
    (method: 'email' | 'slack' | 'sms', value: string) => {
      setPreferences((prev) => ({
        ...prev,
        deliveryMethodConfig: {
          ...prev.deliveryMethodConfig,
          [method === 'email' ? 'email' : method === 'slack' ? 'slackWebhook' : 'phone']:
            value
        }
      }))
    },
    []
  )

  const updatePriorityMatrix = useCallback(
    (method: DeliveryMethod, priority: NotificationPriority, enabled: boolean) => {
      setPreferences((prev) => ({
        ...prev,
        priorityMatrix: {
          ...prev.priorityMatrix,
          [method]: {
            ...prev.priorityMatrix[method],
            [priority]: enabled
          }
        }
      }))
    },
    []
  )

  const updateEventToggle = useCallback((event: EventType, enabled: boolean) => {
    setPreferences((prev) => ({
      ...prev,
      eventToggles: {
        ...prev.eventToggles,
        [event]: enabled
      }
    }))
  }, [])

  const resetDefaults = useCallback(() => {
    setPreferences(DEFAULT_PREFERENCES)
  }, [])

  const exportPreferences = useCallback(() => {
    return JSON.stringify(preferences, null, 2)
  }, [preferences])

  const importPreferences = useCallback((json: string): boolean => {
    try {
      const imported = JSON.parse(json) as Partial<NotificationPreferences>
      if (!validatePreferences(imported)) {
        return false
      }

      const merged: NotificationPreferences = {
        ...DEFAULT_PREFERENCES,
        ...imported,
        deliveryMethods: {
          ...DEFAULT_PREFERENCES.deliveryMethods,
          ...imported.deliveryMethods
        },
        deliveryMethodConfig: {
          ...DEFAULT_PREFERENCES.deliveryMethodConfig,
          ...imported.deliveryMethodConfig
        },
        priorityMatrix: {
          ...DEFAULT_PREFERENCES.priorityMatrix,
          ...imported.priorityMatrix
        },
        quietHours: {
          ...DEFAULT_PREFERENCES.quietHours,
          ...imported.quietHours
        },
        grouping: {
          ...DEFAULT_PREFERENCES.grouping,
          ...imported.grouping
        },
        eventToggles: {
          ...DEFAULT_PREFERENCES.eventToggles,
          ...imported.eventToggles
        },
        sounds: {
          ...DEFAULT_PREFERENCES.sounds,
          ...imported.sounds,
          perPriority: {
            ...DEFAULT_PREFERENCES.sounds.perPriority,
            ...imported.sounds?.perPriority
          }
        },
        digest: {
          ...DEFAULT_PREFERENCES.digest,
          ...imported.digest
        }
      }

      setPreferences(merged)
      return true
    } catch (error) {
      console.error('Error importing preferences:', error)
      return false
    }
  }, [])

  const validateConfig = useCallback(
    (method: DeliveryMethod): { valid: boolean; message?: string } => {
      if (!preferences.deliveryMethods[method]) {
        return { valid: true }
      }

      const config = preferences.deliveryMethodConfig

      switch (method) {
        case 'email':
          if (!config.email) {
            return { valid: false, message: 'Email address required' }
          }
          if (!isValidEmail(config.email)) {
            return { valid: false, message: 'Invalid email address' }
          }
          return { valid: true }

        case 'slack':
          if (!config.slackWebhook) {
            return { valid: false, message: 'Slack webhook URL required' }
          }
          if (!isValidSlackWebhook(config.slackWebhook)) {
            return { valid: false, message: 'Invalid Slack webhook URL' }
          }
          return { valid: true }

        case 'sms':
          if (!config.phone) {
            return { valid: false, message: 'Phone number required' }
          }
          if (!isValidPhone(config.phone)) {
            return { valid: false, message: 'Invalid phone number' }
          }
          return { valid: true }

        case 'browserPush':
          if (typeof Notification === 'undefined') {
            return { valid: false, message: 'Browser notifications not supported' }
          }
          if (Notification.permission === 'denied') {
            return { valid: false, message: 'Browser notification permission denied' }
          }
          if (Notification.permission !== 'granted') {
            return { valid: false, message: 'Browser notification permission required' }
          }
          return { valid: true }

        default:
          return { valid: true }
      }
    },
    [preferences]
  )

  return {
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
  }
}
