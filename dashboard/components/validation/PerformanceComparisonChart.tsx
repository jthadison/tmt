/**
 * PerformanceComparisonChart Component - Story 11.8, Task 3
 *
 * Displays comparison between live and backtest performance metrics
 */

'use client';

import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';
import Card from '@/components/ui/Card';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

interface PerformanceMetric {
  metric: string;
  live_value: number;
  backtest_value: number;
  deviation_pct: number;
}

interface PerformanceComparisonChartProps {
  metrics: PerformanceMetric[];
  loading?: boolean;
}

export function PerformanceComparisonChart({
  metrics,
  loading = false,
}: PerformanceComparisonChartProps) {
  if (loading) {
    return (
      <Card className="p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </Card>
    );
  }

  const chartData = {
    labels: metrics.map((m) => m.metric),
    datasets: [
      {
        label: 'Live Performance',
        data: metrics.map((m) => m.live_value),
        backgroundColor: 'rgba(59, 130, 246, 0.7)', // blue-500
        borderColor: 'rgba(59, 130, 246, 1)',
        borderWidth: 1,
      },
      {
        label: 'Backtest Performance',
        data: metrics.map((m) => m.backtest_value),
        backgroundColor: 'rgba(16, 185, 129, 0.7)', // green-500
        borderColor: 'rgba(16, 185, 129, 1)',
        borderWidth: 1,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: false,
      },
      tooltip: {
        callbacks: {
          afterLabel: function (context: any) {
            const index = context.dataIndex;
            const deviation = metrics[index]?.deviation_pct;
            if (deviation !== undefined) {
              const sign = deviation >= 0 ? '+' : '';
              return `Deviation: ${sign}${deviation.toFixed(1)}%`;
            }
            return '';
          },
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'Value',
        },
      },
    },
  };

  return (
    <Card className="p-6 hover:shadow-lg transition-shadow">
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            Live vs. Backtest Performance
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            Comparison of key performance metrics
          </p>
        </div>

        {/* Chart */}
        <div className="flex-1 min-h-[300px]">
          <Bar data={chartData} options={options} />
        </div>

        {/* Deviation indicators */}
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {metrics.map((metric, index) => {
            const isSignificant = Math.abs(metric.deviation_pct) > 10;
            const deviationColor = metric.deviation_pct < -30
              ? 'text-red-600'
              : metric.deviation_pct < -10
              ? 'text-yellow-600'
              : 'text-green-600';

            return (
              <div
                key={index}
                className={`p-2 rounded-lg ${isSignificant ? 'bg-yellow-50 border border-yellow-200' : 'bg-gray-50'
                  }`}
              >
                <div className="text-xs text-gray-600">{metric.metric}</div>
                <div className={`text-sm font-semibold ${deviationColor}`}>
                  {metric.deviation_pct >= 0 ? '+' : ''}
                  {metric.deviation_pct.toFixed(1)}%
                </div>
              </div>
            );
          })}
        </div>

        {/* Warning for significant deviations */}
        {metrics.some((m) => m.deviation_pct < -30) && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-800">
              ⚠️ <strong>Warning:</strong> Live performance is significantly below backtest
              expectations for some metrics. Review parameter configuration.
            </p>
          </div>
        )}
      </div>
    </Card>
  );
}
