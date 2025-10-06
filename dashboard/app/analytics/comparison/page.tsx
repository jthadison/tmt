'use client'

import { useEffect, useState } from 'react'
import { MetricComparisonTable } from '@/components/analytics/MetricComparisonTable'
import { CumulativeReturnsChart } from '@/components/analytics/CumulativeReturnsChart'
import { OverfittingAnalysisDashboard } from '@/components/analytics/OverfittingAnalysisDashboard'
import { StabilityScoreCard } from '@/components/analytics/StabilityScoreCard'
import { BacktestResults } from '@/app/api/analytics/backtest-results/route'
import { ForwardTestResults } from '@/app/api/analytics/forward-test-performance/route'
import { OverfittingAnalysis } from '@/app/api/analytics/overfitting-analysis/route'

export default function ComparisonPage() {
  const [backtestData, setBacktestData] = useState<BacktestResults | null>(null)
  const [forwardTestData, setForwardTestData] = useState<ForwardTestResults | null>(null)
  const [overfittingData, setOverfittingData] = useState<OverfittingAnalysis | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true)
        setError(null)

        // Fetch backtest results
        const backtestRes = await fetch('/api/analytics/backtest-results')
        if (!backtestRes.ok) {
          throw new Error('Failed to fetch backtest results')
        }
        const backtest = await backtestRes.json()
        setBacktestData(backtest)

        // Fetch forward test results
        const forwardRes = await fetch('/api/analytics/forward-test-performance')
        if (!forwardRes.ok) {
          throw new Error('Failed to fetch forward test results')
        }
        const forward = await forwardRes.json()
        setForwardTestData(forward)

        // Fetch overfitting analysis
        const overfittingRes = await fetch('/api/analytics/overfitting-analysis')
        if (!overfittingRes.ok) {
          throw new Error('Failed to fetch overfitting analysis')
        }
        const overfitting = await overfittingRes.json()
        setOverfittingData(overfitting)

      } catch (err) {
        console.error('Error fetching comparison data:', err)
        setError(err instanceof Error ? err.message : 'Failed to load comparison data')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          <p className="text-muted-foreground">Loading comparison analysis...</p>
        </div>
      </div>
    )
  }

  if (error || !backtestData || !forwardTestData || !overfittingData) {
    return (
      <div className="container mx-auto p-6">
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-6">
          <div className="flex items-start gap-3">
            <span className="text-red-500 text-2xl">⚠</span>
            <div>
              <h3 className="text-lg font-semibold text-red-500 mb-2">Error Loading Data</h3>
              <p className="text-red-400">{error || 'Failed to load comparison data. Please try again later.'}</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-foreground mb-2">
          Forward Test vs. Backtest Comparison
        </h1>
        <p className="text-muted-foreground">
          Comprehensive analysis of strategy performance validation and overfitting detection
        </p>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-card rounded-lg border border-border p-6">
          <div className="text-sm text-muted-foreground mb-1">Backtest Period</div>
          <div className="text-2xl font-bold text-foreground mb-2">
            {backtestData.testPeriod.totalDays} Days
          </div>
          <div className="text-xs text-muted-foreground">
            {new Date(backtestData.testPeriod.startDate).toLocaleDateString()} - {new Date(backtestData.testPeriod.endDate).toLocaleDateString()}
          </div>
        </div>

        <div className="bg-card rounded-lg border border-border p-6">
          <div className="text-sm text-muted-foreground mb-1">Forward Test Period</div>
          <div className="text-2xl font-bold text-foreground mb-2">
            {forwardTestData.testPeriod.totalDays} Days
          </div>
          <div className="text-xs text-muted-foreground">
            {new Date(forwardTestData.testPeriod.startDate).toLocaleDateString()} - {new Date(forwardTestData.testPeriod.endDate).toLocaleDateString()}
          </div>
        </div>

        <div className="bg-card rounded-lg border border-border p-6">
          <div className="text-sm text-muted-foreground mb-1">Total Trades</div>
          <div className="flex items-baseline gap-3">
            <div>
              <div className="text-sm text-muted-foreground">Backtest</div>
              <div className="text-2xl font-bold text-foreground">
                {backtestData.metrics.totalTrades}
              </div>
            </div>
            <div className="text-muted-foreground">|</div>
            <div>
              <div className="text-sm text-muted-foreground">Forward</div>
              <div className="text-2xl font-bold text-foreground">
                {forwardTestData.metrics.totalTrades}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Overfitting Analysis - Full Width */}
      <OverfittingAnalysisDashboard analysis={overfittingData} />

      {/* Metric Comparison Table */}
      <MetricComparisonTable backtest={backtestData} forwardTest={forwardTestData} />

      {/* Stability Score and Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <StabilityScoreCard score={overfittingData.stabilityScore} />
        </div>
        <div className="lg:col-span-2">
          <CumulativeReturnsChart backtest={backtestData} forwardTest={forwardTestData} />
        </div>
      </div>

      {/* Additional Info */}
      <div className="bg-muted/20 rounded-lg p-6 border border-border">
        <h3 className="text-lg font-semibold text-foreground mb-3">Analysis Methodology</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-muted-foreground">
          <div>
            <h4 className="font-medium text-foreground mb-2">Overfitting Score Calculation</h4>
            <p>Normalized degradation across all key performance metrics. Score ranges from 0 (no overfitting) to 1 (severe overfitting).</p>
          </div>
          <div>
            <h4 className="font-medium text-foreground mb-2">Stability Score Calculation</h4>
            <p>Measures consistency of returns across weekly time windows using coefficient of variation. Higher scores indicate more stable performance.</p>
          </div>
          <div>
            <h4 className="font-medium text-foreground mb-2">Risk Thresholds</h4>
            <ul className="list-disc list-inside space-y-1 mt-1">
              <li>Low: {'<'}15% degradation</li>
              <li>Moderate: 15-30% degradation</li>
              <li>High: {'>'}30% degradation</li>
            </ul>
          </div>
          <div>
            <h4 className="font-medium text-foreground mb-2">Data Sources</h4>
            <ul className="list-disc list-inside space-y-1 mt-1">
              <li>Backtest: {backtestData.sourceFile}</li>
              <li>Forward Test: Live trading data</li>
              <li>Updated: {new Date(overfittingData.stabilityScore).toLocaleString()}</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
