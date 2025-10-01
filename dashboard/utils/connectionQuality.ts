/**
 * Connection Quality Calculation Utility
 * Determines connection quality based on WebSocket status, latency, and data age
 */

import { ConnectionQuality, ConnectionMetrics } from '@/types/health'

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
  if (wsStatus === 'disconnected' && dataAge > 30) {
    return 'disconnected'
  }

  // Poor quality conditions
  if (
    wsStatus === 'error' ||
    wsStatus === 'connecting' ||
    wsStatus === 'disconnected' || // Disconnected with recent data is still poor
    avgLatency > 500 ||
    dataAge > 10
  ) {
    return 'poor'
  }

  // Fair quality conditions
  if (avgLatency > 200 || dataAge > 5) {
    return 'fair'
  }

  // Good quality conditions
  if (avgLatency > 100 || dataAge > 2) {
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
 */
export function formatDataAge(seconds: number): string {
  if (seconds < 1) return 'just now'
  if (seconds < 60) return `${Math.floor(seconds)}s ago`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  return `${Math.floor(seconds / 3600)}h ago`
}
