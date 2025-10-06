'use client'

import { BacktestResults } from '@/app/api/analytics/backtest-results/route'
import { ForwardTestResults } from '@/app/api/analytics/forward-test-performance/route'

interface ComparisonRow {
  metric: string
  backtest: number
  forwardTest: number
  variance: number
  status: 'good' | 'warning' | 'poor'
  unit?: string
}

interface Props {
  backtest: BacktestResults
  forwardTest: ForwardTestResults
}

function compareMetric(
  name: string,
  backtestValue: number,
  forwardValue: number,
  unit?: string
): ComparisonRow {
  const variance = backtestValue !== 0
    ? ((forwardValue - backtestValue) / Math.abs(backtestValue)) * 100
    : 0

  let status: 'good' | 'warning' | 'poor'
  const absVariance = Math.abs(variance)
  if (absVariance < 15) status = 'good'
  else if (absVariance < 30) status = 'warning'
  else status = 'poor'

  return {
    metric: name,
    backtest: backtestValue,
    forwardTest: forwardValue,
    variance,
    status,
    unit
  }
}

function formatValue(value: number, unit?: string): string {
  if (unit === '%') return `${value.toFixed(1)}%`
  if (unit === '$') return `$${value.toFixed(2)}`
  return value.toFixed(2)
}

function ComparisonRow({ data }: { data: ComparisonRow }) {
  const statusConfig = {
    good: { icon: '✓', color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
    warning: { icon: '⚠', color: 'text-amber-500', bg: 'bg-amber-500/10' },
    poor: { icon: '✗', color: 'text-red-500', bg: 'bg-red-500/10' }
  }

  const config = statusConfig[data.status]

  return (
    <tr className="border-b border-border/50 hover:bg-muted/30 transition-colors">
      <td className="p-3 font-medium text-foreground">{data.metric}</td>
      <td className="p-3 text-right font-mono text-muted-foreground">
        {formatValue(data.backtest, data.unit)}
      </td>
      <td className="p-3 text-right font-mono text-foreground">
        {formatValue(data.forwardTest, data.unit)}
      </td>
      <td className={`p-3 text-right font-semibold ${data.variance < 0 ? 'text-red-500' : 'text-muted-foreground'}`}>
        {data.variance > 0 ? '+' : ''}{data.variance.toFixed(1)}%
      </td>
      <td className="p-3 flex justify-center">
        <div className={`inline-flex items-center justify-center w-8 h-8 rounded-full ${config.bg}`}>
          <span className={`text-lg ${config.color}`}>{config.icon}</span>
        </div>
      </td>
    </tr>
  )
}

export function MetricComparisonTable({ backtest, forwardTest }: Props) {
  const comparisons: ComparisonRow[] = [
    compareMetric('Win Rate', backtest.metrics.winRate, forwardTest.metrics.winRate, '%'),
    compareMetric('Avg Win', backtest.metrics.avgWin, forwardTest.metrics.avgWin, '$'),
    compareMetric('Avg Loss', backtest.metrics.avgLoss, forwardTest.metrics.avgLoss, '$'),
    compareMetric('Profit Factor', backtest.metrics.profitFactor, forwardTest.metrics.profitFactor),
    compareMetric('Max Drawdown', backtest.metrics.maxDrawdown, forwardTest.metrics.maxDrawdown, '$'),
    compareMetric('Sharpe Ratio', backtest.metrics.sharpeRatio, forwardTest.metrics.sharpeRatio),
  ]

  return (
    <div className="metric-comparison-table bg-card rounded-lg border border-border overflow-hidden">
      <div className="p-4 border-b border-border">
        <h3 className="text-lg font-semibold text-foreground">Performance Metrics Comparison</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Backtest vs. Forward Test Performance Analysis
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border bg-muted/30">
              <th className="text-left p-3 font-semibold text-foreground">Metric</th>
              <th className="text-right p-3 font-semibold text-foreground">Backtest</th>
              <th className="text-right p-3 font-semibold text-foreground">Forward Test</th>
              <th className="text-right p-3 font-semibold text-foreground">Variance</th>
              <th className="text-center p-3 font-semibold text-foreground">Status</th>
            </tr>
          </thead>
          <tbody>
            {comparisons.map((row, index) => (
              <ComparisonRow key={index} data={row} />
            ))}
          </tbody>
        </table>
      </div>

      <div className="p-4 bg-muted/20 border-t border-border">
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-emerald-500/20 border-2 border-emerald-500" />
            <span className="text-muted-foreground">{'<'}15% variance (Good)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-amber-500/20 border-2 border-amber-500" />
            <span className="text-muted-foreground">15-30% variance (Warning)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500/20 border-2 border-red-500" />
            <span className="text-muted-foreground">{'>'}30% variance (Poor)</span>
          </div>
        </div>
      </div>
    </div>
  )
}
