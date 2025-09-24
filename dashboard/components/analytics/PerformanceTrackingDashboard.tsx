/**
 * Performance Tracking Dashboard Component
 * Real-time tracking vs Monte Carlo projections with automated alerts
 */

'use client'

import React, { useState, useEffect, useCallback } from 'react'
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Target,
  Activity,
  Calendar,
  Shield,
  Bell,
  BellOff,
  RefreshCw,
  CheckCircle,
  XCircle,
  Info,
  AlertCircle
} from 'lucide-react'
import { motion } from 'framer-motion'

interface PerformanceTrackingDashboardProps {
  accountIds: string[]
  dateRange: { start: Date; end: Date }
  refreshInterval?: number
  autoRefresh?: boolean
}

interface ProjectionData {
  expected_6month_pnl: number
  current_actual_pnl: number
  daily_expected: number
  weekly_expected: number
  monthly_expected: number
  confidence_lower_95: number
  confidence_upper_95: number
  confidence_lower_99: number
  confidence_upper_99: number
  days_elapsed: number
  variance_percentage: number
}

interface Alert {
  id: string
  severity: 'INFO' | 'WARNING' | 'CRITICAL' | 'EMERGENCY'
  type: string
  message: string
  timestamp: Date
  acknowledged: boolean
}

interface SharpeData {
  current_30day: number
  rolling_7day: number
  rolling_14day: number
  trend: 'improving' | 'declining' | 'stable'
  target_threshold: number
}

const SEVERITY_COLORS = {
  INFO: 'text-blue-400 bg-blue-900/20 border-blue-500',
  WARNING: 'text-yellow-400 bg-yellow-900/20 border-yellow-500',
  CRITICAL: 'text-orange-400 bg-orange-900/20 border-orange-500',
  EMERGENCY: 'text-red-400 bg-red-900/20 border-red-500'
}

const SEVERITY_ICONS = {
  INFO: Info,
  WARNING: AlertTriangle,
  CRITICAL: AlertCircle,
  EMERGENCY: XCircle
}

export default function PerformanceTrackingDashboard({
  accountIds,
  dateRange,
  refreshInterval = 15000,
  autoRefresh = true
}: PerformanceTrackingDashboardProps) {
  const [projectionData, setProjectionData] = useState<ProjectionData | null>(null)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [sharpeData, setSharpeData] = useState<SharpeData | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date())
  const [alertsEnabled, setAlertsEnabled] = useState(true)
  const [dataSource, setDataSource] = useState<string>('unknown')

  // Fetch performance tracking data
  const fetchTrackingData = useCallback(async () => {
    try {
      setLoading(true)

      // Fetch projection data
      const projectionResponse = await fetch('/api/performance-tracking/projections')
      const projectionResult = await projectionResponse.json()

      if (projectionResult.success) {
        setProjectionData(projectionResult.data)
        setDataSource(projectionResult.source || 'unknown')
      }

      // Fetch alerts
      const alertsResponse = await fetch('/api/performance-tracking/alerts')
      const alertsResult = await alertsResponse.json()

      if (alertsResult.success) {
        setAlerts(alertsResult.data)
      }

      // Fetch Sharpe ratio data
      const sharpeResponse = await fetch('/api/performance-tracking/sharpe')
      const sharpeResult = await sharpeResponse.json()

      if (sharpeResult.success) {
        setSharpeData(sharpeResult.data)
      }

      setLastUpdated(new Date())
    } catch (error) {
      console.error('Failed to fetch tracking data:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  // Auto-refresh effect
  useEffect(() => {
    fetchTrackingData()

    if (autoRefresh) {
      const interval = setInterval(fetchTrackingData, refreshInterval)
      return () => clearInterval(interval)
    }
  }, [fetchTrackingData, autoRefresh, refreshInterval])

  // Acknowledge alert
  const acknowledgeAlert = useCallback(async (alertId: string) => {
    try {
      await fetch(`/api/performance-tracking/alerts/${alertId}/acknowledge`, {
        method: 'POST'
      })

      setAlerts(prev => prev.map(alert =>
        alert.id === alertId ? { ...alert, acknowledged: true } : alert
      ))
    } catch (error) {
      console.error('Failed to acknowledge alert:', error)
    }
  }, [])

  // Calculate performance status
  const getPerformanceStatus = useCallback((data: ProjectionData) => {
    const variance = data.variance_percentage
    if (Math.abs(variance) <= 5) return { status: 'on_track', color: 'text-green-400' }
    if (Math.abs(variance) <= 15) return { status: 'caution', color: 'text-yellow-400' }
    return { status: 'concern', color: 'text-red-400' }
  }, [])

  // Format currency
  const formatCurrency = useCallback((amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount)
  }, [])

  // Format percentage
  const formatPercentage = useCallback((value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  }, [])

  const unacknowledgedAlerts = alerts.filter(alert => !alert.acknowledged)
  const criticalAlerts = alerts.filter(alert =>
    ['CRITICAL', 'EMERGENCY'].includes(alert.severity) && !alert.acknowledged
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Target className="w-6 h-6 text-blue-400" />
          <h3 className="text-xl font-semibold text-white">Performance vs Projections</h3>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setAlertsEnabled(!alertsEnabled)}
            className={`p-2 rounded transition-colors ${
              alertsEnabled
                ? 'bg-green-600 text-white'
                : 'bg-gray-700 text-gray-400'
            }`}
            title={alertsEnabled ? 'Disable alerts' : 'Enable alerts'}
          >
            {alertsEnabled ? <Bell className="w-4 h-4" /> : <BellOff className="w-4 h-4" />}
          </button>

          <button
            onClick={fetchTrackingData}
            disabled={loading}
            className="p-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Critical Alerts Banner */}
      {criticalAlerts.length > 0 && alertsEnabled && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-red-900/20 border border-red-500 rounded-lg p-4"
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-400" />
              <span className="font-semibold text-red-400">
                {criticalAlerts.length} Critical Alert{criticalAlerts.length > 1 ? 's' : ''}
              </span>
            </div>
            {dataSource === 'fallback_mock' && (
              <span className="text-xs text-yellow-400 bg-yellow-900/20 px-2 py-1 rounded">
                Demo Data
              </span>
            )}
          </div>
          <div className="space-y-1">
            {criticalAlerts.slice(0, 3).map(alert => (
              <div key={alert.id} className="text-sm text-red-300">
                {alert.message}
              </div>
            ))}
            {criticalAlerts.length > 3 && (
              <div className="text-sm text-red-400">
                +{criticalAlerts.length - 3} more alerts
              </div>
            )}
          </div>
        </motion.div>
      )}

      {/* Main Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* P&L vs Projection */}
        {projectionData && (
          <div className="bg-gray-800 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-lg font-semibold text-white">P&L vs Projection</h4>
              <div className={getPerformanceStatus(projectionData).color}>
                {projectionData.variance_percentage >= 0 ? (
                  <TrendingUp className="w-5 h-5" />
                ) : (
                  <TrendingDown className="w-5 h-5" />
                )}
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-400">Actual P&L:</span>
                <span className="text-white font-semibold">
                  {formatCurrency(projectionData.current_actual_pnl)}
                </span>
              </div>

              <div className="flex justify-between">
                <span className="text-gray-400">Expected ({projectionData.days_elapsed}d):</span>
                <span className="text-gray-400">
                  {formatCurrency(projectionData.daily_expected * projectionData.days_elapsed)}
                </span>
              </div>

              <div className="flex justify-between">
                <span className="text-gray-400">Variance:</span>
                <span className={getPerformanceStatus(projectionData).color}>
                  {formatPercentage(projectionData.variance_percentage)}
                </span>
              </div>

              <div className="pt-2 border-t border-gray-700">
                <div className="text-sm text-gray-500">6-Month Target:</div>
                <div className="text-lg font-semibold text-white">
                  {formatCurrency(projectionData.expected_6month_pnl)}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Confidence Intervals */}
        {projectionData && (
          <div className="bg-gray-800 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-lg font-semibold text-white">Confidence Intervals</h4>
              <Shield className="w-5 h-5 text-blue-400" />
            </div>

            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-400">95% Confidence</span>
                  <span className={
                    projectionData.current_actual_pnl >= projectionData.confidence_lower_95 &&
                    projectionData.current_actual_pnl <= projectionData.confidence_upper_95
                      ? 'text-green-400' : 'text-red-400'
                  }>
                    {projectionData.current_actual_pnl >= projectionData.confidence_lower_95 &&
                     projectionData.current_actual_pnl <= projectionData.confidence_upper_95
                      ? 'Within' : 'Outside'}
                  </span>
                </div>
                <div className="text-sm text-gray-500">
                  {formatCurrency(projectionData.confidence_lower_95)} - {formatCurrency(projectionData.confidence_upper_95)}
                </div>
              </div>

              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-400">99% Confidence</span>
                  <span className={
                    projectionData.current_actual_pnl >= projectionData.confidence_lower_99 &&
                    projectionData.current_actual_pnl <= projectionData.confidence_upper_99
                      ? 'text-green-400' : 'text-orange-400'
                  }>
                    {projectionData.current_actual_pnl >= projectionData.confidence_lower_99 &&
                     projectionData.current_actual_pnl <= projectionData.confidence_upper_99
                      ? 'Within' : 'Outside'}
                  </span>
                </div>
                <div className="text-sm text-gray-500">
                  {formatCurrency(projectionData.confidence_lower_99)} - {formatCurrency(projectionData.confidence_upper_99)}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Sharpe Ratio Monitoring */}
        {sharpeData && (
          <div className="bg-gray-800 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-lg font-semibold text-white">Sharpe Ratio</h4>
              <Activity className="w-5 h-5 text-purple-400" />
            </div>

            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-400">30-day Rolling:</span>
                <span className={
                  sharpeData.current_30day >= sharpeData.target_threshold
                    ? 'text-green-400' : 'text-yellow-400'
                }>
                  {sharpeData.current_30day.toFixed(3)}
                </span>
              </div>

              <div className="flex justify-between">
                <span className="text-gray-400">7-day Rolling:</span>
                <span className="text-gray-300">
                  {sharpeData.rolling_7day.toFixed(3)}
                </span>
              </div>

              <div className="flex justify-between">
                <span className="text-gray-400">Target Threshold:</span>
                <span className="text-gray-500">
                  {sharpeData.target_threshold.toFixed(3)}
                </span>
              </div>

              <div className="flex justify-between">
                <span className="text-gray-400">Trend:</span>
                <span className={
                  sharpeData.trend === 'improving' ? 'text-green-400' :
                  sharpeData.trend === 'declining' ? 'text-red-400' : 'text-yellow-400'
                }>
                  {sharpeData.trend.charAt(0).toUpperCase() + sharpeData.trend.slice(1)}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Recent Alerts */}
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-lg font-semibold text-white">Recent Alerts</h4>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-400">
              {unacknowledgedAlerts.length} unacknowledged
            </span>
          </div>
        </div>

        <div className="space-y-3 max-h-64 overflow-y-auto">
          {alerts.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-400" />
              No alerts at this time
            </div>
          ) : (
            alerts.slice(0, 10).map(alert => {
              const IconComponent = SEVERITY_ICONS[alert.severity]
              return (
                <motion.div
                  key={alert.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className={`border-l-4 p-3 rounded-r ${SEVERITY_COLORS[alert.severity]} ${
                    alert.acknowledged ? 'opacity-60' : ''
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-2">
                      <IconComponent className="w-4 h-4 mt-0.5 flex-shrink-0" />
                      <div>
                        <div className="text-sm font-medium">
                          {alert.type}
                        </div>
                        <div className="text-sm opacity-90 mt-1">
                          {alert.message}
                        </div>
                        <div className="text-xs opacity-60 mt-1">
                          {alert.timestamp.toLocaleString()}
                        </div>
                      </div>
                    </div>

                    {!alert.acknowledged && (
                      <button
                        onClick={() => acknowledgeAlert(alert.id)}
                        className="text-xs px-2 py-1 bg-gray-700 text-gray-300 rounded hover:bg-gray-600 transition-colors"
                      >
                        Acknowledge
                      </button>
                    )}
                  </div>
                </motion.div>
              )
            })
          )}
        </div>
      </div>

      {/* Status Footer */}
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="flex items-center justify-between text-sm text-gray-400">
          <div className="flex items-center gap-4">
            <span>Last updated: {lastUpdated.toLocaleString()}</span>
            <span>Refresh interval: {refreshInterval / 1000}s</span>
            <span className={`flex items-center gap-1 ${
              dataSource === 'real_data' || dataSource === 'performance_tracking_system'
                ? 'text-green-400'
                : dataSource === 'fallback_mock'
                ? 'text-yellow-400'
                : 'text-gray-400'
            }`}>
              <div className={`w-2 h-2 rounded-full ${
                dataSource === 'real_data' || dataSource === 'performance_tracking_system'
                  ? 'bg-green-500'
                  : dataSource === 'fallback_mock'
                  ? 'bg-yellow-500'
                  : 'bg-gray-500'
              }`}></div>
              {dataSource === 'real_data' || dataSource === 'performance_tracking_system' ? 'Live Data' :
               dataSource === 'fallback_mock' ? 'Mock Data' : 'Unknown Source'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {autoRefresh && (
              <>
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span>Auto-refresh enabled</span>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}