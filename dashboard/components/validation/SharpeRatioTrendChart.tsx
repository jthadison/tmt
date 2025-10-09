/**
 * SharpeRatioTrendChart Component - Story 11.8, Task 4
 *
 * Displays 30-day rolling Sharpe ratio trend with target line
 */

'use client';

import React from 'react';
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
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import Card from '@/components/ui/Card';
import { format, parseISO } from 'date-fns';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface SharpeDataPoint {
  date: string;
  sharpe: number;
  target?: number;
}

interface SharpeRatioTrendChartProps {
  data: SharpeDataPoint[];
  targetSharpe?: number;
  loading?: boolean;
}

export function SharpeRatioTrendChart({
  data,
  targetSharpe = 1.0,
  loading = false,
}: SharpeRatioTrendChartProps) {
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

  // Sort data by date
  const sortedData = [...data].sort((a, b) =>
    new Date(a.date).getTime() - new Date(b.date).getTime()
  );

  const chartData = {
    labels: sortedData.map((d) => format(parseISO(d.date), 'MMM dd')),
    datasets: [
      {
        label: 'Sharpe Ratio',
        data: sortedData.map((d) => d.sharpe),
        borderColor: 'rgba(59, 130, 246, 1)', // blue-500
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 3,
        pointHoverRadius: 5,
      },
      {
        label: 'Target',
        data: sortedData.map(() => targetSharpe),
        borderColor: 'rgba(16, 185, 129, 0.8)', // green-500
        backgroundColor: 'transparent',
        borderDash: [5, 5],
        pointRadius: 0,
        pointHoverRadius: 0,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: false,
      },
      tooltip: {
        callbacks: {
          label: function (context: any) {
            let label = context.dataset.label || '';
            if (label) {
              label += ': ';
            }
            if (context.parsed.y !== null) {
              label += context.parsed.y.toFixed(3);
            }
            return label;
          },
        },
      },
    },
    scales: {
      y: {
        beginAtZero: false,
        title: {
          display: true,
          text: 'Sharpe Ratio',
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.05)',
        },
      },
      x: {
        grid: {
          display: false,
        },
      },
    },
  };

  // Calculate statistics
  const currentSharpe = sortedData[sortedData.length - 1]?.sharpe || 0;
  const avgSharpe = sortedData.reduce((sum, d) => sum + d.sharpe, 0) / sortedData.length;
  const minSharpe = Math.min(...sortedData.map((d) => d.sharpe));
  const maxSharpe = Math.max(...sortedData.map((d) => d.sharpe));

  // Identify periods of degradation (below target)
  const degradedPeriods = sortedData.filter((d) => d.sharpe < targetSharpe).length;
  const degradationPct = (degradedPeriods / sortedData.length) * 100;

  return (
    <Card className="p-6 hover:shadow-lg transition-shadow">
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            30-Day Rolling Sharpe Ratio
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            Performance trend over the last 30 days
          </p>
        </div>

        {/* Chart */}
        <div className="flex-1 min-h-[280px] mb-4">
          <Line data={chartData} options={options} />
        </div>

        {/* Statistics */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-3 bg-blue-50 rounded-lg">
            <div className="text-xs text-gray-600">Current</div>
            <div className="text-lg font-bold text-blue-600">
              {currentSharpe.toFixed(3)}
            </div>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg">
            <div className="text-xs text-gray-600">Average</div>
            <div className="text-lg font-bold text-gray-700">
              {avgSharpe.toFixed(3)}
            </div>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg">
            <div className="text-xs text-gray-600">Range</div>
            <div className="text-sm font-semibold text-gray-700">
              {minSharpe.toFixed(2)} - {maxSharpe.toFixed(2)}
            </div>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg">
            <div className="text-xs text-gray-600">Below Target</div>
            <div className={`text-lg font-bold ${degradationPct > 30 ? 'text-red-600' : 'text-gray-700'
              }`}>
              {degradationPct.toFixed(0)}%
            </div>
          </div>
        </div>

        {/* Warning for prolonged degradation */}
        {degradationPct > 30 && (
          <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-sm text-yellow-800">
              ⚠️ Sharpe ratio has been below target ({targetSharpe.toFixed(1)}) for{' '}
              {degradationPct.toFixed(0)}% of the period. Consider reviewing parameters.
            </p>
          </div>
        )}
      </div>
    </Card>
  );
}
