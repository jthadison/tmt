/**
 * ConnectionQualityIndicator Component
 * Displays connection quality in footer with tooltip
 */

'use client'

import React, { useState } from 'react'
import { CheckCircle, AlertTriangle, XCircle, WifiOff, Wifi } from 'lucide-react'
import { useConnectionQuality } from '@/hooks/useConnectionQuality'
import { getQualityColorClasses, formatDataAge } from '@/utils/connectionQuality'
import { ConnectionQuality } from '@/types/health'

interface ConnectionQualityIndicatorProps {
  className?: string
}

/**
 * Get icon for connection quality
 */
function getQualityIcon(quality: ConnectionQuality) {
  switch (quality) {
    case 'excellent':
    case 'good':
      return CheckCircle
    case 'fair':
      return AlertTriangle
    case 'poor':
      return Wifi
    case 'disconnected':
      return WifiOff
  }
}

/**
 * Tooltip content component
 */
function QualityTooltip({
  quality,
  metrics,
  lastUpdate
}: {
  quality: ConnectionQuality
  metrics: any
  lastUpdate: Date | null
}) {
  const colorClasses = getQualityColorClasses(quality)

  return (
    <div className="absolute bottom-full right-0 mb-2 w-64 p-3 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50">
      <div className="space-y-2">
        <div className="flex items-center justify-between border-b border-gray-700 pb-2">
          <span className="text-sm font-semibold text-white">Connection Quality</span>
          <span className={`text-sm font-bold ${colorClasses.text}`}>
            {colorClasses.label}
          </span>
        </div>

        <div className="space-y-1 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-gray-400">WebSocket:</span>
            <span className="text-white capitalize">{metrics.wsStatus}</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-400">Avg Latency:</span>
            <span className="text-white">{metrics.avgLatency}ms</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-400">Last Update:</span>
            <span className="text-white">
              {lastUpdate ? formatDataAge(metrics.dataAge) : 'Never'}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-400">Data Age:</span>
            <span className="text-white">{metrics.dataAge.toFixed(1)}s</span>
          </div>
        </div>

        <div className="pt-2 border-t border-gray-700 text-xs text-gray-400">
          {quality === 'excellent' && 'All systems optimal'}
          {quality === 'good' && 'Minor latency or delays'}
          {quality === 'fair' && 'Noticeable latency or data staleness'}
          {quality === 'poor' && 'High latency or reconnecting'}
          {quality === 'disconnected' && 'Connection lost'}
        </div>
      </div>

      {/* Tooltip arrow */}
      <div className="absolute top-full right-4 -mt-px">
        <div className="border-8 border-transparent border-t-gray-700" />
      </div>
    </div>
  )
}

/**
 * Connection quality indicator component
 */
export default function ConnectionQualityIndicator({
  className = ''
}: ConnectionQualityIndicatorProps) {
  const { quality, metrics, lastUpdate } = useConnectionQuality()
  const [showTooltip, setShowTooltip] = useState(false)

  const colorClasses = getQualityColorClasses(quality)
  const Icon = getQualityIcon(quality)

  return (
    <div
      className={`relative ${className}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <div
        className={`flex items-center gap-2 px-3 py-1.5 rounded-full border ${colorClasses.bg} ${colorClasses.border} cursor-help transition-colors`}
        role="status"
        aria-label={`Connection quality: ${colorClasses.label}`}
      >
        <Icon className={`w-4 h-4 ${colorClasses.text}`} aria-hidden="true" />
        <span className={`text-xs font-medium ${colorClasses.text}`}>
          {colorClasses.label}
        </span>
        <span className="text-xs text-gray-500">
          {lastUpdate ? formatDataAge(metrics.dataAge) : 'No data'}
        </span>
      </div>

      {/* Tooltip */}
      {showTooltip && (
        <QualityTooltip quality={quality} metrics={metrics} lastUpdate={lastUpdate} />
      )}
    </div>
  )
}
