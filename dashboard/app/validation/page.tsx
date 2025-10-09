/**
 * Validation Dashboard Page - Story 11.8, Task 1
 *
 * Main validation dashboard showing metrics, alerts, and reports
 */

'use client';

import React, { useState, useEffect } from 'react';
import MainLayout from '@/components/layout/MainLayout';
import { OverfittingScoreGauge } from '@/components/validation/OverfittingScoreGauge';
import { PerformanceComparisonChart } from '@/components/validation/PerformanceComparisonChart';
import { SharpeRatioTrendChart } from '@/components/validation/SharpeRatioTrendChart';
import { ParameterHistoryTimeline } from '@/components/validation/ParameterHistoryTimeline';
import { WalkForwardReportViewer } from '@/components/validation/WalkForwardReportViewer';
import { AlertDashboard } from '@/components/validation/AlertDashboard';
import { useValidationMetrics } from '@/hooks/useValidationMetrics';
import { useParameterHistory } from '@/hooks/useParameterHistory';
import { useWalkForwardReports } from '@/hooks/useWalkForwardReports';
import { useValidationAlerts } from '@/hooks/useValidationAlerts';
import { exportWalkForwardReportToPDF } from '@/lib/pdf-export';
import type { WalkForwardReport } from '@/types/validation';

export default function ValidationDashboardPage() {
  const [activeTab, setActiveTab] = useState<'overview' | 'history' | 'reports' | 'alerts'>('overview');
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [selectedReport, setSelectedReport] = useState<WalkForwardReport | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Data hooks with auto-refresh
  const { metrics, loading: metricsLoading, error: metricsError, lastUpdated } = useValidationMetrics({
    autoRefresh,
    refreshInterval: 60000, // 60 seconds
  });

  const { versions, loading: versionsLoading, error: versionsError } = useParameterHistory({
    limit: 10,
    autoRefresh: false,
  });

  const {
    reports,
    loading: reportsLoading,
    error: reportsError,
    fetchReportDetail,
  } = useWalkForwardReports({
    limit: 20,
    autoRefresh,
    refreshInterval: 30000, // 30 seconds
  });

  const {
    alerts,
    loading: alertsLoading,
    error: alertsError,
    acknowledgeAlert,
    dismissAlert,
  } = useValidationAlerts({
    limit: 50,
    autoRefresh,
    refreshInterval: 15000, // 15 seconds
  });

  // Fetch selected report details
  useEffect(() => {
    if (selectedReportId) {
      fetchReportDetail(selectedReportId).then((report) => {
        setSelectedReport(report);
      });
    }
  }, [selectedReportId, fetchReportDetail]);

  // Mock data for charts (replace with actual API data)
  const performanceComparison = [
    { metric: 'Sharpe Ratio', live_value: metrics?.live_sharpe || 0, backtest_value: metrics?.backtest_sharpe || 0, deviation_pct: ((metrics?.sharpe_ratio || 1) - 1) * 100 },
    { metric: 'Win Rate', live_value: 0.62, backtest_value: 0.68, deviation_pct: -8.8 },
    { metric: 'Profit Factor', live_value: 1.85, backtest_value: 2.1, deviation_pct: -11.9 },
  ];

  const sharpeHistory = Array.from({ length: 30 }, (_, i) => ({
    date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toISOString(),
    sharpe: 1.2 + Math.random() * 0.4 - 0.2,
    target: 1.0,
  }));

  const handleExportPDF = async () => {
    if (selectedReport) {
      try {
        await exportWalkForwardReportToPDF(selectedReport, {
          includeCharts: true,
          includeDetailedWindows: true,
          format: 'portrait',
        });
      } catch (error) {
        console.error('Failed to export PDF:', error);
        alert('Failed to export PDF. Please try again.');
      }
    }
  };

  return (
    <MainLayout>
      <div className="container mx-auto px-4 py-6 max-w-7xl">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Validation Dashboard</h1>
            <p className="text-gray-500 mt-1">
              Monitor overfitting, performance, and parameter changes
            </p>
          </div>

          <div className="flex items-center space-x-4 mt-4 sm:mt-0">
            {/* Auto-refresh toggle */}
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Auto-refresh</span>
            </label>

            {/* Last updated */}
            {lastUpdated && (
              <span className="text-xs text-gray-500">
                Updated: {lastUpdated.toLocaleTimeString()}
              </span>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="flex space-x-8">
            {[
              { id: 'overview', label: 'Overview' },
              { id: 'history', label: 'Parameter History' },
              { id: 'reports', label: 'Validation Reports' },
              { id: 'alerts', label: 'Alerts', badge: alerts.filter(a => !a.acknowledged).length },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors relative ${activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
              >
                {tab.label}
                {tab.badge !== undefined && tab.badge > 0 && (
                  <span className="absolute -top-1 -right-2 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                    {tab.badge > 9 ? '9+' : tab.badge}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        {/* Content based on active tab */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Top row: Overfitting Score and Performance Comparison */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <OverfittingScoreGauge
                score={metrics?.overfitting_score || 0}
                loading={metricsLoading}
              />
              <PerformanceComparisonChart
                metrics={performanceComparison}
                loading={metricsLoading}
              />
            </div>

            {/* Second row: Sharpe Ratio Trend */}
            <SharpeRatioTrendChart
              data={sharpeHistory}
              targetSharpe={1.0}
              loading={metricsLoading}
            />

            {/* Third row: Recent Alerts */}
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Alerts</h3>
              <AlertDashboard
                alerts={alerts.slice(0, 5)}
                loading={alertsLoading}
                onAcknowledge={async (id) => { await acknowledgeAlert(id); }}
                onDismiss={async (id) => { await dismissAlert(id); }}
              />
            </div>
          </div>
        )}

        {activeTab === 'history' && (
          <ParameterHistoryTimeline
            versions={versions}
            loading={versionsLoading}
            onVersionClick={(version) => {
              console.log('Version clicked:', version);
            }}
          />
        )}

        {activeTab === 'reports' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Reports list */}
            <div className="lg:col-span-1">
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="font-semibold text-gray-900 mb-4">Validation Jobs</h3>
                <div className="space-y-2 max-h-[600px] overflow-y-auto">
                  {reportsLoading ? (
                    <div className="text-center py-8 text-gray-500">Loading...</div>
                  ) : reports.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">No reports found</div>
                  ) : (
                    reports.map((report) => (
                      <button
                        key={report.job_id}
                        onClick={() => setSelectedReportId(report.job_id)}
                        className={`w-full text-left p-3 rounded-lg transition-colors ${selectedReportId === report.job_id
                            ? 'bg-blue-50 border border-blue-200'
                            : 'bg-gray-50 hover:bg-gray-100'
                          }`}
                      >
                        <div className="font-medium text-sm text-gray-900">
                          {report.job_id.substring(0, 8)}...
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          {new Date(report.started_at).toLocaleDateString()}
                        </div>
                        <div className={`text-xs mt-1 ${report.status === 'APPROVED' ? 'text-green-600' :
                            report.status === 'REJECTED' ? 'text-red-600' :
                              'text-yellow-600'
                          }`}>
                          {report.status}
                        </div>
                      </button>
                    ))
                  )}
                </div>
              </div>
            </div>

            {/* Report viewer */}
            <div className="lg:col-span-2">
              <WalkForwardReportViewer
                report={selectedReport}
                loading={selectedReportId !== null && !selectedReport}
                onExportPDF={handleExportPDF}
              />
            </div>
          </div>
        )}

        {activeTab === 'alerts' && (
          <AlertDashboard
            alerts={alerts}
            loading={alertsLoading}
            onAcknowledge={async (id) => { await acknowledgeAlert(id); }}
            onDismiss={async (id) => { await dismissAlert(id); }}
          />
        )}

        {/* Error messages */}
        {(metricsError || versionsError || reportsError || alertsError) && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800">
              ⚠️ Error loading data: {metricsError || versionsError || reportsError || alertsError}
            </p>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
