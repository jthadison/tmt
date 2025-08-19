/**
 * Audit Log Viewer Component - AC6
 * Story 9.5: Audit logging of all manual interventions with administrator identification and approval workflows
 * 
 * SECURITY: Administrator access only - comprehensive audit trail with filtering and export capabilities
 */

'use client'

import React, { useState, useMemo } from 'react'
import {
  AuditLogEntry,
  AuditAction,
  AuditResource,
  AuditLogFilter,
  ApprovalWorkflow,
  ApprovalStatus
} from '@/types/tradingControls'
import Card from '@/components/ui/Card'
import Modal from '@/components/ui/Modal'

/**
 * Props for AuditLogViewer component
 */
interface AuditLogViewerProps {
  /** Array of audit log entries */
  auditLogs: AuditLogEntry[]
  /** Array of approval workflows */
  approvalWorkflows?: ApprovalWorkflow[]
  /** Loading state */
  loading?: boolean
  /** Error message */
  error?: string
  /** Callback to refresh audit logs */
  onRefresh?: (filter?: AuditLogFilter) => void
  /** Callback to export audit data */
  onExport?: (format: 'csv' | 'json' | 'pdf', filter?: AuditLogFilter) => Promise<boolean>
}

/**
 * Audit filter component
 */
function AuditLogFilter({
  onFilterChange,
  currentFilter
}: {
  onFilterChange: (filter: AuditLogFilter) => void
  currentFilter: AuditLogFilter
}) {
  const [localFilter, setLocalFilter] = useState<AuditLogFilter>(currentFilter)

  const actionOptions: { value: AuditAction; label: string }[] = [
    { value: 'agent_control', label: 'Agent Control' },
    { value: 'emergency_stop', label: 'Emergency Stop' },
    { value: 'manual_trade', label: 'Manual Trade' },
    { value: 'parameter_modification', label: 'Parameter Modification' },
    { value: 'compliance_override', label: 'Compliance Override' },
    { value: 'system_access', label: 'System Access' },
    { value: 'data_export', label: 'Data Export' },
    { value: 'configuration_change', label: 'Configuration Change' }
  ]

  const resourceOptions: { value: AuditResource; label: string }[] = [
    { value: 'agent', label: 'Agent' },
    { value: 'system', label: 'System' },
    { value: 'trade', label: 'Trade' },
    { value: 'risk_parameter', label: 'Risk Parameter' },
    { value: 'compliance_rule', label: 'Compliance Rule' },
    { value: 'user_account', label: 'User Account' },
    { value: 'audit_log', label: 'Audit Log' }
  ]

  const handleFilterUpdate = (field: keyof AuditLogFilter, value: any) => {
    const newFilter = { ...localFilter, [field]: value === '' ? undefined : value }
    setLocalFilter(newFilter)
    onFilterChange(newFilter)
  }

  const clearFilters = () => {
    const emptyFilter: AuditLogFilter = {}
    setLocalFilter(emptyFilter)
    onFilterChange(emptyFilter)
  }

  return (
    <Card>
      <h3 className="text-lg font-semibold text-white mb-4">Filter Audit Logs</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Action Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Action</label>
          <select
            value={localFilter.action || ''}
            onChange={(e) => handleFilterUpdate('action', e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
          >
            <option value="">All Actions</option>
            {actionOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Resource Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Resource</label>
          <select
            value={localFilter.resource || ''}
            onChange={(e) => handleFilterUpdate('resource', e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
          >
            <option value="">All Resources</option>
            {resourceOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Risk Level Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Risk Level</label>
          <select
            value={localFilter.riskLevel || ''}
            onChange={(e) => handleFilterUpdate('riskLevel', e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
          >
            <option value="">All Risk Levels</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>

        {/* Date From */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Date From</label>
          <input
            type="datetime-local"
            value={localFilter.dateFrom?.toISOString().slice(0, 16) || ''}
            onChange={(e) => handleFilterUpdate('dateFrom', e.target.value ? new Date(e.target.value) : undefined)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
          />
        </div>

        {/* Date To */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Date To</label>
          <input
            type="datetime-local"
            value={localFilter.dateTo?.toISOString().slice(0, 16) || ''}
            onChange={(e) => handleFilterUpdate('dateTo', e.target.value ? new Date(e.target.value) : undefined)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
          />
        </div>

        {/* Result Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Result</label>
          <select
            value={localFilter.result || ''}
            onChange={(e) => handleFilterUpdate('result', e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
          >
            <option value="">All Results</option>
            <option value="success">Success</option>
            <option value="failure">Failure</option>
            <option value="pending">Pending</option>
          </select>
        </div>
      </div>

      <div className="flex justify-end mt-4">
        <button
          onClick={clearFilters}
          className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded text-sm"
        >
          Clear Filters
        </button>
      </div>
    </Card>
  )
}

/**
 * Individual audit log entry component
 */
function AuditLogEntryCard({
  entry,
  compact = false
}: {
  entry: AuditLogEntry
  compact?: boolean
}) {
  const [showDetails, setShowDetails] = useState(false)

  const getActionIcon = (action: AuditAction): string => {
    switch (action) {
      case 'agent_control': return '🤖'
      case 'emergency_stop': return '🚨'
      case 'manual_trade': return '💰'
      case 'parameter_modification': return '⚙️'
      case 'compliance_override': return '⚖️'
      case 'system_access': return '🔐'
      case 'data_export': return '📤'
      case 'configuration_change': return '🔧'
      default: return '📝'
    }
  }

  const getRiskLevelColor = (level: string): string => {
    switch (level) {
      case 'low': return 'text-green-400 bg-green-900/20 border-green-500/30'
      case 'medium': return 'text-yellow-400 bg-yellow-900/20 border-yellow-500/30'
      case 'high': return 'text-orange-400 bg-orange-900/20 border-orange-500/30'
      case 'critical': return 'text-red-400 bg-red-900/20 border-red-500/30'
      default: return 'text-gray-400 bg-gray-900/20 border-gray-500/30'
    }
  }

  const getResultColor = (result: string): string => {
    switch (result) {
      case 'success': return 'text-green-400'
      case 'failure': return 'text-red-400'
      case 'pending': return 'text-yellow-400'
      default: return 'text-gray-400'
    }
  }

  const getResultIcon = (result: string): string => {
    switch (result) {
      case 'success': return '✓'
      case 'failure': return '✗'
      case 'pending': return '⏳'
      default: return '?'
    }
  }

  if (compact) {
    return (
      <div className="p-3 bg-gray-800 rounded border-l-4 border-blue-500">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-lg">{getActionIcon(entry.action)}</span>
            <div>
              <div className="font-medium text-white text-sm">
                {entry.action.replace('_', ' ').toUpperCase()}
              </div>
              <div className="text-xs text-gray-400">
                {entry.userEmail} • {entry.timestamp.toLocaleString()}
              </div>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <div className={`px-2 py-1 rounded text-xs font-medium border ${getRiskLevelColor(entry.riskLevel)}`}>
              {entry.riskLevel.toUpperCase()}
            </div>
            <div className={`text-lg ${getResultColor(entry.result)}`}>
              {getResultIcon(entry.result)}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      <Card className="cursor-pointer hover:bg-gray-800/50 transition-colors" onClick={() => setShowDetails(true)}>
        <div className="space-y-4">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div className="flex items-start space-x-3">
              <span className="text-2xl">{getActionIcon(entry.action)}</span>
              <div>
                <h3 className="font-medium text-white">
                  {entry.action.replace('_', ' ').toUpperCase()} - {entry.resource.toUpperCase()}
                </h3>
                <p className="text-sm text-gray-400">Resource ID: {entry.resourceId}</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              <div className={`px-2 py-1 rounded text-xs font-medium border ${getRiskLevelColor(entry.riskLevel)}`}>
                {entry.riskLevel.toUpperCase()}
              </div>
              <div className={`text-lg ${getResultColor(entry.result)}`}>
                {getResultIcon(entry.result)}
              </div>
            </div>
          </div>

          {/* User and Time Info */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-400">Administrator:</span>
              <span className="ml-2 text-white">{entry.userEmail}</span>
            </div>
            <div>
              <span className="text-gray-400">Timestamp:</span>
              <span className="ml-2 text-white">{entry.timestamp.toLocaleString()}</span>
            </div>
          </div>

          {/* Justification */}
          <div className="p-3 bg-gray-800 rounded">
            <div className="text-gray-400 text-sm mb-1">Justification:</div>
            <div className="text-white text-sm">{entry.justification}</div>
          </div>

          {/* Approval Status */}
          {entry.approvalRequired && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-400">Approval Status:</span>
              <span className={entry.approvedBy ? 'text-green-400' : 'text-yellow-400'}>
                {entry.approvedBy ? `Approved by ${entry.approvedBy}` : 'Pending Approval'}
              </span>
            </div>
          )}

          {/* Error Message */}
          {entry.result === 'failure' && entry.errorMessage && (
            <div className="p-2 bg-red-900/20 border border-red-500/30 rounded">
              <div className="text-red-400 font-medium text-sm">Error:</div>
              <div className="text-red-300 text-sm">{entry.errorMessage}</div>
            </div>
          )}
        </div>
      </Card>

      {/* Details Modal */}
      <Modal isOpen={showDetails} onClose={() => setShowDetails(false)} size="lg">
        <div className="bg-gray-900 p-6">
          <h2 className="text-xl font-bold text-white mb-6">Audit Log Details</h2>
          
          <div className="space-y-6">
            {/* Basic Information */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Entry ID</label>
                <div className="font-mono text-white text-sm">{entry.id}</div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Session ID</label>
                <div className="font-mono text-white text-sm">{entry.sessionId}</div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Action</label>
                <div className="text-white">{entry.action.replace('_', ' ').toUpperCase()}</div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Resource</label>
                <div className="text-white">{entry.resource.toUpperCase()}</div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Risk Level</label>
                <div className={`inline-flex px-2 py-1 rounded text-xs font-medium border ${getRiskLevelColor(entry.riskLevel)}`}>
                  {entry.riskLevel.toUpperCase()}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Result</label>
                <div className={getResultColor(entry.result)}>
                  {getResultIcon(entry.result)} {entry.result.toUpperCase()}
                </div>
              </div>
            </div>

            {/* Administrator Information */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Administrator Information</label>
              <div className="p-3 bg-gray-800 rounded">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-400">Email:</span>
                    <span className="ml-2 text-white">{entry.userEmail}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">IP Address:</span>
                    <span className="ml-2 text-white font-mono">{entry.ipAddress}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Justification */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Justification</label>
              <div className="p-3 bg-gray-800 rounded">
                <div className="text-white">{entry.justification}</div>
              </div>
            </div>

            {/* Details */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Action Details</label>
              <div className="p-3 bg-gray-800 rounded">
                <pre className="text-white text-sm font-mono overflow-x-auto">
                  {JSON.stringify(entry.details, null, 2)}
                </pre>
              </div>
            </div>

            {/* Compliance Check */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Compliance Check</label>
              <div className="p-3 bg-gray-800 rounded">
                <div className="flex items-center space-x-2 mb-2">
                  <span className={entry.complianceCheck.passed ? 'text-green-400' : 'text-red-400'}>
                    {entry.complianceCheck.passed ? '✓' : '✗'}
                  </span>
                  <span className="text-white">
                    {entry.complianceCheck.passed ? 'Passed' : 'Failed'}
                  </span>
                </div>
                
                {entry.complianceCheck.violations.length > 0 && (
                  <div className="mt-2">
                    <div className="text-red-400 font-medium text-sm mb-1">Violations:</div>
                    {entry.complianceCheck.violations.map((violation, index) => (
                      <div key={index} className="text-red-300 text-sm">
                        • {violation.description}
                      </div>
                    ))}
                  </div>
                )}
                
                {entry.complianceCheck.warnings.length > 0 && (
                  <div className="mt-2">
                    <div className="text-yellow-400 font-medium text-sm mb-1">Warnings:</div>
                    {entry.complianceCheck.warnings.map((warning, index) => (
                      <div key={index} className="text-yellow-300 text-sm">
                        • {warning}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Approval Information */}
            {entry.approvalRequired && (
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Approval Information</label>
                <div className="p-3 bg-gray-800 rounded">
                  {entry.approvedBy ? (
                    <div className="space-y-1 text-sm">
                      <div>
                        <span className="text-gray-400">Approved by:</span>
                        <span className="ml-2 text-green-400">{entry.approvedBy}</span>
                      </div>
                      {entry.approvedAt && (
                        <div>
                          <span className="text-gray-400">Approved at:</span>
                          <span className="ml-2 text-white">{entry.approvedAt.toLocaleString()}</span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-yellow-400">Pending approval</div>
                  )}
                </div>
              </div>
            )}
          </div>

          <div className="flex justify-end mt-6">
            <button
              onClick={() => setShowDetails(false)}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
            >
              Close
            </button>
          </div>
        </div>
      </Modal>
    </>
  )
}

/**
 * Export controls component
 */
function ExportControls({
  onExport,
  currentFilter,
  loading = false
}: {
  onExport?: (format: 'csv' | 'json' | 'pdf', filter?: AuditLogFilter) => Promise<boolean>
  currentFilter?: AuditLogFilter
  loading?: boolean
}) {
  const [exporting, setExporting] = useState<string | null>(null)

  const handleExport = async (format: 'csv' | 'json' | 'pdf') => {
    if (!onExport) return

    setExporting(format)
    try {
      await onExport(format, currentFilter)
    } finally {
      setExporting(null)
    }
  }

  return (
    <div className="flex items-center space-x-2">
      <span className="text-gray-400 text-sm">Export:</span>
      <button
        onClick={() => handleExport('csv')}
        disabled={loading || exporting === 'csv'}
        className="bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white px-3 py-1 rounded text-sm"
      >
        {exporting === 'csv' ? 'Exporting...' : 'CSV'}
      </button>
      <button
        onClick={() => handleExport('json')}
        disabled={loading || exporting === 'json'}
        className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-3 py-1 rounded text-sm"
      >
        {exporting === 'json' ? 'Exporting...' : 'JSON'}
      </button>
      <button
        onClick={() => handleExport('pdf')}
        disabled={loading || exporting === 'pdf'}
        className="bg-red-600 hover:bg-red-700 disabled:bg-gray-600 text-white px-3 py-1 rounded text-sm"
      >
        {exporting === 'pdf' ? 'Exporting...' : 'PDF'}
      </button>
    </div>
  )
}

/**
 * Main AuditLogViewer component
 */
export function AuditLogViewer({
  auditLogs,
  approvalWorkflows = [],
  loading = false,
  error,
  onRefresh,
  onExport
}: AuditLogViewerProps) {
  const [currentFilter, setCurrentFilter] = useState<AuditLogFilter>({})
  const [viewMode, setViewMode] = useState<'list' | 'compact'>('list')

  const filteredLogs = useMemo(() => {
    let filtered = [...auditLogs]

    if (currentFilter.action) {
      filtered = filtered.filter(log => log.action === currentFilter.action)
    }

    if (currentFilter.resource) {
      filtered = filtered.filter(log => log.resource === currentFilter.resource)
    }

    if (currentFilter.riskLevel) {
      filtered = filtered.filter(log => log.riskLevel === currentFilter.riskLevel)
    }

    if (currentFilter.result) {
      filtered = filtered.filter(log => log.result === currentFilter.result)
    }

    if (currentFilter.dateFrom) {
      filtered = filtered.filter(log => log.timestamp >= currentFilter.dateFrom!)
    }

    if (currentFilter.dateTo) {
      filtered = filtered.filter(log => log.timestamp <= currentFilter.dateTo!)
    }

    if (currentFilter.userId) {
      filtered = filtered.filter(log => log.userId === currentFilter.userId)
    }

    return filtered.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
  }, [auditLogs, currentFilter])

  const handleFilterChange = (filter: AuditLogFilter) => {
    setCurrentFilter(filter)
    if (onRefresh) {
      onRefresh(filter)
    }
  }

  if (loading && auditLogs.length === 0) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-700 rounded w-48"></div>
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-32 bg-gray-700 rounded"></div>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <div className="text-center py-8">
          <div className="text-red-400 text-lg mb-2">Error Loading Audit Logs</div>
          <p className="text-gray-400 mb-4">{error}</p>
          {onRefresh && (
            <button
              onClick={() => onRefresh()}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
            >
              Retry
            </button>
          )}
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-white mb-1">Audit Log Viewer</h2>
          <p className="text-sm text-gray-400">Complete audit trail of administrator actions - Read-only access</p>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="flex bg-gray-700 rounded-lg p-1">
            <button
              onClick={() => setViewMode('list')}
              className={`px-3 py-1 rounded text-sm transition-colors ${
                viewMode === 'list'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Detailed
            </button>
            <button
              onClick={() => setViewMode('compact')}
              className={`px-3 py-1 rounded text-sm transition-colors ${
                viewMode === 'compact'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Compact
            </button>
          </div>
          
          {onExport && (
            <ExportControls
              onExport={onExport}
              currentFilter={currentFilter}
              loading={loading}
            />
          )}
          
          {onRefresh && (
            <button
              onClick={() => onRefresh(currentFilter)}
              disabled={loading}
              className="bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white px-4 py-2 rounded text-sm font-medium"
            >
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
          )}
        </div>
      </div>

      {/* Filters */}
      <AuditLogFilter onFilterChange={handleFilterChange} currentFilter={currentFilter} />

      {/* Statistics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <div className="text-center">
            <div className="text-2xl font-bold text-white">{filteredLogs.length}</div>
            <div className="text-sm text-gray-400">Filtered Entries</div>
          </div>
        </Card>
        
        <Card>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-400">
              {filteredLogs.filter(log => log.result === 'success').length}
            </div>
            <div className="text-sm text-gray-400">Successful</div>
          </div>
        </Card>
        
        <Card>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-400">
              {filteredLogs.filter(log => log.result === 'failure').length}
            </div>
            <div className="text-sm text-gray-400">Failed</div>
          </div>
        </Card>
        
        <Card>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-400">
              {filteredLogs.filter(log => log.riskLevel === 'critical' || log.riskLevel === 'high').length}
            </div>
            <div className="text-sm text-gray-400">High Risk</div>
          </div>
        </Card>
      </div>

      {/* Audit Log Entries */}
      {filteredLogs.length === 0 ? (
        <Card>
          <div className="text-center py-12">
            <div className="text-gray-400 text-lg mb-2">No Audit Logs Found</div>
            <p className="text-gray-500">
              No audit log entries match the current filter criteria
            </p>
          </div>
        </Card>
      ) : (
        <div className={viewMode === 'compact' ? "space-y-2" : "space-y-4"}>
          {filteredLogs.map(entry => (
            <AuditLogEntryCard
              key={entry.id}
              entry={entry}
              compact={viewMode === 'compact'}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default AuditLogViewer