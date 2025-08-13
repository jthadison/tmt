'use client'

import { useMemo } from 'react'
import { ComplianceStatus, ComplianceViolation } from '@/types/accountDetail'

/**
 * Props for ComplianceMonitor component
 */
interface ComplianceMonitorProps {
  /** Compliance status data */
  complianceStatus: ComplianceStatus
  /** Loading state indicator */
  loading?: boolean
  /** Show detailed compliance information */
  detailed?: boolean
}

/**
 * Real-time compliance monitoring dashboard
 * Displays prop firm rule adherence and violation alerts
 */
export function ComplianceMonitor({
  complianceStatus,
  loading = false,
  detailed = false
}: ComplianceMonitorProps) {

  // Calculate overall compliance score
  const complianceScore = useMemo(() => {
    const metrics = [
      { weight: 0.3, score: Math.max(0, 100 - complianceStatus.dailyLossLimit.percentage) },
      { weight: 0.25, score: Math.max(0, 100 - complianceStatus.monthlyLossLimit.percentage) },
      { weight: 0.25, score: Math.max(0, 100 - complianceStatus.maxDrawdown.percentage) },
      { weight: 0.2, score: Math.min(100, complianceStatus.minTradingDays.percentage) }
    ]
    
    return metrics.reduce((total, metric) => total + (metric.score * metric.weight), 0)
  }, [complianceStatus])

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount)
  }

  const formatPercentage = (value: number): string => {
    return `${value.toFixed(1)}%`
  }

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'compliant':
        return 'text-green-400'
      case 'warning':
        return 'text-yellow-400'
      case 'violation':
        return 'text-red-400'
      default:
        return 'text-gray-400'
    }
  }

  const getStatusIcon = (status: string): string => {
    switch (status) {
      case 'compliant':
        return '✓'
      case 'warning':
        return '⚠'
      case 'violation':
        return '✗'
      default:
        return '○'
    }
  }

  const getProgressBarColor = (percentage: number, isInverse: boolean = false): string => {
    // For inverse metrics (like trading days), higher is better
    const effective = isInverse ? 100 - percentage : percentage
    
    if (effective <= 50) return 'bg-green-500'
    if (effective <= 75) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  const getRiskLevel = (percentage: number, isInverse: boolean = false): string => {
    const effective = isInverse ? 100 - percentage : percentage
    
    if (effective <= 50) return 'Low Risk'
    if (effective <= 75) return 'Medium Risk'
    return 'High Risk'
  }

  const getSeverityColor = (severity: ComplianceViolation['severity']): string => {
    switch (severity) {
      case 'low':
        return 'text-blue-400 bg-blue-900/20'
      case 'medium':
        return 'text-yellow-400 bg-yellow-900/20'
      case 'high':
        return 'text-orange-400 bg-orange-900/20'
      case 'critical':
        return 'text-red-400 bg-red-900/20'
      default:
        return 'text-gray-400 bg-gray-900/20'
    }
  }

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-700 rounded w-40"></div>
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-16 bg-gray-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-lg font-semibold text-white">
          Compliance Monitor
        </h3>
        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-1 ${getStatusColor(complianceStatus.overallStatus)}`}>
            <span className="text-lg">{getStatusIcon(complianceStatus.overallStatus)}</span>
            <span className="font-medium capitalize">{complianceStatus.overallStatus}</span>
          </div>
          <div className="text-sm text-gray-400">
            Score: {complianceScore.toFixed(0)}/100
          </div>
        </div>
      </div>

      {/* Compliance Rules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {/* Daily Loss Limit */}
        <div className="bg-gray-750 rounded-lg p-4">
          <div className="flex justify-between items-start mb-2">
            <div>
              <div className="font-medium text-white">Daily Loss Limit</div>
              <div className="text-sm text-gray-400">{complianceStatus.accountTier}</div>
            </div>
            <div className={`text-xs px-2 py-1 rounded ${getSeverityColor(
              complianceStatus.dailyLossLimit.percentage > 80 ? 'critical' :
              complianceStatus.dailyLossLimit.percentage > 60 ? 'high' :
              complianceStatus.dailyLossLimit.percentage > 40 ? 'medium' : 'low'
            )}`}>
              {getRiskLevel(complianceStatus.dailyLossLimit.percentage)}
            </div>
          </div>
          
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Used</span>
              <span className="text-white">
                {formatCurrency(complianceStatus.dailyLossLimit.current)} / {formatCurrency(complianceStatus.dailyLossLimit.limit)}
              </span>
            </div>
            <div className="w-full bg-gray-600 rounded-full h-2">
              <div 
                className={`h-2 rounded-full transition-all duration-300 ${getProgressBarColor(complianceStatus.dailyLossLimit.percentage)}`}
                style={{ width: `${Math.min(100, complianceStatus.dailyLossLimit.percentage)}%` }}
              ></div>
            </div>
            <div className="text-right text-sm text-gray-400">
              {formatPercentage(complianceStatus.dailyLossLimit.percentage)}
            </div>
          </div>
        </div>

        {/* Monthly Loss Limit */}
        <div className="bg-gray-750 rounded-lg p-4">
          <div className="flex justify-between items-start mb-2">
            <div>
              <div className="font-medium text-white">Monthly Loss Limit</div>
              <div className="text-sm text-gray-400">Cumulative</div>
            </div>
            <div className={`text-xs px-2 py-1 rounded ${getSeverityColor(
              complianceStatus.monthlyLossLimit.percentage > 80 ? 'critical' :
              complianceStatus.monthlyLossLimit.percentage > 60 ? 'high' :
              complianceStatus.monthlyLossLimit.percentage > 40 ? 'medium' : 'low'
            )}`}>
              {getRiskLevel(complianceStatus.monthlyLossLimit.percentage)}
            </div>
          </div>
          
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Used</span>
              <span className="text-white">
                {formatCurrency(complianceStatus.monthlyLossLimit.current)} / {formatCurrency(complianceStatus.monthlyLossLimit.limit)}
              </span>
            </div>
            <div className="w-full bg-gray-600 rounded-full h-2">
              <div 
                className={`h-2 rounded-full transition-all duration-300 ${getProgressBarColor(complianceStatus.monthlyLossLimit.percentage)}`}
                style={{ width: `${Math.min(100, complianceStatus.monthlyLossLimit.percentage)}%` }}
              ></div>
            </div>
            <div className="text-right text-sm text-gray-400">
              {formatPercentage(complianceStatus.monthlyLossLimit.percentage)}
            </div>
          </div>
        </div>

        {/* Max Drawdown */}
        <div className="bg-gray-750 rounded-lg p-4">
          <div className="flex justify-between items-start mb-2">
            <div>
              <div className="font-medium text-white">Max Drawdown</div>
              <div className="text-sm text-gray-400">Peak to trough</div>
            </div>
            <div className={`text-xs px-2 py-1 rounded ${getSeverityColor(
              complianceStatus.maxDrawdown.percentage > 80 ? 'critical' :
              complianceStatus.maxDrawdown.percentage > 60 ? 'high' :
              complianceStatus.maxDrawdown.percentage > 40 ? 'medium' : 'low'
            )}`}>
              {getRiskLevel(complianceStatus.maxDrawdown.percentage)}
            </div>
          </div>
          
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Current</span>
              <span className="text-white">
                {formatCurrency(complianceStatus.maxDrawdown.current)} / {formatCurrency(complianceStatus.maxDrawdown.limit)}
              </span>
            </div>
            <div className="w-full bg-gray-600 rounded-full h-2">
              <div 
                className={`h-2 rounded-full transition-all duration-300 ${getProgressBarColor(complianceStatus.maxDrawdown.percentage)}`}
                style={{ width: `${Math.min(100, complianceStatus.maxDrawdown.percentage)}%` }}
              ></div>
            </div>
            <div className="text-right text-sm text-gray-400">
              {formatPercentage(complianceStatus.maxDrawdown.percentage)}
            </div>
          </div>
        </div>

        {/* Min Trading Days */}
        <div className="bg-gray-750 rounded-lg p-4">
          <div className="flex justify-between items-start mb-2">
            <div>
              <div className="font-medium text-white">Trading Days</div>
              <div className="text-sm text-gray-400">Minimum required</div>
            </div>
            <div className={`text-xs px-2 py-1 rounded ${getSeverityColor(
              complianceStatus.minTradingDays.percentage < 20 ? 'critical' :
              complianceStatus.minTradingDays.percentage < 40 ? 'high' :
              complianceStatus.minTradingDays.percentage < 70 ? 'medium' : 'low'
            )}`}>
              {getRiskLevel(complianceStatus.minTradingDays.percentage, true)}
            </div>
          </div>
          
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Progress</span>
              <span className="text-white">
                {complianceStatus.minTradingDays.current} / {complianceStatus.minTradingDays.required} days
              </span>
            </div>
            <div className="w-full bg-gray-600 rounded-full h-2">
              <div 
                className={`h-2 rounded-full transition-all duration-300 ${getProgressBarColor(100 - complianceStatus.minTradingDays.percentage, true)}`}
                style={{ width: `${Math.min(100, complianceStatus.minTradingDays.percentage)}%` }}
              ></div>
            </div>
            <div className="text-right text-sm text-gray-400">
              {formatPercentage(complianceStatus.minTradingDays.percentage)}
            </div>
          </div>
        </div>
      </div>

      {/* Violations Section */}
      {complianceStatus.violations.length > 0 && (
        <div className="mb-4">
          <div className="flex justify-between items-center mb-3">
            <h4 className="font-medium text-white">Recent Violations</h4>
            <span className="text-sm text-gray-400">
              {complianceStatus.violations.filter(v => !v.resolved).length} active
            </span>
          </div>
          <div className="space-y-2">
            {complianceStatus.violations.slice(0, detailed ? undefined : 3).map((violation) => (
              <div 
                key={violation.id}
                className={`p-3 rounded-lg border-l-4 ${
                  violation.resolved 
                    ? 'bg-gray-750 border-gray-500' 
                    : 'bg-red-900/20 border-red-500'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs px-2 py-1 rounded ${getSeverityColor(violation.severity)}`}>
                        {violation.severity.toUpperCase()}
                      </span>
                      <span className="text-sm font-medium text-white">
                        {violation.ruleType}
                      </span>
                      {violation.resolved && (
                        <span className="text-xs text-green-400">✓ Resolved</span>
                      )}
                    </div>
                    <p className="text-sm text-gray-300">{violation.description}</p>
                    <div className="text-xs text-gray-500 mt-1">
                      {violation.timestamp.toLocaleDateString()} {violation.timestamp.toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
          {!detailed && complianceStatus.violations.length > 3 && (
            <div className="text-center mt-3">
              <button className="text-blue-400 hover:text-blue-300 text-sm transition-colors">
                View all {complianceStatus.violations.length} violations
              </button>
            </div>
          )}
        </div>
      )}

      {/* Summary Status */}
      <div className="bg-gray-750 rounded-lg p-4">
        <div className="flex justify-between items-center">
          <div>
            <div className="text-white font-medium">Overall Compliance Status</div>
            <div className="text-sm text-gray-400 mt-1">
              Account is currently {complianceStatus.overallStatus} with all prop firm requirements
            </div>
          </div>
          <div className="text-right">
            <div className={`text-xl font-bold ${getStatusColor(complianceStatus.overallStatus)}`}>
              {complianceScore.toFixed(0)}%
            </div>
            <div className="text-sm text-gray-400">Compliance Score</div>
          </div>
        </div>
        
        {complianceStatus.overallStatus !== 'compliant' && (
          <div className="mt-3 p-3 bg-yellow-900/20 rounded border-l-4 border-yellow-500">
            <div className="text-yellow-400 text-sm font-medium">Action Required</div>
            <div className="text-yellow-200 text-sm mt-1">
              {complianceStatus.overallStatus === 'warning' 
                ? 'Monitor trading activity closely to maintain compliance.'
                : 'Immediate attention needed to resolve violations and restore account standing.'}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}