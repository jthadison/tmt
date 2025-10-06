'use client'

import { Bar } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions
} from 'chart.js'
import { DrawdownBucket } from '@/types/analytics'

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

interface Props {
  distribution: DrawdownBucket[]
}

export function DrawdownDistributionChart({ distribution }: Props) {
  const chartData = {
    labels: distribution.map(d => d.bucket),
    datasets: [
      {
        label: 'Drawdown Occurrences',
        data: distribution.map(d => d.count),
        backgroundColor: distribution.map((d, i) => {
          // Color code by severity
          if (i < 2) return 'rgba(16, 185, 129, 0.8)' // Green (0-10%)
          if (i < 4) return 'rgba(234, 179, 8, 0.8)' // Yellow (10-20%)
          return 'rgba(239, 68, 68, 0.8)' // Red (>20%)
        }),
        borderColor: distribution.map((d, i) => {
          if (i < 2) return 'rgb(16, 185, 129)'
          if (i < 4) return 'rgb(234, 179, 8)'
          return 'rgb(239, 68, 68)'
        }),
        borderWidth: 1
      }
    ]
  }

  const options: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        callbacks: {
          label: context => {
            const item = distribution[context.dataIndex]
            return [
              `Occurrences: ${item.count}`,
              `Percentage: ${item.percentage.toFixed(1)}%`
            ]
          }
        }
      }
    },
    scales: {
      x: {
        title: {
          display: true,
          text: 'Drawdown Size',
          color: 'rgb(156, 163, 175)'
        },
        grid: {
          display: false
        },
        ticks: {
          color: 'rgb(156, 163, 175)'
        }
      },
      y: {
        title: {
          display: true,
          text: 'Frequency',
          color: 'rgb(156, 163, 175)'
        },
        beginAtZero: true,
        grid: {
          color: 'rgba(156, 163, 175, 0.1)'
        },
        ticks: {
          color: 'rgb(156, 163, 175)'
        }
      }
    }
  }

  return (
    <div className="drawdown-distribution-chart">
      <h4 className="text-sm font-medium mb-3 text-gray-900 dark:text-white">
        Drawdown Distribution
      </h4>
      <div className="h-64">
        <Bar data={chartData} options={options} />
      </div>
    </div>
  )
}
