'use client'

import { useState } from 'react'
import { PerformanceReport, AnalyticsFilters, ExportOptions } from '@/types/analytics'

/**
 * Props for ReportExporter component
 */
interface ReportExporterProps {
  /** Performance report data */
  performanceReport?: PerformanceReport
  /** Current analytics filters */
  filters: AnalyticsFilters
  /** Callback when export is requested */
  onExport?: (filters: AnalyticsFilters, format: 'pdf' | 'csv' | 'excel' | 'json') => void
  /** Loading state */
  loading?: boolean
  /** Error message */
  error?: string
}

/**
 * Report generation and export component
 * Provides comprehensive report creation with multiple formats and customization
 */
export function ReportExporter({
  performanceReport,
  filters,
  onExport,
  loading = false,
  error
}: ReportExporterProps) {
  const [selectedTemplate, setSelectedTemplate] = useState<'standard' | 'detailed' | 'executive' | 'regulatory'>('standard')
  const [exportOptions, setExportOptions] = useState<ExportOptions>({
    format: 'pdf',
    includeCharts: true,
    includeRawData: false,
    orientation: 'portrait',
    chartResolution: 'high'
  })
  const [customization, setCustomization] = useState({
    companyName: 'Trading Performance Report',
    reportTitle: 'Performance Analytics Report',
    includeDisclaimer: true,
    includeLogo: false,
    customFooter: '',
    watermark: ''
  })
  const [scheduledReport, setScheduledReport] = useState({
    enabled: false,
    frequency: 'weekly' as 'daily' | 'weekly' | 'monthly',
    dayOfWeek: 1, // Monday
    time: '09:00',
    recipients: [] as string[]
  })
  const [emailRecipient, setEmailRecipient] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)

  // Report templates configuration
  const templates = [
    {
      id: 'standard',
      name: 'Standard Report',
      description: 'Comprehensive performance overview with key metrics',
      pages: 8,
      includes: ['Portfolio Overview', 'Account Comparison', 'Risk Analysis', 'Trade Summary'],
      icon: '📊'
    },
    {
      id: 'detailed',
      name: 'Detailed Analysis',
      description: 'In-depth analysis with pattern breakdowns and timing data',
      pages: 15,
      includes: ['All Standard', 'Pattern Analysis', 'Time Breakdown', 'Correlation Matrix'],
      icon: '📈'
    },
    {
      id: 'executive',
      name: 'Executive Summary',
      description: 'High-level summary focused on key performance indicators',
      pages: 4,
      includes: ['Key Metrics', 'Performance Trends', 'Risk Summary', 'Recommendations'],
      icon: '👔'
    },
    {
      id: 'regulatory',
      name: 'Regulatory Compliance',
      description: 'Comprehensive report meeting regulatory requirements',
      pages: 20,
      includes: ['All Detailed', 'Compliance Metrics', 'Risk Disclosures', 'Audit Trail'],
      icon: '⚖️'
    }
  ]

  // Generate sample report data for preview
  const generatePreviewData = () => {
    if (!performanceReport) return null

    const { aggregateMetrics, accountComparisons } = performanceReport
    
    return {
      reportId: `RPT-${Date.now()}`,
      generatedAt: new Date(),
      accountCount: accountComparisons.length,
      dateRange: `${filters.dateRange.start.toLocaleDateString()} - ${filters.dateRange.end.toLocaleDateString()}`,
      totalPnL: aggregateMetrics.totalPnL,
      totalReturn: aggregateMetrics.totalReturn,
      winRate: aggregateMetrics.winRate,
      sharpeRatio: aggregateMetrics.sharpeRatio,
      maxDrawdown: aggregateMetrics.maxDrawdownPercent
    }
  }

  const previewData = generatePreviewData()

  // Handle export
  const handleExport = () => {
    if (onExport) {
      onExport(filters, exportOptions.format)
    }
  }

  // Add email recipient
  const addEmailRecipient = () => {
    if (emailRecipient.trim() && !scheduledReport.recipients.includes(emailRecipient.trim())) {
      setScheduledReport(prev => ({
        ...prev,
        recipients: [...prev.recipients, emailRecipient.trim()]
      }))
      setEmailRecipient('')
    }
  }

  // Remove email recipient
  const removeEmailRecipient = (email: string) => {
    setScheduledReport(prev => ({
      ...prev,
      recipients: prev.recipients.filter(r => r !== email)
    }))
  }

  // Format currency
  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      signDisplay: amount !== 0 ? 'always' : 'never'
    }).format(amount)
  }

  // Format percentage
  const formatPercentage = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'percent',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      signDisplay: value !== 0 ? 'always' : 'never'
    }).format(value / 100)
  }

  // Loading state
  if (loading) {
    return (
      <div className="bg-gray-750 rounded-lg p-8 text-center">
        <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
        <div className="text-white font-medium">Generating Report...</div>
        <div className="text-gray-400 text-sm mt-2">This may take a few moments</div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-6">
        <div className="text-red-400 font-medium">Report Generation Error</div>
        <div className="text-red-200 text-sm mt-1">{error}</div>
      </div>
    )
  }

  // No data state
  if (!performanceReport || !previewData) {
    return (
      <div className="bg-gray-750 rounded-lg p-8 text-center">
        <div className="text-gray-400 text-lg">No Data Available for Report</div>
        <div className="text-gray-500 text-sm mt-2">
          Configure analytics filters and generate performance data first
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold text-white mb-2">Report Generator</h3>
        <p className="text-gray-400 text-sm">
          Generate comprehensive performance reports in multiple formats
        </p>
      </div>

      {/* Report Templates */}
      <div>
        <h4 className="text-white font-medium mb-4">Select Report Template</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {templates.map((template) => (
            <div
              key={template.id}
              onClick={() => setSelectedTemplate(template.id as typeof selectedTemplate)}
              className={`
                bg-gray-750 rounded-lg p-6 border cursor-pointer transition-all
                ${selectedTemplate === template.id ? 'border-blue-500 ring-2 ring-blue-500/20' : 'border-gray-700 hover:border-gray-600'}
              `}
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="text-2xl">{template.icon}</div>
                <div>
                  <h5 className="text-white font-medium">{template.name}</h5>
                  <div className="text-gray-400 text-sm">{template.pages} pages</div>
                </div>
              </div>
              
              <p className="text-gray-300 text-sm mb-3">{template.description}</p>
              
              <div className="space-y-1">
                <div className="text-gray-400 text-xs font-medium">Includes:</div>
                {template.includes.map((item, index) => (
                  <div key={index} className="text-gray-500 text-xs">
                    • {item}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Export Options */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Format and Options */}
        <div className="bg-gray-750 rounded-lg p-6">
          <h4 className="text-white font-medium mb-4">Export Options</h4>
          
          <div className="space-y-4">
            {/* Format Selection */}
            <div>
              <label className="block text-gray-300 text-sm mb-2">Export Format</label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => setExportOptions(prev => ({ ...prev, format: 'pdf' }))}
                  className={`
                    px-4 py-3 rounded border transition-colors
                    ${exportOptions.format === 'pdf' 
                      ? 'border-blue-500 bg-blue-900/20 text-blue-400' 
                      : 'border-gray-600 bg-gray-700 text-gray-300 hover:border-gray-500'
                    }
                  `}
                >
                  <div className="text-lg mb-1">📄</div>
                  <div className="font-medium">PDF Report</div>
                  <div className="text-xs opacity-75">Professional format</div>
                </button>
                
                <button
                  onClick={() => setExportOptions(prev => ({ ...prev, format: 'csv' }))}
                  className={`
                    px-4 py-3 rounded border transition-colors
                    ${exportOptions.format === 'csv' 
                      ? 'border-blue-500 bg-blue-900/20 text-blue-400' 
                      : 'border-gray-600 bg-gray-700 text-gray-300 hover:border-gray-500'
                    }
                  `}
                >
                  <div className="text-lg mb-1">📊</div>
                  <div className="font-medium">CSV Data</div>
                  <div className="text-xs opacity-75">Raw data export</div>
                </button>
              </div>
            </div>

            {/* PDF Options */}
            {exportOptions.format === 'pdf' && (
              <>
                <div>
                  <label className="block text-gray-300 text-sm mb-2">Page Orientation</label>
                  <select
                    value={exportOptions.orientation}
                    onChange={(e) => setExportOptions(prev => ({ 
                      ...prev, 
                      orientation: e.target.value as 'portrait' | 'landscape' 
                    }))}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                  >
                    <option value="portrait">Portrait</option>
                    <option value="landscape">Landscape</option>
                  </select>
                </div>

                <div>
                  <label className="block text-gray-300 text-sm mb-2">Chart Resolution</label>
                  <select
                    value={exportOptions.chartResolution}
                    onChange={(e) => setExportOptions(prev => ({ 
                      ...prev, 
                      chartResolution: e.target.value as 'low' | 'medium' | 'high' 
                    }))}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                  >
                    <option value="low">Low (Fast)</option>
                    <option value="medium">Medium</option>
                    <option value="high">High (Best Quality)</option>
                  </select>
                </div>
              </>
            )}

            {/* Include Options */}
            <div className="space-y-2">
              <div className="text-gray-300 text-sm font-medium">Include in Export</div>
              
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={exportOptions.includeCharts}
                  onChange={(e) => setExportOptions(prev => ({ 
                    ...prev, 
                    includeCharts: e.target.checked 
                  }))}
                  className="rounded border-gray-600 bg-gray-700 text-blue-600"
                />
                <span className="text-gray-300 text-sm">Charts and Visualizations</span>
              </label>
              
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={exportOptions.includeRawData}
                  onChange={(e) => setExportOptions(prev => ({ 
                    ...prev, 
                    includeRawData: e.target.checked 
                  }))}
                  className="rounded border-gray-600 bg-gray-700 text-blue-600"
                />
                <span className="text-gray-300 text-sm">Raw Trade Data</span>
              </label>
            </div>
          </div>
        </div>

        {/* Report Preview */}
        <div className="bg-gray-750 rounded-lg p-6">
          <h4 className="text-white font-medium mb-4">Report Preview</h4>
          
          <div className="space-y-4">
            <div className="bg-gray-800 rounded p-4">
              <div className="text-center mb-4">
                <h5 className="text-white font-bold text-lg">{customization.reportTitle}</h5>
                <div className="text-gray-400 text-sm">{customization.companyName}</div>
                <div className="text-gray-500 text-xs mt-1">
                  Generated: {new Date().toLocaleDateString()}
                </div>
              </div>
              
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Report ID:</span>
                  <span className="text-white font-mono">{previewData.reportId}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Date Range:</span>
                  <span className="text-white">{previewData.dateRange}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Accounts:</span>
                  <span className="text-white">{previewData.accountCount}</span>
                </div>
                
                <div className="border-t border-gray-600 pt-3 mt-3">
                  <div className="text-gray-300 font-medium mb-2">Key Metrics</div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Total P&L:</span>
                      <span className={`font-medium ${previewData.totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatCurrency(previewData.totalPnL)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Return:</span>
                      <span className={`font-medium ${previewData.totalReturn >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatPercentage(previewData.totalReturn)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Win Rate:</span>
                      <span className="text-white font-medium">
                        {formatPercentage(previewData.winRate)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Sharpe:</span>
                      <span className="text-white font-medium">
                        {previewData.sharpeRatio.toFixed(2)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="text-xs text-gray-500">
              * This is a preview. Actual report will contain all selected data and formatting.
            </div>
          </div>
        </div>
      </div>

      {/* Advanced Options */}
      <div className="bg-gray-750 rounded-lg p-6">
        <div className="flex justify-between items-center mb-4">
          <h4 className="text-white font-medium">Advanced Options</h4>
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-blue-400 hover:text-blue-300 text-sm transition-colors"
          >
            {showAdvanced ? 'Hide' : 'Show'} Advanced
          </button>
        </div>

        {showAdvanced && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Customization */}
            <div className="space-y-4">
              <h5 className="text-gray-300 font-medium">Report Customization</h5>
              
              <div>
                <label className="block text-gray-400 text-sm mb-1">Report Title</label>
                <input
                  type="text"
                  value={customization.reportTitle}
                  onChange={(e) => setCustomization(prev => ({ ...prev, reportTitle: e.target.value }))}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
                />
              </div>

              <div>
                <label className="block text-gray-400 text-sm mb-1">Company/Organization</label>
                <input
                  type="text"
                  value={customization.companyName}
                  onChange={(e) => setCustomization(prev => ({ ...prev, companyName: e.target.value }))}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
                />
              </div>

              <div>
                <label className="block text-gray-400 text-sm mb-1">Custom Footer</label>
                <input
                  type="text"
                  value={customization.customFooter}
                  onChange={(e) => setCustomization(prev => ({ ...prev, customFooter: e.target.value }))}
                  placeholder="Optional footer text"
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
                />
              </div>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={customization.includeDisclaimer}
                  onChange={(e) => setCustomization(prev => ({ 
                    ...prev, 
                    includeDisclaimer: e.target.checked 
                  }))}
                  className="rounded border-gray-600 bg-gray-700 text-blue-600"
                />
                <span className="text-gray-300 text-sm">Include Trading Disclaimer</span>
              </label>
            </div>

            {/* Scheduled Reports */}
            <div className="space-y-4">
              <h5 className="text-gray-300 font-medium">Scheduled Reports</h5>
              
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={scheduledReport.enabled}
                  onChange={(e) => setScheduledReport(prev => ({ 
                    ...prev, 
                    enabled: e.target.checked 
                  }))}
                  className="rounded border-gray-600 bg-gray-700 text-blue-600"
                />
                <span className="text-gray-300 text-sm">Enable Automated Reports</span>
              </label>

              {scheduledReport.enabled && (
                <div className="space-y-3 ml-6 border-l-2 border-gray-600 pl-4">
                  <div>
                    <label className="block text-gray-400 text-sm mb-1">Frequency</label>
                    <select
                      value={scheduledReport.frequency}
                      onChange={(e) => setScheduledReport(prev => ({ 
                        ...prev, 
                        frequency: e.target.value as typeof scheduledReport.frequency 
                      }))}
                      className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
                    >
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="monthly">Monthly</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-gray-400 text-sm mb-1">Send Time</label>
                    <input
                      type="time"
                      value={scheduledReport.time}
                      onChange={(e) => setScheduledReport(prev => ({ 
                        ...prev, 
                        time: e.target.value 
                      }))}
                      className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
                    />
                  </div>

                  <div>
                    <label className="block text-gray-400 text-sm mb-1">Email Recipients</label>
                    <div className="flex gap-2">
                      <input
                        type="email"
                        value={emailRecipient}
                        onChange={(e) => setEmailRecipient(e.target.value)}
                        placeholder="Enter email address"
                        className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
                      />
                      <button
                        onClick={addEmailRecipient}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded text-sm transition-colors"
                      >
                        Add
                      </button>
                    </div>
                    
                    {scheduledReport.recipients.length > 0 && (
                      <div className="mt-2 space-y-1">
                        {scheduledReport.recipients.map((email) => (
                          <div key={email} className="flex justify-between items-center bg-gray-700 rounded px-2 py-1">
                            <span className="text-gray-300 text-sm">{email}</span>
                            <button
                              onClick={() => removeEmailRecipient(email)}
                              className="text-red-400 hover:text-red-300 text-sm"
                            >
                              ✕
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Export Actions */}
      <div className="flex justify-between items-center">
        <div className="text-gray-400 text-sm">
          Report will be generated based on current filters and selected options
        </div>
        
        <div className="flex gap-3">
          <button
            onClick={handleExport}
            disabled={!performanceReport}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white px-6 py-3 rounded font-medium transition-colors"
          >
            📥 Generate & Export Report
          </button>
          
          <button
            onClick={() => {
              // Handle preview functionality
              console.log('Preview report:', { selectedTemplate, exportOptions, customization })
            }}
            disabled={!performanceReport}
            className="bg-gray-700 hover:bg-gray-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white px-6 py-3 rounded font-medium transition-colors"
          >
            👁️ Preview
          </button>
        </div>
      </div>
    </div>
  )
}