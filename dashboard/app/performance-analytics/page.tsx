'use client'

import { useState, useEffect } from 'react'
import MainLayout from '@/components/layout/MainLayout'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import PerformanceAnalyticsDashboard from '@/components/analytics/PerformanceAnalyticsDashboard'
import { performanceAnalyticsService } from '@/services/performanceAnalyticsService'
import { TradeBreakdown, ComplianceReport } from '@/types/performanceAnalytics'

export default function PerformanceAnalyticsPage() {
  const [accountIds, setAccountIds] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Fetch available account IDs
    const fetchAccountIds = async () => {
      try {
        setLoading(true)
        // This would typically come from an account service
        // For now, using mock data
        const mockAccountIds = [
          'account_001',
          'account_002', 
          'account_003'
        ]
        setAccountIds(mockAccountIds)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load accounts')
      } finally {
        setLoading(false)
      }
    }

    fetchAccountIds()
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
        <PerformanceAnalyticsDashboard
          accountIds={accountIds}
          initialView="overview"
          onTradeSelect={handleTradeSelect}
          onReportGenerated={handleReportGenerated}
        />
      </MainLayout>
    </ProtectedRoute>
  )
}