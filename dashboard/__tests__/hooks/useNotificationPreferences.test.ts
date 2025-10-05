/**
 * Tests for useNotificationPreferences hook
 */

import { renderHook, act } from '@testing-library/react'
import { useNotificationPreferences } from '@/hooks/useNotificationPreferences'
import { DEFAULT_PREFERENCES } from '@/types/notificationPreferences'
import { NotificationPriority } from '@/types/notifications'

describe('useNotificationPreferences', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('should load default preferences on first use', () => {
    const { result } = renderHook(() => useNotificationPreferences())
    expect(result.current.preferences).toEqual(DEFAULT_PREFERENCES)
  })

  it('should update delivery method', () => {
    const { result } = renderHook(() => useNotificationPreferences())

    act(() => {
      result.current.updateDeliveryMethod('email', true)
    })

    expect(result.current.preferences.deliveryMethods.email).toBe(true)
  })

  it('should update delivery method config', () => {
    const { result } = renderHook(() => useNotificationPreferences())
    const testEmail = 'test@example.com'

    act(() => {
      result.current.updateDeliveryMethodConfig('email', testEmail)
    })

    expect(result.current.preferences.deliveryMethodConfig.email).toBe(testEmail)
  })

  it('should update priority matrix', () => {
    const { result } = renderHook(() => useNotificationPreferences())

    act(() => {
      result.current.updatePriorityMatrix(
        'email',
        NotificationPriority.WARNING,
        true
      )
    })

    expect(
      result.current.preferences.priorityMatrix.email[NotificationPriority.WARNING]
    ).toBe(true)
  })

  it('should update event toggle', () => {
    const { result } = renderHook(() => useNotificationPreferences())

    act(() => {
      result.current.updateEventToggle('trade_opened', false)
    })

    expect(result.current.preferences.eventToggles.trade_opened).toBe(false)
  })

  it('should reset to defaults', () => {
    const { result } = renderHook(() => useNotificationPreferences())

    // Modify preferences
    act(() => {
      result.current.updateDeliveryMethod('email', true)
      result.current.updateEventToggle('trade_opened', false)
    })

    // Reset
    act(() => {
      result.current.resetDefaults()
    })

    expect(result.current.preferences).toEqual(DEFAULT_PREFERENCES)
  })

  it('should export preferences as JSON', () => {
    const { result } = renderHook(() => useNotificationPreferences())

    const exported = result.current.exportPreferences()
    const parsed = JSON.parse(exported)

    expect(parsed).toEqual(DEFAULT_PREFERENCES)
  })

  it('should import valid preferences', () => {
    const { result } = renderHook(() => useNotificationPreferences())

    const customPreferences = {
      ...DEFAULT_PREFERENCES,
      deliveryMethods: {
        ...DEFAULT_PREFERENCES.deliveryMethods,
        email: true
      }
    }

    let success = false
    act(() => {
      success = result.current.importPreferences(
        JSON.stringify(customPreferences)
      )
    })

    expect(success).toBe(true)
    expect(result.current.preferences.deliveryMethods.email).toBe(true)
  })

  it('should reject invalid preferences', () => {
    const { result } = renderHook(() => useNotificationPreferences())

    const invalidJson = '{ "notAValidPref": true }'
    let success = true
    act(() => {
      success = result.current.importPreferences(invalidJson)
    })

    expect(success).toBe(false)
  })

  it('should validate email configuration', () => {
    const { result } = renderHook(() => useNotificationPreferences())

    act(() => {
      result.current.updateDeliveryMethod('email', true)
      result.current.updateDeliveryMethodConfig('email', 'valid@example.com')
    })

    const validation = result.current.validateConfig('email')
    expect(validation.valid).toBe(true)
  })

  it('should invalidate bad email configuration', () => {
    const { result } = renderHook(() => useNotificationPreferences())

    act(() => {
      result.current.updateDeliveryMethod('email', true)
      result.current.updateDeliveryMethodConfig('email', 'invalid-email')
    })

    const validation = result.current.validateConfig('email')
    expect(validation.valid).toBe(false)
    expect(validation.message).toContain('Invalid email')
  })

  it('should persist preferences to localStorage', () => {
    const { result } = renderHook(() => useNotificationPreferences())

    act(() => {
      result.current.updateDeliveryMethod('email', true)
    })

    const stored = localStorage.getItem('notification_preferences')
    expect(stored).not.toBeNull()

    const parsed = JSON.parse(stored!)
    expect(parsed.deliveryMethods.email).toBe(true)
  })

  it('should load preferences from localStorage', () => {
    const customPreferences = {
      ...DEFAULT_PREFERENCES,
      deliveryMethods: {
        ...DEFAULT_PREFERENCES.deliveryMethods,
        slack: true
      }
    }

    localStorage.setItem(
      'notification_preferences',
      JSON.stringify(customPreferences)
    )

    const { result } = renderHook(() => useNotificationPreferences())
    expect(result.current.preferences.deliveryMethods.slack).toBe(true)
  })

  it('should update quiet hours configuration', () => {
    const { result } = renderHook(() => useNotificationPreferences())

    act(() => {
      result.current.updatePreference('quietHours', {
        enabled: true,
        startTime: '23:00',
        endTime: '08:00',
        criticalOnly: true
      })
    })

    expect(result.current.preferences.quietHours.startTime).toBe('23:00')
    expect(result.current.preferences.quietHours.endTime).toBe('08:00')
  })

  it('should update grouping preferences', () => {
    const { result } = renderHook(() => useNotificationPreferences())

    act(() => {
      result.current.updatePreference('grouping', {
        enabled: false,
        windowMinutes: 60
      })
    })

    expect(result.current.preferences.grouping.enabled).toBe(false)
    expect(result.current.preferences.grouping.windowMinutes).toBe(60)
  })

  it('should update sound preferences', () => {
    const { result } = renderHook(() => useNotificationPreferences())

    act(() => {
      result.current.updatePreference('sounds', {
        ...result.current.preferences.sounds,
        volume: 50
      })
    })

    expect(result.current.preferences.sounds.volume).toBe(50)
  })

  it('should update digest preferences', () => {
    const { result } = renderHook(() => useNotificationPreferences())

    act(() => {
      result.current.updatePreference('digest', {
        enabled: true,
        frequencyMinutes: 60,
        priorities: [NotificationPriority.INFO]
      })
    })

    expect(result.current.preferences.digest.enabled).toBe(true)
    expect(result.current.preferences.digest.frequencyMinutes).toBe(60)
  })
})
