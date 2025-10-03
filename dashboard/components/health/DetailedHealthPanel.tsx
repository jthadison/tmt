/**
 * DetailedHealthPanel Component
 * Expandable drawer showing comprehensive health status for all services
 */

'use client'

import React, { useEffect, useRef, useState, useMemo } from 'react'
import { X, RefreshCw, AlertCircle } from 'lucide-react'
import { useHealthData } from '@/context/HealthDataContext'
import AgentHealthCard from './AgentHealthCard'
import ServiceHealthCard from './ServiceHealthCard'
import CircuitBreakerStatus from './CircuitBreakerStatus'
import SystemMetrics from './SystemMetrics'

interface DetailedHealthPanelProps {
  isOpen: boolean
  onClose: () => void
}

/**
 * Data freshness indicator
 */
function FreshnessIndicator({ lastUpdate }: { lastUpdate: Date | null }) {
  const [secondsAgo, setSecondsAgo] = useState(0)

  useEffect(() => {
    if (!lastUpdate) return

    const interval = setInterval(() => {
      const now = new Date()
      const diff = Math.floor((now.getTime() - lastUpdate.getTime()) / 1000)
      setSecondsAgo(diff)
    }, 1000)

    return () => clearInterval(interval)
  }, [lastUpdate])

  const freshnessStatus = useMemo(() => {
    if (secondsAgo <= 5) {
      return { text: 'text-green-400', icon: '', label: 'Fresh' }
    } else if (secondsAgo <= 15) {
      return { text: 'text-yellow-400', icon: '⚠', label: 'Stale' }
    } else {
      return { text: 'text-red-400', icon: '⚠', label: 'Very Stale' }
    }
  }, [secondsAgo])

  if (!lastUpdate) {
    return <span className="text-xs text-gray-500">No data</span>
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-400">Last Updated:</span>
      <span className={`text-xs font-medium ${freshnessStatus.text}`}>
        {freshnessStatus.icon && `${freshnessStatus.icon} `}
        {secondsAgo}s ago
      </span>
    </div>
  )
}

/**
 * Detailed health panel component
 */
export default function DetailedHealthPanel({
  isOpen,
  onClose
}: DetailedHealthPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null)
  // Use shared health data from context
  const { healthData, loading, error, lastUpdate, refreshData, latencyHistory } = useHealthData()

  /**
   * Handle ESC key to close panel
   */
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      // Focus panel for keyboard navigation
      panelRef.current?.focus()
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, onClose])

  /**
   * Handle click outside to close
   */
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose()
      }
    }

    if (isOpen) {
      // Small delay to avoid immediate close on the click that opened the panel
      setTimeout(() => {
        document.addEventListener('mousedown', handleClickOutside)
      }, 100)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen, onClose])

  /**
   * Prevent body scroll when panel is open
   */
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = 'unset'
    }

    return () => {
      document.body.style.overflow = 'unset'
    }
  }, [isOpen])

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40 transition-opacity duration-300"
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        ref={panelRef}
        className="fixed top-0 left-0 right-0 bg-gray-900 border-b border-gray-700 shadow-2xl z-50 max-h-[80vh] overflow-y-auto animate-slide-down"
        role="dialog"
        aria-modal="true"
        aria-labelledby="health-panel-title"
        tabIndex={-1}
      >
        <div className="max-w-7xl mx-auto p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2
                id="health-panel-title"
                className="text-xl font-bold text-white"
              >
                Detailed System Health
              </h2>
              <FreshnessIndicator lastUpdate={lastUpdate} />
            </div>

            <div className="flex items-center gap-2">
              {/* Refresh button */}
              <button
                onClick={() => refreshData()}
                className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded transition-colors"
                aria-label="Refresh health data"
                disabled={loading}
              >
                <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
              </button>

              {/* Close button */}
              <button
                onClick={onClose}
                className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded transition-colors"
                aria-label="Close panel"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Loading state */}
          {loading && !healthData && (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <RefreshCw className="w-8 h-8 text-gray-400 animate-spin mx-auto mb-2" />
                <p className="text-gray-400">Loading health data...</p>
              </div>
            </div>
          )}

          {/* Error state */}
          {error && !healthData && (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
                <p className="text-red-400 mb-2">Failed to load health data</p>
                <p className="text-sm text-gray-500">{error}</p>
                <button
                  onClick={() => refreshData()}
                  className="mt-4 px-4 py-2 bg-gray-800 text-white rounded hover:bg-gray-700 transition-colors"
                >
                  Retry
                </button>
              </div>
            </div>
          )}

          {/* Content */}
          {healthData && (
            <div className="space-y-6">
              {/* System Metrics */}
              <SystemMetrics metrics={healthData.system_metrics} />

              {/* Circuit Breaker Status */}
              <CircuitBreakerStatus circuitBreaker={healthData.circuit_breaker} />

              {/* AI Agents Section */}
              <section>
                <h3 className="text-sm font-semibold text-white mb-3">
                  AI Agents ({healthData.agents.length})
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {healthData.agents.map((agent) => (
                    <AgentHealthCard
                      key={agent.port}
                      agent={agent}
                      latencyHistory={latencyHistory.get(`agent-${agent.port}`) || []}
                    />
                  ))}
                </div>
              </section>

              {/* Core Services Section */}
              <section>
                <h3 className="text-sm font-semibold text-white mb-3">
                  Core Services ({healthData.services.length})
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {healthData.services.map((service) => (
                    <ServiceHealthCard
                      key={service.port || service.name}
                      service={service}
                    />
                  ))}
                </div>
              </section>

              {/* External Services Section */}
              {healthData.external_services.length > 0 && (
                <section>
                  <h3 className="text-sm font-semibold text-white mb-3">
                    External Services ({healthData.external_services.length})
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {healthData.external_services.map((service) => (
                      <ServiceHealthCard
                        key={service.name}
                        service={service}
                      />
                    ))}
                  </div>
                </section>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Add animation styles */}
      <style jsx>{`
        @keyframes slide-down {
          from {
            transform: translateY(-100%);
            opacity: 0;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }

        .animate-slide-down {
          animation: slide-down 300ms ease-out;
        }
      `}</style>
    </>
  )
}
