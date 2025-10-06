/**
 * Sharpe Ratio Historical Chart Component - Story 8.1
 * 90-day trend chart with threshold bands
 */

'use client'

import React from 'react'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  ChartOptions,
} from 'chart.js'

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

interface SharpeRatioHistoricalChartProps {
  data: Array<{
    date: string
    sharpeRatio: number
  }>
}

export const SharpeRatioHistoricalChart: React.FC<SharpeRatioHistoricalChartProps> = ({ data }) => {
  // Prepare chart data
  const chartData = {
    labels: data.map((d) => {
      const date = new Date(d.date)
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    }),
    datasets: [
      {
        label: 'Sharpe Ratio',
        data: data.map((d) => d.sharpeRatio),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointBackgroundColor: '#3b82f6',
        tension: 0.4,
        fill: true,
      },
    ],
  }

  const options: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        padding: 12,
        titleColor: '#fff',
        bodyColor: '#fff',
        borderColor: 'rgba(255, 255, 255, 0.1)',
        borderWidth: 1,
        displayColors: false,
        callbacks: {
          title: (context) => {
            return context[0].label
          },
          label: (context) => {
            const value = context.parsed.y
            let threshold = 'Poor'
            if (value >= 2.0) threshold = 'Outstanding'
            else if (value >= 1.5) threshold = 'Excellent'
            else if (value >= 1.0) threshold = 'Good'
            else if (value >= 0.5) threshold = 'Acceptable'

            return [`Sharpe Ratio: ${value.toFixed(3)}`, `Level: ${threshold}`]
          },
        },
      },
    },
    scales: {
      x: {
        display: true,
        grid: {
          display: false,
        },
        ticks: {
          maxRotation: 45,
          minRotation: 45,
          autoSkip: true,
          maxTicksLimit: 12,
          color: 'rgb(156, 163, 175)',
        },
      },
      y: {
        display: true,
        beginAtZero: true,
        max: 3,
        grid: {
          color: 'rgba(156, 163, 175, 0.1)',
        },
        ticks: {
          color: 'rgb(156, 163, 175)',
          callback: (value) => (typeof value === 'number' ? value.toFixed(1) : value),
        },
      },
    },
  }

  return (
    <div className="sharpe-ratio-historical-chart w-full">
      {/* Threshold reference bands */}
      <div className="flex items-center justify-center gap-4 mb-4 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded" style={{ backgroundColor: '#ef4444' }} />
          <span className="text-muted-foreground">Poor (&lt;0.5)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded" style={{ backgroundColor: '#f59e0b' }} />
          <span className="text-muted-foreground">Acceptable (0.5-1.0)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded" style={{ backgroundColor: '#eab308' }} />
          <span className="text-muted-foreground">Good (1.0-1.5)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded" style={{ backgroundColor: '#10b981' }} />
          <span className="text-muted-foreground">Excellent (1.5-2.0)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded" style={{ backgroundColor: '#059669' }} />
          <span className="text-muted-foreground">Outstanding (&gt;2.0)</span>
        </div>
      </div>

      {/* Chart container */}
      <div className="h-[300px] w-full">
        <Line data={chartData} options={options} />
      </div>
    </div>
  )
}
