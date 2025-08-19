/**
 * Compliance Report Generator Component - AC5
 * Story 9.6: Exportable reports for compliance and performance review meetings
 * 
 * Generate and export comprehensive compliance reports in multiple formats
 */

'use client'

import React, { useState, useCallback, useMemo } from 'react'
import {
  FileText,
  Download,
  Calendar,
  Shield,
  AlertTriangle,
  CheckCircle,
  Settings,
  Mail,
  Eye,
  Clock,
  Users,
  BarChart3
} from 'lucide-react'
import { motion } from 'framer-motion'
import { ComplianceReport, ExportConfig, AuditEntry, RegulatoryMetrics } from '@/types/performanceAnalytics'
import { performanceAnalyticsService } from '@/services/performanceAnalyticsService'
import { formatCurrency, formatPercent, formatNumber } from '@/utils/formatters'

interface ComplianceReportGeneratorProps {
  accountIds: string[]
  onReportGenerated?: (report: ComplianceReport) => void
}

type ReportType = 'standard' | 'detailed' | 'executive' | 'regulatory'
type ExportFormat = 'pdf' | 'csv' | 'excel' | 'json'

export default function ComplianceReportGenerator({
  accountIds,
  onReportGenerated
}: ComplianceReportGeneratorProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reportType, setReportType] = useState<ReportType>('standard')
  const [dateRange, setDateRange] = useState({
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // 30 days ago
    end: new Date()
  })
  const [exportConfig, setExportConfig] = useState<ExportConfig>({
    format: 'pdf',
    includeCharts: true,
    includeRawData: false,
    includeAnalysis: true,
    chartResolution: 'medium',
    dateFormat: 'MM/DD/YYYY',
    numberFormat: 'en-US',
    currency: 'USD',
    timezone: 'UTC',
    compression: false,
    encryption: false
  })
  const [scheduledReports, setScheduledReports] = useState<any[]>([])
  const [currentReport, setCurrentReport] = useState<ComplianceReport | null>(null)
  const [previewMode, setPreviewMode] = useState(false)

  // Generate compliance report - integrates with audit trail system for AuditEntry tracking
  const generateReport = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const report = await performanceAnalyticsService.generateComplianceReport(
        accountIds,
        dateRange,
        reportType
      )
      
      // Report includes auditTrail with AuditEntry records and RegulatoryMetrics
      setCurrentReport(report)
      onReportGenerated?.(report)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate report')
    } finally {
      setLoading(false)
    }
  }, [accountIds, dateRange, reportType, onReportGenerated])

  // Export report
  const exportReport = useCallback(async (format: ExportFormat) => {
    if (!currentReport) return

    try {
      const blob = await performanceAnalyticsService.exportReport(currentReport, format)
      
      // Create download link
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `compliance-report-${currentReport.reportId}.${format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export report')
    }
  }, [currentReport])

  // Report configuration templates
  const reportTemplates = useMemo(() => ({
    standard: {
      name: 'Standard Report',
      description: 'Basic compliance metrics and performance summary',
      includes: ['Account overview', 'P&L summary', 'Key violations', 'Risk metrics'],
      duration: '2-3 minutes'
    },
    detailed: {
      name: 'Detailed Report',
      description: 'Comprehensive analysis with trade-by-trade breakdown',
      includes: ['Full trade history', 'Agent performance', 'Risk analysis', 'Audit trail'],
      duration: '5-8 minutes'
    },
    executive: {
      name: 'Executive Summary',
      description: 'High-level overview for executive review',
      includes: ['Key performance indicators', 'Risk summary', 'Recommendations'],
      duration: '1-2 minutes'
    },
    regulatory: {
      name: 'Regulatory Compliance',
      description: 'Comprehensive report for regulatory submission',
      includes: ['Full compliance audit', 'Regulatory metrics', 'Signed attestation'],
      duration: '10-15 minutes'
    }
  }), [])

  // Report statistics
  const reportStats = useMemo(() => {
    if (!currentReport) return null

    const totalAccounts = currentReport.accounts.length
    const totalViolations = currentReport.violations.length
    const criticalViolations = currentReport.violations.filter(v => v.severity === 'critical').length
    const totalTrades = currentReport.aggregateMetrics.totalTrades
    const avgViolationsPerAccount = totalViolations / Math.max(totalAccounts, 1)

    return {
      totalAccounts,
      totalViolations,
      criticalViolations,
      totalTrades,
      avgViolationsPerAccount,
      complianceScore: Math.max(0, 100 - (criticalViolations * 10) - (totalViolations * 2))
    }
  }, [currentReport])

  return (
    <div className="bg-gray-900 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-gray-800">
        <div className="flex items-center gap-3 mb-4">
          <FileText className="w-6 h-6 text-blue-400" />
          <h2 className="text-xl font-semibold text-white">Compliance Report Generator</h2>
          {currentReport && (
            <div className="flex items-center gap-2 ml-auto">
              <span className="text-sm text-gray-400">Report ID:</span>
              <code className="px-2 py-1 bg-gray-800 text-green-400 rounded text-sm font-mono">
                {currentReport.reportId}
              </code>
            </div>
          )}
        </div>

        {/* Configuration */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Report Type */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Report Type</label>
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value as ReportType)}
              className="w-full px-3 py-2 bg-gray-800 text-white rounded border border-gray-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            >
              {Object.entries(reportTemplates).map(([key, template]) => (
                <option key={key} value={key}>{template.name}</option>
              ))}
            </select>
          </div>

          {/* Date Range */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Start Date</label>
            <input
              type="date"
              value={dateRange.start.toISOString().split('T')[0]}
              onChange={(e) => setDateRange(prev => ({ ...prev, start: new Date(e.target.value) }))}
              className="w-full px-3 py-2 bg-gray-800 text-white rounded border border-gray-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">End Date</label>
            <input
              type="date"
              value={dateRange.end.toISOString().split('T')[0]}
              onChange={(e) => setDateRange(prev => ({ ...prev, end: new Date(e.target.value) }))}
              className="w-full px-3 py-2 bg-gray-800 text-white rounded border border-gray-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Generate Button */}
          <div className="flex items-end">
            <button
              onClick={generateReport}
              disabled={loading}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <div className="flex items-center justify-center gap-2">
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  Generating...
                </div>
              ) : (
                'Generate Report'
              )}
            </button>
          </div>
        </div>

        {/* Template Description */}
        <div className="mt-4 p-4 bg-gray-800/50 rounded-lg">
          <div className="flex items-start gap-3">
            <Settings className="w-5 h-5 text-blue-400 mt-0.5" />
            <div>
              <h3 className="text-sm font-medium text-white mb-1">
                {reportTemplates[reportType].name}
              </h3>
              <p className="text-sm text-gray-400 mb-2">
                {reportTemplates[reportType].description}
              </p>
              <div className="flex items-center gap-4 text-xs text-gray-500">
                <div className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  Est. {reportTemplates[reportType].duration}
                </div>
                <div className="flex items-center gap-1">
                  <Users className="w-3 h-3" />
                  {accountIds.length} accounts
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-900/20 border-l-4 border-red-500">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-400" />
            <span className="text-red-400">{error}</span>
          </div>
        </div>
      )}

      {/* Report Content */}
      {currentReport && (
        <div className="p-6">
          {/* Report Statistics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-gray-800 rounded-lg p-4"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400 text-sm">Compliance Score</span>
                <Shield className="w-4 h-4 text-gray-500" />
              </div>
              <div className={`text-2xl font-bold ${
                reportStats!.complianceScore >= 90 ? 'text-green-400' :
                reportStats!.complianceScore >= 70 ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {reportStats!.complianceScore}
              </div>
              <div className="text-xs text-gray-500">
                Out of 100
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="bg-gray-800 rounded-lg p-4"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400 text-sm">Total P&L</span>
                <BarChart3 className="w-4 h-4 text-gray-500" />
              </div>
              <div className={`text-2xl font-bold ${
                currentReport.aggregateMetrics.totalPnL >= 0 ? 'text-green-400' : 'text-red-400'
              }`}>
                {formatCurrency(currentReport.aggregateMetrics.totalPnL)}
              </div>
              <div className="text-xs text-gray-500">
                Across all accounts
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-gray-800 rounded-lg p-4"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400 text-sm">Violations</span>
                <AlertTriangle className="w-4 h-4 text-gray-500" />
              </div>
              <div className={`text-2xl font-bold ${
                reportStats!.criticalViolations > 0 ? 'text-red-400' :
                reportStats!.totalViolations > 0 ? 'text-yellow-400' : 'text-green-400'
              }`}>
                {reportStats!.totalViolations}
              </div>
              <div className="text-xs text-gray-500">
                {reportStats!.criticalViolations} critical
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="bg-gray-800 rounded-lg p-4"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400 text-sm">Total Trades</span>
                <BarChart3 className="w-4 h-4 text-gray-500" />
              </div>
              <div className="text-2xl font-bold text-white">
                {reportStats!.totalTrades.toLocaleString()}
              </div>
              <div className="text-xs text-gray-500">
                {formatNumber(reportStats!.avgViolationsPerAccount, 1)} violations/account
              </div>
            </motion.div>
          </div>

          {/* Account Summary */}
          <div className="mb-6">
            <h3 className="text-lg font-medium text-white mb-4">Account Summary</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800">
                    <th className="text-left p-3 font-medium text-gray-400">Account</th>
                    <th className="text-right p-3 font-medium text-gray-400">Start Balance</th>
                    <th className="text-right p-3 font-medium text-gray-400">End Balance</th>
                    <th className="text-right p-3 font-medium text-gray-400">Return</th>
                    <th className="text-right p-3 font-medium text-gray-400">Max Drawdown</th>
                    <th className="text-center p-3 font-medium text-gray-400">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {currentReport.accounts.map((account, index) => (
                    <tr key={account.accountId} className="border-b border-gray-800/50">
                      <td className="p-3">
                        <div>
                          <div className="font-medium text-white">{account.accountId}</div>
                          <div className="text-xs text-gray-400">{account.propFirm}</div>
                        </div>
                      </td>
                      <td className="p-3 text-right font-medium text-white">
                        {formatCurrency(account.startBalance)}
                      </td>
                      <td className="p-3 text-right font-medium text-white">
                        {formatCurrency(account.endBalance)}
                      </td>
                      <td className="p-3 text-right">
                        <span className={`font-medium ${
                          account.totalReturn >= 0 ? 'text-green-400' : 'text-red-400'
                        }`}>
                          {formatPercent(account.totalReturn)}
                        </span>
                      </td>
                      <td className="p-3 text-right">
                        <span className={`font-medium ${
                          account.maxDrawdown > 10 ? 'text-red-400' :
                          account.maxDrawdown > 5 ? 'text-yellow-400' : 'text-green-400'
                        }`}>
                          {formatPercent(account.maxDrawdown)}
                        </span>
                      </td>
                      <td className="p-3 text-center">
                        <div className="flex items-center justify-center gap-1">
                          {account.rulesViolated.length === 0 ? (
                            <CheckCircle className="w-4 h-4 text-green-400" />
                          ) : (
                            <AlertTriangle className="w-4 h-4 text-red-400" />
                          )}
                          <span className={`text-xs ${
                            account.rulesViolated.length === 0 ? 'text-green-400' : 'text-red-400'
                          }`}>
                            {account.rulesViolated.length === 0 ? 'Clean' : `${account.rulesViolated.length} issues`}
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Export Options */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h3 className="text-lg font-medium text-white">Export Report</h3>
              <div className="text-sm text-gray-400">
                Generated: {new Date(currentReport.generatedAt).toLocaleString()}
              </div>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => setPreviewMode(!previewMode)}
                className="flex items-center gap-2 px-3 py-2 bg-gray-800 text-gray-300 rounded hover:bg-gray-700 transition-colors"
              >
                <Eye className="w-4 h-4" />
                {previewMode ? 'Hide Preview' : 'Preview'}
              </button>

              {(['pdf', 'excel', 'csv', 'json'] as ExportFormat[]).map(format => (
                <button
                  key={format}
                  onClick={() => exportReport(format)}
                  className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                >
                  <Download className="w-4 h-4" />
                  {format.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          {/* Report Preview */}
          {previewMode && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-6 p-6 bg-white text-black rounded-lg"
            >
              <div className="text-center mb-6">
                <h1 className="text-2xl font-bold mb-2">Compliance Report</h1>
                <p className="text-gray-600">
                  Period: {dateRange.start.toLocaleDateString()} - {dateRange.end.toLocaleDateString()}
                </p>
                <p className="text-sm text-gray-500">
                  Report ID: {currentReport.reportId} | Generated: {new Date().toLocaleString()}
                </p>
              </div>

              <div className="space-y-6">
                <div>
                  <h2 className="text-xl font-semibold mb-3">Executive Summary</h2>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <strong>Total P&L:</strong> {formatCurrency(currentReport.aggregateMetrics.totalPnL)}
                    </div>
                    <div>
                      <strong>Compliance Score:</strong> {reportStats!.complianceScore}/100
                    </div>
                    <div>
                      <strong>Total Trades:</strong> {currentReport.aggregateMetrics.totalTrades.toLocaleString()}
                    </div>
                    <div>
                      <strong>Violations:</strong> {currentReport.violations.length}
                    </div>
                  </div>
                </div>

                <div>
                  <h2 className="text-xl font-semibold mb-3">Risk Metrics</h2>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <strong>Max Drawdown:</strong> {formatPercent(currentReport.aggregateMetrics.maxDrawdown)}
                    </div>
                    <div>
                      <strong>Peak Exposure:</strong> {formatCurrency(currentReport.aggregateMetrics.peakExposure)}
                    </div>
                  </div>
                </div>

                <div>
                  <h2 className="text-xl font-semibold mb-3">Regulatory Compliance</h2>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <strong>MiFID Compliant:</strong> {currentReport.regulatoryMetrics.mifidCompliant ? '✓' : '✗'}
                    </div>
                    <div>
                      <strong>NFA Compliant:</strong> {currentReport.regulatoryMetrics.nfaCompliant ? '✓' : '✗'}
                    </div>
                  </div>
                </div>

                {currentReport.violations.length > 0 && (
                  <div>
                    <h2 className="text-xl font-semibold mb-3">Violations</h2>
                    <div className="space-y-2">
                      {currentReport.violations.slice(0, 5).map((violation, index) => (
                        <div key={index} className="p-3 bg-red-50 border border-red-200 rounded">
                          <div className="flex justify-between items-start">
                            <div>
                              <strong>{violation.ruleName}</strong>
                              <p className="text-sm text-gray-600">{violation.description}</p>
                            </div>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${{
                              'critical': 'bg-red-200 text-red-800',
                              'high': 'bg-orange-200 text-orange-800',
                              'medium': 'bg-yellow-200 text-yellow-800',
                              'low': 'bg-blue-200 text-blue-800'
                            }[violation.severity]}`}>
                              {violation.severity.toUpperCase()}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="text-center pt-6 border-t border-gray-300">
                  <p className="text-sm text-gray-500">
                    This report is electronically signed and timestamped.
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    Signature: {currentReport.signature}
                  </p>
                </div>
              </div>
            </motion.div>
          )}
        </div>
      )}
    </div>
  )
}