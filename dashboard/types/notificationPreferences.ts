/**
 * Notification preferences types for customizable notification delivery
 * Supports multiple delivery channels, priority filtering, and quiet hours
 */

import { NotificationPriority } from './notifications'

export type DeliveryMethod = 'inApp' | 'browserPush' | 'email' | 'slack' | 'sms'

export type EventType =
  // Trade Events
  | 'trade_opened'
  | 'trade_closed_profit'
  | 'trade_closed_loss'
  | 'trade_rejected'
  // System Events
  | 'system_error'
  | 'system_recovered'
  | 'agent_started'
  | 'agent_stopped'
  // Agent Events
  | 'agent_healthy'
  | 'agent_degraded'
  | 'agent_failed'
  | 'performance_alert'
  // Circuit Breaker Events
  | 'breaker_triggered'
  | 'threshold_warning'
  | 'breaker_reset'

export interface DeliveryMethods {
  inApp: boolean
  browserPush: boolean
  email: boolean
  slack: boolean
  sms: boolean
}

export interface DeliveryMethodConfig {
  email?: string
  slackWebhook?: string
  phone?: string
}

export type PriorityMatrix = Record<DeliveryMethod, Record<NotificationPriority, boolean>>

export interface QuietHours {
  enabled: boolean
  startTime: string // "HH:mm" format
  endTime: string // "HH:mm" format
  criticalOnly: boolean
}

export interface GroupingPreferences {
  enabled: boolean
  windowMinutes: 15 | 30 | 60
}

export type EventToggles = Record<EventType, boolean>

export interface SoundPreferences {
  enabled: boolean
  volume: number // 0-100
  perPriority: Record<NotificationPriority, string> // sound file paths or names
}

export interface DigestPreferences {
  enabled: boolean
  frequencyMinutes: 15 | 30 | 60
  priorities: NotificationPriority[]
}

export interface NotificationPreferences {
  deliveryMethods: DeliveryMethods
  deliveryMethodConfig: DeliveryMethodConfig
  priorityMatrix: PriorityMatrix
  quietHours: QuietHours
  grouping: GroupingPreferences
  eventToggles: EventToggles
  sounds: SoundPreferences
  digest: DigestPreferences
}

/**
 * Default notification preferences with recommended settings
 */
export const DEFAULT_PREFERENCES: NotificationPreferences = {
  deliveryMethods: {
    inApp: true,
    browserPush: false,
    email: false,
    slack: false,
    sms: false
  },
  deliveryMethodConfig: {},
  priorityMatrix: {
    inApp: {
      [NotificationPriority.CRITICAL]: true,
      [NotificationPriority.WARNING]: true,
      [NotificationPriority.SUCCESS]: true,
      [NotificationPriority.INFO]: true
    },
    browserPush: {
      [NotificationPriority.CRITICAL]: true,
      [NotificationPriority.WARNING]: true,
      [NotificationPriority.SUCCESS]: false,
      [NotificationPriority.INFO]: false
    },
    email: {
      [NotificationPriority.CRITICAL]: true,
      [NotificationPriority.WARNING]: false,
      [NotificationPriority.SUCCESS]: false,
      [NotificationPriority.INFO]: false
    },
    slack: {
      [NotificationPriority.CRITICAL]: true,
      [NotificationPriority.WARNING]: false,
      [NotificationPriority.SUCCESS]: false,
      [NotificationPriority.INFO]: false
    },
    sms: {
      [NotificationPriority.CRITICAL]: true,
      [NotificationPriority.WARNING]: false,
      [NotificationPriority.SUCCESS]: false,
      [NotificationPriority.INFO]: false
    }
  },
  quietHours: {
    enabled: true,
    startTime: '22:00',
    endTime: '07:00',
    criticalOnly: true
  },
  grouping: {
    enabled: true,
    windowMinutes: 30
  },
  eventToggles: {
    // Trade Events - All enabled by default
    trade_opened: true,
    trade_closed_profit: true,
    trade_closed_loss: true,
    trade_rejected: true,
    // System Events - All enabled by default
    system_error: true,
    system_recovered: true,
    agent_started: true,
    agent_stopped: true,
    // Agent Events - All enabled by default
    agent_healthy: true,
    agent_degraded: true,
    agent_failed: true,
    performance_alert: true,
    // Circuit Breaker Events - All enabled by default
    breaker_triggered: true,
    threshold_warning: true,
    breaker_reset: true
  },
  sounds: {
    enabled: true,
    volume: 70,
    perPriority: {
      [NotificationPriority.CRITICAL]: 'critical-beep',
      [NotificationPriority.WARNING]: 'warning-beep',
      [NotificationPriority.SUCCESS]: 'success-chime',
      [NotificationPriority.INFO]: 'info-notification'
    }
  },
  digest: {
    enabled: false,
    frequencyMinutes: 30,
    priorities: [NotificationPriority.INFO, NotificationPriority.SUCCESS]
  }
}

/**
 * Event type categories for organizational display
 */
export const EVENT_CATEGORIES = {
  'Trade Events': [
    'trade_opened',
    'trade_closed_profit',
    'trade_closed_loss',
    'trade_rejected'
  ] as EventType[],
  'System Events': [
    'system_error',
    'system_recovered',
    'agent_started',
    'agent_stopped'
  ] as EventType[],
  'Agent Events': [
    'agent_healthy',
    'agent_degraded',
    'agent_failed',
    'performance_alert'
  ] as EventType[],
  'Circuit Breaker Events': [
    'breaker_triggered',
    'threshold_warning',
    'breaker_reset'
  ] as EventType[]
} as const

/**
 * Event type display names
 */
export const EVENT_TYPE_LABELS: Record<EventType, string> = {
  trade_opened: 'Trade Opened',
  trade_closed_profit: 'Trade Closed Profitably',
  trade_closed_loss: 'Trade Closed at Loss',
  trade_rejected: 'Trade Rejected',
  system_error: 'System Error',
  system_recovered: 'System Recovered',
  agent_started: 'Agent Started',
  agent_stopped: 'Agent Stopped',
  agent_healthy: 'Agent Healthy',
  agent_degraded: 'Agent Degraded',
  agent_failed: 'Agent Failed',
  performance_alert: 'Performance Alert',
  breaker_triggered: 'Breaker Triggered',
  threshold_warning: 'Threshold Warning',
  breaker_reset: 'Breaker Reset'
}

/**
 * Delivery method display names
 */
export const DELIVERY_METHOD_LABELS: Record<DeliveryMethod, string> = {
  inApp: 'In-App',
  browserPush: 'Browser Push',
  email: 'Email',
  slack: 'Slack',
  sms: 'SMS'
}
