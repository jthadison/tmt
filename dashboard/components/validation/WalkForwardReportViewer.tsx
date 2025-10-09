/**
 * WalkForwardReportViewer Component - Story 11.8, Task 6
 *
 * Detailed view of walk-forward validation reports with PDF export
 */

'use client';

import React from 'react';
import Card from '@/components/ui/Card';
import { Line } from 'react-chartjs-2';
import type { WalkForwardReport } from '@/types/validation';

interface WalkForwardReportViewerProps {
  report: WalkForwardReport | null;
  loading?: boolean;
  onExportPDF?: () => void;
}

export function WalkForwardReportViewer({
  report,
  loading = false,
  onExportPDF,
}: WalkForwardReportViewerProps) {
  if (loading) {
    return (
      <Card className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </Card>
    );
  }

  if (!report) {
    return (
      <Card className="p-6">
        <div className="text-center text-gray-500 py-12">
          <p>No report selected. Select a walk-forward report to view details.</p>
        </div>
      </Card>
    );
  }

  // Equity curve chart data
  const equityChartData = {
    labels: report.equity_curve_in_sample.map((d) => d.date),
    datasets: [
      {
        label: 'In-Sample',
        data: report.equity_curve_in_sample.map((d) => d.equity),
        borderColor: 'rgba(59, 130, 246, 1)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.4,
      },
      {
        label: 'Out-of-Sample',
        data: report.equity_curve_out_of_sample.map((d) => d.equity),
        borderColor: 'rgba(16, 185, 129, 1)',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        fill: true,
        tension: 0.4,
      },
    ],
  };

  const equityChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top' as const },
      title: { display: false },
    },
    scales: {
      y: { beginAtZero: true, title: { display: true, text: 'Equity' } },
    },
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-semibold text-gray-900">
              Walk-Forward Validation Report
            </h3>
            <p className="text-sm text-gray-500 mt-1">
              Job ID: {report.job_id} • {report.config_file}
            </p>
          </div>
          {onExportPDF && (
            <button
              onClick={onExportPDF}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              📄 Export PDF
            </button>
          )}
        </div>

        {/* Summary metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6">
          <div className="p-4 bg-blue-50 rounded-lg">
            <div className="text-xs text-gray-600">Avg IS Sharpe</div>
            <div className="text-2xl font-bold text-blue-600">
              {report.avg_in_sample_sharpe.toFixed(2)}
            </div>
          </div>
          <div className="p-4 bg-green-50 rounded-lg">
            <div className="text-xs text-gray-600">Avg OOS Sharpe</div>
            <div className="text-2xl font-bold text-green-600">
              {report.avg_out_of_sample_sharpe.toFixed(2)}
            </div>
          </div>
          <div className="p-4 bg-yellow-50 rounded-lg">
            <div className="text-xs text-gray-600">Overfitting Score</div>
            <div className="text-2xl font-bold text-yellow-600">
              {report.overfitting_score.toFixed(3)}
            </div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="text-xs text-gray-600">Degradation</div>
            <div className="text-2xl font-bold text-gray-700">
              {((1 - report.degradation_factor) * 100).toFixed(1)}%
            </div>
          </div>
        </div>
      </Card>

      {/* Equity curves */}
      <Card className="p-6">
        <h4 className="text-lg font-semibold text-gray-900 mb-4">Equity Curves</h4>
        <div className="h-80">
          <Line data={equityChartData} options={equityChartOptions} />
        </div>
      </Card>

      {/* Session performance */}
      <Card className="p-6">
        <h4 className="text-lg font-semibold text-gray-900 mb-4">
          Performance by Trading Session
        </h4>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left">Session</th>
                <th className="px-4 py-2 text-right">Sharpe</th>
                <th className="px-4 py-2 text-right">Win Rate</th>
                <th className="px-4 py-2 text-right">Profit Factor</th>
                <th className="px-4 py-2 text-right">Trades</th>
              </tr>
            </thead>
            <tbody>
              {report.session_performance.map((session) => (
                <tr key={session.session} className="border-t">
                  <td className="px-4 py-2 font-medium">{session.session}</td>
                  <td className="px-4 py-2 text-right">{session.sharpe.toFixed(2)}</td>
                  <td className="px-4 py-2 text-right">{(session.win_rate * 100).toFixed(1)}%</td>
                  <td className="px-4 py-2 text-right">{session.profit_factor.toFixed(2)}</td>
                  <td className="px-4 py-2 text-right">{session.num_trades}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Parameter stability */}
      <Card className="p-6">
        <h4 className="text-lg font-semibold text-gray-900 mb-4">Parameter Stability</h4>
        <div className="space-y-3">
          {report.parameter_stability.map((param) => (
            <div key={param.parameter} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex-1">
                <div className="font-medium text-gray-900">{param.parameter}</div>
                <div className="text-sm text-gray-600">
                  Mean: {param.mean.toFixed(2)} ± {param.std_dev.toFixed(2)}
                </div>
              </div>
              <div className="text-right">
                <div className="text-xs text-gray-500">CV</div>
                <div className={`text-sm font-semibold ${param.is_stable ? 'text-green-600' : 'text-red-600'
                  }`}>
                  {param.coefficient_of_variation.toFixed(2)}
                </div>
              </div>
              <div className="ml-3">
                {param.is_stable ? (
                  <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded">Stable</span>
                ) : (
                  <span className="px-2 py-1 bg-red-100 text-red-700 text-xs rounded">Unstable</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
