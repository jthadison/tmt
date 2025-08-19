'use client'

import React, { useState, useEffect } from 'react'
import { 
  TradeExecution, 
  OrderLifecycle, 
  ExecutionExportConfig
} from '@/types/tradeExecution'
import Modal from '@/components/ui/Modal'
import Card from '@/components/ui/Card'
import { OrderLifecycleTracker } from './OrderLifecycleTracker'

/**
 * Props for TradeDetailsModal component
 */
interface TradeDetailsModalProps {
  /** Whether the modal is open */
  isOpen: boolean
  /** Callback to close the modal */
  onClose: () => void
  /** Trade execution to display */
  execution: TradeExecution | null
  /** Order lifecycle data */
  lifecycle?: OrderLifecycle
  /** Loading state */
  loading?: boolean
  /** Error message */
  error?: string
  /** Callback to fetch lifecycle data */
  onFetchLifecycle?: (orderId: string) => Promise<OrderLifecycle | null>
  /** Callback to export trade details */
  onExportTrade?: (execution: TradeExecution, format: 'csv' | 'json' | 'pdf') => Promise<void>
  /** Show lifecycle tracker */
  showLifecycle?: boolean
}

/**
 * Trade information section
 */
function TradeInfo({ 
  execution 
}: { 
  execution: TradeExecution
}) {
  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 5
    }).format(amount)
  }

  const formatNumber = (num: number): string => {
    return new Intl.NumberFormat('en-US').format(num)
  }

  const formatPercent = (value: number): string => {
    return `${value.toFixed(3)}%`
  }

  const formatSlippage = (slippage: number): string => {
    const pips = slippage * 10000
    return `${pips >= 0 ? '+' : ''}${pips.toFixed(1)} pips`
  }

  const getDirectionColor = (direction: string): string => {
    return direction === 'buy' ? 'text-green-400' : 'text-red-400'
  }

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'filled': return 'text-green-400 bg-green-900/20 border-green-500/30'
      case 'partial': return 'text-yellow-400 bg-yellow-900/20 border-yellow-500/30'
      case 'pending': return 'text-blue-400 bg-blue-900/20 border-blue-500/30'
      case 'rejected': return 'text-red-400 bg-red-900/20 border-red-500/30'
      case 'cancelled': return 'text-gray-400 bg-gray-900/20 border-gray-500/30'
      default: return 'text-gray-400 bg-gray-900/20 border-gray-500/30'
    }
  }

  const calculatePnLImpact = (): number => {
    if (!execution.executedPrice || !execution.requestedPrice) return 0
    const priceDiff = execution.direction === 'buy' ? 
      execution.executedPrice - execution.requestedPrice :
      execution.requestedPrice - execution.executedPrice
    return priceDiff * execution.executedSize
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Basic Information */}
      <Card>
        <h3 className="text-lg font-semibold text-white mb-4">Basic Information</h3>
        <div className="space-y-3">
          <div className="flex justify-between">
            <span className="text-gray-400">Execution ID:</span>
            <span className="font-mono text-white text-sm">{execution.id}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Order ID:</span>
            <span className="font-mono text-white text-sm">{execution.orderId}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Account:</span>
            <span className="text-white">{execution.accountAlias}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Broker:</span>
            <span className="text-white">{execution.broker}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Platform:</span>
            <span className="text-white">{execution.platform}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Status:</span>
            <span className={`px-2 py-1 rounded text-xs font-medium border ${getStatusColor(execution.status)}`}>
              {execution.status.toUpperCase()}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Priority:</span>
            <span className="text-white capitalize">{execution.priority}</span>
          </div>
        </div>
      </Card>

      {/* Trade Details */}
      <Card>
        <h3 className="text-lg font-semibold text-white mb-4">Trade Details</h3>
        <div className="space-y-3">
          <div className="flex justify-between">
            <span className="text-gray-400">Instrument:</span>
            <span className="font-semibold text-white">{execution.instrument}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Direction:</span>
            <span className={`font-semibold ${getDirectionColor(execution.direction)}`}>
              {execution.direction.toUpperCase()}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Requested Size:</span>
            <span className="text-white">{formatNumber(execution.requestedSize)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Executed Size:</span>
            <span className="text-white">{formatNumber(execution.executedSize)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Remaining Size:</span>
            <span className="text-white">{formatNumber(execution.remainingSize)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Fill Rate:</span>
            <span className="text-white">
              {((execution.executedSize / execution.requestedSize) * 100).toFixed(1)}%
            </span>
          </div>
        </div>
      </Card>

      {/* Pricing Information */}
      <Card>
        <h3 className="text-lg font-semibold text-white mb-4">Pricing Information</h3>
        <div className="space-y-3">
          <div className="flex justify-between">
            <span className="text-gray-400">Requested Price:</span>
            <span className="text-white">
              {execution.requestedPrice ? formatCurrency(execution.requestedPrice) : 'Market'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Executed Price:</span>
            <span className="text-white">
              {execution.executedPrice ? formatCurrency(execution.executedPrice) : '-'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Average Price:</span>
            <span className="text-white">
              {execution.averagePrice ? formatCurrency(execution.averagePrice) : '-'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Market Price:</span>
            <span className="text-white">
              {execution.marketPrice ? formatCurrency(execution.marketPrice) : '-'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Slippage:</span>
            <span className={`font-medium ${
              execution.slippage > 0.002 ? 'text-red-400' :
              execution.slippage > 0.001 ? 'text-yellow-400' : 'text-green-400'
            }`}>
              {formatSlippage(execution.slippage)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Slippage %:</span>
            <span className={`font-medium ${
              execution.slippagePercent > 0.1 ? 'text-red-400' :
              execution.slippagePercent > 0.05 ? 'text-yellow-400' : 'text-green-400'
            }`}>
              {formatPercent(execution.slippagePercent)}
            </span>
          </div>
        </div>
      </Card>

      {/* Financial Impact */}
      <Card>
        <h3 className="text-lg font-semibold text-white mb-4">Financial Impact</h3>
        <div className="space-y-3">
          <div className="flex justify-between">
            <span className="text-gray-400">P&L Impact:</span>
            <span className={`font-semibold ${
              calculatePnLImpact() >= 0 ? 'text-green-400' : 'text-red-400'
            }`}>
              {calculatePnLImpact() >= 0 ? '+' : ''}{formatCurrency(calculatePnLImpact())}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Commission:</span>
            <span className="text-orange-400">{formatCurrency(execution.fees.commission)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Spread Cost:</span>
            <span className="text-orange-400">{formatCurrency(execution.fees.spread)}</span>
          </div>
          {execution.fees.swapFee && (
            <div className="flex justify-between">
              <span className="text-gray-400">Swap Fee:</span>
              <span className="text-orange-400">{formatCurrency(execution.fees.swapFee)}</span>
            </div>
          )}
          {execution.fees.regulatoryFee && (
            <div className="flex justify-between">
              <span className="text-gray-400">Regulatory Fee:</span>
              <span className="text-orange-400">{formatCurrency(execution.fees.regulatoryFee)}</span>
            </div>
          )}
          <hr className="border-gray-700" />
          <div className="flex justify-between">
            <span className="text-gray-400 font-medium">Total Fees:</span>
            <span className="text-orange-400 font-semibold">{formatCurrency(execution.fees.total)}</span>
          </div>
        </div>
      </Card>
    </div>
  )
}

/**
 * Timestamps section
 */
function TimestampsInfo({ 
  execution 
}: { 
  execution: TradeExecution
}) {
  const formatDateTime = (date: Date): string => {
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3
    })
  }

  const calculateDuration = (start: Date, end?: Date): string => {
    if (!end) return '-'
    const diff = end.getTime() - start.getTime()
    if (diff < 1000) return `${diff}ms`
    return `${(diff / 1000).toFixed(2)}s`
  }

  return (
    <Card>
      <h3 className="text-lg font-semibold text-white mb-4">Timeline</h3>
      <div className="space-y-4">
        <div className="flex justify-between items-center p-3 bg-gray-800 rounded">
          <div>
            <div className="font-medium text-white">Order Created</div>
            <div className="text-sm text-gray-400">{formatDateTime(execution.timestamps.created)}</div>
          </div>
          <div className="text-xs text-green-400">✓</div>
        </div>

        <div className="flex justify-between items-center p-3 bg-gray-800 rounded">
          <div>
            <div className="font-medium text-white">Submitted to Broker</div>
            <div className="text-sm text-gray-400">{formatDateTime(execution.timestamps.submitted)}</div>
            <div className="text-xs text-blue-400">
              +{calculateDuration(execution.timestamps.created, execution.timestamps.submitted)} from creation
            </div>
          </div>
          <div className="text-xs text-green-400">✓</div>
        </div>

        {execution.timestamps.acknowledged && (
          <div className="flex justify-between items-center p-3 bg-gray-800 rounded">
            <div>
              <div className="font-medium text-white">Broker Acknowledgment</div>
              <div className="text-sm text-gray-400">{formatDateTime(execution.timestamps.acknowledged)}</div>
              <div className="text-xs text-blue-400">
                +{calculateDuration(execution.timestamps.submitted, execution.timestamps.acknowledged)} from submission
              </div>
            </div>
            <div className="text-xs text-green-400">✓</div>
          </div>
        )}

        {execution.timestamps.partialFills.length > 0 && (
          <div className="space-y-2">
            {execution.timestamps.partialFills.map((fill, index) => (
              <div key={fill.id} className="flex justify-between items-center p-3 bg-gray-800 rounded">
                <div>
                  <div className="font-medium text-white">Partial Fill #{index + 1}</div>
                  <div className="text-sm text-gray-400">{formatDateTime(fill.timestamp)}</div>
                  <div className="text-xs text-gray-400">
                    Size: {formatNumber(fill.size)} @ {formatCurrency(fill.price)}
                  </div>
                </div>
                <div className="text-xs text-yellow-400">◐</div>
              </div>
            ))}
          </div>
        )}

        {execution.timestamps.completed && (
          <div className="flex justify-between items-center p-3 bg-green-900/20 border border-green-500/30 rounded">
            <div>
              <div className="font-medium text-white">Execution Completed</div>
              <div className="text-sm text-gray-400">{formatDateTime(execution.timestamps.completed)}</div>
              <div className="text-xs text-green-400">
                Total time: {calculateDuration(execution.timestamps.created, execution.timestamps.completed)}
              </div>
            </div>
            <div className="text-xs text-green-400">✓</div>
          </div>
        )}

        {execution.timestamps.cancelled && (
          <div className="flex justify-between items-center p-3 bg-red-900/20 border border-red-500/30 rounded">
            <div>
              <div className="font-medium text-white">Execution Cancelled</div>
              <div className="text-sm text-gray-400">{formatDateTime(execution.timestamps.cancelled)}</div>
              <div className="text-xs text-red-400">
                Reason: {execution.reasonMessage || 'Unknown'}
              </div>
            </div>
            <div className="text-xs text-red-400">✗</div>
          </div>
        )}
      </div>
    </Card>
  )
}

/**
 * Related orders and metadata
 */
function AdditionalInfo({ 
  execution 
}: { 
  execution: TradeExecution
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Related Orders */}
      <Card>
        <h3 className="text-lg font-semibold text-white mb-4">Related Orders</h3>
        {execution.relatedOrders.length > 0 ? (
          <div className="space-y-2">
            {execution.relatedOrders.map(orderId => (
              <div key={orderId} className="flex justify-between items-center p-2 bg-gray-800 rounded">
                <span className="font-mono text-sm text-white">{orderId}</span>
                <button className="text-blue-400 hover:text-blue-300 text-sm">
                  View
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-gray-400 text-sm">No related orders</div>
        )}

        {execution.parentOrderId && (
          <div className="mt-4">
            <div className="text-gray-400 text-sm mb-2">Parent Order:</div>
            <div className="flex justify-between items-center p-2 bg-gray-800 rounded">
              <span className="font-mono text-sm text-white">{execution.parentOrderId}</span>
              <button className="text-blue-400 hover:text-blue-300 text-sm">
                View Parent
              </button>
            </div>
          </div>
        )}
      </Card>

      {/* Metadata and Tags */}
      <Card>
        <h3 className="text-lg font-semibold text-white mb-4">Metadata</h3>
        <div className="space-y-4">
          {/* Tags */}
          {execution.tags.length > 0 && (
            <div>
              <div className="text-gray-400 text-sm mb-2">Tags:</div>
              <div className="flex flex-wrap gap-2">
                {execution.tags.map(tag => (
                  <span key={tag} className="px-2 py-1 bg-blue-900/30 text-blue-400 text-xs rounded">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Metadata */}
          {Object.keys(execution.metadata).length > 0 && (
            <div>
              <div className="text-gray-400 text-sm mb-2">Additional Data:</div>
              <div className="space-y-2">
                {Object.entries(execution.metadata).map(([key, value]) => (
                  <div key={key} className="flex justify-between">
                    <span className="text-gray-400 text-sm">{key}:</span>
                    <span className="text-white text-sm font-mono">
                      {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Venue Information */}
          {execution.venue && (
            <div>
              <div className="text-gray-400 text-sm mb-2">Execution Venue:</div>
              <div className="text-white text-sm">{execution.venue}</div>
            </div>
          )}

          {/* Reason for Rejection/Cancellation */}
          {(execution.reasonCode || execution.reasonMessage) && (
            <div>
              <div className="text-gray-400 text-sm mb-2">Reason:</div>
              <div className="p-2 bg-red-900/20 border border-red-500/30 rounded">
                {execution.reasonCode && (
                  <div className="text-red-400 text-sm font-medium">{execution.reasonCode}</div>
                )}
                {execution.reasonMessage && (
                  <div className="text-red-300 text-sm">{execution.reasonMessage}</div>
                )}
              </div>
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}

/**
 * Export controls
 */
function ExportControls({
  execution,
  onExport,
  loading = false
}: {
  execution: TradeExecution
  onExport?: (execution: TradeExecution, format: 'csv' | 'json' | 'pdf') => Promise<void>
  loading?: boolean
}) {
  const [exporting, setExporting] = useState<string | null>(null)

  const handleExport = async (format: 'csv' | 'json' | 'pdf') => {
    if (!onExport) return
    
    setExporting(format)
    try {
      await onExport(execution, format)
    } catch (error) {
      console.error('Export failed:', error)
    } finally {
      setExporting(null)
    }
  }

  return (
    <div className="flex items-center space-x-2">
      <span className="text-gray-400 text-sm">Export:</span>
      <button
        onClick={() => handleExport('json')}
        disabled={loading || exporting === 'json'}
        className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-3 py-1 rounded text-sm"
      >
        {exporting === 'json' ? 'Exporting...' : 'JSON'}
      </button>
      <button
        onClick={() => handleExport('csv')}
        disabled={loading || exporting === 'csv'}
        className="bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white px-3 py-1 rounded text-sm"
      >
        {exporting === 'csv' ? 'Exporting...' : 'CSV'}
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
 * Main TradeDetailsModal component
 */
export function TradeDetailsModal({
  isOpen,
  onClose,
  execution,
  lifecycle,
  loading = false,
  error,
  onFetchLifecycle,
  onExportTrade,
  showLifecycle = true
}: TradeDetailsModalProps) {
  const [activeTab, setActiveTab] = useState<'details' | 'timeline' | 'lifecycle' | 'additional'>('details')

  // Reset tab when execution changes
  useEffect(() => {
    if (execution) {
      setActiveTab('details')
    }
  }, [execution])

  if (!execution) {
    return null
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <div className="bg-gray-900 min-h-screen max-h-screen overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gray-900 border-b border-gray-700 p-6 z-10">
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-2xl font-bold text-white mb-2">Trade Execution Details</h2>
              <p className="text-gray-400">
                {execution.instrument} • {execution.direction.toUpperCase()} {execution.executedSize.toLocaleString()}
              </p>
              <p className="text-sm text-gray-500">
                {execution.timestamps.lastUpdate.toLocaleString()}
              </p>
            </div>
            
            <div className="flex items-center space-x-4">
              {onExportTrade && (
                <ExportControls
                  execution={execution}
                  onExport={onExportTrade}
                  loading={loading}
                />
              )}
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-white"
              >
                ✕
              </button>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="flex space-x-1 mt-6 bg-gray-800 rounded-lg p-1">
            <button
              onClick={() => setActiveTab('details')}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                activeTab === 'details'
                  ? 'bg-gray-700 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Trade Details
            </button>
            <button
              onClick={() => setActiveTab('timeline')}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                activeTab === 'timeline'
                  ? 'bg-gray-700 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Timeline
            </button>
            {showLifecycle && (
              <button
                onClick={() => setActiveTab('lifecycle')}
                className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                  activeTab === 'lifecycle'
                    ? 'bg-gray-700 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Order Lifecycle
              </button>
            )}
            <button
              onClick={() => setActiveTab('additional')}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                activeTab === 'additional'
                  ? 'bg-gray-700 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Additional Info
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {error && (
            <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-4">
              <div className="text-red-400 font-medium">Error</div>
              <div className="text-red-300 text-sm">{error}</div>
            </div>
          )}

          {activeTab === 'details' && <TradeInfo execution={execution} />}
          {activeTab === 'timeline' && <TimestampsInfo execution={execution} />}
          {activeTab === 'lifecycle' && showLifecycle && (
            <OrderLifecycleTracker
              orderId={execution.orderId}
              lifecycle={lifecycle}
              loading={loading}
              error={error}
              onFetchLifecycle={onFetchLifecycle}
              showLatency={true}
            />
          )}
          {activeTab === 'additional' && <AdditionalInfo execution={execution} />}
        </div>
      </div>
    </Modal>
  )
}

export default TradeDetailsModal