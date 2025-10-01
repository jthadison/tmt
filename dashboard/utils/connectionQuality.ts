/**
 * Connection Quality Calculation Utility
 * Determines connection quality based on WebSocket status, latency, and data age
 */

import { ConnectionQuality, ConnectionMetrics } from '@/types/health'

/**
 * Connection quality thresholds
 * Configurable constants for easier tuning
 */
export const QUALITY_THRESHOLDS = {
  latency: {
    excellent: 100, // ms
    good: 200,      // ms
    fair: 500       // ms
  },
  dataAge: {
    excellent: 2,   // seconds
    good: 5,        // seconds
    fair: 10,       // seconds
    disconnected: 30 // seconds
  }
} as const

/**
 * Calculate connection quality based on current metrics
 *
 * Quality Levels:
 * - Excellent: WebSocket connected + avg latency <100ms + data <2s old
 * - Good: WebSocket connected + avg latency <200ms + data <5s old
 * - Fair: WebSocket connected + avg latency <500ms + data <10s old
 * - Poor: WebSocket reconnecting OR avg latency >500ms OR data >10s old
 * - Disconnected: WebSocket disconnected + data >30s old
 */
export function calculateConnectionQuality(metrics: ConnectionMetrics): ConnectionQuality {
  const { wsStatus, avgLatency, dataAge } = metrics

  // Disconnected takes priority
  if (wsStatus === 'disconnected' && dataAge > QUALITY_THRESHOLDS.dataAge.disconnected) {
    return 'disconnected'
  }

  // Poor quality conditions
  if (
    wsStatus === 'error' ||
    wsStatus === 'connecting' ||
    wsStatus === 'disconnected' || // Disconnected with recent data is still poor
    avgLatency > QUALITY_THRESHOLDS.latency.fair ||
    dataAge > QUALITY_THRESHOLDS.dataAge.fair
  ) {
    return 'poor'
  }

  // Fair quality conditions
  if (avgLatency > QUALITY_THRESHOLDS.latency.good || dataAge > QUALITY_THRESHOLDS.dataAge.good) {
    return 'fair'
  }

  // Good quality conditions
  if (avgLatency > QUALITY_THRESHOLDS.latency.excellent || dataAge > QUALITY_THRESHOLDS.dataAge.excellent) {
    return 'good'
  }

  // Excellent quality (all metrics optimal)
  return 'excellent'
}

/**
 * Get color classes for a given connection quality
 */
export function getQualityColorClasses(quality: ConnectionQuality) {
  switch (quality) {
    case 'excellent':
      return {
        text: 'text-green-400',
        bg: 'bg-green-500/10',
        border: 'border-green-500/20',
        label: 'Excellent'
      }
    case 'good':
      return {
        text: 'text-lime-400',
        bg: 'bg-lime-500/10',
        border: 'border-lime-500/20',
        label: 'Good'
      }
    case 'fair':
      return {
        text: 'text-yellow-400',
        bg: 'bg-yellow-500/10',
        border: 'border-yellow-500/20',
        label: 'Fair'
      }
    case 'poor':
      return {
        text: 'text-orange-400',
        bg: 'bg-orange-500/10',
        border: 'border-orange-500/20',
        label: 'Poor'
      }
    case 'disconnected':
      return {
        text: 'text-red-400',
        bg: 'bg-red-500/10',
        border: 'border-red-500/20',
        label: 'Disconnected'
      }
  }
}

/**
 * Format data age in human-readable format
 * Handles negative values (clock skew) gracefully
 */
export function formatDataAge(seconds: number): string {
  // Handle negative values (clock skew between client and server)
  if (seconds < 0) return 'just now'

  if (seconds < 1) return 'just now'
  if (seconds < 60) return `${Math.floor(seconds)}s ago`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  return `${Math.floor(seconds / 3600)}h ago`
}
