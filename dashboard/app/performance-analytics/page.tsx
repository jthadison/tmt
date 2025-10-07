'use client'

import { useState, useEffect } from 'react'
import MainLayout from '@/components/layout/MainLayout'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import PerformanceAnalyticsDashboard from '@/components/analytics/PerformanceAnalyticsDashboard'
import SessionPerformanceWidget from '@/components/performance/SessionPerformanceWidget'
import PerformanceMetricsDashboard from '@/components/performance/PerformanceMetricsDashboard'
import { SharpeRatioDashboard } from '@/components/analytics/SharpeRatioDashboard'
import { MonteCarloProjectionOverlay } from '@/components/analytics/MonteCarloProjectionOverlay'
import { StabilityScores } from '@/components/analytics/StabilityScores'
import { ActiveAlertPanel } from '@/components/analytics/ActiveAlertPanel'
import { AlertConfigurationPanel } from '@/components/analytics/AlertConfigurationPanel'
import { RiskAdjustedMetricsDashboard } from '@/components/analytics/RiskAdjustedMetricsDashboard'
import { AlertHistory } from '@/components/analytics/AlertHistory'
import { performanceAnalyticsService } from '@/services/performanceAnalyticsService'
import { TradeBreakdown, ComplianceReport } from '@/types/performanceAnalytics'
import { StabilityMetrics } from '@/types/analytics'

export default function PerformanceAnalyticsPage() {
  const [accountIds, setAccountIds] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [stabilityMetrics, setStabilityMetrics] = useState<StabilityMetrics | null>(null)

  useEffect(() => {
    // Fetch available account IDs and stability metrics
    const fetchData = async () => {
      try {
        setLoading(true)
        // Use real OANDA account ID
        const accountIds = [
          '101-001-21040028-001',  // Your real OANDA practice account
          // Additional accounts can be added here
        ]
        setAccountIds(accountIds)

        // Fetch stability metrics
        try {
          const response = await fetch('/api/analytics/monte-carlo?days=180&simulations=1000&stability=true')
          if (response.ok) {
            const data = await response.json()
            if (data.stability) {
              setStabilityMetrics(data.stability)
            }
          }
        } catch (err) {
          console.error('Failed to fetch stability metrics:', err)
          // Non-critical, continue without stability metrics
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load accounts')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const handleTradeSelect = (trade: TradeBreakdown) => {
    console.log('Trade selected:', trade)
    // Handle trade selection (e.g., show trade details modal)
  }

  const handleReportGenerated = (report: ComplianceReport) => {
    console.log('Report generated:', report)
    // Handle report generation (e.g., show success message, download)
  }

  if (loading) {
    return (
      <ProtectedRoute>
        <MainLayout>
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
          </div>
        </MainLayout>
      </ProtectedRoute>
    )
  }

  if (error) {
    return (
      <ProtectedRoute>
        <MainLayout>
          <div className="bg-red-100 dark:bg-red-900/20 border border-red-400 text-red-700 dark:text-red-400 px-4 py-3 rounded">
            <strong className="font-bold">Error:</strong>
            <span className="block sm:inline"> {error}</span>
          </div>
        </MainLayout>
      </ProtectedRoute>
    )
  }

  return (
    <ProtectedRoute>
      <MainLayout>
        <div className="space-y-8">
          {/* Story 8.3: Active Performance Alerts */}
          <div>
            <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Performance Degradation Monitoring</h2>
            <ActiveAlertPanel />
          </div>

          {/* Story 8.3: Risk-Adjusted Metrics Dashboard */}
          <div>
            <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Risk-Adjusted Performance Metrics</h2>
            <RiskAdjustedMetricsDashboard />
          </div>

          {/* Story 8.1: Sharpe Ratio Dashboard */}
          <div>
            <SharpeRatioDashboard />
          </div>

          {/* Story 8.1: Monte Carlo Projection Overlay */}
          <div>
            <MonteCarloProjectionOverlay />
          </div>

          {/* Story 8.1: Stability Scores */}
          {stabilityMetrics && (
            <div>
              <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Strategy Stability Analysis</h2>
              <StabilityScores metrics={stabilityMetrics} />
            </div>
          )}

          {/* Story 8.3: Alert Configuration */}
          <div>
            <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Alert Configuration</h2>
            <AlertConfigurationPanel />
          </div>

          {/* Story 8.3: Alert History */}
          <div>
            <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Alert History</h2>
            <AlertHistory />
          </div>

          {/* Story 3.3: Session Performance Widget */}
          <SessionPerformanceWidget />

          {/* Story 3.3: Performance Metrics Dashboard */}
          <PerformanceMetricsDashboard period="30d" equityDays={30} />

          {/* Existing Performance Analytics Dashboard */}
          <PerformanceAnalyticsDashboard
            accountIds={accountIds}
            initialView="overview"
            onTradeSelect={handleTradeSelect}
            onReportGenerated={handleReportGenerated}
          />
        </div>
      </MainLayout>
    </ProtectedRoute>
  )
}