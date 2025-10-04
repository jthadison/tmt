/**
 * Performance Metrics Dashboard Component
 * 2x2 grid of key performance widgets
 */

'use client'

import React from 'react'
import { usePerformanceMetrics } from '@/hooks/usePerformanceMetrics'
import { useEquityCurve } from '@/hooks/useEquityCurve'
import WinRateGauge from './WinRateGauge'
import ProfitFactorDisplay from './ProfitFactorDisplay'
import AverageTradeMetrics from './AverageTradeMetrics'
import EquityCurveChart from './EquityCurveChart'
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton'

interface PerformanceMetricsDashboardProps {
  /** Metrics period (default: 30d) */
  period?: '7d' | '30d' | '90d' | 'all'
  /** Equity curve days (default: 30) */
  equityDays?: number
}

/**
 * Performance metrics dashboard component
 */
export function PerformanceMetricsDashboard({
  period = '30d',
  equityDays = 30
}: PerformanceMetricsDashboardProps = {}) {
  const { metrics, previousMetrics, isLoading: metricsLoading, error: metricsError } = usePerformanceMetrics({ period })
  const { equityCurve, isLoading: equityLoading, error: equityError } = useEquityCurve({ days: equityDays })

  const isLoading = metricsLoading || equityLoading
  const error = metricsError || equityError

  // Loading skeleton
  if (isLoading) {
    return (
      <section className="space-y-6">
        <h2 className="text-2xl font-bold text-white">Performance Metrics</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <LoadingSkeleton className="h-80" />
          <LoadingSkeleton className="h-80" />
          <LoadingSkeleton className="h-80" />
          <LoadingSkeleton className="h-80" />
        </div>
      </section>
    )
  }

  // Error state
  if (error) {
    return (
      <section className="space-y-6">
        <h2 className="text-2xl font-bold text-white">Performance Metrics</h2>
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      </section>
    )
  }

  // No data state
  if (!metrics || !equityCurve) {
    return (
      <section className="space-y-6">
        <h2 className="text-2xl font-bold text-white">Performance Metrics</h2>
        <div className="text-center text-gray-400 py-12">
          No performance data available
        </div>
      </section>
    )
  }

  return (
    <section className="space-y-6">
      <h2 className="text-2xl font-bold text-white">Performance Metrics</h2>

      {/* 2x2 Grid Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Top Left: Win Rate Gauge */}
        <WinRateGauge winRate={metrics.winRate} />

        {/* Top Right: Profit Factor */}
        <ProfitFactorDisplay profitFactor={metrics.profitFactor} />

        {/* Bottom Left: Average Trade Metrics */}
        <AverageTradeMetrics
          current={metrics}
          previous={previousMetrics}
        />

        {/* Bottom Right: Equity Curve */}
        <EquityCurveChart data={equityCurve} />
      </div>
    </section>
  )
}

export default PerformanceMetricsDashboard
